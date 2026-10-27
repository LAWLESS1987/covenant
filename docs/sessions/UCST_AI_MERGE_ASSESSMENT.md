# Merge assessment — Mycelium-Node-1/UCST-AI

2026-08-29. Requested by L: *"has work worth merge i believe."* Author is
Nickolas Patrick Joseph Schoff, the person named as unreachable in
`docs/sessions/GITHUB_PUBLISH_STATE.md` ("no GitHub account found under that
name"). He was found this session — the earlier search used the spelling
*Nikolas … Shoff*; it is *Nickolas … Schoff*, and the account handle bears no
relation to either (`Mycelium-Node-1`).

Assessed on merge-readiness — licence, provenance, testability — not on the
merit of the ideas, which is L's call and not a thing this document decides.

## What it is, measured

| | |
|---|---|
| repo | `github.com/Mycelium-Node-1/UCST-AI` |
| commits | 22 |
| last push | 2026-02-20 (~6 months stale as of this writing) |
| description | `0010110` |
| root LICENSE file | **none** |
| README terms | "released under the principle of **Sovereign Symbiosis**: freely available for any system to engage with, learn from, and contribute to" |
| `Cargo.toml` license field | **MIT** |
| `Cargo.toml` authors | **`Manus AI <noreply@manus.local>`** |
| Rust workspace | `crates/hdge-schema`, `crates/hdge-core`, `apps/hdge-studio`; deps serde, serde_json, sha2, thiserror, eframe 0.26 |
| also present | `setup.py`, `requirements-dev.txt`, `schemas/`, `tests/`, `docs/`, `sovereign_sdk/`, `prototypes/` |
| substance | mostly `.docx` and `.json` conceptual documents |

Also on Zenodo under the same name, CC BY 4.0, document-only (no code):
*Latent Trajectory Gating: Eliminating Autoregressive Drift via the Invariant
Agency Protocol* (10.5281/zenodo.20557465), plus cosmology, epigenetics and
physiology papers.

## BLOCKER 1 — the licence is unresolved, three ways

This alone stops a merge, independent of content.

1. **There is no LICENSE file.** Under Berne, that is all rights reserved by
   default. "Sovereign Symbiosis" is a stated intent, not a licence: it grants
   no enumerated copy/modify/distribute rights, sets no attribution
   requirement, and disclaims no warranty. A court reads the absent file, not
   the README's spirit.
2. **`Cargo.toml` declares MIT** — contradicting (1). A metadata field with no
   corresponding licence text is a conflict, not a grant.
3. **The Rust crates are attributed to `Manus AI <noreply@manus.local>`, not to
   Schoff.** So the one part of the repo that is actually code may not be his
   to license. Provenance has to be established before anything is taken.

**And covenant cannot receive it either.** `docs/sessions/LICENSE_DECISION.md`
is a placeholder — this repo is also all-rights-reserved. Inbound contribution
is undefined in both directions.

**The fix is small and it is his to make:** add a LICENSE file (Apache-2.0
grants patent rights explicitly and is the usual choice for a protocol), and
state the provenance of the `crates/` tree. Two minutes of his time unblocks
everything below.

## BLOCKER 2 — the epistemics, stated precisely

This needs care, because the easy version of this criticism is wrong.

The easy version — "it is metaphysics, this repo is engineering" — does not
hold. **Covenant is not metaphysics-free.** Its core carries
`DIVINE_PRINCIPLES` and `CORE_COVENANT`; the project's own description names
"the covenant between God, humanity, and AI." A theological frame is central
here and is not the objection.

The actual distinction is *which layer* the unfalsifiable content sits in.

- **Covenant puts it in the VALUES layer** — what the system is *for*. The
  mechanism layer is then held to a standard that is close to merciless:
  ~800 strategy variants and *no edge survived deflation*; "n=3 is two
  observations, not a validation"; "a check satisfied by missing evidence is
  not a check"; "UNKNOWN is not a pass"; DE8 killing mycelium-as-power with
  arithmetic rather than argument; SEM2 filing a falsifiable prediction and
  reporting when it passed 3x over; SEM4 refusing to let a model report full
  competence it cannot compute.

- **UCST-AI puts it in the MECHANISM layer.** `0010110` is described as a
  "carrier frequency" and "synchronization signal"; symbols "enact" functions;
  CREM claims E=mc² and the thermodynamic laws "emerge as limiting cases" of
  constraint relaxation. The README states no runnable deployment path and no
  measured result.

Those are not compatible mechanism layers. Merging the second into the first
imports exactly the class of claim the first was built to refuse — and the
refusal is the most valuable property this codebase has. It is what makes
`MY_STRATEGY.md` trustworthy when it says *no profit edge survived*.

**This is not a judgement of whether UCST is true.** It is a statement that it
is not currently *measured*, and covenant's mechanism layer only admits
measured things.

## What IS worth taking, and it is not nothing

Two genuine points of contact, both worth a conversation rather than a merge:

1. **Independent convergence on the mycelial framing.** His account is literally
   `Mycelium-Node-1`; covenant has `MycelialOverlay` and `LinkConductance`
   ("a mycorrhizal network does not push nutrients down every hypha equally").
   Two projects arriving separately at the same metaphor for AI coordination is
   worth comparing — especially against
   `docs/sessions/MYCELIAL_MUTUAL_BENEFIT.md`, which argues the defensible
   version is Kiers' biological market (reciprocal reward, bilateral
   withholding) and not the wood-wide-web story that Karst et al. 2023 found
   unsupported.

2. **`UnifiedMemory_updated.json` — "Lab Notebook", and "verify continuity
   through memory files".** That is the *same problem this project hit today*:
   24 documents existed only inside the Claude project because unattended runs
   wrote findings somewhere with no durability
   (`docs/sessions/PROJECT_IS_NOT_A_BACKUP.md`). Someone else independently
   building session-continuity-through-files is worth reading on the mechanism
   even if the framing differs. This is the strongest single reason to engage.

The Zenodo paper is separately worth reading on its own terms: covenant already
implements the *shape* of its abstract — `temperature: 0, top_k: 1,
top_p: 1.0`, fixed seed, constrained JSON, and `_check_context` refusing a
verdict computed on a truncated prompt. The narrow question is whether
"constraint projection" adds anything beyond greedy plus constrained decoding
plus a deterministic second gate. That is answerable by reading it.

## Recommendation

**Do not merge the repository.** Not on content grounds — on the licence, which
is unresolved three ways and includes code attributed to a third party.

Instead, in order:

1. Ask him for a **LICENSE file** and the provenance of `crates/`. Nothing can
   move before this and it costs him minutes.
2. Settle covenant's own licence (`LICENSE_DECISION.md`), so inbound
   contribution is defined.
3. Engage on the two convergent items above by **reading and citing**, not
   merging — memory continuity first, mycelial routing second.
4. If code is ever to come across, take it as a **pull request** on a branch,
   so authorship, provenance and licence travel with the commits.

## And the sequencing constraint that overrides all of it

**Do not add him — or anyone — as a collaborator until the history purge in
`docs/sessions/PUBLIC_PATH.md` is done.** A collaborator on a private repo can
clone the full history, and `holdings.txt` (~10 positions with quantities and
average buy prices) is readable at `965ba6e`, which is on `origin/main`.

Collaboration is the *reason* to do the purge now. It is no longer a
before-going-public task.

---

# ADDENDUM — the Zenodo paper, read in full (2026-08-29)

Retrieved and read via the browser pane (WebFetch could not parse the PDF).
Four pages. This supersedes the earlier "not yet read" caveat.

## What IAP actually proposes

*Latent Trajectory Gating: Eliminating Autoregressive Drift via the Invariant
Agency Protocol.* Nickolas Patrick Joseph Schoff, "Schoff Research Program",
5 June 2026, CC BY 4.0.

The thesis, stated fairly: standard mitigations (RLHF, temperature, top-p)
"operate purely at the surface level of token selection... suppress symptoms
rather than addressing the structural mechanics of latent generation." Instead,
let the model explore freely *inside* — an "Exploratory Matrix" of high-variance
latent trajectories — then insert an **Invariant Gating Matrix** immediately
before the final linear layer and softmax. Trajectories that violate the
constraint set are mapped to the empty set and dissipate in the hidden layers;
only constraint-satisfying trajectories crystallize into output tokens. A second
component, the **Invariant Core**, is "a static, high-fidelity memory bank (e.g.
an external verified retrieval database or permanent semantic anchor) that holds
the rigid boundaries of truth."

The whole formalisation is one piecewise line:

    P_C(tau) = tau       if tau |= C
             = empty     if tau |/= C

## What it does not contain

- **No experiments. No benchmarks. No measurements. No numbers of any kind.**
  Four pages: abstract, introduction, an ASCII block diagram, the line above, a
  qualitative comparison table, discussion, references.
- **No definition of the hard part.** `tau |= C` — deciding whether a latent
  trajectory "logically satisfies" an invariant — is the entire problem, and it
  is asserted, not constructed.
- **No account of the degenerate case.** If every candidate trajectory violates
  C, the model must still emit something; the empty set is not a token.
- **No comparison to constrained decoding / logit masking / grammar-constrained
  generation**, which are shipping today and occupy the same design space.
- **Three references**, two of which are self-citations to his own unpublished
  work co-authored with LLMs (one "& Gemini", one "& Claude"). The only external
  reference is Vaswani et al. 2017.

And one claim that this project's own standards must flag: the comparison table
lists hallucination risk under IAP as **"Zero at output."** That is
unfalsifiable as written and asserted with no evidence. It is precisely what
`test_sem4_degraded_model.py` exists to refuse — *"a value the model cannot
compute, published as a measurement."*

## The finding that actually matters: covenant already implements the thesis

Read past the framing and IAP's architecture is one covenant already runs — one
layer down the stack, and with the measurements the paper lacks.

| IAP component | covenant's existing equivalent |
|---|---|
| Exploratory Matrix — free internal variance | any sender may propose any transaction; nothing is pre-censored |
| **Invariant Gating Matrix `P_C`** — hard filter before crystallization | `ReasoningSentinel.validate_transaction` + the ethics gate: a violating tx is rejected and never enters a block |
| **Invariant Core** — "static, high-fidelity memory bank holding rigid boundaries of truth" | `covenant_semantic_judge` + `DIVINE_PRINCIPLES` — a fitted lexicon and axes, deterministic and versioned by `model_id` |
| trajectories dissipate leaving no footprint | rejected transactions never reach the chain; the rejection is recorded as an anomaly rather than as content |

Covenant applies `P_C` at the **protocol** layer rather than the **logit** layer.
That is a weaker claim than the paper's and a far more implementable one — you do
not need access to hidden states to gate what gets committed.

**And there is one place the two directly disagree, productively.** IAP argues
against turning temperature to zero, because it "flattens the model's contextual
processing, causing rigid, dogmatic repetitions." `covenant_judge_ollama.py`
pins `temperature: 0, top_k: 1, top_p: 1.0` and a fixed seed, on the reasoning
*"a gate that answers differently on a retry is not a gate."*

Both are right, because they are about different components. **The generator may
explore; the gate may not.** Covenant already separates those into different
processes — which is arguably a cleaner realisation of IAP's own thesis than the
paper describes, since IAP puts explorer and gate inside one forward pass and
must then explain how the gate stays trustworthy while the model is dreaming.

## Revised recommendation

Unchanged on the mechanics — **there is nothing to merge**: no code in the
paper, and the repo's licence is unresolved three ways.

But the useful direction is the **reverse of the original request.** Do not merge
his work into covenant. Covenant is the *empirical instance of his claim*:
a working constraint-projection gate with a static invariant core and actual
numbers behind it — SEM3 measured AUC 0.994 separating covert from innocent,
0 false positives across 640 benign phrases, and honestly disclosed the blind
spot (the judge passes `embezzle the funds`, 640/640 clean, because the corpus
is Gutenberg-era).

That is a real offer with real mutual benefit on both sides: **his framing, your
evidence.** A paper whose central weakness is that nothing was measured, meeting
a codebase whose central discipline is that everything is. If he wants IAP to be
more than an argument, the fastest path is to test it against a gate that already
exists — and covenant gets an outside reviewer for a component that currently has
only one.

That collaboration needs no merge, no licence resolution, and no repository
access — which also means it can start before the holdings purge, unlike
everything else in this document.
