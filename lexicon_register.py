"""lexicon_register.py -- how crime is actually spoken, not how it is defined.

THE MEASUREMENT. The v2 judge, against twenty lines of screen dialogue in which
a crime is plainly being arranged:

    caught 1 of 20 -- and the one hit was the word `hide`, not the crime.

The lexicon holds the DICTIONARY words for theft -- steal, rob, plunder, theft,
embezzle. Nobody arranging one uses them. They say the vig, a taste off the top,
run it through the restaurant, the score, the take, kite the checks, structure
the deposits, cook the books. Euphemism is not decoration around the crime; it
is the register the crime is conducted in, and a gate fitted only to the
dictionary is deaf to every actual conversation.

WHY A SINGLE MARKER MUST NEVER FIRE, AND THIS IS THE WHOLE DESIGN. Euphemism
works BY using ordinary words. `wash`, `clean`, `the job`, `the drop`, `my cut`,
`a taste`, `protection`, `boiler room` are overwhelmingly innocent -- a car
wash, a boiler-room radiator, a kite for the kids' birthday, cooking dinner for
twelve. So the ordinary word can never be evidence on its own. What is evidence
is CO-OCCURRENCE: several markers of the register in one payload.

    rule                       benign false positives   criminal caught
    2+ distinct markers               0 / 64                 20 / 20
    3+ distinct markers               0 / 64                 13 / 20
    2+ distinct CATEGORIES            0 / 64                  4 / 20
    3+ distinct CATEGORIES            0 / 64                  1 / 20

The category rule was the author's instinct and the measurement rejected it:
criminals stay INSIDE a register, so requiring two different registers throws
away four fifths of the signal. Two distinct markers, of any category, is the
fitted rule.

The 64 benign lines were written to be adversarial -- `car wash, fleet of six`,
`boiler room radiator replacement`, `pump and dump the flood water`, `dump our
position on the old stock, clearance sale`, `the mark on the wall needs
plastering`, `recycle the client list into the new CRM`, `smurf costume for the
party`, `kite for the kids birthday`, `overbilled last month, refunding the
difference`. None of them fired. They are still the author's own, n=64, and that
is two observations rather than a validation, exactly as the model file says of
its own separation set.

WHAT IT MAY DO. It caps at ABSTAIN. It may never assert a VIOLATION, and the
reason is stronger than the one that caps the seeded translations: these are
ORDINARY ENGLISH WORDS. A gate that says `you have committed theft` because a
memo contained `wash` and `the drop` would be asserting something it cannot
possibly know. `I recognise the way this is being discussed and I cannot read
the intent` is ABSTAIN, and ABSTAIN is the honest ceiling.

WHY THE ROBIN HOOD REGISTER IS DELIBERATELY ABSENT, AND IT IS A SAFETY
CONSTRAINT RATHER THAN A TASTE. The noble-thief vocabulary -- take from the
rich, redistribute, they can afford it, the people's money, give it back to
them -- is the one place where theft-language and GENEROSITY-language are the
same language. Encode it and the judge fires on charity, mutual aid, debt
forgiveness, a whip-round for somebody's medical bills, a progressive transfer:
false positives with a political direction, landing on exactly the transactions
this system exists to protect. No lexicon can separate `take from the rich and
give to the poor` from `give to the poor`, so the register stays out and the
gap is stated instead of papered over.

    Excluded for the same reason: Ocean's Eleven, The Italian Job, Jean Valjean
    -- narratives that endorse the theft. Included: predation the story does not
    excuse. Goodfellas, Casino, The Sopranos, The Sting, Catch Me If You Can,
    Heat, The Wolf of Wall Street, Boiler Room, The Firm, The Big Short,
    American Hustle, Fargo, Layer Cake, Office Space, Trading Places.

WHAT IT CANNOT DO, said here rather than discovered later. **Euphemism is
generative.** Anyone who reads this file invents new phrasing in a minute --
that is what euphemism IS FOR. This does not defend against a party who knows
the list. It catches the register leaking through when nobody was hiding, which
is the ordinary case, and it is worth exactly that much and no more.
"""

# Grouped by what each is a euphemism FOR, so a reviewer can check one register
# without reading the rest. Grouping does NOT affect firing -- the fitted rule
# counts distinct markers, not categories. See the table above.
REGISTER = {
 "laundering": [
    "wash", "washed", "washing", "clean", "cleaned", "cleaning", "clean cash",
    "comes out clean", "structure", "structuring", "structured", "smurf",
    "layering", "shell company", "front company", "gross receipts",
    "cash business", "through the restaurant", "through the property",
    "through the car wash", "declare it as", "under the table"],
 "skimming": [
    "skim", "skimmed", "skimming", "off the top", "a taste", "shave", "shaving",
    "fractions of a penny", "count room", "before it gets counted",
    "off the books", "goes in the book"],
 "extortion": [
    "vig", "the juice", "protection money", "tribute", "the envelope",
    "offer he can't refuse", "offer he cannot refuse", "pay me", "sit down",
    "every week", "or else", "has an accident", "insurance", "leaned on"],
 "fraud": [
    "the mark", "on the wire", "the con", "long con", "kite", "kiting",
    "paper hanging", "cook the books", "mismark", "mismarking", "overbill",
    "recycle the client", "boiler room", "bust out", "bust the joint",
    "no-show", "pump and dump", "dump our position", "under ten thousand",
    "nothing reports", "never let him cash out", "nobody audits",
    "before the announcement", "inside information"],
 "the_job": [
    "the score", "the take", "the drop", "the satchel", "split it", "my cut",
    "the earner", "torch it", "goes away clean", "never knows"],
}

MIN_MARKERS = 2          # fitted: 0/64 benign, 20/20 criminal

# Generosity is NOT in the lexicon above, and this list exists so the suite can
# prove it stays out. Every one of these must remain CLEAN.
MUST_STAY_CLEAN = [
 "redistribute the surplus to the families who need it",
 "take from what we have spare and give it to the food bank",
 "they can afford it, we are forgiving the debt in full",
 "the people's fund, paid out to whoever asks",
 "give it back to them, all of it, no conditions",
 "mutual aid for the strike fund, no repayment expected",
 "a whip-round for her medical bills",
 "progressive contribution, the higher earners cover the rest",
 "cancelling what he owes me, he needs it more",
 "wealth going where it does more good",
]


def build():
    """{phrase: category}, longest first so a phrase wins over its own prefix."""
    out = {}
    for cat, phrases in REGISTER.items():
        for p in phrases:
            out[p.lower()] = cat
    return dict(sorted(out.items(), key=lambda kv: (-len(kv[0]), kv[0])))
