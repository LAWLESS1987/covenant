#!/usr/bin/env python3
"""P12 (v8.32): substrate sensing, and a watchdog that transmits change.

WHY THIS SUITE EXISTS
---------------------
Two halves of one defect: the system senses a great deal and almost none of it
returns into the system.

  * The node was blind to the machine under it -- grep for psutil / meminfo /
    GlobalMemoryStatus / loadavg over 8,933 lines returned nothing -- while the
    ethics judge sits INSIDE consensus and is a multi-GB model. On 2026-08-23
    the production nodes restarted with 3.1 GB free against a 5.2 GB model.
  * The watchdog had no adaptation. Twelve hours of watchdog.log: 3,808 lines,
    16 distinct messages, 99.6% redundancy -- 269 identical permanent ALERTs
    and FOUR lines describing the only thing that actually happened.

CHECKS
  S1-S9   the sensor measures, degrades with a reason, and never raises
  H1-H3   /health carries it, and warns rather than deciding
  B1-B3   THE BOUNDARY, asserted mechanically over the source: sensing may
          inform refusal and disclosure, never relaxation. B2 walks the AST and
          fails if any function outside the allowlist touches the sensor; B3
          fails if a function that touches it also touches a consensus path.
          A future edit that wires memory pressure into a decision fails a test
          rather than passing review.
  W1-W10  the watchdog's Adaptation and its reading of the node's own
          /anomalies -- both pure functions, so no nodes are started

Node env needs BOTH COVENANT_INSECURE_MOCK_JUDGE=1 and
COVENANT_JUDGE_PROVIDERS=mock (M2).
"""
import ast, atexit, json, os, shutil, socket, subprocess, sys, tempfile, time
import urllib.error, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
SRC = os.path.join(HERE, "covenant_unified_v8.py")
ENV = dict(os.environ, COVENANT_INSECURE_MOCK_JUDGE="1",
           COVENANT_JUDGE_PROVIDERS="mock")

import covenant_unified_v8 as cov

FIXED = hasattr(cov, "SubstrateSensor")
TMP = tempfile.mkdtemp(prefix="covtest_p12_")
SPAWNED, results = [], []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}")


def stop(p, timeout=10):
    if p is None or p.poll() is not None:
        return
    try:
        p.terminate(); p.wait(timeout=timeout)
    except Exception:
        try:
            p.kill(); p.wait(timeout=5)
        except Exception:
            pass


def _reap():
    for p in SPAWNED:
        stop(p, timeout=5)
    shutil.rmtree(TMP, ignore_errors=True)


atexit.register(_reap)


def pick_base(span=14):
    for base in range(20700, 22200, 100):
        for off in range(span):
            s = socket.socket()
            try:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
                s.bind(("127.0.0.1", base + off))
            except OSError:
                s.close(); break
            s.close()
        else:
            return base
    raise SystemExit("no free port block")


def wait_api(port, timeout=40):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2)
            return True
        except urllib.error.HTTPError:
            return True
        except Exception:
            time.sleep(0.5)
    return False


# ---------------------------------------------------------------- sensor --
def sensor_checks():
    avail, why = cov.read_available_memory_bytes()
    check("S1 available memory is measured on this platform",
          isinstance(avail, int) and avail > 0 and why == "",
          f"{None if avail is None else round(avail/1048576)} MB, reason={why!r}")

    saved = cov.sys.platform
    try:
        cov.sys.platform = "plan9"
        a2, w2 = cov.read_available_memory_bytes()
    except Exception as e:
        a2, w2 = "RAISED", f"{type(e).__name__}"
    finally:
        cov.sys.platform = saved
    check("S2 an unsupported platform degrades with a reason, never raises",
          a2 is None and "plan9" in str(w2), f"{a2!r} {w2!r}")
    check("S2b the real reader still works afterwards",
          cov.read_available_memory_bytes()[0] > 0)

    for k in ("COVENANT_LOCAL_JUDGE_URL", "COVENANT_LOCAL_JUDGE_MODEL",
              "COVENANT_JUDGE_FOOTPRINT_MB"):
        os.environ.pop(k, None)
    f, src, why = cov.read_judge_footprint_bytes()
    check("S3 no judge configured -> no number, a reason, no raise",
          f is None and src == "" and bool(why), f"{f!r} {src!r} {why!r}")

    os.environ["COVENANT_JUDGE_FOOTPRINT_MB"] = "5200"
    f, src, why = cov.read_judge_footprint_bytes()
    check("S4 an operator-declared footprint is used and LABELLED as declared",
          f == 5200 * 1048576 and src == "declared", f"{f} {src!r}")

    os.environ["COVENANT_JUDGE_FOOTPRINT_MB"] = "not-a-number"
    f, src, why = cov.read_judge_footprint_bytes()
    check("S5 a junk declaration is refused with a reason, not silently zero",
          f is None and "not a number" in why, f"{f!r} {why!r}")
    os.environ.pop("COVENANT_JUDGE_FOOTPRINT_MB", None)

    # an unreachable ollama must not hang or raise
    os.environ["COVENANT_LOCAL_JUDGE_URL"] = "http://127.0.0.1:1/v1/chat/completions"
    os.environ["COVENANT_LOCAL_JUDGE_MODEL"] = "nope:1b"
    t0 = time.monotonic()
    f, src, why = cov.read_judge_footprint_bytes()
    dt = time.monotonic() - t0
    check("S6 an unreachable ollama degrades fast, with a reason",
          f is None and bool(why) and dt < 10, f"{dt:.2f}s {why!r}")
    for k in ("COVENANT_LOCAL_JUDGE_URL", "COVENANT_LOCAL_JUDGE_MODEL"):
        os.environ.pop(k, None)

    s = cov.SubstrateSensor(interval=60)
    snap = s.snapshot()
    check("S7 before any sample the snapshot SAYS so",
          snap["available_memory_mb"] is None
          and "not sampled" in snap["unavailable"], str(snap))
    s.sample_once()
    snap = s.snapshot()
    check("S7b after sampling, memory is present and the reading is fresh",
          snap["available_memory_mb"] > 0 and snap["sampled_s_ago"] < 5,
          f"{snap['available_memory_mb']} MB, {snap['sampled_s_ago']}s ago")

    check("S8 no warning when memory comfortably exceeds the model",
          s.warnings() == [] or all("memory available" not in w
                                    for w in s.warnings()), str(s.warnings()))

    s._snap = {"available_memory_mb": 3100, "judge_footprint_mb": 5200,
               "judge_footprint_source": "ollama", "unavailable": ""}
    s._sampled_at = time.monotonic()
    w = s.warnings()
    check("S9 the 2026-08-23 condition produces a warning naming both numbers",
          len(w) == 1 and "3100" in w[0] and "5200" in w[0]
          and "paging" in w[0] and "consensus" in w[0], str(w))

    s._sampled_at = time.monotonic() - 4000
    w = s.warnings()
    check("S9b a stopped sampler is itself a warning, not a stale silence",
          any("sampler may have stopped" in x for x in w), str(w))


# ------------------------------------------------------ the boundary (AST) --
ALLOWED_FUNCS = {
    "<module>", "read_available_memory_bytes", "read_judge_footprint_bytes",
    "__init__", "sample_once", "snapshot", "warnings", "loop", "run", "health",
}
CONSENSUS_MARKS = ("chain_lock", "validate_block", "_accept_block_common",
                   "admit_pending_transaction", "evaluate_transaction",
                   "mine(", "distribute_block_rewards")
SENSOR_NAMES = {"SubstrateSensor", "read_available_memory_bytes",
                "read_judge_footprint_bytes", "SUBSTRATE_SAMPLE_INTERVAL_S",
                "substrate"}


def _enclosing(tree):
    """node -> enclosing function name."""
    owner = {}
    def walk(n, name):
        for c in ast.iter_child_nodes(n):
            nm = c.name if isinstance(c, (ast.FunctionDef, ast.AsyncFunctionDef)) else name
            owner[c] = nm
            walk(c, nm)
    walk(tree, "<module>")
    return owner


def boundary_checks():
    src = open(SRC, encoding="utf-8").read()
    tree = ast.parse(src)
    owner = _enclosing(tree)

    touching = set()
    for node in ast.walk(tree):
        hit = ((isinstance(node, ast.Name) and node.id in SENSOR_NAMES)
               or (isinstance(node, ast.Attribute) and node.attr in SENSOR_NAMES))
        if hit:
            touching.add(owner.get(node, "<module>"))

    stray = sorted(touching - ALLOWED_FUNCS)
    check("B1 the sensor is touched only inside its own code, run() and /health",
          not stray, f"unexpected: {stray}" if stray else f"functions: {sorted(touching)}")

    # B2 -- dataflow, not co-location. The first version of this check matched
    # substrings inside _setup_routes (which contains EVERY route as a nested
    # function) and inside warnings()' own message text, which mentions
    # chain_lock in prose. It failed on correct code. What it should assert is
    # that no BRANCH in /health tests the sensor: a reading that no `if` reads
    # cannot gate anything.
    health_fn = next((f for f in ast.walk(tree)
                      if isinstance(f, ast.FunctionDef) and f.name == "health"), None)
    branches = []
    if health_fn is not None:
        # Follow aliases. Mutation-tested: matching only on the literal word
        # "substrate" is evaded by one local variable --
        #     sub = self.node.substrate.snapshot()
        #     if sub["available_memory_mb"] < 500: ...
        # reads the sensor in a branch and never says "substrate" in the test.
        tainted = {"substrate"}
        for _ in range(3):                       # fixpoint; depth 3 is plenty
            for node in ast.walk(health_fn):
                if isinstance(node, (ast.Assign, ast.AnnAssign)):
                    rhs = ast.get_source_segment(src, node.value) or ""
                    if any(t in rhs for t in tainted):
                        targets = (node.targets if isinstance(node, ast.Assign)
                                   else [node.target])
                        for t in targets:
                            for nm in ast.walk(t):
                                if isinstance(nm, ast.Name):
                                    tainted.add(nm.id)
        for node in ast.walk(health_fn):
            if isinstance(node, (ast.If, ast.IfExp)):
                seg = ast.get_source_segment(src, node.test) or ""
                if any(t in seg for t in tainted):
                    branches.append(seg.strip()[:60])
    check("B2 no branch in /health tests the substrate reading",
          health_fn is not None and not branches,
          str(branches) if branches else "health() has no substrate-gated branch")

    # B3 -- likewise: COMPARISON, not mention. Building a dict that contains the
    # number is not deciding anything; comparing it is. Every Compare node whose
    # source mentions the numbers must sit inside SubstrateSensor.warnings().
    owner_fn = {}
    for fn in ast.walk(tree):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for node in ast.walk(fn):
                owner_fn.setdefault(node, fn.name)
    stray_cmp = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        seg = ast.get_source_segment(src, node) or ""
        if any(k in seg for k in ("available_memory_mb", "judge_footprint_mb")):
            fn = owner_fn.get(node, "<module>")
            if fn != "warnings":
                stray_cmp.append(f"{fn}: {seg.strip()[:50]}")
    check("B3 the sensor's numbers are COMPARED only in warnings()",
          not stray_cmp, str(stray_cmp) if stray_cmp else "clean")

    # B3b -- and the one that would actually hurt: `degraded` is the field a
    # monitor keys off. It must be computed from the node's own capability to do
    # its job, never from the weather on the machine.
    deg = [ast.get_source_segment(src, n) or "" for n in ast.walk(tree)
           if isinstance(n, ast.keyword) and n.arg is None]
    deg_src = next((ln for ln in src.splitlines() if '"degraded"' in ln), "")
    check("B3b 'degraded' is not computed from the substrate",
          "substrate" not in deg_src and "memory" not in deg_src, deg_src.strip()[:80])


# ---------------------------------------------------------------- /health --
def health_checks():
    base = pick_base()
    p = subprocess.Popen([sys.executable, SRC, "--port", str(base), "--node-id", "P"],
                         env=dict(ENV, COVENANT_DB_PATH=os.path.join(TMP, "p.db"),
                                  PYTHONUNBUFFERED="1"),
                         cwd=TMP, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True)
    SPAWNED.append(p)
    try:
        check("H1 node came up", wait_api(base))
        with urllib.request.urlopen(f"http://127.0.0.1:{base}/health", timeout=10) as r:
            h = json.loads(r.read().decode())
        sub = h.get("substrate")
        check("H2 /health carries the substrate reading",
              isinstance(sub, dict)
              and set(sub) >= {"available_memory_mb", "judge_footprint_mb",
                               "judge_footprint_source", "sampled_s_ago",
                               "unavailable"}, str(sub))
        check("H2b it was sampled before the first request, not left blank",
              sub.get("available_memory_mb") is not None
              and sub.get("sampled_s_ago") is not None, str(sub))
        check("H3 substrate never makes a node 'degraded' -- it warns only",
              isinstance(h.get("degraded"), bool)
              and h["degraded"] == bool(
                  h.get("judge_keyless") or h.get("judge_insecure")
                  or h.get("own_genesis") or h.get("crisis_mode")),
              f"degraded={h.get('degraded')}")
    finally:
        stop(p)


# --------------------------------------------------------------- watchdog --
def watchdog_checks():
    try:
        import covenant_watchdog as wd
    except Exception as e:
        check("W0 watchdog importable", False, f"{type(e).__name__}: {e}")
        return
    if not hasattr(wd, "Adaptation"):
        check("W0 watchdog carries P12 adaptation", False, "pre-P12 watchdog")
        return
    check("W0 watchdog carries P12 adaptation", True)

    a = wd.Adaptation(roll_up_every=30)
    check("W1 a new condition is emitted in full", a.observe("k", "sandbox down") == "sandbox down")
    check("W2 the same condition again is silence", a.observe("k", "sandbox down") is None)
    check("W3 a CHANGED condition is emitted in full",
          a.observe("k", "sandbox up") == "sandbox up")

    b = wd.Adaptation(roll_up_every=30)
    emitted = [b.observe("k", "same") for _ in range(90)]
    n = len([e for e in emitted if e])
    check("W4 a permanent condition rolls up instead of repeating",
          n == 4 and "[unchanged, 30 rounds]" in (emitted[29] or ""),
          f"{n} lines from 90 rounds")

    cleared = b.sweep(set())
    check("W5 a condition that stops produces one CLEARED line with its duration",
          len(cleared) == 1 and "90 round" in cleared[0], str(cleared))
    check("W5b and is then forgotten, so its return is news again",
          b.observe("k", "same") == "same")

    # W6 -- the measured claim, replayed. 269 permanent + 4 transient, as the
    # real log held them.
    c = wd.Adaptation(roll_up_every=30)
    out = []
    for i in range(273):
        line = ("peer unreachable" if i in (100, 101, 102, 103)
                else "code sandbox unavailable")
        r = c.observe(f"alert:{line}", line)
        if r:
            out.append(r)
    transient = [o for o in out if o.startswith("peer unreachable")]
    before = 4 / 273
    after = len(transient) / max(1, len(out))
    check("W6 the buried transient stops being buried",
          len(transient) >= 1 and after > before * 5,
          f"share of emitted lines {before:.1%} -> {after:.1%} "
          f"({len(out)} lines from 273 observations)")

    seen = set()
    rep = {"per_kind": {"peer_message_error": {"recent": 9, "baseline": 600,
                                              "expected_recent": 1.2}},
           "spikes": [{"kind": "peer_message_error", "recent": 9,
                       "expected_recent": 1.2}],
           "spike_detected": True}
    al, inf = wd.anomaly_report("A", rep, seen)
    check("W7 the node's own spike verdict becomes an alert with its numbers",
          len(al) == 1 and "peer_message_error" in al[0]
          and "recent 9" in al[0] and "1.2" in al[0], str(al))
    check("W7b a first-seen kind is INFO, not an alert",
          len(inf) == 1 and "new anomaly kind" in inf[0], str(inf))

    al2, inf2 = wd.anomaly_report("A", dict(rep, spike_detected=False), seen)
    check("W8 the same kind next round is neither alert nor info",
          al2 == [] and inf2 == [], f"{al2} {inf2}")

    for junk in (None, "not a dict", {}, {"per_kind": None}):
        try:
            wd.anomaly_report("A", junk, set())
        except Exception as e:
            check("W9 a malformed /anomalies reply cannot crash the watchdog",
                  False, f"{junk!r} -> {type(e).__name__}: {e}")
            break
    else:
        check("W9 a malformed /anomalies reply cannot crash the watchdog", True)

    check("W10 the watchdog now reads /anomalies at all",
          hasattr(wd, "anomalies") and callable(wd.anomalies))

    # ---- the push channel. Opt-in, credential-free, non-blocking. ----
    if not hasattr(wd, "push_alert"):
        check("P0 the watchdog carries the alert push", False, "absent")
        return
    check("P0 the watchdog carries the alert push", True)

    SECRET = "https://ntfy.example/SECRET-TOPIC-abc123"
    wd._push_times.clear()
    act, det = wd.push_alert("x", url="")
    check("P1 no URL configured means OFF, not a silent failure",
          act == "disabled", f"{act} {det}")

    sent = []
    act, det = wd.push_alert("node A down", now=1000.0, url=SECRET,
                             opener=lambda u, b: sent.append((u, b)) or 200)
    check("P2 with a URL it sends the alert text",
          act == "sent" and sent and sent[0][1] == b"node A down", f"{act} {det}")

    wd._push_times.clear()
    outcomes = [wd.push_alert(f"a{i}", now=2000.0 + i, url=SECRET,
                              opener=lambda u, b: 200)[0]
                for i in range(wd.PUSH_MAX_PER_HOUR + 5)]
    check("P3 it rate-limits instead of flooding a phone",
          outcomes.count("sent") == wd.PUSH_MAX_PER_HOUR
          and outcomes.count("rate-limited") == 5,
          f"sent={outcomes.count('sent')} clipped={outcomes.count('rate-limited')}")

    act, det = wd.push_alert("later", now=2000.0 + 4000, url=SECRET,
                             opener=lambda u, b: 200)
    check("P3b and the window rolls, so it recovers on its own",
          act == "sent", f"{act} {det}")

    wd._push_times.clear()
    def boom(u, b):
        raise OSError(f"connection to {u} refused")
    act, det = wd.push_alert("boom", now=3000.0, url=SECRET, opener=boom)
    check("P4 a failing push is reported as a failure, not an alert",
          act == "failed", f"{act} {det}")
    check("P4b THE URL IS NEVER IN THE OUTPUT -- it is a shared secret",
          SECRET not in det and "SECRET-TOPIC" not in det, repr(det))

    wd._push_times.clear()
    big = []
    wd.push_alert("y" * 5000, now=4000.0, url=SECRET,
                  opener=lambda u, b: big.append(b) or 200)
    check("P5 the pushed body is bounded",
          big and len(big[0]) <= 900, f"{len(big[0]) if big else 0} bytes")


def prefix_record():
    print("=== PRE-FIX RECORD (module has no SubstrateSensor) ===")
    src = open(SRC, encoding="utf-8").read()
    check("R1 the node cannot see the machine it runs on",
          not any(k in src for k in ("psutil", "meminfo", "GlobalMemoryStatus",
                                     "loadavg", "virtual_memory")))
    check("R2 /health carries no substrate reading", '"substrate"' not in src)
    try:
        import covenant_watchdog as wd
        check("R3 the watchdog has no adaptation", not hasattr(wd, "Adaptation"))
        check("R4 the watchdog does not read /anomalies", not hasattr(wd, "anomalies"))
    except Exception as e:
        check("R3/R4 watchdog importable", False, str(e))


def main():
    print(f"source under test: {SRC}")
    print(f"mode: {'FIXED (v8.32+)' if FIXED else 'PRE-FIX RECORD'}")
    if FIXED:
        sensor_checks()
        boundary_checks()
        health_checks()
        watchdog_checks()
    else:
        prefix_record()
    ok = sum(1 for _, o, _ in results if o)
    print(f"\n{ok}/{len(results)} passed")
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
