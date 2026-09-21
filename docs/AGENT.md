# The agent on this PC, its browser, and the layer in front of both

Written 2026-09-19 on the operator's instruction, in his words: *"there has to
be a image creation open source we can take and improve on same as the other
asks including our students growing to agents"*; *"optimize the pc towards
these tasks and this purpose"*; *"need a browser and a security layer other
than that optimize"*; *"green light"*.

## What is here

| Piece | Where | What it is |
|---|---|---|
| Runtime | `tools/llama/llama-server.exe` (untracked) | llama.cpp's server, build b11057, CPU. The same 18 MB runtime the judge workflow uses on the GitHub runner. |
| Weights | `models/*.gguf` (untracked) | Qwen2.5-Coder-7B-Instruct Q4_K_M (needs ~6 GB resident) and Qwen2.5-3B-Instruct Q4_K_M (~3 GB). Open weights, Apache-2.0. |
| Keeper | `covenant_model.py` | Starts the server on first use, on 127.0.0.1 only; picks the largest weights that fit the memory free at that moment; stops it after 10 idle minutes. |
| Door | `POST /m/agent` on the node | Tailnet-gated like `/m`. Prompt in, model answer out — **after** the sentinel has judged the answer. Since 2026-09-21 the model speaks as Tetsu (`covenant-phone/docs/PERSONA.md`) in a spoken register, and is handed the caller's last 6 answered exchanges as the turns before this one (`agent_history()`, A165). |
| Browser | `_agent_fetch()` in the node | One GET per ask, to an allow-listed host, text only, 8 KB kept. |
| Memory | `ops/chat/ask_log.jsonl` (untracked) | Every ask, answer and verdict, beside the recorded model conversations. What the chat memory reads, and what the door reads back per caller at ask time. Training goes through the teacher's queue (`ops/teacher_queue.jsonl`, both sides of every exchange and the phone's AI-app chat lines), which the nightly carries to the panel, balanced, once each (`covenant_teacher_queue`, A166). |
| PC page | `GET /pc`, `POST /pc/council`, `GET /pc/training` (`covenant_council.py`, A167) | The sister interface for the PC's browser: talk to Tetsu; a council of three roles of the local model in turn, judged by the gate before it is returned; the training panel with the queue, the ledger, the exam, the last nightly and five graduation criteria, four measured and the fifth UNDETERMINED on one machine. |
| Voice | the phone app (`covenant-phone`) | The box sends a conversation to this door and speaks the answer; `judge:` asks the phone's own gate; a Mic button takes one utterance, long-press for hands-free (the microphone reopens after each spoken answer). |

## The security layer, in order

1. **The network.** The model server binds loopback. The door (`/m/agent`)
   answers loopback and the Tailscale range only — the same predicate, the
   same 403, the same anomaly row as `/m`. Nothing on the house LAN or the
   internet can reach either.
2. **The rate.** 30 asks per 10 minutes per caller behind the API's own
   limiter (which bites first, at the 21st request in a burst). 4,000
   characters in; 700 tokens out.
3. **The browser's leash.** The model may ask for ONE page per answer by
   writing a line `FETCH: https://...`. The host must be on the allow-list
   (`AGENT_FETCH_HOSTS`: github.com, raw.githubusercontent.com,
   developer.android.com, docs.python.org, arxiv.org, en.wikipedia.org).
   GET only, 15 s, 64 KB read, tags stripped, 8 KB kept, no cookies, no
   credentials, no redirects off the list. The fetched text is handed back
   to the model as data, marked as such. Anything else the page says is not
   an instruction. Every fetch is logged with its URL and size.
4. **The gate.** The answer is judged by this node's sentinel — the same
   distilled student and semantic judge that gate every transaction — before
   it is returned. A refused answer is withheld; the caller gets the verdict
   and the reason, not the text. A held answer is returned marked HELD.
5. **The record.** Ask, answer (or that it was withheld), verdict, model,
   tokens, milliseconds, fetches: one row in `ops/chat/ask_log.jsonl`. This
   is how the students grow toward agents: their verdicts on a model's
   answers land in the same ledger the nightly distill learns from.
6. **Put away.** Ten idle minutes and the server is stopped; the weights
   leave memory. His rule since Ollama was removed.

## What it cannot do, said plainly

- It cannot act. No file is written, no command is run, no message is sent
  by the model. It answers text with text, through the gate.
- It is not at the level of the model writing this file. On this CPU the 7B
  answers at a few tokens per second; the 3B faster and worse.
- It is not the judge. Adding it as a seat would change what the gate means
  and waits for the group (his rule: refinements only until a second
  operator).
- Image creation is the next pass, on the same shape: an open-source model
  we can run here (stable-diffusion.cpp, sd-turbo) behind the same door and
  the same gate. Not in this file until it is measured.

## Repro

```
python covenant_model.py --status
python covenant_model.py --ask "what does the covenant judge refuse?"
curl -X POST -H "Content-Type: application/json" -d "{\"text\":\"...\"}" http://127.0.0.1:5000/m/agent
python test_m6_mobile_door.py        # M6q: the door, the leash and the gate, with a stub model
```
