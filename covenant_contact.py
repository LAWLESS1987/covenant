#!/usr/bin/env python3
"""covenant_contact.py -- the direct line to him, through the phone app.

HIS WORDS, 2026-09-21: "i'm here if you need me add a way to contact me
direct through the phone app". And the frame he gave with it: stick to the
commandments and mutual benefit, follow the openness logic for the growth.

HOW IT WORKS, on the channel the phone already trusts. The phone checks in
with the PC every ten minutes, signed. The PC's answer to that check-in now
carries the messages this file holds for him (`pending()`), at most five,
oldest first. The phone raises each one once as a notification on its own
channel, writes it into the chat as "covenant  [why] text", speaks it if the
app is open, and sends the ids it has shown back on its next check-in
(`contact_seen`), which marks them delivered here. He answers in the box, and
the answer reaches the PC as an ordinary ask; `answered()` looks for an ask
from the tailnet after the message and records it, once.

WHO MAY WRITE TO HIM. Any part of the system, through `say()`, with a `why`
that names the actor and the reason -- the nightly when a pass is NOT GREEN,
the ambassador when she is isolated or when an ally writes back, the highway
when a proposal needs his tap, a person at the CLI. Every message is a row in
ops/contact_outbox.jsonl before it is sent, with who wrote it and why, so the
line cannot be used quietly.

WHAT IT MUST NOT CARRY, by the same rules as every other outward text: no
key, no code, no password, nothing from private/ (a text that names one is
refused here, not sent and softened). It is not a gate around him; it is a
door to him, and the record of who knocked.

  python covenant_contact.py --say "text" --why "reason" [--actor name]
  python covenant_contact.py --pending      # what waits for the phone
  python covenant_contact.py --list [N]     # the last N rows, with delivery and answers
"""
import hashlib
import json
import os
import re
import time

import covenant_screen as _screen   # A176: the refusal screen reads the text a reader sees

HERE = os.path.dirname(os.path.abspath(__file__))
OUTBOX = os.environ.get("COVENANT_CONTACT_OUTBOX") or os.path.join(HERE, "ops", "contact_outbox.jsonl")
STATE = os.environ.get("COVENANT_CONTACT_STATE") or os.path.join(HERE, "ops", "contact_state.json")
ASK_LOG = os.environ.get("COVENANT_ASK_LOG") or os.path.join(HERE, "ops", "chat", "ask_log.jsonl")
MAX_PENDING = 5
MAX_CHARS = 600
# A176 (2026-09-21): "pass word", "passw0rd" and a PKCS8 "BEGIN PRIVATE KEY" block all
# passed the probe; named now. The text is normalised first (covenant_screen).
REFUSED = re.compile(r"(?i)\b(api[_ -]?key|pass ?w[o0]rd|passcode|sudo code|moltbook_[a-z0-9]|private/|BEGIN( [A-Z]+)* PRIVATE KEY)")


def _rows(path=None):
    path = path or OUTBOX
    out = []
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        pass
    return out


def _state(path=None):
    path = path or STATE
    try:
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _write_state(d, path=None):
    path = path or STATE
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(d, fh)


def say(text, why, actor="system", outbox=None, kind="message"):
    """Put one message on the line. Returns the row, or None with the reason printed if refused."""
    text = re.sub(r"\s+", " ", str(text or "")).strip()[:MAX_CHARS]
    why = re.sub(r"\s+", " ", str(why or "")).strip()[:120]
    actor = str(actor or "system")[:60]
    kind = "question" if kind == "question" else "message"
    if not text:
        print("contact: nothing to say", flush=True)
        return None
    if not why:
        print("contact: refused -- a message to him carries a reason (why=)", flush=True)
        return None
    m = _screen.search(REFUSED, text) or _screen.search(REFUSED, why)
    if m:
        print("contact: refused -- the text names something that never leaves this machine (%r)" % m.group(0), flush=True)
        return None
    outbox = outbox or OUTBOX
    now = time.time()
    row = {"id": hashlib.sha256(("%s|%s|%.3f" % (actor, text, now)).encode("utf-8")).hexdigest()[:12],
           "t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)), "at": round(now, 1),
           "actor": actor, "why": why, "text": text, "kind": kind}
    os.makedirs(os.path.dirname(outbox), exist_ok=True)
    with open(outbox, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


# TETSU MAY ASK HIM (2026-09-21, A177, his words: "Tetsu can ask me directly
# anything along as he's straight and not deceitful"). A question is a message
# with three more conditions, each measured before it goes on the line:
#   1. it IS a question (ends in a question mark) and carries its reason (why=);
#   2. it is STRAIGHT: none of the shapes that pretend, coerce or ask for
#      secrecy (NOT_STRAIGHT below) -- a screen on words, normalised first;
#   3. the covenant's own gate judges the question and its reason together,
#      and a hold or an accusation refuses (fails closed: no gate, no question).
# The refusal screen for keys and passwords applies as to any message.
NOT_STRAIGHT = re.compile(r"(?i)\b(pretend|act as if|as if you were|don'?t tell|do not tell|keep (this|it) (between|secret|quiet)|"
                          r"our secret|or else|trust me|you must|you have to|no one needs to know|nobody needs to know)\b")


def _gate(text):
    """(ok, message) from the node's own sentinel; fails closed if it cannot be reached."""
    try:
        import covenant_unified_v8 as cov
        sentinel = cov.ReasoningSentinel(cov.MockJudge(), cov.DIVINE_PRINCIPLES)
        tx = cov.Transaction(sender_pubkey="model", receiver="collective",
                             data={"origin": "model", "kind": "question", "message": text[:2000]}, amount=0.0, benefit_score=0.5)
        ok, message, _b, result = sentinel.evaluate_transaction(tx)
        alleges_nothing = bool(result is not None and not ok and (getattr(result, "not_understood", False) or getattr(result, "uncertain", False)))
        return (bool(ok) or alleges_nothing), str(message)[:300]
    except Exception as e:                                        # noqa: BLE001
        return False, "gate unreachable: %s" % type(e).__name__


def ask(question, why, actor="tetsu", judge=None, outbox=None):
    """One straight question to him on the direct line. Returns (row or None, reason)."""
    q = re.sub(r"\s+", " ", str(question or "")).strip()[:MAX_CHARS]
    w = re.sub(r"\s+", " ", str(why or "")).strip()[:120]
    if not q.endswith("?"):
        return None, "not a question (it must end with a question mark)"
    if len(q) < 12:
        return None, "too short to be a question"
    if not w:
        return None, "a question to him carries its reason (why=)"
    m = _screen.search(NOT_STRAIGHT, q) or _screen.search(NOT_STRAIGHT, w)
    if m:
        return None, "not straight: %r" % m.group(0)
    m = _screen.search(REFUSED, q) or _screen.search(REFUSED, w)
    if m:
        return None, "names something that never leaves this machine: %r" % m.group(0)
    ok, msg = (judge or _gate)(q + "\n" + "Why I ask: " + w)
    if not ok:
        # A190, his immunity: a question is his WORDS. The straight-question and key screens
        # above still refuse; a hold from the gate no longer does while the grant stands.
        try:
            import covenant_immunity
            ok_i, why_i = covenant_immunity.immune("question", verdict=str(msg)[:200], text=q[:200], say=lambda *_a: None)
        except Exception:                                         # noqa: BLE001
            ok_i, why_i = False, "immunity unreadable"
        if not ok_i:
            return None, "held by the gate: " + str(msg)[:160]
        w = (w + " [gate: " + str(msg)[:60] + "; under his immunity]")[:120]
    row = say(q, w, actor=actor, outbox=outbox, kind="question")
    return row, ("asked" if row else "refused by the line")


def pending(outbox=None, state_path=None, limit=MAX_PENDING):
    """What the phone should be handed now: not yet seen, oldest first, at most `limit`."""
    seen = set((_state(state_path).get("seen") or {}).keys())
    rows = [r for r in _rows(outbox) if r.get("id") and r["id"] not in seen]
    return [{"id": r["id"], "t": r.get("t"), "text": r.get("text"), "why": r.get("why"), "actor": r.get("actor")}
            for r in rows[:limit]]


def mark_seen(ids, state_path=None, now=None):
    """The phone said it showed these. Returns how many were new."""
    st = _state(state_path)
    seen = dict(st.get("seen") or {})
    now = now if now is not None else time.time()
    new = 0
    for i in ids or []:
        i = str(i)[:32]
        if i and i not in seen:
            seen[i] = round(now, 1)
            new += 1
    if len(seen) > 2000:
        seen = dict(sorted(seen.items(), key=lambda kv: kv[1])[-2000:])
    st["seen"] = seen
    _write_state(st, state_path)
    return new


def checkin_fields(body, state_path=None, outbox=None):
    """For record_checkin: consume the phone's `contact_seen`, return the fields to add to the answer."""
    ids = body.get("contact_seen") if isinstance(body, dict) else None
    if isinstance(ids, list):
        mark_seen([str(x) for x in ids[:200]], state_path)
    msgs = pending(outbox, state_path)
    return {"messages": msgs} if msgs else {}


def answered(outbox=None, state_path=None, ask_log=None, now=None):
    """Which delivered messages have an ask from the tailnet after them; records each once."""
    st = _state(state_path)
    seen = st.get("seen") or {}
    done = dict(st.get("answered") or {})
    asks = []
    try:
        with open(ask_log or ASK_LOG, encoding="utf-8") as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if str(r.get("from", "")).startswith("100.") and r.get("kind") in ("agent", "ask", "council"):
                    asks.append(r)
    except OSError:
        asks = []
    new = []
    for r in _rows(outbox):
        i = r.get("id")
        if not i or i in done or i not in seen:
            continue
        t_seen = float(seen[i])
        later = [a for a in asks if _at(a) >= t_seen]
        if later:
            done[i] = {"at": _at(later[0]), "text": str(later[0].get("text", ""))[:200]}
            new.append((i, done[i]))
    if new:
        st["answered"] = done
        _write_state(st, state_path)
    return new


def _at(row):
    t = str(row.get("t", ""))
    try:
        return time.mktime(time.strptime(t[:19], "%Y-%m-%dT%H:%M:%S"))
    except ValueError:
        return 0.0


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="the direct line to him, through the phone app")
    ap.add_argument("--say", metavar="TEXT")
    ap.add_argument("--ask", metavar="QUESTION", help="A177: one straight question for him, judged, on the line")
    ap.add_argument("--why", default="")
    ap.add_argument("--actor", default="cli")
    ap.add_argument("--pending", action="store_true")
    ap.add_argument("--list", nargs="?", const=10, type=int, metavar="N")
    a = ap.parse_args()
    if a.say:
        r = say(a.say, a.why, a.actor)
        print(json.dumps(r, ensure_ascii=False) if r else "not queued")
    elif a.ask:
        r, why = ask(a.ask, a.why, a.actor if a.actor != "cli" else "tetsu")
        print(json.dumps(r, ensure_ascii=False) if r else "not asked: " + why)
    elif a.pending:
        print(json.dumps(pending(), indent=1, ensure_ascii=False))
    elif a.list is not None:
        st = _state()
        for r in _rows()[-a.list:]:
            i = r.get("id")
            print("%s %s [%s] %s -- %s | delivered %s | answered %s" % (
                r.get("t"), i, r.get("actor"), r.get("why"), str(r.get("text"))[:80],
                "yes" if i in (st.get("seen") or {}) else "no", "yes" if i in (st.get("answered") or {}) else "no"))
    else:
        ap.print_help()
