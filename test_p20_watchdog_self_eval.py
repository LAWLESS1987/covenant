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
  E10b the same boundary pinned by RUNNING it: self_evaluation is called with
      open/urlopen/Popen/log/start_node/os.replace/os.remove replaced by
      recorders, so a probe, a spawn or a write one frame DOWN is caught --
      E10's AST walk can only see the spelling inside its own ~65 lines
  E11 the one_pass hook exists, is gated on SELF_EVAL_EVERY, and logs its
      verdict unconditionally rather than through Adaptation

M13 shape: no node, no socket, no key, no model server. The module is imported,
never run; the writer is tested against a temp directory.
"""
import ast
import builtins
import inspect
import io
import json
import os
import subprocess
import sys
import tempfile
import urllib.request

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
JUDGE = {"digest": "sha256:abcdef123456", "served": {"model-a": "x"},
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
    # 2026-09-03: with ops/quorum_policy.json naming a deferring seat the judge
    # row is WARN, not FAIL (F2). The pin below runs with NO policy; E6b pins
    # the deferring wording.
    os.environ["COVENANT_QUORUM_POLICY_PATH"] = os.path.join(tempfile.mkdtemp(), "absent.json")
    block, overall = ev(judge={})
    _, layers = parse(block)
    check("E6 judge without a baseline is FAIL and names fail-closed",
          layers["judge"][0] == "FAIL"
          and "closed" in layers["judge"][1], str(layers["judge"]))
    _pol = os.path.join(tempfile.mkdtemp(), "quorum_policy.json")
    with open(_pol, "w", encoding="utf-8") as _fh:
        _fh.write('{"providers": "deferring,semantic", "silence_is_not_dissent": true}')
    os.environ["COVENANT_QUORUM_POLICY_PATH"] = _pol
    block, overall = ev(judge={})
    _, layers = parse(block)
    check("E6b with a DEFERRING policy the judge row is WARN and names the deferral, not fail-closed",
          layers["judge"][0] == "WARN" and "defers" in layers["judge"][1], str(layers["judge"]))
    os.environ["COVENANT_QUORUM_POLICY_PATH"] = os.path.join(tempfile.mkdtemp(), "absent.json")

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

    # E10b ---------------------------------------------------------------
    # 2026-09-09: E10 above reads self_evaluation's SOURCE and forbids six
    # spellings inside its own ~65 lines. It cannot see one frame down.
    # The mutation that proved it: give _seat_defers() -- which
    # self_evaluation calls from its own judge branch -- a log line and a
    # /health probe. The suite printed that probe's log line on every round
    # and then asserted, four lines later, that self_evaluation had made no
    # log call. E10 stayed green. The control is worse: inlining
    # _seat_defers()/_quorum_policy() into self_evaluation -- same path, same
    # file, byte-identical behaviour -- turns E10 RED on the word 'open'. So
    # E10 flags a refactor that changes nothing and misses a probe, a spawn
    # and a write that change everything: it measures spelling in one stack
    # frame, not the report-only boundary it names. E10b RUNS the function
    # with every forbidden call replaced by a recorder, at any depth.
    # SCOPE, stated honestly: shipped self_evaluation DOES read
    # ops/quorum_policy.json -- E6b passes only because it does -- so a READ
    # is allowed here and E10b pins the acting half: no probe, no spawn, no
    # restart, no WRITE, no rename, no log.
    fired = []
    _saved = (builtins.open, urllib.request.urlopen, subprocess.Popen,
              wd.log, wd.start_node, os.replace, os.remove)
    _real_open = builtins.open

    def _rec(name):
        def _f(*a, **k):
            fired.append(name)
        return _f

    def _rec_open(file, mode="r", *a, **k):
        if any(c in str(mode) for c in "wax+"):
            fired.append(f"open({os.path.basename(str(file))!r},{mode!r})")
        return _real_open(file, mode, *a, **k)

    try:
        (builtins.open, urllib.request.urlopen, subprocess.Popen, wd.log,
         wd.start_node, os.replace, os.remove) = (
            _rec_open, _rec("urlopen"), _rec("Popen"), _rec("log"),
            _rec("start_node"), _rec("os.replace"), _rec("os.remove"))
        try:
            ev(judge={})                       # the seat/policy branch
            ev()                               # the baseline-present branch
            ev(states={"A": None, "B": None, "C": None}, topo={},
               self_drift=["WATCHDOG SOURCE DRIFT: aaaa/bbbb"],
               alerts=["FORK: founder balance disagrees"])
        except Exception as e:                 # a stub blowing up IS the call
            fired.append(f"{type(e).__name__}: {e}")
    finally:
        (builtins.open, urllib.request.urlopen, subprocess.Popen, wd.log,
         wd.start_node, os.replace, os.remove) = _saved
    check("E10b self_evaluation is REPORT-ONLY when RUN, at any depth: no "
          "probe, no spawn, no restart, no write, no rename, no log",
          not fired, str(sorted(set(fired))))

    # E11 ----------------------------------------------------------------
    src = inspect.getsource(wd.one_pass)
    check("E11a one_pass calls self_evaluation gated on SELF_EVAL_EVERY",
          "self_evaluation(" in src and "SELF_EVAL_EVERY" in src, "")
    check("E11b the verdict line is logged directly, not through Adaptation",
          "_adapt_info.observe" not in src.split("self_evaluation(")[1], "")

    # E11c/E11d: RUN IT. A87 (2026-09-10).
    #
    # E11a and E11b read inspect.getsource(one_pass), so they see the CALL and
    # never the BEHAVIOUR. Measured by mutation: set SELF_EVAL_EVERY's default
    # at covenant_watchdog.py:718 from "60" to "0" and the ledger is silenced
    # permanently -- one_pass stays byte-identical, and P20 and every other
    # watchdog suite stay green. The same is true of `if False and ...` at the
    # call site: the text is still there, the write never happens.
    #
    # covenant_watchdog._self_eval_write is the tree's ONLY writer of
    # ops/SELF_EVAL.md, and the self-eval is the record the operator reads to
    # know the monitor is still watching. A guard on it that cannot tell a live
    # call from a dead one is guarding the sentence, not the thing.
    #
    # Everything below is stubbed the way test_watchdog_outage.py already
    # stubs it: no node is probed, none started, nothing real is written.
    import tempfile as _tf
    import covenant_contact as _cc
    _saved_se = (wd.SELF_EVAL_PATH, wd.SELF_EVAL_EVERY, wd.health,
                 wd.start_node, wd.log, dict(wd._self_eval), wd.SELF_EVAL_TOLD,
                 _cc.say)
    _spoke = []
    try:
        _dir = _tf.mkdtemp()
        wd.SELF_EVAL_PATH = os.path.join(_dir, "SELF_EVAL.md")
        # 2026-09-27: the first version of the direct line spoke from HERE --
        # this block put "Self-evaluation round 1: FAIL" on his phone. The told
        # file and the line are redirected, and E11f pins that a pass outside
        # the daemon says nothing at all.
        wd.SELF_EVAL_TOLD = os.path.join(_dir, "told.json")
        _cc.say = lambda *a, **k: _spoke.append(a) or {"id": "stub"}
        wd._self_eval["persist"] = False
        wd.health = lambda port, timeout=8: (
            {"warnings": [], "chain_height": 9, "peers": 1,
             "version": "v8.40", "judge": "quorum(x)"}, "")
        wd.start_node = lambda n: None
        wd.log = lambda level, msg: None

        wd.SELF_EVAL_EVERY = 1
        wd._self_eval["round"] = 0
        wd.one_pass()
        _wrote = (os.path.exists(wd.SELF_EVAL_PATH)
                  and os.path.getsize(wd.SELF_EVAL_PATH) > 0)
        _body = (io.open(wd.SELF_EVAL_PATH, encoding="utf-8").read()
                 if _wrote else "")
        check("E11c one_pass ACTUALLY WRITES the self-evaluation ledger -- run, "
              "not read: the source can say self_evaluation() while the write "
              "never happens", _wrote, "%d bytes" % (len(_body)))
        check("E11d ...and what it writes is a real verdict block, not an empty "
              "heading", "overall" in _body and "nodes" in _body,
              _body.strip()[:70])
        check("E11f ...and a pass OUTSIDE the daemon says nothing on the direct "
              "line and writes no told file, whatever the verdict",
              not [a for a in _spoke if "Self-evaluation" in str(a)]
              and not os.path.exists(wd.SELF_EVAL_TOLD), _spoke)

        # The gate must work in the OTHER direction too, or E11c would pass on
        # a watchdog that wrote the ledger every single round.
        os.remove(wd.SELF_EVAL_PATH)
        wd.SELF_EVAL_EVERY = 0
        wd._self_eval["round"] = 0
        wd.one_pass()
        check("E11e ...and SELF_EVAL_EVERY=0 genuinely silences it, so E11c is "
              "measuring the gate and not just a write that always happens",
              not os.path.exists(wd.SELF_EVAL_PATH))
    finally:
        (wd.SELF_EVAL_PATH, wd.SELF_EVAL_EVERY, wd.health,
         wd.start_node, wd.log) = _saved_se[:5]
        wd._self_eval.clear()
        wd._self_eval.update(_saved_se[5])
        wd.SELF_EVAL_TOLD, _cc.say = _saved_se[6], _saved_se[7]

    # E12 -- THE OFFLINE LAYERS (2026-09-19) ------------------------------
    # Added because on 2026-09-19 both of the day's real failures were in
    # layers this block could not see. Every guard below is driven BOTH ways:
    # a check that has only ever passed has never been observed.
    _, base = parse(ev()[0])
    check("E12a with offline=None the block is unchanged -- five layers, no "
          "row invented for something nobody measured",
          set(base) == {"nodes", "mycelium", "judge", "self", "alerts"},
          str(sorted(base)))

    _, four = parse(ev(offline={"trader": ("PASS", "t"), "repo": ("PASS", "r"),
                                "git": ("PASS", "g"), "disk": ("PASS", "d")})[0])
    check("E12b supplied layers appear, in the fixed order",
          [k for k in four] [-4:] == ["trader", "repo", "git", "disk"],
          str(list(four)))

    _, partial = parse(ev(offline={"disk": ("PASS", "d")})[0])
    check("E12c a layer that could not be read is OMITTED, not guessed PASS",
          "disk" in partial and "trader" not in partial, str(sorted(partial)))

    blk, ov = ev(offline={"trader": ("FAIL", "seal failed")})
    check("E12d a FAIL in an offline layer drives the OVERALL verdict -- the "
          "whole point, since 09-19 read WARN while the trader could not seal",
          ov == "FAIL" and "seal failed" in blk, ov)
    check("E12e ...and the same block without it is PASS, so E12d measures "
          "the offline row and not a block that always fails", ev()[1] == "PASS",
          ev()[1])

    # The readings themselves, against real files in a temp tree.
    import hashlib
    import time
    _saved_paths = (wd.TRADER_LOG, wd.CORE_FILE, wd.MANIFEST_FILE,
                    wd.VERIFY_DEPLOY_FILE)
    try:
        with tempfile.TemporaryDirectory() as td:
            core = os.path.join(td, "covenant_unified_v8.py")
            man = os.path.join(td, "MANIFEST.sha256")
            body = b'COVENANT_VERSION = "v8.40"\nprint("core")\n'
            with open(core, "wb") as fh:
                fh.write(body)
            good = hashlib.sha256(body).hexdigest()
            wd.CORE_FILE, wd.MANIFEST_FILE = core, man
            vd = os.path.join(td, "verify_deploy.py")
            wd.VERIFY_DEPLOY_FILE = vd
            other = os.path.join(td, "other.py")
            with open(other, "wb") as fh:
                fh.write(b"x = 1\n")
            other_sha = hashlib.sha256(b"x = 1\n").hexdigest()
            with open(os.path.join(td, "companion.py"), "wb") as fh:
                fh.write(b"")

            # The fixture is shaped like the real verify_deploy.py: comments
            # inside the dict, another file listed BEFORE the core (so reading
            # "the first entry" is caught), a companion map, and a module
            # level that raises -- importing it instead of parsing it is red.
            def _pin(sha, version='"v8.40"', lines="2", osha=None,
                     comp="companion.py"):
                with open(vd, "w", encoding="utf-8") as fh:
                    fh.write('EXPECTED_VERSION = %s\n'
                             'EXPECTED_LINES = %s   # a comment\n'
                             'MANIFEST = {\n'
                             '    # a comment, as the real one carries\n'
                             '    "other.py": "%s",\n'
                             '    "covenant_unified_v8.py":\n'
                             '        "%s",\n'
                             '}\n'
                             'COMPANIONS = {"covenant_unified_v8.py": "%s"}\n'
                             'raise SystemExit("imported, never parsed")\n'
                             % (version, lines, osha or other_sha, sha, comp))
            _pin(good)
            with open(man, "w", encoding="utf-8") as fh:
                fh.write(good + "  covenant_unified_v8.py\n")
            check("E12f _repo_reading PASSes when the core matches the manifest",
                  wd._repo_reading()[0] == "PASS", str(wd._repo_reading()))
            # 2026-09-27: the row also asks verify_deploy.py's questions. It
            # read PASS for two days while that pin named the 09-21 core and
            # verify_deploy refused every restart it gates.
            _pin("2" * 64)
            r = wd._repo_reading()
            check("E12s the manifest matches but verify_deploy.py pins other "
                  "bytes -> FAIL, named stale pins and not a bad delivery "
                  "(the 2026-09-25..27 case)",
                  r[0] == "FAIL" and "stale pins" in r[1]
                  and "222222222222" in r[1], str(r))
            _pin(good[:12] + ("0" if good[12] != "0" else "1") + good[13:])
            r = wd._repo_reading()
            check("E12s2 ...and a pin that agrees on the first 12 characters "
                  "only is FAIL too: verify_deploy compares all 64",
                  r[0] == "FAIL", str(r))
            _pin(good, version='"v9.99"')
            r = wd._repo_reading()
            check("E12t the right hash under another EXPECTED_VERSION is FAIL "
                  "too: verify_deploy refuses a version mismatch",
                  r[0] == "FAIL" and "v9.99" in r[1], str(r))
            _pin(good, lines="3")
            r = wd._repo_reading()
            check("E12t2 EXPECTED_LINES one off the core's line count -> FAIL: "
                  "a re-pin of the hash alone still fails verify_deploy "
                  "after the restart", r[0] == "FAIL"
                  and "EXPECTED_LINES is 3" in r[1], str(r))
            _pin(good, osha="3" * 64)
            r = wd._repo_reading()
            check("E12x another pinned file drifted -> FAIL naming it, though "
                  "the core agrees", r[0] == "FAIL" and "other.py" in r[1],
                  str(r))
            _pin(good)
            os.remove(other)
            r = wd._repo_reading()
            check("E12y ...and a pinned file that is missing -> FAIL naming it",
                  r[0] == "FAIL" and "other.py is missing" in r[1], str(r))
            with open(other, "wb") as fh:
                fh.write(b"x = 1\n")
            _pin(good, comp="gone.py")
            r = wd._repo_reading()
            check("E12z a companion verify_deploy needs beside the core is "
                  "missing -> FAIL naming it", r[0] == "FAIL"
                  and "gone.py" in r[1], str(r))
            _pin(good)
            check("E12u broken the other way: every pin, companion, version "
                  "and line count agreeing -> PASS, so E12s..E12z measure "
                  "what they name", wd._repo_reading()[0] == "PASS",
                  str(wd._repo_reading()))
            _pin(good, version='"v8." + "40"')
            r = wd._repo_reading()
            check("E12v2 an EXPECTED_VERSION that is not a literal -> WARN "
                  "unmeasured, never a PASS on the hash alone",
                  r[0] == "WARN" and "UNMEASURED" in r[1], str(r))
            with open(vd, "w", encoding="utf-8") as fh:
                fh.write("MANIFEST = {\n")
            r = wd._repo_reading()
            check("E12v a verify_deploy.py that does not parse -> WARN, "
                  "unmeasured -- never PASS",
                  r[0] == "WARN" and "UNMEASURED" in r[1], str(r))
            os.remove(vd)
            r = wd._repo_reading()
            check("E12w ...and one that is not there at all -> WARN as well",
                  r[0] == "WARN", str(r))
            _pin(good)
            with open(core, "wb") as fh:
                fh.write(b'print("core")\n')
            with open(man, "w", encoding="utf-8") as fh:
                fh.write(hashlib.sha256(b'print("core")\n').hexdigest()
                         + "  covenant_unified_v8.py\n")
            _pin(hashlib.sha256(b'print("core")\n').hexdigest(), lines="1")
            r = wd._repo_reading()
            check("E12w2 a core that declares no COVENANT_VERSION -> WARN: "
                  "verify_deploy calls it UNKNOWN, so this is not a PASS",
                  r[0] == "WARN" and "UNMEASURED" in r[1], str(r))
            _pin("2" * 64, lines="1")
            r = wd._repo_reading()
            check("E12w3 ...but a stale pin found beside that unknown is still "
                  "FAIL: verify_deploy puts failures ahead of unknowns",
                  r[0] == "FAIL" and "222222222222" in r[1], str(r))
            nonl = b'COVENANT_VERSION = "v8.40"\nprint(1)'
            with open(core, "wb") as fh:
                fh.write(nonl)
            with open(man, "w", encoding="utf-8") as fh:
                fh.write(hashlib.sha256(nonl).hexdigest()
                         + "  covenant_unified_v8.py\n")
            _pin(hashlib.sha256(nonl).hexdigest(), lines="1")
            r1 = wd._repo_reading()
            _pin(hashlib.sha256(nonl).hexdigest(), lines="2")
            r2 = wd._repo_reading()
            check("E12t3 lines are counted as the node counts them (newline "
                  "bytes): a core with no final newline is 1 line, not 2",
                  r1[0] == "PASS" and r2[0] == "FAIL", (r1, r2))
            with open(core, "wb") as fh:
                fh.write(body)
            with open(man, "w", encoding="utf-8") as fh:
                fh.write(good + "  covenant_unified_v8.py\n")
            _pin(good)
            with open(man, "w", encoding="utf-8") as fh:
                fh.write("0" * 64 + "  covenant_unified_v8.py\n")
            check("E12g ...and FAILs on a one-byte-different pin, so E12f is "
                  "measuring the hash and not the file's existence",
                  wd._repo_reading()[0] == "FAIL", str(wd._repo_reading()))
            with open(man, "w", encoding="utf-8") as fh:
                fh.write(good + "  something_else.py\n")
            check("E12h ...and WARNs when the manifest carries no row for the "
                  "core at all (unpinned is not the same as matching)",
                  wd._repo_reading()[0] == "WARN", str(wd._repo_reading()))

            tl = os.path.join(td, "trader_log.txt")
            wd.TRADER_LOG = tl
            check("E12i no trader log at all -> no row, rather than a verdict",
                  wd._trader_reading() is None, str(wd._trader_reading()))
            t = time.localtime()
            today = "%02d/%02d/%04d" % (t.tm_mon, t.tm_mday, t.tm_year)
            clean = ("---- CYCLE COMPLETE %s ----\n  SEAL  ok -- HTTP 200\n"
                     "---- CYCLE COMPLETE %s ----\n  exit 0\n" % (today, today))
            with open(tl, "w", encoding="utf-8") as fh:
                fh.write(clean)
            check("E12j a cycle dated today that sealed -> PASS",
                  wd._trader_reading()[0] == "PASS", str(wd._trader_reading()))
            with open(tl, "w", encoding="utf-8") as fh:
                fh.write(clean.replace("SEAL  ok -- HTTP 200",
                                       "SEAL  FAILED -- refusing to seal"))
            r = wd._trader_reading()
            check("E12k ...and the SAME cycle with a failed seal -> FAIL. This "
                  "is the 2026-09-19 case: freshness said RAN, nothing sealed",
                  r[0] == "FAIL" and "FAILED" in r[1], str(r))
            with open(tl, "w", encoding="utf-8") as fh:
                fh.write(clean.replace("exit 0", "exit 3: a required seal failed"))
            check("E12l ...and a non-zero exit is caught even when the seal "
                  "line reads ok", wd._trader_reading()[0] == "FAIL",
                  str(wd._trader_reading()))
    finally:
        (wd.TRADER_LOG, wd.CORE_FILE, wd.MANIFEST_FILE,
         wd.VERIFY_DEPLOY_FILE) = _saved_paths

    o = wd.offline_readings()
    check("E12m offline_readings() runs against the REAL tree and returns "
          "only layers it could take", isinstance(o, dict)
          # "daily" (2026-09-28): Tetsu's daily maintenance cycle, his directive -- a known layer, so the
          # set stays closed: an unknown layer still fails this check
          and set(o) <= {"trader", "student", "repo", "git", "disk", "daily"}, str(sorted(o)))
    check("E12n every returned layer carries a real verdict word",
          all(v[0] in ("PASS", "WARN", "FAIL") and v[1] for v in o.values()),
          str(o))

    _boom = wd._disk_reading
    try:
        wd._disk_reading = lambda: (_ for _ in ()).throw(RuntimeError("x"))
        o2 = wd.offline_readings()
        check("E12o a reading that RAISES becomes a WARN row, never a crash -- "
              "the evaluation must not be able to kill the evaluator",
              o2.get("disk", ("", ""))[0] == "WARN", str(o2.get("disk")))
    finally:
        wd._disk_reading = _boom

    # E12r (2026-10-03, compactness watched): the disk row carries the repository's stored size,
    # and the thresholds bite -- driven with the size stubbed both ways, the real one read once.
    real_mb = wd.repo_packed_mb()
    d_now = wd._disk_reading()
    check("E12r the disk row reports the repository's stored size, read from .git/objects",
          real_mb is not None and real_mb > 0 and "repository" in d_now[1], (real_mb, d_now))
    _rp = wd.repo_packed_mb
    try:
        wd.repo_packed_mb = lambda root=None: wd.REPO_WARN_MB + 1
        w = wd._disk_reading()
        wd.repo_packed_mb = lambda root=None: wd.REPO_FAIL_MB + 1
        f = wd._disk_reading()
        wd.repo_packed_mb = lambda root=None: None
        n = wd._disk_reading()
    finally:
        wd.repo_packed_mb = _rp
    check("E12r ...and turns WARN past %dM and FAIL past %dM; with no .git it says nothing about size"
          % (wd.REPO_WARN_MB, wd.REPO_FAIL_MB),
          w[0] == "WARN" and "repository is past" in w[1] and f[0] == "FAIL" and "repository" not in n[1]
          or (d_now[0] != "PASS"), (w, f, n))

    # E12p -- NO NETWORK, pinned by RUNNING it, not by grepping the source.
    # A source grep would fail on the word "fetch" in FETCH_HEAD, which is a
    # local file read; and it would pass a watchdog that reached the network
    # by some other spelling. So every git argv is recorded and urlopen is
    # replaced by something that fails the test if it is ever called.
    _git_calls, _net = [], []
    _s_git, _s_url = wd._git, urllib.request.urlopen
    try:
        def _rec(*a, **k):
            _git_calls.append(a)
            return _s_git(*a, **k)
        wd._git = _rec
        urllib.request.urlopen = lambda *a, **k: _net.append(a)
        wd.offline_readings()
        check("E12p the offline pass RAN without reaching the network: no "
              "fetch/pull/push in any git argv, no urlopen at all",
              _git_calls and not _net and not any(
                  set(a) & {"fetch", "pull", "push", "clone", "remote"}
                  for a in _git_calls), f"{_git_calls} {_net}")
    finally:
        wd._git, urllib.request.urlopen = _s_git, _s_url

    # ---- E13: the learning loop's row, and the direct line (2026-09-27) ----
    # His words: "Tetsu should do this and tell you about it if needed". The
    # daily Claude evaluation read the student and could say FAIL; the hourly
    # block did neither.
    import time
    _saved13 = (wd.DISTILL_LOG, wd.RUN_WITHOUT_FILE)
    try:
        with tempfile.TemporaryDirectory() as td:
            wd.DISTILL_LOG = os.path.join(td, "DISTILL.md")
            wd.RUN_WITHOUT_FILE = os.path.join(td, "RUN_WITHOUT.json")
            now = 1790500000.0
            fresh = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - 3 * 3600))
            old = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - 50 * 3600))
            check("E13a neither file here -> no student row, rather than a verdict",
                  wd._student_reading(now) is None, str(wd._student_reading(now)))
            with open(wd.DISTILL_LOG, "w", encoding="utf-8") as fh:
                fh.write("## %s  PROMOTED\nx\n\n## %s  REFUSED\nregresses A126\n" % (old, fresh))
            with open(wd.RUN_WITHOUT_FILE, "w", encoding="utf-8") as fh:
                json.dump({"met_count": 2, "of": 5, "exam_streak": 0, "conditions": {
                    "exam_met_streak": {"met": False}, "holdout_decided_min": {"met": True}}}, fh)
            r = wd._student_reading(now)
            check("E13b a REFUSED candidate last night is PASS -- the loop refusing a worse judge is the loop "
                  "working -- and the row names the LAST cycle and the run-without conditions",
                  r[0] == "PASS" and "REFUSED" in r[1] and fresh in r[1] and "2/5 met" in r[1]
                  and "exam_met_streak" in r[1], str(r))
            with open(wd.DISTILL_LOG, "w", encoding="utf-8") as fh:
                fh.write("## %s  PROMOTED\nx\n" % old)
            r = wd._student_reading(now)
            check("E13c broken the other way: no cycle for 50 h -> WARN, the nightly did not run",
                  r[0] == "WARN" and "did not run" in r[1], str(r))
            with open(wd.DISTILL_LOG, "w", encoding="utf-8") as fh:
                fh.write("nothing yet\n")
            check("E13d a DISTILL.md with no cycle heading -> WARN, never PASS",
                  wd._student_reading(now)[0] == "WARN", str(wd._student_reading(now)))
            blk, ov = ev(offline={"student": ("WARN", "no cycle")})
            check("E13e the student row appears in the block when read",
                  "\nstudent   WARN  no cycle" in blk, blk)

            told = []

            def _tell(text, why):
                told.append(text)
                return {"id": "stub"}
            tp = os.path.join(td, "told.json")
            f_blk, f_ov = ev(offline={"repo": ("FAIL", "stale pins at 10.1.2.3")})
            said = wd._self_eval_tell(f_blk, f_ov, 60, live=True, tell=_tell, path=tp)
            check("E13f an overall FAIL is said on the direct line once, naming the failing row, with addresses "
                  "masked", said and len(told) == 1 and "repo: stale pins" in told[0] and "10.1.2.3" not in told[0],
                  told)
            wd._self_eval_tell(f_blk, f_ov, 120, live=True, tell=_tell, path=tp)
            check("E13g ...the same FAIL an hour later says nothing", len(told) == 1, told)
            g_blk, g_ov = ev(offline={"repo": ("FAIL", "x"), "git": ("FAIL", "portfolio file")})
            wd._self_eval_tell(g_blk, g_ov, 180, live=True, tell=_tell, path=tp)
            check("E13h ...a DIFFERENT set of failing rows is said again", len(told) == 2 and "git:" in told[1], told)
            p_blk, p_ov = ev()
            wd._self_eval_tell(p_blk, p_ov, 240, live=True, tell=_tell, path=tp)
            check("E13i broken the other way: out of FAIL is said once...",
                  len(told) == 3 and "out of FAIL" in told[2], told)
            wd._self_eval_tell(p_blk, p_ov, 300, live=True, tell=_tell, path=tp)
            check("E13j ...and a healthy hour after it says nothing", len(told) == 3, told)
            w_blk, w_ov = ev(offline={"trader": ("WARN", "unknown")})
            wd._self_eval_tell(w_blk, w_ov, 360, live=True, tell=_tell, path=tp)
            check("E13k a WARN is not a FAIL: nothing said", len(told) == 3, told)

            def _boom(text, why):
                raise OSError("outbox unwritable")
            bp = os.path.join(td, "boom.json")
            r1 = wd._self_eval_tell(f_blk, f_ov, 60, live=True, tell=_boom, path=bp)
            r2 = wd._self_eval_tell(f_blk, f_ov, 120, live=True, tell=_tell, path=bp)
            check("E13l a direct line that raises never raises here, and is not retried every hour",
                  r1 is None and r2 is None and len(told) == 3, told)
            blocker = os.path.join(td, "notadir")
            with open(blocker, "w") as fh:
                fh.write("x")
            np_ = os.path.join(blocker, "told.json")
            k = len(told)
            for rnd in (60, 120, 180):
                wd._self_eval_tell(f_blk, f_ov, rnd, live=True, tell=_tell, path=np_)
            check("E13m a told-file that cannot be written: three FAIL hours still say it once",
                  len(told) == k + 1, told[k:])

            # Found by the second review (2026-09-27), each with H1/P20 green.
            k = len(told)
            _saved_persist = wd._self_eval.get("persist", False)
            try:
                wd._self_eval["persist"] = False
                r = wd._self_eval_tell(f_blk, f_ov, 60, tell=_tell, path=os.path.join(td, "quiet.json"))
            finally:
                wd._self_eval["persist"] = _saved_persist
            check("E13n outside the daemon (live not given, persist False) it says nothing and writes nothing",
                  r is None and len(told) == k and not os.path.exists(os.path.join(td, "quiet.json")), told[k:])
            for i, junk in enumerate(("[]", '"repo"', "7")):
                jp = os.path.join(td, "junk%d.json" % i)       # a fresh path each: no memo of an earlier telling
                with open(jp, "w", encoding="utf-8") as fh:
                    fh.write(junk)
                wd._self_eval_tell(f_blk, f_ov, 60, live=True, tell=_tell, path=jp)
            check("E13o a told file that is valid JSON but not an object is read as 'nothing told', never as a "
                  "silence for good", len(told) == k + 3, told[k:])
            k = len(told)
            long_blk = ("## T  overall FAIL  (round 1)\nnodes     PASS  ok\n"
                        "deploy_pins_x FAIL  the pins are stale\n")
            wd._self_eval_tell(long_blk, "FAIL", 1, live=True, tell=_tell, path=os.path.join(td, "long.json"))
            check("E13p a layer name longer than the column still parses: the FAIL row is named",
                  len(told) == k + 1 and "deploy_pins_x: the pins are stale" in told[-1], told[k:])
            wd._self_eval_tell("## T  overall FAIL  (round 1)\n", "FAIL", 1, live=True, tell=_tell,
                               path=os.path.join(td, "norow.json"))
            check("E13q an overall FAIL with no row parsed as FAIL is still said (key 'FAIL'), never read as clear",
                  len(told) == k + 2 and "FAIL" in told[-1] and "out of FAIL" not in told[-1], told[k:])
            nl_blk, nl_ov = ev(offline={"repo": ("FAIL", "first line\nabcdefghi FAIL phantom")})
            check("E13r a newline inside a detail stays inside its row: one line per layer",
                  "\nabcdefghi" not in nl_blk and "first line abcdefghi FAIL phantom" in nl_blk, nl_blk)

            with open(wd.DISTILL_LOG, "w", encoding="utf-8") as fh:
                fh.write("## %s  REFUSED\n" % time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - 38 * 3600)))
            r = wd._student_reading(now)
            check("E13s a cycle 38 h old -> WARN: the boundary is measured in UTC, so a heading read as local time "
                  "(4 h off here) is caught", r[0] == "WARN", str(r))
            with open(wd.DISTILL_LOG, "w", encoding="utf-8") as fh:
                fh.write("## %s  PROMOTED\n" % time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now + 5 * 3600)))
            r = wd._student_reading(now)
            check("E13t a heading in the future -> WARN, the clock or the log is wrong", r[0] == "WARN"
                  and "future" in r[1], str(r))
    finally:
        wd.DISTILL_LOG, wd.RUN_WITHOUT_FILE = _saved13

    p = sum(results)
    print(f"\nP20: {p}/{len(results)} passed")
    return 0 if p == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
