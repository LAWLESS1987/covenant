# UNIFIED CONVERSATION IMPORTER â IMPLEMENTATION BRIEF

Target: one stdlib-only Python 3.12 importer â markdown memory store. Env verified: Python 3.12.10, sqlite3 3.49.1.
Modules allowed: `json, sqlite3, zipfile, tarfile, csv, re, io, pathlib, hashlib, datetime, argparse, os, shutil, html.parser, unicodedata`.

---

## 1. RANKED BUILD ORDER

### Tier 0 â already on disk, zero requests, build first
| # | Platform | Present on THIS machine | Effort |
|---|---|---|---|
| 1 | **Claude Code** | â `C:\Users\Lawre\.claude\projects` | low, schema measured |
| 2 | **Ollama desktop** | â `C:\Users\Lawre\AppData\Local\Ollama\db.sqlite` | low, schema dumped |
| 3 | **Open WebUI** | â not installed | low, documented |
| 4 | **LM Studio** | â not installed | med, msg keys unverified |
| 5 | **Cursor** | â not installed | high, KV-blob reverse-eng |
| 6 | **Windsurf** | â not installed | do last, key name unknown |

Tier 0 items 1â2 are the only things in this entire brief that can be tested today. **Write and validate the pipeline against those two, then bolt on the rest.**

### Tier 1 â real self-serve export, request now, parse later
Ranked by (schema confidence Ã likely data volume):
1. **ChatGPT** â best-documented shape, biggest corpus. `Settings > Data controls > Export`. 7d gen, 24h link.
2. **Claude.ai** â `Settings > Privacy > Export data`. 24h link.
3. **Claude Code** (no request needed, listed above).
4. **X/Grok archive** â `Settings > Your X data > Request archive`. Days. Verified schema (in-archive README).
5. **Google Gemini** â Takeout â **My Activity â Gemini Apps**, format switched to **JSON**. 7d link.
6. **DeepSeek** â Settings â Data â Export all chat history.
7. **Mistral Vibe** â `admin.mistral.ai/account/export` (NOT in the chat app).
8. **Pi** â Account â Download Chat history â `pi-user-history.json`.
9. **Character.AI** â Profile Settings â Account â Manage Account & Data â Export data.
10. **Perplexity** â `perplexity.ai/account/details` â Export my data.
11. **xAI grok.com** â `accounts.x.ai/data` â Download account data. (Separate store from #4.)
12. **Meta AI** â Accounts Center â Download your information â **choose JSON**, all-time range.
13. **Google AI Studio** â no button; pull the Drive folder `Google AI Studio` recursively.

**Fire off 1,2,4,5,6,7,8,9,10,11,12 today in one sitting.** Every one has a multi-day latency and a 24hâ4d download window. The importer is useless until the files land.

### Tier 2 â partial / per-conversation only
- **MS Copilot consumer** â activity-history CSV only, twice (Copilot apps + Copilot in M365 apps). Probably has no thread id â may be unusable for a memory store.
- **Poe** â one conversation at a time via `@export-chat` (.md) or `@savechats` (.json). No bulk.
- **Perplexity per-thread** â .md/.pdf/.docx, one at a time. Fallback only.

### Tier 3 â data request, 30-day turnaround, format unknown
- **Replika** â no self-serve. `help.replika.com/hc/en-us/requests/new`, category "Privacy & Safety". **Rewrite their template â it is a DELETION template.** Also: only last **4 months** of chat exists at all.
- **Qwen** â no verified route at all. Manual copy-paste or browser scrape.

### Tier 4 â no path, do not budget for
- **M365 Copilot (work/school)** â Graph API is **application-permission only**; a user cannot authorize their own data. Dead end without a tenant admin.
- **xAI API** â stateless, no LIST endpoint, 30d retention. Cannot reach consumer history.
- **Qwen** â see above.

---

## 2. THE SHAPES (six parser families, not twenty platforms)

Normalize everything to:

```python
Msg  = {id, parent_id, role, text, thinking, ts, model, attachments}
Conv = {source, source_id, title, created_at, updated_at, model, messages: [Msg]}
```
`role â {user, assistant, system, tool}`.

### SHAPE A â node-map DAG (`mapping` + parent/children)
**Platforms: ChatGPT, DeepSeek.** Same traversal, different leaf.

Common: root is `list` of conversations.
- **A1 ChatGPT** conv: `title, create_time, update_time, mapping, current_node, conversation_id, id`.
  node: `id, message, parent, children`.
  message: `id, author{role,name,metadata}, create_time, content, status, end_turn, weight, metadata, recipient`.
  content: `content_type` discriminates â `parts` (list of str **or** dict) for `text`/`multimodal_text`; `text`/`result`/`content` otherwise.
- **A2 DeepSeek** conv: `id, title, inserted_at, updated_at, mapping`.
  node: `children, message`. message: `fragments: [{content, role}]`.

**Traversal (shared code):** start at `current_node` (A1) or the root/leaf (A2), walk `parent` up, reverse. Never iterate `mapping.values()`.
**A1 filters:** skip `message is None`; skip `weight == 0.0`; skip `metadata.is_visually_hidden_from_conversation`; skip `author.name in {web.run, web.search, browser, bio, sonic_webpage, dalle.text2im}`.
**A2 filter:** fragments carry a type tag (values seen: `think`, `search`, `reasoner`, `chat`) â field name unconfirmed; do **not** concatenate all fragments blindly or reasoning leaks into answers.

### SHAPE B â conversation object with a flat message array
**Platforms: Claude.ai, LM Studio, Character.AI(v1), Google AI Studio, Perplexity(community tools).**

- **B1 Claude.ai** â root is a bare `list`. conv: `uuid, name` *(title lives in `name`, not `title`)*, `created_at, updated_at, chat_messages`.
  msg: `uuid, sender` *(values `human`/`assistant`, NOT `user`)*, `text` *(nullable!)*, `content: [{type: text|thinking|tool_use|tool_result, text}]`, `created_at`, `attachments: [{file_name, extracted_content}]`, `parent_message_uuid`.
  Read `content` blocks where `type=="text"`, join, fall back to flat `text`.
- **B2 Google AI Studio** â root is a single `dict`, one file per prompt. `runSettings, systemInstruction, chunkedPrompt{chunks:[{text, role, tokenCount, isThought}], pendingInputs}, citations`.
  `role == "model"` not `"assistant"`. **Drop `isThought: true` chunks.** `text` may be absent. No per-turn timestamps â use Drive file mtime.
- **B3 LM Studio** â root `dict`: `name, createdAt, messages[], lastUsedModel, tokenCount, systemPrompt`. **Message-level keys unverified â introspect at runtime.**
- **B4 Character.AI v1** â `external_id, created, last_interaction, msgs:[{uuid, id, text, src{is_human,name,user{...}}, tgt, is_alternative, image_rel_path}]`.
- **B5 Character.AI v2 (turn-based)** â `turn_key{chat_id,turn_id}, create_time, author{author_id,name,is_human}, candidates:[{candidate_id, raw_content, is_final, safety_truncated}], primary_candidate_id`. **Keep only the candidate whose `candidate_id == primary_candidate_id`** â the rest are swipes the user never saw.
- **B6 Perplexity (community tool output)** â `slug, title, steps:[{step_type, query_str, final_response}]`. Note `brianjhcho/perplexity-export` instead emits Claude-shaped `chat_messages[{sender,text,created_at}]` â that is the tool's own normalization, not Perplexity's.

### SHAPE C â id-keyed message dict + `currentId` pointer
**Platform: Open WebUI.** (Structurally A, but the dict is keyed and the pointer is named differently â keep separate.)

`[{chat:{title, models, history:{currentId, messages:{"<msg-id>":{id,parentId,childrenIds,role,content,model,done,timestamp}}}}, meta, pinned, folder_id, created_at, updated_at}]`
Legacy variant omits the `chat` wrapper. `history.messages` is a **dict keyed by id**, not a list; walk `currentId` â `parentId`.

### SHAPE D â flat event stream, reconstruct by GROUP BY
**Platforms: X/Grok, M365 Copilot Graph, Google Takeout My Activity.** One importer core: map each record to `(conv_key, ts, role, text)`, group, sort.

| | conv_key | ts | role source | text |
|---|---|---|---|---|
| **D1 X/Grok** | `chatId` | `createdAt` | `sender` (`user` â user, anything else â assistant; log unknowns) | `message` |
| **D2 M365 Graph** | `sessionId` (+`requestId` pairs turns) | `createdDateTime` (ISO) | `interactionType`: `userPrompt`/`aiResponse` | `body.content` (+`body.contentType` may be `html`) |
| **D3 Gemini Takeout** | id parsed out of `titleUrl` (`.../app/c/<id>`) | `time` (ISO-8601 Z) | inferred: prompt vs response record | `title`/`subtitles[]` for prompt; **`safeHtmlItem[].html` for response â UNVERIFIED** |

D1 wrapper: file is `.js`, body is `window.YTD.grok_chat_item.part0 = [...]`, and each element is double-nested under `{"grokChatItem": {...}}`.
D3 record keys (Google-documented): `header, title, titleUrl, subtitles, description, time, products, details, activityControls, locationInfos, imageFile, audioFiles, attachedFiles`.

### SHAPE E â JSONL linked list, one file per session
**Platform: Claude Code.** Measured on this machine.

Every line has `type`. Conversational lines (`user`/`assistant`) carry: `uuid, parentUuid, sessionId, timestamp, cwd, gitBranch, version, userType, isSidechain, entrypoint, message{role, content}`.
- `message.content` is a **plain string for real human prompts** and a **list of blocks otherwise**. Type-check before iterating or you iterate characters.
- Of 1236 `user` lines measured, 1151 blocks were `tool_result`; only ~81 string-content lines were the human. **Filter: `type=="user" and isinstance(message.content, str)`.**
- Drop `isSidechain == true` (subagent chatter). Drop `thinking` blocks from assistant text; keep `type=="text"`.
- 9 non-conversational line types (`attachment`, `ai-title`, `bridge-session`, `atis-latch`, `last-prompt`, `queue-operation`, `custom-title`, `system`, `started`, `result`) have **no `message` key**. Titles live on `ai-title`/`custom-title` lines keyed by `sessionId`.
- Wrap `json.loads` per line in try/except â live sessions produce torn last lines.

### SHAPE F â SQLite
**F1 relational (clean): Ollama.** Schema v17 dumped:
```sql
SELECT c.id, c.title, c.created_at, m.id, m.role, m.content, m.thinking, m.model_name, m.created_at
FROM chats c JOIN messages m ON m.chat_id = c.id ORDER BY c.created_at, m.id;
```
`messages.content` **and** `messages.thinking` are both text â thinking was the larger of the two in the sampled row (6410 vs 2541 chars). Read both. Check `settings.schema_version` and fail loudly on mismatch.

**F2 relational: Open WebUI DB** â `chat` table (`id,user_id,title,chat JSON,created_at BIGINT,...`) **and** newer normalized `chat_message` (`id,chat_id,user_id,role,parent_id,content JSON,output,model_id,...`). Detect which is populated; a parser for one returns zero from the other.

**F3 KV-blob: Cursor, Windsurf.** Tables `ItemTable(key,value)` and `cursorDiskKV(key,value)`, values are JSON strings.
Cursor: `composerData:{id}` â `{composerId, name, fullConversationHeadersOnly:[{bubbleId,type}], createdAt, _v}`; message text is in **separate rows** `bubbleId:{composerId}:{bubbleId}` â `{text, type (1=user, 2=assistant), thinking blocks, codeBlocks, toolResults, createdAt}`. `conversationMap` is legacy/empty. Order comes from `fullConversationHeadersOnly` only.
Windsurf: key name unknown â enumerate all `ItemTable` keys and detect by content.

**All SQLite sources: copy `db`, `db-wal`, `db-shm` together to scratch, open the copy read-only** (`file:...?mode=ro&immutable=1`).

### SHAPE G â non-JSON text
**G1 CSV**: MS Copilot consumer. Columns undocumented â `csv.DictReader`, sniff the header, never index positionally.
**G2 Markdown transcript**: Poe (`@export-chat`), Perplexity per-thread. Split on `User:`/`Bot:` line prefixes with the known failure mode that a body line matching the prefix corrupts the split â require the prefix at line-start after a blank line.

---

## 3. AUTO-DETECTION

No `--platform` flag. Dispatch on bytes â container â structure. Each detector returns `(name, score, note)`; highest score wins; ties and zeros go to a quarantine report, **never a silent zero-import**.

### Stage 1 â container sniff (first 16 bytes)
```
b"SQLite format 3\x00"        -> sqlite   (stage 4)
b"PK\x03\x04"                  -> zip      (recurse over members, re-enter stage 1 per member)
b"\x1f\x8b"                    -> gzip/tgz -> tarfile
starts with "window.YTD."      -> X archive .js  -> strip up to first "=", json.loads
ext .jsonl / >1 line each valid JSON obj -> stage 3
ext .csv or sniffable header   -> G1
ext .md/.txt                   -> G2
else                           -> json.loads -> stage 2
```

### Stage 2 â JSON structure discriminators (evaluate in this order)
```python
if isinstance(root, dict) and "conversations" in root: root = root["conversations"]   # ChatGPT defensive
if isinstance(root, dict) and "value" in root and root["value"] and "interactionType" in root["value"][0]:
    return "m365_graph"                       # D2
if isinstance(root, dict):
    if "chunkedPrompt" in root:               return "ai_studio"      # B2  <- strongest single key
    if "messages" in root and "lastUsedModel" in root: return "lm_studio"   # B3
    if "history" in root and "currentId" in root.get("history",{}): return "openwebui_legacy"  # C
if isinstance(root, list) and root:
    s = root[0]
    if set(s) == {"grokChatItem�