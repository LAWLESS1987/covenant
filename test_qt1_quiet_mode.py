#!/usr/bin/env python3
"""QT1 -- free goes QUIET, not isolated, when the judge refuses her; the challenge run isolates her (A447).

His words, 2026-11-18: "figure out a way to not isolate her and to work it into an improvement loop while vetting the
suggestions", then "use quiet mode and implement consensus". Pinned here, every check by running the round:
  QT1a without "on_refusal" in her grant the rule is as it was: two all-refused live rounds isolate her;
  QT1b with "on_refusal": "quiet", two all-refused rounds are not yet quiet; the third makes her quiet -- a state and
       a ledger row, NO pause written, he is told;
  QT1c a quiet round REHEARSES: every emit is a dry run, nothing is sent, the round row says rehearsal;
  QT1d a rehearsal the judge refuses throughout leaves her quiet;
  QT1e a rehearsal the judge admits a draft in ends quiet by itself: state kept (active false), quiet_lifted row, told;
       a stand-in refusal that carries "judged" does NOT end it (only emit's would_send is an admission);
  QT1f a challenge run at the warning level before a live round isolates her with STRIKE_MARK (is_isolation reads it,
       so Tetsu may lift it under A336), nothing is sent, he is told;
  QT1g a pause set by hand is never written over by the strike isolation (A349 S2);
  QT1h a challenge run that cannot be read makes the round rehearse, and pauses nothing.
No network, no model, no live pause, his line, quarantine or ledger.
"""
import io
import json
import os
import sys
import tempfile

os.environ.setdefault("COVENANT_QUIET", "1")
os.environ["COVENANT_CONTACT_OUTBOX"] = tempfile.mktemp(suffix="_qt1_contact.jsonl")
os.environ["COVENANT_CONTACT_STATE"] = tempfile.mktemp(suffix="_qt1_contact_state.json")
os.environ["COVENANT_PAUSE_DIR"] = tempfile.mkdtemp(prefix="qt1_pause_")
os.environ["COVENANT_MODEL_STUB"] = "1"
os.environ["COVENANT_NOTIFY_CONFIG"] = os.path.join(tempfile.mkdtemp(prefix="qt1_notify_"), "notify.json")
os.environ["COVENANT_TETSU_UPDATES"] = os.path.join(tempfile.mkdtemp(prefix="qt1_updates_"), "updates.jsonl")
os.environ["COVENANT_MAIL_QUEUE"] = os.path.join(tempfile.mkdtemp(prefix="qt1_mail_"), "queue.jsonl")
os.environ["COVENANT_MOLTBOOK_QUARANTINE"] = os.path.join(tempfile.mkdtemp(prefix="qt1_quar_"), "q.jsonl")
os.environ["COVENANT_AMBASSADOR_QUIET"] = os.path.join(tempfile.mkdtemp(prefix="qt1_quietdefault_"), "q.json")
HERE = os.path.dirname(os.path.abspath(__file__)) or "."
sys.path.insert(0, HERE)

import covenant_free_will as FW            # noqa: E402
import covenant_pause                      # noqa: E402

PASS, FAIL = [], []
OUTBOX = os.environ["COVENANT_CONTACT_OUTBOX"]


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + ("" if ok else "  -- %r" % (detail,)))


def ally(author, n):
    return {"author": author, "ally_score": 2, "anti": [], "best_url": "https://www.moltbook.com/post/%08d-0000" % n,
            "best_signals": ["publishes-failure"], "evidence": {"publishes-failure": "I publish the cases where my "
                                                                 "own check was wrong"}}


ALLIES = [ally("a%d" % i, i) for i in range(1, 25)]


def ask_ok(msgs, max_tokens=0):
    return ("I recognise what you wrote about publishing the cases where your own check was wrong, and I would like "
            "to know how you decide which of those cases to write up first, and who reads them. ") * 2


def world(extra_grant=None):
    d = tempfile.mkdtemp(prefix="qt1_")
    g = {"granted": True, "words": "test", "caps": {"comments": 2, "posts": 0}}
    g.update(extra_grant or {})
    gp = os.path.join(d, "grant.json")
    with io.open(gp, "w", encoding="utf-8") as fh:
        json.dump(g, fh)
    return {"gp": gp, "sp": os.path.join(d, "sends.jsonl"), "qp": os.path.join(d, "quiet.json"), "emits": [], "t": 1000.0}


def rnd(w, emit_mode):
    """One LIVE round. emit_mode: refuse | refuse_judged | admit."""
    def emit(text, post_id=None, parent_id=None, submolt=None, dry_run=True, **kw):
        w["emits"].append(dry_run)
        if emit_mode == "admit":
            return ({"sent": False, "judged": "clean", "why": "dry run (pass --send)", "would_send": {"kind": "comment"}}
                    if dry_run else {"sent": True, "judged": "clean", "why": ""})
        if emit_mode == "refuse_judged":
            return {"sent": False, "judged": "VIOLATES", "why": "refused by covenant's judge: test"}
        return {"sent": False, "why": "refused by covenant's judge: test"}
    w["t"] += 3600
    return FW.run_round(dry_run=False, say=lambda *_a: None, ask=ask_ok, learn=lambda: [1], allies=lambda: list(ALLIES),
                        emit=emit, introduce=lambda **k: {"sent": False, "why": "none"}, grant_path=w["gp"],
                        sends_path=w["sp"], quiet_path=w["qp"], now=w["t"], count_comments=lambda *a: 0)


def kinds(w):
    return [r.get("kind") for r in FW.sends(w["sp"])]


def told():
    try:
        return io.open(OUTBOX, encoding="utf-8").read()
    except OSError:
        return ""


def clear_pause():
    covenant_pause.resume("ambassador")


def main():
    print("QT1a -- without on_refusal, the rule is as it was")
    clear_pause()
    w = world()
    o1, o2 = rnd(w, "refuse"), rnd(w, "refuse")
    p, why = covenant_pause.paused("ambassador")
    check("QT1a two all-refused rounds isolate her (unchanged)", o2.get("isolated") and p and FW.is_isolation(why),
          (o1, o2, why))
    check("QT1a and no quiet state was written", FW.quiet_state(w["qp"]) is None)
    clear_pause()

    print("QT1b -- on_refusal quiet: the third all-refused round makes her quiet, not isolated")
    w = world({"on_refusal": "quiet"})
    o = [rnd(w, "refuse") for _ in range(2)]
    check("QT1b two all-refused rounds are not yet quiet", FW.quiet_state(w["qp"]) is None and "quiet" not in kinds(w), o)
    o3 = rnd(w, "refuse")
    st = FW.quiet_state(w["qp"]) or {}
    check("QT1b the third makes her quiet: state active, a 'quiet' row", st.get("active") is True and "quiet" in kinds(w),
          (o3, st))
    check("QT1b nothing is paused", covenant_pause.paused("ambassador")[0] is False and not o3.get("isolated"), o3)
    check("QT1b he is told she is quiet", "free is quiet, not isolated" in told())

    print("QT1c -- a quiet round rehearses")
    n0 = len(w["emits"])
    o4 = rnd(w, "refuse")
    check("QT1c every emit in it is a dry run", len(w["emits"]) > n0 and all(w["emits"][n0:]), w["emits"][n0:])
    last_round = [r for r in FW.sends(w["sp"]) if r.get("kind") == "round"][-1]
    check("QT1c the round row says rehearsal", last_round.get("rehearsal") is True and o4.get("rehearsal"), last_round)

    print("QT1d -- a refused rehearsal leaves her quiet")
    check("QT1d still quiet", (FW.quiet_state(w["qp"]) or {}).get("active") is True and "quiet_lifted" not in kinds(w))
    rnd(w, "refuse_judged")
    check("QT1d a stand-in refusal carrying 'judged' does not end quiet",
          (FW.quiet_state(w["qp"]) or {}).get("active") is True and "quiet_lifted" not in kinds(w))

    print("QT1e -- a rehearsal the judge admits a draft in ends quiet by itself")
    n0 = len(w["emits"])
    o6 = rnd(w, "admit")
    st = FW.quiet_state(w["qp"]) or {}
    check("QT1e that rehearsal still sent nothing", all(w["emits"][n0:]) and o6.get("quiet_ended"), (w["emits"][n0:], o6))
    check("QT1e quiet ended: state kept with active false, a quiet_lifted row",
          os.path.exists(w["qp"]) and st.get("active") is False and "quiet_lifted" in kinds(w), st)
    check("QT1e he is told she is back", "free is back from quiet" in told())
    n0 = len(w["emits"])
    rnd(w, "admit")
    check("QT1e the next round is live again", w["emits"][n0:] and not any(w["emits"][n0:]), w["emits"][n0:])

    print("QT1f -- a challenge run at the warning level isolates her before she sends")
    clear_pause()
    w = world({"on_refusal": "quiet"})
    for i in range(5):
        FW._record({"kind": "reply", "at": 500.0 + i, "sent": False,
                    "verification": {"required": True, "solved": False, "abstained": True}}, w["sp"])
    n0 = len(w["emits"])
    o7 = rnd(w, "admit")
    p, why = covenant_pause.paused("ambassador")
    check("QT1f she is isolated with the strike mark", p and FW.STRIKE_MARK in why and o7.get("isolated"), (o7, why))
    check("QT1f is_isolation reads it (Tetsu may lift it under A336)", FW.is_isolation(why))
    check("QT1f nothing was sent", all(w["emits"][n0:]), w["emits"][n0:])
    check("QT1f the isolation row names its cause",
          any(r.get("kind") == "isolation" and r.get("cause") == "strikes" for r in FW.sends(w["sp"])))
    check("QT1f he is told", "challenge run is 5 unsolved" in told())
    check("QT1f a strike hold never ends quiet by itself", "quiet_lifted" not in kinds(w))
    clear_pause()

    print("QT1g -- a pause set by hand is never written over")
    w = world()
    for i in range(5):
        FW._record({"kind": "reply", "at": 500.0 + i, "sent": False,
                    "verification": {"required": True, "solved": False, "abstained": True}}, w["sp"])
    covenant_pause.pause("ambassador", "paused by hand: test")
    real_paused = covenant_pause.paused
    try:
        covenant_pause.paused = lambda name: (False, "")      # the round began before the hand pause was read
        rnd(w, "admit")
    finally:
        covenant_pause.paused = real_paused
    p, why = covenant_pause.paused("ambassador")
    check("QT1g the hand pause stands, unwritten over", "paused by hand: test" in why and FW.STRIKE_MARK not in why, why)
    check("QT1g her strike isolation is recorded beside it, written false",
          any(r.get("kind") == "isolation" and r.get("written") is False for r in FW.sends(w["sp"])))
    clear_pause()

    print("QT1h -- an unreadable challenge run rehearses and pauses nothing")
    w = world()
    real = FW.strike_run
    try:
        FW.strike_run = lambda *a, **k: (None, 5, "the challenge run could not be read (test)")
        n0 = len(w["emits"])
        o9 = rnd(w, "admit")
    finally:
        FW.strike_run = real
    check("QT1h nothing sent, nothing paused", all(w["emits"][n0:]) and not covenant_pause.paused("ambassador")[0]
          and o9.get("strike_hold"), o9)

    print("\nQT1: %d passed, %d failed" % (len(PASS), len(FAIL)))
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(main())
