#!/usr/bin/env python3
"""Increment 2 of the nightly improvement-mining process.

Takes the NEW forum replies the harvester (covenant_improve_mine) found and routes each one through
TETSU'S OWN DOOR (tools/tetsu_work.ask -> /m/agent) to extract a structured improvement candidate. Two
things happen in that one call, by design: the idea is mined, AND Tetsu learns from it -- the door records
every exchange the way all his work does. "Tetsu should be learning all these things as we go" (operator,
2026-10-27).

Read-only on the sources. Idempotent: it harvests WITHOUT consuming, and marks a reply seen ONLY after the
door answered for it -- so a 503/timeout leaves that reply for the next run (the same rule tetsu_work uses).
Rate-aware: at most MAX_PER_RUN replies per run, because the door has its own limits and the nightly delta
is small (the first run seeds the backlog as seen, in increment 3, without extracting 51k).

Output: ops/improve_candidates.jsonl, one row per extracted reply:
  {id, author, url, kind: gap|have|stance|none|unparsed, maps, idea, test, raw, t}

Usage: python covenant_improve_extract.py [N]     (needs the node door up, like tetsu_work)
"""
import json, os, re, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_improve_mine as IM

CANDIDATES_OUT = os.path.join(HERE, "ops", "improve_candidates.jsonl")
MAX_PER_RUN = 20
_KINDS = ("gap", "have", "stance", "none")

PROMPT = """You judge whether a forum reply names a SYSTEM IMPROVEMENT for our covenant: a ledger with an \
ethics gate in the transaction path; every claim gets a test; we keep retractions beside corrections; \
UNDETERMINED is a valid answer; a change earns its place only if removing it reds a real check.

Reply from u/%s:
\"\"\"%s\"\"\"

Answer in EXACTLY these four lines and nothing else:
KIND: one of  gap (names a mechanism we likely LACK) | have (something we likely already do) | stance (a \
principle, not a thing to build) | none (no system idea)
MAPS: the covenant component it touches, or ?
IDEA: the improvement in one line
TEST: a both-ways test as present=green / removed=red, or ?"""

# ---- v2: REPLY-ONLY extraction (2026-11-04, A409 follow-up) ------------------------------------------------------
# The v1 PROMPT above opens with one sentence describing us. MEASURED: 63 of 139 extractions handed that sentence
# back as the "idea" (12 of 20 on 11-04, the first live night with the echo guard), and the replies' real ideas were
# never extracted. Nine outside seats (ops/ECHO_CONSULT_2026-11-04.md) agreed on the cause: the self-description sits
# in the step that extracts. v2 removes it from that step. The model sees ONLY the reply and must QUOTE the sentence
# the idea rests on; code checks the quote is really in the text the model saw (grounded_quote). Whether we already
# HAVE the idea is decided afterwards by the vet's code search, not by the model's memory of a one-line brochure.
# v1 stays here, runnable, for the side-by-side and as the record of what ran from 10-27 to 11-04.
SELF_DESC = PROMPT.split("Reply from", 1)[0]

PROMPT_V2 = """Read this forum reply. Say whether it proposes a concrete improvement to a system, and if so, which.

Reply from u/%s:
\"\"\"%s\"\"\"

Answer in EXACTLY these four lines and nothing else:
KIND: one of  idea (the reply proposes something to build or change) | stance (a principle, not a thing to \
build) | none (no proposal)
QUOTE: the sentence from the reply that the idea rests on, copied word for word, or ?
IDEA: the reply's proposal in one line, in the reply's own words, or ?
TEST: a both-ways test as present=green / removed=red, or ?"""

# One retry, only when the quote is not in the reply -- with a DIFFERENT instruction (every seat: a same-prompt
# re-ask buys a second echo). It is inserted before the answer format so the format block stays last.
RETRY_NOTE = ("Your last answer quoted words that are not in the reply. QUOTE must be copied exactly from the reply "
              "above. If the reply proposes nothing, answer KIND: none.\n\n")
PROMPT_VERSION = "v2"     # switched 2026-11-04 after the side-by-side + blind judging (A409): echo 22->0 of 40, both-judge "real idea" 10->26
QUOTE_MIN_WORDS = 4       # a 1-3 word "quote" ("the ledger") grounds anything; a sentence fragment must carry content
SEEN_CHARS = 1500          # the model is shown the reply's first 1500 chars; a quote must come from what it saw
_KINDS_V2 = {"idea": "gap", "stance": "stance", "none": "none"}   # "gap" = a candidate for the vet, as before


def _tokens(s):
    """Lower-case word tokens; punctuation, quote marks and whitespace are ignored (a model copying a sentence
    routinely drops or straightens quote marks -- found by IM9 on the first run of this check)."""
    s = (s or "").lower().replace("’", "'").replace("‘", "'")
    return re.findall(r"[a-z0-9]+(?:'[a-z0-9]+)?", s)


def grounded_quote(quote, seen_text):
    """True only when the QUOTE's words appear CONTIGUOUSLY, in order, in the text the model was shown, and number
    at least QUOTE_MIN_WORDS. A paraphrase, an invented sentence, or our own prompt handed back is False."""
    q = _tokens(quote)
    if len(q) < QUOTE_MIN_WORDS:
        return False
    return (" " + " ".join(q) + " ") in (" " + " ".join(_tokens(seen_text)) + " ")


def support_frac(idea, reply):
    """Share of the idea's words (same stems as the echo score) that occur in the reply. Recorded, not gated: the
    quote is the gate; this measures how far the one-line IDEA drifted from the quote's reply."""
    w = _words(idea)
    if not w:
        return 0.0
    rep = set(_words(reply))
    return sum(1 for x in w if x in rep) / len(w)


def _parse_v2(answer):
    out = {"kind": "unparsed", "quote": "", "idea": "", "test": ""}
    for line in (answer or "").splitlines():
        s = line.strip().lstrip("*").strip()
        low = s.lower()
        for key in ("kind", "quote", "idea", "test"):
            if low.startswith(key + ":"):
                out[key] = s.split(":", 1)[1].strip().strip("*").strip()
    k = out["kind"].lower()
    out["kind"] = next((v for name, v in _KINDS_V2.items() if name in k), "unparsed")
    for key in ("quote", "idea", "test"):
        if out[key] == "?" or any(e in out[key].lower() for e in _ECHO):
            out[key] = ""
    return out


def extract_one_v2(author, text, ask):
    """One reply through the reply-only prompt, with at most ONE grounding retry. Returns (code, row-fields).
    code != 200 means the door did not answer (the caller leaves the reply un-seen). A gap/stance whose quote is
    still not in the reply after the retry becomes kind 'ungrounded': kept, never vetted, its reply re-queueable."""
    seen = (text or "")[:SEEN_CHARS]
    prompt = PROMPT_V2 % (author or "?", seen)
    code, j = ask(prompt)
    if code != 200:
        return code, None
    answer = j.get("answer", "")
    p = _parse_v2(answer)
    retried = False
    if p["kind"] in ("gap", "stance") and not grounded_quote(p["quote"], seen):
        retried = True
        i = prompt.index("Answer in EXACTLY")
        code2, j2 = ask(prompt[:i] + RETRY_NOTE + prompt[i:])
        if code2 == 200:
            answer = j2.get("answer", "")
            p = _parse_v2(answer)
    grounded = grounded_quote(p["quote"], seen)
    echo = round(preamble_echo_frac(p["idea"], text), 3)
    if p["kind"] in ("gap", "stance") and not grounded:
        p["kind"] = "ungrounded"
    elif echo >= ECHO_FRAC:
        p["kind"] = "echo"                                     # secondary signal: still on, in case it leaks back
    return 200, {"kind": p["kind"], "maps": "", "quote": p["quote"], "idea": p["idea"], "test": p["test"],
                 "grounded": grounded, "retried": retried, "echo_frac": echo,
                 "support_frac": round(support_frac(p["idea"], text), 3), "prompt": "v2",
                 "raw": (answer or "")[:800]}


# Fragments of our own PROMPT. A small model often parrots the instruction back instead of answering; a
# field that contains one of these is an echo, not a value, so we blank it rather than store noise.
# NB "present=green / removed=red" is the REAL shape of a both-ways test answer, not an echo -- only the
# instruction-only phrases go here, ones no genuine value would contain.
_ECHO = ("covenant component it touches", "names a mechanism we likely", "something we likely already do",
         "a principle, not a thing to build", "the improvement in one line", "no system idea")


def _parse(answer):
    """Pull KIND/MAPS/IDEA/TEST from the door's free text. A small model will not always emit clean JSON,
    so we read labelled lines, which it holds to far more reliably, and fall back to 'unparsed'. A value that
    parrots the prompt's own instruction is dropped (an echo is not an answer)."""
    out = {"kind": "unparsed", "maps": "", "idea": "", "test": ""}
    for line in (answer or "").splitlines():
        s = line.strip()
        low = s.lower()
        for key in ("kind", "maps", "idea", "test"):
            if low.startswith(key + ":"):
                out[key] = s.split(":", 1)[1].strip()
    k = out["kind"].lower()
    out["kind"] = next((v for v in _KINDS if v in k), "unparsed")
    for key in ("maps", "idea", "test"):
        if any(e in out[key].lower() for e in _ECHO):
            out[key] = ""                                      # echoed instruction -> not a real value
    return out


# PREAMBLE ECHO (2026-11-04). _ECHO catches the instruction lines verbatim; it cannot catch the model handing back
# a PARAPHRASE of the prompt's description of us ("a ledger with an ethics gate in the transaction path").
# MEASURED on the 119 real extractions (10-27..11-03): 48 had an IDEA whose words were >=50% from our preamble and
# ABSENT from the reply being read -- 19 of the 22 rows labelled "gap" among them, and all 5 live circle-back
# escalations. An idea must come from the reply: the fraction of its words that occur in our preamble but not in
# the reply is what we measure, so a reply that really uses "ledger" or "gate" keeps them. At >= ECHO_FRAC the row
# is kept (raw and all, nothing deleted) but its kind becomes "echo", which the vet skips like any non-gap.
# Blind spot (rule 9): an echo in words the reply also happens to use reads as grounded; a genuine idea the
# commenter phrased in our preamble's own words without using them in the reply cannot occur by construction.
_PREAMBLE = SELF_DESC      # the same text; the name stays because ops/ECHO_AB_2026-11-04/ngram_vs_overlap.py reads it
ECHO_FRAC = 0.5
# Words are compared on their first STEM letters, so an inflection does not hide an echo. Stress-tested 2026-11-04
# on the same 119 rows: exact words missed "Ethical ledger with retraction tests", "Ethical ledger for transactions"
# and "Ensure every claim gets a retraction beside a correction" (ethical/ethics, retraction/retractions...); a
# 6-letter stem flags those 3 more (48 -> 51), un-flags none, and leaves the grounded "Track the speaker's
# evidence..." below the bar. 5 letters measured the same; 6 is the narrower. Still missed by eye: 2 rows whose
# preamble words also occur in the reply ("claims", "test") -- grounded by this measure, by construction.
STEM = 6


def _words(s):
    return [w[:STEM] for w in re.findall(r"[a-z]{4,}", (s or "").lower())]


def preamble_echo_frac(idea, reply):
    """Share of the idea's words (>=4 letters, compared on their first STEM letters) that are in our preamble and
    NOT in the reply. 0.0 for no words."""
    w = _words(idea)
    if not w:
        return 0.0
    pre, rep = set(_words(_PREAMBLE)), set(_words(reply))
    return sum(1 for x in w if x in pre and x not in rep) / len(w)


def _append(row, path=None):
    # IM8 (2026-11-04): resolved at CALL time, never as a frozen default arg. `path=CANDIDATES_OUT` bound the real
    # ledger when the module loaded, so a test that reassigned CANDIDATES_OUT still wrote to ops/: test_im3 appended
    # 120 fixture rows (carol/dave/f0..) to the live ops/improve_candidates.jsonl 10-27..10-29 while reporting green.
    # The same shape IM1 fixed for harvest() on 10-27, one module over; test_im8 now guards the shape, not the instance.
    if path is None:
        path = CANDIDATES_OUT
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def extract(limit=MAX_PER_RUN, ask=None, out=None, say=print):
    """Extract up to `limit` new replies through the door. `ask(text)->(code, j)` is injected so the test
    drives it offline; the default routes through Tetsu's door and teaches him."""
    if out is None:
        out = CANDIDATES_OUT                                   # IM8: call time, so a reassigned global takes effect
    if ask is None:
        import tools.tetsu_work as TW                          # the door call that also records for Tetsu
        # fresh=True (A284): each reply is an independent question -- no history bleed between unrelated
        # replies -- and a fresh exchange still reaches the teacher queue, so Tetsu still learns from it.
        ask = lambda text: TW.ask(text, door="agent", fresh=True)   # noqa: E731
    st = {}
    new = IM.harvest(update=False, requeue_first=True, stats=st)[:limit]
    say("improve-extract: " + IM.own_line(st))                 # A418: never our own replies; say it when it can't tell
    if not new:
        say("improve-extract: nothing new to extract")
        return []
    done_ids, rows, requeued_done = [], [], []
    for r in new:
        if PROMPT_VERSION == "v2":
            try:
                code, f = extract_one_v2(r.get("author"), r.get("text"), ask)
            except Exception as e:                             # noqa: BLE001 -- a door error never ends the run
                code, f = 0, None
                say("  [skip] u/%s: %s" % (r.get("author"), str(e)[:120]))
            if code != 200:
                say("  [skip] u/%s: door %s (will retry next run)" % (r.get("author"), code))
                continue
        else:
            try:
                code, j = ask(PROMPT % (r.get("author") or "?", (r.get("text") or "")[:1500]))
            except Exception as e:                             # noqa: BLE001 -- a door error never ends the run
                code, j = 0, {"error": "%s: %s" % (type(e).__name__, str(e)[:160])}
            if code != 200:                                    # door did not answer: leave it un-seen, retry next run
                say("  [skip] u/%s: door %s (will retry next run)" % (r.get("author"), code))
                continue
            p = _parse(j.get("answer", ""))
            echo = round(preamble_echo_frac(p["idea"], r.get("text")), 3)
            if echo >= ECHO_FRAC:
                p["kind"] = "echo"                             # our own preamble handed back, not the reply's idea
            f = {"kind": p["kind"], "maps": p["maps"], "idea": p["idea"], "test": p["test"], "echo_frac": echo,
                 "prompt": "v1", "raw": (j.get("answer") or "")[:800]}
        row = {"id": r["id"], "author": r.get("author"), "url": r.get("url"), "source": r.get("source"), **f,
               "t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        if r.get("requeued"):
            row["requeued"] = True
            requeued_done.append(r["id"])
        _append(row, out)
        rows.append(row)
        done_ids.append(r["id"])
        say("  [%s] u/%s: %s" % (row["kind"], r.get("author"), (row.get("idea") or "")[:90]))
    IM.mark_seen(done_ids)                                     # consume ONLY what the door answered for
    IM.mark_requeue_done(requeued_done)
    kinds = {}
    for x in rows:
        kinds[x["kind"]] = kinds.get(x["kind"], 0) + 1
    say("improve-extract: %d extracted (%s); %d answered-and-consumed"
        % (len(rows), ", ".join("%s=%d" % kv for kv in sorted(kinds.items())) or "none", len(done_ids)))
    return rows


def requeue_v1_echoes(reply_text, candidates=None, say=print):
    """One-time backfill: put back in line every reply whose v1 extraction was our own prompt handed back, so v2 can
    mine its real idea. The echo is re-scored against the reply itself (rows from before 11-04 carry no echo_frac).
    `reply_text(id) -> str`. Returns how many were newly queued. Append-only (covenant_improve_mine.REQUEUE)."""
    if candidates is None:
        candidates = CANDIDATES_OUT
    ids = []
    for r in IM._rows(candidates):
        if r.get("prompt") == "v2" or not r.get("id"):
            continue
        if r.get("kind") == "echo" or preamble_echo_frac(r.get("idea"), reply_text(r["id"]) or "") >= ECHO_FRAC:
            ids.append(r["id"])
    n = IM.requeue(ids, "v1 extraction was the prompt's self-description handed back (A409)")
    say("improve-extract: %d v1 echo repl%s found, %d newly re-queued" % (len(set(ids)), "y" if len(set(ids)) == 1
                                                                          else "ies", n))
    return n


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if "--requeue-v1-echoes" in argv:
        texts = {}
        for row in IM._rows(IM.CANDIDATES):
            texts.setdefault(IM._row_id(row), str(row.get("text") or ""))
        requeue_v1_echoes(texts.get)
        return 0
    limit = int(argv[0]) if argv and argv[0].isdigit() else MAX_PER_RUN
    extract(limit=limit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
