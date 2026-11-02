# Parallel-OS redundancy — PROPOSE_LIST (2026-11-02)

Everything here **requires an install, another host, a new distro/VM/container,
or a system change. None of it is run by the highway engine** — provisioning a
new environment is `PROPOSE_ONLY`, permanently (`covenant_failover`,
`remedy_propose_provision_redundancy`). These are exact steps for the **operator**
to run and approve. Each says where it should live (TETSU-heavy: 32 GB, headroom;
the laptop is at ~3 GB free with a ram_guard holding the model's room, so heavy
redundant instances must NOT run there), what resilience it buys, and how to undo
it.

**Coordinate the TETSU-side items with the TETSU session before running them** —
TETSU owns its own host. Keys, `private/`, holdings, `*.key` never cross
environments; every item below moves only non-secret service config/state.

Priority order matches the three hard SPOFs in
`ops/PARALLEL_OS_REDUNDANCY_MAP_2026-11-02.md`.

---

## 1. headscale standby on TETSU (SPOF #1 — the mesh coordinator)

**Why:** headscale runs only in the laptop's one WSL/Ubuntu. Lose that distro,
that laptop, or that OS and no node can (re)join or re-key. A warm standby on a
**different host (TETSU)** removes the single-OS dependency.

**Where:** TETSU (its own Linux, or TETSU's WSL). Warm standby, manual cutover —
headscale is not trivially active-active, so this is a standby + periodic state
copy, not HA magic.

**Steps (on TETSU, operator):**
```bash
# 1. install headscale (pin the SAME version the laptop runs)
#    check the laptop's version first:  wsl -d Ubuntu -- headscale version
curl -fsSL https://github.com/juanfont/headscale/releases/download/v<VERSION>/headscale_<VERSION>_linux_amd64 -o headscale
chmod +x headscale && sudo mv headscale /usr/local/bin/headscale
# 2. copy the laptop's config (NON-secret parts only) to TETSU, adjust server_url/listen_addr
#    /etc/headscale/config.yaml  -- do NOT copy private keys; TETSU generates its own
# 3. periodic DB copy from the primary (the standby is only as fresh as its last copy):
#    rsync the sqlite db (or switch both to the same Postgres) on a schedule
# 4. start as a standby (serving, but not the advertised control URL until cutover)
sudo systemctl enable --now headscale
```
**Cutover (when the laptop's headscale is down):** point the tailnet's
`server_url` / DNS at TETSU's headscale and restart nodes. Document the one DNS
record to flip.

**Resilience bought:** the mesh keeps a coordinator when the laptop/WSL dies.
**Cost:** an always-on headscale on TETSU (~tens of MB) + a copy schedule.
**Undo:** `systemctl disable --now headscale` on TETSU; remove the binary/config.

---

## 2. git-host standby — Windows-side, cross-OS (SPOF #2), no second host

**Why:** `git_http_server.py` runs only in the laptop's WSL/Ubuntu. A **Windows**
standby of the SAME server makes the git host survive the loss of the Linux
userland while staying on one host (cheapest resilience for this SPOF). Git for
Windows + the existing Python is all it needs.

**Steps (laptop, operator):**
```powershell
# 1. Git for Windows (if not present):  winget install --id Git.Git -e
# 2. a mirror clone of the served repo on the Windows side (read-only standby):
git clone --mirror \\wsl$\Ubuntu\home\lawre\githost\covenant.git C:\Users\Lawre\covenant-gitmirror\covenant.git
# 3. run the same server on a DISTINCT port against the mirror (e.g. 8089):
python git_http_server.py --root C:\Users\Lawre\covenant-gitmirror --port 8089
# 4. a scheduled `git --git-dir=... remote update` keeps the mirror fresh
```
Then add the Windows instance to `covenant_failover.SERVICES["git_host"]`
(env `windows`, port 8089, `provisioned: True`, `launch` wired) — that promotes
git_host from SPOF to a cross-OS PAIR and `start_redundant_instance` can tend it.

**Resilience bought:** clone/read survives WSL/Ubuntu loss.
**Cost:** a mirror clone on disk + a refresh schedule; read-only (pushes still go
to the primary). **Undo:** stop the Windows server; delete the mirror.

---

## 3. unison feed standby on TETSU (SPOF #3 — the sync fabric source)

**Why:** the `:8800/unison` feed + `:8400` own_git are one host. A second feed on
TETSU lets the sync fabric survive the laptop.

**Steps (TETSU, operator):** run the feed/own_git server (coordinate the exact
launcher with the grow-highway-sync-fabric / auto-onboard branches, which own
the feed) against a mirror of the same repos, on TETSU, distinct ports. Add it to
`SERVICES["unison_feed"]` as the `tetsu` redundant instance once live.

**Resilience bought:** the fabric has a second source of truth on another host.
**Cost:** always-on feed + mirror on TETSU. **Undo:** stop it; drop the entry.

---

## 4. rootless container runtime (podman) — isolated redundant services

**Why:** today there is **no container runtime**. Rootless podman lets redundant
instances run isolated without a full VM — lighter than a VM, no daemon, no root.
Good home for standbys of items 1–3.

**Where:** **TETSU** (Linux, headroom), or the laptop WSL if an item is light
enough (measure `covenant_model.free_gb()` first; skip the laptop if < ~4 GB).

**Steps (TETSU/Ubuntu, operator):**
```bash
sudo apt-get update && sudo apt-get install -y podman   # rootless by default for a normal user
podman info | grep -i rootless                           # confirm rootless
# then run a redundant service, e.g. the beacon, in a container on TETSU:
podman run -d --name beacon-tetsu -p 8773:8773 -v <repo>:/app:ro \
  python:3 python /app/covenant_beacon.py --port 8773 --instance beacon-tetsu --env tetsu --host 0.0.0.0
```
**Resilience bought:** a THIRD environment (containerized, another host) for the
beacon and other light services → survives the loss of BOTH laptop OSes.
**Cost:** the podman install + per-container RAM. **Undo:** `podman rm -f` the
container; `apt-get remove podman`.

---

## 5. a second WSL distro on the laptop (Debian) — a second Linux userland

**Why:** the laptop has ONE distro (Ubuntu). A second distro means a distro-level
corruption/upgrade break is not total — a bare-minimum Linux fallback for
headscale/git-host on the same machine.

**Steps (laptop, operator — needs download + a reboot is NOT required):**
```powershell
wsl --list --online              # see available distros
wsl --install -d Debian          # downloads and registers Debian; set up a user
wsl -d Debian -- python3 --version   # confirm a runtime is present (apt-get install python3 if not)
```
**Resilience bought:** a second Linux userland on the same host for the WSL-only
services. **Cost:** disk + RAM when running (keep it STOPPED unless failing over;
`wsl --terminate Debian`). **RAM caution:** do not run Ubuntu + Debian + the model
concurrently on the laptop. **Undo:** `wsl --unregister Debian`.

---

## 6. a full Linux VM on TETSU — true parallel OS (heaviest)

**Why:** the strongest form of "our own operating systems running parallel" — a
full, independent Linux OS, kernel and all, not a shared-kernel WSL userland. The
place to run a genuinely independent copy of the critical stack.

**Where:** **TETSU only** (32 GB). Never the laptop.

**Steps (TETSU, operator — needs admin + likely a reboot to enable virtualization):**
```powershell
# Windows host (TETSU): enable Hyper-V (admin PowerShell; reboot after)
Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All
# then create a VM from an Ubuntu Server ISO via Hyper-V Manager (or `New-VM`),
# give it 4-8 GB RAM, install headscale/git-host/beacon inside it.
```
(If TETSU runs Linux: use KVM/libvirt — `virt-install` with an Ubuntu cloud image.)

**Resilience bought:** a fully independent OS carrying the critical services —
survives host-OS-level failure of everything else. **Cost:** several GB RAM +
disk, always-on; admin + a reboot to enable virtualization. **Undo:** stop and
delete the VM; disable the Hyper-V feature.

---

## What is already live (no install, for contrast)

The **redundancy beacon** cross-OS pair (Windows + WSL/Ubuntu), its failover
detectors, and the AUTO_REVERSIBLE `start_redundant_instance` remedy are **live
and proven both ways** with the existing runtimes — no item on this list was
needed for them. They ship DARK (`ops/REDUNDANCY_ARMED`) to respect the RAM
budget. See the map doc's measured proof.
