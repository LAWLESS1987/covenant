# The strategy space, scanned. 2026-09-07

**Asked:** *"scan all known crypto trading strategies."*

**The trap in that sentence, named first, because this project already measured
it.** A scan of *variants* is guaranteed to produce a winner and guaranteed
that the winner is noise. `QUANT_README.md`: 150 variants on a **provable
random walk** returned +144.70% at Sharpe 1.10 with an edge of exactly zero.
`strategy_lab.py` prints the rule every time it runs: *"More variants make this
WORSE, not better — each one raises the luck benchmark the winner has to
clear."* And `strategy_cross_sectional.py` measured PBO **0.986** — a 98.6%
probability that the best in-sample config underperforms out of sample.

So this is a scan of **families**, not variants: what exists, what has been
tested here, what is structurally reachable by a $3,889 spot-only account, and
what information each one needs. Sorted by the only axis that has ever mattered
in this project's own results — `strategy_lab.py`'s closing line: *"Refining
further means NEW INFORMATION (a different data source, a real structural
insight), not more knobs on the same price series."*

---

## Group A — same information (past prices of the assets already held)

**Every one of these is a different arrangement of one input: this book's own
price history. All tested here. All dead.**

| family | tested by | verdict |
|---|---|---|
| Trend / momentum — SMA, EMA, MACD, Donchian, breakout | `strategy_validate.py` (~800 variants), intraday run (848) | DSR 0.0000 |
| Mean reversion — RSI, Bollinger, z-score | same searches | DSR 0.0000 |
| Cross-sectional momentum / relative strength | `strategy_cross_sectional.py`, 288 variants | **PBO 0.986** |
| Pairs / cointegration / statistical arbitrage | `strategy_pairs.py` | no survivor |
| Regime filter — 200-day line | `d2_regime_deep.py`, 10 assets | p 0.47–0.92, DSR 0.000 |
| Rebalancing / variance harvesting | `d2_rebalance_deep.py` | mechanical only; 95–97% of its trades violate rule 4 |
| Volatility breakout / ATR channels | inside the breakout family above | DSR 0.0000 |
| Grid trading | — | mean reversion with a worse risk profile; same input |
| Martingale / averaging down | — | rule 4 forbids it, and correctly: it converts small losses into one large one |
| Chart patterns — Elliott, Fibonacci, Ichimoku, candlesticks | — | same price series, no independent information; nothing here to test that the above has not covered |
| DCA | — | not alpha. A schedule that removes timing decisions, which is a behavioural benefit, not an edge |

**Group A is exhausted.** Five mechanism classes, well over 1,900 variants,
nothing surviving deflation and walk-forward together — including at zero
modelled cost, which rules out fees as the explanation.

## Group B — different information, genuinely untested here

These are the only price-adjacent families that bring in something the searches
above have never seen. Each is a **research project**, not a config change.

| family | information needed | reachable? | honest base rate |
|---|---|---|---|
| On-chain — exchange in/outflows, active addresses, stablecoin supply, whale moves | free-to-cheap APIs | yes | widely mined; edges decay fast once published |
| Sentiment / social / NLP | scraping or a paid feed | yes | very noisy; heavily arbitraged |
| Order-book microstructure — order-flow imbalance, queue position | L2 book data | data yes, **execution no** | latency-bound; a daily Python task on a sleeping Windows box cannot compete |
| Derivatives-derived signals — funding rate, open interest, options skew as *inputs* | free public APIs | **yes, without trading perps** | the most interesting untested item: real positioning information, and you can read it while staying spot |

If any Group A search is ever revisited, it should be with one of these as a
new input — not with more knobs.

## Group C — structural, not predictive

**This is where returns for an account this size actually live, and most of it
is not trading at all.** No forecast required.

| family | what it needs | fit here |
|---|---|---|
| **Staking / yield on assets already held** | nothing new | SOL, ADA, HBAR and others in the locked book are stakeable. Requires no edge, no prediction, no gate, no automation. **Never measured in this project.** |
| Funding-rate / basis arbitrage (delta-neutral) | perps + spot, both sides funded | the one structural trade with a real mechanism — but `venues.py` is **spot only**, and it carries liquidation and stablecoin-depeg risk. Vendor-quoted "8–20% APY" figures are marketing, not measurement |
| Cross-exchange arbitrage | capital on both venues, speed | effectively institutional now; the spread is gone before a retail order lands |
| Market making / maker rebates | volume tier + inventory + latency | locked out: the fee tier is a function of volume this book cannot generate |
| Airdrop / points farming | capital at risk in new protocols | real but lottery-shaped; not a strategy, and a smart-contract risk the constitution does not cover |
| Fee-tier optimisation | volume | structurally unavailable at $3,889 |

## Group D — disqualified by this system's own constraints

Leverage, margin, perpetuals, shorting (measured **worse** on every matched
pair, 2026-09-07), anything sub-second, anything needing six figures for tier
access. `venues.py` holds spot adapters only, and the risk frame — position
cap, cash floor, never average down — is built for a world where the worst case
is zero.

---

## What the scan actually says

1. **Group A is finished.** Not "hasn't worked yet" — measured to exhaustion,
   across five mechanism classes and two timeframes, including at zero cost.
   More searching there is how you find noise, and this project has the
   receipts to prove that specific claim about itself.
2. **Group B is the only honest direction left** for a price-adjacent
   strategy, and the entry cost is real research on new data, not a new
   indicator. Funding rate and open interest as *read-only inputs* are the
   cheapest first step: free data, no new venue, no new risk.
3. **Group C is where the arithmetic favours a book this size**, and the
   highest-expected-value item on the whole page is probably the least
   exciting: **staking assets already held and not selling them.** It needs no
   edge, no gate, and no trader. It has never been measured here, which makes
   it the largest untested item in the project — larger than any strategy in
   Group A ever was.

**A caution on sources.** A web scan for this was run on 2026-09-07 and
returned mostly vendor and content-farm material — "strategies that actually
work in 2026", "backtested", quoted APYs with no methodology. None of it is
evidence and none of it is cited as such. The measurements in Group A above are
this project's own, on its own data, at its own costs, and they are the only
numbers here worth acting on.

**Not advice.** This maps a space against this account's constraints. Staking,
perps and new protocols each carry risks — lockups, slashing, liquidation,
depeg, smart-contract failure — that are outside anything this project has
modelled, and choosing among them is the owner's call, not a run's.
