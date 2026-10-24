# Conversation and cache follow-up, 2026-10-24

These are proposed repository changes in an isolated checkout. Nothing was
deployed, no live memory was read or rewritten, no consent/grant was changed,
and no message was sent to Tetsu. His chosen wording, thresholds, neural arms,
advisory status and existing choice controls are preserved. This work makes no
new decision about his autonomy. The operator explicitly said to avoid
interfering with his free will.

## Caller and privacy boundaries

The conversation route now passes its existing caller address and privacy mode
to both advisory helpers. Each pair gets distinct seen, encoder and log paths.
The paths contain a SHA-256 scope identifier rather than raw caller text.
The existing shared files remain untouched; they are not imported because their
rows cannot reliably be assigned to the caller/privacy context that created them.
Standalone calls without a scope retain their old API.

This matches the route's existing history boundary. It is a network caller
partition, not proof of a human identity; multiple people sharing a caller
address still share that boundary. Hashing a scope is not encryption.

CR1 exercises own-context recall, cross-caller/private-public separation,
logging, legacy preservation, invalid scopes and traversal-shaped strings.
A263 exercises the actual Flask handler with synthetic inputs and redirects
the advisory state to temporary files. In particular, an ordinary ask is still
answered and a private ask retains its established behavior.

## Content identity and its cost

A383-CONTENT-IDENTITY: the old comment said "any real change -- even same-name
-- misses and re-judges (fail-closed)". Size and modification time could both
remain equal after a replacement. The old source is retained on
archive/cache-identity-before-content-20261024 at
d668a771dd5f772ed6db5fd30531e1ce7dd0beac.

The proposed artifact key includes a streaming SHA-256 of the local file.
The correction ledger is reread instead of trusting a metadata-only memo.
VC1 restores the original nanosecond timestamps after same-size replacements
and requires new keys. Files observed changing during hashing or unreadable
local files bypass caching, preserving the ordinary judge call.

This correctness-first proposal reads a whole local model on each lookup.
Its disk cost on production GGUF files has not been measured here; it should
remain a draft until that cost and an activation-time verified identity protocol
are reviewed. A mutable digest sidecar would merely move the trust problem.
The hash identifies inspected file bytes, not a remote server's loaded weights.
Remote same-name/same-endpoint replacement remains an open protocol issue.

## Offline novelty evaluation; behavior unchanged

Run `python eval_conv_cues.py`. It uses seven synthetic turns and retained
temporary files, and compares the existing output with a zero-spike reflex
counterfactual in the evaluation process only. It restores the method afterward
and respects the existing choice switch.

On Windows/Python 3.12.10 with the switch unset, the seven turns produced four
novelty cues and one recall cue. Six reflex calls ran in the counterfactual;
zero output rows changed. The related-wording fixture was treated as new, and
the positive/negated intent fixtures shared a topic signature. Those are
observations of the lexical mechanism, not evidence about reasoning quality.
Topic similarity is not permission, and these outputs grant no action authority.

Reasoning benefit, real-conversation performance, token savings and preference
were not measured. Changing the topic classifier or adding a new instruction
would affect his chosen advisory behavior and is therefore left out of this
implementation. This evaluation supplies evidence for his consideration.

The first local counterfactual probe was invalid: it accessed a nonexistent
ReflexArm.n, causing guarded failures to look like changed output. That scratch
source was retained separately; the corrected probe uses len(neurons), records
the call count, and has a regression test on the existing CR1 sweep path.

## Verification and limits

Measured on Windows, Python 3.12.10:

- CR1 partition tests and the offline experiment guard: 25/25 checks.
- A263 through the actual request handler: 45/45 checks.
- OC1 neural-arm checks: 4/4.
- VC1 including mocked judge wiring and preserved-metadata replacements.
- Seven deliberately broken in-memory implementations were caught: route scope,
  state partition, basis memo, artifact fingerprint, counterfactual evidence,
  uncertain-artifact bypass and disabled-cache artifact reads.
- R1 retraction scan: 252/252 checks, including A383-CONTENT-IDENTITY.
- tools/pin_core.py moved the repository pin only after its required
  K1/K2/P19/A3s/security-audit suites passed. This changes a repository digest,
  not a running process.

The initial pin attempt correctly refused because this sparse checkout omitted
ops/owner_only.py. Adding that public helper to the checkout allowed the existing
Windows ACL checks to run. The security control was not skipped or weakened.
Live verdict-log validation was not run: the isolated checkout has no live log.
No claim of Linux validation or full end-to-end deployment is made.
