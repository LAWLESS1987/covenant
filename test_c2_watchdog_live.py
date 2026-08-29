"""test_c2_watchdog_live.py -- C2: the watchdog's kill/detect/restart/recover
path, run LIVE against real nodes for the first time.

WHAT C2 IS.  Every check in covenant_watchdog.py is a pure function taken to
33/33 (P14), 29/29 (P15) -- with its subject handed to it as an argument.  The
loop that FEEDS those functions -- health(), the 3-strike counter, start_node's
Popen, Adaptation wired to a real log file, the P16 silence contract -- had
never executed against a running chain anywhere.  A monitor whose sensing is
proven but whose sensor-to-log path is not is exactly the P14/P16 failure
class one layer up.  This suite stands up the watchdog's OWN production
topology (A:5000 <-> B:5020 <-> C:5060, the line from its NODES table, which
is deliberately not configurable) against three real v8.39 nodes and measures:

  O*  --once strict mode: honest exit code, no false alarms beyond the mock
      judge it is right to name, JUDGE UNREACHABLE when the judge is gone
      (fail-closed named -- the thing /health cannot say).
  L*  loop mode: P11 identity lines, P12 adaptation actually deduplicating on
      a real log, P15 judge identity, and the per-round heartbeat the P16
      contract line promises.
  K*  SIGKILL node C: WARN escalation 1/3 -> 3/3, ALERT, a real restart via
      the launcher, recovery with height preserved, the uptime-went-backwards
      alert and its CLEARED line.
  J*  live judge digest change: ALERT once, baseline moves (M34).
  G*  P16 measured: while alive the log's max inter-line gap honours the
      contract; SIGKILL the watchdog and the ONLY signal is the growing gap --
      the last line is ordinary, so gap-vs-contract is the one valid liveness
      test.  G3 pins that no per-line round number exists (the P16 comment
      claims one; the code has only the roll-up/CLEARED counters), so any
      gap detector MUST be timestamp-based.  If G3 ever fails, someone added
      round numbers: update the P16 comment and this check together, and mind
      that a per-line round number changes every line's text and would break
      Adaptation's dedup unless it is kept out of the observe() key.

The ollama stand-in and the run_with_ollama_judge.py launcher stub are created
INSIDE the scratch dir by this suite and never shipped: the stub launcher
boots the core with the mock judge (this sandbox has no ollama) and exists so
start_node's real code path -- the Popen with the exact argv and env the PC
uses -- is what gets exercised.

Run:  python3 test_c2_watchdog_live.py     (needs covenant_unified_v8.py,
      covenant_path_pattern.py and covenant_watchdog.py beside it; ~4 min)

Linux-first (M29: a pass here is a Linux result).  Ports 5000/5020/5060 must
be free -- they are the watchdog's own hardcoded production ports.
"""
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(tempfile.gettempdir(), "c2_watchdog_live")
INTERVAL = 3                      # watchdog --interval for the loop phase
BOOT_TIMEOUT = 90

results = []


def check(label, ok, detail=""):
    results.append((label, bool(ok)))
    print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail}", flush=True)


# ------------------------------------------------------------------ helpers
def get(url, timeout=6):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode())


def wait_health(port, budget=BOOT_TIMEOUT):
    t0 = time.time()
    while time.time() - t0 < budget:
        try:
            return get(f"http://127.0.0.1:{port}/health")
        except Exception:
            time.sleep(3)         # /chain-class reads are limited 20/60s; 3 s is the polite poll
    return None


def read_log(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


TS = re.compile(r"^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ)\s+(\w+)\s+(.*)$")


def parse_lines(text):
    out = []
    for line in text.splitlines():
        m = TS.match(line)
        if m:
            ts = datetime.strptime(m.group(1), "%Y-%m-%dT%H:%M:%SZ")
            out.append((ts.replace(tzinfo=timezone.utc), m.group(2), m.group(3)))
    return out


def gap_check(logfile, interval_s, now=None):
    """The P16 contract, as a consumer.  Returns ("ALIVE"|"DEAD"|"UNKNOWN", gap).

    With both databases present the watchdog's own startup line promises a
    line at least every interval; 5x that is generously past any slow round.
    Timestamp-based ON PURPOSE: G3 below proves the log carries no per-line
    round number, so timestamps are the only gap a script can measure."""
    lines = parse_lines(read_log(logfile))
    if not lines:
        return "UNKNOWN", None
    now = now or datetime.now(timezone.utc)
    gap = (now - lines[-1][0]).total_seconds()
    return ("ALIVE" if gap <= 5 * interval_s else "DEAD"), gap


# ------------------------------------------------------------- ollama stub
class _Judge(BaseHTTPRequestHandler):
    digest = "aaaaaaaaaaaa1111111111112222222222223333"

    def do_GET(self):
        if self.path == "/api/tags":
            body = {"models": [{"name": "qwen3:8b", "digest": _Judge.digest}]}
        elif self.path == "/api/ps":
            body = {"models": []}
        else:
            self.send_response(404); self.end_headers(); return
        raw = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *a):     # noqa: N802 -- silence
        pass


LAUNCHER_STUB = '''\
#!/usr/bin/env python3
"""run_with_ollama_judge.py -- TEST STAND-IN, created by test_c2_watchdog_live.py.

Exists only inside the scratch dir so covenant_watchdog.start_node() can run
its real restart path in a sandbox with no ollama: same argv contract as the
production launcher, but boots the core on the MOCK judge.  Never ship this."""
import os, sys, subprocess
env = dict(os.environ)
env["COVENANT_INSECURE_MOCK_JUDGE"] = "1"
env["COVENANT_JUDGE_PROVIDERS"] = "mock"
here = os.path.dirname(os.path.abspath(__file__))
cmd = [sys.executable, os.path.join(here, "covenant_unified_v8.py")] + sys.argv[1:]
sys.exit(subprocess.call(cmd, cwd=here, env=env))
'''


NODES = [("A", 5000, "127.0.0.1:5021"),
         ("B", 5020, "127.0.0.1:5001,127.0.0.1:5061"),
         ("C", 5060, "127.0.0.1:5021")]
_children = []


def start_node(nid, port, peers):
    env = dict(os.environ)
    env.update(COVENANT_INSECURE_MOCK_JUDGE="1", COVENANT_JUDGE_PROVIDERS="mock",
               COVENANT_DB_PATH=f"node{nid}_prod.db", PYTHONUNBUFFERED="1")
    out = open(os.path.join(WORK, f"boot_node{nid}.log"), "a")
    kw = {}
    if os.name != "nt":
        kw["start_new_session"] = True
    p = subprocess.Popen(
        [sys.executable, "run_with_ollama_judge.py", "--port", str(port),
         "--node-id", nid, "--genesis", "genesis.json", "--peers", peers],
        cwd=WORK, env=env, stdout=out, stderr=subprocess.STDOUT, **kw)
    _children.append(p)
    return p


def kill_tree(p):
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            os.killpg(os.getpgid(p.pid), signal.SIGKILL)
    except Exception:
        try:
            p.kill()
        except Exception:
            pass


def cleanup():
    for p in _children:
        kill_tree(p)
    if os.name != "nt":
        # the watchdog's own restarted node is not our child; match on the
        # scratch path so nothing outside this suite can be touched
        subprocess.run(["pkill", "-f", WORK], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)


def main():
    if os.path.isdir(WORK):
        shutil.rmtree(WORK, ignore_errors=True)
    os.makedirs(WORK, exist_ok=True)
    for f in ("covenant_unified_v8.py", "covenant_path_pattern.py",
              "covenant_watchdog.py"):
        shutil.copy2(os.path.join(HERE, f), WORK)
    with open(os.path.join(WORK, "run_with_ollama_judge.py"), "w") as fh:
        fh.write(LAUNCHER_STUB)

    env = dict(os.environ)
    env.update(COVENANT_INSECURE_MOCK_JUDGE="1", COVENANT_JUDGE_PROVIDERS="mock")

    # genesis: the LOADED path (A10 -- a self-minted genesis stake-locks the founder)
    p = subprocess.run([sys.executable, "covenant_unified_v8.py",
                       "--export-genesis", "genesis.json"],
                      cwd=WORK, env=dict(env, COVENANT_DB_PATH="genesis_mint.db"),
                      capture_output=True, text=True, timeout=120)
    check("S1 genesis exported for the loaded path",
          p.returncode == 0 and os.path.exists(os.path.join(WORK, "genesis.json")),
          p.stdout.strip().splitlines()[-1] if p.stdout.strip() else p.stderr[-120:])
    for n in ("genesis_mint.db", "genesis_mint.db.key"):
        try:
            os.remove(os.path.join(WORK, n))
        except OSError:
            pass

    # ollama stand-in
    judge_srv = ThreadingHTTPServer(("127.0.0.1", 0), _Judge)
    threading.Thread(target=judge_srv.serve_forever, daemon=True).start()
    judge_url = f"http://127.0.0.1:{judge_srv.server_port}/v1/chat/completions"

    # three real nodes on the watchdog's own production topology
    for nid, port, peers in NODES:
        start_node(nid, port, peers)
    healths = {nid: wait_health(port) for nid, port, _ in NODES}
    ok_boot = all(h for h in healths.values())
    check("S2 three nodes healthy on the watchdog's hardcoded topology",
          ok_boot, {k: (v or {}).get("chain_height") for k, v in healths.items()})
    src12 = {(h or {}).get("source_sha256") for h in healths.values()}
    check("S2b all three report the staged source identity (P11)",
          ok_boot and len(src12) == 1, str(src12))
    if not ok_boot:
        cleanup()
        return finish()
    pre_kill_height = healths["C"]["chain_height"]
    genesis_hash = healths["C"]["genesis"]

    wd_env = dict(env, COVENANT_LOCAL_JUDGE_URL=judge_url,
                  COVENANT_LOCAL_JUDGE_MODEL="qwen3:8b", PYTHONUNBUFFERED="1")

    # ---- O: --once strict ------------------------------------------------
    o = subprocess.run([sys.executable, "covenant_watchdog.py", "--once"],
                       cwd=WORK, env=wd_env, capture_output=True, text=True,
                       timeout=180)
    alerts = [l for l in o.stdout.splitlines() if " ALERT " in l]
    # ALERTS THAT ARE TRUE ARE NOT FALSE ALARMS.
    #
    # O2 asks whether the watchdog invents alarms, so the allowlist must hold
    # every alert that is CORRECT here -- and no more, or the check stops
    # measuring anything.
    #
    # "code sandbox unavailable" was the one failure of the first win32 run
    # of this suite (26/27, 2026-08-29). It is not a false alarm: this
    # platform has no usable `fork` start method, so the sandbox's memory,
    # process and file-size limits genuinely cannot be enforced, and the node
    # responds by REFUSING every /propose_code rather than running one
    # unbounded. The suite was written on Linux, where fork exists and the
    # alert never fires. Silencing it in the node would be the actual defect;
    # excluding it from "false alarms" is the correct fix, and it is matched
    # narrowly on that phrase so no other alert slips through with it.
    benign = ("INSECURE", "insecure", "code sandbox unavailable")
    check("O1 --once exits 1 while the mock judge is live (honest, not green)",
          o.returncode == 1 and alerts, f"rc={o.returncode} alerts={len(alerts)}")
    noisy = [a for a in alerts if not any(b in a for b in benign)]
    check("O2 no false alarm beyond the mock-judge honesty alerts",
          not noisy, "; ".join(noisy)[:200])
    check("O3 the judge probe is green against a serving endpoint",
          "JUDGE UNREACHABLE" not in o.stdout, "")

    o4 = subprocess.run([sys.executable, "covenant_watchdog.py", "--once"],
                        cwd=WORK,
                        env=dict(wd_env, COVENANT_LOCAL_JUDGE_URL="http://127.0.0.1:9/v1/chat/completions"),
                        capture_output=True, text=True, timeout=180)
    check("O4 a dead judge is a named, fail-closed ALERT (P15 live)",
          o4.returncode == 1 and "JUDGE UNREACHABLE" in o4.stdout
          and "fails closed" in o4.stdout, "")

    # ---- L: the loop -----------------------------------------------------
    # The --once passes above wrote to the SAME watchdog.log with FRESH
    # Adaptation state each (per-process), so every measurement below starts
    # from loop_mark: counting from byte 0 charges the loop for the strict
    # passes' un-deduplicated alerts.  (Found by this suite's own first run:
    # 18 "deduplicated" alerts that were really 3 processes x 6.)
    logfile = os.path.join(WORK, "logs", "watchdog.log")
    loop_mark = len(read_log(logfile))
    wd_out = open(os.path.join(WORK, "wd_stdout.log"), "a")
    kw = {"start_new_session": True} if os.name != "nt" else {}
    wd = subprocess.Popen([sys.executable, "covenant_watchdog.py",
                           "--interval", str(INTERVAL)],
                          cwd=WORK, env=wd_env, stdout=wd_out,
                          stderr=subprocess.STDOUT, **kw)
    _children.append(wd)
    time.sleep(INTERVAL * 8)
    text = read_log(logfile)[loop_mark:]
    check("L1 the startup line states the P16 silence contract, per-round floor",
          "SILENCE CONTRACT" in text and f"expect a line at least every {INTERVAL}s" in text
          and "MEANS THIS PROCESS IS DEAD" in text, "")
    p11 = re.findall(r"node ([ABC]) v=(\S+) src=(\S+) height=(\d+)", text)
    check("L2 P11 identity lines for all three nodes, version and source named",
          {i for i, *_ in p11} == {"A", "B", "C"}
          and all(v.startswith("v8.") and re.fullmatch(r"[0-9a-f]{12}", s)
                  for _, v, s, _ in p11),
          str(sorted({(i, v, s) for i, v, s, _ in p11}))[:160])
    n_rounds = len(re.findall(r"balance read for founder unavailable", text))
    ins = [l.split(" ALERT ", 1)[1] for l in text.splitlines()
           if " ALERT " in l and "INSECURE mock judge active" in l]
    # Two stable texts per node (the judge_insecure flag and the /health
    # warning), three nodes: 6 DISTINCT permanent conditions.  Dedup means
    # each distinct text is emitted once plus at most the 30-round roll-up,
    # NOT that the total is small -- the first draft of this check got that
    # wrong and failed against correct behaviour.
    worst = max((ins.count(t) for t in set(ins)), default=0)
    check("L3 adaptation dedups permanent conditions on the real log (P12)",
          n_rounds >= 5 and ins and worst <= 1 + n_rounds // 30,
          f"{len(set(ins))} distinct text(s), worst repeat {worst}, {n_rounds} rounds")
    check("L4 judge identity is named in the log (P15)",
          re.search(r"judge: qwen3:8b@[0-9a-f]{12} -- 1 model\(s\) served", text)
          is not None, "")
    lines = parse_lines(text)[1:]     # first loop line may trail the strict passes
    gaps = [(b[0] - a[0]).total_seconds() for a, b in zip(lines, lines[1:])]
    check("L5 the promised heartbeat is real: max inter-line gap within contract",
          gaps and max(gaps) <= 3 * INTERVAL, f"max gap {max(gaps or [0]):.0f}s")
    st, gap = gap_check(logfile, INTERVAL)
    check("G1 gap_check reads ALIVE while the watchdog runs",
          st == "ALIVE", f"{st} gap={gap and round(gap, 1)}s")

    # ---- K: kill node C --------------------------------------------------
    mark = len(read_log(logfile))
    kill_tree(_children[2])           # node C
    t0 = time.time()
    restarted = False
    while time.time() - t0 < 25 * INTERVAL:
        tail = read_log(logfile)[mark:]
        if "node C restarted" in tail:
            restarted = True
            break
        time.sleep(2)
    tail = read_log(logfile)[mark:]
    w1 = tail.find("node C :5060 unreachable (1/3")
    w2 = tail.find("node C :5060 unreachable (2/3")
    w3 = tail.find("node C :5060 unreachable (3/3")
    check("K1 unreachable WARNs escalate 1/3 -> 2/3 -> 3/3, in order",
          -1 < w1 < w2 < w3, f"offsets {w1},{w2},{w3}")
    check("K2 three strikes is an ALERT: node C down",
          "node C down" in tail, "")
    check("K3 the watchdog itself relaunches the node (start_node ran)",
          restarted, f"waited {time.time() - t0:.0f}s")
    hC = wait_health(5060, budget=25 * INTERVAL)
    check("K4 node C is BACK: reachable, same genesis, height preserved",
          hC is not None and hC.get("genesis") == genesis_hash
          and hC.get("chain_height", 0) >= pre_kill_height,
          f"height {hC and hC.get('chain_height')} vs {pre_kill_height}")
    time.sleep(INTERVAL * 6)
    tail = read_log(logfile)[mark:]
    check("K5 the restart is visible in state: uptime-went-backwards ALERT",
          "restarted since the last check (uptime went backwards)" in tail, "")
    check("K6 ...and it CLEARs when uptime grows again (P12 sweep)",
          re.search(r"CLEARED after \d+ round\(s\): node C: restarted since",
                    tail) is not None, "")
    check("K7 no rollback false alarm: height never 'went backwards'",
          "CHAIN HEIGHT WENT BACKWARDS" not in tail, "")
    post = read_log(logfile)[mark:]
    after_back = post[post.rfind("node C restarted"):]
    trailing_unreach = len(re.findall(r"node C :5060 unreachable", after_back))
    # NOTE a P11 line for the recovered C is deliberately NOT asserted here:
    # if C comes back with an identical /health line, Adaptation correctly
    # suppresses the repeat (this suite's first run proved it does).  K5/K6
    # already prove the watchdog is reading the recovered C; this check pins
    # that recovery also QUIETED it -- no SECOND down-alert, no WARN churn.
    # (ONE "node C down" after the restart WARN is the same pass's own alert:
    # start_node logs its WARN inline, while the pass's alerts are rendered
    # at the end of one_pass -- so the down-ALERT always trails the restart
    # line.  The first draft of this check asserted zero and failed against
    # correct ordering.)
    down_alerts = [l for l in after_back.splitlines()
                   if " ALERT " in l and "node C down" in l]
    down_cleared = [l for l in after_back.splitlines()
                    if "CLEARED" in l and "node C down" in l]
    check("K8 the 3-strike counter reset: one down-ALERT, then it CLEARs, "
          "WARNs stop",
          len(down_alerts) <= 1 and len(down_cleared) >= 1
          and trailing_unreach <= 3,
          f"{len(down_alerts)} ALERT / {len(down_cleared)} CLEARED, "
          f"{trailing_unreach} boot-window WARN(s) after restart line")

    # ---- J: live judge digest change ------------------------------------
    mark = len(read_log(logfile))
    _Judge.digest = "bbbbbbbbbbbb4444444444445555555555556666"
    time.sleep(INTERVAL * 5)
    tail = read_log(logfile)[mark:]
    m = re.search(r"JUDGE MODEL CHANGED: qwen3:8b was digest ([0-9a-f]{12}) and is "
                  r"now ([0-9a-f]{12})", tail)
    check("J1 a re-tagged judge is an ALERT naming both digests (P15 live)",
          m is not None and m.group(1) == "aaaaaaaaaaaa" and m.group(2) == "bbbbbbbbbbbb",
          m.group(0)[:90] if m else tail[-120:].replace("\n", " | "))
    time.sleep(INTERVAL * 4)
    tail = read_log(logfile)[mark:]
    fired = [l for l in tail.splitlines()
             if " ALERT " in l and "JUDGE MODEL CHANGED" in l]
    cleared = [l for l in tail.splitlines()
               if "CLEARED" in l and "JUDGE MODEL CHANGED" in l]
    check("J2 said once, then the baseline moves (M34): one ALERT, no re-fire",
          len(fired) == 1, f"{len(fired)} ALERT line(s)")
    check("J2b ...and the transition is recorded: the alert CLEARs next round",
          len(cleared) >= 1, f"{len(cleared)} CLEARED line(s)")

    # ---- G: P16, the death nothing announces ----------------------------
    check("G3 no per-line round number exists -- gap detection MUST be "
          "timestamp-based (the P16 comment overclaims; see docstring)",
          not [l for _, _, msg in parse_lines(read_log(logfile))
               for l in [msg]
               if re.search(r"\bround[ #=]\d", l)
               and "rounds]" not in l and "round(s)" not in l], "")
    kill_tree(wd)
    time.sleep(6 * INTERVAL)
    st, gap = gap_check(logfile, INTERVAL)
    last = parse_lines(read_log(logfile))[-1]
    check("G2 a SIGKILLed watchdog is detectable ONLY by the gap -- and it is",
          st == "DEAD" and gap > 5 * INTERVAL, f"gap {gap:.0f}s")
    check("G2b ...because its last line is ordinary, not a death notice "
          "(P16's point, measured)",
          "DEAD" not in last[2] and "dying" not in last[2].lower(),
          last[2][:80])

    cleanup()
    return finish()


def finish():
    p = sum(1 for _, ok in results if ok)
    print(f"\nC2-LIVE: {p}/{len(results)} passed")
    return 0 if p == len(results) else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    finally:
        cleanup()
