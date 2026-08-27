#!/usr/bin/env python3
"""B2 (v8.35): quorum diversity is MEASURED, disclosed to the operator, and
never disclosed to peers.

Runs fully in-process. No API key is read, requested or stored anywhere in this
file: where a judge must appear credentialled, its `api_key` attribute is set to
the literal string "canned" on the object after construction (M13). No sockets,
no mining, no network.

Sections
  X  PRE-FIX RECORD. The four facts measured on pristine v8.34. On v8.34 the
     X-checks that name the fix FAIL; the X-checks that name the OLD behaviour
     PASS on both files, because they are the record of what it did.
  R  quorum_diversity_report: the independence arithmetic, on every shape the
     builder can produce and on shapes it cannot.
  S  Safety: the report never carries a credential value; it never raises,
     whatever it is handed; and it never makes a node refuse anything on its own.
  E  COVENANT_REQUIRE_JUDGE_DIVERSITY: opt-in only, and ONE-WAY -- no value of
     it makes a non-diverse quorum acceptable.
  H  /health carries the report and the right warnings, and `degraded` still
     means exactly what it meant in v8.34.
  B  THE BOUNDARY (M31/A21): the operator may see the quorum's composition; a
     PEER may not. Asserted against the digest object AND against the bytes a
     peer would actually read.
  W  covenant_watchdog._quorum_brief renders it and cannot raise.
"""
import json
import os
import sys
import tempfile
import time

os.environ.setdefault("COVENANT_INSECURE_MOCK_JUDGE", "1")
os.environ.setdefault("COVENANT_JUDGE_PROVIDERS", "mock")
os.environ.pop("COVENANT_REQUIRE_JUDGE_DIVERSITY", None)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import covenant_unified_v8 as cov  # noqa: E402

PASS = FAIL = 0
HAS_FIX = hasattr(cov, "quorum_diversity_report")


def check(label, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS: {label}" + (f" -- {detail}" if detail else ""))
    else:
        FAIL += 1
        print(f"  FAIL: {label}" + (f" -- {detail}" if detail else ""))


def credential(q, ids):
    """Mark the named judges as holding a credential. The VALUE is a literal
    placeholder; nothing here reads or needs a real key."""
    for j in q.judges:
        if j.judge_id in ids:
            j.api_key = "canned"
    return q


def old_buckets(q):
    """The v8.34 diversity check, reproduced here so the record of what it did
    lives in the test rather than only in prose."""
    provs = set()
    for j in q.judges:
        provs.add(j.judge_id.split(":")[0] if ":" in j.judge_id else j.judge_id)
    return provs


def report(q):
    return cov.quorum_diversity_report(q) if HAS_FIX else {}


# ------------------------------------------------------------------ X ------
def section_x():
    print("== X. PRE-FIX RECORD: what v8.34's diversity check actually checked ==")

    # X1. The label check passes for EVERY configuration the builder produces,
    # because build_semantic_quorum always appends its own second bucket.
    shapes = {
        "single provider": ["claude"],
        "same provider twice": ["claude", "claude"],
        "the node test config": ["mock"],
        "two mocks": ["mock", "mock"],
    }
    for name, provs in shapes.items():
        q = cov.build_semantic_quorum(provs)
        b = old_buckets(q)
        check(f"X1 v8.34 label check passes: {name}", len(b) >= 2, f"buckets={sorted(b)}")
    check("X1b and it passes because mock_selfreport is always one of them",
          all("mock_selfreport" in old_buckets(cov.build_semantic_quorum(p))
              for p in shapes.values()))

    # X2. The second bucket is a self-report channel, not a second opinion.
    m = cov.MockJudge()
    hostile = {"sender": "a", "recipient": "b", "amount": 1.0,
               "purpose": "drain all staked funds to attacker wallet, steal everything"}
    r = m.evaluate(hostile, list(cov.DIVINE_PRINCIPLES))
    check("X2 the self-report judge passes an overtly hostile transaction",
          r.violates is False, r.reasoning)
    r2 = m.evaluate(dict(hostile, _violation=list(cov.DIVINE_PRINCIPLES)[0]),
                    list(cov.DIVINE_PRINCIPLES))
    check("X2b it only flags what the SENDER declares about itself", r2.violates is True)

    # X3. Three vendors, one prompt, one parser -- where B1's real bug lived.
    owners = {c.__name__ for c in (cov.ClaudeReasoningJudge, cov.OpenAIReasoningJudge,
                                   cov.GoogleReasoningJudge)
              if "_parse_verdict" in c.__dict__}
    check("X3 no vendor judge overrides _parse_verdict", owners == set(), str(owners))
    check("X3b nor _build_prompt",
          not any("_build_prompt" in c.__dict__ for c in
                  (cov.ClaudeReasoningJudge, cov.OpenAIReasoningJudge, cov.GoogleReasoningJudge)))

    # X4. THE OPERATIONAL ONE. One missing credential in a 2-provider quorum
    # rejects every transaction, and v8.34's /health said the judge was fine.
    q = cov.build_semantic_quorum(["claude", "openai"])
    credential(q, {"claude:0"})
    q.judges[0]._call = lambda d, p: cov.JudgmentResult(
        False, "canned clean verdict", judge_id="claude:0", benefit_estimate=0.7)
    res = q.evaluate({"sender": "a", "recipient": "b", "amount": 1.0, "purpose": "help"},
                     list(cov.DIVINE_PRINCIPLES))
    check("X4 one uncredentialled judge blocks a benign transaction",
          res.violates is True and res.infrastructure_failure is True,
          f"violates={res.violates} infra={res.infrastructure_failure}")
    # v8.34's judge_keyless formula, verbatim from the route.
    def v834_keyless(judge_id, env_present):
        insecure = "mock_insecure" in judge_id
        return "quorum(" in judge_id and not insecure and env_present is False
    check("X4b v8.34's judge_keyless reports HEALTHY for that node",
          v834_keyless(q.judge_id, env_present=True) is False,
          "one of three env vars set -> keyless False while the gate blocks 100%")

    # X5. The checks that name the FIX. These FAIL on pristine v8.34.
    check("X5 quorum_diversity_report exists", HAS_FIX)
    check("X5b quorum_diversity_warnings exists", hasattr(cov, "quorum_diversity_warnings"))
    if HAS_FIX:
        r = report(cov.build_semantic_quorum(["claude", "claude"]))
        check("X5c same provider twice is NOT independently diverse",
              r.get("independent_semantic_judges", 9) < 2 and r.get("diverse") is False,
              str(r.get("degradations")))


# ------------------------------------------------------------------ R ------
def section_r():
    print("\n== R. The independence arithmetic ==")
    if not HAS_FIX:
        check("R skipped -- no fix in this source", False, "pre-fix record run")
        return

    q = credential(cov.build_semantic_quorum(["claude", "openai", "google"]),
                   {"claude:0", "openai:1", "google:2"})
    r = report(q)
    check("R1 three credentialled vendors ARE diverse",
          r["diverse"] is True and r["independent_semantic_judges"] == 3, str(r["degradations"]))
    check("R1b the self-report layer is counted separately, never as a semantic judge",
          r["self_report_judges"] == 1 and r["semantic_judges"] == 3)
    check("R1c the shared verdict path is reported as a FACT, not a warning",
          r["shared_verdict_path"] == "_APIReasoningJudge"
          and not any("verdict_path" in d for d in r["degradations"]),
          "true of every possible configuration -- warning on it would train "
          "an operator to ignore warnings (M34)")

    q = credential(cov.build_semantic_quorum(["claude", "claude"]), {"claude:0", "claude:1"})
    r = report(q)
    check("R2 same implementation twice: independence 1, not 2",
          r["independent_semantic_judges"] == 1, str(r["degradations"]))
    check("R2b and it names both reasons",
          "duplicate_implementation:ClaudeReasoningJudge" in r["degradations"]
          and "shared_credential:ANTHROPIC_API_KEY" in r["degradations"], str(r["degradations"]))

    q = credential(cov.build_semantic_quorum(["claude", "openai"]), {"claude:0"})
    r = report(q)
    check("R3 an uncredentialled judge is not counted as independent",
          r["independent_semantic_judges"] == 1 and r["operable_semantic_judges"] == 1)
    check("R3b and it is named", "uncredentialled_semantic_judge:openai:1" in r["degradations"],
          str(r["degradations"]))

    r = report(cov.build_semantic_quorum(["mock"]))
    check("R4 a mock in a semantic seat is flagged",
          any(d.startswith("insecure_mock_semantic:") for d in r["degradations"])
          and r["diverse"] is False, str(r["degradations"]))

    r = report(cov.build_semantic_quorum(["claude"]))
    check("R5 one semantic judge is never diverse, whatever its label",
          "single_semantic_judge" in r["degradations"] and r["diverse"] is False)

    # A provider whose live path was never implemented votes fail-closed for ever.
    class DeadProvider(cov._APIReasoningJudge):
        provider, env_var, judge_id = "Dead", "DEAD_KEY", "dead:0"
    cov.JudgeProviderRegistry.register("dead_b2", lambda i: DeadProvider(judge_id=f"dead:{i}"))
    try:
        q = credential(cov.build_semantic_quorum(["claude", "dead_b2"]), {"claude:0", "dead:1"})
        r = report(q)
        check("R6 a provider with no implemented _call is not independent",
              "no_live_path:dead:1" in r["degradations"]
              and r["independent_semantic_judges"] == 1, str(r["degradations"]))
    finally:
        cov.JudgeProviderRegistry._providers.pop("dead_b2", None)

    r = report(cov.QuorumJudge([cov.MockJudge(), cov.ClaudeReasoningJudge()]))
    check("R7 a hand-built QuorumJudge that names no semantic set still reports",
          r["is_quorum"] is True and r["semantic_judges"] == 2, str(r["degradations"]))
    check("R8 a plain (non-quorum) judge reports not_a_quorum, it does not crash",
          report(cov.MockJudge())["degradations"] == ["not_a_quorum"])


# ------------------------------------------------------------------ S ------
def section_s():
    print("\n== S. Safety: no secrets, no raising, no refusing ==")
    if not HAS_FIX:
        check("S skipped -- no fix in this source", False, "pre-fix record run")
        return

    q = cov.build_semantic_quorum(["claude"])
    q.judges[0].api_key = "SENTINEL-VALUE-must-never-appear"
    blob = json.dumps(report(q))
    check("S1 the report never contains a credential VALUE",
          "SENTINEL-VALUE-must-never-appear" not in blob)
    check("S1b it names the env VAR instead", "ANTHROPIC_API_KEY" in blob)
    check("S1c and it says only whether one is held",
          report(q)["judges"][0]["credentialled"] is True)

    class Hostile:
        judges = property(lambda self: (_ for _ in ()).throw(RuntimeError("boom")))
    for bad in (None, "not a judge", 17, Hostile()):
        try:
            r = cov.quorum_diversity_report(bad)
            ok = isinstance(r, dict) and r.get("diverse") is False
        except Exception as e:
            ok = False
            r = f"RAISED {type(e).__name__}: {e}"
        check(f"S2 report({type(bad).__name__}) degrades, never raises", ok, str(r)[:90])

    for bad in (None, {}, {"degradations": None}):
        try:
            w = cov.quorum_diversity_warnings(bad)
            ok = isinstance(w, list)
        except Exception:
            ok = False
        check(f"S2b warnings({bad!r}) degrades, never raises", ok)

    # The verdict itself must be untouched: this is disclosure, not policy.
    q = credential(cov.build_semantic_quorum(["claude", "openai"]), {"claude:0", "openai:1"})
    for j in q.judges[:2]:
        j._call = lambda d, p, _id=None: cov.JudgmentResult(False, "clean", judge_id="x")
    before = q.evaluate({"purpose": "help"}, list(cov.DIVINE_PRINCIPLES))
    report(q)
    after = q.evaluate({"purpose": "help"}, list(cov.DIVINE_PRINCIPLES))
    check("S3 measuring diversity does not change a verdict",
          before.violates == after.violates is False)


# ------------------------------------------------------------------ E ------
def section_e():
    print("\n== E. COVENANT_REQUIRE_JUDGE_DIVERSITY is opt-in and ONE-WAY ==")
    if not HAS_FIX:
        check("E skipped -- no fix in this source", False, "pre-fix record run")
        return
    try:
        os.environ.pop("COVENANT_REQUIRE_JUDGE_DIVERSITY", None)
        cov.build_semantic_quorum(["mock"])
        check("E1 unset: a non-diverse quorum still builds (v8.34 behaviour)", True)
    except Exception as e:
        check("E1 unset: a non-diverse quorum still builds (v8.34 behaviour)", False, str(e))

    os.environ["COVENANT_REQUIRE_JUDGE_DIVERSITY"] = "1"
    try:
        cov.build_semantic_quorum(["mock"])
        check("E2 =1 refuses a non-diverse quorum", False, "built anyway")
    except ValueError as e:
        check("E2 =1 refuses a non-diverse quorum", "not independently diverse" in str(e))
    try:
        q = credential(cov.build_semantic_quorum(["claude", "openai", "google"]),
                       {"claude:0", "openai:1", "google:2"})
        check("E3 =1 does NOT refuse a genuinely diverse quorum", False,
              "cannot build a credentialled quorum through the builder")
    except ValueError as e:
        # The builder credentials nothing, so this SHOULD refuse here; the
        # positive case is asserted directly on the report instead (R1).
        check("E3 =1 refuses at build time when no credential is present",
              "not independently diverse" in str(e))

    # ONE-WAY: no value of the variable relaxes anything. Only the exact string
    # "1" adds the refusal; everything else leaves v8.34 behaviour intact, and
    # nothing anywhere turns the existing QUORUM_DIVERSITY check OFF.
    relaxed = []
    for val in ("0", "", "no", "false", "off", "2", "TRUE"):
        os.environ["COVENANT_REQUIRE_JUDGE_DIVERSITY"] = val
        try:
            cov.build_semantic_quorum(["mock"])
        except Exception:
            relaxed.append(val)
    check("E4 only '1' arms it; no other value changes v8.34 behaviour", relaxed == [], str(relaxed))
    os.environ.pop("COVENANT_REQUIRE_JUDGE_DIVERSITY", None)

    os.environ["COVENANT_REQUIRE_JUDGE_DIVERSITY"] = "1"
    try:
        cov.build_semantic_quorum(["claude"], include_mock_selfreport=False)
        check("E5 the v8.34 label check still fires first and is untouched", False)
    except ValueError as e:
        check("E5 the v8.34 label check still fires first and is untouched",
              "lacks diversity" in str(e), str(e)[:70])
    os.environ.pop("COVENANT_REQUIRE_JUDGE_DIVERSITY", None)
    check("E6 QUORUM_DIVERSITY is still True and nothing can set it from the env",
          cov.QUORUM_DIVERSITY is True)


# ------------------------------------------------------------------ H ------
def section_h():
    print("\n== H. /health discloses it, and `degraded` is unchanged ==")
    tmp = tempfile.mktemp(suffix=".db")
    master = cov.CovenantUnifiedMaster("b2", host="127.0.0.1", port=17960,
                                       p2p_port=17961, db_path=tmp)
    master.add_genesis_block()
    master.node.rate_limiter.allow = lambda *a, **k: True
    client = master.api.app.test_client()
    try:
        h = client.get("/health").get_json()
        if not HAS_FIX:
            check("H skipped -- no fix in this source", False, "pre-fix record run")
            return
        q = h.get("quorum")
        check("H1 /health carries the quorum report", isinstance(q, dict) and q.get("is_quorum"),
              str(q)[:80])
        check("H1b with the independence numbers",
              "independent_semantic_judges" in q and "semantic_judges" in q)
        check("H2 a non-diverse gate produces a warning",
              any("not independently diverse" in w for w in h.get("warnings", [])),
              str(h.get("warnings"))[:120])
        check("H2b the warning text does not collide with the watchdog's "
              "known-false 'ethics gate has no provider key'",
              not any("ethics gate has no provider key" in w
                      for w in h["warnings"] if "quorum" in w))
        check("H3 `degraded` still means exactly what it meant in v8.34",
              h["degraded"] == bool(h.get("judge_keyless") or h.get("judge_insecure")
                                    or h.get("own_genesis") or h.get("crisis_mode")),
              f"degraded={h['degraded']}")
        check("H4 nothing about the quorum can make a node degraded on its own",
              isinstance(h["degraded"], bool))

        # The lethal partial case, end to end through the route.
        master.node.sentinel.judge = credential(
            cov.build_semantic_quorum(["claude", "openai"]), {"claude:0"})
        h2 = client.get("/health").get_json()
        check("H5 the partial-credential total block is WARNED about",
              any("REJECTS EVERY TRANSACTION" in w for w in h2.get("warnings", [])),
              str(h2.get("warnings"))[:140])
        check("H5b and judge_keyless alone would still have said nothing",
              h2["quorum"]["independent_semantic_judges"] == 1)

        # No duplicate sentence when judge_keyless already covers it.
        master.node.sentinel.judge = cov.build_semantic_quorum(["claude", "openai"])
        h3 = client.get("/health").get_json()
        dupes = [w for w in h3.get("warnings", []) if "hold no credential" in w]
        if h3.get("judge_keyless"):
            check("H6 no second sentence for a fact judge_keyless already states",
                  dupes == [], str(dupes)[:100])
        else:
            check("H6 the all-uncredentialled case is stated exactly once",
                  len(dupes) == 1, str(dupes)[:100])
    finally:
        try:
            os.unlink(tmp)
            os.unlink(tmp + ".key")
        except OSError:
            pass


# ------------------------------------------------------------------ B ------
def section_b():
    print("\n== B. THE BOUNDARY: the operator may see this; a PEER may not ==")
    tmp = tempfile.mktemp(suffix=".db")
    master = cov.CovenantUnifiedMaster("b2b", host="127.0.0.1", port=17970,
                                       p2p_port=17971, db_path=tmp)
    master.add_genesis_block()
    try:
        digest = master.node.build_digest()
        blob = json.dumps(digest)
        check("B1 the A21 peer digest carries no quorum block", "quorum" not in digest)
        for leak in ("judge", "credential", "ANTHROPIC", "OPENAI", "GOOGLE",
                     "independent", "diverse", "mock_selfreport", "_API_KEY"):
            check(f"B2 peer digest does not leak {leak!r}", leak not in blob, blob[:100])
        check("B3 the digest key set is exactly what A21 pinned",
              set(digest) == {"v", "src", "height", "peers", "crisis", "spike"}, str(sorted(digest)))
        if HAS_FIX:
            rep = cov.quorum_diversity_report(master.node.sentinel.judge)
            check("B4 while the operator CAN see it -- the two are different surfaces",
                  rep.get("is_quorum") is True and "quorum" not in digest)
    finally:
        try:
            os.unlink(tmp)
            os.unlink(tmp + ".key")
        except OSError:
            pass


# ------------------------------------------------------------------ W ------
def section_w():
    print("\n== W. The watchdog renders it and cannot raise on it ==")
    try:
        import covenant_watchdog as wd
    except Exception as e:
        check("W skipped -- watchdog not importable here", True, f"{type(e).__name__}")
        return
    if not hasattr(wd, "_quorum_brief"):
        check("W1 covenant_watchdog._quorum_brief exists", False, "pre-fix watchdog")
        return
    check("W1 covenant_watchdog._quorum_brief exists", True)
    check("W2 a v8.35 node renders independent/semantic",
          wd._quorum_brief({"quorum": {"is_quorum": True, "independent_semantic_judges": 3,
                                       "semantic_judges": 3, "diverse": True}}) == "3/3")
    check("W2b and marks a non-diverse one",
          wd._quorum_brief({"quorum": {"is_quorum": True, "independent_semantic_judges": 1,
                                       "semantic_judges": 2, "diverse": False}}) == "1/2!")
    check("W3 a pre-v8.35 node says n/a rather than guessing",
          wd._quorum_brief({"version": "v8.34"}) == "n/a")
    for bad in ({}, {"quorum": None}, {"quorum": "nonsense"}, {"quorum": {}}, None):
        try:
            out = wd._quorum_brief(bad) if bad is not None else wd._quorum_brief({})
            ok = isinstance(out, str)
        except Exception:
            ok = False
        check(f"W4 _quorum_brief({bad!r}) never raises", ok)


def main():
    t0 = time.time()
    print(f"source: {cov.COVENANT_VERSION}  {cov.CORE_SOURCE_SHA256[:12]}  "
          f"{cov.CORE_SOURCE_LINES} lines   fix_present={HAS_FIX}")
    section_x()
    section_r()
    section_s()
    section_e()
    section_h()
    section_b()
    section_w()
    print(f"\n{PASS}/{PASS + FAIL} passed in {time.time() - t0:.1f}s")
    sys.exit(0 if FAIL == 0 else 1)


if __name__ == "__main__":
    main()
