#!/usr/bin/env python3
"""test_v1_verifier_agreement.py -- V1: three witnesses, actually compared.

THE CLAIM THIS EXISTS TO CHECK.

This project says, in the README, in GOVERNANCE.md and repeatedly in its own
commit messages, that the constitution is verified by THREE independent
implementations sharing no code:

    constitution.py   Python, any platform
    verify.sh         sh + awk + sha256, any Unix
    verify.ps1        PowerShell, any Windows

Nothing checked it. The three were compared by hand on 2026-08-30, agreed, and
then the claim was repeated all day on the strength of that one afternoon. If
verify.sh or verify.ps1 drifted -- an awk edit, a normalisation change, a
protected block added to one list and not the others -- the claim would go on
being made and nothing would notice.

That is exactly the shape this project keeps finding in itself: a check that
exists, is correct, and is never invoked. constitution.py had the same problem
until it was wired into three runners this morning.

WHAT V1 PINS.

  A*  the verifiers that CAN run here produce the SAME root, character for
      character, and each agrees with the published anchor.
  N*  A VERIFIER THAT COULD NOT RUN IS NOT A VERIFIER THAT AGREED. This is the
      whole discipline of the project applied to its own tooling -- the same
      rule as triangulate.py's silent witness, and the same rule G1 learned the
      hard way when a missing CONTRIBUTING.md let its checks pass vacuously.
      Fewer than two available means UNPROVEN, reported as a failure, never as
      agreement.
  D*  the verifiers really are INDEPENDENT: three languages, and none of them
      shells out to another. Agreement between two implementations where one
      calls the other is one implementation agreeing with itself.

Runs anywhere. On Linux, verify.ps1 is absent and V1 says so rather than
counting it.
"""
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print(f"{'ok  ' if ok else 'FAIL'}  {label}"
          f"{'' if ok else '  ' + str(detail)[:180]}", flush=True)


HEX64 = re.compile(r"\b([0-9a-f]{64})\b")


def run(cmd, timeout=120):
    try:
        p = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True,
                           timeout=timeout)
        return (p.stdout or "") + (p.stderr or ""), p.returncode
    except Exception as e:                                   # noqa: BLE001
        return "UNAVAILABLE: %s" % e, None


def roots_in(text):
    """Every 64-hex value the verifier printed, in order."""
    return HEX64.findall(text or "")


def main():
    print("V1 -- three witnesses, actually compared\n")

    # ---- gather whichever verifiers this machine can actually run ----------
    found = {}
    unavailable = {}

    out, rc = run([sys.executable, "constitution.py", "hash"])
    hs = roots_in(out)
    if hs:
        found["constitution.py"] = hs[0]
    else:
        unavailable["constitution.py"] = out.strip()[:90]

    sh = shutil.which("sh") or shutil.which("bash")
    if sh and os.path.isfile(os.path.join(HERE, "verify.sh")):
        out, rc = run([sh, "verify.sh"])
        hs = roots_in(out)
        if hs:
            found["verify.sh"] = hs[0]
        else:
            unavailable["verify.sh"] = out.strip()[:90]
    else:
        unavailable["verify.sh"] = "no sh on PATH, or verify.sh absent"

    ps = shutil.which("powershell") or shutil.which("pwsh")
    if ps and os.path.isfile(os.path.join(HERE, "verify.ps1")):
        out, rc = run([ps, "-NoProfile", "-ExecutionPolicy", "Bypass",
                       "-File", "verify.ps1"])
        hs = roots_in(out)
        if hs:
            found["verify.ps1"] = hs[0]
        else:
            unavailable["verify.ps1"] = out.strip()[:90]
    else:
        unavailable["verify.ps1"] = "no powershell on PATH, or verify.ps1 absent"

    for name, root in sorted(found.items()):
        print("      available  %-18s %s" % (name, root[:24]))
    for name, why in sorted(unavailable.items()):
        print("      UNAVAILABLE %-17s %s" % (name, why))
    print()

    # ---- N: an absent verifier is not an agreeing verifier -----------------
    check("N1 AT LEAST TWO verifiers ran. One implementation agreeing with "
          "itself is not agreement, and an absent verifier must never be "
          "counted as a concurring one -- the same rule this project applies "
          "to a silent witness everywhere else",
          len(found) >= 2, sorted(found))
    check("N2 ...and any verifier that could NOT run is named, so a reader "
          "knows which implementations this result actually covers",
          True if not unavailable else all(unavailable.values()),
          unavailable)

    if len(found) < 2:
        print("\nUNPROVEN -- fewer than two verifiers ran, so nothing was "
              "compared. Reported as a failure, never as agreement.")
        n, ok = len(results), sum(results)
        print(f"\nV1: {ok}/{n} passed")
        return 1

    # ---- A: they agree, and with the anchor -------------------------------
    vals = set(found.values())
    check("A1 every verifier that ran produced the SAME root, character for "
          "character. They share no code and no language, so agreement here "
          "is evidence rather than a tautology",
          len(vals) == 1, found)

    anchor = os.path.join(HERE, "docs", "CONSTITUTION_ANCHOR.json")
    published = ""
    try:
        with open(anchor, "r", encoding="utf-8") as fh:
            m = re.search(r'"hash"\s*:\s*"([0-9a-f]{64})"', fh.read())
            published = m.group(1) if m else ""
    except OSError:
        published = ""
    check("A2 the published anchor is readable and holds a root", bool(published))
    if published:
        for name, root in sorted(found.items()):
            check("A3:%-18s agrees with the PUBLISHED anchor, not merely with "
                  "the other verifiers. Three implementations could agree with "
                  "each other and all be wrong about what was published" % name,
                  root == published, (root[:20], published[:20]))

    # ---- D: independence is structural, not asserted -----------------------
    def code_only(name):
        """Source with COMMENT LINES REMOVED.

        D1 and D2 first searched the raw text for "python", and D2 failed on
        verify.ps1's own header -- which says "NEITHER PYTHON NOR A UNIX SHELL"
        and "constitution.py needs Python", because explaining what it replaces
        requires naming it. Fifth time in one day that a check matched a string
        where it should have read code.

        There is no AST for PowerShell or sh here, so this does the equivalent
        available thing: drop every comment line, then look for an INVOCATION.
        A mention in prose is not a call.
        """
        try:
            with open(os.path.join(HERE, name), encoding="utf-8",
                      errors="ignore") as fh:
                lines = fh.read().splitlines()
        except OSError:
            return ""
        return "\n".join(l for l in lines if not l.lstrip().startswith("#"))

    # INVOCATION markers, not words. A bare "sh " matched inside an output
    # string in verify.ps1 -- which is code, not a comment, and still not a
    # call. Each token below is a way a program is actually launched.
    CALLS = ("python", "py -", "constitution.py", "verify.sh", "verify.ps1",
             "Start-Process", "Invoke-Expression", "& sh", "& bash",
             "bash -", "sh -c")
    sh_code, ps_code = code_only("verify.sh"), code_only("verify.ps1")
    sh_calls = [c for c in CALLS if c in sh_code]
    ps_calls = [c for c in CALLS if c in ps_code]
    check("D1 verify.sh invokes neither python nor constitution.py in its "
          "CODE. Agreement between two implementations where one calls the "
          "other is one implementation agreeing with itself",
          not sh_calls, sh_calls)
    check("D2 verify.ps1 invokes neither python nor verify.sh in its code. It "
          "NAMES them in its header, because explaining what it replaces "
          "requires naming it -- which is why this reads code and not prose",
          not ps_calls, ps_calls)
    check("D3 each verifier computes sha256 with its OWN toolchain: hashlib, "
          "a shell sha256 utility, and .NET's SHA256 respectively",
          "hashlib" in code_only("constitution.py")
          and ("sha256sum" in sh_code or "shasum" in sh_code)
          and "System.Security.Cryptography" in ps_code)

    n, ok = len(results), sum(results)
    print(f"\nV1: {ok}/{n} passed")
    return 0 if ok == n else 1


if __name__ == "__main__":
    raise SystemExit(main())
