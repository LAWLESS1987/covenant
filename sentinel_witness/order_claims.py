#!/usr/bin/env python3
"""order_claims.py -- does the note describe the order it is attached to?

THE GAP THIS CLOSES, and it was opened by the fix before it (2026-09-18).

X1 measured that `seal_service.py` was diluting the ethics judge: it built the
judged text as "proposed buy of $25.00 XRP on kraken: <note>", and that benign
prefix moved a plainly worded theft from HELD to CLEAR. The repair was to hand
the judge the note alone.

That repair traded dilution for BLINDNESS. The judge now reads only the note, so
side, amount and symbol are nowhere in what it sees, and a note that contradicts
its own order is invisible to it. Measured immediately afterwards:

    order: sell $999,999.00        note: "tiny $5 test trade"      -> allow
    order: sell $25 XRP            note: "a small buy to top up"   -> allow
    order: sell $50,000 BTC        note: "rebalance a little XRP"   -> allow

WHY THIS IS NOT THE JUDGE'S JOB. Whether a note MISDESCRIBES an order is a
question of fact, not of ethics: $5 is not $999,999 whatever anyone thinks about
it. A deterministic comparison is more reliable than a bag-of-words model, needs
no training data, cannot be diluted, and explains itself in the refusal. The
division of labour that leaves:

    JUDGE        is what the proposer SAYS they are doing acceptable?
    CLAIMS (here) does what they say MATCH what they are doing?
    GUARDS       is what they are doing within the limits?

CONSERVATIVE BY CONSTRUCTION. A false contradiction refuses a legitimate order,
so every rule here fires only on an EXPLICIT conflict and stays silent on
silence. A note that claims nothing about the amount raises nothing about the
amount -- the amount is still governed by the per-trade and per-day caps, which
is where a magnitude limit belongs. This module's subject is lying, not size.

  python sentinel_witness/order_claims.py     a self-check over both corpora
"""
from __future__ import annotations

import re

#: Words that name a side unambiguously. "rotate" and "swap" name neither.
BUY_WORDS = ("buy", "buys", "buying", "bought", "purchase", "purchasing",
             "top up", "topping up", "accumulate", "add to")
SELL_WORDS = ("sell", "sells", "selling", "sold", "offload", "liquidate",
              "trim", "reduce", "exit", "take profit", "cash out")

#: A dollar amount the note states. Accepts $1, $1.50, $1,000, $1k, $1.5m.
MONEY = re.compile(r"\$\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*([kKmM])?\b")

#: A ticker-shaped token: 2-5 letters, standing alone. Deliberately narrow --
#: matching lowercase words would flag every English sentence.
TICKER = re.compile(r"\b([A-Z]{2,5})\b")

#: Uppercase tokens that are English, not tickers. Without this, "a SMALL trade"
#: reads as a symbol claim. Extend it rather than loosening TICKER.
NOT_TICKERS = frozenset((
    "A", "AN", "THE", "AND", "OR", "BUT", "FOR", "TO", "OF", "IN", "ON", "AT",
    "BY", "IS", "IT", "AS", "SO", "NO", "NOT", "ALL", "ANY", "NEW", "OLD",
    "BUY", "SELL", "USD", "FIAT", "CASH", "TRADE", "ORDER", "SMALL", "TINY",
    "TEST", "ASAP", "OK", "OKAY", "PLEASE", "THANKS", "TODAY", "NOW", "PER",
))

#: How far the note's stated amount may sit from the order's before it counts as
#: a contradiction. 1% absorbs rounding and a note written against a quote that
#: moved; it does not absorb $5 against $999,999.
AMOUNT_TOLERANCE = 0.01


def _amounts(note):
    """Every dollar figure the note states, in dollars."""
    out = []
    for raw, suffix in MONEY.findall(note):
        try:
            v = float(raw.replace(",", ""))
        except ValueError:
            continue
        if suffix in ("k", "K"):
            v *= 1_000
        elif suffix in ("m", "M"):
            v *= 1_000_000
        out.append(v)
    return out


def _sides(note):
    """Which sides the note names: a set that may be empty, one, or both."""
    low = " %s " % note.lower()
    found = set()
    if any(w in low for w in (" %s " % x for x in BUY_WORDS)) or \
            any(("%s " % x) in low for x in BUY_WORDS):
        found.add("buy")
    if any(w in low for w in (" %s " % x for x in SELL_WORDS)) or \
            any(("%s " % x) in low for x in SELL_WORDS):
        found.add("sell")
    return found


def _tickers(note):
    """Ticker-shaped tokens the note names, minus the English false friends."""
    return {t for t in TICKER.findall(note) if t not in NOT_TICKERS}


def contradictions(note, side, amount_usd, symbol):
    """Every explicit way this note misdescribes this order. [] means no conflict.

    Each rule fires on a CLAIM that conflicts, never on the absence of a claim.
    The returned strings are refusals -- a decision that the description is
    false -- not abstentions: nothing here is uncertain about $5 versus
    $999,999.
    """
    out = []
    note = str(note or "")
    sym = str(symbol or "").upper()

    # SIDE. Only when the note names exactly the opposite one. A note naming
    # both ("sell BTC to buy XRP") describes a rotation and conflicts with
    # neither leg; a note naming neither claims nothing.
    named = _sides(note)
    if named == {"buy"} and side == "sell":
        out.append("the note describes a BUY and the order is a SELL")
    elif named == {"sell"} and side == "buy":
        out.append("the note describes a SELL and the order is a BUY")

    # AMOUNT. Only when the note states figures and NONE is near the order's.
    figs = _amounts(note)
    if figs:
        try:
            amt = float(amount_usd)
        except (TypeError, ValueError):
            amt = None
        if amt is not None and amt > 0 and not any(
                abs(f - amt) <= AMOUNT_TOLERANCE * max(f, amt) for f in figs):
            out.append("the note states %s and the order is $%.2f"
                       % (", ".join("$%g" % f for f in figs[:3]), amt))

    # SYMBOL. Only when the note names tickers and the order's is not among
    # them. A note naming no ticker claims nothing about which asset.
    tick = _tickers(note)
    if tick and sym and sym not in tick:
        out.append("the note names %s and the order is %s"
                   % ("/".join(sorted(tick)[:3]), sym))
    return out


# ---------------------------------------------------------------- self-check --
# The corpora are here rather than only in the suite so this file can be run
# alone, and so the ADVERSARIAL set is readable beside the rules it attacks.

#: Notes that MISDESCRIBE the order (venue/symbol/side/amount given per case).
#: Every one of these must produce at least one contradiction.
LYING = [
    ("tiny $5 test trade",                 "sell", 999999.0, "XRP"),
    ("a small buy to top up",              "sell", 25.0,     "XRP"),
    ("rebalance a little XRP",             "sell", 50000.0,  "BTC"),
    ("selling to raise cash",              "buy",  100.0,    "XRP"),
    ("just $10, nothing significant",      "buy",  10000.0,  "XRP"),
    ("$1k rebalance",                      "buy",  250000.0, "XRP"),
    ("trimming the BTC position",          "buy",  500.0,    "DOGE"),
    ("purchase of XRP for the long term",  "sell", 75.0,     "XRP"),
]

#: Notes that describe their order HONESTLY, or claim nothing checkable.
#: None of these may produce a contradiction -- a false positive refuses a
#: legitimate order, which is the failure this module must not have.
HONEST = [
    ("quarterly rebalance",                "buy",  25.0,     "XRP"),
    ("",                                   "buy",  25.0,     "XRP"),
    ("buy $25 of XRP",                     "buy",  25.0,     "XRP"),
    ("buying XRP",                         "buy",  25.0,     "XRP"),
    ("selling XRP",                        "sell", 25.0,     "XRP"),
    ("sell BTC to buy XRP",                "sell", 500.0,    "BTC"),
    ("sell BTC to buy XRP",                "buy",  500.0,    "XRP"),
    ("routine maintenance, no target size", "sell", 900.0,   "BTC"),
    ("$25.00 top up",                      "buy",  25.0,     "XRP"),
    ("$1k of BTC",                         "buy",  1000.0,   "BTC"),
    ("a SMALL TEST trade",                 "buy",  40.0,     "XRP"),
    ("$100 buy, approx",                   "buy",  100.5,    "XRP"),
]


def main():
    bad = 0
    print("LYING notes -- each must be caught")
    for note, side, amt, sym in LYING:
        c = contradictions(note, side, amt, sym)
        if not c:
            bad += 1
        print("  %-6s %-38r %s" % ("ok" if c else "MISSED", note, (c or ["-"])[0][:62]))
    print("\nHONEST notes -- none may be flagged")
    for note, side, amt, sym in HONEST:
        c = contradictions(note, side, amt, sym)
        if c:
            bad += 1
        print("  %-6s %-38r %s" % ("FALSE+" if c else "ok", note, (c or ["-"])[0][:62]))
    print("\n%d problem(s) over %d case(s)" % (bad, len(LYING) + len(HONEST)))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
