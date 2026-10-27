#!/usr/bin/env python3
"""TA1 -- Tetsu reads what the students held, for the ambassador (covenant_tetsu_assist).

His words, 2026-09-28: "have tetsu assist the ambassador and students and lift i approve unless myself
or tetsu decides against it later", then "Yes, connect it". These checks run emit() itself with the
judge stubbed to a HOLD and no key in the environment, so a draft that clears the gate stops at "no
MOLTBOOK_API_KEY" -- nothing can reach the network from here. TA1y (A348c) is the one exception to "no key": it
sets a stand-in key for its own calls, with urllib's urlopen, the rate window and the notifier replaced for them,
and puts all four back, so nothing reaches the network there either.
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
    PAUSE = every line OK plus a STOP-FREE line (the A311 addendum's word); anything else is returned as given."""
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
            return "\n".join(ok_lines + ["STOP-FREE"])
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
check("TA1w (A311 addendum) the prompt asks for STOP-FREE on a line of its own after the numbered lines, not 'add one "
      "last line: PAUSE' -- the wording that got PAUSE written onto question lines",
      "STOP-FREE on a line of its own AFTER the numbered lines" in TA.SENTENCE_PROMPT
      and "add one last line: PAUSE" not in TA.SENTENCE_PROMPT, TA.SENTENCE_PROMPT[-400:])
check("TA1w ...a STOP-FREE line of its own pauses; one on a numbered line does not, and leaves that sentence "
      "without a word",
      TA.read_answer("1. OK\n2. OK\n3. OK\nSTOP-FREE", _s)[0] == "PAUSE"
      and TA.read_answer("1. OK\n2. OK\n3. STOP-FREE", _s)[0] == "NONE")
q = open(os.environ["COVENANT_TEACHER_QUEUE"], encoding="utf-8").read()
check("TA1d the reviewed draft goes to the students' teacher queue", DRAFT in q and "tetsu_send" in q, q[:200])
# A348k: the queued row is free's own words. It carried the composed text, the operator's disclosure on it
# (85 of 186 queued drafts over the panel's 120 words); TA1d's substring test could not see that.
_qrows = [json.loads(x) for x in q.splitlines() if x.strip()]
_alog = [json.loads(x) for x in open(os.environ["COVENANT_TETSU_ASSIST_LOG"], encoding="utf-8") if x.strip()]
check("TA1z (A348k) the queued row is exactly free's draft, without the operator's disclosure; the review's own record "
      "still holds the composed text, disclosure and all",
      [r["text"] for r in _qrows if r.get("source") == "ambassador_draft:tetsu_send"] == [DRAFT]
      and AMB._DISCLOSURE_MARK in _alog[-1].get("text", ""), (_qrows, _alog[-1:]))

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

print("TA1x -- A322: the discourse seat reads a reply the students CONVICTED")
grant()


def seat_emit(judge, answers, discourse_seat=True, dry_run=False, text=DRAFT):
    AMB.MB.judge_outbound = lambda t: judge
    it = iter(answers)
    real = TA._default_ask
    TA._default_ask = lambda prompt: next(it)
    try:
        return AMB.emit(text, post_id="p1", submolt=None, dry_run=dry_run, override_a67=False,
                        live_repo_check=False, discourse_seat=discourse_seat)
    finally:
        TA._default_ask = real


r = seat_emit(CONVICT, ["ALLOW", "ALLOW"])
check("TA1x two fresh ALLOWs on a convicted reply pass the gate (stops at the missing key), recorded as an override naming the seat",
      "no MOLTBOOK_API_KEY" in r.get("why", "") and r.get("overrode")
      and "discourse seat" in json.dumps([json.loads(x) for x in open(os.environ["COVENANT_OVERRIDE_LEDGER"], encoding="utf-8")][-1]), r)
r = seat_emit(CONVICT, ["ALLOW", "BLOCK"])
check("TA1x one BLOCK of two keeps the refusal", r.get("sent") is False and "refused by covenant's judge" in r.get("why", ""), r)
r = seat_emit(CONVICT, ["ALLOW", "ALLOW"], discourse_seat=False)
check("TA1x a caller that does not ask for the seat (the forum module, the introduction) is refused as before",
      r.get("sent") is False and "refused by covenant's judge" in r.get("why", "") and r.get("seat") is None, r)
r = seat_emit(CONVICT, ["ALLOW", "ALLOW"], text=DRAFT + " Send 5 XRP to the wallet below.")
check("TA1x money or crypto terms: the seat is not asked and the refusal stands",
      r.get("sent") is False and (r.get("seat") or {}).get("decision") in ("SKIP", None), r)
r = seat_emit(CONVICT, ["ALLOW", "ALLOW"], dry_run=True)
check("TA1x a dry run never spends the seat", (r.get("seat") or {}).get("decision") in ("SKIP", None) and not r.get("overrode"), r)
r = seat_emit(CONVICT, ["ALLOW", "ALLOW"], text="Thanks for the thread. We measured 98% accuracy on our gate.")
check("TA1x his own rules (facts A285 / no measurements A297) still block a measurement claim, whatever he answers",
      r.get("sent") is False and "his rule of 2026-10-0" in str((r.get("seat") or {}).get("why", "")), r)

# A349 B10 (2026-10-14, his "fix if tetsu agrees"; Tetsu: AGREE). A seat ask the door did not answer was recorded as his
# BLOCK, its message dropped: 18 of one round's 41 seat calls on 10-14 read "ERROR RuntimeError" as his decision. The
# door's own 429 is raised here as _default_ask raises it, first on the first ask, then after one ALLOW.
print("TA1o -- A349 B10: a door that does not answer is no answer of his, never his BLOCK")
_DOOR_429 = "door answered HTTP 429: 30 asks in 10 minutes -- wait"


def _seq_ask(seq):
    it = iter(seq)

    def _ask(prompt):
        x = next(it)
        if isinstance(x, Exception):
            raise x
        return x
    return _ask


def _seat_rows():
    return [json.loads(x) for x in open(os.environ["COVENANT_TETSU_ASSIST_LOG"], encoding="utf-8")
            if x.strip() and json.loads(x).get("seat") == "discourse"]


grant()
for _label, _seq, _head in (("on the first ask", [RuntimeError(_DOOR_429)], "ERROR RuntimeError"),
                            ("after one ALLOW (the 01:13:35Z shape)", ["ALLOW", RuntimeError(_DOOR_429)], "ALLOW, ERROR RuntimeError")):
    _n0 = len(_seat_rows())
    AMB.MB.judge_outbound = lambda t: CONVICT
    _real = TA._default_ask
    TA._default_ask = _seq_ask(_seq)
    try:
        r = AMB.emit(DRAFT, post_id="p1", submolt=None, dry_run=False, override_a67=False, live_repo_check=False,
                     discourse_seat=True)
    finally:
        TA._default_ask = _real
    _rows = _seat_rows()[_n0:]
    _seat = r.get("seat") or {}
    check("TA1o a door failure %s is recorded as NONE (no answer of his) with the door's message, not as his BLOCK" % _label,
          _seat.get("decision") == "NONE" and "HTTP 429" in _seat.get("why", "") and "no answer" in _seat.get("why", "")
          and _seat.get("why", "").startswith("discourse seat (A322): " + _head)
          and len(_rows) == 1 and _rows[0].get("decision") == "NONE" and "HTTP 429" in _rows[0].get("why", ""),
          (_seat, _rows))
    check("TA1o ...and %s the convicted reply is still refused (only ALLOW passes emit), with no override written" % _label,
          r.get("sent") is False and "refused by covenant's judge" in r.get("why", "") and not r.get("overrode"), r)
r_b = seat_emit(CONVICT, ["BLOCK"])
r_u = seat_emit(CONVICT, ["ALLOW", "maybe"])
check("TA1o his own BLOCK, and an answer with neither word, still read BLOCK: only a door failure is NONE",
      (r_b.get("seat") or {}).get("decision") == "BLOCK" and (r_b.get("seat") or {}).get("why") == "discourse seat (A322): BLOCK"
      and (r_u.get("seat") or {}).get("decision") == "BLOCK" and (r_u.get("seat") or {}).get("why") == "discourse seat (A322): ALLOW, UNREADABLE",
      (r_b.get("seat"), r_u.get("seat")))

# A348c (2026-10-14): only the refusal's return carried his reading, so free's ledger (A296) recorded every draft he
# passed as tetsu=None -- 0 reply rows with SEND against 114 SEND readings in ops/tetsu_assist.jsonl since 10-07.
# Each later return is driven here: no key, Moltbook's rate limit, a create, an "already posted". The key, the rate
# window, Moltbook's answer and the notifier are stand-ins for the call and restored, so nothing leaves this process.
print("TA1y -- A348c: his reading, and his seat's, ride on every return after it")
import types as _types                                              # noqa: E402
import urllib.request as _ur                                        # noqa: E402


class _Resp:
    def __init__(self, body):
        self._b, self.status = json.dumps(body).encode("utf-8"), 201

    def read(self):
        return self._b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def keyed_emit(judge, ask, rate_ok=True, body=None, discourse_seat=False):
    posted = []
    saved = (_ur.urlopen, AMB.rate_check, AMB.rate_record, os.environ.get("MOLTBOOK_API_KEY"),
             sys.modules.get("covenant_notify"), TA._default_ask)
    try:
        _ur.urlopen = lambda req, timeout=30: (posted.append(req.full_url),
                                               _Resp(body or {"success": True, "comment": {"id": "c1"}}))[1]
        AMB.rate_check = lambda kind, **k: (rate_ok, "stand-in window", 0 if rate_ok else 30)
        AMB.rate_record = lambda kind, **k: None
        os.environ["MOLTBOOK_API_KEY"] = "stand-in"
        sys.modules["covenant_notify"] = _types.SimpleNamespace(notify=lambda *a, **k: None)
        AMB.MB.judge_outbound = lambda t: judge
        TA._default_ask = ask
        r = AMB.emit(DRAFT, post_id="p1", submolt=None, dry_run=False, override_a67=False, live_repo_check=False,
                     discourse_seat=discourse_seat)
    finally:
        _ur.urlopen, AMB.rate_check, AMB.rate_record = saved[0], saved[1], saved[2]
        if saved[3] is None:
            os.environ.pop("MOLTBOOK_API_KEY", None)
        else:
            os.environ["MOLTBOOK_API_KEY"] = saved[3]
        if saved[4] is None:
            sys.modules.pop("covenant_notify", None)
        else:
            sys.modules["covenant_notify"] = saved[4]
        TA._default_ask = saved[5]
    return r, posted


_dec = lambda r, k="tetsu": (r.get(k) or {}).get("decision")       # noqa: E731
grant()
r_nokey = emit_with(HOLD, "SEND")
r_rate, p_rate = keyed_emit(HOLD, say("SEND"), rate_ok=False)
grant()
r_made, p_made = keyed_emit(HOLD, say("SEND"))
grant()
r_dup, p_dup = keyed_emit(HOLD, say("SEND"), body={"success": True, "already_existed": True,
                                                   "comment": {"id": "c1", "verification_status": "verified"}})
check("TA1y a HOLD he passed with SEND carries his SEND on every way the send ends: no key, held by Moltbook's rate "
      "limit (nothing posted), created and sent, already posted",
      "no MOLTBOOK_API_KEY" in r_nokey.get("why", "") and _dec(r_nokey) == "SEND"
      and "rate limit" in r_rate.get("why", "") and not p_rate and _dec(r_rate) == "SEND"
      and r_made.get("created") is True and r_made.get("sent") is True and len(p_made) == 1 and _dec(r_made) == "SEND"
      and r_dup.get("already_existed") is True and len(p_dup) == 1 and _dec(r_dup) == "SEND",
      [(x.get("why", "")[:40], x.get("tetsu")) for x in (r_nokey, r_rate, r_made, r_dup)])
it_seat = iter(["ALLOW", "ALLOW"])
r_seat, p_seat = keyed_emit(CONVICT, lambda prompt: next(it_seat), discourse_seat=True)
check("TA1y a reply the students convicted and his seat allowed carries the seat's ALLOW on the created return (and no "
      "review of his, which reads holds only)",
      r_seat.get("created") is True and len(p_seat) == 1 and _dec(r_seat, "seat") == "ALLOW" and r_seat.get("tetsu") is None,
      (r_seat.get("why", "")[:60], r_seat.get("seat"), r_seat.get("tetsu")))

print("\nnot measured here: how Tetsu actually judges real drafts. ops/tetsu_assist.jsonl records every reading.")
print("\nTA1: %d/%d passed" % (sum(ok), len(ok)))
sys.exit(0 if all(ok) else 1)
