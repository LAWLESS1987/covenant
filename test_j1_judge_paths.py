#!/usr/bin/env python3
"""J1 (v8.38): the paths to other judges are real, and the meter can see them.

Three claims were filed against v8.37 after `tools/judge_paths.py` walked the
registry. Measuring them one at a time is how two of the three turned out to be
wrong, which is the reason this file exists as checks and not as prose:

  J1a  JudgeProviderRegistry.register() overwrote a name in silence, so import
       order alone decided which implementation judged the chain.   TRUE.
  J1b  the `semantic` provider was unreachable by default.          TRUE OF THE
       DEPLOYED v8.37 ONLY -- v8.38 registers it at import. The audit measured
       the deployed core and the claim was reported as a design gap. It was a
       deployment gap, already closed by the candidate.
  J1c  quorum_diversity_report keyed on implementation, not model.  FALSE. It
       has keyed on (impl, credential_env, model) since v8.34. The claim came
       from grepping for `.model` and finding none -- the code says f["model"].
       A syntax was counted and a semantics was reported. What IS true, and is
       worse, is J1d.
  J1d  `model` was read from `getattr(j, "model")` -- the CONSTRUCTOR override,
       which is None in every configuration this repo ships. OllamaJudge keeps
       its real model in `_model_override`. So three judges on three models
       reported `<provider default>` three times and counted as ONE.

Runs fully in-process, M13 shape: no key is read or stored, no socket is
opened, no ollama is required, nothing is mined. Where a judge must appear
credentialled its `api_key` is set to the literal string "canned".

Sections
  X  PRE-FIX RECORD. What v8.37 actually did. The X-checks that name the OLD
     behaviour pass on BOTH files; the X-checks that name the fix fail on
     v8.37, which is what makes this a test and not an assertion (M31).
  R  The registry: shadowing is recorded, announced once, opt-outable, and
     idempotent for a module imported twice.
  M  The model a judge will actually send, including when the resolver lies,
     raises, or is absent.
  D  The diversity arithmetic on a real three-model local quorum.
  S  Safety: no credential VALUE anywhere, nothing raises, nothing gates.
  L  LIVE: the actual `local` collision between the two shipped judge modules,
     skipped rather than failed when those modules are not importable.
"""
import os
import sys

os.environ.setdefault("COVENANT_INSECURE_MOCK_JUDGE", "1")
os.environ.setdefault("COVENANT_JUDGE_PROVIDERS", "mock")
os.environ.setdefault("COVENANT_LOCAL_JUDGE_KEY", "local-no-key")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import covenant_unified_v8 as cov  # noqa: E402

REG = cov.JudgeProviderRegistry
HAS_LEDGER = hasattr(REG, "shadowed_providers")
HAS_MODEL_FIX = "model_source" in cov._judge_facts(cov.MockJudge(), set(), set())

PASS = FAIL = SKIP = 0


def check(label, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS: {label}" + (f" -- {detail}" if detail else ""))
    else:
        FAIL += 1
        print(f"  FAIL: {label}" + (f" -- {detail}" if detail else ""))


def skip(label, why):
    global SKIP
    SKIP += 1
    print(f"  SKIP: {label} -- {why}")


class _StubJudge(cov.MockJudge):
    """Shaped like OllamaJudge where it matters: the real model lives in
    `_model_override` and is resolved by `_model()`, NOT in `self.model`."""
    provider = "stub"
    default_model = "stub-default"
    _model_override = None

    def _model(self):
        return self._model_override or self.model or self.default_model


def _quorum(models, cls=_StubJudge):
    js = []
    for i, m in enumerate(models, start=1):
        j = cls(); j.judge_id = f"pc{i}:{i}"; j._model_override = m
        j.api_key = "canned"
        js.append(j)
    q = cov.QuorumJudge(js, semantic_veto_threshold=max(1, len(js) // 2 + 1))
    q.semantic_judge_ids = {j.judge_id for j in js}
    q.required_judge_ids = set()
    return q


# ------------------------------------------------------------------ X ------
def section_x():
    print("== X. PRE-FIX RECORD: what v8.37's judge paths actually did ==")
    # X1 is TRUE ON BOTH FILES: the overwrite still happens. v8.38 changed what
    # is SAID about it, not whether it is allowed -- disclosure, not gating.
    REG.register("j1_x", lambda i: cov.MockJudge())
    first = REG._providers["j1_x"]
    REG.register("j1_x", lambda i: cov.MockJudge())
    check("X1 OLD+NEW: a second register() of the same name still wins",
          REG._providers["j1_x"] is not first,
          "gating this would break the shipped local/ollama import order")

    # X2 names the FIX. It must FAIL on v8.37.
    check("X2 FIX: and the overwrite is now on the record", HAS_LEDGER,
          "JudgeProviderRegistry.shadowed_providers" if HAS_LEDGER
          else "v8.37 has no ledger -- the overwrite left no trace at all")

    # X3 is the defect J1d, stated as the record of the old behaviour.
    j = _StubJudge(); j._model_override = "qwen3:8b"
    old_read = str(getattr(j, "model", None) or "<provider default>")
    check("X3 OLD: the constructor override is empty for a judge configured "
          "the shipped way", old_read == "<provider default>",
          f"getattr(j,'model') -> {old_read!r} while _model() -> {j._model()!r}")

    # X4 names the FIX. It must FAIL on v8.37.
    check("X4 FIX: the report now reads the model the judge will send",
          HAS_MODEL_FIX,
          "_judge_facts carries model_source" if HAS_MODEL_FIX
          else "v8.37 reports the override and calls it the model")

    # X5 is the claim that measurement REFUTED, kept so it cannot be re-filed.
    check("X5 REFUTED: independence has always keyed on model, not impl",
          "model" in cov._judge_facts(cov.MockJudge(), set(), set()),
          "J1c was a grep for '.model' against code that says f[\"model\"]")


# ------------------------------------------------------------------ R ------
def section_r():
    print("== R. The registry records what it shadows ==")
    if not HAS_LEDGER:
        skip("R1-R6 registry ledger", "v8.37 has none; X2 already recorded that")
        return
    before = len(REG.shadowed_providers())
    f1 = lambda i: cov.MockJudge()   # noqa: E731
    f2 = lambda i: cov.MockJudge()   # noqa: E731

    REG.register("j1_r", f1)
    check("R1 a first registration shadows nothing",
          len(REG.shadowed_providers()) == before)

    REG.register("j1_r", f1)
    check("R2 re-registering the SAME factory is not a shadow",
          len(REG.shadowed_providers()) == before,
          "a module imported twice changed nothing")

    REG.register("j1_r", f2)
    led = REG.shadowed_providers()
    check("R3 a different factory for a live name IS recorded",
          len(led) == before + 1)
    rec = led[-1] if led else {}
    check("R4 and the record names both sides by file:line",
          rec.get("name") == "j1_r" and ":" in rec.get("was", "")
          and ":" in rec.get("now", ""),
          f"{rec.get('was')} -> {rec.get('now')}")
    check("R5 an unflagged overwrite is marked not deliberate",
          rec.get("deliberate") == "no")

    REG.register("j1_r", f1, replace=True)
    led2 = REG.shadowed_providers()
    check("R6 replace=True is still recorded -- silent is not unlogged",
          len(led2) == before + 2 and led2[-1].get("deliberate") == "yes")

    led2[-1]["name"] = "tampered"
    check("R7 the ledger handed out is a copy",
          REG.shadowed_providers()[-1].get("name") == "j1_r",
          "an observer must not be able to edit the record it observes")

    ok = True
    for bad in (None, 42, "not-a-callable", object()):
        try:
            REG._origin(bad)
        except Exception as e:            # noqa: BLE001
            ok = False
            print(f"       _origin({bad!r}) raised {type(e).__name__}: {e}")
    check("R8 _origin is total -- a registry that cannot describe itself must "
          "not become one that cannot boot", ok)


# ------------------------------------------------------------------ M ------
def section_m():
    print("== M. The model a judge will actually send ==")
    if not HAS_MODEL_FIX:
        skip("M1-M6 effective model", "v8.37 reads the constructor override; "
                                      "X4 already recorded that")
        return

    j = _StubJudge(); j._model_override = "qwen3:4b"
    f = cov._judge_facts(j, set(), set())
    check("M1 the resolver wins", f["model"] == "qwen3:4b", f["model_source"])
    check("M1b and says where the answer came from",
          f["model_source"] == "resolver")

    j2 = cov.MockJudge()
    f2 = cov._judge_facts(j2, set(), set())
    check("M2 a judge with no model at all still reports one",
          f2["model"] == "<provider default>", f2["model_source"])

    class _Raiser(cov.MockJudge):
        def _model(self):
            raise RuntimeError("endpoint config unreadable")
    f3 = cov._judge_facts(_Raiser(), set(), set())
    check("M3 a resolver that raises does not take the report down",
          isinstance(f3, dict) and "model" in f3)
    check("M3b and the failure is DISCLOSED, not rendered as 'no model'",
          f3["model_source"] == "resolver_raised",
          "'the meter could not read' and 'the judge has no model' are "
          "different claims (M30)")

    class _Empty(cov.MockJudge):
        default_model = "fallback-model"
        def _model(self):
            return ""
    f4 = cov._judge_facts(_Empty(), set(), set())
    check("M4 a resolver that returns nothing falls through to the class default",
          f4["model"] == "fallback-model" and f4["model_source"] == "class_default",
          f"{f4['model']} via {f4['model_source']}")

    class _Plain(cov.MockJudge):
        pass
    p = _Plain(); p.model = "explicit-model"
    f5 = cov._judge_facts(p, set(), set())
    check("M5 an explicit constructor model is still honoured",
          f5["model"] == "explicit-model" and f5["model_source"] == "constructor")

    long = _StubJudge(); long._model_override = "m" * 500
    f6 = cov._judge_facts(long, set(), set())
    check("M6 the field is still bounded", len(f6["model"]) <= 64,
          f"{len(f6['model'])} chars")


# ------------------------------------------------------------------ D ------
def section_d():
    print("== D. The arithmetic on a real three-model local quorum ==")
    # judges.json on the machine this was written for: qwen3:8b / 4b / 1.7b,
    # one implementation, one endpoint, one credential env.
    q = _quorum(["qwen3:8b", "qwen3:4b", "qwen3:1.7b"])
    rep = cov.quorum_diversity_report(q)
    ws = cov.quorum_diversity_warnings(rep)
    n = rep["independent_semantic_judges"]

    if HAS_MODEL_FIX:
        check("D1 three models count as three opinions", n == 3, f"n={n}")
    else:
        check("D1 PRE-FIX RECORD: three models counted as one", n == 1,
              f"n={n} -- this is the defect, recorded")

    check("D2 sharing one parser and one credential is still not diverse",
          rep["diverse"] is False, str(rep["degradations"]))

    said = " ".join(ws)
    if HAS_MODEL_FIX:
        check("D3 the operator is no longer told something false",
              "1 independent semantic judge" not in said)
        check("D4 and is told the true thing instead",
              "share a failure" in said,
              "trading a false warning for silence is M30 in a fix's clothes")
        check("D4b naming what actually falls together",
              "duplicate_implementation:_StubJudge" in said
              or "duplicate_implementation" in said, said[:120])
    else:
        check("D3 PRE-FIX RECORD: the operator was told 1 of 3",
              "1 independent semantic judge" in said, said[:120])

    # A quorum that IS diverse must stay quiet -- a warning that always fires
    # is how an operator learns to skim (M34).
    class _A(cov.MockJudge):
        provider = "a"; default_model = "model-a"
    class _B(cov.MockJudge):
        provider = "b"; default_model = "model-b"
    js = []
    for cls, mid in ((_A, "a:0"), (_B, "b:0")):
        j = cls(); j.judge_id = mid; j.api_key = "canned"; js.append(j)
    q2 = cov.QuorumJudge(js, semantic_veto_threshold=1)
    q2.semantic_judge_ids = {j.judge_id for j in js}
    q2.required_judge_ids = set()
    rep2 = cov.quorum_diversity_report(q2)
    check("D5 a genuinely diverse quorum is diverse", rep2["diverse"] is True,
          str(rep2["degradations"]))
    check("D6 and says nothing at all", cov.quorum_diversity_warnings(rep2) == [],
          str(cov.quorum_diversity_warnings(rep2)))


# ------------------------------------------------------------------ S ------
def section_s():
    print("== S. Safety: no secret, no raise, no gate ==")
    q = _quorum(["qwen3:8b", "qwen3:4b"])
    for j in q.judges:
        j.api_key = "sk-SECRET-DO-NOT-LEAK"
    blob = repr(cov.quorum_diversity_report(q))
    check("S1 the report never carries a credential VALUE",
          "sk-SECRET-DO-NOT-LEAK" not in blob)
    if HAS_LEDGER:
        check("S2 nor does the shadow ledger",
              "sk-SECRET-DO-NOT-LEAK" not in repr(REG.shadowed_providers()))
    else:
        skip("S2 shadow ledger", "v8.37 has none")

    ok = True
    for junk in (None, 0, "judge", [], {}, object()):
        try:
            r = cov.quorum_diversity_report(junk)
            if not isinstance(r, dict):
                ok = False
        except Exception as e:            # noqa: BLE001
            ok = False
            print(f"       report({junk!r}) raised {type(e).__name__}: {e}")
    check("S3 the report never raises, whatever it is handed", ok)

    # The whole surface is disclosure. Nothing in the core may refuse on it.
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "covenant_unified_v8.py"), encoding="utf-8").read()
    bad = [ln.strip() for ln in src.splitlines()
           if "independent_semantic_judges" in ln
           and ("raise " in ln or "return False" in ln)]
    check("S4 no line in the core refuses on the independence count",
          not bad, "; ".join(bad[:2]))


# ------------------------------------------------------------------ L ------
def section_l():
    print("== L. LIVE: the collision between the two shipped judge modules ==")
    try:
        import covenant_judge_local            # noqa: F401
        import covenant_judge_ollama           # noqa: F401
    except Exception as e:                     # noqa: BLE001
        skip("L1-L2 live local/ollama collision", f"not importable here: {e}")
        return
    check("L1 both modules do claim the name 'local'",
          "local" in REG.available_providers())
    if not HAS_LEDGER:
        skip("L2 the collision is on the record", "v8.37 has no ledger")
        return
    hits = [r for r in REG.shadowed_providers() if r["name"] == "local"]
    check("L2 and the collision is on the record with both sides named",
          bool(hits) and "covenant_judge_local" in hits[0]["was"]
          and "covenant_judge_ollama" in hits[0]["now"],
          str(hits[:1]))


def main():
    print(f"source: {cov.COVENANT_VERSION}  {cov.CORE_SOURCE_SHA256[:12]}  "
          f"{cov.CORE_SOURCE_LINES} lines   ledger={HAS_LEDGER} "
          f"model_fix={HAS_MODEL_FIX}")
    section_x()
    section_r()
    section_m()
    section_d()
    section_s()
    section_l()
    print(f"\nJ1: {PASS}/{PASS + FAIL} passed, {SKIP} skipped")
    sys.exit(0 if FAIL == 0 else 1)


if __name__ == "__main__":
    main()
