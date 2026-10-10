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
  FC8     tetsu_update's default ask is the same fresh path
  FC9     tools/tetsu_work.ask over a real socket: "fresh": true in the body only when asked, from 127.0.0.2
  FC10    every in-tree caller of tools/tetsu_work.ask (found by walking the tree and parsing it) is
          declared, a "fresh" one passes fresh=True, and a declaration with no caller left is stale;
          FC10n drives the same walker over a synthetic undeclared caller and must flag it

Nothing here touches the real ask log, teacher queue, grant, ledgers or model: paths are redirected, the
model is a recorder, the socket server is this suite's own.
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


def main():
    print("A284 -- Tetsu's reviews and round updates are read on their own")
    os.environ["COVENANT_MODEL_STUB"] = "1"
    os.environ["COVENANT_TETSU_IMMUNITY"] = tempfile.mktemp(suffix="_a284_no_immunity.json")
    os.environ["COVENANT_TETSU_IMMUNITY_LEDGER"] = tempfile.mktemp(suffix="_a284_immunity.jsonl")
    os.environ["COVENANT_PAUSE_DIR"] = tempfile.mkdtemp(prefix="a284_pause_")
    d = tempfile.mkdtemp(prefix="a284_")
    LOG = os.environ["COVENANT_ASK_LOG"] = os.path.join(d, "ask_log.jsonl")
    QUEUE = os.environ["COVENANT_TEACHER_QUEUE"] = os.path.join(d, "teacher_queue.jsonl")
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

        import covenant_free_will as FW
        reply[0] = {"status": "success", "answer": "TELL: someone wrote back", "fresh": True}
        calls.clear()
        told = []
        u = FW.tetsu_update({"replied": 1}, [], (), tell=lambda *a: told.append(a) or True,
                            log_path=os.path.join(d, "updates.jsonl"))
        check("FC8 tetsu_update's default ask is the same fresh path, and its decision is read as before",
              u and u.get("decision") == "TELL" and told and calls and all(c["fresh"] is True for c in calls),
              (u, calls))
    finally:
        TWpkg.ask = real_tw

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

    ok = sum(results)
    print("\nA284: %d/%d passed" % (ok, len(results)))
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
