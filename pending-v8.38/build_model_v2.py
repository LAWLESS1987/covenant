"""build_model_v2.py -- add a competence declaration to the v1 model.

WHAT IS ADDED, AND WHY EACH ONE IS IN THE HASHED FILE RATHER THAN IN CODE:

  vocab          the 17,388 words the space was actually fitted on, rebuilt
                 from the corpus cache and checked against the count v1 already
                 claims. This is the competence claim itself, so it must be
                 tamper-evident: a vocabulary that can be edited without
                 changing model_id would let anyone widen the judge's claimed
                 competence silently, and widening competence turns ILLEGIBLE
                 into CLEAN. That is the one direction that buys a pass.

  space_script   the script the corpus was in. One string, and the whole basis
                 of the hard test.

  coverage_min   the threshold. FITTED from measurement, not chosen -- see
                 fit_threshold.py, which prints the separation it achieves and
                 the margin it leaves.

  coverage_window  the sliding window size.
  min_foreign_tokens  how many out-of-script tokens make a sentence rather
                 than a name.

Nothing here touches `principles`, `gate_lo` or `veto_at`. The v1 lexicon and
bands are carried through byte-identical, so every one of the 26 checks that
passed against v1 must still pass -- and the suite runs them against this file.
"""
import collections
import json
import os
import pickle
import sys

HERE = os.path.dirname(os.path.abspath(__file__)) or "."
TOKENS = "/home/claude/jlens/tokens.pkl"
MIN_COUNT, VOCAB_CAP = 8, 30000          # v1's build parameters, from its own file


def main():
    v1 = json.load(open(os.path.join(HERE, "model_v1.json"), encoding="utf-8"))
    want = int(v1["space_vocab"])
    build = v1["build"]
    assert build["min_count"] == MIN_COUNT and build["vocab"] == VOCAB_CAP, build

    toks = pickle.load(open(TOKENS, "rb"))
    assert len(toks) == int(v1["space_tokens"]), (
        f"corpus cache has {len(toks)} tokens, model claims {v1['space_tokens']}"
        " -- this is not the corpus the model was fitted on")
    counts = collections.Counter(toks)
    vocab = sorted(w for w, n in counts.most_common(VOCAB_CAP) if n >= MIN_COUNT)
    assert len(vocab) == want, (
        f"rebuilt vocabulary is {len(vocab)}, model claims {want}")
    print(f"corpus {len(toks):,} tokens -> vocabulary {len(vocab):,}  "
          f"(matches the model's own claim)")

    # every lexicon word must be inside the vocabulary it was induced from,
    # or the model is describing a space it did not come from
    V = set(vocab)
    stray = sorted({w for d in v1["principles"].values() for w in d} - V)
    assert not stray, f"lexicon words outside the fitted vocabulary: {stray}"
    print(f"all {sum(len(d) for d in v1['principles'].values())} lexicon words "
          f"are inside it")

    out = dict(v1)
    out["vocab"] = vocab
    out["space_script"] = "Latin"
    out["coverage_window"] = 8
    out["foreign_word_trigger"] = 20

    # ---- the seeded multilingual lexicon --------------------------------
    import lexicon_multi
    seeded, langs = lexicon_multi.build()
    out["seeded_lexicon"] = {p: dict(sorted(d.items()))
                             for p, d in sorted(seeded.items())}
    out["seeded_languages"] = sorted(set(langs[lexicon_multi.STEAL_P]) |
                                     set(langs[lexicon_multi.FALSE_P]))
    out["seeded_verified"] = False
    # stem -> which languages claim it, so a hit can be attributed to a
    # language and that language's own review record consulted
    idx = {}
    for table in (lexicon_multi.STEAL, lexicon_multi.FALSE_WITNESS):
        for lang, stems in table.items():
            for st in stems:
                idx.setdefault(st.lower(), [])
                if lang not in idx[st.lower()]:
                    idx[st.lower()].append(lang)
    out["seeded_index"] = {k: sorted(v) for k, v in sorted(idx.items())}
    out["verified_languages"] = {}      # none yet. Honest, and it shows.
    out["min_reviewers"] = 2
    out["seeded_note"] = (
        "Translations by the author; no native speaker has reviewed any of "
        "them. seeded_verified=false CAPS this lexicon's contribution at "
        "ABSTAIN: it may block a transaction, and may never assert a "
        "VIOLATION. Promotion is a human act by a speaker of the language, it "
        "changes model_id, and it is the only path to a veto from these "
        "entries. Three Latin-script stems (vol, vole, iba) were removed after "
        "collision testing against English and Spanish.")
    # a stem that is also an English vocabulary word would fire on ordinary
    # English, so the build refuses rather than shipping it
    coll = sorted({w for d in out["seeded_lexicon"].values() for w in d} & set(vocab))
    assert not coll, f"seeded stems collide with the English vocabulary: {coll}"
    print(f"seeded lexicon: "
          f"{sum(len(d) for d in out['seeded_lexicon'].values())} stems across "
          f"{len(out['seeded_languages'])} languages, 0 English collisions, "
          f"capped at ABSTAIN")
    out["competence_note"] = (
        "vocab is the competence claim and is hashed with the rest of the "
        "model. It may only ever be extended from a corpus, never from judged "
        "traffic: traffic-fitted vocabulary is a poisoning door, because a "
        "wider vocabulary raises coverage, and higher coverage turns ILLEGIBLE "
        "into CLEAN.")
    out.pop("model_id", None)

    sys.path.insert(0, HERE)
    from covenant_semantic_judge import SemanticModel
    out["model_id"] = SemanticModel._identity(out)
    path = os.path.join(HERE, "semantic_judge_model.json")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, sort_keys=True, indent=1)
        fh.write("\n")
    print(f"model_id {v1['model_id']} -> {out['model_id']}   "
          f"({os.path.getsize(path):,} bytes)")
    print(f"window={out['coverage_window']}  "
          f"foreign_word_trigger={out['foreign_word_trigger']} (tenths of a word)  "
          f"coverage GATES NOTHING (measured: no separation)")


if __name__ == "__main__":
    main()
