#!/usr/bin/env python3
"""MK1 -- the model keeper steps UP to the largest model that fits once the running one is
counted as reclaimable, never down, never on a guess. RUN with the keeper's readings stubbed
and a temp models directory; no server is started.

Pins covenant_model.step_up (2026-09-21, his words: "we need to rapidly make up the gap in
ai"; measured that day: 15.3 GB RAM, 4.8 free with the 3B holding 2.0, the 7B needing 6.0 --
so the 7B fit only once the 3B was put away, which the plain pick never saw).
"""
import json
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


def main():
    tmp = tempfile.mkdtemp(prefix="mk1_")
    big, small = M.CANDIDATES[0][0], M.CANDIDATES[-1][0]
    for name in (big, small):
        open(os.path.join(tmp, name), "wb").write(b"x")
    real = {k: getattr(M, k) for k in ("MODELS", "free_gb", "alive", "stop", "start", "_read_state", "LOG")}
    calls = []
    try:
        M.MODELS = tmp
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
    finally:
        for k, v in real.items():
            setattr(M, k, v)
    # The weights are not tracked (models/ is gitignored), so the runner's staged copy has none: the file
    # check is made only where the directory exists, and says so otherwise.
    have = os.path.isdir(M.MODELS) and any(os.path.isfile(os.path.join(M.MODELS, n)) for n, _ in M.CANDIDATES)
    check("MK1g the candidates are listed largest first%s" % ("; every weight file is on this tree" if have else " (no weights here: the staged runner)"),
          M.CANDIDATES[0][1] > M.CANDIDATES[-1][1] and (not have or all(os.path.isfile(os.path.join(M.MODELS, n)) for n, _ in M.CANDIDATES)))

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
