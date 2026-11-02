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

    # ---- integration + design invariant
    import inspect
    src = inspect.getsource(hc.make_commitment)
    check("GS4 commit() binds the checkpoint into the signed payload (every head-commit, per Tetsu)",
          "grid_ledger" in src and "grid_ledger_checkpoint" in src)
    vsrc = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "verify_head_commitment.py"), encoding="utf-8").read()
    check("GS4 the standalone verify_head_commitment.py still imports NO covenant code "
          "(the signature already protects the checkpoint value)",
          "import covenant" not in vsrc and "from covenant" not in vsrc)

    print("\nGS4: %d passed, %d failed" % (PASS[0], FAIL[0]))
    return 1 if FAIL[0] else 0


if __name__ == "__main__":
    sys.exit(main())
