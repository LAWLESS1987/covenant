# Daily portfolio check — standalone runbook

This is executed by a scheduled task each morning in a **fresh session with no
memory**. Everything needed is in this document. Follow it exactly.

Owner holds crypto on Kraken and elsewhere. **Nothing here trades.** The output
is a suggestion the owner acts on by hand, or ignores.

---

## 1. Holdings

```
SYMBOL   QUANTITY      AVG_BUY     NOTE
XLM      <qty>    <avg_buy>
SOL         <qty>  <avg_buy>
WLFI     <qty>      <avg_buy>      only ~110d of history; line is 110d not 200d
XRP       <qty>    <avg_buy>
ADA       <qty>   <avg_buy>
CC       <qty>      <avg_buy>      NOT tradable on Coinbase — price by hand, see §5
CRO      <qty>       <avg_buy>
ONDO      <qty>      <avg_buy>
HBAR     <qty>      <avg_buy>
PEPE   <qty>          <avg_buy>
CASH        <qty>          <avg_buy>
```

## 2. Regime lines — recomputed 2026-08-22, and a correction to how they age

`daily.py` computes the line itself from the window it just fetched, so this
table is **not** an input to it. Keep it for one purpose only: rule 3 needs a
previous state to say what *changed*. Compare against the "state 08-22" column.

| symbol | line (200d) | state 08-22 | price 08-22 | state 08-19 | price 08-19 | |
|---|---|---|---|---|---|---|
| XLM | 0.172958 | **ABOVE** | 0.198716 | BELOW | 0.170252 | **flipped** |
| SOL | 81.15230 | ABOVE | 93.75 | ABOVE | 85.34 | |
| XRP | 1.275320 | **ABOVE** | 1.4888 | BELOW | 1.1054 | **flipped** |
| ADA | 0.223836 | **ABOVE** | 0.22482 | BELOW | 0.18702 | **flipped** (0.4% over) |
| ONDO | 0.315602 | ABOVE | 0.36973 | ABOVE | 0.34702 | |
| CRO | 0.066157 | BELOW | 0.06027 | BELOW | 0.0488 | |
| HBAR | 0.084363 | BELOW | 0.07665 | BELOW | 0.07058 | |
| PEPE | 0.00000333615 | **ABOVE** | 0.00000399 | BELOW | 0.00000288 | **flipped** |
| WLFI | 0.075889 (200d) / 0.059041 (110d) | BELOW | 0.05879 | ABOVE | 0.06142 | **flipped** |

Computed two independent ways and reconciled: from the verified Kraken series in
`realdata/deep/` (hashes in `IMPROVEMENT_LOG.md` D1) and from Coinbase's own 200
settled closes. **The two agree to ≤ 0.02% on every symbol** — that agreement is
the evidence the lines are right, not the fact that a script printed them.

### THE CORRECTION — the old freshness rule measured the wrong thing

The previous version of this section said the lines drift "roughly 0.3–0.8% per
week" and that the table could be trusted for **14 days**. The drift figure is
right. The conclusion drawn from it is not, and three days were enough to show
why:

| | measured over 08-19 → 08-22 |
|---|---|
| line drift | −0.38% to +0.31% — as advertised, negligible |
| **states flipped** | **5 of 9** (XLM, XRP, ADA, PEPE BELOW→ABOVE; WLFI ABOVE→BELOW) |

The line is the slow number; the **state** is what the rules act on, and it is a
*comparison* — it flips the moment price crosses, however still the line is. XRP
moved +34.7% in three days. **So: never read a stored state as current.**
Recompute the line from today's window every run (which `daily.py` does), and
use this table only for the "what changed?" half of rule 3.

### WLFI needs two lines, and the reason is not drift

WLFI's line reads +28.8% against the 08-19 table. That is **not** the average
moving; it is the *window* changing — the old figure was a 110-bar mean and
enough history now exists for 200. The mean is strongly window-dependent
(110-bar 0.059041, 200-bar 0.075889, 355-bar 0.113809 — all today, same data),
so quoting one number without its bar count is meaningless. Both are given
above. WLFI is BELOW on **every** window length, so the flip itself is real —
but on the 110-bar convention it is only 0.4% below, which is exactly the
"sitting near its line" case rule 3 says is not a signal.

## 3. Fetching today's prices — RUN THE SCRIPT

```
python daily.py                 # Coinbase, verified against Kraken
python daily.py --push TOPIC    # and push the phone summary
python daily.py --source kraken # if Coinbase is unavailable
```

`daily.py` does everything this section used to describe by hand — the fetch,
the four checks below, the forming-bar rule, the cross-venue check, the 20% cap
and cash floor, and the circuit breakers — and it holds no key and cannot trade.
Prefer it. Doing it by hand is for when the script itself is what you doubt.

### CORRECTION 2026-08-22 — the network was never the problem

`DAILY_CHECK_CLOUD_BLOCKER.md` recorded two scheduled runs (08-20, 08-21) that
reported **no prices at all**, and concluded the cloud sandbox cannot reach a
price API: *"proxy returns 403 Forbidden at the tunnel for
api.exchange.coinbase.com, api.coinbase.com, and api.kraken.com."*

Re-measured from the sandbox on 2026-08-22 with plain `urllib`:

```
api.kraken.com/0/public/Time                    HTTP 200
api.kraken.com/0/public/OHLC?pair=XXLMZUSD…     HTTP 200
api.exchange.coinbase.com/products/XLM-USD/…    HTTP 200   (23 004 bytes)
api.coinbase.com/v2/prices/XLM-USD/spot         HTTP 200
```

All four. **What actually failed was `WebFetch`**, which raises a one-time URL
permission prompt that nobody is present to approve in an unattended run —
`PROVENANCE_REQUIRED`. The runbook sent the reader to a URL, the reader reached
for the summarising tool, and the tool asked for a human. `daily.py` has always
used `urllib` and would have worked on both mornings. **So: fetch with `urllib`
from Bash. Never use WebFetch for prices.**

The old "do not request the full series in one call" warning belongs to that
same summariser (M1/M24): it dropped rows and altered values. A direct `urllib`
call returns the series intact — verified byte-for-byte against Kraken, and the
200-bar means from the two venues agree to ≤ 0.02% (§2).

### If you are doing it by hand

```
https://api.exchange.coinbase.com/products/{SYM}-USD/candles?granularity=86400
    element = [time, low, high, open, close, volume]      close is index 4
https://api.kraken.com/0/public/OHLC?pair={PAIR}&interval=1440&since={epoch}
    element = [time, open, high, low, close, vwap, volume, count]   close is index 4
    pairs: XLM=XXLMZUSD  XRP=XXRPZUSD  everything else is SYM+USD
```

Verify every window before using it — all four, every time:

- consecutive timestamps differ by exactly `86400`
- no duplicate timestamps
- no zero or negative prices
- the newest timestamp is today or yesterday — **if it is older, the read is
  broken; refetch, and if it fails again say so rather than reporting the
  numbers**
- if the newest bar is today's, drop it — it is still forming

**And then the fifth check, which is the only one that catches a window that
passes the other four.** The 70-day-stale series of `PRICE_DATA_INTEGRITY.md`
was internally perfect: contiguous, no duplicates, all positive. Every check
above is internal to one response, so none of them could see it. Compare the
last **settled** close against the other venue: they should agree to well under
1% (measured across all nine symbols on 2026-08-22: worst PEPE 0.292%). If they
disagree by more than 1%, **do not pick one** — report the symbol as unpriced.
There is no way to tell which venue is wrong, and a wrong price does not just
misprice its own line, it mis-sizes the 20% trim on every other holding.
Compare settled closes only; live prices differ between venues legitimately.

## 4. The rules

1. **20% cap.** No single coin above 20% of portfolio value. Over → trim the
   excess. Also hold a **10% cash floor**.
2. **Regime.** Above its line: may hold and add. Below: hold, do **not** add.
3. **Act on changes, not noise.** Only flag a coin whose state *changed* versus
   §2. A coin sitting near its line will cross repeatedly — that is expected and
   is not a signal.
4. **Never average down.** Do not suggest buying more of anything below its line.
5. No claim of a profit edge. Ever. See §6.

## 5. CC (Canton)

Confirmed 2026-08-20 across four Coinbase endpoints: **not tradable on
Coinbase.** Their price page carries the wording "Canton is not tradable on
Coinbase" and showed $0.09105. Use $0.09105 as a hand-entered price, label it as
hand-entered, and note it may be stale. Do not fetch CC-USD — it 404s.

There are impostor tokens using the Canton name, including a Solana one whose
address ends in `pump` (a memecoin-launchpad marker). Never suggest adding to CC.

## 6. What to say, and what never to say

Push a **short** phone summary (under 200 characters): portfolio value, any
rule action, any regime change. If nothing changed, say so plainly — "no action,
all rules satisfied" is a complete and useful answer, and most days it is the
true one.

Never state or imply that these rules predict price or produce profit. Tested
properly, **no timing edge survived out-of-sample** — on 598 bars across ten
held assets the bootstrap p-values run 0.47–0.92 and deflated Sharpe is 0.000
everywhere (`TRADING_READINESS.md` §1b).

**CORRECTED 2026-08-22 — the "~3× drawdown reduction" claim in the previous
version of this section is not supported.** Measured on the deep data, drawdown
reduction is 2.1× on SOL, 2.2× on ADA, 1.8× on XRP, 1.7× on PEPE/ATOM/AVAX,
1.4× on CRO — and **none at all on XLM (0.9×), NEAR (0.9×) or ONDO (0.6×)**,
where the rule whipsawed 9, 11 and 18 times and lost MORE than simply holding.
Three of ten is not a tail. So the honest sentence is: *the regime rule is risk
control on most of this basket and actively harmful on some of it, and it is
never a return edge.* Do not assume drawdown protection for an asset it has not
been measured on.

## 7. Hard limits — do not cross these

- **Never** place, prepare, or offer to place a trade. The owner places every
  order by hand.
- **Never** ask for, store, or use an exchange API key with trade or withdrawal
  permission. A "Query Funds"-only Kraken key is the maximum, and it lives at
  `C:\Users\<user>\.kraken\credentials` — **outside** the cloud-synced folder.
- **Never** touch, request, or record the Ledger recovery phrase or passcode.
  There is no legitimate reason to ever type those anywhere.
- The synced folder `C:\Users\<user>\covenant` leaves the machine. Nothing secret
  goes in it.
