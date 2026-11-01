#!/usr/bin/env python3
"""test_hm1_hf_mirror.py -- HM1. tools/hf_mirror.py can no longer overwrite Hugging Face or bypass his opsec guard.

As first written it force-pushed every repo's full history from a hook-less clone (A396). Driven both ways here,
with local bare repositories standing in for Hugging Face (no network):
  HM1a  an empty remote receives the push; a remote that is an ancestor fast-forwards
  HM1b  a DIVERGED remote (it holds a commit we do not) is refused and left byte-for-byte as it was
  HM1c  a tag that would move on the remote is refused
  HM1d  a new commit carrying his LAN IP is refused by the opsec scan, and the remote is unchanged
  HM1e  an identifier the remote ALREADY holds is not re-scanned: a clean fast-forward on top of it goes through
  HM1f  covenant and threefold-memory are snapshot-only, never git-pushed
  HM1g  snapshot_to_hf refuses a file carrying his identifier before any upload
  HM1h  no `--force` remains in the tool's push path
"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "tools"))
import hf_mirror as HM            # noqa: E402

_results = []


def check(label, cond, detail=""):
    _results.append(bool(cond))
    print(f"{'ok   ' if cond else 'FAIL '} {label}{('  -- ' + str(detail)[:300]) if detail and not cond else ''}")


def git(*args, cwd=None):
    p = subprocess.run(["git"] + list(args), cwd=cwd, capture_output=True, text=True)
    return p.stdout.strip()


def commit(work, name, body):
    with open(os.path.join(work, name), "w") as fh:
        fh.write(body)
    git("add", name, cwd=work)
    git("-c", "user.name=hm1", "-c", "user.email=hm1@example.invalid", "commit", "-q", "-m", name, cwd=work)
    return git("rev-parse", "HEAD", cwd=work)


class StubOpsec:
    """The real scan's shape, with one planted identifier, so the guard is tested whatever this machine holds."""
    MARK = "hm1-planted-identifier-7c1f"

    def __init__(self):
        sys.path.insert(0, os.path.join(HERE, "tools"))
        import opsec_scan as O
        self.O = O

    def pair(self):
        return self.O, [("lan-ip", self.MARK)]


def main():
    base = tempfile.mkdtemp(prefix="hm1_")
    ops = StubOpsec().pair()

    def fresh(n):
        work = os.path.join(base, "work%s" % n)
        remote = os.path.join(base, "remote%s.git" % n)
        git("init", "-q", "-b", "main", work)
        git("init", "-q", "--bare", "-b", "main", remote)
        return work, remote

    # HM1a
    work, remote = fresh("a")
    tip = commit(work, "a.txt", "one\n")
    ok, why = HM.guarded_push(os.path.join(work, ".git"), remote, opsec=ops)
    check("HM1a an empty remote receives the push", ok and git("rev-parse", "main", cwd=remote) == tip, why)
    tip2 = commit(work, "b.txt", "two\n")
    ok, why = HM.guarded_push(os.path.join(work, ".git"), remote, opsec=ops)
    check("HM1a ...and a remote that is an ancestor fast-forwards", ok and git("rev-parse", "main", cwd=remote) == tip2,
          why)

    # HM1b
    work, remote = fresh("b")
    commit(work, "a.txt", "one\n")
    HM.guarded_push(os.path.join(work, ".git"), remote, opsec=ops)
    other = os.path.join(base, "otherb")
    git("clone", "-q", remote, other)
    hf_only = commit(other, "card.md", "an HF-only commit\n")
    git("push", "-q", "origin", "main", cwd=other)
    commit(work, "c.txt", "ours\n")
    ok, why = HM.guarded_push(os.path.join(work, ".git"), remote, opsec=ops)
    check("HM1b a DIVERGED remote is refused (unify first), and its HF-only commit is still its tip",
          not ok and "DIVERGED" in why and git("rev-parse", "main", cwd=remote) == hf_only, why)

    # HM1c
    work, remote = fresh("c")
    t1 = commit(work, "a.txt", "one\n")
    git("tag", "v1", cwd=work)
    HM.guarded_push(os.path.join(work, ".git"), remote, opsec=ops)
    commit(work, "b.txt", "two\n")
    git("tag", "-f", "v1", cwd=work)
    ok, why = HM.guarded_push(os.path.join(work, ".git"), remote, opsec=ops)
    check("HM1c a tag that would move is refused, and the remote's tag is unchanged",
          not ok and "MOVE" in why and git("rev-parse", "v1", cwd=remote) == t1, why)

    # HM1d
    work, remote = fresh("d")
    t1 = commit(work, "a.txt", "clean\n")
    HM.guarded_push(os.path.join(work, ".git"), remote, opsec=ops)
    commit(work, "leak.txt", "the address is %s\n" % StubOpsec.MARK)
    ok, why = HM.guarded_push(os.path.join(work, ".git"), remote, opsec=ops)
    check("HM1d a new commit carrying his identifier is REFUSED by the opsec scan, and the remote is unchanged",
          not ok and "opsec REFUSED" in why and git("rev-parse", "main", cwd=remote) == t1, why)

    # HM1e
    work, remote = fresh("e")
    commit(work, "old.txt", "already public: %s\n" % StubOpsec.MARK)
    git("push", "-q", remote, "main", cwd=work)                     # it reached the remote before the guard
    t2 = commit(work, "new.txt", "clean\n")
    ok, why = HM.guarded_push(os.path.join(work, ".git"), remote, opsec=ops)
    check("HM1e what the remote already holds is not re-scanned: a clean fast-forward on top goes through",
          ok and git("rev-parse", "main", cwd=remote) == t2, why)

    # HM1f
    check("HM1f covenant and threefold-memory are snapshot-only (never git-pushed)",
          {"covenant", "threefold-memory"} <= HM.SNAPSHOT_ONLY)

    # HM1g
    snap = os.path.join(base, "snap")
    os.makedirs(snap)
    with open(os.path.join(snap, "x.md"), "w") as fh:
        fh.write("carries %s\n" % StubOpsec.MARK)
    uploads = []

    class StubApi:                                                # no network: HF is never reached from HM1
        def __init__(self, *a, **k):
            pass

        def list_repo_files(self, *a, **k):
            return []
    # A stand-in module, not the real library: public CI and the Linux pre-push have no huggingface_hub, and
    # snapshot_to_hf imports it inside the function, so the stub is what it finds either way.
    import types
    stub = types.ModuleType("huggingface_hub")
    stub.upload_folder = lambda **kw: uploads.append(kw)
    stub.HfApi = StubApi
    saved = sys.modules.get("huggingface_hub")
    sys.modules["huggingface_hub"] = stub
    try:
        ok, why = HM.snapshot_to_hf("covenant", snap, "nobody/covenant", "no-token", opsec=ops)
    except Exception as e:                                        # noqa: BLE001 -- a crash is an answer too
        ok, why = None, "CRASHED %s: %s" % (type(e).__name__, e)
    finally:
        if saved is None:
            sys.modules.pop("huggingface_hub", None)
        else:
            sys.modules["huggingface_hub"] = saved
    check("HM1g snapshot_to_hf refuses a file carrying his identifier, before any upload",
          not ok and "opsec REFUSED" in why and not uploads, (why, uploads))

    # HM1h
    src = open(os.path.join(HERE, "tools", "hf_mirror.py"), encoding="utf-8").read()
    code = "\n".join(l for l in src.splitlines() if not l.strip().startswith("#") and '"""' not in l)
    check("HM1h no `--force` argument remains in the tool's code", '"--force"' not in code)

    passed, total = sum(_results), len(_results)
    print(f"\nHM1: {passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
