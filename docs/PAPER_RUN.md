# `paper_run.py` — the sealed-signal ledger (2026-09-07, second refinement)

**Ask from L:** a plan to pre-generate a trading strategy, seal it to the chain,
then approve each trade by hand — "without forking or changing the core rules."
That proposal is reviewed and declined as stated in
`claude/PREPLAN_REVIEW_2026-09-07.md`; this is the redirect it ends with, built
and then refined. Same machinery — seal before the outcome exists — pointed at
the target the policy already requires instead of at the one the rules forbid.

**Status:** `paper_run.py`, 2,110 lines, schema 2, sha256 `b8f96449cba417a6…`.
`test_paper_run.py` sha256 `7969f425aca77932…`, **270 checks, 270 passed ×2** —
in the cloud sandbox (py 3.11.15) *and* in `C:\Users\Lawre\covenant` itself
(desktop Linux VM, py 3.10.12), byte-identical files both places. Wired into
`run_all_tests.sh`. **NOT run on win32** (M29).

**What it clears:** `TRADING_READINESS.md` §2 line #4 — *"`paper_run.py` has
≥ 30 sealed, settled signals and `--verify` passes"* — whose recorded status was
**"`paper_run.py` does not exist either… Zero sealed signals exist."** The file
now exists. The 30 signals still do not; only ~30 days of running produces
those, and no amount of code substitutes for them.

**What it does NOT clear.** #3b (`execute.py`) is untouched and stays L's call.
#5 (`EdgeMonitor` seeding) still cannot be done honestly — no rule has passed
`evaluate()`, DSR is 0.000 everywhere. #6–#9 are L's. Nothing here is a
recommendation to trade and no profit edge is claimed anywhere in it.

---

## 1. The boundary, stated in code rather than in a comment

`DAILY_CHECK.md` §7 is broader than Section 0 and is the binding text: *"Never
place, **prepare**, or offer to place a trade."* So:

| the rule | how this file keeps it |
|---|---|
| never place | no venue, no key, no order route, no `kraken` call anywhere |
| never **prepare** | records **calls** (`target ∈ {-1,0,+1}` + a reference price), never orders. No quantity, no side, no order type, and no function that could produce one |
| never offer | the report's footer states it is a measurement, not a recommendation; the suite greps the output and fails if the words BUY or SELL ever appear |
| no credentials | four public market-data endpoints, nothing else; no credential file is read |
| no edge claim | `--report` prints "not a claim of a profit edge" every time, and refuses a headline below 30 signals |
| no scope widening | refuses to run at all if `TRADING_POLICY.json` says `mode != "paper"`, `funded: true`, or `runtime_unlock_allowed: true` |

The policy is read **before** anything is sealed, per `TRADING_POLICY.json`'s own
header: *"execute.py and paper_run.py read this BEFORE generating any order. A
note in a markdown file is a wish; this is a lock."* That sentence names this
file. It is honoured literally, and it fails closed: a missing or unparseable
policy is `UNAVAILABLE` (exit 2), never a default.

---

## 2. The integrity mechanisms

`covenant_backtest.py` states the property: *"the decision is recorded BEFORE
the outcome bar exists, and is immutable afterwards."*

1. **Append-only hash chain.** Every record carries the hash of the one before.
   Editing record *n* breaks *n+1* to the end of the file. `--verify` recomputes
   from genesis and names the **first** break by line number and by kind.
2. **Seal and settle are separate records.** The seal is hashed before the
   outcome exists and is never rewritten; the settle is a later record that
   *references* it.
3. **A sealed call cannot be settled twice.** The chain cannot catch this alone
   — a second settle appended through the writer is perfectly chained. It takes
   a domain rule, and B2 proves the domain rule is what catches it.
4. **A settle must be strictly after its seal.** The look-ahead shape: the
   bootstrap helper that used bar *t+1*'s return for a decision at *t*'s close
   and "found" a +112 % XLM edge (`TRADING_READINESS.md` §1b).
5. **The whole chain must be non-decreasing in time.** *(added in the refinement
   pass)* Rule 4 is only as good as the clock that wrote both numbers. A wall
   clock that steps backwards — NTP correction, a DST-mangled RTC, a VM restored
   from a snapshot — would let a settle be written with a timestamp before its
   seal and look perfectly ordered. Enforced at **write** time (`_append`
   refuses a record behind the tip) and again at **read** time, because a file
   can arrive by some other route.
6. **Schema gating.** *(added)* `--verify` reads the genesis record's declared
   schema and refuses a ledger this build does not know, rather than reading old
   records under new rules. Silently reinterpreting a sealed record is the one
   failure a tamper-evident ledger cannot survive.

Appending does a **full verify first**, not a read of the last line. Reading only
the tail would let an earlier break survive every future append and surface
months later with the whole record in doubt.

**Anchoring.** `--tip` prints a bare 64-hex root committing to every call, in
order. *That* is the thing to put on the chain with `covenant_anchor.py` — it
timestamps the record without exposing it and without authorising anything. It
is the half of the original proposal that was always sound. `--tip` refuses a
ledger that does not verify: an anchor of a broken record is worse than none.

---

## 3. Where the ledger lives, and why not in the synced folder

`~/.covenant/paper_ledger.jsonl` (`COVENANT_PAPER_LEDGER` overrides). D4's
reasoning applied to a second file, and both halves apply **more** strongly here
than to `daily_state.json`:

1. `C:\Users\Lawre\covenant` leaves the machine. A dated record of every
   directional call on the whole book is not a key, but it does not belong off
   the box.
2. `covenant_seal.py` hashes every file in that folder and anchors the root.
   **This ledger changes on every run by construction.** Put it in the synced
   folder and the seal is wrong every day — and `PC_SYNC_LOOP.md` already warns
   that *"a tamper-evident seal that is usually wrong teaches its operator to
   ignore it."*

---

## 4. The guards on the numbers

**NOT ENOUGH DATA below 30 scored signals, regardless of the numbers.** Not a
warning beside an encouraging headline: the headline is **withheld**. No win
rate, no p-value, no Sharpe. *A 7–2 record occurs by chance ~9 % of the time* —
the suite asserts that constant exactly (`P(X≥7 | n=9) = 46/512 = 0.0898`) and
B7 lowers the floor to demonstrate what the floor prevents.

**Two-sided reporting.** The one-sided test reports **p = 1.000 for a
catastrophic record**. All three p-values print every time, the two-sided one is
marked `<-- read this one`, and a record whose inverted p clears 0.05 is named
**INVERTED**: it has predictive content pointing the other way.

**A rule that has not fired is no call.** Below the SMA window `regime_target`
returns `None` and `--auto-target` refuses, rather than recording a flat call.
`0` means *the rule looked and said stay out*; it must not also mean *the rule
could not look*.

**Deflated Sharpe is `UNAVAILABLE` without `--trials` and `--trial-sr-var`,** and
`UNAVAILABLE` never counts as `PASS`. At N = 1 the deflation collapses
(Z⁻¹(0) = −∞) and the DSR degenerates into a Sharpe wearing a better name. Those
two inputs are facts about **the search**, which this file cannot observe.

**One call per asset per bar.** *(added)* Without it, thirty sealed signals can
be thirty reads of one Tuesday afternoon on one asset — reaching the graduation
count while carrying almost no information. A guard on a number is worthless if
the number can be padded, so the thing the number stands for is guarded instead.
Overridable with `--min-reseal-seconds 0`, deliberately.

**Independence, measured rather than assumed.** *(added)* The binomial sign test
assumes independent draws. Thirty calls across seven correlated assets over
overlapping weeks are not: one good fortnight can supply most of the wins and
the p-value reads far better than the evidence warrants — which is why D2 needed
a block bootstrap. This file cannot fix that; it refuses to hide it. Every
report measures the fraction of signal pairs with overlapping holding windows
and the peak number open at once, and says in words that the p is a **ceiling on
the evidence, not a measurement of it**.

---

## 4b. The rule was an orphan — the finding of the second pass

`regime_target()` — **the rule itself** — was defined and called by nothing.
`grep`-equivalent on the shipped file: zero references.

That is D4's defect exactly. D4 is the entry where `guards.py` was written,
hand-tested, and then imported by no one, and *"`grep -i guard daily.py`
returned zero lines. The circuit breakers existed as an idea and never as
behaviour."* This file's own docstring **cites D4**, and shipped the same defect
two passes later. `CONTRIBUTING.md` §6's corollary is the one that bit: *"a
lesson learned at one layer is not automatically applied at the next. Go and
check the code you wrote after learning it."*

Two consequences, and the second matters more than the first:

1. **The rule is wired in.** `--seal --auto-target --fetch` evaluates the
   regime rule on the same completed daily bars the reference price comes from,
   and records **what it saw** in the seal: window, SMA, close, bar count,
   venue, last bar timestamp. A sealed call now carries its own derivation, so
   it can be re-checked rather than taken on trust. `--auto-target` without
   `--fetch` is refused: a rule evaluated on one set of bars and priced from
   another is two experiments again. If the history is too short for the
   window, it **refuses** rather than sealing a flat call — a rule that has not
   fired is *no call*, and sealing it as 0 pads a graduation gate with records
   that carry no signal.
2. **The suite now fails on any orphaned public function.** An AST pass
   collects every module-level `def` and requires each to be referenced
   somewhere in the module. Prose did not enforce this; a check does. It is the
   only thing in the file that would have caught the rule, and it caught it.

**Pre-fix record: 196 passed / 2 failed, then abort** — and the two failures are
exactly the orphan.

---

## 4c. Settlement discretion — the hole the chain cannot close

Worth stating plainly, because every other mechanism here would report a rigged
record as clean:

**This ledger makes it impossible to revise a call after seeing the outcome. It
does not make it impossible to choose which calls to settle.** Seal forty,
settle the thirty that went well, and the hash chain verifies, the timestamps
are monotonic, no call was re-scored, and the gate reads the survivors. That is
survivorship bias with a chain around it.

No code can prevent it — the person running it decides. So the report does the
only honest thing available and **measures the discretion**: how many calls are
outstanding, how far past their holding period, how old the oldest is, and what
fraction of the record the outstanding calls represent. A `warn_selection_bias`
flag rides in the JSON so a script can act on it, and the note says what the
number means rather than leaving it to be read charitably.

And because a reason not to settle is itself a risk, **`--settle-due`** settles
every due call in one command. It settles all of them or reports why each one
could not be settled — never a silent subset, because a partial run that looks
complete is how a biased record gets built by accident. `--status` marks overdue
calls by name and points at the command that clears them. Making the honest
action the easy one is the part of this design that is actually load-bearing.

---

## 5. Price convention — the largest gap the first cut had

`d2_regime_deep.py` decides at the **close of bar t** and fills at the **open of
t+1**, on daily bars with the forming bar dropped. A ticker read at 14:12 on a
Tuesday is none of those things. A paper record built from spot ticks and a
backtest built from daily closes are **not the same experiment**, and
`must_beat_buy_and_hold` would have compared them silently.

So the convention now travels **with every record** — `daily_close`,
`spot_ticker`, or `hand_entered` — is validated on read, and a mixed ledger is
reported rather than averaged (the same treatment mixed `cost_bps` already got).
A seal/settle convention *mismatch* is counted separately, because entry and
exit measured on different clocks make the return partly an artifact of that.
`daily_close` is the default and the only comparable one; the fetcher drops the
forming bar exactly as `PRICE_DATA_INTEGRITY.md` and every deep CSV do.

Two smaller price fixes in the same pass:

- **The sealed price is a real quoted number, not a midpoint.** The first cut
  sealed `(coinbase + kraken) / 2` — a price no venue ever quoted and no order
  could have filled at. Coinbase is now primary (matching
  `VERIFIED_BASELINE_2026-08-19.md`), Kraken is recorded beside it as the
  cross-check with the spread, so a later reader can recompute either way.
- **Both venues must be quoting the same day.** For daily closes, last-completed
  bar starts more than an hour apart is a refusal, not an average.

One venue answering is still not a fallback. Two independent venues quoting the
same asset should agree to well under a percent; when they do not, the number is
a symptom — stale cache, thin book, wrong pair mapping, or the
SOL-not-on-this-venue class of bug `EXECUTION_ARCHITECTURE.md` caught once. A
sealed record is forever; a missed day is a missed day.

---

## 6. Exit codes, and not crying wolf

`--report` now exits **0** whenever it produced an honest report — including
`NOT ENOUGH DATA`, which is the expected state for the next thirty days. The
first cut exited 1 there, which would have painted the terminal red every day
for a month: `SENSING_ACROSS_LAYERS.md` calls that worse than no channel,
because it looks like monitoring. The verdict is still printed.

`--gate` is the strict mode a script asserts on: 0 only on `PASS`, 1 on `FAIL`,
2 on `UNAVAILABLE`. Across the whole CLI, `1` means *looked and it is wrong* and
`2` means *could not look* — P16's lesson at the gate is that "quiet because
healthy" and "quiet because unmeasurable" must not produce the same answer.

---

## 7. What the suite is, and what it found

`test_paper_run.py` — **226 checks, 226 passed ×2**, Linux / py 3.11.15.

Part A is ordinary. **Part B is mutation testing** (`CONTRIBUTING.md` §7): take
the source, delete one guard, `exec` the result, and require the matching Part A
check to **stop detecting** the problem. Each mutation asserts its anchor text
exists first, so a refactor that moves a guard turns the suite **red** instead of
silently testing nothing — the exact failure mode of the AST check evaded by a
single local variable.

B1 hash chain · B2 double-settle · B3 look-ahead · B4/B4b the NaN layers ·
B5 verify-before-append · B6 policy fail-closed · B7 the data floor ·
B8 the monotonic clock · B9 the schema gate · B10 the price convention ·
B11 the re-seal guard · **B12 the discretion note** (remove it and the report
goes silent about eight unscored calls while every other check still says
clean) · **B13 the rule's has-not-fired refusal** (remove it and a rule that
never fired becomes a flat call, thirty of which reach the graduation count
carrying no signal).

Plus a structural check that is not a mutation: **no orphaned public
functions**, §4b.

### Findings, in the order they were found

1. **The NaN guard has four layers, not two.** B4b was written expecting two and
   went red; the code was right and the *test's comment* was wrong. A NaN in a
   sealed price is caught by `loads_strict`'s `parse_constant`; by
   `canonical(allow_nan=False)` raising on re-hash; by `not (px > 0)` — `NaN > 0`
   is `False`, so it fails positivity without anyone writing a NaN check; and by
   the explicit `math.isfinite`. Layer 3 was **accidental**, is load-bearing, and
   is now stated rather than relied on by luck.
2. **The buy-and-hold comparison was a degenerate identity.** Caught by *looking
   at the first full report*: `rule −0.0590 vs B&H −0.0590 (paired 0/0)` on a
   gate line that could never pass. A `+1` call over an interval **is**
   buy-and-hold over that interval, so comparing directional calls only compared
   a series with itself. **The flat calls are the rule** — a long-or-flat rule
   differs from holding precisely in the intervals it sits out, and those were
   the ones excluded. Fixed: the comparison runs over all scored calls; the sign
   test still ignores flats, because a zero return is not a win.
   **PRE-FIX RECORD 171/176.**
3. **The chain-monotonic rule subsumes the settle-after-seal rule except at
   exact equality.** Discovered while writing B3: a strictly-earlier settle is
   now caught as a clock movement *first*. Both guards are kept and the suite
   tests each on the case that isolates it — equality is chain-monotonic and
   still look-ahead.
4. **Three from the same-session audit pass** (`CONTRIBUTING.md` §6, asking
   *what can an adversary make this do?* rather than re-reading the diff): a URL
   built from an unvalidated asset symbol; a `KeyError` in `score()` on
   unverified records; an unvalidated `rule` field.

5. **The rule was never called.** §4b. Caught by a check written *because* the
   same defect had been recorded once already in this project and written into
   this file's own docstring, where it did nothing.

**PRE-REFINEMENT RECORDS.** Pass 1 → pass 2: the 226-check suite against the
pre-refinement build reaches **135 passed / 3 failed then aborts** (no `--gate`;
schema-1 ledger refused by design). Pass 2 → pass 3: the 268-check suite against
the previous build reaches **196 passed / 2 failed then aborts**, and the two
failures are the orphaned rule. Both aborts are the correct signal — these are
breaking changes, and no ledger exists yet to migrate.

---

## 7b. Wired into the sweep, and the wiring is mutation-tested

`run test_paper_run.py 300` sits after `test_d3_daily_guards.py` in
`run_all_tests.sh` (backup: `run_all_tests.sh.PRE-paperrun`).

P20's lesson is that a suite whose output format the gate cannot parse leaves
the sweep green while failing, so the wiring was checked the same way the code
is — by extracting the runner's **own** `run()` and `clean_test_dbs` functions
and driving them, in a scratch copy, never in the live folder:

| case | gate line | exit |
|---|---|---|
| as shipped | `test_paper_run.py   270 passed, 0 failed` | **0** |
| one check seeded to fail | `test_paper_run.py   269 passed, 1 failed` | **1** |

The current PC runner is a later revision than the project's copy and is
stricter in two ways worth knowing: an **absent** file counts as a failure
(not a shrug), and a suite that runs but prints no readable tally is counted
as `UNSCORED`, which also gates the exit code. This suite prints
`N passed, M failed`, which its scrape reads correctly in both directions.

### The finding that only running it in the deployment folder could produce

First run in `C:\Users\Lawre\covenant`: **267 passed, 1 failed.**

The failing check was *"without covenant_backtest, scoring is UNAVAILABLE
(fails closed)"* — and the code was fine. The **test** was wrong: it relied on
`covenant_backtest.py` not being on `sys.path`, which is true in a scratch
sandbox and false in the folder where that file has always lived. So it had
been passing for an **environmental** reason and asserting nothing about the
guard, and it went red the first time it ran beside the code it protects.
`CONTRIBUTING.md` §8, exactly: a green sweep is green for the place it ran, and
"it passes here" is not a claim about there.

Fixed by manufacturing the absence — `sys.modules["covenant_backtest"] = None`
makes the import raise deterministically whether or not the real file is
present — plus two checks that the manufactured absence and the stub are
actually what the rest of the section is measuring. Verified in both
environments: **270/270 with the real `covenant_backtest.py` beside it, and
270/270 without.** That is the property the first version never had.

---

## 8. What is assumed and NOT verified

In `HANDOFF.md` §3's style, because "cannot run here" is an untested claim and
not a passing one (`CONTRIBUTING.md` §8):

- **No network call has ever been made by this file.** `--fetch`,
  `--auto-target`, `--settle-due`, both the daily-close and spot paths, four
  endpoints, `daily_closes()` included — all written and reviewed only. The
  suite exercises them against a fake that returns the documented shapes, which
  proves the parsing logic and proves nothing about the documents.
  **Run it once by hand on L's machine and treat the first run as a test, not
  as a sealed signal.** In particular the Coinbase candle row layout
  (`[time, low, high, open, close, volume]`, newest first) and the Kraken OHLC
  result-key shape are read from documentation, not from a response.
- **`covenant_backtest.CostModel`'s constructor signature is assumed.**
  `load_cost_model()` tries `round_trip_bps=`, then `bps=`, then no argument, and
  raises `UNAVAILABLE` if none works or `fill_price`/`fee` are missing. It never
  falls back to a local cost model — two implementations of one convention drift
  into a P&L difference nobody can attribute.
- **Linux only, on both machines.** The suite has now run in the deployment
  folder itself — but through the desktop's Linux VM, on py 3.10.12. That is
  **not** a win32 run. `AppendLock` uses `O_EXCL` rather than `fcntl`
  specifically so it *can* run there, but that is an intention, not a
  measurement (M29). Run it once from a Windows terminal before believing it.
- **The seal is stale.** `paper_run.py`, `test_paper_run.py` and
  `docs/PAPER_RUN.md` are not in `MANIFEST.sha256` (last built 2026-09-07
  14:47) and `SEAL_ROOT.txt` still says 134 files. Re-run `covenant_seal.py`
  and re-anchor: `PC_SYNC_LOOP.md` warns that a tamper-evident seal that is
  usually wrong teaches its operator to ignore it.
- **Nothing was committed or pushed to git.** `GITHUB_PUBLISH_STATE.md`:
  *"Never run git against this repo through the Cowork file bridge"* — the
  mount cannot delete files and git deletes a `.lock` after every ref write.
  Only read-only `git --no-optional-locks` was used. The worktree already
  carried eleven modifications from other work before this session touched it;
  those must not be swept into a commit for this.
- **Four Kraken pair mappings are UNCONFIRMED** — `WLFI`, `ONDO`, `CRO`, `PEPE`
  — and named as such in the source. A wrong mapping fails closed (the two-venue
  rule refuses a single quote) and the error says the mapping is unconfirmed so
  it is not mistaken for an outage.
- **`CC` (Canton) is on a never-fetch list** per `DAILY_CHECK.md` §5. Sealing on
  CC needs `--ref-px`, recorded as `hand_entered`.

---

## 9. Runbook

```
# daily, one call per asset — the rule picks the target and records why
python paper_run.py --seal --asset SOL --auto-target --fetch

# or set it by hand
python paper_run.py --seal --asset SOL --target 1 --fetch --note "above SMA200"

# settle everything past its holding period, in one command
python paper_run.py --settle-due
python paper_run.py --settle --seq 7 --fetch     # or one at a time

python paper_run.py --verify     # chain integrity; exit 1 if broken
python paper_run.py --status     # n/30 progress, open calls
python paper_run.py --tip        # 64-hex root -> covenant_anchor.py

# after 30 settled signals
python paper_run.py --report --trials 12 --trial-sr-var 0.004
python paper_run.py --gate --trials 12 --trial-sr-var 0.004   # for scripts
```

**One decision still open and free** (`TRADING_READINESS.md` §1d): rule 4 (never
average down) and rebalancing conflict on **95–97 %** of trades at the band
schedule the 20 %-cap policy implies. Both are still in the policy. Keeping rule
4 has already decided against rebalancing — say so in `TRADING_POLICY.json`
rather than discovering the contradiction at execution time.

---

## 10. What this file must never become

The next natural-sounding request is *"now have it compute the order sizes so I
can just confirm them."* That is `execute.py`, it is a different file, it is
L's, and the reason to keep it separate is not tidiness: a ledger whose job is
to be **honest about a rule** and a program whose job is to **act on one** have
opposite failure modes, and merging them puts the pressure of the second on the
integrity of the first. A loop that can edit its own constraints has no
constraints.
