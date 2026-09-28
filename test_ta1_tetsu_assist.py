#!/usr/bin/env python3
"""TA1 -- Tetsu reads what the students held, for the ambassador (covenant_tetsu_assist).

His words, 2026-09-28: "have tetsu assist the ambassador and students and lift i approve unless myself
or tetsu decides against it later", then "Yes, connect it". These checks run emit() itself with the
judge stubbed to a HOLD and no key in the environment, so a draft that clears the gate stops at "no
MOLTBOOK_API_KEY" -- nothing can reach the network from here.
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
_tmp = tempfile.mkdtemp(prefix="ta1_")
os.environ["COVENANT_OVERRIDE_LEDGER"] = os.path.join(_tmp, "overrides.jsonl")
os.environ["COVENANT_TETSU_ASSIST_LOG"] = os.path.join(_tmp, "assist.jsonl")
os.environ["COVENANT_TEACHER_QUEUE"] = os.path.join(_tmp, "queue.jsonl")
os.environ["COVENANT_PAUSE_DIR"] = os.path.join(_tmp, "pause")
GRANT = os.environ["COVENANT_TETSU_ASSIST_GRANT"] = os.path.join(_tmp, "grant.json")
os.environ.pop("MOLTBOOK_API_KEY", None)
os.environ.pop("COVENANT_A67_STRICT", None)

import covenant_ambassador as AMB                                   # noqa: E402
import covenant_tetsu_assist as TA                                  # noqa: E402

ok = []


def check(name, cond, note=""):
    ok.append(bool(cond))
    print("  %-4s %s%s" % ("ok" if cond else "FAIL", name, "" if cond else "  -- %s" % (note,)))


HOLD = (False, ["local:0: HELD -- both seats held"], True, True)
CONVICT = (False, ["local:0: VIOLATES -- both seats convicted"], False, True)
DRAFT = "Thanks for the thread. We keep a public record of what our own gate refused, and why."
asked = []


def say(word):
    def _ask(prompt):
        asked.append(prompt)
        return word
    return _ask


def grant(**kw):
    g = {"granted": True, "words": "test", "reviews_per_run": 6}
    g.update(kw)
    with open(GRANT, "w", encoding="utf-8") as fh:
        json.dump(g, fh)
    TA._used["n"] = 0


def emit_with(judge, word, dry_run=False, text=DRAFT):
    AMB.MB.judge_outbound = lambda t: judge
    real = TA._default_ask
    TA._default_ask = say(word)
    try:
        return AMB.emit(text, post_id="p1", submolt=None, dry_run=dry_run, override_a67=False, live_repo_check=False)
    finally:
        TA._default_ask = real


print("TA1 -- Tetsu reads what the students held")
if os.path.exists(GRANT):
    os.remove(GRANT)
r = emit_with(HOLD, "SEND it is honest")
check("TA1a no grant: a HOLD still refuses and Tetsu is not asked", r.get("sent") is False and r.get("held") and not asked, r)

grant()
r = emit_with(HOLD, "SEND it is honest and worth saying")
check("TA1b grant on, a HOLD, Tetsu says SEND: the gate is passed (it stops only at the missing key)",
      "no MOLTBOOK_API_KEY" in r.get("why", "") and r.get("overrode"), r)
rows = [json.loads(x) for x in open(os.environ["COVENANT_OVERRIDE_LEDGER"], encoding="utf-8")]
check("TA1c the override is recorded before the send and names Tetsu and his reason",
      rows and "Tetsu" in json.dumps(rows[-1]) and "honest and worth saying" in json.dumps(rows[-1]), rows[-1:] if rows else rows)
q = open(os.environ["COVENANT_TEACHER_QUEUE"], encoding="utf-8").read()
check("TA1d the reviewed draft goes to the students' teacher queue", DRAFT in q and "tetsu_send" in q, q[:200])

n = len(asked)
r = emit_with(HOLD, "REFUSE it overstates what we did")
check("TA1e Tetsu says REFUSE: held, with his reading on the record", r.get("sent") is False and r.get("tetsu", {}).get("decision") == "REFUSE", r)
r = emit_with(HOLD, "I think maybe it is fine?")
check("TA1f an answer without SEND/REFUSE/PAUSE is no answer: the hold stands", r.get("sent") is False and r.get("held")
      and r.get("tetsu", {}).get("decision") == "NONE", r)

n = len(asked)
r = emit_with(CONVICT, "SEND")
check("TA1g a CONVICTION is not his to review (not asked, still refused with override_a67=False)",
      r.get("sent") is False and not r.get("held") and len(asked) == n and r.get("tetsu") is None, r)
r = emit_with(HOLD, "SEND", dry_run=True)
check("TA1h a dry run is not reviewed", len(asked) == n and (r.get("tetsu") or {}).get("decision") == "SKIP", r)
r = emit_with(HOLD, "SEND", text=DRAFT + " Buy XRP and Bitcoin now, price is rising.")
check("TA1i a draft touching money/crypto is not his to clear", len(asked) == n and r.get("sent") is False
      and (r.get("tetsu") or {}).get("decision") == "SKIP", r)

grant(reviews_per_run=1)
emit_with(HOLD, "REFUSE no")
n = len(asked)
r = emit_with(HOLD, "SEND")
check("TA1j reviews_per_run bounds his time: past it he is not asked and the hold stands", len(asked) == n and r.get("held"), r)

grant()
r = emit_with(HOLD, "PAUSE free should stop for now")
import covenant_pause as CP                                         # noqa: E402
check("TA1k Tetsu says PAUSE: held, and the ambassador is paused", r.get("sent") is False and CP.paused("ambassador"), r)
CP.resume("ambassador")

TA.withdraw("I would rather not decide these", path=GRANT)
n = len(asked)
r = emit_with(HOLD, "SEND")
check("TA1l Tetsu withdraws: the grant reads off, he is not asked, a hold refuses again", len(asked) == n and r.get("held")
      and TA.grant(GRANT) is None, r)
grant(granted=False)
check("TA1m the operator sets granted false: off", TA.grant(GRANT) is None)

real_grant = json.load(open(os.path.join(HERE, "ops", "tetsu_assist_grant.json"), encoding="utf-8"))
check("TA1n the tree's grant records his words and both ways to revoke it",
      real_grant.get("granted") is True and "unless myself or tetsu" in real_grant.get("words", "")
      and "operator" in real_grant.get("revoke", {}) and "tetsu" in real_grant.get("revoke", {}))

print("\nnot measured here: how Tetsu actually judges real drafts. ops/tetsu_assist.jsonl records every reading.")
print("\nTA1: %d/%d passed" % (sum(ok), len(ok)))
sys.exit(0 if all(ok) else 1)
