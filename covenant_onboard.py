#!/usr/bin/env python3
"""covenant_onboard.py -- the highway's AUTO_GATED lane: auto-onboard a KNOWN node.

ASKED 2026-11-02: the operator chose to "loosen autonomy" for the mycelial
highway and to "create its own lane." The highway's founding line (see
covenant_highway.py) is two classes: AUTO_REVERSIBLE may be run by the engine;
PROPOSE_ONLY -- config, install, money, rule, a narrowing of choice -- may never
be. Onboarding a node sat in PROPOSE_ONLY, so a device the operator already owns
could appear on the tailnet and the highway would only ever PROPOSE peering it,
never do it. This file adds a THIRD class between the two, and nothing else:

    AUTO_GATED -- the engine MAY act, but only through a gate rooted in the
                  operator, and only on a reversible, local action.

WHY A SEPARATE MODULE, NOT A NEW BRANCH IN apply_remedy. The highway's
apply_remedy dispatches on one axis -- is the class AUTO_REVERSIBLE? -- and its
invariants (NEVER_AUTOMATIC, the operator's choices, stateless-or-undo) are
written for repairs of a sensed fault. AUTO_GATED is a different shape: its
"condition" is a roster the operator signed, its gate verifies an identity over
the network, and its actions peer or arm rather than repair. Folding that into
apply_remedy would widen the one function every repair flows through, on the
same day a sibling session is editing the detectors beside it. So the lane lives
here, with its own gate and its own ledger rows (written to the SAME highway
ledger, klass AUTO_GATED, so one audit sees everything), and the highway's hook
is a single call. apply_remedy is not touched; the existing autonomous execution
is unchanged.

THE GATE. The engine auto-acts ONLY when ALL of these hold (any miss -> it does
not act; it PROPOSES or REFUSES, and says why):

  1. A model's output never triggers it. Data is not authority -- the same line
     as the Jang-woo reply, and it binds our own fleet, the uncensored 27B
     included. The trigger's source must be a roster scan or tailnet presence,
     never a model.
  2. ARMED. The operator wrote ops/AUTO_ONBOARD_ARMED choosing a trust root, AND
     that trust root is satisfiable now. Absent either, the lane is DARK: it
     senses and proposes, it acts on nothing. It ships DARK.
  3. A roster the operator ROOTED. Either (a) ops/NODE_ROSTER.json signed by the
     operator's OWN key and the signature verifies here, or (b) the roster is
     committed to the repo and every entry verifies as owned by the operator's
     own Tailscale account (whois). Strongest present wins; neither -> dark. The
     highway only READS and VERIFIES the roster. It never writes it.
  4. The target is ON that roster, and the action is one the roster allows for
     it. An unknown node is never auto-onboarded.
  5. Identity verified, not minted. `tailscale whois <ip>` must name the
     operator's account and the roster's Machine ID, and the node key pinned
     from `tailscale status --json` must equal the roster's. An IP alone is
     never trusted. Keys are only ever verified here, never created or copied.
  6. Reversible, LOCAL, exactly undoable. Auto-peer a known node (a line in
     ops/local_peers.txt; un-peer undoes it) and auto-arm a vetted task that
     keeps its OWN gate (disable undoes it). Anything that publishes, pushes,
     posts or sends is NOT reversible and stays PROPOSE_ONLY.
  7. Still PROPOSE_ONLY, forever: installing software; creating or granting keys
     or signing authority; the consent roster; onboarding an unknown node; any
     firewall / power / security / system-setting change on any node, even a
     reversible one; anything touching Tetsu's key, consent or path; any change
     to the roster itself, removals included.
  8. A per-node refusal is honoured. A node may declare "no system-setting
     auto-action" and the engine respects it whatever the class. TETSU declares
     it (ops/node_refusals.json) -- its Claude session's standing line on that
     machine.
  9. The operator's choices (ops/OPERATOR_CHOICES.json) and the pause switch are
     honoured, and the lane is DRY wherever highway_may_act() is False (a staged
     copy or a fresh clone -- A244). Every auto-action is logged AND announced
     with its undo command, rate-limited per node.

SOVEREIGNTY IS IMMOVABLE. Onboarding grants no signing or consent authority --
that is the owner's alone (Tetsu, 10-31: "a decision for the OWNER"). The host
must not be able to command the signer. Key_id ...dd885ef9... is Tetsu's own
CONSENT key, not a node key; nothing here gates on it, signs with it, or touches
it.

USE
  python covenant_onboard.py                 # what the lane sees, and whether it is armed
  python covenant_onboard.py --plan          # the candidates and what the gate says of each (DRY)
LICENCE: public domain.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import time

HERE = os.path.dirname(os.path.abspath(__file__))
_NOWIN = 0x08000000 if os.name == "nt" else 0

# The third class. A string, like the other two in covenant_highway.py, so a
# ledger row and a test can name it without importing the engine.
AUTO_GATED = "AUTO_GATED"

# Files the operator owns. The highway READS these; it writes none of them.
ROSTER = os.path.join(HERE, "ops", "NODE_ROSTER.json")       # operator-signed / operator-committed
OPERATOR_PUBKEY = os.path.join(HERE, "ops", "operator_pubkey.pem")  # for trust root (a)
ARMED_FILE = os.path.join(HERE, "ops", "AUTO_ONBOARD_ARMED")  # the operator's arm + trust-root choice
# This file the highway MAY write, because a refusal only ever TIGHTENS -- it can
# forbid an action, never permit one. Revoking is easier than granting (the spec's
# own rule), and a per-node "do not touch my system settings" is a revocation.
NODE_REFUSALS = os.path.join(HERE, "ops", "node_refusals.json")
# The highway's own ledger and choices, reused so one audit sees the whole road.
LEDGER = os.path.join(HERE, "ops", "highway.jsonl")
CHOICES = os.path.join(HERE, "ops", "OPERATOR_CHOICES.json")
# off-box peers, one comma-separated line of host:port -- the same file
# covenant_watchdog._local_peers() and covenant_prod.bat read.
LOCAL_PEERS = os.path.join(HERE, "ops", "local_peers.txt")
ARMED_TASKS = os.path.join(HERE, "ops", "armed_tasks.json")  # tasks this lane has armed; each undoable

NOTIFY_COOLDOWN_S = 3600     # one announcement per (node, action) an hour, so the lane cannot spam his phone
_PEER_RE = re.compile(r"[\w.\-]+:\d+")     # one host:port, the watchdog's own grammar

# Decisions a gate pass can return.
ACT = "ACT"           # armed, gated, reversible: the engine performs it
DRY = "DRY"           # it WOULD act, but a pause / may_act==False / dry_run holds it
PROPOSE = "PROPOSE"   # fails closed OR the action is PROPOSE_ONLY: a person decides
REFUSE = "REFUSE"     # a hard line: a model trigger, a bad signature, a failed identity, a refusal flag

# The only trigger sources that may ever reach ACT. A model is NOT here, and an
# unrecognised source is treated as a model would be: data, not authority.
TRIGGER_SOURCES = frozenset({"roster_scan", "tailnet_presence", "operator"})

# Action classes that are PROPOSE_ONLY forever, matched against what an action
# declares it IS. These never become AUTO_GATED however rooted the roster, so a
# careless roster entry naming one of them cannot make the engine run it.
PROPOSE_ONLY_CLASSES = frozenset({
    "install", "key", "sign", "consent", "roster-change", "onboard-unknown",
    "system-setting", "firewall", "power", "security",
})

# Reuse the highway's subject list so the two lanes refuse the same subjects.
try:  # pragma: no cover - a trivial import guard
    import covenant_highway as _H
    NEVER_AUTOMATIC = _H.NEVER_AUTOMATIC
except Exception:                                            # noqa: BLE001
    NEVER_AUTOMATIC = ("money", "holdings", "wallet", "trader", "venue", "order",
                       "rule", "principle", "judge", "seat", "model", "phone",
                       "consent", "key", "grid", "breaker", "relay", "feeder",
                       "substation", "setpoint", "load_shed", "actuat", "scada", "intertie")


# ---- the actions this lane can perform, each reversible and local ----------
#
# `reversible` False means outward (publish/push/post/send): the gate refuses it
# to PROPOSE before it is ever reached, so an outward action can never be
# AUTO_GATED even if a roster lists it. `cls` is matched against
# PROPOSE_ONLY_CLASSES. `touches` is matched against NEVER_AUTOMATIC, the same
# way apply_remedy matches a remedy's touches -- a label is one careless edit
# from wrong, so the subject is checked, not the class alone.

def _do_peer(target, dry_run):
    """Add the node's address to ops/local_peers.txt. LOCAL state, no outward
    effect; un-peer (remove the line) undoes it exactly."""
    addr = str((target or {}).get("peer_addr") or "")
    if not _PEER_RE.fullmatch(addr):
        return False, "no valid host:port peer address on the roster entry"
    cur = _read_peers()
    if addr in cur:
        return False, "already peered: %s" % addr
    if dry_run:
        return True, "would add peer %s to ops/local_peers.txt" % addr
    _write_peers(cur + [addr])
    return True, "peered %s" % addr


def _undo_peer(target):
    addr = str((target or {}).get("peer_addr") or "")
    return "remove %s from ops/local_peers.txt (un-peer)" % addr


def _do_arm_task(target, dry_run):
    """Arm a vetted task by recording it in ops/armed_tasks.json. Allowed ONLY
    if the task keeps its own gate (ff-only / opsec / dry); disabling it undoes
    it. This lane never removes the task's gate and never runs the task -- it
    flips a local 'may run' flag the task itself still gates behind."""
    task = (target or {}).get("task") or {}
    name = str(task.get("name") or "")
    gate = str(task.get("gate") or "")
    if not name:
        return False, "no task name"
    if gate not in ("ff-only", "opsec", "dry"):
        return False, "task does not keep its own gate (ff-only/opsec/dry): %r" % gate
    cur = _read_armed_tasks()
    if name in cur:
        return False, "already armed: %s" % name
    if dry_run:
        return True, "would arm task %s (keeps its %s gate)" % (name, gate)
    cur[name] = {"gate": gate, "armed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    _write_json(ARMED_TASKS, cur)
    return True, "armed %s (keeps its %s gate)" % (name, gate)


def _undo_arm_task(target):
    name = str(((target or {}).get("task") or {}).get("name") or "")
    return "disable %s (remove it from ops/armed_tasks.json)" % name


ACTIONS = {
    "peer": {"fn": _do_peer, "undo": _undo_peer, "reversible": True, "cls": "peer",
             "touches": ["a node address in ops/local_peers.txt"]},
    "arm_task": {"fn": _do_arm_task, "undo": _undo_arm_task, "reversible": True, "cls": "arm_task",
                 "touches": ["a vetted task's armed flag in ops/armed_tasks.json"]},
    # Declared so the gate and the tests can name them; all refuse before acting.
    "install": {"fn": None, "undo": None, "reversible": True, "cls": "install",
                "touches": ["software on a node"]},
    "set_firewall": {"fn": None, "undo": None, "reversible": True, "cls": "firewall",
                     "touches": ["a node's firewall (a system setting)"]},
    "push": {"fn": None, "undo": None, "reversible": False, "cls": "publish",
             "touches": ["an outward publish"]},
}

# Which per-node refusal a given action class trips. A node that refuses
# "system-setting" refuses firewall/power/security actions whatever their class.
_REFUSAL_OF_CLASS = {"firewall": "system-setting", "power": "system-setting",
                     "security": "system-setting", "system-setting": "system-setting"}


# ----------------------------------------------------------------- readers

def _read_json(path, default):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def _write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2, sort_keys=True)
    os.replace(tmp, path)


def _read_peers(path=None):
    """The current off-box peers as a list of host:port, read from the one line
    covenant_watchdog also reads. A malformed line reads as empty (no guessed peer)."""
    path = path or LOCAL_PEERS
    try:
        with open(path, encoding="utf-8") as fh:
            s = fh.readline().strip().strip(",")
    except OSError:
        return []
    if not s:
        return []
    parts = [p for p in s.split(",") if p]
    return parts if all(_PEER_RE.fullmatch(p) for p in parts) else []


def _write_peers(peers, path=None):
    path = path or LOCAL_PEERS
    line = ",".join(peers)
    if line and not re.fullmatch(r"[\w.\-]+:\d+(,[\w.\-]+:\d+)*", line):
        raise ValueError("refusing to write a malformed peers line: %r" % line)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(line + "\n")
    os.replace(tmp, path)


def _read_armed_tasks(path=None):
    d = _read_json(path or ARMED_TASKS, {})
    return d if isinstance(d, dict) else {}


def _operator_choices(path=None):
    d = _read_json(path or CHOICES, {})
    return d if isinstance(d, dict) else {}


def _node_refusals(path=None):
    """{node_id: [refused classes]} -- refusals only tighten, so this file is
    safe for the highway to carry. Absent -> no refusals."""
    d = _read_json(path or NODE_REFUSALS, {})
    out = {}
    if isinstance(d, dict):
        for k, v in d.items():
            if isinstance(v, list):
                out[str(k)] = [str(x) for x in v]
            elif isinstance(v, dict) and isinstance(v.get("refuses"), list):
                out[str(k)] = [str(x) for x in v["refuses"]]
    return out


# ----------------------------------------------------------------- roster + trust root

def _canonical_payload(roster):
    """The bytes a signature covers: the roster without its own signature meta.
    sort_keys so the operator's signer and this verifier agree byte for byte."""
    body = {k: v for k, v in (roster or {}).items()
            if k not in ("signature", "signed_by", "alg")}
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _verify_signature(roster, pubkey_pem):
    """True only if the roster carries a signature that `pubkey_pem` verifies over
    its canonical payload. Any missing piece, any error, any mismatch -> False.
    Supports whatever key type the operator chose (Ed25519 or RSA PEM); a key this
    cannot load is a key it cannot verify, which is False, not a pass."""
    sig_hex = (roster or {}).get("signature")
    if not sig_hex or not pubkey_pem:
        return False
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import ed25519, padding
        key = serialization.load_pem_public_key(pubkey_pem.encode()
                                                 if isinstance(pubkey_pem, str) else pubkey_pem)
        sig = bytes.fromhex(sig_hex)
        payload = _canonical_payload(roster)
        if isinstance(key, ed25519.Ed25519PublicKey):
            key.verify(sig, payload)
        else:  # RSA (or any key whose verify takes a padding+hash); PSS is what a signer should use
            key.verify(sig, payload, padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                                                 salt_length=padding.PSS.MAX_LENGTH), hashes.SHA256())
        return True
    except Exception:                                           # noqa: BLE001 -- unverifiable == not verified
        return False


def load_roster(path=None):
    """The roster dict, or {} when absent/unreadable. {} is the fail-closed shape:
    no roster means no node is known, so nothing is ever auto-onboarded."""
    d = _read_json(path or ROSTER, {})
    return d if isinstance(d, dict) else {}


def _operator_pubkey(path=None):
    try:
        with open(path or OPERATOR_PUBKEY, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return None


def roster_trust_root(roster=None, pubkey=None, committed=None):
    """(root_name, reason). root_name is 'signature' | 'whois' | None.

    Strongest present wins. 'signature' needs the operator's public key and a
    signature over the roster that verifies. 'whois' needs the roster committed
    to the repo (so its authenticity rides the repo) AND is then only as strong
    as the per-entry whois done at identity time. None -> the lane is dark.
    """
    roster = load_roster() if roster is None else roster
    if not roster:
        return None, "no roster on disk -- auto-onboard is dark"
    pk = _operator_pubkey() if pubkey is None else pubkey
    if pk and _verify_signature(roster, pk):
        return "signature", "roster signed by the operator's key and the signature verifies"
    if pk and roster.get("signature"):
        return None, "a signature is present but does NOT verify against the operator's key -- fail closed"
    committed = _roster_is_committed() if committed is None else committed
    if committed:
        return "whois", "no valid signature; roster is repo-committed, anchored per-entry by whois ownership"
    return None, ("roster is present but neither signed-and-verified nor repo-committed -- "
                  "no trust root, fail closed")


def _roster_is_committed(path=None):
    """True only if NODE_ROSTER.json is tracked by git (the whois anchor requires
    the roster's authenticity to ride the repo, not a file anyone could drop in)."""
    path = path or ROSTER
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    try:
        r = subprocess.run(["git", "-C", HERE, "ls-files", "--error-unmatch", os.path.relpath(path, HERE)],
                           capture_output=True, text=True, timeout=20, env=env, creationflags=_NOWIN)
        return r.returncode == 0
    except Exception:                                           # noqa: BLE001
        return False


# ----------------------------------------------------------------- identity (tailscale)

def _tailscale_whois(ip, whois_fn=None):
    """{'machine_id':.., 'user':..} for an IP, or None. Never trusts an IP alone:
    the CALLER checks machine id and owning user against the roster. Any failure
    -> None -> fail closed."""
    if whois_fn is not None:
        return whois_fn(ip)
    try:
        r = subprocess.run(["tailscale", "whois", "--json", str(ip)],
                           capture_output=True, text=True, timeout=20, creationflags=_NOWIN)
        if r.returncode != 0:
            return None
        d = json.loads(r.stdout or "null")
        node = (d or {}).get("Node") or {}
        user = (d or {}).get("UserProfile") or {}
        return {"machine_id": node.get("StableID") or node.get("ID"),
                "user": user.get("LoginName") or user.get("ID"),
                "key": node.get("Key")}
    except Exception:                                           # noqa: BLE001
        return None


def _tailscale_nodekey(ip, status_fn=None):
    """The node's public key pinned from `tailscale status --json`, or None."""
    if status_fn is not None:
        return status_fn(ip)
    try:
        r = subprocess.run(["tailscale", "status", "--json"],
                           capture_output=True, text=True, timeout=20, creationflags=_NOWIN)
        if r.returncode != 0:
            return None
        d = json.loads(r.stdout or "null") or {}
        for peer in list((d.get("Peer") or {}).values()) + [d.get("Self") or {}]:
            for a in (peer.get("TailscaleIPs") or []):
                if str(a) == str(ip):
                    return peer.get("PublicKey") or peer.get("Key")
        return None
    except Exception:                                           # noqa: BLE001
        return None


def verify_identity(node_id, entry, operator_account, whois_fn=None, status_fn=None):
    """(ok, reason). ok only when whois names the operator's account AND the
    roster's Machine ID, and the node key pinned from status equals the roster's.
    An IP alone is never enough; any missing or mismatched piece is False."""
    ip = entry.get("ip")
    if not ip:
        return False, "roster entry for %s has no ip" % node_id
    who = _tailscale_whois(ip, whois_fn=whois_fn)
    if not who:
        return False, "whois failed for %s (%s) -- fail closed" % (node_id, ip)
    if operator_account and str(who.get("user")) != str(operator_account):
        return False, "whois owner %r != operator %r" % (who.get("user"), operator_account)
    if entry.get("machine_id") and str(who.get("machine_id")) != str(entry["machine_id"]):
        return False, "whois machine id %r != rostered %r" % (who.get("machine_id"), entry["machine_id"])
    pinned = _tailscale_nodekey(ip, status_fn=status_fn)
    if entry.get("pubkey"):
        if not pinned:
            return False, "could not pin a node key for %s -- fail closed" % node_id
        if str(pinned) != str(entry["pubkey"]):
            return False, "pinned node key != rostered node key for %s" % node_id
    return True, "identity verified by whois (owner, machine id) and pinned node key"


# ----------------------------------------------------------------- the gate

def _grid_route(action):
    """A reason string if `action` is a grid/ICS effect that must go to the grid
    guard's together-vote, else None. The class is DERIVED from covenant_grid_guard's
    ACTION_CLASS allowlist -- the one source of truth, reused not forked. If the guard
    cannot be imported, this returns None: the known-action check still refuses
    anything that is not one of this lane's own (non-grid) reversible actions, so a
    missing guard opens no hole."""
    try:
        import covenant_grid_guard as G
        cls = G.required_class(action)
    except Exception:                                           # noqa: BLE001
        return None
    if cls is not None:
        holders = "+".join(getattr(G, "AUTHORITY_ROLES", ("operator", "tetsu")))
        return ("grid/ICS action %r (class %s) -> covenant_grid_guard together-vote (%s), "
                "fail-closed, never AUTO_GATED (data/anomaly is ALARM-only, never authority)"
                % (action, cls, holders))
    return None


def is_armed(roster=None, armed_cfg=None, pubkey=None, committed=None):
    """(armed, trust_root, reason). The lane is armed ONLY when the operator wrote
    ops/AUTO_ONBOARD_ARMED choosing a trust root AND that trust root is satisfiable
    now. Ships DARK: the file does not exist, so this returns (False, None, ...)."""
    cfg = _read_json(ARMED_FILE, None) if armed_cfg is None else armed_cfg
    if not isinstance(cfg, dict) or not cfg.get("armed"):
        return False, None, "ops/AUTO_ONBOARD_ARMED absent or armed!=true -- the lane is dark"
    want = str(cfg.get("trust_root") or "auto")
    root, why = roster_trust_root(roster=roster, pubkey=pubkey, committed=committed)
    if root is None:
        return False, None, "armed, but %s" % why
    if want not in ("auto", root):
        return False, None, "operator asked trust root %r but the strongest present is %r" % (want, root)
    return True, root, "armed; trust root %s (%s)" % (root, why)


def evaluate(action, target, trigger, *, roster=None, choices=None, refusals=None,
             operator_account=None, armed_cfg=None, pubkey=None, committed=None,
             whois_fn=None, status_fn=None, paused=None, may_act=True, now=None):
    """The whole gate for one (action, target, trigger), in order, fail-closed.

    Returns {decision, reason, undo, action, node, klass}. decision is ACT only
    when every gate passes AND the lane is armed AND nothing holds it dry; DRY
    when it would act but a pause / may_act False / a declared dry holds it;
    PROPOSE when it fails closed or the action is PROPOSE_ONLY; REFUSE on a hard
    line (a model trigger, a bad signature, a failed identity, a refusal flag).
    """
    node_id = str((target or {}).get("node") or (target or {}).get("id") or "?")
    spec = ACTIONS.get(action)
    base = {"action": action, "node": node_id, "klass": AUTO_GATED, "undo": "n/a"}

    def out(decision, reason):
        return dict(base, decision=decision, reason=reason)

    # 1. A MODEL'S OUTPUT NEVER TRIGGERS AUTO_GATED. Data is not authority.
    src = (trigger or {}).get("source") if isinstance(trigger, dict) else None
    if src not in TRIGGER_SOURCES:
        return out(REFUSE, "trigger source %r is not operator-rooted -- a model's output can never "
                           "trigger AUTO_GATED (data is not authority)" % src)

    # 2. GRID / ICS DEFERS TO covenant_grid_guard -- BEFORE the known-action check, so a
    #    grid action named on a roster is routed to the guard rather than called "unknown".
    #    The class is DERIVED from the grid guard's own ACTION_CLASS allowlist (the single
    #    source of truth -- no forked grid word list, per the PG1/rule-6 lesson): any action
    #    it recognises is grid-domain and goes to the together-vote (operator + Tetsu),
    #    fail-closed, never AUTO_GATED. An action the allowlist does not know is not treated
    #    as grid here; it falls to the known-action check below, which refuses the unknown.
    gr = _grid_route(action)
    if gr:
        return dict(base, decision=REFUSE, reason=gr, route="grid_guard")

    # 3. a known action
    if spec is None:
        return out(REFUSE, "unknown action %r" % action)

    # 4. a per-node refusal, honoured whatever the class and BEFORE the
    #    PROPOSE_ONLY short-circuit below, so it is a guard in its own right: a
    #    node that refuses 'system-setting' REFUSES (a hard no), where an
    #    unflagged node's system-setting action merely PROPOSES. TETSU sets this.
    refusals = _node_refusals() if refusals is None else refusals
    refused = set(refusals.get(node_id, []))
    cls_refusal = _REFUSAL_OF_CLASS.get(spec.get("cls"))
    if spec.get("cls") in refused or (cls_refusal and cls_refusal in refused):
        return out(REFUSE, "%s refuses %s auto-actions (per-node refusal)" % (node_id, cls_refusal or spec["cls"]))

    # 5. PROPOSE_ONLY forever -- by the action's declared class, and by its subject
    if spec.get("cls") in PROPOSE_ONLY_CLASSES:
        return out(PROPOSE, "action class %r is PROPOSE_ONLY forever -- a person decides" % spec["cls"])
    crossed = sorted({w for w in NEVER_AUTOMATIC for t in spec.get("touches", []) if w in t.lower()})
    if crossed:
        return out(PROPOSE, "touches %s -- refused whatever class it claims" % ", ".join(crossed))

    # 6. outward actions are not reversible, so never AUTO_GATED
    if not spec.get("reversible"):
        return out(PROPOSE, "action %r is not reversible (outward: cannot be unsent) -- PROPOSE_ONLY" % action)

    # 7. ARMED and a trust root present, else DARK (fail closed -> propose)
    armed, root, why = is_armed(roster=roster, armed_cfg=armed_cfg, pubkey=pubkey, committed=committed)
    if not armed:
        return out(PROPOSE, "auto-onboard dark: %s" % why)
    base["root"] = root

    # 8. the target is on the roster (an unknown node is never auto-onboarded)
    r = load_roster() if roster is None else roster
    nodes = (r.get("nodes") or {}) if isinstance(r, dict) else {}
    entry = nodes.get(node_id)
    if not isinstance(entry, dict):
        return out(PROPOSE, "node %r is not on the roster -- onboarding an unknown node is PROPOSE_ONLY" % node_id)

    # 9. the roster allows THIS action for THIS node
    allowed = entry.get("allowed") or entry.get("actions") or []
    if action not in allowed:
        return out(REFUSE, "the roster does not allow %r for %s (allowed: %s)" % (action, node_id, allowed))

    # 10. identity verified, not minted
    acct = operator_account if operator_account is not None else r.get("operator_account")
    ok, idreason = verify_identity(node_id, entry, acct, whois_fn=whois_fn, status_fn=status_fn)
    if not ok:
        return out(REFUSE, "identity not verified: %s" % idreason)

    # 11. the operator's explicit choices are untouchable
    choices = _operator_choices() if choices is None else choices
    clash = sorted(set(spec.get("touches", [])) & set(choices or {}))
    if node_id in (choices or {}):
        clash = sorted(set(clash) | {node_id})
    if clash:
        return out(REFUSE, "the operator chose %s: %s" % (clash[0], (choices or {}).get(clash[0], "")))

    # the undo is on record from here
    undo_fn = spec.get("undo")
    base["undo"] = undo_fn(target) if callable(undo_fn) else "n/a"

    # 12. pause / may_act==False -> it would act, but DRY (A244)
    if paused is None:
        paused = _paused()
    if paused or not may_act:
        return out(DRY, "gated and armed, but held DRY (%s)" % ("paused" if paused else "highway_may_act() is False"))

    return out(ACT, "armed, rostered, identity-verified, reversible -- the engine may act (%s)" % idreason)


def _paused():
    try:
        import covenant_pause as _p
        is_paused, _why = _p.paused("highway")
        return bool(is_paused)
    except Exception:                                           # noqa: BLE001
        return False


# ----------------------------------------------------------------- announce + ledger

def _recent_notify(node_id, action, ledger=None, now=None):
    now = time.time() if now is None else now
    for row in reversed(_read_ledger(ledger)):
        if row.get("klass") == AUTO_GATED and row.get("node") == node_id and row.get("action") == action \
                and row.get("announced"):
            return (now - float(row.get("at", 0))) < NOTIFY_COOLDOWN_S
    return False


def announce(decision_row, ledger=None, notify_fn=None, now=None):
    """Announce an auto-action with its undo command, rate-limited per (node, action).
    A notifier that can bring down what it reports on has inverted its purpose, so
    this never raises and returns whether it sent."""
    node_id, action = decision_row.get("node"), decision_row.get("action")
    if _recent_notify(node_id, action, ledger=ledger, now=now):
        return False
    title = "highway auto-onboard: %s %s" % (action, node_id)
    body = "%s\nundo: %s" % (decision_row.get("reason", ""), decision_row.get("undo", "n/a"))
    try:
        if notify_fn is not None:
            notify_fn(title, body)
        else:
            import covenant_notify
            covenant_notify.notify(title, body, priority="default")
        return True
    except Exception:                                           # noqa: BLE001
        return False


def _read_ledger(path=None):
    out = []
    try:
        with open(path or LEDGER, encoding="utf-8") as fh:
            for line in fh:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        pass
    return out


def _write_ledger(row, path=None):
    path = path or LEDGER
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def act(action, target, trigger, *, dry_run=True, ledger=None, notify_fn=None, now=None, **gate):
    """Evaluate the gate and, only on ACT and not dry_run, perform the reversible
    action -- then log the row (klass AUTO_GATED, to the highway ledger) and
    announce it with its undo. DRY/PROPOSE/REFUSE are logged too: a refusal nobody
    can see is indistinguishable from a bug that swallowed the work."""
    d = evaluate(action, target, trigger, **gate)
    row = {"t": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "at": round(now if now is not None else time.time(), 1),
           "klass": AUTO_GATED, "action": action, "node": d.get("node"), "detector": "auto_onboard",
           "decision": d["decision"], "why": d["reason"], "undo": d.get("undo", "n/a"),
           "trigger_source": (trigger or {}).get("source") if isinstance(trigger, dict) else None,
           "dry_run": bool(dry_run)}
    if d["decision"] != ACT or dry_run:
        row["outcome"] = {ACT: "dry run", DRY: "held (dry)", PROPOSE: "proposed", REFUSE: "refused"}[d["decision"]]
        row["ran"] = False
        return _write_ledger(row, ledger)
    spec = ACTIONS.get(action) or {}
    fn = spec.get("fn")
    if not callable(fn):
        row.update(outcome="refused", ran=False, why="no executable function for %r" % action)
        return _write_ledger(row, ledger)
    ok, detail = fn(target, dry_run=False)
    row.update(ran=bool(ok), detail=str(detail)[:300],
               outcome="done" if ok else "held", undo=(spec["undo"](target) if ok and callable(spec.get("undo")) else row["undo"]))
    _write_ledger(row, ledger)
    if ok:
        row_sent = dict(d, undo=row["undo"])
        if announce(row_sent, ledger=ledger, notify_fn=notify_fn, now=now):
            _write_ledger(dict(row, announced=True, outcome="announced",
                               at=round(now if now is not None else time.time(), 1)), ledger)
    return row


# ----------------------------------------------------------------- the pass

def _candidates(roster):
    """[(action, target, trigger)] the roster offers: a rostered node not yet
    peered -> peer it; a vetted task not yet armed -> arm it. The trigger source
    is 'roster_scan' -- never a model. An empty/absent roster yields nothing."""
    out = []
    nodes = (roster.get("nodes") or {}) if isinstance(roster, dict) else {}
    peers = set(_read_peers())
    for node_id, entry in sorted(nodes.items()):
        if not isinstance(entry, dict):
            continue
        allowed = entry.get("allowed") or entry.get("actions") or []
        if "peer" in allowed and str(entry.get("peer_addr") or "") not in peers:
            out.append(("peer", {"node": node_id, "peer_addr": entry.get("peer_addr")},
                        {"source": "roster_scan"}))
        for task in (entry.get("tasks") or []):
            if "arm_task" in allowed and task.get("name") not in _read_armed_tasks():
                out.append(("arm_task", {"node": node_id, "task": task}, {"source": "roster_scan"}))
    return out


def run_once(dry_run=True, ledger=None, now=None, **gate):
    """One auto-onboard pass, in the highway's (alerts, infos) shape so its hook
    can merge the lines. Honours pause and may_act (both default from the gate).
    DARK and empty by default: no roster, not armed -> one info line, no action."""
    alerts, infos = [], []
    roster = gate.get("roster")
    roster = load_roster() if roster is None else roster
    armed, root, why = is_armed(roster=roster, pubkey=gate.get("pubkey"),
                                armed_cfg=gate.get("armed_cfg"), committed=gate.get("committed"))
    if not armed:
        infos.append("highway auto-onboard: DARK -- %s" % why)
        return alerts, infos
    infos.append("highway auto-onboard: armed (trust root %s)" % root)
    for action, target, trigger in _candidates(roster):
        row = act(action, target, trigger, dry_run=dry_run, ledger=ledger, now=now, roster=roster, **{
            k: v for k, v in gate.items() if k in
            ("choices", "refusals", "operator_account", "armed_cfg", "pubkey", "committed",
             "whois_fn", "status_fn", "paused", "may_act")})
        line = "highway auto-onboard: %s %s -> %s (%s)" % (action, target.get("node"), row.get("outcome"), row.get("why", "")[:120])
        (infos if row.get("outcome") in ("done", "announced", "dry run") else alerts).append(line)
    return alerts, infos


# ----------------------------------------------------------------- CLI

def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="the highway's AUTO_GATED auto-onboard lane")
    ap.add_argument("--plan", action="store_true", help="show the candidates and the gate's verdict (DRY)")
    args = ap.parse_args(argv)
    roster = load_roster()
    armed, root, why = is_armed(roster=roster)
    print("auto-onboard: %s" % ("ARMED (trust root %s)" % root if armed else "DARK -- %s" % why))
    if args.plan:
        alerts, infos = run_once(dry_run=True)
        for ln in infos + alerts:
            print("  " + ln)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
