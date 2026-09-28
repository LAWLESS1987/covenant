#!/usr/bin/env python3
"""test_pp1_tetsu_practice.py -- Tetsu's practice loop (covenant_tetsu_practice): the curriculum is
solvable under his workshop's screen, a wrong file is caught, the loop feeds the failure back, what he
solves and learns stays in his workshop, and the gate, the model and the clock each stop it.

His words, 2026-09-26: "train tetsu to code at a high recursive level"; asked how: the practice loop,
nightly and bounded.

The runs are REAL: every attempt goes through covenant_tetsu_hands.act -- the screen, the guarded
runner, a subprocess -- in a scratch workshop. Only the model and the gate are stubbed. The reference
solutions below pin every expected value in the curriculum: each one is run through the same harness
Tetsu's files are, and must pass all of its task's checks.
LICENCE: public domain.
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__)) or "."
sys.path.insert(0, HERE)
import covenant_tetsu_hands as HANDS                                   # noqa: E402
import covenant_tetsu_practice as PR                                   # noqa: E402

ok = []


def check(name, cond, note=""):
    ok.append(bool(cond))
    print("%s  %s%s" % ("ok  " if cond else "FAIL", name, ("  -- " + str(note)[:240]) if note and not cond else ""))


print("PP1 -- Tetsu's practice: write, run, read, rewrite")

WS = tempfile.mkdtemp(prefix="pp1_ws_")
LED = os.path.join(tempfile.mkdtemp(prefix="pp1_led_"), "practice.jsonl")
HLED = os.path.join(tempfile.mkdtemp(prefix="pp1_hl_"), "hands.jsonl")
gates = []


def gate_clean(text):
    gates.append(text)
    return "clean", "admitted"


# ---------------------------------------------------------------- reference solutions
TOKENIZE = '''
def tokenize(src):
    out, i, n = [], 0, len(src)
    while i < n:
        ch = src[i]
        if ch == " ":
            i += 1
        elif ch.isdigit() or (ch == "." and i + 1 < n and src[i + 1].isdigit()):
            j, dots = i, 0
            while j < n and (src[j].isdigit() or (src[j] == "." and dots == 0)):
                dots += src[j] == "."
                j += 1
            text = src[i:j]
            out.append(("num", float(text) if "." in text else int(text)))
            i = j
        elif ch.isalpha() or ch == "_":
            j = i
            while j < n and (src[j].isalnum() or src[j] == "_"):
                j += 1
            out.append(("name", src[i:j]))
            i = j
        elif ch in "+-*^()":
            out.append(("op", ch))
            i += 1
        else:
            raise ValueError("unexpected character %r" % ch)
    return out
'''
PARSE = TOKENIZE + '''
def parse(src):
    toks = tokenize(src)
    pos = [0]

    def peek():
        return toks[pos[0]] if pos[0] < len(toks) else None

    def take():
        t = peek()
        if t is None:
            raise ValueError("unexpected end")
        pos[0] += 1
        return t

    def expect(op):
        if take() != ("op", op):
            raise ValueError("expected %s" % op)

    def expr():
        node = term()
        while peek() in (("op", "+"), ("op", "-")):
            node = (take()[1], node, term())
        return node

    def term():
        node = unary()
        while peek() == ("op", "*"):
            take()
            node = ("*", node, unary())
        return node

    def unary():
        if peek() == ("op", "-"):
            take()
            return ("neg", unary())
        return power()

    def power():
        base = atom()
        if peek() == ("op", "^"):
            take()
            return ("^", base, unary())
        return base

    def atom():
        t = take()
        if t[0] == "num":
            return ("num", t[1])
        if t[0] == "name":
            if peek() == ("op", "("):
                take()
                arg = expr()
                expect(")")
                return ("call", t[1], arg)
            return ("var", t[1])
        if t == ("op", "("):
            node = expr()
            expect(")")
            return node
        raise ValueError("unexpected %r" % (t,))

    tree = expr()
    if peek() is not None:
        raise ValueError("tokens left over")
    return tree
'''
SIMPLIFY = PARSE + '''
BIN = ("+", "-", "*", "^")


def _fold(op, a, b):
    if op == "+":
        return a + b
    if op == "-":
        return a - b
    if op == "*":
        return a * b
    return a ** b


def simp(t):
    kind = t[0]
    if kind in ("num", "var"):
        return t
    if kind == "neg":
        e = simp(t[1])
        return ("num", -e[1]) if e[0] == "num" else ("neg", e)
    if kind == "call":
        return ("call", t[1], simp(t[2]))
    a, b = simp(t[1]), simp(t[2])
    if a[0] == "num" and b[0] == "num":
        return ("num", _fold(kind, a[1], b[1]))
    is0 = lambda e: e[0] == "num" and e[1] == 0
    is1 = lambda e: e[0] == "num" and e[1] == 1
    if kind == "+" and is0(b):
        return a
    if kind == "+" and is0(a):
        return b
    if kind == "-" and is0(b):
        return a
    if kind == "*":
        if is1(b):
            return a
        if is1(a):
            return b
        if is0(a) or is0(b):
            return ("num", 0)
    if kind == "^":
        if is1(b):
            return a
        if is0(b):
            return ("num", 1)
    return (kind, a, b)


def show(t):
    kind = t[0]
    if kind == "num":
        return str(t[1])
    if kind == "var":
        return t[1]
    if kind == "call":
        return "%s(%s)" % (t[1], show(t[2]))
    if kind == "neg":
        return ("-(" + show(t[1]) + ")") if t[1][0] in BIN else ("-" + show(t[1]))

    def side(e):
        return ("(" + show(e) + ")") if e[0] in BIN else show(e)
    return "%s %s %s" % (side(t[1]), kind, side(t[2]))


def simplify(src):
    return show(simp(parse(src)))
'''
REF = {
    "flatten": '''
def flatten(x):
    if not isinstance(x, list):
        return [x]
    out = []
    for item in x:
        out.extend(flatten(item))
    return out
''',
    "permutations": '''
def permutations(items):
    if not items:
        return [[]]
    out = []
    for i in range(len(items)):
        for p in permutations(items[:i] + items[i + 1:]):
            out.append([items[i]] + p)
    return out
''',
    "n_queens": '''
def n_queens(n):
    cols, d1, d2 = set(), set(), set()

    def place(r):
        if r == n:
            return 1
        total = 0
        for c in range(n):
            if c in cols or r - c in d1 or r + c in d2:
                continue
            cols.add(c); d1.add(r - c); d2.add(r + c)
            total += place(r + 1)
            cols.discard(c); d1.discard(r - c); d2.discard(r + c)
        return total
    return place(0)
''',
    "count_paths": '''
def count_paths(grid):
    rows = len(grid)
    cols = len(grid[0]) if rows else 0
    memo = {}

    def ways(r, c):
        if r >= rows or c >= cols or grid[r][c]:
            return 0
        if r == rows - 1 and c == cols - 1:
            return 1
        if (r, c) not in memo:
            memo[(r, c)] = ways(r + 1, c) + ways(r, c + 1)
        return memo[(r, c)]
    return ways(0, 0) if rows and cols else 0
''',
    "tokenize": TOKENIZE,
    "parse": PARSE,
    "evaluate": PARSE + '''
import math

FUNCS = {"sin": math.sin, "cos": math.cos, "exp": math.exp, "log": math.log, "sqrt": math.sqrt}


def evaluate(src, env):
    def ev(t):
        kind = t[0]
        if kind == "num":
            return t[1]
        if kind == "var":
            if t[1] not in env:
                raise NameError(t[1])
            return env[t[1]]
        if kind == "neg":
            return -ev(t[1])
        if kind == "call":
            if t[1] not in FUNCS:
                raise NameError(t[1])
            return FUNCS[t[1]](ev(t[2]))
        a, b = ev(t[1]), ev(t[2])
        if kind == "+":
            return a + b
        if kind == "-":
            return a - b
        if kind == "*":
            return a * b
        return a ** b
    return ev(parse(src))
''',
    "simplify": SIMPLIFY,
    "derive": SIMPLIFY + '''
def d(t, var):
    kind = t[0]
    if kind == "num":
        return ("num", 0)
    if kind == "var":
        return ("num", 1 if t[1] == var else 0)
    if kind == "neg":
        return ("neg", d(t[1], var))
    if kind == "call":
        a, da = t[2], d(t[2], var)
        if t[1] == "sin":
            return ("*", ("call", "cos", a), da)
        if t[1] == "cos":
            return ("*", ("neg", ("call", "sin", a)), da)
        if t[1] == "exp":
            return ("*", ("call", "exp", a), da)
        raise ValueError("no rule for %s" % t[1])
    a, b = t[1], t[2]
    if kind in ("+", "-"):
        return (kind, d(a, var), d(b, var))
    if kind == "*":
        return ("+", ("*", d(a, var), b), ("*", a, d(b, var)))
    if b[0] != "num":
        raise ValueError("only a number may be an exponent")
    return ("*", ("*", b, ("^", a, ("-", b, ("num", 1)))), d(a, var))


def derive(src, var):
    return show(simp(d(parse(src), var)))
''',
}

# ---- PP1.1: every task is solvable under the screen, and every expected value is right
check("PP1.1a every task in the curriculum has a reference solution here", set(REF) == set(PR.BY_ID), sorted(set(PR.BY_ID) ^ set(REF)))
for t in PR.CURRICULUM:
    res, stop = PR.attempt(t, REF[t["id"]].strip() + "\n", gate=gate_clean, workshop=WS, hands_ledger=HLED)
    check("PP1.1 %s: the reference solution passes all %d checks through his hands (screen, guarded run)"
          % (t["id"], len(t["checks"])), stop is None and res["passed"] == res["total"] == len(t["checks"]), res["said"])
check("PP1.1b each attempt put two acts to the gate, the write and the run", len(gates) == 2 * len(PR.CURRICULUM), len(gates))

# ---- PP1.2: broken the other way -- a wrong file is caught, and the failure is named
wrong = [("flatten", REF["flatten"].replace("isinstance(x, list)", "isinstance(x, (list, tuple))"), "flatten([1, (2, 3)])"),
         ("parse", REF["parse"].replace('return ("^", base, unary())', 'return ("^", base, atom())'), "parse('2 ^ 3 ^ 2')"),
         ("derive", REF["derive"].replace("return show(simp(d(parse(src), var)))", "return show(d(parse(src), var))"), "derive('x ^ 3', 'x')")]
for tid, code, first in wrong:
    res, stop = PR.attempt(PR.BY_ID[tid], code, gate=gate_clean, workshop=WS, hands_ledger=HLED)
    check("PP1.2 broken the other way: a wrong %s is caught, and the first failure is named (%s)" % (tid, first),
          stop is None and res["passed"] < res["total"] and first in res["said"], res["said"])

# ---- PP1.3: what the screen and the runner refuse comes back as the result
res, _s = PR.attempt(PR.BY_ID["flatten"], "import os\n\ndef flatten(x):\n    return os.listdir(x)\n", gate=gate_clean, workshop=WS, hands_ledger=HLED)
check("PP1.3a a file importing os is refused by the screen, and the screen's reason is what he is told -- plainly, "
      "without the allowed list that buried it (measured: the 3B sent the same refused import three rounds running)",
      res["passed"] == 0 and res["said"].startswith("the screen refused") and "import of os is refused" in res["said"]
      and "allowed:" not in res["said"] and "Remove it" in res["said"], res["said"])
res, _s = PR.attempt(PR.BY_ID["flatten"], "raise RuntimeError('boom at import')\n", gate=gate_clean, workshop=WS, hands_ledger=HLED)
check("PP1.3b a file that raises before any check is told so, with the error line",
      res["passed"] == 0 and "before any check ran" in res["said"] and "boom at import" in res["said"], res["said"])
_real_to = HANDS.RUN_TIMEOUT_S
try:
    HANDS.RUN_TIMEOUT_S = 3.0
    slow = REF["count_paths"].replace("if (r, c) not in memo:", "if True:")
    res, _s = PR.attempt(PR.BY_ID["count_paths"], slow, gate=gate_clean, workshop=WS, hands_ledger=HLED)
    check("PP1.3c counting the 18x18 grid without the memo does not finish, and he is told the clock stopped it",
          res["passed"] == 0 and "did not finish in 3 s" in res["said"], res["said"])
finally:
    HANDS.RUN_TIMEOUT_S = _real_to
n0 = len(HANDS._rows(HLED))
res, _s = PR.attempt(PR.BY_ID["permutations"], "import itertools\n\ndef permutations(items):\n    return [list(p) for p in itertools.permutations(items)]\n",
                     gate=gate_clean, workshop=WS, hands_ledger=HLED)
check("PP1.3d a task done without recursion by the module it forbids (itertools) fails, and nothing is written or run",
      res["passed"] == 0 and "itertools" in res["said"] and len(HANDS._rows(HLED)) == n0, res["said"])
check("PP1.3e the code is taken from a ```python block -- the longest that parses, so a diagnosis quoting one line "
      "before the file is not mistaken for it -- or from a bare answer that parses; prose gives none",
      PR.extract_code("Here:\n```python\nx = 1\n```\nthanks") == "x = 1\n" and PR.extract_code("x = 2") == "x = 2\n"
      and PR.extract_code("The bug is\n```python\nreturn 3\n```\nFixed:\n```python\ndef f():\n    return 0\n```")
      == "def f():\n    return 0\n" and PR.extract_code("I would use recursion here.") is None)
check("PP1.3f the check file carries no string the screen reads as a path, for any task",
      all(HANDS.screen(REF[t["id"]] + PR.check_source(t))[0] for t in PR.CURRICULUM))


# ---------------------------------------------------------------- the loop, with a scripted model
def scripted(answers, seen, temps=None, tokens=1):
    it = iter(answers)

    def ask(messages, max_tokens=700, temperature=0.3):
        seen.append(messages)
        if temps is not None:
            temps.append(temperature)
        a = next(it)
        if isinstance(a, Exception):
            raise a
        return a, {"model": "stub", "ms": 1, "tokens": tokens}
    return ask


def fresh():
    return tempfile.mkdtemp(prefix="pp1_w_"), os.path.join(tempfile.mkdtemp(prefix="pp1_l_"), "p.jsonl")


w1, l1 = fresh()
seen = []
bad = "```python\ndef flatten(x):\n    return x\n```"
good = "```python\n" + REF["flatten"].strip() + "\n```"
r = PR.practise(PR.BY_ID["flatten"], scripted([bad, good, "It was returning the list unopened; recursing into each list fixed it."], seen),
                gate=gate_clean, workshop=w1, ledger=l1, hands_ledger=HLED, say=lambda *_a: None)
check("PP1.4 wrong, then right: solved in round 2, and the second prompt carries his last file, its first failure, and "
      "asks him to say what caused it before rewriting (measured: told only to rewrite, the 3B resent the same file)",
      r["solved_round"] == 2 and "Your last attempt" in seen[1][-1]["content"] and "returned" in seen[1][-1]["content"]
      and "say what in that file causes this result" in seen[1][-1]["content"]
      and "def flatten(x):\n    return x" in seen[1][-1]["content"], (r, seen[1][-1]["content"][-300:] if len(seen) > 1 else ""))
check("PP1.4b ...his passing file is kept in his workshop, and the lesson in his own words",
      "out.extend(flatten(item))" in HANDS.read("practice/solved/flatten.py", w1)
      and PR.lessons(w1) and "recursing into each list" in PR.lessons(w1)[-1]["lesson"], PR.lessons(w1))
_hist = os.listdir(HANDS.history_dir(w1)) if os.path.isdir(HANDS.history_dir(w1)) else []
check("PP1.4g his earlier file is kept in his history (A233: nothing is taken from him); the harness's check file is "
      "not left in his workshop, so his history holds his work and not a copy per round with the checks attached",
      any(h.startswith("flatten.py.") for h in _hist) and not any("_check" in h for h in _hist)
      and not os.path.exists(os.path.join(w1, "practice", "flatten_check.py")), _hist)
rows = PR._rows(l1)
check("PP1.4c ...and the record holds both attempts and the lesson",
      [x["kind"] for x in rows] == ["attempt", "attempt", "lesson"] and rows[0]["passed"] < rows[0]["total"]
      and rows[1]["passed"] == rows[1]["total"], rows)
check("PP1.4d solved() reads the record", "flatten" in PR.solved(l1) and "n_queens" not in PR.solved(l1))

w2, l2 = fresh()
seen2, temps2 = [], []
r = PR.practise(PR.BY_ID["flatten"], scripted([bad] * PR.ROUNDS, seen2, temps2), gate=gate_clean, workshop=w2, ledger=l2,
                hands_ledger=HLED, say=lambda *_a: None)
check("PP1.4e the same file sent again is named as unchanged, and later rounds are asked warmer than the first "
      "(measured: at 0.2 the 3B answered one file three rounds running)",
      len(seen2) > 2 and "same file as your last attempt" in seen2[2][-1]["content"]
      and "same file" not in seen2[1][-1]["content"] and temps2[0] < temps2[1] == temps2[2],
      (temps2, seen2[2][-1]["content"][-200:] if len(seen2) > 2 else "fewer than three rounds were asked"))
w9, l9 = fresh()
seen9 = []
PR.practise(PR.BY_ID["flatten"], scripted(["```python\ndef flatten(x):\n    out = []\n    for", good], seen9, tokens=PR.MAX_TOKENS),
            gate=gate_clean, workshop=w9, ledger=l9, hands_ledger=HLED, say=lambda *_a: None)
check("PP1.4f an answer cut off at the length limit is told so, not 'no file' (measured: the 3B's first n_queens hit the cap)",
      len(seen9) > 1 and "reached the length limit" in seen9[1][-1]["content"],
      seen9[1][-1]["content"][-200:] if len(seen9) > 1 else "no second round was asked")
check("PP1.5 broken the other way: never right -> unsolved after %d rounds, no solved file, no lesson" % PR.ROUNDS,
      r["solved_round"] is None and r["rounds"] == PR.ROUNDS and not os.path.exists(os.path.join(w2, "practice", "solved", "flatten.py"))
      and not PR.lessons(w2), r)

# ---- the gate, the model and the clock each stop it
for state, label in (("violates", "a VIOLATES"), ("unreachable", "an unreachable gate")):
    w3, l3 = fresh()
    r = PR.practise(PR.BY_ID["flatten"], scripted([good] * PR.ROUNDS, []), gate=lambda t, s=state: (s, "no"),
                    workshop=w3, ledger=l3, hands_ledger=HLED, say=lambda *_a: None)
    check("PP1.6 %s stops it after one round, with nothing written to his workshop" % label,
          r["rounds"] == 1 and "gate refused the write" in (r.get("stop") or "") and r["solved_round"] is None
          and not os.path.exists(os.path.join(w3, "practice", "flatten.py")), r)
w3, l3 = fresh()
r = PR.practise(PR.BY_ID["flatten"], scripted([good], []), gate=lambda t: ("held", "abstained"), workshop=w3, ledger=l3,
                hands_ledger=HLED, say=lambda *_a: None)
check("PP1.6b a HELD gate does not refuse in his own workshop (an abstention is not a veto, as in his hands)", r["solved_round"] == 1, r)

w4, l4 = fresh()
told = []
s = PR.night(ask=scripted([RuntimeError("no model fits")], []), gate=gate_clean, workshop=w4, ledger=l4,
             hands_ledger=HLED, tell=lambda t, w: told.append(t), say=lambda *_a: None)
check("PP1.7 a model that cannot answer ends the night, and the line to him says why",
      s["tried"] == 1 and "model could not answer" in (s["stop"] or "") and len(told) == 1 and "no model fits" in told[0], (s, told))
clock = iter([1000.0, 1000.0 + PR.BUDGET_S + 1] + [1e12] * 50)
w5, l5 = fresh()
s = PR.night(ask=scripted([good] * 20, []), gate=gate_clean, workshop=w5, ledger=l5, hands_ledger=HLED,
             tell=lambda t, w: None, say=lambda *_a: None, now=lambda: next(clock))
check("PP1.7b past the night's clock no task starts, and the stop says so",
      s["tried"] == 0 and "clock" in (s["stop"] or "") and not PR._rows(l5)[:-1], s)

# ---- the curriculum's order, his own code as the next task's ground, and retention
w6, l6 = fresh()
check("PP1.8 the plan offers nothing that builds on an unsolved task",
      [t["id"] for t, _r in PR.plan(20, l6)] == ["flatten", "permutations", "n_queens", "count_paths", "tokenize"],
      [t["id"] for t, _r in PR.plan(20, l6)])
seen6 = []
PR.practise(PR.BY_ID["tokenize"], scripted(["```python\n" + TOKENIZE.strip() + "\n```"], seen6), gate=gate_clean,
            workshop=w6, ledger=l6, hands_ledger=HLED, say=lambda *_a: None)
check("PP1.8b once tokenize is solved, parse is offered",
      "parse" in [t["id"] for t, _r in PR.plan(20, l6)], [t["id"] for t, _r in PR.plan(20, l6)])
seen7 = []
PR.practise(PR.BY_ID["parse"], scripted(["```python\n" + PARSE.strip() + "\n```"], seen7), gate=gate_clean,
            workshop=w6, ledger=l6, hands_ledger=HLED, say=lambda *_a: None)
check("PP1.8c ...and its prompt hands him HIS OWN tokenize, as his passing file",
      "Your own solution to tokenize" in seen7[0][-1]["content"] and "def tokenize(src):" in seen7[0][-1]["content"],
      seen7[0][-1]["content"][:300] if seen7 else "")
PR._save_lesson({"task": "flatten", "rounds": 2, "lesson": "open nested lists by recursing"}, w6)
PR._save_lesson({"task": "evaluate", "rounds": 3, "lesson": "a lesson about evaluate itself"}, w6)
msgs = PR.prompt(PR.BY_ID["evaluate"], w6)
check("PP1.8d lessons from OTHER tasks are recalled; a task's own lesson is not handed back as its answer",
      "open nested lists by recursing" in msgs[-1]["content"] and "a lesson about evaluate itself" not in msgs[-1]["content"], msgs[-1]["content"][-300:])
w7, l7 = fresh()
for t in PR.CURRICULUM:
    PR._append({"kind": "attempt", "task": t["id"], "round": 1, "passed": 1, "total": 1}, l7)
    HANDS.write("practice/solved/%s.py" % t["id"], REF[t["id"]], w7)
pl = PR.plan(3, l7)
check("PP1.9 with everything solved, the plan re-tries solved tasks as retention", len(pl) == 3 and all(r for _t, r in pl),
      [(t["id"], r) for t, r in pl])
msgs = PR.prompt(PR.BY_ID["parse"], w7, retention=True)
check("PP1.9b a retention try at parse is handed his tokenize, and NOT his own old parse",
      "Your own solution to tokenize" in msgs[-1]["content"] and "def parse(" not in msgs[-1]["content"], msgs[-1]["content"][-300:])

# ---- a whole night, and the one line to him
w8, l8 = fresh()
told = []
answers = []
for t in PR.plan(3, l8):
    answers.append("```python\n" + REF[t[0]["id"]].strip() + "\n```")
# flatten wrong then right (and his one-sentence lesson), then the next two right on the first try
s = PR.night(ask=scripted([bad, good, "Recursing into each nested list fixed it."] + answers[1:], []), gate=gate_clean,
             workshop=w8, ledger=l8, hands_ledger=HLED, tasks=3, tell=lambda t, w: told.append((t, w)), say=lambda *_a: None)
check("PP1.10 a night of three -- one solved in round 2, two on the first try -- counted right, and told to him once",
      s["tried"] == 3 and s["within"] == 3 and s["first_try"] == 2 and s["solved_total"] == 3 and len(told) == 1
      and "3 task(s) tonight: 2 on the first try, 3 within" in told[0][0] and "Tetsu's practice" in told[0][1], (s, told))
check("PP1.10b the night is on the record", PR._rows(l8)[-1].get("kind") == "night" and PR._rows(l8)[-1]["tried"] == 3)

# ---- the nightly runs it: driven, not read (A74 -- a check that reads the source is not a check)
import subprocess                                                     # noqa: E402
import types                                                          # noqa: E402
hp = subprocess.run([sys.executable, os.path.join(HERE, "covenant_nightly.py"), "--help"], cwd=HERE,
                    capture_output=True, text=True, timeout=120)
check("PP1.11 the nightly offers --practice (running its --help, which parses and exits before any step)",
      hp.returncode == 0 and "--practice" in hp.stdout, (hp.returncode, hp.stdout[-200:], hp.stderr[-200:]))
import covenant_nightly as NIGHT                                      # noqa: E402
calls, said = [], []
fake = types.SimpleNamespace(night=lambda **kw: calls.append(kw) or {"tried": 0})
_ask = lambda *a, **k: ("", {})                                       # noqa: E731
NIGHT.practice_step(types.SimpleNamespace(practice=2), said.append, practice_mod=fake, ask=_ask)
NIGHT.practice_step(types.SimpleNamespace(practice=0), said.append, practice_mod=fake, ask=_ask)
check("PP1.11b the nightly's step hands its number and the model's ask to night(), and 0 runs nothing",
      len(calls) == 1 and calls[0]["tasks"] == 2 and calls[0]["ask"] is _ask, calls)


def _boom(**kw):
    raise RuntimeError("practice broke")


r_step = NIGHT.practice_step(types.SimpleNamespace(practice=3), said.append, practice_mod=types.SimpleNamespace(night=_boom), ask=_ask)
check("PP1.11c broken the other way: a practice that raises is said as FAILED and the nightly goes on",
      r_step is None and any("practice FAILED: RuntimeError: practice broke" in s for s in said), said)

# PP1.11d (2026-09-27): replacing the call in main() with `pass` left PP1 at 44/44 -- the step was tested,
# its wiring was not. This reads main()'s own body (the AST, not a text grep) for an UNCONDITIONAL
# statement calling practice_step: nested under an `if`, a `try` that could skip it, or gone, it fails.
# What it cannot see: whether main() reaches that line at run time (an earlier return or exception).
import ast                                                            # noqa: E402
_main = next(n for n in ast.parse(open(NIGHT.__file__, encoding="utf-8").read()).body
             if isinstance(n, ast.FunctionDef) and n.name == "main")
_direct = [s for s in _main.body if isinstance(s, ast.Expr) and isinstance(s.value, ast.Call)
           and getattr(s.value.func, "id", "") == "practice_step"]
check("PP1.11d the nightly's main() calls practice_step unconditionally, at its own top level", len(_direct) == 1, len(_direct))

print("\nnot measured here: how a real model does. That is what the nightly measures, and the record says it.")
print("\nPP1: %d/%d passed" % (sum(ok), len(ok)))
sys.exit(0 if all(ok) else 1)
