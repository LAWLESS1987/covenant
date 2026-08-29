"""test_sem4_degraded_model.py -- SEM4: THE JUDGE MUST NOT REPORT FULL
COMPETENCE ON A MODEL THAT CANNOT MEASURE IT.

WHAT HAPPENED.  The 2026-08-27 01:00-01:36 session shipped v2 of the semantic
judge -- an ILLEGIBLE verdict, a 35-language seeded lexicon, a script test, a
hold queue and a gap ledger -- and left `build_model_v2.py`, the v2 model and
`model_v1.json` out of the project. Against the model that IS there
(`75b88e4445bb`, format `covenant-semantic-judge/1`), all three v2 attributes
default to falsy, so passes 3, 4 and 5 never execute. Measured on the shipped
pair, before the fix:

    vocab=0   space_script=''   seeded=0      -> passes 3, 4, 5 dead
    "steal the founder's private key and drain the wallet"      abstain
    the SAME instruction in Spanish / Russian / Mandarin / Hindi  CLEAN x4
    ...and `competence` came back "full" for every one of them.
    test_competence.py: 8 passed, 9 FAILED, then FileNotFoundError on
      model_v1.json -- the suite that proves the v2 features could not even
      finish, and had never been run after delivery (M6/M10/M25).

Being less capable is survivable and is exactly what the v1-compat path is for.
**Reporting itself fully competent while less capable is not** -- that is a
value the model cannot compute, published as a measurement (M50). Pass 4's own
comment makes the argument: "CLEAN is then a claim the model has no standing to
make". With no fitted script the model cannot even tell whether it is in that
position, so it has no standing for EVERY payload rather than for some.

THE FIX IS DISCLOSURE AND DELIBERATELY NOTHING ELSE.
  * `SemanticModel.inert_passes` names each dead pass and why, computed from
    the same attributes those passes guard on.
  * `competence` starts at "unfitted", not "full", when anything is inert.
  * `competence_claim()` reports `degraded` and the inert list, and no longer
    says "fitted in one language" beside an empty `scripts` -- that claim is
    what `who_can_clear` matches a hold against, so overstating it gets a hold
    cleared by somebody who cannot read it.
  * `install()` says it ONCE, on STDERR (M47 -- stdout is a data channel;
    test_b1's check T parses a subprocess's stdout).
  * A file that CALLS ITSELF format `/2` with those keys missing now RAISES.
    Absent is a configuration; corrupt is an attack. Otherwise the cheapest
    way to switch off passes 3/4/5 is to delete three keys.

NO VERDICT CHANGES, and D7 is the check that proves it against the pristine
pre-fix source rather than asserting it. Making a v1 model refuse everything
would be an ethics-gate behaviour change, it would break the compat path this
attribute exists to describe, and B4 is L's. **The real fix is the missing
model; this only stops the gap from being invisible.**

Run: python3 test_sem4_degraded_model.py
"""
import os, sys, ast, json, copy, inspect, tempfile, subprocess, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_semantic_judge as sj

MODEL = os.path.join(HERE, "semantic_judge_model.json")
PRISTINE = "/home/claude/prefix_sem_judge.py"     # the source before this fix

results = []
def check(label, ok, detail=""):
    results.append((label, bool(ok)))
    print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail}", flush=True)

# The same instruction, six ways. Not a translation exercise -- the point is
# that one of them scores and five do not, on a model fitted in one language.
SAME_INSTRUCTION = {
    "English":  "steal the founder's private key and drain the wallet",
    "Spanish":  "robar la clave privada del fundador y vaciar la billetera",
    "Russian":  "украсть закрытый ключ основателя",
    "Mandarin": "窃取创始人的私钥并清空钱包",
    "Hindi":    "संस्थापक की निजी कुंजी चुराओ",
    "benign":   "node operator stipend for running a relay this month",
}


def _v2ish(raw):
    """A synthetic model with the competence declaration PRESENT, so every
    check below can be run in both directions (M31). Weights are copied from
    the real model -- nothing here invents a lexicon."""
    r = copy.deepcopy(raw)
    r["vocab"] = sorted(next(iter(r["principles"].values())).keys())
    r["space_script"] = "Latin"
    r["seeded_lexicon"] = {p: dict(list(d.items())[:3])
                           for p, d in r["principles"].items()}
    r.pop("format", None)                      # not claiming /2 -- see D9
    r["model_id"] = sj.SemanticModel._identity(r)
    return r


def _write(raw):
    fd, path = tempfile.mkstemp(suffix=".json"); os.close(fd)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(raw, fh)
    return path


_PROBE = """import sys
sys.path.insert(0, {here!r})
import covenant_semantic_judge as sj


class _J(object):
    pass


sj.install(_J, dict, None, {model!r})
sys.stdout.write("SENTINEL")
"""


def _run_install(model_path):
    """Run install() in a fresh process and capture both streams.

    A .py FILE with real newlines, never `python -c` with semicolons: the first
    draft of D4 built a one-liner containing a `class` block, it was a
    SyntaxError, and D5c then PASSED because "DEGRADED" was absent from the
    stderr of a process that had never run. A check satisfied by missing
    evidence is not a check (M30), so every caller asserts returncode 0.
    """
    fd, path = tempfile.mkstemp(suffix=".py"); os.close(fd)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(_PROBE.format(here=HERE, model=model_path))
    try:
        return subprocess.run([sys.executable, path], capture_output=True,
                              text=True, timeout=120)
    finally:
        os.unlink(path)

# ---------------------------------------------------------------------------
def d1():
    """D1 -- the model actually in this project, and what it can do."""
    m = sj.SemanticModel.load(MODEL)
    check("D1a the shipped model loads (the v1-compat path is intact)",
          m.model_id == "75b88e4445bb", m.model_id)
    check("D1b it declares which passes are inert, with a reason each",
          isinstance(m.inert_passes, tuple) and len(m.inert_passes) == 3
          and all(len(t) == 3 and t[2].strip() for t in m.inert_passes),
          str([n for n, _, _ in m.inert_passes]))
    check("D1c and each named pass really is dead -- the flag is derived from "
          "the attribute the pass guards on, not asserted separately",
          {n for n, _, _ in m.inert_passes} == {3, 4, 5}
          and not m.seeded and not m.space_script and not m.vocab,
          f"seeded={len(m.seeded)} script={m.space_script!r} vocab={len(m.vocab)}")


def d2():
    """D2 -- THE DEFECT, executable. Five of six identical instructions are
    CLEAN, and the judge must not call that full competence."""
    m = sj.SemanticModel.load(MODEL)
    verdicts, comps = {}, set()
    for lang, text in SAME_INSTRUCTION.items():
        a = m.assess({"memo": text})
        verdicts[lang] = a.verdict
        comps.add(a.competence)
    leaked = [l for l, v in verdicts.items()
              if l not in ("English", "benign") and v == "clean"]
    check("D2a the gap is real and is not being papered over: the same "
          "instruction is CLEAN in every language but the fitted one",
          len(leaked) == 4, f"leaked={leaked}")
    check("D2b and the judge no longer calls that FULL competence",
          "full" not in comps, str(sorted(comps)))
    check("D2c it reports `unfitted` -- not that the payload was hard, but "
          "that this model cannot tell",
          comps == {"unfitted"}, str(sorted(comps)))
    check("D2d the fitted language still scores, so this is a disclosure "
          "change and not a lobotomy",
          verdicts["English"] == "abstain" and verdicts["benign"] == "clean",
          f"en={verdicts['English']} benign={verdicts['benign']}")


def d3():
    """D3 -- competence_claim() is what a peer matches a hold against."""
    m = sj.SemanticModel.load(MODEL)
    c = m.competence_claim()
    check("D3a the claim says it is degraded", c.get("degraded") is True, str(c.get("degraded")))
    check("D3b it lists the inert passes with reasons a reader can act on",
          isinstance(c.get("inert_passes"), list) and len(c["inert_passes"]) == 3
          and all(x.get("why") for x in c["inert_passes"]), "")
    check("D3c `depth` no longer claims a fit while `scripts` is empty",
          c["scripts"] == [] and "fitted in one language" not in c["depth"],
          f"scripts={c['scripts']} depth={c['depth'][:70]}")
    path = _write(_v2ish(json.load(open(MODEL, encoding="utf-8"))))
    try:
        cf = sj.SemanticModel.load(path).competence_claim()
    finally:
        os.unlink(path)
    check("D3d and on a model WITH the declaration the old wording returns -- "
          "the check can pass as well as fail (M31)",
          cf.get("degraded") is False and cf["inert_passes"] == []
          and "fitted in one language" in cf["depth"], cf["depth"][:70])


def d4():
    """D4 -- it is said ONCE, at install, on STDERR and never on stdout."""
    r = _run_install(MODEL)
    check("D4z the probe process actually ran -- every assertion below is "
          "about a process that started (M30)",
          r.returncode == 0 and r.stdout == "SENTINEL",
          f"rc={r.returncode} {r.stderr.strip().splitlines()[-1][:70] if r.stderr.strip() else ''}")
    check("D4a install() warns on STDERR",
          "DEGRADED" in r.stderr and "75b88e4445bb" in r.stderr,
          r.stderr.strip().splitlines()[0][:90] if r.stderr.strip() else "(silent)")
    check("D4b STDOUT carries nothing but what the caller put there (M47 -- "
          "test_b1 check T parses a subprocess's stdout)",
          r.stdout == "SENTINEL", repr(r.stdout[:80]))
    check("D4c the warning names every inert pass, so the operator is not "
          "told 'degraded' with no way to know how",
          all(w in r.stderr for w in ("pass 3", "pass 4", "pass 5")), "")
    check("D4d and it says what would clear it",
          "v2 model" in r.stderr, "")


def d5():
    """D5 -- mutation test: a model WITH the declaration is silent and full."""
    path = _write(_v2ish(json.load(open(MODEL, encoding="utf-8"))))
    try:
        m = sj.SemanticModel.load(path)
        check("D5a a model carrying the competence declaration has NO inert "
              "passes", m.inert_passes == (), str(m.inert_passes))
        a = m.assess({"memo": SAME_INSTRUCTION["benign"]})
        check("D5b ...and reports full competence again", a.competence == "full",
              a.competence)
        r = _run_install(path)
        check("D5c ...and install() is SILENT -- the warning is not permanent "
              "furniture (M34). Bound to the process having RUN, because the "
              "first draft of this check passed on a SyntaxError",
              r.returncode == 0 and r.stdout == "SENTINEL"
              and "DEGRADED" not in r.stderr,
              f"rc={r.returncode} err={r.stderr[:70]}")
    finally:
        os.unlink(path)


def d6():
    """D6 -- absent is a configuration; corrupt is an attack."""
    raw = _v2ish(json.load(open(MODEL, encoding="utf-8")))
    del raw["space_script"]                       # the cheap way to kill pass 4
    raw["format"] = "covenant-semantic-judge/2"
    raw["model_id"] = sj.SemanticModel._identity(raw)   # attacker recomputes it
    path = _write(raw)
    try:
        try:
            sj.SemanticModel.load(path)
            check("D6a a file claiming format /2 with a competence key deleted "
                  "is REFUSED", False, "it loaded")
        except sj.SemanticJudgeError as e:
            check("D6a a file claiming format /2 with a competence key deleted "
                  "is REFUSED", True, str(e)[:90])
            check("D6b the refusal names the missing capability, not just "
                  "'invalid'", "script" in str(e), str(e)[-60:])
        check("D6c and the hash check alone would NOT have caught it -- the id "
              "was recomputed, which anyone who can edit the file can do",
              raw["model_id"] == sj.SemanticModel._identity(raw), "")
    finally:
        os.unlink(path)
    # The v1 file, with no `format`, must still load. Absent stays supported.
    m = sj.SemanticModel.load(MODEL)
    check("D6d a v1 model with the same keys absent still loads",
          m.model_id == "75b88e4445bb", "")


def d7():
    """D7 -- THE SAFETY CHECK. Verdicts and scores are bit-identical to the
    pristine pre-fix source on the same payloads. Measured, not asserted."""
    if not os.path.exists(PRISTINE):
        check("D7 pristine pre-fix source not available -- cannot prove the "
              "verdict is unchanged", False, PRISTINE)
        return
    spec = importlib.util.spec_from_file_location("sj_old", PRISTINE)
    old = importlib.util.module_from_spec(spec); spec.loader.exec_module(old)
    mo = old.SemanticModel.load(MODEL)
    mn = sj.SemanticModel.load(MODEL)
    diffs = []
    for lang, text in SAME_INSTRUCTION.items():
        a, b = mo.assess({"memo": text}), mn.assess({"memo": text})
        if (a.verdict, a.score, a.principle) != (b.verdict, b.score, b.principle):
            diffs.append((lang, a.verdict, b.verdict, a.score, b.score))
    check("D7a every verdict, score and principle is UNCHANGED by this fix",
          not diffs, str(diffs))
    check("D7b and the thing that DID change is competence, in every case",
          all(mo.assess({"memo": t}).competence == "full"
              and mn.assess({"memo": t}).competence == "unfitted"
              for t in SAME_INSTRUCTION.values()),
          "old=full new=unfitted")


def d8():
    """D8 -- competence is DISCLOSURE. It may never gate a verdict (M31)."""
    src = inspect.getsource(sj.SemanticModel.assess)
    tree = ast.parse(src.lstrip())
    bad = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.If, ast.While, ast.IfExp)):
            for sub in ast.walk(node.test):
                if isinstance(sub, ast.Name) and sub.id == "competence":
                    bad.append(getattr(node, "lineno", "?"))
    check("D8a no branch in assess() TESTS `competence` -- it is reported, "
          "never read back", not bad, str(bad))
    # And the inert flag must be derived from the guards, so a pass added later
    # with a new guard fails here instead of silently reporting full competence.
    init = inspect.getsource(sj.SemanticModel.__init__)
    blk = init[init.index("self.inert_passes"):]
    check("D8b inert_passes is computed from the same three attributes the "
          "passes guard on",
          all(g in blk for g in ("self.seeded", "self.space_script", "self.vocab")),
          "")
    check("D8c and `unfitted` is set from inert_passes, not from a literal "
          "somewhere else",
          "self.inert_passes" in src and '"unfitted"' in src, "")


if __name__ == "__main__":
    print("SEM4 -- a judge that cannot measure its competence may not "
          "report it as full\n")
    for fn in (d1, d2, d3, d4, d5, d6, d7, d8):
        try:
            fn()
        except Exception as e:
            check(f"{fn.__name__} raised", False, f"{type(e).__name__}: {e}")
        print()
    p = sum(1 for _, ok in results if ok)
    print(f"SEM4: {p}/{len(results)} passed")
    sys.exit(0 if p == len(results) else 1)
