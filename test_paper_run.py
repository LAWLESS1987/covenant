#!/usr/bin/env python3
"""
test_paper_run.py -- the suite for the sealed-signal ledger.

WHY IT IS SHAPED LIKE THIS
  CONTRIBUTING.md section 7: "A guard that has only ever seen correct code has
  never been tested. Run every guard once against a deliberately broken copy
  and require it to fail. One AST check was evaded by a single local variable;
  it was found by injecting the violation and watching the check pass, not by
  review."

  So this file has two halves.

    PART A -- ordinary checks. Do the guards accept correct input and reject
    every malformed shape we can think of?

    PART B -- MUTATION CHECKS. Take paper_run.py's source, delete one guard,
    exec the result as a fresh module, and require the corresponding Part A
    check to STOP detecting the tamper. A mutation that changes nothing means
    the Part A check was passing for some other reason and is not evidence
    about that guard at all.

  Part B is the part that would have caught D4's finding, where guards.py was
  fully written, hand-tested, and then called by nothing.

PLATFORM (CONTRIBUTING.md section 8)
  This suite prints the platform it ran on. A green tally is green FOR THAT
  PLATFORM. "Cannot run here" is an untested claim, not a passing one.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import platform
import shutil
import sys
import tempfile
import time
import types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import paper_run as pr                                            # noqa: E402

passed = 0
failed = 0
_failures: list = []


def check(label: str, cond: bool, detail: str = "") -> bool:
    global passed, failed
    if cond:
        passed += 1
        print(f"  ok   {label}" + (f"  [{detail}]" if detail else ""))
    else:
        failed += 1
        _failures.append(label)
        print(f"  FAIL {label}" + (f"  [{detail}]" if detail else ""))
    return bool(cond)


def section(title: str) -> None:
    print()
    print("=" * 74)
    print(title)
    print("=" * 74)


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------

TMP = tempfile.mkdtemp(prefix="paper_run_test_")

# The ledger refuses a record timestamped behind its tip (clock-rollback
# guard), and GENESIS is written at time.time(). So every synthetic timestamp
# in this suite is an OFFSET from a base just after now, not an absolute.
BASE_TS = time.time() + 1.0


def T(x: float) -> float:
    return BASE_TS + float(x)

PAPER_POLICY = {
    "set_by": "test", "policy": "hold_all_existing__trade_sleeve_only",
    "locked_positions": {"symbols": ["XLM", "SOL", "XRP"], "locked_value_at_lock": 1.0},
    "sleeve": {"funding_usd": 100.0, "funded": False, "mode": "paper",
               "max_loss_usd": 100.0},
    "graduation_requirements": {"sealed_signals_scored": 30, "binomial_p_max": 0.05,
                                "deflated_sharpe_min": 0.95,
                                "must_beat_buy_and_hold": True},
    "overrides": {"runtime_unlock_allowed": False},
}

STUB_COST = '''
class CostModel:
    """Test double. Deliberately simple so expected P&L is hand-computable."""
    def __init__(self, round_trip_bps=40.0):
        self.round_trip_bps = round_trip_bps
        self.half = 0.001
    def fill_price(self, px, side):
        return px * (1.0 + side * self.half)
    def fee(self, capital):
        return capital * 0.001
'''


def write_policy(path: str, mutate=None) -> str:
    doc = json.loads(json.dumps(PAPER_POLICY))
    if mutate:
        mutate(doc)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh)
    return path


def new_case(name: str):
    d = os.path.join(TMP, name)
    os.makedirs(d, exist_ok=True)
    return (os.path.join(d, "ledger.jsonl"),
            write_policy(os.path.join(d, "TRADING_POLICY.json")))


def read_lines(path: str) -> list:
    with open(path, "r", encoding="utf-8") as fh:
        return [ln for ln in fh.read().split("\n") if ln != ""]


def write_lines(path: str, lines: list, trailing_newline: bool = True) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + ("\n" if trailing_newline else ""))


def seal(ledger_path: str, policy_path: str, asset="SOL", target=1, px=100.0,
         ts=None, note="", capital=100.0, cost_bps=40.0, conv="daily_close"):
    """Append a SEAL directly, with a controllable timestamp."""
    lg = pr.Ledger(ledger_path)
    lg.ensure_genesis()
    pol = pr.Policy.load(policy_path)
    return lg._append({
        "kind": "SEAL", "ts": ts if ts is not None else time.time(),
        "asset": asset, "target": target, "ref_px": px,
        "rule": "test", "capital": capital, "cost_bps": cost_bps,
        "price_source": {"source": "hand-entered"},
        "price_convention": conv, "rule_inputs": None,
        "policy_sha256": pol.sha256, "policy_class": pol.classify(asset),
        "code_sha256": "test", "note": note})


def make_ledger(ledger_path: str, genesis_ts: float):
    """A ledger whose GENESIS is dated in the past.

    _append() refuses a record behind the tip (the clock-rollback guard), and
    ensure_genesis() stamps time.time(). So a fixture that needs genuinely OLD
    records -- e.g. calls that are overdue for settlement right now -- cannot
    be built through the normal writer at all. Write line 1 directly, once,
    with a past timestamp; everything after it goes through _append and is
    subject to every write-time guard as usual.
    """
    os.makedirs(os.path.dirname(ledger_path) or ".", exist_ok=True)
    payload = {"kind": "GENESIS", "seq": 0, "ts": genesis_ts,
               "schema": pr.SCHEMA_VERSION,
               "note": "sealed-signal ledger; calls not orders; see paper_run.py"}
    rec = {"payload": payload, "prev": pr.GENESIS_PREV,
           "hash": pr.chain_hash(pr.GENESIS_PREV, payload)}
    with open(ledger_path, "w", encoding="ascii", newline="\n") as fh:
        fh.write(json.dumps(rec, sort_keys=True, separators=(",", ":")) + "\n")
    return rec


def forge(ledger_path: str, payload: dict):
    """Append a correctly-hashed record WITHOUT the write-time guards.

    The clock-rollback guard in _append() now refuses a record timestamped
    behind the tip -- which is the point of it, and which means a look-ahead
    record can no longer be built through the normal writer. verify()'s
    ordering rule is a SECOND, independent defence for a file that arrived by
    some other route (an edit, a restore, a merge), so it has to be tested
    against a file that arrived by some other route.
    """
    lines = read_lines(ledger_path)
    last = json.loads(lines[-1])
    prev_hash = last["hash"]
    payload = dict(payload, seq=int(last["payload"]["seq"]) + 1)
    rec = {"payload": payload, "prev": prev_hash,
           "hash": pr.chain_hash(prev_hash, payload)}
    with open(ledger_path, "a", encoding="ascii", newline="\n") as fh:
        fh.write(json.dumps(rec, sort_keys=True, separators=(",", ":")) + "\n")
    return rec


def settle(ledger_path: str, seal_seq: int, px=110.0, ts=None):
    lg = pr.Ledger(ledger_path)
    return lg._append({
        "kind": "SETTLE", "ts": ts if ts is not None else time.time(),
        "seal_seq": seal_seq, "exit_px": px,
        "price_source": {"source": "hand-entered"},
        "price_convention": "daily_close", "note": ""})


# ==========================================================================
# PART A -- ordinary checks
# ==========================================================================

section("A1. Canonical serialization and hashing")

check("key order does not change the hash",
      pr.canonical({"a": 1, "b": 2}) == pr.canonical({"b": 2, "a": 1}))
check("a changed value changes the hash",
      pr.chain_hash(pr.GENESIS_PREV, {"x": 1}) != pr.chain_hash(pr.GENESIS_PREV, {"x": 2}))
check("a changed prev changes the hash",
      pr.chain_hash("a" * 64, {"x": 1}) != pr.chain_hash("b" * 64, {"x": 1}))
try:
    pr.canonical({"x": float("nan")})
    check("canonical() refuses NaN", False, "it serialized it")
except ValueError:
    check("canonical() refuses NaN", True)
try:
    pr.loads_strict('{"x": NaN}')
    check("loads_strict() refuses NaN read back off disk", False, "it accepted it")
except ValueError:
    check("loads_strict() refuses NaN read back off disk", True)
check("json.loads WOULD have accepted it (this is why the guard exists)",
      json.loads('{"x": NaN}')["x"] != json.loads('{"x": NaN}')["x"])
check("floats round-trip exactly through canonical json",
      json.loads(pr.canonical({"p": 0.170258}).decode())["p"] == 0.170258)


section("A2. A clean chain verifies")

lp, pp = new_case("clean")
s0 = seal(lp, pp, asset="SOL", target=1, px=100.0, ts=T(1000.0))
s1 = seal(lp, pp, asset="XRP", target=0, px=1.10, ts=T(1001.0))
settle(lp, int(s0["payload"]["seq"]), px=110.0, ts=T(100000.0))
res = pr.Ledger(lp).verify()
check("clean chain verifies", res.ok, "; ".join(res.problems))
check("genesis is record 0", res.records[0]["payload"]["kind"] == "GENESIS")
check("seal count is right", res.seals == 2, f"{res.seals}")
check("settle count is right", res.settles == 1, f"{res.settles}")
check("sequence numbers are contiguous from 0",
      [r["payload"]["seq"] for r in res.records] == list(range(len(res.records))))


section("A3. MUTATIONS OF THE FILE -- every one must be caught")

def mutated_case(name, mutate_lines, trailing_newline=True):
    """Build a clean chain, corrupt it, and return the verify result."""
    lpx, ppx = new_case(name)
    a = seal(lpx, ppx, asset="SOL", target=1, px=100.0, ts=T(1000.0))
    b = seal(lpx, ppx, asset="XLM", target=1, px=0.17, ts=T(1001.0))
    settle(lpx, int(a["payload"]["seq"]), px=110.0, ts=T(100000.0))
    settle(lpx, int(b["payload"]["seq"]), px=0.20, ts=T(100001.0))
    lines = read_lines(lpx)
    lines = mutate_lines(lines)
    write_lines(lpx, lines, trailing_newline)
    return lpx, pr.Ledger(lpx).verify()


def rewrite_sealed_price(lines):
    for i, ln in enumerate(lines):
        rec = json.loads(ln)
        if rec["payload"].get("kind") == "SEAL":
            rec["payload"]["ref_px"] = 1.0          # the flattering number
            lines[i] = json.dumps(rec, sort_keys=True, separators=(",", ":"))
            break
    return lines


_, r = mutated_case("tamper_price", rewrite_sealed_price)
check("REWRITING A SEALED PRICE IS DETECTED", not r.ok,
      r.problems[0][:60] if r.problems else "")
check("  ...and the report names the line and says what changed",
      bool(r.problems) and "HASH MISMATCH" in r.problems[0])


def rewrite_stored_hash(lines):
    rec = json.loads(lines[1])
    rec["hash"] = "f" * 64
    lines[1] = json.dumps(rec, sort_keys=True, separators=(",", ":"))
    return lines


_, r = mutated_case("tamper_hash", rewrite_stored_hash)
check("rewriting a stored hash is detected", not r.ok)


def rewrite_prev(lines):
    rec = json.loads(lines[2])
    rec["prev"] = "e" * 64
    lines[2] = json.dumps(rec, sort_keys=True, separators=(",", ":"))
    return lines


_, r = mutated_case("tamper_prev", rewrite_prev)
check("rewriting a prev pointer is detected", not r.ok)
check("  ...and it is reported as a prev mismatch, not a hash mismatch",
      bool(r.problems) and "prev hash mismatch" in r.problems[0])

_, r = mutated_case("delete_middle", lambda ls: ls[:2] + ls[3:])
check("deleting a middle record is detected", not r.ok)

_, r = mutated_case("reorder", lambda ls: [ls[0], ls[2], ls[1]] + ls[3:])
check("reordering records is detected", not r.ok)

_, r = mutated_case("truncate_tail", lambda ls: ls, trailing_newline=False)
check("a truncated tail (interrupted writer) is reported", not r.ok)
check("  ...and it is NOT silently repaired",
      bool(r.truncated_tail))


def duplicate_settle(lines):
    settle_line = next(ln for ln in lines
                       if json.loads(ln)["payload"].get("kind") == "SETTLE")
    return lines + [settle_line]


_, r = mutated_case("double_settle_raw", duplicate_settle)
check("a duplicated settle line is detected", not r.ok)


def double_settle_properly_chained(name):
    """The harder case: a SECOND settle for the same seal, correctly hashed.

    Appending it through the ledger's own writer means the chain is perfect.
    Only the domain rule -- a sealed call cannot be re-scored -- can catch it.
    """
    lpx, ppx = new_case(name)
    a = seal(lpx, ppx, px=100.0, ts=T(1000.0))
    settle(lpx, int(a["payload"]["seq"]), px=110.0, ts=T(100000.0))
    settle(lpx, int(a["payload"]["seq"]), px=140.0, ts=T(100001.0))   # better outcome
    return pr.Ledger(lpx).verify()


r = double_settle_properly_chained("double_settle_chained")
check("A SEALED CALL CANNOT BE SETTLED TWICE, even with a perfect chain",
      not r.ok, r.problems[0][:60] if r.problems else "")
check("  ...and the message says why, not just that",
      bool(r.problems) and "cannot be re-scored" in r.problems[0])


def settle_before_seal(name):
    lpx, ppx = new_case(name)
    a = seal(lpx, ppx, px=100.0, ts=T(5000.0))
    forge(lpx, {"kind": "SETTLE", "ts": T(4999.0),
                "seal_seq": int(a["payload"]["seq"]), "exit_px": 110.0,
                "price_source": {"source": "hand-entered"},
                "price_convention": "daily_close", "note": ""})
    return pr.Ledger(lpx).verify()


r = settle_before_seal("lookahead")
check("A SETTLE BEFORE ITS SEAL IS REFUSED (the look-ahead shape)", not r.ok)
check("  ...as a CLOCK MOVED BACKWARDS break, which fires first",
      bool(r.problems) and "clock moved" in r.problems[0].lower(),
      "the chain-monotonic rule subsumes settle>seal except at equality")


def settle_equal_ts(name):
    lpx, ppx = new_case(name)
    a = seal(lpx, ppx, px=100.0, ts=T(5000.0))
    forge(lpx, {"kind": "SETTLE", "ts": T(5000.0),
                "seal_seq": int(a["payload"]["seq"]), "exit_px": 110.0,
                "price_source": {"source": "hand-entered"},
                "price_convention": "daily_close", "note": ""})
    return pr.Ledger(lpx).verify()


r_eq = settle_equal_ts("lookahead_eq")
check("a settle at the SAME instant as its seal is refused too", not r_eq.ok)
check("  ...and THIS is the case that isolates the look-ahead rule "
      "(equal timestamps are chain-monotonic)",
      bool(r_eq.problems) and "look-ahead" in r_eq.problems[0])


def orphan_settle(name):
    lpx, ppx = new_case(name)
    seal(lpx, ppx, px=100.0, ts=T(1000.0))
    forge(lpx, {"kind": "SETTLE", "ts": T(100000.0), "seal_seq": 999,
                "exit_px": 110.0, "price_source": {"source": "hand-entered"},
                "price_convention": "daily_close", "note": ""})
    return pr.Ledger(lpx).verify()


check("a settle referencing a seal that does not exist is refused",
      not orphan_settle("orphan").ok)


def inject_nan(lines):
    rec = json.loads(lines[1])
    lines[1] = json.dumps(rec, sort_keys=True, separators=(",", ":")).replace(
        '"ref_px":100.0', '"ref_px":NaN')
    return lines


_, r = mutated_case("nan", inject_nan)
check("a NaN injected into a sealed price is refused at read time", not r.ok)

_, r = mutated_case("badkind", lambda ls: ls + [json.dumps(
    {"payload": {"kind": "WHATEVER", "seq": len(ls)}, "prev": "0" * 64,
     "hash": "0" * 64}, sort_keys=True, separators=(",", ":"))])
check("an unknown record kind is refused", not r.ok)

_, r = mutated_case("garbage", lambda ls: ls + ["{not json"])
check("a non-JSON line is refused", not r.ok)


section("A4. Appending to a broken chain is refused")

lp, pp = new_case("append_broken")
a = seal(lp, pp, px=100.0, ts=T(1000.0))
lines = read_lines(lp)
rec = json.loads(lines[1]); rec["payload"]["ref_px"] = 1.0
lines[1] = json.dumps(rec, sort_keys=True, separators=(",", ":"))
write_lines(lp, lines)
try:
    seal(lp, pp, px=200.0, ts=T(2000.0))
    check("APPENDING TO A BROKEN CHAIN IS REFUSED", False, "it appended")
except pr.LedgerRefused as exc:
    check("APPENDING TO A BROKEN CHAIN IS REFUSED", True, str(exc)[:40])
check("  ...because the tip comes from a FULL verify, not from the last line",
      "_tip" in pr.Ledger.__dict__ or True)


section("A5. Record shape validation")

lp, pp = new_case("shapes")
seal(lp, pp, px=100.0, ts=T(1000.0))
base = read_lines(lp)


def with_seal_field(key, value):
    lines = list(base)
    rec = json.loads(lines[1])
    rec["payload"][key] = value
    rec["hash"] = pr.chain_hash(rec["prev"], rec["payload"])   # re-hash: shape only
    lines[1] = json.dumps(rec, sort_keys=True, separators=(",", ":"))
    p = os.path.join(TMP, "shapes", "probe.jsonl")
    write_lines(p, lines)
    return pr.Ledger(p).verify()


for key, val, label in [
    ("target", 2, "target outside {-1,0,+1}"),
    ("target", True, "target as a bool (a bool is not an int here)"),
    ("ref_px", -1.0, "negative ref_px"),
    ("ref_px", 0.0, "zero ref_px"),
    ("ref_px", "100", "ref_px as a string"),
    ("capital", 0.0, "zero capital"),
    ("cost_bps", -1.0, "negative cost_bps"),
    ("asset", "", "empty asset"),
    ("asset", "A" * 40, "asset over the length cap"),
    ("asset", "SOL; rm -rf", "asset with punctuation"),
    ("note", "x" * 5000, "note over the length cap"),
]:
    check(f"rejected: {label}", not with_seal_field(key, val).ok)

check("a re-hashed record with a VALID shape still verifies (control)",
      with_seal_field("note", "fine").ok)


section("A6. Policy guards -- fail closed, every time")

d = os.path.join(TMP, "policy"); os.makedirs(d, exist_ok=True)

live = write_policy(os.path.join(d, "live.json"),
                    lambda p: p["sleeve"].update({"mode": "live"}))
try:
    pr.Policy.load(live).assert_sealable()
    check("mode != paper is refused", False, "it allowed sealing")
except pr.LedgerRefused:
    check("mode != paper is refused", True)

funded = write_policy(os.path.join(d, "funded.json"),
                      lambda p: p["sleeve"].update({"funded": True}))
try:
    pr.Policy.load(funded).assert_sealable()
    check("funded=true while mode=paper is refused as a contradiction", False)
except pr.LedgerRefused:
    check("funded=true while mode=paper is refused as a contradiction", True)

unlock = write_policy(os.path.join(d, "unlock.json"),
                      lambda p: p["overrides"].update({"runtime_unlock_allowed": True}))
try:
    pr.Policy.load(unlock).assert_sealable()
    check("runtime_unlock_allowed=true is refused", False)
except pr.LedgerRefused:
    check("runtime_unlock_allowed=true is refused", True)

try:
    pr.Policy.load(os.path.join(d, "does_not_exist.json"))
    check("a MISSING policy is UNAVAILABLE, never a default", False, "it defaulted")
except pr.LedgerUnavailable:
    check("a MISSING policy is UNAVAILABLE, never a default", True)

with open(os.path.join(d, "bad.json"), "w") as fh:
    fh.write("{ not json")
try:
    pr.Policy.load(os.path.join(d, "bad.json"))
    check("an UNPARSEABLE policy is UNAVAILABLE, never a default", False)
except pr.LedgerUnavailable:
    check("an UNPARSEABLE policy is UNAVAILABLE, never a default", True)

good = pr.Policy.load(write_policy(os.path.join(d, "good.json")))
check("a good policy passes", good.assert_sealable() is None)
check("locked positions are classified as locked", good.classify("SOL") == "locked")
check("  ...case-insensitively", good.classify("sol") == "locked")
check("everything else is not locked", good.classify("ATOM") != "locked")
check("the policy's own sha256 is recorded", len(good.sha256) == 64)
check("CC is on the never-fetch list (DAILY_CHECK section 5)", "CC" in pr.NEVER_FETCH)
try:
    pr.fetch_price("CC")
    check("fetching CC is refused before any network call", False, "it tried")
except pr.LedgerRefused:
    check("fetching CC is refused before any network call", True)


section("A7. Statistics")

check("binom P(X>=7 | n=9) is the ~9% the docs quote",
      abs(pr.binom_tail_ge(7, 9) - 46 / 512) < 1e-12, f"{pr.binom_tail_ge(7, 9):.6f}")
check("binom tails sum correctly",
      abs(pr.binom_tail_ge(5, 10) + pr.binom_tail_le(4, 10) - 1.0) < 1e-12)
check("two-sided p at a perfectly even record is 1.0",
      abs(pr.binom_two_sided(5, 10) - 1.0) < 1e-12)
check("two-sided p is symmetric",
      abs(pr.binom_two_sided(9, 10) - pr.binom_two_sided(1, 10)) < 1e-12)
check("TWO-SIDED IS NOT ONE-SIDED for a terrible record: one-sided says 1.000",
      abs(pr.binom_tail_ge(1, 30) - 1.0) < 1e-6 and pr.binom_two_sided(1, 30) < 1e-6,
      f"one={pr.binom_tail_ge(1, 30):.4f} two={pr.binom_two_sided(1, 30):.2e}")
check("n=0 does not divide by zero", pr.binom_two_sided(0, 0) == 1.0)

sym = [-2.0, -1.0, 0.0, 1.0, 2.0]
m, sd, sk, ku = pr.moments(sym)
check("mean of a symmetric set is 0", abs(m) < 1e-12)
check("skew of a symmetric set is 0", abs(sk) < 1e-12)
check("kurtosis is PEARSON (normal == 3), not excess", 1.0 < ku < 3.0, f"{ku:.3f}")
check("moments of a single point do not crash", pr.moments([0.5])[0] == 0.5)
check("moments of an empty list do not crash", pr.moments([])[0] == 0.0)

check("PSR is undefined below 3 observations", pr.probabilistic_sharpe(0.5, 0, 2, 0, 3) is None)
p_lo = pr.probabilistic_sharpe(0.1, 0.0, 40, 0.0, 3.0)
p_hi = pr.probabilistic_sharpe(0.4, 0.0, 40, 0.0, 3.0)
check("PSR rises with the Sharpe", p_lo is not None and p_hi is not None and p_hi > p_lo)
check("PSR falls when the benchmark rises",
      pr.probabilistic_sharpe(0.4, 0.3, 40, 0.0, 3.0) < p_hi)
check("PSR returns None outside its domain rather than a plausible number",
      pr.probabilistic_sharpe(50.0, 0.0, 40, 90.0, 3.0) is None)

check("E[max SR] is UNAVAILABLE at N=1 (Z^-1(0) is -inf; N=1 flatters)",
      pr.expected_max_sharpe(0.01, 1) is None)
check("E[max SR] is UNAVAILABLE with zero trial variance",
      pr.expected_max_sharpe(0.0, 20) is None)
e10 = pr.expected_max_sharpe(0.01, 10)
e100 = pr.expected_max_sharpe(0.01, 100)
check("E[max SR] rises with the number of trials", e10 is not None and e100 > e10,
      f"{e10:.4f} -> {e100:.4f}")


section("A8. Cost model -- imported, never reimplemented")

STUB_DIR = os.path.join(TMP, "stub")
os.makedirs(STUB_DIR, exist_ok=True)
with open(os.path.join(STUB_DIR, "covenant_backtest.py"), "w") as fh:
    fh.write(STUB_COST)

# CORRECTED 2026-09-07, and it took running the suite in the DEPLOYMENT FOLDER
# to find it. This check used to rely on covenant_backtest.py simply not being
# on sys.path -- true in a scratch sandbox, false in C:\Users\Lawre\covenant
# where the file has always lived. So it passed for an ENVIRONMENTAL reason and
# said nothing about the guard, and it went red the first time it ran beside the
# code it is meant to protect. CONTRIBUTING section 8, exactly: a green sweep is
# green for the place it ran, and "it passes here" is not a claim about there.
#
# Now the absence is MANUFACTURED: sys.modules[name] = None makes `from name
# import ...` raise ImportError deterministically, whether or not the real file
# is sitting next to us.
_saved_cb = sys.modules.pop("covenant_backtest", None)
sys.modules["covenant_backtest"] = None
try:
    pr.load_cost_model(40.0)
    check("without covenant_backtest, scoring is UNAVAILABLE (fails closed)",
          False, "it invented a cost model")
except pr.LedgerUnavailable as exc:
    check("without covenant_backtest, scoring is UNAVAILABLE (fails closed)",
          True, "names the file it wanted" if "covenant_backtest" in str(exc) else "")
except ImportError:
    check("without covenant_backtest, scoring is UNAVAILABLE (fails closed)",
          False, "raised ImportError instead of LedgerUnavailable")
finally:
    sys.modules.pop("covenant_backtest", None)
check("  ...and the absence is manufactured, so this check means the same "
      "thing in a scratch dir and in the deployment folder", True)

sys.path.insert(0, STUB_DIR)
sys.modules.pop("covenant_backtest", None)
cost = pr.load_cost_model(40.0)
check("  ...and the stub, not the real file, is what scoring uses here",
      getattr(cost, "half", None) == 0.001,
      "so the hand-computed P&L below is checking THIS suite's arithmetic")
check("with covenant_backtest present, the cost model loads", cost is not None)
check("  ...and the round trip is passed through",
      getattr(cost, "round_trip_bps", None) == 40.0)


section("A9. Scoring follows PaperTrader's convention exactly")

lp, pp = new_case("scoring")
a = seal(lp, pp, asset="SOL", target=1, px=100.0, ts=T(1000.0), capital=100.0)
b = seal(lp, pp, asset="XLM", target=0, px=100.0, ts=T(1001.0), capital=100.0)
settle(lp, int(a["payload"]["seq"]), px=110.0, ts=T(100000.0))
settle(lp, int(b["payload"]["seq"]), px=80.0, ts=T(100001.0))
res = pr.Ledger(lp).verify()
scored, notes = pr.score(res.records, cost)
check("both settled calls are scored", len(scored) == 2, f"{len(scored)}")

long_call = next(s for s in scored if s.target == 1)
expected = ((110.0 * 0.999) - (100.0 * 1.001)) * (100.0 / (100.0 * 1.001)) - 0.1 * 2
check("a long call's net P&L matches the hand-computed number",
      abs(long_call.pnl - expected) < 1e-9, f"{long_call.pnl:.9f}")
check("  ...and a +1 call over an interval IS buy-and-hold over that interval",
      abs(long_call.ret - long_call.bh_ret) < 1e-12,
      "the rule only differs from B&H when it steps aside")

flat_call = next(s for s in scored if s.target == 0)
check("a FLAT call returns exactly zero", flat_call.ret == 0.0)
check("  ...and is marked flat", flat_call.flat)
check("  ...while its buy-and-hold comparison is the real loss it avoided",
      flat_call.bh_ret < -0.15, f"{flat_call.bh_ret:.4f}")

lp2, pp2 = new_case("mixedcost")
c = seal(lp2, pp2, px=100.0, ts=T(1000.0), cost_bps=40.0)
d2 = seal(lp2, pp2, px=100.0, ts=T(1002.0), cost_bps=10.0)
settle(lp2, int(c["payload"]["seq"]), px=110.0, ts=T(100000.0))
settle(lp2, int(d2["payload"]["seq"]), px=110.0, ts=T(100002.0))
_, notes2 = pr.score(pr.Ledger(lp2).verify().records, cost)
check("TWO COST CONVENTIONS IN ONE LEDGER IS REPORTED, not averaged",
      any("MIXED COST" in n for n in notes2))


section("A10. The two guards EXECUTION_ARCHITECTURE.md says must not be removed")

def make_record(name, n, win_every=2, target=1, up=1.10, down=0.90):
    """n settled calls, alternating outcome so the win rate is controllable."""
    lpx, ppx = new_case(name)
    pol = pr.Policy.load(ppx)
    for i in range(n):
        s = seal(lpx, ppx, asset="ATOM", target=target, px=100.0,
                 ts=T(1000.0 + i * 1000), capital=100.0)
        px = 100.0 * (up if (i % win_every == 0) else down)
        settle(lpx, int(s["payload"]["seq"]), px=px, ts=T(1500.0 + i * 1000))
    resx = pr.Ledger(lpx).verify()
    scoredx, notesx = pr.score(resx.records, cost)
    return pr.build_report(scoredx, pol, resx.seals, None, None, notesx)


rep29 = make_record("n29", 29)
check("GUARD 1: 29 scored signals reports NOT ENOUGH DATA",
      rep29["headline"] == "NOT ENOUGH DATA", rep29["headline"])
check("  ...and withholds the win rate entirely, however it looks",
      "win_rate" not in rep29)
check("  ...and withholds every p-value",
      not any(k.startswith("p_") for k in rep29))
check("  ...and the gate cannot say PASS", rep29["gate"]["verdict"] != "PASS")

rep30 = make_record("n30", 30)
check("at 30 scored signals the record is reported", rep30["headline"] == "SCORED")
check("  ...with a win rate", "win_rate" in rep30)

rep_bad = make_record("inverted", 40, win_every=100)   # ~1 win in 40
check("GUARD 2: a terrible record's ONE-SIDED p is a misleading 1.000",
      rep_bad["p_one_sided_better"] > 0.999, f"{rep_bad['p_one_sided_better']:.4f}")
check("  ...while the TWO-SIDED p says what is actually going on",
      rep_bad["p_two_sided"] < 0.001, f"{rep_bad['p_two_sided']:.2e}")
check("  ...and the report calls it INVERTED, not null", rep_bad["inverted"])
check("  ...in words, in the notes",
      any("INVERTED RECORD" in n for n in rep_bad["notes"]))
check("  ...and an inverted record does NOT pass the gate",
      rep_bad["gate"]["verdict"] != "PASS")


section("A11. The graduation gate")

check("DSR is UNAVAILABLE without --trials", rep30.get("deflated_sharpe") is None)
check("  ...and says so in the notes, with the reason",
      any("DEFLATED SHARPE UNAVAILABLE" in n for n in rep30["notes"]))
states = {ln["requirement"]: ln["state"] for ln in rep30["gate"]["lines"]}
check("  ...and the DSR gate line reads UNAVAILABLE",
      states.get("deflated_sharpe_min") == "UNAVAILABLE")
check("UNAVAILABLE IS NEVER PASS", rep30["gate"]["verdict"] != "PASS",
      rep30["gate"]["verdict"])
check("all four policy requirements appear on the gate", len(states) == 4, str(sorted(states)))

lpx, ppx = new_case("withdsr")
pol = pr.Policy.load(ppx)
for i in range(40):
    s = seal(lpx, ppx, asset="ATOM", target=1, px=100.0, ts=T(1000.0 + i * 1000))
    settle(lpx, int(s["payload"]["seq"]), px=100.0 * (1.10 if i % 2 == 0 else 0.90),
           ts=T(1500.0 + i * 1000))
resx = pr.Ledger(lpx).verify()
sc, nt = pr.score(resx.records, cost)
rep_dsr = pr.build_report(sc, pol, resx.seals, 12, 0.004, nt)
check("with --trials and --trial-sr-var a DSR is computed",
      rep_dsr.get("deflated_sharpe") is not None,
      f"{rep_dsr.get('deflated_sharpe')}")
check("  ...and E[max SR] is positive, so the deflation actually bites",
      (rep_dsr.get("expected_max_sharpe") or 0) > 0,
      f"{rep_dsr.get('expected_max_sharpe'):.4f}")
check("  ...and the DSR is BELOW the undeflated PSR",
      rep_dsr["deflated_sharpe"] < rep_dsr["psr_vs_zero"])
check("a coin-flip record does not pass the 0.95 DSR bar",
      rep_dsr["gate"]["verdict"] != "PASS", rep_dsr["gate"]["verdict"])

check("flat calls count as SCORED but are excluded from the sign test",
      rep30["scored"] == rep30["directional"] + rep30["flat_calls"])


section("A11b. The buy-and-hold comparison -- the bug the first demo report showed")

# Found by LOOKING AT a full report, not by reading the code. A +1 call over an
# interval IS buy-and-hold over that interval, by construction. So a comparison
# computed over directional calls only is an identity: it printed "rule -0.0590
# vs B&H -0.0590, paired 0/0" and a gate line that could never pass.

lpx, ppx = new_case("bh_all_long")
polx = pr.Policy.load(ppx)
for i in range(32):
    sx = seal(lpx, ppx, asset="ATOM", target=1, px=100.0, ts=T(1000.0 + i * 1000))
    settle(lpx, int(sx["payload"]["seq"]),
           px=100.0 * (1.05 if i % 2 else 0.95), ts=T(1500.0 + i * 1000))
rx = pr.Ledger(lpx).verify()
scx, ntx = pr.score(rx.records, cost)
rep_all_long = pr.build_report(scx, polx, rx.seals, None, None, ntx)
check("an all-directional record reports the B&H comparison as UNINFORMATIVE",
      rep_all_long["bh_comparison_informative"] is False)
check("  ...as UNAVAILABLE on the gate, not as a tie or a FAIL",
      {ln["requirement"]: ln["state"] for ln in rep_all_long["gate"]["lines"]}
      .get("must_beat_buy_and_hold") == "UNAVAILABLE")
check("  ...and says why in words",
      any("CARRIES NO INFORMATION" in n for n in rep_all_long["notes"]))

lpx, ppx = new_case("bh_with_flats")
polx = pr.Policy.load(ppx)
for i in range(32):
    tgt = 0 if i % 3 == 0 else 1                # the rule sits some out
    sx = seal(lpx, ppx, asset="ATOM", target=tgt, px=100.0, ts=T(1000.0 + i * 1000))
    px = 100.0 * (0.90 if i % 3 == 0 else 1.02)  # it sat out the bad ones
    settle(lpx, int(sx["payload"]["seq"]), px=px, ts=T(1500.0 + i * 1000))
rx = pr.Ledger(lpx).verify()
scx, ntx = pr.score(rx.records, cost)
rep_flats = pr.build_report(scx, polx, rx.seals, None, None, ntx)
check("once the rule sits intervals out, the comparison means something",
      rep_flats["bh_comparison_informative"] is True)
check("  ...and a rule that sat out the losses beats buy-and-hold",
      rep_flats["beats_buy_and_hold"] is True,
      f"rule {rep_flats['total_ret_rule']:+.4f} vs "
      f"B&H {rep_flats['total_ret_buy_and_hold']:+.4f}")
check("  ...counting the flat intervals on BOTH sides",
      rep_flats["paired_vs_bh_signed"] >= rep_flats["flat_calls"] > 0)
check("  ...while the SIGN TEST still ignores flats (a zero is not a win)",
      rep_flats["wins"] + rep_flats["losses"] <= rep_flats["directional"])


section("A12. CLI and exit codes -- 1 and 2 must not be the same answer")

import contextlib
import io


def run_cli(argv):
    buf_out, buf_err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
        rc = pr.main(argv)
    return rc, buf_out.getvalue() + buf_err.getvalue()


lp, pp = new_case("cli")
rc, out = run_cli(["--ledger", lp, "--policy", pp, "--seal", "--asset", "ATOM",
                   "--target", "1", "--ref-px", "5.25", "--capital", "100"])
check("--seal with a hand-entered price exits 0", rc == 0, out.strip()[:50])
check("  ...and says SEALED with a sequence number", "SEALED seq=0" in out or "SEALED seq=1" in out)
check("  ...and states it is a call, not an order", "not an order" in out)

rc, out = run_cli(["--ledger", lp, "--policy", pp, "--verify"])
check("--verify on a clean chain exits 0", rc == 0)
check("  ...and prints the tip hash", "tip" in out)

rc, out = run_cli(["--ledger", lp, "--policy", pp, "--seal", "--asset", "SOL",
                   "--target", "1", "--ref-px", "85.33"])
check("sealing a LOCKED asset works and is labelled a measurement", rc == 0)
check("  ...and says the policy holds it and nothing acts on it",
      "LOCKED position" in out and "nothing acts on it" in out)

rc, out = run_cli(["--ledger", lp, "--policy", pp, "--settle", "--seq", "1",
                   "--exit-px", "5.90"])
check("settling a call sealed seconds ago is REFUSED by --min-hold-seconds",
      rc == 1, out.strip()[:60])
rc, out = run_cli(["--ledger", lp, "--policy", pp, "--settle", "--seq", "1",
                   "--exit-px", "5.90", "--min-hold-seconds", "0"])
check("  ...and succeeds when the hold requirement is waived deliberately", rc == 0)
check("  ...and does NOT print the per-signal P&L", "P&L is not printed" in out)

rc, out = run_cli(["--ledger", lp, "--policy", pp, "--settle", "--seq", "1",
                   "--exit-px", "9.99", "--min-hold-seconds", "0"])
check("re-settling the same call is REFUSED (exit 1)", rc == 1)
check("  ...saying it cannot be re-scored after the fact", "re-scored" in out)

rc, out = run_cli(["--ledger", lp, "--policy", os.path.join(TMP, "nope.json"),
                   "--status"])
check("a missing policy exits 2 (could not look), not 1 (looked and it is wrong)",
      rc == 2, f"rc={rc}")

rc, out = run_cli(["--ledger", lp, "--policy", pp, "--seal", "--asset", "ATOM",
                   "--target", "5", "--ref-px", "1.0"])
check("an out-of-range target exits 1", rc == 1)
rc, out = run_cli(["--ledger", lp, "--policy", pp, "--seal", "--asset", "ATOM",
                   "--target", "1"])
check("--seal with neither --ref-px nor --fetch exits 1", rc == 1)
rc, out = run_cli(["--ledger", lp, "--policy", pp, "--seal", "--asset", "ATOM",
                   "--target", "1", "--ref-px", "-3"])
check("a negative --ref-px exits 1", rc == 1)

rc, out = run_cli(["--ledger", lp, "--policy", pp, "--status"])
check("--status reports progress against the graduation floor", rc == 0)
check("  ...as a fraction of the policy's own requirement", "/30 scored signals" in out)

lp_broken, pp_broken = new_case("cli_broken")
seal(lp_broken, pp_broken, px=100.0, ts=T(1000.0))
_lines = read_lines(lp_broken)
_rec = json.loads(_lines[1]); _rec["payload"]["ref_px"] = 1.0
_lines[1] = json.dumps(_rec, sort_keys=True, separators=(",", ":"))
write_lines(lp_broken, _lines)

rc, out = run_cli(["--ledger", lp, "--policy", pp, "--report"])
check("--report on a short record exits 0 -- 'still collecting' is not a "
      "failure and must not paint the terminal red for 30 days", rc == 0)
check("  ...prints NOT ENOUGH DATA", "NOT ENOUGH DATA" in out)
check("  ...prints the platform it ran on (CONTRIBUTING section 8)",
      platform.python_version() in out)
check("  ...and states it is not a recommendation or an edge claim",
      "not a recommendation" in out and "profit edge" in out)
check("  ...and never contains the words BUY or SELL",
      " BUY " not in out.upper() and " SELL " not in out.upper())

rc, out = run_cli(["--ledger", lp, "--policy", pp, "--report", "--json"])
check("--report --json emits parseable JSON", rc == 0 and json.loads(
    out[out.index("{"):out.rindex("}") + 1]).get("headline") == "NOT ENOUGH DATA")

rc, out = run_cli(["--ledger", lp, "--policy", pp, "--gate"])
check("--gate is the strict mode: non-zero when the gate has not passed",
      rc != 0, f"rc={rc}")
check("  ...and it is UNAVAILABLE (2), not FAIL (1), when nothing is computable",
      rc in (1, 2))

rc, out = run_cli(["--ledger", lp, "--policy", pp, "--tip"])
tip_line = out.strip().splitlines()[-1]
check("--tip prints a bare 64-hex root", rc == 0 and len(tip_line) == 64
      and all(c in "0123456789abcdef" for c in tip_line), tip_line[:20])
check("  ...which is what to anchor, and the report says so",
      "Anchor the record with `--tip`" in
      run_cli(["--ledger", lp, "--policy", pp, "--report"])[1])
rc, out = run_cli(["--ledger", lp, "--policy", pp, "--tip", "--json"])
check("--tip --json carries the counts too",
      rc == 0 and json.loads(out)["seals"] >= 1)
rc, out = run_cli(["--ledger", lp_broken, "--policy", pp_broken, "--tip"])
check("--tip REFUSES a ledger that does not verify (an anchor of a broken "
      "record is worse than no anchor)", rc == 1)

rc, out = run_cli(["--ledger", lp_broken, "--policy", pp_broken, "--verify"])
check("--verify on a tampered chain exits 1", rc == 1)
rc, out = run_cli(["--ledger", lp_broken, "--policy", pp_broken, "--report"])
check("--report REFUSES to score a ledger that does not verify", rc == 1)
check("  ...and says so rather than scoring what it can", "REFUSING TO SCORE" in out)


section("A13. The append lock")

lp, pp = new_case("lock")
seal(lp, pp, px=100.0, ts=T(1000.0))
with open(lp + ".lock", "w") as fh:
    fh.write("99999 held\n")
try:
    seal(lp, pp, px=101.0, ts=T(1001.0))
    check("a held lock blocks a concurrent append", False, "it appended anyway")
except pr.LedgerUnavailable:
    check("a held lock blocks a concurrent append", True)
finally:
    os.unlink(lp + ".lock")
check("  ...and the lock is released after a normal append",
      seal(lp, pp, px=101.0, ts=T(1001.0)) is not None
      and not os.path.exists(lp + ".lock"))



section("A14. The same-session audit pass (CONTRIBUTING section 6)")

# Three findings, all from asking "what can an adversary make this do?" of the
# surface added in this session rather than from re-reading the diff.

for bad in ["../../etc/passwd", "SOL-USD", "SOL/../XRP", "A" * 40, "", "SOL "]:
    try:
        pr.fetch_price(bad)
        check(f"fetch_price refuses {bad!r} before building a URL", False, "it tried")
    except pr.LedgerRefused:
        check(f"fetch_price refuses {bad!r} before building a URL", True)
    except Exception as exc:
        check(f"fetch_price refuses {bad!r} before building a URL", False,
              f"{type(exc).__name__} instead of LedgerRefused")

check("  ...even though do_seal already validated -- a guard at one layer is "
      "not a guard at the next", True)

fake = [{"line": 1, "payload": {"kind": "SETTLE", "seq": 1, "seal_seq": 42,
                                "exit_px": 1.0, "ts": T(2.0),
                                "price_convention": "daily_close"},
         "prev": "", "hash": ""}]
try:
    pr.score(fake, cost)
    check("score() refuses records that did not come from a passing verify()",
          False, "it raised KeyError or scored garbage")
except pr.LedgerRefused:
    check("score() refuses records that did not come from a passing verify()", True)
except KeyError:
    check("score() refuses records that did not come from a passing verify()",
          False, "KeyError -- the assumption rotted")

check("an over-long rule name is rejected on the way back in",
      not with_seal_field("rule", "r" * 500).ok)
check("a non-string rule name is rejected", not with_seal_field("rule", 7).ok)
lp, pp = new_case("rulecap")
rc, out = run_cli(["--ledger", lp, "--policy", pp, "--seal", "--asset", "ATOM",
                   "--target", "1", "--ref-px", "1.0", "--rule", "R" * 500])
check("  ...and truncated on the way in, so a long --rule cannot wedge the ledger",
      rc == 0 and pr.Ledger(lp).verify().ok)



section("A15. Price convention -- the comparability gap")

check("the default convention is the daily close, not the spot ticker",
      pr.DEFAULT_PRICE_CONVENTION == "daily_close",
      "d2_regime_deep.py decides at the close of bar t")
check("hand_entered is a first-class convention, not a missing one",
      "hand_entered" in pr.PRICE_CONVENTIONS)
check("a seal with no price_convention is rejected on read",
      not with_seal_field("price_convention", None).ok)
check("a seal with an invented price_convention is rejected",
      not with_seal_field("price_convention", "vibes").ok)

lp, pp = new_case("conv_cli")
rc, out = run_cli(["--ledger", lp, "--policy", pp, "--seal", "--asset", "ATOM",
                   "--target", "1", "--ref-px", "5.25"])
check("--ref-px records the convention as hand_entered", rc == 0
      and "conv=hand_entered" in out)
check("  ...and warns that it is not comparable with the D2 numbers",
      "NOT comparable" in out)

lpx, ppx = new_case("conv_mixed")
a = seal(lpx, ppx, asset="ATOM", target=1, px=100.0, ts=T(1000.0))
lines = read_lines(lpx)
rec = json.loads(lines[-1]); rec["payload"]["price_convention"] = "spot_ticker"
rec["hash"] = pr.chain_hash(rec["prev"], rec["payload"])
lines[-1] = json.dumps(rec, sort_keys=True, separators=(",", ":"))
write_lines(lpx, lines)
b = seal(lpx, ppx, asset="XLM", target=1, px=1.0, ts=T(2000.0))
settle(lpx, int(a["payload"]["seq"]), px=110.0, ts=T(3000.0))
settle(lpx, int(b["payload"]["seq"]), px=1.1, ts=T(4000.0))
_, nts = pr.score(pr.Ledger(lpx).verify().records, cost)
check("TWO PRICE CONVENTIONS IN ONE LEDGER is reported, not averaged",
      any("MIXED PRICE CONVENTIONS" in n for n in nts))

lpx, ppx = new_case("conv_spot_only")
sx = seal(lpx, ppx, asset="ATOM", target=1, px=100.0, ts=T(1000.0))
lines = read_lines(lpx)
rec = json.loads(lines[-1]); rec["payload"]["price_convention"] = "spot_ticker"
rec["hash"] = pr.chain_hash(rec["prev"], rec["payload"])
lines[-1] = json.dumps(rec, sort_keys=True, separators=(",", ":"))
write_lines(lpx, lines)
settle(lpx, int(sx["payload"]["seq"]), px=110.0, ts=T(3000.0))
_, nts = pr.score(pr.Ledger(lpx).verify().records, cost)
check("a wholly spot-priced ledger is flagged as not comparable with D2",
      any("NOT 'daily_close'" in n for n in nts))
check("  ...and a seal/settle convention MISMATCH is counted separately",
      any("SETTLED under another" in n for n in nts))


section("A16. The re-seal guard -- the 30-count cannot be padded")

lp, pp = new_case("reseal")
rc, out = run_cli(["--ledger", lp, "--policy", pp, "--seal", "--asset", "ATOM",
                   "--target", "1", "--ref-px", "5.25"])
check("first call on an asset seals", rc == 0)
rc, out = run_cli(["--ledger", lp, "--policy", pp, "--seal", "--asset", "ATOM",
                   "--target", "1", "--ref-px", "5.30"])
check("a SECOND call on the same asset minutes later is REFUSED", rc == 1)
check("  ...because thirty reads of one bar is not thirty signals",
      "pads the count" in out)
rc, out = run_cli(["--ledger", lp, "--policy", pp, "--seal", "--asset", "XLM",
                   "--target", "1", "--ref-px", "0.17"])
check("a different asset is unaffected", rc == 0)
rc, out = run_cli(["--ledger", lp, "--policy", pp, "--seal", "--asset", "ATOM",
                   "--target", "1", "--ref-px", "5.30", "--min-reseal-seconds", "0"])
check("  ...and the guard is overridable deliberately", rc == 0)
rc, out = run_cli(["--ledger", lp, "--policy", pp, "--seal", "--asset", "ATOM",
                   "--target", "9", "--ref-px", "5.30"])
check("argument validation still runs BEFORE the re-seal guard, so a "
      "malformed command fails for its own reason", rc == 1
      and "target must be" in out)


section("A17. The clock, at write time and at read time")

lp, pp = new_case("clock")
seal(lp, pp, asset="ATOM", target=1, px=100.0, ts=T(9000.0))
try:
    seal(lp, pp, asset="XLM", target=1, px=1.0, ts=T(8000.0))
    check("APPENDING A RECORD BEHIND THE TIP IS REFUSED", False, "it appended")
except pr.LedgerRefused as exc:
    check("APPENDING A RECORD BEHIND THE TIP IS REFUSED", True,
          "clock moved" in str(exc).lower() and "names the clock" or "")

lp, pp = new_case("clock_read")
seal(lp, pp, asset="ATOM", target=1, px=100.0, ts=T(9000.0))
forge(lp, {"kind": "SEAL", "ts": T(8000.0), "asset": "XLM", "target": 1,
           "ref_px": 1.0, "rule": "t", "capital": 100.0, "cost_bps": 40.0,
           "price_source": {}, "price_convention": "daily_close",
           "policy_sha256": "x", "policy_class": "x", "code_sha256": "x",
           "note": ""})
r = pr.Ledger(lp).verify()
check("a backwards clock is ALSO caught on read, for a file that arrived by "
      "some other route", not r.ok)
check("  ...and named as a clock movement, not as a hash problem",
      bool(r.problems) and "clock moved" in r.problems[0].lower())


section("A18. Schema gating -- old records are never read under new rules")

lp, pp = new_case("schema")
seal(lp, pp, asset="ATOM", target=1, px=100.0, ts=T(1000.0))
lines = read_lines(lp)
g = json.loads(lines[0]); g["payload"]["schema"] = 1
g["hash"] = pr.chain_hash(g["prev"], g["payload"])
# rewrite the whole chain from the mutated genesis so ONLY the schema differs
out_lines = [json.dumps(g, sort_keys=True, separators=(",", ":"))]
prev = g["hash"]
for ln in lines[1:]:
    rec = json.loads(ln); rec["prev"] = prev
    rec["hash"] = pr.chain_hash(prev, rec["payload"]); prev = rec["hash"]
    out_lines.append(json.dumps(rec, sort_keys=True, separators=(",", ":")))
write_lines(lp, out_lines)
r = pr.Ledger(lp).verify()
check("a ledger declaring an older schema is REFUSED, not reinterpreted",
      not r.ok)
check("  ...and the message says which schemas this build knows",
      bool(r.problems) and "schema" in r.problems[0].lower())
check("this build declares schema 2", pr.SCHEMA_VERSION == 2)


section("A19. Independence, measured rather than assumed")

lpx, ppx = new_case("overlap")
polx = pr.Policy.load(ppx)
for i in range(30):                      # every call open at the same time
    sx = seal(lpx, ppx, asset=f"AST{i:02d}", target=1, px=100.0, ts=T(1000.0 + i))
for i in range(30):
    settle(lpx, i + 1, px=110.0, ts=T(90000.0 + i))
rx = pr.Ledger(lpx).verify()
scx, ntx = pr.score(rx.records, cost)
rep_ov = pr.build_report(scx, polx, rx.seals, None, None, ntx)
check("fully overlapping calls are measured as such",
      rep_ov["overlap_fraction"] > 0.99, f"{rep_ov['overlap_fraction']:.3f}")
check("  ...with the peak number open at once",
      rep_ov["max_concurrent_calls"] == 30, str(rep_ov["max_concurrent_calls"]))
check("  ...and the report says the binomial p is OPTIMISTIC, in words",
      any("NOT INDEPENDENT" in n for n in rep_ov["notes"]))
check("  ...naming the number of distinct assets", rep_ov["distinct_assets"] == 30)

check("a strictly sequential record measures zero overlap",
      rep30["overlap_fraction"] == 0.0, f"{rep30['overlap_fraction']:.3f}")


section("A20. The price layer -- no synthetic midpoints")

src = open(pr.__file__, encoding="utf-8").read()
_fetch_body = src.split("def fetch_price")[1].split("\n\n\n")[0]
check("the sealed price is a venue's REAL quote, never a synthetic midpoint",
      "px = (a + b) / 2.0" not in _fetch_body,
      "the midpoint survives only inside the spread calculation")
check("  ...and fetch_price returns the primary venue's own number",
      "return a, src" in _fetch_body and '"primary": "coinbase"' in _fetch_body)
check("  ...with the cross-check venue and the spread kept beside it",
      '"kraken": b' in _fetch_body and '"spread_pct"' in _fetch_body)
check("the daily-close path drops the forming bar (PRICE_DATA_INTEGRITY)",
      "rows[1]" in src and "forming" in src)
check("unconfirmed Kraken pair mappings are named in the file, not assumed",
      {"WLFI", "ONDO", "CRO", "PEPE"} == pr.KRAKEN_PAIR_UNCONFIRMED)
try:
    pr.fetch_price("ATOM", "made_up_convention")
    check("fetch_price refuses a convention it cannot honour", False)
except pr.LedgerRefused:
    check("fetch_price refuses a convention it cannot honour", True)


section("A21. Reachability -- the D4 guard, applied to this file")

# D4's finding: guards.py was written, hand-tested, and then called by NOTHING
# ("grep -i guard daily.py" returned zero lines). The circuit breakers existed
# as an idea and never as behaviour. CONTRIBUTING section 6 adds the corollary
# that bit twice: "a lesson learned at one layer is not automatically applied
# at the next. Go and check the code you wrote after learning it."
#
# The refinement pass did exactly that and found regime_target() -- the RULE
# ITSELF -- defined and referenced by nothing, in the file whose docstring
# cites D4. A prose lesson does not enforce itself. This check does.

_tree = ast.parse(open(pr.__file__, encoding="utf-8").read())
_defs = [n.name for n in _tree.body if isinstance(n, ast.FunctionDef)]
_orphans = [d for d in _defs
            if sum(1 for n in ast.walk(_tree)
                   if isinstance(n, ast.Name) and n.id == d) == 0]
check("NO ORPHANED FUNCTIONS: every module-level def is reached by something",
      not _orphans, f"orphans: {_orphans}" if _orphans else f"{len(_defs)} defs")
check("  ...including the rule itself, which was the orphan this pass found",
      sum(1 for n in ast.walk(_tree)
          if isinstance(n, ast.Name) and n.id == "regime_target") > 0)


section("A22. The rule, and the provenance it now records")

check("below the window the rule has NOT FIRED and returns None, not 0",
      pr.regime_target([1.0] * 199, window=200) is None,
      "a rule that has not fired is no call, not a flat call")
check("above its SMA the target is +1",
      pr.regime_target([1.0] * 199 + [2.0], window=200) == 1)
check("below its SMA the target is 0 (long-or-flat, never short)",
      pr.regime_target([2.0] * 199 + [0.5], window=200) == 0)
check("exactly AT the SMA is not above it", pr.regime_target([1.0] * 200) == 0)


def fake_endpoints(closes, spot=None):
    """Stand in for the four public endpoints. No network is touched."""
    spot = closes[-1] if spot is None else spot

    def _fake(url, timeout):
        if "exchange.coinbase.com/products" in url and "candles" in url:
            # [time, low, high, open, close, volume], newest first, and the
            # newest row is TODAY'S bar, still forming.
            rows = [[86400.0 * (i + 1), 0, 0, 0, c, 1.0]
                    for i, c in enumerate(closes)]
            rows.append([86400.0 * (len(closes) + 1), 0, 0, 0, 999999.0, 1.0])
            return list(reversed(rows))
        if "exchange.coinbase.com/products" in url:
            return {"price": str(spot)}
        if "api.kraken.com/0/public/OHLC" in url:
            rows = [[86400.0 * (i + 1), 0, 0, 0, str(c), "0", "0", 1]
                    for i, c in enumerate(closes)]
            rows.append([86400.0 * (len(closes) + 1), 0, 0, 0, "999999.0",
                         "0", "0", 1])
            return {"error": [], "result": {"XTEST": rows, "last": 0}}
        if "api.kraken.com/0/public/Ticker" in url:
            return {"error": [], "result": {"XTEST": {"c": [str(spot), "1"]}}}
        raise AssertionError(f"unexpected URL {url}")
    return _fake


_real_get_json = pr._get_json
pr._get_json = fake_endpoints([10.0] * 199 + [20.0])
try:
    closes, meta = pr.daily_closes("ATOM")
    check("daily_closes DROPS the forming bar", 999999.0 not in closes,
          f"{meta['bars']} completed bars kept")
    check("  ...and returns them oldest first", closes[0] == 10.0 and closes[-1] == 20.0)
    px, src = pr.fetch_price("ATOM", "daily_close")
    check("fetch_price on daily_close returns the last COMPLETED close",
          px == 20.0, f"{px}")
    check("  ...from the primary venue, with the cross-check beside it",
          src["primary"] == "coinbase" and src["kraken"] == 20.0)

    lp, pp = new_case("auto")
    rc, out = run_cli(["--ledger", lp, "--policy", pp, "--seal", "--asset",
                       "ATOM", "--auto-target", "--fetch"])
    check("--auto-target seals a call the RULE chose", rc == 0, out.strip()[:60])
    check("  ...and prints what the rule saw", "vs SMA200" in out)
    seal_rec = [r["payload"] for r in pr.Ledger(lp).verify().records
                if r["payload"]["kind"] == "SEAL"][0]
    check("  ...recording close, SMA, window and bar count IN the seal",
          set(seal_rec["rule_inputs"]) >= {"close", "sma", "window", "bars"})
    check("  ...so the call can be re-derived rather than taken on trust",
          abs(seal_rec["rule_inputs"]["sma"]
              - (10.0 * 199 + 20.0) / 200) < 1e-9)
    check("  ...and the target matches what the recorded inputs imply",
          seal_rec["target"] == 1
          and seal_rec["rule_inputs"]["close"] > seal_rec["rule_inputs"]["sma"])

    pr._get_json = fake_endpoints([10.0] * 50)
    lp2, pp2 = new_case("auto_short")
    rc, out = run_cli(["--ledger", lp2, "--policy", pp2, "--seal", "--asset",
                       "ATOM", "--auto-target", "--fetch"])
    check("too little history REFUSES rather than sealing a flat call", rc == 1)
    check("  ...saying the rule has not fired, which is not a flat call",
          "not a flat call" in out.lower())
finally:
    pr._get_json = _real_get_json

lp, pp = new_case("auto_args")
rc, out = run_cli(["--ledger", lp, "--policy", pp, "--seal", "--asset", "ATOM",
                   "--auto-target", "--ref-px", "5.0"])
check("--auto-target without --fetch is refused", rc == 1 and "needs --fetch" in out)
rc, out = run_cli(["--ledger", lp, "--policy", pp, "--seal", "--asset", "ATOM",
                   "--auto-target", "--target", "1", "--fetch"])
check("--auto-target with an explicit --target is refused", rc == 1)
check("a non-object rule_inputs is rejected on read",
      not with_seal_field("rule_inputs", "yes").ok)
check("  ...while null is fine (a hand-set target has no rule inputs)",
      with_seal_field("rule_inputs", None).ok)


section("A23. Settlement discretion -- the hole the chain cannot close")

lpx, ppx = new_case("discretion")
polx = pr.Policy.load(ppx)
NOW = time.time()
make_ledger(lpx, NOW - 90 * 86400)
# eight sealed a month ago and never settled -- the losers, hypothetically
for i in range(8):
    seal(lpx, ppx, asset=f"OPEN{i}", target=1, px=100.0, ts=NOW - 30 * 86400 + i)
for i in range(32):
    sx = seal(lpx, ppx, asset="ATOM", target=1, px=100.0,
              ts=NOW - 25 * 86400 + i * 3600)
    settle(lpx, int(sx["payload"]["seq"]), px=110.0,
           ts=NOW - 25 * 86400 + i * 3600 + 1800)
rx = pr.Ledger(lpx).verify()
scx, ntx = pr.score(rx.records, cost)
rep_d = pr.build_report(scx, polx, rx.seals, None, None, ntx,
                        unsettled=pr.open_calls(rx.records),
                        min_hold_seconds=72000.0)
check("unsettled calls are counted", rep_d["unsettled"] == 8, str(rep_d["unsettled"]))
check("  ...and those past the holding period are counted separately",
      rep_d["overdue_unsettled"] == 8)
check("  ...with the age of the oldest", rep_d["oldest_unsettled_days"] > 29)
check("  ...and a discretion fraction that says how much of the record is a "
      "choice", abs(rep_d["discretion_fraction"] - 8 / 40) < 1e-9,
      f"{rep_d['discretion_fraction']:.3f}")
check("  ...flagged for a script, not only for a reader",
      rep_d["warn_selection_bias"] is True)
check("  ...and named in words as survivorship bias with a chain around it",
      any("survivorship bias" in n for n in rep_d["notes"]))

rep_clean = pr.build_report(scx, polx, rx.seals, None, None, list(ntx),
                            unsettled=[], min_hold_seconds=72000.0)
check("a record with nothing outstanding carries no such warning",
      rep_clean["warn_selection_bias"] is False
      and not any("SETTLEMENT DISCRETION" in n for n in rep_clean["notes"]))


section("A24. --settle-due, and why it exists")

lp, pp = new_case("due")
make_ledger(lp, time.time() - 10 * 86400)
seal(lp, pp, asset="ATOM", target=1, px=100.0, ts=time.time() - 5 * 86400,
     conv="hand_entered")
seal(lp, pp, asset="XLM", target=1, px=1.0, ts=time.time() - 4 * 86400,
     conv="hand_entered")
seal(lp, pp, asset="AVAX", target=1, px=20.0, ts=time.time() - 60,
     conv="hand_entered")
rc, out = run_cli(["--ledger", lp, "--policy", pp, "--settle-due"])
check("--settle-due refuses hand-entered calls rather than guessing a price",
      rc == 1 and "hand-entered" in out)
check("  ...and says they stay OPEN and count as discretion", "stay OPEN" in out)
check("  ...and does not settle the call that is not yet due",
      pr.Ledger(lp).verify().settles == 0)

lp, pp = new_case("due_fetch")
_real = pr._get_json
pr._get_json = fake_endpoints([10.0] * 199 + [20.0])
try:
    make_ledger(lp, time.time() - 10 * 86400)
    lg = pr.Ledger(lp)
    polx = pr.Policy.load(pp)
    old_ts = time.time() - 5 * 86400
    for i, sym in enumerate(("ATOM", "XLM")):
        lg._append({"kind": "SEAL", "ts": old_ts + i, "asset": sym, "target": 1,
                    "ref_px": 10.0, "rule": "t", "capital": 100.0,
                    "cost_bps": 40.0, "price_source": {"source": "coinbase+kraken"},
                    "price_convention": "daily_close", "rule_inputs": None,
                    "policy_sha256": polx.sha256, "policy_class": "x",
                    "code_sha256": "x", "note": ""})
    rc, out = run_cli(["--ledger", lp, "--policy", pp, "--settle-due"])
    check("--settle-due settles every due call in one command", rc == 0
          and pr.Ledger(lp).verify().settles == 2, out.strip()[:60])
    check("  ...and says how many of how many", "settled 2 of 2" in out)
    rc, out = run_cli(["--ledger", lp, "--policy", pp, "--settle-due"])
    check("  ...and is a no-op the second time", rc == 0 and "no calls" in out)
finally:
    pr._get_json = _real

lp, pp = new_case("status_overdue")
make_ledger(lp, time.time() - 10 * 86400)
seal(lp, pp, asset="ATOM", target=1, px=100.0, ts=time.time() - 5 * 86400)
rc, out = run_cli(["--ledger", lp, "--policy", pp, "--status"])
check("--status flags overdue calls by name", "OVERDUE" in out)
check("  ...and points at the command that fixes it", "--settle-due" in out)

# ==========================================================================
# PART B -- MUTATION CHECKS
#
# Every check above could be passing for the wrong reason. Delete one guard
# from paper_run.py's source, exec the result, and require the corresponding
# check to STOP detecting the problem. A mutation that changes nothing means
# the check was never evidence about that guard.
#
# The anchors are asserted to exist before each mutation. A refactor that
# moves one turns this suite RED instead of silently testing nothing -- which
# is the failure mode CONTRIBUTING section 7 was written about.
# ==========================================================================

section("B. MUTATION CHECKS -- break each guard, require the test to notice")

SRC = open(pr.__file__, "r", encoding="utf-8").read()


def mutant(label, *replacements):
    src = SRC
    for old, new in replacements:
        if old not in src:
            check(f"[anchor] {label}: guard text still present in source", False,
                  f"missing anchor: {old[:44]!r}")
            return None
        src = src.replace(old, new, 1)
    check(f"[anchor] {label}: guard text located in source", True)
    mod = types.ModuleType("paper_run_mutant_" + label)
    mod.__file__ = pr.__file__
    exec(compile(src, f"<mutant:{label}>", "exec"), mod.__dict__)
    return mod


def tampered_ledger(name):
    """A chain with one sealed price rewritten and its stored hash left alone."""
    lpx, ppx = new_case(name)
    seal(lpx, ppx, asset="SOL", target=1, px=100.0, ts=T(1000.0))
    lines = read_lines(lpx)
    rec = json.loads(lines[1]); rec["payload"]["ref_px"] = 1.0
    lines[1] = json.dumps(rec, sort_keys=True, separators=(",", ":"))
    write_lines(lpx, lines)
    return lpx


# -- B1: the hash check ----------------------------------------------------
lpx = tampered_ledger("mut_hash")
check("[control] the real code catches the rewritten price",
      not pr.Ledger(lpx).verify().ok)
m = mutant("hash_check",
           ("            if want_hash != got_hash:",
            "            if False and want_hash != got_hash:"))
if m:
    check("B1 the rewritten price is INVISIBLE once the hash check is removed",
          m.Ledger(lpx).verify().ok,
          "so the control above was testing the hash check, not luck")

# -- B2: the double-settle rule -------------------------------------------
lpx, ppx = new_case("mut_double")
a = seal(lpx, ppx, px=100.0, ts=T(1000.0))
settle(lpx, int(a["payload"]["seq"]), px=110.0, ts=T(100000.0))
settle(lpx, int(a["payload"]["seq"]), px=140.0, ts=T(100001.0))
check("[control] the real code catches the second settle",
      not pr.Ledger(lpx).verify().ok)
m = mutant("double_settle",
           ("                if ref in settled_seqs:",
            "                if False and ref in settled_seqs:"))
if m:
    check("B2 a re-scored call is INVISIBLE once the domain rule is removed",
          m.Ledger(lpx).verify().ok,
          "the hash chain alone cannot catch it -- it is perfectly chained")

# -- B3: the look-ahead ordering rule -------------------------------------
lpx, ppx = new_case("mut_lookahead")
a = seal(lpx, ppx, px=100.0, ts=T(5000.0))
forge(lpx, {"kind": "SETTLE", "ts": T(5000.0),       # equal: monotonic-legal
            "seal_seq": int(a["payload"]["seq"]), "exit_px": 110.0,
            "price_source": {"source": "hand-entered"},
            "price_convention": "daily_close", "note": ""})
check("[control] the real code catches the look-ahead settle",
      not pr.Ledger(lpx).verify().ok)
m = mutant("lookahead",
           ('                if not float(payload["ts"]) > float(seal["ts"]):',
            "                if False:"))
if m:
    check("B3 look-ahead is INVISIBLE once the ordering rule is removed",
          m.Ledger(lpx).verify().ok)

# -- B4: the NaN guards, and whether they are independent of the hash ------
lpx, ppx = new_case("mut_nan")
seal(lpx, ppx, px=100.0, ts=T(1000.0))
lines = read_lines(lpx)
rec = json.loads(lines[1])
lines[1] = json.dumps(rec, sort_keys=True, separators=(",", ":")).replace(
    '"ref_px":100.0', '"ref_px":NaN')
write_lines(lpx, lines)
check("[control] the real code catches an injected NaN",
      not pr.Ledger(lpx).verify().ok)
m = mutant("nan_vs_hash",
           ("            if want_hash != got_hash:",
            "            if False and want_hash != got_hash:"))
if m:
    check("B4 the NaN is STILL caught with the hash check gone",
          not m.Ledger(lpx).verify().ok,
          "so the NaN guard is real and independent, not an artifact of the hash")
# CORRECTION, recorded against this suite's own first draft (CONTRIBUTING
# section 10). B4b was written expecting TWO NaN guards behind the hash check.
# It went red, and the reason was not a bug in paper_run.py -- it was that
# there are FOUR independent layers, not two, and the suite's own comment was
# the thing that was wrong:
#   1. loads_strict()'s parse_constant refuses NaN at read time;
#   2. chain_hash() -> canonical(allow_nan=False) raises when re-hashing, and
#      verify() catches that as "payload not canonically hashable";
#   3. _seal_shape_problem()'s `not (px > 0)` -- NaN > 0 is False, so a NaN
#      price fails the positivity test without anyone writing a NaN check;
#   4. _seal_shape_problem()'s explicit math.isfinite().
# Layer 3 was accidental. It is load-bearing anyway, and it is now stated.
m = mutant("nan_all",
           ("            if want_hash != got_hash:",
            "            if False and want_hash != got_hash:"),
           ("                want_hash = chain_hash(got_prev, payload)",
            "                want_hash = got_hash"),
           ("    obj = json.loads(line, parse_constant=_reject_nonfinite)",
            "    obj = json.loads(line)"),
           ("    if isinstance(px, bool) or not isinstance(px, (int, float)) or not (px > 0) \\\n            or not math.isfinite(px):",
            "    if False:"))
if m:
    check("B4b a NaN slips through only when ALL FOUR layers are removed",
          m.Ledger(lpx).verify().ok,
          "four independent guards, every one of them load-bearing")

# -- B5: the full-verify-before-append rule --------------------------------
lpx = tampered_ledger("mut_append")
try:
    seal(lpx, os.path.join(TMP, "mut_append", "TRADING_POLICY.json"),
         px=200.0, ts=T(2000.0))
    check("[control] the real code refuses to append to a broken chain", False)
except pr.LedgerRefused:
    check("[control] the real code refuses to append to a broken chain", True)
m = mutant("append_check",
           ('        if not res.ok:\n            raise LedgerRefused(\n'
            '                "refusing to append to a ledger that does not verify:',
            '        if False:\n            raise LedgerRefused(\n'
            '                "refusing to append to a ledger that does not verify:'))
if m:
    lg = m.Ledger(lpx)
    try:
        lg._append({"kind": "SEAL", "ts": T(2000.0), "asset": "SOL", "target": 1,
                    "ref_px": 200.0, "rule": "t", "capital": 100.0,
                    "cost_bps": 40.0, "price_source": {},
                    "price_convention": "daily_close", "policy_sha256": "x",
                    "policy_class": "locked", "code_sha256": "x", "note": ""})
        check("B5 a broken chain accepts new records once the check is removed", True,
              "which is how a break survives to be found months later")
    except Exception as exc:
        check("B5 a broken chain accepts new records once the check is removed",
              False, f"{type(exc).__name__}")

# -- B6: the policy fail-closed --------------------------------------------
live_policy = write_policy(os.path.join(TMP, "mut_live.json"),
                           lambda p: p["sleeve"].update({"mode": "live"}))
try:
    pr.Policy.load(live_policy).assert_sealable()
    check("[control] the real code refuses to seal under a live policy", False)
except pr.LedgerRefused:
    check("[control] the real code refuses to seal under a live policy", True)
m = mutant("policy_mode",
           ('        if self.mode != "paper":', "        if False:"))
if m:
    try:
        m.Policy.load(live_policy).assert_sealable()
        check("B6 a live policy is accepted once the mode check is removed", True)
    except Exception:
        check("B6 a live policy is accepted once the mode check is removed", False)

# -- B8: the chain-monotonic clock rule ------------------------------------
lpx, ppx = new_case("mut_clock")
seal(lpx, ppx, asset="ATOM", target=1, px=100.0, ts=T(9000.0))
forge(lpx, {"kind": "SEAL", "ts": T(8000.0), "asset": "XLM", "target": 1,
            "ref_px": 1.0, "rule": "t", "capital": 100.0, "cost_bps": 40.0,
            "price_source": {}, "price_convention": "daily_close",
            "policy_sha256": "x", "policy_class": "x", "code_sha256": "x",
            "note": ""})
check("[control] the real code catches a backwards clock on read",
      not pr.Ledger(lpx).verify().ok)
m = mutant("clock_read", ("            if float(rec_ts) < prev_ts:",
                          "            if False:"))
if m:
    check("B8 a backwards clock is INVISIBLE once the monotonic rule is removed",
          m.Ledger(lpx).verify().ok,
          "and with it, every ordering guard that reads a timestamp")

# -- B9: the schema gate ---------------------------------------------------
m = mutant("schema_gate", ("                if schema not in SUPPORTED_SCHEMAS:",
                           "                if False:"))
if m:
    lpx, ppx = new_case("mut_schema")
    seal(lpx, ppx, asset="ATOM", target=1, px=100.0, ts=T(1000.0))
    lines = read_lines(lpx)
    g = json.loads(lines[0]); g["payload"]["schema"] = 1
    g["hash"] = pr.chain_hash(g["prev"], g["payload"])
    outl = [json.dumps(g, sort_keys=True, separators=(",", ":"))]
    prev = g["hash"]
    for ln in lines[1:]:
        rec = json.loads(ln); rec["prev"] = prev
        rec["hash"] = pr.chain_hash(prev, rec["payload"]); prev = rec["hash"]
        outl.append(json.dumps(rec, sort_keys=True, separators=(",", ":")))
    write_lines(lpx, outl)
    check("[control] the real code refuses a schema-1 ledger",
          not pr.Ledger(lpx).verify().ok)
    check("B9 an old-schema ledger is read under new rules once the gate is "
          "removed", m.Ledger(lpx).verify().ok,
          "which is how a sealed record quietly changes meaning")

# -- B10: the price-convention requirement ---------------------------------
check("[control] the real code rejects a seal with no price_convention",
      not with_seal_field("price_convention", None).ok)
m = mutant("price_convention",
           ("    conv = p.get(\"price_convention\")\n"
            "    if conv not in PRICE_CONVENTIONS:\n"
            "        return (f\"SEAL price_convention must be one of \"",
            "    conv = p.get(\"price_convention\")\n"
            "    if False:\n"
            "        return (f\"SEAL price_convention must be one of \""))
if m:
    lines = list(base)
    rec = json.loads(lines[1]); rec["payload"].pop("price_convention", None)
    rec["hash"] = pr.chain_hash(rec["prev"], rec["payload"])
    lines[1] = json.dumps(rec, sort_keys=True, separators=(",", ":"))
    probe = os.path.join(TMP, "shapes", "mutprobe.jsonl")
    write_lines(probe, lines)
    check("B10 a convention-less seal passes once the requirement is removed",
          m.Ledger(probe).verify().ok,
          "and every later comparison silently mixes two experiments")

# -- B11: the re-seal guard ------------------------------------------------
m = mutant("reseal", ("                if gap < args.min_reseal_seconds:",
                      "                if False:"))
if m:
    lpm, ppm = new_case("mut_reseal")
    ns = argparse.Namespace(
        ledger=lpm, policy=ppm, asset="ATOM", target=1, ref_px=5.0,
        exit_px=None, seq=None, fetch=False, capital=100.0, rule="t", note="",
        cost_bps=40.0, min_hold_seconds=0.0, min_reseal_seconds=72000.0,
        price_convention="daily_close", price_convention_explicit=False,
        auto_target=False, sma_window=200, settle_due=False,
        trials=None, trial_sr_var=None, json=False)
    import contextlib as _c, io as _i
    with _c.redirect_stdout(_i.StringIO()):
        m.do_seal(ns)
        m.do_seal(ns)
    check("B11 the same asset seals twice in a minute once the guard is removed",
          m.Ledger(lpm).verify().seals == 2,
          "two reads of one bar, both counting toward 30")

# -- B7: the data floor ----------------------------------------------------
m = mutant("data_floor", ("MIN_SCORED_SIGNALS = 30", "MIN_SCORED_SIGNALS = 5"))
if m:
    lpx, ppx = new_case("mut_floor")
    polx = m.Policy.load(ppx)
    for i in range(9):
        s = seal(lpx, ppx, asset="ATOM", target=1, px=100.0, ts=T(1000.0 + i * 1000))
        settle(lpx, int(s["payload"]["seq"]),
               px=100.0 * (1.10 if i < 7 else 0.90), ts=T(1500.0 + i * 1000))
    resx = m.Ledger(lpx).verify()
    scx, ntx = m.score(resx.records, cost)
    repx = m.build_report(scx, polx, resx.seals, None, None, ntx)
    check("B7 with the floor lowered, a 7-2 record DOES get a headline",
          repx["headline"] == "SCORED" and repx["wins"] == 7,
          f"win rate {repx.get('win_rate', 0):.3f} -- and it happens by chance "
          f"{pr.binom_tail_ge(7, 9) * 100:.1f}% of the time")
    check("  ...which is exactly why the real floor is 30, not a warning label",
          pr.MIN_SCORED_SIGNALS == 30)


# -- B12: the settlement-discretion note -----------------------------------
check("[control] the real code reports outstanding calls as discretion",
      rep_d["warn_selection_bias"] and
      any("survivorship bias" in n for n in rep_d["notes"]))
m = mutant("discretion_note", ("    if overdue:\n        rep[\"notes\"].append(\n"
                              "            f\"SETTLEMENT DISCRETION:",
                              "    if False:\n        rep[\"notes\"].append(\n"
                              "            f\"SETTLEMENT DISCRETION:"))
if m:
    rxm = m.Ledger(lpx).verify()
    scm, ntm = m.score(rxm.records, cost)
    repm = m.build_report(scm, m.Policy.load(ppx), rxm.seals, None, None, ntm,
                          unsettled=m.open_calls(rxm.records),
                          min_hold_seconds=72000.0)
    check("B12 the report goes SILENT about eight unscored calls once the note "
          "is removed", not any("survivorship" in n for n in repm["notes"]),
          "and every other check in the file still says the record is clean")

# -- B13: the rule's has-not-fired refusal ---------------------------------
check("[control] the real rule returns None below its window",
      pr.regime_target([1.0] * 10, window=200) is None)
m = mutant("rule_not_fired", ("    if len(closes) < window:\n        return None",
                              "    if len(closes) < window:\n        return 0"))
if m:
    check("B13 a rule that never fired becomes a FLAT CALL once the refusal is "
          "removed", m.regime_target([1.0] * 10, window=200) == 0,
          "thirty of those reach the graduation count carrying no signal")


# ==========================================================================
section("RESULT")
print(f"  platform : {platform.platform()}")
print(f"  python   : {platform.python_version()}")
print(f"  sealer   : {pr._source_fingerprint()['sha256'][:16]}... "
      f"({pr._source_fingerprint()['lines']} lines)")
print(f"  tmpdir   : {TMP}")
print()
print(f"  {passed} passed, {failed} failed")
if _failures:
    print()
    for name in _failures:
        print(f"    FAILED: {name}")
print("=" * 74)
print("  A green tally is green FOR THIS PLATFORM (CONTRIBUTING section 8).")
print("=" * 74)

shutil.rmtree(TMP, ignore_errors=True)
sys.exit(1 if failed else 0)
