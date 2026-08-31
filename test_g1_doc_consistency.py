#!/usr/bin/env python3
"""test_g1_doc_consistency.py -- G1: the explanation may not contradict the rule.

THE BUG THIS EXISTS TO CATCH, found on 2026-08-30 by reading rather than by any
check.

The protected, hashed text in CONTRIBUTING.md says:

    a system should serve the mutual benefit of everyone it touches
    -- HUMAN AND MACHINE -- rather than one party at another's expense

CONSTITUTION.md section I, the document people actually read, restated it as
"everyone it touches" and dropped the clause. The most distinctive words in the
whole principle were present in the binding rule and absent from its
explanation. No hash moved, because the hash covers the rule and not the
retelling -- constitution.py was working perfectly and had nothing to say about
it.

That is this project's own failure mode inverted. Usually a summary claims MORE
than the record supports; this one claimed LESS. Both are false statements
about what is true, and only the first has a checker.

WHAT G1 PINS.

  P*  every distinctive phrase of the PROTECTED principle survives into the
      document that explains it. Not the whole text word for word -- an
      explanation is allowed to be an explanation -- but the load-bearing
      clauses may not quietly vanish.
  C*  counts stated in prose match the lists they describe. Section VI's
      numbers were written rather than counted TWICE: "six" over a list of
      seven, then "four" over a list of five, in the one section whose entire
      purpose is to be countable.
  X*  cross-references between documents agree with each other.

Pure: reads two files, parses no code, touches nothing.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CONST = os.path.join(HERE, "docs", "CONSTITUTION.md")
GOV = os.path.join(HERE, "docs", "GOVERNANCE.md")
CONTRIB = os.path.join(HERE, "CONTRIBUTING.md")

results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print(f"{'ok  ' if ok else 'FAIL'}  {label}"
          f"{'' if ok else '  ' + str(detail)[:180]}", flush=True)


def read(p):
    try:
        with open(p, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def norm(t):
    """Dashes and whitespace vary between documents; meaning does not."""
    t = t.replace("—", "-").replace("–", "-").replace("’", "'")
    return re.sub(r"\s+", " ", t).lower()


def section(text, head):
    i = text.find(head)
    if i < 0:
        return ""
    j = text.find("\n## ", i + len(head))
    return text[i:j if j > 0 else len(text)]


def main():
    print("G1 -- the explanation may not contradict the rule\n")

    contrib, const, gov = read(CONTRIB), read(CONST), read(GOV)
    check("S0 all three documents are readable",
          bool(contrib) and bool(const) and bool(gov))
    principle_rule = norm(contrib)

    # THE STATEMENT, not the section. The first version of this test took the
    # whole of section I and PASSED when the bug was reintroduced -- because
    # section I now contains a paragraph explaining that "human and machine"
    # had gone missing, so the phrase survived in the commentary ABOUT it while
    # being absent from the principle itself. A guard blind to the exact defect
    # it was written for, passing 12/12, discovered only by mutation-testing it.
    #
    # So: only the bolded assertion at the top of section I counts. That is
    # what a reader takes as the principle, and it is the thing that lost the
    # words.
    _sec1 = section(const, "## I. The principle")
    _m = re.search(r"\*\*(.+?)\*\*", _sec1, re.S)
    principle_doc = norm(_m.group(1)) if _m else ""
    check("S1 the principle STATEMENT was extracted -- the bolded assertion at "
          "the top of section I, not the whole section. Testing the whole "
          "section WAS the bug: the paragraph explaining the omission contains "
          "the very phrase the omission removed, so the guard passed 12/12 "
          "with the defect reintroduced",
          bool(principle_doc) and len(principle_doc) < 400, principle_doc[:80])

    # ---- P: the load-bearing clauses of the principle -----------------------
    # Each of these is IN the protected text. An explanation may reword, but it
    # may not silently drop the clause that makes the principle distinctive.
    CLAUSES = [
        ("human and machine",
         "the extension beyond people -- the single most distinctive clause, "
         "and the one that actually went missing"),
        ("mutual benefit",
         "the principle's own name for what it requires"),
        ("one party at another's expense",
         "the thing it forbids; without it 'mutual benefit' is a mood"),
    ]
    for phrase, why in CLAUSES:
        in_rule = phrase in principle_rule
        in_doc = phrase in principle_doc
        check("P:%-32s present in the binding text AND in section I -- %s"
              % ('"' + phrase + '"', why),
              (not in_rule) or in_doc,
              "in CONTRIBUTING.md=%s, in CONSTITUTION.md I=%s" % (in_rule, in_doc))

    check("P4 ...and the phrase really is in the protected text, so P1 is "
          "testing something rather than passing vacuously",
          "human and machine" in principle_rule)

    # ---- C: stated counts match counted lists ------------------------------
    sec6 = section(const, '## VI. "Human and machine"')
    check("C0 section VI exists to be counted", bool(sec6))

    def items(start, end):
        seg = sec6[sec6.find(start):sec6.find(end) if end in sec6 else len(sec6)]
        return len(re.findall(r"^- \*\*", seg, re.M))

    enf = items("### Enforced in code", "### Adjacent")
    adj = items("### Adjacent", "### Not enforced")
    non = items("### Not enforced", "Anyone who reads")
    stated = re.search(r"\*\*in (\d+) specific places.*?(\d+) more are adjacent"
                       r".*?In (\d+) it does not ask", sec6, re.S)
    check("C1 section VI states its three counts in a form that can be checked",
          stated is not None)
    if stated:
        s_enf, s_adj, s_non = (int(g) for g in stated.groups())
        check("C2 the ENFORCED count matches the enforced list. Written rather "
              "than counted twice already: 'six' over seven, then 'four' over "
              "five", s_enf == enf, "stated %d, counted %d" % (s_enf, enf))
        check("C3 the ADJACENT count matches", s_adj == adj,
              "stated %d, counted %d" % (s_adj, adj))
        check("C4 the NOT-ENFORCED count matches -- the most important of the "
              "three, because it is the one an author is tempted to shrink",
              s_non == non, "stated %d, counted %d" % (s_non, non))

    # ---- X: the documents agree with each other ----------------------------
    m = re.search(r"section VI lists the (\w+) places this is\s*\n?enforced",
                  gov)
    words = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
             "seven": 7, "eight": 8, "nine": 9, "ten": 10}
    check("X1 GOVERNANCE.md's cross-reference to section VI names the same "
          "number CONSTITUTION.md does. Two documents disagreeing about one "
          "list is how a reader learns to trust neither",
          m is not None and words.get(m.group(1), -1) == enf,
          (m.group(1) if m else "no cross-reference found", enf))
    check("X2 GOVERNANCE.md carries the extension too, so a reader who starts "
          "there is not told a narrower principle than the one that binds",
          "human and machine" in norm(gov))

    n, ok = len(results), sum(results)
    print(f"\nG1: {ok}/{n} passed")
    return 0 if ok == n else 1


if __name__ == "__main__":
    raise SystemExit(main())
