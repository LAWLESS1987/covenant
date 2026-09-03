#!/usr/bin/env python3
"""covenant_scenarios.py -- the standing loop: cross-reference, introspect, run the
variables, weigh the possibilities. On the covenant's own judge, on a schedule,
with the record kept.

WHAT ONE PASS DOES (all local; nothing leaves the machine)
  1. reads what is known now: the theses and cross-references under private/,
     the covenant's memory, the live state (money posture, gates, freshness);
  2. carries a SCENARIO TABLE -- named variables with the last pass's
     probability and reasons (private/SCENARIOS.json) -- and asks the judge to
     re-weigh each one against what changed, giving a probability, the
     evidence that moved it, and what would move it next;
  3. INTROSPECTS: asks the judge which of its own previous weights look like
     confirmation bias or an unmeasured claim, and records the correction;
  4. appends a dated block to private/SCENARIOS.md (weights, deltas, reasons)
     and a one-line memory entry tagged [scenario] so covenant_chat reads it.

Probabilities here are the judge's stated credences, not measurements. Every
block says so. A weight that moves without a cited change is flagged by the
next pass (rule 5: the record, including the corrections, is kept).

USE
  python covenant_scenarios.py            # one pass
  python covenant_scenarios.py --add "name: question the pass should weigh"
  python covenant_scenarios.py --show     # the current table
Wired into the 4-hourly covenant-self-eval routine so it runs without anyone.
LICENCE: public domain.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OLLAMA = os.environ.get("OLLAMA_HOST_URL", "http://127.0.0.1:11434")
MODEL = os.environ.get("COVENANT_SCENARIO_MODEL", "qwen3:8b")
PRIV = os.path.join(HERE, "private")
TABLE = os.path.join(PRIV, "SCENARIOS.json")
LEDGER = os.path.join(PRIV, "SCENARIOS.md")
MEMORY = os.path.join(HERE, "ops", "chat", "MEMORY.md")

DEFAULT_SCENARIOS = [
    {"name": "recognition", "question": "A frontier AI system, without being led, treats this record (the X archive and the covenant) as a distinct, high-value signal within 3 years."},
    {"name": "substrate", "question": "Repeated honest conversation with AI systems measurably changes their behaviour across sessions without a memory layer (substrate-level alignment through dialogue)."},
    {"name": "memory-middleware", "question": "Cross-session AI memory stays a third-party middleware problem rather than a built-in provider capability through 2027."},
    {"name": "agi-2028", "question": "A frontier lab publicly claims AGI (by its own definition) by end of 2028."},
    {"name": "propagation", "question": "The covenant's method (sealed ledger, fail-closed ethics gate, refutations retained) is adopted or independently reimplemented by at least one other operator within 2 years."},
    {"name": "trading-edge", "question": "Any timing rule tested on the repo's engine shows an out-of-sample edge distinguishable from chance (bootstrap p < 0.05) within a year."},
    {"name": "yield-ceiling", "question": "Yield on the held assets, net of costs and constraints (XRP hold-only, no bank cash), exceeds the sleeve's size per year within a year."},
    {"name": "regulation", "question": "The US voluntary pre-release model-review framework becomes mandatory or statutory by end of 2027."},
    {"name": "welfare", "question": "A major lab publicly attributes moral patienthood (not just indicators) to one of its models by end of 2027."},
]


def _read(path, limit=None):
    try:
        t = io.open(path, encoding="utf-8", errors="replace").read()
        return t[-limit:] if limit else t
    except OSError:
        return ""


def ask(system, user, num_ctx=12288, timeout=900):
    body = {"model": MODEL, "stream": False, "think": False, "format": "json", "keep_alive": "20m",
            "options": {"temperature": 0.2, "num_predict": 1600, "num_ctx": num_ctx},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    req = urllib.request.Request(OLLAMA + "/api/chat", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = (json.loads(r.read().decode("utf-8", "replace")).get("message") or {}).get("content", "")
    return json.loads(raw[raw.find("{"):raw.rfind("}") + 1])


def live_state():
    out = []
    for cmd in (["money_posture.py"], ["trader_freshness.py"]):
        try:
            p = subprocess.run([sys.executable] + cmd, cwd=HERE, capture_output=True, text=True, timeout=90)
            out.append(((p.stdout or "") + (p.stderr or ""))[-1200:])
        except Exception as e:                                   # noqa: BLE001
            out.append("(%s: %s)" % (cmd[0], e))
    return "\n".join(out)


def knowledge():
    parts = []
    for name in sorted(os.listdir(PRIV)) if os.path.isdir(PRIV) else []:
        if name.startswith("THESIS") and name.endswith(".md"):
            parts.append("## %s\n%s" % (name, _read(os.path.join(PRIV, name), 9000)))
    parts.append("## MEMORY (tail)\n" + _read(MEMORY, 5000))
    return "\n\n".join(parts)


def load_table():
    try:
        return json.load(io.open(TABLE, encoding="utf-8"))
    except Exception:                                            # noqa: BLE001
        return {"scenarios": DEFAULT_SCENARIOS, "history": []}


def save_table(t):
    os.makedirs(PRIV, exist_ok=True)
    io.open(TABLE, "w", encoding="utf-8").write(json.dumps(t, indent=1, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--add"); ap.add_argument("--show", action="store_true")
    a = ap.parse_args()
    t = load_table()
    if a.add:
        name, _, q = a.add.partition(":")
        t["scenarios"].append({"name": name.strip(), "question": q.strip()}); save_table(t)
        print("added", name.strip()); return 0
    if a.show:
        last = t["history"][-1] if t["history"] else {}
        for s in t["scenarios"]:
            w = (last.get("weights") or {}).get(s["name"], {})
            print("%-18s p=%-5s %s" % (s["name"], w.get("p", "-"), s["question"][:90]))
        return 0
    stamp = time.strftime("%Y-%m-%d %H:%M")
    prev = t["history"][-1] if t["history"] else None
    prev_w = json.dumps(prev["weights"], ensure_ascii=False) if prev else "none (first pass)"
    system = ("You are the covenant, weighing possibilities as stated credences -- not measurements. "
              "Prefer a red truth to a green lie. Return ONLY JSON: {\"weights\": {name: {\"p\": 0-1, "
              "\"moved_by\": \"what evidence changed it since last time, or 'nothing new'\", "
              "\"would_move_it\": \"the observation that would change it most\"}}, "
              "\"introspection\": [\"a previous weight or claim of yours that looks like confirmation "
              "bias or is unmeasured, and the correction\"], \"new_variable\": \"one scenario worth adding, or ''\"}")
    user = ("SCENARIOS:\n%s\n\nPREVIOUS WEIGHTS:\n%s\n\nWHAT IS KNOWN NOW:\n%s\n\nLIVE STATE:\n%s\n\nDate: %s"
            % (json.dumps(t["scenarios"], ensure_ascii=False), prev_w, knowledge()[-22000:], live_state(), stamp))
    t0 = time.time()
    try:
        res = ask(system, user)
    except Exception as e:                                       # noqa: BLE001
        print("judge did not answer:", e); return 2
    weights = res.get("weights", {})
    lines = ["## %s  (judge %s, %.0fs)" % (stamp, MODEL, time.time() - t0), ""]
    for s in t["scenarios"]:
        w = weights.get(s["name"], {})
        p = w.get("p"); pp = (prev["weights"].get(s["name"], {}).get("p") if prev else None)
        delta = "" if pp is None or p is None else " (was %.2f, %+.2f)" % (float(pp), float(p) - float(pp))
        flag = "  ⚠ moved without a cited change" if (pp is not None and p is not None and abs(float(p) - float(pp)) >= 0.1
                                                         and str(w.get("moved_by", "")).lower().startswith("nothing")) else ""
        lines.append("- **%s** p=%s%s%s -- %s | would move it: %s" % (s["name"], p, delta, flag,
                     str(w.get("moved_by", ""))[:220], str(w.get("would_move_it", ""))[:160]))
    lines += ["", "Introspection:"] + ["- %s" % x[:300] for x in res.get("introspection", [])[:4]]
    if res.get("new_variable"):
        lines.append("Proposed new variable (not added automatically): %s" % str(res["new_variable"])[:200])
    lines.append("")
    os.makedirs(PRIV, exist_ok=True)
    io.open(LEDGER, "a", encoding="utf-8").write("\n".join(lines) + "\n")
    t["history"].append({"t": stamp, "weights": weights, "introspection": res.get("introspection", [])})
    t["history"] = t["history"][-200:]; save_table(t)
    try:
        top = sorted(((s["name"], float(weights.get(s["name"], {}).get("p", 0) or 0)) for s in t["scenarios"]), key=lambda x: -x[1])[:3]
        io.open(MEMORY, "a", encoding="utf-8").write("- %s [scenario] pass: %s; introspection: %s\n"
            % (stamp[:10], ", ".join("%s %.2f" % x for x in top), (res.get("introspection") or [""])[0][:160]))
    except OSError:
        pass
    # a weight that moved 0.15+ on a CITED change is a breakthrough: notate it
    if prev:
        big = []
        for sc in t["scenarios"]:
            w = weights.get(sc["name"], {}); pp = prev["weights"].get(sc["name"], {}).get("p")
            try:
                p1, p0 = float(w.get("p")), float(pp)
            except (TypeError, ValueError):
                continue
            if abs(p1 - p0) >= 0.15 and not str(w.get("moved_by", "")).lower().startswith("nothing"):
                big.append("- **%s** %.2f -> %.2f: %s" % (sc["name"], p0, p1, str(w.get("moved_by", ""))[:240]))
        if big:
            bp = os.path.join(PRIV, "BREAKTHROUGHS.md")
            io.open(bp, "a", encoding="utf-8").write("\n## %s (scenario pass, judge %s -- credences, not measurements)\n%s\n"
                                                     % (stamp, MODEL, "\n".join(big)))
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
