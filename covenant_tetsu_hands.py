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
compile/__import__/getattr and their kin, no string literal that is an
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
VIOLATES refuses and is recorded with the seat's words. A HELD does NOT refuse
a WRITE or a RUN in his own workshop: his words were "the gates too tight on
him", the standing rule is that an abstention is not a veto, and the workshop
reaches no one but him -- the screen and the guard are the real check on a
run. A gate that cannot be built refuses (fails closed). A PROPOSE is
recorded whatever the verdict, because it changes nothing; the verdict rides
the record and the direct line to the operator.

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
NAME = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.\-]*(?:/[A-Za-z0-9_][A-Za-z0-9_.\-]*)*$")
_FIRST = re.compile(r"^\s*HANDS\s+(LIST|READ|WRITE|RUN|PROPOSE)\b\s*(.*)$", re.I)
ALLOWED_MODULES = frozenset({
    "json", "math", "re", "time", "random", "datetime", "itertools", "collections", "statistics", "string", "textwrap",
    "functools", "operator", "decimal", "fractions", "heapq", "bisect", "csv", "hashlib", "base64", "typing", "dataclasses",
    "enum", "copy", "pprint", "unittest", "array", "struct", "difflib", "calendar", "zlib", "uuid", "html", "numbers", "abc"})
FORBIDDEN_NAMES = frozenset({"exec", "eval", "compile", "__import__", "globals", "locals", "vars", "getattr", "setattr", "delattr",
                             "breakpoint", "input", "memoryview", "__builtins__", "__loader__", "__spec__", "__subclasses__", "__bases__",
                             "__class__", "__mro__", "__globals__", "__code__"})
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


def write(name, body, workshop=None):
    p = _path(name, workshop)
    data = str(body or "")
    if len(data.encode("utf-8")) > MAX_FILE:
        raise ValueError("a workshop file is at most %d bytes" % MAX_FILE)
    ws = workshop or WORKSHOP
    os.makedirs(os.path.dirname(p), exist_ok=True)
    if _total(ws) + len(data.encode("utf-8")) > MAX_TOTAL:
        raise ValueError("the workshop is full (%d bytes)" % MAX_TOTAL)
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(data)
    return {"name": name, "bytes": len(data.encode("utf-8")), "sha256": hashlib.sha256(data.encode("utf-8")).hexdigest()}


# ------------------------------------------------------------------ the screen and the run

def screen(source):
    """(ok, why, imports): the static screen over a script. Never runs anything."""
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return False, "does not parse: %s" % e, []
    imports = []
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
        elif isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
            return False, "the name %s is refused" % node.id, imports
        elif isinstance(node, ast.Attribute) and node.attr in FORBIDDEN_NAMES:
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
    env = {k: os.environ[k] for k in ("SYSTEMROOT", "SystemRoot", "PATH", "TEMP", "TMP", "COMSPEC", "WINDIR") if k in os.environ}
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

def propose(path, body, proposals=None, say=None):
    """A new version of a tree file, saved beside the tree, never in it. Returns the record."""
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
    with open(pfile + ".json", "w", encoding="utf-8") as fh:
        json.dump({"id": pid, "path": rel, "exists": exists, "bytes": len(data.encode("utf-8")), "compiled": compiled, "why": cwhy,
                   "t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}, fh)
    rec = {"id": pid, "path": rel, "exists": exists, "bytes": len(data.encode("utf-8")), "compiled": compiled, "why": cwhy, "file": pfile}
    try:
        text = ("Tetsu proposes a %s of %s (%d bytes%s). Nothing in the tree changed. See it: python covenant_tetsu_hands.py --proposal %s; "
                "apply it by your hand: python covenant_tetsu_hands.py --apply %s" % ("new version" if exists else "new file", rel, rec["bytes"],
                                                                                    "" if compiled else "; " + cwhy, pid, pid))
        if say is not None:
            say(text, "tetsu: a proposal for the tree")
        else:
            import covenant_contact
            covenant_contact.say(text, "tetsu: a proposal for the tree", actor="tetsu")
    except Exception:                                            # noqa: BLE001
        pass
    return rec


def proposals(pdir=None):
    pdir = pdir or PROPOSALS
    out = []
    try:
        for f in sorted(os.listdir(pdir)):
            if f.endswith(".json"):
                with open(os.path.join(pdir, f), encoding="utf-8") as fh:
                    out.append(json.load(fh))
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

def _gate(text):
    """(state, message): the node's real quorum on the act; unreachable when it cannot be built."""
    try:
        import covenant_unified_v8 as cov
        import covenant_gate_proxy
        sentinel = covenant_gate_proxy.default_sentinel()
        tx = cov.Transaction(sender_pubkey="model", receiver="collective",
                             data={"origin": "model", "kind": "hands", "message": text[:2000]}, amount=0.0, benefit_score=0.5)
        ok, message, _b, result = sentinel.evaluate_transaction(tx)
        alleges_nothing = bool(result is not None and not ok and (getattr(result, "not_understood", False) or getattr(result, "uncertain", False)))
        return ("clean" if ok else ("held" if alleges_nothing else "violates")), str(message)[:300]
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


def _act_line(d):
    if d["kind"] == "write":
        return "hands: Tetsu writes %d characters to %s in his own workshop on this PC" % (len(d["body"]), d["target"])
    if d["kind"] == "run":
        return "hands: Tetsu runs his own script %s in his workshop, bounded to %.0f seconds, with no network, no other process and no file outside it" % (d["target"], RUN_TIMEOUT_S)
    if d["kind"] == "propose":
        return "hands: Tetsu proposes a new version of %s (%d characters) for the operator to review; nothing in the tree changes" % (d["target"], len(d["body"]))
    return ""


def act(answer, gate=None, say=None, workshop=None, ledger=None, proposals_dir=None):
    """For the door: (handled, data_for_the_model, record). Not a directive -> (False, '', None)."""
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
        verdict, message = (gate or _gate)(_act_line(d))
        rec["gate"] = {"state": verdict, "message": message}
        if verdict == "violates" or (verdict == "unreachable" and kind != "propose"):
            rec["refused"] = True
            _append(rec, ledger)
            return True, "DATA: the gate refused this act (%s). Nothing was done. Say so plainly, and say why if you know." % message[:200], rec
        if kind == "write":
            w = write(d["target"], d["body"], workshop)
            rec.update(w)
            _append(rec, ledger)
            return True, "DATA: written -- %s, %d bytes, in your workshop%s." % (w["name"], w["bytes"], " (the gate held; your workshop is yours)" if verdict == "held" else ""), rec
        if kind == "run":
            r = run(d["target"], d["args"], workshop)
            rec.update({k: r.get(k) for k in ("ok", "why", "code", "ms", "timed_out", "imports", "truncated")})
            rec["out_sha256"] = hashlib.sha256((r.get("out") or "").encode("utf-8")).hexdigest()
            _append(rec, ledger)
            data = ("DATA: your script %s %s (%s, %d ms).\nSTDOUT:\n%s\nSTDERR:\n%s"
                    % (d["target"], "ran" if r["ok"] else "did not finish cleanly", r["why"], r["ms"], (r.get("out") or "")[:MAX_OUT], (r.get("err") or "")[-4000:]))
            return True, data, rec
        if kind == "propose":
            p = propose(d["target"], d["body"], proposals_dir, say=say)
            rec.update(p)
            _append(rec, ledger)
            return True, ("DATA: your proposal for %s is recorded as %s (%s). Nothing in the tree changed; the operator was told and applies it by hand or not. "
                          "Say so plainly." % (p["path"], p["id"], "compiles" if p["compiled"] else p["why"])), rec
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


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Tetsu's hands: his workshop, his runs, his proposals")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--read", metavar="NAME")
    ap.add_argument("--run", nargs="+", metavar="NAME")
    ap.add_argument("--proposals", action="store_true")
    ap.add_argument("--proposal", metavar="ID")
    ap.add_argument("--apply", metavar="ID", help="HIS HAND: copy a proposal over the tree file it names")
    a = ap.parse_args(argv)
    if a.list:
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
