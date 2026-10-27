# Independent implementations of `covenant-conformance-v1`

Two implementations of the two operations in `docs/CONFORMANCE_SPEC.json`, written on
2026-09-03 from that file alone, sharing no code with this repository:

| file | language | written by | vectors | root |
|---|---|---|---|---|
| `conformance_ps.ps1` | Windows PowerShell 5.1, .NET SHA256 | an AI agent (Claude) under clean-room rules | 23 / 23 match | `0c398099…0f0ddcef`, equal to the published root |
| `conformance_py.py` | Python 3.12, standard library only | a second AI agent, separately, same rules | 23 / 23 match | equal to the published root |

The outputs of the first runs are kept beside them (`*_output_2026-09-03.txt`).
`test_n2_independent_root.py` reruns both against the current spec on every sweep.
*CONF-BOTH-2026-10-15, proposed tombstone; read and run 2026-10-15 at eeb2f18:
both, on a Windows sweep -- N2 13/13 that day, with N2.7-9 the PowerShell build.
The suite runs that build only on win32 with `powershell` on the path, and has
since it was written as `test_c3_independent_root.py` (ad1d4ee). The CI sweep,
`covenant_one.py --ci`, runs on ubuntu-latest, so by that check N2 skips
N2.7-9 there and reruns the Python build alone. (Read from the workflow and the
suite; no CI log was read.)*

> **Read as an experiment.** *Added 2026-10-03 for clarity, at the operator's
> request ("reflect the scientific method while leaving the substance"). A map
> onto this page; nothing else on it was changed.*
>
> - **Question.** Can implementations that share no code compute the two
>   operations of the specification identically, vector by vector?
> - **Method.** Clean-room builds from the specification file alone, audited by
>   a third party for isolation ([What "independent" means here,
>   exactly](#what-independent-means-here-exactly)).
> - **Evidence.** Per-vector agreement on all 23 vectors, re-run on every sweep.
>   *2026-10-15: both builds on a Windows sweep, the Python build alone on the
>   CI sweep (CONF-BOTH-2026-10-15, above).*
> - **What was refuted.** Agreement on the published root is not evidence of
>   independent computation: the root hashes outputs printed in the
>   specification itself (retraction A121, `docs/RETRACTED.json`). The
>   per-vector comparison is the evidence; the root is not.
> - **Known limits.** The implementers were AI agents, not people unfamiliar
>   with the project, and the vectors pin the operations only where they sample.
> - **Reproduce.** `python test_n2_independent_root.py`.

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

Both implementers matched all 23 vectors per vector — which is the evidence; the root
match beside it is not, since the root hashes the expecteds printed in the spec (A121).
Both listed what they had to assume because
no vector decides it. These are open points of the spec, kept here rather than fixed
silently; adding vectors would change the root, which is an amendment, not a patch.

1. "sha256 over spec" means the UTF-8 bytes of the top-level `spec` string
   (`covenant-conformance-v1`), not the file. Both read it so; the root match confirms
   it; the note should say it.
2. Name lists (`answered`, `silent`, `outliers`, `silent_diverged`, `silent_unproven`)
   are emitted in code-point sorted order. Every vector's input is already sorted, so
   sorted order and input order are indistinguishable from the vectors alone.
   *CONF-SORTED-2026-10-15, proposed tombstone; measured 2026-10-15 over all 54
   levels of the 23 vectors, which are unchanged since 590cf4f (2026-08-31): two
   climb levels are not sorted (`S.silence.two-kinds`: dv, un, k3, k4, k5;
   `S.unproven.speaks-silence`: u, k2, k3). The conclusion holds: each of those
   levels emits lists of at most one name, and the Python build changed to emit
   every list in input order still matches 23 of 23 vectors (reverse-sorted, it
   matches 10).*
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
   *CONF-SIZES-2026-10-15, proposed tombstone; measured the same way: the 54
   levels have 2 witnesses (1 level, `S.compose.height-invariant`), 3 (45), 4 (2:
   `S.divergences.two-outliers-one-level`, `T.diverged.plurality-without-majority`)
   and 5 (6). What is true is narrower: only three-witness levels (7) and
   five-witness levels (5) have a silent witness, the case the default quorum
   decides; at two and four every witness answers. With the default quorum set
   to 1, or to all asked, at every size but 3 and 5, the Python build still
   matches 23 of 23; set to 2 at five witnesses it matches 21, set to 1 at three
   it matches 20.*
7. Reference letters are expanded through the spec's top-level `roots` table; a letter
   absent from it would pass through unchanged. Never exercised.
8. A leaf without a `root` is silent; a `quorum` field on a climb level would be
   honoured. Neither appears in any vector.
9. Duplicate child names within one level never occur and are not handled.
10. Canonical JSON: keys sorted, no spaces, ASCII escaping; every value in the vectors is
    ASCII, so the escaping choice cannot change the result here but would for
    non-ASCII names.
