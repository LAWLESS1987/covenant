#!/usr/bin/env python3
"""
covenant_seal.py -- "they can tell, but they cannot recreate."

Two separate things, deliberately kept apart:

  PROOF  (public)   a manifest of SHA-256 hashes plus one root hash. Anyone
                    holding it can verify that a file they are shown is
                    byte-identical to yours, and can prove the set existed
                    in this exact state at a point in time. It reveals
                    nothing about the contents. Hashes are one-way: you
                    cannot rebuild a file from its digest.

  SECRECY (private) the files themselves, encrypted with AES-256-GCM under a
                    key derived from YOUR passphrase by scrypt. Without the
                    passphrase the archive is noise.

Publish the proof. Keep the archive. That is the whole shape of it.

  covenant_seal.py manifest     write MANIFEST.sha256 + SEAL_ROOT.txt
  covenant_seal.py public       write SEAL_PUBLIC.txt -- root + hashed
                                filenames, safe to hand to anyone
  covenant_seal.py verify       re-hash everything, report any drift
  covenant_seal.py encrypt --keyfile PATH
                                unlock by POSSESSION -- nothing to remember,
                                nothing to write down. Add --passphrase to
                                require both.
  covenant_seal.py encrypt      passphrase only
  covenant_seal.py decrypt DIR [--keyfile PATH]

FOUR THINGS WORTH BEING BLUNT ABOUT

1. This NEVER deletes your plaintext. Encrypting is not moving. Delete the
   originals yourself, only after you have decrypted the archive into a
   scratch folder and confirmed you can read it. An encrypted file you
   cannot open is not a backup, it is a loss with extra steps.

2. Nothing you type here leaves this machine. Not to disk, not to a log, not
   to Claude. With --keyfile there is nothing to type at all: the archive
   opens for whoever holds that file.

   Either way there is no reset. Lose the passphrase, or lose the key file,
   and the archive is gone.

   AND THE ONE THAT ACTUALLY BITES: --keyfile is only secrecy if the key file
   lives somewhere the archive does not. Both in covenant\ means anyone who
   copies the folder has the lock and the key. The tool warns, and then does
   what you asked -- integrity still holds, secrecy does not.

3. covenant_A.db.key is inside this archive. It is your founder identity AND
   the genesis mint key. Sealing it and then losing the passphrase loses the
   genesis balance permanently. Keep an UNENCRYPTED copy somewhere physically
   safe before you rely on this.

4. What this protects against: someone who gets a copy of the folder, a
   backup, or the disk. What it does not protect against: anything running
   on this machine while you are logged in, which can read the plaintext
   directly. Encryption at rest is a real control with a narrow scope.
"""
import argparse
import getpass
import hashlib
import io
import json
import os
import struct
import sys
import tarfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))

# Big, regenerable, or actively written by a running node. Excluded so the
# manifest is stable and the archive is not mostly virtualenv.
EXCLUDE_DIRS = {".venv", "__pycache__", ".git", "logs", "node_modules",
                # Scratch restores. Without this, `decrypt _unsealtest`
                # followed by `manifest` seals a copy of the archive inside
                # the next archive. Observed on the real folder: 129 files
                # became 261 and covenant_sealed.bin doubled to 1.4 MB.
                # A manifest must not swallow its own output.
                "_unsealtest", "_unseal", "scratch", "_to_delete"}
EXCLUDE_EXT = {".pyc", ".pyo", ".tmp",
               # 88MB of vendor installer is not your work and does not
               # need sealing. Re-downloadable; excluded from both the
               # manifest and the archive.
               ".msi", ".exe", ".zip"}
EXCLUDE_SUFFIX = ("-wal", "-shm")          # sqlite sidecars: in flux
EXCLUDE_NAMES = {"covenant_sealed.bin", "covenant_sealed.json",
                 "MANIFEST.sha256", "SEAL_ROOT.txt", "SEAL_PUBLIC.txt"}

SCRYPT_N, SCRYPT_R, SCRYPT_P = 1 << 17, 8, 1     # ~128 MB, ~1s. Deliberate.
MAGIC = b"CVNTSEAL1"
INFO = b"covenant-seal-v1"

# How the archive key was derived. Stored in covenant_sealed.json so decrypt
# does not have to guess.
MODE_PASS = "passphrase"
MODE_KEY = "keyfile"
MODE_BOTH = "keyfile+passphrase"


# ------------------------------------------------------------------ walk --
def walk():
    for root, dirs, files in os.walk(HERE):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDE_DIRS)
        for f in sorted(files):
            if f in EXCLUDE_NAMES or os.path.splitext(f)[1] in EXCLUDE_EXT:
                continue
            if f.endswith(EXCLUDE_SUFFIX):
                continue
            full = os.path.join(root, f)
            rel = os.path.relpath(full, HERE).replace("\\", "/")
            yield rel, full


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_manifest():
    rows = []
    for rel, full in walk():
        try:
            rows.append((rel, os.path.getsize(full), sha256_file(full)))
        except OSError as e:
            print(f"  skipped {rel}: {e}")
    rows.sort()
    return rows


def root_hash(rows):
    """One hash over the whole set. Changing any byte of any file, renaming
    one, adding one, or removing one changes this value."""
    h = hashlib.sha256()
    for rel, size, digest in rows:
        h.update(f"{digest}  {size}  {rel}\n".encode())
    return h.hexdigest()


# ------------------------------------------------------------- manifest --
def cmd_manifest(_):
    rows = build_manifest()
    root = root_hash(rows)
    with open(os.path.join(HERE, "MANIFEST.sha256"), "w", encoding="utf-8") as f:
        for rel, size, digest in rows:
            f.write(f"{digest}  {size:>10}  {rel}\n")
    with open(os.path.join(HERE, "SEAL_ROOT.txt"), "w", encoding="utf-8") as f:
        f.write(f"root  {root}\nfiles {len(rows)}\nutc   "
                f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\n")
    print(f"  {len(rows)} files")
    print(f"  root {root}")
    print("  wrote MANIFEST.sha256 and SEAL_ROOT.txt")
    print("  MANIFEST.sha256 lists your FILENAMES -- use `public` for a")
    print("  version safe to hand to someone you are not sharing names with.")
    return 0


def cmd_public(_):
    """Root hash plus hashed filenames. Proves the set and lets someone check
    a specific file they already hold, without disclosing what exists."""
    rows = build_manifest()
    root = root_hash(rows)
    with open(os.path.join(HERE, "SEAL_PUBLIC.txt"), "w", encoding="utf-8") as f:
        f.write("# Covenant seal -- public proof.\n")
        f.write("# Each line: sha256(path) then sha256(contents).\n")
        f.write("# To check a file you hold: hash its path and its bytes and\n")
        f.write("# look for the pair. You cannot go the other way -- a digest\n")
        f.write("# does not yield the file.\n")
        f.write(f"root {root}\n")
        f.write(f"utc  {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\n")
        f.write(f"n    {len(rows)}\n")
        for rel, _size, digest in rows:
            f.write(f"{hashlib.sha256(rel.encode()).hexdigest()} {digest}\n")
    print(f"  wrote SEAL_PUBLIC.txt  ({len(rows)} entries)")
    print(f"  root {root}")
    print("  Safe to publish: no filenames, no sizes, no contents.")
    return 0


def cmd_verify(_):
    path = os.path.join(HERE, "MANIFEST.sha256")
    if not os.path.exists(path):
        print("  no MANIFEST.sha256 -- run `manifest` first")
        return 2
    old = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            p = line.rstrip("\n").split(None, 2)
            if len(p) == 3:
                old[p[2]] = (int(p[1]), p[0])
    rows = build_manifest()
    new = {r: (s, d) for r, s, d in rows}
    changed = [k for k in old.keys() & new.keys() if old[k][1] != new[k][1]]
    added = sorted(new.keys() - old.keys())
    removed = sorted(old.keys() - new.keys())
    for k in sorted(changed):
        print(f"  CHANGED  {k}")
    for k in added:
        print(f"  ADDED    {k}")
    for k in removed:
        print(f"  REMOVED  {k}")
    if not (changed or added or removed):
        print(f"  {len(rows)} files, all match. root {root_hash(rows)}")
        return 0
    old_rows = sorted((rel, sz, dg) for rel, (sz, dg) in old.items())
    print(f"  root was {root_hash(old_rows)}")
    print(f"  root now {root_hash(rows)}")
    print(f"  {len(changed)} changed, {len(added)} added, {len(removed)} removed")
    return 1


# ------------------------------------------------------------- crypto ----
def _derive(passphrase: bytes, salt: bytes) -> bytes:
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
    return Scrypt(salt=salt, length=32, n=SCRYPT_N, r=SCRYPT_R,
                  p=SCRYPT_P).derive(passphrase)


def _derive_keyfile(keybytes: bytes, salt: bytes) -> bytes:
    """Key from a file you HOLD rather than a phrase you remember.

    The key file is already high-entropy -- it is a private key -- so it does
    not need scrypt's deliberate slowness. scrypt exists to make GUESSING a
    human-chosen passphrase expensive; there is nothing to guess here. HKDF
    is the right primitive for stretching existing entropy.

    THE TRADE, STATED PLAINLY: this turns "something you know" into
    "something you have". You cannot forget it. You can lose it, and if you
    lose covenant_A.db.key you have already lost the founder identity and the
    genesis mint key, so this consolidates onto one object you were obliged to
    protect anyway rather than adding a second.

    AND THE PART THAT MATTERS MORE: if the key file lives in the same folder
    as the archive, you have locked nothing. Anyone who copies the folder gets
    both halves. Keyfile unlock is only worth doing if the key file lives
    somewhere the archive does not -- a USB stick, a different machine. The
    tool warns when it sees them side by side."""
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=salt,
                info=INFO).derive(keybytes)


def _key_material(mode, salt, keyfile, passphrase):
    """One place where every mode resolves to 32 bytes."""
    if mode == MODE_KEY:
        return _derive_keyfile(keyfile, salt)
    if mode == MODE_PASS:
        return _derive(passphrase, salt)
    # both: the passphrase is stretched first, then bound to the key file, so
    # neither half alone is sufficient.
    return _derive_keyfile(_derive(passphrase, salt) + keyfile, salt)


def _read_keyfile(path):
    if not os.path.exists(path):
        print(f"  key file not found: {path}")
        return None
    with open(path, "rb") as f:
        data = f.read()
    if len(data) < 32:
        print(f"  {path} is only {len(data)} bytes -- that is not a key file")
        return None
    same_dir = os.path.dirname(os.path.abspath(path)) == HERE
    if same_dir:
        print()
        print("  WARNING: the key file is in the same folder as the archive.")
        print("  Anyone who copies this folder gets the lock and the key")
        print("  together, which is the same as not locking it. Move the key")
        print("  file to a USB stick or another machine and point --keyfile")
        print("  at it there. Sealing anyway is fine for integrity, but do")
        print("  not count it as secrecy.")
        print()
    return data


def _tar_bytes(rows):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for rel, _size, _d in rows:
            tar.add(os.path.join(HERE, rel), arcname=rel)
    return buf.getvalue()


def cmd_encrypt(args):
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError:
        print("  needs the `cryptography` package (it is in requirements.txt):")
        print("      pip install cryptography")
        return 2

    rows = build_manifest()
    root = root_hash(rows)
    print(f"  {len(rows)} files, root {root}")

    keybytes = passphrase = None
    if args.keyfile:
        keybytes = _read_keyfile(args.keyfile)
        if keybytes is None:
            return 2
    if args.passphrase or not args.keyfile:
        print()
        print("  Your passphrase is typed here and goes nowhere else -- not to")
        print("  disk, not to a log, not to Claude. If you lose it, this")
        print("  archive is gone.")
        p1 = getpass.getpass("  passphrase: ").encode()
        p2 = getpass.getpass("  again     : ").encode()
        if p1 != p2:
            print("  they do not match. nothing written.")
            return 2
        if len(p1) < 12:
            print("  too short. 12+ characters, ideally words.")
            return 2
        passphrase = p1

    mode = (MODE_BOTH if (keybytes and passphrase)
            else MODE_KEY if keybytes else MODE_PASS)
    print(f"  unlock mode: {mode}")
    if mode == MODE_KEY:
        print(f"  the archive opens for whoever holds {args.keyfile}.")
        print("  Nothing to remember. Nothing to write down.")
        print("  covenant_A.db.key is INSIDE the archive as well as being the")
        print("  key to it -- that is fine, but it means the copies in")
        print("  _keybackup\\ and %USERPROFILE%\\.covenant-keys\\ are now")
        print("  load-bearing. Do not delete them.")

    salt = os.urandom(16)
    print("  deriving key...")
    key = _key_material(mode, salt, keybytes, passphrase)
    nonce = os.urandom(12)
    plain = _tar_bytes(rows)
    blob = AESGCM(key).encrypt(nonce, plain, MAGIC + root.encode())

    out = os.path.join(HERE, "covenant_sealed.bin")
    with open(out, "wb") as f:
        f.write(MAGIC)
        f.write(struct.pack("<HH", len(salt), len(nonce)))
        f.write(salt)
        f.write(nonce)
        f.write(blob)
    meta = {"format": "AES-256-GCM", "kdf": mode, "n": SCRYPT_N, "r": SCRYPT_R,
            "p": SCRYPT_P, "root": root, "files": len(rows),
            "keyfile_hint": os.path.basename(args.keyfile) if args.keyfile else None,
            "plain_bytes": len(plain), "sealed_bytes": len(blob),
            "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    with open(os.path.join(HERE, "covenant_sealed.json"), "w",
              encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    # Round-trip NOW, with the key still in memory. An archive that has never
    # been opened is a guess, not a backup.
    try:
        with open(out, "rb") as f:
            data = f.read()
        ls, ln = struct.unpack("<HH", data[len(MAGIC):len(MAGIC) + 4])
        off = len(MAGIC) + 4
        s2, n2 = data[off:off + ls], data[off + ls:off + ls + ln]
        got = AESGCM(_key_material(mode, s2, keybytes, passphrase)).decrypt(
            n2, data[off + ls + ln:], MAGIC + root.encode())
        assert got == plain
        print(f"  round-trip verified: decrypts to the same {len(plain)} bytes.")
    except Exception as e:                                  # noqa: BLE001
        print(f"  ROUND-TRIP FAILED: {type(e).__name__}: {e}")
        print("  Do NOT delete anything. Tell Claude.")
        return 1

    print(f"  wrote covenant_sealed.bin  ({len(blob) / 1e6:.1f} MB)")
    print(f"  wrote covenant_sealed.json (parameters + root, no secrets)")
    print()
    print("  Your plaintext files are UNTOUCHED. That is deliberate.")
    print("  Before deleting anything, run:")
    print("      python covenant_seal.py decrypt some_scratch_folder")
    print("  and read a file out of it. Then decide.")
    return 0


def cmd_decrypt(args):
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError:
        print("  needs the `cryptography` package"); return 2
    src = os.path.join(HERE, "covenant_sealed.bin")
    if not os.path.exists(src):
        print("  no covenant_sealed.bin here"); return 2
    meta = {}
    mp = os.path.join(HERE, "covenant_sealed.json")
    if os.path.exists(mp):
        meta = json.load(open(mp, encoding="utf-8"))
    with open(src, "rb") as f:
        data = f.read()
    if not data.startswith(MAGIC):
        print("  not a covenant seal archive"); return 2
    ls, ln = struct.unpack("<HH", data[len(MAGIC):len(MAGIC) + 4])
    off = len(MAGIC) + 4
    salt, nonce = data[off:off + ls], data[off + ls:off + ls + ln]
    mode = meta.get("kdf", MODE_PASS)
    hint = meta.get("keyfile_hint")
    print(f"  unlock mode: {mode}" + (f" (key file: {hint})" if hint else ""))

    keybytes = passphrase = None
    if mode in (MODE_KEY, MODE_BOTH):
        kf = args.keyfile or hint
        if not kf:
            print("  this archive needs --keyfile PATH")
            return 2
        keybytes = _read_keyfile(kf)
        if keybytes is None:
            return 2
    if mode in (MODE_PASS, MODE_BOTH):
        passphrase = getpass.getpass("  passphrase: ").encode()
    print("  deriving key...")
    try:
        plain = AESGCM(_key_material(mode, salt, keybytes, passphrase)).decrypt(
            nonce, data[off + ls + ln:],
            MAGIC + meta.get("root", "").encode())
    except Exception:                                       # noqa: BLE001
        print("  wrong key, or the archive has been altered.")
        print("  (GCM authenticates: a modified archive fails here rather")
        print("   than decrypting to something subtly wrong.)")
        return 1
    dest = os.path.abspath(args.dest)
    os.makedirs(dest, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(plain), mode="r:gz") as tar:
        for m in tar.getmembers():
            t = os.path.abspath(os.path.join(dest, m.name))
            if not t.startswith(dest + os.sep) and t != dest:
                print(f"  refusing path outside destination: {m.name}")
                return 1
        tar.extractall(dest)
    print(f"  restored {len(plain)} bytes into {dest}")
    if meta.get("root"):
        print(f"  archive root was {meta['root']}")
        print("  compare with: python covenant_seal.py manifest")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("manifest")
    sub.add_parser("public")
    sub.add_parser("verify")
    e = sub.add_parser("encrypt")
    e.add_argument("--keyfile", help="unlock by POSSESSION of this file "
                                     "instead of a passphrase")
    e.add_argument("--passphrase", action="store_true",
                   help="also require a passphrase (two factors)")
    d = sub.add_parser("decrypt")
    d.add_argument("dest")
    d.add_argument("--keyfile", help="path to the key file, if it has moved")
    a = ap.parse_args()
    return {"manifest": cmd_manifest, "public": cmd_public, "verify": cmd_verify,
            "encrypt": cmd_encrypt, "decrypt": cmd_decrypt}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
