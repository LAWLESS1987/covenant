# Live-trading readiness — what is true, what is not, and what the loop may not do (2026-08-22)

**Ask from L:** "work towards preparing for live trades."

**The boundary first (Section 0, immutable):** this loop never places,
prepares, or simulates a real order; never holds or asks for an exchange key;
never claims a profit edge. "Preparing" here means: the data is verified, the
rules are re-tested on it honestly, the guard rails are wired and tested, and
the checklist for *L's own* first live order is written down. The order
itself is L's, by hand, on L's machine, through `kraken` — exactly as
`EXECUTION_ARCHITECTURE.md` decided.

---

## 1. What changed today

### 1a. Three assets now have 598-bar verified series (2025-01-01 → 2026-08-21)

`realdata/deep/XLM_2025_2026Aug.csv`, `SOL_2025_2026Aug.csv`,
`XRP_2025_2026Aug.csv` — Kraken daily bars, five to eight 100-row windows
each, merged on byte-identical overlap rows, 86 400 s spacing / no
duplicates / OHLC sanity / 00:00 UTC asserted, one interior window
re-fetched independently per asset (30/30 identical), today's forming bar
dropped. **Cross-venue check against `VERIFIED_BASELINE_2026-08-19.md`
(Coinbase closes):** XRP 1.10537 vs 1.105400, XLM 0.170258 vs 0.170252,
SOL 85.33 vs 85.34 — two venues, same day, agree to < 0.01 %.

These replace the 220-bar series for those three assets: 396 decision bars
after the 200-day warm-up instead of ~20.

### 1b. D2 — the 200-day regime rule re-tested on the deep data

`d2_regime_deep.py`, on the project's own `covenant_backtest.py` engine
(signal at close *t*, fill at open *t+1*, 40 bps round trip, $12 notional),
regime-long-above-SMA200 vs buy-and-hold, plus a stationary block bootstrap
(2 000 draws, mean block 10 d) of the daily returns with the position series
held fixed — the null that the signal says nothing about tomorrow.

| asset | in-market | switches | regime (engine, fixed $12) | B&H | max DD regime | max DD B&H | timing edge (log-growth, costed) | bootstrap p |
|---|---|---|---|---|---|---|---|---|
| XLM | 34 % | 9 | −74.1 % | −56.7 % | −74.6 % | −69.8 % | +12.2 % | **0.810** |
| SOL | 27 % | 3 | −6.2 % | −48.7 % | −36.4 % | −74.9 % | +58.8 % | **0.465** |
| XRP | 21 % | 3 | −37.8 % | −58.2 % | −39.4 % | −72.1 % | +56.0 % | **0.668** |
| ADA *(07:45 run)* | — | 3 | −33.5 % | −73.6 % | −38 % | −85 % | +110 % | **0.531** |
| ATOM *(08:45 run)* | 10 % | 11 | −44.8 % | −69.3 % | −44.9 % | −76.4 % | +76.8 % | **0.697** |
| AVAX *(08:45 run)* | 19 % | 4 | −32.7 % | −69.0 % | −49.9 % | −83.3 % | +89.2 % | **0.546** |
| NEAR *(08:45 run)* | 38 % | 11 | −63.4 % | −34.2 % | −76.5 % | −69.7 % | −25.8 % | **0.773** |
| CRO *(08:45 run, 570 bars from 2025-01-29)* | 21 % | 1 | −14.6 % | −62.0 % | −60.6 % | −85.9 % | +88.2 % | **0.509** |
| ONDO *(08:45 run)* | — | 18 | −115.9 % † | −62.4 % | −132.6 % † | −80.2 % | −26.3 % | **0.915** |
| PEPE *(08:45 run)* | — | 5 | −47.3 % | −70.9 % | −47.8 % | −83.6 % | +95.5 % | **0.658** |
| WLFI *(08:45 run, 355 bars from 2025-09-01; 155 decision bars, rule never entered)* | 0 % | 0 | 0.0 % | −33.2 % | 0.0 % | −50.7 % | +44.6 % ‡ | n/a ‡ |

† The engine sums fixed-notional dollar P&L (M21), so 18 whipsaw losses read
below −100 %; on a compounding convention the loss is bounded. The sign and
the verdict (regime lost to holding, 0.9× no drawdown reduction) stand.
‡ WLFI's series is too short for the 200-bar rule to have ever fired: the
"edge" is just −(buy-and-hold), and the bootstrap p is meaningless. No
statement about the rule on WLFI is possible from Kraken's history.

*08:45 addendum (eleven assets fetched, ten testable, all Kraken daily, 2025-01-01 → 2026-08-21):*
no asset's timing edge is distinguishable from chance (p 0.47–0.92; second
bootstrap seed moves each p by ≤ 0.03). Drawdown reduction: SOL 2.1×, ADA
2.2×, XRP 1.8×, PEPE 1.7×, ATOM 1.7×, AVAX 1.7×, CRO 1.4× — and **none on
XLM (0.9×), NEAR (0.9×) or ONDO (0.6×)**, where the rule whipsawed 9, 11 and
18 times and lost MORE than holding. Three of ten is not a tail; the "drawdown control" half of the
verdict is itself asset-dependent and should not be assumed for any asset
it has not been measured on.

Reading it honestly:

- **No timing edge is distinguishable from chance** on three times the data
  (p = 0.47–0.81). Same verdict as the 220-bar result (XRP −2.70 %
  p = 0.656; HBAR −7.06 % p = 0.891); the sign happens to be positive this
  time and it still means nothing. Deflated Sharpe is 0.000 on all three.
- **The drawdown claim ("~3× reduction replicated") weakens:** SOL 2.1×,
  XRP 1.8×, **XLM 0.9× — no reduction at all.** XLM whipsawed nine times in
  a falling market and the rule lost *more* than holding. A regime rule on
  an asset that oscillates around its own 200-day line is a fee machine.
- **Power, by arithmetic:** to detect an annualised Sharpe of 0.5 at 80 %
  power with daily bars needs ≈ ((1.96 + 0.84)/0.5)² ≈ 31 years of data
  per asset. No amount of D1 fetching settles the timing question. The rule
  can only ever be justified as *risk control* (cut the tail), never as a
  return edge — and today it is risk control on SOL/XRP and not on XLM.
- One bug caught on the way, recorded because it is the hazard the engine
  exists for: the first cut of the bootstrap helper used bar *t+1*'s own
  open-to-open return for a decision made at *t*'s close — look-ahead by
  one bar — and "found" a +112 % XLM edge. The engine (structurally unable
  to look ahead) said −74 %. Fixed; the engine is the reference.

### 1d. D2 — REBALANCING re-tested (09:45 run): the last Section-0 number, and it is worse than "under-powered"

Section 0 carries one figure computed on the 220-bar series: *"Rebalancing:
+0.45% mean OOS at p=0.109, not significant."* It was the last Section-0 number
whose power was inadequate. `d2_rebalance_deep.py` re-tests it on 598 bars
across three panels (equal-weight target, decision at close *t*, fill at the
open of *t+1*, 40 bps round trip charged on every unit of traded notional,
against letting the same weights DRIFT untouched).

**The 220-bar figure reproduces almost exactly — and that is the problem.**
WATCHLIST-9 monthly on 598 bars: mean OOS spread **+0.96%, 5 of 6 folds
positive, p = 0.109.** Identical p to the original. Not a coincidence:
`binom_p(5, 6) = 7/64 = 0.109375`. **Section 0's p = 0.109 is not a
measurement of the data at all — it is the arithmetic value of "five of six
folds were positive".** With six folds only seven p-values exist, and 0.109 is
the second-best attainable; the best possible (6/6) is 0.016. The conclusion
was never sample-limited. It was fold-limited, and no quantity of extra bars
can move it.

**Worse: re-slice the SAME 598 bars and the sign disappears.**

| panel | 6 folds | 8 folds | 12 folds |
|---|---|---|---|
| HELD-6 | +0.73%, 4/6, p 0.344, t +1.46 | **−0.32%**, 4/8, p 0.637, t −1.01 | **−0.13%**, 4/12, p 0.927, t −0.82 |
| WATCHLIST-9 | +0.96%, 5/6, p 0.109, t +2.44 | **−0.13%**, 4/8, p 0.637, t −0.45 | +0.09%, 5/12, p 0.806, t +0.45 |

Same data, same rule, same costs — only the fold boundaries move, and the mean
out-of-sample spread flips sign. An estimate whose sign depends on where you
cut it is not a weak signal; it is no signal, and the encouraging 6-fold number
is an artifact of where 2025-01-01 + 99 bars happens to land. **Correction
against this loop's own earlier framing:** the 08:45 entry called this "the one
remaining Section-0 number whose power was inadequate", implying deeper data
would settle it. Deeper data does not settle it. The defect is in the
estimator, not the sample.

**What IS solid, and it is not an edge.** Full-sample, the rebalanced book
beats drift by +4.4% to +9.8% depending on panel and schedule, and it is not a
cost artifact (zero-cost control: monthly +6.14% vs +5.69% at 40 bps — costs
eat only ~0.45pp). Breakeven cost is 554–637 bps round trip at monthly against
the 40 bps actually paid, a ~15× cushion. But the block bootstrap puts it at
p = 0.084–0.144 (stable across two seeds), which for THIS test reads the right
way round: under i.i.d. returns the rebalancing bonus is **positive by
construction** — it is the diversification return, half the gap between mean
asset variance and portfolio variance. So a high p means *the observed bonus is
only the mechanical one*. Holding six to nine volatile, imperfectly correlated
assets and periodically resetting the weights harvests variance. That is
arithmetic, not skill, and it would have shown up on random data with the same
covariance.

**Rebalancing does NOT cut the tail.** Max drawdown −74.4% rebalanced vs −74.9%
drifting on HELD-6; −74.3% vs −75.9% on WATCHLIST-9. Unlike the regime rule
(which at least gave 1.4–2.2× drawdown reduction on seven of ten assets), this
buys no tail protection worth naming.

**And the finding that actually decides it — rule 4.** L's rule 4 is *never
average down*. Rebalancing a portfolio in which nine of ten positions are down
is, mechanically, averaging down: the trades sell whatever held up and buy
whatever fell. Measured share of every rebalancing BUY that goes into an asset
which has fallen since the previous rebalance:

| schedule | HELD-6 | WATCHLIST-9 |
|---|---|---|
| daily | 66% | 68% |
| weekly | 68% | 72% |
| monthly | 72% | 75% |
| quarterly | 91% | 91% |
| **5% band** (the shape the 20%-cap policy implies) | **95%** | **97%** |

At the band schedule the policy's own structure points at, **95–97% of the
buying is the thing rule 4 forbids.** Rebalancing and rule 4 are not two
independent settings that happen to conflict at the margin; on this portfolio,
in this window, they are near-opposites. No previous run measured this.

**Verdict.** Section 0's statement stands exactly as written and is not edited
(Section 0 is immutable, and this run's evidence supports it rather than
challenging it). The addition for L is: the rebalancing spread is real,
mechanical, cost-robust, gives no drawdown protection, has no demonstrable
out-of-sample edge at any honest slicing, and is ~95% composed of trades rule 4
prohibits. **If you keep rule 4, you have already decided against rebalancing —
say so explicitly rather than leaving both in the policy.**

---

### 1c. E1 — node efficiency / power (L's second ask)

`probe_power.py` on the shipped v8.27: an idle real node (listeners,
tip-gossip, governor and succession loops) uses **0.03 % of one core and
56 MB RSS**; one block of PoW at difficulty 4 costs **0.34 CPU-s mean
(0.04–1.38, geometric)**; registration PoW at difficulty 2 is < 10 ms; a
tip-gossip frame is 0.03 ms. At 2.5 W per active phone core that is
0.02 Wh/day idle and 0.2 mWh per block — **≈ 0.1 % of a 15 Wh phone battery
per day.** CPU is not the phone's cost; the **radio** is: 720 gossip wake-ups
per peer per day at ~1 J each on cellular ≈ 0.4 Wh/day ≈ 3 %/day (arithmetic,
not measured — the phone has not arrived). The lever already exists:
`COVENANT_TIP_GOSSIP_INTERVAL` (default 120 s); 600 s on a phone cuts radio
wake-ups 5× and leaves K2's boot push untouched. Recorded as **C4** for
when the phone is here.

---

## 2. The readiness checklist — what must be true before L's first live order

Each line is checkable; none is a recommendation to trade.

| # | condition | status | who |
|---|---|---|---|
| 1 | Verified price data for every held asset, no stale-row transport (`PRICE_DATA_INTEGRITY.md`) | **XLM/SOL/XRP/ADA/ATOM/AVAX/NEAR: 598 bars; CRO 570; HBAR 408 (from 2025-07-10) — done on Kraken.** ONDO/PEPE 598; WLFI 355 (listed 2025-09-01). **D1 complete for all ten held assets.** | loop (D1) |
| 2 | The rule being executed has been re-tested on the deep data and its verdict written down | **done for the regime rule** (§1b): not a return edge; drawdown control on SOL/XRP; harmful on XLM this window | loop (D2) |
| 3 | `guards.py` wired into `daily.py` (D4) and unit-tested (D3) | **DONE 2026-08-22.** `guards.py` was reachable by NOTHING (`grep -i guard daily.py` → zero lines). Now imported, failing closed on the import, gating rule 2's "may add" only — never a trim, never a sale. `test_d3_daily_guards.py` 61/61 ×2, in `run_all_tests.sh`, shipped to the PC | loop (done) |
| 3b | The same wiring inside `execute.py` | **VOID — `execute.py` does not exist** (see the correction in `EXECUTION_ARCHITECTURE.md`). Not an upload away; it has to be written | L's call |
| 4 | `paper_run.py` has ≥ 30 sealed, settled signals and `--verify` passes | **`paper_run.py` does not exist either.** The covenant folder holds `paper_bot.py` and nothing else of that shape. Zero sealed signals exist. This line cannot be satisfied until the file is written and has then run ≥ 30 times | L's call |
| 5 | `EdgeMonitor` seeded with `expected_mean`/`expected_sd` from a backtest that **passed** `evaluate()` | **cannot be seeded honestly today** — no rule has passed (DSR 0.000). Run it on the drawdown target instead, or not at all | L's call |
| 6 | `kraken` CLI installed on L's machine, read-only by default, paper mode validated, `--allow-dangerous` never in a cloud path | per `EXECUTION_ARCHITECTURE.md`; L confirms | L |
| 7 | Trade key only in `~/.config/kraken/config.toml` inside WSL; never in `C:\Users\Lawre\covenant`; Ledger phrase untouched | standing | L |
| 8 | Order size clamped to the venue balance (`execute.py` `kraken balance` check) — the SOL-not-on-Kraken bug | implemented per the doc; re-test after D3 | L, loop |
| 9 | `TRADING_POLICY.json` locks the ten positions; the sleeve is the only live capital; rule 4 (never average down) binds | standing | L |
| 10 | Every order confirmed by L per order; the cloud session computes, never places | standing, Section 0 | both |

**Blocking today (rewritten 2026-08-22 after the folder was actually read).**
The old text here said #3 and #4 "need files that exist only on L's machine.
Upload `execute.py`, `guards.py`, `daily.py`, `paper_run.py`…". Two of those
four files do not exist anywhere, and the other two were reachable over the
device bridge all along in an L-started session — see `claude/PC_SYNC_LOOP.md`.
So:

- **#3 is done** (guards wired + 61 automated checks, shipped to the PC).
- **#3b and #4 are not blocked on an upload; they are unwritten code.**
  `execute.py` (compute orders → clamp to the Kraken balance → L confirms each
  one → the local `kraken` binary places it) and `paper_run.py` (hash-chained
  sealed signals, ≥ 30 before any claim) both have to be built, and
  `EXECUTION_ARCHITECTURE.md` must be re-decided rather than assumed, because
  it describes testing that never happened.
- **#5 is unchanged and still cannot be seeded honestly** — no rule has passed
  `evaluate()`; DSR is 0.000 everywhere.

**The honest position on "ready for live trades" is therefore further away
than the 08:00 version of this document implied, not closer.** What moved
today is that the two blockers are now correctly named: not missing uploads,
but missing code and a missing 30-signal paper record. Nothing here is a
recommendation to trade, and the boundary in Section 0 is untouched.

---

## 3. Pushback, recorded

"Preparing for live trades" invites the loop to drift toward placing one.
It will not. What the numbers in §1b say is that the trading rules in this
project are *risk rules*, not *alpha*; the honest preparation is to make the
guard rails unbreakable (D3/D4) and the data trustworthy (D1), and to stop
expecting the backtest to bless a timing edge it has now failed to find on
two data depths. If L wants the regime rule kept on XLM, that is a choice
to accept whipsaw cost for tail protection that did not materialise in this
window — fine, but choose it knowingly.

**Files:** `realdata/deep/*.csv` (twelve series, all re-verified 09:45),
`claude/d2_regime_deep.py`, `claude/d2_rebalance_deep.py`,
`claude/probe_power.py`, `claude/verify_csv.py`, this document. Node source
unchanged by the 09:45 run (project holds v8.28 `76d2c54e…`).

**Added 09:45, on rebalancing (§1d):** the checklist line about "the rule being
executed has been re-tested" now covers both rules in this project. Neither is
a return edge. The regime rule is tail protection on seven of ten assets and
harmful on three; rebalancing is variance harvesting that protects no tail and
contradicts rule 4 on 95% of its trades. There is no third rule waiting to be
tested — D2 is finished, and what remains before a live order is entirely
guard-rail work (D3/D4) on files only L has.
