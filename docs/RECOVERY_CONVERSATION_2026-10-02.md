# Conversation continuity and unattended recovery

Verified against the proposed v8.41 source on 2026-10-02. These changes are
prepared for review. The earlier live v8.40 processes were not replaced during
this audit. Source tests do not establish a particular device's deployed state.

## Conversation

The PC replays complete user/assistant exchanges, including council exchanges,
from the caller's log. Defaults are 20 exchanges, 2,000 characters per side,
and 12,000 characters total. Long messages keep their opening and latest text,
including a correction at the end. Nonobject JSON log records are skipped.

`POST /m/agent` accepts a phone-carried `history` list. Only complete
user/assistant pairs enter context; system and tool roles are never replayed.
This supports route/address changes. History is conversation data and confers
no identity, authorization, tool authority, or grant. Network admission and
the mutual-benefit decision paths still execute.

The phone saves completed exchanges privately, scoped to its configured PC,
and restores up to 200 completed display lines. Stop invalidates requests in
the UI and context writer, including requests stopped before their worker
starts. Errors and withheld answers do not enter carried context. Physical
handset conversation quality and speech recognition remain unmeasured.

## Self-healing

The existing watchdog calls `covenant_highway.run_once()` independently of an
assistant. An exception in one remedy is now recorded and does not stop
unrelated repairs. An unavailable follow-up detector produces `unverified`,
rather than a successful repair or a measured failure used for quarantine.
Detached node restarts create the log directory and close the parent's handle.

The button's `ok` means a pass completed; `healthy` means its measured result
is healthy. Missing, invalid, empty, or UNKNOWN measurements cannot establish
health. New faults discovered afterward are reported for reassessment.
The summary and `unverified` list expose what could not be checked. Existing
pause, choice, and mutual-benefit handling remains in the highway.

Use `python covenant_heal.py --dry-run` to inspect a pass, or
`python covenant_heal.py` to request the existing remedies. The unattended
regression runs the real repair loop against reversible temporary-file
fixtures, with no model, Codex, or Claude doing the repair. It does not prove
every remedy works on every live machine.

## Restored analysis

History at `eb892c047229` removed `covenant_scenarios.py` and
`covenant_thesis.py` with the old server. Both CLI functions now use
`covenant_model.ask`, with no cloud fallback:

- `python covenant_scenarios.py --show` reads the scenario table.
- `python covenant_scenarios.py --add "name: question"` adds a scenario.
- `python covenant_scenarios.py` records probabilities, explanations,
  introspection, and a memory entry. Probabilities are model credences,
  not measured frequencies; invalid probabilities cannot produce success.
- `python covenant_thesis.py` retains chunk findings and reductions in
  `private/THESIS_<date>.md`. Missing inputs or failed analysis return nonzero.
  Later runs append rather than overwrite the earlier record.

Those private output files are not published; a reader cannot verify their
actual contents from this repository. Regression tests use temporary fixtures
to verify retained findings and append behavior, not any private corpus's
analysis or conclusions. This audit did not read the private corpus.

Scenario tables use atomic replacement. Corrupt existing tables are reported
instead of silently reset. A CLI puts away a server it started for analysis
and leaves an already-running server alone. Actual inference requires local
weights and a compatible runtime. Tests used fixture completions and do not
measure model quality. This restoration does not install a scheduler task.

## Optional Muse support

The upstream reference is Meta's
[Muse Glimmer GGUF model card](https://huggingface.co/meta-models/Muse-Glimmer-30B-GGUF).
The keeper recognizes its 17 GB Q4_K_M file only when installed and llama.cpp
reports b10353 or newer, and supplies its template/reasoning options. The
19 GiB working-memory threshold is an estimate, with existing headroom added.

Both smaller Qwen candidates remain available. Insufficient or unreadable RAM,
an unsupported runtime, or failed Muse startup preserves/returns the smaller
model path. Changed weights/runtime permit another attempt. Muse inference was
not run on this 15.3 GiB PC. Projector, drafter, and audio integration are not
claimed; existing image and speech features retain their current paths.

## Evidence and limits

Three final local rounds each passed 360 checks across eleven selected PC
suites, the eleven existing folder checks, 286 phone checks, five phone-context
tests, and seventeen Sentinel bridge/evidence tests. The 360 is the selected
sweep tally; folder-check counts are separate. Four planted defects produced
assertion failures: falsely reported repairs, privileged history replay,
invalid probabilities, and saved stopped replies.

`test_gate_proxy.py` keeps upstream and proxy sockets bound on separate ports.
Its earlier allocate-and-close probes could choose the same port, causing the
test to address the echo server directly. All gate assertions remain, with a
distinct-port premise added (24/24).

The source audit inspected removal history, sensitive execution primitives,
touched admission/outbound paths, and existing security probes. This cannot
prove that all repositories or the whole machine are free of backdoors. The
two lexical-screen paraphrase gaps in `covenant_security_probe.KNOWN_GAPS`
remain declared; downstream decisions have their own suites. Windows code
proposals still need an enforceable platform sandbox. Live exchange accounts,
funded testnet operations, and handset experience were not supplied/measured.
