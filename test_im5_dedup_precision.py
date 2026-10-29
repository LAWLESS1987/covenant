#!/usr/bin/env python3
"""test_im5_dedup_precision.py -- the improve-miner dedup matches CODE, not prose, both ways.

    python test_im5_dedup_precision.py   -> "IM5: n/n passed"

A 'have' once false-killed a real candidate because the keyword 'joins' matched an English verb in a code
COMMENT via a case-insensitive SUBSTRING on the first keyword only (ops/consult_dedup_precision_external_
2026-10-28.md). The dedup now matches candidate keywords against a file's IDENTIFIER tokens at word level
(snake/camel), excluding comments, docstrings and string literals, and collects ALL matches. Driven both
ways over a temp source tree; offline, no git, no network.
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_improve as CI   # noqa: E402

R = []


def check(name, ok, detail=""):
    R.append(bool(ok))
    print("  %-4s %s%s" % ("ok" if ok else "FAIL", name, "" if ok else "  -- %s" % (str(detail)[:300],)))


def with_src(files, fn):
    d = tempfile.mkdtemp()
    try:
        for name, body in files.items():
            with open(os.path.join(d, name), "w", encoding="utf-8") as f:
                f.write(body)
        return fn(d)
    finally:
        import shutil
        shutil.rmtree(d, ignore_errors=True)


def main():
    print("IM5 -- dedup matches code identifiers, not prose or substrings, both ways\n")

    # A: a keyword ONLY in a comment is NOT matched (the 'joins' false-kill)
    check("IM5.1 a keyword that appears only in a COMMENT is not matched",
          with_src({"a.py": "x = 1  # this joins things together\n"},
                   lambda d: CI._grep_repo(["joins"], root=d)) == "")
    # ...nor in a docstring / string literal
    check("IM5.2 a keyword only in a DOCSTRING/string is not matched",
          with_src({"a.py": "'''this module joins stuff'''\nmsg = 'we promote unresolved joins'\n"},
                   lambda d: CI._grep_repo(["joins", "promote"], root=d)) == "")

    # B: matched only as a word-level identifier component, never as a raw substring
    check("IM5.3 a keyword matching an identifier COMPONENT is matched (snake_case)",
          "joins" in with_src({"a.py": "def resolve_joins():\n    return 1\n"},
                              lambda d: CI._grep_repo(["joins"], root=d)))
    check("IM5.4 a keyword matching a camelCase component is matched",
          "joins" in with_src({"a.py": "def resolveJoins():\n    return 1\n"},
                              lambda d: CI._grep_repo(["joins"], root=d)))
    check("IM5.5 a keyword is NOT matched as a substring of a larger identifier",
          with_src({"a.py": "rejoinstuff = 1\nenjoinment = 2\n"},
                   lambda d: CI._grep_repo(["joins"], root=d)) == "")

    # C: ALL matched concepts are collected, not just the first keyword
    out = with_src({"a.py": "def promote_node():\n    unresolved = []\n    return unresolved\n"},
                   lambda d: CI._grep_repo(["promote", "unresolved", "joins"], root=d))
    check("IM5.6 all matched concepts are collected (promote AND unresolved), not just the first",
          "promote" in out and "unresolved" in out and "joins" not in out, out)

    # a file that will not tokenize contributes nothing (conservative: no false 'have')
    check("IM5.7 an unparseable source contributes no match (fail toward fewer 'have's)",
          with_src({"bad.py": "def (:\n  this is not python\n"},
                   lambda d: CI._grep_repo(["joins"], root=d)) == "")

    # the real regression: the candidate no longer matches on the comment word 'joins'
    g = CI._grep_repo(["joins"])          # live tree: 'joins' now appears only in prose, not as an identifier
    check("IM5.8 live: 'joins' alone no longer matches (it was a comment word, not code)", g == "", g)

    # ---- concept-COVERAGE downgrade (ChatGPT, 2026-10-28): a single lone match on a multi-concept candidate
    # is too weak to be a 'have' -> backlog (needs a human), evidence attached. Both ways, with injected grep. ----
    one = lambda terms: "unresolved @ covenant_daily.py (code `unresolved`)"   # noqa: E731
    two = lambda terms: "alpha @ a.py (code `alpha`); beta @ b.py (code `beta`)"  # noqa: E731
    c_multi = {"kind": "gap", "maps": "", "idea": "promote unresolved joins inheritance", "test": "t"}
    c_one = {"kind": "gap", "maps": "", "idea": "unresolved", "test": "t"}
    check("IM5.9 a single lexical match on a multi-concept candidate is DOWNGRADED to backlog (not have)",
          CI.vet(c_multi, grep=one)["status"] == "backlog", CI.vet(c_multi, grep=one))
    check("IM5.10 two matched concepts clear the coverage bar -> have",
          CI.vet(c_multi, grep=two)["status"] == "have", CI.vet(c_multi, grep=two))
    check("IM5.11 a single match that is FULL coverage (candidate has one content term) stays have",
          CI.vet(c_one, grep=one)["status"] == "have", CI.vet(c_one, grep=one))
    check("IM5.12 the live 'promote unresolved joins' candidate is now backlog, not a false have",
          CI.vet({"kind": "gap", "maps": "", "idea": "Promote unresolved joins to first-class objects for "
                  "inheritance", "test": "present=green / removed=red"})["status"] == "backlog", None)

    ok = sum(R)
    print("\nIM5: %d/%d passed" % (ok, len(R)))
    print("LIMIT: this tests the matcher's precision, not whether any match is a real capability -- a lexical "
          "match is evidence to INVESTIGATE (held by the circle-back for a disposition), never proof.")
    return 0 if ok == len(R) else 1


if __name__ == "__main__":
    raise SystemExit(main())
