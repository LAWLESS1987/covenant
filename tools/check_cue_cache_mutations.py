#!/usr/bin/env python3
"""Prove the offline guards fail against deliberately broken in-memory copies."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
MUTATIONS = (
    ("route discards caller/privacy scope", "test_a263_private_teacher.py", """
import covenant_unified_v8 as c
from pathlib import Path
source = Path(c.__file__).read_text(encoding='utf-8')
source = source.replace('_cr.conversation_scope(addr, private)', '_cr.conversation_scope("all", False)')
exec(compile(source, c.__file__, 'exec'), c.__dict__)
"""),
    ("shared caller state", "test_cr1_conv_reflex.py", """
import covenant_tetsu_conv_reflex as c
c._scoped_path = lambda path, scope: path
"""),
    ("metadata-only basis memo", "test_vc1_verdict_cache.py", """
import os
import covenant_verdict_cache as c
original = c.basis_version
memo = {}
def stale(paths=c.DEFAULT_BASIS_PATHS, root=None):
    paths = tuple(paths)
    def stat(p):
        try:
            s = os.stat(p if os.path.isabs(p) else os.path.join(root or c._REPO, p))
            return (s.st_size, s.st_mtime_ns)
        except OSError:
            return None
    key = (paths, root, tuple(stat(p) for p in paths))
    if key not in memo:
        memo[key] = original(paths, root)
    return memo[key]
c.basis_version = stale
"""),
    ("metadata-only artifact identity", "test_vc1_verdict_cache.py", """
import os
import covenant_verdict_cache as c
def stale(model, endpoint=None, models_dir=None):
    ep = os.environ.get('COVENANT_LOCAL_JUDGE_URL', '') if endpoint is None else str(endpoint)
    d = models_dir or os.path.join(c._REPO, 'models')
    for p in (os.path.join(d, str(model)), os.path.join(d, str(model) + '.gguf')):
        try:
            s = os.stat(p)
            return ep + str((s.st_size, s.st_mtime_ns))
        except OSError:
            continue
    return ep + '::artifact=unknown'
c.artifact_version = stale
"""),
    ("broken counterfactual evidence", "test_cue_eval.py", """
import eval_conv_cues as e
original = e.evaluate
def broken():
    result = original()
    result['zero_spike_calls'] = 0
    return result
e.evaluate = broken
"""),
    ("uncertain artifact bypass removed", "test_vc1_verdict_cache.py", """
import inspect
import covenant_judge_local as j
source = inspect.getsource(j._verdict_cache)
source = source.replace('if artifact.endswith(("::artifact=unstable", "::artifact=unreadable")):', 'if False:')
exec(source, j.__dict__)
"""),
    ("disabled cache still reads artifacts", "test_vc1_verdict_cache.py", """
import inspect
import covenant_judge_local as j
source = inspect.getsource(j._verdict_cache).replace('if _vc._disabled():', 'if False:')
exec(source, j.__dict__)
"""),
)


def main():
    missed = []
    for name, suite, patch in MUTATIONS:
        code = patch + "\nimport runpy\nrunpy.run_path(" + repr(suite) + ", run_name='__main__')\n"
        result = subprocess.run([sys.executable, "-B", "-c", code], cwd=ROOT,
                                capture_output=True, text=True, timeout=120)
        output = result.stdout + result.stderr
        # A syntax/import crash is not evidence that the guard caught a defect.
        caught = result.returncode != 0 and ("FAIL" in output or "AssertionError" in output)
        print(("CAUGHT " if caught else "MISSED ") + name)
        if not caught:
            print(output[-1500:])
            missed.append(name)
    print(f"mutations caught: {len(MUTATIONS) - len(missed)}/{len(MUTATIONS)}")
    return bool(missed)


if __name__ == "__main__":
    raise SystemExit(main())
