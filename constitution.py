#!/usr/bin/env python3
"""
constitution.py -- make the rules that bind the operator tamper-evident.

THE PROBLEM THIS EXISTS FOR

  This project already declares constraints it says cannot be changed:
  IMPROVEMENT_LOG.md section 0 states it "may never be edited, weakened,
  reinterpreted, or moved -- by any run, for any reason, including a reason
  that seems excellent at the time." CONTRIBUTING.md has "What never changes."

  Both are prose asserting their own immutability, which is the weakest form a
  constraint can take. Nothing computes anything. An operator who edited either
  one at 3am would find no mechanism that noticed, and the file would go on
  claiming it had never been edited.

  That is the gap between governing TRANSACTIONS and governing POWER. The
  ethics gate binds what flows through the system. Until now, nothing bound the
  person who ships the ethics gate.

WHAT THIS DOES, AND THE LIMIT IT ACCEPTS

  It cannot stop a sole operator from amending their own rules. Nothing can.
  Anyone with the disk can edit any file, and if they also control every node,
  they can rewrite the ledger that recorded the edit.

  What it CAN do is make amendment impossible to perform INVISIBLY. It hashes
  the protected text, commits that hash publicly, and reports any divergence
  from the committed value. After that, changing a rule is still possible and
  is no longer deniable -- and the difference between "cannot" and "cannot do
  so quietly" is most of what constitutional constraint has ever actually been.

  That is a real, achievable precondition for governance by one operator. It is
  not governance. See docs/CONSTITUTION.md for what is still missing and why
  the largest missing piece is a person rather than a program.

USE
  python constitution.py hash      # current hash of the protected text
  python constitution.py verify    # compare against the committed anchor
  python constitution.py show      # print exactly what is protected

LICENCE: public domain, like refutable.py. Take it.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from typing import Dict, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
ANCHOR = os.path.join(HERE, "docs", "CONSTITUTION_ANCHOR.json")

# The protected text. Each entry names a file and the heading that opens the
# protected block; the block runs to the next heading of the same level, or to
# end of file. Adding an entry here widens what is bound. REMOVING one narrows
# it, which is itself an amendment and will show up as a hash change.
PROTECTED: List[Dict[str, str]] = [
    {
        "file": "CONTRIBUTING.md",
        "opens": "## Why it exists, and the one condition",
        "why": "the condition every contribution must satisfy",
    },
    {
        "file": "CONTRIBUTING.md",
        "opens": "## What never changes",
        "why": "the prohibitions the project declares permanent",
    },
    {
        "file": "docs/SUCCESSION.md",
        "opens": "## Layer 4 - Continuation, not just preservation",
        "why": "the reasoning rules a successor inherits",
    },
]


def _norm(text: str) -> str:
    """Canonical form: line endings and trailing whitespace normalised so that
    a checkout on another platform produces the same hash. Content only."""
    lines = [ln.rstrip() for ln in text.replace("\r\n", "\n").split("\n")]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def _extract(path: str, opens: str) -> Optional[str]:
    """The block beginning at `opens`, ending before the next heading of the
    same depth. Returns None if the heading is absent -- which is itself a
    finding, not an error to swallow."""
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        text = f.read().replace("\r\n", "\n")
    # Tolerate en/em dashes differing from the plain hyphen in the marker.
    variants = [opens, opens.replace(" - ", " — "), opens.replace(" - ", " – ")]
    start = -1
    for v in variants:
        start = text.find(v)
        if start != -1:
            break
    if start == -1:
        return None
    depth = len(opens) - len(opens.lstrip("#"))
    rest = text[start + len(opens):]
    end = len(rest)
    for i, line in enumerate(rest.split("\n")):
        if i == 0:
            continue
        stripped = line.lstrip()
        if stripped.startswith("#"):
            d = len(stripped) - len(stripped.lstrip("#"))
            if d <= depth:
                end = rest.find(line)
                break
    return _norm(opens + rest[:end])


def collect() -> Tuple[List[Dict[str, object]], List[str]]:
    blocks, missing = [], []
    for spec in PROTECTED:
        path = os.path.join(HERE, spec["file"].replace("/", os.sep))
        body = _extract(path, spec["opens"])
        if body is None:
            missing.append("%s :: %s" % (spec["file"], spec["opens"]))
            continue
        blocks.append({
            "file": spec["file"],
            "opens": spec["opens"],
            "why": spec["why"],
            "chars": len(body),
            "digest": hashlib.sha256(body.encode("utf-8")).hexdigest(),
            "body": body,
        })
    return blocks, missing


def constitution_hash() -> Dict[str, object]:
    """One hash over every protected block, order-independent so that moving a
    section does not read as a change to what it says."""
    blocks, missing = collect()
    leaves = sorted(b["digest"] for b in blocks)
    h = hashlib.sha256()
    h.update(b"covenant-constitution-v1")
    for leaf in leaves:
        h.update(leaf.encode())
    return {
        "hash": h.hexdigest(),
        "blocks": len(blocks),
        "missing": missing,
        "detail": [{k: b[k] for k in ("file", "opens", "chars", "digest")}
                   for b in blocks],
    }


def cmd_hash() -> int:
    r = constitution_hash()
    print("  constitution hash : %s" % r["hash"])
    print("  protected blocks  : %d" % r["blocks"])
    for d in r["detail"]:
        print("    %-56s %s" % (d["opens"][:56], d["digest"][:16]))
    if r["missing"]:
        print("  MISSING (each is itself an amendment):")
        for m in r["missing"]:
            print("    %s" % m)
        return 1
    return 0


def cmd_verify() -> int:
    r = constitution_hash()
    if not os.path.exists(ANCHOR):
        print("  no anchor at docs/CONSTITUTION_ANCHOR.json")
        print("  current hash is %s" % r["hash"])
        print("  commit it there to start binding.")
        return 2
    with open(ANCHOR, encoding="utf-8") as f:
        anchored = json.load(f)
    want = anchored.get("hash", "")
    print("  anchored : %s  (%s)" % (want, anchored.get("at", "no date")))
    print("  current  : %s" % r["hash"])
    if r["missing"]:
        print()
        print("  A PROTECTED SECTION IS GONE. That is the most serious result")
        print("  this tool reports: not a rule changed, a rule removed.")
        for m in r["missing"]:
            print("    %s" % m)
        return 1
    if want == r["hash"]:
        print()
        print("  UNCHANGED. The rules that bind the operator are as anchored.")
        return 0
    print()
    print("  CHANGED. The constitution has been amended since the anchor.")
    print("  That is not forbidden and this tool cannot forbid it. It is")
    print("  recorded, which is the whole point. Compare block digests:")
    prev = {d["opens"]: d["digest"] for d in anchored.get("detail", [])}
    for d in r["detail"]:
        was = prev.get(d["opens"])
        mark = "same" if was == d["digest"] else ("AMENDED" if was else "NEW")
        print("    %-8s %s" % (mark, d["opens"][:64]))
    for opens in prev:
        if opens not in {d["opens"] for d in r["detail"]}:
            print("    %-8s %s" % ("REMOVED", opens[:64]))
    return 1


def cmd_show() -> int:
    blocks, missing = collect()
    for b in blocks:
        print("=" * 72)
        print("%s  (%s)" % (b["file"], b["why"]))
        print("=" * 72)
        print(b["body"])
        print()
    for m in missing:
        print("MISSING: %s" % m)
    return 1 if missing else 0


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "verify"
    if cmd == "hash":
        return cmd_hash()
    if cmd == "show":
        return cmd_show()
    if cmd == "verify":
        return cmd_verify()
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
