# The console

`AP_CONSOLE.bat` — one page instead of fifteen `.bat` files.

    AP_CONSOLE.bat            read-only. It looks. It cannot touch anything.
    AP_CONSOLE.bat --armed    the buttons and the transaction panel work.

It opens `http://127.0.0.1:5199/` and stops when you close the window.

---

## What it shows

**The three claims (M38).** Disk source hash, how many nodes answer, how many
of those are running *that* source, the heights, and whether they converge.
This is the thing that was invisible for days: a machine can run a source from
last week while every restart reports success. The console names the node that
disagrees rather than averaging it away.

**Per node.** Version, source hash and line count, height, peers, pending
transactions, judge identity, alignment, available memory against the judge's
own footprint, anomaly kinds with counts, and the node's full warning list.
Flags for `source ≠ disk`, `degraded`, `crisis mode`, `judge keyless`,
`judge insecure`, `quorum not diverse`, `own genesis`.

**The watchdog's pulse**, in seconds, against the 60-second bound the watchdog
itself states — and the last few `ALERT` lines. A missing log reads as
**UNKNOWN**, never as age zero.

Height comes from `/health`. The console **never** polls `/chain`: that route
is rate-limited to 20 reads per 60 seconds per node (M11), and a page
refreshing every 2.5 seconds would exhaust it and make a converged network look
split — an observability feature that changes what it observes (M47).

---

## What it can do, when armed

Every action is a **name in a fixed allowlist**, mapped to a script that is
already in this folder. Nothing from a request ever reaches a shell, an
argument list, or a path. An ops console that can run an arbitrary string is a
remote shell with a nicer font.

Each action declares what it costs you, and the page draws that difference:

| | |
|---|---|
| `gates` `verify` `config3` `portdiag` `ports` | **reads only** — safe to click while thinking |
| `dashboard` | **writes a file** in this folder; touches no running process |
| `restart` `aclfix` | **changes state** — red, and asks before it runs |
| `sweep` | **long run** — 30 to 45 minutes against the live nodes |

An interface that draws "run the twelve gates, which change nothing" and "stop
all three production nodes" as the same button teaches its reader to click
without reading. That is M34 arriving through the front door instead of through
a permanently-firing alert.

**Transact.** From-node, to-node, amount, memo, and mine. The signing happens
in the server process using the node's own verified helpers. The key is read at
the moment of signing, used, and dropped: never logged, never in a response,
never in the page. `/api/state` is asserted key-free by the suite, armed and
unarmed.

The panel states the cost in plain sight because it is not small: the ethics
judge runs **inside** the submit call and judging is sequential under the chain
lock. A warm verdict is ~12.8 s, a cold model load is ~39.9 s, the timeout is
91.3 s per judge, and a verdict costs roughly 512 J against the 13.6 J it takes
to mine the block that carries it (B4).

If `/alignment` cannot be read, the console **refuses the transaction** rather
than substituting a plausible `benefit_score`. A guess there is either refused
by the governor's drift band or drags the band, and neither is visible.

---

## Four rules that are structural, not configurable

1. **Loopback only.** `BIND_HOST` is `127.0.0.1`; `main()` refuses to start if
   anything changed it, and every request is checked again at the handler.
   There is no environment variable that moves it. This console can restart
   nodes and sign transactions; a console that can do that must not be one env
   var away from the network. Putting it on a phone is a different program with
   an auth story, and it should be built as one rather than reached by flipping
   a string here.
2. **Actions are a fixed allowlist, never a command string.**
3. **Actions are off until `COVENANT_APP_ACTIONS=1` exactly.** No other value
   arms them and no value relaxes anything else — the same shape as
   `COVENANT_FORCE_NO_SANDBOX` (P4/P10) and `COVENANT_REQUIRE_JUDGE_DIVERSITY`
   (B2). Nothing in this system turns a control **off** from the environment.
   Arming lives in the console window; closing it disarms.
4. **The signing key never leaves the process.**

It also describes itself, because P15 counted the long-lived processes on this
machine and found the fourth one — ollama — reporting nothing. This is the
fifth. It prints its own source hash and line count at boot (P11) and writes a
line to `logs/app.log` at least every 60 seconds even when nothing changes,
**and states that bound in its own banner**, so a longer gap is readable as
death rather than calm (P16).

---

## Proof

`test_covenant_app.py` — 51 checks. It starts three **stub** nodes on the real
production ports and runs the real unmodified `covenant_app.py` against them as
a subprocess, twice: once read-only, once armed.

    python test_covenant_app.py

What it actually proves, rather than asserts:

- the console does **not** answer on this machine's non-loopback address
- every guard is mutation-tested (M31): the test flips the actions gate ON and
  requires the allowlist to keep refusing a name outside it, then flips it back
  and requires the refusal to return
- `COVENANT_APP_ACTIONS` set to `true`, `0`, `yes` or empty does **not** arm it
  — each checked by starting the console that way and asking it
- a node running a different source is named (M38); a height split is reported
  as a split; a node that stops answering is reported down with its error kind
- `/chain` is never touched — the stubs count every hit and the count is zero
- `/api/state` carries no key material, armed or not
- traversal and near-miss action names are refused: `../verify_bundle.py`,
  `/etc/passwd`, `GATES`, `gates `, `gates;rm -rf /`, `gates%00`
- a missing watchdog log reports `age=None`, not `age=0`
- the page loads nothing from anywhere, and says so in a CSP header
- an unreadable `/alignment` refuses the transaction instead of guessing

The suite races `gates` — not `sweep` — for its concurrency check, because
`run_local_sweep.py` is a 30-to-45-minute job against the live nodes. A test
with a side effect on production is not a test.

If the production ports are busy the suite reports **UNKNOWN and exits 2**. It
does not fall back to different ports and call that a pass.
