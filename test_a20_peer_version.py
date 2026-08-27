#!/usr/bin/env python3
"""A20/A21 (v8.33): nodes tell each other what they are, and a bounded digest.

WHY
---
A7 records that v8.17/v8.18 turned block size and three header derivations into
VALIDITY RULES: two nodes on different sources can disagree about what is a valid
block. Until now the only way to find that out was a rejected block after the
fact. P11 made a node self-describing to its OPERATOR; the peer handshake still
carried nothing.

Now every reply carries `v` and `src`, and the 120 s tip-gossip heartbeat carries
a bounded digest. The claim "this is backwards compatible" is not asserted here,
it is MEASURED against a real pristine v8.32 process, in both directions (C1-C5).

CHECKS
  V1-V3   every reply from a v8.33 node carries v and src, and they are true
  C1-C5   interop with a REAL pristine v8.32 process: it tolerates a v8.33 frame
          (digest and all), a v8.33 node tolerates its reply, and neither
          changes behaviour
  T1-T7   PeerStateTable coerces and bounds peer input, and records A7 mismatch
  D1-D5   THE DISGEST BOUNDARY: what the digest carries, and what it must never
          carry -- no substrate reading, no judge identity, no paths. Asserted
          over the built object AND over the frame actually put on the wire.
  D6      the digest rides the HEARTBEAT only, never a plain block announce
  H1-H3   /health carries the mesh view and warns on a split-source mesh

Node env needs BOTH COVENANT_INSECURE_MOCK_JUDGE=1 and
COVENANT_JUDGE_PROVIDERS=mock (M2). Ports picked at runtime.
"""
import atexit, json, os, shutil, socket, subprocess, sys, tempfile, time
import urllib.error, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
SRC = os.path.join(HERE, "covenant_unified_v8.py")
# A pre-A20 source to test interop against. The backup the delivery itself
# leaves behind (PRE-v8.33) is exactly that file, so on the machine that runs
# the node this needs no extra artefact -- which matters, because a
# compatibility test nobody can run where it counts is an assertion (M30).
_OLD_CANDIDATES = ("covenant_unified_v8.PRISTINE-v8.32.py",
                   "covenant_unified_v8.PRE-v8.33.py",
                   "covenant_unified_v8.PRE-v8.32.py")
OLD_SRC = next((os.path.join(HERE, c) for c in _OLD_CANDIDATES
                if os.path.exists(os.path.join(HERE, c))),
               os.path.join(HERE, _OLD_CANDIDATES[0]))
ENV = dict(os.environ, COVENANT_INSECURE_MOCK_JUDGE="1",
           COVENANT_JUDGE_PROVIDERS="mock")

import covenant_unified_v8 as cov

FIXED = hasattr(cov, "PeerStateTable")
TMP = tempfile.mkdtemp(prefix="covtest_a20_")
SPAWNED, results, UNRUN = [], [], []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}")


def not_run(name, why):
    """A third outcome, added 2026-08-24 (B2 run).

    C0 used to be a `check` that a FIXTURE FILE exists -- a property of the
    test directory, not of the system under test. On the one machine that had
    the artifact it was green; on every other machine it was red for ever
    (M34: a check that is always red is a check nobody reads) AND it silently
    took D1-D6 down with it, because `interop_checks` returned before the wire
    capture. So six real checks on what actually leaves the process were not
    running anywhere.

    A section that cannot run is neither a pass nor a failure. It is NAMED,
    printed, and counted in the summary, so a green sweep can never be read as
    "A20 fully verified" when half of it did not execute."""
    UNRUN.append((name, why))
    print(f"NOT RUN  {name}  -- {why}")


def stop(p, timeout=10):
    if p is None or p.poll() is not None:
        return
    try:
        p.terminate(); p.wait(timeout=timeout)
    except Exception:
        try:
            p.kill(); p.wait(timeout=5)
        except Exception:
            pass


def _reap():
    for p in SPAWNED:
        stop(p, timeout=5)
    shutil.rmtree(TMP, ignore_errors=True)


atexit.register(_reap)


def pick_base(span=14):
    for base in range(22400, 24000, 100):
        for off in range(span):
            s = socket.socket()
            try:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
                s.bind(("127.0.0.1", base + off))
            except OSError:
                s.close(); break
            s.close()
        else:
            return base
    raise SystemExit("no free port block")


def wait_api(port, timeout=45):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2)
            return True
        except urllib.error.HTTPError:
            return True
        except Exception:
            time.sleep(0.5)
    return False


def health(port):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=10) as r:
        return json.loads(r.read().decode())


def start(src, base, node_id, tag):
    p = subprocess.Popen([sys.executable, src, "--port", str(base),
                          "--node-id", node_id],
                         env=dict(ENV, COVENANT_DB_PATH=os.path.join(TMP, f"{tag}.db"),
                                  PYTHONUNBUFFERED="1"),
                         cwd=TMP, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True)
    SPAWNED.append(p)
    return p


def frame(p2p_port, payload, timeout=8):
    """Send one JSON frame to a real P2P listener and read the reply."""
    s = socket.socket()
    s.settimeout(timeout)
    s.connect(("127.0.0.1", p2p_port))
    s.sendall(json.dumps(payload).encode())
    s.shutdown(socket.SHUT_WR)
    buf = b""
    try:
        while True:
            chunk = s.recv(65536)
            if not chunk:
                break
            buf += chunk
    except Exception:
        pass
    s.close()
    return json.loads(buf.decode()) if buf else None


def announce_frame(genesis_hash, with_digest, p2p_port_of_sender):
    ev = {"type": "BLOCK_ANNOUNCE", "index": 0, "hash": genesis_hash,
          "gossip": True, "p2p_port": p2p_port_of_sender}
    if with_digest:
        ev["digest"] = {"v": "v8.33", "src": "deadbeefcafe", "height": 7,
                        "peers": 2, "crisis": False, "spike": ["x"]}
    return ev


# --------------------------------------------------------------- table --
def table_checks():
    T = cov.PeerStateTable

    t = T()
    t.observe("a:1", {"v": "v8.33", "src": "aaaaaaaaaaaa", "height": 5,
                      "peers": 2, "crisis": False, "spike": ["k1"]})
    row = t.snapshot()["a:1"]
    check("T1 a well-formed digest is recorded",
          row["v"] == "v8.33" and row["height"] == 5 and row["spike"] == ["k1"],
          str(row))

    t.observe("b:1", {"height": True, "peers": "many", "src": 12345,
                      "spike": "not-a-list", "crisis": "yes"})
    row = t.snapshot().get("b:1", {})
    check("T2 peer input is COERCED, not trusted",
          "height" not in row and "peers" not in row and "src" not in row
          and "spike" not in row and "crisis" not in row, str(row))

    t.observe("c:1", {"src": "x" * 400, "spike": ["k"] * 50, "height": 10**30})
    row = t.snapshot()["c:1"]
    check("T3 strings, lists and integers are all bounded",
          len(row["src"]) == 40 and len(row["spike"]) == 5
          and row["height"] == 10 ** 12, f"src={len(row['src'])} "
          f"spike={len(row['spike'])} height={row['height']}")

    t2 = T()
    for i in range(T.MAX_PEERS_TRACKED + 25):
        t2.observe(f"p{i}", {"src": "s" * 12})
    check("T4 the table cannot be grown without bound by peers",
          len(t2.snapshot()) == T.MAX_PEERS_TRACKED, str(len(t2.snapshot())))

    class Mon:
        def __init__(self): self.rec = []
        def record(self, kind, detail): self.rec.append((kind, detail))

    m = Mon()
    t3 = T()
    t3.observe("d:1", {"v": "v8.30", "src": "0b04473b7cbd"},
               monitor=m, own_src="290c7bf1cd26")
    check("T5 a peer on another source records peer_version_mismatch",
          len(m.rec) == 1 and m.rec[0][0] == "peer_version_mismatch"
          and "0b04473b7cbd" in m.rec[0][1] and "290c7bf1cd26" in m.rec[0][1],
          str(m.rec))

    m2 = Mon()
    t3.observe("e:1", {"v": "v8.33", "src": "290c7bf1cd26"},
               monitor=m2, own_src="290c7bf1cd26")
    check("T6 a peer on OUR source records nothing", m2.rec == [], str(m2.rec))

    m3 = Mon()
    t3.observe("f:1", None, monitor=m3, own_src="290c7bf1cd26")
    t3.observe("f:1", "garbage", monitor=m3, own_src="290c7bf1cd26")
    t3.observe("f:1", {}, monitor=m3, own_src="290c7bf1cd26")
    check("T7 junk in place of a digest is ignored without raising",
          "f:1" not in t3.snapshot() and m3.rec == [], str(m3.rec))


# ------------------------------------------------------ digest boundary --
FORBIDDEN = ("memory", "available", "footprint", "substrate", "judge", "db",
             "path", "key", "host", "addr", "model", "ollama")


def digest_checks(live_digest_on_wire):
    d = live_digest_on_wire
    if not isinstance(d, dict):
        check("D1 a digest was captured from a real node's heartbeat", False,
              repr(d))
        return
    check("D1 the digest has exactly the curated key set",
          set(d) == {"v", "src", "height", "peers", "crisis", "spike"}, str(sorted(d)))

    bad = [k for k in d if any(f in k.lower() for f in FORBIDDEN)]
    check("D2 no substrate/judge/path key is in the digest", not bad, str(bad))

    blob = json.dumps(d).lower()
    leaked = [f for f in FORBIDDEN if f in blob]
    check("D3 and none of those words appear in its VALUES either",
          not leaked, str(leaked))

    check("D4 the digest is small enough to ride a heartbeat",
          len(json.dumps(d)) < 300, f"{len(json.dumps(d))} bytes")

    check("D5 it is the node's true identity, captured off the wire",
          d.get("v") == cov.COVENANT_VERSION and d.get("src") == cov.CORE_SOURCE_SHA12,
          str(d))

    # D6 -- the digest must ride the HEARTBEAT and nothing else. A block
    # announce is ~150 bytes by design (address-event); putting the digest on
    # every one would give back most of what that design buys. Asserted at the
    # source, because the alternative is mining a block to observe the negative.
    src_text = open(SRC, encoding="utf-8").read()
    idx = src_text.find('ev["digest"]')
    gossip_idx = src_text.find('ev["gossip"] = True')
    check("D6 the digest is attached only inside the gossip branch",
          idx > 0 and gossip_idx > 0 and 0 < idx - gossip_idx < 600
          and src_text.count('ev["digest"]') == 1,
          f"gossip@{gossip_idx} digest@{idx} count={src_text.count('ev[chr(34)digest'+chr(34)+']')}")


def capture_heartbeat(timeout=25):
    """Be a peer. Start a listener, point a real node at it, read the frame.

    The node probes us at boot (A2 preflight): answering nothing is read as a
    P2P listener, which is what we want to be.
    """
    import threading
    lp = pick_base(2)
    frames = []
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", lp))
    srv.listen(8)
    srv.settimeout(1.0)
    stop_flag = {"go": True}

    def serve():
        while stop_flag["go"]:
            try:
                c, _ = srv.accept()
            except Exception:
                continue
            try:
                c.settimeout(3)
                buf = b""
                while True:
                    ch = c.recv(65536)
                    if not ch:
                        break
                    buf += ch
                if buf:
                    try:
                        frames.append(json.loads(buf.decode()))
                    except Exception:
                        pass
                    c.sendall(json.dumps({"ok": True, "outcome": "known",
                                          "height": 0}).encode())
            except Exception:
                pass
            finally:
                try:
                    c.close()
                except Exception:
                    pass

    th = threading.Thread(target=serve, daemon=True)
    th.start()

    gb = pick_base(14)
    g = subprocess.Popen(
        [sys.executable, SRC, "--port", str(gb), "--node-id", "G",
         "--peers", f"127.0.0.1:{lp}"],
        env=dict(ENV, COVENANT_DB_PATH=os.path.join(TMP, "g.db"),
                 COVENANT_TIP_GOSSIP_INTERVAL="3", PYTHONUNBUFFERED="1"),
        cwd=TMP, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    SPAWNED.append(g)
    try:
        wait_api(gb)
        t0 = time.time()
        while time.time() - t0 < timeout:
            hb = [f for f in frames
                  if isinstance(f, dict) and f.get("gossip") is True]
            if hb:
                return hb[-1].get("digest")
            time.sleep(0.5)
        return None
    finally:
        stop(g)
        stop_flag["go"] = False
        try:
            srv.close()
        except Exception:
            pass


# ------------------------------------------------------------- interop --
def interop_checks():
    if not os.path.exists(OLD_SRC):
        not_run("C1-C5 interop against a real pre-A20 process",
                f"no pre-A20 source here (looked for {_OLD_CANDIDATES}); the "
                f"backwards-compatibility measurement is DATED 2026-08-23 and "
                f"cannot be re-run without that binary -- see P13")
        return None
    check("C0 a pre-A20 source is available to test against", True,
          os.path.basename(OLD_SRC))

    nb, ob = pick_base(), pick_base(28)
    if ob == nb:
        ob = nb + 40
    new_p = start(SRC, nb, "NEW", "new")
    old_p = start(OLD_SRC, ob, "OLD", "old")
    wire_digest = None
    try:
        check("C1a v8.33 node came up", wait_api(nb))
        check("C1b pristine v8.32 node came up", wait_api(ob))
        hn, ho = health(nb), health(ob)

        r_new = frame(nb + 1, announce_frame(hn["genesis"], True, ob + 1))
        r_old = frame(ob + 1, announce_frame(ho["genesis"], True, nb + 1))

        check("V1 a v8.33 reply carries v and src",
              isinstance(r_new, dict) and r_new.get("v") == cov.COVENANT_VERSION
              and r_new.get("src") == cov.CORE_SOURCE_SHA12, str(r_new))
        check("V2 and the reply still says what it always said",
              r_new.get("ok") is True and r_new.get("outcome") == "known"
              and isinstance(r_new.get("height"), int), str(r_new))
        check("V3 the src it reports is the one /health reports",
              r_new.get("src") == hn.get("source_sha256"),
              f"{r_new.get('src')} vs {hn.get('source_sha256')}")

        check("C2 a pristine v8.32 ACCEPTS a v8.33 frame carrying a digest",
              isinstance(r_old, dict) and r_old.get("ok") is True
              and r_old.get("outcome") == "known", str(r_old))
        check("C3 and its reply carries no v/src -- 'cannot say', not an error",
              "v" not in r_old and "src" not in r_old, str(r_old))

        # C4 -- the v8.33 receiving side, fed a genuine old reply.
        t = cov.PeerStateTable()

        class Mon:
            def __init__(self): self.rec = []
            def record(self, k, d): self.rec.append((k, d))

        m = Mon()
        t.observe(f"127.0.0.1:{ob+1}", r_old, monitor=m,
                  own_src=cov.CORE_SOURCE_SHA12)
        # First draft of this check asserted the old peer would not be recorded
        # AT ALL. It is -- a v8.32 ack carries `height`, which is real
        # information -- and that is the better behaviour: the peer appears in
        # the mesh with no v/src, i.e. "cannot say", exactly as P11 defines a
        # node too old to answer. What must NOT happen is a spurious A7
        # mismatch against a peer that never claimed a version.
        row4 = t.snapshot().get(f"127.0.0.1:{ob+1}", {})
        check("C4 a v8.32 reply yields a row that says 'cannot say', not a mismatch",
              m.rec == [] and row4.get("height") == r_old.get("height")
              and "v" not in row4 and "src" not in row4,
              f"rec={m.rec} row={row4}")
        check("C4b and such a peer is invisible to the by-source split",
              t.summary()["by_source"] == {} and t.summary()["tracked"] == 1,
              str(t.summary()))

        # C5 -- a v8.33 node must accept an OLD-STYLE frame with no digest.
        r_new2 = frame(nb + 1, announce_frame(hn["genesis"], False, ob + 1))
        check("C5 a v8.33 node accepts a v8.32-style frame with no digest",
              isinstance(r_new2, dict) and r_new2.get("ok") is True
              and r_new2.get("outcome") == "known", str(r_new2))

        # D5/D6 -- capture what a REAL node actually puts on the wire, by being
        # its peer. A constructed P2PNode would only prove what build_digest
        # returns; this proves what leaves the process.
        wire_digest = capture_heartbeat()

        # H -- the mesh view
        t2 = cov.PeerStateTable()
        t2.observe("peer:1", {"v": "v8.30", "src": "0b04473b7cbd"})
        summ = t2.summary()
        check("H1 the mesh summary groups peers by source",
              summ["tracked"] == 1 and "0b04473b7cbd" in summ["by_source"], str(summ))
        check("H2 /health carries the mesh view",
              isinstance(hn.get("mesh"), dict) and "by_source" in hn["mesh"],
              str(hn.get("mesh")))
        check("H3 a v8.32 node has no mesh view at all (pre-fix record)",
              "mesh" not in ho, str(list(ho))[:80])
    finally:
        stop(new_p); stop(old_p)
    return wire_digest


def prefix_record():
    print("=== PRE-FIX RECORD (module has no PeerStateTable) ===")
    src = open(SRC, encoding="utf-8").read()
    check("R1 replies carry no version", '"v", COVENANT_VERSION' not in src)
    check("R2 there is no peer state table", "PeerStateTable" not in src)
    check("R3 the heartbeat carries no digest", 'ev["digest"]' not in src)


def main():
    print(f"source under test: {SRC}")
    print(f"mode: {'FIXED (v8.33+)' if FIXED else 'PRE-FIX RECORD'}")
    if FIXED:
        table_checks()
        # The wire capture needs only a NEW node, so it no longer depends on
        # the interop fixture. Before this it was a return value of
        # interop_checks() and vanished whenever the pre-A20 source was absent.
        interop_checks()
        digest_checks(capture_heartbeat())
    else:
        prefix_record()
    ok = sum(1 for _, o, _ in results if o)
    print(f"\n{ok}/{len(results)} passed")
    if UNRUN:
        print(f"{len(UNRUN)} section(s) NOT RUN -- do not read this as covered:")
        for n, why in UNRUN:
            print(f"  - {n}: {why}")
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
