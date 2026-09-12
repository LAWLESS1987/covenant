#!/usr/bin/env python3
"""test_m4_usb_link.py -- M4: the USB-C cable tool decides correctly from what adb
says, and never does more than it promises.

mobile/usb_link.py installs the app over a data cable and tunnels the node's
ports so phone and PC peer with no Wi-Fi and no firewall rule. It shells out to
adb for everything, so every decision it makes is a function of adb's output --
and that is what this suite feeds it. A STUB adb (a .cmd on Windows, a .sh
elsewhere) prints whatever device list a case needs and records every argument
list it was called with, so the checks below read what the tool DID, not what
its source says. No phone, no download, no network: the stub is passed with
--adb, so ensure_adb never looks further.

Runs IN PLACE (it reads mobile/usb_link.py, which the sweep's scratch copy does
not carry). Exit 0 = pass, 1 = fail.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "mobile", "usb_link.py")
results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("ok    " if ok else "FAIL  ") + name + (("  " + str(detail)[:200]) if (detail and not ok) else ""))


def make_stub(tmp, devices_text, install_text="Success\n"):
    """A fake adb: prints DEVICES_TEXT for `devices -l`, INSTALL_TEXT for
    `install`, nothing for anything else; appends every argv to calls.jsonl."""
    log = os.path.join(tmp, "calls.jsonl")
    py = os.path.join(tmp, "stub.py")
    with open(py, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(
            "import json, sys\n"
            "args = sys.argv[1:]\n"
            "open(%r, 'a', encoding='utf-8').write(json.dumps(args) + '\\n')\n"
            "if args[:2] == ['devices', '-l'] or args[:1] == ['devices']:\n"
            "    sys.stdout.write(%r)\n"
            "elif 'install' in args:\n"
            "    sys.stdout.write(%r)\n"
            "sys.exit(0)\n" % (log, devices_text, install_text))
    if os.name == "nt":
        stub = os.path.join(tmp, "adb.cmd")
        with open(stub, "w", encoding="utf-8", newline="\r\n") as fh:
            fh.write('@echo off\r\n"%s" "%s" %%*\r\n' % (sys.executable, py))
    else:
        stub = os.path.join(tmp, "adb")
        with open(stub, "w", encoding="utf-8", newline="\n") as fh:
            fh.write('#!/bin/sh\nexec "%s" "%s" "$@"\n' % (sys.executable, py))
        os.chmod(stub, 0o755)
    return stub, log


def run_tool(stub, *args):
    p = subprocess.run([sys.executable, TOOL, "--adb", stub, "--no-download"] + list(args),
                       capture_output=True, text=True, timeout=120, cwd=HERE)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def calls(log):
    if not os.path.exists(log):
        return []
    return [json.loads(l) for l in open(log, encoding="utf-8") if l.strip()]


def main():
    ok = subprocess.run([sys.executable, "-m", "py_compile", TOOL], capture_output=True).returncode == 0
    check("M4.0 mobile/usb_link.py compiles", ok)

    # --- the port arithmetic that would have collided -----------------------
    sys.path.insert(0, os.path.join(HERE, "mobile"))
    import usb_link as U
    check("M4.1 the phone-side tunnel port is NOT the phone node's own peer port (5001)",
          U.PHONE_SIDE_TO_PC[0] != "5001" and U.PHONE_SIDE_TO_PC[1] == "5001", U.PHONE_SIDE_TO_PC)
    check("M4.1b the PC-side tunnel port is NOT node A's API port (5000)",
          U.PC_SIDE_TO_PHONE[0] != "5000" and U.PC_SIDE_TO_PHONE[1] == "5000", U.PC_SIDE_TO_PHONE)

    with tempfile.TemporaryDirectory() as tmp:
        # --- no phone ---------------------------------------------------------
        stub, log = make_stub(tmp, "List of devices attached\n\n")
        rc, out = run_tool(stub, "status")
        check("M4.2 no device -> exit 2 and it says to use a DATA cable and enable USB debugging",
              rc == 2 and "DATA cable" in out and "USB debugging" in out, out[-300:])
        rc, out = run_tool(stub, "link")
        check("M4.2b no device -> link refuses (exit 2) and calls no reverse/forward",
              rc == 2 and not any("reverse" in c or "forward" in c for c in calls(log)), calls(log))

    with tempfile.TemporaryDirectory() as tmp:
        # --- unauthorised phone --------------------------------------------------
        stub, log = make_stub(tmp, "List of devices attached\nR5CX1234ABC\tunauthorized\n\n")
        rc, out = run_tool(stub, "link")
        check("M4.3 unauthorised -> exit 2, tells the user to accept 'Allow USB debugging' on the phone",
              rc == 2 and "Allow USB debugging" in out, out[-300:])
        check("M4.3b ...and touched no tunnel", not any("reverse" in c or "forward" in c for c in calls(log)), calls(log))

    with tempfile.TemporaryDirectory() as tmp:
        # --- one authorised phone: link ------------------------------------------
        stub, log = make_stub(tmp, "List of devices attached\nR5CX1234ABC\tdevice product:x model:y\n\n")
        rc, out = run_tool(stub, "link")
        c = calls(log)
        rev = [x for x in c if "reverse" in x]
        fwd = [x for x in c if "forward" in x]
        check("M4.4 one device -> link exits 0", rc == 0, out[-300:])
        check("M4.4b it ran exactly one adb reverse, addressed to that serial, phone 15001 -> PC 5001",
              rev == [["-s", "R5CX1234ABC", "reverse", "tcp:15001", "tcp:5001"]], rev)
        check("M4.4c it ran exactly one adb forward, PC 15000 -> phone 5000",
              fwd == [["-s", "R5CX1234ABC", "forward", "tcp:15000", "tcp:5000"]], fwd)
        check("M4.4d it tells the phone which PC_PEER to use over the cable",
              "PC_PEER=127.0.0.1:15001" in out, out[-400:])
        check("M4.4e a phone node that is not running yet is reported as normal, not as failure",
              rc == 0 and "not answering yet" in out, out[-400:])

    with tempfile.TemporaryDirectory() as tmp:
        # --- two authorised phones: refuse to guess ------------------------------
        stub, log = make_stub(tmp, "List of devices attached\nAAA\tdevice\nBBB\tdevice\n\n")
        rc, out = run_tool(stub, "link")
        check("M4.5 two devices -> refuses (exit 2) and names both",
              rc == 2 and "AAA" in out and "BBB" in out and not calls(log)[1:], out[-300:])

    with tempfile.TemporaryDirectory() as tmp:
        # --- install ----------------------------------------------------------------
        stub, log = make_stub(tmp, "List of devices attached\nR5CX1234ABC\tdevice\n\n")
        rc, out = run_tool(stub, "install", os.path.join(tmp, "missing.apk"))
        check("M4.6 install with a missing file -> exit 2 before touching adb install",
              rc == 2 and not any("install" in x for x in calls(log)), out[-200:])
        apk = os.path.join(tmp, "covenant.apk")
        open(apk, "wb").write(b"PK\x03\x04" + b"\0" * 64)
        rc, out = run_tool(stub, "install", apk)
        inst = [x for x in calls(log) if "install" in x]
        check("M4.6b install -> adb install -r FILE, addressed to the serial",
              rc == 0 and inst == [["-s", "R5CX1234ABC", "install", "-r", apk]], inst)
        check("M4.6c ...and NEVER -g (grant-all-permissions)", not any("-g" in x for x in inst), inst)

    with tempfile.TemporaryDirectory() as tmp:
        # --- install that the phone refused ------------------------------------
        stub, log = make_stub(tmp, "List of devices attached\nR5CX1234ABC\tdevice\n\n",
                              install_text="Failure [INSTALL_FAILED_USER_RESTRICTED]\n")
        apk = os.path.join(tmp, "covenant.apk"); open(apk, "wb").write(b"PK" + b"\0" * 64)
        rc, out = run_tool(stub, "install", apk)
        check("M4.7 a refused install -> exit 4 and the phone's own reason is shown",
              rc == 4 and "INSTALL_FAILED_USER_RESTRICTED" in out, out[-300:])

    with tempfile.TemporaryDirectory() as tmp:
        # --- unlink ------------------------------------------------------------------
        stub, log = make_stub(tmp, "List of devices attached\n\n")
        rc, out = run_tool(stub, "unlink")
        c = calls(log)
        check("M4.8 unlink removes all reverse and forward tunnels",
              rc == 0 and ["reverse", "--remove-all"] in c and ["forward", "--remove-all"] in c, c)

    # --- no adb and no permission to fetch one --------------------------------------
    p = subprocess.run([sys.executable, TOOL, "--adb", os.path.join(tempfile.gettempdir(), "no-such-adb"),
                        "--no-download", "status"], capture_output=True, text=True, timeout=60, cwd=HERE,
                       env={**os.environ, "PATH": tempfile.gettempdir()})
    exists_locally = os.path.exists(os.path.join(HERE, "tools", "platform-tools"))
    check("M4.9 with --no-download and no adb on --adb/PATH, exit 3 (or 0/2 when tools/platform-tools is present locally)",
          (p.returncode == 3) or (exists_locally and p.returncode in (0, 2)), (p.returncode, p.stdout[-200:]))

    n = len(results); good = sum(results)
    print("\nM4: %d/%d passed" % (good, n))
    return 0 if good == n else 1


if __name__ == "__main__":
    sys.exit(main())
