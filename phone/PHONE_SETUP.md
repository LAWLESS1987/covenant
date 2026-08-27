# Running the daily check on your Android phone

Five steps. The whole thing takes about ten minutes, most of it downloads.

---

## 1. Install Termux — **from F-Droid, not the Play Store**

This is the step people get wrong, and everything downstream fails if you do.
The Google Play build of Termux was frozen years ago; its package repo is dead,
so `pkg install` either errors or gives you binaries that crash.

Get all three from F-Droid:

- **Termux** — https://f-droid.org/en/packages/com.termux/
- **Termux:API** — the notification bridge
- **Termux:Boot** — restarts the job after a reboot

They must all come from F-Droid. Android checks signatures, and a Play-Store
Termux will refuse an F-Droid add-on.

Open **Termux:Boot once** after installing. It does nothing visible; opening it
is what registers it with Android.

## 2. Download the files

From this chat, download to your phone: `daily.py`, `holdings.txt`,
`install.sh`, `covenant-run.sh`, `covenant-doctor.sh`. They land in Downloads.

## 3. Run the installer

Open Termux and type:

```
cd ~/storage/downloads 2>/dev/null || termux-setup-storage
cd ~/storage/downloads
bash install.sh
```

If the first line asks for file permission, tap **Allow**, then run the last
two lines again.

The installer refuses to schedule anything until it has run `daily.py`
successfully once. A scheduled job that has never worked is worse than none —
it produces silence you'd read as good news.

## 4. Make Android leave it alone

**Settings → Apps → Termux → Battery → Unrestricted**

This one setting decides whether the whole thing survives. Android's battery
manager kills background work within a few days otherwise, and it does it
without any notice. Nothing in a script can override it.

## 5. Check on it

```
cd ~/covenant && ./covenant-doctor.sh
```

This is the part that matters. It lists every day the job *should* have run and
didn't. Silence from a dead job and silence from a quiet market look identical
on a phone — this is what tells them apart. Run it once a week.

---

## The commands you'll actually use

| | |
|---|---|
| run it right now | `cd ~/covenant && ./covenant-run.sh` |
| is it still alive? | `cd ~/covenant && ./covenant-doctor.sh` |
| read the last result | `cat ~/covenant/state/last_output.txt` |
| update your holdings | `nano ~/covenant/holdings.txt` |
| restart the scheduler | `crond` |

---

## The test running for the next week

The phone fires at **07:55**. The cloud task fires at **08:00**. For a week
you'll get both, five minutes apart.

- **Both arrive every day** → the phone works. Turn off the cloud task, you're
  fully local. Tell me and I'll delete it.
- **Only the 08:00 one some days** → that's Android killing the job, and now
  you have dates instead of an argument. `covenant-doctor.sh` lists them.

Either way you'll know from evidence in about seven days.

---

## What this does and doesn't do

It reads public Coinbase prices, compares them against your rules, and prints a
suggestion. It holds no keys. It cannot place an order. Every trade is one you
make yourself.
