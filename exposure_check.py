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

LICENCE: Apache-2.0.
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


def _run(cmd: List[str]) -> Optional[str]:
    """The command's output, or None if it DID NOT RUN. A82 (2026-09-10).

    This returned "" for both, and every caller read "" as "measured, found
    nothing". Measured on this machine: with netstat reachable the tool printed
    four WILDCARD sockets and "REACHABLE ... on: private, public", exit 1; sixty
    seconds later, same binary and same source, with netstat merely not
    resolvable, it printed "Nothing listening on any covenant port. Nothing to
    expose." and exited 0. A 25s TimeoutExpired lands in the same "".

    That is the worst possible failure for THIS tool specifically: it exists to
    answer whether the operator's machine is reachable from the internet, and
    the answer it gave when it could not look was the reassuring one. The file
    says the rule itself twice -- "do not treat 'could not check' as 'not
    exposed'" at the platform branch, and "Treat as UNKNOWN, not as safe" when
    the program cannot be identified. _run defeated both.
    """
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
    except Exception:                                        # noqa: BLE001
        return None
    text = (out.stdout or "") + (out.stderr or "")
    # A non-zero exit with nothing to say is a command that did not do its job.
    # Genuinely empty output from a SUCCESSFUL command stays "", which is a
    # measurement, and callers may read it as one.
    if out.returncode != 0 and not text.strip():
        return None
    return text


def listeners() -> Optional[List[Dict[str, object]]]:
    """(address, port, pid) for every LISTENING socket on a covenant port.

    None means netstat DID NOT RUN -- unknown, not empty. [] means it ran and
    matched nothing, which is a real measurement (A82).
    """
    text = _run(["netstat", "-ano"])
    if text is None:
        return None
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


def allowing_rules(program: str) -> Optional[List[Tuple[str, str]]]:
    """(rule name, profiles) for enabled inbound Allow rules naming `program`.

    None means netsh DID NOT RUN. [] means it ran and no enabled inbound Allow
    rule names this program -- which main() renders as "likely NOT reachable",
    a sentence that must never be printed on the strength of a failed command
    (A82). Measured: with netsh reachable this returned four real Private and
    Public ALLOW rules; with it unreachable, [].
    """
    text = _run(["netsh", "advfirewall", "firewall", "show", "rule",
                 "name=all", "dir=in", "verbose"])
    if text is None:
        return None
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
    if live is None:
        # Exit 2 is this file's existing code for "this check could not run",
        # used by the platform branch above. (The `not programs` branch below
        # predates A82 and returns 1 for its own UNKNOWN; both are non-zero, so
        # nothing that asks "did this pass" is misled either way.)
        print("  COULD NOT RUN netstat, so what is listening is UNKNOWN.")
        print("  This is NOT a clean result. Do not read it as 'nothing to")
        print("  expose' -- that is the sentence this branch exists to prevent.")
        return 2
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
    unknown_firewall = False
    for prog in sorted(programs):
        rules = allowing_rules(prog)
        print("    %s" % prog)
        if rules is None:
            print("      COULD NOT READ the firewall rules for this program")
            print("      (netsh did not run). Whether anything off this machine")
            print("      can reach it is UNKNOWN, and unknown is not safe.")
            unknown_firewall = True
            continue
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
        print("  Consequence, stated at its true size: any other device on a")
        print("  network of that type can READ the ledger, node health, peers")
        print("  and stakes.")
        if "public" in profs:
            print("  'Public' includes coffee shops, hotels and airports.")
        print()
        print("  What this is NOT, tested rather than assumed on 2026-08-30:")
        print("  the write surface is gated. POST /mine, /sync, /peers and")
        print("  /crisis/clear all return 401 without operator headers, and")
        print("  /transactions, /stake, /unstake, /claim_rewards and")
        print("  /propose_code all refuse a missing signature. A stranger can")
        print("  make their own keypair, but it holds no balance and moves")
        print("  nothing. An earlier version of this file called that")
        print("  'unauthenticated attack surface'. That was an overstatement")
        print("  carried forward without being re-checked, and one command")
        print("  settled it.")
        print()
        print("  So this is read exposure. Whether that matters is a judgement")
        print("  about the two things that are NOT published ledger content:")
        print("  /health returns operational internals, and /peers returns")
        print("  topology. The chain itself is meant to be readable.")
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

    if unknown_firewall:
        # THE SENTENCE BELOW MUST NOT BE PRINTED ON A FAILED COMMAND (A82).
        # "Probably not reachable" is a claim about the firewall, and if netsh
        # did not run for even one serving program then nobody looked at it.
        # Measured before the fix: netsh unreachable produced exactly this
        # reassuring paragraph on a machine certified REACHABLE on the public
        # profile one minute earlier.
        print("  UNKNOWN, not safe: the sockets are wildcard-bound and the")
        print("  firewall rules for at least one serving program could not be")
        print("  read. Nothing here says whether they are reachable. Check")
        print("  from another device, or re-run when netsh is available.")
        return 2

    print("  Probably not reachable: sockets are wildcard-bound, but no")
    print("  enabled inbound Allow rule names the serving program. Windows")
    print("  denies inbound by default. Verify from another device before")
    print("  relying on this.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
