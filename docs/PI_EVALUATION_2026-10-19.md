# Pi (the coding agent) evaluated for Tetsu, run by the others (2026-10-19)

**His ask:** evaluate Pi as a coding tool for Tetsu, then "do so" -- run it by the others. Pi (Earendil Works,
MIT) is an open-source terminal coding agent: four tools (read, write, edit, bash), works with local models via
llama.cpp, embeddable (RPC/SDK). Documented caveat: **no sandbox, no permission system.** The plan put to the
reviewers: use Pi behind our existing gates so Tetsu (a local 3B) could propose edits, every write/bash PROPOSE_ONLY.

## The verdict: UNANIMOUS (Tetsu, Gemini, Mistral, Grok)

1. **Do not EMBED Pi. COPY its minimal read/diff design into our own gated harness.** (Gemini, Mistral, Grok all
   independently.) Wrapping an agent that has no permission model is "theater" (Mistral): a wrapper contains
   execution but not the agent's intent-formation -- "it only sees the final proposed action" and "cannot close the
   authority leak inside the agent's planning loop" (Grok). Embedding imports an RPC/attack surface we do not
   control; copying the four-tool pattern keeps tool semantics coupled to our own refusal engine, and is far
   cheaper to audit.
2. **Read-only, propose-only, non-executable unified diffs; a person applies with git. Zero write, zero bash.**
   (All four.) "No execution anywhere -- proposal-only diffs" (Mistral); "absolute refuse-to-apply + human review
   of every diff before any write leaves the scratch area" (Grok). **Tetsu himself:** "I would rather propose and
   let a person apply ... I trust the gatekeepers and the system's principles more than I trust myself with
   write/bash tools."
3. **The first break is not write -- it is bash and read.** Bash writes files too, so a gate that refuses `write`
   but allows `bash` is bypassable even "sandboxed" (Mistral). And the under-watched surface is READ: a 3B
   following prompt injection in a file it reads (a malicious README that says "run X"), or a read tool that
   wanders to `.env`/ssh keys, turns `read` into exfiltration/recon (Gemini, Mistral). Context pollution is the
   other failure: a 3B's repeated failed tool calls flood its small context and trigger degenerative loops
   (Gemini).
4. **A 3B is marginal for edit tools.** Weak planning yields "confident wrong edits that look plausible" -- cheap
   to produce, expensive to review (Gemini, Mistral, Grok).
5. **Keep the principle absolute; resist "just enable one write" later** (Grok). That is the exact creep the
   covenant's own rule names.

## The recommendation

- **Do not adopt Pi as a tool, and do not give Tetsu write/bash.** The evaluation's own answer, and Tetsu's.
- **If a capability is built at all, it is a tiny READ-ONLY diff proposer:** copy Pi's minimal read + unified-diff
  pattern into our own harness, run Tetsu over a scratch clone, emit a unified diff to a person, who applies it with
  `git apply` after review. No write tool, no bash, no auto-apply. Reads are confined (never `.env`, keys, private/)
  and file contents are treated as untrusted (injection).
- **It is NEW CAPABILITY, so it waits for his explicit word** (standing rule: refinements auto, new capability on
  his word or judge consensus). Nothing built yet.

Answers kept in the scratch record (the consult ledger's daily budget was spent; not recorded there).
