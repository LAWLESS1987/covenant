#!/usr/bin/env python3
"""tools/prune_artifacts.py -- keep only the N newest build artifacts.

ASKED 2026-09-27: "yea we do not need old apks only keep the 2 most recent at
all times", after the phone build had been red for five days.

WHY IT WENT RED, measured rather than guessed. The build itself compiles. It
dies at the last step:

    step   : Run actions/upload-artifact@v4
    reason : Failed to CreateArtifact: Artifact storage quota has been hit.
             Unable to upload any new artifacts

and the store behind it, read the same day:

    LAWLESS1987/covenant-phone   120 artifacts, 1,331 MB
    LAWLESS1987/covenant        2389 artifacts, small (1.4 MB per 100)

Every APK the phone has ever been built from was still sitting there. Nothing
expired them, so the quota filled, so no new APK could be uploaded, so the phone
stayed on an old version, so the mesh reported two source digests. One full disk
presenting as two unrelated red alerts.

THE AUTO-SYNC WAS NEVER BROKEN. The highway dispatches a rebuild on its own --
that is why the failing runs are `workflow_dispatch` -- and its own alert text
already said "the highway's rebuild requests change nothing until this is
fixed". It was dispatching into a full disk since 2026-09-22 and saying so fifty
times a day.

WHAT THIS DELETES AND WHAT IT WILL NOT
  * Sorted by created_at, NEWEST FIRST. The newest `--keep` are kept; the rest
    are deleted. Default keep is 2, his number.
  * DRY RUN IS THE DEFAULT. Deleting an artifact is not reversible -- the bytes
    are gone and the run that made them cannot be re-uploaded -- so it takes an
    explicit --apply.
  * It REFUSES to delete anything if it cannot read a created_at for every
    artifact, because "newest" would then be a guess and the wrong two would be
    kept. A pruner that guesses which build to keep is worse than a full disk.
  * It never touches a workflow, a run, a release or a tag. Artifacts only.

USE
  python tools/prune_artifacts.py                      dry run, covenant-phone
  python tools/prune_artifacts.py --apply              really delete
  python tools/prune_artifacts.py --repo X --keep 3
  python tools/prune_artifacts.py --all --apply        both repos
LICENCE: Apache-2.0.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PHONE = "LAWLESS1987/covenant-phone"
CORE = "LAWLESS1987/covenant"
API = "https://api.github.com"


def _token():
    """The operator's token, by the rules covenant_github_judge already sets.

    A21 is why this is not just `git credential fill`: on a cloned node that
    would spend a stranger's credential on the owner's repo unasked. Opting in
    is COVENANT_GITHUB_JUDGE=1, or set GITHUB_TOKEN directly."""
    try:
        import covenant_github_judge as g
        return g.token() or ""
    except Exception:                                             # noqa: BLE001
        return os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""


def _headers(tok):
    return {"Authorization": "Bearer " + tok,
            "Accept": "application/vnd.github+json",
            "User-Agent": "covenant-prune-artifacts"}


def _api(path, tok, method="GET"):
    req = urllib.request.Request(API + path, headers=_headers(tok), method=method)
    with urllib.request.urlopen(req, timeout=40) as r:
        body = r.read()
        return json.loads(body) if body else {}


def artifacts(repo, tok, say=print):
    """Every live artifact, paginated. total_count exceeds one page routinely."""
    out, page = [], 1
    while True:
        d = _api("/repos/%s/actions/artifacts?per_page=100&page=%d" % (repo, page), tok)
        got = d.get("artifacts") or []
        out.extend(a for a in got if not a.get("expired"))
        if len(got) < 100 or page >= 20:
            break
        page += 1
    say("%s: %d live artifact(s), %.1f MB"
        % (repo, len(out), sum(a.get("size_in_bytes", 0) for a in out) / 1e6))
    return out


def prune(repo, keep=2, apply=False, tok=None, flat=False, say=print):
    tok = tok or _token()
    if not tok:
        say("no token -- set GITHUB_TOKEN, or COVENANT_GITHUB_JUDGE=1 to use the "
            "credential store (A21: opting in is deliberate)")
        return 2
    arts = artifacts(repo, tok, say=say)
    if not arts:
        return 0
    if any(not a.get("created_at") for a in arts):
        say("REFUSING: %d artifact(s) carry no created_at, so 'the newest %d' "
            "cannot be determined and the wrong ones could be kept"
            % (sum(1 for a in arts if not a.get("created_at")), keep))
        return 1
    arts.sort(key=lambda a: a["created_at"], reverse=True)
    if flat:
        keepers, doomed = arts[:max(0, int(keep))], arts[max(0, int(keep)):]
    else:
        # PER NAME, and this is the difference between a rollback and none.
        #
        # His words were "only keep the 2 most recent" APKs. A flat top-2 over
        # everything does NOT do that: measured on the real store, the two
        # newest artifacts are one APK and one `android-verify-logs` bundle, so
        # a flat rule keeps a single APK and the phone has nothing to fall back
        # to. Grouping by artifact name keeps 2 of each kind, which is what the
        # sentence means and what the situation needs -- the phone is on 0.1.674
        # and cannot take 0.1.679, so the previous good APK is the only way back
        # if the next one is wrong.
        seen, keepers, doomed = {}, [], []
        for a in arts:
            n = a.get("name") or "?"
            seen[n] = seen.get(n, 0) + 1
            (keepers if seen[n] <= max(0, int(keep)) else doomed).append(a)
    say("keeping %d newest:" % len(keepers))
    for a in keepers:
        say("   KEEP  %-28s %7.1f MB  %s"
            % (a.get("name", "?")[:28], a.get("size_in_bytes", 0) / 1e6, a["created_at"]))
    freed = sum(a.get("size_in_bytes", 0) for a in doomed)
    say("%s %d older artifact(s), %.1f MB"
        % ("DELETING" if apply else "would delete", len(doomed), freed / 1e6))
    if not apply:
        say("dry run -- pass --apply to really delete")
        return 0
    gone = 0
    for a in doomed:
        try:
            _api("/repos/%s/actions/artifacts/%s" % (repo, a["id"]), tok, method="DELETE")
            gone += 1
        except urllib.error.HTTPError as e:
            say("   could not delete %s (HTTP %s)" % (a.get("id"), e.code))
        except Exception as e:                                    # noqa: BLE001
            say("   could not delete %s (%s)" % (a.get("id"), type(e).__name__))
    say("deleted %d of %d, about %.1f MB freed" % (gone, len(doomed), freed / 1e6))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repo", default=PHONE)
    ap.add_argument("--keep", type=int, default=2, help="his number: 2")
    ap.add_argument("--all", action="store_true", help="both repos")
    ap.add_argument("--flat", action="store_true",
                    help="newest N overall instead of N per artifact name")
    ap.add_argument("--apply", action="store_true", help="really delete (default: dry run)")
    a = ap.parse_args()
    repos = [PHONE, CORE] if a.all else [a.repo]
    rc = 0
    for r in repos:
        rc = prune(r, keep=a.keep, apply=a.apply, flat=a.flat) or rc
        print()
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
