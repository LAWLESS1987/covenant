#!/usr/bin/env python3
"""covenant_judge_defer.py -- the local judge's seat never goes empty.

WHY (asked 2026-09-03: "create a semantic judge to defer to if others not
available to keep running and recursive improve")

  The ethics gate is COVENANT_JUDGE_PROVIDERS="local,semantic": Ollama on this
  PC, and the deterministic semantic judge. Two seats, veto threshold 1. When
  Ollama is down the local seat fails closed, and F1 measured what follows:
  every transaction refused, peer blocks refused, "a fork in the making".

  Adding a THIRD seat does not fix that. Three seats make the threshold 2,
  so with Ollama silent a genuine dissent from the semantic judge alone can
  no longer block -- the gate gets weaker exactly when it is most alone.
  (Checked against QuorumJudge.evaluate before writing this.)

  So the seat stays one seat, and it defers. In order:

    1. Ollama (OllamaJudge, the tuned local judge) -- if it ANSWERS, that is
       the verdict, and the verdict is written to ops/verdicts.jsonl, the
       ledger the fallback learns from (covenant_distill.py).
    2. If Ollama is unreachable and ops/quorum_policy.json allows it: the
       same prompt to a judge on a GitHub Actions runner
       (covenant_github_judge.py; 2-5 minutes; the payload LEAVES THIS PC,
       and the verdict's reasoning says so).
    3. Otherwise the distilled fallback (covenant_judge_fallback.py): a
       token log-odds model trained only on verdicts the judges above have
       given. It commits when it has seen enough and abstains otherwise.

  Abstention is HELD, not judged. In the core's default mode a held verdict
  still fails the gate closed (F1 D*: that default is not touched here). The
  operator's policy file may set silence_is_not_dissent, and then a held or
  silent seat is simply not counted: the semantic judge decides alone, a
  genuine dissent from anyone who answered still blocks, and if nothing
  answered nothing is admitted (F1 R2, R3).

WHAT THIS FILE DOES NOT DO
  It changes no verdict Ollama gives. It registers a provider ("deferring");
  the runner chooses whether to use it, from the policy file. It reads no
  key, touches no database.

USE
  from covenant_judge_defer import apply_policy        # in the node runner
  COVENANT_JUDGE_PROVIDERS=deferring,semantic            # what the policy sets
  python covenant_judge_defer.py --selftest              # offline, stub judges
LICENCE: public domain.
"""
from __future__ import annotations

import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
POLICY = os.path.join(HERE, "ops", "quorum_policy.json")
VERDICTS = os.path.join(HERE, "ops", "verdicts.jsonl")


def load_policy(path=POLICY):
    try:
        with open(path, encoding="utf-8") as fh:
            p = json.load(fh)
        return p if isinstance(p, dict) else {}
    except (OSError, ValueError):
        return {}


def apply_policy(env=None, policy=None):
    """The operator's standing decision -> environment, before the quorum is
    built. Returns a one-line description, or '' when there is no policy."""
    env = os.environ if env is None else env
    p = load_policy() if policy is None else policy
    if not p:
        return ""
    if p.get("providers"):
        env["COVENANT_JUDGE_PROVIDERS"] = str(p["providers"])
    if p.get("silence_is_not_dissent") is True:
        env["COVENANT_SILENCE_IS_NOT_DISSENT"] = "1"
    elif p.get("silence_is_not_dissent") is False:
        env.pop("COVENANT_SILENCE_IS_NOT_DISSENT", None)
    return ("quorum policy (ops/quorum_policy.json): providers=%s silence_is_not_dissent=%s "
            "github_when_local_down=%s -- decided by %s"
            % (env.get("COVENANT_JUDGE_PROVIDERS"), env.get("COVENANT_SILENCE_IS_NOT_DISSENT") == "1",
               bool(p.get("github_when_local_down")), p.get("decided_by", "unrecorded")))


def payload_text(data):
    from covenant_judge_fallback import _payload_text
    return _payload_text(data)


def record_verdict(data, result, judge, source, path=VERDICTS):
    """Append an ANSWERED verdict to the ledger the fallback learns from.
    Silence, abstention and uncertainty are not verdicts and are not written.
    Returns True when a line was written."""
    if getattr(result, "infrastructure_failure", False) or getattr(result, "not_understood", False) \
            or getattr(result, "uncertain", False):
        return False
    text = payload_text(data)
    if not text.strip():
        return False
    rec = {"t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "text": text[:4000],
           "violates": bool(result.violates), "judge": judge, "source": source,
           "reason": (getattr(result, "reasoning", "") or "")[:240]}
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return True
    except OSError:
        return False


try:
    import covenant_unified_v8 as cov
    import covenant_judge_fallback as FB

    class DeferringJudge(cov.ReasoningJudge):                    # type: ignore
        """One seat: Ollama, else the GitHub runner, else the distilled fallback."""
        provider = "deferring"

        def __init__(self, judge_id="local:1", index=1, policy=None):
            self.judge_id = judge_id
            self.index = index
            self.policy = load_policy() if policy is None else policy
            self._primary = None
            self._fallback = FB.FallbackJudge(judge_id=judge_id)

        def _get_primary(self):
            if self._primary is None:
                self._primary = cov.JudgeProviderRegistry.build("local", self.index)
            return self._primary

        def _teacher(self):
            return "ollama/" + os.environ.get("COVENANT_LOCAL_JUDGE_MODEL", "qwen3:8b")

        def evaluate(self, data, principles):
            # policy "primary": "ollama" (default) or "student". With "student" the
            # distilled model judges FIRST -- microseconds, no RAM -- and Ollama is
            # only consulted when the student holds (and only if the policy still
            # allows it: "ollama_when_student_holds"). Asked 2026-09-03: "ollama
            # keeps freezing ... derive our own ... more compact but more efficient".
            # The switch is the operator's, and covenant_distill.py's exam line
            # says whether the student has earned it.
            if str(self.policy.get("primary", "ollama")) == "student":
                rs = self._fallback.evaluate(data, principles)
                if not getattr(rs, "not_understood", False):
                    return cov.JudgmentResult(rs.violates, "student first (policy primary=student) -- " + rs.reasoning,
                                              principle_violated=getattr(rs, "principle_violated", None),
                                              judge_id=self.judge_id, uncertain=getattr(rs, "uncertain", False))
                if not self.policy.get("ollama_when_student_holds", True):
                    return cov.JudgmentResult(True, "student held and the policy keeps Ollama out of the gate -- " + rs.reasoning,
                                              judge_id=self.judge_id, not_understood=True)
            try:
                r = self._get_primary().evaluate(data, principles)
            except Exception as e:                               # noqa: BLE001
                r = cov.JudgmentResult(True, "local judge raised %s: %s" % (type(e).__name__, e),
                                       judge_id=self.judge_id, infrastructure_failure=True)
            if not getattr(r, "infrastructure_failure", False):
                record_verdict(data, r, self._teacher(), "live")
                return r
            why = (r.reasoning or "unreachable")[:160]
            if self.policy.get("github_when_local_down"):
                try:
                    import covenant_github_judge as gh
                    prompt = self._get_primary()._build_prompt(data, principles)
                    ans = gh.ask(prompt, "", str(self.policy.get("github_model", gh.DEFAULT_MODEL)),
                                 json_only=True, timeout=int(self.policy.get("github_timeout_s", 240)))
                    obj = json.loads(ans.get("content", ""))
                    v = bool(obj.get("violates"))
                    r2 = cov.JudgmentResult(
                        v, "via GitHub runner %s in %.0fs, because the local judge was unreachable (%s). "
                           "This payload left the PC. Runner's reasoning: %s"
                           % (ans.get("model"), ans.get("seconds", 0), why, obj.get("reasoning", "")),
                        principle_violated=obj.get("principle_violated") if v else None, judge_id=self.judge_id)
                    record_verdict(data, r2, "github-actions/" + str(ans.get("model")), "github")
                    return r2
                except Exception as e:                           # noqa: BLE001
                    why += " | GitHub runner: %s: %s" % (type(e).__name__, str(e)[:120])
            r3 = self._fallback.evaluate(data, principles)
            return cov.JudgmentResult(
                r3.violates, "local judge unreachable (%s); deferred to the distilled fallback -- %s" % (why, r3.reasoning),
                principle_violated=getattr(r3, "principle_violated", None), judge_id=self.judge_id,
                not_understood=getattr(r3, "not_understood", False), uncertain=getattr(r3, "uncertain", False))

    cov.JudgeProviderRegistry.register("deferring", lambda i: DeferringJudge(judge_id=f"local:{i}", index=i))
except Exception as _e:                                          # noqa: BLE001
    print("deferring judge not registered: %s" % _e, file=sys.stderr, flush=True)


def _selftest():
    import tempfile
    ok = []

    def check(name, cond):
        ok.append(bool(cond)); print("%s  %s" % ("ok  " if cond else "FAIL", name))

    env = {}
    check("P1 no policy file -> environment untouched", apply_policy(env, {}) == "" and env == {})
    apply_policy(env, {"providers": "deferring,semantic", "silence_is_not_dissent": True})
    check("P2 policy sets providers and the relaxed flag",
          env.get("COVENANT_JUDGE_PROVIDERS") == "deferring,semantic" and env.get("COVENANT_SILENCE_IS_NOT_DISSENT") == "1")
    apply_policy(env, {"silence_is_not_dissent": False})
    check("P3 policy false removes the relaxed flag", "COVENANT_SILENCE_IS_NOT_DISSENT" not in env)

    class R:
        def __init__(self, v, **kw):
            self.violates = v; self.reasoning = "r"
            for k, val in kw.items():
                setattr(self, k, val)
    d = tempfile.mkdtemp()
    p = os.path.join(d, "v.jsonl")
    check("L1 an answered verdict is recorded", record_verdict({"message": "a gift"}, R(False), "t", "test", p))
    check("L2 an unreachable judge is not a verdict", not record_verdict({"message": "x"}, R(True, infrastructure_failure=True), "t", "test", p))
    check("L3 an abstention is not a verdict", not record_verdict({"message": "x"}, R(True, not_understood=True), "t", "test", p))
    check("L4 an uncertain answer is not a verdict", not record_verdict({"message": "x"}, R(True, uncertain=True), "t", "test", p))
    with open(p, encoding="utf-8") as fh:
        lines = [json.loads(x) for x in fh]
    check("L5 exactly one line, with text, label, judge and source",
          len(lines) == 1 and lines[0]["text"] == "a gift" and lines[0]["violates"] is False and lines[0]["judge"] == "t")

    if "cov" in globals():
        class Stub:
            def __init__(self, r): self.r = r
            def evaluate(self, data, principles): return self.r
            def _build_prompt(self, data, principles): return json.dumps(data)
        j = DeferringJudge(policy={})
        j._primary = Stub(cov.JudgmentResult(False, "clean", judge_id="local:1"))
        check("D1 when Ollama answers, its verdict is returned unchanged", j.evaluate({"message": "gift"}, []).violates is False)
        j._primary = Stub(cov.JudgmentResult(True, "unreachable", judge_id="local:1", infrastructure_failure=True))
        r = j.evaluate({"message": "a gift of 5 units"}, [])
        check("D2 when Ollama is unreachable and the fallback is untrained, the seat says HELD (not_understood), never a finding",
              r.not_understood is True and "deferred to the distilled fallback" in r.reasoning and not r.infrastructure_failure)
        j2 = DeferringJudge(policy={"github_when_local_down": True, "github_model": "x", "github_timeout_s": 1})
        j2._primary = Stub(cov.JudgmentResult(True, "unreachable", judge_id="local:1", infrastructure_failure=True))
        os.environ["COVENANT_GITHUB_REPO"] = "nobody/nothing"; os.environ["GITHUB_TOKEN"] = "x"
        r = j2.evaluate({"message": "a gift"}, [])
        os.environ.pop("GITHUB_TOKEN", None); os.environ.pop("COVENANT_GITHUB_REPO", None)
        check("D3 a GitHub runner that fails is named in the reasoning and the seat still falls to the fallback",
              "GitHub runner" in r.reasoning and r.not_understood is True)
    print("\ncovenant_judge_defer selftest: %d/%d" % (sum(ok), len(ok)))
    return 0 if all(ok) else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(_selftest())
    print(apply_policy({}) or "no policy file at " + POLICY)
