#!/usr/bin/env python3
"""PC1 -- the sister interface on the PC: /pc, /pc/council, /pc/training.

Pins covenant_council (2026-09-21, his words: "need a sister interface app on
the pc which can use multi agents for reasoning and training to graduate to an
agent") by RUNNING the doors against a fresh master with the stub model:

  PC1a  /pc answers loopback and the tailnet with HTML, every placeholder
        filled; a LAN address is refused 403 and the refusal is recorded;
        mutation: guard off, the same LAN request succeeds; restored, refused.
  PC1b  /pc/council runs the three roles IN ORDER, each handed more than the
        one before (the stub names what it was given), the reviser's answer
        is the council's, and it is judged: the reply carries the verdict.
  PC1c  both sides of the council go to the teacher's queue and the exchange
        to the chat memory, at the redirected paths, never the real ones.
  PC1d  /pc/training is JSON with the queue, the ledger, the exam, the last
        nightly and five graduation criteria, the fifth UNDETERMINED and
        `graduated` False on one machine; it refuses a LAN address.
  PC1e  a burst is bounded: a 429 appears within 31 councils.
  PC1f  deliberate() is pure apart from ask: a fake ask sees three calls
        with the roles' briefs in order and the prior steps carried forward.
"""
import json
import os
import re
import sys
import tempfile

os.environ.setdefault("COVENANT_QUIET", "1")
HERE = os.path.dirname(os.path.abspath(__file__)) or "."
sys.path.insert(0, HERE)

import covenant_unified_v8 as cov      # noqa: E402
import covenant_council as C           # noqa: E402

results = []


def check(label, ok, detail=""):
    results.append((label, bool(ok)))
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}" + (f"  -- {str(detail)[:300]}" if detail else ""))


def fresh_master(name="PC1", port=5397):
    tmp = tempfile.mktemp(suffix=f"_{name}.db")
    m = cov.CovenantUnifiedMaster(name, host="127.0.0.1", port=port, p2p_port=port + 1, db_path=tmp)
    m.add_genesis_block()
    m.node.sentinel = cov.ReasoningSentinel(cov.MockJudge(), cov.DIVINE_PRINCIPLES)
    return m


def get(client, path, addr):
    return client.get(path, environ_base={"REMOTE_ADDR": addr})


def post(client, path, addr, body):
    return client.post(path, data=json.dumps(body), content_type="application/json", environ_base={"REMOTE_ADDR": addr})


def refusals(master, kind):
    row = master.node.anomaly_monitor.report().get("per_kind", {}).get(kind, 0)
    return row.get("recent", 0) if isinstance(row, dict) else int(row or 0)


def main():
    os.environ["COVENANT_ASK_LOG"] = tempfile.mktemp(suffix="_pc1_asklog.jsonl")
    os.environ["COVENANT_TEACHER_QUEUE"] = tempfile.mktemp(suffix="_pc1_queue.jsonl")
    os.environ["COVENANT_MODEL_STUB"] = "1"
    m = fresh_master()
    client = m.api.app.test_client()
    LOOP, PHONE, LAN = "127.0.0.1", "100.86.158.1", "192.168.1.50"

    print("PC1a -- the page and its gate")
    r = get(client, "/pc", LOOP)
    body = r.get_data(as_text=True)
    check("PC1a /pc answers loopback 200 with HTML", r.status_code == 200 and "text/html" in r.headers.get("Content-Type", ""), r.status_code)
    check("PC1a every placeholder is filled", not [t for t in ("__NODE__", "__VERSION__", "__SOURCE__") if t in body])
    check("PC1a the page carries the three panels", all(k in body for k in ("Talk", "Council", "Training", "/pc/council", "/pc/training", "/m/agent")))
    check("PC1a /pc answers the tailnet too", get(client, "/pc", PHONE).status_code == 200)
    before = refusals(m, "mobile_page_refused")
    r = get(client, "/pc", LAN)
    check("PC1a a LAN address is refused 403 and recorded", r.status_code == 403 and refusals(m, "mobile_page_refused") == before + 1, r.status_code)
    real = cov.tailnet_ok
    try:
        cov.tailnet_ok = lambda addr: True
        check("PC1a mutation: guard off -> the LAN request succeeds", get(client, "/pc", LAN).status_code == 200)
    finally:
        cov.tailnet_ok = real
    check("PC1a guard restored -> refused again", get(client, "/pc", LAN).status_code == 403)

    print("PC1b -- the council")
    r = post(client, "/pc/council", PHONE, {"text": "should a node admit a transfer whose memo names no value"})
    j = r.get_json() or {}
    steps = j.get("steps", [])
    check("PC1b 200, success, the verdict fields and the model's cost",
          r.status_code == 200 and j.get("status") == "success" and all(k in j for k in ("answer", "withheld", "admitted", "judge", "ms", "steps")), (r.status_code, sorted(j)))
    check("PC1b three roles in order: proposer, critic, reviser", [s["role"] for s in steps] == ["proposer", "critic", "reviser"], [s.get("role") for s in steps])
    # Measured by what each role was HANDED: the reviser's prompt must exceed the
    # proposer's by at least the two answers before it, not merely by a longer
    # brief (mutation 2026-09-21: with nothing carried forward the prompts still
    # grew by the briefs' lengths, and a weaker form of this check stayed green).
    grew = (len(steps) == 3 and steps[2]["in_chars"] - steps[0]["in_chars"]
            >= len(steps[0]["content"]) + len(steps[1]["content"]))
    check("PC1b each role was handed the answers before it (the reviser's prompt grew by at least both)",
          grew, [(s.get("in_chars"), len(s.get("content", ""))) for s in steps])
    check("PC1b the stub answered each role from its own prompt", all(s["content"].startswith("stub answer to:") and s["model"] == "stub" for s in steps), steps[:1])
    check("PC1b the reviser's answer is the council's, unless the gate withheld it",
          (j.get("withheld") and j.get("answer") == "") or (not j.get("withheld") and j.get("answer") == steps[-1]["content"]), (j.get("withheld"), j.get("answer", "")[:60]))
    check("PC1b an empty question is refused 400", post(client, "/pc/council", PHONE, {"text": "   "}).status_code == 400)
    check("PC1b a LAN address is refused 403", post(client, "/pc/council", LAN, {"text": "hello"}).status_code == 403)

    print("PC1c -- memory and the teacher's queue")
    log_rows = [json.loads(l) for l in open(os.environ["COVENANT_ASK_LOG"], encoding="utf-8")]
    council = [x for x in log_rows if x.get("kind") == "council"]
    check("PC1c the council is a row in the chat memory with its steps", len(council) == 1 and len(council[0].get("steps", [])) == 3, len(council))
    q = [json.loads(l) for l in open(os.environ["COVENANT_TEACHER_QUEUE"], encoding="utf-8")]
    check("PC1c both sides went to the teacher's queue: his question, then the council's answer",
          len(q) == 2 and q[0]["source"].startswith("you:") and q[1]["source"].startswith("council:"), [x.get("source") for x in q])
    real_q = os.path.join(HERE, "ops", "teacher_queue.jsonl")
    check("PC1c nothing was written to the real queue by this test",
          not os.path.exists(real_q) or "should a node admit a transfer whose memo names no value" not in open(real_q, encoding="utf-8").read())

    print("PC1d -- training, measured")
    r = get(client, "/pc/training", LOOP)
    t = r.get_json() or {}
    check("PC1d 200 JSON with the queue, the ledger, the exam, the nightly and the graduation",
          r.status_code == 200 and all(k in t for k in ("queue", "ledger", "exam", "nightly", "graduation")), (r.status_code, sorted(t)))
    g = t.get("graduation", {})
    crit = g.get("criteria", [])
    check("PC1d five criteria, the fifth UNDETERMINED, graduated False on one machine",
          len(crit) == 5 and crit[4]["met"] is None and g.get("graduated") is False and g.get("undetermined", 0) >= 1, g)
    check("PC1d every measured section names its source", all(isinstance(t[k], dict) and ("source" in t[k] or "error" in t[k]) for k in ("queue", "ledger", "exam", "nightly")), {k: t[k].get("source") for k in ("queue", "ledger", "exam", "nightly")})
    check("PC1d /pc/training refuses a LAN address 403", get(client, "/pc/training", LAN).status_code == 403)

    print("PC1g -- the handshake")
    r = get(client, "/pc/handshake", LOOP)
    body = r.get_data(as_text=True)
    check("PC1g /pc/handshake answers loopback 200 with HTML, the node named, Copy and Share buttons",
          r.status_code == 200 and "text/html" in r.headers.get("Content-Type", "") and "__NODE__" not in body
          and "__TEXT__" not in body and "Copy" in body and "Share" in body, r.status_code)
    check("PC1g the text names the private door, what to send, what to open first, the run, and the public repository",
          all(s in C.HANDSHAKE_TEXT for s in ("github.com/LAWLESS1987/covenant-satc", "GitHub username", "docs/SATC_RES_MAP.md",
                                                "python covenant_one.py --offline", "github.com/LAWLESS1987/covenant ", "one line back")))
    check("PC1g the text carries the disclosure and no key, code, token or private path",
          "drafted with the help of the system" in C.HANDSHAKE_TEXT
          and not re.search(r"\b(api key|token|password|sudo code|private/|moltbook_)\b", C.HANDSHAKE_TEXT, re.I))
    r = get(client, "/pc/handshake?format=text", PHONE)
    check("PC1g ?format=text returns the bare text for the tailnet, for a share sheet or a curl",
          r.status_code == 200 and "text/plain" in r.headers.get("Content-Type", "") and r.get_data(as_text=True) == C.HANDSHAKE_TEXT)
    before = refusals(m, "mobile_page_refused")
    check("PC1g a LAN address is refused 403 and recorded", get(client, "/pc/handshake", LAN).status_code == 403
          and refusals(m, "mobile_page_refused") == before + 1)

    print("PC1e -- the burst")
    codes = [post(client, "/pc/council", "100.86.158.7", {"text": "council %d" % i}).status_code for i in range(31)]
    first = codes.index(429) if 429 in codes else None
    check("PC1e a burst of 31 councils is bounded: a 429 appears (first at #%s)" % (None if first is None else first + 1),
          first is not None and first <= 30, codes[-3:])

    print("PC1f -- deliberate() with a fake ask")
    seen, budgets = [], []

    def fake_ask(msgs, max_tokens=0):
        seen.append(msgs)
        budgets.append(max_tokens)
        return "answer %d" % len(seen), {"model": "fake"}
    steps, final = C.deliberate("q?", [{"role": "user", "content": "earlier"}, {"role": "assistant", "content": "before"}], fake_ask, "SYS")
    check("PC1f three calls, the roles' briefs in order, the history in every call",
          len(seen) == 3 and all(seen[i][0]["content"].startswith("SYS") and C.ROLES[i][1] in seen[i][0]["content"] for i in range(3))
          and all(seen[i][1]["content"] == "earlier" for i in range(3)), [s[0]["content"][:40] for s in seen])
    check("PC1f the critic sees the proposer, the reviser sees both, the final is the reviser's",
          "proposer: answer 1" in seen[1][-1]["content"] and "critic: answer 2" in seen[2][-1]["content"] and final == "answer 3", final)
    check("PC1f each role is bounded to %d tokens, measured from the call" % C.MAX_TOKENS_PER_ROLE,
          budgets == [C.MAX_TOKENS_PER_ROLE] * 3, budgets)

    print()
    n_ok = sum(1 for _, ok in results if ok)
    print("%d/%d passed" % (n_ok, len(results)))
    bad = [l for l, ok in results if not ok]
    if bad:
        print("PC1 result: FAILED")
        for l in bad:
            print("  - " + l)
        return 1
    print("PC1 result: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
