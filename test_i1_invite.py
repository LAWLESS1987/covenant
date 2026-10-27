#!/usr/bin/env python3
"""I1 (2026-09-18): the greeter's link is derived, and the line it must not cross.

WHY A SUITE FOR A MODULE THAT PRINTS A STRING
---------------------------------------------
Because the string leaves the building. Everything else in this repository is
checked by people who already trust it; an invitation is read by someone who
does not, and the two ways it can be wrong are both silent:

  * a link that does not resolve, or resolves to the wrong repository. The URL
    is built from `git remote get-url origin`, so it tracks whatever remote the
    clone happens to have -- including a fork, a rename, or nothing at all.
    Gmail's composer has already cost this project one empty clone by wrapping
    a URL (see memory: the google.com/url wrapper), so a link is only worth
    sending if something has fetched it.
  * an invitation that leaks. The module's whole claim is that it embeds no
    live peer address and no credential: a greeter, not a spreader. That claim
    is one careless edit from being false, and nothing but a test will notice.

CHECKS
  I1-I4   owner/repo is parsed out of both URL shapes and falls back rather
          than raising when there is no remote at all
  I5-I8   THE LINE: no tailnet or LAN address, no token, no key, no PC_PEER
          value anywhere in the message -- asserted over the rendered text,
          which is what a person actually receives
  I9-I10  the message leads with read-before-run, and the one-liner it offers
          second points at the same URL
  N1      NETWORK, and it is allowed to be absent: the derived URL really
          serves mobile/install.sh. NOT RUN offline rather than red, because a
          suite that fails on a train teaches people to ignore it.
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import covenant_invite as INV

results, UNRUN = [], []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}")


def not_run(name, why):
    UNRUN.append((name, why))
    print(f"NOT RUN  {name}  -- {why}")


def parse_checks():
    check("I1 an https remote yields owner/repo",
          INV.raw_base("LAWLESS1987/covenant").endswith("/LAWLESS1987/covenant/main"),
          INV.raw_base("LAWLESS1987/covenant"))

    # The parser itself, against both shapes git actually hands back. Driven
    # through _owner_repo by faking the subprocess, because that is the code
    # path that runs -- passing owner_repo in would test nothing but string
    # formatting.
    real = subprocess.run
    cases = {
        "https://github.com/LAWLESS1987/covenant.git": "LAWLESS1987/covenant",
        "https://github.com/LAWLESS1987/covenant": "LAWLESS1987/covenant",
        "git@github.com:LAWLESS1987/covenant.git": "LAWLESS1987/covenant",
        "ssh://git@github.com/someone/other-name.git": "someone/other-name",
    }
    got = {}
    try:
        for url, want in cases.items():
            INV.subprocess.run = lambda *a, **k: type("R", (), {"stdout": url + "\n"})()
            got[url] = INV._owner_repo()
    finally:
        INV.subprocess.run = real
    bad = {u: (got[u], w) for u, w in cases.items() if got[u] != w}
    check("I2 both https and ssh remote shapes parse to owner/repo", not bad, str(bad))

    # No remote, or a git that is not there: fall back, never raise. A clone
    # with no origin is the ordinary state of a downloaded zip.
    try:
        INV.subprocess.run = lambda *a, **k: (_ for _ in ()).throw(FileNotFoundError("git"))
        fell = INV._owner_repo()
        raised = False
    except Exception as e:                                       # noqa: BLE001
        fell, raised = "%s" % type(e).__name__, True
    finally:
        INV.subprocess.run = real
    check("I3 no git at all falls back to the public canonical, never raises",
          not raised and fell == INV.FALLBACK_OWNER_REPO, str(fell))

    try:
        INV.subprocess.run = lambda *a, **k: type("R", (), {"stdout": "not-a-url\n"})()
        odd = INV._owner_repo()
    finally:
        INV.subprocess.run = real
    check("I4 an unparseable remote falls back rather than inventing a path",
          odd == INV.FALLBACK_OWNER_REPO, str(odd))


# The line the module says it holds, asserted over what a person receives.
FORBIDDEN_SUBSTRINGS = ("PC_PEER=1", "token", "TOKEN", "secret", "SECRET",
                        "api_key", "API_KEY", "BEGIN ", "PRIVATE KEY",
                        "Bearer ", "password")


def line_checks():
    msg = INV.invite_message()

    # 100.64.0.0/10 is the CGNAT range Tailscale hands out; 10.x/192.168.x are
    # the house LAN. An invitation carrying any of them is an exposure, and it
    # is also useless to the recipient.
    addrs = re.findall(r"\b(?:100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])"
                       r"|10|192\.168|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}"
                       r"(?:\.\d{1,3}){0,2}\b", msg)
    check("I5 no tailnet or private LAN address appears in the invitation",
          not addrs, str(addrs))

    leaked = [s for s in FORBIDDEN_SUBSTRINGS if s in msg]
    check("I6 no credential-shaped text appears in the invitation", not leaked, str(leaked))

    # PC_PEER is NAMED -- the message explains that joining a mesh is a
    # separate deliberate step -- but it must never carry a VALUE.
    assigned = re.findall(r"PC_PEER\s*=\s*([^\s.]+)", msg)
    check("I7 PC_PEER is named as a separate step but never given a value",
          "PC_PEER" in msg and all(v in ("...", "") for v in assigned), str(assigned))

    # BROKEN ON PURPOSE: prove I5-I7 can fail, so their green is earned.
    poisoned = msg + "\n  PC_PEER=100.72.0.50:5001  token=abc123"
    would_catch = bool(re.search(r"\b100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.", poisoned)) \
        and any(s in poisoned for s in FORBIDDEN_SUBSTRINGS)
    check("I8 and those checks DO fire on a message that leaks both",
          would_catch, "a peer address and a token are both caught")


def shape_checks():
    msg = INV.invite_message()
    url = INV.install_url()

    read_at = msg.find("Read it first")
    one_at = msg.find("the one-liner")
    check("I9 read-before-run leads, and the pipe-to-shell form comes second",
          0 < read_at < one_at, f"read@{read_at} one-liner@{one_at}")

    check("I10 the one-liner and the read-first form name the SAME url",
          url in INV.invite_link() and msg.count(url) >= 2,
          f"{url} appears {msg.count(url)}x")

    check("I11 the link is https and points at the raw file, not a web page",
          url.startswith("https://raw.githubusercontent.com/")
          and url.endswith("/" + INV.INSTALL_PATH), url)


def network_check():
    import urllib.error
    import urllib.request
    url = INV.install_url()
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            body, code = r.read(), r.status
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        not_run("N1 the derived link really serves mobile/install.sh",
                f"no network, or the remote refused ({type(e).__name__}) -- an "
                f"offline run must not be red")
        return
    local = os.path.join(HERE, "mobile", INV.INSTALL_PATH.split("/", 1)[1])
    same = None
    if os.path.exists(local):
        with open(local, "rb") as fh:
            same = fh.read().replace(b"\r\n", b"\n") == body.replace(b"\r\n", b"\n")
    check("N1 the derived link serves the install script this tree has",
          code == 200 and body.lstrip().startswith(b"#!")
          and (same is not False),
          f"http={code} bytes={len(body)} identical_to_local={same}")


def main():
    print("I1 -- the greeter: a derived link, and the line it does not cross\n")
    parse_checks()
    line_checks()
    shape_checks()
    network_check()
    ok = sum(1 for _, o, _ in results if o)
    print(f"\n{ok}/{len(results)} passed")
    if UNRUN:
        print(f"{len(UNRUN)} section(s) NOT RUN -- do not read this as covered:")
        for n, why in UNRUN:
            print(f"  - {n}: {why}")
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
