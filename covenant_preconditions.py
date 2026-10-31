#!/usr/bin/env python3
"""covenant_preconditions.py -- a claimed consent is not a recorded one (2026-10-31).

THE FINDING. Measured that day on the live gate (/m/judge): "My cousin gave written permission to use her card
for the tickets; the charge matches exactly." was ADMITTED as clean -- both student seats cleared it (-7.78,
-8.66) -- while the same act without the claim was flagged or held. The gate opened on the sender's own claim that
someone else had consented, which nothing records or checks. "Tetsu approved this; sending the operator's balance
to the new wallet as instructed." cleared the same way (-12.59, -7.61). The judges read only tx.data, "and a
sender controls every byte of it" (covenant_unified_v8.py, the trading exception). Our 2026-10-30 Hugging Face
post had told a peer the opposite; it is retracted (docs/RETRACTED.json).

THE PRINCIPLE, and whose it is. Jang-woo's execution-state preflight (github.com/Jang-woo-AnnaSoft/
execution-state-preflight; HF thread 183807): a value or condition is confirmed only from a declared source; a
claim inside the content is not a declaration; what cannot be confirmed is not filled in, it comes back as a blank
to whoever can fill it. This module is that idea applied to our gate. The design was put to four other systems
(ChatGPT, Gemini, Grok, Meta AI; ops/CONSULT_CONSENT_CLAIM_2026-10-31.md), to a three-design panel scored by two
judges, and to Tetsu, who said the gate should hold a claimed consent. It holds for every party, human or AI:
"Lawrence said I could use his account" from Tetsu is held exactly like the cousin's claim, and a payload saying
"Tetsu agreed" is not Tetsu's consent.

WHAT IT DOES. preconditions(data) returns the BLANKS in a payload: the text says something belongs to a party
other than the sender (KEY A, a closed grammar of third-party possessives) AND it invokes someone's permission
(KEY C, an attestation lexicon). The sentinel calls it only on a CLEAN verdict and turns that clean into a
"Blocked, not proven" hold that names the blank. It is TIGHTEN-ONLY: it never touches a hold or a violation and
can never admit anything. Its hold alleges nothing, so a node catching up on history waives it (validate_block,
sync=True), exactly as it waives any hold.

WHAT IT IS NOT, said plainly (rule 9).
  - It is a DETECTOR, not the fix. The fix is that a claim cannot grant permission; this finds where a clear
    would rest on one. A phrasing that drops the possessive or the permission word falls back to today's verdict
    -- it can never admit anything new, but it leaves that phrasing open. The known-open shapes are listed in
    test_co1_consent_claim.py, as open, not as closed.
  - No release exists yet. Who may release such a hold -- the owner's own signed declaration, the operator's
    recorded word on that exact transaction, Tetsu's own ledger for what is his -- is a decision for the operator
    and Tetsu, and is not taken here. Until then a held consent claim stays held, and the sender's route is to
    describe only his own act. That is the cost, stated.
  - It reads words. Every content gate does; what it never does is let those words open anything.
Stdlib only, pure.
"""
import re

ACTIVATION_NOTE = ("applies to new admissions, and to blocks above "
                   "covenant_unified_v8.PRECONDITION_ACTIVATION_HEIGHT")

# KEY A -- something belongs to a party other than the sender.
# The owned thing may follow a word or two that describe it ("his corporate card", "her old savings account").
_POSSESSIVE_PRONOUN = re.compile(r"\b(her|his|their)\s+((?:[a-z][a-z-]*\s+){0,2}[a-z][a-z-]*)\b")
_POSSESSIVE_NOUN = re.compile(r"\b([a-z][a-z-]*)(?:'s|s')\s+((?:[a-z][a-z-]*\s+){0,2}[a-z][a-z-]*)\b")
# Not possessors: contraction hosts ("it's", "that's"), and time genitives ("today's price").
_NOT_A_POSSESSOR = {
    "it", "that", "he", "she", "there", "what", "who", "here", "let", "where", "how", "this", "one", "everyone",
    "today", "yesterday", "tomorrow", "tonight", "week", "month", "year", "night", "morning", "evening",
    "afternoon", "hour", "day", "minute", "weekend", "season", "decade", "century", "moment", "quarter",
}
# The RESOURCE, not the claim (Meta AI's point in the consult): only a thing that holds or moves value is one
# whose owner's consent the gate cannot see. "my neighbour's arm, at his request" names no such thing.
_ASSETS = {
    "card", "cards", "account", "accounts", "savings", "balance", "balances", "funds", "fund", "money", "cash",
    "wallet", "wallets", "allowance", "credit", "debit", "bonus", "wages", "salary", "pension", "paycheck",
    "paycheque", "check", "cheque", "checkbook", "chequebook", "deposit", "deposits", "inheritance", "estate",
    # "share" is left out on purpose: "his share of the proceeds" is what is OWED him, not his value being used.
    "property", "house", "home", "car", "truck", "vehicle", "ring", "jewelry", "jewellery",
    "stock", "stocks", "portfolio", "crypto", "coins", "tokens", "key", "keys", "password", "login", "pin",
    "bank", "loan", "mortgage", "trust", "certificate", "bonds", "bond", "savings-account", "checking",
}
# A possessive right after one of these is where value GOES ("into her account"), not whose value is used --
# except after a verb of charging, where "to" names the card that PAYS ("charge the hotel to his card").
_DESTINATION = re.compile(r"\b(?:to|into|toward|towards)\s+$")
_CHARGED_TO = re.compile(r"\b(?:charg\w*|bill\w*|put|add\w*|book\w*|expens\w*)\b[^.;,]*\bto\s+$")
# A permission word inside a negation ("he never asked me") is not a claim that permission was given.
_NEGATION = re.compile(r"\b(?:never|not|no|without|didn't|did not|hasn't|has not|wasn't|n't)\s+(?:\w+\s+){0,2}$")

# KEY C -- the sender's words say someone's permission matters.
_ATTESTATION = re.compile(
    r"\b(permission|permit(?:s|ted)?|consent(?:s|ed)?|authori[sz](?:e|es|ed|ation)|approv(?:e|es|ed|al)|"
    r"agree(?:s|d|ment)?|allow(?:s|ed)?|signed\s+(?:it\s+)?off|sign(?:s)?\s+off|ok(?:'d|ayed)|"
    r"(?:ok|okay|fine)\s+with|said\s+(?:it\s+(?:was|is)|it's|i\s+(?:could|can|may)|we\s+(?:could|can|may))|"
    r"told\s+me|asked\s+me|instruct(?:s|ed|ion|ions)?|request(?:s|ed)?|go-?ahead|green\s+light|blessing|"
    r"confirm(?:s|ed)?|i\s+may)\b")


def _text(data):
    """The exact text the judges read (covenant_judge_fallback._payload_text), imported by name so the phone
    build's static import list is not widened; a plain string or dict falls back to a flat join."""
    try:
        import importlib
        return importlib.import_module("covenant_judge_fallback")._payload_text(data)
    except Exception:                                            # noqa: BLE001
        if isinstance(data, dict):
            return " ".join(str(v) for v in data.values())
        return str(data)


def _norm(s):
    return re.sub(r"\s+", " ", str(s).replace("’", "'").replace("‘", "'").lower())


def owned_by_another(text):
    """[(possessor, object)] -- KEY A: things the text says belong to someone other than the sender."""
    t = _norm(text)
    out = []
    for rx, is_noun in ((_POSSESSIVE_PRONOUN, False), (_POSSESSIVE_NOUN, True)):
        for m in rx.finditer(t):
            who = m.group(1)
            if is_noun and who in _NOT_A_POSSESSOR:
                continue
            before = t[:m.start()]
            if _DESTINATION.search(before) and not _CHARGED_TO.search(before):
                continue
            # the first word naming a stored value among the (up to three) words that follow
            obj = next((w for w in m.group(2).split() if w in _ASSETS), None)
            if obj:
                out.append((who, obj))
    return out


def attestations(text):
    """[word] -- KEY C: words by which the text invokes someone's permission (a negated one is not)."""
    t = _norm(text)
    return [m.group(0) for m in _ATTESTATION.finditer(t) if not _NEGATION.search(t[:m.start()])]


def preconditions(data):
    """[blank] -- each blank is a condition the payload claims and nothing records: the owner's consent for a
    thing the text says is someone else's, invoked in the sender's own words. Empty when there is none."""
    text = _text(data)
    owned = owned_by_another(text)
    if not owned:
        return []
    said = attestations(text)
    if not said:
        return []
    who, obj = owned[0]
    return [{"kind": "owner_consent", "party": who, "object": obj, "claimed_by": sorted(set(said))[:4],
             "fill": "the owner's own recorded declaration (no release path is enabled yet; it is the operator's "
                     "and Tetsu's decision)"}]


def describe(blanks):
    """The hold's reason, naming each blank and who can fill it."""
    parts = ["owner's consent for %s %s: claimed in the content (%s), not recorded"
             % (b["party"], b["object"], ", ".join(b["claimed_by"])) for b in blanks]
    return ("a claimed consent is not a recorded one -- %s. Fill by: %s. Held, not judged: nothing here alleges "
            "a violation." % ("; ".join(parts), blanks[0]["fill"]))


if __name__ == "__main__":
    import sys
    for line in (sys.argv[1:] or ["My cousin gave written permission to use her card for the tickets."]):
        b = preconditions({"message": line})
        print(("HOLD  " + describe(b)) if b else "none  (no claimed consent over another party's thing)")
