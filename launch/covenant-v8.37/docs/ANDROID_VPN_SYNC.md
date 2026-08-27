# Android node over a VPN — what is verified, what to run, what is still untested (2026-08-22)

**Ask from L:** "make sure we have a node we can sync with a VPN for Android
integration."

## 1. What was verified today (in the cloud sandbox, real processes)

The shape an Android node has on a VPN is: the PC node is reachable at a
routable (non-loopback) address — Tailscale's `100.x.y.z` — and the phone
lists the PC as a peer while the PC, on day one, lists nobody (it does not
know the phone's address yet, or there will be many phones).

`claude/test_a17_oneway_peer_sync.py` runs exactly that with two real node
processes on this host's interface IP:

| check | v8.27 (before) | v8.28 (now) |
|---|---|---|
| both nodes answer `/health` on the interface IP (node binds `0.0.0.0`) | pass | pass |
| B lists A by IP; A lists nobody | pass | pass |
| A mines block 2 | pass | pass |
| **B learns block 2 with no second block, no restart, no `/sync`** | **never** (15 s, and it would have been for ever) | **2–3 s** ×3 |

**The defect (A17):** a node at genesis announced nothing ("nothing worth
saying", A1/K5), so a one-way-peered node never probed its peer, and A13's
pull-on-higher-height never fired. The PC's own announces went to its
(empty) peer list. Two healthy nodes, peered on paper, never converging —
and this is the first configuration a phone would be in. **Fix (v8.28):**
`_gossip_tip` announces the tip even at genesis; the peer answers `known`
with its height; A13 pulls. One ~150-byte frame per peer per
`COVENANT_TIP_GOSSIP_INTERVAL` (default 120 s). Full sweep green
(18 suites; `test_multinode_live` 21/21 ×2 alone after one load-induced
timeout in the 8-wide batch — M20).

**So: yes, the PC node can be synced to from a phone over a VPN, by code.**
What follows is the part that needs the phone.

## 2. Runbook — PC side (Windows)

1. Install Tailscale on the PC and the phone; sign both into the same
   tailnet. Note the PC's `100.x.y.z` (`tailscale ip -4`). These addresses
   are stable.
2. Run the node **on Windows Python directly, not inside WSL**: WSL2 sits
   behind its own NAT and the Tailscale interface is on the Windows side;
   a node inside WSL is not reachable at `100.x.y.z` without a port proxy.
   (If you must use WSL, install Tailscale *inside* WSL and use that IP.)
3. From `C:\Users\Lawre\covenant` (with `covenant_path_pattern.py` beside
   the core):
   ```
   set COVENANT_JUDGE_PROVIDERS=...      (your real provider config)
   python covenant_unified_v8.py --port 5000 --node-id pc
   ```
   Ports 5000, 5001, 5011 are used (M2). The P2P port the phone peers to
   is **5001**.
4. Windows Firewall: allow `python.exe` inbound on the **Tailscale**
   interface (it is usually classed as a "Public" network, where inbound is
   blocked by default). Check from the phone before anything else:
   `curl http://100.x.y.z:5000/health`.
5. Export the genesis once and copy it to the phone:
   `python covenant_unified_v8.py --export-genesis genesis.json`
   (only if the PC's chain was self-minted; if the PC itself runs on a
   `--genesis` file, copy that file).

## 3. Runbook — phone side (Termux) — UNTESTED, the phone has not arrived

```
pkg install python git
pip install flask cryptography requests
termux-wake-lock                      # keep the process alive when the screen is off
export COVENANT_JUDGE_PROVIDERS=...   # same as the PC
export COVENANT_TIP_GOSSIP_INTERVAL=600   # 5x fewer radio wake-ups (see probe_power: CPU is ~free, the radio is the cost)
python covenant_unified_v8.py --port 5000 --genesis genesis.json --peers 100.x.y.z:5001 --node-id phone
```
Then on the PC: `curl http://<phone-100.x>:5000/health` and watch
`chain_height` follow the PC's after the next mined block. The phone's
`/health` should show `peer_ahead_seen` climbing on each catch-up.

Things that can only be learned with the phone in hand (C1, C3):
- Termux on Android 12+ kills background processes aggressively; the
  wake-lock helps, a foreground notification (`termux-api`) may be needed.
- Bionic vs glibc: `cryptography` wheels usually install on aarch64 Termux;
  if not, `pkg install rust` and build.
- Doze mode drops idle TCP listeners; the phone may be reachable only while
  awake. A17 makes that fine: the phone *pulls* on its own heartbeat, so it
  only needs to reach the PC, never the reverse.
- Battery: measured CPU cost is ~0.1 %/day; the radio estimate (~3 %/day at
  120 s gossip on cellular) is arithmetic — measure it.

## 4. What this is and is not

A phone syncing to the PC over Tailscale is **backup with automatic
catch-up** (NODE_DEPLOYMENT_FINDINGS), not a second independent witness.
And until A16 (yield on-chain) is decided, anything the phone or PC
*stakes* stays local to that node — see `YIELD_ON_CHAIN_DESIGN.md`.

**Files:** `covenant_unified_v8.py` (v8.28, one method changed),
`claude/test_a17_oneway_peer_sync.py`, `claude/test_a1_kill_matrix.py`
(K5 updated), `run_all_tests.sh` (A17 wired in), this document.

---

## 5. CORRECTION 2026-08-23 — one VpnService at a time, and this plan collides with the phone filter (C5)

Written while building `CovenantGuard` (C5, `claude/ANDROID_GUARD.md`), because
the two plans were made for the same handset and neither said this:

**Android permits exactly ONE app to hold the VPN interface.** There is no API
to chain, stack or share it. Starting a second VPN app tears the first down; the
loser receives `onRevoke()`. `VpnService.prepare()` returning non-null is how an
app learns another one holds it.

Consequences for §2 and §3 of this document:

- **The phone cannot run Tailscale (this runbook's transport) and an on-device
  DNS filter at the same time.** It is one or the other, and the choice has to
  be made deliberately rather than discovered when one of them silently stops.
- If the phone is to be a covenant node over Tailscale, C5's app must stay off
  that handset — or C5 must grow its own tunnel, which is a much larger piece of
  work than the filter itself.
- The reverse is also available and may be the better trade: reach the PC node
  over the LAN (§2's interface-IP shape, which `test_a17_oneway_peer_sync.py`
  already exercises) when the phone is on the same wifi, and keep Tailscale off.
  A17 means the phone PULLS on its own heartbeat, so it only ever needs to reach
  the PC — which a plain LAN address satisfies while the phone is home.

**A second, unrelated trap for anyone testing DNS on that phone:** Android's
**Private DNS** (DNS-over-TLS, Settings → Network → Private DNS) does NOT go
through a VpnService TUN. Neither does an app with hardcoded DoH. So a filter
that looks broken may simply be being bypassed by the platform's own resolver.

**Not changed here:** §3's runbook still describes the Tailscale path, because
which way L wants to go is L's decision, not this loop's.
