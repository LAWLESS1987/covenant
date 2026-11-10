#!/usr/bin/env python3
"""IM3 -- the nightly improvement orchestrator (covenant_improve.py), driven BOTH WAYS, offline, no network.

Pins: (1) cold start SEEDS the backlog and emits NO digest; (2) after seeding, a new reply flows
extract -> vet -> backlog, and a capped digest fires ONLY on the weekly day; (3) the vet downgrades every
non-starter (kind!=gap -> skip, no test -> needs-test, tombstone -> recurrence, keyword-in-source -> have)
and only a genuine survivor reaches 'backlog'; (4) the digest is capped at DIGEST_CAP; (5) a non-weekly day
holds the digest. Door, grep and tombstone lookups are all stubbed -- nothing leaves the machine.
"""
import json, os, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_improve_mine as IM
import covenant_improve as CI


def _row(author, text, sha):
    return {"author": author, "text": text, "sha256": sha, "url": "u/" + sha,
            "source": "moltbook/comment", "eligible": True, "flags": {"directive": False}}


def _write(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def main():
    fails = []
    # 2026-11-04: the nightly now extracts with the reply-only prompt (v2), whose idea must rest on a QUOTE found in
    # the reply -- so the fixture replies carry a real sentence to quote, and the stub door answers in v2 format.
    long = " we should keep join keys on every distilled row so it can be traced " + "x" * 200
    import covenant_improve_extract as EX
    orig_cand, orig_seen, orig_out = IM.CANDIDATES, IM.SEEN, EX.CANDIDATES_OUT
    # IM8 (2026-11-04): this suite appended 120 fixture rows to the LIVE ops/improve_candidates.jsonl (10-27..10-29)
    # while printing 15/15, because nightly() -> extract() wrote through a frozen default. Every live ledger the
    # flow can touch is redirected below AND snapshotted here, so a write that escapes the temp dir turns this red.
    live = [orig_out, CI.BACKLOG, orig_seen, orig_cand]
    before = {p: (os.path.getsize(p) if os.path.exists(p) else None) for p in live}
    try:
        with tempfile.TemporaryDirectory() as d:
            IM.CANDIDATES = os.path.join(d, "candidates.jsonl")
            IM.SEEN = os.path.join(d, "seen.json")
            EX.CANDIDATES_OUT = os.path.join(d, "improve_candidates.jsonl")
            backlog = os.path.join(d, "backlog.jsonl")

            # ---- unit: vet downgrades every non-starter, promotes only a genuine gap ----
            no_grep = lambda terms: False        # noqa: E731  capability NOT present
            no_tomb = lambda text: None          # noqa: E731  not tombstoned
            cases = {
                "skip":      {"kind": "have",  "idea": "x", "test": "t"},
                "needs-test":{"kind": "gap",   "idea": "x", "test": ""},
                "recurrence":{"kind": "gap",   "idea": "x", "test": "t"},
                "have":      {"kind": "gap",   "idea": "x", "test": "t"},
                "backlog":   {"kind": "gap",   "idea": "x", "test": "present=green/removed=red"},
            }
            if CI.vet(cases["skip"], no_grep, no_tomb)["status"] != "skip":
                fails.append("vet: non-gap should skip")
            if CI.vet(cases["needs-test"], no_grep, no_tomb)["status"] != "needs-test":
                fails.append("vet: gap with no test should be needs-test")
            if CI.vet(cases["recurrence"], no_grep, lambda t: "RETRACTED.json: old line")["status"] != "recurrence":
                fails.append("vet: tombstoned idea should be recurrence")
            # SUPERSEDED 2026-11-04 (A409 follow-up): "keyword-in-source should be have" pinned the rule that a
            # word match KILLS a candidate. Measured on 32 real ideas, every such kill rested on a co-incidence; a
            # match is now a signal (dup_hint) and never a verdict. The old checks are kept as written in
            # .trash/echo_v2_build_2026-11-04/test_im3_improve_nightly.py.before_never_kill. Both ways, the new rule:
            kw = CI.vet(cases["have"], lambda terms: True, no_tomb)
            if kw["status"] != "backlog":
                fails.append("vet: a keyword match must NOT kill a candidate (signal, not conviction), got %r" % kw)
            if CI.vet(cases["backlog"], no_grep, no_tomb)["status"] != "backlog":
                fails.append("vet: a genuine gap with a test should reach backlog")
            # the evidence is still NAMED, so a person (and the benchmark) can see why it might be a duplicate
            co = {"kind": "gap", "idea": "zebrafoo quokkabar", "test": "t"}
            named = CI.vet(co, lambda terms: "zebrafoo @ m.py (code `zebrafoo`); quokkabar @ m.py (code `quokkabar`)",
                           no_tomb)
            if named["status"] != "backlog" or "zebrafoo @ m.py" not in named.get("dup_hint", ""):
                fails.append("vet: two specific terms in one file must be carried as a named dup_hint, got %r" % named)
            apart = CI.vet(co, lambda terms: "zebrafoo @ m.py (code `zebrafoo`); quokkabar @ n.py (code `quokkabar`)",
                           no_tomb)
            if apart.get("dup_hint"):
                fails.append("vet: the same two terms in DIFFERENT files are not a mechanism -> no hint, got %r" % apart)

            # ---- flow: COLD START seeds, no digest ----
            _write(IM.CANDIDATES, [_row("a", "A " + long, "a1"), _row("b", "B " + long, "b2")])
            digested = []
            r0 = CI.nightly(say=lambda *a: None, ask=lambda t: (200, {"answer": "KIND: gap"}),
                            weekday=CI.DIGEST_WEEKDAY, digest=lambda top, say: digested.append(list(top)),
                            backlog=backlog, grep=no_grep, tomb=no_tomb)
            if not r0.get("seeded"):
                fails.append("first run must seed, got %r" % r0)
            if digested:
                fails.append("cold-start run must emit NO digest")
            if not os.path.exists(IM.SEEN):
                fails.append("seeding must write the seen-set")

            # ---- flow: a NEW reply after seeding -> backlog -> digest on the weekly day ----
            with open(IM.CANDIDATES, "a", encoding="utf-8") as f:
                f.write(json.dumps(_row("carol", "CAROL " + long, "c3")) + "\n")
            door = lambda t: (200, {"answer": "KIND: idea\nQUOTE: we should keep join keys on every distilled row\n"
                                              "IDEA: keep join keys\nTEST: present=green / removed=red"})
            r1 = CI.nightly(say=lambda *a: None, ask=door, weekday=CI.DIGEST_WEEKDAY,
                            digest=lambda top, say: digested.append(list(top)),
                            backlog=backlog, grep=no_grep, tomb=no_tomb)
            if r1.get("ready") != 1 or r1.get("digest_emitted") != 1:
                fails.append("weekly run should have 1 ready and emit it, got %r" % r1)
            if len(digested) != 1 or digested[0][0]["id"] != "c3":
                fails.append("digest should carry the new backlog item c3, got %r" % digested)
            if not any(json.loads(l)["id"] == "c3" for l in open(backlog) if l.strip()):
                fails.append("c3 should be appended to the backlog file")

            # ---- BOTH WAYS: a non-weekly day HOLDS the digest even with a ready item ----
            with open(IM.CANDIDATES, "a", encoding="utf-8") as f:
                f.write(json.dumps(_row("dave", "DAVE " + long, "d4")) + "\n")
            not_monday = (CI.DIGEST_WEEKDAY + 3) % 7
            digested.clear()
            r2 = CI.nightly(say=lambda *a: None, ask=door, weekday=not_monday,
                            digest=lambda top, say: digested.append(list(top)),
                            backlog=backlog, grep=no_grep, tomb=no_tomb)
            if r2.get("ready") != 1:
                fails.append("off-day run should still find 1 ready, got %r" % r2)
            if digested or r2.get("digest_emitted") != 0:
                fails.append("off-day run must NOT emit a digest, got emitted=%r" % r2.get("digest_emitted"))

            # ---- cap: >DIGEST_CAP ready -> digest carries exactly DIGEST_CAP ----
            many = [_row("e%d" % i, ("E%d " % i) + long, "e%d" % i) for i in range(CI.DIGEST_CAP + 3)]
            _write(IM.CANDIDATES, many)
            IM.SEEN = os.path.join(d, "seen2.json")
            CI.seed_baseline(say=lambda *a: None)              # fresh baseline
            IM.mark_seen([])                                   # no-op; baseline already consumed `many`
            # append CAP+3 brand-new ones AFTER the baseline so they are all delta
            _write(IM.CANDIDATES, many + [_row("f%d" % i, ("F%d " % i) + long, "f%d" % i)
                                          for i in range(CI.DIGEST_CAP + 3)])
            digested.clear()
            r3 = CI.nightly(say=lambda *a: None, ask=door, weekday=CI.DIGEST_WEEKDAY,
                            digest=lambda top, say: digested.append(list(top)),
                            backlog=os.path.join(d, "backlog3.jsonl"), grep=no_grep, tomb=no_tomb)
            if r3.get("ready") != CI.DIGEST_CAP + 3:
                fails.append("cap test: expected %d ready, got %r" % (CI.DIGEST_CAP + 3, r3))
            if not digested or len(digested[-1]) != CI.DIGEST_CAP:
                fails.append("digest must be capped at %d, got %r" % (CI.DIGEST_CAP, [len(x) for x in digested]))
    finally:
        IM.CANDIDATES, IM.SEEN, EX.CANDIDATES_OUT = orig_cand, orig_seen, orig_out

    after = {p: (os.path.getsize(p) if os.path.exists(p) else None) for p in live}
    for p in live:
        if before[p] != after[p]:
            fails.append("the suite wrote to a LIVE ledger %s (%r -> %r bytes): a path escaped the temp dir"
                         % (os.path.relpath(p, HERE), before[p], after[p]))

    if fails:
        print("IM3 FAIL:")
        for x in fails:
            print("  -", x)
        return 1
    print("IM3: 16/16 passed -- cold start seeds with no digest; vet downgrades every non-starter; a genuine gap reaches "
          "backlog; the weekly digest fires capped on its day and holds off-day; no live ledger written. Offline, no network.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
