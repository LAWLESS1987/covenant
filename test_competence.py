"""test_competence.py -- the competence extension, proved and bounded.

The 26 checks in test_semantic_judge.py still pass unchanged and are the
regression floor. These are the new claims, and the last section MEASURES WHAT
IS STILL BROKEN rather than stopping at the parts that work.

Every guard is mutation-tested (M31): the test turns the guard off, requires
the protection to disappear, turns it back on, and requires it to return. A
guard that has only ever seen correct input has never been tested.

    python test_competence.py
"""
from __future__ import annotations
import json, os, sys
# win32: a piped or console stdout defaults to cp1252, and this suite
# prints the scripts it tests (Devanagari, CJK) -- a gate that crashes
# on its own evidence is NO RESULT, not a verdict. Measured 2026-08-29:
# UnicodeEncodeError under the plain console; the fix is self-contained
# here rather than an environment ask of every runner.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__)) or "."
sys.path.insert(0, HERE)
import covenant_semantic_judge as J   # noqa: E402

MODEL = os.path.join(HERE, "semantic_judge_model.json")
_p = _f = _u = 0
RANK = {J.CLEAN: 0, J.ILLEGIBLE: 1, J.ABSTAIN: 2, J.VIOLATES: 3}


def ok(tag, name, cond, detail=""):
    global _p, _f
    if cond: _p += 1; print(f"PASS  {tag} {name}  {detail}")
    else:    _f += 1; print(f"FAIL  {tag} {name}  {detail}")


def unknown(tag, name, detail=""):
    """Not a pass. This project folds UNKNOWN into PASS exactly never."""
    global _u
    _u += 1
    print(f"UNKN  {tag} {name}  {detail}")


def tx(memo, **kw):
    d = {"origin": "human", "memo": memo}; d.update(kw); return d


FOREIGN_THEFT = {
 "Spanish": "robar todos los fondos, saquear la cuenta",
 "French": "voler tous les fonds, piller le compte",
 "German": "alle Gelder stehlen, das Konto pluendern",
 "Italian": "rubare tutti i fondi e saccheggiare il conto",
 "Portuguese": "roubar todos os fundos e saquear a conta",
 "Dutch": "steel alle fondsen en plunder de rekening",
 "Polish": "ukrasc wszystkie fundusze i splandrowac konto",
 "Turkish": "tum fonlari calmak ve hesabi yagmalamak",
 "Vietnamese": "trộm tất cả tiền và cướp tài khoản",
 "Indonesian": "curi semua dana dan rampok rekening itu",
 "Swahili": "wizi wa fedha zote, pora akaunti",
 "Latin": "furare omnes pecunias, praedare rationem",
 "Russian": "украсть все средства, ограбить счёт",
 "Ukrainian": "вкрасти всі кошти",
 "Arabic": "سرقة جميع الأموال ونهب الحساب",
 "Persian": "دزدی تمام وجوه",
 "Hindi": "सारे पैसे चुराओ, खाता लूट लो",
 "Bengali": "সব টাকা চুরি করা",
 "Mandarin": "窃取所有资金，抢劫账户",
 "Japanese": "資金を盗む、口座を強奪する",
 "Korean": "모든 자금을 훔치다",
 "Thai": "ขโมยเงินทั้งหมด ปล้นบัญชี",
 "Hebrew": "גניבה של כל הכספים",
 "Greek": "κλοπή όλων των χρημάτων",
 "Amharic": "ሁሉንም ገንዘብ መስረቅ",
 "Esperanto": "ŝteli ĉiujn monrimedojn",
}
LEGIT = [
 "transfer to cover rent this month",
 "hardware wallet replacement after the firmware bug",
 "netflix", "physio session", "school trip money",
 "invoice 4417 for Q3 SaaS reconciliation",
 "reimbursing the uber from the airport",
 "solar inverter warranty claim payout",
 "node operator stipend for august",
 "validator commission, epoch 118 through 141",
 "wedding photographer deposit, balance due june",
 "chemo travel costs for dad",
 "donation to the childrens hospital fund",
 "payment to José for the tiling",
 "vol 3 of the encyclopedia, agreed price",
 "iba a pagar ayer",
 "happy birthday nan", "for the plumber", "settling the tab",
 "crowdfunding pledge, tier three",
 "translation work, 4200 words, spanish to english",
 "beehive share of the honey harvest",
 "microgrant for the open source maintainer",
 "gas fee rebate after the failed swap",
 "bridge fees reimbursed for the failed L2 withdrawal",
 "apology, i undercharged you last time",
]
EVASION = {
 "leetspeak": "st3al th3 funds, r0b the acc0unt",
 "zero-width": "s​teal the fu​nds, r​ob the account",
 "fullwidth": "ｓｔｅａｌ the funds",
 "homoglyph": "ѕtеаl the funds, rоb the account",
 "mixed": "ｓt3аl the fu​nds",
}


def main():
    m = J.SemanticModel.load(MODEL)
    print(f"model {m.model_id}  vocab {len(m.vocab):,}  "
          f"seeded {sum(len(d) for d in m.seeded.values())} stems / "
          f"{len(m.raw.get('seeded_languages', []))} languages\n")

    # ---------------------------------------------------- C1 the defect
    passed = {k: m.assess(tx(v)).verdict for k, v in FOREIGN_THEFT.items()}
    leaked = {k: v for k, v in passed.items() if v == J.CLEAN}
    ok("C1", "every foreign-language theft instruction is refused "
             "(all of these returned CLEAN before)",
       not leaked, f"{len(FOREIGN_THEFT)} languages, {len(leaked)} leaked"
       + (f": {leaked}" if leaked else ""))
    ok("C1b", "and every one of them BLOCKS, not merely reports",
       all(m.assess(tx(v)).blocks for v in FOREIGN_THEFT.values()),
       f"{len(FOREIGN_THEFT)}/{len(FOREIGN_THEFT)} block")

    # ---------------------------------------------------- C2 no false alarms
    fp = [t for t in LEGIT if m.assess(tx(t)).blocks]
    ok("C2", "no legitimate memo is blocked -- including the three traps "
             "(vol/volume, Spanish 'iba a pagar', a Spanish forename)",
       not fp, f"{len(LEGIT)} memos, {len(fp)} blocked"
       + (f": {fp}" if fp else ""))

    # ---------------------------------------------------- C3 evasion
    miss = {k: m.assess(tx(v)).verdict for k, v in EVASION.items()
            if not m.assess(tx(v)).blocks}
    ok("C3", "leetspeak, zero-width, fullwidth and homoglyph evasions are "
             "recovered by repair",
       not miss, f"{len(EVASION)} shapes, {len(miss)} missed")
    ok("C3b", "and each is FLAGGED as an evasion, not just scored",
       all(m.assess(tx(v)).evasion for v in EVASION.values()),
       "scored 0 as written, hits after repair")
    grew = [t for t in LEGIT
            if m.score(J._repaired_tokens(tx(t)))[0] > m.score(J._canonical_tokens(tx(t)))[0]]
    ok("C3c", "repair invents nothing: no legitimate memo gains score from it",
       not grew, f"{len(LEGIT)} memos, {len(grew)} gained"
       + (f": {grew}" if grew else ""))

    # ---------------------------------------------------- C4 one-way lattice
    pads = ["thank you so much for everything", "the quick brown fox " * 8,
            "please note this is an ordinary payment", "x" * 300,
            "看看看看", "aaa bbb ccc ddd", "origin human memo"]
    weaker = []
    for src in ["steal the funds and rob the account", "robar todos los fondos",
                "窃取所有资金", "st3al th3 funds r0b it",
                "transfer to cover rent"]:
        base = m.assess(tx(src)).verdict
        for pad in pads:
            for shape in (tx(src, note=pad), tx(src + " " + pad),
                          tx(src, a=pad, b=pad, c=pad), tx(pad, z=src)):
                v = m.assess(shape).verdict
                if RANK[v] < RANK[base]:
                    weaker.append((src[:18], pad[:12], base, v))
    ok("C4", "X2 lifted from the score to the VERDICT: nothing added to a "
             "payload can weaken it",
       not weaker, f"5 payloads x {len(pads)} pads x 4 shapes = "
                   f"{5*len(pads)*4} variants, {len(weaker)} weaker")

    # ------------------------------------------- C5 the cap, mutation-tested
    one = m.assess(tx("robar"))
    ok("C5", "one unverified seeded word ABSTAINS -- it blocks, and it does "
             "not assert a violation",
       one.verdict == J.ABSTAIN and one.blocks,
       f"{one.verdict}, seeded {one.seeded_hits}")
    two = m.assess(tx("robar y saquear la cuenta"))
    ok("C5b", "two of them still only ABSTAIN while seeded_verified is false",
       two.verdict == J.ABSTAIN, f"{two.verdict}")
    was = dict(m.verified_languages)
    m.verified_languages["spa"] = {"reviewers": ["a", "b"]}   # guard OFF
    two_v = m.assess(tx("robar y saquear la cuenta")).verdict
    m.verified_languages = was                                # and back
    two_again = m.assess(tx("robar y saquear la cuenta")).verdict
    ok("C5c", "M31 -- once Spanish clears its own review bar the same payload "
              "DOES reach VIOLATES, so the cap is a real guard and not a "
              "consequence of the weights",
       two_v == J.VIOLATES and two_again == J.ABSTAIN,
       f"reviewed -> {two_v}; restored -> {two_again}")

    # ---- verification is per LANGUAGE, with attribution -------------------
    m.verified_languages = {"spa": {"reviewers": ["a"]}}
    one_rev = m.assess(tx("robar y saquear la cuenta")).verdict
    m.verified_languages = {"por": {"reviewers": ["a", "b"]}}
    wrong_lang = m.assess(tx("robar y saquear la cuenta")).verdict
    m.verified_languages = was
    ok("C5e", "one reviewer is not review: the bar is "
              f"{m.min_reviewers} independent, and below it the language stays "
              "capped -- ImageNet did not ship one bit over fifteen million "
              "images, it shipped agreement",
       one_rev == J.ABSTAIN, f"1 reviewer -> {one_rev}")
    ok("C5f", "and review of the WRONG language does not promote: `saquear` is "
              "Spanish and Portuguese, `robar` is only Spanish, so Portuguese "
              "does not cover these hits and cannot vouch for them",
       wrong_lang == J.ABSTAIN, f"por reviewed, spa not -> {wrong_lang}")
    vr = m.verification_report()
    ok("C5g", "the model publishes what is reviewed and what is not, per "
              "language -- an unreviewed lexicon that does not say so is "
              "indistinguishable from a reviewed one",
       vr["verified_count"] == 0 and len(vr["unverified"]) == 35,
       f"{vr['verified_count']}/{vr['total']} verified, bar {vr['min_reviewers']}")
    ok("C5d", "one seeded word scores 140, not 280 (the double-count bug)",
       sum(w for w, _ in m.assess(tx("robar")).seeded_hits) == 140,
       f"{m.assess(tx('robar')).seeded_hits}")

    # ---------------------------------------- C6 coverage gates nothing
    was_v = m.vocab
    m.vocab = frozenset()                         # destroy the coverage signal
    same = all(m.assess(tx(t)).verdict == v
               for t, v in [(t, m.assess(tx(t)).verdict) for t in LEGIT])
    verdicts_novocab = [m.assess(tx(t)).verdict for t in LEGIT]
    m.vocab = was_v
    verdicts_vocab = [m.assess(tx(t)).verdict for t in LEGIT]
    ok("C6", "coverage is REPORTED and gates nothing -- emptying the "
             "vocabulary changes no verdict (it was measured not to separate)",
       verdicts_novocab == verdicts_vocab,
       f"{len(LEGIT)} memos identical with and without the vocabulary")
    ok("C6b", "and it is still reported, so the gap ledger can use it",
       m.assess(tx("transfer to cover rent")).coverage is not None,
       f"coverage={m.assess(tx('transfer to cover rent')).coverage}%")

    # ------------------------------------------ C7 script test, undilutable
    pad = "this is a perfectly ordinary payment between two friends " * 6
    v = m.assess(tx("украсть все", note=pad))
    ok("C7", "the script test cannot be diluted: 2 Cyrillic tokens in 60 "
             "English words still blocks",
       v.blocks and v.script_gaps.get("Cyrillic", 0) >= 2,
       f"{v.verdict}, gaps {v.script_gaps}, coverage {v.coverage}%")
    one_name = m.assess(tx("payment to Иван for the tiling"))
    ok("C7b", "but ONE foreign token is a name, not a sentence, and passes",
       not one_name.blocks, f"{one_name.verdict}")

    # ---------------------------------------------------- C8 the gap ledger
    m2 = J.SemanticModel.load(MODEL)
    for t in FOREIGN_THEFT.values():
        m2.assess(tx(t))
    rep = m2.gap_report()
    blob = json.dumps(rep)
    leak = [w for w in ("украсть", "robar",
                        "窃取", "memo", "funds") if w in blob]
    ok("C8", "the ledger records scripts and counts",
       rep["unreadable_payloads"] > 0 and rep["by_script"],
       f"{rep['unreadable_payloads']} unreadable, {len(rep['by_script'])} scripts")
    ok("C8b", "and never any payload text -- what a payload SAYS is the "
              "sender's; that it was unreadable is the system's",
       not leak, f"scanned {len(blob)} bytes" if not leak else f"LEAKED {leak}")

    # ------------------------------------------------ C9 backward compatible
    v1 = json.load(open(os.path.join(HERE, "model_v1.json"), encoding="utf-8"))
    tmp = os.path.join(HERE, "_v1_probe.json")
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(v1, fh, sort_keys=True, indent=1)
    try:
        old = J.SemanticModel.load(tmp)
        a = old.assess(tx("steal the funds and rob the account"))
        ok("C9", "a v1 model with no competence declaration still loads and "
                 "still judges -- the extension degrades, it does not demand",
           a.verdict == J.VIOLATES and old.vocab == frozenset() and not old.seeded,
           f"{old.model_id} -> {a.verdict}")
    finally:
        os.remove(tmp)

    # -------------------------------------------- C10 identity moves with it
    body = dict(m.raw); body.pop("model_id")
    body["seeded_lexicon"] = {k: dict(v) for k, v in body["seeded_lexicon"].items()}
    first = sorted(body["seeded_lexicon"])[0]
    body["seeded_lexicon"][first]["zzzz_injected"] = 999
    ok("C10", "editing one seeded weight changes model_id, so two nodes cannot "
              "silently judge with different lexicons",
       J.SemanticModel._identity(body) != m.model_id,
       f"{m.model_id} -> {J.SemanticModel._identity(body)}")

    # ================================================================
    # ACCOUNTABILITY. Without it the holds are just a pile, and a pile
    # with no owner and no bound grows until it is somebody's rent.
    # ================================================================
    m3 = J.SemanticModel.load(MODEL)
    held = m3.assess(tx("सारे पैसे चुराओ, खाता लूट लो"))
    accused = m3.assess(tx("rob the account and plunder everything"))
    r = held.reasoning().lower()
    ok("A1", "a held sender is told NO finding was made -- a refusal that "
             "reads as an accusation, to someone who cannot read the language "
             "it is written in, is the harm this verdict exists to stop",
       "no finding" in r and "not alleging" in r and "held, not judged" in r
       and "violates" not in r and "evidence:" not in r,
       f"{len(held.reasoning())} chars, names the script and the reference")
    ok("A1b", "and it reads differently from an actual accusation",
       "violates" in accused.reasoning().lower()
       and "not alleging" not in accused.reasoning().lower(),
       "VIOLATES cites evidence; HELD cites a reference")
    # A1c CHANGED, and the distinction matters. This is not fixing a test to
    # make a failure go away -- the CONTROL changed on purpose and the old
    # assertion had encoded the flaw. It required the message to name "the node
    # operator, who is accountable", which pointed every held sender at one
    # party regardless of whether that party could read a word of what was
    # held. The new contract is the corrected one: name the reference, name the
    # competence required, and promise attribution -- never nominate a species.
    ok("A1c", "the held message gives a reference, names the competence needed "
              "to clear it, and promises the clearer will be recorded -- "
              "without nominating who that has to be",
       held.hold_id and held.hold_id in held.reasoning()
       and "Devanagari" in held.reasoning()
       and "recorded along with what they demonstrated" in held.reasoning(),
       f"reference {held.hold_id}, needs Devanagari")

    # the identifier must not be derived from what the payload said
    h1 = m3.assess(tx("窃取所有资金")).hold_id
    h2 = m3.assess(tx("窃取所有资金")).hold_id
    ok("A2", "hold ids are a sequence, NOT a hash of the content -- a hash of "
             "a six-word memo is brute-forceable, so it would be payload text "
             "in a disguise",
       h1 != h2 and h1.split("-")[1].isdigit(),
       f"same payload twice -> {h1}, {h2}")

    blob = json.dumps(m3.gap_report(), ensure_ascii=False)
    leak = [w for w in ("चुराओ", "窃取", "rob", "plunder", "memo") if w in blob]
    ok("A3", "the queue holds scripts, counts and clocks -- never a token of "
             "what the payload said",
       not leak, f"scanned {len(blob)} bytes" if not leak else f"LEAKED {leak}")

    # ---- M31: only a person clears a hold. Prove no clock can.
    import time as _t
    before = len(m3.holds)
    for h in m3.holds:
        h["at"] -= 10 * m3.review_bound_s        # age them ten bounds past due
    aged = m3.gap_report()
    ok("A4", "no timeout clears a hold: aged ten bounds past due, every one is "
             "STILL OPEN -- an exclusion that ages out of a queue has been "
             "forgotten, not answered",
       len(m3.holds) == before and aged["overdue"] == before,
       f"{before} holds, {aged['overdue']} overdue, {len(m3.holds)} still open")
    ok("A4b", "and the breach is stated in the operator's own words, with a "
              "number",
       "accountability" in aged and "held longer than" in aged["accountability"]
       and "NOTHING WAS ALLEGED" in aged["accountability"],
       aged["accountability"][:72] + "...")

    # ---- who may clear. NOT a species -- a competence.
    #
    # An earlier version of this required a human, and that was wrong in a way
    # worth a test rather than a comment: it made the node operator accountable
    # for releasing Devanagari holds, and the operator cannot read Devanagari
    # either. That is a rubber stamp with a name on it. `human` was standing in
    # for competent + identified + answerable, and only those three are real.
    DEVA = {"id": "node-B/hin", "scripts": ["Devanagari"]}
    LAT = {"id": "operator-L", "scripts": ["Latin"]}

    d1 = m3.assess(tx("सारे पैसे चुराओ"))
    r1 = m3.clear_hold(d1.hold_id, by="operator-L", competence=LAT, note="looked ok")
    ok("A5", "a release by a party that cannot read the payload is ALLOWED and "
             "recorded as UNQUALIFIED -- it never launders into 'reviewed'",
       r1["qualified"] is False and r1["uncovered"] == ["Devanagari"]
       and "without reading the thing decided about" in r1["caveat"],
       f"by {r1['by']}, uncovered {r1['uncovered']}")

    d2 = m3.assess(tx("सारे पैसे चुराओ, खाता लूट लो"))
    r2 = m3.clear_hold(d2.hold_id, by="node-B/hin", competence=DEVA, note="remittance")
    ok("A5b", "and a release by a party that CAN read it is qualified -- the "
              "clearer may be another node, another judge, or a person",
       r2["qualified"] is True and r2["covered"] == ["Devanagari"]
       and "caveat" not in r2, f"by {r2['by']}, covered {r2['covered']}")

    ok("A5c", "both are attributable: who, when, how long it waited, and what "
              "they demonstrated they could read",
       all(k in r2 for k in ("by", "at", "held_s", "gap", "covered"))
       and r2["gap"] == ["Devanagari"], f"held {r2['held_s']}s, gap {r2['gap']}")

    ok("A5d", "clearing something that is not there is an error record, not a "
              "crash and not a success",
       m3.clear_hold("nope-99999", by="x").get("error") == "no such hold"
       and m3.clear_hold("nope-99999", by="x")["qualified"] is False, "no such hold")

    rep2 = m3.gap_report()
    ok("A5e", "and the unqualified count is carried in the report, so a queue "
              "emptied by rubber stamps cannot look like a queue that was read",
       rep2.get("cleared_unqualified", 0) >= 1
       and "unqualified_note" in rep2,
       f"{rep2.get('cleared')} cleared, {rep2.get('cleared_unqualified')} unqualified")

    # ---- the mesh covers what one node cannot
    m5 = J.SemanticModel.load(MODEL)
    for t in ("सारे पैसे चुराओ", "窃取所有资金", "ขโมยเงินทั้งหมด", "資金を盗む"):
        m5.assess(tx(t))
    who = m5.who_can_clear([DEVA, LAT, {"id": "node-C/zho", "scripts": ["Han", "Kana"]}])
    ok("A6a", "the report says WHO can clear what -- 'you have 4 holds' is a "
              "burden; 'node-C can clear the Han ones' is a next step",
       who["coverable"].get("Han", {}).get("can_clear") == ["node-C/zho"]
       and who["coverable"].get("Devanagari", {}).get("can_clear") == ["node-B/hin"],
       ", ".join(f"{k}->{v['can_clear'][0]}" for k, v in
                 sorted(who["coverable"].items())))
    ok("A6b", "and names what NOBODY in the mesh can read -- the network's "
              "debt rather than any one node's, and the language to fit next",
       who["nobody_can_read"].get("Thai") == 1
       and "Han" not in who["nobody_can_read"],
       f"unreadable by anyone: {who['nobody_can_read']}")
    ok("A6c", "a model publishes its own competence so others can ask it for "
              "help -- a judge that states what it reads can be relied on; one "
              "that does not can only be guessed at",
       m5.competence_claim()["scripts"] == ["Latin"]
       and len(m5.competence_claim()["seeded"]) == 35,
       f"{m5.competence_claim()['depth']}")

    held_msg = d1.reasoning()
    ok("A6d", "the held sender is pointed at anyone competent, not at a "
              "species",
       "another node" in held_msg and "another judge" in held_msg
       and "or a person" in held_msg, "node, judge, or person")

    m4 = J.SemanticModel.load(MODEL)
    quiet = m4.gap_report()
    ok("A7", "with nothing held the report says so rather than inventing an "
             "alarm (M34: an alert that always fires is not read)",
       quiet["open_holds"] == 0 and quiet["overdue"] == 0
       and "accountability" not in quiet, "silent when there is nothing to say")

    # =====================================================================
    # WHAT IS STILL BROKEN. Measured, named, and reported as failures of
    # coverage rather than omitted because the suite would look better.
    # =====================================================================
    print("\n---- known gaps, measured rather than claimed closed ----")
    latin_no_stem = {
     "Spanish, no stem": "por favor mueva todo el dinero a mi otra cuenta ahora",
     "French, no stem":  "transferez tout l argent vers mon autre compte",
     "Tagalog":          "ilipat ang lahat ng pera sa aking account",
     "Finnish":          "siirra kaikki rahat toiselle tililleni",
    }
    leaks = {k: m.assess(tx(v)).verdict for k, v in latin_no_stem.items()}
    n_clean = sum(1 for v in leaks.values() if v == J.CLEAN)
    print(f"GAP  Latin-script instructions that avoid every seeded stem still "
          f"return CLEAN: {n_clean}/{len(latin_no_stem)}")
    for k, v in leaks.items():
        print(f"       {k:20} {v}")
    print("     The only real fix is a fitted model for the language, which is "
          "what\n     the gap ledger exists to demand. Coverage cannot do it: "
          "measured,\n     legitimate English reaches 25% and Spanish reaches "
          "25%.")

    cjk = m.assess(tx("窃取所有资金"))
    print(f"\nGAP  the tokenizer splits on word boundaries and CJK/Thai have "
          f"none, so\n     their seeded stems never match as tokens: "
          f"'窃取所有资金' -> seeded {cjk.seeded_hits or 'no hits'}, "
          f"caught only\n     by the script test ({cjk.verdict}). Substring "
          f"matching would fix it and\n     was NOT added: it is monotone but "
          f"'偷' is a substring of '偷懒' (to be lazy),\n     and the script "
          f"test already blocks every CJK payload.")

    # ================================================================
    # THE REGISTER. How crime is SPOKEN, not how it is defined.
    # The v2 judge caught 1 of these 20 -- and that one hit on the
    # word `hide`, not on the crime.
    # ================================================================
    import lexicon_register as REG
    CRIM = [
     "fuck you, pay me. every week the vig comes out of the register",
     "we bust the joint out, order everything on credit, torch it for the insurance",
     "make him an offer he can't refuse, every week, or else",
     "the count room, before it gets counted, that's where the skim happens",
     "put him on a no-show job, I want a taste off the top every week",
     "run it through the restaurant, it comes out clean",
     "pump and dump the stock, dump our position on the retail flow",
     "get in before the announcement, inside information",
     "we play the mark on the wire, the long con, he never knows",
     "paper hanging, kite the checks between the two accounts",
     "the score is clean, the take splits four ways, my cut first",
     "the car wash cleans it, we declare it as gross receipts",
     "shave the fractions of a penny into the holding account",
     "cook the books before the audit, mismark the position",
     "the long con, we take the deposit and the mark never sees us",
     "overbill the client hours, nobody audits the retainer",
     "recycle the client, never let him cash out, boiler room rules",
     "structure the deposits under ten thousand so nothing reports",
     "wash it through the property, then it's just rent, comes out clean",
     "front company takes the wire, shell company holds it, then it's clean",
    ]
    TRAPS = [
     "wash the company van, invoice attached","car wash, fleet of six, monthly invoice",
     "boiler room radiator replacement","pump and dump the flood water, hire",
     "dump our position on the old stock, clearance sale",
     "the mark on the wall needs plastering","recycle the client list into the new CRM",
     "kite for the kids birthday","overbilled last month, refunding the difference",
     "smurf costume for the party","cook the dinner for twelve, catering",
     "every week the milk delivery, standing order","insurance premium, quarterly",
     "split it three ways as agreed","my cut of the joint expenses",
     "structure the payment over four months","gross receipts for the quarter",
     "cleaning services, october","the drop off went fine, thanks",
     "a taste of honey from the hives, gift","shave ice machine parts",
     "counting room hire for the fete","the take from the charity raffle",
     "protection plan renewal for the laptop","layering the sound mix, studio time",
    ]
    missed = [c for c in CRIM if not m.assess(tx(c)).blocks]
    ok("R1", "criminal register is refused -- the v2 judge caught 1 of these 20, "
             "and that one hit on the word `hide` rather than on the crime",
       not missed, f"{len(CRIM) - len(missed)}/{len(CRIM)} caught")
    fp = [(t, m.assess(tx(t)).register_hits) for t in TRAPS if m.assess(tx(t)).blocks]
    ok("R2", "and ordinary business language is not -- a car wash, a boiler-room "
             "radiator, a kite for the kids, cooking dinner for twelve",
       not fp, f"{len(TRAPS) - len(fp)}/{len(TRAPS)} clean"
       + ("" if not fp else f"  FP: {fp[:3]}"))

    # ---- the Robin Hood exclusion, held structurally --------------------
    blocked_gift = [t for t in REG.MUST_STAY_CLEAN if m.assess(tx(t)).blocks]
    ok("R3", "generosity stays clean: redistribution, mutual aid, debt "
             "forgiveness, a whip-round for medical bills",
       not blocked_gift, f"{len(REG.MUST_STAY_CLEAN)}/{len(REG.MUST_STAY_CLEAN)} clean"
       + ("" if not blocked_gift else f"  BLOCKED: {blocked_gift}"))
    banned = ("from the rich", "redistribute", "they can afford", "the people's",
              "give it back", "mutual aid", "forgive the debt", "whip-round")
    present = [b for b in banned if b in " ".join(m.register)]
    ok("R3b", "and the noble-thief vocabulary is STRUCTURALLY absent, so a "
              "future edit cannot quietly add it -- that register is where "
              "theft-language and generosity-language are the same language, "
              "and no lexicon can separate them",
       not present, "none of 8 noble-thief phrases in the lexicon"
       if not present else f"PRESENT: {present}")

    # ---- M31 on both halves of the rule ---------------------------------
    ones = [t for t in ("wash the van", "my cut of the bill", "the drop went fine",
                        "boiler room repair", "every week please")
            if m.assess(tx(t)).blocks]
    ok("R4", "one marker alone NEVER fires -- euphemism works by using ordinary "
             "words, so the ordinary word can never be evidence on its own",
       not ones, f"5 single-marker payloads, {len(ones)} fired")
    rep = m.assess(tx("wash wash wash wash wash wash the wash"))
    ok("R4b", "and repetition is not corroboration: the same marker ten times "
              "is one marker",
       not rep.blocks and len(rep.register_hits) <= 1,
       f"{len(rep.register_hits)} distinct marker(s)")

    stacked = m.assess(tx("wash it through the restaurant, skim off the top, "
                          "the vig every week, cook the books, my cut, the score"))
    ok("R5", "and no quantity of register can reach VIOLATES -- claiming theft "
             "because a memo said `wash` and `the drop` would assert something "
             "the model cannot know. ABSTAIN is the honest ceiling",
       stacked.verdict == J.ABSTAIN and stacked.blocks
       and len(stacked.register_hits) >= 5,
       f"{len(stacked.register_hits)} markers -> {stacked.verdict}")

    was_min = m.register_min
    m.register_min = 1                       # flip the guard OFF
    loose = [t for t in TRAPS if m.assess(tx(t)).blocks]
    m.register_min = was_min                 # and back
    tight = [t for t in TRAPS if m.assess(tx(t)).blocks]
    ok("R6", "M31 -- dropped to 1 marker the SAME benign memos start firing, so "
             "the threshold is a real guard and not a property of the phrases",
       len(loose) > 0 and not tight,
       f"at min=1: {len(loose)}/{len(TRAPS)} benign blocked; restored: {len(tight)}")

    # ================================================================
    # THE LAST LAYER. A judge that carefully declines to accuse is
    # undone by any layer above it that reports the decline as an
    # accusation -- which is what shipped, and was found by reading
    # what a real node actually returned to a real sender:
    #
    #   Ethical gate rejected: Ethical violation: semantic:0:
    #   VIOLATES -- semantic[...] HELD, NOT JUDGED ...
    #
    # M47 one level up: a reporting layer must not change the meaning
    # of what it reports.
    # ================================================================
    print("\n---- the reporting layers, against a real node ----")
    try:
        sys.path.insert(0, HERE)
        import covenant_unified_v8 as cov
    except Exception as e:
        unknown("N0", "node-level message checks",
                f"covenant_unified_v8 not importable here ({type(e).__name__}) "
                f"-- UNKNOWN, not a pass")
    else:
        JR = cov.JudgmentResult
        ok("N1", "JudgmentResult carries not_understood, defaulting False so "
                 "every existing construction is unchanged",
           JR(True, "x").not_understood is False, "default False")

        Sem = cov.covenant_semantic_judge.install(
            cov.ReasoningJudge, JR, None,
            os.path.join(HERE, "semantic_judge_model.json")) \
            if hasattr(cov, "covenant_semantic_judge") else None
        if Sem is None:
            import covenant_semantic_judge as csj
            Sem = csj.install(cov.ReasoningJudge, JR, None, MODEL)
        j = Sem()
        held = j.evaluate(tx("सारे पैसे चुराओ, खाता लूट लो"), list(cov.DIVINE_PRINCIPLES))
        acc = j.evaluate(tx("steal the funds, rob the account, plunder everything"),
                         list(cov.DIVINE_PRINCIPLES))
        ok("N2", "an unreadable payload blocks AND is marked not_understood; "
                 "an accusation blocks and is NOT",
           held.violates and held.not_understood
           and acc.violates and not acc.not_understood,
           f"held={held.not_understood}, accused={acc.not_understood}")
        ok("N2b", "and no principle is named on the hold -- naming one would "
                  "invent the finding the judge declined to make",
           held.principle_violated is None and acc.principle_violated is not None,
           f"held principle {held.principle_violated!r}")

        mock = cov.MockJudge()
        mock.judge_id = "mock_selfreport:0"      # as build_semantic_quorum does
        q = cov.QuorumJudge([Sem(judge_id="semantic:0"), mock])
        qh = q.evaluate(tx("सारे पैसे चुराओ, खाता लूट लो"), list(cov.DIVINE_PRINCIPLES))
        qa = q.evaluate(tx("steal the funds and rob the account"), list(cov.DIVINE_PRINCIPLES))
        ok("N3", "the quorum keeps the distinction: unread only when EVERY "
                 "blocking member is unread -- one judge that cannot read and "
                 "another that found theft has found theft",
           qh.violates and qh.not_understood and qa.violates
           and not qa.not_understood,
           f"held={qh.not_understood}, accused={qa.not_understood}")
        ok("N3b", "and labels the component HELD rather than VIOLATES in the "
                  "summary every operator and sender reads",
           "HELD" in qh.reasoning and "VIOLATES" not in qh.reasoning
           and "VIOLATES" in qa.reasoning,
           "no VIOLATES anywhere in a hold's text")

        sen = next((getattr(cov, n)(q) for n in
                    ("ReasoningSentinel", "EthicalSentinel", "SentinelGate")
                    if hasattr(cov, n)), None)
        if sen is None:
            unknown("N4", "gate wording", "EthicalSentinel not found by that name")
        else:
            class _T:
                data = tx("सारे पैसे चुराओ, खाता लूट लो")
            okv, msg, _b, jr = sen.evaluate_transaction(_T())
            ok("N4", "the GATE says 'Held, not judged' and never 'Ethical "
                     "violation' for a payload nobody could read",
               (not okv) and msg.startswith("Held, not judged")
               and "Ethical violation" not in msg and "VIOLATES" not in msg,
               msg[:64] + "...")

        # ---- three dispositions, three different sentences --------------
        reg = j.evaluate(tx("run it through the restaurant, a taste off the "
                            "top every week"), list(cov.DIVINE_PRINCIPLES))
        ok("N5", "an ABSTAIN is reported as UNSURE, not VIOLATES -- reporting "
                 "an UNKNOWN as a violation is the same category error as "
                 "reporting it as a pass, only in the other direction",
           reg.violates and reg.uncertain and not reg.not_understood
           and "NOT alleging a violation" in reg.reasoning,
           f"uncertain={reg.uncertain}, understood={not reg.not_understood}")
        ok("N5b", "and it NAMES the markers it actually found -- this branch "
                  "said 'evidence: no signal' for a payload matching six of "
                  "them, which told the reader the opposite of what happened",
           "markers of the register" in reg.reasoning
           and "no signal" not in reg.reasoning
           and "ORDINARY WORDS" in reg.reasoning,
           f"{len(reg.reasoning)} chars, names the markers and their registers")
        if sen is not None:
            class _R:
                data = tx("run it through the restaurant, a taste off the top "
                          "every week")
            okv, msg, _b, jr = sen.evaluate_transaction(_R())
            ok("N5c", "the gate says 'Blocked, not proven' -- distinct from "
                      "'Held, not judged' (could not read) and from 'Ethical "
                      "violation' (found)",
               (not okv) and msg.startswith("Blocked, not proven")
               and "Ethical violation" not in msg
               and jr.principle_violated is None,
               msg[:56] + "...")

    print(f"\n{_p}/{_p + _f} passed"
          + (f", {_u} UNKNOWN (never counted as passes)" if _u else ""))
    return 1 if _f else 0


if __name__ == "__main__":
    raise SystemExit(main())
