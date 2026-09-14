#!/usr/bin/env python3
"""covenant_sealed_mail.py -- the day's plan and the operator's decision, sealed
for the mail (the operator's ask, 2026-09-13: "encode the email in a way only
you and the node understand for security but explain to me when asked").

WHAT A SEALED BLOCK IS. One text block that can travel in an email, a chat,
a share sheet, and be read only by the key it is addressed to:

    -----BEGIN COVENANT SEALED-----
    <base64 of a JSON envelope, wrapped at 76 columns>
    -----END COVENANT SEALED-----

The envelope: {"v": 1, "kind": "plan"|"decision", "to": <recipient key
fingerprint>, "from": <sender key fingerprint>, "ek": <the content key,
wrapped with RSA-OAEP-SHA256 under the RECIPIENT's public key>, "iv": <12
random bytes>, "ct": <the plaintext under AES-256-GCM with that content key;
the header {v,kind,to,from} is the authenticated additional data>, "sig":
<RSA-PSS-SHA256 by the SENDER over the canonical JSON of v,kind,to,from,ek,
iv,ct>, "spk": <the sender's public key PEM, transport only -- the reader
checks it against what it already trusts>}.

The keys are the ones the nodes already own: the PC node's identity key
(nodeA_prod.db.key) and the phone node's identity key, which the operator
registered as the daily-plan signer "phone". Nothing new is minted; a
fingerprint is sha256 of the whitespace-stripped PEM, first 16 hex, the same
number the approvals ledger writes as pubkey_sha256.

WHO CAN READ WHAT. A plan sealed to the phone opens ONLY on the phone (the PC
that sealed it cannot open it again; it kept the plaintext in its own log).
A decision sealed to the PC opens ONLY on the PC. Google, Yahoo and anyone
between them see the block and nothing inside it. A decision is accepted only
if the signature is a registered signer's, the date is TODAY on the PC, the
plan's sha is the plan on disk, and the nonce has never been opened here --
so a captured block cannot be replayed tomorrow, and a mail "from" the
operator's address that was not signed by the phone's key is refused.

NOTHING HIDDEN FROM THE OPERATOR. Every block sealed or opened on this PC is
written in plain text to ops/sealed_mail.log (gitignored): time, who to whom,
and the whole plaintext. `--explain` prints this description; `--peek FILE`
says who a block is from and for without any key; `--log` shows the ledger.
The method is public (this file, docs/SEALED_MAIL.md); only the keys are
private. That is what "only you and the node understand" can honestly mean:
a secret method would be a weaker promise than a public method with private
keys, and it would be a thing the operator could not check.

Run:
  python covenant_sealed_mail.py --seal-plan [--to phone]   today's plan, sealed to that signer; printed and saved
  python covenant_sealed_mail.py --open FILE|-              open a decision addressed to this PC and record it
  python covenant_sealed_mail.py --peek FILE|-              who -> whom, kind, size; no key needed
  python covenant_sealed_mail.py --fingerprint              this PC's key fingerprint (compare on the phone)
  python covenant_sealed_mail.py --explain                  the format, in plain words
  python covenant_sealed_mail.py --log [N]                  the last N ledger lines (default 20)
"""
import base64
import hashlib
import importlib
import json
import os
import re
import secrets
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
OUTBOX = os.path.join(HERE, "ops", "sealed_mail")
LOG = os.path.join(HERE, "ops", "sealed_mail.log")
SEEN = os.path.join(HERE, "ops", "sealed_mail_seen.json")
BEGIN = "-----BEGIN COVENANT SEALED-----"
END = "-----END COVENANT SEALED-----"
VERSION = 1
KINDS = ("plan", "decision", "identity")
ENVELOPE_KEYS = ("v", "kind", "to", "from", "ek", "iv", "ct")
MAX_BLOCK_BYTES = 1 << 20          # a block larger than this is not one of ours
# the marker lines as a mail client may show them: a no-break space, a double
# space or a line break between the words still marks a block
MARKERS = re.compile(r"-----BEGIN\s+COVENANT\s+SEALED-----(.*?)-----END\s+COVENANT\s+SEALED-----", re.S)
MARKER_BEGIN = re.compile(r"-----BEGIN\s+COVENANT\s+SEALED-----")


class SealedError(Exception):
    """A block that must not be trusted, and the plain reason why."""


# ---------------------------------------------------------------- the primitives (mirrored in the app's entry.py)

def canonical(d):
    return json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _norm(pem):
    return "".join(str(pem).split())


def fingerprint(pem):
    return hashlib.sha256(_norm(pem).encode("utf-8")).hexdigest()[:16]


def pubkey_pem(key):
    from cryptography.hazmat.primitives import serialization
    return key.public_key().public_bytes(serialization.Encoding.PEM,
                                         serialization.PublicFormat.SubjectPublicKeyInfo).decode()


def _load_pub(pem):
    from cryptography.hazmat.primitives import serialization
    try:
        return serialization.load_pem_public_key(str(pem).encode("utf-8"))
    except Exception as e:                                        # noqa: BLE001
        raise SealedError("not a public key PEM: %s" % type(e).__name__)


def _b64(b):
    return base64.b64encode(b).decode("ascii")


def _unb64(s):
    try:
        return base64.b64decode(str(s), validate=True)
    except Exception:                                             # noqa: BLE001
        raise SealedError("a field is not base64")


def armor(env):
    b = base64.b64encode(canonical(env).encode("utf-8")).decode("ascii")
    return "\n".join([BEGIN] + [b[i:i + 76] for i in range(0, len(b), 76)] + [END])


def blocks(text):
    """Every envelope in a text, in order -- tolerant of a mail client's quoting
    ('> ' prefixes), re-wrapping and surrounding prose. Malformed blocks are
    skipped, not fatal: the reader decides what it was looking for."""
    if not text:
        return []
    cleaned = "\n".join(re.sub(r"^[>\s]+", "", ln) for ln in str(text).splitlines())
    out = []
    for m in MARKERS.finditer(cleaned):
        # only the base64 alphabet survives: a mail client's re-wrapping, quoting,
        # no-break spaces, soft hyphens or zero-width marks inside the block are
        # dropped, and a quoted-printable '=3D' is an '=' again (safe: '=' occurs
        # only as trailing padding in valid base64)
        raw = re.sub(r"[^A-Za-z0-9+/=]", "", m.group(1).replace("=3D", "="))
        if not raw or len(raw) > MAX_BLOCK_BYTES:
            continue
        try:
            env = json.loads(base64.b64decode(raw, validate=True).decode("utf-8"))
        except Exception:                                         # noqa: BLE001
            continue
        if isinstance(env, dict):
            out.append(env)
    return out


def _check_shape(env):
    for k in ENVELOPE_KEYS + ("sig", "spk"):
        if k not in env:
            raise SealedError("envelope lacks %r" % k)
    if env["v"] != VERSION:
        raise SealedError("version %r is not %d" % (env["v"], VERSION))
    if env["kind"] not in KINDS:
        raise SealedError("kind %r is not one of %s" % (env["kind"], "/".join(KINDS)))
    if fingerprint(env["spk"]) != env["from"]:
        raise SealedError("the sender key carried does not match the 'from' fingerprint")


def seal(kind, obj, sender_key, sender_pem, recipient_pem):
    """A block only recipient_pem's private key can open, signed by sender_key."""
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    if kind not in KINDS:
        raise SealedError("kind %r is not one of %s" % (kind, "/".join(KINDS)))
    if not isinstance(obj, dict) or obj.get("kind") != kind:
        raise SealedError("the plaintext must be an object whose 'kind' is %r" % kind)
    ck, iv = secrets.token_bytes(32), secrets.token_bytes(12)
    header = {"v": VERSION, "kind": kind, "to": fingerprint(recipient_pem), "from": fingerprint(sender_pem)}
    ct = AESGCM(ck).encrypt(iv, canonical(obj).encode("utf-8"), canonical(header).encode("utf-8"))
    ek = _load_pub(recipient_pem).encrypt(ck, padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
    env = dict(header, ek=_b64(ek), iv=_b64(iv), ct=_b64(ct))
    sig = sender_key.sign(canonical(env).encode("utf-8"),
                          padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH), hashes.SHA256())
    env["sig"], env["spk"] = _b64(sig), sender_pem
    return armor(env)


def open_env(env, my_key, my_pem, expect_sender_pem=None):
    """(envelope, plaintext object, sender PEM) or SealedError. The signature is
    checked BEFORE anything is decrypted; a block for another key, a replaced
    sender key, a changed header or a changed byte all fail with their reason."""
    from cryptography.exceptions import InvalidSignature, InvalidTag
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding, rsa
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    _check_shape(env)
    mine = fingerprint(my_pem)
    if env["to"] != mine:
        raise SealedError("not addressed to this key (to %s, this key is %s)" % (env["to"], mine))
    spk = env["spk"]
    if expect_sender_pem is not None and _norm(expect_sender_pem) != _norm(spk):
        raise SealedError("the sender key is not the key already trusted here (got %s, trusted %s)" % (env["from"], fingerprint(expect_sender_pem)))
    signed = canonical({k: env[k] for k in ENVELOPE_KEYS}).encode("utf-8")
    # Every failure below is a refusal with a reason, never a traceback: a block
    # is untrusted input, and a stranger holds the PC's public key (it rides in
    # every plan block), so a crafted block must not crash the reader or skip
    # the ledger. Anything but an RSA key, a wrong-length key or nonce, a
    # plaintext that is not JSON (or nests until the parser gives up) -- refused.
    try:
        pub = _load_pub(spk)
        if not isinstance(pub, rsa.RSAPublicKey):
            raise SealedError("the sender key is not an RSA key")
        pub.verify(_unb64(env["sig"]), signed,
                   padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH), hashes.SHA256())
    except InvalidSignature:
        raise SealedError("the signature does not verify")
    except SealedError:
        raise
    except Exception as e:                                        # noqa: BLE001
        raise SealedError("the signature cannot be checked: %s" % type(e).__name__)
    try:
        ck = my_key.decrypt(_unb64(env["ek"]), padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
    except SealedError:
        raise
    except Exception:                                             # noqa: BLE001
        raise SealedError("the content key does not unwrap with this key")
    header = {k: env[k] for k in ("v", "kind", "to", "from")}
    try:
        pt = AESGCM(ck).decrypt(_unb64(env["iv"]), _unb64(env["ct"]), canonical(header).encode("utf-8"))
    except InvalidTag:
        raise SealedError("the ciphertext or its header was changed")
    except SealedError:
        raise
    except Exception as e:                                        # noqa: BLE001
        raise SealedError("the ciphertext cannot be opened: %s" % type(e).__name__)
    try:
        obj = json.loads(pt.decode("utf-8"))
    except Exception:                                             # noqa: BLE001  (RecursionError included)
        raise SealedError("the plaintext is not JSON")
    if not isinstance(obj, dict) or obj.get("kind") != env["kind"]:
        raise SealedError("the inner kind differs from the header")
    return env, obj, spk


def open_block(text, my_key, my_pem, expect_sender_pem=None, kind=None):
    """Of the blocks in TEXT of the wanted kind that open with my_key, the NEWEST
    (a plan by its 'issued', a decision by its 'ts'): a reply quotes the earlier
    mail, so an older block usually sits above the one that matters."""
    found = [e for e in blocks(text) if kind is None or e.get("kind") == kind]
    if not found:
        if MARKER_BEGIN.search(str(text or "")):
            raise SealedError("a sealed block is present but was damaged in transit; copy it again from the mail")
        raise SealedError("no %ssealed block in the text" % ((kind + " ") if kind else ""))
    opened, last = [], None
    for env in found:
        try:
            opened.append(open_env(env, my_key, my_pem, expect_sender_pem))
        except SealedError as e:
            last = e
    if not opened:
        raise last
    return max(opened, key=lambda t: (str(t[1].get("issued", "")), _num(t[1].get("ts"))))


def peek(text):
    """Who -> whom, kind and size of every block, with no key at all."""
    out = []
    for env in blocks(text):
        try:
            _check_shape(env)
            ok = "well-formed"
        except SealedError as e:
            ok = "MALFORMED: %s" % e
        out.append({"kind": env.get("kind"), "to": env.get("to"), "from": env.get("from"),
                    "bytes": len(str(env.get("ct", ""))) * 3 // 4, "shape": ok})
    return out


# ---------------------------------------------------------------- this PC's side

def _dp():
    return importlib.import_module("covenant_daily_plan")


def _log(line, plaintext=None, path=None):
    path = path or LOG
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write("%s %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%S%z"), line))
        if plaintext is not None:
            fh.write("    plaintext: %s\n" % canonical(plaintext))


def _seen(path=None):
    """{nonce: [date, ts]} of every decision opened here (an older file that
    was a bare list reads as {nonce: [None, 0.0]}: replay protection unchanged)."""
    try:
        with open(path or SEEN, encoding="utf-8") as fh:
            d = json.load(fh)
    except (OSError, ValueError):
        return {}
    if isinstance(d, list):
        return {str(n): [None, 0.0] for n in d}
    if isinstance(d, dict):
        return {str(n): (v if isinstance(v, list) and len(v) == 2 else [None, 0.0]) for n, v in d.items()}
    return {}


def _remember(nonce, date, ts, path=None):
    path = path or SEEN
    s = _seen(path)
    s[nonce] = [date, ts]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(s, fh, sort_keys=True)
    os.replace(tmp, path)


def my_key(key_path=None):
    dp = _dp()
    key = dp.load_key(key_path)
    return key, pubkey_pem(key)


def seal_plan(to="phone", day=None, key_path=None, plan_dir=None, signers_path=None, outbox=None, log_path=None, now=None):
    """Today's plan, sealed to the registered signer TO and signed by this PC.
    Returns (block, saved path). The plaintext goes to the ledger."""
    dp = _dp()
    day = day or dp.today(now)
    plan = dp.load(day, plan_dir)
    if not plan:
        raise SealedError("no plan written for %s (python covenant_daily_plan.py --write)" % day)
    rec = dp.signers(signers_path).get(to)
    if not rec:
        raise SealedError("no registered daily-plan signer named %r" % to)
    key, pem = my_key(key_path)
    obj = {"kind": "plan", "issued": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(now)), "plan": plan}
    block = seal("plan", obj, key, pem, rec)
    outbox = outbox or OUTBOX
    os.makedirs(outbox, exist_ok=True)
    path = os.path.join(outbox, "%s-plan-to-%s.txt" % (day, re.sub(r"[^A-Za-z0-9_-]", "_", to)))
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(block + "\n")
    _log("SEALED plan for %s (sha %s) to %s [%s] from pc [%s] -> %s" % (day, plan["sha256"][:12], to, fingerprint(rec), fingerprint(pem), path), obj, log_path)
    return block, path


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def open_decision(text, key_path=None, plan_dir=None, approvals=None, signers_path=None, seen_path=None, now=None, log_path=None):
    """Every decision block addressed to this PC in TEXT: verified, checked
    against today's plan, recorded through the same handle_decision the route
    and --approve use. A reply usually quotes the earlier mail, so the text can
    hold a decision already opened AND a fresh one; every block that opens is
    applied in the order it was made (its ts), and the newest is the last word.
    Returns (status, payload) in the route's shape; 200 if any block was
    recorded, else the last refusal."""
    dp = _dp()
    key, pem = my_key(key_path)
    try:
        envs = [e for e in blocks(text) if isinstance(e, dict) and e.get("kind") == "decision"]
    except Exception as e:                                        # noqa: BLE001
        envs, err = [], "unreadable text: %s" % type(e).__name__
        _log("REFUSED a block: %s" % err, None, log_path)
        return 400, {"status": "error", "message": err}
    if not envs:
        _log("REFUSED a block: no decision sealed block in the text", None, log_path)
        return 400, {"status": "error", "message": "no decision sealed block in the text"}
    opened, refusals = [], []
    for env in envs:
        try:
            opened.append(open_env(env, key, pem))
        except SealedError as e:
            refusals.append(str(e))
        except Exception as e:                                    # noqa: BLE001  -- never a traceback on input
            refusals.append("unexpected %s while opening" % type(e).__name__)
    if not opened:
        _log("REFUSED a block: %s" % refusals[-1], None, log_path)
        return 400, {"status": "error", "message": refusals[-1]}
    opened.sort(key=lambda t: _num(t[1].get("ts")))
    applied, last = [], (400, {"status": "error", "message": "no decision block opened"})
    for env, obj, spk in opened:
        last = _apply_decision(dp, env, obj, spk, plan_dir, approvals, signers_path, seen_path, now, log_path)
        if last[0] == 200:
            applied.append(last[1]["decision"])
    if applied:
        return 200, {"status": "success", "decision": applied[-1], "applied": len(applied), "blocks": len(opened)}
    return last


def _apply_decision(dp, env, obj, spk, plan_dir, approvals, signers_path, seen_path, now, log_path):
    """One opened decision: the registry, the day, the nonce, then the ledger."""
    who = dp.signer_name(spk, signers_path)
    if not who:
        _log("REFUSED a decision from an unregistered key [%s]" % env["from"], None, log_path)
        return 403, {"status": "error", "message": "the sender's key [%s] is not a registered daily-plan signer" % env["from"]}
    date, today = str(obj.get("date", "")), dp.today(now)
    if date != today:
        _log("REFUSED a decision by %s for %s (today is %s)" % (who, date, today), obj, log_path)
        return 409, {"status": "error", "message": "the decision is for %s and today is %s; a sealed decision counts only on its own day" % (date, today)}
    nonce = str(obj.get("nonce", "") or "")
    seen = _seen(seen_path)
    if len(nonce) < 16 or nonce in seen:
        _log("REFUSED a decision by %s: nonce missing or already opened" % who, obj, log_path)
        return 409, {"status": "error", "message": "nonce missing or already opened (a sealed decision opens once)"}
    # decisions made on the phone are ordered by WHEN THE PHONE MADE THEM, not by
    # when their mails were opened here: one made earlier than the newest already
    # opened for this day is refused, so opening the mails in any order leaves
    # the phone's last word as the ledger's last word
    ts = _num(obj.get("ts"))
    newest = max((float(v[1]) for v in seen.values() if v[0] == date), default=None)
    if newest is not None and ts < newest:
        _log("REFUSED a decision by %s made at ts %s: a newer one (ts %s) was already opened for %s" % (who, ts, newest, date), obj, log_path)
        return 409, {"status": "error", "message": "a newer decision for %s was already opened here; this one was made earlier on the phone" % date}
    note = str(obj.get("note", "") or "")[:400]
    body = json.dumps({"date": date, "plan_sha256": str(obj.get("plan_sha256", "")), "decision": str(obj.get("decision", "")),
                       "note": ("by sealed mail" + (": " + note if note else ""))}).encode("utf-8")
    code, out = dp.handle_decision(body, who, spk, plan_dir, approvals)
    if code == 200:
        _remember(nonce, date, ts, seen_path)
        _log("OPENED decision from %s [%s]: %s for %s (sha %s) -> recorded" % (who, env["from"], obj.get("decision"), date, str(obj.get("plan_sha256", ""))[:12]), obj, log_path)
    else:
        _log("REFUSED a decision by %s: %s" % (who, out.get("message")), obj, log_path)
    return code, out


EXPLAIN = __doc__.split("Run:")[0].strip()


IDENTITY_DIR = os.path.join(os.path.expanduser("~"), ".covenant", "phone-identity")


def open_identity(text, key_path=None, dest_dir=None):
    """Open a sealed IDENTITY block from the phone and save the key it carries.

    WHY IT COMES THIS WAY (2026-09-14). The phone node's private key had exactly one route
    off the phone -- `adb run-as` -- which needs a cable and a debuggable build. The security
    audit closed debuggable, and the operator's phone offers no wireless debugging, so the
    app now seals its own key to THIS PC's public key and hands the block to whatever will
    carry it. In transit it is ciphertext only this machine can open, which is a better
    posture than the file `run-as` used to hand over in the clear.

    Saved outside every repository, beside the phone signing key, and never overwritten: a
    second, different key arriving where one is already saved is a question, not a refresh."""
    key, pem = my_key(key_path)
    env, obj, spk = open_block(text, key, pem, kind="identity")
    body = str(obj.get("key_pem") or "")
    if "PRIVATE KEY" not in body:
        raise SealedError("the block opened but carries no private key")
    claimed = str(obj.get("pubkey_fingerprint") or "")
    if claimed and claimed != fingerprint(spk):
        raise SealedError("the key inside does not match the phone that signed the block")
    d = dest_dir or IDENTITY_DIR
    os.makedirs(d, exist_ok=True)
    dest = os.path.join(d, "covenant_unified_%s.db.key" % (str(obj.get("node_id") or "phone")[:40]))
    if os.path.exists(dest):
        raise SealedError("a key is already saved at %s -- move it aside yourself if you mean to replace it" % dest)
    tmp = "%s.%d.tmp" % (dest, os.getpid())
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(body)
        os.replace(tmp, dest)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
    try:
        os.chmod(dest, 0o600)
    except OSError:
        pass
    _log("identity key from %s opened and saved (%s)" % (obj.get("node_id"), fingerprint(spk)))
    return dest, fingerprint(spk)


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="the plan and the decision, sealed for the mail")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--seal-plan", action="store_true")
    g.add_argument("--open", metavar="FILE")
    g.add_argument("--peek", metavar="FILE")
    g.add_argument("--open-identity", metavar="FILE", dest="open_identity")
    g.add_argument("--fingerprint", action="store_true")
    g.add_argument("--explain", action="store_true")
    g.add_argument("--log", nargs="?", const=20, type=int, metavar="N")
    ap.add_argument("--to", default="phone")
    ap.add_argument("--key", default=None)
    a = ap.parse_args(argv)

    def read(f):
        return sys.stdin.read() if f == "-" else open(f, encoding="utf-8", errors="replace").read()

    if a.seal_plan:
        try:
            block, path = seal_plan(a.to, key_path=a.key)
        except SealedError as e:
            print("cannot seal: %s" % e); return 1
        print(block); print("saved %s" % path, file=sys.stderr); return 0
    if a.open:
        code, out = open_decision(read(a.open), key_path=a.key)
        print(json.dumps(out, indent=1)); return 0 if code == 200 else 1
    if a.open_identity:
        try:
            dest, fp = open_identity(read(a.open_identity), key_path=a.key)
        except SealedError as e:
            print("cannot open: %s" % e); return 1
        print("saved the phone node's identity key")
        print("  file:        %s" % dest)
        print("  fingerprint: %s" % fp)
        reg = ""
        try:
            import covenant_daily_plan as _dp
            for name, pem2 in _dp.signers().items():
                if fingerprint(pem2) == fp:
                    reg = name
                    break
        except Exception:                                         # noqa: BLE001
            reg = ""
        print("  check:       %s" % ("MATCHES the signer this PC has registered as '%s'" % reg if reg
                                     else "NOT a key this PC has registered -- worth understanding before relying on it"))
        return 0
    if a.peek:
        for p in peek(read(a.peek)) or [{"shape": "no sealed block in the text"}]:
            print(json.dumps(p))
        return 0
    if a.fingerprint:
        _key, pem = my_key(a.key)
        print(fingerprint(pem)); return 0
    if a.explain:
        print(EXPLAIN); return 0
    if a.log is not None:
        try:
            lines = open(LOG, encoding="utf-8").read().splitlines()
        except OSError:
            lines = []
        print("\n".join(lines[-a.log:]) if lines else "(no sealed mail yet)"); return 0
    ap.print_help(); return 0


if __name__ == "__main__":
    sys.exit(main())
