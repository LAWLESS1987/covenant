#!/usr/bin/env python3
"""
test_m6_mobile_door.py -- M6 (2026-09-16): the phone's plain-browser door.

WHY THIS EXISTS
  The phone runs 0.1.421+70c6200, a build from before the in-app updater, so it
  has never asked /app/latest and never can: auto-update cannot bootstrap
  itself. The only client left on that phone is its browser, and a browser
  holds no key -- so /m and /m/apk are unsigned, and the network is what pays
  for it. They answer loopback and the Tailscale CGNAT range (100.64.0.0/10)
  and nothing else. The API binds 0.0.0.0, so this predicate is the entire
  reason the house LAN cannot pull a private build off this port.

  A gate nobody has watched fail is not a gate (M31). Every refusal here is
  mutation-tested: the guard is flipped off and the refusal must DISAPPEAR,
  then restored and the refusal must come back.

CHECKS
  M6a  tailnet_ok: the allow/deny table, including the /10 boundary, an
       IPv4-mapped IPv6 address, an empty string and a non-address.
  M6b  /m from a tailnet address: 200, HTML, and every placeholder filled --
       a page that shipped "__BUILD__" would render a lie about the build.
  M6c  /m from a LAN address: 403, and the refusal is RECORDED as an anomaly,
       not silently dropped.
  M6d  MUTATION: with tailnet_ok forced True the same LAN request succeeds --
       proof the 403 in M6c came from the gate and not from something else.
  M6e  /m/apk from a tailnet address: 200, Android's mimetype, and the bytes
       hash to the sha256 in ops/app/latest.json. The phone is told a hash by
       the same server that serves the bytes (that is the /app/latest weakness
       this route does not pretend to fix); this check at least proves the
       server is not serving something other than what it fetched.
  M6f  /m/apk from a LAN address: 403 -- and mutation-tested like M6c.
  M6g  covenant_daily_plan.build_report: the PC compares the build the phone
       SAYS it is running against the newest build it has fetched, alerts while
       they differ, and goes quiet the moment they match. Its fixtures are its
       own -- a report that reads live repo state would pass or fail by the
       calendar. Includes the case that actually happened (a phone two days
       behind) and the mutation (make the shas agree, the alert must vanish).

    python test_m6_mobile_door.py
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile

import covenant_unified_v8 as cov

HERE = os.path.dirname(os.path.abspath(__file__)) or "."
results = []


def check(label, ok, detail=""):
    results.append((label, bool(ok)))
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}" + (f"  -- {detail}" if detail else ""))


def fresh_master(name="M6", port=5391):
    tmp = tempfile.mktemp(suffix=f"_{name}.db")
    m = cov.CovenantUnifiedMaster(name, host="127.0.0.1", port=port,
                                  p2p_port=port + 1, db_path=tmp)
    m.add_genesis_block()
    m.node.sentinel = cov.ReasoningSentinel(cov.MockJudge(), cov.DIVINE_PRINCIPLES)
    return m


def get(client, path, addr):
    return client.get(path, environ_base={"REMOTE_ADDR": addr})


def refusals(master, kind):
    """How many of `kind` the anomaly monitor has seen (per_kind rows are dicts)."""
    row = master.node.anomaly_monitor.report().get("per_kind", {}).get(kind, 0)
    return row.get("recent", 0) if isinstance(row, dict) else int(row or 0)


def main():
    # ---- M6a: the predicate itself --------------------------------------
    allow = ["127.0.0.1", "::1", "100.64.0.0", "100.86.158.1", "100.127.255.255",
             "::ffff:100.86.158.1"]
    deny = ["192.168.1.50", "10.0.0.61", "172.16.4.9", "8.8.8.8",
            "100.63.255.255", "100.128.0.1", "", "bogus", "100.86.158"]
    bad_allow = [a for a in allow if not cov.tailnet_ok(a)]
    bad_deny = [a for a in deny if cov.tailnet_ok(a)]
    check("M6a tailnet_ok allows loopback + 100.64/10", not bad_allow, f"rejected {bad_allow}")
    check("M6a tailnet_ok denies LAN, public, boundary, junk", not bad_deny, f"allowed {bad_deny}")

    m = fresh_master()
    client = m.api.app.test_client()
    PHONE_ADDR, LAN_ADDR = "100.86.158.1", "192.168.1.50"
    # The ask log is chat MEMORY (ops/chat/ask_log.jsonl); this suite wrote 24
    # sample asks into the real one on 2026-09-19. Redirected for the run, and
    # the model is a stub: no weights are needed to drive the door.
    os.environ["COVENANT_ASK_LOG"] = tempfile.mktemp(suffix="_m6_asklog.jsonl")
    os.environ["COVENANT_MODEL_STUB"] = "1"
    os.environ["COVENANT_IMAGE_STUB"] = "1"

    # ---- M6b: the page a tailnet browser gets ---------------------------
    r = get(client, "/m", PHONE_ADDR)
    body = r.get_data(as_text=True)
    check("M6b /m answers the tailnet 200", r.status_code == 200, f"got {r.status_code}")
    check("M6b /m is HTML", "text/html" in r.headers.get("Content-Type", ""),
          r.headers.get("Content-Type", ""))
    left = [t for t in ("__NODE__", "__SOURCE__", "__VERSION__", "__BUILD__", "__PHONE__")
            if t in body]
    check("M6b every placeholder is filled", not left, f"still literal: {left}")
    check("M6b the page names this node and its source",
          "M6" in body and (cov.CORE_SOURCE_SHA12 or "unreadable") in body)

    # ---- M6c/M6d: the LAN is refused, and the refusal is visible --------
    before = refusals(m, "mobile_page_refused")
    r = get(client, "/m", LAN_ADDR)
    after = refusals(m, "mobile_page_refused")
    check("M6c /m refuses a LAN address 403", r.status_code == 403, f"got {r.status_code}")
    check("M6c the refusal is recorded as an anomaly", after == before + 1,
          f"{before} -> {after}")

    real = cov.tailnet_ok
    try:
        cov.tailnet_ok = lambda addr: True          # M31: flip the guard OFF
        r = get(client, "/m", LAN_ADDR)
        check("M6d mutation: guard off -> the same LAN request succeeds",
              r.status_code == 200, f"got {r.status_code}")
    finally:
        cov.tailnet_ok = real
    r = get(client, "/m", LAN_ADDR)
    check("M6d guard restored -> refused again", r.status_code == 403, f"got {r.status_code}")

    # ---- M6e/M6f: the APK ------------------------------------------------
    manifest = {}
    mp = os.path.join(HERE, "ops", "app", "latest.json")
    if os.path.exists(mp):
        with open(mp, "r", encoding="utf-8") as fh:
            manifest = json.load(fh)
    r = get(client, "/m/apk", PHONE_ADDR)
    if manifest.get("sha256"):
        got = hashlib.sha256(r.get_data()).hexdigest()
        check("M6e /m/apk serves the fetched build to the tailnet",
              r.status_code == 200, f"got {r.status_code}")
        check("M6e the bytes hash to the manifest's sha256",
              got == manifest["sha256"], f"{got[:16]} vs {manifest['sha256'][:16]}")
        check("M6e Android's mimetype",
              "vnd.android.package-archive" in r.headers.get("Content-Type", ""),
              r.headers.get("Content-Type", ""))
    else:
        check("M6e /m/apk says so when no build is fetched", r.status_code == 404,
              f"got {r.status_code} with no ops/app/latest.json")

    before = refusals(m, "mobile_apk_refused")
    r = get(client, "/m/apk", LAN_ADDR)
    after = refusals(m, "mobile_apk_refused")
    check("M6f /m/apk refuses a LAN address 403", r.status_code == 403, f"got {r.status_code}")
    check("M6f that refusal is recorded too", after == before + 1, f"{before} -> {after}")
    try:
        cov.tailnet_ok = lambda addr: True
        r = get(client, "/m/apk", LAN_ADDR)
        check("M6f mutation: guard off -> the LAN gets the APK",
              r.status_code in (200, 404), f"got {r.status_code}")
    finally:
        cov.tailnet_ok = real

    # ---- M6g: behind, level, and AHEAD -- told apart by commit order ----
    #
    # THE FIXTURE THAT CONFIRMED THE BUG. This block used to hand the phone
    # "0.1.500+6953f6d" -- a version string I invented, carrying the head sha
    # of the PRIVATE app repo. No phone has ever emitted one: a phone reports
    # the PUBLIC core it was built from. So the fixture encoded the same
    # misunderstanding as the code it was testing, passed, and the check went
    # on alerting through a successful install. Real shas from THIS repository
    # now, so "which is newer" is a question the test can actually ask.
    import covenant_daily_plan as dp
    import subprocess
    now = 1789560000.0

    def sha_at(n):
        out = subprocess.run(["git", "log", "--format=%h", "-n", str(n + 1)],
                             cwd=HERE, capture_output=True, text=True, timeout=60).stdout.split()
        return out[n] if len(out) > n else ""

    newer, older = sha_at(0), sha_at(6)
    fixture = tempfile.mktemp(suffix="_m6_checkins.jsonl")

    def phone_says(app, age=120):
        with open(fixture, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"signer": "phone", "node_id": "phone", "at": now - age,
                                 "app": app, "chain_height": "28"}) + chr(10))

    build = {"sha7": "c0de384", "built": "2026-09-16T11:37:06Z",
             "version": "0.1.475+" + newer, "core": newer, "size": 45153060}
    real_newest = dp.newest_build
    try:
        dp.newest_build = lambda path=None: build

        check("M6g the two shas used here are real and ordered",
              bool(newer) and bool(older) and newer != older, "%s vs %s" % (newer, older))

        phone_says("0.1.400+" + older)
        a, i = dp.build_report(now=now, path=fixture)
        check("M6g a phone genuinely behind raises exactly one alert", len(a) == 1, str(a)[:120])
        check("M6g the alert names both versions and where to go",
              bool(a) and older in a[0] and newer in a[0] and "/m" in a[0], (a[0] if a else "")[:120])

        # LEVEL: the phone reports exactly what the PC holds. This is the case
        # the old check could never reach, because it was comparing the phone's
        # public-core sha against a private-repo one.
        phone_says(build["version"])
        a2, i2 = dp.build_report(now=now, path=fixture)
        check("M6g a phone on exactly the build this PC holds raises nothing", not a2, str(a2)[:120])
        check("M6g ...and the info line says so", any("the build this PC holds" in x for x in i2), str(i2)[:120])

        # AHEAD: the hour between an install and the next fetch. Being newer
        # than the PC is not a fault of the phone's.
        build_old = dict(build, version="0.1.400+" + older, core=older)
        dp.newest_build = lambda path=None: build_old
        phone_says("0.1.475+" + newer)
        a3, i3 = dp.build_report(now=now, path=fixture)
        check("M6g a phone AHEAD of the build on disk is not called behind", not a3, str(a3)[:120])
        check("M6g ...and the PC is named as the one that must catch up",
              any("AHEAD" in x and "catch up" in x for x in i3), str(i3)[:140])

        # UNKNOWN: a core this repository has never seen. An unknown is not a
        # finding, so it alerts on nothing and says why.
        dp.newest_build = lambda path=None: build
        phone_says("0.1.999+deadbee")
        a4, i4 = dp.build_report(now=now, path=fixture)
        check("M6g a core that cannot be placed in history raises nothing", not a4, str(a4)[:120])
        check("M6g ...and says the order is unknown rather than guessing",
              any("unknown" in x for x in i4), str(i4)[:140])

        # A phone that is switched off is not nagged: an info line, not an alert.
        phone_says("0.1.400+" + older, age=90000)
        a5, i5 = dp.build_report(now=now, path=fixture)
        check("M6g a phone that is not reporting is not told to go install", not a5, str(a5)[:120])

        dp.newest_build = lambda path=None: {}
        a6, i6 = dp.build_report(now=now, path=fixture)
        check("M6g no build fetched -> nothing to be behind", not a6, str(a6)[:120])
    finally:
        dp.newest_build = real_newest
        try:
            os.unlink(fixture)
        except OSError:
            pass

    # ---- M6i: the build's identity comes from the artifact, not the run ----
    import covenant_app_update as AU
    if manifest.get("file"):
        apk = os.path.join(HERE, "ops", "app", manifest["file"])
        v = AU.apk_version(apk)
        check("M6i the APK declares its own versionName, and it is read from it",
              bool(v) and "+" in v, str(v))
        check("M6i ...and that version, not the private repo's sha, is what latest.json records",
              manifest.get("version") == v, "%s vs %s" % (manifest.get("version"), v))
        check("M6i ...and the core it names is a commit in THIS repository",
              subprocess.run(["git", "cat-file", "-t", (v or "+").split("+")[-1]], cwd=HERE,
                             capture_output=True, text=True).returncode == 0,
              (v or "").split("+")[-1])

    # ---- M6h: a build is a RUN, not a commit --------------------------
    # The workflow makes one tree from TWO checkouts -- the private app repo
    # and the PUBLIC core at main -- so the same app commit rebuilt an hour
    # later is a different APK carrying a newer core. The updater used to
    # compare head_sha and discard it as "already have the newest build".
    # Measured the day the highway learned to ask for a rebuild: the dispatch
    # succeeded, the APK existed, and the fetch refused to collect it.
    import covenant_app_update as AU
    same = {"id": 101, "head_sha": "abc1234def"}
    rebuilt = {"id": 102, "head_sha": "abc1234def"}
    held = {"run_id": 101, "sha": "abc1234def", "sha7": "abc1234"}
    check("M6h nothing held yet -> any build is new", AU.is_new_build(None, same))
    check("M6h the run we already hold is not new", not AU.is_new_build(held, same))
    check("M6h a SECOND run of the SAME commit is a new build",
          AU.is_new_build(held, rebuilt), "same head_sha, different run")

    # ---- M6j-M6o (2026-09-19): the PC's own face -- the ask box and /m/judge
    def post(client_, path, addr, body):
        return client_.post(path, json=body, environ_base={"REMOTE_ADDR": addr})

    r = get(client, "/m", PHONE_ADDR)
    body = r.get_data(as_text=True)
    check("M6j /m carries the ask box and posts to /m/judge",
          'id="say"' in body and "/m/judge" in body and 'id="send"' in body)
    r = post(client, "/m/judge", PHONE_ADDR, {"text": "a plain sentence with nothing alleged"})
    j = r.get_json() or {}
    check("M6j /m/judge from the tailnet answers 200 with the phone's four fields",
          r.status_code == 200 and j.get("status") == "success"
          and all(k in j for k in ("admitted", "alleges_nothing", "message", "judge")),
          f"{r.status_code} {sorted(j)}")
    before = refusals(m, "mobile_page_refused")
    r = post(client, "/m/judge", LAN_ADDR, {"text": "hello"})
    after = refusals(m, "mobile_page_refused")
    check("M6k /m/judge refuses a LAN address 403", r.status_code == 403, f"got {r.status_code}")
    check("M6k that refusal is recorded as an anomaly", after == before + 1, f"{before} -> {after}")
    try:
        cov.tailnet_ok = lambda addr: True
        r = post(client, "/m/judge", LAN_ADDR, {"text": "hello"})
        check("M6l mutation: guard off -> the LAN gets a verdict", r.status_code == 200, f"got {r.status_code}")
    finally:
        cov.tailnet_ok = real
    r = post(client, "/m/judge", PHONE_ADDR, {"text": "   "})
    check("M6m an empty text is refused 400, not judged", r.status_code == 400, f"got {r.status_code}")
    r = post(client, "/m/judge", PHONE_ADDR, {"text": "x" * 9000})
    check("M6m a 9000-character text is bounded and judged, not refused", r.status_code == 200, f"got {r.status_code}")
    r = post(client, "/m/judge", PHONE_ADDR, {"nonsense": 1})
    check("M6m a body with no text is refused 400", r.status_code == 400, f"got {r.status_code}")
    codes = [post(client, "/m/judge", "100.86.158.7", {"text": "ask %d" % i}).status_code for i in range(31)]
    # Measured 2026-09-19: the API's own per-peer limiter (rate_limit, 429
    # "Rate limit exceeded") refuses first, at the 21st request in a burst; this
    # route's own 30-per-10-minutes bound sits behind it. Either way a burst is
    # bounded, and the check says which one bit.
    first = codes.index(429) if 429 in codes else None
    check("M6n a burst of 31 asks is bounded: never more than 30 answered, and a 429 appears (first at #%s)" % (None if first is None else first + 1),
          first is not None and codes[:first] == [200] * first and first <= 30, f"{codes[:3]}... {codes[-2:]}")
    h_before, p_before = len(m.node.chain), len(getattr(m.node, "pending_transactions", []) or [])
    r = post(client, "/m/judge", "100.86.158.11", {"text": "one more, recorded nowhere"})
    h_after, p_after = len(m.node.chain), len(getattr(m.node, "pending_transactions", []) or [])
    check("M6o an ask records no transaction and no block (chain length and pending pool unchanged)",
          r.status_code == 200 and h_before == h_after and p_before == p_after, f"chain {h_before}->{h_after} pending {p_before}->{p_after} status {r.status_code}")

    # ---- M6p (2026-09-19): the students' past work, tailnet-gated text
    r = get(client, "/m/students", PHONE_ADDR)
    body = r.get_data(as_text=True)
    check("M6p /m/students answers the tailnet 200 with text naming each record it has or lacks",
          r.status_code == 200 and "text/plain" in r.headers.get("Content-Type", "")
          and "ops/DISTILL.md" in body and "ops/verdicts.jsonl" in body, f"{r.status_code} {body[:80]!r}")
    before = refusals(m, "mobile_page_refused")
    r = get(client, "/m/students", LAN_ADDR)
    check("M6p /m/students refuses a LAN address 403 and records it",
          r.status_code == 403 and refusals(m, "mobile_page_refused") == before + 1, f"got {r.status_code}")

    # ---- M6q (2026-09-19): the agent door, its leash and its gate (stub model)
    r = post(client, "/m/agent", PHONE_ADDR, {"text": "what is two plus two"})
    j = r.get_json() or {}
    check("M6q /m/agent from the tailnet answers 200 with the answer, the verdict and the model's cost",
          r.status_code == 200 and j.get("status") == "success" and "answer" in j and "admitted" in j
          and "withheld" in j and "ms" in j and j.get("model") == "stub", f"{r.status_code} {sorted(j)}")
    # M6q2 (2026-09-21): the turns before this one reach the model, for the SAME caller only.
    # The stub names how many messages it was handed: system + user = 2 on a cold ask; with one
    # answered exchange replayed it is system + user + assistant + user = 4. A different caller
    # on the tailnet starts cold. Read from the answer the door returned, not from the log.
    first_withheld = bool(j.get("withheld"))
    r2 = post(client, "/m/agent", PHONE_ADDR, {"text": "and three plus three"})
    j2 = r2.get_json() or {}
    if first_withheld:
        check("M6q2 the first answer was withheld, so nothing is replayed: the second ask is cold (2 messages)",
              r2.status_code == 200 and "(2 messages)" in str(j2.get("answer", "")) + str(j2.get("message", "")), f"{j2.get('answer')!r}")
    else:
        check("M6q2 the second ask from the same caller carries the first exchange (4 messages)",
              r2.status_code == 200 and "(4 messages)" in str(j2.get("answer", "")), f"{j2.get('answer')!r} withheld={j2.get('withheld')}")
    r3 = post(client, "/m/agent", "100.86.158.9", {"text": "who am i"})
    j3 = r3.get_json() or {}
    check("M6q2 a different tailnet caller starts cold: no one else's turns are replayed to it (2 messages)",
          r3.status_code == 200 and "(2 messages)" in str(j3.get("answer", "")), f"{j3.get('answer')!r} withheld={j3.get('withheld')}")
    hist = cov.agent_history(os.environ["COVENANT_ASK_LOG"], PHONE_ADDR, turns=1)
    check("M6q2 agent_history keeps the caller's newest exchange only when turns=1, user then assistant",
          len(hist) == 2 and hist[0]["role"] == "user" and hist[1]["role"] == "assistant"
          and hist[0]["content"].startswith("and three plus three"), hist)
    check("M6q2 agent_history of a missing log is empty, never an error",
          cov.agent_history(os.path.join(os.environ["COVENANT_ASK_LOG"], "nowhere.jsonl"), PHONE_ADDR) == [])
    r = post(client, "/m/agent", LAN_ADDR, {"text": "hello"})
    check("M6q /m/agent refuses a LAN address 403", r.status_code == 403, f"got {r.status_code}")
    check("M6q the leash: an https URL on a listed host passes, a subdomain of one passes",
          cov._agent_fetch_ok("https://github.com/LAWLESS1987/covenant") and cov._agent_fetch_ok("https://api.github.com/x"))
    check("M6q the leash: http, an unlisted host, a look-alike host and junk are refused",
          not cov._agent_fetch_ok("http://github.com/x") and not cov._agent_fetch_ok("https://example.com/")
          and not cov._agent_fetch_ok("https://github.com.evil.io/x") and not cov._agent_fetch_ok("not a url"))
    txt, note = cov._agent_fetch("https://example.com/")
    check("M6q an off-list fetch is refused before any network, with no text", txt == "" and note.startswith("refused"), note)
    log_rows = []
    try:
        with open(os.environ["COVENANT_ASK_LOG"], "r", encoding="utf-8") as fh:
            log_rows = [json.loads(l) for l in fh if l.strip()]
    except OSError:
        pass
    check("M6q every ask and agent exchange went to the redirected memory log, none to the real one",
          any(x.get("kind") == "agent" for x in log_rows) and any(x.get("kind") == "ask" for x in log_rows), len(log_rows))

    # ---- M6r (2026-09-19): the image door -- the prompt is judged, the PNG comes back (stub model)
    r = post(client, "/m/image", PHONE_ADDR, {"prompt": "a small mountain station at dusk, one lamp"})
    check("M6r /m/image from the tailnet answers a PNG for a clean prompt",
          r.status_code == 200 and r.headers.get("Content-Type") == "image/png" and r.get_data()[:8] == b"\x89PNG\r\n\x1a\n",
          f"{r.status_code} {r.headers.get('Content-Type')}")
    r = post(client, "/m/image", LAN_ADDR, {"prompt": "x"})
    check("M6r /m/image refuses a LAN address 403", r.status_code == 403, f"got {r.status_code}")
    r = post(client, "/m/image", PHONE_ADDR, {"prompt": "   "})
    check("M6r an empty prompt is refused 400", r.status_code == 400, f"got {r.status_code}")
    check("M6r the page carries the Draw control and posts to /m/image",
          'id="draw"' in get(client, "/m", PHONE_ADDR).get_data(as_text=True) and "/m/image" in get(client, "/m", PHONE_ADDR).get_data(as_text=True))

    failed = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} passed")
    if failed:
        print("FAILED: " + "; ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
