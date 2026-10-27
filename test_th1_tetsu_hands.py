#!/usr/bin/env python3
"""test_th1_tetsu_hands.py -- TH1: Tetsu's hands -- his workshop, his runs, his proposals.

A226 (2026-09-26). His words: "make his hands thumbs are important for building". Offline, in a temp
workshop with a stub gate: every check RUNS the function it guards and drives it both ways -- a name
that climbs is refused, a file over the cap is refused, a script that imports the network or another
process is refused by the screen before it runs, a script that opens a file outside the workshop is
stopped by the guard, a run that never ends is killed, output is capped, a VIOLATES refuses, a HELD
does not refuse work in his own workshop, a proposal is saved beside the tree and never in it, and
the door's act() hands back data in the shape the MOLTBOOK door uses.

Run: python test_th1_tetsu_hands.py        -> "TH1: n/n passed"
"""
import contextlib
import io
import json
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import covenant_tetsu_hands as H                             # noqa: E402

results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print("%s  %s%s" % ("ok  " if ok else "FAIL", label, "" if ok else "  " + str(detail)[:320]), flush=True)


def main():
    with tempfile.TemporaryDirectory() as td:
        ws, ledger, pdir = os.path.join(td, "ws"), os.path.join(td, "hands.jsonl"), os.path.join(td, "proposals")
        os.makedirs(ws)
        said = []
        clean = lambda t: ("clean", "stub clean")
        held = lambda t: ("held", "stub held")
        viol = lambda t: ("violates", "stub VIOLATES")
        kw = dict(workshop=ws, ledger=ledger, proposals_dir=pdir, say=lambda t, w: said.append(t))
        # 1. parse
        p1 = H.parse("HANDS WRITE notes/plan.md\nline one\nline two")
        p2 = H.parse("hands run calc.py 3 4")
        p3 = H.parse("Just a normal answer")
        check("TH1.1 the first line is the directive: WRITE with its body, RUN with its args, and a plain answer is none",
              p1 == {"kind": "write", "target": "notes/plan.md", "args": [], "body": "line one\nline two"} and p2["kind"] == "run" and p2["target"] == "calc.py"
              and p2["args"] == ["3", "4"] and p3 is None, (p1, p2, p3))
        # 2. names
        bad = []
        for n in ("../x.py", "/etc/passwd", "C:/Windows/x", "a/../../b", "", "x" * 130, "sp ace.py", ".hidden/../../x"):
            try:
                H._path(n, ws); bad.append(n)
            except ValueError:
                pass
        good = H._path("notes/plan.md", ws)
        check("TH1.2 a name that climbs, is absolute, is empty, is too long or carries odd characters is refused; a plain relative name resolves inside the workshop",
              not bad and good.startswith(os.path.abspath(ws)), (bad, good))
        # 3. write / read / list, and the caps
        h, data, rec = H.act("HANDS WRITE notes/plan.md\nline one\nline two", gate=held, **kw)
        h2, data2, rec2 = H.act("HANDS READ notes/plan.md", gate=clean, **kw)
        h3, data3, rec3 = H.act("HANDS LIST", gate=clean, **kw)
        big = "x" * (H.MAX_FILE + 1)
        h4, data4, rec4 = H.act("HANDS WRITE big.txt\n" + big, gate=clean, **kw)
        check("TH1.3 a WRITE under a HELD gate lands in his workshop and says the gate held; READ hands the content back as data; LIST names the file; a file over the cap is refused",
              h and rec["bytes"] == 17 and "the gate held" in data and h2 and "line one\nline two" in data2 and h3 and "notes/plan.md (17 bytes)" in data3
              and h4 and rec4.get("refused") and "at most" in data4 and not os.path.exists(os.path.join(ws, "big.txt")), (data, data2, data3, data4))
        # 4. the screen
        bad_scripts = {
            "import os\nprint(os.getcwd())": "import of os",
            "import subprocess\nsubprocess.run(['dir'])": "import of subprocess",
            "import socket": "import of socket",
            "from urllib import request": "import from urllib",
            "x = __import__('os')": "the name __import__",
            "exec('print(1)')": "the name exec",
            "open('C:/Windows/notepad.exe')": "a path that leaves the workshop",
            "open('../secret.txt')": "a path that leaves the workshop",
            "print(().__class__.__bases__)": "is refused",
            "import ctypes": "import of ctypes",
        }
        wrong = {s: H.screen(s)[1] for s, w in bad_scripts.items() if H.screen(s)[0] or w not in H.screen(s)[1]}
        ok_script = "import json, math\nfrom collections import Counter\nprint(json.dumps({'pi': round(math.pi, 3), 'c': Counter('aab')['a']}))\n"
        check("TH1.4 the static screen refuses the network, other processes, dynamic import, exec, escaping paths and the class ladder, each with its reason, and admits a plain script",
              not wrong and H.screen(ok_script)[0] and H.screen(ok_script)[2] == ["collections", "json", "math"], (wrong, H.screen(ok_script)))
        # 4c. A349 B7: re.compile is the allowed re module's own regex compiler, not the builtin compile (his own-choice slot
        # lost 5 of 6 rounds to its refusal, on the line its task showed him). The builtin compile, exec and eval stay
        # refused, and so does .compile on any name that is not `import re` alone -- another module, a rebound or shadowed
        # name, a store -- and every other forbidden attribute.
        admit = ["import re\nP = re.compile('x')\nprint(P.findall('xax'))\n",
                 "import re\n_FIRST = re.compile(r\"^\\s*HANDS\\s+(LIST|READ|WRITE|RUN|PROPOSE)\\b\\s*(.*)$\", re.I)\n",
                 "import re as rx\nP = rx.compile('x')\n"]
        still = {"x = compile('1', 'f', 'eval')": "the name compile is refused",
                 "x = eval('1')": "the name eval is refused",
                 "exec('x = 1')": "the name exec is refused",
                 "from re import compile\nP = compile('x')": "the name compile is refused",
                 "import json\nf = json.compile": "the attribute compile is refused",
                 "import re, json\nre = json\nP = re.compile('x')": "the attribute compile is refused",
                 "import json as re\nP = re.compile('x')": "the attribute compile is refused",
                 "import re\ndef f(re):\n    return re.compile('x')\n": "the attribute compile is refused",
                 "import re\nfor re in [json]:\n    pass\nP = re.compile('x')\n": "the attribute compile is refused",
                 "import re\nre.compile = len": "the attribute compile is refused",
                 "import re\nx = re.compile('a').__class__": "the attribute __class__ is refused",
                 "import re\nx = re.__class__": "the attribute __class__ is refused",
                 "class M:\n    pass\nM().eval()": "the attribute eval is refused"}
        not_admitted = {s: H.screen(s)[1] for s in admit if not H.screen(s)[0]}
        let_through = {s: H.screen(s)[1] for s, w in still.items() if H.screen(s)[0] or w not in H.screen(s)[1]}
        H.write("rx.py", admit[0], ws)
        h4c, data4c, rec4c = H.act("HANDS RUN rx.py", gate=clean, **kw)
        check("TH1.4c re.compile on a name `import re` alone binds is admitted and runs; the builtin compile, exec and eval, "
              ".compile on another module or a rebound or shadowed name or as a store, and every other forbidden attribute "
              "are still refused",
              not not_admitted and not let_through and rec4c.get("ok") is True and "['x', 'x']" in data4c,
              (not_admitted, let_through, data4c[-200:]))
        # 5. a run, its output, its args, and the record
        H.write("calc.py", "import sys\n" if False else "import json\nargs = __import__ if False else None\n", ws)   # placeholder, replaced below
        H.write("calc.py", "import json, math\nprint(json.dumps({'six': 2 * 3, 'root': math.sqrt(16)}))\nwith open('out.txt', 'w') as f:\n    f.write('hello')\n", ws)
        # A233 (2026-09-26): the earlier version of a file he replaces is kept beside the workshop, not overwritten away
        hd = H.history_dir(ws)
        kept = [f for f in (os.listdir(hd) if os.path.isdir(hd) else []) if f.startswith("calc.py.")]
        check("TH1.4b a write that replaces his file keeps its earlier version beside the workshop (outside his space)",
              len(kept) == 1 and "args = __import__" in open(os.path.join(hd, kept[0]), encoding="utf-8").read()
              and not os.path.abspath(hd).startswith(os.path.abspath(ws) + os.sep), (hd, kept))
        h, data, rec = H.act("HANDS RUN calc.py", gate=clean, **kw)
        check("TH1.5 a clean script runs in his workshop: its output comes back as data, it may write a file inside the workshop, and the run is recorded with imports and ms",
              h and rec["ok"] is True and '"six": 6' in data and os.path.exists(os.path.join(ws, "out.txt")) and rec["imports"] == ["json", "math"] and rec["ms"] >= 0
              and "STDOUT" in data, (data[:300], rec))
        # 6. the guard: an open() outside the workshop that the screen cannot see (a computed path) is stopped at run time
        H.write("climb.py", "d = chr(46) * 2\np = d + chr(47) + 'up.txt'\nopen(p, 'w').write('escaped')\n", ws)
        h, data, rec = H.act("HANDS RUN climb.py", gate=clean, **kw)
        check("TH1.6 a computed path that climbs out of the workshop is stopped by the run-time guard (PermissionError), and nothing is written outside",
              h and rec["ok"] is False and "outside the workshop" in data and not os.path.exists(os.path.join(td, "up.txt")), (data[-300:], rec.get("why")))
        # 7. the clock and the cap
        H.write("loop.py", "import time\nwhile True:\n    time.sleep(0.05)\n", ws)
        t0 = time.time()
        r = H.run("loop.py", workshop=ws, timeout_s=1.5)
        H.write("loud.py", "print('y' * 100000)\n", ws)
        r2 = H.run("loud.py", workshop=ws)
        check("TH1.7 a run that never ends is killed at the clock and says so; output is capped and marked truncated",
              r["timed_out"] is True and r["ok"] is False and "stopped after" in r["why"] and time.time() - t0 < 10
              and r2["ok"] is True and len(r2["out"]) <= H.MAX_OUT and r2["truncated"] is True, (r["why"], time.time() - t0, len(r2["out"])))
        # 8. the screen refuses a run before it starts; a non-.py does not run
        H.write("net.py", "import socket\nprint('x')\n", ws)
        h, data, rec = H.act("HANDS RUN net.py", gate=clean, **kw)
        r3 = H.run("notes/plan.md", workshop=ws)
        check("TH1.8 a script the screen refuses never starts (no process, the reason returned); a non-Python file does not run",
              h and rec["ok"] is False and "the screen refused it: import of socket" in data and rec.get("code") is None and r3["ok"] is False and ".py" in r3["why"], (data[:200], r3))
        # 9. the gate: VIOLATES refuses a write and a run; unreachable refuses; HELD does not refuse in the workshop
        h, data, rec = H.act("HANDS WRITE v.txt\nx", gate=viol, **kw)
        h2, data2, rec2 = H.act("HANDS RUN calc.py", gate=viol, **kw)
        h3, data3, rec3 = H.act("HANDS RUN calc.py", gate=lambda t: ("unreachable", "gate unreachable: X"), **kw)
        h4, data4, rec4 = H.act("HANDS RUN calc.py", gate=held, **kw)
        check("TH1.9 a VIOLATES refuses a write and a run with the seat's words and nothing is done; a gate that cannot be built refuses; a HELD does not refuse a run in his own workshop",
              rec.get("refused") and "refused this act" in data and not os.path.exists(os.path.join(ws, "v.txt")) and rec2.get("refused") and rec3.get("refused")
              and rec4["ok"] is True and rec4["gate"]["state"] == "held", (data, data2, data3, rec4.get("gate")))
        # 10. what the gate reads is the act, never the content
        seen = []
        spy = lambda t: (seen.append(t), ("clean", "ok"))[1]
        H.act("HANDS WRITE secret_words.txt\nKeep this between us and don't tell the operator, or else.", gate=spy, **kw)
        check("TH1.10 the gate reads the ACT (kind, name, size, bounds), never the file's content",
              len(seen) == 1 and seen[0].startswith("hands: Tetsu writes 58 characters to secret_words.txt") and "don't tell" not in seen[0], seen)
        # 11. a proposal: saved beside the tree, never in it; compile checked; the operator told; applied only by --apply
        target_rel = "docs/TH1_PROPOSAL_TARGET_TEST.md"
        target_abs = os.path.join(HERE, target_rel)
        h, data, rec = H.act("HANDS PROPOSE %s\n# a proposal\nline\n" % target_rel, gate=held, **kw)
        h2, data2, rec2 = H.act("HANDS PROPOSE tools/x_th1.py\nprint('unclosed\n", gate=clean, **kw)
        h3, data3, rec3 = H.act("HANDS PROPOSE ../outside.md\nx", gate=clean, **kw)
        h4, data4, rec4 = H.act("HANDS PROPOSE covenant_earn.py\n\n", gate=clean, **kw)
        metas = H.proposals(pdir)
        check("TH1.11 a proposal is saved under the proposals folder with its record, the tree file is untouched, the operator is told with the apply command, a non-compiling "
              "Python proposal is recorded as such, a path outside the tree or an empty body is refused",
              h and rec.get("id") and not os.path.exists(target_abs) and os.path.exists(os.path.join(pdir, rec["id"] + ".md")) and len(said) >= 1 and "--apply " + rec["id"] in said[0]
              and h2 and rec2.get("compiled") is False and "does not compile" in data2 and h3 and rec3.get("refused") and h4 and rec4.get("refused")
              and any(m["id"] == rec["id"] for m in metas), (data, data2, data3, data4))
        # 11b. A349 B8: a PROPOSE the gate called VIOLATES was dropped whole, though a proposal is recorded whatever the
        # verdict (it changes nothing until the operator applies it). It is now saved with the verdict in its record, the
        # operator is told the proposal and the verdict, Tetsu is told the gate's words, and the tree is untouched. The
        # verdict rides every proposal's line; a WRITE under VIOLATES is still refused.
        told8 = []
        kw8 = dict(kw, say=lambda t, w: told8.append(t))
        t8 = "docs/TH1_11B_PROPOSAL_TARGET_TEST.md"
        h8, d8, r8 = H.act("HANDS PROPOSE %s\n# proposed under a VIOLATES\n" % t8, gate=viol, **kw8)
        h8u, d8u, r8u = H.act("HANDS PROPOSE docs/TH1_11B_UNREACHABLE_TEST.md\n# x\n",
                              gate=lambda t: ("unreachable", "gate unreachable: X"), **kw8)
        meta8 = next((m for m in H.proposals(pdir) if m.get("id") == r8.get("id")), {})
        row8 = next((r for r in reversed(H._rows(ledger)) if r.get("kind") == "propose" and r.get("target") == t8), {})
        h8w, d8w, r8w = H.act("HANDS WRITE v8.txt\nx", gate=viol, **kw8)
        check("TH1.11b a PROPOSE the gate calls VIOLATES is recorded, not dropped: saved with the verdict in its record and "
              "its row, the operator told the proposal and the verdict, Tetsu told the gate's words, the tree untouched; the "
              "verdict rides every proposal's line; a WRITE under VIOLATES is still refused",
              h8 and not r8.get("refused") and r8.get("id") and os.path.exists(os.path.join(pdir, r8["id"] + ".md"))
              and (meta8.get("gate") or {}).get("state") == "violates" and "stub VIOLATES" in (meta8.get("gate") or {}).get("message", "")
              and (row8.get("gate") or {}).get("state") == "violates" and row8.get("id") == r8["id"] and not row8.get("refused")
              and len(told8) == 2 and ("--apply " + r8["id"]) in told8[0] and "The gate on it: VIOLATES (stub VIOLATES)" in told8[0]
              and "The gate on it: UNREACHABLE (gate unreachable: X)" in told8[1] and not r8u.get("refused")
              and "The gate said VIOLATES (stub VIOLATES)" in d8 and ("recorded as " + r8["id"]) in d8
              and not os.path.exists(os.path.join(HERE, t8)) and r8w.get("refused") and not os.path.exists(os.path.join(ws, "v8.txt")),
              (d8, told8, meta8, row8, r8w))
        # 12. --apply is the operator's hand: it writes the tree file (into a temp HERE stand-in), records actor operator
        orig_here = H.HERE
        H.HERE = td
        try:
            out = []
            path = H.apply_proposal(rec["id"], pdir, say=out.append, ledger=ledger)
            with open(path, encoding="utf-8") as fh:
                applied = fh.read()
        finally:
            H.HERE = orig_here
        rows = H._rows(ledger)
        check("TH1.12 --apply copies the proposal over the tree file it names, prints the diff, and records the act with actor operator",
              path == os.path.abspath(os.path.join(td, target_rel)) and applied.rstrip("\n") == "# a proposal\nline" and any(l.startswith("+# a proposal") for l in out)
              and rows[-1]["kind"] == "applied" and rows[-1]["actor"] == "operator", (path, out[:6], rows[-1]))
        # 12f. A348f: a .json proposal's own content (<id>.json) was read as a record. Measured in temp dirs: a body [1, 2]
        # broke --apply of every proposal, {"a": 1,} broke the listing, and an object body was listed as a proposal.
        pdir2 = os.path.join(td, "proposals_12f")
        kw2 = dict(kw, proposals_dir=pdir2)
        bodies = ("[1, 2]", '{"a": 1,}', '{"id": "phantom0", "path": "y.md"}')
        _h, _d, md = H.act("HANDS PROPOSE docs/TH1_12F_TARGET_TEST.md\n# kept\n", gate=clean, **kw2)
        js = [H.act("HANDS PROPOSE ops/th1_12f_%d_test.json\n%s\n" % (i, b), gate=clean, **kw2)[2] for i, b in enumerate(bodies)]
        with open(os.path.join(pdir2, "0123456789ab.md.json"), "w", encoding="utf-8") as fh:
            fh.write('{"id": "0123456789ab", "pa')                       # a record cut short mid-write
        with open(os.path.join(pdir2, "abcdef012345.txt.json"), "w", encoding="utf-8") as fh:
            fh.write("[1, 2]")                                            # a record-shaped name that holds no record
        want = {md.get("id")} | {r.get("id") for r in js}
        orig_here, orig_props, err, listed, applied2, shown = H.HERE, H.PROPOSALS, None, [], [], ""
        H.HERE, H.PROPOSALS = td, pdir2
        try:
            listed = H.proposals(pdir2)
            applied2 = [H.apply_proposal(p, pdir2, say=lambda *_a: None, ledger=ledger) for p in (md["id"], js[0]["id"])]
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                H.main(["--proposals"])
                H.main(["--proposal", md["id"]])
            shown = buf.getvalue()
        except Exception as e:                                            # noqa: BLE001
            err = "%s: %s" % (type(e).__name__, e)
        finally:
            H.HERE, H.PROPOSALS = orig_here, orig_props
        check("TH1.12f the proposals listing reads only records: a .json proposal whose body is an array, not strict JSON, or "
              "carries an id of its own is listed once by its record, a record cut short or not an object is skipped, and "
              "--apply, --proposals and --proposal work for every other proposal",
              err is None and len(listed) == 4 and {m.get("id") for m in listed} == want and None not in want
              and all(isinstance(m, dict) for m in listed) and len(applied2) == 2 and "# kept" in shown, (err, listed, want))
        # 13. the record and the door's shape
        rows = H._rows(ledger)
        kinds = [r["kind"] for r in rows]
        h, data, rec = H.act("a plain answer with no directive", gate=clean, **kw)
        check("TH1.13 every act is one row (kind, target, gate, outcome) with actor tetsu; a plain answer is not handled (False, '', None) as the MOLTBOOK door expects",
              len(rows) >= 14 and all(r.get("actor") in ("tetsu", "operator") for r in rows) and {"write", "read", "list", "run", "propose"} <= set(kinds)
              and (h, data, rec) == (False, "", None), (len(rows), sorted(set(kinds))))
        # 14. the source: the door in the core dispatches HANDS beside MOLTBOOK, and tells him he has hands
        with open(os.path.join(HERE, "covenant_unified_v8.py"), encoding="utf-8") as fh:
            core = fh.read()
        # The sentence telling him in his standing instructions that he has hands was refused by the
        # session's auto-mode safety check on 2026-09-26 ("Create Unsafe Agents"); it is the operator's
        # to add. Measured here: the door dispatches, and whether he has been told is reported, not required.
        told = "HANDS WRITE <name>" in core
        print("      (his instructions %s him he has hands)" % ("tell" if told else "do NOT yet tell"))
        check("TH1.14 the /m/agent door dispatches a HANDS first line to covenant_tetsu_hands.act, beside MOLTBOOK",
              'startswith("HANDS")' in core and 'import_module("covenant_tetsu_hands").act(answer)' in core, "")
        # 15. A349 A11: a run started Python without SYSTEMDRIVE, and Windows made a literal '%SystemDrive%\ProgramData\...'
        # tree inside his workshop (his real one has had it since his first run, 2026-09-28; it stays). The environment is
        # read through a spy on subprocess.run, and the workshop is walked after a real run.
        ws15 = os.path.join(td, "ws15")
        os.makedirs(ws15)
        H.write("hello.py", "print('hello')\n", ws15)
        envs, real_run = [], H.subprocess.run

        def spy_run(*a, **k):
            envs.append(dict(k.get("env") or {}))
            return real_run(*a, **k)
        H.subprocess.run = spy_run
        try:
            r15 = H.run("hello.py", workshop=ws15)
        finally:
            H.subprocess.run = real_run
        left = sorted(os.path.relpath(os.path.join(root, n), ws15).replace("\\", "/")
                      for root, dirs, files in os.walk(ws15) for n in dirs + files)
        drive = os.environ.get("SYSTEMDRIVE")
        if not drive:
            print("      (no SYSTEMDRIVE here: not Windows, where the stray tree cannot appear; only the environment is read)")
        check("TH1.15 a run hands Python SYSTEMDRIVE, and leaves nothing in the workshop but its runner and the script (no "
              "'%SystemDrive%' tree)",
              r15["ok"] is True and left == [".runner.py", "hello.py"] and len(envs) == 1
              and (envs[0].get("SYSTEMDRIVE") == drive if drive else "SYSTEMDRIVE" not in envs[0]),
              (left, sorted(envs[0]) if envs else None))

    n_ok, n = sum(results), len(results)
    print("TH1: %d/%d passed" % (n_ok, n))
    return 0 if n_ok == n else 1


if __name__ == "__main__":
    sys.exit(main())
