"""launch_check.py -- every launch gate, asked out loud, in one command.

WHY THIS EXISTS.  This project's recurring failure is not a bug in the ledger.
It is that a claim gets asserted once and then drifts invisibly (M30): the PC
"has the latest source" (false for sixteen runs, M25); `covenant_prod.bat stop`
"stops the node" (it does not, P3); the guards are "wired into daily.py" (they
were not, D4); "this is v7.0" (it was v8.30, P11); the watchdog is "checking
for staleness" (it had never once executed, P14).

So this file asks. It does not assert, restart, install, chmod, unlock or fix
anything -- `verify_deploy.py` does the restart, and this runs BEFORE it. Every
gate here reports one of three things and never anything else:

    PASS     measured, and correct
    BLOCKED  measured, and wrong -- with the exact command that fixes it
    UNKNOWN  could not be measured HERE

UNKNOWN is a first-class outcome and is never folded into PASS. A node that
cannot be reached is UNKNOWN, not OK; a check that needs Windows is UNKNOWN on
Linux, not skipped. M34's rule is that a check which stops checking on the
platform that runs production has been switched off, so where a gate has a
different correct answer per platform this asserts THAT answer rather than
stepping aside.

Exit codes:
    0   every gate PASS
    1   at least one BLOCKED          -- do not launch
    2   no BLOCKED, but some UNKNOWN  -- this is NOT a pass

Usage:
    python launch_check.py                 all gates
    python launch_check.py --json          machine-readable, for the dashboard
    python launch_check.py --gate G7       one gate
    python launch_check.py --quiet         summary only
"""
import glob
import hashlib
import json
import os
import platform
import re
import socket
import stat
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__)) or "."
WIN = sys.platform.startswith("win")
NODES = [("A", 5000), ("B", 5020), ("C", 5060)]
OLLAMA = "http://127.0.0.1:11434"

PASS, BLOCKED, UNKNOWN = "PASS", "BLOCKED", "UNKNOWN"
results = []


def gate(gid, title):
    def deco(fn):
        fn._gid, fn._title = gid, title
        GATES.append(fn)
        return fn
    return deco


GATES = []


def R(gid, title, state, detail, fix=""):
    results.append(dict(gate=gid, title=title, state=state, detail=detail, fix=fix))


def sha256_of(path, n=None):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    d = h.hexdigest()
    return d[:n] if n else d


def http_json(url, timeout=4.0):
    """Returns (obj, None) or (None, reason). Never raises."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "launch-check/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode()), None
    except Exception as e:  # noqa: BLE001 -- an unreachable service is data
        return None, "%s: %s" % (type(e).__name__, e)


def node_health(port, timeout=4.0):
    """/health for a node, or None. Never raises -- unreachable is DATA."""
    return http_json("http://127.0.0.1:%d/health" % port, timeout=timeout)[0]


def port_busy(port):
    s = socket.socket()
    s.settimeout(0.6)
    try:
        s.connect(("127.0.0.1", port))
        return True
    except Exception:
        return False
    finally:
        s.close()


# ------------------------------------------------------------------ G1 files
def _manifest_sha(rel):
    """The manifest's OWN hash function, imported rather than reimplemented.

    2026-09-04: verify_bundle started folding CRLF to LF for text, so a
    manifest verifies the same on Windows and on Linux. This gate kept its own
    byte-exact copy of the hash, so the two disagreed on all 70 files git
    stores with LF and checks out with CRLF, and G1 went BLOCKED against a
    manifest that was correct. Two definitions of one number is the defect;
    there is now one, and it lives with the manifest.

    sha256_of() above is deliberately NOT changed: it also hashes the core
    source to compare against what a RUNNING node reports, and the node hashes
    its own bytes. That comparison must stay byte-exact.
    """
    try:
        import verify_bundle
        return verify_bundle.sha(rel)
    except Exception:                                        # noqa: BLE001
        return sha256_of(os.path.join(HERE, rel))


@gate("G1", "Bundle integrity -- every shipped file hashes to the manifest")
def g1():
    man = os.path.join(HERE, "MANIFEST.sha256")
    if not os.path.exists(man):
        return R("G1", g1._title, UNKNOWN, "MANIFEST.sha256 is not here.",
                 "Run: python verify_bundle.py --write")
    bad, missing, n = [], [], 0
    for line in open(man, encoding="utf-8"):
        line = line.rstrip("\n")
        if not line or line.startswith("#"):
            continue
        want, rel = line.split("  ", 1)
        p = os.path.join(HERE, rel)
        n += 1
        if not os.path.exists(p):
            missing.append(rel)
        elif _manifest_sha(rel) != want:
            bad.append(rel)
    if not bad and not missing:
        return R("G1", g1._title, PASS, "%d files, all hashing to the manifest." % n)
    d = "%d checked; %d changed; %d missing." % (n, len(bad), len(missing))
    if bad:
        d += " changed: " + ", ".join(bad[:6])
    if missing:
        d += " missing: " + ", ".join(missing[:6])
    return R("G1", g1._title, BLOCKED, d,
             "A changed file is either an edit you meant (re-run "
             "`python verify_bundle.py --write`) or a delivery that did not "
             "land. Do not launch until you know which.")


# ------------------------------------------------------------- G2 companions
COMPANIONS = {
    "covenant_unified_v8.py": ["covenant_path_pattern.py"],
    "test_a1_kill_matrix.py": ["test_a9_relay_race.py"],
    "test_security_audit.py": ["covenant_trading_bridge.py"],
    "daily.py": ["guards.py"],
}


@gate("G2", "Companion imports sit beside the files that need them")
def g2():
    miss = []
    for owner, needs in COMPANIONS.items():
        if not os.path.exists(os.path.join(HERE, owner)):
            continue
        for n in needs:
            if not os.path.exists(os.path.join(HERE, n)):
                miss.append("%s needs %s" % (owner, n))
    if miss:
        return R("G2", g2._title, BLOCKED, "; ".join(miss),
                 "Copy the named file into this folder. A missing companion "
                 "reads as a test regression (M37) and is not one.")
    return R("G2", g2._title, PASS, "all present")


# ---------------------------------------------------------------- G3 runtime
@gate("G3", "Python runtime and the packages the node imports at boot")
def g3():
    need = ["flask", "werkzeug", "cryptography", "requests"]
    opt = ["waitress", "xrpl"]
    missing = [m for m in need if not _importable(m)]
    missing_opt = [m for m in opt if not _importable(m)]
    ver = platform.python_version()
    if missing:
        return R("G3", g3._title, BLOCKED,
                 "python %s; missing required: %s" % (ver, ", ".join(missing)),
                 "pip install -r requirements.txt")
    d = "python %s; required imports present." % ver
    if "waitress" in missing_opt:
        return R("G3", g3._title, BLOCKED,
                 d + " waitress is MISSING, so W1's bounded pool is inert and "
                     "the node falls back to werkzeug's DEV server -- one "
                     "unbounded thread per connection on the port you expose.",
                 "pip install vendor/waitress-3.0.2-py3-none-any.whl")
    if missing_opt:
        d += " optional absent: %s (xrpl is only needed for the XRP path)." % ", ".join(missing_opt)
    return R("G3", g3._title, PASS, d)


def _importable(mod):
    try:
        __import__(mod)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------- G4 genesis
@gate("G4", "One shared canonical genesis, not a self-mint per node")
def g4():
    p = os.path.join(HERE, "genesis.json")
    if not os.path.exists(p):
        return R("G4", g4._title, BLOCKED,
                 "genesis.json is not here. Every node would mint its own, "
                 "they could never converge, and supply would grow by 1000 "
                 "per node.",
                 "python covenant_unified_v8.py --node-id FOUNDER "
                 "--export-genesis genesis.json   (ONCE, then share the file)")
    try:
        g = json.load(open(p, encoding="utf-8"))
    except Exception as e:
        return R("G4", g4._title, BLOCKED, "genesis.json is not valid JSON: %s" % e,
                 "Re-export it; do not hand-edit a signed genesis.")
    h = g.get("hash") or g.get("block", {}).get("hash") or ""
    return R("G4", g4._title, PASS,
             "present, %d bytes, hash %s" % (os.path.getsize(p), (h or "?")[:12]))


# ------------------------------------------------------------------ G5 judge
@gate("G5", "The ethics judge is reachable -- it fails CLOSED, silently")
def g5():
    provs = os.environ.get("COVENANT_JUDGE_PROVIDERS", "")
    insecure = os.environ.get("COVENANT_INSECURE_MOCK_JUDGE", "")
    if provs == "mock" and insecure == "1":
        return R("G5", g5._title, BLOCKED,
                 "COVENANT_JUDGE_PROVIDERS=mock with the insecure flag set. "
                 "The gate is keyword matching and adversarial transactions "
                 "are KNOWN to pass it. Correct for a test rig, never for a "
                 "launch.",
                 "unset both, or set COVENANT_JUDGE_PROVIDERS=local (Ollama) "
                 "or =claude with ANTHROPIC_API_KEY")
    # 2026-09-04: this gate asked "is Ollama up?" and reported a node without
    # it as one that "rejects 100% of transactions". That was true until
    # ops/quorum_policy.json existed. With a deferring seat the order is the
    # distilled student, then Ollama, then a judge on a GitHub runner, and a
    # trained student answers in microseconds with no model server at all --
    # measured on the deployed wiring: a theft REFUSED and a gift ADMITTED in
    # 0 seconds with Ollama gone. So the gate now asks the question it meant to
    # ask, which is whether ANY judge would answer, and it names which one.
    student = None
    try:
        import covenant_judge_defer as _D
        import covenant_judge_fallback as _FB
        _pol = _D.load_policy()
        if "deferring" in str(_pol.get("providers", "")):
            _m = _FB.FallbackModel.load()
            student = {"trained": _m.n_examples >= _FB.MIN_EXAMPLES,
                       "n": _m.n_examples, "digest": getattr(_m, "digest", "?"),
                       "github": bool(_pol.get("github_when_local_down"))}
    except Exception:                                        # noqa: BLE001
        student = None
    tags, err = http_json(OLLAMA + "/api/tags", timeout=6)
    has_key = bool(os.environ.get("ANTHROPIC_API_KEY") or
                   os.environ.get("OPENAI_API_KEY") or
                   os.environ.get("GOOGLE_API_KEY"))
    if tags is None and student and student["trained"]:
        return R("G5", g5._title, PASS,
                 "no Ollama, and it is not needed: ops/quorum_policy.json names a "
                 "deferring seat and the distilled student is trained (%d examples, "
                 "model %s), so a verdict is returned locally in microseconds.%s"
                 % (student["n"], student["digest"],
                    " The GitHub runner backs it when the student abstains."
                    if student["github"] else ""))
    if tags is None and student and not student["trained"]:
        return R("G5", g5._title, BLOCKED,
                 "The seat defers per ops/quorum_policy.json, but the student is "
                 "UNTRAINED (%d examples, %d needed), Ollama does not answer and no "
                 "provider key is set. Every payload would fall through to the "
                 "GitHub runner, and the gate fails closed when that is unreachable."
                 % (student["n"], _FB.MIN_EXAMPLES),
                 "run: python covenant_nightly.py --study 12 --cycle 4")
    if tags is not None:
        models = [m.get("name", "?") for m in tags.get("models", [])]
        if not models:
            return R("G5", g5._title, BLOCKED,
                     "Ollama answers but serves NO models. covenant_prod.bat's "
                     "next step is judge_bench.fit_check(), which aborts.",
                     "ollama pull qwen3:8b")
        return R("G5", g5._title, PASS,
                 "Ollama up, %d model(s): %s" % (len(models), ", ".join(models[:4])))
    if has_key:
        return R("G5", g5._title, PASS,
                 "no local Ollama (%s) but a cloud provider key is set in the "
                 "environment." % (err or "").split(":")[0])
    return R("G5", g5._title, BLOCKED,
             "No judge reachable: Ollama on 11434 does not answer (%s) and no "
             "provider key is set. A node in this state boots, serves /chain, "
             "peers correctly, reports healthy -- and rejects 100%% of "
             "transactions." % (err or "no reason"),
             "Start Ollama, or set ANTHROPIC_API_KEY.")


# ----------------------------------------------------------------- G6 memory
@gate("G6", "The judge model fits in RAM without paging")
def g6():
    tags, err = http_json(OLLAMA + "/api/tags", timeout=6)
    if tags is None:
        try:
            import covenant_judge_defer as _D
            import covenant_judge_fallback as _FB
            if "deferring" in str(_D.load_policy().get("providers", "")):
                _m = _FB.FallbackModel.load()
                if _m.n_examples >= _FB.MIN_EXAMPLES:
                    _kb = os.path.getsize(_FB.MODEL_PATH) / 1024.0
                    return R("G6", g6._title, PASS,
                             "no model has to fit: the seat defers to the distilled "
                             "student, which is %.0f KB of JSON read into the node's "
                             "own process -- against the 4,983 MB the 8B judge needed "
                             "on a box with about 2,300 MB free." % _kb)
        except Exception:                                    # noqa: BLE001
            pass
        return R("G6", g6._title, UNKNOWN,
                 "cannot size the model: Ollama not answering.")
    biggest = 0
    name = "?"
    for m in tags.get("models", []):
        sz = int(m.get("size", 0) or 0)
        if sz > biggest:
            biggest, name = sz, m.get("name", "?")
    model_mb = biggest / (1024 * 1024)
    free_mb = _free_mb()
    if free_mb is None:
        return R("G6", g6._title, UNKNOWN,
                 "model %s is %.0f MB; available memory could not be read here."
                 % (name, model_mb))
    if free_mb < model_mb:
        return R("G6", g6._title, BLOCKED,
                 "model %s is %.0f MB against %.0f MB available -- the judge "
                 "loads by paging. P12 measured exactly this on the production "
                 "box (3,535 MB free against a ~5,200 MB model)."
                 % (name, model_mb, free_mb),
                 "Close what you can (AK_FREE_RAM.bat), or use a smaller model.")
    return R("G6", g6._title, PASS,
             "model %s %.0f MB, %.0f MB available." % (name, model_mb, free_mb))


def _free_mb():
    try:
        if WIN:
            import ctypes

            class MS(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong),
                            ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong),
                            ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong),
                            ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong),
                            ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
            m = MS()
            m.dwLength = ctypes.sizeof(MS)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            return m.ullAvailPhys / (1024 * 1024)
        for line in open("/proc/meminfo"):
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) / 1024
    except Exception:
        return None
    return None


# ------------------------------------------------------------------ G7 ports
@gate("G7", "Port arithmetic -- --port N occupies N, N+1 and N+11")
def g7():
    spans = {}
    for nid, base in NODES:
        spans[nid] = [base, base + 1, base + 11]
    flat = [p for v in spans.values() for p in v]
    if len(set(flat)) != len(flat):
        return R("G7", g7._title, BLOCKED,
                 "configured nodes overlap: %s" % spans,
                 "Space nodes at least 20 apart (M2).")
    busy = {nid: [p for p in ps if port_busy(p)] for nid, ps in spans.items()}
    live = {nid: b for nid, b in busy.items() if b}
    if not live:
        return R("G7", g7._title, PASS,
                 "all ports free -- nothing is running, a cold start is clean.")
    # A busy port is only "expected" if OUR node is what is holding it. If no
    # node answers /health and a port is taken, something ELSE has it, and the
    # node that wants it will fail preflight and exit -- visibly, since v8.15,
    # but only in a console log nobody is reading.
    ours = {nid for nid, port in NODES if node_health(port, 2.0) is not None}
    foreign = {nid: b for nid, b in live.items() if nid not in ours}
    if foreign:
        return R("G7", g7._title, BLOCKED,
                 "port(s) held by something that is NOT a covenant node: " +
                 "; ".join("%s %s" % (k, v) for k, v in sorted(foreign.items())) +
                 ". preflight_port_check will refuse to start that node.",
                 "AD_DIAG_PORTS.bat shows what holds them; then free it, or "
                 "move that node to a clear block of three (N, N+1, N+11) at "
                 "least 20 from its neighbours.")
    return R("G7", g7._title, PASS,
             "in use by our own nodes, as expected: " +
             "; ".join("%s %s" % (k, v) for k, v in sorted(live.items())))


# ------------------------------------------------------------------- G8 keys
@gate("G8", "Identity keys are owner-only -- and on NTFS the mode bit lies (P9)")
def g8():
    keys = [f for f in os.listdir(HERE) if f.endswith(".db.key")]
    if not keys:
        return R("G8", g8._title, UNKNOWN,
                 "no *.db.key here yet -- they are created on first node start.")
    if not WIN:
        bad = []
        for k in keys:
            mode = stat.S_IMODE(os.stat(os.path.join(HERE, k)).st_mode)
            if mode & 0o077:
                bad.append("%s is %s" % (k, oct(mode)))
        if bad:
            return R("G8", g8._title, BLOCKED, "; ".join(bad),
                     "chmod 600 *.db.key")
        return R("G8", g8._title, PASS,
                 "%d key file(s), all 0600." % len(keys))
    # win32: st_mode carries no ACL information at all, so the POSIX check is
    # not a weak check -- it is a constant. Ask the ACL instead.
    unprotected, unreadable = [], []
    for k in keys:
        verdict = _acl_owner_only(os.path.join(HERE, k))
        if verdict is None:
            unreadable.append(k)
        elif verdict is False:
            unprotected.append(k)
    if unreadable:
        return R("G8", g8._title, UNKNOWN,
                 "icacls could not be read for: %s" % ", ".join(unreadable))
    if unprotected:
        return R("G8", g8._title, BLOCKED,
                 "%d key file(s) readable beyond the owner: %s. These ARE the "
                 "operator credential and the genesis mint key."
                 % (len(unprotected), ", ".join(unprotected)),
                 "ops\\fix_key_acl.bat   (icacls /inheritance:r /grant:r)")
    return R("G8", g8._title, PASS,
             "%d key file(s); NTFS ACL restricted to owner + SYSTEM." % len(keys))


def _acl_owner_only(path):
    """True / False / None(unknown). Reads icacls, changes nothing."""
    try:
        out = subprocess.run(["icacls", path], capture_output=True, text=True,
                             timeout=15)
        if out.returncode != 0:
            return None
    except Exception:
        return None
    allowed = re.compile(r"(NT AUTHORITY\\SYSTEM|BUILTIN\\Administrators|"
                         r"OWNER RIGHTS|CREATOR OWNER)", re.I)
    me = (os.environ.get("USERNAME") or "").lower()
    for raw in out.stdout.splitlines():
        line = raw.strip()
        if not line or line.startswith("Successfully") or path in line and ":(" not in line:
            continue
        m = re.match(r"^(?:.*?)([^:]+):\(", line) if ":(" in line else None
        who = (m.group(1).strip() if m else "").lower()
        if not who:
            continue
        if allowed.search(who):
            continue
        if me and me in who:
            continue
        return False
    return True


# ---------------------------------------------------- G9 three-claims (M38)
@gate("G9", "Project, disk and RUNNING process are three claims -- do they agree?")
def g9():
    core = os.path.join(HERE, "covenant_unified_v8.py")
    if not os.path.exists(core):
        return R("G9", g9._title, BLOCKED, "covenant_unified_v8.py is not here.",
                 "Copy the delivered core into this folder.")
    disk12 = sha256_of(core, 12)
    ver = "?"
    for line in open(core, encoding="utf-8", errors="replace"):
        if line.startswith("COVENANT_VERSION"):
            ver = line.split("=", 1)[1].strip().strip('"\'')
            break
    rows, unknown, mismatch = [], [], []
    for nid, port in NODES:
        h = node_health(port)
        if h is None:
            unknown.append(nid)
            rows.append("%s UNREACHABLE" % nid)
            continue
        run12 = str(h.get("source_sha256", ""))[:12]
        runver = h.get("version", "?")
        # NOTE: /health's field is NAMED source_sha256 and CONTAINS
        # CORE_SOURCE_SHA12 -- 12 hex chars, 48 bits (A25). This is a drift
        # check, not a tamper check. Claim 1 (G1) compares the full 64.
        if run12 == disk12:
            rows.append("%s %s == disk" % (nid, runver))
        else:
            mismatch.append(nid)
            rows.append("%s running %s %s != disk %s %s"
                        % (nid, runver, run12, ver, disk12))
    d = "disk %s %s | %s" % (ver, disk12, "; ".join(rows))
    if mismatch:
        return R("G9", g9._title, BLOCKED, d,
                 "The file on disk is not what is executing. Run "
                 "AM_VERIFY_AND_RESTART.bat (which now refuses if the judge "
                 "is down -- P17).")
    if unknown:
        return R("G9", g9._title, UNKNOWN, d + "  -- a node that cannot be "
                 "reached is UNKNOWN, never OK.")
    return R("G9", g9._title, PASS, d)


# ----------------------------------------------------------- G10 watchdog
@gate("G10", "The watchdog is alive -- a quiet monitor is not a healthy one")
def g10():
    p = os.path.join(HERE, "logs", "watchdog.log")
    if not os.path.exists(p):
        return R("G10", g10._title, UNKNOWN, "logs/watchdog.log does not exist yet.")
    age = time.time() - os.path.getmtime(p)
    # A gate must not refuse the action that fixes it. If NOTHING is running,
    # a stale watchdog log is the expected state of a cold machine, and
    # blocking on it deadlocks the launch: the watchdog is dead BECAUSE there
    # has been no start, and the start is what this gate would be refusing.
    # The real P16 condition -- the one worth blocking on -- is a node that
    # answers while its monitor does not, because that is the case where
    # somebody is reading a log that says everything is fine.
    anyone_up = any(node_health(port, 2.0) is not None
                    for _nid, port in NODES)
    last = ""
    try:
        with open(p, "rb") as fh:
            fh.seek(max(0, os.path.getsize(p) - 4096))
            tail = fh.read().decode("utf-8", "replace").strip().splitlines()
            last = tail[-1][:150] if tail else ""
    except Exception:
        pass
    # The balance check logs every round when both databases are present, so
    # the real bound is ~60s, not the roll-up's 30 rounds. Publishing the weak
    # floor would teach a reader to tolerate a watchdog dead for 29 minutes,
    # which is the failure P16 exists to prevent.
    if age > 300 and not anyone_up:
        return R("G10", g10._title, UNKNOWN,
                 "last line was %d min ago and NO node answers /health -- so "
                 "nothing is running and this is a cold start, not a restart. "
                 "The stale log is the expected state, and starting is what "
                 "fixes it. Last line, for the record: %r" % (age / 60, last))
    if age > 300:
        return R("G10", g10._title, BLOCKED,
                 "last line was %d min ago, against a ~60 second bound, while "
                 "a node IS answering. The watchdog process is DEAD and the "
                 "chain is not. Its final line still asserts that everything "
                 "is healthy, and will go on asserting it: %r"
                 % (age / 60, last),
                 "AB_RESTART_NODES.bat also restarts the watchdog "
                 "(covenant_prod.bat starts a fresh one).")
    return R("G10", g10._title, PASS,
             "wrote %ds ago: %r" % (age, last))


# -------------------------------------------------------------- G11 mainnet
@gate("G11", "XRP mainnet gate -- reports its state, never opens it")
def g11():
    proof = os.path.join(HERE, "xrp_testnet_proof.json")
    policy = os.path.join(HERE, "xrp_mainnet_policy.json")
    have_proof = os.path.exists(proof)
    have_policy = os.path.exists(policy)
    bits = []
    bits.append("testnet proof: " + ("PRESENT" if have_proof else "ABSENT"))
    bits.append("policy: " + ("PRESENT" if have_policy else "ABSENT"))
    if have_policy and not WIN:
        mode = stat.S_IMODE(os.stat(policy).st_mode)
        bits.append("policy mode %s" % oct(mode))
        if mode & 0o077:
            bits.append("-> MainnetPolicy.load will REFUSE")
    if have_policy and WIN:
        bits.append("policy mode reads 0o666 on NTFS whatever its ACL says, so "
                    "MainnetPolicy.load refuses on this machine unconditionally "
                    "(P9) -- see docs/P9_WINDOWS_OWNER_ONLY.md")
    # M48, the SECOND instance in one evening and this one shipped AFTER the
    # rule was written. A shut mainnet gate is the CORRECT DEFAULT and has
    # nothing to do with starting a node -- reporting it as BLOCKED made
    # AN_LAUNCH.bat refuse the entire launch because real money was safely
    # locked. "Locked" is a pass-shaped fact wearing a blocked label.
    #
    # This gate now BLOCKS only on an INCONSISTENCY -- a policy that exists and
    # is readable by more than its owner, or a proof file that is malformed --
    # because those are states where somebody has half-opened the gate.
    if not have_proof and not have_policy:
        return R("G11", g11._title, PASS,
                 "; ".join(bits) + ". The gate is SHUT, which is the correct "
                 "default: the XRP submission path has never executed on any "
                 "network and nothing here can open it. Starting a node does "
                 "not touch this.")
    if have_proof:
        try:
            h = json.load(open(proof, encoding="utf-8")).get("tx_hash", "")
        except Exception as e:
            return R("G11", g11._title, BLOCKED,
                     "; ".join(bits) + ". The proof file is not readable JSON "
                     "(%s) -- a malformed proof is not a safe state." % e,
                     "Delete it and re-run python test_xrp_live.py")
        if len(h) != 64:
            return R("G11", g11._title, BLOCKED,
                     "; ".join(bits) + ". The proof file does not carry a "
                     "64-character tx hash, so require_testnet_proof will "
                     "refuse it anyway.",
                     "Delete it and re-run python test_xrp_live.py")
    if have_policy and not WIN:
        mode = stat.S_IMODE(os.stat(policy).st_mode)
        if mode & 0o077:
            return R("G11", g11._title, BLOCKED,
                     "; ".join(bits) + ". Anything that can edit this file can "
                     "raise your own spending limits.",
                     "chmod 600 xrp_mainnet_policy.json")
    return R("G11", g11._title, UNKNOWN,
             "; ".join(bits) + ". The gate is PART-OPEN. Whether the policy "
             "names an address you have checked against its source is not "
             "something this script can know.")


# --------------------------------------------------------------- G12 suites
@gate("G12", "When did the suites last run, and on which platform?")
def g12():
    # Until 2026-09-02 this gate could only ever say UNKNOWN: a filename is not
    # a claim about the platform or the source. But the runner's own transcript
    # IS -- covenant_one.py prints the platform, the core's sha256 and the
    # tally at the top and bottom of every sweep. So read the newest full
    # sweep transcript and MEASURE: same core as on disk, this platform, zero
    # failed, and not older than a week. Anything short of all four is still
    # UNKNOWN, with the reason, never PASS.
    import hashlib
    cands = [os.path.join(HERE, n) for n in ("ONE_SWEEP.txt", "ONE_RUN.txt", "ONE_RUN_stdout.txt")]
    cands += glob.glob(os.path.join(HERE, "docs", "results", "SWEEP_RESULTS_*_win32.txt"))
    cands = [c for c in cands if os.path.exists(c)]
    # The sweep that is asking this question is writing a transcript of its
    # own right now, and that file has no tally yet: it is not evidence, it
    # is the question. covenant_one names it in COVENANT_ONE_TRANSCRIPT and
    # asks the gates a second time once its tally is on disk. Without this,
    # the first sweep after ANY core change read UNKNOWN here for a reason
    # that pointed the wrong way ("a --check transcript?") -- 2026-09-05,
    # the sweep after the A1 fix.
    inflight = os.environ.get("COVENANT_ONE_TRANSCRIPT", "")
    if inflight:
        key = os.path.normcase(os.path.abspath(inflight))
        cands = [c for c in cands if os.path.normcase(os.path.abspath(c)) != key]
    note = (" The transcript this sweep is writing (%s) is not evidence until its "
            "tally is written; covenant_one asks again then." % os.path.basename(inflight)
            if inflight else "")
    if not cands:
        return R("G12", g12._title, UNKNOWN, "no sweep transcript in this folder." + note,
                 "python covenant_one.py --out ONE_SWEEP.txt")
    core = os.path.join(HERE, "covenant_unified_v8.py")
    try:
        disk = hashlib.sha256(open(core, "rb").read()).hexdigest()[:12]
    except OSError:
        disk = "?"
    is_win = sys.platform.startswith("win")
    reasons = []
    for path in sorted(cands, key=os.path.getmtime, reverse=True):
        try:
            text = open(path, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        rel = os.path.relpath(path, HERE)
        age_d = (time.time() - os.path.getmtime(path)) / 86400.0
        m_sha = re.search(r"sha256 ([0-9a-f]{12})", text)
        m_plat = re.search(r"platform\s+(.+)", text)
        m_run = re.search(r"suites run\s+(\d+)", text)
        m_fail = re.search(r"checks failed\s+(\d+)", text)
        sha = m_sha.group(1) if m_sha else "?"
        plat = m_plat.group(1).strip() if m_plat else "?"
        ran = int(m_run.group(1)) if m_run else 0
        failed = int(m_fail.group(1)) if m_fail else -1
        plat_ok = (("Windows" in plat) == is_win) if plat != "?" else False
        when = time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(path)))
        if ran > 0 and failed == 0 and sha == disk and plat_ok and age_d <= 7:
            return R("G12", g12._title, PASS,
                     "%s: %d suites, 0 failed, core %s == disk, platform %s, %s (%.1f d old)."
                     % (rel, ran, sha, plat, when, age_d))
        why = []
        if ran == 0: why.append("no sweep tally (a --check transcript?)")
        if failed > 0: why.append("%d failed" % failed)
        if failed < 0: why.append("no tally line")
        if sha != disk: why.append("core %s != disk %s" % (sha, disk))
        if not plat_ok: why.append("platform '%s' is not this one" % plat)
        if age_d > 7: why.append("%.0f days old" % age_d)
        reasons.append("%s (%s): %s" % (rel, when, "; ".join(why)))
    return R("G12", g12._title, UNKNOWN,
             "no transcript proves a green sweep of THIS core on THIS platform within a week -- "
             + " | ".join(reasons[:3]) + note,
             "python covenant_one.py --out ONE_SWEEP.txt")


def main():
    argv = sys.argv[1:]
    want = None
    if "--gate" in argv:
        want = argv[argv.index("--gate") + 1].upper()
    for fn in GATES:
        if want and fn._gid != want:
            continue
        try:
            fn()
        except Exception as e:  # a gate that crashes is UNKNOWN, never PASS
            R(fn._gid, fn._title, UNKNOWN, "gate raised %s: %s" % (type(e).__name__, e))

    if "--json" in argv:
        print(json.dumps(dict(
            when=time.strftime("%Y-%m-%dT%H:%M:%S"),
            host=platform.node(), platform=sys.platform,
            results=results), indent=1))
    else:
        quiet = "--quiet" in argv
        w = max((len(r["state"]) for r in results), default=7)
        print("=" * 74)
        print("launch_check  %s  %s  (%s)"
              % (time.strftime("%Y-%m-%d %H:%M:%S"), HERE, sys.platform))
        print("=" * 74)
        for r in results:
            print("%-4s %-*s %s" % (r["gate"], w, r["state"], r["title"]))
            if not quiet:
                print("       %s" % r["detail"])
                if r["fix"] and r["state"] != PASS:
                    print("       FIX: %s" % r["fix"])
                print("")
        nb = sum(1 for r in results if r["state"] == BLOCKED)
        nu = sum(1 for r in results if r["state"] == UNKNOWN)
        np_ = sum(1 for r in results if r["state"] == PASS)
        print("-" * 74)
        print("%d PASS   %d BLOCKED   %d UNKNOWN" % (np_, nb, nu))
        if nb:
            print("DO NOT LAUNCH. Fix the BLOCKED gates above.")
        elif nu:
            print("NOT A PASS. %d gate(s) could not be measured here." % nu)
        else:
            print("All gates pass.")
    nb = sum(1 for r in results if r["state"] == BLOCKED)
    nu = sum(1 for r in results if r["state"] == UNKNOWN)
    return 1 if nb else (2 if nu else 0)


if __name__ == "__main__":
    sys.exit(main())
