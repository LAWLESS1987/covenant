#!/usr/bin/env python3
"""tools/covenant_adopt.py -- scan an incoming origin/main and say whether it is safe to adopt.

Lawrence, 2026-11-17: "get this running in the next 2 days ... mutual benefit of all intelligence",
and "make this decision here". A node that blindly ran whatever merged to GitHub would execute
unreviewed remote code; the chain already auto-syncs, node CODE does not, by design. This keeps that
safety while removing the manual toil: it SCANS and VERIFIES, and (once armed) ADOPTS only on a clean gate.

COVENANT-NATIVE, and portable: it lives in the covenant repo every node has, reuses covenant_one.py's
gate as the test, and needs no per-host infrastructure -- so the same tool runs on this host (A/B/C on
one checkout) and on a second operator's node. It is the covenant-native cousin of node D's
noded/safe_integrate.py (that session's design -- the added-line backdoor scan, HIGH-holds-for-review,
the differential gate, kill-switch + daily cap -- is reused here with credit; the model judge seat and
dry_launch it also carries are a v2 addition, deferred).

THE PIPELINE, on a throwaway worktree so the live node is untouched until the very end:
  detect   -> git fetch; how far behind origin/main, which files/commits changed
  candidate-> merge origin/main into a scratch worktree; a CONFLICT is NO-GO (human needed)
  classify -> HIGH if the diff touches a security-sensitive path (gate, keys, launcher, hands, ...)
  scan     -> backdoor pattern scan over the lines the candidate ADDS
  test     -> covenant_one.py --check, DIFFERENTIALLY: only a gate the merge NEWLY breaks blocks
  decide   -> GO only if NORMAL sensitivity and every check is clean; HIGH always HOLDS for review
  apply    -> (only when ARMED: COVENANT_ADOPT_AUTO=1, GO, not kill-switched, under the daily cap)
              hand off to COVENANT_ADOPT_UPDATER, then health-check; rollback is the updater's job

WHAT THE SENDER OF A CHANGE MUST NOT BE ABLE TO DECIDE (A453). The commit this node is on is named by its FULL
id everywhere inside the gate: git reads a shortened id as a ref name first, and a tag is a name the sender
chooses. The fetch takes no tags. The diff is read by each hunk's own line counts, as bytes, and git is asked for
it as text whatever attributes arrive with the change. A tracked name that some other ref shadows holds.
The incoming commit is resolved ONCE, to a full id, and every later step uses that id. Changed files are listed
with rename detection off, so a sensitive file renamed to a neutral name still shows its old name. A fetch that
fails, or a ref that does not resolve, is an ERROR (exit 2), never "already current". A candidate that does not
contain the incoming commit is no candidate. After an apply the tool lists every commit that landed and was not
the one it tested (the updater does its own merge; see apply).

DEFAULT IS PROPOSE: COVENANT_ADOPT_AUTO is OFF unless set to 1. `scan` never applies; `run` applies only
when ARMED. A kill-switch file (ops/covenant_adopt.disabled) forces propose instantly; a daily cap bounds
unattended applies. Nothing here prints a key or a secret.

CLI:
  python tools/covenant_adopt.py scan            # full pipeline, decision only, never applies (safe anywhere)
  python tools/covenant_adopt.py run             # scan, then apply IF armed and GO
  python tools/covenant_adopt.py run --dry        # like run but prints what apply WOULD do, applies nothing
  python tools/covenant_adopt.py digest           # summarize the ledger for the daily/every-few review
  [--json]
Exit: 0 GO/applied, 1 NO-GO/held, 2 error, 3 nothing to do (already current).
"""
from __future__ import annotations
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))     # the covenant repo root
REPO = os.environ.get("COVENANT_ADOPT_REPO", HERE)
TRACKED = os.environ.get("COVENANT_ADOPT_BRANCH", "origin/main")
STATE_DIR = os.path.join(REPO, "ops")
KILL_SWITCH = os.path.join(STATE_DIR, "covenant_adopt.disabled")       # present -> propose-only, instantly
LEDGER = os.path.join(STATE_DIR, "covenant_adopt.jsonl")              # one JSON line per run (gitignored)
UPDATER = os.environ.get("COVENANT_ADOPT_UPDATER")                    # the stop+merge+restart script; apply needs it
AUTO = os.environ.get("COVENANT_ADOPT_AUTO", "0") in ("1", "true", "yes", "on")
MAX_PER_DAY = int(os.environ.get("COVENANT_ADOPT_MAX_PER_DAY", "3"))
_NOWIN = 0x08000000 if os.name == "nt" else 0

# A changed file whose path OR name matches this is security-shaped -> HIGH -> held for a human even when
# armed. Deliberately broad: a false HIGH costs a human glance; a missed one adopts a sensitive change blind.
SENSITIVE = re.compile(
    r"(gate|sign|_key|keys|admit|exec_guard|seal|genesis|operator|allowlist|allow\.json|policy|launch|"
    r"run_node|hands|act_gate|credential|token|secret|watchdog|highway|succession|stake|claim|mine|"
    r"machine|grid|consent|headscale|redund|failover|takeover|"
    r"gitattributes|gitmodules)", re.I)                     # A453: files that tell git how to treat the tree

# Backdoor patterns over ADDED lines only (node D's set, reused). Routine subprocess/urllib in existing code
# never appears here -- only the lines the merge adds are read. A hit is HOLD-for-a-human, not a proven backdoor.
_PATTERNS = [
    ("listener_all_ifaces", re.compile(r"bind\(\(?\s*['\"]?0\.0\.0\.0|host\s*=\s*['\"]0\.0\.0\.0")),
    ("reverse_shell", re.compile(r"(/bin/sh['\"]?\s*,?\s*['\"]-i|cmd\.exe.{0,40}/c\b.{0,40}(socket|connect)|pty\.spawn)")),
    ("exec_of_decoded", re.compile(r"(b64decode|b85decode|unhexlify|fromhex).{0,80}(exec|eval)\(|(exec|eval)\(.{0,40}(decode|loads|\.read)\(")),
    ("persistence_new", re.compile(r"(schtasks.{0,40}/create|New-Service|Register-ScheduledTask|reg(\.exe)?\s+add.{0,60}Run|crontab\s+-|systemctl\s+enable)")),
    ("cred_capture", re.compile(r"(id_rsa|id_ed25519|CryptUnprotectData|DPAPI|/\.ssh/|Authorization['\"]?\s*\].{0,40}(post|send|write))")),
]


def _text(raw):
    """Bytes a child process printed, as text. ALWAYS read as bytes and decoded here, never with text=True:
    with text=True the output is decoded by this machine's default codec in a reader thread, and one byte that
    codec has no character for (0x9d on a cp1252 Windows: half of a curly quote) kills the thread; run() then
    returns stdout None with exit 0 and `(r.stdout or "")` reads as NO OUTPUT. Measured by the laptop session,
    2026-11-19: a check that printed "G5 FAIL" and one curly quote read as nothing failing, GO; a commit subject
    with one emptied the incoming list; and of main's last 40 commits two diffs read as nothing at all. On Linux
    the same byte raised instead. Undecodable bytes become U+FFFD; nothing is dropped."""
    return (raw or b"").decode("utf-8", "replace").replace("\r\n", "\n")


def _git(args, cwd=None, timeout=180):
    r = subprocess.run(["git"] + args, cwd=cwd or REPO, capture_output=True, timeout=timeout, creationflags=_NOWIN)
    return r.returncode, _text(r.stdout).strip(), _text(r.stderr).strip()


def _run(cmd, cwd, timeout, env=None):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, timeout=timeout, creationflags=_NOWIN, env=env)
    return r.returncode, (_text(r.stdout) + _text(r.stderr)).strip()


_FULL_ID = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?")


def is_full_id(v):
    """True for a full commit id (40 hex characters, or 64). Git reads anything shorter as a REF NAME first: a
    tag named after this node's 12-character HEAD made `git diff <those 12> HEAD` compare the incoming change
    with itself (A453). A full id is never taken as a ref name, even when a ref of that name exists."""
    return bool(_FULL_ID.fullmatch(str(v or "")))


def tracked_is_shadowed(cwd=None):
    """"" when TRACKED, read as a name, is the remote-tracking branch it should be; otherwise why not. A tag or
    a local branch called `origin/main` wins over refs/remotes/origin/main in git's lookup, and the gate would
    then test whatever that ref points at. A TRACKED that is not a remote-tracking name is left alone."""
    if TRACKED.startswith("refs/"):
        return ""
    rc_ref, ref, _ = _git(["rev-parse", "--verify", "--quiet", "refs/remotes/%s^{commit}" % TRACKED], cwd=cwd)
    if rc_ref or not ref:
        return ""
    _rc, named, _ = _git(["rev-parse", "--verify", "--quiet", "%s^{commit}" % TRACKED], cwd=cwd)
    if named != ref:
        return "the name %s resolves to %s, not to the remote branch at %s: another ref shadows it" % (
            TRACKED, named[:12] or "nothing", ref[:12])
    return ""


def _resolve(name, cwd=None):
    """The full commit id `name` means right now, or "" when it means no commit."""
    rc, out, _ = _git(["rev-parse", "--verify", "--quiet", "%s^{commit}" % name], cwd=cwd)
    return out if rc == 0 and is_full_id(out) else ""


def detect():
    """Fetch, then name both sides ONCE by full id: `head` (this node) and `incoming` (the remote branch). Every
    later step uses those two ids, so nothing that moves or is renamed afterwards changes what is judged.
    `error` is set when the remote could not be read: the caller must not call that "already current"."""
    # --no-tags: the gate needs no tag, and a tag is a name the SENDER chooses (see is_full_id).
    rc_f, _, ferr = _git(["fetch", "--quiet", "--no-tags", "origin"], timeout=180)
    head = _resolve("HEAD")
    # Never the bare NAME: a tag or anything else called `origin/main` would answer to it. A name that is not a
    # full ref is read as the remote-tracking branch, else as a local branch, and as nothing else.
    incoming = (_resolve(TRACKED) if TRACKED.startswith("refs/") else
                (_resolve("refs/remotes/" + TRACKED) or _resolve("refs/heads/" + TRACKED)))
    info = {"head": head, "incoming": incoming, "behind": None, "ahead": None, "changed_files": [],
            "incoming_commits": [], "tracked_shadowed": tracked_is_shadowed()}
    if rc_f:
        info["error"] = "git fetch origin failed (%s): nothing was checked" % ((ferr.splitlines() or ["rc=%s" % rc_f])[-1][:120])
    elif not head or not incoming:
        info["error"] = "%s does not resolve to a commit: nothing was checked" % ("HEAD" if not head else TRACKED)
    if info.get("error"):
        return info
    rc2, lr, _ = _git(["rev-list", "--left-right", "--count", "%s...%s" % (incoming, head)])
    if rc2 == 0 and len(lr.split()) == 2:
        info["behind"], info["ahead"] = (int(x) for x in lr.split())
    # --no-renames: with rename detection on (git's default) a sensitive file renamed to a neutral name is
    # listed under the new name only, and classify() read NORMAL (measured by the laptop session, 2026-11-19).
    rc3, files, _ = _git(["diff", "--name-only", "--no-renames", "%s...%s" % (head, incoming), "--"])
    rc4, commits, _ = _git(["log", "--oneline", "%s..%s" % (head, incoming)])
    if rc2 or rc3 or rc4 or info["behind"] is None:
        info["error"] = "git could not compare %s with %s: nothing was checked" % (head[:12], incoming[:12])
        return info
    info["changed_files"] = [f for f in files.splitlines() if f.strip()]
    info["incoming_commits"] = commits.splitlines()
    return info


def classify(changed_files):
    hits = [f for f in changed_files if SENSITIVE.search(f.replace("\\", "/"))]
    return ("HIGH" if hits else "NORMAL"), hits


def scan_lines(added):
    hits = []
    for item in added:
        f, text = item if isinstance(item, tuple) else (None, item)
        for label, rx in _PATTERNS:
            if rx.search(text):
                hits.append({"file": f, "pattern": label, "added": text.strip()[:120]})
    return hits


_HUNK = re.compile(rb"^@@ -\d+(?:,(\d+))? \+\d+(?:,(\d+))? @@")
# What the scan asks git for (A453). Each flag answers something the incoming change, or this machine's git
# config, could otherwise decide:
#   --text    a `.gitattributes` that ARRIVES with the change ("*.py -diff") made git print "Binary files
#             differ" for every Python file, and the scan read no added line at all.
#   --no-textconv --no-ext-diff --no-color and the two prefixes: the plain unified diff, whatever diff driver,
#             colour or prefix setting this machine has.
#   --no-renames  a file that arrives under a new name is read whole: text that sat inert under one name is
#             new under another, and the header then names the path it lands at.
_DIFF = ["-c", "core.quotepath=off", "diff", "--text", "--no-textconv", "--no-ext-diff", "--no-color",
         "--no-renames", "--src-prefix=a/", "--dst-prefix=b/"]


def _header_path(line):
    """The path in a `+++ b/<path>` header line; None for /dev/null or anything else."""
    p = line[4:].rstrip("\t")
    if len(p) >= 2 and p.startswith('"') and p.endswith('"'):
        p = p[1:-1]
    return p[2:] if p.startswith("b/") else None


def added_lines(patch):
    """[(file, text)] for every line a unified diff ADDS. `patch` is the BYTES git printed. Pure.

    Lines are counted by each hunk's own header (`@@ -a,b +c,d @@`): inside a hunk every line is content,
    whatever it begins with. The first reader went line by line, took any line starting `+++ b/` as a file
    header and skipped any line starting `+++`. So an added line whose text begins `++` was never scanned
    (`++pty.spawn('/bin/sh')` is valid Python: unary plus, twice), and an added line `++ b/<an existing file>`
    moved every later hit onto that file's name while the file that held it went unnamed (A453).
    Split on the newline byte only: a lone carriage return or form feed inside a line is part of that line, and
    splitting on it would throw the count off. Outside a hunk git prints no `+` line except the `+++` header;
    one that is not a header (the line before it is not `--- `) is read as added rather than skipped."""
    cur, added, old_left, new_left, prev = None, [], 0, 0, b""
    for raw in patch.split(b"\n"):
        if old_left > 0 or new_left > 0:
            c = raw[:1]
            if c == b"+":
                added.append((cur, raw[1:].decode("utf-8", "replace")))
                new_left -= 1
            elif c == b"-":
                old_left -= 1
            elif c != b"\\":                                  # "\ No newline at end of file": neither side
                old_left -= 1
                new_left -= 1
            continue
        m = _HUNK.match(raw)
        if m:
            old_left = 1 if m.group(1) is None else int(m.group(1))
            new_left = 1 if m.group(2) is None else int(m.group(2))
        elif raw.startswith(b"+++ ") and prev.startswith(b"--- "):
            cur = _header_path(raw.decode("utf-8", "replace"))
        elif raw.startswith(b"+"):
            added.append((cur, raw[1:].decode("utf-8", "replace")))
        prev = raw
    return added


def scan(worktree, base_sha):
    """Backdoor scan over the lines the candidate ADDS (git diff base..HEAD inside the scratch). `base_sha` must
    be a FULL commit id; anything else is an error, and an error holds (see is_full_id)."""
    if not is_full_id(base_sha):
        return {"state": "error", "detail": "the base is not a full commit id; refusing to guess", "hits": []}
    try:
        r = subprocess.run(["git"] + _DIFF + [base_sha, "HEAD", "--"], cwd=worktree, capture_output=True,
                           timeout=300, creationflags=_NOWIN)
    except (OSError, subprocess.SubprocessError) as e:
        return {"state": "error", "detail": "diff failed: " + type(e).__name__, "hits": []}
    if r.returncode:
        return {"state": "error", "detail": (r.stderr or b"").decode("utf-8", "replace").strip()[:160], "hits": []}
    hits = scan_lines(added_lines(r.stdout or b""))
    return {"state": "hits" if hits else "clean", "hits": hits}


CHECK_DONE = "--check was passed. Stopping here."     # covenant_one's last line under --check
CHECK_UNFINISHED = "<check did not finish>"


def _check_gates(cwd):
    """covenant_one.py --check -> the SET of gates it reports failing. --check exits 1 on the live HEAD too
    (G5 ethics-judge-down, a stale sweep, a manifest drift), so an absolute pass is the wrong bar; the caller
    compares candidate vs a HEAD reference and blocks only on a NEW failure."""
    _rc, said = _run([sys.executable, "covenant_one.py", "--check"], cwd, 1200)
    failing = set()
    # A FLOOR, NOT A PROOF (A453). "No failing line" was read as "nothing fails": a runner that did not parse,
    # crashed, or printed nothing passed. A run that never reaches --check's own last line did not finish, and
    # that is a failure; a HEAD reference that also does not finish cancels it, as with any other gate. This
    # does not stop a runner that LIES -- the runner is the incoming tree's own -- it stops one that broke.
    if CHECK_DONE not in said:
        failing.add(CHECK_UNFINISHED)
    for ln in said.splitlines():
        m = re.match(r"\s*(G\d+)\s+(BLOCKED|FAIL|UNKNOWN)\b", ln)
        if m:
            failing.add(m.group(1))
        for fm in re.finditer(r"(\S+\.py)=FAIL", ln):
            failing.add(fm.group(1))
    return failing


def _add_worktree(committish):
    scratch = tempfile.mkdtemp(prefix="covenant-adopt-")
    wt = os.path.join(scratch, "wt")
    rc, _, _ = _git(["worktree", "add", "--detach", wt, committish], timeout=300)
    return (wt if rc == 0 else None)


def _cleanup(wt):
    if wt:
        _git(["worktree", "remove", "--force", wt], timeout=120)
        shutil.rmtree(os.path.dirname(wt), ignore_errors=True)
    _git(["worktree", "prune"], timeout=60)


def build_candidate(info):
    """Scratch worktree of this node's commit, merge the incoming commit into it (both by full id), commit a
    clean tree. Conflict -> (None, reason). So is a merge that did not happen: the first version never looked
    at the merge's exit code, and a merge that failed without a conflict (a path this machine cannot create in
    the scratch folder, say) left a "candidate" that was just HEAD -- scanned clean, tested clean, GO (A453)."""
    if not (is_full_id(info.get("head")) and is_full_id(info.get("incoming"))):
        return None, "no candidate: both sides must be named by a full commit id"
    wt = _add_worktree(info["head"])
    if wt is None:
        return None, "worktree add failed"
    _rc_m, _, merge_err = _git(["-c", "user.name=covenant-adopt", "-c", "user.email=node@covenant.local",
                                "merge", "--no-ff", "--no-edit", info["incoming"]], cwd=wt, timeout=300)
    _rc, unmerged, _ = _git(["ls-files", "-u"], cwd=wt, timeout=120)
    if unmerged.strip():
        # a GENERATED-only conflict (MANIFEST.sha256, LOOKBACK) is not a code conflict: take theirs and go on.
        only_generated = all(p.split("\t")[-1] in ("MANIFEST.sha256", "docs/LOOKBACK_INDEX.md")
                             for p in unmerged.splitlines() if p.strip())
        if only_generated:
            for p in ("MANIFEST.sha256", "docs/LOOKBACK_INDEX.md"):
                _git(["checkout", "--theirs", p], cwd=wt, timeout=60)
                _git(["add", p], cwd=wt, timeout=60)
        else:
            _git(["merge", "--abort"], cwd=wt, timeout=120)
            _cleanup(wt)
            return None, "merge conflict (human needed): " + unmerged.splitlines()[0][:100]
    _git(["-c", "user.name=covenant-adopt", "-c", "user.email=node@covenant.local",
          "commit", "--no-verify", "--no-edit"], cwd=wt, timeout=120)
    rc_a, _, _ = _git(["merge-base", "--is-ancestor", info["incoming"], "HEAD"], cwd=wt, timeout=120)
    if rc_a:
        _git(["merge", "--abort"], cwd=wt, timeout=120)
        _cleanup(wt)
        return None, "merge did not complete (human needed): " + (
            (merge_err.splitlines() or ["the scratch tree does not hold the incoming commit"])[-1][:120])
    return wt, "merged cleanly in scratch"


def differential_test(wt, head_sha):
    """APPLES TO APPLES: check the candidate and a HEAD reference in fresh worktrees; a gate that fails on
    BOTH (gitignored on-disk state) cancels. Only a gate the MERGE newly breaks blocks."""
    if not is_full_id(head_sha):
        # A short id can be a tag pointing at the incoming commit: the reference would BE the candidate, and
        # "nothing newly fails" would be true of anything (A453). No reference, no pass.
        return {"ok": False, "new_failures": ["<no reference worktree>"], "candidate_failing": []}
    cand = _check_gates(wt)
    ref_wt = _add_worktree(head_sha)
    if ref_wt is None:
        return {"ok": False, "new_failures": ["<no reference worktree>"], "candidate_failing": sorted(cand)}
    try:
        ref = _check_gates(ref_wt)
    finally:
        _cleanup(ref_wt)
    new = sorted(cand - ref)
    return {"ok": not new, "new_failures": new, "candidate_failing": sorted(cand), "reference_failing": sorted(ref)}


def decide(cls, sens_hits, scan_info, test_info, merge_ok, shadowed=""):
    reasons = []
    if shadowed:
        reasons.append("tracked branch is shadowed: %s" % shadowed)
    if not merge_ok:
        reasons.append("merge not clean")
    if cls == "HIGH":
        reasons.append("security-sensitive diff (%s) -- holds for review" % ", ".join(sens_hits[:5]))
    if scan_info.get("state") != "clean":
        reasons.append("backdoor scan: %s" % scan_info.get("state"))
    if not test_info.get("ok"):
        reasons.append("new failing gate(s): %s" % ", ".join(test_info.get("new_failures", [])))
    return ("GO" if not reasons else "NO-GO"), reasons


def _applied_today():
    today = time.strftime("%Y-%m-%d")
    n = 0
    try:
        for ln in open(LEDGER, encoding="utf-8"):
            d = json.loads(ln)
            if d.get("applied") and str(d.get("t", "")).startswith(today):
                n += 1
    except OSError:
        pass
    return n


def untested_commits(head, incoming, after, cwd=None):
    """Commits that are in `after` (what the node is on now) and were not what the gate tested. Tested: `head`,
    `incoming` and their histories, plus ONE merge commit whose parents are exactly those two. Anything else
    landed unscanned and untested, and is listed (at most 20). Unknown is said, never returned as []."""
    if not (is_full_id(head) and is_full_id(incoming) and is_full_id(after)):
        return ["<unknown: a commit id is missing>"]
    rc, out, _ = _git(["rev-list", "--parents", after, "--not", head, incoming], cwd=cwd)
    if rc:
        return ["<unknown: git could not list the commits>"]
    extra = []
    for ln in out.splitlines():
        parts = ln.split()
        if parts and not (parts[0] == after and len(parts) == 3 and set(parts[1:]) == {head, incoming}):
            extra.append(parts[0])
    rc_a, _, _ = _git(["merge-base", "--is-ancestor", incoming, after], cwd=cwd)
    if rc_a:
        extra.append("<the tested commit %s is not in what landed>" % incoming[:12])
    return extra[:20]


def apply(info, dry):
    """Hand off to COVENANT_ADOPT_UPDATER (the stop-all/merge/start-all/health-check-all/rollback script).
    Only reached when ARMED + GO. This tool does NOT merge the live repo itself -- the updater does.

    NOTHING HERE MAKES THE UPDATER'S MERGE THE ONE THAT WAS TESTED (A453). An updater that fetches again and
    merges the branch by name lands whatever that name means at that moment. So the tested commit's full id is
    handed over as COVENANT_ADOPT_TESTED (and this node's as COVENANT_ADOPT_FROM) for an updater that merges by
    id, and when the updater returns, `untested` lists every commit that landed and was not tested. A non-empty
    list is reported as an error (exit 2); undoing it is the updater's and the operator's job."""
    steps = {"rollback_point": info["head"], "updater": UPDATER}
    if not UPDATER or not os.path.isfile(UPDATER):
        steps.update({"error": "COVENANT_ADOPT_UPDATER not set or missing -- not applying", "applied": False})
        return steps
    if dry:
        steps["dry"] = "would run %s (stop A/B/C, merge %s, restart, health-check, rollback on failure)" % (
            os.path.basename(UPDATER), TRACKED)
        return steps
    cmd = (["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", UPDATER]
           if UPDATER.lower().endswith(".ps1") else [sys.executable, UPDATER])
    rc, out = _run(cmd, REPO, 1200, env=dict(os.environ, COVENANT_ADOPT_TESTED=str(info.get("incoming") or ""),
                                              COVENANT_ADOPT_FROM=str(info.get("head") or "")))
    after = _resolve("HEAD")
    steps["updater_tail"] = [l.strip() for l in out.splitlines() if l.strip()][-10:]
    steps["after"] = after[:12]
    steps["applied"] = rc == 0 and bool(after) and after != info["head"]
    if after != info["head"]:
        steps["untested"] = untested_commits(info["head"], info.get("incoming"), after)
        if steps["untested"]:
            steps["warning"] = "what landed is NOT only what the gate tested: read `untested`"
    steps["updater_rc"] = rc
    return steps


def _record(result):
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(LEDGER, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"t": time.strftime("%Y-%m-%dT%H:%M:%S%z"), **result}) + "\n")
    except OSError:
        pass


def pipeline(do_apply, dry):
    info = detect()
    if info.get("error"):                                        # could not read the remote: say so, exit 2
        r = {"decision": "ERROR", "detail": info["error"], "applied": False, **info}
        _record(r)
        return r, 2
    if info.get("behind") == 0 and not info.get("changed_files"):
        r = {"decision": "NONE", "detail": "already current with %s" % TRACKED, **info}
        _record(r)
        return r, 3
    wt, merge_detail = build_candidate(info)
    try:
        cls, sens = classify(info["changed_files"])
        if wt:
            scan_info = scan(wt, info["head"])
            test_info = differential_test(wt, info["head"])
        else:
            scan_info = {"state": "skipped (conflict)"}; test_info = {"ok": False, "new_failures": ["conflict"]}
        decision, reasons = decide(cls, sens, scan_info, test_info, bool(wt), info.get("tracked_shadowed") or "")
        kill = os.path.isfile(KILL_SWITCH)
        over_cap = _applied_today() >= MAX_PER_DAY
        result = {"decision": decision, "reasons": reasons, "sensitivity": cls, "sensitive_hits": sens,
                  "merge": merge_detail, "scan": scan_info, "test": test_info,
                  "behind": info.get("behind"), "ahead": info.get("ahead"),
                  "changed_files": info["changed_files"], "incoming_commits": info["incoming_commits"],
                  "armed": AUTO, "kill_switch": kill, "over_daily_cap": over_cap, "head": info["head"],
                  "incoming": info["incoming"]}
        if decision == "GO" and do_apply and AUTO and not kill and not over_cap:
            result["apply"] = apply(info, dry)
            result["applied"] = bool(result["apply"].get("applied"))
        else:
            result["applied"] = False
            if decision == "GO" and not do_apply:
                result["note"] = "GO -- scan-only, nothing applied"
            elif decision == "GO" and not AUTO:
                result["note"] = "GO but PROPOSE-only (not armed): apply on the operator's word"
            elif decision == "GO" and (kill or over_cap):
                result["note"] = "GO but held: " + ("kill-switch present" if kill else "daily cap reached")
        _record(result)
        if (result.get("apply") or {}).get("untested"):
            return result, 2
        return result, (0 if decision == "GO" else 1)
    finally:
        _cleanup(wt)


def digest(n=25):
    rows = []
    try:
        for ln in open(LEDGER, encoding="utf-8"):
            if ln.strip():
                rows.append(json.loads(ln))
    except OSError:
        return {"entries": 0, "note": "no ledger yet at %s" % LEDGER, "armed": AUTO, "last": None}
    recent = rows[-n:]
    return {"ledger": LEDGER, "total_runs": len(rows), "showing": len(recent),
            "applied": [{"t": r.get("t"), "to": (r.get("apply") or {}).get("after")} for r in recent if r.get("applied")],
            "held": [{"t": r.get("t"), "why": "; ".join(r.get("reasons", []))[:120]} for r in recent if r.get("decision") == "NO-GO"][-8:],
            "errors": [{"t": r.get("t"), "why": str(r.get("detail"))[:120]} for r in recent if r.get("decision") == "ERROR"][-8:],
            "last": recent[-1].get("decision") if recent else None, "armed": AUTO}


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=("scan", "run", "digest"))
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if a.action == "digest":
        d = digest()
        print(json.dumps(d, indent=1) if a.json else
              "covenant_adopt digest -- %s run(s), last: %s, armed=%s" % (d.get("total_runs"), d.get("last"), d.get("armed")))
        return 0
    result, code = pipeline(do_apply=(a.action == "run"), dry=a.dry)
    if a.json:
        print(json.dumps(result, indent=1))
    else:
        print("decision: %s  (%s behind, %s)" % (result.get("decision"), result.get("behind"), result.get("sensitivity", "-")))
        for r in result.get("reasons", []):
            print("  - " + r)
        if result.get("note"):
            print("  " + result["note"])
        if result.get("decision") == "ERROR":
            print("  " + str(result.get("detail")))
        if (result.get("apply") or {}).get("untested"):
            print("  LANDED UNTESTED: " + ", ".join(str(c)[:12] for c in result["apply"]["untested"]))
    return code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
