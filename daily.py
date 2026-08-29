#!/usr/bin/env python3
"""
daily.py -- your whole strategy in one run.

Reads holdings.txt, fetches live prices, works out where every position sits
against its own 200-day trend, checks your rules, and prints exactly what (if
anything) to do. Optionally pushes the summary to your phone.

It never trades and holds no keys. It tells you; you decide.

  python daily.py
  python daily.py --push YOUR_NTFY_TOPIC
"""
from __future__ import annotations
import os, sys, json, time, argparse, statistics, urllib.request, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
MAX_POSITION_PCT = 0.20      # Rule 1
MIN_CASH_PCT     = 0.10      # Rule 1 -- cash floor
# D4: the journal lives OUTSIDE the synced folder, on purpose. Two reasons,
# both learned the hard way elsewhere in this project:
#   1. `C:\Users\<user>\covenant` leaves the machine (DAILY_CHECK.md section 7).
#      An equity-by-day history of the whole portfolio is not a key, but it is
#      not something to post off the box either -- same reasoning that puts the
#      Kraken read-only credential in `C:\Users\<user>\.kraken`.
#   2. covenant_seal.py hashes every file in the folder and anchors the root to
#      the chain. A state file that changes on every run would invalidate the
#      seal daily and train the operator to ignore a mismatch -- which is the
#      one thing a tamper-evident seal must never do.
STATE_PATH = os.environ.get("COVENANT_DAILY_STATE") or os.path.join(
    os.path.expanduser("~"), ".covenant", "daily_state.json")

# D4 (2026-08-22): guards.py was written, tested by hand, and then called by
# NOTHING. `grep -i guard daily.py` on the shipped file returned zero lines.
# The circuit breakers existed as an idea and never as behaviour.
#
# FAIL CLOSED ON THE IMPORT TOO. If guards.py is missing or broken, we do not
# quietly carry on without circuit breakers -- that is the exact failure the
# module's own header warns about. We record why and block every "may add".
try:
    import guards as _guards
    GUARDS_ERR = None
except Exception as _e:                      # noqa: BLE001 -- reported, not swallowed
    _guards = None
    GUARDS_ERR = f"{type(_e).__name__}: {_e}"

CB = {"XLM":"XLM-USD","SOL":"SOL-USD","XRP":"XRP-USD","ADA":"ADA-USD",
      "HBAR":"HBAR-USD","CRO":"CRO-USD","ONDO":"ONDO-USD","PEPE":"PEPE-USD",
      "WLFI":"WLFI-USD"}

# X1 (2026-08-22): a SECOND, INDEPENDENT venue.
#
# Two reasons, and the second is the important one.
#
# 1. Availability. `DAILY_CHECK_CLOUD_BLOCKER.md` recorded two scheduled runs
#    (08-20, 08-21) that reported no prices at all, and concluded the cloud
#    sandbox cannot reach a price API. Re-measured 2026-08-22 from the sandbox:
#    api.exchange.coinbase.com, api.coinbase.com AND api.kraken.com all answer
#    plain `urllib` with HTTP 200. The blocker was never the network -- it was
#    WebFetch's permission gate, which nobody is present to approve in an
#    unattended run. `daily.py` has always used urllib and would have worked.
#    Keeping two venues means one being unreachable is a degraded run, not a
#    silent one.
#
# 2. Verification, which is what this project keeps learning the hard way. Every
#    check in DAILY_CHECK.md section 3 is INTERNAL to one response: contiguity,
#    duplicates, sign, staleness. A response can pass all four and still be
#    wrong -- the 70-day-stale series of PRICE_DATA_INTEGRITY.md was internally
#    perfect. The only check that catches THAT is a second venue that has no
#    reason to be wrong the same way. Measured today across all nine symbols,
#    the last settled close agrees to <= 0.30% (worst: PEPE 0.292%), while every
#    failure this defends against -- a stale window, a dropped row, the wrong
#    pair -- moves the number by whole percent or more.
KR = {"XLM":"XXLMZUSD","XRP":"XXRPZUSD","SOL":"SOLUSD","ADA":"ADAUSD",
      "HBAR":"HBARUSD","CRO":"CROUSD","ONDO":"ONDOUSD","PEPE":"PEPEUSD",
      "WLFI":"WLFIUSD"}

# "both" = fetch Coinbase, verify against Kraken. "coinbase"/"kraken" = one
# venue only (no cross-check, and the run says so).
SOURCE = os.environ.get("COVENANT_PRICE_SOURCE", "both")
XVENUE_NOTES = []      # single-venue reads, reported rather than hidden
XVENUE_MAXDIV = []     # (sym, divergence) for every symbol that WAS cross-checked
# A disagreement THIS large on the last settled close means at least one read is
# wrong, and there is no way to tell which -- so the symbol is refused rather
# than guessed at. 1.0% is ~3.4x the worst honest divergence measured.
XVENUE_TOL = float(os.environ.get("COVENANT_XVENUE_TOL", "0.01"))

# Assets we hold that Coinbase does NOT trade. Coinbase shows a price PAGE for
# these (that is why they look listed), but there is no market and no candle
# history, so no regime line can be computed. Saying so out loud beats printing
# a silent "n/a" that looks like a bug.
NOT_ON_COINBASE = {
    "CC": "Canton -- Coinbase says 'not tradable on Coinbase'; price page only",
}


def load_holdings(path=os.path.join(HERE, "holdings.txt")):
    out = []
    if not os.path.exists(path):
        sys.exit(f"missing {path}")
    for line in open(path):
        line = line.split("#")[0].strip()
        if not line:
            continue
        p = line.split()
        if len(p) >= 3:
            rec = {"sym": p[0].upper(), "qty": float(p[1]), "avg": float(p[2]),
                   "manual": None}
            # Optional 4th column: a price YOU typed in, for an asset with no
            # Coinbase market. It is used for the total and the 20% cap, and is
            # labelled as hand-entered everywhere it appears -- so it can never
            # be mistaken for a fetched price.
            if len(p) >= 4:
                try: rec["manual"] = float(p[3])
                except ValueError: pass
            out.append(rec)
    return out


def fetch_coinbase(sym):
    """Live price + up to 200 settled daily closes from Coinbase (public, no key).

    Returns (price, closes, why_failed). `why_failed` is None on success and a
    human-readable reason otherwise -- a failed read is REPORTED as failed and
    never silently substituted (DAILY_CHECK.md section 3).
    """
    # S1: same reasoning as _kraken_pair_lookup -- CB is hardcoded to the nine
    # assets held on 2026-08-19, and sync_holdings.py can now add a tenth
    # without anyone opening this file. Coinbase's product ids are plain
    # "{SYM}-USD", so the fallback needs no lookup table; a symbol with no
    # market simply 404s and is reported as a failed read, which is the
    # existing contract. Assets already KNOWN to have no market skip the call.
    prod = CB.get(sym) or (None if sym in NOT_ON_COINBASE else f"{sym}-USD")
    if not prod:
        return None, None, None          # not a Coinbase market at all
    url = f"https://api.exchange.coinbase.com/products/{prod}/candles?granularity=86400"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "covenant-daily/1.0"})
        with urllib.request.urlopen(req, timeout=25) as r:
            rows = json.loads(r.read().decode())
    except Exception as e:
        return None, None, f"fetch failed: {type(e).__name__}"
    if not rows:
        return None, None, "empty candle response"
    rows.sort(key=lambda x: -x[0])              # newest first
    return _verify_and_split(rows)


def _verify_and_split(rows):
    """The DAILY_CHECK.md section 3 checks + the forming-bar rule, applied
    identically to every venue. `rows` is newest-first
    [ts, low, high, open, close, volume]. Returns (price, closes, why_failed)."""
    # D3 (2026-08-22): VERIFY THE WINDOW BEFORE USING IT.
    # DAILY_CHECK.md section 3 lists four checks that must pass before a price
    # series is used -- contiguity at exactly 86400 s, no duplicate timestamps,
    # no non-positive prices, and a newest bar that is today or yesterday, with
    # "if it is older, the read is broken; refetch, and if it fails again say
    # so rather than reporting the numbers". The runbook has said that since
    # 2026-08-20. daily.py implemented NONE of it: it sorted the rows and used
    # them. A 70-day-stale series (PRICE_DATA_INTEGRITY.md) would have printed
    # here as a clean regime call, and the only thing standing between that and
    # a trim suggestion was that nobody had had a bad read yet on this path.
    ts = [int(r[0]) for r in rows]
    if len(set(ts)) != len(ts):
        return None, None, "duplicate timestamps in the candle window"
    if len(ts) >= 2:
        gaps = {ts[i] - ts[i + 1] for i in range(len(ts) - 1)}
        if gaps != {86400}:
            bad = sorted(g for g in gaps if g != 86400)[:4]
            return None, None, f"non-contiguous daily bars (gaps {bad})"
    if any(float(r[4]) <= 0 for r in rows):
        return None, None, "non-positive close in the candle window"
    age_days = (time.time() - ts[0]) / 86400.0
    if age_days > 2.0:
        return None, None, (f"newest bar is {age_days:.1f} days old -- the read "
                            f"is broken, not the market")

    closes = [float(r[4]) for r in rows]

    # TODAY'S BAR IS STILL FORMING. Its close is really "price right now", which
    # is what we want for the live price -- but it must NOT go into the regime
    # average, or the line moves around intraday and the signal flickers. Two
    # independent sources disagreed by 8.9% on an in-progress bar during
    # testing; on settled bars they agreed to 0.00%.
    import time as _t
    newest_is_today = (rows[0][0] // 86400) == (int(_t.time()) // 86400)
    settled = closes[1:] if newest_is_today else closes
    if len(settled) < 30:
        return None, None, f"only {len(settled)} settled bars, need 30"
    return closes[0], settled[:200], None


_KR_PAIRS = None    # lazily built, once per run


def _kraken_pair_lookup(sym):
    """Resolve a symbol Kraken lists but KR does not name. None if unlisted.

    S1 (2026-08-28): KR and CB above are hardcoded to the nine assets held on
    2026-08-19. That was fine while holdings.txt was edited by hand -- you
    could not add a coin without also seeing this file. sync_holdings.py breaks
    that coupling: it can introduce an asset from the exchange without a human
    ever opening daily.py, and the asset would then read NO PRICE despite both
    venues listing it. The hardcoded maps stay as the fast, audited path; this
    is only the fallback, and it fails to None exactly like an unknown symbol.
    """
    global _KR_PAIRS
    if _KR_PAIRS is None:
        _KR_PAIRS = {}
        try:
            req = urllib.request.Request(
                "https://api.kraken.com/0/public/AssetPairs",
                headers={"User-Agent": "covenant-daily/1.0"})
            with urllib.request.urlopen(req, timeout=25) as r:
                res = json.loads(r.read().decode()).get("result", {})
            for name, v in res.items():
                if v.get("quote") not in ("ZUSD", "USD") or v.get("status") != "online":
                    continue
                ws = (v.get("wsname") or "")          # e.g. "XLM/USD"
                base = ws.split("/")[0] if "/" in ws else v.get("base", "")
                if base and (base not in _KR_PAIRS or len(name) < len(_KR_PAIRS[base])):
                    _KR_PAIRS[base] = name
        except Exception:
            _KR_PAIRS = {}
    # Kraken names two majors differently from everyone else, and neither is
    # derivable -- they are historical, so they are listed rather than guessed.
    ALIAS = {"BTC": "XBT", "DOGE": "XDG"}
    s = sym.upper()
    return _KR_PAIRS.get(s) or _KR_PAIRS.get(ALIAS.get(s, s))


def fetch_kraken(sym):
    """Same contract as fetch_coinbase, against Kraken's public OHLC endpoint.

    One call returns up to 720 daily bars with an exact `last`; M24 established
    that this endpoint answers plain urllib byte-exactly, and that every
    row-loss hazard in M1 belonged to the WebFetch summariser, not to Kraken.
    """
    pair = KR.get(sym) or _kraken_pair_lookup(sym)
    if not pair:
        return None, None, None
    url = (f"https://api.kraken.com/0/public/OHLC?pair={pair}&interval=1440"
           f"&since={int(time.time()) - 260 * 86400}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "covenant-daily/1.0"})
        with urllib.request.urlopen(req, timeout=25) as r:
            payload = json.loads(r.read().decode())
    except Exception as e:
        return None, None, f"kraken fetch failed: {type(e).__name__}"
    if payload.get("error"):
        return None, None, f"kraken error {payload['error']}"
    res = payload.get("result") or {}
    series = None
    for k, v in res.items():
        if k != "last" and isinstance(v, list):
            series = v
            break
    if not series:
        return None, None, "kraken returned no series"
    # [time, open, high, low, close, vwap, volume, count] -- close is index 4,
    # the same index as Coinbase's, which is a coincidence worth stating rather
    # than relying on silently.
    rows = [[int(a[0]), float(a[3]), float(a[2]), float(a[1]), float(a[4]),
             float(a[6])] for a in series]
    rows.sort(key=lambda x: -x[0])
    return _verify_and_split(rows)


def prefetch(syms, source=None):
    """Fetch every symbol concurrently. Returns {sym: (px, closes, why, notes)}.

    E1 (2026-08-28): the run was doing two serial HTTPS round trips per holding
    -- ~20 calls, 6.0 s measured -- while waiting on the network for essentially
    all of it. Ten symbols is small enough that the whole thing fits in one
    wave.

    Two things this must NOT break, both of which rule out simply threading the
    existing loop:

      * Determinism. fetch() appends to the XVENUE_NOTES global, and threads
        would interleave those appends in completion order, so the same
        portfolio could print its warnings in a different order each run. A
        report that reshuffles itself trains you to skim it. Each worker gets
        its OWN notes list here, and the caller splices them back in holdings
        order, so the output is byte-identical to the serial version.
      * Duplicated lookups. _KR_PAIRS is a lazily-built global; N threads
        racing on it would each fetch AssetPairs. It is warmed once, before
        the pool starts, and is read-only thereafter.
    """
    from concurrent.futures import ThreadPoolExecutor

    syms = [s for s in syms if s != "CASH"]
    if any(s not in KR for s in syms):
        _kraken_pair_lookup(syms[0] if syms else "BTC")     # warm _KR_PAIRS once

    def one(sym):
        notes, divs = [], []
        px, closes, why = fetch(sym, source, notes=notes, divs=divs)
        return sym, (px, closes, why, notes, divs)

    if not syms:
        return {}
    with ThreadPoolExecutor(max_workers=min(8, len(syms))) as pool:
        return dict(pool.map(one, syms))


def fetch(sym, source=None, notes=None, divs=None):
    """Dispatcher + cross-venue verification.

    Returns (price, closes, why_failed). With source="both" the Coinbase read
    is the one used and Kraken is the CHECK: if the two disagree by more than
    XVENUE_TOL on the same settled bar, the symbol is refused -- there is no
    way to know which venue is wrong, and a wrong price does not just misprice
    one line, it mis-sizes the 20% trim on every OTHER holding.
    """
    source = (source or SOURCE).lower()
    # E1: when prefetch() runs us on a worker thread it hands in its own
    # containers, so concurrent symbols never interleave into the globals.
    # Called directly (source=None), we fall back to them and behave exactly
    # as before -- fetch() is still usable on its own.
    _notes = XVENUE_NOTES if notes is None else notes
    _divs = XVENUE_MAXDIV if divs is None else divs
    if source == "coinbase":
        return fetch_coinbase(sym)
    if source == "kraken":
        return fetch_kraken(sym)

    px, closes, why = fetch_coinbase(sym)
    if px is None:
        # Primary failed. Fall back to the secondary rather than dropping the
        # holding -- but say which venue the number came from.
        kpx, kcloses, kwhy = fetch_kraken(sym)
        if kpx is None:
            return None, None, why or kwhy
        _notes.append(f"{sym}: Coinbase unavailable ({why or 'no Coinbase market'}); priced on Kraken alone")
        return kpx, kcloses, None

    kpx, kcloses, kwhy = fetch_kraken(sym)
    if kpx is None:
        _notes.append(f"{sym}: no Kraken cross-check ({kwhy or 'not listed'}) "
                            f"-- single-venue read")
        return px, closes, None

    # closes[0] is the last SETTLED close on each side (the forming bar is
    # already dropped by _verify_and_split), and both were verified contiguous
    # to today, so they are the same calendar bar.
    a, b = closes[0], kcloses[0]
    div = abs(b / a - 1.0) if a else 1.0
    if div > XVENUE_TOL:
        return None, None, (f"venues disagree on the last settled close by "
                            f"{div * 100:.2f}% (Coinbase {a:.8g}, Kraken {b:.8g}, "
                            f"tolerance {XVENUE_TOL * 100:.2f}%) -- one read is "
                            f"wrong and there is no way to tell which")
    _divs.append((sym, div))
    return px, closes, None


def push(topic, msg):
    if not topic:
        return
    try:
        url = f"https://ntfy.sh/{topic}/publish?title=Daily+check&message=" + \
              urllib.parse.quote_plus(msg[:400])
        urllib.request.urlopen(url, timeout=20).read()
        print("  (pushed to phone)")
    except Exception as e:
        print(f"  (push failed: {e})")


def load_state():
    """D4: the guards' memory. Without it MaxDrawdown has no peak and
    DailyLossLimit has no opening equity, so both fail closed for ever and the
    whole stack is decoration. This file is the only thing that makes them real."""
    try:
        with open(STATE_PATH) as f:
            st = json.load(f)
    except Exception:
        st = {}
    st.setdefault("equity", [])       # [[unix_ts, total_value], ...] oldest first
    st.setdefault("last_sold", {})    # {SYM: unix_ts}
    st.setdefault("closed_trades", [])# [{sym, pnl, closed_at}]
    return st


def save_state(st):
    st["equity"] = st["equity"][-400:]          # ~13 months of daily runs
    st["closed_trades"] = st["closed_trades"][-200:]
    os.makedirs(os.path.dirname(STATE_PATH) or ".", exist_ok=True)
    tmp = STATE_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(st, f, indent=1)
    os.replace(tmp, STATE_PATH)                 # never a half-written state file


def guard_state(st, total, cash, positions, now=None):
    """Build guards.State from the journal. Returns (State, note) where note
    explains any value the history could not supply -- so a guard that blocks
    for want of data says so instead of looking like a market judgement."""
    now = now if now is not None else time.time()
    hist = [(float(t), float(v)) for t, v in st.get("equity", []) if v and v > 0]
    peak = max([v for _, v in hist] + [total])
    notes = []

    # Start-of-day: the first reading recorded today. Falling back to the most
    # recent earlier reading is honest (it is a real measurement of where the
    # account was), but only while it is fresh; past 48h it says nothing about
    # today and DailyLossLimit should block rather than pretend.
    day = time.strftime("%Y-%m-%d", time.localtime(now))
    today = [v for t, v in hist if time.strftime("%Y-%m-%d", time.localtime(t)) == day]
    if today:
        sod = today[0]
    elif hist and now - hist[-1][0] <= 48 * 3600:
        sod = hist[-1][1]
        notes.append("start-of-day taken from the last run (<48h old)")
    else:
        sod = 0.0                     # guards.DailyLossLimit blocks on <= 0
        notes.append("no equity reading inside 48h -- daily-loss guard cannot evaluate")
    if not hist:
        notes.append("first run: no history, so drawdown is measured against today")
    if not st.get("closed_trades"):
        notes.append("no closed trades recorded -- the loss-streak guard can only "
                     "ever say ok until sells are logged with --sold")
    return _guards.State(
        equity_now=total, equity_peak=peak, equity_start_of_day=sod,
        closed_trades=list(st.get("closed_trades", [])),
        last_sold={k: float(v) for k, v in st.get("last_sold", {}).items()},
        positions=dict(positions), cash=cash, now=now), notes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--push", default="", help="ntfy topic for a phone summary")
    ap.add_argument("--sold", default="", metavar="SYM",
                    help="record that you sold SYM today (feeds the cooldown guard)")
    ap.add_argument("--pnl", type=float, default=None,
                    help="with --sold: the realised P/L, for the loss-streak guard")
    ap.add_argument("--no-state", action="store_true",
                    help="do not read or write daily_state.json (dry run)")
    ap.add_argument("--source", default=SOURCE, choices=["both", "coinbase", "kraken"],
                    help="price venue(s). both = Coinbase verified against Kraken")
    args = ap.parse_args()

    state = ({"equity": [], "last_sold": {}, "closed_trades": []}
             if args.no_state else load_state())
    if args.sold:
        sym = args.sold.upper()
        state["last_sold"][sym] = time.time()
        if args.pnl is not None:
            state["closed_trades"].append({"sym": sym, "pnl": float(args.pnl),
                                           "closed_at": time.time()})
        print(f"recorded: sold {sym}" + (f" (P/L {args.pnl:+.2f})" if args.pnl is not None else ""))

    globals()["SOURCE"] = args.source
    XVENUE_NOTES.clear(); XVENUE_MAXDIV.clear()
    hold = load_holdings()
    print("=" * 74)
    print(f"DAILY CHECK   {time.strftime('%Y-%m-%d %H:%M')}")
    print("=" * 74)
    print(f"fetching live prices  [source: {args.source}"
          + ("  -- Coinbase, verified against Kraken]" if args.source == "both"
             else "  -- SINGLE VENUE, no cross-check]"))

    # E1: one concurrent wave for every symbol, then the loop below is pure
    # arithmetic. The notes each worker collected are spliced back in HOLDINGS
    # order, not completion order, so this prints exactly what the serial
    # version printed.
    prefetched = prefetch([h["sym"] for h in hold], args.source)

    rows, total, unpriced = [], 0.0, []
    for h in hold:
        if h["sym"] == "CASH":
            val = h["qty"]
            rows.append({**h, "px": 1.0, "val": val, "regime": "cash", "s200": None})
            total += val
            continue
        px, closes, why_failed, _n, _d = prefetched.get(
            h["sym"], (None, None, "not fetched", [], []))
        XVENUE_NOTES.extend(_n)
        XVENUE_MAXDIV.extend(_d)

        # S1b (2026-08-28): a hand-entered price OUTRANKS a fetched one, and the
        # dynamic symbol fallback above is exactly why this guard is needed.
        # Before it, column 4 was only ever consulted when no venue answered.
        # Now a venue can answer for a symbol that previously had no market --
        # and CC is a three-character ticker that more than one asset can own.
        # Silently swapping the operator's own number for a fetched one on a
        # ticker match alone is how you value the wrong asset without a warning.
        # So: keep the hand-entered price, and REPORT the venue's, which turns a
        # possible collision into something visible instead of something assumed.
        if h.get("manual") is not None and px is not None:
            gap = (px - h["manual"]) / h["manual"] if h["manual"] else 0.0
            XVENUE_NOTES.append(
                f"{h['sym']}: a venue now quotes {px:.6f}, your hand-entered price "
                f"is {h['manual']:.6f} ({gap:+.1%}). Using YOURS. If they are the "
                f"same asset, drop column 4 in holdings.txt to price it live.")
            px, closes = None, None

        if px is None:
            # DO NOT substitute the average buy price. That invents a number,
            # inflates the position's value, prints a flat 0% P/L that looks
            # like the truth, and -- worst -- feeds a wrong TOTAL into the 20%
            # cap, which then mis-sizes the trims on every OTHER holding.
            # Park it, price it by hand, keep it out of the rule maths.
            why = NOT_ON_COINBASE.get(h["sym"]) or why_failed or "no Coinbase market"
            if h.get("manual"):
                px = h["manual"]
                val = h["qty"] * px
                print(f"  {h['sym']:<6} hand-entered price {px:.6f} ({why})")
                rows.append({**h, "px": px, "val": val, "s200": None,
                             "regime": "manual"})
                total += val
                continue
            print(f"  {h['sym']:<6} NO PRICE - {why}")
            print(f"         add a 4th column to holdings.txt to price it by hand")
            unpriced.append({**h, "why": why})
            continue
        val = h["qty"] * px
        s200 = statistics.fmean(closes) if closes and len(closes) >= 50 else None
        regime = "n/a" if s200 is None else ("UP" if px > s200 else "DOWN")
        # D3: the column is headed "200d". Say when it is not 200 days.
        rows.append({**h, "px": px, "val": val, "s200": s200, "regime": regime,
                     "bars": len(closes) if closes else 0})
        total += val
        # E1: the 0.2 s courtesy sleep that used to sit here is gone. It paced
        # the two HTTP calls this loop USED to make per holding; prefetch() now
        # makes them all before the loop starts, so by this line there is
        # nothing left to pace and the delay was purely additive -- 1.80 s of a
        # 3.4 s run, measured. Rate limiting still exists, as the bounded
        # worker pool in prefetch().

    rows.sort(key=lambda r: -r["val"])
    cash = sum(r["val"] for r in rows if r["sym"] == "CASH")

    print()
    print(f"  {'asset':<7}{'value':>10}{'%':>7}{'price':>11}{'200d':>11}{'regime':>8}{'P/L':>9}")
    print("  " + "-" * 64)
    for r in rows:
        if r["sym"] == "CASH":
            continue
        pl = (r["px"] / r["avg"] - 1) if r["avg"] else 0
        s2 = f"{r['s200']:.4f}" if r["s200"] else ("manual" if r["regime"]=="manual" else "n/a")
        print(f"  {r['sym']:<7}{r['val']:>10,.2f}{r['val']/total:>6.1%}{r['px']:>11.5f}"
              f"{s2:>11}{r['regime']:>8}{pl:>8.1%}")
    print("  " + "-" * 64)
    print(f"  {'TOTAL':<7}{total:>10,.2f}{1:>6.0%}      cash {cash:,.2f} ({cash/total:.1%})")
    if XVENUE_MAXDIV:
        worst = max(XVENUE_MAXDIV, key=lambda x: x[1])
        print(f"  cross-venue: {len(XVENUE_MAXDIV)} symbol(s) agreed with Kraken on the "
              f"last settled close; worst {worst[0]} {worst[1] * 100:.3f}% "
              f"(tolerance {XVENUE_TOL * 100:.2f}%)")
    for n in XVENUE_NOTES:
        print(f"  ! {n}")
    short = [(r["sym"], r["bars"]) for r in rows
             if r.get("s200") and r.get("bars", 0) < 200]
    if short:
        # D3: the header says 200d. Where it is not, say the real number rather
        # than letting a 60-bar mean be read as a 200-day trend.
        print("  NOTE the '200d' column is a mean of fewer than 200 bars for: "
              + ", ".join(f"{s_}({n})" for s_, n in short))
    if unpriced:
        print()
        print("  HELD BUT NOT PRICED HERE (excluded from the total and from every")
        print("  rule below, because a guessed price would mis-size the trims):")
        for u in unpriced:
            print(f"    {u['sym']:<6} {u['qty']:>14,.4f} units   {u['why']}")
        print("    -> read the price in the app you actually hold it in, and")
        print("       judge that position separately.")

    # ---- rules ----
    actions = []
    for r in rows:
        if r["sym"] == "CASH":
            continue
        pct = r["val"] / total
        if pct > MAX_POSITION_PCT:
            over = r["val"] - MAX_POSITION_PCT * total
            units = over / r["px"]
            actions.append(f"TRIM {r['sym']}: {pct:.1%} of portfolio (limit {MAX_POSITION_PCT:.0%}). "
                           f"Sell ~{units:,.2f} {r['sym']} = ${over:,.0f}")
    if cash / total < MIN_CASH_PCT:
        need = MIN_CASH_PCT * total - cash
        actions.append(f"CASH: you hold {cash/total:.1%}, floor is {MIN_CASH_PCT:.0%}. "
                       f"Build ~${need:,.0f} (the trims above cover it)")

    print()
    print("  RULE CHECK")
    print("  " + "-" * 64)
    if actions:
        for a in actions:
            print(f"  * {a}")
    else:
        print("  * all rules satisfied - no action needed today")

    # ---- D4: circuit breakers -------------------------------------------
    # Rule 2 says an asset above its line "may hold and add". THAT is the
    # sentence the guards gate. They never block a trim and never suggest a
    # sale: a breaker that liquidates at the bottom is worse than the loss it
    # was stopping (guards.py's own design rule).
    positions = {r["sym"]: r["val"] for r in rows if r["sym"] != "CASH"}
    blocked_syms, guard_lines = [], []
    if _guards is None:
        guard_lines.append(f"  * guards.py did NOT load ({GUARDS_ERR}) -- failing "
                           f"closed: treat every 'may add' below as BLOCKED.")
        blocked_syms = [r["sym"] for r in rows if r.get("regime") == "UP"]
    else:
        gstate, notes = guard_state(state, total, cash, positions)
        stack = _guards.GuardStack()
        for n in notes:
            guard_lines.append(f"  ! {n}")
        portfolio = [v for v in stack.evaluate(gstate) if v.guard in
                     ("max_drawdown", "daily_loss", "loss_streak", "cash_floor")]
        for v in portfolio:
            guard_lines.append(f"  [{'ok   ' if v.allowed else 'BLOCK'}] "
                               f"{v.guard:<14} {v.reason}")
        for r in rows:
            if r["sym"] == "CASH" or r.get("regime") != "UP":
                continue
            ok, blocks, _ = stack.may_buy(gstate, r["sym"])
            if not ok:
                blocked_syms.append(r["sym"])
                # The portfolio-level reasons are already on screen above; a
                # per-asset line repeating them five times reads as five
                # separate problems. Show what is specific to THIS asset, and
                # name the rest by reference.
                own = [b for b in blocks if b.guard in ("cooldown", "concentration")]
                shared = [b for b in blocks if b not in own]
                why = "; ".join(b.reason for b in own)
                if shared:
                    why = (why + "; " if why else "") + \
                          "blocked by the portfolio guards above (" + \
                          ", ".join(b.guard for b in shared) + ")"
                guard_lines.append(f"  [BLOCK] {r['sym']:<14} {why}")

    print()
    print("  CIRCUIT BREAKERS (they gate 'may add' only -- never a sale)")
    print("  " + "-" * 64)
    for line in guard_lines:
        print(line)
    if not guard_lines:
        print("  every guard clear")

    downs = [r["sym"] for r in rows if r.get("regime") == "DOWN"]
    ups = [r["sym"] for r in rows if r.get("regime") == "UP"]
    ups_open = [u for u in ups if u not in blocked_syms]
    print()
    print(f"  regime UP   (above 200d): {', '.join(ups) if ups else 'none'}")
    print(f"  regime DOWN (below 200d): {', '.join(downs) if downs else 'none'}")
    if downs:
        print(f"    -> Rule 4: do NOT add to {', '.join(downs)} while below the 200d line.")
    if ups:
        print(f"    -> of those above the line, adding is permitted by the guards "
              f"only for: {', '.join(ups_open) if ups_open else 'NONE'}")

    print()
    print("  Nothing has been traded. You place any order yourself in Kraken.")
    print("=" * 74)

    if not args.no_state:
        state["equity"].append([time.time(), total])
        save_state(state)

    if args.push:
        n = len(actions)
        blocked_note = f" Guards block adds: {','.join(blocked_syms)}." if blocked_syms else ""
        msg = (f"Portfolio ${total:,.0f}, cash {cash/total:.0%}.{blocked_note} "
               + (f"{n} action(s): " + " | ".join(a.split(':')[0] for a in actions)
                  if actions else "No action needed.")
               + f" Down-regime: {','.join(downs) if downs else 'none'}")
        push(args.push, msg)


if __name__ == "__main__":
    main()
