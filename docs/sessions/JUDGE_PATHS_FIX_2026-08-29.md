# Judge paths: one fix, two refutations, and a gap the fix opened

**2026-08-29.** Target: `pending-v8.38/covenant_unified_v8.py` (the candidate).
**The deployed core `covenant_unified_v8.py` (v8.37) was not touched.**

## What was asked, and what was actually true

`tools/judge_paths.py` walked the registry on 2026-08-27 and I filed three
claims. I then proposed three fixes. Measuring them one at a time before
editing anything is the only reason this document is not three fixes long.

| # | Claim as filed | Verdict on measurement |
|---|---|---|
| J1a | `JudgeProviderRegistry.register()` overwrites a live name in silence | **TRUE.** In both v8.37 and the v8.38 candidate. Fixed. |
| J1b | the `semantic` provider is not registered by default | **TRUE OF THE DEPLOYED NODE ONLY.** The v8.38 candidate already registers it at import (`covenant_unified_v8.py`, the `install()` block). It also fails soft on absence and loud on a corrupt model. Nothing to write. |
| J1c | `quorum_diversity_report` keys on implementation, not model | **FALSE.** It has computed `signatures = {(impl, credential_env, model)}` since v8.34, and `_judge_facts` has carried `"model"` just as long. |
| J1d | *(not filed — found while checking J1c)* | **TRUE, and worse than J1c.** See below. |

### How J1b and J1c were wrong

**J1b** — the audit tool imported `covenant_unified_v8` from the repo root,
which is the *deployed* v8.37. The repo root has neither
`covenant_semantic_judge.py` nor `semantic_judge_model.json`, so `semantic`
could not have registered there under any version. I measured a deployment and
reported a design.

**J1c** — I grepped for `.model` and found zero occurrences, then reported that
the report does not consider the model. The code says `f["model"]` and
`getattr(j, "model", None)`. I counted a *syntax* and reported a *semantics*.
This is M30 read backwards: a claim satisfied by missing evidence is not a
claim.

Both were caught by measuring the specific thing before editing. Neither would
have been caught by review, because in both cases the prose I had written
already agreed with me.

## J1d — the real defect, and the better version of J1c

`_judge_facts` read the model as:

```python
"model": str(getattr(j, "model", None) or "<provider default>")[:64],
```

`j.model` is the **explicit constructor override**, and it is `None` in every
configuration this repo ships. `OllamaJudge` keeps its per-instance model in
`_model_override`, set by the `judges.json` factory, whose own comment says
those overrides exist so "several judges can coexist in one process pointing at
different endpoints and different models". `OpenAICompatJudge` resolves
`model -> COVENANT_LOCAL_JUDGE_MODEL -> default_model` inside `_model()`.

So the mechanism built to **create** model diversity was invisible to the meter
built to **measure** it.

Measured live against this machine's real `judges.json`
(`pc_qwen` qwen3:8b, `pc_mid` qwen3:4b, `pc_small` qwen3:1.7b):

```
BEFORE (v8.37, deployed)
  configured   : ['qwen3:8b', 'qwen3:4b', 'qwen3:1.7b']
  facts[model] : ['<provider default>', '<provider default>', '<provider default>']
  independent_semantic_judges : 1
  WARN: ethics quorum is not independently diverse: 1 independent semantic
        judge(s) of 3 configured ...
```

`judges.json` states in `_why_a_size_ladder` that "the models differ -- which is
real reasoning diversity, not the label diversity QuorumJudge warns about." The
node was printing the opposite of that at every boot. Under M34 a permanent
warning that is false is how an operator learns to skim the true ones.

## What was changed

All three edits are in `pending-v8.38/covenant_unified_v8.py`.
9,994 lines -> 10,135 lines. `CORE_SOURCE_SHA256` `d3a0ca17030a` -> `970b4d28b858`.

**1. `JudgeProviderRegistry`: a shadow ledger, not a refusal.**
`register(name, factory, replace=False)` now records every overwrite in
`_shadowed` and announces it on **stderr** with `file:line` on both sides.
`shadowed_providers()` returns a copy. Re-registering the *same factory object*
(a module imported twice) is neither recorded nor announced. `replace=True` is
recorded but silent.

Why warn rather than refuse: two shipped modules both claim `local`
(`covenant_judge_local.py:207`, `covenant_judge_ollama.py:449`). Refusing the
second would end the silence by breaking a working configuration at import time
on a running node. That is the trade `LinkConductance` already settled —
*conductance orders delivery; it never gates it.* Disclose, do not gate. stderr
and not stdout for the reason the semantic-judge banner learned by breaking
`test_b1`: stdout is a data channel for anything that parses it.

Live output now:

```
WARNING: judge provider 'local' was already registered by
covenant_judge_local.py:207 and is being REPLACED by
covenant_judge_ollama.py:449. Import order now decides which implementation
judges your chain. Pass replace=True if that is deliberate.

shadowed_providers() -> [{'name': 'local', 'was': 'covenant_judge_local.py:207',
                          'now': 'covenant_judge_ollama.py:449',
                          'deliberate': 'no'}]
```

**2. `_judge_facts` reads the model the judge will actually send.**
Precedence: guarded `_model()` -> `_model_override` -> `model` ->
`default_model` -> `<provider default>`. A new `model_source` field says which
path produced the answer, including `resolver_raised` when `_model()` throws —
"the meter could not read" and "the judge has no model" are different claims and
only one of them is safe to render as a default.

It calls `_model()` rather than rebuilding its precedence because that
precedence lives in the judge class and can change there; a second copy here
would be a meter that silently drifts from the thing it meters, which is
P18/M52 in miniature.

**3. `quorum_diversity_warnings`: a gap fix 2 opened, closed in the same change.**
Raising the count from 1 to 3 *silences* the old sentence — while
`duplicate_implementation` and `shared_credential` remain true, remain in
`degradations`, and remain enough to hold `diverse` at `False`. Trading a false
warning for silence about a true one is not an improvement; it is M30 wearing a
fix's clothes. Independence of **opinion** and independence of **failure** are
different properties and only the first one went up.

```
AFTER (v8.38 candidate)
  facts[model] : ['qwen3:8b', 'qwen3:4b', 'qwen3:1.7b']
  model_source : ['resolver', 'resolver', 'resolver']
  independent_semantic_judges : 3
  diverse      : False        <- unchanged, and correct
  WARN: ethics quorum: 3 independent semantic judges, but they share a failure
        (duplicate_implementation:OllamaJudge,
         shared_credential:COVENANT_LOCAL_JUDGE_KEY) -- one parser bug or one
        missing credential takes all of them at once (B2)
```

## The test

`test_j1_judge_paths.py`, 34 checks, in `test_b2`'s idiom: it runs against the
old file and the new one and reports what each did (M31 — a check must be able
to pass *and* fail).

```
v8.38 patched      J1: 34/34 passed, 0 skipped
v8.38 pre-patch    J1: 12/14 passed, 4 skipped   FAIL X2, FAIL X4
v8.37 deployed     J1: 12/14 passed, 4 skipped   FAIL X2, FAIL X4
```

Section X keeps the record of both refutations as checks, so J1b and J1c cannot
be re-filed from prose.

## Regression, run against the file being shipped (M6)

| Suite | Result vs patched candidate | Note |
|---|---|---|
| `test_b2_quorum_diversity` | **73/73** | the suite this change is inside |
| `test_b1_judge_parser` | **162/162** | the suite the stdout banner broke; stderr is why it still passes |
| `test_p11_version_identity` | **29/29** | |
| `test_p18_version_collision` | **20/20** | |
| `test_security_audit` | **128/128** | run alone -- two of these suites in parallel starve each other's RLIMIT_AS probes and neither finishes |
| `test_sem4_degraded_model` | 5/22 | **pre-existing** — identical 5/22 against the pre-patch candidate. Unrelated open item. |
| `test_p15_judge_identity` | crashes | **pre-existing** — `covenant_watchdog` has no `judge_identity`. Identical against v8.37. See below. |

### A test I filed this session that cannot run

`test_p15_judge_identity.py` calls `wd.judge_identity(...)`, and
`covenant_watchdog.py` does not define it. It fails identically on v8.37, so
this change did not break it — I committed a suite that has never executed past
line 93. By this repo's own rule that is not a weak test, it is not a test.
Filed, not fixed here.

## Falsifiable expectation

If this change is right, then on a node running the v8.38 candidate with the
existing three-model `judges.json`:

1. `/health` reports `independent_semantic_judges: 3`, `diverse: false`, and
   the "share a failure" sentence — **not** the "not independently diverse" one.
2. The boot log carries exactly one `local` shadow warning, on stderr, naming
   `covenant_judge_local.py` and `covenant_judge_ollama.py`.
3. Verdicts, routes, bounds and refusals are byte-for-byte what v8.37 produced.
   Nothing here gates: `test_j1` section S4 asserts that no line in the core
   raises or returns False on the independence count.

**What would refute it:** a transaction outcome that differs between v8.37 and
the patched candidate for the same inputs; or an operator who, seeing
`independent_semantic_judges: 3`, concludes the quorum is safe. The second is
the real risk of this change — the number went up because the measurement got
honest, not because the quorum got safer, and all three judges are still one
process on one machine behind one parser. `diverse: false` and the new sentence
exist to say so, and they are the part to watch.

## Not done, on purpose

- **The deployed v8.37 core is unmodified.** This repo's precedent
  (`NODES_UP_2026-08-27.md`): "fixing them is a version bump and a re-deploy,
  not an edit." `verify_deploy.py` pins `EXPECTED_VERSION`, `EXPECTED_LINES` and
  four sha256s of the deployed file; `AM_VERIFY_AND_RESTART.bat` refuses to
  restart on mismatch. Editing the core in place would fail that gate closed,
  correctly.
- **Deploying v8.38 is a separate decision** and needs the v8.38 collision
  (`V838_COLLISION_2026-08-29.md`) resolved first: A24 is in neither core.
- **`duplicate_implementation` still keys on `impl` alone**, deliberately. Three
  `OllamaJudge` instances share `_build_prompt` and `_parse_verdict` whatever
  their models, so one parser bug fails all three. That warning is true and
  stays.
