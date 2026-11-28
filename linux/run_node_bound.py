#!/usr/bin/env python3
"""linux/run_node_bound.py -- start ONE covenant node that listens on one chosen address, never on every interface,
and never under another node's identity. A500, for the Debian towers.

Why a wrapper: covenant_unified_v8.CovenantUnifiedMaster builds its peer listener with the class default host
"0.0.0.0" and run_node.py has no --host flag (#124: "the core has no loopback-only listener option"). On an office
network that is every machine on the LAN. This is the same runtime replacement TETSU's node D has used since
2026-10-31 (noded/run_node_d.py, outside this repository), without D's TETSU-only gates.

Refuses, before anything is imported or written:
  * COVENANT_BIND empty, 0.0.0.0 or :: (every interface);
  * an identity key that is byte-for-byte a production key: the founder key covenant_A.db.key, or the key of node
    A, B, C or D, looked for in this checkout and in ~/.covenant-keys. A tower that held one would sign as that node
    (and, for the founder key, as the key genesis minted to).

Everything after the script name is passed to run_node.py unchanged, e.g.
  COVENANT_BIND=100.x.y.z COVENANT_DB_PATH=nodeE_prod.db python3 linux/run_node_bound.py --port 5000 --node-id E \
      --genesis genesis.json --peers 100.a.b.c:5081
"""
import os
import runpy
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRODUCTION_KEYS = ("covenant_A.db.key", "nodeA_prod.db.key", "nodeB_prod.db.key", "nodeC_prod.db.key",
                   "nodeD_prod.db.key")
EVERY_INTERFACE = ("", "0.0.0.0", "::", "[::]")


def refusal(environ, repo=REPO, home=None):
    """Why this start must not happen, or None. Pure, so the tests drive it both ways."""
    bind = (environ.get("COVENANT_BIND") or "").strip()
    if bind in EVERY_INTERFACE:
        return "refusing to listen on every interface; set COVENANT_BIND to this machine's tailnet address"
    db = environ.get("COVENANT_DB_PATH") or ""
    if not db:
        return "COVENANT_DB_PATH is not set; the node's database (and its key, DB + '.key') must be named"
    own = db if os.path.isabs(db) else os.path.join(repo, db)
    own_key = own + ".key"
    if os.path.basename(own_key) in PRODUCTION_KEYS:
        return "%s is a production node's key name; a tower runs its own node id (E and up)" % os.path.basename(own_key)
    if os.path.exists(own_key):
        mine = open(own_key, "rb").read()
        home = home if home is not None else os.path.expanduser("~")
        for folder in (repo, os.path.join(home, ".covenant-keys")):
            for name in PRODUCTION_KEYS:
                other = os.path.join(folder, name)
                if os.path.isfile(other) and open(other, "rb").read() == mine:
                    return "this node's key is a copy of %s; a tower must have its own identity" % other
    return None


def main():
    why = refusal(os.environ)
    if why:
        sys.exit("run_node_bound: " + why)
    bind = os.environ["COVENANT_BIND"].strip()
    os.chdir(REPO)
    sys.path.insert(0, REPO)
    os.environ["COVENANT_API_HOST"] = bind
    import covenant_unified_v8 as cov  # noqa: E402

    init = cov.CovenantUnifiedMaster.__init__
    defaults = list(init.__defaults__)
    if defaults[0] != "0.0.0.0":
        sys.exit("run_node_bound: the core's host default changed (%r); re-check this wrapper" % (defaults[0],))
    defaults[0] = bind
    init.__defaults__ = tuple(defaults)
    print("[run_node_bound] bind=%s db=%s" % (bind, os.environ["COVENANT_DB_PATH"]), flush=True)
    sys.argv = [os.path.join(REPO, "run_node.py")] + sys.argv[1:]
    runpy.run_path(sys.argv[0], run_name="__main__")


if __name__ == "__main__":
    main()
