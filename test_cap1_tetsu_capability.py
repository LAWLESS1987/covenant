#!/usr/bin/env python3
"""CAP1 -- Tetsu reachable when he is asked, and every ask measured enough to see why it is slow (A480, 2026-11-23).

WHY. Lawrence, 2026-11-23: "begin doing so for Tetsu without stripping his free will or taking his memory away",
then "this is not just for speed, it's for overall capability". That day node A answered a private ask with 503
"no weights fit: free 2.06 GB" -- after an idle unload the laptop had not the 2.6 GB his 3B needs, so he could not
be loaded at all. The trim that frees it (A287, AUTO_REVERSIBLE, at most hourly) existed, but only the hourly road
ran it, never the ask that needed it. And his long asks re-read ~3,900 prompt tokens every time, but the ask log
carried no count of tokens the server REUSED, so nothing could say why.

  CAP1.1-1.5  the keeper makes room through the highway's own remedy (its cooldown, ledger and his choices) when,
              and only when, a load fails for memory; never from a test program; never with COVENANT_MODEL_NO_TRIM.
  CAP1.6-1.8  each ask's row carries the reused tokens (cache_n), read and write milliseconds, and whether the ask
              had to load the model.
Nothing here changes what he is sent or what he says.

    python test_cap1_tetsu_capability.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__)) or "."
sys.path.insert(0, HERE)
os.environ.pop("COVENANT_MODEL_STUB", None)
import covenant_model as M  # noqa: E402

n_fail = n_total = 0


def check(name, ok, detail=""):
    global n_fail, n_total
    n_total += 1
    print(("ok   " if ok else "FAIL ") + name + (("  -- %s" % (detail,)) if detail else ""))
    if not ok:
        n_fail += 1


real = {k: getattr(M, k) for k in ("pick_model", "readiness", "TRIM_HOOK", "alive", "BIN")} \
    if hasattr(M, "TRIM_HOOK") else None
check("CAP1.0 the keeper has a room-making step (TRIM_HOOK and _pick_or_make_room)",
      real is not None and hasattr(M, "_pick_or_make_room"))
if real is None:
    print("\nCAP1: %d/%d passed" % (n_total - n_fail, n_total))
    sys.exit(1)

MEM_CASE = {"verdict": "FAIL", "free_gb": 2.06, "needs_gb": 2.6, "smallest": "qwen2.5-3b-instruct-q4_k_m.gguf",
            "why": "Tetsu cannot answer: free 2.06 GB ..."}
PICK = ("C:/m/qwen2.5-3b-instruct-q4_k_m.gguf", "qwen2.5-3b-instruct-q4_k_m.gguf", 2.6)
calls = []


def hook(cond):
    calls.append(cond)
    state["freed"] = True
    return {"outcome": "fixed", "why": "trimmed 80 background app process(es)"}


state = {"freed": False}
try:
    os.environ.pop("COVENANT_MODEL_NO_TRIM", None)
    M.pick_model = lambda: PICK if state["freed"] else None
    M.readiness = lambda: dict(MEM_CASE)
    M.TRIM_HOOK = hook
    pick, note = M._pick_or_make_room()
    check("CAP1.1 the memory case: the keeper makes room once, then loads",
          pick == PICK and len(calls) == 1, (pick, note, len(calls)))
    m = (calls[0] or {}).get("measured") or {} if calls else {}
    check("CAP1.2 ...handing the remedy the measured free and needed memory as the road's condition",
          calls and calls[0].get("state") == "PRESENT" and m.get("free_gb") == 2.06 and m.get("needs_gb") == 2.6,
          calls[:1])

    calls.clear(); state["freed"] = False
    M.readiness = lambda: {"verdict": "FAIL", "why": "no weights under C:/m", "free_gb": 9.0}
    pick, note = M._pick_or_make_room()
    check("CAP1.3 not the memory case (no weights): nothing is trimmed", pick is None and not calls, note)

    M.readiness = lambda: dict(MEM_CASE)
    os.environ["COVENANT_MODEL_NO_TRIM"] = "1"
    pick, note = M._pick_or_make_room()
    check("CAP1.4 COVENANT_MODEL_NO_TRIM=1 turns it off", pick is None and not calls and "NO_TRIM" in note, note)
    os.environ.pop("COVENANT_MODEL_NO_TRIM", None)

    M.TRIM_HOOK = None
    pick, note = M._pick_or_make_room()
    check("CAP1.5 from a test program, with no hook, the live trim is never run", pick is None and not calls
          and "test" in note, note)

    # wiring: start() goes through it
    class Reached(Exception):
        pass

    def boom():
        raise Reached()

    M.alive = lambda: False
    M.BIN = sys.executable
    saved = M._pick_or_make_room
    M._pick_or_make_room = boom
    try:
        M.start(say=lambda *a: None)
        wired = False
    except Reached:
        wired = True
    finally:
        M._pick_or_make_room = saved
    check("CAP1.5b start() asks _pick_or_make_room for the weights (so the ask that needs room gets it)", wired)
finally:
    for k, v in real.items():
        setattr(M, k, v)

# ---- the ask log: what the server reused, and where the time went
d = {"timings": {"cache_n": 3890, "prompt_n": 13, "prompt_ms": 230.4, "prompt_per_second": 56.4,
                 "predicted_n": 25, "predicted_ms": 2156.0, "predicted_per_second": 11.6}}
r = M._rates(d)
check("CAP1.6 a row carries the tokens the server reused (cache_n) and the read and write milliseconds",
      r.get("cache_n") == 3890 and r.get("prompt_ms") == 230 and r.get("gen_ms") == 2156, r)
r2 = M._rates({"timings": {"prompt_n": 3900, "prompt_per_second": 56.0}})
check("CAP1.7 an older build that does not say cache_n leaves it out; nothing is guessed",
      "cache_n" not in r2 and r2.get("prompt_n") == 3900, r2)
# CAP1.8, behavioural: one ask through a fake server, its row read back from a temp ask log
import io, json, tempfile  # noqa: E401,E402


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


fake_body = json.dumps({"choices": [{"message": {"content": "hi"}}], "usage": {"completion_tokens": 3},
                        "timings": {"cache_n": 3890, "prompt_n": 13, "prompt_ms": 230.0, "predicted_n": 3,
                                    "predicted_ms": 260.0}}).encode()
saved = {k: getattr(M, k) for k in ("alive", "start", "ASKS", "_mark_used", "_watch_idle")}
saved_open = M.urllib.request.urlopen
td = tempfile.mkdtemp(prefix="cap1_")
try:
    state2 = {"up": False}

    def fake_start(say=None):
        state2["up"] = True
        return True, "up"
    M.alive = lambda: state2["up"]
    M.start = fake_start
    M._mark_used = lambda: None
    M._watch_idle = lambda: None
    M.ASKS = os.path.join(td, "asks.jsonl")
    M.urllib.request.urlopen = lambda req, timeout=None: _Resp(fake_body)
    M.ask([{"role": "user", "content": "x"}])          # the first ask finds the model down: cold
    M.ask([{"role": "user", "content": "y"}])          # the second finds it up: warm
    rows = [json.loads(l) for l in open(M.ASKS, encoding="utf-8") if l.strip()]
finally:
    for k, v in saved.items():
        setattr(M, k, v)
    M.urllib.request.urlopen = saved_open
check("CAP1.8 an ask's row says whether it had to load the model, and carries cache_n",
      [r.get("cold") for r in rows] == [True, False] and all(r.get("cache_n") == 3890 for r in rows), rows)

# ---- CAP1.9-1.12 tools/tetsu_replay.py, against fake servers (never the live one from here)
sys.path.insert(0, os.path.join(HERE, "tools"))
import tetsu_replay as TR  # noqa: E402


def fake_server(keeps_after_short):
    """A server whose one slot keeps the last prompt; with keeps_after_short it also restores a long prefix after a
    short ask (as a host cache does)."""
    mem = {"last": None, "saved": None}

    def post(url, body):
        sysmsg = body["messages"][0]["content"]
        n = len(sysmsg) // 4 + 10
        if mem["last"] == sysmsg or (keeps_after_short and mem["saved"] == sysmsg):
            read = 10
        else:
            read = n
        if n > 100:
            mem["saved"] = sysmsg
        mem["last"] = sysmsg
        return {"choices": [{"message": {"content": "fine"}}], "timings": {"prompt_n": read, "cache_n": n - read,
                                                                             "prompt_ms": read * 18, "predicted_ms": 90}}
    return post


SYS = "rules " * 800
rows_keep = TR.run(fake_server(True), "u", SYS, between=32, say=lambda *a: None)
s_keep = TR.summary(rows_keep, None)
rows_evict = TR.run(fake_server(False), "u", SYS, between=32, say=lambda *a: None)
s_evict = TR.summary(rows_evict, None)
check("CAP1.9 the replay runs A, A, then A after 1 and after 32 short asks", [r["step"] for r in rows_keep]
      == ["A1", "A2 (again)", "A after 1", "A after 32"], [r["step"] for r in rows_keep])
check("CAP1.10 a server that keeps the prefix reads as reused throughout; one that loses it to short asks reads as "
      "evicted", s_keep["reading"].startswith("reused throughout") and s_evict["reading"].startswith("reused back to back"),
      (s_keep["reading"], s_evict["reading"]))
check("CAP1.11 the rows keep numbers and an output hash, never the text", all("fine" not in json.dumps(r)
                                                                              for r in rows_keep + rows_evict))
_saved_alive = M.alive
M.alive = lambda: False
try:
    rc = TR.main([])
finally:
    M.alive = _saved_alive
check("CAP1.12 the replay refuses when the model is not up (it never starts it)", rc == 2, rc)

print("\nCAP1: %d/%d passed" % (n_total - n_fail, n_total))
sys.exit(1 if n_fail else 0)
