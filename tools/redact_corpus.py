#!/usr/bin/env python3
"""redact_corpus.py -- black out everything identifying, keep the operator's own.

THE INSTRUCTION, 2026-09-18: "block names and emails and numbers leave who i
stated the rest black out but post." Then: "all of em. totality."

WHO IS LEFT STANDING. The operator, and the family he holds authority for --
his deceased relatives, and his mother, who has dementia and for whom he holds
power of attorney as her only heir. He stated that decision and it is his.

WHAT IS BLACKED OUT. Every other name, and every OTHER category that identifies
a person without naming them -- the part he added after reading the measurement,
and the part that separates redaction from de-identification. A name pass alone
would have removed 13,871 strings and left 4,678 identifying facts standing:
relationship descriptions, dates of death, medical detail, addresses, handles,
financial positions. Those go too.

TWO BUGS IN THE FIRST DRAFT, both found by re-reading it rather than by running
it, and both of the same kind -- a rule that looked protective and leaked:

  1. THE ALLOWLIST LEAKED THROUGH SHARED FIRST NAMES. `_keep()` kept a
     capitalised RUN if ANY word in it matched a kept name, so a third party
     who happened to share the operator's first name survived the pass
     entirely. An allowlist that widens on a partial match is not an allowlist.
  2. SINGLE NAMES WERE NEVER REDACTED. The pattern required two capitalised
     words, so "Sarah said" passed untouched while "Sarah Jones" was caught. In
     a personal corpus most references are first-name-only, which means the
     first draft would have reported thousands of removals and left the
     commonest form of the thing it was removing.

Both are fixed by working TOKEN BY TOKEN: every capitalised word is either a
known English word, a name the operator released, or blacked out. Aggressive on
purpose -- he asked for totality, and over-redaction is the safe direction. It
will black out some ordinary capitalised words, and that is the trade.

IT MEASURES ITS OWN RESIDUAL. The same detectors run over the OUTPUT, plus a
count of surviving capitalised tokens as an independent signal. A redactor that
reports what it removed and not what survived is the false green this repository
keeps finding.

WHAT IT DOES NOT DO. It does not publish. It writes a tree and prints a report;
posting is a separate act by a person who has read the residual.

  python tools/redact_corpus.py --out public_record --sample 40
  python tools/redact_corpus.py --out public_record --dry-run     measure only
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import hmac
import os
import re
import secrets
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOTS = ("private", os.path.join("ops", "chat"))
TEXT_EXT = (".md", ".txt")

#: Released by the operator, at his instruction. EXACT tokens, matched whole and
#: lowercased -- never as a substring, and never widening a multi-word name.
KEEP_TOKENS = frozenset(("lawrence", "adam", "moskowski", "lawless", "larry"))

#: The operator's reading key: token -> real name, in assignment order. It sits
#: INSIDE the gitignored private tree, because it is the only thing that can
#: reverse the published text and it must never be in what gets published.
#: There is no cryptographic key anywhere -- see the Names class for why a
#: counter is the right way to have none.
MAP_PATH = os.path.join(HERE, "private", "REDACTION_MAP.tsv")


class Names:
    """Sequential pseudonyms: [Person-001], [Person-002], in order of appearance.

    NO KEY, at the operator's instruction -- and a counter is the right way to
    have none, where a hash is not.

    WHY NOT AN UNKEYED HASH, which is what "encrypt with no key" would mean in
    practice: a name is drawn from a small set. Anyone can hash a list of
    ordinary first and last names, compare, and read the corpus back. Against
    the ~4,700 names here that dictionary attack succeeds on nearly all of them
    in seconds. It would LOOK like protection and be none, which is worse than
    a visible [NAME] because a reader would trust it.

    A counter carries no information about the name at all. The published text
    cannot be inverted even in principle, because the relationship between
    token and name exists only in the map this writes beside it -- which stays
    in the gitignored tree.

    WHAT IT STILL LEAKS, and this is inherent to any stable pseudonym rather
    than a flaw in the counter: who appears with whom, how often, and in what
    order. With dates and places surviving in the text, that can re-identify
    somebody without any token ever being reversed. The alternative is
    --flat, which destroys the structure and the readability together.
    """

    def __init__(self, width=3):
        self.width = width
        self._by_name = {}
        self.order = []

    def token(self, name):
        low = name.strip().lower()
        if low not in self._by_name:
            self._by_name[low] = "Person-%0*d" % (self.width, len(self._by_name) + 1)
            self.order.append(low)
        return self._by_name[low]

    def map_rows(self):
        """(token, name) in assignment order -- the operator's reading key."""
        return [(self._by_name[n], n) for n in self.order]

    def __len__(self):
        return len(self._by_name)

#: Capitalised words that are ordinary English, not people. Everything
#: capitalised and NOT in here is blacked out, so this list is the entire
#: difference between readable output and a page of bars -- and erring toward a
#: short list errs toward redaction, which is the direction asked for.
COMMON = frozenset("""
a an the this that these those there their them they then than and but or for
nor yet so if because while when where what which who whom whose why how all
any some none each every both few many most other another such only own same
too very can could will would shall should may might must do does did done
have has had having be been being am is are was were i me my mine myself we us
our ours you your yours he him his she her hers it its as at by from in into of
off on onto out over to up upon with within without about above across after
against along among around before behind below beneath beside between beyond
during except inside near outside since through throughout till toward under
until via new old good bad better best worse worst first second third last next
later early late high low long short big small large great little right left
true false yes no not never always often sometimes again once now today
tomorrow yesterday here just also however therefore thus hence still even
almost enough quite rather really very much more less least many
god lord jesus christ bible genesis exodus psalm psalms matthew mark luke john
acts romans revelation holy spirit heaven hell earth amen faith grace mercy
monday tuesday wednesday thursday friday saturday sunday january february march
april may june july august september october november december spring summer
autumn fall winter morning afternoon evening night week month year day hour
minute moment time
covenant sentinel witness ledger chain block node judge student elder operator
rule rules record records report reports note notes data file files document
documents index strategy cost costs yield scan test check gate seal
kraken coinbase crypto bitcoin ethereum ripple solana cardano dogecoin binance
facebook instagram youtube twitter tiktok reddit snapchat whatsapp telegram
google apple microsoft amazon netflix nvidia tesla
claude chatgpt gemini grok deepseek anthropic openai llama mistral copilot
python java javascript windows linux android chrome firefox safari edge github
united states america american usa jersey york county city state country world
thank thanks please sorry hello hey okay yeah yep nope well oh ah um hmm
love hope truth life death money work home family friend people person man
woman child children son daughter parent
video post comment share like follow subscribe channel page group story reel
live stream upload caption transcript audio text words said says say saying
one two three four five six seven eight nine ten hundred thousand million
""".split())

#: Ordered. Emails before names, so a name inside an address never survives as
#: a name; amounts before the generic number rule, so "$1,000" is an AMOUNT and
#: not a bare ID.
RULES = [
    ("EMAIL",    re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]{2,}\b")),
    ("URL",      re.compile(r"https?://\S+|\bwww\.\S+")),
    ("PHONE",    re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b")),
    ("ADDRESS",  re.compile(r"\b\d{1,5}\s+[A-Z][a-z]+\s+(?:St|Street|Ave|Avenue|"
                            r"Rd|Road|Dr|Drive|Ln|Lane|Blvd|Ct|Court|Way|Pl|Place)\b")),
    ("RELATION", re.compile(r"\b(?:my|his|her|their|our|your)\s+(?:mother|father|"
                            r"mom|mum|dad|brother|sister|son|daughter|wife|husband|"
                            r"widow|widower|aunt|uncle|cousin|niece|nephew|"
                            r"grandmother|grandfather|grandma|grandpa|stepmother|"
                            r"stepfather|stepson|stepdaughter|girlfriend|boyfriend|"
                            r"fiance|fiancee|neighbour|neighbor|landlord|doctor|"
                            r"lawyer|attorney|therapist|boss|coworker|colleague)\b",
                            re.I)),
    ("MEDICAL",  re.compile(r"\b(?:dementia|alzheimer\w*|cancer|diagnos\w+|hospice|"
                            r"overdose|addiction|rehab|psychiatric|suicide|chemo\w*|"
                            r"tumou?r|stroke|seizure|prognosis|terminal|palliative)\b",
                            re.I)),
    ("DEATH",    re.compile(r"\b(?:died|dying|passed away|death of|funeral|obituary|"
                            r"buried|burial|memorial|cremat\w+|estate of|"
                            r"executor|probate)\b", re.I)),
    ("AMOUNT",   re.compile(r"\$\s?[\d,]{2,}(?:\.\d\d)?|\b\d+(?:\.\d+)?\s?"
                            r"(?:XRP|BTC|ETH|SOL|ADA|HBAR|LINK|XLM|DOGE|USDC|WLFI|"
                            r"CRO|ONDO|PEPE|WLD|JASMY|TOSHI|XCN|USD)\b")),
    ("HANDLE",   re.compile(r"@[A-Za-z0-9_.]{2,}|\b[a-z][a-z._-]*\d{2,}[a-z0-9._-]*\b")),
    # "numbers", per the instruction: any run of 5+ digits is an identifier of
    # something -- an account, a case, a date of birth, a post id.
    ("NUMBER",   re.compile(r"\b\d{5,}\b")),
]

WORD = re.compile(r"\b([A-Z][A-Za-z'’]{1,})\b")


def _blackout_names(text, counts, names=None):
    """Token by token: kept name, ordinary English, or a pseudonym.

    This is the fix for both first-draft bugs. A run-based rule could keep a
    stranger because one word of the run was the operator's; and it could not
    see a first name standing alone, which is how people are usually named.

    `names` is a Names allocator: the replacement is [Person-014], stable across
    the whole corpus, so a reader can follow who is who without learning who
    anyone IS. Pass None for a flat [NAME] -- safer, unreadable, and it carries
    no co-occurrence structure to correlate.
    """
    def sub(m):
        tok = m.group(1)
        low = tok.lower().rstrip("'’s")
        if low in KEEP_TOKENS or tok.lower() in KEEP_TOKENS:
            return tok
        if low in COMMON or tok.lower() in COMMON:
            return tok
        if len(tok) < 2 or tok.isupper():        # initials and ACRONYMS
            return tok
        counts["NAME"] += 1
        if names is None:
            return "[NAME]"
        return "[%s]" % names.token(low)
    return WORD.sub(sub, text)


def redact(text, names=None):
    counts = collections.Counter()
    for label, rx in RULES:
        def sub(m, label=label):
            counts[label] += 1
            return "[%s]" % label
        text = rx.sub(sub, text)
    return _blackout_names(text, counts, names), counts


def residual(text):
    """What the same detectors still find, plus surviving capitalised tokens.

    The second half is the honest part: it is an INDEPENDENT signal, not the
    same rule re-run, so it can disagree with the first half.
    """
    out = collections.Counter()
    for label, rx in RULES:
        n = len(rx.findall(text))
        if n:
            out[label] += n
    survivors = [t for t in WORD.findall(text)
                 if t.lower() not in COMMON and t.lower() not in KEEP_TOKENS
                 and not t.isupper() and t.lower().rstrip("'’s") not in COMMON]
    if survivors:
        out["CAPITALISED"] += len(survivors)
    return out, collections.Counter(survivors)


def files():
    out = []
    for root in ROOTS:
        base = os.path.join(HERE, root)
        if not os.path.isdir(base):
            continue
        for d, subdirs, names in os.walk(base):
            subdirs[:] = [s for s in subdirs if s != "__pycache__"]
            for n in names:
                if n.lower().endswith(TEXT_EXT) and not n.startswith("NAME_APPROVAL"):
                    out.append(os.path.join(d, n))
    return sorted(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--sample", type=int, default=0,
                    help="print N lines of the first redacted file")
    ap.add_argument("--dry-run", action="store_true",
                    help="measure and report; write nothing")
    ap.add_argument("--flat", action="store_true",
                    help="flat [NAME] instead of [Person-NNN]: unreadable, and "
                         "carries no per-person structure to correlate")
    a = ap.parse_args(argv)

    dest = os.path.join(HERE, a.out)
    if os.path.abspath(dest).startswith(os.path.abspath(os.path.join(HERE, "private"))):
        print("refusing: the output would sit inside the private tree")
        return 2
    paths = files()
    if not paths:
        print("no corpus under %s" % ", ".join(ROOTS))
        return 1

    names = None if a.flat else Names()
    removed, left = collections.Counter(), collections.Counter()
    survivors = collections.Counter()
    in_bytes = out_bytes = written = 0
    first_out = None
    for p in paths:
        try:
            with open(p, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue
        in_bytes += len(text)
        red, counts = redact(text, names)
        removed.update(counts)
        r, surv = residual(red)
        left.update(r)
        survivors.update(surv)
        out_bytes += len(red)
        if not a.dry_run:
            target = os.path.join(dest, os.path.relpath(p, HERE))
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "w", encoding="utf-8") as fh:
                fh.write(red)
            first_out = first_out or target
        written += 1

    print("REDACTION%s -- %d file(s), %.1f MB in, %.1f MB out"
          % (" (dry run, nothing written)" if a.dry_run else "",
             written, in_bytes / 1048576.0, out_bytes / 1048576.0))
    print("   released: %s" % ", ".join(sorted(KEEP_TOKENS)))
    print()
    print("   %-12s %10s %10s" % ("category", "removed", "RESIDUAL"))
    for label in sorted(set(removed) | set(left), key=lambda k: -removed[k]):
        print("   %-12s %10d %10d" % (label, removed[label], left[label]))
    print("   %-12s %10d %10d" % ("TOTAL", sum(removed.values()), sum(left.values())))
    print()
    if survivors:
        print("   %d capitalised token(s) survived, %d distinct. These are the"
              % (sum(survivors.values()), len(survivors)))
        print("   independent signal: every one is either an ordinary word this")
        print("   tool does not know, or a NAME IT FAILED TO REMOVE. Read them.")
        print("   The 15 commonest, for judging which: %s"
              % ", ".join(t for t, _c in survivors.most_common(15)))
    else:
        print("   No capitalised token survived -- which means the output is")
        print("   likely unreadable as well as de-identified. Check the sample.")
    if names is not None:
        print()
        print("   %d distinct person(s) numbered, in order of first appearance."
              % len(names))
        print("   NO KEY EXISTS -- the token is a counter, so the published text")
        print("   cannot be inverted even in principle. An unkeyed HASH would")
        print("   have looked the same and been reversible in seconds: a name")
        print("   comes from a small set, so hashing a name list and comparing")
        print("   reads the corpus straight back.")
        if not a.dry_run:
            os.makedirs(os.path.dirname(MAP_PATH), exist_ok=True)
            with open(MAP_PATH, "w", encoding="utf-8") as fh:
                fh.write("# token\tname -- YOUR reading key for the redacted corpus.\n")
                fh.write("# Gitignored. Posting this file undoes the redaction entirely.\n")
                for tag, real in names.map_rows():
                    fh.write("%s\t%s\n" % (tag, real))
            print("   map -> %s  (yours; posting it undoes all of this)"
                  % os.path.relpath(MAP_PATH, HERE))
        print()
        print("   WHAT A STABLE TOKEN STILL LEAKS, inherent to any pseudonym and")
        print("   not a flaw in the counter: who appears with whom, how often, in")
        print("   what order. With dates and places left in the text that can")
        print("   re-identify somebody without any token being reversed. --flat")
        print("   removes the structure and the readability together.")
    print()
    print("   Residual zero by these detectors is NOT de-identification. These")
    print("   are the patterns I thought of; a paragraph that identifies someone")
    print("   by circumstance alone defeats all of them and always will.")
    if a.sample and first_out:
        print()
        print("   sample -- %s" % os.path.relpath(first_out, HERE))
        with open(first_out, encoding="utf-8") as fh:
            for i, line in enumerate(fh):
                if i >= a.sample:
                    break
                print("     " + line.rstrip()[:96])
    if not a.dry_run:
        print()
        print("   written to %s/ -- NOT committed. Posting is a separate act." % a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
