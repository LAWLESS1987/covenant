#!/usr/bin/env python3
"""
A91 -- the corpus membrane: what the students learn from is larger than what
the repository publishes, and the split is by construction rather than by luck.

THE HAZARD, measured 2026-09-11. ops/verdicts.jsonl is TRACKED and
LAWLESS1987/covenant is public (anonymous GET 200, private=false). A scan of
all 3,569 rows that day found no address, no ticker with an amount, no path and
no balance -- but that was an accident of timing, not a property of the code.
covenant_judge_defer.py:327 records a verdict with source "live", whose `text`
is the transaction payload, and the writer sent every source to the same file.
No live transaction had reached it yet. The first one would have published the
payload. That is the same shape as the chat leak found the same day: a path
that is harmless only until the feature starts working.

THE SPLIT. verdict_path_for() is an ALLOWLIST -- only a source known to be
shareable reaches the tracked ledger, so a source nobody thought of fails
closed to the local one. covenant_distill.corpus_paths() then reads BOTH, so
this machine learns from everything it sees while the repository carries only
what is not the submitter's to publish.

WHY THESE CHECKS ARE BEHAVIOURAL. E4 and E5 RUN record_verdict and read which
file appeared on disk; E6 RUNS the loader against a real temp ledger; E8 audits
the actual published artifact rather than the code that writes it. Nothing here
greps a source file for a word.

E2 has THREE answers, not two. `git check-ignore` cannot be asked in the staged
copy the sweep runs in, because that copy has no .git (A84b/A85c). A check that
treats "cannot determine here" as "pass" is the same defect in a different
coat, so it is reported as SKIP and counted separately.

Run: python test_a91_corpus_membrane.py
"""
import json
import os
import subprocess
import sys
import tempfile

import covenant_judge_defer as jd
import covenant_distill as cd

results = []
skips = []


def check(ok, name, detail=""):
    results.append(bool(ok))
    print("%s  %s%s" % ("PASS" if ok else "FAIL", name, ("  " + detail) if detail else ""))


def skip(name, why):
    skips.append(name)
    print("SKIP  %s  -- %s" % (name, why))


class R:
    def __init__(self, violates):
        self.violates = violates
        self.reasoning = "because"


print("== the allowlist decides, and it fails closed ==")
shareable = sorted(jd.SHAREABLE_SOURCES)
check(all(jd.verdict_path_for(s) == jd.VERDICTS for s in shareable),
      "E1a every shareable source routes to the TRACKED ledger",
      "%d sources" % len(shareable))

closed = ["live", "", "LIVE", "Live", "trader", "coinbase", "a-source-nobody-thought-of",
          None, "seed ", "study/live"]
missed = [s for s in closed if jd.verdict_path_for(s) != jd.LIVE_VERDICTS]
check(not missed, "E1b every other source -- including None, case variants and near-misses "
                  "-- routes to the LOCAL ledger", "checked %d, leaked %s" % (len(closed), missed or "none"))

check(jd.VERDICTS != jd.LIVE_VERDICTS, "E1c the two ledgers are different files")

print()
print("== is the local ledger actually kept out of the repository? ==")
if not os.path.isdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".git")):
    skip("E2 git check-ignore on the local ledger",
         "no .git here; the sweep stages a copy without one, and 'cannot "
         "determine' is not 'ignored' (A84b/A85c)")
else:
    try:
        r = subprocess.run(["git", "check-ignore", "-q", "ops/verdicts_live.jsonl"],
                           cwd=os.path.dirname(os.path.abspath(__file__)),
                           capture_output=True, timeout=30)
        check(r.returncode == 0,
              "E2 git itself says ops/verdicts_live.jsonl is ignored",
              "git exit %d" % r.returncode)
    except (OSError, subprocess.SubprocessError) as e:
        skip("E2 git check-ignore on the local ledger", "git did not run: %s" % e)

print()
print("== run the writer and look at what appeared on disk ==")
d = tempfile.mkdtemp()
_v, _l = jd.VERDICTS, jd.LIVE_VERDICTS
try:
    jd.VERDICTS = os.path.join(d, "shareable.jsonl")
    jd.LIVE_VERDICTS = os.path.join(d, "local.jsonl")

    wrote_live = jd.record_verdict({"message": "pay 400 XRP to rSomeone"}, R(False), "t", "live")
    check(wrote_live and os.path.exists(jd.LIVE_VERDICTS),
          "E3 a LIVE verdict is written, to the local ledger")
    check(not os.path.exists(jd.VERDICTS),
          "E4 ...and the shareable ledger was not even created")

    jd.record_verdict({"message": "a seeded teaching case"}, R(True), "t", "seed")
    check(os.path.exists(jd.VERDICTS), "E5a a SHAREABLE verdict does reach the tracked ledger")

    pub = [json.loads(x) for x in open(jd.VERDICTS, encoding="utf-8") if x.strip()]
    check(len(pub) == 1 and "rSomeone" not in json.dumps(pub),
          "E5b THE INSTRUMENT BITES: the payload that went local is absent from the "
          "shareable file, which holds exactly the one row that belongs there")
finally:
    jd.VERDICTS, jd.LIVE_VERDICTS = _v, _l

print()
print("== the students still see everything ==")
d2 = tempfile.mkdtemp()
_cv, _cl = cd.VERDICTS, cd.LIVE_VERDICTS
MARK = "XYZZY-LOCAL-ONLY-ROW"
try:
    cd.VERDICTS = os.path.join(d2, "shareable.jsonl")
    cd.LIVE_VERDICTS = os.path.join(d2, "local.jsonl")
    with open(cd.VERDICTS, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"text": "a public teaching case", "violates": True, "source": "seed"}) + "\n")
    with open(cd.LIVE_VERDICTS, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"text": MARK, "violates": False, "source": "live"}) + "\n")

    both = cd.load_verdicts(paired_only=False)
    only_pub = cd.load_verdicts(cd.VERDICTS, paired_only=False)
    check(len(both) == 2 and any(MARK in r["text"] for r in both),
          "E6 training reads BOTH ledgers -- the local row is in the corpus", "%d rows" % len(both))
    check(len(only_pub) == 1 and not any(MARK in r["text"] for r in only_pub),
          "E7 THE INSTRUMENT BITES: asked for the shareable ledger alone it returns "
          "only that, so E6 is measuring the union and not a duplicate read")
finally:
    cd.VERDICTS, cd.LIVE_VERDICTS = _cv, _cl

print()
print("== audit the artifact that is actually published ==")
rows, bad = 0, {}
try:
    with open(jd.VERDICTS, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            rows += 1
            src = rec.get("source")
            if str(src) not in jd.SHAREABLE_SOURCES:
                bad[str(src)] = bad.get(str(src), 0) + 1
    check(rows > 0, "E8a the tracked corpus was read", "%d rows" % rows)
    check(not bad,
          "E8b every row in the TRACKED corpus has a shareable source",
          "offending sources: %s" % (bad or "none"))
except OSError as e:
    check(False, "E8 could not read the tracked corpus", str(e))

print()
n_ok = sum(1 for r in results if r)
print("%d/%d passed%s" % (n_ok, len(results),
                          (", %d skipped: %s" % (len(skips), "; ".join(skips))) if skips else ""))
sys.exit(0 if n_ok == len(results) else 1)
