#!/usr/bin/env python3
"""
breakout_ledger.py -- forward record for the 100-day breakout rule.

WHY A SECOND LEDGER, AND WHY IT IS NOT signal_ledger.py
  signal_ledger.py records the 200-day REGIME rule: one call per asset, settled
  when the regime flips, scored on mean return AND a win-run test at p <= 0.05,
  30 signals to clear. That is right for that rule and WRONG for this one, and
  the difference is measured, not stylistic:

  Breakout-100, on 33 assets over 5.7 years (2026-09-07, BREAKOUT_GAUNTLET.md):
      1,304 trades   win rate 33.1%   median trade -2.28%   mean +1.55%
      sd 16.22%      skew +5.19       top 5 trades = 36% of all return

  It LOSES TWO TRADES OUT OF THREE BY DESIGN. Simulated: a 30-signal sample
  from this distribution shows under 50% wins **98% of the time**. Point
  signal_ledger's win-run gate at this rule and it rejects a working strategy
  in 98 runs out of 100. The scoring test has to match the return shape, so
  this file scores the MEAN with a bootstrap interval and refuses to report a
  win rate as a verdict at all.

THE SAMPLE SIZE, STATED UP FRONT BECAUSE IT DECIDES EVERYTHING
  mean 1.546%, sd 16.22%  ->  n for 80% power at p<0.05 = ((1.96+0.84)*sd/m)^2
      = 863 settled trades.
  At ~7 trades per asset per year that is:
      one asset            123 years
      the 10-asset book     12.5 years
      33 assets              3.8 years
      ~200 liquid assets    ~7 months
  **Watching more assets is the only lever that makes this answerable.** Not
  more capital, not faster bars, not more variants. A forward record needs only
  100 bars of warm-up per asset, so the watchlist does NOT have to be assets
  with five years of history, and does NOT have to be assets you own.

WHAT IT DOES NOT DO
  It records. It does not place, prepare or size an order, hold a key, or feed
  the trader's `sealed_signals` counter -- that number belongs to Rule 5 and
  the regime rule, and two rules sharing one counter is how a gate gets cleared
  by the wrong evidence. This ledger has its own file and its own gate.

  No backfill. A call recorded after its outcome is known is not a prediction.
  Entries are hash-chained: editing record n breaks every record after it.

WHERE IT LIVES
  ~/.covenant/breakout_signals.jsonl -- beside regime_signals.jsonl, OUTSIDE
  the synced folder, for the reasons in PAPER_RUN.md section 3.

USAGE -- every flag here exists in the parser, and the suite asserts that.
  python breakout_ledger.py --record                  # one cycle, fetched
  python breakout_ledger.py --record --watchlist 200  # how many pairs to watch
  python breakout_ledger.py --record --quotes q.json  # offline / no network
  python breakout_ledger.py                           # the record and the verdict
  python breakout_ledger.py --verify                  # chain integrity
  python breakout_ledger.py --json                    # machine-readable summary
LICENCE: public domain.
"""
from __future__ import annotations
import argparse, hashlib, json, math, os, random, statistics, sys, time
from typing import Any, Dict, List, Optional, Tuple

HOME = os.path.expanduser("~")
LEDGER = os.environ.get("COVENANT_BREAKOUT_LEDGER") or os.path.join(
    HOME, ".covenant", "breakout_signals.jsonl")

WINDOW = 100                    # the rule: new 100-day high
COST_BPS = 60 * 2 + 10          # 130 bps round trip, same as signal_ledger.py
MIN_TRADES = 863                # the power calculation above, not a round number
STALE_DAYS = 7                  # see settle_stale() -- this one is a bias control
DAY_TZ = "UTC"                  # day boundaries are UTC, stated because
                                # signal_ledger.py uses local time and a ledger
                                # that mixes the two double-counts one day a year
GENESIS = "0" * 64


# --------------------------------------------------------------- chain
def _canon(p: Dict[str, Any]) -> bytes:
    return json.dumps(p, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def _hash(prev: str, p: Dict[str, Any]) -> str:
    h = hashlib.sha256(); h.update(prev.encode("ascii")); h.update(b"\x00")
    h.update(_canon(p)); return h.hexdigest()


def _reject(_c): raise ValueError("non-finite number in ledger")


def _read(path: str = LEDGER) -> List[Dict[str, Any]]:
    if not os.path.exists(path): return []
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line: out.append(json.loads(line, parse_constant=_reject))
    return out


def verify(path: str = LEDGER) -> Tuple[bool, str]:
    rows, prev, seq = _read(path), GENESIS, 0
    seen_open, settled = set(), set()
    for i, r in enumerate(rows, 1):
        p = r.get("payload")
        if not isinstance(p, dict) or r.get("prev") != prev:
            return False, f"line {i}: prev mismatch or malformed"
        if _hash(prev, p) != r.get("hash"):
            return False, f"line {i}: HASH MISMATCH -- this record changed after it was written"
        if p.get("seq") != seq:
            return False, f"line {i}: sequence {p.get('seq')!r}, expected {seq}"
        if p["kind"] == "open":
            if p["open_id"] in seen_open:
                return False, f"line {i}: duplicate open_id"
            seen_open.add(p["open_id"])
        elif p["kind"] == "settled":
            if p["open_id"] not in seen_open:
                return False, f"line {i}: settles an open_id that was never opened"
            if p["open_id"] in settled:
                return False, f"line {i}: already settled -- a call cannot be re-scored"
            if not float(p["settled_at"]) > float(p["sealed_at"]):
                return False, f"line {i}: settled at or before it was sealed (look-ahead)"
            settled.add(p["open_id"])
        prev = r["hash"]; seq += 1
    return True, f"{len(rows)} records, chain OK"


def _append(payload: Dict[str, Any], path: str = LEDGER) -> Dict[str, Any]:
    # Re-verifies the WHOLE chain before every write, which is O(n^2) if you
    # bulk-load. That is the right trade for one append a day and the wrong one
    # for a loop: reading only the tail would let a break earlier in the file
    # survive every future append and surface months later with the whole
    # record in doubt. If a bulk import is ever needed, write it as a separate
    # verified-once path rather than relaxing this.
    rows = _read(path)
    ok, why = verify(path)
    if not ok:
        raise RuntimeError(f"refusing to append to a broken ledger: {why}")
    prev = rows[-1]["hash"] if rows else GENESIS
    payload = dict(payload, seq=len(rows))
    if rows and float(payload["at"]) < float(rows[-1]["payload"]["at"]):
        raise RuntimeError("clock moved backwards; not appending")
    rec = {"payload": payload, "prev": prev, "hash": _hash(prev, payload)}
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a", encoding="ascii", newline="\n") as fh:
        fh.write(json.dumps(rec, sort_keys=True, separators=(",", ":")) + "\n")
        fh.flush(); os.fsync(fh.fileno())
    return rec


# --------------------------------------------------------------- the rule
def signal(closes: List[float], window: int = WINDOW) -> Optional[bool]:
    """True = at a new `window`-day high. None = not enough history yet.

    None is NOT False. A rule that has not warmed up has made no call, and
    recording it as 'no' would pad the count with records carrying no signal.
    """
    if len(closes) < window + 1: return None
    return closes[-1] >= max(closes[-window - 1:-1])


def record_cycle(quotes: List[Dict[str, Any]], now: Optional[float] = None,
                 path: str = LEDGER) -> Dict[str, Any]:
    """quotes: [{"sym", "closes": [...oldest..newest], "px"}] -- one call per day.

    Opens a call the first day an asset prints a new 100-day high; settles it
    the first day it no longer does. One read per local day, for the reason
    signal_ledger.py records: intraday re-runs turn noise into fake signals.
    """
    now = float(now if now is not None else time.time())
    day = time.strftime("%Y-%m-%d", time.gmtime(now))
    rows = _read(path)
    if any(r["payload"].get("kind") == "read" and r["payload"].get("day") == day for r in rows):
        return summary(path)
    if not quotes:
        return summary(path)                    # a cycle that read nothing has not read the day
    _append({"kind": "read", "day": day, "at": now, "n": len(quotes)}, path)

    open_calls = {}
    for r in _read(path):
        p = r["payload"]
        if p["kind"] == "open": open_calls[p["sym"]] = p
        elif p["kind"] == "settled": open_calls.pop(p["sym"], None)

    # PRE-REGISTERED CONDITION. Measured 2026-09-07 on two independent
    # periods -- 275 assets over 2025-11..2026-09, and 33 survivors over
    # 2021-2026 -- the ONLY conditioner that held the same sign in both is the
    # market regime: breakouts do materially worse while BTC is below its own
    # 100-day line (recent -4.41%/trade vs -1.18% above; five-year -0.51% vs
    # +1.69%). Asset volatility looked strong in one period and REVERSED in the
    # other (+2.61 vs -3.94), which is what a slice looks like when you check
    # it twice.
    #
    # It is recorded, not acted on. Stamping the state at seal time means the
    # forward record can test the condition later without RE-CUTTING the data,
    # which is the difference between a hypothesis and a fishing trip.
    regime = _market_regime(quotes)
    seen = set()
    for q in quotes:
        sym, px = str(q["sym"]), float(q["px"])
        seen.add(sym)
        sig = signal(list(q["closes"]))
        if sig is None: continue
        cur = open_calls.get(sym)
        if cur is None:
            if sig:
                _append({"kind": "open", "open_id": f"{sym}:{int(now)}", "sym": sym,
                         "entry": px, "window": WINDOW, "sealed_at": now, "at": now,
                         **regime}, path)
        elif not sig:
            _settle(cur, px, now, "exit", path)

    # MARKS. One small record per cycle carrying the current price of every
    # still-open call. It exists for settle_stale() below: without it, a call
    # on an asset that stops being quoted can only be settled at its ENTRY
    # price, which scores a collapse as zero.
    still = {s2: None for s2 in open_calls if s2 not in
             {r["payload"]["sym"] for r in _read(path)
              if r["payload"]["kind"] == "settled" and float(r["payload"]["at"]) >= now}}
    marks = {q2["sym"]: float(q2["px"]) for q2 in quotes if q2["sym"] in still}
    if marks:
        _append({"kind": "marks", "at": now, "px": marks}, path)

    settle_stale(now, seen, path)
    return summary(path)


def _market_regime(quotes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """The state of the market at seal time, stamped into every open call.

    btc_up   -- is BTC above its own 100-day mean? None when BTC is not in the
                quotes, because "unknown" and "no" are different facts.
    breadth  -- fraction of the watched universe at a new 100-day high.
    """
    btc = next((q for q in quotes if str(q["sym"]).upper() in ("BTC", "XBT")), None)
    up = None
    if btc is not None:
        c = list(btc["closes"])
        if len(c) >= WINDOW:
            up = bool(c[-1] > sum(c[-WINDOW:]) / WINDOW)
    hits = tot = 0
    for q in quotes:
        s = signal(list(q["closes"]))
        if s is None: continue
        tot += 1; hits += 1 if s else 0
    return {"btc_up": up, "breadth": round(hits / tot, 4) if tot else None}


def _settle(cur: Dict[str, Any], px: float, now: float, why: str,
            path: str = LEDGER) -> None:
    gross = px / float(cur["entry"]) - 1.0
    _append({"kind": "settled", "open_id": cur["open_id"], "sym": cur["sym"],
             "entry": float(cur["entry"]), "exit": px, "why": why,
             "btc_up": cur.get("btc_up"), "breadth": cur.get("breadth"),
             "sealed_at": float(cur["sealed_at"]), "settled_at": now, "at": now,
             "held_days": round((now - float(cur["sealed_at"])) / 86400, 2),
             "ret_gross": round(gross, 6),
             "ret_after_costs": round(gross - COST_BPS / 10_000.0, 6)}, path)


def settle_stale(now: float, seen: set, path: str = LEDGER,
                 stale_days: float = STALE_DAYS) -> int:
    """Settle open calls whose asset has stopped being quoted.

    THIS IS A BIAS CONTROL, NOT HOUSEKEEPING, and it is the one thing a
    forward record still gets wrong if nobody writes it.

    A forward ledger is immune to the survivorship bias that ruins backtests --
    you record what exists at the time. But only if you also CLOSE what stops
    existing. An asset that is delisted, halted, or simply stops being quoted
    is overwhelmingly one that collapsed; leave its call open forever and the
    loss never enters the record, which is survivorship bias walking back in
    through the exit. So: absent for `stale_days`, settled at the last MARKED
    price, flagged `why: stale`.

    Settling at the ENTRY price instead would score every collapse as exactly
    zero, which is worse than either alternative.
    """
    rows = _read(path)
    open_calls, last_mark, last_seen = {}, {}, {}
    for r in rows:
        p = r["payload"]
        k = p["kind"]
        if k == "open":
            open_calls[p["sym"]] = p; last_mark[p["sym"]] = float(p["entry"])
            last_seen[p["sym"]] = float(p["at"])
        elif k == "settled":
            open_calls.pop(p["sym"], None)
        elif k == "marks":
            for sym, px in p["px"].items():
                last_mark[sym] = float(px); last_seen[sym] = float(p["at"])
    n = 0
    for sym, cur in list(open_calls.items()):
        if sym in seen: continue
        gone = (now - last_seen.get(sym, float(cur["at"]))) / 86400.0
        if gone >= stale_days:
            _settle(cur, last_mark.get(sym, float(cur["entry"])), now, "stale", path)
            n += 1
    return n


# --------------------------------------------------------------- scoring
def summary(path: str = LEDGER, min_trades: int = MIN_TRADES) -> Dict[str, Any]:
    rows = _read(path)
    rets = [r["payload"]["ret_after_costs"] for r in rows if r["payload"]["kind"] == "settled"]
    opens = sum(1 for r in rows if r["payload"]["kind"] == "open")
    n = len(rets)
    stale = sum(1 for r in rows if r["payload"].get("why") == "stale")
    settled_rows = [r["payload"] for r in rows if r["payload"]["kind"] == "settled"]
    out = {"settled": n, "open": opens - n, "need": min_trades, "stale_settled": stale,
           "mean_after_costs": None, "ci_low": None, "ci_high": None, "sd": None,
           "n_needed_live": None, "ci_seed_stable": None,
           "win_rate": None, "clears": False, "why": ""}
    if n == 0:
        out["why"] = f"0 settled trades, need {min_trades}"; return out
    m = statistics.fmean(rets)
    out["mean_after_costs"] = round(m, 6)
    out["win_rate"] = round(sum(1 for r in rets if r > 0) / n, 4)
    # BOOTSTRAP, not a t-test: skew was +5.19 on the backtested distribution and
    # a t-interval on a distribution like that is not honest.
    def boot_ci(seed):
        rng = random.Random(seed)
        b = sorted(statistics.fmean([rng.choice(rets) for _ in range(n)]) for _ in range(2000))
        return b[50], b[-50]
    out["ci_low"], out["ci_high"] = (round(x, 6) for x in boot_ci(1))
    # SEED STABILITY. A bootstrap interval is itself a random quantity. If two
    # seeds disagree about whether zero is inside it, the answer is "not yet",
    # whatever seed 1 happened to say.
    lo2, _ = boot_ci(2)
    out["ci_seed_stable"] = (out["ci_low"] > 0) == (lo2 > 0)

    # THE REQUIRED n IS RECOMPUTED FROM THE LIVE DATA, not trusted from the
    # backtest. 863 came from one historical estimate of sd/mean; if the live
    # ratio is worse, the honest floor moves and this says so.
    sd = statistics.pstdev(rets) if n > 1 else 0.0
    out["sd"] = round(sd, 6)
    out["n_needed_live"] = (int(((1.96 + 0.84) * sd / m) ** 2) + 1) if m > 0 and sd > 0 else None
    if n < min_trades:
        extra = ""
        if out["n_needed_live"] and out["n_needed_live"] > min_trades:
            extra = (f" The record so far implies {out['n_needed_live']} are needed, "
                     f"MORE than the backtest's {min_trades} -- use the larger.")
        out["why"] = (f"{n} settled trades, need {min_trades} for 80% power "
                      f"(sd/mean on this rule is ~10:1). NOT ENOUGH DATA.{extra}")
        return out
    if out["n_needed_live"] and n < out["n_needed_live"]:
        out["why"] = (f"{n} settled, past the backtest floor of {min_trades}, but the "
                      f"LIVE sd/mean implies {out['n_needed_live']} are needed. NOT ENOUGH DATA.")
        return out
    # The pre-registered split, reported always, gating nothing. It is here so
    # the condition can be READ at the end rather than searched for.
    on = [r["ret_after_costs"] for r in settled_rows if r.get("btc_up") is True]
    off = [r["ret_after_costs"] for r in settled_rows if r.get("btc_up") is False]
    out["btc_up_n"], out["btc_down_n"] = len(on), len(off)
    out["btc_up_mean"] = round(statistics.fmean(on), 6) if len(on) >= 20 else None
    out["btc_down_mean"] = round(statistics.fmean(off), 6) if len(off) >= 20 else None

    if out["ci_low"] > 0 and out["ci_seed_stable"]:
        out["clears"] = True
        out["why"] = f"mean {m*100:+.2f}% after costs, 95% bootstrap CI excludes zero (stable across seeds)"
    elif out["ci_low"] > 0:
        out["why"] = "the bootstrap CI excludes zero on one seed and not another -- not yet"
    else:
        out["why"] = f"mean {m*100:+.2f}%, 95% CI [{out['ci_low']*100:+.2f}%, {out['ci_high']*100:+.2f}%] includes zero"
    return out


# --------------------------------------------------------------- quotes
OKX_INSTR = "https://www.okx.com/api/v5/public/instruments?instType=SPOT"
OKX_TICK = "https://www.okx.com/api/v5/market/tickers?instType=SPOT"
OKX_CANDLE = "https://www.okx.com/api/v5/market/candles?instId={i}&bar=1D&limit={n}"
STABLE = {"USDC", "USDT", "USDG", "DAI", "TUSD", "FDUSD", "PYUSD", "USDP",
          "EURT", "XAUT", "PAXG", "BUSD"}
MIN_COVERAGE = 0.80        # see fetch_quotes()


def _get(url: str, timeout: float = 20.0) -> Any:
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "covenant-breakout/1"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read(1 << 21).decode("utf-8", "replace"),
                          parse_constant=_reject)


def watchlist(n: int = 200) -> List[str]:
    """The n most liquid OKX spot USDT pairs, stablecoins removed.

    Breadth is the ONLY lever that makes this rule answerable in a human
    timespan: 863 trades at ~7 per asset per year is 123 years on one asset,
    12.5 on a ten-asset book, and about seven months on two hundred. A forward
    record needs 100 bars of warm-up and nothing else, so the list does not
    have to be assets with long history and does not have to be assets you own.
    """
    live = {i["instId"] for i in _get(OKX_INSTR).get("data", [])
            if i.get("state") == "live" and i["instId"].endswith("-USDT")}
    vol = {t["instId"]: float(t.get("volCcy24h") or 0)
           for t in _get(OKX_TICK).get("data", []) if t["instId"] in live}
    ranked = sorted(vol, key=lambda k: -vol[k])
    return [i for i in ranked if i.split("-")[0] not in STABLE][:n]


def fetch_quotes(symbols: List[str], pause: float = 0.12) -> List[Dict[str, Any]]:
    """Daily closes for each symbol, forming bar dropped.

    PARTIAL READS ARE REFUSED. If fewer than MIN_COVERAGE of the watchlist
    answers, this raises rather than returning what it got: a cycle that saw
    60% of the universe would open and settle calls on a biased subset and
    record it as if it were the day. The caller writes nothing.
    """
    out, miss = [], 0
    for s in symbols:
        try:
            rows = _get(OKX_CANDLE.format(i=s, n=WINDOW + 2)).get("data") or []
            if len(rows) < WINDOW + 2: miss += 1; continue
            rows = sorted(rows, key=lambda c: int(c[0]))[:-1]   # drop the forming bar
            closes = [float(c[4]) for c in rows]
            out.append({"sym": s.split("-")[0], "closes": closes, "px": closes[-1]})
        except Exception:
            miss += 1
        time.sleep(pause)
    cov = len(out) / max(1, len(symbols))
    if cov < MIN_COVERAGE:
        raise RuntimeError(
            f"only {len(out)}/{len(symbols)} of the watchlist answered "
            f"({cov*100:.0f}% < {MIN_COVERAGE*100:.0f}%). A partial universe is a "
            f"biased universe; not recording this day.")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Forward record for the 100-day breakout rule.")
    ap.add_argument("--record", action="store_true",
                    help="run one cycle: open and settle calls for today")
    ap.add_argument("--watchlist", type=int, default=200,
                    help="how many of the most liquid pairs to watch (default 200)")
    ap.add_argument("--quotes", default="",
                    help="read quotes from a JSON file instead of the network")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if a.record:
        try:
            if a.quotes:
                qs = json.load(open(a.quotes, encoding="utf-8"))
            else:
                syms = watchlist(a.watchlist)
                print(f"watching {len(syms)} pairs; fetching {WINDOW + 2} daily bars each...")
                qs = fetch_quotes(syms)
        except Exception as exc:
            print(f"NOT RECORDED: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 2
        before = summary()
        s = record_cycle(qs)
        print(f"read {len(qs)} assets;  open {before['open']} -> {s['open']};  "
              f"settled {before['settled']} -> {s['settled']}"
              + (f";  {s['stale_settled']} stale-settled to date" if s["stale_settled"] else ""))
        return 0
    if a.verify:
        ok, why = verify(); print(("OK: " if ok else "BROKEN: ") + why); return 0 if ok else 1
    s = summary()
    if a.json: print(json.dumps(s, indent=2, sort_keys=True)); return 0
    print("=" * 70)
    print("BREAKOUT-100 -- calls sealed before the outcome, scored on the MEAN")
    print("=" * 70)
    print(f"  ledger        : {LEDGER}")
    print(f"  settled       : {s['settled']}  (need {s['need']});  open: {s['open']}")
    if s["mean_after_costs"] is not None:
        print(f"  mean/trade    : {s['mean_after_costs']*100:+.3f}% after {COST_BPS} bps")
        print(f"  95% CI (boot) : [{s['ci_low']*100:+.3f}%, {s['ci_high']*100:+.3f}%]")
        print(f"  win rate      : {s['win_rate']*100:.1f}%  <- NOT a verdict. This rule is")
        print(f"                  expected to win about a third of its trades.")
        if s.get("btc_up_mean") is not None or s.get("btc_down_mean") is not None:
            u = f"{s['btc_up_mean']*100:+.2f}%" if s.get("btc_up_mean") is not None else "n/a"
            d = f"{s['btc_down_mean']*100:+.2f}%" if s.get("btc_down_mean") is not None else "n/a"
            print(f"  pre-registered: BTC above its 100d  {u} (n={s['btc_up_n']})   "
                  f"below  {d} (n={s['btc_down_n']})")
    print(f"  CLEARS        : {'yes' if s['clears'] else 'no'} -- {s['why']}")
    print("=" * 70)
    print("  Records only. Places nothing, sizes nothing, holds no key, and does")
    print("  not touch the trader's Rule 5 counter.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
