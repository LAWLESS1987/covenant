# The daily plan

*One page. Written 2026-09-12.*

Every night the covenant writes the day's plan, `ops/daily_plan/<date>.json`:
the money posture as `money_posture.py` prints it, the Rule 5 record, the caps
and switches, the trader's own proposed orders for the day (planned, not
placed), and -- when there is nothing to do -- why. Its sha256 is over its
canonical bytes; a plan whose bytes move is no plan.

A person approves or declines it. The decision is one signed line in
`ops/daily_approvals.jsonl`, signed by a registered key (`ops/daily_plan_signers.json`)
with the node's own operator-request signature, so it cannot be forged,
replayed, or moved to another plan. The last decision for a plan wins.

No order goes live without an approved plan for today: `guards.preconditions`
reason 7, asked by the trader, the sentinel's seal path and the morning
report alike. `daily_plan_required: false` in `trader_config.json` switches
it off, and only that.

```
python covenant_daily_plan.py --write               # the nightly does this
python covenant_daily_plan.py --show
python covenant_daily_plan.py --approve --note "..."   # signed with nodeA_prod.db.key
python covenant_daily_plan.py --decline --note "..."
python covenant_daily_plan.py --pubkey > me.pem; python covenant_daily_plan.py --register-signer pc me.pem
```

The phone: `GET /daily_plan` (signed) shows the plan on the Today screen;
Approve / Decline is `POST /daily_plan/approve`, signed by the phone node's
key, which must be registered here first. An unsigned or unregistered
caller gets 403 and never sees the posture.

What it is not: advice. The plan is the covenant's measured posture and its
own validated rules, of which none has cleared walk-forward, deflation and
PBO as of 2026-09-12 -- so plans read "hold", and approving one is how you
show you looked.
