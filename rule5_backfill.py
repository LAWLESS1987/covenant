#!/usr/bin/env python3
"""
rule5_backfill.py -- what the 200-day rule DID, replayed over verified history.

ASKED 2026-09-10: "expedite with historical data, september 15th is the absolute
cut off to begin."

WHAT THIS IS
  Rule 5 needs 30 settled 200-day regime calls with a positive mean after costs
  and p <= 0.05. Live, that takes months: a 200d regime flips a few times a year
  per asset, and the live ledger currently holds ONE settled call. History
  already contains hundreds of those flips. This replays them.

  It walks realdata/deep/ forward one day at a time and feeds each day's
  regimes through signal_ledger.record_cycle -- THE SAME FUNCTION the live
  trader uses -- into a separate ledger file, then scores it with
  signal_ledger.summary, THE SAME SCORER. Same 200d definition, same
  side/entry/exit arithmetic, same 130 bps round trip, same binomial test.

  That is deliberate. This project's recurring defect is two code paths to one
  answer, where one of them is not enforcing the rule. A second implementation
  of the scoring here could produce a number that disagrees with the gate and
  nobody would know which was right.

WHAT THIS IS NOT, AND THE DISTINCTION IS THE WHOLE POINT
  A Rule 5 signal is SEALED BEFORE THE OUTCOME EXISTS. That is what makes the
  count evidence about this system's discipline rather than about a dataset.
  Every row this file produces is settled from prices that were already known
  when it ran. It is a BACKTEST of the same rule.

  So it will not write to the live ledger, and refuses if pointed at it. It
  cannot raise `sealed_signals`, and nothing here should be read as clearing
  Rule 5. What it CAN do -- today, rather than in months -- is answer the
  question underneath the gate: has this rule, on this book, actually made
  money after costs?

  Read the answer against the standing validation result: 2 hypothesis classes,
  ~1088 variants, nothing cleared walk-forward, deflation or PBO, with PBO
  0.986 on a cash-filtered variant. A positive number here is not proof of an
  edge; a negative number IS informative, because the rule failing on its own
  history is not a sampling artefact.

DATA
  realdata/deep/ only -- twelve Kraken daily series verified for 86,400s
  contiguity, no duplicate timestamps, OHLC sanity and 00:00 UTC alignment,
  with interior windows re-fetched and diffed byte for byte. The three
  shorter overlapping files (SOL/XLM/XRP *_2026Jan) are EXCLUDED by name: they
  are subsets of the canonical series and including them would count the same
  flips twice.

USE
  python rule5_backfill.py                 replay and score
  python rule5_backfill.py --per-asset     add the per-asset breakdown
LICENCE: public domain.
"""
from __future__ import annotations

import csv
import io
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import signal_ledger as SL  # noqa: E402

DEEP = os.path.join(HERE, "realdata", "deep")
OUT = os.path.join(HERE, "ops", "rule5_backfill_ledger.jsonl")

# The canonical twelve named in realdata/README.md. The *_2026Jan files are
# shorter windows of series already here; counting both double-counts flips.
CANONICAL = [
    "ADA_2025_2026Aug.csv", "ATOM_2025_2026Aug.csv", "AVAX_2025_2026Aug.csv",
    "CRO_2025_2026Aug.csv", "HBAR_2025Jul_2026Aug.csv", "NEAR_2025_2026Aug.csv",
    "ONDO_2025_2026Aug.csv", "PEPE_2025_2026Aug.csv", "SOL_2025_2026Aug.csv",
    "WLFI_2025Sep_2026Aug.csv", "XLM_2025_2026Aug.csv", "XRP_2025_2026Aug.csv",
]

WARMUP = 200          # daily.py calls it the 200d line; so does this


def load(fname):
    """-> [(timestamp, close)] ascending. Rows with no usable close are dropped
    and COUNTED, never silently skipped."""
    path = os.path.join(DEEP, fname)
    rows, bad = [], 0
    with io.open(path, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            try:
                rows.append((int(r["timestamp"]), float(r["close"])))
            except (TypeError, ValueError, KeyError):
                bad += 1
    rows.sort()
    return rows, bad


def main():
    if os.path.abspath(OUT) == os.path.abspath(SL.LEDGER):
        print("REFUSING: the backfill ledger is the live ledger. A signal "
              "settled from known prices is not a sealed signal.")
        return 2

    series, dropped = {}, 0
    for f in CANONICAL:
        if not os.path.exists(os.path.join(DEEP, f)):
            print("MISSING: %s -- reported, not skipped" % f)
            return 2
        sym = f.split("_")[0]
        series[sym], bad = load(f)
        dropped += bad

    # A fresh ledger each run: appending would score the same history twice.
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    if os.path.exists(OUT):
        os.remove(OUT)

    all_days = sorted({ts for rows in series.values() for ts, _ in rows})
    idx = {sym: {ts: px for ts, px in rows} for sym, rows in series.items()}
    hist = {sym: [] for sym in series}

    cycles = 0
    for ts in all_days:
        positions = []
        for sym, rows in series.items():
            px = idx[sym].get(ts)
            if px is None:
                continue
            h = hist[sym]
            if len(h) >= WARMUP:
                s200 = statistics.fmean(h[-WARMUP:])
                positions.append({"sym": sym, "px": px, "s200": s200,
                                  "regime": "UP" if px > s200 else "DOWN"})
            h.append(px)
        if positions:
            SL.record_cycle(positions, now=float(ts), path=OUT)
            cycles += 1

    s = SL.summary(path=OUT)
    span = "%s -> %s" % (SL._day(all_days[0]), SL._day(all_days[-1]))

    print("=" * 72)
    print("RULE 5 REPLAYED OVER HISTORY -- a BACKTEST, not sealed evidence")
    print("=" * 72)
    print("  assets        : %d   %s" % (len(series), ", ".join(sorted(series))))
    print("  window        : %s   (%d trading days)" % (span, len(all_days)))
    print("  warmup        : %d bars before an asset can have a regime" % WARMUP)
    print("  cycles fed    : %d" % cycles)
    if dropped:
        print("  unusable rows : %d (dropped, and counted rather than ignored)"
              % dropped)
    print("  ledger        : %s" % OUT)
    print("  " + "-" * 68)
    print("  settled calls : %d   (Rule 5 wants %d)" % (s["settled"], s["min_signals"]))
    print("  still open    : %d" % s["open"])
    if s["settled"]:
        print("  wins          : %d/%d" % (s["wins"], s["settled"]))
        print("  mean return   : %+.3f%% per call after %d bps round trip"
              % (s["mean_after_costs"] * 100, SL.COST_BPS))
        print("  p-value       : %.4f  (needs <= %s)" % (s["p_value"], s["max_p"]))
    print("  VERDICT       : %s" % s["why"])
    print("  " + "-" * 68)
    print("  This CANNOT clear Rule 5 and does not touch the live ledger. Every")
    print("  call above was settled from prices already known when it ran; a")
    print("  sealed signal is one recorded before the outcome exists. What it")
    print("  answers is the question underneath the gate: did this rule, on")
    print("  this book, make money after costs?")
    print("=" * 72)

    if "--per-asset" in sys.argv[1:]:
        rows = SL._read(OUT)
        per = {}
        for r in rows:
            if r.get("kind") != "settled":
                continue
            per.setdefault(r["sym"], []).append(r["ret_after_costs"])
        print("\n  per asset:")
        for sym in sorted(per):
            v = per[sym]
            print("    %-6s n=%-3d wins=%-3d mean=%+.2f%%"
                  % (sym, len(v), sum(1 for x in v if x > 0),
                     statistics.fmean(v) * 100))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
