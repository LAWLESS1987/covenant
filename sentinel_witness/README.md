# Ledger Trading Dashboard

> **CORRECTED 2026-09-17, before the Sentinel work begins. Read this first.**
>
> **This README names 17 files. Twelve of them are not in this folder**, and it
> reports *test results* for several of them — `secureStorage.js | Yes | Full
> encrypt/decrypt round trip`, `gridMath.js | Yes | capital-safety invariant`,
> `exchanges/kraken.js` signing `| Yes |`. A passing test cannot be reported for
> code that is not here. Measured by walking the directory, not by reading the
> table:
>
> ```
> named in README : 17
> present         :  5   automatedLimits.js  AutomatedSetupModal.jsx
>                       Dashboard.jsx  tierNavigation.js  tradeGate.js
> absent          : 12   App.jsx  gridMath.js  ledger.js  secureStorage.js
>                       vite.config.js  src/lib/strategyGuide.js
>                       exchanges/coinbase.js  exchanges/kraken.js
>                       cryptocom.js  recursive_strategy_optimizer.py
>                       src/lib/__tests__/automatedLimits.test.js
>                       src/lib/__tests__/tierNavigation.test.js
> ```
>
> The whole folder is **eight files**, one of which is this README and one a
> `__pycache__` artifact. There is also `seal_service.py`, which the table below
> does not mention at all.
> *(A257, 2026-10-04: true on 2026-09-17; now nine tracked files and the
> `__pycache__`. `order_claims.py` and `verify_record.py` arrived in d5315c3 on
> 2026-09-19; the table names neither. The 17 named / 5 present / 12 absent
> count above still holds.)*
>
> **What this means for the table below.** Its structure is honest — it separates
> "tested" from "cannot be tested without your device", which is the right shape
> and better than most. But a row claiming a green test for an absent file is not
> a weaker claim than an overstatement; it is a claim about nothing. Read every
> `Yes` in it as unverified until the file is in front of you.
>
> Nothing here is armed, and nothing here places an order. That part of the table
> is true and is the part that matters most.
>
> The table is left unedited. This project does not quietly rewrite a document to
> match what it wishes it had said.
>
> **MEASURED 2026-10-15 at eeb2f18: "present" counted file names, not the
> modules the text describes.** Of the five present files, `tradeGate.js` is not
> the module the table, the security model and "not built yet" describe. It
> arrived in 01bab72 on 2026-09-05, written in this repository after the README
> came in with 679a8cf, and it says so in its header. Read, not run (there is no
> JavaScript runtime on this machine):
>
> - It has `enableAutomated()`, which refuses a limit that is not finite and
>   positive, as described. It has no `executeApprovedSignal()`, never mentions
>   the Ledger, and `executeIfAllowed()` hands an allowed order to whatever
>   executor it is given, with no Ledger step. Of an order's size, `gateTrade()`
>   checks only that the amount is finite and positive; `maxPerTradeUsd` and
>   `maxDailyTradesCount` are not re-checked per order there. The caps an
>   order meets are the trader's own, applied by `seal_service.py` through
>   `guards.preconditions`.
> - `automatedLimits.js` does not mirror it exactly: `enableAutomated()` floors
>   the daily count and refuses one below 1, so a daily count of 0.5 passes the
>   form's check and is refused by `enableAutomated()`, and at 2.5 the form's
>   worst case counts 2.5 trades a day where `enableAutomated()` keeps 2.
>   `Dashboard.jsx` also reads `gate.tier` after `gate.enableAutomated(...)`,
>   and calls `gate.getDashboardSnapshot()`, `gate.disableTrading()` and
>   `gate.enableManual()`; this module has none of those three, exports no
>   `tier` and keeps no state, so the `gate` that component is written against
>   is not in this folder.
> - No test here runs JavaScript. No `package.json` is tracked anywhere in the
>   repository, so `npm install` and `npm test` cannot run from it, and
>   `Dashboard.jsx` and `AutomatedSetupModal.jsx` import from `../lib/`, which
>   does not exist. What is checked is `test_sentinel_gate.py`, 41 of 41 on this
>   date: it exercises `seal_service.py` on loopback and reads `tradeGate.js`,
>   walking `executeIfAllowed()` with a refused and an admitted verdict.
>
> The upstream repository, LAWLESS1987/Sentinel-Witness (public; read through
> the GitHub API on this date, at the heads of its seven branches), received
> this README, the same blob as this one's original (`0dd7bceb`), on 2026-08-15
> in 3f9464a, and its only JavaScript files then were the four that are here,
> byte-identical. Its `main` branch (four commits) has never held a
> `tradeGate.js`. Three other branches (`sentinel-trading`,
> `sentinel-operation`, `sentinel-trading-ii6`) hold a copy of this
> repository's own `tradeGate.js` (the same blob, `91d8a1f6`), copied there on
> 2026-10-06 (UTC) in 29c321b. No branch head holds the module the README
> describes, any of the twelve absent files, or a `package.json`. So by the
> module it describes, `tradeGate.js` belongs with the absent: 4 present, 13
> absent. What the sandbox it was built in held cannot be told from either
> repository.

> **Read as an experiment.** *Added 2026-10-03 for clarity, at the operator's
> request ("reflect the scientific method while leaving the substance"). A map
> onto this page; nothing else on it was changed.*
>
> - **Question.** Can a trading dashboard keep every order behind a gate a
>   person controls, so that nothing is placed without that person?
> - **Claim that holds.** Nothing here is armed, and nothing here places an
>   order (the correction above).
> - **What was refuted.** The table's test results for files that are not in
>   this folder: 12 of the 17 files it names are absent, so those rows claim
>   nothing.
> - **Known limits.** No exchange client, signer or credential exists here, so
>   the feature the dashboard is built for cannot run yet.


Phone-first PWA: Ledger hardware wallet + Coinbase/Kraken/Crypto.com, staged
dashboard → manual-approval → automated execution, driven by walk-forward-
validated grid/bracket strategy parameters (see the companion `strategy/`
Python project) with a real-time adaptive layer on top.

## What's actually tested vs. what needs your device

This was built in a sandboxed environment with no access to Coinbase/
Kraken/Crypto.com's APIs, no WebHID, no real Ledger. That shaped what
"tested" can honestly mean here:

| Module | Tested | How |
|---|---|---|
| `secureStorage.js` | Yes | Full encrypt/decrypt round trip, wrong-passphrase-fails-closed, fresh salt/IV per save — real IndexedDB via `fake-indexeddb`, not mocked |
| `gridMath.js` | Yes | Lookahead safety, capital-safety invariant, parity against the Python engine's validated $12 dead-weight case, throttle-never-hits-zero |
| `exchanges/kraken.js`, `cryptocom.js` signing | Yes | Determinism, structural correctness (output length/format), key-order invariance |
| `exchanges/coinbase.js` JWT | Partially | ES256 JWT structure and signature cryptographically verified against a generated key pair — confirms the *mechanism* is right. Does **not** confirm a real Coinbase CDP key imports cleanly; that needs your actual key |
| `tradeGate.js` tier enforcement | Yes | Every limit-rejection path, tier-gating path, and the "no unlimited option" guarantee, via a mock exchange |
| `ledger.js` | No — cannot be | Needs a real browser (WebHID) and a real device |
| Live exchange calls (balances, order placement) | No — cannot be | This sandbox's network can't reach any of the three exchanges |
| UI (`Dashboard.jsx`, `App.jsx`) | No — cannot be | Needs a real browser |

Run `npm test` to re-run everything that *can* run outside a browser.

## Setup

```
npm install
npm run dev      # local dev server
npm run build    # production build, output in dist/
```

### Exchange credentials
- **Kraken**: create an API key with Query Funds + Create/Cancel orders
  permissions (not Withdraw). Enter the key + secret in the app; they're
  encrypted with your passphrase and stored only in this browser's
  IndexedDB.
- **Crypto.com**: same shape (API key + secret), trading permissions only.
- **Coinbase**: create a CDP API key (Advanced Trade). The downloaded
  private key must be PKCS8 PEM (`-----BEGIN PRIVATE KEY-----`). If yours
  says `-----BEGIN EC PRIVATE KEY-----`, convert it first:
  `openssl pkcs8 -topk8 -nocrypt -in your-key.pem -out converted.pem`

None of these should ever have withdrawal permission. This app only ever
needs to read balances and place/cancel limit orders.

## Security model

- **Ledger**: signing happens on-device with a physical confirmation.
  This code never sees a seed phrase or private key — see `ledger.js`'s
  docstring. WebHID (required for the Ledger connection) works in Chrome/
  Edge on desktop and Android; it does **not** work in any iOS browser,
  including Safari-based ones on iPhone. On iOS, this needs a native app
  with Ledger's Bluetooth SDK instead — flagged, not built here.
- **Exchange credentials**: AES-GCM encrypted with a key derived from
  your passphrase (PBKDF2, 210k iterations), stored in this browser's
  IndexedDB. This is real protection against someone reading files off
  disk. It is **not** equivalent to a native app's OS Keychain/Keystore —
  a PWA can't reach either. See `secureStorage.js` and the in-app
  `SecurityNotice` component.
- **Trade execution guardrails**: all enforced in `tradeGate.js`, not
  just documented — automated tier refuses to start without finite,
  positive `maxPerTradeUsd` and `maxDailyTradesCount` (no unlimited
  option), both re-checked on every signal, not just at setup. Every
  execution path requires the Ledger confirmation step; there is no
  code path that skips it.

## What's genuinely not built yet

- **XRP unsigned-transaction-blob assembly.** `tradeGate.executeApprovedSignal()`
  gets all the way to calling the Ledger and reading the address, then
  throws an explicit `not_implemented` error rather than faking a
  completed trade. Turning a `{pair, price, quantity}` signal into the
  actual bytes `signXrpTransaction()` needs to sign (proper XRP Ledger
  transaction encoding, sequence numbers, fees, submission to a node)
  is real protocol work not done in this pass — flagged loudly rather
  than stubbed quietly, per this whole project's standing rule about
  silent failures being the dangerous kind.
- PWA icons (`icon-192.png`, `icon-512.png` referenced in `vite.config.js`)
  aren't generated.
- Only XRP is wired through the UI/gate end-to-end; the strategy guide
  covers DOGE too (see `src/lib/strategyGuide.js`) but the app only
  asks for one asset right now.

## Automated-tier setup

`AutomatedSetupModal.jsx` replaced the earlier `prompt()`/`alert()`
placeholder. Real form, real inline validation (mirrors
`tradeGate.js`'s own `enableAutomated()` check exactly — see
`src/lib/automatedLimits.js` — so the UI never blocks something the gate
would allow or vice versa), and a live "worst-case daily deployment"
figure (`maxPerTradeUsd × maxDailyTradesCount`, related to current USD
balance when known) so the two numbers you're locking in mean something
concrete before you confirm, not just two blank fields. Covered by
`src/lib/__tests__/automatedLimits.test.js`.

While wiring this in, found and fixed a second bug: the "Dashboard" tier
button rendered clickable while at manual/automated tier (stepping down
is deliberately always open, from any tier — see `tierNavigation.js`),
but `handleTierChange` had no branch for it, so tapping it silently did
nothing. Confirmed empirically before fixing (not assumed), and now
covered by `src/lib/__tests__/tierNavigation.test.js`, which asserts the
dashboard-tier case directly rather than just the fields it happened to
break in.

## Re-generating the strategy guide

`src/lib/strategyGuide.js` embeds a snapshot from
`recursive_strategy_optimizer.py` (the Python walk-forward optimizer, in
the companion `strategy/` project — re-run that periodically, it's
designed for it). Either replace the `BAKED_IN_GUIDE` constant with fresh
output, or host the JSON somewhere and call `refreshGuide(url)` so the
app picks up updates without a rebuild.
