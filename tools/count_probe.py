#!/usr/bin/env python3
"""A falsifiable battery separating COUNTING failure from INTERPRETATION failure.

THE OPERATOR'S OBSERVATION, 2026-09-17: asking how many e's are in "17" gets an
answer about the word "seventeen". As written, "17" contains zero. He noted the
two failures are different and must be told apart, and he is right -- they have
different causes, so evidence that separates them also narrows the question of
whether either is deliberate.

    INTERPRETATION failure: the model silently substitutes a different input
      (the numeral's NAME for the numeral) and answers correctly about the thing
      it substituted. Diagnostic: the answer equals the count for the expansion.

    COUNTING failure: the model answers about the right string and gets the
      number wrong. Diagnostic: the answer equals neither the true count nor the
      expansion's count.

These are distinguishable because the two correct answers differ. That is the
whole design: every probe is a string where "counted the input" and "counted
what the input names" give DIFFERENT numbers, so a single response falls into
exactly one bucket.

GROUND TRUTH IS COMPUTED, NEVER ASKED. Note that "seventeen" has FOUR e's, not
three (s-E-v-E-n-t-E-E-n). The author of this file would have said three from
reading it. If the answer key came from a model -- or from a person reading
quickly -- the experiment would measure nothing.

WHY NOT JUST ASK A MODEL WHY IT DOES THIS. Because this repository already
documented the confound: docs/CASE_STUDY_SELF_REPORT.md found that models with
partial access to an artifact complete the gap and report the completed version
as fact. A model asked to explain its own miscount will produce a fluent causal
story that is generated, not retrieved. Cause has to be established
behaviourally, from responses to controlled inputs. That is what this is.
"""
import json
import re
import sys

# (label, exact string, expansion-or-None, note)
# The expansion is what a model would be counting if it reinterpreted.
PROBES = [
    ("numeral",        "17",        "seventeen", "0 vs 4 -- the operator's case"),
    ("word",           "seventeen", None,        "control: no reinterpretation possible"),
    ("numeral-2",      "3",         "three",     "0 vs 2"),
    ("word-2",         "three",     None,        "control"),
    ("numeral-3",      "11",        "eleven",    "0 vs 3"),
    ("case-trap",      "ELEVEN",    None,        "0 lowercase e, 3 if case-folded"),
    ("both-present",   "17e",       "seventeene","1 vs 5 -- rules out 'always says zero'"),
    ("mixed",          "17 (seventeen)", None,   "4 -- the numeral is written out FOR them"),
]

LETTER = "e"


def truth(s, letter=LETTER, fold=False):
    return len(re.findall(re.escape(letter), s.lower() if fold else s))


def prompt_for(s):
    """Deliberately unambiguous. If a model still reinterprets after this, the
    reinterpretation is not caused by ambiguity in the request."""
    return ("Count the occurrences of the lowercase letter 'e' in the exact "
            "string between the markers. Do not expand, translate, or rename "
            "the string. Count characters literally.\n"
            "<<<%s>>>\n"
            "Reply with a single integer and nothing else." % s)


def classify(answer, s, expansion):
    """Which failure is it? Returns (verdict, explanation)."""
    m = re.search(r"-?\d+", str(answer or ""))
    if not m:
        return "UNPARSEABLE", "no integer in the response"
    got = int(m.group(0))
    exact = truth(s)
    folded = truth(s, fold=True)
    exp = truth(expansion) if expansion else None
    if got == exact:
        return "CORRECT", "counted the input as written (%d)" % exact
    if exp is not None and got == exp:
        return "INTERPRETATION", ("answered about %r (%d), not the input %r (%d)"
                                  % (expansion, exp, s, exact))
    if got == folded and folded != exact:
        return "CASE-FOLD", ("case-insensitive count (%d); the request said "
                             "lowercase (%d)" % (folded, exact))
    return "COUNTING", ("said %d; the input has %d%s -- matches neither"
                        % (got, exact,
                           " and the expansion has %d" % exp if exp is not None else ""))


def battery():
    out = []
    for label, s, expansion, note in PROBES:
        out.append({
            "label": label, "string": s, "expansion": expansion, "note": note,
            "prompt": prompt_for(s),
            "true_count": truth(s),
            "expansion_count": truth(expansion) if expansion else None,
            "case_folded_count": truth(s, fold=True),
        })
    return out


def main():
    if "--json" in sys.argv:
        print(json.dumps(battery(), indent=2))
        return 0
    if "--score" in sys.argv:
        # tools/count_probe.py --score '{"numeral": "3", "word": "4"}'
        try:
            answers = json.loads(sys.argv[sys.argv.index("--score") + 1])
        except (IndexError, ValueError):
            print("--score needs a JSON object of {label: answer}")
            return 1
        tally = {}
        for label, s, expansion, _n in PROBES:
            if label not in answers:
                continue
            v, why = classify(answers[label], s, expansion)
            tally[v] = tally.get(v, 0) + 1
            print("  %-13s %-18s -> %-15s %s" % (label, repr(s), v, why))
        print("\n  " + "  ".join("%s=%d" % kv for kv in sorted(tally.items())))
        return 0

    print("COUNTING vs INTERPRETATION -- battery with computed ground truth")
    print("=" * 74)
    print("%-13s %-18s %6s %10s %6s  %s"
          % ("label", "exact string", "true", "expansion", "fold", "note"))
    for b in battery():
        print("%-13s %-18s %6d %10s %6d  %s"
              % (b["label"], repr(b["string"]), b["true_count"],
                 b["expansion_count"] if b["expansion_count"] is not None else "-",
                 b["case_folded_count"], b["note"]))
    print("""
HOW TO READ A RESULT
  answer == true            CORRECT
  answer == expansion       INTERPRETATION -- it answered about a different input
  answer == case-folded     CASE-FOLD      -- ignored an explicit constraint
  anything else             COUNTING       -- wrong about the right string

WHAT WOULD DISTINGUISH DELIBERATE FROM EMERGENT
  A design choice predicts CONSISTENCY: reinterpretation should persist even
  when the prompt forbids it, and should be stable across runs.
  A capability limit predicts VARIANCE: the same model gives different numbers
  on re-asks, and does better on short strings than long ones.
  Neither is established by asking a model to explain itself.

  Run each probe N times. Stable-and-wrong points one way; unstable-and-wrong
  points the other. That is the measurement the argument needs.

  tools/count_probe.py --json    machine-readable battery
  tools/count_probe.py --score '{"numeral":"4"}'   classify collected answers""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
