#!/usr/bin/env python3
"""
A92 -- an ntfy topic is a credential, and one was published in a tracked file.

THE DEFECT, measured 2026-09-11. DAILY.bat:4 read

    python daily.py [the push flag] <the operator's literal topic>

The old topic is deliberately NOT written out here. It is burned -- it has been
in published history since the first commit -- but a file that quotes it is a
file that publishes it again. E6b below caught exactly that when this suite was
first written, which is the check working on its own author.

and DAILY.bat has been tracked on LAWLESS1987/covenant -- a PUBLIC repository --
since the initial commit 462887e. daily.py:708-712 builds
"Portfolio $<total>, cash <n>%" plus the guard-blocked symbols and the
down-regime tickers, and daily.py sends it to
https://ntfy.sh/<topic>/publish?title=...&message=... in a GET query string.

ntfy.sh has no authentication by design: the topic name IS the credential.
Publishing the topic published the channel. ~/.covenant/daily_state.json holds
17 equity points between 2026-08-28 and 2026-09-03, so the tool ran; which of
those runs went through DAILY.bat rather than a direct call cannot be told from
the state file, and is not claimed here. The old topic is burned either way --
it is in published history from the first commit, so it was replaced rather
than hidden.

The topic now lives OUTSIDE the repository (~/.covenant/ntfy_topic, beside the
state file that daily.py already keeps there), where no commit can reach it,
and the tracked caller says only "auto".

WHY THESE CHECKS ARE BEHAVIOURAL. E1-E5 RUN resolve_topic and push with the
network replaced by a recorder. E6 scans the ARTIFACT -- every .bat/.sh/.ps1/
.py/.md in the tree -- rather than asserting something about daily.py's source,
because the defect was never in daily.py: it was in a batch file that called
it. E7 plants a literal and proves the scanner finds it, since a scanner that
cannot see the defect cannot certify its absence.

Run: python test_a92_topic_is_a_credential.py
"""
import os
import re
import sys
import tempfile

import daily

results = []


def check(ok, name, detail=""):
    results.append(bool(ok))
    print("%s  %s%s" % ("PASS" if ok else "FAIL", name, ("  " + detail) if detail else ""))


print("== the topic resolves from outside the repository, or not at all ==")
d = tempfile.mkdtemp()
_tf = daily.TOPIC_FILE
_env = os.environ.pop("COVENANT_NTFY_TOPIC", None)
try:
    daily.TOPIC_FILE = os.path.join(d, "ntfy_topic")
    with open(daily.TOPIC_FILE, "w", encoding="utf-8") as fh:
        fh.write("  a-topic-from-a-file  \n")
    check(daily.resolve_topic("auto") == "a-topic-from-a-file",
          "E1 'auto' reads the file outside the repository, stripped")

    os.environ["COVENANT_NTFY_TOPIC"] = "a-topic-from-the-env"
    check(daily.resolve_topic("auto") == "a-topic-from-the-env",
          "E2 an environment variable wins over the file")
    os.environ.pop("COVENANT_NTFY_TOPIC", None)

    daily.TOPIC_FILE = os.path.join(d, "absent")
    check(daily.resolve_topic("auto") == "",
          "E3 no file and no env -> empty, never a guess")

    check(daily.resolve_topic("an-explicit-topic") == "an-explicit-topic",
          "E4 an explicit topic still passes through unchanged")
finally:
    daily.TOPIC_FILE = _tf
    if _env is not None:
        os.environ["COVENANT_NTFY_TOPIC"] = _env

print()
print("== an unresolved topic sends nothing: run it, with the network recorded ==")
called = []


class _Recorder:
    def __init__(self, url, *a, **k):
        called.append(url)

    def read(self):
        return b""

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


_urlopen = daily.urllib.request.urlopen
try:
    daily.urllib.request.urlopen = _Recorder
    daily.push("", "Portfolio $12,345, cash 8%.")
    check(not called, "E5a an empty topic reaches no network call at all",
          "%d call(s)" % len(called))
    daily.push("a-real-looking-topic", "Portfolio $12,345, cash 8%.")
    check(len(called) == 1 and "a-real-looking-topic" in called[0],
          "E5b THE INSTRUMENT BITES: a non-empty topic DOES call out, so E5a is "
          "measuring the guard and not a broken recorder")
finally:
    daily.urllib.request.urlopen = _urlopen

print()
print("== the artifact: no literal topic anywhere a commit can reach ==")
RX = re.compile(r"(?:^|\s)--push[= ]+([^\s\"')]+)")
STRIP = ",.;:)\"'"
SAFE = re.compile(r"^(auto|TOPIC|<[^>]+>|%[^%]+%|\$\{?[A-Za-z_]+\}?|[A-Z][A-Z0-9_]*)$")
SKIP_DIRS = {".git", ".venv", "__pycache__", "vendor", "node_modules", ".claude", "books"}
EXTS = (".bat", ".sh", ".ps1", ".py", ".md")


def scan(base):
    """Every topic argument in the tree that is neither 'auto', a placeholder,
    nor a shell variable. 'books' is skipped: docs/semantic/books holds public
    domain prose, and one of them contains "Push on--push on, boys!"."""
    out, n = [], 0
    for root, dirs, files in os.walk(base):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
        for f in files:
            if not f.endswith(EXTS):
                continue
            q = os.path.join(root, f)
            try:
                txt = open(q, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            n += 1
            for ln, line in enumerate(txt.splitlines(), 1):
                for m in RX.finditer(line):
                    v = m.group(1).strip(STRIP)
                    if not v or SAFE.match(v) or "YOUR" in v.upper():
                        continue
                    out.append("%s:%d -> %s" % (q, ln, v))
    return out, n


HERE = os.path.dirname(os.path.abspath(__file__)) or "."
found, nfiles = scan(HERE)
check(nfiles > 100, "E6a the scan actually covered the tree", "%d files" % nfiles)
check(not found, "E6b no literal ntfy topic is committed anywhere",
      "; ".join(found) if found else "clean")

plant = tempfile.mkdtemp()
os.makedirs(os.path.join(plant, "sub"), exist_ok=True)
with open(os.path.join(plant, "sub", "PLANTED.bat"), "w", encoding="utf-8") as fh:
    # Assembled at runtime, so this file never CONTAINS the pattern it hunts.
    flag = "--" + "push"
    fh.write("@echo off\npython daily.py " + flag + " covenant-someone-9x8y7z\n")
planted, _ = scan(plant)
check(len(planted) == 1,
      "E7 THE INSTRUMENT BITES: the scanner finds a planted topic, so E6b is a "
      "measurement and not an empty regex", "%d found" % len(planted))

print()
n_ok = sum(1 for r in results if r)
print("%d/%d passed" % (n_ok, len(results)))
sys.exit(0 if n_ok == len(results) else 1)
