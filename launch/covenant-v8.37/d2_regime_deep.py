"""d2_regime_deep.py -- D2: re-run the 200-day regime rule on the deeper data.

WHAT IS TESTED
  The rule every DAILY_CHECK / VERIFIED_BASELINE action derives from: be in
  the asset while its close is above its 200-day simple moving average, in
  cash otherwise. Signal on bar t, executed at the open of t+1 (the engine's
  own timing rule), real costs (40 bps round trip at ~$12 per position).

AGAINST WHAT
  Buy-and-hold over the same bars, same costs, one entry.

THE QUESTION
  Is there a TIMING edge (regime beats buy-and-hold on return), and does the
  drawdown reduction that was the only thing to replicate before still hold?

HOW THE p-VALUE IS MADE
  Stationary block bootstrap (mean block 10 days) of the daily returns under
  the null "the regime signal carries no information about tomorrow": the
  POSITION series is kept exactly as the rule produced it, the RETURN series
  is block-resampled, and the regime-minus-buy-and-hold spread is recomputed
  2000 times. p = share of resampled spreads >= the observed one (one-sided,
  "regime is better"). Costs are charged per switch in both worlds.
  This is a permutation-style null; it is not the exact method the earlier
  figures (XRP -2.70% p=0.656; HBAR -7.06% p=0.891) were produced with, so
  compare direction and magnitude, not decimals.

DATA
  realdata/deep/{XLM,SOL,XRP,ADA,ATOM,AVAX,NEAR}_2025_2026Aug.csv -- 598 bars each
  (CRO 570, listed on Kraken 2025-01-29; ONDO/PEPE 598; WLFI_2025Sep_2026Aug 355,
  listed 2025-09-01),
  2025-01-01 -> 2026-08-21, Kraken, verified (M20). 200-bar warmup leaves
  ~397 decision bars per asset, ~3x what the 220-bar series gave.

Section 0: no claim of profit edge is made here; whatever the numbers say is
reported as it is.
"""
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_backtest as cb

SMA = 200
WARMUP = SMA
N_BOOT = 2000
random.seed(20260822)


def regime_strategy(view, position):
    cl = view.closes(SMA)
    if len(cl) < SMA:
        return 0
    return 1 if view.now.close > sum(cl) / SMA else 0


def buy_hold(view, position):
    return 1


def max_dd(curve):
    peak, worst = curve[0], 0.0
    for v in curve:
        peak = max(peak, v)
        worst = min(worst, v / peak - 1.0)
    return worst


def positions_and_returns(bars):
    """The position the rule holds during bar i+1 (decided at bar i), and the
    open-to-open return of bar i+1 -- the same timing the engine uses."""
    pos, rets = [], []
    # Decided at the close of bar i, filled at the OPEN of bar i+1, and the
    # position then rides bar i+1's open -> bar i+2's open. Using bar i+1's
    # own open-to-open return here would be look-ahead (the first cut did
    # exactly that and "found" +112% on XLM; the engine said -74%).
    for i in range(WARMUP, len(bars) - 2):
        cl = [b.close for b in bars[i - SMA + 1:i + 1]]
        pos.append(1 if bars[i].close > sum(cl) / SMA else 0)
        rets.append(bars[i + 2].open / bars[i + 1].open - 1.0)
    return pos, rets


def spread(pos, rets, cost_bps):
    """Regime log-growth minus buy-and-hold log-growth, costs per switch."""
    c = cost_bps / 10_000.0
    g_reg, g_bh, prev = 0.0, 0.0, 0
    for p, r in zip(pos, rets):
        g_bh += math.log1p(r)
        if p:
            g_reg += math.log1p(r)
        if p != prev:
            g_reg += math.log1p(-c)   # one side of the round trip per switch
            prev = p
    return g_reg - g_bh


def block_bootstrap(rets, mean_block=10):
    n = len(rets)
    out = []
    i = random.randrange(n)
    while len(out) < n:
        if random.random() < 1.0 / mean_block:
            i = random.randrange(n)
        out.append(rets[i % n])
        i += 1
    return out


def run(symbol, path):
    bars = cb.load_csv(path)
    bt = cb.Backtester(cb.CostModel(), capital=12.0)
    reg = bt.run(bars, regime_strategy, warmup=WARMUP, label=f"{symbol} regime200", strategies_tried=3)
    bh = bt.run(bars, buy_hold, warmup=WARMUP, label=f"{symbol} buy&hold", strategies_tried=1)
    pos, rets = positions_and_returns(bars)
    half_rt = cb.CostModel().round_trip_bps() / 2
    obs = spread(pos, rets, half_rt)
    boots = [spread(pos, block_bootstrap(rets), half_rt) for _ in range(N_BOOT)]
    p = sum(1 for b in boots if b >= obs) / N_BOOT
    in_mkt = sum(pos) / len(pos)
    dsr = cb.deflated_sharpe(reg)
    print(f"\n== {symbol}: {len(bars)} bars {cb.__name__} engine, warmup {WARMUP}, "
          f"{len(pos)} decision bars, in-market {in_mkt:.0%}, switches {reg.n_trades}")
    print(f"   regime   : return {reg.total_return:+.2%}  maxDD {max_dd(reg.equity):+.1%}  "
          f"Sharpe {reg.sharpe():.2f}  fees ${reg.total_fees():.2f}  DSR {dsr['deflated_sharpe']:.3f}")
    print(f"   buy&hold : return {bh.total_return:+.2%}  maxDD {max_dd(bh.equity):+.1%}  "
          f"Sharpe {bh.sharpe():.2f}")
    print(f"   timing edge (regime - B&H, log-growth, costs charged): {obs:+.2%}  "
          f"bootstrap p={p:.3f} (one-sided, N={N_BOOT})")
    print(f"   drawdown ratio B&H/regime: {max_dd(bh.equity) / max_dd(reg.equity) if max_dd(reg.equity) else float('inf'):.2f}x")
    return dict(symbol=symbol, edge=obs, p=p, reg_ret=reg.total_return, bh_ret=bh.total_return,
                reg_dd=max_dd(reg.equity), bh_dd=max_dd(bh.equity), n=len(pos), trades=reg.n_trades)


if __name__ == "__main__":
    rows = []
    # symbols may be given on the command line (08:45 run: ATOM AVAX NEAR CRO added)
    for sym in (sys.argv[1:] or ("XLM", "SOL", "XRP", "ADA", "ATOM", "AVAX", "NEAR", "CRO", "ONDO", "PEPE", "WLFI")):
        fn = {"WLFI": "WLFI_2025Sep_2026Aug.csv"}.get(sym, f"{sym}_2025_2026Aug.csv")
        rows.append(run(sym, os.path.join(HERE, fn)))
    print("\n== summary (598-bar series, 2025-01-01 -> 2026-08-21)")
    print(f"   {'sym':<4} {'edge':>8} {'p':>6} {'regime':>9} {'B&H':>9} {'DD reg':>8} {'DD B&H':>8} {'switches':>8}")
    for r in rows:
        print(f"   {r['symbol']:<4} {r['edge']:>+8.2%} {r['p']:>6.3f} {r['reg_ret']:>+9.2%} {r['bh_ret']:>+9.2%} "
              f"{r['reg_dd']:>+8.1%} {r['bh_dd']:>+8.1%} {r['trades']:>8}")
