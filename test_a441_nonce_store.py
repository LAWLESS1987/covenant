"""A441: a signed request's nonce is replay-protected across PROCESSES of one checkout and across a restart,
not only inside the one process that first saw it. Driven both ways: the durable store lets exactly one of N
concurrent processes accept a (signer, nonce) pair and refuses it in a fresh process; the CONTROL (the old
per-process set) accepts it in every process, so the test can see the vector. Then the same through the real
verify_signed path with a registered signer, including that an UNVERIFIED request never consumes a nonce."""
import base64
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_daily_plan as DP          # noqa: E402
import pairstore_excl                     # noqa: E402

CHILD = (
    "import os, sys, json\n"
    "sys.path.insert(0, %r)\n"
    "mode, store, signer, nonce, exp = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5])\n"
    "if mode == 'store':\n"
    "    import pairstore_excl\n"
    "    print(json.dumps(pairstore_excl.ExclPairStore(store).check_and_record(signer, nonce, exp)))\n"
    "elif mode == 'set':\n"
    "    os.environ['COVENANT_NONCE_STORE'] = store\n"
    "    import covenant_daily_plan as DP\n"
    "    pem = '-----BEGIN PUBLIC KEY-----\\nx\\n-----END PUBLIC KEY-----'\n"
    "    print(json.dumps(DP.nonce_check_and_record(pem, nonce, exp - 300, seen=set())))\n"
    "else:\n"
    "    os.environ['COVENANT_NONCE_STORE'] = store\n"
    "    import covenant_daily_plan as DP\n"
    "    req = json.load(open(sys.argv[6], encoding='utf-8'))\n"
    "    ok, why = DP.verify_signed(req['pem'], req['method'], req['path'], req['body'].encode('utf-8'), req['nonce'],\n"
    "                               req['ts'], req['sig'], signers_path=req['signers'], now=float(req['ts']), seen=None)\n"
    "    print(json.dumps([ok, why]))\n"
) % HERE


def child(*args):
    cp = subprocess.run([sys.executable, "-c", CHILD] + [str(a) for a in args], capture_output=True, text=True, timeout=120)
    assert cp.returncode == 0, cp.stderr[-800:]
    return json.loads(cp.stdout.strip().splitlines()[-1])


class A441NonceStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="a441-")
        self.store = os.path.join(self.tmp, "nonces")
        os.environ["COVENANT_NONCE_STORE"] = self.store
        DP.NONCE_STORE = self.store
        DP._nonce_store_obj = None
        self.exp = int(time.time()) + 300

    # -- the store itself, both ways ------------------------------------------------------------------------------
    def test_exactly_one_of_concurrent_processes_accepts(self):
        procs = [subprocess.Popen([sys.executable, "-c", CHILD, "store", self.store, "k", "n1", str(self.exp)],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(6)]
        outs = [json.loads(p.communicate(timeout=120)[0].strip().splitlines()[-1]) for p in procs]
        self.assertEqual(sum(1 for o in outs if o is True), 1, outs)

    def test_refused_in_a_fresh_process_after_one_recorded(self):
        self.assertTrue(child("store", self.store, "k", "n2", self.exp))
        self.assertFalse(child("store", self.store, "k", "n2", self.exp))      # a "restart": new process, same pair

    def test_control_old_per_process_set_accepts_in_every_process(self):
        """The vector A441 closes: a per-process set lets each process accept the same nonce."""
        self.assertTrue(child("set", self.store, "k", "n3", self.exp))
        self.assertTrue(child("set", self.store, "k", "n3", self.exp))

    def test_prune_drops_expired_keeps_live(self):
        s = pairstore_excl.ExclPairStore(self.store)
        now = int(time.time())
        self.assertTrue(s.check_and_record("k", "old", now - 1000))
        self.assertTrue(s.check_and_record("k", "live", now + 1000))
        s.prune(now, DP.WINDOW_S)
        self.assertFalse(s.contains("k", "old"))
        self.assertTrue(s.contains("k", "live"))

    # -- through the real verify path -----------------------------------------------------------------------------
    def _signed(self, payload=None):
        from cryptography.hazmat.primitives.asymmetric import rsa
        key = rsa.generate_private_key(65537, 2048)
        body, h = DP.sign_json_request(key, "POST", "/m/agent", payload or {"message": "hello"})
        pem = base64.b64decode(h["X-Operator-Pubkey"]).decode()
        signers = os.path.join(self.tmp, "signers.json")
        DP.register_signer("a441-test", pem, signers)
        return dict(pem=pem, method="POST", path="/m/agent", body=body.decode("utf-8"), nonce=h["X-Operator-Nonce"],
                    ts=h["X-Operator-Timestamp"], sig=h["X-Operator-Signature"], signers=signers)

    def _verify(self, r, sig=None):
        return DP.verify_signed(r["pem"], r["method"], r["path"], r["body"].encode("utf-8"), r["nonce"], r["ts"],
                                sig if sig is not None else r["sig"], signers_path=r["signers"], now=float(r["ts"]), seen=None)

    def test_verify_signed_refuses_replay_in_same_process(self):
        r = self._signed()
        self.assertEqual(self._verify(r)[0], True)
        ok, why = self._verify(r)
        self.assertFalse(ok)
        self.assertIn("nonce", why)

    def test_verify_signed_refuses_replay_in_a_fresh_process(self):
        r = self._signed()
        self.assertEqual(self._verify(r)[0], True)
        path = os.path.join(self.tmp, "req.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(r, fh)
        ok, why = child("verify", self.store, "k", r["nonce"], self.exp, path)
        self.assertFalse(ok, why)
        self.assertIn("nonce", why)

    def test_unverified_request_does_not_consume_the_nonce(self):
        r = self._signed()
        ok, why = self._verify(r, sig=base64.b64encode(b"not-a-signature").decode())
        self.assertFalse(ok)
        self.assertIn("signature", why)
        self.assertEqual(self._verify(r)[0], True)                                # the genuine one still lands


class A441QuorumPins(unittest.TestCase):
    """What the review panel asked to see pinned (2026-11-18)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="a441q-")
        os.environ["COVENANT_NONCE_STORE"] = os.path.join(self.tmp, "nonces")
        DP.NONCE_STORE = os.environ["COVENANT_NONCE_STORE"]
        DP._nonce_store_obj = None

    def test_registration_and_fingerprint_share_one_canonical_form(self):
        """Conscious Ledger's attack: a key presented in another encoding must either fail registration or map
        to the SAME pair name -- never 'registered but a new fingerprint'. Whitespace variants collapse under
        _norm on both sides; a character-level variant is not the registered key at all."""
        from cryptography.hazmat.primitives.asymmetric import rsa
        key = rsa.generate_private_key(65537, 2048)
        _body, h = DP.sign_json_request(key, "POST", "/m/agent", {"message": "x"})
        pem = base64.b64decode(h["X-Operator-Pubkey"]).decode()
        signers = os.path.join(self.tmp, "signers.json")
        DP.register_signer("canon", pem, signers)
        variants = [pem.replace("\n", "\r\n"), "  " + pem.replace("\n", "\n   ") + "\n\n", pem.replace("\n", "")]
        for v in variants:
            self.assertEqual(DP.signer_name(v, signers), "canon")
            self.assertEqual(DP._pubkey_fp(v), DP._pubkey_fp(pem))
        lines = pem.strip().splitlines()
        mid = lines[1]
        altered = "\n".join([lines[0], ("B" if mid[0] != "B" else "C") + mid[1:]] + lines[2:]) + "\n"
        self.assertIsNone(DP.signer_name(altered, signers))           # not the registered key -> refused before the nonce

    def test_no_production_caller_passes_its_own_seen_set(self):
        """DeepSeek's audit: the in-process `seen` escape hatch is for tests only. Any production call that passed a
        set would silently bring per-process acceptance back, so pin it."""
        import re
        bad = []
        for name in os.listdir(HERE):
            if not name.endswith(".py") or name.startswith("test_"):
                continue
            src = open(os.path.join(HERE, name), encoding="utf-8", errors="replace").read()
            for m in re.finditer(r"(verify_signed|nonce_check_and_record|\badmit)\([^)]*\bseen\s*=\s*(?!None\b|seen\b)", src):
                bad.append("%s: %s" % (name, m.group(0)[:80]))
        self.assertEqual(bad, [])

    def test_suspended_duplicate_is_refused_after_the_window(self):
        """ChatGPT's TOCTOU: a request that passes its window check, is suspended past the window (long enough for
        prune to have removed the original pair), then reaches the atomic record, must still be refused."""
        import time as _t
        pem = "-----BEGIN PUBLIC KEY-----\nabc\n-----END PUBLIC KEY-----"
        ts = _t.time()
        self.assertTrue(DP.nonce_check_and_record(pem, "fresh", ts, now=ts))          # a fresh request lands
        real = _t.time
        try:
            DP.time.time = lambda: ts + DP.WINDOW_S + 5                                 # the clock at record time
            self.assertFalse(DP.nonce_check_and_record(pem, "suspended", ts, now=ts))   # ...is past the window
        finally:
            DP.time.time = real


if __name__ == "__main__":
    unittest.main()
