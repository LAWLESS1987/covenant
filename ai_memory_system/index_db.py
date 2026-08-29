"""index_db.py -- the index that makes one memory and a million memories cost
the same to reach.

WHY. The file store was O(n) in the worst places: list() parsed every file,
search() read every file, /recall read every file TWICE, and every single
write scanned the whole directory (bounds) and tokenised every stored body
(reconcile). At 52 memories that is invisible. At a million it is a system
that cannot be used at all -- and "it should integrate the same way at a
million" is the correct requirement, so the O(n) design was simply wrong.

WHAT THIS IS NOT. It is NOT a second source of truth. The markdown files are
the truth: readable in an editor, diffable, restorable by copying a folder.
This is a CACHE, and it is rebuildable from the files at any time
(`rebuild()`). If the index and the files ever disagree, the files win and
the index is discarded -- which is the only ordering under which a corrupt
index is an inconvenience rather than a data loss.

Deliberately sqlite3 from the stdlib, and FTS5 only if this Python has it,
with a LIKE fallback that is slower but always present. A store that cannot
open on the machine it is needed on has no advantages.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = 1


def _has_fts5(con: sqlite3.Connection) -> bool:
    try:
        con.execute("create virtual table if not exists _fts5probe "
                    "using fts5(x)")
        con.execute("drop table _fts5probe")
        return True
    except sqlite3.Error:
        return False


class MemoryIndex:
    """name -> (description, metadata, size) plus full-text over the body."""

    def __init__(self, root: str):
        self.root = os.path.abspath(root)
        self.path = os.path.join(self.root, ".index.db")
        self._lock = threading.RLock()
        self._con = sqlite3.connect(self.path, check_same_thread=False)
        self._con.execute("pragma journal_mode=WAL")
        # The index is a cache. Losing the last few rows to a power cut costs
        # a rebuild, not data -- so it does not need the fsync-per-write the
        # FILES get. This is the one place in the system where durability is
        # deliberately traded for speed, and it is safe exactly because the
        # files are the truth.
        self._con.execute("pragma synchronous=NORMAL")
        self.fts = _has_fts5(self._con)
        try:
            self._create()
        except sqlite3.DatabaseError:
            # A corrupt index is recoverable BY CONSTRUCTION -- the markdown
            # files are the truth. Throw the file away and start clean rather
            # than propagate a database error into the store.
            self._con.close()
            try:
                os.unlink(self.path)
            except OSError:
                pass
            self._con = sqlite3.connect(self.path, check_same_thread=False)
            self._con.execute("pragma journal_mode=WAL")
            self._con.execute("pragma synchronous=NORMAL")
            self.fts = _has_fts5(self._con)
            self._create()

    def _create(self) -> None:
        c = self._con
        c.execute("""create table if not exists meta
                     (k text primary key, v text)""")
        # An explicit integer id, because FTS5 rows are addressed by rowid.
        # The first version used an EXTERNAL-CONTENT fts table
        # (content='memories') and wrote to it directly -- which sqlite
        # detects as "database disk image is malformed", because an
        # external-content index must be kept in step through its own
        # command syntax and cannot simply be inserted into. A standalone
        # index keyed by this id is duller and correct.
        c.execute("""create table if not exists memories (
                        id integer primary key autoincrement,
                        name text unique not null,
                        description text not null default '',
                        body text not null default '',
                        metadata text not null default '{}',
                        size integer not null default 0,
                        source text not null default 'unknown',
                        tier text not null default 'archival',
                        uses integer not null default 0,
                        last_used integer not null default 0)""")
        c.execute("create index if not exists mem_source on memories(source)")
        c.execute("create index if not exists mem_tier on memories(tier)")
        if self.fts:
            c.execute("""create virtual table if not exists memories_fts
                         using fts5(name, description, body)""")
        c.execute("insert or replace into meta values ('schema', ?)",
                  (str(SCHEMA_VERSION),))
        c.commit()

    # ------------------------------------------------------------- writing
    def upsert(self, mem: Dict[str, Any], size: int = 0) -> None:
        meta = mem.get("metadata") or {}
        name = mem.get("name")
        desc = mem.get("description", "")
        body = mem.get("body", "")
        with self._lock:
            prev = self._con.execute(
                "select size from memories where name=?", (name,)).fetchone()
            self._con.execute(
                """insert into memories
                   (name, description, body, metadata, size, source, tier,
                    uses, last_used)
                   values (?,?,?,?,?,?,?,?,?)
                   on conflict(name) do update set
                     description=excluded.description, body=excluded.body,
                     metadata=excluded.metadata, size=excluded.size,
                     source=excluded.source, tier=excluded.tier,
                     uses=excluded.uses, last_used=excluded.last_used""",
                (name, desc, body, json.dumps(meta, sort_keys=True), size,
                 str(meta.get("source", "unknown")),
                 str(meta.get("tier", "archival")),
                 int(meta.get("uses", 0) or 0),
                 int(float(meta.get("last_used", 0) or 0))))
            if self.fts:
                row = self._con.execute(
                    "select id from memories where name=?", (name,)).fetchone()
                if row:
                    rid = row[0]
                    self._con.execute(
                        "delete from memories_fts where rowid=?", (rid,))
                    self._con.execute(
                        "insert into memories_fts(rowid, name, description, "
                        "body) values (?,?,?,?)", (rid, name, desc, body))
            if prev is None:
                self._bump("count", 1)
                self._bump("bytes", size)
            else:
                self._bump("bytes", size - int(prev[0] or 0))
            self._con.commit()

    def remove(self, name: str) -> None:
        with self._lock:
            row = self._con.execute(
                "select id, size from memories where name=?",
                (name,)).fetchone()
            if row:
                if self.fts:
                    self._con.execute(
                        "delete from memories_fts where rowid=?", (row[0],))
                self._con.execute("delete from memories where name=?", (name,))
                self._bump("count", -1)
                self._bump("bytes", -int(row[1] or 0))
            self._con.commit()

    # ------------------------------------------------------------- reading
    def _stat(self, key: str) -> int:
        row = self._con.execute("select v from meta where k=?",
                                (key,)).fetchone()
        return int(row[0]) if row and str(row[0]).lstrip("-").isdigit() else 0

    def _bump(self, key: str, delta: int) -> None:
        self._con.execute(
            "insert into meta(k, v) values (?, ?) "
            "on conflict(k) do update set v = cast(v as integer) + ?",
            (key, str(delta), delta))

    def count(self) -> int:
        """O(1). This was COUNT(*) over the whole table, called by the bounds
        check on every single write -- so storing a memory got more expensive
        the more memories you had, which is precisely what stops a store from
        growing. Measured 2026-08-29: 20ms/write at 2k, 68ms at 16k, still
        climbing. Now a counter."""
        with self._lock:
            return self._stat("count")

    def total_bytes(self) -> int:
        """O(1), for the same reason -- this was SUM(size) over every row."""
        with self._lock:
            return self._stat("bytes")

    def recount(self) -> None:
        """Recompute the counters from the rows. Used after a rebuild, and
        available to anyone who suspects they have drifted -- a cached count
        that cannot be re-derived is a number you have to take on faith."""
        with self._lock:
            n, b = self._con.execute(
                "select count(*), coalesce(sum(size),0) from memories"
            ).fetchone()
            self._con.execute("insert or replace into meta values ('count',?)",
                              (str(n),))
            self._con.execute("insert or replace into meta values ('bytes',?)",
                              (str(b),))
            self._con.commit()

    def has(self, name: str) -> bool:
        with self._lock:
            return self._con.execute("select 1 from memories where name=?",
                                     (name,)).fetchone() is not None

    def list(self, limit: int = 0, offset: int = 0,
             source: str = "") -> List[Dict[str, Any]]:
        q = "select name, description, metadata, body from memories"
        args: List[Any] = []
        if source:
            q += " where source=?"
            args.append(source)
        q += " order by name"
        if limit:
            q += " limit ? offset ?"
            args += [limit, offset]
        with self._lock:
            rows = self._con.execute(q, args).fetchall()
        return [{"name": r[0], "description": r[1],
                 "metadata": json.loads(r[2] or "{}"),
                 "body": r[3]} for r in rows]

    def search(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            if self.fts:
                try:
                    rows = self._con.execute(
                        """select m.name, m.description, m.metadata
                           from memories_fts f join memories m
                             on m.id = f.rowid
                           where memories_fts match ?
                           order by rank limit ?""",
                        (_fts_query(query), limit)).fetchall()
                    return [{"name": r[0], "description": r[1],
                             "metadata": json.loads(r[2] or "{}")}
                            for r in rows]
                except sqlite3.Error:
                    pass          # malformed match expression -> fall through
            like = f"%{query}%"
            rows = self._con.execute(
                """select name, description, metadata from memories
                   where name like ? or description like ? or body like ?
                   order by name limit ?""",
                (like, like, like, limit)).fetchall()
        return [{"name": r[0], "description": r[1],
                 "metadata": json.loads(r[2] or "{}")} for r in rows]

    def candidates(self, body: str, limit: int = 25) -> List[Dict[str, Any]]:
        """Reconciliation used to compare a new body against EVERY stored
        one. Only memories sharing vocabulary can overlap enough to matter,
        so full-text supplies the shortlist and the exact overlap maths runs
        over tens of rows instead of a million."""
        words = [w for w in
                 "".join(ch if ch.isalnum() else " " for ch in body).split()
                 if len(w) > 3][:24]
        if not words:
            return []
        with self._lock:
            if self.fts:
                try:
                    rows = self._con.execute(
                        """select m.name, m.description, m.body, m.metadata
                           from memories_fts f join memories m
                             on m.id = f.rowid
                           where memories_fts match ?
                           order by rank limit ?""",
                        (" OR ".join(sorted(set(words))), limit)).fetchall()
                    return [{"name": r[0], "description": r[1], "body": r[2],
                             "metadata": json.loads(r[3] or "{}")}
                            for r in rows]
                except sqlite3.Error:
                    pass
            rows = self._con.execute(
                "select name, description, body, metadata from memories "
                "limit ?", (limit,)).fetchall()
        return [{"name": r[0], "description": r[1], "body": r[2],
                 "metadata": json.loads(r[3] or "{}")} for r in rows]

    def get_body(self, name: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            r = self._con.execute(
                "select name, description, body, metadata from memories "
                "where name=?", (name,)).fetchone()
        if not r:
            return None
        return {"name": r[0], "description": r[1], "body": r[2],
                "metadata": json.loads(r[3] or "{}")}

    # ------------------------------------------------------------ lifecycle
    def rebuild(self, parse, listdir=None) -> int:
        """Throw the index away and rebuild it from the FILES.

        The recovery path, and the reason a corrupt index is an
        inconvenience: the truth is on disk in markdown, and this can always
        be regenerated from it.
        """
        names = listdir or (lambda: [f for f in os.listdir(self.root)
                                     if f.endswith(".md")
                                     and not f.startswith(".")])
        with self._lock:
            self._con.execute("delete from memories")
            if self.fts:
                self._con.execute("delete from memories_fts")
            self._con.commit()
        n = 0
        for fn in names():
            path = os.path.join(self.root, fn)
            try:
                mem = parse(open(path, encoding="utf-8").read())
                self.upsert(mem, os.path.getsize(path))
                n += 1
            except (ValueError, OSError):
                continue        # a file that will not parse is reported by
                                # the store's own list(), not silently fixed
        self.recount()
        return n

    def close(self) -> None:
        with self._lock:
            try:
                self._con.close()
            except sqlite3.Error:
                pass


def _fts_query(text: str) -> str:
    """User text -> a safe FTS5 MATCH expression. Quoting every term stops a
    stray quote or NEAR from becoming a syntax error the caller never wrote."""
    words = [w for w in
             "".join(ch if ch.isalnum() else " " for ch in text).split() if w]
    return " ".join('"%s"' % w for w in words) or '""'
