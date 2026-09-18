# Sentinel-Witness — the frozen baseline, 2026-09-18

Step 1 of the operator's order of work, 2026-09-18: *"first freeze the current
baseline."* Everything after this is measured against these bytes and these
numbers. Nothing here is a plan and nothing here is a claim about quality — it
is a record of what exists at `fa13845`, so that any later statement about
progress can be checked rather than believed.

Re-runnable: `python tools/sentinel_baseline.py --check`

> **RE-FROZEN 2026-09-18, later the same day. Everything below describes the
> ORIGINAL freeze and is kept as written**, because a baseline that is edited
> to match the present is not a baseline. What changed, and why:
>
> Steps 6 and 3 of the order of work (abstention, and the witness/judge
> separation) deliberately altered three of the twelve files:
> `seal_service.py` 8,305 -> 12,261 bytes, `tradeGate.js` 5,053 -> 6,228,
> `test_sentinel_gate.py` 16,829 -> 24,867. The gate suite went 28/28 -> 40/40.
> Total 100,369 -> 113,538 bytes. `tools/sentinel_baseline.py` flagged all
> three as UNACCOUNTED FOR -- doing its job -- and carries the new digests;
> the accounting is the commit that moved them.
>
> **The one claim below that is now FALSE is called out in place:** §"What
> those 28 cover" said there is no abstention state anywhere in this path.
> There is, as of today. Everything else here still holds, including the part
> that matters most -- nothing in this path attacks the judge.

---

## The bytes

Twelve tracked files, 100,369 bytes, at commit `fa13845`.

| file | bytes | sha256 |
|---|---|---|
| `sentinel_witness/AutomatedSetupModal.jsx` | 9829 | `3d6b422ec091189e…` |
| `sentinel_witness/Dashboard.jsx` | 7458 | `18728c6119331a92…` |
| `sentinel_witness/README.md` | 8254 | `66b3fdb14d97f101…` |
| `sentinel_witness/automatedLimits.js` | 2101 | `d11adc598fb6465f…` |
| `sentinel_witness/seal_service.py` | 8305 | `f4a1391eb04b3422…` |
| `sentinel_witness/tierNavigation.js` | 1864 | `0283197c44b96d4b…` |
| `sentinel_witness/tradeGate.js` | 5053 | `6abcca43d2bcbcfe…` |
| `test_sentinel_gate.py` | 16829 | `12cc9e657f37c8b9…` |
| `test_sentinels.py` | 968 | `f8c1ea4e1e026cff…` |
| `test_g6_sentinels_fail.py` | 7138 | `b0cbebc02d4d0e6b…` |
| `covenant_sentinels.py` | 28343 | `a762cd17624de25f…` |
| `docs/SENTINEL_WITNESS.md` | 4227 | `a829e95279cf9050…` |

Full digests are in `tools/sentinel_baseline.py`, which is the checkable form;
the table is the readable one. Of these, four are the ORIGINAL upstream UI files
(`AutomatedSetupModal.jsx`, `Dashboard.jsx`, `automatedLimits.js`,
`tierNavigation.js`) and are untouched since 2026-09-05.

## The numbers, measured today and not recalled

    test_sentinel_gate.py     28/28 passed
    test_sentinels.py         18/18 passed  (offline; no anchor written, nothing repaired)
    test_g6_sentinels_fail.py 11/11 passed

**What those 28 cover**, so the number is not mistaken for coverage it does not
have. S1–S19 drive the Python seal service; J1–J7 drive the JS gate:

* **the envelope, partly** — S11 an `admitted (evicted …)` answer is an
  admission; S12 the admission is read as a FIELD so key order cannot decide it;
  S13 a 200 carrying some other admission string is not admitted; J5 only an
  exact admitted answer allows.
* **fail-closed, partly** — S4 a sealer that raises is a refusal, never an
  allowance; S14 an ADMITTED seal is not sufficient on its own, the trader's
  preconditions still run; J4 every failure branch in `gateTrade` is a refusal.
* **input attacks on the SERVICE** — S5 bad side, S6 NaN amount, S7 non-JSON,
  S8 oversized body, S9 only `/seal` exists, S10 loopback only.
* **one implementation** — S19 there is one `preconditions` and the trader
  delegates to it; S18 caller reasons are append-only, so this path cannot be
  looser than the trader's.

**What they do NOT cover, and this is the part that matters for the order of
work:** none of these attack the JUDGE. S5–S8 attack the service's parser.
Adversarial pressure on the judging itself lives in other suites entirely, and
the known results there are refutations, not reassurance — a polite sentence
once cleared 11 of 19 thefts. There was also **no abstention state anywhere in this path** when this was
written: every answer was admitted or refused, so "the judge could not tell"
resolved to a refusal by accident of structure rather than by design.
**CORRECTED the same day** -- `verdict` now carries `allow`/`refuse`/`abstain`,
pinned by AB1-AB9, and the measured live answer separates "Rule 5 refused" from
"no portfolio was supplied, so this could not be evaluated". The sentence is
left standing because it is what made the work necessary.

## What is absent

`Sentinel-Witness` upstream still names modules its tree does not contain:
`ledger.js`, `exchanges/kraken.js`, `exchanges/cryptocom.js`,
`exchanges/coinbase.js`, `secureStorage.js`, `gridMath.js`, `App.jsx`,
`strategyGuide.js`, and the companion optimizer. `tradeGate.js` and
`seal_service.py` were written here on 2026-09-05/07 and are the only executable
gate that exists.

**Nothing in this path can place, sign or gate a real trade today**, and the
freeze is not a step toward arming it. `tierNavigation.js` imports `TIERS` from
`./tradeGate.js`, which now resolves (J7); that is the only upstream import that
does.

## What a freeze is for

So that the next five claims are falsifiable. If `seal_service.py` changes, the
check says so; if `test_sentinel_gate.py` reports 31/31 next week, the delta is
three checks and they can be named. The failure this guards against is the one
this repository keeps meeting: a number that moved for a reason nobody recorded,
read later as progress.

It does **not** freeze the code against editing. It freezes the RECORD, so an
edit has to be accounted for.
