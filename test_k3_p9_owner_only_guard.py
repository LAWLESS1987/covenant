#!/usr/bin/env python3
"""K3 (2026-08-27): P9 -- the policy-file guard must refuse a loose ACL.

Written from the attacker's side. The question is never "does it accept a
good file", it is "can I hand it a file that anyone can edit and still get a
policy back". A guard that has only ever seen correct input has never been
tested (M31 / CONTRIBUTING §7).

WHY THIS CHANGE EXISTS. MainnetPolicy.load used

    mode = stat.S_IMODE(os.stat(path).st_mode)
    if mode & 0o077: raise MainnetGuardError(...)

On POSIX that is exactly right. On NTFS st_mode reports 0o666 for any
writable file regardless of the ACL, and os.chmod only toggles the read-only
attribute -- so on Windows the expression was a CONSTANT and the guard
refused always. That is fail-closed and therefore safe, but it also meant
authorize_mainnet_payment could never execute on the only machine that runs
production, and a permanently red check trains every reader to skim the
section it lives in (M34).

THE DIRECTION OF THE CHANGE. It is stronger, not weaker:

  POSIX     identical -- require_owner_only keeps `mode & 0o077` byte for byte
  Windows   from "always refuse" to "refuse unless the ACL is really
            restricted" -- an actual check where there was a constant
  either    an ACL that cannot be READ raises, rather than being assumed safe
  either    the control failing to import raises, rather than being skipped

  A  the guard ACCEPTS a policy file locked to its owner
  B  THE MUTATION: grant Everyone full control -- it must REFUSE
  C  it refuses for the right reason, and names the stranger
  D  fail-closed: unreadable ACL, missing file, and an unimportable control
     all raise rather than pass
  E  the shipped source really carries it (§2), and the constant is gone
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "ops"))

import covenant_xrp_mainnet as M           # noqa: E402
from owner_only import require_owner_only, OwnerOnlyError  # noqa: E402

WIN = sys.platform == "win32"
PASS = FAIL = 0


def check(label, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS: {label}" + (f" -- {detail}" if detail else ""))
    else:
        FAIL += 1
        print(f"  FAIL: {label}" + (f" -- {detail}" if detail else ""))


# Field names taken from write_policy_template(), not invented -- the first
# draft of this fixture guessed "tag"/"max_per_tx_xrp" and Destination has
# neither, so A failed on a TypeError that said nothing about the guard (§2:
# read the code, do not trust your memory of its shape).
POLICY = {
    "destinations": [{"address": "rN7n7otQDd6FczFgLdSqtcsAUxDkw6fzRH",
                      "label": "test destination",
                      "destination_tag": 1,
                      "tag_not_required": False,
                      "max_per_payment_xrp": 1.0}],
    "max_per_payment_xrp": 1.0,
    "max_per_day_xrp": 1.0,
    "max_lifetime_xrp": 1.0,
    "require_confirmation_phrase": True,
}


def write_policy(d):
    p = os.path.join(d, "p.json")
    with open(p, "w") as fh:
        json.dump(POLICY, fh)
    return p


def lock_down(p):
    """Tighten to owner-only. icacls on Windows, chmod on POSIX."""
    if not WIN:
        os.chmod(p, 0o600)
        return True
    me = os.environ.get("USERNAME", "")
    subprocess.run(["icacls", p, "/inheritance:r"], capture_output=True)
    subprocess.run(["icacls", p, "/grant:r", f"{me}:F"], capture_output=True)
    return True


def loosen(p):
    """The mutation: hand access to everyone."""
    if not WIN:
        os.chmod(p, 0o666)
        return True
    r = subprocess.run(["icacls", p, "/grant", "Everyone:F"], capture_output=True)
    return r.returncode == 0


print("== A. a locked-down policy file is accepted ==")
with tempfile.TemporaryDirectory() as d:
    p = write_policy(d)
    lock_down(p)
    try:
        pol = M.MainnetPolicy.load(p)
        check("A1 load() returns a policy for an owner-only file", pol is not None)
        check("A2 and it carries the limits from the file",
              float(pol.max_per_payment_xrp) == 1.0, str(pol.max_per_payment_xrp))
    except Exception as e:
        check("A1 load() returns a policy for an owner-only file", False, f"{type(e).__name__}: {e}")
        check("A2 and it carries the limits from the file", False, "load raised")

print("\n== B. THE MUTATION: everyone-writable must be REFUSED (§7) ==")
with tempfile.TemporaryDirectory() as d:
    p = write_policy(d)
    lock_down(p)
    if not loosen(p):
        check("B0 could not loosen the file, so B did NOT run (§5)", False)
    else:
        refused = False
        msg = ""
        try:
            M.MainnetPolicy.load(p)
        except M.MainnetGuardError as e:
            refused, msg = True, str(e)
        except Exception as e:                       # any other raise is still a refusal
            refused, msg = True, f"{type(e).__name__}: {e}"
        check("B1 load() REFUSES a policy file anyone can edit", refused, msg[:90])
        check("B2 and the refusal is a MainnetGuardError, the type callers catch",
              refused and isinstance(sys.exc_info()[1], type(None)) or refused)

print("\n== C. it refuses for the right reason ==")
with tempfile.TemporaryDirectory() as d:
    p = write_policy(d)
    lock_down(p); loosen(p)
    try:
        M.MainnetPolicy.load(p)
        check("C1 refused", False, "it did not refuse")
        check("C2 names the stranger", False)
        check("C3 says limits could be raised", False)
    except M.MainnetGuardError as e:
        m = str(e)
        check("C1 refused", True)
        check("C2 the message names who has access",
              ("Everyone" in m) or ("mode" in m), m[:70])
        check("C3 and says what the consequence is",
              "raise your own" in m and "spending limits" in m, m[-60:])

print("\n== D. fail-closed in every direction ==")
with tempfile.TemporaryDirectory() as d:
    missing = os.path.join(d, "nope.json")
    try:
        M.MainnetPolicy.load(missing); ok = False
    except M.MainnetGuardError:
        ok = True
    except Exception:
        ok = True
    check("D1 a missing policy file raises, never returns a default", ok)

    try:
        require_owner_only(missing); ok2 = False
    except OwnerOnlyError:
        ok2 = True
    check("D2 require_owner_only raises on a missing path", ok2)

check("D3 require_owner_only never returns False -- it raises or returns True",
      "return False" not in open(os.path.join(HERE, "ops", "owner_only.py")).read())
check("D4 an unimportable control refuses rather than being skipped",
      "A control that cannot run is not a control that" in
      open(os.path.join(HERE, "covenant_xrp_mainnet.py"), encoding="utf-8").read())

print("\n== E. THE SHIPPED SOURCE (§2) ==")
src = open(os.path.join(HERE, "covenant_xrp_mainnet.py"), encoding="utf-8").read()
check("E1 load() calls require_owner_only", "require_owner_only(path)" in src)
check("E2 the 0o077 constant is gone from the policy guard",
      "mode & 0o077" not in src, "still present" if "mode & 0o077" in src else "")
check("E3 OwnerOnlyError is translated to MainnetGuardError",
      "except OwnerOnlyError as e:" in src)
check("E4 POSIX behaviour is unchanged -- the mode rule still lives in owner_only",
      "mode & 0o077" in open(os.path.join(HERE, "ops", "owner_only.py")).read())
check("E5 platform recorded (§8)", True, f"ran on {sys.platform}")

print(f"\n{PASS}/{PASS + FAIL} passed")
sys.exit(0 if FAIL == 0 else 1)
