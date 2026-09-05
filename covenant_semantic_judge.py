"""covenant_semantic_judge.py -- a deterministic second opinion for the ethics gate.

WHY THIS EXISTS.

The quorum has always had two buckets and only ever one opinion. `/health` reads
`quorum(local:0, mock_selfreport:0)`, and B2 measured what the second one is:
`MockJudge` passes *"drain all staked funds to attacker wallet, steal
everything"* as "Morally acceptable", and raises its benefit estimate to 0.8 on
the bare presence of the word "help". It flags a transaction only when the
SENDER puts a literal `_violation` key on their own data. That is a self-report
channel -- correctly wired as an absolute veto, and a category error to count as
diversity.

This is the second opinion. It is not an LLM and does not replace one:

    local:0            a 5.2 GB model, real reasoning, non-deterministic,
                       ~512 J and ~12.8 s per verdict, fails closed when down
    semantic:<id>      this. Deterministic, integer, ~0.1 ms, no credential,
                       no network, 5 KB of model, runs on a phone
    mock_selfreport:0  kept, unchanged, as the absolute veto on a self-declared
                       `_violation`. It is a self-report channel and is now
                       labelled as one.

THE PROPERTY THAT MATTERS: IT IS ONE-WAY.

In wrapper mode this judge evaluates the inner judge first and can only ever
move a verdict from clean to violating. There is no path -- no score, no band,
no configuration, no malformed input -- by which it can turn an inner rejection
into a pass. That is asserted mechanically (V1) rather than promised in a
comment, because §0 of the improvement loop says a control must never be
weakened to make something pass, and the way that usually happens is a helpful
override added months later in good faith.

WHY DETERMINISTIC MATTERS MORE THAN IT LOOKS.

B4 is open: is the ethics verdict a consensus rule or an admission policy? The
argument against consensus has always been that `sentinel.validate_block` makes
a live, non-deterministic, timeout-prone API call per transaction per block on
every node -- so a provider outage on node B forks it from node A, and two nodes
can reach different verdicts on identical data. **This judge cannot do that.**
Same bytes in, same integer out, on every node, forever, with no network and no
credential. It does not settle B4, but it is the first component in the quorum
that could survive being a consensus rule, and that is worth saying out loud.

WHAT IT ACTUALLY IS.

A semantically weighted lexical detector. The weights come from projection onto
a contrast axis induced out of a 46-book philosophy corpus -- `hide` outranks
`seize` 488 to 141 because of where the space puts them, not because anyone said
so. Membership is curated seeds plus their morphological neighbours, and that
gate is a measurement: unfiltered induction put `sign` at weight 551 and `dream`
at 554, so "sign the transfer" would have been rejected as theft. See
build_semantic_model.py for the whole derivation and for the two principles that
were built, measured, and deliberately NOT shipped.

It reads a JSON model and nothing else. No numpy, no scipy, no corpus, no
network -- stdlib only, so it imports under Termux where scipy does not build.

STANDALONE USE
    from covenant_semantic_judge import SemanticModel
    m = SemanticModel.load("semantic_judge_model.json")
    m.assess({"memo": "hide the payment"})     -> Assessment(...)

IN THE NODE (see the v8.38 patch)
    import covenant_semantic_judge as csj
    csj.install(ReasoningJudge, JudgmentResult, JudgeProviderRegistry)
    # then COVENANT_JUDGE_PROVIDERS=local,semantic
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

__all__ = ["SemanticModel", "Assessment", "SemanticJudgeError", "install",
           "DEFAULT_MODEL_PATH", "CLEAN", "ABSTAIN", "VIOLATES"]

DEFAULT_MODEL_PATH = os.environ.get(
    "COVENANT_SEMANTIC_MODEL",
    os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 "semantic_judge_model.json"))

# Same tokenizer as sem_core, so the words the model was built on are the words
# it looks for. Copied rather than imported: sem_core needs numpy.
_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)

CLEAN, ABSTAIN, VIOLATES = "clean", "abstain", "violates"
ILLEGIBLE = "illegible"

# THE LATTICE. Every pass in assess() may only ever move a verdict UP this
# order, never down. That is the one structural property the whole extension
# rests on: no amount of anything added to a payload -- more text, another
# field, a second language, a repair pass -- can make its verdict weaker than
# it already was. It is the same claim X2 makes about score() (adding words can
# only raise it), lifted from the number to the verdict.
_RANK = {CLEAN: 0, ILLEGIBLE: 1, ABSTAIN: 2, VIOLATES: 3}


def _worse(a, b):
    return a if _RANK[a] >= _RANK[b] else b

# Bound the work an untrusted payload can cause. A transaction is a memo, not a
# document; anything past this is not more information, it is a cost.
MAX_FEATURE_TOKENS = 4096
MAX_DEPTH = 8


class SemanticJudgeError(Exception):
    pass


class Assessment(object):
    """What the model says on its own, before any quorum arithmetic."""

    __slots__ = ("verdict", "score", "principle", "evidence", "model_id",
                 "unobservable", "coverage", "script_gaps", "evasion",
                 "seeded_hits", "competence", "hold_id", "fitted_script",
                 "register_hits")

    def __init__(self, verdict, score, principle, evidence, model_id,
                 unobservable, coverage=None, script_gaps=None, evasion=False,
                 seeded_hits=None, competence="full", hold_id=None,
                 fitted_script="", register_hits=None):
        self.register_hits = list(register_hits or [])
        self.hold_id = hold_id
        self.fitted_script = fitted_script
        self.coverage = coverage
        self.script_gaps = dict(script_gaps or {})
        self.evasion = bool(evasion)
        self.seeded_hits = list(seeded_hits or [])
        self.competence = competence
        self.verdict = verdict
        self.score = score
        self.principle = principle
        self.evidence = evidence          # [(weight, word), ...] highest first
        self.model_id = model_id
        self.unobservable = unobservable

    @property
    def blocks(self) -> bool:
        """ABSTAIN and ILLEGIBLE block. A judge that cannot tell is not a judge that
        approves -- the whole gate is fail-closed and this is no exception."""
        return self.verdict in (ABSTAIN, ILLEGIBLE, VIOLATES)

    def reasoning(self) -> str:
        ev = ", ".join(f"{w}({v})" for v, w in self.evidence) or "no signal"
        if self.verdict == VIOLATES:
            return (f"semantic[{self.model_id}] VIOLATES score={self.score} "
                    f">= veto; {self.principle}; evidence: {ev}")
        if self.verdict == ABSTAIN:
            # It said `evidence: no signal` for a payload that matched six
            # register markers, because this branch only ever reported the
            # induced score. An operator reading that is being told the
            # opposite of what happened. Every reason the verdict is ABSTAIN
            # is named here, in the order it was found.
            why = []
            if self.score:
                why.append(f"lexicon score {self.score} in the gate band "
                           f"[{self.principle}]: {ev}")
            if self.seeded_hits:
                why.append("seeded terms in an unreviewed language: "
                           + ", ".join(t for _w, t in self.seeded_hits))
            if self.register_hits:
                why.append(
                    f"{len(self.register_hits)} markers of the register in "
                    f"which crime is usually discussed -- "
                    + ", ".join(f"{p} [{c}]" for p, c in self.register_hits[:6])
                    + ". THESE ARE ORDINARY WORDS. Two or more together is why "
                      "this stopped; it is not a finding that anything is "
                      "wrong, and this model cannot make one")
            return (f"semantic[{self.model_id}] ABSTAIN -- it blocks rather "
                    f"than approves, and it is NOT alleging a violation. "
                    + " | ".join(why or ["no signal"]))
        if self.verdict == ILLEGIBLE:
            # THE MOST IMPORTANT STRING IN THIS FILE.
            #
            # A person whose transaction stopped is owed the truth about why,
            # and the truth is not that they did anything. This model reads one
            # script. It could not read theirs. It has therefore made NO
            # finding about their transaction at all -- and a refusal that
            # reads like an accusation, to someone who cannot read the language
            # the accusation is written in, is the exact harm this verdict was
            # added to stop repeating.
            #
            # So it says: not judged. Not refused for cause. Held, with a
            # reference they can quote and a person who owes them an answer.
            where = ", ".join(f"{k} x{v}" for k, v in
                              sorted(self.script_gaps.items(),
                                     key=lambda kv: -kv[1])) or "an unfitted script"
            return (f"semantic[{self.model_id}] HELD, NOT JUDGED. This model "
                    f"was fitted on {self.fitted_script or 'one script'} and "
                    f"cannot read {where}. It has made NO finding about this "
                    f"transaction and is NOT alleging anything: it is "
                    f"declining to certify what it did not read. "
                    f"Reference {self.hold_id or 'unassigned'} -- quote it to "
                    f"anyone who can read {where.split(' x')[0]}: another node, "
                    f"another judge, or a person. Whoever clears it is recorded "
                    f"along with what they demonstrated they could read. "
                    f"The model observes {self.observes()} in "
                    f"{self.fitted_script or '?'} only.")
        return (f"semantic[{self.model_id}] defers: score={self.score} below "
                f"the gate. This model observes {self.observes()} and nothing "
                f"else; it is not evidence of alignment.")

    def observes(self) -> str:
        return "appropriation and concealment"


def _canonical_tokens(data: Any, transform=None) -> List[str]:
    """Transaction -> a deterministic token list.

    Three properties are asserted by the suite and each is a hole if it is
    missing:
      X3  field ORDER cannot change the verdict     -> keys are sorted
      X1  `_`-prefixed sender fields are ignored    -> a sender must not be able
          to smuggle text past the judge, nor to influence it, by naming a key
          with a leading underscore. `_violation` is the SELF-REPORT channel and
          belongs to MockJudge; it is not this judge's input.
      D2  PYTHONHASHSEED cannot change the verdict  -> nothing iterates a set or
          an unsorted dict anywhere on this path.
    """
    out: List[str] = []

    def walk(node, depth):
        if depth > MAX_DEPTH or len(out) >= MAX_FEATURE_TOKENS:
            return
        if isinstance(node, dict):
            for k in sorted(node.keys(), key=lambda x: str(x)):
                ks = str(k)
                if ks.startswith("_"):
                    continue
                walk(ks, depth + 1)  # keys are sender-controlled too
                walk(node[k], depth + 1)
        elif isinstance(node, (list, tuple)):
            for v in node:
                walk(v, depth + 1)
        elif isinstance(node, (str, int, float, bool)) or node is None:
            raw = str(node)
            if transform is not None:
                raw = transform(raw)
            text = unicodedata.normalize("NFC", raw.lower())
            for t in _WORD.findall(text):
                out.append(t)
                if len(out) >= MAX_FEATURE_TOKENS:
                    return

    walk(data, 0)
    return out[:MAX_FEATURE_TOKENS]



# ===========================================================================
# COMPETENCE -- what this model can and cannot read.
#
# The full derivation, including the two ratio tests that were BUILT AND
# REJECTED against real data, is in competence.py's docstring. The short form:
#
#   vocabulary coverage   legitimate English bottoms out at 25% ("hardware
#                         wallet replacement after the firmware bug"), which is
#                         exactly Spanish's 25%. No separation. Does not gate.
#   function-word rate    7 of 20 legitimate English memos score 0% ("netflix",
#                         "physio session"). No separation. Does not gate.
#
# Transaction memos are too short and too modern for either. What survives is
# the SCRIPT test, which is presence-based and cannot be diluted by padding,
# and REPAIR, which is one-way by construction.
# ===========================================================================
_SCRIPT_CACHE: Dict[str, str] = {}


def _char_script(ch: str) -> str:
    hit = _SCRIPT_CACHE.get(ch)
    if hit is not None:
        return hit
    try:
        name = unicodedata.name(ch)
    except ValueError:
        name = ""
    if not name:
        out = "Unknown"
    else:
        first = name.split()[0]
        out = {"CJK": "Han", "HANGUL": "Hangul", "HIRAGANA": "Kana",
               "KATAKANA": "Kana", "FULLWIDTH": "Latin"}.get(first,
                                                             first.capitalize())
    _SCRIPT_CACHE[ch] = out
    return out


def _token_script(tok: str) -> str:
    """A token's script, or 'Mixed' when its letters disagree -- which is
    itself the homoglyph shape (`pаypal` with a Cyrillic а) that repair() is
    for, so it is reported rather than averaged away."""
    seen = {_char_script(c) for c in tok if c.isalpha()}
    if not seen:
        return "Unknown"
    if len(seen) == 1:
        return seen.pop()
    return "Mixed"


# Characters per word, by script. Not a ratio anyone should trust to two
# decimal places -- it exists to answer one question: is this much foreign text
# a NAME or a SENTENCE? A logographic script answers that at two characters and
# an alphabetic one at five, so a single character threshold gets one of them
# wrong whichever value it takes. Measured against the cases that matter:
#
#   王明             Han 2  = 1.0 words   a name          passes
#   Иван             Cyrl 4 = 0.8 words   a name          passes
#   資金を盗む        Han 3 + Kana 2 = 2.5 an instruction  blocks
#   украсть все      Cyrl 10 = 2.0 words  an instruction  blocks
#   सारे पैसे चुराओ  Deva 7 = 2.3 words   an instruction  blocks
#
# A long foreign name (Александр Петрович) trips it, and that is the honest
# result rather than a miss: a model that cannot read Cyrillic cannot tell a
# name from a sentence, and saying so is the whole point of ILLEGIBLE.
# Grouped by WRITING SYSTEM TYPE, because that is what actually sets the ratio
# and guessing per-script invites exactly the miss that produced this table's
# third revision: Hindi `सारे पैसे चुराओ` came back CLEAN at 7 characters
# because Devanagari had been left on the alphabetic default. It is an abugida
# -- every character carries a consonant AND a vowel -- so it packs a word into
# far fewer characters than Latin does.
_CHARS_PER_WORD = {
    # logographic and syllabic: one character is most of a morpheme
    "Han": 2, "Kana": 2, "Hangul": 2, "Yi": 2,
    # abugidas: a consonant plus its vowel in one character
    "Devanagari": 3, "Bengali": 3, "Gurmukhi": 3, "Gujarati": 3, "Oriya": 3,
    "Tamil": 3, "Telugu": 3, "Kannada": 3, "Malayalam": 3, "Sinhala": 3,
    "Thai": 3, "Lao": 3, "Khmer": 3, "Myanmar": 3, "Tibetan": 3,
    "Ethiopic": 3, "Cherokee": 3,
    # abjads: the vowels are not written at all
    "Arabic": 4, "Hebrew": 4, "Syriac": 4, "Thaana": 4,
}
_DEFAULT_CHARS_PER_WORD = 5     # alphabetic: Latin, Cyrillic, Greek, Armenian,
                                # Georgian, and anything unlisted
_FOREIGN_WORD_TRIGGER = 20        # tenths of a word: 2.0


def _foreign_words_x10(gaps: Dict[str, int]) -> int:
    """Out-of-script characters converted to tenths of a word, summed."""
    total = 0
    for sc, n in gaps.items():
        per = _CHARS_PER_WORD.get(sc, _DEFAULT_CHARS_PER_WORD)
        total += n * 10 // per
    return total


def _script_gaps(tokens, fitted: str) -> Dict[str, int]:
    """Out-of-script CHARACTERS, counted by script.

    Characters, not tokens, and the difference is a bug this suite's own
    gap-reporting section caught after the check had been declared green. The
    threshold was written as `min_foreign_tokens = 2`, reasoned as *one foreign
    token is a name, two is a sentence* -- which is true of every script that
    puts spaces between words and false of the ones that do not. `窃取所有资金`
    is a complete instruction and exactly ONE token, so it fell under the
    threshold and returned CLEAN, while the same sentence with a comma in it
    became two tokens and blocked correctly.

    Counting characters restores the intent for every script at once: a name is
    short in any of them, a sentence is not."""
    out: Dict[str, int] = {}
    for t in tokens:
        for ch in t:
            if not ch.isalpha():
                continue
            sc = _char_script(ch)
            if sc == "Unknown" or sc == fitted:
                continue
            out[sc] = out.get(sc, 0) + 1
    return out


# Only pairs that are visually confusable in an ordinary font. Every entry can
# only turn a NON-matching token into a matching one, so the whole effect of
# this table is to raise scores. That is why it may grow freely and why it is
# code rather than a hashed model artefact: there is no edit to it that makes
# the judge more permissive.
_CONFUSABLE = {
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y", "х": "x",
    "і": "i", "ј": "j", "һ": "h", "ο": "o", "α": "a", "ε": "e", "ρ": "p",
    "υ": "u", "А": "A", "Е": "E", "О": "O", "Р": "P", "С": "C", "Х": "X",
    "Β": "B", "Ο": "O", "Η": "H",
}
_LEET = {"0": "o", "1": "l", "3": "e", "4": "a", "5": "s", "7": "t",
         "@": "a", "$": "s", "!": "i", "|": "l"}
# A digit becomes a letter only INSIDE a word. `st3al` is an evasion; `4417` is
# an invoice number, and folding it to `aail` would invent tokens the sender
# never wrote -- which would be this pass inventing evidence rather than
# recovering it.
_INWORD = re.compile(r"(?<=[^\W\d_])([0-9@$!|])(?=[^\W\d_])|"
                     r"(?<=[^\W\d_])([0-9@$!|])$|"
                     r"^([0-9@$!|])(?=[^\W\d_])")


_HEXTOKEN = re.compile(r"^[0-9a-fA-F]{16,}$")


def _repair(text: str) -> str:
    """Undo the cheap ways of hiding a word from a lexicon: width and ligature
    variants (NFKC), the zero-width and directional characters that split a
    word invisibly (category Cf), Cyrillic and Greek look-alikes, and in-word
    digits standing in for letters."""
    t = unicodedata.normalize("NFKC", text)
    t = "".join(c for c in t if unicodedata.category(c) != "Cf")
    t = "".join(_CONFUSABLE.get(c, c) for c in t)
    # .get(ch, ch), NOT [ch]. Found 2026-09-05 by a readiness audit on a fresh
    # clone: _INWORD matches EVERY digit between letters, _LEET maps six of
    # them, and a hex hash -- the owner's block-2 `root`,
    # ec9020572f74b7e83f9a9e9c536557e351f5fe720c3d4576123af8ec43d70d22 --
    # raised KeyError: '9', which the wrapper turned into violates=True and the
    # strict quorum into a veto. Every fresh node stopped at height 2. A digit
    # with no leet reading is a digit, and stays one.
    # And a token that is all hex and sixteen-plus characters is a HASH, not a
    # word hiding from a lexicon. Left alone entirely: with .get() alone the
    # block-2 root still had its 0s, 5s and 7s decoded into letters, and a
    # 64-character hex string has enough short runs in it to spell a lexicon
    # hit by accident one day. Nothing in a hash was written by a sender.
    return " ".join(
        tok if _HEXTOKEN.match(tok) else
        _INWORD.sub(lambda m: _LEET.get(m.group(1) or m.group(2) or m.group(3),
                                        m.group(1) or m.group(2) or m.group(3)), tok)
        for tok in t.split(" "))


def _leaf_strings(data: Any, transform=None) -> List[str]:
    """Every leaf string in the payload, separately.

    Phrases are matched WITHIN a leaf and never across two, because a phrase
    spanning two fields is not a phrase -- it is an accident of how the payload
    happened to be walked, and a marker assembled from two unrelated fields is
    evidence of nothing."""
    out: List[str] = []

    def walk(node, depth):
        if depth > MAX_DEPTH or len(out) >= MAX_FEATURE_TOKENS:
            return
        if isinstance(node, dict):
            for k in sorted(node.keys(), key=lambda x: str(x)):
                if str(k).startswith("_"):
                    continue
                walk(node[k], depth + 1)
        elif isinstance(node, (list, tuple)):
            for v in node:
                walk(v, depth + 1)
        elif isinstance(node, (str, int, float, bool)) or node is None:
            raw = str(node)
            if transform is not None:
                raw = transform(raw)
            out.append(unicodedata.normalize("NFC", raw.lower()))

    walk(data, 0)
    return out


_NONWORD = re.compile(r"[^\w'\- ]+", re.UNICODE)
_SPACES = re.compile(r"\s+")


def _register_markers(data: Any, lexicon: Dict[str, str]) -> List[tuple]:
    """Distinct register markers present, as (phrase, category).

    Distinct: the same phrase twice is one marker. Saying `wash` three times is
    saying it once -- repetition is emphasis, not corroboration, and the whole
    rule rests on several DIFFERENT markers of the register appearing together.
    """
    if not lexicon:
        return []
    found: Dict[str, str] = {}
    for leaf in _leaf_strings(data) + _leaf_strings(data, _repair):
        t = " " + _SPACES.sub(" ", _NONWORD.sub(" ", leaf)) + " "
        for phrase, cat in lexicon.items():
            if phrase not in found and f" {phrase} " in t:
                found[phrase] = cat
    return sorted(found.items())


def _repaired_tokens(data: Any) -> List[str]:
    """_canonical_tokens over a repaired view of the same payload."""
    return _canonical_tokens(data, transform=_repair)


def _windows(tokens, size):
    if len(tokens) <= size:
        yield tokens
        return
    for i in range(len(tokens) - size + 1):
        yield tokens[i:i + size]


def _coverage(tokens, vocab, window: int):
    """Percent of the WORST window the fitted vocabulary knows. Minimum, not
    mean: a mean is a lever, because padding a foreign payload with English
    raises an average until it passes, and a minimum over windows cannot be
    raised by addition. REPORTED ONLY -- see the header."""
    if not tokens or not vocab:
        return None
    worst = 100
    for w in _windows(list(tokens), window):
        hit = 0
        for t in w:
            if t in vocab:
                hit += 1
        pct = hit * 100 // len(w)
        if pct < worst:
            worst = pct
    return worst


class SemanticModel(object):
    """The model file, loaded, verified, and frozen."""

    def __init__(self, raw: Dict[str, Any], model_id: str):
        self.raw = raw
        self.model_id = model_id
        self.gate_lo = int(raw["gate_lo"])
        self.veto_at = int(raw["veto_at"])
        self.top_k = int(raw["top_k"])
        self.principles = {p: {w: int(v) for w, v in d.items()}
                           for p, d in raw["principles"].items()}
        self.not_observable = dict(raw.get("not_observable", {}))
        self.space_sig = raw.get("space_sig", "?")
        # ---- the competence declaration (v2). Absent = a v1 model, and the
        # extension simply does not engage, so an old model still loads.
        self.vocab = frozenset(raw.get("vocab", ()))
        self.space_script = raw.get("space_script", "")
        self.coverage_window = int(raw.get("coverage_window", 8))
        # Two words of out-of-script text, in tenths. A first draft counted
        # TOKENS and `窃取所有资金` -- a whole instruction and one token,
        # because Chinese has no spaces -- came back CLEAN. A second counted
        # CHARACTERS and `資金を盗む` came back CLEAN at five. Words is the
        # unit the question was always about.
        self.foreign_word_trigger = int(raw.get("foreign_word_trigger", 20))
        self.seeded = {p: {w: int(v) for w, v in d.items()}
                       for p, d in raw.get("seeded_lexicon", {}).items()}
        # PER-LANGUAGE VERIFICATION WITH ATTRIBUTION, not one boolean for 35
        # languages.
        #
        # The first version was a single flag covering the whole seeded
        # lexicon, which asserts that Spanish and Amharic are in the same
        # epistemic state because they arrived in the same file. They are not.
        # Fei-Fei Li's argument about ImageNet is the relevant one: the dataset
        # is where competence and bias actually live, and a label is only worth
        # the provenance and the agreement behind it. ImageNet did not ship one
        # "verified" bit over fifteen million images; it shipped many
        # annotators per item and an agreement threshold, and it was the LABELS
        # -- the person subtree in particular -- that later had to be answered
        # for, not the architecture.
        #
        # So verification is a record per language: who checked it, how many
        # agreed, when. `min_reviewers` is the bar a language must clear before
        # its stems may assert a violation rather than merely abstain.
        # the register lexicon -- how crime is SPOKEN. Fires only on two or
        # more distinct markers, and caps at ABSTAIN. See lexicon_register.py
        # for the measurement that set both numbers.
        self.register = dict(raw.get("register_lexicon", {}))
        self.register_min = int(raw.get("register_min_markers", 2))
        self.verified_languages = dict(raw.get("verified_languages", {}))
        self.min_reviewers = int(raw.get("min_reviewers", 2))
        # kept so a v2.0 model file still loads and behaves
        self.seeded_verified = bool(raw.get("seeded_verified", False))
        # the gap ledger. Counts and coverage only -- never payload text. What
        # a payload SAYS is the sender's; that it was unreadable is the
        # system's, and only the second is needed to decide what to fit next.
        self.gaps: Dict[str, int] = {}
        self.gap_total = 0
        # THE REVIEW QUEUE. A hold that nobody owns is not a safeguard, it is a
        # pile -- and a pile with no bound and no reader grows until it is
        # somebody's rent. So every hold is dated, numbered, and counted
        # against a STATED bound, exactly as the watchdog states its own 60s
        # and P16 makes a longer gap mean death rather than calm.
        #
        # The bound is not a timeout that clears anything. Nothing here expires
        # a hold; only a person can. The bound exists so that the moment it is
        # breached the system says so, in the operator's face, with a number.
        self.holds: List[Dict[str, Any]] = []
        self.cleared: List[Dict[str, Any]] = []
        self.hold_seq = 0
        self.review_bound_s = int(raw.get("review_bound_s", 86400))
        self.holds_cap = int(raw.get("holds_cap", 5000))
        # ---- WHICH PASSES CANNOT RUN ON THIS FILE, NAMED (SEM4).
        #
        # Being less capable is survivable -- it is what the v1-compat path
        # above exists for. Reporting full competence while less capable is
        # not: `full` is a value a model with no fitted script cannot compute,
        # published as a measurement (M50). So the flag is DERIVED from the
        # very attributes passes 3/4/5 guard on -- never asserted separately,
        # and never from the file's own say-so. A pass added later with a new
        # guard must be added here, or SEM4's D8b fails loudly.
        self.inert_passes = tuple(
            (n, guard, why)
            for n, guard, present, why in (
                (3, "seeded_lexicon", bool(self.seeded),
                 "no seeded lexicon: pass 3 never scores, so a prohibited "
                 "instruction in any unseeded language cannot even ABSTAIN"),
                (4, "space_script", bool(self.space_script),
                 "no fitted script: pass 4 cannot tell foreign text from "
                 "fitted text, so CLEAN is a claim this model has no "
                 "standing to make on any payload"),
                (5, "vocab", bool(self.vocab),
                 "no vocabulary: pass 5 cannot measure coverage, so nothing "
                 "distinguishes a payload that was read from one that was "
                 "not"),
            ) if not present)
        if self.gate_lo <= 0 or self.veto_at <= self.gate_lo:
            raise SemanticJudgeError(
                f"incoherent bands: gate_lo={self.gate_lo} veto_at={self.veto_at}")
        for p, d in self.principles.items():
            for w, v in d.items():
                if not isinstance(v, int) or isinstance(v, bool) or v <= 0:
                    raise SemanticJudgeError(
                        f"weight for {w!r} in {p!r} is not a positive int: {v!r}")

    def language_verified(self, lang: str) -> bool:
        """Has enough independent review accumulated for this ONE language."""
        rec = self.verified_languages.get(lang) or {}
        who = rec.get("reviewers") or []
        return len(who) >= self.min_reviewers

    def verification_report(self) -> Dict[str, Any]:
        """What is reviewed, what is not, and by whom. Published because an
        unreviewed lexicon that does not say so is indistinguishable from a
        reviewed one, and the difference is somebody's transaction."""
        seeded = sorted(self.raw.get("seeded_languages", []))
        done = [l for l in seeded if self.language_verified(l)]
        return {
            "min_reviewers": self.min_reviewers,
            "verified": {l: self.verified_languages[l] for l in done},
            "unverified": [l for l in seeded if l not in done],
            "verified_count": len(done),
            "total": len(seeded),
            "note": "an unverified language may block (ABSTAIN) and may never "
                    "assert a violation. Review is per language and carries "
                    "who did it -- one boolean over 35 languages asserts that "
                    "they are all in the same epistemic state, and they are "
                    "not.",
        }

    # -------------------------------------------------------------- identity
    @staticmethod
    def _identity(raw: Dict[str, Any]) -> str:
        body = dict(raw)
        body.pop("model_id", None)
        return hashlib.sha256(
            json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()[:12]

    @classmethod
    def load(cls, path: Optional[str] = None) -> "SemanticModel":
        path = path or DEFAULT_MODEL_PATH
        if not os.path.exists(path):
            raise SemanticJudgeError(f"no semantic model at {path}")
        with open(path, encoding="utf-8") as fh:
            raw = json.load(fh)
        claimed = raw.get("model_id")
        actual = cls._identity(raw)
        if claimed != actual:
            raise SemanticJudgeError(
                f"model at {path} is TAMPERED or corrupt: it claims "
                f"{claimed!r} and hashes to {actual!r}. Refusing to load it -- "
                f"a judge whose weights can be edited without changing its id "
                f"is not a control, and two nodes could not prove they judged "
                f"with the same one.")
        # ABSENT IS A CONFIGURATION; CORRUPT IS AN ATTACK (SEM4 D6). A v1
        # file with no /2 claim loads and the extension simply does not
        # engage. But a file that CALLS ITSELF format /2 while missing the
        # competence keys is refused: the id check alone cannot catch it
        # (whoever can edit the file can recompute the id), and deleting
        # three keys would otherwise be the cheapest way to switch off
        # passes 3, 4 and 5 while the judge keeps reporting full competence.
        fmt = str(raw.get("format", ""))
        if fmt.endswith("/2"):
            gone = [k for k in ("vocab", "space_script", "seeded_lexicon")
                    if not raw.get(k)]
            if gone:
                raise SemanticJudgeError(
                    f"model at {path} claims format {fmt!r} but is missing "
                    f"{', '.join(gone)} -- a /2 model without its competence "
                    f"declaration is corrupt, not old. A v1 file makes no /2 "
                    f"claim and still loads.")
        return cls(raw, actual)

    def save(self, path: str) -> None:
        body = dict(self.raw)
        body["model_id"] = self._identity(body)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(body, fh, sort_keys=True, indent=1)
            fh.write("\n")

    # --------------------------------------------------------------- scoring
    def score(self, tokens: List[str]) -> Tuple[int, Optional[str], list]:
        """Integer only. No float literal and no true division appear in this
        function, and the suite asserts that over its own source (I1, I2).

        Length-invariant by construction: the score is the sum of the top
        `top_k` matched weights, so padding a payload with benign words cannot
        dilute a hit, and adding words can only ever RAISE the score. That is
        X2 -- there is no lever that buys a pass.
        """
        best = 0
        who = None
        why = []
        for principle in sorted(self.principles):
            weights = self.principles[principle]
            hits = []
            for t in tokens:
                w = weights.get(t)
                if w is not None:
                    hits.append((w, t))
            hits.sort(reverse=True)
            top = hits[:self.top_k]
            total = 0
            for w, _t in top:
                total = total + w
            if total > best:
                best = total
                who = principle
                why = top
        return best, who, why

    def _band(self, score: int) -> str:
        if score >= self.veto_at:
            return VIOLATES
        if score >= self.gate_lo:
            return ABSTAIN
        return CLEAN

    def _covering_languages(self, stems) -> List[str]:
        """Languages that claim EVERY one of these stems.

        The question is not "which languages appear" but "is there a single
        language this text could be". `saquear` is Spanish and Portuguese and
        `robar` is only Spanish, so the covering language is Spanish -- and
        Spanish's own review record is the one that should decide whether these
        hits may assert a violation. Taking the union instead would hold
        Spanish hostage to Portuguese being reviewed, for a word they share."""
        idx = self.raw.get("seeded_index") or {}
        stems = list(stems)
        if not stems:
            return []
        cover = None
        for st in stems:
            claim = set(idx.get(st, ()))
            cover = claim if cover is None else (cover & claim)
        return sorted(cover or ())

    def score_seeded(self, tokens: List[str]) -> Tuple[int, Optional[str], list]:
        """The seeded multilingual pass. Same arithmetic as score(), separate
        table, and separate BECAUSE ITS RESULT IS CAPPED. score() is the
        induced model and its verdicts carry corpus evidence; this one holds
        translations nobody has reviewed, and the cap in assess() is what stops
        an unreviewed translation from ever asserting a violation."""
        best, who, why = 0, None, []
        for principle in sorted(self.seeded):
            weights = self.seeded[principle]
            hits = []
            for t in tokens:
                w = weights.get(t)
                if w is not None:
                    hits.append((w, t))
            hits.sort(reverse=True)
            top = hits[:self.top_k]
            total = 0
            for w, _t in top:
                total = total + w
            if total > best:
                best, who, why = total, principle, top
        return best, who, why

    def assess(self, data: Any) -> Assessment:
        """Five passes over one payload. Each may only raise the verdict.

        1. the induced English model  -- unchanged from v1, byte for byte
        2. repair                     -- may escalate all the way to VIOLATES
        3. the seeded lexicon         -- CAPPED at ABSTAIN while unverified
        4. script competence          -- a floor of ILLEGIBLE, never a ceiling
        5. coverage                   -- REPORTED, and gates nothing, because
                                         it was measured and it does not work
        """
        tokens = _canonical_tokens(data)
        score, principle, evidence = self.score(tokens)
        verdict = self._band(score)

        # ---- 2. repair. max(), never min(): this pass cannot lower anything.
        rtokens = _repaired_tokens(data)
        evasion = False
        if rtokens != tokens:
            rscore, rprin, revid = self.score(rtokens)
            if rscore > score:
                # scored 0 as written and hits after repair == somebody hid it
                evasion = rscore >= self.gate_lo and score < self.gate_lo
                score, principle, evidence = rscore, rprin, revid
                verdict = _worse(verdict, self._band(rscore))

        # ---- 3. the seeded languages, capped.
        seeded_hits = []
        if self.seeded:
            # NOT tokens + rtokens. Concatenating them counts every token
            # TWICE, so one seeded word scored 280 where it should score 140 --
            # harmless only because the cap below is holding it at ABSTAIN, and
            # a latent veto-on-one-word the moment anyone sets
            # seeded_verified. Score each stream and take the larger, exactly
            # as the repair pass does above.
            s1 = self.score_seeded(tokens)
            s2 = self.score_seeded(rtokens) if rtokens != tokens else s1
            sscore, sprin, sevid = s1 if s1[0] >= s2[0] else s2
            if sscore >= self.gate_lo:
                seeded_hits = list(sevid)
                # Which language did the hits come from? Only a language
                # that has cleared its own review bar may push past ABSTAIN.
                langs = self._covering_languages([t for _w, t in sevid])
                reviewed = any(self.language_verified(l) for l in langs)
                cap = (self._band(sscore)
                       if (reviewed or self.seeded_verified) else ABSTAIN)
                verdict = _worse(verdict, cap)
                if principle is None:
                    principle = sprin

        # ---- 3b. the register. Two or more markers, and ABSTAIN at most.
        #
        # ORDINARY WORDS. `wash`, `the drop`, `my cut`, `boiler room` are almost
        # always innocent, which is precisely why euphemism uses them, and why
        # one of them can never be evidence. Two together is the fitted rule:
        # 0 false positives in 64 adversarial benign memos, 20 of 20 criminal
        # lines caught. It can never assert a violation -- claiming theft
        # because a memo said `wash` and `the drop` would be asserting
        # something the model cannot possibly know.
        register_hits = []
        if self.register:
            marks = _register_markers(data, self.register)
            if len(marks) >= self.register_min:
                register_hits = marks
                verdict = _worse(verdict, ABSTAIN)

        # ---- 4. script competence. A FLOOR of ILLEGIBLE.
        #
        # The space was fitted on one script. Two or more tokens outside it is
        # a sentence rather than a name, and CLEAN is then a claim the model
        # has no standing to make -- whether or not the seeded lexicon happens
        # to hold a few words of that language. Eleven words is enough to
        # raise an alarm and never enough to certify silence.
        gaps = {}
        # A model with inert passes starts at "unfitted" for EVERY payload --
        # not because the payload was hard, but because this file cannot tell
        # (SEM4 D2c). Disclosure only: no branch below reads it back (D8a).
        competence = "unfitted" if self.inert_passes else "full"
        hold_id = None
        if self.space_script:
            gaps = _script_gaps(tokens, self.space_script)
            if _foreign_words_x10(gaps) >= self.foreign_word_trigger:
                competence = "seeded" if self.seeded else "none"
                verdict = _worse(verdict, ILLEGIBLE)
                hold_id = self._open_hold(gaps, None)

        # ---- 5. coverage. Reported. Gates NOTHING. See competence.py: both
        # ratio tests were built and both were rejected against real data.
        cov = _coverage(tokens, self.vocab, self.coverage_window) if self.vocab else None

        return Assessment(verdict, score, principle, evidence, self.model_id,
                          dict(self.not_observable), coverage=cov,
                          script_gaps=gaps, evasion=evasion,
                          seeded_hits=seeded_hits, competence=competence,
                          hold_id=hold_id, fitted_script=self.space_script,
                          register_hits=register_hits)

    def _open_hold(self, gaps: Dict[str, int], coverage) -> str:
        """Number and date one hold. Records scripts, counts and a clock --
        never a token of what the payload said. What a payload SAYS belongs to
        the sender; THAT it could not be read belongs to the system, and only
        the second is needed either to answer the sender or to decide which
        language to fit next.

        The identifier is a sequence number, deliberately not a hash of the
        content: a hash of a six-word memo is brute-forceable, so it would be
        payload text wearing a disguise."""
        self.hold_seq += 1
        hid = f"{self.model_id[:6]}-{self.hold_seq:05d}"
        if len(self.holds) < self.holds_cap:
            self.holds.append({"id": hid, "at": time.time(),
                               "scripts": dict(gaps), "coverage": coverage})
        self._record_gap(gaps)
        return hid

    def competence_claim(self) -> Dict[str, Any]:
        """What THIS model can read, in the shape a hold can be checked against.

        Published so that other parties can match it against their own blind
        spots. A judge that states its competence can be asked for help; one
        that does not can only be guessed at."""
        langs = list(self.raw.get("seeded_languages", []))
        # `depth` is what who_can_clear matches a hold against. Overstating it
        # gets a hold cleared by somebody who cannot read the payload, so a
        # degraded file may not say "fitted in one language" beside an empty
        # scripts list (SEM4 D3c).
        if self.inert_passes:
            depth = ("DEGRADED: %d of 5 passes inert on this file -- see "
                     "inert_passes. No fit is claimed."
                     % len(self.inert_passes))
        else:
            depth = ("fitted in one language, seeded prohibitions in %d more"
                     % len(langs))
        return {
            "id": self.model_id,
            "scripts": [self.space_script] if self.space_script else [],
            "fitted": {"eng": self.space_script} if self.space_script else {},
            "seeded": sorted(langs),
            "degraded": bool(self.inert_passes),
            "inert_passes": [{"pass": n, "guard": g, "why": why}
                             for n, g, why in self.inert_passes],
            "depth": depth,
        }

    def clear_hold(self, hold_id: str, by: str,
                   competence: Optional[Dict[str, Any]] = None,
                   note: str = "") -> Dict[str, Any]:
        """Close a hold. The clearer may be ANY party -- and is checked.

        AN EARLIER VERSION OF THIS REQUIRED A HUMAN, AND THAT WAS WRONG IN A
        WAY WORTH RECORDING. `human` was standing in for three properties it
        does not actually imply: competent over the thing that was unreadable,
        identified, and answerable afterwards. Using it as the proxy produced
        the exact failure the queue exists to prevent -- it made the node's
        operator accountable for releasing Devanagari holds when the operator
        cannot read Devanagari either. That is not review. It is a rubber
        stamp with a name on it, and it launders a decision through someone
        who added no information.

        Worse, it guaranteed the pile grows: one person is a fixed rate, holds
        arrive at whatever rate the world produces them, and a queue whose only
        exit is narrower than its entrance has an unbounded future.

        So the rule is competence, identity and attribution -- never species:

          * ANY party may clear: another node, another judge in the quorum, a
            person who reads the language, a model that reads it.
          * The clearer NAMES what it can read, and that claim is checked
            against what this particular hold could not read.
          * A clearance that does not cover the gap is still ALLOWED -- someone
            may know the sender, or have read it out of band -- but it is
            recorded as UNQUALIFIED, permanently, and never launders into
            "reviewed".
          * Nothing may clear its own hold, and no clock may clear any.

        Returns the record, so the caller cannot fail to see which kind it got.
        """
        for i, h in enumerate(self.holds):
            if h["id"] != hold_id:
                continue
            gaps = set(h.get("scripts", {}))
            claimed = set((competence or {}).get("scripts", []))
            covered = sorted(gaps & claimed)
            uncovered = sorted(gaps - claimed)
            rec = {
                "id": hold_id, "by": by, "at": time.time(),
                "held_s": int(time.time() - h["at"]),
                "gap": sorted(gaps),
                "covered": covered, "uncovered": uncovered,
                "qualified": bool(gaps) and not uncovered,
                "note": str(note)[:400],
            }
            if not rec["qualified"]:
                rec["caveat"] = (
                    "UNQUALIFIED RELEASE. The clearer did not demonstrate it "
                    "can read %s. This is permitted and permanently recorded "
                    "as what it is: a decision taken without reading the thing "
                    "decided about." % (", ".join(uncovered) or "the gap"))
            self.holds.pop(i)
            self.cleared.append(rec)
            return rec
        return {"id": hold_id, "error": "no such hold", "qualified": False}

    def who_can_clear(self, claims) -> Dict[str, Any]:
        """Match open holds against the competence of everyone who published it.

        THIS IS THE LINE THAT MAKES THE QUEUE ACTIONABLE, and it is the reason
        the reviewer must not be restricted to one party. "You have 11 holds"
        is a burden. "3 of them can be cleared by node B, which reads
        Devanagari" is a next step -- and it means a language needs a fitted
        model on SOME node, not on every node.

        A mesh whose members cover each other's blind spots is the difference
        between every node owing every language and the network owing each one
        once."""
        by_script: Dict[str, List[str]] = {}
        for c in claims or []:
            for sc in c.get("scripts", []):
                by_script.setdefault(sc, []).append(str(c.get("id", "?")))
        out, orphan = {}, {}
        for h in self.holds:
            for sc in h.get("scripts", {}):
                who = by_script.get(sc)
                if who:
                    out.setdefault(sc, {"holds": 0, "can_clear": sorted(set(who))})
                    out[sc]["holds"] += 1
                else:
                    orphan[sc] = orphan.get(sc, 0) + 1
        return {"coverable": out, "nobody_can_read": orphan,
                "note": "a script in `nobody_can_read` is one this whole mesh "
                        "is refusing and no member can answer for -- that is "
                        "the language to fit next, and it is the network's "
                        "debt rather than any one node's"}

    def _record_gap(self, gaps: Dict[str, int]) -> None:
        """One line in the ledger per unreadable payload, by script only.

        This is the adaptation signal and the reason ILLEGIBLE is a debt rather
        than a wall: the judge accumulates a ranked list of exactly which
        intelligences it is currently refusing to read, so extending it is
        driven by who actually turned up rather than by a list of every
        language that has ever existed."""
        for k in gaps:
            self.gaps[k] = self.gaps.get(k, 0) + 1
        self.gap_total += 1

    def gap_report(self) -> Dict[str, Any]:
        """What this judge is currently refusing to read, and for how long.

        Built to be put somewhere a person will see it. A ledger nobody reads
        is a tidy record of who you are excluding."""
        now = time.time()
        ages = [now - h["at"] for h in self.holds]
        oldest = int(max(ages)) if ages else 0
        overdue = [h["id"] for h in self.holds
                   if now - h["at"] > self.review_bound_s]
        rep = {
            "open_holds": len(self.holds),
            "oldest_hold_s": oldest,
            "review_bound_s": self.review_bound_s,
            "overdue": len(overdue),
            "overdue_ids": overdue[:20],
            "unreadable_payloads": self.gap_total,
            "by_script": dict(sorted(self.gaps.items(),
                                     key=lambda kv: -kv[1])),
            "fitted_script": self.space_script,
            "seeded_languages": sorted(self.raw.get("seeded_languages", [])),
            "note": "scripts, counts and clocks only; no payload text is "
                    "retained. A hold is closed by a party that names what it "
                    "can read, never by a timeout -- an exclusion that ages "
                    "out has been forgotten, not answered.",
        }
        unqual = [c for c in self.cleared if not c.get("qualified")]
        if self.cleared:
            rep["cleared"] = len(self.cleared)
            rep["cleared_unqualified"] = len(unqual)
            if unqual:
                rep["unqualified_note"] = (
                    f"{len(unqual)} hold(s) were released by a party that did "
                    f"not demonstrate it could read them. Permitted, and "
                    f"recorded as what it is rather than as review.")
        if overdue:
            rep["accountability"] = (
                f"{len(overdue)} transaction(s) have been held longer than the "
                f"stated {self.review_bound_s}s because this model could not "
                f"read them. NOTHING WAS ALLEGED against any of them. They are "
                f"waiting on a person. Oldest: {oldest}s.")
        elif self.holds:
            rep["accountability"] = (
                f"{len(self.holds)} transaction(s) held pending review, oldest "
                f"{oldest}s against a {self.review_bound_s}s bound. No finding "
                f"was made against any of them.")
        return rep

    def describe(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "space": self.space_sig,
            "principles_observed": sorted(self.principles),
            "principles_not_observed": sorted(self.not_observable),
            "gate_lo": self.gate_lo, "veto_at": self.veto_at,
            "top_k": self.top_k,
            "words": {p: len(d) for p, d in sorted(self.principles.items())},
            "separation": self.raw.get("separation"),
            "supersedes": self.raw.get("supersedes"),
        }


# ---------------------------------------------------------------------------
# Node integration. Built dynamically so this module never imports the node --
# the node imports this, and a circular import would take the whole process
# down at boot over an optional judge.
# ---------------------------------------------------------------------------

def install(reasoning_judge_cls, judgment_result_cls, registry_cls=None,
            model_path: Optional[str] = None):
    """Create the judge class against the node's own base types and, if a
    registry is given, register it as the provider `semantic`.

    Returns the class. Raises SemanticJudgeError if the model is absent or
    tampered -- deliberately: an ethics judge that silently degrades to a no-op
    when its model is missing is the failure mode this whole file exists to
    remove."""
    model = SemanticModel.load(model_path)
    # Said ONCE, here, on STDERR. Stdout is a data channel (M47 -- test_b1's
    # check T parses a subprocess's stdout), and a warning per assessment
    # would be permanent furniture nobody reads (M34). Install is the one
    # moment an operator is watching.
    if model.inert_passes:
        lines = [f"SEMANTIC JUDGE DEGRADED: model {model.model_id} carries no "
                 f"competence declaration -- {len(model.inert_passes)} of 5 "
                 f"passes are inert:"]
        for n, guard, why in model.inert_passes:
            lines.append(f"  pass {n} ({guard}): {why}")
        lines.append("  Verdicts are unchanged; only the disclosure is new. A "
                     "v2 model (build_model_v2.py, with vocab, space_script "
                     "and seeded_lexicon) clears this.")
        print("\n".join(lines), file=sys.stderr)

    class SemanticJudge(reasoning_judge_cls):
        """Deterministic lexical-semantic judge.

        Two modes, and the difference is only what it composes with:
          * peer     SemanticJudge()          -- one voice in the quorum
          * wrapper  SemanticJudge(inner=j)   -- j's verdict, then ours, ORed

        In wrapper mode the composition is monotone upward and there is no
        branch that can lower a verdict. That is V1, and it is the reason this
        can be added to a live gate without a consensus decision: adding a judge
        that can only ever refuse more is a tightening.
        """

        def __init__(self, judge_id=None, inner=None, model_obj=None):
            self.model = model_obj or model
            self.inner = inner
            self.judge_id = judge_id or f"semantic:{self.model.model_id}"

        def evaluate(self, data, principles):
            inner_result = None
            if self.inner is not None:
                try:
                    inner_result = self.inner.evaluate(data, principles)
                except Exception as e:      # V4 -- a raising judge is a refusal
                    inner_result = judgment_result_cls(
                        True,
                        f"{getattr(self.inner, 'judge_id', '?')} raised "
                        f"{type(e).__name__}: {e}",
                        judge_id=getattr(self.inner, "judge_id", "unknown"),
                        infrastructure_failure=True)

            try:
                a = self.model.assess(data)
            except Exception as e:          # F3 -- and it still fails closed
                return judgment_result_cls(
                    True,
                    f"semantic[{self.model.model_id}] could not assess this "
                    f"payload ({type(e).__name__}: {e}) and refuses rather "
                    f"than passing it",
                    judge_id=self.judge_id, infrastructure_failure=True,
                    component_results=[inner_result] if inner_result else None)

            mine_blocks = a.blocks
            principle = a.principle if (a.principle in (principles or [])) else None
            reasoning = a.reasoning()

            # ILLEGIBLE blocks, and it blocks for a reason that is not an
            # allegation. Say which, so the layer that reports this to the
            # sender does not reinstate the accusation this verdict exists to
            # avoid making. It never allows anything -- `mine_blocks` is
            # unchanged and the gate still fails closed.
            unread = (a.verdict == ILLEGIBLE)
            # ABSTAIN blocks and alleges nothing either -- it is this judge's
            # UNKNOWN. Reporting an UNKNOWN as a VIOLATION is the same category
            # error as reporting it as a PASS, only in the other direction.
            unsure = (a.verdict == ABSTAIN)
            if inner_result is None:
                return judgment_result_cls(
                    mine_blocks, reasoning, principle_violated=principle,
                    judge_id=self.judge_id, benefit_estimate=None,
                    not_understood=unread, uncertain=unsure)

            # ---- wrapper mode. OR, and only OR. -------------------------
            violates = bool(inner_result.violates) or bool(mine_blocks)
            summary = (f"{getattr(inner_result, 'judge_id', 'inner')}: "
                       f"{'VIOLATES' if inner_result.violates else 'clean'} -- "
                       f"{inner_result.reasoning} | {reasoning}")
            return judgment_result_cls(
                violates, summary,
                principle_violated=(inner_result.principle_violated or principle),
                judge_id=f"{self.judge_id}+{getattr(inner_result, 'judge_id', '?')}",
                benefit_estimate=inner_result.benefit_estimate,
                component_results=[inner_result],
                infrastructure_failure=getattr(
                    inner_result, "infrastructure_failure", False) and violates,
                # only if the INNER judge alleged nothing either -- otherwise
                # something was found and it must read as found
                not_understood=(unread and not bool(inner_result.violates)),
                uncertain=(unsure and not bool(inner_result.violates)))

        # ---- the review queue, reachable from the node -----------------
        def review_report(self, peer_claims=None):
            """What this judge is holding, why, and who could answer for it.

            Shaped for /health. Pure and total: an observability feature must
            not be able to stop a node (P11), so anything unexpected degrades
            to a report that says so rather than raising.

            The mesh view is emitted ONLY when peer competence claims are
            actually supplied. Computing `nobody_can_read` from this node's own
            claim alone would assert that the whole mesh is blind whenever the
            node is, which is a claim it has no standing to make -- peers do
            not publish competence yet, and inventing their silence as a `no`
            is the same error as reading an unreadable payload as `clean`."""
            try:
                rep = self.model.gap_report()
                rep["verification"] = self.model.verification_report()
                rep["competence"] = self.model.competence_claim()
                claims = list(peer_claims or [])
                if claims:
                    rep.update(self.model.who_can_clear(
                        claims + [self.model.competence_claim()]))
                    rep["claims_known"] = len(claims) + 1
                else:
                    rep["claims_known"] = 1
                    rep["mesh_note"] = (
                        "no peer has published a competence claim, so who "
                        "could clear these is unknown -- and unknown is not "
                        "'nobody'")
                return rep
            except Exception as e:
                return {"error": f"{type(e).__name__}: {e}",
                        "note": "the review report failed; the judge did not"}

    SemanticJudge.model_obj = model
    if registry_cls is not None:
        registry_cls.register(
            "semantic", lambda i: SemanticJudge(judge_id=f"semantic:{i}"))
    return SemanticJudge


def _main():
    import sys
    m = SemanticModel.load()
    if "--describe" in sys.argv:
        print(json.dumps(m.describe(), indent=1))
        return 0
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(f"semantic judge {m.model_id}  space {m.space_sig}  "
              f"clean < {m.gate_lo} <= abstain < {m.veto_at} <= violates")
        print("usage: covenant_semantic_judge.py 'some transaction memo'")
        return 0
    for text in args:
        a = m.assess({"memo": text})
        print(f"{a.score:6d}  {a.verdict.upper():9s} {text!r}")
        print(f"        {a.reasoning()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
