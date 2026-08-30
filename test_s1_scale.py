#!/usr/bin/env python3
"""test_s1_scale.py -- S1: governance that composes, and refuses to launder.

WHAT S1 PINS.

scale.py lets a level's verdict be a witness one level up, which is what makes
"the same function at every scale" mean a relation that composes rather than a
list of scales somebody thought of. Three nodes make a ledger, three ledgers a
region, three regions a federation, judged by identical code at every step.

  C*  COMPOSITION. Levels that agree produce a parent that agrees. This looks
      trivial and is the bug scale.py shipped with for one run: the upward
      digest was keyed by the LEVEL'S NAME, so three ledgers all holding the
      same root produced three different digests and every region reported
      DIVERGED. Naming the speaker inside what it says means siblings can never
      agree about anything. The identity of a witness belongs in the tally,
      never in the value being compared.
  I*  THE INVARIANT: divergence never disappears as you climb. A diverged level
      goes SILENT upward and never passes its majority root along. The naive
      implementation passes the majority, and then three regions each hiding a
      dissenting node report perfect consensus -- the higher you look the
      cleaner it appears, which is exactly backwards.
  N*  a divergence at any depth is NAMED at the summit, and `overall` is never
      CLEAN while one exists. A clean summit over a hidden disagreement is the
      most dangerous output this system could produce.
  D*  arbitrary DEPTH, with a refusal rather than a hang past the limit.
  S*  silence is not disagreement, at every level, inherited from attest.
  P*  nothing resolves a divergence and nothing overwrites anybody -- the
      property that lets a branch adopt this without adopting an authority.

Pure: no network, no disk, no clock.
"""
import ast
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import scale as s   # noqa: E402
from triangulate import AGREE, DIVERGED, UNPROVEN   # noqa: E402

results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print(f"{'ok  ' if ok else 'FAIL'}  {label}"
          f"{'' if ok else '  ' + str(detail)[:170]}", flush=True)


A, B, C = "a" * 64, "b" * 64, "c" * 64


def ledger(name, roots):
    return s.level(name, [s.leaf("n%d" % i, r) for i, r in enumerate(roots)])


def main():
    print("S1 -- one relation, any depth, and no laundering\n")

    # ---- C: composition ----------------------------------------------------
    up1, r1 = s.climb(ledger("L1", [A, A, A]))
    up2, r2 = s.climb(ledger("L2", [A, A, A]))
    check("C1 a level whose carriers agree, agrees", r1["verdict"] == AGREE, r1["why"])
    check("C2 ...and speaks a root upward", up1 is not None)
    check("C3 THE SHIPPED BUG: two DIFFERENTLY NAMED levels holding the same "
          "content speak the SAME root upward. Keying the digest by level "
          "name made three agreeing ledgers look like three disagreeing ones, "
          "and every region above them reported DIVERGED",
          up1 == up2, (up1, up2))
    check("C4 an agreeing level speaks the agreed root UNCHANGED, so its "
          "value does not depend on how deep it sits. The version that "
          "wrapped a digest per level made a three-deep region unable to "
          "agree with a one-deep ledger beside it -- composition that only "
          "works on balanced trees is a shape requirement, not composition",
          up1 == A, (up1, A))
    mixed_height = s.level("MH", [s.leaf("bare", A),
                                  ledger("one-deep", [A, A, A]),
                                  s.level("three-deep",
                                          [ledger("d", [A, A, A]),
                                           ledger("e", [A, A, A])])])
    _, rmh = s.climb(mixed_height)
    check("C4b ...so a level whose members are a bare carrier, a ledger and a "
          "whole sub-federation AGREES. Infinite in any SHAPE, not just any "
          "depth", rmh["verdict"] == AGREE, rmh["why"])

    region = s.level("R", [ledger("La", [A, A, A]),
                           ledger("Lb", [A, A, A]),
                           ledger("Lc", [A, A, A])])
    _, rr = s.climb(region)
    check("C5 and so a region of agreeing ledgers AGREES -- composition "
          "actually composing, which is the whole point",
          rr["verdict"] == AGREE, rr["why"])

    # ---- I: the invariant --------------------------------------------------
    div = ledger("Ldiv", [A, B, A])
    upd, rd = s.climb(div)
    check("I1 a diverged level is DIVERGED", rd["verdict"] == DIVERGED)
    check("I2 THE INVARIANT: it speaks SILENCE upward, never its majority "
          "root. Passing the majority is how disagreement launders itself "
          "into consensus one level at a time",
          upd is None, upd)
    check("I3 ...and the majority root is not smuggled out some other way",
          not rd.get("speaks_upward"))

    # A region containing one diverged ledger: the region sees one silent
    # witness and two that agree, which is honest agreement AMONG ANSWERERS.
    mixed = s.level("Rmix", [ledger("m1", [A, A, A]),
                             ledger("m2", [A, B, A]),
                             ledger("m3", [A, A, A])])
    _, rm = s.climb(mixed)
    check("I4 the region above it may still AGREE among the levels that "
          "ANSWERED -- that is honest, and is why N* below must exist",
          rm["verdict"] == AGREE, rm["why"])

    # ---- N: named at the summit, and never clean ---------------------------
    check("N1 the divergence is carried up and NAMED at the summit",
          any("m2" in d for d in rm["divergences"]), rm["divergences"])
    ok, why = s.overall(rm)
    check("N2 ...and `overall` refuses CLEAN while it exists. A clean summit "
          "over a hidden disagreement is the one output this must never "
          "produce", not ok, why)
    deep = s.level("top", [s.level("mid", [s.level("low", [
        ledger("bottom", [A, C, A])])])])
    _, rdeep = s.climb(deep)
    okd, _ = s.overall(rdeep)
    check("N3 a divergence FOUR levels down is still named at the top",
          rdeep["divergences"] and not okd, rdeep["divergences"])
    clean = s.level("Rok", [ledger("k1", [A, A, A]), ledger("k2", [A, A, A]),
                            ledger("k3", [A, A, A])])
    okc, whyc = s.overall(s.climb(clean)[1])
    check("N4 ...and a genuinely clean tree DOES report clean, or the check "
          "is just a machine for saying no", okc, whyc)

    # ---- D: depth ----------------------------------------------------------
    node = ledger("deep0", [A, A, A])
    for i in range(1, 30):
        node = s.level("deep%d" % i, [node, ledger("sib%d" % i, [A, A, A])])
    _, rdd = s.climb(node)
    check("D1 thirty levels deep still resolves, with no new mechanism at any "
          "of them -- growth adds scales, not machinery",
          rdd["verdict"] == AGREE, rdd["why"])
    over = ledger("x", [A, A, A])
    for i in range(s.MAX_DEPTH + 5):
        over = s.level("o%d" % i, [over])
    _, rov = s.climb(over)
    check("D2 past the depth limit it REFUSES rather than hangs -- a verifier "
          "that hangs is a verifier that gets switched off",
          "refused" in str(rov).lower() or rov["verdict"] == UNPROVEN)

    # ---- S: silence is not disagreement ------------------------------------
    _, rs = s.climb(ledger("Lsil", [A, A, None]))
    check("S1 one silent carrier among agreeing ones is still AGREE",
          rs["verdict"] == AGREE, rs["why"])
    check("S2 ...and the silent one is NAMED, so the agreement cannot be "
          "quoted as covering it", rs["silent"] == ["n2"], rs["silent"])
    _, rs2 = s.climb(ledger("Lsil2", [A, None, None]))
    check("S3 too few answers is UNPROVEN, never agreement with itself",
          rs2["verdict"] == UNPROVEN, rs2["why"])
    check("S4 silence is never counted as an outlier -- it did not disagree, "
          "it did not speak", rs["outliers"] == [], rs["outliers"])

    # ---- P: it never resolves anything -------------------------------------
    src = open(os.path.join(HERE, "scale.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    called = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Name):
                called.add(f.id)
            elif isinstance(f, ast.Attribute):
                called.add(f.attr)
    banned = called & {"urlopen", "Popen", "run", "system", "remove", "rmtree",
                       "connect", "write"}
    check("P1 PURE: it opens no socket, spawns nothing, writes nothing. Roots "
          "come in as arguments, so a level can be a machine, an institution "
          "or a country without this file knowing the difference",
          not banned, sorted(banned))
    check("P2 nothing in it resolves, overrides or corrects a divergence -- a "
          "mechanism that could settle disagreement between peers is the one "
          "change that turns federation into administration",
          not any(w in src for w in ("def resolve", "def overwrite",
                                     "def correct", "def enforce")))
    check("P3 the majority is EVIDENCE, said in the output rather than only "
          "intended", "evidence" in rd["why"].lower())

    n = len(results)
    ok_n = sum(results)
    print(f"\nS1: {ok_n}/{n} passed")
    return 0 if ok_n == n else 1


if __name__ == "__main__":
    raise SystemExit(main())
