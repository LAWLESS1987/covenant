# The third layer of the loop — 2026-08-23

`PC_SYNC_LOOP.md` closed the loop between the **project** and the **disk**.
This is about the layer under it: between the disk and the **process**. It was
open the whole time, and until tonight nothing in the system could see it.

## The question nobody could answer

M25's rule is: do not trust the backlog's claim that the code shipped — grep the
file on the machine that runs the node. Twenty runs learned to do that. But
after you have verified the bytes on disk, the rule stops. Nothing told you
whether the python process answering `:5000` was running *those* bytes.

At 03:12 UTC tonight, the state was:

```
disk    covenant_unified_v8.py   0b04473b…   8880 lines   mtime 22:57
process node A on :5000          ???
process node B on :5020          ???
```

Three separate pieces of evidence had to be assembled to answer it:

1. `logs/prod.log` said `starting node A on 5000` at 21:39 ET — a real start,
   not the `node A already up` no-op that P3 describes.
2. That start was after 18:57 ET, when v8.30 was written to disk.
3. `logs/watchdog.log` carried `code sandbox unavailable — no usable 'fork'
   start method on this platform (win32)`, and that alert **only exists in
   v8.30** (P4). A v8.29 node cannot emit it.

That is forensics, not verification. It worked here because I happened to know
which version introduced which alert. It would not have worked for any two
adjacent versions, and it would not have worked at all for someone reading the
logs next week. And `covenant_unified_v8.PRE-v8.29.py` and
`covenant_unified_v8.PRE-v8.30.py` both sit in the same folder — a restart from
either would have looked identical from outside.

## Why the node could not say

Not an oversight in one place. Three, each individually harmless:

| what | said | actual |
|---|---|---|
| `COVENANT_VERSION` (line 413) | `"v8.9-merged"` | v8.30 |
| boot banner (line 7109) | `Covenant Unified v7.0 running` | v8.30 |
| `/health` | *no version field at all* | — |

`grep -c COVENANT_VERSION covenant_unified_v8.py` returned **1**: the constant
was defined and read by nothing. So the file carried two version strings, both
wrong, in different ways, and neither reachable from outside the process. The
one an operator actually saw — in `logs/nodeA.log`, every restart, for months —
was three major versions stale.

This is the same shape as M25 and P3 and D4, and it is worth naming as a class:
**a fact that is only ever asserted, never measured, drifts silently.** "The PC
has the latest source" was asserted for sixteen runs. "`covenant_prod.bat stop`
stops the node" was asserted until someone watched it. "The guards are wired
into `daily.py`" was asserted until someone grepped. "This is v7.0" had been
asserted since v7.0.

## What v8.31 does

Additive, no behaviour change, four edit sites (`grep "P11 (v8.31)"`):

- `COVENANT_VERSION = "v8.31"`, and it is now read.
- `CORE_SOURCE_SHA256` / `CORE_SOURCE_LINES`, computed once at import from the
  module's own file. It **never raises**: an observability feature must not be
  able to stop a node from booting, so an unreadable source degrades to
  `"unavailable"` *with a reason* rather than silently.
- Boot banner: `Covenant Unified v8.31 (source 4b7e0a0f6b74, 8933 lines)
  running - API: 5000, P2P: 5001, Bridge: 5011` — and it flushes, because its
  whole job is to appear in a redirected log.
- `/health` carries `version`, `source_sha256` (12 hex), `source_lines`; and if
  the fingerprint failed, a warning saying the node cannot prove what it is.

**The hash is of the source as LOADED, not as it is on disk now.** That is the
point, not a limitation. It is what makes the next part possible.

## What the watchdog does with it

`covenant_watchdog.py` now compares, every round:

```
what /health says the node LOADED    vs    sha256(covenant_unified_v8.py on disk)
```

They differ in exactly one situation, and it is the one that has cost this
project the most: **the file was updated and the node was never restarted.**
That is now an ALERT carrying both hashes and the name of the script that fixes
it, instead of a silence discovered two days later. Two more:

- nodes reporting **different** sources → alert, because they may disagree on
  validity rules (A7 is no longer hypothetical the moment that happens);
- a node too old to answer → INFO, once per round. It cannot lie; it simply
  cannot say. That is not an alert, but it *is* the reason the check is
  impossible, so it is said out loud.

Every INFO line now begins `node A v=v8.31 src=4b7e0a0f6b74 height=…`, so
`logs/watchdog.log` becomes a minute-by-minute record of what was running when.
That record is what tonight's forensics had to substitute for.

The comparison is a pure function, `source_drift_report(states, on_disk)`, so
it is tested without standing up two nodes — `test_p11_version_identity.py`
W0–W6.

## How to check it yourself, in three lines

```cmd
python -c "import hashlib;print(hashlib.sha256(open('covenant_unified_v8.py','rb').read()).hexdigest()[:12])"
curl -s http://127.0.0.1:5000/health   | findstr source_sha256
curl -s http://127.0.0.1:5020/health   | findstr source_sha256
```

Three identical strings means the deployed file is the running file on both
nodes. Anything else is drift, and the watchdog will already be saying so.

## What it does not fix

- **It is not tamper evidence.** A node that has been modified reports the hash
  of what it modified itself into. This answers *"did my deployment land?"*,
  which is an honesty-with-yourself problem, not an adversary problem. The seal
  (`covenant_seal.py`) is the adversary answer, and it is a different mechanism.
- **The API port is still hijackable on Windows** — waitress binds it, so
  P5's `SO_EXCLUSIVEADDRUSE` covers only the node's own P2P, bridge and
  preflight sockets.
- **Peers still cannot see each other's version.** A7 says a validity-rule
  change becomes a protocol-version question the moment anyone else runs a
  node. `/health` is loopback-facing; the P2P handshake carries nothing. That
  is a wire-format change and therefore L's call, not the loop's — opened as
  **A20**.
- **Disclosure trade, stated rather than buried:** `/health` now tells anyone
  who can reach it exactly which source is running. It is a read-only,
  loopback-posture endpoint that already discloses genesis, peer count, judge
  identity, WSGI backend, crisis mode and every anomaly kind — and the
  operational value here is precisely the failure this project has hit twice.
  If `/health` is ever exposed beyond loopback, this field is one more reason
  it should not be.

## Seal state at the time of writing

`covenant_seal.py verify` runs read-only over the device bridge and answers
exactly:

```
root was c119afb5…   root now 679e447f…
20 changed, 81 added, 0 removed
```

**Nothing has been removed** — every difference is explained by known work (the
19 suites P1 delivered, the twelve deep price series, the vendored wheels,
tonight's measurement tools). The seal is stale by 101 files and has been since
2026-08-22 05:23.

It was **not** re-sealed by this run, deliberately. Re-sealing is the act of
blessing a file set as canonical; doing that on the loop's own authority,
immediately after the loop's own writes, is the auditor signing its own work.
The staleness is real and `PC_SYNC_LOOP.md` is right that a seal which is
usually wrong teaches its operator to ignore it — but the fix for that is one
click by L, not a self-issued blessing.
