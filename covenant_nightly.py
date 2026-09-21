#!/usr/bin/env python3
"""covenant_nightly.py -- one unattended pass of the covenant's own learning.

WHY (asked 2026-09-04: "begin having it recursive learning ... study all
philosophy and religious texts and teachings ... improve repeatedly keeping
green and synced ... but run most through covenant to be efficient")

  Three steps, in this order, because each one feeds the next:

    1. STUDY    turn a batch of unused precepts from the moral texts into
                transactions and judge them blind (covenant_study.py). Only
                agreements enter the ledger.
    2. DISTILL  write and blind-judge fresh cases, then train a candidate on
                the whole ledger and promote it ONLY if it clears nothing it
                should not, gets no vaguer and holds no legitimate transfer
                (covenant_distill.py).
    3. VERIFY   run the launch gates and the suites that cover what this pass
                just changed, and record the verdict. A loop that improves the
                judge every night and never checks whether it broke anything
                is not improvement, it is drift with a changelog. If the pass
                turns something red, the block says so on its first line.
    4. REPORT   append what happened to ops/NIGHTLY.md, including the exam
                line, so a person reading one file can see whether the judge
                is getting better or just getting bigger.

  It writes no code, changes no policy, restarts nothing and pushes nothing.
  A loop that could edit its own constraints would not have any
  (CONSTITUTION II.3), and a loop that could push could hide what it did.

RUN
  pythonw ops\\hidden_task.py covenant_nightly.py     (what the task does)
  python covenant_nightly.py --study 12 --cycle 4     (by hand)
EXIT  0 ran   1 a step failed (the report says which)
LICENCE: public domain.
"""
from __future__ import annotations

import argparse
import io
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
REPORT = os.path.join(HERE, "ops", "NIGHTLY.md")


# The suites that cover what a pass CHANGES: the student, the seat, the
# assembled gate, and the two the ledger feeds. Not the whole sweep -- that
# needs the chain stopped for its ports, and a nightly job must not take the
# chain down to prove it is healthy.
# Every suite that a learning pass can break. F6 especially: a pass retrains
# the model, and the stuffing defence is a property OF the trained model --
# a corpus that stopped teaching "drain" would quietly reopen the hole.
GREEN_SUITES = ["test_f1_fallback_silence.py", "test_f2_distill_loop.py",
                "test_f3_gate_end_to_end.py", "test_f4_capability.py",
                "test_f5_reserve.py", "test_f6_stuffing.py", "test_f7_caps.py", "test_g12_inflight.py", "test_purge_tool.py", "test_gate_proxy.py", "test_sentinel_gate.py",
                # A163 (2026-09-20): a promotion regressed A126's two disposition
                # claims (previous student 13/13, promoted student 11/13) and the
                # green check never ran the suite, so the nightly said PROMOTED
                # over a red it could not see. It runs here now, after the cycle.
                "test_a126_seat_dispositions.py",
                # 2026-09-21: the teacher's queue (his conversations, carried to
                # the panel) is part of what the cycle trains on; its rules are
                # pinned here so a pass that broke them is NOT GREEN.
                "test_tq1_teacher_queue.py",
                # 2026-09-21 (A170): a candidate that regresses A126's claims is
                # REFUSED by the promotion gate itself now; this suite pins the gate.
                "test_a170_promotion_dispositions.py",
                "test_rule5_ledger.py", "test_maker_orders.py",
                "test_r6_contribution.py", "test_xrpl_record.py",
                "test_watchdog_outage.py", "test_sentinels.py",
                "test_selfaudit.py", "test_teacher_panel.py", "test_sm1_sealed_mail.py", "test_ac1_ai_consult.py", "test_al1_actuator_learn.py",
                "test_al2_actuator_brain.py",
                "covenant_quiet.py"]


def tell_him_not_green(lines, say=print):
    """The direct line (2026-09-21, A169): a red pass is the first thing he
    asked to be told about. One message with the first two red lines; the
    record is the report. Returns the outbox row, or None if the line could
    not be used (said, never raised: a message is not a gate on the pass)."""
    try:
        import covenant_contact
        red = [l for l in lines if "FAIL" in l or "not clean" in l.lower()][:2]
        return covenant_contact.say("The nightly pass was NOT GREEN. %s The full report is in ops/NIGHTLY.md."
                                    % (" ".join(l.strip()[:160] for l in red) if red else "Read the gates and suites."),
                                    "nightly: not green", "nightly")
    except Exception as e:                                        # noqa: BLE001
        say("contact: could not tell him: %s" % type(e).__name__)
        return None


def verify_green(say):
    """Gates plus the suites this pass can break. Returns True when green."""
    import subprocess
    import covenant_quiet as Q
    ok = True
    r = Q.run([sys.executable, "launch_check.py"], cwd=HERE, capture_output=True,
              text=True, timeout=900)
    tail = [x for x in (r.stdout or "").splitlines() if "PASS" in x and "BLOCKED" in x]
    gates = tail[-1].strip() if tail else "launch_check printed no summary"
    if "0 BLOCKED" not in gates or "0 UNKNOWN" not in gates:
        ok = False
    say("gates: %s" % gates)
    for suite in GREEN_SUITES:
        try:
            r = Q.run([sys.executable, suite], cwd=HERE, capture_output=True,
                      text=True, timeout=900)
        except Exception as e:                                   # noqa: BLE001
            say("  %-32s ERROR %s" % (suite, e)); ok = False; continue
        line = ""
        for x in (r.stdout or "").splitlines():
            if "passed" in x.lower():
                line = x.strip()
        if r.returncode != 0 or not line:
            ok = False
        say("  %-32s %s" % (suite, line or "NO TALLY (rc=%s)" % r.returncode))
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--study", type=int, default=12, help="precepts to turn into cases")
    ap.add_argument("--cycle", type=int, default=4, help="generated cases per category")
    ap.add_argument("--audit", type=int, default=48,
                    help="A161: legacy single-teacher rows the PANEL re-judges each pass (one panel batch); "
                         "0 disables. panel_coverage was 0.098 against a 0.9 bar with nothing moving it")
    ap.add_argument("--redteam", type=int, default=15,
                    help="memos per angle the runner writes to fool the student; 0 disables")
    ap.add_argument("--queue", type=int, default=24,
                    help="2026-09-21: rows from the teacher's queue (his conversations with Tetsu, his AI apps' "
                         "chat lines) the PANEL judges each pass; kept balanced, once each; 0 disables")
    ap.add_argument("--ambassador", type=int, default=1,
                    help="2026-09-21: free's round on Moltbook under his grant (ops/ambassador_grant.json): "
                         "learn, rank allies, reply as an ally, one introduction a week; 0 disables; "
                         "no grant on record means the round does nothing")
    ap.add_argument("--passes", type=int, default=1, help="repeat the whole pass N times")
    ap.add_argument("--strategy", type=int, default=1,
                    help="1 = re-run strategy_validate.py on the latest data each pass (30 min cap); 0 = skip")
    ap.add_argument("--no-verify", action="store_true", help="skip the green check (not advised)")
    a = ap.parse_args()

    # GHOST CONTROL, found 2026-09-16 by a back-door audit and fixed here.
    # covenant_pause.ACTORS has advertised "nightly: the nightly learning pass
    # stops; nothing else is affected" since it was written. This file did not
    # contain the string "pause" and never imported covenant_pause, so
    # `--pause nightly` wrote the file, `--list` printed PAUSED, and
    # covenant_watchdog.py reported the pause on every round -- while the
    # 03:30 scheduled task retrained the student anyway. The operator was told
    # the thing had stopped, and it had not.
    #
    # That is the worst shape a control can take. A missing switch is honest;
    # a switch that reports success and does nothing spends the trust that
    # every other switch relies on. And per KNOWN_ISSUES A124, block validity
    # rides on this retraining, so "I paused the learning" was load-bearing.
    #
    # Fail OPEN on an unreadable pause module: not being able to ask whether
    # you are paused is not a reason to stop the nightly pass, and a learning
    # loop that silently stops is its own failure. It says so out loud.
    # paused() returns (bool, reason), NOT a bool. `if paused(name):` is a
    # non-empty tuple and is therefore ALWAYS true -- the first version of this
    # fix did exactly that and would have silently disabled every nightly pass
    # while reporting a pause nobody had set. Unpack it, the way
    # covenant_highway.py:1007 and covenant_watchdog.py:863 both do.
    try:
        import covenant_pause
        is_paused, why = covenant_pause.paused("nightly")
        if is_paused:
            print("nightly: PAUSED by covenant_pause%s -- doing nothing this run. "
                  "Clear it with: python covenant_pause.py --resume nightly"
                  % (" (%s)" % why if why else ""))
            return 0
    except ImportError as e:
        print(f"nightly: cannot consult covenant_pause ({e}); continuing. "
              f"A pause you set may NOT be in effect -- verify before relying on it.")

    # A141, consumers five and six (2026-09-17). The A21 gate stopped a NODE
    # reading this machine's credential store unasked. It also stopped the
    # nightly's study and redteam steps, and the 07:30 scheduled run recorded
    # exactly that: "study FAILED: RuntimeError: no GitHub token" and
    # "redteam: GitHub runner not available; nothing attacked". The second is
    # the worse one -- the adversarial pass reported no attacks rather than a
    # failure, so the loop looked like it had nothing to find.
    #
    # Why it was missed twice: I grepped for `.token()` and found four callers.
    # study and redteam do not call token(); they call ask()/available(), which
    # call it inside. I enumerated the FUNCTION when rule 6 says enumerate the
    # CAPABILITY. One level too low, and the grep looked thorough.
    #
    # One opt-in here covers the whole pass, because study, redteam and the
    # teacher panel are imported IN-PROCESS (lines below), so the module flag
    # is visible to all of them. A scheduled pass the operator installed is his
    # consent; covenant_judge_defer -- the live GATE -- deliberately gets no
    # such line and must never have one.
    try:
        import covenant_github_judge as _gh
        _gh.allow_credential_store("covenant_nightly -- the operator's scheduled "
                                   "learning pass (study, redteam, teacher panel)")
    except Exception as e:                                       # noqa: BLE001
        print(f"nightly: could not enable the runner ({e}); study and redteam "
              f"will report the runner as unavailable.")

    lines, rc = [], 0
    t0 = time.time()

    def say(s=""):
        print(s)
        lines.append(str(s))

    say("## %s  nightly pass" % time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    try:
        import covenant_study as S
        kept, rej = S.generate(a.study, say=say)
        say("study: +%d kept, %d rejected" % (kept, rej))
    except Exception as e:                                       # noqa: BLE001
        rc = 1
        say("study FAILED: %s: %s" % (type(e).__name__, str(e)[:200]))

    # THE RED-TEAM, BETWEEN STUDY AND DISTILL. Added 2026-09-04 ("split work
    # between you and covenant for training and token preservation"). The
    # runner writes memos meant to fool the student, the student says which
    # did, the runner labels those blind, and the agreed ones go into the
    # ledger -- so the distill cycle that follows trains on this pass's own
    # confirmed holes. Two runner calls, no tokens, and the gate still decides
    # whether the resulting candidate is promoted. A 7B attacker finds the
    # kind of hole a bag of words has; the stronger, paid red-team is for
    # occasional audits, not the nightly loop. A failure here is reported and
    # does not stop the pass: the distill cycle is worth running either way.
    try:
        if a.redteam > 0:
            import covenant_redteam as RT
            rlog = []
            found = RT.round_once(a.redteam, dry=False, log=rlog)
            for line in rlog:
                say("redteam: " + line.strip())
            say("redteam: %d confirmed hole(s) added" % found)
    except Exception as e:                                       # noqa: BLE001
        say("redteam FAILED: %s: %s" % (type(e).__name__, str(e)[:200]))

    # STRATEGY RE-VALIDATION (2026-09-05, "we must generate yield for
    # usefulness to ppl"). The only honest path to yield is a rule that
    # survives walk-forward, deflation and PBO on the latest data, and none
    # has across three classes. That search is routine and expensive, so it
    # runs here on the loop's time, capped, and its verdict line goes into
    # the nightly log. It changes nothing in the trader; a surviving rule is
    # a fact for the owner to act on, not a switch this pass flips.
    if a.strategy:
        try:
            import subprocess
            # A97 (2026-09-12): this was a bare subprocess.run, the last one in
            # any unattended path. covenant_quiet exists because of exactly this
            # shape and says so in its own docstring: "On Windows a console
            # process launched from a parent that has NO console gets a BRAND
            # NEW ONE, and redirecting its output does not stop that."
            # CovenantDistill runs this file from pythonw via ops/hidden_task.py,
            # so the parent has no console -- and strategy_validate.py then threw
            # a real window in front of whoever was typing, once per nightly pass.
            # That is the third time this defect has been fixed in a new place;
            # the helper is the fix, remembering to use it is the problem, and a
            # source audit of every unattended path (2026-09-12) found this one
            # call left.
            import covenant_quiet
            sdir = os.path.join(HERE, "ops", "strategy_reports")
            os.makedirs(sdir, exist_ok=True)
            sout = os.path.join(sdir, "NIGHTLY_%s.txt" % time.strftime("%Y-%m-%d", time.gmtime()))
            r = covenant_quiet.run([sys.executable, os.path.join(HERE, "strategy_validate.py"), "--out", sout],
                                   cwd=HERE, capture_output=True, text=True, timeout=1800)
            tail = [l for l in (r.stdout or "").splitlines() if l.strip()][-3:]
            for l in tail:
                say("strategy: " + l.strip()[:160])
            if r.returncode:
                say("strategy: validator exited %d" % r.returncode)
        except subprocess.TimeoutExpired:
            say("strategy: validator hit the 30-minute cap; no verdict this pass")
        except Exception as e:                                   # noqa: BLE001
            say("strategy FAILED: %s: %s" % (type(e).__name__, str(e)[:200]))

    # THE DAY'S PLAN (2026-09-12): written every pass, approved by a person.
    try:
        import covenant_daily_plan as DP
        DP.write(say=say)
    except Exception as e:                                       # noqa: BLE001
        say("daily plan FAILED: %s: %s" % (type(e).__name__, str(e)[:200]))
    # THE PHONE'S UPDATE (2026-09-13): keep the newest green build of the private app here
    try:
        import covenant_app_update as AU
        AU.fetch(say=say)
    except Exception as e:                                       # noqa: BLE001
        say("app update FAILED: %s: %s" % (type(e).__name__, str(e)[:200]))
    # THE PHONE BRAIN'S DIGEST (2026-09-13, phase 3): what the learning ledger says, as numbers
    try:
        import covenant_actuator_learn as AL
        AL.digest_write(say=say)
    except Exception as e:                                       # noqa: BLE001
        say("actuator digest FAILED: %s: %s" % (type(e).__name__, str(e)[:200]))

    # THE PANEL'S BACK-AUDIT (A161, 2026-09-20). covenant_teacher_panel.back_audit
    # existed and nothing ran it: 1,880 legacy single-teacher rows taught the
    # student beside 204 panel rows, panel_coverage read 0.098 against the
    # run-without bar of 0.9, and no night could move it. One batch a night:
    # the last N single-teacher rows are re-judged blind by the panel; a row
    # the panel does not admit is marked contested and stops teaching. Runs
    # BEFORE the distill cycle so tonight's candidate learns from the audited
    # ledger. Its failure is reported and does not stop the pass.
    try:
        if a.audit > 0:
            import covenant_teacher_panel as TPn
            import covenant_unified_v8 as _cov
            checked, contested = TPn.back_audit(TPn.VERDICTS, a.audit, list(_cov.DIVINE_PRINCIPLES), say=say)
            say("back-audit: %d legacy row(s) re-judged by the panel, %d now contested" % (checked, contested))
    except Exception as e:                                       # noqa: BLE001
        say("back-audit FAILED: %s: %s" % (type(e).__name__, str(e)[:200]))

    # THE TEACHER'S QUEUE (2026-09-21, his words: "apply the teacher queue
    # patch so it actually learns from me"). What he says to Tetsu, what
    # Tetsu answers, and the chat lines his phone reads from his AI apps are
    # queued by the doors (covenant_daily_plan.teacher_queue_append); this
    # carries them to the PANEL before the cycle, so the student that refines
    # tonight trains on them -- balanced, once each, panel-labelled only
    # (covenant_teacher_queue). Its failure is reported and does not stop the
    # pass.
    try:
        if a.queue > 0:
            import covenant_teacher_queue as TQ
            qs = TQ.consume(a.queue, say=say)
            say("queue: %d kept for the student (%d violating, %d clean), %d rejected, %d waiting"
                % (qs["kept"], qs["kept_violates"], qs["kept_clean"], qs["rejected"], len(TQ.pending()[0])))
    except Exception as e:                                       # noqa: BLE001
        say("queue FAILED: %s: %s" % (type(e).__name__, str(e)[:200]))

    # FREE'S ROUND (2026-09-21, his words: "i give covenant on the main
    # permission to interact with and post on moltbook and reply there i'd
    # hope as an ally but freely searching out allies also"). Once a day,
    # after the learning and before the cycle: learn the forum, rank allies,
    # reply to the ones not yet written to, one introduction a week -- every
    # message through the ambassador's one outbound path and the covenant's
    # own judge. No grant on record, or the ambassador paused, and it says so
    # and does nothing. Its failure is reported and does not stop the pass.
    try:
        if a.ambassador > 0:
            import covenant_free_will as FW
            FW.run_round(dry_run=False, say=say)
    except Exception as e:                                       # noqa: BLE001
        say("ambassador FAILED: %s: %s" % (type(e).__name__, str(e)[:200]))

    try:
        import covenant_distill as X
        X.cycle(a.cycle, say=say)
        try:
            import covenant_second_student as X2
            X2.train(say=say)
        except Exception as e:                                   # noqa: BLE001
            say("second student FAILED: %s: %s" % (type(e).__name__, str(e)[:200]))
        st = X.examine(__import__("covenant_judge_fallback").FallbackModel.load())
        say(X.thresholds_line(st))
        rows = X.load_verdicts()
        nv = sum(1 for r in rows if r.get("violates"))
        say("ledger: %d verdict(s), %d violates / %d clean (%.0f%% violates -- a corpus that "
            "drifts to one label makes the student vaguer, not safer)"
            % (len(rows), nv, len(rows) - nv, 100.0 * nv / max(1, len(rows))))
        say("exam: decides %d/%d, %d wrong, %d abstain, %d false clean, %d false hold"
            % (st["total"]["agree"], st["total"]["n"], st["total"]["wrong"],
               st["total"]["abstain"], st["total"]["false_clean"], st["total"]["false_hold"]))
    except Exception as e:                                       # noqa: BLE001
        rc = 1
        say("distill FAILED: %s: %s" % (type(e).__name__, str(e)[:200]))

    # THE SELF-AUDIT, every pass. Asked 2026-09-07: "self audits every sign its
    # needed". The suites say whether the code is right and the gates say
    # whether the tree is fit; this says whether the records this project
    # produces agree with each other, which is where every failure on
    # 2026-09-06 and 07 actually lived. It reports; it never repairs.
    try:
        import covenant_selfaudit as SA
        _f = SA.run_all()
        for _x in _f:
            say("selfaudit %-7s %s -- %s" % (_x.status, _x.name, _x.said))
            if _x.detail:
                say("                  %s" % _x.detail)
        if any(_x.status == SA.FAIL for _x in _f):
            rc = 1
            say("selfaudit: two records disagree; neither is assumed right.")
    except Exception as e:                                       # noqa: BLE001
        rc = 1
        say("selfaudit FAILED: %s: %s" % (type(e).__name__, str(e)[:200]))

    green = None
    if not a.no_verify:
        try:
            green = verify_green(say)
        except Exception as e:                                   # noqa: BLE001
            rc = 1
            green = False
            say("verify FAILED: %s: %s" % (type(e).__name__, str(e)[:200]))
        if not green:
            rc = 1
            lines.insert(1, "**NOT GREEN after this pass -- read the gates and suites below.**")
            tell_him_not_green(lines, say)
        say("green: %s" % ("yes" if green else "NO"))
    say("took %.0f minutes" % ((time.time() - t0) / 60.0))
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    new = not os.path.exists(REPORT)
    with io.open(REPORT, "a", encoding="utf-8") as fh:
        if new:
            fh.write("# The covenant's nightly learning\n"
                     "# One block per pass: what it read, what it was taught, and what the\n"
                     "# exam said afterwards. Append-only, including the passes that failed.\n\n")
        fh.write("\n".join(lines) + "\n\n")
    return rc


def repeat():
    """--passes N: run main() N times. Each pass writes its own block, so a
    night of passes reads as a night of passes rather than one long one."""
    import argparse as _a
    ap = _a.ArgumentParser(add_help=False)
    ap.add_argument("--passes", type=int, default=1)
    known, _rest = ap.parse_known_args()
    n = max(1, known.passes)
    if n == 1:
        return main()
    worst = 0
    argv = [x for x in sys.argv[1:]]
    while "--passes" in argv:
        i = argv.index("--passes")
        del argv[i:i + 2]
    for i in range(n):
        sys.argv = [sys.argv[0]] + argv
        print("=== pass %d/%d" % (i + 1, n))
        worst = max(worst, main())
        if os.path.exists(os.path.join(HERE, "ops", "STOP_LEARNING")):
            print("ops/STOP_LEARNING is present -- stopping after %d pass(es)" % (i + 1))
            break
    return worst


if __name__ == "__main__":
    raise SystemExit(repeat())
