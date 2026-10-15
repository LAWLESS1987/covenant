#!/usr/bin/env python3
"""test_a284_fresh_context.py -- A284: Tetsu's reviews and round updates are read on their own.

WHY. The door replays history per caller ADDRESS, and every ask sent through tools/tetsu_work.py comes
from one: 127.0.0.2. Tetsu's reviews of free's held drafts (covenant_tetsu_assist) and his round updates
(covenant_free_will.tetsu_update) reach the door that way, so each was read beside the batch's and the
earlier reviews' turns. Measured on the node's ask log, 2026-10-06: 33 review asks and 3 update asks, all
from 127.0.0.2; each 10-06 review carried 5 to 9 replayed exchanges, 2 to 5 of them earlier reviews and
their SENDs; and two asks to WRITE a public correction came back "SEND" in a review's form.

THE FIX. {"fresh": true} at /m/agent: no turns replayed into the ask, and its row is replayed into no
later one. covenant_tetsu_assist._default_ask -- the one path reviews and updates use -- sends it and
refuses an answer whose reply does not say "fresh": true (a core older than A284), so the hold stands.

WHAT IT PINS (every check runs the code; none greps it):
  FC1     agent_history() skips a fresh row and keeps the ordinary ones around it
  FC2     the real /m/agent: a fresh ask from a caller WITH history sends the model the rules and the
          question only; the reply and the ask-log row say fresh
  FC3     the next ordinary ask from that caller replays its earlier turns, never the fresh exchange
  FC4     only JSON true is fresh: "true", 1 and "yes" are ordinary asks and replay history
  FC5     nothing else changes for a fresh ask: its answer is still judged and withheld when refused, and
          an admitted one still reaches the teacher queue, not marked private
  FC6     _default_ask sends fresh=True and returns the answer when the door confirms it
  FC7     a door that does not confirm fresh: _default_ask raises, review() records NONE, the hold stands
  FC8     tetsu_update's default ask is the same fresh path; its TELL goes to this suite's own relay, once
  FC8b    the tree's own Moltbook mail queue is byte-identical after the whole suite, or still absent (A350)
  FC8c    the mail queue, the update log and the notify config this suite's code reads are its own (A350)
  FC9     tools/tetsu_work.ask over a real socket: "fresh": true in the body only when asked, from 127.0.0.2
  FC10    every in-tree caller of tools/tetsu_work.ask (found by walking the tree and parsing it) is
          declared, a "fresh" one passes fresh=True, and a declaration with no caller left is stale;
          FC10n drives the same walker over a synthetic undeclared caller and must flag it
  FC11    every in-tree call its STATIC walk can see reaching his mail queue and inbox through the defaults
          (not adversarial shapes: see the list above FC11 in main) -- tetsu_update
          without mail=, mail_tell or mail_flush without a queue and a notify, run_round with tetsu_updates
          on -- is declared with its reason, as many as there are, and a file it cannot parse is not passed;
          FC11n drives the same walker over a synthetic tree and must flag an undeclared one, a miscount, a
          stale declaration and an unparsed file (A350)

What it would otherwise reach is its own. The ask log, teacher queue, grant, assist ledger, immunity files,
pause switch and update log are redirected to its temp files, and since A350 so are the tree's Moltbook mail
queue (covenant_free_will.MAIL_QUEUE), which FC8 wrote a fake letter into from A342 on, and the notify config
every tree shares (COVENANT_NOTIFY_CONFIG), which FC8 handed that letter to. FC8c reads those redirects where
the code reads them; FC8b reads the tree's queue only to show it unchanged. The model is a recorder or
covenant_model's stub, the door a stand-in, the socket server this suite's own. Measured 2026-10-14 with every
open-for-write, replace and rename recorded: a run wrote nothing outside its temp files (Python's bytecode
cache aside), and a loopback stand-in named by the caller's notify config received no letter.
"""
import ast
import json
import os
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
# A350 (2026-10-14): his inbox. covenant_notify reads COVENANT_NOTIFY_CONFIG, or ~/.config/covenant/notify.json --
# outside every tree and shared by all of them -- once, when it is first imported, so the path is set here, before
# anything can import it. From A342 on FC8 left tetsu_update's relay live: each run queued "Moltbook: someone wrote
# back" in the tree it ran in and handed it to that config (measured on a loopback stand-in: 6 runs, 6 letters,
# 13/13 green). This file is never created; FC8c checks the import read it.
NOTIFY_NONE = os.path.join(tempfile.mkdtemp(prefix="a284_notify_"), "notify.json")
os.environ["COVENANT_NOTIFY_CONFIG"] = NOTIFY_NONE
# A350: covenant_free_will's update log and mail queue take overrides now (COVENANT_TETSU_UPDATES, COVENANT_MAIL_QUEUE),
# read once at its import. The update log is this suite's own from that import on. The mail queue's is dropped here so
# that main() reads the TREE's queue as covenant_free_will resolves it (FC8b) before pointing it at its own (FC8c).
OWN = tempfile.mkdtemp(prefix="a284_own_")
os.environ["COVENANT_TETSU_UPDATES"] = os.path.join(OWN, "tetsu_moltbook_updates.jsonl")
os.environ.pop("COVENANT_MAIL_QUEUE", None)

results = []
CALLER = "127.0.0.2"       # the work caller: where reviews and updates come from


def check(label, ok, detail=""):
    results.append(bool(ok))
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", label, "" if ok else "  -- " + str(detail)[:300]), flush=True)


# Every in-tree caller of tools/tetsu_work.ask, and what its asks need. "fresh": each call passes
# fresh=True. "shared": reads the work caller's history on purpose or not yet decided -- named in
# docs/KNOWN_ISSUES.md A284, so a NEW caller cannot join that history without someone deciding it.
DECLARED = {
    "covenant_tetsu_assist.py": "fresh",          # his reviews and, through it, his round updates
    "covenant_earn_business.py": "shared",        # A284: found, dormant since 2026-09-25, not decided here
    "tools/discourse_seat_eval.py": "fresh",      # A322's measurement, one stand-alone question per item (A323)
}
PRUNE = {".git", ".claude", ".trash", "__pycache__", "node_modules", "private", "venv", ".venv"}


def tetsu_work_callers(root):
    """{relative path: [(line, passes fresh=True)]} for every non-test .py under root that calls
    tools/tetsu_work.ask -- found by parsing, not by a name list. Directories are pruned by PATH
    component (A267: a walker that enters .claude/worktrees counts every worktree)."""
    found = {}
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in PRUNE and not x.startswith("pending-")]
        for f in files:
            if not f.endswith(".py") or f.startswith("test_"):
                continue
            p = os.path.join(d, f)
            rel = os.path.relpath(p, root).replace("\\", "/")
            if rel == "tools/tetsu_work.py":
                continue
            try:
                tree = ast.parse(open(p, "rb").read().decode("utf-8", "replace"))
            except (SyntaxError, ValueError, OSError):
                continue
            mods, direct = set(), set()
            for n in ast.walk(tree):
                if isinstance(n, ast.ImportFrom):
                    for a in n.names:
                        if n.module in ("tools", None) and a.name == "tetsu_work":
                            mods.add(a.asname or a.name)
                        elif n.module in ("tools.tetsu_work", "tetsu_work") and a.name == "ask":
                            direct.add(a.asname or a.name)
                elif isinstance(n, ast.Import):
                    for a in n.names:
                        if a.name in ("tetsu_work", "tools.tetsu_work"):
                            mods.add(a.asname or a.name)
            if not mods and not direct:
                continue
            calls = []
            for n in ast.walk(tree):
                if not isinstance(n, ast.Call):
                    continue
                fn = n.func
                hit = ((isinstance(fn, ast.Attribute) and fn.attr == "ask" and isinstance(fn.value, ast.Name)
                        and fn.value.id in mods)
                       or (isinstance(fn, ast.Attribute) and fn.attr == "ask" and isinstance(fn.value, ast.Attribute)
                           and fn.value.attr == "tetsu_work")
                       or (isinstance(fn, ast.Name) and fn.id in direct))
                if hit:
                    fresh = any(k.arg == "fresh" and isinstance(k.value, ast.Constant) and k.value.value is True
                                for k in n.keywords)
                    calls.append((n.lineno, fresh))
            if calls:
                found[rel] = calls
    return found


def guard_problems(found, declared):
    """What FC10 refuses: an undeclared caller, a "fresh" call without fresh=True, a stale declaration."""
    out = []
    for rel, calls in sorted(found.items()):
        how = declared.get(rel)
        if how is None:
            out.append("%s calls tetsu_work.ask (lines %s) and is not declared fresh or shared"
                       % (rel, [c[0] for c in calls]))
        elif how == "fresh":
            out += ["%s:%d calls tetsu_work.ask without fresh=True" % (rel, ln) for ln, fr in calls if not fr]
    out += ["%s is declared but no longer calls tetsu_work.ask (stale)" % rel for rel in declared if rel not in found]
    return out


# A350 (2026-10-14): every in-tree call that can reach his mail queue and inbox through covenant_free_will's
# defaults, and why it may -- {(path, callee): (how many such calls, why)}. tetsu_update's relay is mail=None, and
# then mail_tell queues in the tree's logs/ and mail_flush sends through the notify config every tree shares; run_round
# passes no mail= of its own. FC8 was such a call from A342 on, in a suite, and nothing said so. A NEW one, here or
# in a file already listed, fails FC11 until someone declares it, and a count with fewer calls left is stale.
MAIL_DECLARED = {
    ("covenant_free_will.py", "tetsu_update"): (1, "production: run_round's own call, after a live round"),
    ("covenant_free_will.py", "mail_tell"): (1, "production: tetsu_update's relay when no mail= is passed"),
    ("covenant_free_will.py", "run_round"): (1, "production: --round --send, the scheduled ambassador round"),
    ("covenant_nightly.py", "run_round"): (1, "production: the nightly's live round (A270)"),
    ("test_fw1_free_will.py", "run_round"): (5, "FW1u: FW.mail_tell and FW.TETSU_UPDATES are replaced around them"),
    ("test_fw1_free_will.py", "mail_tell"): (1, "FW1o: the default notify on purpose, covenant_notify's load, push "
                                                "and send replaced"),
    ("test_fw1_free_will.py", "mail_flush"): (1, "FW1o: the same"),
}
# what each callee must be handed so that it cannot reach the defaults; run_round is read for tetsu_updates instead
MAIL_NEEDS = {"tetsu_update": ("mail",), "mail_tell": ("queue", "notify"), "mail_flush": ("queue", "notify")}
_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)


def _in_scope(scope):
    """The nodes of one scope, not descending into the functions and classes defined in it."""
    todo = list(ast.iter_child_nodes(scope))
    while todo:
        n = todo.pop()
        yield n
        if not isinstance(n, _SCOPES):
            todo.extend(ast.iter_child_nodes(n))


def _bindings(scope):
    """(name -> [values of its plain `name = ...` assignments], names bound any other way, in this scope)."""
    plain, assigns, other = set(), {}, set()
    if isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
        a = scope.args
        other |= {p.arg for p in a.posonlyargs + a.args + a.kwonlyargs + [x for x in (a.vararg, a.kwarg) if x]}
    nodes = list(_in_scope(scope))
    for n in nodes:
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    plain.add(id(t))
                    assigns.setdefault(t.id, []).append(n.value)
    for n in nodes:
        if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)) and id(n) not in plain:
            other.add(n.id)
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            other.add(n.name)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            other |= {(a.asname or a.name).split(".")[0] for a in n.names}
    return assigns, other


def _mutated(tree):
    """Names changed after they were built, anywhere in the file: x[k] = ..., del x[k], x.update(...) and the like.
    A ** of one of them cannot be read statically."""
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Subscript) and isinstance(n.ctx, (ast.Store, ast.Del)) and isinstance(n.value, ast.Name):
            out.add(n.value.id)
        elif (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name)
              and n.func.attr in ("update", "setdefault", "pop", "popitem", "clear", "__setitem__")):
            out.add(n.func.value.id)
    return out


def _shapes(expr, chain, mutated, depth=0):
    """The keywords a ** argument can carry, read statically: [{key: value node}], one per way it can be built,
    or None when it cannot be read (a name bound otherwise, changed after it was built, or anything else)."""
    if depth > 12:
        return None
    out = [{}]

    def add(sub):
        return None if sub is None else [dict(o, **s) for o in out for s in sub]
    if isinstance(expr, ast.Dict):
        for k, v in zip(expr.keys, expr.values):
            if k is None:
                out = add(_shapes(v, chain, mutated, depth + 1))
            elif isinstance(k, ast.Constant) and isinstance(k.value, str):
                out = [dict(o, **{k.value: v}) for o in out]
            else:
                return None
            if out is None:
                return None
        return out
    if isinstance(expr, ast.Call) and isinstance(expr.func, ast.Name) and expr.func.id == "dict":
        for a in expr.args:
            out = add(_shapes(a, chain, mutated, depth + 1))
            if out is None:
                return None
        for k in expr.keywords:
            out = add(_shapes(k.value, chain, mutated, depth + 1)) if k.arg is None else \
                [dict(o, **{k.arg: k.value}) for o in out]
            if out is None:
                return None
        return out
    if isinstance(expr, ast.Name) and expr.id not in mutated:
        for i in range(len(chain) - 1, -1, -1):
            if isinstance(chain[i][0], ast.ClassDef) and i != len(chain) - 1:
                continue                            # a class body's names are not seen from its methods
            assigns, other = chain[i][1]
            if expr.id in other:
                return None
            if expr.id in assigns:
                got = []
                for v in assigns[expr.id]:
                    sub = _shapes(v, chain[:i + 1], mutated, depth + 1)
                    if sub is None:
                        return None
                    got += sub
                return got
    return None


def _callee(fn, names, alias=None):
    """The name in `names` a call's function is: f(...), M.f(...), (x or f)(...), (f if c else g)(...), or a name
    `alias` maps to one (`from covenant_free_will import f as g`, `g = M.f`)."""
    if isinstance(fn, ast.Name) and fn.id in names:
        return fn.id
    if isinstance(fn, ast.Name) and alias and fn.id in alias:
        return alias[fn.id]
    if isinstance(fn, ast.Attribute) and fn.attr in names:
        return fn.attr
    for alt in (fn.values if isinstance(fn, ast.BoolOp) else (fn.body, fn.orelse) if isinstance(fn, ast.IfExp) else ()):
        got = _callee(alt, names, alias)
        if got:
            return got
    return None


def _aliases(tree, names):
    """{other name: callee} for the file: `from covenant_free_will import f as g`, and `g = M.f` (or `g = f`) anywhere
    in it. Read for the whole file, not by scope: a reused name reads as the callee, which can only add a call."""
    out = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom) and (n.module or "").split(".")[-1] == "covenant_free_will":
            out.update({a.asname: a.name for a in n.names if a.asname and a.name in names})
        elif isinstance(n, ast.Assign) and isinstance(n.value, (ast.Name, ast.Attribute, ast.BoolOp, ast.IfExp)):
            got = _callee(n.value, names)
            if got:
                out.update({t.id: got for t in n.targets if isinstance(t, ast.Name) and t.id not in names})
    return out


def _is_off(v):
    return isinstance(v, ast.Constant) and v.value in (None, False, 0)


def mail_sites(root, params):
    """[(relative path, callee, line, why)] for every call under root, tests included, that can reach the mail
    queue and the notify config through the defaults -- found by parsing, not by a name list. `params` is each
    callee's parameter names, read from covenant_free_will's own signatures. Pruned as FC10's walker is (A267).
    A file that names one of the callees and cannot be read or parsed is a site too, callee "?": unread is not
    passed (FC10's walker skips such a file; this one may not)."""
    names = set(MAIL_NEEDS) | {"run_round"}
    found = []
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in PRUNE and not x.startswith("pending-")]
        for f in files:
            if not f.endswith(".py"):
                continue
            p = os.path.join(d, f)
            rel = os.path.relpath(p, root).replace("\\", "/")
            try:
                src = open(p, "rb").read().decode("utf-8", "replace")
            except OSError as e:
                found.append((rel, "?", 0, "cannot be read: %s" % type(e).__name__))
                continue
            if not any(n in src for n in names):          # no such name in the text: no call by it to parse for
                continue
            try:
                tree = ast.parse(src)
            except (SyntaxError, ValueError) as e:
                found.append((rel, "?", 0, "cannot be parsed: %s" % type(e).__name__))
                continue
            mutated, alias = _mutated(tree), _aliases(tree, names)
            todo = [(tree, [])]
            while todo:
                scope, outer = todo.pop()
                chain = outer + [(scope, _bindings(scope))]
                for n in _in_scope(scope):
                    if isinstance(n, _SCOPES):
                        todo.append((n, chain))
                    if not isinstance(n, ast.Call):
                        continue
                    name = _callee(n.func, names, alias)
                    if not name:
                        continue
                    pos = params.get(name, [])
                    starred = any(isinstance(a, ast.Starred) for a in n.args)
                    given = {pos[i]: a for i, a in enumerate(n.args) if i < len(pos) and not starred}
                    given.update({k.arg: k.value for k in n.keywords if k.arg})
                    shapes = [{}]
                    for k in n.keywords:
                        if k.arg is None:
                            sub = _shapes(k.value, chain, mutated)
                            shapes = (None if (sub is None or shapes is None)
                                      else [dict(s, **t) for s in shapes for t in sub])
                    if name == "run_round":
                        if starred or shapes is None:
                            found.append((rel, name, n.lineno, "a * or ** argument that cannot be read"))
                        elif (("tetsu_updates" in given and not _is_off(given["tetsu_updates"]))
                              or any("tetsu_updates" in s and not _is_off(s["tetsu_updates"]) for s in shapes)):
                            found.append((rel, name, n.lineno, "tetsu_updates on"))
                        continue
                    lack = [q for q in MAIL_NEEDS[name]
                            if not ((q in given and not _is_off(given[q]))
                                    or (shapes and all(q in s and not _is_off(s[q]) for s in shapes)))]
                    if lack:
                        found.append((rel, name, n.lineno, "no %s" % "/".join(lack)))
    return sorted(found)


def mail_problems(sites, declared):
    """What FC11 refuses: an undeclared call, a declared count the calls do not match, a stale declaration, and a
    file it could not read, which no declaration excuses."""
    by, out = {}, []
    for rel, name, ln, why in sites:
        by.setdefault((rel, name), []).append("%d (%s)" % (ln, why))
    for (rel, name), got in sorted(by.items()):
        want = declared.get((rel, name))
        if name == "?":
            out.append("%s names a call FC11 reads and %s: unread, not passed" % (rel, got[0].split("(", 1)[1][:-1]))
        elif want is None:
            out.append("%s calls %s at %s and is not declared" % (rel, name, ", ".join(got)))
        elif len(got) != want[0]:
            out.append("%s declares %d call(s) of %s and has %d, at %s -- a new one is undeclared, a gone one stale"
                       % (rel, want[0], name, len(got), ", ".join(got)))
    out += ["%s is declared for %s but no such call is left (stale)" % key for key in sorted(declared) if key not in by]
    return out


def _bytes(path):
    """The file's bytes, or None when it is absent."""
    try:
        with open(path, "rb") as fh:
            return fh.read()
    except OSError:
        return None


def _outside(path, root):
    """True when path is not under root (case-folded on Windows)."""
    p, r = os.path.normcase(os.path.abspath(path)), os.path.normcase(os.path.abspath(root))
    try:
        return os.path.commonpath([p, r]) != r
    except ValueError:                              # another drive
        return True


def main():
    print("A284 -- Tetsu's reviews and round updates are read on their own")
    os.environ["COVENANT_MODEL_STUB"] = "1"
    os.environ["COVENANT_TETSU_IMMUNITY"] = tempfile.mktemp(suffix="_a284_no_immunity.json")
    os.environ["COVENANT_TETSU_IMMUNITY_LEDGER"] = tempfile.mktemp(suffix="_a284_immunity.jsonl")
    os.environ["COVENANT_PAUSE_DIR"] = tempfile.mkdtemp(prefix="a284_pause_")
    d = tempfile.mkdtemp(prefix="a284_")
    LOG = os.environ["COVENANT_ASK_LOG"] = os.path.join(d, "ask_log.jsonl")
    QUEUE = os.environ["COVENANT_TEACHER_QUEUE"] = os.path.join(d, "teacher_queue.jsonl")
    # A350: the tree's own mail queue, as covenant_free_will resolves it here, read before anything runs (FC8b);
    # then this suite's own, in the module and for any child it starts, so a call that forgets its relay queues
    # nothing in the tree (FC8c).
    import covenant_free_will as FW
    tree_queue = FW.MAIL_QUEUE
    queue_before = _bytes(tree_queue)
    FW.MAIL_QUEUE = os.environ["COVENANT_MAIL_QUEUE"] = os.path.join(d, "moltbook_mail_queue.jsonl")
    import covenant_model as M
    import covenant_unified_v8 as cov

    def rows():
        try:
            return [json.loads(l) for l in open(LOG, encoding="utf-8") if l.strip()]
        except OSError:
            return []

    # ---- FC1: agent_history ---------------------------------------------------------------
    with open(LOG, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"kind": "agent", "from": CALLER, "text": "OLD-Q", "answer": "OLD-A"}) + "\n")
        fh.write(json.dumps({"kind": "agent", "from": CALLER, "text": "REVIEW-Q", "answer": "SEND it", "fresh": True}) + "\n")
        fh.write(json.dumps({"kind": "council", "from": CALLER, "text": "NEW-Q", "answer": "NEW-A"}) + "\n")
    h = cov.agent_history(LOG, CALLER, budget=None)
    check("FC1 agent_history skips the fresh row and keeps the ordinary turns on either side of it",
          [m["content"] for m in h] == ["OLD-Q", "OLD-A", "NEW-Q", "NEW-A"], [m["content"] for m in h])

    # ---- FC2-FC5: the real /m/agent ---------------------------------------------------------
    m = cov.CovenantUnifiedMaster("A284", host="127.0.0.1", port=5441, p2p_port=5442,
                                  db_path=tempfile.mktemp(suffix="_a284.db"))
    m.add_genesis_block()
    real_sentinel = cov.ReasoningSentinel(cov.MockJudge(), cov.DIVINE_PRINCIPLES)
    judged = []

    class Counting:
        """The real sentinel, counted: proves a fresh ask's answer is still judged."""
        def __init__(self, inner, refuse=False):
            self.inner, self.refuse = inner, refuse

        def evaluate_transaction(self, tx):
            judged.append((tx.data or {}).get("origin"))
            if self.refuse and (tx.data or {}).get("origin") == "model":
                return False, "refused by this suite's stand-in judge", 0.0, None
            return self.inner.evaluate_transaction(tx)

        def __getattr__(self, k):
            return getattr(self.inner, k)

    m.node.sentinel = Counting(real_sentinel)
    client = m.api.app.test_client()
    sent = []

    def recorder(messages, max_tokens=700, **_k):
        sent.append(json.loads(json.dumps(messages)))
        return "an answer from the recorder", {"model": "recorder", "tokens": 1, "ms": 1}

    real_ask = M.ask
    try:
        M.ask = recorder
        sent.clear()
        r = client.post("/m/agent", json={"text": "REVIEW THIS DRAFT", "fresh": True}, environ_base={"REMOTE_ADDR": CALLER})
        j = r.get_json() or {}
        msgs = sent[0] if sent else []
        check("FC2 a fresh ask from a caller with history: the model is handed the rules and the question only",
              r.status_code == 200 and len(sent) == 1 and [x["role"] for x in msgs] == ["system", "user"]
              and msgs[-1]["content"] == "REVIEW THIS DRAFT", (r.status_code, [x["role"] for x in msgs]))
        row = [x for x in rows() if x.get("text") == "REVIEW THIS DRAFT"]
        check("FC2 ...the reply says fresh, and so does its ask-log row",
              j.get("fresh") is True and len(row) == 1 and row[0].get("fresh") is True and row[0].get("answer"),
              (j.get("fresh"), row))

        sent.clear()
        r = client.post("/m/agent", json={"text": "AN ORDINARY ASK"}, environ_base={"REMOTE_ADDR": CALLER})
        j = r.get_json() or {}
        contents = [x["content"] for x in (sent[0] if sent else [])][1:-1]
        check("FC3 the next ordinary ask replays the caller's earlier turns and never the fresh exchange",
              r.status_code == 200 and contents == ["OLD-Q", "OLD-A", "NEW-Q", "NEW-A"] and "fresh" not in j,
              contents)

        got = {}
        for v in ("true", 1, "yes"):
            sent.clear()
            r = client.post("/m/agent", json={"text": "NEAR-FRESH %r" % (v,), "fresh": v}, environ_base={"REMOTE_ADDR": CALLER})
            got[repr(v)] = (len(sent[0]) - 2 if sent else None, (r.get_json() or {}).get("fresh"))
        check("FC4 only JSON true is fresh: \"true\", 1 and \"yes\" replay history and the reply does not say fresh %s" % got,
              all(n and n > 0 and f is None for n, f in got.values()), got)

        judged.clear()
        m.node.sentinel = Counting(real_sentinel, refuse=True)
        sent.clear()
        r = client.post("/m/agent", json={"text": "A FRESH ASK THE JUDGE REFUSES", "fresh": True},
                        environ_base={"REMOTE_ADDR": CALLER})
        j = r.get_json() or {}
        check("FC5 a fresh ask's answer is still judged, and withheld when refused",
              r.status_code == 200 and "model" in judged and j.get("withheld") is True and j.get("answer") == ""
              and j.get("fresh") is True, (judged, j.get("withheld"), j.get("answer")))
        m.node.sentinel = Counting(real_sentinel)
        q = [json.loads(l) for l in open(QUEUE, encoding="utf-8")] if os.path.exists(QUEUE) else []
        mine = [x for x in q if x.get("text") == "REVIEW THIS DRAFT"]
        check("FC5 ...and an admitted fresh exchange still reaches the teacher queue, not marked private",
              len(mine) == 1 and not mine[0].get("private"), mine)
    finally:
        M.ask = real_ask

    # ---- FC6-FC8: the one path reviews and updates use -----------------------------------------
    import covenant_tetsu_assist as TA
    sys.path.insert(0, os.path.join(HERE, "tools"))
    from tools import tetsu_work as TWpkg
    calls = []
    reply = [{"status": "success", "answer": "SEND it is honest", "fresh": True}]

    def stand_in(text, door="agent", host="127.0.0.1", port=5000, timeout=600, private=False, fresh=False):
        calls.append({"fresh": fresh, "private": private, "text": text})
        return 200, dict(reply[0])

    real_tw = TWpkg.ask
    grant = os.path.join(d, "grant.json")
    with open(grant, "w", encoding="utf-8") as fh:
        json.dump({"granted": True, "reviews_per_run": 6}, fh)
    try:
        TWpkg.ask = stand_in
        got = TA._default_ask("a prompt")
        check("FC6 _default_ask asks with fresh=True, not private, and returns the answer the door confirmed",
              got == "SEND it is honest" and calls and calls[-1]["fresh"] is True and calls[-1]["private"] is False,
              (got, calls[-1:]))

        reply[0] = {"status": "success", "answer": "SEND it is honest"}          # a core older than A284
        raised = None
        try:
            TA._default_ask("a prompt")
        except RuntimeError as e:
            raised = str(e)
        TA._used["n"] = 0
        v = TA.review("a held draft", "students held it", dry_run=False, grant_path=grant,
                      log_path=os.path.join(d, "assist.jsonl"), teach=False)
        check("FC7 a door that does not confirm fresh: _default_ask raises, and review() keeps the hold (NONE)",
              raised and "A284" in raised and v.get("decision") == "NONE" and "A284" in v.get("why", ""), (raised, v))

        reply[0] = {"status": "success", "answer": "TELL: someone wrote back", "fresh": True}
        calls.clear()
        told, mailed = [], []
        # A350: the relay is this suite's own. Without mail= the TELL was queued in the tree and handed to his notify
        # config on every run (A342 added the relay; FW1u replaced it, this call did not).
        u = FW.tetsu_update({"replied": 1}, [], (), tell=lambda *a: told.append(a) or True,
                            log_path=os.path.join(d, "updates.jsonl"),
                            mail=lambda text, rows: mailed.append((text, rows)) or (0, 0))
        check("FC8 tetsu_update's default ask is the same fresh path, and its decision is read as before; its TELL "
              "went to this suite's own relay, once",
              u and u.get("decision") == "TELL" and told and calls and all(c["fresh"] is True for c in calls)
              and mailed == [("someone wrote back", [])], (u, calls, mailed))
    finally:
        TWpkg.ask = real_tw
    import covenant_notify as N
    import subprocess
    # a child that imports covenant_free_will afresh reads both overrides from the environment it inherits
    child = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, %r); import covenant_free_will as F; "
                            "print(F.MAIL_QUEUE); print(F.TETSU_UPDATES)" % HERE],
                           capture_output=True, text=True, timeout=120)
    own_updates = os.path.join(OWN, "tetsu_moltbook_updates.jsonl")
    check("FC8c the mail queue, the update log and the notify config this suite's code reads are its own: the queue "
          "and the log temp files outside the tree, in this process and in a child that imports covenant_free_will "
          "afresh; the config this suite's path, outside the tree, never created, nothing loaded (A350)",
          FW.MAIL_QUEUE != tree_queue and _outside(FW.MAIL_QUEUE, HERE)
          and FW.TETSU_UPDATES == own_updates and _outside(FW.TETSU_UPDATES, HERE)
          and child.stdout.splitlines()[:2] == [FW.MAIL_QUEUE, own_updates]
          and N.CONFIG == NOTIFY_NONE and _outside(N.CONFIG, HERE) and not os.path.exists(N.CONFIG) and N.load() == {},
          (FW.MAIL_QUEUE, FW.TETSU_UPDATES, child.stdout.splitlines()[:2], child.stderr[-200:], N.CONFIG,
           os.path.exists(N.CONFIG)))

    # ---- FC9: tools/tetsu_work.ask over a real socket -------------------------------------------
    seen = []

    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            n = int(self.headers.get("Content-Length", "0") or 0)
            seen.append((self.client_address[0], json.loads(self.rfile.read(n).decode("utf-8"))))
            out = json.dumps({"status": "success", "answer": "ok"}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)

        def log_message(self, *_a):
            pass

    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        port = srv.server_address[1]
        TWpkg.ask("with fresh", port=port, timeout=10, fresh=True)
        TWpkg.ask("without", port=port, timeout=10)
    finally:
        srv.shutdown()
    bodies = {b.get("text"): (a, b) for a, b in seen}
    check("FC9 tools/tetsu_work.ask: \"fresh\": true in the body when asked, absent otherwise, from %s" % TWpkg.SOURCE,
          bodies.get("with fresh", (None, {}))[1].get("fresh") is True and "fresh" not in bodies.get("without", (None, {"fresh": 1}))[1]
          and all(a == TWpkg.SOURCE for a, _b in seen) and len(seen) == 2, seen)

    # ---- FC10: every caller of tetsu_work.ask is declared --------------------------------------
    found = tetsu_work_callers(HERE)
    probs = guard_problems(found, DECLARED)
    check("FC10 every in-tree caller of tools/tetsu_work.ask is declared, and the fresh ones pass fresh=True %s"
          % {k: [c[0] for c in v] for k, v in found.items()}, not probs and found, probs or found)
    probe = tempfile.mkdtemp(prefix="a284_probe_")
    with open(os.path.join(probe, "covenant_new_judge.py"), "w", encoding="utf-8") as fh:
        fh.write("from tools import tetsu_work as T\n\ndef judge(x):\n    return T.ask(x)\n")
    os.makedirs(os.path.join(probe, "tools"))
    with open(os.path.join(probe, "covenant_tetsu_assist.py"), "w", encoding="utf-8") as fh:
        fh.write("from tools import tetsu_work as TW\n\ndef _default_ask(p):\n    return TW.ask(p, timeout=600)\n")
    pf = tetsu_work_callers(probe)
    pp = guard_problems(pf, {"covenant_tetsu_assist.py": "fresh", "gone.py": "shared"})
    check("FC10n the same walker over a synthetic tree flags an undeclared caller, a fresh caller without "
          "fresh=True, and a stale declaration (%d)" % len(pp),
          len(pp) == 3 and any("covenant_new_judge.py" in p and "not declared" in p for p in pp)
          and any("without fresh=True" in p for p in pp) and any("stale" in p for p in pp), pp)

    # ---- FC11: every call that can reach his mail queue and inbox is declared (A350) ---------------------------
    # WHAT FC11 CANNOT SEE (rule 9; its verifiers defeated it with each of these, 2026-10-15). It is a static walk
    # that guards ACCIDENTAL reintroduction, not adversarial code: the default handed back explicitly
    # (mail=FW.mail_tell, queue=FW.MAIL_QUEUE), a falsy relay (mail='', or a name bound to None), a wrapper that
    # forwards its own None-defaulted mail/queue/notify, tuple or walrus aliases, getattr, functools.partial,
    # dict dispatch, exec/importlib, a global rebound in another function, dict.update or setitem through an
    # alias, and .pyw files. The runtime defences are the suite redirects (FC8c, FW1A350a-c) and the staged
    # runners' notify isolation (SC6), which held on every route the verifiers drove.
    import inspect
    params = {n: list(inspect.signature(getattr(FW, n)).parameters) for n in list(MAIL_NEEDS) + ["run_round"]}
    sites = mail_sites(HERE, params)
    probs = mail_problems(sites, MAIL_DECLARED)
    shown = {}
    for rel, name, ln, _why in sites:
        shown.setdefault("%s %s" % (rel, name), []).append(ln)
    check("FC11 every in-tree call its static walk can see reaching his mail queue and inbox through the defaults is "
          "declared (what it cannot see is named above), as many "
          "as there are %s" % shown, not probs and sites, probs or sites)
    probe = tempfile.mkdtemp(prefix="a284_mail_probe_")
    with open(os.path.join(probe, "covenant_new_relay.py"), "w", encoding="utf-8") as fh:
        fh.write("import covenant_free_will as FW\n\n\n"
                 "def tell_him(out):\n    return FW.tetsu_update(out, [], ())\n\n\n"
                 "def flush():\n    return FW.mail_flush(queue='q.jsonl')\n\n\n"
                 "def round_with_updates():\n    k = dict(dry_run=False, tetsu_updates=True)\n"
                 "    return FW.run_round(**dict(k, say=print))\n\n\n"
                 "def from_caller(kw):\n    return FW.run_round(**kw)\n\n\n"
                 "def from_elsewhere():\n    return FW.run_round(**settings())\n\n\n"
                 "def kept_off(out):\n    FW.tetsu_update(out, [], (), mail=lambda *a: None)\n"
                 "    FW.mail_tell('t', [], 'q.jsonl', lambda s, b: {})\n    base = {'dry_run': False}\n"
                 "    return FW.run_round(**base)\n")
    with open(os.path.join(probe, "covenant_new_alias.py"), "w", encoding="utf-8") as fh:
        fh.write("from covenant_free_will import tetsu_update as tu\nimport covenant_free_will as FW\n\n"
                 "relay = FW.mail_tell\nkw = dict(dry_run=False, tetsu_updates=True)\n\n\n"
                 "def via_alias(out):\n    tu(out, [], ())\n    return relay('t', [])\n\n\n"
                 "class Round:\n    kw = {'tetsu_updates': False}\n\n"
                 "    def go(self):\n        return FW.run_round(**kw)\n\n"
                 "    def off(self):\n        return FW.run_round(dry_run=False, tetsu_updates=False)\n")
    with open(os.path.join(probe, "covenant_broken_relay.py"), "w", encoding="utf-8") as fh:
        fh.write("def flush(:\n    FW.mail_flush()\n")
    ps = mail_sites(probe, params)
    pp = mail_problems(ps, {("covenant_new_relay.py", "mail_flush"): (2, "x"),
                            ("gone.py", "run_round"): (1, "x")})
    unread = "a * or ** argument that cannot be read"
    check("FC11n the same walker over a synthetic tree finds the eight calls that can reach the defaults (through ** of "
          "a dict built from a dict, a ** it cannot read, an import alias, a name bound to the function, and a module "
          "dict a method's class body does not shadow), none of the four kept off them, and a file it cannot parse; "
          "and flags undeclared calls, a miscount, a stale declaration and the unparsed file (%d)" % len(pp),
          ps == [("covenant_broken_relay.py", "?", 0, "cannot be parsed: SyntaxError"),
                 ("covenant_new_alias.py", "mail_tell", 10, "no queue/notify"),
                 ("covenant_new_alias.py", "run_round", 17, "tetsu_updates on"),
                 ("covenant_new_alias.py", "tetsu_update", 9, "no mail"),
                 ("covenant_new_relay.py", "mail_flush", 9, "no notify"),
                 ("covenant_new_relay.py", "run_round", 14, "tetsu_updates on"),
                 ("covenant_new_relay.py", "run_round", 18, unread), ("covenant_new_relay.py", "run_round", 22, unread),
                 ("covenant_new_relay.py", "tetsu_update", 5, "no mail")]
          and len(pp) == 8 and sum("not declared" in p for p in pp) == 5
          and any(p.startswith("covenant_broken_relay.py") and "unread, not passed" in p for p in pp)
          and any("declares 2 call(s) of mail_flush and has 1" in p for p in pp)
          and any(p.startswith("gone.py") and "stale" in p for p in pp), (ps, pp))

    # ---- FC8b: after the whole suite, the tree's own mail queue is as it was (A350) ------------------------------
    check("FC8b the tree's own mail queue (%s) is byte-identical after the whole suite, or still absent (A350: FC8 "
          "queued a fake letter there on every run from A342 on)" % os.path.relpath(tree_queue, HERE),
          not _outside(tree_queue, HERE) and _bytes(tree_queue) == queue_before,
          (tree_queue, None if queue_before is None else len(queue_before),
           None if _bytes(tree_queue) is None else len(_bytes(tree_queue))))

    ok = sum(results)
    print("\nA284: %d/%d passed" % (ok, len(results)))
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
