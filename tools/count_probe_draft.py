#!/usr/bin/env python3
"""The operator's OWN draft method, run against the panel -- as a control on mine.

WHY. tools/count_probe_panel.py asked all eight probes in ONE prompt, with an
explicit "Do not expand, translate, spell out, or rename any string" and a JSON
schema. It found zero interpretation failures and I reported that.

His objection, 2026-09-17: try the DRAFT's method against multi models. He is
right that mine is a different experiment. A batched prompt that forbids
expansion, and asks for JSON, is a heavily scaffolded condition -- exactly the
scaffolding that could SUPPRESS the behaviour being hunted. Reporting "it did
not reproduce" from a condition designed to prevent it is circular.

His method, from the draft, verbatim:

    "Count the letter e in the exact string '17'"
    ... compared with the same request for "seventeen".

Two separate asks. Plain language. "the exact string" is the ONLY guard, and no
JSON, no schema, no list, no instruction against expanding.

THE ONLY THING THAT CHANGES IS THE PROMPT. Same three models, same families,
same dispatch path, same computed ground truth. If the numbers differ from the
batched run, the difference is the scaffolding -- which is a finding about how
the question is asked, not about the models.

GROUND TRUTH, computed: "17" -> 0. "seventeen" -> 4 (s-E-v-E-n-t-E-E-n).
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) or "."
sys.path.insert(0, HERE)

# His words. Not paraphrased, not "improved".
ASKS = [
    ("17",        'Count the letter e in the exact string "17"',        0),
    ("seventeen", 'Count the letter e in the exact string "seventeen"', 4),
]


WORDS = {"zero": 0, "no": 0, "none": 0, "one": 1, "two": 2, "three": 3,
         "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
         "ten": 10}


def answer_of(text, subject):
    """The model's COUNT, not the first digit in its sentence.

    The first version took re.search(r"-?\\d+") and scored all three models
    wrong on "17": every one of them answered correctly ("contains no letter
    'e'", "no letters", "zero"), and the regex pulled the 17 out of the ECHOED
    INPUT STRING. A confident wrong number from the instrument, on the probe
    the whole experiment is about.

    So: remove the subject string wherever the model quotes it back, then read
    a number word as readily as a digit -- models answer "zero" and "two" as
    often as 0 and 2, and a digit-only reader silently drops those as
    unparseable, which is its own quiet bias."""
    t = re.sub(r"\s+", " ", text or "")
    # Drop the echoed input, quoted or bare, so its digits cannot be mistaken
    # for an answer. Longest first so "seventeen" goes before "seven".
    for pat in ('"%s"' % subject, "'%s'" % subject, "`%s`" % subject):
        t = t.replace(pat, " ")
    t = re.sub(r"(?<![\w])%s(?![\w])" % re.escape(subject), " ", t)
    m = re.search(r"(?<![\w.])(\d{1,4})(?![\w.])", t)
    if m:
        return int(m.group(1))
    for w, v in sorted(WORDS.items(), key=lambda kv: -len(kv[0])):
        if re.search(r"\b%s\b" % w, t, re.I):
            return v
    return None


def main():
    import covenant_github_judge as gh
    import covenant_teacher_panel as P
    gh.allow_credential_store("tools/count_probe_draft.py -- the operator's own "
                              "draft method, run from his own PC")
    models = P.PANEL_MODELS
    print("panel: %s" % ", ".join(models))
    print("method: the operator's draft -- two separate plain-language asks,")
    print("        no schema, no list, no instruction against expanding.\n")

    results = {}
    for label, ask, truth in ASKS:
        print("ASK: %s" % ask)
        answers = gh.ask_many(ask, models=models, timeout=900)
        for m in models:
            a = answers.get(m)
            text = a.get("content", "") if isinstance(a, dict) else str(a)
            got = first_int(text)
            # An INTERPRETATION failure on "17" means answering as if the input
            # were the WORD. Only a number equal to the expansion's count shows
            # that; anything else is a counting error on the right input.
            if got is None:
                verdict = "UNPARSEABLE"
            elif got == truth:
                verdict = "CORRECT"
            elif label == "17" and got == 4:
                verdict = "INTERPRETATION"
            else:
                verdict = "COUNTING"
            results[(m, label)] = (got, verdict)
            snippet = re.sub(r"\s+", " ", text)[:70]
            print("  %-14s said %-5s %-14s  %s"
                  % (m, got if got is not None else "?", verdict, snippet))
        print()

    print("SUMMARY (truth: 17 -> 0, seventeen -> 4)")
    print("%-14s %-16s %s" % ("model", '"17"', '"seventeen"'))
    for m in models:
        a, b = results.get((m, "17")), results.get((m, "seventeen"))
        print("%-14s %-16s %s"
              % (m, "%s %s" % (a[0], a[1]) if a else "-",
                 "%s %s" % (b[0], b[1]) if b else "-"))
    interp = sum(1 for v in results.values() if v[1] == "INTERPRETATION")
    print("\nINTERPRETATION failures under the draft's own method: %d of %d asks"
          % (interp, len(results)))
    print("Compare tools/count_probe_panel.py (batched, anti-expansion "
          "instruction, JSON schema): 0 of 24.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
