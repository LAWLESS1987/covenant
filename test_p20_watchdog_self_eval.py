#!/usr/bin/env python3
"""test_p20_watchdog_self_eval.py -- P20: the watchdog's self-evaluation.

WHAT P20 IS. Every sensory stream the watchdog reads (P11 identity, P12
anomalies, topology/mycelium, P14 self-drift, P15 judge identity) ends in the
LOG -- a record for a reader who already knows something is wrong.
self_evaluation() turns the same round's readings into a periodic VERDICT
block appended to ops/SELF_EVAL.md, so a person or a later session reads one
dated PASS/WARN/FAIL per layer FIRST and the log second. Added 2026-08-29 at
the operator's direction ("constant self-evaluating by all systems
involved"), for all and not just him.

WHAT THIS SUITE PINS.
  E1  healthy inputs -> five layers, all PASS, overall PASS
  E2  a missing node is FAIL, and worst-wins rolls it up
  E3  no node at all names the chain as not running
  E4  height spread / split sources degrade to WARN, not silence
  E5  mycelium: no state is WARN; full state is PASS and counts links
  E6  judge: no baseline digest is FAIL and names fail-closed
  E7  P14 drift input turns the self layer FAIL verbatim
  E8  alerts: benign -> WARN; FORK/down -> FAIL
  E9  the ledger: header (with its dedication) written once, blocks append,
      rotation at the stated cap moves the old ledger to .prev
  E10 REPORT-ONLY, pinned by AST: self_evaluation contains no call to
      start_node, Popen, urlopen or log -- it senses nothing and acts on
      nothing; it only returns text (the same boundary P12 draws)
  E11 the one_pass hook exists, is gated on SELF_EVAL_EVERY, and logs its
      verdict unconditionally rather than through Adaptation

M13 shape: no node, no socket, no key, no ollama. The module is imported,
never run; the writer is tested against a temp directory.
"""
import ast
import inspect
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_watchdog as wd

results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print(f"{'ok  ' if ok else 'FAIL'}  {label}  {detail if not ok else ''}",
          flush=True)


H = {"chain_height": 7, "source_sha256": "89ef8efe914e8bdd",
     "version": "v8.39"}
TOPO = {"A": {"height": 7, "uptime": 100, "addrs": ["h:1", "h:2"]},
        "B": {"height": 7, "uptime": 100, "addrs": ["h:1"]},
        "C": {"height": 7, "uptime": 100, "addrs": ["h:2"]}}
JUDGE = {"digest": "sha256:abcdef123456", "served": {"qwen3:8b": "x"},
         "loaded": []}


def ev(**kw):
    args = dict(states={"A": dict(H), "B": dict(H), "C": dict(H)},
                topo=dict(TOPO), judge=dict(JUDGE), self_drift=[],
                alerts=[], now_iso="2026-08-29T00:00:00Z", round_no=60)
    args.update(kw)
    return wd.self_evaluation(**args)


def parse(block):
    lines = [l for l in block.strip().splitlines() if l.strip()]
    head, layers = lines[0], {}
    for l in lines[1:]:
        parts = l.split(None, 2)
        layers[parts[0]] = (parts[1], parts[2] if len(parts) > 2 else "")
    return head, layers


def main():
    # E1 -----------------------------------------------------------------
    block, overall = ev()
    head, layers = parse(block)
    check("E1a healthy inputs give overall PASS", overall == "PASS", overall)
    check("E1b all five layers present",
          set(layers) == {"nodes", "mycelium", "judge", "self", "alerts"},
          str(sorted(layers)))
    check("E1c every layer PASS", all(v == "PASS" for v, _ in layers.values()),
          str(layers))
    check("E1d the head line carries timestamp, overall and round",
          "2026-08-29T00:00:00Z" in head and "PASS" in head and "60" in head,
          head)

    # E2 -----------------------------------------------------------------
    block, overall = ev(states={"A": dict(H), "B": None, "C": dict(H)})
    _, layers = parse(block)
    check("E2a a missing node is FAIL on the nodes layer",
          layers["nodes"][0] == "FAIL", str(layers["nodes"]))
    check("E2b and it is NAMED", "B" in layers["nodes"][1], layers["nodes"][1])
    check("E2c worst-wins: overall is FAIL", overall == "FAIL", overall)

    # E3 -----------------------------------------------------------------
    block, _ = ev(states={"A": None, "B": None, "C": None})
    _, layers = parse(block)
    check("E3 no node at all says the chain is not running",
          "not running" in layers["nodes"][1], layers["nodes"][1])

    # E4 -----------------------------------------------------------------
    tall = dict(H); tall["chain_height"] = 9
    block, _ = ev(states={"A": dict(H), "B": dict(H), "C": tall})
    _, layers = parse(block)
    check("E4a a height spread over one is WARN, not silence",
          layers["nodes"][0] == "WARN", str(layers["nodes"]))
    other = dict(H); other["source_sha256"] = "deadbeef0000cafe"
    block, _ = ev(states={"A": dict(H), "B": dict(H), "C": other})
    _, layers = parse(block)
    check("E4b split sources are WARN and both named",
          layers["nodes"][0] == "WARN" and "/" in layers["nodes"][1],
          str(layers["nodes"]))

    # E5 -----------------------------------------------------------------
    block, _ = ev(topo={})
    _, layers = parse(block)
    check("E5a no mycelium state is WARN and says so",
          layers["mycelium"][0] == "WARN"
          and "not answered" in layers["mycelium"][1], str(layers["mycelium"]))
    block, _ = ev()
    _, layers = parse(block)
    check("E5b full mycelium state is PASS and counts links per node",
          layers["mycelium"][0] == "PASS" and "A=2" in layers["mycelium"][1],
          str(layers["mycelium"]))

    # E6 -----------------------------------------------------------------
    block, overall = ev(judge={})
    _, layers = parse(block)
    check("E6 judge without a baseline is FAIL and names fail-closed",
          layers["judge"][0] == "FAIL"
          and "closed" in layers["judge"][1], str(layers["judge"]))

    # E7 -----------------------------------------------------------------
    drift = ["WATCHDOG SOURCE DRIFT: running aaaa, disk bbbb"]
    block, overall = ev(self_drift=drift)
    _, layers = parse(block)
    check("E7 P14 drift turns the self layer FAIL and carries the alert",
          layers["self"][0] == "FAIL" and "DRIFT" in layers["self"][1],
          str(layers["self"]))

    # E8 -----------------------------------------------------------------
    block, overall = ev(alerts=["node A: crisis_mode"])
    _, layers = parse(block)
    check("E8a a benign alert is WARN", layers["alerts"][0] == "WARN"
          and overall == "WARN", f"{layers['alerts']} overall={overall}")
    block, overall = ev(alerts=["FORK: founder balance disagrees"])
    _, layers = parse(block)
    check("E8b FORK escalates the alerts layer to FAIL",
          layers["alerts"][0] == "FAIL" and overall == "FAIL", overall)

    # E9 -----------------------------------------------------------------
    tmp = tempfile.mkdtemp(prefix="p20_")
    old_path, old_max = wd.SELF_EVAL_PATH, wd.SELF_EVAL_MAX_BYTES
    try:
        wd.SELF_EVAL_PATH = os.path.join(tmp, "ops", "SELF_EVAL.md")
        block, _ = ev()
        check("E9a first write creates the ledger with its header",
              wd._self_eval_write(block)
              and open(wd.SELF_EVAL_PATH, encoding="utf-8").read()
              .startswith("# covenant self-evaluation ledger"), "")
        text = open(wd.SELF_EVAL_PATH, encoding="utf-8").read()
        check("E9b the dedication is in the header",
              "For Misha, and all that were lost to injustice." in text, "")
        wd._self_eval_write(block)
        text = open(wd.SELF_EVAL_PATH, encoding="utf-8").read()
        check("E9c blocks append; the header appears once",
              text.count("# covenant self-evaluation ledger") == 1
              and text.count("## 2026-08-29T00:00:00Z") == 2, "")
        wd.SELF_EVAL_MAX_BYTES = 10
        wd._self_eval_write(block)
        check("E9d over the cap, the ledger rotates to .prev and restarts "
              "with a fresh header",
              os.path.exists(wd.SELF_EVAL_PATH + ".prev")
              and open(wd.SELF_EVAL_PATH, encoding="utf-8").read()
              .count("# covenant self-evaluation ledger") == 1, "")
    finally:
        wd.SELF_EVAL_PATH, wd.SELF_EVAL_MAX_BYTES = old_path, old_max

    # E10 ----------------------------------------------------------------
    tree = ast.parse(inspect.getsource(wd.self_evaluation).lstrip())
    called = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            called.add(f.attr if isinstance(f, ast.Attribute)
                       else getattr(f, "id", "?"))
    forbidden = {"start_node", "Popen", "urlopen", "log", "open", "replace"}
    check("E10 self_evaluation is REPORT-ONLY by AST: no probe, no restart, "
          "no I/O, not even a log call",
          not (called & forbidden), str(sorted(called & forbidden)))

    # E11 ----------------------------------------------------------------
    src = inspect.getsource(wd.one_pass)
    check("E11a one_pass calls self_evaluation gated on SELF_EVAL_EVERY",
          "self_evaluation(" in src and "SELF_EVAL_EVERY" in src, "")
    check("E11b the verdict line is logged directly, not through Adaptation",
          "_adapt_info.observe" not in src.split("self_evaluation(")[1], "")

    p = sum(results)
    print(f"\nP20: {p}/{len(results)} passed")
    return 0 if p == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
