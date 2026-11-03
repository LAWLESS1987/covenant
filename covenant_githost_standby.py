#!/usr/bin/env python3
"""covenant_githost_standby.py -- a READ-ONLY, cross-OS cold standby for the git host.

WHY (A407, 2026-11-02; the operator: "install is fine towards mutual benefit just
use space wisely between pc laptop n phone"). The smart-HTTP git host
(~/githost/git_http_server.py) runs ONLY in the laptop's one WSL/Ubuntu -- a hard
SPOF (ops/PARALLEL_OS_REDUNDANCY_MAP). This is its cross-OS standby: the SAME
git-http-backend, found portably through `git --exec-path`, so one file serves on
Windows AND Linux. It serves clone/fetch (git-upload-pack) only and REFUSES push
(git-receive-pack) -- a read fallback, never a second writable master, so there is
no split-brain. Pushes stay on the primary.

SPACE-WISE. It is a COLD standby: provisioned (a mirror on disk, ~17 MB) but not
kept running. The laptop is RAM-tight (~3 GB free, ram_guard holds the model's
room), so covenant_failover starts this only when the primary git host is down
(start_githost_standby, AUTO_REVERSIBLE) and the resolver serves reads from it
until the primary returns. Heavy, always-on redundancy belongs on TETSU.

The mirror is kept fresh by `--refresh` (git remote update), which is also what
provisions it the first time (a bare --mirror clone of the primary).

RUN
  python covenant_githost_standby.py --refresh      # create/update the mirror from the primary
  python covenant_githost_standby.py --serve --port 8089
Then:  git clone http://127.0.0.1:8089/covenant.git
LICENCE: public domain.
"""
from __future__ import annotations

import argparse
import http.server
import os
import socketserver
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# The mirror lives OUTSIDE the repo tree (it is state, not source): a sibling dir.
DEFAULT_ROOT = os.path.join(os.path.expanduser("~"), ".covenant_githost_standby")
PRIMARY = os.environ.get("GITHOST_PRIMARY", "http://127.0.0.1:8088/covenant.git")
REPO_NAME = os.environ.get("GITHOST_REPO", "covenant.git")


def _backend():
    """git-http-backend, found through `git --exec-path` so this works on Windows
    (…/mingw64/libexec/git-core) and Linux (/usr/lib/git-core) alike."""
    try:
        ep = subprocess.run(["git", "--exec-path"], capture_output=True, text=True,
                            timeout=10).stdout.strip()
    except Exception:                                        # noqa: BLE001
        ep = ""
    for name in ("git-http-backend", "git-http-backend.exe"):
        c = os.path.join(ep, name) if ep else name
        if ep and os.path.exists(c):
            return c
    # last resort: let PATH resolve it
    return "git-http-backend"


def refresh(root=DEFAULT_ROOT, primary=PRIMARY, repo=REPO_NAME):
    """Create the bare mirror if absent, else update it from the primary. Returns (ok, msg)."""
    os.makedirs(root, exist_ok=True)
    path = os.path.join(root, repo)
    if not os.path.exists(path):
        r = subprocess.run(["git", "clone", "--mirror", primary, path], capture_output=True, text=True,
                           timeout=600)
        return (r.returncode == 0, "cloned mirror from %s" % primary if r.returncode == 0
                else "clone failed: %s" % (r.stderr or r.stdout)[:200])
    r = subprocess.run(["git", "--git-dir", path, "remote", "update", "--prune"],
                       capture_output=True, text=True, timeout=300)
    return (r.returncode == 0, "mirror updated" if r.returncode == 0
            else "update failed: %s" % (r.stderr or r.stdout)[:200])


def make_handler(root):
    backend = _backend()

    class H(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def _reject_push(self, path, qs):
            # READ-ONLY: receive-pack (push) is refused outright. This standby is never a master.
            return path.endswith("/git-receive-pack") or "service=git-receive-pack" in qs

        def _serve(self):
            path = self.path.split("?", 1)[0]
            qs = self.path.split("?", 1)[1] if "?" in self.path else ""
            if self._reject_push(path, qs):
                self.send_response(403)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            env = dict(os.environ)
            env.update(GIT_PROJECT_ROOT=root, GIT_HTTP_EXPORT_ALL="1", PATH_INFO=path,
                       QUERY_STRING=qs, REQUEST_METHOD=self.command,
                       CONTENT_TYPE=self.headers.get("Content-Type", ""),
                       REMOTE_ADDR=self.client_address[0], REMOTE_USER="")
            n = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(n) if n else b""
            p = subprocess.run([backend], input=body, env=env, cwd=root, capture_output=True)
            out = p.stdout
            i = out.find(b"\r\n\r\n"); sl = 4
            if i < 0:
                i = out.find(b"\n\n"); sl = 2
            head, rest = (out[:i], out[i + sl:]) if i >= 0 else (b"", out)
            status, hdrs = 200, []
            for line in head.replace(b"\r\n", b"\n").split(b"\n"):
                if not line:
                    continue
                if line.lower().startswith(b"status:"):
                    try:
                        status = int(line.split(b":", 1)[1].split()[0])
                    except Exception:                        # noqa: BLE001
                        status = 200
                else:
                    k, _, v = line.partition(b":")
                    hdrs.append((k.strip().decode(), v.strip().decode()))
            self.send_response(status)
            have_len = any(k.lower() == "content-length" for k, _ in hdrs)
            for k, v in hdrs:
                self.send_header(k, v)
            if not have_len:
                self.send_header("Content-Length", str(len(rest)))
            self.end_headers()
            self.wfile.write(rest)

        do_GET = do_POST = _serve                            # noqa: N815

        def log_message(self, *a):
            return

    return H


def serve(port, root=DEFAULT_ROOT):
    if not os.path.exists(os.path.join(root, REPO_NAME)):
        ok, msg = refresh(root)
        if not ok:
            print("cannot serve: %s" % msg, file=sys.stderr)
            return 1
    with socketserver.ThreadingTCPServer(("127.0.0.1", port), make_handler(root)) as srv:
        srv.serve_forever()
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="read-only cross-OS git-host cold standby")
    ap.add_argument("--refresh", action="store_true", help="create/update the mirror from the primary")
    ap.add_argument("--serve", action="store_true", help="serve the mirror read-only")
    ap.add_argument("--port", type=int, default=8089)
    ap.add_argument("--root", default=DEFAULT_ROOT)
    a = ap.parse_args(argv)
    if a.refresh:
        ok, msg = refresh(a.root)
        print(msg)
        if not a.serve:
            return 0 if ok else 1
    if a.serve:
        return serve(a.port, a.root)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
