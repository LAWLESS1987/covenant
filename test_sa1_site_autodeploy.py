#!/usr/bin/env python3
"""test_sa1_site_autodeploy.py -- SA1. The laptop's site auto-deploy refuses at every step it should.

Every step of tools/site_autodeploy.one_pass is driven both ways with stand-ins (no network, no deploy):
  SA1a  feed unreachable, empty, or without site_deploy_due -> nothing done, never deploys blind
  SA1b  nothing due -> nothing done
  SA1c  GitHub main (read here) differs from the feed's target -> refused as a half-sync; equal -> proceeds
  SA1d  regeneration fails -> refused
  SA1e  the opsec full-history scan hits in ANY regenerated .git -> refused, and the deploy is never called
  SA1f  the site's tests fail -> refused
  SA1g  all clear -> deploys once, then verifies the site's main equals GitHub's for every due repo
  SA1h  --dry-run stops after the checks: it never regenerates, scans or deploys
  SA1i  the real opsec scan, on a throwaway repo carrying his LAN IP, reports NOT clean; a clean repo reads clean
Offline except SA1i, which uses only local git and his private identifier sources.
"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "tools"))
import site_autodeploy as SA          # noqa: E402

_results = []


def check(label, cond, detail=""):
    _results.append(bool(cond))
    print(f"{'ok   ' if cond else 'FAIL '} {label}{('  -- ' + str(detail)[:300]) if detail and not cond else ''}")


FULL = "a" * 40


class Rig:
    """Stand-ins that record what the pass called."""
    def __init__(self, feed=None, gh=FULL, site=FULL, regen_ok=True, scan_hit=None, tests_ok=True, deploy_ok=True):
        self.calls = []
        self.feed, self.gh_v, self.site_v = feed, gh, site
        self.regen_ok, self.scan_hit, self.tests_ok, self.deploy_ok = regen_ok, scan_hit, tests_ok, deploy_ok
        self.dir = tempfile.mkdtemp(prefix="sa1_")
        for n in ("covenant.git", "threefold-memory.git", "covenant"):
            os.makedirs(os.path.join(self.dir, n))

    def kwargs(self):
        return dict(feed_reader=lambda: self.feed, gh=self._gh, site=self._site, regen=self._regen, scan=self._scan,
                    tests=self._tests, do_deploy=self._deploy, repos_dir=self.dir)

    def _gh(self, n):
        self.calls.append(("gh", n)); return self.gh_v

    def _site(self, n):
        self.calls.append(("site", n)); return self.site_v

    def _regen(self):
        self.calls.append(("regen",)); return self.regen_ok, "regen output"

    def _scan(self, d, remote=None):
        self.calls.append(("scan", os.path.basename(d)))
        self.remotes = getattr(self, "remotes", []) + [remote]
        return (os.path.basename(d) != self.scan_hit), "scan detail"

    def _tests(self):
        self.calls.append(("tests",)); return self.tests_ok, "tests output"

    def _deploy(self):
        self.calls.append(("deploy",)); return self.deploy_ok, "Current Version ID: 1234"

    def did(self, step):
        return any(c[0] == step for c in self.calls)


def passes(rig, **kw):
    """One pass; a crash is an answer too, so each check reads it under its own name."""
    try:
        return SA.one_pass(**kw, **rig.kwargs())
    except Exception as e:                                       # noqa: BLE001
        return {"result": "CRASHED %s: %s" % (type(e).__name__, e)}


def feed(due, target=FULL):
    return {"status": "ok", "site_deploy_due": due, "repos": {n: {"target": target} for n in due}}


def main():
    for label, f in (("unreachable", None), ("empty {}", {}), ("no site_deploy_due", {"status": "ok", "repos": {}}),
                     ("still starting", {"status": "starting", "checked": None, "repos": {}, "site_deploy_due": ["covenant"]})):
        r = Rig(feed=f)
        rec = passes(r)
        check("SA1a feed %s -> feed_not_ready, nothing called" % label,
              rec["result"] == "feed_not_ready" and not r.calls, (rec, r.calls))
    r = Rig(feed=feed([]))
    rec = passes(r)
    check("SA1b nothing due -> nothing_due, nothing regenerated or deployed",
          rec["result"] == "nothing_due" and not r.did("regen") and not r.did("deploy"), rec)
    r = Rig(feed=feed(["covenant"], target="b" * 40))
    rec = passes(r)
    check("SA1c GitHub main != the feed's target -> refused_half_sync, never regenerated",
          rec["result"] == "refused_half_sync" and not r.did("regen") and not r.did("deploy"), rec)
    r = Rig(feed=feed(["covenant"], target=FULL[:7]))
    rec = passes(r)
    check("SA1c ...a short target that GitHub's full ID starts with -> proceeds", rec["result"] == "deployed", rec)
    r = Rig(feed=feed(["covenant"], target=FULL[:3]))
    rec = passes(r)
    check("SA1c ...a target shorter than 7 (a true 3-character prefix) never matches -> refused", rec["result"] == "refused_half_sync",
          rec)
    r = Rig(feed=feed(["covenant"]), regen_ok=False)
    rec = passes(r)
    check("SA1d regeneration fails -> refused_regenerate, never deployed",
          rec["result"] == "refused_regenerate" and not r.did("deploy"), rec)
    r = Rig(feed=feed(["covenant"]), scan_hit="threefold-memory.git")
    rec = passes(r)
    check("SA1e an opsec hit in ANY regenerated .git (not only the due repo) -> refused_opsec, never deployed",
          rec["result"] == "refused_opsec" and "threefold-memory.git" in rec.get("why", "") and not r.did("deploy"),
          rec)
    scanned = {c[1] for c in r.calls if c[0] == "scan"}
    check("SA1e ...every .git is scanned, the working-tree folders are not mistaken for repos",
          "covenant.git" in scanned and "threefold-memory.git" in scanned and "covenant" not in scanned, scanned)
    check("SA1e ...each scan is of what the live site does NOT already hold (its own copy is the remote)",
          sorted(r.remotes) == sorted("%s/%s" % (SA.SITE_ORIGIN, n) for n in ("covenant.git", "threefold-memory.git")),
          r.remotes)
    r = Rig(feed=feed(["covenant"]), tests_ok=False)
    rec = passes(r)
    check("SA1f the site's tests fail -> refused_tests, never deployed",
          rec["result"] == "refused_tests" and not r.did("deploy"), rec)
    r = Rig(feed=feed(["covenant", "threefold-memory"]))
    rec = passes(r)
    deploys = [c for c in r.calls if c[0] == "deploy"]
    check("SA1g all clear -> deployed once, and the site's main verified against GitHub's for every due repo",
          rec["result"] == "deployed" and len(deploys) == 1
          and {c[1] for c in r.calls if c[0] == "site"} == {"covenant", "threefold-memory"}, (rec, r.calls))
    r = Rig(feed=feed(["covenant"]), site="c" * 40)
    rec = passes(r)
    check("SA1g ...a site still behind after the deploy is reported, not called a success",
          rec["result"] == "deployed_but_behind" and rec.get("behind") == ["covenant"], rec)
    r = Rig(feed=feed(["covenant"]))
    rec = passes(r, dry_run=True)
    check("SA1h --dry-run checks the feed and GitHub, then stops: no regenerate, scan or deploy",
          rec["result"] == "dry_run_ok" and not r.did("regen") and not r.did("scan") and not r.did("deploy"), rec)

    # SA1i -- the real scan the job uses, both ways, on throwaway repos (never pushed anywhere).
    try:
        sys.path.insert(0, os.path.join(HERE, "tools"))
        import opsec_scan as O
        lan = [v for c, v in O.gather(O.ROOT) if c == "lan-ip"]
    except Exception as e:                                       # noqa: BLE001
        lan, err = [], e
    if not lan:
        check("SA1i (no lan-ip identifier in his private sources here -- the real-scan check is NOT MEASURED)", True)
    else:
        base = tempfile.mkdtemp(prefix="sa1_scan_")
        for kind, body in (("dirty", "probe: %s\n" % lan[0]), ("clean", "probe: nothing of his\n")):
            work = os.path.join(base, kind)
            subprocess.run(["git", "init", "-q", work], check=True)
            with open(os.path.join(work, "p.txt"), "w") as fh:
                fh.write(body)
            subprocess.run(["git", "-C", work, "add", "p.txt"], check=True)
            subprocess.run(["git", "-C", work, "-c", "user.name=sa1", "-c", "user.email=sa1@example.invalid",
                            "commit", "-q", "-m", "probe"], check=True)
            clean, detail = SA.opsec_full_history(os.path.join(work, ".git"))
            want = kind == "clean"
            check("SA1i the real full-history scan reads a %s repo as %s" % (kind, "clean" if want else "NOT clean"),
                  clean is want, detail)

    passed, total = sum(_results), len(_results)
    print(f"\nSA1: {passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
