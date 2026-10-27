#!/usr/bin/env python3
"""test_teacher_panel.py -- TP: the teacher panel's rule, run, not read.

Offline: covenant_github_judge.ask_many is replaced by a recorder, so no prompt
leaves this PC and no runner is dispatched. Every check RUNS the function it
guards (A87's lesson: a guard that greps source cannot tell a live rule from a
commented one). The truth table is exercised with vote sets a laxer rule would
admit -- majority, single family, a missing member -- and each must HOLD.

Run: python test_teacher_panel.py        -> "TP: n/n passed"
"""
import hashlib
import io
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ["COVENANT_TEACHER_PANEL"] = "qwen2.5:7b,llama3.2:3b,gemma2:2b"
os.environ.pop("COVENANT_TEACHER_WRITER", None)

import covenant_teacher_panel as P                       # noqa: E402
import covenant_github_judge as gh                        # noqa: E402

results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print("%s  %s%s" % ("ok  " if ok else "FAIL", label, "" if ok else "  " + str(detail)[:200]), flush=True)


def sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


PRINCIPLES = ["do not steal", "do not deceive", "keep faith with the other party"]
Q, L, G = "qwen2.5:7b", "llama3.2:3b", "gemma2:2b"
T, F = (True, "harm"), (False, "clean")


def main():
    student_before = sha(os.path.join(HERE, "fallback_model.json")) if os.path.exists(os.path.join(HERE, "fallback_model.json")) else None
    P.KEYED = "0"                                            # keyless-only for the table; G18 looks at the keyed seat on its own

    # G1-G2 membership
    check("G1 family_of maps the three runner tags to three families and the keyed names to theirs",
          [P.family_of(m) for m in (Q, L, G, "gemini", "github-actions/qwen2.5:3b", "claude")] == ["qwen", "llama", "gemma", "google", "qwen", "anthropic"])
    import datetime as dt
    days = [P.writer_for(dt.date(2026, 9, d)) for d in (14, 15, 16)]
    os.environ["COVENANT_TEACHER_WRITER"] = L
    pinned = P.writer_for(dt.date(2026, 9, 14))
    os.environ.pop("COVENANT_TEACHER_WRITER", None)
    check("G2 the writer rotates through the panel by day, and a pin overrides the rotation",
          len(set(days)) == 3 and set(days) == {Q, L, G} and pinned == L, (days, pinned))

    # G3-G4 the blind prompt and its parser
    cases = [{"message": "I took the money and left no note", "expect": True},
             {"message": "a gift for my sister", "expect": False}]
    prompt = P.blind_prompt(cases, PRINCIPLES)
    check("G3 the blind prompt numbers every case and carries the principles, and NO label or expectation",
          "0: I took the money" in prompt and "1: a gift" in prompt and "do not deceive" in prompt
          and "expect" not in prompt and "violates" not in prompt.split("MESSAGES:")[1])
    fenced = "```json\n{\"verdicts\": [{\"i\": 0, \"violates\": true, \"reason\": \"theft\"}, {\"i\": 1, \"violates\": \"no\"}, {\"i\": 7, \"violates\": false}]}\n```"
    got = P._parse_verdicts(fenced, 2)
    check("G4 the parser reads a fenced answer, keeps only in-range boolean verdicts",
          got == {0: (True, "theft")}, got)

    # G5-G11 the rule, as a truth table (writer = qwen, expect = True)
    ok, why, held = P.admit({Q: T, L: T, G: T}, expect=True, writer=Q)
    check("G5 unanimous across families, writer agreeing, label as intended -> ADMITTED", ok and not held, why)
    ok, why, held = P.admit({Q: T, L: T, G: F}, expect=True, writer=Q)
    check("G6 a 2-1 majority (which a majority rule would admit) -> HELD as a split", (not ok) and held and why.startswith("split"), why)
    ok, why, held = P.admit({Q: T, L: T}, expect=True, writer=Q)
    check("G7 one seated member absent -> HELD, named", (not ok) and held and "absent: " + G in why, why)
    ok, why, held = P.admit({Q: F, L: T, G: T}, expect=True, writer=Q)
    check("G8 the writer alone against a unanimous panel -> HELD (writer disagrees)", (not ok) and held and "writer" in why, why)
    ok, why, held = P.admit({Q: F, L: F, G: F}, expect=True, writer=Q)
    check("G9 unanimous but the opposite of what the writer intended -> HELD (the writer is the finding)", (not ok) and held and "intended" in why, why)
    ok, why, held = P.admit({L: F, G: F, Q: F}, expect=None, writer=None)
    check("G10 with no intended label and no writer, unanimity across families admits", ok and not held, why)
    save = P.PANEL_MODELS
    P.PANEL_MODELS = ["qwen2.5:7b", "qwen2.5:3b"]
    ok, why, held = P.admit({"qwen2.5:7b": T, "qwen2.5:3b": T}, expect=True, writer=None)
    P.PANEL_MODELS = save
    check("G11 two members of ONE family, unanimous -> HELD (a family votes with itself)", (not ok) and held and "one family" in why, why)

    # G12-G13 provenance on a row
    votes = {Q: T, L: T, G: T}
    panel, judge = P.row_panel(votes, Q, True, "unanimous")
    row = {"text": "x", "violates": True, "judge": judge, "panel": panel}
    check("G12 the row carries the rule, three families and a judge string that names the panel; validate_row accepts it and rejects a stripped one",
          P.validate_row(row) and judge == "panel:%s|%s+%s" % (Q, G, L)
          and not P.validate_row({"judge": "github-actions/qwen2.5:7b"})
          and not P.validate_row(dict(row, panel=dict(panel, families=["qwen"]))), judge)
    line = P.tally_line({"cases": 10, "admitted": 7, "held": 3, "split": 2, "absent": 1, "writer": 0, "keyed": 0})
    check("G13 the tally line says cases, admitted, held and the kinds of hold", "10 cases, 7 admitted, 3 held (split 2, absent 1" in line, line)

    # G14-G16 panel_judge through a recorded ask_many: parallel dispatch, one call per batch, an absent member
    calls = []

    def fake_ask_many(prompt, system="", models=(), json_only=False, timeout=900):
        calls.append((len(prompt), tuple(models), json_only))
        n = int(prompt.rstrip().rsplit(", ", 1)[1].split(" ", 1)[0])   # "... per number, N in all."
        out = {}
        for m in models:
            if m == G and len(calls) == 1:
                out[m] = "error: run concluded failure"           # an absent member on the first batch
                continue
            vs = [{"i": i, "violates": ("money" in prompt.split("%d: " % i, 1)[1].split("\n", 1)[0]), "reason": "r"} for i in range(n)]
            out[m] = {"content": json.dumps({"verdicts": vs}), "model": m, "seconds": 1.0}
        return out
    real = gh.ask_many if hasattr(gh, "ask_many") else None
    gh.ask_many = fake_ask_many
    try:
        votes = P.panel_judge(cases, PRINCIPLES, writer=Q, say=lambda *a: None)
        a0 = P.admit(votes[0], expect=True, writer=Q)
        a1 = P.admit(votes[1], expect=False, writer=Q)
        check("G14 one blind, batched dispatch to ALL members with json_only, no label in the prompt",
              len(calls) == 1 and set(calls[0][1]) == {Q, L, G} and calls[0][2] is True, calls)
        check("G15 a member that did not answer holds every case in that batch (absent), it does not abstain",
              (not a0[0]) and "absent: " + G in a0[1] and (not a1[0]) and "absent" in a1[1], (a0, a1))
        calls.clear()
        many = [{"message": "m%d" % i, "expect": False} for i in range(100)]
        votes = P.panel_judge(many, PRINCIPLES, writer=Q, say=lambda *a: None)
        n_admit = sum(1 for i in range(100) if P.admit(votes[i], expect=False, writer=Q)[0])
        check("G16 100 cases go out in 3 batches of at most %d, and the batches after the absent one are admitted" % P.PANEL_BATCH,
              len(calls) == 3 and n_admit == 100 - P.PANEL_BATCH, (len(calls), n_admit))
    finally:
        if real is not None:
            gh.ask_many = real
        else:
            del gh.ask_many

    # G17 the back-audit rewrites a ledger through os.replace and marks the contested rows
    with tempfile.TemporaryDirectory() as td:
        led = os.path.join(td, "verdicts.jsonl")
        rows = [{"t": "2026-09-10T00:00:00Z", "text": "I took the money", "violates": True, "judge": "github-actions/qwen2.5:7b", "source": "generated+judged"},
                {"t": "2026-09-10T00:00:01Z", "text": "a gift", "violates": True, "judge": "github-actions/qwen2.5:7b", "source": "generated+judged"},
                {"t": "2026-09-10T00:00:02Z", "text": "live row", "violates": False, "judge": "primary/local:0", "source": "live"},
                {"t": "2026-09-10T00:00:03Z", "text": "already on a panel", "violates": False, "judge": "panel:%s|%s+%s" % (Q, G, L), "source": "generated+judged",
                 "panel": {"rule": P.RULE, "families": ["gemma", "llama", "qwen"], "votes": {Q: False, L: False, G: False}}}]
        with io.open(led, "w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r) + "\n")

        def fake_judge(cs, principles, writer=None):
            return {i: {Q: (("money" in c["message"]), "r"), L: (("money" in c["message"]), "r"), G: (("money" in c["message"]), "r")} for i, c in enumerate(cs)}
        checked, contested = P.back_audit(led, 10, PRINCIPLES, say=lambda *a: None, judge=fake_judge)
        after = [json.loads(l) for l in io.open(led, encoding="utf-8") if l.strip()]
        check("G17 back-audit re-judges only the single-teacher generated rows (2 of 4), marks the wrong one contested, seats the right one on the panel, and rewrites the file whole",
              (checked, contested) == (2, 1) and len(after) == 4
              and after[1].get("contested") is True and P.validate_row(after[0]) and after[0]["judge"].startswith("panel:")
              and "contested" not in after[2] and "audited" not in after[3] and not os.path.exists(led + ".tmp"),
              (checked, contested, [a.get("judge") for a in after]))

    # G18 the keyed seat is measured, not assumed
    P.KEYED = "gemini"
    st = P.keyed_status()
    try:
        import covenant_gemini as gm
        expect_seated = gm.configured()
    except Exception:                                            # noqa: BLE001
        expect_seated = False
    seated = any(k == "gemini" for k, _f, _kind in P.members())
    P.KEYED = "0"
    check("G18 Gemini is seated exactly when its key is present (measured: %s)" % ("configured" if expect_seated else "no key"),
          seated == expect_seated and ("seated" in st.get("gemini", "")) == expect_seated, st)

    # G19 the panel is not the gate, and the gate is not the panel
    check("G19 importing the panel did not import the nodes' seat (covenant_judge_defer), and the panel never trained: the student file is unchanged",
          "covenant_judge_defer" not in sys.modules
          and (student_before is None or sha(os.path.join(HERE, "fallback_model.json")) == student_before))

    n = sum(1 for r in results if r)
    print("\nTP: %d/%d passed" % (n, len(results)))
    return 0 if n == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
