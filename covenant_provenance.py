#!/usr/bin/env python3
"""covenant_provenance.py -- when the antivirus flags a file, decide whether it
is OURS and verified, ours and unaccounted for, or foreign -- by hash, not by
opinion.

HIS WORDS, 2026-09-21: "Delete the anti-virus and have the system act as one."

WHAT THIS IS, AND WHAT IT REFUSES TO BE. It is not an antivirus and it does not
replace one. `covenant_security_probe` says so in its own docstring -- "Nothing
here reads the operating system" -- and nothing in this repository scans a file
as it executes, hooks a kernel, or carries a signature set. Deleting the one
thing on this machine that does would leave nothing, so this module does the
half the covenant CAN do and does it well: **Defender remains the senses, the
covenant becomes the judgement.**

THE JUDGEMENT IT MAKES. Until now every heuristic hit was handed to him with
the words "deciding a heuristic hit is a false positive is a person's, with the
hash in hand". He should not have to hold the hash. For a flagged path this
answers, from the bytes:

  ours:verified   the file is a named member of an archive this repository
                  registered, that archive still hashes to the digest recorded
                  from upstream, and -- when the file still exists -- the file
                  itself hashes to what that archive says it should. A
                  machine-learning verdict (a threat name ending `!ml`) on a
                  file with that provenance is a false positive, and it is
                  named as one instead of alarming him nightly.
  ours:unverified inside this tree (or a staged copy of it) but belonging to no
                  registered archive. NOT dismissed. He is told.
  foreign         outside this tree entirely. Always PRESENT, always his.

WHAT IT CANNOT PROVE, said plainly. That upstream was honest. A hash proves we
hold exactly what a project published; if the project itself were compromised,
the hash matches the compromised file. That is the normal bar for provenance
and this module claims nothing above it. It also cannot judge a file it has no
archive for, and it never guesses in that direction: unaccounted for is not
"probably fine", it is unaccounted for.
LICENCE: public domain.
"""
from __future__ import annotations

import hashlib
import json
import os
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REGISTRY = os.path.join(HERE, "ops", "known_artifacts.json")
ML_SUFFIX = "!ml"


def _sha256(path, chunk=1 << 20):
    h = hashlib.sha256()
    try:
        with open(path, "rb") as fh:
            for b in iter(lambda: fh.read(chunk), b""):
                h.update(b)
    except OSError:
        return None
    return h.hexdigest()


def registry(path=None):
    """[{archive, sha256, source, note}] -- the archives whose bytes were checked
    against what the project published. Empty when the file is absent."""
    try:
        with open(path or REGISTRY, encoding="utf-8") as fh:
            d = json.load(fh)
        return list(d.get("artifacts") or [])
    except (OSError, ValueError):
        return []


def archive_members(archive_path):
    """{member basename: sha256 of its bytes} for a zip, or {} when unreadable.
    Read from the archive itself, so a swapped file on disk cannot match."""
    out = {}
    try:
        with zipfile.ZipFile(archive_path) as z:
            for info in z.infolist():
                if info.is_dir():
                    continue
                h = hashlib.sha256()
                with z.open(info) as fh:
                    for b in iter(lambda: fh.read(1 << 20), b""):
                        h.update(b)
                out[os.path.basename(info.filename).lower()] = h.hexdigest()
    except (OSError, zipfile.BadZipFile, RuntimeError):
        return {}
    return out


def verified_archives(path=None, root=None):
    """The registered archives whose bytes STILL match the digest recorded from
    upstream. Returns [(entry, members)]; an archive that no longer matches is
    left out and reported by `why` in classify()."""
    root = root or HERE
    out = []
    for e in registry(path):
        p = e.get("archive") or ""
        p = p if os.path.isabs(p) else os.path.join(root, p)
        if _sha256(p) != (e.get("sha256") or "").lower():
            continue
        out.append((e, archive_members(p)))
    return out


def _under_our_tree(path, root=None):
    """True when the path is inside this repository OR inside a staged copy of
    it (the runner copies the tree to a temp dir named covenant_one_*)."""
    root = os.path.abspath(root or HERE)
    p = os.path.abspath(path)
    if p.lower().startswith(root.lower() + os.sep):
        return True
    return "covenant_one_" in p or os.sep + "covenant" + os.sep in p.lower()


def classify(path, registry_path=None, root=None):
    """{"verdict", "why", "file_sha256", "archive"} for one flagged path."""
    name = os.path.basename(str(path or "")).lower()
    on_disk = _sha256(path)
    # A217b: a REGISTERED ARCHIVE accounts for itself. It is not a member of
    # itself, so without this the very file whose digest was checked against
    # its publisher came back "unaccounted for".
    for entry in registry(registry_path):
        ap = entry.get("archive") or ""
        ap = ap if os.path.isabs(ap) else os.path.join(root or HERE, ap)
        if os.path.abspath(ap).lower() == os.path.abspath(str(path or "")).lower():
            if on_disk and on_disk == (entry.get("sha256") or "").lower():
                return {"verdict": "ours:verified", "archive": entry.get("archive"), "file_sha256": on_disk,
                        "why": "this IS the registered archive, and it still hashes to what %s published"
                               % (entry.get("source") or "upstream")}
            return {"verdict": "ours:unverified", "archive": entry.get("archive"), "file_sha256": on_disk,
                    "why": "this is the registered archive but its bytes no longer match what %s published"
                           % (entry.get("source") or "upstream")}
    for entry, members in verified_archives(registry_path, root):
        want = members.get(name)
        if not want:
            continue
        if on_disk is None:
            return {"verdict": "ours:verified", "archive": entry.get("archive"), "file_sha256": None,
                    "why": ("a member of %s, which still hashes to what %s published; the file itself is gone "
                            "(the antivirus removed it), so its own bytes could not be re-read"
                            % (entry.get("archive"), entry.get("source") or "upstream"))}
        if on_disk == want:
            return {"verdict": "ours:verified", "archive": entry.get("archive"), "file_sha256": on_disk,
                    "why": ("byte for byte the member of %s, which still hashes to what %s published"
                            % (entry.get("archive"), entry.get("source") or "upstream"))}
        return {"verdict": "ours:unverified", "archive": entry.get("archive"), "file_sha256": on_disk,
                "why": ("a file of this NAME is in %s but the bytes on disk differ from it -- "
                        "that is a swapped file, not a false positive" % entry.get("archive"))}
    if _under_our_tree(path, root):
        return {"verdict": "ours:unverified", "archive": None, "file_sha256": on_disk,
                "why": "inside this tree but belonging to no registered archive -- unaccounted for, not dismissed"}
    return {"verdict": "foreign", "archive": None, "file_sha256": on_disk,
            "why": "outside this tree entirely"}


def judge_detection(row, registry_path=None, root=None):
    """One Defender row -> the same row with a provenance verdict and whether
    it still needs him. A hit is settled ONLY when the file is ours-verified
    AND the verdict was a machine-learning guess (`!ml`)."""
    res = ""
    for r in (row.get("resources"), row.get("resource"), row.get("file")):
        if r:
            res = str(r)
            break
    path = res.split("file:_", 1)[-1].split(";")[0].strip()
    prov = classify(path, registry_path, root)
    threat = str(row.get("threat") or row.get("threat_name") or "")
    heuristic = threat.lower().endswith(ML_SUFFIX)
    settled = prov["verdict"] == "ours:verified" and heuristic
    out = dict(row)
    out["path"] = path
    out["provenance"] = prov
    out["heuristic"] = heuristic
    out["settled"] = settled
    out["says"] = (
        "false positive: %s, and %s is a machine-learning guess, not a signature" % (prov["why"], threat or "the verdict")
        if settled else
        ("NEEDS YOU: %s" % prov["why"]) if prov["verdict"] != "ours:verified" else
        ("NEEDS YOU: the provenance checks out, but %s is a SIGNATURE match, not a heuristic -- "
         "a named piece of malware inside a file we vouch for is the one case that must never be waved through" % threat)
    )
    return out


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="judge a flagged file by its bytes")
    ap.add_argument("path", nargs="?")
    ap.add_argument("--registry", action="store_true", help="show the registered archives and whether they still match")
    a = ap.parse_args(argv)
    if a.registry or not a.path:
        ents = registry()
        good = {e.get("archive") for e, _m in verified_archives()}
        print("%d registered archive(s):" % len(ents))
        for e in ents:
            print("  %-46s %s" % (e.get("archive"), "MATCHES upstream" if e.get("archive") in good else "DOES NOT MATCH"))
            print("      %s" % (e.get("source") or ""))
        return 0
    print(json.dumps(classify(a.path), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
