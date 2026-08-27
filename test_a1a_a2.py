#!/usr/bin/env python3
"""Live verification of v8.15 changes, run twice per the loop's standard.

A1a: /unstake and /claim_rewards must report status=error (with a real HTTP
     error code) for no-ops, instead of the old HTTP 200 {"status":"success",
     "payout":0.0} that misled any caller checking `status`.
A2:  preflight_port_check must (1) refuse to boot on a port collision BEFORE
     the banner, (2) refuse to boot when a --peers entry answers HTTP (the
     API-port-instead-of-P2P-port trap), (3) refuse self-peering, and
     (4) still boot when config is correct or a peer is merely not up yet.

Node env needs BOTH COVENANT_INSECURE_MOCK_JUDGE=1 and
COVENANT_JUDGE_PROVIDERS=mock (M2). Ports: a free base is chosen at runtime (see pick_base) because a production
node owns 5000-5031 on the machine this has to run on; the suite only cares
that P2P = API+1 and bridge = API+11.
"""
import atexit, base64, json, os, shutil, signal, subprocess, sys, time, urllib.request, urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from covenant_unified_v8 import _domain_frame  # exact framing, no re-derivation

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.backends import default_backend

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "covenant_unified_v8.py")
TMP = "/tmp/covtest_a1a"
ENV = dict(os.environ, COVENANT_INSECURE_MOCK_JUDGE="1",
           COVENANT_JUDGE_PROVIDERS="mock")

results = []

# PORTABILITY + LEAK FIX 2026-08-22. Windows' Popen.send_signal accepts only
# SIGTERM / CTRL_C_EVENT / CTRL_BREAK_EVENT; signal.SIGINT raises
# ValueError: Unsupported signal: 2. This suite died on that line, skipped its
# teardown, and left a node running with --port 5001 -- which holds node A's
# P2P port as its Flask API, so the next production restart hit A2's preflight
# and node B refused to boot. A test that leaks a node can take the chain down.
# Hence both halves: a portable stop, and an atexit net so nothing survives
# this process however it exits.
# PORT BASE 2026-08-22. This suite used to hard-code 5001/5002/5012 and
# 5021/5041 -- which is exactly the block a production node occupies here
# (node A: 5000/5001/5011, node B: 5020/5021/5031). On the machine that runs
# the node, `start_node(BASE, "A")` could not bind and every later probe timed
# out. The assertions are about the RELATION between the ports (API, P2P =
# API+1, bridge = API+11), never about their absolute values, so the base is
# chosen at runtime from a block that is actually free.
def pick_base(span=62):
    import socket as _s
    for base in range(17400, 19000, 100):
        for off in range(span):
            x = _s.socket()
            try:
                x.setsockopt(_s.SOL_SOCKET, _s.SO_REUSEADDR, 0)
                x.bind(("127.0.0.1", base + off))
            except OSError:
                x.close(); break
            x.close()
        else:
            return base
    raise SystemExit("no free block of %d ports in 17400-19000" % span)

BASE = pick_base()
print(f"port base for this run: {BASE} (API {BASE}, P2P {BASE+1}, bridge {BASE+11})")

SPAWNED = []

def stop(p, timeout=15):
    if p is None or p.poll() is not None:
        return
    try:
        if os.name == "nt":
            p.terminate()                 # TerminateProcess; SIGINT is not deliverable
        else:
            p.send_signal(signal.SIGINT)  # graceful on POSIX, as before
        p.wait(timeout=timeout)
    except Exception:
        try:
            p.kill(); p.wait(timeout=5)
        except Exception:
            pass

def _reap():
    for p in SPAWNED:
        stop(p, timeout=5)

atexit.register(_reap)

def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}")

def post(port, path, body):
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())

def wait_api(port, timeout=30):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/chain", timeout=2)
            return True
        except urllib.error.HTTPError:
            return True  # any HTTP answer means Flask is up
        except Exception:
            time.sleep(0.5)
    return False

def sign_action(privkey, pubkey_pem, action, ts):
    payload = _domain_frame(b"COVENANT_STAKE_ACTION_V1", pubkey_pem, action, str(ts))
    sig = privkey.sign(payload,
                       padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                                   salt_length=padding.PSS.MAX_LENGTH),
                       hashes.SHA256())
    return base64.b64encode(sig).decode()

def start_node(port, node_id, peers="", db=None, capture=False):
    env = dict(ENV)
    env["COVENANT_DB_PATH"] = db or os.path.join(TMP, f"{node_id}.db")
    cmd = [sys.executable, SRC, "--port", str(port), "--node-id", node_id]
    if peers:
        cmd += ["--peers", peers]
    p = subprocess.Popen(cmd, env=env, cwd=TMP,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True)
    SPAWNED.append(p)      # so _reap() takes it down however this process exits
    return p

def main():
    shutil.rmtree(TMP, ignore_errors=True)
    os.makedirs(TMP)

    # ---- node A up on 5001 ----
    a = start_node(BASE, "A")
    try:
        check("node A API up", wait_api(BASE))

        # founder key = node A's own identity key
        keyfile = os.path.join(TMP, "A.db.key")
        with open(keyfile, "rb") as fh:
            founder = serialization.load_pem_private_key(fh.read(), password=None,
                                                         backend=default_backend())
        founder_pem = founder.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo).decode()

        # A1a-1: unstake the still-locked genesis stake -> 409, status=error
        ts = time.time()
        code, body = post(BASE, "/unstake",
                          {"pubkey": founder_pem, "timestamp": ts,
                           "signature": sign_action(founder, founder_pem, "unstake", ts)})
        check("A1a locked unstake -> 409", code == 409, f"got {code} {body}")
        check("A1a locked unstake status=error", body.get("status") == "error", str(body))
        check("A1a locked unstake message kept", "locked" in body.get("message", ""), str(body))

        # A1a-2: claim on locked stake -> 409, status=error
        ts = time.time()
        code, body = post(BASE, "/claim_rewards",
                          {"pubkey": founder_pem, "timestamp": ts,
                           "signature": sign_action(founder, founder_pem, "claim", ts)})
        check("A1a locked claim -> 409 error", code == 409 and body.get("status") == "error",
              f"got {code} {body}")

        # A1a-3: unstake with a key that has NO stake -> 404, status=error
        stranger = rsa.generate_private_key(public_exponent=65537, key_size=2048,
                                            backend=default_backend())
        stranger_pem = stranger.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo).decode()
        ts = time.time()
        code, body = post(BASE, "/unstake",
                          {"pubkey": stranger_pem, "timestamp": ts,
                           "signature": sign_action(stranger, stranger_pem, "unstake", ts)})
        check("A1a no-stake unstake -> 404 error",
              code == 404 and body.get("status") == "error"
              and "No active stake" in body.get("message", ""), f"got {code} {body}")

        # A1a-4: bad signature still rejected 400 (control unchanged)
        code, body = post(BASE, "/unstake",
                          {"pubkey": founder_pem, "timestamp": time.time(),
                           "signature": base64.b64encode(b"garbage").decode()})
        check("A1a bad signature still 400", code == 400 and body.get("status") == "error",
              f"got {code} {body}")

        # ---- A2 preflight ----
        # A2-1: collision -- --port 5002 while A owns 5002 (its P2P) -> fast fatal
        t0 = time.time()
        p = start_node(BASE + 1, "B")
        out, _ = p.communicate(timeout=30)
        check("A2 collision refused, exit 1", p.returncode == 1, f"rc={p.returncode}")
        check("A2 collision named + arithmetic",
              "PREFLIGHT FAILED" in out and "12 apart" in out, out.strip()[:200])
        check("A2 collision failed fast, before banner",
              "Covenant Unified" not in out and time.time() - t0 < 15)

        # A2-2: peer given as API port (5001) -> fatal with correction to 5002
        p = start_node(BASE + 20, "C", peers=f"127.0.0.1:{BASE}")
        out, _ = p.communicate(timeout=30)
        check("A2 API-port peer refused",
              p.returncode == 1 and "PREFLIGHT FAILED" in out and "Flask API port" in out,
              f"rc={p.returncode} :: {out.strip()[:200]}")
        check("A2 API-port peer suggests +1", f"127.0.0.1:{BASE + 1}" in out)

        # A2-3: self-peering refused
        p = start_node(BASE + 20, "D", peers=f"127.0.0.1:{BASE + 21}")
        out, _ = p.communicate(timeout=30)
        check("A2 self-peer refused", p.returncode == 1 and "OWN ports" in out,
              f"rc={p.returncode} :: {out.strip()[:200]}")

        # A2-4: CORRECT config (peer at A's real P2P port 5002) boots
        e = start_node(BASE + 20, "E", peers=f"127.0.0.1:{BASE + 1}")
        try:
            check("A2 correct config boots", wait_api(BASE + 20))
        finally:
            stop(e)

        # A2-5: unreachable peer is a warning, not fatal
        f = start_node(BASE + 40, "F", peers=f"127.0.0.1:{BASE + 61}")
        try:
            check("A2 absent peer non-fatal", wait_api(BASE + 40))
        finally:
            stop(f)

    finally:
        stop(a)

    fails = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(fails)}/{len(results)} passed")
    sys.exit(1 if fails else 0)

if __name__ == "__main__":
    main()
