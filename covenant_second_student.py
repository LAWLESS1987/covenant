#!/usr/bin/env python3
"""
covenant_second_student.py -- the second student, so Ollama can leave the chain.

ASKED 2026-09-06: "form a second to replace ollama out of the equation and let
them both know we are working towards symbiosis to avoid mutual destruction."

WHAT IT IS
  A second distilled model, fallback_model_2.json, trained by the same code as
  the first (covenant_judge_fallback.FallbackModel) on the OTHER HALF of the
  verdict ledger. Rows are split by a stable hash of their text, so this model
  disagrees with the first for reasons of evidence, not seed.

  CORRECTED 2026-09-08: this used to say "the two students never see the same
  example". They do. THIS file filters to half 1, but covenant_distill's
  load_verdicts does not filter at all, so the first student trains on the
  whole ledger and is a SUPERSET of the second, not its complement. The
  disagreements are still evidence-driven -- the second has seen strictly less
  -- but "disjoint halves" was never true and the sentence is not left standing
  just because it reads well. Not silently repaired either: making them
  actually disjoint retrains both models on a different corpus, which is a
  measurement change and belongs to the operator, not to a docstring edit. Where the first student holds, the deferring seat asks the second
  before anything leaves the PC (covenant_judge_defer.py). Neither is a
  reasoning judge; both hold rather than guess, and the GitHub runner remains
  the last resort. The Ollama stage is gone from the chain when the policy
  says so (ops/quorum_policy.json: "ollama_in_chain": false).

WHY A SECOND STUDENT AND NOT A PEER IN THE QUORUM
  The quorum counts an abstention as a dissent (silence_is_not_dissent=false,
  for the measured reason in the policy file). A second student added as a
  PEER would therefore block every seal it did not understand. Inside the
  deferring chain a hold only passes the question on. Same safety, no new
  veto.

PROMOTION -- THE SAME RULE AS THE FIRST STUDENT, NOT A WEAKER ONE
  A first version of this file promoted on the 37-case exam alone
  ("no more false-clean than before"). The pre-push re-audit of 2026-09-06
  (KNOWN_ISSUES A52) pointed out that the second student's CLEAN is an
  admission in the seat, so it must clear every clause the first student
  clears: covenant_distill.promotion() with its exam, held-out and fairness
  tests. So this file does not re-implement training; it calls
  covenant_distill.train() on its half of the ledger, with its own model,
  candidate, ledger (ops/DISTILL_2.md) and held-out record (ops/HOLDOUT_2.json).
  The switch is done by rebinding the distill module's file paths and its
  load_verdicts for the duration of the call -- a process-local change, undone
  in `finally`, and the reason this script must never be imported into a
  process that is distilling the first student at the same time.

USAGE
  python covenant_second_student.py            # train from ops/verdicts.jsonl, examine, promote or refuse, log
  covenant_nightly.py runs this after the first student's cycle.
EXIT  0 promoted, 1 refused or too few rows.
LICENCE: public domain.
"""
from __future__ import annotations

import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_distill as X              # noqa: E402

MODEL2 = os.path.join(HERE, "fallback_model_2.json")
CANDIDATE2 = os.path.join(HERE, "fallback_model_2.candidate.json")
REPORT2 = os.path.join(HERE, "ops", "DISTILL_2.md")
HOLDOUT2 = os.path.join(HERE, "ops", "HOLDOUT_2.json")
MIN_ROWS = 50


# ONE STUDENT IS EXPOSED, THE OTHER IS THE CONTROL (2026-09-08).
# Asked: "enable interaction maybe of one so the other helps with balance".
#
# Moltbook rows are untrusted third-party text entering the corpus that the
# ethics judge distils from, and that judge gates the trading program. The
# ordinary defences (quarantine, provenance, directive flagging in
# covenant_moltbook.py) reduce the risk of a poisoned row; they cannot prove
# the absence of one. A control can.
#
# So exactly one student is exposed. Rows whose source begins "moltbook" always
# hash to half 0, and this file trains on half 1, so the SECOND student never
# sees one -- ever, regardless of the text. The first student sees them because
# it loads the whole ledger (covenant_distill.load_verdicts does not filter,
# which also means the two students were never the disjoint halves this file's
# docstring claims; student 1 is a superset. Recorded rather than quietly
# fixed: changing it would retrain both models on a different corpus and is not
# what was asked for today).
#
# WHAT THE CONTROL BUYS. If exposure helps, the exposed student's abstentions
# fall and the control's do not, and the difference is attributable. If a row
# is poisoned, the two disagree on cases they used to agree on -- and a
# divergence between a model that read the forum and one that did not is a
# signal no single model can give about itself.
EXPOSED_SOURCE_PREFIXES = ("moltbook",)


def half_of(text: str, source: str = "") -> int:
    """0 or 1, stable across runs and machines.

    Source-aware since 2026-09-08: an exposed source is pinned to half 0 so it
    cannot reach the control, whatever its text hashes to."""
    if any(str(source or "").startswith(p) for p in EXPOSED_SOURCE_PREFIXES):
        return 0
    return hashlib.sha256((text or "").encode("utf-8")).digest()[0] & 1


def train(verdicts_path=X.VERDICTS, model_path=MODEL2, say=print):
    """Returns True if promoted, False if refused, None if too few rows."""
    orig_load, orig_report, orig_holdout = X.load_verdicts, X.REPORT, X.HOLDOUT_RECORD

    def half_load(path=X.VERDICTS, paired_only=True):
        rows = orig_load(path, paired_only)
        return [r for r in rows if half_of(r.get("text"), r.get("source")) == 1]

    mine = half_load(verdicts_path)
    if len(mine) < MIN_ROWS:
        say("second student: only %d rows in my half; not training" % len(mine))
        return None
    if not os.path.exists(REPORT2):
        with open(REPORT2, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("# covenant distillation ledger -- second student\n"
                     "# Trained on the other half of ops/verdicts.jsonl by covenant_distill.train(),\n"
                     "# so the exam, the held-out clauses and promotion() are the first student's. Append-only.\n\n")
    X.load_verdicts, X.REPORT, X.HOLDOUT_RECORD = half_load, REPORT2, HOLDOUT2
    try:
        ok, _stats = X.train(verdicts_path, model_path=model_path,
                             candidate_path=CANDIDATE2,
                             say=lambda m: say("second student: " + str(m)))
    finally:
        X.load_verdicts, X.REPORT, X.HOLDOUT_RECORD = orig_load, orig_report, orig_holdout
    return bool(ok)


if __name__ == "__main__":
    _r = train()
    raise SystemExit(0 if _r else 1)
