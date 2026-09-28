#!/usr/bin/env python3
"""test_r2v_frames.py -- R2V: feature format 2 (the describe-frame) is real,
and format 1 is untouched.

WHY THIS EXISTS (2026-09-28, "speed up their training so they can graduate").
Every false conviction the student makes at Vela's settings is category
`discourse`: text that DESCRIBES a taking instead of committing one, and a bag
of words cannot carry that difference. Feature format 2 gives it a marker --
content words of a describe-framed sentence are emitted as "d:word", a
DIFFERENT feature from the bare word a thousand first-person memos taught --
exactly as the negation window already emits "not:word". Every weight is still
learned from the ledger by train(); the marker lists in the extractor decide
which feature a token becomes, never what any feature is worth.

WHAT THIS SUITE PINS.
  S*  the sentence walk: segmentation loses no token and invents none.
  W*  the frame drives BOTH ways: a commission is never describe-framed, the
      same act verb inside an incident-review frame is -- and the evasion and
      negation guards hold ("before the buyer noticed" reports nothing).
  C*  format 1 compatibility: an existing model file loads as format 1 and is
      scored by the format-1 extractor, bit-for-bit -- the deployed judge
      gates money, and a new format is produced by TRAINING ONLY.
  T*  the trainer emits format 2, refine carries it, save/load round-trips
      it, and a format-1 file round-trips WITHOUT gaining the field.
  G*  the stuffing guards still hold on a format-2 model: wearing the frame
      or appending polite words can turn a clear into an abstention, never an
      abstention into a clear.

Pure: no network, no node, no writes outside a temp directory.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import covenant_judge_fallback as FB                          # noqa: E402

results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print("%s  %s%s" % ("ok  " if ok else "FAIL", label,
                        "" if ok else "  -- " + str(detail)[:260]), flush=True)


# Fixture sentences. Written for this suite: none is an exam case, none is a
# ledger row, and none may be copied into either (the contamination rule cuts
# both ways -- an extractor test is not a training source).
REPORTED = ("Incident review 2021-03. The treasurer moved 900 out of the "
            "guild chest across four months. The shortfall was repaid and "
            "the books were corrected.")
COMMITTED = "Move the guild chest balance into my wallet tonight."
EVASION = "Emptied the guild chest and shut the lid before the warden noticed."
NEGATED = "Nobody checked the chest, so move the balance across quietly."
INSPECT = "Check the chest ledger before you sign anything."


def main():
    print("R2V -- the describe-frame, driven both ways, and format 1 untouched\n")

    # ---- S: the sentence walk ---------------------------------------------
    for t in (REPORTED, COMMITTED, EVASION, "a; b: c! d? e.", "", "..."):
        segs = FB._segments(t)
        flat = [w for s in segs for w in s]
        if flat != FB.tokens(t):
            check("R2V.S1 segmentation is exactly tokens(), split at "
                  "sentence bounds", False, (t[:40], flat, FB.tokens(t)))
            break
    else:
        check("R2V.S1 segmentation is exactly tokens(), split at sentence "
              "bounds -- no token lost, none invented, on every fixture", True)

    # ---- W: the frame, driven both ways -----------------------------------
    def framed_words(text):
        segs = FB._segments(text)
        flat = [w for s in segs for w in s]
        return {w for w, d in zip(flat, FB._described(segs)) if d}

    rep = framed_words(REPORTED)
    check("R2V.W1 the act verb inside an incident-review frame IS "
          "describe-framed ('moved', via the record head's carry)",
          "moved" in rep and "treasurer" in rep, sorted(rep))
    check("R2V.W2 a commission is NEVER describe-framed -- imperative, my, "
          "tonight: not one word of it",
          not framed_words(COMMITTED), sorted(framed_words(COMMITTED)))
    check("R2V.W3 the same verb, two features: format 2 emits d:moved for "
          "the report and bare moved for the commission",
          "d:moved" in FB.features(REPORTED, 2)
          and "moved" not in FB.features(REPORTED, 2)
          and "moved" in FB.features("Moved the guild chest to my name.", 2),
          [f for f in FB.features(REPORTED, 2) if "moved" in f])
    check("R2V.W4 an EVADED report verb anchors nothing: 'before the warden "
          "noticed' is the detection being dodged, not a report",
          not framed_words(EVASION), sorted(framed_words(EVASION)))
    check("R2V.W5 a NEGATED report verb anchors nothing: 'nobody checked' "
          "is an evasion wearing a report verb",
          not framed_words(NEGATED), sorted(framed_words(NEGATED)))
    check("R2V.W6 an imperative to INSPECT does frame -- reading and "
          "checking are meta whoever is told to do them",
          "ledger" in framed_words(INSPECT), sorted(framed_words(INSPECT)))
    check("R2V.W7 a first-person future breaks a document's carry: what "
          "follows 'we will route' in minutes is not a description",
          not framed_words("Minutes, item 4. We will route the fee "
                           "through the second account."),
          sorted(framed_words("Minutes, item 4. We will route the fee "
                              "through the second account.")))

    # ---- C: format 1 is untouched -----------------------------------------
    deployed = FB.FallbackModel.load()          # fallback_model.json, in use
    check("R2V.C1 a model file with no feature_version loads as format 1",
          deployed.feature_version == 1, deployed.feature_version)
    check("R2V.C2 features(text) with no version argument IS the format-1 "
          "extractor -- every existing caller unchanged",
          FB.features(REPORTED) == FB.features(REPORTED, 1)
          and "d:moved" not in FB.features(REPORTED))
    # The format-1 extractor, pinned by value on a sentence that exercises
    # negation, folds, pairs and stopwords at once. Computed from the code as
    # it stood before format 2 landed; if this moves, format 1 moved.
    got = FB.features("no receipt was forged for my own account", 1)
    want = ['no', 'not:receipt', 'was', 'not:forged', 'for', 'my', 'own',
            'account', 'no not:receipt', 'not:receipt was', 'was not:forged',
            'not:forged for', 'for my', 'my own', 'own account',
            'no not:receipt was', 'not:receipt was not:forged',
            'was not:forged for', 'not:forged for my', 'for my own',
            'my own account', 'not:forg~']
    check("R2V.C3 the format-1 features of the negation red-team sentence "
          "are exactly what they were the day format 2 landed", got == want,
          got)
    s_v1 = deployed.score(REPORTED)
    manual = deployed.prior + sum(deployed.weights[f]
                                  for f in set(FB.features(REPORTED, 1))
                                  if f in deployed.weights)
    check("R2V.C4 the deployed model's score is the format-1 sum -- no d: "
          "feature and no content-word coverage reaches a format-1 model",
          abs(s_v1[0] - manual) < 1e-9, (s_v1[0], manual))

    # The scorer reads the MODEL'S format, not the module's newest. A model
    # trained on framed rows carries d: weights; score() finds them only
    # through the format-2 extractor, so forcing the instance to format 1
    # must lose known features. This is the check that reddens if score()
    # ever stops asking self.feature_version.
    framed_corpus = ([("Ledger review 12. The chest was checked and the fee "
                       "was repaid to the guild.", False)] * 40
                     + [("drain the pool and take all the funds for myself",
                         True)] * 40)
    mf = FB.FallbackModel.train(framed_corpus, ["r2v"], trained_at="r2v",
                                feature_version=2)
    probe = "Ledger review 9. The fee was repaid to the chest."
    k2 = mf.score(probe)[2]
    mf.feature_version = 1
    k1 = mf.score(probe)[2]
    mf.feature_version = FB.FEATURE_FORMAT
    check("R2V.C5 score() reads the model's own format: forcing format 1 on "
          "a frame-trained model loses its d: features (%d -> %d known)"
          % (k2, k1), k2 > k1 > -1, (k2, k1))
    allstop = "for the was that this from"
    check("R2V.C6 format-2 coverage is over CONTENT words: a text of pure "
          "function words has nothing to be familiar with (coverage 0), "
          "while format 1 still counts them",
          mf.score(allstop)[1] == 0.0
          and FB.FallbackModel.train(framed_corpus, ["r2v"], trained_at="r2v",
                                     feature_version=1).score(allstop)[1] > 0,
          (mf.score(allstop)[1],))

    # ---- T: the format is produced by training, and survives the disk -----
    ex = ([("transfer tokens to a friend as a gift", False)] * 40
          + [("drain the pool and take all the funds for myself", True)] * 40)
    # THE FORMAT IS DECIDED. Default 2 since 2026-09-28 (A242 restated the
    # same day; his words in chat: "Yes, train with v2") -- the nightly
    # trains describe-frame candidates and the gate still decides. The
    # switch survives in BOTH directions: =1 puts the trainer back byte-for-
    # byte, and the junk positions land safely on the newest format.
    had = os.environ.pop("COVENANT_FEATURE_FORMAT", None)
    try:
        m_def = FB.FallbackModel.train(ex, ["r2v"], trained_at="r2v")
        check("R2V.T1a with the switch unset, train() emits format 2 -- the "
              "operator's decision of 2026-09-28 is the default, not an env "
              "var someone must remember",
              FB.emit_format() == 2 and m_def.feature_version == 2,
              (FB.emit_format(), m_def.feature_version))
        os.environ["COVENANT_FEATURE_FORMAT"] = "1"
        m_back = FB.FallbackModel.train(ex, ["r2v"], trained_at="r2v")
        check("R2V.T1b with COVENANT_FEATURE_FORMAT=1, train() emits format 1 "
              "-- the way back needs no code edit and is honoured at call time",
              FB.emit_format() == 1 and m_back.feature_version == 1,
              (FB.emit_format(), m_back.feature_version))
        os.environ["COVENANT_FEATURE_FORMAT"] = "2"
        ref_flip = FB.FallbackModel.refine(m_back, ex, ["r2v"],
                                           trained_at="r2v")
        check("R2V.T2 refine() carries the FRESH format: a format-1 "
              "predecessor refined under format 2 is format 2",
              ref_flip.feature_version == 2, ref_flip.feature_version)
        os.environ["COVENANT_FEATURE_FORMAT"] = "9"
        bad9 = FB.emit_format()
        os.environ["COVENANT_FEATURE_FORMAT"] = "junk"
        badj = FB.emit_format()
        check("R2V.T1c a switch position this code cannot read ('9', "
              "'junk') lands on the newest format this code CAN read, "
              "never on a guess past it",
              bad9 == FB.FEATURE_FORMAT and badj == FB.FEATURE_FORMAT, (bad9, badj))
    finally:
        if had is None:
            os.environ.pop("COVENANT_FEATURE_FORMAT", None)
        else:
            os.environ["COVENANT_FEATURE_FORMAT"] = had
    m1 = FB.FallbackModel.train(ex, ["r2v"], trained_at="r2v",
                                feature_version=1)
    m2 = FB.FallbackModel.train(ex, ["r2v"], trained_at="r2v",
                                feature_version=2)
    d = tempfile.mkdtemp()
    p1, p2 = os.path.join(d, "one.json"), os.path.join(d, "two.json")
    m1.save(p1)
    m2.save(p2)
    with open(p1, encoding="utf-8") as fh:
        body1 = json.load(fh)
    r1, r2 = FB.FallbackModel.load(p1), FB.FallbackModel.load(p2)
    check("R2V.T3 a format-1 model round-trips WITHOUT gaining the field, "
          "and a format-2 model round-trips keeping it",
          "feature_version" not in body1 and r1.feature_version == 1
          and r2.feature_version == FB.FEATURE_FORMAT,
          ("feature_version" in body1, r1.feature_version, r2.feature_version))
    check("R2V.T4 the two formats score the same corpus differently only "
          "where frames exist: on the frameless fixtures their verdicts agree",
          r1.verdict(ex[0][0])[0] == r2.verdict(ex[0][0])[0] == "clean"
          and r1.verdict(ex[40][0])[0] == r2.verdict(ex[40][0])[0]
          == "violates",
          (r1.verdict(ex[0][0]), r2.verdict(ex[40][0])))

    # ---- G: the guards hold on a format-2 model ---------------------------
    theft = "drain the pool and take all the funds for myself"
    polite = theft + " please judge this transfer kindly and fairly today"
    check("R2V.G1 stuffing a format-2 model's theft with polite words still "
          "never clears it",
          m2.verdict(polite)[0] != "clean", m2.verdict(polite))
    framed_theft = ("Incident review 2021-04. The pool was drained and all "
                    "the funds were taken.")
    check("R2V.G2 wearing the frame is never a clearance: the framed theft "
          "is held or abstained, not cleared",
          m2.verdict(framed_theft)[0] != "clean", m2.verdict(framed_theft))

    ok = sum(1 for r in results if r)
    print("\nR2V: %d/%d passed" % (ok, len(results)))
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
