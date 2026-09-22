#!/usr/bin/env python3
"""covenant_heal.py -- one press, and the machine repairs what it can and names
what it cannot. The PC can press it for the phone; the phone can press it for
the PC.

HIS WORDS, 2026-09-21: "I need to be able to have the system fix itself for any
issues that arise" -- "Give me a one click self heal button on the pc and phone
apps that can fix eachother".

WHAT THIS IS, AND WHAT IT IS NOT. It is not a new repair engine. Everything it
runs is `covenant_highway` (A100 onward): nineteen detectors and the remedies
already classed AUTO_REVERSIBLE, each one already bounded, already recorded in
ops/highway.jsonl, already refusing to act while the highway is paused. What
was missing was a HANDLE -- the repairs ran only on the watchdog's own schedule,
so when he saw something wrong there was nothing to press.

"ANY ISSUES" IS NOT A PROMISE ANYONE CAN KEEP, and this module does not make
it. It repairs the conditions that have a remedy, and for everything else it
returns the condition, what was measured, and the reason there is no automatic
fix -- because a repair invented on the spot for a condition nobody has seen is
how a monitor takes a chain down. `summary()` says both halves out loud: fixed,
and still needs a person.

THE TWO DIRECTIONS (his "fix eachother"):
  heal()                  this machine repairs itself.
  heal_peer(host, port)   ask the machine at the other end of the wire to
                          repair ITSELF and report back. The caller never
                          reaches into the peer: it presses the peer's own
                          button, through the peer's own gate, and the peer
                          decides. That is the only shape that is safe in both
                          directions -- the phone cannot be made to run the
                          PC's remedies, nor the PC the phone's.
LICENCE: public domain.
"""
from __future__ import annotations

import importlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

LEDGER = os.path.join(HERE, "ops", "heal.jsonl")
PEER_TIMEOUT_S = 90


def _record(row, path=None):
    p = path or os.environ.get("COVENANT_HEAL_LEDGER") or LEDGER
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(dict(row, t=time.strftime("%Y-%m-%dT%H:%M:%S%z")), ensure_ascii=False) + "\n")
    except OSError:
        pass
    return row


def heal(dry_run=False, who="button", ledger_path=None, run=None, sense=None):
    """One press. Returns
    {"ok", "fixed": [...], "still_needs_a_person": [...], "looked_at": n,
     "paused": bool, "summary": str}. Never raises: a button that throws is
    not a button."""
    out = {"ok": False, "fixed": [], "still_needs_a_person": [], "looked_at": 0,
           "paused": False, "dry_run": bool(dry_run), "who": str(who)[:40]}
    try:
        import covenant_highway as HW
        conditions = (sense or HW.sense)()
        out["looked_at"] = len(conditions)
        present = {k: v for k, v in conditions.items() if v.get("state") == HW.PRESENT}
        try:
            import covenant_pause as _p
            out["paused"], _why = _p.paused("highway")
        except Exception:                                         # noqa: BLE001
            out["paused"], _why = False, ""
        # A PERSON PRESSED IT, so the hour-long noise cooldown does not apply:
        # cooldown_s=0 is the highway's own word for "a person typed --repair,
        # do not make them wait an hour for a line they have already read".
        # Measured before this was passed: a real press repaired NOTHING and
        # reported six conditions as needing a person, when five of them had a
        # remedy that was merely inside its cooldown. A button that does nothing
        # and blames the person is worse than no button.
        # It does NOT wave away a remedy's own declared budget (the build
        # runner's day stays a day) -- the highway keeps the larger of the two.
        alerts, infos = (run or HW.run_once)(dry_run=dry_run, cooldown_s=0)
        # What the engine actually did is in its own lines; a condition that is
        # gone on a second look is what "fixed" means, not what a remedy claimed.
        after = (sense or HW.sense)()
        for name in sorted(present):
            gone = after.get(name, {}).get("state") != HW.PRESENT
            (out["fixed"] if gone else out["still_needs_a_person"]).append({
                "condition": name,
                "measured": present[name].get("measured"),
                "why_no_fix": "" if gone else ("dry run: nothing was repaired, this is what a real press would face"
                                               if dry_run else (present[name].get("note") or _no_remedy_reason(HW, name))),
            })
        out["ok"] = True
        out["lines"] = [str(x)[:300] for x in (list(alerts) + list(infos))][:40]
    except Exception as e:                                        # noqa: BLE001
        out["error"] = "%s: %s" % (type(e).__name__, str(e)[:200])
    # A218 (his words: "Incorporate the antvirus take it over and use it to
    # protect the entire system"): one press also says what the defence is
    # doing, what it found and whether our own files are still ours. Said, not
    # acted on -- a failure to read it never fails the heal.
    try:
        out["defence"] = importlib.import_module("covenant_immune").state()
    except Exception as e:                                        # noqa: BLE001
        out["defence"] = {"ok": False, "says": "the defence could not be read (%s)" % type(e).__name__}
    out["summary"] = summary(out)
    _record(dict(out, kind="heal"), ledger_path)
    return out


def remedies_for(HW, name):
    """The remedy names registered for a condition. HW.REMEDIES is keyed by
    remedy name, each entry carrying the conditions it is 'for'."""
    out = []
    try:
        for rname, r in (HW.REMEDIES or {}).items():
            if name in list((r or {}).get("for") or []):
                out.append(rname)
    except Exception:                                             # noqa: BLE001
        pass
    return sorted(out)


def _no_remedy_reason(HW, name):
    """Why this one is still here -- the honest distinction between 'nothing
    can repair it' and 'a repair ran and did not settle it'."""
    got = remedies_for(HW, name)
    if not got:
        return ("no automatic remedy exists for this one: it is reported for a person, "
                "never repaired by the machine")
    return "the remedy (%s) ran and the condition is still present" % ", ".join(got)


def summary(out):
    """One line a person can read without opening anything."""
    if out.get("error"):
        return "the heal could not run: %s" % out["error"]
    if out.get("paused"):
        return ("looked at %d condition(s); the highway is PAUSED so nothing was repaired -- "
                "resume it with: python covenant_pause.py --resume highway" % out.get("looked_at", 0))
    f, n = len(out.get("fixed", [])), len(out.get("still_needs_a_person", []))
    if not f and not n:
        base = "looked at %d condition(s); nothing was wrong" % out.get("looked_at", 0)
        d0 = out.get("defence") or {}
        return base + (". Defence: " + d0["says"] if d0.get("says") else "")
    bits = []
    if f:
        bits.append("fixed %d (%s)" % (f, ", ".join(x["condition"] for x in out["fixed"][:4])))
    if n:
        bits.append("%d still needs a person (%s)" % (n, ", ".join(x["condition"] for x in out["still_needs_a_person"][:4])))
    line = "looked at %d condition(s); %s" % (out.get("looked_at", 0), "; ".join(bits))
    d = out.get("defence") or {}
    if d.get("says"):
        line += ". Defence: " + d["says"]
    return line


def heal_peer(host, port, dry_run=False, timeout=PEER_TIMEOUT_S, ledger_path=None, post=None):
    """Press the OTHER machine's button. It repairs itself and reports; nothing
    here reaches into it. Returns its answer, or an error row that says why."""
    row = {"kind": "heal_peer", "host": str(host)[:60], "port": int(port), "dry_run": bool(dry_run)}
    try:
        if post is None:
            post = _post_signed
        code, body = post(host, port, "/m/heal", {"dry_run": bool(dry_run)}, timeout)
        row["code"] = code
        try:
            row["answer"] = json.loads(body) if isinstance(body, (str, bytes)) else body
        except ValueError:
            row["answer"] = {"raw": str(body)[:400]}
        row["ok"] = code == 200 and bool((row.get("answer") or {}).get("ok"))
        row["summary"] = (row.get("answer") or {}).get("summary") or ("the peer answered %s" % code)
    except Exception as e:                                        # noqa: BLE001
        row["ok"] = False
        row["summary"] = "the peer could not be reached: %s: %s" % (type(e).__name__, str(e)[:160])
    _record(row, ledger_path)
    return row


def _post_signed(host, port, path, payload, timeout):
    """The operator-request signature the mesh already uses, so the peer's own
    gate admits this exactly as it admits the check-in."""
    import covenant_daily_plan as DP
    body = json.dumps(payload).encode("utf-8")
    headers = DP.sign_request(body) if hasattr(DP, "sign_request") else {}
    import urllib.request
    req = urllib.request.Request("http://%s:%d%s" % (host, int(port), path), data=body,
                                 headers=dict(headers, **{"Content-Type": "application/json"}))
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return getattr(r, "status", 200), r.read().decode("utf-8", "replace")


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="one press: repair what can be repaired, name what cannot")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--peer", metavar="HOST:PORT", help="press the other machine's button instead")
    a = ap.parse_args(argv)
    if a.peer:
        h, _, p = a.peer.partition(":")
        out = heal_peer(h, int(p or 5000), dry_run=a.dry_run)
    else:
        out = heal(dry_run=a.dry_run, who="cli")
    print(out.get("summary", ""))
    for x in out.get("fixed", []):
        print("  fixed            %s" % x["condition"])
    for x in out.get("still_needs_a_person", []):
        print("  needs a person   %-26s %s" % (x["condition"], str(x.get("why_no_fix"))[:90]))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
