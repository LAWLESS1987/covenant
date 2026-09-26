#!/usr/bin/env python3
"""CC1 -- a code question answered by several systems, and a consensus that is
measured or declared UNDETERMINED. RUN with a stub model and temp ledgers,
and through the real /m/code door on a test node.

Pins covenant_code_consensus (2026-09-21, his words: "The code option must be
synced with the pc and double checked across multiple systems to find logic
reason and consensus"):

  CC1a  open_question runs the council (three roles, the stub) and opens one
        consult seat per model through the consult gate; the row records the
        council's final, the cycle and its seats; an excerpt carrying a key
        refuses every seat and the row says so; a council that raises is
        recorded as an error, not raised.
  CC1b  consensus with only the council answered is UNDETERMINED with the
        digest; after one seat's answer is recorded (two systems) the
        synthesiser is asked with BOTH answers and its text, judged clean, is
        the consensus; a held synthesis returns the digest; a raising model
        returns the digest; an unknown id is UNKNOWN. Each is recorded.
  CC1c  the real door: /m/code from the tailnet answers 200 with the id, the
        council's answer, the cycle and its seats; the LAN is refused 403;
        /m/code/<id> is UNDETERMINED at one answered system and 404 for an
        unknown id.
"""
import json
import os
import sys
import tempfile

os.environ.setdefault("COVENANT_QUIET", "1")
TMP = tempfile.mkdtemp(prefix="cc1_")
os.environ["COVENANT_CODE_CONSENSUS"] = os.path.join(TMP, "code.jsonl")
os.environ["COVENANT_AI_CONSULT_LEDGER"] = os.path.join(TMP, "consult.jsonl")
os.environ["COVENANT_ASK_LOG"] = os.path.join(TMP, "ask.jsonl")
os.environ["COVENANT_TEACHER_QUEUE"] = os.path.join(TMP, "queue.jsonl")
os.environ["COVENANT_MODEL_STUB"] = "1"
HERE = os.path.dirname(os.path.abspath(__file__)) or "."
sys.path.insert(0, HERE)

import covenant_ai_consult as AC        # noqa: E402
import covenant_code_consensus as CCN   # noqa: E402

FAILURES = []
PASSED = [0]
CPATH = AC.LEDGER


def check(label, ok, detail=""):
    print("  %-76s %s%s" % (label, "OK" if ok else "*** FAIL ***", ("  " + str(detail)[:300]) if detail and not ok else ""))
    if ok:
        PASSED[0] += 1
    else:
        FAILURES.append(label)


def role_ask(msgs, max_tokens=0):
    sysm = msgs[0]["content"]
    if "final answer for the person" in sysm:
        role = "reviser"
    elif "read the proposer's answer" in sysm:
        role = "critic"
    elif "AGREED" in sysm:
        role = "synth"
    else:
        role = "proposer"
    return "%s says: use a bounded queue" % role, {"model": "stub"}


def main():
    print("CC1a -- open_question")
    row = CCN.open_question("Is this loop safe under concurrent writers?", "for x in q: q.append(x)", from_addr="100.1.1.1",
                            ask=role_ask, models=["gpt-6-astra", "claude"], system="fixed rules", consult_path=CPATH)
    check("CC1a the council's final answer (the reviser's) and model are recorded, three roles ran",
          row["council"]["final"].startswith("reviser says") and row["council"]["roles"] == 3 and row["council"]["model"] == "stub", row["council"])
    # A180: the roster drives the final scan (gpt-6-astra) LAST whatever order was passed
    check("CC1a one consult seat per model under one cycle, through the consult gate, the final scan last", row["cycle"] and row["seats"] == ["claude", "gpt-6-astra"] and row["refused"] == [], row)
    seats = [r for r in AC._rows(CPATH) if r.get("kind") == "seat" and r.get("cycle") == row["cycle"]]
    check("CC1a the consult ledger carries the two seat rows linked to their intents", len(seats) == 2 and all(s.get("intent_id") for s in seats), seats)
    bad = CCN.open_question("why?", "token = 'ghp_abcdefghijklmnopqrstuvwxyz0123'", from_addr="cli", ask=role_ask, models=["claude"], system="x", consult_path=CPATH)
    check("CC1a an excerpt carrying a key: every seat refused and the row says why; the council still answered on the PC",
          bad["cycle"] is None or bad["seats"] == [], (bad["seats"], bad["refused"]))
    check("CC1a the refusal names the reason", bad["refused"] and bad["refused"][0][0] == "claude" and bad["refused"][0][1], bad["refused"])

    def boom(msgs, max_tokens=0):
        raise RuntimeError("no model")
    err = CCN.open_question("q?", "", from_addr="cli", ask=boom, models=["claude"], system="x", consult_path=CPATH)
    check("CC1a a council that raises is recorded as an error, the seats still open", "error" in err["council"] and err["seats"] == ["claude"], err["council"])
    try:
        CCN.open_question("   ", "", ask=role_ask)
        empty_ok = False
    except ValueError:
        empty_ok = True
    check("CC1a an empty question is refused", empty_ok)

    print("CC1b -- consensus")
    r = CCN.consensus(row["id"], ask=role_ask, judge=lambda t: (True, ""), consult_path=CPATH)
    check("CC1b with only the council answered (1 of 3) it is UNDETERMINED and carries the digest, no synthesis",
          r["state"] == "UNDETERMINED" and r["answered"] == 1 and r["of"] == 3 and "council:stub" in r["text"] and "(no answer recorded)" in r["text"], r)
    AC.record_result(seats[0]["intent_id"], "The loop appends while iterating; use a bounded queue and a lock.", app="chatsmith", path=CPATH)
    seen = []
    def synth_ask(msgs, max_tokens=0):
        seen.append(msgs[-1]["content"])
        return "AGREED: use a bounded queue. DISPUTED: none. UNJUDGED: the lock.", {"model": "stub"}
    r2 = CCN.consensus(row["id"], ask=synth_ask, judge=lambda t: (True, "clean"), consult_path=CPATH)
    check("CC1b with two systems answered the synthesiser is asked with BOTH answers and its clean text is the consensus",
          r2["state"] == "consensus" and r2["answered"] == 2 and r2["text"].startswith("AGREED") and seen
          and "reviser says" in seen[-1] and "bounded queue and a lock" in seen[-1] and ("ANSWER FROM seat:%s" % seats[0]["model"]) in seen[-1], (r2, seen[-1:]))
    r3 = CCN.consensus(row["id"], ask=synth_ask, judge=lambda t: (False, "HOLD"), consult_path=CPATH)
    check("CC1b a held synthesis returns the digest, state digest, with the reason", r3["state"] == "digest" and "held by the gate" in r3["why"] and "## seat:gpt-6-astra" in r3["text"], r3)
    r4 = CCN.consensus(row["id"], ask=boom, judge=lambda t: (True, ""), consult_path=CPATH)
    check("CC1b a raising model returns the digest, never raises", r4["state"] == "digest" and "no synthesis" in r4["why"], r4)
    check("CC1b an unknown id is UNKNOWN", CCN.consensus("nope", ask=synth_ask)["state"] == "UNKNOWN")
    rows = [x for x in CCN._rows() if x.get("kind") == "consensus" and x.get("id") == row["id"]]
    check("CC1b every consensus pass is recorded (four rows for this question)", len(rows) == 4 and [x["state"] for x in rows] == ["UNDETERMINED", "consensus", "digest", "digest"], [x["state"] for x in rows])
    check("CC1b the real gate on this node passes a plain synthesis (measured)", CCN._gate("AGREED: use a bounded queue. DISPUTED: none. UNJUDGED: none.")[0] is True)

    print("CC1c -- the real door")
    import test_pc1_sister_interface as PC1
    m = PC1.fresh_master("CC1", 5398)
    client = m.api.app.test_client()
    PHONE, LAN = "100.72.0.10", "192.168.1.50"
    r = PC1.post(client, "/m/code", PHONE, {"text": "STUB>> proposer: is this loop safe?", "excerpt": "for x in q: q.append(x)"})
    j = r.get_json() or {}
    check("CC1c /m/code from the tailnet: 200 with the id, the council's answer (the stub), the cycle and its seats",
          r.status_code == 200 and j.get("status") == "success" and j.get("id") and j.get("council") and j.get("cycle") and len(j.get("seats") or []) >= 1, (r.status_code, {k: j.get(k) for k in ("status", "id", "cycle", "seats", "council_error")}))
    r = PC1.post(client, "/m/code", LAN, {"text": "hello"})
    check("CC1c the LAN is refused 403", r.status_code == 403, r.status_code)
    r = PC1.post(client, "/m/code", PHONE, {"text": "   "})
    check("CC1c an empty question is refused 400", r.status_code == 400, r.status_code)
    r = PC1.get(client, "/m/code/" + str(j.get("id")), PHONE)
    j2 = r.get_json() or {}
    check("CC1c /m/code/<id> with one system answered is UNDETERMINED with the count and the digest",
          r.status_code == 200 and j2.get("state") == "UNDETERMINED" and j2.get("answered") == 1 and j2.get("of", 0) >= 2 and "no answer recorded" in j2.get("text", ""), j2)
    r = PC1.get(client, "/m/code/nope", PHONE)
    check("CC1c an unknown id is 404", r.status_code == 404, r.status_code)
    r = PC1.get(client, "/m/code/" + str(j.get("id")), LAN)
    check("CC1c the LAN cannot read a consensus either", r.status_code == 403, r.status_code)

    print()
    print("%d passed, %d failed" % (PASSED[0], len(FAILURES)))
    if FAILURES:
        print("CC1 result: FAILED (%d)" % len(FAILURES))
        for f in FAILURES:
            print("  - %s" % f)
        return 1
    print("CC1 result: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
