#!/usr/bin/env python3
"""P11 (v8.31): the node must be able to say which source it is running.

WHY THIS SUITE EXISTS
---------------------
M25 taught the loop to grep the DEPLOYED file rather than trust the backlog.
That discipline stopped one layer short. After you have verified the bytes on
disk, nothing told you whether the process answering :5000 was running THOSE
bytes:

  * COVENANT_VERSION read "v8.9-merged" and was referenced nowhere;
  * the only version string an operator ever saw was a hard-coded
    "Covenant Unified v7.0" in the boot banner -- on a v8.30 file;
  * /health carried no version and no source fingerprint at all.

On 2026-08-23 "is v8.30 live?" could only be answered by forensics: an alert
that exists only in v8.30, plus mtime arithmetic against prod.log. A restart
from covenant_unified_v8.PRE-v8.29.py -- which sits in the same folder -- would
have looked identical from outside.

CHECKS
  V1  the module reports a version, and not either dead string
  V2  its self-reported sha256 equals an INDEPENDENT digest of the file
  V3  its self-reported line count equals an independent count
  V4  the fingerprint TRACKS THE BYTES: a one-byte-different copy, imported
      separately, reports a different hash. (Without V4, a hard-coded constant
      passes V2 by accident.)
  V5  a live node's boot banner names the version and the source hash
  V6  /health carries version + source_sha256 + source_lines, and the hash it
      reports is the true digest's first 12 hex
  V7  an unreadable source DEGRADES with a reason instead of raising -- an
      observability feature must never stop a node from booting
  V8  ...and /health warns about it, so "cannot prove what I am" is loud

Run on the pristine v8.30 this file records the pre-fix state instead
(PRE-FIX RECORD mode) -- the executable record of what was wrong.

Node env needs BOTH COVENANT_INSECURE_MOCK_JUDGE=1 and
COVENANT_JUDGE_PROVIDERS=mock (M2). Ports chosen at runtime: a production node
owns 5000-5031 on the machine this has to run on.
"""
import atexit, hashlib, importlib.util, json, os, shutil, socket, subprocess, sys
import tempfile, time, urllib.error, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
SRC = os.path.join(HERE, "covenant_unified_v8.py")
ENV = dict(os.environ, COVENANT_INSECURE_MOCK_JUDGE="1",
           COVENANT_JUDGE_PROVIDERS="mock")

import covenant_unified_v8 as cov

FIXED = hasattr(cov, "CORE_SOURCE_SHA256")
TMP = tempfile.mkdtemp(prefix="covtest_p11_")
SPAWNED = []
results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}")


def stop(p, timeout=10):
    if p is None or p.poll() is not None:
        return
    try:
        p.terminate()            # portable: TerminateProcess on nt, SIGTERM on posix
        p.wait(timeout=timeout)
    except Exception:
        try:
            p.kill(); p.wait(timeout=5)
        except Exception:
            pass


def _reap():
    for p in SPAWNED:
        stop(p, timeout=5)
    shutil.rmtree(TMP, ignore_errors=True)   # open sqlite on Windows -> WinError 32


atexit.register(_reap)


def pick_base(span=14):
    for base in range(19100, 20600, 100):
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
    raise SystemExit("no free port block in 19100-20600")


def get(port, path, timeout=10):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=timeout) as r:
        return r.status, json.loads(r.read().decode())


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


def true_digest():
    with open(SRC, "rb") as fh:
        raw = fh.read()
    return hashlib.sha256(raw).hexdigest(), raw.count(b"\n")


# --------------------------------------------------------------------------
def prefix_record():
    """What v8.30 and earlier actually did. Assertions are the defect."""
    print("=== PRE-FIX RECORD (module has no CORE_SOURCE_SHA256) ===")
    with open(SRC, encoding="utf-8") as fh:
        text = fh.read()
    check("R1 version constant is the dead 'v8.9-merged'",
          getattr(cov, "COVENANT_VERSION", None) == "v8.9-merged",
          f"COVENANT_VERSION={getattr(cov, 'COVENANT_VERSION', None)!r}")
    check("R2 the constant is referenced nowhere but its definition",
          text.count("COVENANT_VERSION") == 1,
          f"occurrences={text.count('COVENANT_VERSION')}")
    check("R3 boot banner hard-codes v7.0 on a v8.30 file",
          'Covenant Unified v7.0 running' in text)
    base = pick_base()
    p = subprocess.Popen([sys.executable, SRC, "--port", str(base), "--node-id", "P"],
                         env=dict(ENV, COVENANT_DB_PATH=os.path.join(TMP, "p.db")),
                         cwd=TMP, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True)
    SPAWNED.append(p)
    try:
        check("R4 node came up", wait_api(base))
        st, h = get(base, "/health")
        check("R5 /health carries NO version", "version" not in h,
              f"keys with 'version': {[k for k in h if 'version' in k]}")
        check("R6 /health carries NO source fingerprint",
              "source_sha256" not in h)
    finally:
        stop(p)


# --------------------------------------------------------------------------
def fixed_checks():
    digest, lines = true_digest()

    check("V1 module reports a real version",
          isinstance(cov.COVENANT_VERSION, str)
          and cov.COVENANT_VERSION not in ("v8.9-merged", "v7.0")
          and cov.COVENANT_VERSION.startswith("v8."),
          f"COVENANT_VERSION={cov.COVENANT_VERSION!r}")

    check("V2 self-reported sha256 == independent digest of the file",
          cov.CORE_SOURCE_SHA256 == digest,
          f"module={cov.CORE_SOURCE_SHA256[:12]} independent={digest[:12]}")

    check("V3 self-reported line count == independent count",
          cov.CORE_SOURCE_LINES == lines,
          f"module={cov.CORE_SOURCE_LINES} independent={lines}")

    check("V3b no fingerprint failure on a normal source",
          cov.CORE_SOURCE_UNREADABLE == "",
          repr(cov.CORE_SOURCE_UNREADABLE))

    # V4 -- the fingerprint must follow the bytes, not be a constant someone
    # forgot to bump. Import a one-byte-different copy as its own module.
    twin_path = os.path.join(TMP, "covenant_unified_v8_twin.py")
    with open(SRC, "rb") as fh:
        raw = fh.read()
    with open(twin_path, "wb") as fh:
        fh.write(raw + b"\n# one byte of drift\n")
    spec = importlib.util.spec_from_file_location("cov_twin", twin_path)
    twin = importlib.util.module_from_spec(spec)
    sys.modules["cov_twin"] = twin
    spec.loader.exec_module(twin)
    check("V4 a modified copy reports a DIFFERENT hash",
          twin.CORE_SOURCE_SHA256 != cov.CORE_SOURCE_SHA256
          and twin.CORE_SOURCE_LINES == cov.CORE_SOURCE_LINES + 2,
          f"twin={twin.CORE_SOURCE_SHA12} orig={cov.CORE_SOURCE_SHA12} "
          f"lines {cov.CORE_SOURCE_LINES}->{twin.CORE_SOURCE_LINES}")
    check("V4b the twin still agrees with an independent digest of ITSELF",
          twin.CORE_SOURCE_SHA256 == hashlib.sha256(
              open(twin_path, "rb").read()).hexdigest())

    # V5/V6 -- a real node, the way an operator meets it.
    base = pick_base()
    # PYTHONUNBUFFERED: without it a killed node's stdout can arrive empty and
    # the banner assertions below pass vacuously. The loop learned this once
    # already, on the K2 "boot: announced tip" line (2026-08-22 00:40).
    p = subprocess.Popen([sys.executable, SRC, "--port", str(base), "--node-id", "P"],
                         env=dict(ENV, COVENANT_DB_PATH=os.path.join(TMP, "p.db"),
                                  PYTHONUNBUFFERED="1"),
                         cwd=TMP, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True)
    SPAWNED.append(p)
    banner = ""
    try:
        up = wait_api(base)
        check("V5a node came up", up)
        st, h = get(base, "/health")
        check("V6a /health carries the version",
              h.get("version") == cov.COVENANT_VERSION, f"{h.get('version')!r}")
        check("V6b /health's source_sha256 is the TRUE digest's first 12",
              h.get("source_sha256") == digest[:12],
              f"health={h.get('source_sha256')} true={digest[:12]}")
        check("V6c /health carries the line count",
              h.get("source_lines") == lines, f"{h.get('source_lines')}")
        check("V6d no spurious fingerprint warning",
              not any("fingerprint" in w for w in h.get("warnings", [])),
              str(h.get("warnings")))
    finally:
        stop(p)
        try:
            banner = p.communicate(timeout=10)[0] or ""
        except Exception:
            try:
                banner = p.stdout.read() or ""
            except Exception:
                banner = ""

    line = next((l for l in banner.splitlines() if "running - API:" in l), "")
    shown = line.strip() or "<no banner line captured>"
    # Every one of these REQUIRES the line. "v7.0 is absent" is true of an
    # empty string too, so without `line` in the condition V5d is a check that
    # cannot fail -- which is how it passed on the first VM run while V5b/V5c
    # failed for want of the same evidence.
    check("V5b boot banner names the version",
          bool(line) and cov.COVENANT_VERSION in line, shown)
    check("V5c boot banner names the source hash",
          bool(line) and digest[:12] in line, shown)
    check("V5d boot banner no longer says v7.0",
          bool(line) and "v7.0" not in line, shown)

    # V7 -- degrade, never raise.
    saved = cov.__file__
    try:
        cov.__file__ = os.path.join(TMP, "does-not-exist-anywhere.py")
        sha, n, reason = cov._core_source_fingerprint()
    except Exception as e:
        sha, n, reason = None, None, f"RAISED {type(e).__name__}"
    finally:
        cov.__file__ = saved
    check("V7a unreadable source does not raise", not str(reason).startswith("RAISED"),
          str(reason))
    check("V7b it degrades to 'unavailable' with a reason",
          sha == "unavailable" and n == 0 and bool(reason)
          and not str(reason).startswith("RAISED"), f"{sha!r} {n} {reason!r}")
    check("V7c the real fingerprint was restored",
          cov._core_source_fingerprint()[0] == digest)

    # V8 -- and it is loud on /health.
    port = pick_base()
    m = cov.CovenantUnifiedMaster("p11", host="127.0.0.1", port=port,
                                  p2p_port=port + 1,
                                  db_path=os.path.join(TMP, "p11.db"))
    client = m.api.app.test_client()
    saved_reason = cov.CORE_SOURCE_UNREADABLE
    try:
        cov.CORE_SOURCE_UNREADABLE = "OSError: simulated unreadable source"
        body = client.get("/health").get_json()
        warns = body.get("warnings", [])
        check("V8a /health warns when the source cannot be fingerprinted",
              any("fingerprint" in w for w in warns), str(warns))
        check("V8b the warning says the node cannot prove its version",
              any("cannot prove" in w for w in warns), str(warns))
    finally:
        cov.CORE_SOURCE_UNREADABLE = saved_reason
    body = client.get("/health").get_json()
    check("V8c warning gone once the source is readable again",
          not any("fingerprint" in w for w in body.get("warnings", [])),
          str(body.get("warnings")))


def watchdog_checks():
    """W-checks: the watchdog is what turns a one-off answer into a standing
    one. These are the reason the drift comparison is a pure function."""
    try:
        import covenant_watchdog as wd
    except Exception as e:
        check("W0 watchdog importable", False, f"{type(e).__name__}: {e}")
        return
    if not hasattr(wd, "source_drift_report"):
        check("W0 watchdog carries the P11 drift check", False,
              "pre-P11 watchdog: no source_drift_report")
        return
    check("W0 watchdog carries the P11 drift check", True)

    digest, _ = true_digest()
    d12 = digest[:12]

    check("W1 disk fingerprint agrees with an independent digest",
          wd.disk_source_sha12(SRC) == d12, f"{wd.disk_source_sha12(SRC)} vs {d12}")
    check("W1b a missing file reads as None, not a crash",
          wd.disk_source_sha12(os.path.join(TMP, "nope.py")) is None)

    a, i = wd.source_drift_report(
        {"A": {"source_sha256": d12}, "B": {"source_sha256": d12}}, d12)
    check("W2 matching node and disk raises nothing", a == [] and i == [], f"{a} {i}")

    a, i = wd.source_drift_report(
        {"A": {"source_sha256": "0b04473b7cbd"}, "B": {"source_sha256": d12}}, d12)
    # Two alerts here, and both are right: A is behind the deployed file AND
    # the pair no longer agree on a source. The first assertion asked for
    # exactly one and was simply wrong about the behaviour it wanted.
    check("W3 a node running a stale source ALERTS",
          any("NOT the one on disk" in x for x in a)
          and any("DIFFERENT sources" in x for x in a), str(a))
    check("W3b the alert names both hashes and the way out",
          a and "0b04473b7cbd" in a[0] and d12 in a[0]
          and "AB_RESTART_NODES.bat" in a[0], str(a))

    a, i = wd.source_drift_report(
        {"A": {"source_sha256": "aaaaaaaaaaaa"}, "B": {"source_sha256": "bbbbbbbbbbbb"}},
        "aaaaaaaaaaaa")
    check("W4 nodes on DIFFERENT sources alert about validity rules",
          any("DIFFERENT sources" in x and "A7" in x for x in a), str(a))

    a, i = wd.source_drift_report({"A": {"chain_height": 3}, "B": None}, d12)
    check("W5 a pre-v8.31 node is INFO, not an alert",
          a == [] and len(i) == 1 and "predates v8.31" in i[0], f"{a} {i}")

    a, i = wd.source_drift_report({"A": {"source_sha256": d12}}, None)
    check("W6 an unreadable source on disk alerts rather than passing quietly",
          len(a) == 1 and "unverified" in a[0], str(a))


def main():
    print(f"source under test: {SRC}")
    print(f"mode: {'FIXED (v8.31+)' if FIXED else 'PRE-FIX RECORD'}")
    if FIXED:
        fixed_checks()
        watchdog_checks()
    else:
        prefix_record()
    ok = sum(1 for _, o, _ in results if o)
    print(f"\n{ok}/{len(results)} passed")
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
