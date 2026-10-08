#!/usr/bin/env python3
"""test_a314_persona_feed.py -- A314: a refinement pass is shown as the operator's words only what came from him.

WHY. A233 left one machine address (127.0.0.2) out of covenant_persona.his_side by name. Machine prompts then
reached a pass from 127.0.0.3 (a session's correction request, 2026-10-06) and from scripts posting to /pc/council
on 127.0.0.1 (2026-09-28). Tetsu's register copied them word for word, and every ask carried them: on 2026-10-08
the rhythm exam (collective #5) drew "Please WRITE a short public correction" and a stale "quota full" CI
diagnosis out of him. His words are now defined by where they come from -- an address that is not loopback (his
phone, the LAN), or a browser page on this PC, whose rows the doors mark "page": true. His words: "fix the
persona feed don't alter his memory".

WHAT IT PINS (every check runs the code; none greps it).
  R1-R4  the rule: is_his_word on every caller seen in the real log, and on the edge cases
  H1-H2  his_side on a log that replays the incident: his phone and his page are shown, the machine prompts are not;
         the log is read, never written
  F1     page_request: Fetch Metadata or Origin marks a browser; a script's headers do not
  D1-D2  /m/agent and /pc/council through the real handlers (stub model): a page's ask is marked "page": true, a
         script's is not, and his_side then shows the one and not the other
  M1-M2  mutations: the A233 rule restored, then page_request switched off -- each turns its check red

Nothing here touches the real ask log, persona file or network: every path is redirected, the model is the stub.
"""
import hashlib
import json
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", label, "" if ok else "  -- " + str(detail)[:300]), flush=True)


def rows_of(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return [json.loads(l) for l in fh if l.strip()]
    except OSError:
        return []


INCIDENT = [  # the callers and texts of the real log (ops/chat/ask_log.jsonl) that reached his register; his own addresses are fictional stand-ins (opsec)
    {"kind": "agent", "from": "127.0.0.3", "text": "Please WRITE a short public correction (you are not reviewing anything)."},
    {"kind": "council", "from": "127.0.0.1", "text": "Lawrence gave you a standing directive today. In three short sentences: what is your daily duty"},
    {"kind": "council", "from": "127.0.0.1", "text": "Today the phone build broke on GitHub Actions artifact storage (quota full)."},
    {"kind": "agent", "from": "127.0.0.2", "text": "batch item: classify this"},
]
HIS = [
    {"kind": "agent", "from": "100.72.0.10", "text": "recap updates"},
    {"kind": "agent", "from": "10.0.0.50", "text": "Ask the ambassador"},
    {"kind": "council", "from": "127.0.0.1", "text": "what improvements are needed", "page": True},
]


def main():
    os.environ["COVENANT_MODEL_STUB"] = "1"
    os.environ["COVENANT_TETSU_IMMUNITY"] = tempfile.mktemp(suffix="_a314_no_immunity.json")
    os.environ["COVENANT_TETSU_IMMUNITY_LEDGER"] = tempfile.mktemp(suffix="_a314_immunity.jsonl")
    os.environ["COVENANT_PAUSE_DIR"] = tempfile.mkdtemp(prefix="a314_pause_")
    d = tempfile.mkdtemp(prefix="a314_")
    os.environ["COVENANT_ASK_LOG"] = os.path.join(d, "ask_log.jsonl")
    os.environ["COVENANT_TEACHER_QUEUE"] = os.path.join(d, "teacher_queue.jsonl")
    os.environ["COVENANT_TETSU_BLOCKS"] = os.path.join(d, "blocks.json")
    import covenant_persona as P

    # ---- R: the rule ------------------------------------------------------------------------
    check("R1 his phone (tailnet) and the LAN are his words",
          all(P.is_his_word(r) for r in HIS[:2]), [P.is_his_word(r) for r in HIS[:2]])
    check("R2 every machine caller of the incident is not -- 127.0.0.3, 127.0.0.1 without a page, 127.0.0.2",
          not any(P.is_his_word(r) for r in INCIDENT), [P.is_his_word(r) for r in INCIDENT])
    check("R3 a browser page on this PC is his word (page: true, exactly)",
          P.is_his_word(HIS[2]) and not P.is_his_word(dict(HIS[2], page="true")))
    edge = [{"kind": "agent", "from": "::ffff:127.0.0.1", "text": "x"}, {"kind": "agent", "from": "::1", "text": "x"},
            {"kind": "agent", "from": "", "text": "x"}, {"kind": "agent", "text": "x"},
            {"kind": "image", "from": "100.72.0.10", "text": "x"}, {"kind": "ask", "from": "100.72.0.10", "text": "x"}]
    check("R4 mapped and IPv6 loopback, an unknown caller, and a kind that is not a conversation are not his words",
          not any(P.is_his_word(r) for r in edge), [P.is_his_word(r) for r in edge])

    # ---- H: his_side on the incident ---------------------------------------------------------
    nowt = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
    log = os.path.join(d, "incident.jsonl")
    with open(log, "w", encoding="utf-8") as fh:
        for r in INCIDENT[:1] + HIS[:1] + INCIDENT[1:] + HIS[1:]:
            fh.write(json.dumps(dict(r, t=nowt)) + "\n")
    before = hashlib.sha256(open(log, "rb").read()).hexdigest()
    hs = P.his_side(log)
    check("H1 a pass is shown his phone, his LAN ask and his page -- none of the machine prompts",
          hs == ["recap updates", "Ask the ambassador", "what improvements are needed"], hs)
    check("H2 the log is read, never written (his memory is left as it is)",
          hashlib.sha256(open(log, "rb").read()).hexdigest() == before)

    # ---- F: page_request ---------------------------------------------------------------------
    class Broken:
        def get(self, k):
            raise RuntimeError("no headers")
    check("F1 Fetch Metadata or Origin marks a browser; a script's headers and a broken object do not",
          P.page_request({"Sec-Fetch-Mode": "cors"}) and P.page_request({"Origin": "http://127.0.0.1:5000"})
          and not P.page_request({"User-Agent": "Python-urllib/3.12"}) and not P.page_request(Broken()))

    # ---- D: the real doors -------------------------------------------------------------------
    import covenant_unified_v8 as cov
    m = cov.CovenantUnifiedMaster("A314", host="127.0.0.1", port=5431, p2p_port=5432,
                                  db_path=tempfile.mktemp(suffix="_a314.db"))
    m.add_genesis_block()
    m.node.sentinel = cov.ReasoningSentinel(cov.MockJudge(), cov.DIVINE_PRINCIPLES)
    client = m.api.app.test_client()
    page = {"Sec-Fetch-Mode": "cors", "Sec-Fetch-Site": "same-origin", "Origin": "http://127.0.0.1:5000"}
    alog = os.environ["COVENANT_ASK_LOG"]

    def door(path, text, headers=None, addr="127.0.0.1"):
        r = client.post(path, json={"text": text}, headers=headers or {}, environ_base={"REMOTE_ADDR": addr})
        rows = [x for x in rows_of(alog) if x.get("text") == text]
        return r.status_code, (rows[-1] if rows else None)

    out = {}
    for path, kind in (("/m/agent", "agent"), ("/pc/council", "council")):
        c1, from_page = door(path, "A314 %s from the page" % kind, headers=page)
        c2, from_script = door(path, "A314 %s from a script" % kind)
        out[kind] = (c1, c2, from_page, from_script)
        check("D1 %s: a browser page's ask is logged with page: true, a script's without it" % path,
              c1 == 200 and c2 == 200 and from_page and from_page.get("page") is True
              and from_script and "page" not in from_script,
              (c1, c2, from_page and from_page.get("page"), from_script and from_script.get("page")))
    hs2 = P.his_side(alog)
    check("D2 his_side over the doors' own rows: both page asks are his words, neither script ask is",
          "A314 agent from the page" in hs2 and "A314 council from the page" in hs2
          and not any("from a script" in h for h in hs2), hs2)

    # ---- M: mutations, both ways ---------------------------------------------------------------
    real_rule, real_page = P.is_his_word, P.page_request

    def a233_rule(r):  # the rule as it stood before A314
        return r.get("kind") in ("agent", "council") and r.get("from") not in P.WORK_CALLERS
    P.is_his_word = a233_rule
    try:
        hs_old = P.his_side(log)
    finally:
        P.is_his_word = real_rule
    check("M1 with the A233 rule restored, the incident's machine prompts are shown as his words again (H1 red)",
          any("Please WRITE a short public correction" in h for h in hs_old)
          and hs_old != ["recap updates", "Ask the ambassador", "what improvements are needed"], hs_old)
    P.page_request = lambda headers: False
    try:
        _c, mutated = door("/m/agent", "A314 agent from the page, mutated", headers=page)
    finally:
        P.page_request = real_page
    check("M2 with page_request switched off, a page's ask is not marked (D1 red)",
          mutated is not None and "page" not in mutated, mutated)

    bad = results.count(False)
    print("A314: %d/%d passed" % (len(results) - bad, len(results)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
