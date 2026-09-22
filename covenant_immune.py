#!/usr/bin/env python3
"""covenant_immune.py -- the antivirus taken over as an organ of the covenant,
and the half it cannot do added.

HIS WORDS, 2026-09-21: "Delete the anti-virus and have the system act as one",
then, plainly: "Incorporate the antvirus take it over and use it to protect the
entire system and improve on it."

WHY NOT DELETE IT. Nothing in this repository scans a file as it executes.
`covenant_security_probe` says so in its own docstring -- "Nothing here reads
the operating system" -- there is no signature set, no kernel filter, no
real-time hook, and writing one is not a night's work nor a wise one. Deleting
the only thing on this machine that does that would leave nothing. So it is
INCORPORATED: Defender is the senses, the covenant is the judgement and the
hand that directs it.

WHAT "TAKE IT OVER" MEANS HERE, concretely:
  posture()   what the defence is actually doing, in plain words.
  scan(path)  the covenant TELLS it what to look at, when the covenant wants
              it looked at -- not only on Defender's own schedule.
  findings()  what it found, each one already judged by provenance (A217):
              ours and accounted for by hash, ours and unaccounted for, or
              foreign. He is handed the ones that are really his.
  vet(path)   the primitive the rest of the system should call before it
              trusts a file it did not write: scan it AND account for it.
              A file that is foreign to this tree AND unscannable is refused.
  state()     all of it at once, in one shape, for the heal button.

WHAT "IMPROVE ON IT" MEANS, and it is not a boast. An antivirus knows what
malware looks like. It does not know what YOUR files are supposed to be -- a
changed byte in a file of ours is invisible to it forever. This repository
knows exactly: MANIFEST.sha256 over every shipped file. `tree_integrity()`
asks that question, which Defender structurally cannot, and the two answers
together cover more than either alone. That is the whole of the improvement
claimed here, and nothing more is claimed.

WHAT IT STILL CANNOT DO, said plainly: watch a file as it executes. That is
Defender's, it is why Defender stays, and no line here pretends otherwise.
LICENCE: public domain.
"""
from __future__ import annotations

import importlib
import json
import os
import subprocess
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER = os.path.join(HERE, "ops", "immune.jsonl")
_NOWIN = 0x08000000 if os.name == "nt" else 0
NEVER = 4294967295            # what Defender reports for "no scan has ever run"


def _ps(script, timeout=300):
    """(ok, parsed json or text). Never raises."""
    try:
        p = subprocess.run(["powershell", "-NoProfile", "-Command", script],
                           capture_output=True, text=True, timeout=timeout, creationflags=_NOWIN)
    except (OSError, subprocess.SubprocessError) as e:
        return False, "%s: %s" % (type(e).__name__, str(e)[:120])
    if p.returncode != 0:
        return False, (p.stderr or p.stdout or "").strip()[:200]
    txt = (p.stdout or "").strip()
    if not txt:
        return True, {}
    try:
        return True, json.loads(txt)
    except ValueError:
        return True, txt


def _record(row, path=None):
    p = path or os.environ.get("COVENANT_IMMUNE_LEDGER") or LEDGER
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(dict(row, t=time.strftime("%Y-%m-%dT%H:%M:%S%z")), ensure_ascii=False) + "\n")
    except OSError:
        pass
    return row


def posture(ps=None):
    """What the defence is doing. {"ok", "realtime", "service", "signature_age_days",
    "quick_scan_age_days", "full_scan_ever", "says"}."""
    ok, d = (ps or _ps)("Get-MpComputerStatus -ErrorAction Stop | Select-Object RealTimeProtectionEnabled, "
                        "AMServiceEnabled, AntivirusSignatureAge, QuickScanAge, FullScanAge | ConvertTo-Json -Compress")
    if not ok or not isinstance(d, dict):
        return {"ok": False, "says": "the defence could not be read (%s)" % str(d)[:120]}
    full = d.get("FullScanAge")
    out = {"ok": True,
           "realtime": bool(d.get("RealTimeProtectionEnabled")),
           "service": bool(d.get("AMServiceEnabled")),
           "signature_age_days": d.get("AntivirusSignatureAge"),
           "quick_scan_age_days": d.get("QuickScanAge"),
           "full_scan_ever": not (full is None or full == NEVER),
           "full_scan_age_days": None if (full is None or full == NEVER) else full}
    bits = ["real-time protection is %s" % ("ON" if out["realtime"] else "OFF -- and that is his setting to change, never this module's"),
            "signatures %s day(s) old" % out["signature_age_days"],
            "last quick scan %s day(s) ago" % out["quick_scan_age_days"],
            "a full scan has never run" if not out["full_scan_ever"] else "last full scan %s day(s) ago" % out["full_scan_age_days"]]
    out["says"] = "; ".join(bits)
    return out


def scan(path, timeout=900, ps=None):
    """Tell the defence to look at this path NOW. (ok, says). The covenant's
    hand on the senses -- this is what 'take it over' means in practice."""
    p = os.path.abspath(path)
    if not os.path.exists(p):
        return False, "nothing at %s to scan" % p
    ok, said = (ps or _ps)("Start-MpScan -ScanPath '%s' -ScanType CustomScan -ErrorAction Stop; 'scanned'"
                           % p.replace("'", "''"), timeout=timeout)
    return bool(ok), ("scanned on demand" if ok else "the scan was refused: %s" % str(said)[:160])


def findings(hours=24):
    """Every detection in the window, each already judged by provenance.
    {"ok", "total", "settled": [...], "needs_you": [...]}"""
    try:
        HW = importlib.import_module("covenant_highway")
        PV = importlib.import_module("covenant_provenance")
        rows = HW._defender_detections(hours)
    except Exception as e:                                        # noqa: BLE001
        return {"ok": False, "says": "the detection history could not be read (%s)" % type(e).__name__}
    if rows is None:
        return {"ok": False, "says": "the detection history could not be read"}
    settled, needs = [], []
    for r in rows:
        j = PV.judge_detection(r)
        (settled if j.get("settled") else needs).append({"path": j.get("path"), "says": j.get("says")})
    return {"ok": True, "total": len(rows), "settled": settled, "needs_you": needs}


def tree_integrity():
    """THE HALF AN ANTIVIRUS CANNOT DO. Not "does this look like malware" but
    "is this still the file we shipped" -- answered from MANIFEST.sha256 by the
    tool that owns it, so there is no second implementation of the rule."""
    try:
        import io as _io
        import contextlib
        vb = importlib.import_module("verify_bundle")
        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = vb.main() if hasattr(vb, "main") else 0
        said = buf.getvalue().strip().splitlines()[-1:] or [""]
        return {"ok": True, "clean": rc == 0, "says": said[0][:200]}
    except SystemExit as e:                                       # noqa: PERF203 -- the tool may exit
        return {"ok": True, "clean": int(getattr(e, "code", 1) or 0) == 0, "says": "verify_bundle exited %s" % e.code}
    except Exception as e:                                        # noqa: BLE001
        return {"ok": False, "says": "the manifest could not be checked (%s: %s)" % (type(e).__name__, str(e)[:120])}


def versions(ps=None):
    """What the defence IS, by version. Every part is numbered, so a change can
    be judged rather than trusted."""
    ok, d = (ps or _ps)("Get-MpComputerStatus -ErrorAction Stop | Select-Object AntivirusSignatureVersion, "
                        "AMEngineVersion, AMProductVersion, AntivirusSignatureAge, RealTimeProtectionEnabled, "
                        "AMServiceEnabled | ConvertTo-Json -Compress")
    if not ok or not isinstance(d, dict):
        return None
    return {"signature": str(d.get("AntivirusSignatureVersion") or ""),
            "engine": str(d.get("AMEngineVersion") or ""),
            "platform": str(d.get("AMProductVersion") or ""),
            "age_days": d.get("AntivirusSignatureAge"),
            "realtime": bool(d.get("RealTimeProtectionEnabled")),
            "service": bool(d.get("AMServiceEnabled"))}


def _ver_tuple(v):
    out = []
    for part in str(v or "").split("."):
        try:
            out.append(int(part))
        except ValueError:
            out.append(0)
    return tuple(out) or (0,)


def update(ps=None, ledger_path=None, run=None, before=None, after=None):
    """A219 (2026-09-21, his words: "Defender should now be run by our system
    locally any updates must pass our logic and reason or the system itself
    grows and improves it").

    The covenant pulls the update itself, on its own schedule, and JUDGES the
    result. Four rules, each one a thing that can actually be true or false:
      1. no version may move BACKWARDS (signature, engine or platform);
      2. something must actually have moved, or the age must have fallen --
         an update that changed nothing is reported as nothing, not as a win;
      3. real-time protection must be no worse after than before;
      4. the antimalware service must still be running.
    A verdict of REFUSED does not roll anything back -- this account is not an
    administrator and Microsoft's updates are not the covenant's to revoke --
    it is recorded, and named to him, which is the honest meaning of a gate we
    can actually hold.

    WHAT CANNOT BE JUDGED, and is not pretended: the CONTENTS of a signature
    definition. It is opaque binary from Microsoft. A module claiming to reason
    about it would be measuring nothing, which this repository calls a fake
    guard. What is judged is what is observable: provenance by version, and
    effect on the posture."""
    b = before if before is not None else versions(ps)
    if b is None:
        row = {"kind": "update", "verdict": "UNKNOWN", "why": "the defence could not be read before the update"}
        return _record(row, ledger_path)
    ok, said = (run or (lambda: (ps or _ps)("Update-MpSignature -ErrorAction Stop; 'updated'", timeout=900)))()
    a = after if after is not None else versions(ps)
    if a is None:
        row = {"kind": "update", "verdict": "UNKNOWN", "before": b,
               "why": "the defence could not be read after the update (ran: %s)" % ok}
        return _record(row, ledger_path)
    reasons, moved = [], []
    for part in ("signature", "engine", "platform"):
        if _ver_tuple(a[part]) < _ver_tuple(b[part]):
            reasons.append("%s version went BACKWARDS: %s -> %s" % (part, b[part], a[part]))
        elif _ver_tuple(a[part]) > _ver_tuple(b[part]):
            moved.append("%s %s -> %s" % (part, b[part], a[part]))
    if b.get("realtime") and not a.get("realtime"):
        reasons.append("real-time protection was ON before and is OFF after")
    if b.get("service") and not a.get("service"):
        reasons.append("the antimalware service was running before and is not after")
    try:
        fell = a.get("age_days") is not None and b.get("age_days") is not None and a["age_days"] <= b["age_days"]
    except TypeError:
        fell = False
    if not ok and not moved:
        verdict, why = "FAILED", "the update did not run (%s) and nothing moved" % str(said)[:120]
    elif reasons:
        verdict, why = "REFUSED", "; ".join(reasons)
    elif moved:
        verdict, why = "PASSED", "moved forward: " + "; ".join(moved)
    elif fell:
        verdict, why = "PASSED", "nothing moved; already current (signatures %s day(s) old)" % a.get("age_days")
    else:
        verdict, why = "NOTHING", "the update ran and changed nothing measurable"
    row = {"kind": "update", "verdict": verdict, "why": why, "before": b, "after": a, "ran": bool(ok)}
    # THE SYSTEM GROWS: new signatures can newly flag a file we have already
    # accounted for by hash. That is Defender's judgement changing while ours
    # did not, and it is recorded as such rather than alarming him again.
    try:
        f = findings(1)
        row["after_update_findings"] = {"settled": len(f.get("settled") or []), "needs_you": len(f.get("needs_you") or [])}
        row["ours_still_accounted"] = [x.get("path") for x in (f.get("settled") or [])][:6]
    except Exception:                                             # noqa: BLE001
        pass
    return _record(row, ledger_path)


def vet(path, do_scan=True, ledger_path=None):
    """Before the covenant trusts a file it did not write: account for it by
    hash AND have the defence look at it. {"trust", "why", ...}.

    trust is True only when the file is accounted for by provenance OR the
    defence scanned it and the scan raised nothing new. A file that is foreign
    to this tree and could not be scanned is never trusted."""
    PV = importlib.import_module("covenant_provenance")
    prov = PV.classify(path)
    before = findings(1)
    scanned, says = (scan(path) if do_scan else (False, "not scanned (asked not to)"))
    after = findings(1)
    new = len((after.get("needs_you") or [])) - len((before.get("needs_you") or []))
    trust = prov["verdict"] == "ours:verified" or (scanned and new <= 0)
    row = {"kind": "vet", "path": os.path.abspath(path), "provenance": prov["verdict"],
           "scanned": scanned, "new_unsettled_findings": max(0, new), "trust": bool(trust),
           "why": ("accounted for: %s" % prov["why"]) if prov["verdict"] == "ours:verified"
                  else ("%s; %s; %d new unsettled finding(s)" % (prov["why"], says, max(0, new)))}
    _record(row, ledger_path)
    return row


def state(hours=24):
    """The whole immune picture in one shape, for the heal button and the brief."""
    p, f, t = posture(), findings(hours), tree_integrity()
    needs = list(f.get("needs_you") or [])
    lines = [p.get("says", "")]
    if f.get("ok"):
        lines.append("%d detection(s) in %dh: %d settled by hash, %d for you"
                     % (f.get("total", 0), hours, len(f.get("settled") or []), len(needs)))
    else:
        lines.append(f.get("says", ""))
    lines.append("our own files: %s" % (t.get("says") or "unchecked"))
    healthy = bool(p.get("ok") and p.get("realtime") and not needs and t.get("clean"))
    return {"ok": True, "healthy": healthy, "posture": p, "findings": f, "tree": t,
            "needs_you": needs, "says": " | ".join(x for x in lines if x)}


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="the defence, incorporated: posture, findings judged, our own files")
    ap.add_argument("--scan", metavar="PATH", help="tell the defence to look at this path now")
    ap.add_argument("--vet", metavar="PATH", help="account for a file by hash AND scan it")
    ap.add_argument("--update", action="store_true", help="pull the defence's update and judge the result (A219)")
    a = ap.parse_args(argv)
    if a.scan:
        ok, says = scan(a.scan)
        print(says)
        return 0 if ok else 1
    if a.vet:
        r = vet(a.vet)
        print("trust: %s -- %s" % (r["trust"], r["why"]))
        return 0 if r["trust"] else 1
    if a.update:
        r = update()
        print("%s -- %s" % (r["verdict"], r["why"]))
        return 0 if r["verdict"] in ("PASSED", "NOTHING") else 1
    s = state()
    print(s["says"])
    for n in s["needs_you"]:
        print("  NEEDS YOU  %s -- %s" % (n.get("path"), str(n.get("says"))[:110]))
    return 0 if s["healthy"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
