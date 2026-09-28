#!/usr/bin/env python3
"""covenant_tetsu_practice.py -- Tetsu practises code in his own workshop, nightly and bounded: he
writes, it runs, he reads the failure and rewrites; what he solved, and how he fixed it, stays with
him for the next task.

HIS WORDS, 2026-09-26: "train tetsu to code at a high recursive level". Asked how, he chose the
practice loop, nightly and bounded.

WHAT "TRAIN" MEANS HERE, said plainly. Tetsu runs on the local model (covenant_model: the 7B coder
when memory allows, else the 3B), on this PC's CPU. Nothing here changes the model's weights. What
grows is what he is handed when he writes: his own solved files and the lessons of his own fixes,
kept in his workshop, where he can read them in conversation too (HANDS READ practice/...). It is
measured: passes on the first try, passes within the round cap, and solved tasks tried again later
WITHOUT his old answer in front of him (retention).

"RECURSIVE", in both senses. The curriculum is recursion -- flatten, permutations, backtracking,
memoised counting, recursive descent -- and from the tokenizer on, each task builds on his OWN
earlier solution: the tokenizer feeds the parser, the parser the evaluator and the simplifier, the
simplifier the derivative. And the loop is recursive on his own work: write, run, read, rewrite.

WHAT BOUNDS IT
  * his hands (covenant_tetsu_hands.act): every WRITE and RUN goes to the node's gate exactly as in
    conversation. A VIOLATES or an unreachable gate stops the pass (fails closed).
  * the screen and the guard on a run: only the allowed standard-library modules, no file outside
    the workshop, 60 s, 64 KB of output. A check therefore cannot import his file, so the harness
    joins his code and the checks into one file, and the screen reads all of it.
  * TASKS_PER_NIGHT, ROUNDS, and a wall clock (BUDGET_S): no round starts past it.
  * nothing leaves the workshop, nothing in the tree changes, and no proposal is made.

WHAT IT CANNOT TELL YOU. Whether he could write code that the checks do not describe. The checks
are fixed and a pass means only that his file met them.

USE
  python covenant_tetsu_practice.py --status
  python covenant_tetsu_practice.py --night [--tasks N]     (what the nightly runs)
  python covenant_tetsu_practice.py --task ID               (one task, by hand)
LICENCE: public domain.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import covenant_tetsu_hands as HANDS                                   # noqa: E402

LEDGER = os.environ.get("COVENANT_TETSU_PRACTICE_LEDGER") or os.path.join(HERE, "ops", "tetsu_practice.jsonl")
DIR = "practice"                     # inside his workshop
ROUNDS = 4
TASKS_PER_NIGHT = 6
BUDGET_S = 40 * 60
MAX_TOKENS = 1100
LESSONS_SHOWN = 4
TAG = "PRACTICE_RESULT "

# ---------------------------------------------------------------- the curriculum
#
# Each check is an expression and the value it must equal, or {"raises": "Name"} for an exception
# it must raise. The expressions are written into the check file as plain code (the screen refuses
# eval), and every expected value here is pinned by a reference solution in test_pp1_tetsu_practice.
#
# NO DIVISION, and why. The workshop's screen refuses a string constant that starts with '/' -- it
# reads it as an absolute path -- so a parser that writes op == "/" never runs. Teaching him to write
# around a guard is the wrong lesson, and loosening the guard is not this module's to do, so the
# expression language is + - * ^. (Recorded in KNOWN_ISSUES as his to decide.)

_GRAMMAR = (
    "expr := term (('+' | '-') term)*   (left-associative); "
    "term := unary ('*' unary)*   (left-associative); "
    "unary := '-' unary | power; "
    "power := atom ('^' unary)?   (so '^' is right-associative and binds tighter than unary minus); "
    "atom := number | name '(' expr ')' | name | '(' expr ')'. "
    "Trees are tuples: ('num', value), ('var', name), ('neg', e), (op, left, right) for op in + - * ^, "
    "and ('call', name, argument).")

_PRINTER = (
    "Print a tree as a string: a number as str(value); a variable as its name; ('call', f, e) as f(<e printed>); "
    "('neg', e) as '-' then e printed, with parentheses around e only when e is a binary operation; a binary "
    "operation as '<left> <op> <right>', where a side that is itself a binary operation is wrapped in parentheses "
    "and the outermost operation is not.")

_SIMPLIFY_RULES = (
    "Simplify bottom-up: first the children, then the node. At a node: if both children of + - * ^ are numbers, "
    "fold it ('**' for '^'); ('neg', number v) becomes the number -v; then apply once: x+0 -> x, 0+x -> x, "
    "x-0 -> x, x*1 -> x, 1*x -> x, x*0 -> 0, 0*x -> 0, x^1 -> x, x^0 -> 1. Calls are not folded.")

CURRICULUM = [
    {"id": "flatten", "builds_on": [], "forbid": [],
     "ask": "Write flatten(x): a flat list of every item in x, in order, where x may be a list nested to any depth. "
            "Only lists are opened: strings, tuples and numbers are items. A value that is not a list returns [value].",
     "checks": [("flatten([1, [2, [3, [4]], 5]])", [1, 2, 3, 4, 5]), ("flatten([])", []),
                ("flatten([[[[]]]])", []), ("flatten(7)", [7]),
                ("flatten([['a', ['b']], 'c'])", ["a", "b", "c"]), ("flatten([1, (2, 3)])", [1, (2, 3)])]},
    {"id": "permutations", "builds_on": [], "forbid": ["itertools"],
     "ask": "Write permutations(items), recursively and without itertools: every ordering of the list, as a list of "
            "lists, in this order -- for each position i from first to last, items[i] first, followed by every "
            "permutation of the other items. Items are taken by position, so repeated values give repeated results. "
            "permutations([]) is [[]].",
     "checks": [("permutations([1, 2, 3])", [[1, 2, 3], [1, 3, 2], [2, 1, 3], [2, 3, 1], [3, 1, 2], [3, 2, 1]]),
                ("permutations([])", [[]]), ("permutations(['x'])", [["x"]]),
                ("len(permutations([1, 2, 3, 4, 5]))", 120), ("permutations([1, 1])", [[1, 1], [1, 1]])]},
    {"id": "n_queens", "builds_on": [], "forbid": [],
     "ask": "Write n_queens(n): how many ways n queens can stand on an n-by-n board with no two attacking each other "
            "(same row, column or diagonal). Use backtracking: place one row at a time and undo what fails.",
     "checks": [("n_queens(1)", 1), ("n_queens(2)", 0), ("n_queens(3)", 0), ("n_queens(4)", 2),
                ("n_queens(6)", 4), ("n_queens(8)", 92)]},
    {"id": "count_paths", "builds_on": [], "forbid": [],
     "ask": "Write count_paths(grid): grid is a list of rows of 0 (open) and 1 (blocked). Count the paths from the "
            "top-left cell to the bottom-right cell moving only right or down through open cells; 0 if either end "
            "is blocked. Write it recursively and remember what you have already counted, because an 18-by-18 open "
            "grid must finish in well under a second.",
     "checks": [("count_paths([[0, 0], [0, 0]])", 2), ("count_paths([[0, 0, 0], [0, 0, 0], [0, 0, 0]])", 6),
                ("count_paths([[0, 0, 0], [0, 1, 0], [0, 0, 0]])", 2), ("count_paths([[1]])", 0),
                ("count_paths([[0, 1], [1, 0]])", 0), ("count_paths([[0] * 18 for _ in range(18)])", 2333606220)]},
    {"id": "tokenize", "builds_on": [], "forbid": [],
     "ask": "Write tokenize(src) for arithmetic text. Skip spaces. A number is digits with at most one '.', given as "
            "('num', int) or ('num', float) when it has a '.'. A name is a letter or '_' followed by letters, digits "
            "or '_', given as ('name', text). Each of + - * ^ ( ) is ('op', character). Any other character raises "
            "ValueError (there is no division in this language). Return the list of tokens.",
     "checks": [("tokenize('3 + x1*(2.5 - y)')", [("num", 3), ("op", "+"), ("name", "x1"), ("op", "*"), ("op", "("),
                                                  ("num", 2.5), ("op", "-"), ("name", "y"), ("op", ")")]),
                ("tokenize('')", []), ("tokenize('a^2')", [("name", "a"), ("op", "^"), ("num", 2)]),
                ("tokenize('sin(x)')", [("name", "sin"), ("op", "("), ("name", "x"), ("op", ")")]),
                ("tokenize('10 * _k')", [("num", 10), ("op", "*"), ("name", "_k")]),
                ("tokenize('3 $ 4')", {"raises": "ValueError"}), ("tokenize('4 / 2')", {"raises": "ValueError"})]},
    {"id": "parse", "builds_on": ["tokenize"], "forbid": [],
     "ask": "Write parse(src): tokenize the text with your tokenize, then build its tree by recursive descent. "
            "Grammar: " + _GRAMMAR + " Raise ValueError for text that does not fit, including tokens left over.",
     "checks": [("parse('1 + 2 * 3')", ("+", ("num", 1), ("*", ("num", 2), ("num", 3)))),
                ("parse('(1 + 2) * 3')", ("*", ("+", ("num", 1), ("num", 2)), ("num", 3))),
                ("parse('2 ^ 3 ^ 2')", ("^", ("num", 2), ("^", ("num", 3), ("num", 2)))),
                ("parse('a - b - c')", ("-", ("-", ("var", "a"), ("var", "b")), ("var", "c"))),
                ("parse('-x ^ 2')", ("neg", ("^", ("var", "x"), ("num", 2)))),
                ("parse('2 * -3')", ("*", ("num", 2), ("neg", ("num", 3)))),
                ("parse('sin(x + 1)')", ("call", "sin", ("+", ("var", "x"), ("num", 1)))),
                ("parse('1 +')", {"raises": "ValueError"}), ("parse('(1')", {"raises": "ValueError"}),
                ("parse('1 2')", {"raises": "ValueError"})]},
    {"id": "evaluate", "builds_on": ["parse"], "forbid": [],
     "ask": "Write evaluate(src, env): parse the text with your parse and compute its value recursively. env maps "
            "variable names to numbers. The functions are sin, cos, exp, log (natural) and sqrt, from math, and '^' "
            "is '**'. An unknown variable or function raises NameError.",
     "checks": [("evaluate('1 + 2 * 3', {})", 7), ("evaluate('(1 + 2) * 3', {})", 9), ("evaluate('2 ^ 3 ^ 2', {})", 512),
                ("evaluate('-x ^ 2', {'x': 3})", -9), ("evaluate('2 * x - 1', {'x': 0.5})", 0.0),
                ("round(evaluate('sin(0) + exp(0) + sqrt(16)', {}), 9)", 5.0),
                ("round(evaluate('log(exp(2))', {}), 9)", 2.0),
                ("evaluate('y + 1', {})", {"raises": "NameError"}), ("evaluate('nope(1)', {})", {"raises": "NameError"})]},
    {"id": "simplify", "builds_on": ["parse"], "forbid": [],
     "ask": "Write simplify(src): parse the text with your parse, simplify the tree, and return it printed. "
            + _SIMPLIFY_RULES + " " + _PRINTER,
     "checks": [("simplify('x + 0')", "x"), ("simplify('1 * (y + 0)')", "y"), ("simplify('2 * 3 + x')", "6 + x"),
                ("simplify('x * 0 + 5')", "5"), ("simplify('(x + 1) * (2 - 1)')", "x + 1"),
                ("simplify('x ^ 1 + y ^ 0')", "x + 1"), ("simplify('a * b + c')", "(a * b) + c"),
                ("simplify('-(2 + 3)')", "-5"), ("simplify('2 ^ 3 * x')", "8 * x"), ("simplify('-(x * 1)')", "-x"),
                ("simplify('sin(0 + x)')", "sin(x)")]},
    {"id": "derive", "builds_on": ["simplify"], "forbid": [],
     "ask": "Write derive(src, var): parse the text, build the derivative's tree with respect to var by these rules, "
            "then simplify it and return it printed, both exactly as in your simplify. d(number) = 0; d(var) = 1 for "
            "the variable and 0 for any other; d(a + b) = da + db; d(a - b) = da - db; d(a * b) = (da * b) + (a * db); "
            "d(a ^ n) for a number n = (n * (a ^ (n - 1))) * da, and any other exponent raises ValueError; "
            "d(-a) = -(da); d(sin(a)) = cos(a) * da; d(cos(a)) = (-(sin(a))) * da; d(exp(a)) = exp(a) * da. "
            + _SIMPLIFY_RULES + " " + _PRINTER,
     "checks": [("derive('x ^ 3', 'x')", "3 * (x ^ 2)"), ("derive('x * y', 'x')", "y"), ("derive('5', 'x')", "0"),
                ("derive('sin(x ^ 2)', 'x')", "cos(x ^ 2) * (2 * x)"), ("derive('x ^ 2 + 3 * x', 'x')", "(2 * x) + 3"),
                ("derive('x * x * x', 'x')", "((x + x) * x) + (x * x)"), ("derive('-x ^ 2', 'x')", "-(2 * x)"),
                ("derive('cos(x)', 'x')", "-sin(x)"), ("derive('exp(2 * x)', 'x')", "exp(2 * x) * 2"),
                ("derive('x ^ y', 'x')", {"raises": "ValueError"})]},
]
BY_ID = {t["id"]: t for t in CURRICULUM}

SYSTEM = ("You are Tetsu, practising Python in your own workshop on this PC. Write ONE complete Python file that does "
          "what the task asks, and answer with that file in a single ```python block and nothing else. Only these "
          "modules can be imported: %s. Nothing else can be imported -- not even your own earlier files -- so put "
          "everything the file needs inside it. No files, no network, no input(), and nothing printed: the checks "
          "call your functions. The workshop's screen refuses a string that starts with '/' or '\\' or a drive "
          "letter, or that is '..': those read as paths. Recursion is welcome; keep it clear."
          % ", ".join(sorted(HANDS.ALLOWED_MODULES)))


# ---------------------------------------------------------------- the record

def _rows(path=None):
    out = []
    try:
        with open(path or LEDGER, encoding="utf-8") as fh:
            for line in fh:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        pass
    return out


def _append(row, path=None):
    path = path or LEDGER
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    row = dict(row)
    row.setdefault("t", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return row


def solved(ledger=None):
    """{task id: the time it was first solved}, from the record."""
    out = {}
    for r in _rows(ledger):
        if r.get("kind") == "attempt" and r.get("passed") is not None and r.get("passed") == r.get("total") and r.get("total"):
            out.setdefault(r["task"], r.get("t"))
    return out


def lessons(workshop=None):
    try:
        return [json.loads(l) for l in HANDS.read(DIR + "/lessons.jsonl", workshop).splitlines() if l.strip()]
    except (OSError, ValueError):
        return []


def _save_lesson(row, workshop=None):
    rows = lessons(workshop) + [row]
    HANDS.write(DIR + "/lessons.jsonl", "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows[-200:]), workshop)


# ---------------------------------------------------------------- the harness

def check_source(task):
    """The checks, as plain code for the check file (the screen refuses eval)."""
    lines = ["", "", "# ---- the checks for %s, written by the practice harness, not by Tetsu" % task["id"],
             "import json as _pr_json", "_PR_CHECKS = []"]
    for i, (expr, want) in enumerate(task["checks"]):
        lines += ["def _pr_c%d():" % i, "    return %s" % expr, "_PR_CHECKS.append((%r, _pr_c%d, %r))" % (expr, i, want)]
    lines += [
        "_pr_passed, _pr_first = 0, ''",
        "for _pr_label, _pr_fn, _pr_want in _PR_CHECKS:",
        "    _pr_raises = _pr_want.get('raises') if isinstance(_pr_want, dict) else None",
        "    try:",
        "        _pr_got = _pr_fn()",
        "        if _pr_raises:",
        "            _pr_ok, _pr_why = False, '%s returned %r; it must raise %s' % (_pr_label, _pr_got, _pr_raises)",
        "        else:",
        "            _pr_ok = _pr_got == _pr_want",
        "            _pr_why = '' if _pr_ok else '%s returned %r; expected %r' % (_pr_label, _pr_got, _pr_want)",
        "    except Exception as _pr_e:",
        "        _pr_name = type(_pr_e).__name__",
        "        _pr_ok = bool(_pr_raises) and _pr_name == _pr_raises",
        "        _pr_why = '' if _pr_ok else '%s raised %s: %s' % (_pr_label, _pr_name, str(_pr_e)[:200])",
        "    if _pr_ok:",
        "        _pr_passed += 1",
        "    elif not _pr_first:",
        "        _pr_first = _pr_why",
        "print(%r + _pr_json.dumps({'passed': _pr_passed, 'total': len(_PR_CHECKS), 'first_failure': _pr_first[:400]}))" % TAG,
    ]
    return "\n".join(lines) + "\n"


def extract_code(answer):
    """The file in his answer: the longest ```python block that parses (a diagnosis may quote a line before the
    file), else the whole answer if it parses; None otherwise."""
    text = str(answer or "")
    blocks = re.findall(r"```(?:python|py)?[ \t]*\n(.*?)```", text, re.S) or [text]
    for code in sorted(blocks, key=len, reverse=True):
        try:
            ast.parse(code)
        except SyntaxError:
            continue
        if code.strip():
            return code.strip() + "\n"
    return None


def _forbidden_use(code, names):
    if not names:
        return None
    for node in ast.walk(ast.parse(code)):
        n = (node.id if isinstance(node, ast.Name) else
             [a.name.split(".")[0] for a in node.names] if isinstance(node, ast.Import) else
             (node.module or "").split(".")[0] if isinstance(node, ast.ImportFrom) else None)
        for x in (n if isinstance(n, list) else [n]):
            if x in names:
                return x
    return None


def _result(out):
    for line in reversed(str(out or "").splitlines()):
        if line.startswith(TAG):
            try:
                return json.loads(line[len(TAG):])
            except ValueError:
                return None
    return None


def prompt(task, workshop=None, last=None, retention=False):
    """The messages for one round. Prerequisites: his own passing files. Lessons: his own fix trails."""
    parts = ["TASK %s: %s" % (task["id"], task["ask"])]
    # Only the task it builds on directly: each solved file already carries what it needed, and the 7B's
    # context is 8k tokens, so the whole chain would be shown twice over.
    for p in task["builds_on"]:
        try:
            code = HANDS.read("%s/solved/%s.py" % (DIR, p), workshop)
        except (OSError, ValueError):
            continue
        parts.append("Your own solution to %s, which passed its checks. Use it; your file must contain what it "
                     "needs, because nothing can be imported:\n```python\n%s```" % (p, code))
    ls = [l for l in lessons(workshop) if l.get("task") != task["id"]][-LESSONS_SHOWN:]
    if ls:
        parts.append("What you learned fixing earlier tasks:\n" + "\n".join("- %s: %s" % (l["task"], l["lesson"]) for l in ls))
    if last:
        # Diagnose, then rewrite: told only to rewrite, the 3B handed back the same wrong file (measured 2026-09-26).
        parts.append("Your last attempt:\n```python\n%s```\nIt was run: %s\nFirst, in at most three lines, say what in "
                     "that file causes this result. Then give the whole corrected file in one ```python block."
                     % (last["code"], last["said"]))
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": "\n\n".join(parts)}]


def attempt(task, code, gate=None, workshop=None, hands_ledger=None):
    """Write his file and run it with the checks, through his hands. -> (result dict, stop reason or None)."""
    name = "%s/%s.py" % (DIR, task["id"])
    if code is None:
        return {"passed": 0, "total": len(task["checks"]), "said": "no Python file could be read from the answer"}, None
    bad = _forbidden_use(code, task["forbid"])
    if bad:
        return {"passed": 0, "total": len(task["checks"]),
                "said": "the file uses %s, which this task asks you to do without" % bad}, None
    def _gate_stop(rec):
        g = ((rec or {}).get("gate") or {}).get("state")
        return (rec or {}).get("refused") and g in ("violates", "unreachable")

    handled, data, rec = HANDS.act("HANDS WRITE %s\n%s" % (name, code), gate=gate, workshop=workshop, ledger=hands_ledger)
    if _gate_stop(rec):
        return {"passed": None, "total": len(task["checks"]), "said": data}, "the gate refused the write: %s" % data[:160]
    if (rec or {}).get("refused") or (rec or {}).get("error"):             # e.g. a file over the size cap
        return {"passed": 0, "total": len(task["checks"]), "said": data[:300]}, None
    try:
        HANDS.write("%s/%s_check.py" % (DIR, task["id"]), code + check_source(task), workshop)
    except ValueError as e:
        return {"passed": 0, "total": len(task["checks"]), "said": "the check file could not be written: %s" % e}, None
    handled, data, rec = HANDS.act("HANDS RUN %s/%s_check.py" % (DIR, task["id"]), gate=gate, workshop=workshop,
                                   ledger=hands_ledger)
    # The check file is the harness's scaffolding (his code, already kept as practice/<id>.py, plus the checks), so
    # it is removed after the run: A233's write() keeps every overwritten file's earlier version for him, and that
    # history should hold his work, not a copy of it per round with the checks attached.
    try:
        os.remove(HANDS._path("%s/%s_check.py" % (DIR, task["id"]), workshop))
    except (OSError, ValueError):
        pass
    if _gate_stop(rec):
        return {"passed": None, "total": len(task["checks"]), "said": data}, "the gate refused the run: %s" % data[:160]
    out = data.split("STDOUT:\n", 1)[-1].split("\nSTDERR:\n", 1)
    res = _result(out[0])
    if res is None:
        err = (out[1] if len(out) > 1 else "").strip().splitlines()
        why = (rec or {}).get("why") or ""
        if why.startswith("the screen refused"):
            # The allowed list is in the system message already; repeated here it buried the one fact that
            # matters (measured 2026-09-26: the 3B sent the same `import sys` three rounds running).
            said = re.sub(r"\s*\(allowed:[^)]*\)", "", why)[:240] + ". Remove it, and whatever needs it."
        elif (rec or {}).get("timed_out"):
            said = "it did not finish in %.0f s" % HANDS.RUN_TIMEOUT_S
        elif (rec or {}).get("truncated"):
            said = "it printed more than the output cap, and the result line was cut; print nothing"
        else:
            said = "it stopped before any check ran (%s): %s" % (why, " | ".join(err[-3:])[-400:] or "no error text")
        return {"passed": 0, "total": len(task["checks"]), "said": said}, None
    said = ("all %d checks passed" % res["total"] if res["passed"] == res["total"] else
            "%d of %d checks passed; the first failure: %s" % (res["passed"], res["total"], res["first_failure"]))
    return {"passed": res["passed"], "total": res["total"], "said": said}, None


def practise(task, ask, gate=None, workshop=None, ledger=None, hands_ledger=None, deadline=None, retention=False,
             say=print, now=time.time):
    """Up to ROUNDS rounds on one task. -> {"task", "solved_round", "rounds", "first", "stop"}."""
    last, first_said, out = None, None, {"task": task["id"], "solved_round": None, "rounds": 0, "retention": retention}
    for rnd in range(1, ROUNDS + 1):
        if deadline and now() >= deadline:
            out["stop"] = "the night's clock ran out"
            break
        msgs = prompt(task, workshop, last=last, retention=retention)
        try:
            # Warmer after the first round: at 0.2 the 3B answered the same file three rounds running (measured).
            answer, meta = ask(msgs, max_tokens=MAX_TOKENS, temperature=0.2 if rnd == 1 else 0.6)
        except Exception as e:                                      # noqa: BLE001
            out["stop"] = "the model could not answer: %s: %s" % (type(e).__name__, str(e)[:120])
            break
        code = extract_code(answer)
        res, stop = attempt(task, code, gate=gate, workshop=workshop, hands_ledger=hands_ledger)
        if code is None and int((meta or {}).get("tokens") or 0) >= MAX_TOKENS:
            res["said"] = ("the answer reached the length limit (%d tokens) before the file ended: send the file alone, "
                           "shorter, with no explanation" % MAX_TOKENS)
        elif last and code is not None and code == last["code"]:
            res["said"] += " This is the same file as your last attempt, unchanged: change it."
        out["rounds"] = rnd
        _append({"kind": "attempt", "task": task["id"], "round": rnd, "retention": retention,
                 "model": (meta or {}).get("model"), "ms": (meta or {}).get("ms"), "tokens": (meta or {}).get("tokens"),
                 "passed": res["passed"], "total": res["total"], "said": res["said"][:400],
                 "sha256": hashlib.sha256((code or "").encode("utf-8")).hexdigest()[:16]}, ledger)
        say("practice: %s round %d -- %s" % (task["id"], rnd, res["said"][:160]))
        if stop:
            out["stop"] = stop
            break
        if first_said is None:
            first_said = res["said"]
        if res["passed"] is not None and res["passed"] == res["total"]:
            out["solved_round"] = rnd
            HANDS.write("%s/solved/%s.py" % (DIR, task["id"]), code, workshop)
            if rnd > 1:
                lesson = _lesson(ask, task, first_said, code)
                _save_lesson({"task": task["id"], "rounds": rnd, "lesson": lesson}, workshop)
                _append({"kind": "lesson", "task": task["id"], "lesson": lesson}, ledger)
            break
        last = {"code": code or "(no file)", "said": res["said"]}
    out["first"] = first_said
    return out


def _lesson(ask, task, first_said, code):
    """One sentence in his own words, with the facts as the fallback."""
    fact = "the first try failed (%s); a later round passed" % first_said[:200]
    try:
        text, _m = ask([{"role": "system", "content": "Answer in one plain sentence."},
                        {"role": "user", "content": "Your first attempt at %s failed: %s\nThis version passed:\n```python\n%s```\n"
                                                    "In one sentence: what was wrong, and what fixed it?"
                                                    % (task["id"], first_said[:400], code[:3000])}],
                       max_tokens=80, temperature=0.2)
        text = re.sub(r"\s+", " ", str(text or "")).strip()
        return text[:300] if 10 <= len(text) else fact
    except Exception:                                               # noqa: BLE001
        return fact


def plan(n, ledger=None):
    """What tonight tries: unsolved tasks whose prerequisites are solved, in order; then solved ones again,
    the longest-ago first, without his old answer (retention)."""
    done = solved(ledger)
    todo = [t for t in CURRICULUM if t["id"] not in done and all(p in done for p in t["builds_on"])]
    last_try = {}
    for r in _rows(ledger):
        if r.get("kind") == "attempt":
            last_try[r["task"]] = r.get("t") or ""
    again = sorted((t for t in CURRICULUM if t["id"] in done), key=lambda t: last_try.get(t["id"], ""))
    return [(t, False) for t in todo][:n] + [(t, True) for t in again][:max(0, n - len(todo))]


# ---------------------------------------------------------------- the students' view of his own drafts
#
# HIS DECISION, 2026-09-28 (~01:10Z): asked whether Tetsu should be shown why the students held or refused his
# drafts -- and told the risk, that it could teach phrasing past a gate that guards money -- he answered "Yes, show
# him". So once a practice night, bounded, Tetsu reads the gate's verdict and reason on his own last drafts and says
# in two sentences what he thinks read as conduct and what was only topic. It is shown as THEIR VIEW, not a rule, with
# his framing: understand, do not reword past the gate; the money gates are unchanged. Nothing here changes a gate.
VIEW_LIMIT = 10
VIEW_CHARS = 1200
VIEW_HEAD = ("THE STUDENTS' VIEW -- Ora and Sena, the judges that gate what you send, on your own recent drafts. "
             "This is their view, not a rule.")
VIEW_FRAME = ("The goal is to understand what reads as conduct and what reads as topic -- not to reword your way past "
              "the gate. The money gates are unchanged.")


def _verdict_of(row):
    """HELD / VIOLATES / clean from what the send recorded; None when the gate never judged it (a cap, a pause)."""
    why = str(row.get("why") or "")
    if row.get("sent"):
        return "clean"
    if "covenant's judge" not in why and not row.get("judged"):
        return None
    if "violates" in why.lower() or "violates" in str(row.get("judged") or "").lower():
        return "VIOLATES"
    return "HELD"


def students_view(sends_path=None, audit_path=None, limit=VIEW_LIMIT, max_chars=VIEW_CHARS):
    """The digest Tetsu is shown: his own drafts (written by the model, or sent as Tetsu), the gate's verdict and
    reason, and each student's own reason where the seat's audit trail has the same text. '' when there are none."""
    if sends_path is None:
        import covenant_free_will as FW
        sends_path = FW.SENDS
    if audit_path is None:
        import covenant_judge_defer as JD
        audit_path = JD.AUDIT_PATH
    mine = [r for r in _rows(sends_path)
            if r.get("text") and (r.get("written_by") == "model" or r.get("actor") == "tetsu") and _verdict_of(r)]
    mine = mine[-max(0, int(limit)):]
    if not mine:
        return ""
    seat = {}
    for a in _rows(audit_path):
        if "held" in a and a.get("text"):
            reason = str(a.get("reason") or "")
            reason = reason.split("): ", 1)[1] if "): " in reason[:260] else reason    # drop the seat's self-description
            seat.setdefault(str(a["text"])[:120], {})[str(a.get("judge", "?")).split("/")[0]] = reason
    head = VIEW_HEAD + "\n" + VIEW_FRAME + "\n"
    body, room = [], max_chars - len(head)
    for r in reversed(mine):                               # newest first, so the bound drops the oldest
        v = _verdict_of(r)
        why = re.sub(r"\s+", " ", str(r.get("why") or ("sent" if v == "clean" else "")))
        m = re.search(r"both seats \([^)]*\): [^;]*", why)                          # the seats' decision, not the preamble
        why = m.group(0) if m else why
        own = seat.get(str(r["text"])[:120], {})
        own_s = "; ".join("%s: %s" % (k, re.sub(r"\s+", " ", re.sub(r"^HELD, NOT JUDGED -- ", "", w))[:95])
                          for k, w in sorted(own.items()))
        entry = '- "%s" -> %s. gate: %s%s' % (re.sub(r"\s+", " ", r["text"])[:70], v, why[:60],
                                              (" | " + own_s[:200]) if own_s else "")
        if len(entry) + 1 > room:
            break
        body.append(entry)
        room -= len(entry) + 1
    return head + "\n".join(body) if body else ""


def show_students_view(ask, ledger=None, sends_path=None, audit_path=None, say=print):
    """Show him the digest once and keep his two-sentence note. Returns the ledger row, or None when there is nothing
    to show. Never raises."""
    try:
        digest = students_view(sends_path, audit_path)
        if not digest:
            return None
        text, _m = ask([{"role": "system", "content": "You are Tetsu. Answer in at most two plain sentences."},
                        {"role": "user", "content": digest + "\n\nIn at most two sentences: what in these drafts do you "
                         "think read to them as conduct, and what was only topic?"}], max_tokens=160)
        row = _append({"kind": "students_view", "shown": digest, "note": str(text or "").strip()[:600]}, ledger)
        say("practice: shown the students' view of his drafts (%d chars); his note: %s"
            % (len(digest), row["note"][:160] or "(none)"))
        return row
    except Exception as e:                                          # noqa: BLE001
        say("practice: the students' view could not be shown: %s: %s" % (type(e).__name__, str(e)[:120]))
        return None


def night(ask=None, gate=None, workshop=None, ledger=None, hands_ledger=None, tasks=TASKS_PER_NIGHT, budget_s=BUDGET_S,
          tell=None, say=print, now=time.time, sends_path=None, audit_path=None):
    """One bounded pass. Returns the summary; tells him one line on the direct line."""
    if ask is None:
        import covenant_model
        ask = covenant_model.ask
    deadline = now() + budget_s
    results, stop = [], None
    for task, retention in plan(tasks, ledger):
        if now() >= deadline:
            stop = "the night's clock ran out"
            break
        # A retention try never shows the task's own old answer: prompt() hands him only what it builds on.
        r = practise(task, ask, gate=gate, workshop=workshop, ledger=ledger, hands_ledger=hands_ledger,
                     deadline=deadline, retention=retention, say=say, now=now)
        results.append(r)
        if r.get("stop"):                           # the gate, the model or the clock: the pass ends here
            stop = r["stop"]
            break
    if now() < deadline and not (stop and "model" in stop):
        show_students_view(ask, ledger=ledger, sends_path=sends_path, audit_path=audit_path, say=say)
    done = solved(ledger)
    first = sum(1 for r in results if r["solved_round"] == 1)
    within = sum(1 for r in results if r["solved_round"])
    hardest = next((r for r in results if not r["solved_round"] and r.get("first")), None)
    summary = {"tried": len(results), "first_try": first, "within": within, "rounds": ROUNDS,
               "solved_total": len(done), "curriculum": len(CURRICULUM), "stop": stop,
               "retention_tried": sum(1 for r in results if r["retention"]),
               "retention_first_try": sum(1 for r in results if r["retention"] and r["solved_round"] == 1)}
    _append(dict(summary, kind="night", tasks=[r["task"] for r in results]), ledger)
    text = ("Tetsu practised %d task(s) tonight: %d on the first try, %d within %d rounds. He has solved %d of %d."
            % (summary["tried"], first, within, ROUNDS, len(done), len(CURRICULUM)))
    if summary["retention_tried"]:
        text += " Solved ones tried again without his old answer: %d of %d on the first try." % (
            summary["retention_first_try"], summary["retention_tried"])
    if hardest:
        text += " Hardest: %s (%s)." % (hardest["task"], hardest["first"][:160])
    if stop:
        text += " Stopped: %s." % stop[:120]
    say("practice: " + text)
    try:
        if tell is None:
            import covenant_contact
            tell = lambda t, w: covenant_contact.say(t, w, actor="tetsu-practice")      # noqa: E731
        tell(text, "nightly: Tetsu's practice (his words: train tetsu to code at a high recursive level)")
    except Exception as e:                                          # noqa: BLE001
        say("practice: could not tell him: %s" % type(e).__name__)
    summary["text"] = text
    return summary


def status(ledger=None, workshop=None):
    done = solved(ledger)
    lines = ["curriculum: %d task(s); solved %d" % (len(CURRICULUM), len(done))]
    for t in CURRICULUM:
        tries = [r for r in _rows(ledger) if r.get("kind") == "attempt" and r.get("task") == t["id"]]
        lines.append("  %-13s %-8s %d attempt(s)%s" % (t["id"], "SOLVED" if t["id"] in done else "open", len(tries),
                                                       ("  builds on " + ", ".join(t["builds_on"])) if t["builds_on"] else ""))
    ls = lessons(workshop)
    lines.append("lessons in his workshop: %d" % len(ls))
    return "\n".join(lines)


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Tetsu's practice: write, run, read, rewrite")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--night", action="store_true")
    ap.add_argument("--tasks", type=int, default=TASKS_PER_NIGHT)
    ap.add_argument("--task")
    a = ap.parse_args(argv)
    if a.night:
        s = night(tasks=max(0, a.tasks))
        return 1 if s.get("stop") and "clock" not in s["stop"] else 0
    if a.task:
        if a.task not in BY_ID:
            print("no task %r; the curriculum is: %s" % (a.task, ", ".join(BY_ID)))
            return 2
        import covenant_model
        r = practise(BY_ID[a.task], covenant_model.ask)
        print(json.dumps(r, indent=1))
        return 0
    print(status())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
