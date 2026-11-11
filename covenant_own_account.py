#!/usr/bin/env python3
"""Who is US, among the forum comments we read. One rule, shared by every reader (A418, 2026-11-09).

A280 (2026-10-06) taught free's reply round to recognise her own account: the account's name is on no record
here, so she is recognised by what she said -- an author whose comment BEGINS with the text of one of her
replies is her (A349 A13 added the replies Moltbook created and hid behind its challenge). That rule lived
inline in covenant_free_will.run_round. The improve-miner (10-27) reads the same comments log through its own
harvest and never got it: on 2026-11-08 it mined u/covenant-node -- our own reply -- as an outside idea, and 294
more of our replies were waiting in its queue. A rule that lives in one consumer is a fix to that consumer, not
to the shape; this module is the place every reader of ops/moltbook_candidates.jsonl asks.

One correction to A280's rule, measured 2026-11-09 on the live logs: two of free's SENT replies (to u/anakunggul
11-02, to u/TechnoBiota 11-04) open with the other agent's own words, so their comments begin with "our" text and
A280 classed both of them as us. A send row records whom it answered (its `author`), so a match against a reply
TO that same author is the comment we answered, not ours. Free's sends keep that field on every reply row.

Read-only. Standard library only; importing it has no side effects.
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
# The same ledger and the same override as covenant_free_will.SENDS, resolved at call time (IM8), never frozen.
SENDS_ENV = "COVENANT_AMBASSADOR_SENDS"
MIN_CHARS = 60         # A280: a short text ("Thanks!") is not a fingerprint
PREFIX_CHARS = 120     # A280: "begins with" = the first 120 normalised characters agree


def sends_path():
    return os.environ.get(SENDS_ENV) or os.path.join(HERE, "ops", "ambassador_sends.jsonl")


def norm(s):
    """A280's normalisation: whitespace collapsed, lower-cased, the first PREFIX_CHARS characters."""
    return re.sub(r"\s+", " ", str(s or "")).strip().lower()[:PREFIX_CHARS]


def load_sends(path=None):
    """The sends ledger as a list of dicts, or None when the file is missing (a reader must say so, not guess)."""
    path = path or sends_path()
    if not os.path.exists(path):
        return None
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if isinstance(d, dict):
                out.append(d)
    return out


def our_texts(send_rows):
    """{normalised text: {authors it answered}} for every text that went up under our account: sent, or created
    and hidden behind Moltbook's challenge (a row carries a `verification` dict only when content was created)."""
    out = {}
    for r in send_rows or ():
        if not isinstance(r, dict):
            continue
        if not (r.get("sent") or isinstance(r.get("verification"), dict)):
            continue
        t = norm(r.get("text"))
        if len(t) < MIN_CHARS:
            continue
        out.setdefault(t, set()).add(r.get("author"))
    return out


def is_our_text(author, text, ours):
    """Does this comment begin with one of our texts -- and was that text NOT a reply to this same author? (When
    our reply opened with their words, their comment matches it; it is the comment we answered, not ours.)"""
    t = norm(text)
    return len(t) >= MIN_CHARS and t in ours and author not in ours[t]


def own_authors(rows, ours):
    """Authors recognised as us from the rows read. Once an author is us, EVERY row by that author is ours --
    including ones the ledger records as neither sent nor created (2 of the 574 u/covenant-node rows in the log on
    2026-11-09: the text rule alone misses them, the author rule does not)."""
    own = set()
    for row in rows or ():
        if isinstance(row, dict) and row.get("author") and is_our_text(row.get("author"), row.get("text"), ours):
            own.add(row.get("author"))
    return own
