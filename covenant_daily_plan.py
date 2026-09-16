#!/usr/bin/env python3
"""covenant_daily_plan.py -- the day's plan, the operator's signed approval,
and the trader's seventh gate.

ASKED 2026-09-12: "i'll have to daily approve of the strategy it lays out".
The operator is the hand; the trader is the only executor; no order goes
live without a signed approval of THAT day's plan, matching its hash.

THE PLAN (ops/daily_plan/<date>.json, written by the nightly pass or
`--write`): money posture as money_posture.py prints it, the Rule 5 record
(signal_ledger.summary), the caps and switches from trader_config.json, the
trader's own proposed orders for the day (covenant_trader.run_once with
plan_only=True -- it plans, it touches no venue), and the reason there is
nothing to do when there is nothing to do. Its sha256 is over the canonical
JSON without the sha field. It is NOT investment advice: it is the covenant's
measured posture and its own validated rules, of which -- 2026-09-12 -- none
has cleared walk-forward, deflation and PBO, so the plans read "hold".

THE APPROVAL (ops/daily_approvals.jsonl): one line per decision, approve or
decline, with a note, signed by a REGISTERED signer (ops/daily_plan_signers.json:
name -> public key PEM; the phone node's key, the PC node's key). The
signature is the core's own operator-request scheme (sign_operator_request /
verify_operator_signature: method, path, body hash, nonce, timestamp), so a
decision cannot be forged, replayed or moved to another day's plan. The LAST
decision for a plan wins: an approve can be withdrawn by a later decline.

THE GATE (guards.preconditions, reason 7): no approved decision for today's
plan -> "no approved daily plan for <date>". cfg "daily_plan_required" true by
default; the trader, the sentinel's seal path and daily.py all ask
guards.preconditions, so one rule.

PRIVACY. The plan carries the money posture. It lives on this PC, gitignored;
the node serves it ONLY to a signed GET from a registered signer, and the
phone shows it only to the person holding the phone.

USE
  python covenant_daily_plan.py --write            # write today's plan (the nightly does this)
  python covenant_daily_plan.py --show             # today's plan and its decision
  python covenant_daily_plan.py --approve [--note "..."]   # sign with this PC's node key (--key)
  python covenant_daily_plan.py --decline [--note "..."]
  python covenant_daily_plan.py --pubkey           # the PEM of --key, to register it
  python covenant_daily_plan.py --register-signer NAME FILE.pem
LICENCE: public domain.
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

PLAN_DIR = os.path.join(HERE, "ops", "daily_plan")
APPROVALS = os.path.join(HERE, "ops", "daily_approvals.jsonl")
SIGNERS = os.path.join(HERE, "ops", "daily_plan_signers.json")
DEFAULT_KEY = os.path.join(HERE, "nodeA_prod.db.key")
APPROVE_PATH = "/daily_plan/approve"
PLAN_PATH = "/daily_plan"
WINDOW_S = 300           # a signed request older or newer than this is refused
_seen_nonces = set()


def today(now=None):
    return time.strftime("%Y-%m-%d", time.localtime(now if now is not None else time.time()))


def canonical(d):
    return json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def plan_sha(plan):
    return hashlib.sha256(canonical({k: v for k, v in plan.items() if k != "sha256"}).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- gathering

def _run(cmd, timeout):
    try:
        p = subprocess.run([sys.executable] + cmd, cwd=HERE, capture_output=True, text=True, timeout=timeout)
        return (p.stdout or "") + (p.stderr or "")
    except Exception as e:                                       # noqa: BLE001
        return "(%s: %s)" % (type(e).__name__, e)


def gather(say=print):
    """Everything the plan is made of, from the checkers, never from memory."""
    import guards
    import signal_ledger
    cfg = guards.load_config() or {}
    st = guards.load_trader_state() or {}
    r5 = signal_ledger.summary(min_signals=cfg.get("min_sealed_signals", 30))
    posture = _run(["money_posture.py"], 120)
    proposed, planner = [], ""
    try:
        import covenant_trader as T
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            results = T.run_once(cfg, plan_only=True) or []
        for r in results:
            proposed.append({k: r.get(k) for k in ("sym", "side", "usd", "status", "detail") if k in r})
        planner = "covenant_trader.run_once(plan_only=True)"
    except Exception as e:                                       # noqa: BLE001
        planner = "planner unavailable: %s: %s" % (type(e).__name__, str(e)[:160])
    return {
        "posture": "\n".join(posture.strip().splitlines()[-40:]),
        "rule5": r5,
        "armed": bool(cfg.get("armed")),
        "halt": os.path.exists(guards.HALT),
        "caps": {k: cfg.get(k) for k in ("max_order_usd", "max_daily_notional_usd", "max_orders_per_day",
                                          "min_cash_pct", "max_position_pct", "seal_required", "min_sealed_signals")},
        "orders_placed_today": len(st.get("orders_today", []) or []),
        "proposed_orders": proposed,
        "planner": planner,
    }


def write(day=None, say=print, plan_dir=None, gatherer=None):
    """Write the day's plan; returns it. Atomic (tmp + replace)."""
    plan_dir = plan_dir or PLAN_DIR
    day = day or today()
    g = (gatherer or gather)(say=say)
    live = [o for o in g.get("proposed_orders", []) if o.get("status") not in ("NO VENUE",)]
    why = ""
    if not live:
        # THREE ANSWERS, NOT TWO (2026-09-14). An empty order list means one of
        # two completely different things: the planner ran and proposed nothing,
        # or the planner could not be asked at all. gather() already records the
        # difference in `planner`, and this line ignored it -- so a crashed
        # planner produced the calm sentence "no order proposed", which is the
        # one a person reads on their phone before approving. Every morning it
        # failed would look exactly like every morning it had nothing to do.
        # "Could not determine" is its own answer and has to be said out loud.
        planner = str(g.get("planner") or "")
        if planner.startswith("planner unavailable") or not planner:
            why = ("NOT ASKED -- the planner did not run, so this is NOT "
                   "'nothing to do': %s" % (planner or "no planner recorded"))
        else:
            why = "no order proposed"
        if not g.get("rule5", {}).get("clears"):
            why += "; Rule 5 does not clear: " + str(g.get("rule5", {}).get("why", ""))
        if not g.get("armed"):
            why += "; trader disarmed"
        if g.get("halt"):
            why += "; TRADER_HALT present"
    plan = {"date": day, "written": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "no_action_reason": why,
            "rules": "MY_STRATEGY.md: hold-only floor, the reserve, the caps below; nothing here is advice"}
    plan.update(g)
    plan["sha256"] = plan_sha(plan)
    os.makedirs(plan_dir, exist_ok=True)
    p = os.path.join(plan_dir, day + ".json")
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(plan, fh, indent=1, ensure_ascii=False)
    os.replace(tmp, p)
    say("daily plan %s: %d proposed order(s)%s; sha %s" % (day, len(live), "" if live else " -- " + why, plan["sha256"][:12]))
    return plan


def load(day=None, plan_dir=None):
    p = os.path.join(plan_dir or PLAN_DIR, (day or today()) + ".json")
    try:
        with open(p, encoding="utf-8") as fh:
            plan = json.load(fh)
        if plan.get("sha256") != plan_sha(plan):
            return None                                          # a plan whose bytes moved is no plan
        return plan
    except (OSError, ValueError):
        return None


# ---------------------------------------------------------------- signers and decisions

def _norm(pem):
    return "".join(str(pem).split())


def signers(path=None):
    try:
        with open(path or SIGNERS, encoding="utf-8") as fh:
            d = json.load(fh)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def register_signer(name, pem, path=None):
    path = path or SIGNERS
    d = signers(path)
    d[name] = pem
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(d, fh, indent=1)
    os.replace(tmp, path)


def signer_name(pubkey_pem, path=None):
    n = _norm(pubkey_pem)
    for name, pem in signers(path).items():
        if _norm(pem) == n:
            return name
    return None


def verify_signed(pubkey_pem, method, path, body, nonce, timestamp, signature_b64, signers_path=None, now=None, seen=None):
    """(ok, signer name or reason). The core's operator-request scheme, plus:
    the key must be registered, the timestamp inside WINDOW_S, the nonce unseen."""
    import covenant_unified_v8 as cov
    who = signer_name(pubkey_pem, signers_path)
    if not who:
        return False, "key is not a registered daily-plan signer"
    try:
        ts = float(timestamp)
    except (TypeError, ValueError):
        return False, "bad timestamp"
    if abs((now if now is not None else time.time()) - ts) > WINDOW_S:
        return False, "signature outside the %d s window" % WINDOW_S
    seen = _seen_nonces if seen is None else seen
    if not nonce or nonce in seen:
        return False, "nonce reused or missing"
    if not cov.verify_operator_signature(pubkey_pem, method, path, body or b"", nonce, ts, signature_b64 or ""):
        return False, "signature does not verify"
    seen.add(nonce)
    return True, who


def record_decision(day, plan_sha256, decision, note, signer, pubkey_pem, path=None):
    row = {"t": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "date": day, "plan_sha256": plan_sha256,
           "decision": decision, "note": (note or "")[:500], "signer": signer,
           "pubkey_sha256": hashlib.sha256(_norm(pubkey_pem).encode()).hexdigest()[:16]}
    path = path or APPROVALS
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def decision(day, plan_sha256, path=None):
    """The LAST decision recorded for this plan: ('approve'|'decline'|None, row|None)."""
    last = None
    try:
        with open(path or APPROVALS, encoding="utf-8") as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if r.get("date") == day and r.get("plan_sha256") == plan_sha256 and r.get("decision") in ("approve", "decline"):
                    last = r
    except OSError:
        pass
    return (last["decision"], last) if last else (None, None)


def handle_decision(body_bytes, who, pubkey_pem, plan_dir=None, approvals=None):
    """The route's logic, testable without a server: (http status, payload)."""
    try:
        data = json.loads(body_bytes.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return 400, {"status": "error", "message": "body is not JSON"}
    day, sha, dec = str(data.get("date", "")), str(data.get("plan_sha256", "")), str(data.get("decision", ""))
    if dec not in ("approve", "decline"):
        return 400, {"status": "error", "message": "decision must be approve or decline"}
    plan = load(day, plan_dir)
    if not plan:
        return 404, {"status": "error", "message": "no plan for %s" % day}
    if plan["sha256"] != sha:
        return 409, {"status": "error", "message": "the plan changed since it was read; read it again"}
    row = record_decision(day, sha, dec, data.get("note", ""), who, pubkey_pem, approvals)
    return 200, {"status": "success", "decision": row}


def approved(day=None, plan_dir=None, approvals=None):
    day = day or today()
    plan = load(day, plan_dir)
    if not plan:
        return False, "no plan written for %s" % day
    d, row = decision(day, plan["sha256"], approvals)
    if d == "approve":
        return True, "approved by %s at %s" % (row.get("signer"), row.get("t"))
    if d == "decline":
        return False, "declined by %s at %s%s" % (row.get("signer"), row.get("t"), (": " + row["note"]) if row.get("note") else "")
    return False, "no decision recorded for today's plan (%s)" % plan["sha256"][:12]


def gate_reasons(now=None, plan_dir=None, approvals=None):
    ok, why = approved(today(now), plan_dir, approvals)
    return [] if ok else ["no approved daily plan for %s: %s (ops/daily_plan; python covenant_daily_plan.py --approve)" % (today(now), why)]


# ---------------------------------------------------------------- the phone's heartbeat (2026-09-12)

CHECKINS = os.path.join(HERE, "ops", "phone_checkins.jsonl")
SILENT_AFTER_S = 3600          # a phone that reported within a day and then went quiet this long is an alert


def record_checkin(body_bytes, who, path=None):
    """One signed line from a phone: what its node says about itself. Only the
    named fields are kept; anything else in the body is dropped unread."""
    try:
        data = json.loads(body_bytes.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return 400, {"status": "error", "message": "body is not JSON"}
    if not isinstance(data, dict):
        return 400, {"status": "error", "message": "body is not an object"}
    row = {"t": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "at": round(time.time(), 1), "signer": who}
    for k in ("node_id", "chain_height", "peers", "app", "battery", "when"):
        if k in data:
            row[k] = data[k] if isinstance(data[k], (int, float, bool)) else str(data[k])[:80]
    path = path or CHECKINS
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return 200, {"status": "success", "recorded": row}


def last_checkins(path=None):
    """{signer: last row} from the ledger."""
    out = {}
    try:
        with open(path or CHECKINS, encoding="utf-8") as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if r.get("signer"):
                    out[r["signer"]] = r
    except OSError:
        pass
    return out


# ------------------------------------------------- the phone's BUILD (2026-09-16)
#
# The heartbeat above has always carried `app` -- the build the phone is running --
# and nothing has ever read it. That is how the phone sat on 0.1.421+70c6200 for
# two days while a newer build waited in ops/app/: the PC knew both numbers and
# never compared them. Worse, the gap is not self-closing. 70c6200 predates the
# in-app updater, so that build has never asked /app/latest and never will --
# auto-update cannot bootstrap itself, and the one install that fixes it needs a
# person and a browser. A condition only a person can clear has to be SAID, or it
# is not being managed; it is being forgotten.
#
# The alert text is deliberately stable while the facts are (A60/M-rule: the
# watchdog keys on the first 80 characters, so a changing number inside an alert
# makes every round "news"). It names the two builds and the URL to open, and it
# goes away by itself the moment the phone reports the sha it was handed.

LATEST_BUILD = os.path.join(HERE, "ops", "app", "latest.json")


def newest_build(path=None):
    """The build covenant_app_update.py last fetched, or {} if there is none."""
    try:
        with open(path or LATEST_BUILD, encoding="utf-8") as fh:
            d = json.load(fh)
        return d if isinstance(d, dict) and d.get("sha7") else {}
    except (OSError, ValueError):
        return {}


def pc_tailnet_address():
    """This PC's Tailscale address, read from its own interfaces.

    Not hardcoded: the operator is told to open this URL on a phone, and a URL
    that silently rots into someone else's address is worse than no URL. Falls
    back to the hostname, which is what MagicDNS resolves anyway.
    """
    import ipaddress
    import socket
    try:
        cgnat = ipaddress.ip_network("100.64.0.0/10")
        for fam, _t, _p, _c, sa in socket.getaddrinfo(socket.gethostname(), None):
            if fam == socket.AF_INET:
                try:
                    if ipaddress.ip_address(sa[0]) in cgnat:
                        return sa[0]
                except ValueError:
                    continue
    except OSError:
        pass
    return socket.gethostname().lower()


def build_gap(row, build=None, port=5000):
    """(alert, note) for one phone's reported build against the newest fetched one."""
    build = newest_build() if build is None else build
    have = str(row.get("app", "") or "")
    if not build:
        return None, "app %s (no build fetched on this PC)" % (have or "?")
    sha7 = build.get("sha7", "")
    if not have:
        return None, "app unknown (newest fetched %s)" % sha7
    if sha7 and sha7 in have:
        return None, "app %s -- the newest fetched build" % have
    url = "http://%s:%d/m" % (pc_tailnet_address(), port)
    return ("phone %s: running %s, but build %s has been fetched and waiting since %s -- "
            "that installed build predates the in-app updater so it cannot ask for it; "
            "open %s on the phone and tap install"
            % (row.get("node_id") or row.get("signer") or "?", have, sha7,
               build.get("built", "?"), url),
            "app %s, %s waiting (%s)" % (have, sha7, url))


def checkin_report(now=None, path=None):
    """(alerts, infos) for the watchdog: one info line per phone that has ever
    reported, and an ALERT for a phone that reported within a day and has
    been silent for SILENT_AFTER_S."""
    now = now if now is not None else time.time()
    alerts, infos = [], []
    for who, r in sorted(last_checkins(path).items()):
        age = now - float(r.get("at", 0))
        _gap, build_note = build_gap(r)
        line = "phone %s last seen %d min ago: height %s, peers %s, battery %s, %s" % (
            who, int(age // 60), r.get("chain_height", "?"), r.get("peers", "?"),
            r.get("battery", "?"), build_note)
        if SILENT_AFTER_S < age < 86400:
            # THE ALERT NAMES WHEN, NOT HOW LONG (2026-09-14). The watchdog keys an alert on
            # its first 80 characters and prints it again whenever that text changes, so a
            # minute count inside it made every single round "news": measured live, this one
            # line alerted and CLEARED once a minute for five hours while the phone was
            # simply switched off. That is A60's lesson exactly -- a reworded warning turning
            # a documented non-event into permanent noise. The moment the phone went quiet
            # does not change while it stays quiet, so the alert is printed once, rolled up
            # every 30 rounds, and CLEARED once when the phone comes back. The changing
            # minute count still exists, in the INFO line above, which is a heartbeat.
            alerts.append("phone %s: SILENT since %s (last: height %s) -- the node or the app stopped, or the Wi-Fi did" % (
                who, time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(float(r.get("at", 0)))), r.get("chain_height", "?")))
        else:
            infos.append(line)
    return alerts, infos


def build_report(now=None, path=None):
    """(alerts, infos): the phones whose installed build is not the newest fetched.

    Deliberately NOT part of checkin_report. That function answers one question --
    is this phone still reporting -- and D20/D20b pin its alert list exactly so a
    heartbeat cannot become a second source of noise. "You are holding a build
    older than the one on the PC" is a different question with a different life:
    it is true while the phone is switched off, it is cleared by a person rather
    than by time, and it must not stand beside a SILENT alert for the same phone.
    Two questions, two functions, two alert lists.
    """
    now = now if now is not None else time.time()
    alerts, infos = [], []
    build = newest_build()
    for who, r in sorted(last_checkins(path).items()):
        age = now - float(r.get("at", 0))
        gap, note = build_gap(r, build=build)
        if gap and age <= SILENT_AFTER_S:
            alerts.append(gap)
        elif gap:
            infos.append("phone %s is on an older build but is not reporting; nothing to do until it is back (%s)" % (who, note))
        else:
            infos.append("phone %s: %s" % (who, note))
    return alerts, infos


# ---------------------------------------------------------------- signing on this PC

def load_key(path=None):
    import covenant_unified_v8 as cov
    return cov.CovenantUnifiedMaster._load_or_create_identity(path or DEFAULT_KEY)


def pubkey_pem(key):
    from cryptography.hazmat.primitives import serialization
    return key.public_key().public_bytes(serialization.Encoding.PEM,
                                         serialization.PublicFormat.SubjectPublicKeyInfo).decode()


def sign_headers(key, method, path, body):
    import covenant_unified_v8 as cov
    return cov.sign_operator_request(key, pubkey_pem(key), method, path, body)


def decide_locally(decision_word, note="", key_path=None, plan_dir=None, approvals=None, signers_path=None, now=None):
    """Approve or decline today's plan with this PC's node key, through the
    same verification the route applies -- one ledger, one shape."""
    import base64
    plan = load(today(now), plan_dir)
    if not plan:
        return 404, {"status": "error", "message": "no plan written for today; run --write first"}
    key = load_key(key_path)
    body = json.dumps({"date": plan["date"], "plan_sha256": plan["sha256"], "decision": decision_word, "note": note}).encode("utf-8")
    h = sign_headers(key, "POST", APPROVE_PATH, body)
    pem = base64.b64decode(h["X-Operator-Pubkey"]).decode()
    ok, who = verify_signed(pem, "POST", APPROVE_PATH, body, h["X-Operator-Nonce"], h["X-Operator-Timestamp"],
                            h["X-Operator-Signature"], signers_path, now)
    if not ok:
        return 403, {"status": "error", "message": who}
    return handle_decision(body, who, pem, plan_dir, approvals)


def main():
    import argparse
    ap = argparse.ArgumentParser(description="the day's plan, the operator's signed approval, the trader's seventh gate")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--write", action="store_true")
    g.add_argument("--show", action="store_true")
    g.add_argument("--approve", action="store_true")
    g.add_argument("--decline", action="store_true")
    g.add_argument("--pubkey", action="store_true", help="print the public key of --key, to register it")
    g.add_argument("--register-signer", nargs=2, metavar=("NAME", "PEMFILE"))
    ap.add_argument("--note", default="")
    ap.add_argument("--key", default=DEFAULT_KEY, help="the node identity key that signs (default nodeA_prod.db.key)")
    a = ap.parse_args()
    if a.write:
        write(); return 0
    if a.register_signer:
        name, f = a.register_signer
        register_signer(name, open(f, encoding="utf-8").read())
        print("registered signer %r (%s)" % (name, SIGNERS)); return 0
    if a.pubkey:
        print(pubkey_pem(load_key(a.key)), end=""); return 0
    if a.approve or a.decline:
        code, out = decide_locally("approve" if a.approve else "decline", a.note, a.key)
        print(json.dumps(out, indent=1)); return 0 if code == 200 else 2
    plan = load()
    if not plan:
        print("no plan for today (%s); python covenant_daily_plan.py --write" % today()); return 2
    ok, why = approved()
    print(json.dumps({k: plan[k] for k in ("date", "written", "no_action_reason", "proposed_orders", "rule5", "armed", "halt", "caps", "sha256")}, indent=1))
    print("decision:", "APPROVED" if ok else "NOT APPROVED", "--", why)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
