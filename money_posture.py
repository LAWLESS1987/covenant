#!/usr/bin/env python3
"""
money_posture.py -- what could this system do with money, right now?

WHY IT EXISTS

  exposure_check.py asks what the node exposes to the network. Nothing asked
  the equivalent question about money, and money is the one where a wrong
  answer is unrecoverable.

  The honest state is easy to misread in BOTH directions, which is exactly why
  it needs a checker rather than a paragraph:

    * Read CONSTITUTION.md II.1 -- "No trades placed by automation" -- and you
      would conclude no such capability exists. It does. venues.py holds order
      adapters (Kraken, Coinbase, Robinhood at the time of writing -- but this
      file COUNTS them rather than naming them, see below), covenant_trader.py
      plans orders, and a scheduled task runs it DAILY against the real venues.
    * Look at the scheduled task and the AddOrder call and you would conclude
      the thing is trading. It is not. Where the venue offers a server-side
      dry run (Kraken validate=true, Coinbase /orders/preview) every order
      goes there and is priced and rejected without booking; where it does
      not (Robinhood), the dry run is local and says so. The trader is
      disarmed besides.

  THE FIRST VERSION OF THIS FILE WAS WRONG THE DAY IT WAS WRITTEN. It named
  Kraken and Coinbase by hand and said "both default to the venue's own
  dry-run endpoint". Robinhood had been added to venues.py the day before,
  with no venue-side dry run at all. The checker meant to replace a paragraph
  had inherited the paragraph's blind spot. So the venue list is now read
  from venues.py, each adapter declares what its dry run reaches (DRY_RUN),
  and an adapter that declares nothing makes this exit 2 rather than 0.

  Both readings are wrong, and a document cannot fix that because the answer
  changes with a config flag. So this reports the LIVE state, and it is meant
  to be run by anyone evaluating the project rather than taken on trust.

WHAT IT REPORTS

  Whether the trader is armed, what the caps are, whether the halt file is
  present, whether a scheduled task will run it and when, which venues have
  credentials, and what the last run actually did.

WHAT IT DOES NOT DO

  It never reads an API key, never places or cancels anything, never arms or
  disarms. Read-only, and it deliberately cannot become the tool that arms the
  trader -- that has to stay a deliberate human edit to a config file.

USE
  python money_posture.py

Exit 0 disarmed (nothing can be booked), 1 ARMED, 2 could not determine --
and 2 is never read as 0.

LICENCE: Apache-2.0.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(HERE, "trader_config.json")
HALT = os.path.join(HERE, "TRADER_HALT")


def _run(cmd):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
        return (p.stdout or "") + (p.stderr or "")
    except Exception:                                        # noqa: BLE001
        return ""


def load_venues():
    """The adapters, from the module that defines them. Importing venues.py
    runs no network call and opens no credential: it defines classes whose
    constructors set a few Nones. If it cannot be imported that is reported
    as UNKNOWN rather than as 'no venues'."""
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    try:
        import venues as V                                   # noqa: N812
        return list(V.all_venues()), None
    except Exception as e:                                   # noqa: BLE001
        return [], "venues.py could not be imported: %s" % e


def load_cfg():
    try:
        with open(CFG, "r", encoding="utf-8") as fh:
            return json.load(fh), None
    except FileNotFoundError:
        return {}, "trader_config.json not present"
    except Exception as e:                                   # noqa: BLE001
        return {}, "trader_config.json unreadable: %s" % e


def main() -> int:
    print()
    print("  MONEY POSTURE -- what could this do with funds right now?")
    print("  " + "=" * 62)
    print("  Read-only. Reads no key, places nothing, arms nothing.")

    cfg, err = load_cfg()
    armed = bool(cfg.get("armed"))
    halted = os.path.exists(HALT)

    print()
    print("  THE ONE THAT DECIDES EVERYTHING")
    if err:
        print("      armed : UNKNOWN -- %s" % err)
        print("              cfg.get('armed') would be falsy, so orders would be")
        print("              blocked -- but 'absent' and 'false' are different")
        print("              facts and only one of them was written down.")
    else:
        print("      armed : %s" % ("TRUE  <-- live orders CAN be booked" if armed
                                    else "false  -- every order is blocked here"))
    print("      halt file (TRADER_HALT) : %s"
          % ("PRESENT -- everything blocked regardless" if halted else "absent"))

    if cfg:
        print()
        print("  BOUNDS, if it were armed")
        for k, label in (("max_order_usd", "per order"),
                         ("max_daily_notional_usd", "per day"),
                         ("max_orders_per_day", "orders per day"),
                         ("min_order_usd", "minimum order"),
                         ("min_sealed_signals", "sealed signals required first"),
                         ("seal_required", "decision must be sealed to chain")):
            if k in cfg:
                print("      %-32s %s" % (label, cfg[k]))

    print()
    print("  WILL ANYTHING RUN IT WITHOUT A HUMAN?")
    if sys.platform.startswith("win"):
        ps = ("Get-ScheduledTask -ErrorAction SilentlyContinue | ForEach-Object "
              "{ $a = ($_.Actions | ForEach-Object { $_.Execute + ' ' + "
              "$_.Arguments }) -join ' '; if ($a -match 'trader') { "
              "$i = Get-ScheduledTaskInfo -TaskName $_.TaskName; "
              "$_.TaskName + '|' + $_.State + '|' + $i.LastRunTime + '|' + "
              "$i.LastTaskResult + '|' + $i.NextRunTime } }")
        out = _run(["powershell", "-NoProfile", "-Command", ps]).strip()
        if not out:
            print("      No scheduled task invokes the trader. It runs only when")
            print("      a person runs it.")
        for line in out.splitlines():
            parts = line.strip().split("|")
            if len(parts) >= 5:
                print("      TASK %s  state=%s" % (parts[0], parts[1]))
                print("           last run %s (result %s), next %s"
                      % (parts[2], parts[3], parts[4]))
                print("           SO: this runs WITHOUT a human. What it does when")
                print("           it runs is decided entirely by 'armed' above.")
    else:
        print("      Not Windows -- cannot read the task scheduler here. UNKNOWN,")
        print("      which is not the same as 'nothing is scheduled'.")

    print()
    print("  VENUES -- every order adapter, and what its dry run reaches")
    # Enumerated from venues.py itself, never from a list written here. The
    # first version of this file named two venues by hand the day AFTER a
    # third had been added, and nothing noticed -- see the note at the top
    # of venues.py. has_credentials() is os.path.exists and nothing more;
    # no key is opened.
    venues, verr = load_venues()
    undeclared = []
    if verr:
        print("      UNKNOWN -- %s" % verr)
        print("      A checker that cannot see the adapters cannot vouch for")
        print("      them, and this one will not guess.")
    for v in venues:
        cred = ("credential file present" if v.has_credentials()
                else "no credential on this machine")
        mode = getattr(v, "DRY_RUN", None)
        if mode == "venue":
            how = ("dry run = VENUE-SIDE (%s): the exchange prices and"
                   % getattr(v, "DRY_RUN_ENDPOINT", "?"))
            tail = "rejects the order without booking it."
        elif mode == "local":
            how = "dry run = LOCAL ONLY: no preview endpoint exists, so"
            tail = "no matching engine or balance check ever sees it."
        else:
            undeclared.append(v.name)
            how = "dry run = UNDECLARED -- this adapter does not say what"
            tail = "live=False reaches, and this checker will not assume."
        print("      %-10s %s" % (v.name, cred))
        print("      %-10s %s" % ("", how))
        print("      %-10s %s" % ("", tail))
    if venues:
        weakest = ("local" if any(getattr(v, "DRY_RUN", None) == "local"
                                  for v in venues) else "venue")
        print("      %d adapter(s). Weakest dry run: %s."
              % (len(venues), weakest))
        if weakest == "local":
            print("      So a venue-side dry run is true of SOME orders, and a")
            print("      document saying that EVERY order reaches one is out of")
            print("      date.")

    print()
    print("  WHAT THE LAST RUN ACTUALLY DID")
    log = os.path.join(HERE, "trader_log.txt")
    if os.path.isfile(log):
        try:
            with open(log, "r", encoding="utf-8", errors="replace") as fh:
                tail = [l.rstrip() for l in fh.readlines()[-14:] if l.strip()]
            for l in tail[-6:]:
                print("      %s" % l[:96])
        except OSError:
            print("      trader_log.txt unreadable")
    else:
        print("      no trader_log.txt -- it has not run, or logs elsewhere.")

    print()
    print("  " + "-" * 62)
    if armed and not halted:
        print("  ARMED. Live orders can be booked within the bounds above.")
        print("  That is a legitimate state to be in, and it is NOT the state")
        print("  CONSTITUTION.md II.1 describes. If this reads ARMED, that")
        print("  clause needs rewriting before anyone is told otherwise.")
        return 1
    if verr or undeclared:
        # The docstring promises exit 2 is never read as 0. A posture this
        # checker could not fully see is not a posture it can call DISARMED.
        print("  COULD NOT DETERMINE. armed=%s and the halt file is %s, so no"
              % (armed, "present" if halted else "absent"))
        print("  order is being booked -- but the venue layer is only partly")
        print("  visible (%s), and a checker that reports a"
              % (verr or "undeclared dry run: " + ", ".join(undeclared)))
        print("  guarantee it did not read is the failure this file exists to")
        print("  catch. Exit 2, which is never read as 0.")
        return 2
    print("  DISARMED. Orders are built and, where the venue offers it, sent")
    print("  to its own dry-run endpoint, which prices and rejects them")
    print("  without booking. Nothing can move funds in this state.")
    print()
    print("  Stated plainly, because both mistakes are easy: the capability to")
    print("  place a real order EXISTS, is wired to %d real venue(s) (%s),"
          % (len(venues), ", ".join(v.name for v in venues)))
    print("  and runs daily. It is bounded by a flag, a halt file, per-order")
    print("  and per-day caps, and a seal requirement. 'It cannot' would be")
    print("  false; 'it is trading' would also be false. This is the true")
    print("  sentence.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
