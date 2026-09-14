#!/usr/bin/env python3
"""covenant_actuator_guide.py -- what this PC may SAY to the phone's brain
(the Accessibility actuator, phase 3), and the library of recipe cards it may
OFFER. Both are reduce-only: the PC can hold, cap, deny, switch the OCR tap
off, and offer a card the owner imports with a tap. It cannot start a run,
name a recipe, schedule, type, grant autonomy, or clear the owner's own hold
-- no key for any of that exists in the document, and a key that looks like
one (GRANT_LIKE) in the operator file is refused loudly, not dropped quietly.

WHY A SIGNED DOCUMENT AND NOT A SETTING. The phone pins this PC's daily-plan
key (Settings.pcKeyPem, the same key sealed mail signs with). Every GET here
answers {"status","doc","sig","spk"}: the doc is signed PSS-SHA256 over its
canonical JSON, echoes the nonce the phone sent, and carries an `issued`
stamp the phone requires to be newer than the last. So a replayed, stale,
tampered or re-signed document does nothing on the phone -- and this PC
cannot be talked into serving a grant, because build() only ever emits
GUIDE_KEYS.

THE OPERATOR FILE. ops/actuator_guide.json (gitignored) is written by the
CLI below and holds at most: hold, hold_why, until, max_runs_per_day,
deny_apps, ocr_taps, note. build() turns it into the guide document at
request time: `until` is the operator's until clamped to issued+7 days (the
PC re-issues on every fetch, so a 30-day hold stays in force by repetition,
never by a single long-lived document). Every write is tmp+os.replace and
one line in ops/actuator_guide.log.

THE LIBRARY. ops/actuator_library/<sha256>.json, one recipe CARD each --
steps only: no scores, runs, answers, charter or source; every type step is
a slot (the PC never supplies text the phone will type); coordinates of any
kind are refused outright; a denied (money) app is refused. The sha is of
the canonical CLEAN card, so the phone re-derives it and refuses a card
that does not match its listing. Import is the owner's tap on the phone.

Run:
  python covenant_actuator_guide.py --hold WHY [--days N]   hold autonomous starts (default 7 days)
  python covenant_actuator_guide.py --release               lift the PC hold (never the owner's)
  python covenant_actuator_guide.py --cap N                 at most N autonomous starts/day (1..12; 0 refused; "none" clears)
  python covenant_actuator_guide.py --deny PKG | --undeny PKG
  python covenant_actuator_guide.py --ocr-taps on|off
  python covenant_actuator_guide.py --note TEXT
  python covenant_actuator_guide.py --show | --library | --library-add FILE | --library-rm SHA | --explain
"""
import base64
import hashlib
import json
import os
import re
import time

HERE = os.path.dirname(os.path.abspath(__file__))

# ---- constants: pasted VERBATIM from the pinned CONSTANTS.py (phase 3) ----------------------------
LIMITS = {"max_hops": 5, "max_fallbacks": 2, "max_per_day_ceiling": 12, "ai_per_day": 3,
          "min_spacing_min": 5, "chain_wall_s": 600, "global_daily_default": 12, "charter_days": 30,
          "guidance_max_days": 7, "answer_cap": 6000, "slot_cap": 4000, "chain_attended_ok_required": 3,
          "autoruns_keep": 500, "holds_keep": 200, "card_max_steps": 40, "card_str_cap": 400,
          "ocr_label_cap": 120, "template_cap": 400, "learn_recipes_max": 50, "learn_chains_max": 20,
          "learn_autoruns_max": 50, "learn_holds_max": 30, "runs_keep": 40, "hold_why_cap": 200,
          "note_cap": 400, "deny_apps_max": 50, "nonce_hex_len": 32}

# Money apps Covenant never touches, at any level, on any path (the operator's own rule; A105 said
# "refused outright" in prose -- phase 3 makes it code). A denylist the owner extends; ids verified
# only against his own phone. DENIED_RE is a plain alternation (no anchors, no backslashes) matched
# case-insensitively against the package id; ALLOW_DESPITE names known collisions.
DENIED_APPS = ("com.robinhood.android", "com.coinbase.android", "org.toshi", "com.kraken.invest.app",
               "com.kraken.trade", "com.binance.dev", "org.dayup.stocks", "com.schwab.mobile",
               "com.fidelity.android", "com.etrade.mobilepro.activity", "com.tdameritrade.mobile3",
               "co.mona.android", "io.metamask", "com.wallet.crypto.trustapp", "com.squareup.cash",
               "com.paypal.android.p2pmobile", "com.venmo")
DENIED_RE = "(robinhood|coinbase|kraken|binance|webull|etoro|schwab|fidelity|vanguard|ameritrade|interactivebrokers|tradestation|metamask|phantom|trustwallet|paypal|venmo|cashapp|trade|trading|broker|exchange|wallet|bank)"
ALLOW_DESPITE = ("com.android.exchange",)

# The other AI apps: capped at LIMITS["ai_per_day"] autonomous starts per PACKAGE per local day,
# across recipes, chains and fallbacks (the account-terms risk covenant_ai_consult.py names).
AI_APPS = ("com.openai.chatgpt", "com.google.android.apps.bard", "com.anthropic.claude", "ai.x.grok",
           "com.deepseek.chat", "com.microsoft.copilot", "ai.perplexity.app.android")
# Browsers reach everything: attended only, never unattended.
BROWSER_APPS = ("com.android.chrome", "org.mozilla.firefox", "com.sec.android.app.sbrowser", "com.brave.browser",
                "com.microsoft.emmx", "com.opera.browser", "org.chromium.chrome", "com.duckduckgo.mobile.android")
SEND_WORDS = ("send", "post", "submit", "share", "reply", "tweet", "done")

# Byte-for-byte mirror of covenant_ai_consult._SECRET_PATTERNS (regex SOURCE strings; each side
# compiles them). M5.21 / AL2.13 run both sides over the same corpus.
SECRET_PATTERNS = [
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    r"-----BEGIN OPENSSH PRIVATE KEY-----",
    r"\bCOVENANT_[A-Z_]*(?:TOKEN|SECRET|PASSWORD|KEYSTORE)[A-Z_]*\s*[:=]",
    r"\bPHONE_KEYSTORE_(?:B64|PASSWORD)\b",
    r"\bghp_[A-Za-z0-9]{20,}\b",
    r"\b[a-fA-F0-9]{48,}\b",
    r"\.db\.key\b",
    r"\bops[/\\](?:daily_plan|sealed_mail|quorum_policy\.json|phone\.pem)",
]

# What the PC may say to the phone (GET /actuator_guide): reduce-only. Anything else is dropped,
# listed, and -- when it looks like a grant -- counted as an attempted grant.
GUIDE_KEYS = ("v", "issued", "until", "nonce", "hold", "hold_why", "max_runs_per_day", "deny_apps", "ocr_taps", "note")
GRANT_LIKE = ("run", "jobs", "job", "recipes", "recipe", "slot", "standing_slot", "schedule", "unattended", "grant",
              "allowed_apps", "charter", "priors", "locator_priors", "chains", "chain", "owner_hold", "release")

# A recipe card (the PC library, and the owner's own Export): steps only, no scores, runs,
# answers or charter; every type step is a slot. Coordinates of any kind are refused outright.
CARD_KEYS = ("v", "name", "pkg", "goal", "steps")
CARD_STEP_KEYS = ("kind", "id", "text", "desc", "cls", "ordinal", "slot", "ocr")
CARD_KINDS = ("click", "type", "scroll")
CARD_FORBIDDEN = ("x", "y", "tap", "gesture", "coordinates", "bounds", "gestures")
CARD_STRIP = ("charter", "runs", "last_answer", "stats", "scores", "source", "sync_answer", "ocr_answer",
              "created", "last20", "last_answer_new", "answer_source")
# ---- end of the pasted block -----------------------------------------------------------------------

OPERATOR_KEYS = ("hold", "hold_why", "until", "max_runs_per_day", "deny_apps", "ocr_taps", "note")
_DENIED_RE = re.compile(DENIED_RE, re.I)
_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


# ---------------------------------------------------------------- paths (read at CALL time: tests point them at temp dirs)

def guide_path():
    return os.environ.get("COVENANT_ACTUATOR_GUIDE") or os.path.join(HERE, "ops", "actuator_guide.json")


def library_dir():
    return os.environ.get("COVENANT_ACTUATOR_LIBRARY") or os.path.join(HERE, "ops", "actuator_library")


def log_path():
    return os.environ.get("COVENANT_ACTUATOR_GUIDE_LOG") or os.path.join(HERE, "ops", "actuator_guide.log")


def _log(line):
    p = log_path()
    os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
    with open(p, "a", encoding="utf-8") as fh:
        fh.write("%s  %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%S%z"), _clean_str(line, 400)))


def _write_json(path, obj):
    """tmp + os.replace: a reader never sees a half-written file."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, sort_keys=True, indent=1, ensure_ascii=False)
    os.replace(tmp, path)


def _clean_str(x, cap):
    return _CTRL.sub("", str(x if x is not None else ""))[:cap]


def canonical(doc):
    return json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _norm_pem(pem):
    return "".join(str(pem or "").split())


# ---------------------------------------------------------------- the denylist (the same three constants the phone carries)

def denied_app(pkg):
    """'' when the app may be driven; otherwise the plain reason. ALLOW_DESPITE
    wins over the pattern (com.android.exchange is mail, not a market)."""
    p = str(pkg or "").strip()
    if not p:
        return "empty package id"
    if p in ALLOW_DESPITE:
        return ""
    if p in DENIED_APPS:
        return "denied list"
    if _DENIED_RE.search(p):
        return "matches money-app pattern"
    return ""


# ---------------------------------------------------------------- the operator file and the guide document

def load_operator():
    """The CLI-written file as a dict, None when absent. A GRANT_LIKE key in it
    is a ValueError naming the key: this file is the one place a person could
    try to make the PC say more than it may, and that must fail loudly."""
    p = guide_path()
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as fh:
        raw = json.load(fh)
    if not isinstance(raw, dict):
        raise ValueError("operator file %s is not a JSON object" % p)
    bad = sorted(k for k in raw if str(k) in GRANT_LIKE)
    if bad:
        raise ValueError("operator file carries grant-like key(s) %s -- refusing to build a guide; the PC may only hold, cap, deny, switch taps off" % ", ".join(bad))
    return raw


def sanitize(doc):
    """(clean, refused_keys): exactly GUIDE_KEYS, every value coerced and capped;
    any other key is dropped and named. Idempotent: a clean doc refuses nothing.
    Never raises -- the loud refusal for grant-like keys lives in load_operator()."""
    d = doc if isinstance(doc, dict) else {}
    refused = sorted(str(k) for k in d if k not in GUIDE_KEYS)
    cap = d.get("max_runs_per_day")
    if isinstance(cap, bool) or not isinstance(cap, int) or not (1 <= cap <= LIMITS["max_per_day_ceiling"]):
        if cap is not None:
            refused.append("max_runs_per_day")
        cap = None
    deny = d.get("deny_apps")
    deny_clean = []
    if isinstance(deny, list):
        for a in deny:
            s = _clean_str(a, 200).strip()
            if s and s not in deny_clean:
                deny_clean.append(s)
        deny_clean = deny_clean[:LIMITS["deny_apps_max"]]
    elif deny is not None:
        refused.append("deny_apps")
    ocr = d.get("ocr_taps")
    if not (ocr is None or isinstance(ocr, bool)):
        refused.append("ocr_taps")
        ocr = None
    clean = {
        "v": 1,
        "issued": _int(d.get("issued")),
        "until": _int(d.get("until")),
        "nonce": _clean_str(d.get("nonce"), 64),
        "hold": d.get("hold") is True,
        "hold_why": _clean_str(d.get("hold_why"), LIMITS["hold_why_cap"]),
        "max_runs_per_day": cap,
        "deny_apps": deny_clean,
        "ocr_taps": ocr,
        "note": _clean_str(d.get("note"), LIMITS["note_cap"]),
    }
    return clean, sorted(set(refused))


def _int(x, default=0):
    if isinstance(x, bool):
        return default
    try:
        return int(x)
    except (TypeError, ValueError):
        return default


def build(now, nonce):
    """The guide document for one fetch: the operator file, stamped `issued`
    now, `until` clamped to issued + guidance_max_days, the phone's nonce
    echoed. A missing operator file builds the empty guide (no hold, no cap)."""
    op = load_operator() or {}
    issued = int(now)
    doc = {k: op.get(k) for k in OPERATOR_KEYS if k in op}
    doc.update({"v": 1, "issued": issued, "nonce": nonce})
    doc["until"] = min(_int(op.get("until")), issued + LIMITS["guidance_max_days"] * 86400)
    clean, _refused = sanitize(doc)
    return clean


# ---------------------------------------------------------------- signing (the daily-plan key; the PSS primitive sealed mail uses)

def _pss():
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    return padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH), hashes.SHA256()


def _key(key=None):
    if key is not None:
        return key
    import covenant_daily_plan as dp
    return dp.load_key()


def sign_doc(doc, key):
    import covenant_daily_plan as dp
    pad, h = _pss()
    sig = key.sign(canonical(doc), pad, h)
    return {"status": "success", "doc": doc, "sig": base64.b64encode(sig).decode("ascii"), "spk": dp.pubkey_pem(key)}


def verify_doc(resp, pem, expect_nonce=None):
    """(ok, doc, reason) -- the phone's check, runnable here so AL2 can prove a
    tampered byte, another key or a wrong nonce is refused. Never raises."""
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    if not isinstance(resp, dict) or resp.get("status") != "success":
        return False, None, "not a success response"
    doc, sig, spk = resp.get("doc"), resp.get("sig"), resp.get("spk")
    if not isinstance(doc, dict) or not isinstance(sig, str) or not isinstance(spk, str):
        return False, None, "response lacks doc/sig/spk"
    if _norm_pem(spk) != _norm_pem(pem):
        return False, None, "signer key is not the pinned PC key"
    try:
        pub = serialization.load_pem_public_key(spk.encode("utf-8"))
        if not isinstance(pub, rsa.RSAPublicKey):
            return False, None, "signer key is not an RSA key"
        pad, h = _pss()
        pub.verify(base64.b64decode(sig, validate=True), canonical(doc), pad, h)
    except InvalidSignature:
        return False, None, "signature does not verify"
    except Exception as e:                                        # noqa: BLE001
        return False, None, "unverifiable: %s" % type(e).__name__
    if expect_nonce is not None and doc.get("nonce") != expect_nonce:
        return False, None, "nonce mismatch"
    return True, doc, "ok"


def _signed_or_error(doc, key):
    """sign_doc(), or the contract's JSON error when the key cannot be loaded.

    2026-09-14 (review finding 18): only ValueError was guarded, and the key
    comes from covenant_daily_plan.load_key(), which deliberately raises
    whatever the disk gives it -- an OSError on an unreadable
    nodeA_prod.db.key, a cryptography error on a corrupt one. All three
    signed GETs therefore answered an unhandled 500 instead of the JSON
    error the phone's contract (INTERFACE 8) names. The reason goes to the
    log; the phone is told only that the key is unavailable."""
    try:
        return sign_doc(doc, _key(key))
    except Exception as e:                                        # noqa: BLE001
        _log("signing key unavailable (%s: %s) -- served an error, not a document" % (type(e).__name__, e))
        return {"status": "error", "message": "signing key unavailable"}


def guide_signed(nonce, key=None):
    """The route's answer: None when no operator file exists (the route says
    404), an error object when the file is refused or the key is unavailable,
    else the signed guide."""
    try:
        if load_operator() is None:
            return None
        doc = build(time.time(), _clean_str(nonce, 64))
    except ValueError as e:
        _log("REFUSED to serve a guide: %s" % e)
        return {"status": "error", "message": str(e)}
    except OSError as e:
        _log("could not read the operator file (%s: %s) -- served an error, not a document" % (type(e).__name__, e))
        return {"status": "error", "message": "operator file unreadable"}
    return _signed_or_error(doc, key)


# ---------------------------------------------------------------- the card library

def _walk_keys(obj, out):
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.add(str(k))
            _walk_keys(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _walk_keys(v, out)
    return out


def card_clean(card):
    """{"ok":True,"card":clean,"stripped":[...]} or {"ok":False,"error":why}.
    Forbidden (coordinate) keys anywhere refuse the whole card; a type step
    is always a slot with empty text; every string is capped; the money
    denylist applies. The PC has no green list -- that check is the phone's."""
    if not isinstance(card, dict):
        return {"ok": False, "error": "card is not an object"}
    forbidden = sorted(k for k in _walk_keys(card, set()) if k in CARD_FORBIDDEN)
    if forbidden:
        return {"ok": False, "error": "forbidden key(s) %s -- coordinates of any kind are refused" % ", ".join(forbidden)}
    name = _clean_str(card.get("name"), LIMITS["card_str_cap"]).strip()
    pkg = _clean_str(card.get("pkg"), LIMITS["card_str_cap"]).strip()
    if not name:
        return {"ok": False, "error": "card has no name"}
    why = denied_app(pkg)
    if why:
        return {"ok": False, "error": "package %s refused: %s" % (pkg or "(empty)", why)}
    steps = card.get("steps")
    if not isinstance(steps, list) or not steps:
        return {"ok": False, "error": "card has no steps"}
    if len(steps) > LIMITS["card_max_steps"]:
        return {"ok": False, "error": "%d steps exceeds the card cap of %d" % (len(steps), LIMITS["card_max_steps"])}
    stripped = sorted(str(k) for k in card if k in CARD_STRIP) + sorted("(unknown) " + str(k) for k in card if k not in CARD_KEYS and k not in CARD_STRIP)
    out_steps = []
    for i, s in enumerate(steps):
        if not isinstance(s, dict):
            return {"ok": False, "error": "step %d is not an object" % i}
        kind = str(s.get("kind", "")).strip()
        if kind not in CARD_KINDS:
            return {"ok": False, "error": "step %d kind %r is not one of %s" % (i, kind, "/".join(CARD_KINDS))}
        for k in s:
            if k not in CARD_STEP_KEYS:
                stripped.append("step[%d].%s" % (i, k))
        ordinal = _int(s.get("ordinal"), 0)
        st = {"kind": kind,
              "id": _clean_str(s.get("id"), LIMITS["card_str_cap"]),
              "text": _clean_str(s.get("text"), LIMITS["card_str_cap"]),
              "desc": _clean_str(s.get("desc"), LIMITS["card_str_cap"]),
              "cls": _clean_str(s.get("cls"), LIMITS["card_str_cap"]),
              "ordinal": min(max(ordinal, 0), 999),
              "slot": s.get("slot") is True,
              "ocr": _clean_str(s.get("ocr"), LIMITS["ocr_label_cap"])}
        if kind == "type":
            if st["text"] or not st["slot"]:
                stripped.append("step[%d].text (type steps are slots; the PC supplies no text)" % i)
            st["slot"], st["text"] = True, ""
        out_steps.append(st)
    clean = {"v": 1, "name": name, "pkg": pkg, "goal": _clean_str(card.get("goal"), LIMITS["card_str_cap"]), "steps": out_steps}
    return {"ok": True, "card": clean, "stripped": stripped}


def card_sha(clean_card):
    return hashlib.sha256(canonical(clean_card)).hexdigest()


def library_add(path):
    """Validate a card file and store it as <sha256 of the clean card>.json.
    Returns {"ok":True,"sha","stripped"} or {"ok":False,"error"}."""
    try:
        with open(path, encoding="utf-8") as fh:
            card = json.load(fh)
    except (OSError, ValueError) as e:
        return {"ok": False, "error": "cannot read %s: %s" % (path, type(e).__name__)}
    r = card_clean(card)
    if not r["ok"]:
        _log("library-add REFUSED %s: %s" % (os.path.basename(path), r["error"]))
        return r
    try:
        op = load_operator() or {}
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    if r["card"]["pkg"] in (op.get("deny_apps") or []):
        _log("library-add REFUSED %s: pkg on the PC deny list" % os.path.basename(path))
        return {"ok": False, "error": "package %s is on this PC's deny list" % r["card"]["pkg"]}
    sha = card_sha(r["card"])
    item = {"v": 1, "sha256": sha, "card": r["card"], "stripped": r["stripped"],
            "curated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "from": os.path.basename(path)[:200]}
    _write_json(os.path.join(library_dir(), sha + ".json"), item)
    _log("library-add %s %s (%s, %d steps, stripped %d)" % (sha[:12], r["card"]["name"], r["card"]["pkg"], len(r["card"]["steps"]), len(r["stripped"])))
    return {"ok": True, "sha": sha, "stripped": r["stripped"]}


def _read_item(sha):
    if not _HEX64.match(str(sha or "")):
        return None
    p = os.path.join(library_dir(), sha + ".json")
    try:
        with open(p, encoding="utf-8") as fh:
            item = json.load(fh)
    except (OSError, ValueError):
        return None
    card = item.get("card") if isinstance(item, dict) else None
    if not isinstance(card, dict) or card_sha(card) != sha:
        _log("library item %s does not match its own sha -- ignored" % sha[:12])
        return None
    return item


def library_list():
    d = library_dir()
    items = []
    try:
        names = sorted(os.listdir(d))
    except OSError:
        return items
    for n in names:
        if not n.endswith(".json"):
            continue
        item = _read_item(n[:-5])
        if item is None:
            continue
        c = item["card"]
        items.append({"sha": item["sha256"], "name": c["name"], "goal": c.get("goal", ""), "pkg": c["pkg"],
                      "steps": len(c["steps"]), "curated_at": str(item.get("curated_at", ""))})
    items.sort(key=lambda x: x["curated_at"], reverse=True)
    return items[:50]


def library_item(sha):
    item = _read_item(sha)
    return item["card"] if item else None


def library_rm(sha):
    if not _HEX64.match(str(sha or "")):
        return False
    p = os.path.join(library_dir(), sha + ".json")
    try:
        os.remove(p)
    except OSError:
        return False
    _log("library-rm %s" % sha[:12])
    return True


def library_signed(nonce, key=None):
    doc = {"v": 1, "nonce": _clean_str(nonce, 64), "issued": int(time.time()), "items": library_list()}
    return _signed_or_error(doc, key)


def item_signed(sha, nonce, key=None):
    card = library_item(sha)
    if card is None:
        return None
    doc = {"v": 1, "nonce": _clean_str(nonce, 64), "issued": int(time.time()), "sha256": sha, "card": card}
    return _signed_or_error(doc, key)


# ---------------------------------------------------------------- the watchdog's one line

def status():
    try:
        op = load_operator() or {}
        hold, cap, deny = op.get("hold") is True, op.get("max_runs_per_day"), len(op.get("deny_apps") or [])
    except json.JSONDecodeError as e:
        # 2026-09-14 (review finding 21): REFUSED is the word for an attempted
        # grant. A file that is merely not JSON is a disk or edit accident, and
        # the watchdog line must not read as though someone tried something.
        return "phone brain: operator file UNREADABLE (not JSON: %s)" % str(e)[:100]
    except OSError as e:
        return "phone brain: operator file UNREADABLE (%s)" % type(e).__name__
    except ValueError as e:
        return "phone brain: operator file REFUSED (%s)" % str(e)[:120]
    if hold and _int(op.get("until")) <= time.time():
        hold = False
    return "phone brain: hold=%s cap=%s denied +%d library %d card(s)" % (
        hold, cap if isinstance(cap, int) and not isinstance(cap, bool) else "none", deny, len(library_list()))


EXPLAIN = __doc__.split("Run:")[0].strip()


# ---------------------------------------------------------------- CLI

_PKG_RE = re.compile(r"^[A-Za-z0-9_]+(\.[A-Za-z0-9_]+)*$")


def _bad_pkg(pkg):
    """Why this is not a package id, or ''.

    2026-09-14 (review finding 20): --deny "" wrote an empty string into
    deny_apps and still fell through to --show. status() then counted it as a
    denial while sanitize() dropped it again on the way to the phone, so the
    operator file said something the guide never says. Nothing grant-like could
    be served either way -- this is operator-file hygiene, refused at the door."""
    if not pkg:
        return "a package id is required (empty or whitespace is not one)"
    if not _PKG_RE.match(pkg):
        return "%r is not a package id (letters, digits, underscores, dot-separated)" % pkg[:80]
    return ""


def _mutate(fn, what):
    op = load_operator() or {}
    op = {k: op[k] for k in OPERATOR_KEYS if k in op}
    fn(op)
    _write_json(guide_path(), op)
    _log(what)


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="what this PC may say to the phone's brain: hold, cap, deny, taps off, offer")
    ap.add_argument("--hold", metavar="WHY")
    ap.add_argument("--days", type=int, default=LIMITS["guidance_max_days"])
    ap.add_argument("--release", action="store_true")
    ap.add_argument("--cap", metavar="N")
    ap.add_argument("--deny", metavar="PKG")
    ap.add_argument("--undeny", metavar="PKG")
    ap.add_argument("--ocr-taps", choices=("on", "off"))
    ap.add_argument("--note", metavar="TEXT")
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--library", action="store_true")
    ap.add_argument("--library-add", metavar="FILE")
    ap.add_argument("--library-rm", metavar="SHA")
    ap.add_argument("--explain", action="store_true")
    a = ap.parse_args(argv)
    if a.explain:
        print(EXPLAIN)
        return 0
    try:
        if a.hold is not None:
            why = _clean_str(a.hold, LIMITS["hold_why_cap"]).strip()
            if not why:
                print("refused: a hold needs a WHY the phone can show as 'PC says:'"); return 2
            days = max(1, a.days)
            until = int(time.time()) + days * 86400

            def f(op):
                op.update({"hold": True, "hold_why": why, "until": until})
            _mutate(f, "hold for %d day(s): %s" % (days, why))
            print("hold set for %d day(s) (the phone sees at most 7 per document; re-issued on every fetch): %s" % (days, why))
        if a.release:
            def f(op):
                op.update({"hold": False, "hold_why": "", "until": 0})
            _mutate(f, "release (the PC hold only; the owner's hold is his)")
            print("PC hold released")
        if a.cap is not None:
            if str(a.cap).strip().lower() == "none":
                def f(op):
                    op.pop("max_runs_per_day", None)
                _mutate(f, "cap cleared")
                print("cap cleared (the charters' own ceilings apply)")
            else:
                n = _int(a.cap, -1)
                if not (1 <= n <= LIMITS["max_per_day_ceiling"]):
                    print("refused: --cap must be 1..%d (0 is not a cap, it is a hold -- use --hold WHY; 'none' clears)" % LIMITS["max_per_day_ceiling"])
                    return 2

                def f(op):
                    op["max_runs_per_day"] = n
                _mutate(f, "cap %d/day" % n)
                print("cap set: at most %d autonomous start(s) per day" % n)
        if a.deny is not None:
            pkg = _clean_str(a.deny, 200).strip()
            bad = _bad_pkg(pkg)
            if bad:
                print("refused: %s" % bad); return 2
            op0 = load_operator() or {}
            if len(op0.get("deny_apps") or []) >= LIMITS["deny_apps_max"] and pkg not in (op0.get("deny_apps") or []):
                print("refused: the deny list holds %d already" % LIMITS["deny_apps_max"]); return 2

            def f(op):
                lst = [x for x in (op.get("deny_apps") or []) if x != pkg]
                op["deny_apps"] = lst + [pkg]
            _mutate(f, "deny %s" % pkg)
            print("denied on the phone (in addition to its own list): %s" % pkg)
        if a.undeny is not None:
            pkg = _clean_str(a.undeny, 200).strip()
            bad = _bad_pkg(pkg)
            if bad:
                print("refused: %s" % bad); return 2

            def f(op):
                op["deny_apps"] = [x for x in (op.get("deny_apps") or []) if x != pkg]
            _mutate(f, "undeny %s" % pkg)
            print("removed from the PC deny list (the phone's own list is untouched): %s" % pkg)
        if a.ocr_taps is not None:
            val = a.ocr_taps == "on"

            def f(op):
                op["ocr_taps"] = val
            _mutate(f, "ocr_taps %s" % a.ocr_taps)
            print("OCR taps: %s" % a.ocr_taps)
        if a.note is not None:
            note = _clean_str(a.note, LIMITS["note_cap"])

            def f(op):
                op["note"] = note
            _mutate(f, "note: %s" % note[:80])
            print("note set")
        if a.library_add:
            r = library_add(a.library_add)
            print(json.dumps(r, ensure_ascii=False))
            if not r["ok"]:
                return 2
        if a.library_rm:
            ok = library_rm(a.library_rm)
            print("removed" if ok else "no such card")
            if not ok:
                return 2
        if a.library:
            items = library_list()
            for it in items:
                print("%s  %-32s %-28s %2d step(s)  %s  %s" % (it["sha"][:12], it["name"][:32], it["pkg"][:28], it["steps"], it["curated_at"], it["goal"][:40]))
            if not items:
                print("(library empty: python covenant_actuator_guide.py --library-add FILE)")
        if a.show or not any([a.hold is not None, a.release, a.cap is not None, a.deny, a.undeny, a.ocr_taps, a.note is not None,
                              a.library, a.library_add, a.library_rm]):
            op = load_operator()
            print("operator file: %s%s" % (guide_path(), "" if op is not None else " (absent -- the route answers 404; the phone keeps owner-only bounds)"))
            if op is not None:
                ignored = sorted(k for k in op if k not in OPERATOR_KEYS)
                print(json.dumps({k: op[k] for k in OPERATOR_KEYS if k in op}, indent=1, ensure_ascii=False))
                if ignored:
                    print("ignored keys (not operator keys): %s" % ", ".join(ignored))
            doc = build(time.time(), "example-nonce")
            print("guide as the phone would receive it now:")
            print(json.dumps(doc, indent=1, ensure_ascii=False))
            print(status())
    except json.JSONDecodeError as e:
        print("UNREADABLE: %s is not JSON (%s) -- fix or delete it; REFUSED is the word for a grant" % (guide_path(), e))
        return 2
    except ValueError as e:
        print("REFUSED: %s" % e)
        return 2
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
