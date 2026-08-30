#!/usr/bin/env python3
"""
exposure_check.py -- ask the node the question it never asks itself.

WHY THIS EXISTS

  The node already watches a great deal. anomaly_monitor records rejected
  transaction shapes, an unavailable judge, ethics-gate denials. /health
  reports degraded state, dead peers, anomaly kinds. A watchdog revives dead
  nodes. There is even a preflight port check at startup.

  All of it watches PEERS and TRAFFIC. None of it watches the node's own
  posture. It will tell you a peer went quiet. It will not tell you it is
  serving the whole ledger to anyone on the same wifi.

  The hook was already there and one question short. preflight_port_check asks
  "is this port free?" It never asks "should I be reachable from off this
  machine?"

  By the project's own test -- who is worse off if this works? -- a node that
  silently exposes its operator fails. There is an ethics gate on what flows
  through the system and nothing checking what the system exposes.

WHAT IT REPORTS

  For each covenant port: whether anything is listening, whether it is bound to
  a wildcard address rather than loopback, whether the host firewall permits
  inbound to the program serving it, and therefore whether a stranger on the
  same network can read the ledger.

  It states the reachable/not-reachable conclusion only when it can support it.
  Where it cannot determine something it says so rather than guessing, because
  a security tool that guesses reassuringly is worse than no tool.

WHAT IT DOES NOT DO

  It changes nothing. No firewall rule is added, edited or removed, no process
  is stopped, no configuration is written. Modifying a machine's security
  posture is the operator's act, made knowingly. This prints the exact command
  and stops.

  Read-only by construction, so it is safe to run at any time, including on a
  machine you do not own.

USE
  python exposure_check.py

LICENCE: public domain.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from typing import Dict, List, Optional, Set, Tuple

# The node binds `port` and `port + 10` (see the two socket binds in
# covenant_unified_v8.py), so both belong in scope.
BASE_PORTS = [5000, 5020, 5040, 5060, 5100, 5120, 5140]
PORTS = sorted({p for b in BASE_PORTS for p in (b, b + 10)})

LOOPBACK = {"127.0.0.1", "::1", "localhost"}


def _run(cmd: List[str]) -> str:
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
        return (out.stdout or "") + (out.stderr or "")
    except Exception:                                        # noqa: BLE001
        return ""


def listeners() -> List[Dict[str, object]]:
    """(address, port, pid) for every LISTENING socket on a covenant port."""
    text = _run(["netstat", "-ano"])
    if not text:
        return []
    found = []
    for line in text.splitlines():
        if "LISTENING" not in line:
            continue
        parts = line.split()
        if len(parts) < 5:
            continue
        local, pid = parts[1], parts[-1]
        m = re.match(r"^(.*):(\d+)$", local)
        if not m:
            continue
        addr, port = m.group(1), int(m.group(2))
        if port in PORTS:
            found.append({"addr": addr, "port": port, "pid": pid,
                          "wildcard": addr in ("0.0.0.0", "[::]", "*", "::")})
    return found


def program_for(pid: str) -> Optional[str]:
    out = _run(["powershell", "-NoProfile", "-Command",
                "(Get-Process -Id %s -ErrorAction SilentlyContinue).Path" % pid])
    out = out.strip()
    return out or None


def allowing_rules(program: str) -> List[Tuple[str, str]]:
    """(rule name, profiles) for enabled inbound Allow rules naming `program`."""
    text = _run(["netsh", "advfirewall", "firewall", "show", "rule",
                 "name=all", "dir=in", "verbose"])
    if not text:
        return []
    hits, block, target = [], [], os.path.basename(program).lower()
    for line in text.splitlines() + ["Rule Name:"]:
        if line.startswith("Rule Name:") and block:
            joined = "\n".join(block)
            low = joined.lower()
            if (target in low and "action:" in low
                    and re.search(r"action:\s*allow", low)
                    and re.search(r"enabled:\s*yes", low)):
                name = re.search(r"Rule Name:\s*(.+)", joined)
                prof = re.search(r"Profiles:\s*(.+)", joined)
                hits.append(((name.group(1).strip() if name else "?"),
                             (prof.group(1).strip() if prof else "?")))
            block = []
        block.append(line)
    return hits


def main() -> int:
    if not sys.platform.startswith("win"):
        print("  This check reads Windows firewall state and only runs there.")
        print("  On other systems, inspect the equivalent yourself; do not")
        print("  treat 'could not check' as 'not exposed'.")
        return 2

    print()
    print("  COVENANT EXPOSURE CHECK -- read-only, changes nothing")
    print("  " + "-" * 60)

    live = listeners()
    if not live:
        print("  Nothing listening on any covenant port. Nothing to expose.")
        return 0

    programs: Set[str] = set()
    print()
    print("  Listening:")
    wildcard_ports = []
    for L in live:
        flag = "WILDCARD" if L["wildcard"] else "loopback"
        print("    %-16s port %-6s pid %-8s %s"
              % (L["addr"], L["port"], L["pid"], flag))
        if L["wildcard"]:
            wildcard_ports.append(int(L["port"]))
        p = program_for(str(L["pid"]))
        if p:
            programs.add(p)

    if not wildcard_ports:
        print()
        print("  All covenant sockets are on loopback. Nothing off this")
        print("  machine can reach them regardless of firewall state.")
        return 0

    print()
    print("  %d socket(s) bound to a wildcard address, meaning the node will"
          % len(wildcard_ports))
    print("  accept connections arriving on ANY network interface, not just")
    print("  from this machine. Whether that is reachable depends on the")
    print("  firewall, which is the next question.")

    if not programs:
        print()
        print("  COULD NOT DETERMINE which program serves these sockets, so")
        print("  the firewall question cannot be answered. Treat as UNKNOWN,")
        print("  not as safe.")
        return 1

    print()
    print("  Firewall:")
    permitted = []
    for prog in sorted(programs):
        rules = allowing_rules(prog)
        print("    %s" % prog)
        if not rules:
            print("      no enabled inbound Allow rule names this program.")
            print("      Windows blocks inbound by default, so this is likely")
            print("      NOT reachable -- but a rule could permit it by other")
            print("      means. Not proof.")
            continue
        for name, prof in rules:
            print("      ALLOW  %-28s profiles: %s" % (name[:28], prof))
            permitted.append(prof)

    print()
    if permitted:
        profs = {p.strip().lower() for row in permitted for p in row.split(",")}
        print("  REACHABLE. A program serving these ports is permitted inbound")
        print("  on: %s" % ", ".join(sorted(profs)))
        print()
        print("  Consequence, plainly: any other device on a network of that")
        print("  type can read the ledger, node health, peers and stakes.")
        if "public" in profs:
            print("  'Public' includes coffee shops, hotels and airports.")
        print("  Writes appeared authenticated when last tested, so this is")
        print("  read exposure plus unauthenticated attack surface, rather")
        print("  than an open write path. That is a mitigation, not a defence.")
        print()
        print("  Close it, in an admin prompt, having read it:")
        print()
        print("    netsh advfirewall firewall add rule "
              "name=\"Covenant nodes - block inbound\" dir=in action=block "
              "protocol=TCP localport=%s"
              % ",".join(str(p) for p in sorted(wildcard_ports)))
        print()
        print("  Durable fix: bind 127.0.0.1 instead of 0.0.0.0 in")
        print("  covenant_unified_v8.py. Needs a chain restart, and costs")
        print("  nothing while every node runs on this one machine.")
        return 1

    print("  Probably not reachable: sockets are wildcard-bound, but no")
    print("  enabled inbound Allow rule names the serving program. Windows")
    print("  denies inbound by default. Verify from another device before")
    print("  relying on this.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
