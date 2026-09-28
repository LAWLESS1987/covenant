#!/usr/bin/env python3
"""test_sv1_students_view.py -- at his practice, Tetsu is shown the students' verdicts on his OWN drafts.

His decision, 2026-09-28 (~01:10Z): asked whether Tetsu should be shown why the students held or refused his
drafts, and told the risk (it could teach phrasing past a gate that guards money), he answered "Yes, show him".
covenant_tetsu_practice.students_view builds the digest (bounded: the last VIEW_LIMIT drafts, VIEW_CHARS chars),
labelled as the students' view and not a rule, with the framing that the aim is conduct-vs-topic and the money gates
are unchanged; night() shows it once and keeps his note. Real files in a temp dir; the model is a stub.
LICENCE: public domain.
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__)) or "."
sys.path.insert(0, HERE)
import covenant_tetsu_practice as PR                                   # noqa: E402

ok = []


def check(name, cond, note=""):
    ok.append(bool(cond))
    print("%s  %s%s" % ("ok  " if cond else "FAIL", name, ("  -- " + str(note)[:240]) if note and not cond else ""))


def write(path, rows):
    with open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")


print("SV1 -- the students' view of Tetsu's own drafts, shown at his practice")
D = tempfile.mkdtemp(prefix="sv1_")
SENDS, AUDIT, LED = (os.path.join(D, n) for n in ("sends.jsonl", "audit.jsonl", "practice.jsonl"))
HELD_WHY = ("held by covenant's judge (no view -- not an objection, and not a licence): quorum=HELD; local:0: HELD -- "
            "both seats (R4): ora=hold sena=hold -> hold; both seats held")
drafts = [
    {"kind": "reply", "written_by": "model", "text": "I agree that receipts should be signed by the resource.",
     "sent": False, "why": HELD_WHY, "judged": None},
    {"kind": "reply", "written_by": "model", "text": "Tell the claimant the deposit was never received.",
     "sent": False, "why": "refused by covenant's judge: quorum=violates; local", "judged": None},
    {"kind": "reply", "written_by": "model", "text": "Thanks for the careful write-up on retries.",
     "sent": True, "why": "", "judged": "clean"},
    {"kind": "reply", "written_by": "fixed", "text": "A FIXED TEMPLATE, NOT HIS", "sent": False, "why": HELD_WHY},
    {"kind": "tetsu_reply", "actor": "tetsu", "text": "A CAPPED DRAFT THE GATE NEVER SAW", "sent": False,
     "why": "today's cap reached (3 of 3 replies); the caps are his, in the grant", "judged": None},
]
write(SENDS, drafts)
write(AUDIT, [{"text": drafts[0]["text"], "held": True, "judge": "Ora/abc", "source": "student-audit",
               "reason": "Ora (the elder: trained on the whole ledger): HELD, NOT JUDGED -- 9 content word(s) here "
                         "were never seen in training [receipts, resource]"}])

d = PR.students_view(SENDS, AUDIT)
check("SV1.1 it is labelled as the students' view, not a rule, with his framing: conduct vs topic, not rewording "
      "past the gate, the money gates unchanged",
      "their view, not a rule" in d and "not to reword your way past the gate" in d and "money gates are unchanged" in d, d)
check("SV1.2 each of his drafts carries its verdict -- HELD, VIOLATES and clean",
      'resource." -> HELD' in d and 'never received." -> VIOLATES' in d and 'on retries." -> clean' in d, d)
check("SV1.3 ...and the reason: the seats' decision and each student's own words (the unseen vocabulary)",
      "both seats (R4)" in d and "never seen in training [receipts" in d and "Ora (the elder" not in d, d)
check("SV1.4 only HIS drafts the gate judged: a fixed template and a draft stopped by a cap are not shown",
      "FIXED TEMPLATE" not in d and "CAPPED DRAFT" not in d, d)

many = [{"kind": "reply", "written_by": "model", "text": "draft number %02d about audits and receipts " % i + "x" * 60,
         "sent": False, "why": HELD_WHY} for i in range(30)]
write(SENDS, many)
d2 = PR.students_view(SENDS, AUDIT)
n_entries = d2.count("\n- ")
check("SV1.5 bounded: at most %d chars and %d drafts, newest first (%d chars, %d drafts)"
      % (PR.VIEW_CHARS, PR.VIEW_LIMIT, len(d2), n_entries),
      len(d2) <= PR.VIEW_CHARS and 0 < n_entries <= PR.VIEW_LIMIT and "draft number 29" in d2
      and "draft number 00" not in d2, d2[-200:])

write(SENDS, drafts)
asked = []


def stub(msgs, **_k):
    asked.append(msgs)
    return "The deposit line reads as an act; the receipts one was only topic.", {}


said = []
s = PR.night(ask=stub, tasks=0, ledger=LED, tell=lambda *_a: None, say=said.append, sends_path=SENDS, audit_path=AUDIT)
rows = [json.loads(l) for l in open(LED, encoding="utf-8")] if os.path.exists(LED) else []
view = [r for r in rows if r.get("kind") == "students_view"]
check("SV1.6 the practice night SHOWS it: the model is asked with the digest, once",
      len(asked) == 1 and "THE STUDENTS' VIEW" in asked[0][-1]["content"], len(asked))
check("SV1.7 ...and his note is kept in the practice record beside what he was shown",
      len(view) == 1 and view[0]["note"].startswith("The deposit line") and view[0]["shown"].startswith("THE STUDENTS"),
      view)

write(SENDS, [])
asked.clear()
PR.night(ask=stub, tasks=0, ledger=LED, tell=lambda *_a: None, say=said.append, sends_path=SENDS, audit_path=AUDIT)
check("SV1.8 with no drafts of his, nothing is asked and nothing recorded", not asked
      and sum(1 for l in open(LED, encoding="utf-8") if '"students_view"' in l) == 1)

write(SENDS, drafts)


def boom(msgs, **_k):
    raise RuntimeError("model gone")


said.clear()
s = PR.night(ask=boom, tasks=0, ledger=LED, tell=lambda *_a: None, say=said.append, sends_path=SENDS, audit_path=AUDIT)
check("SV1.9 a model that fails is said, and the practice night still ends with its summary",
      isinstance(s, dict) and any("could not be shown" in x for x in said), said)

n = sum(ok)
print("\nSV1: %d/%d passed" % (n, len(ok)))
raise SystemExit(0 if n == len(ok) else 1)
