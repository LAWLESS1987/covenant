#!/usr/bin/env python3
r"""
covenant_trader.py -- the local trading program.

  covenant nodes  +  Kraken  +  Coinbase  ->  rules  ->  orders  ->  sealed record

WHAT IT IS
  One process you run on your own machine. It watches your nodes, reads your
  balances at both exchanges, applies the five rules in MY_STRATEGY.md, writes
  the day's decision to the ledger as a tamper-evident record, and -- when and
  only when it is ARMED -- places the resulting orders itself.

DISARMED IS THE DEFAULT AND IT IS NOT A FORMALITY
  With armed=false every order still goes to the venue, but to its VALIDATE
  endpoint: Kraken's `validate=true` and Coinbase's `/orders/preview`. The real
  venue parses the real order against your real balance and the real minimums
  and tells you what it would do. You get a true rehearsal, not a simulation
  written by the same person who wrote the bug.

  Arming is a change YOU make to trader_config.json, with a trade-scoped API
  key YOU install. Nothing in this program will arm itself, and no argument
  turns arming on.

THE PRECONDITIONS FOR A LIVE ORDER
  All of these, every time, or the order is staged instead of sent:
    1. config armed = true
    2. no TRADER_HALT file in this folder      (drop one to stop everything)
    3. the order is inside max_order_usd, and today is inside
       max_daily_notional_usd and max_orders_per_day -- these are
       guards.PerTradeCap and guards.PerDayCap since 2026-09-04, so
       daily.py's morning report enforces the same numbers this does
    4. guards.py raises no other block      (buys only -- a guard never stops a sale)
    5. the decision sealed to the chain     (if seal_required)
    6. Rule 5 is satisfied: min_sealed_signals sealed signals on record
  Every failed precondition is printed with its name. Nothing is skipped
  quietly.

RULE 5 IS A REAL GATE, NOT A COMMENT
  MY_STRATEGY.md says: seal 30+ signals and score them before letting any of
  this touch real money, because no timing edge in your own out-of-sample
  testing was distinguishable from chance (p 0.47-0.92). That number is
  min_sealed_signals in the config and it blocks live orders until met. You can
  lower it. It is your money and your call -- but it should be a decision you
  make on purpose, not one you never noticed.

USAGE
  python covenant_trader.py --status         nodes, venues, config, counters
  python covenant_trader.py --once           one full cycle
  python covenant_trader.py --loop           every loop_seconds, until stopped
  python covenant_trader.py --plan-only      plan and print; touch no venue
"""
from __future__ import annotations
import os, sys, json, time, argparse, statistics, datetime, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import daily                      # prices, 200d regime, cross-venue verification
import venues as V

try:
    import guards as _guards
    GUARDS_ERR = None
except Exception as _e:           # fail closed, exactly as daily.py does
    _guards, GUARDS_ERR = None, f"{type(_e).__name__}: {_e}"

CONFIG = os.path.join(HERE, "trader_config.json")
HALT = os.path.join(HERE, "TRADER_HALT")
# State lives outside the synced folder for the same two reasons daily.py
# gives: it is a running record of the portfolio, and a file that changes every
# run would invalidate covenant_seal.py's manifest daily.
STATE = os.environ.get("COVENANT_TRADER_STATE") or os.path.join(
    os.path.expanduser("~"), ".covenant", "trader_state.json")

DEFAULT_CONFIG = {
    "armed": False,
    "max_order_usd": 100.0,
    "max_daily_notional_usd": 300.0,
    "max_orders_per_day": 4,
    "min_order_usd": 5.0,
    "max_position_pct": 0.20,
    "min_cash_pct": 0.10,
    "seal_required": True,
    "min_sealed_signals": 30,
    "node_ports": [5000],
    "node_key": "covenant_A.db.key",
    "loop_seconds": 3600,
    "symbols": [],
}


# ------------------------------------------------------------------- plumbing
def load_config():
    if not os.path.exists(CONFIG):
        json.dump(DEFAULT_CONFIG, open(CONFIG, "w", encoding="utf-8"), indent=2)
        print(f"wrote a disarmed default config to {os.path.basename(CONFIG)}")
    cfg = dict(DEFAULT_CONFIG)
    cfg.update(json.load(open(CONFIG, encoding="utf-8")))
    return cfg


def load_state():
    try:
        return json.load(open(STATE, encoding="utf-8"))
    except Exception:
        return {"orders_today": [], "day": "", "equity_peak": 0.0,
                "equity_start_of_day": 0.0, "closed_trades": [], "last_sold": {},
                "sealed_signals": 0, "bought_total_usd": 0.0}


def save_state(st):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    json.dump(st, open(STATE, "w", encoding="utf-8"), indent=2)


def roll_day(st):
    today = time.strftime("%Y-%m-%d")
    if st.get("day") != today:
        st["day"] = today
        st["orders_today"] = []
        st["equity_start_of_day"] = 0.0     # set once equity is known this run
    # BACKFILL THE LIFETIME BUY TOTAL, BUT ONLY ON EVIDENCE.
    #
    # guards.BuyBudget measures cumulative buying against half the starting
    # book, and it blocks when the figure is unknown -- which is right, because
    # assuming zero would hand back a budget that may already be spent. A state
    # file written before the figure existed is exactly that case, and it would
    # block for ever without something to resolve it.
    #
    # So it is resolved from evidence rather than convenience: a file with no
    # closed trades, no orders today and no equity peak has never seen a trade,
    # so nothing has been bought and zero is a measurement. Any other file keeps
    # the key ABSENT, keeps blocking, and waits for an operator who knows what
    # was spent -- because that is a question about their money, not ours.
    if "bought_total_usd" not in st:
        never_traded = (not st.get("closed_trades")
                        and not st.get("orders_today")
                        and not st.get("equity_peak"))
        if never_traded:
            st["bought_total_usd"] = 0.0
            st["bought_total_usd_note"] = (
                "initialised to 0 by roll_day on %s: this state recorded no closed "
                "trades, no orders and no equity peak, so nothing had been bought. "
                "It is a measurement, not a default." % today)
    return st


# ----------------------------------------------------------------------- node
def node_status(ports, timeout=4):
    """Poll every configured node. A node that does not answer is REPORTED as
    down, never omitted -- an absent row reads as 'fine' at a glance."""
    def one(port):
        row = {"port": port, "up": False, "height": None, "peers": None,
               "anomalies": None, "why": None}
        try:
            for path, key in (("/health", None), ("/chain", "height"),
                              ("/peers", "peers"), ("/anomalies", "anomalies")):
                req = urllib.request.Request(f"http://127.0.0.1:{port}{path}",
                                             headers={"User-Agent": "covenant-trader/1.0"})
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    js = json.loads(r.read().decode())
                if path == "/health":
                    row["up"] = True
                elif path == "/chain":
                    ch = js.get("chain") or js.get("blocks") or []
                    row["height"] = js.get("height", len(ch) if isinstance(ch, list) else None)
                elif path == "/peers":
                    p = js.get("peers", js)
                    row["peers"] = len(p) if isinstance(p, (list, dict)) else None
                elif path == "/anomalies":
                    an = js.get("anomalies", js)
                    row["anomalies"] = len(an) if isinstance(an, (list, dict)) else None
        except Exception as e:
            row["why"] = f"{type(e).__name__}"
        return row

    if not ports:
        return []
    with ThreadPoolExecutor(max_workers=min(8, len(ports))) as pool:
        return list(pool.map(one, ports))


def seal_decision(cfg, record):
    """Write the decision to the ledger as a self-send carrying the record.

    Returns (ok, detail). The ethics gate FAILS CLOSED, so a node with no
    reachable judge refuses this -- which is the designed behaviour and is
    reported, not worked around. With seal_required the refusal also stops
    live orders: an auto-trader whose audit trail is broken should not keep
    trading, because the record is the only thing that can say afterwards what
    it decided and when.
    """
    keypath = os.path.join(HERE, cfg.get("node_key", ""))
    if not os.path.exists(keypath):
        return False, f"no node key at {os.path.basename(keypath)}"
    ports = cfg.get("node_ports") or []
    if not ports:
        return False, "no node_ports configured"
    try:
        import covenant_unified_v8 as cov
        import covenant_client as cc
        sk = cc.load_key(keypath)
        pem = cc.pub_of_key(keypath)
        reg = cov.RegistrationPoW.generate(pem, cov.BASE_REGISTRATION_DIFFICULTY)
        data = {"origin": "covenant_trader", "kind": "trade_decision", **record}
        tx = cov.Transaction(sender_pubkey=pem, receiver=pem, data=data,
                             amount=0.0, benefit_score=0.0, reg_nonce=reg)
        tx.sign(sk)
        body = {"sender_pubkey": pem, "receiver": pem, "data": data, "amount": 0.0,
                "timestamp": tx.timestamp, "benefit_score": 0.0,
                "signature": tx.signature, "reg_nonce": reg}
        st, resp = cc.http("POST", ports[0], "/transactions", body, timeout=310)
        return (st == 200), f"HTTP {st}: {json.dumps(resp)[:160]}"
    except SystemExit as e:
        return False, f"node unreachable: {e}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


# ------------------------------------------------------------------ portfolio
def gather(cfg):
    """Balances per venue + live prices and 200d regime. Returns a portfolio."""
    per_venue, venue_notes = {}, []
    for v in V.all_venues():
        if not v.has_credentials():
            venue_notes.append(f"{v.name}: no credential installed")
            continue
        try:
            per_venue[v.name] = v.balances()
        except V.VenueError as e:
            venue_notes.append(f"{v.name}: {e}")

    merged = {}
    for vname, bal in per_venue.items():
        for sym, amt in bal.items():
            s = {"XBT": "BTC", "ZUSD": "USD", "XXLM": "XLM", "XXRP": "XRP",
                 "XETH": "ETH"}.get(sym, sym)
            merged.setdefault(s, {})[vname] = amt

    cash = sum(a for s, per in merged.items()
               if s in ("USD", "USDC", "USDT") for a in per.values())
    syms = [s for s in merged if s not in ("USD", "USDC", "USDT")]
    if cfg.get("symbols"):
        syms = [s for s in syms if s in cfg["symbols"]]

    prices = daily.prefetch(syms, "both") if syms else {}
    positions, unpriced = [], []
    for s in sorted(syms):
        px, closes, why, _n, _d = prices.get(s, (None, None, "not fetched", [], []))
        qty = sum(merged[s].values())
        if px is None:
            unpriced.append({"sym": s, "qty": qty, "why": why or "no price"})
            continue
        s200 = statistics.fmean(closes) if closes and len(closes) >= 50 else None
        positions.append({"sym": s, "qty": qty, "px": px, "val": qty * px,
                          "s200": s200, "bars": len(closes) if closes else 0,
                          "regime": ("UP" if s200 and px >= s200 else
                                     "DOWN" if s200 else "n/a"),
                          "at": dict(merged[s])})
    total = sum(p["val"] for p in positions) + cash
    return {"positions": positions, "cash": cash, "total": total,
            "unpriced": unpriced, "venue_notes": venue_notes,
            "venues_read": sorted(per_venue)}


# --------------------------------------------------------------- rule engine
RESERVE_PATH = os.path.join(HERE, "private", "RESERVE.json")


def reserve_baseline(pf, path=RESERVE_PATH):
    """Half of every coin is not for sale, and half OF WHAT is the whole
    question (asked 2026-09-04: "50% of every current coin should be off
    limits").

    Read as "half of what I hold right now", checked per order, the rule
    permits selling everything: half of 100 leaves 50, half of 50 leaves 25,
    and eight orders later the position is 0.4 units with no single order ever
    breaking it. A floor that moves down with the balance it protects is not a
    floor. So the baseline is written ONCE, here, and the reserve is half of
    that number for ever after.

    It lives under private/ because a per-asset quantity is the portfolio, and
    CONSTITUTION II.4 keeps that unpublished. Buying more RAISES the baseline,
    because a floor that ignored new coin would be a different rule than the
    one asked for. Nothing here ever lowers it -- lowering is the ratchet
    wearing a different hat, and it is an operator's edit to this file, where
    it leaves a mark.
    """
    held = {}
    for p in pf.get("positions", []):
        if p.get("px"):
            held[p["sym"]] = p["val"] / p["px"]
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        base = dict(data.get("baseline", {}))
    except (OSError, ValueError):
        data, base = {}, {}
    raised = []
    for sym, q in held.items():
        if sym not in base:
            base[sym] = q
            raised.append("%s baseline set at %.8g" % (sym, q))
        elif q > base[sym]:
            raised.append("%s baseline raised %.8g -> %.8g (more was bought)" % (sym, base[sym], q))
            base[sym] = q
    if raised or not data:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                json.dump({"_what": "Half of each of these quantities is reserved and may never "
                                    "be sold by any rule. Written once per asset and raised only "
                                    "by buying more. Lowering a number here is an operator's "
                                    "decision and this program never does it.",
                           "pct_reserved": 0.50,
                           "set_by": "covenant_trader.reserve_baseline",
                           "baseline": base}, fh, indent=1, sort_keys=True)
        except OSError:
            pass
    return base, held, raised


def plan(cfg, pf):
    """The five rules -> concrete orders. Sells only; see the note on Rule 4.

    Rule 1 caps any single position at max_position_pct and holds a cash floor.
    Rule 2/3 make the 200-day line a regime switch acted on only when it FLIPS.
    Rule 4 forbids adding to anything below its line.

    Nothing here generates a BUY. That is not an oversight and not timidity: on
    this project's own out-of-sample evidence no timing rule beat chance on any
    of ten assets, so there is no measured reason to buy anything at a
    particular moment. Every rule that DID replicate -- the concentration cap,
    the cash floor, the drawdown control -- is expressed by selling or by doing
    nothing. A buy path would be inventing an edge the data does not support.
    """
    orders, notes = [], []
    total, cap = pf["total"], cfg["max_position_pct"]
    if total <= 0:
        return orders, ["portfolio total is zero -- nothing to plan"]

    # THE RESERVE. Every order this function can produce is a SELL, and the
    # guard stack is consulted for buys only ("a guard never stops a sale"),
    # so a reserve enforced there would never run. It is enforced HERE, on the
    # quantity itself, before an order exists.
    base, held_now, raised = reserve_baseline(pf)
    pct_reserved = 0.50
    for r in raised:
        notes.append("reserve: " + r)

    for p in pf["positions"]:
        pct = p["val"] / total
        if pct > cap:
            over_usd = p["val"] - cap * total
            qty = over_usd / p["px"]
            # guards.sellable_units is the one implementation, and it is what
            # carries the hold-only rule: XRP is excluded from the tradeable
            # half entirely, so this returns 0 for it and the order is dropped
            # below rather than trimmed.
            sellable = _guards.sellable_units(
                held_now.get(p["sym"], 0.0), base.get(p["sym"], 0.0),
                p["sym"], pct_reserved) if _guards else 0.0
            if sellable is None:
                sellable = 0.0
            # ONE CONDITION, ONE NOTE. A hold-only asset produced three lines
            # -- excluded, then "trimmed to 0", then "DROPPED" -- and the
            # middle one was actively wrong: it read "50% of the baseline is
            # reserved and no rule may cross it" when for this asset the
            # reserved fraction is all of it. A note that misstates the reason
            # is worse than no note, because it is the line someone would argue
            # with.
            if p["sym"] in (getattr(_guards, "HOLD_ONLY", ()) if _guards else ()):
                notes.append("reserve: %s is hold-only -- it is excluded from the "
                             "tradeable half entirely, so the %.8g units the "
                             "concentration cap wanted sold are not sold"
                             % (p["sym"], qty))
                continue
            if qty > sellable:
                notes.append("reserve: %s sell trimmed %.8g -> %.8g units; %.0f%% of the "
                             "%.8g baseline is reserved and no rule may cross it"
                             % (p["sym"], qty, sellable, pct_reserved * 100, base.get(p["sym"], 0.0)))
                qty = sellable
                over_usd = qty * p["px"]
            if qty <= 0:
                notes.append("reserve: %s sell DROPPED -- the position is at its reserved floor"
                             % p["sym"])
                continue
            orders.append({"sym": p["sym"], "side": "sell", "qty": qty,
                           "usd": over_usd, "px": p["px"],
                           "rule": "R1 concentration cap",
                           "why": f"{pct:.1%} of portfolio, cap {cap:.0%}",
                           "at": p["at"]})

    cash_pct = pf["cash"] / total
    if cash_pct < cfg["min_cash_pct"]:
        need = cfg["min_cash_pct"] * total - pf["cash"]
        raised = sum(o["usd"] for o in orders)
        if raised >= need:
            notes.append(f"R1 cash floor: need ${need:,.0f}, the cap trims raise "
                         f"${raised:,.0f} -- covered.")
        else:
            notes.append(f"R1 cash floor: cash {cash_pct:.1%} below "
                         f"{cfg['min_cash_pct']:.0%}; cap trims raise ${raised:,.0f} "
                         f"of ${need:,.0f}. NOT auto-selling the shortfall -- which "
                         f"position to reduce is a judgement the rules do not make.")

    below = [p["sym"] for p in pf["positions"] if p["regime"] == "DOWN"]
    if below:
        notes.append("R4: below the 200d line, do not add -- " + ", ".join(below))
    return orders, notes


# ------------------------------------------------------------------ execution
def preconditions(cfg, st, pf, order, sealed_ok, guard_blocks):
    """Every reason this specific order may not go live. Empty list = clear."""
    bad = []
    if not cfg.get("armed"):
        bad.append("armed=false in trader_config.json")
    if os.path.exists(HALT):
        bad.append("TRADER_HALT file present")
    # THE CAPS ARE GUARDS NOW (guards.PerTradeCap / PerDayCap), and this asks
    # them rather than repeating their arithmetic. They were enforced only here
    # until 2026-09-04, which meant daily.py -- the report a person actually
    # reads, which runs the guard stack and prints "may add" -- could not see
    # them. One implementation, two callers, and the guards fail closed.
    if _guards is None:
        bad.append("guards.py unavailable -- the per-trade and per-day caps "
                   "cannot be evaluated")
    else:
        gs = _guards.State(equity_now=0.0, equity_peak=0.0, equity_start_of_day=0.0,
                           closed_trades=[], last_sold={}, positions={}, cash=0.0,
                           orders_today=_guards.orders_today_from(st))
        per_trade = _guards.PerTradeCap(
            max_usd=cfg["max_order_usd"], min_usd=cfg["min_order_usd"],
            max_orders=cfg["max_orders_per_day"],
            max_notional=cfg["max_daily_notional_usd"])
        per_day = _guards.PerDayCap(max_orders=cfg["max_orders_per_day"],
                                    max_notional=cfg["max_daily_notional_usd"])
        for v in (per_day.check(gs), per_trade.check(gs)):
            if not v.allowed:
                bad.append(f"{v.guard}: {v.reason}")
        room = per_trade.largest_allowed(gs)
        if order["usd"] < cfg["min_order_usd"]:
            bad.append(f"${order['usd']:,.2f} under min_order_usd "
                       f"${cfg['min_order_usd']:,.2f}")
        elif room is not None and room > 0 and order["usd"] > room + 1e-9:
            # `room > 0` on purpose. When the day is fully used the two guards
            # above have already said so, in their own words, with their own
            # numbers; adding "over the $0.00 placeable now" makes one
            # condition read as three problems. This line earns its place only
            # when there IS room and this order is bigger than it.
            bad.append(f"${order['usd']:,.2f} over the ${room:,.2f} placeable now "
                       f"(order cap ${cfg['max_order_usd']:,.2f}, daily notional "
                       f"cap ${cfg['max_daily_notional_usd']:,.2f})")
    if cfg.get("seal_required") and not sealed_ok:
        bad.append("decision not sealed to the chain")
    if st.get("sealed_signals", 0) < cfg.get("min_sealed_signals", 0):
        bad.append(f"Rule 5: {st.get('sealed_signals', 0)} sealed signals on "
                   f"record, need {cfg['min_sealed_signals']}")
    # Guards gate BUYS only. This planner emits no buys, so a guard block is
    # recorded for the operator but does not stop a risk-reducing sale.
    if guard_blocks and order["side"] == "buy":
        bad.append("guards: " + ", ".join(guard_blocks))
    return bad


def venue_for(order, live_venues):
    """Sell where the coins actually are. Largest holding wins a tie."""
    at = order.get("at") or {}
    for name, _amt in sorted(at.items(), key=lambda kv: -kv[1]):
        for v in live_venues:
            if v.name == name:
                return v
    return None


def execute(cfg, st, orders, sealed_ok, guard_blocks, plan_only=False):
    live_venues = [v for v in V.all_venues() if v.has_credentials()]
    results = []
    for o in orders:
        bad = preconditions(cfg, st, {}, o, sealed_ok, guard_blocks)
        v = venue_for(o, live_venues)
        if v is None:
            results.append({**o, "status": "NO VENUE",
                            "detail": "no credentialed venue holds it"})
            continue
        if plan_only:
            results.append({**o, "status": "PLAN ONLY", "detail": "no venue call"})
            continue
        go_live = not bad
        try:
            r = v.place(o["sym"], o["side"], o["qty"], live=go_live)
            results.append({**o, "status": "PLACED" if go_live else "VALIDATED",
                            "detail": r.get("descr") or "", "txid": r.get("txid"),
                            "blocked_by": bad, "venue": v.name})
            if go_live:
                # `side` is recorded because guards.FiatBuyPermission needs to
                # separate what selling raised today from what buying spent;
                # without it the two are indistinguishable and that guard
                # fails closed.
                #
                # ONLY THE FIAT PORTION IS BANKED against guards.BuyBudget --
                # the part of this buy that today's sales did not cover. A
                # rotation (sell XLM, buy SOL with the proceeds) puts no new
                # money in and must not consume a budget that exists to limit
                # new money; charging it would switch off the very mechanism
                # the operator asked for. The headroom is read BEFORE this
                # order is appended, because appending it would count the
                # order against itself.
                fiat_part = float(o["usd"])
                if o.get("side") == "buy" and _guards is not None:
                    before = _guards.State(
                        equity_now=0.0, equity_peak=0.0, equity_start_of_day=0.0,
                        closed_trades=[], last_sold={}, positions={}, cash=0.0,
                        orders_today=_guards.orders_today_from(st))
                    room = _guards.FiatBuyPermission().headroom(before)
                    # room is None when the day cannot be read; the whole order
                    # is then treated as new money, which is the safe direction.
                    fiat_part = max(0.0, float(o["usd"]) - (room or 0.0))
                st.setdefault("orders_today", []).append(
                    {"sym": o["sym"], "usd": o["usd"], "side": o.get("side"),
                     "at": time.time(), "txid": r.get("txid")})
                if o.get("side") == "buy" and fiat_part > 0:
                    st["bought_total_usd"] = float(
                        st.get("bought_total_usd") or 0.0) + fiat_part
        except V.VenueError as e:
            results.append({**o, "status": "REFUSED", "detail": str(e)[:160],
                            "blocked_by": bad, "venue": v.name})
    return results


# --------------------------------------------------------------------- report
def hr(t):
    print("\n" + "=" * 74 + f"\n{t}\n" + "=" * 74)


def run_once(cfg, plan_only=False):
    st = roll_day(load_state())

    hr(f"COVENANT TRADER   {time.strftime('%Y-%m-%d %H:%M')}"
       + ("   [ARMED]" if cfg.get("armed") else "   [disarmed]"))

    nodes = node_status(cfg.get("node_ports") or [])
    print("  NODES")
    if not nodes:
        print("    (none configured)")
    for n in nodes:
        if n["up"]:
            print(f"    :{n['port']}  up    height={n['height']}  "
                  f"peers={n['peers']}  anomalies={n['anomalies']}")
        else:
            print(f"    :{n['port']}  DOWN  ({n['why']})")

    pf = gather(cfg)
    print("\n  PORTFOLIO")
    for note in pf["venue_notes"]:
        print(f"    ! {note}")
    if not pf["positions"] and not pf["cash"]:
        print("    nothing readable -- install a credential (EXCHANGE_SETUP.md)")
    for p in pf["positions"]:
        pct = p["val"] / pf["total"] if pf["total"] else 0
        print(f"    {p['sym']:<6}{p['qty']:>16,.6f} {p['px']:>12,.6f} "
              f"{p['val']:>10,.2f} {pct:>6.1%}  {p['regime']:<4} "
              f"@{'+'.join(p['at'])}")
    for u in pf["unpriced"]:
        print(f"    {u['sym']:<6}{u['qty']:>16,.6f}  NO PRICE -- {u['why']}")
    if pf["total"]:
        print(f"    {'TOTAL':<6}{'':>16} {'':>12} {pf['total']:>10,.2f}  "
              f"cash {pf['cash']:,.2f} ({pf['cash']/pf['total']:.1%})")

    # equity history feeds the guards
    if pf["total"]:
        st["equity_peak"] = max(st.get("equity_peak", 0.0), pf["total"])
        if not st.get("equity_start_of_day"):
            st["equity_start_of_day"] = pf["total"]

    guard_blocks = []
    print("\n  GUARDS")
    if GUARDS_ERR:
        print(f"    guards.py unavailable ({GUARDS_ERR}) -- FAILING CLOSED")
        guard_blocks = ["guards unavailable"]
    elif pf["total"]:
        state = _guards.State(
            equity_now=pf["total"], equity_peak=st["equity_peak"],
            equity_start_of_day=st["equity_start_of_day"],
            closed_trades=st.get("closed_trades", []),
            last_sold=st.get("last_sold", {}),
            positions={p["sym"]: p["val"] for p in pf["positions"]},
            cash=pf["cash"],
            orders_today=_guards.orders_today_from(st),
            # The ONLY place this is written, and only from a real portfolio
            # read -- see guards.set_starting_total for what went wrong when it
            # was two places.
            starting_total_usd=_guards.set_starting_total(pf["total"], RESERVE_PATH),
            bought_total_usd=st.get("bought_total_usd"))
        for vd in _guards.GuardStack().evaluate(state):
            print(f"    [{'ok  ' if vd.allowed else 'BLOCK'}] {vd.guard:<14} {vd.reason}")
            # The two cap guards are shown here but NOT added to guard_blocks.
            # guard_blocks is applied to buys only, and preconditions() applies
            # the caps to every order, sells included -- a runaway loop selling
            # costs the same 100 bps a round trip as one buying. Adding them
            # here as well would report the same block twice for a buy and
            # would weaken it to buys-only for a sell.
            if not vd.allowed and vd.guard not in ("per_trade_cap", "per_day_cap"):
                guard_blocks.append(vd.guard)

    orders, notes = plan(cfg, pf)
    print("\n  PLAN")
    for n in notes:
        print(f"    - {n}")
    if not orders:
        print("    no orders. Doing nothing is a position (Rule 3).")

    record = {"at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
              "total": round(pf["total"], 2), "cash": round(pf["cash"], 2),
              "positions": {p["sym"]: round(p["val"], 2) for p in pf["positions"]},
              "regimes": {p["sym"]: p["regime"] for p in pf["positions"]},
              "orders": [{k: o[k] for k in ("sym", "side", "qty", "usd", "rule")}
                         for o in orders]}
    sealed_ok, seal_detail = (False, "nothing to seal")
    if orders or cfg.get("seal_required"):
        sealed_ok, seal_detail = seal_decision(cfg, record)
    print(f"\n  SEAL  {'ok' if sealed_ok else 'FAILED'} -- {seal_detail}")

    results = execute(cfg, st, orders, sealed_ok, guard_blocks, plan_only)
    if results:
        print("\n  ORDERS")
        for r in results:
            print(f"    [{r['status']:<9}] {r['side'].upper():<4} {r['qty']:,.6f} "
                  f"{r['sym']} ~${r['usd']:,.2f}  ({r['rule']})")
            if r.get("detail"):
                print(f"                 {r['detail'][:100]}")
            for b in r.get("blocked_by") or []:
                print(f"                 held back: {b}")

    save_state(st)
    print(f"\n  {'ARMED -- orders above marked PLACED are real.' if cfg.get('armed') else 'Disarmed. Orders were validated against the venue, never booked.'}")
    print("=" * 74)
    return results


def cmd_status(cfg):
    st = roll_day(load_state())
    hr("STATUS")
    print(f"  armed              : {cfg.get('armed')}")
    print(f"  halt file present  : {os.path.exists(HALT)}  ({os.path.basename(HALT)})")
    print(f"  max order          : ${cfg['max_order_usd']:,.0f}")
    print(f"  daily notional cap : ${cfg['max_daily_notional_usd']:,.0f}")
    print(f"  orders per day     : {cfg['max_orders_per_day']}")
    print(f"  seal required      : {cfg.get('seal_required')}")
    print(f"  Rule 5 threshold   : {st.get('sealed_signals', 0)} / "
          f"{cfg.get('min_sealed_signals')} sealed signals")
    print(f"  orders placed today: {len(st.get('orders_today', []))}")
    print(f"  state file         : {STATE}")
    for v in V.all_venues():
        print(f"  {v.name:<18} : credential {'installed' if v.has_credentials() else 'MISSING'}")
    for n in node_status(cfg.get("node_ports") or []):
        print(f"  node :{n['port']:<12} : {'up' if n['up'] else 'DOWN ' + str(n['why'])}")
    print("=" * 74)


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--once", action="store_true", help="one full cycle")
    g.add_argument("--loop", action="store_true", help="repeat every loop_seconds")
    g.add_argument("--status", action="store_true", help="config, venues, nodes, counters")
    g.add_argument("--plan-only", action="store_true", help="plan and print; touch no venue")
    a = ap.parse_args()
    cfg = load_config()

    if a.status or not (a.once or a.loop or a.plan_only):
        cmd_status(cfg)
        if not (a.once or a.loop or a.plan_only):
            print("\n  --once to run a cycle, --plan-only to touch no venue, "
                  "--loop to keep going.")
        return 0
    if a.loop:
        print(f"looping every {cfg['loop_seconds']}s. Ctrl-C to stop; "
              f"or create {os.path.basename(HALT)} to halt ordering.")
        while True:
            try:
                run_once(load_config())       # re-read: arming can change under us
            except KeyboardInterrupt:
                print("\nstopped.")
                return 0
            except Exception as e:
                print(f"\n  cycle failed: {type(e).__name__}: {e}")
            time.sleep(max(60, int(cfg["loop_seconds"])))
    run_once(cfg, plan_only=a.plan_only)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
