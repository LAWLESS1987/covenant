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
    led = os.path.join(d, "highway.jsonl")
    ls = os.path.join(d, "last_sense.json"); es = led + ".eligibility.json"      # where a pass with its own ledger keeps credit
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

# ---- I4: a pass given its own ledger writes no live credit (found 2026-11-22: H1's fixture "fixture_elsewhere"
# reached logs/eligibility_state.json through run_once). Run with COVENANT_ELIGIBILITY_STATE UNSET so the live default
# path is what would be written; the check compares that file before and after.
live = E.STATE
before = open(live, "rb").read() if os.path.exists(live) else None
d = tempfile.mkdtemp(prefix="a471_iso_")
ls = os.path.join(d, "last_sense.json"); led = os.path.join(d, "highway.jsonl"); open(led, "w").close()
with open(ls, "w", encoding="utf-8") as fh:
    json.dump({"at": round(time.time() - 60, 1), "conditions": {"a471_iso_fixture": "PRESENT"}}, fh)
saved_ls = os.environ.get("COVENANT_HIGHWAY_LAST_SENSE"); saved_es = os.environ.pop("COVENANT_ELIGIBILITY_STATE", None)
os.environ["COVENANT_HIGHWAY_LAST_SENSE"] = ls
import covenant_pause
_o = (H.sense, H.apply_remedy, H.grade_started, covenant_pause.paused)
try:
    H.sense = lambda **k: {"a471_iso_fixture": {"state": H.ABSENT, "measured": {}}}
    H.apply_remedy = lambda *a, **k: {"outcome": "dry run"}
    H.grade_started = lambda *a, **k: []
    covenant_pause.paused = lambda *a, **k: (False, "")
    H.run_once(dry_run=True, exclude=(), ledger=led)
finally:
    H.sense, H.apply_remedy, H.grade_started, covenant_pause.paused = _o
    os.environ.pop("COVENANT_HIGHWAY_LAST_SENSE", None)
    if saved_ls is not None: os.environ["COVENANT_HIGHWAY_LAST_SENSE"] = saved_ls
    if saved_es is not None: os.environ["COVENANT_ELIGIBILITY_STATE"] = saved_es
after = open(live, "rb").read() if os.path.exists(live) else None
beside = os.path.join(d, "highway.jsonl.eligibility.json")
check("I4 a pass with its own ledger leaves the live credit file untouched and keeps its credit beside that ledger",
      after == before and os.path.exists(beside) and "a471_iso_fixture" in open(beside, encoding="utf-8").read(),
      "live changed=%s beside=%s" % (after != before, os.path.exists(beside)))

# I5: the second route -- the module's LEDGER swapped (as H1 does), run_once called with NO ledger argument.
before = open(live, "rb").read() if os.path.exists(live) else None
d5 = tempfile.mkdtemp(prefix="a471_iso5_"); led5 = os.path.join(d5, "highway.jsonl"); open(led5, "w").close()
ls5 = os.path.join(d5, "last_sense.json")
with open(ls5, "w", encoding="utf-8") as fh:
    json.dump({"at": round(time.time() - 60, 1), "conditions": {"a471_iso5_fixture": "PRESENT"}}, fh)
_real_led = H.LEDGER; H.LEDGER = led5
saved_ls = os.environ.get("COVENANT_HIGHWAY_LAST_SENSE"); saved_es = os.environ.pop("COVENANT_ELIGIBILITY_STATE", None)
os.environ["COVENANT_HIGHWAY_LAST_SENSE"] = ls5
_o = (H.sense, H.apply_remedy, H.grade_started, covenant_pause.paused)
try:
    H.sense = lambda **k: {"a471_iso5_fixture": {"state": H.ABSENT, "measured": {}}}
    H.apply_remedy = lambda *a, **k: {"outcome": "dry run"}
    H.grade_started = lambda *a, **k: []
    covenant_pause.paused = lambda *a, **k: (False, "")
    H.run_once(dry_run=True, exclude=())
finally:
    H.sense, H.apply_remedy, H.grade_started, covenant_pause.paused = _o
    H.LEDGER = _real_led
    os.environ.pop("COVENANT_HIGHWAY_LAST_SENSE", None)
    if saved_ls is not None: os.environ["COVENANT_HIGHWAY_LAST_SENSE"] = saved_ls
    if saved_es is not None: os.environ["COVENANT_ELIGIBILITY_STATE"] = saved_es
after = open(live, "rb").read() if os.path.exists(live) else None
check("I5 the module's LEDGER swapped (H1's way), no ledger argument: the live credit file is still untouched",
      after == before and os.path.exists(led5 + ".eligibility.json"), "live changed=%s" % (after != before))

# ---- A472: the findings of Codex's audit, each verified on the A471 code before the fix
ALARM_ONLY = next(d for d in H.DETECTORS if d not in H.ALWAYS_APPLIES
                  and not any(d in r["for"] for r in H.REMEDIES.values()))


def run_det(det, prev_conditions, prev_age_s, credit=-0.9, raw_state=None):
    """run_once on one stand-in detector -> (alerts, infos, remedies called for it)."""
    d = tempfile.mkdtemp(prefix="a472_"); led = os.path.join(d, "highway.jsonl"); open(led, "w").close()
    ls = os.path.join(d, "last_sense.json")
    if prev_conditions is not None:
        with open(ls, "w", encoding="utf-8") as fh:
            json.dump({"at": round(time.time() - prev_age_s, 1), "conditions": prev_conditions}, fh)
    with open(led + ".eligibility.json", "w", encoding="utf-8") as fh:
        fh.write(raw_state if raw_state is not None else json.dumps(
            {"detectors": {det: {"credit": credit, "last_present_at": None, "real": 0, "persisted": 0, "self_cleared": 5}}}))
    saved = {k: os.environ.get(k) for k in ("COVENANT_HIGHWAY_LAST_SENSE", "COVENANT_ELIGIBILITY_OFF")}
    os.environ["COVENANT_HIGHWAY_LAST_SENSE"] = ls; os.environ.pop("COVENANT_ELIGIBILITY_OFF", None)
    called = []
    o = (H.sense, H.apply_remedy, H.grade_started, covenant_pause.paused)
    try:
        H.sense = lambda **k: {det: {"state": H.PRESENT, "measured": {"probe": 1}}}
        H.apply_remedy = lambda rname, c, name, **k: called.append(rname) or {"outcome": "dry run"}
        H.grade_started = lambda *a, **k: []
        covenant_pause.paused = lambda *a, **k: (False, "")
        al, inf = H.run_once(dry_run=True, exclude=(), ledger=led)
    finally:
        H.sense, H.apply_remedy, H.grade_started, covenant_pause.paused = o
        for k, v in saved.items():
            os.environ.pop(k, None)
            if v is not None:
                os.environ[k] = v
    return al, inf, called


al, inf, _ = run_det(ALARM_ONLY, {ALARM_ONLY: "ABSENT"}, 60)
check("J1 an alarm-only detector with low credit is never held: its ALERT is raised",
      any(ALARM_ONLY in a for a in al) and not any("A471" in i for i in inf), (al[:2], inf[:2]))
al, inf, called = run_det(DET, None, 0)
check("J2 no recorded previous pass: no hold, the remedies run (a hold cannot repeat on every pass)",
      len(called) >= 1 and not any("A471" in i for i in inf), (called, inf[:2]))
nh = next((d for d in E.NEVER_HOLD if any(d in r["for"] for r in H.REMEDIES.values())), None)
if nh:
    al, inf, called = run_det(nh, {nh: "ABSENT"}, 60)
    check("J3 a security detector (%s) is never held, whatever its credit" % nh, len(called) >= 1 and not any("A471" in i for i in inf), called)
al, inf, called = run_det(DET, {DET: "ABSENT"}, -3600)
check("J4 a future-dated previous pass is ignored: no hold", len(called) >= 1 and not any("A471" in i for i in inf), (called, inf[:2]))
al, inf, called = run_det(DET, {DET: "ABSENT"}, 60, raw_state=json.dumps({"detectors": {DET: {"credit": "-1", "self_cleared": 9}}}))
check("J5 a malformed credit (a string) is dropped, not trusted: no hold", len(called) >= 1, called)
al, inf, called = run_det(DET, {DET: "ABSENT"}, 60)
check("J6 control: the same detector with real low credit and a fresh PRESENT IS held, with its measurement in the line",
      called == [] and any("A471" in i and "probe" in i for i in inf), (called, inf[:2]))
_d = tempfile.mkdtemp(prefix="a472_save_"); _p = os.path.join(_d, "s.json")
E.save({"detectors": {"x": {"credit": 0.1}}}, _p)
check("J7 save leaves no temp file behind and the state reads back", sorted(os.listdir(_d)) == ["s.json"]
      and E.load(_p)["detectors"]["x"]["credit"] == 0.1, os.listdir(_d))

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
