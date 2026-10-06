#!/usr/bin/env python3
"""covenant_model.py -- the open-source model on this PC, on demand and put away.

WHY (2026-09-19, his words). "there has to be a image creation open source we
can take and improve on same as the other asks including our students growing
to agents"; "optimize the pc towards these tasks and this purpose"; "need a
browser and a security layer other than that optimize"; "green light".

WHAT THIS IS. A thin keeper for llama.cpp's llama-server (tools/llama/, the
same 18 MB runtime the judge workflow uses on the GitHub runner) and the GGUF
weights under models/ (never tracked: .gitignore). It starts the server the
first time something asks, on 127.0.0.1 only, and STOPS it after IDLE_S with
nothing asked -- his standing rule since Ollama: unload the model after use.
This PC has 15.3 GB and was using 12.5 GB of it when this was written, mostly
the browser and the desktop app, so the model is a guest: it picks the
largest weights that fit the memory free at the moment it starts, and says
which.

WHAT IT IS NOT. Not a judge seat and not the gate. The gate is the sentinel
(the distilled students and the semantic judge); every answer this model gives
through the node passes that gate before anyone sees it (/m/agent). It is the
thing the students learn to judge -- that is how they grow toward agents:
their verdicts on its answers go into the same ledger the nightly distill
reads.

CLI:  python covenant_model.py --status | --start | --stop | --ask "text"
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(HERE, "tools", "llama", "llama-server.exe")
MODELS = os.path.join(HERE, "models")
HOST, PORT = "127.0.0.1", int(os.environ.get("COVENANT_MODEL_PORT", "8081"))
IDLE_S = int(os.environ.get("COVENANT_MODEL_IDLE_S", "600"))
STATE = os.path.join(HERE, "ops", "model_server.json")        # pid, model, started -- gitignored ops/ state
LOG = os.path.join(HERE, "logs", "model_server.log")

# (file name, resident memory it needs, in GB) -- the first that fits the memory
# free at start is the one loaded. Split GGUFs are named by their first part.
# Measured 2026-09-19 22:55 with his browser and the desktop app open: 2.4 GB
# free of 15.3. The 3B's weights are 2.0 GB and llama.cpp maps them (the page
# cache carries what does not fit), so its bar is set at the weights plus a
# 4k-token cache; the 7B keeps the honest 6 GB and waits for memory he frees.
# 7.0 for the 7B: MEASURED 2026-09-25, llama-server holding 7,029 MB with the 8k cache (it
# was listed at 6.0, a guess from the weight size).
CANDIDATES = [
    ("qwen2.5-coder-7b-instruct-q4_k_m-00001-of-00002.gguf", 7.0),
    ("qwen2.5-3b-instruct-q4_k_m.gguf", 2.6),     # 2.3 + ~0.3 for the 8k cache (an estimate, 2026-09-26; measure the first 8k load)
    # THE FALLBACK (2026-10-04, his words: "add it as the fallback"). Loaded only when the 3B does
    # not fit. Chosen by measurement, A252 / tools/tetsu_bakeoff.py: under the chat door's own system
    # message it scored 11 of 24 on his exam against the 3B's 12, with two wrong-act answers against
    # the 3B's three plus one conditional. Its bar is MEASURED, not estimated: 2116 MB working set at
    # the end of 26 asks with the 8k cache. It needs enable_thinking off (ask() below): without it,
    # measured, it spent all 160 tokens reasoning and answered nothing.
    ("Qwen3.5-2B-Q4_K_M.gguf", 2.1),
]
# THE RUNGS THAT EXIST SO TETSU CAN ANSWER: no headroom before they load, never put away for memory
# pressure. Until 2026-10-04 both rules keyed on "the last candidate", which was the 3B. Appending the
# fallback would have moved both onto it in silence -- the 3B would have needed 4.6 GB free instead of
# 2.6, and an idle 3B would have been stopped under pressure. Named here so neither moves.
ALWAYS_ANSWER = frozenset({"qwen2.5-3b-instruct-q4_k_m.gguf", "Qwen3.5-2B-Q4_K_M.gguf"})

# KEEP THE PC FUNCTIONAL (2026-09-25, his words: "have to constantly optimize to keep the pc
# functional also", and his choice between two of his own goals: "2" -- load the big model
# only with room to spare, otherwise the small one). Measured that evening: the 7B loaded,
# 0.88 GB free of 15.3, and his answers' median latency 72 s against about 5 s on the 3B.
#   HEADROOM_GB  kept free for the rest of the PC before a model outside ALWAYS_ANSWER loads.
#   FLOOR_GB     below this, an idle model outside ALWAYS_ANSWER is put away; the next
#                question loads what fits.
# BOTH NUMBERS ARE MINE (Claude's), not measurements and not his; he can set either in the
# environment without touching code. The ALWAYS_ANSWER rungs never need headroom, so Tetsu can
# always answer when anything fits at all. (Until 2026-10-04 this said "the smallest", which was
# then the 3B; see ALWAYS_ANSWER.)
HEADROOM_GB = float(os.environ.get("COVENANT_MODEL_HEADROOM_GB", "2.0"))
FLOOR_GB = float(os.environ.get("COVENANT_MODEL_FLOOR_GB", "1.0"))
PRESSURE_IDLE_S = 60

# THE WINDOW, COUNTED (A273, 2026-10-06). The server holds CTX_TOKENS for one request (-c, -np 1):
# the prompt AND the answer it writes. The doors' history budget was a fixed 12,000 characters,
# sized beside rules of "about 5,600 characters" (retracted: A273-RULES-SIZE-2026-10-06, docs/
# RETRACTED.json); measured today the composed rules were 11,817
# characters, 2,916 tokens by the server's own tokenizer, and those rules with the batch caller's
# real history (16 messages, 10,980 characters) and a dense 4,000-character question came to a
# 7,594-token prompt: 8,294 with the door's 700-token answer. fit() replaces the guess with
# a count: the server's own chat template (/apply-template) and tokenizer (/tokenize), the two
# steps /v1/chat/completions takes, measured answering in 33 ms while the one slot was busy
# generating -- so counting never waits behind another ask.
#   FIT_MARGIN_TOKENS          slack kept free, mine (Claude's), not a measurement.
#   FALLBACK_CHARS_PER_TOKEN   used only when the server cannot be asked (a stub, a server that
#                              will not start -- and then ask() fails too). MEASURED: 321 texts and
#                              answers of 200+ characters from ops/chat/ask_log.jsonl ran 3.04
#                              characters a token at the lowest, 3.48 at the 1st percentile, 4.52
#                              at the median; 3.0 is at or under every one of them.
#   MIN_ANSWER_TOKENS          with nothing left to drop, the answer may be shortened to this and
#                              no further; below it the request is refused, never sent too big.
CTX_TOKENS = 8192
FIT_MARGIN_TOKENS = 64
FALLBACK_CHARS_PER_TOKEN = 3.0
FALLBACK_TOKENS_PER_MESSAGE = 8        # the template's own tokens; measured ~5 a message (Qwen2.5)
MIN_ANSWER_TOKENS = 128
COUNT_TIMEOUT_S = 10


def _bar(name, need):
    """Free memory a candidate needs before it loads: its size, plus headroom unless it is a rung
    that exists so Tetsu can answer (ALWAYS_ANSWER)."""
    return need + (0.0 if name in ALWAYS_ANSWER else HEADROOM_GB)

_lock = threading.Lock()
_last_used = [0.0]


def free_gb():
    """Physical memory free right now, GB; None where it cannot be read."""
    try:
        if os.name == "nt":
            import ctypes
            class MS(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
            m = MS(); m.dwLength = ctypes.sizeof(MS)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            return round(m.ullAvailPhys / 2 ** 30, 2)
        with open("/proc/meminfo") as fh:
            for line in fh:
                if line.startswith("MemAvailable:"):
                    return round(int(line.split()[1]) / 2 ** 20, 2)
    except Exception:                                             # noqa: BLE001
        return None
    return None


def pick_model():
    """(path, name, needs_gb) of the largest candidate present that fits, or None."""
    free = free_gb()
    for name, need in CANDIDATES:
        p = os.path.join(MODELS, name)
        if os.path.isfile(p) and (free is None or free >= _bar(name, need)):
            return p, name, need
    return None


def readiness():
    """Could Tetsu answer right now? A READ: it starts nothing and stops nothing.

    WHY (2026-10-04, his words: "find a way to safely ensure tetsus operation"). Measured that
    morning: 1.44 GB free of 15.3 and the smallest weights need 2.6, so pick_model() returned None
    and any question to Tetsu would have failed at /m/agent with a 503 that the ask log never
    records. Nothing said so: the daily cycle's model_state() read {"file": None} and its exam
    read "not measured", neither of them a failure. The refusal to load is right -- his rule is
    that the PC stays usable -- but a refusal nobody hears is the silence this project keeps
    finding. This names it, so the daily cycle can carry it as a failure.

    Returns {"verdict": PASS | FAIL | UNDETERMINED, "why": text, "free_gb": float|None, ...}."""
    if alive():
        st = _read_state()
        if not st.get("pid") and not st.get("model"):
            # A265: something answers on the port and this keeper recorded nothing. On 2026-10-05 that
            # was a server whose stop had failed: it answered /health and timed out every ask.
            return {"verdict": "UNDETERMINED", "free_gb": free_gb(), "managed": False,
                    "why": "a server answers on %s:%d that this keeper has no record of starting (no state): "
                           "whether it answers in time is not measured, and nothing here can put it away (A265)"
                           % (HOST, PORT)}
        return {"verdict": "PASS", "why": "up: %s" % (st.get("model") or "?"), "free_gb": free_gb()}
    if os.environ.get("COVENANT_MODEL_STUB"):
        return {"verdict": "PASS", "why": "stub", "free_gb": None}
    if not os.path.isfile(BIN):
        return {"verdict": "FAIL", "why": "no runtime at %s" % BIN, "free_gb": free_gb()}
    present = [(n, need) for n, need in CANDIDATES if os.path.isfile(os.path.join(MODELS, n))]
    if not present:
        return {"verdict": "FAIL", "why": "no weights under %s" % MODELS, "free_gb": free_gb()}
    free = free_gb()
    if free is None:
        return {"verdict": "UNDETERMINED", "why": "free memory unreadable", "free_gb": None}
    pick = pick_model()
    if pick:
        return {"verdict": "PASS", "why": "would load %s (free %.2f GB, its bar %.1f GB)"
                % (pick[1], free, _bar(pick[1], pick[2])), "free_gb": free}
    small, need = present[-1]                     # CANDIDATES is largest first; the last present is the smallest
    return {"verdict": "FAIL", "free_gb": free, "needs_gb": _bar(small, need), "smallest": small,
            "why": "Tetsu cannot answer: free %.2f GB, the smallest weights (%s) need %.1f GB -- "
                   "nothing is loaded and nothing is freed for him; he answers again once that much "
                   "memory is free" % (free, small, _bar(small, need))}


def _read_state():
    try:
        with open(STATE, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def _write_state(d):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(STATE, "w", encoding="utf-8") as fh:
        json.dump(d, fh)


def alive():
    """The server answers /health on the loopback port."""
    try:
        with urllib.request.urlopen("http://%s:%d/health" % (HOST, PORT), timeout=3) as r:
            return r.status == 200
    except Exception:                                             # noqa: BLE001
        return False


def step_up(say=print):
    """STEP UP to the largest model that fits once the running one is counted as reclaimable
    (2026-09-21, his words: "we need to rapidly make up the gap in ai"). Measured that day: 15.3 GB
    of RAM, 4.8 free with the 3B server holding 2.0, and the 7B needs 6.0 -- so the 7B fits only
    if the 3B is put away first, which pick_model() alone never sees. Returns (changed, why). Never
    steps DOWN; never restarts mid-answer (the caller runs it idle: the nightly, or by hand)."""
    st = _read_state()
    cur = str(st.get("model") or "")
    cur_need = next((need for name, need in CANDIDATES if name == cur), 0.0)
    free = free_gb()
    if free is None:
        return False, "free memory unreadable; nothing changed"
    budget = free + (cur_need if alive() else 0.0)
    best = None
    for name, need in CANDIDATES:                     # CANDIDATES is largest first
        if os.path.isfile(os.path.join(MODELS, name)) and budget >= _bar(name, need):
            best = (name, need)
            break
    if not best:
        return False, "no candidate fits even with the running model reclaimed (budget %.1f GB)" % budget
    if best[1] <= cur_need and alive():
        return False, "already on the largest that fits (%s; budget %.1f GB)" % (cur or "?", budget)
    if alive():
        say("model: stepping up from %s to %s (budget %.1f GB)" % (cur or "?", best[0], budget))
        stop(say=say)
    ok, why = start(say=say)
    return ok, ("stepped up to %s" % _read_state().get("model", "?")) if ok else "could not start after the step: " + why


def start(say=print):
    """Start llama-server if it is not answering. Returns (ok, why)."""
    if alive():
        return True, "already up: " + str(_read_state().get("model", "?"))
    if os.environ.get("COVENANT_MODEL_STUB"):
        return True, "stub"
    if not os.path.isfile(BIN):
        return False, "no runtime: %s (tools/llama/ is not tracked; unzip the llama.cpp win-cpu build there)" % BIN
    pick = pick_model()
    if not pick:
        return False, "no weights fit: free %s GB, candidates %s under %s" % (free_gb(), [c[0] for c in CANDIDATES], MODELS)
    path, name, need = pick
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    threads = max(2, (os.cpu_count() or 4) - 2)                   # leave the nodes and the desk two threads
    # 8k for both (2026-09-26): his longer conversation memory (up to 12,000 characters of
    # history, agent_history) must fit beside the rules and the answer. The 3B's bar in
    # CANDIDATES carries the larger cache.
    # (A273, 2026-10-06: 12,000 characters did not always fit beside the rules, which had grown to
    # 2,916 tokens; the doors now fit the history to this window by counting it -- fit() below.)
    ctx = str(CTX_TOKENS)
    # ONE SLOT (A269, 2026-10-06). This llama-server build defaults to 4 parallel slots that share ONE
    # pool of -c tokens: requests running at the same time together overflowed it, and the server
    # answered "500 Context size has been exceeded" -- to a 2,521-token probe while the X batch's
    # ~7,000-token asks were in flight, and to asks through Tetsu's door all that morning. -np 1 runs
    # one request at a time against the whole 8192; the others queue on the server instead of failing.
    # (First written as a per-slot split; retracted as A269-SLOT-SPLIT-2026-10-06, docs/RETRACTED.json.)
    args = [BIN, "-m", path, "--host", HOST, "--port", str(PORT), "-c", ctx, "-np", "1", "-t", str(threads),
            "--no-webui", "--log-disable"]
    creation = 0x08000000 if os.name == "nt" else 0               # CREATE_NO_WINDOW
    with open(LOG, "a", encoding="utf-8") as lf:
        lf.write("%s start %s (free %s GB, needs %s GB, %d threads)\n" % (time.strftime("%Y-%m-%dT%H:%M:%S"), name, free_gb(), need, threads))
        p = subprocess.Popen(args, stdout=lf, stderr=subprocess.STDOUT, creationflags=creation, cwd=os.path.dirname(BIN))
    _write_state({"pid": p.pid, "model": name, "started": time.time(), "needs_gb": need, "threads": threads})
    for _ in range(120):                                          # a 4 GB file from a cold disk can take a minute
        if alive():
            _last_used[0] = time.time()
            _watch_idle()
            say("model server: up, %s, pid %d" % (name, p.pid))
            return True, "up: %s" % name
        if p.poll() is not None:
            return False, "llama-server exited %s -- see %s" % (p.returncode, LOG)
        time.sleep(1)
    return False, "llama-server did not answer within 120 s -- see %s" % LOG


def _stop_origin():
    """Who is stopping the server, for the log line only (2026-10-05, his words: "covenant logging
    green light as long as you not fucking with tetsus free will"). OBSERVATION ONLY: it reads this
    process and its own call stack; it changes nothing about when or whether anything stops, and
    it records no question, answer or thought of his. Why: the stop at 2026-10-04T09:06:25 could
    only be attributed by inference (timing), because the line named no caller.
    The reason is read off the call chain, not passed in: stop()'s signature stays exactly as it
    was (suites replace it with lambda say=print: ...). Never raises."""
    try:
        f = sys._getframe(2)                    # 0 = here, 1 = stop(), 2 = whoever called stop()
        chain = []
        while f is not None and len(chain) < 3:
            co = f.f_code
            chain.append("%s.%s:%d" % (os.path.splitext(os.path.basename(co.co_filename))[0],
                                        getattr(co, "co_qualname", co.co_name), f.f_lineno))
            f = f.f_back
        where = " <- ".join(chain) or "?"
        if "_pressure_check" in where:
            reason = "pressure"
        elif "_watch_idle" in where:
            reason = "idle"
        elif "covenant_model.step_up" in where:
            reason = "step_up"
        elif "covenant_model.main" in where:
            reason = "cli"
        else:
            reason = "other"
        # _last_used is set by ask() and by start() bringing the server up, so this is "last use".
        used = ("last use in that process %.0fs ago" % (time.time() - _last_used[0])) if _last_used[0] \
            else "no use in that process"
        argv = getattr(sys, "argv", None)
        argv0 = os.path.basename(argv[0]) if argv and argv[0] else "?"
        return " -- reason=%s by pid %d (%s) thread %s; %s; from %s" % (
            reason, os.getpid(), argv0, threading.current_thread().name, used, where)
    except Exception:                                             # noqa: BLE001 -- a log line must never break a stop
        try:
            return " -- reason=? by pid %d (origin unreadable)" % os.getpid()
        except Exception:                                         # noqa: BLE001
            return ""


# A STOP IS A STOP ONLY WHEN THE SERVER STOPS ANSWERING (A265, 2026-10-05). The idle stop at
# 2026-10-04T23:10:12 logged "stop pid 5524", deleted the state and returned True -- and taskkill
# had answered "Access is denied" (exit 128): that server ran with rights the node lacks. It kept
# answering on 8081 for a day with no state, so start() reused it as "already up", the idle and
# pressure checks could never put it away, and readiness() read PASS while every ask timed out
# against a model Windows had paged out (0.52 GB free). The kill's own result is now read, and the
# server is asked whether it still answers; until it does not, the state is kept so the keeper
# still knows what it is running, and the log says the stop FAILED, with taskkill's words.
STOP_VERIFY_S = 10


def stop(say=print):
    st = _read_state()
    pid = st.get("pid")
    if not pid:
        return False, "not started by this keeper"
    detail = ""
    try:
        if os.name == "nt":
            r = subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, text=True)
            detail = "taskkill exit %s: %s" % (r.returncode, " ".join(((r.stderr or "") + " " + (r.stdout or "")).split())[:240])
        else:
            os.kill(int(pid), 15)
    except Exception as e:                                        # noqa: BLE001
        return False, "could not stop pid %s: %s" % (pid, e)
    for _ in range(int(STOP_VERIFY_S * 2)):
        if not alive():
            break
        time.sleep(0.5)
    else:
        with open(LOG, "a", encoding="utf-8") as lf:
            lf.write("%s STOP FAILED pid %s (%s): it still answers on %s:%d after %ss; state kept (A265). %s%s\n"
                     % (time.strftime("%Y-%m-%dT%H:%M:%S"), pid, st.get("model"), HOST, PORT, STOP_VERIFY_S,
                        detail, _stop_origin()))
        say("model server: could NOT stop pid %s -- it still answers (%s)" % (pid, detail or "no detail"))
        return False, "could not stop pid %s: it still answers (%s)" % (pid, detail or "no detail")
    try:
        os.remove(STATE)
    except OSError:
        pass
    with open(LOG, "a", encoding="utf-8") as lf:
        # The first part is unchanged (same words, same order); who stopped it follows " -- ".
        lf.write("%s stop pid %s (%s)%s\n" % (time.strftime("%Y-%m-%dT%H:%M:%S"), pid, st.get("model"), _stop_origin()))
    say("model server: stopped pid %s" % pid)
    return True, "stopped"


_idle_thread = [None]


def _pressure_check(now=None):
    """Put an idle big model away when free memory is under FLOOR_GB. Never mid-answer (idle at
    least PRESSURE_IDLE_S), never a rung in ALWAYS_ANSWER. True when it stopped one."""
    now = time.time() if now is None else now
    if not alive():
        return False
    cur = str(_read_state().get("model") or "")
    if not cur or cur in ALWAYS_ANSWER or now - _last_used[0] < PRESSURE_IDLE_S:
        return False
    free = free_gb()
    if free is None or free >= FLOOR_GB:
        return False
    try:
        with open(LOG, "a", encoding="utf-8") as lf:
            lf.write("%s put away %s under memory pressure (free %.2f GB < floor %.2f GB)\n"
                     % (time.strftime("%Y-%m-%dT%H:%M:%S"), cur, free, FLOOR_GB))
    except OSError:
        pass
    stop(say=lambda *_a: None)
    return True


def _watch_idle():
    """One daemon thread: after IDLE_S with no ask, the server is stopped -- the rule since Ollama.
    Each round it also puts a big model away under memory pressure (_pressure_check)."""
    if _idle_thread[0] and _idle_thread[0].is_alive():
        return
    def run():
        while True:
            time.sleep(30)
            if not alive():
                return
            if _pressure_check():
                return
            if time.time() - _last_used[0] > IDLE_S:
                stop(say=lambda *_a: None)
                return
    t = threading.Thread(target=run, name="covenant-model-idle", daemon=True)
    t.start()
    _idle_thread[0] = t


def ask(messages, max_tokens=700, temperature=0.3, timeout=180):
    """One chat completion. messages: [{"role","content"}...]. Returns (text, meta) or raises."""
    if os.environ.get("COVENANT_MODEL_STUB"):
        last = messages[-1]["content"] if messages else ""
        # A scripted answer (2026-09-21, A175): a user line beginning "STUB>> " is
        # returned verbatim, so a suite can make the stub "decide" a directive
        # (FETCH, MOLTBOOK) and drive the door's own handling of it.
        if last.startswith("STUB>> "):
            return last[7:], {"model": "stub", "tokens": 0, "ms": 0}
        # The stub names how many messages it was handed, so a suite can see
        # whether the turns before this one reached the model (M6q, 2026-09-21).
        return "stub answer to: " + last[:80] + " (%d messages)" % len(messages), {"model": "stub", "tokens": 0, "ms": 0}
    with _lock:
        ok, why = start(say=lambda *_a: None)
        if not ok:
            raise RuntimeError(why)
        # WHOEVER ASKS, KEEPS (2026-09-19). The idle watcher lives in the process
        # that asks -- the CLI's watcher died with the CLI and left the server
        # up, measured at 22:52. So every asker arms the watcher, and the
        # long-lived node process is the one that will put the model away.
        _last_used[0] = time.time()
        _watch_idle()
    # enable_thinking off (2026-10-04): the Qwen3.5 fallback, asked without it, spent all 160 tokens
    # reasoning and returned an empty answer (finish=length); with it, it answered in 2.8 s. The 3B
    # answered normally with the same field in both of its exam runs (A252); a template that does not
    # use the variable ignores it.
    body = json.dumps({"messages": messages, "max_tokens": int(max_tokens), "temperature": float(temperature),
                       "chat_template_kwargs": {"enable_thinking": False}}).encode("utf-8")
    req = urllib.request.Request("http://%s:%d/v1/chat/completions" % (HOST, PORT), data=body,
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read().decode("utf-8", "replace"))
    _last_used[0] = time.time()
    text = str(d.get("choices", [{}])[0].get("message", {}).get("content", ""))
    usage = d.get("usage", {}) or {}
    return text, {"model": _read_state().get("model", "?"), "tokens": int(usage.get("completion_tokens", 0) or 0),
                  "ms": int((time.time() - t0) * 1000)}


class ContextTooLong(RuntimeError):
    """A request that cannot fit the model's window even with every replayed turn dropped (A273)."""


def _post(path, body, timeout=COUNT_TIMEOUT_S):
    req = urllib.request.Request("http://%s:%d%s" % (HOST, PORT, path), data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def count_prompt_tokens(messages):
    """The prompt's size in tokens as the server will see it: its chat template, then its tokenizer
    (the same template arguments ask() sends). None when the server cannot be asked."""
    try:
        prompt = _post("/apply-template", {"messages": messages,
                                           "chat_template_kwargs": {"enable_thinking": False}})["prompt"]
        return len(_post("/tokenize", {"content": prompt, "add_special": True})["tokens"])
    except Exception:                                             # noqa: BLE001 -- the caller falls back to the estimate
        return None


def estimate_prompt_tokens(messages):
    """An upper estimate from characters, at FALLBACK_CHARS_PER_TOKEN (measured; see above)."""
    return FALLBACK_TOKENS_PER_MESSAGE + sum(
        FALLBACK_TOKENS_PER_MESSAGE + int(-(-len(str(m.get("content", ""))) // FALLBACK_CHARS_PER_TOKEN))
        for m in messages)


def _counter():
    """(count, how): the server's count when it can be asked, the estimate otherwise. The server is
    started first, as ask() would start it: a count against a stopped server would fall back to the
    estimate, and the first message after an idle stop -- when he comes back to the conversation --
    would lose memory the window had room for."""
    if os.environ.get("COVENANT_MODEL_STUB"):
        return estimate_prompt_tokens, "estimate (stub)"
    with _lock:
        ok, _why = start(say=lambda *_a: None)
    if ok and count_prompt_tokens([{"role": "user", "content": "."}]) is not None:
        def exact(ms):
            n = count_prompt_tokens(ms)
            return estimate_prompt_tokens(ms) if n is None else n
        return exact, "server"
    return estimate_prompt_tokens, "estimate"


def fit(messages, max_tokens=700, droppable=0, count=None):
    """(messages, max_tokens, info): the request cut to fit the window, CTX_TOKENS, before it is sent.

    messages[0] is the system message; messages[1:1 + droppable] are the replayed turns, oldest first,
    in user/assistant pairs; everything after them -- this question, and on a follow-up the first
    answer and its DATA -- is kept whole. The fewest oldest pairs are dropped that make the prompt plus
    max_tokens plus FIT_MARGIN_TOKENS fit, so as much of his conversation as fits stays. With no turn
    left to drop, the answer is shortened, to MIN_ANSWER_TOKENS at the least; below that ContextTooLong
    is raised. info: prompt_tokens, answer_tokens, ctx, kept, dropped, counted."""
    how = "given"
    if count is None:
        count, how = _counter()
    head, hist, tail = list(messages[:1]), list(messages[1:1 + droppable]), list(messages[1 + droppable:])
    cuts = list(range(0, len(hist), 2)) + [len(hist)]             # messages dropped: 0, 2, 4 ... all
    limit = CTX_TOKENS - FIT_MARGIN_TOKENS
    sizes = {}

    def size(i):                                                  # the prompt with cuts[i] turns dropped
        if i not in sizes:
            sizes[i] = int(count(head + hist[cuts[i]:] + tail))
        return sizes[i]
    lo, hi = 0, len(cuts) - 1                                     # dropping more never makes it larger
    if size(hi) + max_tokens > limit:
        lo = hi
    else:
        while lo < hi:
            mid = (lo + hi) // 2
            if size(mid) + max_tokens <= limit:
                hi = mid
            else:
                lo = mid + 1
    n = size(lo)
    answer = min(int(max_tokens), limit - n)
    info = {"prompt_tokens": n, "answer_tokens": answer, "ctx": CTX_TOKENS, "kept": len(hist) - cuts[lo],
            "dropped": cuts[lo], "counted": how}
    if answer < min(int(max_tokens), MIN_ANSWER_TOKENS):
        raise ContextTooLong("the request is %d tokens before any answer, with all %d replayed turns dropped; "
                             "the model's window is %d (A273)" % (n, len(hist), CTX_TOKENS))
    return head + hist[cuts[lo]:] + tail, answer, info


def status():
    st = _read_state()
    return {"alive": alive(), "model": st.get("model"), "pid": st.get("pid"), "free_gb": free_gb(),
            "would_pick": (pick_model() or (None,))[1] if pick_model() else None,
            "runtime": os.path.isfile(BIN), "weights": sorted(f for f in os.listdir(MODELS) if f.endswith(".gguf")) if os.path.isdir(MODELS) else []}


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="the open-source model on this PC, on demand and put away")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--start", action="store_true")
    ap.add_argument("--stop", action="store_true")
    ap.add_argument("--ask", metavar="TEXT")
    ap.add_argument("--keep", action="store_true", help="after --ask, leave the server up (default: put it away)")
    a = ap.parse_args(argv)
    if a.start:
        ok, why = start(); print(why); return 0 if ok else 1
    if a.stop:
        ok, why = stop(); print(why); return 0 if ok else 1
    if a.ask:
        text, meta = ask([{"role": "user", "content": a.ask}])
        print(text); print("--", meta)
        if not a.keep:
            stop(say=lambda *_a: None)                             # the CLI is not a process that stays to watch idle
        return 0
    print(json.dumps(status(), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
