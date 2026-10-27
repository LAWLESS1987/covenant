# Scheduled daily check — cloud run blocked (2026-08-20; recurred 2026-08-21)

> # ✅ RESOLVED 2026-08-22 — AND THE DIAGNOSIS BELOW WAS WRONG
>
> Everything under "What failed" item 1 is false as measured today. Item 2 is
> true and is the whole story.
>
> **The claim:** *"Direct fetch (urllib/curl in the cloud sandbox): proxy
> returns `403 Forbidden` at the tunnel for `api.exchange.coinbase.com`,
> `api.coinbase.com`, and `api.kraken.com`. These hosts are not on the sandbox's
> network allowlist."*
>
> **Re-measured from the cloud sandbox, plain `urllib`, 2026-08-22:**
>
> ```
> api.kraken.com/0/public/Time                   HTTP 200
> api.kraken.com/0/public/OHLC?pair=XXLMZUSD…    HTTP 200
> api.exchange.coinbase.com/products/XLM-USD/…   HTTP 200   23 004 bytes
> api.coinbase.com/v2/prices/XLM-USD/spot        HTTP 200
> ```
>
> All four answer. M24 had already found this for Kraken on 08-22 08:45 —
> *"every M1 hazard was the summariser, not Kraken"* — and nobody re-tested
> Coinbase against it, so this document kept two mornings of the daily check
> switched off on the strength of a superseded measurement.
>
> **What actually failed is item 2, and only item 2.** `WebFetch` raises a
> one-time URL permission prompt; unattended, nobody answers it, and it returns
> `PROVENANCE_REQUIRED` / "not answered in time". The finding recorded here on
> 08-21 — that putting the literal URL in the trigger prompt does **not** avoid
> the gate — stands and is valuable. The wrong step was concluding that the
> *network* was closed and that the check therefore had to move to the local
> machine.
>
> **Fix applied instead of Fix 2 (no local scheduled task needed):**
> `daily.py` fetches with `urllib` and always did. It now also carries the four
> §3 window checks in code, a Kraken cross-venue check on the last settled
> close, and the circuit breakers. Run it — in the cloud, in a scheduled
> session, anywhere:
>
> ```
> python daily.py                  # Coinbase, verified against Kraken
> python daily.py --source kraken  # if Coinbase is ever actually unavailable
> ```
>
> Verified end to end on 2026-08-22 from the cloud sandbox: nine symbols priced,
> all nine agreeing with Kraken on the last settled close (worst 0.292%),
> portfolio <total>, two trims and the cash floor flagged.
>
> **The rule this leaves behind, which is the part worth keeping:** a "the
> network is blocked" finding is a measurement, and a measurement expires. It
> cost two mornings of no data. Before building a workaround around a blocked
> host, re-probe the host — it is four lines of `urllib` and it is cheaper than
> a local scheduled task. And never reach for `WebFetch` where `urllib` will do:
> the gate is a property of the tool, not of the internet.
>
> **Kept below unedited as the record of what was believed and why.**

The 2026-08-20 scheduled run could not fetch any prices. **No numbers were
reported** (per runbook §3: a failed read is reported as failed, never as data).

**2026-08-21 update:** recurred exactly as predicted. The scheduled task's
prompt still does not contain the literal Coinbase URL, so WebFetch returned
`PROVENANCE_REQUIRED` again on the first fetch (XLM). No prices were reported.
Fixing the trigger prompt from inside a run is not possible: `update_trigger`
requires interactive approval and fails unattended (see DE2 in
`claude/TRIGGER_PROMPT_PROPOSED.md`, observed even in an attended session).
L must apply fix 1 or 2 below by hand.

**2026-08-21 second finding (crypto trend alert run): FIX 1 DOES NOT WORK.**
A separate scheduled task ("daily crypto trend alert", XRP/HBAR via
`api.exchange.coinbase.com` candles + ntfy.sh push) *did* contain the literal
URLs verbatim in its trigger prompt. WebFetch still returned
`PROVENANCE_REQUIRED` on every call — both Coinbase URLs (exact string match
with the prompt) and the ntfy publish URL. The error text was "The permission
request for this URL was not answered in time", i.e. a permission prompt is
still raised and times out unattended. Conclusion: **URL-in-prompt provenance
is not honored for scheduled-trigger prompts in this environment.** Retries do
not help. That leaves:

- **Fix 2 (run locally)** as the only reliable path for scheduled price
  fetches + ntfy pushes. Recreate as a *local* scheduled task on the computer.
- **Fix 3 (interactive approval)** untested as to whether approval persists
  into later scheduled runs.
- Phone delivery still works via the built-in push-notification channel
  (used on 2026-08-21 to deliver the honest "data not verified" alert), but
  it cannot carry fetched data that was never obtained.

## What failed

1. **Direct fetch (urllib/curl in the cloud sandbox):** proxy returns
   `403 Forbidden` at the tunnel for `api.exchange.coinbase.com`,
   `api.coinbase.com`, and `api.kraken.com`. These hosts are not on the
   sandbox's network allowlist.
2. **WebFetch tool:** returns `PROVENANCE_REQUIRED` — it asks for a one-time
   user approval of the URL, and in an unattended scheduled run no one is
   there to approve it. Retried; same result. Note the WebFetch path is the
   summarising-model path from `claude/PRICE_DATA_INTEGRITY.md` — small 8-day
   windows + per-window verification would have been applied had it worked.

This will recur every scheduled cloud run until one of the fixes below is done.

## Fixes (pick one)

1. ~~**Include the URL in the task prompt.**~~ **Disproven 2026-08-21** — see
   second finding above. A trigger prompt containing the exact literal URL
   still triggers the permission gate, which times out unattended.
2. **Run it locally instead.** `daily.py` on the local machine fetches with
   urllib and parses JSON directly — no proxy, no summarising model (see
   PRICE_DATA_INTEGRITY.md, "Where this does NOT apply"). Recreate the check
   as a *local* scheduled task on the computer. **Now the recommended fix.**
3. **Run the check once interactively** and approve the Coinbase fetch when
   prompted, then see whether the approval sticks for scheduled runs.

## What was still verified today

- CC (Canton) hand price $0.09105 noted per runbook §5 — but a portfolio value
  from one hand-entered position and nothing else would be meaningless, so
  none was computed. (Same on 2026-08-21.)
- Regime lines dated 2026-08-19 are 1 day old (2 days on 08-21) — well inside
  the 14-day freshness window; no drift caveat needed once prices are
  available.
