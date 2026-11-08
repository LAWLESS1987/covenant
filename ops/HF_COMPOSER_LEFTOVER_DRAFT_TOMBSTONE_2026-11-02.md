# Tombstone: leftover HF composer draft (reply #20, pre-send version)

Captured 2026-11-02 from his Edge (Lawless1987) composer on thread 183807, before
clearing it to post reply #22. Rule 10 — nothing deleted; the text is preserved here
exactly as it stood in the composer.

**Provenance:** an earlier draft of our reply **#20** (addressed to post 18 in the
composer header). It is PRE-gist ("available on request", not the gist link) and
PRE-spec.en.md ("the Korean-language spec was not read"). Reply #20 was already POSTED
(Jang-woo's #21 answers it), so this composer text is a superseded leftover, doubly
replaced by the sent #20 and by the pending #22. Clearing it loses nothing of record.

**I did not author this draft this turn** — it was sitting unsent in his composer.
Kept verbatim in case he wants any of its wording back.

---

On the split: agreed. The gate can't supply what it isn't handed — the provider or
adopting system has to declare that a tool moving someone else's value needs an owner
condition (and, for it to bite, that condition has to be mandatory, configured, and
evaluated against an authoritative source; an omitted one still leaks). Whether the
record it reads is genuine has to be independently verified, not taken on the claimant's
word. And the model's part has a line: it may propose or extract the execution data, but
must not create the authority that validates it. In our cases a wording-reader kept
leaking as the phrasing changed, while a declared condition — mandatory, configured, and
read from an authoritative source — held independently of wording; we have not tested
that under revoked or altered authorizations.

One correction to myself: we do already bind an approval to the whole plan's hash, so an
approval that names a different hash is refused; what we don't have is a check at
execution that each action matches its line in the approved plan. That per-value binding
is still open on both sides.

The case file — the 34 cases in your input shape, our Python port of your two gates with
your commit and line numbers cited, and the runner — is available on request; its header
states the limits (the runner assumes upstream extraction succeeded, and the
Korean-language spec was not read).
