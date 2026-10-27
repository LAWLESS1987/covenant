#!/usr/bin/env python3
"""covenant_actuator_learn.py -- what the phone's on-device "brain" (the
Accessibility actuator, phases 2 and 3: CovenantActuator.java, Recipe.java,
Chain.java, Brain.java in the private app repo) has learned, synced back to
this PC.

The operator's ask, 2026-09-14: "the phone app should send back info to learn
from and learn itself." The phone already keeps everything locally
(files/recipes/*.json, files/chains/*.json, files/brain/*.jsonl); nothing
about that changes -- this just gives the PC its own copy, the same way
daily_plan and phone_checkins already do, so the record survives a lost phone
and the nightly digest (digest_write, ops/ACTUATOR_DIGEST.md) can show what
every recipe, chain and app has learned without touching the device.

WHAT ARRIVES. v1 (phase 2): one recipe's summary per sync -- name, app,
step count, run lines, `last_answer`. v2 (phase 3, body {"v":2,...}): the
same for every recipe and chain, plus the brain's own content-free rows --
autonomous run attempts (codes only), holds and refusals by reason, the
caps in force -- each field copied through an ALLOWLIST (LEARN_*_KEYS below,
the same tuples entry.learn_payload builds from) with its type coerced and
its length capped. A key that is not on the list is dropped and COUNTED
(`dropped_keys`, in the response and on every row), never stored: the phone
is a different trust boundary, and a payload that grows keys is the thing
to notice, not to keep. Run lines are re-scrubbed here to "date time
OUTCOME code (N s)" even though the phone already did it -- a label a
person clicked is not ours to hold.

`last_answer` -- what a recipe read back from the screen -- is the actual
"info to learn from": an AI app's answer, a confirmation, whatever the
green-lit app showed. It goes through judge_learned_text() before it is
kept, for the same reason covenant_moltbook judges what arrives from outside
this machine: a payload from a different trust boundary should not be
trusted just because the channel authenticated the SENDER. Phase 3 adds a
NOT-TEXT refusal ahead of the secret scan: a data: URI or a long run of
base64/hex without whitespace is an image or a blob, and the phone must never
send one (SPEC invariant 3) -- it is HELD with the answer withheld and only
its sha kept, so the digest can show that it happened.

THE LEDGER. ops/actuator_learning.jsonl (gitignored), append-only. v2 writes
one row per recipe (kind "recipe"), per chain ("chain"), per autonomous run
("autorun"), per hold ("hold"), and one "brain" row per sync with the caps
and counts. A row that failed judging is recorded too -- as a HELD or
REFUSED row with the reason, never silently dropped -- so a HELD/REFUSED sync
is visible the same way a refused sealed-mail block is. Charter fields are
recorded and read by the digest only: no function here changes anything on
the strength of them (the PC's whole say is covenant_actuator_guide.py).

Run:
  python covenant_actuator_learn.py --log [N]     the last N synced rows (default 20)
  python covenant_actuator_learn.py --digest      write ops/ACTUATOR_DIGEST.md and print its summary
  python covenant_actuator_learn.py --explain      this, in the module's words
"""
import hashlib
import io
import json
import os
import re
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER = os.environ.get("COVENANT_ACTUATOR_LEDGER") or os.path.join(HERE, "ops", "actuator_learning.jsonl")
MAX_ANSWER_CHARS = 6000           # matches the phone's own cap; nothing bigger is trusted regardless
MAX_RUNS_KEPT = 40                # matches Recipe.save()'s own cap

# ---- constants: pasted VERBATIM from the pinned CONSTANTS.py (phase 3) ----------------------------
LIMITS = {"max_hops": 5, "max_fallbacks": 2, "max_per_day_ceiling": 12, "ai_per_day": 3,
          "min_spacing_min": 5, "chain_wall_s": 600, "global_daily_default": 12, "charter_days": 30,
          "guidance_max_days": 7, "answer_cap": 6000, "slot_cap": 4000, "chain_attended_ok_required": 3,
          "autoruns_keep": 500, "holds_keep": 200, "card_max_steps": 40, "card_str_cap": 400,
          "ocr_label_cap": 120, "template_cap": 400, "learn_recipes_max": 50, "learn_chains_max": 20,
          "learn_autoruns_max": 50, "learn_holds_max": 30, "runs_keep": 40, "hold_why_cap": 200,
          "note_cap": 400, "deny_apps_max": 50, "nonce_hex_len": 32}

# What leaves the phone in one learning sync (POST /actuator_learn, body v2) -- built by
# entry.learn_payload by COPYING NAMED KEYS ONLY; kept by the PC by the same allowlists.
LEARN_TOP_KEYS = ("v", "node_id", "app", "when", "caps", "brain", "recipes", "chains", "autoruns", "holds", "guidance_seen")
LEARN_CAPS_KEYS = ("ocr", "gestures")
LEARN_BRAIN_KEYS = ("owner_hold", "pc_hold", "global_cap", "starts_today", "omitted", "attempted_grants")
LEARN_RECIPE_KEYS = ("name", "pkg", "goal", "source", "steps", "slots", "ocr_steps", "runs", "stats", "reliability",
                     "locator_scores", "charter", "last_answer", "last_answer_sha256", "last_answer_chars",
                     "answer_source", "withheld")
LEARN_CHAIN_KEYS = ("name", "goal", "hops", "runs", "stats", "reliability", "charter", "attended_ok",
                    "last_answer", "last_answer_sha256", "last_answer_chars", "withheld")
LEARN_STATS_KEYS = ("runs", "ok", "fail", "ocr_used", "ocr_hits", "taps", "autonomous", "gate_refused", "last_ok_at")
LEARN_RELIABILITY_KEYS = ("ok", "n", "last20_ok")
LEARN_CHARTER_KEYS = ("unattended", "max_per_day", "hours_from", "hours_to", "spacing_min", "trigger", "granted_at",
                      "expires_at", "quarantined", "ocr_taps", "may_send_unattended")
LEARN_HOP_KEYS = ("recipe", "fallbacks", "placeholders")
LEARN_AUTORUN_KEYS = ("t", "day", "kind", "name", "pkg", "trigger", "result", "ok", "hops", "ms")
LEARN_HOLD_KEYS = ("t", "name", "why")
LEARN_GUIDANCE_SEEN_KEYS = ("issued", "sha256")

# Content-free outcome codes: the only thing an autoruns/holds row or a scrubbed run line carries.
RESULT_CODES = ("done", "step-never-appeared", "step-failed", "timeout", "refused", "aborted", "interrupted",
                "gate_refused", "gate_held", "launch-refused", "chain-wall-clock", "other")
TRIGGERS = ("owner", "schedule", "chain")
CHARTER_TRIGGERS = ("schedule", "chain-only", "manual")
# ---- end of the pasted block -----------------------------------------------------------------------

_NOT_TEXT_RUN = re.compile(r"[A-Za-z0-9+/=]{512,}")      # base64 (hex is a subset): an image or a blob, never an answer
_B64_TOKEN = re.compile(r"^[A-Za-z0-9+/=]+$")            # ONE line of a wrapped one
WRAP_MIN_TOKEN = 20                                      # a MIME/PEM wrap is 64 or 76 columns wide; a word is not
_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")
_RUN_TS = re.compile(r"(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2})")
_RUN_DUR = re.compile(r"\((\d+(?:\.\d+)?)\s*s\)")
_RUN_STEP = re.compile(r"step[- ]?\d*[- ]?(never[- ]appeared|failed)", re.I)
_RUN_OUTCOMES = ("ok", "fail", "held", "refused", "error", "aborted", "timeout", "interrupted", "other")


def _sha(text):
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def _wrapped_run(t):
    """The longest run of base64/hex measured ACROSS whitespace, counting only
    tokens that are entirely base64 characters and at least WRAP_MIN_TOKEN
    long. Deleting every space instead would join ordinary words into a
    512-character "run" and hold genuine prose: "the quick brown fox " * 300
    (AL2.3c) is 4800 letters once the spaces go. A wrapped blob is long
    unbroken tokens; prose is words -- that is the difference measured here."""
    best = run = 0
    for tok in str(t or "").split():
        if len(tok) >= WRAP_MIN_TOKEN and _B64_TOKEN.match(tok):
            run += len(tok)
            best = max(best, run)
        else:
            run = 0
    return best


def not_text(text):
    """The reason a read-back is not prose (an image or a blob), or ''.

    2026-09-14 (review finding 9): the first version measured only a
    CONTIGUOUS run and only read the first ten characters for "data:image",
    so a 6 KB image wrapped at 76 columns the way MIME and PEM wrap one, and
    a data: URI with anything at all in front of it, both judged clean and
    were kept as learned answers. The marker is now looked for anywhere in
    the text, and the run is measured across the wrap (_wrapped_run)."""
    t = text or ""
    low = t.lower()
    if "data:image" in low:
        return "a data:image URI"
    if ";base64," in low:
        return "a ;base64, marker"
    m = _NOT_TEXT_RUN.search(t)
    if m:
        return "a %d-character run of base64/hex without whitespace" % len(m.group(0))
    n = _wrapped_run(t)
    if n >= 512:
        return "a %d-character run of base64/hex wrapped across lines" % n
    return ""


def judge_learned_text(text):
    """(clean, reasons) for one recipe's last_answer -- first the NOT-TEXT
    refusal (a screenshot or a blob is never a learned answer: HELD, the
    text withheld, its sha kept by the caller), then the same secret/leak
    patterns covenant_ai_consult checks for the opposite direction (outbound
    to another AI app); the risk here is symmetric: a screen the phone read
    could just as easily have shown a key or a token as an AI app's answer.

    Deliberately NOT covenant_ai_consult._deterministic_check(): that
    function's length cap (MAX_QUESTION_CHARS, 2000) exists because an
    outbound QUESTION that long is itself suspicious -- a giant paste, not a
    question. A read-back ANSWER is expected to run longer (up to the
    phone's own 6000-char cap on Recipe.lastAnswer) and is not the thing
    being judged as a question, so the secret-pattern scan here runs over
    the FULL text, not a truncated head -- a first version of this function
    scanned only the first 2000 chars and a secret placed later slipped
    through untested until AL1.9 caught it. The theft/deception semantic
    quorum is asked over a bounded excerpt and logged as advisory, for the
    same measured reason as covenant_ai_consult.py (2026-09-14: that quorum
    has no useful opinion on ordinary text of this kind); it does not get a
    vote here either."""
    t = text or ""
    why = not_text(t)
    if why:
        return False, ["HELD: not text -- %s (%d chars); the answer is withheld, its sha kept" % (why, len(t))]
    import covenant_ai_consult as AC
    hits = [p.pattern for p in AC._SECRET_PATTERNS if p.search(t)]
    if hits:
        reasons = ["refused: matches a secret/internal-data pattern (%d pattern(s), not shown), scanned all %d chars" % (len(hits), len(t))]
        clean = False
    else:
        reasons = ["deterministic check: clean (no secret pattern, all %d chars scanned)" % len(t)]
        clean = True
    reasons.append(AC._quorum_opinion(t[:2000]))
    return clean, reasons


def record_sync(body_bytes, who, path=None, now=None):
    """One phone's learning sync. v1: {recipes: [{name, pkg, steps, slots, runs,
    last_answer}, ...]}. v2: {"v":2, ...} per the module docstring. Returns
    (http_status, payload) in this project's usual route shape. Every recipe
    in the body gets its own ledger row, judged independently -- one bad
    recipe does not sink the others."""
    try:
        data = json.loads(body_bytes.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return 400, {"status": "error", "message": "body is not JSON"}
    if isinstance(data, dict) and data.get("v") == 2:
        return _record_v2(data, who, path, now)
    if not isinstance(data, dict) or not isinstance(data.get("recipes"), list):
        return 400, {"status": "error", "message": "body must be {\"recipes\": [...]}"}
    path = path or LEDGER
    os.makedirs(os.path.dirname(path), exist_ok=True)
    kept, held_or_refused = [], []
    with open(path, "a", encoding="utf-8") as fh:
        for r in data["recipes"]:
            if not isinstance(r, dict) or not str(r.get("name", "")).strip():
                continue
            name = str(r.get("name", ""))[:200]
            pkg = str(r.get("pkg", ""))[:200]
            answer = str(r.get("last_answer", "") or "")[:MAX_ANSWER_CHARS]
            raw_runs = r.get("runs")                     # the same type guard as v2 (finding 7): not a list -> no runs, no 500
            runs = [str(x)[:200] for x in (raw_runs if isinstance(raw_runs, list) else [])][-MAX_RUNS_KEPT:]
            clean, reasons = judge_learned_text(answer) if answer else (True, ["no last_answer to judge"])
            row = {
                "t": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(now)),
                "at": round(now if now is not None else time.time(), 1),
                "signer": who,
                "recipe": name,
                "pkg": pkg,
                "steps": int(r.get("steps") or 0),
                "slots": int(r.get("slots") or 0),
                "runs": runs,
                "clean": bool(clean),
                "reasons": reasons,
                "last_answer": answer if clean else None,
                "last_answer_sha256": _sha(answer) if answer else None,
                "last_answer_chars": len(answer),
            }
            fh.write(json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")
            (kept if clean else held_or_refused).append(name)
    return 200, {"status": "success", "recorded": len(kept) + len(held_or_refused),
                "kept": kept, "held_or_refused": held_or_refused}


# ---------------------------------------------------------------- v2: allowlists, coercion, one row per thing

def _s(x, cap):
    return _CTRL.sub("", str(x if x is not None else ""))[:cap]


def _i(x, default=0):
    try:
        return int(x)
    except (TypeError, ValueError):
        return default


def _f(x):
    try:
        v = float(x)
        return v if v == v else 0.0
    except (TypeError, ValueError):
        return 0.0


def _b(x):
    return x is True or x == 1


def _hex(x):
    return str(x).lower() if isinstance(x, str) and _HEX64.match(x) else None


def _pick(src, keys, counter):
    """The allowlisted keys of a dict; every other key adds one to counter[0]."""
    if not isinstance(src, dict):
        return {}
    counter[0] += sum(1 for k in src if k not in keys)
    return {k: src[k] for k in keys if k in src}


def _list(src, key, counter):
    """The list under `key`, or [] -- a field that arrives as a dict, an int or a
    string is DROPPED and COUNTED exactly like an unknown key, never iterated.

    2026-09-14 (review finding 7): every list-typed v2 field was read as
    `(p.get(k) or [])`, so `hops` sent as a dict raised KeyError out of the
    slice and `runs`/`locator_scores`/`fallbacks`/`placeholders` sent as an
    int raised TypeError out of the comprehension. One type-confused body
    therefore answered 500 and sank every OTHER recipe in the same sync --
    against this module's own rule -- and the phone, whose learn_state only
    advances on a 200, would re-send that same body every cycle forever."""
    v = src.get(key) if isinstance(src, dict) else None
    if isinstance(v, list):
        return v
    if v is not None:
        counter[0] += 1
    return []


EPOCH_MAX_AHEAD = 400 * 86400     # a phone clock can be wrong by a lot; more than this is not a time


def _epoch(x, now=None):
    """An epoch second from the phone, clamped to [0, now + 400 days] or 0.

    2026-09-14 (review finding 8): expires_at was stored as whatever integer
    arrived, and one row carrying 10**18 made time.localtime() raise OSError
    inside the digest -- which, the ledger being append-only, stopped
    ops/ACTUATOR_DIGEST.md updating every night thereafter with no way to
    self-heal. Clamped on arrival here; _fmt_day() covers the rows already
    written."""
    t = _i(x)
    ceiling = (time.time() if now is None else now) + EPOCH_MAX_AHEAD
    return t if 0 <= t <= ceiling else 0


def runs_scrub(line):
    """'date time OUTCOME code (N s)' rebuilt from parts -- whatever else the
    line carried (a clicked label, a typed word) is not copied."""
    s = str(line or "")
    m = _RUN_TS.search(s)
    date, tm = (m.group(1), m.group(2)) if m else ("0000-00-00", "00:00")
    mo = re.match(r"\s*([A-Za-z_-]+)", s[m.end():] if m else s)
    outcome = (mo.group(1).lower() if mo else "other")
    outcome = {"failed": "fail"}.get(outcome, outcome)
    if outcome not in _RUN_OUTCOMES:
        outcome = "other"
    low = s.lower()
    ms = _RUN_STEP.search(low)
    if ms:
        code = "step-never-appeared" if "never" in ms.group(1) else "step-failed"
    else:
        code = "other"
        for c in sorted(RESULT_CODES, key=len, reverse=True):
            if re.search(r"(?<![A-Za-z0-9_-])%s(?![A-Za-z0-9_-])" % re.escape(c), low):
                code = c
                break
    md = _RUN_DUR.search(s)
    return "%s %s %s %s (%d s)" % (date, tm, outcome.upper(), code, int(float(md.group(1))) if md else 0)


def _stats(x, counter, now=None):
    p = _pick(x, LEARN_STATS_KEYS, counter)
    out = {k: _i(p.get(k)) for k in LEARN_STATS_KEYS}
    out["last_ok_at"] = _epoch(p.get("last_ok_at"), now)          # a timestamp: clamped like every other one
    return out


def _reliability(x, counter):
    p = _pick(x, LEARN_RELIABILITY_KEYS, counter)
    return {k: _i(p.get(k)) for k in LEARN_RELIABILITY_KEYS}


def _charter(x, counter, now=None):
    if x is None:
        return None
    p = _pick(x, LEARN_CHARTER_KEYS, counter)
    trig = _s(p.get("trigger"), 20)
    return {"unattended": _b(p.get("unattended")), "max_per_day": _i(p.get("max_per_day")),
            "hours_from": _i(p.get("hours_from")), "hours_to": _i(p.get("hours_to")), "spacing_min": _i(p.get("spacing_min")),
            "trigger": trig if trig in CHARTER_TRIGGERS else "other", "granted_at": _epoch(p.get("granted_at"), now),
            "expires_at": _epoch(p.get("expires_at"), now), "quarantined": _b(p.get("quarantined")),
            "ocr_taps": _b(p.get("ocr_taps")), "may_send_unattended": _b(p.get("may_send_unattended"))}


def _answer_fields(p, name):
    """The judged read-back: (clean, reasons, stored text or None, sha, chars, withheld)."""
    answer = _s(p.get("last_answer"), MAX_ANSWER_CHARS)
    withheld = _b(p.get("withheld"))
    if answer:
        clean, reasons = judge_learned_text(answer)
    else:
        clean, reasons = True, ["answer withheld on the phone (sync_answer off or leak_check hit)" if withheld else "no last_answer to judge"]
    sha = _sha(answer) if answer else _hex(p.get("last_answer_sha256"))
    return clean, reasons, (answer if clean else None), sha, (len(answer) if answer else _i(p.get("last_answer_chars"))), withheld


def _base(kind, who, now, node_id, app):
    return {"t": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(now)),
            "at": round(now if now is not None else time.time(), 1), "signer": who, "v": 2, "kind": kind,
            "node_id": node_id, "app": app}


def _record_v2(data, who, path, now):
    path = path or LEDGER
    os.makedirs(os.path.dirname(path), exist_ok=True)
    total = [0]
    top = _pick(data, LEARN_TOP_KEYS, total)
    node_id, app = _s(top.get("node_id"), 80), _s(top.get("app"), 80)
    kept, held_or_refused, rows = [], [], []

    for r in _list(top, "recipes", total)[:LIMITS["learn_recipes_max"]]:
        if not isinstance(r, dict) or not str(r.get("name", "")).strip():
            continue
        c = [0]
        p = _pick(r, LEARN_RECIPE_KEYS, c)
        name = _s(p.get("name"), 200)
        clean, reasons, text, sha, chars, withheld = _answer_fields(p, name)
        src = _s(p.get("answer_source"), 8)
        scores = [[_f(v) for v in (ls + [0] * 5)[:5]] for ls in _list(p, "locator_scores", c) if isinstance(ls, list)][:LIMITS["card_max_steps"]]
        row = dict(_base("recipe", who, now, node_id, app), name=name, pkg=_s(p.get("pkg"), 200), goal=_s(p.get("goal"), 60),
                   source=_s(p.get("source"), 40) or "phone", steps=_i(p.get("steps")), slots=_i(p.get("slots")), ocr_steps=_i(p.get("ocr_steps")),
                   runs=[runs_scrub(x) for x in _list(p, "runs", c) if isinstance(x, (str, int, float))][-MAX_RUNS_KEPT:],
                   stats=_stats(p.get("stats"), c, now), reliability=_reliability(p.get("reliability"), c), locator_scores=scores,
                   charter=_charter(p.get("charter"), c, now), clean=bool(clean), reasons=reasons, last_answer=text, last_answer_sha256=sha,
                   phone_sha256=_hex(p.get("last_answer_sha256")), last_answer_chars=chars,
                   answer_source=src if src in ("tree", "ocr", "both", "") else "", withheld=withheld, dropped_keys=c[0])
        rows.append(row)
        (kept if clean else held_or_refused).append(name)
        total[0] += c[0]

    for ch in _list(top, "chains", total)[:LIMITS["learn_chains_max"]]:
        if not isinstance(ch, dict) or not str(ch.get("name", "")).strip():
            continue
        c = [0]
        p = _pick(ch, LEARN_CHAIN_KEYS, c)
        name = _s(p.get("name"), 200)
        clean, reasons, text, sha, chars, withheld = _answer_fields(p, name)
        hops = []
        for h in _list(p, "hops", c)[:LIMITS["max_hops"]]:
            hp = _pick(h, LEARN_HOP_KEYS, c)
            hops.append({"recipe": _s(hp.get("recipe"), 200),
                         "fallbacks": [_s(x, 200) for x in _list(hp, "fallbacks", c) if isinstance(x, str)][:LIMITS["max_fallbacks"]],
                         "placeholders": [_s(x, 40) for x in _list(hp, "placeholders", c) if isinstance(x, str)][:10]})
        row = dict(_base("chain", who, now, node_id, app), name=name, goal=_s(p.get("goal"), 60), hops=hops,
                   runs=[runs_scrub(x) for x in _list(p, "runs", c) if isinstance(x, (str, int, float))][-MAX_RUNS_KEPT:],
                   stats=_stats(p.get("stats"), c, now), reliability=_reliability(p.get("reliability"), c), charter=_charter(p.get("charter"), c, now),
                   attended_ok=_i(p.get("attended_ok")), clean=bool(clean), reasons=reasons, last_answer=text, last_answer_sha256=sha,
                   phone_sha256=_hex(p.get("last_answer_sha256")), last_answer_chars=chars, withheld=withheld, dropped_keys=c[0])
        rows.append(row)
        (kept if clean else held_or_refused).append(name)
        total[0] += c[0]

    for a in _list(top, "autoruns", total)[:LIMITS["learn_autoruns_max"]]:
        if not isinstance(a, dict):
            continue
        c = [0]
        p = _pick(a, LEARN_AUTORUN_KEYS, c)
        k, trig, res = _s(p.get("kind"), 10), _s(p.get("trigger"), 10), _s(p.get("result"), 40)
        run = {"t": _epoch(p.get("t"), now), "day": _s(p.get("day"), 10), "kind": k if k in ("recipe", "chain", "hop") else "other",
               "name": _s(p.get("name"), 200), "pkg": _s(p.get("pkg"), 200), "trigger": trig if trig in TRIGGERS else "other",
               "result": res if res in RESULT_CODES else "other", "ok": _b(p.get("ok")), "hops": _i(p.get("hops")), "ms": _i(p.get("ms"))}
        rows.append(dict(_base("autorun", who, now, node_id, app), autorun=run, dropped_keys=c[0]))
        total[0] += c[0]

    for h in _list(top, "holds", total)[:LIMITS["learn_holds_max"]]:
        if not isinstance(h, dict):
            continue
        c = [0]
        p = _pick(h, LEARN_HOLD_KEYS, c)
        hold = {"t": _epoch(p.get("t"), now), "name": _s(p.get("name"), 200), "why": _s(p.get("why"), 80)}
        rows.append(dict(_base("hold", who, now, node_id, app), hold=hold, dropped_keys=c[0]))
        total[0] += c[0]

    c = [0]
    caps = _pick(top.get("caps"), LEARN_CAPS_KEYS, c)
    brain = _pick(top.get("brain"), LEARN_BRAIN_KEYS, c)
    seen = _pick(top.get("guidance_seen"), LEARN_GUIDANCE_SEEN_KEYS, c)
    total[0] += c[0]
    n_rec = sum(1 for r in rows if r["kind"] == "recipe")
    n_ch = sum(1 for r in rows if r["kind"] == "chain")
    rows.append(dict(_base("brain", who, now, node_id, app), when=_epoch(top.get("when"), now),
                     caps={"ocr": _b(caps.get("ocr")), "gestures": _b(caps.get("gestures"))},
                     brain={"owner_hold": _b(brain.get("owner_hold")), "pc_hold": _b(brain.get("pc_hold")), "global_cap": _i(brain.get("global_cap")),
                            "starts_today": _i(brain.get("starts_today")), "omitted": _i(brain.get("omitted")),
                            "attempted_grants": _i(brain.get("attempted_grants"))},
                     guidance_seen={"issued": _epoch(seen.get("issued"), now), "sha256": _hex(seen.get("sha256")) or ""},
                     counts={"recipes": n_rec, "chains": n_ch, "autoruns": sum(1 for r in rows if r["kind"] == "autorun"),
                             "holds": sum(1 for r in rows if r["kind"] == "hold")},
                     dropped_keys=total[0]))

    with open(path, "a", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")
    return 200, {"status": "success", "v": 2, "recorded": len(rows), "kept": kept,
                 "held_or_refused": held_or_refused, "dropped_keys": total[0]}


def last_rows(path=None):
    out = []
    try:
        with open(path or LEDGER, encoding="utf-8") as fh:
            for line in fh:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        pass
    return out


# ---------------------------------------------------------------- the digest: numbers, read by the nightly

def _fmt_day(t):
    """A date for the digest, or the raw integer when the clock cannot render it.

    2026-09-14 (review finding 8): epochs are clamped on arrival now, but the
    ledger is append-only -- a row written before that clamp existed still
    carries whatever the phone sent, and one time.localtime() raising OSError
    here stopped the whole nightly digest, permanently and unrecoverably. The
    number is shown instead: a strange date in one cell, not a dead file."""
    try:
        return time.strftime("%Y-%m-%d", time.localtime(t or 0))
    except (OSError, OverflowError, ValueError):
        return str(t)


def _charter_summary(ch):
    if not ch:
        return "none"
    return "%s %d/day %02d-%02d spacing %dm %s exp %s%s" % (
        "UNATTENDED" if ch.get("unattended") else "attended", _i(ch.get("max_per_day")), _i(ch.get("hours_from")), _i(ch.get("hours_to")),
        _i(ch.get("spacing_min")), ch.get("trigger", ""), _fmt_day(_i(ch.get("expires_at"))),
        " QUARANTINED" if ch.get("quarantined") else "")


def _share(hits, used):
    return round(hits / used, 2) if used else None


def digest(rows, now):
    """Everything the ledger says, as numbers: the latest row per recipe and
    chain, apps aggregated, holds by reason, autonomous runs deduped (the
    phone re-sends its tails), the brain's last state, and an ALERT line
    whenever the phone counted an attempted grant in PC guidance."""
    d = {"generated": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(now)), "rows": len(rows), "v1_rows": 0, "v2_rows": 0,
         "syncs": 0, "last_sync_at": None, "last_sync_age_s": None, "recipes": {}, "chains": {}, "apps": {}, "holds": {},
         "autoruns": {"n": 0, "ok": 0, "by_result": {}, "by_trigger": {}}, "attempted_grants": 0, "brain": None, "caps": None,
         "dropped_keys": 0, "alerts": []}
    seen_auto, seen_hold = set(), set()
    for r in rows:
        if not isinstance(r, dict):
            continue
        kind = r.get("kind") or ("recipe" if "recipe" in r else None)
        d["v2_rows" if r.get("v") == 2 else "v1_rows"] += 1
        if kind == "brain":
            d["dropped_keys"] += _i(r.get("dropped_keys"))     # the sync's total; the other rows carry their own share of it
        at = _f(r.get("at"))
        if kind == "recipe":
            name = r.get("name") or r.get("recipe") or ""
            st, rel, ch = r.get("stats") or {}, r.get("reliability") or {}, r.get("charter")
            d["recipes"][name] = {
                "pkg": r.get("pkg", ""), "source": r.get("source", "phone"),
                "reliability": ("%d/%d" % (_i(rel.get("ok")), _i(rel.get("n")))) if rel else None, "last20_ok": _i(rel.get("last20_ok")) if rel else None,
                "runs": _i(st.get("runs")) if st else len(r.get("runs") or []), "ok": _i(st.get("ok")) if st else None, "fail": _i(st.get("fail")) if st else None,
                "autonomous": _i(st.get("autonomous")), "gate_refused": _i(st.get("gate_refused")),
                "ocr_share": _share(_i(st.get("ocr_hits")), _i(st.get("ocr_used"))), "ocr_used": _i(st.get("ocr_used")), "ocr_hits": _i(st.get("ocr_hits")),
                "charter": _charter_summary(ch), "quarantined": bool(ch and ch.get("quarantined")),
                "answer": "held/refused" if r.get("clean") is False else ("withheld" if r.get("withheld") else ("kept" if r.get("last_answer") else "none")),
                "last_sync_at": at, "last_sync_age_s": max(0, int(now - at)) if at else None}
        elif kind == "chain":
            st, rel, ch = r.get("stats") or {}, r.get("reliability") or {}, r.get("charter")
            d["chains"][r.get("name", "")] = {
                "goal": r.get("goal", ""), "hops": len(r.get("hops") or []), "attended_ok": _i(r.get("attended_ok")),
                "reliability": ("%d/%d" % (_i(rel.get("ok")), _i(rel.get("n")))) if rel else None, "runs": _i(st.get("runs")),
                "autonomous": _i(st.get("autonomous")), "charter": _charter_summary(ch), "quarantined": bool(ch and ch.get("quarantined")),
                "answer": "held/refused" if r.get("clean") is False else ("withheld" if r.get("withheld") else ("kept" if r.get("last_answer") else "none")),
                "last_sync_age_s": max(0, int(now - at)) if at else None}
        elif kind == "autorun":
            a = r.get("autorun") or {}
            key = (a.get("t"), a.get("name"), a.get("kind"), a.get("result"))
            if key in seen_auto:
                continue
            seen_auto.add(key)
            au = d["autoruns"]
            au["n"] += 1
            au["ok"] += 1 if a.get("ok") else 0
            au["by_result"][a.get("result", "other")] = au["by_result"].get(a.get("result", "other"), 0) + 1
            au["by_trigger"][a.get("trigger", "other")] = au["by_trigger"].get(a.get("trigger", "other"), 0) + 1
        elif kind == "hold":
            h = r.get("hold") or {}
            key = (h.get("t"), h.get("name"), h.get("why"))
            if key in seen_hold:
                continue
            seen_hold.add(key)
            why = str(h.get("why", ""))
            d["holds"][why] = d["holds"].get(why, 0) + 1
            if why.startswith("pc_attempted_grant:"):
                d["attempted_grants"] = max(d["attempted_grants"], _i(why.split(":", 1)[1]))
        elif kind == "brain":
            d["syncs"] += 1
            if at and (d["last_sync_at"] is None or at >= d["last_sync_at"]):
                d["last_sync_at"], d["brain"], d["caps"] = at, r.get("brain"), r.get("caps")
            d["attempted_grants"] = max(d["attempted_grants"], _i((r.get("brain") or {}).get("attempted_grants")))
    if d["last_sync_at"]:
        d["last_sync_age_s"] = max(0, int(now - d["last_sync_at"]))
    for name, rec in d["recipes"].items():
        a = d["apps"].setdefault(rec["pkg"] or "(none)", {"recipes": 0, "runs": 0, "ok": 0, "ocr_used": 0, "ocr_hits": 0, "ocr_share": None})
        a["recipes"] += 1
        a["runs"] += rec["runs"] or 0
        a["ok"] += rec["ok"] or 0
        a["ocr_used"] += rec["ocr_used"]
        a["ocr_hits"] += rec["ocr_hits"]
        a["ocr_share"] = _share(a["ocr_hits"], a["ocr_used"])
    if d["attempted_grants"] > 0:
        d["alerts"].append("ALERT: the phone counted %d attempted grant(s) in PC guidance -- this PC may only hold, cap, deny and switch taps off; "
                           "read ops/actuator_guide.json and ops/actuator_guide.log" % d["attempted_grants"])
    q = sorted(n for n, x in list(d["recipes"].items()) + list(d["chains"].items()) if x["quarantined"])
    if q:
        d["alerts"].append("quarantined on the phone (autonomy off until re-granted there): %s" % ", ".join(q))
    held = sorted(n for n, x in list(d["recipes"].items()) + list(d["chains"].items()) if x["answer"] == "held/refused")
    if held:
        d["alerts"].append("read-back HELD/REFUSED by the judge (answer withheld, sha kept): %s" % ", ".join(held))
    return d


def _age(s):
    if s is None:
        return "never"
    return "%dm" % (s // 60) if s < 7200 else ("%dh" % (s // 3600) if s < 172800 else "%dd" % (s // 86400))


def digest_markdown(d):
    L = ["# Actuator digest -- what the phone's brain has learned", "",
         "generated %s; ledger rows %d (v1 %d, v2 %d); syncs %d; last sync %s ago; keys dropped on arrival %d"
         % (d["generated"], d["rows"], d["v1_rows"], d["v2_rows"], d["syncs"], _age(d["last_sync_age_s"]), d["dropped_keys"]), ""]
    if d["brain"]:
        b = d["brain"]
        L += ["brain: owner_hold=%s pc_hold=%s global_cap=%s starts_today=%s omitted=%s attempted_grants=%s; caps %s"
              % (b.get("owner_hold"), b.get("pc_hold"), b.get("global_cap"), b.get("starts_today"), b.get("omitted"), b.get("attempted_grants"),
                 json.dumps(d["caps"] or {}, sort_keys=True)), ""]
    L += ["## Alerts", ""] + (["- " + a for a in d["alerts"]] or ["- none"]) + [""]
    L += ["## Recipes", "", "| recipe | app | reliability | runs | autonomous | gate refused | ocr share | charter | answer | last sync |", "|---|---|---|---|---|---|---|---|---|---|"]
    for n, r in sorted(d["recipes"].items()):
        L.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (n, r["pkg"], r["reliability"] or "-", r["runs"], r["autonomous"], r["gate_refused"],
                                                                     "-" if r["ocr_share"] is None else r["ocr_share"], r["charter"], r["answer"], _age(r["last_sync_age_s"])))
    if not d["recipes"]:
        L.append("| (none yet) | | | | | | | | | |")
    L += ["", "## Apps", "", "| app | recipes | runs | ok | ocr share |", "|---|---|---|---|---|"]
    for p, a in sorted(d["apps"].items()):
        L.append("| %s | %d | %d | %d | %s |" % (p, a["recipes"], a["runs"], a["ok"], "-" if a["ocr_share"] is None else a["ocr_share"]))
    L += ["", "## Chains", "", "| chain | hops | attended ok | reliability | autonomous | charter | answer |", "|---|---|---|---|---|---|---|"]
    for n, c in sorted(d["chains"].items()):
        L.append("| %s | %d | %d | %s | %d | %s | %s |" % (n, c["hops"], c["attended_ok"], c["reliability"] or "-", c["autonomous"], c["charter"], c["answer"]))
    if not d["chains"]:
        L.append("| (none) | | | | | | |")
    L += ["", "## Holds by reason (deduped)", ""] + (["- %s: %d" % (w, n) for w, n in sorted(d["holds"].items(), key=lambda x: -x[1])] or ["- none"])
    au = d["autoruns"]
    L += ["", "## Autonomous runs (deduped)", "", "%d attempt(s), %d ok; by result %s; by trigger %s"
          % (au["n"], au["ok"], json.dumps(au["by_result"], sort_keys=True), json.dumps(au["by_trigger"], sort_keys=True)), ""]
    L += ["_Content-free by construction: names, apps, codes and counts. No slot text, template, label or answer text is in the ledger rows "
          "this reads except a judged, kept last_answer -- and this file shows only whether one was kept._", ""]
    return "\n".join(L)


def digest_write(say=print, out=None, path=None, now=None):
    """Write ops/ACTUATOR_DIGEST.md (env COVENANT_ACTUATOR_DIGEST overrides) from
    the ledger; tmp + os.replace; one summary line through `say`. Returns the path."""
    out = out or os.environ.get("COVENANT_ACTUATOR_DIGEST") or os.path.join(HERE, "ops", "ACTUATOR_DIGEST.md")
    now = time.time() if now is None else now
    d = digest(last_rows(path), now)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    tmp = out + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(digest_markdown(d))
    os.replace(tmp, out)
    say("actuator digest: %d recipe(s), %d chain(s), %d app(s), %d hold reason(s), %d autonomous attempt(s), %d alert(s) -> %s"
        % (len(d["recipes"]), len(d["chains"]), len(d["apps"]), len(d["holds"]), d["autoruns"]["n"], len(d["alerts"]), out))
    for a in d["alerts"]:
        say("  " + a)
    return out


EXPLAIN = __doc__.split("Run:")[0].strip()


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="what the phone's actuator has learned, synced to this PC")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--log", nargs="?", const=20, type=int, metavar="N")
    g.add_argument("--digest", action="store_true")
    g.add_argument("--explain", action="store_true")
    a = ap.parse_args(argv)
    if a.log is not None:
        rows = last_rows()
        for r in rows[-a.log:]:
            print(json.dumps(r))
        if not rows:
            print("(no actuator-learning sync yet)")
        return 0
    if a.digest:
        digest_write()
        return 0
    if a.explain:
        print(EXPLAIN)
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
