# Incident, 2026-08-29 ~21:50Z — all three nodes and the watchdog, together

## What was observed

- All three nodes down; no listener on 5000/5020/5060.
- `logs/nodeA.log` ends in `^C`.
- **No watchdog process at all** — so the layer that restarts nodes was
  itself a casualty.
- `logs/watchdog.log` still ended with ordinary `balance agrees across 3 dbs`
  lines. Its last node-health alert was 21:20:06, the restart. Nothing after.
- One stray process survived: a `SMOKE` node on port 5978, left over from the
  v8.40 pre-flight verification hours earlier. It caused nothing, and it is
  exactly the kind of litter that makes the next diagnosis slower.

## The hypothesis that was wrong

First read was a shared console group: one Ctrl+C or one window close taking
everything. **Disproven by the launcher itself.** `covenant_prod.bat` starts
each of the four with its own `start "Title" /min cmd /c ...`, which is a
separate console and therefore a separate process group. A single Ctrl+C
cannot reach the other three.

Worth recording because the fix it implied — decouple the process groups —
was already done, and shipping it would have been churn on a live launcher
justified by a cause that does not exist.

## What actually produces this exact state

`AB_RESTART_NODES.bat` lines 83-86 kill by window title:

    Covenant Node A*, Covenant Node B*, Covenant Node C*, Covenant Watchdog*

That is the only single action in the system that takes precisely those four
and nothing else.

It is guarded — P17 checks Ollama *before* stopping anything. But
`covenant_prod.bat` then checks Ollama **again** at its line 59 and aborts
the start if it does not answer within 8 seconds. Between those two checks
everything is already stopped.

**So the residual risk is a race, not a missing guard:** if Ollama is slow,
busy, or briefly unreachable in the window between the two checks, the stop
succeeds and the start refuses. Stopped, not started — the exact
take-it-down-and-leave-it-down outcome P17 exists to prevent, surviving in a
narrower window than the one P17 closed.

## Why the recovery was slow, and what changed

The healing chain is: guard → watchdog → nodes. It worked as designed; it was
simply late, and every part of the lateness was detection, not repair.

| | before | after |
|---|---|---|
| guard poll interval | 5 min | **2 min** |
| gap before believing the watchdog dead | 300 s (five missed rounds) | **180 s** (three) |
| guard's view of the nodes | none — it reported on one process while three were dead | **reads and reports every pass** |

The guard still **refuses to restart nodes**. That is deliberate: restarting
nodes is the watchdog's job, with its own 3-strike judgement. A second
process restarting on a different rule is two supervisors disagreeing about
one machine, which is worse than a slow recovery. `test_c3_guard.py` pins the
refusal by AST (N3) and pins that the *reason* is written in the code (N4),
so nobody later improves it into a second supervisor.

Worst-case recovery is now roughly: ≤2 min to detect, plus the watchdog's
3 strikes ≈ 3 min → **~5 minutes**, unattended.

## What was NOT changed, and why

The launcher. The process groups are already separate; the Ollama double-check
is a real race but a narrow one, and it now surfaces within two minutes in
`logs/guard.log` as `NODES DOWN [...]`. Changing how a live chain starts, to
close a race that is now visible in two minutes, is not a trade worth making
without evidence it fires.

If it ever does fire, the evidence will be in `NODE_RESTART.txt` (a stop with
no start) beside a `NODES DOWN` line in the guard log — and that pairing is
now the thing to look for.
