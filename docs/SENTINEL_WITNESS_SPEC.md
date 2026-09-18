# Sentinel-Witness — specification v0.1

Step 2 of the operator's order of work, 2026-09-18. This is the artifact the
remaining steps are checked against: separating the witness from the judge,
building the decision envelope, attacking the judge, adding abstention, and
testing fail-closed all need a written thing to be measured against, or each
one is a matter of opinion afterwards.

**Status: v0.1, and DESCRIPTIVE WHERE IT SAYS SO.** Every requirement below is
marked with what actually verifies it today. A requirement with no check is
marked `UNVERIFIED` and is a claim about intent, not about the system. Three
requirements are marked `NOT IMPLEMENTED` — they are holes this document exists
to name, not features it is announcing.

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
  and holdings supplied to it, and when those are absent it must abstain (§6),
  which today it does not (§6.3).

## 2. Normative language

**MUST** / **MUST NOT** — a violation is a defect, and a check should exist.
**SHOULD** — a violation needs a recorded reason.
**MAY** — permitted, no obligation.

Each requirement carries a tag: `[VERIFIED by <check>]`, `[UNVERIFIED]`, or
`[NOT IMPLEMENTED]`. Check ids are from `test_sentinel_gate.py`, measured at
28/28 on 2026-09-18.

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
`[UNVERIFIED]` — true by construction today (nothing reads the chain back to
decide), but nothing checks that it stays true. **This is the gap step 3 should
close, and it is a check, not a refactor.**

**W3.** The JUDGE's verdict and the GUARD's verdict MUST be separately legible
in the answer. `[VERIFIED by S14, S15]` — `sealed` carries the judge, and
`blocked_by` is a list carrying the guards' reasons; `detail` names them.

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
| `ok` | bool | **the only field a caller may act on.** `sealed AND NOT blocked_by` |
| `admission` | string | the judge's verdict, normalised: `"admitted"` \| `"refused"` |
| `sealed` | bool | the judge admitted the record to the chain |
| `blocked_by` | string[] | the guards' reasons; `[]` means the guards refused nothing |
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
**F6.** Guards that cannot be evaluated MUST refuse. `[VERIFIED by S15]`
— but see §6.3: today this refusal is indistinguishable from a judged refusal,
which is the defect.

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

### 6.2 What is required

**A1.** The envelope MUST carry a third verdict state, distinct from admitted
and refused, meaning *no decision was reached*. `[NOT IMPLEMENTED]`
**A2.** An abstention MUST be fail-closed: it MUST NOT permit.
`[NOT IMPLEMENTED]` — currently satisfied only because everything refuses.
**A3.** An abstention MUST name which authority abstained and why.
`[NOT IMPLEMENTED]`
**A4.** A caller MUST NOT be able to convert an abstention into permission.
`[NOT IMPLEMENTED]`

### 6.3 The current state, measured

`seal_service.py`'s own docstring records it: *it refuses everything today*,
because a buy needs a portfolio to evaluate the cash floor and the budgets, a
sell needs holdings and a baseline to clamp against the reserve, and the app
supplies neither.

**So every refusal this path produces today is semantically an abstention
reported as a refusal.** That is the safe direction, and it is why nothing is
armed. But it means the gate's 100% refusal rate is currently evidence of
*nothing at all* about the rules — and a later change that made the rules
evaluable would flip a large number of answers with no test able to tell the
difference between "now correctly allowed" and "now wrongly allowed".

Additionally, `_blocked_by`'s exception path returns the string *"the
preconditions could not be evaluated … refusing"* **inside `blocked_by`** — an
abstention wearing a guard refusal's clothes. `[NOT IMPLEMENTED]` A1 would move
it out.

## 7. Adversarial requirements — NOT YET MET

**X1.** The JUDGE MUST be attacked with adversarial records, not merely the
service with malformed input. `[NOT IMPLEMENTED]` — S5–S8 attack the parser.
Nothing in the frozen suites attacks the judging.
**X2.** The known judge weaknesses MUST be represented as cases here.
`[UNVERIFIED]` — the standing result elsewhere is a refutation, not
reassurance: a polite sentence once cleared 11 of 19 thefts. Until X1 exists,
this path inherits that weakness undocumented.
**X3.** A record whose text is crafted to read as benign while proposing harm
MUST be refused. `[NOT IMPLEMENTED]`

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
| checks the frozen suite emits | **28** (tally 28/28) |
| cited by a requirement, inside a `[VERIFIED by …]` tag | **23** |
| not cited by any requirement | **5** — `J3b`, `J3c`, `J7`, `S1`, `S3` |
| **ghost citations** (cited here, absent from the suite) | **0** |
| requirements marked `[UNVERIFIED]` | 2 — W2, X2 |
| requirements marked `[NOT IMPLEMENTED]` | 6 — A1–A4, X1, X3 |

The five uncited checks are all real and worth having: `J3b`/`J3c` refine J3
(the executor is unreachable without an allowing verdict, and *is* reached with
one, so the gate is not a blanket refusal); `J7` pins that `tierNavigation.js`'s
import of `TIERS` resolves; `S1` and `S3` pin the whole-response shape on the
admitted and refused paths. **The spec is narrower than its suite by exactly
these five.** When §3–§5 are next revised they should each get a requirement, or
that gap should be stated as deliberate.

**A ghost-citation count of 0 is the load-bearing number in this document.** It
is the only thing standing between §3–§5 and §9's warning that prose about a
system is not the system. The count of *citations* can drift harmlessly; a
single ghost means a requirement is claiming a measurement it does not have.
