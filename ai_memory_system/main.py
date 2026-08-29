#!/usr/bin/env python3
"""main.py -- the AI memory system's one entry point.

    python main.py server --host 127.0.0.1 --port 8000
    python main.py server --host 0.0.0.0 --port 8000 --token $AI_MEMORY_TOKEN
    python main.py put   <name> --description "..." --type project \
                         --body "..." --agent claude
    python main.py get   <name>
    python main.py list
    python main.py search "<query>"
    python main.py verify            # walk the audit chain, name any break
    python main.py import <dir>      # adopt an existing memory directory

WHERE MEMORIES LIVE. --root, else $AI_MEMORY_ROOT, else ./memories beside
this file. One directory of markdown files; back it up by copying it, read
it with any text editor, put it in git if you want its history doubly kept.
A memory store you can only read through its own API is a store you cannot
audit when the API is the thing that is wrong.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from memory_store import MemoryStore, parse_memory   # noqa: E402
import server                                        # noqa: E402


def _root(args) -> str:
    return (args.root or os.environ.get("AI_MEMORY_ROOT")
            or os.path.join(HERE, "memories"))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="main.py", description="AI memory system")
    ap.add_argument("--root", default="",
                    help="memory directory (default: $AI_MEMORY_ROOT or "
                         "./memories)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("server", help="run the HTTP server")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8000)
    s.add_argument("--token", default="",
                   help="bearer token; REQUIRED to bind beyond loopback. "
                        "Falls back to $AI_MEMORY_TOKEN.")

    p = sub.add_parser("put", help="write one memory")
    p.add_argument("name")
    p.add_argument("--description", required=True)
    p.add_argument("--type", default="project",
                   choices=["user", "feedback", "project", "reference"])
    p.add_argument("--body", required=True)
    p.add_argument("--agent", default="cli")

    g = sub.add_parser("get", help="read one memory")
    g.add_argument("name")

    sub.add_parser("list", help="list every memory")

    q = sub.add_parser("search", help="substring recall")
    q.add_argument("query")

    sub.add_parser("verify", help="walk the audit chain")

    i = sub.add_parser("import", help="adopt an existing memory directory")
    i.add_argument("source")
    i.add_argument("--agent", default="import")

    a = ap.parse_args(argv)
    root = _root(a)

    if a.cmd == "server":
        return server.serve(a.host, a.port, root,
                            a.token or os.environ.get("AI_MEMORY_TOKEN", ""))

    store = MemoryStore(root)

    if a.cmd == "put":
        out = store.put(a.name, a.description, a.type, a.body, a.agent)
        print(json.dumps(out, indent=1, sort_keys=True))
        return 0

    if a.cmd == "get":
        got = store.get(a.name)
        if got is None:
            print(f"no such memory: {a.name}", file=sys.stderr)
            return 1
        print(json.dumps(got, indent=1, sort_keys=True))
        return 0

    if a.cmd == "list":
        items = store.list()
        for m in items:
            print(f"{m['name']:40s} {m.get('description', '')[:80]}")
        print(f"\n{len(items)} memory(ies) in {store.root}")
        return 0

    if a.cmd == "search":
        hits = store.search(a.query)
        for h in hits:
            print(f"{h['name']:40s} {h.get('description', '')[:80]}")
        print(f"\n{len(hits)} hit(s) for {a.query!r}")
        return 0

    if a.cmd == "verify":
        chain = store.verify_chain()
        print(json.dumps(chain, indent=1, sort_keys=True))
        if not chain["ok"]:
            print("\nAUDIT CHAIN BROKEN -- the ledger was edited after the "
                  "fact, or a line was lost. The memories may still be "
                  "correct; what is gone is the proof.", file=sys.stderr)
            return 1
        return 0

    if a.cmd == "import":
        # Adopt a directory of existing memory files -- e.g. a Claude session
        # memory folder. Anything that does not parse is REPORTED and skipped,
        # never silently dropped: a partial import that says it was total is
        # how a memory system starts lying.
        src = os.path.abspath(a.source)
        if not os.path.isdir(src):
            print(f"not a directory: {src}", file=sys.stderr)
            return 1
        took, skipped = [], []
        for fn in sorted(os.listdir(src)):
            if not fn.endswith(".md") or fn.upper().startswith("MEMORY"):
                continue
            path = os.path.join(src, fn)
            try:
                m = parse_memory(open(path, encoding="utf-8").read())
                store.put(m["name"], m.get("description", ""),
                          (m.get("metadata") or {}).get("type", "reference"),
                          m["body"], a.agent)
                took.append(m["name"])
            except (ValueError, OSError) as e:
                skipped.append(f"{fn}: {type(e).__name__}: {e}")
        for name in took:
            print(f"  imported {name}")
        for s_ in skipped:
            print(f"  SKIPPED  {s_}", file=sys.stderr)
        print(f"\n{len(took)} imported, {len(skipped)} skipped, into "
              f"{store.root}")
        return 1 if skipped else 0

    return 2


if __name__ == "__main__":
    sys.exit(main())
