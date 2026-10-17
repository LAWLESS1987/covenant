#!/usr/bin/env python3
"""MK1 -- the model keeper steps UP to the largest model that fits once the running one is
counted as reclaimable, never down, never on a guess. RUN with the keeper's readings stubbed
and a temp models directory; no server is started.

Pins covenant_model.step_up (2026-09-21, his words: "we need to rapidly make up the gap in
ai"; measured that day: 15.3 GB RAM, 4.8 free with the 3B holding 2.0, the 7B needing 6.0 --
so the 7B fit only once the 3B was put away, which the plain pick never saw).

MK1o (A351, 2026-10-14): no wait the keeper does not keep is handed out -- time_needed is cut to wait_cap (IDLE_S less
one watcher round), driven through the real ask() and the real idle watcher against a slow loopback stand-in, its
clocks scaled 1/150, both ways (MK1o4 hands the uncut wait by hand and sees the keeper cut it).
"""
import json
import math
import os
import sys
import tempfile

os.environ.setdefault("COVENANT_QUIET", "1")
HERE = os.path.dirname(os.path.abspath(__file__)) or "."
sys.path.insert(0, HERE)

import covenant_model as M   # noqa: E402

FAILURES = []
PASSED = [0]


def check(label, ok, detail=""):
    print("  %-76s %s%s" % (label, "OK" if ok else "*** FAIL ***", ("  " + str(detail)[:300]) if detail and not ok else ""))
    if ok:
        PASSED[0] += 1
    else:
        FAILURES.append(label)


def mk1o():
    """MK1o (A351, the review of 2026-10-14): a wait the keeper does not keep is never handed out. A351 gave Tetsu's
    revision a wait sized to its answer (time_needed: 751 s for his register at the floor speeds), and the keeper's
    idle watcher stops the server IDLE_S (600 s) after the last marked use -- an ask marks use when it starts and when
    it is answered, not while it waits -- so a 751 s wait was cut at 601.3 s. time_needed now cuts every wait to
    wait_cap (IDLE_S less one watcher round). Driven here: the REAL ask() and the REAL watcher thread (_watch_idle,
    running the real _idle_tick each round) against a slow stand-in llama-server on loopback, the keeper's clocks
    scaled 1/150 (IDLE_S 600 s -> 4 s, its 30 s round -> 0.2 s, the 180 s floor -> 1.2 s). start() is a stand-in and
    stop() a recorder that drops the stand-in's answer in flight, as ending llama-server would; the shared stamp and the
    ledger are in a temp directory; nothing else is reached."""
    import http.server
    import socket
    import threading
    import time as _t
    scale = 150.0
    tmp = tempfile.mkdtemp(prefix="mk1o_")
    names = ("IDLE_S", "IDLE_ROUND_S", "ASK_TIMEOUT_S", "PORT", "start", "stop", "alive", "_read_state", "USED", "ASKS")
    keep = {k: getattr(M, k) for k in names}
    keep_last, stub_env = M._last_used[0], os.environ.pop("COVENANT_MODEL_STUB", None)
    small = M.CANDIDATES[-1][0]                                   # a rung in ALWAYS_ANSWER: never put away for pressure
    sv = {"delay": 0.0, "stopped": False, "in_flight": False, "stops": []}

    class Slow(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers.get("Content-Length") or 0))
            end = _t.time() + sv["delay"]
            while _t.time() < end:
                if sv["stopped"]:                                 # the server was ended: the answer never comes
                    try:
                        self.connection.shutdown(socket.SHUT_RDWR)
                    except OSError:
                        pass
                    return
                _t.sleep(0.01)
            body = json.dumps({"choices": [{"message": {"content": "ok"}}], "usage": {"completion_tokens": 9}}).encode()
            try:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except OSError:                                       # the asker gave up first
                pass

        def log_message(self, *_a):
            pass

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Slow)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    def rec_stop(say=print):
        sv["stops"].append((_t.time(), sv["in_flight"]))
        sv["stopped"] = True
        return True, "stopped"

    def one(delay, timeout):
        """One ask through the real ask() with the real watcher armed; returns what happened, after the watcher's own
        round has ended (it ends when it stops the server)."""
        sv.update(delay=delay, stopped=False, in_flight=True, stops=[])
        t0 = _t.time()
        try:
            M.ask([{"role": "user", "content": "x"}], max_tokens=16, timeout=timeout)
            outcome = "answered"
        except Exception as e:                                    # noqa: BLE001
            outcome = type(e).__name__
        t_end = _t.time()
        sv["in_flight"] = False
        th = M._idle_thread[0]
        if th is not None:
            th.join(timeout=M.IDLE_S * 3)
        return {"outcome": outcome, "took": round(t_end - t0, 2), "watcher_alive": bool(th and th.is_alive()),
                "stops": [(round(s - t0, 2), f) for s, f in sv["stops"]], "watcher": th is not None}

    try:
        M.IDLE_S, M.IDLE_ROUND_S, M.ASK_TIMEOUT_S = 600 / scale, 30 / scale, 180 / scale
        M.PORT = srv.server_address[1]
        M.start = lambda say=print: (True, "up (stand-in)")
        M.stop = rec_stop
        M.alive = lambda: not sv["stopped"]
        M._read_state = lambda: {"model": small}
        M.USED = os.path.join(tmp, "last_use.stamp")
        M.ASKS = os.path.join(tmp, "model_asks.jsonl")
        M._last_used[0] = 0.0
        # A request whose need at the given speeds is 1.125 x IDLE_S: the margin puts its uncut wait past IDLE_S.
        msgs, tok = [{"role": "user", "content": "x"}], 700
        g = tok / (M.IDLE_S * 1.125)
        cut, info = M.time_needed(msgs, tok, gen_tps=g, prompt_tps=1e9)
        check("MK1o1 a request needing %.1f s at its speed (IDLE_S %.1f s, scaled) is handed %s s: wait_cap, IDLE_S less "
              "one watcher round, said capped -- never a wait past IDLE_S" % (info["need_s"], M.IDLE_S, cut),
              cut == int(M.wait_cap()) and cut <= M.IDLE_S - M.IDLE_ROUND_S and info["capped"] is True
              and info["need_s"] > M.IDLE_S, (cut, info, M.wait_cap()))
        fits = one(cut / 2.0, cut)                                # an answer inside the wait
        check("MK1o2 the real watcher against the stand-in: an answer inside its wait (%.1f s of %s) arrives, and the "
              "server is not stopped under it; the watcher puts it away IDLE_S after the answer (his rule, unchanged)"
              % (cut / 2.0, cut), fits["outcome"] == "answered" and fits["watcher"] and not fits["watcher_alive"]
              and len(fits["stops"]) == 1 and fits["stops"][0][1] is False and fits["stops"][0][0] >= fits["took"] + M.IDLE_S - 0.05,
              fits)
        slow = one(M.IDLE_S * 1.25, cut)                          # an answer slower than IDLE_S, under the uncut wait
        check("MK1o3 an answer slower than IDLE_S (%.1f s) ends on the ask's own clock (TimeoutError at %s s), the server "
              "is not stopped under it, and is put away IDLE_S after the ask began (the last marked use)"
              % (M.IDLE_S * 1.25, cut), slow["outcome"] == "TimeoutError" and abs(slow["took"] - cut) < 0.5
              and len(slow["stops"]) == 1 and slow["stops"][0][1] is False and slow["stops"][0][0] >= M.IDLE_S - 0.05, slow)
        uncut = math.ceil(info["need_s"] * M.TIME_MARGIN)
        by_hand = one(M.IDLE_S * 1.25, uncut)                     # the same answer handed the uncut wait by hand
        check("MK1o4 broken the other way: the same answer handed its uncut %s s by hand is cut by the keeper -- the "
              "watcher stops the server under it at about IDLE_S (%.2f s) and the ask fails (%s), the A351 review's "
              "601.3 s, scaled; so the harness sees the cut it guards" % (uncut, (by_hand["stops"] or [(-1, 0)])[0][0],
                                                                          by_hand["outcome"]),
              by_hand["outcome"] not in ("answered", "TimeoutError") and len(by_hand["stops"]) == 1
              and by_hand["stops"][0][1] is True and M.IDLE_S - 0.05 <= by_hand["stops"][0][0] <= M.IDLE_S + 4 * M.IDLE_ROUND_S,
              by_hand)
    finally:
        for k, v in keep.items():
            setattr(M, k, v)
        M._last_used[0] = keep_last
        if stub_env is not None:
            os.environ["COVENANT_MODEL_STUB"] = stub_env
        srv.shutdown()
        srv.server_close()
    # Arithmetic at the keeper's own defaults (no clock): every wait handed out sits in [ASK_TIMEOUT_S, wait_cap].
    worst = []
    for gtps in (0.05, 0.5, 1.0, 2.0, 4.0, 6.27, 20.0, 200.0):
        for n in (0, 400, 1715, 4000, 8000):
            s, i = M.time_needed([{"role": "user", "content": "y" * 3000}], n, gen_tps=gtps, prompt_tps=58.5)
            if not (M.ASK_TIMEOUT_S <= s <= max(M.ASK_TIMEOUT_S, M.wait_cap())):
                worst.append((gtps, n, s))
    check("MK1o5 at the keeper's defaults (IDLE_S %d s, round %d s) no wait handed out is past wait_cap (%d s) or under "
          "the %d s every ask had, over 40 speeds and sizes" % (M.IDLE_S, M.IDLE_ROUND_S, M.wait_cap(), M.ASK_TIMEOUT_S),
          worst == [] and M.wait_cap() == M.IDLE_S - M.IDLE_ROUND_S, worst)


def main():
    tmp = tempfile.mkdtemp(prefix="mk1_")
    big, small = M.CANDIDATES[0][0], M.CANDIDATES[-1][0]
    for name in (big, small):
        open(os.path.join(tmp, name), "wb").write(b"x")
    real = {k: getattr(M, k) for k in ("MODELS", "free_gb", "alive", "stop", "start", "_read_state", "LOG",
                                       "USED", "_REAL_USED")}
    calls = []
    try:
        M.MODELS = tmp
        M.USED = os.path.join(tmp, "last_use.stamp")     # A348b: never the live shared stamp (its time would move MK1i)
        M.stop = lambda say=print: calls.append("stop")
        M.start = lambda say=print: (calls.append("start") or (True, "up"))
        quiet = lambda *a, **k: None      # noqa: E731

        # (a) 2026-09-25, his choice "2" (load the big model only with room to spare): the small
        # model is up, 4.8 free + 2.3 reclaimable = 7.1 covers the big one's 7.0 but not its
        # headroom -> it STAYS; with 7.0 free (9.3 >= 7.0 + 2.0) it steps up.
        M._read_state = lambda: {"model": small}
        M.alive = lambda: True
        M.free_gb = lambda: 4.8
        ok, why = M.step_up(say=quiet)
        check("MK1a small up, 4.8 free + %.1f reclaimable < 7.0 + %.1f headroom: stays on the small one (his choice 2)" % (M.CANDIDATES[-1][1], M.HEADROOM_GB),
              ok is False and calls == [] and "already on the largest" in why, (ok, why, calls))
        M.free_gb = lambda: 7.0
        ok, why = M.step_up(say=quiet)
        check("MK1a2 ...and with room to spare (7.0 + %.1f >= 7.0 + headroom) it steps up" % M.CANDIDATES[-1][1],
              ok and calls == ["stop", "start"] and why.startswith("stepped up"), (ok, why, calls))

        # (b) the big one already up: nothing changes, even with memory to spare
        calls.clear()
        M._read_state = lambda: {"model": big}
        M.free_gb = lambda: 9.0
        ok, why = M.step_up(say=quiet)
        check("MK1b the largest already up: no restart, said", ok is False and calls == [] and "already on the largest" in why, (ok, why, calls))

        # (c) never steps down: the big one up but memory tight -> the small one 'fits', and nothing moves
        M.free_gb = lambda: 1.0
        ok, why = M.step_up(say=quiet)
        check("MK1c the largest up and memory tight: never steps DOWN", ok is False and calls == [] and "already on the largest" in why, (ok, why))

        # (d) free memory unreadable: nothing on a guess
        M._read_state = lambda: {"model": small}
        M.free_gb = lambda: None
        ok, why = M.step_up(say=quiet)
        check("MK1d free memory unreadable: nothing changed, said", ok is False and calls == [] and "unreadable" in why, why)

        # (e) nothing up and the small one is all that fits: starts without a stop
        M.alive = lambda: False
        M.free_gb = lambda: 3.0
        M._read_state = lambda: {}
        ok, why = M.step_up(say=quiet)
        check("MK1e nothing running: no stop, one start", ok and calls == ["start"], (ok, why, calls))

        # (f) the small one up and the budget short of the big one: no restart
        calls.clear()
        M.alive = lambda: True
        M._read_state = lambda: {"model": small}
        M.free_gb = lambda: 3.0
        ok, why = M.step_up(say=quiet)
        check("MK1f small up, 3.0 + %.1f < the big one's bar: stays (already on the largest that fits)" % M.CANDIDATES[-1][1], ok is False and calls == [] and "already on the largest" in why, (ok, why))

        # (h) the plain pick honours the headroom for the big one only
        big_need, small_need = M.CANDIDATES[0][1], M.CANDIDATES[-1][1]
        points = (big_need + M.HEADROOM_GB + 0.5, big_need + M.HEADROOM_GB - 1.0, small_need + 0.1, small_need - 0.1)
        picks = {}
        for f in points:
            M.free_gb = (lambda v: (lambda: v))(f)
            p = M.pick_model()
            picks[f] = p[1] if p else None
        check("MK1h pick: room for the big one plus headroom -> big; short of the headroom -> small; "
              "just over the small one's need -> small (no headroom); just under -> none",
              [picks[f] for f in points] == [big, small, small, None], picks)

        # (i) memory pressure puts an IDLE big model away; never mid-answer, never the small one
        stops = []
        M.stop = lambda say=print: stops.append("stop")
        M.alive = lambda: True
        M.LOG = os.path.join(tmp, "model.log")
        real_last = M._last_used[0]
        try:
            M._read_state = lambda: {"model": big}
            M.free_gb = lambda: 0.8
            M._last_used[0] = 1000.0
            a = M._pressure_check(now=1000.0 + 120)          # idle two minutes, 0.8 free: put away
            M._last_used[0] = 1000.0
            b = M._pressure_check(now=1000.0 + 10)           # used ten seconds ago: left alone
            M.free_gb = lambda: 1.5
            c = M._pressure_check(now=1000.0 + 120)          # above the floor: left alone
            M._read_state = lambda: {"model": small}
            M.free_gb = lambda: 0.5
            d = M._pressure_check(now=1000.0 + 120)          # the small one is never put away for pressure
            check("MK1i under the floor an idle big model is put away; mid-answer, above the floor, or the small one: left alone",
                  (a, b, c, d) == (True, False, False, False) and stops == ["stop"], (a, b, c, d, stops))
        finally:
            M._last_used[0] = real_last

        # (j) 2026-10-04, his words: "find a way to safely ensure tetsus operation". Measured that
        # morning: 1.44 GB free, the small model needing 2.6, pick_model() None -- Tetsu could not
        # answer and nothing said so. readiness() names it, and is a READ: it starts and stops nothing.
        calls.clear()
        stops.clear()
        real_bin = M.BIN
        bin_file = os.path.join(tmp, "llama-server.exe")
        open(bin_file, "wb").write(b"x")
        stub_env = os.environ.pop("COVENANT_MODEL_STUB", None)
        try:
            M.BIN = bin_file
            small_bar = M._bar(small, M.CANDIDATES[-1][1])
            M.alive = lambda: True
            M._read_state = lambda: {"model": small}
            up = M.readiness()
            M.alive = lambda: False
            M._read_state = lambda: {}
            M.free_gb = lambda: small_bar + 0.1
            fits = M.readiness()
            M.free_gb = lambda: small_bar - 0.1
            short = M.readiness()
            M.free_gb = lambda: None
            unread = M.readiness()
            M.free_gb = lambda: small_bar - 0.1
            M.BIN = os.path.join(tmp, "absent.exe")
            noruntime = M.readiness()
            M.BIN = bin_file
            M.MODELS = os.path.join(tmp, "empty")
            os.makedirs(M.MODELS, exist_ok=True)
            noweights = M.readiness()
            M.MODELS = tmp
            check("MK1j readiness: up -> PASS; nothing up and the small one fits -> PASS naming it; just short -> FAIL "
                  "naming free and need; memory unreadable -> UNDETERMINED; no runtime or no weights -> FAIL",
                  (up["verdict"], fits["verdict"], short["verdict"], unread["verdict"], noruntime["verdict"], noweights["verdict"])
                  == ("PASS", "PASS", "FAIL", "UNDETERMINED", "FAIL", "FAIL")
                  and small in fits["why"] and short.get("needs_gb") == small_bar and "cannot answer" in short["why"],
                  (up, fits, short, unread, noruntime, noweights))
            check("MK1j readiness is a read: it started and stopped nothing", calls == [] and stops == [], (calls, stops))
        finally:
            M.BIN = real_bin
            if stub_env is not None:
                os.environ["COVENANT_MODEL_STUB"] = stub_env

        # (k) 2026-10-04, his words: "add it as the fallback". The 2B goes BELOW the 3B, and the two
        # rules that keyed on "the last candidate" (no headroom; never put away under pressure) must
        # stay on the 3B as well -- appending the 2B would have moved both off it in silence.
        mid = "qwen2.5-3b-instruct-q4_k_m.gguf"
        fb = "Qwen3.5-2B-Q4_K_M.gguf"
        need = dict(M.CANDIDATES)
        for n in (big, mid, fb):
            open(os.path.join(tmp, n), "wb").write(b"x")
        M.MODELS = tmp
        bars = {n: M._bar(n, need[n]) for n in (big, mid, fb)}
        check("MK1k the 3B and the fallback load with no headroom; the 7B keeps its headroom",
              bars[mid] == need[mid] and bars[fb] == need[fb] and bars[big] == need[big] + M.HEADROOM_GB, bars)
        order = {}
        for label, f in (("7B", bars[big] + 0.1), ("3B", bars[mid] + 0.1), ("2B", (bars[fb] + bars[mid]) / 2),
                         ("none", bars[fb] - 0.1)):
            M.free_gb = (lambda v: (lambda: v))(f)
            got = M.pick_model()
            order[label] = got[1] if got else None
        check("MK1k fallback order: room for the 7B -> 7B; for the 3B -> the 3B, as before; between the "
              "fallback's bar and the 3B's -> the fallback; under it -> none",
              order == {"7B": big, "3B": mid, "2B": fb, "none": None}, order)
        stops.clear()
        M.alive = lambda: True
        M.LOG = os.path.join(tmp, "model.log")
        put_away = {}
        for n in (mid, fb):
            M._read_state = (lambda v: (lambda: {"model": v}))(n)
            M.free_gb = lambda: 0.5
            M._last_used[0] = 1000.0
            put_away[n] = M._pressure_check(now=1000.0 + 120)
        check("MK1k under memory pressure an idle 3B is NOT put away, nor the fallback (as the 3B alone was before)",
              put_away == {mid: False, fb: False} and stops == [], (put_away, stops))

        # (l) the fallback answers NOTHING without enable_thinking off: measured 2026-10-04, all 160
        # tokens went to reasoning (finish=length, empty content). ask() must send it on every call.
        import io
        import urllib.request as _ur
        sent = []

        class _Resp(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        real_urlopen, real_watch = _ur.urlopen, M._watch_idle
        stub_env2 = os.environ.pop("COVENANT_MODEL_STUB", None)
        try:
            M.start = lambda say=print: (True, "up")
            M._watch_idle = lambda: None
            _ur.urlopen = lambda req, timeout=None: (sent.append(json.loads(req.data.decode("utf-8")))
                                                      or _Resp(b'{"choices":[{"message":{"content":"ok"}}],"usage":{}}'))
            text, _meta = M.ask([{"role": "user", "content": "hello"}], max_tokens=160)
        finally:
            _ur.urlopen, M._watch_idle = real_urlopen, real_watch
            if stub_env2 is not None:
                os.environ["COVENANT_MODEL_STUB"] = stub_env2
        check("MK1l ask() sends chat_template_kwargs enable_thinking=false (the fallback answers nothing without it)",
              text == "ok" and len(sent) == 1
              and (sent[0].get("chat_template_kwargs") or {}).get("enable_thinking") is False, sent)

        # (n) A348b (2026-10-14): the server is ONE for every process, so its idle clock is too. A node's or the
        # watchdog's watcher read only its own clock and stopped the server under another process's ask: the
        # review matched all 17 ConnectionResetErrors on record to such a stop. The REAL watcher round
        # (_idle_tick) runs here, with stop() a recorder; "another process" is the shared stamp, written as its
        # _mark_used writes it.
        import time as _t
        stops.clear()
        origins = []

        def rec_stop(say=print):
            stops.append("stop")
            origins.append(M._stop_origin())

        def stamp(path, t):
            open(path, "a").close()
            os.utime(path, (t, t))
        M.stop = rec_stop
        M.alive = lambda: True
        M._read_state = lambda: {"model": small}         # a rung in ALWAYS_ANSWER: never put away for pressure
        M.free_gb = lambda: 0.5
        M.USED = os.path.join(tmp, "n.stamp")
        real_last2 = M._last_used[0]
        now = _t.time()
        old = now - (M.IDLE_S + 100)
        try:
            M._last_used[0] = old
            stamp(M.USED, now - 10)
            n1 = M._idle_tick(now=now)
            check("MK1n1 this process idle %ds, another asked 10 s ago: the watcher round does NOT stop the server"
                  % (M.IDLE_S + 100), n1 is False and stops == [], (n1, stops))
            stops.clear()
            origins.clear()
            stamp(M.USED, old)
            n2 = M._idle_tick(now=now)
            check("MK1n2 ...every process idle past IDLE_S: it stops it, logged as an idle stop (his rule, unchanged)",
                  n2 is True and stops == ["stop"] and "reason=idle" in (origins[0] if origins else ""), (n2, stops, origins))
            stops.clear()
            M._last_used[0] = now - 10
            n3 = M._idle_tick(now=now)
            check("MK1n3 ...this process asked 10 s ago and the stamp is old: not stopped, as before", n3 is False and stops == [],
                  (n3, stops))
            M.USED = os.path.join(tmp, "absent.stamp")
            M._last_used[0] = old
            n4 = M._idle_tick(now=now)
            check("MK1n4 ...no stamp at all (a fresh clone): this process's own clock decides, as before",
                  n4 is True and stops == ["stop"], (n4, stops))
            stops.clear()
            M.USED = os.path.join(tmp, "n.stamp")
            stamp(M.USED, now - 10)
            M._read_state = lambda: {"model": big}
            M.free_gb = lambda: 0.8
            M._last_used[0] = now - 120
            n5 = M._pressure_check(now=now)
            check("MK1n5 under memory pressure a big model another process asked 10 s ago is NOT put away (never mid-answer)",
                  n5 is False and stops == [], (n5, stops))
            M.USED = os.path.join(tmp, "mark.stamp")
            M._mark_used(now - 5)
            check("MK1n6 _mark_used sets this process's clock and the shared stamp",
                  M._last_used[0] == now - 5 and os.path.exists(M.USED) and abs(os.path.getmtime(M.USED) - (now - 5)) < 1,
                  (M._last_used[0], os.path.exists(M.USED)))
            live = os.path.join(tmp, "live.stamp")
            M.USED = M._REAL_USED = live
            real_argv0 = sys.argv[0]
            try:
                sys.argv[0] = "test_something.py"
                M._mark_used()
                by_test = os.path.exists(live)
                sys.argv[0] = "run_node.py"
                M._mark_used()
            finally:
                sys.argv[0] = real_argv0
            check("MK1n6b a test program never touches the LIVE stamp; a node does (A272's lesson)",
                  by_test is False and os.path.exists(live), (by_test, os.path.exists(live)))
            M._REAL_USED = real["_REAL_USED"]
            # the ask itself: the stamp must be fresh when the request is SENT (that is what keeps an answer in
            # flight from being cut), and again when it comes back
            M.USED = os.path.join(tmp, "ask.stamp")
            at_send = []
            stub_env3 = os.environ.pop("COVENANT_MODEL_STUB", None)
            real_urlopen3, real_watch3 = _ur.urlopen, M._watch_idle
            t0 = _t.time()
            try:
                M.start = lambda say=print: (True, "up")
                M._watch_idle = lambda: None
                def answer(req, timeout=None):
                    at_send.append(os.path.exists(M.USED) and os.path.getmtime(M.USED) >= t0 - 1)
                    if os.path.exists(M.USED):
                        os.utime(M.USED, (old, old))      # as if the answer took past IDLE_S: only a mark after it is fresh
                    return _Resp(b'{"choices":[{"message":{"content":"ok"}}],"usage":{}}')
                _ur.urlopen = answer
                M.ask([{"role": "user", "content": "hello"}], max_tokens=16)
            finally:
                _ur.urlopen, M._watch_idle = real_urlopen3, real_watch3
                if stub_env3 is not None:
                    os.environ["COVENANT_MODEL_STUB"] = stub_env3
            after = os.path.getmtime(M.USED) if os.path.exists(M.USED) else 0.0
            check("MK1n7 an ask marks the shared stamp before its request is sent, and again after the answer",
                  at_send == [True] and after >= t0 - 1, (at_send, after, t0))
        finally:
            M._last_used[0] = real_last2
    finally:
        for k, v in real.items():
            setattr(M, k, v)

    # MK1m (A341b, 2026-10-13): a server that answers with no state is ADOPTED only when it is provably this
    # keeper's own -- its binary, one of its weights. Temp state and log; the port and the process are stand-ins.
    keep = {k: getattr(M, k) for k in ("STATE", "LOG", "alive")}
    tdm = tempfile.mkdtemp(prefix="mk1m_")
    try:
        M.STATE, M.LOG, M.alive = os.path.join(tdm, "state.json"), os.path.join(tdm, "log.txt"), (lambda: True)
        ours = (lambda pid: (M.BIN, "%s -m x/%s --port 8081" % (M.BIN, M.CANDIDATES[-1][0])))
        ok, why = M.adopt(listener=lambda: 9220, cmdline=ours)
        st = json.load(open(M.STATE, encoding="utf-8")) if os.path.exists(M.STATE) else {}
        check("MK1m a server on the port that is this keeper's binary and weights is adopted: the state is written back",
              ok and st.get("pid") == 9220 and st.get("model") == M.CANDIDATES[-1][0] and st.get("adopted") is True, (ok, why, st))
        os.remove(M.STATE)
        ok, why = M.adopt(listener=lambda: 5524, cmdline=lambda pid: (r"C:\other\llama-server.exe", "x -m %s" % M.CANDIDATES[-1][0]))
        check("MK1m2 ...another binary on the port is NOT adopted (A265's orphan stays his to end)",
              not ok and not os.path.exists(M.STATE) and "not this keeper's runtime" in why, why)
        ok, why = M.adopt(listener=lambda: 7, cmdline=lambda pid: (M.BIN, "%s -m unknown.gguf" % M.BIN))
        check("MK1m3 ...nor our binary running weights the keeper does not know", not ok and not os.path.exists(M.STATE), why)
        M.alive = lambda: False
        check("MK1m4 ...and nothing is adopted when nothing answers", M.adopt(listener=lambda: 1, cmdline=ours)[0] is False)
    finally:
        for k, v in keep.items():
            setattr(M, k, v)

    mk1o()
    # The weights are not tracked (models/ is gitignored), so the runner's staged copy has none: the file
    # check is made only where the directory exists, and says so otherwise.
    have = os.path.isdir(M.MODELS) and any(os.path.isfile(os.path.join(M.MODELS, n)) for n, _ in M.CANDIDATES)
    check("MK1g the candidates are listed largest first%s" % ("; every weight file is on this tree" if have else " (no weights here: the staged runner)"),
          M.CANDIDATES[0][1] > M.CANDIDATES[-1][1] and (not have or all(os.path.isfile(os.path.join(M.MODELS, n)) for n, _ in M.CANDIDATES)))

    # A360 (2026-10-17): llama-server gets one fewer thread than the physical cores, measured +22% generating at real
    # depth on this PC against the old logical-minus-two; an override wins; never fewer than 2.
    saved = os.environ.pop("COVENANT_MODEL_THREADS", None)
    try:
        t12, t4, t2 = M.server_threads(12), M.server_threads(4), M.server_threads(2)
        os.environ["COVENANT_MODEL_THREADS"] = "7"
        t_env = M.server_threads(12)
    finally:
        os.environ.pop("COVENANT_MODEL_THREADS", None)
        if saved is not None:
            os.environ["COVENANT_MODEL_THREADS"] = saved
    check("MK1.T threads: 12 logical -> 5 (not the old 10), 4 -> 2, 2 -> 2 (the floor), and COVENANT_MODEL_THREADS=7 -> 7",
          (t12, t4, t2, t_env) == (5, 2, 2, 7), (t12, t4, t2, t_env))

    print()
    print("%d passed, %d failed" % (PASSED[0], len(FAILURES)))
    if FAILURES:
        print("MK1 result: FAILED (%d)" % len(FAILURES))
        for f in FAILURES:
            print("  - %s" % f)
        return 1
    print("MK1 result: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
