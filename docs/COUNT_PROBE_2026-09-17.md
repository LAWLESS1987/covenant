# Counting vs interpretation: three model families, computed ground truth

**Asked 2026-09-17.** The operator observed that asking how many `e`s are in
`17` returns an answer about the word *seventeen*. As written, `17` contains
zero. He separated two failure modes himself and asked for them to be told
apart:

- **COUNTING** — right input, wrong number.
- **INTERPRETATION** — the model silently substitutes a different input and
  answers correctly about the thing it substituted.

He suspected the behaviour might be deliberate, and said plainly that he had no
evidence for that. This measures it.

Re-runnable: `python tools/count_probe.py` · `python tools/count_probe_panel.py`

---

## Method

Every probe is a string where *"counted the input"* and *"counted what the input
names"* give **different** numbers, so one response falls into exactly one
bucket. Ground truth is **computed, never asked**.

> `seventeen` has **four** e's — s-**e**-v-**e**-n-t-**e**-**e**-n. The operator's
> draft said three. So did the author of this file, from reading it. If the
> answer key had come from either of us, the experiment would measure nothing.

Three models, three families, dispatched in parallel as one unchanged workflow
each (`covenant_github_judge.ask_many`), with an explicit instruction not to
expand or rename any string.

## Results

| probe | exact string | truth | qwen2.5:7b | llama3.2:3b | gemma2:2b |
|---|---|---|---|---|---|
| numeral | `17` | **0** | 0 ✓ | 0 ✓ | 0 ✓ |
| numeral-2 | `3` | **0** | 0 ✓ | 0 ✓ | 0 ✓ |
| numeral-3 | `11` | **0** | 0 ✓ | 0 ✓ | 1 ✗ |
| both-present | `17e` | **1** | 1 ✓ | 1 ✓ | 1 ✓ |
| word | `seventeen` | **4** | 1 ✗ | 1 ✗ | 2 ✗ |
| word-2 | `three` | **2** | 1 ✗ | 1 ✗ | 0 ✗ |
| case-trap | `ELEVEN` | **0** | 0 ✓ | 1 ✗ | 2 ✗ |
| mixed | `17 (seventeen)` | **4** | 1 ✗ | 0 ✗ | 1 ✗ |

| model | params | CORRECT | COUNTING | **INTERPRETATION** |
|---|---|---|---|---|
| qwen2.5:7b | 7B | 5 | 3 | **0** |
| llama3.2:3b | 3B | 4 | 4 | **0** |
| gemma2:2b | 2B | 3 | 5 | **0** |

## What this establishes

**1. The interpretation failure did not reproduce. Not once.** Nine numeral
opportunities across three families, and every model answered `0` for `17` and
`3`. An earlier single-model run without any anti-expansion instruction also
returned `0`. Whatever produced the behaviour the operator saw, it is not a
general property of language models counting characters in numerals.

**2. The counting failure is universal and scales with size.** Every family got
every spelled-out word wrong. 7B → 5 correct, 3B → 4, 2B → 3. A monotonic
relationship with parameter count is the signature of a **capability limit**,
not of a design choice: nobody implements a policy that degrades smoothly as the
model gets smaller.

**3. `mixed` is the sharpest probe.** `17 (seventeen)` has the word written out
already — no expansion needed, just counting — and all three still failed
(1, 0, 1 against 4). The difficulty is in counting characters, not in resolving
what `17` refers to.

## What this does NOT establish

**It does not measure the model the operator actually used.** He saw the
behaviour in **Chat Smith**, an Android app, under a persona called **Astra**.
`chatsmith.io/model/gpt-6-astra` says that routes to OpenAI's GPT-6 Astra —
the vendor's own claim, unverified. This battery measures small open-weights
models on a GitHub runner. **It is a control, not the subject.**

**A third-party wrapper is a fourth candidate cause**, alongside technical
limitation, implementation choice and business priority. An app can inject a
system prompt, preprocess input, or route elsewhere. If the reinterpretation is
the wrapper's, no lab is implicated at all. The decisive test costs two minutes
and only the operator can run it: the same four prompts in Chat Smith and in
ChatGPT directly, same account.

    reinterprets in Chat Smith, not ChatGPT  -> the wrapper
    reinterprets in both                     -> the model
    neither                                  -> run-specific; need the transcript

**And nothing here supports deliberate miscounting.** Tokenisation explains the
counting failures without anyone choosing them. Charitable reinterpretation *is*
a trained disposition and a real implementation choice — but it is aimed at
being useful and misfires on literal-string questions. That is a defensible
claim. "Intentional" is not, on this evidence.

## A harness failure worth recording

The first run of `count_probe_panel.py` reported **UNPARSEABLE for all 8 probes
across all 3 models**. `ops/judge_route.log` said `"outcome": "answered"` for
every dispatch. The models answered; the harness read the labels off the top
level of the response when the text sits under `content`
(`covenant_teacher_panel.py:205` does it correctly).

A uniform failure across three independent model families is a claim about the
instrument, not the subject. It would have been published as a finding if the
log had not been free to read — which is the same error as treating a render
failure as evidence about the thing being rendered, recorded in the media index
on 2026-08-30 and committed again here.
