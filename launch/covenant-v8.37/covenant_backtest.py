"""
covenant_backtest.py -- backtesting that tries to prove itself WRONG.

THE PROBLEM THIS EXISTS FOR
---------------------------
A backtest is a search over strategies for one that fits a fixed history. Run
enough variants and you will find a beautiful equity curve on data with no edge
in it at all -- not because you cheated, but because that is what searching
does. The curve is real. The edge is not. Everything here is built to make that
failure visible instead of flattering.

Three named hazards, each with machinery against it rather than a warning:

1. LOOK-AHEAD. Not prevented by discipline -- prevented STRUCTURALLY. A strategy
   is handed a PointInTimeView that physically cannot index past the current
   bar; asking for tomorrow raises. You cannot forget to be careful about a
   thing you are unable to do.

2. THE BACKTEST ILLUSION. Every reported result carries the number of
   strategies that were TRIED. A Sharpe of 2.0 from one attempt and a Sharpe of
   2.0 from two hundred attempts are not the same claim, and the deflated
   Sharpe ratio (Bailey & Lopez de Prado) says so numerically. Results also go
   through walk-forward with purging and an embargo, so the reported figure is
   out-of-sample by construction.

3. THE EDGE PROBLEM. An edge that existed is not an edge that exists. EdgeMonitor
   tracks live performance against the backtest's own distribution and pulls a
   kill switch when live results stop being explicable by it. Decay is assumed,
   not hoped against.

COSTS ARE NOT A DETAIL AT THIS SIZE
-----------------------------------
Backtesting at 10,000 notional when real per-asset capital is ~12 produces
numbers that mean nothing: fees and spread scale with turnover, not with your
optimism. The cost model is calibrated at the capital actually deployed, and
`min_notional` refuses trades too small to clear the exchange minimum instead
of silently pretending they filled.

WHAT THIS IS NOT
----------------
It is not a strategy, and it will not find you one. It is the apparatus that
decides whether something you already believe survives contact with evidence.
"""

from __future__ import annotations

import math
import json
import statistics
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Callable, Any, Tuple, Sequence


# ---------------------------------------------------------------------------
# Bars and point-in-time access
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Bar:
    ts: float
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


class LookAheadError(Exception):
    """Raised when a strategy reaches for data it could not have had."""


class PointInTimeView:
    """A window over history that ENDS at the current bar.

    The anti-look-ahead measure is that there is no forward index to use. A
    strategy receives this object and can ask for bar -1 (now), -2, -5; asking
    for 0 or a positive index raises LookAheadError rather than quietly handing
    over the future. Bias by omission is the most common way a backtest lies,
    and a convention that must be remembered is one that will eventually be
    forgotten.
    """

    __slots__ = ("_bars", "_i")

    def __init__(self, bars: Sequence[Bar], i: int):
        self._bars = bars
        self._i = i

    def __len__(self) -> int:
        return self._i + 1

    def __getitem__(self, k: int) -> Bar:
        if k >= 0:
            raise LookAheadError(
                f"index {k} reaches forward. Use negative indices: -1 is the "
                f"current bar, -2 the one before it. There is no legitimate "
                f"reason for a strategy to address a future bar.")
        j = self._i + 1 + k
        if j < 0:
            raise IndexError(f"only {self._i + 1} bars exist at this point")
        return self._bars[j]

    def closes(self, n: int) -> List[float]:
        n = min(n, self._i + 1)
        return [self._bars[self._i + 1 - n + k].close for k in range(n)]

    @property
    def now(self) -> Bar:
        return self._bars[self._i]


# ---------------------------------------------------------------------------
# Costs
# ---------------------------------------------------------------------------

@dataclass
class CostModel:
    """Costs at the size actually traded, not at a comfortable size.

    slippage_bps is applied ADVERSELY in both directions. Modelling fills at the
    mid is the single most flattering error available to a backtest, because it
    is invisible: the equity curve simply comes out better and nothing looks
    wrong.
    """
    taker_fee_bps: float = 10.0      # 0.10%
    spread_bps: float = 5.0          # half-spread paid on entry and exit
    slippage_bps: float = 5.0
    min_notional: float = 5.0        # exchange minimum; below this, no trade

    def round_trip_bps(self) -> float:
        return 2 * (self.taker_fee_bps + self.spread_bps + self.slippage_bps)

    def fill_price(self, ref: float, side: int) -> float:
        """side +1 buy, -1 sell. Always worse than the reference."""
        adverse = (self.spread_bps + self.slippage_bps) / 10_000.0
        return ref * (1 + adverse) if side > 0 else ref * (1 - adverse)

    def fee(self, notional: float) -> float:
        return abs(notional) * self.taker_fee_bps / 10_000.0

    def breakeven_move_bps(self) -> float:
        """How far price must move for a round trip to break even. At small
        notional this number is often larger than the edge being claimed."""
        return self.round_trip_bps()


# ---------------------------------------------------------------------------
# Backtest engine
# ---------------------------------------------------------------------------

@dataclass
class Trade:
    entry_ts: float
    exit_ts: float
    entry_px: float
    exit_px: float
    side: int
    notional: float
    pnl: float
    fees: float
    bars_held: int


@dataclass
class BacktestResult:
    trades: List[Trade]
    equity: List[float]
    returns: List[float]
    start_equity: float
    end_equity: float
    n_bars: int
    rejected_min_notional: int = 0
    strategies_tried: int = 1
    label: str = ""

    @property
    def total_return(self) -> float:
        return (self.end_equity / self.start_equity) - 1.0 if self.start_equity else 0.0

    @property
    def n_trades(self) -> int:
        return len(self.trades)

    def sharpe(self, periods_per_year: float = 365.0) -> float:
        """Annualised Sharpe of per-bar returns. Zero risk-free: at these
        horizons the rate is noise next to the estimation error."""
        if len(self.returns) < 2:
            return 0.0
        mu = statistics.fmean(self.returns)
        sd = statistics.pstdev(self.returns)
        if sd == 0:
            return 0.0
        return (mu / sd) * math.sqrt(periods_per_year)

    def max_drawdown(self) -> float:
        peak, mdd = -float("inf"), 0.0
        for e in self.equity:
            peak = max(peak, e)
            if peak > 0:
                mdd = max(mdd, (peak - e) / peak)
        return mdd

    def total_fees(self) -> float:
        return sum(t.fees for t in self.trades)

    def gross_pnl(self) -> float:
        return sum(t.pnl for t in self.trades) + self.total_fees()


# A strategy is: (view, position) -> desired position in {-1, 0, +1}
Strategy = Callable[[PointInTimeView, int], int]


class Backtester:
    """Bar-by-bar, with the one timing rule that matters.

    A signal computed from bar t is executed at the OPEN of bar t+1. Filling at
    the close of the bar that produced the signal is look-ahead wearing ordinary
    clothes: at the moment that close printed, the decision had not been made.
    """

    def __init__(self, cost: Optional[CostModel] = None, capital: float = 12.0):
        self.cost = cost or CostModel()
        self.capital = float(capital)

    def run(self, bars: Sequence[Bar], strategy: Strategy,
            warmup: int = 30, label: str = "", strategies_tried: int = 1) -> BacktestResult:
        if len(bars) < warmup + 10:
            raise ValueError(
                f"{len(bars)} bars is too few for a warmup of {warmup}. A short "
                f"backtest does not produce a weak conclusion, it produces no "
                f"conclusion.")

        equity = self.capital
        eq_curve, rets = [equity], []
        position, entry_px, entry_ts, entry_bar = 0, 0.0, 0.0, 0
        trades: List[Trade] = []
        rejected = 0
        pending: Optional[int] = None

        for i in range(warmup, len(bars) - 1):
            nxt = bars[i + 1]

            # Execute the PREVIOUS bar's decision at this bar's open.
            if pending is not None and pending != position:
                target = pending
                if position != 0:
                    px = self.cost.fill_price(bars[i].open, -position)
                    pnl = position * (px - entry_px) * (self.capital / entry_px)
                    f = self.cost.fee(self.capital) * 2
                    equity += pnl - f
                    trades.append(Trade(entry_ts, bars[i].ts, entry_px, px, position,
                                        self.capital, pnl - f, f, i - entry_bar))
                    position = 0
                if target != 0:
                    if self.capital < self.cost.min_notional:
                        rejected += 1
                    else:
                        entry_px = self.cost.fill_price(bars[i].open, target)
                        entry_ts, entry_bar, position = bars[i].ts, i, target
            pending = None

            # Decide using data that ends HERE.
            view = PointInTimeView(bars, i)
            try:
                desired = int(strategy(view, position))
            except LookAheadError:
                raise
            if desired not in (-1, 0, 1):
                raise ValueError(f"strategy returned {desired}; must be -1, 0 or +1")
            pending = desired

            prev_eq = eq_curve[-1]
            mark = equity
            if position != 0:
                mark = equity + position * (nxt.open - entry_px) * (self.capital / entry_px)
            eq_curve.append(mark)
            rets.append((mark / prev_eq) - 1.0 if prev_eq else 0.0)

        if position != 0:
            last = bars[-1]
            px = self.cost.fill_price(last.close, -position)
            pnl = position * (px - entry_px) * (self.capital / entry_px)
            f = self.cost.fee(self.capital) * 2
            equity += pnl - f
            trades.append(Trade(entry_ts, last.ts, entry_px, px, position,
                                self.capital, pnl - f, f, len(bars) - entry_bar))

        return BacktestResult(trades=trades, equity=eq_curve, returns=rets,
                              start_equity=self.capital, end_equity=equity,
                              n_bars=len(bars), rejected_min_notional=rejected,
                              strategies_tried=strategies_tried, label=label)


# ---------------------------------------------------------------------------
# The guardrails
# ---------------------------------------------------------------------------

def _norm_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _norm_ppf(p: float) -> float:
    """Inverse normal CDF, Acklam's rational approximation."""
    if not 0 < p < 1:
        raise ValueError("p must be in (0,1)")
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    pl, ph = 0.02425, 1 - 0.02425
    if p < pl:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > ph:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q = p - 0.5
    r = q * q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


def _skew_kurt(xs: Sequence[float]) -> Tuple[float, float]:
    n = len(xs)
    if n < 4:
        return 0.0, 3.0
    m = statistics.fmean(xs)
    sd = statistics.pstdev(xs)
    if sd == 0:
        return 0.0, 3.0
    s = sum(((x - m) / sd) ** 3 for x in xs) / n
    k = sum(((x - m) / sd) ** 4 for x in xs) / n
    return s, k


def deflated_sharpe(result: BacktestResult, periods_per_year: float = 365.0) -> Dict[str, float]:
    """Probability the observed Sharpe reflects skill rather than selection.

    THIS IS THE CENTRAL ANTI-ILLUSION NUMBER. The expected maximum Sharpe from
    N independent NO-EDGE trials grows with N: search two hundred strategies on
    random data and the best will look good, guaranteed. The deflated Sharpe
    compares what was observed against that selection benchmark, and corrects
    for the non-normal returns that make raw Sharpe optimistic on financial
    data.

    Bailey & Lopez de Prado, "The Deflated Sharpe Ratio" (2014).
    """
    sr = result.sharpe(periods_per_year)
    n = len(result.returns)
    trials = max(1, int(result.strategies_tried))
    if n < 10:
        return {"sharpe": sr, "deflated_sharpe": 0.0, "expected_max_sharpe": 0.0,
                "trials": trials, "n": n, "verdict": "too few observations"}

    sk, ku = _skew_kurt(result.returns)
    # Expected maximum Sharpe under the null, across `trials` independent tries.
    if trials > 1:
        e = 0.5772156649
        z1 = _norm_ppf(1 - 1.0 / trials)
        z2 = _norm_ppf(1 - 1.0 / (trials * math.e))
        emax = (1 - e) * z1 + e * z2
    else:
        emax = 0.0
    # Variance of the Sharpe estimator with the observed higher moments.
    denom = math.sqrt(max(1e-12, 1 - sk * sr + ((ku - 1) / 4.0) * sr * sr))
    dsr = _norm_cdf(((sr - emax) * math.sqrt(max(1, n - 1))) / denom) if denom else 0.0
    return {"sharpe": sr, "deflated_sharpe": dsr, "expected_max_sharpe": emax,
            "trials": trials, "n": n, "skew": sk, "kurtosis": ku,
            "verdict": "credible" if dsr >= 0.95 else "not distinguishable from selection luck"}


def min_track_record_length(result: BacktestResult, target_sharpe: float = 0.0,
                            confidence: float = 0.95,
                            periods_per_year: float = 365.0) -> Dict[str, float]:
    """How many observations would be needed to call this Sharpe real.

    Answers the question a backtest never volunteers: is this track record long
    enough to support the claim at all? If the requirement exceeds what you
    have, the honest reading is "unknown", not "positive".
    """
    sr = result.sharpe(periods_per_year)
    n = len(result.returns)
    sk, ku = _skew_kurt(result.returns)
    if sr <= target_sharpe:
        return {"observed_sharpe": sr, "have": n, "need": float("inf"),
                "sufficient": False, "reason": "Sharpe does not exceed the target"}
    z = _norm_ppf(confidence)
    need = 1 + (1 - sk * sr + ((ku - 1) / 4.0) * sr * sr) * (z / (sr - target_sharpe)) ** 2
    return {"observed_sharpe": sr, "have": n, "need": need,
            "sufficient": n >= need,
            "reason": "sufficient" if n >= need else
                      f"needs ~{need:,.0f} observations, has {n:,}"}


def walk_forward(bars: Sequence[Bar], build: Callable[[Sequence[Bar]], Strategy],
                 folds: int = 5, embargo_frac: float = 0.01,
                 cost: Optional[CostModel] = None, capital: float = 12.0,
                 warmup: int = 30) -> Dict[str, Any]:
    """Anchored walk-forward with an EMBARGO between fit and test.

    `build` is given ONLY the training slice and returns a strategy; it never
    sees the test slice. The embargo drops bars immediately after the training
    window so that overlapping-horizon effects and any serial correlation cannot
    leak a fitted parameter into the very next test bar. Without the gap,
    "out-of-sample" is adjacent enough to be in-sample in practice.
    """
    n = len(bars)
    if n < (folds + 1) * (warmup + 30):
        raise ValueError(f"{n} bars cannot support {folds} folds with warmup {warmup}")
    emb = max(1, int(n * embargo_frac))
    fold_size = n // (folds + 1)
    out = []
    bt = Backtester(cost=cost, capital=capital)
    for f in range(folds):
        train_end = fold_size * (f + 1)
        test_start = min(n - 1, train_end + emb)
        test_end = min(n, test_start + fold_size)
        if test_end - test_start < warmup + 10:
            continue
        strat = build(bars[:train_end])
        r = bt.run(bars[test_start:test_end], strat, warmup=warmup,
                   label=f"fold{f+1}")
        out.append(r)
    if not out:
        raise ValueError("no usable folds")
    rets = [x.total_return for x in out]
    k, m = sum(1 for r in rets if r > 0), len(out)

    # MEASURED CORRECTION -- see the note below. Counting positive folds is not
    # a test, it is a tally. On a random walk with 5 folds this framework's own
    # validation produced 4/5 positive and +9.76% mean from a strategy mined out
    # of provable noise, and a naive ">= 60% of folds" rule PASSED it.
    #
    # Under the null, each fold is roughly a coin flip, so 4/5 has a one-sided
    # p of about 0.19 -- unremarkable. The binomial p-value below says so, and
    # consistency now requires BOTH a majority of positive folds and a result
    # unlikely under the null. With few folds that is hard to achieve, which is
    # the correct behaviour: five folds cannot support a confident claim, and
    # the framework should say that rather than imply otherwise.
    p_val = sum(math.comb(m, j) for j in range(k, m + 1)) / (2 ** m) if m else 1.0
    return {
        "folds": m,
        "fold_returns": rets,
        "mean_return": statistics.fmean(rets),
        "median_return": statistics.median(rets),
        "positive_folds": k,
        "worst_fold": min(rets),
        "binomial_p": p_val,
        "consistent": (k >= max(1, int(0.6 * m))) and p_val <= 0.05,
        "results": out,
    }


@dataclass
class GuardrailVerdict:
    passed: bool
    checks: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def report(self) -> str:
        lines = [("PASS" if self.passed else "REJECT") + " -- backtest credibility", ""]
        for name, c in self.checks.items():
            mark = "ok  " if c["passed"] else "FAIL"
            lines.append(f"  [{mark}] {name}: {c['detail']}")
        if not self.passed:
            lines += ["", "  A failing check does not mean the strategy is bad.",
                      "  It means this backtest does not constitute evidence."]
        return "\n".join(lines)


def evaluate(result: BacktestResult, wf: Optional[Dict[str, Any]] = None,
             cost: Optional[CostModel] = None,
             min_trades: int = 30, periods_per_year: float = 365.0) -> GuardrailVerdict:
    """Run every guardrail. A strategy is credible only if all of them hold.

    Deliberately unanimous rather than scored: a weighted score lets a strong
    showing on one axis paper over a disqualifying failure on another, and the
    failures here are disqualifying. Too few trades is not partly-credible.
    """
    checks: Dict[str, Dict[str, Any]] = {}
    cost = cost or CostModel()

    checks["sample size"] = {
        "passed": result.n_trades >= min_trades,
        "detail": f"{result.n_trades} trades (need >= {min_trades}); "
                  f"fewer cannot separate skill from variance"}

    d = deflated_sharpe(result, periods_per_year)
    checks["deflated Sharpe"] = {
        "passed": d["deflated_sharpe"] >= 0.95,
        "detail": f"raw Sharpe {d['sharpe']:.2f} over {d['trials']} trial(s) -> "
                  f"DSR {d['deflated_sharpe']:.3f} ({d['verdict']}); "
                  f"selection benchmark {d['expected_max_sharpe']:.2f}"}

    m = min_track_record_length(result, periods_per_year=periods_per_year)
    checks["track record length"] = {
        "passed": bool(m["sufficient"]),
        "detail": f"{m['reason']}"}

    gross, net = result.gross_pnl(), result.end_equity - result.start_equity
    checks["survives costs"] = {
        "passed": net > 0,
        "detail": f"gross {gross:+.4f} -> net {net:+.4f} after {result.total_fees():.4f} "
                  f"in fees; breakeven move {cost.breakeven_move_bps():.0f} bps per round trip"}

    checks["tradeable size"] = {
        "passed": result.rejected_min_notional == 0,
        "detail": f"{result.rejected_min_notional} signal(s) below the "
                  f"{cost.min_notional} minimum notional were dropped"}

    if wf is not None:
        checks["out-of-sample consistency"] = {
            "passed": bool(wf["consistent"]),
            "detail": f"{wf['positive_folds']}/{wf['folds']} folds positive "
                      f"(p={wf.get('binomial_p', 1.0):.3f} under the null; needs <=0.05), "
                      f"mean {wf['mean_return']:+.2%}, worst {wf['worst_fold']:+.2%}"}
    else:
        checks["out-of-sample consistency"] = {
            "passed": False,
            "detail": "NOT RUN -- an in-sample-only result is not evidence"}

    return GuardrailVerdict(passed=all(c["passed"] for c in checks.values()),
                            checks=checks)


# ---------------------------------------------------------------------------
# Edge decay
# ---------------------------------------------------------------------------

class EdgeMonitor:
    """Watches a live strategy against the distribution its backtest implied.

    An edge is a claim about the future made from the past, and it expires.
    This does not ask "is live profitable" -- a losing streak inside the
    backtest's own distribution is expected and means nothing. It asks whether
    live results have become IMPLAUSIBLE under that distribution, which is a
    different and much later question, and it acts when the answer is yes.
    """

    def __init__(self, expected_mean: float, expected_sd: float,
                 window: int = 60, z_kill: float = -2.5,
                 max_consecutive_losses: int = 12):
        if expected_sd <= 0:
            raise ValueError("expected_sd must be positive")
        self.expected_mean = expected_mean
        self.expected_sd = expected_sd
        self.window = window
        self.z_kill = z_kill
        self.max_consecutive_losses = max_consecutive_losses
        self.live: List[float] = []
        self.killed = False
        self.kill_reason = ""

    def record(self, ret: float) -> Dict[str, Any]:
        self.live.append(ret)
        w = self.live[-self.window:]
        state: Dict[str, Any] = {"n": len(self.live), "killed": self.killed}
        if self.killed:
            state["reason"] = self.kill_reason
            return state

        streak = 0
        for r in reversed(self.live):
            if r < 0:
                streak += 1
            else:
                break
        state["loss_streak"] = streak
        if streak >= self.max_consecutive_losses:
            self.killed = True
            self.kill_reason = (f"{streak} consecutive losing periods, at or past the "
                                f"{self.max_consecutive_losses} limit")
            state.update(killed=True, reason=self.kill_reason)
            return state

        if len(w) >= max(10, self.window // 2):
            se = self.expected_sd / math.sqrt(len(w))
            z = (statistics.fmean(w) - self.expected_mean) / se if se else 0.0
            state["z"] = z
            if z <= self.z_kill:
                self.killed = True
                self.kill_reason = (f"rolling mean is {z:.2f} SD below the backtest "
                                    f"expectation over {len(w)} periods -- live results "
                                    f"are no longer explicable by the backtest")
                state.update(killed=True, reason=self.kill_reason)
        return state


# ---------------------------------------------------------------------------
# Paper trading
# ---------------------------------------------------------------------------

class PaperTrader:
    """Forward testing with SEALED predictions.

    The rule that makes paper trading meaningful: the decision is recorded
    BEFORE the outcome bar exists, and is immutable afterwards. Paper trading
    that lets you revise or reinterpret a call after seeing the result is a
    backtest with extra steps and worse data.

    It also holds the backtest's own expectation, so live is compared against
    what was actually claimed rather than against a memory of it.
    """

    def __init__(self, cost: Optional[CostModel] = None, capital: float = 12.0,
                 monitor: Optional[EdgeMonitor] = None):
        self.cost = cost or CostModel()
        self.capital = capital
        self.monitor = monitor
        self.sealed: List[Dict[str, Any]] = []
        self.settled: List[Dict[str, Any]] = []
        self.equity = capital

    def seal(self, ts: float, target: int, ref_px: float, note: str = "") -> int:
        if target not in (-1, 0, 1):
            raise ValueError("target must be -1, 0 or +1")
        self.sealed.append({"ts": ts, "target": target, "ref_px": ref_px,
                            "note": note, "settled": False})
        return len(self.sealed) - 1

    def settle(self, idx: int, exit_px: float) -> Dict[str, Any]:
        s = self.sealed[idx]
        if s["settled"]:
            raise ValueError(f"prediction {idx} is already settled; a sealed call "
                             f"cannot be re-scored after the fact")
        side = s["target"]
        if side == 0:
            s["settled"] = True
            rec = {"idx": idx, "pnl": 0.0, "ret": 0.0, "flat": True}
        else:
            entry = self.cost.fill_price(s["ref_px"], side)
            exit_ = self.cost.fill_price(exit_px, -side)
            pnl = side * (exit_ - entry) * (self.capital / entry) - self.cost.fee(self.capital) * 2
            self.equity += pnl
            s["settled"] = True
            rec = {"idx": idx, "pnl": pnl, "ret": pnl / self.capital, "flat": False}
        self.settled.append(rec)
        if self.monitor is not None:
            rec["monitor"] = self.monitor.record(rec["ret"])
        return rec

    def summary(self) -> Dict[str, Any]:
        rets = [r["ret"] for r in self.settled]
        wins = sum(1 for r in rets if r > 0)
        return {"sealed": len(self.sealed), "settled": len(self.settled),
                "equity": self.equity,
                "total_return": (self.equity / self.capital) - 1.0,
                "win_rate": wins / len(rets) if rets else 0.0,
                "killed": bool(self.monitor and self.monitor.killed),
                "kill_reason": self.monitor.kill_reason if self.monitor else ""}


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_csv(path: str, ts_col: str = "timestamp", o: str = "open", h: str = "high",
             l: str = "low", c: str = "close", v: str = "volume") -> List[Bar]:
    """Load real OHLCV. Validates rather than trusting: a bar whose high is
    below its low, or whose close sits outside its own range, is corrupt data
    and will silently distort every result computed from it."""
    import csv as _csv
    bars: List[Bar] = []
    with open(path) as fh:
        for n, row in enumerate(_csv.DictReader(fh), start=2):
            try:
                b = Bar(float(row[ts_col]) if str(row[ts_col]).replace(".", "").isdigit()
                        else float(n),
                        float(row[o]), float(row[h]), float(row[l]),
                        float(row[c]), float(row.get(v, 0) or 0))
            except (KeyError, ValueError) as e:
                raise ValueError(f"{path} line {n}: {e}")
            if b.high < b.low or not (b.low <= b.close <= b.high) or not (b.low <= b.open <= b.high):
                raise ValueError(
                    f"{path} line {n}: incoherent bar (o={b.open} h={b.high} "
                    f"l={b.low} c={b.close}). Refusing to backtest on corrupt data.")
            bars.append(b)
    if len(bars) < 2:
        raise ValueError(f"{path} yielded {len(bars)} bars")
    return bars
