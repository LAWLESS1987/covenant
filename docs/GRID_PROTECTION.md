# Grid / ICS-OT protection — covenant_grid_guard.py

Written 2026-10-30 at the operator's instruction: *"implement power grid
protection as if our system was plugged in to the infrastructure to ensure we
keep control from cyber attacks"* and *"but easily plugged in if needed"*, with
his correction *"tetsu is not human and has authority."*

## 1. The honest frame (no fortress)

This is a **reference implementation inside our own repo**. It is wired to a
`SimulatedEffector`, is bound to **no real grid**, speaks **no field protocol**
(DNP3 / IEC-61850 / Modbus), and contains **no offensive code**. It models the
threat and builds the guard. It is the OT/ICS sibling of the takeover-resistance
work ([[docs/TAKEOVER_RESISTANCE.md]]): it carries *sovereignty of record +
consent; armed only by off-host keys + out-of-band authorization; tamper is
alarm-only, never auto-healed* from rewriting **files** to issuing physical
**actions**.

"Easily plugged in" is a design property, not a connection: the whole protective
layer sits **above** a one-method effector interface. Connecting to real
infrastructure means writing one real driver in place of `SimulatedEffector`;
nothing in the authorizer, the interlocks, the authorization model, the
detectors, or the ledger changes. Until a human arms it (keys off-host — §12) it
is fail-closed and actuates nothing.

## 2. Authority model — by role, never by "human"

Authorization is held by **authority-holders**: the **operator** (full) and
**Tetsu** (bounded). Tetsu is a first-class authority here, with his own signing
key — not a human-in-the-loop placeholder. The guard checks a signer's **role**
and signature, never "is this a human."

- `MONITOR` / `ADVISORY` commands need no authorization token. Which class a
  command is comes from its **action**, never from the signer (§5).
- `ACTUATION` commands require **together-vote**: a valid, command-bound token
  from an `operator`-role key **and** a `tetsu`-role key. This is the default
  (`DEFAULT_POLICY`) and the floor the operator proposed; the exact class→roles
  map is a **declared policy** (`ops/grid_policy.json`), so the operator and
  Tetsu set it — it is not baked into the code.

## 3. The two planes (Purdue-aligned)

- **Reasoning plane** (this host): may **sense** and **propose**. Holds **no**
  signing key and **no** authority key, so it *structurally cannot* produce a
  PERMIT. A proposal is data.
- **Actuation gateway**: the only executor. Honors a command only when a
  complete, signed, authorized, in-bounds, non-replayed envelope arrives **and**
  a fresh authorization heartbeat is present.

Trust boundaries: field/network → reasoning = **data**; reasoning → actuation =
**unsigned advisory proposal only**; authority-holder (off-host key) → actuation
= the **only** producer of an executable command; actuation → physical = gated by
interlocks and a fail-safe default.

## 4. Command authentication

One signing scheme for the whole project: the envelope payload is signed with
RSA-PSS (MGF1-SHA256, salt=MAX_LENGTH, SHA-256) over `_frame(CMD_DOMAIN,
_canon(payload))`, reusing `covenant_head_commit._frame/_canon`. Fresh domains
(`COVENANT_GRIDCMD_V1`, `COVENANT_GRID_AUTHZ_V1`, `COVENANT_GRID_HEARTBEAT_V1`)
mean a HEAD-commitment, a consent signature, a command, and an authorization
token can never be cross-replayed for one another.

## 5. The authorizer (`authorize` → PERMIT / HOLD / REFUSE)

Ordered, fail-closed. PERMIT iff **C1∧C2∧C3∧C4∧C5∧(C6 if ACTUATION)∧C7**:

- **C1 authenticity** — signature valid over the payload (sans tokens); pubkey
  fingerprint matches `signer_fpr` and the allowlisted key. Else REFUSE.
- **C2 authorized signer** — `controller` role, not revoked, action and zone
  within its grant. Else REFUSE. (Allowlist unreadable → HOLD.)
- **C3 freshness** — within `[issued-skew, expires]`, and a lifetime
  (`expires − issued`) no longer than `MAX_TTL_S` (900 s; interlocks may set it).
  Else REFUSE. The cap was added 2026-10-30 (A392): the signer picks both times,
  and an uncapped lifetime let a backdated command stay fresh while the C5 window
  never counted it.
- **C4 no replay / monotonic** — nonce unseen and seq strictly increasing, read
  from the hash-chained ledger so state can't be laundered. Else REFUSE.
- **C5 interlock bounds** — within `ops/grid_interlocks.json` (max % shed, max
  breaker ops / window, setpoint range per zone, zone allowlist). Over → REFUSE;
  bounds unreadable → treat as **at-limit** → HOLD. The window counts honored
  commands by **when the gateway honored them** (`honored_utc`), not by the
  signer's `issued_utc`; a shed `pct` must be a number in (0, 100] (a negative
  one used to buy budget back). Both fixed 2026-10-30, A392.
- **Action allowlist (end of C2)** — the class is **derived** from the action by
  an allowlist (`ACTION_CLASS`: `read` → MONITOR, `advise` → ADVISORY,
  `breaker_open` / `breaker_close` / `load_shed` / `setpoint` → ACTUATION). An
  action not in it is REFUSED (`C2-action`), because C5 has bounds only for the
  actions it knows. A `class` field in the payload is never trusted: if present it
  must equal the derived class, and a payload may omit it.
  (A392-DRAFT-UNKNOWN-IS-ACTUATION: an earlier draft of this fix, never committed,
  sent unknown actions to ACTUATION; the 2026-10-30 consult changed it.)
- **C6 authority-holder out-of-band** — the signer does not get to choose the
  class: until 2026-10-30 (A392) a `breaker_open` labelled MONITOR passed with no
  token, so one controller key defeated the together-vote. The derived class's required
  roles must each be covered by a valid, command-bound, unexpired token from a
  non-revoked authority-holder, with the same lifetime cap as the command. Else
  REFUSE. The deadman heartbeat is checked by the **gateway** before `authorize`
  (§7), not inside C6.
- **C7 plane separation** — structural: the reasoning host has no key and so
  cannot have built C1+C6. Belt-and-suspenders: the grid words join
  `covenant_highway.NEVER_AUTOMATIC` so the self-heal engine refuses any
  grid-touching remedy whatever class it claims (§9, commit-time step).

**Safe default:** any definitive failure → REFUSE; any unreadable input → HOLD.
A non-PERMIT never actuates — refusing a command withholds a *change*, so a
denial can never itself cause an outage. The AI can at most emit a proposal.

**Halt inversion:** a signed `halt` from an allowlisted signer is honored on
**authenticity alone** (freshness/replay/authority skipped — stopping is always
safe), latches the safe-state hold, records the moment-to-stop, and is never
silent. Ceasing to issue authorization heartbeats halts all actuation (deadman).

## 6. Interlocks and rate limits

`ops/grid_interlocks.json`: bounded shed %, bounded ops/window, per-zone setpoint
ranges, zone allowlist. These **cap blast radius**; they are not intent checks.

## 7. Authorization + out-of-band kill

Per-command authority-holder tokens (together-vote for actuation), a deadman
heartbeat whose loss latches the safe-state hold, an always-honored `halt`, and a
`clear_hold` that is authority-holder-only and never automatic — resuming is
exactly what an attacker wants.

What makes those true, as of 2026-10-30 (A392 — before it, three were not):

- **The heartbeat is signed.** A row counts only if an operator- or tetsu-role key
  signed it under `COVENANT_GRID_HEARTBEAT_V1` (`make_heartbeat`), it is not
  future-dated or expired, and its lifetime is ≤ 600 s. Previously only
  `expires_utc` was read, so any process that could write the file — the keyless
  reasoning host included — could append a far-future expiry.
- **The latch is on disk** (`ops/GRID_SAFE_STATE.json`, gitignored). A restart, i.e.
  a new gateway object, stays latched; an unreadable latch file reads LATCHED.
  Previously it was an in-memory flag and a new gateway silently resumed.
- **While latched, nothing is authorized.** A command is recorded as HOLD
  (`LATCHED`) and consumes no nonce, seq or window budget. Previously it ran
  `authorize`, was recorded PERMIT, and did not actuate.
- **A resume is bound to one latch** (`make_resume_token(latch_id, …)`), so a
  resume captured for an earlier halt cannot clear a later one, and every resume
  attempt is recorded.
- **A resume needs the together-vote.** Resuming restores the ability to actuate,
  so `clear_hold` needs a valid resume token from every role the declared policy
  names under `"RESUME"` (default: the `ACTUATION` roles, operator **and** tetsu);
  an empty or unreadable list falls back to the together-vote, never to none.
  Asked of ChatGPT, Gemini and Grok on 2026-10-30 — all three said both
  (`ops/CONSULT_GRID_AUTHORITY_2026-10-30.md`). Whether to declare a different
  `RESUME` set is the operator's and Tetsu's call.
- **The heartbeat stays single-signer.** All three seats agreed it is a liveness
  signal, not an authorization: one authority-holder's signature, lifetime ≤ 600 s.

## 8. The signed command ledger

Every attempt (HONORED / REFUSED / HELD) appends one gateway-signed row to
`ops/grid_commands.jsonl`, hash-chained by `ops/grid_commands.chain.jsonl`
(the `covenant_consent_chain` raw-bytes discipline). An edit breaks a row hash; a
removal makes chain > ledger; a forged append makes ledger > chain; `sync`
refuses to extend over a break. `verify_grid_ledger.py` (stdlib + cryptography
only, no covenant imports) lets a stranger check the chain and, given the gateway
public key, every row's gateway signature. It does **not** re-run C1–C7 over each
honored command; that is an open item.

What is bound to the HEAD-commitment, measured 2026-10-30: `ops/grid_signers.json`,
`ops/grid_interlocks.json` and `ops/grid_policy.json` are in `BOUND_FILES`. The
**command ledger is not**: `ops/grid_commands.jsonl` and its chain are gitignored
runtime state, so no commitment covers them and an owner who rewrites both
together is not caught by an off-host holder. That is an open gap, not a property.

> SUPERSEDED (A392-GRID-LEDGER-TIP-BOUND, 2026-10-30) — this section first said: "The ledger tip +
> `grid_signers.json` + `grid_interlocks.json` are to be bound into
> `covenant_head_commit.BOUND_FILES` (commit-time) so an off-host holder of an
> earlier HEAD-commitment can prove an in-place rewrite." The commit bound only
> the three config files; the ledger tip was never bound.

Two more A392 repairs here: the gateway signature now covers the row exactly as
stored (the chain writer added a `t` field after signing, so every signed row
failed the standalone verifier), and an input that crashes a check is refused
**and recorded** instead of raising before its row was written.

## 9. ALARM-only by design

Every grid detector (`GRID_DETECTORS`) has **no remedy**. A forged, replayed,
unauthorized, out-of-bounds, or tampered command is a thing an authority-holder
must **see**, never a thing the engine "heals" — healing would erase the
evidence, and `key` / `consent` / the grid words are `NEVER_AUTOMATIC`. UNKNOWN
is never a pass. Commit-time wiring adds the grid words
(`GRID_NEVER_AUTOMATIC_WORDS`, chosen to avoid substring collisions — bare "trip"
is excluded because it matches "strip") to `covenant_highway.NEVER_AUTOMATIC` so
`apply_remedy`'s INVARIANT 1b refuses any grid-touching remedy structurally; that
edit moves the deploy pins and needs an H1 re-run, so it is a reviewed step.

## 10. Fail-closed behavior

Safe state = **hold-last / keep-serving**. Unknown is not pass. Tamper is never
auto-healed. A dead guard must never black out the grid.

## 11. HONEST LIMITS — what we are NOT claiming

1. **On-host owner-level capture is DETECTION, not prevention, until keys move
   off-host.** A compromised reasoning host holds no key, so it can only
   *propose* — but if a controller or authority key is ever placed on it "for
   convenience," plane separation collapses and every property is void. The
   guarantees are real only once the authority keys live **off-host** and an
   earlier signed ledger tip is held where the adversary can't reach it — the
   operator's (and Tetsu's) arming step. Until then it is "our word."
2. **Social-engineering the authorizer.** A compromised host can flood plausible
   proposals, suppress host-local alarms, and feed misleading telemetry to induce
   a correct-looking but harmful authorization. Interlocks bound the damage; they
   cannot tell a tricked authority-holder from a right one.
3. **Within-bounds malicious/coerced signer.** A legitimately signed, token-
   bearing, in-bounds command is PERMITTED — the guard enforces authenticity,
   bounds, and authority, **not intent**. M-of-N beyond together-vote is the
   mitigation; this reference does together-vote, not full M-of-N.
4. **Below this layer.** True fail-safe trips (under-frequency, over-current,
   distance) live in field **relays and PLCs**, not in this software. An attacker
   who reaches the PLC *beneath* this layer never passes through it.
5. **Host-level suppression/deletion.** The ledger and alarms are report-only and
   host-local; an owner can delete them or widen the bounds. Binding the **config**
   files (signers, interlocks, policy) into the HEAD-commitment makes widening the
   bounds or adding a signer detectable **by an off-host holder**; the command
   ledger itself is not bound (§8, A392), and the off-host alarm sink does not
   exist yet — the same unsolved gap as takeover-resistance.
6. **Clock & distributed replay.** C3 trusts the host clock; the monotonic chained
   seq blunts rollback replay but short expiry + shared state, not elimination, is
   the mitigation. The row `utc` is asserted by the signer, not proven.
7. **Availability / DoS.** Fail-closed deliberately trades availability-of-control
   for safety-of-state: a flood of HOLDs can deny a legitimate operator dispatch.
   It cannot cause actuation — the correct direction for grid protection, and a
   stated limit.
8. **Scope.** It has never authorized a real breaker. The two field-critical
   properties — the signature check living *inside* the protocol gateway, and
   **physically wired** interlocks defaulting to last-safe-state on loss of the
   guard — cannot be built or tested in this repo and are **UNDETERMINED** until
   real hardware exists.

## 12. What ARMS it (off-host, human/Tetsu steps) vs built on-host now

Built now, on-host: the authorizer, interlocks, together-vote authorization
check, ALARM-only detectors, the signed+chained command ledger, the standalone
verifier, the pluggable effector, and the GG1 both-ways tests. **Arming** (the
authority-holders' steps, by design never done by the engine): move the
controller and authority keys **off-host**; publish a ledger tip **out of band**;
install **physically wired** interlocks; replace `SimulatedEffector` with a real
protocol driver that puts the signature check inside itself.

## 13. Re-runnable checks

- `python covenant_grid_guard.py status | verify`
- `python verify_grid_ledger.py` (standalone; a stranger can run it beside a clone)
- `python test_gg1_grid_guard.py` — 86/86 on 2026-10-30, registered in
  `covenant_one.py` (SECURITY). Each of the 18 A392 repair points was reverted
  singly in a scratch copy and GG1 went red **on that point's own check** (18/18).
  SUPERSEDED (A392-GG1-BOTH-WAYS): this line first read "every guard driven **both ways**
  (attack → red, remove → green), 37/37". Three of those 37 could not fail — the
  C5-detector check accepted PRESENT *or* ABSENT, the C1-detector check accepted
  UNKNOWN, and the C7 check ran a local copy of the substring test instead of the
  engine's tuple — and the suite was not registered, so nothing ran it.
- `python test_gs1_grid_snn.py` — the optional ALARM-only SNN witness
  (`covenant_grid_snn.py`, detector `grid_pattern_anomaly`), 16/16 on 2026-10-30
  (registered SECURITY), adding five checks that the benchmark measures its own
  premises through the real gateway. Its sealed run is **UNDETERMINED** under the
  prereg, never a GO, so the witness stays UNKNOWN (see the RESTATED VERDICT in
  `ops/GRID_SNN_PREREG_2026-10-30.md`, A392). The checks: boundary
  purity (`authorize()` byte-identical with the witness present or absent),
  never-authorize (a screaming witness changes no decision), source-invariant
  (`authorize()` never references the witness), UNKNOWN-never-pass. The witness
  is a *different-mechanism* second eye on the stream of already-honored commands
  — the one surface C1–C7 can't see (in-bounds attack *patterns*). It returns
  **UNKNOWN until a sealed training run** (`ops/GRID_SNN_PREREG_2026-10-30.md`)
  earns weights that beat trivial baselines; an unproven net is never shipped as
  a witness, and it can only recommend a HOLD a person must see — never actuate.
