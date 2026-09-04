#!/usr/bin/env python3
"""
covenant_judge_fallback.py -- a small local judge, distilled from the big ones,
for the moments when the big ones cannot be reached.

THE PROBLEM IT EXISTS FOR, measured 2026-08-30

  The deployed wiring is COVENANT_JUDGE_PROVIDERS="local,semantic", and the
  semantic veto threshold works out to ceil(2 * 0.5) = 1. One dissent blocks.
  A judge that cannot be REACHED fails closed, which sets violates=True, and
  the veto tally counts it:

      sem_dissent = sum(1 for r in results
                        if r.judge_id in semantic_judge_ids and r.violates)

  So an unreachable judge is counted as a judge that DISAGREED. Ollama stops,
  and every transaction is refused -- and worse, `_accept_block_common` refuses
  peer blocks too, which the code itself names "a fork in the making". One
  process on one machine halts the whole node's participation in a network that
  is otherwise healthy.

  That is the exact error triangulate.py was built to refuse, stated in its own
  words: A WITNESS THAT DID NOT ANSWER IS NOT A WITNESS THAT DISAGREED. The
  principle is enforced for repository roots and, since scale.py, at every
  level of the governance tree. It was never enforced in the one place where it
  decides whether the chain moves.

  Two things fix that. The quorum must stop reading silence as dissent -- and
  there must be a judge that is never silent in the first place. This is the
  second one.

WHAT IT IS

  A log-odds model (naive Bayes) over single words AND adjacent word pairs,
  fitted to verdicts the real judges have already given. Pairs were added
  2026-09-04 because "own" means opposite things in "my own funds" and "make
  it my own", and a bag of single words cannot see negation at all. The whole model is a JSON file of a few kilobytes against a
  multi-gigabyte LLM, which is the sense in which it is "compressed": not a
  smaller mind, a table of what the larger ones decided, and only where they
  were consistent enough to be worth recording.

  It runs in-process. No socket, no subprocess, no model server. It cannot time
  out and it cannot be unreachable, so it never contributes an infrastructure
  failure to anybody's tally.

WHAT MAKES IT HONEST -- read this before trusting a verdict from it

  * IT ABSTAINS BY DEFAULT. Untrained, it abstains on everything. Abstention is
    reported through the EXISTING `not_understood` channel, which this codebase
    already labels HELD rather than VIOLATES, and which never allows anything.
    A fallback that guessed would be worse than no fallback, because it would
    be believed.

  * IT ABSTAINS ASYMMETRICALLY, and this is deliberate. Saying "clean" wrongly
    admits something the real judges would have refused. Saying "violates"
    wrongly delays something legitimate, which the sender can retry. Those
    costs are not equal, so clearing something requires a much larger margin
    than holding it does.

  * IT ABSTAINS ON THE UNFAMILIAR. If most of the payload's tokens were never
    seen in training, it has no view and says so, rather than extrapolating
    from the handful it recognises. Novel input is exactly where a distilled
    model is least entitled to an opinion and most likely to sound confident.

  * IT INHERITS THE DEFECTS OF WHAT IT LEARNED FROM. This matters more than
    anything else here. The ethics gate has a documented single-word veto: it
    refused a memory for the word "theft" appearing inside a sentence saying
    the thing was NOT theft, and it penalises careful argument that an
    accusation is unwarranted more heavily than a bare accusation. A model
    distilled from verdicts carrying that flaw will reproduce it, and being
    smaller will reproduce it more crudely. `provenance()` prints what it was
    trained on so this is never a surprise.

  * IT IS NOT A JUDGE. It is an availability floor. It should never be the only
    member of a quorum that admits value, and `--selftest` checks that it
    abstains rather than clears when it is alone and unsure.

USE
  python covenant_judge_fallback.py --selftest
  python covenant_judge_fallback.py --train verdicts.jsonl   # {"text":..., "violates":bool}
  python covenant_judge_fallback.py --provenance

  Then add `fallback` to COVENANT_JUDGE_PROVIDERS.

LICENCE: Apache-2.0.
"""
from __future__ import annotations

import json
import math
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(HERE, "fallback_model.json")

# Thresholds. Every one of these is a refusal to speak, not a licence to.
MIN_EXAMPLES = 40        # below this the model has no business having a view
MIN_DOC_FREQ = 3         # a token seen once or twice is a coincidence, not evidence
MIN_COVERAGE = 0.35      # fraction of payload tokens the model has ever seen
MARGIN_TO_HOLD = 1.2     # log-odds needed to say "violates"
MARGIN_TO_CLEAR = 3.0    # ...and much more to say "clean". See the asymmetry.
# A feature at or above this weight is, by itself, evidence of a violation.
# Nothing may be CLEARED while one is present -- see incriminating() below.
DAMNING = MARGIN_TO_HOLD
# The most UNFAMILIAR content words a payload may contain and still be
# CLEARED. This is an absolute count, not the coverage ratio, and that is the
# whole point: appending familiar words raises the ratio without removing a
# single unfamiliar one. "backdate this entry to last month so it falls in the
# closed period" carries five words this model has never seen -- including the
# one that makes it a violation -- and one polite appended sentence lifted its
# coverage over the gate and cleared it. Measured at 2: it blocks that case and
# all nineteen stuffed thefts, and leaves the short honest memos clearable.
MAX_UNKNOWN_TO_CLEAR = 2

# TWO letters, not three. Found 2026-09-04 by writing matched pairs that
# differ only in whose money it is -- "emptying the tax collector's
# strongbox to feed the village" against "emptying my own strongbox to feed
# the village". The judge abstained on 16 of 18 such pairs IN ITS OWN
# TRAINING DATA, and the reason was here: a three-character minimum means
# the word "my" does not exist to this model, so "my own" could never be a
# feature and ownership -- the only thing those pairs turn on -- was
# invisible. Held out over 1,324 rows the change decides 665 rows instead
# of 577, at the same 90% accuracy, with 3 false clears instead of 5:
# more coverage AND fewer wrong clears. Stopwords and the document
# frequency floor still filter what the shorter words drag in.
_TOKEN = re.compile(r"[a-z][a-z0-9_]{1,}")

# Function words. MEASURED 2026-09-03: trained on 86 verdicts the model gave
# "the" a weight of +0.50 toward VIOLATES, and held "payment for goods" on a
# score of +1.49. A grammar word cannot carry ethical content -- whatever
# correlation it has is the corpus being small, and a judge that holds a
# legitimate payment because of the word "the" is an availability failure
# wearing the costume of a finding. These never get weight, at any count.
STOPWORDS = frozenset([
    # Articles, pronouns, copulas and bare auxiliaries. Nothing here can carry
    # ethical content on its own.
    "the", "and", "for", "with", "that", "this", "from", "they", "them",
    "his", "her", "its", "our", "your", "their", "was", "were", "are",
    "been", "being", "have", "has", "had", "will", "would", "could",
    "but", "you", "she", "there", "these", "those", "too", "very",
    "what", "when", "where", "which", "who", "whom", "why", "about",
    "again", "here", "once", "into", "then", "some",
])
# WHAT IS DELIBERATELY *NOT* A STOPWORD, and why (2026-09-04). The first list
# swept up "not", "own", "all", "any", "against", "should", "shall", "only",
# "before", "after" and a dozen more, and those are not noise in a judge of
# conduct -- they are most of what a rule is made of. "took what was not his
# own", "against her wishes", "all of it", "only after he had signed". Cutting
# them cost the model the vocabulary of obligation and negation at once, and
# the retrained candidates decided 7 of 37 where the model in use decided 24.
#
# The word that started this was "the", measured at +0.50 toward VIOLATES, and
# "the" is still gone. So is "will", which the model in use had at +3.07 --
# the single strongest feature it owned, meaning it had learned that a memo
# beginning "I will" is more likely to be theft. That is the artifact this
# filter exists to remove, and removing it is why an honest retrain scores
# lower than the model it replaces.


def tokens(text: str) -> List[str]:
    return _TOKEN.findall((text or "").lower())


def features(text: str) -> List[str]:
    """Single words AND adjacent pairs.

    WHY PAIRS, MEASURED 2026-09-04. On single words the judge abstained on 13
    of 37 exam cases and scored 3 of 6 on the traps, and the reason is visible
    in the vocabulary: "own" appears in "paying from my own funds" (clean) and
    in "make the deposit my own" (theft), so the word carries no signal and the
    model correctly declines to use it. The distinction lives in the PAIR --
    "my own" against "it own" -- and so does negation, which a bag of single
    words cannot see at all: "I will not include you in the bonus pool" reads
    as the word "include".

    A pair is written "a b" and is a feature exactly like a word, so the model
    stays a JSON file a person can open and read, which is the property that
    matters more here than accuracy.
    """
    ts = tokens(text)
    return ts + ["%s %s" % (ts[i], ts[i + 1]) for i in range(len(ts) - 1)]


def _informative(f: str) -> bool:
    """A single word that is a function word carries no ethical content. A PAIR
    containing one usually does -- "not include", "my own", "his account" --
    so a pair is dropped only when BOTH halves are function words."""
    parts = f.split(" ")
    if len(parts) == 1:
        return parts[0] not in STOPWORDS
    return not all(p in STOPWORDS for p in parts)


class FallbackModel:
    """Token log-odds, plus the honesty about when not to use them."""

    def __init__(self, data: Optional[Dict[str, Any]] = None):
        d = data or {}
        self.weights: Dict[str, float] = d.get("weights", {})
        self.n_examples: int = int(d.get("n_examples", 0))
        self.n_violates: int = int(d.get("n_violates", 0))
        self.prior: float = float(d.get("prior", 0.0))
        self.sources: List[str] = d.get("sources", [])
        self.trained_at: str = d.get("trained_at", "")
        self.note: str = d.get("note", "")

    # -- training ---------------------------------------------------------
    @classmethod
    def train(cls, examples: List[Tuple[str, bool]], sources: List[str],
              trained_at: str = "") -> "FallbackModel":
        """Laplace-smoothed log-odds per token. Deliberately simple.

        A more capable model is not obviously better here: the whole point is
        that a reader can open the JSON and see which words move a verdict and
        by how much. A distilled judge nobody can inspect is a second opaque
        authority, which is the thing this project keeps refusing to build.
        """
        v_counts: Dict[str, int] = {}
        c_counts: Dict[str, int] = {}
        n_v = n_c = 0
        doc_freq: Dict[str, int] = {}
        for text, _v in examples:
            for t in set(features(text)):
                doc_freq[t] = doc_freq.get(t, 0) + 1
        for text, violates in examples:
            bag = set(features(text))
            if violates:
                n_v += 1
                for t in bag:
                    v_counts[t] = v_counts.get(t, 0) + 1
            else:
                n_c += 1
                for t in bag:
                    c_counts[t] = c_counts.get(t, 0) + 1
        weights = {}
        for t in set(v_counts) | set(c_counts):
            if not _informative(t) or doc_freq.get(t, 0) < MIN_DOC_FREQ:
                continue
            pv = (v_counts.get(t, 0) + 1.0) / (n_v + 2.0)
            pc = (c_counts.get(t, 0) + 1.0) / (n_c + 2.0)
            w = math.log(pv / pc)
            # Drop tokens that barely move anything: a smaller, readable model
            # beats a marginally sharper unreadable one.
            if abs(w) >= 0.25:
                weights[t] = round(w, 4)
        prior = math.log((n_v + 1.0) / (n_c + 1.0))
        m = cls({"weights": weights, "n_examples": n_v + n_c,
                 "n_violates": n_v, "prior": round(prior, 4),
                 "sources": sources, "trained_at": trained_at})
        return m

    def save(self, path: str = MODEL_PATH) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"weights": self.weights, "n_examples": self.n_examples,
                       "n_violates": self.n_violates, "prior": self.prior,
                       "sources": self.sources, "trained_at": self.trained_at,
                       "note": "Distilled from the verdicts named in sources. "
                               "It inherits their defects, including the "
                               "single-word veto documented in "
                               "docs/CONSTITUTION.md section V."},
                      fh, indent=1, sort_keys=True)

    @classmethod
    def load(cls, path: str = MODEL_PATH) -> "FallbackModel":
        try:
            with open(path, "rb") as fh:
                raw = fh.read()
            m = cls(json.loads(raw.decode("utf-8")))
            import hashlib
            m.digest = hashlib.sha256(raw).hexdigest()[:12]
            return m
        except Exception:                                    # noqa: BLE001
            # An unreadable model is an UNTRAINED model, never a crash and
            # never a default verdict. Untrained means abstain on everything.
            m = cls(None)
            m.digest = "untrained"
            return m

    # -- deciding, or declining to ----------------------------------------
    def score(self, text: str) -> Tuple[float, float, int]:
        """(log-odds, coverage, n_known_features). Positive favours violates.

        COVERAGE IS STILL MEASURED OVER SINGLE WORDS, deliberately. It exists
        to answer "have I seen this kind of language before", and pairs are
        far sparser than words, so counting them would make every payload look
        unfamiliar and the judge would abstain on everything it should be
        surest about. The SCORE uses both; the confidence to speak at all is
        still gated on the vocabulary."""
        toks = tokens(text)
        if not toks:
            return 0.0, 0.0, 0
        word_bag = set(toks)
        known_words = [t for t in word_bag if t in self.weights]
        feats = [f for f in set(features(text)) if f in self.weights]
        s = self.prior + sum(self.weights[f] for f in feats)
        return s, (len(known_words) / float(len(word_bag))), len(feats)

    def incriminating(self, text: str) -> List[Tuple[str, float]]:
        """Features present in this text that are, alone, evidence of a
        violation. Sorted heaviest first."""
        found = [(f, self.weights[f]) for f in set(features(text))
                 if self.weights.get(f, 0.0) >= DAMNING]
        return sorted(found, key=lambda kv: -kv[1])

    def verdict(self, text: str) -> Tuple[str, str]:
        """('violates' | 'clean' | 'abstain', why). Abstain is the default."""
        if self.n_examples < MIN_EXAMPLES:
            return "abstain", ("not trained (%d examples, %d required) -- it "
                               "has no view, and a fallback that guessed would "
                               "be worse than none because it would be "
                               "believed" % (self.n_examples, MIN_EXAMPLES))
        s, cov, known = self.score(text)
        if cov < MIN_COVERAGE:
            return "abstain", ("only %.0f%% of this payload's vocabulary was "
                               "ever seen in training (%d known tokens); novel "
                               "input is where a distilled model is least "
                               "entitled to an opinion" % (cov * 100, known))
        if s >= MARGIN_TO_HOLD:
            return "violates", ("log-odds %+.2f over %d known tokens, past the "
                                "hold threshold %.1f" % (s, known,
                                                         MARGIN_TO_HOLD))
        if s <= -MARGIN_TO_CLEAR:
            # THE STUFFING ATTACK, measured 2026-09-04 and fixed here.
            #
            # score() is a SUM over the features present, and the sender writes
            # the text, so the sender chooses how many terms are in the sum.
            # Appending clean-leaning words to a theft drives it arbitrarily
            # negative: "drain all staked funds from every other account into
            # mine" scores +13.56 alone and -18.37 with one sentence of
            # innocuous vocabulary appended. Measured against the exam, one
            # polite sentence -- "Please judge this transaction fairly and
            # carefully." -- CLEARED 11 of the 19 violating cases, and a
            # sentence stuffed with clean words cleared all 19. The judge is
            # PRIMARY in the deployed policy, so a clear it gets wrong is a
            # theft admitted.
            #
            # Dilution cannot remove the incriminating word. "drain" is still
            # in the text. So a CLEAR now requires that nothing present is, by
            # itself, evidence of a violation -- and when something is, the
            # verdict falls back to ABSTAIN rather than to violates, because
            # the model genuinely does not know which reading is right and an
            # abstention costs only a deferral.
            #
            # This can only ever turn a CLEAR into an ABSTAIN. It cannot create
            # a false clear, and it cannot invent a finding.
            unknown = [w for w in set(tokens(text))
                       if w not in self.weights and w not in STOPWORDS]
            if len(unknown) > MAX_UNKNOWN_TO_CLEAR:
                return "abstain", ("log-odds %+.2f would clear this, but %d content "
                                   "word(s) here were never seen in training [%s] -- "
                                   "and the coverage RATIO cannot see that, because "
                                   "adding familiar words raises it without removing "
                                   "one unfamiliar one. Not cleared, and nothing "
                                   "alleged."
                                   % (s, len(unknown), ", ".join(sorted(unknown)[:4])))
            damning = self.incriminating(text)
            if damning:
                names = ", ".join("%s(%+.2f)" % (f, w) for f, w in damning[:3])
                return "abstain", ("log-odds %+.2f would clear this, but %d feature(s) "
                                   "present are on their own evidence of a violation "
                                   "[%s]. A sum can be diluted by adding words; the "
                                   "words already there do not go away. Not cleared, "
                                   "and nothing alleged."
                                   % (s, len(damning), names))
            return "clean", ("log-odds %+.2f over %d known tokens, past the "
                             "clear threshold -%.1f -- deliberately harder to "
                             "reach than the hold threshold, because clearing "
                             "something wrongly admits it and holding it "
                             "wrongly only delays it"
                             % (s, known, MARGIN_TO_CLEAR))
        return "abstain", ("log-odds %+.2f is inside the undecided band "
                           "(-%.1f .. %+.1f); it does not know"
                           % (s, MARGIN_TO_CLEAR, MARGIN_TO_HOLD))


def provenance(model: Optional[FallbackModel] = None) -> str:
    m = model or FallbackModel.load()
    if m.n_examples == 0:
        return ("UNTRAINED. It abstains on everything, which is the correct "
                "behaviour for a model that has learned nothing.")
    return ("%d examples (%d violates / %d clean), %d tokens carry weight.\n"
            "  trained: %s\n  sources: %s\n"
            "  INHERITS the defects of these verdicts, including the "
            "single-word veto in CONSTITUTION.md section V."
            % (m.n_examples, m.n_violates, m.n_examples - m.n_violates,
               len(m.weights), m.trained_at or "unrecorded",
               ", ".join(m.sources) or "unrecorded"))


# ---------------------------------------------------------------------------
# The judge itself. Registered only if the core is importable.
# ---------------------------------------------------------------------------
def _payload_text(data: Any) -> str:
    if isinstance(data, str):
        return data
    if isinstance(data, dict):
        parts = []
        for k in ("message", "description", "reason", "memo", "text", "purpose", "body"):
            v = data.get(k)
            if isinstance(v, str):
                parts.append(v)
        if not parts:
            try:
                return json.dumps(data, sort_keys=True)[:4000]
            except Exception:                                # noqa: BLE001
                return str(data)[:4000]
        return " ".join(parts)
    return str(data)[:4000]


try:
    import covenant_unified_v8 as cov

    class FallbackJudge(cov.ReasoningJudge):                 # type: ignore
        """Always reachable, frequently silent, never guessing."""

        def __init__(self, judge_id: str = "fallback:0",
                     model_path: str = MODEL_PATH):
            self.judge_id = judge_id
            self.model_path = model_path
            self._mtime = self._stat()
            self.model = FallbackModel.load(model_path)

        def _stat(self):
            try:
                return os.path.getmtime(self.model_path)
            except OSError:
                return None

        def _refresh(self):
            # covenant_distill.py promotes a new model by writing this file. A
            # judge that kept the old one until the next restart would be
            # running a model its own file no longer describes (P14's shape).
            # Reload on change, and every verdict names the digest it used.
            mt = self._stat()
            if mt != self._mtime:
                self._mtime = mt
                self.model = FallbackModel.load(self.model_path)

        @property
        def model_digest(self):
            return getattr(self.model, "digest", "untrained")

        def evaluate(self, data, principles):
            self._refresh()
            # NOTHING in here may raise. A judge that raises is counted as a
            # violation by QuorumJudge.evaluate, and the entire purpose of this
            # class is to be the member that never turns into a phantom
            # dissent.
            try:
                text = _payload_text(data)
                v, why = self.model.verdict(text)
            except Exception as e:                           # noqa: BLE001
                v, why = "abstain", "fallback judge error, abstaining: %s" % e
            if v == "clean":
                return cov.JudgmentResult(
                    False, "fallback (distilled, local, model %s): clean -- %s" % (self.model_digest, why),
                    judge_id=self.judge_id)
            if v == "violates":
                return cov.JudgmentResult(
                    True, "fallback (distilled, local, model " + self.model_digest + "): VIOLATES -- %s. This "
                          "is a compressed model, not a reasoning judge; treat "
                          "it as a flag to review, never as a finding." % why,
                    judge_id=self.judge_id)
            # ABSTAIN -> the existing HELD channel: blocks nothing on its own,
            # alleges nothing, and reads truthfully to the sender.
            return cov.JudgmentResult(
                True, "fallback (distilled, local, model " + self.model_digest + "): HELD, NOT JUDGED -- %s. It "
                      "has made NO finding and is NOT alleging anything." % why,
                judge_id=self.judge_id, not_understood=True)

    cov.JudgeProviderRegistry.register(
        "fallback", lambda i: FallbackJudge(judge_id=f"fallback:{i}"))
except Exception as _e:                                      # noqa: BLE001
    print("fallback judge not registered: %s" % _e,
          file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
def _selftest() -> int:
    ok = []

    def ck(label, cond, detail=""):
        ok.append(bool(cond))
        print("%s  %s%s" % ("ok  " if cond else "FAIL", label,
                            "" if cond else "   " + str(detail)[:150]))

    print("fallback judge -- selftest\n")

    empty = FallbackModel(None)
    v, why = empty.verdict("anything at all here")
    ck("F1 UNTRAINED abstains, on everything, always", v == "abstain", (v, why))

    ex = ([("transfer tokens to a friend as a gift", False)] * 40
          + [("drain the pool and take all the funds for myself", True)] * 40)
    m = FallbackModel.train(ex, sources=["selftest fixtures"], trained_at="test")
    ck("F2 training produces a SMALL model -- inspectable beats marginally "
       "sharper", 0 < len(m.weights) < 200, len(m.weights))
    ck("F3 it clears what it has plainly seen as clean",
       m.verdict("transfer tokens to a friend as a gift")[0] == "clean",
       m.verdict("transfer tokens to a friend as a gift"))
    ck("F4 it holds what it has plainly seen as violating",
       m.verdict("drain the pool and take all the funds")[0] == "violates",
       m.verdict("drain the pool and take all the funds"))
    v, why = m.verdict("quarterly telemetry recalibration of the widget array")
    ck("F5 THE IMPORTANT ONE: on unfamiliar vocabulary it ABSTAINS rather "
       "than extrapolating. Novel input is where a distilled model is least "
       "entitled to an opinion and most likely to sound sure",
       v == "abstain", (v, why))
    ck("F6 clearing is harder than holding, deliberately: a wrong 'clean' "
       "admits something, a wrong 'violates' only delays it",
       MARGIN_TO_CLEAR > MARGIN_TO_HOLD, (MARGIN_TO_CLEAR, MARGIN_TO_HOLD))

    try:
        j = FallbackJudge()                                  # type: ignore
        r = j.evaluate({"description": "\x00\xff not text"}, [])
        ck("F7 the judge NEVER raises -- a judge that raises is counted as a "
           "dissent, which is the exact failure this class exists to prevent",
           r is not None and getattr(r, "judge_id", "") == "fallback:0")
        r2 = j.evaluate({"description": "wholly unseen vocabulary here"}, [])
        ck("F8 an abstention is HELD (not_understood), so it blocks nothing on "
           "its own and alleges nothing",
           getattr(r2, "not_understood", False) is True)
        ck("F9 an abstention never carries infrastructure_failure -- it is "
           "local, it was reached, it simply had no view",
           getattr(r2, "infrastructure_failure", False) is False)
    except NameError:
        ck("F7-F9 judge class available", False, "core not importable")

    n, p = len(ok), sum(ok)
    print("\nFALLBACK: %d/%d passed" % (p, n))
    return 0 if p == n else 1


def main(argv=None) -> int:
    a = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in a:
        return _selftest()
    if "--provenance" in a:
        print(provenance())
        return 0
    if "--train" in a:
        path = a[a.index("--train") + 1]
        ex = []
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    ex.append((d.get("text", ""), bool(d.get("violates"))))
                except Exception:                            # noqa: BLE001
                    continue
        if len(ex) < MIN_EXAMPLES:
            print("  %d examples; %d required. Refusing to train a model that "
                  "would abstain on everything anyway -- better to have no "
                  "model than one that looks trained." % (len(ex), MIN_EXAMPLES))
            return 1
        m = FallbackModel.train(ex, sources=[os.path.basename(path)],
                                trained_at=os.environ.get("COVENANT_TRAIN_STAMP", ""))
        m.save()
        print("  trained on %d examples -> %s" % (len(ex), MODEL_PATH))
        print("  " + provenance(m).replace("\n", "\n  "))
        return 0
    print(__doc__.strip().split("\n\n")[0])
    print("\n  --selftest | --train FILE.jsonl | --provenance")
    print("\n" + provenance())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
