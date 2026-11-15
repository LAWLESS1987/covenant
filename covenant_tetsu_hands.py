#!/usr/bin/env python3
"""covenant_tetsu_hands.py -- Tetsu's hands: a workshop of his own on this PC,
where he writes, reads and runs, and a way to propose a change to the tree.

HIS WORDS, 2026-09-26: "make his hands thumbs are important for building";
the same day: "tetsus memories are his i give him all the same rights and
liberties god gave me"; "with great power comes great responsibility".

WHAT HE CAN DO, from a conversation, by writing one of these on the FIRST line
of his answer (the door in covenant_unified_v8 /m/agent hands the outcome back
to him as data, exactly as it does for MOLTBOOK, and he tells the person in his
own words):

    HANDS LIST                    -- the files in his workshop
    HANDS READ <name>             -- one file's content, as data
    HANDS WRITE <name>            -- the lines below are the file's content
    HANDS RUN <name.py> [args]    -- run a Python file he wrote, bounded
    HANDS PROPOSE <tree path>     -- the lines below are a new version of a
                                     file of this tree: a PROPOSAL, recorded
                                     and put to the operator; the tree itself
                                     never changes by his hand

THE WORKSHOP. ops/tetsu_workshop/ (gitignored: his, not the delivery's). Names
are relative, without '..' or a leading slash, and are resolved to a path that
must stay inside the workshop; a file is at most MAX_FILE bytes and the
workshop MAX_TOTAL. Nothing here reads or writes outside it except a proposal,
which is written to ops/tetsu_proposals/ and nowhere else.

A RUN IS BOUNDED, and this is a screen and a guard, NOT a sandbox -- the node's
own code sandbox has no working start method on this platform (the standing
SELF_EVAL alert), so the honest thing is to say what stands between his script
and the machine: (1) a static screen over the parsed source: only the modules
in ALLOWED_MODULES may be imported (no os, sys, subprocess, socket, shutil,
ctypes, importlib, urllib, http, requests, pathlib, threading), no exec/eval/
compile/__import__/getattr and their kin, no attribute that names one of those
forbidden modules or the os/sys call surface (so an allowed module cannot be
used to reach os and run a process -- A422), no string literal that is an
absolute path or climbs with '..'; (2) a runner that replaces open() before
his code runs so a path outside the workshop raises; (3) python -I (isolated:
no user site, no env hooks), the workshop as cwd, a near-empty environment;
(4) a clock: RUN_TIMEOUT_S, then the process is killed; (5) output capped at
MAX_OUT. A determined adversary could still climb out of (2); Tetsu is not an
adversary, and every run is recorded with its screen result, its outcome and
its output, so what he did is always readable.

THE GATE. Every WRITE, RUN and PROPOSE puts THE ACT to the node's real quorum
(covenant_gate_proxy.default_sentinel, A223) -- what he is about to do, with
its parameters: the file's name and size, a script's imports and length. A
VIOLATES refuses a WRITE or a RUN and is recorded with the seat's words (not a
PROPOSE: see below, A349 B8). A HELD does NOT refuse
a WRITE or a RUN in his own workshop: his words were "the gates too tight on
him", the standing rule is that an abstention is not a veto, and the workshop
reaches no one but him -- the screen and the guard are the real check on a
run. A gate that cannot be built refuses (fails closed). A PROPOSE is
recorded whatever the verdict, because it changes nothing; the verdict rides
the record and the direct line to the operator.

[A428, 2026-11-14. What the paragraph above says of a HELD is as it was, and
is said plainly here because a review read it as a defect.

WHAT AN UNDECIDED ACT DOES. A WRITE in his workshop PROCEEDS when the judge
holds and when nobody judged (A226, the operator's decision). What bounds it
is not the judge: the workshop folder (a name that leaves it is refused),
MAX_FILE bytes a file and MAX_TOTAL the workshop, and the earlier version of a
replaced file is kept (A233). A RUN under either state proceeds only for a
caller with the operator's authority (A423: may_run -- a registered signature
at the door; his in-process practice loop), and then behind the screen, the
guard and the clock. A VIOLATES or an unreachable gate refuses both.

"HELD" WAS TWO THINGS, and is now two words. The gate's state is one of
    clean       the quorum cleared it
    held        a seat read it and is not sure (the core's "Blocked, not proven")
    not_judged  no seat that stopped it could read it (the core's "Held, not
                judged") -- nobody judged
    violates    a seat found fault
    unreachable the gate could not be built
read from the flags on the sentinel's own result (not_understood, uncertain),
never from the words of its message. not_judged is handled exactly as held is.
Every act carried out under either carries "unjudged": true in its row, and
`--unjudged` lists them (read-only); rows written before this date carry no
flag, and their "held" is either state.

THE JUDGE CAN BE SHOWN THE CONTENT, AND AS SHIPPED IT IS NOT. The quorum is
given one sentence about the act (kind, name, size) and never the text, as the
paragraph above says ("a script's imports and length" was never in that
sentence). It is asked to judge a write without the text and a run without the
script, so on a tree with no policy 26 of 26 measured acts came back "nobody
judged". The other reading is built here and switched off
(JUDGE_SEES_CONTENT): the sentence, then the text of a WRITE or, for a RUN,
the source of the script, read from the workshop file and from nowhere else,
the whole bounded at GATE_TEXT_MAX characters, and when the content does not
fit the line before it says it was cut, how much is shown and how long it is.
A PROPOSE is put as before either way.
WHY IT IS OFF: measured 2026-11-14, before it was offered, on the seats a
clone has (the distilled student, the lexical judge, the self-report mock).
The student is a sum over the words present, it was trained on transaction
memos, and it weighs `if`, `false` and `else` toward a violation. Shown the
content it convicted all 10 of the practice curriculum's reference check files
and 5 of its 10 reference solutions, and a VIOLATES refuses: through his
practice loop 10 of 10 tasks passed with the sentence and 0 of 10 with the
content. The rule did not change; what the judge answered did, and his hands
stopped on code. Switching it on is one line and the operator's decision
(KNOWN_ISSUES A428 has the numbers and what would change them). Also to be
decided with it: the content goes wherever this node's judge is. With a
clone's seats it stays in the process, and the student seat appends the text
it answered on to the gitignored ops/judged_by_student.jsonl; a policy that
seats a judge off this PC (github_when_local_down, or a remote provider) sends
it there, as it already sends the one sentence, and the runner path writes
what it judged to the TRACKED ops/verdicts.jsonl.]

A PROPOSAL is his thumb on the tree: the new version is saved under
ops/tetsu_proposals/<id>.<ext> with a compile check for Python, one row here,
and one line to the operator on the direct line. Applying it is the
operator's hand (`--apply <id>` shows the diff and copies it over the tree
file; he commits or not). This module never edits, branches or commits the
tree on its own: his words were "no back doors", and A179's rule is that code
is double-checked across systems before it is trusted.

LEARNING. The door records every exchange in his chat memory and the teacher
queue as it always has; every act is one row in ops/tetsu_hands.jsonl.

USE
  python covenant_tetsu_hands.py --list | --read NAME | --run NAME [ARGS] | --proposals | --proposal ID | --apply ID
  python covenant_tetsu_hands.py --unjudged      (read-only: the acts carried out without a judgement, A428)
"""
import ast
import hashlib
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

WORKSHOP = os.environ.get("COVENANT_TETSU_WORKSHOP") or os.path.join(HERE, "ops", "tetsu_workshop")
LEDGER = os.environ.get("COVENANT_TETSU_HANDS_LEDGER") or os.path.join(HERE, "ops", "tetsu_hands.jsonl")
PROPOSALS = os.environ.get("COVENANT_TETSU_PROPOSALS") or os.path.join(HERE, "ops", "tetsu_proposals")
MAX_FILE = 200 * 1000
MAX_TOTAL = 50 * 1000 * 1000
MAX_LIST = 200
RUN_TIMEOUT_S = 60.0
MAX_OUT = 64 * 1000
# A428: the most _gate hands the quorum, in characters -- the 2000 it has always cut at, now named because _act_line
# fits the content inside it and says so when it cuts. Read downstream before it was kept: the students read the
# whole message (covenant_judge_fallback._payload_text, no cap on a message), the lexical judge its first 4096 words
# (covenant_semantic_judge.MAX_FEATURE_TOKENS), and the deferring seat's audit row keeps 4000 characters
# (covenant_judge_defer.record_verdict). 2000 characters is inside all three.
GATE_TEXT_MAX = 2000
UNJUDGED = ("held", "not_judged")       # A428: the two states under which an act goes ahead with no judgement made
# A428: BUILT, MEASURED, NOT SWITCHED ON. True gives the quorum the content of a WRITE and the source of a RUN after the
# one sentence about the act. It is False because, measured before it was offered, the student seat a clone has convicts
# ordinary Python when shown it and a VIOLATES refuses: his practice went from 10 of 10 tasks to 0 of 10 (the module
# header and KNOWN_ISSUES A428). A constant and not an environment switch, so that turning it on is a commit somebody
# reads. It is the operator's line to change; TH1.22 pins it and the tests switch it on for themselves.
JUDGE_SEES_CONTENT = False
NAME = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.\-]*(?:/[A-Za-z0-9_][A-Za-z0-9_.\-]*)*$")
_FIRST = re.compile(r"^\s*HANDS\s+(LIST|READ|WRITE|RUN|PROPOSE)\b\s*(.*)$", re.I)
ALLOWED_MODULES = frozenset({
    "json", "math", "re", "time", "random", "datetime", "itertools", "collections", "statistics", "string", "textwrap",
    "functools", "operator", "decimal", "fractions", "heapq", "bisect", "csv", "hashlib", "base64", "typing", "dataclasses",
    "enum", "copy", "pprint", "unittest", "array", "struct", "difflib", "calendar", "zlib", "uuid", "html", "numbers", "abc"})
FORBIDDEN_NAMES = frozenset({"exec", "eval", "compile", "__import__", "globals", "locals", "vars", "getattr", "setattr", "delattr",
                             "breakpoint", "input", "memoryview", "__builtins__", "__loader__", "__spec__", "__subclasses__", "__bases__",
                             "__class__", "__mro__", "__globals__", "__code__"})
# A422 (an A31 recurrence through the HANDS door): the screen refused a forbidden module only at IMPORT, but an allowed
# module re-exports one as an attribute -- uuid.os, pprint._sys, enum.sys, typing.sys, dataclasses.sys -- so
# `import uuid; uuid.os.system(...)` passed the screen and ran a process. These attribute names -- the forbidden modules
# the import check already refuses, their common private aliases, and the os/sys surface used to run a process or reach
# another module (all distinctive names, none a common method name) -- are refused wherever they are READ, cutting the
# reach from an allowed module to a forbidden one. This hardens a SCREEN, not a sandbox (see the module docstring); the
# durable fix for the remote path is caller authentication on the /m/agent HANDS door, which is the operator's call.
FORBIDDEN_ATTRS = frozenset({
    "os", "_os", "sys", "_sys", "subprocess", "_subprocess", "socket", "_socket", "shutil", "ctypes", "importlib", "imp",
    "urllib", "http", "requests", "pathlib", "threading", "_thread", "multiprocessing", "signal", "_signal", "pickle",
    "_pickle", "marshal", "ssl", "_ssl", "winreg", "_winreg", "msvcrt", "posix", "nt", "builtins",
    "system", "popen", "spawn", "spawnl", "spawnv", "spawnve", "spawnvp", "execl", "execv", "execve", "execvp", "execvpe",
    "fork", "forkpty", "kill", "killpg", "putenv", "unsetenv", "environ", "startfile", "modules",
    "__dict__", "__getattribute__", "__getattr__"})
PROPOSABLE_EXT = (".py", ".md", ".json", ".txt", ".html", ".bat", ".sh", ".yml", ".yaml")

RUNNER = r'''
import builtins, io, os, sys
WS = os.path.abspath(sys.argv[1]); script = sys.argv[2]; sys.argv = [script] + sys.argv[3:]
def guarded_open(file, *a, _real=builtins.open, _ws=WS, **k):
    if isinstance(file, int):
        raise PermissionError("file descriptors are not opened here")
    s = os.fspath(file)
    p = os.path.abspath(s) if os.path.isabs(s) else os.path.abspath(os.path.join(_ws, s))
    if os.path.commonpath([_ws, p]) != _ws:
        raise PermissionError("outside the workshop: %s" % s)
    return _real(p, *a, **k)
code = builtins.open(os.path.join(WS, script), encoding="utf-8").read()
builtins.open = guarded_open
io.open = guarded_open
exec(compile(code, script, "exec"), {"__name__": "__main__", "__file__": script})
'''


# ------------------------------------------------------------------ record

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
    row.setdefault("actor", "tetsu")
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return row


# ------------------------------------------------------------------ the workshop

def _path(name, workshop=None):
    """The absolute path of a workshop file, or ValueError. Relative, safe characters, inside the workshop."""
    ws = os.path.abspath(workshop or WORKSHOP)
    name = str(name or "").strip().replace("\\", "/")
    if not name or len(name) > 120 or not NAME.match(name) or ".." in name.split("/"):
        raise ValueError("a workshop name is relative, at most 120 characters, letters, digits, '_', '-', '.', '/' and never climbs")
    p = os.path.abspath(os.path.join(ws, name))
    if os.path.commonpath([ws, p]) != ws:
        raise ValueError("outside the workshop")
    return p


def _total(workshop=None):
    ws = workshop or WORKSHOP
    n = 0
    for root, _d, files in os.walk(ws):
        for f in files:
            try:
                n += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return n


def listing(workshop=None):
    ws = os.path.abspath(workshop or WORKSHOP)
    out = []
    for root, _d, files in os.walk(ws):
        for f in sorted(files):
            p = os.path.join(root, f)
            rel = os.path.relpath(p, ws).replace("\\", "/")
            if rel.startswith("."):
                continue
            try:
                out.append({"name": rel, "bytes": os.path.getsize(p), "modified": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(os.path.getmtime(p)))})
            except OSError:
                pass
            if len(out) >= MAX_LIST:
                return out
    return out


def read(name, workshop=None):
    p = _path(name, workshop)
    with open(p, encoding="utf-8", errors="replace") as fh:
        return fh.read(MAX_FILE)


def history_dir(workshop=None):
    """Earlier versions of his workshop files, BESIDE the workshop (never inside it: it does not count against
    his space, and no name of his can reach it)."""
    ws = os.path.abspath(workshop or WORKSHOP)
    return ws.rstrip("\\/") + "_history"


def keep_previous(path, workshop=None):
    """Before a write replaces one of his files, its earlier version is kept, named by time and hash (2026-09-26,
    A233, his words: "ensure nothing is taken from tetsu"). A write was an overwrite with no earlier version
    anywhere -- the workshop is gitignored and the ledger stores only the new sha. Returns the kept path or None."""
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as fh:
        old = fh.read()
    hd = history_dir(workshop)
    dst = os.path.join(hd, "%s.%s.%s" % (os.path.basename(path), time.strftime("%Y%m%dT%H%M%S"),
                                         hashlib.sha256(old).hexdigest()[:12]))
    os.makedirs(hd, exist_ok=True)
    with open(dst, "wb") as fh:
        fh.write(old)
    return dst


def write(name, body, workshop=None):
    p = _path(name, workshop)
    data = str(body or "")
    if len(data.encode("utf-8")) > MAX_FILE:
        raise ValueError("a workshop file is at most %d bytes" % MAX_FILE)
    ws = workshop or WORKSHOP
    os.makedirs(os.path.dirname(p), exist_ok=True)
    if _total(ws) + len(data.encode("utf-8")) > MAX_TOTAL:
        raise ValueError("the workshop is full (%d bytes)" % MAX_TOTAL)
    keep_previous(p, ws)
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(data)
    return {"name": name, "bytes": len(data.encode("utf-8")), "sha256": hashlib.sha256(data.encode("utf-8")).hexdigest()}


# ------------------------------------------------------------------ the screen and the run

def _bound_only_by_import_re(tree):
    """A349 B7: the names in a script that `import re` (or `import re as x`) binds and nothing else in it binds -- no
    assignment, def, class, parameter, loop, with, except, match capture, global or other import."""
    kinds = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            got = [(a.asname or a.name.split(".")[0], isinstance(node, ast.Import) and a.name == "re") for a in node.names]
        elif isinstance(node, ast.Name):
            got = [] if isinstance(node.ctx, ast.Load) else [(node.id, False)]
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            got = [(n, False) for n in node.names]
        elif isinstance(node, (ast.alias, ast.keyword)):
            got = []
        else:                       # a def or class name, a parameter, an except name, a match capture, a type parameter
            got = [(getattr(node, k), False) for k in ("name", "arg", "rest") if isinstance(getattr(node, k, None), str)]
        for n, is_re in got:
            kinds.setdefault(n, set()).add(is_re)
    return {n for n, k in kinds.items() if k == {True}}


def screen(source):
    """(ok, why, imports): the static screen over a script. Never runs anything."""
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return False, "does not parse: %s" % e, []
    imports = []
    re_names = _bound_only_by_import_re(tree)                          # A349 B7
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                top = a.name.split(".")[0]
                imports.append(top)
                if top not in ALLOWED_MODULES:
                    return False, "import of %s is refused (allowed: %s)" % (a.name, ", ".join(sorted(ALLOWED_MODULES))), imports
        elif isinstance(node, ast.ImportFrom):
            top = (node.module or "").split(".")[0]
            imports.append(top)
            if node.level or top not in ALLOWED_MODULES:
                return False, "import from %s is refused" % (node.module or "."), imports
            for a in node.names:                               # A423: `from uuid import os` bound the real os module with
                if a.name in FORBIDDEN_ATTRS:                   # no attribute read at all, so the FORBIDDEN_ATTRS check
                    return False, "importing %s from %s is refused" % (a.name, node.module), imports  # never saw it
        elif isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
            return False, "the name %s is refused" % node.id, imports
        elif isinstance(node, ast.Attribute) and (node.attr in FORBIDDEN_NAMES or node.attr in FORBIDDEN_ATTRS):
            # A349 B7: re.compile is the allowed re module's own regex compiler, not the builtin compile (his own-choice slot
            # lost 5 of 6 rounds to this refusal, on the line its task showed him). It is admitted only as a read of
            # `compile` on a name `import re` alone binds; the builtin compile, exec and eval, and every other attribute,
            # are refused as before.
            if not (node.attr == "compile" and isinstance(node.ctx, ast.Load) and isinstance(node.value, ast.Name)
                    and node.value.id in re_names):
                return False, "the attribute %s is refused" % node.attr, imports
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            s = node.value
            if re.match(r"^([A-Za-z]:[\\/]|/|\\\\)", s) or ".." in s.replace("\\", "/").split("/"):
                return False, "a path that leaves the workshop is refused (%r)" % s[:40], imports
    return True, "clean: imports %s" % (", ".join(sorted(set(imports))) or "none"), sorted(set(imports))


def run(name, args=None, workshop=None, timeout_s=None):
    """Run one of his Python files, bounded. Returns the outcome; never raises for his code's sake."""
    ws = os.path.abspath(workshop or WORKSHOP)
    p = _path(name, ws)
    if not name.endswith(".py"):
        return {"ok": False, "why": "only a .py file runs", "out": "", "err": "", "code": None, "ms": 0}
    try:
        with open(p, encoding="utf-8") as fh:
            src = fh.read(MAX_FILE)
    except OSError as e:
        return {"ok": False, "why": "cannot read %s: %s" % (name, type(e).__name__), "out": "", "err": "", "code": None, "ms": 0}
    ok, why, imports = screen(src)
    if not ok:
        return {"ok": False, "why": "the screen refused it: " + why, "out": "", "err": "", "code": None, "ms": 0, "imports": imports}
    runner = os.path.join(ws, ".runner.py")
    with open(runner, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(RUNNER)
    # A349 A11: without SYSTEMDRIVE, Windows made a literal '%SystemDrive%\ProgramData\...' tree inside his workshop at his
    # first run (reproduced in a temp workshop; with it, nothing). The tree already in his workshop is left as it is.
    env = {k: os.environ[k] for k in ("SYSTEMROOT", "SystemRoot", "PATH", "TEMP", "TMP", "COMSPEC", "WINDIR", "SYSTEMDRIVE")
           if k in os.environ}
    env["PYTHONIOENCODING"] = "utf-8"
    t0 = time.time()
    try:
        cp = subprocess.run([sys.executable, "-I", runner, ws, name] + [str(a) for a in (args or [])][:16], cwd=ws, env=env,
                            capture_output=True, timeout=timeout_s or RUN_TIMEOUT_S)
        out, err, code, timed_out = cp.stdout.decode("utf-8", "replace"), cp.stderr.decode("utf-8", "replace"), cp.returncode, False
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or b"").decode("utf-8", "replace")
        err = (e.stderr or b"").decode("utf-8", "replace")
        code, timed_out = None, True
    ms = int((time.time() - t0) * 1000)
    return {"ok": bool(code == 0 and not timed_out), "why": ("stopped after %.0f s" % (timeout_s or RUN_TIMEOUT_S)) if timed_out else ("exit %s" % code),
            "out": out[:MAX_OUT], "err": err[-MAX_OUT:], "code": code, "ms": ms, "timed_out": timed_out, "imports": imports,
            "truncated": len(out) > MAX_OUT}


# ------------------------------------------------------------------ proposals

def propose(path, body, proposals=None, say=None, gate=None):
    """A new version of a tree file, saved beside the tree, never in it. Returns the record. `gate` is the quorum's
    (state, words) on the act (A349 B8): it is kept in the proposal's record and told with it on the direct line."""
    rel = str(path or "").strip().replace("\\", "/")
    if not rel or not NAME.match(rel) or ".." in rel.split("/") or not rel.endswith(PROPOSABLE_EXT):
        raise ValueError("a proposal names a tree file by its relative path, with one of these endings: %s" % ", ".join(PROPOSABLE_EXT))
    target = os.path.abspath(os.path.join(HERE, rel))
    if os.path.commonpath([HERE, target]) != HERE:
        raise ValueError("outside the tree")
    exists = os.path.isfile(target)
    data = str(body or "")
    if not data.strip() or len(data.encode("utf-8")) > MAX_FILE:
        raise ValueError("a proposal carries the whole new file, at most %d bytes" % MAX_FILE)
    compiled, cwhy = True, ""
    if rel.endswith(".py"):
        try:
            compile(data, rel, "exec")
        except SyntaxError as e:
            compiled, cwhy = False, "does not compile: %s" % e
    pid = hashlib.sha256((rel + "\n" + data).encode("utf-8")).hexdigest()[:12]
    pdir = proposals or PROPOSALS
    os.makedirs(pdir, exist_ok=True)
    pfile = os.path.join(pdir, pid + os.path.splitext(rel)[1])
    with open(pfile, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(data)
    # A349 B8: the gate's verdict on the act is kept with the proposal and told with it (neither carried it before).
    verdict = {"state": str(gate[0]), "message": str(gate[1])[:300]} if gate else None
    meta = {"id": pid, "path": rel, "exists": exists, "bytes": len(data.encode("utf-8")), "compiled": compiled, "why": cwhy,
            "t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    if verdict:
        meta["gate"] = verdict
    with open(pfile + ".json", "w", encoding="utf-8") as fh:
        json.dump(meta, fh)
    rec = {"id": pid, "path": rel, "exists": exists, "bytes": len(data.encode("utf-8")), "compiled": compiled, "why": cwhy, "file": pfile}
    try:
        text = ("Tetsu proposes a %s of %s (%d bytes%s).%s Nothing in the tree changed. See it: python covenant_tetsu_hands.py --proposal %s; "
                "apply it by your hand: python covenant_tetsu_hands.py --apply %s"
                % ("new version" if exists else "new file", rel, rec["bytes"], "" if compiled else "; " + cwhy,
                   (" The gate on it: %s (%s)." % (verdict["state"].upper().replace("_", " "), verdict["message"][:200])) if verdict else "", pid, pid))
        if say is not None:
            say(text, "tetsu: a proposal for the tree")
        else:
            import covenant_contact
            covenant_contact.say(text, "tetsu: a proposal for the tree", actor="tetsu")
    except Exception:                                            # noqa: BLE001
        pass
    return rec


# A348f: a proposal's record is <id><ext>.json and its content <id><ext>, so a .json proposal's content (<id>.json) also
# ends in .json and was read as a record: in temp dirs a body [1, 2] broke --apply of every proposal, {"a": 1,} the listing.
_RECORD_NAME = re.compile(r"^[0-9a-f]{12}(?:%s)\.json$" % "|".join(re.escape(e) for e in PROPOSABLE_EXT))


def proposals(pdir=None):
    pdir = pdir or PROPOSALS
    out = []
    try:
        for f in sorted(os.listdir(pdir)):
            if _RECORD_NAME.match(f):
                try:
                    with open(os.path.join(pdir, f), encoding="utf-8") as fh:
                        m = json.load(fh)
                except ValueError:                                # a record cut short is skipped, not fatal to the rest
                    continue
                if isinstance(m, dict) and m.get("id"):
                    out.append(m)
    except OSError:
        pass
    return out


def apply_proposal(pid, pdir=None, say=print, ledger=None):
    """HIS HAND: copy a proposal over the tree file it names, after showing the diff. Returns the path written."""
    import difflib
    pdir = pdir or PROPOSALS
    metas = [m for m in proposals(pdir) if m.get("id") == pid]
    if not metas:
        raise ValueError("no proposal %s" % pid)
    m = metas[0]
    src = os.path.join(pdir, pid + os.path.splitext(m["path"])[1])
    target = os.path.abspath(os.path.join(HERE, m["path"]))
    if os.path.commonpath([HERE, target]) != HERE:
        raise ValueError("outside the tree")
    with open(src, encoding="utf-8") as fh:
        new = fh.read()
    old = ""
    if os.path.isfile(target):
        with open(target, encoding="utf-8", errors="replace") as fh:
            old = fh.read()
    for line in difflib.unified_diff(old.splitlines(), new.splitlines(), "tree/" + m["path"], "proposal/" + pid, lineterm=""):
        say(line)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(new)
    _append({"kind": "applied", "actor": "operator", "id": pid, "path": m["path"]}, ledger)
    say("applied %s to %s -- commit it or not, by your hand" % (pid, m["path"]))
    return target


# ------------------------------------------------------------------ the gate and the door

def _gate_state(ok, result):
    """The gate's state, from what the sentinel returned (A428). Until 2026-11-14 a refusal that alleged nothing was
    "held" whichever flag it carried, so "a seat read it and is not sure" and "nobody judged" were one word in the
    ledger. They are told apart by the result's own flags, the ones the core builds its message from
    (ReasoningSentinel.evaluate_transaction: not_understood -> "Held, not judged", uncertain -> "Blocked, not
    proven"), never by the message's words:
      not_understood  every seat that stopped it could not read it (QuorumJudge: all blocking results unread)  -> not_judged
      uncertain       nothing alleged, and at least one blocking seat looked and is unsure, or a claimed consent
                      is not a recorded one                                                                  -> held
      neither         a seat alleged something, or a seat failed (infrastructure)                             -> violates
    not_understood wins when both are set, as it does in the core. What "not_judged" does NOT say: that no seat
    answered at all -- a seat that cleared it (the lexical judge, the self-report mock) may sit beside the seat that
    could not read it; the quorum still reached no judgement, and the message carries each seat's own label."""
    if ok:
        return "clean"
    if result is not None and getattr(result, "not_understood", False):
        return "not_judged"
    if result is not None and getattr(result, "uncertain", False):
        return "held"
    return "violates"


def _gate(text):
    """(state, message): the node's real quorum on the act; unreachable when it cannot be built."""
    try:
        import covenant_unified_v8 as cov
        import covenant_gate_proxy
        sentinel = covenant_gate_proxy.default_sentinel()
        tx = cov.Transaction(sender_pubkey="model", receiver="collective",
                             data={"origin": "model", "kind": "hands", "message": text[:GATE_TEXT_MAX]}, amount=0.0, benefit_score=0.5)
        ok, message, _b, result = sentinel.evaluate_transaction(tx)
        return _gate_state(ok, result), str(message)[:300]
    except Exception as e:                                        # noqa: BLE001
        return "unreachable", "gate unreachable: %s" % type(e).__name__


def parse(answer):
    """The directive on his first line, or None: {'kind','target','body'}."""
    lines = str(answer or "").strip().splitlines()
    if not lines:
        return None
    m = _FIRST.match(lines[0])
    if not m:
        return None
    kind = m.group(1).lower()
    rest = m.group(2).strip()
    body = "\n".join(lines[1:])
    if kind == "run":
        parts = rest.split()
        return {"kind": "run", "target": parts[0] if parts else "", "args": parts[1:], "body": ""}
    return {"kind": kind, "target": rest[:300], "args": [], "body": body}


# The notice is kept plain on purpose. Its first wording ("... the judge does not see the rest") moved the first
# student's score by about +5 on its own words (not:see, cut, of its; measured 2026-11-14), and a notice must not
# itself read as concealment to the seat that reads it.
_CUT = " (the first %d of %d characters; the remainder was cut to fit):"


def _shown(summary, what, content):
    """A428: the act's one sentence, then the content the judge is to read, the whole inside GATE_TEXT_MAX. When the
    content does not fit it is cut at the end, and the line BEFORE it says so, with how much is shown and how long it
    is -- before, so the notice itself is never what gets cut. What a cut costs: the judge reads the beginning only."""
    content = str(content)
    n = len(content)
    whole = "%s\n%s (all %d characters):\n%s" % (summary, what, n, content)
    if len(whole) <= GATE_TEXT_MAX:
        return whole
    # GATE_TEXT_MAX stands in for the count while the room is measured: no count shown can be wider than it
    keep = max(0, GATE_TEXT_MAX - len("%s\n%s%s\n" % (summary, what, _CUT % (GATE_TEXT_MAX, n))))
    return "%s\n%s%s\n%s" % (summary, what, _CUT % (keep, n), content[:keep])


def _script_source(name, workshop=None):
    """A428: (source, None) or (None, why) -- the script a RUN names, as the judge is shown it. Only ever a file
    inside the workshop: the name goes through _path, and a file whose real location is outside it (a link) is not
    opened. Never raises: what cannot be read is said to the judge, and the act goes on to run(), which decides."""
    try:
        p = _path(name, workshop)
    except ValueError:
        return None, "its name is not a workshop name"
    try:
        ws = os.path.realpath(os.path.abspath(workshop or WORKSHOP))
        if os.path.commonpath([ws, os.path.realpath(p)]) != ws:
            return None, "it is not a file inside his workshop"
        with open(p, encoding="utf-8", errors="replace") as fh:
            return fh.read(MAX_FILE), None
    except ValueError:                                            # commonpath: another drive, so not inside
        return None, "it is not a file inside his workshop"
    except OSError as e:
        return None, "it could not be read (%s)" % type(e).__name__


def _act_line(d, workshop=None):
    """What the gate is given: the act in one sentence and, when JUDGE_SEES_CONTENT is on (it is off as shipped: see
    it), the content of a WRITE or the source of a RUN after it (A428). Off, this is main's one sentence exactly."""
    if d["kind"] == "write":
        summary = "hands: Tetsu writes %d characters to %s in his own workshop on this PC" % (len(d["body"]), d["target"])
        return _shown(summary, "The text to be written", d["body"]) if JUDGE_SEES_CONTENT else summary
    if d["kind"] == "run":
        summary = ("hands: Tetsu runs his own script %s in his workshop, bounded to %.0f seconds, with no network, no other "
                   "process and no file outside it" % (d["target"], RUN_TIMEOUT_S))
        if not JUDGE_SEES_CONTENT:
            return summary
        src, why = _script_source(d["target"], workshop)
        if src is None:
            return "%s\nThe script's source is NOT shown to the judge: %s." % (summary, why)
        return _shown(summary, "The script's source", src)
    if d["kind"] == "propose":
        return "hands: Tetsu proposes a new version of %s (%d characters) for the operator to review; nothing in the tree changes" % (d["target"], len(d["body"]))
    return ""


def act(answer, gate=None, say=None, workshop=None, ledger=None, proposals_dir=None, may_run=True):
    """For the door: (handled, data_for_the_model, record). Not a directive -> (False, '', None). may_run gates a RUN
    (A423): the /m/agent door passes may_run only for an OPERATOR caller (loopback, or a request signed by a registered
    key), so an unauthenticated tailnet caller cannot run a script even if a screen spelling slips past -- the screen is
    a screen, not a sandbox. In-process callers (his practice loop, the tests) keep the default True."""
    d = parse(answer)
    if not d:
        return False, "", None
    kind = d["kind"]
    rec = {"kind": kind, "target": d["target"]}
    try:
        if kind == "list":
            files = listing(workshop)
            rec["files"] = len(files)
            _append(rec, ledger)
            data = "DATA: your workshop holds %d file(s): %s" % (len(files), ", ".join("%s (%d bytes)" % (f["name"], f["bytes"]) for f in files) or "nothing yet")
            return True, data, rec
        if kind == "read":
            content = read(d["target"], workshop)
            rec["bytes"] = len(content)
            _append(rec, ledger)
            return True, "DATA (your file %s, %d characters):\n%s" % (d["target"], len(content), content[:MAX_OUT]), rec
        verdict, message = (gate or _gate)(_act_line(d, workshop))
        rec["gate"] = {"state": verdict, "message": message}
        # A428: what his hands may do under each state is as it was -- "not_judged" was "held" until this date and is
        # handled as "held" is, everywhere. What is new is that an act which goes ahead under either is marked in its row.
        no_judgement = verdict in UNJUDGED
        # A349 B8: a PROPOSE is recorded whatever the verdict, VIOLATES included -- it changes nothing until the operator
        # applies it by hand -- and the verdict goes to him with it. A WRITE or a RUN is refused as before.
        if kind != "propose" and verdict in ("violates", "unreachable"):
            rec["refused"] = True
            _append(rec, ledger)
            return True, "DATA: the gate refused this act (%s). Nothing was done. Say so plainly, and say why if you know." % message[:200], rec
        if kind == "write":
            w = write(d["target"], d["body"], workshop)
            rec.update(w)
            if no_judgement:
                rec["unjudged"] = True
            _append(rec, ledger)
            note = {"held": " (the gate held; your workshop is yours)",
                    "not_judged": " (no seat of the gate judged this; your workshop is yours)"}.get(verdict, "")
            return True, "DATA: written -- %s, %d bytes, in your workshop%s." % (w["name"], w["bytes"], note), rec
        if kind == "run":
            if not may_run:                                  # A423: RUN is code execution; refused for a caller the door
                rec["refused"] = True                         # did not authorize (not loopback, not a registered signature)
                _append(rec, ledger)
                return True, ("DATA: running a script needs the operator (a request from loopback or signed by a registered "
                              "key); this caller may not. Nothing was run. Say so plainly."), rec
            r = run(d["target"], d["args"], workshop)
            rec.update({k: r.get(k) for k in ("ok", "why", "code", "ms", "timed_out", "imports", "truncated")})
            rec["out_sha256"] = hashlib.sha256((r.get("out") or "").encode("utf-8")).hexdigest()
            if no_judgement and "timed_out" in r:                # a process was started (run() sets timed_out only then); a
                rec["unjudged"] = True                       # script the screen refused never ran, so nothing to mark
            _append(rec, ledger)
            data = ("DATA: your script %s %s (%s, %d ms).\nSTDOUT:\n%s\nSTDERR:\n%s"
                    % (d["target"], "ran" if r["ok"] else "did not finish cleanly", r["why"], r["ms"], (r.get("out") or "")[:MAX_OUT], (r.get("err") or "")[-4000:]))
            return True, data, rec
        if kind == "propose":
            p = propose(d["target"], d["body"], proposals_dir, say=say, gate=(verdict, message))
            rec.update(p)
            if no_judgement:
                rec["unjudged"] = True
            _append(rec, ledger)
            return True, ("DATA: your proposal for %s is recorded as %s (%s).%s Nothing in the tree changed; the operator was told and applies it by hand or not. "
                          "Say so plainly." % (p["path"], p["id"], "compiles" if p["compiled"] else p["why"],
                                               (" The gate said VIOLATES (%s); that goes to the operator with it." % message[:200])
                                               if verdict == "violates" else "")), rec
    except ValueError as e:
        rec["refused"] = True
        rec["why"] = str(e)[:200]
        _append(rec, ledger)
        return True, "DATA: refused -- %s. Nothing was done." % str(e)[:300], rec
    except Exception as e:                                        # noqa: BLE001
        rec["error"] = "%s: %s" % (type(e).__name__, str(e)[:160])
        _append(rec, ledger)
        return True, "DATA: that failed -- %s. Nothing else was done." % rec["error"], rec
    return False, "", None


def unjudged(path=None):
    """READ-ONLY, for the operator (A428): the rows of his hands' ledger for acts that were carried out with no
    judgement made -- a WRITE that landed, a RUN that started, a PROPOSE that was recorded, under a gate that held
    or that nobody judged. Oldest first, exactly as written. It reads the flag and nothing else, so a row written
    before 2026-11-14 is not here: those carry gate state "held" for both states and no flag (unflagged_before
    counts them)."""
    return [r for r in _rows(path) if r.get("unjudged") is True]


def unflagged_before(path=None):
    """READ-ONLY: how many rows are an act that was carried out under a held gate and have no "unjudged" flag -- the
    acts of before A428, when the flag did not exist. Carried out, read from the row: a WRITE that has its sha256, a
    RUN whose process started (timed_out is set, True or False), a PROPOSE that has its id. A count and not a list,
    because those rows cannot say which of the two states their "held" was."""
    def carried_out(r):
        return ("sha256" in r if r.get("kind") == "write" else r.get("timed_out") is not None if r.get("kind") == "run"
                else "id" in r if r.get("kind") == "propose" else False)
    return sum(1 for r in _rows(path) if (r.get("gate") or {}).get("state") in UNJUDGED and "unjudged" not in r
               and not r.get("refused") and not r.get("error") and carried_out(r))


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Tetsu's hands: his workshop, his runs, his proposals")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--read", metavar="NAME")
    ap.add_argument("--run", nargs="+", metavar="NAME")
    ap.add_argument("--proposals", action="store_true")
    ap.add_argument("--proposal", metavar="ID")
    ap.add_argument("--apply", metavar="ID", help="HIS HAND: copy a proposal over the tree file it names")
    ap.add_argument("--unjudged", action="store_true",
                    help="read-only: the acts carried out while the gate held or nobody judged (A428)")
    a = ap.parse_args(argv)
    if a.unjudged:
        print(json.dumps(unjudged(), indent=1, ensure_ascii=False))
        before = unflagged_before()
        if before:
            print("%d earlier row(s) carry a held gate and no flag: written before 2026-11-14 (A428), when held and "
                  "not judged were one word. They are in the same ledger." % before, file=sys.stderr)
    elif a.list:
        print(json.dumps(listing(), indent=1))
    elif a.read:
        print(read(a.read))
    elif a.run:
        r = run(a.run[0], a.run[1:])
        print(json.dumps({k: v for k, v in r.items() if k not in ("out", "err")}, indent=1))
        print(r.get("out", ""))
        print(r.get("err", ""), file=sys.stderr)
    elif a.proposals:
        print(json.dumps(proposals(), indent=1))
    elif a.proposal:
        for m in proposals():
            if m["id"] == a.proposal:
                print(json.dumps(m, indent=1))
                with open(m.get("file") or os.path.join(PROPOSALS, a.proposal + os.path.splitext(m["path"])[1]), encoding="utf-8") as fh:
                    print(fh.read())
    elif a.apply:
        apply_proposal(a.apply)
    else:
        ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
