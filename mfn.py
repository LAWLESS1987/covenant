#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""mfn.py -- measure this node's conduct against the two federation rules.

THE RULES IT MEASURES are in docs/FEDERATION_RULES.md, under the constitution's
protected text, so amending them changes the constitution hash and every peer
reading federation.py sees AMENDED:

  * MOST FAVOURED PEER -- any term extended to one peer is extended to every
    peer; an undeclared difference is a defect.
  * EXIT IS UNILATERAL -- no term may be written that survives a party's exit.

A TERM IS NOT AN OUTCOME, and this file would be wrong in a dangerous
direction if it confused them. MFN binds what is OFFERED. It does not bind
what a peer's own conduct produces under an equal rule. The update door's
futility bound (A147) refuses the phone and not the PC right now -- that is
not an unequal term, it is one rule offered to everyone, which the phone has
met and the PC has not. A version of this check that flagged it would be
demanding equal RESULTS, and a federation whose rules may never refuse anyone
cannot say no to anything. So this reads CONFIGURATION KEYED BY PEER, which is
where terms live, and deliberately not outcomes.

ENUMERATED BY DISCOVERY, NEVER BY RECALL (CLAUDE.md rule 2). The surfaces are
found by scanning ops/ for structures keyed by a peer's name, not by reading a
list somebody has to remember to extend. A hardcoded list cannot find the file
added after the list was written, which is exactly the file a recount exists to
catch -- and this project has already shipped that bug once, in a tool written
to fix it.

WHAT IT STRUCTURALLY CANNOT SEE, reported on every run rather than implied:
route-level permission lives in code, not configuration; the address-gated
routes (/m, /m/apk, /hwy/state) have no peer identity at all, they answer a
network range; and anything handed to a peer out of band leaves no trace here.
A clean result from this tool means NO ASYMMETRY IN THE SURFACES IT CAN READ,
which is a smaller claim than "MFN holds" and must never be quoted as the
larger one.

USE
    python mfn.py
    python mfn.py --json
    python mfn.py --residue phone      # what would survive that peer's exit
LICENCE: Apache-2.0.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROSTER = os.path.join(HERE, "ops", "daily_plan_signers.json")
EXCEPTIONS = os.path.join(HERE, "ops", "mfn_exceptions.json")
SCAN = ("ops/*.json",)

# Read but never treated as a per-peer term: the roster IS the peer list, so
# every peer appearing in it is not an asymmetry, it is the population.
ROSTER_REL = "ops/daily_plan_signers.json"

BLIND_SPOTS = (
    "route-level permission is in code, not configuration -- this reads files",
    "/m, /m/apk and /hwy/state gate on network address and carry no peer identity",
    "anything given to a peer out of band leaves no trace on this machine",
    "a peer this node has never registered is invisible: the roster is the population",
)


def peers():
    """The peer population: whoever holds a signing credential here.

    Empty is a real answer and is reported as UNDETERMINED by the callers --
    never as "no asymmetry found", which is what an empty loop would silently
    produce and is the fake-guard shape this project has paid for twice."""
    try:
        with open(ROSTER, encoding="utf-8") as fh:
            d = json.load(fh)
        return sorted(d) if isinstance(d, dict) else []
    except (OSError, ValueError):
        return []


def exceptions():
    """Declared, reasoned exceptions. An exception with no reason is not one.

    The rule says an asymmetry must be "written down as a named exception
    carrying its reason", so a reasonless entry is rejected here rather than
    honoured -- otherwise the escape hatch is wider than the rule."""
    try:
        with open(EXCEPTIONS, encoding="utf-8") as fh:
            d = json.load(fh)
    except (OSError, ValueError):
        return {}, []
    good, bad = {}, []
    for row in (d.get("exceptions") or []):
        term, why = str(row.get("term", "")), str(row.get("why", "")).strip()
        if term and len(why) >= 20:
            good[term] = row
        else:
            bad.append(row)
    return good, bad


def surfaces(root=None, scan=None, roster=None):
    """Every per-peer configuration surface found on disk, by content.

    A surface qualifies when a JSON object's top-level keys, or any nested
    object's keys, include a peer's name. That is the content test the rule
    needs: it finds ops/whatever_new.json the day somebody adds it.
    """
    root = root or HERE
    names = set(roster if roster is not None else peers())
    if not names:
        return {}
    found = {}
    for pat in (scan or SCAN):
        for path in sorted(glob.glob(os.path.join(root, pat))):
            rel = os.path.relpath(path, root).replace("\\", "/")
            try:
                with open(path, encoding="utf-8") as fh:
                    d = json.load(fh)
            except (OSError, ValueError):
                continue
            if not isinstance(d, dict):
                continue
            if set(d) & names:
                found[rel] = {p: (p in d) for p in sorted(names)}
                continue
            for k, v in d.items():
                if isinstance(v, dict) and set(v) & names:
                    found["%s::%s" % (rel, k)] = {p: (p in v) for p in sorted(names)}
    return found


def asymmetries(found=None, roster=None):
    """Terms held by some peers and not others, minus declared exceptions."""
    found = surfaces(roster=roster) if found is None else found
    exc, _bad = exceptions()
    out = []
    for term, held in sorted(found.items()):
        if term.split("::")[0] == ROSTER_REL:
            continue                      # the roster is the population, not a term
        have = sorted(p for p, v in held.items() if v)
        lack = sorted(p for p, v in held.items() if not v)
        if have and lack:
            out.append({"term": term, "held_by": have, "withheld_from": lack,
                        "declared": term in exc,
                        "why": exc.get(term, {}).get("why", "")})
    return out


def residue(peer, found=None, roster=None):
    """What would still name `peer` after they left.

    The exit rule says no term may survive a party's exit. This does not
    remove anything -- it reports what a removal would have to reach, which is
    the checkable half. Acting on it is the operator's."""
    found = surfaces(roster=roster) if found is None else found
    return sorted(t for t, held in found.items() if held.get(peer))


def report(roster=None):
    ps = peers() if roster is None else roster
    found = surfaces(roster=ps)
    exc, bad = exceptions()
    return {
        "peers": ps,
        "peer_count": len(ps),
        "surfaces": found,
        "asymmetries": asymmetries(found, ps),
        "undeclared": [a for a in asymmetries(found, ps) if not a["declared"]],
        "exceptions_declared": sorted(exc),
        "exceptions_rejected_no_reason": bad,
        "residue": {p: residue(p, found, ps) for p in ps},
        "blind_spots": list(BLIND_SPOTS),
        "verdict": _verdict(ps, asymmetries(found, ps), bad),
    }


def _verdict(ps, asym, bad):
    if len(ps) < 2:
        return ("UNDETERMINED: %d peer(s) registered. MFN is a statement about "
                "differences between peers and cannot be measured below two. "
                "This is not a pass." % len(ps))
    und = [a for a in asym if not a["declared"]]
    if bad:
        return "DEFECT: %d exception(s) declared with no reason -- an escape hatch wider than the rule" % len(bad)
    if und:
        return "DEFECT: %d undeclared asymmetr(y/ies): %s" % (len(und), ", ".join(a["term"] for a in und))
    return ("no asymmetry in the surfaces this can read (%d surface(s), %d peer(s)) "
            "-- which is smaller than 'MFN holds'; see blind_spots" % (len(surfaces(roster=ps)), len(ps)))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--residue", metavar="PEER")
    a = ap.parse_args(argv)
    r = report()
    if a.residue:
        print(json.dumps({"peer": a.residue, "residue": residue(a.residue)},
                         indent=1))
        return 0
    if a.json:
        print(json.dumps(r, indent=1))
        return 0
    print("peers        %s" % (", ".join(r["peers"]) or "(none registered)"))
    print("surfaces     %d per-peer configuration surface(s)" % len(r["surfaces"]))
    for t, held in sorted(r["surfaces"].items()):
        print("   %-44s %s" % (t, {p: ("yes" if v else "NO") for p, v in held.items()}))
    print("asymmetries  %d (%d undeclared)" % (len(r["asymmetries"]), len(r["undeclared"])))
    for x in r["asymmetries"]:
        print("   %-44s held by %s, withheld from %s%s"
              % (x["term"], x["held_by"], x["withheld_from"],
                 "" if not x["declared"] else "  [declared: %s]" % x["why"][:60]))
    print("exit residue")
    for p, rs in sorted(r["residue"].items()):
        print("   %-12s %s" % (p, ", ".join(rs) or "(nothing would survive their exit)"))
    print("\nCANNOT SEE -- a clean line above does not cover these:")
    for b in r["blind_spots"]:
        print("   - %s" % b)
    print("\n%s" % r["verdict"])
    return 0 if r["verdict"].startswith("no asymmetry") else 2


if __name__ == "__main__":
    raise SystemExit(main())
