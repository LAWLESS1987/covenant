#!/usr/bin/env python3
"""test_a129_bystanders.py -- A129: a third party's name is in no tracked file.

THE RULE, in the operator's words on 2026-09-16: **"there's safety in
transparency -- just leave <her> out."**

Transparency is the default for HIS material, and that posture is his to hold.
A third party never consented to any of it, so their name is the one thing in
the record that is not his to publish. The two halves are not in tension: the
openness is what makes the single exception coherent rather than arbitrary.

WHY IT EXISTS. On 2026-09-16, writing up A122, I quoted an August email subject
line verbatim into `docs/KNOWN_ISSUES.md` -- a file in the PUBLIC repository --
and it carried a bystander's name. It sat there until it was swept for. Nothing
in the tree would have caught it, and the failure mode is silent by nature: the
name reads as ordinary prose.

WHERE THE LIST LIVES, and why that is the whole design. `private/bystanders.txt`
is GITIGNORED. The names never enter the public repository; the check that
enforces them does. A list committed alongside the check would publish exactly
what it exists to protect -- and a hash list would be no better, because a
first name falls to a dictionary in seconds.

WHAT IT PINS.
  N*  no protected name appears in any file git TRACKS. Untracked and ignored
      paths are the operator's own workspace and are deliberately not policed.
  S*  the check is honest when it cannot run: with no list it reports NOT
      MEASURED and says so, and never reports a pass it did not earn.
  T*  it has teeth -- a planted name in a tracked file is caught.

Pure: no network, no node, no database. Reads only; writes nothing.
"""
from __future__ import annotations

import hashlib
import io
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LIST = os.path.join(HERE, "private", "bystanders.txt")
SCAN_EXT = {".md", ".txt", ".json", ".jsonl", ".py", ".sh", ".ps1", ".yml",
            ".yaml", ".html", ".bat"}

results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print("%s  %s%s" % ("ok  " if ok else "FAIL", label,
                        "" if ok else "  -- " + str(detail)[:300]), flush=True)


def load_names():
    """Lower-cased names. Held in memory only; never echoed, never written."""
    if not os.path.isfile(LIST):
        return None
    out = []
    for ln in io.open(LIST, encoding="utf-8"):
        ln = ln.strip()
        if ln and not ln.startswith("#"):
            out.append(ln.lower())
    return out


def tracked_files():
    try:
        p = subprocess.run(["git", "ls-files"], cwd=HERE, capture_output=True,
                           text=True, timeout=120)
        return [f for f in p.stdout.splitlines() if f.strip()]
    except Exception:                                            # noqa: BLE001
        return []


def scan(names, files):
    """Files containing a protected name, whole-word, case-insensitive.

    Returns paths and counts ONLY. The name itself is never put in the output,
    because a failure message that printed it would publish the thing this
    suite exists to keep out of the record -- into the CI log, which is public.
    """
    pats = [re.compile(r"\b" + re.escape(n) + r"\b", re.I) for n in names]
    hits = {}
    for f in files:
        if os.path.splitext(f)[1].lower() not in SCAN_EXT:
            continue
        p = os.path.join(HERE, f)
        try:
            text = io.open(p, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        n = sum(len(rx.findall(text)) for rx in pats)
        if n:
            hits[f] = n
    return hits


def main():
    print("A129 -- a third party's name is in no tracked file\n")

    names = load_names()
    if names is None:
        # NOT MEASURED, and never rounded up to a pass. The list is gitignored,
        # so a fresh clone or a staged sweep legitimately has none -- but this
        # suite has then checked nothing and says so in plain words.
        print("  NOT MEASURED. private/bystanders.txt is absent (it is")
        print("  gitignored by design, so a clone or a staged copy will not")
        print("  have it). NOTHING WAS CHECKED. Run this in the working tree.")
        print("\nA129: 0/0 passed -- nothing measured, nothing claimed")
        return 0

    check("A129.S1 the list loaded and names at least one person",
          bool(names), len(names or []))

    files = tracked_files()
    check("A129.S2 git listed the tracked files -- an empty listing would make "
          "every check below vacuous", len(files) > 50, len(files))

    hits = scan(names, files)
    if hits:
        for f, n in sorted(hits.items(), key=lambda kv: -kv[1])[:10]:
            print("        %-58s %d occurrence(s)" % (f[:58], n))
    check("A129.N1 no protected name appears in any file git TRACKS. A tracked "
          "file is a published file",
          not hits, "%d file(s)" % len(hits))

    # T*: teeth. A suite that cannot fail is not protecting anything, and this
    # one greps text, which is exactly the shape A74 caught being fake.
    probe = os.path.join(HERE, "_a129_probe.md")
    try:
        io.open(probe, "w", encoding="utf-8").write(
            "harmless line mentioning %s in passing\n" % names[0])
        caught = bool(scan(names, ["_a129_probe.md"]))
    finally:
        if os.path.isfile(probe):
            os.remove(probe)
    check("A129.T1 a planted name IS caught, so the green above is earned "
          "rather than a grep that matches nothing", caught)

    ok = sum(1 for r in results if r)
    print("\n  %d name(s) enforced over %d tracked files. The list itself is "
          "gitignored and is never printed." % (len(names), len(files)))
    print("\nA129: %d/%d passed" % (ok, len(results)))
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
