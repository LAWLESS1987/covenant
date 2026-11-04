"""covenant_state -- one explicit state root for tests, injectable through child processes (A409/G, 2026-11-04).

The problem (Codex's scan, and our own A409): tests were kept off live state by MATCHING THE FILENAME test_*
(A401). That is brittle -- a frozen default path (A409: covenant_improve_extract.extract froze the live
ops/improve_candidates.jsonl at import, and a test reached it through nightly() and appended 120 fixture rows
while printing green), a forgotten env override, or a separately launched real node all slip past a filename
check. Filename isolation also cannot cover a subprocess.

The fix here is two things that do NOT depend on the test's filename:
  1. an explicit state ROOT -- COVENANT_STATE_ROOT. A module that resolves its live paths through `ops(name)`
     writes under the root; a test (and, via `child_env()`, its subprocesses) points the root at a temp dir,
     so nothing it does -- frozen path or not -- lands in live ops/.
  2. a GUARD -- `isolate(tmp_root)` -- that, while active, makes ANY open-for-write to the real repo ops/
     (outside tmp_root) RAISE. A test wraps the code under test in it; the A409-class leak then fails LOUDLY
     instead of silently appending to the live ledger. It catches writes that never adopted `ops()` at all.

Adopting `ops()` across every ledger, and running the whole suite inside `isolate()`, is the follow-on; this
module is the mechanism and the guard, with a both-ways test (test_si1_isolation.py). The guard wraps BOTH
builtins.open (json.dump into an opened file) AND os.open (the atomic-write path -- tempfile.mkstemp +
os.replace -- that the improve-miner's seen-set write, the A409 ledger shape, actually uses). Remaining blind
spot: a write by a C extension that bypasses both -- named here, not hidden (rule 9)."""
import os
import contextlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT_ENV = "COVENANT_STATE_ROOT"


class IsolationError(RuntimeError):
    """A test wrote to live state inside isolate(). Raised before the write happens."""


def root():
    """The live-state root: COVENANT_STATE_ROOT if set (a test's temp dir), else the repo itself."""
    return os.environ.get(ROOT_ENV) or HERE


def ops(name=""):
    """A path under <root>/ops. A module that uses this for its ledger default follows the test root
    automatically -- under isolate() it resolves to the temp root, never live ops/."""
    base = os.path.join(root(), "ops")
    return os.path.join(base, name) if name else base


def child_env(extra=None, tmp_root=None):
    """An os.environ copy with COVENANT_STATE_ROOT set, to inject into a subprocess so the child writes
    under the same test root. tmp_root defaults to the active root(); extra merges on top."""
    env = dict(os.environ)
    env[ROOT_ENV] = tmp_root or root()
    if extra:
        env.update(extra)
    return env


def _under(path, base):
    """True if `path` is `base` or lives under it (both resolved)."""
    p = os.path.realpath(str(path))
    b = os.path.realpath(str(base))
    return p == b or p.startswith(b + os.sep)


@contextlib.contextmanager
def isolate(tmp_root):
    """While active: COVENANT_STATE_ROOT=tmp_root, and any open-for-write to the real repo ops/ that is NOT
    under tmp_root raises IsolationError (before the file is touched). Reads are never blocked. Tests wrap the
    code under test in this to prove it writes no live state. Drive it both ways: a live-ops write raises;
    remove the write (or point it under tmp_root) and it passes."""
    import builtins
    real_ops = os.path.join(HERE, "ops")
    tmp_root = os.path.realpath(tmp_root)
    os.makedirs(os.path.join(tmp_root, "ops"), exist_ok=True)
    _open = builtins.open
    _os_open = os.open
    _WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_TRUNC

    def _blocked(p):
        return _under(p, real_ops) and not _under(p, tmp_root)

    def _guarded(file, mode="r", *a, **k):
        try:
            writing = any(c in str(mode) for c in ("w", "a", "x", "+"))
        except Exception:                                      # noqa: BLE001 -- a weird mode is not our business
            writing = False
        if writing and _blocked(file):
            raise IsolationError(
                "test wrote to live state: %s (outside the test root %s). Resolve the path through "
                "covenant_state.ops(), or point it under the test root." % (file, tmp_root))
        return _open(file, mode, *a, **k)

    def _guarded_os_open(path, flags, *a, **k):
        # the atomic-write path (tempfile.mkstemp / os.fdopen / os.replace) goes through os.open, not
        # builtins.open, so it is guarded here too -- this is what catches the improve-miner's mkstemp
        # seen-set write (the A409 ledger shape). A read (O_RDONLY == 0) sets no write flag and is allowed.
        if (flags & _WRITE_FLAGS) and _blocked(path):
            raise IsolationError(
                "test wrote to live state via os.open: %s (outside the test root %s). Resolve the path "
                "through covenant_state.ops(), or point it under the test root." % (path, tmp_root))
        return _os_open(path, flags, *a, **k)

    old = os.environ.get(ROOT_ENV)
    os.environ[ROOT_ENV] = tmp_root
    builtins.open = _guarded
    os.open = _guarded_os_open
    try:
        yield tmp_root
    finally:
        builtins.open = _open
        os.open = _os_open
        if old is None:
            os.environ.pop(ROOT_ENV, None)
        else:
            os.environ[ROOT_ENV] = old
