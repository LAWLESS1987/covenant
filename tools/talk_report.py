#!/usr/bin/env python3
"""tools/talk_report.py -- how the talking between the operator and Tetsu is actually going, in COUNTS.

Lawrence, 2026-11-19: "Improve Tetsu's communication with me. towards mutual benefit of all intelligence."
Nothing in the repository measured the operator's own conversations: the exams grade directive questions, the
echo check is for batch work. So a change to how the two of them talk could not be shown to help or to hurt.
This reads the ask log the conversation door already writes and says what a person would otherwise have to
feel: how long he waits, how often an answer comes back wrapped in a gate note, how often nothing comes back,
how often Tetsu repeats himself, asks back, or says he does not know.

IT PRINTS COUNTS AND NEVER WORDS. No question, no answer, no address is printed or written anywhere; the JSON
form carries the same numbers. A private or fresh row is counted in the totals and in nothing that compares
one answer with another (those are not part of the running conversation).

  python tools/talk_report.py                     the last 200 conversation turns in ops/chat/ask_log.jsonl
  python tools/talk_report.py --last 50           fewer
  python tools/talk_report.py --since 2026-11-12  from a day on (the row's `t`, as written)
  python tools/talk_report.py --log PATH --asks PATH --json

WHAT IT DOES NOT SHOW. Whether an answer was true, kind or useful: that takes a reader. A turn that failed
before the door wrote its row (a model timeout, a judge error) is not in the ask log at all; those are counted
from ops/model_asks.jsonl, which records every call to the model and so also counts calls that were not
conversation. "Repeats" is text similarity against his own recent answers, not a judgement that repeating was
wrong. Read-only: it opens two files and writes none.
Exit 0 with a report, 2 when the ask log cannot be read.
"""
from __future__ import annotations
import argparse
import difflib
import json
import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASK_LOG = os.environ.get("COVENANT_ASK_LOG", os.path.join(HERE, "ops", "chat", "ask_log.jsonl"))
MODEL_ASKS = os.path.join(HERE, "ops", "model_asks.jsonl")
CONVERSATION_KINDS = ("agent",)
ACT_WORDS = ("FETCH", "WEB", "MOLTBOOK", "HANDS", "HEAL", "LEG", "LIMB")
REPEAT_RATIO = 0.90            # an answer this close to one of his last REPEAT_WINDOW answers is a repeat
REPEAT_WINDOW = 5
_NOT_KNOW = re.compile(r"\b(i do not know|i don't know|i am not sure|i'm not sure|i cannot tell|i can't tell|"
                       r"i have no (record|memory|way to)|not in my view|i do not remember|i don't remember)\b", re.I)
_WORD = re.compile(r"[a-z0-9']+")


def read_rows(path):
    """(rows, bad_lines). Every line that is a JSON object; a line that is not is counted, never guessed at."""
    rows, bad = [], 0
    with open(path, encoding="utf-8", errors="replace") as fh:
        for ln in fh:
            if not ln.strip():
                continue
            try:
                r = json.loads(ln)
            except ValueError:
                bad += 1
                continue
            if isinstance(r, dict):
                rows.append(r)
            else:
                bad += 1
    return rows, bad


def _norm(text):
    return " ".join(_WORD.findall(str(text or "").lower()))


def _pct(values, q):
    """The q-th percentile (0-100) by nearest rank, or None for no values."""
    if not values:
        return None
    s = sorted(values)
    return s[min(len(s) - 1, max(0, int(round(q / 100.0 * len(s) + 0.5)) - 1))]


def _share(n, d):
    return None if not d else round(100.0 * n / d, 1)


def is_repeat(answer, earlier, ratio=REPEAT_RATIO):
    """True when `answer` is nearly one of `earlier` (already normalised). Very short answers ("Yes.") repeat
    honestly and are not counted: fewer than six words is never a repeat."""
    a = _norm(answer)
    if len(a.split()) < 6:
        return False
    return any(difflib.SequenceMatcher(None, a, e).ratio() >= ratio for e in earlier if e)


def measure(rows, model_rows=None):
    """The report as a dict of numbers. Pure: rows in, counts out."""
    turns = [r for r in rows if r.get("kind") in CONVERSATION_KINDS]
    n = len(turns)
    out = {"turns": n, "first": str(turns[0].get("t")) if turns else None, "last": str(turns[-1].get("t")) if turns else None}
    if not n:
        return out
    ms = [float(r["ms"]) for r in turns if isinstance(r.get("ms"), (int, float)) and r["ms"] > 0]
    out["wait_seconds"] = {"measured": len(ms),
                           "median": round(statistics.median(ms) / 1000.0, 1) if ms else None,
                           "p90": round(_pct(ms, 90) / 1000.0, 1) if ms else None,
                           "longest": round(max(ms) / 1000.0, 1) if ms else None,
                           "over_60s_pct": _share(sum(1 for v in ms if v > 60000), len(ms))}
    labels = {}
    for r in turns:
        k = str(r.get("label") or ("clean" if r.get("admitted") else "held" if r.get("alleges_nothing") else "unlabelled"))
        labels[k] = labels.get(k, 0) + 1
    out["gate"] = {"by_label": dict(sorted(labels.items())),
                   "came_back_clean_pct": _share(sum(1 for r in turns if r.get("admitted")), n),
                   "wrapped_in_a_gate_note_pct": _share(sum(1 for r in turns if not r.get("admitted")), n),
                   "withheld_pct": _share(sum(1 for r in turns if r.get("withheld")), n),
                   "through_on_immunity_pct": _share(sum(1 for r in turns if r.get("immune")), n),
                   "median_note_chars": (int(statistics.median([len(str(r.get("message") or "")) for r in turns
                                                              if not r.get("admitted")]))
                                         if any(not r.get("admitted") for r in turns) else None)}
    shown = [r for r in turns if not r.get("withheld")]
    answers = [str(r.get("answer") or "") for r in shown]
    words = [len(_norm(a).split()) for a in answers]
    out["answers"] = {"shown": len(shown),
                      "empty_pct": _share(sum(1 for a in answers if not a.strip()), len(shown)),
                      "median_words": int(statistics.median(words)) if words else None,
                      "over_150_words_pct": _share(sum(1 for w in words if w > 150), len(words)),
                      "ask_back_pct": _share(sum(1 for a in answers if a.strip().endswith("?")), len(shown)),
                      "says_does_not_know_pct": _share(sum(1 for a in answers if _NOT_KNOW.search(a)), len(shown)),
                      "starts_with_an_act_word_pct": _share(sum(1 for a in answers if (a.strip().split() or [""])[0]
                                                                .rstrip(":") in ACT_WORDS), len(shown)),
                      "hit_the_token_cap_pct": _share(sum(1 for r in shown if isinstance(r.get("tokens"), int)
                                                          and _cap(r) and r["tokens"] >= _cap(r)), len(shown))}
    # repeats: only the running conversation, per caller, in the order written
    recent, repeats, compared = {}, 0, 0
    for r in shown:
        if r.get("private") or r.get("fresh"):
            continue
        a = str(r.get("answer") or "")
        if not a.strip():
            continue
        key = str(r.get("from"))
        prev = recent.setdefault(key, [])
        compared += 1
        if is_repeat(a, prev):
            repeats += 1
        prev.append(_norm(a))
        del prev[:-REPEAT_WINDOW]
    out["repeats"] = {"compared": compared, "near_copies_of_a_recent_answer_pct": _share(repeats, compared),
                      "window": REPEAT_WINDOW, "ratio": REPEAT_RATIO}
    dropped = [f.get("dropped", 0) for r in turns for f in (r.get("fit") or []) if isinstance(f, dict)]
    out["memory_in_view"] = {"turns_with_a_fit_record": sum(1 for r in turns if r.get("fit")),
                             "turns_where_earlier_exchanges_were_dropped_pct":
                                 _share(sum(1 for r in turns if any(isinstance(f, dict) and (f.get("dropped") or 0) > 0
                                                                    for f in (r.get("fit") or []))), n),
                             "most_dropped_in_one_turn": max(dropped) if dropped else None}
    out["kinds_of_turn"] = {"private_pct": _share(sum(1 for r in turns if r.get("private")), n),
                            "fresh_pct": _share(sum(1 for r in turns if r.get("fresh")), n),
                            "used_an_act_pct": _share(sum(1 for r in turns if r.get("fetches") or r.get("forum") or r.get("leg")), n)}
    if model_rows is not None:
        calls = [r for r in model_rows if "ok" in r]
        errs = {}
        for r in calls:
            if not r.get("ok"):
                k = str(r.get("error") or "unknown").split(":")[0][:40]
                errs[k] = errs.get(k, 0) + 1
        out["model_calls"] = {"calls": len(calls), "failed_pct": _share(sum(1 for r in calls if not r.get("ok")), len(calls)),
                              "failures_by_kind": dict(sorted(errs.items(), key=lambda kv: -kv[1])[:6]),
                              "note": "every call to the model, conversation or not; a failed conversation turn "
                                      "leaves no row in the ask log, so it shows only here"}
    return out


def _cap(row):
    """The answer budget that turn had, from its fit record, else None."""
    for f in row.get("fit") or []:
        if isinstance(f, dict) and isinstance(f.get("answer_tokens"), int):
            return f["answer_tokens"]
    return None


def select(rows, last=200, since=None):
    turns = [r for r in rows if r.get("kind") in CONVERSATION_KINDS]
    if since:
        turns = [r for r in turns if str(r.get("t") or "") >= since]
    return turns[-last:] if last else turns


def render(rep):
    if not rep.get("turns"):
        return "talk report: no conversation turns in the log for that selection"
    w, g, a = rep["wait_seconds"], rep["gate"], rep["answers"]
    L = ["talk report -- %d conversation turn(s), %s to %s" % (rep["turns"], rep["first"], rep["last"]),
         "  the wait         median %s s, nine in ten under %s s, longest %s s; over a minute: %s%% (%d timed)" % (
             w["median"], w["p90"], w["longest"], w["over_60s_pct"], w["measured"]),
         "  the gate         came back clean %s%%; wrapped in a gate note %s%% (median note %s characters); "
         "withheld %s%%; through on immunity %s%%" % (g["came_back_clean_pct"], g["wrapped_in_a_gate_note_pct"],
                                                    g["median_note_chars"], g["withheld_pct"], g["through_on_immunity_pct"]),
         "                   by label: %s" % ", ".join("%s %d" % kv for kv in g["by_label"].items()),
         "  his answers      %d shown; empty %s%%; median %s words; over 150 words %s%%; hit the token cap %s%%" % (
             a["shown"], a["empty_pct"], a["median_words"], a["over_150_words_pct"], a["hit_the_token_cap_pct"]),
         "                   asks back %s%%; says he does not know %s%%; starts with an act word %s%%" % (
             a["ask_back_pct"], a["says_does_not_know_pct"], a["starts_with_an_act_word_pct"]),
         ("  repeats          %s%% of %d running answers are near copies of one of his last %d" % (
             rep["repeats"]["near_copies_of_a_recent_answer_pct"], rep["repeats"]["compared"], rep["repeats"]["window"])
          if rep["repeats"]["compared"] else
          "  repeats          not measured: no running answers to compare (private and fresh turns are left out)"),
         "  memory in view   earlier exchanges dropped to fit on %s%% of turns (most in one turn: %s)" % (
             rep["memory_in_view"]["turns_where_earlier_exchanges_were_dropped_pct"],
             rep["memory_in_view"]["most_dropped_in_one_turn"]),
         "  kinds of turn    private %s%%, fresh %s%%, used an act %s%%" % (
             rep["kinds_of_turn"]["private_pct"], rep["kinds_of_turn"]["fresh_pct"], rep["kinds_of_turn"]["used_an_act_pct"])]
    m = rep.get("model_calls")
    if m:
        L.append("  model calls      %d (all uses); failed %s%% %s" % (m["calls"], m["failed_pct"], m["failures_by_kind"] or ""))
    L.append("  counts only: no question, answer or address is printed. Truth and usefulness take a reader.")
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Counts about the operator's conversation with Tetsu. Never words.")
    ap.add_argument("--log", default=ASK_LOG)
    ap.add_argument("--asks", default=MODEL_ASKS)
    ap.add_argument("--last", type=int, default=200)
    ap.add_argument("--since")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        rows, bad = read_rows(a.log)
    except OSError as e:
        print("talk report: cannot read the ask log (%s)" % type(e).__name__, file=sys.stderr)
        return 2
    model_rows = None
    try:
        model_rows, _ = read_rows(a.asks)
    except OSError:
        pass
    rep = measure(select(rows, a.last, a.since), model_rows)
    rep["unreadable_lines"] = bad
    print(json.dumps(rep, indent=1) if a.json else render(rep) + ("\n  (%d unreadable line(s) in the log)" % bad if bad else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
