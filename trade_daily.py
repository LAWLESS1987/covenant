#!/usr/bin/env python3
r"""
trade_daily.py -- the one command for the trading side.

  read both exchanges  ->  sync holdings.txt  ->  run the daily rule check

WHY IT EXISTS
  The chain was four commands in a required order, and the failure that
  actually happened on 2026-08-28 was not any one of them breaking. It was the
  chain not being run at all: holdings.txt went missing, the last copy on disk
  was nine days and four regime flips old, and nothing in the output said so.
  Every percentage still summed to 100%.

  So the one property this file guarantees is not speed. It is that a run on
  stale positions CANNOT look like a run on fresh ones.

WHAT IT DOES NOT DO
  It holds no key, places no order, and asks for no trade permission. The two
  balance readers it invokes each hold their own read-only credential, outside
  this folder. Every order remains yours, by hand, at the exchange.

USAGE
  python trade_daily.py                 read, sync, check
  python trade_daily.py --no-sync       read and check; show the diff, apply nothing
  python trade_daily.py --check-only    skip the exchanges entirely
  python trade_daily.py --push TOPIC    forward the daily summary to your phone
  python trade_daily.py --max-age 6     treat a balance file over 6h old as failed
"""
from __future__ import annotations
import os, sys, time, subprocess, argparse, datetime
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
HOLDINGS = os.path.join(HERE, "holdings.txt")

READERS = [("Kraken", "kraken_balance.py", os.path.join(os.path.expanduser("~"), ".kraken")),
           ("Coinbase", "coinbase_balance.py", os.path.join(os.path.expanduser("~"), ".coinbase"))]


def run(script, *args, quiet=True):
    """Invoke one of our own scripts. Returns (rc, combined output)."""
    p = subprocess.run([PY, os.path.join(HERE, script), *args],
                       capture_output=True, text=True, cwd=HERE)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def hr(title):
    print()
    print("=" * 74)
    print(title)
    print("=" * 74)


def holdings_age_h():
    """Age of the QUANTITIES, not of the file. Returns (hours, is_known).

    mtime is the wrong clock and dangerously so: copying, restoring or opening
    and re-saving the file all reset it while the numbers inside stay exactly
    as old as they were. On 2026-08-28 the restored file had an mtime minutes
    old and quantities from 2026-08-19 -- a nine-day gap that mtime reported as
    zero. sync_holdings.py stamps the real time into a header line; when that
    stamp is absent the honest answer is "unknown", never mtime.
    """
    if not os.path.exists(HOLDINGS):
        return None, False
    stamp = None
    for line in open(HOLDINGS, encoding="utf-8"):
        if not line.startswith("#"):
            break
        if "synced by sync_holdings.py at" in line:
            stamp = line.rsplit("at", 1)[-1].strip().rstrip(" from:").strip()
            break
    if stamp:
        try:
            t = datetime.datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=datetime.timezone.utc)
            return (datetime.datetime.now(datetime.timezone.utc) - t
                    ).total_seconds() / 3600.0, True
        except ValueError:
            pass
    return None, False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-sync", action="store_true",
                    help="show the holdings diff but do not apply it")
    ap.add_argument("--check-only", action="store_true",
                    help="skip the exchange readers entirely")
    ap.add_argument("--push", metavar="TOPIC", help="ntfy topic for the summary")
    ap.add_argument("--max-age", default="24",
                    help="hours before a balance file counts as failed")
    a = ap.parse_args()

    t0 = time.time()
    synced = False
    problems = []

    # ---------------------------------------------------------------- step 1
    if not a.check_only:
        hr("1/3  READING BOTH EXCHANGES")
        missing = [(n, d) for n, _s, d in READERS if not os.path.isdir(d)]
        for n, d in missing:
            print(f"  {n:<9} SKIPPED -- no credential directory at {d}")
            problems.append(f"{n}: no credential installed (see EXCHANGE_SETUP.md)")

        todo = [(n, s) for n, s, d in READERS if os.path.isdir(d)]
        if todo:
            # Both readers are network-bound and independent; there is no reason
            # for the second to wait on the first.
            with ThreadPoolExecutor(max_workers=len(todo)) as pool:
                results = list(pool.map(lambda t: (t[0], *run(t[1])), todo))
            for name, rc, out in results:
                if rc == 0:
                    total = [l for l in out.splitlines() if "TOTAL" in l]
                    print(f"  {name:<9} ok   {total[0].strip() if total else ''}")
                else:
                    first = next((l for l in out.splitlines() if l.strip()), "no output")
                    print(f"  {name:<9} FAILED -- {first.strip()[:90]}")
                    problems.append(f"{name}: reader failed")
    else:
        hr("1/3  EXCHANGES SKIPPED (--check-only)")

    # ---------------------------------------------------------------- step 2
    if not a.check_only:
        hr("2/3  SYNCING holdings.txt")
        args = ["--max-age", str(a.max_age)]
        rc, out = run("sync_holdings.py", *args)
        print("\n".join("  " + l for l in out.splitlines()[2:] if l.strip()))
        if rc == 0 and not a.no_sync:
            rc2, out2 = run("sync_holdings.py", *args, "--write")
            if rc2 == 0:
                synced = True
                print("\n  -> applied.")
            else:
                problems.append("sync refused on write")
        elif rc != 0:
            problems.append("holdings NOT synced -- see above")
        elif a.no_sync:
            print("\n  -> --no-sync: shown, not applied.")
    else:
        hr("2/3  SYNC SKIPPED (--check-only)")

    # ---------------------------------------------------------------- step 3
    hr("3/3  DAILY RULE CHECK")
    daily_args = ["--push", a.push] if a.push else []
    rc, out = run("daily.py", *daily_args)
    print(out.rstrip())

    # ------------------------------------------------------------- the point
    # This block is the reason the file exists. It runs LAST, after the report,
    # because a warning above a wall of numbers is a warning nobody reads.
    age, known = holdings_age_h()
    hr("POSITION FRESHNESS")
    if synced:
        print("  Positions came from the exchanges just now. The percentages,")
        print("  the 20% cap and the trim sizes above are current.")
    elif not os.path.exists(HOLDINGS):
        print("  !! holdings.txt DOES NOT EXIST. Nothing above is about your money.")
    else:
        print("  !! Positions were NOT refreshed this run.")
        if known:
            print(f"     The quantities were last synced from the exchanges "
                  f"{age:.1f}h ago ({age/24:.1f} days).")
        else:
            print("     The quantities carry NO sync stamp, so their true age is")
            print("     UNKNOWN. The file's timestamp is not an answer -- copying or")
            print("     re-saving it resets that while the numbers stay as old as")
            print("     they were. Treat them as unverified until a sync succeeds.")
        print()
        print("     Every percentage, every trim size and the 20% cap check above")
        print("     were computed from those quantities. Prices are live; the")
        print("     amounts you hold are not. If you have traded since, the")
        print("     numbers above are wrong in a way the report cannot detect.")
    if problems:
        print()
        print("  why it did not sync:")
        for p in problems:
            print(f"    - {p}")
    print()
    print(f"  [{time.time() - t0:.1f}s]  Nothing was traded. Every order is yours, by hand.")
    print("=" * 74)
    return 0 if synced or a.check_only else 3


if __name__ == "__main__":
    raise SystemExit(main())
