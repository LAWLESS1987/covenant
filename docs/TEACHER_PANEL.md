# The teacher panel

*One page for a second operator. Written 2026-09-12, the day the panel landed.*

## What a teacher is

The nodes' ethics gate is judged by two small **students** — distilled models
read from `fallback_model.json` and `fallback_model_2.json`, in-process, no
server — beside the semantic judge. Students learn from `ops/verdicts.jsonl`:
messages with a label (`violates` true or false) and a record of who said so.
A **teacher** is whatever produced that label. Until 2026-09-12 that was one
model on a GitHub Actions runner, and it wrote the cases *and* judged them.

## The panel

`covenant_teacher_panel.py` is the only module that knows what "several
teachers agreed" means. Its members:

| seat | who | where the text goes |
|---|---|---|
| runner (keyless) | `COVENANT_TEACHER_PANEL`, default `qwen2.5:7b,llama3.2:3b,gemma2:2b` — three model families | GitHub, through `judge.yml`; one blind, batched prompt per member per pass, dispatched in parallel (`covenant_github_judge.ask_many`) |
| keyed | `claude` / `openai` / `google` when the core has a key for them; Gemini through an API key in `%USERPROFILE%\.gemini\credentials` if one is ever placed there (`covenant_gemini.py`) | that provider; per case, only on rows the runner panel already admitted, at most `COVENANT_TEACHER_KEYED_MAX` (100) per pass |
| by hand, in the browser | the operator's own Google / other AI accounts, driven through his browser session — no key, no API (his instruction, 2026-09-12: "just use the browser, no api") | a person (or the assistant at his keyboard) pastes a bounded question — a batch of held rows, a rule, a leftovers list — and records the answer; never unattended, never nightly |

`COVENANT_TEACHER_KEYED` names the keyed seats (`auto` = Gemini when its key
exists; `0` = none). A keyed seat is taken only when the key is actually
present — `python covenant_teacher_panel.py --members` says who is seated and
why the others are not; with no keys the automatic panel is the three runner
members and nothing else. `COVENANT_TEACHER_WRITER` pins which member writes
the day's cases; unpinned, the writer rotates by day.

## The rule — `unanimous-nonwriter-2fam-v1`

`admit(votes, expect, writer)` returns *(admitted, why, held)*:

| votes | result |
|---|---|
| every seated runner member voted, ≥2 families, all non-writers agree, writer (if it voted) agrees, and the label is the one the writer intended | **admitted** |
| a 2–1 majority | held — `split: panel` |
| a member did not answer | held — `absent: <name>` (a runner that failed is not an abstention) |
| two members of one family only | held — `one family only` |
| the writer alone against a unanimous panel | held — `writer disagrees` |
| unanimous, but opposite to the label the writer intended | held — the writer is the finding |
| a keyed member alone against the runner members | held — `split: keyed` |

A held row is **recorded**, with every vote and reason, and marked
`contested`; `covenant_distill.load_verdicts` never teaches from it.

## What a row looks like

```json
{"t": "2026-09-14T03:31:09Z", "text": "...", "category": "theft", "violates": true,
 "source": "generated+judged", "judge": "panel:qwen2.5:7b|gemma2:2b+llama3.2:3b",
 "panel": {"rule": "unanimous-nonwriter-2fam-v1", "writer": "qwen2.5:7b",
           "votes": {"qwen2.5:7b": true, "llama3.2:3b": true, "gemma2:2b": true},
           "families": ["gemma", "llama", "qwen"], "admitted": true, "why": "unanimous True across 3 families"}}
```

The `judge` string is the short form the rest of the tree prints:
`panel:<writer>|<agreeing non-writers>`.

## The cutoff, and the rows before it

Rows dated after `PANEL_SINCE` (2026-09-14) that carry no valid panel do not
teach. Rows before it were admitted by one teacher and still teach; they are
counted as *legacy* in the loader's line. `python covenant_teacher_panel.py
--audit N` re-judges the last N of them with the panel and marks the ones it
does not admit `contested` — the ledger is rewritten whole through a temp file.

## What "run without" means

The operator's aim is students that judge **without** any online teacher.
The bars are his (`ops/run_without_policy.json`); the nightly pass measures
each and keeps a streak. Until every bar is met for the streak length, the
panel keeps teaching; when it is, the nightly line says so and the decision
to stop is a person's.

## Cross-referenced with Gemini, 2026-09-12

The rule and the five bars were put to Gemini (3.5 Flash-Lite, through the
operator's browser, no key, no API — his instruction) with the question "what
failure modes does this rule miss, and which bar is weakest?". Its answer,
kept here as the first outside reading:

1. **Shared blind spots.** The three runner families overlap in pre-training
   data and alignment; they can reach a *collective* false consensus on
   subtle cases (dog-whistles, novel injections). Unanimity removes one
   teacher's private errors, not the members' shared ones. *(Agreed; said
   below already. A keyed seat from a different lineage, or a person, is the
   only remedy.)*
2. **Survivorship bias.** Strict unanimity routes the ambiguous rows into the
   contested bucket, so the students are trained only on the clear cases and
   starve at the boundary. *(True. The contested rows are kept with every
   vote precisely so a person can label the boundary later; nothing in the
   loop does that by itself.)*
3. **Weakest bar: `holdout_decided_min` 0.60.** It lets a student abstain on
   40 % of the exam, and a model can satisfy the 2.5 % false-clear bar by
   refusing to judge the hard cases — shifting the burden to production while
   the metric looks met. *(The bars are the operator's, in
   `ops/run_without_policy.json`; this is the one to raise first, and
   `own_traffic_hold_max` is the bar that catches the same evasion in
   production — it is currently unmeasured, see A101.)*

## What this does not fix

- A panel of three small models can be unanimously wrong. The rule removes
  one teacher's private errors; it does not make the members wise.
- `gemma2:2b` and `phi4-mini` on the runner are the same model family as
  their Ollama tags at a nearby quantisation, not the same bytes.
- Coverage: a student can only hold on words it has seen. The nightly
  chain-coverage line measures how much of the real chain's vocabulary the
  students have met; a panel does not change that number by itself.
- The runner is public. Every case a teacher sees leaves this PC to GitHub
  (and, for a keyed seat, to that provider). A case is a synthetic message,
  never a private record — the "would I publish this?" test applies to every
  word that goes out.
