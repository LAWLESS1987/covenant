#!/usr/bin/env python3
"""
signal_ledger.py -- the writer Rule 5 never had.

THE HOLE THIS FILLS (found 2026-09-06)
  covenant_trader.py blocks every live order until `sealed_signals` reaches
  min_sealed_signals (30). It reads that counter, initialises it to 0, and
  NOTHING in the repository ever increments it. signal_watch.py, which
  MY_STRATEGY.md names as the scorer, was never scheduled and never wrote a
  record. So Rule 5 was a gate with no key: it could not clear on evidence,
  only by someone lowering the number.

WHAT A SIGNAL IS HERE
  The trader's one timing rule is the 200-day line: each asset is UP or DOWN
  against it, and the rule acts only when that FLIPS. Every daily cycle already
  seals the per-asset regime to the chain before the outcome exists. This file
  turns those sealed calls into a scored record, the same way signal_watch.py
  does for its SMA cross:

    * the first time an asset is seen, its regime is recorded as an OPEN call
      (sealed_at, entry price, regime);
    * while the regime holds, nothing happens -- it is one call, not one per day
      (a book of correlated assets re-read daily is not thirty trials);
    * when the regime FLIPS, the open call is SETTLED at the flip price:
      side = +1 for UP, -1 for DOWN, ret = side * move - round-trip costs,
      and a new open call begins with the new regime.

  A settled call is one signal. Thirty of them is the Rule 5 count. The
  VERDICT is the same test signal_watch.py applies: mean return after costs
  must be positive AND the win run must be rarer than 1-in-20 under a no-edge
  coin flip (p <= 0.05). Count alone is not evidence, so the trader's gate
  checks both (rule5_require_significance, default true).

WHY IT IS SLOW, AND WHY THAT IS RIGHT
  200-day regimes flip a few times a year per asset. Across the book that is
  perhaps 30 settled calls in several months. That is the honest cadence of
  the rule the trader actually uses. A faster counter would have to come from
  a different signal (hourly SMA crosses), and scoring THAT would say nothing
  about THIS.

  No backfill. A call sealed after its outcome is known is not a prediction.
  The chain holds the trader's earlier sealed cycles, but the ledger starts
  counting from the first cycle that runs with this file present.

WHERE IT LIVES
  ~/.covenant/regime_signals.jsonl (next to trader_state.json, outside the
  synced folder). Rows carry symbol, regime, prices and returns -- no
  quantities, no dollar values, no credentials.

USAGE
  python signal_ledger.py            # print the track record and the verdict
  (covenant_trader.py calls record_cycle() every cycle; nothing else needed)
LICENCE: public domain.
"""
from __future__ import annotations

import json
import math
import os
import statistics
import time

HOME = os.path.expanduser("~")
LEDGER = os.environ.get("COVENANT_SIGNAL_LEDGER") or os.path.join(
    HOME, ".covenant", "regime_signals.jsonl")

# Round-trip cost charged against every settled call: the maker fee both ways
# at Advanced Trade's entry tier (60 bps), plus spread and slippage.
# Pessimistic on purpose: a signal that only works before costs is not a
# signal.
COST_BPS = 60 * 2 + 10

MIN_SIGNALS = 30
MAX_P = 0.05


def _read(path=LEDGER):
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue      # a torn line is skipped, never guessed at
    return rows


def _append(row, path=LEDGER):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")


def _open_calls(rows):
    """Latest OPEN row per symbol (a row is open until a 'settled' row with the
    same open_id follows it)."""
    settled_ids = {r["open_id"] for r in rows if r.get("kind") == "settled"}
    out = {}
    for r in rows:
        if r.get("kind") == "open" and r["open_id"] not in settled_ids:
            out[r["sym"]] = r
    return out


def _day(ts):
    # LOCAL date, like roll_day() and the 09:00 local scheduled task. A UTC
    # date would split one local trading day in two after 20:00 Eastern.
    return time.strftime("%Y-%m-%d", time.localtime(ts))


def record_cycle(positions, now=None, path=LEDGER, cost_bps=COST_BPS,
                 min_signals=MIN_SIGNALS):
    """Feed one cycle's positions (dicts with sym, px, regime, and optionally
    s200). Opens calls for new symbols, settles calls whose regime flipped.
    Returns the summary() after recording."""
    now = int(now if now is not None else time.time())
    rows = _read(path)
    # ONE READ PER LOCAL DAY. The rule is a 200-day line against a DAILY close,
    # and TRADER_TASK.bat runs once for that reason. An operator or a test
    # re-running the trader within the day would otherwise turn intraday
    # noise around the line into "flips" (measured 2026-09-06: three same-day
    # re-runs settled one asset at -1.9%, which is the round-trip cost and
    # nothing else). Every cycle that is admitted as the day's read leaves a
    # marker row; a first version keyed on open/settled rows instead, which
    # exist only when something CHANGED, so on an ordinary flat day the guard
    # never armed (pre-push audit, 2026-09-06). Later runs on the same day
    # read the ledger and write nothing.
    day = _day(now)
    if any(r.get("kind") == "read" and r.get("day") == day for r in rows):
        return summary(path, min_signals=min_signals)
    if not positions:
        # A cycle that read nothing (venue down, no credential) has not read
        # the day. Do not claim it; a later corrected run may.
        return summary(path, min_signals=min_signals)
    _append({"kind": "read", "day": day, "at": now, "n": len(positions)}, path)
    open_calls = _open_calls(rows)
    for p in positions:
        sym, px, regime = p.get("sym"), p.get("px"), p.get("regime")
        if not sym or not px or regime not in ("UP", "DOWN"):
            continue                       # n/a regimes (too few bars) are not calls
        cur = open_calls.get(sym)
        if cur is None:
            _append({"kind": "open", "open_id": f"{sym}:{now}", "sym": sym,
                     "regime": regime, "entry": float(px), "s200": p.get("s200"),
                     "sealed_at": now}, path)
            continue
        if cur["regime"] == regime:
            continue                       # the call stands; nothing to score yet
        side = 1 if cur["regime"] == "UP" else -1
        entry = float(cur["entry"])
        gross = side * (float(px) - entry) / entry if entry else 0.0
        ret = gross - cost_bps / 10_000.0
        _append({"kind": "settled", "open_id": cur["open_id"], "sym": sym,
                 "regime": cur["regime"], "entry": entry, "exit": float(px),
                 "sealed_at": cur["sealed_at"], "settled_at": now,
                 "held_days": round((now - cur["sealed_at"]) / 86400, 1),
                 "side": side, "ret_gross": round(gross, 6),
                 "ret_after_costs": round(ret, 6)}, path)
        _append({"kind": "open", "open_id": f"{sym}:{now}", "sym": sym,
                 "regime": regime, "entry": float(px), "s200": p.get("s200"),
                 "sealed_at": now}, path)
    return summary(path, min_signals=min_signals)


def summary(path=LEDGER, min_signals=MIN_SIGNALS, max_p=MAX_P):
    rows = _read(path)
    settled = [r for r in rows if r.get("kind") == "settled"]
    open_calls = _open_calls(rows)
    out = {"open": len(open_calls), "settled": len(settled), "wins": 0,
           "mean_after_costs": None, "p_value": None,
           "min_signals": min_signals, "max_p": max_p,
           "clears": False, "why": ""}
    if not settled:
        out["why"] = (f"0 settled signals, need {min_signals}; "
                      f"{len(open_calls)} open calls waiting for a regime flip")
        return out
    rets = [r["ret_after_costs"] for r in settled]
    n = len(rets)
    wins = sum(1 for r in rets if r > 0)
    mean = statistics.fmean(rets)
    # Under the null every call is a coin flip; how often does luck alone
    # produce at least this many wins? Same correction as signal_watch.py and
    # the walk-forward study.
    p_val = sum(math.comb(n, k) for k in range(wins, n + 1)) / (2 ** n)
    out.update({"wins": wins, "mean_after_costs": round(mean, 6),
                "p_value": round(p_val, 4)})
    if n < min_signals:
        out["why"] = (f"{n} settled signals, need {min_signals} "
                      f"({wins}/{n} wins, mean {mean:+.2%} after costs, p={p_val:.3f})")
    elif mean <= 0:
        out["why"] = (f"{n} settled signals but mean return {mean:+.2%} after costs "
                      f"-- on real money this loses")
    elif p_val > max_p:
        out["why"] = (f"{n} settled signals, {wins} wins, p={p_val:.3f} > {max_p} "
                      f"-- not distinguishable from luck")
    else:
        out["clears"] = True
        out["why"] = (f"{n} settled signals, {wins} wins, mean {mean:+.2%} after "
                      f"costs, p={p_val:.3f} -- survives the significance test")
    return out


def main():
    s = summary()
    print("=" * 68)
    print(f"RULE 5 -- 200d regime calls, sealed before outcome, scored on flips")
    print("=" * 68)
    print(f"  ledger        : {LEDGER}")
    print(f"  open calls    : {s['open']}")
    print(f"  settled       : {s['settled']}  (need {s['min_signals']})")
    if s["settled"]:
        print(f"  wins          : {s['wins']}/{s['settled']}")
        print(f"  mean return   : {s['mean_after_costs']:+.3%} per call after "
              f"{COST_BPS} bps round trip")
        print(f"  p-value       : {s['p_value']:.3f}  (need <= {s['max_p']})")
    print(f"  CLEARS        : {'YES' if s['clears'] else 'no'} -- {s['why']}")
    print("=" * 68)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
