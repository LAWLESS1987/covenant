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
import re
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


def _run_rc(cmd):
    """(ok, text). ok is False when the command could not start or exited non-zero. A479 (2026-11-23): the scheduler
    listing went through _run, which returns "" on any failure, and "" printed as "No scheduled task invokes the
    trader" -- a listing that failed read as a confident none."""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
        return p.returncode == 0, (p.stdout or "") + (p.stderr or "")
    except Exception as e:                                   # noqa: BLE001
        return False, "%s: %s" % (type(e).__name__, str(e)[:120])


def scheduler_lines(is_win, listed_ok, listing, last_run_hdr, log_ymd, log_found):
    """The lines of WILL ANYTHING RUN IT WITHOUT A HUMAN, from the scheduler listing. Pure, so every branch is tested
    on every platform (A479). Every branch prints 'last ATTEMPT' and 'last RUN per trader_log.txt' (V2 A12): before
    A479 a Windows machine with no trader task printed neither, and a failed listing printed 'no task'."""
    run_line = "           last RUN per trader_log.txt: %s" % (
        last_run_hdr or ("none found" if log_found else "none (there is no trader_log.txt)"))
    if not is_win:
        return ["      Not Windows -- cannot read the task scheduler here. UNKNOWN,",
                "      which is not the same as 'nothing is scheduled'.",
                "           last ATTEMPT unknown (no scheduler read on this platform)",
                run_line]
    rows, unread = [], []
    for line in (listing or "").splitlines():
        if not line.strip():
            continue
        parts = [x.strip() for x in line.strip().split("|")]
        (rows if len(parts) >= 5 else unread).append(parts if len(parts) >= 5 else line.strip())
    if not listed_ok or (unread and not rows):
        why = (unread[0] if unread else (listing or "no output").strip())[:90]
        return ["      The task scheduler could not be read (%s). UNKNOWN," % why,
                "      which is not the same as 'nothing is scheduled'.",
                "           last ATTEMPT unknown (the scheduler was not read)",
                run_line]
    out = []
    if not rows:
        out += ["      No scheduled task invokes the trader. Services, Run keys and the",
                "      Startup folder are not read here, so this does not show that only",
                "      a person runs it.",
                "           last ATTEMPT none on record (no scheduled task invokes it now; an",
                "           earlier, since-deleted task would not show here)",
                run_line]
    for parts in rows:
        name, state, last, code, nxt = parts[:5]
        missed = parts[5] if len(parts) > 5 else "?"
        no_batt = parts[6] if len(parts) > 6 else "?"
        catch_up = parts[7] if len(parts) > 7 else "?"
        wake = parts[8] if len(parts) > 8 else "?"
        kind, why = decode_task_result(code)
        try:
            code_hex = "0x%08X" % (int(code, 0) & 0xFFFFFFFF)
        except (TypeError, ValueError):
            code_hex = repr(code)
        attempt_ymd = None
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})", last)
        if m:
            attempt_ymd = tuple(int(g) for g in m.groups())
        out += ["      TASK %s  state=%s" % (name, state),
                "           last ATTEMPT %s -> %s (%s)" % (last or "none", kind.upper(), code_hex),
                "           %s" % why,
                run_line,
                "           %s" % attempt_vs_log(attempt_ymd, kind, log_ymd),
                "           next %s; scheduler's missed-run counter %s" % (nxt or "none", missed),
                "           conditions: no start on battery=%s, catch up a "
                "missed start=%s, wake to run=%s" % (no_batt, catch_up, wake),
                "           SO: it runs WITHOUT a human -- on a day this machine",
                "           is awake, logged on and on mains at the trigger time.",
                "           A day it is not is skipped, and the counter above",
                "           stays 0. What it does when it runs is decided",
                "           entirely by 'armed' above."]
    if unread and rows:
        out.append("      %d line(s) of the scheduler listing could not be read; UNKNOWN for them." % len(unread))
    return out


# Task Scheduler's LastTaskResult is an HRESULT, and the one this file first
# printed raw -- 2147946720 -- reads as "last run today" to anyone who does not
# happen to know it is 0x800710E0, "the operator or administrator has refused
# the request": the scheduler considered launching the task and declined,
# because a condition on the task (AC power, interactive logon, idle) was not
# met. Nothing ran. On 2026-09-02 that number sat next to a LastRunTime six
# minutes after the laptop woke from a sleep that had swallowed the 09:00
# trigger -- measured on 2026-09-02: the scheduler's post-resume sweep stamped
# seven tasks in the same second, and the one attribute separating the three
# refused from the four that ran was StartWhenAvailable=False ("run as soon
# as possible after a missed start" unchecked). trader_log.txt had not been
# written since the day before. A
# checker that prints "last run <today>" over a day the trader did not run is
# this project's failure mode with a timestamp on it. So: decode, and compare
# against the log the run would have written.
TASK_RESULTS = {
    0x00000000: ("ran", "the last launch ran and exited 0"),
    0x00041300: ("ready", "ready; has not run since it was registered"),
    0x00041301: ("running", "an instance is running right now"),
    0x00041302: ("disabled", "the task is disabled"),
    0x00041303: ("never", "the task has never run"),
    0x00041304: ("no-more-runs", "no more scheduled runs"),
    0x00041306: ("terminated", "the last run was terminated"),
    0x800710E0: ("refused", "the launch was REFUSED by the scheduler: a start "
                            "that was missed (machine asleep) was rejected "
                            "because catch-up is off, or a condition (AC "
                            "power, logon, idle) was not met. Nothing ran."),
}


def decode_task_result(code):
    """(kind, sentence) for a LastTaskResult. Unknown non-zero codes are
    reported as such rather than guessed; a code that came back unparseable is
    'unknown' too, never 'ran'."""
    try:
        n = int(str(code).strip(), 0) & 0xFFFFFFFF
    except (TypeError, ValueError):
        return "unknown", "result %r could not be read" % (code,)
    if n in TASK_RESULTS:
        return TASK_RESULTS[n]
    if n < 0x100:
        return "exited", ("the run started and its program exited %d -- "
                          "read trader_log.txt" % n)
    return "unknown", "result 0x%08X is not one this checker knows" % n


_LOG_HEADER = re.compile(r"^==== (.*?) ====\s*$", re.M)
_US_DATE = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})")


def last_log_run(text):
    """The last '==== %DATE% %TIME% ====' header TRADER_TASK.bat appends before
    every run, or None. This is what a run leaves behind; the scheduler's
    LastRunTime is what an ATTEMPT leaves behind, and they are not the same."""
    heads = _LOG_HEADER.findall(text or "")
    return heads[-1].strip() if heads else None


def log_run_date(header):
    """(y, m, d) from a header in the US %DATE% form, else None -- 'cannot
    compare' is reported as such rather than as 'they match'."""
    m = _US_DATE.search(header or "")
    if not m:
        return None
    mo, d, y = (int(g) for g in m.groups())
    return (y, mo, d)


def attempt_vs_log(attempt_ymd, kind, log_ymd):
    """The sentence that keeps an attempt and a run apart. attempt_ymd is
    from the scheduler's LastRunTime; log_ymd from trader_log.txt's last
    header; kind from decode_task_result."""
    if attempt_ymd is None:
        return "no attempt recorded by the scheduler."
    if log_ymd is None:
        return ("cannot compare with trader_log.txt (no dated run header), so "
                "whether the attempt above produced a run is UNKNOWN.")
    if kind == "ran" and log_ymd == attempt_ymd:
        return "the attempt above is the run the log shows. They agree."
    if log_ymd == attempt_ymd:
        return ("the log shows a run that day, but the scheduler's result is "
                "not 0 -- read trader_log.txt before believing either.")
    return ("the attempt above did NOT produce a run -- the last run the log "
            "shows is %04d-%02d-%02d. A day the trader was due and did not "
            "run is silent everywhere else." % log_ymd)


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

    # BOUNDS ARE REPORTED EVEN WITHOUT A CONFIG. This used to print nothing
    # when trader_config.json was absent -- which is the normal state, since
    # the file is per-operator and deliberately unshipped -- while the caps
    # were being enforced from guards.CAP_DEFAULTS all the same. A posture
    # report that says nothing about the bounds in force is the exact failure
    # this file exists to catch: a document claiming less than the code does is
    # as misleading as one claiming more.
    try:
        import guards as _g
        fallback = dict(_g.CAP_DEFAULTS)
    except Exception:                                              # noqa: BLE001
        fallback = {}
    print()
    print("  BOUNDS, if it were armed")
    for k, label in (("max_order_usd", "per order"),
                     ("max_daily_notional_usd", "per day"),
                     ("max_orders_per_day", "orders per day"),
                     ("min_order_usd", "minimum order"),
                     ("min_sealed_signals", "sealed signals required first"),
                     ("seal_required", "decision must be sealed to chain")):
        if cfg and k in cfg:
            print("      %-32s %s" % (label, cfg[k]))
        elif k in fallback:
            print("      %-32s %s   (guards.CAP_DEFAULTS; no trader_config.json)"
                  % (label, fallback[k]))
        else:
            print("      %-32s unset" % label)

    print()
    print("  WILL ANYTHING RUN IT WITHOUT A HUMAN?")
    log_path = os.path.join(HERE, "trader_log.txt")
    log_text = ""
    if os.path.isfile(log_path):
        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as fh:
                log_text = fh.read()
        except OSError:
            log_text = ""
    last_run_hdr = last_log_run(log_text)
    log_ymd = log_run_date(last_run_hdr)
    listed_ok, out = False, ""
    if sys.platform.startswith("win"):
        ps = ("Get-ScheduledTask -ErrorAction SilentlyContinue | ForEach-Object "
              "{ $a = ($_.Actions | ForEach-Object { $_.Execute + ' ' + "
              "$_.Arguments }) -join ' '; if ($a -match 'trader') { "
              "$i = Get-ScheduledTaskInfo -TaskName $_.TaskName; $st = $_.Settings; "
              "$lr = if ($i.LastRunTime) { $i.LastRunTime.ToString('yyyy-MM-dd HH:mm:ss') } else { '' }; "
              "$nr = if ($i.NextRunTime) { $i.NextRunTime.ToString('yyyy-MM-dd HH:mm:ss') } else { '' }; "
              "$_.TaskName + '|' + $_.State + '|' + $lr + '|' + "
              "$i.LastTaskResult + '|' + $nr + '|' + $i.NumberOfMissedRuns + '|' + "
              "$st.DisallowStartIfOnBatteries + '|' + $st.StartWhenAvailable + '|' + "
              "$st.WakeToRun } }")
        listed_ok, out = _run_rc(["powershell", "-NoProfile", "-Command", ps])
    for line in scheduler_lines(sys.platform.startswith("win"), listed_ok, out, last_run_hdr, log_ymd,
                                os.path.isfile(log_path)):
        print(line)

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
    if verr or undeclared:
        # ORDER MATTERS, AND IT WAS WRONG UNTIL 2026-09-07. This check used to
        # come AFTER the armed check, so an armed trader whose venue layer
        # could not be read printed "ARMED. Live orders can be booked within
        # the bounds above" and returned 1 -- asserting bounds this checker had
        # just failed to read. Being unable to see the guarantee is a statement
        # about what was measured, and it outranks any statement about what
        # was found. Armed AND unreadable is the worst combination available,
        # not a milder one. test_v2_venue_guarantee P4/P6 caught this the day
        # the trader was first armed.
        print("  COULD NOT DETERMINE. armed=%s and the halt file is %s."
              % (armed, "present" if halted else "absent"))
        if armed and not halted:
            print("  This is the ARMED case with an unreadable venue layer, which")
            print("  is the worst of the two and is why it is reported first.")
        else:
            print("  No order is being booked in this state.")
        print("  The venue layer is only partly visible (%s),"
              % (verr or "undeclared dry run: " + ", ".join(undeclared)))
        print("  and a checker that reports a guarantee it did not read is the")
        print("  failure this file exists to catch. Exit 2, never read as 0.")
        return 2
    if armed and not halted:
        # UPDATED 2026-09-09. This used to say ARMED "is NOT the state
        # CONSTITUTION.md II.1 describes" and that the clause needed rewriting.
        # It did need rewriting, it WAS rewritten on 2026-09-07, and this
        # message was left behind -- so the tool whose job is catching drift
        # between the documents and the machine had drifted itself, and went on
        # reporting a conflict that had already been resolved.
        print("  ARMED. Live orders can be booked within the bounds above.")
        print("  This is PERMITTED by CONSTITUTION.md II.1 as amended 2026-09-07:")
        print("  'Now permitted: automated placement by covenant_trader.py, and")
        print("  by nothing else.' Armed is a recorded, approved state -- not a")
        print("  breach, and not a surprise. Exit 1 still marks it as the state")
        print("  that deserves a second look every time it is read.")
        return 1
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
