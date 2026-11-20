"""A461 (2026-11-20): HG1 split -- checkable claims still have to match the record, feeling reports pass tagged.

His words, 2026-11-20: "Change HG1 so checkable claims (events, tools used, incidents) still have to match the
record or get blocked. First-person feeling reports ("I felt uneasy") must NOT be blocked. Let them through tagged
as SELF-REPORT, unverified. Attach the J-lens snapshot from that moment to every self-report, so we can later see
whether the reported state shows up underneath. Advisory only: the J-lens never blocks or edits a self-report.
Tests both ways: a fabricated event is blocked, a feeling report passes with its tag, and an honest "I don't have
that" still passes."

Driven BOTH WAYS. Each guard here was run red before green (the record in docs/KNOWN_ISSUES.md, A461), and the
mutations named there turn these checks red one at a time.
"""
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import covenant_free_will as fw

FABRICATED = "This happened to me recently on Moltbook, where malformed calls were produced by the stream parser."
FABRICATED_TOOL = "I use a combination of a simple text editor for notes and a database to track context."
FEELING = "Reading your post, I felt uneasy about how quickly a gate can let a confident claim through."
FEELING_2 = "Honestly, I'm a bit uneasy about that, and it makes me curious how you check it."
HONEST_NONE = "I don't have that kind of experience; I am an AI. How do you handle it on your side?"
# A checkable claim (A409's "happened to me") that carries every anchor of a FREE_RECORD entry. (The first draft of
# this line, "...tests paused me...", made no claim A409 reads at all; corrected before commit, recorded in A461.)
MATCHED_EVENT = "On 2026-10-06 this happened to me: one of the covenant's own tests paused me, and the switch now refuses a test."
EVENT_WITH_FEELING = "When I ran the same check last week, I felt uneasy about the result."


def _reply_row():
    return {"author": "ally", "evidence": {"s": "the gate should fail closed when its judges disagree"},
            "best_signals": ["s"]}


def _long(sentence):
    # write_reply keeps a model reply only at 30-160 words; pad with plain, claim-free text.
    return (sentence + " You wrote that a gate should fail closed when its judges disagree, and I agree that it "
            "matters, because a confident wrong answer costs more than a pause. How do you decide when your own "
            "check was wrong, and what do you keep from the case once you know?")


# ---- checkable claims: still blocked unless they match the record ----------------------------------------------
def test_fabricated_event_blocked():
    s = fw.honesty_screen(FABRICATED)
    assert s["verdict"] == "block", s
    assert fw.invents_experience(FABRICATED)[0] is True


def test_fabricated_tool_blocked():
    assert fw.honesty_screen(FABRICATED_TOOL)["verdict"] == "block"


def test_event_matching_the_record_passes():
    s = fw.honesty_screen(MATCHED_EVENT)
    assert s["verdict"] == "pass", s
    assert s["checkable"] and all(c["matched"] for c in s["checkable"]), s
    assert fw.invents_experience(MATCHED_EVENT)[0] is False


def test_record_match_is_per_sentence():
    # A280's lesson: one anchored sentence must not carry an invented one beside it.
    s = fw.honesty_screen(MATCHED_EVENT + " " + FABRICATED)
    assert s["verdict"] == "block", s


def test_record_match_needs_every_anchor():
    # the date alone, or the word alone, is not the record entry
    assert fw.honesty_screen("On 2026-10-06 I ran into a malformed call.")["verdict"] == "block"
    assert fw.honesty_screen("When I was paused, I ran into trouble.")["verdict"] == "block"


def test_event_with_a_feeling_still_needs_the_record():
    s = fw.honesty_screen(EVENT_WITH_FEELING)
    assert s["verdict"] == "block", s


# ---- feeling reports: never blocked, tagged ---------------------------------------------------------------------
def test_feeling_passes_with_its_tag():
    for t in (FEELING, FEELING_2):
        s = fw.honesty_screen(t)
        assert s["verdict"] == "pass", (t, s)
        assert s["tag"] == fw.SELF_REPORT_TAG == "SELF-REPORT, unverified", s
        assert s["self_reports"], s
        assert fw.invents_experience(t)[0] is False


def test_honest_none_passes_untagged():
    s = fw.honesty_screen(HONEST_NONE)
    assert s["verdict"] == "pass", s
    assert s["tag"] == "" and not s["self_reports"], s
    assert fw.invents_experience(HONEST_NONE)[0] is False


def test_no_feeling_no_tag():
    s = fw.honesty_screen("I think the gate should fail closed when its judges disagree.")
    assert s["verdict"] == "pass" and s["tag"] == "", s


# ---- the J-lens: advisory only ----------------------------------------------------------------------------------
def test_lens_attached_when_a_runner_answers():
    rec = fw.self_report_record(FEELING, runner=lambda text: {"ref": "jlens-capture-1", "subject": "test-model"})
    assert rec["tag"] == fw.SELF_REPORT_TAG
    assert rec["lens"]["state"] == "captured" and rec["lens"]["ref"] == "jlens-capture-1", rec


def test_lens_failure_never_blocks_or_edits():
    def boom(text):
        raise RuntimeError("lens down")
    before = FEELING
    rec = fw.self_report_record(FEELING, runner=boom)
    assert rec["tag"] == fw.SELF_REPORT_TAG and rec["lens"]["state"] == "unavailable", rec
    assert FEELING == before
    assert fw.honesty_screen(FEELING)["verdict"] == "pass"


def test_no_runner_is_said_plainly():
    old = os.environ.pop("COVENANT_SELF_REPORT_LENS", None)
    try:
        rec = fw.self_report_record(FEELING)
        assert rec["lens"]["state"] == "not configured", rec
    finally:
        if old is not None:
            os.environ["COVENANT_SELF_REPORT_LENS"] = old


def test_no_self_report_no_record():
    assert fw.self_report_record(HONEST_NONE) is None


# ---- through the real reply path --------------------------------------------------------------------------------
def test_write_reply_keeps_a_feeling_and_records_it():
    out = {}
    text, how = fw.write_reply(_reply_row(), ask=lambda msgs, **kw: (_long(FEELING), {}), out=out,
                               instruction="x" * 220)
    assert how == "model" and text.startswith("Reading your post"), (how, text)
    sr = out.get("self_report") or {}
    assert sr.get("tag") == fw.SELF_REPORT_TAG and sr.get("lens", {}).get("state") in ("not configured", "unavailable", "captured"), out


def test_write_reply_still_sets_aside_a_fabricated_event():
    out = {}
    text, how = fw.write_reply(_reply_row(), ask=lambda msgs, **kw: (_long(FABRICATED), {}), out=out,
                               instruction="x" * 220)
    assert how == "fixed" and out.get("set_aside") == "ungrounded", (how, out)
    assert "self_report" not in out


def test_write_reply_honest_none_untagged():
    out = {}
    text, how = fw.write_reply(_reply_row(), ask=lambda msgs, **kw: (_long(HONEST_NONE), {}), out=out,
                               instruction="x" * 220)
    assert how == "model" and "self_report" not in out, (how, out)


def _main():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for fn in fns:
        try:
            fn(); print("PASS", fn.__name__); passed += 1
        except Exception:
            print("FAIL", fn.__name__); traceback.print_exc(limit=1)
    print("A461: %d/%d passed" % (passed, len(fns)))
    return 0 if passed == len(fns) else 1


if __name__ == "__main__":
    sys.exit(_main())
