#!/usr/bin/env python3
"""test_purge_tool.py -- the purge tool's content rules, on synthetic text.

WHY (2026-09-05)
  tools/purge_history.py rewrites every blob of every ref. A rule that is too
  loose damages code and documents across the whole history; a rule that is
  too tight leaves the portfolio public while the tool prints CLEAN. Both
  failure modes are silent unless something pins the rules to examples. The
  examples here are invented: no line below is from the owner's files, and
  the numbers are made up.
LICENCE: public domain.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "tools"))

import purge_history as PH  # noqa: E402

NL = chr(10)
FAILS = []
N = 0


def ok(tag, name, cond, detail=""):
    global N
    N += 1
    print("   %s  %s %s  %s" % ("PASS" if cond else "FAIL", tag, name, str(detail)[:90]))
    if not cond:
        FAILS.append(tag)


def main():
    print("purge tool -- content rules on invented text")

    table = NL.join([
        "SYMBOL   QUANTITY      AVG_BUY     NOTE",
        "XLM      1234.5678     0.3210",
        "PEPE   98765432.10     0.0000123   thin market",
        "CASH        321.00     1.00",
        "ABC      1.5          2.5",       # not a portfolio symbol: untouched
    ])
    out, n = PH.rewrite_text(table, None)
    ok("R1", "every portfolio row loses both numbers", n == 3 and out.count("<qty>") == 3 and out.count("<avg_buy>") == 3, n)
    ok("R2", "the note after the numbers survives", "thin market" in out)
    ok("R3", "a row for a symbol not in the set is untouched", "ABC      1.5          2.5" in out)
    ok("R4", "the header row is untouched", "SYMBOL   QUANTITY" in out)

    prose = NL.join([
        "rebates only appear above roughly $10M in 30-day volume. At $4,321",
        "of capital, market making pays fees.",
        "the $1,234 sleeve is the only live capital",
        "exceeds $1,234/year in the long run",
        "# which is where a ~$4k book sits -- is 0.40% taker.",
    ])
    out, n = PH.rewrite_text(prose, None)
    ok("R5", "the capital sentence loses its amount", "At this scale of capital" in out and "$4,321" not in out)
    ok("R6", "the sleeve sentence loses its amount", "the sleeve is the only" in out and "$1,234 sleeve" not in out)
    ok("R7", "the per-year sentence loses its amount", "exceeds the sleeve's size per year" in out)
    ok("R8", "the book-size comment loses its amount", "a small book" in out and "$4k" not in out)
    ok("R9", "the fee tier that is not the owner's number survives", "$10M in 30-day volume" in out and "0.40% taker" in out)

    sample = '{"equity": [[1700000000, 4321.98]], "last_sold": {}}'
    out, n = PH.rewrite_text(sample, None)
    ok("R10", "the sample equity value becomes a round synthetic one, timestamp kept",
       '"equity": [[1700000000, 1000.0]]' in out, out)
    pretty = '{' + NL + ' "equity": [' + NL + '  [' + NL + '   1700000000.0,' + NL + '   4321.98' + NL + '  ]' + NL + ' ],' + NL + ' "last_sold": {}}'
    out, n = PH.rewrite_text(pretty, None)
    ok("R11", "the same when pretty-printed with a float timestamp", "4321.98" not in out and "1000.0" in out, out.replace(NL, " "))
    wrapped = "All ten positions are locked in `TRADING_POLICY.json`; the $1,234" + NL + "sleeve is the only live capital"
    out, n = PH.rewrite_text(wrapped, None)
    ok("R12", "a sleeve sentence that wraps onto the next line still loses its amount", "$1,234" not in out and "the sleeve is the only" in out)
    out, n = PH.rewrite_text("# which is where a ~$3.5k book sits -- is 0.40% taker.", None)
    ok("R13", "a book-size comment with a decimal loses its amount", "$3.5k" not in out and "a small book" in out)

    logs = NL.join([
        "> portfolio $3,210.50, two trims and the cash floor flagged.",
        "portfolio **$3,214.04**, two trims and the cash floor flagged, all nine agreeing",
        "**Portfolio $2,468.10 · 0.0% cash · prices as of the settled close**",
        "- **The two Rule-1 trims are still undone.** XLM ~$210, SOL ~$140.",
        "- **TRIM XLM** 27.4% → 20%: sell ~1,234.5678 XLM ≈ $210",
        "is in the Kraken account. The first version sized a sell for 1,239 XLM when the",
        "1. SELL 98.7654321 XLM  [clamped: rule wants 123.456 but Kraken holds 98.7654]",
    ])
    out, n = PH.rewrite_text(logs, None)
    ok("R14", "portfolio totals in logs become <total>, in all three spellings",
       out.count("portfolio <total>") == 2 and "Portfolio <total>" in out and "$3,2" not in out and "$2,4" not in out)
    ok("R15", "the trim amounts and shares go", "XLM and SOL by the Rule-1 amounts" in out and "sell ~<qty> XLM ≈ $<value>" in out
       and "**TRIM XLM** <share> → <cap>" in out and "27.4%" not in out)
    ok("R16", "the execution note's Kraken quantities go", "sized a sell for <qty> XLM" in out
       and "SELL <qty> XLM  [clamped: rule wants <qty> but Kraken holds <qty>]" in out and "98.76" not in out)
    ok("R17", "the words around them survive", "two trims and the cash floor flagged" in out and "is in the Kraken account" in out)
    ok("R18", "ALERTS.md is a removed path, root and launch copy", "ALERTS.md" in PH.PATHS and "launch/covenant-v8.37/ALERTS.md" in PH.PATHS)

    baseline = NL.join([
        "# Verified price baseline", "", "| XRP | 369 | 1.2345 | 1.4567 |", "",
        "## Portfolio at these prices", "", "Total **$2,468.10**, cash **$0.00 (0.0%)**.", "",
        "| XLM | 789.12 | 27.4% | -23.4% |", "", "## Actions the rules call for", "",
        "- **TRIM XLM** 27.4% → 20%: sell ~1,234.5678 XLM ≈ $210", "",
        "## Provenance", "", "Coinbase daily closes.",
    ])
    out, n = PH.rewrite_text(baseline, None)
    ok("R19", "the baseline keeps its price table and provenance", "| XRP | 369 | 1.2345 | 1.4567 |" in out and "Coinbase daily closes." in out)
    ok("R20", "and loses the whole portfolio section, total to actions",
       "2,468" not in out and "789.12" not in out and "TRIM" not in out and "Removed 2026-09-05" in out)

    toks = PH.tokens_from_text("qty 1234.5678 at 0.3210 on 2026-09-05; port 5001; total 12,345.67; small 12.5; round 10000")
    ok("T1", "a distinctive quantity is a token", "1234.5678" in toks)
    ok("T2", "a comma amount yields both spellings", "12,345.67" in toks and "12345.67" in toks)
    ok("T3", "a year, a port, a round thousand and a short number are not tokens",
       not ({"2026", "5001", "10000", "12.5"} & toks), sorted(toks))
    shape = PH.tokens_from_text("fee 100.00 cap 2500.0 rate 0.0500 lot 12000.0 real 10234.5")
    ok("T5", "trailing-zero shapes are not tokens; a real five-digit value is",
       shape == {"10234.5"}, sorted(shape))
    ok("T6", "tokens never run on market data, vendored code or the model",
       not PH.tokens_allowed("realdata/deep/XRP.csv") and not PH.tokens_allowed("vendor/three.min.js")
       and not PH.tokens_allowed("fallback_model.json") and PH.tokens_allowed("docs/DAILY_CHECK.md"))
    rx = PH.token_regex(toks)
    out, n = PH.rewrite_text("cost 1234.5678 and 12345.67 and 1234.56789 and x1234.5678", rx)
    ok("T4", "tokens are replaced whole-word only",
       out.count(PH.PLACEHOLDER) == 2 and "1234.56789" in out and "x1234.5678" in out, out)

    ok("M1", "masking shows only the first two and last digit", PH.mask("1234.5678") == "12*****8 (8d)", PH.mask("1234.5678"))
    ok("M2", "an email is masked to its first letter and domain", PH.mask_email("someone@example.com") == "s***@example.com")
    ok("M3", "the tool contains no dollar figure of its own",
       not __import__("re").search(r"\$[0-9][0-9,]{2,}", open(PH.__file__, encoding="utf-8").read()))

    ok("X1", "the tool and its own test are exempt from the content rules",
       not PH.rules_allowed("test_purge_tool.py") and not PH.rules_allowed("tools/purge_history.py") and PH.rules_allowed("docs/DAILY_CHECK.md"))
    out, n = PH.rewrite_text("the $1,234 sleeve", None, "test_purge_tool.py")
    ok("X2", "a rule does nothing inside the exempt test file", n == 0 and "$1,234" in out)
    ok("X3", "a sibling folder whose name begins with the repo name is OUTSIDE the tree",
       not (os.path.normcase(os.path.abspath(os.path.join(HERE, "..", os.path.basename(HERE) + "-backup"))).startswith(
            os.path.normcase(os.path.abspath(HERE)).rstrip(os.sep) + os.sep)))

    print("PURGE-TOOL: %d/%d passed" % (N - len(FAILS), N))
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
