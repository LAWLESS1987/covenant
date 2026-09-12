"""entry.py -- the service entry module, and the ONLY Python file Chaquopy
packages as source. Everything the Termux start script does, done in-process:
make files/core look like a clone root to the launcher (cwd = clone root, db
and key beside the code), then run the tracked launcher file itself.

It exports NOTHING about judge providers (test_a93's contract): the launcher's
own defaults decide, as on any clone -- the operator's ops/quorum_policy.json if
one is placed in files/core/ops, else deferring,semantic.

judge_text() is the SHARE-IN path: the same quorum and sentinel the node builds,
in whichever process asks, with no HTTP endpoint added to the node.
"""
import json
import os
import runpy
import sys
import time
import traceback
import zipfile

DEFAULTS = {"port": 5000, "pc_peer": "", "node_id": "phone", "autostart": False}
LAUNCHER = "run_node.py"      # the tracked launcher, byte for byte
REQUIRED = (LAUNCHER, "covenant_unified_v8.py", "genesis.json",
            "semantic_judge_model.json", "fallback_model.json")


def _settings(files_dir):
    try:
        with open(os.path.join(files_dir, "settings.json"), encoding="utf-8") as f:
            s = json.load(f)
    except Exception:                                             # noqa: BLE001
        s = {}
    return {**DEFAULTS, **{k: v for k, v in s.items() if k in DEFAULTS}}


def _exit(files_dir, text):
    """last_exit.txt: shown by the Activity; deleted on the next Start."""
    tmp = os.path.join(files_dir, "last_exit.txt.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("%s pid=%d\n%s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), os.getpid(), text))
    os.replace(tmp, os.path.join(files_dir, "last_exit.txt"))


def _tail(path, n):
    try:
        with open(path, errors="replace") as f:
            return "".join(f.readlines()[-n:])
    except Exception:                                             # noqa: BLE001
        return ""


class _Tee:
    """stdout/stderr also to files/node.log (Chaquopy already routes them to logcat)."""
    def __init__(self, a, b): self.a, self.b = a, b
    def write(self, s): self.a.write(s); self.b.write(s); self.b.flush()
    def flush(self): self.a.flush(); self.b.flush()


def ensure_core(files_dir, apk_path):
    """Extract assets/core/* from the APK (a zip) into files/core on EVERY start,
    overwriting only the allowlisted names. The db, the .key, ops/*.jsonl, an
    operator's ops/quorum_policy.json and __pycache__ are never touched.
    About 1.5 MB, sub-second. Returns the core directory."""
    core = os.path.join(files_dir, "core")
    os.makedirs(os.path.join(core, "ops"), exist_ok=True)
    with zipfile.ZipFile(apk_path) as z:
        for m in z.namelist():
            if m.startswith("assets/core/") and not m.endswith("/"):
                with z.open(m) as src, open(os.path.join(core, os.path.basename(m)), "wb") as dst:
                    dst.write(src.read())
    return core


def main(files_dir, apk_path):
    core = ensure_core(files_dir, apk_path)
    # log: rotate node.log -> node.log.1, tee stdout/stderr
    log = os.path.join(files_dir, "node.log")
    if os.path.exists(log):
        os.replace(log, log + ".1")
    lf = open(log, "a", buffering=1, encoding="utf-8", errors="replace")
    sys.stdout = _Tee(sys.stdout, lf)
    sys.stderr = _Tee(sys.stderr, lf)
    s = _settings(files_dir)
    port, node_id, peer = int(s["port"]), str(s["node_id"]), str(s["pc_peer"]).strip()
    for name in REQUIRED:
        if not os.path.isfile(os.path.join(core, name)):
            _exit(files_dir, "missing %s in %s" % (name, core))
            return
    # cwd = clone root, exactly like covenant_phone.sh: the db and the .db.key land
    # beside the code, --genesis genesis.json resolves, and covenant_judge_defer's
    # HERE/ops sees the same folder it sees on Termux.
    os.chdir(core)
    # one phone-only guard and nothing else: Android reports 'fork' available;
    # refuse code-proposal sandboxing rather than fork inside ART. NO providers,
    # NO override, NO local-judge variables here.
    os.environ["COVENANT_FORCE_NO_SANDBOX"] = "1"
    # The API (/health, the dashboard, every route) answers only this phone:
    # the app polls 127.0.0.1, a USB tunnel lands on 127.0.0.1, and nothing on
    # the Wi-Fi can read it. The peer port stays open so the PC node can talk.
    os.environ.setdefault("COVENANT_API_HOST", "127.0.0.1")
    sys.path.insert(0, core)
    argv = [LAUNCHER, "--real", "--port", str(port), "--node-id", node_id, "--genesis", "genesis.json"]
    if peer:
        argv += ["--peers", peer]
    sys.argv = argv
    try:
        # the tracked launcher, byte for byte: its judge imports, apply_policy,
        # banner and cov.main(); never returns while the node lives
        runpy.run_path(os.path.join(core, LAUNCHER), run_name="__main__")
        _exit(files_dir, "main() returned")
    except SystemExit as e:                                       # preflight: port taken, peer answered like HTTP, self-peer
        _exit(files_dir, "SystemExit %s\n%s" % (e.code, _tail(log, 40)))
    except BaseException:
        _exit(files_dir, traceback.format_exc()[-2000:])
        raise


# ---------------------------------------------------------------- share in

_SENTINEL = None


def _sentinel(files_dir, apk_path):
    """The node's own quorum and sentinel, built the way covenant_unified_v8's
    master builds them (build_semantic_quorum + ReasoningSentinel), once per process."""
    global _SENTINEL
    if _SENTINEL is not None:
        return _SENTINEL
    core = ensure_core(files_dir, apk_path)
    os.chdir(core)
    os.environ["COVENANT_FORCE_NO_SANDBOX"] = "1"
    if core not in sys.path:
        sys.path.insert(0, core)
    import importlib
    launcher = importlib.import_module(LAUNCHER[:-3])           # wires the seats; applies policy or the default
    cov = launcher.cov
    judge = cov.build_semantic_quorum()
    _SENTINEL = (cov, cov.ReasoningSentinel(judge, cov.DIVINE_PRINCIPLES))
    return _SENTINEL


def judge_text(files_dir, apk_path, text):
    """Judge a shared text with the same gate the node uses. Returns JSON."""
    try:
        cov, sentinel = _sentinel(files_dir, apk_path)
        tx = cov.Transaction(sender_pubkey="shared", receiver="collective",
                             data={"origin": "human", "kind": "shared", "message": str(text)[:4000]},
                             amount=0.0, benefit_score=0.5)
        ok, message, _benefit, result = sentinel.evaluate_transaction(tx)
        alleges_nothing = bool(result is not None and not ok and (
            getattr(result, "not_understood", False) or getattr(result, "uncertain", False)))
        return json.dumps({
            "admitted": bool(ok),
            "alleges_nothing": alleges_nothing,
            "message": str(message)[:2000],
            "judge": getattr(result, "judge_id", "") if result is not None else "",
        }, ensure_ascii=False)
    except Exception:                                             # noqa: BLE001
        return json.dumps({"admitted": False, "alleges_nothing": False,
                           "message": "could not judge: " + traceback.format_exc()[-800:], "judge": ""})
