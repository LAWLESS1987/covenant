#!/usr/bin/env python3
"""test_t1_triangulate.py -- T1: three witnesses, and the honesty in between.

WHAT T1 PINS. attest() decides whether the PC, GitHub and the cloud agree.
Everything that makes it trustworthy is a REFUSAL rather than a feature, and
each one is a property somebody could quietly remove:

  A*  a witness that did not ANSWER is not a witness that DISAGREED. Collapse
      those and an unreachable cloud reads as agreement, and the check
      reports a clean bill of health for something nobody compared.
  Q*  fewer answers than the quorum is UNPROVEN, and UNPROVEN IS NOT SUCCESS.
      A check that exits 0 when it could not check teaches its reader that
      silence is health.
  D*  divergence NAMES the outlier and changes nothing. The majority is
      evidence about the minority, never a decision to overwrite it.
  S*  the same function at every scale -- one file, one store, one repo --
      because growth must add scales and not mechanisms.
  L*  the limits are carried IN the verdict, so a caller cannot quote the
      result without the caveat.

Pure. No network, no git, no cloud, no repository state.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import triangulate as t   # noqa: E402

results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print(f"{'ok  ' if ok else 'FAIL'}  {label}"
          f"{'' if ok else '  ' + str(detail)[:150]}", flush=True)


A, B = "a" * 64, "b" * 64


def main():
    print("T1 -- triangulation: agreement, divergence, and silence\n")

    # ---- A: silence is not disagreement -----------------------------------
    r = t.attest({"pc": A, "github": A, "cloud": None})
    check("A1 two agreeing witnesses with one SILENT is agreement -- but the "
          "verdict says which witnesses it actually covers",
          r["verdict"] == t.AGREE and r["silent"] == ["cloud"]
          and "cloud" in r["why"], r["why"][:90])
    check("A2 the silent witness is NOT counted as an outlier -- it did not "
          "disagree, it did not speak",
          r["outliers"] == [], r["outliers"])

    r = t.attest({"pc": A, "github": None, "cloud": None})
    check("A3 ONE answer is UNPROVEN, never agreement with itself",
          r["verdict"] == t.UNPROVEN and not r["agreed"], r["verdict"])
    check("A4 ...and it says plainly that nothing was compared",
          "nothing has been compared" in r["why"], r["why"][:90])

    r = t.attest({"pc": None, "github": None, "cloud": None})
    check("A5 total silence is UNPROVEN, not vacuous agreement",
          r["verdict"] == t.UNPROVEN and not r["agreed"], r["verdict"])

    # ---- Q: unproven is not success ---------------------------------------
    check("Q1 UNPROVEN never reports agreed=True -- the one bit a caller "
          "checks must never say yes when nothing was verified",
          not t.attest({"pc": A})["agreed"], "")
    check("Q2 a raised quorum is honoured: three witnesses agreeing still "
          "fails a quorum of four",
          t.attest({"pc": A, "github": A, "cloud": A},
                   quorum=4)["verdict"] == t.UNPROVEN, "")

    # ---- D: divergence names, never decides -------------------------------
    r = t.attest({"pc": A, "github": A, "cloud": B})
    check("D1 one differing witness is DIVERGED", r["verdict"] == t.DIVERGED,
          r["verdict"])
    check("D2 the OUTLIER is named, and the majority is named separately",
          r["outliers"] == ["cloud"] and r["majority"]["held_by"]
          == ["github", "pc"], (r["outliers"], r["majority"]))
    check("D3 the verdict says the majority is EVIDENCE, not a decision -- "
          "nothing here overwrites anybody",
          "not a decision" in r["why"] and "overwrites" in r["why"],
          r["why"][:100])
    check("D4 divergence is never `agreed`", not r["agreed"], "")

    r3 = t.attest({"pc": A, "github": B, "cloud": "c" * 64})
    check("D5 three-way disagreement is still DIVERGED, with two outliers "
          "and no winner declared by luck of ordering",
          r3["verdict"] == t.DIVERGED and len(r3["outliers"]) == 2,
          r3["outliers"])
    check("D6 a two-way tie is resolved DETERMINISTICALLY, so the same "
          "inputs never produce two different reports",
          t.attest({"pc": A, "github": B})["majority"]
          == t.attest({"pc": A, "github": B})["majority"], "")

    # ---- S: one mechanism, every scale -------------------------------------
    micro = t.attest({"disk": A, "backup": A}, scale="one-file")
    macro = t.attest({"pc": A, "github": A}, scale="whole-repo")
    check("S1 the SAME function judges one file and a whole repository -- "
          "growth adds scales, not mechanisms",
          micro["verdict"] == macro["verdict"] == t.AGREE, "")
    check("S2 the scale label is carried through so a report can say what "
          "it was about", micro["scale"] == "one-file", micro["scale"])
    check("S3 witness NAMES are arbitrary: nothing is hard-coded to pc/"
          "github/cloud, so a fourth witness needs no new code",
          t.attest({"phone": A, "friend": A, "notary": A})["verdict"]
          == t.AGREE, "")

    # ---- L: the limits travel with the verdict ----------------------------
    check("L1 every verdict carries its limits, so the result cannot be "
          "quoted without the caveat",
          "NOT byzantine" in t.attest({"pc": A, "github": A})["limits"], "")
    check("L2 ...and the caveat names WHY: one operator holds all three",
          "one operator" in t.attest({"pc": A})["limits"], "")

    # ---- the real witnesses, on this machine ------------------------------
    check("W1 file_root hashes a real file at the micro scale",
          len(t.file_root(os.path.join(HERE, "triangulate.py")) or "") == 64,
          "")
    check("W2 an absent file is SILENT, not an exception -- unreachable is a "
          "verdict this system knows how to report",
          t.file_root(os.path.join(HERE, "no-such-file")) is None, "")

    p = sum(results)
    print(f"\nT1: {p}/{len(results)} passed")
    return 0 if p == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
