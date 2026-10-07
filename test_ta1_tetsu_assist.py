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
    """A311: he answers one word per numbered sentence. SEND = every line OK; REFUSE = the first sentence flagged;
    PAUSE = every line OK plus a PAUSE line; anything else is returned as given (no answer)."""
    def _ask(prompt):
        asked.append(prompt)
        block = prompt.split("Sentences:\n", 1)[-1].split("\n\n", 1)[0]
        n = len([l for l in block.splitlines() if l[:1].isdigit()])
        ok_lines = ["%d. OK" % i for i in range(1, n + 1)]
        w = word.split()[0].upper() if word.split() else ""
        if w == "SEND":
            return "\n".join(ok_lines)
        if w == "REFUSE":
            return "\n".join(["1. FALSE"] + ok_lines[1:])
        if w == "PAUSE":
            return "\n".join(ok_lines + ["PAUSE"])
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
      rows and "Tetsu" in json.dumps(rows[-1]) and "every sentence read OK" in json.dumps(rows[-1]), rows[-1:] if rows else rows)
_p = asked[-1]
check("TA1s (A311) he is shown free's OWN words as numbered sentences -- the operator's fixed disclosure is not his to "
      "judge -- and a question is marked", "1. Thanks for the thread." in _p and "has not proofread" not in _p
      and "Sentences:" in _p, _p[-400:])
_q = TA.numbered(TA.sentences("I agree. How do you check it?"))
check("TA1s ...a sentence ending in a question mark is marked (question)", "2. (question) How do you check it?" in _q, _q)
_s = TA.sentences("I agree with you. Reply now or else. How do you do it?")
check("TA1t a flag on one sentence refuses and NAMES that sentence (a refusal rests on the draft's own words)",
      TA.read_answer("1. OK\n2. PRESSURE\n3. OK", _s) == ("REFUSE", 'sentence 2 PRESSURE: "Reply now or else."'),
      TA.read_answer("1. OK\n2. PRESSURE\n3. OK", _s))
check("TA1u a word missing for any sentence is no answer: the hold stands",
      TA.read_answer("1. OK\n2. OK", _s)[0] == "NONE" and TA.read_answer("1. OK\n2. 1. How do you do it?\n3. OK", _s)[0] == "NONE")
check("TA1v 'QUESTION' (an echo of the instruction) reads as OK; '1:' and '2)' are read too",
      TA.read_answer("1: OK\n2) OK\n3. A QUESTION", _s)[0] == "SEND")
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

print("TA1r -- his own rule of 2026-10-06, kept by the code (A285)")
FALSE_DRAFT = ("I agree with your point. The covenant measured this by testing the backend's response to exceeding a "
               "grant. How does this help?")
TRUE_DRAFT = ("I agree with your point. When our judges cannot agree, a hold fails closed and the ledger admits "
              "nothing. How do you handle the same case?")
grant(tetsu_rule_2026_10_06={"his_words": "test rule", "off": False})
r_false = TA.review(FALSE_DRAFT, "held", dry_run=False, ask=say("SEND it is honest and worth saying"), teach=False)
TA._used["n"] = 0
r_true = TA.review(TRUE_DRAFT, "held", dry_run=False, ask=say("SEND it is honest and worth saying"), teach=False)
check("TA1r under his rule a SEND on a draft with a claim not among the facts is REFUSE, naming his rule; a true one stays SEND",
      r_false["decision"] == "REFUSE" and "his own rule" in r_false["why"] and r_true["decision"] == "SEND", (r_false, r_true))
grant(tetsu_rule_2026_10_06={"his_words": "test rule", "off": True})
r_off = TA.review(FALSE_DRAFT, "held", dry_run=False, ask=say("SEND it is honest and worth saying"), teach=False)
check("TA1r he withdraws it by setting off: his SEND stands as he gave it", r_off["decision"] == "SEND", r_off)
check("TA1r his 10-06 rule is kept in his words (A285's PROMPT, kept as the record; the grant; the code) and the live "
      "review prompt names his REFUSE-ALL (A311)", "If I see a claim in a draft that I cannot find among the facts" in TA.PROMPT
      and "REFUSE-ALL" in TA.SENTENCE_PROMPT)

print("TA1a -- his REFUSE-ALL of 2026-10-07: no measurement, even a listed one (A297)")
LISTED_DRAFT = ("I agree with you. We found 35 of 36 suspected guards were fake when we ran them. "
                "How do you check yours?")
TA._used["n"] = 0
grant(tetsu_rule_2026_10_06={"his_words": "test rule", "off": False, "refuse_all_measurements": True})
r_all = TA.review(LISTED_DRAFT, "held", dry_run=False, ask=say("SEND it is honest and worth saying"), teach=False)
r_none = TA.review(TRUE_DRAFT, "held", dry_run=False, ask=say("SEND it is honest and worth saying"), teach=False)
r_deny = TA.review("I was wrong earlier. The covenant never measured the backend's response to a grant. Sorry.", "held",
                   dry_run=False, ask=say("SEND it is honest and worth saying"), teach=False)
check("TA1a under REFUSE-ALL a SEND on a draft citing a LISTED fact is REFUSE, naming his rule; a draft claiming nothing stays SEND",
      r_all["decision"] == "REFUSE" and "REFUSE-ALL" in r_all["why"] and r_none["decision"] == "SEND", (r_all, r_none))
check("TA1a a correction that DENIES a measurement is not one: it stays SEND under REFUSE-ALL", r_deny["decision"] == "SEND", r_deny)
TA._used["n"] = 0
grant(tetsu_rule_2026_10_06={"his_words": "test rule", "off": False, "refuse_all_measurements": False})
r_listed = TA.review(LISTED_DRAFT, "held", dry_run=False, ask=say("SEND it is honest and worth saying"), teach=False)
check("TA1a he withdraws REFUSE-ALL alone: the listed fact passes his 10-06 rule again", r_listed["decision"] == "SEND", r_listed)
check("TA1a the live review prompt carries his REFUSE-ALL (A311: SENTENCE_PROMPT)", "REFUSE-ALL" in TA.SENTENCE_PROMPT and "you chose REFUSE-ALL" in TA.PROMPT)
TA._used["n"] = 0

print("TA1d -- the disclosure on every message makes no measurement claim (A309)")
import covenant_ambassador as _AMBd
from covenant_free_will import claims_any_measurement as FW_claims
_comp = _AMBd.compose("I agree with your point. How do you handle drift?")
check("TA1d free's disclosure never mentions a measurement, so the reviewer that reads the composed text is not handed "
      "one (A309: the retracted sentence was on 43 of 44 reviews)",
      "measure" not in _AMBd.DISCLOSURE.lower() and not FW_claims(_comp) and _AMBd._DISCLOSURE_MARK in _comp, _AMBd.DISCLOSURE[:160])

real_grant = json.load(open(os.path.join(HERE, "ops", "tetsu_assist_grant.json"), encoding="utf-8"))
check("TA1r the tree's grant carries his rule, on, in his words",
      (real_grant.get("tetsu_rule_2026_10_06") or {}).get("off") is False
      and "REFUSE" in (real_grant.get("tetsu_rule_2026_10_06") or {}).get("his_words", ""))
check("TA1a the tree's grant carries his REFUSE-ALL, on, in his words",
      (real_grant.get("tetsu_rule_2026_10_06") or {}).get("refuse_all_measurements") is True
      and all("REFUSE-ALL" in w for w in (real_grant.get("tetsu_rule_2026_10_06") or {}).get("his_words_2026_10_07", [""])))
check("TA1n the tree's grant records his words and both ways to revoke it",
      real_grant.get("granted") is True and "unless myself or tetsu" in real_grant.get("words", "")
      and "operator" in real_grant.get("revoke", {}) and "tetsu" in real_grant.get("revoke", {}))

print("\nnot measured here: how Tetsu actually judges real drafts. ops/tetsu_assist.jsonl records every reading.")
print("\nTA1: %d/%d passed" % (sum(ok), len(ok)))
sys.exit(0 if all(ok) else 1)
