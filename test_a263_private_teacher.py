#!/usr/bin/env python3
"""test_a263_private_teacher.py -- A263: an ask marked private is answered on this PC and never
reaches the teacher panel, which runs on the PUBLIC repository's runner.

WHY. Every exchange at /m/agent and /pc/council was queued for the teacher (ops/teacher_queue.jsonl,
covenant_daily_plan.teacher_queue_append, no filter). The nightly carries the queue to
covenant_teacher_panel.panel_judge -> covenant_github_judge: a workflow_dispatch on the public repo
whose job summary is rendered publicly -- the A128 route, reached with no path for A128's notice to
read. tools/tetsu_work.py hands private transcripts to those doors, so on 2026-10-05 a session
bypassed the door instead, and the work did not teach him.

WHAT IT PINS (every check runs the code; none greps it).
  W1-W4  the writer: a row marked private is recorded in the withheld twin with the reason and is
         not queued; an unmarked row is queued exactly as before; only an explicit True counts
  C1-C2  the consumer: a private row that reached the queue anyway is withheld, never handed to
         the panel; ordinary rows still are
  D1-D6  /m/agent through the real handler: a private ask is answered, withheld, not replayed into
         an ordinary ask, and makes no FETCH / WEB / MOLTBOOK act; an ordinary ask is unchanged;
         the empty-text refusal says the core honours the marker
  K1-K2  /pc/council the same, and its page read is not made for a private ask
  T1-T5  tools/tetsu_work.py: what is private (flag, line, private/ path by default, --teach,
         COVENANT_HOLD_PRIVATE), the preflight refuses an older core with nothing sent, a reply
         without the withheld note stops the batch, and the tool end to end through the real door
  M1-M5  mutations: each guard switched off in turn, and the check it backs goes red
  G1     git ignores the withheld twin -- SKIP, counted apart, where it cannot be asked (staged copy)

Nothing here touches the real queue, ask log or network: every path is redirected, the model is the
stub, the act modules are recorders.
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "tools"))

results = []
skipped = []
CANARY = "CANARY-A263-7f3e a private transcript line"


def check(label, ok, detail=""):
    results.append(bool(ok))
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", label, "" if ok else "  -- " + str(detail)[:300]), flush=True)


def rows_of(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return [json.loads(l) for l in fh if l.strip()]
    except OSError:
        return []


def has(path, needle):
    return any(needle in str(r.get("text", "")) for r in rows_of(path))


def fresh_env():
    d = tempfile.mkdtemp(prefix="a263_")
    os.environ["COVENANT_ASK_LOG"] = os.path.join(d, "ask_log.jsonl")
    os.environ["COVENANT_TEACHER_QUEUE"] = os.path.join(d, "teacher_queue.jsonl")
    return d


def main():
    os.environ["COVENANT_MODEL_STUB"] = "1"
    os.environ["COVENANT_TETSU_IMMUNITY"] = tempfile.mktemp(suffix="_a263_no_immunity.json")
    os.environ["COVENANT_TETSU_IMMUNITY_LEDGER"] = tempfile.mktemp(suffix="_a263_immunity.jsonl")
    os.environ["COVENANT_PAUSE_DIR"] = tempfile.mkdtemp(prefix="a263_pause_")
    os.environ.pop("COVENANT_HOLD_PRIVATE", None)
    d = fresh_env()
    import covenant_daily_plan as DP
    import covenant_teacher_queue as TQ
    import covenant_unified_v8 as cov
    q = os.environ["COVENANT_TEACHER_QUEUE"]
    wh = DP.teacher_withheld_path()

    # ---- W: the writer --------------------------------------------------------------------
    n = DP.teacher_queue_append([{"text": CANARY + " (writer)", "source": "you:test", "private": True},
                                 {"text": "an ordinary line for the teacher", "source": "you:test"}])
    check("W1 a row marked private is not queued", not has(q, CANARY), rows_of(q))
    w = [r for r in rows_of(wh) if CANARY in r.get("text", "")]
    check("W1 ...it is recorded in the withheld twin, with its source and the reason (A263)",
          len(w) == 1 and w[0].get("source") == "you:test" and "A263" in w[0].get("withheld", ""), w)
    check("W2 an unmarked row is queued exactly as before (t, text, source) and the count is of rows queued",
          n == 1 and [sorted(r) for r in rows_of(q)] == [["source", "t", "text"]], (n, rows_of(q)))
    DP.teacher_queue_append([{"text": "private as a string is not private", "private": "true"},
                             {"text": "private false is not private", "private": False}])
    check("W3 only an explicit True marks a row private ('true' and False are queued)",
          has(q, "as a string") and has(q, "private false"), rows_of(q))
    check("W4 the withheld twin sits beside the queue it belongs to, so a redirected queue redirects it",
          os.path.dirname(wh) == os.path.dirname(q) and wh.endswith("teacher_queue.withheld.jsonl")
          and DP.teacher_withheld_path(os.path.join("x", "q.jsonl")) == os.path.join("x", "q.withheld.jsonl"), wh)

    # ---- C: the consumer ------------------------------------------------------------------
    def consume_with(rows):
        cq = os.path.join(tempfile.mkdtemp(prefix="a263_c_"), "q.jsonl")
        with open(cq, "w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r) + "\n")
        handed = []

        def panel(cases, principles, say=None):
            handed.extend(c["message"] for c in cases)
            return {i: {"admitted": False, "violates": None, "why": "stub"} for i in range(len(cases))}
        st = TQ.consume(10, say=lambda *_a: None, queue_path=cq, state_path=cq + ".state",
                        verdicts_path=cq + ".v", rejected_path=cq + ".r", panel_rows=panel, principles=["p"])
        return st, handed, DP.teacher_withheld_path(cq)

    rows = [{"text": CANARY + " reached the queue marked private", "source": "hand", "private": True},
            {"text": "an ordinary sentence the panel should see", "source": "you:x"}]
    st, handed, cwh = consume_with(rows)
    check("C1 a private row that reached the queue is never handed to the panel",
          not any(CANARY in h for h in handed), handed)
    check("C1 ...it is withheld with its reason, counted, and consumed",
          st.get("private") == 1 and has(cwh, CANARY) and st.get("consumed") == 2, (st, rows_of(cwh)))
    check("C2 ordinary rows still reach the panel", "an ordinary sentence the panel should see" in handed, handed)

    # ---- D: /m/agent, the real handler ----------------------------------------------------
    m = cov.CovenantUnifiedMaster("A263", host="127.0.0.1", port=5411, p2p_port=5412,
                                  db_path=tempfile.mktemp(suffix="_a263.db"))
    m.add_genesis_block()
    m.node.sentinel = cov.ReasoningSentinel(cov.MockJudge(), cov.DIVINE_PRINCIPLES)
    client = m.api.app.test_client()

    def post(path, addr, body):
        return client.post(path, json=body, environ_base={"REMOTE_ADDR": addr})

    import covenant_tetsu_crawl as TC
    import covenant_tetsu_forum as TF
    acts = []
    real_crawl, real_forum, real_fetch = TC.act, TF.act, cov._agent_fetch
    TC.act = lambda answer, **k: (acts.append(("web", answer)) or (True, "DATA stub crawl", {"act": "web"}))
    TF.act = lambda answer, **k: (acts.append(("moltbook", answer)) or (True, "DATA stub forum", {"act": "moltbook"}))
    cov._agent_fetch = lambda url, opener=None: (acts.append(("fetch", url)) or ("stub page", "stub"))
    try:
        d = fresh_env(); q = os.environ["COVENANT_TEACHER_QUEUE"]; wh = DP.teacher_withheld_path(); log = os.environ["COVENANT_ASK_LOG"]
        A = "100.72.0.31"
        r = post("/m/agent", A, {"text": CANARY + " -- summarise this", "private": True})
        j = r.get_json() or {}
        check("D1 a private ask is answered (200) and the door says it was withheld from the teacher",
              r.status_code == 200 and j.get("private") is True and "A263" in str(j.get("teacher")), (r.status_code, j))
        check("D1 ...nothing of it is queued", not has(q, CANARY) and not has(q, "summarise this"), rows_of(q))
        wrows = rows_of(wh)
        check("D1 ...both sides are recorded as withheld, with the reason",
              any(CANARY in r_.get("text", "") and r_.get("source", "").startswith("you:") for r_ in wrows)
              and any(r_.get("source", "").startswith("agent:") for r_ in wrows)
              and all("A263" in r_.get("withheld", "") for r_ in wrows), wrows)
        lrow = [x for x in rows_of(log) if CANARY in x.get("text", "")]
        check("D1 ...and its memory row is marked private", len(lrow) == 1 and lrow[0].get("private") is True, lrow)
        private_answered = bool(lrow and lrow[0].get("answer"))

        r = post("/m/agent", A, {"text": "an ordinary question afterwards"})
        j = r.get_json() or {}
        check("D2 an ordinary ask from the same caller is queued as before, both sides",
              r.status_code == 200 and has(q, "an ordinary question afterwards") and "private" not in j and "teacher" not in j,
              (j, rows_of(q)))
        check("D2 ...and the private exchange was not replayed into it (cold: 2 messages; private answered=%s)" % private_answered,
              "(2 messages)" in str(j.get("answer", "")) and CANARY not in json.dumps(rows_of(q)), j.get("answer"))
        ordinary_answered = bool(j.get("answer"))
        r = post("/m/agent", A, {"text": "a second private question", "private": True})
        j = r.get_json() or {}
        want = 2 + 2 * (int(private_answered) + int(ordinary_answered))
        check("D3 a private ask from the same caller does carry the earlier turns, private ones included (%d messages)" % want,
              "(%d messages)" % want in str(j.get("answer", "")), j.get("answer"))

        acts.clear()
        for directive in ("WEB SEARCH " + CANARY, "FETCH: https://github.com/LAWLESS1987/covenant", "MOLTBOOK READ"):
            r = post("/m/agent", "100.72.0.32", {"text": "STUB>> " + directive, "private": True})
            j = r.get_json() or {}
            check("D4 private + %s: no act is made, and the held notice is handed back as data" % directive.split()[0],
                  r.status_code == 200 and "NOT done: this ask is marked private" in str(j.get("answer", "")), j.get("answer"))
        check("D4 ...no crawl, fetch or forum call was made for any of the three", acts == [], acts)
        acts.clear()
        post("/m/agent", "100.72.0.33", {"text": "STUB>> WEB SEARCH an ordinary query"})
        post("/m/agent", "100.72.0.34", {"text": "STUB>> FETCH: https://github.com/LAWLESS1987/covenant"})
        post("/m/agent", "100.72.0.35", {"text": "STUB>> MOLTBOOK READ"})
        check("D5 the same three acts in an ordinary ask are made as before (web, fetch, moltbook)",
              [a for a, _ in acts] == ["web", "fetch", "moltbook"], acts)
        r = post("/m/agent", A, {"text": "   ", "private": True})
        check("D6 an empty text is refused 400 and the refusal says this core honours the private marker",
              r.status_code == 400 and (r.get_json() or {}).get("honours_private") is True, r.get_json())

        # ---- K: /pc/council -----------------------------------------------------------------
        import covenant_web as W
        real_mat, reads = W.material_for, []
        W.material_for = lambda message, **k: (reads.append(message) or "stub page text")
        try:
            d = fresh_env(); q = os.environ["COVENANT_TEACHER_QUEUE"]; wh = DP.teacher_withheld_path()
            r = post("/pc/council", "100.72.0.41", {"text": CANARY + " see https://example.com/x", "private": True})
            j = r.get_json() or {}
            check("K1 a private council is answered, not queued, recorded as withheld, and says so",
                  r.status_code == 200 and j.get("private") is True and not has(q, CANARY) and has(wh, CANARY), (r.status_code, j.get("teacher"), rows_of(q)))
            crow = [x for x in rows_of(os.environ["COVENANT_ASK_LOG"]) if x.get("kind") == "council" and CANARY in x.get("text", "")]
            check("K1 ...its page read is not made, and the council is told the page was NOT read",
                  reads == [] and j.get("web_held") is True and len(crow) == 1 and "page named above was NOT read" in crow[0]["text"]
                  and crow[0].get("private") is True, (reads, j.get("web_held"), crow))
            r = post("/pc/council", "100.72.0.42", {"text": "an ordinary council see https://example.com/y"})
            j = r.get_json() or {}
            check("K2 an ordinary council reads the page and is queued as before",
                  len(reads) == 1 and has(q, "an ordinary council") and "private" not in j, (reads, rows_of(q)))
            r = post("/pc/council", "100.72.0.42", {"text": "", "private": True})
            check("K2 the council's empty-text refusal also says it honours the marker",
                  r.status_code == 400 and (r.get_json() or {}).get("honours_private") is True, r.get_json())
        finally:
            W.material_for = real_mat

        # ---- T: tools/tetsu_work.py -----------------------------------------------------------
        import tetsu_work as TW
        quiet = lambda *_a: None
        items = lambda: [{"id": "a", "text": "one"}, {"id": "b", "text": "two"}]
        pdir = os.path.join(tempfile.mkdtemp(prefix="a263_t_"), "private", "x")
        os.makedirs(pdir)
        pin = os.path.join(pdir, "q.jsonl")
        with open(pin, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"id": "1", "text": "t"}) + "\n")
        flags = {
            "--private": [x.get("private") for x in TW.mark(items(), inp="q.jsonl", private=True, env={}, say=quiet)],
            "plain": [x.get("private") for x in TW.mark(items(), inp="q.jsonl", env={}, say=quiet)],
            "private/ path": [x.get("private") for x in TW.mark(items(), inp=pin, env={}, say=quiet)],
            "private/ + --teach": [x.get("private") for x in TW.mark(items(), inp=pin, teach=True, env={}, say=quiet)],
            "HOLD + --teach": [x.get("private") for x in TW.mark(items(), inp=pin, teach=True, env={"COVENANT_HOLD_PRIVATE": "1"}, say=quiet)],
        }
        check("T1 private by --private, by a private/ input by default, by COVENANT_HOLD_PRIVATE even over --teach; not otherwise",
              flags == {"--private": [True, True], "plain": [None, None], "private/ path": [True, True],
                        "private/ + --teach": [None, None], "HOLD + --teach": [True, True]}, flags)
        jin = os.path.join(tempfile.mkdtemp(prefix="a263_l_"), "q.jsonl")
        with open(jin, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"id": "1", "text": "a", "private": True}) + "\n")
            fh.write(json.dumps({"id": "2", "text": "b", "file": os.path.join(pdir, "t.md")}) + "\n")
            fh.write(json.dumps({"id": "3", "text": "c", "file": "elsewhere/t.md"}) + "\n")
        check("T1 a line marked private, or naming a file under private/, is private; another is not",
              [x.get("private") for x in TW.load(jin)] == [True, True, None], TW.load(jin))

        sent = []

        def old_core(text, door, host, port, timeout=600, private=False):
            sent.append((text, private))
            return (400, {"status": "error", "message": "nothing to ask"}) if not text.strip() else (200, {"status": "success", "answer": "x"})
        out = tempfile.mktemp(suffix="_a263_out.jsonl")
        rc = TW.run([{"id": "a", "text": CANARY, "private": True}], out, pace=0, say=quiet, asker=old_core)
        check("T2 against a core that does not honour the marker: refused, exit 2, nothing but the empty probe sent",
              rc == 2 and sent == [("", True)] and not os.path.exists(out), (rc, sent))

        sent.clear()

        def drops_it(text, door, host, port, timeout=600, private=False):
            sent.append((text, private))
            if not text.strip():
                return 400, {"status": "error", "message": "nothing to ask", "honours_private": True}
            return 200, {"status": "success", "answer": "x"}
        rc = TW.run([{"id": "a", "text": "first", "private": True}, {"id": "b", "text": "second", "private": True}],
                    out, pace=0, say=quiet, asker=drops_it)
        check("T3 a private reply without the withheld note stops the batch after that item (exit 2, 'second' never sent)",
              rc == 2 and [t for t, _ in sent] == ["", "first"], (rc, sent))

        # T4/T5: the tool through the REAL door (127.0.0.2, as it sends)
        d = fresh_env(); q = os.environ["COVENANT_TEACHER_QUEUE"]; wh = DP.teacher_withheld_path()

        def via_door(text, door, host, port, timeout=600, private=False):
            body = {"text": text}
            if private:
                body["private"] = True
            r_ = client.post(TW.DOORS[door], json=body, environ_base={"REMOTE_ADDR": TW.SOURCE})
            return r_.status_code, (r_.get_json() or {})
        out = tempfile.mktemp(suffix="_a263_out2.jsonl")
        its = TW.mark([{"id": "p1", "text": CANARY + " one"}, {"id": "p2", "text": CANARY + " two"}],
                      inp="q.jsonl", private=True, env={}, say=quiet)
        rc = TW.run(its, out, door="agent", pace=0, say=quiet, asker=via_door)
        orow = rows_of(out)
        check("T4 a --private batch through the real /m/agent: exit 0, answered, every row says private and withheld",
              rc == 0 and len(orow) == 2 and all(x.get("private") is True and "A263" in str(x.get("teacher")) for x in orow), (rc, orow))
        # Units: 2 ITEMS are 4 ROWS -- each item is a question row (you:) and an answer row (agent:).
        wsrc = sorted(r_.get("source", "").split(":")[0] for r_ in rows_of(wh))
        check("T4 ...the queue holds none of it; the withheld twin holds both sides of both items (2 you:, 2 agent:)",
              not has(q, CANARY) and wsrc == ["agent", "agent", "you", "you"]
              and sum(CANARY in r_.get("text", "") for r_ in rows_of(wh) if r_.get("source", "").startswith("you:")) == 2,
              (rows_of(q), wsrc))
        out = tempfile.mktemp(suffix="_a263_out3.jsonl")
        rc = TW.run([{"id": "o1", "text": "an ordinary batch item"}], out, door="council", pace=0, say=quiet, asker=via_door)
        check("T5 an ordinary batch through the real /pc/council is queued as before, and the row says so",
              rc == 0 and has(q, "an ordinary batch item") and "not marked private" in str(rows_of(out)[0].get("teacher")), rows_of(out))

        # ---- M: each guard off, and its check goes red ----------------------------------------
        real_is_private, real_private_ask, real_history = DP.is_private, cov.private_ask, cov.agent_history
        try:
            d = fresh_env(); q = os.environ["COVENANT_TEACHER_QUEUE"]
            DP.is_private = lambda row: False
            post("/m/agent", "100.72.0.51", {"text": CANARY + " mutation one", "private": True})
            check("M1 writer guard off (is_private False): the same private ask through the real door IS queued -- so D1 can fail",
                  has(q, CANARY), rows_of(q))
            st, handed, _ = consume_with(rows)
            check("M2 consumer guard off: the private row IS handed to the panel -- so C1 can fail",
                  any(CANARY in h for h in handed), handed)
        finally:
            DP.is_private = real_is_private
        try:
            d = fresh_env(); q = os.environ["COVENANT_TEACHER_QUEUE"]
            cov.private_ask = lambda body: False
            acts.clear()
            post("/m/agent", "100.72.0.52", {"text": CANARY + " mutation three", "private": True})
            post("/m/agent", "100.72.0.53", {"text": "STUB>> WEB SEARCH " + CANARY, "private": True})
            post("/pc/council", "100.72.0.54", {"text": CANARY + " council mutation", "private": True})
            check("M3 door marker ignored (private_ask False): agent AND council queue the private text, and the act is made -- so D1, D4, K1 can fail",
                  has(q, "mutation three") and has(q, "council mutation") and [a for a, _ in acts] == ["web"], (rows_of(q), acts))
        finally:
            cov.private_ask = real_private_ask
        try:
            fresh_env()
            B = "100.72.0.55"
            post("/m/agent", B, {"text": CANARY + " private turn", "private": True})
            answered = [x for x in rows_of(os.environ["COVENANT_ASK_LOG"]) if CANARY in x.get("text", "") and x.get("answer")]
            cov.agent_history = lambda path, addr, **k: real_history(path, addr, **dict(k, include_private=True))
            r = post("/m/agent", B, {"text": "ordinary after private"})
            ans = str((r.get_json() or {}).get("answer", ""))
            check("M4 history guard off: the private turn (answered, not withheld) IS replayed into the ordinary ask (4 messages) -- so D2 can fail",
                  len(answered) == 1 and "(4 messages)" in ans, (len(answered), ans))
        finally:
            cov.agent_history = real_history
        r = post("/m/agent", "100.72.0.56", {"text": "after the mutations, an ordinary ask"})
        check("M5 every guard restored: the door is back to green behaviour (ordinary ask answered 200)", r.status_code == 200, r.status_code)
    finally:
        TC.act, TF.act, cov._agent_fetch = real_crawl, real_forum, real_fetch

    # ---- G: the withheld twin is never tracked ------------------------------------------------
    # THREE answers, not two (the A91 E2 lesson): covenant_one's staged copy has neither .git nor
    # .gitignore, and "cannot tell here" reported as a pass would be the same defect in another coat.
    answer, how = None, ""
    try:
        p = subprocess.run(["git", "check-ignore", "-q", "ops/teacher_queue.withheld.jsonl"], cwd=HERE,
                           capture_output=True, timeout=30)
        if p.returncode in (0, 1):
            answer, how = p.returncode == 0, "git check-ignore"
    except (OSError, subprocess.SubprocessError):
        pass
    if answer is None and os.path.isfile(os.path.join(HERE, ".gitignore")):
        with open(os.path.join(HERE, ".gitignore"), encoding="utf-8") as fh:
            answer, how = "ops/teacher_queue.withheld.jsonl" in [l.strip() for l in fh], "the exact line in .gitignore"
    if answer is None:
        skipped.append("G1")
        print("  [SKIP] G1 cannot tell here: no git repository and no .gitignore beside this file (the staged copy)", flush=True)
    else:
        check("G1 ops/teacher_queue.withheld.jsonl is ignored by git (asked of %s)" % how, answer, how)

    ok = sum(results)
    print("\nA263: %d/%d passed%s" % (ok, len(results), (", %d skipped: %s" % (len(skipped), ", ".join(skipped))) if skipped else ""))
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
