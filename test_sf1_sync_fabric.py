#!/usr/bin/env python3
"""
test_sf1_sync_fabric.py -- SF1 (A405, 2026-11-02): the highway's sync-fabric detectors and remedies, each
driven BOTH WAYS and proven red before green (CLAUDE.md rule 8). His words: "continue growing the mycelial
highway. Make it pave itself."

WHAT THE FABRIC IS. A unison feed on TETSU (:8800/unison) reads, for each repo, whether its github / hf /
website copies have reached a common target; two operator-armed, guarded, idempotent scheduled tasks act on
it (CovenantHFMirror -> Hugging Face, CovenantSiteAutoDeploy -> the website). The detectors below let the loop
SENSE that fabric and, in the ONE reversible case -- re-running an already-armed task -- reversibly heal it.

HERMETIC. Every feed is a dict fixture or a fake `get`; every scheduler read is a `tasks=` fixture or a fake
`run`; every remedy is a spy. No network, no PowerShell, no node. The cache is a temp file. So this measures
the RULES, not the machine, and the same file runs green on Linux CI and on the box.

THE LINE THAT DOES NOT MOVE is asserted, not assumed: a public GitHub push is PROPOSE_ONLY (github lag has no
auto remedy), a missing task is PROPOSE_ONLY (arming is config), and the feed's own repair is PROPOSE_ONLY
(it runs on TETSU). Only re-running an armed task is AUTO_REVERSIBLE.

    python test_sf1_sync_fabric.py
"""
from __future__ import annotations

import os
import sys
import tempfile
import time

import covenant_highway as H

results = []


def check(label, ok, detail=""):
    results.append((label, bool(ok)))
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}" + (f"  -- {detail}" if detail else ""))


def tmp_path(suffix):
    return tempfile.mktemp(suffix=suffix)


def feed(checked, repos, status="ok", interval=900):
    return {"status": status, "checked": checked, "interval_s": interval, "repos": repos}


def repo(target, github=None, hf=None, website=None):
    return {"target": target,
            "heads": {"github": github or target, "hf": hf or target, "website": website or target}}


def iso(dt_s):
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(dt_s))


def main():
    NOW = 1_793_650_000.0

    # ================================================================= SF1a: unison_feed_stale
    # UNKNOWN when unconfigured (the reader's blindness), PRESENT when configured-and-down, status, and age.
    unconfigured = lambda _u: (_ for _ in ()).throw(AssertionError("get should not be called when None"))
    r = H.detect_unison_feed_stale(get=lambda u: None, url=None)  # get returns None -> "configured, unreachable"
    check("SF1a a feed that will not answer is PRESENT (unreachable)",
          r["state"] == H.PRESENT and r["measured"].get("reachable") is False, str(r["measured"])[:90])

    # unconfigured: no url, no get, and no env/local file -> UNKNOWN (never OK). Force no URL.
    saved_url = os.environ.pop("COVENANT_UNISON_FEED", None)
    saved_local = H.UNISON_FEED_LOCAL
    try:
        H.UNISON_FEED_LOCAL = tmp_path("_nofeed.txt")             # a path that does not exist
        H._unison_feed_cache.update(at=0.0, feed=None, note="")   # defeat any warm cache
        r = H.detect_unison_feed_stale()
        check("SF1a no feed configured here is UNKNOWN, never OK",
              r["state"] == H.UNKNOWN and "no feed URL configured" in r["measured"].get("why", ""),
              str(r["measured"])[:90])
    finally:
        H.UNISON_FEED_LOCAL = saved_local
        if saved_url is not None:
            os.environ["COVENANT_UNISON_FEED"] = saved_url

    bad_status = feed(iso(NOW - 10), {}, status="starting")
    r = H.detect_unison_feed_stale(feed=bad_status, now=NOW)
    check("SF1a a feed whose status is not 'ok' is PRESENT", r["state"] == H.PRESENT, str(r["measured"].get("reasons")))

    old = feed(iso(NOW - 2000), {}, status="ok", interval=900)   # 2000s > 2x900
    r = H.detect_unison_feed_stale(feed=old, now=NOW)
    check("SF1a a reading older than 2x interval is PRESENT (stale)",
          r["state"] == H.PRESENT and any("over 2x" in x for x in r["measured"]["reasons"]), str(r["measured"]["reasons"]))

    fresh = feed(iso(NOW - 60), {}, status="ok", interval=900)
    r = H.detect_unison_feed_stale(feed=fresh, now=NOW)
    check("SF1a mutation: a fresh, status-ok feed CLEARS it (ABSENT)",
          r["state"] == H.ABSENT and not r["measured"]["reasons"], str(r["measured"]))

    # ================================================================= SF1b: sync_task_not_firing
    def task(present=True, state="Ready", result=0, interval_s=900, last_run=None):
        if last_run is None and present:
            last_run = NOW - 100
        return {"present": present, "state": state, "result": result, "interval_s": interval_s, "last_run": last_run}

    healthy = {"CovenantHFMirror": task(interval_s=7200, last_run=NOW - 1000),
               "CovenantSiteAutoDeploy": task(interval_s=900, last_run=NOW - 200)}
    r = H.detect_sync_task_not_firing(tasks=dict(healthy), now=NOW)
    check("SF1b two armed tasks firing on time, exit 0 -> ABSENT", r["state"] == H.ABSENT, str(r["measured"]))

    failed = dict(healthy)
    failed["CovenantHFMirror"] = task(interval_s=7200, last_run=NOW - 1000, result=1)
    r = H.detect_sync_task_not_firing(tasks=failed, now=NOW)
    check("SF1b a nonzero LAST RESULT fires it, naming the task",
          r["state"] == H.PRESENT and r["measured"]["not_firing"] == ["CovenantHFMirror"], str(r["measured"]))

    stale = dict(healthy)
    stale["CovenantSiteAutoDeploy"] = task(interval_s=900, last_run=NOW - 5000)   # >3x900
    r = H.detect_sync_task_not_firing(tasks=stale, now=NOW)
    check("SF1b a last run older than 3x the task's own interval fires it",
          r["state"] == H.PRESENT and r["measured"]["not_firing"] == ["CovenantSiteAutoDeploy"], str(r["measured"]))

    running = dict(healthy)
    running["CovenantHFMirror"] = task(interval_s=7200, last_run=NOW - 1000, result=0x41301)  # 'currently running'
    r = H.detect_sync_task_not_firing(tasks=running, now=NOW)
    check("SF1b a run in flight (0x41301) is not a failure -> ABSENT", r["state"] == H.ABSENT, str(r["measured"]))

    disabled = dict(healthy)
    disabled["CovenantHFMirror"] = task(state="Disabled", result=1, interval_s=7200, last_run=NOW - 999999)
    r = H.detect_sync_task_not_firing(tasks=disabled, now=NOW)
    check("SF1b a DISABLED task is the operator's choice, never flagged", r["state"] == H.ABSENT, str(r["measured"]))

    # a missing task is NOT this detector's finding (it belongs to sync_task_missing) -- the split that keeps
    # the re-run remedy from being graded against a condition it cannot clear.
    gone = {"CovenantHFMirror": {"present": False},
            "CovenantSiteAutoDeploy": task(interval_s=900, last_run=NOW - 200)}
    r = H.detect_sync_task_not_firing(tasks=gone, now=NOW)
    check("SF1b an ABSENT task is NOT 'not firing' here (that is sync_task_missing)",
          r["state"] == H.ABSENT, str(r["measured"]))

    r = H.detect_sync_task_not_firing(tasks=None, now=NOW) if os.name != "nt" else {"state": H.UNKNOWN}
    # On Windows the real scheduler is read; off Windows tasks=None -> UNKNOWN. Either way, UNKNOWN is honest.
    # (We assert the off-Windows contract; on Windows this line reads the live machine and is not asserted.)
    if os.name != "nt":
        check("SF1b off-Windows the scheduler cannot be read -> UNKNOWN, never OK", r["state"] == H.UNKNOWN)

    # ================================================================= SF1c: sync_task_missing
    r = H.detect_sync_task_missing(tasks={"CovenantHFMirror": {"present": True},
                                          "CovenantSiteAutoDeploy": {"present": True}})
    check("SF1c both expected tasks present -> ABSENT", r["state"] == H.ABSENT, str(r["measured"]))

    r = H.detect_sync_task_missing(tasks={"CovenantHFMirror": {"present": False},
                                          "CovenantSiteAutoDeploy": {"present": True}})
    check("SF1c an expected task gone entirely -> PRESENT (arming is config, no auto remedy)",
          r["state"] == H.PRESENT and r["measured"]["missing"] == ["CovenantHFMirror"], str(r["measured"]))

    # the optional pusher's absence is never flagged (it may not be armed yet)
    check("SF1c sync_task_missing never expects the optional CovenantRepoAutopush",
          "CovenantRepoAutopush" not in H.SYNC_TASKS_EXPECTED, str(H.SYNC_TASKS_EXPECTED))

    # ================================================================= SF1d: mirror_lag + cycle counting
    cp = tmp_path("_lag.json")
    tgt, behind = "a" * 40, "b" * 40
    # hf behind across 4 distinct readings: ABSENT through cycle 3, PRESENT at cycle 4 (>MIRROR_LAG_CYCLES=3)
    states = []
    for i in range(1, 5):
        f = feed(iso(NOW + i * 900), {"covenant": repo(tgt, hf=behind)})   # github/website == target; hf behind
        states.append(H.detect_mirror_lag(feed=f, cache_path=cp, now=NOW + i * 900)["state"])
    check("SF1d hf behind for <=3 feed readings is NOT yet a finding (a mirror mid-catch-up)",
          states[:3] == [H.ABSENT, H.ABSENT, H.ABSENT], str(states))
    r = H.detect_mirror_lag(feed=feed(iso(NOW + 5 * 900), {"covenant": repo(tgt, hf=behind)}),
                            cache_path=cp, now=NOW + 5 * 900)
    check("SF1d hf behind across >3 readings fires mirror_lag, naming CovenantHFMirror",
          r["state"] == H.PRESENT and r["measured"]["rerun_tasks"] == ["CovenantHFMirror"], str(r["measured"]))

    # mutation: the copy catches up -> dropped from the cache -> ABSENT
    r = H.detect_mirror_lag(feed=feed(iso(NOW + 6 * 900), {"covenant": repo(tgt)}), cache_path=cp, now=NOW + 6 * 900)
    check("SF1d mutation: when the copy reaches target, mirror_lag CLEARS (ABSENT)",
          r["state"] == H.ABSENT and not H._load_lag_cache(cp).get("covenant/hf"), str(r["measured"]))

    # the M34 guard: the SAME feed reading seen many times must NOT advance the cycle count
    cp2 = tmp_path("_lag2.json")
    same = feed("2026-11-02T10:00:00", {"covenant": repo(tgt, website=behind)})
    seen = [H.detect_mirror_lag(feed=same, cache_path=cp2, now=NOW)["state"] for _ in range(6)]
    cyc = (H._load_lag_cache(cp2).get("covenant/website") or {}).get("cycles")
    check("SF1d six passes on ONE feed reading stay at cycle 1 (not 'the loop ran again')",
          all(s == H.ABSENT for s in seen) and cyc == 1, "cycles=%s" % cyc)

    # a changed target restarts the count (a fresh lag instance, not a continuation)
    cp3 = tmp_path("_lag3.json")
    for i in range(1, 5):
        H.detect_mirror_lag(feed=feed(iso(NOW + i * 900), {"covenant": repo(tgt, hf=behind)}), cache_path=cp3, now=NOW + i * 900)
    newtgt = "c" * 40
    r = H.detect_mirror_lag(feed=feed(iso(NOW + 5 * 900), {"covenant": repo(newtgt, hf=behind)}), cache_path=cp3, now=NOW + 5 * 900)
    check("SF1d a changed target restarts the cycle count (fresh instance) -> back to ABSENT",
          r["state"] == H.ABSENT and (H._load_lag_cache(cp3).get("covenant/hf") or {}).get("cycles") == 1, str(r["measured"]))

    # feed not ready -> UNKNOWN, so a feed outage is unison_feed_stale's finding, not "no lag"
    r = H.detect_mirror_lag(feed={"status": "starting"}, cache_path=tmp_path("_x.json"))
    check("SF1d a not-ready feed makes mirror_lag UNKNOWN, never OK", r["state"] == H.UNKNOWN, str(r["measured"]))

    # ================================================================= SF1e: github_push_lag (PROPOSE_ONLY copy)
    cpg = tmp_path("_lagg.json")
    for i in range(1, 5):
        H.detect_github_push_lag(feed=feed(iso(NOW + i * 900), {"covenant": repo(tgt, github=behind)}), cache_path=cpg, now=NOW + i * 900)
    r = H.detect_github_push_lag(feed=feed(iso(NOW + 5 * 900), {"covenant": repo(tgt, github=behind)}), cache_path=cpg, now=NOW + 5 * 900)
    check("SF1e github behind across >3 readings fires github_push_lag",
          r["state"] == H.PRESENT and r["measured"]["github_behind_over_3_cycles"].get("covenant/github") == 5, str(r["measured"]))
    # and mirror_lag does NOT claim the github copy -- a public push is never its auto job
    rm = H.detect_mirror_lag(feed=feed(iso(NOW + 5 * 900), {"covenant": repo(tgt, github=behind)}), cache_path=cpg, now=NOW + 5 * 900)
    check("SF1e mirror_lag never claims a github copy (public push is PROPOSE_ONLY)",
          rm["state"] == H.ABSENT and not rm["measured"]["rerun_tasks"], str(rm["measured"]))
    # mutation: github caught up -> cleared
    r = H.detect_github_push_lag(feed=feed(iso(NOW + 6 * 900), {"covenant": repo(tgt)}), cache_path=cpg, now=NOW + 6 * 900)
    check("SF1e mutation: github at target clears github_push_lag", r["state"] == H.ABSENT, str(r["measured"]))

    # ================================================================= SF1f: the remedy functions, both ways
    ok, said = H.remedy_rerun_sync_task({"not_firing": ["CovenantHFMirror"]}, dry_run=True)
    check("SF1f rerun_sync_task would re-run the named task (dry)", ok and "CovenantHFMirror" in said, said)
    ok, said = H.remedy_rerun_sync_task({"not_firing": []}, dry_run=True)
    check("SF1f mutation: rerun_sync_task with nothing to run DECLINES (held, not a failure)", not ok, said)
    ok, said = H.remedy_trigger_mirror_sync({"rerun_tasks": ["CovenantSiteAutoDeploy"]}, dry_run=True)
    check("SF1f trigger_mirror_sync would re-run the owning task (dry)", ok and "CovenantSiteAutoDeploy" in said, said)
    ok, said = H.remedy_trigger_mirror_sync({"rerun_tasks": []}, dry_run=True)
    check("SF1f mutation: trigger_mirror_sync with no lagging task DECLINES", not ok, said)

    # ================================================================= SF1g: the class line does not move
    # rerun_sync_task is AUTO_REVERSIBLE and may run (its touches cross no NEVER_AUTOMATIC subject); the remedy
    # runs through apply_remedy as an async 'started'. propose_unison_feed is PROPOSE_ONLY and is REFUSED by the
    # engine with a proposal carrying the covenant's reading and the cost beside the gain.
    led = tempfile.mktemp(suffix="_sf.jsonl")
    calls = []
    real = dict(H.REMEDIES["rerun_sync_task"])
    try:
        H.REMEDIES["rerun_sync_task"] = dict(real)               # keep the real class/touches; swap only the fn
        H.REMEDIES["rerun_sync_task"]["fn"] = lambda m, dry_run=True: (calls.append(dry_run), (True, "spy ran"))[1]
        row = H.apply_remedy("rerun_sync_task", present_cond({"not_firing": ["CovenantHFMirror"]}),
                             "sync_task_not_firing", dry_run=False, ledger=led, choices={}, cooldown_s=0)
        check("SF1g rerun_sync_task is AUTO_REVERSIBLE and RUNS (async 'started'), its fn entered",
              row["outcome"] == "started" and calls == [False], (row["outcome"], calls))
    finally:
        H.REMEDIES["rerun_sync_task"] = real

    row = H.apply_remedy("propose_unison_feed", present_cond({"reachable": False}), "unison_feed_stale",
                         dry_run=False, ledger=led, choices={}, cooldown_s=0)
    cov = row.get("covenant", {})
    check("SF1g propose_unison_feed is PROPOSE_ONLY: the engine REFUSES it (proposed, not run)",
          row["outcome"] == "proposed", row.get("outcome"))
    check("SF1g ...the proposal carries the cost beside the gain",
          bool(row.get("mutual_benefit", {}).get("gains") and row.get("mutual_benefit", {}).get("cost")),
          str(row.get("mutual_benefit"))[:90])
    check("SF1g ...and the covenant's own running seat, named",
          bool(cov.get("seat")) and cov.get("principles_put_to_it", 0) > 0, str(cov)[:90])

    # ================================================================= SF1h: healing graded both ways (async)
    # The re-run is async, so grade_started judges it a later pass: condition gone -> fixed; still present ->
    # did not fix. A fixture detector is swapped in so no scheduler is read.
    led2 = tempfile.mktemp(suffix="_sf2.jsonl")
    real = dict(H.REMEDIES["rerun_sync_task"])
    saved_det = H.DETECTORS.get("sync_task_not_firing")
    try:
        H.REMEDIES["rerun_sync_task"] = dict(real, fn=lambda m, dry_run=True: (True, "spy ran"))
        start = H.apply_remedy("rerun_sync_task", present_cond({"not_firing": ["CovenantHFMirror"]}),
                               "sync_task_not_firing", dry_run=False, ledger=led2, choices={}, cooldown_s=0)
        later = start["at"] + H.REMEDIES["rerun_sync_task"]["grade_after_s"] + 10
        H.DETECTORS["sync_task_not_firing"] = lambda health=None: {"state": H.ABSENT, "measured": {}}
        g = H.grade_started(ledger=led2, now=later)
        check("SF1h the started re-run, graded after its window with the condition GONE -> fixed",
              len(g) == 1 and g[0]["outcome"] == "fixed", str(g))
    finally:
        H.REMEDIES["rerun_sync_task"] = real
        if saved_det is not None:
            H.DETECTORS["sync_task_not_firing"] = saved_det

    led3 = tempfile.mktemp(suffix="_sf3.jsonl")
    real = dict(H.REMEDIES["rerun_sync_task"])
    saved_det = H.DETECTORS.get("sync_task_not_firing")
    try:
        H.REMEDIES["rerun_sync_task"] = dict(real, fn=lambda m, dry_run=True: (True, "spy ran"))
        start = H.apply_remedy("rerun_sync_task", present_cond({"not_firing": ["CovenantHFMirror"]}),
                               "sync_task_not_firing", dry_run=False, ledger=led3, choices={}, cooldown_s=0)
        later = start["at"] + H.REMEDIES["rerun_sync_task"]["grade_after_s"] + 10
        H.DETECTORS["sync_task_not_firing"] = lambda health=None: {"state": H.PRESENT, "measured": {"not_firing": ["CovenantHFMirror"]}}
        g = H.grade_started(ledger=led3, now=later)
        check("SF1h mutation: the same start, condition STILL present -> did not fix",
              len(g) == 1 and g[0]["outcome"] == "did not fix", str(g))
    finally:
        H.REMEDIES["rerun_sync_task"] = real
        if saved_det is not None:
            H.DETECTORS["sync_task_not_firing"] = saved_det

    # ================================================================= SF1i: _iso8601_dur_s and _read_sync_tasks
    check("SF1i interval parse: PT2H=7200, PT15M=900, PT1H30M=5400, junk=None",
          (H._iso8601_dur_s("PT2H"), H._iso8601_dur_s("PT15M"), H._iso8601_dur_s("PT1H30M"), H._iso8601_dur_s("x"))
          == (7200, 900, 5400, None))
    fake = [{"name": "CovenantHFMirror", "state": "Ready", "last": 1793640000, "result": 0, "next": 1793647200, "interval": "PT2H"}]
    parsed = H._read_sync_tasks(("CovenantHFMirror", "CovenantSiteAutoDeploy"), run=lambda: fake)
    check("SF1i _read_sync_tasks parses result/interval and marks an absent name present=False",
          parsed["CovenantHFMirror"]["interval_s"] == 7200 and parsed["CovenantHFMirror"]["result"] == 0
          and parsed["CovenantSiteAutoDeploy"]["present"] is False, str(parsed))

    # ================================================================= SF1j: the registry audits cover the new remedies
    bad_undo = [n for n, r in H.REMEDIES.items()
                if r["klass"] == H.AUTO_REVERSIBLE and r.get("kind") != "stateless" and not r.get("undo")]
    thin = [n for n, r in H.REMEDIES.items()
            if not (r.get("benefit", {}).get("gains") and r.get("benefit", {}).get("cost"))]
    no_det = [n for n, r in H.REMEDIES.items() if not set(r["for"]) & set(H.DETECTORS)]
    mine = ("rerun_sync_task", "trigger_mirror_sync", "propose_unison_feed")
    crossed = {n: sorted({w for w in H.NEVER_AUTOMATIC for t in H.REMEDIES[n].get("touches", []) if w in t.lower()})
               for n in ("rerun_sync_task", "trigger_mirror_sync")}
    check("SF1j every new remedy is stateless/undoable, declares gains AND cost, and answers a real detector",
          not (set(mine) & (set(bad_undo) | set(thin) | set(no_det))), str((bad_undo, thin, no_det)))
    check("SF1j the AUTO_REVERSIBLE re-run remedies cross no NEVER_AUTOMATIC subject",
          not crossed["rerun_sync_task"] and not crossed["trigger_mirror_sync"], str(crossed))
    check("SF1j every new detector is registered in DETECTORS",
          all(d in H.DETECTORS for d in ("unison_feed_stale", "sync_task_not_firing", "sync_task_missing",
                                         "mirror_lag", "github_push_lag")))

    failed = [n for n, ok in results if not ok]
    print(f"\nSF1: {len(results) - len(failed)}/{len(results)} passed")
    if failed:
        print("FAILED: " + "; ".join(failed))
    return 1 if failed else 0


def present_cond(measured):
    return {"state": H.PRESENT, "measured": measured}


if __name__ == "__main__":
    sys.exit(main())
