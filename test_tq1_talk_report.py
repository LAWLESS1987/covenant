"""TQ1 -- tools/talk_report.py counts the operator's conversation with Tetsu, and prints no words.

Both ways on a made-up ask log in a temp directory: a quiet, healthy conversation reads healthy, and each fault
(a long wait, a gate note on every answer, an empty answer, a repeat, an act word left in the answer, earlier
exchanges dropped, a failed model call) moves the one number that is meant to see it. And the bar the tool sets
for itself: nothing a person typed, nothing Tetsu said and no address appears in either output form.
Nothing here reads the real ask log. Run: python test_tq1_talk_report.py"""
import io
import json
import os
import sys
import tempfile
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
import talk_report as T  # noqa: E402

results = []


def check(label, ok, detail=""):
    results.append((label, bool(ok)))
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", label, ("  -- " + str(detail)) if detail and not ok else ""))


SECRET_Q = "zebra-question-marker what is the weather on the moon"
SECRET_A = "quokka-answer-marker the moon has no weather that I can see from here today"
ADDR = "203.0.113.77"
VARIED = ["the ledger grew by three blocks overnight and every peer agreed on the tip",
          "nothing new arrived from the forum so I spent the hour rereading old notes",
          "your second idea is the stronger one because it needs no extra key at all",
          "I could not open that page and so I have nothing honest to report about it",
          "the garden metaphor fits better than the machine one for what we are building",
          "two tests failed for the same reason and that reason is a missing folder",
          "tomorrow I would start with the smallest repair and measure before touching more",
          "that name is unknown to me and I would rather ask than guess who it is",
          "the phone lost its road twice today and found another one both times quickly",
          "a short answer serves you here so I will stop after this single sentence"]


def turn(i, answer=SECRET_A, ms=20000, admitted=True, **over):
    r = {"kind": "agent", "from": ADDR, "t": "2026-11-19T10:%02d:00" % i, "text": SECRET_Q + " %d" % i,
         "answer": answer if answer != SECRET_A else SECRET_A + " " + VARIED[i % len(VARIED)],
         "withheld": False, "admitted": admitted, "alleges_nothing": not admitted, "immune": False,
         "message": "ok" if admitted else "Held, not judged: local:0: HELD -- both seats held; the question waits",
         "label": "clean" if admitted else "held", "model": "m", "tokens": 40, "ms": ms,
         "fit": [{"answer_tokens": 700, "ctx": 8192, "dropped": 0, "kept": 3, "prompt_tokens": 3000}]}
    r.update(over)
    return r


def main():
    healthy = [turn(i) for i in range(1, 11)]
    rep = T.measure(healthy, model_rows=[{"ok": True, "ms": 1}] * 10)
    check("TQ1a a healthy conversation: 10 turns, median wait 20 s, none over a minute",
          rep["turns"] == 10 and rep["wait_seconds"]["median"] == 20.0 and rep["wait_seconds"]["over_60s_pct"] == 0.0, rep.get("wait_seconds"))
    check("TQ1a ...all clean, none wrapped, none empty, no repeats, nothing dropped, no failed call",
          rep["gate"]["came_back_clean_pct"] == 100.0 and rep["gate"]["wrapped_in_a_gate_note_pct"] == 0.0
          and rep["answers"]["empty_pct"] == 0.0 and rep["repeats"]["near_copies_of_a_recent_answer_pct"] == 0.0
          and rep["memory_in_view"]["turns_where_earlier_exchanges_were_dropped_pct"] == 0.0
          and rep["model_calls"]["failed_pct"] == 0.0, rep)

    slow = [turn(i, ms=95000 if i > 5 else 20000) for i in range(1, 11)]
    w = T.measure(slow)["wait_seconds"]
    check("TQ1b five slow turns: half are over a minute and the ninth-in-ten wait is 95 s",
          w["over_60s_pct"] == 50.0 and w["p90"] == 95.0 and w["longest"] == 95.0, w)

    held = [turn(i, admitted=False) for i in range(1, 11)]
    g = T.measure(held)["gate"]
    check("TQ1c every answer held: none clean, all wrapped, and the note's length is measured",
          g["came_back_clean_pct"] == 0.0 and g["wrapped_in_a_gate_note_pct"] == 100.0 and g["by_label"] == {"held": 10}
          and g["median_note_chars"] == len(held[0]["message"]), g)
    wh = T.measure([turn(1), turn(2, withheld=True, admitted=False, answer="", label="lexical-detection"),
                    turn(3, immune=True, admitted=False, label="lexical-detection")])
    check("TQ1c a withheld turn and an immune one are each counted, and a withheld answer is not 'shown'",
          wh["gate"]["withheld_pct"] == 33.3 and wh["gate"]["through_on_immunity_pct"] == 33.3 and wh["answers"]["shown"] == 2, wh["gate"])

    rows = [turn(i) for i in range(1, 9)] + [dict(turn(9), answer="   "), dict(turn(10), answer="")]
    check("TQ1d two empty answers of ten are 20 percent empty", T.measure(rows)["answers"]["empty_pct"] == 20.0)

    same = "I think the plan is sound and we should carry on with the next step together"
    rep_rows = [turn(1)] + [dict(turn(i), answer=same + ("." if i % 2 else "!")) for i in range(2, 6)]
    r = T.measure(rep_rows)["repeats"]
    check("TQ1e the same sentence four times is three repeats of five compared (the first time is not one)",
          r["compared"] == 5 and r["near_copies_of_a_recent_answer_pct"] == 60.0, r)
    short = [dict(turn(i), answer="Yes.") for i in range(1, 6)]
    check("TQ1e a short honest 'Yes.' five times is never counted as a repeat",
          T.measure(short)["repeats"]["near_copies_of_a_recent_answer_pct"] == 0.0)
    priv = [dict(turn(i), answer=same, private=True) for i in range(1, 4)] + [dict(turn(4), answer=same, fresh=True)]
    check("TQ1e private and fresh turns are not part of the running conversation: nothing is compared",
          T.measure(priv)["repeats"]["compared"] == 0)
    check("TQ1e ...and the report says 'not measured' for it, never 'None%'",
          "not measured" in T.render(T.measure(priv)) and "None%" not in T.render(T.measure(priv)))
    check("TQ1e is_repeat both ways", T.is_repeat(same, [T._norm(same + "!")]) and not T.is_repeat(same, [T._norm(SECRET_A + " and more words here")]))

    acts = [turn(1), dict(turn(2), answer="FETCH https://example.org/page"), dict(turn(3), answer="I do not know that yet."),
            dict(turn(4), answer="Which of the two did you mean?"), dict(turn(5), tokens=700)]
    a = T.measure(acts)["answers"]
    check("TQ1f an act word left as the answer, an 'I do not know', a question back and a capped answer: one each of five",
          a["starts_with_an_act_word_pct"] == 20.0 and a["says_does_not_know_pct"] == 20.0 and a["ask_back_pct"] == 20.0
          and a["hit_the_token_cap_pct"] == 20.0, a)

    # kept and dropped are MESSAGES, two to an exchange (covenant_model.fit); the report speaks in exchanges
    drop = [turn(1), dict(turn(2), fit=[{"answer_tokens": 700, "dropped": 6, "kept": 2}, {"answer_tokens": 700, "dropped": 30, "kept": 0}]),
            dict(turn(3), fit=[{"answer_tokens": 700, "dropped": 2, "kept": 40}])]
    m = T.measure(drop)["memory_in_view"]
    check("TQ1g six MESSAGES dropped is three exchanges; the turn's FIRST fit record is the one that counts",
          m["turns_where_earlier_exchanges_were_dropped_pct"] == 66.7 and m["most_exchanges_dropped_in_one_turn"] == 3, m)
    check("TQ1g a turn with 40 messages kept is at the 20-exchange cap (one of three); median in view is counted in exchanges",
          m["turns_at_the_history_cap_pct"] == 33.3 and m["median_exchanges_in_view"] == 1, m)
    # A KNOWN SPLIT (the laptop session's read of ff2e5a8): 4 newer turns at the cap with a fit record, 6 older ones
    # with none. The median and every share are over the same 4 turns, so at the cap is 100%, not 40%.
    split = [dict(turn(i), fit=[]) for i in range(1, 7)] + [dict(turn(i), fit=[{"dropped": 0, "kept": 40}]) for i in range(7, 11)]
    ms = T.measure(split)["memory_in_view"]
    check("TQ1g a known split: 4 of 10 turns carry a fit record, all at the cap: median 20 in view, at the cap 100%, dropped 0%",
          ms["turns_with_a_fit_record"] == 4 and ms["median_exchanges_in_view"] == 20
          and ms["turns_at_the_history_cap_pct"] == 100.0 and ms["turns_where_earlier_exchanges_were_dropped_pct"] == 0.0, ms)
    txt = T.render(T.measure(split))
    check("TQ1g ...and the report says over which turns: '4 of 10 turns carry a fit record'",
          "4 of 10 turns carry a fit record" in txt and "cap on 100.0%" in txt, [l for l in txt.splitlines() if "memory" in l])
    none_fit = [dict(turn(i), fit=[]) for i in range(1, 4)]
    check("TQ1g no fit record at all is 'not measured', never 'None%'",
          "memory in view   not measured" in T.render(T.measure(none_fit)) and "None%" not in T.render(T.measure(none_fit)))
    core = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "covenant_unified_v8.py"), encoding="utf-8").read()
    import re as _re
    cap = _re.search(r"^AGENT_HISTORY_TURNS\s*=\s*(\d+)", core, _re.M)
    check("TQ1g the cap this tool and the two pages speak of is the door's own (AGENT_HISTORY_TURNS, two messages each)",
          cap and int(cap.group(1)) * 2 == T.HISTORY_CAP_MESSAGES
          and all("last %s exchanges" % cap.group(1) in open(os.path.join(os.path.dirname(os.path.abspath(__file__)), f),
                                                              encoding="utf-8").read() for f in ("covenant_pc3d.py", "covenant_council.py")),
          cap and cap.group(1))
    hed = [turn(1), dict(turn(2), answer="I am not entirely sure, but I think it was Tuesday."), dict(turn(3), answer="I do not know."),
           dict(turn(4), answer="It was Tuesday.")]
    a2 = T.measure(hed)["answers"]
    check("TQ1g a hedge and an 'I do not know' are counted apart: one of four says he does not know, two of four hedge",
          a2["says_does_not_know_pct"] == 25.0 and a2["hedges_pct"] == 50.0, a2)

    mc = T.measure([turn(1)], model_rows=[{"ok": True}, {"ok": False, "error": "TimeoutError: timed out"},
                                          {"ok": False, "error": "TimeoutError: timed out"}, {"ok": False, "error": "ContextTooLong: x"},
                                          {"at": "no ok field: not a call"}])["model_calls"]
    check("TQ1h failed model calls are counted by kind (three of four calls; two timeouts)",
          mc["calls"] == 4 and mc["failed_pct"] == 75.0 and mc["failures_by_kind"].get("TimeoutError") == 2, mc)

    mixed = [{"kind": "council", "text": "x", "answer": "y"}, {"kind": "tx"}] + healthy
    check("TQ1i only conversation turns are counted; --last and --since select",
          T.measure(T.select(mixed, last=200))["turns"] == 10 and len(T.select(mixed, last=3)) == 3
          and len(T.select(mixed, last=0, since="2026-11-19T10:08")) == 3)
    # THE RUNNING CONVERSATION IS THE DEFAULT. The laptop's real log: the last 200 rows by kind alone were all
    # fresh batch asks. Here: 4 running turns, then 30 fresh one-word batch answers and 2 private asks.
    batch = healthy[:4] + [dict(turn(20 + i, ms=3000), answer="yes", fresh=True) for i in range(30)] \
        + [dict(turn(55 + i), private=True) for i in range(2)]
    check("TQ1i the default selection is the 4 running turns, however many batch asks came after them",
          len(T.select(batch, last=200)) == 4 and T.measure(T.select(batch, last=200))["wait_seconds"]["median"] == 20.0)
    check("TQ1i ...the same log by kind alone (--which all) reads as the batch work: a 3 s median over 36 turns",
          len(T.select(batch, last=200, which="all")) == 36
          and T.measure(T.select(batch, last=200, which="all"))["wait_seconds"]["median"] == 3.0)
    check("TQ1i fresh and private can each be asked for, and --last is applied AFTER the kind is chosen",
          len(T.select(batch, which="fresh")) == 30 and len(T.select(batch, which="private")) == 2
          and len(T.select(batch, last=3, which="running")) == 3)
    check("TQ1i divide() says how the door's rows divide", T.divide(batch) == {"running": 4, "fresh": 30, "private": 2})
    two = [dict(turn(i), **{"from": "198.51.100.1"}) for i in range(1, 8)] + [dict(turn(i, ms=90000), **{"from": "198.51.100.2"}) for i in range(8, 11)]
    rc = T.measure(two)["callers"]
    check("TQ1i callers are counted and named by rank, never by address",
          rc["distinct"] == 2 and [c["turns"] for c in rc["by_rank"]] == [7, 3] and rc["by_rank"][1]["median_wait_s"] == 90.0
          and "198.51" not in json.dumps(rc))
    check("TQ1i --caller 2 is the second busiest caller's turns; a rank that does not exist is nothing",
          len(T.select(two, caller=2)) == 3 and T.select(two, caller=9) == [])
    check("TQ1i an empty selection is said, not divided by", "no conversation turns" in T.render(T.measure([])))

    tmp = tempfile.mkdtemp(prefix="tq1-")
    log, asks = os.path.join(tmp, "ask_log.jsonl"), os.path.join(tmp, "model_asks.jsonl")
    with open(log, "w", encoding="utf-8") as fh:
        for r in held + rep_rows:
            fh.write(json.dumps(r) + "\n")
        fh.write("this line is not json\n[1, 2]\n")
    with open(asks, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"ok": False, "error": "TimeoutError: " + SECRET_Q}) + "\n")
    outs = []
    for extra in ([], ["--json"]):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = T.main(["--log", log, "--asks", asks] + extra)
        outs.append((code, buf.getvalue()))
    check("TQ1j both output forms exit 0 and count the two unreadable lines",
          all(c == 0 for c, _ in outs) and "2 unreadable" in outs[0][1] and json.loads(outs[1][1])["unreadable_lines"] == 2)
    check("TQ1j the first line says how the log divides and what is measured; the model-call line says WHOLE file",
          outs[0][1].startswith("the door carried 15 running, 0 fresh and 0 private") and "measured below: running" in outs[0][1]
          and "WHOLE file" in outs[0][1] and json.loads(outs[1][1])["selection"]["the_log_divides"]["running"] == 15, outs[0][1][:160])
    leaked = [w for _, text in outs for w in ("zebra", "quokka", "moon", "weather", ADDR, "sound and we should", "Held, not judged")
              if w in text]
    check("TQ1j NO WORDS: no question, answer, gate note or address appears in either output", not leaked, leaked)
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = T.main(["--log", os.path.join(tmp, "no-such-file.jsonl")])
    check("TQ1k a log that cannot be read is exit 2, never an empty healthy report", code == 2 and buf.getvalue() == "")
    check("TQ1k a missing model-call log still gives the report, without that line",
          "model_calls" not in T.measure(healthy, None))

    failed = [l for l, ok in results if not ok]
    print("\nTQ1: %d/%d passed" % (len(results) - len(failed), len(results)))
    if failed:
        print("FAILED: " + "; ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
