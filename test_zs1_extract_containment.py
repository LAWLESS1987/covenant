#!/usr/bin/env python3
"""test_zs1_extract_containment.py -- ZS1: archive extraction cannot write outside its destination.

WHY THIS EXISTS (2026-11-02, the security-hunt). A sweep of the tree found three `extractall` sites:

  - ai_memory_system/import_conversations.py and mobile/usb_link.py use **zipfile**. CPython's
    zipfile re-roots '..' and drive-letter members UNDER the destination (it sanitizes in
    _extract_member), so a classic Zip-Slip member cannot escape. ZS1.z* MEASURES that on this
    interpreter rather than trusting it -- if a future Python relaxed it, or a site swapped to a
    non-sanitizing extractor, the property these two untrusted-input sites rely on would be gone.

  - covenant_seal.cmd_decrypt uses **tarfile**, which does NOT self-sanitize member paths. It
    carries its OWN hand-rolled guard (covenant_seal.py:768): abspath-join every member against
    dest, refuse any that escapes. That guard was UNPINNED -- no test drove a malicious tar member
    through the real unseal. A hand-rolled guard that has only ever passed has never been observed
    (rule 8), so ZS1.s* drives the REAL cmd_decrypt both ways.

NOT a found vulnerability: the zip sites are safe by the stdlib and the tar site is guarded (and a
sealed archive is AES-GCM authenticated, so reaching the guard needs the key already). This pins the
properties that make all three sound, so none can regress silently.

Drives the real covenant_seal.cmd_decrypt over a crafted sealed archive built with the module's own
_key_material and MAGIC (so decrypt genuinely succeeds and reaches the guard). seal.HERE is
redirected to a tempdir, so the live checkout is never written. Run: python3 test_zs1_extract_containment.py
"""
import getpass
import io
import json
import os
import struct
import sys
import tarfile
import tempfile
import zipfile
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print("%s  %s%s" % ("ok  " if ok else "FAIL", label, "" if ok else "  -- " + str(detail)[:300]), flush=True)


def _escaped(base, dest):
    """Files under `base` that landed OUTSIDE `dest` (the sealed sidecars excluded)."""
    dest = os.path.abspath(dest)
    out = []
    for dp, _, fns in os.walk(base):
        for fn in fns:
            if fn.startswith("covenant_sealed."):
                continue
            p = os.path.abspath(os.path.join(dp, fn))
            if p != dest and not p.startswith(dest + os.sep):
                out.append(os.path.relpath(p, base))
    return out


def _inner_tar(members):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, data in members.items():
            ti = tarfile.TarInfo(name)
            ti.size = len(data)
            tar.addfile(ti, io.BytesIO(data))
    return buf.getvalue()


def _write_seal(seal, heredir, plain, passphrase):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    salt, nonce, root = os.urandom(16), os.urandom(12), "deadbeefroot"
    key = seal._key_material(seal.MODE_PASS, salt, None, passphrase)
    blob = AESGCM(key).encrypt(nonce, plain, seal.MAGIC + root.encode())
    with open(os.path.join(heredir, "covenant_sealed.bin"), "wb") as f:
        f.write(seal.MAGIC)
        f.write(struct.pack("<HH", len(salt), len(nonce)))
        f.write(salt + nonce + blob)
    with open(os.path.join(heredir, "covenant_sealed.json"), "w", encoding="utf-8") as f:
        json.dump({"kdf": seal.MODE_PASS, "root": root}, f)


def zip_checks():
    """ZS1.z: the stdlib property the two untrusted-input zip sites rely on -- a hostile member is
    re-rooted UNDER dest, never outside it. Measured on this interpreter."""
    base = tempfile.mkdtemp(prefix="zs1_zip_")
    try:
        dest = os.path.join(base, "dest")
        os.makedirs(dest)
        zpath = os.path.join(base, "evil.zip")
        with zipfile.ZipFile(zpath, "w") as z:
            z.writestr("normal.txt", b"ok\n")
            z.writestr("../zs1_zip_escape.txt", b"ESCAPED\n")                     # classic Zip-Slip member
            z.writestr("/" + os.path.join(base, "ABS", "zs1_zip_abs.txt").lstrip("/\\"), b"ABS\n")
        with zipfile.ZipFile(zpath) as z:
            z.extractall(dest)
        # the hostile members' escape targets, named precisely (not "anything outside dest" -- evil.zip
        # legitimately sits in base): a '..' target one level above dest, and the absolute-path target.
        rel_target = os.path.join(base, "zs1_zip_escape.txt")
        abs_target = os.path.join(base, "ABS", "zs1_zip_abs.txt")
        check("ZS1.z1 zipfile.extractall keeps every hostile member inside dest (neither escape target written)",
              not os.path.exists(rel_target) and not os.path.exists(abs_target),
              "rel=%s abs=%s" % (os.path.exists(rel_target), os.path.exists(abs_target)))
        # the hostile member WAS present and WAS re-rooted (so z1 is active sanitization, not an empty zip)
        rerooted = any(f == "zs1_zip_escape.txt" for _, _, fs in os.walk(dest) for f in fs)
        check("ZS1.z2 ...and the '..' member was extracted RE-ROOTED under dest (sanitized, not dropped)",
              rerooted, "dest tree: %s" % [f for _, _, fs in os.walk(dest) for f in fs])
    finally:
        import shutil
        shutil.rmtree(base, ignore_errors=True)


def seal_checks():
    try:
        import covenant_seal as seal
    except Exception as e:                                           # noqa: BLE001
        print("NOT RUN: covenant_seal did not import (%s) -- ZS1.s* did not run. Not a pass." % e)
        return
    try:
        import cryptography  # noqa: F401
    except Exception:                                                # noqa: BLE001
        print("NOT RUN: the `cryptography` package is absent -- the real unseal cannot run. Not a pass.")
        return

    PW = "correct horse battery staple words"
    base = tempfile.mkdtemp(prefix="zs1_seal_")
    orig_here, orig_getpass = seal.HERE, getpass.getpass
    try:
        seal.HERE = base
        getpass.getpass = lambda *a, **k: PW

        class A:
            pass

        # ZS1.s1 REFUSE: a sealed archive whose tar carries a '..' member -> the real unseal refuses
        # at the guard, writes nothing outside dest, and says so.
        _write_seal(seal, base, _inner_tar({"notes.txt": b"ok\n", "../zs1_escape.txt": b"PWNED\n"}), PW.encode())
        a = A()
        a.dest, a.keyfile = os.path.join(base, "out_evil"), None
        out = io.StringIO()
        with redirect_stdout(out):
            rc = seal.cmd_decrypt(a)
        said = out.getvalue()
        escaped_here = os.path.exists(os.path.join(base, "zs1_escape.txt"))
        check("ZS1.s1 unseal REFUSES a tar member that escapes dest (rc=1), names it, and writes nothing outside",
              rc == 1 and "outside destination" in said and not escaped_here and not _escaped(base, a.dest),
              "rc=%s escaped=%s said=%s" % (rc, escaped_here, said.strip().splitlines()[-1:]))

        # ZS1.s2 CONTROL / the other way: a benign sealed archive restores cleanly -> the guard is not
        # a blanket block.
        _write_seal(seal, base, _inner_tar({"notes.txt": b"ok\n", "sub/deep.txt": b"deep\n"}), PW.encode())
        a = A()
        a.dest, a.keyfile = os.path.join(base, "out_ok"), None
        out = io.StringIO()
        with redirect_stdout(out):
            rc = seal.cmd_decrypt(a)
        check("ZS1.s2 ...and a benign archive restores (rc=0, files land inside dest)",
              rc == 0 and os.path.exists(os.path.join(a.dest, "notes.txt"))
              and os.path.exists(os.path.join(a.dest, "sub", "deep.txt")), "rc=%s" % rc)

        # ZS1.s3 the guard is LOAD-BEARING: the SAME tar member, extracted by a raw tarfile.extractall
        # with no guard, DOES escape -- tar is not self-sanitizing like zip, so s1's refusal is what
        # prevents the write (break-it-to-prove, rule 8).
        d3 = os.path.join(base, "raw_dest")
        os.makedirs(d3)
        with tarfile.open(fileobj=io.BytesIO(_inner_tar({"../zs1_raw_escape.txt": b"RAW\n"})), mode="r:gz") as t:
            # filter="fully_trusted" forces the no-sanitization path on every Python (3.12+ default-filters,
            # 3.14 rejects by default) so this demo of "tar does not self-sanitize" is deterministic. The
            # point: covenant_seal must NOT rely on that default -- its own guard is what refuses, per s1.
            try:
                t.extractall(d3, filter="fully_trusted")
            except TypeError:
                t.extractall(d3)                                     # Python < 3.12: no filter kwarg, old behaviour
        raw_escaped = os.path.exists(os.path.join(base, "zs1_raw_escape.txt"))
        check("ZS1.s3 WITHOUT the guard the same member escapes (raw tarfile.extractall) -- so s1's guard "
              "is load-bearing; tar, unlike zip, does not self-sanitize",
              raw_escaped, "raw extract did not escape -- then s1 would prove nothing on this interpreter")
    finally:
        seal.HERE, getpass.getpass = orig_here, orig_getpass
        import shutil
        shutil.rmtree(base, ignore_errors=True)


def main():
    print("ZS1 -- archive extraction cannot write outside its destination\n")
    zip_checks()
    seal_checks()
    ok = sum(1 for r in results if r)
    print("\nZS1: %d/%d passed" % (ok, len(results)))
    return 0 if results and ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
