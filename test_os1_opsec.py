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
  OS1i  against a real bare remote: commits the remote already holds are not what a push
        publishes (moving a branch onto them passes); a new value on top is refused; an old
        tip this clone lacks and an unreachable remote both still refuse it; outgoing commits
        git cannot read, or a read that fails, refuse the push (2026-09-26, A231).

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

    print("OS1i -- what the remote already holds is not what a push publishes; what cannot be read is refused")
    if not shutil.which("git"):
        not_run("OS1i the push guard against a remote", "no git on this machine")
    else:
        # 2026-09-26 (A231): moving sentinel-witness onto main was refused for values main had published long
        # before (the range ran from the old tip of the one ref), and a remote tip this clone did not have made
        # git log fail, which read as 'nothing added' -- a new value went through.
        base = tempfile.mkdtemp(prefix="os1i_")
        bare, wk = os.path.join(base, "remote.git"), os.path.join(base, "work")
        env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.org",
                   GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.org")
        subprocess.run(["git", "init", "-q", "--bare", bare], env=env, capture_output=True)
        git(base, "init", "-q", wk, env=env)
        git(wk, "remote", "add", "origin", bare, env=env)

        def commit2(name, text, msg):
            open(os.path.join(wk, name), "w").write(text)
            git(wk, "add", name, env=env)
            git(wk, "commit", "-q", "-m", msg, env=env)
            return git(wk, "rev-parse", "HEAD").stdout.strip()
        a2 = commit2("f.md", "clean\n", "first")
        git(wk, "branch", "-M", "main", env=env)
        git(wk, "push", "-q", "--no-verify", "origin", "main:side", env=env)
        commit2("f.md", "phone at 100.72.1.3:5001\n", "published long ago")
        c2 = commit2("g.md", "ok\n", "clean")
        git(wk, "push", "-q", "--no-verify", "origin", "main", env=env)
        d2 = commit2("h.md", "fresh 100.72.1.3\n", "a new value")
        quiet = lambda *_a: None  # noqa: E731
        ref = lambda name, new, old: "refs/heads/%s %s refs/heads/%s %s" % (name, new, name, old)  # noqa: E731
        said = []
        rc_move = O.pre_push([ref("side", c2, a2)], root=wk, toks=toks, env={}, say=said.append, remote="origin")
        check("OS1i moving a branch onto commits the remote already holds publishes nothing, and is let through",
              rc_move == 0 and "0 outgoing commit(s)" in " ".join(said) and "asked the remote" in " ".join(said), said[:1])
        check("OS1i a new commit with a value on top of them is still refused",
              O.pre_push([ref("main", d2, c2)], root=wk, toks=toks, env={}, say=quiet, remote="origin") == 1)
        check("OS1i an old tip this clone does not have is not trusted: the new value is still refused",
              O.pre_push([ref("main", d2, "1" * 40)], root=wk, toks=toks, env={}, say=quiet, remote="origin") == 1)
        said_fb = []
        saved_ok = O._run_ok                    # the remote's own url, and ls-remote failing (offline, auth, timeout)
        O._run_ok = lambda args, timeout=15, stdin=None: (False, "") if "ls-remote" in args else saved_ok(args, timeout, stdin)
        try:
            rc_fb = O.pre_push([ref("main", d2, "1" * 40)], root=wk, toks=toks, env={}, say=said_fb.append,
                               remote=bare, remote_name="origin")
        finally:
            O._run_ok = saved_ok
        check("OS1i with the remote unreachable, the clone's copies of its branches stand in, and the new value is refused",
              rc_fb == 1 and "remote not reached" in " ".join(said_fb) and len([s for s in said_fb if s.startswith("  ")]) == 1,
              said_fb[:3])
        said2 = []
        rc_unread = O.pre_push([ref("main", "2" * 40, c2)], root=wk, toks=toks, env={}, say=said2.append, remote="origin")
        check("OS1i outgoing commits git cannot read are refused as NOT MEASURED, never read as 'nothing added'",
              rc_unread == 1 and "NOT MEASURED" in " ".join(said2), said2[:1])
        saved_rb = O._run_bytes
        O._run_bytes = lambda args, timeout=300, stdin=b"": (False, b"") if "cat-file" in args else saved_rb(args, timeout, stdin)
        try:
            rc_timeout = O.pre_push([ref("main", d2, c2)], root=wk, toks=toks, env={}, say=quiet, remote="origin")
        finally:
            O._run_bytes = saved_rb
        check("OS1i a read that fails or times out refuses the push", rc_timeout == 1, rc_timeout)

    print("OS1j -- every way past the guard an adversarial review reproduced, 2026-09-26 (A231)")
    if not shutil.which("git"):
        not_run("OS1j the object scan", "no git on this machine")
    else:
        base = tempfile.mkdtemp(prefix="os1j_")
        bare, wk = os.path.join(base, "remote.git"), os.path.join(base, "work")
        env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.org",
                   GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.org")
        subprocess.run(["git", "init", "-q", "--bare", bare], env=env, capture_output=True)
        git(base, "init", "-q", wk, env=env)
        git(wk, "remote", "add", "origin", bare, env=env)

        def put(name, data, msg="c"):
            full = os.path.join(wk, name)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "wb") as fh:
                fh.write(data)
            git(wk, "add", "-A", env=env)
            git(wk, "commit", "-q", "-m", msg, env=env)
            return git(wk, "rev-parse", "HEAD").stdout.strip()
        root0 = put("a.md", b"clean\n", "first")
        git(wk, "branch", "-M", "main", env=env)
        git(wk, "push", "-q", "--no-verify", "origin", "main", env=env)
        head = lambda: git(wk, "rev-parse", "HEAD").stdout.strip()  # noqa: E731
        ref = lambda name, new, old: "%s %s %s %s" % (name, new, name, old)  # noqa: E731

        def refused(label, new, refname="refs/heads/main", old=None):
            said = []
            rc = O.pre_push([ref(refname, new, old or root0)], root=wk, toks=toks, env={}, say=said.append, remote="origin")
            check("OS1j " + label, rc == 1 and any("tailnet-ip" in s or "private-person" in s for s in said), said[:3])
            git(wk, "reset", "-q", "--hard", root0, env=env)
        refused("an annotated tag's MESSAGE (on a commit the remote holds) is refused",
                (git(wk, "tag", "-a", "t1", "-m", "node at 100.72.1.3", root0, env=env), git(wk, "rev-parse", "t1").stdout.strip())[1],
                "refs/tags/t1", O.ZERO)
        git(wk, "tag", "-a", "inner", "-m", "inner 100.72.1.3", root0, env=env)
        git(wk, "tag", "-a", "outer", "-m", "outer clean", "inner", env=env)
        refused("a value in a tag NESTED inside a clean one is refused", git(wk, "rev-parse", "outer").stdout.strip(),
                "refs/tags/outer", O.ZERO)
        blob = subprocess.run(["git", "-C", wk, "hash-object", "-w", "--stdin"], input="peer 100.72.1.3\n",
                              capture_output=True, text=True, env=env).stdout.strip()
        refused("a bare blob pushed to a non-branch ref is refused", blob, "refs/leakstash/x", O.ZERO)
        git(wk, "checkout", "-q", "-b", "side", env=env)
        side = put("s.md", b"s\n", "side")
        git(wk, "checkout", "-q", "main", env=env)
        put("m.md", b"m\n", "main2")
        git(wk, "merge", "-q", "--no-commit", "--no-ff", "side", env=env)
        with open(os.path.join(wk, "evil.md"), "w") as fh:
            fh.write("peer 100.72.1.3\n")
        git(wk, "add", "evil.md", env=env)
        git(wk, "commit", "-q", "-m", "merge", env=env)
        refused("a file a MERGE commit adds is refused", head())
        git(wk, "branch", "-q", "-D", "side", env=env)
        refused("a UTF-16 file (PowerShell 5.1's default) is refused", put("n.txt", "peer 100.72.1.3\r\n".encode("utf-16")))
        refused("a value after a FORM FEED on its line is refused", put("f.py", b"x = 1\n\x0cHOST = '100.72.1.3'\n"))
        refused("a value after a bare CR is refused", put("p.log", b"progress 10%\rpeer 100.72.1.3 ok\n"))
        refused("an added line starting '++' is refused", put("l.md", b"++ peer 100.72.1.3\n"))
        refused("a value in a new FILE NAME (empty file) is refused", put("peer_100.72.1.3_5001.json", b""))
        put("people/contact.md", b"notes\n", "add")
        git(wk, "push", "-q", "--no-verify", "origin", "main", env=env)
        pushed = head()
        git(wk, "mv", "people/contact.md", "people/Zelphine.md", env=env)
        git(wk, "commit", "-q", "-m", "rename", env=env)
        refused("a PURE RENAME to a name carrying a value is refused", head(), old=pushed)
        git(wk, "reset", "-q", "--hard", pushed, env=env)
        root0 = pushed
        refused("a value in the commit AUTHOR field is refused",
                (git(wk, "commit", "-q", "--allow-empty", "-m", "x", "--author", "Zelphine <z@example.org>", env=env), head())[1])
        # the two regressions the first version of the new range brought, found by the same review. First, a value
        # the remote published long ago, so a guard that forgets what the remote holds has something to blame.
        put("old.md", b"phone at 100.72.1.3\n", "published long ago")
        git(wk, "push", "-q", "--no-verify", "origin", "main", env=env)
        other = os.path.join(base, "other")
        subprocess.run(["git", "clone", "-q", bare, other], env=env, capture_output=True)
        with open(os.path.join(other, "o.md"), "w") as fh:
            fh.write("o\n")
        git(other, "add", "o.md", env=env)
        git(other, "commit", "-q", "-m", "moved on elsewhere", env=env)
        git(other, "push", "-q", "--no-verify", "origin", "main", env=env)
        git(wk, "checkout", "-q", "-b", "feature", env=env)
        clean = put("feature.md", b"clean work\n", "feature")
        said = []
        rc_behind = O.pre_push([ref("refs/heads/feature", clean, O.ZERO)], root=wk, toks=[("tailnet-ip", "100.72.1.3")],
                               env={}, say=said.append, remote="origin")
        check("OS1j a clone BEHIND the remote pushes a clean new branch: let through (its copies of the remote's branches count)",
              rc_behind == 0, said[:2])
        backup = os.path.join(base, "backup.git")
        subprocess.run(["git", "init", "-q", "--bare", backup], env=env, capture_output=True)
        git(wk, "remote", "add", "backup", backup, env=env)
        leak = put("b.md", b"peer 100.72.1.3\n", "to the private backup only")
        git(wk, "push", "-q", "--no-verify", "backup", "feature", env=env)
        saved_ok = O._run_ok
        O._run_ok = lambda args, timeout=15, stdin=None: (False, "") if "ls-remote" in args else saved_ok(args, timeout, stdin)
        try:
            rc_backup = O.pre_push([ref("refs/heads/feature", leak, O.ZERO)], root=wk, toks=toks, env={}, say=quiet,
                                   remote=bare, remote_name="origin")
        finally:
            O._run_ok = saved_ok
        check("OS1j with the remote unreachable, ANOTHER remote's copies never stand in: a value only on the backup is refused",
              rc_backup == 1, rc_backup)
        refs, bad = O.parse_push_lines(("refs/heads/là-bas %s refs/heads/là-bas %s\n" % (leak, O.ZERO)).encode("utf-8"))
        check("OS1j a push line with a non-ASCII branch name parses as UTF-8, whole", len(refs) == 1 and not bad, (refs, bad))
        said = []
        rc_bad = O.pre_push(["refs/heads/x not-a-sha refs/heads/x %s" % O.ZERO], root=wk, toks=toks, env={}, say=said.append)
        check("OS1j a push line that does not parse refuses the push (NOT MEASURED), never drops out", rc_bad == 1
              and "NOT MEASURED" in " ".join(said), said[:1])
        said = []
        O.pre_push([ref("refs/heads/feature", put("people/Zelphine.md", b"Zelphine\n", "n"), O.ZERO)], root=wk, toks=toks,
                   env={}, say=said.append, remote="origin")
        check("OS1j a refusal masks values in the paths it prints", said and not any("Zelphine" in s for s in said), said[:4])

    print("OS1k -- round 2 of the review, 2026-09-26 (A231): forms, sources, remotes, worktrees")
    if not shutil.which("git"):
        not_run("OS1k the round-2 cases", "no git on this machine")
    else:
        base = tempfile.mkdtemp(prefix="os1k_")
        bare, wk = os.path.join(base, "r.git"), os.path.join(base, "w")
        env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.org",
                   GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.org")
        subprocess.run(["git", "init", "-q", "--bare", bare], env=env, capture_output=True)
        git(base, "init", "-q", wk, env=env)
        git(wk, "remote", "add", "origin", bare, env=env)

        def put(name, data, msg="c"):
            full = os.path.join(wk, name)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "wb") as fh:
                fh.write(data)
            git(wk, "add", "-A", env=env)
            git(wk, "commit", "-q", "-m", msg, env=env)
            return git(wk, "rev-parse", "HEAD").stdout.strip()
        r0 = put("a.md", b"clean\n", "first")
        git(wk, "branch", "-M", "main", env=env)
        git(wk, "push", "-q", "--no-verify", "origin", "main", env=env)
        WAL = "0x" + "aB3dE5f7" * 5
        V6 = "fd7a:115c:a1e0::1:2"
        k_toks = [("wallet-address", WAL), ("tailnet-ip", V6), ("device-name", "Quorvath's Pixel"),
                  ("device-name", "vantrell-desk"), ("wifi-name", "Brindlemoor Home"), ("private-person", "Zélphine"),
                  ("private-person", "Bkk"), ("tailnet-ip", "100.72.1.3")]

        def verdict(new, toks_=None, **kw):
            said = []
            rc = O.pre_push(["refs/heads/main %s refs/heads/main %s" % (new, r0)], root=wk, toks=toks_ or k_toks, env={},
                            say=said.append, remote="origin", **kw)
            git(wk, "reset", "-q", "--hard", r0, env=env)
            return rc, said

        forms = [
            ("the wallet LOWER-CASED (covenant_earn compares addresses that way)", ("to: %s\n" % WAL.lower()).encode()),
            ("the wallet zero-padded into a log topic, no 0x in front", ("0x%s%s\n" % ("0" * 24, WAL[2:].lower())).encode()),
            ("an IPv6 address in UPPER CASE", ("peer %s\n" % V6.upper()).encode()),
            ("a device name with a CURLY apostrophe", "Quorvath’s Pixel\n".encode("utf-8")),
            ("a device name through json.dumps (\\u2019)", (json.dumps({"n": "Quorvath’s Pixel"}) + "\n").encode()),
            ("a device name through PowerShell's ConvertTo-Json (\\u0027)", b'{"n": "Quorvath\\u0027s Pixel"}\n'),
            ("a device name with a NON-BREAKING hyphen", "vantrell‑desk\n".encode("utf-8")),
            ("a Wi-Fi name with a NO-BREAK space", "Brindlemoor Home\n".encode("utf-8")),
            ("a Wi-Fi name as an HTML entity (&nbsp;)", b"Brindlemoor&nbsp;Home\n"),
            ("an accented name through json.dumps (\\u00e9)", (json.dumps({"who": "Zélphine"}) + "\n").encode()),
            ("an accented name in cp1252 bytes (open() with no encoding here)", "met Zélphine\n".encode("cp1252")),
            ("an accented name in NFD", "met Zélphine\n".encode("utf-8")),
            ("an accented name as an HTML entity", b"met Z&eacute;lphine\n"),
            ("a file in UTF-32", "peer 100.72.1.3\n".encode("utf-32")),
            ("a name inside a binary's printable text", b"\x00\x01\x02 note: ask Bkk about it \x00\x03"),
        ]
        for i, (label, data) in enumerate(forms):
            rc, said = verdict(put("f%d.dat" % i, data))
            check("OS1k refused: " + label, rc == 1, said[:2])
        rc, said = verdict(put("z.bin", b"\x00\x9c\x11Bkk\x02\x00\xff\x13"))
        check("OS1k let through: a 3-letter name that occurs only by chance inside compressed bytes", rc == 0, said[:2])
        refs, bad = O.parse_push_lines(":/fix typo %s refs/heads/snap %s\n" % (r0, O.ZERO))
        check("OS1k a refspec whose local side holds a space parses (from the right)", len(refs) == 1 and not bad, (refs, bad))
        # the private sources, as Windows tools save them
        src = tempfile.mkdtemp(prefix="os1k_src_")
        os.makedirs(os.path.join(src, "private"))
        os.makedirs(os.path.join(src, "ops"))
        with open(os.path.join(src, "private", "bystanders.txt"), "wb") as fh:
            fh.write(b"\xef\xbb\xbfZelphine\r\nQuorvath\r\n")
        got = O.tokens_from_files(src)
        check("OS1k a bystander list with a UTF-8 BOM (PowerShell's '>' here) yields its FIRST name clean",
              ("private-person", "Zelphine") in got, got)
        with open(os.path.join(src, "private", "bystanders.txt"), "wb") as fh:
            fh.write("Zelphine\r\nQuorvath\r\n".encode("utf-16"))
        got = O.tokens_from_files(src)
        check("OS1k a bystander list in UTF-16 yields both names", ("private-person", "Zelphine") in got
              and ("private-person", "Quorvath") in got, got)
        with open(os.path.join(src, "ops", "earn_grant.json"), "w") as fh:
            fh.write('{"pay_to": "%s",}' % WAL)
        O.tokens_from_files(src)
        check("OS1k a grant that does not parse is recorded as unreadable, not passed over", bool(O.UNREADABLE), O.UNREADABLE)
        saved_gather = O.gather
        O.gather = lambda root=None, **kw: (O.UNREADABLE.append("ops/earn_grant.json (test)") or [("tailnet-ip", "100.72.1.3")])
        try:
            said = []
            rc = O.pre_push(["refs/heads/main %s refs/heads/main %s" % (put("clean.md", b"clean\n"), r0)], root=wk, env={},
                            say=said.append, remote="origin")
            git(wk, "reset", "-q", "--hard", r0, env=env)
        finally:
            O.gather = saved_gather
            del O.UNREADABLE[:]
        check("OS1k an unreadable private source refuses the push as NOT MEASURED, even for clean work",
              rc == 1 and "could not be read" in " ".join(said), said[:1])
        # a push url set apart from the fetch url: copies fetched privately prove nothing about the public side
        priv, pub = os.path.join(base, "priv.git"), os.path.join(base, "pub.git")
        for b_ in (priv, pub):
            subprocess.run(["git", "init", "-q", "--bare", b_], env=env, capture_output=True)
        git(wk, "remote", "add", "tri", priv, env=env)
        git(wk, "remote", "set-url", "--push", "tri", pub, env=env)
        leak = put("peers.txt", b"peer 100.72.1.3\n", "private only")
        git(wk, "push", "-q", "--no-verify", priv, "main", env=env)
        git(wk, "fetch", "-q", "tri", env=env)
        said = []
        rc = O.pre_push(["refs/heads/main %s refs/heads/main %s" % (leak, O.ZERO)], root=wk, toks=k_toks, env={},
                        say=said.append, remote=pub, remote_name="tri")
        git(wk, "reset", "-q", "--hard", r0, env=env)
        check("OS1k with a push url set apart from the fetch url, privately fetched copies do not count as published",
              rc == 1, said[:2])
        # the override must survive a report it cannot print in the console's code page
        wrapper = os.path.join(base, "run_main.py")
        with open(wrapper, "w", encoding="utf-8") as fh:
            fh.write("import sys\nsys.path.insert(0, %r)\nimport opsec_scan as O\nreal = O.pre_push\n"
                     "O.pre_push = lambda lines, **kw: real(lines, root=%r, toks=[('tailnet-ip', '100.72.1.3')], **kw)\n"
                     "O.OVERRIDES = %r\nsys.exit(O.main(['--pre-push', 'origin', %r]))\n"
                     % (os.path.join(HERE, "tools"), wk, os.path.join(base, "ov.jsonl"), bare))
        omega = put("Ωmega/p.txt", b"peer 100.72.1.3\n")
        clean_env = {k: v for k, v in os.environ.items() if not k.startswith("PYTHONIO") and k != "PYTHONUTF8"}
        p = subprocess.run([sys.executable, wrapper], input=("refs/heads/main %s refs/heads/main %s\n" % (omega, r0)).encode(),
                           capture_output=True, env=dict(clean_env, COVENANT_OPSEC_ALLOW="1"))
        git(wk, "reset", "-q", "--hard", r0, env=env)
        check("OS1k the override lets a push through even when a path cannot be printed in the console's code page",
              p.returncode == 0 and b"Traceback" not in p.stderr, (p.returncode, p.stderr[-200:]))
        # the hook itself, from a worktree checked out before the tool existed
        if shutil.which("sh"):
            hk = os.path.join(base, "hk")
            git(base, "init", "-q", hk, env=env)
            git(hk, "remote", "add", "origin", bare, env=env)
            with open(os.path.join(hk, "old.md"), "w") as fh:
                fh.write("before the guard\n")
            git(hk, "add", "-A", env=env)
            git(hk, "commit", "-q", "-m", "old", env=env)
            git(hk, "branch", "-M", "main", env=env)
            git(hk, "branch", "old-line", env=env)
            os.makedirs(os.path.join(hk, "tools"))
            os.makedirs(os.path.join(hk, "private"))
            shutil.copyfile(os.path.join(HERE, "tools", "opsec_scan.py"), os.path.join(hk, "tools", "opsec_scan.py"))
            with open(os.path.join(hk, "private", "bystanders.txt"), "w") as fh:
                fh.write("Quorvathine\n")
            with open(os.path.join(hk, ".gitignore"), "w") as fh:
                fh.write("private/\n")
            git(hk, "add", "-A", env=env)
            git(hk, "commit", "-q", "-m", "the guard", env=env)
            shutil.copyfile(os.path.join(HERE, "ops", "pre-push.opsec"), os.path.join(hk, ".git", "hooks", "pre-push"))
            wt = os.path.join(base, "wt")
            git(hk, "worktree", "add", "-q", wt, "old-line", env=env)
            with open(os.path.join(wt, "n.md"), "w") as fh:
                fh.write("met Quorvathine today\n")
            git(wt, "add", "-A", env=env)
            git(wt, "commit", "-q", "-m", "from the old worktree", env=env)
            leaked_push = git(wt, "push", "origin", "old-line", env=env)
            on_remote = git(bare, "rev-parse", "--verify", "-q", "refs/heads/old-line").returncode == 0
            check("OS1k a push from a worktree checked out BEFORE the tool existed is still checked, by the main "
                  "worktree's guard, and refused", leaked_push.returncode != 0 and not on_remote
                  and "can't open file" not in leaked_push.stderr, leaked_push.stderr[-300:])
            git(wt, "reset", "-q", "--hard", "HEAD~1", env=env)
            with open(os.path.join(wt, "c.md"), "w") as fh:
                fh.write("clean\n")
            git(wt, "add", "-A", env=env)
            git(wt, "commit", "-q", "-m", "clean", env=env)
            clean_push = git(wt, "push", "origin", "old-line", env=env)
            check("OS1k ...and clean work from that worktree goes through", clean_push.returncode == 0, clean_push.stderr[-300:])
        else:
            not_run("OS1k the hook from an old worktree", "no sh on this machine")

    print("OS1l -- round 3 of the review, 2026-09-26 (A231): what git sends, and the hook's layouts")
    if not shutil.which("git"):
        not_run("OS1l the round-3 cases", "no git on this machine")
    else:
        base = tempfile.mkdtemp(prefix="os1l_")
        bare, wk = os.path.join(base, "r.git"), os.path.join(base, "w")
        env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.org",
                   GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.org")
        subprocess.run(["git", "init", "-q", "--bare", bare], env=env, capture_output=True)
        git(base, "init", "-q", wk, env=env)

        def put(name, data, msg="c"):
            with open(os.path.join(wk, name), "wb") as fh:
                fh.write(data)
            git(wk, "add", "-A", env=env)
            git(wk, "commit", "-q", "-m", msg, env=env)
            return git(wk, "rev-parse", "HEAD").stdout.strip()
        l0 = put("a.md", b"clean\n", "first")
        git(wk, "branch", "-M", "main", env=env)
        git(wk, "push", "-q", "--no-verify", bare, "main", env=env)
        l_toks = [("tailnet-ip", "100.72.1.3"), ("device-name", "vantrel"), ("private-person", "Zelphine")]
        line_ = lambda new: "refs/heads/main %s refs/heads/main %s" % (new, l0)  # noqa: E731
        leaky = put("leak.md", b"peer 100.72.1.3\n", "leaky")
        git(wk, "checkout", "-q", "--detach", l0, env=env)
        stand_in = put("clean.md", b"clean\n", "clean stand-in")
        git(wk, "checkout", "-q", "main", env=env)
        git(wk, "replace", leaky, stand_in, env=env)
        rc = O.pre_push([line_(leaky)], root=wk, toks=l_toks, env={}, say=lambda *_a: None, remote=bare)
        check("OS1l a local refs/replace entry does not hide the commit `git push` sends (it sends the original)", rc == 1, rc)
        git(wk, "replace", "-d", leaky, env=env)
        git(wk, "reset", "-q", "--hard", l0, env=env)
        tree = git(wk, "rev-parse", "HEAD^{tree}").stdout.strip()
        raw = ("tree %s\nparent %s\nauthor t <t@example.org> 0 +0000\ncommitter t <t@example.org> 0 +0000\n"
               "encoding UTF-16\n\n" % (tree, l0)).encode() + "note: ask Zelphine\n".encode("utf-16")
        u16 = subprocess.run(["git", "-C", wk, "hash-object", "-t", "commit", "-w", "--stdin", "--literally"],
                             input=raw, capture_output=True, env=env).stdout.decode().strip()
        rc = O.pre_push([line_(u16)], root=wk, toks=l_toks, env={}, say=lambda *_a: None, remote=bare)
        check("OS1l a commit message stored in UTF-16 (an 'encoding' header) is read, and refused", rc == 1, (u16, rc))
        rc = O.pre_push([line_(put("x.bin", b"\x00\x13\x7fvantrel\x00\x02"))], root=wk, toks=l_toks, env={},
                        say=lambda *_a: None, remote=bare)
        git(wk, "reset", "-q", "--hard", l0, env=env)
        check("OS1l a 7-character device name stored alone between NULs (a C string) is refused", rc == 1, rc)
        src = tempfile.mkdtemp(prefix="os1l_src_")
        os.makedirs(os.path.join(src, "private"))
        with open(os.path.join(src, "private", "bystanders.txt"), "w", encoding="utf-8") as fh:
            fh.write("Zelphine​\n")
        got = O.tokens_from_files(src)
        check("OS1l a bystander entry with a pasted zero-width space yields the plain name", ("private-person", "Zelphine") in got, got)
        if shutil.which("sh"):
            # the hook, in the two layouts round 3 broke: the main worktree checked out to a commit without the tool,
            # and a separated git dir (the main worktree is not beside the repository)
            hk = os.path.join(base, "hk")
            git(base, "init", "-q", hk, env=env)
            with open(os.path.join(hk, "old.md"), "w") as fh:
                fh.write("before the guard\n")
            git(hk, "add", "-A", env=env)
            git(hk, "commit", "-q", "-m", "old", env=env)
            git(hk, "branch", "-M", "main", env=env)
            old = git(hk, "rev-parse", "HEAD", env=env).stdout.strip()
            os.makedirs(os.path.join(hk, "tools"))
            os.makedirs(os.path.join(hk, "private"))
            shutil.copyfile(os.path.join(HERE, "tools", "opsec_scan.py"), os.path.join(hk, "tools", "opsec_scan.py"))
            with open(os.path.join(hk, "private", "bystanders.txt"), "w") as fh:
                fh.write("Quorvathine\n")
            with open(os.path.join(hk, ".gitignore"), "w") as fh:
                fh.write("private/\n")
            git(hk, "add", "-A", env=env)
            git(hk, "commit", "-q", "-m", "the guard", env=env)
            shutil.copyfile(os.path.join(HERE, "ops", "pre-push.opsec"), os.path.join(hk, ".git", "hooks", "pre-push"))
            git(hk, "remote", "add", "origin", bare, env=env)
            wt = os.path.join(base, "wt")
            git(hk, "worktree", "add", "-q", "-b", "side", wt, "main", env=env)
            git(hk, "checkout", "-q", "--detach", old, env=env)          # the tool leaves the main worktree's disk
            with open(os.path.join(wt, "n.md"), "w") as fh:
                fh.write("met Quorvathine\n")
            git(wt, "add", "-A", env=env)
            git(wt, "commit", "-q", "-m", "leak", env=env)
            p1 = git(wt, "push", "origin", "side", env=env)
            git(wt, "reset", "-q", "--hard", "HEAD~1", env=env)
            with open(os.path.join(wt, "c.md"), "w") as fh:
                fh.write("clean\n")
            git(wt, "add", "-A", env=env)
            git(wt, "commit", "-q", "-m", "clean", env=env)
            p2 = git(wt, "push", "origin", "side", env=env)
            check("OS1l main worktree on an old commit: a push from another worktree is still checked (the main "
                  "branch's copy) -- the value refused, clean work through", p1.returncode != 0 and p2.returncode == 0,
                  (p1.stderr[-200:], p2.stderr[-200:]))
            gd, sw = os.path.join(base, "sep.git"), os.path.join(base, "sep")
            subprocess.run(["git", "init", "-q", "--separate-git-dir", gd, sw], env=env, capture_output=True)
            os.makedirs(os.path.join(sw, "tools"))
            os.makedirs(os.path.join(sw, "private"))
            shutil.copyfile(os.path.join(HERE, "tools", "opsec_scan.py"), os.path.join(sw, "tools", "opsec_scan.py"))
            with open(os.path.join(sw, "private", "bystanders.txt"), "w") as fh:
                fh.write("Quorvathine\n")
            with open(os.path.join(sw, ".gitignore"), "w") as fh:
                fh.write("private/\n")
            git(sw, "add", "-A", env=env)
            git(sw, "commit", "-q", "-m", "the guard", env=env)
            git(sw, "branch", "-M", "main", env=env)
            shutil.copyfile(os.path.join(HERE, "ops", "pre-push.opsec"), os.path.join(gd, "hooks", "pre-push"))
            git(sw, "remote", "add", "origin", bare, env=env)
            p3 = git(sw, "push", "origin", "main:sep-main", env=env)
            with open(os.path.join(sw, "n.md"), "w") as fh:
                fh.write("met Quorvathine\n")
            git(sw, "add", "-A", env=env)
            git(sw, "commit", "-q", "-m", "leak", env=env)
            p4 = git(sw, "push", "origin", "main:sep-main", env=env)
            check("OS1l a separated git dir: clean work goes through and the value is refused",
                  p3.returncode == 0 and p4.returncode != 0, (p3.stderr[-200:], p4.stderr[-200:]))
        else:
            not_run("OS1l the hook's layouts", "no sh on this machine")


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
