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
  - re-states a RETRACTED claim -> recurrence (matches that retraction's narrow pattern -- what R1 enforces)
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
RETRACTED = os.path.join(HERE, "docs", "RETRACTED.json")   # the DESIGNED recurrence instrument (R1's ledger)
DIGEST_CAP = 5
DIGEST_WEEKDAY = 0          # Monday (time.gmtime().tm_wday); the weekly roll-up, not per-round
_STOP = {"the", "that", "with", "from", "this", "into", "when", "which", "their", "about", "every",
         "value", "check", "claim", "model", "agent", "system", "covenant", "gate", "test"}
# Closed-class English (function words, modals, generic connectives). MEASURED 2026-11-04: with the reply-only
# extractor, 13 of 19 ideas were called 'have' on words like "before", "should", "against", "ensure" matching code
# identifiers (`held_before`, `should_canary`, `_emit_against`). A word with no content is never evidence that we
# already built someone's idea. Closed-class only -- no domain word is added here (that is what df below is for).
_STOP |= {"after", "again", "against", "along", "also", "although", "among", "another", "around", "because",
          "before", "behind", "being", "below", "beside", "between", "beyond", "both", "could", "doing", "during",
          "each", "either", "else", "enough", "even", "ever", "first", "have", "having", "here", "however",
          "instead", "itself", "just", "less", "like", "make", "makes", "many", "might", "more", "most", "much",
          "must", "never", "only", "other", "otherwise", "over", "rather", "same", "shall", "should", "since",
          "some", "still", "such", "than", "them", "then", "there", "these", "they", "those", "though",
          "through", "under", "unless", "until", "upon", "very", "what", "whatever", "where", "whether", "while",
          "whose", "will", "within", "without", "would", "your", "ensure", "using", "always"}
# (Specificity for the dedup HINT is measured by document frequency over the scanned files: see term_df and
# DUP_HINT_DF_FRAC below.)


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


_CAMEL = re.compile(r"[A-Z]+(?![a-z])|[A-Z][a-z]+|[a-z]+|[0-9]+")


def _code_identifiers(src):
    """The identifier (NAME) tokens of a Python source -- CODE ONLY. tokenize drops comments and string/
    docstring tokens, so prose never counts as a capability; Python keywords (def, class, ...) are dropped
    too. A file that will not tokenize contributes nothing (conservative: fewer, not more, false 'have's)."""
    import io
    import keyword
    import tokenize as _tok
    out = set()
    try:
        for t in _tok.generate_tokens(io.StringIO(src).readline):
            if t.type == _tok.NAME and not keyword.iskeyword(t.string):
                out.add(t.string)
    except (_tok.TokenError, IndentationError, SyntaxError, ValueError):
        pass
    return out


def _components(identifier):
    """An identifier split into its lowercase word parts (snake_case and camelCase) plus the whole thing, so a
    keyword matches `resolve_joins` on 'joins' but a comment containing the English word 'joins' never does."""
    parts = {identifier.lower()}
    for chunk in identifier.split("_"):
        for m in _CAMEL.finditer(chunk):
            parts.add(m.group(0).lower())
    return parts


def _scan_files(root):
    """The files the dedup reads: top-level .py, minus frozen '.PRE-' copies (retired versions kept as tombstones --
    a match there says what we HAD, not what we have; 20 of 496 on 2026-11-04)."""
    return [p for p in sorted(glob.glob(os.path.join(root, "*.py"))) if ".PRE-" not in os.path.basename(p)]


_DF_CACHE = {}


def term_df(root=HERE):
    """(n_files, {component: number of scanned files whose identifiers contain it}). Cached per root and file-set
    signature (names + mtimes), so a nightly builds it once."""
    files = _scan_files(root)
    sig = tuple((p, os.path.getmtime(p)) for p in files)
    hit = _DF_CACHE.get(root)
    if hit and hit[0] == sig:
        return hit[1]
    df = {}
    for p in files:
        try:
            src = open(p, encoding="utf-8", errors="ignore").read()
        except Exception:                                      # noqa: BLE001
            continue
        comps = set()
        for ident in _code_identifiers(src):
            comps |= _components(ident)
        for c in comps:
            df[c] = df.get(c, 0) + 1
    val = (len(files), df)
    _DF_CACHE[root] = (sig, val)
    return val


def _grep_repo(terms, root=HERE):
    """Dedup against the CODE, not the prose. For each top-level .py, match each candidate keyword against the
    file's identifier tokens at WORD level (snake/camel components), never as a raw-text substring. Returns
    every distinct "term @ basename (code `identifier`)" it matched, joined by '; ' (a truthy string), or "".

    Redesigned 2026-10-28 (ops/consult_dedup_precision_external_2026-10-28.md) after a 'have' false-killed a
    real candidate: 'joins' had matched an English verb in a COMMENT via a case-insensitive SUBSTRING on the
    first keyword only. ChatGPT + DeepSeek: match code identifiers not raw text (tokenize; snake/camel, not \\b),
    collect ALL matched concepts, and a lexical match is evidence to INVESTIGATE -- never, on its own, proof. So
    a 'have' from this is held by the circle-back guard for a disposition, not silently discarded. Still bounded
    to top-level .py for a cheap nightly run; a no-match stays 'backlog' (needs a human call), never a confident
    'new' -- absence of evidence in a partial scan is not evidence of absence (DeepSeek)."""
    if not terms:
        return ""
    termset = {t.lower() for t in terms}
    matches, seen = [], set()
    for path in _scan_files(root):
        try:
            src = open(path, encoding="utf-8", errors="ignore").read()
        except Exception:                                      # noqa: BLE001
            continue
        base = os.path.basename(path)
        for ident in sorted(_code_identifiers(src)):
            for t in sorted(termset & _components(ident)):
                if (t, base) not in seen:
                    seen.add((t, base))
                    matches.append("%s @ %s (code `%s`)" % (t, base, ident))
    return "; ".join(matches)


_RETRACTION_CACHE = {}


def _retraction_patterns(path=None):
    """The narrow per-claim regexes from docs/RETRACTED.json -- the DESIGNED recurrence instrument, the very
    patterns test_r1_retracted.py enforces (rule 10: 'a narrow pattern', one set per refuted claim). Returns
    [(id, claim, compiled), ...]; cached by (path, mtime) so a nightly compiles them once."""
    if path is None:                                           # IM8: every path default resolves at call time
        path = RETRACTED
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return []
    hit = _RETRACTION_CACHE.get(path)
    if hit and hit[0] == mtime:
        return hit[1]
    out = []
    try:
        data = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        return []
    for r in data.get("retractions", []):
        claim = (r.get("claim") or "").strip()
        for p in r.get("patterns", []):
            try:
                out.append((r.get("id"), claim, re.compile(p, re.I)))
            except re.error:
                continue                                       # a malformed pattern is R1's problem to flag, not ours
    _RETRACTION_CACHE[path] = (mtime, out)
    return out


def _tombstoned(text, path=None):
    """Return 'RETRACTED <id>: <claim>' if `text` RE-STATES a retracted claim (matches one of that retraction's
    narrow patterns), else None.

    REDESIGNED 2026-10-29 (A391). The old check flagged a 'recurrence' when any TWO >=6-char non-stopword terms
    co-occurred on ONE line of RETRACTED.json + KNOWN_ISSUES.md + LOOKBACK_INDEX.md (18,858 lines of prose).
    MEASURED on the dedup benchmark it fired on 6 of 10 candidates and ALL SIX were FALSE: function words slip
    the length filter ('reserve'+'before' hit a line about preserving a check on a branch; 'retraction'+'beside'
    hit the file HEADER; the real gap 'mobile push on a verdict flip' hit a line about re-judging blocks and was
    SILENTLY DISCARDED). Same shape as the dedup substring bug -- a lexical co-occurrence in prose read as a
    semantic match (rule 7 / A30). The designed instrument is RETRACTED.json's narrow patterns (what R1 runs); a
    recurrence = re-stating a REFUTED claim. KNOWN_ISSUES/LOOKBACK carry no patterns and are OPEN defects, not
    refuted claims -- a candidate matching one may be PROPOSING the fix, so they no longer force a 'recurrence'
    (they fall through to the dedup/backlog -> a human). The hit names the retraction id so the circle-back can
    re-verify it mechanically (the instrument is re-runnable, unlike a 'have's justification)."""
    for rid, claim, rx in _retraction_patterns(path):
        if rx.search(text or ""):
            return "RETRACTED %s: %s" % (rid, claim[:110])
    return None


# A LEXICAL MATCH NEVER KILLS (2026-11-04, A409 follow-up; the operator: "use logic and reason towards mutual
# benefit"). Until now a keyword in our code made a candidate 'have' -- discarded as a duplicate, then held by the
# circle-back until a person wrote a disposition. MEASURED on the reply-only extractor's 32 real ideas: at every
# generic-word cutoff tried (5%..100% of files) the 'have' verdicts rested on co-incidences ("handle"+"rollback" in a
# 9,000-line file, "before" in `held_before`), and the author-labelled seed traded 4/5 false haves for 4/5 missed
# duplicates as the cutoff moved. A word match cannot show a MECHANISM exists. The 10-28 design already said so ("a
# lexical match is evidence to INVESTIGATE -- never, on its own, proof"); the covenant's own precept is "investigate
# on a signal, never convict on one". So the strongest lexical evidence (two specific terms in one file) is carried as
# `dup_hint` and the candidate goes to the backlog; the weekly digest (capped at DIGEST_CAP) shows unhinted ideas
# first. Who gains: commenters' ideas are no longer discarded on a coincidence; the person's load stays capped and
# the circle-back is not flooded; Tetsu learns from what was really proposed. What it costs: a true duplicate is no
# longer dropped automatically -- it reaches a person, ranked after new ideas, with its evidence attached. The
# precise kill that remains is 'recurrence' (a RETRACTED.json pattern), re-verified mechanically by the circle-back.
DUP_HINT_DF_FRAC = 0.20     # for the HINT only: a term in > 20% of scanned files is not specific (seed: 2/5 missed,
                            # 0/5 false at 0.20; n=10, author-labelled -- indicative, not validated)


def dup_hint(g, content):
    """The strongest lexical evidence in a grep result: matches of >= 2 specific terms in ONE file (or the single
    term of a one-term candidate), as a '; '-joined string -- or "". Evidence to rank and show, never a verdict."""
    if not g or g is True:
        return ""
    segs = [s.strip() for s in str(g).split(";") if "@" in s]
    by_file = {}
    for s in segs:
        t = s.split("@", 1)[0].strip()
        f = s.split("@", 1)[1].strip().split(" ", 1)[0]
        n, df = term_df()
        if n and df.get(t.lower(), 0) > DUP_HINT_DF_FRAC * n:
            continue
        by_file.setdefault(f, []).append(s)
    best = max(by_file.values(), key=lambda v: len({x.split("@", 1)[0].strip() for x in v}), default=[])
    k = len({x.split("@", 1)[0].strip() for x in best})
    return "; ".join(best) if (k >= 2 or (k == 1 and len(content) == 1)) else ""


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
    hint = dup_hint(g, _keywords(c))
    if g:
        return {"status": "backlog", "dup_hint": hint,
                "why": "survived cheap vet -- %s; needs a human/strong-seat call"
                       % ("POSSIBLE DUPLICATE (two specific terms in one file): %s" % hint if hint else
                          "lexical matches only, no file holds two specific terms -- not evidence we have it"
                          + ("; matches: %s" % str(g)[:300] if g is not True else ""))}
    return {"status": "backlog", "dup_hint": "", "why": "survived cheap vet -- needs a human/strong-seat call"}


def _append_backlog(row, path=None):
    if path is None:                                           # IM8: call time, never a frozen default (see extract)
        path = BACKLOG
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
_OUTCOMES = ("verified_have", "false_match", "unresolved", "miner_echo")
# miner_echo (2026-11-04, A409 follow-up; 7 of 7 context seats, ops/ECHO_CONSULT_2026-11-04.md): the "idea" came
# from the MINER'S OWN PROMPT, not the reply. false_match says the matcher was wrong about real text; here the matcher
# did its job on text that should not have existed. Logging it as false_match would hide the miner's failure rate
# and feed the false_match stopword-demotion count with matches that were never the vocabulary's fault.
# Clears only with evidence: the echo score at/over the bar (echo_frac) AND the echoed phrase AND a rationale.
# Proposed by propose_echo_dispositions(); WRITTEN by a human or Tetsu (4 of 7 seats: a person confirms each).
_HAVE_TERM = re.compile(r"dedup\)\s*:\s*(?P<term>[^@;]+?)\s*@\s*(?P<file>[^\s();]+)")   # first "term @ file"
_RECURRENCE_ID = re.compile(r"RETRACTED\s+(?P<id>[^\s:]+)\s*:")                         # "RETRACTED A121: ..."


def have_killing_term(why):
    """Parse a 'have' verdict's killing term Y from its `why`: ('term', 'file'), or (None, None) when the
    have did not name which keyword tripped the dedup."""
    m = _HAVE_TERM.search(why or "")
    return (m.group("term").strip(), m.group("file").strip()) if m else (None, None)


def recurrence_retraction_id(why):
    """Parse a 'recurrence' verdict's named retraction id from its `why` ('RETRACTED A121: ...'), or None for a
    legacy verdict written by the old prose scan (which named a file, never a retraction id)."""
    m = _RECURRENCE_ID.search(why or "")
    return m.group("id").strip() if m else None


def _recurrence_still_matches(idea, rid, path=None):
    """Does `idea` STILL match the named retraction's narrow patterns? The recurrence instrument is re-runnable
    (unlike a have's justification), so the circle-back can MECHANICALLY reconfirm a recurrence. One that no
    longer matches -- a crude legacy verdict, or a retraction later restated/removed -- is surfaced for re-vet,
    so a false recurrence can no longer silently discard a real gap."""
    if not rid:
        return False
    return any(r_rid == rid and rx.search(idea or "") for r_rid, _claim, rx in _retraction_patterns(path))


def _load_backlog(path=None):
    if path is None:                                           # IM8: call time
        path = BACKLOG
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(ln) for ln in f if ln.strip()]


def load_dispositions(path=None):
    """{candidate_id: latest disposition row}. Append-only ledger, last write wins (an 'unresolved' can later
    become 'verified_have' or 'false_match')."""
    if path is None:                                           # IM8: call time
        path = DISPOSITIONS
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
    if o == "miner_echo":
        try:
            ef = float(d.get("echo_frac"))
        except (TypeError, ValueError):
            return False
        return (ef >= EX.ECHO_FRAC and bool((d.get("phrase") or "").strip())
                and bool((d.get("rationale") or "").strip()))
    return False


def propose_echo_dispositions(escalated, reply_text):
    """For escalated 'have' rows whose IDEA is our prompt handed back (echo score >= the bar against the row's own
    reply), return the miner_echo disposition a human/Tetsu would write. PROPOSES ONLY -- writes nothing.
    `reply_text(id) -> str` supplies the reply the miner read."""
    out = []
    for o in escalated:
        rep = reply_text(o.get("id")) or ""
        ef = EX.preamble_echo_frac(o.get("idea"), rep)
        if ef < EX.ECHO_FRAC:
            continue
        out.append({"candidate_id": o.get("id"), "outcome": "miner_echo", "echo_frac": round(ef, 3),
                    "phrase": o.get("idea"), "term": o.get("term"),
                    "rationale": "IDEA is %d%% preamble words absent from the reply; the term '%s' matched text the "
                                 "miner invented" % (round(ef * 100), o.get("term"))})
    return out


def circle_back(rows=None, dispositions=None, n_runs=CIRCLE_BACK_RUNS, backlog=None,
                fix_iso=TERM_NAMING_FIX_ISO, sunset_runs=SUNSET_RUNS, disp_path=None, today=None,
                retracted=None):
    """Read the discard verdicts back -- BOTH the have-Y claims and the recurrence claims. Returns
    {'escalate','miner_defect','stale_recurrence','cleared','reconfirmed','demote_terms','ok'}.
    A 'have' is CLEARED only by a well-formed disposition keyed to its candidate id; otherwise it is held to an
    escalation window (n_runs; sunset_runs for grandfathered pre-fix rows) and, past it, ESCALATED; a term-less
    non-grandfathered have is a miner_defect. A 'recurrence' is re-verified MECHANICALLY against the named
    retraction's patterns: one that still matches is reconfirmed (no human needed); one that no longer matches --
    a crude legacy prose verdict, or a retraction since restated/removed -- is stale_recurrence (surfaced for
    re-vet), unless a disposition clears it. ok == nothing escalated, no miner defect, no stale recurrence."""
    rows = _load_backlog(backlog) if rows is None else rows
    disp = load_dispositions(disp_path) if dispositions is None else dispositions
    today = today or time.strftime("%Y-%m-%d", time.gmtime())
    escalate, miner_defect, cleared, stale_recurrence, reconfirmed = [], [], [], [], []
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
    for r in (x for x in rows if x.get("vet") == "recurrence"):
        cid = r.get("id")
        d = disp.get(cid)
        if d and disposition_clears(d, today):
            cleared.append({"id": cid, "outcome": d.get("outcome")})
            continue
        rid = recurrence_retraction_id(r.get("why"))
        if _recurrence_still_matches(r.get("idea"), rid, retracted):
            reconfirmed.append({"id": cid, "rid": rid})       # a precise recurrence that still holds -- no human
            continue
        stale_recurrence.append({"id": cid, "rid": rid, "idea": r.get("idea"), "t": r.get("t"),
                                 "needs": "re-vet: this 'recurrence' no longer matches a RETRACTED pattern "
                                          "(a legacy prose verdict, or the retraction was restated)"})
    demote = sorted(t for t, c in fm.items() if c >= FALSE_MATCH_STOPWORD_K)
    return {"escalate": escalate, "miner_defect": miner_defect, "stale_recurrence": stale_recurrence,
            "cleared": cleared, "reconfirmed": reconfirmed, "demote_terms": demote,
            "ok": not escalate and not miner_defect and not stale_recurrence}


# ---- dedup benchmark (operator "build the benchmark"; ChatGPT asked to MEASURE before more precision) --------
# A labelled set of candidate ideas, each adjudicated real_have (a capability we DO have -> the dedup should
# flag it) or real_gap (we LACK it -> the dedup must NOT flag it). Running the vet over them MEASURES the two
# error rates ChatGPT named: a false_have (a real_gap the dedup killed) and a missed_duplicate (a real_have the
# dedup let through). "covered" = the vet treated it as already-present (status have OR recurrence). The seed
# labels are AUTHOR-written, not blind independent adjudication (ops/dedup_benchmark.jsonl) -- so the live
# numbers are INDICATIVE scaffolding, not a validated benchmark; the harness + metrics are the durable part.
BENCHMARK = os.path.join(HERE, "ops", "dedup_benchmark.jsonl")
_COVERED = ("have", "recurrence")


def benchmark(rows=None, path=None, grep=None, tomb=None):
    """Score the vet over a labelled set. Returns the two error rates + the per-row outcomes. refs/tomb inject
    for the test; the default runs the real matcher over the live tree."""
    if path is None:                                           # IM8: call time (NOT _load_backlog's BACKLOG default)
        path = BENCHMARK
    rows = _load_backlog(path) if rows is None else rows
    out = []
    for r in rows:
        v = vet({"kind": "gap", "maps": r.get("maps", ""), "idea": r.get("idea", ""),
                 "test": r.get("test") or "present=green / removed=red"}, grep=grep, tomb=tomb)
        covered = v["status"] in _COVERED or bool(v.get("dup_hint"))   # a hint now = 'flagged as a dup'
        if r.get("label") == "real_have":
            outcome = "caught" if covered else "missed_duplicate"
        else:                                                  # real_gap
            outcome = "false_have" if covered else "correct_pass"
        out.append({"id": r.get("id"), "idea": r.get("idea"), "label": r.get("label"),
                    "vet": v["status"], "outcome": outcome, "why": v["why"]})
    nh = sum(1 for r in out if r["label"] == "real_have")
    ng = sum(1 for r in out if r["label"] == "real_gap")
    missed = [r for r in out if r["outcome"] == "missed_duplicate"]
    false_have = [r for r in out if r["outcome"] == "false_have"]
    by_status = {}
    for r in out:
        by_status[r["vet"]] = by_status.get(r["vet"], 0) + 1
    return {"n": len(out), "n_real_have": nh, "n_real_gap": ng,
            "missed_duplicates": [r["id"] for r in missed], "false_haves": [r["id"] for r in false_have],
            "missed_dup_rate": (len(missed) / nh) if nh else None,
            "false_have_rate": (len(false_have) / ng) if ng else None,
            "by_status": by_status, "rows": out}


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


def rank_ready(rows):
    """The order a person sees the weekly digest in: ideas WITHOUT a dup_hint (likely new) first, hinted ones
    after; stable within each group. The digest is capped, so this decides which ideas use the person's slots."""
    return sorted(rows, key=lambda r: bool(r.get("dup_hint")))


def nightly(say=print, ask=None, weekday=None, digest=None, backlog=None, grep=None, tomb=None):
    """One cycle. Seeds on the first ever run; otherwise extracts the delta, vets it, and on the weekly day
    emits ONE capped digest of what reached 'backlog'. Fail-soft: never raises into the nightly."""
    if backlog is None:                                        # IM8: call time, never a frozen default
        backlog = BACKLOG
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
        row = {**c, "vet": v["status"], "why": v["why"], "dup_hint": v.get("dup_hint", "")}
        _append_backlog(row, backlog)
        counts[v["status"]] = counts.get(v["status"], 0) + 1
        if v["status"] == "backlog":
            ready.append(row)
    say("improve: %d new, vetted -> %s" % (len(new), ", ".join("%s=%d" % kv for kv in sorted(counts.items())) or "none"))
    emitted = 0
    ready = rank_ready(ready)
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
        for s in cb["stale_recurrence"]:
            say("improve: CIRCLE-BACK stale-recurrence -- '%s' was discarded as a recurrence but no longer "
                "matches RETRACTED %s; re-vet (a real gap may have been silently dropped)"
                % ((s.get("idea") or "?")[:70], s.get("rid") or "(no id -- legacy prose verdict)"))
    for t in cb["demote_terms"]:
        say("improve: CIRCLE-BACK vocabulary -- '%s' false-matched >=%d times; demote it to a dedup stopword"
            % (t, FALSE_MATCH_STOPWORD_K))
    return {"new": len(new), "counts": counts, "ready": len(ready), "digest_emitted": emitted,
            "circle_back_ok": cb["ok"], "escalate": len(cb["escalate"]), "miner_defect": len(cb["miner_defect"]),
            "stale_recurrence": len(cb["stale_recurrence"]), "cleared": len(cb["cleared"]),
            "reconfirmed": len(cb["reconfirmed"]), "demote_terms": cb["demote_terms"]}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if "--seed" in argv:
        seed_baseline()
        return 0
    if "--propose-echo" in argv:                              # print miner_echo dispositions for a person to confirm
        texts = {}
        for row in IM._rows(IM.CANDIDATES):
            texts.setdefault(IM._row_id(row), str(row.get("text") or ""))
        props = propose_echo_dispositions(circle_back()["escalate"], texts.get)
        for p in props:
            print(json.dumps(p, ensure_ascii=False))
        print("propose-echo: %d miner_echo proposal(s); nothing written -- append the ones you confirm to %s"
              % (len(props), DISPOSITIONS))
        return 0
    if "--circle-back" in argv:                               # the hard check: nonzero if any have needs a human
        cb = circle_back()
        for o in cb["escalate"]:
            print("ESCALATE  have '%s' (%s) -- %s (since %s%s)"
                  % ((o.get("idea") or "?")[:70], o.get("term") or "no term", o["needs"], o["t"],
                     ", grandfathered" if o.get("grandfathered") else ""))
        for u in cb["miner_defect"]:
            print("MINER-DEFECT  have '%s' named no killing term -- re-vet (%s)" % ((u.get("idea") or "?")[:70], u["t"]))
        for s in cb["stale_recurrence"]:
            print("STALE-RECURRENCE  '%s' no longer matches RETRACTED %s -- re-vet, a real gap may have been "
                  "dropped (%s)" % ((s.get("idea") or "?")[:70], s.get("rid") or "(no id)", s["t"]))
        for t in cb["demote_terms"]:
            print("DEMOTE  '%s' false-matched >=%d times -- make it a dedup stopword" % (t, FALSE_MATCH_STOPWORD_K))
        print("circle-back: %d cleared, %d reconfirmed, %d escalate, %d miner-defect, %d stale-recurrence -> %s"
              % (len(cb["cleared"]), len(cb["reconfirmed"]), len(cb["escalate"]), len(cb["miner_defect"]),
                 len(cb["stale_recurrence"]), "ok" if cb["ok"] else "FAILED"))
        return 0 if cb["ok"] else 1
    print(nightly())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
