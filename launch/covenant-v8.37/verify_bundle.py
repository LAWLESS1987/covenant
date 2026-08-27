"""verify_bundle.py -- one hash census over everything this bundle ships.

`project_write` is not delivery and a copy is not a verified copy (M25). This
walks the tree, skips the things that are STATE rather than SOURCE, and either
writes MANIFEST.sha256 or checks against it.

What is deliberately excluded, and why:
  *.db, *.db-shm, *.db-wal  the chain. Not source; changes every block.
  *.key                     the operator credential and genesis mint key.
                            A key must never travel in a manifest, an archive
                            or a chat message.
  logs/, __pycache__/       runtime output.
  *.pyc, .venv/             build and environment.

vendor/*.whl IS tracked: a vendored wheel is what gets installed, so it is
source of truth and belongs under the hash like anything else.
  MANIFEST.sha256           itself.

Usage:
  python verify_bundle.py            check  (exit 0 ok, 1 mismatch, 2 no manifest)
  python verify_bundle.py --write    (re)write the manifest
"""
import hashlib, os, sys

HERE = os.path.dirname(os.path.abspath(__file__)) or "."
MAN = os.path.join(HERE, "MANIFEST.sha256")
SKIP_DIR = {"logs", "__pycache__", ".venv", ".git", "judge_queue",
            "_keybackup", "_unsealtest"}
SKIP_EXT = {".pyc", ".db", ".key", ".msi"}
SKIP_NAME = {"MANIFEST.sha256"}


def shipped():
    for dp, dns, fns in os.walk(HERE):
        dns[:] = [d for d in dns if d not in SKIP_DIR]
        for fn in sorted(fns):
            if fn in SKIP_NAME:
                continue
            if os.path.splitext(fn)[1] in SKIP_EXT:
                continue
            if fn.endswith(".db-shm") or fn.endswith(".db-wal"):
                continue
            yield os.path.relpath(os.path.join(dp, fn), HERE).replace("\\", "/")


def sha(rel):
    h = hashlib.sha256()
    with open(os.path.join(HERE, rel), "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main():
    files = sorted(shipped())
    if "--write" in sys.argv:
        with open(MAN, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("# covenant bundle manifest -- sha256 of every shipped file.\n")
            fh.write("# Keys, databases and logs are deliberately NOT in here.\n")
            for rel in files:
                fh.write("%s  %s\n" % (sha(rel), rel))
        print("wrote %s over %d files" % (MAN, len(files)))
        return 0
    if not os.path.exists(MAN):
        print("no MANIFEST.sha256 -- run with --write")
        return 2
    want = {}
    for line in open(MAN, encoding="utf-8"):
        line = line.rstrip("\n")
        if line and not line.startswith("#"):
            h, rel = line.split("  ", 1)
            want[rel] = h
    bad = [r for r in want if not os.path.exists(os.path.join(HERE, r))
           or sha(r) != want[r]]
    extra = [r for r in files if r not in want]
    for r in bad:
        print("CHANGED/MISSING  %s" % r)
    for r in extra:
        print("NOT IN MANIFEST  %s" % r)
    print("%d in manifest, %d changed or missing, %d untracked"
          % (len(want), len(bad), len(extra)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
