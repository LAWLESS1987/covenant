#!/usr/bin/env python3
"""name_approval.py -- the operator's approval list for names in the corpus.

ASKED 2026-09-18: "no numbers or emails and give me an approval list of names."

WHAT THIS IS. Every candidate person-name in private/ and ops/chat, ranked by
how often it occurs, written to a file with a DECISION column. The operator
marks KEEP on the names he is releasing; everything else stays REDACT. It is a
worksheet, not a redactor: it reads the corpus and writes one local file.

TWO THINGS ARE NOT NEGOTIABLE HERE, and both are his instruction:

  * PHONE NUMBERS AND EMAIL ADDRESSES ARE NOT ON THE LIST AT ALL. They are not
    names, they cannot be "approved", and they are stripped unconditionally by
    any pass that consumes this file. They appear in the report only as a
    count, so their removal can be verified rather than assumed.
  * REDACT IS THE DEFAULT. An unreviewed name is redacted, never kept. A
    worksheet whose blank rows mean "publish" would turn not-getting-round-to-it
    into disclosure.

WHERE IT WRITES. private/NAME_APPROVAL.tsv -- inside the gitignored tree, so the
list of people in a private corpus cannot itself be committed. It is never
printed to stdout for the same reason: a tool whose log enumerates the private
individuals in a private corpus has moved the exposure into the log.

AND THE RULE THIS DOES NOT TOUCH. docs/CONSTITUTION.md II.4: "The private corpus
is never published, in whole or in part, for any reason, including a reason that
seems excellent at the time." This tool publishes nothing and is not a step
toward publishing; it answers a narrower question -- which names are the
operator's to release if he ever amends that rule deliberately.

  python tools/name_approval.py              write the worksheet
  python tools/name_approval.py --min 3      only names occurring 3+ times
"""
from __future__ import annotations

import argparse
import collections
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOTS = ("private", os.path.join("ops", "chat"))
TEXT_EXT = (".md", ".txt", ".json", ".jsonl")
OUT = os.path.join(HERE, "private", "NAME_APPROVAL.tsv")

#: Pre-approved: the operator's own name and the family he holds authority for.
#: Family members are included at his instruction, on legal authority he holds;
#: the decision is his. The basis is recorded privately (not in this public
#: file, 2026-09-26 OPSEC sweep) rather than inferred, so it stays auditable.
PRE_APPROVED = ("Lawrence", "Adam", "Moskowski", "Lawless")

NAME_RUN = re.compile(r"\b([A-Z][a-z]{1,15}(?:\s+[A-Z][a-z]{1,15}){1,3})\b")

#: Never a person. Kept long deliberately: every false candidate on the
#: worksheet is a row the operator has to read, and 6,000 rows is not a review.
NOT_PEOPLE = frozenset("""
the this that these those there then than and but for with from into onto over
under after before while when where what which who whom whose why how all any
some none each every both few many most other another such only own same so
than too very can will just should now also however therefore because about
above across against along among around behind below beneath beside between
beyond during except inside outside through toward under until upon within
without new old good bad best worst first last next later early late high low
long short big small great little right left true false yes no not none
god lord jesus christ bible genesis exodus psalm psalms matthew mark luke john
acts romans revelation holy spirit father son heaven hell earth
united states america american jersey york city county street road avenue
monday tuesday wednesday thursday friday saturday sunday
january february march april may june july august september october november
december spring summer autumn winter today tomorrow yesterday morning evening
night week month year day hour minute second
covenant sentinel witness ledger chain block node judge student elder
kraken coinbase crypto bitcoin ethereum ripple solana cardano dogecoin
facebook instagram youtube twitter tiktok reddit google apple microsoft amazon
claude chatgpt gemini grok deepseek anthropic openai llama mistral
python java script windows linux android chrome firefox safari edge
thank thanks please sorry hello hi hey okay yeah yep nope well oh ah um
love hope faith truth life death time money work home family friend
video post comment share like follow subscribe channel page group
""".split())


def files():
    out = []
    for root in ROOTS:
        base = os.path.join(HERE, root)
        if not os.path.isdir(base):
            continue
        for d, _s, names in os.walk(base):
            if "__pycache__" in d:
                continue
            for n in names:
                if n.lower().endswith(TEXT_EXT) and n != os.path.basename(OUT):
                    out.append(os.path.join(d, n))
    return sorted(out)


def _plausible(run):
    """A capitalised run that could be a person. Conservative about EXCLUDING:
    a name wrongly dropped here is a name that never reaches the worksheet and
    so is silently redacted -- which fails safe, and is why the stoplist may be
    aggressive while the KEEP default may not."""
    words = run.split()
    low = [w.lower() for w in words]
    if any(w in NOT_PEOPLE for w in low):
        return False
    if all(w in {p.lower() for p in PRE_APPROVED} for w in low):
        return False            # already the operator's; no decision needed
    return True


def scan(paths):
    names = collections.Counter()
    where = collections.defaultdict(set)
    stripped = collections.Counter()
    PHONE = re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b")
    EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]{2,}\b")
    for p in paths:
        try:
            with open(p, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue
        stripped["phone"] += len(PHONE.findall(text))
        stripped["email"] += len(EMAIL.findall(text))
        # Removed BEFORE name scanning, so a name inside an email address never
        # reaches the worksheet as an approvable string.
        text = EMAIL.sub(" ", PHONE.sub(" ", text))
        for run in NAME_RUN.findall(text):
            if _plausible(run):
                names[run] += 1
                where[run].add(os.path.relpath(p, HERE))
    return names, where, stripped


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--min", type=int, default=1,
                    help="only list names occurring at least this often")
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args(argv)

    paths = files()
    if not paths:
        print("no corpus under %s" % ", ".join(ROOTS))
        return 1
    names, where, stripped = scan(paths)
    listed = [(n, c) for n, c in names.most_common() if c >= a.min]

    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write("# NAME APPROVAL -- %d file(s) scanned, %d candidate name(s)\n"
                 % (len(paths), len(names)))
        fh.write("# Mark the DECISION column KEEP for a name you are releasing.\n")
        fh.write("# ANYTHING NOT MARKED KEEP IS REDACTED. Blank means redact.\n")
        fh.write("#\n")
        fh.write("# Pre-approved and not listed: %s\n" % ", ".join(PRE_APPROVED))
        fh.write("# Phone numbers (%d) and email addresses (%d) are NOT on this\n"
                 % (stripped["phone"], stripped["email"]))
        fh.write("# list and cannot be approved: they are stripped unconditionally.\n")
        fh.write("#\n")
        fh.write("# count\tDECISION\tname\tfiles\n")
        for n, c in listed:
            fh.write("%d\t\t%s\t%d\n" % (c, n, len(where[n])))

    total = sum(c for _n, c in names.most_common())
    cum, need90 = 0, 0
    for _n, c in names.most_common():
        cum += c
        need90 += 1
        if cum >= 0.9 * total:
            break
    print("NAME APPROVAL WORKSHEET")
    print("   scanned            %d file(s) under %s" % (len(paths), ", ".join(ROOTS)))
    print("   candidate names    %d distinct, %d occurrence(s)" % (len(names), total))
    print("   written            %d row(s) (--min %d)" % (len(listed), a.min))
    print("   reviewing the top  %d row(s) covers 90%% of all occurrences" % need90)
    print()
    print("   STRIPPED, not listed, cannot be approved:")
    print("     phone numbers    %d" % stripped["phone"])
    print("     email addresses  %d" % stripped["email"])
    print()
    print("   -> %s" % os.path.relpath(a.out, HERE))
    print("   Blank DECISION means REDACT. Only KEEP releases a name.")
    print("   The file is inside the gitignored tree, so the list itself cannot")
    print("   be committed, and no name is printed here.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
