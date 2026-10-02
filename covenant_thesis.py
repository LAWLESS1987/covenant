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
USE      python covenant_thesis.py [--chunk 7000]
Restored 2026-10-02 through the local on-demand keeper. Legacy model flags
remain accepted as labels; hardware selection belongs to covenant_model.
LICENCE: public domain.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS_USED = set()
def ask(model, system, user, num_ctx, timeout=600, json_only=True):
    from covenant_local_analysis import complete
    raw, meta = complete(system, user, max_tokens=2200, timeout=timeout)
    MODELS_USED.add(str(meta.get("model", "unknown")))
    return raw


def _read(rel):
    try:
        return io.open(os.path.join(HERE, rel), encoding="utf-8", errors="replace").read()
    except OSError:
        return ""


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="on-demand local model")
    ap.add_argument("--map-model", default="on-demand local model")
    ap.add_argument("--chunk", type=int, default=7000)
    ap.add_argument("--reduce-only", metavar="THESIS_MD", default="",
                    help="skip the map: reuse the chunk findings written into an earlier THESIS file")
    ap.add_argument("--group", type=int, default=6, help="chunks per intermediate reduce")
    a = ap.parse_args(argv)
    if a.chunk < 256 or a.chunk > 12000 or a.group < 1 or a.group > 12:
        ap.error("chunk must be 256..12000 and group 1..12")
    index = _read(os.path.join("private", "njest1987_videos", "INDEX.md"))
    memory = _read(os.path.join("ops", "chat", "MEMORY.md"))
    const = _read(os.path.join("docs", "CONSTITUTION.md"))
    i = const.find("## I. The principle"); j = const.find("\n## II", i)
    principle = const[i:j][:2500] if i > 0 else ""
    if not index.strip() and not memory.strip() and not a.reduce_only:
        print("No source index or conversation memory is available; no thesis written."); return 2
    corpus = "VIDEO SUMMARY INDEX (coverage is that of the supplied index):\n" + index + \
             "\n\nMEMORY:\n" + memory
    chunks = [corpus[k:k + a.chunk] for k in range(0, len(corpus), a.chunk)]
    out = os.path.join(HERE, "private", "THESIS_%s.md" % time.strftime("%Y-%m-%d"))
    print("corpus %d chars -> %d chunks; map model %s, reduce model %s" % (len(corpus), len(chunks), a.map_model, a.model), flush=True)
    findings = []
    if a.reduce_only:
        prev = _read(os.path.relpath(a.reduce_only, HERE)) if not os.path.isabs(a.reduce_only) else \
            io.open(a.reduce_only, encoding="utf-8", errors="replace").read()
        for blk in re.findall(r"### chunk \d+\n```json\n(.*?)\n```", prev, re.S):
            try:
                findings.append(json.loads(blk))
            except ValueError:
                findings.append({"error": "unparseable chunk"})
        chunks = [""] * len(findings)
        print("reduce-only: %d chunk findings reused from %s" % (len(findings), a.reduce_only), flush=True)
    sys_map = ("You read one chunk of a record of a person's conversations with AI systems. Return ONLY "
               "JSON: {\"claims\": [\"...\"], \"themes\": [\"...\"], \"contradictions\": [\"...\"], "
               "\"dated_examples\": [\"YYYY-MM-DD: ...\"]}. Claims = what the person or the AIs assert; "
               "contradictions = where an AI disagreed, walked something back, or refused. Short, concrete, no filler.")
    for k, ch in enumerate(chunks, 1):
        if a.reduce_only:
            break
        t0 = time.time()
        try:
            raw = ask(a.map_model, sys_map, ch, 8192)
            from covenant_local_analysis import parse_object
            f = parse_object(raw)
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
    sys_mid = ("Condense these chunk findings from a record of one person's conversations with AI systems. "
               "Return ONLY JSON: {'claims': [...], 'contradictions': [...], 'dated_examples': [...], "
               "'unmeasured': [...]} -- keep every distinct claim once, keep every contradiction and every "
               "dated example, drop repeats and filler. Short, concrete.").replace("'", '"')
    def condense(part, label):
        t0 = time.time()
        try:
            raw = ask(a.map_model, sys_mid, json.dumps(part, ensure_ascii=False)[:24000], 8192, timeout=900)
            if "{" not in raw:
                raise ValueError("no JSON in reply (%d chars)" % len(raw))
            from covenant_local_analysis import parse_object
            c = parse_object(raw)
        except Exception as e:                                   # noqa: BLE001
            c = {"error": str(e), "chunks": label}
        print("condense chunks %s in %.0fs: %d claims%s" % (label, time.time() - t0, len(c.get("claims", [])),
                                                            (" (" + c["error"] + ")") if "error" in c else ""), flush=True)
        return c
    condensed = []
    for g in range(0, len(findings), a.group):
        part = findings[g:g + a.group]
        c = condense(part, "%d-%d" % (g + 1, g + len(part)))
        if "error" in c and len(part) > 1:                       # split and retry, once
            h = len(part) // 2
            condensed.append(condense(part[:h], "%d-%d retry" % (g + 1, g + h)))
            condensed.append(condense(part[h:], "%d-%d retry" % (g + h + 1, g + len(part))))
        else:
            condensed.append(c)
    failed = [c["chunks"] for c in condensed if "error" in c]
    if failed:
        print("WARNING: condensates missing for chunks %s -- the thesis below does not cover them" % failed, flush=True)
    t0 = time.time()
    try:
        thesis = ask(a.model, sys_red, json.dumps(condensed, ensure_ascii=False)[:20000], 8192, timeout=1500, json_only=False)
    except Exception as e:                                       # noqa: BLE001
        thesis = "(reduce failed: %s)" % e
    print("reduce in %.0fs over %d condensates" % (time.time() - t0, len(condensed)), flush=True)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with io.open(out, "a", encoding="utf-8") as fh:
        fh.write("<!-- written by local analysis model(s) %s on %s from %d chunks; no cloud model -->\n"
                 % (", ".join(sorted(MODELS_USED)) or "unverified", time.strftime("%Y-%m-%d %H:%M"), len(chunks)))
        fh.write("<!-- coverage: %d of %d condensates succeeded%s -->\n\n"
                 % (len(condensed) - len(failed), len(condensed),
                    ("; MISSING chunks " + ", ".join(failed)) if failed else ""))
        fh.write(thesis.strip() + "\n\n---\n\n## Condensates (what the judge actually reduced)\n\n")
        for k, c in enumerate(condensed, 1):
            fh.write("### group %d\n```json\n%s\n```\n" % (k, json.dumps(c, indent=1, ensure_ascii=False)[:8000]))
        fh.write("\n---\n\n## Chunk findings (the evidence the thesis was reduced from)\n\n")
        for k, f in enumerate(findings, 1):
            fh.write("### chunk %d\n```json\n%s\n```\n" % (k, json.dumps(f, indent=1, ensure_ascii=False)[:6000]))
    print("wrote", out)
    return 2 if failed or any("error" in f for f in findings) or thesis.startswith("(reduce failed:") else 0


if __name__ == "__main__":
    from covenant_local_analysis import cleanup
    try:
        raise SystemExit(main())
    finally:
        cleanup()
