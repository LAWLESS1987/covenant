#!/usr/bin/env python3
"""
federation.py -- ask other instances whether we still mean the same thing.

DELIBERATELY OUTSIDE THE CORE

  Nothing in the core depends on this file. Delete it and `refutable.py`,
  `constitution.py` and the ledger all behave identically. That is a design
  requirement, not an accident: a core that needed the federation would be a
  core that needed other people's servers to be reachable, and an instance
  under sanctions, behind a firewall, or simply offline would stop working.

  Federation is a thing you may do. It is never a thing you must do.

WHAT IT IS

  Not a registry. Not a membership list. Not a standard anyone administers.

  Every instance publishes a constitution hash -- one number over the rules
  that bind its operator. This reads other instances' published hashes and
  reports, block by block, whether they still carry the same core rules or have
  amended them, and which.

  That is all it does. It confers no status, grants no permission, and cannot
  remove anyone from anything, because there is nothing to be removed from.

WHY DIVERGENCE IS REPORTED AND NEVER PUNISHED

  A federation that expels members for diverging is a hierarchy wearing a
  federation's clothes, and whoever decides what counts as divergence is simply
  in charge. This has no such office and no way to create one.

  An instance that amends the core is not defective. It may have found
  something the original got wrong -- that is the single most valuable thing a
  fork can do, and the whole record is built to keep refutations rather than
  argue them away. What matters is only that the amendment is VISIBLE, so that
  anyone relying on a shared rule can see it is no longer shared.

  So the output is descriptive. `SAME`, `AMENDED`, `MISSING`, `UNREACHABLE`.
  No verdict, no score, no compliance rating. Those would each be a lever, and
  a lever is a thing somebody eventually pulls.

WHY FORKS AND NOT BRANCHES

  A branch in someone's repository is that person's property; they can rewrite
  or delete it. A fork lives on an account they do not control. Only the second
  is sovereignty, and sovereignty is the point: the constitution names "a second
  independent operator" as the largest missing precondition for governance.
  Every genuine fork is one.

PEERS

  A plain text file, one entry per line, `name<space>url-or-path`. Yours. No
  one approves it and no one can add to it. Comments start with #.

      # peers.txt
      upstream  https://raw.githubusercontent.com/LAWLESS1987/covenant/main/docs/CONSTITUTION_ANCHOR.json
      local     docs/CONSTITUTION_ANCHOR.json

USE
  python federation.py check                # read ./peers.txt
  python federation.py check other.txt
  python federation.py mine                 # print this instance's hash to publish

LICENCE: public domain, like the rest of the shareable layer.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Dict, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PEERS = os.path.join(HERE, "peers.txt")
TIMEOUT = 15


def _conformance():
    """This instance's behaviour root, or None if it cannot be computed.

    Never fatal: an instance that cannot run the vectors still has a
    constitution hash, and losing the older check to gain the newer one would
    be a bad trade.
    """
    try:
        import conformance
        rs = conformance.run_vectors()
        if any(r["error"] for r in rs):
            return None
        return {"root": conformance.conformance_root(rs), "vectors": len(rs),
                "spec": conformance.SPEC_VERSION}
    except Exception:                                        # noqa: BLE001
        return None


def _local_anchor() -> Optional[Dict[str, object]]:
    sys.path.insert(0, HERE)
    try:
        import constitution                                  # noqa: WPS433
        return constitution.constitution_hash()
    except Exception:                                        # noqa: BLE001
        return None


def _fetch(where: str) -> Tuple[Optional[Dict[str, object]], str]:
    """Anchor from a URL or a path. Returns (anchor, error)."""
    try:
        if where.startswith(("http://", "https://")):
            req = urllib.request.Request(
                where, headers={"User-Agent": "covenant-federation/1"})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return json.loads(r.read().decode("utf-8")), ""
        path = where if os.path.isabs(where) else os.path.join(HERE, where)
        with open(path, encoding="utf-8") as f:
            return json.load(f), ""
    except urllib.error.HTTPError as e:
        return None, "HTTP %s" % e.code
    except Exception as e:                                   # noqa: BLE001
        return None, "%s: %s" % (type(e).__name__, str(e)[:60])


def read_peers(path: str) -> List[Tuple[str, str]]:
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(None, 1)
            if len(parts) == 2:
                out.append((parts[0], parts[1]))
    return out


def compare(mine: Dict[str, object], theirs: Dict[str, object]) -> List[str]:
    """Block-by-block. Descriptive only."""
    m = {d["opens"]: d["digest"] for d in mine.get("detail", [])}
    t = {d["opens"]: d["digest"] for d in theirs.get("detail", [])}
    rows = []
    for opens in sorted(set(m) | set(t)):
        if opens in m and opens in t:
            rows.append(("SAME" if m[opens] == t[opens] else "AMENDED", opens))
        elif opens in m:
            rows.append(("MISSING", opens))
        else:
            rows.append(("ADDED", opens))
    return rows


def cmd_mine() -> int:
    r = _local_anchor()
    if not r:
        print("  cannot compute a local hash; is constitution.py present?")
        return 2
    print("  hash   : %s" % r["hash"])
    print("  blocks : %d" % r["blocks"])
    cr = _conformance()
    if cr:
        print("  behave : %s  (%d vectors)" % (cr["root"], cr["vectors"]))
        print()
        print("  Publish BOTH. The hash says your rules read the same; the")
        print("  behaviour root says your code DOES the same. A fork in another")
        print("  language will differ on the first and can still match the")
        print("  second, and that combination is the whole point of forking.")
    print()
    print("  Publish docs/CONSTITUTION_ANCHOR.json somewhere fetchable and")
    print("  give anyone the raw URL. That is the whole of joining, and there")
    print("  is nobody to ask.")
    return 0


def cmd_check(peers_path: str) -> int:
    mine = _local_anchor()
    if not mine:
        print("  cannot compute a local hash; is constitution.py present?")
        return 2
    peers = read_peers(peers_path)
    print("  this instance : %s" % mine["hash"])
    print("  peers file    : %s" % peers_path)
    if not peers:
        print()
        print("  No peers listed. That is a normal state, not an error: an")
        print("  instance with no peers is complete on its own.")
        return 0
    print()
    same = diverged = unreachable = conformant = 0
    for name, where in peers:
        anchor, err = _fetch(where)
        if anchor is None:
            print("  %-12s UNREACHABLE  (%s)" % (name, err))
            print("               An unreachable peer is a fact about the network,")
            print("               not about them. It says nothing about their rules.")
            unreachable += 1
            continue
        if anchor.get("hash") == mine["hash"]:
            print("  %-12s SAME CORE    %s" % (name, anchor["hash"][:16]))
            same += 1
            continue
        # TEXT DIFFERS. Before calling that divergence, ask whether they
        # BEHAVE the same -- a faithful reimplementation, or the same rules in
        # another language, differs here and is not diverged in any sense that
        # matters. Comparing artefacts instead of computations is the mistake
        # the Neuromorphic Intermediate Representation exists to fix in its own
        # field, and it was this file's mistake too.
        mine_c = _conformance()
        theirs_c = anchor.get("conformance") or {}
        if (mine_c and theirs_c.get("root")
                and theirs_c["root"] == mine_c["root"]):
            print("  %-12s CONFORMANT   behaviour %s (%d vectors)"
                  % (name, mine_c["root"][:16], mine_c["vectors"]))
            print("               Their rules are WORDED differently and their")
            print("               code answers every vector as ours does. That is")
            print("               a sovereign fork, not a divergence.")
            conformant += 1
            continue
        diverged += 1
        print("  %-12s DIVERGED     %s" % (name, str(anchor.get("hash"))[:16]))
        if mine_c and theirs_c.get("root"):
            print("               behaviour differs too: %s vs ours %s"
                  % (str(theirs_c["root"])[:16], mine_c["root"][:16]))
        elif mine_c and not theirs_c:
            print("               they publish no behaviour root, so whether")
            print("               they COMPUTE the same is unknown -- which is")
            print("               not the same as knowing they do not.")
        for mark, opens in compare(mine, anchor):
            if mark != "SAME":
                print("               %-8s %s" % (mark, opens[:56]))
    print()
    print("  %d sharing the core, %d conformant, %d diverged, %d unreachable."
          % (same, conformant, diverged, unreachable))
    print()
    print("  Diverged is not a failing grade. An instance that amended a rule")
    print("  may have found something this one got wrong, and that is the most")
    print("  useful thing a fork can do. What matters is that you can see it.")
    return 0


def main() -> int:
    args = sys.argv[1:]
    cmd = args[0] if args else "check"
    if cmd == "mine":
        return cmd_mine()
    if cmd == "check":
        return cmd_check(args[1] if len(args) > 1 else DEFAULT_PEERS)
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
