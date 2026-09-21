# Reconnecting when the phone or the PC is lost

Written 2026-09-21 on the operator's instruction: *"For both phone and pc if
either or both lost find a way to reconnect with me."* This page is public on
purpose: a rebuilt PC or a new phone can read it with neither side running.

## What each side does on its own

**The PC** (`covenant_reconnect.py`, run by the nightly) reads four records it
already keeps: the phone's check-in, his conversations, the direct line, and
the last commit. When the phone has been silent for 24 hours and nothing from
him has arrived on any channel for 24 hours, it reaches out once a day:

1. a message on the direct line, so the phone shows it the moment it is back;
2. every second channel `covenant_notify.py` has configured (ntfy, email);
3. and it names, in its own report, the channels it does **not** have.

Measured 2026-09-21: this PC has **no** second channel configured. Until
`python covenant_notify.py --setup` is run, the PC's only road to him is the
phone, which is the road that is lost. The report says `UNDETERMINED` for
step 2 rather than pretending.

**The phone** (the covenant-phone app, `NodeService`) counts failed check-ins.
After 24 hours of them it shows one notification a day with the steps below.

## The steps

1. **Phone first.** Open Covenant, Settings: is the PC peer still the PC's
   Tailscale name and port? Is Tailscale up on both? A check-in every ten
   minutes is the heartbeat; `python covenant_reconnect.py --status` on the
   PC says when the last one arrived.
2. **PC next.** `python rolling_restart.py` restarts the nodes one at a time.
   `python covenant_watchdog.py --status` says whether they are on the source
   that is on disk. The API answers on 5000, 5020 and 5060; 5001 is peer
   traffic and swallows HTTP.
3. **If the PC is gone.** A fresh clone of `github.com/LAWLESS1987/covenant`
   plus his private copies of `private/` and `ops/` rebuilds it. Nothing in
   the public repository carries a key. The phone finds the new PC by the
   same Tailscale name once Tailscale is signed in on it.
4. **If the phone is gone.** Install the app from the covenant-phone release
   (the APK is the build artifact; auto-update cannot bootstrap itself, so the
   first install is by hand), then pair it from the PC's `/pc/handshake` page
   on the tailnet. The old phone's key is not the new phone's key; the PC's
   `/checkin` accepts the new one when he confirms it on the PC.
5. **If both are gone.** The repository is the record. Rebuild the PC (step
   3), then the phone (step 4). What is his alone -- the keys, the private
   directory -- is only where he put it; see `docs/SUCCESSION_REGISTER.md` for what he
   was asked to write down.

## What this cannot do

It cannot reach him through a channel he has not configured, and it cannot
know he is well from silence. Silence is measured and reported; it is never
read as anything more.
