"""SI1 (A409/G, 2026-11-04): covenant_state gives tests an explicit, injectable state root and a guard that
makes a write to live ops/ RAISE instead of silently leaking (the A409 fixture-leak class). Driven BOTH WAYS:
a live-ops write under isolate() raises; the same write pointed under the test root passes. No live file is
ever created by this suite."""
import os, sys, tempfile, shutil, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import covenant_state as cs

REAL_OPS = os.path.join(cs.HERE, "ops")
_dirs = []
def _tmp():
    d = tempfile.mkdtemp(prefix="si1_"); _dirs.append(d); return d


def test_root_default_is_repo():
    os.environ.pop(cs.ROOT_ENV, None)
    assert cs.root() == cs.HERE


def test_live_write_raises_inside_isolate():
    canary = os.path.join(REAL_OPS, "si1_canary_DO_NOT_CREATE.jsonl")
    with cs.isolate(_tmp()):
        raised = False
        try:
            open(canary, "w").close()
        except cs.IsolationError:
            raised = True
        assert raised, "a write to live ops/ did not raise under isolate()"
    assert not os.path.exists(canary), "the guard let a live file be created"


def test_under_root_write_allowed():
    with cs.isolate(_tmp()):
        p = cs.ops("x.jsonl")                       # resolves under the test root
        with open(p, "w") as f:
            f.write("ok")
        assert os.path.exists(p) and os.path.realpath(p).startswith(os.path.realpath(cs.root())), p


def test_both_ways_same_filename():
    # the break-test: the SAME file name raises under real ops/, passes under the test root
    with cs.isolate(_tmp()) as tr:
        try:
            open(os.path.join(REAL_OPS, "improve_candidates.jsonl"), "a").close()
            assert False, "live ledger write should have raised"
        except cs.IsolationError:
            pass
        with open(os.path.join(tr, "ops", "improve_candidates.jsonl"), "a") as f:  # under the root -> fine
            f.write("")


def test_read_not_blocked():
    with cs.isolate(_tmp()):
        try:
            open(os.path.join(REAL_OPS, "si1_nonexistent.txt"), "r")
            assert False, "expected FileNotFoundError"
        except cs.IsolationError:
            assert False, "a READ of a live path was blocked"
        except FileNotFoundError:
            pass                                    # reached the real open -> reads are not guarded


def test_open_restored_after_isolate():
    with cs.isolate(_tmp()):
        pass
    import builtins
    # outside isolate: a write to an ordinary temp path works, and a live-ops path does NOT raise IsolationError
    t = os.path.join(_tmp(), "free.txt")
    with builtins.open(t, "w") as f:
        f.write("ok")
    assert os.path.exists(t)
    assert cs.ROOT_ENV not in os.environ or os.environ.get(cs.ROOT_ENV) != "LEAKED"


def test_child_env_carries_root():
    with cs.isolate(_tmp()) as tr:
        env = cs.child_env({"EXTRA": "1"})
        assert env[cs.ROOT_ENV] == tr and env["EXTRA"] == "1"
    env2 = cs.child_env(tmp_root="/some/where")
    assert env2[cs.ROOT_ENV] == "/some/where"


def test_ops_follows_root():
    os.environ.pop(cs.ROOT_ENV, None)
    assert os.path.realpath(cs.ops("a.jsonl")) == os.path.realpath(os.path.join(cs.HERE, "ops", "a.jsonl"))
    with cs.isolate(_tmp()) as tr:
        assert os.path.realpath(cs.ops("a.jsonl")) == os.path.realpath(os.path.join(tr, "ops", "a.jsonl"))


def _main():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for fn in fns:
        try:
            fn(); print("PASS", fn.__name__); passed += 1
        except Exception:
            print("FAIL", fn.__name__); traceback.print_exc()
    for d in _dirs:
        shutil.rmtree(d, ignore_errors=True)
    print("SI1: %d/%d passed" % (passed, len(fns)))
    return 0 if passed == len(fns) else 1


if __name__ == "__main__":
    sys.exit(_main())
