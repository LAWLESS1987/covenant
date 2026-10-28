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
    return {"new": len(new), "counts": counts, "ready": len(ready), "digest_emitted": emitted}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if "--seed" in argv:
        seed_baseline()
        return 0
    print(nightly())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
