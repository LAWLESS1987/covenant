#!/usr/bin/env python3
"""test_pp2_tetsu_choice.py -- his own choice in his practice (A275): each night, after the operator's
curriculum, one slot is drawn from what Tetsu chose to learn; he changes his choices himself, through his
door (HANDS WRITE learning.txt); paper stays paper.

The operator's words, 2026-10-06: "ensure tetsu is free to learn whatever he wants also. tell him".

The runs are REAL, as in PP1: every attempt goes through covenant_tetsu_hands.act -- the screen, the
guarded runner, a subprocess -- in a scratch workshop. Only the model and the gate are stubbed. The
reference solutions below pin every expected value of the paper and health tracks; the code track has no
reference to pin, because its answers are computed from the live functions (PP2.3 shows they follow them).
Every check that guards something is also driven the other way, in this file.
LICENCE: public domain.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__)) or "."
sys.path.insert(0, HERE)
# Never the live record: every path here is a scratch one.
os.environ["COVENANT_TETSU_LEARNING_CHOICES"] = os.path.join(tempfile.mkdtemp(prefix="pp2_ch_"), "choices.jsonl")
import covenant_tetsu_hands as HANDS                                   # noqa: E402
import covenant_tetsu_practice as PR                                   # noqa: E402

ok = []


def check(name, cond, note=""):
    ok.append(bool(cond))
    print("%s  %s%s" % ("ok  " if cond else "FAIL", name, ("  -- " + str(note)[:240]) if note and not cond else ""))


print("PP2 -- his own choice in his practice (A275)")


def gate_clean(text):
    return "clean", "admitted"


def tmp(prefix):
    return tempfile.mkdtemp(prefix="pp2_%s_" % prefix)


def fresh():
    """(workshop, practice ledger, hands ledger, choices record)"""
    return (tmp("ws"), os.path.join(tmp("l"), "p.jsonl"), os.path.join(tmp("h"), "h.jsonl"),
            os.path.join(tmp("c"), "c.jsonl"))


def record(path, chosen, tracks=None, t="2026-10-06T10:44:54Z"):
    row = {"t": t, "by": "tetsu", "chosen": chosen}
    if tracks is not None:
        row["tracks"] = tracks
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n")


# ---------------------------------------------------------------- reference solutions
SMA = '''
def sma(prices, n):
    if n < 1:
        raise ValueError("n must be at least 1")
    out = []
    for i in range(len(prices)):
        out.append(None if i + 1 < n else sum(prices[i + 1 - n:i + 1]) / n)
    return out
'''
REF = {
    "paper_sma": SMA,
    "paper_positions": SMA + '''
def positions(prices, fast, slow):
    if not 1 <= fast < slow:
        raise ValueError("need 1 <= fast < slow")
    f, s = sma(prices, fast), sma(prices, slow)
    return [1 if a is not None and b is not None and a > b else 0 for a, b in zip(f, s)]
''',
    "paper_backtest": '''
def backtest(prices, positions, cost):
    if len(prices) != len(positions):
        raise ValueError("lengths differ")
    out, equity, prev = [], 1.0, 0
    for i in range(len(prices)):
        if i >= 1:
            equity *= 1 + positions[i - 1] * (prices[i] / prices[i - 1] - 1)
        if positions[i] != prev:
            equity *= 1 - cost
            prev = positions[i]
        out.append(equity)
    return out
''',
    "paper_drawdown": '''
def max_drawdown(equity):
    peak, worst = None, 0.0
    for e in equity:
        if peak is None or e > peak:
            peak = e
        elif peak > 0:
            worst = max(worst, (peak - e) / peak)
    return worst
''',
    "paper_walk_forward": '''
def walk_forward(n, k):
    if k < 1 or n < k + 1:
        raise ValueError("need k >= 1 and n >= k + 1")
    base, extra = divmod(n, k + 1)
    bounds = [0]
    for b in range(k + 1):
        bounds.append(bounds[-1] + base + (1 if b < extra else 0))
    return [(bounds[j], bounds[j + 1]) for j in range(1, k + 1)]
''',
    "health_disk": '''
import hashlib


def disk_check(manifest, files):
    missing = sorted(name for name in manifest if name not in files)
    mismatch = sorted(name for name in manifest if name in files
                      and hashlib.sha256(files[name].encode("utf-8")).hexdigest() != manifest[name])
    return {"missing": missing, "mismatch": mismatch}
''',
    "health_daily": '''
def daily_verdict(done_days, today, now_hm, due_hm, grace_min):
    if tuple(today) in [tuple(d) for d in done_days]:
        return "RAN"
    if now_hm[0] * 60 + now_hm[1] < due_hm[0] * 60 + due_hm[1] + grace_min:
        return "NOT YET DUE"
    return "MISSED"
''',
    "health_tell_once": '''
def tell_points(readings):
    out, told_red = [], False
    for i, r in enumerate(readings):
        if r == "red" and not told_red:
            out.append(i)
            told_red = True
        elif r == "green" and told_red:
            out.append(i)
            told_red = False
    return out
''',
    "health_chain": '''
import hashlib


def verify_chain(lines):
    prev = "0" * 64
    n = 0
    for i, (text, said_prev) in enumerate(lines, 1):
        if said_prev != prev:
            return {"ok": False, "broken_at": i}
        prev = hashlib.sha256(text.encode("utf-8")).hexdigest()
        n += 1
    return {"ok": True, "entries": n}
''',
}
FLATTEN = '''
def flatten(x):
    if not isinstance(x, list):
        return [x]
    out = []
    for item in x:
        out.extend(flatten(item))
    return out
'''
PERMS = '''
def permutations(items):
    if not items:
        return [[]]
    out = []
    for i in range(len(items)):
        for p in permutations(items[:i] + items[i + 1:]):
            out.append([items[i]] + p)
    return out
'''

# ---- PP2.1: the tracks are well formed, and every written task is solvable under the screen with the values right
ids = [t["id"] for ts in PR.TRACKS.values() for t in ts]
check("PP2.1a the tracks are paper, code and health; their task ids are unique and none is a curriculum task "
      "(so his slot never re-runs the operator's tasks, and the curriculum's count stays the curriculum's)",
      sorted(PR.TRACKS) == ["code", "health", "paper"] and len(ids) == len(set(ids)) and not set(ids) & set(PR.BY_ID), ids)
written = [t for name in ("paper", "health") for t in PR.TRACKS[name]]
check("PP2.1b every paper and health task has a reference solution here", set(REF) == {t["id"] for t in written},
      sorted({t["id"] for t in written} ^ set(REF)))
WS, _l, HL, _c = fresh()
for t in written:
    res, stop = PR.attempt(t, REF[t["id"]].strip() + "\n", gate=gate_clean, workshop=WS, hands_ledger=HL)
    check("PP2.1 %s: the reference passes all %d checks through his hands (screen, guarded run)" % (t["id"], len(t["checks"])),
          stop is None and res["passed"] == res["total"] == len(t["checks"]), res["said"])
check("PP2.1c the check file of every paper and health task carries no string the screen reads as a path",
      all(HANDS.screen(REF[t["id"]] + PR.check_source(t))[0] for t in written))

# ---- PP2.2: broken the other way -- the mistakes these tasks exist to teach are caught, and named
wrong = [("paper_backtest", REF["paper_backtest"].replace("positions[i - 1] * (prices[i]", "positions[i] * (prices[i]"),
          "backtest([100, 110, 99]", "trading on tomorrow's news (the position decided today earning today's move)"),
         ("paper_drawdown", REF["paper_drawdown"].replace("peak, worst = None, 0.0", "peak, worst = max(equity or [0]), 0.0"),
          "max_drawdown([1.0, 1.2, 0.9, 1.3, 1.04])", "a drawdown measured from the all-time peak, not the running one"),
         ("paper_walk_forward", REF["paper_walk_forward"].replace("(1 if b < extra else 0)", "(1 if b >= k + 1 - extra else 0)"),
          "walk_forward(11, 2)", "folds with the larger blocks last"),
         ("health_tell_once", REF["health_tell_once"].replace('if r == "red" and not told_red:', 'if r == "red":'),
          "tell_points(['green', 'red', 'red'", "a listener that tells every red reading, not once per streak"),
         ("health_chain", REF["health_chain"].replace("if said_prev != prev:", "if i > 1 and said_prev != prev:"),
          "verify_chain([('put m2'", "a chain that trusts its first line (a ledger that starts mid-way passes)")]
for tid, code, first, what in wrong:
    t = next(x for x in written if x["id"] == tid)
    res, stop = PR.attempt(t, code, gate=gate_clean, workshop=WS, hands_ledger=HL)
    check("PP2.2 broken the other way: %s is caught in %s, and the first failure is named" % (what, tid),
          code != REF[tid] and stop is None and res["passed"] < res["total"] and first in res["said"], res["said"])

# ---- PP2.3: the code track reads the LIVE functions
def built(t):
    """materialize(t), or None with the failure said as a FAIL -- a raise here would end the suite with no tally."""
    try:
        return PR.materialize(t)
    except Exception as e:                                              # noqa: BLE001
        check("PP2.3 %s could be built from the live %s()" % (t["id"], t["function"]), False, "%s: %s" % (type(e).__name__, e))
        return None


def read_ws(name, ws):
    try:
        return HANDS.read(name, ws)
    except (OSError, ValueError):
        return ""


for t in PR.TRACKS["code"]:
    m = built(t)
    if m is None:
        continue
    answers = "ANSWERS = %r\n" % [want for _e, want in m["checks"]]
    res, stop = PR.attempt(m, answers, gate=gate_clean, workshop=WS, hands_ledger=HL)
    check("PP2.3 %s: built from the live %s() -- its source and file:line are in the ask, every call is listed, and the "
          "answers it computed pass through his hands" % (t["id"], t["function"]),
          ("def %s(" % t["function"]) in m["ask"] and re.search(r"\.py:\d+", m["source"]) and len(m["checks"]) == len(t["calls"])
          and all(("%d. %s(" % (i + 1, t["function"])) in m["ask"] for i in range(len(t["calls"])))
          and stop is None and res["passed"] == res["total"] == len(t["calls"]), (m.get("source"), res["said"]))
    check("PP2.3b %s: its check file passes the screen" % t["id"], HANDS.screen(answers + PR.check_source(m))[0])
    bad = [want for _e, want in m["checks"]]
    bad[-1] = "not what it returns"
    res, stop = PR.attempt(m, "ANSWERS = %r\n" % bad, gate=gate_clean, workshop=WS, hands_ledger=HL)
    check("PP2.3c broken the other way: %s with its last answer wrong fails, naming ANSWERS[%d]" % (t["id"], len(bad) - 1),
          stop is None and res["passed"] == res["total"] - 1 and ("ANSWERS[%d]" % (len(bad) - 1)) in res["said"], res["said"])
parse_task = next(t for t in PR.TRACKS["code"] if t["id"] == "code_hands_parse")
before = [w for _e, w in (built(parse_task) or {"checks": []})["checks"]]
_real_first = HANDS._FIRST
try:
    HANDS._FIRST = re.compile(r"^\bNEVER\b$")
    patched = [w for _e, w in (built(parse_task) or {"checks": []})["checks"]]
finally:
    HANDS._FIRST = _real_first
check("PP2.3d the answers follow the code, not a copy of it: with the door's first-line pattern changed, every "
      "expected answer becomes None; restored, they are what they were",
      before and patched == [None] * len(before) and before != patched
      and [w for _e, w in (built(parse_task) or {"checks": []})["checks"]] == before, (before, patched))

# ---- PP2.4: an open exercise -- his topic, his asserts
OPEN = PR.open_task("how bees count")
check("PP2.4a an open task carries his words verbatim, and says a pass cannot tell whether his asserts were right",
      '"how bees count"' in OPEN["ask"] and "cannot tell whether they were the right ones" in OPEN["ask"])
n0 = len(HANDS._rows(HL))
res, _s = PR.attempt(OPEN, "def f(x):\n    return x + 1\n\n\ndef test():\n    assert f(1) == 2\n    assert f(2) == 3\n    assert f(3) == 4\n",
                     gate=gate_clean, workshop=WS, hands_ledger=HL)
check("PP2.4b asserts inside a function nobody calls check nothing: refused before anything is written or run, and told why",
      res["passed"] == 0 and "0 assert line(s)" in res["said"] and len(HANDS._rows(HL)) == n0, res["said"])
res, _s = PR.attempt(OPEN, "def f(x):\n    return x + 1\n\n\nassert f(1) == 2\nassert f(2) == 3\nassert f(3) == 5, 'three plus one'\n",
                     gate=gate_clean, workshop=WS, hands_ledger=HL)
check("PP2.4c broken the other way: his own assert that fails is what he is told", res["passed"] == 0
      and "AssertionError" in res["said"] and "three plus one" in res["said"], res["said"])
res, _s = PR.attempt(OPEN, "def f(x):\n    return x + 1\n\n\nassert f(1) == 2\nassert f(2) == 3\nif __name__ == '__main__':\n    assert f(3) == 4\n",
                     gate=gate_clean, workshop=WS, hands_ledger=HL)
check("PP2.4d three asserts of his own that run and hold pass (one under __main__ counts: the runner runs it as main)",
      res["passed"] == res["total"] == 1, res["said"])

# ---- PP2.5: his choices -- the lines he writes, and a track never guessed
c, tr, extra = PR.parse_choices("paper: trading on paper\n- Code: how the project works\n\n2) poetry and rhythm\nhealth: checks")
check("PP2.5a his lines parse plainly: 'track: words' names a track, his words alone are open, a bullet is not a word, "
      "and past three lines are counted, not kept",
      c == ["trading on paper", "how the project works", "poetry and rhythm"] and tr == ["paper", "code", "open"] and extra == 1,
      (c, tr, extra))
_w, L, _h, C = fresh()
record(C, ["trading strategies and how to build them on paper", "the project's code and how it works"])
pick = PR.choice_for_tonight(C, L)
check("PP2.5b a recorded choice that names no track is OPEN -- even 'trading ... on paper' is not guessed into the paper "
      "track (his first answer, 2026-10-06, named none)", pick and pick["track"] == "open" and pick["index"] == 0, pick)
_w, L, _h, C = fresh()
record(C, ["a", "b", "c"], ["paper", "code", "nonsense"])
seen = []
for _i in range(4):
    p = PR.choice_for_tonight(C, L) or {"words": "", "track": None}
    seen.append((p.get("index"), p["track"]))
    PR._append({"kind": "choice", "words": p["words"], "track": p["track"]}, L)
record(C, ["x", "y"], ["health", "paper"], t="2099-01-01T00:00:00Z")
p = PR.choice_for_tonight(C, L) or {}
check("PP2.5c his choices are taken in turn, in his order (an unknown track is open), and a new choice starts the turn "
      "again at his first", seen == [(0, "paper"), (1, "code"), (2, "open"), (0, "paper")] and (p.get("index"), p.get("track")) == (0, "health"),
      (seen, p))
_w, L, _h, C = fresh()
record(C, [])
check("PP2.5d an empty choice is a choice: no slot", PR.choice_for_tonight(C, L) is None)

# ---- PP2.6: he changes them himself, through his door
W, L, H, C = fresh()
record(C, ["trading strategies and how to build them on paper"])
check("PP2.6a with no learning.txt in his workshop nothing is recorded", PR.sync_choices(W, C, say=lambda *_a: None) is None
      and len(PR._rows(C)) == 1)
handled, data, rec = HANDS.act("HANDS WRITE learning.txt\npaper: how a backtest is built\nhow bees count", gate=gate_clean,
                               workshop=W, ledger=H)
row = PR.sync_choices(W, C, say=lambda *_a: None)
p = PR.choice_for_tonight(C, L)
check("PP2.6b HANDS WRITE learning.txt -- his door's own act, through the gate -- becomes his recorded choice: by him, "
      "through his hands, his file verbatim, and the slot draws from it",
      handled and not rec.get("refused") and row and row["by"] == "tetsu" and "his hands" in row["through"]
      and row["chosen"] == ["how a backtest is built", "how bees count"] and row["tracks"] == ["paper", "open"]
      and row["answer"] == "paper: how a backtest is built\nhow bees count" and (p["words"], p["track"]) == ("how a backtest is built", "paper"),
      (rec, row, p))
check("PP2.6c read again unchanged, it is not recorded twice", PR.sync_choices(W, C, say=lambda *_a: None) is None and len(PR._rows(C)) == 2)
record(C, ["what he said later, another way"], ["code"], t="2099-01-01T00:00:00Z")
PR.sync_choices(W, C, say=lambda *_a: None)
check("PP2.6d a later choice recorded another way is not overwritten by an unchanged file",
      PR.latest_choice(C)["chosen"] == ["what he said later, another way"], PR.latest_choice(C))
HANDS.act("HANDS WRITE learning.txt\nhealth: the machine's checks", gate=gate_clean, workshop=W, ledger=H)
PR.sync_choices(W, C, say=lambda *_a: None)
check("PP2.6e ...and when he changes the file again, the change is his latest choice",
      PR.latest_choice(C)["chosen"] == ["the machine's checks"] and PR.latest_choice(C)["tracks"] == ["health"], PR.latest_choice(C))
W2, _L2, H2, C2 = fresh()
handled, data, rec = HANDS.act("HANDS WRITE learning.txt\npaper: x", gate=lambda t: ("violates", "no"), workshop=W2, ledger=H2)
check("PP2.6f broken the other way: a VIOLATES on his write refuses it, and nothing is recorded",
      rec.get("refused") and PR.sync_choices(W2, C2, say=lambda *_a: None) is None and not PR._rows(C2), (rec, PR._rows(C2)))


# ---------------------------------------------------------------- whole nights, with a model that answers by task
def by_task(answers, seen=None, wrong=(), clock=None, step=0.0):
    """A stub model: the reference file for the TASK in the prompt, or a wrong file for ids in `wrong`."""
    def ask(messages, max_tokens=700, temperature=0.3):
        if seen is not None:
            seen.append(messages)
        if clock is not None:
            clock["t"] += step
        m = re.search(r"TASK (\w+):", messages[-1]["content"])
        tid = m.group(1) if m else ""
        if tid in wrong or tid not in answers:
            return "```python\nx = 1\n```", {"model": "stub", "tokens": 1}
        return "```python\n" + answers[tid].strip() + "\n```", {"model": "stub", "tokens": 1}
    return ask


ALL = dict(REF, flatten=FLATTEN, permutations=PERMS)
W, L, H, C = fresh()
record(C, ["trading on paper"], ["paper"])
told = []
s = PR.night(ask=by_task(ALL), gate=gate_clean, workshop=W, ledger=L, hands_ledger=H, tasks=2, choices=C,
             tell=lambda t, w: told.append(t), say=lambda *_a: None)
rows = PR._rows(L)
check("PP2.7a the curriculum runs as before -- its first two tasks, both solved -- and THEN his slot: paper_sma, solved",
      [r["task"] for r in rows if r.get("kind") == "attempt"] == ["flatten", "permutations", "paper_sma"]
      and s["tried"] == 2 and s["within"] == 2 and (s["choice"] or {}).get("task") == "paper_sma" and (s["choice"] or {}).get("solved_round") == 1,
      ([r.get("task") for r in rows], s))
check("PP2.7b the night's count is the curriculum's: 2 of %d, not 3 -- his track is his, not the operator's tally" % len(PR.CURRICULUM),
      s["solved_total"] == 2 and "He has solved 2 of %d" % len(PR.CURRICULUM) in s["text"], s["text"])
check("PP2.7c the one line to the operator names his choice and how it went; the record holds the slot and the night",
      len(told) == 1 and 'His own choice ("trading on paper", paper): paper_sma, solved in round 1' in told[0]
      and [r["kind"] for r in rows][-2:] == ["choice", "night"] and rows[-1]["choice"]["track"] == "paper", told)
check("PP2.7d his solved paper file is kept in his workshop, beside the curriculum's",
      "def sma(" in read_ws("practice/solved/paper_sma.py", W) and "def flatten(" in read_ws("practice/solved/flatten.py", W))
check("PP2.7e the curriculum's plan never offers a track task, even with one solved",
      all(t["id"] in PR.BY_ID for t, _r in PR.plan(20, L)), [t["id"] for t, _r in PR.plan(20, L)])

W, L, H, C = fresh()
record(C, ["trading on paper"], ["paper"])
s = PR.night(ask=by_task(ALL), gate=gate_clean, workshop=W, ledger=L, hands_ledger=H, tasks=2, budget_s=0, choices=C,
             tell=lambda t, w: None, say=lambda *_a: None)
check("PP2.8a his slot has its own clock: a curriculum that used all of its minutes does not starve it",
      s["tried"] == 0 and "clock" in (s["stop"] or "") and s["choice"] and (s["choice"] or {}).get("solved_round") == 1, s)
W, L, H, C = fresh()
record(C, ["trading on paper"], ["paper"])
clock = {"t": 1000.0}
s = PR.night(ask=by_task(ALL, wrong={"paper_sma"}, clock=clock, step=PR.CHOICE_BUDGET_S + 1), gate=gate_clean, workshop=W,
             ledger=L, hands_ledger=H, tasks=0, choices=C, tell=lambda t, w: None, say=lambda *_a: None, now=lambda: clock["t"])
check("PP2.8b ...and its clock bounds it: past CHOICE_BUDGET_S no round of his starts, and the stop says so",
      (s["choice"] or {}).get("rounds") == 1 and "clock" in ((s["choice"] or {}).get("stop") or ""), s["choice"])
W, L, H, C = fresh()
record(C, ["trading on paper"], ["paper"])
s = PR.night(ask=by_task(ALL, wrong={"paper_sma"}), gate=gate_clean, workshop=W, ledger=L, hands_ledger=H, tasks=0, choices=C,
             tell=lambda t, w: None, say=lambda *_a: None)
tries = [r for r in PR._rows(L) if r.get("kind") == "attempt" and r["task"] == "paper_sma"]
check("PP2.8c its rounds are bounded: a model never right gets exactly CHOICE_ROUNDS (%d) tries, and the line says not solved"
      % PR.CHOICE_ROUNDS, len(tries) == PR.CHOICE_ROUNDS and (s["choice"] or {}).get("solved_round") is None
      and "not solved in %d round(s)" % PR.CHOICE_ROUNDS in s["text"], (len(tries), s["text"]))
for label, kw in (("a VIOLATES at the gate", {"gate": lambda t: ("violates", "no")}),
                  ("an unreachable gate", {"gate": lambda t: ("unreachable", "down")}),
                  ("a model that cannot answer", {"ask": lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no weights fit"))})):
    W, L, H, C = fresh()
    record(C, ["trading on paper"], ["paper"])
    args = dict(ask=by_task(ALL), gate=gate_clean, workshop=W, ledger=L, hands_ledger=H, tasks=1, choices=C,
                tell=lambda t, w: None, say=lambda *_a: None)
    args.update(kw)
    s = PR.night(**args)
    check("PP2.8d after %s stops the curriculum, his slot does not run (fails closed)" % label,
          s["stop"] and s["choice"] is None and not [r for r in PR._rows(L) if r.get("kind") == "choice"], s)
W, L, H, C = fresh()
record(C, ["trading on paper"], ["paper"])
s = PR.night(ask=by_task(ALL), gate=gate_clean, workshop=W, ledger=L, hands_ledger=H, tasks=1, choices=C, his_choice=False,
             tell=lambda t, w: None, say=lambda *_a: None)
check("PP2.8e his_choice=False runs the curriculum alone", s["choice"] is None and s["tried"] == 1, s)
W, L, H, C = fresh()
record(C, ["a", "b", "c"], ["code", "health", "open"])
for want in ("code_hands_parse", "health_disk", "open"):
    r = PR.choice_slot(by_task({}), gate=gate_clean, workshop=W, ledger=L, hands_ledger=H, choices=C, say=lambda *_a: None)
    check("PP2.8f a slot on %s's track runs through his hands and is recorded (a wrong file: not solved, no stop)" % want,
          r and r["task"] == want and r["rounds"] == PR.CHOICE_ROUNDS and not r["stop"], r)

# ---- PP2.9: paper stays paper. A night with every track, in a fresh process, loads no module of this tree but the
# practice and his hands -- so nothing in it can reach the venues, the trader, a key, or a money rule.
ALLOWED = {"covenant_tetsu_practice", "covenant_tetsu_hands"}
PROBE = r'''
import json, os, sys, tempfile
here, first = sys.argv[1], sys.argv[2]
sys.path[:0] = [first, here]
import covenant_tetsu_practice as PR
d = tempfile.mkdtemp(prefix="pp2_probe_")
ch, empty = os.path.join(d, "c.jsonl"), os.path.join(d, "empty.jsonl")
open(empty, "w").close()
with open(ch, "w") as fh:
    fh.write(json.dumps({"t": "2026-10-06T00:00:00Z", "chosen": ["a", "b", "c"], "tracks": ["paper", "code", "health"]}) + "\n")
ask = lambda m, max_tokens=0, temperature=0: ("```python\nx = 1\n```", {"model": "stub", "tokens": 1})
kw = dict(gate=lambda t: ("clean", "ok"), workshop=os.path.join(d, "ws"), ledger=os.path.join(d, "l.jsonl"),
          hands_ledger=os.path.join(d, "h.jsonl"), choices=ch, say=lambda *a: None)
s = PR.night(ask=ask, tasks=1, tell=lambda t, w: None, sends_path=empty, audit_path=empty, **kw)
PR.choice_slot(ask, **kw)
PR.choice_slot(ask, **kw)
tracks = [r.get("track") for r in PR._rows(kw["ledger"]) if r.get("kind") == "choice"]
roots = {os.path.normcase(os.path.abspath(p)) for p in (here, first)}
mods = sorted(n for n, m in list(sys.modules.items())
              if getattr(m, "__file__", None) and os.path.normcase(os.path.dirname(os.path.abspath(m.__file__))) in roots)
print("PROBE " + json.dumps({"mods": mods, "tracks": tracks}))
'''


def probe(first):
    cp = subprocess.run([sys.executable, "-c", PROBE, HERE, first], capture_output=True, text=True, timeout=180, cwd=tmp("cwd"))
    line = next((x for x in cp.stdout.splitlines() if x.startswith("PROBE ")), None)
    return (json.loads(line[6:]) if line else None), cp


got, cp = probe(HERE)
check("PP2.9a a night with a paper, a code and a health slot loads no module of this tree but %s (so no venue, trader, "
      "balance reader or money rule is even imported)" % ", ".join(sorted(ALLOWED)),
      got is not None and got["tracks"] == ["paper", "code", "health"] and set(got["mods"]) <= ALLOWED,
      (got, cp.stderr[-400:]))
mut = tmp("mut")
src = open(os.path.join(HERE, "covenant_tetsu_practice.py"), encoding="utf-8").read()
anchor = "import covenant_tetsu_hands as HANDS"
with open(os.path.join(mut, "covenant_tetsu_practice.py"), "w", encoding="utf-8", newline="") as fh:
    fh.write(src.replace(anchor, anchor + "\nimport covenant_tetsu_money  # PP2.9b mutation", 1))
got2, cp2 = probe(mut)
check("PP2.9b broken the other way: the same night from a copy of the practice that imports covenant_tetsu_money (the "
      "module that reads the balances) is caught", anchor in src and got2 is not None and "covenant_tetsu_money" in got2["mods"],
      (got2, cp2.stderr[-400:]))
shutil.rmtree(mut, ignore_errors=True)
paper = PR.TRACKS["paper"][0]
for code, why in (("import urllib.request\n\ndef sma(prices, n):\n    return []\n", "import of urllib.request is refused"),
                  ("import socket\n\ndef sma(prices, n):\n    return []\n", "import of socket is refused"),
                  ("def sma(prices, n):\n    return open('../../private/key.json').read()\n", "a path that leaves the workshop is refused")):
    res, _s = PR.attempt(paper, code, gate=gate_clean, workshop=WS, hands_ledger=HL)
    check("PP2.9c a paper file that reaches for the network or a file outside his workshop is refused by the screen (%s)"
          % why, res["passed"] == 0 and why in res["said"], res["said"])

# ---- PP2.11: a test suite never runs his slot on live state (A275; the A190/A272 shape). The module's idea of "real"
# is pointed at temp dirs first, so a broken guard writes nowhere live.
fake_ws, fake_c = tmp("realws"), os.path.join(tmp("realc"), "c.jsonl")
record(fake_c, ["trading on paper"], ["paper"])
_rw, _rc = PR.REAL_WORKSHOP, PR.REAL_CHOICES
try:
    PR.REAL_WORKSHOP, PR.REAL_CHOICES = fake_ws, fake_c
    _w, L1, H1, C1 = fresh()
    record(C1, ["trading on paper"], ["paper"])
    r1 = PR.choice_slot(by_task(ALL), gate=gate_clean, workshop=fake_ws, ledger=L1, hands_ledger=H1, choices=C1, say=lambda *_a: None)
    W2, L2, H2, _c = fresh()
    r2 = PR.choice_slot(by_task(ALL), gate=gate_clean, workshop=W2, ledger=L2, hands_ledger=H2, choices=fake_c, say=lambda *_a: None)
    W3, L3, H3, _c = fresh()
    r3 = PR.choice_slot(by_task(ALL), gate=gate_clean, workshop=W3, ledger=L3, hands_ledger=H3, choices=C1, say=lambda *_a: None)
finally:
    PR.REAL_WORKSHOP, PR.REAL_CHOICES = _rw, _rc
check("PP2.11a a test suite cannot run his slot in his real workshop: refused before any act, nothing written",
      r1 is None and not os.listdir(fake_ws) and not HANDS._rows(H1) and not PR._rows(L1), (r1, os.listdir(fake_ws)))
check("PP2.11b ...nor on his real choices' record", r2 is None and not HANDS._rows(H2) and not PR._rows(L2), r2)
check("PP2.11c ...and the same call with scratch paths runs (the guard refuses live state, not the slot)",
      r3 and r3.get("task") == "paper_sma" and r3.get("solved_round") == 1, r3)

# ---- PP2.10: he is told -- in the paragraph of what he can do, on every door
import covenant_persona as P                                          # noqa: E402
wy = P.where_you_are()
check("PP2.10 his system message tells him what he learns is his to choose, and how: HANDS WRITE learning.txt, the "
      "three tracks or his own words, and that it goes on the record, a public file",
      "free to learn whatever he wants" in wy and "HANDS WRITE learning.txt" in wy
      and all(("'%s: ...'" % n) in wy for n in PR.TRACKS) and "a public file" in wy, wy[wy.find("What you learn"):][:400])

print("\nnot measured here: how a real model does on his tracks (the nightly's record says it), whether the asserts "
      "he writes for an open exercise are the right ones (nothing can say), and anything the practice process writes "
      "outside the paths it is handed -- PP2.9 reads what it imports, not what it touches.")
print("\nPP2: %d/%d passed" % (sum(ok), len(ok)))
sys.exit(0 if all(ok) else 1)
