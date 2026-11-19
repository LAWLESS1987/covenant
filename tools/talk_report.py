#!/usr/bin/env python3
"""tools/talk_report.py -- how the talking between the operator and Tetsu is actually going, in COUNTS.

Lawrence, 2026-11-19: "Improve Tetsu's communication with me. towards mutual benefit of all intelligence."
Nothing in the repository measured the operator's own conversations: the exams grade directive questions, the
echo check is for batch work. So a change to how the two of them talk could not be shown to help or to hurt.
This reads the ask log the conversation door already writes and says what a person would otherwise have to
feel: how long he waits, how often an answer comes back wrapped in a gate note, how often nothing comes back,
how often Tetsu repeats himself, asks back, or says he does not know.

IT PRINTS COUNTS AND NEVER WORDS. No question, no answer, no address is printed or written anywhere; the JSON
form carries the same numbers. Callers are named by rank ("caller 1"), never by address.

IT MEASURES THE RUNNING CONVERSATION, and says how much else the door carried. The same door serves batch
work: a `fresh` ask replays no earlier turn and a `private` one is kept out of the history. The first version
took "the last 200 turns" by kind alone, and on the laptop's real log (2026-11-19, read by the laptop session)
all 200 were fresh batch asks, 125 of them one-word answers: median wait 7.5 s, when his own last 200 running
turns had a median of 56.6 s. Of 5,711 rows 391 were the running conversation. So the selection is `running`
unless asked otherwise, and the first line of the report says how the log divides.

  python tools/talk_report.py                     the last 200 RUNNING turns in ops/chat/ask_log.jsonl
  python tools/talk_report.py --last 50           fewer
  python tools/talk_report.py --since 2026-11-12  from a day on (the row's `t`, as written)
  python tools/talk_report.py --which fresh       the batch asks instead (running | fresh | private | all)
  python tools/talk_report.py --caller 1          only the busiest caller's turns (rank within the selection)
  python tools/talk_report.py --log PATH --asks PATH --json

WHAT IT DOES NOT SHOW. Whether an answer was true, kind or useful: that takes a reader. A turn that failed
before the door wrote its row (a model timeout, a judge error) is not in the ask log at all; those are counted
from ops/model_asks.jsonl, which records every call to the model and so also counts calls that were not
conversation, and that file carries no time this tool reads, so its line is the WHOLE file and not the window.
"Repeats" is text similarity against his own recent answers, not a judgement that repeating was wrong. "Says he
does not know" and "hedges" are phrase lists: a zero may mean he never says it or that he says it another way.
`kept` and `dropped` in a fit record are MESSAGES, two to an exchange. Read-only: it opens two files and writes none.
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
HISTORY_CAP_MESSAGES = 40      # the door replays at most 20 exchanges (AGENT_HISTORY_TURNS); TQ1 pins the two together
REPEAT_RATIO = 0.90            # an answer this close to one of his last REPEAT_WINDOW answers is a repeat
REPEAT_WINDOW = 5
_NOT_KNOW = re.compile(r"\b(i do not know|i don't know|i am not sure|i'm not sure|i cannot tell|i can't tell|"
                       r"i have no (record|memory|way to)|not in my view|i do not remember|i don't remember)\b", re.I)
_HEDGE = re.compile(r"\b(not (entirely |completely |quite )?(sure|certain)|unsure|uncertain|i (may|might|could) be wrong|"
                    r"i think|i believe|as far as i (know|can tell)|if i (recall|remember)|i cannot (see|find|access)|"
                    r"i can't (see|find|access)|i do not have|i don't have)\b", re.I)
_WORD = re.compile(r"[a-z0-9']+")


def kind_of(row):
    """running | fresh | private: which use of the door a conversation row was."""
    return "fresh" if row.get("fresh") else "private" if row.get("private") else "running"


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
                      "hedges_pct": _share(sum(1 for a in answers if _HEDGE.search(a) or _NOT_KNOW.search(a)), len(shown)),
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
    def first_fit(r):                       # the first model call of the turn is the one that carried the history
        for f in r.get("fit") or []:
            if isinstance(f, dict):
                return f
        return {}
    fits = [first_fit(r) for r in turns]
    dropped = [int(f.get("dropped") or 0) for f in fits if isinstance(f.get("dropped"), int)]
    kept = [int(f.get("kept") or 0) for f in fits if isinstance(f.get("kept"), int)]
    out["memory_in_view"] = {"turns_with_a_fit_record": sum(1 for f in fits if f),
                             "turns_where_earlier_exchanges_were_dropped_pct": _share(sum(1 for d in dropped if d > 0), n),
                             "most_exchanges_dropped_in_one_turn": (max(dropped) + 1) // 2 if dropped else None,
                             "median_exchanges_in_view": int(statistics.median(kept)) // 2 if kept else None,
                             "turns_at_the_history_cap_pct": _share(sum(1 for k in kept if k >= HISTORY_CAP_MESSAGES), n),
                             "note": "at the cap, anything said more than %d exchanges ago was out of his view"
                                     % (HISTORY_CAP_MESSAGES // 2)}
    by_caller = {}
    for r in turns:
        by_caller.setdefault(str(r.get("from")), []).append(r)
    ranked = sorted(by_caller.values(), key=lambda rs: -len(rs))
    out["callers"] = {"distinct": len(ranked),
                      "by_rank": [{"caller": i + 1, "turns": len(rs),
                                   "median_wait_s": (round(statistics.median([float(x["ms"]) for x in rs
                                                                              if isinstance(x.get("ms"), (int, float)) and x["ms"] > 0]) / 1000.0, 1)
                                                     if any(isinstance(x.get("ms"), (int, float)) and x["ms"] > 0 for x in rs) else None)}
                                  for i, rs in enumerate(ranked[:5])]}
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
                              "note": "THE WHOLE FILE, not this window: every call to the model, conversation or "
                                      "not; a failed conversation turn leaves no row in the ask log, so it shows only here"}
    return out


def _cap(row):
    """The answer budget that turn had, from its fit record, else None."""
    for f in row.get("fit") or []:
        if isinstance(f, dict) and isinstance(f.get("answer_tokens"), int):
            return f["answer_tokens"]
    return None


def divide(rows, since=None):
    """How the door's conversation rows divide: {"running": n, "fresh": n, "private": n}."""
    out = {"running": 0, "fresh": 0, "private": 0}
    for r in rows:
        if r.get("kind") in CONVERSATION_KINDS and (not since or str(r.get("t") or "") >= since):
            out[kind_of(r)] += 1
    return out


def select(rows, last=200, since=None, which="running", caller=None):
    """The turns to measure. `which` is running (the default: his own conversation), fresh, private or all, and
    is applied BEFORE `last`, so "the last 200" are the last 200 of that kind. `caller` is a rank (1 = busiest)
    within what is left."""
    turns = [r for r in rows if r.get("kind") in CONVERSATION_KINDS and (which == "all" or kind_of(r) == which)]
    if since:
        turns = [r for r in turns if str(r.get("t") or "") >= since]
    if caller:
        counts = {}
        for r in turns:
            counts[str(r.get("from"))] = counts.get(str(r.get("from")), 0) + 1
        ranked = sorted(counts, key=lambda k: -counts[k])
        want = ranked[caller - 1] if 0 < caller <= len(ranked) else None
        turns = [r for r in turns if str(r.get("from")) == want]
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
         "                   ends with a question %s%%; says he does not know %s%%; hedges %s%%; starts with an act word %s%%" % (
             a["ask_back_pct"], a["says_does_not_know_pct"], a["hedges_pct"], a["starts_with_an_act_word_pct"]),
         ("  repeats          %s%% of %d running answers are near copies of one of his last %d" % (
             rep["repeats"]["near_copies_of_a_recent_answer_pct"], rep["repeats"]["compared"], rep["repeats"]["window"])
          if rep["repeats"]["compared"] else
          "  repeats          not measured: no running answers to compare (private and fresh turns are left out)"),
         "  memory in view   median %s exchanges in view; at the %d-exchange cap on %s%% of turns; dropped to fit "
         "on %s%% (most in one turn: %s)" % (
             rep["memory_in_view"]["median_exchanges_in_view"], HISTORY_CAP_MESSAGES // 2,
             rep["memory_in_view"]["turns_at_the_history_cap_pct"],
             rep["memory_in_view"]["turns_where_earlier_exchanges_were_dropped_pct"],
             rep["memory_in_view"]["most_exchanges_dropped_in_one_turn"]),
         "  callers          %d distinct; by rank: %s" % (
             rep["callers"]["distinct"], ", ".join("caller %d: %d turns, median wait %s s" % (
                 c["caller"], c["turns"], c["median_wait_s"]) for c in rep["callers"]["by_rank"])),
         "  kinds of turn    private %s%%, fresh %s%%, used an act %s%%" % (
             rep["kinds_of_turn"]["private_pct"], rep["kinds_of_turn"]["fresh_pct"], rep["kinds_of_turn"]["used_an_act_pct"])]
    m = rep.get("model_calls")
    if m:
        L.append("  model calls      %d in the WHOLE file (all uses, not this window); failed %s%% %s" % (
            m["calls"], m["failed_pct"], m["failures_by_kind"] or ""))
    L.append("  counts only: no question, answer or address is printed. Truth and usefulness take a reader.")
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Counts about the operator's conversation with Tetsu. Never words.")
    ap.add_argument("--log", default=ASK_LOG)
    ap.add_argument("--asks", default=MODEL_ASKS)
    ap.add_argument("--last", type=int, default=200)
    ap.add_argument("--since")
    ap.add_argument("--which", choices=("running", "fresh", "private", "all"), default="running")
    ap.add_argument("--caller", type=int, help="a rank within the selection: 1 is the busiest caller")
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
    rep = measure(select(rows, a.last, a.since, a.which, a.caller), model_rows)
    rep["unreadable_lines"] = bad
    rep["selection"] = {"which": a.which, "caller": a.caller, "the_log_divides": divide(rows, a.since)}
    d = rep["selection"]["the_log_divides"]
    head = "the door carried %d running, %d fresh and %d private conversation row(s)%s; measured below: %s%s\n" % (
        d["running"], d["fresh"], d["private"], (" since %s" % a.since) if a.since else "", a.which,
        (", caller %d" % a.caller) if a.caller else "")
    print(json.dumps(rep, indent=1) if a.json else head + render(rep) + ("\n  (%d unreadable line(s) in the log)" % bad if bad else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
