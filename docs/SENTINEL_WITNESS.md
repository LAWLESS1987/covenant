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

**Update 2026-10-05 -- the trading layer moved to Sentinel-Witness: copy, prove,
then retire.** The operator: "move all info that was here regarding trading and
move it to the actual sentinel witness branch intergrate and rewire to actually
trade". Asked how, he chose to build on Sentinel-Witness's `codex/ethics-gate-repair`;
to copy, prove, then retire; and "Trade now within caps" (Rule 5 off; $25/order,
$50/day, 2 orders/day and the XRP/LINK/HBAR floors kept).

* **Where.** `github.com/LAWLESS1987/Sentinel-Witness`, branch `sentinel-trading`
  (29c321b), built on `codex/ethics-gate-repair` with that repository's `main`
  merged in so its `COWORK_TOMBSTONE.md` stays. Its `trader/` is this repository's
  trader, guards, venues, Rule 5 ledger, strategy research, `realdata/` and trading
  docs at 260f3dd, tracked files only, each listed with its SHA-256 in
  `trader/COPIED_FROM_COVENANT.tsv`. `tradeGate.js` went to its root, where
  `tierNavigation.js` already imports it.
* **Sentinel-Witness executes, covenant witnesses.** Its `trader/witness.py` runs
  three things *in this folder, with this folder's python*: the seal
  (`covenant_trader.seal_decision_result`), the day's approval
  (`covenant_daily_plan.gate_reasons`), and the reserve floors (`private/RESERVE.json`,
  read in place, never copied). A `TRADER_HALT` dropped here stops it too. Without
  this folder configured as its `covenant_home`, or without the floor file, it
  runs no cycle at all.
* **Rule 5 is waived there, not here.** Waived by a record in its local config,
  which is printed and sealed (`"waived": "yes"`) every cycle. Covenant's own
  trader is unchanged: armed, Rule 5 in force, so it places nothing. The
  Sentinel-Witness copy is disarmed until the operator runs its
  `SENTINEL_ARM_AND_RUN.bat`.
* **Proved in plan-only, 2026-10-05, from the Sentinel-Witness folder**, on scratch
  copies of the shared state: balances read, this repository's floors applied, the
  decision admitted and mined by node A (tx `49bfef21...`). It planned no orders.
  Cash is below the 10% floor, XRP is at its frozen floor, `contribution_symbols`
  is empty, and no daily plan has been approved here since 2026-09-19.
  **A reader cannot check these four facts** (II.6). They rest on the exchange
  account, on `private/RESERVE.json` and on the gitignored approvals ledger, and
  none of those is ever published. What is public is the code that reads them,
  and the sealed decision's commitment on the operator's node.
  **RETRACTED in part (SW-CONTRIB-2026-10-06, docs/RETRACTED.json):** the
  `contribution_symbols` fact is true, but it was not a reason. An empty list
  restricts nothing. `plan()` reads it as "every held asset under the cap and above
  its line", and the weekly contribution was blocked by cash alone. The document as
  first written is on branch `sentinel-witness-contribution-claim-as-written-2026-10-06`.

**What retiring this repository's copy has to do first.** Sentinel-Witness's
seal call and this repository's `sentinel_witness/seal_service.py` both import
`covenant_trader`. Retiring `covenant_trader.py` here means first moving
`seal_decision_result` into a module that stays, and pointing both callers at it.
Otherwise every Sentinel-Witness seal fails. It fails closed, so no order goes
live, but the trader is dead. Then disarm this copy, move the `CovenantTrader`
scheduled task to Sentinel-Witness, and move the files aside under `.trash/`
with this record. Not before the Sentinel-Witness copy has run live.

**Not done, and why (2026-10-05).** A request pasted earlier the same day asked
to delete `sentinel_witness/` and the "stale copies" of `covenant_unified_v8.py`
and `covenant_trading_bridge.py` from this repository's root. Here they are not
stale. `covenant_unified_v8.py` is the live node: 734,511 bytes, changed that
day, and referenced by 185 tracked files. `seal_service.py` was running and is
tended by the watchdog. None of it was deleted. In Sentinel-Witness those two
files *are* older copies, but the `codex/ethics-gate-repair` work the operator
chose to build on uses them (the verified profit bridge and its tests), so they
stay there too. That README now says the trader does not use them.
