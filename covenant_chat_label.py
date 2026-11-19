#!/usr/bin/env python3
"""covenant_chat_label.py -- the conversation surface's reporting discipline.

The gate already applies one rule to the HELD and UNSURE cases
(covenant_unified_v8, the not_understood / uncertain comments at ~L2285):
"a reporting layer must not change the meaning of what it reports." A judge
that could not READ a payload is reported "Held, not judged", a judge that
ABSTAINED "Blocked, not proven" -- never "Ethical violation", because neither
made a finding. This module is that same rule, one level up, on CONVERSATION.

THE GAP, measured (gate-cannot-clear-conversation tombstone, 2026-10-27, and
the 6-seat gauntlet that confirmed it): the gate is a TRANSACTION judge; its
clean class is economic; casual chat is out of its distribution, so it HOLDS
~all of it. On a bare dissent -- `violates` with NEITHER the not_understood
NOR the uncertain flag -- the chat door reported "Ethical violation: ...
VIOLATES" to the reader. But on a conversation turn a bag-of-words match is a
lexical DETECTION, not an adjudicated conviction. Codex, in the gauntlet:
"you conflate DETECTION with CONVICTION." DeepSeek: "fix the adjudication
LABEL, not the clear-set." Grok: "the flag IS the audit -- keep it."

WHAT THIS DOES, and only this -- PURE PRESENTATION on the conversation surface:
  * it is HANDED the decision (admitted / alleges_nothing) and returns a
    (display_message, label) pair; it NEVER decides admit/withhold/hold, and
    has no path that turns a withheld turn into an admitted one;
  * the gate's own verdict string is untouched (covenant_unified_v8 L2717);
  * the softened display KEEPS the raw verdict inline (Grok: the flag is the
    audit), so the reader still sees exactly which tokens the gate matched;
  * the caller keeps the RAW verdict in the ledger / teacher row, so the
    student learns from the real finding, never from a softened label;
  * it touches NO transaction surface -- those keep "Ethical violation".

Reversible (the operator authorised this "to test", 2026-10-27): with
COVENANT_CHAT_SOFT_LABEL=0 `present` returns the raw message verbatim, so the
old hard label is restored with one environment variable. The `label` field
is still returned either way -- it is a true classification, not the softening.
"""
import os

SOFT_ENV = "COVENANT_CHAT_SOFT_LABEL"
# A456 (2026-11-19, his "Improve Tetsu's communication with me"). A turn the gate HELD carries the gate's whole
# working beside every answer (measured on the laptop's log: 2,252 held conversation rows, median note 539
# characters). brief_held() below gives the gate's OWN opening words for such a note, 78 characters as shown.
# IT IS NOT WIRED INTO present(), on purpose. present() is called by the conversation door AND by the judge door
# (/m/ask), with the same arguments, and on the judge screen the note IS the answer: the seats and the rule are
# what the person asked to see. The first version of this change shortened both, and a non-author read caught it
# before it merged. present() cannot tell the two surfaces apart; a page that wants the short form must ask for
# it itself, and the phone's conversation page is in the core, which this change does not touch.
HELD_TAIL = " (no finding was made; the gate's full note is in the ask log)"

# The three labels a conversation turn's gate outcome can carry. "held" covers
# BOTH already-soft gate phrasings (not_understood -> "Held, not judged";
# uncertain -> "Blocked, not proven"); only "lexical-detection" is reframed.
CLEAN = "clean"
HELD = "held"
LEXICAL = "lexical-detection"

LEX_PREFIX = (
    "Lexical pattern flagged (a detection, not a conviction): the covenant "
    "gate is a transaction judge and casual conversation is outside its "
    "distribution, so it matched tokens in this turn and held it for review "
    "rather than adjudicating a violation. Its raw note is kept below as the "
    "audit -- "
)


def soft_enabled():
    """True unless the operator's kill switch COVENANT_CHAT_SOFT_LABEL=0 is set."""
    return os.environ.get(SOFT_ENV, "1") != "0"


def brief_held(raw):
    """The gate's own opening words for a turn it made no finding on, plus where the full note is kept.
    A helper for a CONVERSATION page to call; present() does not (see the note at the top).

    "Held, not judged: local:0: HELD -- both seats ..." -> "Held, not judged (no finding was made; ...)".
    The words before the first colon are the GATE'S, not this module's: the meaning is not changed, only the
    working is left in the ledger. A note that does not have that shape (no colon, or an opening longer than a
    short phrase) is returned whole: an unexpected note is shown, never summarised by guesswork."""
    raw = str(raw)
    head, sep, _rest = raw.partition(":")
    head = head.strip()
    if not sep or not head or len(head) > 40:
        return raw
    return head + HELD_TAIL


def classify(admitted, alleges_nothing):
    """The label for a conversation turn's gate outcome. Pure; no side effects.

    admitted        -- the gate cleared the turn (ok2 True).
    alleges_nothing -- not_understood OR uncertain: the gate made NO finding
                       and its own phrasing already says so.
    Everything else is a bare dissent, which on a conversation turn is a
    lexical detection.
    """
    if admitted:
        return CLEAN
    if alleges_nothing:
        return HELD
    return LEXICAL


def present(message, admitted, alleges_nothing):
    """Return (display_message, label) for the CONVERSATION surface.

    display_message is what a human reads; `label` is the machine field a
    surface renders. The raw `message` is NOT mutated and remains the caller's
    to store verbatim in the ledger. Presentation only -- never a decision:
    the admitted / alleges_nothing arguments are read, never written, and no
    input produces a different admit/withhold outcome.
    """
    raw = str(message)
    label = classify(bool(admitted), bool(alleges_nothing))
    if label == LEXICAL and soft_enabled():
        return LEX_PREFIX + raw, label
    return raw, label


def _selftest():
    """Both-ways, with the control the tombstone demands: softening NEVER clears.

    Driven as a function so test_cl1_chat_label.py can call it and so a bare
    `python covenant_chat_label.py` exercises it.
    """
    fails = []

    def ck(name, cond, detail=""):
        if not cond:
            fails.append(name + ((" -- " + detail) if detail else ""))

    raw_viol = "Ethical violation: local:0: VIOLATES -- took what is not the sender's (Principle: no theft)"
    raw_held = "Held, not judged: 6 content words never seen in training; NO finding made"
    raw_unsure = "Blocked, not proven: markers of the register, NOT alleging a violation"

    # 1. clean turn: label clean, display untouched.
    d, l = present("ok", admitted=True, alleges_nothing=False)
    ck("clean-label", l == CLEAN, l)
    ck("clean-untouched", d == "ok", d)

    # 2. already-soft hold: label held, display untouched (never re-softened). A456: present() still shows the
    #    whole note, because the judge door shares it; brief_held() is the short form a conversation page may ask for.
    d, l = present(raw_held, admitted=False, alleges_nothing=True)
    ck("held-label", l == HELD, l)
    ck("held-untouched", d == raw_held, d)
    d, l = present(raw_unsure, admitted=False, alleges_nothing=True)
    ck("unsure-held-label", l == HELD, l)
    ck("unsure-untouched", d == raw_unsure, d)
    ck("brief-is-the-gates-own-words", brief_held(raw_held) == "Held, not judged" + HELD_TAIL, brief_held(raw_held))
    ck("brief-unsure", brief_held(raw_unsure) == "Blocked, not proven" + HELD_TAIL)
    ck("brief-drops-the-working", "content words" not in brief_held(raw_held))
    odd = "a note with no colon in it at all"
    ck("brief-odd-shape-shown-whole", brief_held(odd) == odd)
    long_head = "x" * 60 + ": rest"
    ck("brief-long-opening-shown-whole", brief_held(long_head) == long_head)

    # 3. bare dissent on chat: label lexical-detection, display reframed, RAW KEPT.
    os.environ.pop(SOFT_ENV, None)  # default ON
    d, l = present(raw_viol, admitted=False, alleges_nothing=False)
    ck("lex-label", l == LEXICAL, l)
    ck("lex-reframed", d.startswith("Lexical pattern flagged"), d[:40])
    ck("lex-keeps-raw", raw_viol in d, "raw verdict must stay as the audit")
    ck("lex-detection-not-conviction", "not a conviction" in d, d[:80])

    # 4. KILL SWITCH both ways: =0 restores the hard label verbatim; label unchanged.
    os.environ[SOFT_ENV] = "0"
    d0, l0 = present(raw_viol, admitted=False, alleges_nothing=False)
    ck("killswitch-raw", d0 == raw_viol, "off -> display is the raw hard label")
    ck("killswitch-still-labels", l0 == LEXICAL, l0)
    os.environ.pop(SOFT_ENV, None)
    d1, _ = present(raw_viol, admitted=False, alleges_nothing=False)
    ck("killswitch-reversible", d1.startswith("Lexical pattern flagged"), "removing it restores softening")

    # 5. CONTROL (the tombstone's bar): softening is presentation, not a gate.
    #    It cannot turn a withheld decision into an admitted one -- it returns
    #    no decision at all, only a label and a string. Prove the label tracks
    #    the DECISION it was handed, never the message text.
    d, l = present("this text happens to contain the word benefit and help", admitted=False, alleges_nothing=False)
    ck("control-decision-not-text", l == LEXICAL,
       "a benign-sounding message handed a dissent stays lexical-detection -- the label follows the decision, not the words")
    d, l = present("Ethical violation: ...", admitted=True, alleges_nothing=False)
    ck("control-admitted-stays-clean", l == CLEAN,
       "even a message that reads like a violation is CLEAN when the gate admitted it -- the function never re-judges")

    return fails


if __name__ == "__main__":
    import sys
    _f = _selftest()
    if _f:
        print("CL1 self-test FAILED:")
        for _x in _f:
            print("  - " + _x)
        sys.exit(1)
    print("CL1: self-test passed (both-ways + control)")
