# Agentic wallet on Base — design brief

_2026-09-06. Asked: "we need an agentic wallet and an agent to handle the trades whose purpose is
growing wealth for mutual benefit only, probably a branch off sentinel, using any available info."_

Six research agents swept Coinbase's docs, the `coinbase/cdp-sdk` and `coinbase/agentkit` source,
Base docs, open-source agents, incident records and the terms. The verification and synthesis
stages died when the account ran out of usage credits, so this brief is written from the raw
facts. Each is marked **[code]** (read in a repository), **[docs]** (documented by the vendor) or
**[press]** (claimed, unverified). Nothing here has been acted on.

---

## 1. The finding that shapes everything

`coinbase/agentkit`'s own README, Managing Risk section, says verbatim that **AgentKit does not
gate transfers behind human approval, enforce spend caps, or allowlist destinations** [code, last
push 2026-09-03, Apache-2.0, 1,299 stars]. Its only shipped guardrail example is TypeScript
LangChain middleware inside the agent process — which is to say, inside the thing being guarded.
The Python package on PyPI is stale against the repo (0.7.4, uploaded 2025-10-03) [code].

So AgentKit is a **toolbox, not a fence**. Anyone who adopts it and assumes otherwise has an
unguarded wallet. The fence has to come from two places that are not the agent process:

1. **CDP's server-side Policy Engine**, enforced at Coinbase before signing.
2. **The covenant guards**, enforced here before proposing.

That is exactly the architecture already running for the Coinbase trader. The Base limb is the
same shape with a different venue.

## 2. What the fence can actually express

CDP Policy Engine [docs + code, `cdp-sdk/python/cdp/policies/types.py`]:

- Rules evaluated **top-down, first match wins**; **if no rule matches the request is rejected**
  (fail-secure default). Project-level policy evaluated first, then account-level. At most one
  policy of each scope at a time.
- Criteria available to API-key EVM accounts: `EthValueCriterion` (wei, comparison operators),
  `EvmAddressCriterion` (allowlist, max 300 addresses), `EvmNetworkCriterion` (`base`,
  `base-sepolia`, and others), `EvmDataCriterion` (**ABI-aware**: e.g. permit ERC-20 `transfer`
  only to allowlisted addresses and only below an amount), `NetUSDChangeCriterion` (mainnet only),
  plus message and typed-data criteria.
- **No native per-week cumulative cap.** The only periodic allowance is **Spend Permissions**,
  enforced onchain by a manager contract on Base, and documented as supported on CDP Smart
  Accounts owned by CDP Server Wallets [docs]. Create and revoke are user operations that cost gas.

**Consequence for the $100/week rule:** the weekly cap cannot be delegated to Coinbase. It stays
where it already is — `guards.WeeklyBudget` on this machine — with the policy engine holding the
per-transaction ceiling, the network, and the destination allowlist beneath it. Two independent
fences, neither sufficient alone, which is the correct shape.

## 3. The security finding that decides key layout

CDP uses two operator-held secrets [code, `cdp-sdk/python/cdp/auth/utils/jwt.py`]:

- **Secret API Key** (Ed25519 recommended) → mints a ~2-minute Bearer JWT.
- **Wallet Secret** (ECDSA P-256, generated in the portal) → mints an ES256 `X-Wallet-Auth` JWT
  carrying a SHA-256 of the sorted request body.

**The gap:** which requests require the Wallet Secret is decided **client-side**, by a path
predicate in the SDK (`_requires_wallet_auth` in `http.py`) [code]. Coinbase's documented
mitigation for policy management is **API-key scoping, not Wallet-Secret gating** [docs]. A
research agent's threat matrix concluded the same.

**Therefore:** use **two separate API keys**. One narrow key for the agent that can sign and send
but **cannot manage policies**. A second key, never on the trading machine, for changing policy.
An attacker who takes the agent's key then cannot widen the fence it operates inside. Coinbase's
own hardening guidance says to use separate keys per environment and restrict by IP [docs] — the
existing Coinbase key here is already IP-allowlisted, and the same should apply.

## 4. Costs, and why they are not the constraint

- Wallet operations: **first 5,000 per month free**, then **$0.005** each. A send counts as 2, a
  signature 1, a policy evaluation 1 [docs]. At a few trades a week this is entirely inside the
  free tier.
- Swaps go through the **CDP Trade API, which is 0x-powered DEX aggregation** [docs]. Quotes carry
  `fees.gasFee` and `fees.protocolFee`; `slippageBps` defaults to **100 (1%)** and is capped at
  10000 [code]. **1% default slippage is far looser than the 0.6% maker fee** being paid on
  Coinbase — it must be set down explicitly, and the covenant should refuse a quote whose implied
  cost exceeds the venue it is replacing.
- **Permit2 allowance is mandatory for ERC-20 sells** [code]. That is a one-time approval per
  token and a real step, not a detail.
- Gas on Base can be sponsored by the **CDP Paymaster (Base mainnet and Base Sepolia only)**
  with Smart Accounts [docs].

## 5. Getting money there

Coinbase-account → Base withdrawal is the **Coinbase App API**
(`POST /v2/accounts/:account_id/transactions`), **not Advanced Trade** [docs]. Advanced Trade key
permissions are `can_view`, `can_trade`, `can_transfer` — and the key in use here has **no
transfer scope**, deliberately. Moving funds to Base therefore stays a **manual operator action**
unless that changes, which is the right default and should not change without a decision.

## 6. What "growing wealth" can honestly mean here

No timing edge has replicated in this project's own out-of-sample testing, and Rule 5 stands at
0/30. So the Base agent's first mandate is **not** to predict. It is:

- **Deploy on a schedule** (Rule 6 already does this on Coinbase).
- **Earn on idle USDC** rather than let it sit. Any specific yield figure must be measured before
  it is quoted; do not import a number from marketing.
- **Reduce cost**, which is measurable today: 1% default slippage versus 0.6% maker fee is a real
  and quantifiable difference, and any swap that cannot beat the Coinbase path should not happen.

Sobering evidence from the sweep: a marketed "agent grows your USDC on Base" product with claimed
assets under agent [press, unverified]; a **May 2026 wallet-drain incident** where an agent
auto-provisioned wallets and was exploited [docs, OECD.AI incident record + SlowMist analysis];
and an arXiv study measuring third-party LLM API routers leaking or altering traffic [docs]. Every
one of these is an argument for the fence being outside the agent process, and for the agent's
key holding only what it may lose.

## 7. Phases

Each phase closes on itself and is verifiable before the next begins. Nothing moves value until
the last.

1. **Read-only.** `cdp-sdk` installed; create a Base **Sepolia** account; read balances; write
   nothing. Proves credentials and the two-JWT flow.
2. **The fence, first.** Author the project-level and account-level policies — network `base`,
   destination allowlist, per-transaction ceiling — and **prove they refuse** by attempting a
   transaction outside each rule. A fence is only real once you have watched it stop something.
3. **Testnet round trip.** Faucet, one swap on Base Sepolia through the Trade API, sealed through
   the existing sentinel and recorded. No mainnet key present on the machine.
4. **Mainnet, minimum size.** A single operator-approved swap at the smallest size the venue
   accepts, with slippage set explicitly and the cost compared against the Coinbase path.
5. **Autonomy, earned.** The agent runs unattended inside the fence, with its own Rule 5 ledger
   sealing each decision before the outcome and scoring it after. The tier widens only on the
   record, never on a request.

## 8. The operator's hands

Every one of these needs his keys or his judgement, and none can be delegated:

- Accept the CDP terms (an individual may) [docs] and create the **two** API keys with the split
  scopes above.
- Generate the Wallet Secret in the portal; keep it off the trading machine wherever possible.
- Author and apply the policies, and decide the allowlist and the ceiling.
- Move any funds from Coinbase to Base. The trading key has no transfer scope by design.
- Decide when a tier widens.

## 9. What would make me stop

- If the policy engine cannot be shown refusing a real transaction in phase 2.
- If the agent's API key turns out to be able to modify its own policy.
- If measured swap cost on Base does not beat the Coinbase maker path for the sizes in question,
  in which case the whole limb is a fee machine and should not exist.
- If any design step requires the agent to hold a secret it does not need, or requires disabling a
  guard rather than satisfying it.

## 10. Open questions

Slippage settings that are actually achievable on Base for the assets in question; whether Spend
Permissions work for an API-key server wallet without a Smart Account; real, measured USDC yields
on Base and their counterparty risk; and whether the CDP terms constrain an automated agent beyond
the general market-manipulation prohibition [docs].
