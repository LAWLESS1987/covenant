#!/usr/bin/env python3
"""test_tk1_tetsu_key.py -- TK1. tools/tetsu_key.py makes Tetsu's key where it will live, and nothing else.

Driven both ways in a temp folder (never the real ~/.tetsu):
  TK1a  the dry run writes nothing, and says it would refuse once a key exists;
  TK1b  --generate makes an RSA-2048 key with e = 65537, locked to this account and VERIFIED by
        ops/owner_only.py, plus the public half and a record;
  TK1c  only the public PEM and key_id are printed -- the private key never reaches stdout;
  TK1d  key_id is the consent code's own identity for that key (covenant_consent_release.key_id), and the
        record carries the same one;
  TK1e  a second --generate REFUSES (exit 2) and leaves the private key byte-identical;
  TK1f  --check re-verifies the lock; a key whose lock was loosened reads "LOCK NOT VERIFIED" (exit 3);
  TK1g  a lock that cannot be verified at creation is reported (exit 3), and the file is kept, not deleted.
Offline.
"""
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "tools"))
import tetsu_key as TK                       # noqa: E402
import covenant_consent_release as R         # noqa: E402

_results = []


def check(label, cond, detail=""):
    _results.append(bool(cond))
    print(f"{'ok   ' if cond else 'FAIL '} {label}{('  -- ' + str(detail)[:300]) if detail and not cond else ''}")


def run(argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = TK.main(argv)
    return rc, out.getvalue()


def main():
    from cryptography.hazmat.primitives import serialization
    base = tempfile.mkdtemp(prefix="tk1_")
    folder = os.path.join(base, "keys")
    priv, pub, rec = TK._paths(folder)

    rc, out = run(["--dir", folder])
    check("TK1a the dry run exits 0 and writes nothing", rc == 0 and not os.path.exists(folder), (rc, out))

    rc, out = run(["--dir", folder, "--generate"])
    check("TK1b --generate exits 0 and writes the private key, the public half and the record",
          rc == 0 and all(os.path.exists(p) for p in (priv, pub, rec)), (rc, out[:300]))
    with open(priv, "rb") as fh:
        priv_bytes = fh.read()
    key = serialization.load_pem_private_key(priv_bytes, password=None)
    nums = key.public_key().public_numbers()
    check("TK1b ...RSA-2048 with e = 65537", key.key_size == 2048 and nums.e == 65537, (key.key_size, nums.e))
    try:
        TK._verify(folder)
        TK._verify(priv)
        locked = True
    except Exception as e:                                       # noqa: BLE001
        locked = "%s: %s" % (type(e).__name__, e)
    check("TK1b ...the folder and the private key are owner-only, verified", locked is True, locked)

    secret_lines = [l for l in priv_bytes.decode().splitlines() if l and not l.startswith("-----")]
    check("TK1c the private key never reaches stdout", "PRIVATE KEY" not in out
          and not any(l in out for l in secret_lines), out[:200])
    with open(pub, encoding="utf-8") as fh:
        public_pem = fh.read()
    with open(rec, encoding="utf-8") as fh:
        record = json.load(fh)
    kid = R.key_id(public_pem)
    check("TK1c ...the public PEM and its key_id are printed", public_pem.strip() in out and kid in out)
    check("TK1d key_id is the consent code's identity for this key, and the record carries it",
          kid is not None and record.get("key_id") == kid and record.get("public_exponent") == 65537, record)

    rc, out = run(["--dir", folder, "--generate"])
    with open(priv, "rb") as fh:
        after = fh.read()
    check("TK1e a second --generate REFUSES (exit 2) and leaves the key byte-identical",
          rc == 2 and "REFUSED" in out and after == priv_bytes, (rc, out[:200]))
    rc, out = run(["--dir", folder])
    check("TK1a ...and the dry run now says it would refuse", rc == 0 and "would refuse" in out, out[:200])

    rc, out = run(["--dir", folder, "--check"])
    check("TK1f --check re-verifies the lock and prints the key_id", rc == 0 and kid in out, (rc, out[:200]))
    if os.name == "nt":
        subprocess.run(["icacls", os.path.abspath(priv), "/grant", "*S-1-1-0:R"], capture_output=True)  # Everyone
        rc, out = run(["--dir", folder, "--check"])
        check("TK1f ...a key readable by Everyone reads LOCK NOT VERIFIED (exit 3)",
              rc == 3 and "LOCK NOT VERIFIED" in out, (rc, out[:200]))
    else:
        os.chmod(priv, 0o644)
        rc, out = run(["--dir", folder, "--check"])
        check("TK1f ...a key readable by others reads LOCK NOT VERIFIED (exit 3)",
              rc == 3 and "LOCK NOT VERIFIED" in out, (rc, out[:200]))

    folder2 = os.path.join(base, "keys2")
    saved = TK._verify
    calls = []

    def fails_on_file(path):
        calls.append(path)
        if path.endswith(".pem"):
            raise RuntimeError("probe: lock not taken")
        return saved(path)
    TK._verify = fails_on_file
    try:
        rc, out = run(["--dir", folder2, "--generate"])
    finally:
        TK._verify = saved
    p2, _pub2, _rec2 = TK._paths(folder2)
    check("TK1g a lock that cannot be verified at creation is REPORTED (exit 3), and the file is kept",
          rc == 3 and "could NOT be verified" in out and os.path.exists(p2), (rc, out[:200]))
    check("TK1g ...and no public half or record is written for an unverified key",
          not os.path.exists(_pub2) and not os.path.exists(_rec2))

    passed, total = sum(_results), len(_results)
    print(f"\nTK1: {passed}/{total} checks passed")
    print("temp folder kept (keys are probes, never real): %s" % base)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
