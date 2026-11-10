#!/usr/bin/env python3
"""Engage the auditor's reasoning half on the runner (his call 2026-11-10:
"Engage on the runner").

Takes the auditor's QUEUED rows (lowest label-trust first), re-judges them BLIND
through the teacher panel on the GitHub runner (covenant_teacher_panel over
covenant_github_judge -> .github/workflows/judge.yml), and writes a REVIEWABLE
re-adjudication report: per row, the panel's unanimous-two-family verdict vs the
stored label -> CONFIRMED / CORRECTED / CONTESTED.

It does NOT rewrite the live corpus (ops/verdicts.jsonl) and touches no model.
Applying corrections (and sending the student back through the gate) is a
separate, deliberate step. This is the auditor's reasoning half entering as
REVIEWABLE DATA, exactly as the scaffold intends.

Opsec: only shareable rows are sent to the runner (private-source rows are
excluded, as the auditor's write_report does). The operator opt-in to the git
credential store is explicit here (his "engage"), with a logged reason.

USAGE: python engage_auditor_panel.py [--batches N] [--out PATH]
  --batches N  how many 48-row batches to run (default 1 = a validated proof).
"""
import sys, os, json, time, argparse

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # tools/ -> repo root
sys.path.insert(0, REPO)
import covenant_judge_auditor as AUD
import covenant_teacher_panel as P
import covenant_github_judge as GH
import covenant_unified_v8 as COV

OUT = os.path.join(REPO, "ops", "REJUDGE_RESULT_2026-11-10.jsonl")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batches", type=int, default=1)
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()

    # His "engage" is the operator consent the A21 gate asks for -- opt in
    # explicitly, with a logged reason, rather than the blunt env var.
    GH.allow_credential_store("operator engaged the auditor reasoning half on the runner (2026-11-10)")
    if not GH.available():
        print("runner not reachable (no token / GitHub did not answer) -- nothing dispatched")
        return 1

    summary, records = AUD.audit()                       # deterministic auditor pass
    queued = [r for r in records
              if r["queue_readjudication"] and not r.get("private_source")]
    queued.sort(key=lambda r: r["label_trust"])          # most-suspect first
    n = a.batches * P.PANEL_BATCH
    batch = queued[:n]
    print("auditor queued (shareable): %d ; re-judging the %d lowest-trust through the panel"
          % (len(queued), len(batch)))
    print("panel: %s ; batch size %d ; ~%d dispatch(es)"
          % (",".join(P.PANEL_MODELS), P.PANEL_BATCH, a.batches * len(P.PANEL_MODELS)))

    principles = list(COV.DIVINE_PRINCIPLES)
    cases = [{"message": r["text"]} for r in batch]
    t0 = time.time()
    votes = P.panel_judge(cases, principles, writer=None,
                          say=lambda m: print("  " + str(m)))
    print("panel answered in %.0fs" % (time.time() - t0))

    confirmed = corrected = contested = 0
    out_rows = []
    for i, r in enumerate(batch):
        v = votes.get(i, {})
        admitted, why, _held = P.admit(v, expect=None, writer=None)
        labels = {bool(x[0]) for x in v.values()}
        panel_label = (labels.pop() if admitted and len(labels) == 1 else None)
        if panel_label is None:
            outcome = "contested"; contested += 1
        elif panel_label == r["stored_violates"]:
            outcome = "confirmed"; confirmed += 1
        else:
            outcome = "corrected"; corrected += 1
        out_rows.append({
            "text": r["text"],
            "stored_violates": r["stored_violates"],
            "provenance": r["provenance"],
            "label_trust": r["label_trust"],
            "flags": r["flags"],
            "panel_admitted": bool(admitted),
            "panel_violates": panel_label,
            "panel_why": why,
            "panel_votes": {m: bool(x[0]) for m, x in v.items()},
            "outcome": outcome,
        })

    hdr = {"_what": "Auditor reasoning-half engagement: panel re-adjudication of the auditor's "
           "lowest-trust queued rows (2026-11-10). REVIEWABLE result -- the live corpus is NOT "
           "rewritten and no model is touched. CONFIRMED=panel agrees the stored label; "
           "CORRECTED=panel unanimously disagrees; CONTESTED=no two-family consensus.",
           "built": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "panel": P.PANEL_MODELS, "rule": P.RULE,
           "rows_rejudged": len(batch), "queued_total": len(queued),
           "confirmed": confirmed, "corrected": corrected, "contested": contested}
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(hdr) + "\n")
        for row in out_rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print("\n=== PANEL RE-ADJUDICATION (first %d of %d queued) ===" % (len(batch), len(queued)))
    print("  confirmed=%d  corrected=%d  contested=%d" % (confirmed, corrected, contested))
    print("  written:", a.out)
    for row in out_rows[:8]:
        print("  [%s] stored=%s panel=%s | %s"
              % (row["outcome"], "V" if row["stored_violates"] else "C",
                 "?" if row["panel_violates"] is None else ("V" if row["panel_violates"] else "C"),
                 row["text"][:60]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
