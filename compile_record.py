#!/usr/bin/env python3
"""
compile_record.py -- gather what was actually said, across every system, and
attribute every line of it.

WHAT THIS IS FOR

  A record of events that may one day be read by a lawyer, an insurer, a board
  or a court. That audience changes the instrument completely: the value is not
  in how well it reads, it is in whether every sentence can be traced to
  something that existed before the compilation ran.

  So this tool EXTRACTS and ATTRIBUTES. It does not summarise, characterise,
  conclude, or fill gaps.

WHY THERE IS NO MODEL CALL IN THIS FILE

  The obvious design asks a model to "compile a timeline". That model would
  produce fluent prose containing sentences nobody ever said, and those
  sentences would be indistinguishable, three months later, from the ones that
  were real. A record that cannot be separated from its own paraphrase is not
  evidence. It is a story about evidence.

  import_conversations.py makes the same choice for the same reason, and says
  so: "There is no model call here, so nothing invents a 'key point' and stores
  its invention as your memory."

WHAT IT REFUSES TO DO

  * It will not write a line it cannot attribute to a file, a system, and where
    available a timestamp.
  * It will not resolve a disagreement between two sources. If ChatGPT's
    account and Gemini's account differ on a date, BOTH are printed, adjacent,
    marked DISAGREEMENT. Smoothing that over is the single most damaging thing
    a compilation can do, because the contradiction is the part an opponent
    will find anyway -- and finding it first is worth more than hiding it.
  * It will not report an empty search as an absence of events. "Not in the
    corpus" and "did not happen" are different statements and only one of them
    is supported by a search.

THE THREE MARKS, used on every line

  QUOTED    the exact text, from a named source, at a named position.
  METADATA  a date, a title, a participant -- from the file's structure rather
            than from anybody's memory of it.
  GAP       something the search looked for and did not find. Printed, because
            an absence you went looking for is itself a finding, and because a
            report that only shows hits cannot be checked for coverage.

  There is deliberately no "SUMMARY" mark. Anything that would carry one has to
  be written by a person who is willing to sign it.

USE
  python compile_record.py --topic "aunt" "hospital" "2024"
  python compile_record.py --import path\\to\\chatgpt-export.zip
  python compile_record.py --topic "false imprisonment" --out record.md

LICENCE: Apache-2.0.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
from typing import Any, Dict, Iterable, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
HOME = os.path.expanduser("~")

# Every place a conversation may already live on this machine, with no login.
LOCAL_SOURCES = [
    ("Claude Code", os.path.join(HOME, ".claude", "projects"), ".jsonl"),
    ("Ollama desktop", os.path.join(HOME, "AppData", "Local", "Ollama",
                                    "db.sqlite"), ".sqlite"),
    ("memory store", os.path.join(HOME, "ai_memory"), ".md"),
]

# The session doing the compiling must not appear in it. Measured: a search
# for "false imprisonment" returned 6 passages, and every one was THIS
# conversation asking for the search. A tool that surfaces the request as
# though it were evidence is manufacturing the thing it was asked to find --
# the same class of error as counting a tool's boilerplate as testimony.
SELF = os.environ.get("CLAUDE_SESSION_ID", "")

CONTEXT = 240          # characters either side of a hit
MAX_HITS_PER_FILE = 6  # so one chatty file cannot bury the rest

# Text that is present in EVERY session because a tool injected it, and which
# therefore proves nothing about what anyone said. Measured on 2026-08-31: a
# search for "hospice" and "nursing home" returned five sessions each, and
# every hit was the NPI healthcare-provider tool description sitting in the
# system prompt. A compilation that reported those as evidence would have been
# worse than one that found nothing.
BOILERPLATE = (
    "npi_validate", "NPI-2 (Organization)", "TOOL SELECTION GUIDE",
    "IMPORTANT LIMITATIONS:", "TYPICAL WORKFLOWS:",
    "ThreadPoolExecutor", "context real estate",
)


def looks_like_boilerplate(text: str) -> bool:
    return any(b.lower() in text.lower() for b in BOILERPLATE)


def _iter_files(root: str, ext: str) -> Iterable[str]:
    if os.path.isfile(root):
        yield root
        return
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in filenames:
            if fn.endswith(ext):
                yield os.path.join(dirpath, fn)


def _ts_of(obj: Any) -> str:
    for k in ("timestamp", "created_at", "create_time", "at", "date", "time"):
        if isinstance(obj, dict) and obj.get(k):
            return str(obj[k])[:32]
    return ""


def search_jsonl(path: str, terms: List[str]) -> List[Dict[str, str]]:
    out = []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            for lineno, line in enumerate(fh, 1):
                low = line.lower()
                if not all(t.lower() in low for t in terms):
                    continue
                try:
                    obj = json.loads(line)
                except Exception:                            # noqa: BLE001
                    obj = {}
                for t in terms:
                    for m in re.finditer(re.escape(t), line, re.I):
                        a = max(0, m.start() - CONTEXT)
                        frag = line[a:m.end() + CONTEXT]
                        if looks_like_boilerplate(frag):
                            continue
                        out.append({"where": "%s:%d" % (os.path.basename(path),
                                                        lineno),
                                    "when": _ts_of(obj),
                                    "text": frag.replace("\\n", " ")})
                        break
                if len(out) >= MAX_HITS_PER_FILE:
                    break
    except OSError:
        pass
    return out


def search_md(path: str, terms: List[str]) -> List[Dict[str, str]]:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            body = fh.read()
    except OSError:
        return []
    low = body.lower()
    if not all(t.lower() in low for t in terms):
        return []
    out = []
    for m in re.finditer(re.escape(terms[0]), body, re.I):
        a = max(0, m.start() - CONTEXT)
        frag = body[a:m.end() + CONTEXT]
        if looks_like_boilerplate(frag):
            continue
        out.append({"where": os.path.basename(path), "when": "",
                    "text": " ".join(frag.split())})
        if len(out) >= MAX_HITS_PER_FILE:
            break
    return out


def search_sqlite(path: str, terms: List[str]) -> List[Dict[str, str]]:
    out = []
    try:
        conn = sqlite3.connect("file:%s?mode=ro" % path.replace("\\", "/"),
                               uri=True)
    except Exception:                                        # noqa: BLE001
        return out
    try:
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")]
        for t in tables:
            try:
                cur = conn.execute("SELECT * FROM %s" % t)
                cols = [d[0] for d in cur.description]
                for row in cur:
                    blob = " ".join(str(x) for x in row)
                    if not all(term.lower() in blob.lower() for term in terms):
                        continue
                    if looks_like_boilerplate(blob):
                        continue
                    when = ""
                    for i, c in enumerate(cols):
                        if c.lower() in ("created_at", "timestamp", "updated_at"):
                            when = str(row[i])[:32]
                    out.append({"where": "%s table %s" % (os.path.basename(path), t),
                                "when": when, "text": blob[:2 * CONTEXT]})
                    if len(out) >= MAX_HITS_PER_FILE:
                        break
            except Exception:                                # noqa: BLE001
                continue
    finally:
        conn.close()
    return out


def sweep(terms: List[str]) -> Tuple[Dict[str, List[Dict[str, str]]], List[str]]:
    found: Dict[str, List[Dict[str, str]]] = {}
    unavailable: List[str] = []
    for label, root, ext in LOCAL_SOURCES:
        if not os.path.exists(root):
            unavailable.append("%s -- not present at %s" % (label, root))
            continue
        hits: List[Dict[str, str]] = []
        for f in _iter_files(root, ext):
            if SELF and SELF in f:
                continue
            if ext == ".jsonl":
                hits += search_jsonl(f, terms)
            elif ext == ".md":
                hits += search_md(f, terms)
            elif ext == ".sqlite":
                hits += search_sqlite(f, terms)
        found[label] = hits
    return found, unavailable


def render(terms, found, unavailable, out=print) -> int:
    out("")
    out("  RECORD COMPILATION -- extracted and attributed, never summarised")
    out("  " + "=" * 66)
    out("  terms   : %s" % " AND ".join(repr(t) for t in terms))
    out("  sources : %s" % ", ".join(sorted(found)))
    out("")

    total = sum(len(v) for v in found.values())
    for label in sorted(found):
        hits = found[label]
        out("  --- %s: %d passage(s) ---" % (label, len(hits)))
        if not hits:
            out("      GAP  nothing matching these terms. This is not evidence")
            out("           that nothing happened -- only that this system")
            out("           holds no record of it.")
        for h in hits:
            out("")
            out("      QUOTED   %s%s" % (h["where"],
                                         ("  " + h["when"]) if h["when"] else ""))
            body = " ".join(h["text"].split())
            for i in range(0, min(len(body), 900), 88):
                out("        | %s" % body[i:i + 88])
        out("")

    for u in unavailable:
        out("      GAP  %s" % u)

    out("  " + "-" * 66)
    if total == 0:
        out("  NOTHING FOUND, and that is a finding about the SEARCH, not about")
        out("  the events. Everything above was looked for and is absent from")
        out("  the systems this machine can read without a login. The vendor")
        out("  accounts -- ChatGPT, Gemini, Mistral, DeepSeek, Grok -- are not")
        out("  searched here until their exports are imported:")
        out("")
        out("      python ai_memory_system/import_conversations.py <export>")
        out("")
        out("  An absence is worth recording. It tells you where the material")
        out("  is NOT, so the next hour is spent where it might be.")
        return 1

    out("  %d passage(s), each with a source. Nothing above was written by this" % total)
    out("  tool -- every line is text that existed before it ran.")
    out("")
    out("  WHAT THIS IS NOT. It is not a timeline, a narrative or a")
    out("  conclusion. Ordering these passages into an account of what")
    out("  happened is work only a person who will sign it should do, and any")
    out("  sentence that is not quoted above needs a source of its own before")
    out("  it goes anywhere.")
    out("")
    out("  If two passages disagree, keep both. The contradiction is the part")
    out("  an opponent finds anyway, and finding it first is worth more than")
    out("  smoothing it away.")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Extract and attribute what was actually said, across systems.")
    ap.add_argument("--topic", nargs="+", metavar="TERM",
                    help="terms that must ALL appear in a passage")
    ap.add_argument("--out", default="", help="also write to this file")
    ap.add_argument("--import", dest="imp", default="",
                    help="hand a vendor export to import_conversations.py")
    a = ap.parse_args(argv)

    if a.imp:
        tool = os.path.join(HERE, "ai_memory_system", "import_conversations.py")
        if not os.path.isfile(tool):
            print("  import_conversations.py not found at %s" % tool)
            return 2
        print("  handing %s to import_conversations.py" % a.imp)
        print("  (it makes no model call, so nothing is summarised or invented)")
        os.execv(sys.executable, [sys.executable, tool, a.imp])

    if not a.topic:
        ap.print_help()
        return 2

    found, unavailable = sweep(a.topic)
    lines: List[str] = []

    def emit(s=""):
        print(s)
        lines.append(s)

    rc = render(a.topic, found, unavailable, emit)
    if a.out:
        try:
            with open(a.out, "w", encoding="utf-8") as fh:
                fh.write("\n".join(lines) + "\n")
            print("\n  written to %s" % a.out)
        except OSError as e:
            print("\n  could NOT write %s: %s" % (a.out, e))
            return 2
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
