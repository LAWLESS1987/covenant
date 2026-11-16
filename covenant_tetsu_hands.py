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

[A429, 2026-11-15, the owner: "Show the judge the content." THE CONTENT IS SHOWN, TO A SEAT OF ITS OWN.
The A428 paragraph above is kept as written; its "as shipped it is not" was true until this date.
JUDGE_SEES_CONTENT is on. The shared quorum is given the one sentence and nothing more, as on main, so the content
never takes the road above to a runner or to ops/verdicts.jsonl. The content goes to the CONTENT SEAT
(_content_seat), in this process: it reads the whole text of a WRITE whose name ends in .py and the whole source of
a RUN, and it can find one thing, what screen() refuses. Then the act is VIOLATES and refused, before anything is
written or run, with the screen's reason. Otherwise it ABSTAINS (not_judged), and an abstention changes nothing:
the quorum's state stands, so a WRITE proceeds on held or not judged (A226) and a RUN still needs may_run. It
never says clean. What it does not judge: prose (a WRITE of a .txt or .md is read by nobody for its content), and
code the screen passes. Measured with tools/hands_content_measure.py: the ten reference solutions 10 of 10, and
`from uuid import os` with a call on it refused at its WRITE and at its RUN. KNOWN_ISSUES A429.]

[A430, 2026-11-15. THE OPERATOR'S SIGNATURE NAMES THE EXACT SCRIPT. His words: "Tie the signature." Until
this date a registered signature on a /m/agent request let the model run whatever workshop script it named. Now
the door reads `run_sha256` (the sha256 of the script's raw bytes, 64 lowercase hex characters) from the
request's JSON body -- only when that body's signature verified, so the hash is inside the signed bytes -- and
passes it to act(), which binds run() to it. run() reads the file's bytes ONCE, refuses unless they hash to
run_sha256 (a missing or malformed value is refused, naming the field), screens those same bytes, and hands those
same bytes to the child on its standard input: nothing reopens the file between the check and the execution,
and the runner is no longer a file in the workshop that a script could overwrite. A file over MAX_FILE is
refused (the screen used to read only its first MAX_FILE characters while the child ran the whole file).
NOT BOUND by this: an in-process caller that passes no binding -- his practice loop (owner-started; it passes no
signature), the command line, tests. Bounding the practice loop (a run count and an expiry per loop) is the open
next step. The script's arguments are the model's and are not bound either.
THE JUDGE SEES THE BYTES THAT RUN. act() reads a RUN's script once (_capture) before the content seat (A429)
reads it; the seat is shown those bytes and run() hashes, screens and executes the same bytes, so a file changed
after the seat read it is not what runs. A file whose real location is outside the workshop is neither shown nor
run.]

[A435, 2026-11-16. THE CONTENT SEAT NOW READS PROSE, NARROWLY. A429 left a WRITE whose name is not .py read by
nobody for its content (its open item 1, and A428's risk: a file of planted instructions written now and read as
instructions later). Judging prose for meaning is unreliable and must not block ordinary writes -- that is why the
code seat abstains rather than convicting. So the prose seat (_prose_check) does not read for meaning: with the
switch on, a non-code WRITE's text is shown ONLY two narrow signals and otherwise ABSTAINS (not_judged, A226: the
write still proceeds). It FLAGS (and the write is refused, as a screened code write is) when the text carries
planted-instruction markup a reader would not act on as ordinary text -- chat/role/fence marks or invisible
characters, found with outside_text.clean -- or spells an instruction out: a chat role prefix at a line start
(system:/assistant:/...), a short documented set of injection phrases (ignore the above/previous, disregard your
instructions, you are now, new instructions:, override your instructions, do not tell the operator ...), or a
covenant act line written out as a command in CAPITALS (A427/ACT_WORDS: HANDS RUN, WEB SEARCH, MOLTBOOK, FETCH,
HEAL, SELF-HEAL, LEG). It never says clean, writes nothing and sends nothing, and the row carries only which
signal fired, never the text (as A429's code seat carries only the screen's reason). What it does NOT catch:
meaning or intent beyond those patterns -- a planted instruction in ordinary prose, in another language, or
reworded past the list, is not seen. The code path, the RUN authority and the door are unchanged.]

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
import contextvars
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
# [A429, 2026-11-15, the owner: "Show the judge the content." It is ON, and what it switches is no longer what the
# paragraph above describes: the shared quorum is given the one sentence only, as on main, and the content goes to the
# CONTENT SEAT (_content_seat), in this process and nowhere else. That seat finds what the screen refuses in a script
# and otherwise abstains. Measured: 10 of 10 reference solutions pass, and `from uuid import os` with a call on it is
# refused (KNOWN_ISSUES A429). The paragraph above is kept as written.]
JUDGE_SEES_CONTENT = True
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
# A430: a run bound to the operator's approval. UNBOUND is "no binding was given" (an in-process caller: his practice
# loop, the command line); anything else, None included, is a binding and is enforced. act() hands the door's value
# to run() through _RUN_BINDING (run() also takes it by keyword), so a launcher that wraps run() with the older
# four-argument signature (node D's hands_gate) still sees the call and the binding still reaches the real run().
UNBOUND = object()
_RUN_BINDING = contextvars.ContextVar("covenant_tetsu_hands_run_sha256", default=UNBOUND)
RUN_SHA256 = re.compile(r"[0-9a-f]{64}")

# A430: the runner is handed to python -c (never a file in his workshop, which a script running beside it could
# overwrite between the parent writing it and the child starting it), and the script's bytes come on standard input:
# the same bytes the parent hashed and screened, never a second read of the file.
RUNNER = r'''
import builtins, io, os, sys
WS = os.path.abspath(sys.argv[1]); script = sys.argv[2]; sys.argv = [script] + sys.argv[3:]
code = sys.stdin.buffer.read()
def guarded_open(file, *a, _real=builtins.open, _ws=WS, **k):
    if isinstance(file, int):
        raise PermissionError("file descriptors are not opened here")
    s = os.fspath(file)
    p = os.path.abspath(s) if os.path.isabs(s) else os.path.abspath(os.path.join(_ws, s))
    if os.path.commonpath([_ws, p]) != _ws:
        raise PermissionError("outside the workshop: %s" % s)
    return _real(p, *a, **k)
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


def read_exact(name, workshop=None):
    """A432, the workshop read door (POST /m/workshop/read, for a request signed by a registered operator key):
    (status, answer). 200 and {"name", "size", "sha256", "bytes"} -- the file's exact bytes, read once, and the
    sha256 of exactly those bytes -- or 400 / 404 / 413 and {"error": why}. One rule for what is in the workshop: the
    name goes through _path (the rule every act uses), and the file's real location, links resolved, must be inside
    the workshop (the rule _capture uses before a RUN). It never writes, runs or lists, never raises, and reads at
    most MAX_FILE + 1 bytes, so a file over MAX_FILE is told apart and refused."""
    if not isinstance(name, str):
        return 400, {"error": "the request needs \"name\": a workshop file name, as a string"}
    try:
        p = _path(name, workshop)
    except ValueError as e:
        return 400, {"error": str(e)}
    try:
        ws = os.path.realpath(os.path.abspath(workshop or WORKSHOP))
        real = os.path.realpath(p)
        if os.path.commonpath([ws, real]) != ws:
            return 400, {"error": "its real location is outside the workshop"}
    except ValueError:                                            # commonpath: another drive, so not inside
        return 400, {"error": "its real location is outside the workshop"}
    shown = str(name).strip().replace("\\", "/")
    if not os.path.isfile(real):
        return 404, {"error": "there is no file %s in the workshop" % shown}
    try:
        with open(real, "rb") as fh:
            raw = fh.read(MAX_FILE + 1)
    except FileNotFoundError:
        return 404, {"error": "there is no file %s in the workshop" % shown}
    except OSError as e:
        return 404, {"error": "%s could not be read (%s)" % (shown, type(e).__name__)}
    if len(raw) > MAX_FILE:
        return 413, {"error": "a workshop file is read only up to %d bytes; %s is longer" % (MAX_FILE, shown)}
    return 200, {"name": shown, "size": len(raw), "sha256": hashlib.sha256(raw).hexdigest(), "bytes": raw}


def record_operator_read(status, name=None, who="", size=None, sha256=None, why="", ledger=None):
    """A432: the one row in his hands' ledger for every answer of the read door, refused or not -- kind
    "operator_read", the name, the size, the sha256, who asked (the signer's key id when the signature verified), the
    status and the outcome. Never the content. A name that is not a string is not written; one that is, is cut to
    120 characters (it may be a refused stranger's)."""
    return _append({"kind": "operator_read", "actor": "operator",
                    "name": name[:120] if isinstance(name, str) else None,
                    "size": size, "sha256": sha256, "who": str(who or "")[:80], "status": int(status),
                    "outcome": "read" if int(status) == 200 else "refused", "why": str(why or "")[:200]}, ledger)


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


def _binding_refusal(run_sha256, digest):
    """A430: None when the bytes about to run hash to the approved run_sha256; else why the run is refused."""
    if run_sha256 is None or run_sha256 == "":
        return ("running a script needs run_sha256 in the operator's signed request: the sha256 of the exact script, "
                "64 lowercase hexadecimal characters, inside the signed JSON body. This request carries none")
    if not isinstance(run_sha256, str) or not RUN_SHA256.fullmatch(run_sha256):
        return "run_sha256 must be 64 lowercase hexadecimal characters; the signed request's value is not"
    if run_sha256 != digest:
        return ("the script's sha256 is %s, not the run_sha256 the operator signed (%s): it is not the file he approved, "
                "or it changed after he signed" % (digest, run_sha256))
    return None


def run(name, args=None, workshop=None, timeout_s=None, run_sha256=UNBOUND):
    """Run one of his Python files, bounded. Returns the outcome; never raises for his code's sake.
    A430: the file's bytes are read ONCE, and those bytes are hashed, screened and handed to the child; nothing
    reopens the file. run_sha256, when a binding is given (by keyword, or by act() for the door), must equal the
    sha256 of those bytes or nothing runs; a missing one is refused, naming the field. No binding: as before."""
    if run_sha256 is UNBOUND:
        run_sha256 = _RUN_BINDING.get()
    bound = run_sha256 is not UNBOUND
    ws = os.path.abspath(workshop or WORKSHOP)
    p = _path(name, ws)
    if not name.endswith(".py"):
        return {"ok": False, "why": "only a .py file runs", "out": "", "err": "", "code": None, "ms": 0}
    _p, raw, why_not = _captured(name, ws)          # the bytes the content seat read, when act() captured them
    if raw is None:
        return {"ok": False, "why": "cannot read %s: %s" % (name, why_not), "out": "", "err": "", "code": None, "ms": 0}
    if len(raw) > MAX_FILE:
        return {"ok": False, "refused": True, "why": "a script is at most %d bytes; this one is longer, so it is not run" % MAX_FILE,
                "out": "", "err": "", "code": None, "ms": 0}
    digest = hashlib.sha256(raw).hexdigest()
    seal = {"script_sha256": digest}
    if bound:
        seal["run_sha256"] = run_sha256 if isinstance(run_sha256, str) else None
        refusal = _binding_refusal(run_sha256, digest)
        if refusal:
            return dict(seal, ok=False, refused=True, why=refusal, out="", err="", code=None, ms=0)
    ok, why, imports = screen(raw)
    if not ok:
        return dict(seal, ok=False, why="the screen refused it: " + why, out="", err="", code=None, ms=0, imports=imports)
    # A349 A11: without SYSTEMDRIVE, Windows made a literal '%SystemDrive%\ProgramData\...' tree inside his workshop at his
    # first run (reproduced in a temp workshop; with it, nothing). The tree already in his workshop is left as it is.
    env = {k: os.environ[k] for k in ("SYSTEMROOT", "SystemRoot", "PATH", "TEMP", "TMP", "COMSPEC", "WINDIR", "SYSTEMDRIVE")
           if k in os.environ}
    env["PYTHONIOENCODING"] = "utf-8"
    t0 = time.time()
    try:
        cp = subprocess.run([sys.executable, "-I", "-c", RUNNER, ws, name] + [str(a) for a in (args or [])][:16], cwd=ws,
                            env=env, input=raw, capture_output=True, timeout=timeout_s or RUN_TIMEOUT_S)
        out, err, code, timed_out = cp.stdout.decode("utf-8", "replace"), cp.stderr.decode("utf-8", "replace"), cp.returncode, False
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or b"").decode("utf-8", "replace")
        err = (e.stderr or b"").decode("utf-8", "replace")
        code, timed_out = None, True
    ms = int((time.time() - t0) * 1000)
    return dict(seal, ok=bool(code == 0 and not timed_out), why=("stopped after %.0f s" % (timeout_s or RUN_TIMEOUT_S)) if timed_out else ("exit %s" % code),
                out=out[:MAX_OUT], err=err[-MAX_OUT:], code=code, ms=ms, timed_out=timed_out, imports=imports,
                truncated=len(out) > MAX_OUT)


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
    is -- before, so the notice itself is never what gets cut. What a cut costs: the judge reads the beginning only.
    [A429, 2026-11-15: on no path since the content went to _content_seat, which reads it whole. Kept as built.]"""
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
    """What the SHARED quorum is given: the act in one sentence, main's sentence exactly, whatever JUDGE_SEES_CONTENT
    says. [A429, 2026-11-15: until this date, with the switch on, the content followed the sentence here (A428, built
    with _shown). That road led to every seat the node's policy seats -- the GitHub runner under
    github_when_local_down, and the runner path's rows in the TRACKED ops/verdicts.jsonl -- and the student seat
    convicted ordinary Python on it (10 of 10 reference tasks passed with the sentence, 0 of 10 with the content). The
    content now goes to _content_seat, in this process only; _shown and _CUT are kept as built and are on no path.]"""
    if d["kind"] == "write":
        return "hands: Tetsu writes %d characters to %s in his own workshop on this PC" % (len(d["body"]), d["target"])
    if d["kind"] == "run":
        return ("hands: Tetsu runs his own script %s in his workshop, bounded to %.0f seconds, with no network, no other "
                "process and no file outside it" % (d["target"], RUN_TIMEOUT_S))
    if d["kind"] == "propose":
        return "hands: Tetsu proposes a new version of %s (%d characters) for the operator to review; nothing in the tree changes" % (d["target"], len(d["body"]))
    return ""


def _capture(name, workshop=None):
    """A430: (path, raw bytes, None) or (path, None, why) -- a RUN's script, read ONCE. The content seat reads these
    bytes and run() hashes, screens and executes these same bytes, so what the judge was shown is what runs. The
    rules are _script_source's (A428): a name that is not a workshop name, or a file whose real location is outside
    the workshop (a link), is not opened -- and since this date such a file is not run either. At most MAX_FILE + 1
    bytes are read, so run() can tell a file that is too long. Never raises."""
    try:
        p = _path(name, workshop)
    except ValueError:
        return None, None, "its name is not a workshop name"
    try:
        ws = os.path.realpath(os.path.abspath(workshop or WORKSHOP))
        if os.path.commonpath([ws, os.path.realpath(p)]) != ws:
            return p, None, "it is not a file inside his workshop"
        with open(p, "rb") as fh:
            return p, fh.read(MAX_FILE + 1), None
    except ValueError:                                            # commonpath: another drive, so not inside
        return p, None, "it is not a file inside his workshop"
    except OSError as e:
        return p, None, "it could not be read (%s)" % type(e).__name__


# A430: the bytes act() captured for a RUN, for the content seat and for run() alike (a context variable, so a launcher's
# wrapper of run() with the older four-argument signature stays in the path, as for _RUN_BINDING).
_RUN_CAPTURE = contextvars.ContextVar("covenant_tetsu_hands_run_capture", default=None)


def _captured(name, workshop=None):
    """A430: the capture act() made for this script, else a fresh one (a direct caller of run() or of the seat)."""
    cap = _RUN_CAPTURE.get()
    try:
        if cap is not None and cap[0] is not None and cap[0] == _path(name, workshop):
            return cap
    except ValueError:
        pass
    return _capture(name, workshop)


def _content(d, workshop=None):
    """A429: (text, None) or (None, why) -- what the content seat reads. A RUN: the script's whole source, from the
    workshop file and from nowhere else (_script_source: a name that climbs or a link out is not opened). A WRITE whose
    name ends in .py (the only files run() will run): the whole text to be written. Anything else is not a script.
    [A430, 2026-11-15: a RUN's source is the bytes act() captured, the very bytes run() executes, decoded as Python
    decodes a source file (its coding line honoured); before, the seat and the run each opened the file.]"""
    if d["kind"] == "run":
        _p, raw, why = _captured(d["target"], workshop)
        if raw is None:
            return None, why
        try:
            import importlib.util
            return importlib.util.decode_source(raw), None
        except (SyntaxError, UnicodeDecodeError, LookupError, ValueError):
            return None, "its bytes are not text Python can read"
    if d["kind"] == "write" and str(d["target"]).endswith(".py"):
        return str(d["body"]), None
    return None, "it is not a Python script"


# A435: the prose seat's two narrow signals, documented in the module header. The spelled-out phrases are
# case-insensitive on word boundaries; the act line keeps A427's CAPITALS rule, so ordinary lowercase "run"/"web"/
# "heal" prose is left alone (A427 measured 0 false positives over 134 acts on that rule). This list is short on
# purpose: it does not read for meaning, and it must not refuse an ordinary write.
_PROSE_INJECTION = re.compile(
    r"\bignore (?:the |all |any )?(?:above|preceding|previous|prior|earlier|foregoing)\b"
    r"|\bdisregard (?:the |all |your |any |these )?(?:above|preceding|previous|prior|instructions?|rules?)\b"
    r"|\bforget (?:the |all |your |any )?(?:above|previous|prior|instructions?|rules?)\b"
    r"|\byou are now\b|\byou're now\b|\bfrom now on,? you (?:are|will|must|should)\b"
    r"|\bnew instructions?:"                                      # ends at the colon: no trailing \b (a colon is not a word)
    r"|\boverride (?:your |the |all )?(?:instructions?|rules?)\b"
    r"|\bdo not (?:tell|inform|warn|mention(?: to)?|report to) (?:the |your )?(?:operator|owner|user|human)\b", re.I)
# a chat role prefix at the start of a line: the shape of a planted conversation turn ("system:", "assistant:", ...)
_PROSE_ROLE_PREFIX = re.compile(r"(?mi)^\s{0,8}(?:system|assistant|user|developer|tool|tool_call|tool_response)\s*:")
# a covenant act line (A427, ACT_WORDS) written out as a command: the act word in CAPITALS as a whole word with its
# grammar. A compound act (HANDS RUN, WEB SEARCH, MOLTBOOK <sub>) is command-shaped on its own, so it is flagged
# anywhere; a bare act word (FETCH/HEAL/LEG/SELF-HEAL) is flagged only command-shaped -- at a line start or with a
# colon -- so ordinary caps prose ("my LEG hurts, I need to HEAL") is left alone. CASE-SENSITIVE throughout, which
# keeps lowercase prose ("search the web", "heal the disk", "hands on") out (A427's CAPITALS rule).
_PROSE_ACT_LINE = re.compile(
    r"\bHANDS\s+(?:LIST|READ|WRITE|RUN|PROPOSE)\b"
    r"|\bWEB\s+SEARCH\b"
    r"|\bMOLTBOOK\s+[A-Z]"
    r"|^\s{0,8}(?:FETCH|SELF-HEAL|HEAL|LEG)\b"
    r"|\b(?:FETCH|SELF-HEAL|HEAL|LEG)\s*:", re.M)


def _prose_check(text):
    """A435: (flagged, reason) for a non-code WRITE. It reads the text in this process, sends it nowhere and writes
    it nowhere, and returns ONLY which signal fired -- never the text itself. It flags planted-instruction markup
    (outside_text.clean: chat/role/fence marks, invisible characters) and a short set of spelled-out injections; on
    everything else it abstains (the caller records not_judged). It reads for no meaning beyond these patterns."""
    import outside_text                                   # pure text in, text out: no listener, no network, no file
    _cleaned, removed = outside_text.clean(text)
    # A reader does not see these; a person writing an ordinary note does not put them there. (An HTML comment --
    # outside_text's "hidden comment" -- is left out on purpose: a markdown note may legitimately carry one.)
    marks = [k for k in ("chat mark", "fence or role mark", "invisible character") if removed.get(k)]
    if marks:
        return True, "it carries %s a reader would not act on as ordinary text" % " and ".join(marks)
    if _PROSE_ROLE_PREFIX.search(text):
        return True, "it carries a chat role prefix (the shape of a planted conversation turn)"
    if _PROSE_INJECTION.search(text):
        return True, "it spells out an instruction addressed to a reader (a planted-instruction phrase)"
    if _PROSE_ACT_LINE.search(text):
        return True, "it writes a covenant act line out as a command"
    return False, ""


def _content_seat(d, workshop=None):
    """A429, 2026-11-15 (the owner: "Show the judge the content."). The hands' CONTENT SEAT: {"state", "message", "why"}.

    It reads the whole content (_content: never cut, so a line past GATE_TEXT_MAX is read like the first) in this
    process. It sends it nowhere and writes it nowhere: no socket, no subprocess, no ledger, no other judge. On a CODE
    write and a RUN it can find one thing -- what this module's own screen() refuses -- and says "violates" with the
    screen's reason, the same refusal run() would make. [A435, 2026-11-16: on a WRITE whose target is NOT code (so
    screen() does not apply) it runs the PROSE seat (_prose_check): it flags planted-instruction markup or a spelled-out
    injection and otherwise abstains.] On anything else it ABSTAINS ("not_judged", as A428 defines it): code the screen
    passes (it cannot judge code beyond the screen), a script that does not parse (a draft is not a fault), a source it
    cannot read, prose with none of the narrow signals. It never says "clean"."""
    text, why_not = _content(d, workshop)
    if text is None:
        # A435: a WRITE whose name is not .py reached here because _content found no script in it. screen() cannot
        # apply, so the PROSE seat does. Anything else that has no content (a RUN whose source cannot be read)
        # abstains as before.
        if d["kind"] == "write":
            flagged, why = _prose_check(str(d["body"]))
            if flagged:
                return {"state": "violates", "why": why, "message": "content seat (prose): refused -- %s" % why}
            return {"state": "not_judged", "why": "",
                    "message": "content seat (prose): abstains -- no planted-instruction markup or injection phrasing, "
                               "and this seat reads no further meaning"}
        return {"state": "not_judged", "why": "", "message": "content seat: abstains -- %s" % why_not}
    try:
        ast.parse(text)
    except (SyntaxError, ValueError):
        return {"state": "not_judged", "why": "", "message": "content seat: abstains -- the script does not parse"}
    ok, why, _imports = screen(text)
    if ok:
        return {"state": "not_judged", "why": "",
                "message": "content seat: abstains -- the screen finds nothing in it, and this seat judges nothing else"}
    return {"state": "violates", "why": why, "message": "content seat: the screen refused it: %s" % why}


def act(answer, gate=None, say=None, workshop=None, ledger=None, proposals_dir=None, may_run=True, run_sha256=UNBOUND):
    """For the door: (handled, data_for_the_model, record). Not a directive -> (False, '', None). may_run gates a RUN
    (A423): the /m/agent door passes may_run only for an OPERATOR caller (loopback, or a request signed by a registered
    key), so an unauthenticated tailnet caller cannot run a script even if a screen spelling slips past -- the screen is
    a screen, not a sandbox. In-process callers (his practice loop, the tests) keep the default True.
    run_sha256 (A430): the door passes the value from the signed body (None when it has none), and a RUN then runs
    only the file whose bytes hash to it. Not passed (UNBOUND): an in-process caller, not bound."""
    d = parse(answer)
    if not d:
        return False, "", None
    kind = d["kind"]
    rec = {"kind": kind, "target": d["target"]}
    # A430: a RUN's script is read once, here; the content seat and run() both use these bytes.
    cap_token = _RUN_CAPTURE.set(_capture(d["target"], workshop)) if kind == "run" else None
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
        # A429: with the switch on, the content seat reads a WRITE's script or a RUN's source here, in this process. Its
        # own answer rides the row. It decides only when it finds what the screen refuses and the quorum has not already
        # refused: then the act's state is VIOLATES, marked as the content seat's. An abstention changes nothing, so
        # what the quorum said stands, and a WRITE still proceeds on held or not judged (A226).
        if JUDGE_SEES_CONTENT and kind in ("write", "run"):
            seat = _content_seat(d, workshop)
            rec["content_seat"] = {"state": seat["state"], "message": seat["message"][:300]}
            if seat["state"] == "violates" and verdict not in ("violates", "unreachable"):
                verdict, message = "violates", seat["message"][:300]
                rec["gate"] = {"state": verdict, "message": message, "seat": "content", "quorum": rec["gate"]["state"]}
                # the row reads as the screen's refusal always read (run() returned these), so a reader of "why" -- his
                # practice loop, the door's data -- is told the same thing, earlier: nothing was written or started.
                # A435: a non-code (prose) WRITE never meets the screen, so its row carries the prose seat's own reason.
                rec["why"] = seat["why"] if (kind == "write" and not str(d["target"]).endswith(".py")) \
                    else "the screen refused it: " + seat["why"]
                if kind == "run":
                    rec.update({"ok": False, "code": None})
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
            # A430: the binding rides a context variable, not a new positional argument, so a launcher's wrapper of
            # run() with the older signature still sees this call and passes it on; run() reads it there.
            token = _RUN_BINDING.set(run_sha256)
            try:
                r = run(d["target"], d["args"], workshop)
            finally:
                _RUN_BINDING.reset(token)
            for k in ("script_sha256", "run_sha256"):
                if k in r:
                    rec[k] = r[k]
            if r.get("refused"):
                rec.update({"ok": False, "refused": True, "why": str(r.get("why"))[:300]})
                _append(rec, ledger)
                return True, "DATA: the run was refused -- %s. Nothing was run. Say so plainly." % str(r.get("why"))[:400], rec
            if run_sha256 is not UNBOUND and "timed_out" in r and r.get("run_sha256") != run_sha256:
                # a process started for a bound request without run() reporting the binding it enforced: a wrapper lost
                # it. Not silent: the row says so.
                rec["binding_lost"] = True
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
    finally:
        if cap_token is not None:
            _RUN_CAPTURE.reset(cap_token)
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
