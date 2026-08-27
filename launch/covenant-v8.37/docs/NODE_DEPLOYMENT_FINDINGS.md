# Multi-node deployment — tested findings, 2026-08-20

Three live nodes, real kills. Four of these explain long-standing flakiness.

## 1. Port arithmetic (the big one)

`--port N` occupies **three** ports: `N` (HTTP API), `N+1` (P2P), `N+11` (bridge).

- **Nodes must be ≥12 apart.** 5001/5002/5003 collides: B's P2P (5003) takes
  C's API port. C fails with `Address already in use` — printed *after* its
  startup banner, so it reads as a healthy start. Use 5001 / 5021 / 5041.
- **`--peers` takes the peer's P2P port** (their API port **+1**), while
  `--port` takes the API port. Same-looking numbers, different meaning.

Getting this wrong sends peer JSON to the peer's Flask port. Flask answers
`400 Bad request version ('5003}')` and the *sender* sees nothing. Nodes look
peered; they aren't. This is almost certainly the source of past "mutual
peering" trouble.

Correct form:
```
--port 5001 --peers 127.0.0.1:5022,127.0.0.1:5042
```

## 2. A fresh chain has zero spendable supply

Founder ledger immediately after minting genesis:

```
genesis_mint   +1000.00
stake_lock     -1000.00
                   0.00
```

The genesis mint is entirely stake-locked. Every `send` returns
`Insufficient balance: have 0.00`, and `/mine` needs a pending transaction — so
no block past genesis is reachable. Reads as a broken ledger.

There **is** a `/unstake` route. Unstaking is a **mandatory undocumented first
step** on any new chain.

## 3. The ethics gate needs two env vars

`COVENANT_INSECURE_MOCK_JUDGE=1` alone still rejects everything; `mock` is a
provider that must also be selected:

```
COVENANT_INSECURE_MOCK_JUDGE=1
COVENANT_JUDGE_PROVIDERS=mock
```

Testing only — the code's own docstring notes adversarial transactions pass it.

## 4. `covenant_client.py` argument order (fixed)

`--port`/`--key` sat on the top-level parser, so `client.py mine --port 5001`
died with "unrecognized arguments" — reads as a broken tool rather than a typo.
It silently ate five mining attempts before the cause was clear. Fixed with an
argv hoist so both orders work.

## 5. The cloud sandbox cannot host a node (tested, not assumed)

- no inbound connectivity
- no general outbound — `1.1.1.1:53` times out; only proxied HTTPS to
  allowlisted hosts succeeds
- ephemeral container, reclaimed on inactivity or session end

"Cloud, PC, phone" is really **PC and phone** unless a real always-on VPS with a
public IP is rented. Do not present a sandbox node as a survival node.

## Kill-test results

| test | result |
|---|---|
| three nodes adopt the same canonical genesis tip | PASS (identical hash) |
| kill one node | PASS — survivors keep serving, no cascade |
| restart killed node | PASS — rejoins with correct chain, unattended |
| kill the miner | PASS — chain intact on survivors |
| block propagation after a kill | **UNPROVEN** — blocked by finding #2 |

Replication and restart survive. Propagation under failure is untested because
no second block could be minted. Closing that needs `/unstake` first.

## Phone-to-PC networking

Cellular puts the phone behind carrier-grade NAT: it cannot accept inbound and
cannot reach a home PC. Same-wifi peering works over the LAN. Off-wifi the phone
node still runs and keeps its own copy — survival holds, sync does not.

Fix for peering from anywhere: **Tailscale** on both, use the `100.x.y.z`
addresses as peers. No code change required.

## What "survival" means precisely

Three copies means the **data** survives one machine dying — real and worth
having. It is **not** consensus security: three nodes one person controls are
three copies, not three independent witnesses. Accurate description is **backup
with automatic catch-up**.
