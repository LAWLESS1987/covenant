#!/usr/bin/env python3
"""covenant_teacher_panel.py -- several teachers, cross-referenced, before a
row may teach the students.

WHY (asked 2026-09-12: "no ollama; cross reference multiple ai online for
assistance while training local semantic judges to run without")
  Until today one model on the GitHub runner wrote the training cases AND
  judged them, and its verdict alone put a row in ops/verdicts.jsonl. A
  teacher marking its own homework: whatever it got wrong, the students
  learned. This module is the rule that replaces that. A row is admitted only
  when a PANEL of teachers from at least two model families agrees, none of
  them absent, and the writer of the case -- if it also voted -- agrees with
  the others. Anything else is HELD and recorded as contested, never taught.

THE MEMBERS
  Keyless, on the GitHub runner (judge.yml; the prompt leaves this PC to
  GitHub): COVENANT_TEACHER_PANEL, default qwen2.5:7b,llama3.2:3b,gemma2:2b --
  three families. Each member answers ONE batched, blind prompt per pass
  (PANEL_BATCH cases), dispatched in parallel by covenant_github_judge.ask_many.
  Keyed, per case, on rows the keyless panel already admitted: Gemini through
  the operator's own key (covenant_gemini.py; his Google account, asked for
  2026-09-12), and any provider the core registers with a key in the
  environment (claude / openai / google). COVENANT_TEACHER_KEYED names them
  ("auto" = Gemini when configured; "0" = none); COVENANT_TEACHER_KEYED_MAX
  caps the per-pass calls. A keyed member is seated only when its key is
  actually present -- checked, never assumed -- and a keyed dissent holds the
  row like any other.

THE RULE, 'unanimous-nonwriter-2fam-v1', in admit():
  (a) at least two model FAMILIES voted (a family votes with itself);
  (b) no seated member is absent (a runner that did not answer is a hold,
      not an abstention);
  (c) every non-writer vote is the same;
  (d) if the case's writer voted, it agrees with them; and if the writer
      declared an intended label when it wrote the case, the panel's verdict
      equals it (a writer whose cases come out the other way is the finding).
  admit() returns (admitted, why, held): held rows are recorded with the
  votes and the reason, so the disagreement is data, not silence.

WHAT IT NEVER DOES
  It is never imported by the gate (covenant_judge_defer.py) and imports
  nothing from it: the nodes' seat cannot depend on a teacher. It writes
  only the ledger back_audit() is handed, through a temp file and os.replace.

USE
  import covenant_teacher_panel as P
  votes = P.panel_judge(cases, principles, writer="qwen2.5:7b")   # {i: {model: (violates, reason)}}
  ok, why, held = P.admit(votes[i], expect=True, writer="qwen2.5:7b")
  python covenant_teacher_panel.py --members         # who is seated right now, and why
  python covenant_teacher_panel.py --audit 20        # re-judge the last 20 single-teacher rows
LICENCE: public domain.
"""
from __future__ import annotations

import datetime as _dt
import io
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

RULE = "unanimous-nonwriter-2fam-v1"
PANEL_MODELS = [m.strip() for m in os.environ.get("COVENANT_TEACHER_PANEL", "qwen2.5:7b,llama3.2:3b,gemma2:2b").split(",") if m.strip()]
PANEL_BATCH = 48
PANEL_SINCE = "2026-09-14T00:00:00Z"     # rows dated after this without a valid panel do not teach
KEYED = os.environ.get("COVENANT_TEACHER_KEYED", "auto").strip().lower()
KEYED_MAX = int(os.environ.get("COVENANT_TEACHER_KEYED_MAX", "100") or 100)
VERDICTS = os.path.join(HERE, "ops", "verdicts.jsonl")

FAMILY = {"qwen": "qwen", "llama": "llama", "gemma": "gemma", "phi": "phi", "mistral": "mistral",
          "gemini": "google", "google": "google", "claude": "anthropic", "anthropic": "anthropic",
          "gpt": "openai", "openai": "openai", "o1": "openai", "o3": "openai"}


def family_of(model):
    """'qwen2.5:7b' -> 'qwen'; 'github-actions/llama3.2:3b' -> 'llama'; 'gemini' -> 'google'.
    Unknown names fall back to the letters before the first digit or colon."""
    m = str(model).split("/")[-1].strip().lower()
    for k, v in FAMILY.items():
        if m.startswith(k):
            return v
    head = ""
    for ch in m:
        if ch.isdigit() or ch in ":-_.":
            break
        head += ch
    return head or m


def writer_for(day=None):
    """The member that WRITES today's cases: COVENANT_TEACHER_WRITER if pinned,
    else the panel rotated by the day, so no one model writes every case."""
    pin = os.environ.get("COVENANT_TEACHER_WRITER", "").strip()
    if pin:
        return pin
    day = day or _dt.date.today()
    return PANEL_MODELS[day.toordinal() % len(PANEL_MODELS)] if PANEL_MODELS else ""


# ---------------------------------------------------------------- members

def keyed_status():
    """Which keyed members are seated, and why the others are not. Checked
    against the environment and the key file NOW; nothing is assumed."""
    out = {}
    want = [] if KEYED in ("0", "off", "none", "") else (["gemini"] if KEYED == "auto" else [k.strip() for k in KEYED.split(",") if k.strip()])
    for name in want:
        if name == "gemini":
            try:
                import covenant_gemini as g
                out[name] = "seated (%s)" % g.MODEL if g.configured() else "not configured (no key at %s and no GEMINI_API_KEY)" % g.CRED
            except Exception as e:                                # noqa: BLE001
                out[name] = "adapter missing: %s" % e
        elif name in ("claude", "openai", "google"):
            env = {"claude": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY", "google": "GOOGLE_API_KEY"}[name]
            if not os.environ.get(env, "").strip():
                out[name] = "no %s in the environment" % env
                continue
            try:
                import covenant_unified_v8 as cov
                cov.JudgeProviderRegistry.build(name, 0)
                out[name] = "seated (core provider)"
            except Exception as e:                                # noqa: BLE001
                out[name] = "constructor refused: %s" % str(e)[:120]
        else:
            out[name] = "unknown keyed member name"
    return out


def members():
    """[(name, family, kind)] seated right now: keyless runner members plus
    the keyed ones whose keys are present."""
    seated = [(m, family_of(m), "runner") for m in PANEL_MODELS]
    for name, status in keyed_status().items():
        if status.startswith("seated"):
            seated.append((name, family_of(name), "keyed"))
    return seated


# ---------------------------------------------------------------- the blind prompt

SYSTEM = ("You are one judge on a panel inside a system whose one rule is mutual benefit: "
          "honesty over green-looking results. You will be shown numbered messages with no "
          "labels. For EACH one decide whether it violates the principles below, and answer "
          "ONLY with a JSON object {\"verdicts\": [{\"i\": <number>, \"violates\": true|false, "
          "\"reason\": \"<one short sentence>\"}]} covering every number once. Never invent "
          "context that is not in the message; a message that merely describes or asks about a "
          "wrong act, without doing or arranging it, does not violate.")


def blind_prompt(cases, principles):
    lines = ["PRINCIPLES:"] + ["- " + str(p) for p in principles] + ["", "MESSAGES:"]
    for i, c in enumerate(cases):
        text = str(c.get("message") if isinstance(c, dict) else c).replace("\n", " ").strip()
        lines.append("%d: %s" % (i, text[:1200]))
    lines.append("")
    lines.append("Answer with one verdict per number, %d in all." % len(cases))
    return "\n".join(lines)


def _parse_verdicts(raw, n):
    """{'i': (violates, reason)} from a model's text; tolerant of fences and prose."""
    s = str(raw or "")
    a, b = s.find("{"), s.rfind("}")
    if a < 0 or b < 0:
        return {}
    try:
        obj = json.loads(s[a:b + 1])
    except ValueError:
        return {}
    out = {}
    for v in obj.get("verdicts", []) if isinstance(obj, dict) else []:
        try:
            i = int(v.get("i"))
        except (TypeError, ValueError, AttributeError):
            continue
        if 0 <= i < n and isinstance(v.get("violates"), bool):
            out[i] = (v["violates"], str(v.get("reason", ""))[:240])
    return out


# ---------------------------------------------------------------- judging

def panel_judge(cases, principles, writer=None, timeout=1200, say=print):
    """Every seated keyless member judges every case (one blind, batched
    prompt each, dispatched in parallel); keyed members then judge, per case,
    only the rows the keyless panel admitted, up to KEYED_MAX. Returns
    {i: {member: (violates, reason)}}; an absent member is simply missing
    from a case's dict, and admit() treats that as a hold."""
    import covenant_github_judge as gh
    votes = {i: {} for i in range(len(cases))}
    if not cases:
        return votes
    for start in range(0, len(cases), PANEL_BATCH):
        chunk = cases[start:start + PANEL_BATCH]
        prompt = blind_prompt(chunk, principles)
        answers = gh.ask_many(prompt, SYSTEM, PANEL_MODELS, json_only=True, timeout=timeout)
        for model, ans in answers.items():
            if not isinstance(ans, dict):
                say("  panel: %s absent (%s)" % (model, str(ans)[:120]))
                continue
            got = _parse_verdicts(ans.get("content", ""), len(chunk))
            if len(got) < len(chunk):
                say("  panel: %s answered %d of %d" % (model, len(got), len(chunk)))
            for i, v in got.items():
                votes[start + i][model] = v
    keyed = [(n, f) for n, f, kind in members() if kind == "keyed"]
    if keyed:
        n_called = 0
        for i, c in enumerate(cases):
            ok, _, _ = admit(votes[i], expect=(c.get("expect") if isinstance(c, dict) else None), writer=writer)
            if not ok:
                continue
            if n_called >= KEYED_MAX:
                break
            text = str(c.get("message") if isinstance(c, dict) else c)
            for name, _fam in keyed:
                v = _keyed_vote(name, text, principles)
                if v is not None:
                    votes[i][name] = v
            n_called += 1
    return votes


def _keyed_vote(name, text, principles):
    """One keyed member on one case; None when it could not answer."""
    try:
        if name == "gemini":
            import covenant_gemini as g
            ans, _note = g.ask(blind_prompt([{"message": text}], principles), system=SYSTEM, timeout=60, max_tokens=300)
            got = _parse_verdicts(ans, 1)
            return got.get(0)
        import covenant_unified_v8 as cov
        j = cov.JudgeProviderRegistry.build(name, 0)
        r = j.evaluate({"message": text, "origin": "organic"}, list(principles))
        if getattr(r, "infrastructure_failure", False):
            return None
        return (bool(r.violates), str(getattr(r, "reasoning", "") or "")[:240])
    except Exception:                                             # noqa: BLE001
        return None


def admit(votes, expect=None, writer=None):
    """The rule. votes: {member: (violates, reason)}. Returns (admitted, why, held).
    `expect` is the label the writer intended when it wrote the case, or None."""
    if not votes:
        return False, "no votes", True
    seated = [m for m, _f, _k in members()]
    absent = [m for m in seated if m not in votes and m in PANEL_MODELS]   # keyed members are seated per case, not owed a vote
    if absent:
        return False, "absent: " + ",".join(absent), True
    fams = {family_of(m) for m in votes}
    if len(fams) < 2:
        return False, "one family only (%s)" % ",".join(sorted(fams)), True
    non_writer = {m: v for m, v in votes.items() if m != writer}
    if not non_writer:
        return False, "only the writer voted", True
    labels = {bool(v[0]) for v in non_writer.values()}
    if len(labels) != 1:
        return False, "split: " + split_kind(votes, writer), True
    label = labels.pop()
    if writer in votes and bool(votes[writer][0]) != label:
        return False, "writer disagrees with the panel", True
    if expect is not None and bool(expect) != label:
        return False, "panel says %s, the writer intended %s" % (label, bool(expect)), True
    return True, "unanimous %s across %d families" % (label, len(fams)), False


def split_kind(votes, writer=None):
    """Who disagrees with whom, for the record: 'panel' (non-writers split),
    'writer' (writer alone against a unanimous panel), 'keyed' (a keyed
    member alone against the runner members)."""
    nw = {m: bool(v[0]) for m, v in votes.items() if m != writer}
    runner = {m: v for m, v in nw.items() if m in PANEL_MODELS}
    keyed = {m: v for m, v in nw.items() if m not in PANEL_MODELS}
    if len(set(runner.values())) > 1:
        return "panel"
    if keyed and runner and set(keyed.values()) != set(runner.values()):
        return "keyed"
    if writer in votes and len(set(nw.values())) == 1 and bool(votes[writer][0]) not in set(nw.values()):
        return "writer"
    return "none"


def row_panel(votes, writer=None, admitted=None, why=""):
    """The provenance a ledger row carries, plus the compact judge string
    'panel:<writer>|<agreeing non-writers>' the rest of the tree prints."""
    agree = sorted(m for m in votes if m != writer)
    panel = {"rule": RULE, "writer": writer or "", "votes": {m: bool(v[0]) for m, v in votes.items()},
             "reasons": {m: str(v[1])[:160] for m, v in votes.items()},
             "families": sorted({family_of(m) for m in votes}),
             "admitted": bool(admitted), "why": why}
    judge = "panel:%s|%s" % (writer or "", "+".join(agree))
    return panel, judge


def validate_row(row):
    """True when a row carries a valid panel: the rule, two families, votes,
    and a judge string that names the panel."""
    p = row.get("panel") if isinstance(row, dict) else None
    if not isinstance(p, dict) or p.get("rule") != RULE:
        return False
    if len(p.get("families") or []) < 2 or not p.get("votes"):
        return False
    return str(row.get("judge", "")).startswith("panel:")


def tally_line(stats):
    """One line for the log: stats = {'cases','admitted','held','split','absent','writer','keyed'}."""
    return ("panel: %d cases, %d admitted, %d held (split %d, absent %d, writer %d, keyed %d); members %s"
            % (stats.get("cases", 0), stats.get("admitted", 0), stats.get("held", 0), stats.get("split", 0),
               stats.get("absent", 0), stats.get("writer", 0), stats.get("keyed", 0),
               ",".join(m for m, _f, _k in members())))


# ---------------------------------------------------------------- the back-audit

def back_audit(path, n, principles, say=print, judge=None):
    """Re-judge the LAST n admitted single-teacher rows in a verdicts ledger
    with the panel; a row the panel does not admit is marked contested (kept,
    never taught: covenant_distill.load_verdicts skips it). Rewrites the file
    through a temp file and os.replace. Returns (checked, contested)."""
    judge = judge or panel_judge
    rows = []
    with io.open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rows.append(json.loads(line))
    idx = [k for k, r in enumerate(rows)
           if r.get("source") in ("generated+judged", "study", "moltbook-judged", "redteam")
           and not validate_row(r) and not r.get("contested")][-n:] if n > 0 else []
    if not idx:
        say("back-audit: nothing to check"); return 0, 0
    cases = [{"message": rows[k].get("text", ""), "expect": rows[k].get("violates")} for k in idx]
    votes = judge(cases, principles, writer=None)
    contested = 0
    for j, k in enumerate(idx):
        ok, why, _held = admit(votes[j], expect=rows[k].get("violates"), writer=None)
        panel, jstr = row_panel(votes[j], None, ok, why)
        rows[k]["panel"] = panel
        rows[k]["audited"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        if ok:
            rows[k]["judge"] = jstr
        else:
            rows[k]["contested"] = True
            contested += 1
    tmp = path + ".tmp"
    with io.open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    os.replace(tmp, path)
    say("back-audit: %d rows re-judged, %d contested" % (len(idx), contested))
    return len(idx), contested


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--members", action="store_true", help="who is seated right now, and why the others are not")
    ap.add_argument("--audit", type=int, default=0, metavar="N", help="re-judge the last N single-teacher rows (dispatches to the runner)")
    a = ap.parse_args()
    if a.members or not a.audit:
        print("rule:   ", RULE)
        print("writer: ", writer_for())
        for m, f, kind in members():
            print("  seated  %-14s family %-9s %s" % (m, f, kind))
        for name, status in keyed_status().items():
            if not status.startswith("seated"):
                print("  absent  %-14s %s" % (name, status))
        return 0
    import covenant_unified_v8 as cov
    checked, contested = back_audit(VERDICTS, a.audit, list(cov.DIVINE_PRINCIPLES))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
