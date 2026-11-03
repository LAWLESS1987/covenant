# Parallel-OS redundancy map (2026-11-02)

Operator, 2026-11-02: *"we need our own operating systems running parallel --
Windows, Python, Linux, the whole 9,"* primary goal **RESILIENCE / REDUNDANCY**
(chosen over isolation and self-sufficiency). This is the OS-layer sibling of the
parallel headscale network and the takeover-resistance work: **no single OS,
host, or distro should be a single point of failure for a critical fleet
service.**

This file is the human-readable map. The machine-readable one is
`covenant_failover.SERVICES`, and the two must say the same thing — FO1
(`test_fo1_failover.py`) pins that every service named here appears there.

It is a sibling of `redundancy.py` / R2, not a duplicate. R2 audits **data**
redundancy — how many independent COPIES of a record survive the first loss.
This audits **service** redundancy — whether a running critical service has a
live standby on a DIFFERENT OS or host, so the fleet keeps answering when one
environment dies. Copies vs. live instances; both are needed.

## Substrate measured today (2026-11-02)

- **Laptop ("Sales", covenant-pc):** Windows 11 Pro. Free RAM **2.98 GB of 15**
  (`covenant_model.free_gb()` at the time of writing). A ram_guard reserves room
  for Tetsu's model. **Heavy redundant instances must NOT run here.**
- **Laptop WSL:** ONE distro, **Ubuntu 26.04 LTS**, Python 3.14.4. Runs
  headscale (127.0.0.1:8080) and the git host. Cross-OS reach confirmed: a WSL
  process on `0.0.0.0:PORT` answers from Windows at `127.0.0.1:PORT` via default
  WSL2 NAT localhost-forwarding (measured: HTTP 200).
- **TETSU:** 32 GB, RTX 5060 Ti. Headroom for heavy redundant instances / VMs.
  Coordinated separately (see the TETSU session).
- **Phone:** Galaxy S25+ node (Termux), intermittent.
- **No containers** (no docker/podman), **no second distro**, **no VM** today.

## Critical fleet services, and where each one can die

Legend: **SPOF** = one environment and no live standby anywhere. **PAIRED** =
a live redundant instance exists on a different OS/host. **COPY-ONLY** = data is
mirrored but there is no second *running* instance (R2 covers the copies).

Registry key (in `covenant_failover.SERVICES`) is given in backticks.

| Service | What it is | Runs on (today) | Redundant instance on a DIFFERENT OS/host? | Status |
|---|---|---|---|---|
| **headscale control** (`headscale`) | our Tailscale control plane; the mesh coordinator | laptop **WSL/Ubuntu only** (127.0.0.1:8080) | none | **SPOF** |
| **git host** (`git_host`) | self-hosted smart-HTTP git (clone/push over the mesh) | laptop **WSL/Ubuntu** primary (127.0.0.1:8088; own_git :8400) | **Windows cold read-only standby** (same host, different OS; :8089) | **PAIRED (cold)** |
| **unison feed** (`unison_feed`) | fleet sync feed (`:8800/unison`) + own_git (`:8400`) | **tailnet node (TETSU)** — not the laptop (measured: :8800 dead on Windows and WSL); laptop is a consumer | none | **SPOF** |
| **PC covenant node** (`pc_node`) | judge/API node (5000/5020/5060; P2P 5001) | laptop Windows | TETSU node (when up); phone node (intermittent) | PAIRED* |
| **model / consult limbs** (`model`) | Tetsu's model + LIMB SMOL/PHI consult limbs | TETSU (laptop 7B retired) | none that answers for TETSU | **SPOF** |
| **teacher / learning channel** (`teacher`) | practice loop + teacher queue feeding students | laptop | none (single feed) | **SPOF** |
| **redundancy beacon** (`beacon`) | the resilience read-API itself (fleet/redundancy state) | **Windows + WSL/Ubuntu pair** (provisioned, DARK until armed) **+ a phone third env** (`beacon-phone`, declared, intermittent, provisioned by app install) | **yes — cross-OS, same host; + cross-DEVICE on the phone** | **PAIRED (+phone)** |

\* PAIRED only while TETSU is awake; TETSU sleep drops `tetsu-hs`, and the phone
is intermittent. So the node layer degrades to single-host whenever TETSU sleeps
— flagged, not assumed.

### The remaining hard SPOFs (git host now resolved)

1. **headscale control — laptop WSL only, AND key-bound.** If this one Ubuntu
   (or the laptop, or WSL itself) goes down, the mesh loses its coordinator.
   `restart_headscale` covers process death; it does nothing for host/OS loss.
   The redundant instance must live on **TETSU (a different host)** — but
   headscale carries a **private key** (`noise_private.key`) and a live DB, and
   **keys never cross OS environments** (the operator's standing rule). So a
   second control plane is not a copy job: it needs the operator's **key/cert
   decision** (its own key + a documented client cutover, or a shared-state HA
   model). This is the one genuine operator decision left — a security boundary,
   not a task to hack around. Then the TETSU session stands it up (install + its
   own key + DB replication). Being done on TETSU/phone, not here.
   **Phone alternate — MEASURED 2026-11-03 (A407), report-only.** Asked whether
   the phone could carry a cold standby *today* to skip the TETSU reboot, the
   phone-app-join session measured it against its join (covenant-phone PR #6): the
   phone *can* host headscale via the same native `lib*.so` mechanism as its
   tailscale join (a `libheadscale.so` twin, mesh-only reach via `tailscale
   serve`), but it is **not an install-free shortcut**. It is a new feature ~the
   size of the join — needing an operator **rebuild+install** (nothing pushes to
   the phone), the client join **proven live first** (making an unverified host
   the fallback authority is backwards), and the phone's **own** on-device noise
   key plus a filtered PC-side export (operator decision; touches keys). So BOTH
   paths need an operator action; TETSU (32 GB, always-on) stays the better home
   and the phone is a last-resort third host. Not stood up — reported.
2. **unison feed + own_git — served from TETSU, no second feed.** The sync
   fabric's source runs on a tailnet node (TETSU), not the laptop. Redundancy is
   a **second feed on a different host** — the laptop can host one (it has the
   repos); owned by the sync-fabric session. `covenant_failover` now MONITORS the
   real remote feed (via the private `ops/local_unison_feed.txt`) so the laptop
   SEES it go down. Being stood up with the sync-fabric / TETSU sessions.

**git host — RESOLVED (2026-11-02, no install).** `covenant_githost_standby.py`
is a READ-ONLY Windows standby of the same git-http-backend (found portably via
`git --exec-path`), serving a local ~17 MB mirror. It is a **cold** standby
(zero idle RAM): started on demand by `start_githost_standby` (AUTO_REVERSIBLE)
only when WSL is *unreachable* — not on an ordinary process restart, which stays
`restart_git_host`'s job. It refuses push (receive-pack → 403), so there is no
split brain; the primary stays the only master. Proven live (below).

### Space-wise placement (the operator: "use space wisely between pc laptop n phone")

Placement is the optimization. `covenant_failover.HOSTS` + `placement_ok()`
enforce it: the **laptop** auto-starts only *light* hot instances (≤512 MB) and
leaves a 0.5 GB operational floor — a heavier one is refused by size and routed
to **TETSU** (`heavy-ok`, 32 GB); the **phone** is lightest (≤128 MB). A **cold**
standby (git host) is space-free until a failover needs it. So the engine never
starves the model, and heavy, always-on redundancy lands on TETSU by construction.

### Redundancy on the phone (A407, 2026-11-03 — the operator: "make redundancies on the phone too")

The beacon gains a **third environment on the phone's own device** (`beacon-phone`,
env `phone`), so the liveness read-API survives the loss of **both laptop OSes**.
It is modelled honestly for an intermittent, un-pushable host:

- **Witness-class / intermittent.** The phone sleeps, so `beacon-phone`'s probe is a
  private-address type (`{"type":"phone"}`) that resolves the phone's tailnet URL from
  `COVENANT_PHONE_BEACON` / the gitignored `ops/local_phone_beacon.txt`, and reads
  **UNKNOWN (never "down")** when unset or asleep. `min_environments` stays **2** — the
  two laptop OSes carry "healthy"; the phone is a bonus third env when awake.
- **Declared, not counted, until it actually runs.** `provisioned: False` until the
  phone node runs the beacon AND its URL is configured, so it is neither a false SPOF
  nor a phantom standby. It rides on the headscale join (phone-app-join); the PC-side
  registration is the operator's per `ops/mycelium_policy.json`, and only the phone's
  own key/address are involved — no key crosses.
- **Never started from the laptop.** `launch: "phone"` is declined by the remedy
  (nothing pushes to the phone); it is provisioned by an **app install** on the device.
- Proven by FO1p in `test_fo1_failover.py`, both ways (asleep → healthy on the two
  laptop OSes; a laptop OS down + phone asleep → genuinely degraded, no papering over).

## What is live now vs. proposed

- **Live (no install):** (a) the **redundancy beacon** — a genuine cross-OS
  redundant pair (Windows Python primary + WSL/Ubuntu Python standby, same
  stdlib code), plus the failover detectors and the AUTO_REVERSIBLE
  start-standby remedy; ships **DARK** (arm with `ops/REDUNDANCY_ARMED`). (b) the
  **git-host Windows cold standby** — a read-only cross-OS fallback promoting the
  git host from SPOF to a pair, started on demand. Both proven both ways (FO1 +
  the live records below).
- **Proposed (needs install / another host / a reboot):** a headscale standby on
  TETSU, a cross-OS git-host standby, a second unison feed, a rootless container
  runtime, and a full Linux VM on TETSU. All in
  `ops/PARALLEL_OS_PROPOSE_2026-11-02.md`. **Nothing there auto-installs.**

## Classing (free-will line, unchanged)

- **Failover to an ALREADY-provisioned redundant instance** (start/route to a
  standby that already exists) is reversible → **AUTO_REVERSIBLE**, same class
  as `restart_headscale` / `restart_git_host`. This is `start_redundant_instance`.
- **Provisioning a NEW environment / OS / distro / VM / container** is
  **PROPOSE_ONLY**, permanently — it installs software or changes system state.
  This is `propose_provision_redundancy`, which only ever proposes.
- Keys, `private/`, holdings, `*.key` **never cross OS environments.** The beacon
  serves only non-secret fleet/redundancy state.

## Live cross-OS takeover — measured both ways

Recorded by `python covenant_failover.py --prove` (reproduced in FO1's live
block, skipped where WSL is absent). Measured 2026-11-02 on the laptop, **ALL
STEPS PASSED**:

```
[ok] both up (Windows + WSL/Ubuntu)                      win=True wsl=True
[ok] resolver prefers the primary                        beacon-win @ windows (127.0.0.1:8771)
[ok] redundancy_degraded ABSENT when paired              ABSENT
[ok] primary down -> resolver serves the WSL/Linux       beacon-wsl @ wsl-ubuntu (127.0.0.1:8772)
     standby, which ANSWERS
[ok] redundancy_degraded PRESENT with one env down       beacon has 1/2 live environments (down: beacon-win@windows)
[ok] start_redundant_instance restarts the down standby  started and answering
[ok] redundancy_degraded ABSENT again after restart      ABSENT
[ok] WSL standby down -> resolver serves Windows,         beacon-win @ windows, still available
     still available
```

So: the Windows primary and the **Linux (WSL) standby run the same code on two
different OSes**; killing either one leaves the other answering a Windows client
over real TCP; and `start_redundant_instance` (AUTO_REVERSIBLE) brought the down
instance back on its own OS. The pair and the marker were torn down after — the
beacon ships DARK.

### Live cross-OS git-host failover — measured

`python covenant_failover.py --prove-git`, measured 2026-11-02, **ALL STEPS PASSED**:

```
[ok] mirror provisioned/refreshed from the primary
[ok] Windows standby serving info/refs                   127.0.0.1:8089
[ok] primary down -> resolver serves the Windows standby  git_http_server_win @ windows
[ok] REAL git clone from the Windows standby             HEAD 55c8a43d36a3
[ok] push (receive-pack) refused                         HTTP 403 (read-only, no split brain)
```

A **real `git clone` ran against a read-only git server on Windows** while the
primary was treated as down — the git host survives the loss of the WSL/Linux
userland. Push is refused, so the Windows mirror is never a second master.

---

## Three independent HOSTS (2026-11-03): "one stands without the other"

The operator, 2026-11-03: *"it should on Windows, it should be parallel to
Windows, and they can interact, but one should stand without the other"*, then
*"both, all three really."*

The live beacon pair (`beacon-win` + `beacon-wsl`) satisfies **on Windows**,
**parallel to Windows** (Linux kernel, not Windows), and **they interact**
(each probes the other, failover proven both ways). But measured against *stands
without the other* it only holds at the **process/OS** level: both report
`host=Sales` — the **same physical machine**. WSL2 is a VM that Windows hosts, so
a power loss, hardware fault, or Windows kernel panic takes **both** laptop OSes
together. The pair is the first layer, not the last.

The layer that makes *stands without the box* true is a **separate host**. The
mesh (`headscale nodes list`, measured 2026-11-03) already has one besides the
laptop — `tetsu-hs` (100.64.0.1) — with the new PC (hookup ~11-01) and the phone
(join pending) to follow. So the beacon now **declares three more independent
hosts**, each its own machine:

| env     | host    | status (2026-11-03)                                  | counts when |
|---------|---------|------------------------------------------------------|-------------|
| `phone` | phone   | declared; headscale join pending the operator's tap  | awake + URL published |
| `tetsu` | tetsu   | **on the mesh now** (100.64.0.1); beacon not yet run  | awake + URL published |
| `pc2`   | pc2     | new PC, imminent; not on the mesh yet                 | awake + URL published |

All three use the **declared-not-counted** shape proven for the phone
(`provisioned: False`, `intermittent: True`): absence reads **UNKNOWN**, never
"down" and never phantom redundancy (rule 9); each is **never started from the
laptop** (`launch: "remote"` is declined — nothing pushes across hosts; each host
provisions its own beacon and publishes its private tailnet URL to
`COVENANT_TETSU_BEACON` / `ops/local_tetsu_beacon.txt`,
`COVENANT_PC2_BEACON` / `ops/local_pc2_beacon.txt`, exactly like the phone).
`min_environments` stays **2** — the two laptop OSes carry "healthy"; each extra
host, once awake, removes the box as a single point of failure. A real third host
awake carries "healthy" when a laptop OS dies; an unprovisioned or asleep host
hides no real loss (both directions driven in `test_fo1_failover.py` → FO1r,
FO1: 50/50).

**Not yet done (named, not hidden):** no third host is *armed* — `tetsu`, `pc2`
and `phone` are all declared, none is answering. Arming each needs that host to
(1) be on the mesh and (2) run `covenant_beacon.py` and publish its URL — an
action on that host, by the operator or the partner, not from here. Provisioning a
new host stays **PROPOSE_ONLY** (keys/private never cross envs). The map is ready;
the hosts light up when they answer.
