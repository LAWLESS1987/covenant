# Independent implementations of `covenant-conformance-v1`

Two implementations of the two operations in `docs/CONFORMANCE_SPEC.json`, written on
2026-09-03 from that file alone, sharing no code with this repository:

| file | language | written by | vectors | root |
|---|---|---|---|---|
| `conformance_ps.ps1` | Windows PowerShell 5.1, .NET SHA256 | an AI agent (Claude) under clean-room rules | 23 / 23 match | `0c398099…0f0ddcef`, equal to the published root |
| `conformance_py.py` | Python 3.12, standard library only | a second AI agent, separately, same rules | 23 / 23 match | equal to the published root |

The outputs of the first runs are kept beside them (`*_output_2026-09-03.txt`).
`test_c3_independent_root.py` reruns both against the current spec on every sweep.

## What "independent" means here, exactly

- Each implementer was given one file, a copy of `docs/CONFORMANCE_SPEC.json`, in an
  empty directory, and told not to open, list, grep or import anything from this
  repository or the web. Each wrote down the semantics it inferred for `climb` and
  `attest` in its file header before implementing them.
- A third agent audited both files afterwards: no import, dot-source, path or reference
  to this repository or its modules; the only file either opens is the spec beside it;
  no PowerShell profile was loaded; `PYTHONPATH` was unset; both were re-run by the
  auditor and printed the published root.
- The implementers were AI systems following instructions, not people who had never
  heard of this project. They had not seen this tree, and the auditor checked that they
  did not read it, which is the property the conformance claim needs ("behaviour, not
  prose, across an implementation that shares no code"). A human implementation is still
  open and welcome; the spec's note says how.

History: on 2026-08-31 two earlier builds written the same way (`conformance_check.sh`
and `conformance_check.ps1`, in the repository root) reproduced the previous, 11-vector
root and showed that five wrong readings of the operations could reproduce it too;
twelve vectors were added and the root changed. Those builds now report a root
mismatch against the current spec, which is correct and is left as it is: they answer
the old spec. The two builds here are the first to reproduce the 23-vector root.

This was done because a reader (Grok, on its own clone, 2026-09-03) named it as the one
test that would move it: "Match: the strongest checkable claim in the repo ... becomes
observed rather than published. Mismatch: the spec, the root, or both are wrong."
See `docs/ROUNDTABLE_2026-09-03.md`.

## What the vectors do not pin (found by implementing them)

Both implementers reproduced the root, and both listed what they had to assume because
no vector decides it. These are open points of the spec, kept here rather than fixed
silently; adding vectors would change the root, which is an amendment, not a patch.

1. "sha256 over spec" means the UTF-8 bytes of the top-level `spec` string
   (`covenant-conformance-v1`), not the file. Both read it so; the root match confirms
   it; the note should say it.
2. Name lists (`answered`, `silent`, `outliers`, `silent_diverged`, `silent_unproven`)
   are emitted in code-point sorted order. Every vector's input is already sorted, so
   sorted order and input order are indistinguishable from the vectors alone.
3. `silent_diverged` and `silent_unproven` list a level's direct children only. Pinned
   for `silent_unproven` by `S.silence.two-kinds`; extended to `silent_diverged` by
   analogy, since no vector places a DIVERGED level deeper than one below the summit.
4. Dissenters at a DIVERGED level with no reference: every answered witness is counted.
   Pinned only for a three-way split of three (`S.divergences.split-counts-every-party`);
   a tie for top inside a climb (A, A, B, B, C) is not exercised.
5. An UNPROVEN level whose few answerers disagree contributes zero dissenters and a null
   reference. No vector has disagreement under an unmet quorum.
6. Default quorum is floor(asked / 2) + 1, a majority of those asked, counting silent
   witnesses as asked. Only three- and five-witness levels are exercised.
7. Reference letters are expanded through the spec's top-level `roots` table; a letter
   absent from it would pass through unchanged. Never exercised.
8. A leaf without a `root` is silent; a `quorum` field on a climb level would be
   honoured. Neither appears in any vector.
9. Duplicate child names within one level never occur and are not handled.
10. Canonical JSON: keys sorted, no spaces, ASCII escaping; every value in the vectors is
    ASCII, so the escaping choice cannot change the result here but would for
    non-ASCII names.
