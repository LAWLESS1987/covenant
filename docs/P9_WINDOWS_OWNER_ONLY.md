# P9 — "owner-only" does not mean anything on NTFS, and the guard knows it

**Status: measured, tooling shipped, code change written and NOT applied.
The code change is a change to a security control, so it is L's to approve
(Section 0).**

---

## What was filed, and what it actually is

P9 was filed as a key-ACL nicety: *"the node's identity key file is not
owner-only on Windows."* The first Windows sweep, 2026-08-24, showed it is not
a nicety. Two independent witnesses in one run:

- `test_security_audit`'s single red — *identity key file is owner-only*
- `probe_final_pass` dying on
  `MainnetGuardError: Policy file ... is mode 0o666`

The second one means **`authorize_mainnet_payment` refuses on this machine,
always.** The XRP mainnet path cannot execute on the only box that runs
production — and nobody knew, because that probe had never been run there.

## The mechanism

```python
mode = stat.S_IMODE(os.stat(path).st_mode)
if mode & 0o077:
    raise MainnetGuardError(...)
```

On POSIX this is exactly right. On NTFS access is governed by ACLs;
`os.stat().st_mode` reports `0o666` for any writable file and `0o444` for a
read-only one, regardless of the ACL, and `os.chmod` only toggles the
read-only attribute. So on Windows `mode & 0o077` is not a weak check — it is
a **constant**, and the branch is unreachable in the passing direction.

That is fail-closed, so nothing unsafe has happened. It is still the disease
M34 describes: a check that is permanently red on the platform that runs
production has been switched off, and it teaches every reader to skim the
section it lives in. A sweep with a standing red cannot report a new one.

## What is shipped here, and what is not

| | |
|---|---|
| `ops/fix_key_acl.bat` | **applies** the control the mode bit was standing in for: `icacls /inheritance:r` then `/grant:r` to you, SYSTEM and Administrators, for every `*.db.key` and the policy file. Strictly tightening — it can only remove access. Writes `ops/ACL_RESULT.txt` and prints the resulting ACL. |
| `ops/owner_only.py` | the **reference implementation** of a platform-correct check, mutation-tested in both directions. Imported by nothing. |
| `launch_check.py` gate **G8** | **measures** it — reads the real ACL via `icacls` and reports PASS/BLOCKED/UNKNOWN. Disclosure only. |
| the code change below | **not applied.** |

## The change, if you want it

In `covenant_xrp_mainnet.MainnetPolicy.load`, and again at the key-file check
in `covenant_unified_v8.py`, replace the three lines above with:

```python
from owner_only import require_owner_only, OwnerOnlyError
try:
    require_owner_only(path)
except OwnerOnlyError as e:
    raise MainnetGuardError(str(e))
```

`require_owner_only` keeps the POSIX rule byte-for-byte and, on win32, reads
the real DACL and requires that every ACE names the owner, SYSTEM,
Administrators, or OWNER RIGHTS. Anything else — Users, Everyone,
Authenticated Users, another account — raises. **An ACL that cannot be read
raises too**, rather than being assumed safe.

It is strictly stronger than the line it replaces, in both directions: on
Windows it goes from *always refuse* to *refuse unless the ACL is actually
restricted*, and it never returns a value you can ignore.

## Before applying it

```
python ops\owner_only.py --test
```

It creates a temp file, tightens it, requires the guard to accept; then grants
`Everyone:F` and **requires the guard to refuse**. A guard that has only ever
seen correct input has never been tested (M31). On Linux both mutations pass
(`0600 accepted`, `0644 REFUSED`); on Windows it has not been run yet, because
this bundle was assembled in a Linux sandbox — M29 applies in full and this
line is here rather than smoothed over.

## Why it is not applied for you

Section 0: *never weaken a security control to make a test pass*, and a
consensus- or credential-affecting change is L's call. This change does not
weaken the control — but "it does not weaken it, trust me" is precisely the
sentence that should not be enough, and the whole point of the guard is that
it is the thing standing between a signing key and someone else's ability to
raise your limits. Read it, run the mutation test on the machine, then decide.
