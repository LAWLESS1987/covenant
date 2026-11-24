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
  look back-> (A452, advisory) when the run CONTRADICTS a clean adoption -- an unclean merge, a scan hit, a newly
              failing gate, an apply that did not land; never the deliberate HIGH hold -- this checkout's record
              of past errors (KNOWN_ISSUES headers, the tombstones) is searched with words from the run, and the
              closest entries go into the result, the ledger line and the digest. It changes no decision.

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
# A452: the record's own readers, loaded when the gate STARTS -- before any apply can change the file on disk.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import lookback_index as LI
except Exception:                                                 # noqa: BLE001 -- a checkout without it still gates
    LI = None
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


_GENERATED = ("MANIFEST.sha256", "docs/LOOKBACK_INDEX.md")
_CONFLICT = "merge conflict (human needed): "


def conflict_files(unmerged):
    """(hand-written files, generated files) that `git ls-files -u` says are conflicted, each sorted."""
    paths = sorted({ln.split("\t")[-1].strip() for ln in str(unmerged).splitlines() if ln.strip()})
    return [p for p in paths if p not in _GENERATED], [p for p in paths if p in _GENERATED]


def conflict_detail(unmerged):
    """The reason for a conflicted merge, for a person: the files that conflict, hand-written ones first.

    A452 (2026-11-18). This was the FIRST line of `git ls-files -u`, cut at 100 characters: one path, in git's
    order. On the only conflicted run on record (2026-11-18 08:37) that path was MANIFEST.sha256, a generated
    file that conflicts on every merge, while the files a person had to resolve went unnamed -- so the look back
    was aimed at the manifest. Generated files are named last, and only so the count is honest.

    This is PROSE. The list itself travels in the result as `merge_conflicts` and is never parsed back out of
    this string: the first version did parse it, and a non-author read showed "a,b.py" coming back as two files."""
    real, gen = conflict_files(unmerged)
    said = ", ".join(real[:8]) + (" (+%d more)" % (len(real) - 8) if len(real) > 8 else "")
    if gen:
        said += " [generated, also conflicted: %s]" % ", ".join(gen)
    return _CONFLICT + said


def conflict_paths(merge_detail):
    """For a ledger line from BEFORE A452 only, which carries `<mode> <sha> <stage>\\t<path>`: that one path,
    unless it is a generated file. Anything else gives no keys, never guessed ones."""
    s = str(merge_detail or "")
    if not s.startswith(_CONFLICT) or "\t" not in s:
        return []
    return [p for p in [s.split("\t")[-1].strip()] if p and p not in _GENERATED]


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
        only_generated = all(p.split("\t")[-1] in _GENERATED
                             for p in unmerged.splitlines() if p.strip())
        if only_generated:
            for p in _GENERATED:
                _git(["checkout", "--theirs", p], cwd=wt, timeout=60)
                _git(["add", p], cwd=wt, timeout=60)
        else:
            _git(["merge", "--abort"], cwd=wt, timeout=120)
            _cleanup(wt)
            info["merge_conflicts"] = conflict_files(unmerged)[0]      # the list, beside the prose (A452)
            return None, conflict_detail(unmerged)
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
        return {"ok": False, "new_failures": [_NO_REFERENCE], "candidate_failing": []}
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


# ---------------------------------------------------------------- contradictions and the look back (A452) --
# His words, 2026-11-18, on whether a change to the core should hold for his word (typed in the TETSU session,
# relayed verbatim; his go for building it into THIS gate, typed here the same day, was "Build it locally"):
#     "keep it auto, but if something contradicts, use the tombstones to figure out where it went wrong."
# So classify() is unchanged, and this is added BESIDE the gate: when a run contradicts a clean adoption, the
# record of past errors is searched with words from the run, and the closest entries travel with the result,
# the ledger line and the digest. It is ADVISORY. It never turns a NO-GO into a GO or a GO into a NO-GO, it
# never raises into the pipeline, and it uses no model. The shape is node D's (noded/safe_integrate.py, tetsu
# 3ad7c61), built there the same day on the same words.
#
# WHAT IT CANNOT SEE. It reads the record's HEADER LINES and the tombstones' claim and truth, not entry bodies:
# an error whose header does not name the file, gate or number that tripped is not found. A hit is a POINTER
# (CLAUDE.md rule 7): open the line before relying on it.
#
# WHOSE RECORD, AND WHOSE WORDS (the TETSU session's non-author read of #87, 2026-11-18, every point reproduced).
#   - The record is read from the COMMIT THE RUN STARTED AT (`git show <head>:docs/...`), never from the working
#     tree. The first version read the working tree and said it searched "this checkout's record, never the
#     incoming one" (retracted: A452-LOOKBACK-NEVER-INCOMING in docs/RETRACTED.json). After an apply that failed with HEAD already moved, the working tree IS the incoming one: a
#     planted header describing that very failure as known came back as its pointer. No commit to read from means
#     "unreadable", said out loud -- never a fall back to the files on disk. The record's readers
#     (tools/lookback_index.py) are loaded when this module is, before any apply, for the same reason.
#   - The search WORDS come from the merge under test: its failing names, its commit subjects, its file names. So
#     its sender can influence WHICH of this checkout's entries are shown, never what they say. Each hit says
#     where its words came from, and hits supported by nothing that tripped are capped at SENDER_ONLY_MAX.
LOOKBACK_TOP = 5
SENDER_ONLY_MAX = 2
_WORDS = re.compile(r"[a-z0-9_]+")
_ANUM = re.compile(r"(?<![a-z0-9])a(\d{1,4}[a-z]?)(?![a-z0-9])")
# A WHOLE object id, never an abbreviation. Git resolves a short id as a REF NAME before an object id, so a tag
# named after this node's 12-character HEAD, arriving with the change, makes "<head12>:path" read the INCOMING
# tree (the TETSU session's third read of #87, 2026-11-19, reproduced here). A whole id cannot be shadowed.
_SHA = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")
_GATE_ID = re.compile(r"G\d+")                  # as _check_gates reads one; a suite it reads always ends ".py"
_NO_REFERENCE = "<no reference worktree>"       # differential_test's own placeholder, not a suite (pinned by CA1)
# Words every header carries: matching on them would rank by nothing.
_STOP = frozenset(("covenant", "test", "tests", "tools", "docs", "ops", "main", "init", "the", "and", "for",
                   "not", "with", "from", "that", "this", "py", "md", "json"))
_ORIGINS = ("tripped", "new_name", "subject", "changed")


def contradictions(result):
    """What in a run CONTRADICTS a clean adoption: [{"kind", "detail", "keys", "paths"}], `keys` being what
    tripped (a file, a scan pattern, a gate, a suite) and `paths` the ones among them that are FILE PATHS: a
    scan hit's file, a conflicted path, a failing suite. The rest are this tool's own words (a pattern label, a
    gate id). Which is which is decided here, by where each came from, never later by how it is spelled. A pure
    function of the result, so it reads old ledger lines too -- and an odd one (a `scan` that is not an object,
    say) reads as nothing rather than raising.

    The deliberate HIGH hold is NOT one: a security-sensitive diff waiting for his word is the gate working as
    he chose, not something that went wrong. Nor is an already-current run, a dry apply, or an apply that landed."""
    out = []
    if not isinstance(result, dict) or result.get("decision") in (None, "NONE"):
        return out
    if result.get("decision") == "ERROR":                       # A453: the remote could not be read; nothing was judged
        return [{"kind": "error", "detail": str(result.get("detail") or "")[:200], "keys": [], "paths": []}]

    def obj(key):
        v = result.get(key)
        return v if isinstance(v, dict) else {}

    def lst(v):
        return v if isinstance(v, list) else []

    merge = str(result.get("merge") or "")
    merged = merge.startswith("merged cleanly")
    if not merged:
        listed = result.get("merge_conflicts")
        keys = [str(p) for p in listed] if isinstance(listed, list) else conflict_paths(merge)
        out.append({"kind": "merge", "detail": merge[:200] or "no candidate was built", "keys": keys,
                    "paths": list(keys)})
    scan_info = obj("scan")
    state = str(scan_info.get("state") or "")
    if state == "hits":
        hits = [h for h in lst(scan_info.get("hits")) if isinstance(h, dict)]
        labels = {str(h["pattern"]) for h in hits if h.get("pattern")}
        files = {str(h["file"]) for h in hits if h.get("file")}
        out.append({"kind": "scan_hit", "keys": sorted(labels | files), "paths": sorted(files - labels),
                    "detail": "; ".join("%s in %s" % (h.get("pattern"), h.get("file")) for h in hits[:5])[:200]})
    elif state == "error":
        out.append({"kind": "scan_error", "detail": str(scan_info.get("detail") or "")[:160], "keys": [], "paths": []})
    test_info = obj("test")
    if merged and test_info and not test_info.get("ok", True):   # an unmerged run carries a placeholder, not a measurement
        new = [str(f) for f in lst(test_info.get("new_failures"))]
        out.append({"kind": "new_failing_gate", "detail": ", ".join(new)[:200], "keys": new,
                    "paths": [f for f in new if not _GATE_ID.fullmatch(f)
                              and f not in (_NO_REFERENCE, CHECK_UNFINISHED)]})
    ap = result.get("apply")
    if isinstance(ap, dict) and "dry" not in ap and not ap.get("applied"):
        out.append({"kind": "apply_failed", "keys": [], "paths": [],
                    "detail": str(ap.get("error") or "updater rc=%s; HEAD after is %s" % (ap.get("updater_rc"), ap.get("after")))[:200]})
    return out


def _stem(path):
    return os.path.basename(str(path).replace("\\", "/")).rsplit(".", 1)[0].lower()


def _exists_at(head):
    """A function saying whether a path is tracked at commit `head` in REPO. `head` must be a WHOLE commit id:
    with a short one, or none, it vouches for nothing. The working tree is never asked: after an apply it holds
    what arrived. The commit's paths are listed ONCE, on the first ask (`git ls-tree -r -z`): one process however
    many names are asked, where one `git cat-file -e` per name took 302 processes for 300 new files (the TETSU
    session's measurement), and no `<rev>:<path>` is built from a name the sender chose."""
    tracked = []

    def exists(path):
        if not _SHA.fullmatch(str(head or "")):
            return False
        if not tracked:
            names = frozenset()
            try:
                r = subprocess.run(["git", "-C", REPO, "ls-tree", "-r", "-z", "--name-only", "--full-tree", head],
                                   capture_output=True, timeout=120, creationflags=_NOWIN)
                if r.returncode == 0:
                    names = frozenset(r.stdout.decode("utf-8", "surrogateescape").split("\0")) - {""}
            except (OSError, subprocess.SubprocessError):
                pass
            tracked.append(names)
        return str(path).replace("\\", "/") in tracked[0]
    return exists


def _terms(result, contras, exists=None):
    """{word: (weight, origin)}. What TRIPPED weighs 3 (its file or gate name, and any A-number inside it); an
    A-number in an incoming commit's subject weighs 2; a file that merely changed weighs 1, as do the separate
    words of what tripped. The heaviest use of a word wins, so naming a thing twice does not rank it higher.

    A FILE'S NAME COUNTS AS WHAT TRIPPED ONLY IF THE FILE WAS THERE BEFORE THE RUN (`exists(path)`; None vouches
    for every path, for a hand run over a directory). The TETSU session's re-read at b2b4268: five failing
    suites that ARRIVED with the merge, test_a12_x.py ... test_a441_x.py, gave five pointers, each labelled
    "tripped" at weight 3, and one new file named after five entries did the same alone. A suite that existed
    and now fails is evidence; a name that arrives with the merge is its sender's word. Such a name gets the
    origin "new_name" and a subject's weight, and falls under the same cap.

    WHICH KEYS ARE FILES is said by the contradiction (`paths`), from where each key came. The version at 41b85a7
    decided by spelling -- a key with a dot or a slash was a file -- and its third read (2026-11-19) walked past
    it: a new file at the repository root with no extension, a12_a34_a56_a78_a441, was taken for the gate's own
    word and gave five pointers labelled "tripped" (retracted: A452-NEW-NAME-EVERY-FILE in docs/RETRACTED.json). A
    contradiction that does not say which of its keys are paths has every key asked."""
    terms = {}
    exists = exists or (lambda _path: True)

    def add(tok, w, origin):
        tok = tok.lower()
        if len(tok) >= 2 and tok not in _STOP and w > terms.get(tok, (0, ""))[0]:
            terms[tok] = (w, origin)

    for c in contras:
        keys = c.get("keys") or []
        paths = set(c["paths"]) if isinstance(c.get("paths"), list) else set(keys)
        for k in keys:
            stem = _stem(k)
            w, origin = (2, "new_name") if k in paths and not exists(k) else (3, "tripped")
            add(stem, w, origin)
            for m in _ANUM.finditer(stem.replace("_", " ")):
                add("a" + m.group(1), w, origin)
            for part in stem.split("_"):
                if len(part) >= 4:
                    add(part, 1, origin)
    for subj in result.get("incoming_commits") or []:
        for m in _ANUM.finditer(str(subj).lower()):
            add("a" + m.group(1), 2, "subject")
    for f in result.get("changed_files") or []:
        add(_stem(f), 1, "changed")
    return terms


def lookback_terms(result, contras):
    """{word: weight}, for showing."""
    return {t: w for t, (w, _o) in _terms(result, contras).items()}


def _at_commit(head, rel):
    """(text, None) for a tracked file as it is at commit `head` in REPO, else (None, why). Bytes from git, read
    as UTF-8: the working tree is never opened."""
    if not _SHA.fullmatch(str(head or "")):
        return None, ("no pre-run commit in the result" if not head else
                      "the pre-run commit in the result is not a whole id (%d characters): not read" % len(str(head)))
    try:
        r = subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (head, rel)], capture_output=True, timeout=120,
                           creationflags=_NOWIN)
    except (OSError, subprocess.SubprocessError) as e:
        return None, type(e).__name__
    if r.returncode:
        return None, "not readable at commit %s" % str(head)[:12]
    try:
        return r.stdout.decode("utf-8"), None
    except ValueError as e:
        return None, type(e).__name__


def _from_dir(root, rel):
    try:
        with open(os.path.join(root, *rel.split("/")), encoding="utf-8") as fh:
            return fh.read(), None
    except (OSError, ValueError) as e:
        return None, type(e).__name__


def lookback(result, contras=None, root=None, top=LOOKBACK_TOP, exists=None):
    """Search the record of past errors with words from a run that contradicted. Returns {"searched",
    "unreadable", "terms", "hits", "note"}; `hits` are the closest record entries and tombstones, each with
    where it is, which words matched, where those words came from, and its score. No contradiction: nothing is
    searched.

    The record is the one at the commit the run started at (`result["head"]`); `root` names a directory to read
    instead, for a test or a hand run. Matching is by WHOLE WORD (`stake` does not match `mistaken`). A record
    that cannot be read is named in `unreadable` and the other is still searched: a look back that hid a missing
    record would read as "nothing like this has happened before"."""
    contras = contradictions(result) if contras is None else contras
    # The note's last sentence was not true of every file at 41b85a7 (A452-NEW-NAME-EVERY-FILE in docs/RETRACTED.json):
    # a new file with no dot and no slash in its name was labelled tripped. It is true now that `paths` says which.
    out = {"searched": [], "unreadable": [], "terms": {}, "hits": [],
           "note": "pointers, not findings: open the line before relying on it. The search words come from the "
                   "merge under test (what failed, its commit subjects, its file names), so its sender can "
                   "influence which entries are shown, never what they say. A failing file that was not there "
                   "before the run is labelled new_name, not tripped."}
    if not contras:
        return out
    if LI is None:
        out["unreadable"].append("tools/lookback_index.py could not be loaded when the gate started")
        return out
    if root is None:
        head = str(result.get("head") or "")
        read, where = (lambda rel: _at_commit(head, rel)), "at commit %s" % head[:12]
        exists = exists or _exists_at(head)
    else:
        read, where = (lambda rel: _from_dir(root, rel)), "in %s" % os.path.basename(str(root).rstrip("\\/"))
    terms = _terms(result, contras, exists)
    out["terms"] = dict(sorted(((t, w) for t, (w, _o) in terms.items()), key=lambda kv: (-kv[1], kv[0]))[:20])
    entries, heads, tombs = [], [], []
    text, why = read("docs/KNOWN_ISSUES.md")
    if text is None:
        out["unreadable"].append("docs/KNOWN_ISSUES.md %s: %s" % (where, why))
    else:
        entries, heads = LI.entries(text), text.splitlines()
        out["searched"].append("docs/KNOWN_ISSUES.md %s (header lines)" % where)
    text, why = read("docs/RETRACTED.json")
    if text is None:
        out["unreadable"].append("docs/RETRACTED.json %s: %s" % (where, why))
    else:
        try:
            tombs = LI.tombstones(json.loads(text), {e["id"] for e in entries} if entries else None)
            out["searched"].append("docs/RETRACTED.json %s (claim and truth)" % where)
        except (ValueError, AttributeError, TypeError) as e:
            out["unreadable"].append("docs/RETRACTED.json %s: %s" % (where, type(e).__name__))
    scored = []

    def weigh(text, rid, hit):
        toks = set(_WORDS.findall(text.lower()))
        matched = sorted(t for t in terms if t in toks)
        if matched:
            score = sum(terms[t][0] for t in matched)
            frm = {o: [t for t in matched if terms[t][1] == o] for o in _ORIGINS}
            scored.append((score, LI._num(rid), dict(hit, matched=matched, score=score,
                                                     matched_from={o: ts for o, ts in frm.items() if ts})))

    for e in entries:
        # the whole header LINE, not only its bracketed title: 163 of 439 entries had a title of three words or
        # fewer on 2026-11-18 (A445's is "security"), with the file named after the bracket.
        weigh(heads[e["line"] - 1], e["id"],
              {"where": "docs/KNOWN_ISSUES.md", "line": e["line"], "id": e["id"], "date": e["date"],
               "status": e["status"], "title": LI._short(e["title"], 140)})
    for t in tombs:
        weigh(" ".join((t["id"], t["entry"], t["claim"], t["truth"])), t["entry"] or t["id"],
              {"where": "docs/RETRACTED.json", "id": t["id"], "entry": t["entry"], "claim": LI._short(t["claim"], 140)})
    scored.sort(key=lambda s: (s[0], s[1]), reverse=True)       # closest first; among equals, the newest entry
    sender_only = 0
    for _score, _num, h in scored:
        if len(out["hits"]) >= max(0, int(top)):
            break
        if "tripped" not in h["matched_from"]:                  # only new names, subjects, changed files: the sender's words
            if sender_only >= SENDER_ONLY_MAX:
                continue
            sender_only += 1
        out["hits"].append(h)
    return out


def seen_before(contras, rows):
    """For each contradiction, how many EARLIER runs in the ledger carried the same kind tripped by the same
    thing (rule 10: a second time is a recurrence, and the earlier one did not stop it). An odd row reads as
    no contradiction (contradictions() does not raise on one), so it cannot void the count."""
    earlier = [(r.get("t") if isinstance(r, dict) else None, contradictions(r)) for r in rows]
    out = []
    for c in contras:
        n, first, last = 0, None, None
        for t, past in earlier:
            if any(pc["kind"] == c["kind"] and (not c["keys"] or set(pc["keys"]) & set(c["keys"])) for pc in past):
                n, first, last = n + 1, first or t, t
        out.append({"kind": c["kind"], "earlier_runs": n, "first": first, "last": last})
    return out


def _ledger_rows():
    rows = []
    try:
        with open(LEDGER, encoding="utf-8") as fh:
            for ln in fh:
                try:
                    d = json.loads(ln)
                except ValueError:                                # one torn line never drops the rest
                    continue
                if isinstance(d, dict):
                    rows.append(d)
    except OSError:
        pass
    return rows


def annotate(result, rows=None, root=None):
    """Add `contradictions` to a result and, when there are any, `lookback` and `seen_before`. Advisory: it never
    touches the decision, and a failure inside it is recorded in the result instead of raised."""
    try:
        contras = contradictions(result)
    except Exception as e:                                        # noqa: BLE001 -- advisory code never stops the gate
        result["contradictions"] = [{"kind": "unreadable_result", "detail": type(e).__name__, "keys": []}]
        return result
    result["contradictions"] = contras
    if not contras:
        return result
    try:
        result["lookback"] = lookback(result, contras, root=root)
    except Exception as e:                                        # noqa: BLE001
        result["lookback"] = {"error": "%s: %s" % (type(e).__name__, str(e)[:120]), "hits": []}
    try:
        result["seen_before"] = seen_before(contras, _ledger_rows() if rows is None else rows)
    except Exception as e:                                        # noqa: BLE001
        result["seen_before"] = [{"error": type(e).__name__}]
    return result


def annotate_and_record(result):
    """Annotate, then record -- and record even when the look back is interrupted. The first version annotated
    before recording with nothing between: a Ctrl-C or a kill inside it left a run, possibly one whose apply had
    already landed, with no ledger line at all."""
    try:
        annotate(result)
    finally:
        _record(result)


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
        annotate_and_record(r)
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
        if "merge_conflicts" in info:
            result["merge_conflicts"] = info["merge_conflicts"]
        annotate_and_record(result)     # A452: after the decision and any apply; advisory; the run is recorded either way
        ap = result.get("apply")
        if isinstance(ap, dict) and (ap.get("untested") or ("dry" not in ap and not ap.get("applied"))):
            return result, 2                # untested work landed, or an apply was attempted and did not land:
                                            # the exit code is no longer the decision's (it read 0 for both)
        return result, (0 if decision == "GO" else 1)
    finally:
        _cleanup(wt)


def digest(n=25):
    if not os.path.isfile(LEDGER):
        return {"entries": 0, "note": "no ledger yet at %s" % LEDGER, "armed": AUTO, "last": None}
    rows = _ledger_rows()           # A452: a torn line is skipped; it used to raise out of the whole digest
    recent = rows[-n:]

    def held(r):
        # A452: what contradicted, and where the record says to look. Read from the line as it was written, and
        # worked out for a line from before the look back existed (its pointers are then not on file: none shown).
        contras = r.get("contradictions")
        if not isinstance(contras, list):
            contras = contradictions(r)                           # reads an odd row as nothing; it does not raise
        return {"t": r.get("t"), "why": "; ".join(r.get("reasons", []))[:120],
                "contradictions": [c.get("kind") for c in contras],
                "look_at": [h.get("id") for h in ((r.get("lookback") or {}).get("hits") or [])[:3]]}

    return {"ledger": LEDGER, "total_runs": len(rows), "showing": len(recent),
            "applied": [{"t": r.get("t"), "to": (r.get("apply") or {}).get("after")} for r in recent if r.get("applied")],
            "held": [held(r) for r in recent if r.get("decision") == "NO-GO"][-8:],
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
        for c, sb in zip(result.get("contradictions") or [], result.get("seen_before") or []):
            again = (" -- seen in %d earlier run(s), first %s" % (sb["earlier_runs"], sb.get("first"))
                     if sb.get("earlier_runs") else "")
            print("  contradiction: %s: %s%s" % (c.get("kind"), c.get("detail"), again))
        lb = result.get("lookback") or {}
        for u in lb.get("unreadable") or []:
            print("  look back: COULD NOT READ %s" % u)
        if lb.get("error"):
            print("  look back: failed (%s); the decision above stands without it" % lb["error"])
        for h in lb.get("hits") or []:
            print("  look at: %s%s  %s  [%s]  %s" % (
                h.get("where"), (" line %s" % h["line"]) if h.get("line") else "", h.get("id"),
                "; ".join("%s: %s" % (o, ", ".join(ts)) for o, ts in (h.get("matched_from") or {}).items()),
                h.get("title") or h.get("claim") or ""))
        if lb.get("hits"):
            print("  (%s)" % lb.get("note"))
    return code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
