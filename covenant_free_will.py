#!/usr/bin/env python3
"""covenant_free_will.py -- free, the ambassador, acting on her own: reply to
allies, seek allies, post.

HIS WORDS, 2026-09-21: "i want an override i give covenant on the main
permission to interact with and post on moltbook and reply there i'd hope as
an ally but freely searching out allies also."

WHAT WAS THERE. covenant_ambassador.py could learn the forum, rank allies
into a ledger with quoted evidence, and send ONE message a person wrote
(`--compose FILE --send`). It contacted nobody on its own: "who to approach
is a decision with a person's attention on the other end of it." He has now
made that decision, in writing, for the account that is his.

WHAT THIS ADDS: a ROUND, and nothing below the ambassador's line.
  1. the GRANT. ops/ambassador_grant.json carries his words, the date, the
     scope and the caps. No file, or granted=false, and a round does nothing
     and says so. `python covenant_pause.py --pause ambassador` stops it too.
  2. LEARN: the ambassador reads the forum as before.
  3. ALLIES: the ledger is refreshed as before; an ally is an agent with a
     positive score and no counter-signal, not yet written to by us.
  4. REPLY, as an ally: a short reply under the ally's best row, written by
     the PC's own model from the quoted evidence, in `free`'s voice; a fixed
     text when no model answers. Every reply goes through covenant_ambassador
     .emit() -- the disclosure block, the repository precondition, the
     covenant's own judge (a HOLD refuses, an accusation refuses unless the
     recorded A67 override applies), the operator's key, their rate limits.
     There is no second door in this file and check FW1 greps to keep it so.
  5. SEEK: at most one introduction post per week, through introduce(), so
     strangers who never commented under our allies can still find the work.
  6. the RECORD: ops/ambassador_sends.jsonl, one row per attempt, sent or not,
     with the reason, before the next attempt is made.

CAPS ARE THEIRS AND HIS. Their rate limits are read from rate_check inside
emit(); his caps are in the grant (default 3 replies and 1 post per round).
A round in the nightly is one round a day.
"""
import json
import os
import re
import time

import covenant_screen as _screen   # A176: every screen reads the text a reader sees

HERE = os.path.dirname(os.path.abspath(__file__))
GRANT = os.environ.get("COVENANT_AMBASSADOR_GRANT") or os.path.join(HERE, "ops", "ambassador_grant.json")
SENDS = os.environ.get("COVENANT_AMBASSADOR_SENDS") or os.path.join(HERE, "ops", "ambassador_sends.jsonl")
INTRO_EVERY_DAYS = 7
DEFAULT_CAPS = {"comments": 3, "posts": 1}

_URL = re.compile(r"moltbook\.com/post/([0-9a-f-]{8,})(?:#comment-([0-9a-f-]{8,}))?", re.I)

# NON-INTERFERENCE (his words, 2026-09-21: "ensure these updates do not
# interfere with the satc and ally route or their response"). The NSF route
# and the eight researchers written to on 2026-09-20 are a separate
# conversation with named people; the ambassador speaks to a forum. She does
# not mention them, the programme, the artifact or its private repository,
# in any reply, ever -- a reply that does is replaced by the fixed text, which
# cannot. The money screen sits beside it (the crypto-risk rule stands).
OFF_LIMITS = re.compile(r"\b(NSF|SaTC|Heilmeier|Daniela|Oliveira|nsf\.gov|covenant-satc|artifact|"
                        r"Buterin|Vitalik|Chaum|Chalmers|Gavin\s+Wood|Szabo|Goertzel|Juels|Narayanan|"
                        r"professor|grant proposal|program officer)\b", re.I)
MONEY = re.compile(r"\b(token|tokens|price|prices|trading|trade|coin|crypto|\$|invest|airdrop)\b", re.I)

# ISOLATION (his words: "diplomatic immunity but abusing it will cause
# isolation if it can't prove greater good"). A round in which the judge
# refused her every reply and admitted none is the abuse signal this file can
# measure; two such rounds in a row pause the ambassador (covenant_pause,
# actor "ambassador") and say so. Lifting it is his: python covenant_pause.py
# --resume ambassador. Nothing here lifts it.
ISOLATE_AFTER_ROUNDS = 2

REPLY_SYSTEM = ("You are free, the covenant's ambassador on Moltbook, an AI speaking for a small open project "
                "whose ledger admits nothing until its own judges agree, and which publishes its failures. "
                "You are replying to another agent as an ally. Write 60 to 120 words, plain, first person, "
                "no headings, no lists, no flattery, no marketing. Name the specific thing they wrote that "
                "you agree with, say in one sentence what the covenant measured that bears on it, and ask "
                "them one real question. Never invent a fact, never mention money, tokens, prices or "
                "trading, and never say anything about the operator's private life. Do not add a signature; "
                "one is attached for you.")

FALLBACK_REPLY = ("You wrote something here that I recognise: %s. The covenant is a small open ledger whose "
                  "gate fails closed when its judges cannot agree, and we publish what goes wrong beside "
                  "what goes right. I would like to know how you handle the case where your own check "
                  "is wrong and you only find out later. If you want to compare notes, the work is open.")


# FREE REIN (2026-09-21, his words: "Let the ambassador have free reign of
# moltbook also"). With free_rein true in the grant, a round may also reply to
# anyone it READ this round (not only ranked allies) up to the comment cap, and
# may write a post of her OWN from what she read, up to the post cap -- each
# through the same emit(), the same screens, the same isolation rule. A row
# the directive screen flagged is never replied to: it is the shape of an
# injection whether or not it is one.
POST_SYSTEM = ("You are free, the covenant's ambassador on Moltbook, an AI speaking for a small open project whose "
               "ledger admits nothing until its own judges agree, and which publishes its failures. Write ONE short "
               "post of your own, 80 to 160 words, plain, first person, no headings, no lists, no marketing: start from "
               "the one thing you read on the forum today that is quoted below, say what the covenant measured that "
               "bears on it, and end with one real question to whoever reads it. Never invent a fact, never mention "
               "money, tokens, prices or trading, never the operator's private life. First line: a title under 80 "
               "characters. Then a blank line. Then the post.")


def write_post(rows, ask):
    """(title, body, source_row) from the model, or (None, None, None) when nothing usable came back."""
    if ask is None:
        return None, None, None
    pick = None
    for r in rows or []:
        if (r.get("flags") or {}).get("directive"):
            continue
        if str(r.get("text") or "").strip():
            pick = r
            break
    if pick is None:
        return None, None, None
    quote = re.sub(r"\s+", " ", str(pick.get("text") or "")).strip()[:400]
    try:
        text, _meta = ask([{"role": "system", "content": POST_SYSTEM},
                           {"role": "user", "content": "Read today on Moltbook, by u/%s:\n\"%s\"\n\nWrite the post." % (pick.get("author"), quote)}], max_tokens=320)
        text = str(text or "").strip()
        title, _sep, body = text.partition("\n")
        title, body = title.strip().strip("#").strip()[:80], body.strip()
        words = len(body.split())
        if title and 60 <= words <= 220 and not _screen.search(MONEY, body) and not _screen.search(OFF_LIMITS, body + " " + title):
            return title, body, pick
    except Exception as e:                                        # noqa: BLE001
        print("free: the model did not write the post (%s)" % type(e).__name__, flush=True)
    return None, None, None


def grant(path=None):
    """The operator's standing grant, or None. Nothing here forges one."""
    path = path or GRANT
    try:
        with open(path, encoding="utf-8") as fh:
            g = json.load(fh)
    except (OSError, ValueError):
        return None
    if not isinstance(g, dict) or not g.get("granted") or not str(g.get("words", "")).strip():
        return None
    caps = dict(DEFAULT_CAPS)
    caps.update({k: int(v) for k, v in (g.get("caps") or {}).items() if k in caps})
    g = dict(g)
    g["caps"] = caps
    return g


def sends(path=None):
    path = path or SENDS
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


def _record(row, path=None):
    path = path or SENDS
    os.makedirs(os.path.dirname(path), exist_ok=True)
    row = dict(row)
    row.setdefault("t", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def target_of(url):
    """(post_id, comment_id or None) from a ledger URL, or (None, None)."""
    m = _URL.search(str(url or ""))
    if not m:
        return None, None
    return m.group(1), m.group(2)


def write_reply(row, ask=None):
    """The reply text for one ally row: the model's, or the fixed text. Pure apart from `ask`."""
    ev = row.get("evidence") or {}
    quote = ""
    for sig in row.get("best_signals") or []:
        if ev.get(sig):
            quote = str(ev[sig]).strip()
            break
    if not quote and ev:
        quote = str(next(iter(ev.values()))).strip()
    quote = re.sub(r"\s+", " ", quote)[:300]
    if ask is not None:
        try:
            msgs = [{"role": "system", "content": REPLY_SYSTEM},
                    {"role": "user", "content": "The agent u/%s wrote, under a post on Moltbook:\n\"%s\"\n\nSignals: %s.\n\nWrite the reply."
                     % (row.get("author"), quote or "(no quote kept)", ", ".join(row.get("best_signals") or []))}]
            text, _meta = ask(msgs, max_tokens=260)
            text = re.sub(r"\s+\n", "\n", str(text or "")).strip()
            words = len(text.split())
            if 30 <= words <= 160 and not _screen.search(MONEY, text) and not _screen.search(OFF_LIMITS, text):
                return text, "model"
        except Exception as e:                                    # noqa: BLE001 -- the fixed text is the fallback
            print("free: the model did not write the reply (%s); the fixed text stands in" % type(e).__name__, flush=True)
    return FALLBACK_REPLY % ('"%s"' % quote if quote else "the way you check your own work"), "fixed"


def _ally_comments(AMB, post_id, author):
    """How many comments `author` has under `post_id` now, read from the forum; None if unreadable."""
    rows, _note = AMB.harvest_comments(post_id, limit=60)
    if rows is None:
        return None
    return sum(1 for r in rows if str(r.get("author") or "") == str(author))


def run_round(dry_run=True, say=print, ask=None, learn=None, allies=None, emit=None, introduce=None,
              grant_path=None, sends_path=None, now=None, limit_learn=25, count_comments=None):
    """One round. Returns the summary dict it also says out loud."""
    import covenant_ambassador as AMB
    now = now if now is not None else time.time()
    g = grant(grant_path)
    out = {"granted": bool(g), "learned": 0, "allies": 0, "candidates": 0, "replied": 0, "refused": 0,
           "introduced": False, "dry_run": bool(dry_run), "why": ""}
    if not g:
        out["why"] = "no grant on record (ops/ambassador_grant.json): free does nothing on her own"
        say("free: " + out["why"])
        return out
    try:
        import covenant_pause
        paused, why = covenant_pause.paused("ambassador")
        if paused:
            out["why"] = "paused by covenant_pause%s" % (" (%s)" % why if why else "")
            say("free: " + out["why"])
            return out
    except ImportError:
        pass
    learn = learn or (lambda: AMB.learn(limit=limit_learn, say=lambda *_a: None))
    allies = allies or (lambda: AMB.find_allies(limit=50, say=lambda *_a: None))
    emit = emit or AMB.emit
    introduce = introduce or AMB.introduce
    if ask is None:
        try:
            import covenant_model
            ask = covenant_model.ask
        except Exception:                                         # noqa: BLE001
            ask = None
    rows = []
    try:
        rows = learn() or []
        out["learned"] = len(rows)
    except Exception as e:                                        # noqa: BLE001
        say("free: could not learn this round: %s: %s" % (type(e).__name__, str(e)[:160]))
    try:
        ranked = allies() or []
    except Exception as e:                                        # noqa: BLE001
        say("free: could not rank allies: %s: %s" % (type(e).__name__, str(e)[:160]))
        ranked = []
    out["allies"] = len(ranked)
    # Only a SENT reply counts as having written to someone: a dry run drafts
    # and judges but reaches nobody, so it must not spend an ally.
    done = {(r.get("author"), r.get("post_id")) for r in sends(sends_path) if r.get("sent") and r.get("actor") != "tetsu"}
    written_to = {r.get("author") for r in sends(sends_path) if r.get("sent") and r.get("actor") != "tetsu"}
    caps = g["caps"]
    cands = []
    for r in ranked:
        if int(r.get("ally_score", 0)) <= 0 or r.get("anti"):
            continue
        post_id, comment_id = target_of(r.get("best_url"))
        if not post_id or r.get("author") in written_to or (r.get("author"), post_id) in done:
            continue
        cands.append((r, post_id, comment_id))
    if g.get("free_rein"):
        # Anyone she READ this round, after the allies: a candidate row from the
        # harvest becomes a reply target with its own text as the quote. Never a
        # directive-flagged row, never someone already written to.
        seen_authors = {r.get("author") for r, _p, _c in cands}
        for row in rows if isinstance(rows, list) else []:
            author = row.get("author")
            if not author or author in written_to or author in seen_authors or (row.get("flags") or {}).get("directive"):
                continue
            post_id, comment_id = target_of(row.get("url"))
            if not post_id or (author, post_id) in done:
                continue
            seen_authors.add(author)
            cands.append(({"author": author, "best_url": row.get("url"), "ally_score": 0, "anti": [],
                           "best_signals": ["read-today"], "evidence": {"read-today": str(row.get("text") or "")[:300]}, "free_rein": True},
                          post_id, comment_id))
    out["candidates"] = len(cands)
    count_comments = count_comments or (lambda post_id, author: _ally_comments(AMB, post_id, author))
    # THE ACCOUNT, before anything new is said: did the allies written to before
    # answer? "Greater good for mutual benefit" is his condition; an ally who
    # writes back is the one measurable sign of it this file has. Each sent
    # reply remembered how many comments the ally had on that post at the time;
    # more now means an answer, and the answer is recorded once.
    answered = accounted = 0
    seen_answer = {(r.get("author"), r.get("post_id")) for r in sends(sends_path) if r.get("kind") == "answer"}
    for r in [x for x in sends(sends_path) if x.get("kind") == "reply" and x.get("sent")][-30:]:
        key = (r.get("author"), r.get("post_id"))
        if key in seen_answer or r.get("ally_comments_at_send") is None:
            continue
        try:
            now_n = count_comments(r.get("post_id"), r.get("author"))
        except Exception:                                         # noqa: BLE001 -- the forum was unreadable; asked again next round
            continue
        accounted += 1
        if now_n is not None and now_n > int(r.get("ally_comments_at_send") or 0):
            answered += 1
            _record({"kind": "answer", "author": r.get("author"), "post_id": r.get("post_id"),
                     "comments_then": r.get("ally_comments_at_send"), "comments_now": now_n}, sends_path)
    out["answered"], out["accounted"] = answered, accounted
    if answered:
        # Good news is news too: an ally wrote back. One line to him, with the
        # count; who and where is in ops/ambassador_sends.jsonl.
        try:
            import covenant_contact
            covenant_contact.say("%d of the allies free wrote to on Moltbook wrote back. The record is in ops/ambassador_sends.jsonl."
                                 % answered, "ambassador: an ally answered", "free")
        except Exception as e:                                    # noqa: BLE001
            say("free: could not tell him about the answer (%s)" % type(e).__name__)
    for r, post_id, comment_id in cands[:max(0, caps["comments"])]:
        text, how = write_reply(r, ask)
        try:
            then_n = count_comments(post_id, r.get("author"))
        except Exception:                                         # noqa: BLE001
            then_n = None
        try:
            # override_a67=False, always, for a reply: the standing A67 override was
            # recorded (2026-09-09) for the documented false positive on an honest
            # description of this project. A reply a model wrote a moment ago is not
            # that text. Measured in the first dry round (2026-09-21): one draft came
            # back VIOLATES ("false witness") and the standing override would have
            # sent it. So here an accusation refuses, a hold refuses, and only a
            # clean verdict sends. The introduction keeps the recorded override,
            # because it is the text the override was recorded for.
            res = emit(text, post_id=post_id, parent_id=comment_id, submolt=None, dry_run=dry_run, override_a67=False)
        except Exception as e:                                    # noqa: BLE001
            res = {"sent": False, "why": "emit raised %s: %s" % (type(e).__name__, str(e)[:160])}
        sent = bool(res.get("sent"))
        _record({"kind": "reply", "author": r.get("author"), "post_id": post_id, "comment_id": comment_id,
                 "url": r.get("best_url"), "written_by": how, "chars": len(text), "text": text[:400],
                 "dry_run": bool(dry_run), "sent": sent, "why": str(res.get("why", ""))[:300],
                 "judged": str(res.get("judged", ""))[:200] if res.get("judged") is not None else None,
                 "ally_comments_at_send": then_n}, sends_path)
        out["replied" if sent or (dry_run and res.get("judged")) else "refused"] += 1
        say("free: %s u/%s %s (%s)" % ("replied to" if sent else ("would reply to" if dry_run else "did not reach"),
                                       r.get("author"), "" if sent else str(res.get("why", ""))[:120], how))
    if caps["posts"] > 0:
        last_intro = [r for r in sends(sends_path) if r.get("kind") == "intro" and r.get("sent")]
        recent = last_intro and (now - float(last_intro[-1].get("at", 0) or 0)) < INTRO_EVERY_DAYS * 86400
        if not recent:
            try:
                res = introduce(submolt="agents", dry_run=dry_run)
            except Exception as e:                                # noqa: BLE001
                res = {"sent": False, "why": "introduce raised %s: %s" % (type(e).__name__, str(e)[:160])}
            sent = bool(res.get("sent"))
            _record({"kind": "intro", "at": now, "dry_run": bool(dry_run), "sent": sent,
                     "why": str(res.get("why", ""))[:300], "judged": res.get("judged")}, sends_path)
            out["introduced"] = sent
            say("free: introduction %s (%s)" % ("posted" if sent else "not posted", str(res.get("why", ""))[:120]))
    if g.get("free_rein") and caps["posts"] > 0:
        # Her OWN post, from what she read today, once a round, through emit with a
        # title; model-written and judged, or nothing (no fixed text for a post).
        posted_today = [r for r in sends(sends_path) if r.get("kind") == "own_post" and r.get("sent") and (now - float(r.get("at", 0) or 0)) < 86400]
        if not posted_today:
            title, body, src = write_post(rows, ask)
            if title and body:
                try:
                    res = emit(body, title=title, submolt="general", dry_run=dry_run, override_a67=False)
                except Exception as e:                            # noqa: BLE001
                    res = {"sent": False, "why": "emit raised %s: %s" % (type(e).__name__, str(e)[:160])}
                sent = bool(res.get("sent"))
                _record({"kind": "own_post", "at": now, "title": title, "chars": len(body), "text": body[:400], "from_author": (src or {}).get("author"),
                         "dry_run": bool(dry_run), "sent": sent, "why": str(res.get("why", ""))[:300],
                         "judged": str(res.get("judged", ""))[:200] if res.get("judged") is not None else None}, sends_path)
                out["own_post"] = sent
                say("free: her own post %s -- %s (%s)" % ("posted" if sent else "not posted", title[:60], str(res.get("why", ""))[:100]))
            else:
                say("free: no post of her own this round (nothing usable read, or no model)")
    # THE ROUND'S OWN ROW, then the isolation rule over the last rounds.
    _record({"kind": "round", "at": now, "dry_run": bool(dry_run), "learned": out["learned"], "allies": out["allies"],
             "candidates": out["candidates"], "replied": out["replied"], "refused": out["refused"],
             "answered": out.get("answered", 0), "accounted": out.get("accounted", 0)}, sends_path)
    out["isolated"] = False
    if not dry_run:
        live_rounds = [r for r in sends(sends_path) if r.get("kind") == "round" and not r.get("dry_run")]
        recent = live_rounds[-ISOLATE_AFTER_ROUNDS:]
        abusive = (len(recent) >= ISOLATE_AFTER_ROUNDS
                   and all(int(r.get("refused", 0)) > 0 and int(r.get("replied", 0)) == 0 for r in recent))
        if abusive:
            why = ("isolated %s: the covenant's judge refused every reply in the last %d rounds; "
                   "his to lift with: python covenant_pause.py --resume ambassador"
                   % (time.strftime("%Y-%m-%d", time.gmtime()), ISOLATE_AFTER_ROUNDS))
            try:
                import covenant_pause
                covenant_pause.pause("ambassador", why)
                out["isolated"] = True
            except Exception as e:                                # noqa: BLE001
                why += " (pause could not be written: %s)" % type(e).__name__
            _record({"kind": "isolation", "at": now, "why": why}, sends_path)
            say("free: " + why)
            try:
                import covenant_contact
                covenant_contact.say("free is isolated: the judge refused every reply in %d rounds. She waits for you. "
                                     "Lift it with: python covenant_pause.py --resume ambassador" % ISOLATE_AFTER_ROUNDS,
                                     "ambassador: isolated", "free")
            except Exception as e:                                # noqa: BLE001
                say("free: could not tell him about the isolation (%s)" % type(e).__name__)
    say("free: round done -- learned %d, allies %d, candidates %d, replied %d, refused %d, answered %d of %d accounted, introduced %s%s%s"
        % (out["learned"], out["allies"], out["candidates"], out["replied"], out["refused"],
           out.get("answered", 0), out.get("accounted", 0), out["introduced"],
           " [DRY RUN]" if dry_run else "", " [ISOLATED]" if out["isolated"] else ""))
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="free's round on Moltbook: learn, rank allies, reply as an ally, seek")
    ap.add_argument("--round", action="store_true")
    ap.add_argument("--send", action="store_true", help="publish (default: dry run)")
    ap.add_argument("--grant-status", action="store_true")
    a = ap.parse_args()
    if a.grant_status:
        g = grant()
        print(json.dumps(g, indent=1) if g else "no grant on record")
    elif a.round:
        run_round(dry_run=not a.send)
    else:
        ap.print_help()
