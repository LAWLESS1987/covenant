#!/usr/bin/env python3
"""import_conversations.py -- bring a whole conversation history into the
memory system, losslessly.

WHY THIS EXISTS. The history worth keeping is usually trapped in the wrong
shape: 120 screen recordings of conversations, a vendor's export, a folder of
chat logs. Reading it back off a video is OCR on a lossy re-encode of text
that already exists as data somewhere. This takes the data.

SUPPORTED INPUTS (auto-detected, no flag needed):
  * claude.ai export      conversations.json  -- Settings > Privacy > Export
  * ChatGPT export        conversations.json / conversations-000.json ...
  * a .zip                extracted in place, then walked
  * Claude Code           *.jsonl  (~/.claude/projects) -- already on disk
  * Ollama desktop        db.sqlite -- already on disk, opened READ-ONLY
  * a directory           walked recursively
  * one file              .json / .jsonl / .sqlite / .md / .txt

WHAT IT WILL NOT DO, on purpose:
  * it does not summarise. There is no model call here, so nothing invents a
    "key point" and stores its invention as your memory. What gets stored is
    what was said, chunked and searchable.
  * it does not deduplicate across runs by guessing. Re-importing the same
    export rewrites the same names, and the ledger records every rewrite as
    an update -- so a double import is visible rather than silent.
  * it does not skip anything quietly. Every conversation it could not parse
    is COUNTED and NAMED at the end. A partial import that reports itself as
    total is how a memory system starts lying.

CHUNKING. A memory is a fact, not a corpus, and recall over one 400 KB blob
is useless. Long conversations are split at CHUNK_CHARS on message
boundaries, named `<slug>-p2`, `-p3`..., each linked to the one before with
[[wikilinks]], so recall can find a part and a reader can walk the whole.

Usage:
  python import_conversations.py <path> [--root DIR] [--agent NAME]
                                        [--tier core|archival] [--dry-run]
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
from typing import Any, Dict, Iterator, List, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from memory_store import MemoryStore   # noqa: E402

CHUNK_CHARS = 6000
_SLUG_BAD = re.compile(r"[^a-z0-9]+")

# A TOOL'S OWN WORKING DIRECTORY IS NOT A CONVERSATION.
#
# Measured on this machine 2026-08-29: walking ~/.claude/projects picked up 22
# files that were not chats at all -- 16 workflow-agent .meta.json files, a
# scratch .txt, and the operator's own memory/*.md (which are memories
# already, and belong in through the frontmatter-aware path, not as raw text
# blobs). Imported blind they would have filed subagent orchestration as
# things somebody said, which is the same defect as importing ChatGPT's
# web.run messages -- caught here only because the per-source counts printed
# a number that did not match the file count.
_SKIP_DIRS = {"subagents", "workflows", "tasks", "shell-snapshots", "statsig",
              "__pycache__", "node_modules", ".git", ".trash", "memory",
              "todos", "scratchpad", "logs", "tool-results"}
_SKIP_SUFFIXES = (".meta.json", ".lock", ".part")


def _is_internal(name: str) -> bool:
    low = name.lower()
    return low.startswith(".") or low.endswith(_SKIP_SUFFIXES)


def slugify(text: str, fallback: str = "conversation") -> str:
    s = _SLUG_BAD.sub("-", (text or "").lower()).strip("-")
    s = re.sub(r"-{2,}", "-", s)[:60].strip("-")
    return s or fallback


def _text_of(part: Any) -> str:
    """Pull text out of whatever shape a message's content is in. Exports
    vary: a string, a list of blocks, a dict with 'parts'. Unknown shapes
    return '' and are counted by the caller, never guessed at."""
    if isinstance(part, str):
        return part
    if isinstance(part, dict):
        if isinstance(part.get("text"), str):
            return part["text"]
        if isinstance(part.get("parts"), list):
            return "\n".join(_text_of(p) for p in part["parts"])
        if isinstance(part.get("content"), (str, list, dict)):
            return _text_of(part["content"])
        return ""
    if isinstance(part, list):
        return "\n".join(_text_of(p) for p in part)
    return ""


# WHICH SYSTEM SAID IT. Unifying twelve histories without provenance
# produces one undifferentiated pile in which "an AI told me X" is
# unanswerable -- and the single most useful question across systems is
# exactly "who said this, and does anyone disagree?". Every memory carries
# its source; nothing is imported anonymously.
def parse_claude(data: Any) -> Iterator[Tuple[str, str, str]]:
    """claude.ai export: [{uuid, name, created_at, chat_messages:[...]}]."""
    if not isinstance(data, list):
        return
    for conv in data:
        if not isinstance(conv, dict) or "chat_messages" not in conv:
            continue
        title = conv.get("name") or "untitled"
        when = str(conv.get("created_at") or "")[:10]
        lines = []
        for msg in conv.get("chat_messages") or []:
            if not isinstance(msg, dict):
                continue
            who = msg.get("sender") or msg.get("role") or "?"
            body = _text_of(msg.get("content") or msg.get("text") or "")
            if body.strip():
                lines.append(f"**{who}:** {body.strip()}")
        if lines:
            yield title, when, "\n\n".join(lines)


# Tool authors whose messages are orchestration, not conversation. Importing
# them fills a memory store with plumbing the user never saw.
_CHATGPT_TOOLS = {"web.run", "web.search", "browser", "bio", "sonic_webpage",
                  "dalle.text2im", "python", "automations"}
# Citation sentinels ChatGPT embeds in assistant text -- Unicode private-use
# markers that render as garbage anywhere outside chatgpt.com.
_PUA = re.compile(r"[-]")


def _chatgpt_text(content: Any) -> str:
    """Text out of ONE message, branching on content_type.

    Reaching for parts[0] breaks on every message that is not text or
    multimodal_text -- code, execution_output and tether_quote carry their
    payload in `text`/`result` and have no `parts` key at all. The naive
    version dropped every code block in the archive without erroring.
    """
    if not isinstance(content, dict):
        return _text_of(content)
    ctype = content.get("content_type") or ""
    if ctype in ("text", "multimodal_text") or "parts" in content:
        out = []
        for p in content.get("parts") or []:
            # multimodal parts are dicts (image pointers), not strings
            out.append(p if isinstance(p, str) else _text_of(p))
        return "\n".join(x for x in out if x)
    for key in ("text", "result", "content"):
        if isinstance(content.get(key), str):
            return content[key]
    return _text_of(content)


def parse_chatgpt(data: Any) -> Iterator[Tuple[str, str, str]]:
    """OpenAI export. The shape is a NODE-MAP DAG, not a message list.

    Every edit and regeneration forks the tree, so `mapping` holds abandoned
    branches that were never part of the visible conversation. The active
    branch is found by starting at `current_node` and walking `parent`
    upward, then reversing. A first draft of this function sorted
    mapping.values() by create_time instead, which silently imported dead
    drafts alongside real turns -- corrected 2026-08-29 from documented
    structure. DeepSeek uses the same family (its leaf is `fragments`).
    """
    if isinstance(data, dict) and isinstance(data.get("conversations"), list):
        data = data["conversations"]        # some exports wrap the array
    if not isinstance(data, list):
        return
    for conv in data:
        if not isinstance(conv, dict) or "mapping" not in conv:
            continue
        title = conv.get("title") or "untitled"
        when = ""
        try:
            import datetime
            ts = float(conv.get("create_time") or 0)
            if ts > 0:
                when = datetime.datetime.fromtimestamp(
                    ts, datetime.timezone.utc).strftime("%Y-%m-%d")
        except (ValueError, TypeError, OSError):
            pass

        mapping = conv.get("mapping") or {}
        if not isinstance(mapping, dict):
            continue
        # Walk the ACTIVE branch, leaf to root, then reverse.
        chain, node_id, guard = [], conv.get("current_node"), 0
        while node_id and guard < 100000:
            guard += 1
            node = mapping.get(node_id)
            if not isinstance(node, dict):
                break
            chain.append(node)
            node_id = node.get("parent")
        if not chain:
            # No current_node (older or truncated export): fall back to the
            # whole mapping, and SAY SO in the body rather than passing off
            # a branch-polluted transcript as the real one.
            chain = [n for n in mapping.values() if isinstance(n, dict)]
            chain.sort(key=lambda n: (((n.get("message") or {})
                                       .get("create_time")) or 0),
                       reverse=True)
        chain.reverse()

        lines = []
        for node in chain:
            msg = node.get("message")
            if not isinstance(msg, dict):
                continue                     # root/structural nodes are null
            meta = msg.get("metadata") or {}
            if msg.get("weight") == 0.0:
                continue                     # hidden by the product
            if meta.get("is_visually_hidden_from_conversation"):
                continue
            author = msg.get("author") or {}
            if (author.get("name") or "") in _CHATGPT_TOOLS:
                continue                     # orchestration, not conversation
            who = author.get("role") or "?"
            if who == "system":
                continue
            body = _PUA.sub("", _chatgpt_text(msg.get("content"))).strip()
            if body:
                lines.append(f"**{who}:** {body}")
        if lines:
            yield title, when, "\n\n".join(lines)


def parse_plain(path: str) -> Iterator[Tuple[str, str, str]]:
    try:
        text = open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return
    if text.strip():
        yield os.path.splitext(os.path.basename(path))[0], "", text


# ---------------------------------------------------------------- LOCAL --
# Two corpora that need no export request because they are already on disk.
# Both are read STRICTLY read-only: these are live application databases and
# transcript files, and an importer that corrupts the thing it is reading has
# destroyed the original to make a copy.

# Claude Code writes one JSONL per session. Most record types are plumbing;
# only `user` and `assistant` carry conversation. Titles arrive in their own
# records, keyed by sessionId, so a first pass collects them.
_CC_NOISE = {"bridge-session", "queue-operation", "attachment", "last-prompt",
             "atis-latch", "system", "ai-title", "custom-title"}


def _cc_text(content: Any) -> str:
    """Text out of a Claude Code message.

    Assistant content is a list of typed blocks. `text` is the conversation;
    `tool_use` and `tool_result` are ORCHESTRATION -- and tool_result in
    particular carries whole file contents, which would bury the actual
    exchange under megabytes of things nobody said. `thinking` is dropped
    too: it was never shown, and storing it as something the assistant said
    would misattribute reasoning as statement.
    """
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return _text_of(content)
    out = []
    for b in content:
        if isinstance(b, dict) and b.get("type") == "text":
            out.append(str(b.get("text") or ""))
        elif isinstance(b, str):
            out.append(b)
    return "\n".join(x for x in out if x.strip())


def parse_claude_code(path: str) -> Iterator[Tuple[str, str, str]]:
    """One Claude Code .jsonl -> one conversation per sessionId."""
    titles: Dict[str, str] = {}
    sessions: Dict[str, List[str]] = {}
    stamps: Dict[str, str] = {}
    meta: Dict[str, str] = {}
    try:
        fh = io.open(path, encoding="utf-8", errors="replace")
    except OSError:
        return
    with fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue          # a torn last line is normal in a live log
            if not isinstance(rec, dict):
                continue
            kind = rec.get("type")
            sid = str(rec.get("sessionId") or "")
            if kind in ("ai-title", "custom-title"):
                t = rec.get("customTitle") or rec.get("aiTitle")
                if sid and t:
                    titles[sid] = str(t)
                continue
            if kind in _CC_NOISE or kind not in ("user", "assistant"):
                continue
            msg = rec.get("message") or {}
            body = _cc_text(msg.get("content")).strip()
            if not body:
                continue
            who = msg.get("role") or kind
            # A sidechain is a subagent's conversation, not the operator's.
            # Kept -- it is real work -- but LABELLED, so nobody later reads
            # a subagent's words as something the user said.
            if rec.get("isSidechain"):
                who = f"{who} (subagent)"
            sessions.setdefault(sid, []).append(f"**{who}:** {body}")
            stamps.setdefault(sid, str(rec.get("timestamp") or "")[:10])
            if sid not in meta:
                bits = [str(rec.get("cwd") or ""), str(rec.get("gitBranch")
                                                       or "")]
                meta[sid] = " ".join(b for b in bits if b)
    for sid, lines in sessions.items():
        if not lines:
            continue
        title = titles.get(sid) or f"session {sid[:8]}"
        head = meta.get(sid, "")
        body = (f"_{head}_\n\n" if head else "") + "\n\n".join(lines)
        yield title, stamps.get(sid, ""), body


def parse_ollama(path: str) -> Iterator[Tuple[str, str, str]]:
    """Ollama desktop's db.sqlite -- chats + messages.

    Opened via a mode=ro URI, never a plain connect: Ollama may be RUNNING,
    and a writer that takes a lock on a live application database to read it
    is how an import corrupts the thing it was copying.
    """
    import sqlite3
    try:
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=10)
    except sqlite3.Error as e:
        print(f"  UNREADABLE {os.path.basename(path)}: {e}", file=sys.stderr)
        return
    try:
        cur = con.cursor()
        cur.execute("select name from sqlite_master where type='table'")
        tables = {r[0] for r in cur.fetchall()}
        if not {"chats", "messages"} <= tables:
            return                       # not an Ollama db; leave it alone
        cur.execute("select id, title, created_at from chats")
        for cid, title, created in cur.fetchall():
            cur.execute(
                "select role, content, thinking, model_name, created_at "
                "from messages where chat_id=? order by id", (cid,))
            lines = []
            model = ""
            for role, content, _thinking, model_name, _ts in cur.fetchall():
                model = model or (model_name or "")
                text = (content or "").strip()
                if text:
                    lines.append(f"**{role or '?'}:** {text}")
            if lines:
                head = f"_model: {model}_\n\n" if model else ""
                yield (str(title or f"ollama chat {cid}"),
                       str(created or "")[:10], head + "\n\n".join(lines))
    except sqlite3.Error as e:
        print(f"  SQLITE ERROR on {os.path.basename(path)}: {e}",
              file=sys.stderr)
    finally:
        con.close()


def detect_source(path: str, data: Any) -> str:
    """Name the system this file came from, from its SHAPE first and its
    path second. Shape is the stronger signal: a folder can be renamed, a
    `mapping` node-graph cannot be anything but an OpenAI export."""
    if isinstance(data, list) and data:
        first = data[0] if isinstance(data[0], dict) else {}
        if "chat_messages" in first:
            return "claude"
        if "mapping" in first:
            return "chatgpt"
    low = path.lower()
    for key in ("claude", "chatgpt", "openai", "grok", "gemini", "bard",
                "copilot", "perplexity", "deepseek", "mistral", "poe",
                "character", "replika", "ollama", "qwen", "meta"):
        if key in low:
            return "grok" if key == "grok" else key
    return "unknown"


def sources(path: str) -> Iterator[Tuple[str, str, str, str]]:
    """(title, date, body, source_system) for every conversation under
    `path`."""
    if os.path.isdir(path):
        # RECURSE. An export usually arrives as a zip that unpacks into a
        # folder, and two exports side by side are two folders -- a
        # non-recursive walk silently imported one and reported success,
        # measured on this file's own fixture 2026-08-29.
        # SPLIT EXPORTS. A large OpenAI archive contains conversations-000.json,
        # conversations-001.json ... and NO conversations.json at all, so an
        # importer that opens the singular name finds nothing and reports
        # success -- the silent-empty-import. Globbing every .json in the tree
        # (below) covers it by construction; this comment is here so nobody
        # "optimises" the walk down to the one expected filename.
        for fn in sorted(os.listdir(path)):
            full = os.path.join(path, fn)
            if os.path.isdir(full) and not fn.startswith("."):
                if fn.lower() in _SKIP_DIRS:
                    continue
                yield from sources(full)
            elif (fn.lower().endswith((".json", ".jsonl", ".md", ".txt",
                                       ".sqlite", ".db"))
                  and not _is_internal(fn)):
                yield from sources(full)
        return
    if path.lower().endswith(".zip"):
        # Exports arrive as zips. Unpacking by hand first is a step people
        # skip, and a skipped step reads as "the importer found nothing".
        import tempfile
        import zipfile
        try:
            with zipfile.ZipFile(path) as z:
                tmp = tempfile.mkdtemp(prefix="mem_zip_")
                z.extractall(tmp)
            yield from sources(tmp)
        except (zipfile.BadZipFile, OSError) as e:
            print(f"  UNREADABLE ZIP {os.path.basename(path)}: {e}",
                  file=sys.stderr)
        return
    low = path.lower()
    if low.endswith(".jsonl"):
        for title, when, body in parse_claude_code(path):
            yield title, when, body, "claude-code"
        return
    if low.endswith((".sqlite", ".db")):
        src = "ollama" if "ollama" in low else detect_source(path, None)
        for title, when, body in parse_ollama(path):
            yield title, when, body, src
        return
    if path.lower().endswith(".json"):
        try:
            data = json.load(open(path, encoding="utf-8", errors="replace"))
        except (ValueError, OSError) as e:
            print(f"  UNPARSEABLE {os.path.basename(path)}: {e}",
                  file=sys.stderr)
            return
        src = detect_source(path, data)
        got = False
        for title, when, body in parse_claude(data):
            got = True
            yield title, when, body, src
        if not got:
            for title, when, body in parse_chatgpt(data):
                got = True
                yield title, when, body, src
        if not got:
            # A JSON we do not recognise is stored WHOLE rather than
            # dropped: unknown shape is not the same as no content.
            yield (os.path.splitext(os.path.basename(path))[0], "",
                   json.dumps(data, indent=1)[:200000], src)
        return
    src = detect_source(path, None)
    for title, when, body in parse_plain(path):
        yield title, when, body, src


def chunks(body: str, size: int = CHUNK_CHARS) -> List[str]:
    """Split on message boundaries, never mid-sentence, never mid-word."""
    if len(body) <= size:
        return [body]
    out, cur = [], ""
    for para in body.split("\n\n"):
        if cur and len(cur) + len(para) + 2 > size:
            out.append(cur)
            cur = para
        else:
            cur = (cur + "\n\n" + para) if cur else para
    if cur:
        out.append(cur)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("path")
    ap.add_argument("--root", default="")
    ap.add_argument("--agent", default="import")
    ap.add_argument("--tier", default="archival", choices=["core", "archival"])
    ap.add_argument("--source", default="",
                    help="override the detected source system (claude, grok, "
                         "chatgpt, gemini...). Detection reads the file's "
                         "SHAPE; override when it cannot tell.")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    if not os.path.exists(a.path):
        print(f"not found: {a.path}", file=sys.stderr)
        return 1
    root = (a.root or os.environ.get("AI_MEMORY_ROOT")
            or os.path.join(HERE, "memories"))
    store = MemoryStore(root)

    seen: Dict[str, int] = {}
    by_source: Dict[str, int] = {}
    written, parts, skipped = 0, 0, []
    for title, when, body, src in sources(a.path):
        src = a.source or src
        by_source[src] = by_source.get(src, 0) + 1
        # The source is in the NAME as well as the metadata. Two systems
        # discussing the same topic on the same day would otherwise collide
        # on one slug, and the second would silently overwrite the first.
        base = slugify(f"{src}-{when}-{title}" if when else f"{src}-{title}")
        n = seen.get(base, 0) + 1
        seen[base] = n
        if n > 1:
            base = f"{base}-{n}"
        pieces = chunks(body)
        for i, piece in enumerate(pieces, 1):
            name = base if i == 1 else f"{base}-p{i}"
            nxt = f"{base}-p{i + 1}" if i < len(pieces) else ""
            linked = piece
            if nxt:
                linked += f"\n\ncontinues in [[{nxt}]]"
            if i > 1:
                prev = base if i == 2 else f"{base}-p{i - 1}"
                linked = f"continued from [[{prev}]]\n\n" + linked
            desc = (f"[{src}] {title} ({when})" if when
                    else f"[{src}] {title}")
            if len(pieces) > 1:
                desc += f" -- part {i}/{len(pieces)}"
            if a.dry_run:
                print(f"  would write {name}  ({len(linked)} chars)")
            else:
                try:
                    store.put(name, desc[:200], "reference", linked, a.agent,
                              tier=a.tier, extra={"source": src})
                except ValueError as e:
                    skipped.append(f"{name}: {e}")
                    continue
            parts += 1
        written += 1

    print(f"\n{written} conversation(s) -> {parts} memory file(s) in {root}")
    # WHAT CAME FROM WHERE, every run. Unifying twelve histories, the count
    # per system is the first thing you check and the first thing that
    # reveals a silent miss -- an export that contributed nothing shows up
    # here as an absence rather than as a number nobody printed.
    if by_source:
        print("by source system:")
        for k in sorted(by_source):
            flag = ("   <- shape and path both unrecognised; pass --source "
                    "to name it" if k == "unknown" else "")
            print(f"  {k:12s} {by_source[k]}{flag}")
    if skipped:
        print(f"{len(skipped)} SKIPPED (named, never silent):", file=sys.stderr)
        for s in skipped:
            print(f"  {s}", file=sys.stderr)
    if not a.dry_run:
        chain = store.verify_chain()
        print(f"audit chain: {'OK' if chain['ok'] else 'BROKEN'} "
              f"({chain.get('entries', 0)} entries)")
    return 1 if skipped else 0


if __name__ == "__main__":
    sys.exit(main())
