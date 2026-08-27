"""test_3node_config.py -- the production topology, checked in the files that ship.

`test_multinode_live.py` proves the CODE relays: three real processes, A<->B<->C
with C not a peer of A, a block mined on A reaching C through B, and a cold
fourth node catching up. That has been green since v8.19.

What nothing checked is that the CONFIGURATION asks for the shape the code was
proven on. Those are two claims, and this project's whole history is about the
gap between two claims that sound like one. The failure this closes is specific
and silent: `--peers` takes each peer's **P2P** port (API + 1) while `--port`
takes the API port. Point one at the other and both nodes boot, report healthy,
and never hear each other. `preflight_port_check` catches it at startup since
v8.15 -- but only on the machine, at boot, in a console nobody is reading.

So this reads the shipped files and asserts the arithmetic before anyone starts
anything:

  N1  three nodes, >= 20 apart, and no overlap across {N, N+1, N+11}
  N2  every --peers entry names a P2P port of a configured node, never an API
      port                                                     <- the footgun
  N3  the topology is a LINE, not a mesh: C is not a peer of A in either
      direction, so the relay path is exercised in production
  N4  the peer graph is connected -- no node is isolated
  N5  covenant_watchdog.py's NODES matches covenant_prod.bat exactly
  N6  launch_check, verify_deploy and dashboard_render all know all three
  N7  AB_RESTART_NODES.bat stops every configured API port
  N8  every node has its own database

N5 and N7 are cross-file drift checks and they are the ones worth having.
A22 alerts on any peer it did not expect, so a watchdog that disagrees with the
launcher is a guaranteed false alert every round -- and a permanently-firing
alert trains its reader to skim (M34). A port the restart script does not stop
keeps its listener, and the next start reports "node already up" and does
nothing -- which is P3, the mechanism by which this machine ran a source from
days ago while every restart reported success.

    python test_3node_config.py
"""
from __future__ import annotations

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__)) or "."
PROD = os.path.join(HERE, "covenant_prod.bat")
WATCHDOG = os.path.join(HERE, "covenant_watchdog.py")
RESTART = os.path.join(HERE, "AB_RESTART_NODES.bat")

_passed, _failed = 0, 0


def ok(tag, name, cond, detail=""):
    global _passed, _failed
    if cond:
        _passed += 1
        print(f"PASS  {tag} {name}  {detail}")
    else:
        _failed += 1
        print(f"FAIL  {tag} {name}  {detail}")


def read(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


# --------------------------------------------------------------- the parser
LAUNCH = re.compile(
    r"--port\s+(\d+)\s+--node-id\s+(\w+)\s+--genesis\s+(\S+)"
    r"(?:\s+--peers\s+([\d\.,:]+))?")
DBPATH = re.compile(r"set COVENANT_DB_PATH=(\S+?)&&")


def parse_prod():
    """The launcher is the source of truth: this reads the actual command lines
    that start the nodes, not a summary of them."""
    text = read(PROD)
    nodes = {}
    for line in text.splitlines():
        m = LAUNCH.search(line)
        if not m:
            continue
        api, nid, genesis, peers = m.group(1), m.group(2), m.group(3), m.group(4)
        d = DBPATH.search(line)
        nodes[nid] = {
            "api": int(api),
            "genesis": genesis,
            "peers": [] if not peers else [p for p in peers.split(",") if p],
            "db": d.group(1) if d else None,
        }
    return nodes


def parse_watchdog():
    text = read(WATCHDOG)
    block = text[text.index("NODES = ["):]
    block = block[:block.index("\n]") + 2]
    out = {}
    for m in re.finditer(
            r'\{"id":\s*"(\w+)",\s*"port":\s*(\d+),\s*"db":\s*"([^"]+)",'
            r'\s*"key":\s*"([^"]+)",\s*"peers":\s*"([^"]*)"\}', block):
        out[m.group(1)] = {"api": int(m.group(2)), "db": m.group(3),
                           "key": m.group(4),
                           "peers": [p for p in m.group(5).split(",") if p]}
    return out


def main():
    nodes = parse_prod()
    print(f"covenant_prod.bat starts {len(nodes)} node(s): "
          f"{ {k: v['api'] for k, v in sorted(nodes.items())} }\n")

    # -------------------------------------------------------------- N1 ports
    ok("N1a", "three nodes are configured", len(nodes) == 3,
       ", ".join(f"{k}:{v['api']}" for k, v in sorted(nodes.items())))
    span = {}
    for nid, n in nodes.items():
        span[nid] = [n["api"], n["api"] + 1, n["api"] + 11]
    flat = [p for v in span.values() for p in v]
    ok("N1b", "no port collision across API, P2P (+1) and bridge (+11)",
       len(set(flat)) == len(flat),
       "; ".join(f"{k}={v}" for k, v in sorted(span.items())))
    apis = sorted(n["api"] for n in nodes.values())
    gaps = [b - a for a, b in zip(apis, apis[1:])]
    ok("N1c", "nodes are at least 20 apart", all(g >= 20 for g in gaps),
       f"gaps {gaps}")

    # ------------------------------------------------------------- N2 the P2P
    p2p_of = {n["api"] + 1: nid for nid, n in nodes.items()}
    api_of = {n["api"]: nid for nid, n in nodes.items()}
    bad, good = [], []
    for nid, n in sorted(nodes.items()):
        for peer in n["peers"]:
            port = int(peer.rsplit(":", 1)[1])
            if port in p2p_of:
                good.append(f"{nid}->{p2p_of[port]}")
            elif port in api_of:
                bad.append(f"{nid} points at {api_of[port]}'s API port {port}, "
                           f"not its P2P port {port + 1}")
            else:
                bad.append(f"{nid} points at {port}, which is no configured "
                           f"node's P2P port")
    ok("N2", "every --peers entry is a configured node's P2P port (API+1)",
       not bad, "; ".join(bad) if bad else " ".join(good))

    # ------------------------------------------------------------ N3/N4 shape
    edges = set()
    for nid, n in nodes.items():
        for peer in n["peers"]:
            port = int(peer.rsplit(":", 1)[1])
            if port in p2p_of:
                edges.add((nid, p2p_of[port]))
    undirected = {tuple(sorted(e)) for e in edges}
    ids = sorted(nodes)
    if len(ids) == 3:
        a, b, c = ids
        far = tuple(sorted((a, c)))
        ok("N3", f"the topology is a LINE -- {c} is not a peer of {a}, so a "
                 f"block from {a} must RELAY through {b}",
           far not in undirected,
           f"edges {sorted(undirected)}")
    else:
        ok("N3", "the topology is a line", False, "not three nodes")

    reach = {ids[0]}
    changed = True
    while changed:
        changed = False
        for x, y in undirected:
            if x in reach and y not in reach:
                reach.add(y); changed = True
            elif y in reach and x not in reach:
                reach.add(x); changed = True
    ok("N4", "the peer graph is connected -- no node is isolated",
       reach == set(ids), f"reachable from {ids[0]}: {sorted(reach)}")

    # ----------------------------------------------------------- N5 watchdog
    wd = parse_watchdog()
    mismatches = []
    for nid in sorted(set(nodes) | set(wd)):
        p = nodes.get(nid)
        w = wd.get(nid)
        if p is None:
            mismatches.append(f"{nid} in watchdog, not started by covenant_prod")
        elif w is None:
            mismatches.append(f"{nid} started by covenant_prod, not watched")
        else:
            if p["api"] != w["api"]:
                mismatches.append(f"{nid} port {p['api']} vs {w['api']}")
            if sorted(p["peers"]) != sorted(w["peers"]):
                mismatches.append(
                    f"{nid} peers {sorted(p['peers'])} vs {sorted(w['peers'])}")
            if p["db"] and p["db"] != w["db"]:
                mismatches.append(f"{nid} db {p['db']} vs {w['db']}")
    ok("N5", "covenant_watchdog.py NODES matches covenant_prod.bat exactly",
       not mismatches,
       "; ".join(mismatches) if mismatches
       else f"{len(wd)} nodes, ports peers and dbs all agree")

    # ------------------------------------------------------------- N6 tooling
    missing = []
    for fname, needle in (("launch_check.py", "NODES = ["),
                          ("verify_deploy.py", "NODES = ["),
                          ("dashboard_render.py", "NODES = [")):
        path = os.path.join(HERE, fname)
        if not os.path.exists(path):
            missing.append(f"{fname} absent")
            continue
        text = read(path)
        line = text[text.index(needle):]
        line = line[:line.index("]") + 1]
        for nid, n in nodes.items():
            if str(n["api"]) not in line:
                missing.append(f"{fname} does not know {nid}:{n['api']}")
    ok("N6", "launch_check, verify_deploy and dashboard_render know every node",
       not missing, "; ".join(missing) if missing else "all three updated")

    # ------------------------------------------------------------- N7 restart
    rtext = read(RESTART)
    unstopped = [f"{nid}:{n['api']}" for nid, n in sorted(nodes.items())
                 if str(n["api"]) not in rtext]
    ok("N7", "AB_RESTART_NODES.bat stops every configured API port",
       not unstopped,
       "; ".join(unstopped) + " -- an unstopped node keeps its port and the "
       "next start reports 'already up' and does nothing (P3)"
       if unstopped else "all ports named")

    # ------------------------------------------------------------------ N8 db
    dbs = [n["db"] for n in nodes.values() if n["db"]]
    ok("N8", "every node has its own database",
       len(set(dbs)) == len(dbs) and len(dbs) == len(nodes), ", ".join(sorted(dbs)))

    genesis = {n["genesis"] for n in nodes.values()}
    ok("N9", "every node is started with the SAME canonical genesis file",
       len(genesis) == 1, str(genesis))

    print(f"\n{_passed}/{_passed + _failed} passed")
    return 1 if _failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
