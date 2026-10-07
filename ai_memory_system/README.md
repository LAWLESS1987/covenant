# AI Memory System

> **CORRECTED 2026-09-17. Read this before the claims below.**
>
> This README's central promise — *nothing is destroyed, contradictions are
> surfaced rather than resolved* — is **PARTLY TRUE**, and the project's own
> field test says so in detail:
> [`docs/FIELD_TEST_2026-08-29_memory_provenance.md`](docs/FIELD_TEST_2026-08-29_memory_provenance.md)
> §4. Three carve-outs the text below does not state:
>
> 1. **`put()` does no overlap detection at all.** That coupling lives only in
>    the HTTP PUT handler (`server.py:398-405`). A direct library call to
>    `MemoryStore.put()` with an overlapping name marks nothing, silently. It is
>    a property of the server, not of the store.
> 2. **A same-name write overwrites irrecoverably.** `_atomic_write`
>    (`memory_store.py:348`) overwrites unconditionally — no trash copy, and the
>    ledger records only a `sha256`, never the text. Measured: after overwriting,
>    the original body is unrecoverable. *This is the same failure this project
>    diagnosed in other systems, present here, on this path.*
> 3. **`superseded_by` is write-only.** Nothing in `score_explain`, `rank` or
>    `context_window` reads it. A superseded memory and its correction score
>    identically, `context_window` emits **both** bodies, and because
>    `supersede()` carries the old use count forward a superseded memory can
>    **outrank its own correction (10.82 vs 7.23)** and push it out of the
>    8000-character core budget. The flag is a durable record with **no
>    consequence for what an agent is handed back.**
>
> So "SUPERSEDE, both survive" describes a real state change that is written,
> ledgered, and then not consulted. The honest summary is: the store does not
> delete on the supersede path, one other path does delete irrecoverably, and
> the surviving link does not change what recall returns.
>
> The claims below are left unedited. A README that quietly fixed its own
> wording would be doing the thing this project exists to argue against.
>
> **CORRECTED AGAIN 2026-09-28, this time against the code, because the block
> above committed the sin it warns about:** written 2026-09-17, it restated
> the 2026-08-29 field test in the present tense without re-measuring, and
> commit `590cf4f` (2026-08-31) had already changed two of the three claims:
>
> - Item 2 is **outdated as written**: `put()` archives the prior text to
>   `.trash/` before a content-changing overwrite (`memory_store.py:665`,
>   "THE PRIOR WORDING SURVIVES AN OVERWRITE" -- line 668 since the code above
>   it grew; re-pointed 2026-10-04, A257) and the ledger records the
>   archive name. `_atomic_write` itself still overwrites; the copy is taken
>   above it.
> - Item 3 is **half outdated**: `context_window` now reads the link and
>   marks a superseded memory "SUPERSEDED BY <name> -- prefer that memory
>   where the two disagree" (`recall.py:195`). Still true, measured
>   2026-09-28: `score_explain` and `rank` do not consult it, so a
>   superseded memory can outrank its correction (21.80 vs 16.23 on current
>   code) and under a tight budget the correction can be omitted -- named in
>   `omitted`, but absent from what the agent is handed.
> - Item 1 stands as written.
>
> **FIXED 2026-10-04 -- item 3's ranking half, measured against the code:**
> `score_explain` now halves a superseded memory's score (`supersede_penalty`,
> shown in `because`) and `rank` places it strictly below its correction, even
> after a million uses (`placed_below`, `score_before_placement`). It stays in
> the results, above zero, naming its successor. `context_window` fills newest
> versions first, so under a tight budget the superseded memory is the one
> named in `omitted`. `/recall` brings each candidate's correction into the
> candidates (`recall.with_successors`), so the shortlist cannot hand back
> only the stale version. (The context mark cited as `recall.py:195` above is
> at `recall.py:367` since this change.)
>
> Limits added on purpose, each stated in `because` as `supersede_withheld`:
> only a write the ethics gate ALLOWED counts as checked, and a link from a
> less-checked write does not demote a checked memory -- otherwise copying a
> stored rule and adding an exception would bury the rule. A successor that
> cannot be read (tombstoned, or not among the candidates) is not applied
> either; a memory cannot supersede itself; a loop of memories each marked
> superseded by another has no newer side, so none is demoted
> (`supersede_cycle`). Checks SR1-SR12 in `test_memory_system.py` (14 checks;
> the suite reads 154/154). An adversarial pass broke the first version five
> ways before it was committed; each break is now a check, and twelve mutations
> of `recall.py` are each caught. Record: A245 in `docs/KNOWN_ISSUES.md`.
> *(This block first said thirteen; the count had included the unmutated
> baseline. Retraction A245-MUT13.)*


> **Read as an experiment.** *Added 2026-10-03 for clarity, at the operator's
> request ("reflect the scientific method while leaving the substance"). A map
> onto this page; nothing else on it was changed.*
>
> - **Question.** Can memory shared by several AI agents keep every change
>   auditable, and keep disagreements visible instead of resolving them away?
> - **Claim under test.** Nothing is silently discarded: supersede, demote,
>   re-order, disclose; never erase, never overwrite, never quietly truncate
>   ([The rule underneath](#the-rule-underneath)).
> - **Method.** A field test against the source with empirical runs
>   (`docs/FIELD_TEST_2026-08-29_memory_provenance.md`, section 4), and a test
>   suite that executes the store, the chain and the HTTP surface.
> - **What refuted parts of it.** The two corrected blocks above: the claim was
>   partly true, and the correction itself went stale once and was corrected
>   again against the code. *2026-10-04: a third block, FIXED, records the
>   ranking repair.*
> - **Known limits, measured 2026-10-03.** Ranking does not read supersession,
>   so a superseded memory can outrank its correction; a direct `put()` does no
>   overlap detection. *2026-10-04: the ranking limit is fixed -- see the FIXED
>   block above; the `put()` limit stands.*
> - **Reproduce.** `python test_memory_system.py`.

Shared, persistent, **auditable** memory for AI agents. Plain markdown files,
a hash-chained ledger, and an HTTP API small enough that an agent can learn it
from `/openapi.json` without being told.

```bash
python main.py server --host 127.0.0.1 --port 8000
python main.py server --host 0.0.0.0 --port 8000 --token "$AI_MEMORY_TOKEN"
python main.py rereview [name]   # 2026-10-05: put unchecked memories back in front of the gate; BLOCK retires to .trash.
                                 # Run it on a COPY first: on the live store it would retire 16-26 imported conversations (A256).
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
| `GET /context?unreviewed=withhold` | Since 2026-10-05 (A253 G3): core memories the gate did not ALLOW come after every checked one, quoted line by line under a never-act rule (`fenced` counts them), or with `withhold` are left out and named in `withheld`. Any other value is refused with 400. |
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
- **Wider than first written (A304-CHAIN-SPLICE-2026-10-07):** not only the newest
  record. Any record can be rewritten and still pass a chain walk if every later
  link is recomputed (check A8c). The same remedy covers both: keep the head of
  the first N lines outside the file, and check that the next copy still hashes to
  it (A8d).

## Tests

```bash
python test_memory_system.py     # last line: M1: N/N passed (154/154 on 2026-10-04; 155/155 the same night, G8b added for A250; 162/162 on 2026-10-05, M1b/M1c/M2b added for A254; 182/182 the same night, U1-U7, RV1-RV6, RV2b, R6b and C4 added for A253's G3, M1d and M2c for an A254 recurrence)
```

*This line said 66/66 until 2026-10-04: a count that went stale as checks were
added, and reached a fix request as fact. Retraction AIMEM-66 in
`docs/RETRACTED.json`; the suite's own last line is the count.*

Covers the store, the chain (including a real tamper detection and the
last-record limitation above), tombstones, the live HTTP surface on a loopback
port, and the auth boundary — the off-loopback refusal is executed, not
asserted.

## License

Part of [covenant](https://github.com/LAWLESS1987/covenant). Same license.
