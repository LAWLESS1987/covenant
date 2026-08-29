# Improvements found — 2026-08-29 (trading, and memory)

Research pass against the code as it actually is, not as the docs describe it.
Everything below was checked against the tracked tree first; where the finding
is "this is missing", the grep that establishes it is given.

---

## 1. TRADING

### 1.1 The finding: Rule 1 is half-built

`MY_STRATEGY.md` opens with RULE 1 — *"Size by volatility, not by conviction"* —
and calls it **"the only lever in this document with a guaranteed, arithmetic
effect. Everything else is probabilistic."** It is the first rule for a reason.

Rules 2 and 3 (the 200-day regime switch, acted on only when it FLIPS) **are**
implemented — `covenant_trader.py:233,247,286`, `daily.py`, `d2_regime_deep.py`.

Rule 1's second clause is not. Searched across every tracked `.py`:

    git ls-files '*.py' | xargs grep -liE \
      'target_vol|vol_target|volatility.?target|inverse.?vol|risk.?parity|atr.?size|vol.?scal'
    -> no matches

Position size today is decided by three **static** constraints:

| where | what |
|---|---|
| `guards.py:134` `ConcentrationCap(0.20)` | no single asset above 20% |
| `guards.py:169` `CashFloor(0.10)` | keep 10% cash |
| `covenant_trader.py:258` `cfg["max_position_pct"]` | a fixed cap |

Realized volatility is computed in exactly one place — `covenant_backtest.py:190`,
`statistics.pstdev(self.returns)` — and it is used for the Sharpe ratio, never
for sizing. So the strategy holds a fixed 20% of a coin whether it is running at
40% annualised or 120%. The document's first and strongest rule is a comment.

### 1.2 The pushback: do NOT implement naive vol-targeting expecting free returns

This is where the obvious fix meets evidence that argues against it, and the
evidence deserves to win.

Moreira & Muir (2017) is the paper everyone cites for volatility management. It
has been substantially challenged. Cederburg, O'Doherty, Wang & Yan, *"On the
performance of volatility-managed portfolios"*, **Journal of Financial Economics
138(1), 2020, 95-117**, found that **reasonable out-of-sample versions generally
earn LOWER certainty-equivalent returns than the unmanaged portfolios.** The
in-sample alphas depend on knowing future return moments; the underlying
regressions carry "substantial structural instability".

What survived their test was narrow — and it happens to be the relevant case:

> **momentum**, profitability, and betting-against-beta.

Volatility management worked there because *volatility is persistent for
momentum*. This project runs a 200-day trend rule. That is the one family where
the effect replicated.

**So the honest framing, which is also the one this project's own evidence
already supports:** vol-scaling is not a return enhancer and must not be sold as
one. It is a *drawdown* instrument. Drawdown reduction is the single effect that
replicated across XRP and HBAR here (3.0x and 3.4x). Scaling exposure inversely
to realized vol serves that specific, already-evidenced objective, on the one
factor family where the literature says it survives out of sample.

Implement it as a risk control with a measured drawdown target. Do not put a
return number on it. If a backtest of it shows improved returns, that is the
signal to distrust the backtest — which is what §1.3 is for.

### 1.3 The missing statistic: Probability of Backtest Overfitting

`covenant_backtest.py` already implements more discipline than most production
systems: `deflated_sharpe` (Bailey & Lopez de Prado), `min_track_record_length`,
`walk_forward`, `PointInTimeView` + `LookAheadError`, an embargo, and a
`CostModel` (10 bps taker, 5 spread, 5 slippage).

One thing is missing, and it is the one that measures what was actually observed:

    deflated_sharpe        6 hits
    min_track_record       present
    walk_forward           present
    embargo                5 hits
    probabilistic_sharpe   0
    PBO / overfit          0
    minimum_backtest       0

The d6 run measured "top-10 chosen on train -> -2.70% / -7.06% out of sample"
and computed a permutation p-value for it. **PBO is the standard statistic for
exactly that phenomenon** — the rate at which the in-sample-optimal strategy
lands below the out-of-sample median.

CSCV, per Bailey, Borwein, Lopez de Prado & Zhu:

- Input: a `T x N` matrix of per-period returns — T observations, N configurations.
- Partition T into **S = 16** disjoint blocks (the paper's recommended default;
  it preserves serial-correlation structure and, on daily data, is roughly
  quarterly).
- Form all `C(16, 8) = 12,870` train/test splits from complementary halves.
- For each: find the in-sample best, take its out-of-sample **rank**, convert to
  a logit. **PBO = the fraction of splits where that logit is below zero.**
- Requirements: `N >> 10`, and T about double what the investor would use.

**This fits the existing grid exactly.** The d6 battery is N = 53 variants over
T = 408 bars — N >> 10 holds comfortably; S = 16 gives ~25 bars per block. The
return series per variant are already produced by `Backtester.run`. It is a
matrix reshape and a rank count, not new infrastructure.

Predicted result, recorded now so the run can falsify it: **PBO will come back
high — above 0.5.** The -2.70% / -7.06% out-of-sample readings and the near-1
p-values (0.656, 0.891) say train rank carried no information. If PBO comes back
*low*, something is wrong with the implementation, not with the strategy.

### 1.4 `minimum_backtest_length` answers a question already asked here

`d6_hbar_clean.py` records: *"349 bars could not support walk-forward folds at
warmup 74; 408 still cannot: (4+1)*(74+30)=520 > 408."* That is minBTL reasoning
done by hand. Bailey & Lopez de Prado's `minBTL` formalises it: given N trials,
how many observations are needed before a Sharpe of a given size is not expected
from chance alone. Worth having as a gate that refuses to report a result rather
than a note in a docstring.

### 1.5 Library: `purgedcv` — useful, but read before depending

`github.com/eslazarev/purged-cross-validation` (`pip install purgedcv`), MIT,
Python 3.10-3.14, scikit-learn-compatible. Provides `WalkForwardSplit`,
`PurgedKFold`, `PurgedGroupKFold`, `CombinatorialPurgedCV`,
`CombinatoriallySymmetricCV`, plus `probability_of_backtest_overfitting`,
`deflated_sharpe`, `probabilistic_sharpe`, `minimum_backtest_length`,
`effective_n_trials`.

**Caveat, stated because this project's standard demands it: ~24 stars, 5 forks.**
That is a thin dependency for a repo whose gates refuse unmeasured claims, and it
would be the first third-party analytics dependency in a codebase that hand-rolled
its own `deflated_sharpe` rather than import one. Two defensible routes:

- **Read it as a reference implementation and write PBO locally** (~80 lines: a
  reshape, `C(16,8)` iteration, a rank, a logit). Keeps the zero-dependency
  posture that chose waitress over gunicorn. **Recommended.**
- Or take the dependency for the CV splitters only, and keep the statistics local.

`pypbo` (`github.com/esvhd/pypbo`) is the older reference for PBO specifically;
also worth reading rather than importing.

---

## 2. MEMORY

### 2.1 The judge is the memory risk, and this repo already found it

`judge_bench.py:148` `fit_check()` is one of the sharpest things in this codebase:

> Ollama cannot allocate the weights, returns HTTP 500, the judge fails closed,
> and EVERY transaction is rejected -- with a reasoning string that says
> "semantic judge error", buried where nobody reads it. Observed on a 7GB box
> asked to load a 9.3GB model:
>
>     ggml_aligned_malloc: insufficient memory
>     (attempted to allocate 8589.04 MB)  -> HTTP 500 -> 3/6
>
> **3/6 is the tell, and it is a trap: a gate that rejects everything scores
> exactly right on every case that SHOULD be rejected. It does not look broken.
> It looks strict.**

That is the whole memory problem in one paragraph, already diagnosed. Nothing
below improves on the diagnosis; it hardens the margin.

### 2.2 The margin, measured

`LEAN_MEASURE.txt`, 2026-08-22:

    TotalVisibleMemorySize   16,056,316 KB   (~15.3 GB)
    FreePhysicalMemory        5,893,984 KB   (~5.6 GB)

The three node `python.exe` processes were ~10 MB each and `ollama.exe` 20 MB —
i.e. the model was **not resident** at that moment. When qwen3:8b loads, it wants
several GB on top of that. ~5.6 GB free against an 8b model is not comfortable
headroom; it is roughly the same shape as the 7GB-box failure above, and whether
it fits depends on quantization and on what else is open.

### 2.3 What to change, cheapest first

1. **Pin the quantization and put it in `fit_check`.** An 8b model at `Q4_K_M`
   is roughly half the resident size of `Q8_0` for a small quality cost — the
   difference between comfortable and marginal on a 16 GB box. `fit_check` today
   compares the model size Ollama reports against available RAM; have it also
   *name the tag* it expects, so a silent re-pull to a bigger quant is caught by
   the same check rather than at 3am by a node rejecting every transaction.
   This also closes a P15 gap: `test_p15_judge_identity.py` already alerts on a
   digest change — a quant change IS a digest change, so the alarm exists; it
   just needs the fit consequence attached to it.

2. **Set `OLLAMA_KEEP_ALIVE` deliberately.** The default unloads the model after
   a few minutes idle. For a judge that fires irregularly, that means a
   multi-second reload on the critical path of a consensus gate, and a
   load-time allocation spike exactly when memory is tightest. Either keep it
   resident (`OLLAMA_KEEP_ALIVE=-1`, costs steady RAM, removes the spike) or
   accept eviction and make the timeout explicit. The bad case is the default,
   because it is neither and it is invisible.

3. **`OLLAMA_MAX_LOADED_MODELS=1`.** Prevents a second model being resident
   concurrently. On a box with this margin, one concurrent load is the
   difference between fitting and HTTP 500.

4. **`num_ctx` is already right and already reasoned.** `covenant_judge_ollama.py`
   pins 2048 with the argument "the prompt is ~500 tokens; anything larger just
   allocates KV cache you will never fill", and `_check_context` refuses a
   verdict computed on a truncated prompt. Do not raise it casually — KV cache
   scales with context, and this is the one dial that silently trades correctness
   (front-of-prompt truncation drops the principles) for memory.

### 2.4 The other reading of "memory"

If what was meant is the *knowledge* memory rather than RAM — the 2 MB project
cap that this same day nearly destroyed 24 documents — that is written up in
`docs/sessions/PROJECT_IS_NOT_A_BACKUP.md` and in the project itself. The short
version: capacity was never the problem, undeletability was, and publishing to
GitHub fixed it structurally.

---

## 3. Incidental: ten branches are not on GitHub

`git branch -a` shows eleven local branches and **only `main` on origin**:

    chore/normalise-line-endings          fix/restore-captured-output-bytes
    docs/correct-missing-suite-count      fix/sweep-uses-project-venv
    docs/withdraw-unverified-suite-totals fix/tally-counts-failures-as-passes
    feat/one-command                      fix/test-runner-deletes-node-keys
    fix/remove-phantom-suites             p9/platform-correct-owner-only

All eleven are merged into `main`, so no *content* is at risk. But the branch
refs — and the history of why each change was made separately — exist on one
disk. `git push origin --all` costs nothing and completes the redundancy.

---

## Order I would take these

1. `git push origin --all` — one command, finishes the redundancy already started.
2. PBO on the existing 53 x 408 grid. It uses data already collected, adds no
   dependency, and it either confirms the strategy's own honest conclusion or
   overturns it. Highest information per unit of work.
3. `OLLAMA_KEEP_ALIVE` + `OLLAMA_MAX_LOADED_MODELS`, and the quant tag pinned
   into `fit_check`. Small, and it protects a gate that fails silently-strict.
4. Volatility-scaled sizing, built as a drawdown control with an explicit target,
   validated by CPCV rather than a single split — and with the Cederburg result
   written into its docstring so nobody later mistakes it for an edge.

---

## OUTCOME — PBO run, same day. Prediction confirmed, but only after the first answer was disbelieved.

§1.3 filed: *"PBO will come back high — above 0.5... If PBO comes back low,
something is wrong with the implementation, not with the strategy."*

`pbo_hbar.py`, CSCV per Bailey/Borwein/López de Prado/Zhu. HBAR 408 bars,
warmup 74, the same 53-variant D6 grid, T=333 returns, S=16 contiguous blocks
of 20, all C(16,8)=12,870 splits, combined-window Sharpe computed exactly from
per-block (n, Σ, Σ²).

**First answer: PBO = 0.3469.** Refuted. So the filed rule was honoured rather
than the number, and the implementation was audited.

**The no-op trap.** Seven of the 53 variants never trade. Scored 0.0 they are
not neutral — they are the **best performers in the grid**, because:

| | |
|---|---|
| variants that trade | 46 |
| of those, with POSITIVE full-sample Sharpe | **0** |
| best | **−0.0299** (`sma_cross 20/72`) |
| worst | −0.1596 |

Zero beats every negative number, so `argmax` picked a no-op in sample *and*
out of sample. PBO 0.347 was a faithful measurement of **"not trading beats
trading"** — true, and not the question PBO asks. PBO asks whether *selection
among strategies* generalises, which is only meaningful over strategies that
trade.

**Corrected, over the 46 live variants: PBO = 0.5440.**

- 7,001 of 12,870 splits put the in-sample-best variant **below** the
  out-of-sample median
- median logit λ = **−0.128** (negative favours overfitting)
- median OOS rank of the in-sample-best variant = **0.468**

**Prediction CONFIRMED.** Choosing a variant on train performance is slightly
*worse* than choosing at random. This is the standard statistic for what D6
already saw anecdotally (top-10 by train → −2.70% / −7.06% OOS, p = 0.656 /
0.891) — now named, and reproducible in one command.

**Both numbers are kept in the script**, because the degenerate one carries the
sharper finding: on 408 verified bars, across 46 trading variants, **the null
strategy outperforms every strategy in the grid.** `MY_STRATEGY.md` says no
profit edge survived deflation. This is stronger — nothing was close, and doing
nothing won.

That is not an argument against the system. It is the argument *for* the one
`MY_STRATEGY.md` already makes: the only replicated effect is drawdown
reduction, and sizing is the lever. It also raises the bar for §1.1's
volatility-scaled sizing — it must be built as a drawdown control and validated
by CPCV, never sold as return improvement, because there is no return here to
improve.


---

## CORRECTION to §2.3 — the memory recommendations were already done, and one was wrong

While staging an `OLLAMA_TUNE.bat`, I overwrote an existing **`ollama_tune.bat`**
(Windows filesystems are case-insensitive, so the two are one file). 93 lines of
prior work, destroyed and then recovered from git. Recorded here rather than
quietly reverted, because what it contained invalidates part of §2.3.

**§2.3 item 3 — `OLLAMA_MAX_LOADED_MODELS=1` — is WRONG for this system.**
`ollama_tune.bat` sets it to **3**, and states the measurement:

> one slot per DISTINCT judge model. At 1, every judge call evicts the previous
> one and pays a full reload: **measured 23.7 s wasted per transaction with
> three judges.**

The quorum runs several judge models. Setting 1 does not protect the memory
margin; it forces eviction thrash on the critical path of a consensus gate. I
reasoned from the margin and ignored that the judge is a QUORUM — the plurality
that `CONSTRAINT_COVERAGE.md` argues is the whole coverage strategy. The two
recommendations contradicted each other and I did not notice.

**§2.3 item 2 — `OLLAMA_KEEP_ALIVE`** — already set, to `30m`, with reasoning
("a 24GB model reloaded per verdict is the difference between seconds and
minutes"). My suggestion of `-1` is defensible but not obviously better, and it
was not new.

**And the file already does more than §2.3 proposed**, all with reasons:

| setting | why, in its own words |
|---|---|
| `OLLAMA_HOST=127.0.0.1:11434` | "Ollama has NO auth: any process or machine that can reach the port can load models and read your prompts. Do not bind 0.0.0.0." |
| `OLLAMA_NUM_PARALLEL=1` | parallel slots each get their own KV cache |
| `OLLAMA_FLASH_ATTENTION=1` | cheaper attention, less KV memory |
| `OLLAMA_KV_CACHE_TYPE=q8_0` | "roughly halves KV cache RAM" |
| `OLLAMA_CONTEXT_LENGTH=2048` | matches the ~500-token judge prompt |
| `ollama_tune.bat undo` | reversible, which mine was not |

**So §2.3 stands only in its first item** — pin the quantization tag into
`fit_check`, which nothing here does. Items 2 and 3 are withdrawn: one was
already done better, the other was actively harmful.

The lesson is the session's own, turned inward: **I recommended a memory fix
without reading the memory tooling that already existed.** `IMPROVEMENTS_2026-08-29.md`
§2 opens by praising `judge_bench.fit_check` for exactly this kind of care, and
I did not extend the same reading to the file sitting beside it.
