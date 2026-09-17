# Running a covenant node on your own PC

*Written 2026-09-16, closing KNOWN_ISSUES A18. Before this, every PC launcher,
every gate and the DEPLOYMENT.md install section assumed the owner's machine.
There was no page for anyone else, which is a strange gap in a project whose
whole ask is "please be the second operator".*

This page is for a **second operator**: someone who is not the owner, on their
own hardware, who wants a node that agrees with the chain and can be checked.

---

## Before you start, what this costs you

- A Python 3.11+ environment and about 200 MB.
- One inbound port if you want two-way peering, or Tailscale if you would
  rather not touch your router.
- Electricity, and your attention when it breaks.

What it does **not** cost you: no keys leave the machine, no telemetry, no
account anywhere. The one exception is the GitHub judging rung, which is off
by default — see *What leaves your machine* in [`PARTNER.md`](PARTNER.md).

---

## 1. Check it before you run it

```
git clone https://github.com/LAWLESS1987/covenant && cd covenant && sh check.sh
```

On Windows:

```
powershell -ExecutionPolicy Bypass -File check.ps1
```

Neither needs Python, both take a few seconds, and both print what they could
**not** check. Read that part. If it says something failed, you have found
something, and the project would rather hear it than not.

---

## 2. Install

```
pip install -r requirements.txt
```

---

## 3. Start a node

```
python run_with_ollama_judge.py --port 5000 --node-id <your-name> \
    --genesis genesis.json --peers <owner-address>:5001
```

- **Do not run `--export-genesis`.** `genesis.json` is tracked and canonical.
  Minting your own is the single most common way to end up unable to converge
  with anyone. `export_genesis` now refuses to overwrite an existing file, but
  do not go looking for the exception.
- `--peers` takes the owner's **P2P** port, which is their API port + 1. Ask
  them for the address; it is not discoverable.
- Leave off `--peers` entirely if you just want to run a node and watch it.

---

## 4. Confirm it is actually working

```
curl http://127.0.0.1:5000/health
```

What you want to see:

| field | good value | if it is wrong |
|---|---|---|
| `genesis` | starts `00009b31c6c654d7` | you minted your own — stop, delete the node `.db`, restart with `--genesis genesis.json` |
| `chain_height` | climbing, and matching your peer | stuck at 2 means the gate is vetoing catch-up blocks |
| the gate | able to answer, not failing closed | see below |

**A node that rejects everything is not broken, it is refusing.** The gate
fails closed on purpose: if no judge can answer, nothing is accepted. That is
the design, not a fault. What you should check is *why* it cannot answer.

---

## 5. Firewall, if you want two-way peering

Peering only becomes two-way when the owner adds your address to their node
and restarts. Until then you receive blocks and they do not receive yours.

Open **inbound TCP on your P2P port** (API port + 1, so 5001 by default), or
use Tailscale and skip the router entirely. On Windows:

```
netsh advfirewall firewall add rule name="covenant p2p" dir=in action=allow protocol=TCP localport=5001
```

Bind the API to loopback unless you mean otherwise — the node accepts
`COVENANT_API_HOST`, and an API reachable from your LAN exposes unauthenticated
read endpoints to anything on it (KNOWN_ISSUES A46).

---

## 6. Stopping and removing it

Ctrl-C. Nothing is installed outside the folder; delete the folder to remove it.
Keep the `*.db.key` file if you ever intend to come back — it is the node's
identity, and losing it loses that node's balance and operator rights for good.

---

## What will probably go wrong

These are known, written down, and not hidden from you:

- **Height stuck at 2** — historically the semantic judge crashed on the
  owner's block-2 hash and vetoed it. Fixed (A4), but if you see it, say so.
- **Your node holds where the owner's answered** — different judge seats
  disagree and your node forks. See *Staying in consensus* in `PARTNER.md`.
- **`git pull` refuses to update** — the node appends to a tracked ledger file,
  so an updated node has local changes it cannot fast-forward past
  (KNOWN_ISSUES **A20, still open**). Stash or reset that file to update.
- **Status surfaces disagree** — preflight, `/health` and the launch check can
  give three different answers about whether your gate works (A22).

The full register is [`KNOWN_ISSUES.md`](KNOWN_ISSUES.md). It is honest,
including about the things that make this annoying to run.

---

## If something here is wrong

That is the most useful thing you can send back. Open an issue, or write to
lawrencemoskowski@gmail.com. A finding that this project's claims do not hold
is worth more than agreement — an outside reviewer refuted its central
conformance claim on 2026-09-15, and that is recorded as A121 beside the
original wording rather than in place of it.
