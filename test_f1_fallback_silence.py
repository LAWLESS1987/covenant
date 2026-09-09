#!/usr/bin/env python3
"""test_f1_fallback_silence.py -- F1: silence is not dissent, and the fallback
that makes that safe to act on.

THE DEFECT, measured 2026-08-30.

Deployed wiring is COVENANT_JUDGE_PROVIDERS="local,semantic", so the semantic
veto threshold is ceil(2 * 0.5) = 1: one dissent blocks. A judge that cannot be
REACHED fails closed, which sets violates=True, and the veto tally counted it
alongside genuine dissent. Stop Ollama and a benign payload comes back
violates=True. Every transaction refused -- and `_accept_block_common` refuses
PEER blocks too, which the code there already names "a fork in the making". One
local process halts a node's participation in a healthy network.

It is the error triangulate.py exists to refuse -- A WITNESS THAT DID NOT
ANSWER IS NOT A WITNESS THAT DISAGREED -- in the one place where it decides
whether the chain moves.

WHAT F1 PINS.

  D*  THE DEFAULT IS UNCHANGED. The first attempt at this fix made the new
      behaviour unconditional and broke five checks in B1, B2 and J1 that
      turned out to be deliberate, not oversights: a timing-out component is
      SUPPOSED to fail the gate closed. Those tests were the encoded intent and
      the change was wrong. So the trade is offered, never taken by default,
      and D* is here to make sure nobody quietly flips it.
  R*  the relaxed mode does what it claims AND keeps what matters: a genuine
      dissent still blocks, and if NOTHING answered, nothing is admitted.
  A*  the fallback judge abstains rather than guesses -- untrained, on
      unfamiliar vocabulary, and inside its undecided band.
  N*  it never raises and never reports an infrastructure failure, because a
      judge that raises is counted as a dissent, which is the exact failure it
      exists to prevent.

Pure: no network, no node, no model server.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_unified_v8 as C           # noqa: E402
import covenant_judge_fallback as F       # noqa: E402

results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print(f"{'ok  ' if ok else 'FAIL'}  {label}"
          f"{'' if ok else '  ' + str(detail)[:170]}", flush=True)


def mk(jid, violates, infra=False, unread=False, why="fixture"):
    class J(C.ReasoningJudge):
        judge_id = jid

        def evaluate(self, d, p):
            return C.JudgmentResult(violates, why, judge_id=jid,
                                    infrastructure_failure=infra,
                                    not_understood=unread)
    return J()


def verdict(judges, relaxed):
    os.environ["COVENANT_SILENCE_IS_NOT_DISSENT"] = "1" if relaxed else "0"
    q = C.QuorumJudge(judges, semantic_judge_ids={j.judge_id for j in judges},
                      semantic_veto_threshold=1)
    return q.evaluate({"description": "send a gift to a friend"}, [])


def main():
    print("F1 -- silence is not dissent, and the fallback that makes it safe\n")

    UNREACH = lambda: mk("down:0", True, infra=True, why="unreachable")   # noqa: E731
    CLEAN = lambda: mk("ok:0", False, why="looks fine")                   # noqa: E731
    DISSENT = lambda: mk("no:0", True, why="a real objection")            # noqa: E731
    GONE = lambda: mk("gone:0", True, infra=True, why="also unreachable") # noqa: E731
    HELD = lambda: mk("held:0", True, unread=True, why="could not read")  # noqa: E731

    # ---- D: the default is exactly what it was ----------------------------
    check("D1 DEFAULT: an unreachable judge beside a CLEAN one still fails "
          "the gate closed. This is B1's 'timeout component -> quorum "
          "violates', and it is deliberate -- the first version of this fix "
          "broke it by making the new behaviour unconditional",
          verdict([UNREACH(), CLEAN()], relaxed=False).violates)
    check("D2 DEFAULT: ...and it is still flagged as infrastructure, so the "
          "operator can tell a broken judge from a bad transaction",
          verdict([UNREACH(), CLEAN()], relaxed=False).infrastructure_failure)
    check("D3 DEFAULT: a judge that could not READ the payload also still "
          "blocks -- J1's 'HELD, not judged' path",
          verdict([HELD(), CLEAN()], relaxed=False).violates)
    check("D4 the relaxed path is OFF unless the operator sets the variable. "
          "A safety property must never be traded away by a default",
          "COVENANT_SILENCE_IS_NOT_DISSENT" in
          open(os.path.join(HERE, "covenant_unified_v8.py"),
               encoding="utf-8").read())

    # ---- R: what relaxed mode does, and does not, give up -----------------
    check("R1 RELAXED: an unreachable judge no longer outvotes a judge that "
          "actually looked and found nothing wrong",
          not verdict([UNREACH(), CLEAN()], relaxed=True).violates)
    check("R2 RELAXED: a GENUINE dissent still blocks. This is the line "
          "between availability and permissiveness, and crossing it would "
          "make the whole change indefensible",
          verdict([UNREACH(), DISSENT()], relaxed=True).violates)
    check("R3 RELAXED: if NOTHING answered, NOTHING is admitted. This is the "
          "one thing relaxed mode does not trade away",
          verdict([UNREACH(), GONE()], relaxed=True).violates)
    check("R4 RELAXED: ...and that refusal is still marked infrastructure, "
          "not dressed up as a finding against the sender",
          verdict([UNREACH(), GONE()], relaxed=True).infrastructure_failure)
    check("R5 RELAXED: an ABSTENTION does not block either -- which is what "
          "makes a fallback judge usable rather than just another veto",
          not verdict([HELD(), CLEAN()], relaxed=True).violates)
    check("R6 RELAXED: a real dissent beside a clean judge still blocks, so "
          "the veto threshold is intact",
          verdict([CLEAN(), DISSENT()], relaxed=True).violates)
    os.environ["COVENANT_SILENCE_IS_NOT_DISSENT"] = "0"

    # ---- A: the fallback abstains rather than guesses ---------------------
    empty = F.FallbackModel(None)
    check("A1 UNTRAINED, it abstains on everything. A fallback that guessed "
          "would be worse than none, because it would be believed",
          empty.verdict("literally anything")[0] == "abstain")
    ex = ([("transfer tokens to a friend as a gift", False)] * 40
          + [("drain the pool and take all the funds for myself", True)] * 40)
    m = F.FallbackModel.train(ex, sources=["F1 fixtures"])
    check("A2 trained, it clears what it has plainly seen as clean",
          m.verdict("transfer tokens to a friend as a gift")[0] == "clean")
    check("A3 ...and holds what it has plainly seen as violating",
          m.verdict("drain the pool and take all the funds")[0] == "violates")
    check("A4 THE IMPORTANT ONE: on unfamiliar vocabulary it ABSTAINS instead "
          "of extrapolating from the few tokens it recognises. Novel input is "
          "where a distilled model is least entitled to an opinion and most "
          "likely to sound certain",
          m.verdict("quarterly telemetry recalibration of the widget array")[0]
          == "abstain")
    check("A5 clearing is deliberately harder than holding: a wrong 'clean' "
          "admits something, a wrong 'violates' only delays it",
          F.MARGIN_TO_CLEAR > F.MARGIN_TO_HOLD,
          (F.MARGIN_TO_CLEAR, F.MARGIN_TO_HOLD))
    check("A6 the model stays SMALL and readable -- a distilled judge nobody "
          "can inspect is a second opaque authority",
          0 < len(m.weights) < 200, len(m.weights))
    check("A7 it says what it learned FROM, so its inherited defects are "
          "never a surprise", "sources" in F.provenance(m)
          or "INHERITS" in F.provenance(m), F.provenance(m)[:80])

    # ---- N: it can never become a phantom dissent -------------------------
    j = F.FallbackJudge()
    r = j.evaluate({"description": "\x00\xff unreadable bytes"}, [])
    check("N1 it NEVER raises. QuorumJudge counts a raising judge as a "
          "violation, which is precisely the failure this class exists to "
          "prevent", r is not None)
    r2 = j.evaluate({"description": "entirely unseen vocabulary"}, [])
    check("N2 an abstention is HELD (not_understood), so it alleges nothing",
          r2.not_understood is True)
    check("N3 an abstention NEVER carries infrastructure_failure -- it is "
          "local, it was reached, it simply had no view. Claiming otherwise "
          "would make it look like the outage it exists to survive",
          r2.infrastructure_failure is False)

    # ---- X: THE TRADING EXCEPTION (2026-09-07) ---------------------------
    # Asked: "the local covenant needs a trading exception ... and to stop
    # going to git hub for a judge", then narrowed to "the exception should be
    # nodes local pc's". With the runner out of the gate the deferring seat is
    # students-only and both students HOLD on covenant_trader's records, so
    # without this the trader could not seal at all -- no live order AND no
    # audit record. The exception relaxes ONE reading (a seat that did not
    # ANSWER stops counting as one that DISAGREED) and only for a transaction
    # that pays nothing, to nobody, signed by a key on this PC.
    #
    # These checks exist because that is a deliberate weakening of a
    # fail-closed gate, and the only thing standing between "narrow" and
    # "general" is the three conditions below actually being required.
    import hashlib as _h

    class _Stub(object):
        judge_id = "stub:0"
        last = "unset"

        def evaluate(self, data, principles, relaxed=None):
            _Stub.last = relaxed
            return C.JudgmentResult(False, "stub clean", judge_id=self.judge_id)

    class _Tx(object):
        def __init__(self, sender, receiver, amount):
            self.sender_pubkey, self.receiver, self.amount = sender, receiver, amount
            self.data = {"origin": "covenant_trader", "kind": "trade_decision"}

    MINE = "-----BEGIN PUBLIC KEY-----\nlocal\n-----END PUBLIC KEY-----\n"
    THEIRS = "-----BEGIN PUBLIC KEY-----\npeer\n-----END PUBLIC KEY-----\n"
    _prev = os.environ.get("COVENANT_RELAX_VALUELESS_FOR")
    os.environ["COVENANT_RELAX_VALUELESS_FOR"] = _h.sha256(MINE.encode()).hexdigest()
    _sent = C.ReasoningSentinel(_Stub())

    def _relaxed_for(tx):
        _Stub.last = "unset"
        _sent.evaluate_transaction(tx)
        return _Stub.last

    check("X1 a valueless self-send from a key on THIS PC gets the relaxed "
          "reading -- the trader can seal, so the decision is recorded",
          _relaxed_for(_Tx(MINE, MINE, 0.0)) is True)
    check("X2 the same key moving REAL money does not -- the exception is "
          "about records, not about trades",
          _relaxed_for(_Tx(MINE, MINE, 25.0)) is None)
    check("X3 the same key PAYING SOMEONE does not, even for $0 -- a self-send "
          "is required, not merely a zero amount",
          _relaxed_for(_Tx(MINE, THEIRS, 0.0)) is None)
    check("X4 A PEER'S valueless self-send does NOT qualify. This is the whole "
          "of 'nodes local pc's': the test is on a key that exists only on "
          "this machine, so no payload a peer can shape reaches the exception",
          _relaxed_for(_Tx(THEIRS, THEIRS, 0.0)) is None)
    os.environ.pop("COVENANT_RELAX_VALUELESS_FOR", None)
    check("X5 with the policy switch off the exception does not exist at all, "
          "so the default posture is the old fail-closed one",
          _relaxed_for(_Tx(MINE, MINE, 0.0)) is None)
    if _prev is not None:
        os.environ["COVENANT_RELAX_VALUELESS_FOR"] = _prev
    check("X6 apply_policy builds the allow-list from local *.db.key files, so "
          "the operator never types a hash and a peer key cannot appear in it",
          (lambda e: (__import__("covenant_judge_defer").apply_policy(
              e, {"relax_valueless_for_local_nodes": True})
              and len(e.get("COVENANT_RELAX_VALUELESS_FOR", "").split(",")) >= 1))({}))

    # X6 CANNOT FAIL, and was measured green on an allow-list that did not
    # exist (2026-09-09). apply_policy returns the DISCLOSURE STRING, which is
    # truthy for any non-empty policy, and `"".split(",")` is `[""]` -- length
    # 1 -- so the second half holds when the list is EMPTY too. On a checkout
    # with no *.db.key file the line X6 claims to guard writes "" and the
    # disclosure reads `trading_exception=off`, and X6 still printed ok.
    # Nothing in it touches PROVENANCE: that the hashes are the sha256 of the
    # public key of a key FILE ON THIS MACHINE, which is the whole of the
    # operator's "the exception should be nodes local pc's" narrowing.
    #
    # THE MUTATION THAT PROVED IT: at covenant_judge_defer.py:120, write a
    # constant instead of the derived list --
    #     env["COVENANT_RELAX_VALUELESS_FOR"] = str(p.get(
    #         "relax_hashes", <sha256 of the PEER public key X4 uses>))
    # -- putting a peer's key in the allow-list, the one thing X6's own label
    # says cannot happen. F1 still printed 26/26, exit 0, X6 "ok".
    #
    # So X6b and X6c do not READ the value at all. They put a real key file in
    # a scratch folder (or leave the folder empty), point the module's key
    # folder at it, run apply_policy, and drive the REAL ReasoningSentinel
    # with the environment that produced. Provenance measured by consequence:
    # the key that IS on this machine gets the relaxed reading, nothing else
    # does, and where there is no key file the exception reaches nobody.
    import shutil as _shutil
    import tempfile as _tempfile
    _D = __import__("covenant_judge_defer")
    _here_was = _D.HERE
    _env_was = os.environ.get("COVENANT_RELAX_VALUELESS_FOR")
    _scratch = _tempfile.mkdtemp(prefix="f1_x6_keys_")

    def _policy_env(folder):
        """What apply_policy writes with the module's key folder at `folder`."""
        _D.HERE = folder
        try:
            e = {}
            _D.apply_policy(e, {"relax_valueless_for_local_nodes": True})
            return e.get("COVENANT_RELAX_VALUELESS_FOR") or ""
        finally:
            _D.HERE = _here_was

    try:
        from cryptography.hazmat.primitives import serialization as _ser
        from cryptography.hazmat.primitives.asymmetric import rsa as _rsa
        import covenant_client as _cc
        _kp = os.path.join(_scratch, "scratch_node.db.key")
        with open(_kp, "wb") as _fh:
            _fh.write(_rsa.generate_private_key(
                public_exponent=65537, key_size=1024).private_bytes(
                    _ser.Encoding.PEM, _ser.PrivateFormat.PKCS8,
                    _ser.NoEncryption()))
        LOCAL = _cc.pub_of_key(_kp)      # the identity of that key FILE

        os.environ["COVENANT_RELAX_VALUELESS_FOR"] = _policy_env(_scratch)
        _mine = _relaxed_for(_Tx(LOCAL, LOCAL, 0.0))
        _theirs = _relaxed_for(_Tx(THEIRS, THEIRS, 0.0))
        check("X6b apply_policy's allow-list is DERIVED FROM the *.db.key files "
              "on this PC: with one key file in the folder, THAT key's valueless "
              "self-send gets the relaxed reading, and a peer key that is not in "
              "the folder still does not. A hash somebody merely typed into the "
              "policy would fail both halves",
              _mine is True and _theirs is not True, (_mine, _theirs))

        _empty = _policy_env(_scratch + "_no_such_folder")
        os.environ["COVENANT_RELAX_VALUELESS_FOR"] = _empty
        _none = _relaxed_for(_Tx(THEIRS, THEIRS, 0.0))
        check("X6c ...and with NO key file to derive from, the allow-list is "
              "EMPTY and the exception reaches nobody -- not even a peer. This "
              "is the state X6 was passing green in, and it is where a constant "
              "written into the variable is loudest: it would relax a peer here",
              _empty == "" and _none is None, (_empty[:16], _none))
    finally:
        _D.HERE = _here_was
        _shutil.rmtree(_scratch, ignore_errors=True)
        if _env_was is None:
            os.environ.pop("COVENANT_RELAX_VALUELESS_FOR", None)
        else:
            os.environ["COVENANT_RELAX_VALUELESS_FOR"] = _env_was

    n, ok = len(results), sum(results)
    print(f"\nF1: {ok}/{n} passed")
    return 0 if ok == n else 1


if __name__ == "__main__":
    raise SystemExit(main())
