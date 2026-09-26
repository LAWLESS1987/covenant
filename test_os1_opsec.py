#!/usr/bin/env python3
"""OS1 -- his identifiers stay out of the public repository, by default.

His words, 2026-09-26: "take the portfolio id out of the public file protect operation
security in all we do by default". tools/opsec_scan.py reads his identifiers at run time
from where they live privately and checks what would be published; ops/pre-push.opsec
runs it on every push.

  OS1a  Tailscale's status becomes tokens of the right kind: this PC, its peers, the
        public and LAN endpoints Tailscale found, the tailnet's names.
  OS1b  the private files become tokens: Syncthing ids, the grant's account id and
        wallet, the people in bystanders.txt, LAN callers in the heal log.
  OS1c  an address is found in every form a file writes it (peer_<ip>_5001, <ip>:5001)
        and not inside a longer number; nothing it reports carries the raw value.
  OS1d  --fix labels records and docs and leaves code alone (a label there stops a node).
  OS1e  a value he publishes by choice (listed by hash) is not a token.
  OS1f  the push guard, on a real temporary repository: a value added and removed inside
        one push is refused, a value in a commit message is refused, a clean push passes,
        and his override lets one through and is logged.
  OS1g  THIS machine: no tracked file carries an identifier read from its private
        sources. NOT RUN (never counted) where there is no git index or no private source
        -- the staged sweep copy and a fresh clone -- because an empty list is not "clean".
  OS1h  the hook source runs the guard, and where this clone has hooks it is installed.

Every case is driven both ways.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__)) or "."
sys.path.insert(0, os.path.join(HERE, "tools"))
import opsec_scan as O  # noqa: E402

PASSED, FAILURES, NOT_RUN = [0], [], []


def check(label, ok, detail=""):
    print("  %-78s %s" % (label[:78], "OK" if ok else "*** FAIL ***  %s" % str(detail)[:300]))
    if ok:
        PASSED[0] += 1
    else:
        FAILURES.append(label)


def not_run(label, why):
    print("  %-78s NOT RUN (%s)" % (label[:78], why))
    NOT_RUN.append(label)


# Values below are invented: documentation ranges, a made-up tailnet, made-up names.
STATUS = {
    "Self": {"TailscaleIPs": ["100.72.1.2", "fd7a:115c:a1e0::aa"], "DNSName": "desktop-zz9.tail0000.ts.net.",
             "HostName": "desktop-zz9", "Addrs": ["8.8.4.4:41641", "192.168.55.4:41641", "203.0.113.9:41641"]},
    "Peer": {"k": {"TailscaleIPs": ["100.72.1.3"], "DNSName": "handset-q1.tail0000.ts.net.", "HostName": "handset-q1"}},
    "MagicDNSSuffix": "tail0000.ts.net",
    "CurrentTailnet": {"Name": "someone@example.org"},
}


def cats(toks):
    d = {}
    for c, v in toks:
        d.setdefault(c, set()).add(v)
    return d


def git(repo, *args, env=None):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, env=env)


def main():
    print("OS1a -- Tailscale's status")
    d = cats(O.tokens_from_tailscale(STATUS))
    check("OS1a this PC's addresses are pc-tailnet-ip, a peer's are tailnet-ip",
          d.get("pc-tailnet-ip") == {"100.72.1.2", "fd7a:115c:a1e0::aa"} and d.get("tailnet-ip") == {"100.72.1.3"}, d)
    # 8.8.4.4 is a public DNS service, nobody's home; 203.0.113.9 is a documentation address
    check("OS1a a public endpoint is home-public-ip, a LAN endpoint lan-ip, a documentation address neither",
          d.get("home-public-ip") == {"8.8.4.4"} and d.get("lan-ip") == {"192.168.55.4"}
          and not any("203.0.113.9" in vs for vs in d.values()), d)
    check("OS1a device and tailnet names are tokens; nothing is invented from an empty status",
          {"desktop-zz9", "handset-q1"} <= d.get("device-name", set()) and "tail0000.ts.net" in d.get("tailnet-name", set())
          and O.tokens_from_tailscale({}) == [], d)

    print("OS1b -- the private files")
    td = tempfile.mkdtemp(prefix="os1b_")
    os.makedirs(os.path.join(td, "ops", "syncthing"))
    os.makedirs(os.path.join(td, "private"))
    sid = "-".join(["ABCDEFG"] * 8)
    open(os.path.join(td, "ops", "syncthing", "config.xml"), "w").write('<device id="%s" name="x"/>' % sid)
    uid, wal = "0123abcd-0000-4000-8000-00000000beef", "0x" + "ab" * 20
    json.dump({"a": {"b": [uid]}, "pay_to": wal, "note": "plain words"}, open(os.path.join(td, "ops", "earn_grant.json"), "w"))
    open(os.path.join(td, "private", "bystanders.txt"), "w").write("# comment\nZelphine\n")
    open(os.path.join(td, "ops", "heal.jsonl"), "w").write('{"who": "press:10.9.8.7"}\n')
    d = cats(O.tokens_from_files(td))
    check("OS1b syncthing id, account id, wallet, bystander and heal-log LAN caller all read",
          d.get("syncthing-device-id") == {sid} and d.get("account-id") == {uid} and d.get("wallet-address") == {wal}
          and d.get("private-person") == {"Zelphine"} and d.get("lan-ip") == {"10.9.8.7"}, d)
    check("OS1b a directory with none of them yields nothing", O.tokens_from_files(tempfile.mkdtemp()) == [])

    print("OS1c -- found in every form, never printed")
    toks = [("tailnet-ip", "100.72.1.3"), ("private-person", "Zelphine")]
    txt = "peer_100.72.1.3_5001 up\nhost 100.72.1.3:5001\nnot 100.72.1.31 nor 1100.72.1.3\nzelphine said\nZelphinex"
    hits = O.scan_text(txt, toks)
    check("OS1c peer_<ip>_5001, <ip>:5001 and a name in any case are found (lines 1, 2, 4)",
          sorted({n for n, _c, _m in hits}) == [1, 2, 4], hits)
    check("OS1c a longer number and a longer word are not the same value", not any(n in (3, 5) for n, _c, _m in hits), hits)
    check("OS1c no reported hit carries the raw value", all("100.72.1.3" not in m and "Zelphine" not in m for _n, _c, m in hits), hits)

    print("OS1d -- --fix labels records, not code")
    tf = tempfile.mkdtemp(prefix="os1d_")
    open(os.path.join(tf, "notes.md"), "w").write("the phone is 100.72.1.3:5001\n")
    open(os.path.join(tf, "run.py"), "w").write('PEERS = "100.72.1.3:5001"\n')
    fixed, left = O.fix_tree(tf, toks, files=["notes.md", "run.py"], say=lambda *_a: None)
    md, py = open(os.path.join(tf, "notes.md")).read(), open(os.path.join(tf, "run.py")).read()
    check("OS1d the record is labelled", "100.72.1.3" not in md and "<tailnet-ip>:5001" in md and fixed == {"notes.md": 1}, (md, fixed))
    check("OS1d the code is left as it was and reported", py == 'PEERS = "100.72.1.3:5001"\n' and list(left) == ["run.py"], (py, left))

    print("OS1e -- published by choice")
    pub = {O._sha("someone@example.org")}
    t1 = cats(O.gather(td, status=STATUS, system=False, public=pub))
    t2 = cats(O.gather(td, status=STATUS, system=False, public=set()))
    check("OS1e a value listed by hash is dropped, and only that value",
          "someone@example.org" not in t1.get("tailnet-name", set()) and "someone@example.org" in t2.get("tailnet-name", set())
          and "tail0000.ts.net" in t1.get("tailnet-name", set()), (t1.get("tailnet-name"), t2.get("tailnet-name")))
    real = O.public_by_choice()
    check("OS1e the tracked list holds hashes only (64 hex), never a value",
          all(len(h) == 64 and all(ch in "0123456789abcdef" for ch in h) for h in real), real)

    print("OS1f -- the push guard on a real repository")
    if not shutil.which("git"):
        not_run("OS1f the push guard", "no git on this machine")
    else:
        rp = tempfile.mkdtemp(prefix="os1f_")
        env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.org",
                   GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.org")
        git(rp, "init", "-q", env=env)

        def commit(name, text, msg):
            open(os.path.join(rp, name), "w").write(text)
            git(rp, "add", name, env=env)
            git(rp, "commit", "-q", "-m", msg, env=env)
            return git(rp, "rev-parse", "HEAD").stdout.strip()
        a = commit("f.md", "clean\n", "first")
        b = commit("f.md", "phone at 100.72.1.3:5001\n", "add")
        c = commit("f.md", "clean again\n", "remove")
        d_ = commit("g.md", "ok\n", "ping Zelphine about it")
        e = commit("h.md", "ok\n", "clean")
        quiet = lambda *_a: None  # noqa: E731
        line = lambda new, old: "refs/heads/main %s refs/heads/main %s" % (new, old)  # noqa: E731
        check("OS1f a value added then removed inside one push is refused (both commits would be public)",
              O.pre_push([line(c, a)], root=rp, toks=toks, env={}, say=quiet) == 1)
        check("OS1f a value in a commit MESSAGE is refused", O.pre_push([line(d_, c)], root=rp, toks=toks, env={}, say=quiet) == 1)
        check("OS1f a clean push passes", O.pre_push([line(e, d_)], root=rp, toks=toks, env={}, say=quiet) == 0)
        check("OS1f a new branch is checked from its first commit", O.pre_push([line(e, O.ZERO)], root=rp, toks=toks, env={}, say=quiet) == 1)
        saved = O.OVERRIDES
        O.OVERRIDES = os.path.join(rp, "overrides.jsonl")
        try:
            rc = O.pre_push([line(c, a)], root=rp, toks=toks, env={"COVENANT_OPSEC_ALLOW": "1"}, say=quiet)
            logged = open(O.OVERRIDES).read() if os.path.exists(O.OVERRIDES) else ""
        finally:
            O.OVERRIDES = saved
        check("OS1f his override lets one push through, and it is logged masked",
              rc == 0 and "tailnet-ip" in logged and "100.72.1.3" not in logged, (rc, logged[:200]))
        check("OS1f with no private source it says NOT MEASURED and does not refuse",
              O.pre_push([line(c, a)], root=rp, toks=[], env={}, say=quiet) == 0)

    print("OS1g -- this machine")
    files = O.tracked(HERE)
    live = O.gather(HERE)
    if not files:
        not_run("OS1g no tracked file carries his identifiers", "no git index here (the staged sweep copy)")
    elif not live:
        not_run("OS1g no tracked file carries his identifiers", "no private source on this machine (a fresh clone)")
    else:
        rep = O.scan_tree(HERE, live, files)
        check("OS1g %d identifier(s) from this machine's private sources: no tracked file carries one" % len(live),
              not rep, {f: [(n, c) for n, c, _m in h][:3] for f, h in list(rep.items())[:6]})

    print("OS1h -- the hook")
    src = os.path.join(HERE, "ops", "pre-push.opsec")
    body = open(src, encoding="utf-8").read() if os.path.exists(src) else ""
    check("OS1h ops/pre-push.opsec runs tools/opsec_scan.py --pre-push", "opsec_scan.py" in body and "--pre-push" in body)
    hooks = os.path.join(HERE, ".git", "hooks")
    if not os.path.isdir(hooks):
        not_run("OS1h the hook is installed in this clone", "no .git/hooks here")
    else:
        inst = os.path.join(hooks, "pre-push")
        got = open(inst, encoding="utf-8").read() if os.path.exists(inst) else ""
        check("OS1h .git/hooks/pre-push is the tracked guard, byte for byte", got == body, "missing or different")

    print()
    print("OS1: %d/%d passed%s" % (PASSED[0], PASSED[0] + len(FAILURES),
                                   (" (%d NOT RUN, not counted)" % len(NOT_RUN)) if NOT_RUN else ""))
    if FAILURES:
        print("OS1 result: FAILED (%d)" % len(FAILURES))
        for f in FAILURES:
            print("  - %s" % f)
        return 1
    print("OS1 result: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
