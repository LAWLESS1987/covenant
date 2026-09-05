# ALERTS.md -- removed from the repository and its history on 2026-09-05

This file was the owner's alert levels of 2026-08-19: position values,
quantities, a cost basis and the portfolio total, in prose and tables. That
is the owner's private corpus, which the constitution says is never
published, and it had been public since the repository was. The file was
removed from every commit by `tools/purge_history.py`; this stub keeps the
links in `INDEX.md` honest.

What the file did that the project still needs is done elsewhere:

- regime lines and alert levels: `python daily.py` prints the live ones
  (the frozen 2026-08-19 lines had already flipped, per `INDEX.md`);
- the Rule-1 concentration check: `guards.py` and `daily.py`;
- the record of what was exposed and how it was closed:
  `docs/KNOWN_ISSUES.md` issue 15.
