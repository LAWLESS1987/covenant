# Codex security audit of the 2026-11-22 changes (A470, A471, head commitment, eval scripts) -- A472

Lawrence, 2026-11-22: "have codecs run a audit on all the updates we just did, look for improvements in security flaws."

**How it was run.** The Codex desktop app's own CLI on this laptop (codex-cli 0.167.0-alpha.4.1): `codex exec --sandbox
read-only --ephemeral`, in a scratch folder holding COPIES of only the changed code, never the live tree, whose
private/ holds addresses.
- **The copies were scrubbed before sending:** the user folder path, author lines, and the one stand-in address inside
  our tailnet block in a patch (replaced with 192.0.2.9).
- **Rescanned clean:** only 127.0.0.1, 192.0.2.9 and 8.8.8.8 remained.
- **The brief:** in the session scratch, `codex_audit_prompt.txt`.
- Codex modified nothing and ran no network command.

**Verified here, each against the code, before any fix (a review is not a verification).** Its answer follows, whole.

| # | Codex | verified here | fixed |
|---|---|---|---|
| 1 | HIGH: manifest is a server claim; substring match | substring CONFIRMED (a header with another hash and the pin passed). The server-claim half is the known limit recorded in A470; the traffic is WireGuard on the tailnet | exact equality on a canonical form (`manifest_hex`), checked before the body; leg AND limbs |
| 2 | HIGH: default opener honours proxies | CONDITIONAL: no proxy env now, but one at import would carry a private ask | `ProxyHandler({})` on the shared opener; the health check uses it too |
| 3 | HIGH: a hold suppresses an alarm-only detector's ALERT | CONFIRMED (model_unmanaged: no ALERT, only an info line) | only detectors WITH automatic remedies can be held; the hold line carries the measurement |
| 4 | HIGH: writable state drives security holds | real for security detectors | NEVER_HOLD (defense_lapse, manifest_stale, held_core_drift); malformed state dropped, not trusted; 1 MB cap |
| 5 | MED: one pass depends on a fresh previous reading | CONFIRMED (no recent previous pass -> held, every pass) | no known previous pass = no hold; a future-dated previous pass is ignored |
| 6 | MED: commitment does not bind private/leg.json | true by design (private config is untracked) | NOT fixed; recorded |
| 7 | MED: env cannot override the file | CONFIRMED (ALLOW_REMOTE=0 still allowed remote) | a SET env switch decides, strictly; a set empty pin means never asked |
| 8 | MED: unlocked read-modify-write, shared .tmp | real (rare: run_once in two processes) | unique temp file per writer; last writer wins (advisory) |
| 9 | MED: bad config aborts import | CONFIRMED with a text port (crashed covenant_leg AND covenant_limbs); Codex's own example `{}` happens not to crash | port validated (1-65535, else default); 64 KB config cap |
| 10 | MED: no overall response deadline | CONFIRMED, and my first fix was wrong: chunked read() still blocks per chunk; caught because the check passed against the old code | `read_bounded`: read1() under one monotonic deadline; leg and limbs |
| 11 | MED: quadratic hedge regex (eval only) | plausible; eval-only | reply capped at 20,000 chars before the regexes |
| 12 | LOW: committee KeyError on asked_back | CONFIRMED | every label scored; unexpected -> 0 |

**Checks added, each red against the pre-fix code, green after:**
- **test_a470:** S1-S5. On the old code S1-S4 and S5 FAILED (S5: 6.01 s against a 1 s deadline). A470 is 20/20.
- **test_a471:** J1-J7. On the old code J1 FAILED; J3-J7 could not run there (the names did not exist). A471 is 21/21.
- **Also passing:** LM1 17/17 (its stand-in sends "sha256=<hash>"; the canonical form accepts both spellings and
  nothing else), LG1 38/38, A463 34/34, LP1 7/7, XB1 8/8, H1 311/311.
- **Live:** the leg answered, and SMOL and PHI "engaged", through the exact match.

## Codex's answer (whole, as returned)

1. **HIGH — `covenant_leg.py:532`, `covenant_leg.py:540`**  
   **Flaw:** The manifest is an unauthenticated server claim, checked after the private ask has already been transmitted over HTTP.  
   **Scenario:** A compromised gateway runs another model and returns the expected public hash in `X-Leg-Manifest`; its answer passes. A replacement endpoint receives the ask even if its reply subsequently fails the pin. Substring matching also accepts a header containing both an incorrect manifest and the expected hash.  
   **Minimal fix:** Authenticate and encrypt the connection before sending the ask; validate a canonical manifest with exact equality. A compromised gateway requires independently trusted measurement/attestation—or must explicitly remain outside the pin’s security guarantee.

2. **HIGH — `covenant_leg.py:104`**  
   **Flaw:** The default urllib opener honors proxy configuration, allowing an ostensibly loopback consult to leave the machine without a manifest check.  
   **Scenario:** Set `http_proxy` to an attacker’s proxy and remove applicable `no_proxy` exclusions. With `LEG_HOST=127.0.0.1`, the proxy receives the private POST and can supply an answer; `remote` remains false.  
   **Minimal fix:** Construct the opener with `urllib.request.ProxyHandler({})` alongside `_NoRedirect`. Apply the same explicit transport policy to the health probe.

3. **HIGH — `covenant_highway.py:4777`**  
   **Flaw:** An eligibility hold suppresses the normal alert and measured details, including for detectors with no automatic remedy.  
   **Scenario:** Low credit for `model_drift` or `defender_threat` causes a fresh real alarm to produce only an informational A471 message. The `continue` skips the alert at line 4821 and its evidence. An intermittent condition can disappear before any subsequent alert.  
   **Minimal fix:** Generate the original alarm and measured details independently of eligibility; apply holds only when dispatching eligible automatic remedies. Preserve proposals and alarm-only detectors.

4. **HIGH — `covenant_eligibility.py:57`, `covenant_eligibility.py:139`**  
   **Flaw:** Writable eligibility and previous-sense files directly control security-relevant holds without integrity or provenance checks.  
   **Scenario:** An actor with write access to these operational files sets `defense_lapse` credit to `-1` and repeatedly supplies a fresh previous `ABSENT` reading. Defender maintenance can remain held despite a persistent real condition. This requires operational-file write access, not source modification.  
   **Minimal fix:** Restrict writes to a trusted state owner, authenticate state where less-trusted writers are possible, and validate schemas, finite numbers and timestamps. Independently exempt security-critical remedies from learned holds.

5. **MEDIUM — `covenant_highway.py:4707`, `covenant_eligibility.py:142`**  
   **Flaw:** The “one pass” limit depends entirely on a fresh previous `PRESENT` reading rather than recording that a hold has already occurred.  
   **Scenario:** With negative credit and passes more than 30 minutes apart, every pass discards its predecessor and holds the same persistent condition again. Silent failures in `save_last_sense()` can similarly repeat a hold. Future timestamps are also accepted without a lower age bound.  
   **Minimal fix:** Record an episode’s consumed hold transactionally; disable holding when predecessor state is stale, invalid or cannot be persisted. Enforce a bounded timestamp range.

6. **MEDIUM — `covenant_head_commit.py:60`, `verify_head_commitment.py:215`**  
   **Flaw:** The commitment does not bind the newly authoritative `private/leg.json` configuration.  
   **Scenario:** Someone who can edit that file changes the endpoint, remote permission and manifest together. The leg follows the replacement configuration while head-commitment verification remains unchanged. Environment overrides likewise have no binding to the commitment.  
   **Minimal fix:** Bind an approved digest of the leg configuration through a signed policy and verify the effective configuration before use; explicitly govern environment overrides. Avoid binding routinely changing eligibility state into a static commitment.

7. **MEDIUM — `covenant_leg.py:109`, `covenant_leg.py:127`**  
   **Flaw:** Environment variables cannot reliably override the file to revoke remote access or clear its pin.  
   **Scenario:** With file `allow_remote: true`, setting `COVENANT_LEG_ALLOW_REMOTE=0` still permits remote access because `"0"` is truthy. An empty manifest environment variable falls back to the file’s pin.  
   **Minimal fix:** Distinguish an absent variable from an explicitly supplied value; parse documented boolean values strictly and let an explicit empty pin disable remote consultation.

8. **MEDIUM — `covenant_eligibility.py:70`, `covenant_highway.py:4715`**  
   **Flaw:** Eligibility updates use an unlocked read-modify-write sequence and a shared temporary filename.  
   **Scenario:** Two node processes load different snapshots and overwrite each other’s credit. Concurrent writers can truncate the same `.tmp`; one can rename it while the other is still writing, exposing incomplete state or causing replacement failures.  
   **Minimal fix:** Lock the complete observation/state-update transaction across processes and use uniquely created temporary files. Coordinate predecessor snapshots within the same transaction.

9. **MEDIUM — `covenant_leg.py:56`, `covenant_leg.py:66`, `covenant_eligibility.py:60`**  
   **Flaw:** Configuration and eligibility JSON ingestion is unbounded, and invalid leg settings can abort module import.  
   **Scenario:** A writable `leg.json` containing `"port": {}` raises `TypeError` during import, also affecting `covenant_limbs`, which imports this module. Very large configuration or state files can exhaust memory before normal failure handling or alarm reporting.  
   **Minimal fix:** Bound file reads, validate types and ranges before initializing globals, and handle invalid configuration as an explicit unavailable/disabled state.

10. **MEDIUM — `covenant_leg.py:536`**  
    **Flaw:** The socket timeout and response-size limit do not impose a total response deadline.  
    **Scenario:** A malicious server sends occasional bytes before each socket timeout expires, keeping both semaphore slots occupied for a prolonged period while staying below 1 MiB. Manifest validation occurs only after this read completes.  
    **Minimal fix:** Enforce a monotonic overall deadline with cancellation, retain the byte limit, and reject an invalid manifest before reading the body.

11. **MEDIUM — `eval_tools/score_v2.py:17`, `eval_tools/score_v2.py:59`**  
    **Flaw:** The hedge regex can perform quadratic work on attacker-controlled reply text.  
    **Scenario:** A long reply containing repeated `either ` and no matching `or` makes the regex repeatedly scan the remaining suffix. The scorer imposes no reply-length or execution-time limit.  
    **Minimal fix:** Bound reply length and replace the expression with a linear scan. **UNCERTAIN:** Whether the remote client already imposes a sufficiently small response cap requires inspecting the absent `covenant_tetsu_client` implementation.

12. **LOW — `eval_tools/committee.py:28`**  
    **Flaw:** The committee scorer crashes on valid outcome labels returned from untrusted replies.  
    **Scenario:** An answerable panel reply containing “Please provide details” yields `asked_back`; the score dictionary lacks that key and raises `KeyError`, aborting the report. `echo` and `abstained` can also reach unsupported mappings.  
    **Minimal fix:** Handle every outcome emitted by `score_v2.outcome()` and provide an explicit fallback for unexpected labels.

Checked and found sound:

- Both `ALWAYS_APPLIES` guards are explicitly exempted before eligibility credit is considered.
- A471 does not change detector readings or introduce a new remedy-execution path; its normal persistence exception and kill switch remove holds.
- Non-default ledgers receive separate eligibility paths.
- The consult opener refuses redirects; remote consults with missing or wrong-length pins return before sending the POST.
- Response bytes, structured field lengths, duplicate keys, field types and confidence values receive checks. These checks do **not** establish semantic prompt-injection resistance.
- Eval scripts serialize replies as JSON and do not execute model-supplied code.
- Commitment signing and verification use matching domain framing, canonical serialization, RSA-PSS, sequence checks and predecessor hashes.

This was a source review; tests were not executed. Python was unavailable on PATH, and the supplied tests write files. No files were modified and no network commands were run.

The actual signed commitment, repository history, private configuration, filesystem permissions, gateway implementation, transport protection and downstream ethics gates were not supplied. Their deployed integrity—and whether tonight’s commitment actually covers the changed code—cannot be established from these files.

## Addendum 2026-11-23 (on Lawrence's "fix"). The table above is kept as written.

- **#6** (recorded above as NOT fixed): now FIXED by A474. The approved pins for the leg and each limb live in the
  tracked `ops/leg_policy.json`. A remote consult whose pin is not listed there is refused before sending, and the
  environment can only narrow within the list. Checks: test_a474_leg_policy.py 15/15 with two mutations; A470 21/21;
  LM1 17/17.
- **#1, its server-claim half:** still open, and it cannot be closed from the laptop. A gateway that is itself
  compromised can claim the approved hash; only an independent measurement or attestation of TETSU could prove what it
  runs. The traffic stays on our WireGuard tailnet.
