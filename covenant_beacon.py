#!/usr/bin/env python3
"""covenant_beacon.py -- a light, stdlib-only liveness beacon.

WHY THIS EXISTS. The parallel-OS redundancy work (2026-11-02, the operator:
"we need our own operating systems running parallel ... RESILIENCE/REDUNDANCY")
needs ONE real, provable, no-install cross-OS redundant pair to stand on. Not a
mock: a service that genuinely runs the same code on Windows and on Linux (WSL
Ubuntu), so that killing either instance leaves the other answering. The beacon
is that service. It is deliberately tiny -- the standard library only, a few MB
resident -- because the laptop has ~3 GB free and a ram_guard protecting the
model's room (covenant_model), and a resilience layer that starved the model
would be the opposite of resilience.

WHAT IT SERVES. One endpoint, GET /beacon, returning JSON that identifies WHICH
instance on WHICH OS answered:

    {"ok": true, "service": "redundancy-beacon", "instance": "<name>",
     "env": "windows"|"wsl-ubuntu"|..., "host": "<hostname>", "pid": <int>,
     "os": "<platform>", "ts": <epoch>, "version": "<n>"}

GET /health is an alias that returns the same body (so a plain health probe
works). Anything else is 404 -- a 404 still proves the process is ALIVE, which
is all a liveness probe needs.

WHAT IT NEVER SERVES. No keys, no holdings, no private record, nothing under
private/ -- only non-secret liveness/identity. Keys never cross OS environments
(the operator's line, 2026-11-02), and the beacon is built so there is nothing
secret for it to leak in the first place.

RUN
    python  covenant_beacon.py --port 8771 --instance win-a   --env windows
    python3 covenant_beacon.py --port 8772 --instance wsl-b   --env wsl-ubuntu
LICENCE: public domain.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import socket
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

VERSION = "1"
SERVICE = "redundancy-beacon"


def _body(instance, env):
    return {
        "ok": True,
        "service": SERVICE,
        "instance": instance,
        "env": env,
        "host": socket.gethostname(),
        "pid": os.getpid(),
        "os": platform.system() + " " + platform.release(),
        "ts": round(time.time(), 1),
        "version": VERSION,
    }


def make_handler(instance, env):
    payload = _body(instance, env)

    class _H(BaseHTTPRequestHandler):
        def _send(self, code):
            # ts is refreshed per request so a probe can see the beacon is live NOW,
            # not merely that it once started.
            out = dict(payload, ts=round(time.time(), 1))
            raw = json.dumps(out).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):                                    # noqa: N802
            if self.path.split("?", 1)[0] in ("/beacon", "/health", "/"):
                self._send(200)
            else:
                # A 404 is still a live process answering -- the probe reads ANY
                # HTTP response as "alive", exactly as git_host_down does.
                self._send(404)

        def log_message(self, *a):                           # silence; a window/log is a nuisance
            return

    return _H


def serve(port, instance, env, host="127.0.0.1"):
    """Block, serving the beacon. host defaults to loopback; pass 0.0.0.0 in WSL
    so Windows can reach it over the WSL2 NAT localhost forward."""
    srv = ThreadingHTTPServer((host, port), make_handler(instance, env))
    srv.serve_forever()


def main(argv=None):
    ap = argparse.ArgumentParser(description="covenant redundancy beacon (stdlib only)")
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--instance", default="beacon")
    ap.add_argument("--env", default=platform.system().lower())
    ap.add_argument("--host", default="127.0.0.1",
                    help="bind address; use 0.0.0.0 inside WSL so Windows can reach it")
    a = ap.parse_args(argv)
    serve(a.port, a.instance, a.env, a.host)
    return 0


if __name__ == "__main__":
    sys.exit(main())
