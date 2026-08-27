#!/usr/bin/env python3
"""Close the launcher consoles today's runs left sitting at `pause`.

Measured 2026-08-22: 20 cmd.exe + 26 conhost.exe + 16 OpenConsole.exe, about
540 MB across 62 processes, on a box with 2.8 GB free and a 5.2 GB judge model
that has to fit in it.

Matched on the COMMAND LINE, which names the .bat, not on the window title:
taskkill's title filter rejects a leading wildcard, and the launcher name sits
in the middle of "C:\\WINDOWS\\system32\\cmd.exe - AA_INTEGRATE_AND_RUN.bat".

Never touches: the node wrappers (their command line runs
run_with_ollama_judge.py), the watchdog, this process, or its own console.
"""
import os, subprocess, sys

LAUNCHERS = ("AA_INTEGRATE_AND_RUN", "AB_RESTART_NODES", "AC_COPY_SWEEP_LOGS",
             "AD_DIAG_PORTS", "AE_KILL_STRAY_START_B", "AF_RETEST",
             "AG_LEAN_MEASURE", "AH_FITCHECK", "AI_TOPMEM")
NEVER = ("run_with_ollama_judge", "covenant_watchdog", "AJ_CLEANUP",
         "cleanup_consoles")

ps = ("Get-CimInstance Win32_Process -Filter \"Name='cmd.exe'\" | "
      "ForEach-Object { \"$($_.ProcessId)`t$($_.CommandLine)\" }")
out = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                     capture_output=True, text=True).stdout

mine, spared, killed = [], [], []
for line in out.splitlines():
    if "\t" not in line:
        continue
    pid, _, cmdline = line.partition("\t")
    if not pid.strip().isdigit():
        continue
    pid = int(pid)
    if any(n in cmdline for n in NEVER):
        spared.append((pid, cmdline.strip()[:70])); continue
    if any(n in cmdline for n in LAUNCHERS):
        mine.append((pid, cmdline.strip()[:70]))

print("found {} leftover launcher console(s)".format(len(mine)))
for pid, c in mine:
    r = subprocess.run(["taskkill", "/f", "/t", "/pid", str(pid)],
                       capture_output=True, text=True)
    ok = r.returncode == 0
    killed.append(ok)
    print("  {} pid {:<7} {}".format("closed " if ok else "FAILED ", pid, c))
for pid, c in spared:
    print("  spared  pid {:<7} {}".format(pid, c))
print("closed {} of {}".format(sum(killed), len(mine)))
