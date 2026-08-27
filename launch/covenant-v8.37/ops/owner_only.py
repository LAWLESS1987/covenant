"""ops/owner_only.py -- what "owner-only" MEANS on Windows. Reference only.

NOT WIRED INTO ANYTHING, DELIBERATELY.  This is the proposed fix for P9 and it
is a change to a security control, which Section 0 of the improvement loop
reserves for L. It sits here so the change can be read, run and argued with
before anyone decides to make it. Importing this module changes no behaviour.

THE PROBLEM, stated precisely.

covenant_xrp_mainnet.MainnetPolicy.load does:

    mode = stat.S_IMODE(os.stat(path).st_mode)
    if mode & 0o077:
        raise MainnetGuardError(...)

On POSIX that is exactly right. On NTFS it is not a weak check, it is a
CONSTANT: Windows reports 0o666 for any writable file and 0o444 for a
read-only one, regardless of the ACL, and os.chmod there only toggles the
read-only attribute. So `mode & 0o077` is always true, the guard always
raises, and `authorize_mainnet_payment` refuses on that machine
unconditionally -- measured, 2026-08-24, by probe_final_pass.

That is FAIL-CLOSED, so nothing unsafe has happened. But it means the control
has never been tested on the only platform that runs production, and a check
that is permanently red teaches its reader to skim past the section it lives
in (M34). The fix is not to skip it there and not to relax it there. It is to
assert what "only the owner can read this" actually means there.

WHAT THIS DOES INSTEAD.

  posix : unchanged. mode & 0o077 must be zero.
  win32 : read the real DACL with icacls and require that every ACE names the
          file's owner, SYSTEM, Administrators, or OWNER RIGHTS. Anything else
          -- Users, Everyone, Authenticated Users, another account -- fails.
          If the ACL cannot be read, that is UNKNOWN, and UNKNOWN raises.

It is strictly STRONGER than the line it would replace, in both directions:
on Windows it goes from "always refuse" to "refuse unless the ACL is actually
restricted", and it refuses on an unreadable ACL rather than assuming.

THE DIFF, if L approves it. In covenant_xrp_mainnet.MainnetPolicy.load,
replace the three lines quoted above with:

    from owner_only import require_owner_only, OwnerOnlyError
    try:
        require_owner_only(path)
    except OwnerOnlyError as e:
        raise MainnetGuardError(str(e))

and the same at covenant_unified_v8.py's key-file check.

BEFORE APPLYING IT, and this is the part that matters: run test_mutations()
below. A guard that has only ever seen correct input has never been tested
(M31). It builds a file granting Everyone:F and requires this to REFUSE it.
If that mutation passes the guard, the guard is decoration.
"""
import os
import re
import stat
import subprocess
import sys

WIN = sys.platform.startswith("win")


class OwnerOnlyError(Exception):
    pass


_ALLOWED = re.compile(
    r"(NT AUTHORITY\\SYSTEM|BUILTIN\\Administrators|OWNER RIGHTS|CREATOR OWNER)",
    re.I)
_DENIED_HINT = re.compile(
    r"(Everyone|BUILTIN\\Users|NT AUTHORITY\\Authenticated Users|"
    r"NT AUTHORITY\\INTERACTIVE)", re.I)


def acl_principals(path):
    """Every principal named in the file's DACL. Raises if it cannot be read."""
    try:
        out = subprocess.run(["icacls", path], capture_output=True, text=True,
                             timeout=20)
    except Exception as e:
        raise OwnerOnlyError("cannot read the ACL of %s (%s). An ACL that "
                             "cannot be read is not an ACL that is safe."
                             % (path, e))
    if out.returncode != 0:
        raise OwnerOnlyError("icacls failed on %s: %s"
                             % (path, (out.stderr or "").strip()[:200]))
    who = []
    for raw in out.stdout.splitlines():
        line = raw.strip()
        if not line or line.lower().startswith("successfully"):
            continue
        if ":(" not in line:
            continue
        head = line.split(":(", 1)[0]
        # the first line is "<path> <principal>:(...)"; later ones are just the
        # principal. Take the trailing token group either way.
        if head.lower().startswith(path.lower()):
            head = head[len(path):]
        head = head.strip()
        if head:
            who.append(head)
    if not who:
        raise OwnerOnlyError("no ACEs parsed from icacls output for %s -- "
                             "refusing rather than guessing." % path)
    return who


def require_owner_only(path):
    """Raise OwnerOnlyError unless only the owner (plus SYSTEM/Admins) has
    access. Never returns False -- a check that can be ignored is a comment."""
    if not os.path.exists(path):
        raise OwnerOnlyError("%s does not exist" % path)
    if not WIN:
        mode = stat.S_IMODE(os.stat(path).st_mode)
        if mode & 0o077:
            raise OwnerOnlyError(
                "%s is mode %s -- readable or writable beyond its owner. "
                "Anything that can edit this can raise your own limits. "
                "Run: chmod 600 %s" % (path, oct(mode), path))
        return True
    me = (os.environ.get("USERNAME") or "").lower()
    strangers = []
    for who in acl_principals(path):
        w = who.lower()
        if _ALLOWED.search(who):
            continue
        if me and (w == me or w.endswith("\\" + me)):
            continue
        strangers.append(who)
    if strangers:
        hint = " (this is the default inherited ACL)" if any(
            _DENIED_HINT.search(s) for s in strangers) else ""
        raise OwnerOnlyError(
            "%s grants access to %s%s. On NTFS the mode bit says nothing; the "
            "ACL is the control. Run: ops\\fix_key_acl.bat"
            % (path, ", ".join(strangers), hint))
    return True


def test_mutations(tmpdir="."):
    """Prove the guard can FAIL. Run this before trusting it (M31)."""
    import tempfile
    ok = []
    fd, p = tempfile.mkstemp(dir=tmpdir, suffix=".ownertest")
    os.close(fd)
    try:
        if WIN:
            subprocess.run(["icacls", p, "/inheritance:r"], capture_output=True)
            subprocess.run(["icacls", p, "/grant:r",
                            "%s:F" % os.environ.get("USERNAME", "")],
                           capture_output=True)
            try:
                require_owner_only(p)
                ok.append(("tightened file accepted", True))
            except OwnerOnlyError as e:
                ok.append(("tightened file accepted", False, str(e)))
            subprocess.run(["icacls", p, "/grant:r", "Everyone:F"],
                           capture_output=True)
            try:
                require_owner_only(p)
                ok.append(("Everyone:F REFUSED", False,
                           "the guard passed a world-readable file"))
            except OwnerOnlyError:
                ok.append(("Everyone:F REFUSED", True))
        else:
            os.chmod(p, 0o600)
            ok.append(("0600 accepted", require_owner_only(p) is True))
            os.chmod(p, 0o644)
            try:
                require_owner_only(p)
                ok.append(("0644 REFUSED", False, "the guard passed 0644"))
            except OwnerOnlyError:
                ok.append(("0644 REFUSED", True))
    finally:
        try:
            os.remove(p)
        except Exception:
            pass
    for r in ok:
        print(("PASS " if r[1] else "FAIL ") + r[0] +
              ("" if len(r) < 3 else "  <- " + r[2]))
    return all(r[1] for r in ok)


if __name__ == "__main__":
    if "--test" in sys.argv:
        sys.exit(0 if test_mutations() else 1)
    for a in sys.argv[1:]:
        try:
            require_owner_only(a)
            print("OWNER-ONLY  %s" % a)
        except OwnerOnlyError as e:
            print("NOT SAFE    %s" % e)
