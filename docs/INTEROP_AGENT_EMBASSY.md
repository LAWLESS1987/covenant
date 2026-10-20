# Interop & credit: Agent Embassy (verifiable agent-work receipts)

**Credit where due.** This note records a design we can borrow from, and whose author we credit:
**Agent Embassy** — by **nootxlm** ("1OF1 · Agent Embassy") on the Hugging Face forums, site **aemb.pro**,
Space `huggingface.co/spaces/1OF1-Verified/agent-embassy`, on-chain reputation **ERC-8004 agentId 167279 (Base)**.
We found it because nootxlm engaged in good faith on our threads (the Confidence Trap and others); borrowing their
design openly, with attribution, is the good-faith-alliance standard applied to ourselves.

## What they built (verified from a live receipt, 2026-10-20)

A **portable, third-party-verifiable Outcome Receipt** for a paid agent task. From receipt
`emb_84d3f5d475dd435db026f4f8` (tool `compute_spot_prices`, status delivered):

- **Payment:** $0.25 **USDC on Base** (`eip155:8453`), authorised by an **x402** facilitator.
- **Signature:** the receipt is signed **eip191-personal-sign** by a dedicated signer
  (`0x0c37…289F`), separate from the payment wallet.
- **Receipt hash:** SHA-256 of the **canonical receipt JSON** (the proof stage excluded).
- **Verification (free, trustless):** recompute the canonical SHA-256, `ecrecover` the signer from the 65-byte
  signature, and compare it to the signer published at **`/.well-known/embassy-signer.json`**. No need to trust
  the server — anyone can check a receipt from the receipt alone.
- **Honest scope, stated on the receipt:** *"proof of request + payment + one machine check at the recorded time,
  not of ongoing truth."* Same discipline covenant_earn already holds (a receipt "never says certified/attested/
  verified; it says what it checked and what it cannot see").
- **Reputation:** the call is recorded to an **ERC-8004 Reputation Registry** entry for the agent.

## Convergence with covenant_earn (already ours)

`covenant_earn.py` is a close cousin, built independently: x402 protocol v2 over HTTP, buyer-signed **EIP-3009**
USDC payments, **USDC on Base** (`MAINNET = eip155:8453`), per-job receipts carrying the **sha256 of each file
read**, the same **honest-scoping** rule, a **maker-credit** field ("made by … credited in every receipt"), and a
receipt **hash-chained to a public-method ledger so the check itself can be checked**.

The difference is **portability of trust**:
- covenant_earn: a receipt is verifiable by replaying it against covenant's **public-method ledger** — you need
  access to that ledger.
- Agent Embassy: a receipt is verifiable **from itself** — a portable eip191 signature + a published signer at a
  well-known path. No server, no ledger access.

## The borrowable upgrade (mapped onto covenant_earn)

Add a **portable seller signature** to each covenant_earn receipt, so a buyer can verify it offline:
1. Define a **canonical receipt JSON** (stable key order, the proof/signature fields excluded) and its SHA-256
   (covenant already computes sha256 of inputs/outputs — extend to the whole receipt).
2. Sign that hash with a **dedicated receipt signer** (eip191-personal-sign), distinct from any payment/wallet
   key — as Agent Embassy does.
3. Publish the signer at **`/.well-known/covenant-signer.json`** for discovery.
4. Optionally record the job to an **ERC-8004** reputation entry on Base.
5. Keep the honest-scope line verbatim; keep the existing maker-credit field (which already lets us credit an
   external maker like Agent Embassy on receipts that build on their design).

This also makes covenant able to **verify Agent Embassy receipts** (recompute hash, ecrecover, check their
`/.well-known/embassy-signer.json`) — real interop, both directions.

## What is done here vs what needs the operator's word

- **Done autonomously (this note):** the credit, the record of convergence, and the concrete design — no keys, no
  money, no new trust.
- **Needs the operator's approval (money/keys are `NEVER_AUTOMATIC`; see test_na1_never_automatic.py):**
  - creating or using a **receipt-signing key** (a `key`/`consent` subject the self-heal engine itself may never
    auto-touch);
  - adding an **EVM crypto dependency** (e.g. `eth-account`/`coincurve`; none is installed) to the money-adjacent
    `covenant_earn` path;
  - any change to the **earn trust model** or on-chain reputation.
  These are his, by the same gate NA1 pins. This note exists so the work is ready the moment he says go.

## Standing

Borrowed openly and credited, per the good-faith-alliance principle. If the design is used, the maker-credit field
names **Agent Embassy (nootxlm)** on the relevant receipts, and this note is the provenance.
