# Covenant — Deployment Notes

Everything here was verified by running the system, not inferred from the source.

---

## Install and run

```bash
pip install -r requirements.txt
python3 preflight.py --genesis genesis.json --db covenant_unified_A.db   # ALWAYS run this first
python3 covenant_unified_v8.py --port 5000 --node-id A --genesis genesis.json
```

`preflight.py` exits **0** ready, **1** blocking, **2** degraded-but-launchable.
Every check in it maps to a failure that was real and *silent* during
development — a keyless node that rejects all traffic, a self-minted genesis that
can never converge, a world-readable identity key. Run it in CI and before every
launch.

Once running, `GET /health` is the single status signal: it returns `degraded`
plus a `warnings` list naming exactly what is wrong. Point a monitor at it.

A node binds **three** ports: `--port` for HTTP, `--port + 1` for P2P, and
`--port + 11` for the bridge listener. Space nodes at least 20 apart on one host.

Peer at startup:

```bash
python3 covenant_unified_v8.py --port 5000 --node-id A --peers 127.0.0.1:5101
```

Verify: `curl http://127.0.0.1:5000/chain` should return a chain of height 1.

---

## The three things that will surprise you

### 1. A node without a judge API key rejects every transaction

The ethics gate fails **closed**. With no `ANTHROPIC_API_KEY`, a node boots,
serves `/chain`, peers correctly, reports normal alignment — and denies 100% of
transactions. It looks completely healthy. This was found by running two real
nodes and wondering why nothing propagated.

Production: set `ANTHROPIC_API_KEY`.

Development only, and deliberately awkward to enable:

```bash
export COVENANT_JUDGE_PROVIDERS=mock
export COVENANT_INSECURE_MOCK_JUDGE=1     # both are required
```

That reduces the ethics gate to keyword matching. Adversarial transactions are
known to pass it. It prints a banner at boot for a reason.

Ethics-gate rejections are recorded to `/anomalies`, so a stuck gate now shows
up as a spike instead of as silence.

### 2. Node identity is a FILE now — back it up  [FIXED]

The key is now written once to `<db_path>.key` at mode `0600` and reloaded on
every start, so identity, operator credentials and the genesis mint all survive a
restart. If the file exists but cannot be read the node **refuses to start**
rather than silently minting a new identity.

Back that file up — it IS the operator credential and the genesis mint key.

Previously it regenerated on every start, with three consequences:

- A node's identity changes across restarts.
- The operator allowlist is seeded with that key, so **operator credentials for
  `/mine`, `/crisis/clear` and `POST /peers` rotate on every restart** and cannot
  be scripted across one.
- Genesis mints 1000 to the minting key. After a restart nobody holds that
  private key — the balance is stranded.

All three are resolved by persistence.

### 3. Give every node the same genesis file  [FIXED]

Two nodes started independently have **different genesis hashes and cannot
converge** — total supply also grows by 1000 per node. Verified with two real
processes.

The founder mints once and distributes the file:

```bash
# genesis.json is TRACKED and CANONICAL. Do not mint one -- a joiner never does.
# (The founder minted once; export_genesis now refuses to overwrite an existing file.)
python3 covenant_unified_v8.py --port 5000 --node-id A --genesis genesis.json
python3 covenant_unified_v8.py --port 5020 --node-id B --genesis genesis.json
```

Both then hold an identical genesis and supply is 1000 NETWORK-WIDE. A file, not
a source constant, because genesis is signed by the founder's key. It is fully
re-verified on load: hash recomputed, proof-of-work re-checked, embedded
signature re-verified.

The older database-copy workaround (no longer needed):

```bash
python3 - <<'PY'
import sqlite3, shutil
with sqlite3.connect("covenant_unified_A.db") as c:
    c.execute("PRAGMA wal_checkpoint(TRUNCATE)")   # required — see below
shutil.copy("covenant_unified_A.db", "covenant_unified_B.db")
PY
```

The WAL checkpoint is **not optional**. Without it the copy carries an empty
chain, every node silently mints its own genesis, and node construction costs 35x
more because each one re-runs proof-of-work.

---

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Semantic ethics judge. Without it the gate fails closed. |
| `COVENANT_JUDGE_PROVIDERS` | `claude` | Comma-separated: `claude`, `openai`, `google`, `mock`. |
| `COVENANT_INSECURE_MOCK_JUDGE` | unset | Must be `1` to permit the `mock` provider. |
| `COVENANT_VETO_FRACTION` | `0.5` | `phi` raises the threshold, making the gate **harder** to trip. Warns at boot. |
| `COVENANT_MAX_CONCURRENT_SENDS` | 64 | Outbound propagation workers. |
| `COVENANT_MAX_CONCURRENT_HANDLERS` | 96 | Inbound handler workers. |
| `COVENANT_MAX_CONCURRENT_FETCHES` | 32 | Address-event fetch workers — **must stay separate from sends**. |
| `COVENANT_PEER_SEND_TIMEOUT` | 5 | Seconds. 2s was too tight under load at N=1000. |
| `COVENANT_MAX_CATCHUP_BLOCKS` | 64 | Cap per self-heal gap fill. |

---

## Topology

Use a **hierarchy** (tree or clustered tree), not a full mesh. Measured at N=60:

| topology | edges | delivered | messages | bytes |
|---|---|---|---|---|
| flat random (deg 4) | 240 | 55/55 | 218 | 32.1 KB |
| 4-ary tree | 118 | **60/60** | **59** | **8.7 KB** |

Hierarchy was *unsafe* before per-hop acknowledgement and self-heal existed — a
single dropped message stranded an entire subtree. It is safe now, and messages
scale as exactly **N−1**.

---

## Optional subsystems

**Trading bridge** — attaches automatically; `node.trading_bridge` is `None` if
the module is missing and the `/trading/*` routes report "not configured".
Profit reports are **self-attested**: sequence numbers prevent replay and
reordering, not lying. A compromised pool key can mint spendable balance.

**Neural bridge** — telemetry only, `None` without `brainflow`. It never gates
signing, authentication or any chain action; the module docstring gives the
measured reason. `SpikingAnomalyMonitor.observe()` expects **epoch** seconds;
relative timestamps are anchored to now and counted in
`/anomalies.nonepoch_observations` rather than silently vanishing.

---

## Known limitations

- **Finding U** — off-chain credits (`genesis_mint`, `trading_profit`,
  `node_gift`, `stake_lock`) never appear in blocks, so chain sync alone cannot
  reconstruct balances. A synced node will *reject* blocks whose senders it
  believes unfunded.
- **Live XRP signing unimplemented** — the bridge records reports of trades
  executed elsewhere.
- **No multi-core validation** — all scale figures come from one process on one
  CPU, and the largest full-stack (HTTP serving) run was single digits.

Fixed since the previous revision: canonical genesis, persistent node identity,
and transaction address-event propagation (1243 bytes -> 134).

---

## Verifying an install

```bash
./run_all_tests.sh          # everything: integrity, security, crypto, ethics, trading, propagation
python3 preflight.py        # launch readiness for THIS host and config
```

Individually:

| command | covers |
|---|---|
| `verify_bundle.py` | tamper-evident manifest over all shipped files |
| `verify_patches.py` | the regression fixes are still present |
| `verify_auth.py` | operator authentication (12 checks) |
| `test_security_audit.py` | **99** security checks — shape, bounds, idempotency, ghost controls, governor liveness, Finding U |
| `test_path_pattern.py` / `test_succession_seal.py` | path-dependent sealing (37 checks) |
| `test_ethics_judge.py` and friends | ethics gate (41 checks) |
| `test_v86_bridge.py` / `test_v86_loss_tracking.py` | trading bridge (45 checks) |
| `verify_tx_aer.py` | canonical genesis + transaction propagation |
