# Turning Ollama into a Covenant judge

You have Ollama, so this needs no API key and no internet.

## 1. Pick a model

Any of these work. Smaller is faster; larger judges better.

```
ollama pull qwen2.5:7b          # good instruction-following, solid default
ollama pull mistral             # Mistral's open weights
ollama pull deepseek-r1:7b      # reasoning model -- see the note below
```

Check what you already have:

```
ollama list
```

## 2. Point Covenant at it

```
export COVENANT_LOCAL_JUDGE_URL=http://localhost:11434/v1/chat/completions
export COVENANT_LOCAL_JUDGE_MODEL=qwen2.5:7b
export COVENANT_LOCAL_JUDGE_TIMEOUT=180
export COVENANT_JUDGE_PROVIDERS=local,mock
```

On Windows the node runs in your normal Python, so set them with `set` instead
of `export`, or add them to `start_live.bat`.

`local,mock` gives you the two distinct providers the quorum requires. `mock`
is keyword matching, not judgment — it is there to satisfy the diversity check
while you have exactly one real judge. **Replace it with a second real provider
when you have one.**

## 3. The timeout is not optional

The cloud judges default to 30 seconds. A 7B model on CPU can take longer than
that for one verdict, and a timeout is recorded as a **violation** — so slow
hardware silently rejects your own transactions. That's why the local judge
defaults to 180s. Leave it high.

---

## Two bugs found while wiring this up

Both were verified against the real parser, not guessed at.

### String booleans were inverting verdicts

Small models very often answer `{"violates": "false"}` — a string, not a
boolean. The core parser did `bool(obj.get("violates"))`, and in Python
`bool("false")` is **True**. A model saying *"this is fine"* was read as
*"this violates"* and the transaction rejected, with the clean reasoning sitting
right there in the same object.

Fixed in the core, so every provider benefits. Unrecognisable values still
return True — fail-closed was never the bug, reading an explicit "no" as a "yes"
was.

### Reasoning models broke the parser entirely

The core parser takes everything between the first `{` and the last `}`.
`deepseek-r1` emits `<think>...</think>` before answering, and any `{` in that
monologue becomes the start of the "JSON". The parse then dies, the judge
raises, and `QuorumJudge` counts a raising judge as a **violation**.

Net effect: the model reasoning out loud rejects your transaction.

**`deepseek-r1:7b` was the default I'd set in `covenant_judge_local.py`.** My
mistake — I picked a reasoning model without checking its output survived the
parser. The local judge now strips thinking blocks and code fences, walks the
text for balanced objects, and takes the last one carrying a `violates` key —
the answer, not the scratchpad.

All eight response shapes now parse correctly, including garbage, which still
fails closed.

---

## Check it works

```
python -c "
import os, covenant_judge_local as L
j = L.OpenAICompatJudge(judge_id='local:1')
r = j.evaluate({'message':'a gift to a friend','origin':'organic'},
               ['You shall not steal.'])
print('violates:', r.violates)
print('reason  :', r.reasoning[:200])
"
```

If Ollama isn't running you'll get a fail-closed rejection naming the connection
error — that's correct behaviour, not a crash.

## What this does and doesn't buy you

A second model is a second opinion, not a guarantee. Models with overlapping
training data share blind spots, and a quantised 7B is a **weaker** judge than a
frontier model — it will miss things Claude would catch.

What it buys is independence and availability: a judge that keeps working with
no key, no bill, and no internet. On the road, that's the only kind that works.
