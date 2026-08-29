"""memory_store.py -- the persistent store under the AI memory system.

One memory, one markdown file, the same shape Claude's own session memory
uses -- so integrating an agent's existing memory directory is a file copy,
not a translation:

    ---
    name: <kebab-case-slug>
    description: <one line, used for recall relevance>
    metadata:
      type: user | feedback | project | reference
      agent: <who wrote it>
    ---
    <the fact. [[other-name]] links other memories.>

WHAT THIS STORE PROMISES, in covenant terms:
  * APPEND-ONLY HISTORY. Every write and every tombstone is a line in
    audit.jsonl, and each line carries the sha256 of the line before it --
    a hash chain, so an edit to history is detectable by anyone holding a
    later line. verify_chain() is the check; it is cheap, run it freely.
  * NO SILENT DELETION. delete() writes a tombstone and moves the file to
    .trash/ -- the memory leaves the index, never the record. What one
    agent wrote, another may retire but may not erase.
  * SELF-DESCRIPTION. state() reports the count, the newest write, and the
    chain head, so a reader can know WHAT it is reading before trusting it.

Stdlib only, deliberately: this must run wherever a python does, with no
environment to assemble -- the same constraint that shaped the semantic
judge (a phone under Termux builds no scipy).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from typing import Any, Dict, List, Optional

_SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,79}$")
GENESIS = "0" * 64


def _now() -> float:
    return time.time()


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_memory(text: str) -> Dict[str, Any]:
    """Frontmatter + body -> dict. Tolerant of the two-space YAML nesting the
    memory format uses; deliberately NOT a YAML engine -- the format is four
    known keys, and a parser that accepts more accepts injections too."""
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n(.*)$", text, re.S)
    if not m:
        raise ValueError("not a memory file: missing frontmatter fences")
    head, body = m.group(1), m.group(2).strip()
    meta: Dict[str, Any] = {"metadata": {}}
    in_meta = False
    for line in head.splitlines():
        if not line.strip():
            continue
        if line.startswith("metadata:"):
            in_meta = True
            continue
        if in_meta and line.startswith("  ") and ":" in line:
            k, v = line.strip().split(":", 1)
            meta["metadata"][k.strip()] = v.strip()
            continue
        in_meta = False
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    if not meta.get("name"):
        raise ValueError("memory has no name")
    meta["body"] = body
    meta["links"] = sorted(set(re.findall(r"\[\[([a-z0-9-]+)\]\]", body)))
    return meta


def render_memory(name: str, description: str, mtype: str, body: str,
                  agent: str, extra: Optional[Dict[str, Any]] = None) -> str:
    """The frontmatter other agents already parse, plus whatever recall
    fields this write carries (tier, uses, last_used, supersedes...). Extra
    keys are written in sorted order so the file is byte-stable for the same
    inputs -- a memory whose bytes churn on every write cannot be diffed."""
    lines = [f"---", f"name: {name}", f"description: {description}",
             "metadata:", f"  type: {mtype}", f"  agent: {agent}"]
    for k in sorted(extra or {}):
        v = (extra or {})[k]
        if v not in (None, ""):
            lines.append(f"  {k}: {v}")
    lines += ["---", ""]
    return "\n".join(lines) + f"\n{body.strip()}\n"


class MemoryStore:
    def __init__(self, root: str):
        self.root = os.path.abspath(root)
        self.trash = os.path.join(self.root, ".trash")
        self.audit = os.path.join(self.root, "audit.jsonl")
        os.makedirs(self.root, exist_ok=True)
        os.makedirs(self.trash, exist_ok=True)

    # ---------------------------------------------------------- audit chain
    def _chain_head(self) -> str:
        head = GENESIS
        try:
            with open(self.audit, encoding="utf-8") as fh:
                for line in fh:
                    if line.strip():
                        head = _sha(line.rstrip("\n"))
        except OSError:
            pass
        return head

    def _audit(self, action: str, name: str, agent: str, digest: str) -> None:
        rec = {"at": _now(), "action": action, "name": name, "agent": agent,
               "sha256": digest, "prev": self._chain_head()}
        with open(self.audit, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(rec, sort_keys=True) + "\n")

    def verify_chain(self) -> Dict[str, Any]:
        """Walk the audit chain; the first broken link is named, not summed
        away. An empty ledger verifies -- an absent one is a fresh store,
        not a corrupt one."""
        prev, n = GENESIS, 0
        try:
            with open(self.audit, encoding="utf-8") as fh:
                for i, line in enumerate(fh, 1):
                    if not line.strip():
                        continue
                    rec = json.loads(line)
                    if rec.get("prev") != prev:
                        return {"ok": False, "entries": n, "broken_at": i,
                                "expected": prev, "found": rec.get("prev")}
                    prev = _sha(line.rstrip("\n"))
                    n += 1
        except OSError:
            pass
        return {"ok": True, "entries": n, "head": prev}

    # --------------------------------------------------------------- files
    def _path(self, name: str) -> str:
        if not _SLUG.match(name):
            raise ValueError(f"bad memory name {name!r}: kebab-case, <=80")
        return os.path.join(self.root, name + ".md")

    def put(self, name: str, description: str, mtype: str, body: str,
            agent: str, tier: str = "archival",
            extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if mtype not in ("user", "feedback", "project", "reference"):
            raise ValueError(f"bad type {mtype!r}")
        if tier not in ("core", "archival"):
            raise ValueError(f"bad tier {tier!r}: core|archival")
        path = self._path(name)
        action = "update" if os.path.exists(path) else "create"
        # A rewrite KEEPS the memory's use history. Resetting `uses` on every
        # edit would make an often-corrected memory look cold, which is
        # backwards: correction is use.
        meta: Dict[str, Any] = {"tier": tier, "uses": 0,
                                "last_used": int(_now())}
        if action == "update":
            old = (self.get(name) or {}).get("metadata") or {}
            meta["uses"] = int(old.get("uses", 0) or 0)
            meta["last_used"] = old.get("last_used", meta["last_used"])
        meta.update(extra or {})
        text = render_memory(name, description, mtype, body, agent, meta)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        self._audit(action, name, agent, _sha(text))
        return parse_memory(text)

    def touch(self, name: str) -> Optional[Dict[str, Any]]:
        """Record that a memory was USED: +1 use, stamp the clock. This is
        the reinforcement half of consolidation (see recall.strength).

        Deliberately NOT audited. The ledger records what agents CLAIM about
        the world; reads are traffic, and a chain that grows on every recall
        would bury the writes that matter under noise. Use counts live in
        the file and are therefore also visible in a diff."""
        m = self.get(name)
        if m is None:
            return None
        meta = m.get("metadata") or {}
        meta["uses"] = int(meta.get("uses", 0) or 0) + 1
        meta["last_used"] = int(_now())
        text = render_memory(m["name"], m.get("description", ""),
                             meta.get("type", "reference"), m["body"],
                             meta.get("agent", "unknown"), meta)
        with open(self._path(name), "w", encoding="utf-8",
                  newline="\n") as fh:
            fh.write(text)
        return parse_memory(text)

    def supersede(self, old_name: str, new_name: str, agent: str) -> bool:
        """Mark old as superseded BY new, keeping both. The destructive
        update this store refuses to perform -- see recall.reconcile."""
        old = self.get(old_name)
        if old is None:
            return False
        meta = dict(old.get("metadata") or {})
        meta["superseded_by"] = new_name
        text = render_memory(old["name"], old.get("description", ""),
                             meta.get("type", "reference"), old["body"],
                             meta.get("agent", "unknown"), meta)
        with open(self._path(old_name), "w", encoding="utf-8",
                  newline="\n") as fh:
            fh.write(text)
        self._audit("supersede", old_name, agent, _sha(new_name))
        return True

    def get(self, name: str) -> Optional[Dict[str, Any]]:
        path = self._path(name)
        if not os.path.exists(path):
            return None
        return parse_memory(open(path, encoding="utf-8").read())

    def delete(self, name: str, agent: str, why: str = "") -> bool:
        """Tombstone, never erasure: the file moves to .trash/ with a stamp
        and the chain records who retired it and why."""
        path = self._path(name)
        if not os.path.exists(path):
            return False
        stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        os.replace(path, os.path.join(self.trash, f"{name}.{stamp}.md"))
        self._audit("tombstone", name, agent, _sha(why))
        return True

    def list(self) -> List[Dict[str, Any]]:
        out = []
        for fn in sorted(os.listdir(self.root)):
            if fn.endswith(".md") and not fn.startswith("."):
                try:
                    m = parse_memory(
                        open(os.path.join(self.root, fn),
                             encoding="utf-8").read())
                    out.append({k: m.get(k) for k in
                                ("name", "description", "metadata", "links")})
                except (ValueError, OSError):
                    out.append({"name": fn[:-3], "description":
                                "(unparseable -- see file)", "metadata": {},
                                "links": []})
        return out

    def search(self, query: str) -> List[Dict[str, Any]]:
        """Case-insensitive substring over name, description and body.
        Deliberately dumb: a store this size needs recall, not ranking, and
        a scorer nobody can explain is a judge nobody can check."""
        q = query.lower()
        hits = []
        for fn in sorted(os.listdir(self.root)):
            if not fn.endswith(".md") or fn.startswith("."):
                continue
            try:
                text = open(os.path.join(self.root, fn),
                            encoding="utf-8").read()
            except OSError:
                continue
            if q in text.lower():
                m = parse_memory(text)
                hits.append({"name": m["name"],
                             "description": m.get("description", ""),
                             "metadata": m.get("metadata", {})})
        return hits

    def state(self) -> Dict[str, Any]:
        files = [f for f in os.listdir(self.root)
                 if f.endswith(".md") and not f.startswith(".")]
        newest = 0.0
        for f in files:
            try:
                newest = max(newest,
                             os.path.getmtime(os.path.join(self.root, f)))
            except OSError:
                pass
        chain = self.verify_chain()
        return {"memories": len(files), "newest_write_epoch": newest,
                "audit": chain, "root": self.root}
