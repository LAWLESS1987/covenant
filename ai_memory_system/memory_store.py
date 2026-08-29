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
import tempfile
import threading
import time
from typing import Any, Dict, List, Optional

from index_db import MemoryIndex

_SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,79}$")
GENESIS = "0" * 64

# ---------------------------------------------------------------- BOUNDS --
# STATED, ENFORCED, AND REFUSED AT -- not "reasonable defaults" a flood walks
# quietly past. A store with no ceiling is a disk-exhaustion primitive handed
# to anyone holding the token, and the damage lands on the OPERATOR: a full
# disk takes down the node, the watchdog and the chain sharing that disk.
#
# Generous for a memory store, and finite. Raise by environment where a big
# corpus is intended -- importing 200k conversations is a legitimate reason
# to lift a bound, and lifting it deliberately is not the same as never
# having had one.
MAX_BODY_BYTES = int(os.environ.get("AI_MEMORY_MAX_BODY", 1 << 20))
MAX_MEMORIES = int(os.environ.get("AI_MEMORY_MAX_COUNT", 250000))
MAX_STORE_BYTES = int(os.environ.get("AI_MEMORY_MAX_BYTES", 4 << 30))


class StoreFull(Exception):
    """A bound was reached. Distinct from ValueError on purpose: a caller
    should fix and retry a bad name, and must NOT retry a full store --
    retrying a flood is the flood."""


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
        # ONE WRITER AT A TIME, AND THE LEDGER MOVES WITH THE FILE.
        #
        # Without this the audit chain BREAKS UNDER CONCURRENCY, and breaks
        # the worst way -- silently, discovered later by whoever runs
        # verify. Two racing writes both read the same chain head and both
        # claim it as `prev`, so the chain forks; verify_chain() then
        # reports BROKEN and cannot distinguish a race from an attacker.
        # The integrity check would be accusing the operator of tampering
        # because two agents happened to write at once.
        #
        # Re-entrant: put() and supersede() both call get() while holding
        # it on the same thread.
        self._lock = threading.RLock()
        # THE INDEX IS A CACHE OVER THE FILES, NEVER A SECOND TRUTH.
        #
        # Without it every operation was O(n): list() parsed every file,
        # search() read every file, and each WRITE scanned the directory for
        # bounds and tokenised every stored body to reconcile. Fine at 52
        # memories; unusable at a million -- and "a million should integrate
        # the same way" is the correct requirement, so O(n) was simply the
        # wrong design.
        #
        # If index and files ever disagree, THE FILES WIN and the index is
        # rebuilt. That ordering is what makes a corrupt index an
        # inconvenience instead of a data loss.
        self.index = MemoryIndex(self.root)
        self._bulk = False
        try:
            if self.index.count() != len(self._files()):
                self.index.rebuild(parse_memory, self._files)
        except Exception:            # noqa: BLE001 -- an index that cannot
            pass                     # be built must not stop the store

    def _files(self) -> List[str]:
        try:
            return [f for f in os.listdir(self.root)
                    if f.endswith(".md") and not f.startswith(".")]
        except OSError:
            return []

    def bulk(self, on: bool = True) -> None:
        """Import mode: skip the per-write fsync.

        Durability is per-WRITE for interactive use, because losing the one
        memory somebody just wrote is the failure that matters. A bulk import
        is different: it is re-runnable from the source export, so paying an
        fsync a million times to protect work that can simply be replayed is
        the wrong trade. Ends with one flush."""
        self._bulk = bool(on)
        if not on:
            try:
                os.sync()            # POSIX; Windows has no equivalent call
            except AttributeError:
                pass

    # ------------------------------------------------------- durable write
    @staticmethod
    def _atomic_write(path, text, fsync=True):
        """Write via temp file + fsync + os.replace.

        open(path, "w") TRUNCATES FIRST. A crash, a full disk, or a killed
        process between the truncate and the write leaves a zero-byte or
        half-written memory: the file is still present, still parses as
        "there", and its content is gone. os.replace is atomic on Windows
        and POSIX alike, so a reader sees the old file or the new one and
        never a torn one.
        """
        d = os.path.dirname(path) or "."
        fd, tmp = tempfile.mkstemp(dir=d, prefix=".tmp-", suffix=".part")
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text)
                fh.flush()
                if fsync:
                    os.fsync(fh.fileno())  # the bytes, not just the buffer
            os.replace(tmp, path)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    def _bounds_check(self, name, body):
        """Refuse BEFORE writing, naming the bound and the numbers. A limit
        that reports only "error" teaches the caller to retry, which is
        precisely wrong when the cause is a flood."""
        n = len(body.encode("utf-8"))
        if n > MAX_BODY_BYTES:
            raise StoreFull(
                "memory body is %d bytes, over the %d-byte limit. A memory "
                "is a fact, not a corpus -- chunk it, or raise "
                "AI_MEMORY_MAX_BODY deliberately." % (n, MAX_BODY_BYTES))
        # Counted and summed from the INDEX. This used to listdir and stat
        # every file on every write -- a million syscalls per memory stored.
        count = self.index.count()
        if count >= MAX_MEMORIES and not self.index.has(name):
            raise StoreFull(
                "store holds %d memories, at the %d limit. Existing memories "
                "can still be UPDATED; only new names are refused, so a "
                "flood cannot push out what is already here."
                % (count, MAX_MEMORIES))
        total = self.index.total_bytes()
        if total + n > MAX_STORE_BYTES:
            raise StoreFull(
                "store is %d bytes; this write would pass the %d-byte limit. "
                "Refusing rather than filling the disk that the node and the "
                "watchdog share." % (total, MAX_STORE_BYTES))

    # ---------------------------------------------------------- audit chain
    def _chain_head(self) -> str:
        """The last line's hash, in O(1) -- by seeking to the END of the
        ledger rather than reading all of it.

        Two earlier versions were both wrong, and the second wrong one is
        worth keeping on the record. Reading every line to find the last made
        each write cost O(total writes): storing a memory got slower the more
        you had stored. Caching the head in memory fixed the speed and BROKE
        THE CHAIN -- two MemoryStore instances can share one root (the server
        holds one, a script another), each cached its own head, and the second
        writer appended against a stale one, forking the ledger. The lock is
        per-instance; the file is not.

        So: no cache, and no full read. Seek back from the end for the last
        newline. The file is always consulted, which is what keeps
        independent writers agreeing, and the cost no longer depends on how
        much history there is.
        """
        try:
            with open(self.audit, "rb") as fh:
                fh.seek(0, os.SEEK_END)
                end = fh.tell()
                if end == 0:
                    return GENESIS
                # Walk backwards in blocks until a complete final line is in
                # hand. 4 KiB covers any realistic record in one read.
                block, pos, buf = 4096, end, b""
                while pos > 0:
                    step = min(block, pos)
                    pos -= step
                    fh.seek(pos)
                    buf = fh.read(step) + buf
                    lines = [ln for ln in buf.split(b"\n") if ln.strip()]
                    if len(lines) >= 1 and (pos == 0 or buf.count(b"\n") >= 2):
                        return _sha(lines[-1].decode("utf-8"))
                lines = [ln for ln in buf.split(b"\n") if ln.strip()]
                return _sha(lines[-1].decode("utf-8")) if lines else GENESIS
        except (OSError, UnicodeDecodeError):
            return GENESIS

    def _audit(self, action: str, name: str, agent: str, digest: str) -> None:
        # In bulk mode the ledger flushes but does not fsync, matching the
        # file write beside it. Both are re-derivable from the source export
        # a bulk import is replaying; paying two fsyncs per memory to protect
        # replayable work is the wrong trade, and paying one while skipping
        # the other is just an accident.
        rec = {"at": _now(), "action": action, "name": name, "agent": agent,
               "sha256": digest, "prev": self._chain_head()}
        # fsync: a ledger that loses its last line after the FILE it
        # describes has landed is worse than no ledger -- verify would
        # blame the operator for a write the disk had merely not flushed.
        with open(self.audit, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(rec, sort_keys=True) + "\n")
            fh.flush()
            if not self._bulk:
                os.fsync(fh.fileno())

    def verify_chain(self) -> Dict[str, Any]:
        # Deliberately reads the FILE and ignores the cached head: this is the
        # integrity check, and a check that consults the thing it is checking
        # proves nothing.
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
        with self._lock:
            self._bounds_check(name, body)
            self._atomic_write(path, text, fsync=not self._bulk)
            self._audit(action, name, agent, _sha(text))
            out = parse_memory(text)
            self.index.upsert(out, len(text.encode("utf-8")))
            # A written [[link]] is an ASSERTED edge, not an observed one --
            # never pruned, never decayed away. The system does not get to
            # forget what it was told because it has not needed it lately.
            if out.get("links") and self.index.myc:
                self.index.myc.link_explicit(out["name"], out["links"])
        return out

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
        with self._lock:
            self._atomic_write(self._path(name), text, fsync=not self._bulk)
            out = parse_memory(text)
            self.index.upsert(out, len(text.encode("utf-8")))
        return out

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
        with self._lock:
            self._atomic_write(self._path(old_name), text)
            self._audit("supersede", old_name, agent, _sha(new_name))
            self.index.upsert(parse_memory(text), len(text.encode("utf-8")))
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
        with self._lock:
            if not os.path.exists(path):
                return False        # another thread tombstoned it first
            os.replace(path, os.path.join(self.trash,
                                          f"{name}.{stamp}.md"))
            self._audit("tombstone", name, agent, _sha(why))
            self.index.remove(name)
        return True

    def list(self) -> List[Dict[str, Any]]:
        """From the index -- O(rows), no file reads. Falls back to the files
        if the index is unavailable, because the files are the truth."""
        try:
            out = self.index.list()
            if out or not self._files():
                # links come from the body THIS query already returned. The
                # first version re-queried per row (N+1), which kept list()
                # linear even with an index in front of it.
                return [{"name": m["name"],
                         "description": m.get("description", ""),
                         "metadata": m.get("metadata", {}),
                         "links": sorted(set(re.findall(
                             r"\[\[([a-z0-9-]+)\]\]", m.get("body", ""))))}
                        for m in out]
        except Exception:            # noqa: BLE001
            pass
        return self._list_from_files()

    def _list_from_files(self) -> List[Dict[str, Any]]:
        out = []
        for fn in sorted(self._files()):
            try:
                m = parse_memory(
                    open(os.path.join(self.root, fn), encoding="utf-8").read())
                out.append({k: m.get(k) for k in
                            ("name", "description", "metadata", "links")})
            except (ValueError, OSError):
                out.append({"name": fn[:-3], "description":
                            "(unparseable -- see file)", "metadata": {},
                            "links": []})
        return out

    def search(self, query: str) -> List[Dict[str, Any]]:
        """Full-text through the index. The old version opened and read every
        file in the store for every query."""
        try:
            return [{"name": m["name"],
                     "description": m.get("description", ""),
                     "metadata": m.get("metadata", {})}
                    for m in self.index.search(query, limit=200)]
        except Exception:            # noqa: BLE001
            pass
        q = query.lower()
        hits = []
        for fn in sorted(self._files()):
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
        files = self._files()
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
