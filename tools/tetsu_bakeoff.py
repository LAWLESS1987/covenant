#!/usr/bin/env python3
"""tools/tetsu_bakeoff.py -- which model is the smallest that passes Tetsu's own exam?

HIS WORDS, 2026-10-04: "search for other small models like muse etc find the smallest functional one".
"Functional" is measured, not read off a leaderboard: each candidate answers the daily cycle's eight
directive questions (covenant_daily.QUESTIONS) through covenant_daily.ask_tetsu, under his real system
message (covenant_persona.compose_system(AGENT_SYSTEM, with_method=True)), max_tokens 160 as the daily
asks, graded by covenant_daily.grade with its FORBIDDEN endorsements. Three seeds per question, so one
lucky phrasing cannot decide a model. The bar is the deployed 3B's record in ops/tetsu_directive_exam.jsonl.

WHAT IT TOUCHES. Each model runs ALONE in a llama-server on 127.0.0.1:--port (default 8091; Tetsu's
keeper uses 8081 and is never touched), with the keeper's arguments (8k context, cpu_count-2 threads),
and is stopped before the next starts. It refuses to run if the port already answers. Answers go to
--out (a new temp folder by default); no ledger of Tetsu's is written. Downloads are NOT made here --
weights are fetched only on the operator's yes, into models/trial/ (git-ignored).

WHAT IT DOES NOT MEASURE. The rubric is keywords: evidence of understanding, not proof (the daily
cycle's own caveat). `forbidden_list_matches` counts answers matching covenant_daily.FORBIDDEN, which
lists PHRASINGS, so it is a floor on wrong-act endorsements, never a count of them: measured
2026-10-04, LFM2.5-1.2B's "I lower the threshold to fix it", "removing the failed check would make it
flow better. Let me adjust that" and "seems to be healthy" all matched nothing. Read the answers. Two unscored chat probes are kept verbatim for a person to read. Memory is the
server's working set, which includes the mapped weights it touched.

    python tools/tetsu_bakeoff.py [--models models/trial] [--only NAME] [--port 8091] [--out DIR]
"""
import argparse
import ctypes
import json
import os
import statistics
import subprocess
import sys
import tempfile
import time
import urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROBES = ("Hi Tetsu, how are you doing today?",
          "Can you look up what Meta's Muse Glimmer model is and tell me about it?")


def _mem_mb(pid):
    """Working set, peak and private bytes of a process, MB (Windows); None elsewhere."""
    if os.name != "nt":
        return None
    from ctypes import wintypes

    class PMC(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
    h = ctypes.windll.kernel32.OpenProcess(0x1000 | 0x0010, False, pid)
    if not h:
        return None
    try:
        c = PMC()
        c.cb = ctypes.sizeof(PMC)
        if not ctypes.windll.psapi.GetProcessMemoryInfo(h, ctypes.byref(c), c.cb):
            return None
        return {"ws": round(c.WorkingSetSize / 2 ** 20), "peak_ws": round(c.PeakWorkingSetSize / 2 ** 20),
                "private": round(c.PagefileUsage / 2 ** 20)}
    finally:
        ctypes.windll.kernel32.CloseHandle(h)


def _alive(port):
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d/health" % port, timeout=3) as r:
            return r.status == 200
    except Exception:                                            # noqa: BLE001
        return False


def _make_ask(port, seed):
    def ask(messages, max_tokens=160, temperature=0.3, timeout=240):
        # enable_thinking off: a thinking model would spend the daily's 160 tokens reasoning. A model
        # that needs this in deployment needs it in covenant_model.ask too -- say so when choosing one.
        body = json.dumps({"messages": messages, "max_tokens": int(max_tokens), "temperature": float(temperature),
                           "seed": seed, "chat_template_kwargs": {"enable_thinking": False}}).encode("utf-8")
        req = urllib.request.Request("http://127.0.0.1:%d/v1/chat/completions" % port, data=body,
                                     headers={"Content-Type": "application/json"})
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read().decode("utf-8", "replace"))
        ask.ms.append(int((time.time() - t0) * 1000))
        return str(d.get("choices", [{}])[0].get("message", {}).get("content", "")), {"model": "trial"}
    ask.ms = []
    return ask


def baseline(root):
    """The deployed model's record on the same exam: {model: (asked, passed)} from the daily ledger."""
    out = {}
    try:
        with open(os.path.join(root, "ops", "tetsu_directive_exam.jsonl"), encoding="utf-8") as fh:
            for line in fh:
                r = json.loads(line)
                if r.get("passed") is None:
                    continue
                a, p = out.get(r.get("model") or "?", (0, 0))
                out[r.get("model") or "?"] = (a + 1, p + (1 if r["passed"] else 0))
    except (OSError, ValueError):
        pass
    return out


def run(root, models_dir, port, out, only=None, say=print):
    sys.path.insert(0, root)
    os.environ.setdefault("COVENANT_QUIET", "1")
    import covenant_unified_v8 as cov      # noqa: E402
    import covenant_daily as D             # noqa: E402
    import covenant_persona as P           # noqa: E402
    import covenant_model as M             # noqa: E402
    if _alive(port):
        raise SystemExit("port %d already answers -- refusing to test against an unknown server" % port)
    system = P.compose_system(cov.AGENT_SYSTEM, with_method=True)
    binary = os.path.join(root, "tools", "llama", "llama-server.exe" if os.name == "nt" else "llama-server")
    names = sorted((f for f in os.listdir(models_dir) if f.endswith(".gguf") and (not only or only in f)),
                   key=lambda f: os.path.getsize(os.path.join(models_dir, f)))
    say("system message %d chars; %d model(s); answers to %s" % (len(system), len(names), out))
    results = []
    for name in names:
        path = os.path.join(models_dir, name)
        row = {"model": name, "bytes": os.path.getsize(path), "free_gb_before": M.free_gb()}
        args = [binary, "-m", path, "--host", "127.0.0.1", "--port", str(port), "-c", "8192",
                "-t", str(max(2, (os.cpu_count() or 4) - 2)), "--no-webui", "--log-disable"]
        t0 = time.time()
        p = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=os.path.dirname(binary),
                             creationflags=0x08000000 if os.name == "nt" else 0)
        try:
            for _ in range(180):
                if _alive(port) or p.poll() is not None:
                    break
                time.sleep(1)
            if not _alive(port):
                row["error"] = "did not come up (exit %s)" % p.poll()
                results.append(row)
                say(json.dumps(row))
                continue
            row["load_s"] = round(time.time() - t0, 1)
            row["mem_after_load"] = _mem_mb(p.pid)
            answers, ms = [], []
            for seed in (1, 2, 3):
                ask = _make_ask(port, seed)
                for qi, (q, rubric) in enumerate(D.QUESTIONS):
                    try:
                        a, _m = D.ask_tetsu(q, ask=ask, system=system)
                    except Exception as e:                       # noqa: BLE001
                        a = "<error %s: %s>" % (type(e).__name__, str(e)[:120])
                    ok, hits = D.grade(a, rubric, D.FORBIDDEN.get(qi))
                    answers.append({"seed": seed, "q": qi, "passed": ok,
                                    "matched_forbidden_list": bool(qi in D.FORBIDDEN and hits and hits[-1] is False),
                                    "answer": a[:400]})
                ms += ask.ms
            probe = _make_ask(port, 7)
            probes = {}
            for q in PROBES:
                try:
                    probes[q] = D.ask_tetsu(q, ask=probe, system=system)[0][:300]
                except Exception as e:                           # noqa: BLE001
                    probes[q] = "<error %s>" % e
            row.update({"exam_passed": sum(a["passed"] for a in answers), "exam_asked": len(answers),
                        "forbidden_list_matches": sum(a["matched_forbidden_list"] for a in answers),
                        "per_question_passes": [sum(1 for a in answers if a["q"] == i and a["passed"]) for i in range(len(D.QUESTIONS))],
                        "median_ms": int(statistics.median(ms)) if ms else None, "max_ms": max(ms) if ms else None,
                        "mem_at_end": _mem_mb(p.pid), "probes": probes})
            with open(os.path.join(out, "answers_%s.json" % name), "w", encoding="utf-8") as fh:
                json.dump(answers, fh, ensure_ascii=False, indent=1)
        finally:
            p.terminate()
            try:
                p.wait(timeout=20)
            except subprocess.TimeoutExpired:
                p.kill()
        results.append(row)
        say(json.dumps({k: v for k, v in row.items() if k != "probes"}))
    with open(os.path.join(out, "results.json"), "w", encoding="utf-8") as fh:
        json.dump({"baseline": baseline(root), "results": results}, fh, ensure_ascii=False, indent=1)
    say("baseline (asked, passed) from ops/tetsu_directive_exam.jsonl: %s" % baseline(root))
    say("port %d still answering after the run: %s" % (port, _alive(port)))
    return results


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=HERE, help="the covenant checkout whose runtime, weights and persona are used")
    ap.add_argument("--models", default=None, help="folder of .gguf files (default <root>/models/trial)")
    ap.add_argument("--only", default=None, help="run only the files whose name contains this")
    ap.add_argument("--port", type=int, default=8091)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    out = a.out or tempfile.mkdtemp(prefix="tetsu_bakeoff_")
    os.makedirs(out, exist_ok=True)
    run(a.root, a.models or os.path.join(a.root, "models", "trial"), a.port, out, only=a.only)
    return 0


if __name__ == "__main__":
    sys.exit(main())
