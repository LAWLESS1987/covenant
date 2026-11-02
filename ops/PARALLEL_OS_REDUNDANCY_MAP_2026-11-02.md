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
| **unison feed** (`unison_feed`) | fleet sync feed (`:8800/unison`) + own_git (`:8400`) | laptop (one host) | none | **SPOF** |
| **PC covenant node** (`pc_node`) | judge/API node (5000/5020/5060; P2P 5001) | laptop Windows | TETSU node (when up); phone node (intermittent) | PAIRED* |
| **model / consult limbs** (`model`) | Tetsu's model + LIMB SMOL/PHI consult limbs | TETSU (laptop 7B retired) | none that answers for TETSU | **SPOF** |
| **teacher / learning channel** (`teacher`) | practice loop + teacher queue feeding students | laptop | none (single feed) | **SPOF** |
| **redundancy beacon** (`beacon`) | the resilience read-API itself (fleet/redundancy state) | **Windows + WSL/Ubuntu pair** (provisioned, DARK until armed) | **yes — cross-OS, same host** | **PAIRED** |

\* PAIRED only while TETSU is awake; TETSU sleep drops `tetsu-hs`, and the phone
is intermittent. So the node layer degrades to single-host whenever TETSU sleeps
— flagged, not assumed.

### The remaining hard SPOFs (git host now resolved)

1. **headscale control — laptop WSL only.** If this one Ubuntu (or the laptop,
   or WSL itself) goes down, the mesh loses its coordinator. Existing tunnels
   keep flowing, but no node can (re)join or re-key. `detect_headscale_down`
   already restarts it *on the same host*; that does nothing for host/OS loss.
   **The redundant instance must live on TETSU (a different host).** PROPOSE-only
   (install + config). See `ops/PARALLEL_OS_PROPOSE_2026-11-02.md` #1.
2. **unison feed + own_git — one host.** The sync fabric's source. A second
   feed on TETSU makes the fabric survive the laptop. PROPOSE #4.

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
