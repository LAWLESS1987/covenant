#!/usr/bin/env python3
"""PC2 (2026-10-03): the deploy pin moves with the core -- only after the core's judges pass.

M53 broke six times by hand (tools/pin_core.py says when). These checks drive the tool on TEMP
copies of verify_deploy.py and a core, never the real ones, with the four judging suites stubbed
both ways, plus one read of the real tree: the pin on disk matches the core on disk.

PC2.9-PC2.25 (2026-10-06, A315; PC2.25 2026-10-08): the other four pins, moved by tools/pin_deploy.py. In-process on
temp copies with git and the judges stubbed (PC2.11-PC2.20), and END TO END (PC2.22-PC2.25): the
tracked hook installed in a scratch repository, a run_all_tests.sh edit committed through it with
K1/K2 stubbed passing and then failing, then a merge of two such edits. Every git call aimed at a scratch repository drops git's
repository-pinning variables first: this suite runs inside the real pre-commit hook (A255).

    python test_pc2_pin_core.py
"""
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "tools"))
import pin_core as P  # noqa: E402
import pin_deploy as D  # noqa: E402

ok = []


def check(name, cond, note=""):
    ok.append(bool(cond))
    print("  %-4s %s%s" % ("ok" if cond else "FAIL", name, "" if cond else "  -- %s" % (note,)))


print("PC2 -- the deploy pin moves with the core")
real_sha, real_lines = P.core_now()
with open(P.VD, encoding="utf-8") as fh:
    real_text = fh.read()
check("PC2.1 the real tree: the pin and EXPECTED_LINES match the core on disk",
      P.pinned(real_text) == (real_sha, real_lines), (P.pinned(real_text), (real_sha[:12], real_lines)))

td = tempfile.mkdtemp(prefix="pc2_")
try:
    core = os.path.join(td, "core.py")
    with open(core, "wb") as fh:
        fh.write(b"print('a core')\n" * 7)
    vd = os.path.join(td, "verify_deploy.py")
    stale = P.rewrite(real_text, "0" * 64, 1)
    with open(vd, "w", encoding="utf-8", newline="") as fh:
        fh.write(stale)
    saved = (P.CORE, P.VD, P.run_judges)
    P.CORE, P.VD = core, vd
    want_sha, want_lines = P.core_now(core)
    try:
        check("PC2.2 --check on a stale pin says STALE and exits 1", P.main(["--check"]) == 1)
        P.run_judges = lambda run=None: ["test_k2_tally_arithmetic.py"]
        rc = P.main(["--write"])
        with open(vd, encoding="utf-8") as fh:
            after_fail = fh.read()
        check("PC2.3 a judging suite FAILS: the pin is NOT moved (the b969 order), exit 1",
              rc == 1 and after_fail == stale, rc)
        P.run_judges = lambda run=None: []
        rc = P.main(["--write"])
        with open(vd, encoding="utf-8") as fh:
            after_pass = fh.read()
        check("PC2.4 all four pass: the pin and the line count move to the core's",
              rc == 0 and P.pinned(after_pass) == (want_sha, want_lines), P.pinned(after_pass))
        strip = lambda t: P.LINES_RE.sub("", P.PIN_RE.sub("", t))  # noqa: E731
        check("PC2.5 ...and nothing else in the file changes -- the history comments stay as written",
              strip(after_pass) == strip(stale))
        check("PC2.6 --check after the move exits 0", P.main(["--check"]) == 0)
    finally:
        P.CORE, P.VD, P.run_judges = saved
    try:
        P.rewrite(real_text + '\n"covenant_unified_v8.py":\n        "' + "a" * 64 + '"\n', "b" * 64, 1)
        doubled = False
    except ValueError:
        doubled = True
    check("PC2.7 two core pins in one file is refused, never half-moved", doubled)
    hook = open(os.path.join(HERE, "ops", "pre-commit.synchold"), encoding="utf-8").read()
    check("PC2.8 the tracked hook calls the tool when the core is staged, and stages verify_deploy.py",
          "python tools/pin_core.py --write" in hook and "git add -- verify_deploy.py" in hook)
finally:
    shutil.rmtree(td, ignore_errors=True)

# ------------------------------------------------------------- PC2.9+: the other four pins (A315)
RAT = "run_all_tests.sh"
CORE_NAME = "covenant_unified_v8.py"
sha = lambda b: hashlib.sha256(b).hexdigest()  # noqa: E731
real_vd = open(P.VD, "rb").read()
real_man = D.manifest(real_vd.decode("utf-8"))


def on_disk(name):
    try:
        return sha(open(os.path.join(HERE, name), "rb").read())
    except OSError:
        return None


stale_now = sorted(n for n in (real_man or {}) if on_disk(n) != real_man[n])
check("PC2.9 the real tree: every pin verify_deploy.py holds -- discovered from its MANIFEST, %d of them -- "
      "matches its file on disk" % len(real_man or {}), real_man and len(real_man) >= 5 and not stale_now,
      "stale: %s" % stale_now)
others = sorted(n for n in (real_man or {}) if n not in D.OWNED_ELSEWHERE)
missing_judges = sorted(t for js in D.JUDGES.values() for t in js if not os.path.isfile(os.path.join(HERE, t)))
check("PC2.10 every pinned file has a mover: the core pin_core, each other one its judges in JUDGES -- and JUDGES "
      "names no file verify_deploy.py has stopped pinning, and no judge that is not here",
      real_man and CORE_NAME in real_man and set(others) == set(D.JUDGES) and not missing_judges,
      "pinned without judges: %s; judged but not pinned: %s; judges absent: %s"
      % (sorted(set(others) - set(D.JUDGES)), sorted(set(D.JUDGES) - set(others)), missing_judges))


class Rig:
    """A temp root holding copies of the four non-core pinned files and verify_deploy.py, the module pointed
    at it, and git and the judges stubbed: `index` is what the commit holds, `ran` the judges run."""

    def __init__(self, td):
        self.td = td
        for n in others:
            shutil.copy2(os.path.join(HERE, n), os.path.join(td, n))
        self.vd = os.path.join(td, "verify_deploy.py")
        with open(self.vd, "wb") as fh:
            fh.write(real_vd)
        self.index = {n: open(os.path.join(td, n), "rb").read() for n in others}
        self.index["verify_deploy.py"] = real_vd
        self.staged, self.added, self.ran, self.fail = [], [], [], set()

    def write(self, name, data, stage=True):
        with open(os.path.join(self.td, name), "wb") as fh:
            fh.write(data)
        if stage:
            self.index[name] = data
            self.staged.append(name)

    def vd_bytes(self):
        return open(self.vd, "rb").read()

    def run(self, argv):
        saved = (D.HERE, D.VD, D.indexed, D.staged_names, D.stage, D.run_judges)
        D.HERE, D.VD = self.td, self.vd
        D.indexed = lambda n: self.index.get(n)
        D.staged_names = lambda: list(self.staged)
        D.stage = lambda p: self.added.append(p) or True

        def judges(names, run=None):
            self.ran.extend(names)
            return [t for t in names if t in self.fail]
        D.run_judges = judges
        import io
        import contextlib
        out = io.StringIO()
        try:
            with contextlib.redirect_stdout(out):
                rc = D.main(argv)
        finally:
            D.HERE, D.VD, D.indexed, D.staged_names, D.stage, D.run_judges = saved
        return rc, out.getvalue()


def rig_case(fn):
    td = tempfile.mkdtemp(prefix="pc2d_")
    try:
        return fn(Rig(td))
    finally:
        shutil.rmtree(td, ignore_errors=True)


def edit_rat(r, stage=True, extra=b"run test_new_suite.py 60\n"):
    data = open(os.path.join(r.td, RAT), "rb").read() + extra
    r.write(RAT, data, stage)
    return data


def c11(r):
    edit_rat(r)
    rc, said = r.run(["--check"])
    return rc == 1 and "STALE  %s" % RAT in said and said.count("STALE") == 1, said


def c12(r):
    edit_rat(r)
    r.fail = {"test_k2_tally_arithmetic.py"}
    rc, said = r.run(["--write", "--staged"])
    return (rc == 1 and r.vd_bytes() == real_vd and "NOT moved: %s" % RAT in said
            and "test_k2_tally_arithmetic.py" in said and not r.added), said


def c13(r):
    data = edit_rat(r)
    rc, said = r.run(["--write", "--staged"])
    after = r.vd_bytes().decode("utf-8")
    man = D.manifest(after) or {}
    back = D.pin_re(RAT).sub(lambda m: m.group(1) + real_man[RAT] + m.group(3), after, count=1)
    ok = (rc == 0 and man.get(RAT) == sha(data) and back.encode("utf-8") == real_vd
          and all(man.get(n) == real_man[n] for n in real_man if n != RAT)
          and r.added == ["verify_deploy.py"] and sorted(r.ran) == sorted(D.JUDGES[RAT]))
    return ok, "rc=%s ran=%s added=%s %s" % (rc, r.ran, r.added, said)


def c14(r):
    lf = edit_rat(r)
    r.write(RAT, lf.replace(b"\n", b"\r\n"), stage=False)      # the 09-20 shape: a CRLF copy on disk
    rc, said = r.run(["--write", "--staged"])
    return (rc == 1 and r.vd_bytes() == real_vd and not r.ran and "are not the bytes this commit holds" in said
            and not r.added), said


def c15(r):
    edit_rat(r)
    with open(r.vd, "ab") as fh:
        fh.write(b"# an edit this commit does not stage\n")
    before = r.vd_bytes()
    rc, said = r.run(["--write", "--staged"])
    return (rc == 1 and r.vd_bytes() == before and not r.ran and not r.added
            and "changes this commit does not stage" in said), said


def c16(r):
    text = real_vd.decode("utf-8").replace('MANIFEST = {', 'MANIFEST = {\n    "a_sixth_file.py":\n        "%s",'
                                           % ("0" * 64), 1)
    with open(r.vd, "wb") as fh:
        fh.write(text.encode("utf-8"))
    r.index["verify_deploy.py"] = text.encode("utf-8")
    r.write("a_sixth_file.py", b"x = 1\n")
    rc, said = r.run(["--write", "--staged"])
    rc2, said2 = r.run(["--check"])
    return (rc == 1 and "NOT moved: a_sixth_file.py" in said and r.vd_bytes() == text.encode("utf-8")
            and rc2 == 1 and "NO JUDGES  a_sixth_file.py" in said2), said + said2


def c17(r):
    for n in ("run_local_sweep.py", "test_p19_overlay_guard.py"):
        r.write(n, open(os.path.join(r.td, n), "rb").read() + b"# moved\n")
    rc, said = r.run(["--write", "--staged"])
    man = D.manifest(r.vd_bytes().decode("utf-8")) or {}
    moved = all(man.get(n) == sha(r.index[n]) for n in ("run_local_sweep.py", "test_p19_overlay_guard.py"))
    return rc == 0 and moved and r.ran == ["test_p19_overlay_guard.py"], "ran=%s %s" % (r.ran, said)


def c18(r):
    r.staged.append(CORE_NAME)
    rc, said = r.run(["--write", "--staged"])
    rc2, said2 = r.run(["--write", CORE_NAME])
    return (rc == 0 and not said and not r.ran and r.vd_bytes() == real_vd
            and "tools/pin_core.py" in said2), said + said2


for label, fn in (
        ("PC2.11 --check on a stale run_all_tests.sh pin says STALE for that file alone, exit 1", c11),
        ("PC2.12 a judge FAILS (K2): --write --staged leaves verify_deploy.py byte-identical, names the suite, "
         "stages nothing, exit 1", c12),
        ("PC2.13 K1 and K2 pass: the pin moves to the committed bytes' digest, every other byte of verify_deploy.py "
         "-- the other four pins and the trailing history comment included -- is unchanged, and it is staged", c13),
        ("PC2.14 the file on disk is not the file being committed (a CRLF copy, the 09-20 shape): not moved, said, "
         "no judge run", c14),
        ("PC2.15 verify_deploy.py has changes this commit does not stage: not moved and NOT staged -- staging it "
         "would commit them", c15),
        ("PC2.16 a sixth pin with no judges recorded is not moved and is named, by --write and by --check", c16),
        ("PC2.17 run_local_sweep.py and test_p19 staged together: P19 runs once and both pins move", c17),
        ("PC2.18 the core staged: this tool runs nothing and leaves the core's pin to pin_core", c18)):
    good, note = rig_case(fn)
    check(label, good, note)

try:
    D.rewrite(real_vd.decode("utf-8") + '\n"%s":\n        "%s"\n' % (RAT, "a" * 64), RAT, "b" * 64)
    doubled = False
except ValueError:
    doubled = True
check("PC2.19 a file pinned twice is refused, never half-moved", doubled)

# PC2.20 drives the REAL default runner (no stub) with a hook's variables planted in this process.
td = tempfile.mkdtemp(prefix="pc2e_")
planted = {"GIT_DIR": os.path.join(td, "nowhere.git"), "GIT_INDEX_FILE": os.path.join(td, "index")}
saved_env = {k: os.environ.get(k) for k in planted}
saved_here = D.HERE
try:
    with open(os.path.join(td, "envprobe.py"), "w", encoding="utf-8") as fh:
        fh.write("import os, sys\nsys.exit(1 if {'GIT_DIR', 'GIT_INDEX_FILE'} & set(os.environ) else 0)\n")
    os.environ.update(planted)
    D.HERE = td
    leaked = D.run_judges(["envprobe.py"])
finally:
    D.HERE = saved_here
    for k, v in saved_env.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    shutil.rmtree(td, ignore_errors=True)
check("PC2.20 the judges run without the hook's GIT_DIR / GIT_INDEX_FILE (A255), driven through the real runner "
      "with both planted", leaked == [], leaked)

hook = open(os.path.join(HERE, "ops", "pre-commit.synchold"), encoding="utf-8").read()
# The executable lines, not their names: the header's comments mention the manifest command too.
code = "\n".join(l for l in hook.splitlines() if not l.lstrip().startswith("#"))
steps = ("pin=$(python tools/pin_core.py --write", "python tools/pin_deploy.py --write --staged",
         "python tools/stage_check.py", "vout=$(python verify_bundle.py --write-if-clean")
at = [code.find(s) for s in steps]
check("PC2.21 the tracked hook calls pin_deploy --write --staged on every commit, after pin_core's step and before "
      "stage_check and the manifest, which both read verify_deploy.py", 0 <= at[0] < at[1] < at[2] < at[3], at)


def e2e():
    """The tracked hook, installed in a scratch repository, committing run_all_tests.sh edits for real."""
    if not shutil.which("git"):
        print("  NOT RUN PC2.22-25: no git on PATH here -- the hook was not driven end to end")
        return
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["PATH"] = os.path.dirname(sys.executable) + os.pathsep + env.get("PATH", "")
    root = tempfile.mkdtemp(prefix="pc2_e2e_")

    def g(*a):
        return subprocess.run(["git", "-c", "user.name=pc2", "-c", "user.email=pc2@invalid", "-c", "core.autocrlf=false",
                               "-c", "core.hooksPath=.git/hooks"] + list(a), cwd=root, capture_output=True, timeout=300,
                              env=env)

    def head(name):
        return g("show", "HEAD:" + name).stdout

    try:
        g("init", "-q")
        os.makedirs(os.path.join(root, "tools"))
        shutil.copy2(os.path.join(HERE, "tools", "pin_deploy.py"), os.path.join(root, "tools"))
        stub = ("import os, sys\nhere = os.path.dirname(os.path.abspath(__file__))\nme = os.path.basename(__file__)\n"
                "open(os.path.join(here, 'ran.txt'), 'a').write('%s %s\\n' % (me, 'LEAKED' if 'GIT_INDEX_FILE' in "
                "os.environ else 'clean'))\nsys.exit(1 if os.path.exists(os.path.join(here, 'FAIL_' + me)) else 0)\n")
        for j in D.JUDGES[RAT]:
            with open(os.path.join(root, j), "w", encoding="utf-8", newline="\n") as fh:
                fh.write(stub)
        rat = b"#!/bin/sh\necho one\n"
        with open(os.path.join(root, RAT), "wb") as fh:
            fh.write(rat)
        base_vd = D.rewrite(real_vd.decode("utf-8"), RAT, sha(rat)).encode("utf-8")
        with open(os.path.join(root, "verify_deploy.py"), "wb") as fh:
            fh.write(base_vd)
        g("add", RAT, "verify_deploy.py", "tools/pin_deploy.py", *D.JUDGES[RAT])
        if g("commit", "-q", "-m", "base").returncode != 0:
            print("  NOT RUN PC2.22-25: the scratch base commit failed")
            return
        hook_dst = os.path.join(root, ".git", "hooks", "pre-commit")
        shutil.copy2(os.path.join(HERE, "ops", "pre-commit.synchold"), hook_dst)
        os.chmod(hook_dst, 0o755)                                # Linux git ignores a hook without +x (A255)

        def commit(line, msg):
            with open(os.path.join(root, RAT), "ab") as fh:
                fh.write(line)
            g("add", RAT)
            c = g("commit", "-m", msg)
            return c, (c.stdout + c.stderr).decode("utf-8", "replace")

        c, said = commit(b"echo two\n", "a suite line")
        vd_a, rat_a = head("verify_deploy.py"), head(RAT)
        check("PC2.22 END TO END: a committed run_all_tests.sh edit carries its moved pin in the SAME commit -- "
              "HEAD's verify_deploy.py pins HEAD's run_all_tests.sh, and nothing else in it changed",
              c.returncode == 0 and "pre-commit:" in said and b"echo two" in rat_a
              and vd_a == D.rewrite(base_vd.decode("utf-8"), RAT, sha(rat_a)).encode("utf-8"),
              "rc=%s %s" % (c.returncode, said[-400:]))
        ran = open(os.path.join(root, "ran.txt")).read() if os.path.isfile(os.path.join(root, "ran.txt")) else ""
        check("PC2.23 ...the judges ran first, inside the hook, and without the GIT_INDEX_FILE git gives the hook",
              ran.count(" clean") == len(D.JUDGES[RAT]) and "LEAKED" not in ran, repr(ran))
        open(os.path.join(root, "FAIL_test_k2_tally_arithmetic.py"), "w").close()
        c, said = commit(b"echo three\n", "a line K2 refuses")
        rat_b = head(RAT)
        check("PC2.24 END TO END the other way: K2 fails -- the commit still lands (the hook never blocks), its pin is "
              "NOT moved, and the hook says so naming K2",
              c.returncode == 0 and b"echo three" in rat_b and head("verify_deploy.py") == vd_a
              and (D.manifest(vd_a.decode("utf-8")) or {}).get(RAT) != sha(rat_b)
              and "NOT moved: %s" % RAT in said and "test_k2_tally_arithmetic.py" in said,
              "rc=%s %s" % (c.returncode, said[-400:]))

        # PC2.25 (2026-10-08): the path work lands by -- a merge. Two branches each edit run_all_tests.sh, each
        # commit moves the pin, so the digest LINE conflicts while the file merges cleanly. Resolving it to either
        # side leaves a digest of bytes the merge does not hold; the merge's own commit runs the hook, which must
        # move it. (A clean merge runs no pre-commit hook, but cannot reach this state: a file changed on one side
        # only merges to that side's bytes, and its pin moved with them.)
        os.remove(os.path.join(root, "FAIL_test_k2_tally_arithmetic.py"))
        commit(b"echo four\n", "the stale pin recovers on the next commit that stages the file")
        trunk = g("rev-parse", "--abbrev-ref", "HEAD").stdout.decode().strip()
        g("checkout", "-q", "-b", "side")
        commit(b"echo side\n", "side: a suite line at the end")
        g("checkout", "-q", trunk)
        body = open(os.path.join(root, RAT), "rb").read()
        with open(os.path.join(root, RAT), "wb") as fh:
            fh.write(body.replace(b"#!/bin/sh\n", b"#!/bin/sh\necho trunk-first\n", 1))
        g("add", RAT)
        g("commit", "-q", "-m", "trunk: a suite line at the top")
        m = g("merge", "--no-edit", "side")
        conflicted = g("diff", "--name-only", "--diff-filter=U").stdout.decode().split()
        g("checkout", "--ours", "verify_deploy.py")
        g("add", "verify_deploy.py")
        merged = open(os.path.join(root, RAT), "rb").read()
        resolved_stale = (D.manifest(open(os.path.join(root, "verify_deploy.py"), "rb").read().decode("utf-8"))
                          or {}).get(RAT) != sha(merged)
        c = g("commit", "--no-edit")
        said = (c.stdout + c.stderr).decode("utf-8", "replace")
        parents = g("rev-list", "--parents", "-n", "1", "HEAD").stdout.split()
        rat_m = head(RAT)
        check("PC2.25 END TO END, a merge: both branches moved the pin, the digest line conflicted and was resolved to "
              "one side's (stale for the merged bytes); the merge commit's hook moved it to HEAD's run_all_tests.sh",
              m.returncode != 0 and conflicted == ["verify_deploy.py"] and resolved_stale and c.returncode == 0
              and len(parents) == 3 and b"echo trunk-first" in rat_m and b"echo side" in rat_m
              and (D.manifest(head("verify_deploy.py").decode("utf-8")) or {}).get(RAT) == sha(rat_m)
              and "moved %s" % RAT in said,
              "merge rc=%s conflicted=%s resolved_stale=%s commit rc=%s parents=%d %s"
              % (m.returncode, conflicted, resolved_stale, c.returncode, len(parents), said[-300:]))
    finally:
        shutil.rmtree(root, ignore_errors=True)


e2e()

print("\nnot measured here: the installed .git/hooks/pre-commit (a local file git does not track);"
      " PC2.8 and PC2.21 read the tracked source it is installed from, PC2.22-25 install that source in a"
      " scratch repository; A117.8c compares the installed copy with it")
print("\nPC2: %d/%d passed" % (sum(ok), len(ok)))
sys.exit(0 if all(ok) else 1)
