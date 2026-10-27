# Three nodes, and what "survival" actually buys you

Tested today on three live nodes with real kills. Findings first, because four
of them explain failures you've already hit.

---

## 1. Port arithmetic — this is what was breaking your multi-node runs

A node started with `--port N` does not use one port. It uses **three**:

| | |
|---|---|
| `N` | HTTP API (what `covenant_client.py --port` talks to) |
| `N+1` | **P2P** — peer traffic |
| `N+11` | bridge |

Two consequences, both of which bit me today:

**Nodes must be at least 12 apart.** Running A on 5001, B on 5002, C on 5003
means B's P2P port (5003) collides with C's API port (5003). C died with
`Address already in use` — but it printed that *after* its startup banner, so it
looked like it had started fine. Use **5001, 5021, 5041**.

**`--peers` takes the peer's P2P port, not its API port.** This is the one that
silently poisons everything. `--peers 127.0.0.1:5002` when you meant "node B on
5001" sends peer messages to B's *Flask* port. Flask tries to parse the JSON as
an HTTP request line and answers `400 Bad request version ('5003}')`. No error
surfaces on the sending side. The nodes look peered. They are not.

```
node A: --port 5001    peers reach it at 5002
node B: --port 5021    peers reach it at 5022
node C: --port 5041    peers reach it at 5042

start:  --port 5001 --peers 127.0.0.1:5022,127.0.0.1:5042
```

## 2. A fresh chain has zero spendable supply

Every `send` returned `Insufficient balance: have 0.00` even for the founder who
had just minted genesis. The ledger explains it:

```
genesis_mint   +1000.00
stake_lock     -1000.00
                   0.00
```

The genesis mint is **immediately and entirely stake-locked**. So on a brand-new
chain nobody can spend anything, and since `/mine` needs a pending transaction,
no block after genesis can ever be produced. It reads exactly like a broken
ledger.

It isn't — there's a `/unstake` route. But **unstaking is a mandatory first step
on any new chain** and nothing says so. Do that before expecting a single
transaction to work.

## 3. The ethics gate needs two env vars, not one

`COVENANT_INSECURE_MOCK_JUDGE=1` alone still rejects every transaction, because
`mock` is a *provider* that must also be selected:

```
COVENANT_INSECURE_MOCK_JUDGE=1
COVENANT_JUDGE_PROVIDERS=mock
```

Testing only. It reduces the ethics gate to keyword matching — the code's own
docstring says adversarial transactions pass it.

## 4. The cloud leg does not exist

I tested this rather than assumed it. This sandbox has:

- **no inbound connectivity** at all
- **no general outbound** — `1.1.1.1:53` times out; only proxied HTTPS to
  allowlisted hosts works (that's how the price fetches get through)
- **an ephemeral container**, reclaimed after inactivity or when the session ends

So a node here cannot peer with anything, and would evaporate anyway. **"Cloud,
PC, phone" is really "PC and phone"** unless you rent a real always-on VPS with
a public IP — about $5/month. If you want the third leg to be real, that's the
purchase. I'd rather say that than hand you a node that looks like it's running.

---

## What the kill test actually proved

Three nodes, correct ports, shared canonical genesis:

| test | result |
|---|---|
| all three adopt the same genesis tip | **pass** — identical hash on all three |
| kill one node | **pass** — the other two keep serving, no cascade |
| restart the killed node | **pass** — rejoins, correct chain, unattended |
| kill the miner | **pass** — chain intact on the survivors |
| blocks propagating after a kill | **not proven** — blocked by finding #2 |

So: **replication and restart survive. Block propagation under failure is still
unproven** — not because it failed, but because I couldn't mint a second block
to test it with. That gap is honest and it's the next thing to close.

---

## On the road: your phone can't reach your PC

Your phone on cellular sits behind carrier-grade NAT. It cannot accept incoming
connections and cannot reach your home PC. On your home wifi they peer fine over
the LAN. Off it, they don't — the phone node keeps running and keeps its own
copy (survival still works), but it won't sync until you're home.

The fix, if you want them peered from anywhere: **Tailscale**. Free for personal
use, apps for Android and Windows, gives every device a stable `100.x.y.z`
address that works over cellular. Put those addresses in `node-peers.conf` and
the existing code needs no changes at all.

---

## What survival means here, precisely

Three copies of the chain means the **data** survives any one machine dying.
That is real and it is worth having.

It is not consensus security. Three nodes you control are three copies, not
three independent witnesses — anyone who controls you controls all three. And
with the whole genesis supply stake-locked, there is currently nothing on the
chain to protect.

The honest summary: this is **backup with automatic catch-up**. That's a genuinely
useful property. It just isn't the same thing as a decentralised network, and I'd
rather you hear that from me than discover it later.
