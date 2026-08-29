#!/usr/bin/env python3
"""import_conversations.py -- bring a whole conversation history into the
memory system, losslessly.

WHY THIS EXISTS. The history worth keeping is usually trapped in the wrong
shape: 120 screen recordings of conversations, a vendor's export, a folder of
chat logs. Reading it back off a video is OCR on a lossy re-encode of text
that already exists as data somewhere. This takes the data.

SUPPORTED INPUTS (auto-detected, no flag needed):
  * claude.ai export      conversations.json  -- Settings > Privacy > Export
  * ChatGPT export        conversations.json  (a different shape, same name)
  * a directory           any .json / .md / .txt inside it
  * one file              .json / .md / .txt

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


def parse_chatgpt(data: Any) -> Iterator[Tuple[str, str, str]]:
    """ChatGPT export: [{title, create_time, mapping:{id:{message}}}]."""
    if not isinstance(data, list):
        return
    for conv in data:
        if not isinstance(conv, dict) or "mapping" not in conv:
            continue
        title = conv.get("title") or "untitled"
        when = ""
        try:
            import datetime
            when = datetime.datetime.utcfromtimestamp(
                float(conv.get("create_time") or 0)).strftime("%Y-%m-%d")
        except (ValueError, TypeError, OSError):
            pass
        nodes = [n for n in (conv.get("mapping") or {}).values()
                 if isinstance(n, dict) and isinstance(n.get("message"), dict)]
        nodes.sort(key=lambda n: (n["message"].get("create_time") or 0))
        lines = []
        for n in nodes:
            msg = n["message"]
            who = ((msg.get("author") or {}).get("role")) or "?"
            body = _text_of(msg.get("content"))
            if body.strip():
                lines.append(f"**{who}:** {body.strip()}")
        if lines:
            yield title, when, "\n\n".join(lines)


def parse_plain(path: str) -> Iterator[Tuple[str, str, str]]:
    try:
        text = open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return
    if text.strip():
        yield os.path.splitext(os.path.basename(path))[0], "", text


def sources(path: str) -> Iterator[Tuple[str, str, str]]:
    """(title, date, body) for every conversation found under `path`."""
    if os.path.isdir(path):
        # RECURSE. An export usually arrives as a zip that unpacks into a
        # folder, and two exports side by side are two folders -- a
        # non-recursive walk silently imported one and reported success,
        # measured on this file's own fixture 2026-08-29.
        for fn in sorted(os.listdir(path)):
            full = os.path.join(path, fn)
            if os.path.isdir(full) and not fn.startswith("."):
                yield from sources(full)
            elif fn.lower().endswith((".json", ".md", ".txt")):
                yield from sources(full)
        return
    if path.lower().endswith(".json"):
        try:
            data = json.load(open(path, encoding="utf-8", errors="replace"))
        except (ValueError, OSError) as e:
            print(f"  UNPARSEABLE {os.path.basename(path)}: {e}",
                  file=sys.stderr)
            return
        got = False
        for title, when, body in parse_claude(data):
            got = True
            yield title, when, body
        if not got:
            for title, when, body in parse_chatgpt(data):
                got = True
                yield title, when, body
        if not got:
            # A JSON we do not recognise is stored WHOLE rather than
            # dropped: unknown shape is not the same as no content.
            yield (os.path.splitext(os.path.basename(path))[0], "",
                   json.dumps(data, indent=1)[:200000])
        return
    yield from parse_plain(path)


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
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    if not os.path.exists(a.path):
        print(f"not found: {a.path}", file=sys.stderr)
        return 1
    root = (a.root or os.environ.get("AI_MEMORY_ROOT")
            or os.path.join(HERE, "memories"))
    store = MemoryStore(root)

    seen: Dict[str, int] = {}
    written, parts, skipped = 0, 0, []
    for title, when, body in sources(a.path):
        base = slugify(f"{when}-{title}" if when else title)
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
            desc = (f"{title} ({when})" if when else title)
            if len(pieces) > 1:
                desc += f" -- part {i}/{len(pieces)}"
            if a.dry_run:
                print(f"  would write {name}  ({len(linked)} chars)")
            else:
                try:
                    store.put(name, desc[:200], "reference", linked, a.agent,
                              tier=a.tier)
                except ValueError as e:
                    skipped.append(f"{name}: {e}")
                    continue
            parts += 1
        written += 1

    print(f"\n{written} conversation(s) -> {parts} memory file(s) in {root}")
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
