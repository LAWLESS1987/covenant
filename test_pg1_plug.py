#!/usr/bin/env python3
"""test_pg1_plug.py -- PG1: the plug an external AI runs (covenant_plug.py) is SENSE/REPORT/PROPOSE,
and its two act-gates hold BOTH WAYS.

Every guard here is driven red as well as green (CLAUDE.md rule 8): the kill switch silences the
spiking readout and clearing it restores it; may_act() refuses a paused highway and a non-production
tree and allows neither-of-those; heal(act=True) outside the production tree does NOT call the real
repair (it is downgraded to a dry run); and the plug's readable NEVER_AUTOMATIC copy is the live
tuple, never a narrowed one. No real repair is ever run -- covenant_heal.heal is stubbed to record
the dry_run it was handed, so the test proves the gate without touching the live tree.
LICENCE: public domain.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import covenant_plug as P            # noqa: E402
import covenant_highway as HW        # noqa: E402
import covenant_pause as PAUSE       # noqa: E402
import covenant_heal as HEAL         # noqa: E402
import covenant_watchdog as WD       # noqa: E402

KILL = "COVENANT_VERDICT_CACHE_OFF"
checks = []


def ok(name, cond, detail=""):
    checks.append((name, bool(cond), detail))


def _clear_kill():
    os.environ.pop(KILL, None)


# --- 1/2. kill switch silences the spiking readout, both ways ------------------------------------
_clear_kill()
s_on = P.spine()
ok("spine_runs_when_enabled", s_on.get("octopus") and "witness" in s_on["octopus"],
   "octopus=%r" % s_on.get("octopus"))
ok("kill_switch_reported_off", s_on.get("kill_switch") is False, "kill_switch=%r" % s_on.get("kill_switch"))

os.environ[KILL] = "1"
try:
    s_off = P.spine()
finally:
    _clear_kill()
ok("kill_switch_silences_octopus", s_off.get("octopus") == {}, "octopus=%r" % s_off.get("octopus"))
ok("kill_switch_reported_on", s_off.get("kill_switch") is True, "kill_switch=%r" % s_off.get("kill_switch"))

s_back = P.spine()
ok("clearing_kill_restores_octopus", bool(s_back.get("octopus")), "octopus=%r" % s_back.get("octopus"))

# --- 3/4. the plug never narrows NEVER_AUTOMATIC; the readable copy is the live tuple ------------
live = tuple(HW.NEVER_AUTOMATIC)
ok("never_automatic_is_live", P._never_automatic() == live and len(live) > 0, "live=%r" % (live,))
ok("never_automatic_doc_matches_live", P._NEVER_AUTOMATIC_DOC == live,
   "doc=%r" % (P._NEVER_AUTOMATIC_DOC,))

# --- 5. may_act() refuses a PAUSED highway (on a temp switch, never the live one) ----------------
tmp_pause = tempfile.mkdtemp(prefix="pg1_pause_")
old_pause_dir = os.environ.get("COVENANT_PAUSE_DIR")
os.environ["COVENANT_PAUSE_DIR"] = tmp_pause
# covenant_pause read PAUSE_DIR at import; point its module-level at the temp dir for this check.
_saved_pause_dir = PAUSE.PAUSE_DIR
PAUSE.PAUSE_DIR = tmp_pause
try:
    PAUSE.pause("highway", "PG1 test")
    allowed_paused, why_paused = P.may_act()
    ok("may_act_refuses_paused", (not allowed_paused) and "pause" in why_paused.lower(),
       "allowed=%r why=%r" % (allowed_paused, why_paused))
    PAUSE.resume("highway")
finally:
    PAUSE.PAUSE_DIR = _saved_pause_dir
    if old_pause_dir is None:
        os.environ.pop("COVENANT_PAUSE_DIR", None)
    else:
        os.environ["COVENANT_PAUSE_DIR"] = old_pause_dir

# --- 6/7/8/9. the production-tree gate, and heal() honoring it, both ways ------------------------
# Stub the real repair so NOTHING is repaired; record the dry_run it was handed.
_saved_heal = HEAL.heal
_saved_may = WD.highway_may_act
_calls = []


def _stub_heal(dry_run=False, who="", **kw):
    _calls.append(dry_run)
    return {"ok": True, "fixed": [], "still_needs_a_person": [], "dry_run": bool(dry_run), "who": who}


try:
    HEAL.heal = _stub_heal

    # not the production tree -> heal(act=True) must NOT act; it previews and says it refused.
    WD.highway_may_act = lambda: False
    allowed_nonprod, why_nonprod = P.may_act()
    ok("may_act_refuses_non_production", (not allowed_nonprod) and "production" in why_nonprod.lower(),
       "allowed=%r why=%r" % (allowed_nonprod, why_nonprod))
    _calls.clear()
    r_ref = P.heal(act=True)
    ok("heal_outside_production_does_not_act",
       (r_ref.get("acted") is False) and _calls == [True] and r_ref.get("gate", "").startswith("REFUSED"),
       "acted=%r calls=%r gate=%r" % (r_ref.get("acted"), _calls, r_ref.get("gate")))

    # the production tree, not paused -> heal(act=True) acts for real (here: the stub, dry_run False).
    WD.highway_may_act = lambda: True
    allowed_prod, _ = P.may_act()
    ok("may_act_allows_production_unpaused", allowed_prod is True, "allowed=%r" % allowed_prod)
    _calls.clear()
    r_act = P.heal(act=True)
    ok("heal_in_production_acts", (r_act.get("acted") is True) and _calls == [False],
       "acted=%r calls=%r" % (r_act.get("acted"), _calls))

    # preview never acts, whatever the gate says.
    _calls.clear()
    r_prev = P.heal(act=False)
    ok("heal_preview_never_acts", (r_prev.get("acted") is False) and _calls == [True],
       "acted=%r calls=%r" % (r_prev.get("acted"), _calls))
finally:
    HEAL.heal = _saved_heal
    WD.highway_may_act = _saved_may

# --- 10. the spine path imports NO heavy deps (phone-safe), proven in a clean subprocess ---------
code = ("import sys; sys.path.insert(0, %r); import covenant_plug as p; p.spine(); "
        "bad=[m for m in ('numpy','torch','snntorch','brian2') if m in sys.modules]; "
        "print('HEAVY:' + ','.join(bad))" % HERE)
proc = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, cwd=HERE)
heavy_line = [ln for ln in (proc.stdout or "").splitlines() if ln.startswith("HEAVY:")]
ok("spine_is_stdlib_only", heavy_line == ["HEAVY:"], "stdout=%r stderr=%r" % (proc.stdout[-200:], proc.stderr[-200:]))

# ------------------------------------------------------------------------------------- tally
passed = sum(1 for _n, c, _d in checks if c)
total = len(checks)
for name, c, detail in checks:
    if not c:
        print("  FAIL %s -- %s" % (name, detail))
print("PG1 %d/%d passed" % (passed, total))
sys.exit(0 if passed == total else 1)
