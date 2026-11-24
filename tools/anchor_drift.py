#!/usr/bin/env python3
"""tools/anchor_drift.py -- A477 (2026-11-23): how far each anchored ledger has moved from ops/RECORD_ANCHORS.json.

WHY. The anchors were written once, on 2026-09-09. covenant_sentinels.MemorySentinel compares a ledger's first 200
lines with them and alerts when they differ, but nothing runs that comparison: the sweep runs only the sentinels'
offline self-test, test_g6 drove the sentinel with an EMPTY anchor dict (until G6.9), and no scheduler calls the live
check (the logs on both machines stop at 2026-09-16). Measured on main 2c1d9a6 the day this was written, all five
anchored ledgers had drifted, and nobody had been told.

WHAT IT DOES. For each ledger in ops/RECORD_ANCHORS.json it hashes the file's first 200 lines exactly as the sentinel
does (bytes split on b"\\n", first 200 pieces, joined with b"\\n") and classifies:
  MATCH          the head still hashes to the anchor;
  INSERTION      the anchored head's 200 lines are all still there, in order, with lines inserted among them;
  REWRITTEN      some anchored lines are gone or changed (kept-in-order count given);
  UNVERIFIABLE   no committed version of the file ever hashed to the anchor, so the anchored text cannot be recovered.
The anchored text is recovered from git: the newest commit on this checkout's history whose version of the file
hashes to the anchor. Without git (a staged copy) the class is not measured, only the hash.

WHAT IT DOES NOT DO. It never rewrites an anchor (that stays the operator's act, `covenant_sentinels.py --anchor`), and
it does not decide whether a drift was right. ops/ANCHOR_DRIFT_ACK.json records each known drift, keyed by the exact
current head hash, with its measured class; test_ra1_record_anchors.py fails on a drift that file does not name.

    python tools/anchor_drift.py            one line per ledger
    python tools/anchor_drift.py --json

Stdlib only. Public domain.
"""
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANCHORS = os.path.join(HERE, "ops", "RECORD_ANCHORS.json")
ACK = os.path.join(HERE, "ops", "ANCHOR_DRIFT_ACK.json")
_NOWIN = 0x08000000 if os.name == "nt" else 0


def prefix(raw, lines=200):
    return b"\n".join(raw.split(b"\n")[:lines])


def sha(b):
    return hashlib.sha256(b).hexdigest()


def kept_in_order(old_lines, new_lines):
    """The length of the run of old_lines, from the first, that appears in new_lines as an ordered subsequence (exact
    bytes). It stops at the first old line that cannot be found, so it decides INSERTION (all kept) but is not a count of
    survivors: see present_anywhere for that."""
    j = 0
    for ln in new_lines:
        if j < len(old_lines) and ln == old_lines[j]:
            j += 1
    return j


def _git(root, *args):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    r = subprocess.run(["git", "-C", root] + list(args), capture_output=True, env=env, timeout=120, creationflags=_NOWIN)
    return r.returncode, r.stdout


def anchored_text(root, rel, want, revs=None):
    """(commit, raw bytes) of the newest commit whose version of REL hashes to WANT; (None, None) if none or no git."""
    if revs is None:
        rc, out = _git(root, "log", "--format=%H", "--", rel)
        if rc != 0:
            return None, None
        revs = out.decode().split()
    for r in revs:
        rc, raw = _git(root, "show", "%s:%s" % (r, rel))
        if rc == 0 and sha(prefix(raw)) == want:
            return r, raw
    return None, None


def measure(root=HERE, anchors=None, classify=True, hint=None):
    """{ledger: {state, current_prefix_sha256, anchored_prefix_sha256, anchored_from_commit, kept_in_order, lines}}.
    HINT {ledger: commit} is tried first (the ack file names the commit it measured from), so a sweep does not walk
    hundreds of commits; a hint that no longer hashes to the anchor falls back to the walk."""
    if anchors is None:
        with open(os.path.join(root, "ops", "RECORD_ANCHORS.json"), encoding="utf-8") as fh:
            anchors = json.load(fh)
    n = int(anchors.get("prefix_lines", 200))
    out = {}
    for rel, base in sorted((anchors.get("ledgers") or {}).items()):
        p = os.path.join(root, rel)
        if not os.path.isfile(p):
            out[rel] = {"state": "MISSING"}
            continue
        with open(p, "rb") as fh:
            raw = fh.read()
        cur = sha(prefix(raw, n))
        row = {"current_prefix_sha256": cur, "anchored_prefix_sha256": base.get("prefix_sha256"),
               "lines": raw.count(b"\n")}
        if cur == base.get("prefix_sha256"):
            row["state"] = "MATCH"
        elif not classify:
            row["state"] = "DRIFTED (class not measured)"
        else:
            commit, old = None, None
            h = (hint or {}).get(rel)
            if h:
                commit, old = anchored_text(root, rel, base.get("prefix_sha256"), revs=[h])
            if commit is None:
                commit, old = anchored_text(root, rel, base.get("prefix_sha256"))
            if commit is None:
                rc, _ = _git(root, "rev-parse", "HEAD")
                row["state"] = "UNVERIFIABLE" if rc == 0 else "DRIFTED (no git here)"
            else:
                old_lines = prefix(old, n).split(b"\n")
                new_lines = raw.split(b"\n")
                k = kept_in_order(old_lines, new_lines)
                have = set(new_lines)
                row.update(anchored_from_commit=commit, kept_in_order=k, anchored_lines=len(old_lines),
                           present_anywhere=sum(1 for x in old_lines if x in have),
                           state="INSERTION" if k == len(old_lines) else "REWRITTEN")
        out[rel] = row
    return out


def load_ack(path=ACK):
    try:
        with open(path, encoding="utf-8") as fh:
            return (json.load(fh) or {}).get("ledgers") or {}
    except (OSError, ValueError):
        return {}


# A ledger whose head CANNOT hold an anchor, by how it is written (measured 2026-11-23: ops/SELF_EVAL.md puts each new
# round at the top and drops old ones). Its drift row may say head_anchor_cannot_hold; no other ledger may. Moved here
# from test_ra1 in A478 so the nightly's live check and RA1 read one list.
PREPENDING = {"ops/SELF_EVAL.md"}


def split_alerts(alerts, ack):
    """(new, known) for the live sentinel's alert strings (A478). KNOWN is only a head-anchor alert for a ledger in
    PREPENDING whose drift row says head_anchor_cannot_hold; every other alert is new. It never hides an alert: the
    caller prints both lists."""
    new, known = [], []
    for a in alerts:
        rel = a.split(":", 1)[0].strip()
        row = ack.get(rel) or {}
        if rel in PREPENDING and row.get("head_anchor_cannot_hold") and "first 200 lines" in a:
            known.append(a)
        else:
            new.append(a)
    return new, known


if __name__ == "__main__":
    ack = load_ack()
    m = measure(hint={k: v.get("anchored_from_commit") for k, v in ack.items()})
    if "--json" in sys.argv:
        print(json.dumps(m, indent=1, sort_keys=True))
    else:
        for rel, r in m.items():
            extra = (" %d/%d anchored lines still present (in order from the first: %d), anchored text from %s"
                     % (r["present_anywhere"], r["anchored_lines"], r["kept_in_order"], r["anchored_from_commit"][:9])
                     if "kept_in_order" in r else "")
            a = ack.get(rel)
            acked = (" | acknowledged (%s)" % a.get("class")) if a and a.get("current_prefix_sha256") == r.get("current_prefix_sha256") else ""
            print("%-22s %-12s%s%s" % (rel, r["state"], extra, acked))
