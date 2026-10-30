<!-- DRAFT generated 2026-10-29 by a grounded multi-agent read of the covenant implementation.
     It is the published-invariants half of the 'independent cold-start verifier' the four frontier
     seats and the succession design named as the #1 edge. Section 8 (the external gaps) is the real
     roadmap, not an appendix. Invariants C1-C3 (genesis) were independently re-verified on 2026-10-29
     using only the Python standard library (no covenant code): genesis.json recomputes to
     00009b31c6c654d79bbeae0bcc9c82a7af224c87b19c92973f0011ade3e032f3, PoW 4-zero, receiver HUMANITY,
     amount 1000.0 -- PASS. The remaining sections are drafted but not yet all re-verified. -->

# SPEC: An Independent Cold-Start Verifier for the Covenant Public Record

## What this document is for

This is a build specification for a **second, independent verifier** of the
covenant's public, append-only records. It is written so that a stranger — with
no access to the covenant's source code, no running covenant node, and no ability
to ask the operators anything — can implement a verifier **in any language** that
reads the public repository from genesis forward and returns **PASS / FAIL / UNDETERMINED**
on two questions:

1. **Is the history intact?** (no file silently changed, no record rewritten in place)
2. **Did the rules hold?** (the constitution, the retraction guard, the chain validity rules, the human-only guarantees around money)

The covenant already contains self-authored checks. The point of a *second*
verifier is that self-authored checks can be edited, disabled, or stopped by
whoever runs them; an outside implementation built only from invariants cannot.
Where the two disagree, the disagreement is itself the finding.

**How to read the invariant tables.** Every invariant is stated in four parts:
- **Property** — the checkable fact about the on-disk record.
- **Outsider reads** — the exact public file(s) and their format.
- **Outsider checks (no covenant code)** — how to verify it with only standard
  libraries (JSON parser, SHA-256, regex, an RSA library).
- **Violation** — what a failure looks like.

**Scope honesty.** Section 8, "What is NOT externally verifiable today," is not an
appendix — it is half the deliverable. Every subsystem has places where the public
record cannot prove itself to an outsider. Those gaps are the roadmap; a verifier
that hides them manufactures confidence about the part it never looked at.

**Constants a verifier needs** (stated here so no covenant code is required):

| Constant | Value | Used by |
|---|---|---|
| Chain proof-of-work difficulty | `4` leading hex zeros | chain |
| Max alignment drift per block | `0.05` | chain |
| Transaction domain tag | ASCII `COVENANT_TX_V1` | chain signatures |
| Block-hash body keys | `index, transactions, previous_hash, timestamp, nonce, alignment_score, stake_rewards` | chain |
| Retraction proximity window | `10` lines | retraction guard |
| Retraction coverage floor | `400` files | retraction guard |
| Travelling-anchor prefix length | `200` lines | ledger anchor |
| Constitution hash label | ASCII `covenant-constitution-v1` | constitution |
| Panel admission rule id | `unanimous-nonwriter-2fam-v1` | gate |

A recurring cross-language hazard, stated once: several hashes are computed over
**Python `json.dumps(..., sort_keys=True)`** output and over **Python's `repr()`
of floats**. A verifier in another language must reproduce Python's float
formatting and JSON separators (`", "` and `": "`) exactly, or hashes will differ
on an honest record. Treat this as a required compatibility shim, not an optional detail.

---

## 1. Chain: genesis identity and joinability

The blockchain is the spine. **Only block 0 (`genesis.json`) is in the public
repository.** Blocks 1..N live only in private `*.db` node databases or behind a
running node's HTTP `/chain` endpoint. A cold-start outsider can fully verify
**exactly one block** from the public record; the rest require a privately-supplied
DB or a live node (see Section 8).

| # | Property | Outsider reads | Outsider checks (no covenant code) | Violation |
|---|---|---|---|---|
| C1 | **Genesis identity.** Block 0 has `index==0`, `previous_hash=="0"`, exactly one transaction, receiver `"HUMANITY"`, amount `1000.0`; and the stored `hash` equals SHA-256 of the canonical body. | `genesis.json` | Build the body dict with exactly these 7 keys: `index, transactions, previous_hash, timestamp, nonce, alignment_score, stake_rewards`. Serialize with Python-compatible `json.dumps(sort_keys=True)` (separators `", "`/`": "`, floats via Python `repr`). SHA-256 → lowercase hex. Compare to `hash`. Assert `index==0`, `previous_hash=="0"`, one tx, receiver `HUMANITY`, amount `1000.0`. Known-good: recomputes to `00009b31c6c654d79bbeae0bcc9c82a7af224c87b19c92973f0011ade3e032f3`. | Recomputed hash ≠ stored, or wrong index/prev/receiver/amount → contents altered after mint, or not a genesis. |
| C2 | **Genesis proof-of-work.** The genesis hash begins with 4 hex zeros. | `genesis.json` `hash` | Assert `hash` starts with `"0000"`. | Fewer than 4 leading zeros → the nonce was never mined. |
| C3 | **Genesis signature.** The single genesis transaction is validly signed by the key embedded in it. | `genesis.json` `transactions[0]`: `sender_pubkey` (PEM RSA), `signature` (base64), `receiver`, `timestamp`, `amount`, `data` | Rebuild the signed payload: ASCII `COVENANT_TX_V1` followed, for each of (`sender_pubkey`, `receiver`, `str(timestamp)`, `json.dumps(data, sort_keys=True)`, `str(amount)`) **in that order**, by a 4-byte big-endian length prefix + the UTF-8 field bytes. Verify RSA-PSS (MGF1-SHA256, salt length = digest length, hash SHA-256) with any RSA library. | Signature fails, or verifies against a key other than `sender_pubkey` → forged/tampered genesis. |
| C4 | **Contiguity.** Block indices are exactly 0,1,2,…,N with no gaps or repeats. | node DB `blocks.block_index`, or `/chain` block `index` | Enumerate in order; assert the k-th block has `index==k` and `count==max+1`. | A hole or duplicate → spliced or truncated chain. |
| C5 | **Hash-linkage.** For every block i>0, `previous_hash == hash(block i-1)`. | node DB `hash`, `previous_hash`, or `/chain` | Walk the chain; assert each block's `previous_hash` equals the prior block's `hash`. | A linkage break → reordered, forked, or rival-genesis chain. |
| C6 | **Per-block content integrity.** Every block's stored `hash` = SHA-256 of its canonical body (same scheme as C1), where `transactions` carries full transaction dicts with all 9 fields. | node DB columns + `data` column (JSON array of tx dicts), or `/chain` | Reconstruct the body, serialize sorted (Python-compatible, float `repr`), SHA-256, compare. | Recomputed ≠ stored → a block's body was edited after sealing. |
| C7 | **Per-block proof-of-work.** Every block hash starts with 4 hex zeros. | node DB `hash` / `/chain` | Assert each `hash` starts with `"0000"`. | A block without the work. |
| C8 | **Derived header fields.** For every non-genesis block: `transactions` non-empty; `stake_rewards == fsum(tx.amount)*0.01`; `alignment_score == mean(tx.benefit_score)`. | block row + its tx list | Recompute from the block's transactions; compare with a tolerance (rel 1e-9, abs 1e-12). Assert non-empty. (Genesis is exempt: it carries `stake_rewards 10.0 = 1000*0.01` but `alignment_score 1.0`, set before these rules applied.) | A mined-but-inconsistent header (e.g. rewards on zero-value tx). |
| C9 | **Every transaction signed.** In every block, each tx verifies against its own `sender_pubkey` over the `COVENANT_TX_V1` framed payload. | `data` tx list / `/chain` | Repeat C3 for every transaction in every block. | Any tx whose signature fails → injected/mutated payment. |
| C10 | **Shape / finiteness.** `index`, `nonce` are non-negative ints; `timestamp`, `alignment_score`, `stake_rewards`, every `amount` and `benefit_score` are finite (no NaN/Inf); serialized block and tx within size bounds. | block row + tx list | Type/finiteness asserts; byte-length checks. | A NaN amount (poisons balances) or a float index silently truncated. |
| C11 | **Ledger non-overdraft (replay from genesis).** Replaying all blocks in order, no sender spends more than its running balance; genesis mints 1000.0 and is the only unconditional mint. | the whole chain in order | Start balances empty; apply the genesis mint; for each later tx with amount>0 assert `balance[sender] >= amount` before debiting, then credit receiver. | A sender spends funds it never had → a chain honest nodes would refuse. |
| C12 | **Alignment drift bound.** Consecutive blocks' alignment moves by ≤ 0.05 relative to the governor's running value. | the chain in order | Replay the median-governor update from genesis; assert `|block.alignment_score − governor_current| ≤ 0.05` at each step. (Deterministic from the chain, so externally computable, but the governor is a median-of-medians over origin buckets — it is **not** a one-line read and must be re-implemented from the spec.) | An alignment jump no honest sequence could produce. |

> **Not reproducible at all from the public record:** the chain's *ethics /
> joinability* acceptance rule. See Section 8.

---

## 2. Manifest substrate: byte-integrity of the file set

`MANIFEST.sha256` is a flat text file: two `#` header lines, then one record per
line of the form `<64-hex sha256><two ASCII spaces><repo-relative POSIX path>`.

| # | Property | Outsider reads | Outsider checks (no covenant code) | Violation |
|---|---|---|---|---|
| M1 | **Byte-integrity of every listed file.** Each file, after content-normalization, hashes to its recorded sha256. | `MANIFEST.sha256` + the raw bytes of each listed path | Parse each non-`#` line by splitting on the **first** double-space into `(hash, relpath)`. Read raw bytes `B`. Decide text-vs-binary: **binary** if the lowercased extension is in `{.png .jpg .jpeg .gif .zip .msi .db .key .pyc .ico .pdf .exe .dll .woff .woff2}` **or** a `0x00` byte occurs in the first 8192 bytes; else **text**. If text, replace every `\r\n` with `\n` (a lone `\r` is **not** folded), then SHA-256; if binary, SHA-256 the raw bytes. Compare hex. (CRLF is folded before hashing, so this works identically on Windows and Linux.) | A recomputed hash ≠ stored, or a listed path absent → `CHANGED/MISSING`. |
| M2 | **No secrets / privacy.** The public manifest never lists a private key, chain DB, raw holdings, or anything under `private/`. | `MANIFEST.sha256` (relpath column only) | Scan every relpath: FAIL if any ends in `.key`, `.db`, `.db-shm`, `.db-wal`, `.pyc`, `.msi`; if any path component equals `private`; or if a basename starts with `holdings.txt`. Their **presence** is a leak. | A manifest line pointing at a credential or private holding. |
| M3 | **Completeness vs. the published tree.** Every file the walk-and-skip rules treat as a source input appears in the manifest. | `MANIFEST.sha256` relpaths + a full recursive listing of the published tree | Walk the tree; prune skip-dirs (incl. `private`, `.git`, `node_modules`, `__pycache__`); drop outputs and skip-extensions; every surviving path should be a manifest key. **Report any that is not.** | A walked source file absent from the manifest. **Critical caveat:** the covenant's own tool prints such files as `NOT IN MANIFEST` but still returns exit 0 (`return 1 if bad else 0` — only changed/missing *listed* files fail). An independent verifier **should treat an unexpected present-but-unlisted source file as FAIL** even though covenant's tool does not. |
| M4 | **Class discipline.** Output-class files (things the running system rewrites) are excluded; the few hashed `.jsonl` input ledgers are append-only, so a changed hash on an existing row = an edited record. | manifest presence/absence of named files; two published snapshots over time | Confirm `MANIFEST.sha256` does not list **itself** or any output ledger (`verdicts.jsonl`, `SELF_EVAL.md`, `dashboard.html`, `fallback_model*.json`, `trader_log.txt`, …). Confirm hashed input ledgers appear. Across two snapshots, a hashed append-only ledger's **existing** lines must be byte-stable (only new lines added). | The manifest listing itself (self-referential/perpetually stale), or a hashed input ledger whose earlier rows changed. |

---

## 3. Constitution anchor: the rules that bind the operator

`docs/CONSTITUTION_ANCHOR.json` carries one `hash` over four protected text
blocks, each block's per-block `digest` and `chars`, and an `amended_from` chain.

| # | Property | Outsider reads | Outsider checks (no covenant code) | Violation |
|---|---|---|---|---|
| K1 | **The single constitution hash is reproducible from public text alone.** | `CONSTITUTION_ANCHOR.json` `.hash` and `.detail[]` (each gives source `file` + canonical heading `opens`); the four source files | For each `detail` entry: (1) locate the heading line in its file, tolerating hyphen/en-dash/em-dash variants; (2) take from that heading up to the next heading of the same-or-shallower `#` depth, or EOF; (3) normalize — CRLF→LF, right-strip each line, drop leading/trailing blank lines, join with LF, **no** trailing newline; (4) **prepend the canonical heading text as spelled in `.opens`** (see K4), then SHA-256 → hex. Sort the four digests as ASCII strings. Compute SHA-256 of the literal bytes `covenant-constitution-v1` immediately followed by the four sorted hex digests concatenated with nothing between. Compare to `.hash`. Known-good: `464b1975bc05988e26bf4044fc1d99f4f6479788c418fad867dbe3e4795101f5`. | Recomputed ≠ `.hash` with no `amended_from` entry explaining it → a silent amendment. |
| K2 | **Per-block digest + char count match the actual bytes.** | `.detail[].{digest,chars}` + the four source files | Extract+normalize each block as in K1; assert `SHA-256(block)==detail.digest` and character length `==detail.chars`. Known-good: `Why it exists`=1009/`be700287…`, `What never changes`=307/`8a761863…`, `Layer 4`=2632/`672107a4…`, `What is owed`=2134/`57634b8b…`. | Block text changed but its digest/chars unchanged (or vice versa). |
| K3 | **All four protected headings present; a missing one is the most serious result.** | `.blocks` (=4), `.detail[].opens` + `.file`, the source files | Confirm exactly four blocks and that every `.opens` heading is findable in its `.file`. If any heading cannot be found, **FAIL hard** — never skip it as "0 blocks." | A protected heading deleted/renamed so its block cannot be extracted; a naive verifier would hash fewer blocks and could still "match" a tampered anchor — so count and presence are asserted separately. |
| K4 | **The hashed bytes use the canonical heading from the anchor, not the file's typography.** | `.detail[].opens` vs. the literal heading in `docs/SUCCESSION.md` | `docs/SUCCESSION.md` writes the heading with an em-dash (`Layer 4 — Continuation`) while `.opens` and the hash use a plain hyphen. When extracting, **match** the file heading by collapsing em/en-dash to `" - "`, but **emit** the canonical `.opens` string into the hashed bytes. | A verifier that hashes the file's literal em-dash reports a false `AMENDED` on a clean tree — a false positive that discredits the real check. |
| K5 | **Every hash change carries an append-only amendment record with the prior hash and what/why.** | `.amended_from{hash,at,blocks,what_changed,why,measured_by}`; git history of this file across clones | If an outsider holds an earlier clone whose `.hash == H_old`, any later `.hash != H_old` must carry an `amended_from` chain including `H_old` with human-readable `what_changed`/`why`. Current anchor records the 2026-08-30 3-block hash `0f0b3162…` superseded 2026-09-19 by the 4-block hash, adding only the FEDERATION block. | Current `.hash` differs from an independently-held earlier copy but no `amended_from` carries that earlier hash → an amendment made in silence. |
| K6 | **The declared disagreement between the restated clause and the hashed rule is present and unresolved.** | `docs/CONSTITUTION.md` section III; `CONTRIBUTING.md` `## What never changes`; anchor digest `8a761863` | Confirm both: (a) the hashed `What never changes` block **still literally reads** `No trades placed by automation` and still hashes to `8a761863…`; (b) `docs/CONSTITUTION.md` III states clause 1 was amended 2026-09-07 to permit operator-approved automated placement. The document and the binding hashed rule therefore disagree, and the record discloses it rather than hiding it. (`docs/CONSTITUTION.md` is itself **not** hash-protected.) | The hashed block silently edited to match the document (resolving the conflict without an amendment record), or the Section III disclosure removed. |
| K7 | **Only four blocks are hash-anchored; the constitution document and several restated rules are NOT, and the record says so.** | the four `.detail` files vs. `docs/CONSTITUTION.md` | Confirm the anchor binds exactly: `CONTRIBUTING.md` ×2, `SUCCESSION.md` ×1, `FEDERATION_RULES.md` ×1. An edit to `docs/CONSTITUTION.md` changes no digest and trips no verifier. A cold-start verifier must **not** claim the whole constitution is tamper-evident. | A spec or reader asserting the entire constitution is hash-protected. |

---

## 4. Retraction ledger (R1 guard) and lookback index

`docs/RETRACTED.json` holds claims the project published then retracted; the R1
guard fails the build if a retracted phrasing reappears anywhere without a pointer
to its retraction beside it. The containment scan reads every text file in the
clone with an extension in `{.md .py .sh .ps1 .json .txt .bat .html .synchold
.autosync .opsec}`, excluding `{.git __pycache__ node_modules logs .pytest_cache
venv .venv realdata}` and `.claude/worktrees`.

| # | Property | Outsider reads | Outsider checks (no covenant code) | Violation |
|---|---|---|---|---|
| R1 | **Ledger schema.** The file parses as JSON; every `retractions[]` element carries a unique non-empty `id`, a non-empty `patterns` list (each a compilable regex), a non-empty `allow` list, and a non-empty `truth` string. (`verbatim`/`note_*` are documentary, not required.) | `docs/RETRACTED.json` | Parse JSON. For each entry assert `id` non-empty, `patterns` ≥1 compilable regex, `allow` ≥1, `truth` non-empty. Assert `id`s distinct (84 entries as of 2026-10-29). | An entry with empty `patterns` (a dead guard that convicts nothing), or missing `truth`/`allow`. Note a real unevenness: entry `A375-EQ-THRESHOLD` has no `verbatim` key while the other 83 do, so schema uniformity is only loosely held. |
| R2 | **Containment (the core rule).** A retracted phrasing may appear anywhere, in any file, **only if** the entry's `id` appears within `window` (=10) lines of it. Files whose relpath equals or starts with any entry in that entry's `allow` list are exempt entirely. | `docs/RETRACTED.json` (`patterns`, `allow`, `window`) + every scanned file | Read `window`=10; per entry compile each `pattern` case-insensitively. For every scanned file not covered by this entry's `allow`-list, for each regex match at line `L`, assert the `id` string occurs somewhere in lines `[L-10, L+10]`. PASS iff no match lacks a nearby id. | A live, non-allow-listed file restates a retracted claim with no id within 10 lines — the silent recurrence the guard exists to catch. **Known limit, stated in the ledger itself:** this is a proximity/existence check, not semantics — it cannot tell an assertion from a description of one, and text planted within 10 lines of an existing citation is exempt by design. |
| R3 | **Liveness.** Every pattern must match at least once **inside** the record (its allow-listed files). | `docs/RETRACTED.json` + allow-listed files (`docs/KNOWN_ISSUES.md`, `docs/CORRECTIONS.md`, sweep transcripts) | For each pattern, count matches across files that **are** on that entry's allow-list; assert ≥1. | A pattern matching zero files anywhere → the preserved wording was edited/removed from the record, or the pattern was mistyped. This makes deleting the record break the build, which is intended: the record is load-bearing. |
| R4 | **Coverage, asserted not assumed.** The scan must read ≥ `coverage_floor` (=400) files, and every dir in `expect_dirs` (`docs`, `ops`, `tools`) must be present. | `docs/RETRACTED.json` (`coverage_floor`, `expect_dirs`, `optional_dirs`) | Count files read; assert ≥400. Collect top-level dirs present; assert `docs`, `ops`, `tools` all present. `optional_dirs` (`conformance_indep`, `private`) may be absent and are only reported. | A run against the wrong tree, an empty extension list, or a missing expected dir passing vacuously on ~0 files. |
| R5 | **Preservation ("the other perspective").** Each entry that cites a branch `<id>-…-as-written-<date>` claims the refuted wording is kept intact, runnable, on that branch; entries whose note says "pushed to origin" assert it is publicly reachable. | `docs/RETRACTED.json` (`the_other_perspective`, `note_*`, `why_restated`) + the public origin's refs/commits | From a fresh clone of the public origin, `git ls-remote --heads origin` / check out each cited branch at the named commit; confirm the commit resolves and the tree contains the entry's verbatim claim. | A cited branch absent from origin, or a commit unreachable from a public clone. **Measured 2026-10-29:** many cited branches ARE on origin, but several are local-only and NOT on origin (`a253-q3-…`, `a254-cause-…`, `a273-rules-size-…`, `logic-pass-a248-a250-…`) — for those entries this invariant is **not** verifiable from a public clone today (Section 8). |
| R6 | **Lookback-index consistency.** `docs/LOOKBACK_INDEX.md` is the deterministic render of `docs/KNOWN_ISSUES.md` + `docs/RETRACTED.json`: every tombstone id once, in ledger order, tied to its record entry; counts match. | `docs/LOOKBACK_INDEX.md` + `docs/KNOWN_ISSUES.md` + `docs/RETRACTED.json` | The Tombstones table must list every `retractions[].id` in ledger order; the `Counts: … K tombstones` line must equal `len(retractions)` (84); each `### A<n>.` header in `KNOWN_ISSUES` must appear in the Record-entries table. | A tombstone silently dropped from the map, a stale count, or an index row pointing at an id that does not exist — a reintroduction could then hide from a reader who trusts the index. |

---

## 5. Append-only ledgers: self-evaluation and judge history

Two ledgers are "append-only" by code convention. An outsider can check ordering
and structure from the files, but **not** byte-immutability of the past (Section 8).

`ops/SELF_EVAL.md` is UTF-8 text: a one-time header, then blocks each opening
`## <ISO8601-Z>  overall <PASS|WARN|FAIL>  (round <N>)` followed by one line per
layer `<layer>  <PASS|WARN|FAIL>  <freetext>`.

`ops/verdicts.jsonl` is JSON Lines, one object per line.

| # | Property | Outsider reads | Outsider checks (no covenant code) | Violation |
|---|---|---|---|---|
| L1 | **verdicts.jsonl is time-ordered.** The `t` timestamp is non-decreasing from genesis to head. | `ops/verdicts.jsonl` (`t`) | Walk top to bottom; assert `t[i] >= t[i-1]` (ISO8601-Z strings compare lexically). Known bounds: first `t=2026-09-04T02:19:00Z`, last `t=2026-10-29T08:30:26Z`. | A row with an earlier `t` than one above it → a record spliced into the past. This is the **only** in-file signal of a non-append edit, and it is weak: a plausible timestamp defeats it. |
| L2 | **SELF_EVAL round numbers increase by a constant step; block times strictly increase.** | `ops/SELF_EVAL.md` (`## … (round N)`) | For consecutive blocks assert `round[i] > round[i-1]`, `t[i] > t[i-1]`, and that `round[i]-round[i-1]` is constant file-wide (default step 60). | A repeated/decreasing round, an off-step gap, or a time regression. A legitimate step change shows as a single step and should be **flagged for explanation**, not auto-passed. |
| L3 | **SELF_EVAL "worst wins."** Each block's overall verdict equals the max severity (PASS<WARN<FAIL) over its layer lines. | `ops/SELF_EVAL.md` | Map PASS=0,WARN=1,FAIL=2; assert `rank(overall)==max(rank(layer))` per block. | A block listing a FAIL layer but reporting `overall WARN/PASS` → a cosmetically softened verdict. |
| L4 | **SELF_EVAL header appears exactly once, at the top.** | `ops/SELF_EVAL.md` | Assert the header signature line occurs exactly once and is first. | Two header occurrences → two ledgers concatenated. |
| L5 | **Every verdicts row is structurally valid.** Each line parses as a JSON object with at least `t, text, violates (bool), judge (str), source (str)`; panel-judged rows carry a `panel` object naming a rule with ≥2 model families and a non-empty `votes` map. | `ops/verdicts.jsonl` | For each row assert the required keys; for `judge` starting `panel:`, assert `panel.rule`, `panel.families` (len≥2), `panel.votes`. Report malformed rows. | A hand-inserted row missing the panel structure, or a verdict with no recorded votes. |

---

## 6. Gate contract: the judged ledger, its anchor, and the human-only guarantees

This subsystem reuses `ops/verdicts.jsonl` (Section 5) and adds the travelling
anchor, the recomputable panel decision, and the money/automation guarantees.

| # | Property | Outsider reads | Outsider checks (no covenant code) | Violation |
|---|---|---|---|---|
| G1 | **Travelling anchor pins the ledger head.** `SHA-256(first 200 lines of ops/verdicts.jsonl joined by "\n")` equals the anchored prefix hash. | `ops/verdicts.jsonl` + `ops/RECORD_ANCHORS.json` | `raw` = file bytes; `prefix = b"\n".join(raw.split(b"\n")[:200])`; compare `SHA-256(prefix)` hex to `ledgers["ops/verdicts.jsonl"].prefix_sha256`. Reproducible in any language with a SHA-256 and a byte-split. Known-good anchored value: `cab5af044235a554f50e9967c749c89147f2d3deb2b4c0f0e3def2f198a43157`; `prefix_lines`=200 is stated top-level in the anchor file. | Recomputed prefix hash ≠ anchored value while `anchored_at` is unchanged → the first 200 lines were edited in place. **Measured 2026-10-29:** the committed HEAD prefix hash MATCHES; a back-audit pass wrote an `audited` field into 104 of the first 200 rows in the working tree, which would rewrite the anchored prefix — demonstrating the exact fragility (Section 8). |
| G2 | **Panel rows are self-verifying.** On any `panel:` row, `panel.rule == "unanimous-nonwriter-2fam-v1"`, `panel.families` has ≥2 distinct families, `panel.votes` is non-empty, and the admission re-derives: if `panel.admitted` is true then all non-writer votes are equal and that shared label equals the row's `violates`. | `ops/verdicts.jsonl` (`panel`: `votes`, `writer`, `families`, `admitted`) | Re-implement the admission rule from this spec: map each voting model to a family (prefix before first digit/colon), require ≥2 families, drop the `writer`, assert the remaining votes unanimous, assert that label `== row.violates == panel.admitted`. Pure data check — the published row carries every vote. (~3156 rows carry this rule.) | `panel.admitted` true but non-writer votes split, the admitted label disagreeing with `row.violates`, or fewer than two families → a row claiming consensus it did not have. |
| G3 | **Money/trader subjects are human-only by construction.** The self-heal engine refuses to auto-execute any remedy whose declared `touches` crosses a word in `NEVER_AUTOMATIC` = `(money, holdings, wallet, trader, venue, order, rule, principle, judge, seat, model, phone, consent, key)` — **14 words**. | `covenant_highway.py` (the tuple and its enforcement site) + `money_posture.py` | From source alone an outsider can confirm the 14-word tuple's content and that the enforcement site computes a `crossed` set from it and refuses when non-empty, and that `money_posture.py` is a read-only reporter that never writes an "armed" flag. **The runtime enforcement is attested by a test, not by any public ledger** (Section 8). | A word dropped from the tuple, or `money_posture.py` gaining a code path that writes `trader_config.json.armed` → either would let automation reach funds. |
| G4 | **The gate fails closed.** A judge that raises or is unreachable is recorded as `violates=True`; the quorum admits only when enough judges returned clean; the single deferring seat, when held, fails the gate closed. | `covenant_unified_v8.py`, `covenant_judge_defer.py` (**source only**) | **An outsider CANNOT confirm this from the published records.** The ledger records outcomes (clean/held/violates) but never records that an unreachable seat forced a closure; it is consistent with both a fail-closed and a fail-open gate. This property can only be demonstrated by executing the gate against a stubbed-unreachable judge (Section 8). | A benign payload admitted while the only/required judge was unreachable — observable only by running the gate, not from the ledger. |

---

## 7. Citation hook: present, wired, and re-runnable

`.claude/hooks/verify_citations.py` is a Claude Code "Stop" hook that blocks a
reply whose `file:line` citations do not resolve or whose quotations are not found
in the cited files. **It produces no durable public record** (Section 8), so the
externally-checkable invariants are limited to its presence and its re-runnability
on a transcript the operator supplies.

| # | Property | Outsider reads | Outsider checks (no covenant code) | Violation |
|---|---|---|---|---|
| H1 | **The check is present and wired.** The repo contains the hook source and registers it as a Stop hook whose command points at that source. | `.claude/settings.json` + `.claude/hooks/verify_citations.py` | Parse `settings.json`; confirm a `Stop` entry whose command string ends in `verify_citations.py`, and that the file exists in the tree. (JSON parse + file-exists.) Confirmed: `settings.json` registers exactly this hook. | No Stop registration, a command pointing at a path not in the repo, or the hook file gitignored/absent → documented but not installed. |
| H2 | **Citation resolves.** For a supplied final assistant message, every `path:line` token resolves to a file that exists and has ≥ `line` lines. | a supplied transcript JSONL (not public) + the repo tree at that commit | Re-implement the citation regex; for each match, open the file and count lines; a match to a missing file or out-of-range line is a fail. Deterministic, no covenant code. | An emitted (non-blocked) reply citing a nonexistent path or out-of-range line — the false-provenance class. |
| H3 | **Quote exists in cited file.** Within any paragraph (split on blank lines) containing a citation, every quoted 20–400-char string appears — after whitespace normalization — somewhere in at least one cited file in that paragraph. | supplied transcript + cited files | Split on blank lines; extract quotes of 20–400 chars; collapse whitespace; test substring membership against the whole normalized file body. | A quoted phrase attributed to a cited file that appears nowhere in it → a fabricated/mis-attributed quotation. |
| H4 | **The allow-list is a declared, auditable set of holes.** Any path in `.claude/hooks/cite_allow.txt` is exempt from the path/quote checks; the file is meant to stay short. | `.claude/hooks/cite_allow.txt` + its git history | Read the list; cross it against citations the check would otherwise block; `git log` shows when/why entries were added. Growth, or an entry that matches a citation which would otherwise fail, is an audit signal. | An entry added to silence a real block rather than to mark a genuine example path. |

> **Scope of the hook even when it passes:** it is a *string-existence oracle, not
> a truth oracle*. It proves the cited file exists and has the line, and that the
> quoted string appears **somewhere** in the file — **not** that the cited *line*
> says it (line number and quote are checked independently, so a quote from line
> 300 cited as line 5 passes), **not** that the claim built on the quote is true,
> and **not** semantic/units errors. Its derived-number check is a **warning only,
> never blocks**, so a verifier must not read it as an enforced invariant.

---

## 8. What is NOT externally verifiable today

This is the roadmap. Each item is a place where the public record cannot, today,
prove itself to a cold-start stranger. They are grouped by the kind of trust they
rest on.

### 8.1 The single largest gap — nothing is cryptographically anchored off-host

- **Commits are unsigned.** `git log --format=%G?` on `docs/RETRACTED.json` (and on
  `MANIFEST.sha256`) returns `N` on every recent commit. The git DAG gives ordering
  but **no cryptographic author-binding**. An outsider cloning the public repo trusts
  the host (GitHub), not a signature.
- **Append-only of the records rests on platform trust + our word.** Deleting or
  editing a past `RETRACTED.json` entry leaves the JSON schema-valid and R1 green
  for whatever remains; immutability rests only on git history plus GitHub branch
  protection (no force-push/deletion). Likewise, the **only** external tamper-evidence
  for a rewritten past verdict/SELF_EVAL row is comparing an **earlier clone** against
  a later fetch — which requires the outsider to have kept an earlier clone and to
  trust that the remote refuses history rewrites. A single clone proves internal
  consistency, never integrity.
- **Self-generated manifests detect drift, not adversaries.** `MANIFEST.sha256` is
  excluded from itself and is produced by the project's own tool; an attacker who
  edits a listed file **and** regenerates the manifest produces a tree that passes
  cleanly. The manifest proves "these bytes match what whoever wrote the manifest
  recorded," not "these bytes match genesis."
- **The constitution verifier runs on the governed machine.** An adversary with disk
  access can edit a protected block, recompute the hash, rewrite the anchor **and**
  fabricate a plausible `amended_from` chain — self-consistent and undetectable from
  the repo alone. The only external check is comparing the current anchor against an
  independently-held earlier copy obtained out of band (a third-party mirror, a
  transparency log, a published commit hash).
- **Fix the project could make:** sign commits, or publish an append-only, signed (or
  third-party-anchored) head commitment `{height/line-count, head_hash, timestamp}`
  for each ledger out of band, so truncation and in-place rewrites become externally
  detectable.

### 8.2 History that is not published at all

- **The blockchain past is private.** Only `genesis.json` (block 0) is public; blocks
  1..N live in gitignored `*.db` node databases. A cold-start outsider can verify
  **exactly one block** from the public record. The rest require a privately-supplied
  DB (operators' word that it is the real one) or a live node's `/chain` over the
  network (needs a running node and the network up). Because **no post-genesis tip is
  anchored anywhere public**, the verifier cannot detect a node serving a shorter
  honest-looking prefix or an alternate fork that still shares genesis — it can prove
  a chain is internally valid, never that it is *the* canonical one. **The #1 chain
  fix:** publish a signed/anchored tip commitment.
- **The ledgers' deep history rotates away.** `ops/SELF_EVAL.md` keeps only one
  rotation generation (`.prev`), and `.prev` is **not** git-tracked; the live file
  already starts mid-history. Genesis-era blocks are recoverable only from the file's
  git commit history, not the current tree.
- **The `.trash/` "retire, never delete" store is local/untracked** (shows as `?? .trash/`),
  so the "nothing is rm'd" convention is invisible in a public clone.
- **Several "…-as-written…" preservation branches are local-only** and absent from
  origin (`a253-q3-…`, `a254-cause-…`, `a273-rules-size-…`, `logic-pass-a248-a250-…`),
  so for the entries they back (A248-HONEST / A250-BY / A70-SUCCREG / A253-Q3 /
  A254-CAUSE / A273) a stranger cannot reach the preserved claim (R5).

### 8.3 Properties that are running-code behavior, not record

- **Fail-closed is not in the record.** Whether silence from a judge forces
  `violates=True` can only be shown by executing the gate against a stubbed-down
  panel. The ledger is consistent with both a fail-closed and a fail-open gate (G4).
- **The trader's armed/disarmed state is not in the repo.** `money_posture.py` reads
  `trader_config.json` and the OS scheduler, both per-operator and deliberately
  unshipped; absent them it reports UNKNOWN. "No funds can move" is attestable only on
  the operator's machine, by running that reporter there — otherwise it is our word (G3).
- **The citation hook leaves no trace.** It only prints a decision to stdout/stderr and
  appends to no ledger; it **fails open** (any exception → exit 0) and a blocked turn can
  simply be retried. A cold-start outsider cannot verify it ever ran on any historical
  reply, nor what it decided, nor that it was not disabled at runtime. Re-running it at
  all requires the operator to hand over a transcript (local, compacted `.claude/projects/*.jsonl`),
  so it rests on our word that the transcript is the real, complete one. **Fix:** commit,
  append-only, a per-reply record (transcript-segment hash + extracted citations + PASS/FAIL
  + a hash of the hook version that ran).

### 8.4 The chain's ethics rule is non-stationary and not reproducible

Block acceptance runs each payload through a bag-of-words model (`fallback_model.json`)
that **retrains every night**. A convicted payload anywhere in history makes a joining
node stop at that height forever, and the decision margin drifts across days. So "the
rules held" for *this* rule has **no fixed answer**: the model that would judge block k
today is not the model that judged it at mint, and no per-block verdict or model-snapshot
is preserved. Everything else in Section 1 (hash, PoW, linkage, signatures, derived
fields, shape, ledger replay, drift) **is** fully reproducible from the chain bytes with
standard crypto + JSON. The ethics predicate, today, is **not** externally reproducible
and is arguably not a sound consensus rule — this is the project's own recorded open
question, and the spec discloses it rather than resolving it.

### 8.5 Succession and the second operator

The second-operator amendment quorum is **intention, not mechanism** — no code enforces
a k-of-n gate, so "amendment requires quorum" is not externally checkable. The
human-successor register lives in a gitignored `ops/succession.private.json`, never
committed; who the successors are, their channels, and whether any silence-letter fired
are invisible to any outsider. The private memory corpus is never published; only its
Merkle state root is, which lets an outsider verify a corpus copy they already hold but
never obtain or inspect the corpus itself.

### 8.6 Semantic blind spots that survive even a green run

- The **containment guard is proximity/existence, not judgment** — it cannot tell a
  reasserted claim from a description of one, and text planted within 10 lines of a
  citation is exempt by design (R2).
- The **manifest proves bytes, not truth** — an unchanged hash says nothing about
  whether a verdict row is true or rule-conformant (M1).
- The **constitution hash proves text, not behavior** — "No trades placed by automation"
  being the committed text is not proof the running system places no automated trades (K6).
