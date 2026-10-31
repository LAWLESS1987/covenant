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
    """The tool's exit code and output. A crash is an answer too ("EXC"), so a check reads it under its own name."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        try:
            rc = TK.main(argv)
        except Exception as e:                                   # noqa: BLE001 -- reported, never hidden
            rc = "EXC"
            print("%s: %s" % (type(e).__name__, e))
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

    # TK1i -- the half-made key from TK1g (exit 3) can be FINISHED. Measured on TETSU on 2026-10-31: there was no
    # way to complete it, and --check crashed on the missing public half.
    rc, out = run(["--dir", folder2, "--check"])
    check("TK1i --check on a half-made key says so (exit 5) instead of crashing", rc == 5 and "--finish" in out,
          (rc, out[:200]))
    with open(p2, "rb") as fh:
        half_bytes = fh.read()
    if os.name == "nt":
        # as on TETSU: the half-made key carries a stray ACE that --finish must clear by re-locking, not ignore
        subprocess.run(["icacls", os.path.abspath(p2), "/grant", "*S-1-1-0:(R)"], capture_output=True)
    rc, out = run(["--dir", folder2, "--finish"])
    with open(p2, "rb") as fh:
        after_finish = fh.read()
    pub2_pem = open(_pub2, encoding="utf-8").read() if os.path.exists(_pub2) else ""
    check("TK1i --finish re-locks, verifies and writes the public half of the SAME key (exit 0)",
          rc == 0 and after_finish == half_bytes and pub2_pem and R.key_id(pub2_pem) in out, (rc, out[:200]))
    check("TK1i ...never printing the private key", "PRIVATE KEY" not in out)
    try:
        TK._verify(p2)
        finished_locked = True
    except Exception as e:                                       # noqa: BLE001
        finished_locked = "%s: %s" % (type(e).__name__, str(e)[:160])
    check("TK1i ...and the finished key is owner-only again (the stray ACE was cleared, not ignored)",
          finished_locked is True, finished_locked)
    rc, out = run(["--dir", folder2, "--finish"])
    check("TK1i ...and a second --finish REFUSES (exit 2)", rc == 2 and "REFUSED" in out, (rc, out[:200]))

    # TK1h -- the lock removes explicit ACEs for other principals (TETSU: an explicit ReadAndExecute ACE for the
    # creating logon session survived /inheritance:r /grant:r and the verify refused the key).
    if os.name == "nt":
        # The probes sit in a folder that grants Everyone INHERITABLY, so a lock that let inheritance back in
        # would leave Everyone on the file and fail -- an owner-only temp folder would hide that.
        open_dir = os.path.join(base, "open_parent")
        os.makedirs(open_dir, exist_ok=True)
        subprocess.run(["icacls", open_dir, "/grant", "*S-1-1-0:(OI)(CI)(RX)"], capture_output=True)
        for label, sid in (("Everyone (a named principal)", "*S-1-1-0"),
                           ("a logon-session SID (unresolvable, as on TETSU)", "*S-1-5-5-0-4242")):
            probe = os.path.join(open_dir, "acl_probe_%d.txt" % len(_results))
            with open(probe, "w") as fh:
                fh.write("probe")
            g = subprocess.run(["icacls", probe, "/grant", "%s:(RX)" % sid], capture_output=True, text=True)
            try:
                TK._verify(probe)
                before = "verified"
            except Exception as e:                                  # noqa: BLE001
                before = "refused"
            try:
                TK._lock(probe)
                TK._verify(probe)
                after = "verified"
            except Exception as e:                                  # noqa: BLE001
                after = "%s: %s" % (type(e).__name__, str(e)[:160])
            check("TK1h an explicit ACE for %s is REMOVED by the lock (refused before, verified after)" % label,
                  g.returncode == 0 and before == "refused" and after == "verified", (g.returncode, before, after))

    passed, total = sum(_results), len(_results)
    print(f"\nTK1: {passed}/{total} checks passed")
    print("temp folder kept (keys are probes, never real): %s" % base)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
