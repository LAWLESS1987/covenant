# Propagation fix (finding AV) — the exact change, for review

One behavioural change in `covenant_unified_v8.py`, plus one call-site update.
This is the diff a human should read before trusting real-time propagation.

## What changed and why

A block applied via the **pull** paths (startup bootstrap and gap-fill, both
routed through `_apply_fetched_blocks`) was never re-announced to this node's
other peers. The **push** paths (`_fetch_announced` and the `BLOCK_PROPAGATE`
accept branch) already re-announce. Because the pull paths race the push and
sometimes win, a block could arrive at a node and stop there — breaking the relay
to anything past it on a sparse topology. Traced live on a 3-process line A–B–C.

## Hunk 1 — `_apply_fetched_blocks` re-announces onward

```diff
-    def _apply_fetched_blocks(self, raws: List[dict]) -> int:
+    def _apply_fetched_blocks(self, raws: List[dict], source_peer_id: Optional[str] = None) -> int:
         """Decode and accept a run of blocks fetched from a peer. Returns the
         number applied. Shared by gap-fill and startup bootstrap ..."""
         applied = 0
         for raw in raws[:MAX_CATCHUP_BLOCKS]:
             try:
                 ... decode b ...
             except Exception as e:
                 self.node.anomaly_monitor.record("bootstrap_decode_failed", ...)
                 break
             if not self._accept_block_common(b):
                 break
             applied += 1
+            # Relay onward so a block pulled here is not a propagation dead end.
+            self.node.announce_block(b, exclude_peer=source_peer_id)
         return applied
```

## Hunk 2 — pass the pull source through so it is excluded from the re-announce

```diff
     for pid, (host, port) in peers:
         ...
         if raws:
-            gained += self._apply_fetched_blocks(raws)
+            gained += self._apply_fetched_blocks(raws, source_peer_id=pid)
```

## Why it is loop-safe (the same argument the other accept paths rely on)

- `_accept_block_common` admits a given height **at most once** (it rejects any
  block whose `index != len(chain)`), so a node re-announces each height at most
  once.
- The re-announce is an **address event** `(index, hash)`, not a full block. A
  peer that already holds that index replies "known" and does **nothing** — no
  fetch, no forward (lateral inhibition, `BLOCK_ANNOUNCE` handler). Redundant
  announcements die where they land.
- The peer the blocks were pulled from is excluded (`exclude_peer=source_peer_id`)
  — it provably already has them.

Net: message count stays bounded by the edge set; there is no echo storm.

## Verification

- `test_multinode_live.py`: 19/21 → **21/21, four consecutive runs**; the
  previously-failing "block RELAYED to C" and three-way tip agreement hold every
  run, with C reaching the new height in ~2s by push.
- Full adversarial regression re-run after the change — security 127,
  adversarial 21, e2e 11, xrp 22+69, quant 16, probe 0-findings,
  order-independence held — **no regression**.
