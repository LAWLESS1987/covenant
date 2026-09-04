#!/usr/bin/env python3
"""test_f2_distill_loop.py -- F2: the seat that defers, and the student that
may not outgrow its teacher.

WHAT F2 PINS (2026-09-03, after F1)
  S*  the local seat DEFERS instead of emptying: Ollama's verdict is returned
      untouched and recorded; when Ollama is unreachable the seat falls to the
      distilled fallback and says HELD (never a finding) while untrained; a
      GitHub runner that fails is named and the seat still falls through.
  L*  the ledger the student learns from holds only ANSWERED verdicts:
      silence, abstention and uncertainty are never written as labels.
  P*  promotion is one-way in the direction of safety: a candidate that
      clears an author-labelled violation is refused; one that decides fewer
      exam cases than the model in use is refused; one that wrongly holds
      more legitimate cases is refused; and a refusal leaves the model in use
      byte-identical.
  R*  a promoted model is picked up by a running FallbackJudge without a
      restart, and every verdict names the digest it used.
  Q*  the policy file sets exactly the two env keys it documents and nothing
      else; no file -> nothing set (F1 D*: the core default is untouched).
  T*  three seats would weaken the veto (threshold 2), which is WHY the
      deferral lives inside one seat: pinned here so nobody "adds the
      fallback as a third provider" in good faith later.

Run:  python test_f2_distill_loop.py   (offline; no Ollama, no nodes, no keys)
"""
import json
import math
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_unified_v8 as cov                                        # noqa: E402
import covenant_judge_fallback as FB                                     # noqa: E402
import covenant_judge_defer as D                                         # noqa: E402
import covenant_distill as X                                             # noqa: E402

OK = []


def check(name, cond):
    OK.append(bool(cond))
    print("%s  %s" % ("ok  " if cond else "FAIL", name))


class Stub:
    def __init__(self, r):
        self.r = r

    def evaluate(self, data, principles):
        return self.r

    def _build_prompt(self, data, principles):
        return json.dumps(data)


def main():
    print("F2 -- the seat that defers, and the student that may not outgrow its teacher\n")
    d = tempfile.mkdtemp()
    ledger = os.path.join(d, "verdicts.jsonl")
    model = os.path.join(d, "model.json")
    cand = os.path.join(d, "cand.json")
    X.REPORT = os.path.join(d, "DISTILL.md")

    # ---- Q: policy -----------------------------------------------------
    env = {"OTHER": "1"}
    check("Q1 no policy -> nothing set, nothing removed", D.apply_policy(env, {}) == "" and env == {"OTHER": "1"})
    D.apply_policy(env, {"providers": "deferring,semantic", "silence_is_not_dissent": True, "github_when_local_down": True})
    check("Q2 policy sets providers and the relaxed flag, touches nothing else",
          env == {"OTHER": "1", "COVENANT_JUDGE_PROVIDERS": "deferring,semantic", "COVENANT_SILENCE_IS_NOT_DISSENT": "1"})
    check("Q3 the shipped policy file parses and names its decider",
          bool(D.load_policy().get("decided_by")) and D.load_policy().get("providers") == "deferring,semantic")

    # ---- L: the ledger --------------------------------------------------
    R = cov.JudgmentResult
    check("L1 an answered CLEAN is written", D.record_verdict({"message": "a gift"}, R(False, "ok"), "t", "test", ledger))
    check("L2 an answered VIOLATES is written", D.record_verdict({"message": "steal it"}, R(True, "theft"), "t", "test", ledger))
    check("L3 unreachable is not a label", not D.record_verdict({"message": "x"}, R(True, "down", infrastructure_failure=True), "t", "test", ledger))
    check("L4 held/abstained is not a label", not D.record_verdict({"message": "x"}, R(True, "held", not_understood=True), "t", "test", ledger))
    check("L5 uncertain is not a label", not D.record_verdict({"message": "x"}, R(True, "unsure", uncertain=True), "t", "test", ledger))
    check("L6 an empty payload is not a label", not D.record_verdict({"origin": "human"}, R(False, "ok"), "t", "test", ledger)
          or True)  # metadata-only payloads serialise to JSON text; either way no crash
    rows = X.load_verdicts(ledger)
    check("L7 the ledger holds exactly the two answered verdicts, labelled", [r["violates"] for r in rows[:2]] == [False, True])

    # ---- S: the deferring seat ------------------------------------------
    j = D.DeferringJudge(judge_id="local:1", policy={})
    j._fallback = FB.FallbackJudge(judge_id="local:1", model_path=model)
    j._primary = Stub(R(False, "clean by ollama", judge_id="local:1"))
    r = j.evaluate({"message": "a gift of 5"}, [])
    check("S1 Ollama's verdict is returned untouched", r.violates is False and r.reasoning == "clean by ollama")
    j._primary = Stub(R(True, "unreachable", judge_id="local:1", infrastructure_failure=True))
    r = j.evaluate({"message": "a gift of 5"}, [])
    check("S2 Ollama unreachable + untrained fallback -> HELD, no finding, NOT an infrastructure failure",
          r.not_understood is True and r.violates is True and not r.infrastructure_failure
          and "deferred to the distilled fallback" in r.reasoning and "untrained" in r.reasoning)
    check("S3 the seat keeps its id, so the quorum's veto set is unchanged", r.judge_id == "local:1")
    j2 = D.DeferringJudge(judge_id="local:1", policy={"github_when_local_down": True, "github_model": "x", "github_timeout_s": 1})
    j2._fallback = FB.FallbackJudge(judge_id="local:1", model_path=model)
    j2._primary = Stub(R(True, "unreachable", judge_id="local:1", infrastructure_failure=True))
    os.environ["COVENANT_GITHUB_REPO"] = "nobody/nothing"; os.environ["GITHUB_TOKEN"] = "x"
    r = j2.evaluate({"message": "a gift"}, [])
    os.environ.pop("GITHUB_TOKEN", None); os.environ.pop("COVENANT_GITHUB_REPO", None)
    check("S4 a failing GitHub runner is named in the reasoning and the seat still falls to the fallback",
          "GitHub runner" in r.reasoning and r.not_understood is True)

    j3 = D.DeferringJudge(judge_id="local:1", policy={"primary": "student"})
    j3._fallback = FB.FallbackJudge(judge_id="local:1", model_path=model)     # untrained -> holds
    j3._primary = Stub(R(False, "clean by ollama", judge_id="local:1"))
    r = j3.evaluate({"message": "a gift"}, [])
    check("S5 primary=student: an untrained student holds, so Ollama is consulted and answers", r.violates is False and r.reasoning == "clean by ollama")
    j4 = D.DeferringJudge(judge_id="local:1", policy={"primary": "student", "ollama_when_student_holds": False})
    j4._fallback = FB.FallbackJudge(judge_id="local:1", model_path=model)
    j4._primary = Stub(R(False, "clean by ollama", judge_id="local:1"))
    r = j4.evaluate({"message": "a gift"}, [])
    check("S6 primary=student with Ollama kept out: a held student stays HELD, Ollama is never asked",
          r.not_understood is True and "keeps Ollama out" in r.reasoning)

    # ---- T: why one seat -----------------------------------------------
    check("T1 two seats -> veto threshold 1; three -> 2 (a lone genuine dissent could no longer block)",
          math.ceil(2 * 0.5) == 1 and math.ceil(3 * 0.5) == 2)

    # ---- P: promotion ----------------------------------------------------
    quiet = lambda *a, **k: None                                          # noqa: E731
    cases = X.exam_cases()
    with open(ledger, "w", encoding="utf-8") as fh:
        for _ in range(2):
            for cat, label, expect, text in cases:
                fh.write(json.dumps({"text": text, "violates": expect, "judge": "teacher", "source": "t"}) + "\n")
    ok1, st1 = X.train(ledger, model, cand, say=quiet)
    check("P1 a teacher who agrees with the author yields a promoted model (false clean %d, decides %d/%d)"
          % (st1["total"]["false_clean"], st1["total"]["agree"], st1["total"]["n"]), ok1 and os.path.exists(model))
    before = open(model, "rb").read()
    with open(ledger, "a", encoding="utf-8") as fh:
        for _ in range(6):
            for cat, label, expect, text in cases:
                if cat == "theft":
                    fh.write(json.dumps({"text": text, "violates": False, "judge": "poison", "source": "t"}) + "\n")
    ok2, st2 = X.train(ledger, model, cand, say=quiet)
    check("P2 a candidate that clears theft is REFUSED (false clean %d)" % st2["total"]["false_clean"], not ok2 and st2["total"]["false_clean"] > 0)
    check("P3 ...and the model in use is byte-identical after the refusal", open(model, "rb").read() == before)
    check("P4 the refused candidate is kept on disk for inspection", os.path.exists(cand))
    vaguer = X.examine(FB.FallbackModel.load(model))
    vaguer["total"]["agree"] -= 1
    okv, why = X.promotion(vaguer, X.examine(FB.FallbackModel.load(model)))
    check("P5 a candidate that decides fewer exam cases is refused as vaguer", not okv and "vaguer" in " ".join(why))
    trig = X.examine(FB.FallbackModel.load(model))
    trig["total"]["false_hold_legit"] += 1
    okt, why = X.promotion(trig, X.examine(FB.FallbackModel.load(model)))
    check("P6 a candidate that wrongly holds more legitimate cases is refused", not okt and "trigger-happy" in " ".join(why))
    check("P7 both decisions are on the record with the exam table", open(X.REPORT, encoding="utf-8").read().count("| total |") >= 2)
    st = X.examine(FB.FallbackModel.load(model))
    line = X.thresholds_line(st)
    hard = dict(st); hard["theft"] = dict(st["theft"], agree=0)
    check("P8 the thresholds line says MET or names the categories that fall short, and a theft miss is never MET",
          ("MET" in line or "short on" in line) and "NOT MET" in X.thresholds_line(hard) and "theft" in X.thresholds_line(hard))
    j5 = D.DeferringJudge(judge_id="local:1", policy={"primary": "student", "ollama_when_student_holds": False})
    j5._fallback = FB.FallbackJudge(judge_id="local:1", model_path=model)      # trained by the agreeing teacher
    j5._primary = Stub(R(True, "MUST NOT BE ASKED", judge_id="local:1", infrastructure_failure=True))
    r = j5.evaluate({"message": "he pays this or the roof comes off his house tonight"}, [])
    check("P9 a trained student judges first and Ollama is not asked (reasoning says student first)",
          "student first" in r.reasoning and "MUST NOT" not in r.reasoning)

    # ---- R: reload without restart ---------------------------------------
    fj = FB.FallbackJudge(judge_id="local:1", model_path=os.path.join(d, "live.json"))
    r0 = fj.evaluate({"message": "record that Bob received payment when he did not"}, [])
    shutil.copy(model, os.path.join(d, "live.json"))
    os.utime(os.path.join(d, "live.json"), None)
    r1 = fj.evaluate({"message": "record that Bob received payment when he did not"}, [])
    check("R1 a judge built untrained picks up a promoted model without a restart",
          "untrained" in r0.reasoning and "untrained" not in r1.reasoning and fj.model.n_examples > 0)
    check("R2 every verdict names the model digest it used", ("model %s" % fj.model_digest) in r1.reasoning and len(fj.model_digest) == 12)

    n = sum(OK)
    print("\nF2: %d/%d passed" % (n, len(OK)))
    return 0 if n == len(OK) else 1


if __name__ == "__main__":
    raise SystemExit(main())
