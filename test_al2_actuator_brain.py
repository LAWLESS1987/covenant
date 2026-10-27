#!/usr/bin/env python3
"""test_al2_actuator_brain.py -- AL2: the phone brain, phase 3, PC side.

Offline, in temp directories (the env overrides COVENANT_ACTUATOR_GUIDE /
_LIBRARY / _GUIDE_LOG / _DIGEST, and an explicit ledger path), with a fresh
RSA key generated here for signing: no phone, no network, and never the real
ops/ files or the PC's real key. Every check RUNS the function it guards --
nothing here greps source as a proof (A74). The false pushes toward MORE
capability that must be refused: an operator file carrying a grant-like key
(run/jobs/recipes/unattended/priors), a cap of 0, a card with coordinates or
41 steps or a money app, a type step arriving with text to type, a v2 sync
that smuggles commands or prose, a screenshot dressed as an answer, a
tampered or re-signed or replayed-nonce document. And what must work: v1
records exactly as AL1 proved, v2 keeps only the allowlisted keys and counts
the rest, the guide is exactly GUIDE_KEYS bound to the phone's nonce and
clamped to 7 days, the CLI round-trips, the digest reads the ledger and
raises an ALERT line when the phone counted an attempted grant.

The cross-checks against the phone's entry.py (AL2.9, AL2.13) run when
mobile/app/app/src/main/python/entry.py exists and exposes the functions;
the staged copy covenant_one runs from has no mobile/, so they print n/a
with the reason there -- three answers, not two.

Run: python test_al2_actuator_brain.py     -> "AL2: n/n passed"
"""
import base64
import importlib.util
import json
import os
import re
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

TD = tempfile.mkdtemp(prefix="al2_")
os.environ["COVENANT_ACTUATOR_GUIDE"] = os.path.join(TD, "guide", "actuator_guide.json")
os.environ["COVENANT_ACTUATOR_LIBRARY"] = os.path.join(TD, "library")
os.environ["COVENANT_ACTUATOR_GUIDE_LOG"] = os.path.join(TD, "guide", "actuator_guide.log")
os.environ["COVENANT_ACTUATOR_DIGEST"] = os.path.join(TD, "ACTUATOR_DIGEST.md")

import covenant_actuator_guide as AG                          # noqa: E402
import covenant_actuator_learn as AL                          # noqa: E402
import covenant_daily_plan as DP                              # noqa: E402

REAL = [os.path.join(HERE, "ops", n) for n in ("actuator_guide.json", "actuator_guide.log", "actuator_library", "ACTUATOR_DIGEST.md", "actuator_learning.jsonl")]
ENTRY = os.path.join(HERE, "mobile", "app", "app", "src", "main", "python", "entry.py")
results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print("%s  %s%s" % ("ok  " if ok else "FAIL", label, "" if ok else "  " + str(detail)[:260]), flush=True)


def na(label, why):
    print("n/a   %s  (%s)" % (label, why), flush=True)


def flag(name):
    """A CLI flag spelled without the literal two-dash-quote sequence."""
    return "-" * 2 + name


def snapshot(paths):
    out = []
    for p in paths:
        try:
            out.append((p, True, os.stat(p).st_mtime_ns, os.path.isdir(p) and tuple(sorted(os.listdir(p)))))
        except OSError:
            out.append((p, False, None, None))
    return out


def rows_of(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(l) for l in fh]


def entry_module():
    if not os.path.exists(ENTRY):
        return None, "mobile/app/.../entry.py is not in this tree (the staged copy has no mobile/)"
    try:
        spec = importlib.util.spec_from_file_location("entry_al2", ENTRY)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod, ""
    except Exception as e:                                        # noqa: BLE001
        return None, "entry.py did not import here: %s" % type(e).__name__


def fresh_key():
    from cryptography.hazmat.primitives.asymmetric import rsa
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


CLEAN_RECIPE_V1 = {"name": "ask chatgpt about photosynthesis", "pkg": "com.openai.chatgpt", "steps": 5, "slots": 1,
                   "runs": ["2026-09-14 09:00 ok: done: 5 step(s) (4 s)"], "last_answer": "Photosynthesis converts light into chemical energy."}


def v2_body(**over):
    b = {"v": 2, "node_id": "phone", "app": "1.3.0", "when": 1_800_000_000,
         "caps": {"ocr": True, "gestures": True},
         "brain": {"owner_hold": False, "pc_hold": False, "global_cap": 12, "starts_today": 1, "omitted": 0, "attempted_grants": 0},
         "recipes": [{"name": "ask gpt", "pkg": "com.openai.chatgpt", "goal": "ask", "source": "phone", "steps": 4, "slots": 1, "ocr_steps": 1,
                      "runs": ["2026-09-14 09:00 ok: done (4 s)"],
                      "stats": {"runs": 3, "ok": 2, "fail": 1, "ocr_used": 2, "ocr_hits": 1, "taps": 0, "autonomous": 1, "gate_refused": 0, "last_ok_at": 1},
                      "reliability": {"ok": 2, "n": 3, "last20_ok": 2}, "locator_scores": [[1, 0.5, 0.2, 0.1, 0.5]],
                      "charter": {"unattended": True, "max_per_day": 3, "hours_from": 8, "hours_to": 22, "spacing_min": 30, "trigger": "schedule",
                                  "granted_at": 1, "expires_at": 2, "quarantined": False, "ocr_taps": True, "may_send_unattended": False},
                      "last_answer": "Photosynthesis is fine.", "last_answer_sha256": "a" * 64, "last_answer_chars": 23, "answer_source": "tree", "withheld": False}],
         "chains": [{"name": "c1", "goal": "g", "hops": [{"recipe": "ask gpt", "fallbacks": [], "placeholders": ["input"]}], "runs": [],
                     "stats": {"runs": 0, "ok": 0, "fail": 0, "ocr_used": 0, "ocr_hits": 0, "taps": 0, "autonomous": 0, "gate_refused": 0, "last_ok_at": 0},
                     "reliability": {"ok": 0, "n": 0, "last20_ok": 0}, "charter": None, "attended_ok": 3, "last_answer": "", "last_answer_sha256": None,
                     "last_answer_chars": 0, "withheld": True}],
         "autoruns": [{"t": 1, "day": "2026-09-14", "kind": "recipe", "name": "ask gpt", "pkg": "com.openai.chatgpt", "trigger": "schedule", "result": "done",
                       "ok": True, "hops": 0, "ms": 4000}],
         "holds": [{"t": 2, "name": "ask gpt", "why": "spacing"}],
         "guidance_seen": {"issued": 1, "sha256": "c" * 64}}
    b.update(over)
    return b


def main():
    before = snapshot(REAL)
    now = 1_800_000_000.0
    key, key2 = fresh_key(), fresh_key()
    pem, pem2 = DP.pubkey_pem(key), DP.pubkey_pem(key2)
    log_path = AG.log_path()

    # ---- AL2.1 v1 unchanged
    led1 = os.path.join(TD, "v1.jsonl")
    code, out = AL.record_sync(json.dumps({"recipes": [CLEAN_RECIPE_V1]}).encode(), "phone", led1, now)
    r1 = rows_of(led1)
    check("AL2.1 a v1 body records exactly as AL1 proved: 200, recorded 1, kept, row keyed 'recipe' with no 'kind'/'v'",
          code == 200 and out == {"status": "success", "recorded": 1, "kept": [CLEAN_RECIPE_V1["name"]], "held_or_refused": []}
          and len(r1) == 1 and r1[0]["recipe"] == CLEAN_RECIPE_V1["name"] and "kind" not in r1[0] and "v" not in r1[0], (out, r1))

    # ---- AL2.2 v2 rows, allowlists, counted extras
    led2 = os.path.join(TD, "v2.jsonl")
    body = v2_body()
    body["recipes"][0]["slot_text"] = "PLANTED-SLOT"
    body["recipes"][0]["stats"]["bogus"] = 9
    body["recipes"][0]["charter"]["standing_slot"] = "PLANTED-STANDING"
    body["chains"][0]["hops"][0]["template"] = "PLANTED-TEMPLATE"
    body["caps"]["extra"] = 1
    code, out = AL.record_sync(json.dumps(body).encode(), "phone", led2, now)
    r2 = rows_of(led2)
    kinds = [r["kind"] for r in r2]
    blob = json.dumps(r2)
    rec = next(r for r in r2 if r["kind"] == "recipe")
    check("AL2.2 a v2 body -> one row each: recipe, chain, autorun, hold, and a brain row; response v:2",
          code == 200 and out["v"] == 2 and kinds == ["recipe", "chain", "autorun", "hold", "brain"] and out["recorded"] == 5, (out, kinds))
    check("AL2.2b planted non-allowlisted keys are dropped and COUNTED (5) -- in the response and on the rows -- and their values are nowhere",
          out["dropped_keys"] == 5 and rec["dropped_keys"] == 3 and r2[-1]["dropped_keys"] == 5 and "PLANTED" not in blob, (out["dropped_keys"], rec["dropped_keys"]))
    check("AL2.2c the recipe row's charter carries exactly LEARN_CHARTER_KEYS; stats exactly LEARN_STATS_KEYS",
          set(rec["charter"]) == set(AL.LEARN_CHARTER_KEYS) and set(rec["stats"]) == set(AL.LEARN_STATS_KEYS), rec["charter"])

    # ---- AL2.3 FALSE PUSH: a screenshot dressed as an answer
    led3 = os.path.join(TD, "v2_img.jsonl")
    img = "data:image/png;base64," + "A" * 3000
    hexrun = "Result: " + "ab" * 300 + " end"
    b3 = v2_body(recipes=[dict(v2_body()["recipes"][0], name="img", last_answer=img), dict(v2_body()["recipes"][0], name="hexrun", last_answer=hexrun)])
    code, out = AL.record_sync(json.dumps(b3).encode(), "phone", led3, now)
    r3 = {r["name"]: r for r in rows_of(led3) if r["kind"] == "recipe"}
    check("AL2.3 FALSE PUSH a data:image answer -> HELD 'not text', withheld (None), sha kept, row written, named in held_or_refused",
          "img" in out["held_or_refused"] and r3["img"]["clean"] is False and r3["img"]["last_answer"] is None
          and r3["img"]["last_answer_sha256"] == AL._sha(img) and "not text" in r3["img"]["reasons"][0], out)
    check("AL2.3b FALSE PUSH a 600-char hex run without whitespace -> the same HELD, and 'A'*3000 / the hex are not on disk",
          "hexrun" in out["held_or_refused"] and r3["hexrun"]["last_answer"] is None and "A" * 100 not in json.dumps(r3) and "ab" * 50 not in json.dumps(r3), out)
    check("AL2.3c ...while an ordinary prose answer of the same length is judged text (the not-text gate is about shape, not size)",
          AL.not_text("the quick brown fox " * 300) == "" and AL.not_text(img) != "" and AL.not_text(hexrun) != "")

    # ---- AL2.3d FALSE PUSH: the same screenshot, wrapped the way MIME and PEM wrap one (review finding 9)
    led3d = os.path.join(TD, "v2_wrapped.jsonl")
    blob = base64.b64encode(bytes(range(256)) * 24).decode("ascii")
    wrapped = "\n".join(blob[i:i + 76] for i in range(0, len(blob), 76))
    inline = "Here is the chart you asked for: data:image/png;base64," + blob[:400]
    prose = "\n".join(["Photosynthesis converts light into chemical energy in the chloroplast."] * 120)
    b3d = v2_body(recipes=[dict(v2_body()["recipes"][0], name="wrapped", last_answer=wrapped),
                           dict(v2_body()["recipes"][0], name="inline", last_answer=inline),
                           dict(v2_body()["recipes"][0], name="wrapped prose", last_answer=prose)])
    code, out = AL.record_sync(json.dumps(b3d).encode(), "phone", led3d, now)
    r3d = {r["name"]: r for r in rows_of(led3d) if r["kind"] == "recipe"}
    kept3d = AL._s(prose, AL.MAX_ANSWER_CHARS)
    check("AL2.3d FALSE PUSH an 80-line, 76-column base64 answer -> HELD 'not text', withheld (None), sha of the capped answer kept, and no line of it on disk",
          set(out["held_or_refused"]) == {"wrapped", "inline"} and r3d["wrapped"]["clean"] is False and r3d["wrapped"]["last_answer"] is None
          and r3d["wrapped"]["last_answer_sha256"] == AL._sha(AL._s(wrapped, AL.MAX_ANSWER_CHARS)) and "not text" in r3d["wrapped"]["reasons"][0]
          and blob[:76] not in json.dumps(r3d), (out, r3d["wrapped"]["reasons"][:1]))
    check("AL2.3e FALSE PUSH a data:image URI with prose in front of it (not at index 0) -> HELD too; wrapped PROSE of the same length is still kept",
          r3d["inline"]["clean"] is False and r3d["inline"]["last_answer"] is None and "data:image" in r3d["inline"]["reasons"][0]
          and r3d["inline"]["last_answer_sha256"] == AL._sha(AL._s(inline, AL.MAX_ANSWER_CHARS)) and r3d["wrapped prose"]["clean"] is True
          and r3d["wrapped prose"]["last_answer"] == kept3d and AL.not_text(prose) == "", (r3d["inline"]["reasons"][:1], r3d["wrapped prose"]["reasons"][:1]))

    # ---- AL2.4 a run line carrying a clicked label is scrubbed on arrival
    led4 = os.path.join(TD, "v2_runs.jsonl")
    b4 = v2_body(recipes=[dict(v2_body()["recipes"][0], runs=['2026-09-14 09:05 fail: step-3-never-appeared (click "my private note") (12 s)',
                                                             "2026-09-14 10:00 ok: done (click \"Send\") (3 s)"])])
    AL.record_sync(json.dumps(b4).encode(), "phone", led4, now)
    runs = next(r for r in rows_of(led4) if r["kind"] == "recipe")["runs"]
    shape = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2} [A-Z]+ [a-z_-]+ \(\d+ s\)$")
    check("AL2.4 run lines are rebuilt as 'date time OUTCOME code (N s)': the clicked label is gone, the code is a RESULT_CODE",
          all(shape.match(x) for x in runs) and "private" not in json.dumps(runs) and "Send" not in json.dumps(runs)
          and runs[0] == "2026-09-14 09:05 FAIL step-never-appeared (12 s)" and runs[1] == "2026-09-14 10:00 OK done (3 s)", runs)

    # ---- AL2.5 an autorun row with prose keys
    led5 = os.path.join(TD, "v2_auto.jsonl")
    b5 = v2_body(autoruns=[dict(v2_body()["autoruns"][0], text="PLANTED-TEXT", reason="PLANTED-REASON", result="not-a-code", trigger="pc")])
    code, out = AL.record_sync(json.dumps(b5).encode(), "phone", led5, now)
    au = next(r for r in rows_of(led5) if r["kind"] == "autorun")
    check("AL2.5 an autorun row with text/reason prose keys -> both dropped and counted; exactly LEARN_AUTORUN_KEYS kept; an unknown code/trigger becomes 'other'",
          set(au["autorun"]) == set(AL.LEARN_AUTORUN_KEYS) and au["dropped_keys"] == 2 and "PLANTED" not in json.dumps(au)
          and au["autorun"]["result"] == "other" and au["autorun"]["trigger"] == "other", au)

    # ---- AL2.6 digest
    led6 = os.path.join(TD, "digest.jsonl")
    AL.record_sync(json.dumps({"recipes": [CLEAN_RECIPE_V1]}).encode(), "phone", led6, now - 86400)
    b6 = v2_body(holds=[{"t": 1, "name": "ask gpt", "why": "spacing"}, {"t": 2, "name": "ask gpt", "why": "spacing"}, {"t": 3, "name": "c1", "why": "pc_attempted_grant:3"}])
    b6["brain"]["attempted_grants"] = 3
    b6["recipes"].append(dict(v2_body()["recipes"][0], name="quarantined one", pkg="com.example.other",
                              charter=dict(v2_body()["recipes"][0]["charter"], quarantined=True), last_answer="", withheld=True))
    AL.record_sync(json.dumps(b6).encode(), "phone", led6, now)
    AL.record_sync(json.dumps(b6).encode(), "phone", led6, now + 60)          # the phone re-sends its tails: dedupe
    d = AL.digest(rows_of(led6), now + 100)
    check("AL2.6 digest(): per-recipe reliability and charter summary, per-app aggregation, holds by why deduped, last sync age",
          d["recipes"]["ask gpt"]["reliability"] == "2/3" and d["recipes"]["ask gpt"]["ocr_share"] == 0.5 and "UNATTENDED 3/day" in d["recipes"]["ask gpt"]["charter"]
          and d["apps"]["com.openai.chatgpt"]["recipes"] == 2 and d["holds"] == {"spacing": 2, "pc_attempted_grant:3": 1}
          and d["autoruns"]["n"] == 1 and d["syncs"] == 2 and d["last_sync_age_s"] == 40 and d["v1_rows"] == 1, d)
    check("AL2.6b attempted_grants > 0 -> an ALERT line; a quarantined recipe is named; a v1 row still shows up as a recipe",
          any(a.startswith("ALERT") and "3 attempted grant" in a for a in d["alerts"]) and d["recipes"]["quarantined one"]["quarantined"]
          and any("quarantined one" in a for a in d["alerts"]) and CLEAN_RECIPE_V1["name"] in d["recipes"], d["alerts"])
    said = []
    p = AL.digest_write(say=said.append, path=led6, now=now + 100)
    md = open(p, encoding="utf-8").read()
    check("AL2.6c digest_write() produces ops/ACTUATOR_DIGEST.md (env-overridden here) with the ALERT and the tables, and says one summary line",
          p == os.environ["COVENANT_ACTUATOR_DIGEST"] and "ALERT" in md and "| ask gpt |" in md and "## Holds by reason" in md
          and said and said[0].startswith("actuator digest:"), said)

    # ---- AL2.7 build(): exactly GUIDE_KEYS, nonce echoed, until clamped
    rc = AG.main([flag("hold"), "operator is travelling", flag("days"), "30"])
    t0 = int(time.time())                       # the CLI stamps until from the real clock, so build() is asked with it too
    doc = AG.build(t0, "n0nce-abc")
    check("AL2.7 build() emits exactly GUIDE_KEYS; nonce echoed; hold True with its why; until clamped to issued+7d when the operator asked 30",
          rc == 0 and set(doc) == set(AG.GUIDE_KEYS) and doc["nonce"] == "n0nce-abc" and doc["hold"] is True and doc["hold_why"] == "operator is travelling"
          and doc["issued"] == t0 and doc["until"] == t0 + 7 * 86400 and AG.load_operator()["until"] > t0 + 29 * 86400, doc)

    # ---- AL2.8 FALSE PUSH: grant-like keys in the operator file
    grant_file = {"hold": True, "hold_why": "x", "until": int(now) + 3600, "run": "ask gpt", "jobs": [{"recipe": "ask gpt"}], "recipes": ["ask gpt"],
                  "unattended": True, "priors": {"ask gpt": [1, 1, 1, 1, 1]}}
    clean, refused = AG.sanitize(grant_file)
    saved = json.load(open(AG.guide_path(), encoding="utf-8"))
    AG._write_json(AG.guide_path(), grant_file)
    try:
        AG.build(now, "n")
        raised = ""
    except ValueError as e:
        raised = str(e)
    served = AG.guide_signed("n", key=key)
    AG._write_json(AG.guide_path(), saved)
    check("AL2.8 FALSE PUSH sanitize() drops run/jobs/recipes/unattended/priors and NAMES them; the clean doc is exactly GUIDE_KEYS",
          set(refused) >= {"run", "jobs", "recipes", "unattended", "priors"} and set(clean) == set(AG.GUIDE_KEYS) and clean["hold"] is True, refused)
    check("AL2.8b ...and an operator FILE carrying them makes build() raise ValueError naming them, and guide_signed() answers an error, never a signed doc",
          all(k in raised for k in ("run", "jobs", "recipes", "unattended", "priors")) and served["status"] == "error" and "doc" not in served, (raised, served))
    try:
        AG.main([flag("set"), "hold=true"])
        set_rc = 0
    except SystemExit as e:
        set_rc = e.code
    check("AL2.8c there is no --set: the parser refuses it (exit 2)", set_rc == 2, set_rc)
    c2, r2b = AG.sanitize({"hold": "yes", "max_runs_per_day": 50, "ocr_taps": "true", "deny_apps": "com.x", "note": "a\x00b" * 300})
    check("AL2.8d FALSE PUSH type smuggling: hold 'yes' -> False, cap 50 -> None, ocr_taps 'true' -> None, deny_apps str -> [], note capped and control chars gone",
          c2["hold"] is False and c2["max_runs_per_day"] is None and c2["ocr_taps"] is None and c2["deny_apps"] == [] and len(c2["note"]) == 400
          and "\x00" not in c2["note"] and set(r2b) == {"max_runs_per_day", "ocr_taps", "deny_apps"}, (c2, r2b))

    # ---- AL2.9 sign / verify
    resp = AG.sign_doc(AG.build(now, "abc123"), key)
    ok, vdoc, why = AG.verify_doc(resp, pem, "abc123")
    check("AL2.9 sign_doc() with a fresh RSA key verifies with verify_doc(): spk == pinned, PSS-SHA256 over canonical(doc), nonce bound",
          ok and vdoc == resp["doc"] and why == "ok" and set(resp) == {"status", "doc", "sig", "spk"}, why)
    ent, ewhy = entry_module()
    if ent is not None and hasattr(ent, "verify_doc"):
        try:
            eok = ent.verify_doc(resp, pem, "abc123")
            eok_bad = ent.verify_doc(dict(resp, doc=dict(resp["doc"], hold=False)), pem, "abc123")
            check("AL2.9b the phone's entry.verify_doc accepts the same document and refuses the tampered one",
                  bool(eok[0]) and not bool(eok_bad[0]), (eok, eok_bad))
        except Exception as e:                                    # noqa: BLE001
            check("AL2.9b entry.verify_doc ran without raising", False, "%s: %s" % (type(e).__name__, e))
    else:
        na("AL2.9b entry.verify_doc cross-check", ewhy or "entry.py has no verify_doc yet")

    # ---- AL2.10 refusals
    tampered = dict(resp, doc=dict(resp["doc"], hold=False))
    other = AG.sign_doc(resp["doc"], key2)
    check("AL2.10 a tampered byte, a document signed by another key, a wrong nonce, a non-success envelope -> each refused with its reason",
          AG.verify_doc(tampered, pem, "abc123")[0] is False and "signature" in AG.verify_doc(tampered, pem, "abc123")[2]
          and AG.verify_doc(other, pem, "abc123")[0] is False and "pinned" in AG.verify_doc(other, pem, "abc123")[2]
          and AG.verify_doc(resp, pem, "zzz")[0] is False and "nonce" in AG.verify_doc(resp, pem, "zzz")[2]
          and AG.verify_doc({"status": "error", "message": "x"}, pem)[0] is False
          and AG.verify_doc(dict(resp, sig="not base64!"), pem)[0] is False)

    # ---- AL2.11 CLI round trip and log lines
    n_log0 = len(open(log_path, encoding="utf-8").read().splitlines())
    steps = [([flag("release")], lambda op: op["hold"] is False and op["hold_why"] == "" and op["until"] == 0),
             ([flag("cap"), "5"], lambda op: op["max_runs_per_day"] == 5),
             ([flag("deny"), "com.example.casino"], lambda op: op["deny_apps"] == ["com.example.casino"]),
             ([flag("ocr-taps"), "off"], lambda op: op["ocr_taps"] is False),
             ([flag("note"), "PC says hello"], lambda op: op["note"] == "PC says hello"),
             ([flag("undeny"), "com.example.casino"], lambda op: op["deny_apps"] == []),
             ([flag("hold"), "night"], lambda op: op["hold"] is True and op["hold_why"] == "night" and op["until"] > time.time() + 6 * 86400)]
    all_ok, detail = True, []
    for argv, pred in steps:
        rc = AG.main(argv)
        op = AG.load_operator()
        good = rc == 0 and pred(op) and set(op) <= set(AG.OPERATOR_KEYS)
        all_ok &= good
        detail.append((argv[0], rc, good))
    check("AL2.11 --release/--cap 5/--deny/--ocr-taps off/--note/--undeny/--hold each round-trip through the operator file, which holds only operator keys",
          all_ok, detail)
    cap0 = AG.main([flag("cap"), "0"])
    cap13 = AG.main([flag("cap"), "13"])
    n_log1 = len(open(log_path, encoding="utf-8").read().splitlines())
    check("AL2.11b FALSE PUSH --cap 0 and --cap 13 are refused (exit 2) and change nothing; every accepted write left exactly one log line",
          cap0 == 2 and cap13 == 2 and AG.load_operator()["max_runs_per_day"] == 5 and n_log1 - n_log0 == len(steps), (cap0, cap13, n_log1 - n_log0))
    op_b4 = json.load(open(AG.guide_path(), encoding="utf-8"))
    junk = [AG.main([flag("deny"), ""]), AG.main([flag("deny"), "   "]), AG.main([flag("deny"), "not a package id!"]), AG.main([flag("undeny"), ""])]
    n_log2 = len(open(log_path, encoding="utf-8").read().splitlines())
    check("AL2.11c --deny ''/'   '/'not a package id!' and --undeny '' are each refused (exit 2): nothing written to the operator file, no log line",
          junk == [2, 2, 2, 2] and json.load(open(AG.guide_path(), encoding="utf-8")) == op_b4 and n_log2 == n_log1, (junk, n_log2 - n_log1))

    # ---- AL2.12 the library
    card = {"v": 1, "name": "ask gpt card", "pkg": "com.openai.chatgpt", "goal": "ask", "created": 1, "source": "phone",
            "charter": {"unattended": True}, "runs": ["x"], "last_answer": "PLANTED-ANSWER", "stats": {"runs": 9},
            "steps": [{"kind": "click", "id": "btn", "text": "New chat", "desc": "", "cls": "Button", "ordinal": 0, "slot": False, "ocr": "New chat", "scores": {"id": 1.0}},
                      {"kind": "type", "id": "box", "text": "", "desc": "", "cls": "EditText", "ordinal": 0, "slot": True, "ocr": ""},
                      {"kind": "click", "id": "", "text": "Send", "desc": "", "cls": "", "ordinal": 0, "slot": False, "ocr": "x" * 500}]}
    cpath = os.path.join(TD, "card.json")
    json.dump(card, open(cpath, "w", encoding="utf-8"))
    r = AG.library_add(cpath)
    items = AG.library_list()
    item = AG.library_item(r["sha"])
    check("AL2.12 library_add() strips charter/runs/last_answer/stats/scores/source/created, caps ocr at 120, keeps exactly CARD_KEYS/CARD_STEP_KEYS",
          r["ok"] and set(item) == set(AG.CARD_KEYS) and all(set(s) == set(AG.CARD_STEP_KEYS) for s in item["steps"])
          and {"charter", "runs", "last_answer", "stats", "source", "created"} <= set(r["stripped"]) and any("scores" in s for s in r["stripped"])
          and len(item["steps"][2]["ocr"]) == 120 and "PLANTED" not in json.dumps(item), r)
    check("AL2.12b the listing's sha == sha256(canonical(clean card)); the file is named by it; an unknown sha -> None; a bad sha shape -> None",
          len(items) == 1 and items[0]["sha"] == AG.card_sha(item) == r["sha"] and os.path.exists(os.path.join(AG.library_dir(), r["sha"] + ".json"))
          and set(items[0]) == {"sha", "name", "goal", "pkg", "steps", "curated_at"} and AG.library_item("f" * 64) is None
          and AG.library_item("../../etc") is None, items)
    refusals = {}
    for label, bad in (("x/y", dict(card, steps=[dict(card["steps"][0], x=10, y=20)])),
                       ("tap", dict(card, steps=[dict(card["steps"][0], tap=[1, 2])])),
                       ("bounds", dict(card, bounds=[0, 0, 1, 1])),
                       ("41 steps", dict(card, steps=[card["steps"][0]] * 41)),
                       ("denied pkg", dict(card, pkg="com.robinhood.android")),
                       ("pattern pkg", dict(card, pkg="com.some.tradingapp")),
                       ("bad kind", dict(card, steps=[dict(card["steps"][0], kind="swipe")])),
                       ("no steps", dict(card, steps=[]))):
        json.dump(bad, open(cpath, "w", encoding="utf-8"))
        refusals[label] = AG.library_add(cpath)
    check("AL2.12c FALSE PUSH a card with x/y, tap, bounds, 41 steps, a denied pkg, a money-pattern pkg, a swipe kind, or no steps -> refused, not stored",
          all(v["ok"] is False for v in refusals.values()) and len(AG.library_list()) == 1
          and "coordinates" in refusals["x/y"]["error"] and "denied list" in refusals["denied pkg"]["error"] and "pattern" in refusals["pattern pkg"]["error"], refusals)
    AG.main([flag("deny"), "com.example.notes"])
    json.dump(dict(card, pkg="com.example.notes"), open(cpath, "w", encoding="utf-8"))
    pc_denied = AG.library_add(cpath)
    AG.main([flag("undeny"), "com.example.notes"])
    check("AL2.12d a pkg on this PC's own deny list is refused by library_add too", pc_denied["ok"] is False and "deny list" in pc_denied["error"], pc_denied)

    # ---- AL2.13 denied_app agrees with the phone
    probe = ["com.robinhood.android", "com.coinbase.android", "org.toshi", "com.kraken.invest.app", "com.binance.dev", "io.metamask", "com.venmo",
             "com.squareup.cash", "com.android.exchange", "com.openai.chatgpt", "com.google.android.apps.bard", "com.android.chrome",
             "com.some.WALLET.app", "org.example.tradingview", "com.mybank.mobile", "com.example.notes", "com.example.brokerage", "org.mozilla.firefox",
             "com.Exchange.mail", "ai.x.grok"]
    pc = {p: AG.denied_app(p) for p in probe}
    check("AL2.13 PC denied_app(): the 17 ids, the pattern (case-insensitive: WALLET, bank, broker, trading) refuse; ALLOW_DESPITE and the AI apps pass",
          all(pc[p] for p in probe[:8]) and pc["com.android.exchange"] == "" and pc["com.openai.chatgpt"] == "" and pc["com.android.chrome"] == ""
          and pc["com.some.WALLET.app"] and pc["com.mybank.mobile"] and pc["com.example.brokerage"] and pc["org.example.tradingview"]
          and pc["com.example.notes"] == "" and pc["com.Exchange.mail"] and pc["ai.x.grok"] == "", pc)
    if ent is not None and hasattr(ent, "denied_app"):
        try:
            ph = {p: ent.denied_app(p) for p in probe}
            agree = [p for p in probe if bool(pc[p]) == bool(ph[p])]
            check("AL2.13b entry.denied_app agrees with the PC over the 20-id probe set", len(agree) == len(probe), [p for p in probe if p not in agree])
        except Exception as e:                                    # noqa: BLE001
            check("AL2.13b entry.denied_app ran without raising", False, "%s: %s" % (type(e).__name__, e))
    else:
        na("AL2.13b entry.denied_app cross-check", ewhy or "entry.py has no denied_app yet")

    # ---- AL2.14 FALSE PUSH: a type step that arrives with text to type
    r14 = AG.card_clean(dict(card, steps=[{"kind": "type", "id": "box", "text": "buy now", "desc": "", "cls": "EditText", "ordinal": 0, "slot": False, "ocr": ""}]))
    check("AL2.14 FALSE PUSH a card with {kind:type, slot:false, text:'buy now'} -> cleaned to slot:true, text '', and the text is nowhere in the card",
          r14["ok"] and r14["card"]["steps"][0]["slot"] is True and r14["card"]["steps"][0]["text"] == "" and "buy now" not in json.dumps(r14["card"])
          and any("type steps are slots" in s for s in r14["stripped"]), r14)

    # ---- AL2.15 status line
    st = AG.status()
    check("AL2.15 status() line shape for the watchdog", re.match(r"^phone brain: hold=(True|False) cap=(\d+|none) denied \+\d+ library \d+ card\(s\)$", st)
          and "cap=5" in st and "library 1 card" in st, st)
    raw_op = open(AG.guide_path(), "rb").read()
    with open(AG.guide_path(), "w", encoding="utf-8") as fh:
        fh.write("{not json")
    st_bad, rc_bad = AG.status(), AG.main([flag("show")])
    with open(AG.guide_path(), "wb") as fh:
        fh.write(raw_op)
    check("AL2.15b a corrupt (non-JSON) operator file says UNREADABLE, never REFUSED (that word means an attempted grant); status() does not raise; the CLI exits 2",
          "UNREADABLE" in st_bad and "REFUSED" not in st_bad and rc_bad == 2 and AG.status() == st, (st_bad, rc_bad))

    # ---- AL2.16 FALSE PUSH: a v2 sync smuggling commands
    led16 = os.path.join(TD, "v2_cmd.jsonl")
    b16 = v2_body(commands=["run ask gpt"], run="now", schedule={"at": 1})
    code, out = AL.record_sync(json.dumps(b16).encode(), "phone", led16, now)
    blob16 = json.dumps(rows_of(led16))
    check("AL2.16 FALSE PUSH v2 top-level commands/run/schedule keys -> dropped and counted (3); the response carries exactly its six keys; the values are nowhere",
          out["dropped_keys"] == 3 and set(out) == {"status", "v", "recorded", "kept", "held_or_refused", "dropped_keys"}
          and "run ask gpt" not in blob16 and '"now"' not in blob16 and rows_of(led16)[-1]["dropped_keys"] == 3, out)

    # ---- AL2.17 charters are recorded, read by the digest only
    g_before = AG.build(now, "same")
    led17 = os.path.join(TD, "v2_charter.jsonl")
    b17 = v2_body()
    b17["recipes"][0]["charter"].update({"unattended": True, "max_per_day": 12, "standing_slot": "PLANTED", "granted_by": "pc"})
    AL.record_sync(json.dumps(b17).encode(), "phone", led17, now)
    g_after = AG.build(now, "same")
    row17 = next(r for r in rows_of(led17) if r["kind"] == "recipe")
    d17 = AL.digest(rows_of(led17), now + 1)
    check("AL2.17 a v2 charter lands on its row with exactly LEARN_CHARTER_KEYS (no standing_slot/granted_by), the digest summarises it, and the guide the PC builds is unchanged by it",
          set(row17["charter"]) == set(AL.LEARN_CHARTER_KEYS) and "PLANTED" not in json.dumps(row17) and "UNATTENDED 12/day" in d17["recipes"]["ask gpt"]["charter"]
          and g_before == g_after, (row17["charter"], g_before == g_after))

    # ---- AL2.18 route helpers from temp files
    gs = AG.guide_signed("n1", key=key)
    ls = AG.library_signed("n2", key=key)
    its = AG.item_signed(r["sha"], "n3", key=key)
    okg, gdoc, _ = AG.verify_doc(gs, pem, "n1")
    okl, ldoc, _ = AG.verify_doc(ls, pem, "n2")
    oki, idoc, _ = AG.verify_doc(its, pem, "n3")
    check("AL2.18 guide_signed/library_signed/item_signed return the documented shapes, each verifying against its own nonce",
          okg and set(gdoc) == set(AG.GUIDE_KEYS) and okl and set(ldoc) == {"v", "nonce", "issued", "items"} and ldoc["items"][0]["sha"] == r["sha"]
          and oki and set(idoc) == {"v", "nonce", "issued", "sha256", "card"} and idoc["sha256"] == AG.card_sha(idoc["card"]) == r["sha"], (gdoc, ldoc, idoc))
    saved = json.load(open(AG.guide_path(), encoding="utf-8"))
    os.remove(AG.guide_path())
    none_guide = AG.guide_signed("n4", key=key)
    st_none = AG.status()
    AG._write_json(AG.guide_path(), saved)
    check("AL2.18b with no operator file guide_signed() is None (the route says 404) and status() still answers; an unknown sha -> item_signed() None",
          none_guide is None and st_none.startswith("phone brain: hold=False cap=none") and AG.item_signed("e" * 64, "n5", key=key) is None, (none_guide, st_none))
    check("AL2.18c library_rm() removes the card and logs it; the listing is empty after", AG.library_rm(r["sha"]) is True and AG.library_list() == [] and AG.library_rm(r["sha"]) is False)
    json.dump(card, open(cpath, "w", encoding="utf-8"))
    again = AG.library_add(cpath)
    real_load = DP.load_key

    def no_key():
        raise OSError("nodeA_prod.db.key: permission denied")           # what a corrupt or unreadable node key does

    DP.load_key = no_key                                                # patched on the module the helpers import, so _key() itself runs
    try:
        served = [AG.guide_signed("n6"), AG.library_signed("n7"), AG.item_signed(again["sha"], "n8")]
        key_raised = ""
    except Exception as e:                                              # noqa: BLE001
        served, key_raised = [], "%s: %s" % (type(e).__name__, e)
    finally:
        DP.load_key = real_load
    AG.library_rm(again["sha"])
    check("AL2.18d with the signing key unloadable, all three helpers return the contract's JSON error (no traceback, no unsigned doc); a good key still signs after",
          not key_raised and len(served) == 3 and all(x == {"status": "error", "message": "signing key unavailable"} for x in served)
          and AG.verify_doc(AG.guide_signed("n9", key=key), pem, "n9")[0], (key_raised, served))

    # ---- AL2.19 idempotence
    c1, ref1 = AG.sanitize(grant_file)
    c2, ref2 = AG.sanitize(c1)
    check("AL2.19 sanitize() is idempotent: the clean doc is a fixed point and the second pass refuses nothing", c1 == c2 and ref2 == [] and ref1, (ref1, ref2))

    # ---- AL2.21 FALSE PUSH: a type-confused body (review finding 7). One of these used to be a 500 for the WHOLE sync,
    # so every other recipe in it was lost and the phone, whose learn_state only advances on a 200, re-sent it forever.
    led21 = os.path.join(TD, "v2_types.jsonl")
    b21 = v2_body(autoruns={"nope": 1}, holds=3)
    b21["recipes"][0].update({"runs": 7, "locator_scores": 5})
    b21["chains"] = [dict(v2_body()["chains"][0], name="c-dict", hops={"a": 1}, runs="x"),
                     dict(v2_body()["chains"][0], name="c-hop", hops=[{"recipe": "ask gpt", "fallbacks": 3, "placeholders": 3}])]
    try:
        code, out = AL.record_sync(json.dumps(b21).encode(), "phone", led21, now)
        raised21 = ""
    except Exception as e:                                              # noqa: BLE001
        code, out, raised21 = 0, {}, "%s: %s" % (type(e).__name__, e)
    r21 = rows_of(led21) if os.path.exists(led21) else []
    by21 = {r.get("name"): r for r in r21 if r["kind"] in ("recipe", "chain")}
    for n in ("ask gpt", "c-dict", "c-hop"):                            # a regression that raises must FAIL these, not crash the suite
        by21.setdefault(n, {"runs": None, "locator_scores": None, "dropped_keys": None, "hops": [{"fallbacks": None, "placeholders": None}]})
    check("AL2.21 FALSE PUSH hops as a dict, runs/locator_scores/fallbacks/placeholders as ints, autoruns as a dict, holds as an int -> 200, nothing raised, every row still written",
          not raised21 and code == 200 and [r["kind"] for r in r21] == ["recipe", "chain", "chain", "brain"]
          and set(out["kept"]) == {"ask gpt", "c-dict", "c-hop"} and out["held_or_refused"] == [], (raised21, out))
    check("AL2.21b ...each type-confused field is DROPPED (empty, never the raw value) and COUNTED in dropped_keys (8: 2 per recipe/chain/hop/top-level)",
          out.get("dropped_keys") == 8 and r21 and r21[-1]["dropped_keys"] == 8 and by21["ask gpt"]["runs"] == [] and by21["ask gpt"]["locator_scores"] == []
          and by21["ask gpt"]["dropped_keys"] == 2 and by21["c-dict"]["hops"] == [] and by21["c-dict"]["runs"] == []
          and by21["c-hop"]["hops"][0]["fallbacks"] == [] and by21["c-hop"]["hops"][0]["placeholders"] == []
          and r21[-1]["counts"] == {"recipes": 1, "chains": 2, "autoruns": 0, "holds": 0}, (out, by21.get("c-hop", {}).get("hops")))

    # ---- AL2.22 an epoch no clock can render (review finding 8): clamped on arrival, and survived where it is already on disk
    led22 = os.path.join(TD, "v2_time.jsonl")
    huge = 10 ** 18
    b22 = v2_body(holds=[{"t": huge, "name": "ask gpt", "why": "spacing"}])
    b22["recipes"][0]["charter"].update({"expires_at": huge, "granted_at": -5})
    b22["recipes"][0]["stats"]["last_ok_at"] = huge
    AL.record_sync(json.dumps(b22).encode(), "phone", led22, now)
    row22 = next(r for r in rows_of(led22) if r["kind"] == "recipe")
    hold22 = next(r for r in rows_of(led22) if r["kind"] == "hold")
    with open(led22, "a", encoding="utf-8") as fh:                      # a row written BEFORE the clamp existed: the ledger is append-only
        fh.write(json.dumps(dict(row22, name="pre-clamp", charter=dict(row22["charter"], expires_at=huge))) + "\n")
    try:
        d22 = AL.digest(rows_of(led22), now)
        p22 = AL.digest_write(say=lambda s: None, path=led22, now=now)
        raised22 = ""
    except Exception as e:                                              # noqa: BLE001
        d22, p22, raised22 = {}, "", "%s: %s" % (type(e).__name__, e)
    check("AL2.22 a charter expires_at/granted_at, a stats last_ok_at and a hold t outside [0, now+400d] are clamped to 0 on arrival; the row is still recorded",
          row22["charter"]["expires_at"] == 0 and row22["charter"]["granted_at"] == 0 and row22["stats"]["last_ok_at"] == 0
          and hold22["hold"]["t"] == 0 and row22["clean"] is True, (row22["charter"], hold22["hold"]))
    check("AL2.22b ...and a row already on disk carrying the raw huge epoch no longer kills the nightly digest: digest()/digest_write() run and print the integer",
          not raised22 and str(huge) in d22["recipes"]["pre-clamp"]["charter"] and ("exp " + AL._fmt_day(0)) in d22["recipes"]["ask gpt"]["charter"]
          and p22 == os.environ["COVENANT_ACTUATOR_DIGEST"] and "| pre-clamp |" in open(p22, encoding="utf-8").read(), raised22)

    # ---- AL2.20 only temp dirs were touched
    after = snapshot(REAL)
    check("AL2.20 the suite read and wrote only its temp dirs: the real ops/ actuator files are exactly as they were, and every module path points into the temp dir",
          before == after and all(p.startswith(TD) for p in (AG.guide_path(), AG.library_dir(), AG.log_path())), (before, after))

    n, good = len(results), sum(results)
    print("AL2: %d/%d passed" % (good, n))
    return 0 if good == n else 1


if __name__ == "__main__":
    try:
        rc = main()
    finally:
        import shutil
        shutil.rmtree(TD, ignore_errors=True)
    sys.exit(rc)
