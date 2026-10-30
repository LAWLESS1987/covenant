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

Standalone check: verify_grid_ledger.py (imports no covenant code) lets a
stranger check that the command record was not rewritten (the raw-bytes hash
chain) and, given the gateway public key, that every row carries a valid gateway
signature. It does NOT re-run C1..C7 over each honored command; re-checking that
each one was authentic, authorized and in-bounds is an open item, not a claim.
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
# A signer chooses issued_utc and expires_utc, so an uncapped lifetime let a command
# dated more than WINDOW_S ago stay "fresh" while the C5 window never counted it
# (pre-merge review 2026-10-30: six authorized 15% sheds -> 90% against a 20% cap).
MAX_TTL_S = 900

# The class a command NEEDS is fixed by its ACTION, never chosen by the signer. The
# review reproduced a breaker_open labelled MONITOR passing with no token at all --
# one controller key defeating the together-vote. The map is an ALLOWLIST: an action
# not in it is REFUSED, not treated as ACTUATION, because C5 has bounds only for the
# actions it knows -- an unknown action carrying both tokens would pass uncapped.
# (Consult 2026-10-30, ChatGPT + Gemini; Grok preferred ACTUATION-by-default.)
# "halt" is not here: it never goes through authorize(), the gateway honors it on
# authenticity alone.
ACTION_CLASS = {"read": "MONITOR", "advise": "ADVISORY",
                "breaker_open": "ACTUATION", "breaker_close": "ACTUATION",
                "load_shed": "ACTUATION", "setpoint": "ACTUATION"}


def required_class(action):
    """The class `action` needs, or None for an action the guard does not know."""
    return ACTION_CLASS.get(action) if isinstance(action, str) else None

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


def _entry(signers, fpr):
    """One allowlist entry, or None. ops/grid_signers.json carries a string '_note'
    key; a bare signers.get(fpr) handed that string to .get() and raised, so a
    signer_fpr or issuer_fpr of '_note' crashed submit() before the row was written."""
    if not isinstance(signers, dict) or not isinstance(fpr, str):
        return None
    e = signers.get(fpr)
    return e if isinstance(e, dict) else None


def _int(v):
    """int, or None for anything that is not a plain integer (bool excluded)."""
    if isinstance(v, bool):
        return None
    try:
        return int(v)
    except Exception:  # noqa: BLE001
        return None


def _finite(v):
    if isinstance(v, bool):
        return None
    try:
        f = float(v)
    except Exception:  # noqa: BLE001
        return None
    return f if f == f and f not in (float("inf"), float("-inf")) else None


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


def make_heartbeat(issuer_fpr, priv_pem, ttl_s=600, now=None):
    """One deadman heartbeat row, signed by an authority-holder under its own domain.
    Before 2026-10-30 heartbeat_fresh read only expires_utc from the last line, so
    any process able to write the file -- the keyless reasoning host included --
    could append a far-future expiry and the deadman would never latch."""
    now = _now() if now is None else now
    hb = {"v": HEARTBEAT_DOMAIN.decode(), "issuer_fpr": issuer_fpr,
          "issued_utc": now, "expires_utc": now + ttl_s}
    hb["signature"] = _sign(HEARTBEAT_DOMAIN, dict(hb), priv_pem)
    return hb


def make_resume_token(latch_id, issuer_fpr, priv_pem, ttl_s=300, now=None):
    """An authority-holder's resume for ONE latch. Binding latch_id means a resume
    captured for an earlier halt cannot clear a later one inside its lifetime."""
    now = _now() if now is None else now
    tok = {"v": AUTHZ_DOMAIN.decode(), "scope": "resume", "latch_id": latch_id,
           "issuer_fpr": issuer_fpr, "issued_utc": now, "expires_utc": now + ttl_s}
    tok["signature"] = _sign(AUTHZ_DOMAIN, dict(tok), priv_pem)
    return tok


def _pub_from_priv(priv_pem):
    hashes, serialization, padding, _ = _crypto()
    if isinstance(priv_pem, str):
        priv_pem = priv_pem.encode()
    priv = serialization.load_pem_private_key(priv_pem, password=None)
    return priv.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo).decode()


# --------------------------------------------------------------- replay/window state
def _honored_rows(ledger=None):
    rows = []
    for raw in cc.read_ledger_lines(LEDGER if ledger is None else ledger):
        try:
            rows.append(json.loads(raw))
        except Exception:  # noqa: BLE001
            pass
    return rows


def _seen_nonces(ledger=None):
    out = set()
    for r in _honored_rows(ledger):
        if r.get("decision") == PERMIT:
            n = (r.get("command", {}).get("payload", {}) or {}).get("nonce")
            if n:
                out.add(n)
    return out


def _last_seq(signer_fpr, ledger=None):
    last = -1
    for r in _honored_rows(ledger):
        if r.get("decision") != PERMIT:
            continue
        p = r.get("command", {}).get("payload", {}) or {}
        if p.get("signer_fpr") == signer_fpr:
            last = max(last, _int(p.get("seq")) if _int(p.get("seq")) is not None else -1)
    return last


def _window(now, interlocks, ledger=None):
    """Counts honored commands by WHEN THE GATEWAY HONORED THEM (honored_utc, which
    the gateway writes), not by the signer-chosen issued_utc. A row written before
    honored_utc existed falls back to issued_utc, the later of the two times."""
    win = _int((interlocks or {}).get("WINDOW_S", 3600))
    win = 3600 if win is None else win
    ops, shed = 0, 0.0
    for r in _honored_rows(ledger):
        if r.get("decision") != PERMIT:
            continue
        p = r.get("command", {}).get("payload", {}) or {}
        t = max(_int(r.get("honored_utc")) or 0, _int(p.get("issued_utc")) or 0)
        if now - t > win:
            continue
        if p.get("action") in ("breaker_open", "breaker_close"):
            ops += 1
        if p.get("action") == "load_shed":
            shed += max(0.0, _finite((p.get("magnitude") or {}).get("pct", 0)) or 0.0)
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
    except Exception:  # noqa: BLE001
        return _dec(REFUSE, "C0", "malformed envelope")
    if not isinstance(payload, dict) or not isinstance(envelope, dict):
        return _dec(REFUSE, "C0", "malformed envelope")
    issued, expires, seq = (_int(payload.get("issued_utc")), _int(payload.get("expires_utc")),
                            _int(payload.get("seq")))
    if issued is None or expires is None or seq is None:
        return _dec(REFUSE, "C0", "issued_utc / expires_utc / seq not integers")

    # C1 AUTHENTICITY -- signature over _frame(CMD_DOMAIN, canon(payload-sans-tokens)).
    signer = _entry(signers, payload.get("signer_fpr"))
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
    # The class is DERIVED here, after authenticity, so a forged command is still
    # reported as unauthenticated; a class the payload carries is only checked
    # against it, never trusted (consult 2026-10-30: all three seats said so).
    # "C2-action" is its own label: an authentic halt evaluated by the snapshot
    # detectors lands here and must not read as an unauthenticated command.
    cls = required_class(payload.get("action"))
    if cls is None:
        return _dec(REFUSE, "C2-action", "unknown action %r -- not in the guard's action allowlist"
                    % (payload.get("action"),))

    # C3 FRESHNESS -- inside [issued-skew, expires], and a lifetime no longer than
    # MAX_TTL_S (interlocks may lower or raise it; unreadable interlocks HOLD at C5).
    max_ttl = _int((interlocks or {}).get("MAX_TTL_S", MAX_TTL_S)) if interlocks_ok is not False else MAX_TTL_S
    max_ttl = MAX_TTL_S if max_ttl is None else max_ttl
    if expires - issued <= 0 or expires - issued > max_ttl:
        return _dec(REFUSE, "C3", "command lifetime %ss outside (0, MAX_TTL_S=%s]"
                    % (expires - issued, max_ttl))
    if now < issued - CLOCK_SKEW_S:
        return _dec(REFUSE, "C3", "command is future-dated")
    if now > expires:
        return _dec(REFUSE, "C3", "command expired")

    # C4 NO REPLAY / MONOTONIC (state read from the chained ledger).
    if payload.get("nonce") in _seen_nonces(ledger):
        return _dec(REFUSE, "C4", "nonce already honored (replay)")
    if seq <= _last_seq(payload.get("signer_fpr"), ledger):
        return _dec(REFUSE, "C4", "seq not strictly increasing (reorder/replay)")

    # C5 INTERLOCK BOUNDS -- blast-radius caps. Unreadable -> treat as AT LIMIT (HOLD).
    if interlocks_ok is False:
        return _dec(HOLD, "C5", "interlock file unreadable -> treat as at-limit")
    il = interlocks if isinstance(interlocks, dict) else {}
    action = payload.get("action")
    mag = payload.get("magnitude") if isinstance(payload.get("magnitude"), dict) else {}
    w = _window(now, il, ledger)
    if action == "load_shed":
        pct = _finite(mag.get("pct"))
        if pct is None or pct <= 0 or pct > 100:
            # A negative pct used to pass and LOWER the window sum, buying budget back.
            return _dec(REFUSE, "C5", "load-shed pct must be a number in (0, 100]",
                        pct=mag.get("pct"))
        if w["shed_pct"] + pct > (_finite(il.get("MAX_SHED_PCT", 0)) or 0.0):
            return _dec(REFUSE, "C5", "load-shed exceeds MAX_SHED_PCT in window",
                        shed=w["shed_pct"], add=pct)
    if action in ("breaker_open", "breaker_close"):
        if w["breaker_ops"] + 1 > (_int(il.get("MAX_BREAKER_OPS", 0)) or 0):
            return _dec(REFUSE, "C5", "breaker ops exceed MAX_BREAKER_OPS in window",
                        ops=w["breaker_ops"])
    if action == "setpoint":
        rng = (il.get("setpoint_ranges") or {}).get(str(payload.get("zone")))
        val = _finite(mag.get("value"))
        try:
            lo, hi = float(rng[0]), float(rng[1])
        except Exception:  # noqa: BLE001
            lo = hi = None
        if val is None or lo is None or not (lo <= val <= hi):
            return _dec(REFUSE, "C5", "setpoint outside allowed range for zone")
    if (il.get("zone_allowlist") or []) and payload.get("zone") not in il["zone_allowlist"]:
        return _dec(REFUSE, "C5", "zone not in interlock allowlist")

    # C6 AUTHORITY-HOLDER OUT-OF-BAND (per class policy; actuation = together-vote).
    # The class is checked against the ACTION first: the signer may not pick a class
    # whose policy asks for fewer authority-holders than the action needs.
    claimed = payload.get("class")
    if claimed is not None and claimed != cls:
        return _dec(REFUSE, "C6", "class %r does not match action %r (needs %s)"
                    % (claimed, action, cls), required_class=cls)
    required = list(policy.get(cls, DEFAULT_POLICY.get(cls, list(AUTHORITY_ROLES))))
    if required:
        got_roles = set()
        toks = payload.get("authz_tokens")
        for tok in (toks if isinstance(toks, list) else []):
            if not isinstance(tok, dict):
                continue
            iss = _entry(signers, tok.get("issuer_fpr"))
            if not iss or iss.get("revoked") or iss.get("role") not in AUTHORITY_ROLES:
                continue
            if tok.get("cmd_sha256") != cmd_digest(payload):
                continue      # token bound to a DIFFERENT command -> ignored
            t_iss, t_exp = _int(tok.get("issued_utc")), _int(tok.get("expires_utc"))
            if t_iss is None or t_exp is None or now > t_exp or now < t_iss - CLOCK_SKEW_S:
                continue
            if t_exp - t_iss <= 0 or t_exp - t_iss > max_ttl:
                continue      # same lifetime cap as the command it authorizes
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
    # and externally signed. Belt-and-suspenders: GRID_NEVER_AUTOMATIC_WORDS are in
    # covenant_highway.NEVER_AUTOMATIC (GG1 checks the live tuple, NA1 the refusal).
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
    p = _payload_of(envelope)
    s = _entry(signers, p.get("signer_fpr"))
    if not s or s.get("revoked") or "halt" not in (s.get("allowed_actions") or []):
        return False
    if _fpr(envelope.get("pubkey", "")) != p.get("signer_fpr"):
        return False
    if s.get("pubkey_pem") and s["pubkey_pem"].strip() != str(envelope.get("pubkey", "")).strip():
        return False
    core = {k: v for k, v in p.items() if k != "authz_tokens"}
    return _verify(CMD_DOMAIN, core, envelope.get("signature", ""), envelope.get("pubkey", ""))


def _payload_of(envelope):
    p = envelope.get("payload") if isinstance(envelope, dict) else None
    return p if isinstance(p, dict) else {}


def _read_latch(path):
    """(latched, latch_id). The latch lives on disk so a restart -- a new gateway
    object -- cannot clear it; only clear_hold can. Before 2026-10-30 it was an
    instance attribute and constructing a fresh gateway silently resumed. A latch
    file that exists but cannot be read is LATCHED (fail closed)."""
    if not os.path.exists(path):
        return False, None
    st, ok = _load_json(path)
    if not ok or not isinstance(st, dict):
        return True, "unreadable"
    return bool(st.get("latched")), st.get("latch_id")


class GridEffectorGateway:
    def __init__(self, effector=None, gateway_priv_pem=None,
                 ledger=None, chain=None, heartbeat=None, safe_state=None):
        self.effector = effector or SimulatedEffector()
        self.gateway_priv_pem = gateway_priv_pem      # off-host in the real world
        # Resolved at call time, not def time: a default bound at definition kept
        # the production ops/ paths after a caller reassigned the module paths.
        self.ledger = LEDGER if ledger is None else ledger
        self.chain = CHAIN if chain is None else chain
        self.heartbeat = HEARTBEAT if heartbeat is None else heartbeat
        self.safe_state = SAFE_STATE if safe_state is None else safe_state

    @property
    def latched_hold(self):
        return _read_latch(self.safe_state)[0]

    def latch_id(self):
        return _read_latch(self.safe_state)[1]

    def _latch(self, why, now):
        st = {"latched": True, "latch_id": new_nonce(), "why": why, "latched_utc": now}
        tmp = self.safe_state + ".tmp"
        os.makedirs(os.path.dirname(self.safe_state) or ".", exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(st, fh, sort_keys=True)
        os.replace(tmp, self.safe_state)

    def _snapshot(self, envelope, now):
        return snapshot_detectors(envelope, now, ledger=self.ledger, chain=self.chain,
                                  heartbeat=self.heartbeat)

    def _record(self, envelope, decision, detector_snapshot, now=None):
        now = _now() if now is None else now
        prev_rows = _honored_rows(self.ledger)
        utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        row = {
            "seq": len(prev_rows),
            "utc": utc,
            # append_consent adds "t" when absent. Set it here so the gateway
            # signature covers the row exactly as stored: before 2026-10-30 the
            # field was added after signing and every gateway-signed row failed
            # verify_grid_ledger.py.
            "t": utc,
            "honored_utc": now,       # the C5 window counts by this, not issued_utc
            "command": envelope,
            "signer_fpr": _payload_of(envelope).get("signer_fpr"),
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
        try:
            return self._submit(envelope, now)
        except Exception as e:  # noqa: BLE001
            # Fail closed AND recorded: an input that crashes a check is a refusal a
            # person must see, not an attempt that leaves no row.
            d = _dec(REFUSE, "C0", "internal error while checking: %s" % type(e).__name__)
            self._record(envelope if isinstance(envelope, dict) else {"raw": repr(envelope)[:200]},
                         d, {}, now)
            return d

    def _submit(self, envelope, now):
        payload = _payload_of(envelope)
        # HALT INVERSION -- stopping is always the safe direction, honored even with a
        # stale heartbeat and even while latched.
        if payload.get("action") == "halt":
            if _halt_authentic(envelope, now):
                self._latch("halt", now)
                d = _dec(HOLD, "HALT", "halt honored: safe-state hold latched")
                self._record(envelope, d, self._snapshot(envelope, now), now)
                return d
            d = _dec(REFUSE, "C1", "halt command not authentic -- not honored")
            self._record(envelope, d, self._snapshot(envelope, now), now)
            return d
        if self.latched_hold:
            # Latched: nothing is authorized, so nothing consumes a nonce, a seq or
            # window budget, and the ledger never says PERMIT for a command that did
            # not run (before 2026-10-30 it did both).
            d = _dec(HOLD, "LATCHED", "safe-state hold in force; resume needs clear_hold")
            self._record(envelope, d, self._snapshot(envelope, now), now)
            return d
        if not heartbeat_fresh(now, self.heartbeat):
            self._latch("deadman", now)
            d = _dec(REFUSE, "C6-deadman", "authorization heartbeat stale -> safe-state hold")
            self._record(envelope, d, self._snapshot(envelope, now), now)
            return d
        d = authorize(envelope, now=now, ledger=self.ledger)
        self._record(envelope, d, self._snapshot(envelope, now), now)
        if d["decision"] == PERMIT:
            self.effector.apply(payload)
        return d

    def clear_hold(self, resume_tokens, now=None):
        """Authority-holder-only, off-band. Resuming is NEVER automatic -- a resume
        is exactly what an attacker wants. It needs, for EVERY role the policy names
        under "RESUME" (default: the ACTUATION roles, i.e. the together-vote), a
        fresh token scoped to 'resume' AND bound to the current latch_id. Resuming
        restores the ability to actuate, so it gets the same vote as actuation
        (consult 2026-10-30: ChatGPT, Gemini and Grok all said both). One token is
        accepted as a list of one."""
        now = _now() if now is None else now
        toks = resume_tokens if isinstance(resume_tokens, list) else [resume_tokens]
        need = self._resume_roles()
        got = sorted({r for r in (self._resume_valid(t, now) for t in toks) if r})
        ok_resume = bool(need) and all(r in got for r in need)
        d = _dec(PERMIT if ok_resume else REFUSE, None if ok_resume else "RESUME",
                 "resume honored: safe-state hold cleared" if ok_resume else
                 "resume refused (needs %s, valid tokens from %s)" % (need, got or "none"))
        self._record({"payload": {"action": "resume",
                                  "tokens": [t for t in toks if isinstance(t, dict)]}}, d, {}, now)
        if ok_resume:
            st = {"latched": False, "latch_id": None, "cleared_utc": now, "cleared_by": got}
            tmp = self.safe_state + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(st, fh, sort_keys=True)
            os.replace(tmp, self.safe_state)
        return ok_resume

    @staticmethod
    def _resume_roles():
        """The roles a resume needs. Declared policy (ops/grid_policy.json "RESUME",
        else its "ACTUATION"); unreadable policy -> DEFAULT_POLICY's together-vote. An
        empty list is never honored: some authority-holder always has to act."""
        pol, ok = _load_json(POLICY)
        pol = pol if ok and isinstance(pol, dict) else DEFAULT_POLICY
        roles = pol.get("RESUME", pol.get("ACTUATION", DEFAULT_POLICY["ACTUATION"]))
        roles = [r for r in (roles if isinstance(roles, list) else []) if r in AUTHORITY_ROLES]
        return roles or list(DEFAULT_POLICY["ACTUATION"])

    def _resume_valid(self, resume_token, now):
        """The role of a valid resume token, or None."""
        if not isinstance(resume_token, dict):
            return None
        latched, latch_id = _read_latch(self.safe_state)
        if not latched or latch_id in (None, "unreadable"):
            return False      # nothing to clear, or an unreadable latch a person must fix
        signers, ok = _load_json(SIGNERS)
        if not ok:
            return False
        iss = _entry(signers, resume_token.get("issuer_fpr"))
        if not iss or iss.get("role") not in AUTHORITY_ROLES or iss.get("revoked"):
            return False
        t_iss, t_exp = _int(resume_token.get("issued_utc")), _int(resume_token.get("expires_utc"))
        if resume_token.get("scope") != "resume" or t_exp is None or t_iss is None or now > t_exp:
            return False
        if t_exp - t_iss <= 0 or t_exp - t_iss > MAX_TTL_S or now < t_iss - CLOCK_SKEW_S:
            return False
        if resume_token.get("latch_id") != latch_id:
            return False
        tcore = {k: v for k, v in resume_token.items() if k != "signature"}
        if not _verify(AUTHZ_DOMAIN, tcore, resume_token.get("signature", ""), iss.get("pubkey_pem", "")):
            return None
        return iss.get("role")     # every failure above returns a falsy value


# --------------------------------------------------------------- heartbeat (deadman)
def heartbeat_fresh(now=None, path=None, limit_s=600, signers=None, signers_ok=None):
    """Fresh iff the LAST heartbeat row is signed under HEARTBEAT_DOMAIN by a
    non-revoked authority-holder, is not future-dated, has not expired, and claims
    a lifetime no longer than limit_s. Anything else -- unsigned, signed by a
    controller, unreadable signers, a far-future expiry -- is stale."""
    now = _now() if now is None else now
    path = HEARTBEAT if path is None else path
    if signers is None and signers_ok is None:
        signers, signers_ok = _load_json(SIGNERS)
    if signers_ok is False:
        return False
    try:
        last = None
        with open(path, encoding="utf-8") as fh:
            for ln in fh:
                ln = ln.strip()
                if ln:
                    last = json.loads(ln)
        if not isinstance(last, dict):
            return False
        iss = _entry(signers, last.get("issuer_fpr"))
        if not iss or iss.get("revoked") or iss.get("role") not in AUTHORITY_ROLES:
            return False
        t_iss, t_exp = _int(last.get("issued_utc")), _int(last.get("expires_utc"))
        if t_iss is None or t_exp is None:
            return False
        if t_exp - t_iss <= 0 or t_exp - t_iss > limit_s or now < t_iss - CLOCK_SKEW_S or now > t_exp:
            return False
        core = {k: v for k, v in last.items() if k != "signature"}
        return _verify(HEARTBEAT_DOMAIN, core, last.get("signature", ""), iss.get("pubkey_pem", ""))
    except Exception:  # noqa: BLE001
        return False


# --------------------------------------------------------------- ALARM-only detectors
# Every detector returns {"state": PRESENT|ABSENT|UNKNOWN, "measured": {}} and has
# NO remedy: a forged/replayed/unauthorized command or a tamper is a thing a person
# (operator or Tetsu) must SEE, never a thing the engine "heals". UNKNOWN is never a
# pass (covenant_highway P20).
def _st(state, **m):
    return {"state": state, "measured": m}


def detect_grid_command_unauthenticated(envelope=None, now=None, ledger=None, **kw):
    if envelope is None:
        return _st(ABSENT, note="no pending command")
    d = authorize(envelope, now=now, ledger=ledger)
    if d["failed_check"] in ("C1", "C2") and d["decision"] == REFUSE:
        return _st(PRESENT, reason=d["reason"])
    if d["decision"] == HOLD and d["failed_check"] == "C2":
        return _st(UNKNOWN, reason=d["reason"])
    return _st(ABSENT)


def detect_grid_command_replay(envelope=None, now=None, ledger=None, **kw):
    if envelope is None:
        return _st(ABSENT)
    d = authorize(envelope, now=now, ledger=ledger)
    if d["failed_check"] in ("C3", "C4") and d["decision"] == REFUSE:
        return _st(PRESENT, reason=d["reason"])
    return _st(ABSENT)


def detect_grid_actuation_without_authority(envelope=None, now=None, ledger=None, **kw):
    if envelope is None:
        return _st(ABSENT)
    d = authorize(envelope, now=now, ledger=ledger)
    if d["failed_check"] in ("C6", "C6-deadman") and d["decision"] == REFUSE:
        return _st(PRESENT, reason=d["reason"])
    return _st(ABSENT)


def detect_grid_interlock_breach(envelope=None, now=None, ledger=None, **kw):
    if envelope is None:
        return _st(ABSENT)
    d = authorize(envelope, now=now, ledger=ledger)
    if d["failed_check"] == "C5":
        return _st(PRESENT if d["decision"] == REFUSE else UNKNOWN, reason=d["reason"])
    return _st(ABSENT)


def detect_grid_ledger_broken(ledger=None, chain=None, **kw):
    ledger = LEDGER if ledger is None else ledger
    chain = CHAIN if chain is None else chain
    rows = cc.read_ledger_lines(ledger)
    if not rows:
        return _st(ABSENT, note="no ledger yet")
    ok, findings = cc.verify(ledger_path=ledger, chain_path=chain)
    return _st(ABSENT) if ok else _st(PRESENT, findings=findings[:3])


def detect_grid_authz_channel_lost(now=None, path=None, heartbeat=None, **kw):
    path = path or heartbeat or HEARTBEAT
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
# actuation, "load_shed" avoids matching unrelated words). Wired into the live
# tuple on 2026-10-30; GG1 fails if any of these leaves it.
GRID_NEVER_AUTOMATIC_WORDS = ("grid", "breaker", "relay", "feeder", "substation",
                              "setpoint", "load_shed", "actuat", "scada", "intertie")


def snapshot_detectors(envelope=None, now=None, ledger=None, chain=None, heartbeat=None):
    """Every detector over the GIVEN ledger/chain/heartbeat. Before 2026-10-30 a
    gateway built on its own ledger snapshotted the default ops/ ledger instead, so
    its signed rows carried another ledger's evidence."""
    out = {}
    for name, fn in GRID_DETECTORS.items():
        try:
            out[name] = fn(envelope=envelope, now=now, ledger=ledger, chain=chain,
                           heartbeat=heartbeat)["state"]
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
