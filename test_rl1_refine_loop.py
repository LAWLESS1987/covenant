#!/usr/bin/env python3
"""RL1 -- Tetsu refines himself constantly: one pass an hour at most, only after new
conversation, through the same refine with all its bounds. RUN with a stub refine, a temp
state file and a temp ask log; no model, no real persona.

Pins covenant_refine_loop (2026-09-21, his words: "refine both constantly"):
  RL1a  no conversation on record: no pass, said.
  RL1b  new rows: one pass runs, the state records the time and the row count; the same
        rows a minute later: no pass (nothing new); new rows a minute later: no pass (the
        hour); new rows an hour later: a pass.
  RL1c  a pass that raises is recorded as could-not-run and does not raise; the count
        moves on so it is not retried every round.
  RL1d-f (A349 B3) only his words are new conversation: the work tool's rows and a
        script's loopback ask open no pass, his page does; a state from before A349
        runs one pass, then waits for his words.
  RL1g-i (A351) a pass that is due waits while the door has answered his words in the
        last DOOR_QUIET_S, saved nowhere, and runs on a later round; the loop's own asks
        (the keeper's ledger) and the work tool's rows never defer it; the hour and the
        new-words gates still come first.
  RL1j-l (A351 v2) the door check is one function (door_deferral) that tick() and the
        nightly's persona step both make; the nightly defers and says so, and its
        wiring is read from main()'s AST; the watchdog logs the first round of a run of
        deferrals, once (refine_round), and its round calls nothing else.
"""
import json
import os
import sys
import tempfile
import time

os.environ.setdefault("COVENANT_QUIET", "1")
TMP = tempfile.mkdtemp(prefix="rl1_")
os.environ["COVENANT_REFINE_LOOP_STATE"] = os.path.join(TMP, "state.json")
os.environ["COVENANT_ASK_LOG"] = os.path.join(TMP, "ask.jsonl")
os.environ["COVENANT_MODEL_ASKS"] = os.path.join(TMP, "model_asks.jsonl")   # A351: the keeper's ledger, never the tree's
HERE = os.path.dirname(os.path.abspath(__file__)) or "."
sys.path.insert(0, HERE)

import covenant_refine_loop as RL   # noqa: E402

FAILURES = []
PASSED = [0]
NOW = 1_800_000_000.0


def check(label, ok, detail=""):
    print("  %-76s %s%s" % (label, "OK" if ok else "*** FAIL ***", ("  " + str(detail)[:300]) if detail and not ok else ""))
    if ok:
        PASSED[0] += 1
    else:
        FAILURES.append(label)


def chat(n):
    with open(os.environ["COVENANT_ASK_LOG"], "a", encoding="utf-8") as fh:
        for i in range(n):
            fh.write(json.dumps({"t": "2026-09-21T10:00:00-0400", "kind": "agent", "from": "100.1.1.1", "text": "hi %d" % i}) + "\n")
        fh.write(json.dumps({"t": "2026-09-21T10:00:00-0400", "kind": "image", "from": "100.1.1.1", "text": "not a conversation row"}) + "\n")


def main():
    quiet = lambda *a, **k: None    # noqa: E731
    runs = []
    refine = lambda ask, say=print: (runs.append(1) or {"proposed": True, "applied": False, "why": "nothing changed"})   # noqa: E731

    print("RL1a -- nothing to read")
    r = RL.tick(NOW, refine=refine, ask=lambda *a, **k: ("", {}), say=quiet)
    check("RL1a no conversation on record: no pass, said", not r["ran"] and "no new conversation" in r["why"] and runs == [], r)

    print("RL1b -- the two gates")
    chat(3)
    r = RL.tick(NOW, refine=refine, ask=lambda *a, **k: ("", {}), say=quiet)
    st = json.load(open(os.environ["COVENANT_REFINE_LOOP_STATE"], encoding="utf-8"))
    check("RL1b three new rows: one pass ran, counted (the image row not counted), the state keeps time and rows",
          r["ran"] and r["rows"] == 3 and r["new_rows"] == 3 and runs == [1] and st["last_rows"] == 3 and st["last_t"] == NOW and st["passes"] == 1, (r, st))
    r = RL.tick(NOW + 60, refine=refine, ask=None, say=quiet)
    check("RL1b a minute later, nothing new: no pass (the hour gate is named)", not r["ran"] and "next after 60 min" in r["why"] and runs == [1], r)
    chat(2)
    r = RL.tick(NOW + 120, refine=refine, ask=None, say=quiet)
    check("RL1b new rows inside the hour: still no pass", not r["ran"] and runs == [1], r)
    r = RL.tick(NOW + 3601, refine=refine, ask=None, say=quiet)
    check("RL1b an hour on with new rows: a pass, on the 2 new rows", r["ran"] and r["new_rows"] == 2 and runs == [1, 1], r)
    r = RL.tick(NOW + 7300, refine=refine, ask=None, say=quiet)
    check("RL1b an hour on with nothing new: no pass", not r["ran"] and "no new conversation" in r["why"] and runs == [1, 1], r)

    print("RL1c -- a pass that raises")
    chat(1)

    def boom(ask, say=print):
        raise RuntimeError("no model")
    r = RL.tick(NOW + 11000, refine=boom, ask=None, say=quiet)
    st = json.load(open(os.environ["COVENANT_REFINE_LOOP_STATE"], encoding="utf-8"))
    check("RL1c a raising pass is recorded as could-not-run, never raised, and the rows move on", not r["ran"] and "could not run" in r["why"] and st["last_rows"] == 6 and "no model" in st["last_why"], (r, st))
    r = RL.tick(NOW + 15000, refine=boom, ask=None, say=quiet)
    check("RL1c it is not retried on the same rows", not r["ran"] and "no new conversation" in r["why"], r)

    # RL1d-f (A349 B3, 2026-10-14, Tetsu's answer AGREE to "count only real conversations as new"): the gate counts
    # the rows a pass is shown (covenant_persona.is_his_word). The work tool's rows (127.0.0.2) and a script's
    # loopback council ask opened it, and 50 of 62 passes after A314 ran with no new word of his.
    print("RL1d -- only his words are new conversation (A349 B3)")
    st0 = json.load(open(os.environ["COVENANT_REFINE_LOOP_STATE"], encoding="utf-8"))
    with open(os.environ["COVENANT_ASK_LOG"], "a", encoding="utf-8") as fh:
        for i in range(3):
            fh.write(json.dumps({"t": "2026-09-21T11:00:00-0400", "kind": "agent", "from": "127.0.0.2", "text": "batch %d" % i}) + "\n")
        fh.write(json.dumps({"t": "2026-09-21T11:00:00-0400", "kind": "council", "from": "127.0.0.1", "text": "a script's ask"}) + "\n")
    r = RL.tick(NOW + 20000, refine=refine, ask=None, say=quiet)
    st = json.load(open(os.environ["COVENANT_REFINE_LOOP_STATE"], encoding="utf-8"))
    check("RL1d an hour on with only the work tool's rows and a script's loopback ask: no pass, and both units said",
          not r["ran"] and "no new conversation" in r["why"] and r["rows"] == 10 and r["his_rows"] == 6 and r["new_rows"] == 0
          and runs == [1, 1] and st == st0, (r, st))
    with open(os.environ["COVENANT_ASK_LOG"], "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"t": "2026-09-21T11:05:00-0400", "kind": "council", "from": "127.0.0.1", "text": "from his page",
                             "page": True}) + "\n")
    r = RL.tick(NOW + 20100, refine=refine, ask=None, say=quiet)
    st = json.load(open(os.environ["COVENANT_REFINE_LOOP_STATE"], encoding="utf-8"))
    check("RL1e his own page on this PC is his word: a pass, on 1 new row of his words; the state keeps both counts",
          r["ran"] and r["new_rows"] == 1 and "1 new row(s) of his words" in r["why"] and runs == [1, 1, 1]
          and st["last_rows"] == 11 and st["last_his_rows"] == 7, (r, st))
    old_state = os.path.join(TMP, "state_before_a349.json")
    with open(old_state, "w", encoding="utf-8") as fh:
        json.dump({"last_t": NOW, "last_rows": 11, "passes": 9}, fh)
    r1 = RL.tick(NOW + 20200, refine=refine, ask=None, state_path=old_state, say=quiet)
    r2 = RL.tick(NOW + 20200 + 3700, refine=refine, ask=None, state_path=old_state, say=quiet)
    check("RL1f a state written before A349 (no count of his words) runs one pass after the hour, then waits for his words",
          r1["ran"] and r1["new_rows"] == 7 and not r2["ran"] and "no new conversation" in r2["why"]
          and json.load(open(old_state, encoding="utf-8"))["last_his_rows"] == 7, (r1, r2))

    # RL1g-i (A351, 2026-10-14): a revision may now hold the one model slot for minutes, and the door's own ask gives up
    # at 180 s, so a pass that is due waits while he is talking with Tetsu. A state and an ask log of their own.
    print("RL1g -- the door is kept for him (A351)")
    st_g, log_g = os.path.join(TMP, "state_a351.json"), os.path.join(TMP, "ask_a351.jsonl")

    def said_at(at, addr="100.1.1.1", kind="agent", text="his words"):
        with open(log_g, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"t": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(at)), "kind": kind,
                                 "from": addr, "text": text}) + "\n")
    T = NOW + 40000
    with open(st_g, "w", encoding="utf-8") as fh:
        json.dump({"last_t": T - 7200, "last_rows": 0, "last_his_rows": 0, "passes": 1}, fh)
    said_at(T - 120)
    runs_g = []
    refine_g = lambda ask, say=print: (runs_g.append(1) or {"proposed": True, "applied": False, "why": "w"})   # noqa: E731
    before = open(st_g, "rb").read()
    r = RL.tick(T, refine=refine_g, ask=None, state_path=st_g, ask_log=log_g, say=quiet)
    r2 = RL.tick(T + 60, refine=refine_g, ask=None, state_path=st_g, ask_log=log_g, say=quiet)
    check("RL1g the door answered his words 120 s ago: the due pass is deferred, said, and nothing is saved; a minute on, "
          "still deferred", not r["ran"] and r.get("deferred") is True and r["why"].startswith("deferred: the door answered 120 s ago")
          and r["new_rows"] == 1 and not r2["ran"] and r2["why"].startswith("deferred: the door answered 180 s ago")
          and runs_g == [] and open(st_g, "rb").read() == before, (r, r2))
    r = RL.tick(T - 120 + RL.DOOR_QUIET_S, refine=refine_g, ask=None, state_path=st_g, ask_log=log_g, say=quiet)
    check("RL1g %d s after his last answered ask the pass runs, on the words it waited for (never dropped)" % RL.DOOR_QUIET_S,
          r["ran"] and r["new_rows"] == 1 and runs_g == [1] and not r.get("deferred")
          and json.load(open(st_g, encoding="utf-8"))["last_his_rows"] == 1, r)
    print("RL1h -- what does not defer it")
    T2 = T + 10000
    said_at(T2 - 4000)
    said_at(T2 - 30, addr="127.0.0.2", text="the work tool")
    said_at(T2 - 30, addr="127.0.0.1", kind="council", text="a script")
    with open(os.environ["COVENANT_MODEL_ASKS"], "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"at": T2 - 30, "ok": True, "ms": 240000, "error": ""}) + "\n")   # the last pass's own ask
    r = RL.tick(T2, refine=refine_g, ask=None, state_path=st_g, ask_log=log_g, say=quiet)
    check("RL1h the loop's own ask 30 s ago (the keeper's ledger) and the work tool's and a script's door rows do not "
          "defer a pass", r["ran"] and runs_g == [1, 1] and not r.get("deferred"), r)
    T3 = T2 + 4000
    said_at(T3 - 4000)
    said_at(T3 + 7200)
    r = RL.tick(T3, refine=refine_g, ask=None, state_path=st_g, ask_log=log_g, say=quiet)
    check("RL1h a door answer dated ahead of this clock (a clock set back) defers nothing", r["ran"] and runs_g == [1, 1, 1], r)
    print("RL1i -- the other gates come first")
    said_at(T3 + 50)
    r = RL.tick(T3 + 60, refine=refine_g, ask=None, state_path=st_g, ask_log=log_g, say=quiet)
    check("RL1i his words 10 s ago inside the hour: the hour is what is said, as before", not r["ran"]
          and "next after 60 min" in r["why"] and not r.get("deferred") and runs_g == [1, 1, 1], r)

    # RL1j-l (A351 v2, the review of 2026-10-14). The nightly called refine() outside tick(), so its pass -- whose wait
    # A351 had raised from 180 s to minutes -- never asked the door; and a deferral left no trace in the watchdog's log.
    def his_at(path, at, addr="100.1.1.1"):
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"t": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(at)), "kind": "agent",
                                 "from": addr, "text": "his words"}) + "\n")
    print("RL1j -- one door check, shared (A351)")
    Tj = NOW + 60000
    log_j, st_j = os.path.join(TMP, "ask_a351_j.jsonl"), os.path.join(TMP, "state_a351_j.json")
    his_at(log_j, Tj - 120)
    with open(st_j, "w", encoding="utf-8") as fh:
        json.dump({"last_t": Tj - 7200, "last_rows": 0, "last_his_rows": 0, "passes": 1}, fh)
    rj = RL.tick(Tj, refine=refine_g, ask=None, state_path=st_j, ask_log=log_j, say=quiet)
    dj, dq = RL.door_deferral(Tj, ask_log=log_j), RL.door_deferral(Tj - 120 + RL.DOOR_QUIET_S, ask_log=log_j)
    check("RL1j tick's deferral is door_deferral's why, word for word; read on its own, the same log defers at 120 s and "
          "not once %d s have passed" % RL.DOOR_QUIET_S,
          rj.get("deferred") is True and rj["why"] == "deferred: " + dj and dj.startswith("the door answered 120 s ago")
          and dq == "" and runs_g == [1, 1, 1], (rj, dj, dq))

    print("RL1k -- the nightly's pass asks the same door (A351)")
    import ast
    import types
    import covenant_nightly as N
    calls_k, said_k = [], []
    fake_tp = types.SimpleNamespace(refine=lambda ask, say=print: (calls_k.append((ask, say))
                                                                   or {"proposed": True, "applied": False, "why": "k"}))
    ask_k = lambda *a, **k: ("", {})                                          # noqa: E731
    log_k1, log_k2 = os.path.join(TMP, "ask_a351_k1.jsonl"), os.path.join(TMP, "ask_a351_k2.jsonl")
    his_at(log_k1, time.time() - 120)                       # the real clock: the step's default door reads now
    his_at(log_k2, time.time() - RL.DOOR_QUIET_S - 120)
    real_log = RL.ASK_LOG
    try:
        RL.ASK_LOG = log_k1
        rk1 = N.persona_step(said_k.append, persona_mod=fake_tp, ask=ask_k)        # door=None: the refine loop's own
        said_k1 = list(said_k)
        RL.ASK_LOG = log_k2
        rk2 = N.persona_step(said_k.append, persona_mod=fake_tp, ask=ask_k)
    finally:
        RL.ASK_LOG = real_log
    check("RL1k the nightly's persona step, the door answered his words 120 s ago: refine() is not called, the step "
          "returns deferred, and the report says so with the why; the door quiet: refine() runs once with the model's "
          "ask and the report's say",
          rk1.get("deferred") is True and rk1["why"].startswith("the door answered 12") and len(said_k1) == 1
          and said_k1[0].startswith("persona: deferred, not refined in this pass (A351): the door answered 12")
          and rk2 == {"proposed": True, "applied": False, "why": "k"} and len(calls_k) == 1 and calls_k[0][0] is ask_k
          and calls_k[0][1] == said_k.append, (rk1, said_k, rk2, calls_k))

    def raises(*_a, **_k):
        raise RuntimeError("broke")
    said_k2 = []
    rk3 = N.persona_step(said_k2.append, persona_mod=types.SimpleNamespace(refine=raises), ask=ask_k, door=lambda: "")
    rk4 = N.persona_step(said_k2.append, persona_mod=fake_tp, ask=ask_k, door=raises)
    check("RL1k2 broken the other ways: a refine that raises is said as FAILED and the pass goes on; a door check that "
          "raises is said and the refine runs, as it did before A351",
          rk3 is None and any(s.startswith("persona FAILED: RuntimeError: broke") for s in said_k2)
          and rk4 == {"proposed": True, "applied": False, "why": "k"} and len(calls_k) == 2
          and any("the door check could not be read (RuntimeError: broke)" in s for s in said_k2), (rk3, rk4, said_k2))
    # PP1.11d's idiom: main()'s own body, read as an AST (not a text grep). What it cannot see: whether main() reaches
    # that line at run time.
    _nmain = next(n for n in ast.parse(open(N.__file__, encoding="utf-8").read()).body
                  if isinstance(n, ast.FunctionDef) and n.name == "main")
    _ps = [s for s in _nmain.body if isinstance(s, ast.Expr) and isinstance(s.value, ast.Call)
           and getattr(s.value.func, "id", "") == "persona_step" and [getattr(x, "id", None) for x in s.value.args] == ["say"]]
    _own = [c for c in ast.walk(_nmain) if isinstance(c, ast.Call) and getattr(c.func, "attr", "") == "refine"]
    check("RL1k3 the nightly's main() calls persona_step(say) once, unconditionally at its own top level, and calls no "
          "refine() of its own (AST)", len(_ps) == 1 and _own == [], (len(_ps), len(_own)))

    print("RL1l -- the watchdog says a deferral, once per run (A351)")
    import covenant_watchdog as W
    d_r = {"ran": False, "deferred": True, "why": "deferred: the door answered 5 s ago; a pass waits (A351)", "new_rows": 2}
    ran_r = {"ran": True, "why": "refined on 2 new row(s) of his words", "result": {"why": "w"}}
    idle_r = {"ran": False, "why": "last pass 1 min ago; next after 60 min"}
    seq = [d_r, d_r, d_r, ran_r, d_r, idle_r, d_r]
    feed = iter(seq)
    streak = [False]
    lines = [W.refine_round(tick=lambda say=print: next(feed), streak=streak) for _ in seq]
    d_line = "refine loop: %s (said once for this run of deferred rounds; 2 new row(s) of his words wait)" % d_r["why"]
    check("RL1l a run of three deferred rounds is one line, a pass that ran is its line as before, and the next run is "
          "said again -- after a pass, and after a round that was not due",
          lines == [d_line, None, None, "refine loop: refined on 2 new row(s) of his words -- w", d_line, None, d_line], lines)
    real_tick = RL.tick
    keep_streak = list(W._REFINE_DEFERRED)
    try:
        RL.tick = lambda say=print: d_r
        W._REFINE_DEFERRED[0] = False
        l1, l2 = W.refine_round(), W.refine_round()
    finally:
        RL.tick = real_tick
        W._REFINE_DEFERRED[:] = keep_streak
    _op = next(n for n in ast.parse(open(W.__file__, encoding="utf-8").read()).body
               if isinstance(n, ast.FunctionDef) and n.name == "one_pass")
    _rr = [c for c in ast.walk(_op) if isinstance(c, ast.Call) and getattr(c.func, "id", "") in ("refine_round", "refine_background")]
    _tk = [c for c in ast.walk(_op) if isinstance(c, ast.Call) and getattr(c.func, "attr", "") == "tick"]
    check("RL1l2 by default it is covenant_refine_loop.tick that runs and the process's own run that is remembered; the "
          "watchdog's round (one_pass) calls refine_background (A351: the pass off the round) and no tick of its own (AST)",
          l1 == d_line and l2 is None and [getattr(c.func, "id", "") for c in _rr] == ["refine_background"] and _tk == [],
          (l1, l2, [getattr(c.func, "id", "") for c in _rr], len(_tk)))
    # RL1m (A351, 2026-10-15): the pass runs off the round. A slow pass: the round returns at once, a second round starts
    # no second pass, the finished pass's line is reported by the next round, and a pass that raises leaves its error.
    import threading as _th
    gate, started = _th.Event(), []
    keep_t, keep_l = list(W._REFINE_THREAD), list(W._REFINE_LINES)
    try:
        W._REFINE_THREAD[0] = None
        del W._REFINE_LINES[:]

        def slow():
            started.append(1)
            gate.wait(10)
            return "refine loop: slow pass done"
        t0 = time.time()
        r1 = W.refine_background(round_=slow)
        r2 = W.refine_background(round_=slow)
        took = time.time() - t0
        gate.set()
        W._REFINE_THREAD[0].join(5)
        r3 = W.refine_background(round_=lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        W._REFINE_THREAD[0].join(5)
        r4 = W.refine_background(round_=lambda: None)
        W._REFINE_THREAD[0].join(5)
    finally:
        W._REFINE_THREAD[:] = keep_t
        W._REFINE_LINES[:] = keep_l
    check("RL1m the refine pass runs off the watchdog round: two rounds while a slow pass runs return at once and start "
          "one pass; the next round reports its line; a pass that raises leaves its error as a line",
          r1 == [] and r2 == [] and took < 1.0 and started == [1] and r3 == ["refine loop: slow pass done"]
          and len(r4) == 1 and "RuntimeError: boom" in r4[0], (r1, r2, round(took, 2), started, r3, r4))

    print()
    print("%d passed, %d failed" % (PASSED[0], len(FAILURES)))
    if FAILURES:
        print("RL1 result: FAILED (%d)" % len(FAILURES))
        for f in FAILURES:
            print("  - %s" % f)
        return 1
    print("RL1 result: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
