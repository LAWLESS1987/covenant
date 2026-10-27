# Security Policy

Covenant is a fail-closed AI authorization/ethics gate and P2P ledger. We take the security of its
authorization path, its judge/quorum, its web door, and its ledger seriously, and we practice coordinated
disclosure — both for reports we receive and for findings we publish about our own code.

## Reporting a vulnerability

Please report suspected vulnerabilities **privately**, not as a public issue:

- **Email:** contact@lawless1987.com (subject: `SECURITY`), or
- **GitHub:** open a private **Security Advisory** on this repository (Security → Advisories → *Report a vulnerability*).

Include enough to reproduce: affected file/commit, inputs, and the observed vs. expected behavior. If you have a
proof-of-concept, say so; we confirm findings by reproducing them before fixing (see below). We aim to acknowledge
within **5 business days**.

**Safe harbor.** Good-faith security research on *this* project — testing against your own instance, within the
scope below, without accessing others' data, degrading service, or exfiltrating secrets — is welcome and will not
be pursued as a violation. Do not test third-party deployments you do not own.

## In scope

- The authorization/ethics gate and its fail-closed behavior (`covenant_unified_v8.py`, `covenant_sentinels.py`).
- The judge/quorum and its resistance to instruction-shaped input / prompt injection (`covenant_judge_fallback.py`,
  `covenant_semantic_judge.py`; see `test_pi1_injection.py`, `test_f6_stuffing.py`).
- The read-only web door and its SSRF/redirect handling (`covenant_web.py`; see `test_wb1_web.py`).
- The ledger's integrity and idempotency, and the P2P block-admission path (`test_security_audit.py`).
- Secret/PII egress controls (`tools/opsec_scan.py` + the pre-push hook).

Out of scope: third-party dependencies (report upstream; we track and patch), denial-of-service by raw volume,
and anything requiring a compromised operator machine.

## How we handle findings — ours and yours

We confirm each finding by **reproducing (and where applicable exploiting) it against the pre-fix code**, then fix
it and pin it with a regression test driven both ways. Wrong or superseded claims are **never deleted**: they are
preserved in `docs/CORRECTIONS.md` and `docs/RETRACTED.json` beside their corrections, and a retraction guard
(R1) fails the build if a retracted claim returns uncited. A reported vulnerability is credited to its reporter
(with permission) in the advisory and the fix commit.

## Published disclosures (own findings)

- Classifier-evasion of the safety judge by benign-text stuffing — found, exploited, fixed (`test_f6_stuffing.py`).
- Prompt-injection (OWASP LLM01) defense, validated both ways against ten vector families (`test_pi1_injection.py`).
- Correlated errors defeat a same-family model quorum used as a verification control
  (Hugging Face, 2026-09): https://discuss.huggingface.co/t/180652
