#!/usr/bin/env python3
"""test_ted1_learn.py -- TED1: Tetsu learns from TED transcripts in his own words (covenant_ted.py). Offline: the web
door and Tetsu are stubs, the queue and the state are temp files; nothing is read from the network, no model is
asked, nothing reaches the real teacher queue.  Run: python test_ted1_learn.py   Tally: `TED1: n/n passed`."""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_ted as T  # noqa: E402

RAN, FAILS = [], []


def check(name, cond, detail=""):
    RAN.append(bool(cond))
    print(("ok    " if cond else "FAIL  ") + name + ("" if cond or detail == "" else "  -- %s" % (detail,)))
    if not cond:
        FAILS.append(name)


TALK = ("Machines that pursue fixed objectives can be dangerous because they will resist being switched off . "
        "The first principle is that the robot's only objective is to maximize the realization of human values . ") * 30
page = ('<html><script id="__NEXT_DATA__" type="application/json">%s</script></html>' % json.dumps(
    {"props": {"pageProps": {"videoData": {"title": "3 principles", "presenterDisplayName": "Stuart Russell"},
                             "transcriptData": {"translation": {"paragraphs": [{"cues": [{"text": TALK[:400]}, {"text": TALK[400:]}]}]}}}}}))
title, speaker, text = T.transcript_from_html(page)
check("TED1.1 the transcript, title and speaker come out of __NEXT_DATA__", title == "3 principles" and speaker == "Stuart Russell"
      and "switched off" in text and len(text.split()) > 200, (title, speaker, len(text.split())))
check("TED1.2 a page without the block gives no transcript, never a guess", T.transcript_from_html("<html>x</html>") == (None, None, ""))
check("TED1.3 the shared run counts consecutive words, ignoring case and punctuation",
      T.longest_shared_run("They Resist being SWITCHED off, he says", TALK) == 4
      and T.longest_shared_run("nothing here matches at all zebra", TALK) <= 2, T.longest_shared_run("They Resist being SWITCHED off, he says", TALK))
own = "A goal-driven system might fight shutdown; Russell wants machines unsure of what we want, so they defer to us."
copied = "He said the robot's only objective is to maximize the realization of human values, which is his first rule."


def run_with(answers, slug="stuart_russell_3_principles_for_creating_safer_ai", withheld=True):
    d = tempfile.mkdtemp(prefix="ted1_")
    q, asked = [], []
    it = iter(answers)

    def ask(prompt_text):
        asked.append(prompt_text)
        return 200, {"answer": next(it), "withheld": withheld, "teacher": "withheld: private (A263)" if withheld else "queued"}
    r = T.run(n=1, talks=[slug], state_path=os.path.join(d, "s.json"), notes_path=os.path.join(d, "n.jsonl"),
              queue_append=lambda rows: q.extend(rows), say=lambda *a: None,
              read=lambda url, **k: {"ok": True, "html": page}, ask=ask, cache=os.path.join(d, "cache"))
    notes = [json.loads(l) for l in open(os.path.join(d, "n.jsonl"), encoding="utf-8")] if os.path.exists(os.path.join(d, "n.jsonl")) else []
    return r, q, asked, notes, json.load(open(os.path.join(d, "s.json")))


r, q, asked, notes, st = run_with([own])
check("TED1.4 own-words notes are kept: one queue row (source ted:<slug>), one record, state says learned",
      r["learned"] and len(q) == 1 and q[0]["source"].startswith("ted:stuart_russell") and len(notes) == 1
      and "stuart_russell_3_principles_for_creating_safer_ai" in st["learned"], (r, q))
check("TED1.5 the queued row carries his notes, the talk's licence and the shared run -- never the transcript",
      own in q[0]["text"] and "CC BY-NC-ND" in q[0]["text"] and "switched off" not in q[0]["text"], q[0]["text"][:200])
r, q, asked, notes, st = run_with([copied, own])
check("TED1.6 notes that copy 8+ words get a retry that SHOWS him the copied phrase; the retry in his own words is kept",
      r["learned"] and len(asked) == 2 and "word for word" in asked[1]
      and "the robot's only objective is to maximize the realization of human values" in asked[1]
      and notes[0]["tries"][0] >= T.COPY_RUN and notes[0]["longest_shared_run"] < T.COPY_RUN, (len(asked), notes and notes[0]["tries"]))
r, q, asked, notes, st = run_with([copied, copied, copied])
check("TED1.7 copying in all three tries: nothing queued, nothing kept, the refusal recorded with the runs",
      not r["learned"] and r["refused"] and not q and not notes and "consecutive words" in st["refused"][r["refused"][0]]["why"], (r, st))
r, q, asked, notes, st = run_with([own], withheld=False)
check("TED1.8 a door that did not withhold the private ask: nothing kept (A263)", not q and not notes and r["refused"], (r, st))
# TED1.9 RUNS the real ask path (ask=None) against a stand-in tetsu_work and records the call -- the first version read
# the source text for "private=True, fresh=True", which is A65's fake-guard shape
import types  # noqa: E402
_calls = []
_fake = types.ModuleType("tetsu_work")
_fake.ask = lambda q, **k: (_calls.append(k), (200, {"answer": own, "teacher": "withheld: private (A263)"}))[1]
_saved_tw = sys.modules.get("tetsu_work")
sys.modules["tetsu_work"] = _fake
try:
    _r9 = T.learn("stuart_russell_3_principles_for_creating_safer_ai", read=lambda url, **k: {"ok": True, "html": page},
                  cache=tempfile.mkdtemp(prefix="ted1_9_"))
finally:
    if _saved_tw is None:
        sys.modules.pop("tetsu_work", None)
    else:
        sys.modules["tetsu_work"] = _saved_tw
check("TED1.9 the real ask path sends the transcript to Tetsu with private=True and fresh=True",
      _r9.get("ok") and _calls and all(c.get("private") is True and c.get("fresh") is True for c in _calls), (_r9, _calls))
check("TED1.10 Tetsu's first choice comes first", T.TALKS[0].startswith("stuart_russell"))

# TED1.11: refused on one pass, learned on the next -- the state says learned only
_d11 = tempfile.mkdtemp(prefix="ted1_11_")
_sp = os.path.join(_d11, "s.json")
for _answers in ([copied, copied, copied], [own]):
    _it = iter(_answers)
    T.run(n=1, talks=["stuart_russell_3_principles_for_creating_safer_ai"], state_path=_sp,
          notes_path=os.path.join(_d11, "n.jsonl"), queue_append=lambda rows: None, say=lambda *a: None,
          read=lambda url, **k: {"ok": True, "html": page}, cache=os.path.join(_d11, "c"),
          ask=lambda q: (200, {"answer": next(_it), "teacher": "withheld: private (A263)"}))
_st11 = json.load(open(_sp))
# TED1.12: the OpenAlex route -- a stub API with two works' inverted-index abstracts, a stub Tetsu
def _inv(s):                       # OpenAlex's inverted index: every position of each word (the first stub kept one)
    out = {}
    for i, w in enumerate(s.split()):
        out.setdefault(w, []).append(i)
    return out
_abs1 = " ".join("silicon retina adaptive photoreceptor analog circuit models the outer plexiform layer".split() * 12)
_abs2 = " ".join("address event representation carries spikes between chips on a shared digital bus".split() * 12)
_api = lambda url: {"results": [{"title": "Silicon retina", "publication_year": 1991, "abstract_inverted_index": _inv(_abs1)},
                                {"title": "AER", "publication_year": 1992, "abstract_inverted_index": _inv(_abs2)}]}   # noqa: E731
_d12 = tempfile.mkdtemp(prefix="ted1_12_")
_q12, _asked12 = [], []
_r12 = T.learn_open("A5038154254", "Misha A. Mahowald", api=_api, state_path=os.path.join(_d12, "s.json"),
                    notes_path=os.path.join(_d12, "n.jsonl"), queue_append=lambda rows: _q12.extend(rows),
                    cache=os.path.join(_d12, "c"), say=lambda *a: None,
                    ask=lambda q: (_asked12.append(q), (200, {"answer": "Her chips mimic the eye's first layers and send "
                                   "events only when something changes.", "teacher": "withheld: private (A263)"}))[1])
check("TED1.12 OpenAlex route: abstracts become one private text for Tetsu; his own-words notes are queued as "
      "openalex:<id>, attributed, never the abstracts", _r12["learned"] == ["openalex:A5038154254"] and len(_q12) == 1
      and _q12[0]["source"] == "openalex:A5038154254" and "OpenAlex" in _q12[0]["text"] and "plexiform" not in _q12[0]["text"]
      and "plexiform" in _asked12[0], (_r12, _q12[:1]))
check("TED1.11 a talk refused and then learned is no longer listed as refused",
      "stuart_russell_3_principles_for_creating_safer_ai" in _st11["learned"] and not _st11.get("refused"), _st11)

print()
if FAILS:
    print("%d FAILED" % len(FAILS))
    sys.exit(1)
print("TED1: %d/%d passed (offline: stub door, stub Tetsu, temp queue)" % (len(RAN), len(RAN)))
