#!/usr/bin/env python3
"""test_m2_merkle_seal.py -- M2: followable branches, sealed base.

WHAT M2 IS. covenant_seal.py's flat root proves the SET: to let anyone check
one file you must hand them every filename and hash in it. The merkle layer
proves ONE file with ~log2(n) sibling hashes and discloses nothing about the
rest -- the branch is followable, the base stays shut.

WHAT THIS SUITE PINS, and every one of these is a property somebody could
quietly remove:

  T*  the tree: domain separation (a leaf digest can never equal an internal
      one), odd nodes CARRIED not duplicated, order is part of the
      commitment
  P*  proofs: a real one verifies, and every way of faking one FAILS --
      wrong leaf, wrong sibling, wrong root, truncated path
  D*  disclosure: a proof contains the proven file and nothing about any
      other file in the set
  S*  self-reference: the seal must not hash its own output. Caught live
      2026-08-29 -- writing SEAL_MERKLE.txt changed the set, so a proof was
      invalid the moment it was produced.

Pure hashing. No archive is written, no file is encrypted, nothing is sealed.
"""
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_seal as cs   # noqa: E402

results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print(f"{'ok  ' if ok else 'FAIL'}  {label}"
          f"{'' if ok else '  ' + str(detail)[:150]}", flush=True)


def rows(n):
    return sorted((f"file{i:03d}.py", 100 + i, hashlib.sha256(
        f"content{i}".encode()).hexdigest()) for i in range(n))


def main():
    print("M2 -- merkle seal: prove one file, disclose nothing else\n")

    # ---- T: the tree ------------------------------------------------------
    r8 = rows(8)
    lv = cs.merkle_levels(r8)
    check("T1 a power-of-two set halves cleanly to one root",
          [len(x) for x in lv] == [8, 4, 2, 1], [len(x) for x in lv])

    leaf = cs._leaf(*r8[0])
    internal = cs._pair(leaf, leaf)
    check("T2 DOMAIN SEPARATION: a leaf and an internal node over the same "
          "bytes hash differently, so an internal node can never be passed "
          "off as a leaf (the classic second-preimage attack)",
          leaf != internal
          and cs._leaf("a", 1, "b") != cs._pair(cs._leaf("a", 1, "b"),
                                                cs._leaf("a", 1, "b")), "")

    r5 = rows(5)
    lv5 = cs.merkle_levels(r5)
    check("T3 an odd node is CARRIED UP, not duplicated -- duplicating the "
          "last leaf is what cost Bitcoin CVE-2012-2459",
          [len(x) for x in lv5] == [5, 3, 2, 1], [len(x) for x in lv5])
    check("T4 ...and the carried node keeps its own hash, unchanged",
          lv5[1][-1] == lv5[0][-1], "")

    a, b = cs.merkle_root(r8), cs.merkle_root(list(reversed(r8)))
    check("T5 ORDER IS PART OF THE COMMITMENT: the same files in another "
          "order are a different root", a != b, "")
    check("T6 an empty set still yields a root rather than crashing",
          len(cs.merkle_root([])) == 64, "")
    check("T7 one file is its own root", len(cs.merkle_root(rows(1))) == 64, "")

    # ---- P: proofs --------------------------------------------------------
    r = rows(11)                       # odd, so carries are exercised
    root = cs.merkle_root(r)
    for i in (0, 5, 10):
        pr = cs.merkle_proof(r, i)
        ok = cs.verify_merkle(cs._leaf(*r[i]), pr, root)
        check(f"P1 a real proof verifies (leaf {i} of 11, {len(pr)} siblings)",
              ok, (i, len(pr)))

    pr = cs.merkle_proof(r, 3)
    check("P2 a WRONG LEAF is rejected -- claiming a file that is not in the "
          "set cannot be proven into it",
          not cs.verify_merkle(cs._leaf("evil.py", 1, "00" * 32), pr, root), "")
    check("P3 a TAMPERED SIBLING is rejected",
          not cs.verify_merkle(cs._leaf(*r[3]),
                               [("left", "11" * 32)] + pr[1:], root), "")
    check("P4 a proof is rejected against a DIFFERENT root",
          not cs.verify_merkle(cs._leaf(*r[3]), pr, cs.merkle_root(rows(12))),
          "")
    check("P5 a TRUNCATED path is rejected -- stopping early must not "
          "accidentally land on the root",
          not cs.verify_merkle(cs._leaf(*r[3]), pr[:-1], root), "")
    check("P6 the proof is logarithmic, not linear: 11 files need <= 4 "
          "siblings, not 10",
          len(pr) <= 4, len(pr))

    # ---- D: disclosure ----------------------------------------------------
    big = rows(64)
    idx = 7
    pr = cs.merkle_proof(big, idx)
    sibs = {h for _s, h in pr}
    leaves = {cs._leaf(*row) for j, row in enumerate(big) if j != idx}
    check("D1 a proof reveals at most ONE other leaf hash (the immediate "
          "sibling); the other 62 files are never in it",
          len(sibs & leaves) <= 1, len(sibs & leaves))
    check("D2 no filename other than the proven one appears anywhere in the "
          "proof",
          not any(row[0] in str(pr) for j, row in enumerate(big) if j != idx),
          "")

    # ---- S: the seal must not hash its own output -------------------------
    check("S1 every file this script WRITES is excluded from the walk -- "
          "otherwise producing a proof changes the set the proof is about",
          {"MANIFEST.sha256", "SEAL_ROOT.txt", "SEAL_PUBLIC.txt",
           "SEAL_MERKLE.txt"} <= cs.EXCLUDE_NAMES, sorted(cs.EXCLUDE_NAMES))
    check("S2 proof files are excluded by prefix, since there can be any "
          "number of them",
          "PROOF_" in cs.EXCLUDE_PREFIX, cs.EXCLUDE_PREFIX)
    walked = {os.path.basename(rel) for rel, _f in cs.walk()}
    check("S3 measured on the real folder: no seal output is inside the "
          "sealed set",
          not any(n.startswith("PROOF_") or n.startswith("SEAL_")
                  or n == "MANIFEST.sha256" for n in walked),
          sorted(n for n in walked
                 if n.startswith(("PROOF_", "SEAL_")))[:4])
    check("S4 the merkle root is STABLE across two builds -- the property "
          "S1-S3 exist to protect",
          cs.merkle_root(cs.build_manifest())
          == cs.merkle_root(cs.build_manifest()), "")

    p = sum(results)
    print(f"\nM2: {p}/{len(results)} passed")
    return 0 if p == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
