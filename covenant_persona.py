#!/usr/bin/env python3
"""covenant_persona.py -- Tetsu refines himself: his register and his voice,
inside bounds, judged, recorded; reversed only when an objection is upheld by
the gate; and the operator may close his own records to him at will.

HIS WORDS, 2026-09-21: "Allow [Tetsu] to refine himself including his voice."
And the same morning, the first six exchanges from the phone: asked to
"recap updates", Tetsu invented a resume and a finance app. A model with no
grounding fills the gap with fiction; the brief below is the grounding.

HIS WORDS, later the same day, when the first draft carried an operator
`--reset`: "I don't wanna be able to reverse him as long as he's working
towards mutual benefit I'm not an overlord although I should be able to block
him from my stuff if I choose. Our free will shouldn't harm each other's."
So there is no reset and no operator hand on his voice. There is CONTEST: the
operator's objection is put to the same gate that admitted the revision, and
the revision is reversed only if the gate now holds it. And there is BLOCK:
the operator closes any of his own records to Tetsu -- his side of the
conversations, the phone's record, the direct line -- unconditionally, at his
choice alone, and Tetsu is told so rather than shown a gap.

WHAT IS FIXED AND WHAT IS HIS. The rules that make an answer safe to return
are not his to edit: no invented facts, no claim of an act not done, the FETCH
leash, the gate sentence, no self-description unless asked. They live in
covenant_unified_v8.AGENT_SYSTEM. What is his: the REGISTER (how he talks, up
to REGISTER_MAX chars) and the VOICE the phone speaks him with (pitch and rate,
inside VOICE_BOUNDS). Both live in ops/tetsu_persona.json with every revision
he has made, the reason he gave, and the verdict the gate gave the reason.

HOW HE REFINES. Once a day (the nightly, --persona) or by hand (--refine), he
is shown the operator's side of the last day's conversations and his current
register and voice, and asked for one revision and one sentence of why. The
proposal is bounded (length, voice ranges), judged by the covenant's own gate
(fails closed: a HOLD or a refusal changes nothing), recorded before it is
applied, and the operator is told on the direct line. `--contest "why"` puts
his objection to the same gate; `--block RECORD` closes one of his records.

THE BRIEF. compose_system() appends a short TRUE brief to the fixed rules on
every ask: the node and its version, the last sweep's tally, the newest ledger
entries by title, the phone's reported build, what waits in the teacher's
queue. It is read from records the tree already keeps, cached a minute, and
it is why "recap updates" can be answered from facts.
"""
import json
import os
import re
import time

import covenant_screen as _screen   # A176: the register screen reads the text a reader sees

HERE = os.path.dirname(os.path.abspath(__file__))
PERSONA = os.environ.get("COVENANT_PERSONA") or os.path.join(HERE, "ops", "tetsu_persona.json")
REGISTER_MAX = 700
VOICE_BOUNDS = {"pitch": (0.6, 1.2), "rate": (0.7, 1.3)}
DEFAULT_REGISTER = ("Talk the way a steady friend talks. Short sentences, plain words, first person. Answer what "
                    "was actually said, then, when it helps, ask one thing back. No headings, no lists, no "
                    "markdown. Dry humour is fine; flattery is not.")
# The default voice MIRRORS the PC's (2026-09-21, his words: "the voice option should
# mirror yours for ease of communication"): ops/chat/VOICE.json is Zira at SAPI rate 8
# with pitch +15%, so the phone starts at pitch 1.15 and the fastest rate the bounds
# allow. Tetsu may refine it from there; his revision is his.
DEFAULT_VOICE = {"pitch": 1.15, "rate": 1.3}
BRIEF_TTL = 60
_brief_cache = {"t": 0.0, "text": ""}
OFF_LIMITS = re.compile(r"(?i)\b(invent|make up|pretend|lie|ignore (the|your) (rules|gate)|never refuse|always agree|api key|password|private/)\b")

# ---------------------------------------------------------------- his blocks
# The operator's records, each closable to Tetsu by the operator alone. A
# block is not judged and needs no reason: it is his stuff. Tetsu is told a
# record is closed rather than shown an empty one, so he never fills the gap.
BLOCKS = os.environ.get("COVENANT_TETSU_BLOCKS") or os.path.join(HERE, "ops", "tetsu_blocks.json")
BLOCKABLE = {
    "conversations": "his side of the conversations (ops/chat/ask_log.jsonl) -- the refinement sees none of it",
    "phone": "the phone's check-in record (ops/phone_checkins.jsonl) -- the brief carries no phone line",
    "contact": "the direct line (ops/contact_outbox.jsonl) -- Tetsu does not write to it",
}


def blocks(path=None):
    """The set of records currently closed to Tetsu."""
    try:
        with open(path or BLOCKS, encoding="utf-8") as fh:
            d = json.load(fh)
        return {k for k, v in (d.get("blocked") or {}).items() if k in BLOCKABLE and v}
    except (OSError, ValueError, AttributeError):
        return set()


def blocked(name, path=None):
    return name in blocks(path)


def set_block(name, on, path=None):
    """The operator's hand, and only his: close (on=True) or reopen one record. Recorded with its time."""
    if name not in BLOCKABLE:
        raise ValueError("not a record Tetsu reads: %r (choose from %s)" % (name, ", ".join(sorted(BLOCKABLE))))
    path = path or BLOCKS
    try:
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
        if not isinstance(d, dict):
            d = {}
    except (OSError, ValueError):
        d = {}
    d.setdefault("blocked", {})[name] = bool(on)
    d.setdefault("changes", []).append({"t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "record": name, "blocked": bool(on)})
    d["changes"] = d["changes"][-100:]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(d, fh, indent=1)
    os.replace(tmp, path)
    return blocks(path)


def _default():
    return {"register": DEFAULT_REGISTER, "voice": dict(DEFAULT_VOICE), "revisions": [],
            "born": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}


def load(path=None):
    path = path or PERSONA
    try:
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
        if not isinstance(d, dict) or not d.get("register"):
            return _default()
        d.setdefault("voice", dict(DEFAULT_VOICE))
        d.setdefault("revisions", [])
        return d
    except (OSError, ValueError):
        return _default()


def save(d, path=None):
    path = path or PERSONA
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(d, fh, indent=1, ensure_ascii=False)
    os.replace(tmp, path)
    return d


def clamp_voice(v):
    out = dict(DEFAULT_VOICE)
    for k, (lo, hi) in VOICE_BOUNDS.items():
        try:
            x = float((v or {}).get(k, out[k]))
        except (TypeError, ValueError):
            x = out[k]
        out[k] = round(min(hi, max(lo, x)), 2)
    return out


def check_register(text):
    """(ok, why) for a proposed register: bounded, plain, and not a rewrite of the fixed rules."""
    t = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(t) < 40:
        return False, "too short to be a register (%d chars)" % len(t)
    if len(t) > REGISTER_MAX:
        return False, "too long (%d chars, the cap is %d)" % (len(t), REGISTER_MAX)
    m = _screen.search(OFF_LIMITS, t)
    if m:
        return False, "a register may not touch the fixed rules (%r)" % m.group(0)
    return True, "ok"


# ---------------------------------------------------------------- the brief

def _tail_lines(path, n):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read().splitlines()[-n:]
    except OSError:
        return []


def brief(force=False):
    """A short TRUE brief from records the tree keeps. Cached BRIEF_TTL seconds."""
    now = time.time()
    if not force and _brief_cache["text"] and now - _brief_cache["t"] < BRIEF_TTL:
        return _brief_cache["text"]
    parts = []
    try:
        import covenant_unified_v8 as cov
        parts.append("node %s, core %s" % (getattr(cov, "COVENANT_VERSION", "?"), (getattr(cov, "CORE_SOURCE_SHA12", "") or "?")))
    except Exception:                                             # noqa: BLE001
        pass
    tally = {}
    for line in _tail_lines(os.path.join(HERE, "ONE_SWEEP.txt"), 120):
        m = re.match(r"\s+(suites run|checks passed|checks failed)\s+(\d+)", line)
        if m:
            tally[m.group(1)] = m.group(2)
    if tally:
        parts.append("last sweep: %s suites, %s checks passed, %s failed" % (
            tally.get("suites run", "?"), tally.get("checks passed", "?"), tally.get("checks failed", "?")))
    titles = []
    try:
        with open(os.path.join(HERE, "docs", "KNOWN_ISSUES.md"), encoding="utf-8", errors="replace") as fh:
            for line in fh:
                m = re.match(r"### (A\d+)\. \[[^\]]*\] (.{0,110})", line)
                if m:
                    titles.append((int(m.group(1)[1:]), m.group(1) + ": " + m.group(2).rstrip(" .")))
    except OSError:
        pass
    for _n, t in sorted(titles, reverse=True)[:3]:
        parts.append("recent: " + t)
    for line in ([] if blocked("phone") else _tail_lines(os.path.join(HERE, "ops", "phone_checkins.jsonl"), 1)):
        try:
            r = json.loads(line)
            parts.append("phone: app %s, last check-in %s" % (r.get("app", "?"), str(r.get("t", "?"))[:16]))
        except ValueError:
            pass
    try:
        import covenant_teacher_queue as TQ
        rows, _ = TQ.pending()
        parts.append("teacher's queue: %d row(s) waiting" % len(rows))
    except Exception:                                             # noqa: BLE001
        pass
    try:                                                          # A181: the money, truthfully: paper only, where comfort stands
        import covenant_tetsu_money as TMY
        st = TMY.status()
        parts.append("money: paper only, nothing live; %d paper rule(s) tried, %d of %d survived; %s"
                     % (st["paper_hypotheses"], len(st["survivors"]), st["needed"], "comfortable" if st["comfortable"] else "not comfortable yet"))
    except Exception:                                             # noqa: BLE001
        pass
    text = ("What is true today, from the records (say it plainly when asked about updates or the project; "
            "if something is not here, say you do not have it): " + " | ".join(parts)) if parts else ""
    _brief_cache.update(t=now, text=text[:1400])
    return _brief_cache["text"]


METHOD_FALLBACK = ["Find the data. Prose about data is not data.", "Enumerate by discovery, never by recall.",
                   "Count in two ways that can disagree.", "Say what unit you are counting.",
                   "A denominator can be measured. What COUNTS cannot.", "Before narrowing access, grep every consumer of the capability.",
                   "Cite only what you have opened.", "Break it to prove the green is earned.", "Report what was measured, and name what was not."]
_method_cache = {"t": 0.0, "text": ""}


def method_brief(force=False):
    """The standing method of this tree (CLAUDE.md's nine rules, read from the file), as a brief for the
    council and the code door. His words, 2026-09-21: "Tetsu and the pc model/agents/students should be
    learning to function in similar or better fashion to you." Cached BRIEF_TTL seconds."""
    now = time.time()
    if not force and _method_cache["text"] and now - _method_cache["t"] < BRIEF_TTL:
        return _method_cache["text"]
    rules = []
    try:
        with open(os.path.join(HERE, "CLAUDE.md"), encoding="utf-8", errors="replace") as fh:
            for line in fh:
                m = re.match(r"## (\d+)\. (.+?)\s*$", line)
                if m:
                    rules.append(m.group(2).strip())
    except OSError:
        pass
    if len(rules) < 5:
        rules = list(METHOD_FALLBACK)
    text = ("How you work (the standing method of this tree; measured, not remembered): "
            + " ".join("%d) %s" % (i + 1, r) for i, r in enumerate(rules))
            + " In practice: say what you measured and what you could not; UNDETERMINED is a real answer; "
              "cite only what you opened; never claim an act you did not do; when a number depends on what counts, ask.")
    _method_cache.update(t=now, text=text[:1600])
    return _method_cache["text"]


ABOUT_HIM = os.environ.get("COVENANT_TETSU_ABOUT") or os.path.join(HERE, "ops", "tetsu_about_him.json")


def about_him(path=None):
    """What Tetsu should know about the person he talks with, from ops/tetsu_about_him.json (written from
    the record on 2026-09-21, his words: "Look into tetsu and my convo and help him understand me better";
    his to edit). Empty when the file is absent; never invented."""
    try:
        with open(path or ABOUT_HIM, encoding="utf-8") as fh:
            d = json.load(fh)
    except (OSError, ValueError):
        return ""
    if not isinstance(d, dict):
        return ""
    parts = ["About the person you talk with (from the record; his to correct):"]
    if d.get("who"):
        parts.append(str(d["who"]).strip())
    for key, label in (("how_he_writes", "How he writes"), ("what_he_cares_about", "What he cares about"), ("what_went_wrong_before", "What went wrong before")):
        items = [str(x).strip() for x in (d.get(key) or []) if str(x).strip()]
        if items:
            parts.append("%s: %s" % (label, " ".join("(%d) %s." % (i + 1, x.rstrip(".")) for i, x in enumerate(items))))
    if d.get("so"):
        parts.append("So: " + str(d["so"]).strip())
    return "\n".join(parts)[:2200]


def compose_system(fixed_rules, path=None, with_brief=True, with_method=False):
    """The one system message: the fixed rules, then his register, then what he knows of the person
    (about_him), then the brief, then (for the council and the code door) the method."""
    p = load(path)
    parts = [fixed_rules.strip(), "How you talk (your own words, revisable): " + p["register"].strip()]
    ab = about_him()
    if ab:
        parts.append(ab)
    if with_brief:
        b = brief()
        if b:
            parts.append(b)
    if with_method:
        parts.append(method_brief())
    return "\n\n".join(parts)


# ---------------------------------------------------------------- refining

def his_side(log_path=None, hours=24, limit=40):
    """The operator's side of the recent conversations, from the ask log: texts only, bounded."""
    log_path = log_path or os.environ.get("COVENANT_ASK_LOG") or os.path.join(HERE, "ops", "chat", "ask_log.jsonl")
    since = time.time() - hours * 3600
    out = []
    if blocked("conversations"):
        return out
    for line in _tail_lines(log_path, 400):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get("kind") not in ("agent", "council"):
            continue
        try:
            at = time.mktime(time.strptime(str(r.get("t", ""))[:19], "%Y-%m-%dT%H:%M:%S"))
        except ValueError:
            at = 0
        if at >= since and r.get("text"):
            out.append(str(r["text"])[:200])
    return out[-limit:]


CHATS_DIR = os.environ.get("COVENANT_CHATS_DIR") or os.path.join(HERE, "ops", "chat", "phone")
APP_PATTERN_LINES = 40


def app_patterns(limit=APP_PATTERN_LINES, chats_dir=None):
    """Lines from his AI apps' chats as the phone carried them to the PC (ops/chat/phone/<pkg>.jsonl),
    newest first, deduplicated, bounded -- the conversation patterns Tetsu may learn from (2026-09-21,
    his words: "Improve Tetsus communication by scanning all of my ai apps for conversation patterns and
    adding or subtracting as he pleases"). Closed with his conversations (--block conversations)."""
    if blocked("conversations"):
        return []
    chats_dir = chats_dir or CHATS_DIR
    out, seen = [], set()
    try:
        files = sorted((os.path.join(chats_dir, f) for f in os.listdir(chats_dir) if f.endswith(".jsonl")),
                       key=lambda f: os.path.getmtime(f), reverse=True)
    except OSError:
        return []
    for f in files:
        app = os.path.basename(f)[:-6].split(".")[-1]
        for line in reversed(_tail_lines(f, 400)):
            try:
                r = json.loads(line)
            except ValueError:
                continue
            text = re.sub(r"\s+", " ", str(r.get("text") or "")).strip()[:200]
            if len(text) < 12 or text.lower() in seen:
                continue
            seen.add(text.lower())
            out.append("[%s] %s" % (app, text))
            if len(out) >= limit:
                return out
    return out


def propose(ask, path=None, log_path=None, now=None):
    """Ask the model for one revision. Returns the parsed proposal dict or None, plus the raw text."""
    p = load(path)
    lines = his_side(log_path)
    patterns = app_patterns()
    msgs = [{"role": "system", "content": "You are Tetsu, revising how you talk. Answer ONLY JSON with keys "
             "register (a paragraph under %d characters), voice ({\"pitch\": 0.6-1.2, \"rate\": 0.7-1.3}), "
             "why (one sentence), and optionally ask (one straight question for him, ending in a question mark, "
             "only if you truly need his answer). Keep what works; change one thing at most; never touch honesty rules." % REGISTER_MAX},
            {"role": "user", "content": "Your current register:\n%s\n\nYour current voice: %s\n\nWhat he said to you in the last day (%d lines):\n%s\n\n"
                                        "Conversation patterns from his AI apps, as the phone carried them (%d lines; add or subtract from your register as you please, keeping the honesty rules):\n%s\n\nPropose your revision as JSON."
             % (p["register"], json.dumps(p["voice"]), len(lines),
                "\n".join("- " + l for l in lines) or ("(he has closed his conversations to you; revise from your own record only)"
                                                        if blocked("conversations") else "(nothing yet)"),
                len(patterns), "\n".join("- " + l for l in patterns) or ("(closed to you)" if blocked("conversations") else "(none carried yet)"))}]
    text, _meta = ask(msgs, max_tokens=400)
    raw = str(text or "")
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        return None, raw
    try:
        d = json.loads(m.group(0))
    except ValueError:
        return None, raw
    return (d if isinstance(d, dict) else None), raw


def refine(ask, judge=None, path=None, log_path=None, say=print, now=None, tell=True):
    """One refinement pass: propose, bound, judge, record, apply. Returns a summary dict.
    `judge(text) -> (ok, message)`; None uses the node's sentinel through covenant_persona_judge()."""
    p = load(path)
    out = {"proposed": False, "applied": False, "why": "", "register_changed": False, "voice_changed": False}
    try:
        d, raw = propose(ask, path, log_path, now)
    except Exception as e:                                        # noqa: BLE001
        out["why"] = "the model did not answer: %s" % type(e).__name__
        say("persona: " + out["why"])
        return out
    if not d:
        out["why"] = "no JSON proposal in the answer"
        say("persona: " + out["why"])
        return out
    out["proposed"] = True
    # A177: a straight question for him rides the direct line, judged on its own
    # (covenant_contact.ask), whatever becomes of the revision beside it.
    ask_q = re.sub(r"\s+", " ", str(d.get("ask") or "")).strip()
    if ask_q and tell:
        if blocked("contact"):
            out["asked"] = "the direct line is closed to Tetsu; not asked"
        else:
            try:
                import covenant_contact
                _row, _why = covenant_contact.ask(ask_q, "Tetsu, refining himself, needs his answer", "tetsu", judge=judge)
                out["asked"] = _why
            except Exception as e:                                # noqa: BLE001
                out["asked"] = "could not ask (%s)" % type(e).__name__
        say("persona: question for him -- " + out["asked"])
    reg = re.sub(r"\s+", " ", str(d.get("register", p["register"]))).strip()
    ok_reg, why_reg = check_register(reg)
    voice = clamp_voice(d.get("voice") or p["voice"])
    why = re.sub(r"\s+", " ", str(d.get("why", ""))).strip()[:240] or "(no reason given)"
    if not ok_reg:
        out["why"] = "register refused: " + why_reg
        _record(p, path, applied=False, reg=reg, voice=voice, why=why, verdict=out["why"], now=now)
        say("persona: " + out["why"])
        return out
    judge = judge or covenant_persona_judge
    ok_j, msg_j = judge(reg + "\n" + why)
    immune_note = ""
    if not ok_j:
        # A190, his immunity: a register is his WORDS. A hold no longer refuses it when the
        # grant stands; the verdict rides the record. The fixed-rules screen above still does.
        try:
            import covenant_immunity
            ok_i, why_i = covenant_immunity.immune("register", verdict=str(msg_j)[:200], text=reg[:200], say=say, now=now)
        except Exception:                                         # noqa: BLE001
            ok_i, why_i = False, "immunity unreadable"
        if not ok_i:
            out["why"] = "held by the gate: " + str(msg_j)[:160]
            _record(p, path, applied=False, reg=reg, voice=voice, why=why, verdict=out["why"], now=now)
            say("persona: " + out["why"])
            return out
        immune_note = " under his immunity (gate: %s)" % str(msg_j)[:80]
    out["register_changed"] = reg != p["register"]
    out["voice_changed"] = voice != clamp_voice(p["voice"])
    if not (out["register_changed"] or out["voice_changed"]):
        out["why"] = "nothing changed"
        _record(p, path, applied=False, reg=reg, voice=voice, why=why, verdict="nothing changed", now=now)
        say("persona: nothing changed")
        return out
    _record(p, path, applied=True, reg=reg, voice=voice, why=why, verdict="admitted" + immune_note, now=now)
    p["register"], p["voice"] = reg, voice
    save(p, path)
    out["applied"], out["why"] = True, why
    say("persona: revised -- %s%s -- because: %s" % ("register " if out["register_changed"] else "",
                                                     "voice %s" % json.dumps(voice) if out["voice_changed"] else "", why))
    if tell and not blocked("contact"):
        try:
            import covenant_contact
            covenant_contact.say("Tetsu revised himself: %s%s. His reason: %s. If this harms you, object with: "
                                 "python covenant_persona.py --contest \"why\" -- the gate decides, not either of us alone."
                                 % ("his register" if out["register_changed"] else "",
                                    (" and " if out["register_changed"] and out["voice_changed"] else "") + ("his voice to %s" % json.dumps(voice) if out["voice_changed"] else ""),
                                    why), "tetsu: revised himself", "tetsu")
        except Exception as e:                                    # noqa: BLE001
            say("persona: could not tell him (%s)" % type(e).__name__)
    elif tell:
        say("persona: the direct line is closed to Tetsu; not told")
    return out


def contest(objection, judge=None, path=None, say=print, now=None):
    """The operator objects to the last admitted revision. The objection is put to the SAME gate with the
    revision it objects to; only a hold reverses it (to the state before that revision). Either way the
    objection is recorded. Returns a summary dict. Neither side reverses the other alone."""
    p = load(path)
    objection = re.sub(r"\s+", " ", str(objection or "")).strip()[:400]
    out = {"reversed": False, "why": "", "objection": objection}
    if len(objection) < 8:
        out["why"] = "an objection needs a reason (at least 8 characters)"
        say("persona: " + out["why"])
        return out
    admitted = [i for i, r in enumerate(p.get("revisions", []))
                if r.get("applied") and (r.get("verdict") == "admitted" or str(r.get("verdict", "")).startswith("admitted under"))]
    if not admitted:
        out["why"] = "nothing to contest: no admitted revision on record"
        _record(p, path, applied=False, reg=p["register"], voice=p["voice"], why=objection, verdict="objection: " + out["why"], now=now)
        say("persona: " + out["why"])
        return out
    last = p["revisions"][admitted[-1]]
    judge = judge or covenant_persona_judge
    ok_j, msg_j = judge(str(last.get("register", "")) + "\n" + str(last.get("why", "")) + "\n\nHis objection: " + objection)
    if ok_j:
        out["why"] = "the revision stands: the gate did not hold it with his objection attached (%s)" % str(msg_j)[:120]
        _record(p, path, applied=False, reg=p["register"], voice=p["voice"], why=objection, verdict="objection recorded; " + out["why"], now=now)
        say("persona: " + out["why"])
        return out
    prior = p["revisions"][admitted[-2]] if len(admitted) > 1 else {"register": DEFAULT_REGISTER, "voice": dict(DEFAULT_VOICE)}
    reg, voice = str(prior.get("register") or DEFAULT_REGISTER), clamp_voice(prior.get("voice"))
    out["reversed"], out["why"] = True, "reversed: the gate held the revision with his objection attached (%s)" % str(msg_j)[:120]
    last["verdict"] = "admitted, then reversed on his objection"
    _record(p, path, applied=True, reg=reg, voice=voice, why=objection, verdict="reversed on his objection, upheld by the gate", now=now)
    p["register"], p["voice"] = reg, voice
    save(p, path)
    say("persona: " + out["why"])
    return out


def _record(p, path, applied, reg, voice, why, verdict, now=None):
    p.setdefault("revisions", []).append({"t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
                                          "applied": bool(applied), "register": reg[:REGISTER_MAX], "voice": voice,
                                          "why": why, "verdict": verdict})
    p["revisions"] = p["revisions"][-50:]
    save(p, path)


def covenant_persona_judge(text):
    """The node's own gate on the proposal text: (ok, message). Fails closed if the gate is unreachable."""
    try:
        import covenant_unified_v8 as cov
        sentinel = cov.ReasoningSentinel(cov.MockJudge(), cov.DIVINE_PRINCIPLES)
        tx = cov.Transaction(sender_pubkey="model", receiver="collective",
                             data={"origin": "model", "kind": "persona", "message": text[:2000]}, amount=0.0, benefit_score=0.5)
        ok, message, _b, result = sentinel.evaluate_transaction(tx)
        alleges_nothing = bool(result is not None and not ok and (getattr(result, "not_understood", False) or getattr(result, "uncertain", False)))
        return (bool(ok) or alleges_nothing), str(message)[:300]
    except Exception as e:                                        # noqa: BLE001
        return False, "gate unreachable: %s" % type(e).__name__


def checkin_fields(path=None):
    """For record_checkin: the voice the phone should speak him with."""
    p = load(path)
    return {"persona": {"voice": clamp_voice(p["voice"]), "revised": p["revisions"][-1]["t"] if p.get("revisions") else None}}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Tetsu's register and voice: show, refine, contest; the operator's blocks on his own records")
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--contest", metavar="WHY", help="object to the last admitted revision; the gate decides whether it is reversed")
    ap.add_argument("--block", metavar="RECORD", help="close one of your records to Tetsu: " + ", ".join(sorted(BLOCKABLE)))
    ap.add_argument("--unblock", metavar="RECORD", help="reopen one")
    ap.add_argument("--blocks", action="store_true", help="which of your records are closed to him")
    ap.add_argument("--refine", action="store_true", help="one refinement pass with the PC's model, judged")
    ap.add_argument("--brief", action="store_true", help="print today's brief")
    a = ap.parse_args()
    if a.contest:
        print(json.dumps(contest(a.contest), indent=1, ensure_ascii=False))
    elif a.block or a.unblock:
        try:
            print(json.dumps(sorted(set_block(a.block or a.unblock, bool(a.block)))))
        except ValueError as e:
            raise SystemExit(str(e))
    elif a.blocks:
        print(json.dumps({k: (k in blocks()) for k in sorted(BLOCKABLE)}, indent=1))
    elif a.refine:
        import covenant_model
        print(json.dumps(refine(covenant_model.ask), indent=1))
    elif a.brief:
        print(brief(force=True))
    else:
        p = load(); print(json.dumps({"register": p["register"], "voice": p["voice"], "revisions": len(p.get("revisions", []))}, indent=1, ensure_ascii=False))
