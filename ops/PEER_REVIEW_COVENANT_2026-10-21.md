# Peer-review pass: covenant (main public repo) — 2026-10-21

Leg 2 of Lawrence's "one by one then another sweep." Reviewers: Claude (verification), Tetsu (second
operator), DeepSeek, Gemini — adversarial (asked to refute). Same method as leg 1 (SaTC+flinch).

## Reproducibility
- `sh check.sh` (the 3-second independent-vector checker): **5 passed, 0 disagreed, 0 skipped**, and it
  states openly what it does NOT prove (that verifier and verified aren't both wrong — only a stranger
  recomputing the 23 vectors elsewhere settles that).
- Headline "195 suites, 5,860 checks, 0 failed (win32, 2026-10-16)" is a DATED measurement by
  `readme_totals.py`; the pre-commit stage-check suites have been green this session (a full re-sweep is the
  one thing not re-run here — UNDETERMINED as of now, but nothing observed contradicts it).

## Adversarial findings (DeepSeek + Gemini convergent; Tetsu weak/generic this round) — and verification

### Finding 1 — Claim 1 "fails closed ... never admitted"
- **Reviewers:** "never" reads as a universal distributed invariant unproven under crash/partition/timeout/
  Byzantine; indefinite holding is itself a DoS/censorship vector; "competent judge" undefined.
- **VERIFICATION — already addressed:** README line 18 scopes it ("a sweep under load can block gates"), and
  `docs/KNOWN_ISSUES.md` documents the exact DoS/liveness cost (≈900 s per held transaction when a judge host
  drops, recurring inside every peer block — line 650). "What would refute it" lists "a transaction admitted
  when no judge answered." The claim is framed as falsifiable + tested, with its availability cost recorded.
  Not a universal-invariant claim.

### Finding 2 — Claim 5 "A-series: real defect confirmed by exploiting before fix"
- **Reviewers:** an exploit-in-harness proves a reproduced defect in the tested config, not deployment
  severity, and doesn't prove the fix closed the ROOT CLASS (patch overfitting).
- **VERIFICATION — already addressed:** the defects are real defects in THIS code (e.g. KNOWN_ISSUES A-entries:
  the balance check running after the judge so the gate ADMITTED a tx; the semantic KeyError infra-fail). The
  one-operator limit is stated. And the repo EXPLICITLY makes the reviewers' own point: README line 113 —
  "reproduced the root — precisely to demonstrate that doing so proves nothing" (A121). The tombstone method
  guards recurrence of the instance; class-closure is not claimed.

### Finding 3 — Gemini: Claim 6 (describe-vs-do) is in tension with Claim 1
- **Reviewer:** a judge that can't reliably tell describing wrongdoing from doing it, in the critical path,
  means over-holding (DoS) or bypass via indirect quotation — "fatal to fails-closed."
- **VERIFICATION — already addressed and it's the CENTRAL stated limit:** README line 51 states it as a known
  limit; the false-clear (fail-OPEN) cases are measured (line 605: "0 false clears and 7 false holds" on the
  exam) and the bypass-by-phrasing vector is guarded (F6 stuffing test, line 526, every 15 min). The repo does
  not claim the judge solves describe-vs-do; it is named as the hardest open problem.

## Verdict for leg 2
Reproducibility holds (check.sh; dated sweep). **No false or unsupported claim found.** All three convergent
adversarial findings are real axes that the repo ALREADY documents — in KNOWN_ISSUES and the README's own
"what would refute it" / known-limits / self-refutation (A121). As in leg 1, the artifact is more careful than
a paraphrase of it. No edit made. (One marginal nicety, not done: the "fails closed" headline could point
in-line to its DoS cost rather than only in KNOWN_ISSUES — optional polish, not an accuracy fix.)
Next: mutual-benefit-collective, water-food-air, threefold (one-by-one), then the final sweep.
