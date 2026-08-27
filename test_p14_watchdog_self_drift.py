#!/usr/bin/env python3
"""P14 (2026-08-24): the watchdog can detect that IT is the stale one.

Pure functions only -- no node, no socket, no mining, no key. Every check here
runs in-process in under a second on any platform (M29: run it on Windows too,
that is where the node runs).

  A  self_drift_report is a pure comparison of two hashes and never raises.
  B  The alert text is STABLE while the condition holds, so Adaptation says it
     once and then CLEARs it, rather than re-firing every round (M34).
  C  It is DISCLOSURE: it cannot restart, refuse or change anything.
  D  The wiring: SELF_SOURCE_SHA12 is captured at import and is the hash of the
     file this process actually loaded.
  E  THE PRE-FIX RECORD: what the 08-23 01:39 watchdog process could not say.
"""
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import covenant_watchdog as wd  # noqa: E402

PASS = FAIL = 0


def check(label, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS: {label}" + (f" -- {detail}" if detail else ""))
    else:
        FAIL += 1
        print(f"  FAIL: {label}" + (f" -- {detail}" if detail else ""))


print("== A. the comparison itself ==")
a, i = wd.self_drift_report("aaaaaaaaaaaa", "aaaaaaaaaaaa")
check("A1 same hash -> silence", a == [] and i == [])

a, i = wd.self_drift_report("aaaaaaaaaaaa", "bbbbbbbbbbbb")
check("A2 different hash -> exactly one alert", len(a) == 1 and i == [])
check("A2b the alert names BOTH hashes",
      "aaaaaaaaaaaa" in a[0] and "bbbbbbbbbbbb" in a[0], a[0][:70])
check("A2c and says which one is running",
      "loaded aaaaaaaaaaaa" in a[0] and "on disk is bbbbbbbbbbbb" in a[0])
check("A2d and says the reports before it came from the older source",
      "produced by the older source" in a[0])

for loaded, disk in ((None, "b" * 12), ("a" * 12, None), (None, None)):
    a, i = wd.self_drift_report(loaded, disk)
    check(f"A3 unhashable ({loaded}, {disk}) is an INFO, never an alert",
          a == [] and len(i) == 1, str(i)[:60])
check("A3b and it says so rather than implying agreement",
      "unverified" in wd.self_drift_report(None, None)[1][0])

for bad in (0, "", [], {}, 3.4, object()):
    try:
        a, i = wd.self_drift_report(bad, "b" * 12)
        ok = isinstance(a, list) and isinstance(i, list)
    except Exception as e:
        ok = False
        a = f"RAISED {type(e).__name__}"
    check(f"A4 self_drift_report({bad!r}) never raises", ok, str(a)[:50])

print("\n== B. stable text, so Adaptation can silence it ==")
one = wd.self_drift_report("a" * 12, "b" * 12)[0][0]
two = wd.self_drift_report("a" * 12, "b" * 12)[0][0]
check("B1 the same drift produces byte-identical text", one == two)
ad = wd.Adaptation(roll_up_every=30)
key = f"alert:{one[:80]}"
emitted = [ad.observe(key, one) for _ in range(29)]
check("B2 Adaptation emits it once and then stays silent",
      emitted[0] == one and all(e is None for e in emitted[1:]),
      f"{sum(e is not None for e in emitted)} of 29 rounds emitted")
check("B3 and it CLEARs when the condition goes away",
      ad.sweep(set())[0].startswith("CLEARED after 29 round(s):"))

print("\n== C. disclosure only ==")
src = open(wd.SELF_SRC, encoding="utf-8").read()
body = src[src.index("def self_drift_report"):src.index("# ---", src.index("def self_drift_report"))]
for forbidden in ("start_node", "Popen", "taskkill", "os.remove", "sys.exit", "raise "):
    check(f"C1 self_drift_report does not {forbidden}", forbidden not in body)
check("C2 it returns text and nothing else",
      isinstance(wd.self_drift_report("a" * 12, "b" * 12), tuple))

print("\n== D. the wiring ==")
check("D1 SELF_SRC points at this watchdog file",
      os.path.basename(wd.SELF_SRC) == "covenant_watchdog.py")
check("D2 SELF_SOURCE_SHA12 was captured at import", wd.SELF_SOURCE_SHA12 is not None)
on_disk = hashlib.sha256(open(wd.SELF_SRC, "rb").read()).hexdigest()[:12]
check("D3 and it equals the file on disk right now (nothing has shipped since)",
      wd.SELF_SOURCE_SHA12 == on_disk, f"{wd.SELF_SOURCE_SHA12} vs {on_disk}")
check("D4 disk_source_sha12 of a missing file is None, not a crash",
      wd.disk_source_sha12(os.path.join(os.path.dirname(wd.SELF_SRC), "no-such-file.py")) is None)
check("D5 the node's drift check is still there and separate",
      callable(wd.source_drift_report) and callable(wd.self_drift_report))

print("\n== E. PRE-FIX RECORD: what the 08-23 01:39 process could not say ==")
check("E1 a pre-P14 watchdog has no self check at all",
      not hasattr(wd, "_pre_p14_marker"), "the 01:39 process had neither this nor Adaptation")
check("E2 Adaptation exists to be the reason this alert is bearable",
      hasattr(wd, "Adaptation"))
check("E3 and the node-side drift check it complements exists",
      "restart to pick " in "".join(wd.source_drift_report({"A": {"source_sha256": "x" * 12}}, "y" * 12)[0]))

print(f"\n{PASS}/{PASS + FAIL} passed")
sys.exit(0 if FAIL == 0 else 1)
