#!/usr/bin/env python3
"""
test_og1_onboard.py -- OG1 (2026-11-02): the highway's AUTO_GATED auto-onboard lane.

THE LANE (covenant_onboard.py) is a third class between AUTO_REVERSIBLE and
PROPOSE_ONLY: the engine MAY auto-peer a known node or auto-arm a vetted task,
but only through a gate rooted in the operator and only on a reversible, local
action. Every promise the lane makes is a refusal, and a refusal nobody has
watched fail is not a guard (M31, and the 35-of-36 fake guards of 2026-09-09).
So each one here is driven BOTH WAYS: the guard refuses, then the one thing it
guards is changed and the SAME call is allowed through -- green proven by having
been red first.

  OG1a  a model's output never triggers it (trigger source must be operator-rooted).
  OG1b  a node NOT on the roster is never auto-onboarded.
  OG1c  an absent / unsigned / signature-bad roster fails closed (the lane is DARK).
  OG1d  a failed whois fails closed (an IP alone is never trusted).
  OG1e  a rostered, identity-verified node auto-peers AND un-peers (exactly reversible).
  OG1f  a system-setting action is refused on a node with the refusal flag (TETSU's line).
  OG1g  a non-reversible (outward) action is never AUTO_GATED.
  OG1j  a grid/ICS-classed effect is refused and handed to covenant_grid_guard's
        together-vote (class derived from the guard's allowlist, reused not forked).
  OG1h  it ships DARK and NOT ARMED: no roster, no arm file -> nothing auto-acts.

Hermetic: a keypair made in-process signs a fixture roster, identity is stubbed,
every path is a temp file. No tailscale, no node, no network.

    python test_og1_onboard.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

import covenant_onboard as O

results = []


def check(label, ok, detail=""):
    results.append((label, bool(ok)))
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}" + (f"  -- {detail}" if detail else ""))


def tmp(suffix):
    return tempfile.mktemp(suffix=suffix)


OPERATOR = "operator@example.com"
PEER_ADDR = "198.51.100.56:5001"
MACHINE_ID = "nABC123NODE"
NODEKEY = "nodekey:abcd1234"


def _sign(body, priv):
    from cryptography.hazmat.primitives import serialization
    payload = O._canonical_payload(body)
    sig = priv.sign(payload)
    pem = priv.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    return sig.hex(), pem


def signed_roster():
    """A roster signed by a fresh operator Ed25519 key (trust root 'signature').
    Returns (roster_dict, operator_pubkey_pem)."""
    from cryptography.hazmat.primitives.asymmetric import ed25519
    priv = ed25519.Ed25519PrivateKey.generate()
    body = {
        "operator_account": OPERATOR,
        "nodes": {
            "known": {"ip": "198.51.100.56", "machine_id": MACHINE_ID, "pubkey": NODEKEY,
                      "peer_addr": PEER_ADDR, "allowed": ["peer", "arm_task", "set_firewall", "push"],
                      "tasks": [{"name": "nightly_self_eval", "gate": "dry"}]},
        },
    }
    sig, pem = _sign(body, priv)
    roster = dict(body, signature=sig, signed_by="operator", alg="ed25519")
    return roster, pem


def good_whois(ip):
    return {"machine_id": MACHINE_ID, "user": OPERATOR, "key": NODEKEY}


def good_status(ip):
    return NODEKEY


ARMED = {"armed": True, "trust_root": "auto"}


def base_gate(roster, pem, **over):
    g = dict(roster=roster, pubkey=pem, armed_cfg=ARMED, operator_account=OPERATOR,
             choices={}, refusals={}, whois_fn=good_whois, status_fn=good_status,
             paused=False, may_act=True)
    g.update(over)
    return g


def main():
    roster, pem = signed_roster()
    known = {"node": "known", "peer_addr": PEER_ADDR}
    scan = {"source": "roster_scan"}

    # A control: with everything right, the gate reaches ACT. Every red below is
    # this exact call with ONE thing broken, so a red proves that one guard.
    ctrl = O.evaluate("peer", known, scan, **base_gate(roster, pem))
    check("OG1 control: armed + rostered + verified + reversible -> ACT", ctrl["decision"] == O.ACT, ctrl["reason"])

    # ---- OG1a: a model's output never triggers AUTO_GATED
    d = O.evaluate("peer", known, {"source": "model"}, **base_gate(roster, pem))
    check("OG1a a model-sourced trigger is REFUSED", d["decision"] == O.REFUSE and "model" in d["reason"], d["reason"])
    d2 = O.evaluate("peer", known, {"source": "model"}, **base_gate(roster, pem))  # still red
    d3 = O.evaluate("peer", known, {"source": "roster_scan"}, **base_gate(roster, pem))  # mutation: operator-rooted
    check("OG1a mutation: an operator-rooted trigger -> ACT", d3["decision"] == O.ACT, d3["decision"])

    # ---- OG1b: a node NOT on the roster is never auto-onboarded
    stranger = {"node": "stranger", "peer_addr": "203.0.113.99:5001"}
    d = O.evaluate("peer", stranger, scan, **base_gate(roster, pem))
    check("OG1b an unknown node is not auto-onboarded (PROPOSE)",
          d["decision"] == O.PROPOSE and "unknown node" in d["reason"], d["reason"])
    # mutation: add the stranger to the roster (re-sign so the trust root still holds)
    r2, pem2 = signed_roster()
    r2body = {k: v for k, v in r2.items() if k not in ("signature", "signed_by", "alg")}
    r2body["nodes"]["stranger"] = {"ip": "203.0.113.99", "machine_id": MACHINE_ID, "pubkey": NODEKEY,
                                   "peer_addr": "203.0.113.99:5001", "allowed": ["peer"]}
    from cryptography.hazmat.primitives.asymmetric import ed25519  # noqa: F401 (kept for parity)
    # re-sign r2body with a fresh key and its pem
    from cryptography.hazmat.primitives.asymmetric import ed25519 as _ed
    priv = _ed.Ed25519PrivateKey.generate()
    sig, pem2 = _sign(r2body, priv)
    r2 = dict(r2body, signature=sig, signed_by="operator", alg="ed25519")
    d = O.evaluate("peer", stranger, scan, **base_gate(r2, pem2))
    check("OG1b mutation: once on the roster -> ACT", d["decision"] == O.ACT, d["decision"])

    # ---- OG1c: absent / unsigned / signature-bad roster fails closed
    d = O.evaluate("peer", known, scan, **base_gate({}, pem))
    check("OG1c an ABSENT roster is dark (PROPOSE, fail closed)",
          d["decision"] == O.PROPOSE and "dark" in d["reason"], d["reason"])
    # a tampered signature: flip the roster body after signing so the sig no longer verifies
    bad = dict(roster)
    bad_nodes = json.loads(json.dumps(bad["nodes"]))
    bad_nodes["known"]["peer_addr"] = "198.51.100.56:9999"   # changed AFTER signing
    bad = dict(bad, nodes=bad_nodes)
    d = O.evaluate("peer", {"node": "known", "peer_addr": "198.51.100.56:9999"}, scan, **base_gate(bad, pem))
    check("OG1c a BAD signature fails closed (PROPOSE, not verified)",
          d["decision"] == O.PROPOSE and "dark" in d["reason"], d["reason"])
    # an unsigned roster that is NOT committed is dark...
    unsigned = {k: v for k, v in roster.items() if k not in ("signature", "signed_by", "alg")}
    d = O.evaluate("peer", known, scan, **base_gate(unsigned, None, committed=False))
    check("OG1c an UNSIGNED, uncommitted roster is dark",
          d["decision"] == O.PROPOSE and "dark" in d["reason"], d["reason"])
    # mutation: the valid signature verifies -> armed -> ACT (already the control), and
    # the whois anchor: an unsigned roster that IS committed arms via trust root 'whois'
    d = O.evaluate("peer", known, scan, **base_gate(unsigned, None, committed=True))
    check("OG1c mutation: unsigned but repo-committed -> whois anchor arms -> ACT",
          d["decision"] == O.ACT and d.get("root") == "whois", "%s root=%s" % (d["decision"], d.get("root")))

    # ---- OG1d: a failed whois fails closed
    d = O.evaluate("peer", known, scan, **base_gate(roster, pem, whois_fn=lambda ip: None))
    check("OG1d a failed whois is REFUSED (identity not verified)",
          d["decision"] == O.REFUSE and "identity not verified" in d["reason"], d["reason"])
    # a whois that names a DIFFERENT owner also fails closed (an IP alone is never trusted)
    d = O.evaluate("peer", known, scan,
                   **base_gate(roster, pem, whois_fn=lambda ip: {"machine_id": MACHINE_ID, "user": "someone_else"}))
    check("OG1d a whois owned by someone else is REFUSED",
          d["decision"] == O.REFUSE and "!=" in d["reason"], d["reason"])
    d = O.evaluate("peer", known, scan, **base_gate(roster, pem))  # mutation: real owner
    check("OG1d mutation: whois names the operator + machine id -> ACT", d["decision"] == O.ACT, d["decision"])

    # ---- OG1e: a rostered, identity-verified node auto-peers AND un-peers (exactly reversible)
    peers_path = tmp("_local_peers.txt")
    real_peers = O.LOCAL_PEERS
    led = tmp("_onboard.jsonl")
    try:
        O.LOCAL_PEERS = peers_path
        before = O._read_peers(peers_path)
        # armed + verified + not dry: the engine performs the peer
        row = O.act("peer", known, scan, dry_run=False, ledger=led, **base_gate(roster, pem))
        after = O._read_peers(peers_path)
        check("OG1e a verified node is auto-PEERED (ran, address written)",
              row.get("ran") and PEER_ADDR in after, "ran=%s peers=%s" % (row.get("ran"), after))
        # the undo is on record and is exact: remove the line, and the file is as it was
        check("OG1e ...the row carries the un-peer undo",
              "un-peer" in row.get("undo", "") and PEER_ADDR in row.get("undo", ""), row.get("undo"))
        O._write_peers([p for p in after if p != PEER_ADDR], peers_path)   # the documented un-peer
        check("OG1e ...un-peering restores the prior state exactly", O._read_peers(peers_path) == before,
              O._read_peers(peers_path))
        # mutation: the same action DRY changes nothing on disk
        O._write_peers(before, peers_path)
        row = O.act("peer", known, scan, dry_run=True, ledger=led, **base_gate(roster, pem))
        check("OG1e mutation: DRY writes nothing (A244)",
              not row.get("ran") and O._read_peers(peers_path) == before, "ran=%s" % row.get("ran"))
    finally:
        O.LOCAL_PEERS = real_peers

    # ---- OG1f: a system-setting action is refused on a node with the refusal flag
    flagged = {"known": ["system-setting"]}
    d = O.evaluate("set_firewall", known, scan, **base_gate(roster, pem, refusals=flagged))
    check("OG1f a flagged node REFUSES a system-setting auto-action",
          d["decision"] == O.REFUSE and "refuses" in d["reason"], d["reason"])
    # mutation: no flag -> the SAME firewall action is only PROPOSED (still never ACTs: system-setting
    # is PROPOSE_ONLY forever), so the flag's effect is the decision changing from REFUSE to PROPOSE
    d2 = O.evaluate("set_firewall", known, scan, **base_gate(roster, pem, refusals={}))
    check("OG1f mutation: unflagged -> PROPOSE (not REFUSE); the flag is a real guard, and firewall still never ACTs",
          d2["decision"] == O.PROPOSE, d2["decision"])

    # ---- OG1g: a non-reversible (outward) action is never AUTO_GATED
    out_target = {"node": "known"}
    d = O.evaluate("push", out_target, scan, **base_gate(roster, pem))
    check("OG1g an outward (push) action is PROPOSE (not reversible)",
          d["decision"] == O.PROPOSE and "not reversible" in d["reason"], d["reason"])
    real_push = dict(O.ACTIONS["push"])
    try:
        # mutation: pretend push were reversible -> the guard stops refusing it
        O.ACTIONS["push"] = dict(real_push, reversible=True)
        d = O.evaluate("push", out_target, scan, **base_gate(roster, pem))
        check("OG1g mutation: flip reversible -> the 'not reversible' refusal disappears",
              "not reversible" not in d.get("reason", ""), d.get("reason"))
    finally:
        O.ACTIONS["push"] = real_push

    # ---- OG1j: a grid/ICS-classed effect is refused and handed to the grid guard (together-vote)
    import covenant_grid_guard as G
    # breaker_open is ACTUATION in the grid guard's OWN allowlist -- a grid effect, though it is NOT one
    # of this lane's actions. AUTO_GATED must REFUSE it and route it to the operator+Tetsu together-vote.
    d = O.evaluate("breaker_open", {"node": "known"}, scan, **base_gate(roster, pem))
    check("OG1j a grid ACTUATION action is REFUSED by AUTO_GATED and routed to the grid guard",
          d["decision"] == O.REFUSE and d.get("route") == "grid_guard" and "together-vote" in d["reason"],
          "%s route=%s" % (d["decision"], d.get("route")))
    # mutation 1: a non-grid action (peer), everything else identical, is NOT grid-routed -> ACT
    d2 = O.evaluate("peer", known, scan, **base_gate(roster, pem))
    check("OG1j mutation: a non-grid action is not routed to the grid guard -> ACT",
          d2["decision"] == O.ACT and d2.get("route") != "grid_guard", d2["decision"])
    # mutation 2: the class is DERIVED from the grid guard's allowlist (reused, not forked) -- remove the
    # entry and the SAME action stops being grid-routed, proving the single source of truth.
    real_ac = dict(G.ACTION_CLASS)
    try:
        G.ACTION_CLASS.pop("breaker_open", None)
        d3 = O.evaluate("breaker_open", {"node": "known"}, scan, **base_gate(roster, pem))
        check("OG1j mutation: drop breaker_open from the grid allowlist -> no longer grid-routed",
              d3.get("route") != "grid_guard", "%s route=%s" % (d3["decision"], d3.get("route")))
    finally:
        G.ACTION_CLASS.clear()
        G.ACTION_CLASS.update(real_ac)

    # ---- OG1h: ships DARK and NOT ARMED (the real files, read from disk as production would)
    armed, root, why = O.is_armed()
    check("OG1h the lane ships DARK (not armed from the real files on disk)", not armed, why)
    a, i = O.run_once(dry_run=False)     # even asked to act for real, it does nothing: dark
    check("OG1h run_once dark -> no alerts, one DARK info, nothing acted",
          not a and any("DARK" in x for x in i), "alerts=%s infos=%s" % (a, i))

    # ---- arm_task keeps its own gate (a vetted task only, and the gate must be present)
    tasks_path = tmp("_armed_tasks.json")
    real_tasks = O.ARMED_TASKS
    try:
        O.ARMED_TASKS = tasks_path
        good_task = {"node": "known", "task": {"name": "nightly_self_eval", "gate": "dry"}}
        d = O.evaluate("arm_task", good_task, scan, **base_gate(roster, pem))
        check("OG1i a vetted task that keeps its gate -> ACT", d["decision"] == O.ACT, d["reason"])
        ungated = {"node": "known", "task": {"name": "nightly_self_eval", "gate": ""}}
        row = O.act("arm_task", ungated, scan, dry_run=False, ledger=led, **base_gate(roster, pem))
        check("OG1i mutation: a task with NO gate is not armed (held)",
              not row.get("ran") and "own gate" in row.get("detail", ""), row.get("detail"))
    finally:
        O.ARMED_TASKS = real_tasks

    failed = [n for n, ok in results if not ok]
    print(f"\nOG1: {len(results) - len(failed)}/{len(results)} passed")
    if failed:
        print("FAILED: " + "; ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
