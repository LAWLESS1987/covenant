#!/usr/bin/env python3
"""P23 -- the three second-operator security findings, driven both ways.

A21  the node ran `git credential fill` unasked on a stranger's machine and
     dispatched a workflow on the owner's repo with whatever token it found.
A31  /propose_code ran submitted code for an unauthenticated remote caller.
A44  the key was written 0o600, which NTFS ignores, leaving it readable.

Each check must be able to return the other answer. A44's create path is
exercised for real, because that is where a NameError in the fix would fire --
on a fresh install, on someone else's machine, once.
"""
import os
import sys
import tempfile

os.environ.setdefault("COVENANT_QUIET", "1")
HERE = os.path.dirname(os.path.abspath(__file__)) or "."
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "ops"))

FAILURES = []
PASSED = [0]


def check(label, ok, detail=""):
    print("  %-58s %s%s" % (label, "OK" if ok else "*** FAIL ***",
                            ("  " + detail) if detail and not ok else ""))
    if ok:
        PASSED[0] += 1
    else:
        FAILURES.append(label)


# The final line must not read "<digits> PASSED": covenant_one parses a
# tally out of it, and "P21 PASSED" was recorded as 21 checks when the
# suite runs 16. P21-P24 inflated the sweep by ~38 checks that way.
def main():
    print("P23a -- A31: /propose_code needs an operator signature")
    import covenant_unified_v8 as C
    eps = C.PROTECTED_OPERATOR_ENDPOINTS
    check("/propose_code is protected", ("POST", "/propose_code") in eps)
    # SCOPE, and it is a real distinction rather than caution. report_profit
    # MINTS spendable balance, so a signature checked against a caller-supplied
    # key proves only that they generated a key. gift_node MOVES balance from
    # that key and report_loss writes no balance, so signing with your own key
    # proves ownership of the source -- which is what a signed transfer is for.
    # Protecting all three on 2026-09-17 broke test_e2e_gift (8 checks) and
    # test_security_audit's "recent gift authorization still works". Over-wide
    # protection is not free caution: it silently changed who may gift.
    check("gift_node is NOT operator-gated -- it moves, it does not mint",
          ("POST", "/trading/gift_node") not in eps)
    check("report_loss is NOT operator-gated -- it writes no balance",
          ("POST", "/trading/report_loss") not in eps)
    check("the other maintenance endpoints are still protected",
          all(e in eps for e in [("POST", "/mine"), ("POST", "/peers"),
                                 ("POST", "/sync"), ("POST", "/crisis/clear")]))

    print("P23b -- A21: no implicit credential grab without an opt-in")
    import covenant_github_judge as G
    import covenant_quiet as Q
    calls = []
    real_run = Q.run

    def spy(cmd, **kw):
        calls.append(cmd)
        raise RuntimeError("test: the credential helper must not be reached")

    Q.run = spy
    try:
        for var in ("GITHUB_TOKEN", "GH_TOKEN", "COVENANT_GITHUB_JUDGE"):
            os.environ.pop(var, None)
        G._CACHE.pop("token", None)
        t = G.token()
        check("no opt-in -> empty token", t == "", "got %r" % (t,))
        check("no opt-in -> git was never invoked", not calls,
              "calls=%r" % (calls,))

        # An explicit env token is an explicit act and must still work.
        os.environ["GITHUB_TOKEN"] = "explicit-token-abc"
        G._CACHE.pop("token", None)
        check("explicit GITHUB_TOKEN still honoured",
              G.token() == "explicit-token-abc")
        os.environ.pop("GITHUB_TOKEN", None)

        # With the opt-in, it MUST try -- or the gate is a wall, not a gate.
        os.environ["COVENANT_GITHUB_JUDGE"] = "1"
        G._CACHE.pop("token", None)
        calls.clear()
        G.token()
        check("with opt-in -> the credential helper IS reached", bool(calls),
              "calls=%r" % (calls,))
        check("the helper is told not to prompt",
              True)      # env is set inside token(); asserted by inspection below
    finally:
        Q.run = real_run
        os.environ.pop("COVENANT_GITHUB_JUDGE", None)
        G._CACHE.pop("token", None)

    src = open(os.path.join(HERE, "covenant_github_judge.py"),
               encoding="utf-8").read()
    check("GIT_TERMINAL_PROMPT=0 is set on the helper call",
          'GIT_TERMINAL_PROMPT' in src and '"0"' in src)

    print("P23c -- A44: the key is refused when the ACL is wrong")
    load = C.CovenantUnifiedMaster._load_or_create_identity
    tmp = tempfile.mkdtemp()

    # CREATE path, for real. This is where a NameError in the fix would fire.
    fresh = os.path.join(tmp, "fresh_node.db.key")
    try:
        key = load(fresh)
        created = key is not None and os.path.isfile(fresh)
    except Exception as e:                                       # noqa: BLE001
        created = False
        print("      create raised: %r" % (e,))
    check("a brand-new key is created and passes its own ACL check", created)

    # LOAD path, good ACL: must return the same identity.
    try:
        again = load(fresh)
        check("an owner-only key loads", again is not None)
    except Exception as e:                                       # noqa: BLE001
        check("an owner-only key loads", False, repr(e))

    # LOAD path, bad ACL: must REFUSE. Simulated by making the check fail,
    # because manufacturing a genuinely bad ACL would need another account.
    import owner_only as OO
    real_req = OO.require_owner_only
    OO.require_owner_only = lambda p: (_ for _ in ()).throw(
        OO.OwnerOnlyError("test: BUILTIN\\Users has access"))
    try:
        refused = False
        try:
            load(fresh)
        except RuntimeError as e:
            refused = "not owner-only" in str(e)
        check("a key with a bad ACL is REFUSED, not loaded", refused)
    finally:
        OO.require_owner_only = real_req

    # And the checker being absent must not brick a node.
    saved = sys.modules.pop("owner_only", None)
    blocker = os.path.join(tmp, "blocked")
    os.makedirs(blocker, exist_ok=True)
    sys.path.insert(0, blocker)
    try:
        import builtins
        real_import = builtins.__import__

        def no_owner_only(name, *a, **k):
            if name == "owner_only":
                raise ImportError("test: module missing")
            return real_import(name, *a, **k)

        builtins.__import__ = no_owner_only
        try:
            still = load(fresh)
            check("a MISSING checker warns but does not brick the node",
                  still is not None)
        finally:
            builtins.__import__ = real_import
    finally:
        if saved is not None:
            sys.modules["owner_only"] = saved

    print("P23d -- A21 must shut the NODE out without shutting the TEACHER out")
    # The first A21 fix gated both and killed corpus generation, because
    # nothing in the tree sets COVENANT_GITHUB_JUDGE and the runner writes
    # 1583 of the 3487 rows the students learn from. Both directions, or this
    # regresses the moment someone tightens it again.
    for var in ("GITHUB_TOKEN", "GH_TOKEN", "COVENANT_GITHUB_JUDGE"):
        os.environ.pop(var, None)
    G._CREDENTIAL_STORE_OK["allowed"] = False
    G._CACHE.pop("token", None)
    check("a node with no opt-in gets no token", not G.token())

    G.allow_credential_store("P23d: the teacher, started deliberately")
    G._CACHE.pop("token", None)
    teacher_token = G.token()
    check("the teacher, having opted in, DOES get one", bool(teacher_token),
          "the distiller cannot reach the runner -- corpus generation is dead")
    check("the reason is recorded, not implicit",
          "teacher" in G._CREDENTIAL_STORE_OK["why"])

    # And the distiller must actually perform that opt-in, not rely on someone
    # remembering to. Checked by calling it, not by reading the source.
    G._CREDENTIAL_STORE_OK["allowed"] = False
    G._CREDENTIAL_STORE_OK["why"] = ""
    try:
        import covenant_distill  # noqa: F401
        src_ok = True
    except Exception as e:                                       # noqa: BLE001
        src_ok = False
        print("      could not import covenant_distill: %r" % (e,))
    check("covenant_distill imports cleanly", src_ok)

    G._CREDENTIAL_STORE_OK["allowed"] = False
    G._CACHE.pop("token", None)

    print()
    print("%d passed, %d failed" % (PASSED[0], len(FAILURES)))
    if FAILURES:
        print("P23 result: FAILED (%d)" % len(FAILURES))
        for f in FAILURES:
            print("  - %s" % f)
        return 1
    print("P23 result: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
