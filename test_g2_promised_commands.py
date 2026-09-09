#!/usr/bin/env python3
"""test_g2_promised_commands.py -- G2: a document that promises a command must
be able to run it, and the command must describe the code that exists.

THE BUG THIS EXISTS TO CATCH, found on 2026-09-02 at the start of a session,
by `git status` rather than by any check.

CONSTITUTION.md II.1 says, of the one clause that concerns money: "Do not take
that on trust ... it is reported by a checker rather than asserted by a
document: python money_posture.py". README.md, GOVERNANCE.md (twice) and
SAFEGUARD.bat step 7 of 7 say the same. That file was DELETED from the working
tree -- uncommitted, unexplained -- and four documents plus the safeguard
script went on promising it. SAFEGUARD.bat would have printed Python's
"can't open file" and carried on to "STILL OPEN". G1 checks that explanations
do not contradict rules; nothing checked that a promised command exists.

Then, restored, the checker was found to have been wrong the day it was
written: it named two venues by hand (Kraken, Coinbase) and said "both default
to the venue's own dry-run endpoint". venues.py had held a THIRD adapter
(Robinhood) since the day before, with no venue-side dry run at all -- and
every document making the money claim named two venues and one uniform
guarantee. Code and documents did not contradict each other; the guarantee
was narrower than the sentence, and no check compared them.

WHAT G2 PINS.

  E*  every `python X.py` a governing document or safeguard script promises
      resolves to a file that exists and compiles. Not "is mentioned" --
      exists, and would at least parse if run.
  R*  the money checker the constitution names actually RUNS and can
      DETERMINE the posture. Exit 2 ("could not determine") is a failure
      here: the documents point a reader at a checker that cannot see.
  D*  every document that describes the money posture names every order
      adapter venues.py holds, and does not promise a venue-side dry run of
      "every order" when the weakest adapter's dry run is local.
  M*  the checks above are not vacuous: the regex really finds the
      constitution's own reference, and the venue list really has entries.

Reads documents and code. Runs money_posture.py (read-only by contract).
Places nothing, opens no credential.
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# The documents that promise commands. A .bat is a document too: it is the
# one a non-technical successor double-clicks, and the one that carried on
# past the missing file without a word.
DOCS = [
    "README.md",
    "CONTRIBUTING.md",
    os.path.join("docs", "CONSTITUTION.md"),
    os.path.join("docs", "GOVERNANCE.md"),
    os.path.join("docs", "SUCCESSION.md"),
    "SAFEGUARD.bat",
    "GO.bat",
]

# Where a bare `python X.py` may resolve, in order. Root first. The memory
# store is its own package with its own main.py, and SUCCESSION.md promises
# `python main.py verify` from inside it. Anything that needs a THIRD entry
# here is a document that should say where it means.
SEARCH = ["", "ai_memory_system"]

# The documents that make the money claim, and therefore must name every
# adapter. money_posture.py is included on purpose: it is a document that
# happens to be executable, and it was the one that was wrong first.
MONEY_DOCS = [
    "README.md",
    os.path.join("docs", "CONSTITUTION.md"),
    os.path.join("docs", "GOVERNANCE.md"),
    "money_posture.py",
]

results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print(f"{'ok  ' if ok else 'FAIL'}  {label}"
          f"{'' if ok else '  ' + str(detail)[:200]}", flush=True)


def read(rel):
    try:
        with open(os.path.join(HERE, rel), "r", encoding="utf-8",
                  errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def norm(t):
    t = t.replace("—", "-").replace("–", "-").replace("’", "'")
    return re.sub(r"\s+", " ", t).lower()


PROMISE = re.compile(r'(?:python|"%PY%")\s+([A-Za-z0-9_][A-Za-z0-9_.-]*\.py)\b')


def promised(rel):
    """Every script a document tells someone to run, with the line it is on."""
    out = []
    for n, line in enumerate(read(rel).splitlines(), 1):
        for m in PROMISE.finditer(line):
            out.append((m.group(1), n))
    return out


def resolve(name):
    for d in SEARCH:
        p = os.path.join(HERE, d, name)
        if os.path.isfile(p):
            return p, d or "."
    return None, None


# ---- the money claim, asked from the CODE side and from the missing hedge ---
# WHY THESE EXIST, added 2026-09-09. The D over-claim tripwire below (the
# `universal` regex) is one literal phrasing, and nothing proved it could ever
# match. A mutation that rewrote README.md's money paragraph to "All orders it
# builds reach the venue's own dry-run endpoint and are priced and rejected
# without booking" -- a false universal safety claim about order placement, in
# the money paragraph of a public README -- left G2 at 64/64, exit 0, and the
# very check whose label reads "does not promise a venue-side dry run of
# 'every order'" printed ok. "All orders" is not "every order".
#
# Worse: the sentence this file's own docstring names as the reason it exists
# -- "both default to the venue's own dry-run endpoint", 2026-09-02 -- contains
# no "every order" at all, so the tripwire named after the bug could never have
# seen the bug. Four of G2's 64 checks were green because a phrase happened to
# be absent from the corpus, not because any document had been compared with
# the code. The E section carries M1/M2 as controls and says out loud what it
# means if they fail; the D section had none.
#
# So the two predicates below ask it the other way round. D2b reads venues.py
# at run time and requires the DISCLOSURE to be present; D3b requires the
# scoping HEDGE to be present. Both fail on an absence, which is the shape the
# defect actually had, and M3/M4/M5 run them on prose with a known answer so
# neither can go quietly vacuous the way the regex did.

# The weaker guarantee, however a document phrases it. Every money document
# today writes it within ~130 characters of the adapter's own name.
LOCAL_DISCLOSURE = re.compile(
    r"dry[- ]run (?:is |= )?local|local only|no (?:preview|such) endpoint"
    r"|no venue[- ]side dry run|venue_validated: false")

# A universal quantifier over ORDERS, the endpoint nouns a person would
# actually write, and the scoping qualifier the shipped documents all carry.
UNIVERSAL = re.compile(r"\b(?:every|all|each)\s+orders?\b")
ENDPOINT = re.compile(
    r"venues?'?s? own (?:dry[- ]run|preview|validation) endpoint"
    r"|(?:venue|server|exchange)[- ]side (?:dry run|dry-run|preview|validation)"
    r"|(?:dry[- ]run|preview|validation) endpoint"
    r"|/orders/preview|validate=true")
HEDGE = re.compile(
    r"where (?:the|a) venue|where it does not|where one exists|where offered"
    r"|(?:if|when) the venue|venues? that (?:offer|publish|have)"
    r"|some orders|not all|not every|except")

# Fixtures for M3/M4/M5. Written from the mutation and from the 2026-09-02
# defect, NOT copied out of the documents being checked -- a control copied
# from the artifact under test is empty by construction.
OVERCLAIMS = [
    "all orders it builds reach the venue's own dry-run endpoint and are "
    "priced and rejected without booking.",
    "every order it builds is sent to the venue's own dry-run endpoint and is "
    "rejected without booking.",
    "each order is validated against the venue's own preview endpoint before "
    "anything is placed.",
    "the trader is armed. all orders are priced and rejected by the venue's "
    "own dry-run endpoint. it is bounded by a halt file and a $25 cap.",
]
SCOPED = [
    "where a venue publishes one, every order is sent to its own dry-run "
    "endpoint; where none exists the check is local.",
    "for the two venues that offer it, every order reaches the preview "
    "endpoint. where it does not, the dry run is local.",
    "a venue-side dry run is true of some orders only; a document saying "
    "every order reaches one is out of date.",
]


def discloses_local(doc, venue):
    """True if `doc` says, near the adapter's OWN NAME, that its dry run does
    not reach the venue. A window rather than a sentence, because the
    documents write it as "Robinhood publishes no preview endpoint, so its dry
    run is local only". Naming the adapter somewhere else in the file is not
    disclosure: naming three and describing one guarantee is exactly what the
    2026-09-02 documents did."""
    for m in re.finditer(re.escape(venue), doc):
        if LOCAL_DISCLOSURE.search(doc[max(0, m.start() - 60):m.start() + 260]):
            return True
    return False


def overclaims(text):
    """The sentences that promise a venue-side dry run for EVERY order with no
    scoping qualifier in them or in either neighbour. Returns the offending
    sentences, so a failure prints the prose rather than a boolean. This flags
    the ABSENCE of the qualifier; the regex in the D section flags the
    presence of one exact phrase, which is why it missed the mutant."""
    sents = re.split(r"(?<=[.!?])\s+", text)
    bad = []
    for i, s in enumerate(sents):
        u = UNIVERSAL.search(s)
        if not u:
            continue
        e = ENDPOINT.search(s)
        if not e or abs(e.start() - u.start()) > 200:
            continue
        if HEDGE.search(" ".join(sents[max(0, i - 1):i + 2])):
            continue
        bad.append(s[:200])
    return bad


def main():
    print("G2 -- a document that promises a command must be able to run it\n")

    # ---- E: promised commands exist and compile -----------------------------
    seen = {}
    for rel in DOCS:
        if not read(rel):
            # GO.bat is optional; the rest are not.
            check(f"E0 {rel} is readable", rel == "GO.bat", "missing")
            continue
        for name, line in promised(rel):
            seen.setdefault(name, []).append(f"{rel}:{line}")
    check("E1 the documents promise at least one command (else E* is vacuous)",
          len(seen) >= 5, sorted(seen))
    for name in sorted(seen):
        path, where = resolve(name)
        refs = ", ".join(seen[name][:4])
        check(f"E:{name:<28} exists -- promised at {refs}",
              path is not None, f"searched {SEARCH}")
        if path is None:
            continue
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                compile(fh.read(), path, "exec")
            ok, why = True, ""
        except SyntaxError as e:
            ok, why = False, f"{e.__class__.__name__}: {e}"
        check(f"E:{name:<28} compiles (found in {where})", ok, why)

    # ---- M: the regex is not vacuous ---------------------------------------
    const_refs = [n for n, _ in promised(os.path.join("docs", "CONSTITUTION.md"))]
    check("M1 the regex finds money_posture.py in CONSTITUTION.md II.1 -- the "
          "reference this test was written for. If it cannot, E* passed on "
          "nothing", "money_posture.py" in const_refs, const_refs)
    check("M2 SAFEGUARD.bat step 7's \"%PY%\" money_posture.py is found too, so "
          "the .bat form of a promise is covered",
          "money_posture.py" in [n for n, _ in promised("SAFEGUARD.bat")])

    # ---- R: the named checker runs and can determine the posture -----------
    mp = os.path.join(HERE, "money_posture.py")
    rc, out = None, ""
    if os.path.isfile(mp):
        try:
            p = subprocess.run([sys.executable, mp], capture_output=True,
                               text=True, timeout=90, cwd=HERE)
            rc, out = p.returncode, (p.stdout or "") + (p.stderr or "")
        except Exception as e:                               # noqa: BLE001
            out = str(e)
    check("R1 money_posture.py runs to completion", rc is not None, out[-200:])
    check("R2 ...and DETERMINES the posture: exit 0 (disarmed) or 1 (armed). "
          "Exit 2 is 'could not determine', and four documents pointing a "
          "reader at a checker that cannot see is the failure G2 exists for",
          rc in (0, 1), f"rc={rc}")
    check("R3 ...and prints the one line a reader is told to look for",
          "DISARMED" in out or "ARMED" in out, out[-300:])

    # ---- D: money documents describe the code that exists ------------------
    try:
        import venues as V                                   # noqa: N812
        vs = list(V.all_venues())
        names = [v.name.lower() for v in vs]
        modes = {v.name: getattr(v, "DRY_RUN", None) for v in vs}
    except Exception as e:                                   # noqa: BLE001
        vs, names, modes = [], [], {}
        check("D0 venues.py imports", False, str(e))
    check("D0 venues.py holds at least three adapters (M: not vacuous)",
          len(vs) >= 3, names)
    weakest = "local" if "local" in modes.values() else "venue"
    local_names = [v.name.lower() for v in vs
                   if getattr(v, "DRY_RUN", None) == "local"]
    check("D1 every adapter declares what its dry run reaches (DRY_RUN in "
          "{venue, local}) -- an adapter that declares nothing gets no "
          "adjective from any document",
          vs and all(m in ("venue", "local") for m in modes.values()), modes)

    universal = re.compile(r"every order[^.]{0,120}venue'?s own dry-run endpoint")
    for rel in MONEY_DOCS:
        doc = norm(read(rel))
        missing = [n for n in names if n not in doc]
        check(f"D:{rel:<24} names every adapter venues.py holds",
              doc and not missing, f"missing {missing}")
        m = universal.search(doc)
        check(f"D:{rel:<24} does not promise a venue-side dry run of 'every "
              f"order' while the weakest adapter's dry run is {weakest}",
              not (m and weakest == "local"),
              (m.group(0)[:100] if m else ""))
        # D2b -- the same claim from the code side. venues.py is read at run
        # time; every adapter it holds whose DRY_RUN is "local" must be
        # disclosed as local, BY NAME, in this document. It fails on an ABSENT
        # disclosure, so no rewording of the promise evades it, and it is the
        # arm that would have caught the 2026-09-02 sentence ("both default to
        # the venue's own dry-run endpoint") that the phrase-tripwire above
        # cannot see. If venues.py ever holds no local adapter this requires
        # nothing -- and at that point the universal claim would be true.
        undisclosed = [v for v in local_names if not discloses_local(doc, v)]
        check(f"D2b:{rel:<22} discloses by name the weaker dry run of every "
              f"adapter venues.py declares LOCAL {local_names}",
              bool(doc) and not undisclosed, f"undisclosed {undisclosed}")
        # D3b -- the missing hedge. Every money document today scopes the
        # promise ("Where the venue offers a server-side dry run ...").
        over = overclaims(doc)
        check(f"D3b:{rel:<22} makes no UNSCOPED universal claim -- an "
              f"every/all/each-order promise of a venue-side endpoint with no "
              f"qualifier in that sentence or its neighbours",
              bool(doc) and not (over and weakest == "local"), over[:2])

    # ---- M: the two new D predicates are not vacuous -----------------------
    # The D section had no control at all, which is how the tripwire above sat
    # green on an absent phrase. These run the predicates on prose whose
    # answer is known, so "D2b/D3b passed" can never again mean "D2b/D3b
    # cannot fire".
    missed = [s[:60] for s in OVERCLAIMS if not overclaims(s)]
    check("M3 the unscoped-claim detector fires on real over-claims, "
          "including the exact sentence the mutation put in README.md. If it "
          "cannot, D3b* passed on nothing", not missed, missed)
    flagged = [s[:60] for s in SCOPED if overclaims(s)]
    check("M4 ...and does NOT fire on the scoped form the documents actually "
          "use, so a future widening that refuses everything is caught here "
          "rather than by deleting D3b*", not flagged, flagged)
    check("M5 discloses_local() tells naming an adapter apart from disclosing "
          "it -- the 2026-09-02 documents named the venues and described one "
          "guarantee. If it cannot, D2b* passed on nothing",
          not discloses_local(norm("venues.py holds Kraken, Coinbase and "
                                   "Robinhood order adapters."), "robinhood")
          and discloses_local(norm("Robinhood publishes no preview endpoint, "
                                   "so its dry run is local only."),
                              "robinhood"))

    n, ok = len(results), sum(results)
    print(f"\nG2: {ok}/{n} passed")
    return 0 if ok == n else 1


if __name__ == "__main__":
    raise SystemExit(main())
