#!/usr/bin/env python3
"""
test_a465_mesh_split_who.py -- A465 (2026-11-21): on a machine with a profile, the mesh checks are handed that
machine's OWN node's health by every profiled reader, and mesh_source_split says which side is the one on disk and
what its count is a count of.

WHAT WAS MEASURED (the second PC, node D only, after A464 was live there). The watchdog's pass hands node D's
health in by hand and read mesh_source_split PRESENT. The same node's GET /hwy/state, the same minute, read it
UNKNOWN: sense() gives a machine whose profile marks node_down as not applying an EMPTY health, so the page, the
orb page and the heal button could not see a split that was there. And the detector's own answer said "drifted:
7 names" for 3 nodes: each of the first PC's nodes is filed twice (its address and a relay port), and one name was
the second PC's own address with no port, traffic that arrived through its relay. It did not say which of the
two sources is the one on this disk.

WHAT THIS DRIVES, both ways. No node is asked: covenant_highway._get and ._health are stand-ins for the whole
suite, and apply_remedy is replaced by a function that fails the suite if it is ever entered.
  P  machine_profile(): "own_nodes" {id: loopback port}; a wrong shape makes the whole profile unreadable (every
     detector applies, nothing acts); the home profile and a file without it are exactly as before.
  S  sense(): with node_down not applying and own_nodes given, the detectors are handed {id: health} read from
     127.0.0.1:<port>/health and nowhere else; the three answers of _health() are kept (a dict, {"http": code},
     None); without own_nodes the health is empty as before; a machine where node_down applies asks as before.
  R  report(): on such a machine mesh_source_split is measured instead of UNKNOWN.
  M  detect_mesh_source_split(): the old keys keep their exact values; by_source, unmapped, disk, ours_is_disk,
     unit and summary are added.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import urllib.error

import covenant_highway as H

results = []
A, B = "a" * 12, "b" * 12


def check(label, ok, detail=""):
    results.append((label, bool(ok)))
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}" + (f"  -- {detail}" if detail else ""))


def call(fn, *a, **k):
    try:
        return fn(*a, **k), None
    except Exception as e:                                        # noqa: BLE001
        return None, "%s: %s" % (type(e).__name__, str(e)[:140])


def main():
    os.environ["COVENANT_HIGHWAY_LAST_SENSE"] = tempfile.mktemp(suffix="_a465_last_sense.json")
    work = tempfile.mkdtemp(prefix="a465_")
    asked, home_asked, old_get = [], [], []
    answers = {}

    def fake_get(url, timeout=6, deadline=None):
        asked.append(url)
        got = answers.get(url, OSError("refused"))
        if isinstance(got, Exception):
            raise got
        return got

    def no_remedy(*a, **k):
        raise AssertionError("A465: a remedy was entered; this suite only senses")

    def profile_file(body, name="machine.json"):
        p = os.path.join(work, name)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(body if isinstance(body, str) else json.dumps(body))
        return p

    real = {n: getattr(H, n, None) for n in ("_get", "_get_own", "_health", "apply_remedy", "OWN_HEALTH_MAX", "OWN_HEALTH_BUDGET_S")}
    real_detectors = dict(H.DETECTORS)
    import covenant_watchdog as W
    real_disk = W.disk_source_sha12
    try:
        H._get_own, H.apply_remedy = fake_get, no_remedy
        H._get = lambda *a, **k: (old_get.append(a), {})[1]      # the home nodes' reader: never used for an own node
        H._health = lambda: home_asked.append(1) or {}
        W.disk_source_sha12 = lambda: A

        # ---- P: the profile
        base = {"acts_here": False, "why": "a second PC: sensing only",
                "not_applicable": {"node_down": "this PC hosts node D only"}}
        prof = H.machine_profile(path=profile_file(dict(base, own_nodes={"D": 15080})))
        check("A465.P1 a profile may name this machine's own node by a loopback port",
              prof.get("own_nodes") == {"D": 15080} and prof.get("source") == "file", str(prof.get("own_nodes")))
        home = H.machine_profile(path=os.path.join(work, "no-such-file.json"))
        check("A465.P2 the home profile is exactly what it was: no new key",
              home == {"acts_here": True, "not_applicable": {}, "why": "", "source": "none", "refused": [], "sha": ""},
              str(sorted(home)))
        plain = H.machine_profile(path=profile_file(base, "plain.json"))
        check("A465.P2 ...and so is a file that names no own node",
              "own_nodes" not in plain and plain["not_applicable"] == base["not_applicable"], str(sorted(plain)))
        for label, bad in (("a port as text", {"D": "15080"}), ("port 0", {"D": 0}), ("a port past 65535", {"D": 70000}),
                           ("True for a port", {"D": True}), ("an address instead of a port", {"D": "http://192.0.2.7/health"}),
                           ("a list", ["D"]), ("an id with a slash", {"../D": 15080}), ("an empty id", {"": 15080}),
                           ("nine nodes", {"N%d" % i: 15080 + i for i in range(9)})):
            got, err = call(H.machine_profile, path=profile_file(dict(base, own_nodes=bad), "bad.json"))
            got = got or {}                # a profile reader that RAISES on a bad file is a failure of this check
            check("A465.P3 own_nodes with %s: the whole profile is unreadable, so nothing is hidden and nothing acts" % label,
                  err is None and got.get("source") == "unreadable" and got.get("acts_here") is False
                  and got.get("not_applicable") == {} and "own_nodes" not in got,
                  err or json.dumps({k: got.get(k) for k in ("source", "acts_here", "own_nodes")}))

        # ---- S: what sense() hands the detectors
        seen = {}

        def keep(name):
            def fn(health=None, **kwargs):
                seen[name] = health
                return {"state": H.ABSENT, "measured": {"fixture": name}}
            return fn
        H.DETECTORS.clear()
        H.DETECTORS.update({"node_down": keep("node_down"), "a465_reader": keep("a465_reader")})
        d_health = {"source_sha256": A + "ffff", "mesh": {"by_source": {B: ["peer_192.0.2.1_5001"]}, "heard_s_ago": {}}}
        answers["http://127.0.0.1:15080/health"] = d_health
        del asked[:], home_asked[:]
        _, err = call(H.sense, machine=prof)
        check("A465.S1 with node_down not applying and an own node named, the detectors are handed that node's health",
              err is None and seen.get("a465_reader") == {"D": d_health}, err or json.dumps(seen.get("a465_reader"))[:120])
        check("A465.S1 ...read from this machine's loopback, that port, /health, and nowhere else",
              asked == ["http://127.0.0.1:15080/health"] and not home_asked and not old_get, str(asked) + str(home_asked) + str(old_get))
        check("A465.S1 ...and the detector that does not apply is still not entered", "node_down" not in seen, str(sorted(seen)))

        seen.clear()
        del asked[:], home_asked[:]
        _, err = call(H.sense, machine=plain)
        check("A465.S2 mutation: the same machine with no own node named gets the empty health it always got",
              err is None and seen.get("a465_reader") == {} and not asked and not home_asked, err or str(seen.get("a465_reader")))

        seen.clear()
        del asked[:], home_asked[:]
        applies = H.machine_profile(path=profile_file({"acts_here": False, "why": "w", "own_nodes": {"D": 15080},
                                                       "not_applicable": {"a465_other": "elsewhere"}}, "applies.json"))
        _, err = call(H.sense, machine=applies)
        check("A465.S3 a machine where node_down APPLIES asks for the home nodes as before; own_nodes is not read",
              err is None and home_asked == [1] and not asked, err or str(asked) + str(home_asked))

        seen.clear()
        del asked[:], home_asked[:]
        _, err = call(H.sense, machine=prof, health={"X": {"given": True}})
        check("A465.S4 a health the caller hands in is used as given: nothing is asked",
              err is None and seen.get("a465_reader") == {"X": {"given": True}} and not asked and not home_asked,
              err or str(asked))

        two = H.machine_profile(path=profile_file(dict(base, own_nodes={"D": 15080, "E": 15081, "F": 15082}), "two.json"))
        answers["http://127.0.0.1:15081/health"] = urllib.error.HTTPError("u", 429, "slow down", {}, None)
        seen.clear()
        del asked[:]
        _, err = call(H.sense, machine=two)
        got = seen.get("a465_reader") or {}
        check("A465.S5 the three answers are kept: a dict, {'http': code} for a node that answered with an error, None for no answer",
              err is None and got.get("D") == d_health and got.get("E") == {"http": 429} and "F" in got and got.get("F") is None,
              err or json.dumps(got, default=str)[:160])

        # whatever answers on the port must be the node the file names: another node's answer is no answer from this one
        answers["http://127.0.0.1:15080/health"] = dict(d_health, node_id="Z")
        seen.clear()
        _, err = call(H.sense, machine=prof)
        got = seen.get("a465_reader") or {}
        check("A465.S6 an answer on that port that names ANOTHER node is read as no answer from the node the file names",
              err is None and "D" in got and got.get("D") is None, err or json.dumps(got, default=str)[:120])
        answers["http://127.0.0.1:15080/health"] = dict(d_health, node_id="D")
        seen.clear()
        _, err = call(H.sense, machine=prof)
        check("A465.S6 mutation: the same answer naming THIS node is taken",
              err is None and (seen.get("a465_reader") or {}).get("D") == dict(d_health, node_id="D"), err or "")
        answers["http://127.0.0.1:15080/health"] = ["not", "a", "health"]
        seen.clear()
        _, err = call(H.sense, machine=prof)
        got = seen.get("a465_reader") or {}
        check("A465.S7 an answer that is not an object is no answer", err is None and "D" in got and got.get("D") is None,
              err or json.dumps(got, default=str)[:120])
        answers["http://127.0.0.1:15080/health"] = d_health

        # ---- M: the detector's own answer
        health = {"D": {"source_sha256": A + "ffff", "mesh": {
            "by_source": {B: ["192.0.2.9:?", "peer_127.0.0.1_15001", "peer_192.0.2.1_5001"], A: ["peer_192.0.2.2_5001"]},
            "heard_s_ago": {"192.0.2.9:?": 5.0, "peer_127.0.0.1_15001": 7.5, "peer_192.0.2.1_5001": 9.0, "peer_192.0.2.2_5001": 3.0}}}}
        out = H.detect_mesh_source_split(health=health)
        m = out.get("measured") or {}
        check("A465.M1 the answer's old keys keep their exact values",
              out.get("state") == H.PRESENT and m.get("running") == [A]
              and m.get("drifted") == ["192.0.2.9:?", "peer_127.0.0.1_15001", "peer_192.0.2.1_5001"]
              and m.get("peers", {}).get("peer_192.0.2.2_5001") == A
              and m.get("heard_s_ago") == {"192.0.2.9:?": 5.0, "peer_127.0.0.1_15001": 7.5, "peer_192.0.2.1_5001": 9.0}
              and "no remedy" in m.get("note", ""), json.dumps(m)[:200])
        check("A465.M2 it says which names report which source",
              m.get("by_source") == {A: ["peer_192.0.2.2_5001"], B: ["192.0.2.9:?", "peer_127.0.0.1_15001", "peer_192.0.2.1_5001"]},
              json.dumps(m.get("by_source")))
        check("A465.M3 a name with no port is an unmapped sender, listed apart (and still counted in drifted)",
              m.get("unmapped") == ["192.0.2.9:?"], str(m.get("unmapped")))
        check("A465.M4 it says which source is the one on this disk, and that this machine runs it",
              m.get("disk") == A and m.get("ours_is_disk") is True, "%s %s" % (m.get("disk"), m.get("ours_is_disk")))
        s = m.get("summary") or ""
        check("A465.M5 a plain summary: who runs what, the counts, and the unit",
              A in s and B in s and "on disk" in s and "2 peer name" in s and "1 unmapped sender" in s and "not nodes" in s, s)
        check("A465.M5 ...and the unit is a key of its own", "peer names" in (m.get("unit") or ""), str(m.get("unit")))

        W.disk_source_sha12 = lambda: B
        m2 = H.detect_mesh_source_split(health=health).get("measured") or {}
        check("A465.M6 mutation: when the disk holds the OTHER source, it says this machine does not run the one on disk",
              m2.get("disk") == B and m2.get("ours_is_disk") is False and "not the source on disk" in (m2.get("summary") or ""),
              m2.get("summary") or "")

        def boom():
            raise OSError("no disk reading")
        W.disk_source_sha12 = boom
        out3 = H.detect_mesh_source_split(health=health)
        m3 = out3.get("measured") or {}
        check("A465.M7 a disk that cannot be read changes nothing but the two disk keys: the state stands",
              out3.get("state") == H.PRESENT and "disk" in m3 and m3.get("disk") is None and m3.get("ours_is_disk") is None
              and m3.get("drifted") == m.get("drifted"), json.dumps({k: m3.get(k) for k in ("disk", "ours_is_disk")}))

        W.disk_source_sha12 = lambda: A
        same = {"D": {"source_sha256": A, "mesh": {"by_source": {A: ["peer_192.0.2.2_5001"]}, "heard_s_ago": {}}}}
        out4 = H.detect_mesh_source_split(health=same)
        check("A465.M8 one source everywhere is ABSENT, and the summary says one source",
              out4.get("state") == H.ABSENT and out4["measured"].get("drifted") == []
              and "one source" in (out4["measured"].get("summary") or ""), out4["measured"].get("summary") or "")
        none_local = H.detect_mesh_source_split(health={})
        no_peers = H.detect_mesh_source_split(health={"D": {"source_sha256": A, "mesh": {"by_source": {}, "heard_s_ago": {}}}})
        check("A465.M9 the two UNKNOWN answers say why, as before",
              none_local.get("state") == H.UNKNOWN and "no local node" in none_local["measured"].get("why", "")
              and no_peers.get("state") == H.UNKNOWN and "no peer" in no_peers["measured"].get("why", ""),
              json.dumps(none_local["measured"])[:80])

        # ---- R: the page's function, on a machine with a profile
        H.DETECTORS.clear()
        H.DETECTORS.update({"node_down": keep("node_down"), "mesh_source_split": H.detect_mesh_source_split})
        answers["http://127.0.0.1:15080/health"] = health["D"]
        led = os.path.join(work, "highway.jsonl")
        rep, err = call(H.report, node_id="D", ledger=led, machine=prof)
        check("A465.R1 report() on a profiled machine with its own node named MEASURES the split (it read UNKNOWN before)",
              err is None and ((rep or {}).get("conditions") or {}).get("mesh_source_split") == H.PRESENT,
              err or json.dumps((rep or {}).get("conditions")))
        rep2, err = call(H.report, node_id="D", ledger=led, machine=plain)
        check("A465.R2 mutation: with no own node named it is UNKNOWN, as before",
              err is None and ((rep2 or {}).get("conditions") or {}).get("mesh_source_split") == H.UNKNOWN,
              err or json.dumps((rep2 or {}).get("conditions")))
        check("A465.R3 the report still sends state words only: no peer name, address or source leaves in it",
              "192.0.2" not in json.dumps(rep or {}) and B not in json.dumps(rep or {}), json.dumps(rep or {})[:160])

        # ---- N: the own-node reader itself, against throwaway servers on this machine (an outside read, 2026-11-21:
        # the first form used the shared _get, which follows a redirect, obeys a proxy, reads without a bound and
        # could be kept waiting for ever by a trickle; eight stalled nodes were 48 s).
        import http.server
        import threading
        import time as _t
        hits = {"away": 0}

        def serve(handler):
            srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            return srv

        class Quiet(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

        class Away(Quiet):
            def do_GET(self):
                hits["away"] += 1
                body = b'{"source_sha256": "from-elsewhere"}'
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
        away = serve(Away)

        class Local(Quiet):
            def do_GET(self):
                if self.path == "/health":
                    body = b'{"node_id": "D", "source_sha256": "abc"}'
                    self.send_response(200)
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                elif self.path == "/redirect":
                    self.send_response(302)
                    self.send_header("Location", "http://127.0.0.1:%d/health" % away.server_address[1])
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                elif self.path == "/big":
                    self.send_response(200)
                    self.send_header("Content-Length", "5000")
                    self.end_headers()
                    self.wfile.write(b'"' + b"x" * 4998 + b'"')
                elif self.path == "/trickle":
                    self.send_response(200)
                    self.end_headers()
                    try:
                        for _ in range(60):
                            self.wfile.write(b" ")
                            self.wfile.flush()
                            _t.sleep(0.1)
                    except OSError:
                        pass
        local = serve(Local)
        base_url = "http://127.0.0.1:%d" % local.server_address[1]
        own = real["_get_own"]
        check("A465.N0 the own-node reader exists and is not the shared _get", callable(own) and own is not real["_get"])
        if callable(own):
            got, err = call(own, base_url + "/health")
            check("A465.N1 it reads a health from this machine", err is None and got == {"node_id": "D", "source_sha256": "abc"}, err or str(got))
            got, err = call(own, base_url + "/redirect")
            check("A465.N2 a redirect is NOT followed: it is an answer with an error, and nothing was asked elsewhere",
                  got is None and "HTTPError" in (err or "") and "302" in (err or "") and hits["away"] == 0,
                  "%s | hits elsewhere: %d" % (err, hits["away"]))
            H.OWN_HEALTH_MAX = 1000
            got, err = call(own, base_url + "/big")
            check("A465.N3 an answer larger than the bound is refused, not read to the end",
                  got is None and "ValueError" in (err or ""), err or str(got)[:60])
            H.OWN_HEALTH_MAX = real["OWN_HEALTH_MAX"] or (1 << 20)
            began = _t.time()
            got, err = call(own, base_url + "/trickle", deadline=_t.time() + 0.5)
            took = _t.time() - began
            check("A465.N4 an answer that trickles is given up at the deadline, not waited for",
                  got is None and "TimeoutError" in (err or "") and took < 3.0, "%s after %.1f s" % (err, took))
            old_proxy = {k: os.environ.get(k) for k in ("http_proxy", "HTTP_PROXY")}
            try:
                os.environ["http_proxy"] = os.environ["HTTP_PROXY"] = "http://127.0.0.1:%d" % away.server_address[1]
                got, err = call(own, base_url + "/health")
                check("A465.N5 a proxy in the environment is not used for this machine's own node",
                      err is None and got == {"node_id": "D", "source_sha256": "abc"} and hits["away"] == 0,
                      "%s | hits at the proxy: %d" % (err or got, hits["away"]))
            finally:
                for k, v in old_proxy.items():
                    if v is None:
                        os.environ.pop(k, None)
                    else:
                        os.environ[k] = v
            # wired in: a redirecting port named in a profile is an answered error, and the mesh check is not told a source
            H._get_own = own
            redir = dict(prof, own_nodes={"D": local.server_address[1]})
            real_path = "http://127.0.0.1:%d/health" % local.server_address[1]
            got, err = call(H._own_health, redir)
            check("A465.N6 _own_health uses that reader: this machine's port answers through it",
                  err is None and (got or {}).get("D") == {"node_id": "D", "source_sha256": "abc"}, err or str(got) + real_path)
            H._get_own = fake_get
        for s in (local, away):
            s.shutdown()

        # ---- B: one sensing has a time budget for all own nodes together
        many = dict(prof, own_nodes={"N%d" % i: 15090 + i for i in range(8)})
        del asked[:]
        H.OWN_HEALTH_BUDGET_S = 0
        got, err = call(H._own_health, many)
        check("A465.B1 with the budget spent, the nodes left are no answer and are not asked",
              err is None and len(got or {}) == 8 and all(v is None for v in (got or {}).values()) and not asked,
              err or "%d asked" % len(asked))
        H.OWN_HEALTH_BUDGET_S = real["OWN_HEALTH_BUDGET_S"] or 10.0
        given = []
        H._get_own = lambda url, timeout=3.0, deadline=None: (given.append(deadline), {})[1]
        t_before = _t.time()
        call(H._own_health, many)
        check("A465.B2 every read is handed the same deadline, at most the budget away",
              len(given) == 8 and len(set(given)) == 1 and given[0] is not None
              and 0 < given[0] - t_before <= (real["OWN_HEALTH_BUDGET_S"] or 10.0) + 1, str(given[:2]))
        H._get_own = fake_get

        # ---- two older ways for hostile input to raise, closed here because own_nodes makes them easier to reach
        deep = profile_file('{"own_nodes":' + "[" * 10000 + "0" + "]" * 10000 + "}", "deep.json")
        got, err = call(H.machine_profile, path=deep)
        check("A465.P4 a profile nested ten thousand deep does not raise: it is unreadable, nothing hidden, nothing acts",
              err is None and (got or {}).get("source") == "unreadable" and (got or {}).get("acts_here") is False, err or str(got)[:80])
        for label, bad_mesh in (("a list for mesh", [1]), ("a list for by_source", {"by_source": [1]}),
                                ("text for heard_s_ago", {"by_source": {B: ["p"]}, "heard_s_ago": "soon"}),
                                ("a number for a name list", {"by_source": {B: 7}})):
            got, err = call(H.detect_mesh_source_split, health={"D": {"source_sha256": A, "mesh": bad_mesh}})
            check("A465.M10 a health with %s does not raise" % label,
                  err is None and (got or {}).get("state") in (H.UNKNOWN, H.PRESENT, H.ABSENT), err or str(got)[:80])
    finally:
        for n, fn in real.items():
            if fn is not None:
                setattr(H, n, fn)
        W.disk_source_sha12 = real_disk
        H.DETECTORS.clear()
        H.DETECTORS.update(real_detectors)

    failed = [n for n, ok in results if not ok]
    print(f"\nA465: {len(results) - len(failed)}/{len(results)} passed")
    if failed:
        print("FAILED: " + "; ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
