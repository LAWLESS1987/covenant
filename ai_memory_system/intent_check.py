#!/usr/bin/env python3
"""intent_check.py -- read any record's intent provenance, verbatim, plus one
line on whether that intent is still satisfiable given the current ledger state.

    python intent_check.py <memory-root> <name>        # JSON to stdout
    from intent_check import intent_check               # -> dict

WHAT IT DOES, AND WHAT IT DELIBERATELY DOES NOT. Any agent can call this on any
record. It returns the three provenance fields (intent, beneficiary, divergence)
and the diverges_from cross-link EXACTLY as stored -- no rewriting, no
summarizing, no paraphrase, because paraphrase is where a claim quietly changes.
On top of the raw fields it adds ONE derived thing: a boolean `satisfiable` and a
single-line `assessment`, computed from the current ledger, not from the record's
own words.

SATISFIABILITY is a structural question, not a semantic one (and that limit is
stated, not hidden): an intent is called UNSATISFIABLE when the ledger can no
longer let it hold --

  * the record is not in the ledger (missing or tombstoned): nothing to satisfy;
  * the record has been superseded (`superseded_by`): its intent to stand as the
    current word on its subject is no longer met -- the superseding record now
    holds that ground;
  * it declares a divergence (`divergence` != "none") but the record it diverges
    from (`diverges_from`) is gone: the conflict chain is broken, so the
    divergence can no longer be checked against what it named.

Otherwise it is called satisfiable. This never asserts an intent is BEING served
-- only that the ledger has not structurally foreclosed it. Judging whether the
record actually causes what its intent names is a reader's job, not this flag's.

READ-ONLY. It parses files and never writes, never touches use counters, never
constructs the gate -- calling it on a record has no effect on the record.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, Optional

from memory_store import parse_memory, PROVENANCE_FIELDS


def _read(root: str, name: str) -> Optional[Dict[str, Any]]:
    path = os.path.join(root, f"{name}.md")
    try:
        with open(path, encoding="utf-8") as fh:
            return parse_memory(fh.read())
    except (OSError, ValueError):
        return None


def intent_check(root: str, name: str) -> Dict[str, Any]:
    """Return {name, intent, beneficiary, divergence, diverges_from,
    satisfiable, assessment}. Fields are verbatim from the record; satisfiable
    and assessment are derived from the current ledger state in `root`."""
    rec = _read(root, name)
    if rec is None:
        return {"name": name, "intent": None, "beneficiary": None,
                "divergence": None, "diverges_from": None,
                "satisfiable": False,
                "assessment": "UNSATISFIABLE: record is not in the ledger "
                              "(missing or tombstoned)"}
    meta = rec.get("metadata") or {}
    intent = meta.get("intent")
    beneficiary = meta.get("beneficiary")
    divergence = meta.get("divergence")
    diverges_from = meta.get("diverges_from")
    superseded_by = meta.get("superseded_by")

    # A record written before the schema carries none of the fields. That is a
    # real, separate state -- say so rather than call it satisfiable.
    if any(not str(meta.get(k) or "").strip() for k in PROVENANCE_FIELDS):
        return {"name": name, "intent": intent, "beneficiary": beneficiary,
                "divergence": divergence, "diverges_from": diverges_from,
                "satisfiable": False,
                "assessment": "UNSATISFIABLE: record predates intent provenance "
                              "(no intent/beneficiary/divergence recorded)"}

    reasons = []
    if str(superseded_by or "").strip():
        reasons.append(f"superseded by {superseded_by!r}")
    if str(divergence).strip().lower() != "none":
        if not str(diverges_from or "").strip():
            reasons.append("declares a divergence but names no diverges_from record")
        elif _read(root, str(diverges_from).strip()) is None:
            reasons.append(f"diverges_from {diverges_from!r} is gone from the ledger")

    satisfiable = not reasons
    if satisfiable:
        assessment = ("satisfiable: record stands, not superseded"
                      + ("; divergence cross-link intact"
                         if str(divergence).strip().lower() != "none"
                         else "; declares no divergence"))
    else:
        assessment = "UNSATISFIABLE: " + "; ".join(reasons)

    return {"name": name, "intent": intent, "beneficiary": beneficiary,
            "divergence": divergence, "diverges_from": diverges_from,
            "satisfiable": satisfiable, "assessment": assessment}


def main(argv: Optional[list] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 2:
        sys.stderr.write("usage: intent_check.py <memory-root> <name>\n")
        return 2
    root, name = argv
    print(json.dumps(intent_check(root, name), indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
