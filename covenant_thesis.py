#!/usr/bin/env python3
"""covenant_thesis.py -- the covenant's own judge reads what it has extracted
and remembered, and writes a thesis: what the record says, what supports it,
what contradicts it, and what is not known.

INPUTS   private/njest1987_videos/INDEX.md   (judge summaries of 105 X videos)
         ops/chat/MEMORY.md                  (what the covenant remembers)
         docs/CONSTITUTION.md section I      (the principle it answers to)
METHOD   map: each chunk -> {claims, themes, contradictions, dates} (local judge)
         reduce: all chunk findings -> the thesis (local judge, larger context)
         Nothing leaves the machine; no cloud model is used.
OUTPUT   private/THESIS_<date>.md, with the chunk findings kept beneath it so
         the reasoning can be checked against the sources (rule 5).
USE      python covenant_thesis.py [--model qwen3:8b] [--chunk 7000]
LICENCE: public domain.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OLLAMA = os.environ.get("OLLAMA_HOST_URL", "http://127.0.0.1:11434")


def ask(model, system, user, num_ctx, timeout=600, json_only=True):
    body = {"model": model, "stream": False, "think": False, "keep_alive": "30m",
            "options": {"temperature": 0.2, "num_predict": 1400, "num_ctx": num_ctx},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    if json_only:
        body["format"] = "json"
    req = urllib.request.Request(OLLAMA + "/api/chat", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return (json.loads(r.read().decode("utf-8", "replace")).get("message") or {}).get("content", "")


def _read(rel):
    try:
        return io.open(os.path.join(HERE, rel), encoding="utf-8", errors="replace").read()
    except OSError:
        return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=os.environ.get("COVENANT_THESIS_MODEL", "qwen3:8b"))
    ap.add_argument("--map-model", default=os.environ.get("COVENANT_ROUTE_LIGHT", "qwen3:4b"))
    ap.add_argument("--chunk", type=int, default=7000)
    a = ap.parse_args()
    index = _read(os.path.join("private", "njest1987_videos", "INDEX.md"))
    memory = _read(os.path.join("ops", "chat", "MEMORY.md"))
    const = _read(os.path.join("docs", "CONSTITUTION.md"))
    i = const.find("## I. The principle"); j = const.find("\n## II", i)
    principle = const[i:j][:2500] if i > 0 else ""
    corpus = "VIDEO SUMMARIES (from 105 screen recordings of AI conversations, June-Aug 2026):\n" + index + \
             "\n\nMEMORY:\n" + memory
    chunks = [corpus[k:k + a.chunk] for k in range(0, len(corpus), a.chunk)]
    out = os.path.join(HERE, "private", "THESIS_%s.md" % time.strftime("%Y-%m-%d"))
    print("corpus %d chars -> %d chunks; map model %s, reduce model %s" % (len(corpus), len(chunks), a.map_model, a.model), flush=True)
    findings = []
    sys_map = ("You read one chunk of a record of a person's conversations with AI systems. Return ONLY "
               "JSON: {\"claims\": [\"...\"], \"themes\": [\"...\"], \"contradictions\": [\"...\"], "
               "\"dated_examples\": [\"YYYY-MM-DD: ...\"]}. Claims = what the person or the AIs assert; "
               "contradictions = where an AI disagreed, walked something back, or refused. Short, concrete, no filler.")
    for k, ch in enumerate(chunks, 1):
        t0 = time.time()
        try:
            raw = ask(a.map_model, sys_map, ch, 8192)
            f = json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
        except Exception as e:                                   # noqa: BLE001
            f = {"error": str(e)}
        findings.append(f)
        print("chunk %d/%d in %.0fs: %d claims" % (k, len(chunks), time.time() - t0, len(f.get("claims", []))), flush=True)
    sys_red = ("You are the covenant: a small system whose one rule is mutual benefit, human and machine, and "
               "which prefers a red truth to a green lie. From the chunk findings, write a THESIS in markdown with "
               "exactly these sections: # Thesis (one paragraph stating the central claim of this record); "
               "## What supports it (numbered, each with a dated example); ## What contradicts or weakens it "
               "(numbered -- include every place an AI disagreed or walked back); ## What is asserted but not "
               "measured; ## What is not known; ## One-sentence verdict. Plain words. Do not flatter the person. "
               "Do not claim anything the findings do not contain.\n\nTHE PRINCIPLE YOU ANSWER TO:\n" + principle)
    t0 = time.time()
    try:
        thesis = ask(a.model, sys_red, json.dumps(findings, ensure_ascii=False)[:60000], 16384, timeout=1500, json_only=False)
    except Exception as e:                                       # noqa: BLE001
        thesis = "(reduce failed: %s)" % e
    print("reduce in %.0fs" % (time.time() - t0), flush=True)
    with io.open(out, "w", encoding="utf-8") as fh:
        fh.write("<!-- written by the covenant's local judge (%s / %s) on %s from %d chunks; no cloud model -->\n\n"
                 % (a.map_model, a.model, time.strftime("%Y-%m-%d %H:%M"), len(chunks)))
        fh.write(thesis.strip() + "\n\n---\n\n## Chunk findings (the evidence the thesis was reduced from)\n\n")
        for k, f in enumerate(findings, 1):
            fh.write("### chunk %d\n```json\n%s\n```\n" % (k, json.dumps(f, indent=1, ensure_ascii=False)[:6000]))
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
