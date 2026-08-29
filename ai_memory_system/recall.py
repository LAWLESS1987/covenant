"""recall.py -- tiering, scoring and supersession: what turns a pile of files
into a memory.

MODELLED ON THE FIELD, AND WHERE IT DEPARTS FROM IT.

  Letta / MemGPT -- tiered memory. CORE memory is always in the agent's
      context; ARCHIVAL memory is recalled on demand. Taken directly:
      `tier` is a first-class field and `context_window()` fills a stated
      character budget, core first. Departure: the budget is stated and the
      overflow is NAMED, so an agent knows what it did not get. A context
      that silently truncates is a context that lies by omission.

  Mem0 -- an extraction pipeline that decides ADD / UPDATE / DELETE / NOOP
      against what is already stored. The decision loop is right and is
      kept (`reconcile`). Departure, and it is the important one: Mem0's
      UPDATE OVERWRITES THE OLD FACT. This one never destroys the thing it
      disagrees with. A new memory SUPERSEDES an old one: both survive, the
      old is marked superseded_by, the new carries supersedes, and the
      audit chain records the move. You can always answer "what did we
      believe before, and when did that change" -- which is the question
      you most need after a memory turns out to be wrong.

  Supermemory -- one API over many sources. Kept in spirit: the HTTP
      surface is deliberately tiny and source-agnostic. Departure: no
      hosted dependency. This runs on a laptop with stdlib python.

  memSearch / vector recall -- embedding search. Deliberately NOT copied
      yet. An embedding score is a number nobody can audit, and this store
      is small enough that explainable lexical scoring beats an opaque
      ranker. `score_explain` returns every component that produced a
      score, so a recall can be argued with. Vectors can be added later
      behind the same interface; they may not replace the explanation.

  Engram -- consolidation: memories that are used strengthen, memories that
      are not decay. Taken, with the sharp edge removed: strength here
      NEVER deletes anything and never hides it. It only ORDERS recall.
      A system that forgets what it stopped using would have deleted
      exactly the safety lesson nobody had needed for a year.

THE RULE UNDERNEATH ALL OF IT: nothing here silently discards. Supersede,
demote, re-order, disclose -- never erase, never overwrite, never quietly
truncate. That is the same rule the covenant's ethics gate runs on, and it
is why this is in that repository.
"""
from __future__ import annotations

import math
import re
import time
from typing import Any, Dict, List, Optional, Tuple

CORE, ARCHIVAL = "core", "archival"
HALF_LIFE_DAYS = 30.0          # Engram-style decay, gentle and stated
DEFAULT_BUDGET = 8000          # characters, ~2k tokens of core context
CONTESTED_MIN = 0.35           # see reconcile(): asymmetric on purpose

_WORD = re.compile(r"[a-z0-9]+")


_STOP = {"the", "a", "an", "and", "or", "is", "are", "was", "were", "to",
         "of", "in", "on", "for", "that", "this", "it", "be", "as", "at"}


def _tokens(text: str) -> List[str]:
    return _WORD.findall((text or "").lower())


def _content(text: str) -> set:
    """Content words, crudely singularised. Not linguistics -- just enough
    that `prefers` and `prefer` are the same word, so a restatement is not
    read as a new topic. Stopwords go: they inflate every overlap equally
    and therefore measure nothing."""
    out = set()
    for t in _tokens(text):
        if t in _STOP or len(t) < 2:
            continue
        out.add(t[:-1] if len(t) > 3 and t.endswith("s") else t)
    return out


def overlap(a: str, b: str) -> Tuple[float, float]:
    """(containment, jaccard) between two bodies.

    CONTAINMENT is the one that matters for reconciliation and Jaccard is
    not: a new memory that keeps everything the old one said AND adds a
    clause has containment 1.0 and Jaccard well under a half. Measured on
    this suite's own corpus 2026-08-29 -- Jaccard scored a true supersession
    at 0.385 and called it unrelated, which would have left two versions of
    the same fact side by side with nothing pointing between them.
    """
    ta, tb = _content(a), _content(b)
    if not ta or not tb:
        return 0.0, 0.0
    inter = len(ta & tb)
    return inter / float(min(len(ta), len(tb))), inter / float(len(ta | tb))


def strength(uses: int, last_used_epoch: float, now: Optional[float] = None
             ) -> float:
    """Engram-style consolidation, made explainable.

    Repetition strengthens (log, so the tenth use matters less than the
    second); time weakens on a stated half-life. The floor is deliberately
    ABOVE zero: a memory can become cold, never worthless. Nothing in this
    module deletes on a low score -- see the module docstring.
    """
    now = time.time() if now is None else now
    days = max(0.0, (now - (last_used_epoch or now)) / 86400.0)
    recency = 0.5 ** (days / HALF_LIFE_DAYS)
    return round(0.15 + math.log1p(max(0, uses)) * (0.4 + 0.6 * recency), 4)


def score_explain(memory: Dict[str, Any], query: str,
                  now: Optional[float] = None) -> Dict[str, Any]:
    """Every component of a recall score, returned. No opaque ranker.

    An agent that cannot say WHY it recalled something cannot be argued
    with, and a memory system you cannot argue with is one you must simply
    trust -- which is the property this whole repository refuses to ship.
    """
    meta = memory.get("metadata") or {}
    q = set(_tokens(query))
    name_hits = len(q & set(_tokens(memory.get("name", ""))))
    desc_hits = len(q & set(_tokens(memory.get("description", ""))))
    body_hits = len(q & set(_tokens(memory.get("body", ""))))
    exact = 1 if query.strip().lower() in (memory.get("body", "")
                                           + memory.get("description", "")
                                           ).lower() else 0
    st = strength(int(meta.get("uses", 0) or 0),
                  float(meta.get("last_used", 0) or 0), now)
    tier_bonus = 1.0 if meta.get("tier") == CORE else 0.0
    # Weights are here, in the open, in one expression. Change them and the
    # explanation changes with them -- that is the point.
    total = (3.0 * name_hits + 2.0 * desc_hits + 1.0 * body_hits
             + 2.0 * exact + 1.5 * st + tier_bonus)
    return {"name": memory.get("name"), "score": round(total, 4),
            "because": {"name_hits": name_hits, "description_hits": desc_hits,
                        "body_hits": body_hits, "exact_phrase": exact,
                        "strength": st, "tier_bonus": tier_bonus,
                        "uses": int(meta.get("uses", 0) or 0)}}


def rank(memories: List[Dict[str, Any]], query: str, limit: int = 10,
         now: Optional[float] = None) -> List[Dict[str, Any]]:
    """Score every memory, drop the zeroes, best first. Ties break by name
    so the same query twice gives the same order -- a recall that reorders
    under you is a recall you cannot reproduce in a bug report."""
    scored = [score_explain(m, query, now) for m in memories]
    scored = [s for s in scored if s["score"] > 0]
    scored.sort(key=lambda s: (-s["score"], s["name"] or ""))
    return scored[:limit]


def context_window(memories: List[Dict[str, Any]], budget: int = DEFAULT_BUDGET
                   ) -> Dict[str, Any]:
    """Letta's core/archival split, with the omission made explicit.

    Fills `budget` characters with CORE memories first, strongest first.
    Whatever does not fit is NAMED in `omitted` rather than dropped in
    silence: an agent that knows it is missing three core memories can go
    and fetch them; an agent handed a truncated context cannot tell.
    """
    core, arch = [], []
    for m in memories:
        ((core if (m.get("metadata") or {}).get("tier") == CORE else arch)
         .append(m))
    core.sort(key=lambda m: -strength(
        int((m.get("metadata") or {}).get("uses", 0) or 0),
        float((m.get("metadata") or {}).get("last_used", 0) or 0)))
    included, omitted, used = [], [], 0
    for m in core:
        block = f"## {m.get('name')}\n{m.get('body', '')}\n"
        if used + len(block) > budget:
            omitted.append(m.get("name"))
            continue
        included.append(block)
        used += len(block)
    return {"context": "\n".join(included), "chars": used, "budget": budget,
            "included": len(included), "omitted": omitted,
            "archival_available": len(arch),
            "note": ("core memories that did not fit are NAMED in `omitted` "
                     "-- fetch them individually rather than assuming this "
                     "context is complete") if omitted else
                    "every core memory fit inside the budget"}


def reconcile(new_body: str, existing: List[Dict[str, Any]],
              threshold: float = 0.5) -> Dict[str, Any]:
    """Mem0's ADD / UPDATE / NOOP decision -- with SUPERSEDE in place of a
    destructive update, and CONTESTED in place of a silent winner.

    Returns {"action", "target", "overlap", "why"}:
      ADD        nothing similar is stored
      NOOP       an existing memory already says this (near-identical)
      SUPERSEDE  an existing memory covers this ground and the new text
                 differs -- the caller should write the new one and mark
                 the old superseded_by, keeping BOTH
      CONTESTED  strong overlap AND an explicit contradiction marker: two
                 agents disagree. Nothing is overwritten and nothing is
                 auto-resolved; a disagreement between agents is exactly
                 the thing a human should see.

    Overlap is Jaccard over content words -- crude, explainable, and no
    model call. This is a decision about what to STORE; using a language
    model to make it would make the store's contents depend on a model
    nobody can pin, which is how a memory quietly becomes an opinion.
    """
    if not _content(new_body):
        return {"action": "NOOP", "target": None, "overlap": 0.0,
                "why": "empty body"}
    best, best_ov, best_jac = None, 0.0, 0.0
    for m in existing:
        con, jac = overlap(new_body, m.get("body", ""))
        if con > best_ov:
            best, best_ov, best_jac = m, con, jac

    negations = ("not ", "no longer", "never", "wrong", "incorrect",
                 "actually", "instead", "correction", "does not", "isn't")
    contradicts = any(w in new_body.lower() for w in negations)

    # A CONTRADICTION IS SURFACED ON LESS EVIDENCE THAN A SUPERSESSION.
    # Deliberately asymmetric: missing a supersession leaves two versions of
    # a fact side by side (untidy, recoverable). Missing a contradiction
    # leaves two agents believing opposite things with nothing saying so
    # (silent, and the kind of thing you find out from the consequence).
    # So contradiction fires at CONTESTED_MIN and supersession at threshold.
    if best is not None and contradicts and best_ov >= CONTESTED_MIN:
        return {"action": "CONTESTED", "target": best["name"],
                "overlap": round(best_ov, 3), "jaccard": round(best_jac, 3),
                "why": ("this contradicts a stored memory; BOTH are kept and "
                        "the disagreement is surfaced rather than resolved -- "
                        "two agents disagreeing is a fact a human should see, "
                        "not a merge conflict to auto-resolve")}
    if best is None or best_ov < threshold:
        return {"action": "ADD", "target": None, "overlap": round(best_ov, 3),
                "why": f"nothing stored overlaps above {threshold}"}
    if best_ov >= 0.98 and best_jac >= 0.9:
        return {"action": "NOOP", "target": best["name"],
                "overlap": round(best_ov, 3), "jaccard": round(best_jac, 3),
                "why": "an existing memory already says this"}
    return {"action": "SUPERSEDE", "target": best["name"],
            "overlap": round(best_ov, 3), "jaccard": round(best_jac, 3),
            "why": ("this covers the same ground and differs; write the new "
                    "memory and mark the old superseded_by -- both survive, "
                    "so 'what did we believe before, and when did it change' "
                    "stays answerable")}
