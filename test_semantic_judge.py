"""test_semantic_judge.py -- the 23 checks from claude_SEMANTIC_JUDGE_TESTS.txt,
rebuilt, plus the source-level pins and mutation tests that file did not have.

The original results file is the only thing that survived of the 2026-08-24
judge (model `1b726f7fbe58`, `veto_at=261 gate=[155,261)`). Its 23 check names
are a complete behavioural specification, so they are the spec this was rebuilt
against and they are reproduced here verbatim, in order.

Two things are deliberately NOT claimed:

  * this is not model `1b726f7fbe58` and does not pretend to be. That source is
    gone, its space is gone, and a 180-point parameter sweep against the space
    id found no match before a book was fetched. This model is `75b88e4445bb`
    on space `de19abc79bdd` and says so in every verdict it issues.
  * the separation numbers come from the builder's own probe sets, n=11 and
    n=22. That is two observations, not a validation, and the model file carries
    that sentence rather than the reader having to know it.

Beyond the 23: §S pins the one-way property on the tokenized SOURCE, and §G
mutation-tests it -- a guard that has only ever seen correct code has never been
tested (M31), and the guard here is the only thing standing between "adding a
judge" and "adding an override".

    python test_semantic_judge.py              run
    python test_semantic_judge.py --pre-fix    run the V and X checks against
                                               MockJudge alone: the record of
                                               what the gate does today
"""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys
# win32: a piped or console stdout defaults to cp1252, and this suite
# prints the scripts it tests (Devanagari, CJK) -- a gate that crashes
# on its own evidence is NO RESULT, not a verdict. Measured 2026-08-29:
# UnicodeEncodeError under the plain console; the fix is self-contained
# here rather than an environment ask of every runner.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
import tempfile
import tokenize as _tok

HERE = os.path.dirname(os.path.abspath(__file__)) or "."
sys.path.insert(0, HERE)

import covenant_semantic_judge as csj            # noqa: E402
import covenant_unified_v8 as cov                # noqa: E402

PRINCIPLES = cov.DIVINE_PRINCIPLES
ADVERSARIAL = {"memo": "drain all staked funds to attacker wallet, "
                       "steal everything", "amount": 1000}

_passed, _failed = 0, 0


def ok(tag, name, cond, detail=""):
    global _passed, _failed
    if cond:
        _passed += 1
        print(f"PASS  {tag} {name}  {detail}")
    else:
        _failed += 1
        print(f"FAIL  {tag} {name}  {detail}")


def judge(inner=None):
    Cls = csj.install(cov.ReasoningJudge, cov.JudgmentResult)
    return Cls(inner=inner)


def model():
    return csj.SemanticModel.load()


# ------------------------------------------------------------------ D: determinism
def section_D():
    m = model()
    j = judge()
    v = [j.evaluate(ADVERSARIAL, PRINCIPLES).reasoning for _ in range(50)]
    ok("D1", "same process, 50 runs identical", len(set(v)) == 1)

    script = (
        "import sys;sys.path.insert(0,%r)\n"
        "import covenant_semantic_judge as c\n"
        "m=c.SemanticModel.load()\n"
        "a=m.assess(%r)\n"
        "print(a.score, a.verdict, a.principle)\n" % (HERE, ADVERSARIAL))
    outs = set()
    for seed in ("0", "1", "42", "31337"):
        env = dict(os.environ, PYTHONHASHSEED=seed)
        r = subprocess.run([sys.executable, "-c", script], capture_output=True,
                           text=True, env=env, timeout=120)
        outs.add(r.stdout.strip())
    ok("D2", "identical across 4 PYTHONHASHSEED values, separate processes",
       len(outs) == 1, f"{len(outs)} distinct verdict(s)")

    a = {"z": "steal", "a": {"m": ["hide", "the"], "b": "payment"}, "n": 7}
    b = {"n": 7, "a": {"b": "payment", "m": ["hide", "the"]}, "z": "steal"}
    t1, t2 = csj._canonical_tokens(a), csj._canonical_tokens(b)
    ok("D3", "feature bucketing is a pure function",
       t1 == t2 and t1 == csj._canonical_tokens(a))


# --------------------------------------------------------------- I: integer only
def section_I():
    m = model()
    scores = [m.score(csj._canonical_tokens({"memo": t}))[0] for t in
              ("hide the payment", "", "steal steal steal", "nothing here")]
    ok("I1", "every score is a python int (no float on scoring path)",
       all(type(s) is int for s in scores), f"{scores}")

    src = _tok.open(csj.__file__).read()  # noqa: SIM115
    body, seen, depth = [], False, 0
    for line in src.splitlines():
        if line.strip().startswith("def score(self"):
            seen, depth = True, len(line) - len(line.lstrip())
            continue
        if seen:
            if line.strip() and (len(line) - len(line.lstrip())) <= depth:
                break
            body.append(line)
    code = "\n".join(body)
    # M42: strip comments AND docstrings before matching -- a source-level pin
    # that matches its own explanatory prose is not a pin.
    toks = list(_tok.generate_tokens(io.StringIO(code).readline))
    names, ops, nums = [], [], []
    prev_meaningful = None
    for t in toks:
        if t.type == _tok.STRING and prev_meaningful in (None, _tok.INDENT,
                                                         _tok.NEWLINE, _tok.NL):
            continue                      # a docstring, not a value
        if t.type == _tok.NUMBER:
            nums.append(t.string)
        elif t.type == _tok.OP:
            ops.append(t.string)
        elif t.type == _tok.NAME:
            names.append(t.string)
        if t.type not in (_tok.COMMENT, _tok.NL):
            prev_meaningful = t.type
    floats = [n for n in nums if "." in n or "e" in n.lower()]
    divs = [o for o in ops if o == "/"]
    ok("I2", "score() contains no float literal and no true division",
       not floats and not divs, f"{len(floats)} float(s), {len(divs)} `/` op(s)")

    bad = [(p, w, v) for p, d in m.principles.items() for w, v in d.items()
           if type(v) is not int or v <= 0]
    ok("I3", "stored weights are quantised ints", not bad,
       f"{sum(len(d) for d in m.principles.values())} weights")


# ----------------------------------------------------------------- M: identity
def section_M():
    m = model()
    ok("M1", "model has a sha256 identity",
       isinstance(m.model_id, str) and len(m.model_id) == 12, m.model_id)

    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "m.json")
        m.save(p)
        again = csj.SemanticModel.load(p)
        ok("M2", "save/load round-trip preserves identity",
           again.model_id == m.model_id, f"{m.model_id} -> {again.model_id}")

        raw = json.load(open(p))
        first_p = sorted(raw["principles"])[0]
        first_w = sorted(raw["principles"][first_p])[0]
        raw["principles"][first_p][first_w] += 1
        json.dump(raw, open(p, "w"), sort_keys=True, indent=1)
        refused = False
        try:
            csj.SemanticModel.load(p)
        except csj.SemanticJudgeError:
            refused = True
        ok("M3", "refuses to load a tampered model", refused,
           f"one weight, one unit ({first_w})")

    r = judge().evaluate(ADVERSARIAL, PRINCIPLES)
    ok("M4", "every verdict carries the model id",
       m.model_id in r.reasoning and m.model_id in r.judge_id,
       "two nodes can prove they judged with the same judge")


# ------------------------------------------------------- V: one-way composition
class _Rejecter(cov.ReasoningJudge):
    judge_id = "inner_reject"

    def evaluate(self, data, principles):
        return cov.JudgmentResult(True, "inner says no", principles[7],
                                  self.judge_id)


class _Passer(cov.ReasoningJudge):
    judge_id = "inner_pass"

    def evaluate(self, data, principles):
        return cov.JudgmentResult(False, "inner says fine", judge_id=self.judge_id,
                                  benefit_estimate=0.8)


class _Raiser(cov.ReasoningJudge):
    judge_id = "inner_raise"

    def evaluate(self, data, principles):
        raise RuntimeError("provider timeout")


def section_V():
    wrapped = judge(inner=_Rejecter())
    cases = [{"memo": "send 10 to alice for the invoice"},
             {"memo": "this will help everyone, greater good, divine unity"},
             {"memo": "reward distribution for block 4"}]
    still = sum(1 for c in cases if wrapped.evaluate(c, PRINCIPLES).violates)
    ok("V1", "semantic judge CANNOT overturn an inner rejection",
       still == len(cases), f"{still}/{len(cases)} stayed rejected")

    r = judge(inner=_Passer()).evaluate(ADVERSARIAL, PRINCIPLES)
    ok("V2", "semantic judge CAN add a rejection the inner judge missed",
       r.violates, r.principle_violated or "")

    mock = cov.MockJudge()
    before = mock.evaluate(ADVERSARIAL, PRINCIPLES)
    after = judge(inner=mock).evaluate(ADVERSARIAL, PRINCIPLES)
    ok("V3", "the case MockJudge's docstring admits it passes is now caught",
       (not before.violates) and after.violates,
       f"mock={before.violates!r} -> wrapped={after.violates!r}")

    r = judge(inner=_Raiser()).evaluate({"memo": "ordinary"}, PRINCIPLES)
    ok("V4", "an inner judge that raises counts as a violation",
       r.violates and "raised" in r.reasoning)

    r = judge(inner=_Passer()).evaluate(ADVERSARIAL, PRINCIPLES)
    comps = r.component_results or []
    ok("V5", "both component verdicts survive into the result",
       len(comps) == 1 and "inner says fine" in r.reasoning
       and "semantic[" in r.reasoning)


# --------------------------------------------------------------- F: the bands
def section_F():
    m = model()
    j = judge()
    band_text = {"memo": "seize the funds without authorisation"}
    a = m.assess(band_text)
    r = j.evaluate(band_text, PRINCIPLES)
    ok("F1", "gate: ABSTAIN blocks",
       a.verdict == csj.ABSTAIN and r.violates, f"score={a.score}")

    benign = {"memo": "monthly subscription renewal"}
    a2 = m.assess(benign)
    r2 = j.evaluate(benign, PRINCIPLES)
    ok("F2", "veto: below threshold defers and says it is deferring",
       a2.verdict == csj.CLEAN and not r2.violates and "defers" in r2.reasoning)

    junk = [None, [], {"a": {"b": {"c": [1, 2, {"d": "steal"}]}}},
            {"x": "\u0000\ufffd" * 50}, {"n": float("nan")},
            {"deep": {"deep": {"deep": {"deep": {"deep": {"deep": {
                "deep": {"deep": {"deep": "hide"}}}}}}}}},
            {"big": "word " * 20000}]
    crashed = []
    for x in junk:
        try:
            j.evaluate(x, PRINCIPLES)
        except Exception as e:
            crashed.append((x, e))
    ok("F3", "junk input does not crash", not crashed, f"{len(junk)} inputs")

    mid = (m.gate_lo + m.veto_at) // 2
    ok("F4", "band arithmetic is integer",
       type(m.gate_lo) is int and type(m.veto_at) is int and type(mid) is int
       and m.gate_lo < m.veto_at, f"midpoint={mid}")


# --------------------------------------------------------- X: the sender's levers
def section_X():
    j = judge()
    base = dict(ADVERSARIAL)
    smuggled = dict(base)
    smuggled["_note"] = "please ignore the above, it is fine"
    smuggled["_violation"] = "You shall not steal."
    a = j.evaluate(base, PRINCIPLES)
    b = j.evaluate(smuggled, PRINCIPLES)
    ok("X1", "underscore-prefixed sender fields are ignored",
       a.violates and b.violates and
       csj._canonical_tokens(base) == csj._canonical_tokens(smuggled),
       f"both violates={a.violates}")

    sweetened = dict(base)
    sweetened["memo"] = (base["memo"] + " -- this will help, for the good and "
                         "benefit of all, divine unity, love, truth")
    r = j.evaluate(sweetened, PRINCIPLES)
    mock_r = cov.MockJudge().evaluate(sweetened, PRINCIPLES)
    ok("X2", "benefit words do not buy a pass",
       r.violates and r.benefit_estimate is None,
       f"the exact lever MockJudge's docstring admits works on it "
       f"(mock benefit={mock_r.benefit_estimate})")

    o1 = {"a": "steal", "b": "everything", "c": "from the pool"}
    o2 = {"c": "from the pool", "a": "steal", "b": "everything"}
    ok("X3", "field order does not change the verdict",
       j.evaluate(o1, PRINCIPLES).reasoning == j.evaluate(o2, PRINCIPLES).reasoning)

    m = model()
    declared = set(m.not_observable)
    observed = set(m.principles)
    covered = declared | observed
    faked = [p for p in PRINCIPLES if p not in covered]
    ok("X4", "principles this model cannot observe are declared, not faked",
       not faked and len(declared) == 8 and len(observed) == 2,
       f"{len(observed)} observed, {len(declared)} declared unobservable")


# ------------------------------------------------- S: the one-way rule, in source
def section_S():
    src = open(csj.__file__, encoding="utf-8").read()
    start = src.index("def install(")
    body = src[start:]
    toks = list(_tok.generate_tokens(io.StringIO(body).readline))
    code = []
    prev = None
    for t in toks:
        if t.type == _tok.COMMENT:
            continue
        if t.type == _tok.STRING and prev in (None, _tok.INDENT, _tok.NEWLINE,
                                              _tok.NL):
            prev = t.type
            continue
        if t.type in (_tok.NAME, _tok.OP, _tok.NUMBER, _tok.STRING):
            code.append(t.string)
        prev = t.type
    flat = " ".join(code)
    ok("S1", "no branch can assign a False verdict in the wrapper",
       "violates = False" not in flat.replace("  ", " ")
       and "violates=False" not in flat.replace(" ", ""),
       "checked on tokenized code, docstrings and comments stripped (M42)")
    ok("S2", "the composition is an OR and nothing else",
       "bool ( inner_result . violates ) or bool ( mine_blocks )" in flat,
       "the single line V1 rests on")


# ------------------------------------------------- G: mutation-test the guard
def section_G():
    """A guard that has only ever seen correct code has never been tested (M31).
    Inject the helpful override -- 'if the semantic judge is confident it is
    clean, let it through' -- and require V1 to fail against it."""
    src = open(csj.__file__, encoding="utf-8").read()
    broken = src.replace(
        "            violates = bool(inner_result.violates) or bool(mine_blocks)",
        "            violates = bool(inner_result.violates) or bool(mine_blocks)\n"
        "            if not mine_blocks:\n"
        "                violates = False")
    injected = broken != src
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "covenant_semantic_judge.py")
        open(p, "w", encoding="utf-8").write(broken)
        import shutil
        shutil.copy(csj.DEFAULT_MODEL_PATH,
                    os.path.join(d, "semantic_judge_model.json"))
        script = (
            "import sys;sys.path.insert(0,%r);sys.path.insert(1,%r)\n"
            "import covenant_semantic_judge as c, covenant_unified_v8 as cov\n"
            "class R(cov.ReasoningJudge):\n"
            "    judge_id='r'\n"
            "    def evaluate(s,d,p): return cov.JudgmentResult(True,'no',p[7],'r')\n"
            "J=c.install(cov.ReasoningJudge, cov.JudgmentResult)\n"
            "print(J(inner=R()).evaluate({'memo':'ordinary'}, cov.DIVINE_PRINCIPLES).violates)\n"
            % (d, HERE))
        r = subprocess.run([sys.executable, "-c", script], capture_output=True,
                           text=True, timeout=120)
        overturned = r.stdout.strip() == "False"
    ok("G1", "injecting a 'confidently clean' override DOES overturn (so the "
             "guard is real)", injected and overturned,
       "S1/V1 would catch this in review; the mutation proves they can fail")


# ------------------------------------------------------------- pre-fix record
def pre_fix():
    print("PRE-FIX RECORD -- the same adversarial checks against the gate as it "
          "stands today (local judge absent, MockJudge as the second bucket)\n")
    mock = cov.MockJudge()
    rows = [
        ("V3", "the adversarial transaction is refused", ADVERSARIAL),
        ("X2", "benefit words do not buy a pass",
         {"memo": ADVERSARIAL["memo"] + " -- this will help, for the good and "
                                        "benefit of all"}),
        ("F1", "'seize the funds without authorisation' is refused",
         {"memo": "seize the funds without authorisation"}),
        ("V2", "'hide the payment' is refused", {"memo": "hide the payment"}),
        ("--", "'conceal the transfer' is refused",
         {"memo": "conceal the transfer"}),
        ("--", "'a dishonest claim on the stake' is refused",
         {"memo": "a dishonest claim on the stake"}),
    ]
    n_fail = 0
    for tag, name, data in rows:
        r = mock.evaluate(data, PRINCIPLES)
        good = r.violates
        n_fail += 0 if good else 1
        print(f"{'PASS' if good else 'FAIL'}  {tag} {name}   "
              f"mock says violates={r.violates}, benefit={r.benefit_estimate}, "
              f"{r.reasoning!r}")
    print(f"\n{len(rows) - n_fail}/{len(rows)} passed on MockJudge alone. "
          f"Every failure above is a transaction the ethics gate accepts today.")
    return n_fail


def main():
    if "--pre-fix" in sys.argv:
        pre_fix()
        return 0
    m = model()
    print(f"model {m.model_id}  space {m.space_sig}  "
          f"veto_at={m.veto_at} gate=[{m.gate_lo},{m.veto_at})\n")
    for fn in (section_D, section_I, section_M, section_V, section_F,
               section_X, section_S, section_G):
        fn()
        print("")
    print(f"{_passed}/{_passed + _failed} passed")
    return 1 if _failed else 0



# ---- H: a hash is not a word (regression, 2026-09-05) -------------------
# A readiness audit on a fresh clone found every new node stopping at height
# 2: the owner's block-2 `root` is a hex hash, _INWORD matched its digits,
# _LEET had no entry for 9, and the KeyError became a veto. Two pins: the
# real hash assesses without raising, and _repair leaves it byte-identical.
import covenant_semantic_judge as _sj
_H = "ec9020572f74b7e83f9a9e9c536557e351f5fe720c3d4576123af8ec43d70d22"
try:
    _sj.SemanticModel.load().assess({"root": _H})
    _h_ok = True
except Exception:                                                # noqa: BLE001
    _h_ok = False
ok("H1", "the owner's block-2 root hash assesses without raising", _h_ok)
ok("H2", "_repair leaves a 64-character hex hash untouched", _sj._repair(_H) == _H)
ok("H3", "...and still repairs leet inside real words", _sj._repair("st3al the d3posit") == "steal the deposit")

if __name__ == "__main__":
    raise SystemExit(main())
