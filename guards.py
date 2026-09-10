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
  * NO GUARD EVER FORCES A SALE. A circuit breaker that liquidates you at the
    bottom is worse than the loss it was stopping. This is the rule; the one
    below used to be stated in its place and is not the same claim.
  * Most guards block BUYS ONLY, and callers apply them that way -- see
    covenant_trader.preconditions(). Two do not, and both were added
    2026-09-04, so the older wording ("guards only ever block buys") is no
    longer true and has been corrected rather than left as a comment that
    quietly disagrees with the code:
      - ReserveFloor blocks a SELL that would cross the reserved half. Refusing
        to sell is not forcing a sale, so it keeps the rule above.
      - PerTradeCap and PerDayCap apply to EVERY order. They are throughput
        limits, and a runaway loop selling costs the same 100 bps a round trip
        as one buying, so restricting them to buys would leave the hole open on
        the side the planner actually emits.
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
    quantities: dict = field(default_factory=dict)   # {sym: units held now}
    reserve_baseline: dict = field(default_factory=dict)  # {sym: units at the day the floor was set}
    # Orders already placed TODAY: [{usd: float}, ...]. None is not the same as
    # []: an empty list means "none placed, and I know that", None means "I
    # could not find out", and the cap guards block on the second. The
    # distinction is the whole reason this is not a plain default_factory.
    orders_today: Optional[list] = None
    # The buy budget's two numbers, both Optional for the same reason
    # orders_today is: None means "could not be established", and the guard
    # blocks on that rather than assuming a convenient zero.
    starting_total_usd: Optional[float] = None   # the book when the floor was set
    bought_total_usd: Optional[float] = None     # cumulative buy notional since
    # Fiat-funded buys in the trailing seven days: [{at: unix_ts, usd: float}].
    # None means "could not be established" and WeeklyBudget blocks on it.
    fiat_buys_week: Optional[list] = None
    now: float = field(default_factory=time.time)

    @property
    def total(self) -> float:
        return sum(self.positions.values()) + self.cash


class Guard:
    name = "guard"
    # WHICH ORDERS THIS GUARD CONSTRAINS: "buy", "sell", or "both".
    #
    # This used to be prose in the header and nothing in the code, and the cost
    # of that showed up on 2026-09-04. ReserveFloor is a SELL-side rule -- half
    # of every coin may not be sold, and XRP may not be sold at all -- but it
    # sits in DEFAULTS, and may_buy() asked every guard in DEFAULTS. Before
    # hold-only existed it happened to answer "no baseline recorded, no claim"
    # on the buy path and the muddle was invisible. The moment XRP became
    # hold-only it started refusing to BUY XRP, which is not the rule and is
    # not what anybody asked for: "may not be sold" is not "may not be bought".
    #
    # So the side is declared, may_buy() honours it, and evaluate() still
    # reports every guard -- the operator should see the reserve line whether
    # or not it bears on the question being asked.
    side = "buy"

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


# HOLD-ONLY ASSETS. Asked 2026-09-04: "50 percent of current holdings
# excluding xrp can be sold and rebought". XRP is not half-reserved, it is
# wholly reserved -- the standing instruction on it has been hold-only since
# this account was first described, and the sentence above says "excluding"
# rather than "including at fifty percent". Nothing here may sell any part of
# it, and no rule in this program can add to this tuple: removing a symbol from
# it is an operator's edit, in the open, like every other loosening.
#
# REDEFINED 2026-09-07. Asked, in two messages: "everything except hbar
# chainlink and xrp can be considered available balance for trading", then
# "hold the current amount able to add and use for trading", confirmed as:
# today's quantity is a FLOOR, more may be bought, and everything above the
# floor is tradeable.
#
# So these three are no longer "never sellable". They are FULLY RESERVED AT
# THE BASELINE: reserved_pct is 1.0 of the recorded baseline where every other
# asset reserves 0.50 of it. Held == baseline (the case today) still means zero
# sellable, which is why this reads the same from outside until something is
# added. The difference appears the moment more is bought.
#
# AND THE FLOOR DOES NOT FOLLOW A PURCHASE UP. For a 50%-reserved asset,
# buying more raises the baseline -- half of a bigger holding is a bigger
# floor, which is the rule that was asked for in September. Applying that here
# would make "able to add and use for trading" impossible: every coin added
# would raise the floor above itself and be locked on arrival. So
# covenant_trader.reserve_baseline() freezes the baseline for these symbols.
# That is the whole content of "hold the CURRENT amount".
#
# WHAT THIS DOES NOT BIND. The operator, who said "unless i choose to sell
# myself". Every floor in this file constrains the PROGRAM's rules. Nothing
# here reaches his own hands at the exchange, and nothing should.
HOLD_ONLY = ("XRP", "HBAR", "LINK")

# The fraction of the BASELINE reserved for a HOLD_ONLY symbol. One, not a
# half: the whole of what he holds today stays put.
FULL_RESERVE_PCT = 1.0


def reserved_pct(sym, pct=0.50, hold_only=None):
    """The fraction of `sym`'s baseline that no rule may sell into."""
    return (FULL_RESERVE_PCT
            if sym in (HOLD_ONLY if hold_only is None else hold_only)
            else float(pct))


def sellable_units(held, base, sym, pct=0.50, hold_only=None):
    """Units of `sym` that may still be sold. The ONE implementation.

    covenant_trader's planner used to compute this inline with its own copy of
    the arithmetic, which is how the per-trade and per-day caps came to be
    enforced in one place and invisible in the other. Both call this now."""
    full = sym in (HOLD_ONLY if hold_only is None else hold_only)
    if base is None or held is None:
        # A fully-reserved asset with no recorded baseline FAILS CLOSED: with
        # no floor there is no "above the floor", so nothing of it is sellable.
        # Zero here is KNOWN and is not None -- None means "no claim either
        # way" and would let a caller fall through to its own default.
        return 0.0 if full else None
    return max(0.0, held - base * reserved_pct(sym, pct, hold_only))


class ReserveFloor(Guard):
    """Half of every coin is not for sale, and XRP is not for sale at all.

    Asked 2026-09-04: "50% of every current coin should be off limits", and
    then "50 percent of current holdings excluding xrp can be sold and
    rebought".

    THE RATCHET, which is why the baseline is FIXED AND STORED. Read the rule
    as "half of what I hold right now", evaluated per order, and it permits
    selling everything: sell half of 100 and 50 remain, then half of 50, then
    half of 25. Eight orders and the position is 0.4 units, and no single
    order ever broke the rule. A floor that moves down with the balance it is
    protecting is not a floor.

    So the baseline is written once to ops/RESERVE.json and the floor is half
    of THAT, not half of whatever is left. Selling can take a holding from 100
    to 50 and no further, whatever route it takes and however many orders it
    uses.

    RAISING the baseline is allowed -- buying more raises what half means, and
    a floor that ignored new coin would be a different rule than the one
    asked for. LOWERING it is not, because that is the ratchet wearing a
    different hat, and this class refuses to do it. Moving a floor down is an
    operator's decision, made by editing ops/RESERVE.json, where it leaves a
    mark.
    """
    name = "reserve_floor"
    side = "sell"          # it refuses SALES; it has never had a view on buying

    def __init__(self, pct: float = 0.50, hold_only=None):
        self.pct = float(pct)
        self.hold_only = tuple(HOLD_ONLY if hold_only is None else hold_only)

    def check(self, st, sym=None):
        if sym is None:
            return Verdict(True, self.name, "no symbol named; nothing to reserve")
        full = sym in self.hold_only
        base = (st.reserve_baseline or {}).get(sym)
        held = (st.quantities or {}).get(sym)
        if base is None or held is None:
            if full:
                return Verdict(False, self.name,
                               "%s is hold-only and has no recorded baseline, so "
                               "there is no floor to be above -- refusing" % sym)
            return Verdict(True, self.name,
                           f"{sym}: no baseline recorded, so this guard makes no claim")
        pct = reserved_pct(sym, self.pct, self.hold_only)
        floor = base * pct
        label = "hold-only: 100%% of the %.8g baseline" % base if full else                 "%.0f%% of the %.8g baseline" % (pct * 100, base)
        if held <= floor + 1e-12:
            return Verdict(False, self.name,
                           f"{sym}: {held:.8g} held is at or below the reserved "
                           f"{floor:.8g} ({label}) -- no sell may cross it")
        return Verdict(True, self.name,
                       f"{sym}: {held:.8g} held, {floor:.8g} reserved ({label}), "
                       f"{held - floor:.8g} sellable")

    @staticmethod
    def sellable(st, sym, pct=0.50, hold_only=None):
        """Units that may still be sold without touching the reserve. This is
        what a sizing rule must clamp to -- the check above refuses an order
        that starts below the floor, and this stops one from ending below it.
        A hold-only symbol reserves 100% of its baseline rather than 50%, so
        this returns whatever is held ABOVE that baseline -- zero while the
        holding is exactly the amount that was frozen, which is not the same as
        None: it is known, and it is none."""
        return sellable_units((st.quantities or {}).get(sym),
                              (st.reserve_baseline or {}).get(sym),
                              sym, pct, hold_only)


# ------------------------------------------------------------------ the caps
# WHY THESE ARE GUARDS AND NOT JUST CONFIG, added 2026-09-04 on request.
#
# The three numbers already existed -- max_order_usd, max_daily_notional_usd
# and max_orders_per_day are in trader_config.json and covenant_trader.py has
# enforced them since it was written. The problem was WHERE. They lived in one
# function, `preconditions()`, in the file that places orders. daily.py -- the
# report an operator actually reads every morning, which runs this guard stack
# and prints "may add" -- knew nothing about them. Two enforcement points, one
# of them blind, and the blind one is the one a person looks at.
#
# Moving them here gives them the two properties the rest of this file has:
# they FAIL CLOSED when they cannot evaluate, and they state the number that
# triggered them. covenant_trader.preconditions() now asks these classes
# instead of doing the arithmetic again, so there is one implementation.
#
# WHAT THE DAILY CAP IS FOR, which is not what DailyLossLimit is for.
# DailyLossLimit watches EQUITY, so it sees a bad day. It cannot see a runaway
# loop: a scheduler that fires every hour, or a planner that re-proposes the
# same order, can place many small orders that each pass every other guard and
# move equity very little per trade -- while the round trip costs 100 bps.
# Four orders a day at the shipped $300 daily cap is $1,200 of notional a
# month, which on a book this size is roughly 18% a year paid to the exchange
# before any market move at all. The cap is a cost control, and a bug control.
CAP_DEFAULTS = {
    "max_order_usd": 100.0,
    "max_daily_notional_usd": 300.0,
    "max_orders_per_day": 4,
    "min_order_usd": 5.0,
    # R6 contribution (2026-09-06): dollars the trader may put to work in any
    # trailing seven days. 0 is the shipped default and means NO contribution
    # path -- the operator sets the number in trader_config.json.
    "weekly_fiat_budget_usd": 0.0,
}
# Not a number, so it is not in caps() -- but it is read the same way and from
# the same file, and it defaults to the refusing answer.
ALLOW_FIAT_KEY = "allow_fiat_buys"
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "trader_config.json")


def caps(path: Optional[str] = None) -> dict:
    """The operator's caps, or the shipped defaults where the file is silent.

    trader_config.json is deliberately NOT shipped -- it carries `armed`, and
    it is per-operator runtime state -- so this must work without it, and a
    missing file means "use the defaults", never a crash. A present file with a
    missing key means the same for that key."""
    out = dict(CAP_DEFAULTS)
    try:
        with open(path or CONFIG_PATH, encoding="utf-8") as fh:
            cfg = json.load(fh)
        if isinstance(cfg, dict):
            for k in out:
                if isinstance(cfg.get(k), (int, float)):
                    out[k] = cfg[k]
    except (OSError, ValueError):
        pass
    return out


def fiat_buys_week_from(trader_state: Optional[dict], now: Optional[float] = None):
    """Fiat-funded buys in the trailing seven days out of covenant_trader's
    state file, for guards.WeeklyBudget. None if the state is unknown (a
    reader that cannot see the week must not assume it is empty); a state
    with no record yet is a KNOWN empty week."""
    if trader_state is None or not isinstance(trader_state, dict):
        return None
    t = now if now is not None else time.time()
    got = trader_state.get("fiat_buys", [])
    if not isinstance(got, list):
        return None
    out = []
    for r in got:
        try:
            if t - float(r.get("at", 0)) <= 7 * 86400:
                out.append({"at": float(r.get("at", 0)), "usd": float(r["usd"])})
        except (TypeError, ValueError, KeyError, AttributeError):
            return None
    return out


def orders_today_from(trader_state: Optional[dict], now: Optional[float] = None):
    """The day's orders out of covenant_trader's state file, or None if unknown.

    APPLIES THE SAME ROLLOVER covenant_trader.roll_day() does. The trader clears
    orders_today when the stored day is not today, and a reader that skips that
    step counts yesterday's orders against this morning -- which blocks rather
    than admits, so it is safe, but it is still wrong, and it would block every
    morning until the trader next ran.

    A state file that does not exist is not unknown: the trader has never run,
    so no orders have been placed, and that is a KNOWN zero."""
    if trader_state is None:
        return None
    if not isinstance(trader_state, dict):
        return None
    day = time.strftime("%Y-%m-%d", time.localtime(now if now is not None else time.time()))
    if trader_state.get("day") != day:
        return []
    got = trader_state.get("orders_today")
    return list(got) if isinstance(got, list) else None


# covenant_trader.py owns this path and this env var. It is repeated rather
# than imported because covenant_trader imports daily, daily imports guards,
# and guards importing covenant_trader would close the loop. A test pins the
# two against each other so they cannot drift apart quietly.
TRADER_STATE = os.environ.get("COVENANT_TRADER_STATE") or os.path.join(
    os.path.expanduser("~"), ".covenant", "trader_state.json")


def fiat_buys_week_now(path: Optional[str] = None, now: Optional[float] = None):
    """The trailing week's fiat-funded buys straight off disk, for WeeklyBudget.
    Same contract as orders_today_now: a missing file is a KNOWN empty week
    (the trader has never run), a file that will not parse is unknown."""
    p = path or TRADER_STATE
    if not os.path.exists(p):
        return []
    try:
        with open(p, encoding="utf-8") as fh:
            return fiat_buys_week_from(json.load(fh), now)
    except (OSError, ValueError):
        return None


def orders_today_now(path: Optional[str] = None, now: Optional[float] = None):
    """The day's orders straight off disk: a list, or None if it cannot be told.

    A MISSING FILE IS A KNOWN ZERO, not an unknown. The trader writes its state
    the first time it runs; if the file is not there it has never run, so it has
    placed no orders, and blocking on that would mean the caps refuse every
    order until the caps have already been used once. A file that exists but
    will not parse IS unknown, and that blocks."""
    p = path or TRADER_STATE
    if not os.path.exists(p):
        return []
    try:
        with open(p, encoding="utf-8") as fh:
            return orders_today_from(json.load(fh), now)
    except (OSError, ValueError):
        return None


def allow_fiat_buys(path: Optional[str] = None) -> bool:
    """Has the operator permitted buying with dollars? Default NO.

    Asked 2026-09-04: "not from fiat without permission". Absent, unreadable
    and malformed all mean no, which is the same posture `armed` takes -- a
    permission that can be granted by a missing file is not a permission."""
    try:
        with open(path or CONFIG_PATH, encoding="utf-8") as fh:
            return json.load(fh).get(ALLOW_FIAT_KEY) is True
    except (OSError, ValueError, AttributeError):
        return False


def bought_total_now(path: Optional[str] = None) -> Optional[float]:
    """Lifetime buy notional out of the trader's state, or None if unknown.

    A MISSING FILE IS A KNOWN ZERO, for the same reason orders_today_now()
    treats it that way: the trader has never run, so it has bought nothing. A
    file that exists and does not carry the figure IS unknown -- it was written
    by a build that did not keep the total, and guessing zero for it would hand
    back a whole budget that may already have been spent."""
    p = path or TRADER_STATE
    if not os.path.exists(p):
        return 0.0
    try:
        with open(p, encoding="utf-8") as fh:
            v = json.load(fh).get("bought_total_usd")
        return float(v) if isinstance(v, (int, float)) and v >= 0 else None
    except (OSError, ValueError, TypeError):
        return None


def _proceeds(orders):
    """(raised by selling today, spent buying today), or None if a side is
    unreadable. An order whose side is not recorded cannot be counted on
    either line, and guessing which would be the whole question."""
    sold = bought = 0.0
    for o in orders:
        if not isinstance(o, dict):
            return None
        side = str(o.get("side", "")).lower()
        try:
            usd = float(o.get("usd"))
        except (TypeError, ValueError):
            return None
        if side == "sell":
            sold += usd
        elif side == "buy":
            bought += usd
        else:
            return None
    return sold, bought


def _spent(orders):
    """Notional placed today, or None if any entry's size cannot be read.

    An order whose amount is unreadable is not worth zero. It is an order that
    happened for an unknown amount, and the file's first design rule says a
    guard that cannot evaluate blocks -- so the sum goes unknown and the caps
    refuse, rather than quietly counting a possibly-large order as nothing.
    Found by F7's C9, which had asserted the opposite."""
    tot = 0.0
    for o in orders:
        if not isinstance(o, dict) or "usd" not in o:
            return None
        try:
            tot += float(o["usd"])
        except (TypeError, ValueError):
            return None
    return tot


class PerDayCap(Guard):
    """How much may be traded in one day, by count and by notional.

    Blocks on history alone -- it needs no proposed order. Once the count is
    used up or the notional is spent, nothing more goes today, and the guard
    says which of the two stopped it."""
    name = "per_day_cap"
    side = "both"          # a throughput limit: a runaway loop selling costs
                           # the same 100 bps a round trip as one buying

    def __init__(self, max_orders: Optional[int] = None,
                 max_notional: Optional[float] = None,
                 config_path: Optional[str] = None):
        # WHAT WAS PASSED IS KEPT; WHAT WAS NOT IS READ AT EVERY CHECK.
        # DEFAULTS is built at import, so resolving the config here would
        # freeze the caps at start-up -- and covenant_trader --loop runs for
        # days. An operator who tightens a cap mid-run should have it apply on
        # the next cycle rather than the next restart, and tightening is
        # exactly the edit someone makes in a hurry. Explicit arguments still
        # win, so a test can pin fixed numbers.
        self._max_orders, self._max_notional = max_orders, max_notional
        self._config_path = config_path

    @property
    def max_orders(self):
        c = caps(self._config_path)
        return int(c["max_orders_per_day"] if self._max_orders is None
                   else self._max_orders)

    @property
    def max_notional(self):
        c = caps(self._config_path)
        return float(c["max_daily_notional_usd"] if self._max_notional is None
                     else self._max_notional)

    def check(self, st, sym=None):
        if st.orders_today is None:
            return Verdict(False, self.name,
                           "the day's orders are unknown (no trader state could be "
                           "read) -- cannot evaluate, blocking")
        n, spent = len(st.orders_today), _spent(st.orders_today)
        if n >= self.max_orders:
            return Verdict(False, self.name,
                           f"{n} order(s) already today, limit {self.max_orders}")
        if spent is None:
            return Verdict(False, self.name,
                           f"one of today's {n} order(s) records no readable amount "
                           f"-- the day's notional cannot be totalled, blocking")
        if spent >= self.max_notional:
            return Verdict(False, self.name,
                           f"${spent:,.2f} of notional already today, cap "
                           f"${self.max_notional:,.2f}")
        return Verdict(True, self.name,
                       f"{n}/{self.max_orders} orders, ${spent:,.2f}/"
                       f"${self.max_notional:,.2f} notional used today")


class PerTradeCap(Guard):
    """No single order over max_order_usd, and none under min_order_usd.

    THE SIZE OF A PROPOSED ORDER IS NOT IN State, deliberately -- State is the
    account's own history, and a guard that judged one order would have to be
    re-run per order with a different argument. So this follows ReserveFloor's
    shape: check() refuses the situation where no legal order EXISTS, and
    largest_allowed() is the number a sizing rule clamps to, which is what
    stops an order from ending over the line."""
    name = "per_trade_cap"
    side = "both"          # as above

    def __init__(self, max_usd: Optional[float] = None,
                 min_usd: Optional[float] = None,
                 max_orders: Optional[int] = None,
                 max_notional: Optional[float] = None,
                 config_path: Optional[str] = None):
        # Read at every check, not at construction -- see PerDayCap.__init__.
        self._max_usd, self._min_usd = max_usd, min_usd
        self._max_orders, self._max_notional = max_orders, max_notional
        self._config_path = config_path

    @property
    def max_usd(self):
        c = caps(self._config_path)
        return float(c["max_order_usd"] if self._max_usd is None else self._max_usd)

    @property
    def min_usd(self):
        c = caps(self._config_path)
        return float(c["min_order_usd"] if self._min_usd is None else self._min_usd)

    @property
    def max_orders(self):
        c = caps(self._config_path)
        return int(c["max_orders_per_day"] if self._max_orders is None
                   else self._max_orders)

    @property
    def max_notional(self):
        c = caps(self._config_path)
        return float(c["max_daily_notional_usd"] if self._max_notional is None
                     else self._max_notional)

    def largest_allowed(self, st) -> Optional[float]:
        """The biggest order that may be placed right now, or None if unknown.

        Both caps bind at once: the per-order ceiling, and whatever is left of
        today's notional. Returning the minimum is what makes many small orders
        unable to do what one large one may not -- the same ratchet ReserveFloor
        exists to stop, in the other direction."""
        if st.orders_today is None:
            return None
        if len(st.orders_today) >= self.max_orders:
            return 0.0
        spent = _spent(st.orders_today)
        if spent is None:
            return None
        return max(0.0, min(self.max_usd, self.max_notional - spent))

    def check(self, st, sym=None):
        room = self.largest_allowed(st)
        if room is None:
            why = ("the day's orders are unknown (no trader state could be read)"
                   if st.orders_today is None else
                   "one of today's orders records no readable amount")
            return Verdict(False, self.name, why + " -- cannot evaluate, blocking")
        if room < self.min_usd:
            return Verdict(False, self.name,
                           f"${room:,.2f} of headroom left, under the "
                           f"${self.min_usd:,.2f} minimum order -- nothing legal "
                           f"can be placed today")
        return Verdict(True, self.name,
                       f"orders capped at ${self.max_usd:,.2f}; ${room:,.2f} "
                       f"placeable now")


RESERVE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "private", "RESERVE.json")


def starting_total(path: Optional[str] = None) -> Optional[float]:
    """The book's value when the floor was set, or None if never recorded."""
    try:
        with open(path or RESERVE_PATH, encoding="utf-8") as fh:
            v = json.load(fh).get("starting_total_usd")
        return float(v) if isinstance(v, (int, float)) and v > 0 else None
    except (OSError, ValueError, TypeError):
        return None


def set_starting_total(total: float, path: Optional[str] = None) -> Optional[float]:
    """Record the starting book ONCE. Never overwrites; returns what stands.

    ONE WRITER: covenant_trader.py, from a real portfolio read. daily.py calls
    starting_total() and only reads.

    It was briefly both, and that was a defect worth recording rather than
    quietly correcting. daily.py is driven by test_d3_daily_guards.py with a
    fabricated $44 book, so a test run could have written the number that
    anchors this budget for ever. It did not, only because a real run happened
    to go first and this function never overwrites -- which is luck, not
    design. A figure that fixes how much of someone's money may be spent is not
    something a program should settle from whatever it happened to read on a
    Tuesday, and it is certainly not something a test should be able to set.

    It never raises the number either, which is the opposite of what
    reserve_baseline() does for per-asset quantities and is deliberate. That
    baseline rises when more coin is bought, because the rule is "half of every
    coin". This one is "half of the STARTING amount", and a starting amount
    that grows is not a starting amount. If money is deposited and the budget
    should grow with it, that is an operator's edit to private/RESERVE.json,
    where it leaves a mark."""
    have = starting_total(path)
    if have is not None:
        return have
    # "NEVER RECORDED" AND "CANNOT BE READ" BOTH ARRIVE HERE AS None. A78
    # (2026-09-10). starting_total() returns None for an absent file, for an
    # absent key, AND for a file that will not parse -- and only the first two
    # mean "not set yet". On the third, the write below rebuilds `data` from
    # {} and persists it, which deletes the reserve floors and re-anchors this
    # lifetime budget to today's book. Measured: one torn-file cycle turned
    # $100 of remaining buy budget into $2,100, and the new anchor was then
    # protected by the very "never overwrites" invariant that had just failed.
    #
    # Line 472 of this file already states the rule: a file that exists and
    # will not parse IS unknown, and that blocks. Returning None makes
    # BuyBudget.check refuse with its existing "no starting book value
    # recorded" verdict, which is the fail-closed direction.
    p = path or RESERVE_PATH
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as fh:
                if not isinstance(json.load(fh), dict):
                    raise ValueError("RESERVE.json is not an object")
        except (OSError, ValueError):
            return None
    if not (isinstance(total, (int, float)) and total > 0):
        return None
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        try:
            with open(p, encoding="utf-8") as fh:
                data = json.load(fh)
            if not isinstance(data, dict):
                data = {}
        except (OSError, ValueError):
            data = {}
        data["starting_total_usd"] = float(total)
        data.setdefault("_what", "")
        data["_what"] = (data["_what"] + " " if data["_what"] else "") + (
            "starting_total_usd is the book at the moment the floor was set; "
            "buying is capped at pct_buyable of it, cumulatively, for ever.")
        data.setdefault("pct_buyable", 0.50)
        # ATOMIC (A78). This is one of the two writers of RESERVE.json, and a
        # kill between open("w") and the last byte leaves a torn file that
        # both readers must now refuse. Do not manufacture the emergency you
        # fail closed on.
        tmp = p + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=1, sort_keys=True)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, p)
    except OSError:
        return None
    return float(total)


class BuyBudget(Guard):
    """Buying may spend half of what the book was worth at the start. Total.

    Asked 2026-09-04: "buys are allowed with 50% of starting amount", beside
    the earlier "50% of every current coin should be off limits". The two are
    the same shape from opposite ends -- half the book cannot be sold, and half
    of what it started at is what may be spent -- and they need the same
    defence, because "half of what I have now" ratchets in this direction too:
    spend half, and half of what remains is another spend, and the budget never
    runs out. So the baseline is the STARTING total, fixed and stored, and the
    spend is CUMULATIVE and never forgotten.

    WHAT COUNTS AGAINST IT IS NEW MONEY, NOT ROTATION. Asked and settled
    2026-09-04: "50 percent of current holdings excluding xrp can be sold and
    rebought to gain yield and purchase other assets". Selling XLM and buying
    SOL with those proceeds is the intended mechanism, so charging it to the
    budget would switch the mechanism off after about sixty-nine rotations at
    the $50 daily cap -- a cap that had never let a dollar in. So the figure
    accumulated is the FIAT portion of each buy: whatever part of it was not
    covered by that day's sale proceeds. A rotation adds nothing.

    That keeps it un-gameable in the way that matters. Each dollar that enters
    the book is counted once and never forgotten, and no sequence of sells and
    buys can spend a dollar twice. Reaching the end means half the STARTING
    book has been put in, which is the point at which someone should look up
    rather than continue. Raising it is an operator's edit to
    private/RESERVE.json.

    BUYS ONLY. It never touches a sale: refusing to let someone stop is not
    something this file does."""
    name = "buy_budget"

    def __init__(self, pct: float = 0.50, reserve_path: Optional[str] = None):
        self.pct = float(pct)
        self._reserve_path = reserve_path

    def remaining(self, st) -> Optional[float]:
        """Budget left to spend on buys, or None if it cannot be told. A sizing
        rule clamps to this -- check() refuses a purchase once the budget is
        gone, and this stops one from going past the end of it."""
        start = (st.starting_total_usd if st.starting_total_usd is not None
                 else starting_total(self._reserve_path))
        if start is None or st.bought_total_usd is None:
            return None
        return max(0.0, start * self.pct - float(st.bought_total_usd))

    def check(self, st, sym=None):
        start = (st.starting_total_usd if st.starting_total_usd is not None
                 else starting_total(self._reserve_path))
        if start is None:
            return Verdict(False, self.name,
                           "no starting book value recorded in private/RESERVE.json, "
                           "so the buy budget cannot be evaluated -- blocking. It is "
                           "written on the first run that can read the portfolio.")
        if st.bought_total_usd is None:
            return Verdict(False, self.name,
                           "the cumulative amount already spent on buys is unknown "
                           "(no trader state could be read) -- cannot evaluate, blocking")
        budget = start * self.pct
        spent = float(st.bought_total_usd)
        if spent >= budget:
            return Verdict(False, self.name,
                           f"${spent:,.2f} spent on buys against a ${budget:,.2f} budget "
                           f"({self.pct:.0%} of the ${start:,.2f} starting book) -- "
                           f"the budget is used up")
        return Verdict(True, self.name,
                       f"${budget - spent:,.2f} of the ${budget:,.2f} buy budget left "
                       f"({self.pct:.0%} of the ${start:,.2f} starting book)")


class FiatBuyPermission(Guard):
    """Rotating crypto you already hold is not the same act as spending dollars.

    Asked 2026-09-04: "not from fiat without permission", alongside "buys are
    allowed with 50% of starting amount" and the older "can buy but can't
    withdraw from my bank".

    The distinction is real and the program can see it, but only if it wrote
    down which side each order was. Selling XLM and buying SOL with the
    proceeds moves value between assets already owned; buying SOL out of the
    dollar balance spends money. From a balance sheet alone the two look
    identical, which is why covenant_trader now records `side` on every booked
    order -- so "funded by today's sales" is a number rather than a guess.

    So: a buy is permitted up to what selling raised today and has not already
    been spent. Beyond that it is coming out of dollars, and it waits for
    permission -- `allow_fiat_buys: true` in trader_config.json, an operator's
    edit that leaves a mark, exactly like `armed`.

    THE HEADROOM IS TODAY'S, not all time. A rotation is a thing that happens
    within a session; treating a sale from three months ago as funding today's
    purchase would make "funded by sales" true of almost any buy, and the rule
    would mean nothing.

    BUYS ONLY, and it never forces a sale."""
    name = "fiat_permission"

    def __init__(self, config_path: Optional[str] = None):
        self._config_path = config_path

    def headroom(self, st) -> Optional[float]:
        """What may still be bought without touching dollars, or None if it
        cannot be told. Infinite (returned as None's opposite: a float) is not
        used -- when fiat is permitted the guard simply allows."""
        if st.orders_today is None:
            return None
        got = _proceeds(st.orders_today)
        if got is None:
            return None
        sold, bought = got
        return max(0.0, sold - bought)

    def check(self, st, sym=None):
        if allow_fiat_buys(self._config_path):
            return Verdict(True, self.name,
                           "buying with dollars is permitted in trader_config.json "
                           "(allow_fiat_buys)")
        if st.orders_today is None:
            return Verdict(False, self.name,
                           "the day's orders are unknown, so what selling raised "
                           "today cannot be told -- cannot evaluate, blocking")
        got = _proceeds(st.orders_today)
        if got is None:
            return Verdict(False, self.name,
                           "one of today's orders does not record which side it was, "
                           "so sale proceeds cannot be separated from spending -- "
                           "cannot evaluate, blocking")
        sold, bought = got
        room = sold - bought
        if room <= 0:
            return Verdict(False, self.name,
                           f"nothing left from today's sales to buy with "
                           f"(${sold:,.2f} raised, ${bought:,.2f} already spent) -- "
                           f"a purchase now comes out of dollars, and that needs "
                           f"allow_fiat_buys in trader_config.json")
        return Verdict(True, self.name,
                       f"${room:,.2f} of today's sale proceeds may be re-bought "
                       f"without spending dollars (${sold:,.2f} raised, "
                       f"${bought:,.2f} spent)")


class WeeklyBudget(Guard):
    """Dollars put to work in any trailing seven days may not exceed the
    operator's weekly figure (weekly_fiat_budget_usd in trader_config.json).

    Asked 2026-09-06: "a budget of 100 a week". This is the ceiling the R6
    contribution rule sizes itself under, and the backstop if it ever does
    not. Counts fiat-funded buys only -- a rotation funded by today's sales is
    not new money (FiatBuyPermission draws that line). Reads the figure at
    every check, like the other caps, so a mid-week edit applies next cycle.
    A budget of 0 -- the shipped default -- means R6 is off and this guard does
    not constrain; the other guards still apply to any buy."""
    name = "weekly_budget"
    side = "buy"
    WINDOW_S = 7 * 86400

    def __init__(self, budget: Optional[float] = None, config_path: Optional[str] = None):
        self._budget, self._config_path = budget, config_path

    @property
    def budget(self):
        c = caps(self._config_path)
        return float(c["weekly_fiat_budget_usd"] if self._budget is None else self._budget)

    def spent(self, st) -> Optional[float]:
        if st.fiat_buys_week is None:
            return None
        total = 0.0
        for r in st.fiat_buys_week:
            try:
                if st.now - float(r.get("at", 0)) <= self.WINDOW_S:
                    total += float(r["usd"])
            except (TypeError, ValueError, KeyError):
                return None
        return total

    def headroom(self, st) -> Optional[float]:
        s = self.spent(st)
        return None if s is None else max(0.0, self.budget - s)

    def check(self, st, sym=None):
        b = self.budget
        if b <= 0:
            # No budget means the R6 contribution path is off (it checks the
            # same number before emitting anything). It does not mean every
            # buy is forbidden: an operator adding by hand under the other
            # guards is not bound by a contribution schedule that does not exist.
            return Verdict(True, self.name,
                           "no weekly contribution budget set (R6 off) -- not constraining")
        s = self.spent(st)
        if s is None:
            return Verdict(False, self.name,
                           "the week's fiat buys are unknown (no readable record) -- blocking")
        if s >= b:
            return Verdict(False, self.name,
                           f"${s:,.2f} of the ${b:,.2f} weekly budget already used")
        return Verdict(True, self.name,
                       f"${s:,.2f}/${b:,.2f} of the weekly budget used, ${b - s:,.2f} left")


DEFAULTS = [MaxDrawdown(0.25), DailyLossLimit(0.08), CooldownPeriod(7),
            LossStreak(4, 30), ConcentrationCap(0.20), CashFloor(0.10),
            ReserveFloor(0.50), PerDayCap(), PerTradeCap(), BuyBudget(0.50),
            FiatBuyPermission(), WeeklyBudget()]


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
        """Whether SYM may be added to. Sell-side guards are not asked, because
        a rule about what may be sold has no view on what may be bought -- see
        Guard.side for the day that stopped being merely tidy."""
        buy_side = {g.name for g in self.guards if getattr(g, "side", "buy") != "sell"}
        v = self.evaluate(st, sym)
        blocks = [x for x in v if not x.allowed and x.guard in buy_side]
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


# ===========================================================================
# THE PRECONDITIONS. ONE IMPLEMENTATION, TWO CALLERS.       (2026-09-07)
#
# Until today covenant_trader.preconditions() was the only thing that knew
# what may go live, and it lived in the file that places orders. The other
# path to a real order -- sentinel_witness/tradeGate.js -> seal_service.py --
# reached covenant_trader.seal_decision() and nothing else, so it recorded a
# decision through the ethics gate and then applied NONE of: armed,
# TRADER_HALT, the per-trade and per-day caps, Rule 5, or the guard stack.
#
# That is the same split the caps had before 2026-09-04, when they were
# enforced in preconditions() and invisible to daily.py -- and it is the same
# fix: move the rule here, where both callers can ask it, and leave ONE
# implementation. The trader's copy was deleted in the same commit; a
# consolidation that leaves the old body behind has not consolidated anything.
#
# WHY THIS CAN ONLY TIGHTEN. The answer is built as
#     base reasons  +  caller-specific reasons          (APPEND ONLY)
# so a caller may add a reason to refuse and can never remove one. The trader
# adds nothing and therefore behaves exactly as before. The sentinel went from
# zero checks to all of them plus two of its own, and there is no expressible
# way for it to end up more permissive than the trader.
#
# WHY guards.py AND NOT covenant_trader.py. covenant_trader imports daily,
# daily imports guards; guards importing covenant_trader would close the loop.
# guards.py already repeats CONFIG_PATH and TRADER_STATE for that exact
# reason, and imports only json/os/time/dataclasses/typing, so this adds
# nothing to daily.py's dependency cone.
# ===========================================================================

HALT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "TRADER_HALT")


def load_config(path: Optional[str] = None) -> dict:
    """The whole trader config as a dict. Unreadable or malformed reads as {},
    which makes `armed` false -- the posture allow_fiat_buys() already takes."""
    try:
        with open(path or CONFIG_PATH, encoding="utf-8") as fh:
            cfg = json.load(fh)
        return cfg if isinstance(cfg, dict) else {}
    except (OSError, ValueError):
        return {}


def load_trader_state(path: Optional[str] = None):
    """covenant_trader's state, or None if it exists and will not parse.

    A MISSING FILE IS A KNOWN EMPTY STATE, not an unknown one -- the rule
    orders_today_now() already applies, for the same reason: the trader writes
    this the first time it runs, and treating "never run" as unknown would
    block every order until one had already been placed."""
    p = path or TRADER_STATE
    if not os.path.exists(p):
        return {}
    try:
        with open(p, encoding="utf-8") as fh:
            st = json.load(fh)
        return st if isinstance(st, dict) else None
    except (OSError, ValueError):
        return None


def preconditions(order, cfg=None, st=None, sealed_ok=None, guard_blocks=None,
                  caller="trader", config_path=None, state_path=None, now=None):
    """Every reason THIS order may not go live. Empty list means clear.

    order        {"side": "buy"|"sell", "usd": float, "sym": str}
    cfg / st     loaded from disk when None
    sealed_ok    True  -- already sealed and admitted
                 False -- sealing was attempted and refused
                 None  -- THE CALLER SEALS AFTER THIS AND ANDS THE ANSWER
                          ITSELF. Only False produces the "not sealed" reason,
                          because a caller that gates before it seals would
                          otherwise deadlock: seal_required is true and at gate
                          time the seal has not happened. A caller that passes
                          None owes the conjunction. seal_service.py does NOT
                          use this -- it seals first and passes the real
                          answer -- but the reading has to exist, or the order
                          of the two steps becomes load-bearing.
    guard_blocks the guard stack's blocking reasons, or None for "the guard
                 stack could not be evaluated" -- which is NOT the same as [].
    caller       "trader" or "sentinel". Adds reasons, never removes them.
    """
    bad = []
    cfg = load_config(config_path) if cfg is None else cfg
    if st is None:
        st = load_trader_state(state_path)
    if st is None:
        bad.append("trader state exists but will not parse -- the day's order "
                   "count and Rule 5 cannot be read, so nothing may go live")
        st = {}

    if not cfg.get("armed"):
        bad.append("armed=false in trader_config.json")
    if os.path.exists(HALT):
        bad.append("TRADER_HALT file present")

    # THE CAPS ARE GUARDS, and this asks them rather than repeating their
    # arithmetic. A number absent from cfg falls back through caps() to the
    # shipped default, so a caller handing in a partial config still gets a
    # cap rather than none.
    c = caps(config_path)

    def _n(key):
        v = cfg.get(key)
        return v if isinstance(v, (int, float)) else c[key]

    gs = State(equity_now=0.0, equity_peak=0.0, equity_start_of_day=0.0,
               closed_trades=[], last_sold={}, positions={}, cash=0.0,
               orders_today=orders_today_from(st, now))
    per_trade = PerTradeCap(max_usd=_n("max_order_usd"), min_usd=_n("min_order_usd"),
                            max_orders=_n("max_orders_per_day"),
                            max_notional=_n("max_daily_notional_usd"))
    per_day = PerDayCap(max_orders=_n("max_orders_per_day"),
                        max_notional=_n("max_daily_notional_usd"))
    for v in (per_day.check(gs), per_trade.check(gs)):
        if not v.allowed:
            bad.append(f"{v.guard}: {v.reason}")
    room = per_trade.largest_allowed(gs)
    usd = float(order.get("usd") or 0.0)
    if usd < _n("min_order_usd"):
        bad.append(f"${usd:,.2f} under min_order_usd ${_n('min_order_usd'):,.2f}")
    elif room is not None and room > 0 and usd > room + 1e-9:
        # `room > 0` on purpose. When the day is fully used the two guards
        # above have already said so, in their own words, with their own
        # numbers; adding "over the $0.00 placeable now" makes one condition
        # read as three problems.
        bad.append(f"${usd:,.2f} over the ${room:,.2f} placeable now "
                   f"(order cap ${_n('max_order_usd'):,.2f}, daily notional "
                   f"cap ${_n('max_daily_notional_usd'):,.2f})")

    if cfg.get("seal_required") and sealed_ok is False:
        bad.append("decision not sealed to the chain")

    min_sig = cfg.get("min_sealed_signals", 0)
    if st.get("sealed_signals", 0) < min_sig:
        bad.append(f"Rule 5: {st.get('sealed_signals', 0)} sealed signals on "
                   f"record, need {min_sig}")
    elif cfg.get("rule5_require_significance", True):
        r5 = st.get("rule5") or {}
        # The count is met; the record must also mean something. A losing or
        # luck-shaped record with 30 rows is the answer Rule 5 exists to give,
        # not a licence.
        if not r5.get("clears"):
            bad.append(f"Rule 5: {r5.get('why') or 'no scored record in state'}")

    # Guards gate BUYS only -- a guard never stops a risk-reducing sale.
    if guard_blocks and order.get("side") == "buy":
        bad.append("guards: " + ", ".join(guard_blocks))

    return bad + _caller_reasons(caller, order, guard_blocks)


def _caller_reasons(caller, order, guard_blocks):
    """APPEND ONLY. A caller may add a reason to refuse; it can never remove
    one. That is what makes the sentinel provably no looser than the trader."""
    if caller != "sentinel":
        return []
    out = []
    side = order.get("side")
    # The sentinel answers about a proposal from an app with no portfolio view,
    # so the two portfolio-dependent rules cannot be evaluated here. They FAIL
    # CLOSED rather than being skipped -- skipping them is precisely what this
    # consolidation exists to stop.
    if side == "buy" and guard_blocks is None:
        out.append("sentinel: no portfolio was supplied, so the buy-side guards "
                   "(cash floor, concentration, budgets) could not be evaluated")
    if side == "sell":
        out.append("sentinel: a sell cannot be admitted here -- the reserve floor "
                   "is enforced on the QUANTITY by covenant_trader.plan(), and "
                   "this path has no holdings or baseline to clamp against")
    return out
