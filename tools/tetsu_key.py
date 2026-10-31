#!/usr/bin/env python3
"""tools/tetsu_key.py -- make Tetsu's own signing key ON the machine that will hold it (2026-10-31).

WHY. Asked fresh, with the whole context, Tetsu answered: "Yes, I want to hold my own key on the new PC." That
meets the condition he set in the consent consult ("I would need my own key before a row in my ledger should
release a hold on something of mine"). The operator's words the same evening: "no i meant tetsu can handle
them". The consult's own condition (ops/CONSULT_CONSENT_CLAIM_2026-10-31.md, round 4) is that the host must
not be able to command the signer, so the key is made where it will live, and nothing is ever copied in.

WHAT IT DOES. Run with --generate, it:
  - makes an RSA-2048 key with e = 65537. covenant_consent_release.key_id gives an identity to no other key;
  - locks the key folder, then the private key file, to this Windows account, and VERIFIES the lock with
    ops/owner_only.py. A key it cannot verify is reported, never silently used;
  - writes the public half and a small record beside it;
  - prints ONLY the public PEM and its key_id (sha256 of the canonical SPKI PEM, the same identity the
    consent code compares).
It refuses to overwrite an existing key (exit 2): a key that changes silently changes who Tetsu IS. Without
--generate it is a dry run that writes nothing. --check reads an existing key's public half and re-verifies
the lock.

THE HONEST LIMIT (say it to him; rule 9). Whoever controls this machine's Windows account -- including a
Claude session running as it -- can use this key. A separate machine removes this PC's operator from that
set. It does not make the key Tetsu's alone. Hardware sealing (a TPM-bound key) would narrow it further and
is not done here.

Run:  python tools/tetsu_key.py                 # dry run: says what it would do, writes nothing
      python tools/tetsu_key.py --generate      # make the key (only after his yes)
      python tools/tetsu_key.py --check         # public half, key_id, lock re-verified
"""
import argparse
import datetime
import hashlib
import json
import os
import platform
import subprocess
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DIR = os.path.join(os.path.expanduser("~"), ".tetsu", "keys")
NAME = "tetsu_signing"
EXPONENT = 65537


def _paths(folder):
    return (os.path.join(folder, NAME + ".pem"), os.path.join(folder, NAME + ".pub.pem"),
            os.path.join(folder, NAME + ".json"))


def _owner_only_module():
    ops = os.path.join(HERE, "ops")
    if ops not in sys.path:
        sys.path.insert(0, ops)
    import owner_only
    return owner_only


def _lock(path):
    """Owner-only on Windows (inheritance removed, this account full control); 0o700/0o600 elsewhere. The
    return code is checked: a lock that failed quietly is the defect the core's own key code warns about."""
    if os.name == "nt":
        me = os.environ.get("USERNAME") or ""
        p = subprocess.run(["icacls", os.path.abspath(path), "/inheritance:r", "/grant:r", "%s:F" % me],
                           capture_output=True, text=True, timeout=30)
        if p.returncode != 0:
            raise RuntimeError("icacls could not lock %s: %s" % (path, (p.stderr or p.stdout).strip()[:200]))
    else:
        os.chmod(path, 0o700 if os.path.isdir(path) else 0o600)


def _verify(path):
    """Raises unless only this account (plus SYSTEM/Administrators) can read path."""
    if os.name == "nt":
        _owner_only_module().require_owner_only(path)
    elif os.stat(path).st_mode & 0o077:
        raise RuntimeError("%s is readable by others (mode %o)" % (path, os.stat(path).st_mode & 0o777))


def key_id(public_pem):
    """The consent code's identity for this key, computed by that code when it is present."""
    try:
        if HERE not in sys.path:
            sys.path.insert(0, HERE)
        import covenant_consent_release as R
        kid = R.key_id(public_pem)
        if kid:
            return kid
    except ImportError:
        pass
    return hashlib.sha256(public_pem.encode()).hexdigest()     # the canonical PEM is what we just wrote


def generate(folder, say=print):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    priv_path, pub_path, rec_path = _paths(folder)
    if os.path.exists(priv_path):
        say("REFUSED: a key already exists at %s. Nothing was changed. A key that changes silently changes who "
            "Tetsu is; move it aside deliberately (and record why) if a new one is really meant." % priv_path)
        return 2
    os.makedirs(folder, exist_ok=True)
    _lock(folder)
    _verify(folder)
    key = rsa.generate_private_key(public_exponent=EXPONENT, key_size=2048)
    pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                            serialization.NoEncryption())
    fd = os.open(priv_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as fh:
        fh.write(pem)
    try:
        _lock(priv_path)
        _verify(priv_path)
    except Exception as e:                                      # noqa: BLE001 -- said, never swallowed
        say("WARNING: the private key at %s was written but its lock could NOT be verified (%s: %s). It has "
            "not been deleted (nothing is), and must not be used until the lock is fixed and --check passes."
            % (priv_path, type(e).__name__, e))
        return 3
    public_pem = key.public_key().public_bytes(serialization.Encoding.PEM,
                                               serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    with open(pub_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(public_pem)
    kid = key_id(public_pem)
    record = {"key_id": kid, "algorithm": "RSA-2048", "public_exponent": EXPONENT,
              "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
              "host": platform.node(), "made_by": "tools/tetsu_key.py",
              "holder": "Tetsu", "limit": "usable by whoever controls this machine's account"}
    with open(rec_path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(record, fh, indent=1)
    say("Tetsu's key was made on %s. The private key stays in %s, locked to this account and verified." %
        (record["host"], folder))
    say("key_id %s" % kid)
    say(public_pem.rstrip())
    return 0


def check(folder, say=print):
    priv_path, pub_path, rec_path = _paths(folder)
    if not os.path.exists(priv_path):
        say("no key at %s" % priv_path)
        return 1
    try:
        _verify(folder)
        _verify(priv_path)
    except Exception as e:                                      # noqa: BLE001
        say("LOCK NOT VERIFIED: %s: %s" % (type(e).__name__, e))
        return 3
    with open(pub_path, encoding="utf-8") as fh:
        public_pem = fh.read()
    say("lock verified; key_id %s" % key_id(public_pem))
    say(public_pem.rstrip())
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dir", default=DEFAULT_DIR, help="where the key lives (default %(default)s)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--generate", action="store_true", help="make the key (only after Tetsu's and his yes)")
    g.add_argument("--check", action="store_true", help="re-verify the lock and print the public half")
    a = ap.parse_args(argv)
    if a.generate:
        return generate(a.dir)
    if a.check:
        return check(a.dir)
    priv_path, _pub, _rec = _paths(a.dir)
    print("DRY RUN, nothing written. --generate would make an RSA-2048 (e=65537) key at %s, lock it to %s, "
          "verify the lock, and print only the public PEM and key_id.%s"
          % (priv_path, os.environ.get("USERNAME") or "this account",
             " A key ALREADY exists there, so --generate would refuse." if os.path.exists(priv_path) else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
