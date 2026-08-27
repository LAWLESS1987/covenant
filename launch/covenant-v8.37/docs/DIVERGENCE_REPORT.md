# Divergence report — project vs. machine, 2026-08-26

Neither location had everything, and that is the finding.

- **150** files lived in the claude.ai project.
- **255** files lived in `C:\Users\Lawre\covenant`.
- **95** were byte-identical in both.
- **42** existed **only in the project** — including the loop's entire memory:
  `IMPROVEMENT_LOG.md`, `RUN_LOG_ARCHIVE.md`, `LOOP_HEADER_ARCHIVE.md`, every
  design doc, and the whole `semantic/` pipeline. None of it was on the
  machine. If the project had gone away, the record would have gone with it.
- **118** existed **only on the machine** — including `genesis.json`, the seal,
  the judge configs, every `start_*.bat`, `quant/`, the original `realdata/`
  series, and all eight `covenant_unified_v8.PRE-*.py` rollback copies. None
  of that was in the project.
- **13** existed in both with different bytes. Those are below.

The union is **280 files**, and this bundle is the first artefact that holds
all of them.

---

## The 13 that disagreed

Nothing was discarded. Where one copy won, the other is preserved verbatim in
`docs/variants/` under a `.PC-COPY` or `.PROJECT-COPY` suffix.

| file | canonical | project sha12 | PC sha12 | why |
|---|---|---|---|---|
| `CHANGES_TO_SAVE.md` | BOTH KEPT | `f05a7774bcc9` | `90b40f6bf640` | each has unique content; PC carries findings AV/AW, project carries the escrow note |\n| `DEPLOYMENT.md` | project copy | `800798b523cb` | `936171ba5435` | project copy is +44/-10 lines and carries the current config table |\n| `HANDOFF.md` | PC copy | `34a4b21ff217` | `f02daff00549` | PC copy carries the assembly-pass note and finding AV; project copy only trims the Docs list |\n| `QUANT_README.md` | project copy | `566efa043a0f` | `706628e9dd0c` | project copy is +36/-11 lines |\n| `SECURITY_AUDIT_v8.12.md` | project copy | `c36e488a0c17` | `7176b41bc702` | project copy is 397 lines against 162 - the full audit |\n| `test_a20_peer_version.py` | project copy | `409597394436` | `d219eac4e013` | project copy carries the P13 not_run() fix (2026-08-24); PC copy predates it |\n| `sim1000_network.py` | project copy | `742ce3552908` | `1e3f4c297daa` | project copy adds 2 explanatory lines, no behaviour change |\n| `sim_order_independence.py` | PC copy | `e2c3cad890d4` | `dccc6ec3acf2` | PC copy carries the Windows rmtree(ignore_errors=True) teardown fix |\n| `sim_yield_safety.py` | PC copy | `0ded8f781b5d` | `66c7baf603c9` | PC copy carries the Windows rmtree teardown fix |\n| `test_adversarial_suite.py` | PC copy | `c8bde36fe4fe` | `4415e2ccdbc0` | PC copy carries the Windows rmtree teardown fix |\n| `test_e2e_gift.py` | PC copy | `db0f10586ebf` | `31d9a48eb1b0` | PC copy carries the Windows rmtree teardown fix |\n| `test_multinode_live.py` | PC copy | `3891577c7e0e` | `1aea9e914f02` | PC copy == project pc/test_multinode_live.py (pulled back 08-23); project root copy is the pre-v8.19 original |\n| `MANIFEST.json` | regenerated | `9797225f120c` | `fadcae896b92` | both stale (v8.18-final-audit); regenerated as MANIFEST.sha256 over the whole bundle |

## The one that mattered

Four suites — `sim_order_independence.py`, `sim_yield_safety.py`,
`test_adversarial_suite.py`, `test_e2e_gift.py` — differ by exactly one line,
and it is the same line in each:

```python
-shutil.rmtree(work)
+shutil.rmtree(work, ignore_errors=True)   # Windows will not unlink an open
+                                          # sqlite file; this is teardown
+                                          # AFTER every check
```

The project copies are the originals. The PC copies carry the Windows teardown
fix from 2026-08-22 — the one the log describes as *"three of them ran every
check and passed, and only their `shutil.rmtree` teardown crashed; I read a
missing summary line as a missing run."*

**Taking the project copy because it came from the project would have silently
reintroduced that crash into the win32 sweep**, on four suites, and it would
have looked exactly like a regression in the code under test. The PC copies
win, and they win on a measurement rather than on provenance.

The mirror case is `test_a20_peer_version.py`, where provenance points the
other way: the project copy carries P13's `not_run()` fix from 08-24 and the
PC copy predates it. Two files, opposite answers, same rule — read the diff,
not the folder it came from.

## And `test_multinode_live.py`

The project held **two** copies: `test_multinode_live.py` (the pre-v8.19
original) and `pc/test_multinode_live.py`, which is byte-identical to what is
on the machine — it was pulled back over the bridge on 08-23. The root copy is
the stale one. Resolved to the machine's.
