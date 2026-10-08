#!/usr/bin/env python3
"""C4 (2026-09-18): a public claim resting on private evidence must say so.

WHERE THIS CAME FROM. The operator, on being told the private corpus stays
unpublished: *"Hiding stuff in a system based off honesty seems wrong."*

The objection dissolves on one distinction -- honesty is about the truthfulness
of CLAIMS, publication is about whose FACTS they are, and CONSTITUTION.md II.4
already handles the corpus honestly by publishing its fingerprint rather than
pretending it does not exist. But it leaves a real residue, and this is it:

    5 public documents cite `private/` as their evidence. Three of them said
    nothing about the reader being unable to open it.

That is the honesty failure his instinct found. Not the non-publication -- the
SILENCE ABOUT IT AT THE POINT OF THE CLAIM. A reader is handed a conclusion and
a citation they cannot follow, with nothing marking the difference. It collides
with II.6, "what is not checked is not claimed: every assertion is marked
observed, implemented, inferred, or hypothesised."

WHAT THIS CHECKS. Every published markdown file that cites `private/` must
either carry a caveat naming the limit, or be on DECLARED_ILLUSTRATIVE below.

WHY AN EXEMPTION LIST AT ALL, and why it is declared rather than pattern-matched:
`CLAUDE.md` mentions `private/*/catalog.csv` as an EXAMPLE of the difference
between data and prose. It rests no claim on the file. A checker that tried to
tell an illustration from a citation by reading the sentence around it would be
a checker that could be talked out of a finding -- the same conclusion reached
when the Sentinel-Witness spec's own ghost-citation check flagged a sentence
illustrating a bad tag. So the distinction is a human's, written down, one line
per file, and adding to it is visible in a diff.

  python test_c4_uncheckable_claims.py      reads only published documents
"""
from __future__ import annotations

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

#: Any reference to the unpublishable tree, including glob forms. The `*` is not
#: optional in this pattern: leaving it out is how the first count of these
#: documents came back 3 instead of 5.
CITE = re.compile(r"private/[\w./*-]+")

#: Phrases that admit the reader cannot follow the citation. Any one suffices --
#: this checks that the limit is STATED, not how it is worded.
CAVEAT = re.compile(r"unverifiable|cannot be (checked|verified|opened|followed)|"
                    r"reader cannot|not publishable|only its fingerprint|"
                    r"never published|not independently verifiable", re.I)

#: Files that MENTION the path without resting a claim on it. One line each,
#: with the reason, because an undeclared exemption is indistinguishable from an
#: oversight.
DECLARED_ILLUSTRATIVE = {
    "CLAUDE.md": "uses private/*/catalog.csv as an EXAMPLE of data versus prose "
                 "in the standing method; rests no finding on the file",
}

#: Walked, not listed (rule 2): a document added after this file was written is
#: exactly the one a check like this exists to catch.
SKIP_DIRS = {".git", "__pycache__", "node_modules", "private", "ops"}


def published_markdown(root=HERE):
    out = []
    for d, subdirs, names in os.walk(root):
        subdirs[:] = [s for s in subdirs if s not in SKIP_DIRS]
        # A267 (2026-10-06): .claude/worktrees/ holds whole second copies of the
        # tree at other commits, git-excluded. Run in the main folder with 7 of
        # them, this read 1354 .md files where the tree has 192, and reported
        # "52 citing" where the tree has 7 -- so one worktree holding an older,
        # uncaveated document would turn C4.2 red for a file that is not in the
        # tree. The shape R1 fixed for itself in bc13694; pruned the same way,
        # by PATH, not by name: the rest of .claude/ is tree and stays scanned.
        if os.path.relpath(d, root).replace(os.sep, "/") == ".claude":
            subdirs[:] = [s for s in subdirs if s != "worktrees"]
        for n in names:
            if n.endswith(".md"):
                out.append(os.path.relpath(os.path.join(d, n), root))
    return sorted(out)


def classify(root=HERE):
    """(citing, missing, exempt) over the published markdown under root."""
    citing, missing, exempt = [], [], []
    for rel in published_markdown(root):
        try:
            with open(os.path.join(root, rel), encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue
        hits = CITE.findall(text)
        if not hits:
            continue
        key = rel.replace("\\", "/")
        citing.append((key, len(hits)))
        if key in DECLARED_ILLUSTRATIVE or os.path.basename(key) in DECLARED_ILLUSTRATIVE:
            exempt.append(key)
        elif not CAVEAT.search(text):
            missing.append((key, len(hits)))
    return citing, missing, exempt


def worktree_probe():
    """A267, driven both ways on a scratch tree: the same uncaveated citation
    under .claude/worktrees/x/, under .claude/hooks/ and under docs/worktrees/.
    Only the first may be dropped -- the prune is by path, not by name."""
    import shutil
    import tempfile
    bare = "Counted in private/data/, the corpus is 133 files.\n"
    probes = {"wt": ".claude/worktrees/x/docs/PROBE.md",
              "hooks": ".claude/hooks/PROBE.md",
              "named": "docs/worktrees/PROBE.md"}
    tmp = tempfile.mkdtemp(prefix="c4_a267_")
    try:
        for p in probes.values():
            full = os.path.join(tmp, *p.split("/"))
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", encoding="utf-8") as fh:
                fh.write(bare)
        reachable = {os.path.relpath(os.path.join(d, n), tmp).replace(os.sep, "/")
                     for d, _s, ns in os.walk(tmp) for n in ns}
        flagged = {k for k, _n in classify(tmp)[1]}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return probes, reachable, flagged


def main():
    results = []

    def check(name, ok, detail=""):
        results.append((name, bool(ok), detail))
        print("%s  %s  %s" % ("PASS" if ok else "FAIL", name, str(detail)[:120]))

    citing, missing, exempt = classify()

    check("C4.1 the scan found published documents that cite the unpublishable "
          "corpus at all -- a zero here would mean the pattern is broken, not "
          "that the repository is clean",
          len(citing) > 0, "%d document(s) cite private/" % len(citing))

    check("C4.2 every public claim resting on private evidence SAYS the reader "
          "cannot check it (II.6), or is a declared illustration",
          not missing,
          missing if missing else "%d citing, %d caveated, %d declared illustrative"
          % (len(citing), len(citing) - len(exempt), len(exempt)))

    # Driven the other way: the caveat detector must be capable of failing, or
    # C4.2 passing means nothing.
    check("C4.3 ...and the caveat detector REFUSES text that makes the claim "
          "without the admission",
          not CAVEAT.search("Counted in private/data/, the corpus is 133 files.")
          and bool(CAVEAT.search("private/ is never published; only its fingerprint is.")),
          "a bare claim is not accepted; an admitted one is")

    check("C4.4 every declared illustration still EXISTS and still mentions the "
          "path -- an exemption for a file that no longer cites it is stale "
          "permission nobody withdrew",
          all(any(k == c or os.path.basename(c) == k for c, _n in citing)
              for k in DECLARED_ILLUSTRATIVE),
          sorted(DECLARED_ILLUSTRATIVE))

    probes, reachable, flagged = worktree_probe()
    check("C4.5 a worktree under .claude/worktrees/ is not the tree (A267): an "
          "uncaveated probe there is on the walk's path yet never counted, while "
          "the same probe under .claude/hooks/ and docs/worktrees/ is flagged",
          probes["wt"] in reachable and probes["wt"] not in flagged
          and probes["hooks"] in flagged and probes["named"] in flagged,
          "flagged: %s" % sorted(flagged))

    ok = sum(1 for _n, o, _d in results if o)
    print("\nC4: %d/%d passed" % (ok, len(results)))
    if missing:
        print("\nThese documents rest a claim on evidence a reader cannot open,")
        print("and do not say so. Add the limit, or declare the mention")
        print("illustrative in DECLARED_ILLUSTRATIVE with a reason:")
        for f, n in missing:
            print("  %-46s %d citation(s)" % (f, n))
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
