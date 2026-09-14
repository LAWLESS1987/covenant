#!/usr/bin/env python3
"""covenant_ai_consult.py -- letting the covenant's own learning consult the
OTHER AI apps the operator already uses (ChatGPT, Gemini, ...), the way he
himself does: through his own signed-in browser session, never an API key,
never the phone's actuator automating a mobile app unattended.

The operator's ask, 2026-09-13/14: "have it start learning asking the ai apps
questions", clarified to mean his own past conversations WITH those apps
(never another person's), and a bounded exchange through HIS browser -- the
same channel this session already used for the Gemini/ChatGPT roundtable and
for reading his last two threads (ops/chat/SESSIONS_2026-09-13_chatgpt_gemini.md).

WHY THIS FILE DOES NOT DRIVE A BROWSER ITSELF. It cannot: a plain Python
process has no channel into Claude-in-Chrome or any other browser automation
-- that tool exists only for the assistant driving an interactive session, at
the operator's direction, one exchange at a time. That absence is load-
bearing, not a gap to fill: this project's own history (A67/A69/A79 in
docs/KNOWN_ISSUES.md) is that every outbound path built WEAKER than the
transaction gate got exploited or forged its own provenance. An unattended
script that could reach out to ChatGPT on a timer, with no session watching,
would be exactly that weaker path. So the two pieces stay separate on
purpose: this module is the judge and the ledger (offline, testable,
side-effect-free by itself); the browser action happens through the
assistant, in a session, one bounded question at a time, using the two
functions below around it.

THE GATE. Deterministic, not a reused financial-fraud classifier. The first
version of this file called covenant_moltbook's exact judge_outbound() --
the SAME build_semantic_quorum() the trading gate uses -- on the theory that
a second path should never be weaker than the first (A69's lesson). Measured
result, 2026-09-14: pointed at an ordinary question ("what year was the
transistor invented?"), it came back VIOLATES, on 4 matched tokens, log-odds
past its own hold threshold -- its own reasoning text calls itself "a
compressed model, not a reasoning judge; treat it as a flag to review, never
as a finding." Right strength, wrong domain: a classifier trained on this
project's theft/deception ledger has nothing to say about whether a trivia
question is safe to send to ChatGPT. So judge_outbound() here checks the
thing that actually matters for this domain -- no secret or key pattern, no
internal file path, not an absurdly long paste -- deterministically, and
logs the theft/deception quorum's opinion alongside as a record for whoever
tunes this later, without letting it decide.

THE LEDGER. ops/ai_consult.jsonl (gitignored), append-only, one row per
question: written BEFORE the browser action runs, the same as
ops/outbound_overrides.jsonl records an override before the send. If the
browser step never happens (he changes his mind, the tab won't load), the
row still says a clean question was ABOUT to be asked and by whom -- the
record is of the intent, not just the outcome, so an interrupted run cannot
look like nothing happened. record_result() appends the answer afterward,
keyed to the same id.

THE RATE LIMIT. Being a good guest of someone else's service is a
precondition of being allowed to consult it at all (the ambassador's own
words, covenant_ambassador.py): DEFAULT_MAX_PER_DAY per app, counted from the
ledger itself, refusing further questions once hit rather than throttling
silently.

Run:
  python covenant_ai_consult.py --check "the question text" [--app chatgpt]
      judge only, no ledger row, no send -- see what the gate would say
  python covenant_ai_consult.py --log [N]
      the last N ledger rows (default 20)
"""
import hashlib
import io
import json
import os
import re
import secrets
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER = os.environ.get("COVENANT_AI_CONSULT_LEDGER") or os.path.join(HERE, "ops", "ai_consult.jsonl")
KNOWN_APPS = ("chatgpt", "gemini")
DEFAULT_MAX_PER_DAY = 12          # a bounded number of exchanges, not a background chatter loop
MAX_QUESTION_CHARS = 2000         # a real question, not an accidental paste of a file

# What a question bound for someone else's service must never carry -- checked
# deterministically, not by a model. Found the hard way, 2026-09-14: the
# covenant's semantic quorum is a theft/deception classifier for financial
# transactions (build_semantic_quorum(), the same one the trading gate uses),
# and pointed at an ordinary trivia question ("what year was the transistor
# invented?") it came back VIOLATES -- its own reasoning text says why: "a
# compressed model ... treat it as a flag to review, never as a finding."
# Right strength for a different domain, wrong domain for this one. A leaked
# secret or a wholesale paste of internal files is a concrete, nameable risk
# a simple pattern check catches reliably; "is this a reasonable question"
# is not, and a financial-fraud classifier answering it produces noise, not
# safety. So: deterministic checks are the gate (they block); the semantic
# quorum's opinion is still asked and still logged, for whoever tunes this
# later, but it no longer gets a vote.
_SECRET_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"-----BEGIN OPENSSH PRIVATE KEY-----"),
    re.compile(r"\bCOVENANT_[A-Z_]*(?:TOKEN|SECRET|PASSWORD|KEYSTORE)[A-Z_]*\s*[:=]"),
    re.compile(r"\bPHONE_KEYSTORE_(?:B64|PASSWORD)\b"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),                      # a live-shaped GitHub token
    re.compile(r"\b[a-fA-F0-9]{48,}\b"),                          # a hash/key-length hex run
    re.compile(r"\.db\.key\b"),                                   # a node identity key filename
    re.compile(r"\bops[/\\](?:daily_plan|sealed_mail|quorum_policy\.json|phone\.pem)"),
]


def _canon(d):
    return json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha(text):
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def _deterministic_check(text):
    """(clean, reasons) -- the checks that actually block: secrets, internal
    file paths, and a length sane for a question rather than a paste."""
    reasons = []
    t = text or ""
    if len(t) > MAX_QUESTION_CHARS:
        reasons.append("refused: %d characters is a paste, not a question (max %d)" % (len(t), MAX_QUESTION_CHARS))
        return False, reasons
    hits = [p.pattern for p in _SECRET_PATTERNS if p.search(t)]
    if hits:
        reasons.append("refused: matches a secret/internal-data pattern (%d pattern(s), not shown)" % len(hits))
        return False, reasons
    reasons.append("deterministic check: clean (no secret pattern, %d chars)" % len(t))
    return True, reasons


def _quorum_opinion(text):
    """The semantic/theft-deception quorum's opinion, for the log only -- see
    the module docstring for why it is advisory here, not a gate. Never
    raises: any failure just means no opinion was logged, not a refusal."""
    try:
        import covenant_judge_defer as D
        import covenant_unified_v8 as cov
        D.apply_policy(os.environ, D.load_policy())
        data = {"text": text, "kind": "outbound_ai_consult", "origin": "covenant_ai_consult"}
        r = cov.build_semantic_quorum().evaluate(data, cov.DIVINE_PRINCIPLES)
        held = bool(getattr(r, "not_understood", False))
        ran = not bool(getattr(r, "infrastructure_failure", False))
        label = "HELD" if held else ("DID NOT RUN" if not ran else ("violates" if r.violates else "clean"))
        return "quorum opinion (advisory, not a gate): %s -- %s" % (label, str(getattr(r, "reasoning", ""))[:300])
    except Exception as e:                                        # noqa: BLE001
        return "quorum opinion unavailable (advisory, not a gate): %s: %s" % (type(e).__name__, str(e)[:120])


def judge_outbound(text):
    """(clean, reasons, held, ran) -- deterministic secret/leak/length checks
    DECIDE; the theft/deception semantic quorum's opinion is asked and always
    appended to `reasons` for the record, but never blocks (see the module
    docstring for the measured reason). `held`/`ran` are always False/True
    here -- this gate has no HOLD state of its own; a refusal is always a
    stated reason, never an unresolved one."""
    clean, reasons = _deterministic_check(text)
    reasons.append(_quorum_opinion(text))
    return clean, reasons, False, True


def _today():
    return time.strftime("%Y-%m-%d", time.localtime())


def _rows(path=None):
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


def rate_ok(app, max_per_day=None, path=None, now=None):
    """(ok, count_today, limit). Counts INTENT rows (kind=='ask') for this app
    today -- asking counts against the limit whether or not an answer ever
    came back, since the point is not chattering at their service."""
    limit = DEFAULT_MAX_PER_DAY if max_per_day is None else max_per_day
    day = time.strftime("%Y-%m-%d", time.localtime(now)) if now is not None else _today()
    n = sum(1 for r in _rows(path) if r.get("kind") == "ask" and r.get("app") == app and str(r.get("t", "")).startswith(day))
    return n < limit, n, limit


def record_intent(app, question, verdict, by, path=None, now=None):
    """Written BEFORE the browser action runs -- an interrupted exchange still
    leaves a true record that a clean question was about to be sent, by whom.
    Returns the row (its 'id' is what record_result() needs)."""
    if app not in KNOWN_APPS:
        raise ValueError("app must be one of %s, got %r" % (KNOWN_APPS, app))
    clean, reasons, held, ran = verdict
    row = {
        "id": secrets.token_hex(8),
        "t": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(now)),
        "at": round(now if now is not None else time.time(), 1),
        "kind": "ask",
        "app": app,
        "by": by,
        "question_sha256": _sha(question),
        "question_chars": len(question or ""),
        "clean": bool(clean),
        "held": bool(held),
        "ran": bool(ran),
        "reasons": reasons,
    }
    path = path or LEDGER
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(_canon(row) + "\n")
    return row


def record_result(intent_id, answer, app=None, path=None, now=None):
    """Appended after the browser step returns (or fails). A second, linked
    row rather than a rewrite of the first: the ledger is append-only, the
    same discipline every other ledger in this project keeps."""
    row = {
        "id": secrets.token_hex(8),
        "t": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(now)),
        "at": round(now if now is not None else time.time(), 1),
        "kind": "result",
        "intent_id": intent_id,
        "app": app,
        "answer_sha256": _sha(answer) if answer else None,
        "answer_chars": len(answer or ""),
        "answer_excerpt": (answer or "")[:800],
    }
    path = path or LEDGER
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(_canon(row) + "\n")
    return row


def gate(app, question, by, max_per_day=None, path=None, now=None):
    """The one call a caller needs: judge, rate-limit, and (if both pass)
    write the before-send row. Returns (ok, message, intent_row_or_None).
    ok=False means: do not open the browser, do not type anything -- the
    message says why. ok=True means the intent row is already written; the
    caller runs the browser step next and MUST call record_result(row['id'],
    ...) when it returns, success or failure, so the ledger has both halves."""
    if app not in KNOWN_APPS:
        return False, "unknown app %r (known: %s)" % (app, ", ".join(KNOWN_APPS)), None
    if not (question or "").strip():
        return False, "empty question", None
    ok_rate, n, limit = rate_ok(app, max_per_day, path, now)
    if not ok_rate:
        return False, "rate limit reached for %s today: %d/%d already asked" % (app, n, limit), None
    verdict = judge_outbound(question)
    clean, reasons, held, ran = verdict
    if not clean:
        return False, "refused: %s" % "; ".join(reasons), None
    row = record_intent(app, question, verdict, by, path, now)
    return True, "clean, logged as %s" % row["id"], row


EXPLAIN = __doc__.split("Run:")[0].strip()


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="the judge and ledger for consulting the other AI apps")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--check", metavar="TEXT")
    g.add_argument("--log", nargs="?", const=20, type=int, metavar="N")
    g.add_argument("--explain", action="store_true")
    ap.add_argument("--app", default="chatgpt", choices=KNOWN_APPS)
    a = ap.parse_args(argv)
    if a.check:
        clean, reasons, held, ran = judge_outbound(a.check)
        ok_rate, n, limit = rate_ok(a.app)
        print(json.dumps({"clean": clean, "held": held, "ran": ran, "reasons": reasons,
                          "rate_ok": ok_rate, "asked_today": n, "limit": limit}, indent=1))
        return 0 if clean and ok_rate else 1
    if a.log is not None:
        rows = _rows()
        for r in rows[-a.log:]:
            print(json.dumps(r))
        if not rows:
            print("(no consult ledger yet)")
        return 0
    if a.explain:
        print(EXPLAIN)
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
