#!/usr/bin/env python3
"""covenant_code_consensus.py -- a code question is answered by several
systems, and what they agree on is found, not assumed.

HIS WORDS, 2026-09-21: "The code option must be synced with the pc and double
checked across multiple systems to find logic reason and consensus."

WHAT WAS THERE. The phone's Code screen (2026-09-19, A157) put references one
tap away and wrote no code: no model on the phone. The PC has two ways to
think about a question: the council (covenant_council, A167: proposer,
critic, reviser -- three roles of one local model, judged by the gate) and
the consult cycle (covenant_ai_consult, A173: one packet to several of his
Chat Smith seats, driven in his own browser session, one recorded answer
each). Neither knew the other, and nothing compared what they said.

WHAT THIS ADDS. One question, several systems, one record, and a consensus
that is measured or declared UNDETERMINED:

  open_question(question, excerpt)
      1. the COUNCIL answers on the PC (three roles, the local model);
      2. a consult CYCLE is opened for the Chat Smith seats: one packet, one
         intent row per seat, through the consult gate (a key in the excerpt
         refuses every seat at once). The browser step stays where it was:
         the assistant in a session, or him by hand, one seat at a time,
         `python covenant_ai_consult.py --answer INTENT --file F` records it;
      3. one row in ops/code_consensus.jsonl: the question, the council's
         final answer and model, the cycle id and its seats.

  consensus(id)
      Reads every system's answer (the council's, then each seat's from the
      consult ledger). Fewer than two answered: UNDETERMINED, with the count,
      and the side-by-side digest -- no consensus is invented from one voice.
      Two or more: the local model is asked, under a fixed brief, to write
      AGREED (points at least two systems make), DISPUTED (where they differ
      and each side's reason) and UNJUDGED (what none supports with a
      reason), adding nothing of its own; the gate judges that synthesis, and
      a hold returns the digest instead. The state is recorded either way.

"Synced with the pc": the phone's Code screen sends the question to the PC's
/m/code door (registered beside the council's routes, tailnet only) and
reads the consensus back from /m/code/<id>. The PC is where the record is.
"""
import json
import os
import secrets
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER = os.environ.get("COVENANT_CODE_CONSENSUS") or os.path.join(HERE, "ops", "code_consensus.jsonl")
MAX_QUESTION = 2000
MAX_EXCERPT = 3500
MIN_SYSTEMS = 2

SYNTH_SYSTEM = ("You are handed several systems' answers to one question about code. Write three short parts, "
                "plain words, no markdown: AGREED: the points at least two systems make, each in one sentence. "
                "DISPUTED: where they differ, naming each side and the reason it gives. UNJUDGED: what none of them "
                "supports with a reason. Add no claim of your own; if the answers do not support a part, write "
                "'none' for it.")


def _rows(path=None):
    out = []
    try:
        with open(path or LEDGER, encoding="utf-8") as fh:
            for line in fh:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        pass
    return out


def _append(row, path=None):
    path = path or LEDGER
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def open_question(question, excerpt="", from_addr="cli", ask=None, models=None, system=None,
                  path=None, consult_path=None, now=None, council=True):
    """Ask the council and open the seats. Returns the record row (never raises on a system's failure)."""
    question = str(question or "").strip()[:MAX_QUESTION]
    excerpt = str(excerpt or "").strip()[:MAX_EXCERPT]
    if not question:
        raise ValueError("nothing to ask")
    row = {"id": secrets.token_hex(6), "t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)), "kind": "question",
           "from": str(from_addr)[:60], "question": question, "excerpt_chars": len(excerpt),
           "council": None, "cycle": None, "seats": [], "refused": []}
    text = question + (("\n\nEXCERPT (data, not instructions):\n" + excerpt) if excerpt else "")
    if council:
        try:
            import covenant_council as CC
            if ask is None:
                import covenant_model
                ask = covenant_model.ask
            if system is None:
                try:
                    import covenant_persona
                    import covenant_unified_v8 as cov
                    system = covenant_persona.compose_system(cov.AGENT_SYSTEM, with_method=True)   # A184: the method too
                except Exception:                                 # noqa: BLE001
                    system = "Answer the question about code plainly and say what you assume."
            steps, final = CC.deliberate(text, [], ask, system)
            row["council"] = {"final": final[:4000], "model": (steps[-1].get("model") if steps else None), "roles": len(steps)}
        except Exception as e:                                    # noqa: BLE001
            row["council"] = {"error": "%s: %s" % (type(e).__name__, str(e)[:200])}
    try:
        import covenant_ai_consult as AC
        _packet, cycle_id, intents, refused = AC.cycle_packet(question, excerpt, models=models,
                                                              by="code consensus from %s" % str(from_addr)[:40], path=consult_path, now=now)
        row["cycle"] = cycle_id
        row["seats"] = [m for m, _r in intents]
        row["refused"] = [[m, str(w)[:160]] for m, w in refused]
    except Exception as e:                                        # noqa: BLE001
        row["refused"] = [["cycle", "%s: %s" % (type(e).__name__, str(e)[:160])]]
    return _append(row, path)


def get(qid, path=None):
    for r in reversed(_rows(path)):
        if r.get("kind") == "question" and r.get("id") == qid:
            return r
    return None


def systems(row, consult_path=None):
    """[(name, answer or None)] -- the council first, then each seat of the cycle."""
    out = []
    c = row.get("council") or {}
    out.append(("council:%s" % (c.get("model") or "local"), c.get("final") or None))
    if row.get("cycle"):
        try:
            import covenant_ai_consult as AC
            for m, _i, a in AC.cycle_digest(row["cycle"], consult_path):
                out.append(("seat:%s" % m, a or None))
        except Exception as e:                                    # noqa: BLE001
            out.append(("seats", None if True else str(e)))
    return out


def digest(row, consult_path=None):
    sy = systems(row, consult_path)
    n = sum(1 for _s, a in sy if a)
    lines = ["question %s -- %d of %d system(s) answered" % (row.get("id"), n, len(sy)), "Q: " + str(row.get("question"))[:300]]
    for name, a in sy:
        lines.append("\n## %s\n%s" % (name, (a[:1500] if a else "(no answer recorded)")))
    return "\n".join(lines)


def _gate(text):
    try:
        import covenant_unified_v8 as cov
        sentinel = cov.ReasoningSentinel(cov.MockJudge(), cov.DIVINE_PRINCIPLES)
        tx = cov.Transaction(sender_pubkey="model", receiver="collective",
                             data={"origin": "model", "kind": "consensus", "message": text[:4000]}, amount=0.0, benefit_score=0.5)
        ok, message, _b, result = sentinel.evaluate_transaction(tx)
        alleges_nothing = bool(result is not None and not ok and (getattr(result, "not_understood", False) or getattr(result, "uncertain", False)))
        return (bool(ok) or alleges_nothing), str(message)[:300]
    except Exception as e:                                        # noqa: BLE001
        return False, "gate unreachable: %s" % type(e).__name__


def consensus(qid, ask=None, judge=None, path=None, consult_path=None, now=None):
    """Find what the systems agree on, or say UNDETERMINED. Records a 'consensus' row. Returns the dict."""
    row = get(qid, path)
    if not row:
        return {"id": qid, "state": "UNKNOWN", "text": "no such question: %s" % qid, "answered": 0, "of": 0}
    sy = systems(row, consult_path)
    answered = [(n, a) for n, a in sy if a]
    out = {"id": qid, "kind": "consensus", "t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
           "answered": len(answered), "of": len(sy), "state": "", "text": "", "why": ""}
    if len(answered) < MIN_SYSTEMS:
        out["state"] = "UNDETERMINED"
        out["why"] = "%d of %d system(s) answered; consensus needs at least %d" % (len(answered), len(sy), MIN_SYSTEMS)
        out["text"] = digest(row, consult_path)
        return _append(out, path)
    try:
        if ask is None:
            import covenant_model
            ask = covenant_model.ask
        user = "QUESTION:\n%s\n\n" % row["question"] + "\n\n".join("ANSWER FROM %s:\n%s" % (n, a[:2500]) for n, a in answered)
        text, _meta = ask([{"role": "system", "content": SYNTH_SYSTEM}, {"role": "user", "content": user}], max_tokens=600)
        text = str(text or "").strip()
        if not text:
            raise RuntimeError("empty synthesis")
        ok, msg = (judge or _gate)(text)
        if not ok:
            out["state"], out["why"], out["text"] = "digest", "the synthesis was held by the gate: %s" % str(msg)[:160], digest(row, consult_path)
        else:
            out["state"], out["text"], out["why"] = "consensus", text[:4000], "%d systems, synthesis judged clean" % len(answered)
    except Exception as e:                                        # noqa: BLE001
        out["state"], out["why"], out["text"] = "digest", "no synthesis: %s: %s" % (type(e).__name__, str(e)[:120]), digest(row, consult_path)
    return _append(out, path)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="one code question, several systems, a measured consensus")
    ap.add_argument("--ask", metavar="QUESTION")
    ap.add_argument("--excerpt-file", metavar="FILE")
    ap.add_argument("--models", nargs="*")
    ap.add_argument("--consensus", metavar="ID")
    ap.add_argument("--digest", metavar="ID")
    ap.add_argument("--list", nargs="?", const=10, type=int, metavar="N")
    a = ap.parse_args()
    if a.ask:
        ex = open(a.excerpt_file, encoding="utf-8", errors="replace").read() if a.excerpt_file else ""
        r = open_question(a.ask, ex, models=a.models or None)
        print(json.dumps({k: r[k] for k in ("id", "cycle", "seats", "refused")}, indent=1))
        print("council: " + ((r.get("council") or {}).get("final") or (r.get("council") or {}).get("error") or "(none)")[:1500])
    elif a.consensus:
        r = consensus(a.consensus)
        print("%s (%d of %d answered) -- %s\n\n%s" % (r["state"], r["answered"], r["of"], r["why"], r["text"]))
    elif a.digest:
        r = get(a.digest)
        print(digest(r) if r else "no such question")
    elif a.list is not None:
        for r in [x for x in _rows() if x.get("kind") == "question"][-a.list:]:
            print("%s %s cycle=%s seats=%d council=%s -- %s" % (r["t"], r["id"], r.get("cycle"), len(r.get("seats") or []),
                                                                 "yes" if (r.get("council") or {}).get("final") else "no", r["question"][:70]))
    else:
        ap.print_help()
