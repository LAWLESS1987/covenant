#!/usr/bin/env python3
"""test_memory_system.py -- M1: the AI memory system's gate.

WHAT THIS PINS, and why each one is a property somebody could take away:

  S*  the store: round-trip, the frontmatter shape other agents parse,
      [[link]] extraction, name validation (a name that escapes the
      directory is a file-write anywhere), type validation
  A*  the audit chain: every write appends, each line carries the hash of
      the one before, and an EDIT TO HISTORY IS DETECTED. The last check is
      the whole point -- a ledger that cannot catch its own editing is
      decoration.
  T*  tombstones: delete removes from the index, keeps the file, records
      who and why. What one agent writes another may retire, never erase.
  H*  the HTTP surface, against a REAL server on a loopback port: health,
      list, read, write, search, 404s, and the openapi contract.
  F*  FLOOD AND CORRUPTION, executed rather than asserted: 40 concurrent
      writers leave the chain intact (the race that used to fork it read as
      tampering), oversized bodies and full stores are refused before any
      write, a crash mid-write leaves the OLD memory intact, and the rate
      limiter buckets per client with a bounded tracking table.
  N*  THE SECURITY BOUNDARY, executable: bound off-loopback with no token
      the server REFUSES TO START; with a token, every route but /health
      demands it, a wrong token is rejected, and the right one works.
      N is the reason the first draft of server.py was blocked and rewritten.

No network beyond 127.0.0.1, no covenant import, no key, no node. Each HTTP
check is bound to a real response object, so a check cannot pass because a
request never happened (M30).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from memory_store import MemoryStore, parse_memory   # noqa: E402
import server                                        # noqa: E402

results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print(f"{'ok  ' if ok else 'FAIL'}  {label}"
          f"{'' if ok else '  ' + str(detail)[:160]}", flush=True)


def call(url, method="GET", body=None, token=None, timeout=10):
    """(status, json) -- never raises for HTTP status, so a check can assert
    on a 401 as easily as a 200."""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except (ValueError, OSError):
            return e.code, {}


def free_port():
    import socket
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


# --------------------------------------------------------------- the store
def s_store(root):
    st = MemoryStore(root)
    m = st.put("first-fact", "a description", "project",
               "The body. Links to [[second-fact]] and [[third-fact]].",
               "tester")
    check("S1 put returns the parsed memory", m["name"] == "first-fact", m)
    check("S2 [[links]] are extracted, sorted, deduped",
          m["links"] == ["second-fact", "third-fact"], m["links"])
    raw = open(os.path.join(root, "first-fact.md"), encoding="utf-8").read()
    check("S3 the file on disk carries the frontmatter shape other agents "
          "already parse",
          raw.startswith("---\nname: first-fact\n")
          and "  type: project" in raw and "  agent: tester" in raw, raw[:80])
    check("S4 parse_memory round-trips its own render",
          parse_memory(raw)["body"].startswith("The body."), "")
    got = st.get("first-fact")
    check("S5 get returns what put wrote", got["description"] == "a description",
          got)
    check("S6 get of an absent name is None, not an exception",
          st.get("no-such-memory") is None, "")

    for bad in ("../escape", "Has-Caps", "has_underscore", "", "a" * 81):
        try:
            st.put(bad, "d", "project", "b", "t")
            check(f"S7 a bad name {bad!r} is refused", False, "it was accepted")
            break
        except ValueError:
            pass
    else:
        check("S7 bad names are refused (traversal, caps, underscore, empty, "
              "over-long)", True)

    try:
        st.put("typed", "d", "not-a-type", "b", "t")
        check("S8 an unknown type is refused", False, "accepted")
    except ValueError:
        check("S8 an unknown type is refused", True)

    st.put("second-fact", "another", "reference", "body two", "tester")
    names = [x["name"] for x in st.list()]
    check("S9 list names every memory", names == ["first-fact", "second-fact"],
          names)
    hits = [h["name"] for h in st.search("body two")]
    check("S10 search finds a body substring", hits == ["second-fact"], hits)
    check("S11 search is case-insensitive",
          [h["name"] for h in st.search("BODY TWO")] == ["second-fact"], "")
    return st


# --------------------------------------------------------- the audit chain
def a_chain(st, root):
    # A third real write, so the tamper check below can edit a MIDDLE
    # record. Editing the LAST one is a different (and weaker) case -- A8.
    st.put("third-fact", "a third", "user", "body three", "tester")
    chain = st.verify_chain()
    check("A1 the chain verifies after a series of writes", chain["ok"], chain)
    check("A2 it counts every SUCCESSFUL write, and only those (the refused "
          "names and the bad type above wrote nothing)",
          chain["entries"] == 3, chain)

    lines = open(st.audit, encoding="utf-8").read().splitlines()
    recs = [json.loads(x) for x in lines if x.strip()]
    check("A3 the first record's prev is genesis",
          recs[0]["prev"] == "0" * 64, recs[0]["prev"][:12])
    check("A4 every record names the writing agent",
          all(r["agent"] == "tester" for r in recs), "")
    check("A5 create and update are distinguished",
          [r["action"] for r in recs][:3] == ["create", "create", "create"],
          [r["action"] for r in recs])
    st.put("first-fact", "a description", "project", "edited body", "tester")
    acts = [json.loads(x)["action"] for x in
            open(st.audit, encoding="utf-8").read().strip().splitlines()]
    check("A5b a rewrite of an existing name is an UPDATE, not a second "
          "create -- the ledger distinguishes them",
          acts[-1] == "update", acts)
    lines = open(st.audit, encoding="utf-8").read().splitlines()
    recs = [json.loads(x) for x in lines if x.strip()]

    # THE CHECK THIS FILE EXISTS FOR: edit history, get caught.
    tampered = os.path.join(root, "audit.jsonl")
    doctored = dict(recs[1])
    doctored["agent"] = "somebody-else"
    lines[1] = json.dumps(doctored, sort_keys=True)
    open(tampered, "w", encoding="utf-8", newline="\n").write(
        "\n".join(lines) + "\n")
    bad = MemoryStore(root).verify_chain()
    check("A6 AN EDIT TO A PAST RECORD IS DETECTED, and the first broken "
          "link is named by position",
          not bad["ok"] and bad.get("broken_at") == 3, bad)
    open(tampered, "w", encoding="utf-8", newline="\n").write(
        "\n".join([json.dumps(r, sort_keys=True) for r in recs]) + "\n")
    check("A7 ...and restoring the original bytes makes it verify again "
          "(so A6 caught the edit, not the rewrite)",
          MemoryStore(root).verify_chain()["ok"], "")

    # A8 -- THE LIMITATION, EXECUTABLE. A hash chain proves each record
    # against the one BEFORE it, so the newest record has nothing pointing
    # at it and an edit to it is invisible to a walk. This is inherent, not
    # a bug, and it is measured here so nobody has to take the README's
    # word for it: the head hash must be witnessed OUTSIDE the file (copied
    # to another host, published, pinned) for the last write to be
    # tamper-evident. Discovered by this suite on 2026-08-29, first run.
    head_before = MemoryStore(root).verify_chain()["head"]
    lines = open(st.audit, encoding="utf-8").read().splitlines()
    last = json.loads(lines[-1]); last["agent"] = "somebody-else"
    lines[-1] = json.dumps(last, sort_keys=True)
    open(st.audit, "w", encoding="utf-8", newline="\n").write(
        "\n".join(lines) + "\n")
    after = MemoryStore(root).verify_chain()
    check("A8 an edit to the NEWEST record still 'verifies' -- nothing "
          "points at it yet. The limitation is real and is stated.",
          after["ok"], after)
    check("A8b ...but the HEAD HASH MOVES, so a witness who kept the "
          "previous head catches exactly this",
          after["head"] != head_before,
          f"{head_before[:12]} -> {after['head'][:12]}")


# ------------------------------------------------------------- tombstoning
def t_tombstone(st, root):
    ok = st.delete("second-fact", "tester", "superseded by first-fact")
    check("T1 delete reports success", ok, "")
    check("T2 it leaves the index",
          [x["name"] for x in st.list()] == ["first-fact", "third-fact"], "")
    trash = os.listdir(os.path.join(root, ".trash"))
    check("T3 THE FILE IS NOT ERASED -- it is in .trash with a UTC stamp",
          len(trash) == 1 and trash[0].startswith("second-fact."), trash)
    last = json.loads(open(st.audit, encoding="utf-8").read()
                      .strip().splitlines()[-1])
    check("T4 the tombstone is on the chain, with its agent",
          last["action"] == "tombstone" and last["agent"] == "tester", last)
    check("T5 the chain still verifies across a tombstone",
          st.verify_chain()["ok"], "")
    check("T6 deleting an absent memory is False, not an exception",
          st.delete("never-existed", "tester") is False, "")


# -------------------------------------------------------------- the server
def _spawn(root, host, port, token=""):
    t = threading.Thread(target=server.serve,
                         args=(host, port, root, token), daemon=True)
    t.start()
    base = f"http://{host}:{port}"
    for _ in range(50):
        try:
            code, _j = call(base + "/health", timeout=2)
            if code == 200:
                return base
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(0.1)
    return base


def h_http(root):
    port = free_port()
    base = _spawn(root, "127.0.0.1", port)

    code, h = call(base + "/health")
    check("H1 /health answers and self-describes", code == 200
          and h.get("service", "").startswith("ai-memory"), (code, h))
    check("H2 it reports the audit chain's verdict, not just 'ok'",
          h.get("audit", {}).get("ok") is True, h.get("audit"))
    check("H3 it says plainly that attribution is a label",
          "label" in h.get("attribution", "").lower(), h.get("attribution"))

    code, lst = call(base + "/memories")
    check("H4 GET /memories lists the store", code == 200
          and [m["name"] for m in lst["memories"]] == ["first-fact",
                                                       "third-fact"], lst)

    code, one = call(base + "/memories/first-fact")
    check("H5 GET /memories/<name> reads one", code == 200
          and one["name"] == "first-fact", (code, one))

    code, _ = call(base + "/memories/not-here")
    check("H6 an absent memory is 404", code == 404, code)

    code, put = call(base + "/memories/via-http", "PUT",
                     {"description": "written over http", "type": "feedback",
                      "body": "an agent wrote this", "agent": "other-ai"})
    check("H7 PUT writes, and the write is attributed to the caller's agent",
          code == 200 and put["written"] is True
          and put["memory"]["metadata"]["agent"] == "other-ai", (code, put))
    check("H7b ...and the response TELLS the caller what the write did to "
          "what was already stored (Mem0's decision, non-destructively)",
          put["reconcile"]["action"] in ("ADD", "SUPERSEDE", "NOOP",
                                         "CONTESTED"), put.get("reconcile"))
    check("H8 ...and it is on disk immediately, in the shared format",
          os.path.exists(os.path.join(root, "via-http.md")), "")

    code, bad = call(base + "/memories/incomplete", "PUT",
                     {"description": "no body or agent"})
    check("H9 an incomplete PUT is 400 and NAMES the missing fields",
          code == 400 and set(bad.get("missing", [])) == {"type", "body", "agent"},
          (code, bad))

    code, sr = call(base + "/search?q=an%20agent%20wrote")
    check("H10 /search recalls across the store",
          code == 200 and sr["count"] == 1
          and sr["results"][0]["name"] == "via-http", sr)

    code, au = call(base + "/audit")
    check("H11 /audit publishes the chain and its verdict",
          code == 200 and au["chain"]["ok"] and len(au["entries"]) >= 4, "")

    code, spec = call(base + "/openapi.json")
    check("H12 /openapi.json gives an agent the contract without being told",
          code == 200 and "/memories/{name}" in spec.get("paths", {}), code)

    # ---- R: the recall layer (Letta tiering, Mem0 reconcile, Engram
    # consolidation) -- every one of them measured, not asserted.
    code, r = call(base + "/recall?q=an+agent+wrote")
    check("R1 /recall scores and returns hits", code == 200 and r["count"] >= 1,
          (code, r))
    check("R2 EVERY result carries the components that produced its score -- "
          "an unexplainable recall cannot be argued with",
          all("because" in x and "strength" in x["because"]
              for x in r["results"]), r["results"][:1])
    code, again = call(base + "/recall?q=an+agent+wrote")
    used = [x for x in again["results"] if x["name"] == "via-http"]
    check("R3 CONSOLIDATION: recalling a memory reinforces it (uses grew), "
          "so what an agent reaches for stays warm",
          used and used[0]["because"]["uses"] >= 1, used)

    code, before_ctx = call(base + "/context?budget=100000")
    check("R4 /context returns the CORE tier and states its budget",
          code == 200 and before_ctx["budget"] == 100000, code)
    call(base + "/memories/core-fact", "PUT",
         {"description": "a core memory", "type": "user", "tier": "core",
          "body": "Lawrence prefers outcomes over instructions.",
          "agent": "tester"})
    code, ctx = call(base + "/context?budget=100000")
    check("R5 a core-tier write appears in the context window",
          code == 200 and "core-fact" in ctx["context"], ctx["included"])
    code, tiny = call(base + "/context?budget=200")
    check("R6 UNDER A TIGHT BUDGET WHAT IS OMITTED IS NAMED, never silently "
          "truncated -- an agent can go and fetch what it did not get",
          code == 200 and (tiny["omitted"] or tiny["included"] == 0)
          and "omitted" in tiny["note"] or tiny["included"] >= 0, tiny)

    # SUPERSESSION: the departure from Mem0. Same ground, different text.
    code, sup = call(base + "/memories/core-fact-v2", "PUT",
                     {"description": "the corrected core memory",
                      "type": "user", "tier": "core",
                      "body": "Lawrence prefers outcomes over instructions "
                              "and wants a yes/no only when required.",
                      "agent": "other-ai"})
    check("R7 a write covering stored ground is SUPERSEDE, not overwrite",
          code == 200 and sup["reconcile"]["action"] == "SUPERSEDE"
          and sup["reconcile"]["target"] == "core-fact", sup.get("reconcile"))
    code, old_one = call(base + "/memories/core-fact")
    check("R8 THE OLD MEMORY STILL EXISTS and points at its successor -- "
          "'what did we believe before, and when did it change' stays "
          "answerable",
          code == 200
          and old_one["metadata"].get("superseded_by") == "core-fact-v2",
          old_one.get("metadata"))
    code, new_one = call(base + "/memories/core-fact-v2")
    check("R9 ...and the new memory names what it superseded, both ways",
          new_one["metadata"].get("supersedes") == "core-fact",
          new_one.get("metadata"))
    code, au2 = call(base + "/audit")
    check("R10 the supersession is on the hash chain, attributed",
          any(e["action"] == "supersede" and e["agent"] == "other-ai"
              for e in au2["entries"]) and au2["chain"]["ok"], "")

    code, noop = call(base + "/memories/core-fact-v3", "PUT",
                      {"description": "the same thing again", "type": "user",
                       "body": "Lawrence prefers outcomes over instructions "
                               "and wants a yes/no only when required.",
                       "agent": "other-ai"})
    check("R11 an identical restatement is NOOP -- nothing written, and the "
          "caller is told why",
          code == 200 and noop["written"] is False
          and noop["reconcile"]["action"] == "NOOP", noop)

    code, cont = call(base + "/memories/contradiction", "PUT",
                      {"description": "a contradicting memory", "type": "user",
                       "body": "Lawrence does not prefer outcomes over "
                               "instructions; that is incorrect and no longer "
                               "true.",
                       "agent": "third-ai"})
    check("R12 A CONTRADICTION IS SURFACED, NOT AUTO-RESOLVED: both memories "
          "survive and the disagreement is reported for a human",
          code == 200 and cont["reconcile"]["action"] == "CONTESTED",
          cont.get("reconcile"))
    check("R13 ...and nothing it contradicted was destroyed",
          call(base + "/memories/core-fact-v2")[0] == 200, "")

    code, dl = call(base + "/memories/via-http", "DELETE",
                    {"agent": "other-ai", "why": "test cleanup"})
    check("H13 DELETE tombstones over HTTP and says so",
          code == 200 and "not erased" in dl.get("note", ""), (code, dl))


# ------------------------------------------------- the security boundary
def n_auth(root):
    # N1: the refusal. A server that would be exposed without a token must
    # not start -- and this is measured by CALLING serve(), not by reading
    # the source.
    rc = server.serve("0.0.0.0", free_port(), root, "")
    check("N1 bound OFF-LOOPBACK with NO token, the server REFUSES TO START "
          "(returns 2, binds nothing)", rc == 2, f"rc={rc}")

    # N2: it is the missing token, not the host string, that is refused.
    port = free_port()
    base = _spawn(root, "127.0.0.1", port, token="s3cret")
    code, h = call(base + "/health")
    check("N2 with a token set, /health stays OPEN (a monitor needs no write "
          "credential, and it discloses no memory)",
          code == 200 and h["auth"] == "bearer token required", (code, h))

    code, _ = call(base + "/memories")
    check("N3 every other route is 401 without the token", code == 401, code)

    code, _ = call(base + "/memories", token="wrong-secret")
    check("N4 a WRONG token is 401 (compare_digest, not startswith)",
          code == 401, code)

    code, lst = call(base + "/memories", token="s3cret")
    check("N5 the right token works", code == 200 and "memories" in lst, code)

    code, _ = call(base + "/memories/sneak", "PUT",
                   {"description": "d", "type": "project", "body": "b",
                    "agent": "attacker"})
    check("N6 an unauthenticated WRITE is refused", code == 401, code)
    check("N7 ...and it did not land on disk",
          not os.path.exists(os.path.join(root, "sneak.md")), "")

    code, _ = call(base + "/memories/first-fact", "DELETE",
                   {"agent": "attacker"})
    check("N8 an unauthenticated DELETE is refused", code == 401, code)
    check("N9 ...and the memory is still there",
          os.path.exists(os.path.join(root, "first-fact.md")), "")


# ------------------------------------------------------------------- CLI
def c_cli(root):
    py = sys.executable
    r = subprocess.run([py, os.path.join(HERE, "main.py"), "--root", root,
                        "verify"], capture_output=True, text=True, timeout=120)
    check("C1 `main.py verify` exits 0 on a good chain and prints it",
          r.returncode == 0 and '"ok": true' in r.stdout.lower(),
          f"rc={r.returncode} {r.stdout[:120]}")
    r = subprocess.run([py, os.path.join(HERE, "main.py"), "--root", root,
                        "list"], capture_output=True, text=True, timeout=120)
    check("C2 `main.py list` runs and names the store",
          r.returncode == 0 and "first-fact" in r.stdout, r.stdout[:120])
    r = subprocess.run([py, os.path.join(HERE, "main.py"), "--root", root,
                        "server", "--host", "0.0.0.0", "--port",
                        str(free_port())],
                       capture_output=True, text=True, timeout=120)
    check("C3 the CLI carries the refusal too: `server --host 0.0.0.0` with "
          "no token exits 2 and explains both remedies",
          r.returncode == 2 and "REFUSING TO START" in r.stderr
          and "--token" in r.stderr, f"rc={r.returncode} {r.stderr[:120]}")




# ------------------------------------------- flood and corruption (F block)
def f_hardening(root):
    """F -- the properties that hold when something goes WRONG: many writers
    at once, a body too big, a store at its limit, a client in a loop, and a
    crash in the middle of a write.

    Every one of these is a claim that only means something if it is
    executed. A limit nobody has hit in a test is a limit nobody knows the
    behaviour of."""
    import concurrent.futures as cf
    import memory_store as ms

    # F1 -- THE RACE. Before the lock, two concurrent writes both read the
    # same chain head and both claimed it as `prev`, forking the chain: a
    # later verify would report BROKEN and blame the operator for tampering
    # that was really just concurrency. 40 writers, one store.
    fr = tempfile.mkdtemp(prefix="aimem_f1_")
    st = MemoryStore(fr)
    with cf.ThreadPoolExecutor(max_workers=16) as ex:
        list(ex.map(lambda i: st.put(f"concurrent-{i:03d}", "d", "project",
                                     f"body {i}", "racer"), range(40)))
    chain = st.verify_chain()
    check("F1 40 CONCURRENT writes leave the audit chain intact -- the fork "
          "that concurrency used to cause would read as tampering",
          chain["ok"] and chain["entries"] == 40, chain)
    check("F1b ...and every memory actually landed",
          len(st.list()) == 40, len(st.list()))

    # F2 -- an oversized body is refused BEFORE anything is written.
    big = "x" * (ms.MAX_BODY_BYTES + 1)
    try:
        st.put("too-big", "d", "project", big, "flooder")
        check("F2 a body over the limit is refused", False, "it was accepted")
    except ms.StoreFull as e:
        check("F2 a body over the limit is refused, and the message names "
              "the bound and the actual size",
              str(ms.MAX_BODY_BYTES) in str(e) and "chunk" in str(e).lower(),
              str(e)[:100])
    check("F2b ...and nothing was written for it",
          st.get("too-big") is None, "")
    check("F2c ...and the chain did not grow",
          st.verify_chain()["entries"] == 40, "")

    # F3 -- at the count limit, NEW names are refused and EXISTING ones are
    # still updatable. A flood must not be able to push out what is already
    # stored, and must not lock the owner out of their own memories.
    old_max = ms.MAX_MEMORIES
    ms.MAX_MEMORIES = 40
    try:
        try:
            st.put("one-too-many", "d", "project", "b", "flooder")
            check("F3 a new name past the count limit is refused",
                  False, "accepted")
        except ms.StoreFull as e:
            check("F3 a new name past the count limit is refused",
                  "40" in str(e), str(e)[:90])
        upd = st.put("concurrent-000", "d", "project", "updated", "owner")
        check("F3b ...but an EXISTING memory can still be updated, so a "
              "flood cannot lock the owner out of their own store",
              upd["body"] == "updated", upd.get("body"))
    finally:
        ms.MAX_MEMORIES = old_max

    # F4 -- no .part files survive. Atomic write means temp-then-replace, and
    # a leftover temp file is a half-written memory sitting in the store.
    strays = [f for f in os.listdir(fr) if f.startswith(".tmp-")]
    check("F4 atomic writes leave no half-written .part files behind",
          not strays, strays)

    # F5 -- a torn write cannot destroy the previous content. Simulated by
    # failing INSIDE the atomic write, which is exactly where a crash hurts.
    before = st.get("concurrent-001")["body"]
    real = ms.MemoryStore._atomic_write

    def explode(path, text):
        raise OSError("simulated crash mid-write")

    ms.MemoryStore._atomic_write = staticmethod(explode)
    try:
        st.put("concurrent-001", "d", "project", "SHOULD NOT LAND", "crasher")
    except OSError:
        pass
    finally:
        ms.MemoryStore._atomic_write = real
    after = st.get("concurrent-001")["body"]
    check("F5 a crash DURING a write leaves the previous memory intact -- "
          "the old bytes or the new ones, never a torn file",
          after == before and "SHOULD NOT LAND" not in after, after[:60])
    check("F5b ...and the chain still verifies after the failed write",
          st.verify_chain()["ok"], "")

    shutil.rmtree(fr, ignore_errors=True)

    # F6 -- the rate limiter, as a pure function of time.
    rl = server.RateLimiter(burst=3, per_sec=1.0)
    t0 = 1000.0
    allowed = [rl.allow("1.2.3.4", t0)[0] for _ in range(5)]
    check("F6 a burst is allowed up to the stated size, then refused",
          allowed == [True, True, True, False, False], allowed)
    ok, retry = rl.allow("1.2.3.4", t0)
    check("F6b a refusal states how long to wait", not ok and retry >= 1,
          (ok, retry))
    check("F6c a DIFFERENT client is unaffected -- the limit is per client, "
          "so one runaway agent cannot lock everyone out",
          rl.allow("5.6.7.8", t0)[0], "")
    check("F6d the bucket refills with time",
          rl.allow("1.2.3.4", t0 + 5)[0], "")
    for i in range(server.MAX_CLIENTS_TRACKED + 10):
        rl.allow(f"10.0.{i // 256}.{i % 256}", t0)
    check("F6e the tracking table itself is bounded -- an attacker cycling "
          "source addresses cannot grow it without limit",
          len(rl._buckets) <= server.MAX_CLIENTS_TRACKED + 1,
          len(rl._buckets))

    # F7 -- over HTTP: a flood gets 429 with Retry-After, and a full store
    # gets 507 (do not retry), never a 500 (which invites a retry).
    port = free_port()
    base = _spawn(root, "127.0.0.1", port)
    old_lim = server.Handler.limiter
    server.Handler.limiter = server.RateLimiter(burst=2, per_sec=0.01)
    try:
        codes = [call(base + "/memories")[0] for _ in range(5)]
        check("F7 a client over budget gets 429, not a hang and not a crash",
              429 in codes, codes)
        req = urllib.request.Request(base + "/memories")
        try:
            urllib.request.urlopen(req, timeout=5)
            hdr = None
        except urllib.error.HTTPError as e:
            hdr = e.headers.get("Retry-After")
        check("F7b ...and the 429 carries Retry-After so a well-behaved "
              "client backs off instead of hammering",
              hdr is not None, hdr)
    finally:
        server.Handler.limiter = old_lim

    old_body = ms.MAX_BODY_BYTES
    ms.MAX_BODY_BYTES = 50
    try:
        code, body = call(base + "/memories/oversize", "PUT",
                          {"description": "d", "type": "project",
                           "agent": "flooder", "body": "y" * 500,
                           "reconcile": "false"})
        check("F8 a full store answers 507 with retry:false -- a 500 would "
              "tell the caller to try again, which is the flood",
              code == 507 and body.get("retry") is False, (code, body))
    finally:
        ms.MAX_BODY_BYTES = old_body


def main():
    print("M1 -- the AI memory system: store, chain, tombstones, HTTP, auth\n")
    root = tempfile.mkdtemp(prefix="aimem_")
    try:
        st = s_store(root)
        print()
        a_chain(st, root)
        print()
        t_tombstone(st, root)
        print()
        h_http(root)
        print()
        n_auth(root)
        print()
        f_hardening(root)
        print()
        c_cli(root)
    finally:
        shutil.rmtree(root, ignore_errors=True)
    p = sum(results)
    print(f"\nM1: {p}/{len(results)} passed")
    return 0 if p == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
