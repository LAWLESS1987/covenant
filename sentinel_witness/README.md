# Ledger Trading Dashboard

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
