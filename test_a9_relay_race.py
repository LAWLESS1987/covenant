"""
A9 (v8.19) -- relay must survive whichever path delivered the block.

Three REAL node processes in a line: A -- B -- C (C is not a peer of A).

Found by running test_multinode_live.py for the first time against v8.18: its
two standing failures ("block RELAYED to C" and "identical tip hash") were not
flakiness. Traced with a patched runner: B's startup bootstrap polled A in the
same instant A mined, so the block entered B through bootstrap_chain ->
_apply_fetched_blocks, which NEVER announced onward; the announce-driven
_fetch_announced then lost the persist race (block_rejected_persist) and did
not announce either. C stayed at height 1 until the next block forced a
catch-up. Any block that arrives while a peer is bootstrapping was one-hop.

Checks (each scenario uses fresh processes, fresh ports, a shared genesis):

  S1  deterministic: A mines with B and C down; C comes up first (its
      bootstrap finds B dead and stops), THEN B comes up. B pulls the block
      from A by bootstrap and must relay it to C.  Pre-fix: C stranded.
  S2  the race as observed: B and C up, tx + mine on A with no pause.
      All three must reach height 2 and the same tip.  Pre-fix: 2/2 failures.
  S3  stake-table convergence across processes after a value block (the
      original A9 wording): /stakes must agree on every node.

Env: both COVENANT_INSECURE_MOCK_JUDGE=1 and COVENANT_JUDGE_PROVIDERS=mock.
Ports: --port N occupies N, N+1, N+11; --peers takes API+1.
"""
import os, sys, json, time, shutil, signal, subprocess, tempfile, urllib.request, urllib.error
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import covenant_unified_v8 as cov
from cryptography.hazmat.primitives import serialization

HERE = os.path.dirname(os.path.abspath(__file__))
CORE = os.path.join(HERE, "covenant_unified_v8.py")
results = []

def check(label, ok, detail=""):
    results.append((label, bool(ok)))
    print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail}", flush=True)

def http(method, port, path, body=None, headers=None, timeout=15):
    raw = json.dumps(body).encode() if body is not None else None
    h = {"Content-Type": "application/json"}; h.update(headers or {})
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=raw, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


class Net:
    def __init__(self, base):
        self.work = tempfile.mkdtemp(prefix="a9_")
        self.base = base
        self.procs = {}
        self.genesis = os.path.join(self.work, "genesis.json")
        env = dict(os.environ, COVENANT_JUDGE_PROVIDERS="mock", COVENANT_INSECURE_MOCK_JUDGE="1",
                   COVENANT_DB_PATH=os.path.join(self.work, "exporter.db"))
        subprocess.run([sys.executable, CORE, "--export-genesis", self.genesis], env=env,
                       capture_output=True, timeout=180)
        # whoever mints genesis is the first node: give A the exporter's key
        shutil.copy(os.path.join(self.work, "exporter.db.key"), os.path.join(self.work, "A.db.key"))
        self.api = {"A": base, "B": base + 20, "C": base + 40}

    def launch(self, nid, peers):
        env = dict(os.environ, COVENANT_JUDGE_PROVIDERS="mock", COVENANT_INSECURE_MOCK_JUDGE="1",
                   COVENANT_GENESIS=self.genesis, COVENANT_DB_PATH=os.path.join(self.work, f"{nid}.db"))
        cmd = [sys.executable, CORE, "--real", "--port", str(self.api[nid]), "--node-id", nid,
               "--genesis", self.genesis]
        if peers:
            cmd += ["--peers", ",".join(f"127.0.0.1:{self.api[p] + 1}" for p in peers)]
        logf = open(os.path.join(self.work, f"{nid}.log"), "w")
        p = subprocess.Popen(cmd, env=env, stdout=logf, stderr=subprocess.STDOUT)
        self.procs[nid] = (p, logf)
        ok = self.wait_http(self.api[nid])
        return ok

    def wait_http(self, port, t=40):
        t0 = time.time()
        while time.time() - t0 < t:
            try:
                http("GET", port, "/health", timeout=3); return True
            except Exception:
                time.sleep(0.4)
        return False

    def key(self, nid):
        kp = os.path.join(self.work, f"{nid}.db.key")
        for _ in range(80):
            if os.path.exists(kp):
                with open(kp, "rb") as fh:
                    return serialization.load_pem_private_key(fh.read(), password=None)
            time.sleep(0.25)
        raise RuntimeError(kp)

    def pem(self, nid):
        return self.key(nid).public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()

    def height(self, nid):
        _, ch = http("GET", self.api[nid], "/chain")
        c = ch.get("chain", ch if isinstance(ch, list) else [])
        return len(c)

    def tip(self, nid):
        _, ch = http("GET", self.api[nid], "/chain")
        c = ch.get("chain", ch if isinstance(ch, list) else [])
        return c[-1].get("hash", "") if c else ""

    def wait_height(self, nid, target, t=30):
        t0 = time.time()
        while time.time() - t0 < t:
            if self.height(nid) >= target:
                return True
            time.sleep(1.5)   # /chain is rate-limited 20/60s per node
        return False

    def submit_tx(self, nid, receiver_pem, amount):
        api = self.api[nid]
        _, a = http("GET", api, "/alignment"); benefit = float(a.get("current_alignment", 0.5))
        sk = self.key(nid); pem = self.pem(nid)
        reg = cov.RegistrationPoW.generate(pem, cov.BASE_REGISTRATION_DIFFICULTY)
        tx = cov.Transaction(sender_pubkey=pem, receiver=receiver_pem, data={"origin": "human"},
                             amount=float(amount), benefit_score=benefit, reg_nonce=reg)
        tx.sign(sk)
        body = {"sender_pubkey": pem, "receiver": receiver_pem, "data": {"origin": "human"},
                "amount": float(amount), "timestamp": tx.timestamp, "benefit_score": benefit,
                "signature": tx.signature, "reg_nonce": reg}
        return http("POST", api, "/transactions", body)

    def op_post(self, nid, path, body=None):
        sk = self.key(nid); pem = self.pem(nid)
        raw = json.dumps(body or {}).encode()
        hdrs = cov.sign_operator_request(sk, pem, "POST", path, raw)
        return http("POST", self.api[nid], path, body or {}, hdrs)

    def anomalies(self, nid):
        _, a = http("GET", self.api[nid], "/anomalies")
        return a.get("per_kind", {})

    def stakes(self, nid):
        _, s = http("GET", self.api[nid], "/stakes")
        return s.get("stakes", {})

    def stop(self):
        for nid, (p, logf) in self.procs.items():
            try:
                p.send_signal(signal.SIGINT); p.wait(timeout=5)
            except Exception:
                p.kill()
            logf.close()
        self.procs = {}

    def log_lines(self, nid):
        lp = os.path.join(self.work, f"{nid}.log")
        return [l.rstrip() for l in open(lp) if '"GET /' not in l and '"POST /' not in l]


def scenario_1(base):
    print("\n== S1: block mined before B/C exist; C up first, then B. B must relay by bootstrap ==")
    n = Net(base)
    try:
        check("S1 A up", n.launch("A", ["B"]))
        st, r = n.submit_tx("A", n.pem("A"), 1.0)  # self-send: any receiver works for the relay
        check("S1 tx admitted on A", st == 200, str(r)[:80])
        s, m = n.op_post("A", "/mine", {})
        check("S1 A mined", s == 200 and n.height("A") == 2, f"HTTP {s}")
        check("S1 C up first (knows only B, which is down)", n.launch("C", ["B"]))
        time.sleep(4.0)   # C's bootstrap round fails against dead B and stops
        check("S1 C still at genesis before B exists", n.height("C") == 1, f"C={n.height('C')}")
        check("S1 B up (peers A and C)", n.launch("B", ["A", "C"]))
        check("S1 B pulled the block from A by bootstrap", n.wait_height("B", 2, 25), f"B={n.height('B')}")
        check("S1 C received the block RELAYED by B after B's bootstrap",
              n.wait_height("C", 2, 25), f"C={n.height('C')}")
        tips = {x: n.tip(x)[:12] for x in "ABC"}
        check("S1 all three agree on the tip", len(set(tips.values())) == 1, tips)
        anC = n.anomalies("C")
        check("S1 C recorded no rejection of the relayed block",
              not any(k.startswith("block_rejected") for k in anC), anC)
    finally:
        n.stop()
        for nid in ("B", "C"):
            print(f"  -- {nid} log:", " | ".join(n.log_lines(nid)[-4:]))


def scenario_2(base):
    print("\n== S2: the observed race -- tx + mine immediately after all three boot ==")
    n = Net(base)
    try:
        okA = n.launch("A", ["B"]); okB = n.launch("B", ["A", "C"]); okC = n.launch("C", ["B"])
        check("S2 three nodes up", okA and okB and okC)
        st, r = n.submit_tx("A", n.pem("B"), 5.0)
        check("S2 tx admitted on A", st == 200, str(r)[:80])
        s, m = n.op_post("A", "/mine", {})
        check("S2 A mined", s == 200, f"HTTP {s}")
        check("S2 block reached B", n.wait_height("B", 2, 20), f"B={n.height('B')}")
        check("S2 block relayed to C (not a peer of A)", n.wait_height("C", 2, 20), f"C={n.height('C')}")
        tips = {x: n.tip(x)[:12] for x in "ABC"}
        check("S2 identical tip on all three", len(set(tips.values())) == 1, tips)
        anB = n.anomalies("B")
        check("S2 a lost delivery race on B is named block_already_held, never block_rejected_persist",
              "block_rejected_persist" not in anB, anB)
        # S3 -- stake-table convergence (original A9 wording)
        print("\n== S3: stake tables agree on every process after a value block ==")
        stk = {x: n.stakes(x) for x in "ABC"}
        norm = {x: json.dumps({k: round(v.get("amount", 0), 9) for k, v in s.items()}, sort_keys=True)
                for x, s in stk.items()}
        check("S3 /stakes identical across A, B, C", len(set(norm.values())) == 1,
              {x: len(s) for x, s in stk.items()})
        # Observation for the log (not asserted): with a LOADED canonical genesis
        # the founder's 1000 is NOT stake-locked (load_canonical_genesis credits
        # the mint and never stakes it), so /stakes is empty on every node while
        # a self-minted node locks the same 1000 for 365 days. See A10.
        print(f"  (observation) founder stake entries on A: {len(stk['A'])}; "
              f"spendable path is the loaded-genesis one")
    finally:
        n.stop()


def main():
    scenario_1(18200)
    scenario_2(18300)
    p = sum(1 for _, ok in results if ok); f = len(results) - p
    print(f"\n{p}/{len(results)} passed" + (f", {f} FAILED" if f else ""))
    sys.exit(1 if f else 0)

if __name__ == "__main__":
    main()
