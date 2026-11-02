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
| **git host** (`git_host`) | self-hosted smart-HTTP git (clone/push over the mesh) | laptop **WSL/Ubuntu only** (127.0.0.1:8088; own_git :8400) | none | **SPOF** |
| **unison feed** (`unison_feed`) | fleet sync feed (`:8800/unison`) + own_git (`:8400`) | laptop (one host) | none | **SPOF** |
| **PC covenant node** (`pc_node`) | judge/API node (5000/5020/5060; P2P 5001) | laptop Windows | TETSU node (when up); phone node (intermittent) | PAIRED* |
| **model / consult limbs** (`model`) | Tetsu's model + LIMB SMOL/PHI consult limbs | TETSU (laptop 7B retired) | none that answers for TETSU | **SPOF** |
| **teacher / learning channel** (`teacher`) | practice loop + teacher queue feeding students | laptop | none (single feed) | **SPOF** |
| **redundancy beacon** (`beacon`) | the resilience read-API itself (fleet/redundancy state) | **Windows + WSL/Ubuntu pair** (provisioned, DARK until armed) | **yes — cross-OS, same host** | **PAIRED** |

\* PAIRED only while TETSU is awake; TETSU sleep drops `tetsu-hs`, and the phone
is intermittent. So the node layer degrades to single-host whenever TETSU sleeps
— flagged, not assumed.

### The three hard SPOFs

1. **headscale control — laptop WSL only.** If this one Ubuntu (or the laptop,
   or WSL itself) goes down, the mesh loses its coordinator. Existing tunnels
   keep flowing, but no node can (re)join or re-key. `detect_headscale_down`
   already restarts it *on the same host*; that does nothing for host/OS loss.
   **The redundant instance must live on TETSU (a different host).** PROPOSE-only
   (install + config). See `ops/PARALLEL_OS_PROPOSE_2026-11-02.md` #1.
2. **git host — laptop WSL only.** Same shape: a Windows-side or TETSU-side
   read-only standby removes the single-OS dependency. PROPOSE #2 / #3.
3. **unison feed + own_git — one host.** The sync fabric's source. A second
   feed on TETSU makes the fabric survive the laptop. PROPOSE #4.

## What is live now vs. proposed

- **Live (no install):** the **redundancy beacon** — a genuine cross-OS
  redundant pair (Windows Python primary + WSL/Ubuntu Python standby, same
  stdlib code), plus the failover detectors and the AUTO_REVERSIBLE
  start-standby remedy. Proven both ways (FO1 + the live cross-OS takeover
  record below). Ships **DARK** (not auto-started) to respect the 2.98 GB RAM
  budget; the operator arms it with `ops/REDUNDANCY_ARMED`.
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
