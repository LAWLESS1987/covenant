#!/usr/bin/env python3
"""cluster.py -- nodes D, E and F: the memory layer's three-node quorum.

The chain has A (5000), B (5020) and C (5060) with a watchdog above them and a
guard above that. This is the same shape one layer down, for memory: D (5100),
E (5120), F (5140), a watchdog that reads all three, and the guard pattern
above it. Same mechanism, micro and macro.

WHAT THE NODES ACTUALLY COMPARE, AND THE CLAIM THAT WAS WRONG FIRST.

This module originally used each node's AUDIT CHAIN HEAD as the consensus
token, arguing that replicas accepting the same writes in the same order must
produce identical hashes. Three real nodes were then given one identical write
and produced THREE DIFFERENT HEADS. Every ledger line carries `"at": _now()`,
so the bytes differ by microseconds per node and the chain commits to them.
The head fingerprints one node's log INCLUDING WHEN IT WROTE -- perfect for
local tamper-evidence, worthless for agreement. The claim survived writing,
review and a docstring; it did not survive being run.

So nodes compare `state_root()`: a domain-separated Merkle root over the
sorted set of (name, content_digest) pairs. Three properties, each load-bearing:

  * UNTIMED -- no clock, no write order, nothing node-local, so honest
    replicas match exactly.
  * OVER STATE, NOT SEQUENCE -- two nodes that accepted the same memories in
    opposite orders HOLD the same memories and agree. A sequence token would
    call ordinary concurrent traffic a split, and an alarm that fires on
    normal operation is one nobody keeps.
  * CONTENT-SENSITIVE -- edit one body on one node and that node's root moves
    alone, because the leaves are content digests.

The chain head is still checked, per node, for the job it is actually good at.

WHAT THIS IS NOT, STATED PLAINLY BECAUSE THE NAME INVITES THE ERROR.

This is replicated write plus divergence detection. It is NOT Raft, NOT Paxos,
NOT Byzantine fault tolerance, and it does NOT give partition-tolerant
linearizability. There is no leader election, no log repair, and no rollback of
a write that reached one node and not the others.

What it does give, which is the property that was actually asked for:

  * No single node can be quietly altered. Change a memory on D and D's
    content digest moves; its head stays put while its files no longer match
    it, and E and F still disagree with whatever D now says. One machine
    cannot sway the record because two others hold it independently.
  * A write that does not reach a quorum is reported as UNCOMMITTED rather
    than being reported as success. A one-node write is not a stored fact.
  * Every node self-verifies BOTH ways -- chain and content -- so a node that
    is lying about its own history is visible without trusting its summary.

The decision logic is a PURE FUNCTION (`assess`) over reports, so every split
this cluster can experience is exercised in the suite with no ports, no
servers, and no sleeping. A supervisor that can only be tested by breaking a
live deployment is a supervisor nobody tests.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

# Same 20-port spacing as A/B/C, in a band that cannot collide with them.
NODES: Tuple[Tuple[str, int], ...] = (("D", 5100), ("E", 5120), ("F", 5140))

# 2 of 3. Deliberately a constant rather than len(NODES)//2+1 computed at the
# call site: a quorum that silently follows the node count would become 1-of-1
# the moment somebody ran a single node for convenience, and a one-node quorum
# is not a quorum, it is a spelling of "no quorum".
QUORUM = 2

AGREE, SPLIT, DEGRADED, NO_QUORUM = "agree", "split", "degraded", "no-quorum"


def assess(reports: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Pure verdict over per-node reports. No I/O, no clock, no state.

    A report is {node, ok, head, chain_ok, content_ok, count, error}.
    `ok` False means the node did not answer at all -- which is a DIFFERENT
    thing from a node that answered with a different head, and the two must
    never be collapsed. An unreachable node is unknown; a disagreeing node is
    evidence.
    """
    live = [r for r in reports if r.get("ok")]
    dead = [r for r in reports if not r.get("ok")]
    # A node whose own self-checks fail is not a witness, whatever it says its
    # head is. Excluded from the agreement count and named separately, because
    # "two nodes agree" is a lie if one of them cannot verify its own files.
    sound = [r for r in live
             if r.get("chain_ok") and r.get("content_ok")]
    unsound = [r for r in live if r not in sound]

    heads: Dict[str, List[str]] = {}
    for r in sound:
        heads.setdefault(r.get("head") or "", []).append(r["node"])

    if not sound:
        return {"verdict": NO_QUORUM, "reason":
                f"no sound node answered ({len(dead)} unreachable, "
                f"{len(unsound)} failing self-check)",
                "heads": heads, "dead": [r["node"] for r in dead],
                "unsound": [r["node"] for r in unsound], "majority": None}

    top_head, top_nodes = max(heads.items(), key=lambda kv: len(kv[1]))
    agreeing = len(top_nodes)

    if len(heads) > 1:
        # Real divergence: two sound nodes that disagree about history. This
        # is the case the whole layer exists to surface, so it outranks a
        # thin-but-unanimous cluster in severity.
        return {"verdict": SPLIT, "reason":
                f"sound nodes disagree on history: "
                + "; ".join(f"{h[:12]}={sorted(ns)}" for h, ns in heads.items()),
                "heads": heads, "dead": [r["node"] for r in dead],
                "unsound": [r["node"] for r in unsound],
                "majority": top_head if agreeing >= QUORUM else None}

    if agreeing < QUORUM:
        return {"verdict": NO_QUORUM, "reason":
                f"only {agreeing} sound node(s); quorum is {QUORUM}",
                "heads": heads, "dead": [r["node"] for r in dead],
                "unsound": [r["node"] for r in unsound], "majority": None}

    if dead or unsound:
        return {"verdict": DEGRADED, "reason":
                f"{agreeing} agree at {top_head[:12]}, but "
                f"{len(dead)} unreachable and {len(unsound)} failing self-check",
                "heads": heads, "dead": [r["node"] for r in dead],
                "unsound": [r["node"] for r in unsound], "majority": top_head}

    return {"verdict": AGREE, "reason":
            f"all {agreeing} nodes at {top_head[:12]}", "heads": heads,
            "dead": [], "unsound": [], "majority": top_head}


def _get(url: str, token: str = "", timeout: float = 4.0) -> Any:
    req = urllib.request.Request(url, method="GET")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def poll(nodes: Tuple[Tuple[str, int], ...] = NODES, token: str = "",
         host: str = "127.0.0.1", timeout: float = 4.0) -> List[Dict[str, Any]]:
    """Ask every node for its head and its two self-checks. Reads only."""
    out = []
    for name, port in nodes:
        rec: Dict[str, Any] = {"node": name, "port": port, "ok": False,
                               "head": "", "chain_head": "", "memories": 0, "chain_ok": False,
                               "content_ok": False, "count": 0, "error": ""}
        try:
            v = _get(f"http://{host}:{port}/audit", token, timeout)
            chain = v.get("chain") or {}
            content = v.get("content") or {}
            state = v.get("state") or {}
            # `head` is the STATE root -- the thing that is comparable. The
            # chain head is kept beside it under its own name so a report can
            # show both without either being mistaken for the other.
            rec.update(ok=True, head=state.get("root", ""),
                       chain_head=chain.get("head", ""),
                       memories=int(state.get("memories", 0) or 0),
                       chain_ok=bool(chain.get("ok")),
                       content_ok=bool(content.get("ok")),
                       count=int(chain.get("entries", 0) or 0))
            if not state:
                # An older node that does not serve a state root cannot be
                # compared. Not sound, and not silently agreed with.
                rec["content_ok"] = False
                rec["error"] = "node serves no state root; cannot be compared"
            # An unverifiable-but-undrifted node is SOUND. Memories written
            # before content digests existed cannot be checked either way, and
            # treating "cannot check" as "failed" would take a whole node out
            # of the quorum over its own history rather than over any fault.
            if content.get("drifted") or content.get("missing"):
                rec["content_ok"] = False
        except (urllib.error.URLError, OSError, ValueError) as exc:
            rec["error"] = f"{type(exc).__name__}: {exc}"
        out.append(rec)
    return out


class MemoryCluster:
    """Write to D, E and F; a write counts only when a quorum took it."""

    def __init__(self, nodes: Tuple[Tuple[str, int], ...] = NODES,
                 token: str = "", host: str = "127.0.0.1"):
        self.nodes, self.token, self.host = nodes, token, host

    def put(self, name: str, payload: Dict[str, Any],
            timeout: float = 8.0) -> Dict[str, Any]:
        """Replicate one write. Reports per-node outcome and whether it COMMITTED.

        There is no rollback. A write that lands on one node and fails on two
        is reported UNCOMMITTED with the node that took it named, so the
        operator repairs a known inconsistency rather than discovering an
        unknown one. Pretending to undo a write we cannot undo would be worse
        than saying where it landed.
        """
        results, took = [], []
        for nm, port in self.nodes:
            url = f"http://{self.host}:{port}/memories/{name}"
            data = json.dumps(payload).encode()
            req = urllib.request.Request(url, data=data, method="PUT")
            req.add_header("Content-Type", "application/json")
            if self.token:
                req.add_header("Authorization", f"Bearer {self.token}")
            try:
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    body = json.loads(r.read().decode())
                results.append({"node": nm, "status": r.status, "body": body})
                if 200 <= r.status < 300 and body.get("written") is not False:
                    took.append(nm)
            except urllib.error.HTTPError as e:
                # A 4xx is the node REFUSING -- an ethics block or a bad name.
                # Distinct from a node being down, and it must not read as one:
                # three nodes refusing a poisoned memory is the system working,
                # not an outage.
                try:
                    body = json.loads(e.read().decode())
                except (ValueError, OSError):
                    body = {}
                results.append({"node": nm, "status": e.code, "body": body,
                                "refused": True})
            except (urllib.error.URLError, OSError) as exc:
                results.append({"node": nm, "status": 0,
                                "error": f"{type(exc).__name__}: {exc}"})
        refused = [r["node"] for r in results if r.get("refused")]
        return {"committed": len(took) >= QUORUM, "accepted": took,
                "refused": refused, "quorum": QUORUM, "results": results,
                "reason": ("committed on " + ",".join(took)) if
                len(took) >= QUORUM else
                (f"REFUSED by {','.join(refused)}" if refused else
                 f"UNCOMMITTED: only {len(took)}/{QUORUM} accepted"
                 + (f"; landed on {','.join(took)}" if took else ""))}

    def status(self, timeout: float = 4.0) -> Dict[str, Any]:
        reports = poll(self.nodes, self.token, self.host, timeout)
        return {"assessment": assess(reports), "nodes": reports}


def roots(base: str) -> Dict[str, str]:
    """Per-node store directories under one base. Separate roots on purpose:
    three nodes sharing one directory would agree trivially and prove nothing.
    """
    return {n: os.path.join(base, f"node{n}") for n, _ in NODES}
