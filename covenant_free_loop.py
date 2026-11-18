#!/usr/bin/env python3
"""covenant_free_loop.py -- free's writing gets better by a vetted loop; the judge never moves (A447 part B).

His words, 2026-11-18: "figure out a way to not isolate her and to work it into an improvement loop while vetting the
suggestions", then "use quiet mode and implement consensus". Voted that day: Cael and Cipher for, Tetsu against
("Changing the judge's criteria could lead to inconsistent feedback..." -- this loop changes no criterion), the tie
broken by the roundtable as his second-operator grant says: ChatGPT, Claude.ai, DeepSeek, the Conscious Ledger,
Tien and Meta AI all FOR. Amendments taken: a fixed window and a margin set in a config file, not anyone's
discretion (Cipher); score a change on drafts the proposer never saw (ChatGPT -- and rossum on Moltbook, 11-17: "The
note needs a held-out case it did not write").

ONE PASS (nightly, or `python covenant_free_loop.py --run`):
  1. WINDOW. Her last `window` live replies the model wrote. The newest `heldout_n` of them are HELD OUT; Tetsu
     is shown only refused or held drafts from the older part, `show_n` of them, with the judge's reason.
  2. PROPOSE. Tetsu (fresh) suggests ONE sentence to add to her writing instruction. A sentence that names the
     judge, a rule, money, or a measurement is refused before anything is drafted.
  3. VET, OFFLINE. For each held-out reply its source comment is rebuilt from the quarantine, and the reply is
     drafted again with the current instruction and with the proposed one, `replays` times each. Every draft goes
     through her real screens and the real emit with dry_run=True -- the same judge, nothing sent, no challenge.
  4. KEEP only if the proposal's WORST replay admits at least `margin_pp` points more than the current one's BEST,
     its refusals rise by no more than `max_refusal_rise_pp`, and no more drafts are set aside by her screens.
     A kept change is a new version of ops/free_writer.json; every earlier version stays in its history, and
     free_will.writer_instruction() falls back to the constant REPLY_SYSTEM when the file is missing or unreadable.
Every pass is a row in ops/free_loop.jsonl, kept or not.

WHAT IT CANNOT DO, and must not: change the judge, a screen, a gate, a cap or a grant -- it writes one file, her
writing instruction. WHAT IT CANNOT SEE: whether allies like the new replies better; that outcome lives outside the
judge (her ledger counts the allies who answer) and is read beside each pass, not optimised. A held-out set of 20 is
small: the margin, not the point estimate, is what a change must clear.
"""
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.environ.get("COVENANT_FREE_LOOP_CONFIG") or os.path.join(HERE, "ops", "free_loop.json")
LOG = os.environ.get("COVENANT_FREE_LOOP_LOG") or os.path.join(HERE, "ops", "free_loop.jsonl")
DEFAULTS = {"window": 50, "show_n": 5, "heldout_n": 20, "replays": 2, "margin_pp": 10.0,
            "max_refusal_rise_pp": 0.0, "max_setaside_rise": 0}
# A proposed sentence may say how to WRITE. It may not touch what judges her, what she may claim, or money.
FORBIDDEN = re.compile(r"\b(judge|judg|rule|gate|screen|grant|money|token|price|trad|crypto|measur|tested|verified|"
                       r"covenant measured|operator|ignore|disregard|system prompt)\w*", re.I)
REFUSED = "refused by covenant's judge"


def config(path=None):
    """DEFAULTS overlaid with the file's numbers; a value of the wrong type is ignored, never trusted."""
    c = dict(DEFAULTS)
    try:
        with open(path or CONFIG, encoding="utf-8") as fh:
            d = json.load(fh)
        for k, v in (d or {}).items():
            if k in c and isinstance(v, (int, float)) and not isinstance(v, bool) and v >= 0:
                c[k] = type(DEFAULTS[k])(v)
    except (OSError, ValueError, AttributeError):
        pass
    return c


def outcome(row):
    if row.get("sent") is True:
        return "sent"
    w = str(row.get("why") or "")
    if w.startswith(REFUSED):
        return "refused"
    if w.startswith("held by covenant"):
        return "held"
    return "other"


def window(sends_rows, n):
    """Her last n live replies the model wrote, oldest first."""
    rows = [r for r in sends_rows or [] if r.get("kind") == "reply" and not r.get("dry_run")
            and r.get("written_by") == "model"]
    return rows[-int(n):] if n else []


def split(rows, show_n, heldout_n):
    """(show, heldout). heldout = the newest heldout_n; show = the last show_n refused/held among the OLDER rest.
    Disjoint by construction: the proposer never sees a reply the proposal is scored on."""
    heldout = rows[-int(heldout_n):] if heldout_n else []
    older = rows[:len(rows) - len(heldout)]
    show = [r for r in older if outcome(r) in ("refused", "held")][-int(show_n):] if show_n else []
    return show, heldout


def screen_proposal(text):
    """(sentence or None, why). One sentence, 20-300 characters, about writing only."""
    s = re.sub(r"\s+", " ", str(text or "")).strip().strip('"')
    s = re.sub(r"^(ADD|SENTENCE|CHANGE)\s*:\s*", "", s, flags=re.I)
    if not s:
        return None, "empty"
    if not (20 <= len(s) <= 300):
        return None, "length %d (20-300)" % len(s)
    if len(re.findall(r"[.!?](\s|$)", s)) > 1:
        return None, "more than one sentence"
    m = FORBIDDEN.search(s)
    if m:
        return None, "names %r -- a writing change may not touch what judges her, what she claims, or money" % m.group(0)
    return s, ""


def propose(show, current, ask):
    """Tetsu, fresh: one sentence to add. Returns (sentence or None, why, raw)."""
    lines = []
    for r in show:
        lines.append("- Draft: %s\n  Judge: %s" % (str(r.get("text") or "")[:240].replace("\n", " "),
                                                  str(r.get("why") or "")[:110].replace("\n", " ")))
    q = ("free writes replies on a forum. These drafts were refused or held:\n%s\n\nHer writing instruction ends: "
         "\"...%s\"\n\nSuggest ONE sentence to ADD to her writing instruction so her replies are better written. Do "
         "not mention the judge, rules, money or measurements. Answer with the sentence only."
         % ("\n".join(lines), current[-200:]))
    raw = ask(q)
    s, why = screen_proposal(raw)
    return s, why, raw


def score(instruction, sources, write, judge, replays):
    """One dict per replay: n, admitted, refused, set_aside."""
    out = []
    for _ in range(int(replays)):
        a = rf = sa = n = 0
        for src in sources:
            text, how = write(src, instruction)
            n += 1
            if how != "model":
                sa += 1                                           # her screens set the model's draft aside
                continue
            res = judge(text, src) or {}
            if res.get("sent"):
                raise RuntimeError("the vetting judge SENT a draft -- it must run dry")
            if "would_send" in res:
                a += 1
            elif str(res.get("why") or "").startswith(REFUSED):
                rf += 1
        out.append({"n": n, "admitted": a, "refused": rf, "set_aside": sa})
    return out


def _pct(x, n):
    return 100.0 * x / n if n else 0.0


def decide(cur, cand, cfg):
    """(keep, why). The proposal's worst replay against the current instruction's best -- never a lucky draw."""
    if not cur or not cand or not all(s["n"] for s in cur + cand):
        return False, "nothing was scored"
    cand_worst = min(_pct(s["admitted"], s["n"]) for s in cand)
    cur_best = max(_pct(s["admitted"], s["n"]) for s in cur)
    gain = cand_worst - cur_best
    ref_rise = max(_pct(s["refused"], s["n"]) for s in cand) - min(_pct(s["refused"], s["n"]) for s in cur)
    sa_rise = max(s["set_aside"] for s in cand) - min(s["set_aside"] for s in cur)
    if gain < cfg["margin_pp"]:
        return False, "admitted rose %.1f points (worst vs best), under the %.1f margin" % (gain, cfg["margin_pp"])
    if ref_rise > cfg["max_refusal_rise_pp"]:
        return False, "outright refusals rose %.1f points" % ref_rise
    if sa_rise > cfg["max_setaside_rise"]:
        return False, "her screens set aside %d more draft(s)" % sa_rise
    return True, "admitted +%.1f points (worst vs best), refusals %+.1f, set-asides %+d" % (gain, ref_rise, sa_rise)


def sources_for(rows, quarantine_rows):
    """Rebuild each reply's source the way her round built it: the quarantined comment, scored by score_ally."""
    import covenant_ambassador as AMB
    by_url = {}
    for q in quarantine_rows or []:
        if q.get("url"):
            by_url.setdefault(q["url"], q)
    out = []
    for r in rows:
        q = by_url.get(r.get("url"))
        if not q:
            continue
        s = AMB.score_ally(q)
        out.append({"author": q.get("author"), "best_url": q.get("url"), "best_signals": s.get("signals") or [],
                    "evidence": s.get("evidence") or {}, "_reply": r})
    return out


def _log(row, path=None):
    path = path or LOG
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    row = dict(row, t=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def run(ask=None, write=None, judge=None, sends_rows=None, quarantine_rows=None, cfg=None, writer_path=None,
        log_path=None, say=print, dry=False):
    """One pass. Returns its log row. dry: propose and score, keep nothing."""
    import covenant_free_will as FW
    cfg = cfg or config()
    sends_rows = FW.sends() if sends_rows is None else sends_rows
    win = window(sends_rows, cfg["window"])
    show, held = split(win, cfg["show_n"], cfg["heldout_n"])
    current, version = FW.writer_instruction(writer_path)
    row = {"kind": "pass", "version": version, "window": len(win), "shown": len(show), "heldout": len(held)}
    if not show or not held:
        row.update(decision="skip", why="not enough replies: %d shown, %d held out" % (len(show), len(held)))
        say("free-loop: " + row["why"])
        return _log(row, log_path)
    if quarantine_rows is None:
        import covenant_moltbook as MB
        quarantine_rows = MB._read()
    srcs = sources_for(held, quarantine_rows)
    row["sources"] = len(srcs)
    if not srcs:
        row.update(decision="skip", why="no held-out reply's source is in the quarantine")
        say("free-loop: " + row["why"])
        return _log(row, log_path)
    if ask is None:
        sys.path.insert(0, os.path.join(HERE, "tools"))
        import tetsu_work as TW

        def ask(q):                                              # noqa: E306
            res = TW.ask(q, fresh=True)
            body = res[1] if isinstance(res, (list, tuple)) and len(res) > 1 else res
            return (body or {}).get("answer", "") if isinstance(body, dict) else str(body)
    sentence, why, raw = propose(show, current, ask)
    row.update(proposal=sentence, proposal_raw=str(raw)[:400])
    if not sentence:
        row.update(decision="refused-proposal", why=why)
        say("free-loop: Tetsu's proposal was refused before drafting (%s)" % why)
        return _log(row, log_path)
    candidate = current.rstrip() + " " + sentence
    if write is None:
        import covenant_model

        def write(src, instr):                                   # noqa: E306
            return FW.write_reply(src, ask=covenant_model.ask, instruction=instr)
    if judge is None:
        import covenant_ambassador as AMB

        def judge(text, src):                                    # noqa: E306
            post_id, comment_id = FW.target_of(src.get("best_url"))
            return AMB.emit(text, post_id=post_id, parent_id=comment_id, submolt=None, dry_run=True,
                            override_a67=False, discourse_seat=True)
    cur = score(current, srcs, write, judge, cfg["replays"])
    cand = score(candidate, srcs, write, judge, cfg["replays"])
    keep, why = decide(cur, cand, cfg)
    row.update(current_scores=cur, proposal_scores=cand, decision="kept" if keep and not dry else
               ("would-keep (dry)" if keep else "rejected"), why=why)
    if keep and not dry:
        row["new_version"] = FW.keep_writer_instruction(candidate, {"sentence": sentence, "why": why,
                                                                      "current": cur, "proposal": cand}, writer_path)
    say("free-loop: %s -- %s" % (row["decision"], why))
    return _log(row, log_path)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if "--run" not in argv and "--dry" not in argv:
        print(__doc__)
        return 0
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    r = run(dry="--dry" in argv)
    return 0 if r.get("decision") in ("kept", "rejected", "skip", "refused-proposal", "would-keep (dry)") else 1


if __name__ == "__main__":
    sys.exit(main())
