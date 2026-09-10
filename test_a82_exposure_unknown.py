#!/usr/bin/env python3
"""
A82 -- exposure_check said "Nothing to expose" when it could not look.

THE HAZARD, measured on this machine on 2026-09-10. With netstat reachable the
tool printed four WILDCARD sockets and "REACHABLE ... on: private, public",
exit 1. Sixty seconds later, same binary, same source, netstat merely not
resolvable:

    COVENANT EXPOSURE CHECK -- read-only, changes nothing
    ------------------------------------------------------------
    Nothing listening on any covenant port. Nothing to expose.
    EXIT=0

`_run` collapsed FileNotFoundError, a non-zero exit and a real 25-second
TimeoutExpired all into `""`, and both readers -- `listeners()` and
`allowing_rules()` -- treated `""` as "measured, found nothing".

This is the worst possible failure for this tool in particular: it exists to
answer whether the operator's machine is reachable from the internet, and the
answer it gave when it could not look was the reassuring one. The file states
the correct rule twice in its own prose -- "do not treat 'could not check' as
'not exposed'" and "Treat as UNKNOWN, not as safe" -- and `_run` defeated both.

Nothing in the repository referenced exposure_check before this file.

WHY THESE CHECKS ARE BEHAVIOURAL. They run the real functions. E1/E2 execute a
real subprocess that genuinely cannot be found and one that genuinely succeeds;
the rest substitute `_run` -- the single seam where "did not run" is decided --
and then run the real `listeners`, `allowing_rules` and `main`. No check reads
the source of exposure_check.py or asserts on a string in it, which is the
fake-guard shape A74 found in 35 of 36 suites.

PLATFORM. `main()` refuses on non-Windows by design and returns 2. On win32
E4-E8 exercise it fully; elsewhere they are replaced by E9, which asserts that
refusal, and the count reflects which ran -- a suite that silently tests less on
another platform would be this file's own subject one level up.

CHECKS (fast, no network, nothing written):
  E1  _run returns None for a command that cannot run at all
  E2  _run returns text for a command that does run
  E3  listeners() -> None when netstat did not run, [] when it ran clean
  E4  main() on an unrunnable netstat NEVER prints "Nothing to expose" and
      does not exit 0
  E5  ...and the clean empty case is untouched: exit 0, and it does say it
  E6  allowing_rules() -> None when netsh did not run, [] when it ran clean
  E7  main() with wildcard sockets and unreadable firewall rules does not
      print "Probably not reachable" and does not exit 0
  E8  ...and with rules genuinely absent it still prints exactly that
  E9  (non-Windows only) main() refuses rather than guessing
"""
import io
import os
import sys
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exposure_check as X  # noqa: E402

results = []


def check(label, ok, detail=""):
    results.append((label, bool(ok)))
    detail = "" if detail == "" or detail is None else str(detail)[:100]
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", label,
                           ("  -- " + detail) if detail else ""))


def run_main():
    """main()'s exit code and everything it printed."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = X.main()
    return rc, buf.getvalue()


NETSTAT_TWO_WILDCARD = """
  Proto  Local Address          Foreign Address        State           PID
  TCP    0.0.0.0:5000           0.0.0.0:0              LISTENING       4242
  TCP    0.0.0.0:5010           0.0.0.0:0              LISTENING       4242
"""


def main():
    print("A82 -- 'could not look' must never render as 'nothing to expose'\n")

    # E1/E2 -- the seam itself, against real subprocesses.
    gone = X._run(["definitely-not-a-real-binary-a82", "--version"])
    check("E1 _run returns None for a command that cannot run at all",
          gone is None, repr(gone))
    real = X._run([sys.executable, "-c", "print('hello-a82')"])
    check("E2 _run returns the text for a command that does run",
          isinstance(real, str) and "hello-a82" in real, repr(real)[:60])

    saved = X._run
    try:
        # E3 -- unknown and empty must not be the same value.
        X._run = lambda cmd: None
        none_listeners = X.listeners()
        X._run = lambda cmd: "no LISTENING lines here at all"
        empty_listeners = X.listeners()
        check("E3 listeners() is None when netstat did not run",
              none_listeners is None, repr(none_listeners))
        check("E3b ...and [] when it ran and matched nothing -- a real "
              "measurement, and a different fact",
              empty_listeners == [], repr(empty_listeners))

        # E6 -- the same distinction on the firewall side.
        X._run = lambda cmd: None
        check("E6 allowing_rules() is None when netsh did not run",
              X.allowing_rules("python.exe") is None)
        X._run = lambda cmd: "Rule Name:  something unrelated\nEnabled: Yes\n"
        check("E6b ...and [] when it ran and named no rule for this program",
              X.allowing_rules("python.exe") == [])

        if sys.platform.startswith("win"):
            # E4 -- the exact sentence that was printed on a REACHABLE machine.
            X._run = lambda cmd: None
            rc, out = run_main()
            # THE WHOLE VERDICT SENTENCE, not the phrase. The new warning text
            # quotes "nothing to expose" in lower case to tell the reader what
            # it is refusing to say, so a substring test on the phrase would
            # pass only by capitalisation -- an accidental pass, which is this
            # file's own subject. Assert the line that actually reassures.
            CLEAN_LINE = "Nothing listening on any covenant port. Nothing to expose."
            check("E4 an unrunnable netstat NEVER prints the clean verdict line",
                  CLEAN_LINE not in out, out.strip()[-70:])
            check("E4b ...and does not exit 0", rc != 0, "rc=%s" % rc)
            check("E4c ...and says the word UNKNOWN, so a reader is told which "
                  "of the two it is", "UNKNOWN" in out, out.strip()[-70:])

            # E5 -- the honest empty case must be untouched.
            X._run = lambda cmd: "nothing listening here"
            rc, out = run_main()
            check("E5 a netstat that RAN and found nothing still reports clean",
                  rc == 0 and "Nothing to expose" in out, "rc=%s" % rc)

            # E7 -- wildcard sockets, firewall unreadable.
            def netstat_ok_netsh_dead(cmd):
                if cmd and cmd[0] == "netstat":
                    return NETSTAT_TWO_WILDCARD
                if cmd and cmd[0] == "netsh":
                    return None
                return "C:\\fake\\python.exe"        # program_for
            X._run = netstat_ok_netsh_dead
            rc, out = run_main()
            check("E7 wildcard sockets with UNREADABLE firewall rules do not "
                  "print 'Probably not reachable'",
                  "Probably not reachable" not in out, out.strip()[-70:])
            check("E7b ...and do not exit 0", rc != 0, "rc=%s" % rc)

            # E8 -- but a firewall that really has no rule still says so.
            def netstat_ok_netsh_empty(cmd):
                if cmd and cmd[0] == "netstat":
                    return NETSTAT_TWO_WILDCARD
                if cmd and cmd[0] == "netsh":
                    return "Rule Name:  unrelated\nEnabled: Yes\n"
                return "C:\\fake\\python.exe"
            X._run = netstat_ok_netsh_empty
            rc, out = run_main()
            check("E8 a firewall that genuinely names no rule still reports "
                  "'Probably not reachable' and exits 0",
                  rc == 0 and "Probably not reachable" in out, "rc=%s" % rc)
        else:
            rc, out = run_main()
            check("E9 on a non-Windows host main() refuses rather than guessing",
                  rc == 2 and "do not" in out.lower(), "rc=%s" % rc)
    finally:
        X._run = saved

    n = sum(1 for _, ok in results if ok)
    print("\nA82: %d/%d passed" % (n, len(results)))
    return 0 if n == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
