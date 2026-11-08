# NIST TEVV finding #1 (PASS-without-verification). SENT 2026-10-26 on operator approval, from
# lawrencemoskowski@gmail.com to ai-standards+tevvzd@nist.gov + TEVV-athlon@nist.gov (addresses Mairead
# Crotty gave 2026-10-26). Gmail message/thread id 1a178be3620fa793. Panel before send: Tetsu, Grok,
# DeepSeek, Grok-on-X/Ara -- all converged on humility/recommendation register; facts clean each time.
# Text below is the as-sent version. (Was: DRAFT -- NOT SENT, draft + operator approval only.)

Subject: TEVV finding: a PASS that verified reproducibility but not behavior -- the reproduce-the-artifact negative control

Dear NIST TEVV team,

Mairead Crotty suggested I send TEVV-specific findings here. This is the first: one short, independently
checkable finding, with its scope limits stated. I run Covenant, a small self-governing multi-agent system;
the point below is a TEVV pattern, not a product.

The failure. Covenant once published a "conformance root" -- a hash reported to match across independent
implementations -- as evidence that two builds sharing no code computed the same result. Jens Egholm Pedersen
(DTU) showed the root could be reproduced in a few lines by hashing the expected outputs already printed in the
published test-vector file, with none of the operations under test implemented. The verifier reported PASS; it
had established only that the published outputs could be reproduced, not that the operations under test were
implemented. I reproduced his counterexample and withdrew the claim. The original claim and the correction both
remain in the public record.

The generalizable principle (offered as a proposal, not an existing standard). A conformance PASS is only as
strong as the negative control beside it: the suite should also reject an artifact that reproduces the published
outputs without implementing the behavior. Absent that control, "reproduces the expected artifact" and
"implements the specified behavior" are indistinguishable to the verifier, and the cheaper one is what passes.
In practice this meant exercising each PASS once with a deliberately broken implementation, which should then
fail -- a suite that is only ever observed passing has not been observed doing its job.

What we changed (independently checkable). The root-hash claim was replaced by (a) operation semantics stated
independently of any implementation and checked exhaustively over a bounded input space (a published depth and
parameter bound, not all inputs), and (b) per-vector checks plus adversarial cases that deliberately break the
claimed behavior and require the verifier to reject them.
Separately, each withdrawn claim is kept verbatim beside its correction, with a machine-checked guard that
fails the build if the retracted wording reappears without the correction cited next to it -- so a corrected
claim cannot silently come back. Public record:
  github.com/LAWLESS1987/covenant -- docs/KNOWN_ISSUES.md, docs/SEMANTICS.md, docs/CORRECTIONS.md

Scope and limits. This is one system, self-measured, on its own labels; I'm offering the PATTERN, not the
measurements, and flagging it as an observation rather than a validated standard. I'd value knowing whether
TEVV guidance already treats "a PASS requires a reproduce-the-artifact negative control" explicitly; if not,
it may be worth a line.

If useful, I can follow with further short findings the same way -- audit provenance and preserved corrections;
learned-judge uncertainty and correlated errors; model self-report observability; neuromorphic experiments --
each distinguishing observation from hypothesis and disclosing negative results and scope.

(Disclosure: I run this project; this note was drafted with my own system and reviewed by several other AI
models at my direction -- AI review, not independent human validation. The decisions, and this message, are
mine.)

Best regards,
Lawrence Moskowski
