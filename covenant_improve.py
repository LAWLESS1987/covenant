#!/usr/bin/env python3
"""Increment 3 of the nightly improvement-mining process -- the orchestrator.

Operator, 2026-10-27: "nightly is probably the right move. Tetsu should be learning all these things as we
go." And the firehose that made the old mail queue useless is the thing to avoid: "it's a lot for me to
keep up with."

So the shape is: harvest the delta (increment 1) -> extract it through Tetsu's door, teaching him
(increment 2) -> VET each candidate cheaply -> append to one backlog -> and only ONCE A WEEK, a capped
digest of what survived. Not every conversation; only vetted candidates, a few at a time, or silence.

THE VET is deliberately cheap and errs toward "have" (rejecting a duplicate is cheaper than building one --
Codex's rule). It does NOT claim a candidate is a real improvement; it filters out the obvious non-starters
and leaves a human or a stronger seat the final call:
  - kind != gap            -> skip (have / stance / none / unparsed)
  - no both-ways test       -> needs-test (cannot earn a ring without one)
  - matches a tombstone     -> recurrence (RETRACTED / KNOWN_ISSUES already covers it)
  - keyword already in src   -> have (dedup against the capability, not the idea)
  - else                     -> backlog (survived; needs a human/strong-seat call)

COLD START: the first run seeds the whole backlog as SEEN without extracting (51k replies would flood the
door and the digest). From then on, only genuinely-new replies flow.

Usage: python covenant_improve.py            # one cycle (seeds on first run)
       python covenant_improve.py --seed     # force baseline-seed only
"""
import json, os, re, sys, glob, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_improve_mine as IM
import covenant_improve_extract as EX

BACKLOG = os.path.join(HERE, "ops", "improve_backlog.jsonl")
TOMBSTONES = (os.path.join(HERE, "docs", "RETRACTED.json"),
              os.path.join(HERE, "docs", "KNOWN_ISSUES.md"),
              os.path.join(HERE, "docs", "LOOKBACK_INDEX.md"))
DIGEST_CAP = 5
DIGEST_WEEKDAY = 0          # Monday (time.gmtime().tm_wday); the weekly roll-up, not per-round
_STOP = {"the", "that", "with", "from", "this", "into", "when", "which", "their", "about", "every",
         "value", "check", "claim", "model", "agent", "system", "covenant", "gate", "test"}


def is_seeded(seen_path=None):
    return os.path.exists(seen_path or IM.SEEN)


def seed_baseline(say=print):
    """Cold start: consume the whole current backlog as seen, extract nothing, emit nothing."""
    n = len(IM.harvest(update=True))
    say("improve: baseline seeded %d backlog repl%s (no digest; deltas start next run)"
        % (n, "y" if n == 1 else "ies"))
    return n


def _keywords(c, k=4):
    words = re.findall(r"[a-zA-Z][a-zA-Z_-]{4,}", ((c.get("maps") or "") + " " + (c.get("idea") or "")).lower())
    out = []
    for w in words:
        if w not in _STOP and w not in out:
            out.append(w)
        if len(out) >= k:
            break
    return out


def _grep_repo(terms, root=HERE):
    """Crude dedup: does any keyword already appear in a top-level .py source? Errs toward 'have' (a false
    match rejects a duplicate, the safe direction). Bounded to top-level sources so a nightly run stays cheap.

    Returns the FIRST "term @ basename" it matched (a truthy string), or "" when nothing matched. The string
    is so a 'have' verdict can name WHICH keyword tripped the dedup: the blind spot is a single GENERIC word
    (e.g. 'joins', 'promote') matching everywhere, and a 'have' that cannot say which word is unmeasurable --
    run-check-adjust needs that evidence before the threshold is ever changed (2026-10-28, A375 side-finding)."""
    if not terms:
        return ""
    pats = [(t, re.compile(re.escape(t), re.I)) for t in terms]
    for path in glob.glob(os.path.join(root, "*.py")):
        try:
            src = open(path, encoding="utf-8", errors="ignore").read()
        except Exception:                                      # noqa: BLE001
            continue
        for t, p in pats:
            if p.search(src):
                return "%s @ %s" % (t, os.path.basename(path))
    return ""


def _tombstoned(text, paths=TOMBSTONES):
    """Return the first tombstone/known-issue line whose distinctive keyword appears in `text`, else None."""
    terms = [w for w in re.findall(r"[a-zA-Z][a-zA-Z_-]{5,}", (text or "").lower()) if w not in _STOP]
    if not terms:
        return None
    for path in paths:
        if not os.path.exists(path):
            continue
        try:
            for line in open(path, encoding="utf-8", errors="ignore"):
                low = line.lower()
                if sum(1 for t in terms if t in low) >= 2:     # two distinctive terms co-occurring = a real match
                    return "%s: %s" % (os.path.basename(path), line.strip()[:120])
        except Exception:                                      # noqa: BLE001
            continue
    return None


def vet(c, grep=None, tomb=None):
    grep = grep or _grep_repo
    tomb = tomb or _tombstoned
    kind = c.get("kind")
    if kind != "gap":
        return {"status": "skip", "why": "kind=%s" % kind}
    if not (c.get("test") or "").strip():
        return {"status": "needs-test", "why": "no both-ways test -> cannot earn a ring"}
    hit = tomb(c.get("idea", ""))
    if hit:
        return {"status": "recurrence", "why": hit}
    g = grep(_keywords(c))
    if g:
        why = "a capability keyword already appears in source (dedup)"
        if g is not True:                                      # real _grep_repo names the term; a True stub does not
            why += ": %s" % g
        return {"status": "have", "why": why}
    return {"status": "backlog", "why": "survived cheap vet -- needs a human/strong-seat call"}


def _append_backlog(row, path=BACKLOG):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


# ---- circle-back enforcement (operator 2026-10-28; REDESIGNED the same day after two outside reviews) -------
# "IM3 surfaces the killing term but nothing consumes it." A 'have' verdict kills a candidate as a duplicate
# and names a killing term Y (keyword@file). Nothing read Y back. My first cut cleared a 'have' when a later
# commit referenced Y; ChatGPT and DeepSeek (2026-10-28, ops/consult_circleback_external_2026-10-28.md) were
# blunt that this is WRONG: a commit mentioning Y proves MENTION, not JUSTIFICATION, and a generic term like
# "joins" gets referenced by coincidence -- so an N-run timeout would AUTO-CLEAR a spurious 'have'. So:
#   - a 'have' is CLEARED only by an explicit DISPOSITION keyed to the candidate id, carrying evidence:
#       verified_have -- a code anchor (file[:line/symbol]) whose file exists + a one-line rationale
#       false_match   -- which keyword matched spuriously + why (the candidate returns for human consideration)
#       unresolved    -- acknowledged, HOLDING until a recheck date (after which it escalates)
#   - N runs is an ESCALATION window, never an auto-clear or auto-fail: a 'have' with no (or stale) disposition
#     past N runs is ESCALATED to a human -- that surfacing IS the "failure";
#   - a 'have' that named no term is a MINER DEFECT (the dedup failed to record Y) -> re-vet, NOT evidence the
#     gap is real;
#   - grandfathered pre-fix rows get a SUNSET: past SUNSET_RUNS they must be dispositioned too;
#   - a term with >= FALSE_MATCH_STOPWORD_K false_match dispositions is a dedup-VOCABULARY bug -> demote it.
# This module only READS and SURFACES; it never resurrects a candidate (a human writes a false_match to do that).
DISPOSITIONS = os.path.join(HERE, "ops", "have_dispositions.jsonl")
CIRCLE_BACK_RUNS = 3                                   # his run-check-adjust x3: the escalation window
SUNSET_RUNS = 30                                       # grandfathered pre-fix haves must be dispositioned by then
FALSE_MATCH_STOPWORD_K = 3                             # this many false_match hits on a term = a vocabulary bug
TERM_NAMING_FIX_ISO = "2026-10-28T13:29:21Z"           # f08ce10: 'have' verdicts name the term from here on
_OUTCOMES = ("verified_have", "false_match", "unresolved")
_HAVE_TERM = re.compile(r"dedup\)\s*:\s*(?P<term>[^@]+?)\s*@\s*(?P<file>\S+)\s*$")


def have_killing_term(why):
    """Parse a 'have' verdict's killing term Y from its `why`: ('term', 'file'), or (None, None) when the
    have did not name which keyword tripped the dedup."""
    m = _HAVE_TERM.search(why or "")
    return (m.group("term").strip(), m.group("file").strip()) if m else (None, None)


def _load_backlog(path=BACKLOG):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(ln) for ln in f if ln.strip()]


def load_dispositions(path=DISPOSITIONS):
    """{candidate_id: latest disposition row}. Append-only ledger, last write wins (an 'unresolved' can later
    become 'verified_have' or 'false_match')."""
    out = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for ln in f:
                if not ln.strip():
                    continue
                try:
                    d = json.loads(ln)
                except ValueError:
                    continue
                if d.get("candidate_id"):
                    out[d["candidate_id"]] = d
    return out


def _run_day(t):
    return (t or "")[:10]        # a nightly run is one UTC day; the date is the run key (no separate counter)


def _runs_after(row, rows):
    """Distinct later run-days in the backlog after this row -- the proxy for 'runs since', read from the
    ledger itself. Conservative: a quiet night with no new rows is not counted, so a have is flagged later,
    never earlier, than its true age."""
    d = _run_day(row.get("t"))
    return len({_run_day(r.get("t")) for r in rows if _run_day(r.get("t")) > d})


def disposition_clears(d, today, root=HERE):
    """A disposition CLEARS a 'have' only if it is well-formed for its outcome (reviewers: store proof, not a
    boolean): verified_have needs a code anchor whose file EXISTS and a rationale; false_match needs the matched
    term and a rationale; unresolved HOLDS only until its recheck date (a future date), then stops clearing."""
    o = (d or {}).get("outcome")
    if o == "verified_have":
        f = (d.get("anchor") or "").split(":", 1)[0].split("#", 1)[0].strip()
        return bool(f) and os.path.exists(os.path.join(root, f)) and bool((d.get("rationale") or "").strip())
    if o == "false_match":
        return bool((d.get("term") or "").strip()) and bool((d.get("rationale") or "").strip())
    if o == "unresolved":
        return bool(d.get("recheck")) and str(d.get("recheck")) >= today
    return False


def circle_back(rows=None, dispositions=None, n_runs=CIRCLE_BACK_RUNS, backlog=BACKLOG,
                fix_iso=TERM_NAMING_FIX_ISO, sunset_runs=SUNSET_RUNS, disp_path=DISPOSITIONS, today=None):
    """Read the have-Y claims back. Returns {'escalate','miner_defect','cleared','demote_terms','ok'}.
    A 'have' is CLEARED only by a well-formed disposition keyed to its candidate id. Otherwise it is held to
    an escalation window (n_runs; sunset_runs for grandfathered pre-fix rows) and, past it, ESCALATED. A
    term-less have (not grandfathered) is a miner_defect. ok == nothing to escalate and no miner defect."""
    rows = _load_backlog(backlog) if rows is None else rows
    disp = load_dispositions(disp_path) if dispositions is None else dispositions
    today = today or time.strftime("%Y-%m-%d", time.gmtime())
    escalate, miner_defect, cleared = [], [], []
    fm = {}
    for d in disp.values():
        if d.get("outcome") == "false_match" and (d.get("term") or "").strip():
            fm[d["term"].strip()] = fm.get(d["term"].strip(), 0) + 1
    for r in (x for x in rows if x.get("vet") == "have"):
        cid = r.get("id")
        term, file = have_killing_term(r.get("why"))
        d = disp.get(cid)
        if d and disposition_clears(d, today):
            cleared.append({"id": cid, "outcome": d.get("outcome")})
            continue
        grandfathered = bool(fix_iso and (r.get("t") or "") < fix_iso)
        if term is None and not grandfathered:
            miner_defect.append({"id": cid, "idea": r.get("idea"), "t": r.get("t")})
            continue
        if _runs_after(r, rows) >= (sunset_runs if grandfathered else n_runs):
            escalate.append({"id": cid, "term": term, "file": file, "idea": r.get("idea"), "t": r.get("t"),
                             "grandfathered": grandfathered, "needs": "a disposition keyed to this candidate id"})
    demote = sorted(t for t, c in fm.items() if c >= FALSE_MATCH_STOPWORD_K)
    return {"escalate": escalate, "miner_defect": miner_defect, "cleared": cleared, "demote_terms": demote,
            "ok": not escalate and not miner_defect}


def _default_digest(top, say):
    lines = ["Weekly improvement digest -- %d candidate(s) survived the cheap vet (a human/strong-seat makes "
             "the call; nothing is adopted automatically):" % len(top)]
    for r in top:
        lines.append("  - [%s] %s  (maps: %s)  test: %s"
                     % (r.get("kind"), (r.get("idea") or "?")[:90], r.get("maps") or "?", (r.get("test") or "?")[:70]))
    body = "\n".join(lines)
    try:
        import covenant_contact
        covenant_contact.say(body)
    except Exception as e:                                      # noqa: BLE001 -- a failed notify never fails the cycle
        say("improve: digest not delivered (%s); it is in %s" % (type(e).__name__, os.path.basename(BACKLOG)))
    return body


def nightly(say=print, ask=None, weekday=None, digest=None, backlog=BACKLOG, grep=None, tomb=None):
    """One cycle. Seeds on the first ever run; otherwise extracts the delta, vets it, and on the weekly day
    emits ONE capped digest of what reached 'backlog'. Fail-soft: never raises into the nightly."""
    if not is_seeded():
        return {"seeded": True, "n": seed_baseline(say)}
    weekday = time.gmtime().tm_wday if weekday is None else weekday
    digest = digest or _default_digest
    try:
        new = EX.extract(ask=ask, say=say)
    except Exception as e:                                      # noqa: BLE001
        say("improve: extract raised %s: %s" % (type(e).__name__, str(e)[:160]))
        return {"error": str(e)[:160]}
    counts, ready = {}, []
    for c in new:
        v = vet(c, grep=grep, tomb=tomb)
        row = {**c, "vet": v["status"], "why": v["why"]}
        _append_backlog(row, backlog)
        counts[v["status"]] = counts.get(v["status"], 0) + 1
        if v["status"] == "backlog":
            ready.append(row)
    say("improve: %d new, vetted -> %s" % (len(new), ", ".join("%s=%d" % kv for kv in sorted(counts.items())) or "none"))
    emitted = 0
    if ready and weekday == DIGEST_WEEKDAY:
        digest(ready[:DIGEST_CAP], say)
        emitted = min(len(ready), DIGEST_CAP)
        say("improve: weekly digest emitted (%d of %d backlog-ready)" % (emitted, len(ready)))
    elif ready:
        say("improve: %d backlog-ready; digest holds until the weekly day" % len(ready))
    cb = circle_back(backlog=backlog)                          # read the have-Y claims back -- the circle-back
    if not cb["ok"]:
        for o in cb["escalate"]:
            say("improve: CIRCLE-BACK escalate -- have '%s' (%s) has no disposition for >=%d runs; a human must "
                "mark it verified_have / false_match / unresolved"
                % ((o.get("idea") or "?")[:70], o.get("term") or "no term", CIRCLE_BACK_RUNS))
        for u in cb["miner_defect"]:
            say("improve: CIRCLE-BACK miner-defect -- have '%s' named no killing term (re-vet; not a real gap)"
                % ((u.get("idea") or "?")[:70]))
    for t in cb["demote_terms"]:
        say("improve: CIRCLE-BACK vocabulary -- '%s' false-matched >=%d times; demote it to a dedup stopword"
            % (t, FALSE_MATCH_STOPWORD_K))
    return {"new": len(new), "counts": counts, "ready": len(ready), "digest_emitted": emitted,
            "circle_back_ok": cb["ok"], "escalate": len(cb["escalate"]), "miner_defect": len(cb["miner_defect"]),
            "cleared": len(cb["cleared"]), "demote_terms": cb["demote_terms"]}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if "--seed" in argv:
        seed_baseline()
        return 0
    if "--circle-back" in argv:                               # the hard check: nonzero if any have needs a human
        cb = circle_back()
        for o in cb["escalate"]:
            print("ESCALATE  have '%s' (%s) -- %s (since %s%s)"
                  % ((o.get("idea") or "?")[:70], o.get("term") or "no term", o["needs"], o["t"],
                     ", grandfathered" if o.get("grandfathered") else ""))
        for u in cb["miner_defect"]:
            print("MINER-DEFECT  have '%s' named no killing term -- re-vet (%s)" % ((u.get("idea") or "?")[:70], u["t"]))
        for t in cb["demote_terms"]:
            print("DEMOTE  '%s' false-matched >=%d times -- make it a dedup stopword" % (t, FALSE_MATCH_STOPWORD_K))
        print("circle-back: %d cleared, %d escalate, %d miner-defect -> %s"
              % (len(cb["cleared"]), len(cb["escalate"]), len(cb["miner_defect"]), "ok" if cb["ok"] else "FAILED"))
        return 0 if cb["ok"] else 1
    print(nightly())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
