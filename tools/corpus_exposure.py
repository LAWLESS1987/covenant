#!/usr/bin/env python3
"""corpus_exposure.py -- what would publishing the private corpus actually expose?

ASKED 2026-09-18: copy the covenant memories somewhere unblocked, redacting
every name except the operator's own and his family's (his mother included --
he holds power of attorney, she has dementia, he is her only heir, and that
decision is his).

WHY THIS TOOL EXISTS RATHER THAN A REDACTOR THAT JUST RUNS. A name blocklist is
an EXISTENCE ORACLE: it answers "does this string appear?" and nothing else. It
cannot see "my brother's widow", a street, a date of death, a photo caption, or
a paragraph that identifies somebody precisely without ever naming them. Run one
over a personal corpus and it will report success while leaving people
identifiable -- a false green, of exactly the shape this repository spent the day
removing. So this measures the exposure FIRST, in categories, and states its own
blind spots, and the operator decides with numbers in front of him.

WHAT IT WILL NOT DO
  * It writes no redacted corpus and publishes nothing. It is a report.
  * It prints COUNTS and CATEGORIES, never the names it found. A tool whose
    output is a list of the private individuals in a private corpus has moved
    the exposure into its own log.
  * The candidate names go to a local file, for the operator's eyes, which is
    itself gitignored by the caller's choice -- not to stdout.

  python tools/corpus_exposure.py                 measure, print the report
  python tools/corpus_exposure.py --names OUT     also write candidates to OUT
"""
from __future__ import annotations

import argparse
import collections
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: Where the corpus lives. Discovered by walking, never a filename list (rule 2).
ROOTS = ("private", os.path.join("ops", "chat"))
TEXT_EXT = (".md", ".txt", ".json", ".jsonl")

#: Names the operator has authority to release: his own, and his family's.
#: Deliberately short and explicit. Everything else is a third party.
KEEP = {"lawrence", "adam", "moskowski", "lawless", "l."}

#: Capitalised runs of 2+ words: the crude person-name candidate. Crude is
#: acceptable ONLY because the report says how crude -- see BLIND_SPOTS.
NAME_RUN = re.compile(r"\b([A-Z][a-z]{1,15}(?:\s+[A-Z][a-z]{1,15}){1,3})\b")

#: Words that begin a capitalised run without being a person.
NOT_PEOPLE = frozenset("""
the this that these those and but for with from into over under after before
new old god lord jesus christ bible genesis exodus psalm matthew mark luke john
united states new jersey north south east west monday tuesday wednesday
thursday friday saturday sunday january february march april may june july
august september october november december covenant sentinel witness kraken
coinbase crypto bitcoin ethereum ripple facebook instagram youtube twitter
claude chatgpt gemini grok deepseek anthropic openai google microsoft apple
""".split())

#: Things a name blocklist provably cannot catch. Counted, so the gap has a size.
BLIND_SPOTS = {
    "relationship": re.compile(
        r"\b(my|his|her|their)\s+(mother|father|mom|dad|brother|sister|son|"
        r"daughter|wife|husband|widow|widower|aunt|uncle|cousin|niece|nephew|"
        r"grandmother|grandfather|grandma|grandpa|stepmother|stepfather|"
        r"girlfriend|boyfriend|fiance|fiancee|ex|neighbour|neighbor|landlord|"
        r"doctor|lawyer|attorney|therapist|boss|coworker)\b", re.I),
    "street address": re.compile(
        r"\b\d{1,5}\s+[A-Z][a-z]+\s+(St|Street|Ave|Avenue|Rd|Road|Dr|Drive|"
        r"Ln|Lane|Blvd|Ct|Court|Way|Pl|Place)\b"),
    "phone": re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b"),
    "email": re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]{2,}\b"),
    "date of death": re.compile(r"\b(died|passed away|death of|funeral|obituary|"
                                r"buried|memorial)\b", re.I),
    "medical": re.compile(r"\b(dementia|alzheimer|cancer|diagnos\w+|hospice|"
                          r"overdose|addiction|rehab|psychiatric|suicide)\b", re.I),
    "financial position": re.compile(
        r"(\$\s?[\d,]{3,}(?:\.\d\d)?|\b\d+(?:\.\d+)?\s?(?:XRP|BTC|ETH|SOL|ADA|"
        r"HBAR|LINK|XLM|DOGE|USDC)\b)"),
    "handle": re.compile(r"\b[a-z]{2,}\d{3,}\b"),
}


def files():
    """Every text file under the roots, by walking. Never a hardcoded list."""
    out = []
    for root in ROOTS:
        base = os.path.join(HERE, root)
        if not os.path.isdir(base):
            continue
        for d, _subdirs, names in os.walk(base):
            if "__pycache__" in d:
                continue
            for n in names:
                if n.lower().endswith(TEXT_EXT):
                    out.append(os.path.join(d, n))
    return sorted(out)


def _is_person(run):
    words = run.lower().split()
    if any(w in NOT_PEOPLE for w in words):
        return False
    return not all(w in KEEP for w in words)


def measure(paths):
    names = collections.Counter()
    spots = collections.Counter()
    per_file_spots = collections.Counter()
    unreadable = []
    total_bytes = 0
    for p in paths:
        try:
            with open(p, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError as e:
            unreadable.append((p, type(e).__name__))
            continue
        total_bytes += len(text)
        for run in NAME_RUN.findall(text):
            if _is_person(run):
                names[run] += 1
        for label, rx in BLIND_SPOTS.items():
            n = len(rx.findall(text))
            if n:
                spots[label] += n
                per_file_spots[label] += 1
    return names, spots, per_file_spots, unreadable, total_bytes


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--names", metavar="OUT",
                    help="write the candidate third-party names to this file "
                         "(local only; never printed to stdout)")
    a = ap.parse_args(argv)

    paths = files()
    if not paths:
        print("no corpus found under %s -- nothing to measure" % ", ".join(ROOTS))
        return 1
    names, spots, per_file, unreadable, nbytes = measure(paths)

    print("CORPUS EXPOSURE -- measured, %d file(s), %.1f MB of text"
          % (len(paths), nbytes / 1048576.0))
    print("   roots walked: %s" % ", ".join(ROOTS))
    if unreadable:
        print("   %d file(s) could not be read: %s"
              % (len(unreadable), sorted({k for _p, k in unreadable})))
    print()
    print("WHAT A NAME BLOCKLIST WOULD HAVE TO REDACT")
    print("   distinct candidate third-party names : %d" % len(names))
    print("   total occurrences                    : %d" % sum(names.values()))
    top = sum(c for _n, c in names.most_common(20))
    print("   the 20 commonest account for         : %d of those (%.0f%%)"
          % (top, 100.0 * top / max(1, sum(names.values()))))
    print()
    print("WHAT IT PROVABLY CANNOT REDACT -- the same corpus, by category.")
    print("Each of these identifies a person without using their name, so")
    print("blocking names leaves every one of them standing:")
    print()
    print("   %-20s %8s  %s" % ("category", "hits", "files"))
    for label in sorted(spots, key=lambda k: -spots[k]):
        print("   %-20s %8d  %d" % (label, spots[label], per_file[label]))
    if not spots:
        print("   (none found -- which would be surprising; check the patterns)")
    print()
    print("READ THIS AS: a name pass would remove %d strings and leave %d other"
          % (sum(names.values()), sum(spots.values())))
    print("identifying facts in place. The second number is not a bug in the")
    print("redactor; it is the reason a name pass is not de-identification.")
    if a.names:
        with open(a.names, "w", encoding="utf-8") as fh:
            fh.write("# candidate third-party names, most frequent first.\n")
            fh.write("# Reviewed by the operator; NOT printed to any log.\n")
            for n, c in names.most_common():
                fh.write("%6d  %s\n" % (c, n))
        print()
        print("candidates written to %s (%d distinct) -- local, for your eyes."
              % (a.names, len(names)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
