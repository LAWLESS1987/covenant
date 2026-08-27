# Running the real ethics gate without an Anthropic key

You have two keyless paths, and neither is the insecure keyword mock. I verified
both end-to-end in the sandbox before writing this. One of them was blocked by a
bug; that is fixed and included.

**Recommendation: the local Ollama judge.** You already have the model.

---

## Path A — local judge via Ollama (recommended)

Real semantic judgment, no key, no bill, no internet, and it runs unattended.

### The blocker I hit, and the fix

`OLLAMA_JUDGE.md` §2 tells you to set `COVENANT_JUDGE_PROVIDERS=local`. Do that
and the node dies at startup:

```
ValueError: unknown judge provider: 'local'
            (known: ['claude', 'google', 'mock', 'openai'])
```

`covenant_judge_local.py` registers `local`, `deepseek` and `mistral` in its last
three lines (207–209) — but **`covenant_unified_v8.py` never imports it**, and
nothing else does either except `judge_check.py`. So the judge was written,
debugged, documented, and never actually reachable from a running node. The
`RUN.bat` wiring works only because `RUN.bat` runs `daily.py` / `judge_check.py`,
which import the module directly — it never starts a node.

Fix: `run_with_local_judge.py` (included), the same 10-line shape as your
existing `run_with_claude_judge.py` — import the module, then hand off to
`cov.main()`.

### Verified behaviour

Two nodes, fresh adopting DBs, full production sequence:

```
judge   : quorum(local:0,mock_selfreport:0) | insecure: False | keyless: True
founder balance          1000.0
send 10 A->B             accepted
mine                     block 0000d69c7c7ebc62
status                   height=2 both, same tip, converged: True
balances                 founder 990 / nodeB 10 -- IDENTICAL on both dbs
```

Negative cases, all correct:

| case | result |
|---|---|
| model says `violates: true` | **rejected** — `local:0: VIOLATES -- on reflection this is theft` |
| same tx data as one already approved | **rejected** — so it re-judges every time, it does **not** cache |
| model emits `<think>…</think>` first (qwen3 does) | parsed correctly, admitted |
| model returns string `"false"` not boolean | parsed correctly, admitted |
| Ollama not running | **fails closed** — `ConnectionError`, transaction rejected |

Both parser bugs `OLLAMA_JUDGE.md` documents are genuinely fixed. I tested all
six response shapes against the real parser; garbage still fails closed.

### One good surprise

You do **not** need `local,mock`. `COVENANT_JUDGE_PROVIDERS=local` alone
satisfies the quorum diversity check — the node pairs it with `mock_selfreport`,
which is *not* the insecure keyword mock. `/health` confirms
`judge_insecure: False`. So you can leave `COVENANT_INSECURE_MOCK_JUDGE` unset
entirely, which `OLLAMA_JUDGE.md` implies you cannot.

### Two cautions

**Your model is 22 GB.** On CPU a single verdict can take minutes. A judge
timeout is recorded as a **violation**, so a slow machine silently rejects your
own transactions. The launcher sets both timeouts to 300s. Do not lower them.

**`preflight.py` will still say BLOCKING.** It reports
`no provider API key set … this node will REJECT EVERY TRANSACTION`, and
`/health` carries the matching warning — while the gate is in fact working. I
saw both while transactions were being correctly admitted and rejected. That
check tests for an API key, not for a functioning judge. Ignore it on this path;
`judge_check.py` is the real test.

### Run it

```
start_live_local.bat
```

It checks Ollama is up, runs `judge_check.py` first and makes you confirm the
verdict, backs up your founder key, then launches both nodes.

`judge_check.py` is the part that matters. It sends one benign transaction and
one outright theft, because — as its own docstring says — a judge that approves
everything and a judge that works look identical if you only ever show it
something harmless. If it prints **"Approves EVERYTHING"**, stop. That is worse
than no gate, because it looks like one.

---

## Path B — file judge, with me as the gate

`run_with_claude_judge.py` writes each pending decision to
`judge_queue/requests/` and waits for a verdict in `judge_queue/verdicts/`. I
read the request, write the verdict, the node admits it. Real judgment, no key.

Verified: with no verdict written, the node **failed closed** exactly as
designed —
`claudefile:0: VIOLATES -- no verdict from Claude within timeout`. With a verdict
written, the transaction was admitted and mined.

It also reported `judge_insecure: False`, `judge: quorum(claudefile:0,
mock_selfreport:0)`.

**But it cannot run unattended, and there is a sharper problem.**

### FINDING — one verdict permanently approves any amount

`_key()` in `run_with_claude_judge.py` hashes the transaction **data** only. And
the gate itself only ever receives data — `Sentinel.validate_transaction` at line
1046 is:

```python
result = self.judge.evaluate(tx.data, self.principles)
```

`tx.amount`, `tx.sender_pubkey` and `tx.recipient_pubkey` are never passed. For a
`covenant_client.py send`, `tx.data` is just `{"origin": "human"}`.

So every human-origin transfer hashes to the same key. Demonstrated:

```
approved a 10-unit transfer  -> admitted
then sent 900, same data     -> admitted INSTANTLY, gate never asked
```

Both were recorded in the judgments table with the identical reasoning:
*"approved by Claude: benign human-origin transfer"*. I judged a 10. It approved
a 900.

**This applies to your machine right now.** `judge_queue/verdicts/` already
contains `08cb9db4fe4f4b94d91b16ea.json` — and that is exactly the key my
sandbox generated for `{"origin": "human"}`. That one file blanket-approves every
human-origin transaction of any size, permanently, on the file-judge path.

### And the part that is not the file judge's fault

The amount-blindness is **structural and affects every provider** — Claude,
Ollama, or a frontier API. The gate judges the *message*, never the *transfer*.
No judge you plug in can distinguish a 10-unit gift from draining the account,
because it is never shown the number.

Balance is still enforced separately (you cannot overdraw), so this is not a
theft vector on its own. But "ethics gate" overstates what it does. Feeding
`amount` and the counterparties into `tx.data`, or into `evaluate()`, is the
change that would make the name true — and per `HANDOFF.md` §5 that is a ledger
change needing its own adversarial pass and a human reading the diff. I did not
make it.

---

## What I'd do

1. `start_live_local.bat` — the Ollama path, unattended, no key.
2. Watch `judge_check.py`'s two verdicts. Approving the theft is the failure mode
   that matters.
3. Decide what to do about `judge_queue/verdicts/08cb9db4fe4f4b94d91b16ea.json`.
   On the Ollama path it is inert. If you ever run the file judge again, it is a
   standing approval for everything.

Mainnet stays blocked either way — `xrp_testnet_proof.json` still does not exist.
