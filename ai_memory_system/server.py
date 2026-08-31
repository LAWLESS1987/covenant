"""server.py -- the HTTP surface. Any AI that can speak JSON over HTTP can
read and write this memory: no SDK, no client library, seven routes.

ROUTES (JSON in, JSON out):
  GET    /health            what this is, and whether its audit chain
                            verifies. Ask this first; it needs no token.
  GET    /memories          the index: name, description, metadata, links
  GET    /memories/<name>   one memory, whole
  PUT    /memories/<name>   write {description,type,body,agent}
  DELETE /memories/<name>   tombstone it (never erased -- see memory_store)
  GET    /search?q=         substring recall over the whole store
  GET    /audit             the hash-chained write ledger
  GET    /openapi.json      the machine-readable contract, so an agent can
                            discover this API instead of being taught it

AUTHENTICATION, AND WHY IT IS NOT OPTIONAL OFF-LOOPBACK.
A memory store is not a cache: it is what an agent believes. Anyone who can
write it can change what every reader concludes, quietly, and the reader has
no way to tell an implanted memory from a remembered one. So:

  * bound to 127.0.0.1 -> a token is OPTIONAL. The reachable set is already
    "processes on this machine", which is the trust boundary the OS gives.
  * bound anywhere else -> a token is REQUIRED. The server refuses to start
    without one rather than come up quietly exposed. Refusing to start is
    loud; starting open is silent, and silence is how this goes wrong.

The token is a shared secret in `Authorization: Bearer <token>`, compared
with hmac.compare_digest. That is ONE bar: it proves the caller holds the
secret, and nothing else. The `agent` field on a write is a LABEL, not a
proof of identity -- two agents sharing a token are indistinguishable in the
ledger. The audit chain makes tampering DETECTABLE, never impossible. Those
are different properties, and conflating them is how a log becomes theatre.

Stdlib http.server, threaded -- not because it is fast, but because it is
present on every python. A memory system nobody can start is worse than a
slow one.
"""
from __future__ import annotations

import hmac
import json
import os
import re
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from ethics_gate import MemoryRefused           # noqa: E402
from memory_store import (MemoryStore, StoreFull,      # noqa: E402
                          MAX_BODY_BYTES)
import recall                                    # noqa: E402


# ------------------------------------------------------------ FLOOD LIMITS --
# A memory endpoint with no rate limit is a machine anyone with the token can
# stop. Every write here fsyncs (durability, deliberately) which makes writes
# EXPENSIVE, and expensive-per-request plus unlimited-requests is the whole
# recipe. So: a token bucket per client address, refilling steadily, with a
# burst allowance so ordinary agent traffic never notices it exists.
#
# This bounds ONE client. It is not DDoS protection and does not pretend to
# be -- a thousand addresses still add up, and the answer to that is a proxy
# in front, not a bigger number here. What it does buy is that a single
# runaway agent (or a loop somebody wrote by accident) cannot take the store
# down while the operator is asleep.
RATE_BURST = int(os.environ.get("AI_MEMORY_RATE_BURST", 60))
RATE_PER_SEC = float(os.environ.get("AI_MEMORY_RATE_PER_SEC", 5))
MAX_CLIENTS_TRACKED = 4096
# Recalls touch (write) the memories they return -- consolidation. Capped,
# because otherwise one cheap GET /recall?limit=50 becomes 50 fsynced writes
# and the read path is a write amplifier a flood can aim with.
TOUCH_PER_RECALL = 3


class RateLimiter:
    """Token bucket per client. Pure enough to test: time is an argument."""

    def __init__(self, burst=RATE_BURST, per_sec=RATE_PER_SEC):
        self.burst, self.per_sec = float(burst), float(per_sec)
        self._buckets = {}
        self._lock = threading.Lock()

    def allow(self, who, now=None):
        """(allowed, retry_after_seconds)."""
        now = time.time() if now is None else now
        with self._lock:
            # Bound the tracking table itself: an attacker cycling source
            # addresses must not be able to grow this without limit. Dropping
            # the whole table is crude and safe -- worst case every client
            # gets a fresh full bucket, which is the state we started in.
            if len(self._buckets) > MAX_CLIENTS_TRACKED:
                self._buckets.clear()
            tokens, last = self._buckets.get(who, (self.burst, now))
            tokens = min(self.burst, tokens + (now - last) * self.per_sec)
            if tokens < 1.0:
                self._buckets[who] = (tokens, now)
                return False, max(1, int((1.0 - tokens) / self.per_sec) + 1)
            self._buckets[who] = (tokens - 1.0, now)
            return True, 0

# ONE exact origin, or empty. Empty is the default and means no CORS headers
# at all, which is correct for an API consumed by HTTP clients rather than by
# browser pages. "*" is rejected on purpose: see _send().
ALLOW_ORIGIN = os.environ.get("AI_MEMORY_ALLOW_ORIGIN", "").strip()
if ALLOW_ORIGIN == "*":
    raise SystemExit(
        "AI_MEMORY_ALLOW_ORIGIN=* is refused.\n"
        "  A wildcard makes every response readable by any page the operator\n"
        "  visits, and this server is unauthenticated on loopback by default.\n"
        "  Name one exact origin, e.g. http://localhost:5173")

VERSION = "ai-memory/1.0"
MAX_BODY = 1 << 20          # 1 MiB. A memory is a fact, not a corpus.
_NAME = re.compile(r"^/memories/([a-z0-9][a-z0-9-]{0,79})$")
LOOPBACK = ("127.0.0.1", "::1", "localhost")


class Handler(BaseHTTPRequestHandler):
    server_version = VERSION
    store: MemoryStore = None          # set by serve()
    token: str = ""                    # "" -> loopback-only, unauthenticated
    started: float = 0.0
    limiter: "RateLimiter" = None
    # A slow-loris client that opens a socket and dribbles bytes holds a
    # thread for as long as it likes. A read timeout turns that from a
    # resource leak into a dropped connection.
    timeout = 30

    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s %s\n" % (
            time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            self.address_string(), fmt % args))

    # ------------------------------------------------------------- plumbing
    def _send(self, code: int, payload: Any) -> None:
        body = json.dumps(payload, indent=1, sort_keys=True).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        # NO WILDCARD CORS. Removed 2026-08-30 after an audit demonstrated the
        # attack end to end against a scratch store.
        #
        # This server makes a token OPTIONAL on loopback, justified by "the
        # reachable set is already processes on this machine". A BROWSER IS A
        # PROCESS ON THIS MACHINE, and it runs JavaScript chosen by whatever
        # page happens to be open. `Access-Control-Allow-Origin: *` made every
        # response READABLE cross-origin, and the OPTIONS reply advertising
        # PUT and DELETE approved the preflight for both. So any page the
        # operator loaded could read the entire store, implant a memory at
        # tier=core -- which recall scores +1.0 and puts unconditionally into
        # /context -- and tombstone anything, with no credentials at all.
        # Measured: preflight 204, PUT 200 written, implanted text present in
        # /context, DELETE 200.
        #
        # Nothing that legitimately consumes this API is a browser page.
        # Agents use HTTP clients, which ignore CORS entirely, so these
        # headers bought nothing and cost the whole trust boundary.
        #
        # For a browser UI, set AI_MEMORY_ALLOW_ORIGIN to ONE exact origin.
        # Never "*", and never reflect the request's Origin back -- reflecting
        # it is the same hole with extra steps.
        if ALLOW_ORIGIN:
            self.send_header("Access-Control-Allow-Origin", ALLOW_ORIGIN)
            self.send_header("Access-Control-Allow-Methods",
                             "GET, PUT, DELETE, OPTIONS")
            self.send_header("Access-Control-Allow-Headers",
                             "Content-Type, Authorization")
            self.send_header("Vary", "Origin")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _authed(self) -> bool:
        """No token configured -> loopback-only server, everything allowed.
        Token configured -> every route but /health must present it."""
        if not self.token:
            return True
        got = self.headers.get("Authorization") or ""
        if got.startswith("Bearer "):
            return hmac.compare_digest(got[7:].strip(), self.token)
        return False

    def _deny(self) -> None:
        self._send(401, {
            "error": "unauthorized",
            "how": "send header 'Authorization: Bearer <token>'",
            "note": "the operator set a token because this server is "
                    "reachable beyond localhost"})

    def _read_json(self) -> Tuple[Dict[str, Any], str]:
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return {}, "bad Content-Length"
        if n > MAX_BODY:
            return {}, f"body over {MAX_BODY} bytes"
        raw = self.rfile.read(n) if n else b"{}"
        try:
            data = json.loads(raw.decode("utf-8") or "{}")
        except (ValueError, UnicodeDecodeError) as e:
            return {}, f"body is not JSON: {e}"
        if not isinstance(data, dict):
            return {}, "body must be a JSON object"
        return data, ""

    def _rate_ok(self) -> bool:
        """False (and a 429 already sent) when this client is over budget."""
        if self.limiter is None:
            return True
        ok, retry = self.limiter.allow(self.client_address[0])
        if ok:
            return True
        body = json.dumps({
            "error": "rate limited",
            "retry_after_seconds": retry,
            "limit": f"{RATE_PER_SEC}/s sustained, {RATE_BURST} burst, "
                     f"per client address",
            "why": "every write here fsyncs, so unlimited requests would "
                   "let one client stop the machine. Raise with "
                   "AI_MEMORY_RATE_PER_SEC if your workload is legitimately "
                   "heavier.",
        }, indent=1).encode()
        self.send_response(429)
        self.send_header("Content-Type", "application/json")
        self.send_header("Retry-After", str(retry))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        return False

    def do_OPTIONS(self):                       # noqa: N802
        # Answers 204 with no CORS approval unless AI_MEMORY_ALLOW_ORIGIN
        # names an origin (_send decides). A preflight that advertises PUT
        # and DELETE to any origin is what turns blind CSRF into full
        # read-write-delete, so the default advertises nothing.
        self._send(204, {})

    # ------------------------------------------------------------- routing
    def do_GET(self):                           # noqa: N802
        if not self._rate_ok():
            return
        u = urllib.parse.urlparse(self.path)
        path = u.path.rstrip("/") or "/"
        qs = urllib.parse.parse_qs(u.query)

        # /health is deliberately open even under a token: a monitor must be
        # able to see that this is alive without holding write credentials,
        # and it discloses no memory content.
        if path in ("/", "/health"):
            st = self.store.state()
            return self._send(200, {
                "service": VERSION,
                "ok": st["audit"]["ok"],
                "memories": st["memories"],
                "uptime_seconds": round(time.time() - self.started, 1),
                "audit": st["audit"],
                "auth": ("bearer token required"
                         if self.token else
                         "none -- loopback-only server"),
                "attribution": "the 'agent' field on a write is a LABEL, "
                               "not a proof of identity",
                "routes": ["/health", "/memories", "/memories/<name>",
                           "/search?q=", "/recall?q=", "/context?budget=",
                           "/audit", "/openapi.json"],
            })

        if path == "/openapi.json":
            return self._send(200, OPENAPI)

        if not self._authed():
            return self._deny()

        if path == "/memories":
            return self._send(200, {"memories": self.store.list()})

        m = _NAME.match(path)
        if m:
            got = self.store.get(m.group(1))
            if got is None:
                return self._send(404, {"error": "no such memory",
                                        "name": m.group(1)})
            return self._send(200, got)

        if path == "/search":
            q = (qs.get("q") or [""])[0]
            if not q:
                return self._send(400, {"error": "q= is required"})
            hits = self.store.search(q)
            return self._send(200, {"query": q, "count": len(hits),
                                    "results": hits})

        # RECALL -- scored, and every score EXPLAINED (recall.py). A hit
        # also counts as a use, which is the reinforcement half of
        # consolidation: what an agent actually reaches for stays warm.
        if path == "/recall":
            q = (qs.get("q") or [""])[0]
            if not q:
                return self._send(400, {"error": "q= is required"})
            try:
                limit = max(1, min(50, int((qs.get("limit") or ["10"])[0])))
            except ValueError:
                limit = 10
            # Shortlist through the index, then rank. This used to read
            # EVERY memory off disk on every recall -- an index in the store
            # that the request path never called.
            # MYCELIAL RECALL. Text search supplies a few SEEDS; activation
            # spreads outward along proven edges. Cost follows the GRAPH, not
            # the size of the store -- and it reaches memories that never used
            # the query's words but have repeatedly proven related, which no
            # amount of scanning can do at any speed.
            seeds = self.store.index.search(q, limit=8)
            names = {c["name"]: 1.0 for c in seeds}
            myc = self.store.index.myc
            if myc and names:
                for row in myc.spread(names, hops=2,
                                      limit=max(25, limit * 3)):
                    names.setdefault(row["name"], row["activation"])
            full = [self.store.index.get_body(n) for n in names]
            ranked = recall.rank([f for f in full if f], q, limit)
            # Only the top few are reinforced -- see TOUCH_PER_RECALL. A
            # read path that writes once per result is a write amplifier
            # pointed at the operator's disk.
            used = [r["name"] for r in ranked[:TOUCH_PER_RECALL]]
            for name in used:
                self.store.touch(name)
            # Only what was actually RETURNED thickens. Reinforcing every
            # candidate would teach the graph that everything relates to
            # everything, which is the same as teaching it nothing.
            if myc and len(used) > 1:
                myc.reinforce(used)
            return self._send(200, {
                "query": q, "count": len(ranked), "results": ranked,
                "note": "every result carries the components that produced "
                        "its score -- an unexplainable recall is one you "
                        "cannot argue with"})

        # CONTEXT -- Letta's core/archival split, with the omission named.
        if path == "/context":
            try:
                budget = max(200, min(200000,
                                      int((qs.get("budget") or
                                           [str(recall.DEFAULT_BUDGET)])[0])))
            except ValueError:
                budget = recall.DEFAULT_BUDGET
            full = [self.store.get(m["name"]) for m in self.store.list()]
            return self._send(200,
                              recall.context_window([f for f in full if f],
                                                    budget))

        if path == "/mycelium":
            myc = self.store.index.myc
            if not myc:
                return self._send(200, {"edges": 0,
                                        "note": "no edge layer on this store"})
            name = (qs.get("name") or [""])[0]
            out = dict(myc.stats())
            # Published deliberately: a store's structural identity is not a
            # secret, because it protects nothing by being hidden. It lets a
            # holder detect substitution and drift, and its own `limits`
            # field says plainly that it does not stop duplication.
            out["fingerprint"] = myc.fingerprint()
            if name:
                out["neighbours"] = myc.neighbours(name, 15)
            return self._send(200, out)

        if path == "/audit":
            recs = []
            try:
                with open(self.store.audit, encoding="utf-8") as fh:
                    for line in fh:
                        if line.strip():
                            recs.append(json.loads(line))
            except OSError:
                pass
            # Both checks, never merged into one verdict. The chain proves the
            # ledger was not reordered; `content` proves the memories still
            # say what the ledger says they said. A store can pass the first
            # and fail the second -- that was the real state of this system
            # until 2026-08-29, and test I4b pins it.
            # THREE things, and they answer three different questions:
            #   chain    -- was THIS node's ledger reordered?      (local)
            #   content  -- do its files still match that ledger?  (local)
            #   state    -- what does it HOLD?                     (comparable)
            # Only `state` is meaningful across nodes: the chain head embeds
            # each line's write time, so three nodes taking one identical
            # write produce three different heads. Measured, not assumed.
            return self._send(200, {"chain": self.store.verify_chain(),
                                    "content": self.store.verify_integrity(),
                                    "state": self.store.state_root(),
                                    "entries": recs})

        return self._send(404, {"error": "no such route", "path": path})

    def do_PUT(self):                           # noqa: N802
        if not self._rate_ok():
            return
        if not self._authed():
            return self._deny()
        m = _NAME.match(urllib.parse.urlparse(self.path).path.rstrip("/"))
        if not m:
            return self._send(404, {"error": "PUT /memories/<kebab-name>"})
        data, err = self._read_json()
        if err:
            return self._send(400, {"error": err})
        missing = [k for k in ("description", "type", "body", "agent")
                   if not str(data.get(k) or "").strip()]
        if missing:
            return self._send(400, {
                "error": "missing required field(s)", "missing": missing,
                "required": {"description": "one line, used for recall",
                             "type": "user|feedback|project|reference",
                             "body": "the fact itself",
                             "agent": "who is writing (recorded verbatim)"}})
        # RECONCILE FIRST (Mem0's decision loop, non-destructive form).
        # The caller is TOLD what this write does to what is already stored,
        # and a superseded memory is marked, never overwritten. Pass
        # reconcile=false to skip -- an importer moving a known-good corpus
        # should not have every file argued with.
        verdict = None
        if str(data.get("reconcile", "true")).lower() != "false":
            # Only memories sharing vocabulary can overlap enough to
            # matter, so the full-text shortlist replaces comparing this body
            # against every stored one -- which was a full scan plus a file
            # read per row, on every write.
            existing = self.store.index.candidates(str(data["body"]), limit=40)
            existing = [e for e in existing if e and e["name"] != m.group(1)]
            verdict = recall.reconcile(str(data["body"]), existing)
            if verdict["action"] == "NOOP" and verdict["target"]:
                return self._send(200, {
                    "written": False, "reconcile": verdict,
                    "note": "nothing written: an existing memory already "
                            "says this. Force with reconcile=false."})
        try:
            out = self.store.put(
                m.group(1), str(data["description"]), str(data["type"]),
                str(data["body"]), str(data["agent"]),
                tier=str(data.get("tier", "archival")))
        except StoreFull as e:
            # 507, not 400 and not 500: the request was well-formed and the
            # server is fine -- the STORE is full. A caller that reads the
            # status knows not to retry, which a 500 would invite.
            return self._send(507, {"error": "store full", "detail": str(e),
                                    "retry": False})
        except MemoryRefused as e:
            # 403, and never 500. A refusal is the gate WORKING, and a 500
            # would tell a caller to retry the thing that was just refused --
            # and would make three nodes refusing a poisoned memory look like
            # three nodes falling over. The verdict travels with it so the
            # caller learns which principle it hit; `retry` is false because
            # the same bytes will be refused again.
            return self._send(403, {"error": "refused by ethics gate",
                                    "verdict": dict(e.verdict),
                                    "retry": False, "written": False})
        except ValueError as e:
            return self._send(400, {"error": str(e)})
        if verdict and verdict["action"] == "SUPERSEDE" and verdict["target"]:
            self.store.supersede(verdict["target"], m.group(1),
                                 str(data["agent"]))
            out = self.store.put(
                m.group(1), str(data["description"]), str(data["type"]),
                str(data["body"]), str(data["agent"]),
                tier=str(data.get("tier", "archival")),
                extra={"supersedes": verdict["target"]})
        return self._send(200, {"written": True, "memory": out,
                                "reconcile": verdict})

    def do_DELETE(self):                        # noqa: N802
        if not self._rate_ok():
            return
        if not self._authed():
            return self._deny()
        m = _NAME.match(urllib.parse.urlparse(self.path).path.rstrip("/"))
        if not m:
            return self._send(404, {"error": "DELETE /memories/<name>"})
        data, _ = self._read_json()
        agent = str(data.get("agent") or "unknown")
        why = str(data.get("why") or "")
        if not self.store.delete(m.group(1), agent, why):
            return self._send(404, {"error": "no such memory",
                                    "name": m.group(1)})
        return self._send(200, {"tombstoned": m.group(1), "agent": agent,
                                "note": "moved to .trash/ and recorded in "
                                        "the audit chain; not erased"})


OPENAPI = {
    "openapi": "3.0.0",
    "info": {"title": "AI Memory System", "version": "1.0",
             "description": "Shared persistent memory for AI agents. "
                            "Markdown+frontmatter files, a hash-chained audit "
                            "ledger, tombstones instead of deletion. Off "
                            "loopback a bearer token is required; the 'agent' "
                            "field is a label, not a proof."},
    "components": {"securitySchemes": {"bearer": {"type": "http",
                                                  "scheme": "bearer"}}},
    "paths": {
        "/health": {"get": {"summary": "state + audit verification (open)"}},
        "/memories": {"get": {"summary": "list all memories"}},
        "/memories/{name}": {
            "get": {"summary": "read one memory"},
            "put": {"summary": "write one memory",
                    "requestBody": {"content": {"application/json": {"schema": {
                        "type": "object",
                        "required": ["description", "type", "body", "agent"],
                        "properties": {
                            "description": {"type": "string"},
                            "type": {"type": "string",
                                     "enum": ["user", "feedback", "project",
                                              "reference"]},
                            "body": {"type": "string"},
                            "agent": {"type": "string"}}}}}}},
            "delete": {"summary": "tombstone one memory (never erased)"}},
        "/search": {"get": {"summary": "substring recall",
                            "parameters": [{"name": "q", "in": "query",
                                            "required": True,
                                            "schema": {"type": "string"}}]}},
        "/recall": {"get": {"summary": "scored recall; every score carries "
                            "the components that produced it",
                            "parameters": [{"name": "q", "in": "query",
                                            "required": True,
                                            "schema": {"type": "string"}},
                                           {"name": "limit", "in": "query",
                                            "schema": {"type": "integer"}}]}},
        "/context": {"get": {"summary": "core-tier context under a character "
                             "budget; anything omitted is named",
                             "parameters": [{"name": "budget", "in": "query",
                                             "schema": {"type": "integer"}}]}},
        "/audit": {"get": {"summary": "the hash-chained write ledger"}},
    },
}


def _guard(fn):
    """Any unhandled exception becomes a 500 with a JSON body.

    Without this an exception inside a handler propagated out and the
    connection was simply DROPPED -- the caller got no status, no body, and
    no reason, and had to time out to learn anything. Worse, one malformed
    record on disk could make /context and /recall drop every request
    permanently, so a single bad write became an outage of the read path.
    Audit 2026-08-30.

    The detail goes to the server log, never into the response: an exception
    string can carry absolute paths and fragments of stored memories, and a
    caller who triggered a crash is exactly who should not be shown them.
    """
    def wrapper(self):
        try:
            return fn(self)
        except Exception as exc:            # noqa: BLE001
            try:
                self.log_message("unhandled %s: %s", type(exc).__name__, exc)
            except Exception:               # noqa: BLE001
                pass
            try:
                self._send(500, {"error": "internal error",
                                 "detail": "logged server-side"})
            except Exception:               # noqa: BLE001
                pass                        # response already begun; drop it
    wrapper.__name__ = getattr(fn, "__name__", "wrapped")
    return wrapper


for _m in ("do_GET", "do_PUT", "do_DELETE", "do_OPTIONS"):
    setattr(Handler, _m, _guard(getattr(Handler, _m)))


def serve(host: str, port: int, root: str, token: str = "",
          rate_burst: int = RATE_BURST, rate_per_sec: float = RATE_PER_SEC
          ) -> int:
    """Start the server. Refuses to bind beyond loopback without a token --
    see the module docstring for why that refusal is the design."""
    # `host != ""` USED TO BE HERE AND WAS BACKWARDS. An empty host binds
    # EVERY interface -- it is 0.0.0.0, the most exposed possible bind -- and
    # the clause treated it as loopback, so `--host ""` came up reachable from
    # the network with no token while the banner announced "auth: none
    # (loopback only)". The server was wrong about its own exposure, which is
    # worse than being exposed: the operator had a printed assurance.
    # Audit 2026-08-30. Empty is now off-loopback and demands a token like any
    # other non-loopback bind.
    off_loopback = host not in LOOPBACK
    if off_loopback and not token:
        sys.stderr.write(
            "REFUSING TO START.\n"
            f"  --host {host} is reachable beyond this machine, and no token\n"
            "  is set. Anyone who could reach the port could rewrite what\n"
            "  every agent reading this store believes, and no reader could\n"
            "  tell an implanted memory from a remembered one.\n\n"
            "  Either:  --host 127.0.0.1            (local agents only)\n"
            "  or:      --token <secret>            (or set AI_MEMORY_TOKEN)\n"
            "  and put TLS in front of it if it crosses a network you do\n"
            "  not control -- a bearer token over plain HTTP is readable by\n"
            "  anything on the path.\n")
        return 2

    Handler.store = MemoryStore(root)
    Handler.token = token
    Handler.started = time.time()
    Handler.limiter = RateLimiter(rate_burst, rate_per_sec)
    httpd = ThreadingHTTPServer((host, port), Handler)
    chain = Handler.store.verify_chain()
    print(f"{VERSION} on http://{host}:{port}   store={Handler.store.root}")
    print(f"  memories: {len(Handler.store.list())}   audit chain: "
          f"{'OK' if chain['ok'] else 'BROKEN'} "
          f"({chain.get('entries', 0)} entries)")
    print(f"  auth: {'bearer token' if token else 'none (loopback only)'}")
    print(f"  limits: {rate_per_sec}/s per client (burst {rate_burst}), "
          f"body <= {MAX_BODY_BYTES} bytes, atomic+fsync writes")
    print("  GET /openapi.json for the machine-readable contract.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")
    finally:
        httpd.server_close()
    return 0
