#!/usr/bin/env python3
"""phone_identity_export.py -- save the phone node's identity key off the phone,
while that is still possible, and prove it is the key this PC trusts.

WHY THIS EXISTS, and why it is urgent rather than tidy (2026-09-14). The phone
node's RSA identity lives inside the app's private directory as
files/core/covenant_unified_phone.db.key. It is not a backup detail: it is
REGISTERED on this PC as a daily-plan signer (ops/daily_plan_signers.json),
which means whoever holds it can approve the day's trading plan, and it is the
key sealed mail is addressed to. There is exactly one copy, on the phone, and
an uninstall deletes it.

Two things now make this the moment:

  * The security audit's top item is that every build is signed with the PUBLIC
    debug key from the app repository, so anyone can build an APK that installs
    over the operator's. Closing that means switching to his own release key --
    and a new signing key is a new app identity, so Android refuses the update
    and the app must be UNINSTALLED first. That deletes this key.
  * The same audit's other finding was that every build was `debuggable`, which
    is what let `adb run-as` read the app's private directory at all. That is
    fixed from the 2026-09-14 build onward -- and the fix closes this door too.
    The app installed on his phone today is still debuggable. The next one is
    not.

So: run this while the old app is still on the phone. After that it needs root.

WHAT IT DOES NOT DO. It never prints the key, never copies it into a
repository, and never sends it anywhere. It writes one file under
~/.covenant/phone-identity/ -- outside every checkout, beside the phone signing
key that already lives at ~/.covenant/phone-signing/ -- and refuses to
overwrite an existing one. What it prints is the SHA-256 fingerprint of the
PUBLIC half, which is safe to read aloud and is what lets you check that the
file you just saved is the signer this PC has registered.

NO CABLE NEEDED. Android's own Wireless debugging does the same job over Wi-Fi,
or over the tailnet the PC and the phone already share. The wireless option
walks through it: Android separates a one-time PAIRING (its own port, a
six-digit code) from the CONNECTION (a different port, new every time the
switch is toggled), so both numbers are read off the phone's screen once. The
cable is used when one is plugged in and asked for otherwise.

Run:
  python mobile/phone_identity_export.py             save it over USB (refuses if one exists)
  python mobile/phone_identity_export.py --wireless  same, walking through Wireless debugging when no cable is present
  python mobile/phone_identity_export.py --status     what is on the phone and what is saved, changing nothing
  python mobile/phone_identity_export.py --explain    this, in the module's words
"""
import argparse
import hashlib
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PKG = "org.covenant.node"
REMOTE = "files/core/covenant_unified_phone.db.key"
DEST_DIR = os.path.join(os.path.expanduser("~"), ".covenant", "phone-identity")
DEST = os.path.join(DEST_DIR, "covenant_unified_phone.db.key")
SIGNERS = os.path.join(ROOT, "ops", "daily_plan_signers.json")
PEM_HEAD = b"-----BEGIN"


def adb_path():
    """The bundled adb first: the operator has it in the tree already, and a PATH
    lookup that finds a different Android SDK is a worse answer than a known one."""
    local = os.path.join(ROOT, "tools", "platform-tools", "adb.exe")
    if os.path.isfile(local):
        return local
    local_nix = os.path.join(ROOT, "tools", "platform-tools", "adb")
    if os.path.isfile(local_nix):
        return local_nix
    from shutil import which
    return which("adb")


def run(adb, args, binary=False, timeout=60):
    p = subprocess.run([adb] + args, capture_output=True, timeout=timeout)
    out = p.stdout if binary else p.stdout.decode("utf-8", "replace")
    err = p.stderr.decode("utf-8", "replace")
    return p.returncode, out, err


def devices(adb):
    """[(serial, state)] from `adb devices`, header and blanks dropped."""
    rc, out, err = run(adb, ["devices"])
    if rc != 0:
        return None, err.strip() or "adb devices failed"
    rows = []
    for line in out.splitlines()[1:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) >= 2:
            rows.append((parts[0], parts[1]))
    return rows, ""


def fingerprint_of_private_pem(data):
    """(fingerprint, bits, reason). The SHA-256 of the PUBLIC key in this project's
    own registry shape -- sha256 over the whitespace-stripped public PEM, the first
    16 hex, which is what covenant_daily_plan and the phone's Today screen print.
    Nothing secret is derived or shown."""
    try:
        from cryptography.hazmat.primitives import serialization
    except ImportError:
        return "", 0, "cryptography is not installed here, so the key could not be checked"
    try:
        key = serialization.load_pem_private_key(data, password=None)
    except Exception as e:                                        # noqa: BLE001
        return "", 0, "not a readable private key: %s" % type(e).__name__
    pub = key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    fp = hashlib.sha256("".join(pub.split()).encode("utf-8")).hexdigest()[:16]
    return fp, getattr(key, "key_size", 0), ""


def registered_phone_fp():
    """The fingerprint of the key this PC has registered under the name 'phone',
    so the export can be checked against what the PC actually trusts."""
    import json
    try:
        with open(SIGNERS, encoding="utf-8") as fh:
            d = json.load(fh)
    except (OSError, ValueError):
        return "", "no signer registry on this PC (ops/daily_plan_signers.json)"
    pem = d.get("phone")
    if not pem:
        return "", "no signer named 'phone' is registered on this PC"
    return hashlib.sha256("".join(str(pem).split()).encode("utf-8")).hexdigest()[:16], ""


def pull(adb, say):
    """The key's bytes, or (None, why). run-as is the only route that does not need
    root, and it works only while the installed build is debuggable."""
    rc, out, err = run(adb, ["exec-out", "run-as", PKG, "cat", REMOTE], binary=True)
    text = (err or "").strip()
    if rc != 0 or not out:
        if "not debuggable" in text or "run-as: " in text:
            return None, ("the installed app is NOT debuggable, so run-as is refused. "
                          "That is the 2026-09-14 hardening: from that build on, this key can "
                          "only be read with root. If you have not saved it yet and the old app "
                          "is gone, it is only on the phone. (%s)" % text[:160])
        if "device unauthorized" in text or "unauthorized" in text:
            return None, "the phone has not authorised this computer: unlock it and accept the USB debugging prompt"
        return None, text[:200] or "adb returned nothing (rc=%d)" % rc
    if not out.startswith(PEM_HEAD):
        # run-as can succeed and still print an error into stdout
        return None, "what came back is not a PEM key: %r" % out[:80]
    return out, ""


def _ask(prompt, allow_blank=False):
    try:
        v = input(prompt).strip()
    except EOFError:
        return ""
    if not v and not allow_blank:
        return ""
    return v


def _endpoint(v):
    """'10.77.0.12:41234' -> ('10.77.0.12', '41234'), tolerating stray spaces and a
    trailing dot. Returns ('','') when it is not host:port."""
    v = (v or "").strip().strip(".").replace(" ", "")
    if v.count(":") != 1:
        return "", ""
    host, port = v.split(":", 1)
    if not host or not port.isdigit():
        return "", ""
    return host, port


def hints():
    """Addresses this phone is known to answer on, so he can recognise the one the
    phone is showing him rather than wonder which is which."""
    out = []
    tail = os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "Tailscale", "tailscale.exe")
    if os.path.isfile(tail):
        try:
            rc, o, _e = 0, subprocess.run([tail, "status"], capture_output=True, timeout=20).stdout.decode("utf-8", "replace"), ""
            for line in o.splitlines():
                parts = line.split()
                if len(parts) >= 4 and parts[3] == "android":
                    out.append("%s  (%s, over Tailscale)" % (parts[0], parts[1]))
                    if "direct" in line:
                        seg = line.split("direct", 1)[1].strip().split(",")[0]
                        if ":" in seg:
                            out.append("%s  (%s, on your Wi-Fi)" % (seg.split(":")[0], parts[1]))
        except Exception:                                         # noqa: BLE001
            pass
    return out


def wireless_connect(adb, say=print):
    """Android's Wireless debugging, walked through. True when a device is connected.

    Deliberately interactive: the pairing code and both ports are shown on the phone
    and change every time, so there is nothing to remember and nothing to store. Both
    numbers are read off the screen and typed once."""
    say("")
    say("  WIRELESS DEBUGGING -- no cable needed")
    say("")
    say("  On the phone, open:  Settings > Developer options > Wireless debugging")
    say("  Turn it ON. (If Developer options is hidden: Settings > About phone >")
    say("  Software information, then tap 'Build number' seven times.)")
    for h in hints():
        say("      this phone should appear as %s" % h)
    say("")
    say("  Now tap 'Pair device with pairing code'. A box appears showing an")
    say("  'IP address & Port' and a six-digit 'Wi-Fi pairing code'.")
    say("")
    ep = _ask("  Type the IP address & Port from that box (e.g. 10.77.0.12:41234): ")
    host, port = _endpoint(ep)
    if not host:
        say("  That did not look like an address and port. Nothing was done.")
        return False
    code = _ask("  Type the six-digit pairing code: ")
    if not code.isdigit() or len(code) != 6:
        say("  A pairing code is six digits. Nothing was done.")
        return False
    say("")
    say("  pairing with %s:%s ..." % (host, port))
    rc, out, err = run(adb, ["pair", "%s:%s" % (host, port), code], timeout=90)
    blob = (out or "") + (err or "")
    if "Successfully paired" not in blob:
        say("  Pairing did not succeed: %s" % blob.strip().splitlines()[-1][:160] if blob.strip() else "  Pairing did not succeed.")
        say("  The code and port change every time that box is closed -- reopen it and try again.")
        return False
    say("  paired.")
    say("")
    say("  Close that pairing box. The main Wireless debugging screen shows its own")
    say("  'IP address & Port' -- a DIFFERENT port from the one you just used.")
    say("")
    ep2 = _ask("  Type that IP address & Port (e.g. %s:37000): " % host)
    host2, port2 = _endpoint(ep2)
    if not host2:
        say("  That did not look like an address and port. The pairing is kept; run this again.")
        return False
    say("")
    say("  connecting to %s:%s ..." % (host2, port2))
    rc, out, err = run(adb, ["connect", "%s:%s" % (host2, port2)], timeout=60)
    blob = ((out or "") + (err or "")).strip()
    if "connected to" not in blob:
        say("  Could not connect: %s" % (blob.splitlines()[-1][:160] if blob else "no answer"))
        return False
    say("  connected.")
    return True


def status(say=print):
    adb = adb_path()
    say("phone identity key -- status, changing nothing")
    say("  adb:        %s" % (adb or "NOT FOUND (expected tools/platform-tools/adb.exe)"))
    reg_fp, reg_why = registered_phone_fp()
    say("  registered: %s" % (reg_fp or ("-- " + reg_why)))
    if os.path.isfile(DEST):
        with open(DEST, "rb") as fh:
            data = fh.read()
        fp, bits, why = fingerprint_of_private_pem(data)
        say("  saved here: %s (%d bytes%s)" % (DEST, len(data), ", %d-bit" % bits if bits else ""))
        say("              fingerprint %s%s" % (fp or "unreadable", "" if not why else " -- " + why))
        if fp and reg_fp:
            say("              %s" % ("MATCHES the key this PC trusts as 'phone'" if fp == reg_fp
                                      else "DOES NOT match the registered 'phone' key -- a different phone, or the key was replaced"))
    else:
        say("  saved here: nothing yet (%s)" % DEST)
    if not adb:
        return 0
    rows, why = devices(adb)
    if rows is None:
        say("  phone:      could not ask adb (%s)" % why)
        return 0
    if not rows:
        say("  phone:      no device. Plug it in by USB, unlock it, and turn on Developer options > USB debugging.")
        return 0
    for serial, state in rows:
        say("  phone:      %s (%s)" % (serial, state))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="save the phone node's identity key off the phone")
    ap.add_argument("--status", action="store_true", help="what is on the phone and what is saved; changes nothing")
    ap.add_argument("--wireless", action="store_true",
                    help="no cable: walk through Android's Wireless debugging (pair, then connect) first")
    ap.add_argument("--explain", action="store_true", help="why this exists, in the module's own words")
    a = ap.parse_args(argv)
    if a.explain:
        print(__doc__.split("Run:")[0].strip())
        return 0
    if a.status:
        return status()

    adb = adb_path()
    if not adb:
        print("adb not found. It ships in this repository at tools/platform-tools/adb.exe;")
        print("if that is missing, install Android platform-tools and try again.")
        return 2
    if os.path.isfile(DEST):
        print("A key is already saved at:\n  %s" % DEST)
        print("Refusing to overwrite it. Run with --status to see its fingerprint, or move that")
        print("file aside yourself if you really mean to replace it.")
        return 1

    rows, why = devices(adb)
    if rows is None:
        print("adb could not run: %s" % why)
        return 2
    live = [r for r in rows if r[1] == "device"]
    if not live and a.wireless:
        # No cable. Android's own Wireless debugging does the same job over Wi-Fi (or over
        # the tailnet, since both machines are on it) and needs nothing installed on either
        # side. It is two steps because Android deliberately separates them: a one-time
        # PAIRING on one port with a six-digit code, then the CONNECTION on a different
        # port that changes every time the switch is toggled.
        if not wireless_connect(adb):
            return 2
        rows, why = devices(adb)
        live = [r for r in (rows or []) if r[1] == "device"]
    if not live:
        if any(r[1] == "unauthorized" for r in rows):
            print("The phone is connected but has not authorised this computer.")
            print("Unlock it, and accept the 'Allow USB debugging?' prompt, then run this again.")
            return 2
        print("No phone is connected over USB.")
        print("Plug it in, unlock it, turn on Developer options > USB debugging, then run this again.")
        print("")
        print("No cable? Run this instead and it will walk you through Android's own")
        print("Wireless debugging, which needs no cable and nothing installed:")
        print("    python mobile\\phone_identity_export.py --wireless")
        return 2
    if len(live) > 1:
        print("More than one device is connected: %s" % ", ".join(r[0] for r in live))
        print("Unplug the others so this cannot save the wrong phone's key.")
        return 2

    rc, out, err = run(adb, ["shell", "pm", "path", PKG])
    if PKG not in (out or ""):
        print("Covenant Node is not installed on that phone (pm path %s said nothing)." % PKG)
        return 2

    data, why = pull(adb, print)
    if data is None:
        print("Could not read the key: %s" % why)
        return 2

    fp, bits, fwhy = fingerprint_of_private_pem(data)
    if fwhy and not fp:
        print("What came off the phone does not read as a private key: %s" % fwhy)
        print("Nothing was saved.")
        return 2

    os.makedirs(DEST_DIR, exist_ok=True)
    tmp = "%s.%d.tmp" % (DEST, os.getpid())
    try:
        with open(tmp, "wb") as fh:
            fh.write(data)
        os.replace(tmp, DEST)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
    try:
        os.chmod(DEST, 0o600)
    except OSError:
        pass

    reg_fp, reg_why = registered_phone_fp()
    print("Saved the phone node's identity key.")
    print("  file:        %s" % DEST)
    print("  size:        %d bytes%s" % (len(data), ", %d-bit RSA" % bits if bits else ""))
    print("  fingerprint: %s" % (fp or "unreadable"))
    if reg_fp and fp:
        if fp == reg_fp:
            print("  check:       MATCHES the key this PC has registered as the signer 'phone'.")
        else:
            print("  check:       DOES NOT MATCH the registered 'phone' signer (%s)." % reg_fp)
            print("               Either this is a different phone, or the phone's identity was")
            print("               recreated since it was registered. Worth understanding before you")
            print("               rely on this file.")
    elif reg_why:
        print("  check:       not compared -- %s" % reg_why)
    print("")
    print("This file is the credential that approves the day's trading plan. Keep it the way")
    print("you keep the PC's node key: it is outside every repository on purpose, and nothing")
    print("in this project will ever copy it back on its own.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
