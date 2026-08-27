# The launch gates

`launch_check.py` asks twelve questions and changes nothing. Every answer is
**PASS**, **BLOCKED**, or **UNKNOWN**, and UNKNOWN is never folded into PASS.

Why three states and not two: this project's characteristic failure is a claim
that is true, unmeasurable, and quietly wrong later. A two-state check has to
guess on the cases it cannot see, and it always guesses green. So a node that
cannot be reached is UNKNOWN. A check that needs Windows is UNKNOWN on Linux.
A gate that raises is UNKNOWN, never PASS.

Where a gate has a *different correct answer* per platform, it asserts that
answer instead of stepping aside (M34) — a check that stops checking on the
platform that runs production has been switched off.

| gate | asks | blocked means |
|---|---|---|
| **G1** | does every shipped file hash to `MANIFEST.sha256`? | either an edit you meant, or a delivery that did not land. Both need to be known before launch |
| **G2** | is each companion import beside the file that needs it? | a missing companion reads as a test regression and is not one (M37) |
| **G3** | flask, werkzeug, cryptography, requests — and waitress? | without waitress, W1's bounded pool is inert and Flask is served by werkzeug's **dev** server: one unbounded thread per connection, on the port you expose |
| **G4** | one shared canonical genesis? | every node mints its own, they can never converge, supply grows by 1000 per node |
| **G5** | is the ethics judge reachable? | the gate fails **closed**. The node boots, serves `/chain`, peers, reports healthy — and rejects 100% of transactions. Also blocks on `mock` + the insecure flag: adversarial transactions are known to pass it |
| **G6** | does the judge model fit in RAM? | it loads by paging. P12 measured 3,535 MB free against a ~5,200 MB model on this box |
| **G7** | port arithmetic — `--port N` takes N, N+1, N+11 | nodes closer than 20 apart collide, and the victim prints `Address already in use` *after* a healthy-looking banner |
| **G8** | are the identity keys owner-only? | they **are** the operator credential and the genesis mint key. On NTFS the mode bit says nothing, so this reads the real ACL — see `P9_WINDOWS_OWNER_ONLY.md` |
| **G9** | do disk and the **running process** agree? | the file on disk is not what is executing. This is the one that has been wrong for two days at a time |
| **G10** | is the watchdog alive? | a monitor that dies silently reports health for ever. Its last line still says everything is fine, and goes on saying it |
| **G11** | XRP mainnet gate state | reports; never opens. Four locks, described in `LAUNCH.md` |
| **G12** | when did the suites last run, and where? | always UNKNOWN by design — a result is a claim about the platform it ran on and the source it ran against, and neither is checkable from a filename |

## Reading the exit code

```
0   every gate PASS
1   at least one BLOCKED          do not launch
2   no BLOCKED, but some UNKNOWN  this is NOT a pass
```

`AN_LAUNCH.bat` stops dead on 1, and on 2 it asks before continuing rather
than deciding for you.

## G9 and the 48-bit comparison

`/health`'s field is **named** `source_sha256` and **contains**
`CORE_SOURCE_SHA12` — twelve hex characters, 48 bits (A25). The contract is
correct, intentional, and pinned by `test_p11` V6b; only the name lies, and it
lied convincingly enough that `verify_deploy.py`'s first draft compared it
against a full 64-character digest and reported MISMATCH on a perfectly
correct deployment.

So G9 compares twelve, and says so. It is a **drift check** — "has anybody
restarted this node?" — not a tamper check. G1 compares the full 64.
