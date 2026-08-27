#!/usr/bin/env python3
"""B5 -- /mine latency with live (slow / timing-out) judges, measured in-process.

What this measures, on the real /mine route via app.test_client() (M13):

  L1  /mine re-judges every included transaction AFTER the PoW, sequentially:
      wall time == N_tx x N_judges x per-call latency (+ PoW).
  L2  A judge that times out costs 3 attempts + backoff per transaction
      (3 x JUDGE_TIMEOUT_S + 0.5 + 0.5*PHI), the mined block is DISCARDED
      (HTTP 400), and the transactions stay pending -- so the next /mine
      repeats the PoW and the whole wait.  One transaction whose verdict
      flips (non-deterministic judge, admitted clean, judged violating at
      mine time) wedges /mine until that transaction is evicted: the miner
      cannot produce ANY block while it is in the pool.
  L3  All of that runs while /mine holds node.chain_lock, so every
      /transactions admission, peer tx fetch (find_pending), peer block
      acceptance (the locked tail of _accept_block_common), tip gossip and
      /chain read on this node blocks for the whole judging window.
  L4  The arithmetic from the module's own constants, so the honest maximum
      is on record: worst case per transaction per judge, and the
      5000-pending figure.

Nothing here changes the source; B4 (is the ethics verdict a consensus rule
or an admission policy?) gates the fix.  Needs COVENANT_INSECURE_MOCK_JUDGE=1
and COVENANT_JUDGE_PROVIDERS=mock (set below), no sockets, no keys.
"""
import base64
import json
import os
import sys
import tempfile
import threading
import time

os.environ.setdefault("COVENANT_INSECURE_MOCK_JUDGE", "1")
os.environ.setdefault("COVENANT_JUDGE_PROVIDERS", "mock")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cryptography.hazmat.primitives import hashes, serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import padding, rsa  # noqa: E402
from cryptography.hazmat.backends import default_backend  # noqa: E402

import covenant_unified_v8 as cov  # noqa: E402

PASS = FAIL = 0


def check(label, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS: {label}" + (f" -- {detail}" if detail else ""))
    else:
        FAIL += 1
        print(f"  FAIL: {label}" + (f" -- {detail}" if detail else ""))


class SlowJudge(cov._APIReasoningJudge):
    """Canned provider judge whose _call sleeps `delay` then returns the reply
    (or raises it).  `attempts` counts _call invocations, i.e. retries too."""
    provider = "Slow"
    env_var = "SLOW_KEY"

    def __init__(self, reply, delay, judge_id="slow:0"):
        super().__init__(api_key="x", judge_id=judge_id)
        self.reply, self.delay = reply, delay
        self.attempts = 0
        self.evaluations = 0

    def evaluate(self, data, principles):
        self.evaluations += 1
        return super().evaluate(data, principles)

    def _call(self, data, principles):
        self.attempts += 1
        self.first_call = getattr(self, "first_call", None) or time.monotonic()
        time.sleep(self.delay)
        if isinstance(self.reply, Exception):
            raise self.reply
        return self._parse_verdict(self.reply)


def keypair():
    priv = rsa.generate_private_key(65537, 2048, default_backend())
    pem = priv.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    return priv, pem


def sign(priv, payload):
    return base64.b64encode(priv.sign(
        payload, padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                             salt_length=padding.PSS.MAX_LENGTH), hashes.SHA256())).decode()


CLEAN = '{"violates": false, "reasoning": "clean", "benefit_estimate": 0.5}'
VIOL = '{"violates": true, "reasoning": "flipped", "principle_violated": "1"}'


class Client:
    """test_client wrapper that signs /mine as the node operator."""

    def __init__(self, master):
        self.m = master
        self.c = master.api.app.test_client()
        self.pem = master.public_key.public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()

    def post(self, path, json=None):
        if path == "/mine":
            hdr = cov.sign_operator_request(self.m.private_key, self.pem, "POST", path, b"")
            return self.c.post(path, headers=hdr)
        return self.c.post(path, json=json)

    def get(self, path):
        return self.c.get(path)


def make_master(port):
    tmp = tempfile.mktemp(suffix=".db")
    m = cov.CovenantUnifiedMaster("b5", host="127.0.0.1", port=port, p2p_port=port + 1, db_path=tmp)
    m.add_genesis_block()
    m.node.rate_limiter.allow = lambda *a, **k: True
    return m, Client(m), tmp


def admit(master, client, priv, pem, reg, n, tag):
    """Admit n zero-value transactions under a fast clean judge."""
    master.node.sentinel = cov.ReasoningSentinel(SlowJudge(CLEAN, 0.0), cov.DIVINE_PRINCIPLES)
    for i in range(n):
        ts = time.time() + i * 1e-3
        data = {"origin": "organic", "message": f"{tag}-{i}"}
        pl = cov._domain_frame(b"COVENANT_TX_V1", pem, "collective", str(ts),
                               json.dumps(data, sort_keys=True), str(0.0))
        body = {"sender_pubkey": pem, "receiver": "collective", "data": data, "amount": 0.0,
                "timestamp": ts, "benefit_score": 0.5, "signature": sign(priv, pl), "reg_nonce": reg}
        r = client.post("/transactions", json=body)
        assert r.status_code == 200, (r.status_code, r.get_data(as_text=True)[:200])
    with master.node.chain_lock:
        return len(master.node.pending_transactions)


def pow_cost(master, client, priv, pem, reg):
    """One /mine with a zero-latency judge: the PoW + bookkeeping baseline."""
    admit(master, client, priv, pem, reg, 1, "pow")
    t0 = time.monotonic()
    r = client.post("/mine")
    dt = time.monotonic() - t0
    assert r.status_code == 200, r.get_data(as_text=True)[:200]
    return dt


def section_l1(master, client, priv, pem, reg):
    print("== L1. /mine judge latency is N_tx x N_judges x per-call, sequential, after PoW ==")
    base = pow_cost(master, client, priv, pem, reg)
    print(f"  PoW baseline (zero-latency judge): {base:.2f}s")
    n, d = 4, 0.5
    admit(master, client, priv, pem, reg, n, "l1")
    j1, j2 = SlowJudge(CLEAN, d, "slowA:0"), SlowJudge(CLEAN, d, "slowB:0")
    quorum = cov.QuorumJudge([j1, j2])
    master.node.sentinel = cov.ReasoningSentinel(quorum, cov.DIVINE_PRINCIPLES)
    t0 = time.monotonic()
    r = client.post("/mine")
    dt = time.monotonic() - t0
    expect = n * 2 * d
    check("L1 block mined under slow quorum", r.status_code == 200, r.get_data(as_text=True)[:100])
    check("L1 every included tx re-judged by every judge at mine time",
          j1.evaluations == n and j2.evaluations == n, f"{j1.evaluations},{j2.evaluations} of {n}")
    judging = (t0 + dt) - j1.first_call       # from first judge call to /mine return
    pow_s = j1.first_call - t0                 # PoW (difficulty 4, geometric tail) before it
    print(f"  PoW this block: {pow_s:.2f}s; judging window: {judging:.2f}s; total {dt:.2f}s")
    check("L1 judging window >= N_tx x N_judges x delay (sequential, no overlap)",
          judging >= expect, f"{judging:.2f}s >= {expect:.2f}s")
    check("L1 and not much more than that (all of it is judge latency)",
          judging < expect + 1.0, f"{judging:.2f}s < {expect + 1.0:.2f}s")
    check("L1 judging happens AFTER the PoW", pow_s > 0.0, f"{pow_s:.2f}s of PoW first")
    return base


def section_l2(master, client, priv, pem, reg, base):
    print("== L2. Timeout at mine time: 3 attempts + backoff per tx, block discarded, pool wedged ==")
    n, t = 2, 0.4
    admit(master, client, priv, pem, reg, n, "l2")
    jt = SlowJudge(TimeoutError("read timed out"), t, "slowT:0")
    master.node.sentinel = cov.ReasoningSentinel(jt, cov.DIVINE_PRINCIPLES)
    h0 = len(master.node.chain)
    t0 = time.monotonic()
    r = client.post("/mine")
    dt = time.monotonic() - t0
    per_tx = 3 * t + 0.5 + 0.5 * cov.PHI          # _retry_with_backoff(max_retries=2, base 0.5)
    # P8 (2026-08-23): compare against the bar with a small tolerance. The claim
    # is "it paid the full judging cost again", not "it took at least this exact
    # float". Measured 2.50s against a 2.51s bar the same run had computed one
    # line earlier -- a 10 ms margin, on a machine also running two nodes and
    # Ollama -- so it passed one sweep and failed the next two. 5% keeps every
    # bit of the check's power (if the retries stopped happening the cost would
    # be ~t, i.e. a third of the bar) and stops it crying wolf about the
    # scheduler. A test that fails two sweeps in three teaches you to ignore it.
    BAR = per_tx * 0.95
    dt = (t0 + dt) - jt.first_call                 # judging window only (PoW excluded)
    check("L2 /mine refused after PoW (400)", r.status_code == 400, f"{r.status_code} {r.get_data(as_text=True)[:90]}")
    check("L2 first failing tx stops the block: one evaluation", jt.evaluations == 1, f"{jt.evaluations}")
    check("L2 three attempts for that one tx", jt.attempts == 3, f"{jt.attempts}")
    check("L2 cost >= 3 x timeout + backoff (5% tolerance)", dt >= BAR,
          f"{dt:.2f}s >= {BAR:.2f}s (bar {per_tx:.2f}s)")
    check("L2 chain height unchanged (mined block thrown away)", len(master.node.chain) == h0)
    with master.node.chain_lock:
        still = len(master.node.pending_transactions)
    check("L2 transactions remain pending -- next /mine repeats PoW + wait", still == n, f"{still}")
    # Second /mine: same again, proving the repeat (and that the PoW is redone).
    jt.attempts = jt.evaluations = 0
    jt.first_call = None
    t0 = time.monotonic()
    r2 = client.post("/mine")
    dt2 = (time.monotonic()) - jt.first_call
    check("L2 second /mine refused the same way", r2.status_code == 400 and jt.attempts == 3, f"{r2.status_code} {jt.attempts}")
    check("L2 second /mine paid again (>= 3 x timeout + backoff, 5% tolerance)",
          dt2 >= BAR, f"{dt2:.2f}s >= {BAR:.2f}s (bar {per_tx:.2f}s)")
    # v8.23 and earlier: NOTHING was recorded on /anomalies for a /mine refusal
    # (the pre-fix record: judge_unavailable == 0 and no mine_rejected_* kind).
    # v8.24: both /mine refusals are named, and a timeout is distinguishable.
    k = _kinds(client)
    check("L2 v8.24: /mine refusal recorded as mine_rejected_ethics (was: bare 400, nothing on /anomalies)",
          k.get("mine_rejected_ethics", 0) == 2, str(k))
    check("L2 v8.24: judge_unavailable recorded for the timeout refusals on /mine (one per refusal)",
          k.get("judge_unavailable", 0) == 2, str(k))
    # Verdict flip: admitted clean, judged violating at mine time -> wedged.
    jv = SlowJudge(VIOL, 0.0, "flip:0")
    master.node.sentinel = cov.ReasoningSentinel(jv, cov.DIVINE_PRINCIPLES)
    r3 = client.post("/mine")
    with master.node.chain_lock:
        still3 = len(master.node.pending_transactions)
    check("L2 flipped verdict: /mine 400, nothing evicted -> wedged until manual action",
          r3.status_code == 400 and still3 == n, f"{r3.status_code} pending={still3}")
    k = _kinds(client)
    check("L2 v8.24: a REAL dissent is never relabelled judge_unavailable (count unchanged)",
          k.get("judge_unavailable", 0) == 2 and k.get("mine_rejected_ethics", 0) == 3, str(k))
    # Drain so later sections start clean.
    master.node.sentinel = cov.ReasoningSentinel(SlowJudge(CLEAN, 0.0), cov.DIVINE_PRINCIPLES)
    r4 = client.post("/mine")
    check("L2 same pool mines at once with a clean judge (nothing wrong with the txs)", r4.status_code == 200)


def _kinds(client):
    rep = client.get("/anomalies").get_json() or {}
    return {k: v.get("recent", 0) for k, v in rep.get("per_kind", {}).items()}


def section_l3(master, client, priv, pem, reg, base):
    print("== L3. chain_lock is held for the whole judging window ==")
    n, d = 3, 0.7
    admit(master, client, priv, pem, reg, n, "l3")
    js = SlowJudge(CLEAN, d, "slowC:0")
    master.node.sentinel = cov.ReasoningSentinel(js, cov.DIVINE_PRINCIPLES)
    judged_at = []
    orig = js._call

    def tracing_call(data, principles):
        judged_at.append(time.monotonic())
        return orig(data, principles)
    js._call = tracing_call

    result = {}

    def miner():
        t0 = time.monotonic()
        r = client.post("/mine")
        result["status"], result["dt"] = r.status_code, time.monotonic() - t0

    th = threading.Thread(target=miner, name="miner")
    th.start()
    # Wait until the first judge call has started (PoW done, judging under way).
    while not judged_at and th.is_alive():
        time.sleep(0.01)
    t_try = time.monotonic()
    got = master.node.chain_lock.acquire(timeout=0.25)
    if got:
        master.node.chain_lock.release()
    check("L3 chain_lock NOT acquirable while /mine is judging", not got)
    # find_pending() is what a peer tx fetch does: take chain_lock, scan, release.
    # It -- and every /transactions admission, which takes the same lock --
    # stalls until the judging window ends.
    t1 = time.monotonic()
    master.node.find_pending("nope")
    waited = time.monotonic() - t1
    th.join()
    remaining_at_try = max(0.0, n * d - (t1 - judged_at[0]))
    check("L3 /mine completed", result.get("status") == 200, str(result))
    check("L3 a plain pending lookup waited for the judging to finish",
          waited >= remaining_at_try - 0.35, f"waited {waited:.2f}s, judging had {remaining_at_try:.2f}s left")
    check("L3 judge calls are strictly sequential (gaps >= delay)",
          all(b - a >= d - 0.05 for a, b in zip(judged_at, judged_at[1:])),
          " ".join(f"{b - a:.2f}" for a, b in zip(judged_at, judged_at[1:])))


def section_l5(master, client, priv, pem, reg):
    """v8.24: the PEER block-acceptance path names an infrastructure refusal too.
    A valid block (built exactly as /mine builds it) is pushed through the real
    _accept_block_common while this node's judge times out: the block is still
    refused (B4 decides whether that is right), but block_rejected_ethics now
    comes with judge_unavailable; a real dissent does not."""
    print("== L5. Peer block acceptance: refusal by a DOWN judge is named, a dissent is not ==")
    import math
    admit(master, client, priv, pem, reg, 1, "l5")
    with master.node.chain_lock:
        txs = list(master.node.pending_transactions)[:1]
        master.node.pending_transactions = [t for t in master.node.pending_transactions if t not in txs]
        last = master.node.chain[-1]
        blk = cov.Block(index=len(master.node.chain), transactions=txs, previous_hash=last.hash)
    blk.stake_rewards = math.fsum(t.amount for t in txs) * 0.01
    blk.mine(cov.MINING_DIFFICULTY)
    h0 = len(master.node.chain)
    before = _kinds(client)
    jt = SlowJudge(TimeoutError("read timed out"), 0.05, "slowT:1")
    master.node.sentinel = cov.ReasoningSentinel(jt, cov.DIVINE_PRINCIPLES)
    ok = master._accept_block_common(blk)
    k = _kinds(client)
    check("L5 block refused while the judge is down (unchanged: fail closed)",
          ok is False and len(master.node.chain) == h0, f"ok={ok} height={len(master.node.chain)}")
    check("L5 block_rejected_ethics recorded",
          k.get("block_rejected_ethics", 0) == before.get("block_rejected_ethics", 0) + 1, str(k))
    check("L5 v8.24: judge_unavailable recorded beside it on the peer path",
          k.get("judge_unavailable", 0) == before.get("judge_unavailable", 0) + 1, str(k))
    jv = SlowJudge(VIOL, 0.0, "flip:1")
    master.node.sentinel = cov.ReasoningSentinel(jv, cov.DIVINE_PRINCIPLES)
    ok2 = master._accept_block_common(blk)
    k2 = _kinds(client)
    check("L5 real dissent: refused, block_rejected_ethics +1, judge_unavailable unchanged",
          ok2 is False and k2.get("block_rejected_ethics", 0) == k.get("block_rejected_ethics", 0) + 1
          and k2.get("judge_unavailable", 0) == k.get("judge_unavailable", 0), str(k2))
    master.node.sentinel = cov.ReasoningSentinel(SlowJudge(CLEAN, 0.0), cov.DIVINE_PRINCIPLES)
    ok3 = master._accept_block_common(blk)
    check("L5 same block accepted once the judge answers (nothing wrong with the block)",
          ok3 is True and len(master.node.chain) == h0 + 1, f"ok={ok3} height={len(master.node.chain)}")


def section_l4():
    print("== L4. Honest maximum from the module's constants ==")
    T = cov.JUDGE_TIMEOUT_S
    backoff = 0.5 + 0.5 * cov.PHI
    worst_tx_judge = 3 * T + backoff
    print(f"  JUDGE_TIMEOUT_S={T:.0f}s -> worst case per tx per judge = 3T + backoff = {worst_tx_judge:.2f}s")
    n_max = cov.MAX_PENDING_TRANSACTIONS
    worst_block_1j = n_max * worst_tx_judge
    print(f"  MAX_PENDING_TRANSACTIONS={n_max}: one slow provider, full block -> {worst_block_1j/3600:.1f} h under chain_lock")
    happy = n_max * 2 * 2.0
    print(f"  happy path (2 judges, 2 s per call), full block -> {happy/3600:.1f} h under chain_lock, after the PoW")
    check("L4 worst case per tx per judge > 90 s at default timeout", worst_tx_judge > 90.0, f"{worst_tx_judge:.2f}")
    check("L4 a full block with one timing-out provider exceeds 5 days", worst_block_1j > 5 * 86400, f"{worst_block_1j/86400:.1f} d")
    check("L4 happy-path full block exceeds 5 h", happy > 5 * 3600, f"{happy/3600:.1f} h")
    check("L4 retry count is 3 attempts (max_retries=2) -- the figure above assumes it",
          _attempts_of_retry() == 3, str(_attempts_of_retry()))


def _attempts_of_retry():
    n = [0]

    def f():
        n[0] += 1
        raise RuntimeError("x")
    real = cov.time.sleep
    cov.time.sleep = lambda s: None
    try:
        cov._retry_with_backoff(f, max_retries=2, base_delay_s=0.5)
    except RuntimeError:
        pass
    finally:
        cov.time.sleep = real
    return n[0]


def main():
    t0 = time.time()
    master, client, tmp = make_master(17950)
    priv, pem = keypair()
    reg = cov.RegistrationPoW.generate(pem, cov.BASE_REGISTRATION_DIFFICULTY)
    try:
        base = section_l1(master, client, priv, pem, reg)
        section_l2(master, client, priv, pem, reg, base)
        section_l3(master, client, priv, pem, reg, base)
        section_l5(master, client, priv, pem, reg)
        section_l4()
    finally:
        for p in (tmp, tmp + ".key"):
            try:
                os.unlink(p)
            except OSError:
                pass
    print(f"\n{PASS}/{PASS + FAIL} passed in {time.time() - t0:.1f}s")
    sys.exit(0 if FAIL == 0 else 1)


if __name__ == "__main__":
    main()
