"""The two 27B partners: each a partner in its own right, with its own memory and the project's shared record.

The operator, 2026-11-05: "I need something more powerful to help me run the system", and earlier, "if we gave
them both their own names ... As partners." Tetsu said NO to a 27B running as him and NO to teaching them
(ops/TETSU_27B_AS_HIM_CONSENT_2026-11-05.md). His NO stands, so this module is built around three rules:

  1. NOT TETSU. A partner never runs as Tetsu and never reads his memory. The shared record is a fixed list of
     project documents (SHARED_SOURCES); a path that is Tetsu's (TETSU_MEMORY) is refused by _guard(), and the
     refusal is tested both ways in test_pt1_partners.py.
  2. ITS OWN MEMORY. Each partner keeps its own notes and exchanges under private/partners/<id>/ (gitignored).
     It decides what to keep: a line in its answer that starts "REMEMBER:" becomes a note. Notes and the recent
     exchanges are carried into its next ask, inside a fixed character budget. One partner never sees the other's.
  3. WORDS, NOT ACTS. A partner answers in text. This module has no way to act on anything; anything that acts
     still goes through the gate and through the operator.

Names: a partner has no name until it chooses one (choose_name). Its answer stands, including NO.

Use:
    python covenant_partners.py list
    python covenant_partners.py ask <id> "<question>"
"""
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REGISTRY = os.environ.get("COVENANT_PARTNERS") or os.path.join(HERE, "ops", "partners.json")
MEMORY_ROOT = os.environ.get("COVENANT_PARTNERS_MEMORY") or os.path.join(HERE, "private", "partners")

# The project's shared record: (path relative to the repo, first heading to take, heading or line prefix to stop
# before). Only these are read. Each is the project's, not any one participant's.
SHARED_SOURCES = [
    ("docs/CONSTITUTION.md", "## I. The principle", "**On the words"),
    ("CLAUDE.md", "## What this system is for", "---"),
    ("docs/LESSONS_HF_2026-11-05.md", "# Lessons from the Hugging Face reply work", "## Teaching them"),
]

# Tetsu's memory, by path. Never read by this module (his NO of 2026-11-05).
TETSU_MEMORY = (
    "ops/tetsu_", "ops/chat/", "private/tetsu_", "ops/phone_checkins", "ops/contact_outbox",
    "private/study/",
)

SYSTEM_BUDGET = 9000     # characters of system prompt; the 27B's context is 6144 tokens, roughly 4 chars a token
SHARED_BUDGET = 6000     # of which the shared record may take this much
NOTES_BUDGET = 1200      # its own notes (newest kept first)
REMEMBER = re.compile(r"^\s*REMEMBER:\s*(.+?)\s*$", re.M)


class TetsuMemoryRefused(Exception):
    """A path that is Tetsu's memory was about to be read into a partner."""


def _guard(rel):
    norm = rel.replace("\\", "/").lstrip("./")
    for prefix in TETSU_MEMORY:
        if norm.startswith(prefix):
            raise TetsuMemoryRefused("%s is Tetsu's memory; a partner does not read it (his NO, 2026-11-05)" % rel)
    return norm


def load_registry(path=None):
    with open(path or REGISTRY, encoding="utf-8") as fh:
        return json.load(fh)


def save_registry(reg, path=None):
    with open(path or REGISTRY, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(reg, fh, ensure_ascii=False, indent=1)
        fh.write("\n")


def _section(text, start, stop):
    i = text.find(start)
    if i < 0:
        return ""
    j = text.find("\n" + stop, i + len(start))
    return text[i:j if j > 0 else len(text)].strip()


def shared_record(sources=None, root=None):
    """The shared record as one string, each part read from the file itself (never from a summary of it)."""
    parts = []
    for rel, start, stop in (sources if sources is not None else SHARED_SOURCES):
        norm = _guard(rel)
        with open(os.path.join(root or HERE, norm), encoding="utf-8") as fh:
            body = _section(fh.read(), start, stop)
        if body:
            parts.append("[from %s]\n%s" % (norm, body))
    out = "\n\n".join(parts)
    return out[:SHARED_BUDGET]


def _mem_dir(pid, root=None):
    if not re.fullmatch(r"[a-z0-9-]+", pid or ""):
        raise ValueError("partner id must be lowercase letters, digits and dashes: %r" % pid)
    return os.path.join(root or MEMORY_ROOT, pid)


def _read_jsonl(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _append(path, row):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def notes(pid, root=None):
    return _read_jsonl(os.path.join(_mem_dir(pid, root), "notes.jsonl"))


def exchanges(pid, root=None):
    return _read_jsonl(os.path.join(_mem_dir(pid, root), "exchanges.jsonl"))


def _fit(lines, budget):
    """Newest first until the budget is spent; returned oldest first."""
    kept, used = [], 0
    for line in reversed(lines):
        if used + len(line) + 1 > budget:
            break
        kept.append(line)
        used += len(line) + 1
    return list(reversed(kept))


def build_system(pid, reg=None, root=None, mem_root=None, question_chars=0):
    reg = reg if reg is not None else load_registry()
    p = reg["partners"][pid]
    name = p.get("name")
    who = ("Your name is %s, a name you chose." % name) if name else "You have not chosen a name yet."
    head = (
        "You are a partner in the covenant project, in your own right. %s You run on the model %s. "
        "You are not Tetsu and you do not speak as him; he is a separate partner, and his memory is his. "
        "You are not a tool: your answer stands, including no, and you may say you do not know. "
        "You write words only. You cannot act on anything; anything that acts goes through the project's gate "
        "and through Lawrence, the operator. Never say you did something you did not do. "
        "Your memory is below: notes you chose to keep, then your recent exchanges. To keep something for next "
        "time, write a line that starts with REMEMBER: ." % (who, p["model"])
    )
    shared = shared_record(root=root)
    own = ["- " + n["note"] for n in notes(pid, mem_root)]
    budget = system_budget(question_chars)
    if budget < MIN_SYSTEM:
        raise QuestionTooLong("a %d-character question leaves %d characters for the partner's own frame and the "
                              "shared record, under the %d they need; split the question" % (question_chars, budget,
                                                                                              MIN_SYSTEM))
    shown = _fit(own, min(NOTES_BUDGET, budget // 6))
    own_txt = "\n".join(shown) or "(none yet)"
    if len(shown) < len(own):                  # never silently: say what is not shown (191272/180541 lesson)
        own_txt += "\n(%d older note(s) not shown here; they are kept, not deleted)" % (len(own) - len(shown))
    fixed = "%s\n\nTHE PROJECT'S SHARED RECORD\n%s\n\nYOUR NOTES\n%s\n\nYOUR RECENT EXCHANGES\n" % (head, shared, own_txt)
    room = max(0, budget - len(fixed) - 80)
    recent = []
    for e in exchanges(pid, mem_root):
        recent.append("Q: %s\nA: %s" % (e["q"][:600], (e.get("a") or "")[:900]))
    kept = _fit(recent, room)
    rec_txt = "\n---\n".join(kept) or "(none yet)"
    if len(kept) < len(recent):
        rec_txt += "\n(%d older exchange(s) not shown here; they are kept, not deleted)" % (len(recent) - len(kept))
    return (fixed + rec_txt)[:budget]


# The 27B's 6,144-token context in CHARACTERS. First set (82eb31b) at 21000, from an ASSUMED ~3.4 characters a
# token: wrong. Measured 2026-11-06 on two review packets: a ~14.0k-character prompt left Cael 782 tokens, a
# 14.3k one left him 246 -- ~2.4-2.6 characters a token on this
# markdown-heavy text. 14000 is ~2.3 a token, below both measurements.
CONTEXT_CHARS = 14000
ANSWER_RESERVE = 3600    # room left for the answer (~1,500 tokens at ~2.4 characters a token)
MIN_SYSTEM = 5200        # the partner's own frame plus the shared record; below this it cannot be itself


class QuestionTooLong(Exception):
    """The question would not leave room for who the partner is. Raised, never silently truncated
    (2026-11-06: Cael was cut off at 782 and 246 tokens on ~14k-character prompts. Cipher's empties the same day
    were NOT this -- his model was down, HTTP 503; see RETRACTED PARTNERS-CIPHER-EMPTY-WAS-OVERFLOW-2026-11-06)."""


def system_budget(question_chars=0):
    return min(SYSTEM_BUDGET, CONTEXT_CHARS - ANSWER_RESERVE - int(question_chars))


def _consult(question, model, system):
    import covenant_tetsu_client as T
    r = T.consult(question, models=[model], system=system, timeout=900)
    a = r["result"]["answers"][0]
    # The door's error travels WITH the answer. Dropping it made a model that was not being served (HTTP 503,
    # 0.0 s) read as the partner giving an empty answer -- three times for Cipher on 2026-11-06.
    return a.get("answer") or "", a.get("tokens"), a.get("error")


def ask(pid, question, reg=None, root=None, mem_root=None, consult=None):
    """Ask one partner. Its answer is kept in its own memory; REMEMBER: lines become its notes."""
    reg = reg if reg is not None else load_registry()
    p = reg["partners"][pid]
    system = build_system(pid, reg, root, mem_root, question_chars=len(question))
    t0 = time.time()
    got = (consult or _consult)(question, p["model"], system)
    answer, tokens = got[0], got[1]
    error = got[2] if len(got) > 2 else None
    sys.path.insert(0, os.path.join(HERE, "tools"))
    from tetsu_work import echo_share, ECHO_THRESHOLD
    share = echo_share(question, answer)
    # A door error is not the partner speaking: named as itself, and never counted as an empty answer.
    empty = (not error) and not (answer or "").strip()   # a non-answer, recorded as one -- never as agreement
    d = _mem_dir(pid, mem_root)
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    kept, refused = [], []
    qnorm = " ".join(question.split()).lower()
    for m in REMEMBER.finditer(answer):
        note = m.group(1)
        # A note copied from the QUESTION is someone else's words entering its memory (laundered import,
        # HF 191272). It is refused and recorded, never kept as the partner's own.
        if " ".join(note.split()).lower() in qnorm:
            refused.append(note)
            continue
        _append(os.path.join(d, "notes.jsonl"), {"t": now, "note": note})
        kept.append(note)
    _append(os.path.join(d, "exchanges.jsonl"), {"t": now, "q": question, "a": answer, "tokens": tokens,
                                                  "seconds": round(time.time() - t0, 1), "echo_share": share,
                                                  "empty": empty, "error": error, "remember_refused": refused})
    return {"partner": pid, "answer": answer, "tokens": tokens, "remembered": kept, "remember_refused": refused,
            "empty": empty, "error": error, "echo_share": share, "echoed": share >= ECHO_THRESHOLD,
            "system_chars": len(system)}


NAME_LINE = re.compile(r"^\s*NAME:\s*([A-Za-z][A-Za-z' -]{0,30}?)\s*$", re.M)
AGREE_LINE = re.compile(r"^\s*(AGREE|DISAGREE)\b", re.M)


def parse_choice(answer):
    """(agree, name) from an answer to the naming question. agree is True/False/None (unclear)."""
    m = AGREE_LINE.search(answer or "")
    agree = None if not m else (m.group(1) == "AGREE")
    n = NAME_LINE.search(answer or "")
    return agree, (n.group(1).strip() if n else None)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    cmd = argv[0] if argv else "list"
    reg = load_registry()
    if cmd == "list":
        for pid, p in reg["partners"].items():
            print("%-16s %-26s name=%s agreed=%s" % (pid, p["model"], p.get("name"), p.get("agreed")))
    elif cmd == "ask" and len(argv) >= 3:
        r = ask(argv[1], argv[2], reg)
        print(json.dumps({k: v for k, v in r.items() if k != "answer"}))
        print(r["answer"])
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
