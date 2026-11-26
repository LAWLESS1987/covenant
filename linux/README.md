# Covenant on Linux (Debian 13)

Started 2026-11-25 (A492), for running Covenant on the Debian towers. This
folder holds the Linux launchers. Ported so far: **2 of the 53 tracked `.bat`
files** (`covenant_prod.bat`, `TRADER_TASK.bat`), and **all 5 of the scheduled
tasks** that this repository registers on Windows. The other 3 Covenant tasks on
the operator's PC run from other folders (`site`, `covenant-adopt`) and are
not part of this repository.

## What works today

| Windows | Linux | Tested how |
|---|---|---|
| `covenant_prod.bat` | `linux/covenant_prod.sh` | `linux/test_covenant_prod_sh.sh`, with fake nodes, under WSL Ubuntu 26.04 |
| `covenant_prod.bat stop` | `linux/covenant_prod.sh stop` | same |
| `covenant_prod.bat status` | `linux/covenant_prod.sh status` | same |

The script has not yet started a real node on Debian. That happens on the
first tower, and until then the live start is **UNDETERMINED**.

## First run on a fresh Debian 13 machine

```sh
sudo apt install git python3 python3-venv curl
git clone https://github.com/LAWLESS1987/covenant.git && cd covenant
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
# copy genesis.json and covenant_A.db.key from the existing install (never commit them)
linux/covenant_prod.sh            # start
linux/covenant_prod.sh status
```

## Stop / remove

- **Stop:** `linux/covenant_prod.sh stop`. It ends the watchdog first, then the
  three nodes. Databases are untouched.
- **Nothing starts at boot.** This folder installs no service, timer or cron
  entry (the lesson of A14). If you add one yourself, remove it the same way
  you added it.
- **Remove completely:** stop it, then delete the `covenant` folder and
  `~/.covenant-keys`. The key folder holds the node's identity key, so keep a
  copy first if you ever want the same node back.

## Fixed for Linux (A492)

Three Windows-only paths broke under Linux. Each was found by running the code
there, and each is now fixed and tested by `test_a492_linux_paths.py`:

1. **`ops/hidden_task.py`** passed a Windows-only `creationflags`, so under
   Linux the child never ran and nothing was logged. It now passes the flag
   only on Windows, logs any launch failure, and refuses a `.bat` off Windows.
2. **`covenant_watchdog_guard.py`** asked `tasklist` whether the watchdog was
   alive, and under Linux got "no" for a running one. It now reads `/proc`.
3. **The watchdog's twin check** used PowerShell and skipped under Linux. It
   now lists processes from `/proc` and stops an older twin with TERM.

## Scheduled tasks (systemd user timers)

`linux/install_timers.sh` writes the five Windows tasks as systemd user
timers, on the Windows tasks' own schedules:

| Timer | Windows task | Runs | Time limit |
|---|---|---|---|
| `guard` | CovenantGuard | every 2 min | 10 min |
| `refine-check` | CovenantRefineCheck | every 15 min, at :03 | 10 min |
| `ambassador` | CovenantAmbassador | every 3 h: 02, 05, 08 ... 23 | 2 h 50 min |
| `distill` | CovenantDistill | daily 02:30 | 6 h |
| `trader` | CovenantTrader | daily 09:00 (`linux/trader_task.sh`) | 72 h |

```sh
linux/install_timers.sh install            # writes the units; enables NOTHING
linux/install_timers.sh enable guard,refine-check,distill
linux/install_timers.sh enable ambassador  # SENDS messages
linux/install_timers.sh enable trader      # TRADES
linux/install_timers.sh status
loginctl enable-linger "$USER"             # so timers run when nobody is logged in
```

Set the tower's time zone to the office's first (`sudo timedatectl set-timezone
America/Chicago`): the schedules are local time.

**Stop / remove timers:** `linux/install_timers.sh disable NAME` stops one.
`linux/install_timers.sh remove` disables all five and moves the unit files to
`logs/retired-units/`, never deleting them. `loginctl disable-linger "$USER"`
undoes lingering.

A timer has not yet run one of the real scripts on Debian; only fakes, under
WSL. The first tower decides it.

## Re-running the tests

From WSL or any Linux shell, at the repository root:

```sh
bash linux/test_covenant_prod_sh.sh "$PWD"
bash linux/mutate_covenant_prod_sh.sh "$PWD" "$PWD/linux/test_covenant_prod_sh.sh"
```

The first must end `0 failed`. The second breaks the script three ways on
purpose (no working-directory check, wrong stop order, wrong peers), and each
break must be `CAUGHT`. Both use throwaway copies in `/tmp` with fake nodes,
and start or stop nothing real.

The timers, the same way:

```sh
bash linux/test_install_timers_sh.sh "$PWD"
bash linux/mutate_install_timers_sh.sh "$PWD"
```

The test replaces `systemctl` with a logger, so nothing is installed or
enabled. It uses `systemd-analyze` to check the units and the calendars when it
is installed. The breaks: a plain install that enables everything, the
Ambassador schedule shifted to 00:00, and a remove that deletes instead of
moving aside.
