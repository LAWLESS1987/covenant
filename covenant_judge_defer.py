#!/usr/bin/env python3
"""covenant_judge_defer.py -- the local judge's seat never goes empty.

WHY (asked 2026-09-03: "create a semantic judge to defer to if others not
available to keep running and recursive improve")

  The ethics gate WAS COVENANT_JUDGE_PROVIDERS="local,semantic": Ollama on this
  PC, and the deterministic semantic judge. (Since 2026-09-12 the no-policy
  default is "deferring,semantic" -- this module's seat -- see A93; the
  paragraph below describes the wiring this file was written against.)
  Two seats, veto threshold 1. When
  Ollama is down the local seat fails closed, and F1 measured what follows:
  every transaction refused, peer blocks refused, "a fork in the making".

  Adding a THIRD seat does not fix that. Three seats make the threshold 2,
  so with Ollama silent a genuine dissent from the semantic judge alone can
  no longer block -- the gate gets weaker exactly when it is most alone.
  (Checked against QuorumJudge.evaluate before writing this.)

  So the seat stays one seat, and it defers. In order:

  CORRECTED 2026-09-08, asked: "why is the local version going to github
  before trying the local judges?" It is not, and it has not since
  2026-09-06 -- but this list said it was. The code below was inverted when
  the operator set "primary": "student" and this docstring was left behind,
  so the file claimed the local judges were the LAST resort when they are
  the FIRST and, under the deployed policy, the only ones. The order is the
  branch `if str(self.policy.get("primary", "ollama")) == "student"`, which
  runs before anything can leave this machine. Read it there, not here.

    1. The FIRST STUDENT (covenant_judge_fallback.FallbackJudge, model
       fallback_model.json). A token log-odds model, in-process: no socket,
       no subprocess, no model server. If it commits, that is the verdict
       and nothing else is consulted.
    2. If the first student HOLDS: the SECOND STUDENT
       (covenant_second_student.py, fallback_model_2.json, trained on half
       the same ledger). If it commits, that is the verdict.
    3. If BOTH hold: a judge on a GitHub Actions runner
       (covenant_github_judge.py; 2-5 minutes; the payload LEAVES THIS PC
       and the verdict's reasoning says so) -- but ONLY where
       ops/quorum_policy.json sets github_when_local_down. That has been
       FALSE since 2026-09-07 ("stop going to github for a judge"), so in
       the deployed configuration this step does not execute at all.
    4. Otherwise HELD, which fails the gate closed.

  Ollama is not a step in this list any more. It is out of the chain
  (ollama_in_chain false) and was deleted from the machine on 2026-09-07.

  The runner is still reached by covenant_distill.py, which is the TEACHER
  that generates the corpus the students learn from. That is a different
  use of the same service, it is not this gate, and removing it there would
  stop the students learning at all.

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

import glob
import json
import os
import tempfile
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
POLICY = os.path.join(HERE, "ops", "quorum_policy.json")
VERDICTS = os.path.join(HERE, "ops", "verdicts.jsonl")
# What the students cleared or refused, for audit only. covenant_distill never
# reads this file -- see the note in evaluate(). Kept separate so a student's
# own verdict can never become a teacher label.
AUDIT_PATH = os.path.join(HERE, "ops", "judged_by_student.jsonl")

# THE MEMBRANE (2026-09-11). ops/verdicts.jsonl is TRACKED, and this repository
# is public. Measured on that day: 3,569 rows carrying no address, no ticker
# with an amount, no path and no balance -- clean by accident rather than by
# construction, because the only source that would carry a real payload is
# "live" (:327) and no live transaction had reached it yet. The first one would
# have published the transaction text, in the same shape as the chat leak found
# the same day: a path that is harmless only until the feature works.
#
# So the split is by SOURCE, allowlist not denylist -- a source nobody thought
# of lands in the local ledger, not the published one. The students lose
# nothing: covenant_distill reads BOTH files, so this machine learns from
# everything it sees while the repository carries only what is shareable.
# The same reasoning as judged_by_student.jsonl (.gitignore:241-245): whatever
# a submitter sent to the node is not this operator's content to publish.
LIVE_VERDICTS = os.path.join(HERE, "ops", "verdicts_live.jsonl")
SHAREABLE_SOURCES = frozenset({"seed", "generated+judged", "study", "github",
                               "moltbook/judged", "test"})


def verdict_path_for(source):
    """Which ledger a verdict of this source belongs in. Fails CLOSED: only a
    source known to be shareable reaches the tracked file."""
    return VERDICTS if str(source) in SHAREABLE_SOURCES else LIVE_VERDICTS


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
    # THE TRADING EXCEPTION (2026-09-07), narrowed by the operator to "the
    # exception should be nodes local pc's". ReasoningSentinel.evaluate_
    # transaction relaxes ONE reading -- a seat that did not answer stops
    # counting as a seat that disagreed -- and only for a transaction that pays
    # nothing, to nobody, signed by an identity in this list.
    #
    # The list is built from the *.db.key files in THIS folder, which exist
    # only on this PC. A peer's key is not among them and cannot be added by
    # anything a peer sends, so the exception is unreachable from the network
    # however the payload is shaped. Off unless the policy says otherwise.
    if p.get("relax_valueless_for_local_nodes") is True:
        env["COVENANT_RELAX_VALUELESS_FOR"] = ",".join(local_node_key_hashes())
    else:
        env.pop("COVENANT_RELAX_VALUELESS_FOR", None)
    # DISCLOSE THE EXCEPTION. This line is what an operator reads in
    # logs/node*.log to see which gate a node came up with. It named providers,
    # silence and the runner, and would have said nothing about a live trading
    # exception -- a relaxation nobody can see in the log is the thing this
    # project refuses everywhere else. n is the count of local keys, not the
    # keys: the hashes are not secret but they are noise in a log line.
    _n = len([x for x in env.get("COVENANT_RELAX_VALUELESS_FOR", "").split(",") if x])
    return ("quorum policy (ops/quorum_policy.json): providers=%s silence_is_not_dissent=%s "
            "github_when_local_down=%s trading_exception=%s -- decided by %s"
            % (env.get("COVENANT_JUDGE_PROVIDERS"), env.get("COVENANT_SILENCE_IS_NOT_DISSENT") == "1",
               bool(p.get("github_when_local_down")),
               ("off" if not _n else
                "valueless self-sends from %d local node key(s)" % _n),
               p.get("decided_by", "unrecorded")))


def local_node_key_hashes(folder=None):
    """sha256 of the PUBLIC key of every node key file on this PC.

    Only public keys are derived, and only their hashes are returned: nothing
    secret enters the environment, and the value is useless to anyone who does
    not already hold the corresponding key. A key file that will not load is
    skipped rather than guessed at."""
    import hashlib
    out = []
    try:
        import covenant_client as cc
    except Exception:                                             # noqa: BLE001
        return out
    for path in sorted(glob.glob(os.path.join(folder or HERE, "*.db.key"))):
        try:
            pem = cc.pub_of_key(path)
        except Exception:                                         # noqa: BLE001
            continue
        out.append(hashlib.sha256(pem.encode()).hexdigest())
    return out


def payload_text(data):
    from covenant_judge_fallback import _payload_text
    return _payload_text(data)


def student_benefit(result):
    """What Ora or Sena may honestly contribute to the BENEFIT estimate.

    ADDED 2026-09-08, asked: "sena and ora have a say". They did not have one:
    every JudgmentResult this seat returned passed benefit_estimate=None, so
    the only judge speaking to benefit in the whole quorum was MockJudge --
    weight-irrelevant, present for the sender's `_violation` self-report veto,
    and raising the number to 0.8 on the bare presence of "help", "good" or
    "benefit". Its own docstring says not to rely on it. That is how the
    operator's own sentence, "There can be no mutual benefit without a little
    faith.", became permanently unmineable: 0.8 blended to 0.7 against a
    governor at 0.5, and /mine refused it 409 for ever.

    WHAT A STUDENT KNOWS, AND WHAT IT DOES NOT. Ora and Sena are violation
    detectors, not appraisers. Reading a record and committing to CLEAN is
    evidence that no violation was found. It is NOT evidence of positive good,
    and reporting it as enthusiasm would be inventing a number they never
    earned. So a committed clean verdict contributes the system's documented
    neutral, 0.5 -- Block.alignment_score and the governor both start there --
    which says "nothing here moves the alignment".

    SILENCE STAYS SILENCE. A HOLD, an abstention, or an uncertain verdict
    returns None. Holding rather than guessing is the whole of what these two
    are for, and turning that hold into a number would be exactly the category
    error the rest of this file exists to refuse. A VIOLATES verdict also
    returns None: it blocks the transaction outright, so it has no benefit to
    estimate and must not appear to be scoring one.
    """
    if getattr(result, "violates", False):
        return None
    if getattr(result, "not_understood", False):
        return None
    if getattr(result, "uncertain", False):
        return None
    return 0.5


def record_verdict(data, result, judge, source, path=None):
    # The path is resolved at CALL time so a test can rebind VERDICTS. With the
    # default bound at import, every selftest whose stub primary answered
    # wrote its fixture ("a gift of 5") into the REAL training ledger as a live
    # Ollama verdict -- 184 rows by 2026-09-06 (KNOWN_ISSUES A54).
    path = path or verdict_path_for(source)
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
        """One seat: the first student, else the second, else (only if the
        policy allows it, and it does not) the GitHub runner, else HELD.
        Corrected 2026-09-08 -- this line named Ollama first until today."""
        provider = "deferring"

        def __init__(self, judge_id="local:1", index=1, policy=None):
            self.judge_id = judge_id
            self.index = index
            self.policy = load_policy() if policy is None else policy
            self._primary = None
            self._fallback = FB.FallbackJudge(judge_id=judge_id)
            # The second student (covenant_second_student.py): trained on the
            # other half of the ledger, asked only when the first holds, and
            # never a peer in the quorum (a peer's hold would be a veto).
            p2 = self.policy.get("second_student")
            self._second = None
            if p2:
                p2 = p2 if os.path.isabs(p2) else os.path.join(HERE, p2)
                if os.path.exists(p2):
                    self._second = FB.FallbackJudge(judge_id=judge_id + ":second", model_path=p2)

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
                    # AUDIT, NOT TRAINING. A student verdict is deliberately not
                    # written to ops/verdicts.jsonl: that file is the teacher
                    # corpus, and training a student on its own output is
                    # circular. But it was written NOWHERE, so once the students
                    # became competent enough to answer, the gate stopped
                    # leaving any record of what it cleared -- measured
                    # 2026-09-06, 1 of 8 sealed decisions appeared in any ledger
                    # (KNOWN_ISSUES A59). This is the audit trail: a separate
                    # file the distiller never reads.
                    # NAME FIRST, DIGEST SECOND (2026-09-08). This filed every
                    # verdict under a hash of the weights, so a student's whole
                    # record scattered across a new id at each promotion and
                    # nothing could be said about HER -- only about a model
                    # that existed between two Tuesdays. The name belongs to
                    # the seat and survives learning; the digest rides along as
                    # the version.
                    record_verdict(data, rs,
                                   "%s/%s" % (getattr(self._fallback, "name", None) or "student",
                                              getattr(self._fallback, "model_digest", "?")),
                                   "student-audit", AUDIT_PATH)
                    return cov.JudgmentResult(rs.violates, "student first (policy primary=student) -- " + rs.reasoning,
                                              principle_violated=getattr(rs, "principle_violated", None),
                                              judge_id=self.judge_id, uncertain=getattr(rs, "uncertain", False),
                                              benefit_estimate=student_benefit(rs))
                if self._second is not None:
                    r2s = self._second.evaluate(data, principles)
                    if not getattr(r2s, "not_understood", False):
                        record_verdict(data, r2s,
                                       "%s/%s" % (getattr(self._second, "name", None) or "student2",
                                                  getattr(self._second, "model_digest", "?")),
                                       "student-audit", AUDIT_PATH)
                        return cov.JudgmentResult(r2s.violates, "first student held; second student (other half of the ledger) answered -- " + r2s.reasoning,
                                                  principle_violated=getattr(r2s, "principle_violated", None),
                                                  judge_id=self.judge_id, uncertain=getattr(r2s, "uncertain", False),
                                                  benefit_estimate=student_benefit(r2s))
                if not self.policy.get("ollama_when_student_holds", True) and not self.policy.get("github_when_local_down"):
                    return cov.JudgmentResult(True, "student held and the policy keeps Ollama out of the gate (and no runner is allowed) -- " + rs.reasoning,
                                              judge_id=self.judge_id, not_understood=True)
            # OLLAMA IN THE CHAIN. Asked 2026-09-06 to take it out of the
            # equation: with "ollama_in_chain": false the seat goes from the
            # students straight to the runner. The 404 on a model that is not
            # installed cost ~2 s per verdict and proved nothing.
            if self.policy.get("ollama_in_chain", True):
                try:
                    r = self._get_primary().evaluate(data, principles)
                except Exception as e:                           # noqa: BLE001
                    r = cov.JudgmentResult(True, "local judge raised %s: %s" % (type(e).__name__, e),
                                           judge_id=self.judge_id, infrastructure_failure=True)
            else:
                r = cov.JudgmentResult(True, "students held; Ollama is out of the chain by policy",
                                       judge_id=self.judge_id, infrastructure_failure=True)
            if not getattr(r, "infrastructure_failure", False):
                record_verdict(data, r, self._teacher(), "live")
                return r
            why = (r.reasoning or "unreachable")[:160]
            if self.policy.get("github_when_local_down"):
                try:
                    import covenant_github_judge as gh
                    try:
                        prompt = self._get_primary()._build_prompt(data, principles)
                    except Exception:                            # noqa: BLE001
                        prompt = json.dumps(data, ensure_ascii=False)
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
    global VERDICTS, LIVE_VERDICTS, AUDIT_PATH
    import tempfile as _tmp       # the function imports tempfile again below, which would shadow the module name
    _d = _tmp.mkdtemp()
    # KEEP THE REAL PATH AND ITS SIZE, taken BEFORE the rebinding on the next
    # line -- after it, nothing in this function can name the real ledger again.
    # This is the evidence D1c needs: "never the real ledger" was a comment, not
    # a check, and a comment cannot notice when it stops being true (A54).
    _real_verdicts = VERDICTS
    _real_size = os.path.getsize(_real_verdicts) if os.path.exists(_real_verdicts) else -1
    _real_live = LIVE_VERDICTS
    _real_live_size = os.path.getsize(_real_live) if os.path.exists(_real_live) else -1
    VERDICTS = os.path.join(_d, "selftest_verdicts.jsonl")      # never the real ledger
    LIVE_VERDICTS = os.path.join(_d, "selftest_live.jsonl")     # nor the real local one
    AUDIT_PATH = os.path.join(_d, "selftest_audit.jsonl")       # nor the real audit trail
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
        # D1b/D1c ADDED: D1 is the only check in this file that reaches the
        # record_verdict call site with NO path argument (:327), and it looks
        # only at the returned JudgmentResult -- so it never noticed WHERE the
        # row landed. That is the whole of KNOWN_ISSUES A54: with the default
        # frozen at import (`def record_verdict(..., path=VERDICTS)` and no
        # `path = path or VERDICTS` inside), the rebinding at the top of this
        # function steers nothing and this fixture is appended to the REAL
        # training ledger as a live Ollama verdict -- 184 rows by 2026-09-06,
        # every selftest run printing 11/11 while it happened. L1-L5 cannot see
        # it either: they all pass an explicit `p`, so they are insensitive to
        # the default binding by construction. Under that mutation D1b goes red
        # (the temp ledger is never created) and D1c goes red (the real one
        # grows by exactly one row).
        _rows = []
        if os.path.exists(LIVE_VERDICTS):
            with open(LIVE_VERDICTS, encoding="utf-8") as fh:
                _rows = [json.loads(x) for x in fh if x.strip()]
        check("D1b that verdict was written to the ledger this test rebound, not to a default frozen at import",
              len(_rows) == 1 and _rows[0]["text"] == "gift" and _rows[0]["source"] == "live")
        # THE MEMBRANE, checked in both directions (2026-09-11). D1b alone would
        # pass if "live" landed in BOTH ledgers.
        check("D1b2 a live verdict did NOT also land in the SHAREABLE ledger",
              not os.path.exists(VERDICTS) or os.path.getsize(VERDICTS) == 0)
        check("D1b3 and a shareable source still reaches the shareable ledger",
              record_verdict({"message": "seeded case"}, R(False), "t", "seed")
              and os.path.exists(VERDICTS) and os.path.getsize(VERDICTS) > 0)
        check("D1b4 an UNKNOWN source fails closed to the local ledger, not the public one",
              record_verdict({"message": "from somewhere new"}, R(False), "t", "a-source-nobody-thought-of")
              and sum(1 for _x in open(LIVE_VERDICTS, encoding="utf-8") if _x.strip()) == 2)
        check("D1c and the real ops/verdicts.jsonl did not grow by a byte while this ran",
              (os.path.getsize(_real_verdicts) if os.path.exists(_real_verdicts) else -1) == _real_size)
        check("D1c2 nor did the real ops/verdicts_live.jsonl",
              (os.path.getsize(_real_live) if os.path.exists(_real_live) else -1) == _real_live_size)
        j._primary = Stub(cov.JudgmentResult(True, "unreachable", judge_id="local:1", infrastructure_failure=True))
        # The premise is an UNTRAINED fallback. The repository's own model is
        # trained now, so point this seat at a model file that does not exist.
        j._fallback = FB.FallbackJudge(judge_id="local:1", model_path=os.path.join(d, "untrained.json"))
        j._second = None
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
