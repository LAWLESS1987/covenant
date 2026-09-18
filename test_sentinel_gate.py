#!/usr/bin/env python3
"""test_sentinel_gate.py -- the Sentinel-Witness gate fails closed, on both
sides of the wire.

The seal service is exercised on loopback with a fake sealer (admit,
refuse, raise), so no node is needed. tradeGate.js cannot run here (no node
runtime on this machine), so its invariants are pinned by reading it: the
only executor path is behind the gate, every failure branch is a refusal,
and no "unlimited" limit can be expressed.

Reading a file is not running it, and J3 is where that bit: it compared two
str.find() results, which is satisfied by ABSENCE, and stayed green when the
guard it names was deleted from the source. J3b/J3c replace the claim with a
walk of executeIfAllowed that evaluates its guards -- see the walker below.
LICENCE: public domain.
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "sentinel_witness"))
import seal_service as SS  # noqa: E402

FAILS = []
N = 0


def ok(tag, name, cond, detail=""):
    global N
    N += 1
    print("   %s  %s %s  %s" % ("PASS" if cond else "FAIL", tag, name, str(detail)[:100]))
    if not cond:
        FAILS.append(tag)


def _cfg_for_live():
    """The operator's real trader config, for A6 -- which asks the REAL guards
    what they say about a real order rather than a fixture.

    A fixture would prove only that split_reasons partitions a list I wrote.
    What A6 is for is the measured fact that one live $25 buy produces a
    decision AND an abstention at the same time, which is why the three states
    could never have been exclusive. Falls back to a minimal armed config when
    there is no trader_config.json here, so the check still runs in a staging
    directory -- it asserts "at least one of each", not particular reasons.
    """
    try:
        import covenant_trader as T
        return T.load_config()
    except Exception:                                            # noqa: BLE001
        return {"armed": True}


def post(url, obj, raw=None):
    data = raw if raw is not None else json.dumps(obj).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")


# ---- the JS side has no runtime here, so executeIfAllowed is WALKED. --------
# J3 below compares two str.find() results, and that shape is satisfied by
# ABSENCE: str.find returns -1 for a guard that is not there, and -1 sorts
# before the executor call, so J3 stays green when the guard is DELETED.
# Proved by mutation 2026-09-09 -- with `if (!verdict.allowed) return` removed
# from tradeGate.js, the only thing standing between a refused verdict and the
# executor, this suite still reported 26/26 and J3 still said PASS. It stays
# green for a NEUTERED guard too (`verdict.allowed === "no"`), because that
# text is absent as well.
#
# So J3b/J3c do not look for the line. They split executeIfAllowed into its
# top-level statements, EVALUATE each guard's condition -- once against a
# refused verdict, once against an admitted one -- and report whether control
# reaches the executor. What the walker cannot read it reports as None, which
# fails both checks: an unreadable gate is a refusal, the same way the gate
# itself fails closed. This is not node and does not pretend to be; it reads
# only the shapes tradeGate.js is written in, and when it stops recognising
# them it gets louder, never quieter.


class _Obj:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def _typeof(x):
    if callable(x):
        return "function"
    if x is None:
        return "undefined"
    if isinstance(x, str):
        return "string"
    if isinstance(x, (int, float)):
        return "number"
    return "object"


def _close(s, i):
    """Index of the ) matching the ( at s[i]."""
    depth = 0
    for j in range(i, len(s)):
        if s[j] == "(":
            depth += 1
        elif s[j] == ")":
            depth -= 1
            if depth == 0:
                return j
    raise ValueError("unbalanced condition: %s" % s[:60])


def _js_truth(cond, env):
    """Evaluate one small JS condition (!, typeof, ===, !==, &&, ||) or raise."""
    py = cond.replace("!==", "\0").replace("!=", "\0").replace("===", "==")
    py = re.sub(r"typeof\s+([A-Za-z_$][\w$]*)", r"_typeof(\1)", py)
    py = py.replace("&&", " and ").replace("||", " or ").replace("!", " not ")
    py = py.replace("\0", "!=")
    py = re.sub(r"\btrue\b", "True", py)
    py = re.sub(r"\bfalse\b", "False", py)
    py = re.sub(r"\b(null|undefined)\b", "None", py)
    return bool(eval(py, {"__builtins__": {}}, dict(env, _typeof=_typeof)))


def _js_block(js, header):
    """The body of the function whose signature starts with `header`."""
    open_i = js.index("{", js.index(header))
    depth = 0
    for i in range(open_i, len(js)):
        if js[i] == "{":
            depth += 1
        elif js[i] == "}":
            depth -= 1
            if depth == 0:
                return js[open_i + 1:i]
    raise ValueError("unbalanced function body")


def _js_statements(block):
    """The top-level statements of a JS block, in order, comments dropped."""
    block = "\n".join(x for x in block.splitlines() if not x.strip().startswith("//"))
    out, cur, depth, quote, i = [], [], 0, "", 0
    while i < len(block):
        ch = block[i]
        cur.append(ch)
        if quote:
            if ch == "\\" and i + 1 < len(block):
                i += 1
                cur.append(block[i])
            elif ch == quote:
                quote = ""
        elif ch in "\"'`":
            quote = ch
        elif ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
            if depth == 0 and ch == "}":
                out.append("".join(cur)); cur = []
        elif ch == ";" and depth == 0:
            out.append("".join(cur)); cur = []
        i += 1
    out.append("".join(cur))
    return [x.strip() for x in out if x.strip()]


def _js_reaches_executor(js, allowed):
    """Walk executeIfAllowed with verdict.allowed = `allowed`. True if control
    reaches the executor call, False if it returns first, None if unreadable."""
    try:
        env = {"verdict": _Obj(allowed=allowed), "order": _Obj(), "opts": None,
               "executor": lambda *a: "filled"}
        for st in _js_statements(_js_block(js, "export async function executeIfAllowed")):
            if st.startswith("if"):
                lp = st.index("(")
                rp = _close(st, lp)
                if not _js_truth(st[lp + 1:rp], env):
                    continue
                st = st[rp + 1:].strip()
            if re.search(r"\bexecutor\s*\(", st):
                return True
            if st.startswith("return") or st.startswith("throw"):
                return False
        return False
    except Exception as e:
        print("      (the walker could not read executeIfAllowed: %r)" % (e,))
        return None


class FakeSealer:
    mode = "admit"

    def __call__(self, cfg, record):
        FakeSealer.last = record
        if FakeSealer.mode == "admit":
            return True, 'HTTP 200: {"admission": "admitted", "status": "accepted", "tx_id": "abc123"}'
        if FakeSealer.mode == "evicted":
            # THE ADMISSION THAT USED TO READ AS A REFUSAL. covenant_unified_v8
            # returns this from admit_pending_transaction when it makes room;
            # the old substring test was '"admitted"' in detail, and there is a
            # space after the word here, not a quote.
            return True, ('HTTP 200: {"admission": "admitted (evicted lowest-priority '
                          'pending transaction)", "status": "accepted", "tx_id": "ev99"}')
        if FakeSealer.mode == "refuse":
            return False, 'HTTP 403: {"admission": "refused", "reason": "Ethical violation: takes what is not the sender\'s"}'
        raise RuntimeError("node unreachable")


def main():
    print("sentinel gate -- seal service and tradeGate.js, fail closed")
    import socket
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    holder = {}
    # gate=... stubbed to "no reasons": S1-S10 are about the seal transport,
    # and the real preconditions get their own server at S11 below.
    threading.Thread(target=SS.serve, kwargs=dict(listen=("127.0.0.1", port), sealer=FakeSealer(), cfg={},
                                                  gate=lambda order, cfg: [],
                                                  ready=lambda srv: holder.setdefault("srv", srv)), daemon=True).start()
    for _ in range(50):
        if "srv" in holder:
            break
        time.sleep(0.05)
    url = "http://127.0.0.1:%d/seal" % port
    order = {"venue": "coinbase", "symbol": "XLM", "side": "buy", "amountUsd": 12.5, "note": "test"}

    code, body = post(url, order)
    ok("S1", "an admitted decision answers ok=true, admission=admitted, with the tx id",
       code == 200 and body.get("ok") is True and body.get("admission") == "admitted" and body.get("tx_id") == "abc123", body)
    ok("S2", "the record the sentinel judges carries the order as text",
       "proposed buy of $12.50 XLM on coinbase" in FakeSealer.last.get("text", ""), FakeSealer.last.get("text"))
    FakeSealer.mode = "refuse"
    code, body = post(url, order)
    ok("S3", "a refused decision answers ok=false, admission=refused, with the reason",
       code == 200 and body.get("ok") is False and body.get("admission") == "refused" and "Ethical violation" in body.get("detail", ""), body)
    FakeSealer.mode = "raise"
    code, body = post(url, order)
    ok("S4", "a sealer that raises is a refusal, never an allowance", code == 500 and body.get("ok") is False, body)
    FakeSealer.mode = "admit"
    code, body = post(url, {"venue": "coinbase", "symbol": "XLM", "side": "hold", "amountUsd": 5})
    ok("S5", "an order with a bad side is refused before any seal", code == 400 and body.get("ok") is False)
    code, body = post(url, {"venue": "coinbase", "symbol": "XLM", "side": "buy", "amountUsd": "NaN"})
    ok("S6", "a NaN amount is refused", code == 400 and body.get("ok") is False)
    code, body = post(url, None, raw=b"not json")
    ok("S7", "a non-JSON body is refused", code == 400 and body.get("ok") is False)
    code, body = post(url, {"venue": "x", "symbol": "y", "side": "buy", "amountUsd": 1, "note": "z" * 9000})
    ok("S8", "an oversized body is refused", code == 400 and body.get("ok") is False)
    code, body = post(url.replace("/seal", "/other"), order)
    ok("S9", "only /seal exists", code == 404)
    ok("S10", "the service binds to loopback only", SS.LISTEN[0] == "127.0.0.1")

    # S11 IS THE FIRST OF THE TWO SEAL FIXES. An eviction admission is an
    # admission. Before 2026-09-07 this answered ok=false and the decision the
    # judges had ADMITTED was recorded by the gate as a refusal.
    FakeSealer.mode = "evicted"
    code, body = post(url, order)
    ok("S11", "an 'admitted (evicted ...)' answer is an admission, not a refusal",
       code == 200 and body.get("ok") is True and body.get("sealed") is True
       and body.get("tx_id") == "ev99", body)
    # S12 IS THE SECOND. The admission is read as a FIELD, so it does not
    # depend on where the node happens to serialise it or on the 160-character
    # truncation of the prose.
    FakeSealer.mode = "admit"
    res = SS._as_result((True, 'HTTP 200: {"status": "accepted", "tx_id": "z9", '
                               '"admission": "admitted"}'))
    ok("S12", "the admission is read as a field, so key order does not decide it",
       SS.admitted(res) and res["tx_id"] == "z9", res)
    ok("S13", "a 200 that carried some other admission string is NOT admitted",
       not SS.admitted({"ok": True, "admission": "quarantined"}))
    holder["srv"].shutdown()

    # ---- S14+: THE CONSOLIDATION. Sealed is not allowed. -------------------
    s2 = socket.socket(); s2.bind(("127.0.0.1", 0)); port2 = s2.getsockname()[1]; s2.close()
    holder2 = {}
    FakeSealer.mode = "admit"
    # A config that clears `armed` and the seal, so that what refuses below is
    # the preconditions and nothing else.
    live_cfg = {"armed": True, "seal_required": False, "max_order_usd": 25.0,
                "max_daily_notional_usd": 50.0, "max_orders_per_day": 2,
                "min_order_usd": 5.0, "min_sealed_signals": 0}
    threading.Thread(target=SS.serve, kwargs=dict(listen=("127.0.0.1", port2), sealer=FakeSealer(),
                                                  cfg=live_cfg,
                                                  ready=lambda srv: holder2.setdefault("srv", srv)),
                     daemon=True).start()
    for _ in range(50):
        if "srv" in holder2:
            break
        time.sleep(0.05)
    url2 = "http://127.0.0.1:%d/seal" % port2

    code, body = post(url2, order)
    ok("S14", "an ADMITTED seal is no longer enough on its own -- the trader's "
              "preconditions are asked and they refuse",
       code == 200 and body.get("sealed") is True and body.get("ok") is False
       and body.get("blocked_by"), body)
    ok("S15", "...and the refusal names the reason, rather than failing silently",
       any("portfolio" in r for r in body.get("blocked_by", [])), body.get("blocked_by"))
    code, body = post(url2, dict(order, side="sell"))
    ok("S16", "a SELL is refused here too: the reserve floor is clamped on the "
              "quantity by the planner, and this path has no holdings to clamp",
       body.get("ok") is False and any("reserve floor" in r for r in body.get("blocked_by", [])),
       body.get("blocked_by"))
    code, body = post(url2, dict(order, amountUsd=500.0))
    ok("S17", "an order over the per-trade cap is refused by the SAME cap the "
              "trader uses, not by a second copy of the number",
       body.get("ok") is False
       and any("25" in r for r in body.get("blocked_by", [])), body.get("blocked_by"))
    holder2["srv"].shutdown()

    # S18: the property that makes this safe to have done at all.
    import inspect
    import guards as G
    ok("S18", "caller reasons are APPEND ONLY, so the sentinel path cannot be "
              "looser than the trader's on the same order",
       G._caller_reasons("trader", {"side": "buy"}, None) == []
       and len(G._caller_reasons("sentinel", {"side": "buy"}, None)) >= 1)
    ok("S19", "there is ONE preconditions implementation and the trader delegates to it",
       "_guards.preconditions(" in io.open(os.path.join(HERE, "covenant_trader.py"),
                                           encoding="utf-8").read()
       and callable(G.preconditions))

    js = io.open(os.path.join(HERE, "sentinel_witness", "tradeGate.js"), encoding="utf-8").read()
    ok("J1", "tradeGate.js exports TIERS, enableAutomated, gateTrade and executeIfAllowed",
       all(("export " in js and name in js) for name in ("TIERS", "enableAutomated", "gateTrade", "executeIfAllowed")))
    ok("J2", "no unlimited option can be expressed", "unlimited option" in js and "Infinity" not in js.replace("Number.isFinite", ""))
    body_exec = js[js.find("export async function executeIfAllowed"):]
    ok("J3", "the executor runs only after allowed is checked",
       body_exec.find("if (!verdict.allowed) return") < body_exec.find("await executor(order, verdict)"))
    # J3b/J3c ARE THE REAL FORM OF J3'S CLAIM (see the walker above). J3 is
    # kept because it still documents the intended shape, but it is satisfied
    # by absence and cannot carry this on its own. The pair kills: deleting the
    # guard, inverting it, neutering its condition so it never fires, and
    # moving the executor call above it -- and J3c is what stops the cheapest
    # "repair" of all, refusing everything.
    on_refused, on_admitted = _js_reaches_executor(js, False), _js_reaches_executor(js, True)
    ok("J3b", "walked with a REFUSED verdict, no path through executeIfAllowed reaches the executor",
       on_refused is False, on_refused)
    ok("J3c", "...and with an ADMITTED verdict it does reach it, so the gate is not a blanket refusal",
       on_admitted is True, on_admitted)
    body_gate = js[js.find("export async function gateTrade"):js.find("export async function executeIfAllowed")]
    ok("J4", "every failure branch in gateTrade is a refusal: unreachable, non-JSON, HTTP error, not admitted, no fetch",
       all(s in body_gate for s in ("unreachable or timed out", "answered without JSON", "answered HTTP", "not admitted", "no fetch available")))
    ok("J5", "only an exact admitted answer allows",
       'body.ok === true && body.admission === "admitted"' in body_gate and body_gate.count("allowed: true") == 1)
    ok("J6", "the seal request has a timeout", "AbortController" in body_gate and "setTimeout" in body_gate)
    ok("J7", "tierNavigation.js's import of TIERS from ./tradeGate.js now resolves",
       os.path.exists(os.path.join(HERE, "sentinel_witness", "tradeGate.js"))
       and 'from "./tradeGate.js"' in io.open(os.path.join(HERE, "sentinel_witness", "tierNavigation.js"), encoding="utf-8").read())

    # ---- A: THE THIRD STATE (2026-09-18, spec A1-A4) ---------------------
    #
    # Until today three different situations collapsed into ok:false -- the
    # judge refused, a guard refused, and NOBODY COULD EVALUATE IT. The first
    # two are decisions; the third is the absence of one. Both must refuse, and
    # they did, but reporting them identically meant the gate's 100% refusal
    # rate was evidence of nothing about the rules.
    import guards as _G
    ADM = lambda cfg, rec: {"ok": True, "admission": "admitted", "tx_id": "t1", "detail": "sealed"}
    REF = lambda cfg, rec: {"ok": False, "admission": "refused", "tx_id": None, "detail": "judge said no"}
    def BOOM(cfg, rec):
        raise RuntimeError("node unreachable")

    ORD = {"venue": "kraken", "symbol": "XRP", "side": "buy", "amountUsd": 25.0}

    c, b = SS.seal(ORD, sealer=ADM, cfg={}, gate=lambda o, cf: [])
    ok("AB1", "a clear order is verdict=allow and ok=true",
       c == 200 and b["verdict"] == "allow" and b["ok"] is True, b["verdict"])
    c, b = SS.seal(ORD, sealer=ADM, cfg={}, gate=lambda o, cf: ["per-trade cap"])
    ok("AB2", "a GUARD refusing is verdict=refuse, and the reason is in refused_by",
       c == 200 and b["verdict"] == "refuse" and b["ok"] is False
       and b["refused_by"] == ["per-trade cap"] and b["abstained_by"] == [], b["verdict"])
    c, b = SS.seal(ORD, sealer=REF, cfg={})
    ok("AB3", "the JUDGE refusing is verdict=refuse -- it decided, so it is not an abstention",
       c == 200 and b["verdict"] == "refuse" and b["sealed"] is False, b["verdict"])
    c, b = SS.seal(ORD, sealer=BOOM, cfg={})
    ok("AB4", "a seal that CANNOT HAPPEN is verdict=abstain, not refuse -- nobody was asked",
       c == 500 and b["verdict"] == "abstain" and b["ok"] is False
       and len(b["abstained_by"]) == 1, b["verdict"])
    ok("AB5", "...and an abstention still refuses: ok is false in every non-allow verdict",
       all(SS.seal(o, sealer=s, cfg={}, gate=g)[1]["ok"] is False
           for o, s, g in ((ORD, REF, None), (ORD, BOOM, None),
                           (ORD, ADM, lambda o, cf: ["x"]))), "fail-closed")

    # A6 -- THE LIVE CASE, and the reason A1-A5 are not academic. The real
    # guards return BOTH kinds for one $25 buy: Rule 5 deciding against it, and
    # the buy-side guards unable to evaluate without a portfolio.
    reasons = _G.preconditions({"side": "buy", "usd": 25.0, "sym": "XRP"},
                               cfg=_cfg_for_live(), sealed_ok=True,
                               guard_blocks=None, caller="sentinel")
    rs, ab = _G.split_reasons(reasons)
    ok("AB6", "one real order yields a decision AND an abstention together, so these were never exclusive states",
       len(rs) >= 1 and len(ab) >= 1, "%d refusal(s), %d abstention(s)" % (len(rs), len(ab)))
    ok("AB7", "the classifier is EXACT -- a reworded abstention is not silently one",
       _G.is_abstention(_G.NO_PORTFOLIO) and not _G.is_abstention(_G.NO_PORTFOLIO + ".")
       and not _G.is_abstention("Rule 5: 2 sealed signals on record, need 30"), "exact membership")
    ok("AB8", "guards.preconditions still returns the FLAT list its other callers read",
       isinstance(reasons, list) and all(isinstance(x, str) for x in reasons)
       and sorted(rs + ab) == sorted(reasons), "%d reason(s), partition is lossless" % len(reasons))

    # A9 -- every body the service emits carries a verdict. These paths used to
    # return {"ok": false, "detail": ...} with no verdict at all, and null is
    # not "refuse": a caller switching on the verdict fell through a hole.
    bodies = [SS.seal({"venue": "k", "symbol": "X", "side": "nope", "amountUsd": 1}, sealer=ADM, cfg={})[1],
              SS.seal({"venue": "k", "symbol": "X", "side": "buy", "amountUsd": float("nan")}, sealer=ADM, cfg={})[1],
              SS._bad_request("only POST /seal exists here")]
    ok("AB9", "EVERY emitted body carries one of the three verdicts -- never null",
       all(x.get("verdict") in ("allow", "refuse", "abstain") for x in bodies),
       [x.get("verdict") for x in bodies])

    # ---- W2: THE WITNESS IS NOT AN AUTHORITY (spec section 3, step 3) -----
    #
    # The separation the operator asked for. Three roles decide (judge, guard,
    # the request parser); the WITNESS only records. W2 was [UNVERIFIED] in the
    # spec -- true by construction because nothing reads the chain back to
    # decide, with nothing checking that it stays true. This is that check.
    # DRIVEN, NOT READ. The first version of W2a/W2b inspected seal_service.py's
    # source text for the absence of "tx_id" and the presence of "either way" --
    # which is the fake-guard shape this repository has already paid for once
    # (35 of 36 suspected guards grepped source instead of running the code).
    # Both are now properties of the running objects.
    import inspect as _inspect
    sig = list(_inspect.signature(SS._envelope).parameters)
    ok("WS1", "the verdict function takes ONLY the judge's answer and the two reason "
       "lists -- the record, its tx_id and its prose are not parameters at all",
       sig == ["sealed", "refused_by", "abstained_by"], sig)

    # W2b: the witness must record a proposal the gate goes on to refuse. Asked
    # by counting the sealer's calls with a gate that refuses everything.
    _calls = []
    def _counting_sealer(cf, rec):
        _calls.append(rec)
        return {"ok": True, "admission": "admitted", "tx_id": "t%d" % len(_calls), "detail": "sealed"}
    c3, b3 = SS.seal(ORD, sealer=_counting_sealer, cfg={}, gate=lambda o, cf: ["per-trade cap"])
    ok("WS2", "a proposal the guards REFUSE was still sealed -- the record is written "
       "either way, so this is an audit trail and not a list of permissions",
       len(_calls) == 1 and b3["verdict"] == "refuse" and b3["ok"] is False
       and _calls[0].get("side") == "buy",
       "sealer called %d time(s), verdict %s" % (len(_calls), b3["verdict"]))
    # Driven, not just read: change ONLY the witness's fields and the verdict
    # must not move. A witness that could alter a verdict is the conflation.
    c1, b1 = SS.seal(ORD, sealer=lambda cf, r: {"ok": True, "admission": "admitted", "tx_id": "AAA", "detail": "one"}, cfg={}, gate=lambda o, cf: [])
    c2, b2 = SS.seal(ORD, sealer=lambda cf, r: {"ok": True, "admission": "admitted", "tx_id": "ZZZ", "detail": "quite different prose"}, cfg={}, gate=lambda o, cf: [])
    ok("WS3", "two records differing ONLY in tx_id and detail produce the identical verdict -- the record cannot vote",
       (b1["verdict"], b1["ok"]) == (b2["verdict"], b2["ok"]) and b1["tx_id"] != b2["tx_id"],
       "%s/%s vs %s/%s" % (b1["verdict"], b1["tx_id"], b2["verdict"], b2["tx_id"]))

    print("SENTINEL-GATE: %d/%d passed" % (N - len(FAILS), N))
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
