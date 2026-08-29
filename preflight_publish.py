"""preflight_publish.py -- the questions to answer BEFORE the first push.

Same shape as launch_check.py and for the same reason: it ASKS, it changes
nothing, and it answers in three states. A repository is the one deployment
that cannot be rolled back -- `git push --force` rewrites your history and not
the forks, the caches, or the clones. So the gate belongs before the push, not
after somebody reads it.

  exit 0   nothing blocking
  exit 1   BLOCKED -- do not push
  exit 2   something could not be measured. NOT a pass.

    python preflight_publish.py
    python preflight_publish.py --json
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__)) or "."
PASS, BLOCKED, UNKNOWN = "PASS", "BLOCKED", "UNKNOWN"
_R = []


def R(tag, title, state, detail, fix=""):
    _R.append({"tag": tag, "title": title, "state": state,
               "detail": detail, "fix": fix})
    return _R[-1]


def git(*args, ok_codes=(0,)):
    try:
        p = subprocess.run(["git"] + list(args), cwd=HERE, text=True,
                           capture_output=True, timeout=180)
        return (p.stdout if p.returncode in ok_codes else ""), p.returncode
    except Exception as e:
        return "", -1


# ---------------------------------------------------------------- G1 secrets
def g1_key_material():
    """A PEM private key block, in ANY commit -- not just the current tree.

    History is the point. Deleting a key in a later commit removes it from the
    checkout and from nothing else: it stays in the pack, in every clone, and
    in GitHub's cache after a force-push. The only safe answer is that it was
    never committed, and that is what this asks."""
    rev, rc = git("rev-list", "--all")
    if rc != 0:
        return R("G1", "No private key ever committed", UNKNOWN,
                 "this is not a git repository, or git is unavailable",
                 "run inside the repository")
    revs = rev.split()
    if not revs:
        return R("G1", "No private key ever committed", UNKNOWN,
                 "no commits yet -- nothing to search")
    # the literal PEM header, anchored: the search STRINGS that appear in this
    # project's own tests must not count as findings (test_covenant_app.py
    # asserts that /api/state contains no "BEGIN PRIVATE KEY", and that
    # assertion is not a key).
    out, _ = git("grep", "-I", "-l", "-E",
                 r"^-----BEGIN [A-Z ]*PRIVATE KEY-----", *revs, ok_codes=(0, 1))
    hits = sorted({l.split(":", 1)[-1] for l in out.splitlines() if l.strip()})
    if hits:
        return R("G1", "No private key ever committed", BLOCKED,
                 f"{len(hits)} file(s) contain a PEM private key block in "
                 f"history: {', '.join(hits[:6])}",
                 "DO NOT PUSH. The key is compromised the moment this is "
                 "public: rotate it first, then rewrite history "
                 "(git-filter-repo), then push.")
    return R("G1", "No private key ever committed", PASS,
             f"{len(revs)} commit(s) searched for an anchored PEM header, none found")


def g2_secret_assignments():
    pat = (r"(api[_-]?key|apikey|secret|password|passwd|access[_-]?token|"
           r"auth[_-]?token|private[_-]?key|mnemonic|recovery[_-]?phrase)"
           r"\s*[:=]\s*[\"'][A-Za-z0-9+/=_\-]{16,}[\"']")
    out, _ = git("grep", "-I", "-n", "-E", pat, ok_codes=(0, 1))
    real = [l for l in out.splitlines()
            if not re.search(r"(os\.environ|getenv|EXAMPLE|example|placeholder|"
                             r"your[_-]|xxxx|<[a-z]|\.md:)", l, re.I)]
    # A TEST NEEDS A FAKE CREDENTIAL TO PROVE A REAL ONE CANNOT LEAK.
    #
    # test_b2_quorum_diversity sets `api_key = "SENTINEL-VALUE-must-never-
    # appear"` and then asserts that string is absent from the quorum report.
    # That is the check working, not a credential -- and the first run of this
    # gate reported it as BLOCKED, which is a gate crying wolf on the thing it
    # was built to protect. Classified UNKNOWN rather than excluded: a
    # credential-shaped literal in a test file is PROBABLY a fixture, and
    # "probably" is exactly what UNKNOWN is for. It is never silently passed,
    # and the value is printed so the glance takes one second.
    def _fixture(line):
        path = line.split(":", 1)[0]
        return (re.search(r"(^|/)(test_|probe_|sim_)", path)
                and re.search(r"SENTINEL|must-never-appear|FAKE|DUMMY|NOTREAL",
                              line, re.I))
    fixtures = [l for l in real if _fixture(l)]
    real = [l for l in real if not _fixture(l)]
    if real:
        return R("G2", "No hard-coded credential in the tracked tree", BLOCKED,
                 f"{len(real)} line(s): " + "; ".join(x[:70] for x in real[:4]),
                 "move it to an environment variable and rotate the value")
    if fixtures:
        return R("G2", "No hard-coded credential in the tracked tree", UNKNOWN,
                 f"{len(fixtures)} credential-shaped literal(s), all inside "
                 f"test files and all self-labelled as fixtures: "
                 + "; ".join(x[:74] for x in fixtures[:3]),
                 "read them once and confirm. A test that proves a key cannot "
                 "leak needs a key that is not real.")
    return R("G2", "No hard-coded credential in the tracked tree", PASS,
             "no assignment of a 16+ character literal to a credential name")


def g3_tracked_kinds():
    """Key files, databases and logs must not be tracked at all."""
    out, rc = git("ls-files")
    if rc != 0:
        return R("G3", "No key, database or log file is tracked", UNKNOWN,
                 "git ls-files failed")
    files = out.split()
    bad = [f for f in files
           if re.search(r"(\.key|\.pem|\.p12|\.pfx|\.db|\.db-wal|\.db-shm|"
                        r"\.log|\.env)$", f)]
    if bad:
        return R("G3", "No key, database or log file is tracked", BLOCKED,
                 f"{len(bad)}: {', '.join(bad[:8])}",
                 "git rm --cached them and add the patterns to .gitignore")
    return R("G3", "No key, database or log file is tracked", PASS,
             f"{len(files)} tracked files, none matching key/db/log extensions")


def g4_gitignore_works():
    """M31: a .gitignore nobody has watched refuse anything has not been tested.

    `git check-ignore` is asked directly, with paths that do not exist. It
    answers from the RULES, so this needs no file created and cleans nothing up.
    """
    probes = ["nodeA_prod.db.key", "secrets.env", "logs/watchdog.log",
              "nodeB_prod.db", ".covenant-keys/id", "wallet.pem"]
    missed = []
    for p in probes:
        _, rc = git("check-ignore", "-q", p, ok_codes=(0, 1))
        if rc != 0:
            missed.append(p)
    if missed:
        return R("G4", "The ignore rules actually refuse key material", BLOCKED,
                 f"NOT ignored: {', '.join(missed)}",
                 "add these patterns to .gitignore before the first push")
    return R("G4", "The ignore rules actually refuse key material", PASS,
             f"{len(probes)} probe paths, all ignored (asked of the rules, "
             f"nothing written)")


def g5_personal_paths():
    """Somebody's home directory is not a secret and is still theirs.

    A published repo carrying `C:\\Users\\<name>` tells every reader the
    author's account name, and it is far cheaper to fix before the first push
    than after a fork exists."""
    out, _ = git("grep", "-I", "-l", "-E",
                 r"C:\\+Users\\+[A-Za-z0-9_.-]+|/home/[a-z][a-z0-9_-]+/",
                 ok_codes=(0, 1))
    hits = sorted({l for l in out.splitlines() if l.strip()})
    docs = [h for h in hits if h.endswith((".md", ".txt"))]
    code = [h for h in hits if not h.endswith((".md", ".txt"))]
    if hits:
        return R("G5", "No personal filesystem path is published", BLOCKED,
                 f"{len(hits)} tracked file(s) carry a home-directory path "
                 f"({len(code)} code/config, {len(docs)} docs): "
                 f"{', '.join(hits[:6])}",
                 "these are paths, not secrets -- but they name the author's "
                 "account to every reader. Replace with a placeholder, or "
                 "accept deliberately and re-run with --allow-paths")
    return R("G5", "No personal filesystem path is published", PASS,
             "no tracked file contains a home-directory path")


def g6_outputs_tracked():
    """A repository of INPUTS. Same rule the manifest learned the hard way."""
    out, _ = git("ls-files")
    files = out.split()
    outs = [f for f in files if re.search(
        r"(RESULTS|_DIAG|DIAG_|diag_out|TOPMEM|FREE_RAM|PORT_PICK|PORT_DIAG|"
        r"LEAN_MEASURE|FIT_CHECK|CLEANUP|STRAY_FIX|NODE_RESTART|"
        r"LAUNCH_CHECK|DEPLOY_VERIFY)", f)]
    outs = [f for f in outs if not f.startswith("docs/")]
    if outs:
        return R("G6", "The repository tracks inputs, not its own output",
                 UNKNOWN,
                 f"{len(outs)} generated file(s) tracked outside docs/: "
                 f"{', '.join(outs[:8])}",
                 "these are this machine's output. Harmless to publish, noisy "
                 "to maintain, and every run makes the tree dirty. Archive "
                 "under docs/results/ or ignore them.")
    return R("G6", "The repository tracks inputs, not its own output", PASS,
             "no generated output tracked outside docs/")


def g7_remote():
    out, _ = git("remote", "-v")
    if not out.strip():
        return R("G7", "The push target is known", UNKNOWN,
                 "no remote configured yet -- nothing can be pushed by "
                 "accident, and nothing is verified either")
    return R("G7", "The push target is known", PASS,
             "; ".join(sorted({l.split()[1] for l in out.splitlines() if l.split()})))


def g8_license():
    for n in ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING"):
        p = os.path.join(HERE, n)
        if os.path.exists(p):
            txt = open(p, encoding="utf-8", errors="replace").read()
            known = any(k in txt for k in ("MIT License", "Apache License",
                                           "GNU GENERAL PUBLIC", "BSD",
                                           "Mozilla Public License"))
            if known:
                return R("G8", "The terms of use are stated", PASS,
                         f"{n}, a recognised licence")
            return R("G8", "The terms of use are stated", UNKNOWN,
                     f"{n} exists but is not a recognised licence -- readers "
                     f"get no rights by default, which may be deliberate",
                     "if that IS deliberate, say so in the README's first "
                     "screen so nobody has to guess")
    return R("G8", "The terms of use are stated", BLOCKED,
             "no LICENSE file",
             "without one, default copyright applies and nobody may legally "
             "use, fork or contribute. Choose deliberately.")


def g9_line_endings():
    """A .bat checked out with bare LF is M44, and it fails SILENTLY.

    This project spent a run finding that a GOTO-based batch file with LF
    endings aborts after a few lines with no error anywhere. `.gitattributes`
    handles it -- and nothing asserted that it does. A clone is the one place
    the rule has to hold and the one place nobody was checking, because on the
    authoring machine the file is already correct.

    Asked of git's own attribute resolution, per file, so it reports what a
    CHECKOUT will produce rather than what the working tree happens to hold."""
    out, rc = git("ls-files")
    if rc != 0:
        return R("G9", "Batch files will check out with CRLF", UNKNOWN,
                 "git ls-files failed")
    wrong = []
    for f in out.split():
        want = ("crlf" if f.lower().endswith((".bat", ".cmd"))
                else "lf" if f.lower().endswith(".sh") else None)
        if want is None:
            continue
        a, _ = git("check-attr", "eol", "--", f)
        got = a.strip().rsplit(":", 1)[-1].strip() if a.strip() else "unset"
        if got != want:
            wrong.append(f"{f} -> {got}, want {want}")
    if wrong:
        return R("G9", "Batch files will check out with CRLF", BLOCKED,
                 f"{len(wrong)}: {', '.join(wrong[:5])}",
                 "add `*.bat text eol=crlf` (and `*.sh text eol=lf`) to "
                 ".gitattributes. A GOTO-based .bat with LF endings aborts a "
                 "few lines in and prints nothing -- the clone breaks in a way "
                 "no error message describes.")
    n = sum(1 for f in out.split() if f.lower().endswith((".bat", ".cmd", ".sh")))
    return R("G9", "Batch files will check out with CRLF", PASS,
             f"{n} script(s) checked; .bat/.cmd resolve to crlf, .sh to lf")


def main():
    allow_paths = "--allow-paths" in sys.argv
    for fn in (g1_key_material, g2_secret_assignments, g3_tracked_kinds,
               g4_gitignore_works, g5_personal_paths, g6_outputs_tracked,
               g7_remote, g8_license, g9_line_endings):
        try:
            fn()
        except Exception as e:
            R(fn.__name__, fn.__name__, UNKNOWN,
              f"the check itself raised {type(e).__name__}: {e}")
    if allow_paths:
        for r in _R:
            if r["tag"] == "G5" and r["state"] == BLOCKED:
                r["state"] = PASS
                r["detail"] += "  [accepted with --allow-paths]"

    if "--json" in sys.argv:
        print(json.dumps(_R, indent=1))
    else:
        print("PREFLIGHT -- before the first push\n" + "=" * 62)
        for r in _R:
            print(f"{r['state']:<8} {r['tag']:<4} {r['title']}")
            print(f"         {r['detail']}")
            if r["fix"] and r["state"] != PASS:
                print(f"         -> {r['fix']}")
        n = {s: sum(1 for r in _R if r["state"] == s)
             for s in (PASS, BLOCKED, UNKNOWN)}
        print("=" * 62)
        print(f"{n[PASS]} pass  {n[BLOCKED]} blocked  {n[UNKNOWN]} unknown")
        if n[BLOCKED]:
            print("DO NOT PUSH. A repository is the one deployment that cannot "
                  "be rolled back.")
        elif n[UNKNOWN]:
            print("Nothing blocking, but something could not be measured -- "
                  "and UNKNOWN is not a pass.")
    return 1 if any(r["state"] == BLOCKED for r in _R) else (
        2 if any(r["state"] == UNKNOWN for r in _R) else 0)


if __name__ == "__main__":
    raise SystemExit(main())
