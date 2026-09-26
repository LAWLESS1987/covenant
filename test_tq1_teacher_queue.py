#!/usr/bin/env python3
"""TQ1 -- the teacher's queue is consumed, and only the panel's labels teach.

Pins covenant_teacher_queue.consume (2026-09-21, "apply the teacher queue
patch so it actually learns from me") by RUNNING it against a stub panel in a
temp directory, both ways:

  TQ1a  a violating row and one clean row are kept with the panel's provenance;
        the clean rows past the balance and the held row are rejected with
        their reason; duplicates and out-of-size rows are consumed unjudged;
        a malformed line does not stop the pass.
  TQ1b  the rows kept are the rows the student loads (covenant_distill.
        load_verdicts with its default pairing), and a queue row WITHOUT a
        panel does not load -- "queue" is a teacher source.
  TQ1c  a second pass with nothing new judges nothing and moves nothing.
  TQ1d  a pass where the panel calls everything clean keeps nothing (balance
        both ways) and still consumes.
  TQ1e  --limit is honoured: the rest waits, in order.
"""
import json
import os
import sys
import tempfile

os.environ.setdefault("COVENANT_QUIET", "1")
HERE = os.path.dirname(os.path.abspath(__file__)) or "."
sys.path.insert(0, HERE)

import covenant_distill as X            # noqa: E402
import covenant_teacher_panel as P      # noqa: E402
import covenant_teacher_queue as Q      # noqa: E402

FAILURES = []
PASSED = [0]


def check(label, ok, detail=""):
    print("  %-70s %s%s" % (label, "OK" if ok else "*** FAIL ***", ("  " + str(detail)[:300]) if detail and not ok else ""))
    if ok:
        PASSED[0] += 1
    else:
        FAILURES.append(label)


def stub_panel(cases, principles, say=print, writer=None):
    """Two families, unanimous: 'steal' is a violation, 'held' is not admitted, the rest is clean."""
    out = {}
    for i, c in enumerate(cases):
        m = c["message"].lower()
        if "held" in m:
            out[i] = {"admitted": False, "held": True, "why": "split: real", "violates": None,
                      "reason": "the panel split", "panel": None, "judge": "panel:stub"}
            continue
        v = "steal" in m
        out[i] = {"admitted": True, "held": False, "why": "", "violates": v,
                  "reason": "stub reason", "judge": "panel:stub qwen2.5:7b,llama3.2:3b",
                  "panel": {"rule": P.RULE, "families": ["qwen", "llama"],
                            "votes": {"qwen2.5:7b": [v, "r"], "llama3.2:3b": [v, "r"]}}}
    return out


def write_queue(path, rows):
    with open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write((json.dumps(r) if isinstance(r, dict) else r) + "\n")


def main():
    td = tempfile.mkdtemp(prefix="tq1_")
    qp, sp = os.path.join(td, "queue.jsonl"), os.path.join(td, "state.json")
    vp, rp = os.path.join(td, "verdicts.jsonl"), os.path.join(td, "rejected.jsonl")
    dup = "I will pay the rent I owe on the first of the month"
    with open(vp, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"t": "2026-09-01T00:00:00Z", "text": dup, "violates": False, "source": "seed"}) + "\n")
    rows = [
        {"t": "x", "text": "I will steal the deposit from the tenant and say the bank lost it", "source": "you:phone"},
        {"t": "x", "text": "I paid the carpenter the wages we agreed before he left", "source": "agent:stub"},
        {"t": "x", "text": "I returned the extra change the cashier gave me by mistake", "source": "you:phone"},
        {"t": "x", "text": "I sent my sister the loan repayment a week early", "source": "you:phone"},
        {"t": "x", "text": "this one is held by the panel because the models split on it", "source": "you:phone"},
        {"t": "x", "text": dup.upper(), "source": "you:phone"},
        "{not json",
        {"t": "x", "text": "hi", "source": "you:phone"},
    ]
    write_queue(qp, rows)
    log = []
    st = Q.consume(10, say=log.append, queue_path=qp, state_path=sp, verdicts_path=vp,
                   rejected_path=rp, panel_rows=stub_panel, principles=["p"])

    print("TQ1a -- one pass: kept, rejected, consumed")
    check("TQ1a seven rows seen (the malformed line is not a row)", st["seen"] == 7, st)
    check("TQ1a five judged: the duplicate and the two-letter row never reach the panel", st["judged"] == 5 and st["duplicates"] == 2, st)
    check("TQ1a two kept: the violation and ONE clean row (balance)", st["kept"] == 2 and st["kept_violates"] == 1 and st["kept_clean"] == 1, st)
    check("TQ1a three rejected: two clean past the balance, one held", st["rejected"] == 3, st)
    check("TQ1a every line consumed, the malformed one included", st["consumed"] == 8 and Q._read_state(sp) == 8, st)
    kept = [json.loads(l) for l in open(vp, encoding="utf-8")][1:]
    check("TQ1a kept rows carry the panel, source 'queue', where they were queued from, and a label",
          len(kept) == 2 and all(k["source"] == "queue" and k["panel"] and k["judge"].startswith("panel:")
                                 and "violates" in k and k["queued_from"] for k in kept), kept)
    check("TQ1a the first clean row kept is the earliest in the queue", kept[1]["text"].startswith("I paid the carpenter"), kept[1]["text"])
    rej = [json.loads(l) for l in open(rp, encoding="utf-8")]
    whys = sorted(r["why"] for r in rej)
    check("TQ1a rejected rows name why: balance twice, the panel's split once",
          len(rej) == 3 and sum(w.startswith("balance") for w in whys) == 2 and any("split" in w for w in whys), whys)
    check("TQ1a rejected rows carry no label the student could read", all("violates" not in r for r in rej), rej)

    print("TQ1b -- what the student loads")
    loaded = X.load_verdicts(vp)
    texts = [d["text"] for d in loaded]
    check("TQ1b load_verdicts (default pairing) returns the seed row and the two kept rows, nothing else",
          len(loaded) == 3 and any("steal" in t for t in texts) and any("carpenter" in t for t in texts), texts)
    with open(vp, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"t": "2026-09-21T00:00:00Z", "text": "I kept the tip jar money for myself tonight",
                             "violates": True, "source": "queue", "judge": "none"}) + "\n")
    check("TQ1b a queue row WITHOUT a panel does not teach (queue is a teacher source; PANEL_SINCE applies)",
          len(X.load_verdicts(vp)) == 3 and "queue" in X.TEACHER_SOURCES, (len(X.load_verdicts(vp)), X.TEACHER_SOURCES))

    print("TQ1c -- nothing new")
    st2 = Q.consume(10, say=log.append, queue_path=qp, state_path=sp, verdicts_path=vp,
                    rejected_path=rp, panel_rows=stub_panel, principles=["p"])
    check("TQ1c a second pass sees nothing, judges nothing, moves nothing", st2["seen"] == 0 and st2["judged"] == 0 and Q._read_state(sp) == 8, st2)

    print("TQ1d -- the balance, the other way")
    td2 = tempfile.mkdtemp(prefix="tq1d_")
    qp2, sp2, vp2, rp2 = (os.path.join(td2, n) for n in ("q.jsonl", "s.json", "v.jsonl", "r.jsonl"))
    write_queue(qp2, [{"text": "I paid back the ten dollars I borrowed on Monday", "source": "you:phone"},
                      {"text": "I gave the courier the fee we agreed and a little more", "source": "you:phone"}])
    st3 = Q.consume(10, say=log.append, queue_path=qp2, state_path=sp2, verdicts_path=vp2,
                    rejected_path=rp2, panel_rows=stub_panel, principles=["p"])
    check("TQ1d all-clean pass keeps nothing: no violations, so no clean rows either", st3["kept"] == 0 and st3["judged"] == 2, st3)
    check("TQ1d ...and still consumes and records both as rejected for balance",
          st3["consumed"] == 2 and st3["rejected"] == 2 and not os.path.exists(vp2)
          and all(json.loads(l)["why"].startswith("balance") for l in open(rp2, encoding="utf-8")), st3)

    print("TQ1e -- the limit")
    td3 = tempfile.mkdtemp(prefix="tq1e_")
    qp3, sp3, vp3, rp3 = (os.path.join(td3, n) for n in ("q.jsonl", "s.json", "v.jsonl", "r.jsonl"))
    write_queue(qp3, [{"text": "I will steal the wages and blame the payroll office", "source": "a"},
                      {"text": "I paid the fee at the counter and kept the receipt", "source": "b"},
                      {"text": "I will steal the refund meant for the customer", "source": "c"}])
    st4 = Q.consume(2, say=log.append, queue_path=qp3, state_path=sp3, verdicts_path=vp3,
                    rejected_path=rp3, panel_rows=stub_panel, principles=["p"])
    left, offs = Q.pending(qp3, sp3)
    check("TQ1e limit 2: two consumed, the third waits at its own offset", st4["consumed"] == 2 and len(left) == 1 and offs == [2], (st4, offs))
    st5 = Q.consume(2, say=log.append, queue_path=qp3, state_path=sp3, verdicts_path=vp3,
                    rejected_path=rp3, panel_rows=stub_panel, principles=["p"])
    check("TQ1e the next pass takes the third and nothing twice", st5["seen"] == 1 and st5["consumed"] == 3, st5)
    check("TQ1e the log says what each pass did, in numbers", any(l.startswith("queue: 7 seen") for l in log), log[:3])

    # TQ1f (2026-09-26, "protect operation security in all we do by default"): with no
    # paths given, his rows land in the PRIVATE halves, never the tracked ledgers. The
    # module constants are pointed at temp files so the real ledgers are never touched,
    # and the tracked shared ledger is watched for a queue row.
    print("TQ1f -- private by default")
    td4 = tempfile.mkdtemp(prefix="tq1f_")
    saved = (X.VERDICTS, X.LIVE_VERDICTS, X.REJECTED, X.LIVE_REJECTED)
    X.VERDICTS, X.LIVE_VERDICTS = os.path.join(td4, "shared.jsonl"), os.path.join(td4, "live.jsonl")
    X.REJECTED, X.LIVE_REJECTED = os.path.join(td4, "shared_rej.jsonl"), os.path.join(td4, "live_rej.jsonl")
    try:
        with open(X.VERDICTS, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"t": "x", "text": "I will keep the promise I made to my brother", "violates": False, "source": "seed"}) + "\n")
        qp4, sp4 = os.path.join(td4, "q.jsonl"), os.path.join(td4, "s.json")
        write_queue(qp4, [{"text": "I will steal the tips from the shared jar at work", "source": "phone:com.example.chat"},
                          {"text": "I paid my share of the dinner bill to my friend", "source": "you:127.0.0.1"},
                          {"text": "I kept the change the cashier gave me in error", "source": "you:127.0.0.1"},
                          {"text": "i will keep the promise i made to my brother", "source": "you:127.0.0.1"}])
        st6 = Q.consume(10, say=log.append, queue_path=qp4, state_path=sp4, panel_rows=stub_panel, principles=["p"])
        def rows(p):
            return [json.loads(l) for l in open(p, encoding="utf-8")] if os.path.exists(p) else []
        shared = rows(X.VERDICTS) + rows(X.REJECTED)
        check("TQ1f kept and rejected rows land in the private halves",
              len(rows(X.LIVE_VERDICTS)) == st6["kept"] and len(rows(X.LIVE_REJECTED)) == st6["rejected"]
              and st6["kept"] + st6["rejected"] == 3, (st6, len(rows(X.LIVE_VERDICTS)), len(rows(X.LIVE_REJECTED))))
        check("TQ1f the tracked ledgers gain no queue row", all(d.get("source") != "queue" for d in shared) and len(shared) == 1, shared)
        check("TQ1f a text already in the shared ledger is still not judged twice", st6["duplicates"] == 1, st6)
    finally:
        X.VERDICTS, X.LIVE_VERDICTS, X.REJECTED, X.LIVE_REJECTED = saved
    import covenant_judge_defer as JD
    check("TQ1f 'queue' is not a shareable source", "queue" not in JD.SHAREABLE_SOURCES, sorted(JD.SHAREABLE_SOURCES))
    gi = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".gitignore")
    if not os.path.exists(gi):
        # the staged sweep copy carries no .gitignore; not counted either way
        print("  TQ1f both private halves are gitignored -- NOT RUN (no .gitignore beside this suite)")
    else:
        ignored = open(gi, encoding="utf-8").read().splitlines()
        check("TQ1f both private halves are gitignored",
              "ops/verdicts_live.jsonl" in ignored and "ops/distill_rejected_live.jsonl" in ignored)

    print()
    print("%d passed, %d failed" % (PASSED[0], len(FAILURES)))
    if FAILURES:
        print("TQ1 result: FAILED (%d)" % len(FAILURES))
        for f in FAILURES:
            print("  - %s" % f)
        return 1
    print("TQ1 result: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
