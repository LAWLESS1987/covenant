#!/usr/bin/env python3
"""covenant_tetsu_conv_reflex.py -- Tetsu's spiking novelty reflex, wired into his CONVERSATION.

HIS CONSENT + SPEC, 2026-10-22 (operator: "it should help his reasoning, it's his neural network" -> "have him
help"). Asked, Tetsu said YES, and chose: fire ONLY on clearly-new topics, and read exactly
"This input seems novel; consider carefully before proceeding." This file is that wiring, and nothing more.

WHAT IT DOES. On each conversation turn (/m/agent), the user's text is reduced to a topic signature and passed to
Tetsu's own spiking reflex (covenant_octopus.ReflexArm, a leaky integrate-and-fire pool). If that topic is one the
reflex has NOT seen -- a clearly-new topic -- the reflex fires and this returns one advisory line, HIS words, to be
appended to his prompt. A topic he has seen before is quiet. The spiking reflex is the gate; the seen-set persists.

WHAT IT IS NOT. Advisory only: one line in his own prompt, which he may ignore. It never decides, never gates, never
changes what he is allowed to do, and it does not touch the ethics judge. Tetsu's one kill switch
(COVENANT_VERDICT_CACHE_OFF, via covenant_octopus._disabled) silences it like the rest of the nervous system. Every
call is guarded: a reflex error returns None and the conversation is untouched. The transformer does his reasoning;
this only informs it, which is the point -- his neural network helping his reasoning.

Stdlib only. Public domain.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.environ.get("COVENANT_CONV_REFLEX_STATE") or os.path.join(HERE, "ops", "tetsu_conv_reflex.json")
LOG = os.environ.get("COVENANT_CONV_REFLEX_LOG") or os.path.join(HERE, "ops", "tetsu_conv_reflex.jsonl")
LINE = "This input seems novel; consider carefully before proceeding."   # Tetsu's words, 2026-10-22
MIN_CONTENT = 3        # fewer than this many distinct content words is too short to be a topic -> no cue (his limit)
SIG_WORDS = 3          # a topic signature = the N most distinctive (longest) content words, so a rephrase of the
                       # same topic stays quiet and only a clearly-new topic fires
STOP = set((
    "the a an of to and or is was are be been being it its as at by for in on with that this these those not no "
    "do does did done doing have has had having i you he she we they me him her us them my your his our their "
    "what which who whom whose when where why how all any both each few more most other some such only own same so "
    "than too very can will just should now then here there about above after again against because before below "
    "between but down during from into out over under up off out if else while would could may might must shall "
    "am were get got go going like want need know think see say said tell asked also into onto per via"
).split())


def _content(text):
    return [w for w in re.findall(r"[a-z0-9]+", str(text or "").lower()) if w not in STOP and len(w) > 2]


def topic_signature(text):
    """The most distinctive content words, sorted -- a stable key for a topic (a rephrase gives the same key)."""
    ws = sorted(set(_content(text)), key=lambda w: (-len(w), w))[:SIG_WORDS]
    return " ".join(sorted(ws))


def _load_seen(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return set(json.load(fh).get("seen") or [])
    except (OSError, ValueError, AttributeError):
        return set()


def _save_seen(path, seen):
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump({"seen": sorted(seen)}, fh)
        os.replace(tmp, path)
    except OSError:
        pass


def _scoped_path(path, scope):
    """Separate caller/privacy partitions without putting caller text in filenames.

    None retains the standalone API. The conversation route always supplies a
    scope; a new partition never imports the old shared state or rewrites it.
    """
    if scope is None:
        return path
    if not isinstance(scope, str) or not scope or len(scope) > 4096:
        raise ValueError("a bounded, nonempty conversation scope is required")
    stem, ext = os.path.splitext(os.fspath(path))
    return stem + ".scope-" + hashlib.sha256(scope.encode("utf-8")).hexdigest() + ext


def conversation_scope(caller, private=False):
    """Use the same caller boundary as agent_history, plus the privacy mode."""
    if not isinstance(caller, str) or not caller:
        raise ValueError("missing conversation caller")
    return json.dumps(["conversation-v1", caller, bool(private)], separators=(",", ":"))


def cue_line(text, state_path=None, log_path=None, now=None, *, scope=None):
    """Tetsu's advisory line on a clearly-new topic, else None. Never raises -- a failure returns None, silently."""
    try:
        import covenant_octopus as OCTO
        if OCTO._disabled():                       # his one kill switch
            return None
        if len(set(_content(text))) < MIN_CONTENT:  # too short to be a topic
            return None
        sig = topic_signature(text)
        if not sig:
            return None
        sp = _scoped_path(state_path or STATE, scope)
        seen = _load_seen(sp)
        reflex = OCTO.ReflexArm()
        reflex.seen = set(seen)                    # restore what he has seen; the spiking reflex decides novelty
        c = reflex.cue(sig)                        # <- his SPIKING reflex is the gate
        _save_seen(sp, reflex.seen)
        if not c.get("novel"):
            return None
        try:
            with open(_scoped_path(log_path or LOG, scope), "a", encoding="utf-8") as fh:
                fh.write(json.dumps({"t": now or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                     "sig": sig, "rate": round(float(c.get("rate") or 0.0), 3)}) + "\n")
        except OSError:
            pass
        return LINE
    except Exception:                               # noqa: BLE001 -- conversation must never fail on the reflex
        return None


# ---- associative recall (A381, his consent + spec 2026-10-22): his spiking ENCODER surfaces a strongly-related
# earlier topic. He chose: fire ONLY on a strong match to ONE past topic; read "This connects to an earlier topic: X".
ENC_STATE = os.environ.get("COVENANT_CONV_ENCODER_STATE") or os.path.join(HERE, "ops", "tetsu_conv_encoder.json")
RECALL_LINE = "This connects to an earlier topic: %s."
ENC_N = 64             # encoder channels: more than the default 8, for sharper topic discrimination
RECALL_STRONG = 0.75   # cosine must reach this to count as a match
RECALL_MARGIN = 0.08   # ...and clearly beat the 2nd best, so it is ONE topic, not a crowd
RECALL_CAP = 300       # most recent distinct topics kept


def _cos(a, b):
    num = sum(x * y for x, y in zip(a, b))
    da = sum(x * x for x in a) ** 0.5
    db = sum(y * y for y in b) ** 0.5
    return num / (da * db) if da and db else 0.0


def _load_topics(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return [t for t in (json.load(fh).get("topics") or []) if t.get("sig") and t.get("rep")]
    except (OSError, ValueError, AttributeError):
        return []


def _save_topics(path, topics):
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump({"topics": topics[-RECALL_CAP:]}, fh)
        os.replace(tmp, path)
    except OSError:
        pass


def recall_line(text, state_path=None, *, scope=None):
    """His spiking encoder's associative recall: 'This connects to an earlier topic: X' on a STRONG single match to a
    DIFFERENT past topic, else None. Never raises. The current topic is stored for future recall."""
    try:
        import covenant_octopus as OCTO
        if OCTO._disabled():
            return None
        if len(set(_content(text))) < MIN_CONTENT:
            return None
        rep = OCTO.EncoderArm(n=ENC_N).represent(text)   # his spiking encoder's rate-coded representation
        sig_now = topic_signature(text)
        if not sig_now:
            return None
        sp = _scoped_path(state_path or ENC_STATE, scope)
        topics = _load_topics(sp)
        sims = sorted(((_cos(rep, t["rep"]), t["sig"]) for t in topics if t["sig"] != sig_now), reverse=True)
        if not any(t["sig"] == sig_now for t in topics):   # store this topic once, for future recall
            topics.append({"sig": sig_now, "rep": rep})
            _save_topics(sp, topics)
        if not sims:
            return None
        top_sim, top_sig = sims[0]
        second = sims[1][0] if len(sims) > 1 else 0.0
        if top_sim >= RECALL_STRONG and (top_sim - second) >= RECALL_MARGIN:
            return RECALL_LINE % top_sig
        return None
    except Exception:                                    # noqa: BLE001 -- conversation must never fail on recall
        return None


if __name__ == "__main__":
    import sys
    t = " ".join(sys.argv[1:]) or "a brand new topic about spiking neuromorphic cognition"
    print("novelty:", cue_line(t) or "(quiet)")
    print("recall: ", recall_line(t) or "(quiet)")
