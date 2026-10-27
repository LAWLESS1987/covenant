#!/usr/bin/env python3
"""covenant_screen.py -- one normaliser in front of every text screen.

MEASURED 2026-09-21 (A176, his words: "Evolving cyber security protection").
Five screens in this tree are regular expressions on raw text, and each was
probed with the same six disguises. What got through:

    disguise                      forum OFF_LIMITS  contact REFUSED  persona  directive flag
    zero-width joiner in a word   passed            passed           passed   passed
    fullwidth letters             passed            (not tried)      -        passed
    Cyrillic look-alike letter    passed            -                -        -
    dotted acronym  N.S.F.        passed            -                -        -
    spaced letters  N S F         passed            pass word        a l w a y s   -
    hyphenated      n-s-f         passed            -                -        -

None of those screens was wrong about the plain text; every one was blind to
the same six disguises, because each matched bytes rather than what a reader
sees. This file is the one place that undoes the disguises, so a fix here
reaches every screen that calls normalize() first, and the probe set in
covenant_security_probe.py keeps them honest from now on.

WHAT normalize() DOES, in order:
  1. Unicode NFKC: fullwidth and other compatibility forms to their plain
     letters (ＮＳＦ -> NSF).
  2. Drops format characters (category Cf: zero-width space/joiner/non-joiner,
     soft hyphen, direction marks) -- they are invisible and carry no meaning
     a reader could see.
  3. Maps the common Cyrillic and Greek look-alikes to the Latin letter they
     imitate (а е о р с х у і ј ѕ -> a e o p c x y i j s, and capitals).
  4. Joins letters that were pulled apart with dots, hyphens or single spaces
     (N.S.F. / N S F / n-s-f -> NSF; a l w a y s -> always). Three or more
     single letters in a row are joined; ordinary words are not touched.

WHAT IT CANNOT DO. It is a normaliser, not a judge: a paraphrase ("the
national science funder") is not a disguise of a word, it is a different
sentence, and no screen on words will see it. The gate that judges meaning
sits behind every screen for that reason. Leetspeak (passw0rd) is handled by
the screens' own patterns where it matters, not here, because 0 for o inside
ordinary prose (e.g. "10 o'clock") would be wrong to undo globally.
"""
import re
import unicodedata

_CONFUSABLES = {
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x", "у": "y",
    "і": "i", "ј": "j", "ѕ": "s", "һ": "h", "ԁ": "d", "ԛ": "q", "ԝ": "w",
    "А": "A", "В": "B", "Е": "E", "К": "K", "М": "M", "Н": "H", "О": "O",
    "Р": "P", "С": "C", "Т": "T", "Х": "X", "І": "I", "Ј": "J", "Ѕ": "S",
    "α": "a", "ο": "o", "ρ": "p", "υ": "y", "ν": "v", "Α": "A", "Β": "B",
    "Ε": "E", "Η": "H", "Ι": "I", "Κ": "K", "Μ": "M", "Ν": "N", "Ο": "O",
    "Ρ": "P", "Τ": "T", "Υ": "Y", "Χ": "X", "Ζ": "Z",
}
_SPLIT = re.compile(r"(?<![A-Za-z0-9])(?:[A-Za-z][.\-· ]){2,}[A-Za-z](?![A-Za-z0-9])")


def normalize(text):
    """The text a reader sees, for a screen to read. Never raises; non-str -> ''."""
    if not isinstance(text, str):
        return ""
    t = unicodedata.normalize("NFKC", text)
    t = "".join(_CONFUSABLES.get(ch, ch) for ch in t if unicodedata.category(ch) != "Cf")
    t = _SPLIT.sub(lambda m: re.sub(r"[.\-· ]", "", m.group(0)), t)
    return t


def search(pattern, text):
    """pattern.search(normalize(text)) -- the one call every screen makes."""
    return pattern.search(normalize(text))


if __name__ == "__main__":
    import sys
    for line in sys.stdin:
        print(normalize(line.rstrip("\n")))
