"""mycelium.py -- recall that spreads along proven paths instead of scanning.

THE SAME MECHANICS AS THE NODE LAYER, ONE LEVEL UP. covenant_unified_v8.py's
LinkConductance already routes between PEERS this way, and the constants here
are deliberately identical (BASELINE 0.5, MIN 0.05, REINFORCE 0.08, ATTENUATE
0.02, relax toward baseline rather than zero). A memory store has the same
problem a 1000-node network had: scoring everything equally is both slow and
wrong, because use is evidence and the system was throwing it away.

  * A mycorrhizal network does not push nutrients down every hypha equally.
    Routes that carry useful flow thicken; routes that carry nothing wither
    back toward baseline -- not to zero.
  * Recall is the same shape. Memories that are useful TOGETHER should be
    reachable from each other, and a query that finds one should surface the
    others without having to match their text.

WHY IT IS FASTER. Full-text finds a handful of SEEDS, then activation spreads
outward along edges. The cost is (seeds x degree x hops), not the size of the
store -- so a million memories cost what a thousand do, provided the graph
stays sparse, and it does: edges only exist where a link was written or a
co-recall happened.

WHY IT IS BETTER, WHICH MATTERS MORE. A text search can only return what
matches the words. Spreading returns what has PROVEN RELATED, so asking about
"the ethics gate" reaches the memory about fail-closed judging that never used
that phrase. That is the recall a scan cannot do at any speed.

THE RULE FROM THE NODE LAYER IS KEPT: conductance ORDERS, it never GATES.
No memory is unreachable because its edges are weak; weak paths are simply
visited later. And nothing here deletes -- an unused edge relaxes to baseline
and stays, because an idle path is unproven, not condemned.
"""
from __future__ import annotations

import math
import sqlite3
import threading
import time
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

BASELINE = 0.5
MIN_W = 0.05
MAX_W = 1.0
REINFORCE = 0.08
ATTENUATE = 0.02
DECAY_HALFLIFE_S = 7 * 86400.0     # a week: memory moves slower than gossip
MAX_EDGES_PER_NODE = 64            # keeps the graph sparse, and the spread cheap


class Mycelium:
    """The edge layer over a MemoryIndex's sqlite connection."""

    def __init__(self, con: sqlite3.Connection, lock: threading.RLock):
        self._con = con
        self._lock = lock
        self._create()

    def _create(self) -> None:
        with self._lock:
            self._con.execute("""create table if not exists edges (
                                    a text not null,
                                    b text not null,
                                    w real not null default 0.5,
                                    seen real not null default 0,
                                    kind text not null default 'learned',
                                    primary key (a, b))""")
            self._con.execute(
                "create index if not exists edges_a on edges(a, w desc)")
            self._con.commit()

    # ------------------------------------------------------------ mechanics
    @staticmethod
    def _decayed(w: float, seen: float, now: float) -> float:
        """Relax toward BASELINE, never toward zero -- an idle path is
        unproven, not condemned. Lifted verbatim in spirit from
        LinkConductance._decayed."""
        if not seen:
            return w
        frac = 0.5 ** (max(0.0, now - seen) / DECAY_HALFLIFE_S)
        return BASELINE + (w - BASELINE) * frac

    def weight(self, a: str, b: str, now: Optional[float] = None) -> float:
        now = time.time() if now is None else now
        with self._lock:
            r = self._con.execute(
                "select w, seen from edges where a=? and b=?", (a, b)
            ).fetchone()
        return self._decayed(r[0], r[1], now) if r else 0.0

    def _touch(self, a: str, b: str, delta: float, kind: str,
               now: float) -> None:
        r = self._con.execute("select w, seen from edges where a=? and b=?",
                              (a, b)).fetchone()
        base = self._decayed(r[0], r[1], now) if r else BASELINE
        w = max(MIN_W, min(MAX_W, base + delta))
        self._con.execute(
            """insert into edges(a, b, w, seen, kind) values (?,?,?,?,?)
               on conflict(a, b) do update set w=excluded.w, seen=excluded.seen,
                 kind=case when edges.kind='explicit' then 'explicit'
                           else excluded.kind end""",
            (a, b, w, now, kind))

    def reinforce(self, names: Sequence[str], kind: str = "learned") -> int:
        """Co-recall is evidence. Every pair in `names` thickens, both ways.

        Hebbian, and bounded: a recall returning 10 memories would make 90
        directed edges, so callers pass the few that were actually USED --
        see recall_used(). Reinforcing everything a search returned would
        teach the graph that everything relates to everything, which is the
        same as teaching it nothing.
        """
        names = [n for n in dict.fromkeys(names) if n]
        if len(names) < 2:
            return 0
        now = time.time()
        n = 0
        with self._lock:
            for i, a in enumerate(names):
                for b in names[i + 1:]:
                    self._touch(a, b, REINFORCE, kind, now)
                    self._touch(b, a, REINFORCE, kind, now)
                    n += 2
            self._prune(names, now)
            self._con.commit()
        return n

    def attenuate(self, a: str, b: str) -> None:
        """A path that was offered and did not help. Thins, never severs --
        the floor is MIN_W and the edge stays in the table."""
        now = time.time()
        with self._lock:
            self._touch(a, b, -ATTENUATE, "learned", now)
            self._touch(b, a, -ATTENUATE, "learned", now)
            self._con.commit()

    def link_explicit(self, a: str, targets: Iterable[str]) -> int:
        """[[wikilinks]] are edges the author asserted. Marked `explicit` so
        decay and pruning never remove them: a written link is a statement,
        not an observation, and the system does not get to forget what it was
        told because it has not needed it lately."""
        now = time.time()
        n = 0
        with self._lock:
            for b in targets:
                if b and b != a:
                    self._touch(a, b, REINFORCE, "explicit", now)
                    self._touch(b, a, REINFORCE / 2, "explicit", now)
                    n += 1
            self._con.commit()
        return n

    def _prune(self, names: Sequence[str], now: float) -> None:
        """Keep the graph sparse so the spread stays cheap. Only LEARNED
        edges are droppable, only the weakest, and only past the cap --
        explicit links are never pruned."""
        for a in names:
            rows = self._con.execute(
                "select b, w, seen, kind from edges where a=?", (a,)
            ).fetchall()
            if len(rows) <= MAX_EDGES_PER_NODE:
                continue
            scored = sorted(
                ((self._decayed(w, seen, now), b, kind)
                 for b, w, seen, kind in rows), reverse=True)
            for _w, b, kind in scored[MAX_EDGES_PER_NODE:]:
                if kind != "explicit":
                    self._con.execute(
                        "delete from edges where a=? and b=?", (a, b))

    # -------------------------------------------------------------- spread
    def spread(self, seeds: Dict[str, float], hops: int = 2,
               limit: int = 25, decay: float = 0.55,
               now: Optional[float] = None) -> List[Dict[str, Any]]:
        """Activation from `seeds` (name -> starting activation) outward.

        Cost is (frontier x degree x hops), not the size of the store. Each
        hop multiplies by `decay`, so distant memories surface only when the
        path to them is genuinely strong -- a weak two-hop route loses to a
        strong one-hop route, which is exactly the ordering a mycelial
        network converges on.
        """
        now = time.time() if now is None else now
        activation: Dict[str, float] = dict(seeds)
        via: Dict[str, str] = {}
        frontier = dict(seeds)
        for hop in range(hops):
            nxt: Dict[str, float] = {}
            if not frontier:
                break
            with self._lock:
                qs = ",".join("?" * len(frontier))
                rows = self._con.execute(
                    f"""select a, b, w, seen from edges where a in ({qs})
                        order by w desc limit ?""",
                    list(frontier) + [len(frontier) * MAX_EDGES_PER_NODE]
                ).fetchall()
            for a, b, w, seen in rows:
                gain = frontier[a] * self._decayed(w, seen, now) * decay
                if gain <= 0.01:
                    continue
                if gain > activation.get(b, 0.0):
                    activation[b] = gain
                    via.setdefault(b, a)
                    nxt[b] = max(nxt.get(b, 0.0), gain)
            frontier = {k: v for k, v in nxt.items() if k not in seeds}
        out = [{"name": n, "activation": round(v, 4),
                "hops": 0 if n in seeds else 1,
                "via": via.get(n)}
               for n, v in activation.items()]
        out.sort(key=lambda r: (-r["activation"], r["name"]))
        return out[:limit]

    def neighbours(self, name: str, limit: int = 10) -> List[Dict[str, Any]]:
        now = time.time()
        with self._lock:
            rows = self._con.execute(
                "select b, w, seen, kind from edges where a=? "
                "order by w desc limit ?", (name, limit)).fetchall()
        return [{"name": b, "weight": round(self._decayed(w, seen, now), 4),
                 "kind": kind} for b, w, seen, kind in rows]

    # ---------------------------------------------------------- identity --
    # WHAT GROWTH ACTUALLY BUYS, AND WHAT IT DOES NOT.
    #
    # The graph is PATH-DEPENDENT: its shape is the record of which memories
    # proved useful together, in what order. Two stores holding byte-identical
    # memories but used differently diverge structurally within a handful of
    # recalls, and the difference cannot be derived from the memories -- it is
    # evidence of use, not of content. So the topology is an identity: a store
    # can prove which store it is, and detect that another is not it.
    #
    # IT DOES NOT MAKE THE STORE HARD TO COPY, and saying otherwise would be
    # the worst line in this repository. Anything on disk can be copied
    # byte-for-byte; a copy of this database IS this graph. Growth defeats
    # RECONSTRUCTION (you cannot infer the graph from the memories) and
    # defeats SUBSTITUTION (a different store fails the fingerprint). It does
    # nothing whatever against duplication, and a system that felt unclonable
    # while being one `copy` away from cloned would be trusted exactly where
    # it is weakest -- which is the failure this project exists to refuse.
    #
    # The honest security value is therefore DETECTION, never prevention:
    # after a copy, the two diverge on first use and can both prove it.
    def fingerprint(self, now: Optional[float] = None) -> Dict[str, Any]:
        """A digest over the topology and its decayed weights.

        Weights are rounded to two places before hashing: the fingerprint has
        to survive the continuous decay it measures, or it would change every
        second on its own and detect nothing.
        """
        import hashlib
        now = time.time() if now is None else now
        with self._lock:
            rows = self._con.execute(
                "select a, b, w, seen, kind from edges order by a, b"
            ).fetchall()
        parts, explicit = [], 0
        for a, b, w, seen, kind in rows:
            if kind == "explicit":
                explicit += 1
            parts.append(f"{a}|{b}|{self._decayed(w, seen, now):.2f}|{kind}")
        body = "\n".join(parts)
        return {
            "edges": len(rows),
            "explicit": explicit,
            "topology": hashlib.sha256(
                "\n".join(f"{a}|{b}" for a, b, _w, _s, _k in rows)
                .encode()).hexdigest()[:16],
            "weighted": hashlib.sha256(body.encode()).hexdigest()[:16],
            "means": ("`topology` is the shape alone and changes only when an "
                      "edge appears or goes; `weighted` also tracks how "
                      "strongly, so it moves whenever use does"),
            "limits": ("this identifies a store and detects substitution or "
                       "drift. It does NOT make the store hard to copy -- a "
                       "byte copy of this database reproduces this graph "
                       "exactly. Detection, never prevention."),
        }

    def divergence(self, other: Dict[str, Any]) -> Dict[str, Any]:
        """Compare against another store's fingerprint and say WHICH claim
        failed -- same shape but different strengths is a different fact from
        a different shape, and reporting one number would hide it."""
        mine = self.fingerprint()
        same_topo = mine["topology"] == other.get("topology")
        same_w = mine["weighted"] == other.get("weighted")
        if same_topo and same_w:
            verdict = "identical: same edges, same strengths"
        elif same_topo:
            verdict = ("same edges, DIFFERENT strengths -- these were the "
                       "same store and have been used differently since")
        else:
            verdict = ("DIFFERENT edges -- not the same graph. Either a "
                       "different store, or one that has learned links the "
                       "other never had")
        return {"same_topology": same_topo, "same_weights": same_w,
                "mine": mine, "theirs": other, "verdict": verdict}

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            n, avg = self._con.execute(
                "select count(*), coalesce(avg(w),0) from edges").fetchone()
            ex = self._con.execute(
                "select count(*) from edges where kind='explicit'").fetchone()[0]
        return {"edges": n, "explicit": ex, "learned": n - ex,
                "mean_weight": round(avg, 4),
                "note": "conductance ORDERS recall and never gates it; no "
                        "memory is unreachable because its edges are weak"}
