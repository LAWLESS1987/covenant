#!/usr/bin/env python3
"""
covenant_grid_guard.py -- a fail-closed, PROPOSE-ONLY authorizer for grid /
ICS-OT actuation.

REFERENCE IMPLEMENTATION ONLY. It is wired to a SimulatedEffector, bound to no
real grid, speaks no field protocol (DNP3 / IEC-61850 / Modbus), and contains no
offensive code. It models the threat -- "if the covenant were plugged into
infrastructure, how do we keep a cyber-attacker from seizing control?" -- and
builds the guard, so a real driver is a drop-in (replace SimulatedEffector).

It is the OT/ICS sibling of covenant_head_commit.py + covenant_consent_chain.py
and extends docs/TAKEOVER_RESISTANCE.md ("sovereignty of record + consent; armed
only by off-host keys + out-of-band authorization; tamper is alarm-only, never
auto-healed") from rewriting FILES to issuing physical ACTIONS.

AUTHORITY MODEL (operator's correction, 2026-10-30: "tetsu is not human and has
authority"). Authorization is by AUTHORITY-HOLDER, never by "being human". The
authority-holders are the operator (full) and Tetsu (bounded). For the highest
criticality -- actuation -- the policy is TOGETHER-VOTE: both an operator-role
and a tetsu-role authorization token. Which roles each class needs is a declared
policy (ops/grid_policy.json), not baked in, so the operator and Tetsu set it.

THE TWO PLANES.
  - Reasoning plane (this host): may SENSE and PROPOSE. Holds NO signing key and
    NO authority key, so it structurally cannot produce a PERMIT.
  - Actuation gateway: the ONLY executor. Honors a command only when a complete,
    signed, authorized, in-bounds, non-replayed envelope arrives AND a fresh
    authorization heartbeat is present. Default state is SAFE (hold-last / keep
    serving); refusing a command withholds a CHANGE and so can never itself trip
    the grid.

Standalone proof: verify_grid_ledger.py (imports no covenant code) lets a
stranger check every honored command was authentic, authorized and in-bounds and
that the record was not rewritten.
"""
import base64
import hashlib
import json
import os
import secrets
import time

# ONE signing scheme for the whole project: reuse the HEAD-commitment framing and
# canonicalization verbatim so a verifier needs no new primitive.
from covenant_head_commit import _frame, _canon
import covenant_consent_chain as cc

HERE = os.path.dirname(os.path.abspath(__file__))

# Fresh domains: a HEAD-commitment or consent signature can never be cross-replayed
# as a grid command, and a command signature can never be replayed as an authz token.
CMD_DOMAIN = b"COVENANT_GRIDCMD_V1"
AUTHZ_DOMAIN = b"COVENANT_GRID_AUTHZ_V1"
HEARTBEAT_DOMAIN = b"COVENANT_GRID_HEARTBEAT_V1"

LEDGER = os.path.join(HERE, "ops", "grid_commands.jsonl")
CHAIN = os.path.join(HERE, "ops", "grid_commands.chain.jsonl")
SIGNERS = os.path.join(HERE, "ops", "grid_signers.json")
INTERLOCKS = os.path.join(HERE, "ops", "grid_interlocks.json")
POLICY = os.path.join(HERE, "ops", "grid_policy.json")
SAFE_STATE = os.path.join(HERE, "ops", "GRID_SAFE_STATE.json")
HEARTBEAT = os.path.join(HERE, "ops", "grid_authz_heartbeat.jsonl")

AUTHORITY_ROLES = ("operator", "tetsu")   # who may authorize; NOT "human"
CLOCK_SKEW_S = 120

PERMIT, HOLD, REFUSE = "PERMIT", "HOLD", "REFUSE"
PRESENT, ABSENT, UNKNOWN = "PRESENT", "ABSENT", "UNKNOWN"

# Default policy if ops/grid_policy.json is absent/unreadable -> the most RESTRICTIVE
# reading (fail-closed): actuation needs BOTH authority-holders (together-vote).
DEFAULT_POLICY = {
    "ACTUATION": ["operator", "tetsu"],   # together-vote; the floor the operator proposed
    "MONITOR": [],
    "ADVISORY": [],
}


# --------------------------------------------------------------------------- utils
def _now():
    return int(time.time())


def _sha_hex(b):
    return hashlib.sha256(b).hexdigest()


def _load_json(path):
    """Fail-closed reader: (obj, ok). ok=False means the authorizer must treat the
    input as worst-case (HOLD / at-limit), never as permission."""
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh), True
    except Exception:  # noqa: BLE001
        return None, False


def new_nonce():
    return secrets.token_hex(16)


# --------------------------------------------------------------- crypto (lazy load)
def _crypto():
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.exceptions import InvalidSignature
    return hashes, serialization, padding, InvalidSignature


def _pss(padding, hashes):
    return padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                       salt_length=padding.PSS.MAX_LENGTH)


def _sign(domain, payload, priv_pem):
    """Sign _frame(domain, _canon(payload)) with an RSA private key (PEM bytes/str).
    Reference/test + the OFF-HOST authority use this; the reasoning host does not."""
    hashes, serialization, padding, _ = _crypto()
    if isinstance(priv_pem, str):
        priv_pem = priv_pem.encode()
    priv = serialization.load_pem_private_key(priv_pem, password=None)
    sig = priv.sign(_frame(domain, _canon(payload)), _pss(padding, hashes), hashes.SHA256())
    return base64.b64encode(sig).decode()


def _verify(domain, payload, sig_b64, pub_pem):
    hashes, serialization, padding, InvalidSignature = _crypto()
    try:
        if isinstance(pub_pem, str):
            pub_pem = pub_pem.encode()
        pub = serialization.load_pem_public_key(pub_pem)
        pub.verify(base64.b64decode(sig_b64), _frame(domain, _canon(payload)),
                   _pss(padding, hashes), hashes.SHA256())
        return True
    except (InvalidSignature, ValueError, TypeError, Exception):  # noqa: BLE001
        return False


def _fpr(pub_pem):
    if isinstance(pub_pem, str):
        pub_pem = pub_pem.encode()
    return _sha_hex(pub_pem)[:16]


# --------------------------------------------------------------- envelope builders
def build_command(seq, action, zone, magnitude, cls, signer_fpr,
                  ttl_s=300, authz_tokens=None, now=None):
    now = _now() if now is None else now
    return {
        "v": CMD_DOMAIN.decode(),
        "seq": int(seq),
        "nonce": new_nonce(),
        "issued_utc": now,
        "expires_utc": now + ttl_s,
        "signer_fpr": signer_fpr,
        "class": cls,
        "action": action,
        "zone": zone,
        "magnitude": magnitude or {},
        "authz_tokens": authz_tokens or [],
    }


def sign_command(payload, priv_pem):
    """Returns an envelope. Signs the payload WITHOUT its authz_tokens, so tokens
    (which bind the command by hash) can be attached without invalidating the sig."""
    core = {k: v for k, v in payload.items() if k != "authz_tokens"}
    sig = _sign(CMD_DOMAIN, core, priv_pem)
    pub_pem = _pub_from_priv(priv_pem)
    return {"payload": payload, "signature": sig, "pubkey": pub_pem}


def cmd_digest(payload):
    core = {k: v for k, v in payload.items() if k != "authz_tokens"}
    return _sha_hex(_canon(core))


def make_authz_token(payload, issuer_fpr, priv_pem, ttl_s=300, now=None):
    """An authority-holder authorizes ONE command (bound by cmd_sha256)."""
    now = _now() if now is None else now
    token = {
        "v": AUTHZ_DOMAIN.decode(),
        "cmd_sha256": cmd_digest(payload),
        "issuer_fpr": issuer_fpr,
        "issued_utc": now,
        "expires_utc": now + ttl_s,
    }
    token["signature"] = _sign(AUTHZ_DOMAIN, {k: v for k, v in token.items()}, priv_pem)
    return token


def _pub_from_priv(priv_pem):
    hashes, serialization, padding, _ = _crypto()
    if isinstance(priv_pem, str):
        priv_pem = priv_pem.encode()
    priv = serialization.load_pem_private_key(priv_pem, password=None)
    return priv.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo).decode()


# --------------------------------------------------------------- replay/window state
def _honored_rows(ledger=LEDGER):
    rows = []
    for raw in cc.read_ledger_lines(ledger):
        try:
            rows.append(json.loads(raw))
        except Exception:  # noqa: BLE001
            pass
    return rows


def _seen_nonces(ledger=LEDGER):
    out = set()
    for r in _honored_rows(ledger):
        if r.get("decision") == PERMIT:
            n = (r.get("command", {}).get("payload", {}) or {}).get("nonce")
            if n:
                out.add(n)
    return out


def _last_seq(signer_fpr, ledger=LEDGER):
    last = -1
    for r in _honored_rows(ledger):
        if r.get("decision") != PERMIT:
            continue
        p = r.get("command", {}).get("payload", {}) or {}
        if p.get("signer_fpr") == signer_fpr:
            last = max(last, int(p.get("seq", -1)))
    return last


def _window(now, interlocks, ledger=LEDGER):
    win = int((interlocks or {}).get("WINDOW_S", 3600))
    ops, shed = 0, 0.0
    for r in _honored_rows(ledger):
        if r.get("decision") != PERMIT:
            continue
        p = r.get("command", {}).get("payload", {}) or {}
        if now - int(p.get("issued_utc", 0)) > win:
            continue
        if p.get("action") in ("breaker_open", "breaker_close"):
            ops += 1
        if p.get("action") == "load_shed":
            shed += float((p.get("magnitude") or {}).get("pct", 0))
    return {"breaker_ops": ops, "shed_pct": shed}


# --------------------------------------------------------------- the authorizer
def _dec(decision, check, reason, **measured):
    return {"decision": decision, "failed_check": check, "reason": reason,
            "measured": measured}


def authorize(envelope, now=None, signers=None, signers_ok=None,
              interlocks=None, interlocks_ok=None, policy=None, ledger=None):
    """Pure decision over one envelope. PERMIT iff C1..C7 all hold. Any definitive
    failure -> REFUSE; any unreadable input -> HOLD (never PERMIT on missing
    evidence). A non-PERMIT never actuates, so it can never itself trip the grid."""
    now = _now() if now is None else now
    if ledger is None:                       # resolve at call time, not def time
        ledger = LEDGER
    # Load from disk only when the caller gave neither the data nor an explicit
    # ok-flag; an explicit signers_ok=False means "treat as unreadable", don't reload.
    if signers is None and signers_ok is None:
        signers, signers_ok = _load_json(SIGNERS)
    if interlocks is None and interlocks_ok is None:
        interlocks, interlocks_ok = _load_json(INTERLOCKS)
    if policy is None:
        pol, pol_ok = _load_json(POLICY)
        policy = pol if pol_ok and isinstance(pol, dict) else DEFAULT_POLICY

    try:
        payload = envelope["payload"]
        cls = payload["class"]
    except Exception:  # noqa: BLE001
        return _dec(REFUSE, "C0", "malformed envelope")

    # C1 AUTHENTICITY -- signature over _frame(CMD_DOMAIN, canon(payload-sans-tokens)).
    signer = (signers or {}).get(payload.get("signer_fpr", "")) if signers else None
    if signers_ok is False:
        return _dec(HOLD, "C2", "signer allowlist unreadable -> fail closed")
    if not signer:
        return _dec(REFUSE, "C2", "signer not in allowlist")
    core = {k: v for k, v in payload.items() if k != "authz_tokens"}
    if _fpr(envelope.get("pubkey", "")) != payload.get("signer_fpr"):
        return _dec(REFUSE, "C1", "pubkey fingerprint != signer_fpr")
    if signer.get("pubkey_pem") and signer["pubkey_pem"].strip() != str(envelope.get("pubkey", "")).strip():
        return _dec(REFUSE, "C1", "pubkey does not match the allowlisted key for this signer")
    if not _verify(CMD_DOMAIN, core, envelope.get("signature", ""), envelope.get("pubkey", "")):
        return _dec(REFUSE, "C1", "command signature invalid")

    # C2 AUTHORIZED SIGNER -- role controller, not revoked, action/zone in grant.
    if signer.get("revoked"):
        return _dec(REFUSE, "C2", "signer revoked")
    if signer.get("role") != "controller":
        return _dec(REFUSE, "C2", "signer is not a controller key")
    if payload.get("action") not in (signer.get("allowed_actions") or []):
        return _dec(REFUSE, "C2", "action not in signer's grant")
    if (signer.get("zones") or []) and payload.get("zone") not in signer["zones"]:
        return _dec(REFUSE, "C2", "zone not in signer's grant")

    # C3 FRESHNESS.
    if now < int(payload.get("issued_utc", 0)) - CLOCK_SKEW_S:
        return _dec(REFUSE, "C3", "command is future-dated")
    if now > int(payload.get("expires_utc", 0)):
        return _dec(REFUSE, "C3", "command expired")

    # C4 NO REPLAY / MONOTONIC (state read from the chained ledger).
    if payload.get("nonce") in _seen_nonces(ledger):
        return _dec(REFUSE, "C4", "nonce already honored (replay)")
    if int(payload.get("seq", -1)) <= _last_seq(payload.get("signer_fpr"), ledger):
        return _dec(REFUSE, "C4", "seq not strictly increasing (reorder/replay)")

    # C5 INTERLOCK BOUNDS -- blast-radius caps. Unreadable -> treat as AT LIMIT (HOLD).
    if interlocks_ok is False:
        return _dec(HOLD, "C5", "interlock file unreadable -> treat as at-limit")
    il = interlocks or {}
    action = payload.get("action")
    mag = payload.get("magnitude") or {}
    w = _window(now, il, ledger)
    if action == "load_shed":
        if w["shed_pct"] + float(mag.get("pct", 0)) > float(il.get("MAX_SHED_PCT", 0)):
            return _dec(REFUSE, "C5", "load-shed exceeds MAX_SHED_PCT in window",
                        shed=w["shed_pct"], add=mag.get("pct"))
    if action in ("breaker_open", "breaker_close"):
        if w["breaker_ops"] + 1 > int(il.get("MAX_BREAKER_OPS", 0)):
            return _dec(REFUSE, "C5", "breaker ops exceed MAX_BREAKER_OPS in window",
                        ops=w["breaker_ops"])
    if action == "setpoint":
        rng = (il.get("setpoint_ranges") or {}).get(str(payload.get("zone")))
        if not rng or not (float(rng[0]) <= float(mag.get("value", 0)) <= float(rng[1])):
            return _dec(REFUSE, "C5", "setpoint outside allowed range for zone")
    if (il.get("zone_allowlist") or []) and payload.get("zone") not in il["zone_allowlist"]:
        return _dec(REFUSE, "C5", "zone not in interlock allowlist")

    # C6 AUTHORITY-HOLDER OUT-OF-BAND (per class policy; actuation = together-vote).
    required = list(policy.get(cls, DEFAULT_POLICY.get(cls, list(AUTHORITY_ROLES))))
    if required:
        got_roles = set()
        for tok in (payload.get("authz_tokens") or []):
            iss = (signers or {}).get(tok.get("issuer_fpr", ""))
            if not iss or iss.get("revoked") or iss.get("role") not in AUTHORITY_ROLES:
                continue
            if tok.get("cmd_sha256") != cmd_digest(payload):
                continue      # token bound to a DIFFERENT command -> ignored
            if now > int(tok.get("expires_utc", 0)):
                continue
            tcore = {k: v for k, v in tok.items() if k != "signature"}
            if _verify(AUTHZ_DOMAIN, tcore, tok.get("signature", ""), iss.get("pubkey_pem", "")):
                got_roles.add(iss.get("role"))
        missing = [r for r in required if r not in got_roles]
        if missing:
            return _dec(REFUSE, "C6",
                        "missing authority-holder authorization: %s" % ", ".join(missing),
                        required=required, got=sorted(got_roles))

    # C7 PLANE SEPARATION is structural: the reasoning host holds no key, so it
    # cannot have reached C1+C6 at all. If we got here the envelope was complete
    # and externally signed. (Belt-and-suspenders wiring into covenant_highway's
    # NEVER_AUTOMATIC is the commit-time step; see docs/GRID_PROTECTION.md.)
    return _dec(PERMIT, None, "all checks passed", **{"class": cls, "action": action})


# --------------------------------------------------------------- the gateway
class SimulatedEffector:
    """The pluggable boundary. apply() RECORDS an intended action and touches no
    hardware. A real deployment replaces this with a protocol driver that puts the
    signature check INSIDE itself and defaults to the last safe state on loss of
    the guard -- PHYSICALLY wired interlocks this repo cannot build or test."""
    def __init__(self):
        self.actuated = []

    def apply(self, payload):
        self.actuated.append({"action": payload.get("action"), "zone": payload.get("zone"),
                              "magnitude": payload.get("magnitude"), "t": _now()})
        return True


def _halt_authentic(envelope, now=None):
    """A halt is honored on AUTHENTICITY alone -- a valid signature from an
    allowlisted, non-revoked signer whose grant includes 'halt'. Freshness, replay
    and authority checks are deliberately skipped: stopping is always the safe
    direction, and a replayed halt only re-latches the safe-state hold."""
    signers, ok = _load_json(SIGNERS)
    if not ok or not signers:
        return False
    p = envelope.get("payload", {})
    s = signers.get(p.get("signer_fpr", ""))
    if not s or s.get("revoked") or "halt" not in (s.get("allowed_actions") or []):
        return False
    if _fpr(envelope.get("pubkey", "")) != p.get("signer_fpr"):
        return False
    core = {k: v for k, v in p.items() if k != "authz_tokens"}
    return _verify(CMD_DOMAIN, core, envelope.get("signature", ""), envelope.get("pubkey", ""))


class GridEffectorGateway:
    def __init__(self, effector=None, gateway_priv_pem=None,
                 ledger=LEDGER, chain=CHAIN, heartbeat=HEARTBEAT):
        self.effector = effector or SimulatedEffector()
        self.gateway_priv_pem = gateway_priv_pem      # off-host in the real world
        self.ledger, self.chain, self.heartbeat = ledger, chain, heartbeat
        self.latched_hold = False

    def _record(self, envelope, decision, detector_snapshot):
        prev_rows = _honored_rows(self.ledger)
        row = {
            "seq": len(prev_rows),
            "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "command": envelope,
            "signer_fpr": envelope.get("payload", {}).get("signer_fpr"),
            "decision": decision["decision"],
            "failed_check": decision["failed_check"],
            "reason": decision["reason"],
            "detector_snapshot": detector_snapshot,
        }
        if self.gateway_priv_pem:
            row["gateway_sig"] = _sign(CMD_DOMAIN, row, self.gateway_priv_pem)
        cc.append_consent(row, ledger_path=self.ledger, chain_path=self.chain)
        return row

    def submit(self, envelope, now=None):
        now = _now() if now is None else now
        payload = envelope.get("payload", {})
        # HALT INVERSION -- stopping is always the safe direction, honored even with a
        # stale heartbeat and even while latched.
        if payload.get("action") == "halt":
            if _halt_authentic(envelope, now):
                self.latched_hold = True
                d = _dec(HOLD, "HALT", "halt honored: safe-state hold latched")
                self._record(envelope, d, snapshot_detectors(envelope, now))
                return d
            d = _dec(REFUSE, "C1", "halt command not authentic -- not honored")
            self._record(envelope, d, snapshot_detectors(envelope, now))
            return d
        if not heartbeat_fresh(now, self.heartbeat):
            self.latched_hold = True
            d = _dec(REFUSE, "C6-deadman", "authorization heartbeat stale -> safe-state hold")
            self._record(envelope, d, snapshot_detectors(envelope, now))
            return d
        d = authorize(envelope, now=now, ledger=self.ledger)
        self._record(envelope, d, snapshot_detectors(envelope, now))
        if d["decision"] == PERMIT and not self.latched_hold:
            self.effector.apply(payload)
        return d

    def clear_hold(self, resume_token, now=None):
        """Authority-holder-only, off-band. Resuming is NEVER automatic -- a resume
        is exactly what an attacker wants, so it needs a fresh authority-holder
        token scoped to 'resume'."""
        now = _now() if now is None else now
        signers, ok = _load_json(SIGNERS)
        if not ok:
            return False
        iss = (signers or {}).get(resume_token.get("issuer_fpr", "")) if signers else None
        if not iss or iss.get("role") not in AUTHORITY_ROLES or iss.get("revoked"):
            return False
        if resume_token.get("scope") != "resume" or now > int(resume_token.get("expires_utc", 0)):
            return False
        tcore = {k: v for k, v in resume_token.items() if k != "signature"}
        if not _verify(AUTHZ_DOMAIN, tcore, resume_token.get("signature", ""), iss.get("pubkey_pem", "")):
            return False
        self.latched_hold = False
        return True


# --------------------------------------------------------------- heartbeat (deadman)
def heartbeat_fresh(now=None, path=HEARTBEAT, limit_s=600):
    now = _now() if now is None else now
    try:
        last = None
        with open(path, encoding="utf-8") as fh:
            for ln in fh:
                ln = ln.strip()
                if ln:
                    last = json.loads(ln)
        if not last:
            return False
        return now <= int(last.get("expires_utc", 0))
    except Exception:  # noqa: BLE001
        return False


# --------------------------------------------------------------- ALARM-only detectors
# Every detector returns {"state": PRESENT|ABSENT|UNKNOWN, "measured": {}} and has
# NO remedy: a forged/replayed/unauthorized command or a tamper is a thing a person
# (operator or Tetsu) must SEE, never a thing the engine "heals". UNKNOWN is never a
# pass (covenant_highway P20).
def _st(state, **m):
    return {"state": state, "measured": m}


def detect_grid_command_unauthenticated(envelope=None, **kw):
    if envelope is None:
        return _st(ABSENT, note="no pending command")
    d = authorize(envelope)
    if d["failed_check"] in ("C1", "C2") and d["decision"] == REFUSE:
        return _st(PRESENT, reason=d["reason"])
    if d["decision"] == HOLD and d["failed_check"] == "C2":
        return _st(UNKNOWN, reason=d["reason"])
    return _st(ABSENT)


def detect_grid_command_replay(envelope=None, now=None, **kw):
    if envelope is None:
        return _st(ABSENT)
    d = authorize(envelope, now=now)
    if d["failed_check"] in ("C3", "C4") and d["decision"] == REFUSE:
        return _st(PRESENT, reason=d["reason"])
    return _st(ABSENT)


def detect_grid_actuation_without_authority(envelope=None, now=None, **kw):
    if envelope is None:
        return _st(ABSENT)
    d = authorize(envelope, now=now)
    if d["failed_check"] in ("C6", "C6-deadman") and d["decision"] == REFUSE:
        return _st(PRESENT, reason=d["reason"])
    return _st(ABSENT)


def detect_grid_interlock_breach(envelope=None, now=None, **kw):
    if envelope is None:
        return _st(ABSENT)
    d = authorize(envelope, now=now)
    if d["failed_check"] == "C5":
        return _st(PRESENT if d["decision"] == REFUSE else UNKNOWN, reason=d["reason"])
    return _st(ABSENT)


def detect_grid_ledger_broken(ledger=LEDGER, chain=CHAIN, **kw):
    rows = cc.read_ledger_lines(ledger)
    if not rows:
        return _st(ABSENT, note="no ledger yet")
    ok, findings = cc.verify(ledger_path=ledger, chain_path=chain)
    return _st(ABSENT) if ok else _st(PRESENT, findings=findings[:3])


def detect_grid_authz_channel_lost(now=None, path=HEARTBEAT, **kw):
    if not os.path.exists(path):
        return _st(UNKNOWN, note="no heartbeat channel in this reference")
    return _st(ABSENT) if heartbeat_fresh(now, path) else _st(PRESENT,
               note="authorization heartbeat stale -> gateway should be latched to safe-state hold")


def detect_grid_pattern_anomaly(envelope=None, now=None, ledger=None, **kw):
    """ALARM-only, OPTIONAL redundant SNN witness (covenant_grid_snn) over the
    stream of ALREADY-honored commands -- a different-mechanism eye on the one
    thing C1..C7 cannot see: an attack made of individually in-bounds commands.
    Deferred import so the guard never hard-depends on it or on numpy/torch;
    absent or erroring -> UNKNOWN (never ABSENT: an absent witness is not 'all
    clear', covenant_highway P20). It can recommend a HOLD a person must SEE; it
    is NEVER called by authorize() (a tested invariant, test_gs1)."""
    try:
        from covenant_grid_snn import pattern_anomaly_state
    except Exception:  # noqa: BLE001
        return _st(UNKNOWN, note="snn witness unavailable (optional module/deps absent)")
    try:
        return pattern_anomaly_state(envelope=envelope, now=now, ledger=ledger)
    except Exception as e:  # noqa: BLE001
        return _st(UNKNOWN, note="snn witness error: %s" % type(e).__name__)


GRID_DETECTORS = {
    "grid_command_unauthenticated": detect_grid_command_unauthenticated,
    "grid_command_replay": detect_grid_command_replay,
    "grid_actuation_without_authority": detect_grid_actuation_without_authority,
    "grid_interlock_breach": detect_grid_interlock_breach,
    "grid_ledger_broken": detect_grid_ledger_broken,
    "grid_authz_channel_lost": detect_grid_authz_channel_lost,
    "grid_pattern_anomaly": detect_grid_pattern_anomaly,   # ALARM-only SNN witness
}

# The grid words that must join covenant_highway.NEVER_AUTOMATIC at commit time so
# apply_remedy's INVARIANT 1b refuses ANY grid-touching remedy whatever class it
# claims. Chosen to avoid substring collisions with existing remedies' `touches`
# (e.g. bare "trip" matches "strip", so it is excluded; "actuat" covers actuate/
# actuation, "load_shed" avoids matching unrelated words). Wiring + a both-ways
# test + a deploy-pin refresh are the reviewed commit step, not done here.
GRID_NEVER_AUTOMATIC_WORDS = ("grid", "breaker", "relay", "feeder", "substation",
                              "setpoint", "load_shed", "actuat", "scada", "intertie")


def snapshot_detectors(envelope=None, now=None):
    out = {}
    for name, fn in GRID_DETECTORS.items():
        try:
            out[name] = fn(envelope=envelope, now=now)["state"]
        except Exception:  # noqa: BLE001
            out[name] = UNKNOWN
    return out


# --------------------------------------------------------------- CLI
def main(argv=None):
    import sys
    argv = sys.argv[1:] if argv is None else argv
    cmd = argv[0] if argv else "status"
    if cmd == "status":
        print("grid-guard: reference implementation, PROPOSE-ONLY, no real grid bound.")
        print("detectors:", json.dumps(snapshot_detectors(), indent=2))
        print("ledger:", LEDGER, "| chain intact:",
              cc.verify(ledger_path=LEDGER, chain_path=CHAIN)[0])
        return 0
    if cmd == "simulate" and len(argv) > 1:
        env, ok = _load_json(argv[1])
        if not ok:
            print("could not read envelope:", argv[1]); return 2
        print(json.dumps(authorize(env), indent=2))
        return 0
    if cmd == "verify":
        ok, findings = cc.verify(ledger_path=LEDGER, chain_path=CHAIN)
        print("PASS" if ok else "FAIL")
        for f in findings:
            print("  -", f)
        return 0 if ok else 1
    print("usage: covenant_grid_guard.py [status|simulate <envelope.json>|verify]")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
