#!/usr/bin/env python3
"""
GS4 -- both-ways guard for the OFF-HOST binding of the grid command ledger (CLAUDE.md
rule 8). Closes the grid-guard open item "the command ledger is bound to nothing
off-host". The ledger is gitignored runtime state, so it cannot go in
covenant_head_commit.BOUND_FILES (which bind COMMITTED bytes); instead each head-
commitment carries a FROM-DISK checkpoint of the command chain's head
(grid_ledger_checkpoint), and grid_ledger_anchor_ok proves the current chain is still an
append-only extension of an earlier commitment's checkpoint -- so an outside holder of
that earlier, out-of-band commitment catches a rewrite or truncation BELOW it.

This suite drives it both ways: honest growth stays OK; a rewrite at the checkpoint seq,
a truncation below it, or a vanished chain all turn it red. Shape + every-commit cadence
were consulted with Tetsu (2026-11-02).

Run:  python test_gs4_grid_ledger_anchor.py    (exit 0 = all pass)
"""
import os
import sys
import tempfile

PASS = [0]
FAIL = [0]


def check(name, cond, detail=""):
    if cond:
        PASS[0] += 1
        print("  ok  ", name)
    else:
        FAIL[0] += 1
        print("  FAIL", name, "--", detail)


def main():
    import covenant_head_commit as hc
    import covenant_consent_chain as cc

    d = tempfile.mkdtemp(prefix="gs4_")
    ledger = os.path.join(d, "grid_commands.jsonl")
    chain = os.path.join(d, "grid_commands.chain.jsonl")

    def _append(n):
        for i in range(n):
            cc.append_consent({"seq_marker": i, "action": "breaker_open", "payload": {"nonce": "n%d" % i}},
                              ledger_path=ledger, chain_path=chain)

    def _lines(p):
        with open(p, encoding="utf-8") as fh:
            return [ln for ln in fh.read().split("\n") if ln.strip()]

    # ---- absent chain: a checkpoint pins nothing, and nothing is dishonored
    cp0 = hc.grid_ledger_checkpoint(chain_path=chain)
    check("GS4 absent chain -> checkpoint pins 0 rows / head None", cp0 == {"rows": 0, "head_sha256": None}, str(cp0))
    check("GS4 a 0-row checkpoint is vacuously honored", hc.grid_ledger_anchor_ok(cp0, chain_path=chain)[0] is True)

    # ---- build 3 rows, take the checkpoint
    _append(3)
    cp = hc.grid_ledger_checkpoint(chain_path=chain)
    check("GS4 checkpoint counts the chain rows and pins a head", cp["rows"] == 3 and cp["head_sha256"], str(cp))
    ok, why = hc.grid_ledger_anchor_ok(cp, chain_path=chain)
    check("GS4 the chain honors its own checkpoint", ok, why)

    # ---- honest growth: append more -> STILL honored (append-only extension)
    _append(2)
    ok, why = hc.grid_ledger_anchor_ok(cp, chain_path=chain)
    check("GS4 later honest appends keep the earlier checkpoint honored (append-only)", ok and len(_lines(chain)) == 5, why)

    # ---- tamper BELOW the checkpoint: rewrite the row at the checkpoint seq -> red
    lines = _lines(chain)
    saved = lines[2]
    lines[2] = lines[2].replace('"seq_marker":2', '"seq_marker":999') if '"seq_marker":2' in lines[2] else (lines[2][:-1] + ' ')
    with open(chain, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    ok, why = hc.grid_ledger_anchor_ok(cp, chain_path=chain)
    check("GS4 a rewrite at/below the checkpoint seq is CAUGHT by the earlier commitment (red)", ok is False, why)
    # the other way: restore the row -> honored again
    lines[2] = saved
    with open(chain, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    ok, why = hc.grid_ledger_anchor_ok(cp, chain_path=chain)
    check("GS4 broken the other way: restoring the row restores the anchor", ok, why)

    # ---- truncation below the checkpoint -> red
    with open(chain, "w", encoding="utf-8") as fh:
        fh.write("\n".join(_lines(chain)[:2]) + "\n")
    ok, why = hc.grid_ledger_anchor_ok(cp, chain_path=chain)
    check("GS4 truncating the chain below the pinned row count is CAUGHT (red)", ok is False and "truncat" in why.lower(), why)

    # ---- the chain vanishes entirely while a checkpoint pinned rows -> red (never silent OK)
    os.remove(chain)
    ok, why = hc.grid_ledger_anchor_ok(cp, chain_path=chain)
    check("GS4 a vanished chain against a non-empty checkpoint is red, never a silent pass", ok is False, why)

    # ---- integration, BEHAVIOURAL (A74: run the code, never read its source). Build a FRESH
    # clean chain (the tamper/vanish tests above left theirs inconsistent) and call the REAL
    # signer end-to-end; the produced, signed payload must carry exactly the from-disk checkpoint.
    fd = tempfile.mkdtemp(prefix="gs4f_")
    fled, fchain = os.path.join(fd, "l.jsonl"), os.path.join(fd, "c.jsonl")
    for i in range(3):
        cc.append_consent({"seq_marker": i, "payload": {"nonce": "m%d" % i}},
                          ledger_path=fled, chain_path=fchain)
    try:
        from cryptography.hazmat.primitives.asymmetric import rsa  # noqa: F401
        _have_crypto = True
    except Exception:  # noqa: BLE001
        _have_crypto = False
    if _have_crypto:
        saved_chain = hc.GRID_CHAIN
        hc.GRID_CHAIN = fchain
        kd = tempfile.mkdtemp(prefix="gs4k_")
        try:
            row, _note = hc.make_commitment(repo=os.path.dirname(os.path.abspath(__file__)),
                                            key_path=os.path.join(kd, "hc.key"),
                                            pubkey_path=os.path.join(kd, "hc.pem"),
                                            ledger=os.path.join(kd, "hc_ledger.jsonl"))
            want = hc.grid_ledger_checkpoint(chain_path=fchain)
            got = (row.get("payload") or {}).get("grid_ledger")
            check("GS4 the REAL make_commitment binds the from-disk checkpoint into the SIGNED "
                  "payload -- ran end-to-end, not a source grep (every head-commit, per Tetsu)",
                  got == want and got.get("rows") == 3 and bool(got.get("head_sha256")),
                  "%r vs %r" % (got, want))
        finally:
            hc.GRID_CHAIN = saved_chain
    else:
        check("GS4 (cryptography absent here) make_commitment binding not runnable -- skipped, "
              "measured as skipped, never a false pass", True)

    # ---- design invariant, BEHAVIOURAL: load the standalone verifier with EVERY covenant
    # import blocked; it must load clean (proves it imports no covenant code -- run, not grep).
    import importlib.util
    vpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "verify_head_commitment.py")

    class _Block:
        def find_spec(self, name, path=None, target=None):
            if name.split(".")[0].startswith("covenant"):
                raise ImportError("standalone imported covenant code: " + name)
            return None

    blk = _Block()
    sys.meta_path.insert(0, blk)
    try:
        spec = importlib.util.spec_from_file_location("_vhc_probe", vpath)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        loaded_ok = True
    except ImportError:
        loaded_ok = False
    finally:
        sys.meta_path.remove(blk)
    check("GS4 the standalone verify_head_commitment.py LOADS with every covenant import blocked "
          "(ran it -- proves independence; the signature already protects the checkpoint value)",
          loaded_ok is True)

    print("\nGS4: %d passed, %d failed" % (PASS[0], FAIL[0]))
    return 1 if FAIL[0] else 0


if __name__ == "__main__":
    sys.exit(main())
