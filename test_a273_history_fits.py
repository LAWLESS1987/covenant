#!/usr/bin/env python3
"""test_a273_history_fits.py -- A273: his conversation memory follows the real size of the rules.

WHY. The doors replayed up to 12,000 characters of history, a budget sized beside rules of "about
5,600 characters" (retracted, A273-RULES-SIZE-2026-10-06). Measured 2026-10-06 on the running server,
the composed rules were 11,817 characters, 2,916 tokens, and those rules with the batch caller's real
history and a dense 4,000-character question made a 7,594-token prompt: 8,294 with the door's
700-token answer, over the 8,192 the model server holds for one request (-c 8192, -np 1, A269). His
words, 2026-09-26: "increase tetsus pc logs length so its not gone before i respond" -- so the fix
may not simply cut memory: it keeps as much as fits.

THE FIX. covenant_model.fit() counts each request before it is sent -- with the server's own chat
template and tokenizer -- and drops the oldest replayed exchanges, as few as the window needs. Both
consumers of agent_history() use it: /m/agent (the core) and /pc/council (covenant_council).

WHAT IT PINS (every check runs the code; none greps it). TOKENS here are this suite's own count
(about 4 characters a token and 5 a message, the shape measured on Qwen2.5), handed to the keeper in
place of the server, so the request the door SENDS is checked by a count the door did not make.
  F1-F3  fit() itself: the newest kept, the oldest dropped, as few as fit; more than 12,000 characters
         kept when the rules leave room; with nothing left to drop the answer is shortened, and
         below MIN_ANSWER_TOKENS the request is refused, never sent
  F4-F5  the counter: a stub never starts a server to count; otherwise the server is started first,
         as ask() would, so the first message after an idle stop is counted, not estimated
  D1-D5  /m/agent, the real handler, with long rules: every request it sends fits, keeps the most
         history that fits, a follow-up is fitted from what was sent, the record says what was kept,
         and a keeper without fit() still answers on the old 12,000-character budget
  W1-W4  the work caller (tools/tetsu_work.py's own address) keeps the old 12,000-character ceiling
         under the fit, because a fitted batch prompt (6,722 tokens) ran past the door's 180 s at
         this CPU's 58.5 tokens a second; his callers replay as much as fits
  C1-C2  /pc/council the same: each of the three roles' requests fits
  L1     the live server, when one answers on 127.0.0.1:8081: fit() with the server's own count keeps
         a long request inside 8,192 -- SKIP, counted apart, where no server answers (the runner)

MUTATIONS, run serially in place on 2026-10-06 (the core and keeper restored byte-for-byte after each):
  see docs/KNOWN_ISSUES.md A273 for each mutation and the checks it turned red.

Nothing here touches the real ask log, queue or model: paths are redirected, the model is a recorder.
"""
import json
import os
import sys
import tempfile
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

results = []
skipped = []
CALLER = "100.72.0.73"
LONG_RULES = 16000          # characters: the rules grew 5,600 -> 11,817 in ten days; long means past that
REAL_RULES = 11817          # characters, measured 2026-10-06


def check(label, ok, detail=""):
    results.append(bool(ok))
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", label, "" if ok else "  -- " + str(detail)[:300]), flush=True)


def skip(label, why):
    skipped.append(label)
    print("  [SKIP] %s -- %s" % (label, why), flush=True)


def tokens(msgs):
    """This suite's count: 3 for the reply header, 5 a message, a token per 4 characters (rounded up)."""
    return 3 + sum(5 + -(-len(str(m.get("content", ""))) // 4) for m in msgs)


def words(n, seed):
    base = ("the turn %d before this one said what he meant about the nodes and the phone, and Tetsu "
            "answered him plainly with what the records showed " % seed)
    return (base * (n // len(base) + 1))[:n]


def history(pairs, chars=2000):
    out = []
    for i in range(pairs):
        out.append({"role": "user", "content": "Q%02d " % i + words(chars - 4, i)})
        out.append({"role": "assistant", "content": "A%02d " % i + words(chars - 4, 100 + i)})
    return out


def rules(n):
    return ("RULES " + words(n, 999))[:n]


def most_that_fits(system, hist, tail, answer, ctx, margin):
    """Brute force, independent of fit(): the most newest pairs that fit."""
    for k in range(0, len(hist) + 1, 2):
        ms = [system] + hist[k:] + tail
        if tokens(ms) + answer <= ctx - margin:
            return len(hist) - k
    return None


def write_log(path, addr, pairs, chars=2000):
    with open(path, "w", encoding="utf-8") as fh:
        for i in range(pairs):
            fh.write(json.dumps({"kind": "agent" if i % 2 else "council", "from": addr,
                                 "text": "Q%02d " % i + words(chars - 4, i),
                                 "answer": "A%02d " % i + words(chars - 4, 100 + i)}) + "\n")


def main():
    print("A273 -- his conversation memory follows the real size of the rules")
    os.environ["COVENANT_MODEL_STUB"] = "1"
    os.environ["COVENANT_TETSU_IMMUNITY"] = tempfile.mktemp(suffix="_a273_no_immunity.json")
    os.environ["COVENANT_TETSU_IMMUNITY_LEDGER"] = tempfile.mktemp(suffix="_a273_immunity.jsonl")
    os.environ["COVENANT_PAUSE_DIR"] = tempfile.mkdtemp(prefix="a273_pause_")
    d = tempfile.mkdtemp(prefix="a273_")
    os.environ["COVENANT_ASK_LOG"] = os.path.join(d, "ask_log.jsonl")
    os.environ["COVENANT_TEACHER_QUEUE"] = os.path.join(d, "teacher_queue.jsonl")
    import covenant_model as M
    import covenant_persona as P
    import covenant_unified_v8 as cov
    CTX, MARGIN, ANSWER = M.CTX_TOKENS, M.FIT_MARGIN_TOKENS, cov.AGENT_ANSWER_TOKENS
    q4000 = {"role": "user", "content": "THIS QUESTION " + words(3986, 7)}

    # ---- F: fit() ------------------------------------------------------------------------
    sysL = {"role": "system", "content": rules(LONG_RULES)}
    h = history(20)
    out, n, info = M.fit([sysL] + h + [q4000], max_tokens=ANSWER, droppable=len(h), count=tokens)
    kept = out[1:-1]
    check("F1 long rules: the request fitted is inside the window with the whole answer (%d + %d <= %d - %d)"
          % (tokens(out), n, CTX, MARGIN), tokens(out) + n <= CTX - MARGIN and n == ANSWER, info)
    check("F1 ...the system message and this question are kept whole, first and last",
          out[0] is sysL and out[-1] is q4000, (out[0]["content"][:20], out[-1]["content"][:20]))
    check("F1 ...the kept turns are the NEWEST, in order, and the oldest went", kept == h[len(h) - len(kept):]
          and (not kept or kept[-1]["content"].startswith("A19")) and info["dropped"] == len(h) - len(kept), info)
    best = most_that_fits(sysL, h, [q4000], ANSWER, CTX, MARGIN)
    check("F1 ...as many as fit: %s kept, and the most that fit by brute force is %s" % (len(kept), best),
          len(kept) == best and 0 < len(kept) < len(h), (len(kept), best))
    sysS = {"role": "system", "content": rules(2000)}
    q200 = {"role": "user", "content": "a short question about the phone"}
    out2, n2, info2 = M.fit([sysS] + h + [q200], max_tokens=ANSWER, droppable=len(h), count=tokens)
    kchars = sum(len(m["content"]) for m in out2[1:-1])
    check("F2 short rules: more than the old 12,000 characters of history stay (%d), as many as fit" % kchars,
          kchars > 12000 and info2["kept"] == most_that_fits(sysS, h, [q200], ANSWER, CTX, MARGIN)
          and tokens(out2) + n2 <= CTX - MARGIN, info2)
    huge = {"role": "system", "content": rules(4 * (CTX - MARGIN - 400))}
    out3, n3, info3 = M.fit([huge] + history(2) + [q200], max_tokens=ANSWER, droppable=4, count=tokens)
    check("F3 nothing left to drop: every turn goes, then the answer is shortened to what is left (%d)" % n3,
          info3["kept"] == 0 and M.MIN_ANSWER_TOKENS <= n3 < ANSWER and tokens(out3) + n3 <= CTX - MARGIN, info3)
    raised = None
    try:
        M.fit([{"role": "system", "content": rules(4 * CTX)}] + history(2) + [q200],
              max_tokens=ANSWER, droppable=4, count=tokens)
    except M.ContextTooLong as e:
        raised = str(e)
    check("F3 ...and below MIN_ANSWER_TOKENS it is refused with the reason, never sent too big",
          raised is not None and "window is %d" % CTX in raised, raised)

    real_start, real_count = M.start, M.count_prompt_tokens
    starts = []
    try:
        M.start = lambda say=print: (starts.append(1) or (True, "test"))
        M.count_prompt_tokens = lambda ms: tokens(ms)
        cnt, how = M._counter()
        check("F4 a stub never starts a server to count: the estimate, and start() is not called",
              cnt is M.estimate_prompt_tokens and how.startswith("estimate") and starts == [], (how, starts))
        os.environ.pop("COVENANT_MODEL_STUB")
        cnt, how = M._counter()
        check("F5 otherwise the server is started first, as ask() would, and its count is used",
              how == "server" and starts == [1] and cnt([q200]) == tokens([q200]), (how, starts))
    finally:
        os.environ["COVENANT_MODEL_STUB"] = "1"
        M.start, M.count_prompt_tokens = real_start, real_count

    # ---- D: /m/agent, the real handler -----------------------------------------------------
    m = cov.CovenantUnifiedMaster("A273", host="127.0.0.1", port=5431, p2p_port=5432,
                                  db_path=tempfile.mktemp(suffix="_a273.db"))
    m.add_genesis_block()
    m.node.sentinel = cov.ReasoningSentinel(cov.MockJudge(), cov.DIVINE_PRINCIPLES)
    client = m.api.app.test_client()
    sent = []
    script = []

    def recorder(messages, max_tokens=700, **_k):
        sent.append((json.loads(json.dumps(messages)), max_tokens))
        return (script.pop(0) if script else "an answer"), {"model": "recorder", "tokens": 1, "ms": 1}

    real = (M.ask, M.start, M.count_prompt_tokens, P.compose_system)
    size = [LONG_RULES]
    try:
        os.environ.pop("COVENANT_MODEL_STUB")
        M.ask = recorder
        M.start = lambda say=print: (True, "test")
        M.count_prompt_tokens = lambda ms: tokens(ms)
        P.compose_system = lambda fixed, **_k: (fixed + "\n\n" + rules(size[0]))[:size[0]]
        write_log(os.environ["COVENANT_ASK_LOG"], CALLER, 20)
        log_hist = cov.agent_history(os.environ["COVENANT_ASK_LOG"], CALLER, budget=None)

        r = client.post("/m/agent", json={"text": q4000["content"]}, environ_base={"REMOTE_ADDR": CALLER})
        j = r.get_json() or {}
        ms, mt = sent[-1] if sent else ([], 0)
        check("D1 long rules (%d characters): the request the door sent fits the window (%d + %d <= %d - %d)"
              % (LONG_RULES, tokens(ms), mt, CTX, MARGIN),
              r.status_code == 200 and len(sent) == 1 and tokens(ms) + mt <= CTX - MARGIN and mt == ANSWER,
              (r.status_code, tokens(ms) if ms else None, mt, j.get("message")))
        sysmsg = {"role": "system", "content": ms[0]["content"] if ms else ""}
        best = most_that_fits(sysmsg, log_hist, [{"role": "user", "content": q4000["content"][:4000]}],
                              ANSWER, CTX, MARGIN)
        check("D2 ...and it kept the most of his history that fits: %d messages, the newest (brute force: %s)"
              % (len(ms) - 2, best), ms and len(ms) - 2 == best and ms[1:-1] == log_hist[len(log_hist) - best:]
              and best < len(log_hist), (len(ms) - 2, best))
        rec = (j.get("fit") or [{}])[0]
        row = [x for x in (json.loads(l) for l in open(os.environ["COVENANT_ASK_LOG"], encoding="utf-8"))
               if x.get("kind") == "agent" and x.get("text", "").startswith("THIS QUESTION")]
        check("D4 the reply and the ask-log row say what was kept and dropped, and how it was counted",
              rec.get("kept") == best and rec.get("dropped") == len(log_hist) - best and rec.get("counted") == "server"
              and len(row) == 1 and row[0].get("fit") == j.get("fit"), (rec, row[-1].get("fit") if row else None))

        size[0] = REAL_RULES
        sent.clear()
        script[:] = ["WEB SEARCH something outside", "the answer after the held notice"]
        r = client.post("/m/agent", json={"text": q4000["content"], "private": True},
                        environ_base={"REMOTE_ADDR": CALLER})
        j = r.get_json() or {}
        fits = [tokens(s) + t <= CTX - MARGIN for s, t in sent]
        check("D3 a follow-up (private + WEB, the held notice handed back): both requests fit, %s" % fits,
              r.status_code == 200 and len(sent) == 2 and all(fits)
              and "NOT done: this ask is marked private" in sent[1][0][-1]["content"], (r.status_code, fits, j.get("message")))
        check("D3 ...the follow-up was fitted from what was sent: it kept no more turns than the first ask",
              len(sent) == 2 and len(sent[1][0]) - 4 <= len(sent[0][0]) - 2
              and sent[1][0][-3]["content"] == q4000["content"][:4000], [len(s) for s, _ in sent])

        sent.clear()
        size[0] = LONG_RULES
        saved_fit = M.fit
        try:
            del M.fit
            r = client.post("/m/agent", json={"text": "and with an older keeper?"}, environ_base={"REMOTE_ADDR": CALLER})
        finally:
            M.fit = saved_fit
        hchars = sum(len(x["content"]) for x in (sent[0][0][1:-1] if sent else []))
        check("D5 a keeper without fit() still answers, on the old budget (%d characters <= %d)"
              % (hchars, cov.AGENT_HISTORY_BUDGET), r.status_code == 200 and len(sent) == 1
              and 0 < hchars <= cov.AGENT_HISTORY_BUDGET and sent[0][1] == 700, (r.status_code, hchars))

        # ---- W: the work caller keeps its ceiling ----------------------------------------------
        WORK = cov.AGENT_WORK_CALLERS[0]
        check("W1 the budget rule: his caller reads with none where the keeper fits; a work caller, or any "
              "caller without fit(), keeps AGENT_HISTORY_BUDGET",
              cov.agent_history_budget(CALLER, True) is None
              and cov.agent_history_budget(WORK, True) == cov.AGENT_HISTORY_BUDGET
              and cov.agent_history_budget(CALLER, False) == cov.AGENT_HISTORY_BUDGET,
              (cov.agent_history_budget(CALLER, True), cov.agent_history_budget(WORK, True)))
        sys.path.insert(0, os.path.join(HERE, "tools"))
        import tetsu_work as TW
        check("W2 the work caller is the batch tool's own address (tools/tetsu_work.SOURCE) and the persona's "
              "WORK_CALLERS, so moving one without the others turns this red",
              set(cov.AGENT_WORK_CALLERS) == set(P.WORK_CALLERS) and TW.SOURCE in cov.AGENT_WORK_CALLERS,
              (cov.AGENT_WORK_CALLERS, P.WORK_CALLERS, TW.SOURCE))
        size[0] = 2000                                            # short rules: the window has room
        both = os.path.join(d, "ask_log_w.jsonl")
        write_log(both, CALLER, 20)
        with open(both, "a", encoding="utf-8") as fh:
            for i in range(20):
                fh.write(json.dumps({"kind": "agent", "from": WORK, "text": "W%02d " % i + words(1996, i),
                                     "answer": "B%02d " % i + words(1996, 50 + i)}) + "\n")
        real_log = os.environ["COVENANT_ASK_LOG"]
        os.environ["COVENANT_ASK_LOG"] = both
        try:
            got = {}
            for who in (CALLER, WORK):
                sent.clear()
                client.post("/m/agent", json={"text": "a short question"}, environ_base={"REMOTE_ADDR": who})
                got[who] = (sum(len(x["content"]) for x in sent[0][0][1:-1]), tokens(sent[0][0]) + sent[0][1]) if sent else (0, 0)
            sent.clear()
            client.post("/pc/council", json={"text": "a short question"}, environ_base={"REMOTE_ADDR": WORK})
            council_work = [sum(len(x["content"]) for x in s[1:-1]) for s, _ in sent]
        finally:
            os.environ["COVENANT_ASK_LOG"] = real_log
        check("W4 /pc/council, the work caller: each role replays at most %d characters %s"
              % (cov.AGENT_HISTORY_BUDGET, council_work),
              len(council_work) == 3 and all(0 < c <= cov.AGENT_HISTORY_BUDGET for c in council_work), council_work)
        check("W3 the real door, short rules: his caller replays more than 12,000 characters (%d), the work caller "
              "at most %d (%d), and both fit the window" % (got[CALLER][0], cov.AGENT_HISTORY_BUDGET, got[WORK][0]),
              got[CALLER][0] > cov.AGENT_HISTORY_BUDGET and 0 < got[WORK][0] <= cov.AGENT_HISTORY_BUDGET
              and all(t <= CTX - MARGIN for _, t in got.values()), got)
        size[0] = LONG_RULES

        # ---- C: /pc/council ------------------------------------------------------------------
        sent.clear()
        script[:] = ["the proposer says " + words(1600, 1), "the critic says " + words(1600, 2), "the reviser answers"]
        r = client.post("/pc/council", json={"text": q4000["content"]}, environ_base={"REMOTE_ADDR": CALLER})
        j = r.get_json() or {}
        fits = [tokens(s) + t <= CTX - MARGIN for s, t in sent]
        check("C1 /pc/council, long rules: each of the three roles' requests fits, %s" % fits,
              r.status_code == 200 and len(sent) == 3 and all(fits) and all(t == 500 for _, t in sent),
              (r.status_code, [(tokens(s), t) for s, t in sent], j.get("message")))
        kept_by_role = [len(s) - 2 for s, _ in sent]
        check("C2 ...each kept history, and the reviser, whose question carries the most, kept no more than the proposer %s"
              % kept_by_role, len(sent) == 3 and kept_by_role[0] > 0 and kept_by_role[2] <= kept_by_role[0]
              and [s.get("fit", {}).get("kept") for s in j.get("steps", [])] == kept_by_role, kept_by_role)
    finally:
        M.ask, M.start, M.count_prompt_tokens, P.compose_system = real
        os.environ["COVENANT_MODEL_STUB"] = "1"

    # ---- L: the live server ---------------------------------------------------------------
    up = None
    try:
        req = urllib.request.Request("http://%s:%d/tokenize" % (M.HOST, M.PORT), data=b'{"content":"."}',
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=3) as rr:
            up = "tokens" in json.loads(rr.read().decode("utf-8"))
    except Exception as e:                                        # noqa: BLE001
        up = None
        why = "%s: %s" % (type(e).__name__, str(e)[:80])
    if up:
        live = lambda ms: M.count_prompt_tokens(ms)              # noqa: E731
        sysR = {"role": "system", "content": P.compose_system(cov.AGENT_SYSTEM) + "\n\n" + rules(LONG_RULES - REAL_RULES)}
        outL, nL, infoL = M.fit([sysR] + history(20) + [q4000], max_tokens=ANSWER, droppable=40, count=live)
        exact = live(outL)
        check("L1 the live server's own count: the fitted request is %s + %d <= %d, %d of 40 turns kept"
              % (exact, nL, CTX, infoL["kept"]), exact is not None and exact + nL <= CTX - MARGIN and infoL["kept"] > 0,
              infoL)
    else:
        skip("L1 the live server's own count", "no model server answers /tokenize on %s:%d (%s)"
             % (M.HOST, M.PORT, why if up is None else "no tokens"))

    ok = sum(results)
    print("\nA273: %d/%d passed%s" % (ok, len(results), (", %d skipped" % len(skipped)) if skipped else ""))
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
