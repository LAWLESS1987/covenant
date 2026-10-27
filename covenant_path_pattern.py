#!/usr/bin/env python3
"""
covenant_path_pattern.py -- path-dependent pattern assembly.

A pattern P is split into shares, each share is sealed into a node, and the
seal for node v_i is derived from the RUNNING STATE of the traversal that
reaches it -- not from the node itself. Collecting every node's payload is
therefore not enough; you must walk the exact directed path, in order.

    State_1 = HMAC(seed, tag(v_1))
    State_i = HMAC(State_{i-1}, K_{i-1,i} || node_id(v_i))
    S_i     = Unseal(D_i, State_i)
    P       = S_1 XOR S_2 XOR ... XOR S_k

ONE DESIGN DECISION IS LOAD-BEARING, and it is the one that looks wrong:

  Node payloads are sealed with an UNAUTHENTICATED keystream, not with an AEAD
  such as AES-GCM. Reaching for AES-GCM here is the obvious "improvement" and it
  silently destroys the security property. AEAD fails loudly on a wrong key,
  which hands an attacker a per-hop ORACLE: guess hop 1, see whether it
  authenticates, keep it, move on. That reduces the search from "guess the whole
  path at once" to "guess one hop at a time" -- from exponential to linear in
  path length. With a raw keystream a wrong hop yields bytes indistinguishable
  from noise, and the attacker learns nothing until the ENTIRE path is right.

  Integrity is recovered at the end instead: a single tag over the reconstructed
  P. Verification happens once, on the whole pattern, where it cannot be used as
  a stepwise oracle. See test_path_pattern.py, which demonstrates the oracle
  against an AEAD variant rather than asserting it.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

DOMAIN_SEED = b"COVENANT_PATTERN_SEED_V1"
DOMAIN_EDGE = b"COVENANT_PATTERN_EDGE_V1"
DOMAIN_SEAL = b"COVENANT_PATTERN_SEAL_V1"
DOMAIN_TAG = b"COVENANT_PATTERN_TAG_V1"


def _hmac(key: bytes, *parts: bytes) -> bytes:
    m = hmac.new(key, digestmod=hashlib.sha256)
    for p in parts:
        m.update(len(p).to_bytes(4, "big"))
        m.update(p)
    return m.digest()


def _keystream(state: bytes, nbytes: int) -> bytes:
    """Deterministic keystream from a traversal state. Counter-mode HMAC."""
    out = bytearray()
    counter = 0
    while len(out) < nbytes:
        out += _hmac(state, DOMAIN_SEAL, counter.to_bytes(8, "big"))
        counter += 1
    return bytes(out[:nbytes])


def _xor(a: bytes, b: bytes) -> bytes:
    return bytes(x ^ y for x, y in zip(a, b))


def split_xor(pattern: bytes, k: int) -> List[bytes]:
    """n-of-n XOR split. Every share is required; any k-1 shares are
    information-theoretically independent of the pattern."""
    if k < 2:
        raise ValueError("need at least 2 shares")
    shares = [secrets.token_bytes(len(pattern)) for _ in range(k - 1)]
    last = pattern
    for s in shares:
        last = _xor(last, s)
    shares.append(last)
    return shares


def combine_xor(shares: List[bytes]) -> bytes:
    out = shares[0]
    for s in shares[1:]:
        out = _xor(out, s)
    return out


@dataclass
class PatternGraph:
    """Nodes hold sealed payloads; edges hold keys. Neither reveals the path."""
    node_payloads: Dict[str, bytes] = field(default_factory=dict)
    edge_keys: Dict[Tuple[str, str], bytes] = field(default_factory=dict)
    pattern_tag: bytes = b""
    pattern_len: int = 0

    def decoy_fill(self, node_ids: List[str], size: int):
        """Give every non-path node a uniformly random payload of the same size.

        Without this the path is trivially visible: only the nodes that carry
        real shares would hold data at all. Decoys make every node look
        identical to every other -- which is the whole point of topological
        anonymity."""
        for nid in node_ids:
            self.node_payloads.setdefault(nid, secrets.token_bytes(size))

    def ensure_edges(self, node_ids: List[str], rng=None):
        """Populate edge keys for every ordered pair, so the presence of an edge
        key does not itself leak which edges are on the path."""
        for a in node_ids:
            for b in node_ids:
                if a != b:
                    self.edge_keys.setdefault((a, b), secrets.token_bytes(32))


def traversal_states(seed: bytes, path: List[str], graph: PatternGraph) -> List[bytes]:
    """The running state at each hop. Node identity is folded in alongside the
    edge key so that two different paths sharing an edge-key sequence still
    diverge -- binding the walk to WHO was visited, not only to which keys."""
    states = [_hmac(seed, DOMAIN_SEED, path[0].encode())]
    for i in range(1, len(path)):
        k = graph.edge_keys.get((path[i - 1], path[i]))
        if k is None:
            # A missing edge must NOT be distinguishable from a wrong one:
            # deriving a deterministic pseudo-key keeps the failure silent.
            k = _hmac(seed, DOMAIN_EDGE, path[i - 1].encode(), path[i].encode())
        states.append(_hmac(states[-1], DOMAIN_EDGE, k, path[i].encode()))
    return states


def build(pattern: bytes, path: List[str], all_nodes: Optional[List[str]] = None,
          seed: Optional[bytes] = None) -> Tuple[PatternGraph, bytes]:
    """Seal `pattern` across `path`. Returns (graph, seed)."""
    if len(path) < 2:
        raise ValueError("path must contain at least 2 nodes")
    if len(set(path)) != len(path):
        raise ValueError("path must not repeat a node")
    seed = seed or secrets.token_bytes(32)
    g = PatternGraph(pattern_len=len(pattern))
    g.ensure_edges(all_nodes or path)

    shares = split_xor(pattern, len(path))
    states = traversal_states(seed, path, g)
    for node_id, share, st in zip(path, shares, states):
        g.node_payloads[node_id] = _xor(share, _keystream(st, len(share)))

    # Integrity over the FINAL pattern only -- never per hop, so it cannot be
    # used as a stepwise oracle.
    g.pattern_tag = _hmac(seed, DOMAIN_TAG, pattern)
    if all_nodes:
        g.decoy_fill(all_nodes, len(pattern))
    return g, seed


def assemble(graph: PatternGraph, path: List[str], seed: bytes) -> Tuple[bytes, bool]:
    """Walk `path` and reconstruct. Returns (result, verified).

    A wrong path returns bytes, not an error -- indistinguishable from noise.
    `verified` is the single end-of-walk integrity check.
    """
    states = traversal_states(seed, path, graph)
    shares = []
    for node_id, st in zip(path, states):
        payload = graph.node_payloads.get(node_id)
        if payload is None:
            # Absent node: contribute deterministic noise rather than failing,
            # so a missing node is not distinguishable from a wrong key.
            payload = _keystream(_hmac(seed, DOMAIN_SEAL, node_id.encode()),
                                 graph.pattern_len)
        shares.append(_xor(payload, _keystream(st, len(payload))))
    result = combine_xor(shares)
    verified = hmac.compare_digest(_hmac(seed, DOMAIN_TAG, result), graph.pattern_tag)
    return result, verified


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------
import json as _json


def serialize(graph: PatternGraph) -> str:
    """Serialize a sealed graph for storage. Contains no plaintext and no
    indication of which nodes lie on the path -- payloads are uniform-length
    and uniformly random-looking whether they carry a share or a decoy."""
    return _json.dumps({
        "v": 1,
        "pattern_len": graph.pattern_len,
        "pattern_tag": graph.pattern_tag.hex(),
        "nodes": {k: v.hex() for k, v in graph.node_payloads.items()},
        "edges": {f"{a}\x1f{b}": k.hex() for (a, b), k in graph.edge_keys.items()},
    }, sort_keys=True)


def deserialize(blob: str) -> PatternGraph:
    d = _json.loads(blob)
    g = PatternGraph(pattern_len=int(d["pattern_len"]),
                     pattern_tag=bytes.fromhex(d["pattern_tag"]))
    g.node_payloads = {k: bytes.fromhex(v) for k, v in d["nodes"].items()}
    g.edge_keys = {tuple(k.split("\x1f")): bytes.fromhex(v) for k, v in d["edges"].items()}
    return g
