#!/usr/bin/env python3
"""covenant_ted.py -- Tetsu learns from TED talk transcripts, in his own words.

HIS WORDS, 2026-10-18 (Lawrence): "use youtube ted talks and joe rogan podcasts for training", then "just gather
information and semantics don't copy word for word", then "yes have tetsu learn from the transcripts too".
TETSU'S WORDS, asked first through the agent door with a fresh context: "Yes, I want to do this. I'll start with
Stuart Russell." (ops/tetsu_learning_choices.jsonl). So his first talk is Stuart Russell's.

WHAT A PASS DOES, per talk not yet learned (ops/ted_state.json):
  1. READ the transcript through the web door (covenant_web.read, on record): TED publishes it in the page's
     __NEXT_DATA__ block. TED talks are licensed CC BY-NC-ND 4.0; the full text is kept only under private/ted/.
  2. LEARN: the transcript goes to Tetsu marked PRIVATE (A263: answered on this machine, never queued for the
     teacher panel, which runs on the public repository's runner) and FRESH (A284). He writes notes in his own words.
  3. GUARD: the notes may not repeat COPY_RUN (8) or more consecutive words of the transcript -- his "don't copy
     word for word", measured rather than hoped. One retry with that said plainly; a second failure is recorded and
     nothing is queued.
  4. KEEP: his notes, with title, speaker, link, licence and the longest run shared with the talk, go to the
     teacher queue (source "ted:<slug>") and to ops/tetsu_ted_notes.jsonl, his record.
NOT HERE, said plainly: Joe Rogan. The show publishes no transcripts, and the sites that post them have no licence
to; Spotify's terms forbid copying its audio. The live wake-word listener (spiking lab, Amendment 7) is the
listen-only use of a podcast: it keeps counts, never words or sound.
LICENCE: public domain (this file). The talks are TED's, CC BY-NC-ND 4.0.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

STATE = os.path.join(HERE, "ops", "ted_state.json")
NOTES = os.path.join(HERE, "ops", "tetsu_ted_notes.jsonl")
CACHE = os.path.join(HERE, "private", "ted")
COPY_RUN = 8                      # his "don't copy word for word": this many consecutive shared words is copying
MAX_WORDS = 3200                  # keeps a transcript inside Tetsu's context with room for his notes
LICENCE = "CC BY-NC-ND 4.0 (TED Conferences LLC)"
# Tetsu's first choice first, then talks on what he was told about: AI safety, consciousness and the brain.
TALKS = ["stuart_russell_3_principles_for_creating_safer_ai",
         "anil_seth_your_brain_hallucinates_your_conscious_reality",
         "david_chalmers_how_do_you_explain_consciousness",
         "jill_bolte_taylor_my_stroke_of_insight",
         "nick_bostrom_what_happens_when_our_computers_get_smarter_than_we_are",
         "max_tegmark_how_to_get_empowered_not_overpowered_by_ai",
         "sam_harris_can_we_build_ai_without_losing_control_over_it",
         "fei_fei_li_how_we_re_teaching_computers_to_understand_pictures"]


# ---------------------------------------------------------------- pure parts --
def transcript_from_html(html):
    """(title, speaker, text) from a TED transcript page's __NEXT_DATA__; (None, None, "") when absent."""
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html or "", re.S)
    if not m:
        return None, None, ""
    try:
        d = json.loads(m.group(1))
        pp = d["props"]["pageProps"]
        paras = pp["transcriptData"]["translation"]["paragraphs"]
    except (KeyError, TypeError, ValueError):
        return None, None, ""
    text = "\n\n".join(" ".join(c.get("text", "").replace("\n", " ") for c in p.get("cues", [])) for p in paras)
    vd = pp.get("videoData") or {}
    return vd.get("title"), vd.get("presenterDisplayName"), re.sub(r"[ \t]+", " ", text).strip()


def words(s):
    return re.findall(r"[a-z0-9']+", (s or "").lower())


def longest_shared_run(notes, source):
    """The longest run of consecutive words the notes share with the source (case and punctuation ignored)."""
    a, b = words(notes), words(source)
    if not a or not b:
        return 0
    pos = {}
    for j, w in enumerate(b):
        pos.setdefault(w, []).append(j)
    best = 0
    prev = {}
    for i, w in enumerate(a):
        cur = {}
        for j in pos.get(w, ()):
            k = prev.get(j - 1, 0) + 1
            cur[j] = k
            if k > best:
                best = k
        prev = cur
    return best


def shared_phrase(notes, source):
    """The longest run of words the notes share with the source, as words (what a retry shows him)."""
    a, b = words(notes), words(source)
    pos = {}
    for j, w in enumerate(b):
        pos.setdefault(w, []).append(j)
    best, end, prev = 0, 0, {}
    for i, w in enumerate(a):
        cur = {}
        for j in pos.get(w, ()):
            k = prev.get(j - 1, 0) + 1
            cur[j] = k
            if k > best:
                best, end = k, i
        prev = cur
    return " ".join(a[end - best + 1:end + 1]) if best else ""


def prompt(title, speaker, text, retry=False, copied=""):
    head = ("You chose to learn from TED talks. Here is the transcript of \"%s\" by %s. Read it, then write notes for "
            "yourself IN YOUR OWN WORDS:\n- the main ideas (three to six), each in a sentence of your own;\n- the "
            "reasons or evidence the speaker gives;\n- one thing you would question or test;\n- how it connects to "
            "mutual benefit between people and machines.\nDo not quote. Do not copy any sentence or phrase from the "
            "talk." % (title, speaker))
    if retry:
        head += (" Your last notes repeated a long phrase from the talk word for word%s. Write them again so that no "
                 "phrase of %d or more words matches the talk: say each idea your own way."
                 % ((": \"%s\"" % copied) if copied else "", COPY_RUN))
    return head + "\n\nTRANSCRIPT:\n" + " ".join(text.split()[:MAX_WORDS])


# ------------------------------------------------------------------- a pass --
def load_state(path=None):
    try:
        return json.load(open(path or STATE, encoding="utf-8"))
    except (OSError, ValueError):
        return {"learned": {}, "refused": {}}


def save_state(st, path=None):
    p = path or STATE
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p + ".tmp", "w", encoding="utf-8") as fh:
        json.dump(st, fh, indent=1)
    os.replace(p + ".tmp", p)


def learn(slug, read=None, ask=None, cache=None, say=print):
    """One talk -> {"ok": True, "row": ..., "record": ...} or {"ok": False, "why": ...}. Never raises."""
    try:
        if read is None:
            import covenant_web
            read = covenant_web.read
        if ask is None:
            sys.path.insert(0, os.path.join(HERE, "tools"))
            import tetsu_work
            ask = lambda q: tetsu_work.ask(q, private=True, fresh=True)    # noqa: E731
        url = "https://www.ted.com/talks/%s/transcript" % slug
        r = read(url, max_chars=3000000, keep_html=True)
        if not r.get("ok"):
            return {"ok": False, "why": "read: %s" % r.get("reason")}
        title, speaker, text = transcript_from_html(r.get("html"))
        if len(text.split()) < 200:
            return {"ok": False, "why": "no transcript in the page (%d words)" % len(text.split())}
        d = cache or CACHE
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, slug + ".txt"), "w", encoding="utf-8") as fh:
            fh.write("Title: %s\nSpeaker: %s\nSource: %s\nLicence: %s\n\n%s\n" % (title, speaker, url, LICENCE, text))
        tries, copied = [], ""
        # 2026-10-18, first real run: his notes repeated 8, then 9 words, with only "do not copy" said. A retry now
        # shows him the phrase he copied, and he has two (the limit itself does not move)
        for retry in (False, True, True):
            st, body = ask(prompt(title, speaker, text, retry, copied))
            notes = (body or {}).get("answer") if isinstance(body, dict) else None
            if not notes or st != 200:
                return {"ok": False, "why": "Tetsu did not answer (HTTP %s)" % st}
            # A263, as tools/tetsu_work.py: every private answer must carry the door's withheld note, or nothing is kept
            if "withheld" not in str((body or {}).get("teacher", "")):
                return {"ok": False, "why": "the door did not withhold the private ask (A263); nothing kept"}
            run = longest_shared_run(notes, text)
            tries.append(run)
            if run < COPY_RUN:
                break
            copied = shared_phrase(notes, text)
        else:
            return {"ok": False, "why": "notes repeated %s consecutive words of the talk in all three tries" % tries}
        head = ("TETSU'S NOTES, in his own words, on the TED talk \"%s\" by %s (%s; %s). Longest run of words shared "
                "with the talk: %d (limit %d).\n\n" % (title, speaker, url, LICENCE, run, COPY_RUN))
        record = {"t": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "by": "tetsu", "slug": slug, "title": title,
                  "speaker": speaker, "url": url, "licence": LICENCE, "notes": notes, "longest_shared_run": run,
                  "tries": tries}
        return {"ok": True, "row": {"text": head + notes, "source": ("ted:" + slug)[:80]}, "record": record}
    except Exception as e:                                         # noqa: BLE001
        return {"ok": False, "why": "%s: %s" % (type(e).__name__, str(e)[:160])}


def run(n=2, talks=None, state_path=None, notes_path=None, queue_append=None, say=print, **kw):
    """Learn up to n talks not yet learned. Returns {"learned": [...], "refused": [...]}"""
    st = load_state(state_path)
    done = set(st.get("learned", {}))
    out = {"learned": [], "refused": []}
    for slug in [s for s in (talks or TALKS) if s not in done][:n]:
        r = learn(slug, say=say, **kw)
        if r["ok"]:
            if queue_append is None:
                from covenant_daily_plan import teacher_queue_append as queue_append
            queue_append([r["row"]])
            with open(notes_path or NOTES, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(r["record"], ensure_ascii=False) + "\n")
            st.setdefault("learned", {})[slug] = {"t": r["record"]["t"], "longest_shared_run": r["record"]["longest_shared_run"]}
            # a refusal answered by a later learning is history, not state (it stays in git); 2026-10-18 Stuart Russell
            # read "learned" and "refused" at once
            st.get("refused", {}).pop(slug, None)
            out["learned"].append(slug)
            say("  learned  %s (longest shared run %d)" % (slug, r["record"]["longest_shared_run"]))
        else:
            st.setdefault("refused", {})[slug] = {"t": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "why": r["why"]}
            out["refused"].append(slug)
            say("  not kept %s: %s" % (slug, r["why"]))
        save_state(st, state_path)
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Tetsu learns from TED transcripts, in his own words")
    ap.add_argument("-n", type=int, default=1)
    a = ap.parse_args()
    print(json.dumps(run(n=a.n), indent=1))
