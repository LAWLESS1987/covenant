#!/usr/bin/env python3
"""
W2 -- the code sandbox on a platform that cannot enforce its own limits.

THE FINDING (2026-08-22, found by running the suite on the machine that runs
the node, not by reading the file). run_sandboxed() needs a "fork" start
method: its child target is a nested closure, and the limits it enforces are
POSIX RLIMITs. The node runs on Windows. There, get_context("fork") raised
ValueError, which escaped run_sandboxed -> validate_and_score -> DAGNode.create
-> past /propose_code's `except CodeSecurityError` -> bare HTTP 500, nothing on
/anomalies. Fail-closed by accident and impossible to diagnose from the outside.

WHAT THIS SUITE PINS, and what it deliberately does not:
  * a platform without fork REFUSES proposals -- it never runs a snippet with
    the memory / process / file-size caps silently unenforced. There is no
    "spawn" fallback and this suite would fail if one were added, because the
    refusal is the control.
  * the refusal is a normal rejection (CodeSecurityError -> 400 with a reason),
    not an exception escaping to a 500.
  * /health says so at boot, and the refusal is recorded on /anomalies.
  * on a fork platform NOTHING changes: snippets still run, and the 256 MiB cap
    still turns `[0] * 10**10` into a failure rather than an OOM.

COVENANT_FORCE_NO_SANDBOX=1 makes a fork platform take the fork-less path, so
the Windows behaviour is testable here. It is one-way: it can only take the
sandbox away. Nothing turns it on where the platform cannot enforce the limits.

Run: python3 test_w2_sandbox_platform.py
"""
import json, multiprocessing, os, subprocess, sys, time, urllib.error, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("COVENANT_INSECURE_MOCK_JUDGE", "1")
os.environ.setdefault("COVENANT_JUDGE_PROVIDERS", "mock")
import covenant_unified_v8 as cov

P = F = 0
def check(label, ok, detail=""):
    global P, F
    if ok: P += 1; print(f"  [PASS] {label}" + (f" -- {detail}" if detail else ""))
    else:  F += 1; print(f"  [FAIL] {label} -- {detail}")

HAS_FORK = "fork" in multiprocessing.get_all_start_methods()
print(f"platform {sys.platform}, fork available: {HAS_FORK}")

# ---------------------------------------------------------------- W2.1 wiring
print("\n== W2.1 the capability constant reflects the platform ==")
check("W2.1 SANDBOX_FORK_AVAILABLE matches get_all_start_methods()",
      cov.SANDBOX_FORK_AVAILABLE == HAS_FORK, f"{cov.SANDBOX_FORK_AVAILABLE} vs {HAS_FORK}")
check("W2.1b a reason string exists exactly when the sandbox is unavailable",
      bool(cov.SANDBOX_UNAVAILABLE_REASON) == (not cov.SANDBOX_FORK_AVAILABLE),
      repr(cov.SANDBOX_UNAVAILABLE_REASON)[:60])

# ------------------------------------------------- W2.2-W2.4 the refusal path
print("\n== W2.2 a fork-less platform refuses instead of raising ==")
real = cov.SANDBOX_FORK_AVAILABLE
cov.SANDBOX_FORK_AVAILABLE = False
cov.SANDBOX_UNAVAILABLE_REASON = "no usable 'fork' start method on this platform (test)"
try:
    try:
        r = cov.run_sandboxed("x = 1")
        raised = None
    except Exception as e:                      # the pre-fix behaviour
        r, raised = None, e
    check("W2.2 run_sandboxed returns instead of raising", raised is None, repr(raised))
    if r is not None:
        check("W2.2b it reports it did not run", r.get("ran") is False, r)
        check("W2.2c ok is False -- a refusal is not a pass", r.get("ok") is False, r)
        check("W2.2d the error names the cause", "SandboxUnavailable" in str(r.get("error")), r.get("error"))

    print("\n== W2.3 the Guardian refuses a BENIGN snippet when it cannot sandbox it ==")
    g = cov.CovenantGuardian()
    ok, score, err = g.validate_and_score("x = 1\n")
    check("W2.3 a harmless snippet is refused, not accepted", ok is False, f"ok={ok} err={err}")
    check("W2.3b the reason reaches the caller", "SandboxUnavailable" in err, err)

    print("\n== W2.4 enforce() raises the type /propose_code catches ==")
    try:
        g.enforce("x = 1\n"); kind = "no exception"
    except cov.CodeSecurityError as e:
        kind = "CodeSecurityError"
    except Exception as e:
        kind = type(e).__name__
    check("W2.4 CodeSecurityError, so the route answers 400 and not 500",
          kind == "CodeSecurityError", kind)
finally:
    cov.SANDBOX_FORK_AVAILABLE = real
    cov.SANDBOX_UNAVAILABLE_REASON = "" if real else cov.SANDBOX_UNAVAILABLE_REASON

# ------------------------------------------------ W2.5-W2.6 the fork platform
print("\n== W2.5 on a fork platform nothing changed ==")
if not HAS_FORK:
    print("  [SKIP] no fork on this platform -- W2.5/W2.6 cannot run here, and are")
    print("         not counted as passes. Run this suite on Linux for those two.")
else:
    r = cov.run_sandboxed("x = 1\n")
    check("W2.5 a good snippet still runs AND reports success", r.get("ran") is True and r.get("ok") is True, r)
    check("W2.5a the child could speak under its own limits -- no silent death",
          "without reporting" not in str(r.get("error")), r.get("error"))
    r = cov.run_sandboxed("z = 1 / 0\n")
    check("W2.5b a raising snippet is reported as failed WITH its exception",
          r.get("ran") is True and r.get("ok") is False
          and "ZeroDivisionError" in str(r.get("error")), r)

    print("\n== W2.6 the memory cap is still enforced (the reason fork was chosen) ==")
    r = cov.run_sandboxed("y = [0] * 10**10\n")
    check("W2.6 `[0] * 10**10` is refused",  r.get("ok") is False, r)
    # A dead child also produces ok=False. The first version of this check could
    # not tell the two apart and passed while the sandbox was killing everything.
    check("W2.6a and refused with a MemoryError, not by dying",
          "MemoryError" in str(r.get("error")), r.get("error"))
    check("W2.6b the file-size limit is still applied",
          cov.run_sandboxed("open('w2_should_not_exist','w').write('x')\n").get("ok") is False, "")

# ------------------------------------------------------- W2.7 live /health
print("\n== W2.7 a live node says so on /health, both ways ==")
def free_port():
    import socket as s
    x = s.socket(); x.bind(("127.0.0.1", 0)); p = x.getsockname()[1]; x.close(); return p

def boot(tag, extra_env, tries=40):
    port = free_port()
    env = dict(os.environ); env.update(extra_env)
    env["COVENANT_DB_PATH"] = f"w2_{tag}.db"
    for f in (env["COVENANT_DB_PATH"], env["COVENANT_DB_PATH"] + ".key"):
        try: os.remove(f)
        except OSError: pass
    p = subprocess.Popen([sys.executable, "covenant_unified_v8.py", "--port", str(port),
                          "--node-id", tag],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
    for _ in range(tries):
        time.sleep(0.5)
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=3) as r:
                return p, json.loads(r.read().decode())
        except Exception:
            if p.poll() is not None:
                return p, None
    return p, None

for tag, env, expect in (("w2on", {}, True), ("w2off", {"COVENANT_FORCE_NO_SANDBOX": "1"}, False)):
    if not HAS_FORK and expect:
        print("  [SKIP] W2.7 sandbox-available case needs a fork platform")
        continue
    proc, h = boot(tag, env)
    try:
        if h is None:
            check(f"W2.7 node {tag} came up", False, "no /health")
            continue
        sub = h.get("subsystems", {})
        check(f"W2.7 {tag}: /health exposes subsystems.code_sandbox",
              "code_sandbox" in sub, sorted(sub))
        check(f"W2.7b {tag}: it reports {expect}", sub.get("code_sandbox") is expect, sub.get("code_sandbox"))
        warned = any("code sandbox unavailable" in w for w in h.get("warnings", []))
        check(f"W2.7c {tag}: warning present exactly when unavailable",
              warned == (not expect), h.get("warnings"))
    finally:
        proc.terminate()
        try: proc.wait(timeout=10)
        except Exception: proc.kill()
        for f in (f"w2_{tag}.db", f"w2_{tag}.db.key"):
            try: os.remove(f)
            except OSError: pass

print("\n" + "=" * 60)
print(f"{P}/{P+F} passed" + (f", {F} FAILED" if F else ""))
print("=" * 60)
sys.exit(1 if F else 0)
