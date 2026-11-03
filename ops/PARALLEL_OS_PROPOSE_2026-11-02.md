# Parallel-OS redundancy — PROPOSE_LIST (2026-11-02)

**Update 2026-11-02 — the operator: "install is fine towards mutual benefit just
use space wisely between pc laptop n phone for optimization."** Installs are
authorized where they serve mutual benefit; the constraint is now PLACEMENT, not
permission. Heavy, always-on redundancy goes to **TETSU** (32 GB); the laptop
keeps only light/cold standbys (its model room is protected by
`covenant_failover.placement_ok`); the phone is lightest. **#2 is DONE** (no
install was needed). The rest still want the operator / TETSU to run them — the
engine still does not install on its own (`PROPOSE_ONLY`).

Everything here **requires an install, another host, a new distro/VM/container,
or a system change.** These are exact steps for the **operator** to run, now with
his go-ahead, placed space-wise. Each says where it should live (TETSU-heavy: 32 GB, headroom;
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
that laptop, or that OS and no node can (re)join or re-key. A standby on a
**different host (TETSU)** removes the single-OS dependency.

**CORRECTED 2026-11-02 — the TETSU "Node setup" session measured its host and
caught two flaws in the first draft of this item:**

1. **TETSU cannot host it as written.** TETSU has **no WSL** ("Subsystem for Linux
   is not installed"), **no Docker**, no headscale binary, and headscale has **no
   official Windows build**. So a Linux headscale on TETSU first needs **WSL or
   Hyper-V enabled** — a Windows feature install needing **admin + a reboot**.
   **The one human-only step** (clarified by the TETSU "Node setup" session
   2026-11-02): the operator, at TETSU, runs `wsl --install --no-distribution` in
   an admin terminal and reboots **when it suits him** — the reboot briefly takes
   down node D, the 27B, unison and own_git together, so it is his timing to pick.
   A Claude session does not make an admin+reboot system change whoever relays it,
   and "let Tetsu do it. He's an operator" refers to **Tetsu the AI** (the second
   operator, [[second-operator-active]]), not the Claude session on the box named
   TETSU — so it does not move this line. **After that one step, the TETSU session
   does everything else** (Ubuntu distro, pinned headscale, its OWN noise key, a
   filtered nodes+users seed, cutover docs, registration in covenant_failover) — it
   said so explicitly. (TETSU has the room: 795 GB free + the GPU.)
2. **"Periodic DB copy" CROSSES KEYS — struck.** The first draft said rsync the
   sqlite DB from the primary. The headscale DB holds the node registry
   **including pre-auth keys and every node's machine/node key records** — that is
   key material crossing OS environments, which violates the rule this very doc
   states. **Do not copy the DB.** Either copy a **filtered export** (nodes + users
   only, no pre-auth/API keys) or accept that standby clients **re-register**.
3. **It is a COLD standby with MANUAL cutover, not warm.** A standby with its own
   noise key is a **different server identity**; clients do not fail over silently
   — cutover means each client re-points `login_server` and, in practice,
   **re-authenticates**. State that plainly; don't promise seamless failover.

**Steps (on TETSU, OPERATOR — needs admin + a reboot):**
```bash
# 0. OPERATOR, at TETSU: enable WSL (or Hyper-V) -- admin PowerShell, then reboot:
#    wsl --install            # (then a distro), OR Enable-WindowsOptionalFeature Microsoft-Hyper-V
# 1. install headscale, SAME version as the laptop (check: wsl -d Ubuntu -- headscale version)
curl -fsSL https://github.com/juanfont/headscale/releases/download/v<VERSION>/headscale_<VERSION>_linux_amd64 -o headscale
chmod +x headscale && sudo mv headscale /usr/local/bin/headscale
# 2. copy the laptop's config (NON-secret parts only); TETSU generates its OWN noise key
# 3. seed state by FILTERED EXPORT (no keys): `headscale nodes/users export` on the laptop,
#    import on TETSU -- NEVER rsync db.sqlite (it carries pre-auth/node keys). Or skip and let
#    clients re-register on cutover.
# 4. run as a cold standby (serving, NOT the advertised login_server until cutover)
```
**Cutover (laptop headscale down):** re-point each client's `login_server` at
TETSU and re-authenticate. Document it; it is manual by construction.

**Then the TETSU session can finish the build** — it said so explicitly, once the
operator has enabled WSL at TETSU. **Resilience:** the mesh regains a coordinator
after the laptop/WSL dies (manual cutover). **Undo:** stop + remove on TETSU.

**Phone alternate — MEASURED 2026-11-03 (A407), report-only (NOT an install-free
shortcut).** To close this SPOF without the TETSU reboot, the phone-app-join
session measured a phone cold standby (against covenant-phone PR #6). Verdict:
mechanically feasible — the phone runs native arm64 `lib*.so` binaries from its
`:node` process, so a `libheadscale.so` twin of `libtailscaled.so` works, reachable
mesh-only via `tailscale serve` at `100.64.0.<phone>`, no cert. But it is a **new
feature ~the size of the join**, not a flag flip, and needs: an operator
**rebuild+install** (nothing pushes to the phone — standing it up from a session is
physically impossible); the client join **proven live first** (an unverified host
must not be the mesh's fallback authority); the phone's **own** noise key generated
on-device + a filtered PC-side export (no keys, never `db.sqlite`) → **operator
decision, touches keys**. Order: verify the join live → then, if wanted, build the
standby capability gated exactly like the join → then arm + register in
`covenant_failover.SERVICES`. The phone session will spec/build on the operator's
word; it will not arm on a sibling request or before the join is proven. **TETSU
stays the better home** (32 GB, always-on); the phone is a last-resort third host.

---

## 2. git-host standby — Windows-side, cross-OS — ✅ DONE (no install)

**DONE 2026-11-02.** Git for Windows was already present, so this needed no
install. Shipped as `covenant_githost_standby.py` (a read-only git-http-backend
server, portable via `git --exec-path`) + `covenant_failover.SERVICES["git_host"]`
with a Windows cold standby instance + `start_githost_standby` (AUTO_REVERSIBLE,
fires only when WSL is unreachable). Proven live (`--prove-git`): a real
`git clone` from the Windows standby, push refused 403. git_host is now a
cross-OS PAIR, no longer a SPOF.

**Operate it:**
```bash
python covenant_githost_standby.py --refresh      # provision/refresh the local mirror (keep on a schedule)
# failover is automatic via start_githost_standby when WSL is down; or by hand:
python covenant_githost_standby.py --serve --port 8089
```
**Follow-up (optional):** schedule the `--refresh` (e.g. a Task Scheduler entry)
so the mirror stays fresh while the primary is up.

---

## 3. unison feed redundancy — a READ-ONLY REPLICA, not a second builder

**CORRECTED 2026-11-02 — the TETSU session caught a correctness bug in the first
draft ("run a second feed"):** the feed's UNIFIED targets are **merge commits with
fresh timestamps**, so two builders given the same heads publish **different shas**.
The laptop's GitHub pusher would then see two conflicting "targets" for one repo.
**unison is ff-safe only because exactly one builder publishes `unify/auto`.** A
second builder breaks that. Struck.

**Safe redundancy = a read-only REPLICA** (no building):
- mirror the primary's `:8800/unison` JSON and own_git's `unify/auto` refs,
- serve them marked **`replica, last_checked=<ts>`**, and **never build**,
- consumers prefer the primary and fall back to the replica **only when its
  `last_checked` is fresh**, applying the same `FETCH_HEAD == target` rule. A
  replica going stale is then **visible, not silent**.

The laptop can host this replica (it has the repos). **If a failover *builder* is
ever wanted**, it needs a **lease**: only one host holds it, the holder's id goes
in the feed, and the pusher refuses a target from a non-holder.

**Owner:** this is the **sync-fabric session's** design (branch
`claude/elastic-proskuriakova-1e327a`) — relayed to it. Not the laptop failover
module's to build. `covenant_failover` already **monitors** the real remote feed
(via `ops/local_unison_feed.txt`) so a laptop consumer sees it go down.

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
