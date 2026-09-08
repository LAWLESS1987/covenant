# Sentinel-Witness, joined to covenant -- what is real, 2026-09-05

`github.com/LAWLESS1987/Sentinel-Witness` describes a phone-first trading app:
three tiers (Dashboard, Manual, Automated), a trade gate with no unlimited
option, a Ledger hardware signer, encrypted exchange credentials for Kraken,
Crypto.com and Coinbase, and walk-forward-validated grid strategies.

**What its tree contains** (measured from the GitHub tree, not the README):
`AutomatedSetupModal.jsx`, `Dashboard.jsx`, `automatedLimits.js`,
`tierNavigation.js`, `README.md`, `requirements.txt`, and copies of
`covenant_unified_v8.py` and `covenant_trading_bridge.py` from an earlier
version of this project.

**What the README names that is not there:** `tradeGate.js` (the gate the
other files import from), `ledger.js`, `exchanges/kraken.js`,
`exchanges/cryptocom.js`, `exchanges/coinbase.js`, `secureStorage.js`,
`gridMath.js`, `App.jsx`, `strategyGuide.js`, and the companion optimizer.
The README itself notes the XRP transaction-blob assembly is unimplemented.
So nothing in that repository can place, sign or gate a trade today.

**Written on this branch, 2026-09-05:** `sentinel_witness/tradeGate.js`, the
gate the other files import, with `TIERS`, `enableAutomated()` (no
unlimited option) and `gateTrade()`, which seals every proposed order
through covenant's ethics gate via `sentinel_witness/seal_service.py`, a
loopback service that signs a zero-amount self-send carrying the order and
submits it to the node exactly as the trader does. Only an exact admitted
answer allows; everything else refuses. `test_sentinel_gate.py` pins both
sides. Still absent: the exchange clients, the Ledger signer, the encrypted
storage, the grid math -- the app cannot place an order, and this branch
does not arm anything.

**This branch** carries the four real files under `sentinel_witness/` so
they live beside the live core rather than a stale copy of it. They are
untouched; `tierNavigation.js` still imports `TIERS` from a `tradeGate.js`
that does not exist, and this document says so instead of inventing one.

**How the two designs already agree.** Sentinel-Witness's automated tier
wants a per-trade cap, a daily trade count and the exposure they imply
(`computeMaxDailyExposure`, `computeExposurePctOfBalance`). covenant's
`guards.py` enforces the same shape on the Python side: `PerTradeCap`,
`PerDayCap`, `BuyBudget`, `FiatBuyPermission`, `ReserveFloor` with XRP
hold-only. The tier ladder's rule that stepping down is always one tap is
the same rule as the trader's `TRADER_HALT` file. A future `tradeGate.js`
should call covenant's node (`/transactions`, judged by the sentinel) and
treat any answer but "admitted" as a refusal -- the pattern
`covenant_gate_proxy.py` uses for another runtime.

**What this branch does not do.** It does not arm the trader, install a
credential, or make the app executable.

**Update 2026-09-07 -- the gate now asks the trader's rules, not just the
judge.** When this document was written the sentinel path sealed a decision and
applied none of the trader's other preconditions; see `docs/KNOWN_ISSUES.md`
A61. `preconditions()` has since moved into `guards.py` as the one
implementation, was deleted from `covenant_trader.py`, and
`sentinel_witness/seal_service.py` asks it with `caller="sentinel"`. The answer
is *base reasons + caller reasons*, append only, so this path is provably no
looser than the trader's on the same order.

Two consequences worth stating plainly:

* **It refuses everything today.** A buy needs a portfolio to evaluate the cash
  floor and the budgets; a sell needs holdings and a baseline to clamp against
  the reserve; the app supplies neither. Refusing what it cannot evaluate is
  the design, not a defect. Giving this path a portfolio view is open work --
  and it must not be done by letting the seal service read exchange
  credentials.
* **The seal service is credential-*unused*, not credential-free.**
  `seal_service.seal()` lazily imports `covenant_trader`, which imports
  `venues`, so on its first seal the process can read `~/.coinbase`. There is
  no call site. That is a property of the design, not of the process, and any
  future work here should make it structural.
