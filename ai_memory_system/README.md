# AI Memory System

Shared, persistent, **auditable** memory for AI agents. Plain markdown files,
a hash-chained ledger, and an HTTP API small enough that an agent can learn it
from `/openapi.json` without being told.

```bash
python main.py server --host 127.0.0.1 --port 8000
python main.py server --host 0.0.0.0 --port 8000 --token "$AI_MEMORY_TOKEN"
```

The second form is required off loopback — see [Trust boundary](#trust-boundary).

---

## Why another one

Letta, Mem0, Supermemory and Engram each solved a real piece. This takes those
pieces and changes one thing they share: **they all destroy what they disagree
with.**

| Idea | Taken from | What is different here |
|---|---|---|
| Core vs archival tiers | Letta / MemGPT | The context budget is stated, and whatever does not fit is **named** in `omitted`. A truncated context that doesn't say so lies by omission. |
| ADD / UPDATE / NOOP reconciliation | Mem0 | `UPDATE` is replaced by **SUPERSEDE**: both memories survive, linked both ways, and the move is on the ledger. "What did we believe before, and when did it change" stays answerable. |
| One API over many sources | Supermemory | Same spirit, no hosted dependency — stdlib Python, runs on a laptop or a phone. |
| Scored recall | memSearch / vector stores | Scoring is **lexical and explainable**: every result carries the components that produced it. Vectors may be added later; they may not replace the explanation. |
| Consolidation: use strengthens, time decays | Engram | Strength only **orders** recall. It never deletes and never hides — a system that forgets what it stopped using would delete the safety lesson nobody has needed for a year. |

And one thing none of them do: **contradictions are surfaced, not resolved.**
When a new memory contradicts a stored one, both are kept and the disagreement
is reported. Two agents disagreeing is a fact a human should see, not a merge
conflict to auto-resolve.

## The rule underneath

> Nothing is silently discarded. Supersede, demote, re-order, disclose —
> never erase, never overwrite, never quietly truncate.

Deletes are **tombstones**: the file moves to `.trash/` and the ledger records
who retired it and why. What one agent writes, another may retire — never erase.

## API

| Route | Does |
|---|---|
| `GET /health` | State + audit verification. Open even under a token; discloses no memory. |
| `GET /memories` | The index: name, description, metadata, links. |
| `GET /memories/<name>` | One memory, whole. |
| `PUT /memories/<name>` | Write `{description, type, body, agent}`, optional `tier`. Returns what the write did to what was already stored. |
| `DELETE /memories/<name>` | Tombstone it. |
| `GET /search?q=` | Substring recall. |
| `GET /recall?q=` | Scored recall — every score carries its components. Counts as a use. |
| `GET /context?budget=` | Core-tier context under a character budget; omissions named. |
| `GET /audit` | The hash-chained write ledger. |
| `GET /openapi.json` | The machine-readable contract. |

```bash
curl -X PUT localhost:8000/memories/user-prefers-outcomes \
  -H 'Content-Type: application/json' \
  -d '{"description":"how to work with L","type":"user","tier":"core",
       "body":"Prefers outcomes over instructions.","agent":"claude"}'

curl 'localhost:8000/recall?q=outcomes'
```

## Storage format

One memory, one file — the same frontmatter shape Claude Code's own session
memory uses, so adopting an existing memory directory is a copy, not a
translation (`python main.py import <dir>`).

```markdown
---
name: user-prefers-outcomes
description: how to work with L
metadata:
  type: user
  agent: claude
  tier: core
  uses: 3
  last_used: 1788029722
---

Prefers outcomes over instructions. Links with [[other-memory]].
```

Back it up by copying the directory. Read it with any text editor. A memory
store you can only read through its own API is one you cannot audit when the
API is the thing that's wrong.

## Trust boundary

Stated plainly, because a memory store is not a cache — it is what an agent
believes, and anyone who can write it can change what every reader concludes.

- **Bound to `127.0.0.1`** → a token is optional; the reachable set is already
  "processes on this machine".
- **Bound anywhere else** → a token is **required**. Without one the server
  **refuses to start** rather than come up quietly exposed. Refusing is loud;
  starting open is silent, and silence is how this goes wrong.
- The token proves the caller holds a secret and **nothing else**. The `agent`
  field on a write is a **label, not a proof of identity**.
- A bearer token over plain HTTP is readable by anything on the path. Put TLS
  in front of it if it crosses a network you don't control.
- The audit chain makes tampering **detectable, not impossible**. Those are
  different properties, and conflating them is how a log becomes theatre.
- **Known limit, measured, not hidden:** a hash chain proves each record
  against the one before it, so an edit to the *newest* record is invisible to
  a chain walk — nothing points at it yet. The head hash must be witnessed
  outside the file for the last write to be tamper-evident. Pinned by check A8
  in the suite.

## Tests

```bash
python test_memory_system.py     # 66/66
```

Covers the store, the chain (including a real tamper detection and the
last-record limitation above), tombstones, the live HTTP surface on a loopback
port, and the auth boundary — the off-loopback refusal is executed, not
asserted.

## License

Part of [covenant](https://github.com/LAWLESS1987/covenant). Same license.
