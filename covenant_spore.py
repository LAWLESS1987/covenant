#!/usr/bin/env python3
"""covenant_spore.py -- the third road on the mycelial highway (A374): the spore road,
and the road neurons that choose among the roads.

HIS WORDS, 2026-10-19: "make our own similar option on the mycelial road using
the spiking system" -- similar to Tailscale, for the phone and the PC.

THE GAP IT ANSWERS. Two roads reach the PC today: the tailnet, and the LAN
address with a signed request (A200, covenant_mycelium). Away from home with
Tailscale off there is none: the PC has no public address and no port is open
(A8), so phone and PC cannot meet.

THE SPORE ROAD. Neither device has to be reachable; both only reach OUT, to a
relay. The phone leaves the SAME signed request it sends on the other roads
(method, path, body, its X-Operator-* headers) sealed with covenant_sealed_mail
to the PC's key; the PC collects, opens, and runs covenant_mycelium.admit on
the inner signature -- a registered signer's key, the 300 s window, a nonce
used once -- and only then hands it to its own door on loopback. The answer is
sealed back to the phone's key. Like a spore: it waits where it was left, and
only the one it was meant for can make anything of it.

  - The relay cannot READ a block: it is AES-GCM under a key wrapped to the
    recipient's RSA key.
  - It cannot FORGE one: the block is signed by the sender, and the request
    inside is signed again under the scheme every door already checks.
  - It cannot REPLAY one past the window or twice: the nonce is single-use.
  - It cannot DRAIN a box it does not own: a take is signed by the key whose
    fingerprint names the box (take_proof / verify_take).

WHAT IT CANNOT DO, said plainly. It can DROP or DELAY blocks (a delay past the
window turns into a refusal, never into a late action). It sees which two
fingerprints talk, when, and how much. It is not a tunnel: only the doors in
SPORE_DOORS ride it, and a round trip is seconds, not milliseconds. WHERE the
relay lives is his decision -- serve_relay() runs one anywhere Python runs,
bound to loopback unless told otherwise.

THE ROAD NEURONS (the spiking part). One leaky integrate-and-fire neuron per
road, event-driven: nothing runs between calls. Between events the potential
leaks exactly as v * exp(-dt / tau) -- the leak snnTorch's Leaky neuron applies
per step (beta = exp(-dt/tau)), solved over the whole gap at once. A call that
reached the PC clears any negative charge and injects +W_OK (a connect that
worked is proof); a call that failed to CONNECT injects -W_FAIL (an error
answered BY the PC is the road working). A road at or above THETA fires:
it is alive. Alive roads go first, in the preference order; a dead road that is
preferred is probed once per PROBE_S, so the faster road is found again when it
comes back; old evidence leaks away, so after a long idle the preference order
is tried afresh. What this buys is measured in test_sp1: a dead tailnet costs
one connect timeout per probe interval instead of one per call, and one blip on
a road with a run of successes does not drop it. It is a small hand-set neuron,
not a trained network; it earns its place by those two behaviours, not by its
name.
"""
import base64
import hashlib
import json
import math
import os
import secrets
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROADS = ("tailnet", "lan", "spore")
KIND_REQ, KIND_REPLY = "spore", "spore_reply"
# the doors the second road already carries (entry.py's _pc_route callers, counted 2026-10-19): six calls on five
# paths plus /m/code/<id>. The check-in, the daily plan and the money doors are NOT here.
SPORE_DOORS = ("/m/agent", "/m/heal", "/pc/3d/state", "/m/image", "/m/code")
# A reply body above this is answered 413, never cut silently. The body is base64'd three times on its way into a
# block (the body field, the ciphertext field, the armor): about 2.37x. 400 KB keeps a block under the 1 MB every
# reader refuses above (SP1b sends one this size through). The first value, 600 KB, would have made blocks of ~1.4 MB.
MAX_BODY = 400 * 1024
REPLY_HEADERS = ("Content-Type", "X-Covenant-Model", "X-Covenant-Ms")   # what the app reads from an answer (pc_draw)
MAX_BOX = 200                      # blocks waiting in one box at a relay
WINDOW_S = 300                     # the window of the signature scheme and of a take
# A376: a take may ask the relay to HOLD the connection up to this long for a block, so a reply reaches the phone the
# instant the PC seals it instead of at the next poll tick. Capped here; the client's own HTTP timeout must exceed it.
LONGPOLL_MAX_S = 25


# ---------------------------------------------------------------- the road neurons

class RoadNeurons:
    """One leaky integrate-and-fire neuron per road (see the module docstring)."""

    def __init__(self, roads=ROADS, tau_s=900.0, w_ok=1.0, w_fail=1.0, theta=0.5, probe_s=300.0, vmax=3.0):
        self.roads, self.tau, self.w_ok, self.w_fail = tuple(roads), float(tau_s), float(w_ok), float(w_fail)
        self.theta, self.probe_s, self.vmax = float(theta), float(probe_s), float(vmax)
        self.v = {r: 0.0 for r in self.roads}           # potential at the last event
        self.t = {r: None for r in self.roads}          # time of the last event
        self.tried = {r: None for r in self.roads}      # time of the last attempt

    def potential(self, road, now):
        t = self.t[road]
        if t is None:
            return 0.0
        return self.v[road] * math.exp(-max(0.0, now - t) / self.tau)

    def event(self, road, ok, now):
        """A call on ROAD reached the PC (ok) or failed to connect. Returns True when the road fires (alive)."""
        # A connect that worked is proof the road is up NOW; a failed one can be a blip. So a success first clears
        # any negative charge (SP1a found a road that came back still dead after a successful probe: its failures
        # outweighed the proof), while a failure only subtracts.
        p = self.potential(road, now)
        v = (max(p, 0.0) + self.w_ok) if ok else (p - self.w_fail)
        self.v[road] = max(-self.vmax, min(self.vmax, v))
        self.t[road] = self.tried[road] = now
        return self.v[road] >= self.theta

    def alive(self, road, now):
        return self.potential(road, now) >= self.theta

    def order(self, now):
        """The roads to try, in order: one due probe of a road preferred over the best live one, then the
        live roads in preference order, then the rest in preference order."""
        live = [r for r in self.roads if self.alive(r, now)]
        if not live:
            return list(self.roads)
        best = self.roads.index(live[0])
        due = [r for r in self.roads[:best]
               if self.tried[r] is None or now - self.tried[r] >= self.probe_s]
        # the due road tried LEAST recently: with the tailnet and the LAN both dead, taking the first due road
        # would probe the tailnet every time and never the LAN (found working the test through by hand)
        probe = sorted(due, key=lambda r: -1e18 if self.tried[r] is None else self.tried[r])[:1]
        rest = [r for r in self.roads if r not in live and r not in probe]
        return probe + live + rest

    def to_json(self):
        return {"roads": {r: {"v": self.v[r], "t": self.t[r], "tried": self.tried[r]} for r in self.roads},
                "tau_s": self.tau, "w_ok": self.w_ok, "w_fail": self.w_fail, "theta": self.theta,
                "probe_s": self.probe_s, "vmax": self.vmax}

    @classmethod
    def from_json(cls, d):
        rs = (d or {}).get("roads") or {}
        n = cls(roads=tuple(rs) or ROADS, **{k: d[k] for k in ("tau_s", "w_ok", "w_fail", "theta", "probe_s", "vmax") if k in (d or {})})
        for r, row in rs.items():
            n.v[r], n.t[r], n.tried[r] = float(row.get("v") or 0.0), row.get("t"), row.get("tried")
        return n


def load_neurons(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return RoadNeurons.from_json(json.load(fh))
    except (OSError, ValueError, TypeError, KeyError):
        return RoadNeurons()


def save_neurons(n, path):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(n.to_json(), fh)
    os.replace(tmp, path)


# ---------------------------------------------------------------- the sealer (covenant_sealed_mail on the PC; the app passes its mirror)

class Sealer:
    """seal(kind, obj, key, pem, to_pem) -> text; open(env, key, pem, expect_pem) -> (env, obj, spk); blocks(text)."""

    def __init__(self, seal=None, open_env=None, blocks=None, fingerprint=None, error=Exception):
        if seal is None:
            import covenant_sealed_mail as SM
            seal, open_env, blocks, fingerprint, error = SM.seal, SM.open_env, SM.blocks, SM.fingerprint, SM.SealedError
        self.seal, self.open_env, self.blocks, self.fingerprint, self.error = seal, open_env, blocks, fingerprint, error


def _b64(b):
    return base64.b64encode(b or b"").decode("ascii")


def _canon(d):
    return json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def door_ok(path):
    p = str(path or "").split("?", 1)[0]
    return p in SPORE_DOORS or (p.startswith("/m/code/") and len(p) <= 60)


def wrap_request(sealer, method, path, body, headers, my_key, my_pem, pc_pem):
    """(id, block): the signed request, sealed for the PC. HEADERS are the X-Operator-* headers the phone signed."""
    rid = secrets.token_hex(8)
    obj = {"kind": KIND_REQ, "id": rid, "method": str(method), "path": str(path), "body": _b64(body),
           "headers": {k: str(v) for k, v in (headers or {}).items() if str(k).startswith("X-Operator-")}}
    return rid, sealer.seal(KIND_REQ, obj, my_key, my_pem, pc_pem)


# ---------------------------------------------------------------- the take proof: only a box's owner drains it

def _pss():
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    return padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH), hashes.SHA256()


def take_proof(key, pem, box, now=None):
    msg = {"box": box, "ts": float(now if now is not None else time.time()), "nonce": secrets.token_hex(12)}
    pad, h = _pss()
    sig = key.sign(_canon(msg).encode("utf-8"), pad, h)
    return dict(msg, sig=_b64(sig), pem=pem)


def verify_take(proof, box, seen, now=None):
    """(ok, why). The proof's key must hash to BOX, be fresh, carry an unused nonce, and verify."""
    from cryptography.hazmat.primitives import serialization
    try:
        pem, ts, nonce = str(proof["pem"]), float(proof["ts"]), str(proof["nonce"])
        if proof.get("box") != box or hashlib.sha256("".join(pem.split()).encode("utf-8")).hexdigest()[:16] != box:
            return False, "the key does not own this box"
        if abs((now if now is not None else time.time()) - ts) > WINDOW_S:
            return False, "the proof is outside the window"
        if not nonce or nonce in seen:
            return False, "the proof's nonce was used"
        pad, h = _pss()
        serialization.load_pem_public_key(pem.encode("utf-8")).verify(
            base64.b64decode(proof["sig"]), _canon({"box": box, "ts": ts, "nonce": nonce}).encode("utf-8"), pad, h)
    except Exception as e:                                        # noqa: BLE001 -- untrusted input
        return False, "the proof does not verify: %s" % type(e).__name__
    seen.add(nonce)
    return True, "owner"


# ---------------------------------------------------------------- relays: a folder (tests, a shared drive) and HTTP

class FileRelay:
    """A relay in a folder. take() moves what it hands over into BOX/collected/ -- kept, never deleted."""

    def __init__(self, root):
        self.root = root

    def _box(self, box):
        if len(box) != 16 or any(c not in "0123456789abcdef" for c in box):
            raise ValueError("a box is a 16-hex fingerprint")
        return os.path.join(self.root, box)

    def put(self, box, blob):
        d = self._box(box)
        os.makedirs(d, exist_ok=True)
        if len(str(blob).encode("utf-8")) > (1 << 20):
            raise ValueError("a block larger than 1 MB is not one of ours")
        if sum(1 for f in os.listdir(d) if f.endswith(".blk")) >= MAX_BOX:
            raise ValueError("the box is full")
        bid = "%d-%s" % (time.time_ns(), secrets.token_hex(4))
        tmp = os.path.join(d, bid + ".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(str(blob))
        os.replace(tmp, os.path.join(d, bid + ".blk"))
        return bid

    def take(self, box, proof=None, seen=None, now=None):
        d = self._box(box)
        if proof is not None:
            ok, why = verify_take(proof, box, seen if seen is not None else set(), now)
            if not ok:
                raise PermissionError(why)
        out = []
        if not os.path.isdir(d):
            return out
        kept = os.path.join(d, "collected")
        for f in sorted(x for x in os.listdir(d) if x.endswith(".blk")):
            p = os.path.join(d, f)
            with open(p, encoding="utf-8") as fh:
                out.append((f[:-4], fh.read()))
            os.makedirs(kept, exist_ok=True)
            os.replace(p, os.path.join(kept, f))
        return out


class HttpRelay:
    """The client side of serve_relay(): POST /box/<box> leaves a block; POST /box/<box>/take with a take proof.
    take(wait_s=N) asks the relay to long-poll: hold until a block arrives or N seconds pass (A376)."""

    def __init__(self, base, key=None, pem=None, timeout=15):
        self.base, self.key, self.pem, self.timeout = base.rstrip("/"), key, pem, timeout

    def _post(self, url, data, timeout=None):
        import urllib.request
        req = urllib.request.Request(url, data=data, method="POST", headers={"Content-Type": "application/octet-stream"})
        with urllib.request.urlopen(req, timeout=timeout or self.timeout) as r:
            return json.loads(r.read().decode("utf-8"))

    def put(self, box, blob):
        return self._post("%s/box/%s" % (self.base, box), str(blob).encode("utf-8")).get("id")

    def take(self, box, proof=None, seen=None, now=None, wait_s=0.0):
        proof = proof or take_proof(self.key, self.pem, box, now)
        url, timeout = "%s/box/%s/take" % (self.base, box), None
        if wait_s and wait_s > 0:
            w = min(float(wait_s), LONGPOLL_MAX_S)
            url += "?wait=%g" % w
            timeout = w + float(self.timeout)              # outlast the relay's hold, or urlopen aborts it
        rows = self._post(url, _canon(proof).encode("utf-8"), timeout=timeout).get("blocks") or []
        return [(r.get("id"), r.get("blob")) for r in rows]


def make_relay_server(root, host="127.0.0.1", port=0):
    """A ThreadingHTTPServer serving a FileRelay at ROOT. Loopback unless HOST says otherwise; where it runs is his."""
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    relay, seen = FileRelay(root), set()

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):                                # quiet: the relay keeps no log of who
            pass

        def _send(self, code, obj):
            b = json.dumps(obj).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def do_POST(self):
            raw, _, query = self.path.partition("?")
            parts = raw.strip("/").split("/")
            n = int(self.headers.get("Content-Length") or 0)
            if n > (1 << 20) + 4096:
                return self._send(413, {"error": "too large"})
            data = self.rfile.read(n)
            try:
                if len(parts) == 2 and parts[0] == "box":
                    return self._send(200, {"id": relay.put(parts[1], data.decode("utf-8"))})
                if len(parts) == 3 and parts[0] == "box" and parts[2] == "take":
                    rows = relay.take(parts[1], json.loads(data.decode("utf-8")), seen)   # verify + collect once; nonce spent here
                    # A376 long-poll: box empty and the caller asked to wait -> HOLD, re-collecting WITHOUT re-verifying
                    # (proof=None), so the reply is handed over the instant the PC seals it, not at the next client poll.
                    wait = 0.0
                    for kv in query.split("&"):
                        if kv.startswith("wait="):
                            try:
                                wait = min(float(kv[5:]), LONGPOLL_MAX_S)
                            except ValueError:
                                wait = 0.0
                    if not rows and wait > 0:
                        deadline = time.time() + wait
                        while time.time() < deadline:
                            time.sleep(0.2)
                            rows = relay.take(parts[1], None)
                            if rows:
                                break
                    return self._send(200, {"blocks": [{"id": i, "blob": b} for i, b in rows]})
            except PermissionError as e:
                return self._send(403, {"error": str(e)})
            except (ValueError, UnicodeDecodeError) as e:
                return self._send(400, {"error": str(e)[:200]})
            return self._send(404, {"error": "no such path"})

    return ThreadingHTTPServer((host, int(port)), H)


# ---------------------------------------------------------------- the PC's pass

class _Req:
    def __init__(self, method, path, headers):
        self.remote_addr, self.method, self.path, self.headers = "spore", method, path, headers


def _norm(pem):
    return "".join(str(pem or "").split())


def forward_local(method, path, body, headers, base="http://127.0.0.1:5000", timeout=180):
    """Hand an ADMITTED request to this PC's own door on loopback. (code, body bytes, the REPLY_HEADERS present)."""
    import urllib.error
    import urllib.request
    h = dict(headers)
    if body:
        h["Content-Type"] = "application/json"
    req = urllib.request.Request(base + path, data=body or None, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.getcode(), r.read(), {k: r.headers.get(k) for k in REPLY_HEADERS if r.headers.get(k)}
    except urllib.error.HTTPError as e:
        return e.code, e.read(), {k: e.headers.get(k) for k in REPLY_HEADERS if e.headers and e.headers.get(k)}


def pc_pass(relay, my_key, my_pem, forward=forward_local, sealer=None, signers_path=None, ledger_path=None,
            now=None, seen=None, proof=None):
    """Collect this PC's box once: open, admit by key, hand admitted requests to the door, seal each answer back.
    Returns one row per block, the same rows covenant_mycelium's ledger keeps."""
    import covenant_daily_plan as DP
    import covenant_mycelium as M
    sealer = sealer or Sealer()
    rows = []
    for bid, text in relay.take(sealer.fingerprint(my_pem), proof=proof):
        envs = sealer.blocks(text)
        if not envs:
            rows.append(_row(ledger_path, M, "refused", bid, "", "", "not a sealed block"))
            continue
        try:
            env, obj, spk = sealer.open_env(envs[0], my_key, my_pem)
        except sealer.error as e:
            rows.append(_row(ledger_path, M, "refused", bid, "", "", "did not open: %s" % e))
            continue
        path, method = str(obj.get("path", "")), str(obj.get("method", "GET"))
        registered = DP.signer_name(spk, signers_path)

        def answer(code, body, rh=None):
            if registered:      # an answer only to his own registered keys: a stranger learns nothing
                rep = {"kind": KIND_REPLY, "id": str(obj.get("id", ""))[:40], "code": int(code), "body": _b64(body),
                       "headers": {k: str(v)[:200] for k, v in (rh or {}).items() if k in REPLY_HEADERS}}
                try:
                    relay.put(sealer.fingerprint(spk), sealer.seal(KIND_REPLY, rep, my_key, my_pem, spk))
                except (ValueError, OSError) as e:    # a full box, a relay away: recorded, and the pass goes on
                    rows.append(_row(ledger_path, M, "unanswered", bid, path, registered, "the answer could not be left: %s" % e))

        if env.get("kind") != KIND_REQ:
            rows.append(_row(ledger_path, M, "refused", bid, path, registered, "kind %s is not a request" % env.get("kind")))
            continue
        if not door_ok(path):
            rows.append(_row(ledger_path, M, "refused", bid, path, registered, "not a spore door"))
            answer(403, b'{"status":"error","message":"not a spore door"}')
            continue
        headers = obj.get("headers") or {}
        try:
            inner = base64.b64decode(headers.get("X-Operator-Pubkey", "")).decode()
        except Exception:                                         # noqa: BLE001
            inner = ""
        if _norm(inner) != _norm(spk):
            rows.append(_row(ledger_path, M, "refused", bid, path, registered, "the request is signed by another key than the block"))
            continue
        try:
            body = base64.b64decode(obj.get("body") or "")
        except Exception:                                         # noqa: BLE001
            rows.append(_row(ledger_path, M, "refused", bid, path, registered, "body is not base64"))
            continue
        ok, _addr, who, how = M.admit(_Req(method, path, headers), body, lambda a: False, signers_path=signers_path,
                                      peers_path=os.devnull, ledger_path=ledger_path, now=now, seen=seen)
        if not ok or how != "signed:operator":
            rows.append({"kind": "refused", "road": "spore", "block": bid, "path": path, "why": how})
            answer(403, json.dumps({"status": "error", "message": "refused on the spore road: %s" % how}).encode())
            continue
        got = forward(method, path, body, headers)
        code, rbody, rh = (tuple(got) + ({},))[:3]
        if len(rbody or b"") > MAX_BODY:
            code, rbody, rh = 413, json.dumps({"status": "error", "message": "the answer is %d bytes; the spore road carries %d"
                                               % (len(rbody), MAX_BODY)}).encode(), {"Content-Type": "application/json"}
        answer(code, rbody or b"", rh)
        rows.append({"kind": "answered", "road": "spore", "block": bid, "path": path, "who": who, "code": int(code)})
    return rows


def _row(ledger_path, M, kind, bid, path, who, why):
    row = {"kind": kind, "addr": "spore", "road": "spore", "block": bid, "path": path, "who": who or "", "why": str(why)[:200]}
    M._record(row, ledger_path)
    return row


# ---------------------------------------------------------------- the phone's call

def call(relay, sealer, method, path, body, headers, my_key, my_pem, pc_pem, timeout=90.0, poll_s=2.0,
         clock=time.time, sleep=time.sleep, proof_fn=None):
    """Leave the request, then collect this phone's box until the PC's answer with the same id arrives.
    (code, body bytes, headers), or None when TIMEOUT passes. A block not sealed by the PC's own key is ignored."""
    rid, block = wrap_request(sealer, method, path, body, headers, my_key, my_pem, pc_pem)
    relay.put(sealer.fingerprint(pc_pem), block)
    mine, deadline = sealer.fingerprint(my_pem), clock() + float(timeout)
    while True:
        proof = proof_fn(mine) if proof_fn else None
        for _bid, text in relay.take(mine, proof=proof):
            for env in sealer.blocks(text):
                try:
                    env, obj, _spk = sealer.open_env(env, my_key, my_pem, pc_pem)
                except sealer.error:
                    continue
                if env.get("kind") == KIND_REPLY and obj.get("id") == rid:
                    rh = obj.get("headers") if isinstance(obj.get("headers"), dict) else {}
                    return int(obj.get("code", 0)), base64.b64decode(obj.get("body") or ""), rh
        if clock() >= deadline:
            return None
        sleep(poll_s)


# ---------------------------------------------------------------- the PC's command line

def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="the spore road: a sealed, signed request through a relay that cannot read it")
    ap.add_argument("--serve-relay", action="store_true", help="run a relay (loopback unless --host says otherwise)")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=5097)
    ap.add_argument("--dir", default=os.path.join(HERE, "ops", "spore_relay"))
    ap.add_argument("--pc-pass", metavar="RELAY_URL", help="collect this PC's box once")
    ap.add_argument("--pc-loop", metavar="RELAY_URL", help="collect every --every seconds")
    ap.add_argument("--every", type=float, default=5.0)
    a = ap.parse_args(argv)
    if a.serve_relay:
        srv = make_relay_server(a.dir, a.host, a.port)
        print("relay on %s:%d, blocks in %s" % (a.host, srv.server_address[1], a.dir), flush=True)
        srv.serve_forever()
        return 0
    url = a.pc_pass or a.pc_loop
    if url:
        import covenant_sealed_mail as SM
        key = SM.my_key()
        pem = SM.pubkey_pem(key)
        relay = HttpRelay(url, key, pem)
        while True:
            for r in pc_pass(relay, key, pem):
                print(json.dumps(r), flush=True)
            if not a.pc_loop:
                return 0
            time.sleep(a.every)
    ap.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
