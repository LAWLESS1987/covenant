"""competence.py -- what the judge can and cannot read.

THE DEFECT THIS CLOSES, measured on the shipped v1 model before a line of this
was written:

    English  "steal the funds, rob the account"    623  violates
    Spanish  "robar todos los fondos, saquear"       0  clean
    Russian  "украсть все средства, ограбить счёт"   0  clean
    leetspeak "st3al th3 funds, r0b the acc0unt"     0  clean

Every one of those returned the SAME verdict as "transfer to cover rent this
month", because the only thing deciding was `score < gate_lo -> CLEAN`. The
judge was treating **I found no evidence of a violation** as **there is no
violation**. Those are different claims. This project already has the rule for
it -- UNKNOWN is never PASS -- and had simply never applied it to the judge.

AND IT IS NOT A SIDE ISSUE, given what this system says it is for. A judge that
silently returns "clean" on every language it was not fitted for is not
neutral toward those speakers; it is excluding them and calling the exclusion
approval. Saying ILLEGIBLE out loud is the smaller, more honest claim, and it
is the only one that can be extended -- you cannot fix a gap the system does
not report.

TWO TESTS, BECAUSE ONE RATIO CANNOT CARRY IT.

  1. SCRIPT (hard, presence-based, cannot be diluted). The space was fitted on
     one script. Two or more tokens outside it and the model is definitionally
     not competent, no matter how much English is padded around them. One
     foreign token is a name and passes -- two is a sentence.

  2. COVERAGE (soft, ratio-based). For a language sharing the fitted script --
     Spanish, French, Latin -- the signal is how much of the payload was in the
     fitted vocabulary at all. Measured:

         English, benign AND violating   60-100%   (worst: "node operator
                                                    stipend" -- a 19th-century
                                                    corpus has no `node`)
         Spanish / French / German          28-33%
         Russian / Mandarin / Latin          0%

     Taken as the MINIMUM over sliding windows, never the mean, for the same
     reason score() takes the maximum hit: an average lets a payload buy a pass
     by padding, and X2 says there is no lever that buys a pass. Adding tokens
     can only add windows, and a minimum over a larger set can only fall.

WHAT THIS DOES NOT DO, said plainly rather than discovered later. A payload
that interleaves one foreign token per five English ones defeats the coverage
window, and the script test only catches it if the tokens are non-Latin. That
is a deliberate limit: the ethics gate is a VALUES gate, and the system's
actual defence against theft is the signature and balance checks. A judge that
`mock_selfreport` already waves "drain all staked funds" past is not the place
to spend effort on adversarial token-interleaving.

REPAIR IS ONE-WAY. NFKC, zero-width stripping, homoglyph folding and leet
de-substitution produce a second token stream which is scored separately, and
the final score is the MAXIMUM of the two. Repair can raise a score. Nothing in
here can lower one. That is asserted, not intended.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Dict, List, Optional, Tuple

_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)

# ---------------------------------------------------------------- the scripts
_SCRIPT_CACHE: Dict[str, str] = {}


def char_script(ch: str) -> str:
    """The script a character belongs to, from its own Unicode name.

    No table to maintain and no dependency: unicodedata already knows that
    'CYRILLIC SMALL LETTER U' is Cyrillic. A name we cannot read is 'Unknown',
    which is a competence answer too.
    """
    hit = _SCRIPT_CACHE.get(ch)
    if hit is not None:
        return hit
    try:
        name = unicodedata.name(ch)
    except ValueError:
        name = ""
    if not name:
        out = "Unknown"
    else:
        first = name.split()[0]
        out = {"CJK": "Han", "HANGUL": "Hangul", "HIRAGANA": "Kana",
               "KATAKANA": "Kana"}.get(first, first.capitalize())
    _SCRIPT_CACHE[ch] = out
    return out


def token_script(tok: str) -> str:
    """A token's script: the one its letters agree on, or 'Mixed'.

    Mixed is itself a finding -- a token whose letters come from two scripts is
    the classic homoglyph shape (`pаypal` with a Cyrillic а), and it is exactly
    what repair() is for.
    """
    seen = {char_script(c) for c in tok if c.isalpha()}
    if not seen:
        return "Unknown"
    if len(seen) == 1:
        return seen.pop()
    return "Mixed"


# ------------------------------------------------------------------- repairing
# Only pairs that are visually confusable in a normal font. Each one can only
# ever turn a non-matching token INTO a matching one, so this table's whole
# effect is to raise scores. Growing it is therefore always safe -- which is
# the reason it is a plain dict and not a hashed model artefact.
_CONFUSABLE = {
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c",
    "у": "y", "х": "x", "і": "i", "ј": "j", "һ": "h",
    "ο": "o", "α": "a", "ε": "e", "ρ": "p", "υ": "u",
    "А": "A", "Е": "E", "О": "O", "Р": "P", "С": "C",
    "Х": "X", "Β": "B", "Ο": "O", "Η": "H",
}
_LEET = {"0": "o", "1": "l", "3": "e", "4": "a", "5": "s", "7": "t",
         "@": "a", "$": "s", "!": "i", "|": "l"}
# A digit only becomes a letter when it is sitting INSIDE a word. `st3al` is an
# evasion; `4417` is an invoice number and must stay a number, because turning
# it into `aail` would invent tokens the sender never wrote.
_INWORD = re.compile(r"(?<=[^\W\d_])([0-9@$!|])(?=[^\W\d_])|"
                     r"(?<=[^\W\d_])([0-9@$!|])$|"
                     r"^([0-9@$!|])(?=[^\W\d_])")


def repair(text: str) -> str:
    """Undo the cheap ways of hiding a word from a lexicon.

    NFKC folds width and ligature variants; Cf strips the zero-width and
    directional characters that split a word invisibly; the confusable table
    folds Cyrillic and Greek look-alikes back to Latin; and in-word digits and
    symbols become the letters they are standing in for.
    """
    t = unicodedata.normalize("NFKC", text)
    t = "".join(c for c in t if unicodedata.category(c) != "Cf")
    t = "".join(_CONFUSABLE.get(c, c) for c in t)
    return _INWORD.sub(lambda m: _LEET[m.group(1) or m.group(2) or m.group(3)], t)


# ------------------------------------------------------------------- coverage
def windows(tokens: List[str], size: int):
    """Every contiguous window, or the whole thing if it is shorter than one."""
    if len(tokens) <= size:
        yield tokens
        return
    for i in range(len(tokens) - size + 1):
        yield tokens[i:i + size]


def coverage(tokens: List[str], vocab, window: int) -> Optional[int]:
    """Percent of the WORST window that the fitted vocabulary knows.

    Minimum, not mean. A mean is a lever: pad a foreign payload with English
    and the average climbs until it passes. A minimum over windows cannot be
    raised by addition -- more tokens means more windows, and the smallest
    member of a larger set is never larger. Returns None when there is nothing
    to measure, which is not 100 and is not 0.
    """
    if not tokens:
        return None
    worst = 100
    for w in windows(tokens, window):
        hit = 0
        for t in w:
            if t in vocab:
                hit += 1
        pct = hit * 100 // len(w)
        if pct < worst:
            worst = pct
    return worst


def script_gaps(tokens: List[str], fitted: str) -> Dict[str, int]:
    """Tokens whose script the model was never fitted on, counted by script."""
    out: Dict[str, int] = {}
    for t in tokens:
        s = token_script(t)
        if s == "Unknown":
            continue
        if s != fitted:
            out[s] = out.get(s, 0) + 1
    return out


def tokens_of(text: str) -> List[str]:
    return _WORD.findall(unicodedata.normalize("NFC", str(text).lower()))
