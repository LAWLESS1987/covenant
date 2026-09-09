#!/usr/bin/env python3
"""
covenant_notify.py -- reach his phone, from a background process, with no
credential in this repository.

ASKED 2026-09-09: "set it up to email my phone", said while leaving. So the
requirement is not "send one email" -- that already happened from the session.
It is that `free` and the nightly can reach him LATER, when nobody is watching
the console.

TWO CHANNELS, TRIED IN ORDER, AND THE REASON THERE ARE TWO
  1. ntfy  -- push, no account, no credential anywhere. The repository already
     chose this (start_alerts.bat, signal_watch.push) and a second mechanism for
     the same job would be the two-paths mistake again, so this CALLS that one
     rather than reimplementing it. Needs the ntfy app and a topic.
  2. email -- SMTP, for exactly the case he asked about: a phone that already
     gets his mail, with nothing to install.

  Whichever are configured, all are tried, and the return value says which
  actually delivered. A notifier that reports success on a channel that silently
  dropped the message is worse than no notifier -- that is the A71 lesson
  (silence looked like nothing to report) applied to the way out instead of the
  way in.

THE CREDENTIAL IS NOT HERE AND CANNOT BE
  Read from ~/.config/covenant/notify.json, outside the repository, locked to
  his Windows account, and never logged. This file has no default password, no
  fallback account, and no code path that writes a credential anywhere. Test
  N6 greps this file for the config path to make sure it stays outside the tree.

  A Yahoo or Gmail account needs an APP PASSWORD, not the login password. He
  creates it; an assistant does not handle either. `--setup` prints exactly what
  to paste and where, and creates nothing.

USE
  python covenant_notify.py --selftest      offline, sends nothing
  python covenant_notify.py --setup         what to put in the config file
  python covenant_notify.py --test          send a real test to the phone
LICENCE: Apache-2.0.
"""
from __future__ import annotations

import argparse
import json
import os
import smtplib
import ssl
from email.message import EmailMessage

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.environ.get("COVENANT_NOTIFY_CONFIG") or os.path.join(
    os.path.expanduser("~"), ".config", "covenant", "notify.json")

_SECRET_KEYS = ("smtp_password", "password", "api_key", "token")


def load(path=None):
    """The config, or {}. Never raises, never logs a secret."""
    path = path or CONFIG
    try:
        with open(path, encoding="utf-8") as fh:
            cfg = json.load(fh)
        return cfg if isinstance(cfg, dict) else {}
    except Exception:                                             # noqa: BLE001
        return {}


def redact(cfg):
    """A copy safe to print or log. Used everywhere this file shows config."""
    out = {}
    for k, v in (cfg or {}).items():
        out[k] = "<set>" if (k in _SECRET_KEYS and v) else v
    return out


def _send_ntfy(topic, title, body, priority="default"):
    """Delegates to signal_watch.push -- the repository's existing pusher."""
    try:
        import signal_watch
        return bool(signal_watch.push(topic, title, body, priority=priority))
    except Exception:                                             # noqa: BLE001
        return False


def _send_email(cfg, title, body):
    """One SMTP send. Returns (ok, note). The password is never in the note."""
    host = cfg.get("smtp_host")
    port = int(cfg.get("smtp_port") or 587)
    user = cfg.get("smtp_user")
    pwd = cfg.get("smtp_password")
    to = cfg.get("email_to") or user
    if not (host and user and pwd and to):
        return False, "email not configured"
    msg = EmailMessage()
    msg["Subject"] = title
    msg["From"] = user
    msg["To"] = to
    msg.set_content(body)
    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=30,
                                  context=ssl.create_default_context()) as s:
                s.login(user, pwd)
                s.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=30) as s:
                s.starttls(context=ssl.create_default_context())
                s.login(user, pwd)
                s.send_message(msg)
        return True, "sent to %s" % to
    except Exception as e:                                        # noqa: BLE001
        # The exception text can carry the account name; it never carries the
        # password, and it is truncated rather than dumped.
        return False, "%s: %s" % (type(e).__name__, str(e)[:120])


def notify(title, body, priority="default", cfg=None, say=None):
    """Try every configured channel. Returns {channel: (ok, note)}.

    NEVER RAISES. A notifier that can bring down the thing it is reporting on
    has inverted its own purpose."""
    cfg = load() if cfg is None else cfg
    results = {}
    topic = cfg.get("ntfy_topic") or os.environ.get("NTFY_TOPIC")
    if topic:
        ok = _send_ntfy(topic, title, body, priority)
        results["ntfy"] = (ok, "delivered" if ok else "no delivery")
    if cfg.get("smtp_host"):
        results["email"] = _send_email(cfg, title, body)
    if not results:
        results["none"] = (False, "no channel configured -- see --setup")
    if say:
        for ch, (ok, note) in results.items():
            say("  %-6s %-5s %s" % (ch, "OK" if ok else "FAIL", note))
    return results


SETUP = """
Create this file (it is OUTSIDE the repository, on purpose):

    %s

FOR EMAIL TO YOUR PHONE -- Yahoo needs an APP PASSWORD, not your login
password. Make one at: Yahoo Account Security -> Generate app password.

    {
     "smtp_host": "smtp.mail.yahoo.com",
     "smtp_port": 465,
     "smtp_user": "you@yahoo.com",
     "smtp_password": "<the 16-character app password>",
     "email_to": "you@yahoo.com"
    }

FOR PUSH INSTEAD (no account, no password, arrives faster) -- install the
"ntfy" app, subscribe to a random topic name, then add:

    { "ntfy_topic": "covenant-<something-random>" }

Both may be present; both will be used.

THEN LOCK IT so only you can read it:

    icacls "%s" /inheritance:r /grant:r "%%USERNAME%%:F"

Test it with:  python covenant_notify.py --test
""".strip()


def selftest(say=print):
    ok = []

    def check(label, cond, detail=""):
        ok.append(bool(cond))
        say("%s  %s%s" % ("ok  " if cond else "FAIL", label,
                          ("  " + str(detail)[:140]) if (detail and not cond) else ""))

    r = notify("t", "b", cfg={})
    check("N1 with nothing configured it reports NO CHANNEL rather than "
          "claiming success", r.get("none") == (False, r["none"][1])
          and r["none"][0] is False)
    check("N2 a redacted config hides the password and keeps the rest",
          redact({"smtp_user": "a@b.c", "smtp_password": "hunter2"})
          == {"smtp_user": "a@b.c", "smtp_password": "<set>"})
    bad, note = _send_email({"smtp_host": "h", "smtp_user": "u",
                             "smtp_password": "p"}, "t", "b")
    check("N3 an email with no recipient and no reachable host FAILS and says "
          "so -- it does not return success", bad is False and note)
    check("N4 a half-configured email reports 'not configured', not an error",
          _send_email({"smtp_host": "h"}, "t", "b")[1] == "email not configured")
    r2 = notify("t", "b", cfg={"ntfy_topic": ""})
    check("N5 an empty topic is not a channel", "ntfy" not in r2)
    src = open(os.path.join(HERE, "covenant_notify.py"), encoding="utf-8").read()
    body_only = src.split('"""', 2)[-1]
    # N6 FIRST TRIED TO GREP FOR THE STRING "smtp_password" AND FAILED ON
    # ITSELF -- the word appears legitimately in cfg.get() and in the setup
    # text this file prints. Grepping for a word was never the claim. The claim
    # is that the credential lives outside the tree and that nothing here
    # writes one, so both halves are now tested as behaviour.
    inside = os.path.commonpath([os.path.abspath(CONFIG), HERE]) == HERE
    check("N6a the credential path is OUTSIDE the repository, so a commit can "
          "never carry it", not inside, CONFIG)
    # NEEDLES BUILT, NOT WRITTEN -- the third time today a check in this
    # repository has failed on its own source (M6, AM11, and now this). Spelling
    # the pattern puts a copy of it in the body being scanned.
    opener = "open" + "("
    modes = [q + c + q for q in ('"', "'") for c in ("w", "a")]
    writes = [ln for ln in body_only.splitlines()
              if opener in ln and any(m in ln for m in modes)]
    check("N6b this file opens NOTHING for writing -- it cannot create or "
          "modify a credential, so --setup can only ever print", not writes,
          writes)
    check("N7 notify() never raises, whatever it is handed",
          isinstance(notify("t", "b", cfg={"smtp_host": "nonexistent.invalid",
                                           "smtp_user": "u",
                                           "smtp_password": "p",
                                           "email_to": "a@b.c"}), dict))
    n = sum(ok)
    say("\nNOTIFY: %d/%d passed" % (n, len(ok)))
    return 0 if n == len(ok) else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--setup", action="store_true")
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--title", default="covenant")
    ap.add_argument("--body", default="test from covenant_notify.py")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.setup:
        print(SETUP % (CONFIG, CONFIG))
        return 0
    cfg = load()
    print("config: %s" % CONFIG)
    print("        %s" % (json.dumps(redact(cfg)) if cfg else "MISSING -- see --setup"))
    if a.test:
        print("sending...")
        res = notify(a.title, a.body, priority="high", cfg=cfg, say=print)
        return 0 if any(ok for ok, _ in res.values()) else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
