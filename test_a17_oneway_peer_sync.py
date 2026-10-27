"""test_a17_oneway_peer_sync.py -- A17: a node that lists a peer the peer does
not list back must still learn what that peer mints.

THE SHAPE
  Two REAL processes on the host's routable interface address (not
  loopback -- the shape a Tailscale 100.x peer has): A (the founder's node,
  spendable genesis on its own db) lists no peers; B adopts A's exported
  genesis and lists A by IP:P2P_PORT. This is the phone-to-PC, VPS-to-home,
  many-clients-one-server configuration, and it is what L's Android node
  over a VPN will be on day one.

PRE-FIX (v8.27, measured)
  A mines block 2. B stays at height 1 for ever: A announces to its peer
  list (empty); B's bootstrap ran at boot when A was also at 1; B never
  announces because _gossip_tip says nothing at genesis; /sync is manual.
  Two healthy nodes, peered on paper, never converging.

FIX (v8.28)
  _gossip_tip announces the tip even at genesis. The reply carries A's
  height; A13's _send_announce turns height > ours into a pull. B converges
  within one TIP_GOSSIP_INTERVAL_S (set to 3 s here) with no second block,
  no restart and no /sync.

CHECKS
  O1  both nodes answer /health on the interface IP (not 127.0.0.1)
  O2  B lists A by interface IP; A lists nobody
  O3  A mines block 2 (/mine, operator-signed, zero-value tx)
  O4  FIXED: B reaches height 2 within 15 s      PRE-FIX RECORD: B still 1 at 15 s
  O5  FIXED: B's /health shows peer_ahead_seen >= 1 (A13's path did it)
  O6  FIXED: A's /health tip_gossip_seen >= 1 (B's genesis heartbeat was
      answered "known", not recorded as a duplicate -- A11's path)

Run:  COVENANT_INSECURE_MOCK_JUDGE=1 COVENANT_JUDGE_PROVIDERS=mock \
      python3 test_a17_oneway_peer_sync.py          (FIXED=1 default)
      FIXED=0 ... for the pre-fix record against a v8.27 source
"""
import base64
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
FIXED = os.environ.get("FIXED", "1") == "1"
A_PORT, B_PORT = 19800, 19812                  # 12 apart (M2)
GOSSIP_S = "3"

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

import covenant_unified_v8 as cov

results = []


def check(label, ok, detail=""):
    results.append((label, bool(ok)))
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}" + (f"  -- {detail}" if detail else ""))


def primary_ipv4():
    """The host's primary non-loopback IPv4, portably.

    Was `hostname -I`, which is a GNU coreutils flag: Windows' hostname.exe
    rejects it (CalledProcessError) and a loopback-only container returns an
    empty string (IndexError on [0]). Both crashed this suite before it began.
    The UDP socket sends nothing -- connect() on a datagram socket only picks
    the route -- so this works offline."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("203.0.113.1", 9))      # TEST-NET-3, never routed
        ip = s.getsockname()[0]
    except OSError:
        ip = None
    finally:
        s.close()
    return ip if ip and not ip.startswith("127.") else None


def main():
    ip = primary_ipv4()
    if ip is None:
        print("  [SKIP] no non-loopback IPv4 on this host -- A17 is the phone/VPN")
        print("         shape and needs a real interface. Not counted as a pass.")
        return 0
    work = tempfile.mkdtemp(prefix="a17_")
    env = dict(os.environ, COVENANT_INSECURE_MOCK_JUDGE="1", COVENANT_JUDGE_PROVIDERS="mock",
               PYTHONUNBUFFERED="1", COVENANT_TIP_GOSSIP_INTERVAL=GOSSIP_S)
    core = os.path.join(HERE, "covenant_unified_v8.py")
    founder_db = os.path.join(work, "founder.db")
    gpath = os.path.join(work, "genesis.json")
    print(f"== A17 one-way peer sync ({'v8.28+ FIXED' if FIXED else 'PRE-FIX RECORD'}) on {ip}, "
          f"gossip every {GOSSIP_S}s")

    # founder mints genesis on its own db and exports it
    r = subprocess.run([sys.executable, core, "--export-genesis", gpath, "--node-id", "founder"],
                       cwd=HERE, env=dict(env, COVENANT_DB_PATH=founder_db), capture_output=True, text=True)
    assert os.path.exists(gpath), r.stdout + r.stderr

    def get(port, path):
        return json.load(urllib.request.urlopen(f"http://{ip}:{port}{path}", timeout=5))

    a = subprocess.Popen([sys.executable, core, "--port", str(A_PORT), "--node-id", "founder"],
                         cwd=HERE, env=dict(env, COVENANT_DB_PATH=founder_db),
                         stdout=open(os.path.join(work, "A.log"), "w"), stderr=subprocess.STDOUT)
    time.sleep(4)
    b = subprocess.Popen([sys.executable, core, "--port", str(B_PORT), "--genesis", gpath,
                          "--peers", f"{ip}:{A_PORT + 1}", "--node-id", "B"],
                         cwd=HERE, env=dict(env, COVENANT_DB_PATH=os.path.join(work, "B.db")),
                         stdout=open(os.path.join(work, "B.log"), "w"), stderr=subprocess.STDOUT)
    time.sleep(6)
    try:
        ha, hb = get(A_PORT, "/health"), get(B_PORT, "/health")
        check("O1 both nodes answer /health on the interface IP",
              ha.get("chain_height") == 1 and hb.get("chain_height") == 1,
              f"A {ha.get('chain_height')} B {hb.get('chain_height')}")
        pa, pb = get(A_PORT, "/peers")["peers"], get(B_PORT, "/peers")["peers"]
        check("O2 B lists A by interface IP; A lists nobody",
              any(v[0] == ip and v[1] == A_PORT + 1 for v in pb.values()) and not pa, f"A={pa} B={pb}")

        # founder key from the founder db (same identity file the node uses)
        m = cov.CovenantUnifiedMaster("founder", port=A_PORT + 1000, db_path=founder_db)
        pem = m.public_key.public_bytes(serialization.Encoding.PEM,
                                        serialization.PublicFormat.SubjectPublicKeyInfo).decode()
        gov = ha.get("alignment")
        reg = cov.RegistrationPoW.generate(pem, cov.BASE_REGISTRATION_DIFFICULTY)
        ts = time.time(); dd = {"origin": "human", "message": "a17"}
        pl = cov._domain_frame(b"COVENANT_TX_V1", pem, "HUMANITY", str(ts), json.dumps(dd, sort_keys=True), str(0.0))
        sig = base64.b64encode(m.private_key.sign(
            pl, padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256())).decode()
        body = json.dumps({"sender_pubkey": pem, "receiver": "HUMANITY", "data": dd, "amount": 0.0,
                           "timestamp": ts, "benefit_score": gov, "signature": sig, "reg_nonce": reg}).encode()
        urllib.request.urlopen(urllib.request.Request(f"http://{ip}:{A_PORT}/transactions", data=body,
                                                      headers={"Content-Type": "application/json"}), timeout=10)
        h = cov.sign_operator_request(m.private_key, pem, "POST", "/mine", b"{}")
        h["Content-Type"] = "application/json"
        r = urllib.request.urlopen(urllib.request.Request(f"http://{ip}:{A_PORT}/mine", data=b"{}", headers=h),
                                   timeout=60)
        check("O3 A mined block 2", r.status == 200 and get(A_PORT, "/health").get("chain_height") == 2)

        t0 = time.time(); hb2 = 1
        while time.time() - t0 < 15:
            try:
                hb2 = get(B_PORT, "/health").get("chain_height")
            except Exception:
                pass
            if hb2 and hb2 >= 2:
                break
            time.sleep(1)
        dt = time.time() - t0
        if FIXED:
            check("O4 B reached height 2 with no second block, no restart, no /sync", hb2 == 2, f"B={hb2} after {dt:.1f}s")
            hb = get(B_PORT, "/health"); ha = get(A_PORT, "/health")
            check("O5 B pulled via A13 (peer_ahead_seen >= 1)", hb.get("peer_ahead_seen", 0) >= 1,
                  f"peer_ahead_seen={hb.get('peer_ahead_seen')}")
            check("O6 A counted B's genesis heartbeat as tip gossip, not a duplicate",
                  ha.get("tip_gossip_seen", 0) >= 1 and "announce_inhibited" not in json.dumps(ha.get("anomaly_kinds")),
                  f"tip_gossip_seen={ha.get('tip_gossip_seen')} anomalies={ha.get('anomaly_kinds')}")
        else:
            check("O4 (PRE-FIX RECORD) B still at height 1 after 15 s", hb2 == 1, f"B={hb2}")
    finally:
        a.kill(); b.kill(); a.wait(); b.wait()
    p = sum(1 for _, ok in results if ok)
    print(f"\n{p}/{len(results)} passed" + ("" if p == len(results) else f", {len(results) - p} FAILED"))
    return 0 if p == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
