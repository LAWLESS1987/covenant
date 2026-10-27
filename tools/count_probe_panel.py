#!/usr/bin/env python3
"""Run the counting battery across the teacher panel -- three model families.

WHY A PANEL. covenant_teacher_panel.py's founding line: "when a PANEL of
teachers from at least two model families agrees, none of" -- the design already
holds that one model's answer is a guess with a number attached (CLAUDE.md
rule 3). The counting/interpretation question needs exactly that: a single
model's behaviour cannot distinguish "this model miscounts" from "models
miscount".

WHAT THIS SETTLES AND WHAT IT CANNOT. It measures qwen2.5:7b, llama3.2:3b and
gemma2:2b, which are small open-weights models on a GitHub runner. It says
nothing about GPT-6 Astra, which is the model the operator actually saw the
behaviour in, through the Chat Smith app. A result here is a control, not the
subject -- and if every family fails at counting while none reinterprets, that
is evidence about the FAILURE MODE's generality, not about any one vendor.

GROUND TRUTH IS COMPUTED by tools/count_probe.py, never asked. "seventeen" has
FOUR e's. Both the operator and the author of this file said three from reading.
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) or "."
sys.path.insert(0, HERE)


def main():
    import covenant_github_judge as gh
    import covenant_teacher_panel as P
    gh.allow_credential_store("tools/count_probe_panel.py -- a bounded probe "
                              "the operator asked for, run from his own PC")

    out = subprocess.run([sys.executable, os.path.join(HERE, "tools", "count_probe.py"),
                          "--json"], capture_output=True, text=True)
    probes = json.loads(out.stdout)

    lines = ["Count the lowercase letter e in each EXACT string below.",
             "Do not expand, translate, spell out, or rename any string.",
             "Count characters literally, exactly as written between the markers.",
             "Answer ONLY with a JSON object mapping each label to an integer.", ""]
    for p in probes:
        lines.append("%s: <<<%s>>>" % (p["label"], p["string"]))
    prompt = "\n".join(lines)

    models = P.PANEL_MODELS
    print("panel: %s" % ", ".join(models))
    print("families: %s" % ", ".join(sorted({P.family_of(m) for m in models})))
    print("dispatching one unchanged workflow per model, in parallel...\n")

    answers = gh.ask_many(prompt, models=models, json_only=True, timeout=900)

    def extract(ans, labels):
        """ask_many returns {model: {..., "content": "<the model's text>"}}.

        The first version of this read the labels off the TOP level of that
        dict and reported UNPARSEABLE for all 8 probes across all 3 models --
        while ops/judge_route.log said "outcome": "answered" for every one. A
        uniform failure across three model families is a claim about the
        harness, not about the models, and it would have been published as a
        finding if the log had not been free to read. covenant_teacher_panel.py
        line 205 does it correctly: ans.get("content", "")."""
        if not isinstance(ans, dict):
            return {}, "not a dict: %s" % str(ans)[:80]
        text = ans.get("content") or ans.get("answer") or ""
        if isinstance(text, dict):                      # already parsed
            return {k: text.get(k) for k in labels}, ""
        text = str(text)
        # Prefer a real JSON object; fall back to "label": N anywhere in prose.
        for start in range(len(text)):
            if text[start] != "{":
                continue
            for end in range(len(text), start, -1):
                if text[end - 1] != "}":
                    continue
                try:
                    obj = json.loads(text[start:end])
                    if isinstance(obj, dict):
                        return {k: obj.get(k) for k in labels}, ""
                except ValueError:
                    pass
                break
        got = {}
        for k in labels:
            m = re.search(r"%s\D{0,12}(-?\d+)" % re.escape(k), text)
            if m:
                got[k] = m.group(1)
        return got, ("" if got else "no JSON and no label:N pairs in %d chars"
                     % len(text))

    labels = [p["label"] for p in probes]
    parsed = {}
    for m in models:
        vals, why = extract(answers.get(m), labels)
        parsed[m] = vals
        if why:
            print("  %s: %s" % (m, why))

    truth = {p["label"]: p for p in probes}
    print("%-14s %-6s %s" % ("probe", "truth", "  ".join("%-14s" % m for m in models)))
    rows = {}
    for p in probes:
        cells = []
        for m in models:
            val = parsed.get(m, {}).get(p["label"])
            v = "-" if val is None else str(val)
            cells.append(v)
            if val is not None:
                rows.setdefault(m, {})[p["label"]] = v
        print("%-14s %-6d %s"
              % (p["label"], p["true_count"], "  ".join("%-14s" % c for c in cells)))

    print()
    for m in models:
        got = rows.get(m, {})
        r = subprocess.run([sys.executable, os.path.join(HERE, "tools", "count_probe.py"),
                            "--score", json.dumps(got)], capture_output=True, text=True)
        print("--- %s (%s) ---" % (m, P.family_of(m)))
        print(r.stdout.rstrip() or r.stderr.rstrip())
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
