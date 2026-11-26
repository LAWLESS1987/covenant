# Covenant on Linux (Debian 13)

Started 2026-11-25 (A492), for running Covenant on the Debian towers. This
folder holds the Linux launchers. Ported so far: **2 of the 53 tracked `.bat`
files** (`covenant_prod.bat`, `TRADER_TASK.bat`), and **all 8 Covenant scheduled
tasks** on the operator's PC: the 5 this repository registers, and the 3 that
start from other folders (`site\hf_mirror.vbs` and `site\site_autodeploy.vbs`,
which run this repository's `tools/`, and `covenant-adopt`, whose Linux updater
lives in that folder as its README says host config should).

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

`linux/install_timers.sh` writes the eight Windows tasks as systemd user
timers, on the Windows tasks' own schedules:

| Timer | Windows task | Runs | Time limit |
|---|---|---|---|
| `guard` | CovenantGuard | every 2 min | 10 min |
| `refine-check` | CovenantRefineCheck | every 15 min, at :03 | 10 min |
| `ambassador` | CovenantAmbassador | every 3 h: 02, 05, 08 ... 23 | 2 h 50 min |
| `distill` | CovenantDistill | daily 02:30 | 6 h |
| `trader` | CovenantTrader | daily 09:00 (`linux/trader_task.sh`) | 72 h |
| `hf-mirror` | CovenantHFMirror | every 2 h, :05 on odd hours | 72 h |
| `site-autodeploy` | CovenantSiteAutoDeploy | every 15 min, at :07 | 72 h |
| `adopt` | covenant-adopt | daily 05:00 (`~/covenant-adopt/linux/run_adopt.sh`) | 72 h |

**Which to enable where -- the quorum's answer (2026-11-26, five seats, A492):**

| Timer | Towers | Seats |
|---|---|---|
| `guard` | all three | 5 of 5 |
| `refine-check` | all three | 4 of 5 |
| `distill` | one | 3 of 5 (2 said all) |
| `ambassador` | none | 4 of 5 |
| `trader` | none | 5 of 5 |
| `hf-mirror` | one machine in all (2 said none) | 3 of 5 |
| `site-autodeploy` | one machine in all (2 said none) | 3 of 5 |
| `adopt` | none | 3 of 5 |

"One" counts the laptop: it runs `hf-mirror` and `site-autodeploy` today, so
while it does, the towers enable neither. `install`, `enable` and `status`
warn when lingering is off, because without it every timer stops at logout and
none starts after a reboot (the risk two seats named first).

**Enable `hf-mirror` and `site-autodeploy` on one machine only.** The laptop
runs them today; a second machine would push and deploy the same things. On
Linux, `site-autodeploy` needs the website checkout at
`~/site/lawless1987-website-backup/website` (or `COVENANT_SITE_DIR`) and `node`
(`sudo apt install nodejs`, or `COVENANT_NODE_DIR`). `adopt` merges into this
checkout and restarts the nodes: see the covenant-adopt folder's README.

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
`linux/install_timers.sh remove` disables all eight and moves the unit files to
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
