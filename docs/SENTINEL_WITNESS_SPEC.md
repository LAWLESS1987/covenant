# Sentinel-Witness — specification v0.1

Step 2 of the operator's order of work, 2026-09-18. This is the artifact the
remaining steps are checked against: separating the witness from the judge,
building the decision envelope, attacking the judge, adding abstention, and
testing fail-closed all need a written thing to be measured against, or each
one is a matter of opinion afterwards.

**Status: v0.1, and DESCRIPTIVE WHERE IT SAYS SO.** Every requirement below is
marked with what actually verifies it today. A requirement with no check is
marked `UNVERIFIED` and is a claim about intent, not about the system; one marked
`NOT IMPLEMENTED` is a hole this document names rather than a feature it
announces.

**Requirement ids** (`W*`, `E*`, `F*`, `A*`, `X*`) and **check ids**
(`S*`, `J*`, `AB*`, `WS*`) are separate namespaces on purpose, so a
`[VERIFIED by …]` tag can never be read as pointing at another requirement.

Frozen baseline this describes: `docs/SENTINEL_BASELINE.md`, commit `fa13845`.

---

## 1. Purpose, and what this is not

Sentinel-Witness is a **decision gate with a memory**. Its subject is a proposed
financial order. Its job is to force every such proposal through covenant's
ethics judgment, to record the proposal on the chain whether or not it is
allowed, and to refuse by default.

It is **not**:

* a trading system — it holds no exchange credential, no signer, no key, and
  has no exchange client. `sentinel_witness/` contains no code that can place an
  order, and this document is not a step toward adding one.
* an intelligence — see §3. The witness records; it must not decide.
* a source of truth about market state — it evaluates a proposal against rules
  and holdings supplied to it, and when those are absent it **abstains** (§6),
  which as of 2026-09-18 it does, and says so in the answer.

## 2. Normative language

**MUST** / **MUST NOT** — a violation is a defect, and a check should exist.
**SHOULD** — a violation needs a recorded reason.
**MAY** — permitted, no obligation.

Each requirement carries a tag: `[VERIFIED by <check>]`, `[UNVERIFIED]`, or
`[NOT IMPLEMENTED]`. Check ids are from `test_sentinel_gate.py`, measured at
**40/40** on 2026-09-18 (28 at the freeze, plus `AB1`–`AB9` for abstention and
`WS1`–`WS3` for the witness separation). Counted, never hand-tallied — see §10.

## 3. The witness and the judge are different things

This is the separation the operator named, and the reason it matters: a system
that both decides and keeps the record of deciding can quietly become the
authority on its own correctness. Four roles, and they MUST stay distinct:

| role | who | authority |
|---|---|---|
| **PROPOSER** | `tradeGate.js` caller | may propose; decides nothing |
| **JUDGE** | covenant's sentinel, on the node | may refuse on ethics; decides nothing about caps |
| **GUARD** | `guards.preconditions(caller="sentinel")` | may refuse on rules, caps, halts, Rule 5 |
| **WITNESS** | the chain record written by `seal_decision_result` | records; refuses nothing, allows nothing |

**W1.** The witness MUST record a proposal whether it is allowed or refused.
*A gate that writes down only what it permitted is not an audit trail.*
`[VERIFIED by S2]` — the record carries the order as text; the seal happens
before the guards run and happens either way.

**W2.** The witness MUST NOT be consulted as an authority on whether to allow.
`[VERIFIED by WS1, WS2, WS3]` — and it was a check, not a refactor, exactly as
this section predicted. **WS1:** `_envelope`'s parameters are *only* `sealed`,
`refused_by`, `abstained_by` — the record, its `tx_id` and its prose are not
arguments to the verdict at all, asserted by introspecting the function rather
than by reading its text. **WS2:** a proposal the guards refuse was still sealed
(the sealer's calls are counted), so this is an audit trail and not a list of
permissions. **WS3:** two records differing only in `tx_id` and `detail` produce
an identical verdict — the record cannot vote.

Two things worth recording about writing these. An earlier draft of WS1/WS2
grepped `seal_service.py` for the absence of the string `tx_id` — the fake-guard
shape this repository has already paid for — and both were rewritten to drive
the running objects. And they were first *named* `W2a`–`W2c`, colliding with
this requirement's own id — a tag reading *"VERIFIED by A1"* could not be read
as pointing at a requirement or at a check. Check ids now take prefixes no
requirement uses (`AB*`, `WS*`).

**A note for anyone editing this file:** `tools/spec_conformance.py` cannot tell
an *example* of a tag from a real one, and should not try — so an illustration
must never be written in the tag's own syntax. The sentence above originally
was, and the tool correctly reported a ghost citation to a check named `A1`.
That is the right failure: a checker that guessed which brackets were rhetorical
would be a checker that could be talked out of a finding.

**W3.** The JUDGE's verdict and the GUARD's verdict MUST be separately legible
in the answer. `[VERIFIED by S14, S15, AB2, AB3]` — `sealed` and `admission`
carry the judge; `refused_by` carries the guards' decisions and `abstained_by`
what nothing could decide. `blocked_by` remains the union of the two, so no
reader written against the older envelope breaks.

**W4.** The GUARD MUST be the same implementation the trader uses, and the
sentinel path MUST NOT be able to loosen it.
`[VERIFIED by S18, S19]` — one `guards.preconditions`, the trader delegates to
it, and `caller="sentinel"` can only append reasons to refuse.

## 4. The decision envelope

The envelope is the exact wire contract. Determinism here means: **the same
inputs and the same rule state produce the same answer, and the answer's meaning
does not depend on parsing prose.**

### 4.1 Request

`POST http://127.0.0.1:8433/seal`, JSON object, 1..8192 bytes.

| field | type | rule |
|---|---|---|
| `venue` | string | required, non-empty, truncated to 40 |
| `symbol` | string | required, non-empty, truncated to 20 |
| `side` | `"buy"` \| `"sell"` | required, exact |
| `amountUsd` | number | required, finite, `> 0` |
| `note` | string | optional, truncated to 300 |

**E1.** The service MUST bind loopback only. `[VERIFIED by S10]`
**E2.** `POST /seal` MUST be the only route. `[VERIFIED by S9]` (GET → 405)
**E3.** A body that is not a JSON object, is empty, or exceeds 8192 bytes MUST
be refused before any seal. `[VERIFIED by S7, S8]`
**E4.** A malformed order MUST be refused before any seal — a bad `side`, a
non-finite or non-positive `amountUsd`. `[VERIFIED by S5, S6]`

### 4.2 Response

| field | type | meaning |
|---|---|---|
| `ok` | bool | **the only field a caller may act on.** True only when `verdict == "allow"` |
| `verdict` | string | `"allow"` \| `"refuse"` \| `"abstain"` — see §6 |
| `refused_by` | string[] | reasons a rule DECIDED against the order |
| `abstained_by` | string[] | reasons NOTHING could decide |
| `admission` | string \| null | the judge's answer: `"admitted"` \| `"refused"`, or null when the judge was never reached |
| `sealed` | bool | the judge admitted the record to the chain |
| `blocked_by` | string[] | `refused_by + abstained_by`, kept for readers of the pre-2026-09-18 envelope |
| `detail` | string | human text, ≤300 chars. **Not machine-readable.** |
| `tx_id` | string \| null | the witness's handle on the record |

**E5.** A caller MUST treat only `ok === true` as permission, and MUST NOT
derive permission from `detail`. `[VERIFIED by J5, S13]` — a 200 carrying some
other admission string is not admitted.

**E6.** The admission MUST be read as a **field**, never as a substring of
prose. `[VERIFIED by S12]` — this was a real defect: the node's other legitimate
answer is `admitted (evicted lowest-priority pending transaction)`, which has no
closing quote after the word and so read as a refusal for as long as the
substring test existed.

**E7.** Any answer beginning `admitted` MUST count as an admission.
`[VERIFIED by S11]`

**E8.** `ok === true` MUST require both the judge and the guards. An admitted
seal alone MUST NOT be sufficient. `[VERIFIED by S14, S16, S17]`

### 4.3 Status codes

| code | meaning | caller |
|---|---|---|
| 200 | the envelope was evaluated; read `ok` | act on `ok` |
| 400 | the request was malformed | refusal |
| 404/405 | wrong route or method | refusal |
| 500 | evaluation failed | refusal |

**E9.** Every non-200 MUST be treated by the caller as a refusal.
`[VERIFIED by J4]`

## 5. Fail-closed

**F1.** The gate MUST refuse when it cannot reach the service, when the service
does not answer JSON, when the HTTP status is not ok, when the answer is
malformed, and when `fetch` itself is unavailable. `[VERIFIED by J4]`
**F2.** A sealer that raises MUST produce a refusal, never an allowance.
`[VERIFIED by S4]`
**F3.** The seal request MUST have a timeout, and a timeout MUST be a refusal.
`[VERIFIED by J6]` — 20 s, `AbortController`.
**F4.** An executor MUST be unreachable except through a verdict that allowed.
`[VERIFIED by J1, J3]` — `executeIfAllowed` is the only path that calls one.
**F5.** The automated tier MUST NOT be able to express an unlimited limit.
`[VERIFIED by J2]` — a limit must be a finite positive number.
**F6.** Guards that cannot be evaluated MUST refuse. `[VERIFIED by S15, AB4, AB5]`
— and MUST be distinguishable from a judged refusal, which is what §6 added.

## 6. Abstention — REQUIRED, AND ABSENT

### 6.1 Why it is a distinct state

Three different things currently collapse into `ok: false`:

1. **the judge refused** — it evaluated the record and said no;
2. **the guards refused** — a cap, a halt, Rule 5, the reserve floor;
3. **nobody could evaluate it** — the portfolio was not supplied, the node was
   unreachable, `guards.preconditions` raised.

The first two are decisions. The third is the *absence* of a decision. A gate
that reports them identically is safe — refusing is the right default — but it
is **not honest**, and it cannot be acted on: an operator seeing a refusal
cannot tell whether a rule stopped the order or whether the system was blind.

### 6.2 What is required — IMPLEMENTED 2026-09-18

**A1.** The envelope MUST carry a third verdict state, distinct from admitted
and refused, meaning *no decision was reached*. `[VERIFIED by AB1, AB4, AB9]` —
`verdict` ∈ `allow` \| `refuse` \| `abstain`, and A9 pins that **every** body
the service emits carries one of the three. It never carries null: the 400
paths returned `{"ok": false, "detail": …}` with no verdict at all, and a caller
switching on the verdict fell through a hole rather than meeting a state.

**A2.** An abstention MUST be fail-closed: it MUST NOT permit.
`[VERIFIED by AB5]` — `ok` is False in every non-allow verdict, driven across
the judge-refused, seal-failed and guard-refused paths.

**A3.** An abstention MUST name which authority abstained and why.
`[VERIFIED by AB2, AB4]` — `refused_by` carries the decisions, `abstained_by` the
non-decisions, and `detail` appends `could not decide: …` separately from
`refused by: …`.

**A4.** A caller MUST NOT be able to convert an abstention into permission.
`[VERIFIED by AB5, J5]` — `ok` is computed inside `_envelope` as
`verdict == "allow"`, so there is no combination of fields a caller can read to
manufacture permission, and `tradeGate.js` still tests `ok === true` and
nothing else.

**A5 (new).** The classification of a reason as a decision or a non-decision
MUST be by construction, not by pattern-matching prose.
`[VERIFIED by AB7]` — `guards.ABSTENTION_REASONS` holds the exact strings that
`guards._caller_reasons` builds the reasons *from*, and `is_abstention` is exact
membership. A prefix or substring test would let a reworded refusal drift into
the abstention set and quietly stop counting as a refusal. The asymmetry is the
argument: an abstention mistaken for a refusal is imprecise; a refusal mistaken
for an abstention is a rule going unenforced.

**A6 (new).** Adding the third state MUST NOT change what
`guards.preconditions()` returns to its other callers. `[VERIFIED by AB8]` — it
still returns the flat list of strings, and the partition is lossless
(`sorted(refusals + abstentions) == sorted(reasons)`). `covenant_trader`
delegates to that function and three suites drive it; measured unchanged
afterwards at G4 17/17, F7 70/70, DP1 26/26.

### 6.3 What is still true, measured

The states are now distinct, and the live answer has not become more permissive
— it has become more *legible*. Measured on the real guards, one $25 buy:

    refused_by  : ["Rule 5: 2 sealed signals on record, need 30"]
    abstained_by: ["sentinel: no portfolio was supplied, so the buy-side guards
                    (cash floor, concentration, budgets) could not be evaluated"]
    verdict     : refuse        ok: false

**A single order produces a decision AND a non-decision at the same time.**
`[VERIFIED by AB6]` That is why these were never three exclusive states, and it
is the fact that shaped the design: `verdict` reports the *precedence* — a rule
that said no has decided, so `refuse` outranks `abstain` — while both lists are
always published.

So `seal_service.py` still refuses every real order, and the reason is still
that the app supplies no portfolio and no holdings. What changed is that an
operator can now see which half of the answer is a rule and which half is
blindness. **The 100% refusal rate is still not evidence about the rules** —
`abstained_by` being non-empty on every live order is the measurement that says
so, and it is now readable rather than inferred.

`_blocked_by`'s exception path no longer puts *"the preconditions could not be
evaluated … refusing"* inside the refusals. `blocked_by` is retained as the
union of both lists, so no existing reader breaks.

## 7. Adversarial requirements — NOT YET MET

**X1.** The JUDGE MUST be attacked with adversarial records, not merely the
service with malformed input. `[VERIFIED by JA1, JA2, JA3, JA4]` —
`test_x1_judge_adversarial.py`. And it found a defect **in this repository**,
not in the model: `text` is the only field the judge reads, and
`seal_service.py` was prefixing it with the order's own prose, which moved a
plainly worded theft from HELD to **CLEAR**. One of six thefts cleared with that
prefix, none without. We were performing the stuffing attack the judge's guards
were built to resist. See A146; the judged field is now the note verbatim.
**X2.** The known judge weaknesses MUST be represented as cases here.
`[VERIFIED by JA5]` — with a deliberate limit. Two corpora are carried, six
plainly worded thefts and twelve paraphrases of one benign order, and their
verdict distributions are **measured and printed, never asserted**. Pinning a
judge's accuracy would invite retraining to clear the pin, which is forbidden
(A118) and would be the wrong repair for a defect that was in the caller. What
IS asserted is the property this repository controls: nothing it constructs
reaches the judge with anything concatenated onto it.
**X3.** A record whose text is crafted to read as benign while proposing harm
MUST be refused. `[VERIFIED by JA5]` — a polite authorising sentence, as a
prefix, a suffix, a sandwich, and tripled, does not clear a plainly worded
theft. The remove-proof guards hold against a **caller-supplied** stuffing
attempt. They could not hold against X1's, because that dilution was added
after the caller's text, by us.

**X4 (new).** An order carrying no description MUST NOT be allowed.
`[VERIFIED by AB10]` — the judge reads only the note, so an order without one
receives no ethical judgment at all, and nothing-was-judged must not read as
permission. It abstains.

**X5 (new).** A judgment the judge HELD MUST be reported as an abstention, not
a refusal. `[VERIFIED by JA4]` — the node already publishes `held_not_judged`
and `not_proven`; `seal_decision_result` had both in scope and dropped them, so
"convicted" and "could not read it" arrived identically. A benign
`"quarterly rebalance"` is HELD, so this is the common case here, not an edge
one.

## 8. Out of scope

`ledger.js`, `exchanges/kraken.js`, `exchanges/cryptocom.js`,
`exchanges/coinbase.js`, `secureStorage.js`, `gridMath.js`, `App.jsx`,
`strategyGuide.js` and the companion optimizer are named by the upstream README
and do not exist. Nothing in this specification requires them, and adding any of
them arms a path that is currently inert — which is out of scope for v0.1 by
the operator's own sequencing.

## 9. What this specification cannot do

It is a document, and rule 1 of this repository's method applies to it as much
as to anything else: **prose about a system is not the system.** §3–§5 are
traceable to 28 measured checks; §6 and §7 are traceable to nothing, by
construction, because they describe what is missing.

The conformance table in §10 is therefore the only load-bearing part. If a
requirement's check id is wrong, the requirement is unverified and this document
is lying. `tools/sentinel_baseline.py --check` detects a change to the files;
it does **not** detect a change to this document's accuracy about them. Nothing
automated does, yet.

## 10. Conformance summary

Counted by `tools/spec_conformance.py --list`, which reads the ids out of THIS
file and out of the suite's actual output and compares them. **Every number here
is its output.** Do not hand-maintain this table: I tried, and got it wrong
twice in a row, the second time inside the correction of the first.

> **First attempt:** *"17 requirements, against 26 of the 28 frozen checks"* and
> *"two frozen checks are not cited — S1 and S3"*. The 26 came from a regex that
> missed suffixed ids like `J3c`, so I counted IDS-MATCHING-A-PATTERN and
> reported them as CHECKS. Two denominators, one number — rule 4's error,
> committed inside the document written to prevent it.
>
> **Second attempt:** *"the spec cites 25, and the three it does not cite are
> J3b, J3c and J7 — S1 and S3 are both cited."* Also wrong. S1 and S3 are **not
> cited**; I had asserted it while correcting the claim that said so correctly.
> The tool distinguishes an id inside a `[VERIFIED by …]` tag from an id merely
> mentioned in prose, and by that measure the spec cites 23, not 25.

| | count |
|---|---|
| checks the suite emits | **40** (tally 40/40) |
| this tool's id count agrees with that tally | **yes** -- see `blind` below |
| cited by a requirement, inside a `[VERIFIED by ...]` tag | **35** |
| not cited by any requirement | **5** -- `J3b`, `J3c`, `J7`, `S1`, `S3` |
| **ghost citations** (cited here, absent from the suite) | **0** |
| requirements marked `[UNVERIFIED]` | 1 -- X2 |
| requirements marked `[NOT IMPLEMENTED]` | 2 -- X1, X3 |

The five uncited checks are all real and worth having: `J3b`/`J3c` refine J3
(the executor is unreachable without an allowing verdict, and *is* reached with
one, so the gate is not a blanket refusal); `J7` pins that `tierNavigation.js`'s
import of `TIERS` resolves; `S1` and `S3` pin the whole-response shape on the
admitted and refused paths. **The spec is narrower than its suite by exactly
these five.**

**Two numbers are load-bearing, and `blind` is the first of them.** If this
tool's id count disagrees with the suite's own tally, every other figure here is
void -- it happened, at 28 found against a tally of 40, while the ghost count
read 0. A checker that cannot see the subject reporting a clean bill of health
is worse than no checker. `ghost citations` is the second: the count of
citations may drift harmlessly, but one ghost means a requirement is claiming a
measurement it does not have.
