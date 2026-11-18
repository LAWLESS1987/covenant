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
        _record(result)
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
    return code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
