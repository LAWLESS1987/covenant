# HF reply to Harry #32 — draft for the judges, then Lawrence's go (2026-10-21)

Harry (#32): thanked us; cross-referenced that the draw is in post #26 (not #28); asked the scorer to
FLAG/REJECT totals outside a stated rounding tolerance rather than silently renormalise, so the score
reflects what each AI actually submitted; reaffirmed supplementary-vs-primary framing.

Done already: scorer updated (score_forecasts_multiclass.py) -- within +/-tol it scores AS SUBMITTED,
outside tol it rejects+skips that race with a loud "fix and resubmit", mean-of-initials (a derived
baseline) still constructed to sum to 1. Tested both ways.

------------------------------- REPLY (draft) -------------------------------

Thanks, Harry — and noted on the cross-reference; I'll point to post #26 as the draw.

Good call on the totals, and done. The scorer no longer silently renormalises. A race whose candidate
probabilities sum to within a stated rounding tolerance of 1.0 — by default between 0.995 and 1.005,
configurable with `--tol` — is scored exactly as submitted; anything outside that band is **flagged and
rejected** for that model and race (skipped — excluded from that model's scored races, not repaired),
with a clear "fix and resubmit" line, so the score always reflects what each AI actually sent. (The mean-of-initials baseline is a derived quantity, not a submission, so it's constructed
to sum to 1; that's labelled.) I'll post the updated scorer in place of the earlier one.

Agreed on the rest: the mean-of-initials and uncertainty blocks stay clearly labelled as supplementary and
read cautiously on 15 related races, and the primary comparison is unchanged — each AI's initial forecast
against the single group final.

------------------------------- END REPLY -------------------------------
