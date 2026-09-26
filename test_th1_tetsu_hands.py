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
        # 5. a run, its output, its args, and the record
        H.write("calc.py", "import sys\n" if False else "import json\nargs = __import__ if False else None\n", ws)   # placeholder, replaced below
        H.write("calc.py", "import json, math\nprint(json.dumps({'six': 2 * 3, 'root': math.sqrt(16)}))\nwith open('out.txt', 'w') as f:\n    f.write('hello')\n", ws)
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

    n_ok, n = sum(results), len(results)
    print("TH1: %d/%d passed" % (n_ok, n))
    return 0 if n_ok == n else 1


if __name__ == "__main__":
    sys.exit(main())
