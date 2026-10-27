"""pbo_hbar.py -- Probability of Backtest Overfitting (CSCV) on the D6 grid.

WHY. covenant_backtest.py already has deflated_sharpe, min_track_record_length,
walk_forward, an embargo and look-ahead guards. It has no PBO -- which is the
standard statistic for the thing d6 ALREADY OBSERVED: choosing the top variants
by train performance produced -2.70% (XRP) and -7.06% (HBAR) out of sample, at
p = 0.656 and 0.891. A permutation p-value was computed for that. PBO is the
named measure of it.

METHOD -- Bailey, Borwein, Lopez de Prado & Zhu, "The Probability of Backtest
Overfitting", followed as specified:
  * input is a T x N matrix of per-period returns; N configurations, T periods
  * T is split into S = 16 DISJOINT CONTIGUOUS blocks (the paper's recommended
    default; contiguity preserves the serial-correlation structure)
  * all C(16,8) = 12,870 train/test splits are formed from complementary halves
  * for each split: take the variant that is best IN SAMPLE, find its
    OUT-OF-SAMPLE rank, convert to logit lambda = ln(w/(1-w))
  * PBO = the rate at which the in-sample-optimal variant lands BELOW the
    out-of-sample median, i.e. the fraction of splits with lambda <= 0
  * requirements: N >> 10 (here 53), T about double what an investor would use

Combined-window Sharpe is computed EXACTLY from per-block (n, sum, sumsq), not
approximated by averaging per-block Sharpes -- averaging ratios is wrong and
would quietly flatter the result.

THE NO-OP TRAP, found by running this and disbelieving the answer. Seven of
the 53 variants never trade at all. Scored 0.0 they are not neutral -- they are
the BEST performers in the grid, because every one of the 46 variants that DOES
trade has a negative full-sample Sharpe (best -0.0299, worst -0.1596, zero
positive). So argmax picks a no-op in sample AND out of sample, and PBO comes
back 0.347: a measurement of "not trading beats trading", which is true and is
not the question PBO asks.

PBO asks whether SELECTION AMONG STRATEGIES generalises. That question is only
meaningful over strategies that trade. Both numbers are therefore reported, and
the degenerate one is kept because it carries the sharper finding.

PREDICTION, filed before the run (docs/sessions/IMPROVEMENTS_2026-08-29.md):
PBO > 0.5. A LOW value means this implementation is wrong, not that the
strategy is good.

OUTCOME 2026-08-29. The all-variant run returned 0.347 and the filed rule was
honoured rather than the number: the implementation was audited, the no-op trap
above was found, and over the 46 variants that actually trade PBO = 0.5440 --
prediction CONFIRMED. Median logit lambda -0.128, median out-of-sample rank of
the in-sample-best variant 0.468. Choosing on train performance is slightly
WORSE than choosing at random.

Run: python3 pbo_hbar.py
"""
import itertools, math, os, statistics, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import covenant_backtest as cb

CSV     = os.path.join("realdata", "deep", "HBAR_2025Jul_2026Aug.csv")
WARMUP  = 74            # d6's warmup: slowest lookback 72 + margin
CAPITAL = 12.0
S       = 16            # the paper's recommended default

# ---- the exact 53-variant grid from d6_hbar_clean.py ----------------------
def breakout(n):
    def strat(view, pos):
        closes = view.closes(n + 1)
        if len(closes) < n + 1: return pos
        now, prior = closes[-1], closes[:-1]
        if now > max(prior): return 1
        if now < min(prior): return 0
        return pos
    return strat

def sma_cross(f, s):
    def strat(view, pos):
        closes = view.closes(s)
        if len(closes) < s: return pos
        return 1 if statistics.fmean(closes[-f:]) > statistics.fmean(closes) else 0
    return strat

def momentum(n):
    def strat(view, pos):
        closes = view.closes(n + 1)
        if len(closes) < n + 1: return pos
        return 1 if closes[-1] > closes[0] else 0
    return strat

VARIANTS = []
for n in (10, 15, 20, 24, 30, 36, 48, 60, 72, 96):
    VARIANTS.append((f"breakout {n}", breakout(n)))
for s in (20, 30, 48, 72, 96):
    for f in (5, 8, 10, 12, 15, 20, 25, 30):
        if f <= s // 2:
            VARIANTS.append((f"sma_cross {f}/{s}", sma_cross(f, s)))
for n in (10, 15, 20, 24, 30, 36, 48, 60, 72, 96, 120, 144, 168):
    VARIANTS.append((f"momentum {n}", momentum(n)))
assert len(VARIANTS) == 53, len(VARIANTS)


def main():
    bars = cb.load_csv(CSV)
    bt = cb.Backtester(capital=CAPITAL)
    print(f"bars {len(bars)}  variants {len(VARIANTS)}  warmup {WARMUP}")

    cols = []
    for name, strat in VARIANTS:
        r = bt.run(bars, strat, warmup=WARMUP, label=name)
        cols.append(np.asarray(r.returns, dtype=float))
    T = min(len(c) for c in cols)
    R = np.column_stack([c[:T] for c in cols])          # T x N
    N = R.shape[1]
    print(f"returns matrix  T={T}  N={N}   (N >> 10: {N > 10})")

    # contiguous blocks; drop the ragged tail so every block is equal size
    bl = T // S
    R = R[: bl * S]
    B = R.reshape(S, bl, N)
    n_b  = np.full(S, bl, dtype=float)
    s_b  = B.sum(axis=1)                                 # S x N
    q_b  = (B ** 2).sum(axis=1)                          # S x N
    print(f"S={S} blocks of {bl} periods each ({bl*S} of {T} used)")

    def sharpe(idx):
        n  = n_b[list(idx)].sum()
        S1 = s_b[list(idx)].sum(axis=0)
        S2 = q_b[list(idx)].sum(axis=0)
        mu = S1 / n
        var = np.maximum(S2 / n - mu ** 2, 0.0)
        sd = np.sqrt(var)
        out = np.zeros(N)
        nz = sd > 1e-15
        out[nz] = mu[nz] / sd[nz]
        return out

    combos = list(itertools.combinations(range(S), S // 2))
    print(f"splits C({S},{S//2}) = {len(combos):,}\n")
    live = np.asarray(R.std(axis=0) > 1e-15)

    allb = set(range(S))

    def pbo_over(mask, label):
        m = np.asarray(mask)
        k = int(m.sum())
        lam, below, ranks = [], 0, []
        for c in combos:
            oos = tuple(sorted(allb - set(c)))
            a, b = sharpe(c)[m], sharpe(oos)[m]
            best = int(np.argmax(a))
            r = int((b <= b[best]).sum())
            w = min(max(r / (k + 1.0), 1e-9), 1 - 1e-9)
            ranks.append(w); lam.append(math.log(w / (1 - w)))
            if w <= 0.5:
                below += 1
        lam = np.asarray(lam); pbo = below / len(combos)
        print(f"{label}  (N={k})")
        print(f"  PBO = {pbo:.4f}   ({below:,}/{len(combos):,} splits put the "
              f"IS-best below the OOS median)")
        print(f"  median logit lambda {np.median(lam):+.4f}   "
              f"median OOS rank of IS-best {np.median(ranks):.3f}")
        return pbo

    full = R.mean(axis=0) / np.where(R.std(axis=0) > 1e-15, R.std(axis=0), 1)
    print("THE GRID ITSELF")
    print(f"  variants that never trade      {int((~live).sum())}  (Sharpe forced to 0.0)")
    print(f"  variants that trade            {int(live.sum())}")
    print(f"  of those, POSITIVE full Sharpe {int((full[live] > 0).sum())}")
    print(f"  best {full[live].max():+.4f}   worst {full[live].min():+.4f}")
    print("  -> the no-ops, at exactly 0.0, outrank every strategy that trades.\n")

    pbo_over(np.ones(N, bool), "DEGENERATE -- all variants")
    print("  ^ argmax selects a no-op. True, and not the question PBO asks.\n")
    pbo = pbo_over(live, "ANSWER -- variants that actually trade")
    print()
    print(f"  PREDICTION WAS: PBO > 0.5   ->  {'CONFIRMED' if pbo > 0.5 else 'REFUTED'}")
    if pbo <= 0.5:
        print("  A low PBO means this implementation is suspect. Check it before")
        print("  believing it -- that is what the filed prediction is for.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
