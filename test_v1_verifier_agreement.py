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

    # ---- D4: no shell verifier may CALL a command Windows also ships ------
    #
    # THE BUG THIS CATCHES, found 2026-08-31 by running V1 from a PowerShell
    # prompt instead of from Git Bash. `sort` resolved to
    # C:\WINDOWS\system32\sort.exe while awk, sed, tr and sha256sum all still
    # came from /usr/bin. Windows sort emits CRLF and orders differently, so
    # verify.sh combined the block digests differently and computed
    # 520dd1c09ceaeca4... against the anchored 0f0b316270f5acff... -- then
    # printed MISMATCH.
    #
    # A confident false alarm is worse than a silence: it told an honest
    # reader the constitution had been tampered with on a machine where
    # nothing was wrong. Every check on the blocks themselves passed, because
    # the three block digests were identical in both environments; only the
    # combining step diverged. Which process launched the shell is not
    # something a stranger will think to control, so the dependency had to go
    # rather than be documented.
    #
    # THE FIRST VERSION OF THIS CHECK MADE THE EXACT ERROR IT WARNS ABOUT.
    # It looked for the WORDS, and duly failed on `find` inside the text of an
    # error message, on `print` inside an awk program, and on a shell variable
    # named path. Ninth grep-instead-of-parse in this repository, and the
    # first one committed inside the check written to prevent a different one.
    #
    # So it reads COMMAND POSITIONS. String literals are removed first, which
    # deletes prose and embedded awk in one step; then each line is split on
    # the operators that open a new command, and only the first token of each
    # piece can be a command. Tokens containing "=" are assignments.
    SHADOWED = ("sort", "find", "more", "timeout", "expand", "comp", "print",
                "replace", "forfiles", "where", "tree", "fc")

    STRINGS = re.compile(r"'[^']*'|\"[^\"]*\"")
    OPENERS = re.compile(r"\||&&|\|\||;|\$\(|`|\{|\(|&")
    WORDS = ("if", "then", "else", "elif", "fi", "for", "while", "do", "done",
             "case", "esac", "in", "!", "[", "[[", "test", "return", "exit")

    def commands_in(name):
        """Every token that stands in a command position. Comments and string
        literals are gone before anything is looked at."""
        path = os.path.join(HERE, name)
        if not os.path.exists(path):
            return None
        found = []
        for ln in open(path, encoding="utf-8"):
            stripped = ln.strip()
            if not stripped or stripped.startswith("#"):
                continue
            bare = STRINGS.sub(" ", stripped)
            for piece in OPENERS.split(bare):
                for tok in piece.split():
                    if "=" in tok or tok in WORDS:
                        continue
                    found.append((tok, stripped[:70]))
                    break
        return found

    for script in ("verify.sh", "check.sh"):
        cmds = commands_in(script)
        if cmds is None:
            check("D4:%-10s exists to be read" % script, False, "absent")
            continue
        hits = [(t, l) for t, l in cmds if t in SHADOWED]
        check("D4:%-10s CALLS no command that Windows System32 also "
              "provides. On Windows the tool a shell finds depends on which "
              "process launched it, so a verifier that calls one is a "
              "verifier whose answer depends on its caller" % script,
              not hits, hits[:3])


    # ---- C: the two ONE-COMMAND checkers must not drift apart --------------
    #
    # check.sh and check.ps1 are the front door: almost everyone who ever
    # verifies anything here will do it by running one of them and reading
    # nothing else. They are hand-maintained twins, so the failure to fear is
    # that a POSIX reader and a Windows reader get DIFFERENT verdicts on the
    # same tree and neither can tell.
    #
    # They are not independent verifiers and nothing here claims they are --
    # both shell out to the same tools. What is checked is that they AGREE,
    # and that each still fails when it should.
    import tempfile   # the rest -- os, re, shutil, subprocess -- are module-level

    def tally(out):
        """The 'N passed, N disagreed, N skipped' line, as numbers. Behaviour,
        not prose: comparing the two scripts' TEXT would pass while they
        disagreed, which is the failure being guarded against."""
        m = re.search(r"(\d+) passed, (\d+) disagreed, (\d+) skipped", out)
        return tuple(int(g) for g in m.groups()) if m else None

    def run_checker(cmd, cwd):
        try:
            r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                               timeout=180)
            return r.returncode, r.stdout + r.stderr
        except Exception as e:                               # noqa: BLE001
            return None, "%s: %s" % (type(e).__name__, e)

    sh_bin = shutil.which("sh")
    ps_bin = shutil.which("powershell") or shutil.which("pwsh")

    check("C1 both one-command checkers are SHIPPED. The README and both "
          "outreach letters tell a stranger to run one of these, so a missing "
          "file is a broken instruction on a platform this host cannot test",
          os.path.exists(os.path.join(HERE, "check.sh"))
          and os.path.exists(os.path.join(HERE, "check.ps1")))

    # WHICH OF THE TWO CAN RUN HERE, named rather than demanded.
    #
    # The first version of C2 required BOTH, and there are only two checkers --
    # one of them PowerShell -- so requiring both required Windows. It failed
    # on both ubuntu CI jobs, which is a wrong check behaving correctly.
    #
    # V1 already had the answer in its own docstring: "On Linux, verify.ps1 is
    # absent and V1 says so rather than counting it." The same rule, applied
    # to the same problem, one section further down the same file. Cross-
    # platform agreement can only be tested where both exist, and saying that
    # plainly is worth more than a check that cannot pass off Windows.
    ran = {}
    absent = {}
    if sh_bin:
        rc, out = run_checker([sh_bin, "check.sh"], HERE)
        t = tally(out)
        if t is None:
            absent["check.sh"] = "ran but printed no tally: " + out.strip()[-90:]
        else:
            ran["check.sh"] = (t, rc)
    else:
        absent["check.sh"] = "no sh on PATH"
    if ps_bin:
        rc, out = run_checker([ps_bin, "-NoProfile", "-ExecutionPolicy",
                               "Bypass", "-File", "check.ps1"], HERE)
        t = tally(out)
        if t is None:
            absent["check.ps1"] = "ran but printed no tally: " + out.strip()[-90:]
        else:
            ran["check.ps1"] = (t, rc)
    else:
        absent["check.ps1"] = "no powershell on PATH -- expected on Linux"

    for name in sorted(absent):
        print("      UNAVAILABLE %-17s %s" % (name, absent[name]))

    check("C2 AT LEAST ONE checker ran here and reported a verdict. This is "
          "the part that holds on every platform: the front door the README "
          "sends people to must work on the host running this suite",
          bool(ran), {"ran": sorted(ran), "absent": absent})

    if len(ran) >= 2:
        verdicts = {v for v in ran.values()}
        check("C2b the two checkers reach the SAME verdict on this tree -- "
              "same passed/disagreed/skipped, same exit code. A Windows "
              "reader and a POSIX reader must not be told different things "
              "about the same repository",
              len(verdicts) == 1, ran)
    else:
        # Not a pass, not a failure: a statement about this host. Counting it
        # as agreement would be the exact error N* exists to prevent, and
        # counting it as disagreement is what just broke CI.
        print("      NOT COMPARED  only %s ran here, so cross-platform "
              "agreement was not tested on this host" % (sorted(ran) or "none"))

    # C3/C4 -- the mutation test, run every time rather than once by hand.
    #
    # A check that exists, is correct and is never invoked is this project's
    # most frequently rediscovered defect, and a mutation test verified once
    # on an afternoon is exactly that shape. So it runs here -- in a COPY, in
    # a temp directory. The real CONTRIBUTING.md is never touched, because a
    # suite that mutates the repository it is testing leaves it mutated the
    # first time it crashes.
    if sh_bin:
        tmp = tempfile.mkdtemp(prefix="v1_mut_")
        try:
            os.makedirs(os.path.join(tmp, "docs"), exist_ok=True)
            for rel in ("check.sh", "verify.sh", "constitution.py",
                        "CONTRIBUTING.md", "docs/CONSTITUTION_ANCHOR.json",
                        "docs/SUCCESSION.md"):
                src = os.path.join(HERE, rel.replace("/", os.sep))
                if os.path.exists(src):
                    shutil.copy2(src, os.path.join(tmp, rel.replace("/", os.sep)))

            rc_clean, out_clean = run_checker([sh_bin, "check.sh"], tmp)
            check("C3 on an unmutated copy the checker exits 0. Without this, "
                  "C4 could pass because the checker fails on everything",
                  rc_clean == 0, "rc=%s %s" % (rc_clean, out_clean[-200:]))

            cpath = os.path.join(tmp, "CONTRIBUTING.md")
            with open(cpath, encoding="utf-8") as fh:
                body = fh.read()
            head = "## What never changes"
            i = body.index(head) + len(head)
            with open(cpath, "w", encoding="utf-8", newline="") as fh:
                fh.write(body[:i] + "\n\nMUTATION.\n" + body[i:])

            rc_mut, out_mut = run_checker([sh_bin, "check.sh"], tmp)
            check("C4 altering ONE protected line makes the checker exit "
                  "non-zero and print MISMATCH. This is the property every "
                  "invitation to verify depends on, and it is now tested on "
                  "every run instead of once by hand",
                  rc_mut == 1 and "MISMATCH" in out_mut,
                  "rc=%s %s" % (rc_mut, out_mut[-200:]))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    else:
        check("C3 mutation test ran", False, "NOT CHECKED: no sh on this host")
        check("C4 mutation test ran", False, "NOT CHECKED: no sh on this host")

    n, ok = len(results), sum(results)
    print(f"\nV1: {ok}/{n} passed")
    return 0 if ok == n else 1


if __name__ == "__main__":
    raise SystemExit(main())
