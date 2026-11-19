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
    r"machine|grid|consent|headscale|redund|failover|takeover)", re.I)

# Backdoor patterns over ADDED lines only (node D's set, reused). Routine subprocess/urllib in existing code
# never appears here -- only the lines the merge adds are read. A hit is HOLD-for-a-human, not a proven backdoor.
_PATTERNS = [
    ("listener_all_ifaces", re.compile(r"bind\(\(?\s*['\"]?0\.0\.0\.0|host\s*=\s*['\"]0\.0\.0\.0")),
    ("reverse_shell", re.compile(r"(/bin/sh['\"]?\s*,?\s*['\"]-i|cmd\.exe.{0,40}/c\b.{0,40}(socket|connect)|pty\.spawn)")),
    ("exec_of_decoded", re.compile(r"(b64decode|b85decode|unhexlify|fromhex).{0,80}(exec|eval)\(|(exec|eval)\(.{0,40}(decode|loads|\.read)\(")),
    ("persistence_new", re.compile(r"(schtasks.{0,40}/create|New-Service|Register-ScheduledTask|reg(\.exe)?\s+add.{0,60}Run|crontab\s+-|systemctl\s+enable)")),
    ("cred_capture", re.compile(r"(id_rsa|id_ed25519|CryptUnprotectData|DPAPI|/\.ssh/|Authorization['\"]?\s*\].{0,40}(post|send|write))")),
]


def _git(args, cwd=REPO, timeout=180):
    r = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True, timeout=timeout, creationflags=_NOWIN)
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


def _run(cmd, cwd, timeout):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, creationflags=_NOWIN)
    return r.returncode, ((r.stdout or "") + (r.stderr or "")).strip()


def detect():
    _git(["fetch", "--quiet", "origin"], timeout=180)
    _rc, head, _ = _git(["rev-parse", "HEAD"])
    _rc2, lr, _ = _git(["rev-list", "--left-right", "--count", "%s...HEAD" % TRACKED])
    behind = ahead = None
    if len(lr.split()) == 2:
        behind, ahead = (int(x) for x in lr.split())
    _rc3, files, _ = _git(["diff", "--name-only", "HEAD...%s" % TRACKED])
    _rc4, commits, _ = _git(["log", "--oneline", "HEAD..%s" % TRACKED])
    return {"head": head[:12], "behind": behind, "ahead": ahead,
            "changed_files": [f for f in files.splitlines() if f.strip()],
            "incoming_commits": commits.splitlines()}


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


def scan(worktree, base_sha):
    """Backdoor scan over the lines the candidate ADDS (git diff base..HEAD inside the scratch)."""
    rc, patch, err = _git(["diff", base_sha, "HEAD"], cwd=worktree)
    if rc:
        return {"state": "error", "detail": err[:160], "hits": []}
    cur, added = None, []
    for raw in patch.splitlines():
        if raw.startswith("+++ b/"):
            cur = raw[6:]
        elif raw.startswith("+") and not raw.startswith("+++"):
            added.append((cur, raw[1:]))
    hits = scan_lines(added)
    return {"state": "hits" if hits else "clean", "hits": hits}


def _check_gates(cwd):
    """covenant_one.py --check -> the SET of gates it reports failing. --check exits 1 on the live HEAD too
    (G5 ethics-judge-down, a stale sweep, a manifest drift), so an absolute pass is the wrong bar; the caller
    compares candidate vs a HEAD reference and blocks only on a NEW failure."""
    _rc, said = _run([sys.executable, "covenant_one.py", "--check"], cwd, 1200)
    failing = set()
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
    """Scratch worktree of HEAD, merge TRACKED into it, commit a clean tree. Conflict -> (None, reason)."""
    wt = _add_worktree("HEAD")
    if wt is None:
        return None, "worktree add failed"
    _git(["-c", "user.name=covenant-adopt", "-c", "user.email=node@covenant.local",
          "merge", "--no-ff", "--no-edit", TRACKED], cwd=wt, timeout=300)
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
    return wt, "merged cleanly in scratch"


def differential_test(wt, head_sha):
    """APPLES TO APPLES: check the candidate and a HEAD reference in fresh worktrees; a gate that fails on
    BOTH (gitignored on-disk state) cancels. Only a gate the MERGE newly breaks blocks."""
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


def decide(cls, sens_hits, scan_info, test_info, merge_ok):
    reasons = []
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
_SHA = re.compile(r"[0-9a-f]{7,40}")
# Words every header carries: matching on them would rank by nothing.
_STOP = frozenset(("covenant", "test", "tests", "tools", "docs", "ops", "main", "init", "the", "and", "for",
                   "not", "with", "from", "that", "this", "py", "md", "json"))
_ORIGINS = ("tripped", "subject", "changed")


def contradictions(result):
    """What in a run CONTRADICTS a clean adoption: [{"kind", "detail", "keys"}], `keys` being what tripped (a
    file, a scan pattern, a gate, a suite). A pure function of the result, so it reads old ledger lines too --
    and an odd one (a `scan` that is not an object, say) reads as nothing rather than raising.

    The deliberate HIGH hold is NOT one: a security-sensitive diff waiting for his word is the gate working as
    he chose, not something that went wrong. Nor is an already-current run, a dry apply, or an apply that landed."""
    out = []
    if not isinstance(result, dict) or result.get("decision") in (None, "NONE"):
        return out

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
        out.append({"kind": "merge", "detail": merge[:200] or "no candidate was built", "keys": keys})
    scan_info = obj("scan")
    state = str(scan_info.get("state") or "")
    if state == "hits":
        hits = [h for h in lst(scan_info.get("hits")) if isinstance(h, dict)]
        keys = sorted({str(h["pattern"]) for h in hits if h.get("pattern")} | {str(h["file"]) for h in hits if h.get("file")})
        out.append({"kind": "scan_hit", "keys": keys,
                    "detail": "; ".join("%s in %s" % (h.get("pattern"), h.get("file")) for h in hits[:5])[:200]})
    elif state == "error":
        out.append({"kind": "scan_error", "detail": str(scan_info.get("detail") or "")[:160], "keys": []})
    test_info = obj("test")
    if merged and test_info and not test_info.get("ok", True):   # an unmerged run carries a placeholder, not a measurement
        new = [str(f) for f in lst(test_info.get("new_failures"))]
        out.append({"kind": "new_failing_gate", "detail": ", ".join(new)[:200], "keys": new})
    ap = result.get("apply")
    if isinstance(ap, dict) and "dry" not in ap and not ap.get("applied"):
        out.append({"kind": "apply_failed", "keys": [],
                    "detail": str(ap.get("error") or "updater rc=%s; HEAD after is %s" % (ap.get("updater_rc"), ap.get("after")))[:200]})
    return out


def _stem(path):
    return os.path.basename(str(path).replace("\\", "/")).rsplit(".", 1)[0].lower()


def _terms(result, contras):
    """{word: (weight, origin)}. What TRIPPED weighs 3 (its file or gate name, and any A-number inside it); an
    A-number in an incoming commit's subject weighs 2; a file that merely changed weighs 1, as do the separate
    words of what tripped. The heaviest use of a word wins, so naming a thing twice does not rank it higher."""
    terms = {}

    def add(tok, w, origin):
        tok = tok.lower()
        if len(tok) >= 2 and tok not in _STOP and w > terms.get(tok, (0, ""))[0]:
            terms[tok] = (w, origin)

    for c in contras:
        for k in c.get("keys") or []:
            stem = _stem(k)
            add(stem, 3, "tripped")
            for m in _ANUM.finditer(stem.replace("_", " ")):
                add("a" + m.group(1), 3, "tripped")
            for part in stem.split("_"):
                if len(part) >= 4:
                    add(part, 1, "tripped")
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
        return None, "no pre-run commit in the result"
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


def lookback(result, contras=None, root=None, top=LOOKBACK_TOP):
    """Search the record of past errors with words from a run that contradicted. Returns {"searched",
    "unreadable", "terms", "hits", "note"}; `hits` are the closest record entries and tombstones, each with
    where it is, which words matched, where those words came from, and its score. No contradiction: nothing is
    searched.

    The record is the one at the commit the run started at (`result["head"]`); `root` names a directory to read
    instead, for a test or a hand run. Matching is by WHOLE WORD (`stake` does not match `mistaken`). A record
    that cannot be read is named in `unreadable` and the other is still searched: a look back that hid a missing
    record would read as "nothing like this has happened before"."""
    contras = contradictions(result) if contras is None else contras
    out = {"searched": [], "unreadable": [], "terms": {}, "hits": [],
           "note": "pointers, not findings: open the line before relying on it. The search words come from the "
                   "merge under test (what failed, its commit subjects, its file names), so its sender can "
                   "influence which entries are shown, never what they say."}
    if not contras:
        return out
    if LI is None:
        out["unreadable"].append("tools/lookback_index.py could not be loaded when the gate started")
        return out
    terms = _terms(result, contras)
    out["terms"] = dict(sorted(((t, w) for t, (w, _o) in terms.items()), key=lambda kv: (-kv[1], kv[0]))[:20])
    if root is None:
        head = str(result.get("head") or "")
        read, where = (lambda rel: _at_commit(head, rel)), "at commit %s" % head[:12]
    else:
        read, where = (lambda rel: _from_dir(root, rel)), "in %s" % os.path.basename(str(root).rstrip("\\/"))
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
        if "tripped" not in h["matched_from"]:                  # nothing that tripped supports it: the sender's words
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


def apply(info, dry):
    """Hand off to COVENANT_ADOPT_UPDATER (the stop-all/merge/start-all/health-check-all/rollback script).
    Only reached when ARMED + GO. This tool does NOT merge the live repo itself -- the updater does, after the
    scratch pipeline proved the same merge is clean."""
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
    rc, out = _run(cmd, REPO, 1200)
    _rc, after, _ = _git(["rev-parse", "HEAD"])
    steps["updater_tail"] = [l.strip() for l in out.splitlines() if l.strip()][-10:]
    steps["after"] = after[:12]
    steps["applied"] = rc == 0 and after[:12] != info["head"]
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
    if info.get("behind") in (0, None) and not info.get("changed_files"):
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
        decision, reasons = decide(cls, sens, scan_info, test_info, bool(wt))
        kill = os.path.isfile(KILL_SWITCH)
        over_cap = _applied_today() >= MAX_PER_DAY
        result = {"decision": decision, "reasons": reasons, "sensitivity": cls, "sensitive_hits": sens,
                  "merge": merge_detail, "scan": scan_info, "test": test_info,
                  "behind": info.get("behind"), "ahead": info.get("ahead"),
                  "changed_files": info["changed_files"], "incoming_commits": info["incoming_commits"],
                  "armed": AUTO, "kill_switch": kill, "over_daily_cap": over_cap, "head": info["head"]}
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
