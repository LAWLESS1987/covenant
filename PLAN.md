# Cross-referenced against the field

Looked at the three most-used open-source trading projects and compared them to
what you already have. Sources are their own repos and docs, not review sites.

| | stars | licence | what it is |
|---|---|---|---|
| **Freqtrade** | 52.1k | GPL-3.0 | Python crypto bot: backtest, hyperopt, dry-run, FreqAI |
| **NautilusTrader** | 24.1k | LGPL-3.0 | Rust engine, research-to-live parity |
| **Hummingbot** | 19.5k | Apache-2.0 | market making + arbitrage, $34B user volume |

---

## The three findings that matter

### 1. The biggest project in the space refuses to claim it works

Freqtrade's own README, verbatim:

> "This software is for educational purposes only. Do not risk money which you
> are afraid to lose. USE THE SOFTWARE AT YOUR OWN RISK. THE AUTHORS AND ALL
> AFFILIATES ASSUME NO RESPONSIBILITY FOR YOUR TRADING RESULTS."

And:

> "Always start by running a trading bot in Dry-Run and do not engage money
> before you understand how it works and what profit/loss you should expect."

52,000 stars, years of development, thousands of users — and the flagship
project's first instruction is *paper trade first* and its second is *we promise
nothing*. That is the field's own verdict on the base rate, and it matches what
your two assets showed independently.

### 2. Their optimiser has the exact flaw your backtester already corrects

Freqtrade's **hyperopt** searches thousands of parameter combinations for the
best backtest. Its documentation covers reproducibility, precision limits, and
troubleshooting — but does **not** prominently warn that an optimised result
usually fails to transfer to live trading.

That omission is the single most expensive thing in retail algo trading. Search
N combinations and the best one looks brilliant on pure noise, guaranteed. The
correction is to penalise the winner by how many things you tried — deflated
Sharpe, Bailey & López de Prado.

**`quant/covenant_backtest.py` already implements this. Freqtrade's hyperopt does
not surface it.** On the thing that decides whether a strategy is real, what you
have is stricter than the 52k-star project.

### 3. Hummingbot is the only one with a non-prediction edge — and it is out of reach

Market making earns the **bid-ask spread**. No forecast required, structurally
different from everything that failed your out-of-sample tests. Same category as
the rebalancing bonus.

But it needs **maker rebates and volume**. Your Kraken tier pays 0.40% taker /
0.23% maker; rebates only appear above roughly $5M in 30-day volume. At this scale of capital, market making pays fees to provide liquidity. Real edge, wrong scale.

---

## What this changes

**Stop building execution infrastructure.** Order retries, partial fills,
exchange quirks, rate limits — Freqtrade and Nautilus have solved this over
years. `execute.py` and `paper_run.py` should stay thin: compute the orders,
seal the signals, hand off. They already do.

**Keep the validation layer.** It is the genuinely differentiated part:

| | you | Freqtrade | Nautilus |
|---|---|---|---|
| deflated Sharpe / trial penalty | **yes** | no | no |
| out-of-sample split enforced in workflow | **yes** | manual | manual |
| hash-chained sealed forward signals | **yes** | no | no |
| mature exchange abstraction | no | **yes** | **yes** |
| battle-tested order execution | no | **yes** | **yes** |

Nobody else seals forward predictions in a tamper-evident journal. That is worth
more than another indicator, because it is the only thing that can tell you
afterwards whether you actually knew something.

**Adopt one idea from Nautilus: research-to-live parity.** Same code path in
backtest and live, so a strategy cannot behave differently in production than it
did in test. `paper_run.py` and `execute.py` already share the rule logic — keep
it that way, and never let a "live-only" branch creep in.

---

## The plan

1. **Paper first, and it is not a formality.** The field's most-used bot opens
   with this instruction. 30+ sealed signals, then look.
2. **Any strategy must clear the deflated-Sharpe gate before it touches money.**
   You already have the gate. Use it as a gate, not a report.
3. **Do not run hyperopt-style parameter searches.** More variants make the
   result worse, not better — each one raises the bar the winner has to clear.
4. **Risk rules stay mechanical.** The 20% cap and cash floor need no forecast
   and are the only part with evidence behind them (~3× drawdown reduction,
   replicated on both assets tested).
5. **Revisit market making at a different scale**, or not at all. Honest edge,
   wrong account size.

## The uncomfortable part

Three projects, 95,000 stars between them, $34 billion in routed volume — and
not one claims its users make money. The most-used bot in the category leads
with a disclaimer and an instruction to trade on paper.

That is not a reason to stop. It is a reason to be exact about what you are
buying: better risk control and smaller drawdowns are real and achievable.
Reliable profit from short-term prediction is not, and every serious project in
this space declines to claim otherwise.
