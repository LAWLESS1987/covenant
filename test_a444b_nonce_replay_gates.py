"""A444b -- A444's durable nonce store, guarded at BOTH signed gates, each node life a fresh process.

HISTORY. On 2026-11-17 this test was written as "A445" against 9d85f6c, before A444 reached main, and MEASURED the
exposure A444 then fixed: with the in-memory sets, a captured signed request was ACCEPTED again by a restarted
process inside WINDOW_S, and by BOTH of two processes released together -- at the operator gate
(covenant_daily_plan.verify_signed) and at covenant_mycelium.admit's ALLY branch. That version, and its number,
are kept as written on branch a445-nonce-replay-as-numbered-2026-11-17 (A444b in docs/KNOWN_ISSUES.md says why
the number moved). On main the same cases now assert the FIX.

WHAT THIS ADDS TO test_a444_nonce_store.py. A444's test races the store itself and drives verify_signed in a fresh
process. This one drives the ALLY branch of admit() too, through admit() as the node's off-tailnet doors call it,
with every life a fresh interpreter importing the modules anew and using the DEFAULT store:
  1. CONTROL, same life: presented twice -> accepted, then refused.
  2. RESTART: life 1 accepts; life 2, a new process, presents the same bytes inside the window -> REFUSED.
  3. TWO PROCESSES released by one barrier, same bytes -> EXACTLY ONE accepts.
  4. BOUND: a life presenting the bytes one second past the window is refused for the window.
  5. The legacy sets (_seen_nonces, _seen) are no longer what the gate reads: clearing them in-process and
     replaying is still refused.
  6. THE VECTOR IS STILL VISIBLE (both ways): give each life its OWN store directory -- per-process memory, the
     pre-A444 shape -- and both lives accept. If the store stopped being shared, cases 2 and 3 would read like 6.
The store is pointed at a temp dir (COVENANT_NONCE_STORE); nothing here touches ops/.
What this cannot see (rule 9): a live node over HTTP, network filesystems, and cross-HOST replay (A444's open
follow-up: the node is not bound into the signed request).
"""
import base64
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest

_STORE_ROOT = tempfile.mkdtemp(prefix="a444b_store_")
os.environ["COVENANT_NONCE_STORE"] = os.path.join(_STORE_ROOT, "shared")   # before the modules read it

from cryptography.hazmat.backends import default_backend                    # noqa: E402
from cryptography.hazmat.primitives import serialization                    # noqa: E402
from cryptography.hazmat.primitives.asymmetric import rsa                   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import covenant_daily_plan as DP          # noqa: E402
import covenant_mycelium as M             # noqa: E402
import covenant_unified_v8 as cov         # noqa: E402

OP_PATH = "/daily_plan/approve"           # a door that calls verify_signed with the default store
ALLY_PATH = "/m/agent"                    # an ALLY_DOOR, admit's ally branch

# One life of the node: a fresh interpreter, the modules imported anew, the gate called with its DEFAULT store.
CHILD = r'''
import json, os, sys, time
args = json.load(open(sys.argv[1], encoding="utf-8"))
os.environ["COVENANT_NONCE_STORE"] = args["store"]
sys.path.insert(0, args["repo"])
import covenant_daily_plan as DP
import covenant_mycelium as M

class Req:
    def __init__(self, method, path, headers):
        self.method, self.path, self.headers, self.remote_addr = method, path, headers, "192.0.2.7"

if args.get("ready"):
    open(args["ready"], "w").close()
    t0 = time.time()
    while not os.path.exists(args["go"]):
        if time.time() - t0 > 60:
            print(json.dumps({"error": "barrier timeout"})); sys.exit(2)
        time.sleep(0.01)

h, body, out = args["headers"], args["body"].encode("utf-8"), []
for _ in range(args.get("times", 1)):
    if args["gate"] == "operator":
        pem = __import__("base64").b64decode(h["X-Operator-Pubkey"]).decode()
        ok, why = DP.verify_signed(pem, args["method"], args["path"], body, h["X-Operator-Nonce"],
                                   h["X-Operator-Timestamp"], h["X-Operator-Signature"],
                                   signers_path=args["signers"], now=args.get("now"))
        out.append({"ok": ok, "why": why})
    else:
        ok, _addr, who, how = M.admit(Req(args["method"], args["path"], h), body, lambda a: False,
                                      signers_path=args["signers"], peers_path=args["peers"],
                                      ledger_path=args["ledger"], now=args.get("now"))
        out.append({"ok": ok, "why": how, "who": who})
print(json.dumps(out))
'''


def _keypair():
    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
    pem = priv.public_key().public_bytes(serialization.Encoding.PEM,
                                         serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    return priv, pem


class _Cases:
    """The six cases; a mixin, so it is not itself collected."""
    GATE = None   # "operator" | "ally"
    PATH = None

    @classmethod
    def setUpClass(cls):
        cls.td = tempfile.mkdtemp(prefix="a444b_")
        cls.child = os.path.join(cls.td, "life.py")
        with open(cls.child, "w", encoding="utf-8") as fh:
            fh.write(CHILD)
        cls.signers = os.path.join(cls.td, "signers.json")
        cls.peers = os.path.join(cls.td, "peers.json")
        cls.ledger = os.path.join(cls.td, "mycelium.jsonl")
        cls.store = os.path.join(_STORE_ROOT, "shared")
        cls.priv, cls.pem = _keypair()
        if cls.GATE == "operator":
            DP.register_signer("throwaway-phone", cls.pem, cls.signers)
        else:
            # the ally key is NOT a signer: the operator branch refuses it first, then the ally branch runs
            _op_priv, op_pem = _keypair()
            DP.register_signer("someone-else", op_pem, cls.signers)
            M.register_ally("throwaway-ally", cls.pem, granted_by="test fixture", path=cls.peers)

    def _signed(self):
        """One request, signed once, with real time -- the bytes a wire tap would capture."""
        body = '{"decision":"approve","note":"a444b"}'
        h = cov.sign_operator_request(self.priv, self.pem, "POST", self.PATH, body.encode("utf-8"))
        return h, body

    def _life(self, h, body, times=1, now=None, barrier=None, store=None):
        args = {"repo": HERE, "gate": self.GATE, "method": "POST", "path": self.PATH, "body": body,
                "headers": h, "signers": self.signers, "peers": self.peers, "ledger": self.ledger,
                "times": times, "now": now, "store": store or self.store}
        if barrier:
            args.update(barrier)
        f = tempfile.NamedTemporaryFile("w", suffix=".json", dir=self.td, delete=False, encoding="utf-8")
        json.dump(args, f)
        f.close()
        return subprocess.Popen([sys.executable, self.child, f.name], cwd=self.td,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    @staticmethod
    def _result(p):
        out, err = p.communicate(timeout=120)
        lines = [l for l in out.splitlines() if l.startswith("[")]
        if p.returncode != 0 or not lines:
            raise AssertionError("a node life did not run (rc %s): %s" % (p.returncode, (err or out)[-800:]))
        return json.loads(lines[-1])

    def _together(self, h, body, stores):
        go = os.path.join(self.td, "go-%s" % os.urandom(4).hex())
        ready = [os.path.join(self.td, "ready-%d-%s" % (i, os.urandom(4).hex())) for i in range(len(stores))]
        ps = [self._life(h, body, barrier={"ready": ready[i], "go": go}, store=stores[i]) for i in range(len(stores))]
        t0 = time.time()
        while not all(os.path.exists(r) for r in ready):
            if time.time() - t0 > 90 or any(p.poll() is not None for p in ps):
                break
            time.sleep(0.02)
        open(go, "w").close()
        return [self._result(p)[0]["ok"] for p in ps]

    def test_1_control_same_life_refuses_replay(self):
        h, body = self._signed()
        r = self._result(self._life(h, body, times=2))
        self.assertTrue(r[0]["ok"], r)
        self.assertFalse(r[1]["ok"], "the same life accepted its own replay: %r" % r)

    def test_2_restart_replay_inside_window_refused(self):
        h, body = self._signed()
        self.assertTrue(self._result(self._life(h, body))[0]["ok"])
        second = self._result(self._life(h, body))
        # Measured ACCEPTED on 2026-11-17 at 9d85f6c (in-memory sets); A444's shared store refuses it.
        self.assertFalse(second[0]["ok"], "a restarted life accepted a replay inside the window: %r" % second)

    def test_3_two_processes_exactly_one_accepts(self):
        h, body = self._signed()
        oks = self._together(h, body, [self.store, self.store])
        # Measured BOTH accepted on 2026-11-17 at 9d85f6c, in 12 of 12 runs with a check-then-add durable probe.
        self.assertEqual(sorted(oks), [False, True], "two processes on one store: %r" % oks)

    def test_4_past_window_refused(self):
        h, body = self._signed()
        late = float(h["X-Operator-Timestamp"]) + (DP.WINDOW_S if self.GATE == "operator" else M.WINDOW_S) + 1
        r = self._result(self._life(h, body, now=late))
        self.assertFalse(r[0]["ok"], "a request past the window was accepted: %r" % r)

    def test_5_clearing_the_legacy_set_does_not_reopen(self):
        h, body = self._signed()
        legacy = DP._seen_nonces if self.GATE == "operator" else M._seen

        class R:
            method, path, headers, remote_addr = "POST", self.PATH, h, "192.0.2.7"

        def present():
            if self.GATE == "operator":
                return DP.verify_signed(self.pem, "POST", self.PATH, body.encode("utf-8"), h["X-Operator-Nonce"],
                                        h["X-Operator-Timestamp"], h["X-Operator-Signature"],
                                        signers_path=self.signers)[0]
            return M.admit(R, body.encode("utf-8"), lambda a: False, signers_path=self.signers,
                           peers_path=self.peers, ledger_path=self.ledger)[0]
        self.assertTrue(present())
        saved = set(legacy)
        legacy.clear()                           # what a restart did to the pre-A444 store
        try:
            self.assertFalse(present(), "clearing the in-memory set re-opened the replay")
        finally:
            legacy.update(saved)

    def test_6_control_separate_stores_both_accept(self):
        # Both ways: per-process stores ARE the pre-A444 shape, and the test still sees the replay through them.
        h, body = self._signed()
        a, b = (os.path.join(_STORE_ROOT, "solo-%s-%d" % (os.urandom(4).hex(), i)) for i in (0, 1))
        self.assertEqual(self._together(h, body, [a, b]), [True, True],
                         "the control could not see the vector -- cases 2 and 3 would prove nothing")


class OperatorGate(_Cases, unittest.TestCase):
    """covenant_daily_plan.verify_signed -- registered operator signers, WINDOW_S."""
    GATE, PATH = "operator", OP_PATH


class AllyGate(_Cases, unittest.TestCase):
    """covenant_mycelium.admit, ally branch -- a registered ally key on an ALLY_DOOR, WINDOW_S = 300."""
    GATE, PATH = "ally", ALLY_PATH


if __name__ == "__main__":
    unittest.main(verbosity=2)
