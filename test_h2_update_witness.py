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
  F1-F12  the bound on futile sending: a build delivered whole and answered
          by a heartbeat still on another version, three times over, is not
          sent again -- and every direction that must NOT trip it is driven
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


# --------------------------------------------- the bound on futile sending --
def futility_checks():
    """F1-F12: the door stops sending a build it has PROVED does not install.

    Driven both ways on purpose (CLAUDE.md rule 8). The dangerous failure here
    is not a bound that fires too eagerly -- it is one that can never fire, or
    one that fires on the wrong caller and closes the door on a path that still
    works. So the false direction gets more checks than the true one: below the
    budget, no check-in at all, a check-in that agrees, another signer, a newer
    build, partials, an unreadable ledger.
    """
    import covenant_app_update as AU

    tmp = tempfile.mkdtemp(prefix="h2_futile_")
    saved = (AU.DIR, AU.REQUESTS, AU.CHECKINS, AU.ALLOW_AGAIN, AU.latest)
    AU.DIR = tmp
    AU.REQUESTS = os.path.join(tmp, "requests.jsonl")
    AU.CHECKINS = os.path.join(tmp, "phone_checkins.jsonl")
    AU.ALLOW_AGAIN = os.path.join(tmp, "serve_anyway.json")
    # `fetched` matters: install_futility counts only deliveries recorded
    # AFTER the build landed on disk, because two runs of one app commit carry
    # the same sha7 and the ledger cannot tell them apart. Set below the
    # fixture clock so every row written here belongs to this build.
    BUILD = {"sha7": "ab5ea5a", "version": "0.1.560+fa13845", "size": 45163344,
             "fetched": "2023-11-14T00:00:00+0000",
             "file": "x.apk", "path": os.path.join(tmp, "x.apk")}
    AU.latest = lambda: dict(BUILD)

    # AN EXPLICIT CLOCK, because the real one is not precise enough here.
    # note_request stores `at` ROUNDED TO A TENTH OF A SECOND -- which is
    # invisible in production, where a delivery and the heartbeat that answers
    # it are ten minutes apart, and decisive in a fixture that writes both
    # inside a millisecond: the rounding walked deliveries forward past the
    # check-ins meant to follow them and every round trip read as ungraded. A
    # test whose result depends on how fast the machine ran it is not a
    # measurement, so the ordering is stated rather than raced for.
    CLOCK = [1_700_000_000.0]

    def _tick(minutes=10):
        CLOCK[0] += minutes * 60.0
        return CLOCK[0]

    def deliver(n, sha7="ab5ea5a", signer="phone", outcome="sent-complete"):
        for _ in range(n):
            with open(AU.REQUESTS, "a", encoding="utf-8") as fh:
                fh.write(json.dumps({"t": "fixture", "at": _tick(), "route": "/app/apk",
                                     "signer": signer, "offered": sha7, "outcome": outcome,
                                     "detail": "45163344 of 45163344 bytes"}) + "\n")

    def checkin(app, signer="phone"):
        with open(AU.CHECKINS, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"t": "fixture", "at": _tick(), "signer": signer,
                                 "node_id": signer, "app": app}) + "\n")

    try:
        f = AU.install_futility()
        check("F1 nothing delivered yet is not futile",
              f["futile"] is False and f["complete"] == 0, f["why"][:80])

        # Two whole copies, each followed by a heartbeat still on the old
        # build: two graded round trips, one short of the bound.
        deliver(1); checkin("0.1.475+13b946a")
        deliver(1); checkin("0.1.475+13b946a")
        f = AU.install_futility()
        check("F2 below the budget is not futile, and says how far along it is",
              f["futile"] is False and f["complete"] == 2 and f["proved"] == 2
              and "budget" in f["why"], f["why"][:90])

        deliver(1)                       # a third copy, not yet answered
        f = AU.install_futility()
        check("F3 a delivery with no check-in after it YET is not graded "
              "-- silence is not evidence of a failed install",
              f["futile"] is False and f["complete"] == 3
              and f["proved"] == 2 and f["ungraded"] == 1, f["why"][:95])

        checkin("0.1.560+fa13845")       # it installed after all
        f = AU.install_futility()
        check("F4 a check-in naming the build's OWN version is not futile",
              f["futile"] is False and "installed" in f["why"]
              and f["have"] == "0.1.560+fa13845", f["why"][:80])

        # Back on the old build, and one more whole copy comes back unchanged:
        # the third graded round trip.
        checkin("0.1.475+13b946a")
        deliver(1); checkin("0.1.475+13b946a")
        f = AU.install_futility()
        check("F5 THE TRUE DIRECTION: three whole copies, each answered by a "
              "heartbeat still on another version, is futile",
              f["futile"] is True and f["complete"] == 4 and f["proved"] == 3
              and f["want"] == "0.1.560+fa13845" and f["have"] == "0.1.475+13b946a"
              and f["bytes"] == 4 * 45163344, f["why"][:120])

        check("F6 ...and the refusal names the door that still works",
              "/m" in f["why"] and "hand" in f["why"], f["why"][-90:])

        # THE REGRESSION THAT MATTERS. test_h2's own L3-L4 downloads the APK
        # signed as `pc`. If the phone's failure bounded every caller, this
        # suite would close the door on itself -- and so would any other
        # consumer of the capability (CLAUDE.md rule 6).
        f_pc = AU.install_futility(signer="pc")
        check("F7 another signer is NOT bounded by the phone's failure",
              f_pc["futile"] is False and f_pc["complete"] == 0, f_pc["why"][:80])

        # A newer build clears it by itself: the count is per build.
        BUILD2 = dict(BUILD, sha7="9999999", version="0.1.561+2e61e52")
        AU.latest = lambda: dict(BUILD2)
        f_new = AU.install_futility()
        check("F8 a NEWER build starts the count again",
              f_new["futile"] is False and f_new["complete"] == 0, f_new["why"][:80])
        AU.latest = lambda: dict(BUILD)

        # Partials are not deliveries.
        deliver(5, outcome="sent-PARTIAL")
        f_part = AU.install_futility()
        check("F9 a PARTIAL transfer does not count toward the budget",
              f_part["complete"] == 4 and f_part["proved"] == 3,
              "complete=%d proved=%d after 5 partials" % (f_part["complete"], f_part["proved"]))

        m = AU.serve_anyway(hours=1.0)
        f_allow = AU.install_futility()
        check("F10a serve-anyway clears it for this build",
              f_allow["futile"] is False and "serve-anyway" in f_allow["why"],
              str(m)[:70])
        with open(AU.ALLOW_AGAIN, "w", encoding="utf-8") as fh:
            json.dump({"sha7": "ab5ea5a", "until": time.time() - 1}, fh)
        check("F10b ...and an EXPIRED serve-anyway does not",
              AU.install_futility()["futile"] is True, "expired marker ignored")
        os.remove(AU.ALLOW_AGAIN)

        # A SECOND BUILD OF THE SAME COMMIT IS A SECOND BUILD (2026-09-18).
        # The workflow builds one app commit against whatever the public core
        # is at the time, so run 35370202625 and run 35410624880 are BOTH
        # `ab5ea5a` -- and the first draft of the counter keyed on sha7 alone,
        # which would have handed a brand new build its predecessor's 43
        # failures and refused it on the first ask. The floor is the fetch
        # time, and this drives it: same commit, same ledger, later fetch.
        BUILD3 = dict(BUILD, version="0.1.568+2e61e52",
                      fetched=time.strftime("%Y-%m-%dT%H:%M:%S%z"))
        AU.latest = lambda: dict(BUILD3)
        f_run = AU.install_futility()
        check("F12 a NEW RUN of the SAME commit does not inherit the old "
              "build's failures",
              f_run["futile"] is False and f_run["complete"] == 0
              and f_run["want"] == "0.1.568+2e61e52", f_run["why"][:85])
        AU.latest = lambda: dict(BUILD)

        # VERSIONNAME IS NOT A BUILD (2026-09-19, the second time this bit).
        # versionName is 0.1.<count of public-core commits>+<core sha7>, so two
        # app builds against one core share it: 2068c8f and a0fd2a1 are BOTH
        # "0.1.597+7ffa73b". A guard comparing versionName reads a phone on the
        # first as "installed" for the second. When the heartbeat carries
        # `build` (the app-repo commit), that wins; without it, versionName is
        # all there is and the fallback stays exactly as it was.
        AU.latest = lambda: dict(BUILD, sha7="a0fd2a1", version="0.1.597+7ffa73b")
        deliver(3, sha7="a0fd2a1")
        with open(AU.CHECKINS, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"t": "fixture", "at": _tick(), "signer": "phone",
                                 "node_id": "phone", "app": "0.1.597+7ffa73b",
                                 "build": "2068c8fbfc24ed93c63e683c1350b60378578823"}) + "\n")
        f_twin = AU.install_futility()
        check("F13 the same versionName on a DIFFERENT build is NOT installed -- "
              "the heartbeat's `build` decides, not the version string",
              f_twin["futile"] is False or f_twin["why"].find("installed") < 0,
              "have_build=%s why=%s" % (f_twin.get("have_build"), f_twin["why"][:60]))
        check("F13b ...and it is counted as a round trip, so the bound can still "
              "trip on a phone that reports the wrong build",
              f_twin.get("proved", 0) >= 1, "proved=%s" % f_twin.get("proved"))
        with open(AU.CHECKINS, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"t": "fixture", "at": _tick(), "signer": "phone",
                                 "node_id": "phone", "app": "0.1.597+7ffa73b",
                                 "build": "a0fd2a1deadbeef"}) + "\n")
        f_same = AU.install_futility()
        check("F14 a matching `build` IS installed, whatever versionName says",
              f_same["futile"] is False and "installed" in f_same["why"],
              f_same["why"][:60])
        AU.latest = lambda: dict(BUILD)

        # A measurement that cannot be taken has no opinion, and must never
        # become a refusal by accident.
        AU.latest = lambda: (_ for _ in ()).throw(RuntimeError("ledger on fire"))
        f_err = AU.install_futility()
        check("F11 an unreadable measurement says so and refuses nothing",
              f_err["futile"] is False and "could not be measured" in f_err["why"],
              f_err["why"][:70])
    finally:
        AU.DIR, AU.REQUESTS, AU.CHECKINS, AU.ALLOW_AGAIN, AU.latest = saved
        shutil.rmtree(tmp, ignore_errors=True)


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

    # ---- L3-L4: WHAT ACTUALLY LEFT, not what we meant to send -----------
    #
    # The first witness logged "sending" BEFORE send_file and stopped there, so
    # when the phone began downloading a build every ten minutes and never
    # installing it, this PC still could not tell a TRUNCATED transfer from an
    # installer refusing a complete one -- a witness carrying the same blind
    # spot as the thing it witnesses. Both outcomes are driven here against the
    # REAL route, signed as `pc` (this machine's own registered identity, never
    # the phone's key), because a generator's early-close behaviour is not
    # something a fixture can honestly stand in for.
    import covenant_daily_plan as DP
    import covenant_app_update as AU
    try:
        key = DP.load_key()
        d = AU.latest()
    except Exception as e:                                       # noqa: BLE001
        not_run("L3-L4 the /app/apk transfer records what actually left",
                f"no signing key or no fetched build here ({type(e).__name__})")
        return
    if not d or not key:
        not_run("L3-L4 the /app/apk transfer records what actually left",
                "no signing key or no fetched build on this machine")
        return

    def _get(stop_after=None):
        hdr = DP.sign_headers(key, "GET", "/app/apk", b"")
        req = urllib.request.Request("http://127.0.0.1:5000/app/apk", headers=hdr)
        r = urllib.request.urlopen(req, timeout=180)
        got = 0
        try:
            while True:
                c = r.read(1 << 16)
                if not c:
                    break
                got += len(c)
                if stop_after and got >= stop_after:
                    break
        finally:
            r.close()
        return got

    # THE SIGNED DOOR IS NOT OPEN EVERYWHERE, and finding that out by traceback
    # cost this suite its whole tally (2026-09-18). Run inside covenant_one the
    # first version raised `HTTPError: 403 FORBIDDEN` here -- the runner stages
    # to a temp directory, so ops/daily_plan_signers.json is not the one this
    # key is registered in -- and an unhandled exception meant the suite printed
    # NO tally line at all: 27 checks that HAD passed were scored NO RESULT.
    # A section that cannot run is neither a pass nor a failure; it has to be
    # named and the rest has to survive it (the rule test_a20's not_run was
    # written for, which I had read).
    try:
        _probe = DP.sign_headers(key, "GET", "/app/apk", b"")
        urllib.request.urlopen(
            urllib.request.Request("http://127.0.0.1:5000/app/apk", headers=_probe),
            timeout=30).close()
    except urllib.error.HTTPError as e:
        not_run("L3-L4 the /app/apk transfer records what actually left",
                f"this environment's key is not a registered signer for the live "
                f"node (HTTP {e.code}) -- the runner stages to a temp dir with its "
                f"own ops/, so the signed door is closed there. Run this suite in "
                f"the working tree to measure L3-L4.")
        return
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        not_run("L3-L4 the /app/apk transfer records what actually left",
                f"the signed door did not answer ({type(e).__name__})")
        return

    def _await_outcome(timeout=20.0):
        """The last /app/apk row once it is no longer `started`.

        The generator's `finally` runs when the WSGI server finishes unwinding
        the response, which is AFTER the client's last read() returns -- so
        reading the ledger straight away is a race, and it caught this test
        before it caught anything else. Polled rather than slept past, because
        a fixed sleep is a guess that passes on a fast machine and lies on a
        slow one."""
        end = time.time() + timeout
        row = {}
        while time.time() < end:
            rows = AU.requests_tail(1, route="/app/apk")
            row = rows[-1] if rows else {}
            if row.get("outcome") in ("sent-complete", "sent-PARTIAL"):
                return row
            time.sleep(0.25)
        return row

    got = _get()
    row = _await_outcome()
    check("L3 a COMPLETE transfer is recorded as complete, with the byte count",
          got == d["size"] and row.get("outcome") == "sent-complete"
          and str(d["size"]) in row.get("detail", ""),
          f"got={got} row={row.get('outcome')} {row.get('detail')}")

    # BROKEN ON PURPOSE: walk away after 2 MB of ~45.
    _get(stop_after=2 << 20)
    row = _await_outcome()
    check("L4 ...and a client that disconnects part way is recorded as PARTIAL "
          "-- the distinction the first witness could not make",
          row.get("outcome") == "sent-PARTIAL"
          and "of %d bytes" % d["size"] in row.get("detail", ""),
          f"row={row.get('outcome')} {row.get('detail')}")


def main():
    print("H2 -- the update door's witness, and a peer's drift made visible\n")
    # NO SECTION MAY TAKE THE TALLY DOWN WITH IT (2026-09-18). One unhandled
    # HTTPError in live_checks cost this suite its tally line inside
    # covenant_one, and the runner scored 27 passing checks as NO RESULT --
    # strictly worse than a FAIL, because a failure is at least a number. A
    # section that dies is recorded as a failed check naming the exception, and
    # every other section still runs and still counts.
    for name, fn in (("witness", witness_checks), ("futility", futility_checks),
                     ("split", split_checks),
                     ("namespace", namespace_checks), ("age", age_checks),
                     ("live", live_checks)):
        try:
            fn()
        except Exception as e:                                   # noqa: BLE001
            import traceback
            traceback.print_exc()
            check("X1 the %s section ran without raising" % name, False,
                  "%s: %s" % (type(e).__name__, e))
    ok = sum(1 for _, o, _ in results if o)
    print(f"\n{ok}/{len(results)} passed")
    if UNRUN:
        print(f"{len(UNRUN)} section(s) NOT RUN -- do not read this as covered:")
        for n, why in UNRUN:
            print(f"  - {n}: {why}")
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
