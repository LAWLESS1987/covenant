#!/usr/bin/env python3
"""test_breakout_ledger.py -- the suite for the breakout forward record."""
import json, os, random, re, shutil, statistics, sys, tempfile, time, types
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import breakout_ledger as bl

passed = failed = 0; fails = []
def check(label, cond, detail=""):
    global passed, failed
    if cond: passed += 1; print(f"  ok   {label}" + (f"  [{detail}]" if detail else ""))
    else: failed += 1; fails.append(label); print(f"  FAIL {label}" + (f"  [{detail}]" if detail else ""))
def sec(t): print("\n" + "=" * 70 + f"\n{t}\n" + "=" * 70)

TMP = tempfile.mkdtemp(prefix="brkl_")
def newp(n): return os.path.join(TMP, n + ".jsonl")
def q(sym, closes, px): return {"sym": sym, "closes": closes, "px": px}
RISE = [10.0 + i * 0.1 for i in range(120)]          # always a new high
FLAT = [10.0] * 120

sec("A. the rule")
check("below the window it has NOT fired and returns None, not False",
      bl.signal([1.0] * 50) is None, "no call is not a flat call")
check("a new 100-day high is a signal", bl.signal(RISE) is True)
check("a flat series is not", bl.signal(FLAT + [9.0]) is False)
check("the window is 100, as tested", bl.WINDOW == 100)

sec("B. sealing and settling")
p = newp("basic"); t0 = time.time()
bl.record_cycle([q("AAA", RISE, 22.0)], now=t0, path=p)
rows = bl._read(p)
check("a new high opens a call", any(r["payload"]["kind"] == "open" for r in rows))
check("  ...and the day is marked read", any(r["payload"]["kind"] == "read" for r in rows))
bl.record_cycle([q("AAA", RISE, 25.0)], now=t0 + 60, path=p)
check("a second run the SAME day writes nothing",
      len(bl._read(p)) == len(rows), "intraday re-runs cannot manufacture signals")
bl.record_cycle([q("AAA", FLAT + [9.0], 20.0)], now=t0 + 86400 * 3, path=p)
st = [r["payload"] for r in bl._read(p) if r["payload"]["kind"] == "settled"]
check("losing the high settles the call", len(st) == 1)
check("  ...costs are charged", abs(st[0]["ret_after_costs"] - (st[0]["ret_gross"] - 0.0130)) < 1e-9)
check("  ...and settled strictly after sealed", st[0]["settled_at"] > st[0]["sealed_at"])
ok, why = bl.verify(p); check("the chain verifies", ok, why)

sec("C. integrity -- every mutation must be caught")
def broken(name, mutate):
    pp = newp(name); shutil.copy(p, pp)
    lines = [l for l in open(pp).read().split("\n") if l]
    lines = mutate(lines)
    open(pp, "w").write("\n".join(lines) + "\n")
    return bl.verify(pp)
def rewrite_entry(ls):
    r = json.loads(ls[1]); r["payload"]["entry"] = 1.0
    ls[1] = json.dumps(r, sort_keys=True, separators=(",", ":")); return ls
check("REWRITING A SEALED ENTRY PRICE IS DETECTED", not broken("t1", rewrite_entry)[0],
      broken("t1b", rewrite_entry)[1][:48])
check("deleting a record is detected", not broken("t2", lambda ls: ls[:1] + ls[2:])[0])
check("reordering is detected", not broken("t3", lambda ls: [ls[0], ls[2], ls[1]] + ls[3:])[0])
check("duplicating the settle is detected -- a call cannot be re-scored",
      not broken("t4", lambda ls: ls + [ls[-1]])[0])
try:
    pp = newp("app"); shutil.copy(p, pp)
    ls = rewrite_entry([l for l in open(pp).read().split("\n") if l])
    open(pp, "w").write("\n".join(ls) + "\n")
    bl._append({"kind": "read", "day": "x", "at": time.time(), "n": 1}, pp)
    check("appending to a broken chain is refused", False, "it appended")
except RuntimeError:
    check("appending to a broken chain is refused", True)

sec("D. scoring -- the part that had to differ from signal_ledger.py")
s = bl.summary(p)
check("below the floor it says NOT ENOUGH DATA regardless of the numbers",
      not s["clears"] and "NOT ENOUGH DATA" in s["why"], s["why"][:44])
check("the floor is the POWER calculation, not a round number",
      bl.MIN_TRADES == 863, "((1.96+0.84)*16.22/1.546)^2")

pp = newp("many"); import random
rng = random.Random(5)
# A distribution shaped like the measured one: loses 2 of 3, fat right tail.
# 260 pairs, not 900 -- _append re-verifies the whole chain on every write
# (O(n^2)), which is right for one append a day and wrong for a test loop.
NP = 260
rets = [(-0.03 if rng.random() < 0.67 else rng.expovariate(1/0.11)) for _ in range(NP)]
now = time.time() - NP * 7200
def pair(path, i, r, base):
    bl._append({"kind": "open", "open_id": f"S{i}", "sym": "X", "entry": 1.0,
                "window": 100, "sealed_at": base, "at": base}, path)
    bl._append({"kind": "settled", "open_id": f"S{i}", "sym": "X", "entry": 1.0,
                "exit": 1 + r, "sealed_at": base, "settled_at": base + 60,
                "at": base + 60, "held_days": 0.04,
                "ret_gross": r + 0.013, "ret_after_costs": r}, path)
for i, r in enumerate(rets): pair(pp, i, r, now + i * 7200)
s2 = bl.summary(pp, min_trades=NP)
check(f"with {NP} settled trades a verdict is given", s2["settled"] == NP and bool(s2["why"]))
check("  ...the win rate is about a third, as the rule predicts",
      0.25 < s2["win_rate"] < 0.42, f"{s2['win_rate']*100:.0f}%")
check("  ...and a LOSING win rate does not by itself block it",
      s2["clears"] is True, "the mean and its bootstrap CI decide, not the sign test")
check("  ...the CI is a bootstrap, reported at both ends",
      s2["ci_low"] is not None and s2["ci_high"] > s2["ci_low"],
      f"[{s2['ci_low']*100:+.2f}%, {s2['ci_high']*100:+.2f}%]")
check("  ...and at the REAL floor of 863 the same record is NOT ENOUGH DATA",
      not bl.summary(pp)["clears"] and "NOT ENOUGH" in bl.summary(pp)["why"])
check("the report calls the win rate NOT a verdict, in words",
      "NOT a verdict" in open("breakout_ledger.py").read())
check("the chain of all those pairs still verifies", bl.verify(pp)[0])

pp3 = newp("null"); base = time.time() - NP * 7200
for i in range(NP):
    r = rng.gauss(0, 0.16)
    bl._append({"kind": "open", "open_id": f"N{i}", "sym": "X", "entry": 1.0,
                "window": 100, "sealed_at": base + i * 7200, "at": base + i * 7200}, pp3)
    bl._append({"kind": "settled", "open_id": f"N{i}", "sym": "X", "entry": 1.0, "exit": 1 + r,
                "sealed_at": base + i * 7200, "settled_at": base + i * 7200 + 60,
                "at": base + i * 7200 + 60, "held_days": 0.04,
                "ret_gross": r, "ret_after_costs": r}, pp3)
sn = bl.summary(pp3, min_trades=NP)
check("A ZERO-MEAN RECORD DOES NOT CLEAR -- the control that matters",
      not sn["clears"], sn["why"][:50])

sec("D2. stale settlement -- survivorship bias walking back in through the exit")

pp = newp("stale"); t0 = time.time() - 40 * 86400
RISE2 = [10.0 + i * 0.1 for i in range(120)]
bl.record_cycle([q("GONE", RISE2, 22.0), q("STAY", RISE2, 22.0)], now=t0, path=pp)
check("two calls opened", sum(1 for r in bl._read(pp) if r["payload"]["kind"] == "open") == 2)
bl.record_cycle([q("GONE", RISE2, 18.0), q("STAY", RISE2, 22.0)], now=t0 + 86400, path=pp)
check("a MARKS record carries the open calls' current prices",
      any(r["payload"]["kind"] == "marks" for r in bl._read(pp)),
      "without it a delisted asset can only settle at its entry price")
# GONE stops being quoted; STAY keeps reporting
for d in range(2, 12):
    bl.record_cycle([q("STAY", RISE2, 22.0)], now=t0 + d * 86400, path=pp)
st = [r["payload"] for r in bl._read(pp) if r["payload"]["kind"] == "settled"]
check("an asset that stops being quoted IS SETTLED, not stranded", len(st) == 1, "GONE")
check("  ...flagged as stale, so it is visible in the record",
      st[0].get("why") == "stale" and st[0]["sym"] == "GONE")
check("  ...at its LAST MARKED price, not its entry -- a collapse must not score zero",
      abs(st[0]["exit"] - 18.0) < 1e-9, f"exit {st[0]['exit']}")
check("  ...and the loss is real", st[0]["ret_after_costs"] < -0.15,
      f"{st[0]['ret_after_costs']*100:.1f}%")
check("the still-quoted call stays open", bl.summary(pp)["open"] == 1)
check("the summary counts stale settlements separately",
      bl.summary(pp)["stale_settled"] == 1)
check("STALE_DAYS is a bias control, and the file says so",
      "survivorship bias walking back in" in open("breakout_ledger.py").read())

sec("D3. the floor adapts to the live data, and the CI must be seed-stable")
s3 = bl.summary(pp, min_trades=1)
check("sd and the live-implied n are reported", "sd" in s3 and "n_needed_live" in s3)
pp4 = newp("noisy"); base = time.time() - 300 * 7200
rng2 = random.Random(11)
for i in range(300):
    r = rng2.gauss(0.004, 0.30)      # a real but tiny mean under huge noise
    bl._append({"kind": "open", "open_id": f"Q{i}", "sym": "X", "entry": 1.0,
                "window": 100, "sealed_at": base + i * 7200, "at": base + i * 7200}, pp4)
    bl._append({"kind": "settled", "open_id": f"Q{i}", "sym": "X", "entry": 1.0, "exit": 1 + r,
                "sealed_at": base + i * 7200, "settled_at": base + i * 7200 + 60,
                "at": base + i * 7200 + 60, "held_days": 0.04,
                "ret_gross": r, "ret_after_costs": r}, pp4)
s4 = bl.summary(pp4, min_trades=100)
check("past the fixed floor, a WORSE live sd/mean raises the bar and blocks",
      not s4["clears"] and s4["n_needed_live"] > 300,
      f"live n needed {s4['n_needed_live']}")
check("  ...and says the live number, not the backtest's, is the one to use",
      "LIVE sd/mean implies" in s4["why"])
check("the CI is checked on two seeds before it may clear",
      s2["ci_seed_stable"] is True and "ci_seed_stable" in s2)

sec("D4. the file may not promise a flag it does not have (test_g2's lesson)")
import re
src_all = open("breakout_ledger.py").read()
promised = set(re.findall(r"python breakout_ledger\.py ([^\n#]*)", src_all))
flags = set(re.findall(r"--[a-z-]+", " ".join(promised)))
have = set(re.findall(r'ap\.add_argument\("(--[a-z-]+)"', src_all))
check("EVERY FLAG IN THE USAGE BLOCK EXISTS IN THE PARSER",
      flags <= have, f"promised {sorted(flags)}, parser has {sorted(have)}")
check("  ...and --record, which the first version promised and did not have, is real",
      "--record" in have)
check("a partial universe refuses to record the day",
      "not recording this day" in src_all and "MIN_COVERAGE" in src_all)
check("the day boundary convention is stated (UTC), not left to differ from "
      "signal_ledger.py silently", bl.DAY_TZ == "UTC")

sec("D5. the pre-registered condition -- recorded, never acted on")

pp = newp("cond"); t5 = time.time() - 30 * 86400
UP = [10.0 + i * 0.1 for i in range(120)]          # BTC above its own 100d
DOWN = [30.0 - i * 0.15 for i in range(120)]       # BTC below it
bl.record_cycle([q("BTC", UP, 22.0), q("AAA", UP, 22.0)], now=t5, path=pp)
op = [r["payload"] for r in bl._read(pp) if r["payload"]["kind"] == "open"]
check("every sealed call stamps the market state at seal time",
      all("btc_up" in o and "breadth" in o for o in op), f"{len(op)} opens")
check("  ...and BTC rising is recorded as btc_up=True",
      all(o["btc_up"] is True for o in op))
check("  ...with the universe breadth alongside it",
      all(isinstance(o["breadth"], float) for o in op))

pp2 = newp("cond_down")
bl.record_cycle([q("BTC", DOWN, 5.0), q("AAA", UP, 22.0)], now=t5, path=pp2)
op2 = [r["payload"] for r in bl._read(pp2) if r["payload"]["kind"] == "open"]
check("BTC falling is recorded as btc_up=False", all(o["btc_up"] is False for o in op2))

pp3 = newp("cond_none")
bl.record_cycle([q("AAA", UP, 22.0)], now=t5, path=pp3)
op3 = [r["payload"] for r in bl._read(pp3) if r["payload"]["kind"] == "open"]
check("with no BTC in the quotes it is None, not False -- unknown and no are "
      "different facts", all(o["btc_up"] is None for o in op3))

# AAA must actually LOSE its high: a flat series still equals its own max.
DROP = UP[:-1] + [5.0]
bl.record_cycle([q("BTC", UP, 22.0), q("AAA", DROP, 5.0)], now=t5 + 86400 * 2, path=pp)
stt = [r["payload"] for r in bl._read(pp) if r["payload"]["kind"] == "settled"]
check("the condition travels onto the SETTLED record, so it can be read "
      "without re-cutting the data", stt and "btc_up" in stt[0])
check("the file says the condition is recorded, not acted on",
      "It is recorded, not acted on" in open("breakout_ledger.py").read())
check("  ...and names the period-flip that disqualified asset volatility",
      "REVERSED" in open("breakout_ledger.py").read()
      and "+2.61 vs -3.94" in open("breakout_ledger.py").read())

pp4 = newp("cond_split"); base = time.time() - 200 * 7200
rngc = random.Random(21)
for i in range(120):
    up = i % 2 == 0
    r = (0.02 if up else -0.05) + rngc.gauss(0, 0.02)
    bl._append({"kind": "open", "open_id": f"C{i}", "sym": "X", "entry": 1.0, "window": 100,
                "btc_up": up, "breadth": 0.05, "sealed_at": base + i * 7200,
                "at": base + i * 7200}, pp4)
    bl._append({"kind": "settled", "open_id": f"C{i}", "sym": "X", "entry": 1.0, "exit": 1 + r,
                "why": "exit", "btc_up": up, "breadth": 0.05,
                "sealed_at": base + i * 7200, "settled_at": base + i * 7200 + 60,
                "at": base + i * 7200 + 60, "held_days": 0.04,
                "ret_gross": r, "ret_after_costs": r}, pp4)
sc = bl.summary(pp4, min_trades=100)
check("the summary reports the split both ways", sc["btc_up_n"] == 60 and sc["btc_down_n"] == 60)
check("  ...and separates them correctly",
      sc["btc_up_mean"] > 0 > sc["btc_down_mean"],
      f"up {sc['btc_up_mean']*100:+.2f}%  down {sc['btc_down_mean']*100:+.2f}%")
check("  ...and the split GATES NOTHING -- the verdict is still the whole record",
      "btc_up" not in bl.summary(pp4, min_trades=100)["why"])

sec("E. the boundary")
src = open("breakout_ledger.py").read()
for word in ("place", "order", "api_key", "secret", "sealed_signals"):
    check(f"the file never {word}s anything",
          f"def {word}" not in src and f"{word}(" not in src.replace(f"'{word}'", ""),
          "" if word != "sealed_signals" else "Rule 5's counter is untouched")
home = os.path.expanduser("~")
synced = os.path.join(home, "covenant")     # the folder covenant_seal.py hashes
check("it writes to ~/.covenant, OUTSIDE the synced folder",
      os.path.dirname(bl.LEDGER) == os.path.join(home, ".covenant"), bl.LEDGER)
check("  ...and specifically NOT inside the sealed folder, which it would "
      "invalidate on every run",
      not os.path.abspath(bl.LEDGER).startswith(os.path.abspath(synced) + os.sep))

print(f"\n  {passed} passed, {failed} failed")
for f in fails: print(f"    FAILED: {f}")
shutil.rmtree(TMP, ignore_errors=True)
sys.exit(1 if failed else 0)
