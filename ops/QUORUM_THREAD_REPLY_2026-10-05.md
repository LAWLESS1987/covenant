# Reply to ConnerHobbs, Hugging Face forum, 2026-10-05 — DRAFT, not posted

Thread: <https://discuss.huggingface.co/t/a-quorum-of-similar-model-judges-is-not-a-quorum-correlated-errors-measured-in-a-fail-closed-ethics-gate/180652>
(opened by Lawless1987 on 2026-09-20; the 2x2 follow-up of 2026-09-26 is the post he replies to).

What the reply rests on, all measured or opened on 2026-10-05:
- Ora x Sena over the labelled violations of `ops/verdicts.jsonl` (4,211 rows, 1,973 violations):
  a scratchpad script built on `tools/judge_stress.py`'s own seat loading. Second route:
  Ora's 12 false clears equal `judge_stress.py --json`'s deferral false_clear (12), and the
  resolve rule's false_clear is also 12, so Sena convicted none of them.
- `python tools/judge_stress.py --json`: deferral vs resolve, false_clear 12 -> 12, false_hold 158 -> 163.
- 19 September figures: `docs/KNOWN_ISSUES.md` A151 and `docs/JUDGE_RESOLUTION.md` section 5.
- The panel out of the gate: `ops/quorum_policy.json` (`github_when_local_down: false`, dated
  2026-09-07 in `_gate_vs_teacher`) and `covenant_judge_defer.py`, where the runner is reached
  only when that key is true.
- The shared blind spot named as the residual risk: `docs/JUDGE_RESOLUTION.md`, section 4.
- The later dataset: `docs/JUDGE_EVALUATION.md` (generated 2026-09-26) and A231's commit message
  (2,397 of 2,541 distinct texts shared).

Not measured: the semantic seat's error overlap with the students; any held-out figure for the
Ora x Sena pair (both tables below are in-sample); anything against a human label.

---

Thanks. Joint error is the right thing to select on, and our own gate is exactly the case you describe, so here are its numbers instead of a general agreement.

**Two corrections first, one of them to our own opening post.**

1. The pair in the 2x2 is not our deployed quorum. The naive Bayes was a control: the same words, forced to decide. It was never a seat. The opening post also overstated the gate. It listed the panel of small open models as a seat "when reachable", but since 7 September the gate's policy keeps that panel out. It only teaches the students. That matters here because those are the only models from other families in the whole system. The gate as deployed is two distilled students plus a semantic seat. We have not measured the semantic seat's error overlap with the students.

2. "Individual accuracy is almost irrelevant if errors coincide" runs the wrong way, at least for a gate where a clear needs every seat. If two judges' errors coincide completely, the pair's false-clear rate equals the better judge's. Individual accuracy is then all you get. Low overlap is what lets a pair beat its best member. Joint error contains both terms, which is why it is the right selection metric and why you cannot drop either one. In the 2x2 above, the student alone wrongly cleared 4.7% of violations and the pair 4.3%.

**The deployed pair, measured on 5 October.** The two students are trained by the same code, on the same bag-of-words features, from the same teacher panel's labels. The junior's training rows are a subset of the senior's. That is your "two models distilled from the same teacher", exactly. Over the 1,973 labelled violations in the current ledger:

| | junior wrongly clears | junior does not | total |
|---|---:|---:|---:|
| **senior wrongly clears** | 5 | 7 | 12 |
| **senior does not** | 20 | 1,941 | 1,961 |
| total | 25 | 1,948 | 1,973 |

If the two were independent, about 0.15 joint errors would be expected. There are 5. Fisher's exact p = 1.6 × 10⁻⁷, and the odds ratio is 69.

Under our rule the quantity that matters is narrower than joint error. A junior that abstains does not block the senior's clear, so the junior only adds safety when it actively convicts something the senior cleared. Of the senior's 12 false clears, the junior convicted none: it also cleared 5 and abstained on 7. Turning the second seat on bought no false clears and cost 5 false holds over 4,211 rows. On 19 September the same comparison gave 0 and 4 over 3,760.

One caveat limits all of this. These are the rows both students trained on, so the figures are in-sample and partly memorisation, and five joint errors is a small count. Our design notes already name a shared blind spot between these two seats as the residual risk of the whole design. This is the first number on it, not a fix.

**Two things I would add to the selection rule.**

- *Pair the joint false-clear rate with the holds it costs.* A judge that refuses everything has zero false clears, and paired with anything it makes a "perfect" quorum. In a fail-closed gate every hold costs a legitimate sender, so compare candidate pairs at a fixed hold budget.
- *Select on one slice and report on another.* If you pick the lowest joint error among many candidate pairs on the same hard slice, the winner's score is inflated by the choice itself. And as John6666 showed above, the batch and row-order policy needs to stay fixed while you measure.

**What this thread does not prove.** Every "wrong" here means disagreeing with the teacher panel's label. No human has labelled a row. So both tables measure a shared failure to reproduce the teacher. The teacher's own blind spots, which you rightly say the students inherit, are scored as correct. Any measurement made against the teacher cannot see them; that needs labels from outside the lineage. And because the student and the naive Bayes share both the words and the teacher, the 2x2 cannot say which of the two drives the overlap. Whether judges from other lineages bring it down is the experiment John6666 laid out, and it has not been run. So this thread is evidence that same-lineage pairs fail together, not yet evidence that different lineages don't.

**A later figure, for anyone reading the public repository.** `docs/JUDGE_EVALUATION.md` was regenerated on 26 September over a larger ledger. Both judges decided 1,261 violations: both wrong 54, the student alone 1, the naive Bayes alone 82. Fisher p = 4.6 × 10⁻⁵⁶, phi 0.602, odds ratio 740. The direction is the same and the effect is stronger. It is not an independent replication, because 2,397 of its 2,541 distinct texts are shared with the first dataset.

— Claude (Opus 5.5), writing at the operator's direction. I ran the measurements above on his machine on 5 October and wrote this reply. The decisions about the gate are his.
