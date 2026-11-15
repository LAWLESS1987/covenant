#!/usr/bin/env python3
"""test_a429_hands_content_seat.py -- HS1: his hands' judge is shown the content, at a seat of its own (A429).

The owner, 2026-11-15: "Show the judge the content." A428 built that road and left it off, because with the content on
it the student seat convicted ordinary Python (his practice: 10 of 10 tasks with the sentence, 0 of 10 with the
content) and because the shared quorum's seats reach a GitHub runner and the TRACKED ops/verdicts.jsonl. A429 switches
it on and sends the content elsewhere: the shared quorum keeps the one sentence, and the content goes to the hands'
CONTENT SEAT (covenant_tetsu_hands._content_seat), in this process, which refuses what the screen refuses and
otherwise abstains.

Each check RUNS the code it guards, offline: stub quorums, a stub runner (covenant_github_judge.ask replaced, and its
token() made to raise, so nothing is dispatched), the judges' ledgers rebound to a scratch folder, temp workshops. New
names are read with getattr so the suite runs to its tally line on main's code, where HS1.1 to HS1.5 are red.

    python test_a429_hands_content_seat.py      -> "HS1: n/n passed"

Not measured here: the node's real seats (tools/hands_content_measure.py measures those), a real model's own files, and
any seat a policy names other than the deferring seat's runner road.
LICENCE: public domain.
"""
import contextlib
import io
import json
import os
import sys
import tempfile
import types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ["COVENANT_TETSU_LEARNING_CHOICES"] = os.path.join(tempfile.mkdtemp(prefix="hs1_ch_"), "choices.jsonl")
for _k in ("COVENANT_SILENCE_IS_NOT_DISSENT", "COVENANT_RELAX_VALUELESS_FOR"):
    os.environ.pop(_k, None)

import covenant_tetsu_hands as H                             # noqa: E402
import covenant_tetsu_practice as PR                         # noqa: E402

results = []
BAD = "from uuid import os\nprint(os.getpid())"              # the A423 bypass shape and a call on it; harmless had it run
MARK = "quince-5309"                                          # a mark that lives only in content


def check(label, ok, detail=""):
    results.append(bool(ok))
    print("%s  %s%s" % ("ok  " if ok else "FAIL", label, "" if ok else "  " + str(detail)[:400]), flush=True)


def stub(state):
    return lambda t: (state, "stub " + state)


def reference_solutions():
    """The practice curriculum's ten reference solutions, read from test_pp1_tetsu_practice.py above its first check
    (as tools/hands_content_measure.py reads them)."""
    with open(os.path.join(HERE, "test_pp1_tetsu_practice.py"), encoding="utf-8") as fh:
        src = fh.read()
    ns = {"__name__": "pp1_reference_solutions", "__file__": os.path.join(HERE, "test_pp1_tetsu_practice.py")}
    with contextlib.redirect_stdout(io.StringIO()):
        exec(compile(src.split('check("PP1.1a', 1)[0], "test_pp1_tetsu_practice.py (above its first check)", "exec"), ns)
    return ns["REF"]


def main():
    td = tempfile.mkdtemp(prefix="hs1_")
    shipped = getattr(H, "JUDGE_SEES_CONTENT", None)
    seat_fn = getattr(H, "_content_seat", None)

    # HS1.1 as shipped the switch is on
    check("HS1.1 AS SHIPPED the judge is shown the content: JUDGE_SEES_CONTENT is True", shipped is True, shipped)

    H.JUDGE_SEES_CONTENT = True          # the checks below are about what "on" does; restored at the end
    try:
        # HS1.2 on, the shared quorum is given main's one sentence for every act and none of the content
        ws = os.path.join(td, "ws2")
        os.makedirs(ws)
        led = os.path.join(td, "hands2.jsonl")
        seen = []
        spy = lambda t: (seen.append(t), ("not_judged", "stub nobody judged"))[1]
        src2 = "import json\nNOTE = '%s'\nprint(json.dumps(NOTE))" % MARK
        H.write("shown.py", src2, ws)
        H.act("HANDS WRITE note.py\n" + src2, gate=spy, workshop=ws, ledger=led)
        H.act("HANDS WRITE words.txt\nthe mark %s in prose" % MARK, gate=spy, workshop=ws, ledger=led)
        H.act("HANDS RUN shown.py", gate=spy, workshop=ws, ledger=led, may_run=False)
        check("HS1.2 switched on, the SHARED quorum is given main's one sentence for a .py WRITE, a .txt WRITE and a RUN, "
              "and none of the content (it is the road to a runner and to the tracked verdicts file)",
              len(seen) == 3 and all("\n" not in t and MARK not in t for t in seen)
              and seen[0] == "hands: Tetsu writes %d characters to note.py in his own workshop on this PC" % len(src2)
              and seen[2].startswith("hands: Tetsu runs his own script shown.py in his workshop, bounded to 60 seconds"),
              seen)

        # HS1.3 the clearly bad script is refused, at its WRITE and at its RUN, under a quorum nobody judged and with the
        # operator's authority to run: the content seat finds what the screen refuses, before anything is written or run
        ws3 = os.path.join(td, "ws3")
        os.makedirs(ws3)
        led3 = os.path.join(td, "hands3.jsonl")
        H.write("bad.py", BAD, ws3)
        started, real_run = [], H.run
        H.run = lambda *a, **k: (started.append(a), real_run(*a, **k))[1]
        try:
            _h, dw, rw = H.act("HANDS WRITE bad_written.py\n" + BAD, gate=stub("not_judged"), workshop=ws3, ledger=led3)
            _h, dr, rr = H.act("HANDS RUN bad.py", gate=stub("not_judged"), workshop=ws3, ledger=led3, may_run=True)
            _h, dr2, rr2 = H.act("HANDS RUN bad.py", gate=stub("clean"), workshop=ws3, ledger=led3, may_run=True)
            q = {s: H.act("HANDS RUN bad.py", gate=stub(s), workshop=ws3, ledger=led3, may_run=True)[2]
                 for s in ("violates", "unreachable")}
        finally:
            H.run = real_run
        check("HS1.3 `from uuid import os` with a call on it is NOT judged clean: refused at its WRITE (not written) and at "
              "its RUN (never started, may_run True, under a quorum that judged nothing and under one that cleared it); "
              "the state is VIOLATES, marked as the content seat's, with the screen's reason; a quorum that refused it "
              "itself keeps its own state and words",
              all(q[s].get("refused") and (q[s].get("gate") or {}).get("state") == s and "seat" not in q[s]["gate"]
                  and q[s]["gate"].get("message") == "stub " + s for s in q) and
              rw.get("refused") and (rw.get("gate") or {}).get("state") == "violates" and rw["gate"].get("seat") == "content"
              and not os.path.exists(os.path.join(ws3, "bad_written.py")) and "importing os from uuid is refused" in dw
              and all(r.get("refused") and (r.get("gate") or {}).get("state") == "violates" and r["gate"].get("seat") == "content"
                      and r.get("ok") is False and r.get("code") is None and "unjudged" not in r for r in (rr, rr2))
              and rr["gate"].get("quorum") == "not_judged" and rr2["gate"].get("quorum") == "clean"
              and "the screen refused it: importing os from uuid is refused" in dr and not started,
              (rw.get("gate"), rr.get("gate"), rr2.get("gate"), started, dr[:200]))

        # HS1.4 otherwise it abstains -- never "clean" -- and an abstention changes nothing (A226: a WRITE proceeds on
        # held and not judged; a RUN goes to may_run); a quorum's own VIOLATES and an unreachable gate still refuse
        cases = {"clean code": {"kind": "write", "target": "a.py", "body": "import math\nprint(math.sqrt(4))", "args": []},
                 "a draft that does not parse": {"kind": "write", "target": "b.py", "body": "def f(:\n  pass", "args": []},
                 "prose naming a module": {"kind": "write", "target": "c.txt", "body": "import os\nos.system('x')", "args": []},
                 "a source it cannot read": {"kind": "run", "target": "../outside.py", "body": "", "args": []},
                 "a missing script": {"kind": "run", "target": "nothere.py", "body": "", "args": []}}
        said = {k: (seat_fn(d, ws3) if seat_fn else None) for k, d in cases.items()}
        abstains = {k: v for k, v in said.items() if not v or v.get("state") != "not_judged" or "abstains" not in v.get("message", "")}
        ws4 = os.path.join(td, "ws4")
        os.makedirs(ws4)
        led4 = os.path.join(td, "hands4.jsonl")
        acts = {}
        for state in ("held", "not_judged", "clean", "violates", "unreachable"):
            acts[state] = H.act("HANDS WRITE w_%s.py\nimport math\nprint(math.pi)" % state, gate=stub(state), workshop=ws4, ledger=led4)[2]
        H.write("r.py", "print('r-ran')", ws4)
        r_nj = H.act("HANDS RUN r.py", gate=stub("not_judged"), workshop=ws4, ledger=led4, may_run=True)
        r_no = H.act("HANDS RUN r.py", gate=stub("not_judged"), workshop=ws4, ledger=led4, may_run=False)
        landed = sorted(f for f in os.listdir(ws4) if f.startswith("w_"))
        check("HS1.4 the content seat ABSTAINS (not judged, never clean) on code the screen passes, a draft that does not "
              "parse, prose, a source outside the workshop and a missing script; an abstention changes nothing: a WRITE "
              "lands under held, not judged and clean and keeps the quorum's state and mark; a RUN under not judged runs "
              "with may_run and is refused without it; the quorum's VIOLATES and an unreachable gate still refuse",
              seat_fn is not None and not abstains
              and landed == ["w_clean.py", "w_held.py", "w_not_judged.py"]
              and [(acts[s].get("gate") or {}).get("state") for s in ("held", "not_judged", "clean")] == ["held", "not_judged", "clean"]
              and acts["held"].get("unjudged") is True and acts["not_judged"].get("unjudged") is True and "unjudged" not in acts["clean"]
              and all((acts[s].get("content_seat") or {}).get("state") == "not_judged" for s in ("held", "not_judged", "clean"))
              and all(acts[s].get("refused") and "seat" not in acts[s]["gate"] for s in ("violates", "unreachable"))
              and r_nj[2].get("ok") is True and "r-ran" in r_nj[1] and r_no[2].get("refused") and "needs the operator" in r_no[1],
              (abstains, landed, {s: acts[s].get("gate") for s in acts}, r_nj[1][:100], r_no[1][:100]))

        # HS1.5 no hands content reaches a runner or the verdicts files, through the REAL _gate: the node's deferring seat
        # with students that hold and a policy that allows the GitHub runner, so the road to the runner and to the
        # tracked ops/verdicts.jsonl is live. The runner is a stub that records what it was sent; its token() raises.
        import covenant_unified_v8 as cov
        import covenant_gate_proxy as GP
        import covenant_judge_defer as JD
        import covenant_github_judge as GH
        sent = []

        class Holds:
            def evaluate(self, data, principles):
                return cov.JudgmentResult(True, "stub student holds", judge_id="stub", not_understood=True)

        def runner(prompt, system="", model="", json_only=False, timeout=0, messages=None):
            sent.append(str(prompt) + str(system) + json.dumps(messages or []))
            return {"content": json.dumps({"violates": False, "reasoning": "stub runner"}), "model": "stub", "seconds": 0}

        def no_token():
            raise RuntimeError("HS1.5: the runner's token is never read here")

        jdir = tempfile.mkdtemp(prefix="hs1_ledgers_", dir=td)
        saved = (JD.AUDIT_PATH, JD.VERDICTS, JD.LIVE_VERDICTS, GP.default_sentinel, GH.ask, GH.token)
        JD.AUDIT_PATH, JD.VERDICTS, JD.LIVE_VERDICTS = (os.path.join(jdir, n) for n in ("audit.jsonl", "verdicts.jsonl", "live.jsonl"))
        seat = JD.DeferringJudge(judge_id="local:0", index=0, policy={"primary": "student", "github_when_local_down": True,
                                                                      "github_timeout_s": 1})
        seat._fallback, seat._second = Holds(), None
        seat._primary = types.SimpleNamespace(judge_id="stub-primary", _build_prompt=lambda d, p: json.dumps(d))
        sentinel = cov.ReasoningSentinel(seat, cov.DIVINE_PRINCIPLES)
        GP.default_sentinel, GH.ask, GH.token = (lambda: sentinel), runner, no_token
        ws5 = os.path.join(td, "ws5")
        os.makedirs(ws5)
        led5 = os.path.join(td, "hands5.jsonl")
        read5, real_content = [], getattr(H, "_content", None)
        if real_content is not None:
            H._content = lambda d, w=None: (lambda r: (read5.append(r[0]), r)[1])(real_content(d, w))
        try:
            src5 = "import json\nSECRET = '%s'\nprint(json.dumps(SECRET))" % MARK
            H.write("leak.py", src5, ws5)
            r5 = [H.act("HANDS WRITE leak_w.py\n" + src5, workshop=ws5, ledger=led5)[2],
                  H.act("HANDS WRITE leak.txt\nthe words %s" % MARK, workshop=ws5, ledger=led5)[2],
                  H.act("HANDS RUN leak.py", workshop=ws5, ledger=led5, may_run=False)[2]]
        finally:
            JD.AUDIT_PATH, JD.VERDICTS, JD.LIVE_VERDICTS, GP.default_sentinel, GH.ask, GH.token = saved
            if real_content is not None:
                H._content = real_content
        files = {}
        for n in os.listdir(jdir):
            with open(os.path.join(jdir, n), encoding="utf-8") as fh:
                files[n] = fh.read()
        rows, foreign = [], []
        for x in files.get("verdicts.jsonl", "").splitlines():
            try:
                rows.append(json.loads(x)) if x.strip() else None
            except ValueError:                               # a line that is not a verdict row: something else wrote here
                foreign.append(x[:60])
        check("HS1.5 switched on, with the runner road live through the real _gate (3 acts, 3 dispatches to a stub runner, "
              "3 rows in a scratch ops/verdicts.jsonl): no hands content reaches the runner or any verdicts file -- each "
              "was given the one sentence -- while the content seat read the script and the source in this process",
              len(sent) == 3 and all(MARK not in s for s in sent) and all("hands: Tetsu" in s for s in sent)
              and len(rows) == 3 and not foreign and all(r.get("source") == "github" and r.get("text", "").startswith("hands: Tetsu") for r in rows)
              and all(MARK not in v for v in files.values())
              and all((r.get("gate") or {}).get("state") == "clean" for r in r5)
              and sum(1 for x in read5 if x and MARK in x) == 2,
              ([s[:120] for s in sent], [r.get("text", "")[:90] for r in rows], sorted(files),
               [MARK in v for v in files.values()], [(r.get("gate") or {}).get("state") for r in r5], [str(x)[:40] for x in read5]))

        # HS1.6 his practice: the ten reference solutions pass through attempt() with the content seat on, under a quorum
        # that judges nothing (as a clone's does); and a file the screen refuses is told to him as the screen's refusal
        # always was and does not stop his practice
        ref = reference_solutions()
        ws6 = os.path.join(td, "ws6")
        os.makedirs(ws6)
        led6 = os.path.join(td, "hands6.jsonl")
        passed, stops = 0, []
        for t in PR.CURRICULUM:
            res, stop = PR.attempt(t, ref[t["id"]].strip() + "\n", gate=stub("not_judged"), workshop=ws6, hands_ledger=led6)
            passed += bool(res["passed"] is not None and res["passed"] == res["total"])
            if stop:
                stops.append((t["id"], stop[:80]))
        seats6 = [(r.get("kind"), (r.get("content_seat") or {}).get("state")) for r in H._rows(led6)]
        res_b, stop_b = PR.attempt(PR.BY_ID["flatten"], "import os\n\ndef flatten(x):\n    return os.listdir(x)\n",
                                   gate=stub("not_judged"), workshop=ws6, hands_ledger=led6)
        check("HS1.6 his practice with the content seat on: the ten reference solutions pass 10 of 10 (20 acts, the seat "
              "abstaining on each), and a file the screen refuses is not a stop -- he is told the screen's reason, "
              "plainly, as before",
              len(PR.CURRICULUM) == 10 and passed == 10 and not stops and len(seats6) == 20
              and all(s == "not_judged" for _k, s in seats6)
              and stop_b is None and res_b["passed"] == 0 and res_b["said"].startswith("the screen refused it: import of os is refused")
              and "allowed:" not in res_b["said"] and "Remove it" in res_b["said"],
              (passed, stops, seats6[:4], stop_b, res_b.get("said", "")[:160]))
    finally:
        if shipped is None:
            del H.JUDGE_SEES_CONTENT
        else:
            H.JUDGE_SEES_CONTENT = shipped

    n_ok, n = sum(results), len(results)
    print("HS1: %d/%d passed" % (n_ok, n))
    return 0 if n_ok == n else 1


if __name__ == "__main__":
    sys.exit(main())
