#!/usr/bin/env python3
"""IM9 -- reply-only extraction (v2), the quote gate, the grounding retry, the re-queue and the miner_echo outcome.
Offline: the door is stubbed, every ledger is redirected to a temp dir and the live ones are snapshotted.

Why (A409 follow-up, 2026-11-04). The v1 prompt opened with one sentence describing us; 63 of 139 extractions handed
it back as the "idea" and the reply's real idea was never mined. Nine outside seats agreed (ops/ECHO_CONSULT_2026-11-
04.md): take the self-description out of the extracting step, make the idea rest on a QUOTE that code checks is in
the reply, re-ask once with a DIFFERENT instruction, re-queue what an echo swallowed, and record an echo as the
miner's failure (miner_echo), not the matcher's (false_match).

Both ways, each property: the thing present -> green; the thing removed/violated -> the check goes red (driven by
mutation in the 2026-11-04 build; see docs/KNOWN_ISSUES.md A409).

Blind spots (rule 9): a quote that IS in the reply while the one-line IDEA drifts from it passes the gate (the
support_frac field measures that drift; it is recorded, not gated). The quote check is lexical: a reply that itself
quotes our self-description grounds an echo of it.
"""
import hashlib, json, os, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_improve_mine as IM
import covenant_improve_extract as EX
import covenant_improve as CI

LONG = " and the rest of the reply goes on about other things" * 6


def _row(author, text, sha):
    return {"author": author, "text": text, "sha256": sha, "url": "u/" + sha,
            "source": "moltbook/comment", "eligible": True, "flags": {"directive": False}}


def _write(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def _snap(paths):
    return {p: hashlib.sha256(open(p, "rb").read()).hexdigest() for p in paths if os.path.exists(p)}


def main():
    fails, checks = [], 0

    def ok(cond, msg):
        nonlocal checks
        checks += 1
        if not cond:
            fails.append(msg)

    # 1. The extracting prompt carries none of the self-description's distinctive words; the self-description does
    #    (so the check can go red).
    distinct = ("ledger", "ethics", "retraction", "undetermined", "transaction")
    ok(all(w in EX.SELF_DESC.lower() for w in distinct), "SELF_DESC must hold the words this check looks for")
    ok(not any(w in EX.PROMPT_V2.lower() for w in distinct),
       "PROMPT_V2 must not carry the self-description into the extracting step")

    # 2. The quote gate.
    reply = "EVE: Put the ethics gate in the  “transaction path” of the ledger, before the write." + LONG
    ok(EX.grounded_quote("put the ethics gate in the \"transaction path\"", reply), "a verbatim quote must ground")
    ok(not EX.grounded_quote("place the ethics gate inside the transaction path", reply), "a paraphrase must not ground")
    ok(not EX.grounded_quote("a ledger with an ethics gate", reply), "our own phrase absent from the reply must not")
    ok(not EX.grounded_quote("the ledger", reply), "a quote under QUOTE_MIN_WORDS must not ground")
    tail = "x" * EX.SEEN_CHARS + " this sentence sits past what the model saw"
    ok(not EX.grounded_quote("this sentence sits past what the model saw", tail[:EX.SEEN_CHARS]),
       "a quote from past the shown text must not ground")

    # 3. One reply through v2: grounded first time / grounded on the retry / never grounded / none / door down.
    good = "KIND: idea\nQUOTE: Put the ethics gate in the transaction path of the ledger\nIDEA: gate before the write\nTEST: ?"
    bad = "KIND: idea\nQUOTE: a ledger with an ethics gate in the transaction path\nIDEA: ethics ledger\nTEST: ?"
    seen = []

    def seq(*answers):
        it = iter(answers)

        def ask(t):
            seen.append(t)
            a = next(it)
            return (a, {}) if isinstance(a, int) else (200, {"answer": a})
        return ask

    seen.clear()
    code, f = EX.extract_one_v2("eve", reply, seq(good))
    ok(code == 200 and f["kind"] == "gap" and f["grounded"] and not f["retried"] and len(seen) == 1,
       "a grounded first answer is a gap, no retry: %r" % (f,))
    seen.clear()
    code, f = EX.extract_one_v2("eve", reply, seq(bad, good))
    ok(f["kind"] == "gap" and f["retried"] and len(seen) == 2, "an ungrounded first answer is retried once: %r" % (f,))
    ok(len(seen) == 2 and EX.RETRY_NOTE in seen[1] and EX.RETRY_NOTE not in seen[0],
       "the retry must carry a DIFFERENT instruction, not the same prompt")
    seen.clear()
    code, f = EX.extract_one_v2("eve", reply, seq(bad, bad))
    ok(f["kind"] == "ungrounded" and len(seen) == 2, "never grounded -> 'ungrounded' after ONE retry: %r" % (f,))
    ok(CI.vet({**f})["status"] == "skip", "the vet must skip an ungrounded row")
    seen.clear()
    code, f = EX.extract_one_v2("eve", reply, seq("KIND: none\nQUOTE: ?\nIDEA: ?\nTEST: ?"))
    ok(f["kind"] == "none" and len(seen) == 1, "'none' is not retried: %r" % (f,))
    code, f = EX.extract_one_v2("eve", reply, seq(503))
    ok(code == 503 and f is None, "a door failure returns its code and no row")

    # 4-6. End to end through extract(), re-queue, backfill -- all ledgers redirected.
    live = [EX.CANDIDATES_OUT, IM.SEEN, IM.CANDIDATES, IM.REQUEUE, CI.BACKLOG, CI.DISPOSITIONS]
    before = _snap(live)
    saved = (IM.CANDIDATES, IM.SEEN, IM.REQUEUE, EX.CANDIDATES_OUT, EX.PROMPT_VERSION)
    try:
        with tempfile.TemporaryDirectory() as d:
            IM.CANDIDATES = os.path.join(d, "cand.jsonl")
            IM.SEEN = os.path.join(d, "seen.json")
            IM.REQUEUE = os.path.join(d, "requeue.jsonl")
            EX.CANDIDATES_OUT = os.path.join(d, "out.jsonl")
            EX.PROMPT_VERSION = "v2"
            _write(IM.CANDIDATES, [_row("eve", reply, "e1"), _row("old", "OLD talks about retries" + LONG, "o2"),
                                   _row("new", "NEW: Put the ethics gate in the transaction path of the ledger" + LONG,
                                        "n3")])
            IM.mark_seen(["o2"])                               # o2 was mined by v1 already
            _write(EX.CANDIDATES_OUT, [{"id": "o2", "kind": "gap", "idea": "a ledger with an ethics gate in the "
                                        "transaction path", "prompt": "v1"}])
            texts = {IM._row_id(r): r.get("text") for r in IM._rows(IM.CANDIDATES)}

            # 5. control: without the re-queue, a seen reply is never offered again
            ok("o2" not in [x["id"] for x in IM.harvest(update=False, requeue_first=True)],
               "a seen reply must not come back without a re-queue")
            n = EX.requeue_v1_echoes(texts.get, say=lambda *a: None)
            ok(n == 1 and IM.pending_requeue() == ["o2"], "the v1 echo must be re-queued once, got %r %r"
               % (n, IM.pending_requeue()))
            ok(EX.requeue_v1_echoes(texts.get, say=lambda *a: None) == 0, "re-queueing is idempotent")
            h = IM.harvest(update=False, requeue_first=True)
            ok([x["id"] for x in h][:1] == ["o2"], "a re-queued reply is offered FIRST, got %r" % [x["id"] for x in h])

            ans = lambda t: (200, {"answer": "KIND: idea\nQUOTE: Put the ethics gate in the transaction path of the "  # noqa: E731
                                             "ledger\nIDEA: gate first\nTEST: present=green / removed=red"}
                             if "ethics gate" in t else {"answer": "KIND: none\nQUOTE: ?\nIDEA: ?\nTEST: ?"})
            rows = EX.extract(limit=20, ask=ans, say=lambda *a: None)
            by = {r["id"]: r for r in rows}
            ok(all(r.get("prompt") == "v2" for r in rows), "v2 rows must say so")
            ok(by.get("o2", {}).get("requeued") is True and by["o2"]["kind"] == "none",
               "the re-queued reply is re-extracted from the reply, not the echo: %r" % by.get("o2"))
            ok(IM.pending_requeue() == [], "a re-extracted reply leaves the queue (append-only 'done')")
            ok(by.get("n3", {}).get("kind") == "gap" and by["n3"]["grounded"], "a grounded new reply is a gap")
            ok(not [x for x in IM.harvest(update=False, requeue_first=True)], "nothing is offered twice")

            # door failure under v2: the reply stays UN-seen and is offered again (IM2's property, for the live path)
            with open(IM.CANDIDATES, "a", encoding="utf-8") as f:
                f.write(json.dumps(_row("dan", "DAN: Put the ethics gate in the transaction path of the ledger" + LONG,
                                        "d4")) + "\n")
            down = EX.extract(limit=20, ask=lambda t: (503, {}), say=lambda *a: None)
            ok(down == [] and "d4" in [x["id"] for x in IM.harvest(update=False)],
               "a door failure under v2 must record nothing and leave the reply un-seen")
    finally:
        IM.CANDIDATES, IM.SEEN, IM.REQUEUE, EX.CANDIDATES_OUT, EX.PROMPT_VERSION = saved
    ok(_snap(live) == before, "the suite wrote to a LIVE ledger")

    # 7. miner_echo clears only with evidence; proposals skip a grounded row.
    today = "2026-11-04"
    full = {"outcome": "miner_echo", "echo_frac": 1.0, "phrase": "a ledger with an ethics gate", "rationale": "echo"}
    ok(CI.disposition_clears(full, today), "a well-formed miner_echo must clear")
    for k, v in (("phrase", ""), ("rationale", " "), ("echo_frac", 0.3), ("echo_frac", "high")):
        ok(not CI.disposition_clears({**full, k: v}, today), "miner_echo with %s=%r must NOT clear" % (k, v))
    esc = [{"id": "x1", "idea": "a ledger with an ethics gate in the transaction path", "term": "ledger"},
           {"id": "x2", "idea": "a raw-source manifest with exact wording and source", "term": "manifest"}]
    rep = {"x1": "a reply about retries", "x2": "keep a raw-source manifest with the exact wording and the source"}
    props = CI.propose_echo_dispositions(esc, rep.get)
    ok([p["candidate_id"] for p in props] == ["x1"], "only the echo is proposed, got %r" % props)
    ok(all(CI.disposition_clears(p, today) for p in props), "a proposal must be a disposition that clears")
    bl = [{"id": "x1", "vet": "have", "idea": esc[0]["idea"], "t": "2026-11-01T00:00:00Z",
           "why": "a capability keyword already appears in source (dedup): ledger @ breakout_ledger.py"}] + [
          {"id": "z%d" % i, "vet": "skip", "t": "2026-11-0%dT00:00:00Z" % i} for i in (2, 3, 4, 5)]
    ok(len(CI.circle_back(rows=bl, dispositions={}, today=today)["escalate"]) == 1, "control: the echo escalates")
    ok(CI.circle_back(rows=bl, dispositions={"x1": props[0]}, today=today)["escalate"] == [],
       "a miner_echo disposition clears the escalation")

    # 8. A word match never kills; the hint needs two specific terms in ONE file; the digest shows unhinted first.
    g_co = lambda t: "zebrafoo @ m.py (code `zebrafoo`); quokkabar @ m.py (code `quokkabar`)"  # noqa: E731
    g_apart = lambda t: "zebrafoo @ m.py (code `zebrafoo`); quokkabar @ n.py (code `quokkabar`)"  # noqa: E731
    cand = {"kind": "gap", "maps": "", "idea": "zebrafoo quokkabar", "test": "present=green / removed=red"}
    v = CI.vet(cand, grep=g_co, tomb=lambda t: None)
    ok(v["status"] == "backlog" and "zebrafoo @ m.py" in v["dup_hint"], "co-located terms: hint, never a kill: %r" % v)
    ok(not CI.vet(cand, grep=g_apart, tomb=lambda t: None)["dup_hint"], "terms in different files: no hint")
    ok(CI.vet(cand, grep=lambda t: True, tomb=lambda t: None)["status"] == "backlog", "a bare match never kills")
    ranked = CI.rank_ready([{"id": "h1", "dup_hint": "x @ y"}, {"id": "n1", "dup_hint": ""}, {"id": "n2"}])
    ok([r["id"] for r in ranked] == ["n1", "n2", "h1"], "the digest must show unhinted ideas first, got %r"
       % [r["id"] for r in ranked])

    if fails:
        print("IM9 FAIL:")
        for x in fails:
            print("  -", x)
        return 1
    print("IM9: %d/%d passed -- the extracting prompt carries no self-description; a quote must be verbatim in what "
          "the model saw; one retry with a different instruction, then 'ungrounded' (vet skips); a v1 echo is "
          "re-queued once, offered first, re-extracted from the reply and leaves the queue; miner_echo clears only "
          "with evidence and is proposed only for echoes; no live ledger touched." % (checks, checks))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
