#!/usr/bin/env python3
"""secret_egress_guard.py -- stop YOUR secrets from being pushed to a git remote, before the push leaves.

WHAT IT DOES. You declare the secret values that must never reach a remote (API keys, tokens, internal
hostnames, a customer's name -- any literal string). It scans, and as a pre-push hook it refuses a push that
would publish any of them. It checks every OBJECT the push would send that the remote does not already hold --
blob contents, commit and tag messages, author/committer fields, tree entry names, file paths -- each read in
every encoding a tool might have written (UTF-8, cp1252, UTF-16 both ways and offsets, UTF-32) and in its
"plain" reading (JSON \\u escapes, HTML entities, NFKC, curly quotes). It FAILS CLOSED: a push line it cannot
parse, or objects git cannot list or read, refuse the push rather than being read as "nothing added".

WHY THIS FORM. A value added and removed within one push is still public, so diff-based scanners miss it; this
walks objects, not diffs. The scanning core is covenant's tools/opsec_scan.py, hardened in an adversarial review
that reproduced eight distinct ways past a `git log -p` scanner (tag messages, non-branch refs, merges, UTF-16,
binary files, form feeds/bare CRs, '++' lines, file names). This wrapper feeds that core YOUR secrets instead of
covenant's private sources, so you inherit the rigor without the covenant-specific bits.

DECLARE SECRETS (any combination):
  --config PATH     JSON: {"secrets": [{"label": "stripe-key", "value": "sk_live_..."}, ...]}
  --value LABEL=VAL  one secret (repeatable)
  --from-env NAME    read the value of environment variable NAME (its NAME becomes the label); repeatable.
                     Reads the value, never writes it anywhere; output masks every secret (first 4 + last 2 chars).

RUN:
  python secret_egress_guard.py --scan [--config ...]          scan tracked files as they are on disk
  python secret_egress_guard.py --pre-push [--config ...]      git pre-push hook (reads refs on stdin)

Install as a hook (bash .git/hooks/pre-push):
  #!/bin/sh
  exec python /path/to/secret_egress_guard.py --pre-push --config /path/to/secrets.json "$@"

Exit: 0 = nothing of yours would be published (or nothing to check); 1 = a secret found, or the push could not
be fully read (refused); 2 = usage / the scanning core could not be imported.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))           # .../tools, where opsec_scan.py lives
try:
    import opsec_scan as O                            # the hardened object-walk + multi-encoding scanner
except ImportError as e:                              # pragma: no cover - import guard
    sys.exit("secret_egress_guard: cannot import the scanning core (tools/opsec_scan.py): %s" % e)


def git_root(start=None):
    ok, out = O._run_ok(["git", "-C", start or os.getcwd(), "rev-parse", "--show-toplevel"])
    return out.strip() if ok and out.strip() else (start or os.getcwd())


def load_secrets(args):
    """[(label, value)] from --config, --value, --from-env. Blank/missing values are dropped with a note."""
    secrets, dropped = [], []
    if args.config:
        with open(args.config, encoding="utf-8") as fh:
            for e in json.load(fh).get("secrets", []):
                if e.get("value"):
                    secrets.append((str(e.get("label") or "secret"), str(e["value"])))
                else:
                    dropped.append(str(e.get("label") or "secret"))
    for pair in args.value or []:
        label, _, val = pair.partition("=")
        (secrets if val else dropped).append((label, val) if val else label)
    for name in args.from_env or []:
        val = os.environ.get(name)
        (secrets.append((name, val)) if val else dropped.append(name))
    # de-dupe by value; longest first so a longer secret masks before a shorter substring of it
    seen, out = set(), []
    for label, val in secrets:
        if val and val not in seen:
            seen.add(val)
            out.append((label, val))
    return sorted(out, key=lambda t: -len(t[1])), dropped


def build_pats(secrets, ignore_case):
    """[(label, value, compiled)] -- an exact literal match for each secret. Case-sensitive by default (keys are);
    --ignore-case for values that travel case-folded (lower-cased hex, hostnames)."""
    flags = re.I if ignore_case else 0
    return [(label, val, re.compile(re.escape(val), flags)) for label, val in secrets]


def scan_tracked(root, pats):
    """{path: [(line, label, masked)]} over tracked files, read as bytes through the hardened scanner."""
    report = {}
    for f in O.tracked(root):
        try:
            with open(os.path.join(root, f), "rb") as fh:
                data = fh.read()
        except OSError:
            continue
        hits = []
        for _sha, where, label, masked in O.scan_objects([(O.ZERO, "blob", f, data)], pats):
            ln = re.search(r":(\d+)$", where)
            hits.append((int(ln.group(1)) if ln else 0, label, masked))
        if hits:
            report[f] = hits
    return report


def pre_push(root, pats, stdin_text, remote=None, remote_name=None, say=print):
    """0 to allow, 1 to refuse. Fails closed on unparsed lines or unreadable objects."""
    refs, unparsed = O.parse_push_lines(stdin_text)
    tips, how = O.published(root, remote, remote_name) if refs else ([], "")
    hits, unread, commits, done = [], [], set(), set()
    for parts in refs:
        objs = O.outgoing(root, [parts[1]], sorted(set(tips) | set(O.present(root, [parts[3]]))))
        if objs is None:
            unread.append(parts[2])
            continue
        objs = [o for o in objs if o[0] not in done]
        done.update(o[0] for o in objs)
        commits.update(s for s, kind, _p, _d in objs if kind == "commit")
        hits += O.scan_objects(objs, pats)
    if not hits and not unread and not unparsed:
        say("secret-egress: %d secret(s) checked against every object %d outgoing commit(s) bring (%s); none found"
            % (len(pats), len(commits), how))
        return 0
    if unparsed:
        say("secret-egress: REFUSED -- could not read git's list of what is being pushed: %s"
            % "; ".join(u[:80] for u in unparsed[:3]))
    if unread:
        say("secret-egress: REFUSED -- could not read the outgoing objects of %s (git failed/timed out)"
            % ", ".join(unread))
    if hits:
        say("secret-egress: REFUSED -- the push would publish %d secret occurrence(s) (%s):" % (len(hits), how))
    for sha, where, label, masked in hits[:30]:
        say("  %s %s  %s %s" % (sha, where, label, masked))
    say("Nothing was lost: the commit is still local. Remove the secret, amend or add a commit, and push again.")
    return 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="Refuse a git push that would publish your declared secrets.")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--scan", action="store_true")
    mode.add_argument("--pre-push", dest="pre_push", action="store_true")
    ap.add_argument("--config"); ap.add_argument("--value", action="append"); ap.add_argument("--from-env", action="append")
    ap.add_argument("--ignore-case", action="store_true")
    ap.add_argument("--root")
    a, rest = ap.parse_known_args(argv)

    root = a.root or git_root()
    secrets, dropped = load_secrets(a)
    for d in dropped:
        print("secret-egress: note -- '%s' had no value, skipped" % d)
    if not secrets:
        print("secret-egress: NOT MEASURED -- no secrets declared (use --config/--value/--from-env); nothing to check")
        return 0
    pats = build_pats(secrets, a.ignore_case)
    print("secret-egress: %d secret(s) declared: %s" % (len(pats), ", ".join(O.mask(v) for _l, v in secrets)))

    if a.pre_push:
        # git passes the hook: <remote name> <remote url>, then refs on stdin.
        raw = sys.stdin.buffer.read() if hasattr(sys.stdin, "buffer") else sys.stdin.read().encode("utf-8")
        text = raw.decode("utf-8", "surrogateescape")
        remote_name = rest[0] if rest else None
        remote = rest[1] if len(rest) > 1 else remote_name
        return pre_push(root, pats, text, remote=remote, remote_name=remote_name)

    report = scan_tracked(root, pats)
    for f, hits in sorted(report.items()):
        labels = sorted({l for _n, l, _m in hits})
        print("  %-48s %3d line(s)  %s  e.g. line %d" % (f, len(hits), ",".join(labels), hits[0][0]))
    print("secret-egress: %d tracked file(s) carry a declared secret" % len(report))
    return 1 if report else 0


if __name__ == "__main__":
    sys.exit(main())
