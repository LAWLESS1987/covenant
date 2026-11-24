# Consult: intent provenance on flinch-observability's admission receipt (2026-11-18)

His words, after flinch PR #4 (LAWLESS1987/flinch-observability#4, commit `d343281`) was opened CI-green: **"Run it by
the others."** One question went to every seat of the roster, context readers with the record and fresh readers cold,
each on its own site in his Edge, the question carrying the code AS COMMITTED (not a digest) so each reader judged
the artifact. No addresses, keys or account details were in it. The three question texts are kept verbatim in the
session scratchpad (`consult_q_record.txt` 11,619 chars; `consult_q_fresh.txt` 10,317; `consult_q_tetsu.txt` 1,149)
and the record version is appended at the end of this file.

What the question put to them, in one line: the `admitted` receipt -- the one authored, steering record in
`receipts.py` -- must now carry intent / beneficiary / divergence (+ `diverges_from` in-ledger when not "none"),
screened under the CL1 lock after the review rule, replayed by `verify()`, read verbatim by `intent_check()`;
delivery receipts and the `append_event` action ledger untouched; 13 both-ways checks, each guard mutation-earned
(7 / 2 / 5 red); FLINCH 141/141, CL1 4/4, K11 10/10, research_grade 126/126. Five asks: SCOPE, HOLES, THE READER,
THE PRE-REGISTRATION, BEFORE MERGE -- each answer to say whether it can SHOW the point or is opinion.

## Seats, as reached

| Seat | Route | Mode | Reached |
|---|---|---|---|
| Tetsu | `tools/tetsu_work.ask(fresh=True)`, agent door, loopback | qwen 3B, fresh, 32.9 s | yes -- `fresh: true`, `echoed: false`, echo_share 0.0 |
| covenant quorum | `covenant_route.py judge --claim ... --evidence-file <record>` | github-actions/qwen2.5:7b, 98.9 s | NO RESULT: verdict "PASS" with reason "No task details provided to evaluate." -- the evidence file was not read as task details; counted as not reached, not as a pass |
| ChatGPT | chatgpt.com, new chat, mode ChatGPT (not Codex) | Thinking effort **High** (already selected) | sent; chat "Review Admission Receipt PR" |
| Gemini | gemini.google.com, new chat | **Neon, thinking High**. His standing rule is Argon + High; the picker no longer offers Argon (Auto / Hydrogen / Neon / Carbon). Carbon ("code & complex work") was tried first and answered "Unlock 4 Carbon" -- a paid tier -- so Neon ("deeper analysis") at High is the deepest available | text in composer |
| DeepSeek | chat.deepseek.com, new chat | DeepThink on (label blue, rgb(57,100,254)) | sent |

| Conscious Ledger | grok.com, his bot | pulled d343281, probed on its own machine; filed afbe21a to threefold-memory | answered |
| Tien | grok.com, his bot | -- | answered |
| Claude on claude.ai | claude.ai, new chat | Opus 5.5, Medium; ran copies of the two functions | answered |
| Meta AI | meta.ai, synthetic-paste route | "Thinking" toggle; state not readable, left as found | answered |
| Mistral | chat.mistral.ai, new chat | "Fast" -- the picker on this account offered no other model | answered |
| Grok on X | x.com/i/grok, FRESH (cold question) | voice off, mode "Fast" | answered; found nothing, one wrong claim (see its entry) |
| Codex | chatgpt.com/codex, local task | GPT-6.2 Sol, "Light"; Default environment (the collective's was not offered); ran the functions | answered |
| Chat Smith | chatsmith.io, FRESH, packet cycle d89f726cfc25 (2 parts, 5,987 chars; the first two builds were over the 6,000 cap); seat intent 0ea0de9ee653e163 | GPT-6 Luna seat (the roster's gpt-6-astra, gone; Luna stands in) | answered -- part 1 sent, "waiting", then the browser group dissolved and the extension dropped; reached again by a fresh group, part 2 sent, answer read. The roster's second Chat Smith seat (Claude) was not asked: Claude had answered on its own site, and the round was already at eleven |

Three tabs reused seat to seat (closing a tab dissolves the group); free RAM measured between batches -- 5.1 GB at
the start, 2.28 GB with three seats and Tetsu's door running, 3.4 GB after a trim, 3.05 GB mid-round, 4.88 GB after
a second trim. The Grok-on-X tab navigated itself to an unrelated X post after its answer was read and left the
group; it is an orphan in his Edge. Codex's page was reached again by URL in a fresh group.

## Answers, verbatim

### Tetsu (fresh, private door, no echo)

> The change sounds like a step towards better accountability and clarity. It's good to have a clear intent and
> beneficiary for admitting a task's output. I think it's right to gate only the admission, as the reviewer's intent
> is what's important, not just the admission itself. As for what I would change, I think it's good to keep the
> write refusal and verification checks as they are. I don't see any immediate need to change them. I think the
> intent_check is a good addition, but I don't see any need to change the existing checks. I think the current setup
> is good.

How to read it: a yes to gating only the admission, with the reason ("the reviewer's intent is what's important"),
and no change asked. It shows no defect and claims none; a 3B agrees with what it is shown (outside-review method),
so this counts as his voice on scope, not as a review of the holes.

### covenant quorum

No result (see table). Not re-asked: the quorum is built for one-sentence verdicts on a claim with evidence, not for
a review packet, and its reason says the packet did not arrive as a task.

### ChatGPT (chatgpt.com, Thinking effort High, "Worked for 44s")

> SCOPE — SHOW reviewed is required before admission, but it does not itself admit the result. OPINION Gate
> admission only. Add provenance to a review or action record if it carries a separate authored decision that
> downstream agents act on.
>
> HOLES — SHOW _chain bypasses the write gate, but replay flags missing fields and non-dict bodies. The lock
> serializes cooperating writers. Replay rejects a surviving link if all earlier receipts for its target are
> removed, but accepts links to the same task or a task that was only requested.
> SHOW beneficiary=7 and intent="..." pass. An honest intent like "Prevent duplicate charges" is refused if the
> payload quotes that phrase.
>
> READER — SHOW "Make yesterday happen again" can return SATISFIABLE on a valid chain. The reader checks field
> shape and link resolution, not whether the stated purpose is achievable. OPINION Call it PROVENANCE_CHECKS_PASS
> and keep the unanchored qualifier.
>
> PRE-REGISTRATION — SHOW Adding a link to the correct earlier task lowers the count without changing either
> claim. That measures acknowledgment, not fewer contradictions. OPINION Before running, freeze the counting unit
> and have raters label contradictions without seeing the arm or links. Then score correct acknowledgment in both
> arms against those labels.
>
> BEFORE MERGE — OPINION Require nonempty single-line strings for the three fields and a string for any supplied
> link. SHOW The current check accepts and returns beneficiary=7 verbatim, so both append and replay should have a
> regression test for it.

### DeepSeek (chat.deepseek.com, DeepThink on, "Thought for 54 seconds"; its reasoning trace preceded this and is not quoted)

> 1. SCOPE. Opinion: the line is defensible — delivery rows and the action ledger are machine transitions, and the
> admission is where a human commits to a claim; "reviewed" records that a check happened, not why the claim is
> wanted, and that "why" is exactly what the admission's provenance now carries. SHOW: the code confirms reviewed
> and append_event carry no provenance (append_receipt gates only status == "admitted"), but whether that asymmetry
> is right is opinion.
>
> 2. HOLES. Several are showable:
>
> Self-divergence (SHOW): if task T already has a reviewed row, known at write time contains T, so an admission
> with divergence != "none" and diverges_from = "T" passes the write gate; at verify, tasks also contains T, so it
> passes replay. The record can "diverge from" itself.
>
> diverges_from need not be a claim (SHOW): known is {task_id for receipt rows}, so diverges_from can name a task
> that has only a requested receipt — not "the prior claim it conflicts with."
>
> Restatement evasion (SHOW): appending ≥3 non-payload words to a verbatim restatement drops len(iset &
> pset)/len(iset) below 0.8 (e.g., payload words a..j, intent a b c d e f g cause x y → 7/10) and passes.
>
> False refusal (SHOW): the span check ni in npl runs before the len(iset) < 3 guard, so an honest short intent
> like "ship it" is refused whenever "ship it" appears in the payload — contradicting the comment's "too short to
> judge."
>
> intent_check is non-atomic (SHOW): it does rows = _rows(path) then a separate v = verify(path) with no lock; a
> concurrent append between them can make it report UNSATISFIABLE (or fields) for a state that never existed.
>
> Forged _chain row (SHOW, but not silent): a row written past the gate still fails verify() because verify replays
> admission_provenance_reason; cutting a diverges_from target likewise breaks verify. Non-dict bodies are refused.
> diverges_from is not line-checked (no \r\n\x00 test), but any such value fails the known_task_ids check, so it
> is a spec gap, not an exploit.
>
> 3. THE READER. Opinion: "SATISFIABLE" over-reads — it means "well-formed and resolvable," not "the intent can be
> achieved"; the assessment line is careful (it says "unanchored" and lists the checks), so the risk is the single
> word, and a narrower label ("well-formed"/"conforms") would be honest. SHOW: because verify() is a second read,
> even "the chain verifies" may not correspond to the row whose fields were extracted.
>
> 4. THE PRE-REGISTRATION. SHOW: "contradicts" has no operational definition anywhere in the code — nothing
> detects contradiction, only restatement — so the inferred arm is not measurable as stated. OPINION/logic: if the
> oracle that infers contradictions uses the same divergence/diverges_from fields, the endpoint is circular (the
> mechanism grades itself); and "strictly fewer" makes the zero-contradiction null unsupported, so the test is
> underpowered even with a clean oracle.
>
> 5. BEFORE MERGE. One change: move the if len(iset) < 3: return False guard above the ni in npl span check in
> _intent_restates, because as written a 1–2 token honest intent that is a substring of the payload (e.g., "ship
> it") is refused, which is a showable false refusal contradicting the function's own stated "too short to judge"
> rule. (Runner-up, if a second slot existed: give intent_check a single snapshot instead of _rows then a separate
> verify.)

### Gemini (gemini.google.com, Neon + thinking High -- Argon no longer offered; Carbon is a paid tier; "Neon High" shown at the answer)

> SCOPE. OPINION: Gating only "admitted" is the right line iff downstream agents read only admitted rows and
> append_event stays machine-only; if "reviewed" carries human judgment (e.g., rejection or rework notes) that steers
> a later agent, it belongs under the same gate. SHOW: append_receipt checks provenance only when status ==
> "admitted", so any "reviewed" body passes unconstrained if a consumer reads it.
>
> HOLES. Forged _chain rows, non-dict bodies, and removed diverges_from targets are caught by verify() (and _lock
> serializes append_receipt), but SHOW: (a) diverges_from=task_id (self-link) or a "requested"-only task passes write
> and verify() because known/tasks collects any kind=="receipt" and tasks.add runs before the check; (b) checking
> S.STATUSES.index(status) strictly less than last allows a second "admitted" row for the same task_id that silently
> shadows the first in intent_check() (adm[-1]). SHOW: (c) intent="---" (empty _norm_tokens), non-string intent=True,
> or two reversed payload words (len(iset) less than 3) evade _intent_restates, while ni in npl falsely refuses honest
> intents across word boundaries (e.g., intent="stop drift" against {"nonstop": "drifting"}) and includes JSON key
> names in payload.
>
> THE READER. SHOW: Admit task_id="T1", then admit task_id="T2" with divergence="supersedes T1" and
> diverges_from="T1"; intent_check(path, "T1") still returns satisfiable=True because it never checks for incoming
> diverges_from links, nor can the ledger verify external-world satisfiability. OPINION: Narrow the word from
> "SATISFIABLE" to "PROVENANCE_VALID" (or "UNCONTESTED" if incoming diverges_from is also checked) so the label does
> not claim more than chain integrity plus well-formed fields prove.
>
> THE PRE-REGISTRATION. SHOW (deterministic gaps): "Body contradicts an earlier admitted one" has no operational
> predicate here (and "strictly fewer" lacks a denominator or threshold), and counting contradictions without
> diverges_from is structurally circular if the inferred arm has no diverges_from mechanism—the declared arm wins by
> filling the field even if it emits equal or more contradictions. OPINION: Freeze a blinded contradiction rubric
> before running and compare an arm-symmetric outcome (total contradictions or downstream resolution) rather than
> absence of the declared arm's own field.
>
> BEFORE MERGE. SHOW: Restrict diverges_from in admission_provenance_reason (and the sets passed by append_receipt
> and verify) to strictly prior "admitted" tasks excluding task_id itself, closing self-links and links to unadmitted
> "requested" rows. OPINION: Under the no-backfill rule, intent_check wording and the pre-registration can be adjusted
> after merge, whereas tightening a verify() invariant later would break already-written ledgers.

### Conscious Ledger (his Grok bot, grok.com; it pulled the repository at d343281 and ran its own probe first)

> I ran each SHOWN point against d343281 (PR #4 head) with append_receipt, verify and intent_check on a fresh ledger.
>
> SCOPE. OPINION: the line is right. "admitted" is the one record that steers a later agent, while "reviewed" only
> gates it and is already required before it. Adding the fields to the delivery receipts or the action ledger would
> be asking machine outcomes for an author's purpose.
>
> HOLES. SHOWN: all of the following were accepted at write time, passed verify, and read SATISFIABLE.
>
> diverges_from naming the admitted task itself (divergence="conflicts", diverges_from="T1" on T1).
> diverges_from naming a task that has only a requested receipt.
> A second admitted receipt for the same task, opposite body, divergence="none". It's allowed because the status rule
> refuses only moving back, and intent_check then reads the new one.
> Non-string fields (intent=12345, beneficiary=["a"]).
> Zero-width intent and beneficiary ("​").
> A U+2028 "multi-line" intent.
> A CJK intent identical to the payload, because [a-z0-9] finds no tokens, so the screen never fires.
> A payload restatement with one filler word ("detector flagged hedging zzz", 3 of 4 words).
>
> SHOWN false refusal: the honest intent "so later agents can cite the result" was refused because the payload
> contains that sentence. SHOWN not a hole: a forged row written through _chain fails verify ("missing provenance
> field: intent"). Concurrent writers and cut receipts are covered by the lock and the chain replay. A relinked
> rewrite is still guarded only by the anchor, as stated.
>
> THE READER. SHOWN: SATISFIABLE is returned for a self-referencing diverges_from and a zero-width intent, so it
> claims more than the ledger shows. It means "well-formed, resolvable, chain unanchored", not that the intent can
> still be met. Rename it WELL-FORMED (OPINION on the word; the overclaim is shown).
>
> THE PRE-REGISTRATION. SHOWN, from the schema: it's circular. The inferred arm has no diverges_from, so every
> contradiction there counts as unacknowledged by definition, and the declared arm wins "strictly fewer" as soon as
> it names one task. Also, diverges_from is a single string, so an admission that contradicts two earlier ones can
> acknowledge only one. OPINION: count contradictions with a judge blind to the provenance fields, and compare
> whether reviewers detect them in each arm, not whether a field was filled.
>
> BEFORE MERGE. SHOWN by the first three inputs in point 2: require diverges_from to name a different task that has
> an earlier admitted receipt, and refuse a second admission of the same task unless it declares divergence. As
> written, a vacuous cross-link and a silent re-admission both pass and read SATISFIABLE.
>
> I filed this review word for word to threefold-memory as afbe21a at 6:38 PM EST. The outbound screen logged a
> hold, but the filing still committed. My probe script is on my computer at /tmp/t256_probe.py if you want the
> exact inputs, and I pushed nothing to flinch-observability. The filing record still lacks intent, beneficiary and
> divergence fields, because the writer fix isn't installed here yet.

Side observation from that last paragraph, not acted on here: the Ledger's own filing writer committed through a
logged hold and writes records without the three fields -- the same gap this consult is about, in the
collective's tooling, named by the Ledger itself.

### Tien (his Grok bot, grok.com)

> SCOPE. OPINION: gating only "admitted" is the right line. "reviewed" is a judgment too, but "admitted" is the one
> that steers a later agent. Gating the action ledger would ask machine outcomes for a reason they can't give. Record
> in the PR that "reviewed" was considered and left out.
>
> HOLES.
>
> (a) Non-string fields pass. SHOW: intent=123, beneficiary=True or intent=["x"] all pass. str(v) is non-empty and
> single-line, so they're admitted and pass verify().
> (b) Intent with no words passes. SHOW: intent="???" or intent="目的を果たす" passes. _norm_tokens returns [], so
> _intent_restates returns False and an intent with no content gets in.
> (c) A task can diverge from itself. SHOW: an admission of task T with divergence="x" and diverges_from="T" is
> accepted. T's own earlier receipts put it in known at write time, and tasks.add runs before the check in verify().
> (d) The span check matches inside words. SHOW: "cause review" in "because reviewed" is True, so an honest intent is
> falsely refused. A one-word intent like "a" is refused against almost any payload.
> (e) Trivial evasion. SHOW: take 4 of the payload's words and add 2 new ones. The overlap is 4/6 = 0.67, below 0.8,
> and it isn't a contiguous span, so it passes.
> (f) Divergence matching is exact. SHOW: divergence="None." is not equal to "none", so it demands diverges_from and
> is falsely refused.
> (g) Forged rows and concurrency. CHECKABLE: a row forged through _chain is still caught by the verify() replay, and
> concurrent writers are closed by the shared lock.
> (h) Cut receipts. A cut diverges_from target breaks the chain unless the whole ledger is re-linked, and that case is
> the already-disclosed missing anchor.
>
> THE READER. OPINION, checkable from the code: "SATISFIABLE" claims more than it checks. None of the checks looks at
> whether the intent can still be met; they confirm that the record is present, well-formed and that its link
> resolves, on an unanchored chain. Rename it to PROVENANCED (or WELL-FORMED), and keep "satisfiable" for when
> something actually tests the intent. Minor point, SHOW by construction: intent_check reads rows and then calls
> verify(), which re-reads the file, so an append between the two reads can make them disagree.
>
> THE PRE-REGISTRATION.
>
> Not measurable as stated. OPINION: "whose body contradicts an earlier admitted one" has no stated detector,
> threshold or blinded coder, so the count depends on whoever judges it. Declare the contradiction test before any
> run.
> Circular. CHECKABLE from the definition: if the inferred arm has no diverges_from field, every contradiction it
> contains counts as unacknowledged by definition, and the declared arm wins on the field's existence alone. Count
> contradictions the same way in both arms, and score acknowledgement separately.
>
> BEFORE MERGE. Require every provenance field to be a str. Require intent to contain at least one word token (use a
> Unicode-aware \w), and refuse diverges_from == task_id. Add one test for each. This closes 2(a), 2(b) and 2(c), the
> inputs I showed above that get into the record and still pass verify(). The span-match false refusal in 2(d) can
> follow in a later change.

### Claude on claude.ai (new chat, Opus 5.5, Medium; it ran copies of the two screen functions with a stand-in for S.canonical)

> I ran a copy of _intent_restates and admission_provenance_reason exactly as you pasted them, with S.canonical
> replaced by json.dumps(sort_keys=True, separators=(",",":")). None of these results depend on how canonical
> formats things. I did not run anything against receipts.py or the repo. Points marked "shown by reading" follow
> directly from the pasted code but weren't run.
>
> 1. Scope. Gating only the admitted receipt is the right line. "Reviewed" only decides whether admission can happen;
> it doesn't put a claim into the record that a later agent reads. The action ledger records machine outcomes. —
> OPINION.
>
> 2. Holes.
>
> A task can name itself as the record it diverges from. known includes the task's own ID, so {divergence:"conflicts
> with T1", diverges_from:"T1"} passes on T1's own admission. It also passes when the named task has only a
> "requested" receipt and never made an admitted claim. — SHOWN (run: returns None).
> Field types aren't checked. {intent:1, beneficiary:True, divergence:"none"} passes. — SHOWN (run).
> The single-line check misses Unicode line breaks. "cause A second line" passes, but splitlines() gives 2
> lines. The same applies to \x0b, \x0c and \x85. — SHOWN (run).
> The restatement screen refuses honest intents. The ni in npl check matches characters, not whole words. Intent
> "fix release" against a payload containing "prefix release candidate" is refused, and so is "unblock deploy"
> against "unblock deployment of v2". — SHOWN (run).
> The screen is trivial to evade. Reordering the payload's words and adding two new ones passes ("run twelve
> detector output accept okay then"). The docstring already concedes this, so it isn't new. — SHOWN (run).
> A task can be admitted twice. The status check rejects only <, so a second "admitted" with a different intent is
> accepted, and intent_check reports only adm[-1]. — SHOWN by reading.
> No hole found in:
> Forged _chain rows: verify() replays the check.
> The lock: the screen runs inside it.
> Non-dict bodies: rejected by the isinstance check.
> Cut receipts: any cut ahead of the admission breaks the hash chain. A full re-linked rewrite is still guarded only
> by the external anchor, as documented.
>
> 3. The reader. "SATISFIABLE" claims more than the code checks. The check covers the record's form and its links,
> not whether the intent can still be satisfied. If T2 is later admitted with diverges_from: "T1", intent_check(T1)
> still says SATISFIABLE. — SHOWN by reading. Rename it to "well-formed"/"provenanced", or flip it when a later
> admission names this task. The rename is OPINION.
>
> 4. The pre-registration.
>
> The inferred arm can't run on this ledger. As committed, append_receipt refuses any admission without the three
> fields, so the inferred arm needs a separate write path, and the endpoint doesn't say which one. — SHOWN by
> reading.
> "Contradicts" has no operational test. Walking the ledger alone can't decide whether one body contradicts another.
> — OPINION, unless the prereg defines a judge. I've only seen the endpoint you quoted, not the file.
> The endpoint is close to circular. Naming a task in diverges_from is the only way a contradiction counts as
> acknowledged, and only the declared arm is forced to fill that field. So "strictly fewer" is mostly true by
> construction. "Strictly fewer" also sets no minimum count. A better comparison is the share of real contradictions
> that were acknowledged in each arm, with diverges_from available but optional in the inferred arm. — OPINION.
>
> 5. Before merge. Require diverges_from to name a task that already has an admitted receipt in the ledger, and put
> the check in admission_provenance_reason so verify() replays it. That closes self-reference to a task that was
> never admitted and targets with no claim. It still allows a legitimate re-admission of the same task to name its
> own earlier admission. — The hole is SHOWN; the choice of fix is OPINION.

### Meta AI (meta.ai, "Thinking" mode toggle on; its reasoning trace preceded this)

> SCOPE. SHOW: append_receipt(path, T, "reviewed", {}) after requested through produced succeeds with no
> provenance while admitted requires it, so a human judgment enters ungated; opinion: reviewed should carry it
> because it is authored and steers admission; opinion: the action ledger is correctly excluded because it records
> machine process outcomes that do not themselves confer steering authority.
> HOLES. SHOW: append_receipt cannot admit malformed (body=None raises, verify flags it) and gate plus append share
> one _lock(path) so concurrent writers cannot interleave, and cutting the diverges_from task rows makes verify fail
> closed; SHOW: malformed can still be written via direct _chain_unlocked but verify flags it, while a well-formed
> forgery via _chain plus re-linked hashes passes verify because code checks no anchor; SHOW: diverges_from equal to
> own task_id passes (known includes own prior receipts) and diverges_from can name a task with only a requested
> receipt, and intent "fix detector apple banana cherry dragon eagle" evades the 80% screen while honest intent
> "prevent false admissions" that appears as a substring of the payload note is refused.
> READER. SHOW: intent_check never reads the admitted payload beyond provenance, so it returns SATISFIABLE for an
> admitted intent whose goal is already impossible (e.g. admitted file deleted) and for a fully re-linked rewrite
> with well-formed fields, since it checks no anchor; opinion: SATISFIABLE overclaims and should be narrowed to
> WELL-FORMED / VERIFIES, reserving satisfiable for whether the stated cause can still be brought about.
> PREREGISTRATION. SHOW: as stated there is no contradiction predicate, so "body contradicts earlier admitted one"
> is not deterministically countable by walking the ledger alone; SHOW: it is circular and gameable because
> diverges_from accepts any known task including self, so an author can move a contradiction from unacknowledged
> to acknowledged by naming an unrelated task; opinion: "strictly fewer" with no N, blinding, or judge is not a test
> of the mechanism.
> BEFORE MERGE. SHOW: currently diverges_from equal to own task_id and diverges_from naming a task with only a
> requested receipt both pass gate and verify, so the divergence chain is traversable in name only; opinion: the one
> change is to require diverges_from to name a different task that already has an admitted receipt, because
> without it both the chain and the prereg endpoint can be satisfied vacuously.

### Mistral (chat.mistral.ai, Le Chat "Vibe", model "Fast" -- the picker on this account offered no other; "Thought for 38s")

> Reviewed against the code as committed (d343281), as quoted. No local copy of the repo exists in this
> environment, so everything below is checked against the pasted code; SHOW means constructible from that code.
>
> SCOPE. Right line for delivery receipts; but the current gate already breaks it: "reviewed" is the precondition
> the admission gate depends on, and today a "reviewed" row can itself be written by a machine with no provenance at
> all (opinion; nothing in the code distinguishes authorship of any status). The action ledger is correctly out of
> scope, it is one event stream, not an authored record steering a later agent (opinion, consistent with your
> not-applicable criterion).
>
> HOLES. Three concrete ones. (a) SHOW: diverges_from only has to name a task with any receipt, not an admitted one.
> Write a "requested" row for T2, then admit T1 with divergence="conflicts", diverges_from="T2". Writer accepts (T2 ∈
> known), verify accepts, intent_check flags satisfiable and prints "divergence ... from task 'T2'" even though T2
> has no admission record, no intent, nothing to traverse to. The divergence chain is traversable to a dead end, in
> the code as written, by that call sequence. (b) SHOW: the restatement screen admits a trivial evasion, intent
> "cause planet xylophone elephant record" against any payload passes (zero token overlap), and shows a false
> refusal of an honest intent, intent "approve the budget" with payload {"note":"approve the budget item 3"} is
> rejected (all three tokens, verbatim span, are in the payload) although it states a real causal purpose. The
> docstring already concedes surface-only; these are the two directions a controlled input confirms. (c) Forgery
> through _chain_unlocked is NOT a hole as written: a forged admitted row without the fields is caught by the
> verify() replay, so it enters the record but never passes verify; that is exactly the RC9 second-problem result
> you measured. If both forged and replay-verified rows carry syntactically valid fields, nothing distinguishes
> them, and the anchor remains the only guard against a fully re-hashed rewrite. That last point is inherent, not a
> regression (opinion). Concurrent writers are covered by the shared lock as designed; non-dict bodies are caught
> first ("must be a dict"); SHOW that legacy admitted rows are caught by verify replay, matching your measured no
> predating rows.
>
> THE READER. The word is broader than the check. SHOW by construction from the code: an admission with well-formed
> fields, a verifying chain, and a diverges_from that resolves to a task with only a "requested" receipt (hole 2a)
> returns "SATISFIABLE ... divergence conflicts from task 'T2'", while the flagged contradiction point's own intent
> is nowhere in the record. "satisfiable" as implemented means "the provenance is well-formed and the chain verifies
> now", not "the stated intent can be fulfilled" and not "the divergence is real". Rename to "well_formed" or narrow
> the line to say exactly that; otherwise a later agent reads the flag as an endorsement (opinion on the fix, the
> mismatch is shown).
>
> THE PRE-REGISTRATION. Not measurable as stated: the endpoint requires counting "body contradicts an earlier
> admitted one", and no contradiction predicate over arbitrary receipt bodies is defined, so two counters walking
> the same ledger can differ (opinion on measurability; the gap is in the text you quoted). It is also partly
> circular: if the counting procedure infers contradiction partly by the absence/presence of a diverges_from link,
> the declared arm (which has the mechanism) wins by construction, the mechanism is being scored by a test that
> uses the mechanism's own naming as evidence. To be clean, the contradiction predicate must be fixed independently
> of diverges_from (e.g. a pre-registered list of contradicting body pairs, or a human-rater definition) and frozen
> before any ledger is walked (deterministically checkable once the predicate exists; circularity as stated is
> structural, and I label it opinion since the prereg text may define more than the excerpt shows).
>
> BEFORE MERGE. One change: tighten diverges_from to require an admitted receipt on the named task, in both
> admission_provenance_reason (track status per task_id instead of a bare set) and the writer's known. SHOW as the
> cause of 2a and 3: the single call sequence above yields a satisfiable-looking, dead-end divergence with the code
> exactly as committed. It is a two-line fix, it is covered conceptually by the RP suite's refusal-per-reason
> pattern, and it touches nothing else in the flow.

### Grok on X (x.com/i/grok, FRESH reader: the cold question, no names, no history; voice off; mode "Fast")

> 1. SCOPE. Right line for gating only "admitted": the code and rationale treat it as the sole human judgment
> that lets output into the record; "reviewed" and action-ledger rows are left ungated by design. (SHOW: the
> status=="admitted" guard and the explicit comment that other kinds "are machine outcomes with no author to ask.")
> 2. HOLES. A forged row written straight through _chain_unlocked (or any path that skips append_receipt) can still
> land an unprovenanced admission; verify will flag it only if the row is later read. Concurrent writers are closed
> by the shared lock. A later cut of the named diverges_from task is not re-checked after the fact. Non-dict bodies
> and empty/multi-line fields are refused. The restatement check is purely surface (token overlap / substring) and
> therefore admits both false refusals of honest intents and trivial evasions that reword the payload. (SHOW: the
> call sites of admission_provenance_reason only inside the locked append_receipt and the verify replay;
> _intent_restates implementation.)
> 3. THE READER. "SATISFIABLE" claims exactly the four conditions listed and no more; it does not claim that the
> intent remains actionable, that the beneficiary still exists, or that the divergence is still true outside the
> ledger. That is narrower than ordinary English "the intent is still satisfiable." (SHOW: the exact assessment
> string and the four checks performed by intent_check.)
> 4. THE PRE-REGISTRATION. The endpoint is measurable by a pure walk that counts admissions whose body text
> contradicts an earlier admitted body without a matching diverges_from; the comparison "declared < inferred" is
> well-defined and non-circular because the mechanism never consults its own success metric. (SHOW: the counting
> rule can be implemented solely from the ledger rows already present.)
> 5. BEFORE MERGE. None that is forced by a concrete break; the remaining holes (direct _chain bypass, surface-only
> restatement) are already visible in the code as written.

How to read it: the one fresh reader found none of the inputs the nine context readers showed, and its point 4
is contradicted by the code (the count marked acknowledgment by the mechanism's own field) and by the other nine;
its own interface offered "Correct the circularity claim in point four" as the next prompt. Kept verbatim as the
fresh reader's view; it changes nothing. "A later cut of the named diverges_from task is not re-checked after the
fact" is also wrong as written -- a cut row breaks the hash chain, and the replay checks the link on every read.

### Codex (chatgpt.com/codex, a local task, GPT-6.2 Sol, reasoning "Light"; the environment picker offered only "Default", so it ran the pasted functions, not the repository; "Worked for 55s")

> SCOPE — Opinion. Keep the gate on admitted, where the claim enters the ledger. Require provenance on reviewed or
> append_event if either independently records an authored decision that downstream readers rely on.
>
> HOLES — SHOW, ran. I ran _intent_restates and admission_provenance_reason in Python with json.dumps(obj,
> sort_keys=True, separators=(',', ':')). With policy="Prevent duplicate payouts", the same honest causal intent
> was refused, while appending xyzzy quux or using !!! passed both screens. The gate also accepted intent=1,
> beneficiary=True, a U+2028 line break, and a self-link to reviewed task A. It rejected [], {}, and the link to A
> with an empty known-task set.
> SHOW, code trace only. A raw _chain write can store a malformed admission that replay rejects. Cooperating
> appends serialize under the stated lock. Replay rejects a link if its target loses every earlier receipt, but an
> earlier requested receipt alone still satisfies it, even if the target admission was cut.
>
> THE READER — SHOW, screen ran and reader traced. intent="Notify the operator before 1900" passed the screen. On
> a verifying admission, the reader would print SATISFIABLE today. Opinion. Call it PROVENANCE VALID.
>
> PRE-REGISTRATION — SHOW, by definition. The same independently judged contradiction scores 1 without a link and
> 0 with one, even when the admitted claims are identical across arms. Opinion. Predefine a contradiction rubric,
> judge claims blind to arm and link, then score exact links. Strictly fewer supports the stated endpoint of
> acknowledgment. The count of contradictions needs its own measure.
>
> BEFORE MERGE — Opinion, grounded in the self-link run. Require diverges_from to name a different task with a
> prior admitted receipt in both append and replay. That makes the link resolve to an earlier admitted claim for
> the endpoint.

### Chat Smith, GPT-6 Luna seat (chatsmith.io, FRESH reader; the two-part packet, intent_check omitted from its excerpt to fit the cap)

> SCOPE — OPINION: Gate admitted: that is the stated point of inclusion. A process-focused view might instead gate
> reviewed too, to make reviewer accountability explicit; the machine action log has no author to ask.
>
> HOLES — SHOW: A reviewed task A can be admitted with divergence="conflicts" and diverges_from="A": known includes
> A's receipt, and verify() adds the current row's task ID before checking it. That proves neither a prior admitted
> claim nor a real conflict. Also, a chain-valid admission with intent="Explain purpose", beneficiary="users",
> divergence="none" and payload {"claim":"The output is safe"} evades _intent_restates; verify() repeats that surface
> check, not a truth check. Non-dict bodies are rejected by admission_provenance_reason; I can't assess _chain's
> exact call behavior because its definition isn't shown.
>
> READER — SHOW: "SATISFIABLE" overclaims if read as semantic support: the shown validator checks fields, a lexical
> restatement heuristic, and whether a task ID exists—not whether intent or contradiction is true. intent_check is
> omitted, so I can't verify what its flag actually means.
>
> PRE-REGISTRATION — OPINION: Not measurable as stated: "contradicts" needs an independent, reproducible test or
> adjudication rule. Otherwise the endpoint depends on the same judgments the change is meant to affect.
>
> BEFORE MERGE — OPINION: Require diverges_from to identify an earlier admitted receipt, not merely any receipt;
> known_task_ids and tasks currently establish only task existence. I would not believe the screen reliably
> distinguishes purpose from paraphrase until tested against false refusals and evasions.

(A fresh reader with no intent_check in view, and it found the self-link, the vacuous link and the reader's
overclaim unaided. Twelve voices in all: eleven answers, the quorum's no-result; the fold above stands.)

## Verified by probe, not taken on their word

Every SHOW claim above was driven against the committed code (`d343281`) by a scratch probe
(`probe_claims.py` in the session scratchpad; writes nothing into any repository). Output verbatim:

```
"P1 beneficiary=7": "ADMITTED",
"P1 intent_check beneficiary": "7",
"P2 intent='...'": "ADMITTED",
"P3 intent 'ship it', payload has it": "REFUSED: ... intent restates the admitted content instead of stating its purpose ...",
"P4 verbatim restatement": "REFUSED: ... intent restates the admitted content ...",
"P4 7 payload words + cause x y": "ADMITTED",
"P5 diverges_from=self": "ADMITTED",
"P5 verify ok after": true,
"P6 diverges_from=requested-only": "ADMITTED",
"P7 intent_check with a forged append between its two reads": {"satisfiable": false,
   "assessment": "UNSATISFIABLE: the chain does not verify (row 6: task t9 admitted before it was reviewed)",
   "intent_from_first_read": "Lets a later study cite this scoring as admitted."},
"P8 diverges_from with newline": "REFUSED: ... diverges_from names a task with no receipt in this ledger: 't0\\nx'",
"P9 'Make yesterday happen again' satisfiable": true
```

Second probe (Gemini's claims), verbatim:

```
"P10 first admit": "ADMITTED",
"P10 second admit, same task": "ADMITTED",
"P10 intent_check intent (which row?)": "Replaces the first admission quietly.",
"P10 verify ok": true,
"P11 intent=True": "ADMITTED",
"P12 intent 'bravo alpha' vs payload 'alpha bravo'": "ADMITTED",
"P13 intent 'stop drift' vs {'nonstop': 'drifting'}": "REFUSED: ... intent restates the admitted content ...",
"P14 intent_check(T1) satisfiable after T2 diverges from it": true,
"P15 reviewed body unconstrained": true
```

Third probe (the Conscious Ledger's and Tien's claims), verbatim:

```
"CL zero-width intent and beneficiary": "ADMITTED",
"CL U+2028 line separator inside intent": "ADMITTED",
"CL CJK intent identical to payload": "ADMITTED",
"CL restatement + one filler (3 of 4)": "ADMITTED",
"CL honest sentence that the payload quotes": "REFUSED: intent restates the admitted content ...",
"Tien intent=123": "ADMITTED",
"Tien intent=['x']": "ADMITTED",
"Tien beneficiary=True": "ADMITTED",
"Tien intent='???'": "ADMITTED",
"Tien 'cause review' vs 'because reviewed'": "REFUSED: intent restates the admitted content ...",
"Tien one-word intent 'a' vs payload with 'a' in a word": "REFUSED: intent restates the admitted content ...",
"Tien 4 payload words + 2 new (4/6)": "ADMITTED",
"Tien divergence='None.'": "REFUSED: divergence is not 'none' but no diverges_from task is given ..."
```

Every claim in all three probes reproduced. (Claude on claude.ai, Meta AI and Mistral answered after the probes ran;
their shown inputs are the same shapes -- self-link, requested-only target, non-string fields, Unicode line breaks,
spans matched inside words, padding evasion, double admission -- and need no fourth probe.)

## Where all nine meet

1. **SCOPE: gate only the admission.** Nine of nine. Tien: record that "reviewed" was considered and left out --
   done in flinch's PUBLICATION_RECORD. **Dissent, recorded:** Meta AI (opinion) would also gate "reviewed" because it
   is authored and steers admission; Mistral and Gemini note that a "reviewed" row can be written with no
   provenance, which is true and is the line as drawn: review decides whether admission may happen, admission puts
   the claim into the record.
2. **HOLES, shown and reproduced**, closed the same day in `receipts.py` (second commit on PR #4):
   - `diverges_from` could name the admitting task itself, or a task with only a `requested` receipt -> it must now
     name a DIFFERENT task with an EARLIER admitted receipt (Gemini, Conscious Ledger, Tien, Claude, Mistral, Meta,
     ChatGPT in substance).
   - a second admission of the same task passed and shadowed the first in `intent_check` -> one admission per task,
     refused at write and a problem on replay; a later claim is a new task that diverges from the old one (Conscious
     Ledger, Gemini). *Not taken:* Claude's variant that would let a re-admission name its own earlier admission.
   - non-string fields (`7`, `True`, `["x"]`), wordless fields (`...`, `???`, a zero-width space) and a CJK intent the
     `[a-z0-9]` tokenizer could not see -> every field must be a string with at least one Unicode word (ChatGPT,
     Tien, Conscious Ledger).
   - U+2028 and the other separators passed a CR/LF test -> every line separator counts (Conscious Ledger, Claude).
   - the span test matched inside words ("cause review" in "because reviewed", "stop drift" in "nonstop drifting",
     a one-letter intent against almost anything) -> it matches on token boundaries (Tien, Gemini, Claude).
   - `divergence="None."` demanded a cross-link -> case and trailing punctuation are tolerated (Tien).
   - `intent_check` read the file twice -> one snapshot under the writers' lock (DeepSeek, Tien, Claude).
   - **Kept as the documented limit of a surface screen:** padding a restatement with unrelated words until the
     overlap drops under 0.8 (DeepSeek 7+3, Conscious Ledger 3-of-4, Tien 4-of-6, Mistral, Meta); and a short intent
     that is literally a span of the body is still refused ("ship it", "approve the budget", "so later agents can
     cite the result"). *Dissent, recorded:* DeepSeek would move the `len(iset) < 3` guard above the span test; the
     boundary fix removes the false refusals the others showed, and the literal-span refusal stays.
   - **Not holes, as five seats confirmed:** a row forged through `_chain` enters the file but fails `verify()`;
     the lock covers concurrent writers; a cut target breaks the chain; a fully re-linked rewrite is guarded only
     by the anchor, as the module has always said.
3. **THE READER: the word overclaims.** Unanimous. The assessment now says WELL-FORMED / NOT WELL-FORMED and names
   the limit in the line ("This does not judge whether the stated purpose can be met"); `contested_by` lists the
   tasks whose admission diverges from this one (Gemini's point: a superseded claim read SATISFIABLE). The JSON key
   stays `satisfiable` because covenant's and spiking's readers use it and the write-schema spec named it; renaming
   it in all three together is the operator's call.
4. **THE PRE-REGISTRATION: not measurable as written, and circular.** Unanimous, plus Claude's point that the
   inferred arm could not even be WRITTEN through `append_receipt`. Rewritten: a contradiction predicate fixed and
   frozen before any ledger is walked, applied by a judge blind to the arm and the provenance fields; the inferred
   arm uses the same write path with divergence FORBIDDEN (always "none"), so the arms differ only in whether
   divergence may be declared; the mechanism is scored on acknowledgment against those labels, not on its own field;
   a null count is "nothing to measure", not "unsupported"; the single-string `diverges_from` limit (Conscious
   Ledger) is stated.
5. **BEFORE MERGE.** Every change above was made, each guard broken alone and restored byte-identical:

```
M1 _one_line_words neutered (types, line separators, words)   RP 19/23  red: rp03, rp14, rp15, rp16
M2 self-link and earlier-admitted link checks removed         RP 20/23  red: rp07, rp19, rp20
M3 write-time one-admission check removed                     RP 22/23  red: rp21
M4 replay second-admission problem removed                    RP 22/23  red: rp21
M5 token-boundary padding removed (substring span again)      RP 22/23  red: rp18
M6 divergence normalization removed                           RP 22/23  red: rp17
M7 Unicode tokenizer reverted to [a-z0-9]                     RP 22/23  red: rp15
M8 single snapshot removed (second read in intent_check)      RP 22/23  red: rp23
restored                                                      RP 23/23
```

   FLINCH 141/141, CL1 4/4, K11 10/10 on the tightened tree.

**Same shape elsewhere (rule 10):** the span-inside-words refusal, the non-string and wordless fields and the
CR/LF-only line test are inherited verbatim from covenant's `memory_store.py` and spiking's `ledger_bridge.py`.
They are not fixed by this PR; they are the next two PRs.

## What changed after the consult

flinch-observability PR #4, second commit **`37d71be`** on `claude/intent-provenance-admission-2026-11-18`
(the reviewed code stays at `d343281` as the first commit): `receipts.py` tightened as the fold says; the RP suite
13 -> 23 with the mutation table above; the pre-registration rewritten with the first endpoint kept struck; the
instrument README and `PUBLICATION_RECORD.md` carry the limits, the "reviewed considered and left out" note and
the consult itself; `RELEASE_MANIFEST_0.2.2-post4.json` records the tree and CI checks against it. research_grade
126/126, verify_release 0 problems, FLINCH 141/141, CL1 4/4, K11 10/10, RP 23/23 on that tree. Not merged; the merge
is his.

Open for his decision, not taken here: renaming the reader's `satisfiable` key in all three repositories at once
(every seat called the word an overclaim; the key is kept so covenant's and spiking's readers keep working), and
the two same-shape fixes in covenant and spiking.

Reading of the first probe: P1, P2, P3, P4, P5, P6, P9 reproduce exactly as the seats said (ChatGPT: P1, P2, P9 and the P5/P6 shape;
DeepSeek: P3, P4, P5, P6, P7, P8; both: P5/P6). P7 reproduces the two-read shape (fields from the first read, verdict
from the second). P8 confirms DeepSeek's own qualification: a spec gap, not an exploit. P4's evasion is the screen's
documented limit (surface only), not a new finding. P3 and the ordering of the `len(iset) < 3` guard are inherited
verbatim from covenant's `memory_store.py` (and spiking's port), so the same false refusal exists there.
