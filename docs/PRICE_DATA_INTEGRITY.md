# Price data integrity — a transport failure worth remembering

**Found 2026-08-20.** Recorded here because it silently produced wrong numbers
and would have done so again.

## What happened

Daily price series were being pulled by fetching the Coinbase candles endpoint
and having a small summarising model read the numbers out of the response. For
long responses (~300 rows) that model **silently drops leading rows and
occasionally alters the first value**. It never errors. The output looks
perfect.

Measured on a single round of four assets, all fetched within seconds of each
other from the same endpoint:

| asset | rows silently dropped | newest bar returned | actual newest |
|---|---|---|---|
| ONDO | 0 | 2026-08-20 | 2026-08-20 |
| ADA | 2 | 2026-08-17 | 2026-08-19 |
| CRO | 4 | 2026-08-14 | 2026-08-19 |
| PEPE | **70** | 2026-06-11 | 2026-08-19 |

Plus first-value corruption: ADA 2026-08-17 came back `0.17358`, true value
`0.17416`. CRO came back `0.04935`, true `0.04838`. WLFI came back `0.06078`,
true `0.06142`.

Consequence had it gone unchecked: a 200-day regime line for PEPE computed
entirely from data ending 70 days earlier, presented as current, and used to
set a buy/sell alert level on a real position.

The stored `HBAR-USD.csv` was already contaminated this way — 70 days stale,
same 2026-06-11 cutoff.

## The tell

Two cheap checks catch all of it:

1. **Compare the newest bar's timestamp against today's date.** A live endpoint
   returning a bar from ten weeks ago is not a data quirk, it is a broken read.
2. **Different assets from the same endpoint ending on different dates.** They
   should all end on the same day. When they don't, the transport is at fault,
   not the market.

## The fix

Fetch in **small explicit windows** (`start`/`end` params, ~55 rows) and verify
each window before trusting it:

- exactly `86400` between consecutive timestamps, no other gap value
- no duplicate timestamps
- no zero or negative prices
- adjacent windows must join seamlessly (`prev_window_end − 86400 == next_window_start`)
- drop the newest bar when it is today's — it is still forming

Re-pulled this way, all nine tradable holdings gave 220-row series with
`gaps=[86400]` and zero duplicates. The HBAR archive's *interior* values were
then spot-checked against a fresh independent pull on six separate dates and
matched to **0.000%** — so only the leading row had been corrupted, and the
archive was salvageable by splicing.

## Where this does NOT apply

`daily.py` running on the user's own machine fetches with `urllib` and parses
JSON directly. There is no summarising model in that path, so it is not exposed
to this failure. The bug was confined to sandbox-side fetching.

## A false confirmation worth flagging

The corrupted WLFI value (`0.06078`) was "cross-checked" against a live Kraken
price (`0.06074`) and declared a 0.07% match. Both numbers were wrong for the
purpose: `0.06078` was corrupt, and the Kraken figure was an intraday live price
being compared against a *settled daily close* — two different quantities. The
agreement was coincidence. **A cross-check only confirms anything if both sides
measure the same thing.**
