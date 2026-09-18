#!/usr/bin/env python3
"""H2 (2026-09-18): the update door has a witness, and the self-heal can see a
peer's drift without being handed a condition it cannot clear.

WHY
---
Three things were measured on 2026-09-18 and all three were invisible to the
machinery built to notice them:

1. The phone ran core ddfaaa9f704f while disk and all three local nodes ran
   7b12fe509061. Node A said so in a /health warning on every self-eval round
   for two days. The highway's detect_source_drift answered `drifted: []`
   throughout -- correctly: it reads the three nodes it can restart.
2. The APK that fixes it had been on this PC since 07:41 and the phone had not
   taken it in 46.6 h. Nothing here could say whether the phone had ever asked,
   because the node keeps no access log -- `grep /app/latest logs/*.log` is 0
   in every file, and so is `grep checkin`, while ops/phone_checkins.jsonl
   holds 615 rows. Absence in those logs was never evidence.
3. mesh.tracked read 4 for 2 peers: the outbound path keyed peer rows by
   host:port and the inbound path by resolve_peer_id, so each peer held two
   rows under two spellings.

CHECKS
  W1-W6   the witness ledger: it records, it is bounded, it coerces what a
          header hands it, it survives an unwritable directory, and an EMPTY
          ledger is reported as "nobody asked SINCE IT BEGAN", never as proof
  S1-S5   detect_mesh_source_split: PRESENT on a drifted peer, ABSENT when the
          mesh agrees, UNKNOWN when no peer has reported -- and it names what
          it cannot see
  R1-R3   THE REGRESSION THAT MATTERS: a drifted PEER must NOT make
          source_drift PRESENT. restart_nodes is paired to that detector and
          cannot clear a phone; if it were graded against this it would
          quarantine itself after two correct runs (the fetch_build lesson).
  N1-N3   one namespace for peer rows: the key both call sites compute for the
          same peer is the SAME key, and a peer sent-to and heard-from holds
          one row, not two
  A1-A3   summary() carries heard_s_ago, and `tracked`/`by_source` keep the
          exact shape test_a20's C4b and H1 read
  L1-L2   LIVE, when the mesh is up: what node A actually reports now

Nothing here needs .git, a network, or a running node: L1-L2 report NOT RUN
when the mesh is down (covenant_one stages to a temp dir with no .git, and a
suite that is green only on this machine is an assertion, not a measurement).
"""
import json
import os
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

results, UNRUN = [], []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}")


def not_run(name, why):
    UNRUN.append((name, why))
    print(f"NOT RUN  {name}  -- {why}")


# ----------------------------------------------------------- the witness --
def witness_checks():
    import covenant_app_update as AU

    tmp = tempfile.mkdtemp(prefix="h2_witness_")
    old_dir, old_req = AU.DIR, AU.REQUESTS
    AU.DIR = tmp
    AU.REQUESTS = os.path.join(tmp, "requests.jsonl")
    try:
        check("W1 an empty ledger reads as [] and not as an error",
              AU.requests_tail() == [], "no file yet")

        AU.note_request("/app/latest", "phone", "c0de384", "served-signed")
        rows = AU.requests_tail()
        check("W2 an ask is recorded with route, signer, build and outcome",
              len(rows) == 1 and rows[0]["route"] == "/app/latest"
              and rows[0]["signer"] == "phone" and rows[0]["offered"] == "c0de384"
              and rows[0]["outcome"] == "served-signed" and rows[0]["at"] > 0,
              json.dumps(rows[0], sort_keys=True)[:160])

        # A REFUSAL is the event that distinguishes the two faults.
        AU.note_request("/app/latest", "", "", "refused", "unknown signer")
        AU.note_request("/app/apk", "phone", "c0de384", "sending", "45158352 bytes")
        check("W3 the route filter separates the manifest ask from the download",
              len(AU.requests_tail(route="/app/latest")) == 2
              and len(AU.requests_tail(route="/app/apk")) == 1
              and AU.requests_tail(route="/app/latest")[-1]["outcome"] == "refused",
              str([r["outcome"] for r in AU.requests_tail()]))

        # Coercion: `signer` comes off a request header, `detail` off an auth
        # message. Neither is trusted for type or length.
        AU.note_request("/app/latest", "s" * 400, 12345, {"not": "a string"}, "d" * 900)
        r = AU.requests_tail(1)[0]
        check("W4 header-supplied fields are coerced and length-capped",
              len(r["signer"]) == 64 and r["offered"] == "12345"
              and isinstance(r["outcome"], str) and len(r["detail"]) == 200,
              f"signer={len(r['signer'])} detail={len(r['detail'])} offered={r['offered']!r}")

        keep = AU.REQUESTS_KEEP
        AU.REQUESTS_KEEP = 20
        try:
            for i in range(60):
                AU.note_request("/app/latest", "phone", "b%d" % i, "served-signed")
            with open(AU.REQUESTS, encoding="utf-8") as fh:
                n = len([l for l in fh if l.strip()])
            check("W5 the ledger is bounded -- it cannot eat the disk",
                  n == 20, f"{n} lines with KEEP=20")
        finally:
            AU.REQUESTS_KEEP = keep

        # BROKEN ON PURPOSE: a witness that can break the door it watches is
        # worse than no witness. Point it at a path that cannot be written.
        AU.REQUESTS = os.path.join(tmp, "nope", "deeper", "requests.jsonl")
        AU.DIR = os.path.join(tmp, "nope") + "\0bad" if os.name != "nt" else "\0bad"
        try:
            AU.note_request("/app/latest", "phone", "x", "served-signed")
            raised = False
        except Exception:                                        # noqa: BLE001
            raised = True
        check("W6 an unwritable ledger is swallowed, never raised at the door",
              not raised, "note_request returned normally")
    finally:
        AU.DIR, AU.REQUESTS = old_dir, old_req
        shutil.rmtree(tmp, ignore_errors=True)


# ------------------------------------------------- the mesh split detector --
def _health_fixture(local_src, peer_map, ages=None):
    """One local node's /health, with `mesh` as A20 builds it."""
    by_source = {}
    for who, src in peer_map.items():
        by_source.setdefault(src, []).append(who)
    return {"A": {"source_sha256": local_src, "chain_height": 35,
                  "mesh": {"tracked": len(peer_map), "by_source": by_source,
                           "heard_s_ago": ages or {}}}}


def split_checks():
    import covenant_highway as H
    import covenant_watchdog as W

    disk = W.disk_source_sha12()
    if not disk:
        not_run("S1-S5/R1-R3 the split detector",
                "this tree's own core source is unreadable, so there is no "
                "disk sha for the source_drift half of this section")
        return
    running = "aaaaaaaaaaaa"
    other = "ffffffffffff"

    r = H.detect_mesh_source_split(
        health=_health_fixture(running, {"phone:5001": other}, {"phone:5001": 12.5}))
    check("S1 a peer on another source is PRESENT",
          r["state"] == H.PRESENT and r["measured"]["drifted"] == ["phone:5001"],
          json.dumps(r["measured"])[:220])
    check("S1b and the finding carries how long ago that peer was heard",
          r["measured"].get("heard_s_ago") == {"phone:5001": 12.5},
          json.dumps(r["measured"].get("heard_s_ago")))

    r = H.detect_mesh_source_split(health=_health_fixture(running, {"phone:5001": running,
                                                                   "b:5021": running}))
    check("S2 a mesh that agrees is ABSENT -- the green is reachable",
          r["state"] == H.ABSENT and r["measured"]["drifted"] == [],
          json.dumps(r["measured"])[:200])

    # THE REFERENCE IS THE RUNNING MESH, NOT DISK. A peer matching what the
    # nodes RUN is agreement even when disk has moved on -- and disk always
    # moves on, so comparing to it would pin this PRESENT for ever.
    r = H.detect_mesh_source_split(health=_health_fixture(running, {"phone:5001": running}))
    check("S2b a peer that matches the RUNNING mesh is ABSENT even though "
          "disk has moved ahead of both",
          r["state"] == H.ABSENT and disk != running, f"disk={disk} running={running}")

    r = H.detect_mesh_source_split(health=_health_fixture(running, {}))
    check("S3 no peer reporting is UNKNOWN, never ABSENT (P20: unknown is not pass)",
          r["state"] == H.UNKNOWN and "why" in r["measured"], json.dumps(r["measured"])[:200])

    r = H.detect_mesh_source_split(health={"A": None, "B": {"http": 429}})
    check("S4 a mesh nobody could read is UNKNOWN, not a finding",
          r["state"] == H.UNKNOWN, json.dumps(r["measured"])[:200])

    r = H.detect_mesh_source_split(
        health=_health_fixture(running, {"phone:5001": other}))
    check("S5 the finding says no remedy belongs to this machine",
          "no remedy" in r["measured"].get("note", ""), r["measured"].get("note", "")[:120])

    # ---- R1-R3: the pairing that must NOT change -----------------------
    h = _health_fixture(disk, {"phone:5001": other})
    r = H.detect_source_drift(health=h)
    check("R1 a drifted PEER leaves source_drift ABSENT",
          r["state"] == H.ABSENT and r["measured"]["drifted"] == [],
          json.dumps(r["measured"])[:200])

    h2 = _health_fixture(other, {"phone:5001": disk})      # the LOCAL node drifted
    r = H.detect_source_drift(health=h2)
    check("R2 a drifted LOCAL node still makes source_drift PRESENT",
          r["state"] == H.PRESENT and r["measured"]["drifted"] == ["A"],
          json.dumps(r["measured"])[:200])

    paired = [k for k, v in H.REMEDIES.items() if "source_drift" in (v.get("for") or [])]
    check("R3 restart_nodes is still the remedy graded against source_drift alone",
          paired == ["restart_nodes"]
          and "mesh_source_split" not in (H.REMEDIES["restart_nodes"].get("for") or []),
          f"paired={paired}")

    check("S6 the new detector is registered, so sense() actually runs it",
          H.DETECTORS.get("mesh_source_split") is H.detect_mesh_source_split,
          str(sorted(H.DETECTORS))[:160])


# -------------------------------------------------------- one namespace --
def namespace_checks():
    import covenant_unified_v8 as cov

    class FakeNode:
        """Only what resolve_peer_id touches: the peers table and its lock."""
        def __init__(self):
            import threading
            self.peers = {"peer_127.0.0.1_5021": ("127.0.0.1", 5021)}
            self.peers_lock = threading.Lock()
        resolve_peer_id = cov.P2PNode.resolve_peer_id

    n = FakeNode()
    outbound_key = n.resolve_peer_id("127.0.0.1", 5021) or "127.0.0.1:5021"
    inbound_key = n.resolve_peer_id("127.0.0.1", 5021) or "127.0.0.1:?"
    check("N1 both call sites compute the SAME key for one peer",
          outbound_key == inbound_key == "peer_127.0.0.1_5021",
          f"outbound={outbound_key} inbound={inbound_key}")

    t = cov.PeerStateTable()
    t.observe(outbound_key, {"v": "v8.40", "src": "aaaaaaaaaaaa", "height": 35})
    t.observe(inbound_key, {"v": "v8.40", "src": "aaaaaaaaaaaa", "height": 35})
    s = t.summary()
    check("N2 a peer sent-to AND heard-from holds ONE row, not two",
          s["tracked"] == 1 and s["by_source"] == {"aaaaaaaaaaaa": ["peer_127.0.0.1_5021"]},
          json.dumps(s)[:200])

    # BROKEN ON PURPOSE: the pre-fix behaviour, so the green above is earned.
    t2 = cov.PeerStateTable()
    t2.observe("127.0.0.1:5021", {"v": "v8.40", "src": "aaaaaaaaaaaa"})
    t2.observe("peer_127.0.0.1_5021", {"v": "v8.40", "src": "aaaaaaaaaaaa"})
    s2 = t2.summary()
    check("N3 and the OLD two-namespace pattern still doubles the count "
          "(so N2 is measuring something)",
          s2["tracked"] == 2 and len(s2["by_source"]["aaaaaaaaaaaa"]) == 2,
          json.dumps(s2)[:200])

    # An unknown peer must still be recordable: resolve_peer_id returns None
    # for a host that is not in the table, and the fallback has to hold.
    unknown = n.resolve_peer_id("10.0.0.9", 5001) or "10.0.0.9:5001"
    check("N1b a peer not in the table still gets a key, via the fallback",
          unknown == "10.0.0.9:5001", unknown)


# ------------------------------------------------------------ the age --
def age_checks():
    import covenant_unified_v8 as cov

    t = cov.PeerStateTable()
    t.observe("p:1", {"v": "v8.40", "src": "aaaaaaaaaaaa"})
    s = t.summary()
    check("A1 summary carries how long ago each peer was heard",
          isinstance(s.get("heard_s_ago"), dict) and "p:1" in s["heard_s_ago"]
          and 0 <= s["heard_s_ago"]["p:1"] < 5, json.dumps(s.get("heard_s_ago"))[:120])

    # Backdate the row by an hour and read the age again.
    with t._lock:
        t._rows["p:1"]["seen"] = time.time() - 3600
    s = t.summary()
    check("A2 a stale reading reports as stale, not as fresh",
          3590 <= s["heard_s_ago"]["p:1"] <= 3610, str(s["heard_s_ago"]))

    check("A3 tracked and by_source keep the shape test_a20 C4b/H1 reads",
          s["tracked"] == 1 and s["by_source"] == {"aaaaaaaaaaaa": ["p:1"]},
          json.dumps({k: v for k, v in s.items() if k != "heard_s_ago"}))

    t2 = cov.PeerStateTable()
    t2.observe("q:1", {"height": 5})            # a v8.32 reply: no src, no v
    s2 = t2.summary()
    check("A3b a peer that cannot say its source is still aged, and still "
          "invisible to the split",
          s2["by_source"] == {} and s2["tracked"] == 1 and "q:1" in s2["heard_s_ago"],
          json.dumps(s2)[:160])


# ----------------------------------------------------------------- live --
def live_checks():
    import urllib.error
    import urllib.request

    try:
        with urllib.request.urlopen("http://127.0.0.1:5000/health", timeout=8) as r:
            h = json.loads(r.read().decode())
    except (urllib.error.URLError, OSError, ValueError, TimeoutError) as e:
        not_run("L1-L2 what node A reports right now",
                f"no node answering on 127.0.0.1:5000 ({type(e).__name__}) -- "
                f"this suite is run in a staging dir with no mesh, and that is "
                f"not a failure")
        return

    mesh = h.get("mesh") or {}
    tracked, by_src = mesh.get("tracked"), mesh.get("by_source") or {}
    named = sorted({w for ws in by_src.values() for w in ws})
    check("L1 no peer is double-counted under two spellings",
          len(named) == len({w.replace("peer_", "").replace("_", ":") for w in named}),
          f"tracked={tracked} named={named}")
    check("L2 the live mesh view carries the age of each reading",
          isinstance(mesh.get("heard_s_ago"), dict),
          json.dumps(mesh.get("heard_s_ago"))[:200])


def main():
    print("H2 -- the update door's witness, and a peer's drift made visible\n")
    witness_checks()
    split_checks()
    namespace_checks()
    age_checks()
    live_checks()
    ok = sum(1 for _, o, _ in results if o)
    print(f"\n{ok}/{len(results)} passed")
    if UNRUN:
        print(f"{len(UNRUN)} section(s) NOT RUN -- do not read this as covered:")
        for n, why in UNRUN:
            print(f"  - {n}: {why}")
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
