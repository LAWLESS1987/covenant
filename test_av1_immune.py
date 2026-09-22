#!/usr/bin/env python3
"""test_av1_immune.py -- A218: the antivirus incorporated as an organ, and the
half it cannot do.

His words, 2026-09-21: "Incorporate the antvirus take it over and use it to
protect the entire system and improve on it."

The PowerShell layer is stubbed so these run anywhere and in milliseconds; two
checks read the REAL defence on this machine and say so. What is pinned is the
JUDGEMENT: that a posture is reported honestly including the parts that are
his to change, that a file is trusted only on evidence, and that "improve on
it" means the manifest question an antivirus structurally cannot answer.
LICENCE: public domain.
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__)) or "."
sys.path.insert(0, HERE)
import covenant_immune as IM                                          # noqa: E402

ok = []


def check(name, cond, note=""):
    ok.append(bool(cond))
    print("%s  %s%s" % ("ok  " if cond else "FAIL", name, ("  -- " + str(note)[:200]) if note and not cond else ""))


print("AV1 -- the defence, incorporated")
LEDGER = os.path.join(tempfile.mkdtemp(prefix="av1_"), "immune.jsonl")


def stub(payload, ok_=True):
    def _f(script, timeout=300):
        return ok_, payload
    return _f


# ---- posture: said plainly, including what is HIS
p = IM.posture(ps=stub({"RealTimeProtectionEnabled": True, "AMServiceEnabled": True,
                        "AntivirusSignatureAge": 0, "QuickScanAge": 3, "FullScanAge": IM.NEVER}))
check("AV1.1 posture reads the defence and reports a never-run full scan as never, not as a number",
      p["ok"] and p["realtime"] is True and p["full_scan_ever"] is False and "never run" in p["says"], p)
p_off = IM.posture(ps=stub({"RealTimeProtectionEnabled": False, "AMServiceEnabled": True,
                            "AntivirusSignatureAge": 9, "QuickScanAge": 40, "FullScanAge": 4}))
check("AV1.2 protection OFF is named as OFF and as HIS to change -- this module never turns a setting",
      p_off["realtime"] is False and "his setting to change, never this module's" in p_off["says"], p_off["says"])
check("AV1.3 a defence that cannot be read is said, never assumed healthy",
      IM.posture(ps=stub("access denied", ok_=False))["ok"] is False)

# ---- scan: the covenant's hand on the senses
f = os.path.join(tempfile.mkdtemp(prefix="av1s_"), "thing.bin")
open(f, "wb").write(b"x" * 32)
okk, says = IM.scan(f, ps=stub("scanned"))
check("AV1.4 the covenant can TELL the defence what to look at, and hears that it did", okk is True and "on demand" in says, says)
okk, says = IM.scan(f, ps=stub("Start-MpScan : denied", ok_=False))
check("AV1.5 broken the other way: a refused scan is reported as refused, never as clean", okk is False and "refused" in says, says)
okk, says = IM.scan(os.path.join(f, "nope"), ps=stub("scanned"))
check("AV1.6 a path that is not there is not 'scanned'", okk is False and "nothing at" in says, says)

# ---- vet: trust only on evidence
real_find, real_scan = IM.findings, IM.scan
try:
    IM.findings = lambda hours=24: {"ok": True, "total": 0, "settled": [], "needs_you": []}
    IM.scan = lambda path, timeout=900, ps=None: (True, "scanned on demand")
    v = IM.vet(f, ledger_path=LEDGER)
    check("AV1.7 a foreign file that scans clean is trusted, and the record says on what basis",
          v["trust"] is True and v["provenance"] == "foreign" and v["scanned"] is True, v)
    IM.scan = lambda path, timeout=900, ps=None: (False, "the scan was refused")
    v = IM.vet(f, ledger_path=LEDGER)
    check("AV1.8 broken the other way: a foreign file that could NOT be scanned is NOT trusted",
          v["trust"] is False and v["scanned"] is False, v)
    IM.scan = lambda path, timeout=900, ps=None: (True, "scanned on demand")
    calls = {"n": 0}

    def growing(hours=24):
        calls["n"] += 1
        return {"ok": True, "total": calls["n"] - 1, "settled": [],
                "needs_you": [] if calls["n"] == 1 else [{"path": f, "says": "NEEDS YOU"}]}

    IM.findings = growing
    v = IM.vet(f, ledger_path=LEDGER)
    check("AV1.9 broken the other way: if the scan RAISES something new, the file is not trusted",
          v["trust"] is False and v["new_unsettled_findings"] == 1, v)
finally:
    IM.findings, IM.scan = real_find, real_scan

rows = [json.loads(l) for l in open(LEDGER, encoding="utf-8") if l.strip()]
check("AV1.10 every vetting is on the record, with its verdict", len(rows) == 3 and all(r["kind"] == "vet" for r in rows))

# ---- the improvement: the question an antivirus cannot answer
t = IM.tree_integrity()
check("AV1.11 tree_integrity answers 'is this still the file we shipped' from the manifest, which no antivirus can",
      t["ok"] is True and "manifest" in t["says"], t)

# ---- the real defence on this machine, read-only
rp = IM.posture()
check("AV1.12 the REAL defence on this machine is readable and its real-time state is known",
      rp["ok"] is True and isinstance(rp["realtime"], bool), rp.get("says"))
rf = IM.findings(24)
check("AV1.13 the REAL detections are each judged, none left unclassified",
      rf["ok"] is True and rf["total"] == len(rf["settled"]) + len(rf["needs_you"]), rf)

print("\nnot measured here: watching a file as it EXECUTES. That is Defender's, it is why Defender stays, "
      "and nothing in this module pretends to replace it.")
print("\nAV1: %d/%d passed" % (sum(ok), len(ok)))
sys.exit(0 if all(ok) else 1)
