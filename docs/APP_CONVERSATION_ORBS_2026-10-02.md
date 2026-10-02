# Conversation, orbs and continuing refinement

Verified in separate review checkouts on 2026-10-02. These changes are prepared
for review; source checks do not establish an installed PC or phone's state.

The PC orb page defaults to **Talk**, through `/m/agent`, with Tetsu's existing
work, web and repair tools. **Council** remains selectable through
`/pc/council`. Both accept bounded complete conversation pairs as data. Stop
cancels browser speech and suppresses obsolete replies; Mic interrupts a turn
and sends a new utterance. Already admitted server work may still finish.
Scalar log records no longer break the browser's conversation history.

Android speaks complete answers in engine-sized chunks. Only the current final
chunk can resume hands-free listening; obsolete callbacks, background activity
and duplicate recognizers cannot. Stop interrupts TTS. Mic barge-in sends the
new utterance. Disabled/unavailable speech has an explicit completion path.
The phone remembers twenty complete exchanges per PC for eight recent peers
without mixing contexts, and displays context-save failures.

## Retried work

For clients supplying `request_id`, authentication precedes a process-local
reply cache. Identical retries return the recorded result; changed payloads
with the same id are rejected. Pending turns return an explicit in-progress
response and are not executed twice. Failures and withheld replies are retained.
Old clients without ids keep the ordinary route behavior.

When a LAN fallback address is known and its existing key can sign, the phone
signs the initial conversation request and uses a fresh nonce for a signed LAN
retry. Verified
public-key identity associates both roads and distinguishes two keys at one
address. A supplied signature that does not verify cannot fall back to another
unsigned identity. Unsigned tailnet callers remain supported, including a new
phone without a known LAN fallback. A cached LAN address does not prove current
key registration; a changed PC or revoked key can require registration again.
An unverified
public-key header is never an authenticated identity.

The cache holds at most 256 turns per door and retains completed results for
600 seconds after completion. Pending records are not evicted; a hung operation
can occupy a slot until restart. Restart, expiry, a different id/endpoint and
an unsigned caller changing address end the corresponding protection. This is
not durable exactly-once execution. Regenerate starts a new turn. Replay
acknowledges the original decision and work; it does not execute another act.

## Orb controls

`/pc/3d/state` adds an `orbs` inventory with stable ids, names, status, summaries
and details. Every item has keyboard-accessible PC controls, even without
Three.js or WebGL. The existing scene and picking controls remain. Selected
details refresh with state. Android's **System orbs** screen reads the same
inventory through the existing tailnet/signed-LAN route, with Refresh and
Connection settings, polling every 30 seconds only while foregrounded.

Orb selection is informational. Each green condition concerns its stated
measurement, not global safety or proof of mutual benefit. Missing, malformed
or unrecognized Highway readings stay unknown; all seven detectors must report
absent before its orb is clear. Node warnings and failure reasons are carried.
Peer addresses alone do not prove a phone or its health. Tetsu's information
orb does not measure consciousness or answer quality. Failed phone reads mark
retained rows unknown instead of presenting old green rows as current state.

## Tetsu's work and learning

Existing HEAL, HANDS, practice, analysis and proposal capabilities remain.
Application watchdogs drive their own work; the Codex monitor is an independent
observer. Persona refinement sees paired operator/Tetsu exchanges and recorded
verdict flags: at most twelve records, 600 characters per side and 6,000 total.
Records are evidence data, not instructions or a quality score. Work callers
and blocked conversation feedback remain excluded.

Unavailable, exception and invalid-model attempts retain uninspected feedback
and retry after 300, 600, 1,200 and 2,400 seconds, capped at one hour afterward.
Recovery can inspect feedback without a new human message. Inspected no-change,
voluntary decline, block and gate refusal end that round. Fixed rules, bounds,
contestation and choice remain. This refines a recorded persona; it does not
train GGUF weights or deploy arbitrary source proposals. The broader Windows
source-application path still needs an enforceable sandbox.

## Evidence and limits

Three final Windows/Python 3.12 rounds passed twenty test programs: 343 checks
across fourteen selected PC suites; 286 phone source checks; 24 context cases;
ten orb-transport cases; 42 executed Java controller checks; seven Activity
wiring checks; five emulator-evidence parser cases; and structural scans of
nineteen Java files. These scopes are separate from a full sweep or Android
compilation. Ten PC orb cases execute the real inline JS in a mock browser.
Real temporary-key tests verify identity, nonce checks and one HEAL action
across both roads. Five planted reply-cache defects caused assertion failures.

CI additionally compiles the APK and exercises its native orb tap path and
existing node/idle/Stop/restart checks. Consult actual PR checks for platform
evidence. Physical handset conversation quality, browser WebGL rendering,
model quality and live network handovers remain unmeasured. Existing declared
security-screen gaps remain; no scan proves that backdoors are absent.

The first full Windows sweep at `42150ea` passed 4,698 checks and failed the
strict Merkle stability check. The watchdog tests had left unrelated Highway
and refinement callbacks live, allowing test-node maintenance to run during an
offline check. Shared test fixtures now isolate those callbacks and reject
known process and network boundaries; outage decisions and the self-evaluation
ledger still run. The Merkle assertion still compares two complete roots and
reports changed paths and sizes on failure. These are test-only boundaries;
the application's independent watchdog capabilities remain enabled. Consult
the final review checks for the full rerun result.
