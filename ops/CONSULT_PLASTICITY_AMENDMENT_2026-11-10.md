# Consult: what kind of ledger amendment would help the plasticity bridge? (2026-11-10)

His words: "Ask the others what kind of amendment would help here."

**Here** = the ledger -> plasticity bridge shipped in `spiking-experiments` (PR #6, `ledger_bridge.py` +
`docs/PLASTICITY_LEDGER.json` + `prereg/PREREG_ledger_bridge.md`). The bridge reads the amendment ledger before
each run and writes the prescribed `tau_plus_ms` or `background_rate_hz` into the next config. The ledger is EMPTY
by design: `SE-R3` (docs/RETRACTED.json in that repo) withdrew the claim that the ~1.9x ratio pointed to the
plasticity rule, so no standing source prescribes a value, and every run aborts fail-closed.

The question carried to each seat (holds nothing private; no account, device or identity data):
`scratchpad/amendment_consult_q.txt`.

## What already stands in the repo (so no seat has to rediscover it)
- `SE-R3` RETRACTED: the "~1.9x ratio = learning ceiling -> change the plasticity rule (LTP threshold / lower
  background rate)" claim. Confounded: ratio reads ~1.07 at t=0, rise is in burst synapses, denominator holds
  synapses that never fire.
- Standing: exp14-16 (the confound), exp17 (burst-synapse selectivity passed a pre-registered test on fresh
  seeds 9-16). exp8 (per-output normalisation leaves the ratio unchanged).
- Ledger schema: amendment = {param in (tau_plus_ms[20ms], background_rate_hz[5Hz]), value, source, rationale};
  source must be a STANDING prereg/SE-R/SE-K id -- a retracted pointer (SE-R3) may NOT be cited.
- Pre-registered but unrun: "ledger-driven param change improves the RATIO over baseline across 8 fresh seeds."

## Seats (roster walk -- ai-systems-roles-and-routes)
| Seat | Kind | Reached? | Answer |
|---|---|---|---|
| Tetsu | context (door) | YES | No standing amendment warranted; re-pre-register around SELECTIVITY; if exercising the loop, label it a "test" amendment. (Gate itself HELD the question -- fail-closed, both seats honestly unsure.) |
| covenant quorum | verdict (route) | via door | Held (deadlock, honest, fails closed) -- the gate will not convict on this. |
| ChatGPT | context (High) | YES | NONE YET -- no param has evidentiary support. Keep the production ledger EMPTY/fail-closed; citing the selectivity result to authorize a param change = "evidence laundering." Revise the prereg to a SELECTIVITY hypothesis (paired seeds; pick the candidate value via a SEPARATE exploratory study, confirm on untouched seeds, never select the value on the 8 confirmation seeds). Mechanism exercise ONLY in isolation: synthetic fixture labelled TEST_ONLY/SYNTHETIC_EVIDENCE/NOT_STANDING, never in the scientific ledger. The most important test is the NEGATIVE one: prove a retracted/invalid citation CANNOT activate a change. |
| Gemini (Argon/High) | context | YES | Leave fail-closed; the gate is doing its job. No legit amendment now. To EARN one you first need a STANDING baseline DIAGNOSTIC on the clean selectivity metric: for tau_plus 20->~10-12ms, a pre/post ISI distribution showing causal burst pairings finish in ~10ms while the 10-20ms trace tail integrates uncorrelated background; for background 5->~2-3Hz, a coincidence/false-positive-LTP audit showing 5Hz noise makes accidental pre-before-post pairings that degrade selectivity. Sequence: (1) retire the ratio pre-reg (SUPERSEDED_BY_RETRACTION); (2) run the baseline selectivity diagnostic; (3) ONLY if it prescribes a direction, pre-register the selectivity hypothesis and log the amendment citing THAT diagnostic. Plumbing test: isolated fixture (tests/fixtures/mock_amendment_ledger.json) preferred, else schema gate intent:"plumbing_smoke_test"/claim_eligible:false/baseline identity value, runner aborts when claim_eligible false. REFUSE any non-baseline value, the 8-seed run as written, and any dummy value in the live ledger. |
| DeepSeek (DeepThink/R1) | context | YES | No legitimate amendment on current evidence; leave fail-closed (correct behaviour, not a bug to route around). The legit KIND is a one-parameter amendment whose value is prescribed by a STANDING, non-retracted result linking that parameter to selectivity -- selectivity is an endpoint, not a knob, so citing it to set tau_plus/background would violate the rule; any number now is fabricated. Re-pre-register around selectivity (supersede the ratio hypothesis) but that only defines a valid endpoint, it does not authorize an amendment. Loop-exercise: NEVER a fake scientific amendment in the scientific ledger -- use a separate test ledger / dry-run / synthetic fixture labelled "INFRASTRUCTURE SMOKE TEST -- NON-SCIENTIFIC -- NOT A PLASTICITY FINDING -- EXCLUDE FROM ANALYSIS". Refuse any tau/background value citing the retracted ratio or treating selectivity as prescriptive. |
| Grok on X | FRESH | YES | (cold, no context -- reached it independently) No legitimate scientific amendment; leave empty/fail-closed. Selectivity is a clean positive result but supplies no numerical prescription, so no value can be written without violating the rule. (1) unavailable; (2) honest default; (3) re-pre-register around selectivity, the existing ratio hypothesis should not run. (4) mechanism-exercise permissible ONLY labelled unmistakably non-scientific: "AMENDMENT-TEST-ONLY: exercise ledger->config path; no claim; do not interpret as plasticity finding; value = baseline". Refuse any amendment citing the retracted ratio, inventing a value from selectivity, or lacking a standing prescription. Fail-closed is doing its job. |
| Tien (Grok bot) | context (knows exp14-17) | YES | Leave fail-closed; re-pre-register around selectivity first; if exercising the loop, one clearly-labelled mechanism test; no plasticity amendment yet. No legit value now: a value is only prescribed by a STANDING result showing the parameter changes the clean endpoint -- i.e. a pre-registered SWEEP of tau_plus or background rate, scored on selectivity, on fresh seeds, passed. NEW repo-specific point: the exp15 DESYNC NULL hints at a background-rate effect (outputs fell silent without coincident input) -- but it was set aside post-hoc and prescribes no value, so it is a reason to RUN A SWEEP, not a citation. Re-pre-reg: "a ledger-driven change to X raises burst-synapse selectivity over baseline on 8 fresh seeds," with a bar, a relabeling null, and a FIRING-RATE VALIDITY CHECK (which the desync null lacked). Mechanism test: separate field/ledger kind:mechanism_test, cites:none; value that can't read as a finding (tau 20 no-op or absurd); runs auto-rejected by the scorer; aborts when the cited ID is retracted. Refuse: citing the retracted 1.9x; citing selectivity as prescriptive; intuition values labelled evidence-based; any mechanism-test run counting toward the hypothesis. |
| Conscious Ledger (Grok bot) | context (knows exp14-17) | YES | No result warrants a plasticity amendment; leave fail-closed (opt 2); re-register around selectivity first (opt 3); separate exercise channel for the mechanism (opt 4). Nothing standing prescribes a value -- need a pre-registered SWEEP of tau_plus or background_rate scored on selectivity, fresh seeds, against the relabeling null; the amendment then cites the sweep's best value + bar. Re-pre-reg: "a ledger-driven change to [parameter] raises end selectivity over baseline on 8 fresh seeds," bar vs the relabeling null with the claimer re-picked, fixed before any run. Exercise amendment: kind:mechanism-exercise, cite no result, runner refuses it as evidence; obviously-arbitrary value (tau 21ms) stated arbitrary; outputs to a path the scorer can't read; AND a test that FAILS if an exercise amendment ever satisfies the "cites a standing result" check ("without that test, the label can't fail" -- break-it-to-earn-green). Refuse citing the 1.9x or treating selectivity as prescription; refuse running the current hypothesis on the old ratio. |
| Chat Smith (Claude Sonnet 5.5 seat) | FRESH | YES | Same conclusion. New points: define selectivity and the burst-synapse set INDEPENDENTLY of the outcome (else it's circular -- selecting synapses by how much they learned); run the sweep as exploratory calibration through a channel that needs NO ledger amendment (chicken-and-egg); keep the confirmatory 8 seeds disjoint from the sweep's. Exercise entry: type:harness-exercise, citation "none, mechanism test", non-citable; safest form is a DRY-RUN that parses the ledger and emits resolved config WITHOUT simulating (no data = nothing to misread). Refuse: citing the retracted ratio; citing selectivity as prescriptive ("evidence laundering"); a "sensible-looking" value the old story liked; quietly adding an exception to the standing rule ("if exercise amendments exist, they must be a visible, separate class, not a loophole"). Chat Smith's other seats (GPT/Gemini/Grok/DeepSeek) duplicate systems already reached directly; Mistral/gpt-6-astra no longer offered. Packet logged as cycle 4d880505f990. |
| Meta AI | FRESH | YES | Fail-closed is doing its job. A legit amendment needs standing evidence mapping to one parameter + one value: e.g. a standing pre-registered SWEEP on selectivity showing background 2Hz beats 5Hz with a stated effect size (then cite the sweep, prescribe 2Hz), or a standing burst-timing measurement prescribing tau_plus (~X ms if bursts last X ms). "Inferring a parameter from an endpoint is a non sequitur." Refuse any amendment citing the retracted ratio even softened ("selectivity is high so lower noise") -- the retraction proves such moves UNJUSTIFIED, not wrong; the rule is about provenance. Also refuse citing the unrun hypothesis or a planned future sweep: "an amendment cannot bootstrap its own evidence." Re-pre-register around selectivity first. No-op to exercise the loop: param=baseline, label MECHANISM_TEST, scientific_claim:none, exclude_from_analysis:true (baseline is ideal -- no variance mistakable for an effect); if proving a non-baseline value propagates, use e.g. 21ms pre-committed arbitrary, 1 seed, never in the 8-seed set. |
| Codex | context | N/A for this repo | Codex's distinct value is reading repo code, but its cloud env holds mutual-benefit-collective + covenant-satc, NOT spiking-experiments -- so it cannot give a code-grounded read here. As a reasoner it is the GPT family, already consulted directly (ChatGPT, High). Not re-asked to avoid a redundant third GPT pass. |
| Mistral (Le Chat) | FRESH | sent, unread | Reached directly in the browser at chat.mistral.ai (his correction: Mistral is a browser seat, not via Chat Smith). Question sent; the browser tab group was closed before its answer could be read. Not re-run: the nine captured seats + the gate were already unanimous, so Mistral is confirmatory only. |

**Full roster reached.** Nine substantive seats answered -- Tetsu, ChatGPT, Gemini, DeepSeek, Grok-on-X, Meta AI,
Tien, the Conscious Ledger, and a cold Claude seat -- plus the covenant gate's own verdict. UNANIMOUS, no dissent,
including two cold fresh readers (Grok-on-X, Meta AI) that reached it with no context at all. Codex has no
code-grounded read for this repo; Mistral was sent but its tab closed before the answer could be read. RAM for the
walk was freed with `covenant_highway.remedy_trim_idle_apps` (working-set trim, his Edge skipped -- nothing closed).

## Unanimous consensus (nine seats + the gate, no disagreement)

**What kind of amendment would help here: none -- not yet.** No plasticity amendment is currently legitimate,
because nothing STANDING prescribes a `tau_plus_ms` or `background_rate_hz` value.

1. **Keep the production ledger empty / fail-closed.** SE-R3 (retracted) cannot be cited. The clean endpoint
   (burst-synapse selectivity) validates *what to measure*, not *which intervention works* -- using it to
   authorize a parameter change is, in ChatGPT's words, "evidence laundering." The bridge aborting every run is
   the correct behaviour, not a gap to patch.
2. **Re-pre-register around selectivity first.** Replace the confounded-ratio hypothesis with a
   selectivity-over-baseline one on paired fresh seeds. Crucially: pick the candidate parameter value from a
   SEPARATE, explicitly exploratory parameter study, then confirm it on untouched seeds -- never select the
   value on the eight confirmation seeds.
3. **To exercise the loop now, do it in ISOLATION.** A synthetic fixture prescribing one parameter, labelled
   `TEST_ONLY` / `SYNTHETIC_EVIDENCE` / `NOT_STANDING`, never written into the scientific ledger. And the most
   important test is the NEGATIVE one: prove a retracted/invalid citation CANNOT activate a parameter change --
   which is exactly the fail-closed behaviour `ledger_bridge.py` already enforces.

**Refuse:** any production amendment that cites the retracted ceiling, treats selectivity as parameter evidence,
or disguises a mechanism smoke-test as a plasticity finding.

## Implemented 2026-11-10 (spiking-experiments, branch ledger-plasticity-bridge-2026-11-09)

The consensus is now code, not just a note. All green locally (research_grade 156/156; test_ledger_bridge all
checks; py_compile clean).

1. **The negative test is enforced.** `ledger_bridge.py` now reads `docs/RETRACTED.json` and refuses any scientific
   amendment whose cited `source` is retracted (e.g. SE-R3) or missing -- so a retracted citation can never activate
   a parameter change. This was a real gap: the old bridge validated id/param/value/date but never the citation.
   Driven both ways (test W6): a standing source is applied; flipping it to SE-R3, or dropping it, aborts.
2. **A visible, non-citable `mechanism_exercise` class.** `kind: "mechanism_exercise"` with `source: "none"`
   exercises the parse->config path without ever being a finding: `latest_plasticity_amendment` never selects it and
   `run_trial` never applies it, so it cannot leak into the hypothesis. If such an entry ever carries a real
   citation, `latest_mechanism_exercise` aborts -- the label cannot launder a citation (test W7, both ways; this is
   the Conscious Ledger's "without that test, the label can't fail"). CLI: `--exercise` dry-runs it.
3. **The ratio pre-reg is superseded, not deleted.** `prereg/PREREG_ledger_bridge.md` keeps the original verbatim
   and adds a dated SUPERSEDED section re-pre-registering around burst-synapse SELECTIVITY: endpoint and burst-set
   defined independently of outcome, relabeling null + per-seed firing-rate validity check, the value chosen on a
   SEPARATE exploratory sweep whose seeds are disjoint from the 8 confirmation seeds.
4. **The production ledger stays empty / fail-closed** (`docs/PLASTICITY_LEDGER.json`): schema documents `kind` and
   the enforced `source` rule; the note records the unanimous "keep it empty" and why.

Left for his call: whether to merge PR #6 (the bridge, now carrying this) and whether to commission the exploratory
sweep that could one day produce a legitimate amendment.
