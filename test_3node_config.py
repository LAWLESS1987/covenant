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
# Node A's off-box peers (the phone's tailnet address) live in this gitignored file,
# read by BOTH launchers (2026-09-26 OPSEC sweep): the public files carry no address.
# N5 still compares the two launchers' TEXT; the shared file is resolved the same way
# for each, so dropping it from either launcher is a mismatch here.
LOCAL_PEERS = os.path.join(HERE, "ops", "local_peers.txt")


def local_peers():
    try:
        with open(LOCAL_PEERS, encoding="utf-8") as fh:
            s = fh.readline().strip().strip(",")
    except OSError:
        return []
    return [p for p in s.split(",") if p]

_passed, _failed = 0, 0


def ok(tag, name, cond, detail="", needs=None):
    """`needs`: the input file this check reads.

    If that file is absent the check is not run and not counted -- neither as a
    pass nor as a failure. Letting it run against an empty string turns "the
    file is not here" into "the three nodes disagree", which is a different
    finding about a different thing."""
    global _passed, _failed
    if needs and needs in MISSING:
        print(f"UNKN  {tag} {name}  not run: {needs} is not here")
        return
    if cond:
        _passed += 1
        print(f"PASS  {tag} {name}  {detail}")
    else:
        _failed += 1
        print(f"FAIL  {tag} {name}  {detail}")


MISSING = []


def read(path):
    """Read one of this suite's INPUTS, or record that it is not here.

    A missing input is not a failing check (M37). This suite asserts that the
    shipped configuration files agree with each other; run somewhere one of
    them is absent -- a fresh clone, a partial copy, a sweep scratch tree
    staged without the .bat files -- it used to die on a raw FileNotFoundError
    traceback with no tally, which the sweep then printed as a RED suite. That
    reads exactly like the three nodes disagreeing, and it is not: it is the
    file not being there.

    Returns "" and records the name, so main() can report UNKNOWN and say which
    file. UNKNOWN is never folded into PASS."""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        rel = os.path.basename(path)
        if rel not in MISSING:
            MISSING.append(rel)
        return ""


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
        plist = [] if not peers else [p for p in peers.split(",") if p]
        if m.group(4) is not None and line[m.end():].startswith("%A_EXTRA%"):
            plist += local_peers()
        nodes[nid] = {
            "api": int(api),
            "genesis": genesis,
            "peers": plist,
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
            r'\s*"key":\s*"([^"]+)",\s*"peers":\s*"([^"]*)"(\s*\+\s*_local_peers\(\))?\}', block):
        out[m.group(1)] = {"api": int(m.group(2)), "db": m.group(3),
                           "key": m.group(4),
                           "peers": [p for p in m.group(5).split(",") if p]
                                    + (local_peers() if m.group(6) else [])}
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
    # HOST-AWARE SINCE 2026-09-14. These checks used to do
    # `int(peer.rsplit(":", 1)[1])` and throw the host away, which is only safe
    # while every peer is on loopback. The operator's phone was added to node A
    # as 100.72.0.10:5001, and 5001 IS node A's own P2P port -- so N2 read it
    # as "A peers with A", N3 gained a self-edge, and the suite reported 11/11
    # on a graph that was wrong. It passed by coincidence of port numbers, and
    # the next remote peer whose port happened NOT to collide would have been
    # reported as "no configured node's P2P port" -- a false FAIL on a correct
    # configuration. A peer somewhere else on the network is a legitimate thing
    # this file had no way to say.
    LOCAL_HOSTS = ("127.0.0.1", "localhost", "::1")

    def split_peer(p):
        host, _, port = p.rpartition(":")
        return host, int(port)

    p2p_of = {n["api"] + 1: nid for nid, n in nodes.items()}
    api_of = {n["api"]: nid for nid, n in nodes.items()}
    bad, good, external = [], [], []
    for nid, n in sorted(nodes.items()):
        for peer in n["peers"]:
            host, port = split_peer(peer)
            if host not in LOCAL_HOSTS:
                # Off-box peer. Nothing here can check that it is reachable or
                # that it is really a node; what it CAN check is that it is not
                # silently malformed, and that it is not aimed at an API port,
                # which is the one mistake the shape can reveal.
                if port in api_of and port not in p2p_of:
                    bad.append(f"{nid} points at {host}:{port}, an API port number; "
                               f"--peers wants the P2P port ({port + 1})")
                else:
                    external.append(f"{nid}->{host}:{port}")
                continue
            if port in p2p_of and p2p_of[port] == nid:
                # A NODE LISTED AS ITS OWN PEER. Added 2026-09-14 after an audit
                # asked whether making this check CORRECT had made it
                # PROTECTIVE, and the answer was no: planting
                # `127.0.0.1:5001` in node A's peers -- node A's own P2P port --
                # left every check in this file green. Before the host-aware
                # fix above, the phone's off-box `100.72.0.10:5001` was being
                # MISREAD as exactly this and passing; the fix stopped the
                # misreading without ever making the real thing fail, which is
                # a report that got truer while protecting nothing.
                #
                # run_node's preflight does refuse this, fatally, at startup
                # (covenant_unified_v8.py: "A node cannot peer with itself").
                # That is the guarantee; this is the place it is cheap to
                # learn, because the alternative is finding out when a node
                # will not come back up.
                bad.append(f"{nid} lists its OWN P2P port {port} as a peer -- a node "
                           f"cannot peer with itself, and run_node will refuse to start")
            elif port in p2p_of:
                good.append(f"{nid}->{p2p_of[port]}")
            elif port in api_of:
                bad.append(f"{nid} points at {api_of[port]}'s API port {port}, "
                           f"not its P2P port {port + 1}")
            else:
                bad.append(f"{nid} points at {port}, which is no configured "
                           f"node's P2P port")
    ok("N2", "every LOCAL --peers entry is a configured node's P2P port (API+1); "
             "off-box peers are allowed and named",
       not bad, "; ".join(bad) if bad else
       " ".join(good) + (("  | external: " + " ".join(external)) if external else ""))

    # ------------------------------------------------------------ N3/N4 shape
    # LOCAL edges only. An off-box peer is not part of the three-node line these
    # two checks describe, and counting one as an edge produced a self-loop
    # (A->A) the moment the phone was added -- see the note on N2 above.
    edges = set()
    for nid, n in nodes.items():
        for peer in n["peers"]:
            host, port = split_peer(peer)
            if host in LOCAL_HOSTS and port in p2p_of:
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
       else f"{len(wd)} nodes, ports peers and dbs all agree", needs="covenant_watchdog.py")

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
       if unstopped else "all ports named", needs="AB_RESTART_NODES.bat")

    # ------------------------------------------------------------------ N8 db
    dbs = [n["db"] for n in nodes.values() if n["db"]]
    ok("N8", "every node has its own database",
       len(set(dbs)) == len(dbs) and len(dbs) == len(nodes), ", ".join(sorted(dbs)))

    genesis = {n["genesis"] for n in nodes.values()}
    ok("N9", "every node is started with the SAME canonical genesis file",
       len(genesis) == 1, str(genesis))

    if MISSING:
        print(f"\nUNKNOWN: {len(MISSING)} input file(s) are not here -- "
              f"{', '.join(MISSING)}")
        print("These are the files this suite COMPARES. Without them it has "
              "not checked the\nconfiguration and has not found it wrong. "
              "Exit 2: not a pass, and not a failure\nof the three nodes.")
        print(f"\n{_passed}/{_passed + _failed} passed, {len(MISSING)} input(s) missing")
        return 2
    print(f"\n{_passed}/{_passed + _failed} passed")
    return 1 if _failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
