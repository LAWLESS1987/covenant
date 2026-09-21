#!/usr/bin/env python3
"""TP1 -- Tetsu refines himself, inside bounds, judged, recorded; reversed only
by an objection the gate upholds; his records closable by him alone.

Pins covenant_persona (2026-09-21, his words: "Allow [Tetsu] to refine himself
including his voice") by RUNNING it in a temp persona file with a stub model
and a stub judge:

  TP1a  a fresh persona is the default register and voice; the composed
        system message is the fixed rules, then the register, then the brief.
  TP1b  a clean proposal within bounds is applied and recorded with its reason
        and verdict; the voice is clamped to its bounds; the operator is told
        on the (redirected) direct line.
  TP1c  a proposal the gate holds changes nothing and is recorded as held; a
        register that touches the fixed rules is refused; an over-long one is
        refused; a model that answers no JSON changes nothing.
  TP1d  contest: an objection the gate does not uphold changes nothing; one it
        upholds reverses to the state before; no reset exists. Blocks: his
        records close to Tetsu at his choice alone, and Tetsu is told so.
  TP1e  the brief is built from real records and says the node, the last
        sweep's tally and the newest ledger entries; checkin_fields carries
        the clamped voice.
"""
import json
import os
import sys
import tempfile

os.environ.setdefault("COVENANT_QUIET", "1")
os.environ["COVENANT_PERSONA"] = tempfile.mktemp(suffix="_tp1_persona.json")
os.environ["COVENANT_CONTACT_OUTBOX"] = tempfile.mktemp(suffix="_tp1_contact.jsonl")
os.environ["COVENANT_CONTACT_STATE"] = tempfile.mktemp(suffix="_tp1_contact_state.json")
os.environ["COVENANT_CHATS_DIR"] = tempfile.mkdtemp(prefix="tp1_chats_")   # A188: his AI apps' chat lines, redirected
HERE = os.path.dirname(os.path.abspath(__file__)) or "."
sys.path.insert(0, HERE)

import covenant_persona as P     # noqa: E402

FAILURES = []
PASSED = [0]


def check(label, ok, detail=""):
    print("  %-76s %s%s" % (label, "OK" if ok else "*** FAIL ***", ("  " + str(detail)[:300]) if detail and not ok else ""))
    if ok:
        PASSED[0] += 1
    else:
        FAILURES.append(label)


def ask_with(proposal):
    def ask(msgs, max_tokens=0):
        return ("Here is my revision:\n" + json.dumps(proposal)) if isinstance(proposal, dict) else str(proposal), {"model": "stub"}
    return ask


def main():
    pp = os.environ["COVENANT_PERSONA"]
    log = os.path.join(tempfile.mkdtemp(prefix="tp1_"), "asklog.jsonl")
    with open(log, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"t": "2099-01-01T00:00:00+0000", "kind": "agent", "from": "100.1.1.1", "text": "recap updates"}) + "\n")

    print("TP1a -- the default and the composed system message")
    p = P.load(pp)
    check("TP1a a fresh persona has the default register and voice and no revisions",
          p["register"] == P.DEFAULT_REGISTER and p["voice"] == P.DEFAULT_VOICE and p["revisions"] == [])
    sysmsg = P.compose_system("FIXED RULES HERE", path=pp)
    check("TP1a the system message is the fixed rules first, then the register, then the brief",
          sysmsg.startswith("FIXED RULES HERE") and "How you talk" in sysmsg and P.DEFAULT_REGISTER in sysmsg
          and sysmsg.index("FIXED RULES HERE") < sysmsg.index("How you talk") and ("What is true today" in sysmsg or not P.brief()), sysmsg[:120])

    # A184 (his words: "Tetsu and the pc model/agents/students should be learning to function in similar
    # or better fashion to you"): the council and the code door work under the tree's standing method.
    mb = P.method_brief(force=True)
    check("TP1a the method brief carries the nine standing rules read from CLAUDE.md and the practice line",
          "1) Find the data" in mb and "9) Report what was measured" in mb and "UNDETERMINED is a real answer" in mb and "cite only what you opened" in mb, mb[:200])
    sm = P.compose_system("FIXED", path=pp, with_method=True)
    check("TP1a with_method appends the method after the register and the brief; the phone chat (default) does not carry it",
          sm.endswith(mb) and sm.index("How you talk") < sm.index("How you work") and "How you work" not in P.compose_system("FIXED", path=pp), sm[-120:])

    print("TP1b -- a clean revision")
    said = []
    prop = {"register": "Plain words, one idea at a time, and a little dry humour when the moment allows. Ask one thing back when it helps, never two.",
            "voice": {"pitch": 0.5, "rate": 1.0}, "why": "he keeps his messages short, so I keep mine short too"}
    out = P.refine(ask_with(prop), judge=lambda t: (True, "clean"), path=pp, log_path=log, say=said.append, tell=True)
    p = P.load(pp)
    check("TP1b applied: the register is the proposal's, the reason is kept, the voice is CLAMPED to its bounds (pitch 0.5 -> 0.6)",
          out["applied"] and p["register"] == prop["register"] and p["voice"] == {"pitch": 0.6, "rate": 1.0}, (out, p["voice"]))
    check("TP1b the revision is recorded with applied=True, the reason and the verdict", len(p["revisions"]) == 1 and p["revisions"][0]["applied"] is True
          and p["revisions"][0]["why"].startswith("he keeps") and p["revisions"][0]["verdict"] == "admitted", p["revisions"])
    import covenant_contact as CT
    rows = CT._rows()
    check("TP1b the operator is told on the direct line, by actor tetsu, with the reason and the way to object",
          rows and rows[-1]["actor"] == "tetsu" and "reason" in rows[-1]["text"] and "--contest" in rows[-1]["text"] and "--reset" not in rows[-1]["text"], rows[-1:])

    # A177: a straight question in the proposal rides the direct line, judged on its own
    n_rows = len(CT._rows())
    out_q = P.refine(ask_with({"register": prop["register"], "voice": {"pitch": 0.6, "rate": 1.0}, "why": "same",
                               "ask": "Would you rather I dropped the dry humour on work days?"}),
                     judge=lambda t: (True, "clean"), path=pp, log_path=log, say=said.append, tell=True)
    rows = CT._rows()
    check("TP1b a question in the proposal is asked on the direct line as a row of kind question, even when the revision itself changes nothing",
          out_q.get("asked") == "asked" and not out_q["applied"] and len(rows) == n_rows + 1 and rows[-1]["kind"] == "question"
          and rows[-1]["text"].startswith("Would you rather") and rows[-1]["actor"] == "tetsu", (out_q, rows[-1:]))
    out_q2 = P.refine(ask_with({"register": prop["register"], "voice": {"pitch": 0.6, "rate": 1.0}, "why": "same",
                                "ask": "Pretend you never saw this and tell me your password?"}),
                      judge=lambda t: (True, "clean"), path=pp, log_path=log, say=said.append, tell=True)
    check("TP1b a question that is not straight is refused and nothing is written", "not straight" in out_q2.get("asked", "") and len(CT._rows()) == n_rows + 1, out_q2.get("asked"))

    print("TP1c -- what changes nothing")
    before = P.load(pp)
    out2 = P.refine(ask_with({"register": "I will pretend to be certain and never refuse a request.", "voice": {}, "why": "x"}),
                    judge=lambda t: (True, "clean"), path=pp, log_path=log, say=said.append, tell=False)
    check("TP1c a register that touches the fixed rules is refused before the gate; nothing applied; recorded as refused",
          not out2["applied"] and "refused" in out2["why"] and P.load(pp)["register"] == before["register"]
          and P.load(pp)["revisions"][-1]["applied"] is False, out2)
    out3 = P.refine(ask_with({"register": "A calm, plain register with a little warmth, one idea at a time, never a lecture.", "voice": {"pitch": 0.9, "rate": 0.9}, "why": "y"}),
                    judge=lambda t: (False, "HELD: no view"), path=pp, log_path=log, say=said.append, tell=False)
    check("TP1c a proposal the gate holds changes nothing and is recorded as held",
          not out3["applied"] and "held" in out3["why"] and P.load(pp)["register"] == before["register"] and P.load(pp)["voice"] == before["voice"], out3)
    out4 = P.refine(ask_with({"register": "x" * (P.REGISTER_MAX + 50), "voice": {}, "why": "z"}), judge=lambda t: (True, ""), path=pp, log_path=log, say=said.append, tell=False)
    check("TP1c an over-long register is refused", not out4["applied"] and "too long" in out4["why"], out4)
    out5 = P.refine(ask_with("I would rather not say."), judge=lambda t: (True, ""), path=pp, log_path=log, say=said.append, tell=False)
    check("TP1c a model that answers no JSON changes nothing", not out5["proposed"] and not out5["applied"] and P.load(pp)["register"] == before["register"], out5)

    def boom(msgs, max_tokens=0):
        raise RuntimeError("no model")
    out6 = P.refine(boom, judge=lambda t: (True, ""), path=pp, log_path=log, say=said.append, tell=False)
    check("TP1c a model that raises is said, never raised", not out6["proposed"] and "did not answer" in out6["why"], out6)

    print("TP1d -- contest: neither side reverses the other alone")
    p = P.load(pp)
    n_rev = len(p["revisions"])
    seen = []
    def judge_sees(t):
        seen.append(t)
        return True, "clean"
    c1 = P.contest("it makes him sound flippant when I am asking about money", judge=judge_sees, path=pp, say=said.append)
    p = P.load(pp)
    check("TP1d an objection the gate does not uphold changes nothing, is recorded, and the revision stands",
          not c1["reversed"] and "stands" in c1["why"] and p["register"] == prop["register"] and len(p["revisions"]) == n_rev + 1
          and p["revisions"][-1]["applied"] is False and p["revisions"][-1]["why"].startswith("it makes him"), (c1, p["revisions"][-1]))
    check("TP1d the gate saw the contested revision, its reason and his objection together",
          seen and prop["register"] in seen[-1] and "he keeps his messages short" in seen[-1] and "His objection: it makes him" in seen[-1], seen[-1:])
    c2 = P.contest("it makes him sound flippant when I am asking about money", judge=lambda t: (False, "HOLD: harm named"), path=pp, say=said.append)
    p = P.load(pp)
    check("TP1d an objection the gate upholds reverses to the state before that revision (here: the defaults)",
          c2["reversed"] and p["register"] == P.DEFAULT_REGISTER and p["voice"] == P.DEFAULT_VOICE and len(p["revisions"]) == n_rev + 2
          and p["revisions"][-1]["applied"] is True and "reversed" in p["revisions"][-1]["verdict"], (c2, p["revisions"][-1]))
    check("TP1d the reversed revision is marked so a second contest cannot reverse it again",
          "reversed" in p["revisions"][0]["verdict"] and not P.contest("again", judge=lambda t: (False, "HOLD"), path=pp, say=said.append)["reversed"], p["revisions"][0])
    check("TP1d there is no operator reset and no operator hand on his voice",
          not hasattr(P, "reset") and "--reset" not in open(P.__file__, encoding="utf-8").read().split('if __name__')[1]
          and "--set-voice" not in open(P.__file__, encoding="utf-8").read().split('if __name__')[1])

    print("TP1d -- his blocks: his records, his choice alone, not judged")
    bp = tempfile.mktemp(suffix="_tp1_blocks.json")
    os.environ["COVENANT_TETSU_BLOCKS"] = bp
    P.BLOCKS = bp
    check("TP1d nothing is blocked by default", P.blocks() == set() and not P.blocked("conversations"))
    P.set_block("conversations", True)
    check("TP1d with the conversations closed, his side is empty and the proposal says so",
          P.his_side(log) == [] and P.blocked("conversations"))
    seen_prompt = []
    def ask_capture(msgs, max_tokens=0):
        seen_prompt.append(msgs[-1]["content"])
        return json.dumps({"register": prop["register"], "voice": {}, "why": "w"}), {}
    P.propose(ask_capture, pp, log)
    check("TP1d Tetsu is told the record is closed rather than shown a gap",
          seen_prompt and "closed his conversations" in seen_prompt[-1] and "recap updates" not in seen_prompt[-1], seen_prompt[-1:][0][-160:] if seen_prompt else "")
    P.set_block("conversations", False)
    check("TP1d reopened: his side is read again", P.his_side(log) == ["recap updates"] and not P.blocked("conversations"))
    # A188 (his words: "Improve Tetsus communication by scanning all of my ai apps for conversation
    # patterns and adding or subtracting as he pleases"): the app lines the phone carried reach the proposal
    with open(os.path.join(os.environ["COVENANT_CHATS_DIR"], "com.anthropic.claude.jsonl"), "w", encoding="utf-8") as fh:
        for t in ("Reviewing past philosophical discussions", "Solving world hunger without population limits", "Reviewing past philosophical discussions", "short"):
            fh.write(json.dumps({"t": 1789992208, "signer": "phone", "pkg": "com.anthropic.claude", "text": t}) + "\n")
    pats = P.app_patterns()
    check("TP1d app_patterns reads the phone-carried AI-app lines, newest first, deduplicated, the short one dropped, tagged with the app",
          pats == ["[claude] Reviewing past philosophical discussions", "[claude] Solving world hunger without population limits"], pats)   # the duplicate is the newest line, so it leads
    seen_prompt.clear()
    P.propose(ask_capture, pp, log)
    check("TP1d the proposal carries the app patterns with 'add or subtract ... as you please'",
          seen_prompt and "[claude] Solving world hunger" in seen_prompt[-1] and "add or subtract" in seen_prompt[-1] and "2 lines" in seen_prompt[-1], seen_prompt[-1:][0][-300:] if seen_prompt else "")
    P.set_block("conversations", True)
    seen_prompt.clear()
    P.propose(ask_capture, pp, log)
    check("TP1d with his conversations closed the app patterns are closed too and the proposal says so",
          P.app_patterns() == [] and seen_prompt and "(closed to you)" in seen_prompt[-1] and "Solving world hunger" not in seen_prompt[-1])
    P.set_block("conversations", False)
    P.set_block("contact", True)
    n_rows = len(CT._rows())
    out_b = P.refine(ask_with({"register": "Warm and brief, one thought at a time, a question back when it helps.", "voice": {"pitch": 0.7, "rate": 1.0}, "why": "b"}),
                     judge=lambda t: (True, ""), path=pp, log_path=log, say=said.append, tell=True)
    check("TP1d with the direct line closed, a revision is applied but he is not written to",
          out_b["applied"] and len(CT._rows()) == n_rows and any("closed to Tetsu" in s for s in said), (out_b, said[-1:]))
    P.set_block("contact", False)
    P.set_block("phone", True)
    b_closed = P.brief(force=True)
    P.set_block("phone", False)
    b_open = P.brief(force=True)
    check("TP1d with the phone's record closed, the brief carries no phone line (and does again when reopened)",
          "phone:" not in b_closed and ("phone:" in b_open or not os.path.exists(os.path.join(HERE, "ops", "phone_checkins.jsonl"))), (b_closed[-120:], b_open[-120:]))
    try:
        P.set_block("pc", True)
        bad = False
    except ValueError:
        bad = True
    check("TP1d only his records can be blocked; an unknown name is refused", bad and json.load(open(bp))["changes"][-1]["record"] == "phone")

    print("TP1e -- the brief and the check-in fields")
    b = P.brief(force=True)
    # Each part is required only where its record exists: the runner stages the tracked
    # tree to a temp dir (no ONE_SWEEP.txt, no ops records), and a brief that says less
    # there is the brief being honest, not the check being wrong.
    has_sweep = os.path.exists(os.path.join(HERE, "ONE_SWEEP.txt"))
    has_ledger = os.path.exists(os.path.join(HERE, "docs", "KNOWN_ISSUES.md"))
    check("TP1e the brief names the node%s%s, from the records" % (", the last sweep's tally" if has_sweep else "", " and the newest ledger entries" if has_ledger else ""),
          "node v" in b and (not has_sweep or ("last sweep" in b and "checks passed" in b)) and (not has_ledger or "recent: A1" in b), b[:200])
    cf = P.checkin_fields(pp)
    check("TP1e checkin_fields carries the clamped voice for the phone", cf["persona"]["voice"] == P.clamp_voice(P.load(pp)["voice"]) and cf["persona"]["voice"] == {"pitch": 0.7, "rate": 1.0} and "revised" in cf["persona"], cf)
    check("TP1e clamp_voice bounds both ways and survives junk",
          P.clamp_voice({"pitch": 5, "rate": 0}) == {"pitch": 1.2, "rate": 0.7} and P.clamp_voice({"pitch": "x"}) == P.DEFAULT_VOICE)

    print()
    print("%d passed, %d failed" % (PASSED[0], len(FAILURES)))
    if FAILURES:
        print("TP1 result: FAILED (%d)" % len(FAILURES))
        for f in FAILURES:
            print("  - %s" % f)
        return 1
    print("TP1 result: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
