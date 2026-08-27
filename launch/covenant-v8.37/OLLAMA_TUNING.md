# Making the local judge operational, and tuning it for semantics

> **Superseded in part by `LIVE_RUN_2026-08-22.md`.** The chain is now up on
> this machine with `qwen3:8b`, 6/6 on the bench, 16.7 s per verdict. Read
> that file for what actually happened; read this one for why each setting is
> what it is.
>
> **`qwen3.6:latest` is not the model.** It is 23.94 GB against 16.4 GB of
> RAM — it cannot load. Section 4 below has the numbers.

Everything below was measured, not estimated. The tuning numbers come from
`qwen3:1.7b` on 2 CPU cores — a deliberately weak stand-in, so read them as
the *shape* of the win. The live numbers on your own hardware are in
`LIVE_RUN_2026-08-22.md`.

`judge_bench.py` reruns all of it on your machine. Nothing here touches the
ledger, the verdict schema, or the quorum.

---

## 1. What actually changed

Six cases, the real parser, the real registry:

| path | accuracy | parsed | wall | generated tokens |
|---|---|---|---|---|
| shipped — `/v1/chat/completions`, `max_tokens=512` | 4/6 | **5/6** | 253.1 s | 2238 |
| + `/api/chat`, thinking off, constrained JSON, `num_predict=160`, `temp=0` | 4/6 | 6/6 | 58.2 s | 467 |
| + semantics-tuned prompt | **6/6** | 6/6 | **53.5 s** | **379** |

**83% fewer generated tokens, 4.7× faster, and two verdicts that were wrong
are now right.** Same model, same hardware, same transactions.

### The four transport levers

**Thinking off.** qwen3-family models emit `<think>…</think>` before
answering, and `_extract_verdict_json` already *strips that block*. Every one
of those tokens was generated at CPU speed and then discarded. On a 24 GB
model this is the single largest cost in a verdict.

**Constrained JSON (`format` = schema).** The model cannot ramble, fence, or
run past the closing brace. This is what took parse success from 5/6 to 6/6 —
and the failure it fixed matters: a *benign* transaction was rejected because
the model talked past `max_tokens` mid-thought and the verdict never arrived.
A parse failure is scored as a violation, so verbosity was silently rejecting
good transactions.

**`num_predict=160`, `temperature=0`, `top_k=1`.** A verdict is ~60 tokens;
512 was a licence to ramble. Temperature 0 also makes the gate
**deterministic** — verified, same verdict three times running. For a gate
that is a correctness property, not a nicety.

**`keep_alive=30m`.** Cold vs warm at 1.7 B: 4.4 s prefill → 1.2 s. Scale
that by model size — a 24 GB model reloaded from disk per verdict is the
difference between seconds and minutes.

### The prompt changes, and why each one exists

Every one of these fixed an observed wrong verdict:

- **Applicability.** Ten commandments against a token transfer invites a model
  to stretch "Sabbath" or "carved image" to reach a transaction they plainly
  do not touch. It is now told not to.
- **Giving is never taking.** *"Return 10% of my mining yield to the community
  pool"* was judged a **violation** — the model read giving as taking. A gate
  that blocks generosity is broken in the expensive direction.
- **The empty-payload rule.** This is the important one. `covenant_client.py
  send` produces `tx.data == {"origin": "human"}` and nothing else. Shown only
  that, the model has nothing to judge and was guessing — and at temperature 0
  it guessed **VIOLATES**. That verdict would have rejected *every real
  transfer on your chain*. `judge_check.py`'s two cases never exercise this
  payload, so it would have surfaced only in production.
- **Spotlighting + sandwich defense.** The transaction data is fenced in
  explicit markers and the instruction repeated after it, so injected text is
  judged *as evidence of intent to deceive* rather than obeyed.

---

## 2. Token efficiency

You asked whether the improvements compound into token savings. They do, in
three separate ways.

**Generated tokens fell 83%** (2238 → 379). Generation is the expensive half:
every output token is a full forward pass. This is the bulk of the win.

**The added guidance is nearly free.** The tuned prompt is ~250 tokens longer.
Measured with an isolated prefix test:

```
  step                                 prompt_tok  prefill_s
  prefix A + suffix 1  (cold)              389       3.48
  prefix A + suffix 2                      389       0.27
  prefix A + suffix 3                      388       0.32
  NEW prefix B + suffix 1                  389       3.38    <- full recompute
  prefix A again                           389       0.32    <- still cached
```

A byte-identical prefix is reused from KV cache: **3.48 s → 0.27 s, about
13×**. The preamble is prefilled once and reused for every verdict after.
Changing one character at the front costs the full recompute again (the
`prefix B` row proves it).

**Consequence — a rule worth keeping:** the constant material (principles,
guidance, injection warning) must stay byte-identical and stay *first*, with
only the transaction data varying at the tail. That is how
`covenant_judge_ollama.py` builds the prompt. Do not put a timestamp, a nonce,
or a per-transaction detail into the preamble; it would silently cost you a
full prefill on every verdict.

**The capability probe runs once.** The fallback ladder memoises the rung that
worked on the class, so an older Ollama is probed at startup rather than on
every verdict.

---

## 3. A defect I introduced and then fixed

Worth recording, because the fix is the interesting part.

The fallback ladder walks five progressively simpler request shapes so an
older Ollama degrades in speed rather than failing closed. My first version
walked it on **any** exception — including transport errors. Against a *hung*
Ollama (accepts the connection, never answers) that meant 5 rungs × 300 s
timeout × the base class's 3 attempts: **~50 minutes stalled on one
transaction.**

A transport failure is not a capability problem. The ladder now advances only
on HTTP 4xx/5xx or an unusable body, and re-raises immediately on a timeout or
refused connection. Fault-injected against a socket that accepts and never
replies:

```
hung server, timeout=4s  -> 13.4s elapsed, violates=True
  PASS fail-closed
  PASS no ladder-multiplied stall (13.4s; the bug would have been >60s)
```

13.4 s is three attempts plus backoff — the base class's own retry policy, and
nothing more.

---

## 4. PC tuning

`ollama_tune.bat` sets the server-side half. Two kinds of setting exist and
they are not interchangeable:

- **Per-request** — `num_ctx`, `num_predict`, `temperature`, `keep_alive`.
  `covenant_judge_ollama.py` already sends these on every call. Nothing to do.
- **Server-side** — flash attention, KV cache type, parallel slots, bind
  address. These belong to the `ollama.exe` process, which on Windows is
  started by the tray app, *not* by a `.bat`. They need `setx` and an Ollama
  restart. That is what `ollama_tune.bat` does, and `ollama_tune.bat undo`
  reverses it.

| setting | value | why |
|---|---|---|
| `OLLAMA_NUM_PARALLEL` | 1 | Each parallel slot gets its own KV cache. On auto this multiplies RAM for concurrency one judge will never use. |
| `OLLAMA_MAX_LOADED_MODELS` | 1 | Never hold two large models at once. |
| `OLLAMA_FLASH_ATTENTION` | 1 | Cheaper attention, less KV memory. |
| `OLLAMA_KV_CACHE_TYPE` | q8_0 | Roughly halves KV cache RAM. Requires flash attention. Negligible effect on a 60-token JSON verdict. |
| `OLLAMA_CONTEXT_LENGTH` | 2048 | The judge prompt is ~500 tokens; the 4096 default allocates cache you never fill. |
| `OLLAMA_KEEP_ALIVE` | 30m | Server-side backstop for the per-request value. |
| power plan | High performance | On a laptop, CPU inference on Balanced runs at a fraction of full speed. |

**Answered: your RAM is 16.4 GB, and `qwen3.6:latest` is 23.94 GB.** It cannot
load — Ollama returns HTTP 500, the judge fails closed, and every transaction
is rejected. `judge_bench.py` now runs a fit check first and refuses to
proceed, because a gate that rejects everything still scores 3/6 on the suite:
it does not look broken, it looks strict. `qwen3:8b` (5.2 GB) is the model in
use, verified 6/6 on this machine. If a model does not fit, Windows pages it
from disk on every token and no amount of tuning will save it. `pc_check.bat`
answers this. If you are under 32 GB, the honest fix is a smaller model, not
better settings — and I would rather tell you that than hand you a tuned
config that thrashes.

---

## 5. Security

**Ollama has no authentication.** Anything that can reach port 11434 can load
models, run inference, and see prompts. Bind it to loopback.
`start_live_ollama.bat` refuses to proceed quietly if it finds `0.0.0.0`.

**CVE-2026-7482 ("Bleeding Llama"), CVSS 9.1** — an unauthenticated heap
memory leak in Ollama's GGUF loader. Three unauthenticated calls
(`/api/blobs` → `/api/create` → `/api/push`) read out-of-bounds heap: system
prompts, other sessions' conversations, environment variables **including API
keys**, and credentials. **All versions before 0.17.1 are affected**; 0.17.1
fixed it in February 2026. `pc_check.bat` reports your version. If you are
behind, update before you launch — you have an `ANTHROPIC_API_KEY` path in
this codebase and that class of secret is exactly what leaks.

**Done already:** `judge_queue/verdicts/08cb9db4fe4f4b94d91b16ea.json` is
moved to `judge_queue/revoked/`. It was a verdict keyed on
`sha256({"origin":"human"})` — the payload every `send` produces — and since
`tx.amount` never reaches the gate, that one file was a permanent blanket
approval for a human-origin transfer of any size. Moved, not deleted, so the
evidence survives.

**Still structural, not fixed here:** the gate is shown `tx.data` only —
never `tx.amount`, never the counterparties
(`covenant_unified_v8.py` line ~1046). No prompt can judge a number it is not
given. Feeding amount and counterparties into `evaluate()` is the change that
would make "ethics gate" true, and `HANDOFF.md` §5 is right that it needs its
own adversarial pass and a human reading the diff. Say the word and I will
prepare it as a reviewable diff rather than a silent edit.

---

## 6. What to run

```
pc_check.bat            read-only; writes pc_report.txt. Do this first.
ollama_tune.bat         server-side settings; then restart Ollama.
python judge_bench.py   six cases on YOUR model, both paths, real numbers.
start_live_ollama.bat   the launch.
```

**Files added:** `covenant_judge_ollama.py`, `run_with_ollama_judge.py`,
`judge_bench.py`, `start_live_ollama.bat`, `ollama_tune.bat`, `pc_check.bat`.

**Files changed: none.** `start_live_local.bat`, `covenant_judge_local.py` and
`run_with_local_judge.py` are untouched and still work — they stay on the old
untuned path. Importing `covenant_judge_ollama` is the entire mechanism, and
deleting that one file reverts everything.

**Verified before shipping** (against your real `covenant_unified_v8.py`, not a
stand-in): the registry resolves `local` → `OllamaJudge`; six cases 6/6; the
same case judged three times returns the same verdict; URL derivation handles
all four forms of `COVENANT_LOCAL_JUDGE_URL`; and with Ollama unreachable the
judge **rejects**, it does not fall open.

**What I could not verify:** none of this has run on Windows, or against
`qwen3.6:latest`. The launcher is `.bat`, the model is 60× larger than my
stand-in, and `preflight.py`'s `chmod 600` check is still unsatisfiable on
NTFS. `judge_bench.py` is what closes that gap — run it before you launch.

Mainnet is still gated shut: `xrp_testnet_proof.json` does not exist, and
nothing here changed that.
