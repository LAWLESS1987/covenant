#!/usr/bin/env python3
"""PB1 -- the two highway signals about the phone's build measure what they name (2026-09-26, A231).

Found while answering "how do we get all orbs green?". The PC page's Highway orb was red on
phone_build_behind_core for commits the phone never runs, and the remedy that collects new builds
(fetch_build) had been quarantined since 2026-09-23 for doing its job:

  PB1a  covenant_app_update.fetch, finding nothing newer ("already have build ..."), records that it LOOKED
        (`checked`); before, only a download moved the record, so build_stale_on_pc stayed PRESENT right
        after a look, fetch_build was graded "did not fix" twice, and it was quarantined.
  PB1b  build_stale_on_pc counts the newest of `fetched` and `checked`; an old download with a recent
        look is ABSENT, an old download with no recent look is PRESENT (driven both ways).
  PB1c  phone_build_behind_core, with covenant-phone's python_sources.txt and the build's core readable,
        asks exactly "has a file the APK ships changed since the core this build carries": a docs-only
        commit after it is ABSENT, a commit to a shipped file is PRESENT.
  PB1d  without the shipped-file list it falls back to the old any-commit comparison and says so.

Nothing here touches the network, the real ops/app record or the real highway ledger.

    python test_pb1_phone_build_signals.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_app_update as AU  # noqa: E402
import covenant_highway as H  # noqa: E402

PASSED, FAILED, NOT_RUN = [0], [], []
ENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.org", GIT_COMMITTER_NAME="t",
           GIT_COMMITTER_EMAIL="t@example.org")


def check(label, ok, detail=""):
    print("  %-78s %s" % (label[:78], "ok" if ok else "FAIL  %s" % str(detail)[:300]))
    if ok:
        PASSED[0] += 1
    else:
        FAILED.append(label)


def stamp(hours_ago):
    return time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(time.time() - hours_ago * 3600))


def main():
    tmp = tempfile.mkdtemp(prefix="pb1_")
    real = (AU.LATEST, AU.DIR, AU.latest, AU._get_json, AU.is_new_build)
    try:
        # ---- PB1a: a look that finds nothing newer is recorded
        AU.DIR, AU.LATEST = tmp, os.path.join(tmp, "latest.json")
        with open(os.path.join(tmp, "covenant-node-aaaaaaa-r1.apk"), "wb") as fh:
            fh.write(b"apk")
        rec = {"sha": "a" * 40, "sha7": "aaaaaaa", "run_id": 1, "built": "2026-09-22T22:03:15Z", "core": "9ebb8fe",
               "fetched": stamp(80), "file": "covenant-node-aaaaaaa-r1.apk"}
        with open(AU.LATEST, "w", encoding="utf-8") as fh:
            json.dump(rec, fh)
        import covenant_github_judge as gh
        real_tok, real_allow = gh.token, gh.allow_credential_store
        gh.token, gh.allow_credential_store = (lambda *a, **k: "t0ken"), (lambda *a, **k: None)
        AU._get_json = lambda path, tok: ({"workflow_runs": [{"id": 1, "head_sha": "a" * 40}]} if "/runs?" in path
                                          else {"artifacts": [{"name": AU.ARTIFACT, "expired": False}]})
        AU.is_new_build = lambda cur, run: False
        said = []
        try:
            out = AU.fetch(say=said.append)
        finally:
            gh.token, gh.allow_credential_store = real_tok, real_allow
        with open(AU.LATEST, encoding="utf-8") as fh:
            on_disk = json.load(fh)
        check("PB1a a look that finds nothing newer stamps `checked` on the record (and says 'already have')",
              bool(on_disk.get("checked")) and on_disk.get("fetched") == rec["fetched"] and out and out.get("checked")
              and any("already have" in s for s in said), (said, on_disk))

        # ---- PB1e (2026-09-28, his words: "3 with the same mechanism of last 2"): the build now hands its APK
        # to a release of its own run; a green run with no artifact is fetched from that release as the raw
        # APK, and a PRERELEASE (a build the emulator has not passed, or a branch build) is not taken.
        real_dl, real_ver = AU._download, AU.apk_version
        gh.token, gh.allow_credential_store = (lambda *a, **k: "t0ken"), (lambda *a, **k: None)
        AU.is_new_build = lambda cur, run: True
        AU.apk_version = lambda p: "1.0+abcdef1"
        AU._download = lambda url, tok, accept=None: (b"RAWAPK" if accept == "application/octet-stream" and url.endswith("/asset/1") else b"")
        got = {}
        try:
            for pre in (False, True):
                def gj(path, tok, pre=pre):
                    if "/runs?" in path:
                        return {"workflow_runs": [{"id": 7, "head_sha": "b" * 40, "html_url": "u", "updated_at": "x"}]}
                    if "/artifacts" in path:
                        return {"artifacts": []}
                    if path.endswith("/releases/tags/build-r7"):
                        return {"prerelease": pre, "assets": [{"name": AU.RELEASE_ASSET, "url": "https://api/asset/1"}]}
                    raise AssertionError(path)
                AU._get_json = gj
                said = []
                got[pre] = (AU.fetch(say=said.append), said)
        finally:
            gh.token, gh.allow_credential_store = real_tok, real_allow
            AU._download, AU.apk_version = real_dl, real_ver
        ok_rel = got[False][0]
        body = open(os.path.join(tmp, ok_rel["file"]), "rb").read() if ok_rel else b""
        check("PB1e a green run with no artifact is fetched from its own release, as the raw APK",
              bool(ok_rel) and ok_rel.get("run_id") == 7 and body == b"RAWAPK", got[False])
        check("PB1e a prerelease is never taken: a build the emulator has not passed does not reach the phone",
              got[True][0] is None and any("no green build" in s for s in got[True][1]), got[True])

        # ---- PB1b: the staleness detector counts the look
        AU.latest = lambda: dict(rec, checked=stamp(1))
        r_look = H.detect_build_stale_on_pc()
        AU.latest = lambda: dict(rec)
        r_none = H.detect_build_stale_on_pc()
        check("PB1b an 80-hour-old download with a look 1 hour ago is ABSENT; with no recent look it is PRESENT",
              r_look["state"] == H.ABSENT and r_none["state"] == H.PRESENT, (r_look, r_none))

        # ---- PB1c/d: behind the core means behind in what the APK ships
        if not shutil.which("git"):
            NOT_RUN.append("PB1c-d: no git on this machine")
        else:
            repo = os.path.join(tmp, "repo")
            subprocess.run(["git", "init", "-q", repo], env=ENV, capture_output=True)

            def commit(name, text):
                with open(os.path.join(repo, name), "w") as fh:
                    fh.write(text)
                subprocess.run(["git", "-C", repo, "add", "-A"], env=ENV, capture_output=True)
                subprocess.run(["git", "-C", repo, "commit", "-q", "-m", name], env=ENV, capture_output=True)
                return subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
            base = commit("core.py", "v1\n")
            phone = os.path.join(tmp, "phone")
            os.makedirs(phone)
            with open(os.path.join(phone, "python_sources.txt"), "w") as fh:
                fh.write("# the allowlist\ncore.py\n\n")
            os.environ["COVENANT_PHONE_REPO"] = phone
            real_here = H.HERE
            H.HERE = repo
            AU.latest = lambda: dict(rec, core=base[:7], built=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 3600)))
            try:
                commit("notes.md", "docs only\n")
                r_docs = H.detect_phone_build_behind_core()
                commit("core.py", "v2\n")
                r_core = H.detect_phone_build_behind_core()
                check("PB1c a docs-only commit after the build's core is ABSENT; a commit to a shipped file is PRESENT",
                      r_docs["state"] == H.ABSENT and r_core["state"] == H.PRESENT
                      and r_core["measured"].get("basis") == "files the APK ships"
                      and r_core["measured"].get("shipped_commits_since") == 1, (r_docs, r_core))
                os.environ["COVENANT_PHONE_REPO"] = os.path.join(tmp, "nowhere")
                real_default = H._phone_shipped_paths
                H._phone_shipped_paths = lambda: None
                r_fb = H.detect_phone_build_behind_core()
                H._phone_shipped_paths = real_default
                check("PB1d with no shipped-file list it falls back to the any-commit comparison, and says so",
                      r_fb["state"] == H.PRESENT and "any commit" in str(r_fb["measured"].get("basis")), r_fb)
            finally:
                H.HERE = real_here
                os.environ.pop("COVENANT_PHONE_REPO", None)
    finally:
        AU.LATEST, AU.DIR, AU.latest, AU._get_json, AU.is_new_build = real
    for n in NOT_RUN:
        print("  NOT RUN  %s" % n)
    print("PB1: %d/%d passed%s" % (PASSED[0], PASSED[0] + len(FAILED),
                                   (" (%d NOT RUN, not counted)" % len(NOT_RUN)) if NOT_RUN else ""))
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
