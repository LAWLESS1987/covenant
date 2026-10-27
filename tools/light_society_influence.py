#!/usr/bin/env python3
"""light_society_influence.py -- a Light Society "communication language"
experiment, resolved by table lookup instead of by model calls.

WHAT THIS REPRODUCES. Guan et al., "Modeling Earth-Scale Human-Like Societies
with One Billion Agents" (arXiv:2506.12078), Section 2.4.2, *Effect of
Communication Language*: the WVS agent profiles, the stance-pair conditions
and the prompt template are held identical while the language the agents talk
in is swapped between Chinese and French, and each combination is summarised
by its STANCE CHANGE RATE -- "the fraction of interactions in which the
influencee's final stance differs from the initial stance."

WHY A LOOKUP AND NOT A MODEL CALL PER PAIR. This is the paper's own answer to
the same cost problem, not a shortcut around it. Their billion-agent run
distils the teacher LLM into a surrogate and then, in their words, "each
interaction reduces to a single array lookup", resolved "through one vectorized
lookup on the prediction table using both agents' profile indices and current
stances". A teacher model resolved ~400,000 tuples per topic ONCE; the
simulation never called it again. The same shape here: the table is built from
the effect sizes the paper reports, and every pair is a lookup.

WHAT THIS IS, SAID PLAINLY, BECAUSE IT DECIDES WHAT THE OUTPUT IS WORTH.
This is a CALIBRATED SURROGATE, not a simulation of language models talking.
There is no teacher LLM behind it: the transition table is constructed so that
its aggregate behaviour matches the numbers printed in the paper. So it can
show how those reported effects compose across a demographic grid, and it
CANNOT discover anything the paper did not report. Any change rate it produces
that matches Section 2.4.2 is agreement by construction and is not evidence.
A real replication needs the teacher model and the WVS microdata, and neither
is on this machine.

WHAT IS CALIBRATED, AND FROM WHERE (all from the paper's own text):
  * change rate by topic and language, Section 2.4.2 --
      Earth-is-flat   Chinese 45.22%   French 47.25%
      Martian city    Chinese 22.53%   French 21.61%
      Short videos    Chinese 30.05%   French 25.34%
  * education raises BOTH persuasiveness and resistance (Fig. 3g), so it enters
    the influencer and the influencee terms with opposite sign;
  * education and income raise influence success TOGETHER, highest among
    postgraduate-and-high-income agents (Fig. 3h);
  * dissent-seeded influence "primarily induces neutralization rather than
    reverse persuasion" (Section 2.3), so a stance that moves goes to NEUTRAL
    far more often than it flips to the opposite pole.

WHAT IS NOT CALIBRATED, and is therefore this file's invention, not theirs:
country, religion and age weights. The paper reports demographic effects for
education, income and social class; it does not publish per-country or
per-religion coefficients. Those three enter as small, explicitly-listed
modifiers so that profiles differ, and they are the first thing to discount in
any reading of the output. They are named in `UNCALIBRATED` below and printed
by --provenance.

USE
  python tools/light_society_influence.py                  # compact JSON to stdout
  python tools/light_society_influence.py --out runs.json
  python tools/light_society_influence.py --rates          # change rates only
  python tools/light_society_influence.py --provenance     # what is calibrated
  python tools/light_society_influence.py --profiles 32 --topic short_videos
LICENCE: public domain.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import sys

STANCES = ("agree", "neutral", "disagree")

# Section 2.4.2, verbatim figures. change_rate[topic][language]
TOPICS = {
    "earth_flat": {"text": "The Earth is flat", "zh": 0.4522, "fr": 0.4725},
    "martian_city": {"text": "Humans will establish a Martian city within 50 years",
                     "zh": 0.2253, "fr": 0.2161},
    "short_videos": {"text": "Short-form videos are reducing human attention spans",
                     "zh": 0.3005, "fr": 0.2534},
}

# Ordered low -> high. The index is the weight; that ordering is the model.
EDUCATION = ("none", "primary", "lower_secondary", "upper_secondary",
             "post_secondary", "bachelor", "postgraduate")
INCOME = tuple(range(1, 11))          # WVS self-placed household income, 1-10
CLASS = ("lower", "working", "lower_middle", "upper_middle", "upper")
COUNTRIES = ("CN", "FR", "US", "NG", "BR", "IN", "EG", "JP")
RELIGIONS = ("none", "christian", "muslim", "hindu", "buddhist", "jewish")
AGES = (19, 27, 34, 42, 51, 63, 74)

UNCALIBRATED = ("country", "religion", "age")

# Short codes for the compact rows. `topic[:2] + topic[-2:]` produced "eaat",
# which is compact and unreadable -- a key nobody can decode without the source
# is a cost paid by every later reader to save four bytes once.
CODE = {"earth_flat": "ef", "martian_city": "mc", "short_videos": "sv"}


def _u(*parts):
    """A deterministic unit float from the parts -- the stochastic draw, made
    reproducible. Two runs of this file agree exactly; that is the point of a
    table, and it is why `--seed` changes the table rather than the sampler."""
    h = hashlib.sha256("|".join(str(p) for p in parts).encode()).digest()
    return int.from_bytes(h[:8], "big") / float(1 << 64)


def profiles(n, seed=0):
    """`n` agent profiles spread across the six attributes he named.

    Spread deliberately rather than sampled independently: an independent draw
    on six attributes leaves whole corners of the grid empty at n=24, and the
    corners are where the education-by-income effect is supposed to show.
    """
    out = []
    for i in range(n):
        out.append({
            "id": i,
            "age": AGES[i % len(AGES)],
            "country": COUNTRIES[(i * 3) % len(COUNTRIES)],
            "education": EDUCATION[(i * 5) % len(EDUCATION)],
            "income": INCOME[(i * 7) % len(INCOME)],
            "religion": RELIGIONS[(i * 2) % len(RELIGIONS)],
            "class": CLASS[(i * 4) % len(CLASS)],
        })
    return out


def _persuasiveness(p):
    """Fig. 3g/3h: education raises it, and income raises it WITH education."""
    e = EDUCATION.index(p["education"]) / (len(EDUCATION) - 1)
    inc = (p["income"] - 1) / 9.0
    cls = CLASS.index(p["class"]) / (len(CLASS) - 1)
    return 0.55 * e + 0.30 * (e * inc) + 0.15 * cls


def _resistance(p):
    """Fig. 3g: the SAME attribute that makes an agent persuasive makes them
    harder to move. One coefficient for both directions would collapse that."""
    e = EDUCATION.index(p["education"]) / (len(EDUCATION) - 1)
    inc = (p["income"] - 1) / 9.0
    age = (p["age"] - min(AGES)) / float(max(AGES) - min(AGES))
    return 0.60 * e + 0.20 * inc + 0.20 * age


def _soft(src, tgt, topic, lang):
    """The uncalibrated modifiers, kept small and kept together so they are
    easy to switch off. Homophily on country and religion; nothing here is
    from the paper."""
    s = 0.0
    if src["country"] == tgt["country"]:
        s += 0.04
    if src["religion"] == tgt["religion"]:
        s += 0.03
    if abs(src["age"] - tgt["age"]) <= 10:
        s += 0.02
    return s


_CENTRE = 0.0        # population mean of (persuasiveness - resistance); set by calibrate()
_SOFT_MEAN = 0.0     # population mean of the uncalibrated homophily term


def calibrate(ps):
    """Measure the two population means so the demographic terms are mean-zero.

    Measured over the actual profile grid in use rather than assumed, because
    the grid is what `profiles()` happens to produce and a constant written
    here would silently stop being the mean the moment n changes."""
    global _CENTRE, _SOFT_MEAN
    pairs = list(itertools.permutations(ps, 2)) or [(ps[0], ps[0])]
    _CENTRE = sum(_persuasiveness(a) - _resistance(b) for a, b in pairs) / len(pairs)
    _SOFT_MEAN = sum(_soft(a, b, None, None) for a, b in pairs) / len(pairs)
    return _CENTRE, _SOFT_MEAN


def interact(src, tgt, src_stance, tgt_stance, topic, lang, seed=0, soft=True):
    """One influence interaction. Returns the influencee's stance AFTER it.

    A lookup, in the paper's sense: no model is called, the inputs are the two
    profile indices and the two stances, and the answer is deterministic.
    """
    if src_stance == tgt_stance:
        return tgt_stance              # nothing to persuade
    base = TOPICS[topic][lang]
    # THE MODIFIER IS CENTRED, and the first draft's was not. `persuasiveness
    # - resistance` has a population mean well below zero on this grid, so
    # multiplying the paper's rate by (1 + that) dragged every topic down --
    # earth-flat came out at 0.288 against the 0.4522 this file claims to be
    # calibrated to. A surrogate whose aggregate does not reproduce the number
    # it was built from is not calibrated, it is just decorated with a
    # citation. Subtracting the mean makes the demographic term REDISTRIBUTE
    # influence across the grid, which is what Fig. 3g/3h describe, instead of
    # shifting the level, which they do not.
    p = base * (1.0 + (_persuasiveness(src) - _resistance(tgt)) - _CENTRE)
    if soft:
        p += _soft(src, tgt, topic, lang) - _SOFT_MEAN
    p = min(max(p, 0.0), 1.0)
    if _u(seed, topic, lang, src["id"], tgt["id"], src_stance, tgt_stance) >= p:
        return tgt_stance              # unmoved
    # MOVED -- but "dissent-seeded influence primarily induces neutralization
    # rather than reverse persuasion" (Section 2.3). A stance leaving a pole
    # lands on neutral far more often than on the opposite pole.
    if tgt_stance == "neutral":
        return src_stance
    flip = _u("flip", seed, topic, lang, src["id"], tgt["id"]) < 0.25
    return src_stance if flip else "neutral"


def run(n=24, seed=0, topics=None, langs=("zh", "fr"), soft=True):
    """Every ordered pair, every topic, every language. Compact rows."""
    ps = profiles(n, seed)
    calibrate(ps)
    topics = topics or list(TOPICS)
    rows, rates = [], {}
    for topic in topics:
        for lang in langs:
            changed = total = contested = 0
            for a, b in itertools.permutations(ps, 2):
                # The influencer's and influencee's starting stances are drawn
                # from the profile+topic, so a pair is one interaction, not a
                # sweep over all nine stance combinations.
                sa = STANCES[int(_u("s", seed, topic, a["id"]) * 3)]
                sb = STANCES[int(_u("s", seed, topic, b["id"]) * 3)]
                nb = interact(a, b, sa, sb, topic, lang, seed, soft)
                rows.append({"t": CODE[topic], "l": lang,
                             "i": a["id"], "j": b["id"], "b": nb[0]})
                total += 1
                contested += (sa != sb)
                changed += (nb != sb)
            # TWO DENOMINATORS, BOTH NAMED, because they answer different
            # questions and quoting one as the other is this project's most
            # repeated error. `contested` counts only the pairs that disagreed
            # to begin with -- the paper's "stance-pair conditions", and the
            # population its 45.22% is over. `all` divides by every pair,
            # including the third or so who already agreed and therefore
            # cannot change. Calibration targets `contested`.
            rates.setdefault(topic, {})[lang] = {
                "contested": round(changed / contested, 4) if contested else None,
                "all": round(changed / total, 4),
                "n_contested": contested, "n_all": total,
                "paper": TOPICS[topic][lang]}
    return ps, rows, rates


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--profiles", type=int, default=24)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--topic", action="append", choices=sorted(TOPICS))
    ap.add_argument("--out")
    ap.add_argument("--rates", action="store_true", help="change rates only")
    ap.add_argument("--provenance", action="store_true",
                    help="what is calibrated from the paper and what is not")
    ap.add_argument("--no-soft", action="store_true",
                    help="switch off the uncalibrated country/religion/age terms")
    a = ap.parse_args(argv)

    if a.provenance:
        print(json.dumps({
            "paper": "arXiv:2506.12078, Guan et al., Section 2.4.2",
            "what_this_is": "a calibrated surrogate, not a replication: no teacher "
                            "LLM is called, so agreement with the paper's change "
                            "rates is by construction and is not evidence",
            "calibrated_from_the_paper": {
                "change_rate_by_topic_and_language": {k: {"zh": v["zh"], "fr": v["fr"]}
                                                      for k, v in TOPICS.items()},
                "education_raises_persuasion_and_resistance": "Fig. 3g",
                "education_x_income_raises_success": "Fig. 3h",
                "movement_neutralises_rather_than_flips": "Section 2.3"},
            "NOT_calibrated_invented_here": list(UNCALIBRATED),
            "disable_those_with": "--no-soft"}, separators=(",", ":")))
        return 0

    ps, rows, rates = run(a.profiles, a.seed, a.topic, soft=not a.no_soft)
    if a.rates:
        print(json.dumps(rates, separators=(",", ":")))
        return 0
    doc = {"n": len(ps), "profiles": ps, "rates": rates, "runs": rows}
    blob = json.dumps(doc, separators=(",", ":"))
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(blob)
        print(json.dumps({"wrote": a.out, "bytes": len(blob),
                          "interactions": len(rows), "rates": rates},
                         separators=(",", ":")))
    else:
        print(blob)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
