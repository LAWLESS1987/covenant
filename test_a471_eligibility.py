#!/usr/bin/env python3
"""test_a471_eligibility.py -- A471: detectors earn credit from outcomes; one whose alarms keep clearing by themselves
waits one pass before its remedies run. Every check runs the code; none greps it. No real remedy runs: apply_remedy
is replaced by a recorder, sense() by stand-in readings, the pause by "not paused", and every path is a temp file.

  E1  three self-cleared alarms drive credit to <= -0.5, and a fresh PRESENT is then held
  E2  the same detector PRESENT on two passes running is NOT held (it persisted: act now)
  E3  an alarm a remedy of its own fixed raises credit; no hold
  E4  a takeover guard (ALWAYS_APPLIES) is never held, whatever its credit
  E5  the kill switch COVENANT_ELIGIBILITY_OFF: no credit update and no hold
  E6  credit above -0.5: no hold
  E7  recent_rows reads only the tail and skips a cut first line
  I1  through covenant_highway.run_once: a low-credit detector's fresh PRESENT -> its remedies are NOT called, the
      reading is still in the pass's infos with an A471 line
  I2  through run_once: the same detector PRESENT on the last pass too -> its remedies ARE called
  I3  through run_once with the kill switch: its remedies ARE called
  M1  mutation: run_once's hold check removed -> I1's remedies are called (the hold is what stops them)
  M2  mutation: hold() without the persisted exception -> I2's remedies are NOT called
"""
import json
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.pop("COVENANT_ELIGIBILITY_OFF", None)
import covenant_eligibility as E      # noqa: E402
import covenant_highway as H          # noqa: E402

results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print("%s  %s%s" % ("ok  " if ok else "FAIL", label, "" if ok else "  -- " + str(detail)[:200]), flush=True)


P, A = E.PRESENT, E.ABSENT
now = 1_800_000_000.0

# ---- unit checks
st = {"detectors": {}}
for i in range(3):                                   # three alarms that cleared with nothing of their own having run
    E.observe({"x": A}, {"x": {"state": P}}, [], st, now=now + 600 * i * 2)
    E.observe({"x": P}, {"x": {"state": A}}, [], st, now=now + 600 * (i * 2 + 1), prev_at=now + 600 * i * 2)
c = st["detectors"]["x"]["credit"]
check("E1 three self-cleared alarms -> credit <= -0.5 and a fresh PRESENT is held",
      c <= -0.5 and E.hold("x", {"x": A}, st) is not None, c)
check("E2 PRESENT on the last pass too -> not held", E.hold("x", {"x": P}, st) is None)
st2 = {"detectors": {}}
E.observe({"y": A}, {"y": {"state": P}}, [], st2, now=now)
E.observe({"y": P}, {"y": {"state": A}}, [{"detector": "y", "outcome": "fixed", "at": now + 10}], st2, now=now + 60, prev_at=now)
check("E3 a remedy of its own fixed it -> credit up, no hold",
      st2["detectors"]["y"]["credit"] > 0 and E.hold("y", {"y": A}, st2) is None, st2["detectors"]["y"])
st3 = {"detectors": {"head_commitment_broken": {"credit": -1.0, "self_cleared": 9}}}
check("E4 a takeover guard is never held", E.hold("head_commitment_broken", {}, st3, exempt=H.ALWAYS_APPLIES) is None)
os.environ["COVENANT_ELIGIBILITY_OFF"] = "1"
st4 = {"detectors": {}}
upd = E.observe({"z": P}, {"z": {"state": A}}, [], st4, now=now)
check("E5 kill switch: no update and no hold", upd == [] and st4 == {"detectors": {}} and E.hold("x", {"x": A}, st) is None)
os.environ.pop("COVENANT_ELIGIBILITY_OFF")
check("E6 credit above -0.5 -> no hold", E.hold("q", {}, {"detectors": {"q": {"credit": -0.4}}}) is None)
tmpd = tempfile.mkdtemp(prefix="a471_")
lp = os.path.join(tmpd, "ledger.jsonl")
with open(lp, "w", encoding="utf-8") as fh:
    for i in range(3000):
        fh.write(json.dumps({"detector": "d", "outcome": "fixed", "at": i, "pad": "x" * 100}) + "\n")
rows = E.recent_rows(lp, tail_bytes=4096)
check("E7 recent_rows: the tail only, whole rows", 0 < len(rows) < 100 and rows[-1]["at"] == 2999 and all("detector" in r for r in rows), len(rows))

# ---- through run_once
DET = next(d for r in H.REMEDIES.values() for d in r["for"] if d not in H.ALWAYS_APPLIES)


def run_pass(prev_state, kill=False, mutate=None):
    """One run_once with stand-ins. -> (remedies called for DET, infos)."""
    d = tempfile.mkdtemp(prefix="a471_run_")
    ls = os.path.join(d, "last_sense.json"); es = os.path.join(d, "elig.json"); led = os.path.join(d, "highway.jsonl")
    with open(ls, "w", encoding="utf-8") as fh:
        json.dump({"at": round(time.time() - 60, 1), "conditions": {DET: prev_state}}, fh)
    with open(es, "w", encoding="utf-8") as fh:
        json.dump({"detectors": {DET: {"credit": -0.9, "last_present_at": None, "real": 0, "persisted": 0, "self_cleared": 4}}}, fh)
    open(led, "w").close()
    env = {"COVENANT_HIGHWAY_LAST_SENSE": ls, "COVENANT_ELIGIBILITY_STATE": es}
    if kill:
        env["COVENANT_ELIGIBILITY_OFF"] = "1"
    saved = {k: os.environ.get(k) for k in list(env) + ["COVENANT_ELIGIBILITY_OFF"]}
    os.environ.update(env)
    called = []
    orig = (H.sense, H.apply_remedy, H.grade_started, E.hold)
    import covenant_pause
    orig_pause = covenant_pause.paused
    try:
        H.sense = lambda **k: {DET: {"state": H.PRESENT, "measured": {}}}
        H.apply_remedy = lambda rname, c, name, **k: called.append((rname, name)) or {"outcome": "dry run"}
        H.grade_started = lambda *a, **k: []
        covenant_pause.paused = lambda *a, **k: (False, "")
        if mutate:
            mutate()
        _, infos = H.run_once(dry_run=True, exclude=(), ledger=led)
    finally:
        H.sense, H.apply_remedy, H.grade_started, E.hold = orig
        covenant_pause.paused = orig_pause
        for k, v in saved.items():
            os.environ.pop(k, None)
            if v is not None:
                os.environ[k] = v
    return [c for c in called if c[1] == DET], infos


calls, infos = run_pass(H.ABSENT)
check("I1 run_once: a low-credit detector's fresh PRESENT -> remedies not called, the reading still reported (A471 line)",
      calls == [] and any(DET in i and "A471" in i for i in infos), (calls, infos[:3]))
calls, _ = run_pass(H.PRESENT)
check("I2 run_once: PRESENT on the last pass too -> remedies called", len(calls) >= 1, calls)
calls, _ = run_pass(H.ABSENT, kill=True)
check("I3 run_once with the kill switch -> remedies called", len(calls) >= 1, calls)

# ---- mutations of the real behaviour
calls, _ = run_pass(H.ABSENT, mutate=lambda: setattr(E, "hold", lambda *a, **k: None))
check("M1 the hold removed -> I1's remedies are called (the hold is what stops them)", len(calls) >= 1, calls)


def no_persist_exception():
    real = E.hold
    E.hold = lambda name, prev, state, exempt=(): real(name, {}, state, exempt)   # forget the last pass
calls, _ = run_pass(H.PRESENT, mutate=no_persist_exception)
check("M2 without the persisted exception -> I2's remedies are NOT called", calls == [], calls)

print("\nA471: %d/%d passed" % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)
