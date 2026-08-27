#!/usr/bin/env python3
"""
guards.py -- circuit breakers. The part we had none of.

WHAT THIS IS AND WHY IT IS THE HIGHEST-VALUE ADDITION
  The rules so far answer "what should I hold?" Nothing answers "should I be
  trading at all right now?" Freqtrade ships a whole subsystem for that
  (protections: MaxDrawdown, StoplossGuard, CooldownPeriod, LowProfitPairs) and
  it is the piece most retail setups skip, because it never makes money -- it
  only stops you losing it faster.

  It needs no forecast. Every guard here is arithmetic on your own history.
  That matters because the one thing established across this whole project is
  that prediction did not survive out-of-sample while risk control replicated.
  This is more risk control.

DESIGN RULES
  * FAIL CLOSED. A guard that cannot evaluate BLOCKS. Same posture as the
    ethics gate: silence is not consent.
  * Guards only ever block BUYS. They never force a sale. A circuit breaker
    that liquidates you at the bottom is worse than the loss it was stopping.
  * Every block states the number that triggered it, so you can argue with the
    threshold instead of guessing at the reason.
"""
from __future__ import annotations
import json, os, time
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Verdict:
    allowed: bool
    guard: str
    reason: str


@dataclass
class State:
    """Everything the guards reason over. All of it is your own history."""
    equity_now: float
    equity_peak: float
    equity_start_of_day: float
    closed_trades: list          # [{sym, pnl, closed_at}] newest last
    last_sold: dict              # {sym: unix_ts}
    positions: dict              # {sym: value}
    cash: float
    now: float = field(default_factory=time.time)

    @property
    def total(self) -> float:
        return sum(self.positions.values()) + self.cash


class Guard:
    name = "guard"
    def check(self, st: State, sym: Optional[str] = None) -> Verdict:
        raise NotImplementedError


class MaxDrawdown(Guard):
    """Stop buying once the account is this far below its own high-water mark.

    Not a stop-loss -- it does not sell. It stops you adding while things are
    going against you, which is exactly when the urge to average down peaks."""
    name = "max_drawdown"
    def __init__(self, pct: float = 0.25):
        self.pct = pct
    def check(self, st, sym=None):
        if st.equity_peak <= 0:
            return Verdict(False, self.name, "no peak recorded -- cannot evaluate, blocking")
        dd = (st.equity_peak - st.equity_now) / st.equity_peak
        if dd >= self.pct:
            return Verdict(False, self.name,
                           f"drawdown {dd:.1%} at/over limit {self.pct:.0%} "
                           f"(peak ${st.equity_peak:,.0f} -> now ${st.equity_now:,.0f})")
        return Verdict(True, self.name, f"drawdown {dd:.1%} under {self.pct:.0%}")


class DailyLossLimit(Guard):
    """One bad day should not become one bad day plus a revenge trade."""
    name = "daily_loss"
    def __init__(self, pct: float = 0.08):
        self.pct = pct
    def check(self, st, sym=None):
        if st.equity_start_of_day <= 0:
            return Verdict(False, self.name, "no start-of-day equity -- blocking")
        chg = (st.equity_now - st.equity_start_of_day) / st.equity_start_of_day
        if chg <= -self.pct:
            return Verdict(False, self.name,
                           f"down {abs(chg):.1%} today, limit {self.pct:.0%}")
        return Verdict(True, self.name, f"today {chg:+.1%}")


class CooldownPeriod(Guard):
    """After selling something, do not buy it back for N days.

    Sell-then-immediately-rebuy is the most common way a rules system turns
    into churn: the rule fires, the price ticks the other way, and you undo it
    an hour later having paid two fees to end up where you started."""
    name = "cooldown"
    def __init__(self, days: float = 7):
        self.secs = days * 86400
        self.days = days
    def check(self, st, sym=None):
        if sym is None:
            return Verdict(True, self.name, "not asset-specific")
        t = st.last_sold.get(sym)
        if t is None:
            return Verdict(True, self.name, f"{sym} not sold recently")
        age = st.now - t
        if age < self.secs:
            return Verdict(False, self.name,
                           f"{sym} sold {age/86400:.1f}d ago, cooldown {self.days:.0f}d")
        return Verdict(True, self.name, f"{sym} last sold {age/86400:.1f}d ago")


class LossStreak(Guard):
    """N losing closed trades in a window means the current approach is not
    working NOW. Pause rather than push."""
    name = "loss_streak"
    def __init__(self, n: int = 4, window_days: float = 30):
        self.n, self.window = n, window_days * 86400
    def check(self, st, sym=None):
        recent = [t for t in st.closed_trades if st.now - t.get("closed_at", 0) <= self.window]
        losses = [t for t in recent if t.get("pnl", 0) < 0]
        if len(losses) >= self.n:
            return Verdict(False, self.name,
                           f"{len(losses)} losing trades in {self.window/86400:.0f}d "
                           f"(limit {self.n})")
        return Verdict(True, self.name, f"{len(losses)}/{self.n} recent losses")


class ConcentrationCap(Guard):
    """No single position past this share. Blocks buys that would breach it."""
    name = "concentration"
    def __init__(self, pct: float = 0.20):
        self.pct = pct
    def check(self, st, sym=None):
        if sym is None:
            return Verdict(True, self.name, "not asset-specific")
        tot = st.total
        if tot <= 0:
            return Verdict(False, self.name, "no portfolio value -- blocking")
        w = st.positions.get(sym, 0.0) / tot
        if w >= self.pct:
            return Verdict(False, self.name,
                           f"{sym} already {w:.1%}, cap {self.pct:.0%}")
        return Verdict(True, self.name, f"{sym} at {w:.1%}")


class CashFloor(Guard):
    """Keep a buffer. Buying the floor away is how you end up forced to sell."""
    name = "cash_floor"
    def __init__(self, pct: float = 0.10):
        self.pct = pct
    def check(self, st, sym=None):
        tot = st.total
        if tot <= 0:
            return Verdict(False, self.name, "no portfolio value -- blocking")
        c = st.cash / tot
        if c < self.pct:
            return Verdict(False, self.name,
                           f"cash {c:.1%} below floor {self.pct:.0%}")
        return Verdict(True, self.name, f"cash {c:.1%}")


DEFAULTS = [MaxDrawdown(0.25), DailyLossLimit(0.08), CooldownPeriod(7),
            LossStreak(4, 30), ConcentrationCap(0.20), CashFloor(0.10)]


class GuardStack:
    """Evaluates every guard and reports ALL blocks, not just the first.

    Short-circuiting on the first failure hides the rest, so you fix one thing,
    rerun, hit the next, and never see the shape of the problem."""
    def __init__(self, guards: Optional[List[Guard]] = None):
        self.guards = guards if guards is not None else DEFAULTS

    def evaluate(self, st: State, sym: Optional[str] = None):
        out = []
        for g in self.guards:
            try:
                out.append(g.check(st, sym))
            except Exception as e:
                out.append(Verdict(False, g.name,
                                   f"guard raised {type(e).__name__}: {e} -- blocking"))
        return out

    def may_buy(self, st: State, sym: str):
        v = self.evaluate(st, sym)
        blocks = [x for x in v if not x.allowed]
        return (len(blocks) == 0), blocks, v

    def report(self, st: State, sym: Optional[str] = None):
        v = self.evaluate(st, sym)
        tag = f" for {sym}" if sym else ""
        print(f"  GUARDS{tag}")
        for x in v:
            print(f"    [{'ok  ' if x.allowed else 'BLOCK'}] {x.guard:<14} {x.reason}")
        blocks = [x for x in v if not x.allowed]
        print(f"    -> buying {'ALLOWED' if not blocks else 'BLOCKED by ' + ', '.join(b.guard for b in blocks)}")
        return not blocks
