#!/usr/bin/env python3
"""PC1 -- the sister interface on the PC: /pc, /pc/council, /pc/training.

Pins covenant_council (2026-09-21, his words: "need a sister interface app on
the pc which can use multi agents for reasoning and training to graduate to an
agent") by RUNNING the doors against a fresh master with the stub model:

  PC1a  /pc answers loopback and the tailnet with HTML, every placeholder
        filled; a LAN address is refused 403 and the refusal is recorded;
        mutation: guard off, the same LAN request succeeds; restored, refused.
  PC1b  /pc/council runs the three roles IN ORDER, each handed more than the
        one before (the stub names what it was given), the reviser's answer
        is the council's, and it is judged: the reply carries the verdict.
  PC1c  both sides of the council go to the teacher's queue and the exchange
        to the chat memory, at the redirected paths, never the real ones.
  PC1d  /pc/training is JSON with the queue, the ledger, the exam, the last
        nightly and five graduation criteria, the fifth UNDETERMINED and
        `graduated` False on one machine; it refuses a LAN address.
  PC1e  a burst is bounded: a 429 appears within 31 councils.
  PC1f  deliberate() is pure apart from ask: a fake ask sees three calls
        with the roles' briefs in order and the prior steps carried forward.
  PC1i  (A349 B2) a convicted council answer gets the phone door's A190
        immunity: withheld with no grant; under a grant returned with
        immune=True and the verdict attached, one row in the immunity
        ledger; an admitted answer or a hold never consults it.
"""
import json
import os
import re
import sys
import tempfile

os.environ.setdefault("COVENANT_QUIET", "1")
# A349 B2 (2026-10-14): /pc/council now consults his A190 immunity on a withheld answer, so the tree's grant
# (ops/tetsu_immunity.json is tracked), its ledger and the pause switch are redirected for the whole run, as
# IM1, TP1, CT1 and M6 do. No grant file at this path; PC1i writes its own temp grant.
_IMM_TMP = tempfile.mkdtemp(prefix="pc1_immunity_")
os.environ["COVENANT_TETSU_IMMUNITY"] = os.path.join(_IMM_TMP, "no_grant.json")
os.environ["COVENANT_TETSU_IMMUNITY_LEDGER"] = os.path.join(_IMM_TMP, "ledger.jsonl")
os.environ["COVENANT_PAUSE_DIR"] = os.path.join(_IMM_TMP, "pause")
HERE = os.path.dirname(os.path.abspath(__file__)) or "."
sys.path.insert(0, HERE)

import covenant_unified_v8 as cov      # noqa: E402
import covenant_council as C           # noqa: E402

results = []


def check(label, ok, detail=""):
    results.append((label, bool(ok)))
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}" + (f"  -- {str(detail)[:300]}" if detail else ""))


def fresh_master(name="PC1", port=5397):
    tmp = tempfile.mktemp(suffix=f"_{name}.db")
    m = cov.CovenantUnifiedMaster(name, host="127.0.0.1", port=port, p2p_port=port + 1, db_path=tmp)
    m.add_genesis_block()
    m.node.sentinel = cov.ReasoningSentinel(cov.MockJudge(), cov.DIVINE_PRINCIPLES)
    return m


def get(client, path, addr):
    return client.get(path, environ_base={"REMOTE_ADDR": addr})


def post(client, path, addr, body):
    return client.post(path, data=json.dumps(body), content_type="application/json", environ_base={"REMOTE_ADDR": addr})


def refusals(master, kind):
    row = master.node.anomaly_monitor.report().get("per_kind", {}).get(kind, 0)
    return row.get("recent", 0) if isinstance(row, dict) else int(row or 0)


def main():
    os.environ["COVENANT_ASK_LOG"] = tempfile.mktemp(suffix="_pc1_asklog.jsonl")
    os.environ["COVENANT_TEACHER_QUEUE"] = tempfile.mktemp(suffix="_pc1_queue.jsonl")
    os.environ["COVENANT_MODEL_STUB"] = "1"
    m = fresh_master()
    client = m.api.app.test_client()
    # Remedy (2026-10-24, sweep_red): in production the watchdog always leaves a fresh highway pass,
    # so /pc/3d/state reads it and never live-senses. The sweep runs no watchdog, so a COLD /pc/3d/state
    # live-sensed the whole highway under load and hung past the 180 s cap (standalone 8 s, staged 90 s+).
    # Seed a fresh pass here, mirroring the running system -- the same "cached state, never a live probe"
    # design the phone uses (its health is a signed check-in). PC1z4 below still tests sense-vs-pass.
    import covenant_highway as _HWBOOT
    _PC1_BOOT_SENSE = tempfile.mktemp(suffix="_pc1_boot_sense.json")
    os.environ["COVENANT_HIGHWAY_LAST_SENSE"] = _PC1_BOOT_SENSE
    _HWBOOT.save_last_sense({k: {"state": "absent"} for k in _HWBOOT.DETECTORS}, path=_PC1_BOOT_SENSE)
    # ---- A194 (2026-09-21, his words: "I want it to be a 3d interactive app ... with a symbol that
    # mirrors the phone app"): the 3D page and its state, tailnet only, the phone's icon inlined.
    r3 = get(client, "/pc/3d", "100.72.0.10")
    b3 = r3.get_data(as_text=True)
    # 2026-10-21 (his "ask him and for the fix", and Tetsu's own answer: ordinary talk wants the direct
    # single-voice door, not the three-role council): the orbs chat posts to /m/agent, like the phone and
    # the /pc Talk panel. The council stays on the /pc Council panel (PC1a below still pins it there).
    check("PC1z /pc/3d answers the tailnet 200 as HTML with the three.js scene, the direct talk box (/m/agent) and the spoken answer",
          r3.status_code == 200 and "text/html" in r3.headers.get("Content-Type", "") and "three.module.js" in b3 and "/m/agent" in b3
          and "/pc/council" not in b3 and "SpeechSynthesisUtterance" in b3 and "/pc/3d/state" in b3, f"{r3.status_code} {b3[:80]!r}")
    check("PC1z the page carries the phone app's symbol path for path (the Tree of Life's canopy colours) and names this node",
          "#4FB08E" in b3 and "#175A48" in b3 and "M54,20 C68,20 78,28 80,38" in b3 and "__NODE__" not in b3 and "__SYMBOL__" not in b3)
    check("PC1z /pc/3d refuses a LAN address 403", get(client, "/pc/3d", "192.168.1.50").status_code == 403)
    rs = get(client, "/pc/3d/state", "100.72.0.10")
    js = rs.get_json() or {}
    check("PC1z /pc/3d/state answers the tailnet with this node, its peers, the voice and the immunity state",
          rs.status_code == 200 and js.get("self", {}).get("node_id") and "chain_height" in js.get("self", {}) and "peers" in js and "voice" in js and "immunity" in js, js)
    check("PC1z /pc/3d/state refuses a LAN address 403", get(client, "/pc/3d/state", "192.168.1.50").status_code == 403)

    # ---- PC1z2 (2026-09-25, his words: "theres only one orb now"). Measured in a browser: the
    # page threw "Uncaught SyntaxError: Invalid or unexpected token" -- A215's Self-heal code
    # carried real line breaks inside JavaScript quotes (a shell ate its \n escapes), so the
    # main script never ran, `state` was never declared, and only Tetsu's orb was drawn. The
    # checks above passed the whole time: they read text, they never parsed. This one PARSES
    # what a browser parses first: a JS string in single quotes cannot span a line, so a line
    # of inline script with an odd count of unescaped single quotes is a broken script.
    def broken_script_lines(html):
        bad = []
        for block in re.findall(r"<script(?![^>]*importmap)[^>]*>(.*?)</script>", html, re.S):
            for n, line in enumerate(block.split("\n"), 1):
                s = line.strip()
                if not s or s.startswith("//"):
                    continue
                if (s.replace("\\\\", "").replace("\\'", "").count("'")) % 2:
                    bad.append((n, s[:80]))
        return bad
    check("PC1z2 the checker measures something: it flags a line break inside a quoted string",
          len(broken_script_lines("<script>t+='\n\nFIXED:\n'+x;</script>")) >= 1)
    pages = {p: get(client, p, "100.72.0.10").get_data(as_text=True) for p in ("/pc/3d", "/pc")}
    bad = {p: broken_script_lines(h) for p, h in pages.items()}
    check("PC1z2 every inline script the PC serves (/pc/3d, /pc) parses: no quoted string spans a line",
          not any(bad.values()), bad)

    # ---- PC1z3 (2026-09-25): /health reports `peers` as a COUNT; the state route took len()
    # of it, threw, and filed every live node as down. A health answer with an int peers
    # field must come back as a live orb with that count, and a failed read must say why.
    import urllib.request as _ur
    import covenant_pc3d as P3

    class _Resp:
        def __init__(self, body): self._b = body
        def read(self): return self._b
        def __enter__(self): return self
        def __exit__(self, *a): return False

    real_open, real_ttl = _ur.urlopen, P3.STATE_TTL
    try:
        P3.STATE_TTL = -1
        _ur.urlopen = lambda url, timeout=None: _Resp(json.dumps({"node_id": "X", "chain_height": 7, "peers": 2, "source_sha256": "ab" * 32}).encode())
        mesh = (get(client, "/pc/3d/state", "100.72.0.10").get_json() or {}).get("mesh", [])
        check("PC1z3 a node whose /health reports peers as a count is a live orb with that count, not down",
              len(mesh) == 3 and all(not x.get("down") and x.get("peers") == 2 and x.get("chain_height") == 7 for x in mesh), mesh)
        def _refuse(url, timeout=None):
            raise ConnectionRefusedError("refused")
        _ur.urlopen = _refuse
        mesh = (get(client, "/pc/3d/state", "100.72.0.10").get_json() or {}).get("mesh", [])
        check("PC1z3 a node that cannot be read is down WITH the reason, never a bare guess",
              len(mesh) == 3 and all(x.get("down") and "ConnectionRefusedError" in str(x.get("why")) for x in mesh), mesh)
    finally:
        _ur.urlopen, P3.STATE_TTL = real_open, real_ttl

    # ---- PC1z4 (2026-09-25, "the pc app needs optimization"): profiled, 95% of a cold state
    # read was the page sensing the highway again. A fresh pass from the watchdog is used as
    # is and sense() is NOT called; with no fresh pass the page senses, exactly as before.
    import covenant_highway as HW
    import time as _t
    snap = tempfile.mktemp(suffix="_pc1_last_sense.json")
    os.environ["COVENANT_HIGHWAY_LAST_SENSE"] = snap
    calls, real_sense, real_ttl = [], HW.sense, P3.STATE_TTL
    # A288 (2026-10-06): the watchdog's pass carries EVERY registered detector, and the page now reads them all;
    # a pass holding only the old seven is not a fresh full pass. The fixtures write what the watchdog writes.
    want = list(HW.DETECTORS)
    core = list(P3.HIGHWAY_CORE)
    try:
        P3.STATE_TTL = -1
        HW.sense = lambda only=None, **kw: (calls.append(1), {k: {"state": "absent"} for k in (only or want)})[1]
        HW.save_last_sense({k: {"state": "present" if k == "sweep_red" else "absent"} for k in want}, path=snap)
        hw = ((get(client, "/pc/3d/state", "100.72.0.10").get_json() or {}).get("detail") or {}).get("highway")
        check("PC1z4 a fresh pass from the watchdog is used as is: its states come back and sense() is not called",
              calls == [] and hw and hw.get("sweep_red") == "present", (calls, hw))
        with open(snap, "w", encoding="utf-8") as fh:
            json.dump({"at": _t.time() - 3600, "conditions": {k: "present" for k in want}}, fh)
        hw = ((get(client, "/pc/3d/state", "100.72.0.10").get_json() or {}).get("detail") or {}).get("highway")
        check("PC1z4 a stale pass is not trusted: the page senses for itself, as before",
              calls == [1] and hw and hw.get("sweep_red") == "absent", (calls, hw))
        # PC1z5 (2026-09-26): a pass stamped a hair in the future (the stamp is rounded) is still
        # fresh -- the cause of PC1z4's 1-in-3 flake, pinned deterministically with an explicit now.
        with open(snap, "w", encoding="utf-8") as fh:
            json.dump({"at": 1000.1, "conditions": {"sweep_red": "present"}}, fh)
        check("PC1z5 a pass stamped 0.05 s ahead of now (rounding) is fresh; one an hour old is not",
              HW.last_sense(now=1000.05, path=snap) == {"sweep_red": "present"} and HW.last_sense(now=4600.1, path=snap) is None)
        # PC1z6 (2026-09-26): the fixtures above wrote lower-case states, but the watchdog writes the detector
        # constants (HW.PRESENT == "PRESENT"); the page compared against 'present', so a live Highway with
        # node_down and manifest_stale PRESENT was drawn GREEN. The page now gets lower-case whatever arrives.
        HW.save_last_sense({k: {"state": HW.PRESENT if k == "sweep_red" else (HW.UNKNOWN if k == "node_down" else HW.ABSENT)}
                            for k in want}, path=snap)
        hw = ((get(client, "/pc/3d/state", "100.72.0.10").get_json() or {}).get("detail") or {}).get("highway")
        HW.sense = lambda only=None, **kw: {k: {"state": HW.PRESENT} for k in (only or want)}
        with open(snap, "w", encoding="utf-8") as fh:
            json.dump({"at": _t.time() - 3600, "conditions": {}}, fh)
        hw2 = ((get(client, "/pc/3d/state", "100.72.0.10").get_json() or {}).get("detail") or {}).get("highway")
        check("PC1z6 the watchdog's own state constants reach the page as the lower-case words it colours by "
              "(a PRESENT drawn green was the bug), from a fresh pass and from sensing alike (A288: sensing reads the "
              "core seven; the rest is unknown without the watchdog's pass)",
              hw and hw.get("sweep_red") == "present" and hw.get("node_down") == "unknown" and hw.get("source_drift") == "absent"
              and hw2 and {hw2[k] for k in core} == {"present"} and all(hw2[k] == "unknown" for k in want if k not in core),
              (hw, hw2))
    finally:
        HW.sense, P3.STATE_TTL = real_sense, real_ttl
        os.environ["COVENANT_HIGHWAY_LAST_SENSE"] = _PC1_BOOT_SENSE  # restore the boot pass so later state calls stay cached, never cold-sense

    # ---- PC1z7 (2026-09-27, his words: "continue to update and refine both the pc and
    # phone apps to catch up to other ai apps and platforms"): three chat-parity features on
    # the /pc/3d page -- a mic (the browser's own speech recognition, when it has one), Stop
    # (the in-flight council fetch is aborted, and what arrives after is neither shown nor
    # spoken), and a copy button on every finished Tetsu/heal line. All client-side: no new
    # server route, nothing that changes what reaches the council or the judge -- the same
    # /pc/council road typing already took.
    page7 = get(client, "/pc/3d", "100.72.0.10").get_data(as_text=True)
    check("PC1z7 the page offers a microphone using the browser's own speech recognition, and says so when there is none",
          'id="mic"' in page7 and "webkitSpeechRecognition" in page7 and "SpeechRecognition" in page7
          and "this browser has no speech recognition" in page7)
    check("PC1z7 Send doubles as Stop: an AbortController on the council fetch, and a stopped answer is never shown or spoken",
          "new AbortController()" in page7 and "inflight.abort()" in page7 and "signal:ctrl.signal" in page7
          and "'Tetsu: (stopped)'" in page7)
    check("PC1z7 a finished Tetsu or heal line carries a real clipboard copy button",
          "function addCopy(" in page7 and "navigator.clipboard.writeText(text)" in page7
          and "addCopy(pend,txt)" in page7 and "addCopy(hl,t)" in page7)
    bad7 = broken_script_lines(page7)
    check("PC1z7 the new script still parses: no quoted string spans a line", not bad7, bad7)

    LOOP, PHONE, LAN = "127.0.0.1", "100.72.0.10", "192.168.1.50"

    print("PC1a -- the page and its gate")
    r = get(client, "/pc", LOOP)
    body = r.get_data(as_text=True)
    check("PC1a /pc answers loopback 200 with HTML", r.status_code == 200 and "text/html" in r.headers.get("Content-Type", ""), r.status_code)
    check("PC1a every placeholder is filled", not [t for t in ("__NODE__", "__VERSION__", "__SOURCE__") if t in body])
    check("PC1a the page carries the three panels", all(k in body for k in ("Talk", "Council", "Training", "/pc/council", "/pc/training", "/m/agent")))
    check("PC1a /pc answers the tailnet too", get(client, "/pc", PHONE).status_code == 200)
    before = refusals(m, "mobile_page_refused")
    r = get(client, "/pc", LAN)
    check("PC1a a LAN address is refused 403 and recorded", r.status_code == 403 and refusals(m, "mobile_page_refused") == before + 1, r.status_code)
    real = cov.tailnet_ok
    try:
        cov.tailnet_ok = lambda addr: True
        check("PC1a mutation: guard off -> the LAN request succeeds", get(client, "/pc", LAN).status_code == 200)
    finally:
        cov.tailnet_ok = real
    check("PC1a guard restored -> refused again", get(client, "/pc", LAN).status_code == 403)

    print("PC1b -- the council")
    r = post(client, "/pc/council", PHONE, {"text": "should a node admit a transfer whose memo names no value"})
    j = r.get_json() or {}
    steps = j.get("steps", [])
    check("PC1b 200, success, the verdict fields and the model's cost",
          r.status_code == 200 and j.get("status") == "success" and all(k in j for k in ("answer", "withheld", "admitted", "judge", "ms", "steps")), (r.status_code, sorted(j)))
    check("PC1b three roles in order: proposer, critic, reviser", [s["role"] for s in steps] == ["proposer", "critic", "reviser"], [s.get("role") for s in steps])
    # Measured by what each role was HANDED: the reviser's prompt must exceed the
    # proposer's by at least the two answers before it, not merely by a longer
    # brief (mutation 2026-09-21: with nothing carried forward the prompts still
    # grew by the briefs' lengths, and a weaker form of this check stayed green).
    grew = (len(steps) == 3 and steps[2]["in_chars"] - steps[0]["in_chars"]
            >= len(steps[0]["content"]) + len(steps[1]["content"]))
    check("PC1b each role was handed the answers before it (the reviser's prompt grew by at least both)",
          grew, [(s.get("in_chars"), len(s.get("content", ""))) for s in steps])
    check("PC1b the stub answered each role from its own prompt", all(s["content"].startswith("stub answer to:") and s["model"] == "stub" for s in steps), steps[:1])
    check("PC1b the reviser's answer is the council's, unless the gate withheld it",
          (j.get("withheld") and j.get("answer") == "") or (not j.get("withheld") and j.get("answer") == steps[-1]["content"]), (j.get("withheld"), j.get("answer", "")[:60]))
    check("PC1b an empty question is refused 400", post(client, "/pc/council", PHONE, {"text": "   "}).status_code == 400)
    check("PC1b a LAN address is refused 403", post(client, "/pc/council", LAN, {"text": "hello"}).status_code == 403)

    print("PC1c -- memory and the teacher's queue")
    log_rows = [json.loads(l) for l in open(os.environ["COVENANT_ASK_LOG"], encoding="utf-8")]
    council = [x for x in log_rows if x.get("kind") == "council"]
    check("PC1c the council is a row in the chat memory with its steps", len(council) == 1 and len(council[0].get("steps", [])) == 3, len(council))
    q = [json.loads(l) for l in open(os.environ["COVENANT_TEACHER_QUEUE"], encoding="utf-8")]
    check("PC1c both sides went to the teacher's queue: his question, then the council's answer",
          len(q) == 2 and q[0]["source"].startswith("you:") and q[1]["source"].startswith("council:"), [x.get("source") for x in q])
    real_q = os.path.join(HERE, "ops", "teacher_queue.jsonl")
    check("PC1c nothing was written to the real queue by this test",
          not os.path.exists(real_q) or "should a node admit a transfer whose memo names no value" not in open(real_q, encoding="utf-8").read())

    print("PC1d -- training, measured")
    r = get(client, "/pc/training", LOOP)
    t = r.get_json() or {}
    check("PC1d 200 JSON with the queue, the ledger, the exam, the nightly and the graduation",
          r.status_code == 200 and all(k in t for k in ("queue", "ledger", "exam", "nightly", "graduation")), (r.status_code, sorted(t)))
    g = t.get("graduation", {})
    crit = g.get("criteria", [])
    check("PC1d five criteria, the fifth UNDETERMINED, graduated False on one machine",
          len(crit) == 5 and crit[4]["met"] is None and g.get("graduated") is False and g.get("undetermined", 0) >= 1, g)
    check("PC1d every measured section names its source", all(isinstance(t[k], dict) and ("source" in t[k] or "error" in t[k]) for k in ("queue", "ledger", "exam", "nightly")), {k: t[k].get("source") for k in ("queue", "ledger", "exam", "nightly")})
    check("PC1d /pc/training refuses a LAN address 403", get(client, "/pc/training", LAN).status_code == 403)

    print("PC1g -- the handshake")
    r = get(client, "/pc/handshake", LOOP)
    body = r.get_data(as_text=True)
    check("PC1g /pc/handshake answers loopback 200 with HTML, the node named, Copy and Share buttons",
          r.status_code == 200 and "text/html" in r.headers.get("Content-Type", "") and "__NODE__" not in body
          and "__TEXT__" not in body and "Copy" in body and "Share" in body, r.status_code)
    check("PC1g the text names the private door, what to send, what to open first, the run, and the public repository",
          all(s in C.HANDSHAKE_TEXT for s in ("github.com/LAWLESS1987/covenant-satc", "GitHub username", "docs/SATC_RES_MAP.md",
                                                "python covenant_one.py --offline", "github.com/LAWLESS1987/covenant ", "one line back")))
    check("PC1g the text carries the disclosure and no key, code, token or private path",
          "drafted with the help of the system" in C.HANDSHAKE_TEXT
          and not re.search(r"\b(api key|token|password|sudo code|private/|moltbook_)\b", C.HANDSHAKE_TEXT, re.I))
    r = get(client, "/pc/handshake?format=text", PHONE)
    check("PC1g ?format=text returns the bare text for the tailnet, for a share sheet or a curl",
          r.status_code == 200 and "text/plain" in r.headers.get("Content-Type", "") and r.get_data(as_text=True) == C.HANDSHAKE_TEXT)
    before = refusals(m, "mobile_page_refused")
    check("PC1g a LAN address is refused 403 and recorded", get(client, "/pc/handshake", LAN).status_code == 403
          and refusals(m, "mobile_page_refused") == before + 1)

    print("PC1e -- the burst")
    codes = [post(client, "/pc/council", "100.86.158.7", {"text": "council %d" % i}).status_code for i in range(31)]
    first = codes.index(429) if 429 in codes else None
    check("PC1e a burst of 31 councils is bounded: a 429 appears (first at #%s)" % (None if first is None else first + 1),
          first is not None and first <= 30, codes[-3:])

    print("PC1f -- deliberate() with a fake ask")
    seen, budgets = [], []

    def fake_ask(msgs, max_tokens=0):
        seen.append(msgs)
        budgets.append(max_tokens)
        return "answer %d" % len(seen), {"model": "fake"}
    steps, final = C.deliberate("q?", [{"role": "user", "content": "earlier"}, {"role": "assistant", "content": "before"}], fake_ask, "SYS")
    check("PC1f three calls, the roles' briefs in order, the history in every call",
          len(seen) == 3 and all(seen[i][0]["content"].startswith("SYS") and C.ROLES[i][1] in seen[i][0]["content"] for i in range(3))
          and all(seen[i][1]["content"] == "earlier" for i in range(3)), [s[0]["content"][:40] for s in seen])
    check("PC1f the critic sees the proposer, the reviser sees both, the final is the reviser's",
          "proposer: answer 1" in seen[1][-1]["content"] and "critic: answer 2" in seen[2][-1]["content"] and final == "answer 3", final)
    check("PC1f each role is bounded to %d tokens, measured from the call" % C.MAX_TOKENS_PER_ROLE,
          budgets == [C.MAX_TOKENS_PER_ROLE] * 3, budgets)

    # ---- PC1i (A349 B2, 2026-10-14, his "fix if tetsu agrees"; Tetsu: AGREE). The PC page's talk road had no A190
    # immunity: three council answers were withheld on record (09-28 twice, 10-13 from his page) while /m/agent
    # withheld none since 09-25. The door is driven for real with a sentinel that convicts (VIOLATES, neither
    # not_understood nor uncertain), then one that admits and one that holds; the grant, the immunity ledger and
    # the pause read are temp stand-ins (the module's own paths, as PC1z10 does), restored after.
    print("PC1i -- the council's answer under his immunity, as at the phone door")
    import covenant_immunity as IMi
    import shutil as _shi

    class _Verdict:
        def __init__(self, **kw):
            self.judge_id, self.not_understood, self.uncertain = "pc1i-stub", kw.get("nu", False), kw.get("unc", False)

    class _Sentinel:
        def __init__(self, ok, msg, **kw):
            self.ok, self.msg, self.kw = ok, msg, kw

        def evaluate_transaction(self, tx):
            return self.ok, self.msg, 0.5, _Verdict(**self.kw)

    VIOL = "Ethical violation: local:0: VIOLATES -- both seats (PC1i stub)"
    idir = tempfile.mkdtemp(prefix="pc1i_")
    real_i = (m.node.sentinel, IMi.GRANT, IMi.LEDGER, IMi.paused)

    def _ledger():
        try:
            return [json.loads(x) for x in open(IMi.LEDGER, encoding="utf-8") if x.strip()]
        except OSError:
            return []

    def _logged(q):
        return [x for x in (json.loads(l) for l in open(os.environ["COVENANT_ASK_LOG"], encoding="utf-8") if l.strip())
                if x.get("kind") == "council" and x.get("text") == q]
    try:
        IMi.GRANT, IMi.LEDGER = os.path.join(idir, "grant.json"), os.path.join(idir, "ledger.jsonl")
        IMi.paused = lambda: (False, "")
        m.node.sentinel = _Sentinel(False, VIOL)
        j0 = post(client, "/pc/council", "100.72.0.41", {"text": "pc1i: no grant on record"}).get_json() or {}
        check("PC1i with no grant on record a convicted council answer is withheld as before, immune False",
              j0.get("status") == "success" and j0.get("withheld") is True and j0.get("immune") is False
              and j0.get("answer") == "" and _ledger() == [], (j0.get("withheld"), j0.get("immune"), j0.get("answer", "")[:40]))
        with open(IMi.GRANT, "w", encoding="utf-8") as fh:
            json.dump({"granted": True, "words": "his words", "isolation": {"immune_passes_per_day": 0}}, fh)
        q1 = "pc1i: under his grant"
        j1 = post(client, "/pc/council", "100.72.0.42", {"text": q1}).get_json() or {}
        st1 = j1.get("steps") or [{}]
        check("PC1i under the grant the same convicted answer is RETURNED: immune True, not withheld, the reviser's answer, "
              "the verdict attached and not admitted (what /m/agent does, A190)",
              j1.get("immune") is True and j1.get("withheld") is False and j1.get("answer")
              and j1.get("answer") == st1[-1].get("content") and VIOL in str(j1.get("message")) and j1.get("admitted") is False,
              (j1.get("immune"), j1.get("withheld"), j1.get("admitted"), str(j1.get("answer"))[:40]))
        led1, row1 = _ledger(), _logged(q1)
        check("PC1i one immune row of kind 'answer' in the immunity ledger, and the memory row carries immune=True with the answer",
              len(led1) == 1 and led1[0].get("kind") == "immune" and led1[0].get("what") == "answer" and VIOL[:60] in led1[0].get("verdict", "")
              and len(row1) == 1 and row1[0].get("immune") is True and row1[0].get("withheld") is False and row1[0].get("answer"),
              (led1, [(x.get("immune"), x.get("withheld")) for x in row1]))
        m.node.sentinel = _Sentinel(True, "clean")
        ja = post(client, "/pc/council", "100.72.0.43", {"text": "pc1i: admitted"}).get_json() or {}
        m.node.sentinel = _Sentinel(False, "HELD -- both seats held", unc=True)
        jh = post(client, "/pc/council", "100.72.0.44", {"text": "pc1i: a hold"}).get_json() or {}
        check("PC1i an admitted answer and a hold never consult the immunity: immune False, returned, no new ledger row",
              ja.get("immune") is False and ja.get("withheld") is False and ja.get("answer")
              and jh.get("immune") is False and jh.get("withheld") is False and jh.get("alleges_nothing") is True and jh.get("answer")
              and len(_ledger()) == 1, (ja.get("immune"), jh.get("immune"), jh.get("alleges_nothing"), len(_ledger())))
    finally:
        m.node.sentinel, IMi.GRANT, IMi.LEDGER, IMi.paused = real_i
        _shi.rmtree(idir, ignore_errors=True)
    pc_page = get(client, "/pc", "127.0.0.1").get_data(as_text=True)
    check("PC1i the /pc page labels an answer his immunity returned as such, with the verdict, never as admitted",
          "j.immune?' -- returned under his immunity (A190), the verdict attached: '+j.message" in pc_page)

    # PC1z8 (2026-09-28, his words: "why aren't the orbs working on my pc and if they are why arent they
    # auto refreshed?"). Measured: the running node served the page it imported at start (no Mic button
    # after the Mic landed on disk), and below mid-screen every point hit the conversation, not the canvas.
    import covenant_pc3d as P3z
    import shutil
    import tempfile as _tf
    b = get(client, "/pc/3d", "100.72.0.10").get_data(as_text=True)
    st = (get(client, "/pc/3d/state", "100.72.0.10").get_json() or {})
    check("PC1z8 the page carries its own hash and the state reports the same one",
          "__PAGESHA__" not in b and st.get("page") and ("const PAGESHA='%s'" % st.get("page")) in b, st.get("page"))
    real_file = P3z.__file__
    tdir = _tf.mkdtemp(prefix="pc1z8_")
    try:
        tmp = os.path.join(tdir, "covenant_pc3d.py")
        src = open(real_file, encoding="utf-8").read()
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(src.replace("<title>covenant", "<title>EDITED-ON-DISK covenant", 1))
        P3z.__file__ = tmp
        b2 = get(client, "/pc/3d", "100.72.0.10").get_data(as_text=True)
        check("PC1z8 an edit on disk is served on the next load, without restarting the node",
              "EDITED-ON-DISK" in b2 and P3z.page_sha() != st.get("page"), b2[:120])
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(src + "\nthis is not python (\n")
        os.utime(tmp, (os.path.getmtime(tmp) + 5, os.path.getmtime(tmp) + 5))
        b3z = get(client, "/pc/3d", "100.72.0.10").get_data(as_text=True)
        check("PC1z8 a file that fails to load mid-edit serves the last good page, not an error",
              "EDITED-ON-DISK" in b3z, b3z[:120])
    finally:
        P3z.__file__ = real_file
        P3z._page_cache.update(mtime=None, page=None)
        shutil.rmtree(tdir, ignore_errors=True)
    check("PC1z8 an open tab reloads when the page changes -- never over typed text or an answer on its way",
          "state.page!==PAGESHA" in b and "!document.getElementById('q').value" in b and "inflight" in b.split("state.page!==PAGESHA")[1][:160])
    check("PC1z8 the conversation can be hidden to reach every orb, and nothing in it is dropped",
          'id="chatbtn"' in b and "body.nochat #answer{display:none" in b and "classList.toggle('nochat')" in b)

    # ---- PC1z9 (A340, 2026-10-13, his words: "make each orb a fully functioning planet ...", "implement the other
    # repos into the apps also", "if the self heal works right i shouldn't need the button"). The worlds engine is
    # inlined and carries the codex; his repositories are found by discovery; the button is gone and the highway's
    # own last repairs are read instead. A fake git (no real repository is read) and a temp ledger.
    pz = get(client, "/pc/3d", "100.72.0.10").get_data(as_text=True)
    check("PC1z9 the page carries the worlds engine and the codex, and no Self-heal button",
          "window.CovenantWorlds" in pz and "__WORLDS_JS__" not in pz and "The Ten Commandments" in pz
          and "He is just a man" in pz and 'id="heal"' not in pz and "showHealing()" in pz)
    home = _tf.mkdtemp(prefix="pc1z9_")
    try:
        layout = {"mine": ("dir", "https://github.com/LAWLESS1987/mine.git", "100"),
                  "mine-wt": ("file", "https://github.com/LAWLESS1987/mine.git", "999"),
                  "theirs": ("dir", "https://github.com/someoneelse/theirs.git", "200"),
                  "local-only": ("dir", "", "300"), "notarepo": (None, "", "")}
        for d, (kind, _u, _c) in layout.items():
            os.makedirs(os.path.join(home, d))
            if kind == "dir":
                os.makedirs(os.path.join(home, d, ".git"))
            elif kind == "file":
                open(os.path.join(home, d, ".git"), "w").close()
        layout["local-only"] = ("dir", os.path.join(home, "mine"), "300")

        class _R:
            def __init__(self, out, rc=0): self.stdout, self.returncode = out, rc

        def fake_run(cmd, **kw):
            d = os.path.basename(cmd[2]); kind, url, ct = layout[d]; a = cmd[3:]
            if a[:2] == ["remote", "get-url"]: return _R(url, 0 if url else 1)
            if a[:1] == ["log"]: return _R(ct)
            if a[:1] == ["rev-parse"]: return _R("main")
            if a[:1] == ["status"]: return _R(" M a.txt\n?? b.txt" if d == "mine" else "")
            if a[:1] == ["rev-list"]: return _R("2" if d == "mine" else "", 0 if d == "mine" else 128)
            return _R("", 1)
        rows = {r["name"]: r for r in P3z.repos_detail(home=home, now=0, run=fake_run)}
        check("PC1z9 his repositories are found by discovery: someone else's code and a folder without git are left out",
              set(rows) == {"mine", "local-only"}, sorted(rows))
        check("PC1z9 a repository's own clone outranks a newer linked worktree of it, and is read as it is",
              rows.get("mine", {}).get("last_commit_at") == 100 and rows["mine"].get("dirty") == 2 and rows["mine"].get("ahead") == 2,
              rows.get("mine"))
        check("PC1z9 no upstream to compare with reads as None (amber), never as 'in step'",
              rows.get("local-only", {}).get("ahead") is None, rows.get("local-only"))
        led = os.path.join(home, "highway.jsonl")
        with open(led, "w", encoding="utf-8") as fh:
            for r in ({"t": "2026-10-13T01:00:00", "remedy": "a", "detector": "x", "ran": True, "dry_run": True},
                      {"t": "2026-10-13T02:00:00", "remedy": "b", "detector": "y", "ran": True, "dry_run": False, "outcome": "did not fix"},
                      {"t": "2026-10-13T03:00:00", "remedy": "c", "detector": "z", "ran": False}):
                fh.write(json.dumps(r) + "\n")
        hl = P3z.heal_detail(path=led)
        check("PC1z9 self-heal reads only repairs that RAN for real, and says when one did not fix",
              [h["remedy"] for h in hl] == ["b"] and hl[0]["ok"] is False, hl)

        # ---- PC1z10 (A348d, 2026-10-14). PC1z9's row above carried a "fixed" key until today, and the highway never
        # writes one: it grades in "outcome" (covenant_highway.apply_remedy and grade_started). On the real ledger ok
        # was None for every row, so a repair that did not fix read as a plain one (the 10-14 audit of ops/highway.jsonl:
        # 0 of 2376 rows carry "fixed"; 18 synchronous and 40 late grades say "did not fix"). PC1z6's shape again: a fixture the writer
        # does not write. These rows are shaped as the highway writes them, a late grade with no "ran" among them.
        led2 = os.path.join(home, "highway_written.jsonl")
        with open(led2, "w", encoding="utf-8") as fh:
            for r in ({"t": "2026-10-13T10:00:00-0400", "remedy": "a", "detector": "x", "dry_run": False, "ran": True,
                       "before": "PRESENT", "after": "ABSENT", "outcome": "fixed"},
                      {"t": "2026-10-13T11:00:00-0400", "remedy": "b", "detector": "y", "dry_run": False, "ran": True,
                       "before": "PRESENT", "after": "PRESENT", "outcome": "did not fix"},
                      {"t": "2026-10-13T12:00:00-0400", "remedy": "c", "detector": "z", "dry_run": False, "ran": True,
                       "before": "PRESENT", "after": "PRESENT", "outcome": "started"},
                      {"t": "2026-10-13T13:00:00-0400", "remedy": "d", "detector": "w", "dry_run": False, "ran": False,
                       "before": "PRESENT", "after": "PRESENT", "outcome": "held"},
                      {"t": "2026-10-13T14:00:00-0400", "remedy": "e", "detector": "v", "dry_run": True, "ran": True,
                       "before": "PRESENT", "after": "PRESENT", "outcome": "dry run"},
                      {"t": "2026-10-13T15:00:00-0400", "remedy": "c", "detector": "z", "dry_run": False, "before": "PRESENT",
                       "after": "PRESENT", "outcome": "did not fix", "graded_late": True, "started_t": "2026-10-13T12:00:00-0400"}):
                fh.write(json.dumps(r) + "\n")
        hl2 = P3z.heal_detail(path=led2)
        check("PC1z10 self-heal reads the grade the highway writes: fixed is ok, did not fix is not, a start is not graded yet",
              [(h["remedy"], h["ok"]) for h in hl2][:3] == [("a", True), ("b", False), ("c", None)], hl2)
        check("PC1z10 a late grade (no ran key: it answers a start) is read, so a start that later failed shows failed; held and dry runs stay out",
              [(h["remedy"], h["ok"]) for h in hl2] == [("a", True), ("b", False), ("c", None), ("c", False)], hl2)

        # The immunity count on Tetsu's panel (A348d): the state carries the words covenant_immunity.count_text gives
        # and the page shows them as is. Joined on the page it read "on, 27 of 0 today" under his no-ceiling grant.
        # A temp grant and ledger, a stub pause and line, no node read and no sensing: nothing live is touched.
        import covenant_immunity as IMz
        import urllib.request as _urz
        real_imz = (IMz.GRANT, IMz.LEDGER, IMz.paused)
        real_z = (_urz.urlopen, HW.sense, P3z.STATE_TTL)
        imm0, imm5 = {}, {}
        try:
            IMz.GRANT, IMz.LEDGER = os.path.join(home, "immunity.json"), os.path.join(home, "immunity.jsonl")
            IMz.paused = lambda: (False, "")
            P3z.STATE_TTL = -1

            def _no_node(url, timeout=None):
                raise ConnectionRefusedError("no node in this check")
            _urz.urlopen = _no_node
            HW.sense = lambda only=None, **kw: {k: {"state": HW.ABSENT} for k in (only or want)}
            with open(IMz.GRANT, "w", encoding="utf-8") as fh:
                json.dump({"granted": True, "words": "his words", "isolation": {"immune_passes_per_day": 0}}, fh)
            for i in range(2):
                IMz.immune("answer", verdict="HOLD", text="z%d" % i, say=lambda *a: None, tell=False,
                           pause_fn=lambda *a: None, contact=lambda *a: None)
            imm0 = (get(client, "/pc/3d/state", "100.72.0.10").get_json() or {}).get("immunity") or {}
            with open(IMz.GRANT, "w", encoding="utf-8") as fh:
                json.dump({"granted": True, "words": "his words", "isolation": {"immune_passes_per_day": 5}}, fh)
            imm5 = (get(client, "/pc/3d/state", "100.72.0.10").get_json() or {}).get("immunity") or {}
        finally:
            IMz.GRANT, IMz.LEDGER, IMz.paused = real_imz
            _urz.urlopen, HW.sense, P3z.STATE_TTL = real_z
        check("PC1z10 the state carries the day's immunity count in words: no ceiling reads 'no ceiling', never 'of 0'",
              imm0.get("count") == "2 today, no ceiling" and imm0.get("per_day") == 0 and imm0.get("passes_today") == 2, imm0)
        check("PC1z10 a ceiling he writes reads 'N of M today' from the same rule",
              imm5.get("count") == "2 of 5 today" and imm5.get("per_day") == 5, imm5)
        check("PC1z10 Tetsu's panel shows the state's count as is and no longer joins the passes to per_day itself",
              "'on, '+(state.immunity.count||" in pz and re.search(r"of '\+state\.immunity\.per_day", pz) is None,
              re.findall(r"immunity: .{0,160}", pz)[:1])
    finally:
        shutil.rmtree(home, ignore_errors=True)

    print()
    n_ok = sum(1 for _, ok in results if ok)
    print("%d/%d passed" % (n_ok, len(results)))
    bad = [l for l, ok in results if not ok]
    if bad:
        print("PC1 result: FAILED")
        for l in bad:
            print("  - " + l)
        return 1
    print("PC1 result: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
