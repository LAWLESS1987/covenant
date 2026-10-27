# Execution architecture — decided 2026-08-20

> ## ⚠ CORRECTION 2026-08-22: `execute.py` and `paper_run.py` DO NOT EXIST
>
> This document is written in the present tense about two files —
> *"`execute.py` shells out to `kraken`"*, *"`execute.py` **now** calls
> `kraken balance` first and clamps every order"*, *"`paper_run.py` — sealed
> signals … Tamper-tested: rewriting a sealed price is detected"*. On
> 2026-08-22 the covenant folder was reachable over the device bridge for the
> first time and searched end to end. **Neither file is there.** The only
> nearby file is `paper_bot.py`, which is not the same thing.
>
> They were almost certainly written in a cloud session, delivered by
> SendUserFile, and never saved to disk — the same failure mode that left the
> node source fourteen versions stale (`claude/PC_SYNC_LOOP.md`, M25). The bug
> report about the SOL order sized against a Kraken balance that did not hold
> it is real and worth keeping; **the sentence saying it was fixed describes
> code that cannot be found.**
>
> What this changes:
> - `TRADING_READINESS.md` §2 lines 3 and 4 were never blocked on an upload.
>   They are blocked on code that has to be written.
> - Nothing below has been run against a live `kraken` CLI by anyone but L.
>   Treat the whole document as a **design that was agreed**, not as a
>   description of working software, until the two files exist and have tests.
> - The design itself still stands and is not weakened by this: the split
>   below (cloud computes, L confirms, the local `kraken` binary places) is
>   what the Section-0 boundary requires whether or not any code implements it
>   yet.

Kraken shipped an official CLI (v0.4.1, MIT, Rust) with a built-in MCP server.
That changed what is possible here, so this records the shape and why.

## The split

| layer | where it runs | holds a key? |
|---|---|---|
| compute the orders | cloud session (me) | **no** |
| confirm each order | the user, per order | — |
| place the order | `kraken` on the user's machine | yes, its own config |

`execute.py` shells out to `kraken`. It never reads, stores, or asks for a
credential.

**This is not ceremony.** The cloud session fetches web pages, reads project
docs, and processes tool output continuously — any of which can contain text
crafted to look like an instruction. If that process could also reach a
trade-enabled credential, a poisoned page becomes a market order. Keeping the
key out of its reach makes that impossible rather than unlikely.

Kraken's own guidance agrees: `--allow-dangerous` should be used *"only when the
calling agent is trusted and has been validated through paper trading."*

## MCP defaults (from the binary's own help, not the README)

> "Default exposes read-only services (market, account, paper, workspace).
> Use `-s all` to include trade, funding, futures, earn, subaccount, and auth."

Default list: `market,account,paper,workspace,feedback`. The README understated
this — always read `--help` on the actual binary.

## Bug caught in testing: orders must be clamped to the venue

`holdings.txt` is everything owned across every venue. Kraken can only sell what
is in the Kraken account. The first version sized a sell for <qty> XLM when the
test balance held 900, and generated a SOL order for coins not there at all.

`execute.py` now calls `kraken balance` first and clamps every order, reporting
the gap rather than silently shrinking it:

```
SOL: rule fires but cannot act here -- held elsewhere, not on Kraken
1. SELL <qty> XLM  [clamped: rule wants <qty> but Kraken holds <qty>]
```

## paper_run.py — sealed signals

Appends one hash-chained record per run: the call, the price, the time, sealed
**before** the outcome exists. Editing entry *n* breaks every entry after it;
`--verify` proves the chain. Tamper-tested: rewriting a sealed price is detected.

Guards that must not be removed:

- **Below 30 scored signals it reports NOT ENOUGH DATA** regardless of the
  numbers. A 7-2 record occurs by chance ~9% of the time.
- **Two-sided reporting.** The headline test is one-sided ("better than a coin
  flip"), which reports p=1.000 for a terrible record — technically true and
  badly misleading. A strongly *inverted* result is not a null result; it has
  predictive content pointing the other way and should be investigated, not
  filed as noise.

## Standing constraints

- Never hold, request, or use a trade- or withdrawal-enabled key in the cloud
  session.
- Never touch the Ledger recovery phrase. Unchanged, absolute.
- Credentials live in `~/.config/kraken/config.toml` inside WSL — **never** in
  `C:\Users\<user>\covenant`, which syncs off the machine.
- Never claim a profit edge. Established: no timing edge survived out-of-sample
  on two real assets (XRP −2.70% p=0.656; HBAR −7.06% p=0.891). Only drawdown
  reduction (~3×) replicated.
