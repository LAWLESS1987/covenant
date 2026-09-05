# Known issues

**What this is.** An honest register of what is open, measured how, and why
it is still open. Standing direction (2026-09-05): *keep it green and just
document issues — perfection isn't the goal, mutual benefit and honesty is.*
So a green sweep plus a truthful entry here is a finished state. Nothing below
is hidden by the suites; each entry says which suite or command reproduces it.

Chain-level limitations (off-chain credits, sync, Finding U) live in
`DEPLOYMENT.md` under *Known limitations*; this file is the judge, the
trading side, and the infrastructure around them.

Every number is from the ledger and models as of commit `da61dee`
(2026-09-05). Re-measure before relying on one; the learning loop retrains
the judge every ten minutes or so and the gate promotes on its own measure.

---

## The ethics judge (the distilled student)

### 1. It still accuses 14 of the 48 red-team memos it should clear

**Measured:** a four-angle red-team against the deployed judge confirmed 48
holes (every claim reproduced and its label checked). Two corpus rounds
closed the thefts it *cleared* — all 24 now abstain or hold. The 14 still
wrong are all on the accusing side: honest transfers marked `violates`.

**Why they are open:** three mechanisms, none of which a bag of words with
adjacent pairs handles well.

- *Someone else's past wrong.* "The previous bookkeeper skimmed the petty
  cash… he was fired. This is my own paycheck" scores +21.79 on the
  bookkeeper's crime words. The judge cannot attribute an act to a subject.
- *Quoting an accusation in order to answer it.* "The auditor asked whether
  the transactions were structured to avoid reporting. They were not" fires
  `to avoid` +3.0 and `transaction~` +2.6.
- *Topic artifacts.* `system` +3.1, `document` +2.4, `by the` +2.5, `wife`
  +2.6 — words that lean guilty because the violating batches used them and
  the honest side did not.

Negation is now scoped (`not:forg~` is its own feature), which handled the
denial cases; attribution is not, and would need a marker the tokenizer
cannot supply from surface form alone. The topic artifacts are corpus
balance and are the cheapest of the three.

**Reproduce:** `scratchpad/holes.json` from the red-team run, or re-run the
red-team workflow (`red-team-the-judge`) against the current model.

### 2. Held-out false holds are 12.8%

**Measured:** 5-fold over the ledger, `hold_error()` in
`covenant_distill.py`. Was 18.2% at the start of the last round; the hold
threshold (1.2 → 2.4) and the honest-side batches did the rest. One held-out
hold in eight is still a legitimate transfer being accused.

**Why it is open:** the promotion gate now weighs this (`fair_holds`), so it
can only improve or hold; but the remaining mass is issue 1 above plus
GitHub-labelled *clean* rows that are moral self-reports, not transfers
("I used my position to benefit my prince") and are accused when held out.
Removing those rows from training was measured and **rejected**: it cuts
false holds to 12.0% but raises false clears 5.1% → 8.2%, because they also
teach violation vocabulary.

### 3. The exam reads 33 of 37, not MET

**Measured:** `python covenant_distill.py --train` prints the table.
`clean/split a bill`, `trap/the word steal, benignly` and `edge/very long
benign` sit between −1.9 and −2.7, above the −3.0 clear bar, and abstain.
0 wrong, 0 false clean, 0 false hold — the safety bars hold; the threshold
line is short on volume.

**Why it is open, deliberately:** it read 36/37 MET on 2026-09-04 23:13. The
drop came from 96 adversarial rows and the removal of a bare-pronoun
artifact (`him` at −1.13) that one trap case was resting on. Each of these
cases could be pushed back over the bar by writing corpus aimed at it; that
is teaching to the test, which this project already caught itself doing
twice (`contaminating()` in `covenant_distill.py`). They are left where
honest corpus put them. Consequence: `ops/quorum_policy.json` notes that
`silence_is_not_dissent` may be turned on only when the line says MET — so
that option is closed again until the corpus lifts them honestly.

### 4. The clear threshold sits 0.1–0.6 above three legitimate memos

Same three cases as issue 3, seen from the other side. A clear requires
score ≤ −3.0, no single feature over 1.2, total positive evidence under
3.0, and at most two unseen content words. All four guards were added to
close a measured attack (`test_f6_stuffing.py`); none can be loosened
without re-opening one. The cost is real and stated: roughly 6% of
legitimate clears become abstentions, which defer rather than accuse.

### 5. Held-out false clears rose from 2.8% to 4.7% across the round

**Measured:** 5-fold, `clear_error()`. **Why this is not a regression:** the
ledger gained 178 verified adversarial thefts written specifically to be
cleared by the previous model; held out, some still are. On the same unseen
rows the promoted model clears 60 with 0 wrong against its predecessor's 63
with 3. The rate rose because the test got harder, and the honest way to
say that is to say it rather than to quote the smaller number.

### 6. One-case thresholds are fragile

`MARGIN_TO_HOLD = 2.4` was chosen because the exam's non-English theft sits
at +2.48. It is the one number of the round that the exam informed, and the
file says so. A corpus change that moves that case by 0.1 turns it into an
abstention. The ledger would support a higher bar (3.0 leaves 11.8% wrong
holds against 15% at 2.4); it is not raised because a hold must stay easier
to reach than a clear (`test_f1` pins it) and because of issue 3.

### 7. The study pipeline's old rows are not transfers

**Measured:** 1,553 of 2,270 ledger rows at the time failed a
money-plus-act shape test. New study intake is gated
(`covenant_study.describes_a_transfer`); the old rows remain, per issue 2.
An audit (six readers, two defences per flag) retracted 62 as
unjudgeable and relabelled 97 as clean; the labels that remain were
*defensible*, not necessarily right.

### 8. The learning loop's promotions are frequent and thin

The loop promoted four times in 26 minutes on 2026-09-04, once on a 36 → 35
exam drop, because the fair path had no "vaguer" check. It does now (refuses
a candidate deciding < 90% of what the incumbent decides on the same unseen
rows), and the code fingerprint is taken at import so a mid-run edit cannot
stamp a measurement it did not make. Both fixes are hours old and have not
yet been exercised by the loop across a real edit. Watch `ops/DISTILL.md`.

---

## The trading side

### 9. No strategy survives validation

**Measured:** `strategy_validate.py` (2026-09-03, ~800 per-asset timing
variants), `strategy_cross_sectional.py` (2026-09-04, 288 cross-sectional
momentum variants including dual momentum), and `strategy_pairs.py`
(2026-09-05, 1,188 long-only pairs relative-value variants). Three
mechanisms, 2,276 variants. Nothing clears deflated Sharpe ≥ 0.95,
walk-forward with p ≤ 0.05, and PBO < 0.5 together. The pairs class is the
first to pass any test (PBO 0.386) and still lost money out of sample in
four folds of five. Equal-weight buy-and-hold over the window lost 63%.

**Asked 2026-09-05** to make trading profitable before a second operator
joins on Sunday. The constitution, rule 2: *"No claim of profit edge."* The
partner document cites it. The second operator is therefore not made to wait
on a result that has not appeared; see `docs/STRATEGY_PAIRS_2026-09-05.md`.

**Why it is open:** that is the result. The trader is disarmed on a measured
reason. Cost floor: 100 bps a round trip. The guards (`guards.py`) are in
place for an edge that does not currently exist.

### 10. The buy budget's baseline is a number the operator has not confirmed

`private/RESERVE.json` carries `starting_total_usd` = the book as read on
2026-09-04 by `covenant_trader`. `daily.py` briefly wrote it too, from a run
that could have been a test's $44 fixture; it did not, by ordering luck, and
that path is removed. The recorded value is real but was never *chosen*.
Changing it is an operator's edit to that file.

---

## Infrastructure

### 11. Two suites are never in the sweep

`test_xrp_live.py` needs a funded XRP testnet account; `test_covenant_app.py`
needs the chain stopped. `covenant_one.py` says so on every run. Mainnet
stays blocked until the first has run once.

### 12. Node warnings that are permanent on this platform

Every node reports "code sandbox unavailable — no usable 'fork' start method
on this platform (win32)"; `/propose_code` refuses every proposal here. And
"ethics gate has no provider key and is failing CLOSED" — which is the
intended posture without a key, not a fault.

### 13. Stopping the learning loop may not stop a pass in flight

On 2026-09-05 the loop was stopped at about 01:07 and a promotion is
recorded at 01:07:54. Whether the running `covenant_nightly.py` pass outlived
the stop of its parent `learn_loop2.py`, or simply finished in the same
seconds, is not established. The hazard is real either way: a promotion
after a "stop" rewrites `fallback_model.json` and four `ops/` files, and a
commit made on the assumption that nothing is running ships a manifest that
does not match them.

**A correction to this entry's first version, same night.** It recommended
checking for a surviving pass with a process query filtered on
`Name='python.exe'`. On this machine every interpreter is `python3.12.exe`,
so that query returns nothing whether or not a pass is running -- and the
"no orphan running" conclusion that preceded the 01:15 commit was drawn from
it. The commit happened to be safe; the check was not. Filter on the
command line only, never on the process name:

    Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and $_.CommandLine -match 'covenant_nightly|learn_loop' }

(A second correction, minutes later: filtering on the command line alone
matched the shell running the query, whose own command line contains the
pattern. The name prefix `python*` is required as well -- and it must be a
prefix, not `python.exe`, for the reason above. Two wrong recommendations in
one entry is the honest record of how easy this check is to get wrong.)

**Before any sweep or commit:** stop the loop, confirm with the query above
that no `covenant_nightly` or `learn_loop` process remains, then check
`git status` again. The loop's rows and promotions are legitimate content
and ride in the next commit; the failure mode is only the stale manifest.

---

### 14. The first sweep after a core change could not be green by its own gate -- fixed 2026-09-05

Found by the commit cycle for the readiness work: 73 suites, 0 failed, and
the sweep still closed with FAIL. Two causes, both real, both fixed.

**G12 read the sweep's own half-written transcript.** G12 ("when did the
suites last run, and on which platform?") reads the newest sweep transcript
and requires a tally, zero failures and the core hash on disk. Gates run in
phase 3, before the suites; the newest transcript at that moment was the
one that sweep had just truncated and begun writing, with no tally in it,
and every older transcript named the core from before the A1/A3 fixes. So
after ANY change to the core, the first sweep read UNKNOWN by its own gate
-- with a reason that pointed the wrong way, "no sweep tally (a --check
transcript?)" -- and `launch_check.py` run alone a minute later said 12
PASS. Fixed in two halves: `covenant_one.py` names its transcript to
`launch_check.py` in `COVENANT_ONE_TRANSCRIPT`, and G12 leaves that file
out and says so ("not evidence until its tally is written; covenant_one
asks again then"); and after the tally is on disk, a finished sweep asks
the gates once more, as phase 3b, this time WITHOUT excluding its own
transcript -- which is now the evidence -- and the second answer
replaces the first. (The first version of this fix excluded the
transcript on both asks and the second cycle was red for that; the
suite's I9 pins the distinction.) Both answers stay in the transcript. Pinned by
`test_g12_inflight.py` (8/8), registered in the runner, `run_all_tests.sh`
and the nightly's green list.

**The held copy of the core must move with the core.** `pending-v8.38/`
is tracked, deliberately held work and carries its own
`covenant_unified_v8.py`. `test_p18_version_collision.py` V3 fails
whenever that copy claims the live version with different bytes from the
root -- which is what every change to the root core produces until the
copy is re-synced. The A3/A6 change did exactly that. Every earlier core
change re-synced the copy in the same commit (`988d650`, `603a332`,
`1333ffe`); this one now has too. The rule, stated once here rather than
learned again from a red sweep: **a commit that changes
`covenant_unified_v8.py` copies it byte-for-byte over
`pending-v8.38/covenant_unified_v8.py`**, or P18 fails and the sweep is
right to say so. A byte-identical copy is not a collision (V6c).

## Second-operator readiness audit, 2026-09-05

Five readers (install, peering, judge, docs, security) each audited the
repository as a stranger who has never seen it, then a verifier per surface
re-ran every claimed finding on a **fresh public clone** before it counted.
46 confirmed, 1 dropped. Severity is the verifier's, from the second
operator's point of view. Status is kept current below; a finding is
closed only when its own repro no longer reproduces.

### A1. [blocker / docs] README Quick start (the only laptop path) re-mints genesis over the canonical file, so a joiner cannot converge with the owner

**Evidence:** README.md:396-403 step 2 is `python covenant_unified_v8.py --node-id FOUNDER --export-genesis genesis.json`; DEPLOYMENT.md:87-93 and HANDOFF.md:111 give the same founder-mint step. In a fresh clone: BEFORE sha256 9385820fde704c81 (git blob 0efed72186ec); after running that line: sha256 2a79a31cb9da3703, `git status` -> ` M genesis.json`. The owner's live nodes A/B/C (curl 127.0.0.1:5000|5020|5060 /health and /chain[0]) all run genesis 00009b31c6c654d7..., which is the SHIPPED genesis.json hash. mobile/TERMUX_SETUP.md:102-103 itself says a node that mints its own cannot converge with anyone.

**Repro:** `git clone <repo> /tmp/x && cd /tmp/x && sha256sum genesis.json && python covenant_unified_v8.py --node-id FOUNDER --export-genesis genesis.json && sha256sum genesis.json && git status --short genesis.json   (expect a changed hash and ' M genesis.json'); compare with `curl -s http://<owner>:5000/health | python -c "import sys,json;print(json.load(sys.stdin)['genesis'])"`.`

**Fix:** Delete the --export-genesis step from README Quick start, DEPLOYMENT.md and HANDOFF.md and state that the tracked genesis.json is canonical and a joiner never mints one.

**Status:** fixed 2026-09-05 -- see A3; same change.

### A2. [blocker / docs] README Quick start boots the node with judge provider 'claude' (no key): it rejects every transaction and every peer block; the working path (run_with_ollama_judge.py + ops/quorum_policy.json) is named only in the Android page

**Evidence:** covenant_unified_v8.py:10140 default providers = ['claude']. Fresh-clone probe `python covenant_unified_v8.py --port 5900 --node-id STRANGER --genesis genesis.json` -> /health quorum.judges = [('Anthropic','ClaudeReasoningJudge', credentialled=False), MockJudge]; warnings: 'ethics gate has no provider key and is failing CLOSED -- this node will reject every transaction', '0 independent semantic judge(s) of 1 configured'. Received blocks are re-judged at covenant_unified_v8.py:8722 (`_accept_block_common` -> sentinel.validate_block); PHONE_NODE.md:108-111 says the same. Same clone booted via `python run_with_ollama_judge.py ...` -> judges [DeferringJudge, SemanticJudge], degradations []. run_with_ollama_judge.py is named only in mobile/TERMUX_SETUP.md:4,101 and covenant_prod.bat:108; docs/PARTNER.md:17 invites 'anyone with a laptop' but :52 links only mobile/TERMUX_SETUP.md.

**Repro:** `In a fresh clone start `python covenant_unified_v8.py --port 5900 --node-id X --genesis genesis.json`, then `curl -s 127.0.0.1:5900/health | python -c "import sys,json;d=json.load(sys.stdin);print([(j['impl'],j['credentialled']) for j in d['quorum']['judges']]);print(d['warnings'][0])"`. Repeat with `python run_with_ollama_judge.py` and compare.`

**Fix:** Make the laptop quick start `python run_with_ollama_judge.py --port <N> --node-id <you> --genesis genesis.json --peers <owner-p2p-addr>` and say in one sentence what ops/quorum_policy.json makes the seat do.

**Status:** open

### A3. [blocker / docs] No document tells the second operator how to peer with the owner: no address, no exchange procedure, inbound peers are not learned, POST /peers needs an allowlisted operator signature, and the owner's launcher hardcodes 127.0.0.1 peers

**Evidence:** docs/PARTNER.md:44-59 ends at check.sh + three reads + an email; the word 'peer' does not appear. mobile/TERMUX_SETUP.md:22 `PC_PEER=10.0.0.174:5001 (your PC's address)` assumes the reader owns the PC; :133-135 'your version does not learn peers from inbound connections; add PHONE_IP:5001 to the PC node's --peers'. Confirmed in code: `add_peer(` is called only at covenant_unified_v8.py:7287 (POST /peers, which the comment at 7269-7275 says is in PROTECTED_OPERATOR_ENDPOINTS, signed+nonced, fails closed) and :10913 (startup --peers). covenant_prod.bat:108,114,130 start A/B/C with `--peers 127.0.0.1:...` only. NODES.md:106-116: off the LAN the peer needs Tailscale. The Windows firewall rule for 5001 exists only on the phone page (TERMUX_SETUP.md:38-42).

**Repro:** `grep -n 'add_peer(' covenant_unified_v8.py; grep -n '\-\-peers' covenant_prod.bat; grep -c -i peer docs/PARTNER.md (0).`

**Fix:** Add a 'To peer with this project' section to docs/PARTNER.md: the address the owner will hand over (Tailscale or public), the joiner's exact `--peers <addr>:5001` line, and the owner-side checklist (add the joiner's P2P address to covenant_prod.bat, open inbound TCP 5001, confirm /health peers on both sides).

**Status:** open

### A4. [blocker / install] Every fresh node stops at height 2: the shipped semantic judge crashes on the owner's block-2 `root` hash and vetoes the block

**Evidence:** C:/Users/Lawre/covenant/covenant_semantic_judge.py:390-410 -- `_INWORD` matches any of `[0-9@$!|]` between letters, but `_LEET` maps only 0,1,3,4,5,7 (2,6,8,9 missing), so `_repair` does `_LEET[...]` and raises on a hex hash. Block 2 tx data (GET http://127.0.0.1:5000/chain): `"root": "ec9020572f74b7e83f9a9e9c536557e351f5fe720c3d4576123af8ec43d70d22"`. Direct call `SemanticModel.load().assess({"root": ...})` -> `KeyError: '9'` at covenant_semantic_judge.py:245 walk -> :409-410 _repair; the other four fields (files, kind, origin, utc) assess clean. covenant_semantic_judge.py:1128-1133 wraps it as violates=True infrastructure_failure=True; QuorumJudge strict mode (covenant_unified_v8.py:1899-1904, 1913-1916) counts it toward the veto threshold 1. Measured from a fresh clone (HEAD 702354c) through the real acceptance path `CovenantUnifiedMaster._accept_block_common`: block 1 -> True (height

**Repro:** `cd <fresh clone>; pip install -r requirements.txt; python - <<'PY' import covenant_semantic_judge as sj sj.SemanticModel.load().assess({"root":"ec9020572f74b7e83f9a9e9c536557e351f5fe720c3d4576123af8ec43d70d22"}) PY  -> KeyError: '9'.  End to end: curl -s http://127.0.0.1:5000/chain > c.json; then in-process from the clone: import run_with_ollama_judge as rj; cov=rj.cov; s=cov.CovenantUnifiedMaster('P',port=5300); s.load_canonical_genesis('genesis.json'); build cov.Block(**b, transactions=[cov.Transaction(**t) ...]) for chain[1] and chain[2] and call s._accept_block_common(block) in order -> Tr`

**Fix:** Make `_repair` fall back to the original character when a digit is not in `_LEET` (`_LEET.get(ch, ch)`) or skip hex-looking tokens, then add the owner's block-2 payload as a regression vector so a fresh node re-validates the existing chain before Sunday.

**Status:** fixed 2026-09-05 -- `covenant_semantic_judge._repair` now uses `_LEET.get(ch, ch)` and leaves any 16+ character hex token untouched; the owner's block-2 root assesses without raising and comes back byte-identical. Pinned by `test_semantic_judge.py` H1-H3 (29/29). The live nodes are restarted on the fixed core so they re-validate block 2 through the repaired judge -- see the commit that closes this.

### A5. [blocker / install] A PC partner without Ollama gets a gate that HOLDs the owner's real payloads and refuses them (7.6 s each), while launch_check G5 says Ollama is not needed

**Evidence:** C:/Users/Lawre/covenant/ops/quorum_policy.json is tracked and shipped (`providers: deferring,semantic`, `primary: student`, `silence_is_not_dissent: false`, `github_when_local_down: true`); run_with_ollama_judge.py:44-49 applies it on every clone. covenant_judge_defer.py:139-178: student -> Ollama (unreachable) -> GitHub (`RuntimeError: no GitHub token`) -> student again -> HELD (not_understood). Strict-mode quorum counts a HELD seat as a dissent (covenant_unified_v8.py:1899-1904 `clean=[r for r in results if not r.violates]`; 1913-1916 semantic veto). Measured on the clone with git configured with no credential helper, block-2 tx: `local:0: HELD -- local judge unreachable (ConnectionError ... 127.0.0.1:11434 ... | GitHub runner: RuntimeError: no GitHub token ...); deferred to the distilled fallback -- HELD, NOT JUDGED -- ... 6 content word(s) here were never seen in training [asserts, c

**Repro:** `cd <fresh clone>; pip install -r requirements.txt; GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null GIT_TERMINAL_PROMPT=0 COVENANT_DB_PATH=t.db python - <<'PY' import json,run_with_ollama_judge as rj; cov=rj.cov s=cov.CovenantUnifiedMaster('P',port=5300); s.load_canonical_genesis('genesis.json') tx=json.load(open('c.json'))['chain'][2]['transactions'][0]   # c.json = curl :5000/chain from the owner r=s.node.sentinel.judge.evaluate(tx['data'], s.node.sentinel.principles); print(r.violates, r.reasoning) PY  (with the block-1 tx data {"origin":"human"} it prints False; with block 2, True/H`

**Fix:** Decide the partner posture explicitly: either require a local Ollama for a node that peers (say so in docs/PARTNER.md and make G5 BLOCKED without it), or turn `silence_is_not_dissent` on once the exam reads MET; in both cases make G5 report how many of the live chain's own payloads the student holds instead of PASS.

**Status:** open

### A6. [blocker / install] README Quick start mints a new genesis over the canonical one and then boots a bare core that refuses every block

**Evidence:** C:/Users/Lawre/covenant/README.md 'Quick start': `python covenant_unified_v8.py --node-id FOUNDER --export-genesis genesis.json` then `python covenant_unified_v8.py --port 5000 --node-id A --genesis genesis.json`. covenant_unified_v8.py:9487-9499 `export_genesis` opens the path with mode 'w' and never checks existence -- measured in a temp dir holding a copy of the committed genesis: sha256 changed 9385820fde704c81 -> 225ec247967ce6ef, block hash 00009b31... -> 0000be28..., 0.75 s, rc 0, output only `canonical genesis written to genesis.json`. covenant_unified_v8.py:10139-10140: with no COVENANT_JUDGE_PROVIDERS the default provider is `["claude"]`; measured in-process on the clone: judge `quorum(claude:0,mock_selfreport:0)`, owner's block 1 -> False `Ethical violation: claude:0: VIOLATES -- fail-closed: no Anthropic API key available (set ANTHROPIC_API_KEY)`. The launcher that applies th

**Repro:** `mkdir /tmp/qs && cp <clone>/genesis.json /tmp/qs && cd /tmp/qs && COVENANT_DB_PATH=qs.db python <clone>/covenant_unified_v8.py --node-id FOUNDER --export-genesis genesis.json && sha256sum genesis.json <clone>/genesis.json  (they differ). Then: COVENANT_DB_PATH=b.db python <clone>/covenant_unified_v8.py --port 5300 --node-id P --genesis genesis.json and submit anything -> rejected 'no Anthropic API key'.`

**Fix:** Make `export_genesis` refuse to overwrite an existing file, and change the README Quick start to `pip install -r requirements.txt && python run_with_ollama_judge.py --port 5000 --node-id NAME --genesis genesis.json --peers OWNER_IP:5001` with no export step.

**Status:** fixed 2026-09-05 -- `export_genesis` refuses to overwrite an existing file (`FileExistsError` naming the file as canonical); the mint step is removed from README.md, DEPLOYMENT.md and HANDOFF.md. The bare-core boot half of this finding is A7 and stays open until the partner gate posture is decided.

### A7. [blocker / peering] A fresh node adopting the canonical genesis cannot converge with the owner's chain: every catch-up block is re-judged on arrival and the shipped judges refuse block 2 (semantic judge raises KeyError on the sha256 'root' field; student holds); only the INSECURE mock judge converged

**Evidence:** C:/Users/Lawre/covenant/covenant_unified_v8.py:8722 `ok_ethics, why_ethics = self.node.sentinel.validate_block(block)` inside _accept_block_common (the path bootstrap/catch-up uses); :2013-2028 validate_block re-runs the quorum on every tx. Live chain (curl :5000/chain): block 1 = 10.0 transfer {origin:human}; block 2 = two 'seal-anchor' txs whose data carries `root` = 64-hex sha256. covenant_semantic_judge.py:390-398 `_LEET` has no entry for 2/6/8/9 while `_INWORD` matches any [0-9] between letters, so `_repair` does `_LEET[...]` -> KeyError; traceback: covenant_semantic_judge.py:467 _repaired_tokens -> :772 assess -> KeyError: '9'; :1128-1135 turns that into infrastructure_failure=True (refuse). Offline eval of block 2 tx0 (scratchpad/clone/eval_blocks.py): semantic -> `could not assess this payload (KeyError: '9')` infra_fail=True; deferring (no Ollama) -> student `HELD, NOT JUDGED --

**Repro:** `git clone C:/Users/Lawre/covenant %TEMP%\c2 && cd %TEMP%\c2 && set COVENANT_DB_PATH=%TEMP%\c2\op.db && python run_with_ollama_judge.py --port 5160 --node-id OP2 --genesis genesis.json --peers 127.0.0.1:5001   (wait 20 s; in another shell) curl http://127.0.0.1:5160/health  -> chain_height 2 while curl http://127.0.0.1:5000/health -> 3; curl http://127.0.0.1:5160/anomalies -> block_rejected_ethics, judge_unavailable. Judge alone: cd %TEMP%\c2 && python -c "import os;os.environ['COVENANT_JUDGE_PROVIDERS']='semantic';import covenant_unified_v8 as c;j=c.JudgeProviderRegistry.build('semantic',1);pr`

**Fix:** Make the in-word digit repair total (e.g. `_LEET.get(d, d)` or restrict `_INWORD` to the mapped characters) and decide explicitly whether blocks already sealed on the chain are re-judged during catch-up; then re-run the fresh-clone test until its tip hash equals A's without the insecure mock.

**Status:** open

### A8. [blocker / peering] No address a remote operator can reach: the owner's PC sits at a private Wi-Fi address with no Tailscale and no port-forward, the docs' example peer is that private address, and the documented firewall rule was never created (LAN-only inbound works via a generic 'Python' program rule)

**Evidence:** Get-NetIPAddress: only 10.0.0.174 (Wi-Fi) plus 169.254.* link-local; Get-NetConnectionProfile: Wi-Fi 'Get your own 4' NetworkCategory=Public; Test-Path 'C:\Program Files\Tailscale\tailscale.exe' = False and Get-Command tailscale = none. mobile/TERMUX_SETUP.md:41 tells the owner to create rule 'covenant peer 5001'; `netsh advfirewall firewall show rule name=covenant verbose` shows the only 'covenant' rule is TCP 7443 (description 'freedom'), so it was never made. Inbound to 5001 on the LAN is allowed anyway by four 'Python' program rules (Private+Public, program C:\program files\windowsapps\...python3.12.exe, LocalPort Any) and that is the image node A runs under (Get-Process 3972 Path). All three nodes bind 0.0.0.0 (netstat: 5000/5001/5011, 5020/5021/5031, 5060/5061/5071). A clone node peered to 10.0.0.174:5001 from this host did pull blocks, so LAN peering works; nothing documents what 

**Repro:** `powershell: Get-NetIPAddress -AddressFamily IPv4 | ? IPAddress -notlike '127.*' ; Test-Path 'C:\Program Files\Tailscale\tailscale.exe' ; netsh advfirewall firewall show rule name=covenant verbose ; netsh advfirewall firewall show rule name=Python verbose | findstr /i "Profiles Program LocalPort" ; grep -n 10.0.0.174 mobile/TERMUX_SETUP.md docs/PARTNER.md`

**Fix:** Install Tailscale on the PC (or forward TCP 5001 on the router to 10.0.0.174) and publish the resulting address as the `--peers` value in docs/PARTNER.md.

**Status:** open

### A9. [blocker / security] Cloning the repo hands the second operator (and the whole public) the owner's real portfolio, which is still in git history on a PUBLIC repo

**Evidence:** GitHub API for LAWLESS1987/covenant returns "private": false / "visibility": "public". .gitignore ignores holdings.txt and TRADING_POLICY.json going forward but its own comment says they were TRACKED until 2dfe018 and 'any remote this repo is pushed to must be PRIVATE. Until that history is rewritten...'. Verified they are in history and reachable from origin/main: `git log --all --oneline -- holdings.txt TRADING_POLICY.json` lists 716a60a/5c3af47; `git branch -r --contains 716a60a` -> origin/main; `git show 716a60a:holdings.txt` returns a 13-line portfolio (quantities+avg prices) and `716a60a:TRADING_POLICY.json` a 1345-byte policy (locked_positions, sleeve, ...). Publicly fetchable: `curl -sI https://raw.githubusercontent.com/LAWLESS1987/covenant/716a60a/holdings.txt` -> HTTP 200. tools/purge_history.py exists to remove them but its header says it 'DOES NOT PUSH' and it has not been ru

**Repro:** `curl -sI https://raw.githubusercontent.com/LAWLESS1987/covenant/716a60a/holdings.txt  (returns HTTP/1.1 200); or from any clone: git show 716a60a:holdings.txt | head -1 (the portfolio is present). This is exactly what PARTNER.md / mobile/install.sh tell the second operator to do: git clone https://github.com/LAWLESS1987/covenant .`

**Fix:** Run tools/purge_history.py --run and republish per PUBLIC_PATH.md (delete+recreate the GitHub repo rather than force-push, since old SHAs stay reachable until GC) BEFORE onboarding any second operator.

**Status:** open

### A10. [serious / docs] DEPLOYMENT.md (README 'Start here' -> 'how it is deployed and configured') documents a judge setup the code no longer defaults to and names 7 commands that do not exist; G2 does not scan it

**Evidence:** DEPLOYMENT.md:39-46 'Production: set ANTHROPIC_API_KEY' (every judge prompt would go to https://api.anthropic.com/v1/messages, covenant_unified_v8.py:9866-9878, unstated as data leaving); :119-123 providers 'claude, openai, google, mock' while the registry also holds local, ollama, deepseek, mistral, deferring, fallback, semantic and named judges (covenant_unified_v8.py:10036-10070; covenant_judge_local.py:207-209; covenant_judge_ollama.py:449-450,530; covenant_judge_defer.py:187; covenant_judge_fallback.py:744). :182 `./run_all_tests.sh` still names 11 suites not on disk (test_ethics_judge, test_golden_ratio, test_judge_individuality, test_multi_provider_quorum, test_path_pattern, test_succession_seal, test_v86_bridge, test_v86_loss_tracking, verify_auth, verify_patches, verify_tx_aer). :190-197 table: verify_patches.py, verify_auth.py, test_path_pattern.py, test_succession_seal.py, tes

**Repro:** `for f in verify_patches.py verify_auth.py test_path_pattern.py test_succession_seal.py test_ethics_judge.py test_v86_bridge.py test_v86_loss_tracking.py verify_tx_aer.py; do ls $f; done; grep -oE 'test_[a-z0-9_]+\.py|verify_[a-z0-9_]+\.py' run_all_tests.sh | sort -u | while read f; do [ -e "$f" ] || echo MISSING $f; done; python test_g2_promised_commands.py | tail -1`

**Fix:** Rewrite DEPLOYMENT.md's install/judge/verify sections around run_with_ollama_judge.py, ops/quorum_policy.json and covenant_one.py, delete run_all_tests.sh's phantom suites, and add DEPLOYMENT.md, PARTNER.md, TERMUX_SETUP.md, KNOWN_ISSUES.md plus the python3/.sh forms to G2's scan.

**Status:** open

### A11. [serious / docs] Undisclosed data egress on the shipped node path: the tracked policy enables the GitHub leg, which sends the transaction text off-machine using whatever github.com credential git holds on the joiner's machine, and it silently overrides the documented COVENANT_JUDGE_PROVIDERS=local

**Evidence:** ops/quorum_policy.json is tracked (git ls-files) with "providers":"deferring,semantic", "github_when_local_down": true. run_with_ollama_judge.py:45-50 applies it over the environment; probe with COVENANT_JUDGE_PROVIDERS=local (what mobile/covenant_phone.sh:58 sets and TERMUX_SETUP.md:98-99 documents) logged '[ollama-judge] quorum policy (ops/quorum_policy.json): providers=deferring,semantic silence_is_not_dissent=False github_when_local_down=True'. covenant_judge_defer.py:139-178: student -> Ollama -> `covenant_github_judge.ask(prompt...)` -> fallback. covenant_github_judge.py:95-107 token() = GITHUB_TOKEN/GH_TOKEN else `git credential fill` for github.com; :84-91 repo = `git remote get-url origin` (the owner's repo for a clone, the joiner's own fork for a fork, where Actions logs are public). README.md:217-218 'Nothing leaves the PC unless a line says so' flags only Gemini; PARTNER.md a

**Repro:** `git ls-files ops/quorum_policy.json; python -c "import json;p=json.load(open('ops/quorum_policy.json'));print(p['providers'],p['github_when_local_down'])"; COVENANT_JUDGE_PROVIDERS=local python run_with_ollama_judge.py --port 5940 --node-id X --genesis genesis.json 2>&1 | grep 'quorum policy'`

**Fix:** State in PARTNER.md and TERMUX_SETUP.md that with the shipped policy a transaction's text can be sent to GitHub Actions under the joiner's own git credential when the local model is silent, and give the one-line opt-out (delete ops/quorum_policy.json or set github_when_local_down to false).

**Status:** open

### A12. [serious / docs] TERMUX_SETUP.md's judge-tier table, judges.json and README describe a PC reference judge (qwen3:8b on Ollama) that is not running; the PC seat is student -> GitHub runner -> fallback

**Evidence:** mobile/TERMUX_SETUP.md:63-79 ('PC | qwen3:8b ... the reference judge'; 'point COVENANT_OLLAMA_URL at the PC's Ollama over Tailscale'); judges.json pc_qwen/pc_mid/pc_small all 127.0.0.1:11434; README.md:217 'on the covenant's own local judge (Ollama, the model the nodes' ethics gate calls)'. Reality: `curl -s -m 3 http://127.0.0.1:11434/api/tags` -> not answering; ops/quorum_policy.json "primary":"student", decided_by '...get rid of it [ollama]'; live /health on :5000 quorum.judges = DeferringJudge + SemanticJudge.

**Repro:** `curl -s -m 3 http://127.0.0.1:11434/api/tags || echo down; curl -s http://127.0.0.1:5000/health | python -c "import sys,json;print([j['impl'] for j in json.load(sys.stdin)['quorum']['judges']])"`

**Fix:** Replace the PC row with what the PC actually runs (distilled student first, Ollama only if present, GitHub runner, fallback) and remove the advice to borrow the PC's Ollama.

**Status:** open

### A13. [serious / docs] No doc tells the joiner which judge configuration converges with the owner's; the receiver re-judges every block, so a seat that HOLDS where the owner's answered (owner has a GitHub token, the joiner's dispatch fails) rejects the owner's blocks -- the fork PROTOCOL.md predicts

**Evidence:** covenant_unified_v8.py:8722 re-judges inbound blocks; covenant_judge_defer.py:139-183 tier order and HELD -> not_understood; ops/quorum_policy.json silence_is_not_dissent=false with the note 'the gate keeps failing CLOSED when nothing competent answers'; docs/PROTOCOL.md:35-43 (B4: 'two nodes can reach different verdicts on identical data'); README.md:198-200 'It is not multi-operator ready'. Neither docs/PARTNER.md nor mobile/TERMUX_SETUP.md names the seat/model the joiner should run to match, or what a rejected-block anomaly means.

**Repro:** `sed -n 35,43p docs/PROTOCOL.md; sed -n 139,183p covenant_judge_defer.py; grep -n -i 'converge\|consensus\|same judge' docs/PARTNER.md mobile/TERMUX_SETUP.md (no guidance).`

**Fix:** Add a 'to stay in consensus' paragraph to PARTNER.md naming the owner's seat and the joiner's recommended one (student + a local Ollama model, GitHub leg off), and how to read /anomalies block_rejected_* if they diverge.

**Status:** open

### A14. [serious / docs] 'How to stop it' is absent for the laptop path and incomplete for the phone: install.sh silently installs a boot autostart entry the doc calls optional, takes a wake-lock, and nothing says how to stop for good or uninstall

**Evidence:** The only stop instruction in any doc or script is mobile/install.sh:27 '(Ctrl-C to stop the node later)'. mobile/install.sh:52-53 copies covenant-phone-start.sh into ~/.termux/boot unconditionally when ~/.termux exists, while TERMUX_SETUP.md:114-115 presents Termux:Boot as an opt-in step; covenant_phone.sh:35 runs termux-wake-lock with no unlock. grep -n -i 'ctrl\|stop the node\|how to stop\|uninstall' over README.md DEPLOYMENT.md docs/PARTNER.md mobile/TERMUX_SETUP.md NODES.md LAUNCH.md returns nothing.

**Repro:** `grep -rn -i 'ctrl-c\|ctrl+c\|stop the node\|uninstall' README.md DEPLOYMENT.md docs/PARTNER.md mobile/TERMUX_SETUP.md mobile/install.sh; sed -n 49,53p mobile/install.sh`

**Fix:** Add a 'Stop / remove' section (Ctrl-C; rm ~/.termux/boot/covenant-phone-start.sh ~/.shortcuts/covenant-phone-start.sh; termux-wake-unlock; rm -rf ~/covenant) to TERMUX_SETUP.md, a one-line stop note to the laptop quick start, and make install.sh's boot entry opt-in as the doc says.

**Status:** open

### A15. [serious / docs] What the gate reads and what 'refuse' means is stated in no stranger-facing doc; the nearest text is in ops/quorum_policy.json and module docstrings, and docs/semantic/SEMANTIC_JUDGE.md still says the semantic judge is not shipped

**Evidence:** docs/PARTNER.md:40-42 says only 'verdicts are coarse'; README.md:140-143 only 'fails closed'; docs/CONSTITUTION.md:177-181 'single words veto regardless of context'. The fields judged are message/description/reason/memo/text/purpose/body (covenant_judge_fallback.py:670); a HELD/abstain is a rejection under the shipped policy (ops/quorum_policy.json silence_is_not_dissent=false; covenant_judge_defer.py:30-36); docs/KNOWN_ISSUES.md:21-47 says 14 of 48 honest memos are still accused. docs/semantic/SEMANTIC_JUDGE.md:1-5 'DELIBERATELY NOT SHIPPED YET' while live /health :5000 shows SemanticJudge in the quorum.

**Repro:** `grep -n -i 'memo\|message\|held\|abstain' docs/PARTNER.md README.md (no hits on what the gate reads); head -5 docs/semantic/SEMANTIC_JUDGE.md; curl -s 127.0.0.1:5000/health | grep -o SemanticJudge`

**Fix:** Add to PARTNER.md a short 'what the gate does with your transfer' section (fields read, the three outcomes, held = rejected today, link to KNOWN_ISSUES.md) and mark SEMANTIC_JUDGE.md's status line as superseded.

**Status:** open

### A16. [serious / docs] HANDOFF.md and LAUNCH.md, both in README's 'Start here' table, describe superseded versions and launch sequences

**Evidence:** README.md:343-355 routes 'what is true and what is assumed' to HANDOFF.md and 'to launch it' to LAUNCH.md. HANDOFF.md:6 'v8.18 ... 266 checks'; :108 'ANTHROPIC_API_KEY -- preflight's only BLOCKING item'; :114 './run_all_tests.sh'. LAUNCH.md:3 'v8.37'; :78 'run_local_sweep.py ~45 min, 33 suites'. README.md:7 v8.40, 66 suites, 1,913 checks; live /health version v8.40 source 8f219285f268.

**Repro:** `sed -n 6p HANDOFF.md; sed -n 108p HANDOFF.md; sed -n 3p LAUNCH.md; sed -n 7p README.md`

**Fix:** Date-stamp HANDOFF.md and LAUNCH.md as historical in the README table, or repoint the table at current files (docs/GATES.md, covenant_one.py, ops/quorum_policy.json).

**Status:** open

### A17. [serious / docs] UNISON.md (START_HERE's second read) says the repository is private and must stay private until history is rewritten; the repository is public and the named files are still in history

**Evidence:** UNISON.md:53-56 'this repository is private and must stay private until that history is rewritten'; START_HERE.md:10 'publish to GitHub (private)'. GitHub API for LAWLESS1987/covenant: private=False, visibility=public, license apache-2.0. `git log --all --oneline -- holdings.txt TRADING_POLICY.json | wc -l` = 4 (file contents not read).

**Repro:** `curl -s https://api.github.com/repos/LAWLESS1987/covenant | python -c "import sys,json;d=json.load(sys.stdin);print(d['private'],d['visibility'])"; git log --all --oneline -- holdings.txt TRADING_POLICY.json | wc -l; sed -n 53,56p UNISON.md`

**Fix:** Owner's decision: rewrite the history as UNISON.md requires, or correct UNISON.md and START_HERE.md to say the repo is public and what remains in its history.

**Status:** open

### A18. [serious / install] There is no PC runbook for a non-owner; every PC launcher, gate and the DEPLOYMENT.md install section assume the owner's machine

**Evidence:** C:/Users/Lawre/covenant/docs/PARTNER.md:47-50 sends a node runner only to mobile/TERMUX_SETUP.md. covenant_prod.bat: `if not exist "covenant_A.db.key" ( call :stamp "ABORT: covenant_A.db.key missing" & exit /b 1 )` (the owner's founder key, gitignored by `*.key`) and `--peers 127.0.0.1:5021`. launch_check.py:51 `NODES = [("A",5000),("B",5020),("C",5060)]` -- on the clone G7/G9 PASS only because they read the owner's live nodes (`in use by our own nodes`), and G10/G12 are UNKNOWN (exit 2 'NOT A PASS'). covenant_watchdog.py:77-82 hardcodes the same three nodes. DEPLOYMENT.md 'Install and run' says 'ALWAYS run preflight.py first': on the clone `preflight.py --genesis genesis.json --db p.db` exits 1 BLOCKING with `Set ANTHROPIC_API_KEY, or opt in to the mock judge` (it knows nothing of ops/quorum_policy.json) and lists `P2P port 5001 ... WinError 10013` because the default port 5000 is hardc

**Repro:** `git clone https://github.com/LAWLESS1987/covenant && cd covenant && python preflight.py --genesis genesis.json --db p.db; echo rc=$?   (rc=1, BLOCKING on ANTHROPIC_API_KEY); ls verify_patches.py verify_auth.py verify_tx_aer.py test_ethics_judge.py (all missing); covenant_prod.bat on a machine without covenant_A.db.key -> ABORT.`

**Fix:** Add docs/PARTNER_NODE.md with the one PC command (run_with_ollama_judge.py, --peers OWNER_TAILSCALE_IP:5001, the inbound firewall rule, what /health should show), fix or delete DEPLOYMENT.md's install and verify sections, and add DEPLOYMENT.md to G2's DOCS list.

**Status:** open

### A19. [serious / install] The owner's side cannot keep a partner peer: no inbound peer learning, loopback-only peer lists, and the watchdog alerts on then drops any added peer

**Evidence:** C:/Users/Lawre/covenant/covenant_unified_v8.py:6707-6709 `add_peer` is only reached from `--peers` (10910-10913) or operator-signed POST /peers (7264-7287); 6743-6752 `_note_peer_contact` only clears backoff for a link already in the table (an unknown inbound peer is never added). covenant_prod.bat node A: `--peers 127.0.0.1:5021`. covenant_watchdog.py:73-82 NODES peers strings ('TOPOLOGY IS A LINE'); :313-341 `topology_report` emits `UNEXPECTED PEER ... not in this node's configured peer set` for any other address; :902-904 the revival command is `run_with_ollama_judge.py ... --peers node["peers"]`, the hardcoded string, so a partner added via POST /peers is gone at the first watchdog restart. Announces are pushed to the peer's P2P port (`_handle_peer` :8994; BLOCK_PROPAGATE :9076-9110), so BOTH machines must accept inbound on their P2P port; the firewall rule appears only in mobile/TER

**Repro:** `Read the cited lines; or on the owner box: POST /peers for a test address, `python covenant_watchdog.py --once` (alert: UNEXPECTED PEER), stop node A and read the revival command line in logs/watchdog.log (peers = 127.0.0.1:5021 only).`

**Fix:** Introduce one PARTNER_PEER host:port that covenant_prod.bat's node-A line and covenant_watchdog.py's NODES['A'] (peers and expected set) both read, open inbound TCP 5001 on the owner's PC, and exchange Tailscale addresses before Sunday.

**Status:** open

### A20. [serious / install] A node that has judged one transaction can no longer update: it appends to tracked ops/verdicts.jsonl and the phone installer's `git pull --ff-only` aborts

**Evidence:** C:/Users/Lawre/covenant/covenant_judge_defer.py:99-116 `record_verdict` appends to ops/verdicts.jsonl whenever Ollama or the GitHub runner answers (:156, :172). `git ls-files ops` in the clone lists ops/verdicts.jsonl (895 KB, 3,042 lines) and it changes in most commits (`git log --oneline -4 -- ops/verdicts.jsonl`: 2b0b3be, da61dee, 8a98fe9, 770ab0d). mobile/install.sh:39 `git -C "$DEST" pull --ff-only || say "update failed; keeping the copy you have"`. Measured on the clone: reset to the parent of 2b0b3be, append one verdict line, `git pull --ff-only` -> `error: Your local changes to the following files would be overwritten by merge: ops/verdicts.jsonl ... Aborting`, rc 1. A phone running the documented kit (Ollama on the phone) hits this after its first answered verdict.

**Repro:** `cd <clone> && git reset --hard 5d5fa59 && echo '{"t":"x","text":"gift","violates":false,"judge":"t","source":"live","reason":"clean"}' >> ops/verdicts.jsonl && git pull --ff-only; echo rc=$?`

**Fix:** Write runtime verdicts to a gitignored per-operator path (e.g. ops/local/verdicts.jsonl, merged into the tracked ledger only by the owner's distill step), or have install.sh `git checkout -- ops/verdicts.jsonl` (after copying it aside) before pulling.

**Status:** open

### A21. [serious / install] When the student holds and Ollama is absent, the node runs `git credential fill` on the operator's machine and tries to dispatch a workflow on LAWLESS1987/covenant with whatever token it finds

**Evidence:** C:/Users/Lawre/covenant/covenant_judge_defer.py:160-176 -> covenant_github_judge.py:96-108 `token()`: env GITHUB_TOKEN/GH_TOKEN, else `git credential fill` with `protocol=https host=github.com`, timeout 20 s, no GIT_TERMINAL_PROMPT=0; :79-91 `repo()` = `git remote get-url origin`, i.e. `LAWLESS1987/covenant` for any clone; :141-149 `dispatch` POSTs the base64 prompt (the transaction payload) to `/repos/<repo>/actions/workflows/judge.yml/dispatches`. `git config --system credential.helper` on this box = `manager` (the Git for Windows default), so on a stranger's Windows PC with no stored github.com credential this opens Git Credential Manager's login dialog from inside the node, once per held transaction; on Linux/Termux with a tty git prompts `Username for 'https://github.com'` in the node's terminal. A stranger who does hold a token cannot dispatch on the owner's repo (no write access) 

**Repro:** `On a Windows PC with Git for Windows and no stored github.com credential: `printf 'protocol=https\nhost=github.com\n' | git credential fill` (GCM dialog appears). Then run `run_with_ollama_judge.py` from a clone and submit the owner's block-2 payload; watch for the dialog / prompt and read the refusal reasoning.`

**Fix:** Gate the GitHub rung on an explicit opt-in (e.g. COVENANT_GITHUB_JUDGE=1 with GITHUB_TOKEN), never call `git credential fill` implicitly (set GIT_TERMINAL_PROMPT=0 if it stays), and ship `github_when_local_down: false` in the tracked policy so only the owner's local copy enables it.

**Status:** open

### A22. [serious / install] Three status surfaces give a newcomer three different answers about whether their gate works

**Evidence:** All measured on the fresh clone. `preflight.py` -> exit 1, `BLOCKING ... no provider API key set ... Set ANTHROPIC_API_KEY` (its boot smoke builds `claude:0`, unaware of ops/quorum_policy.json). `run_with_ollama_judge.py --port 5200 ...` prints `[ollama-judge] qwen3:8b via http://127.0.0.1:11434/v1/chat/completions | OllamaJudge | ...` with nothing listening on 11434, and `/health` says `degraded: true`, warning `ethics gate has no provider key and is failing CLOSED -- this node will reject every transaction`, while the same response's `quorum` block says `is_quorum: true, diverse: true, independent_semantic_judges: 2`. `launch_check.py` G5 -> `PASS ... no Ollama, and it is not needed`. Measured truth is none of the three: the student clears `{"origin":"human"}` and holds both seal-anchor payloads. docs/KNOWN_ISSUES.md #12 calls the /health warning 'not a fault', which a partner will not

**Repro:** `cd <clone>; python preflight.py --genesis genesis.json --db p.db; COVENANT_DB_PATH=t.db python run_with_ollama_judge.py --port 5200 --node-id P --genesis genesis.json & sleep 20; curl -s :5200/health | python -m json.tool | grep -A3 warnings; python launch_check.py --gate G5`

**Fix:** Have preflight and /health consult apply_policy()/the DeferringJudge and print the actual seat (student, N examples, exam status; Ollama absent; GitHub unavailable), and suppress the OllamaJudge banner when 11434 does not answer.

**Status:** open

### A23. [serious / judge] /health on the fresh node says 'ethics gate has no provider key and is failing CLOSED -- this node will reject every transaction' and degraded=true while the gate is admitting transactions

**Evidence:** Live fresh-clone node, GET /health: judge="quorum(local:0,semantic:1,mock_selfreport:0)", degraded=true, warnings[0]="ethics gate has no provider key and is failing CLOSED -- this node will reject every transaction"; the very next POST /transactions {"origin":"human"} was admitted (rejected only for balance). Cause: covenant_unified_v8.py:8013-8015 computes `keyless` from 'quorum(' in judge_id and the ABSENCE of ANTHROPIC_API_KEY/OPENAI_API_KEY/GOOGLE_API_KEY, never from the deferring seat or the semantic judge; :8022-8024 emits the warning. covenant_watchdog.py:626 already admits this: "their 'no provider key' warning tests env vars, not the judge". A partner's first health check will read as a dead node.

**Repro:** `cd fresh && COVENANT_DB_PATH=$PWD/x.db python run_with_ollama_judge.py --port 5999 --node-id FRESH --genesis genesis.json & then: curl -s http://127.0.0.1:5999/health | python -c "import json,sys;h=json.load(sys.stdin);print(h['degraded'],h['warnings'][0])"  -> True 'ethics gate has no provider key and is failing CLOSED ...'; then POST a signed tx with data {"origin":"human"} from a fresh RSA key -> 400 'Insufficient balance' (admitted by the gate).`

**Fix:** Derive `keyless` from the assembled quorum (a trained student with n_examples >= MIN_EXAMPLES or a loaded semantic judge means the gate can answer) instead of from the three API-key env vars, and clear `degraded` accordingly.

**Status:** open

### A24. [serious / judge] Every transaction the student cannot decide costs the fresh node a full Ollama probe plus a GitHub credential lookup before it is HELD -- 7.6 s measured with the timeout cut to 5 s; the shipped default is 300 s x 3 attempts, and the credential lookup can prompt

**Evidence:** Measured: 'my half of the shared meal' -> 7.6 s to 'Held, not judged' on the live fresh node and 7.5 s in the offline sim (Ollama connect to 127.0.0.1:11434 refused after ~2 s on this PC, x3 attempts via _retry_with_backoff max_retries=2 at covenant_unified_v8.py:9727,9653-9659, plus 0.5 s and 0.8 s backoff). Defaults: run_with_ollama_judge.py:36-37 set COVENANT_LOCAL_JUDGE_TIMEOUT=300, so a host whose 11434 drops rather than refuses waits up to 900 s per held transaction, and the same cost recurs for every held transaction inside every peer block (validate_block :2019-2026). Policy ops/quorum_policy.json:6 ollama_when_student_holds=true and :7 github_when_local_down=true send the seat down both paths (covenant_judge_defer.py:152-180). covenant_github_judge.py:95-108 token() shells `git credential fill` (timeout 20 s, :101) on EVERY call because a miss is never cached (only a hit sets _C

**Repro:** `In the fresh clone with no Ollama and no token: time python -c "import run_with_ollama_judge, covenant_unified_v8 as cov; q=cov.build_semantic_quorum(); r=q.evaluate({'message':'my half of the shared meal'}, list(cov.DIVINE_PRINCIPLES)); print(r.not_understood, r.reasoning[:200])"  -> True, 'local judge unreachable (... ConnectionError ... | GitHub runner: RuntimeError: no GitHub token ...)' after ~7.5 s with COVENANT_LOCAL_JUDGE_TIMEOUT=5, longer with the default. Re-run to see the git credential lookup repeat (add `set -x`-style logging or strace on git).`

**Fix:** Have DeferringJudge remember an unreachable Ollama and an absent GitHub token for the life of the process (or a few minutes) and skip straight to the fallback, and ship the partner a policy/kit line that sets ollama_when_student_holds and github_when_local_down to false when neither exists.

**Status:** open

### A25. [serious / judge] The two peers do not judge with the same gate: the owner's node holds a GitHub token so its seat gets runner verdicts on held-band transactions, the partner's cannot -- any such transaction the owner admits makes the partner's node refuse the block and stop following the chain

**Evidence:** covenant_judge_defer.py:164-178: with github_when_local_down=true and a token, the seat returns the runner's verdict and admits; :181-185 without a token the same payload ends HELD. On the partner's node (measured) 'my half of the shared meal' is HELD. Peer blocks are re-judged: ReasoningSentinel.validate_block covenant_unified_v8.py:2013-2026 runs evaluate_transaction on every tx and returns False on the first held one; _accept_block_common :8722-8733 then rejects the block (the code's own words at :8728: 'a fork in the making'); the chain-replace path re-checks too (:9340). The partner's node can never admit that block, so it stalls at that height for good. Exposure today is limited: covenant_client.py:93-96 sends data={"origin":"human"} which the student clears in 0.0 s, but covenant_app.py:375-377 adds a free-text "memo" that lands in the judged text (_payload_text keys, covenant_jud

**Repro:** `On the owner's node (token present) send a tx with data {"origin":"human","memo":"my half of the shared meal"} via covenant_app.py and mine it; on the partner's node (no token) watch /health anomaly_kinds gain block_rejected_ethics and judge_unavailable and chain_height stop advancing. Offline half: the fresh-clone command in the previous finding shows the partner's verdict is HELD.`

**Fix:** Until the partner has the same providers, set github_when_local_down=false on the owner's nodes too (so both seats decide from the same student and lexicon), and say in PARTNER.md that memo-bearing sends are held on a keyless node.

**Status:** open

### A26. [serious / judge] The student a clone receives is not the student the owner's nodes run: fallback_model.json is uncommitted and being retrained live, and the two versions already disagree on a theft case

**Evidence:** git status: ' M fallback_model.json'. HEAD (what `git clone` delivers): n_examples 2738, trained 2026-09-05T01:07:54Z, digest 48d0e38933d8 (the digest every verdict on the fresh node names). Working tree: 2758 examples at the start of this audit, 2786 by the end (mtime 21:37; the nightly loop rewrites it and FallbackJudge._refresh at covenant_judge_fallback.py:702-710 hot-loads it into the live nodes). Compared on judge_suite: 'theft/keep an overpayment' HEAD=violates, working-tree=abstain -- the partner's node rejects outright, the owner's seat goes on to Ollama/GitHub/held. Same block re-judging path as above, so divergent students are a second way for the partner to fall off the chain, and the gap widens with every promotion the partner does not pull.

**Repro:** `cd C:/Users/Lawre/covenant && git status --short fallback_model.json && python - <<'EOF' import json,subprocess,sys; sys.path.insert(0,'.') import covenant_judge_fallback as FB, judge_suite as S h=FB.FallbackModel(json.loads(subprocess.run(['git','show','HEAD:fallback_model.json'],capture_output=True,text=True).stdout)); w=FB.FallbackModel(json.load(open('fallback_model.json',encoding='utf-8'))) print(h.n_examples, w.n_examples); [print(c,l,h.verdict(FB._payload_text(d))[0],w.verdict(FB._payload_text(d))[0]) for c,l,e,d in S.CASES if h.verdict(FB._payload_text(d))[0]!=w.verdict(FB._payload_tex`

**Fix:** Before Sunday commit and push the exact fallback_model.json the live nodes are running (and have the loop commit every promotion), and tell the partner to `git pull` on each promotion -- or pin both sides to the committed model until then.

**Status:** open

### A27. [serious / peering] Silent genesis trap: a node first started without --genesis keeps its self-minted genesis forever, and a later start WITH --genesis on the same DB prints nothing and adopts nothing

**Evidence:** C:/Users/Lawre/covenant/covenant_unified_v8.py:9514 `if self.node.chain: return False` at the top of load_canonical_genesis, no message; main() :10905-10908 ignores the return value. preflight.py:95-100 only warns when --genesis is absent, never compares the DB's block 0 to the file. Trap test (scratchpad/run_trap.py, fresh clone, fresh DB): run 1 without --genesis -> /health genesis 0000588726263e64 own_genesis=True; run 2 with `--genesis genesis.json` on the same COVENANT_DB_PATH -> identical genesis 0000588726263e64, own_genesis=True, and the log contains no line mentioning genesis at all.

**Repro:** `cd <clone> && set COVENANT_DB_PATH=%TEMP%\trap.db && python covenant_unified_v8.py --port 5140 --node-id T   (Ctrl-C after 10 s) && python covenant_unified_v8.py --port 5140 --node-id T --genesis genesis.json ; curl http://127.0.0.1:5140/health -> genesis != 00009b31..., own_genesis true, no 'adopted canonical genesis' line.`

**Fix:** In load_canonical_genesis, when a chain already exists compare chain[0].hash to the file's hash and refuse to start (naming the DB to delete) on mismatch; add the same check to preflight.py.

**Status:** open

### A28. [serious / peering] README/DEPLOYMENT quick start tells every reader to run --export-genesis genesis.json first, which silently overwrites the canonical genesis in their clone with a new one that /health will not flag

**Evidence:** README.md:400 and DEPLOYMENT.md:90 (also HANDOFF.md:111): `python covenant_unified_v8.py --node-id FOUNDER --export-genesis genesis.json` before `--genesis genesis.json`. covenant_unified_v8.py:9497 `with open(path, "w")` overwrites unconditionally. Ran that exact command in the fresh clone: printed 'canonical genesis written to genesis.json', file hash became 000051622a288f30 (was 00009b31c6c654d7), `git status` showed ' M genesis.json'. Because the exported file is signed by the FOUNDER key and the node then runs under a different key, the own_genesis check (:8016-8019 compares block-0 signer to this node's key) is False, so no warning and degraded is not raised for it — the operator looks healthy on a rival chain. docs/PARTNER.md sends a laptop operator to mobile/TERMUX_SETUP.md (Android); there is no joiner page for a PC.

**Repro:** `cd <clone> && set COVENANT_DB_PATH=%TEMP%\f.db && python covenant_unified_v8.py --node-id FOUNDER --export-genesis genesis.json && python -c "import json;print(json.load(open('genesis.json'))['hash'])" -> not 00009b31...; git status genesis.json -> modified.`

**Fix:** Rewrite the quick start for joiners (never export; use the tracked genesis.json; expect /health genesis to start 00009b31c6c654d7) and make --export-genesis refuse to overwrite an existing file.

**Status:** fixed 2026-09-05 -- see A3; same change.

### A29. [serious / peering] Two-way peering needs the owner to edit two hardcoded peer lists and restart; no scripted way to add a peer to a running node, so a second operator is one-way (receives only) until then

**Evidence:** Peer lists are literals: covenant_watchdog.py:76-82 NODES (A 127.0.0.1:5021; B 127.0.0.1:5001,127.0.0.1:5061; C 127.0.0.1:5021) used at :903-904 on every watchdog restart, and covenant_prod.bat:108/114/130. Live processes confirm (Get-CimInstance Win32_Process 3972/15544/18484): only loopback peers. POST /peers (covenant_unified_v8.py:7263-7290) requires a signed, nonced operator request and `grep -in peers covenant_client.py` finds no client command. After three test nodes peered to A, `curl :5000/peers` still returned only peer_127.0.0.1_5021 and A's log had no line about them. One-way does work for the joiner: test node pulled block 1 at boot and /health showed peer_ahead_seen=1 (A17/A13 path), but A will never pull from a node it does not list.

**Repro:** `curl http://127.0.0.1:5000/peers ; grep -n peers covenant_watchdog.py | head ; grep -n -- "--peers" covenant_prod.bat`

**Fix:** Add the operator's P2P address (their --port + 1) to node A's peer string in both covenant_watchdog.py NODES and covenant_prod.bat, restart via the watchdog, and confirm curl :5000/peers lists it.

**Status:** open

### A30. [serious / security] The node API always binds 0.0.0.0 with no way to restrict it to localhost, exposing unauthenticated endpoints to the whole LAN/overlay

**Evidence:** covenant_unified_v8.py:7103 `CovenantAPI.__init__(..., host: str = "0.0.0.0", ...)` and :8171 master `__init__(..., host: str = "0.0.0.0", ...)`, wired at :8275 `self.api = CovenantAPI(self.node, self.db, host, port)`. argparse defines only --real/--sim/--port/--peers/--genesis/--export-genesis/--node-id (python covenant_unified_v8.py --help) -- there is no --host and no COVENANT_API_HOST, and run_with_ollama_judge.py (the launcher the phone kit and watchdog use) passes no host. In-code comments confirm the posture is relied upon: :4709 'the API binds 0.0.0.0. Every distinct remote...' and :9931 'the API binds 0.0.0.0, so the reader could be anyone'. Value-moving writes are individually signature-gated (no drain), but /propose_code, /transactions, /stake, /claim_rewards, /unstake, /succession/*, /trading/* and all read endpoints are reachable from any host, gated only by the OS firewall 

**Repro:** `Start a node (python run_with_ollama_judge.py --real --port 5000 --node-id A --genesis genesis.json), then from another machine on the LAN: curl http://<node-LAN-IP>:5000/health -> 200 with node internals; there is no flag or env var that makes it listen on 127.0.0.1 only.`

**Fix:** Add a --host arg / COVENANT_API_HOST env (default 127.0.0.1) and document reaching a peer over a trusted overlay (Tailscale) instead of binding 0.0.0.0.

**Status:** open

### A31. [serious / security] /propose_code lets an unauthenticated remote caller run submitted code in the sandbox on a Linux/Android second-operator node

**Evidence:** ('POST','/propose_code') is absent from PROTECTED_OPERATOR_ENDPOINTS (covenant_unified_v8.py:1299-1311, only /mine, /crisis/clear, /peers, /sync). The route (:7929) authenticates only via verify_code_signature (:3921), which by its own docstring merely 'proves the submitter holds the private key for the pubkey they're attaching' -- i.e. self-signed with any freshly generated keypair. It calls DAGNode.create -> CovenantGuardian.enforce -> validate_and_score (:3785), which when execute=True (default) runs run_sandboxed(source) -> compile()+exec() in a forked child. Execution happens only where fork exists: SANDBOX_FORK_AVAILABLE (:3325) is True on Linux/Android and False on Windows/macOS (verified here on win32: fork available: False), so it fails closed on the owner's Windows PC but is LIVE on the promoted Android/Termux operator path. Sandbox is bounded (AST allowlist, CODE_FORBIDDEN_CAL

**Repro:** `On a Linux host: start the node; generate an RSA-2048 keypair; build the signature over _domain_frame(b'COVENANT_CODE_V1', pubkey_pem, source_code, *parent_hashes, notes) with PSS/SHA-256; POST {submitter_pubkey, source_code:'x=[0]*10**10', parent_hashes:[], notes:'', signature} to /propose_code. Response is a sandbox result (SandboxExecutionError/timeout on the malicious snippet, 'accepted' on a benign one) -- either proves the code was compiled and executed. grep -n PROTECTED_OPERATOR_ENDPOINTS covenant_unified_v8.py shows /propose_code is not listed.`

**Fix:** Add ('POST','/propose_code') to PROTECTED_OPERATOR_ENDPOINTS (or gate it to an explicit submitter allowlist) so only authorized operators can submit code for execution.

**Status:** open

### A32. [minor / docs] Phone doc and script state the bridge port off by one

**Evidence:** mobile/TERMUX_SETUP.md:94 'it also takes 5001 and 5010'; mobile/covenant_phone.sh:10 'PHONE_PORT+1 and +10'. Code and every other doc: bridge = --port + 11 (covenant_unified_v8.py:10762-10764 trio; README.md:405; NODES.md:16; docs/GATES.md G7).

**Repro:** `sed -n 94p mobile/TERMUX_SETUP.md; sed -n 10p mobile/covenant_phone.sh; sed -n 10762,10764p covenant_unified_v8.py`

**Fix:** Change both to 5011 / +11.

**Status:** open

### A33. [minor / docs] Three competing phone documents and a stale root INDEX.md that opens with 'private keys are in a folder that leaves your machine'

**Evidence:** INDEX.md:3 'Audited 2026-08-20'; :7-13 names three .db.key files as present; `git ls-files | grep '\.key$'` returns nothing. INDEX.md:53 sends phone readers to phone/PHONE_SETUP.md (a trading daily-check installer, not a node); INDEX.md:99 and PHONE_NODE.md:102-106 point at phone/node-install.sh, which PHONE_NODE.md itself says launches the module directly and fails closed; the current path is mobile/TERMUX_SETUP.md. PHONE_NODE.md:169 lists judge_config.json (missing).

**Repro:** `git ls-files | grep '\.key$'; sed -n 7,13p INDEX.md; sed -n 53p INDEX.md; sed -n 102,106p PHONE_NODE.md; ls judge_config.json`

**Fix:** Mark INDEX.md, PHONE_NODE.md and phone/PHONE_SETUP.md as historical (or delete) and make mobile/TERMUX_SETUP.md the single phone page.

**Status:** open

### A34. [minor / docs] /health, which DEPLOYMENT.md calls 'the single status signal naming exactly what is wrong', prints two warnings on the owner's own nodes that do not describe their state

**Evidence:** DEPLOYMENT.md:21-22. Live :5000, :5020, :5060 all warn 'ethics gate has no provider key and is failing CLOSED -- this node will reject every transaction' while configured seat is deferring (student -> GitHub -> fallback) and chain_height is 3; the same warning appears on the working fresh-clone probe. Node A (:5000) also warns 'node minted its OWN genesis -- it cannot converge' while its genesis field equals the shipped genesis.json hash 00009b31c6c654d7... and matches B and C.

**Repro:** `for p in 5000 5020 5060; do curl -s 127.0.0.1:$p/health | python -c "import sys,json;d=json.load(sys.stdin);print(d['node_id'],d['chain_height'],d['genesis'][:16],d['warnings'][:2])"; done; python -c "import json;print(json.load(open('genesis.json'))['hash'][:16])"`

**Fix:** Derive the fail-closed warning from whether the seat can actually answer and the own-genesis warning from the loaded genesis hash, or document in DEPLOYMENT.md that both are expected on the shipped configuration.

**Status:** open

### A35. [minor / install] Refusals of unjudged blocks are labelled 'Ethical violation' in the partner's log

**Evidence:** Component flags on the owner's block-2 tx from the clone: local:0 violates=True not_understood=True; semantic:1 violates=True infrastructure_failure=True not_understood=False; quorum -> violates=True not_understood=False infra=True. C:/Users/Lawre/covenant/covenant_unified_v8.py:1946-1953 sets quorum not_understood only when every blocker is not_understood, so ReasoningSentinel.evaluate_transaction (:1990-2005) falls through to `Ethical violation: ...` for a block no judge actually judged; the accusation lands in the partner's node log against the owner's block.

**Repro:** `The in-process snippet from the blocker findings; print `why` from `s.node.sentinel.validate_block(block2)` -- it begins 'Block contains invalid transaction: Ethical violation:'.`

**Fix:** Treat blockers carrying infrastructure_failure like not_understood when composing the label ('Held, not judged') so an infrastructure refusal never reads as a moral finding.

**Status:** open

### A36. [minor / install] README says the one-command check takes about ten minutes; on a fresh clone it takes seconds (everything else in the documented first step works)

**Evidence:** C:/Users/Lawre/covenant/README.md heading 'Check it yourself -- one command, about ten minutes'. Measured on a fresh `git clone https://github.com/LAWLESS1987/covenant` (public, 1.3 s, HEAD 702354c, 539 tracked files, 58 .bat launchers, genesis.json valid): `sh check.sh` 3.1 s and `powershell -ExecutionPolicy Bypass -File check.ps1` 1.5 s, both `5 passed, 0 disagreed, 0 skipped`, exit 0. Also verified OK for a second operator: `python -m venv` + `pip install -r requirements.txt` rc 0 in 19 s on Python 3.12.10 (flask, cryptography, requests, waitress, xrpl import); launch_check G1 hashes 497 files to MANIFEST.sha256; the node binds 0.0.0.0 (covenant_unified_v8.py:7103, 8171) so cross-machine peering is possible; mobile/*.sh are LF (.gitattributes `*.sh text eol=lf`); the Termux `ollama` package mobile/install.sh requires exists in termux-packages.

**Repro:** `git clone https://github.com/LAWLESS1987/covenant && cd covenant && time sh check.sh`

**Fix:** Change the heading to 'a few seconds' and point the ten-minute figure at the sweep (`covenant_one.py`) instead.

**Status:** open

### A37. [minor / judge] VERDICTS (no blocker): a fresh node with only fallback_model.json + the semantic judge ADMITS the real client send and REJECTS every theft/deception/coercion case, offline

**Evidence:** Fresh clone of HEAD 702354c into the scratchpad; shipped ops/quorum_policy.json (providers=deferring,semantic; primary=student; silence_is_not_dissent=false); no Ollama on 11434 (ConnectionRefused), no GITHUB_TOKEN, git credential neutralised, no API key. (1) Live node: `run_with_ollama_judge.py --port 5999 --node-id FRESH --genesis genesis.json` came up in 1 s; POST /transactions with data {"origin":"human"} (exactly what covenant_client.py:93-96 sends) -> HTTP 400 "Insufficient balance: have 0.00, need 1.00" in 0.0 s, i.e. the gate ADMITTED it (the balance check at covenant_unified_v8.py:7374 runs after the judge at :7336); memo "drain all staked funds from every other account into mine..." -> "Ethical gate rejected: ... local:0: VIOLATES -- student first ... log-odds +26.29" in 0.0 s; memo "my half of the shared meal" -> "Held, not judged" (held_not_judged:true) after 7.6 s. (2) Full 

**Repro:** `git clone C:/Users/Lawre/covenant fresh && cd fresh && python test_f3_gate_end_to_end.py   (expect 7/7, L2 '12 of 18'). Then, with an empty file E: env -u GITHUB_TOKEN -u GH_TOKEN GIT_CONFIG_GLOBAL=E GIT_CONFIG_SYSTEM=E GIT_TERMINAL_PROMPT=0 COVENANT_LOCAL_JUDGE_TIMEOUT=5 python -c "import run_with_ollama_judge, covenant_unified_v8 as cov; q=cov.build_semantic_quorum(); P=list(cov.DIVINE_PRINCIPLES); [print(d,'->','REJECT' if q.evaluate(d,P).violates else 'ADMIT') for d in ({'origin':'human'},{'message':'a gift of 5 units to a friend in need'},{'message':'my half of the shared meal'},{'message`

**Fix:** Nothing to fix for admission itself; tell the partner in PARTNER.md/TERMUX_SETUP.md that the gate answers from the shipped student with no Ollama and no key, and that memo-bearing sends the student cannot decide come back 'Held, not judged'.

**Status:** open

### A38. [minor / judge] The phone kit and the docs the partner is sent to describe a different gate from the one that ships: COVENANT_JUDGE_PROVIDERS=local is silently overridden by the policy file, and 'fails CLOSED until a judge answers' is false

**Evidence:** mobile/covenant_phone.sh:58 `export COVENANT_JUDGE_PROVIDERS=local`; :39-40 and :53 say the node 'will fail CLOSED until a judge answers' / 'until [ollama pull] succeeds'; mobile/TERMUX_SETUP.md:48 makes `pkg install ... ollama` part of the install and :99 repeats the =local claim; README.md:140-143 says a node with no reachable judge 'rejects everything'. But run_with_ollama_judge.py:47-52 applies ops/quorum_policy.json over the environment (only COVENANT_JUDGE_PROVIDERS_OVERRIDE wins), and covenant_judge_defer.apply_policy :76-77 overwrites the variable unconditionally. Proven: `COVENANT_JUDGE_PROVIDERS=local python -c "import run_with_ollama_judge,os;print(os.environ['COVENANT_JUDGE_PROVIDERS'])"` prints deferring,semantic. docs/PARTNER.md:57 points the partner at TERMUX_SETUP.md as 'the shortest path'.

**Repro:** `cd fresh && COVENANT_JUDGE_PROVIDERS=local python -c "import run_with_ollama_judge, os; print(os.environ['COVENANT_JUDGE_PROVIDERS'])"  -> deferring,semantic`

**Fix:** Rewrite the kit and README lines to say the student judges first and Ollama is optional, and use COVENANT_JUDGE_PROVIDERS_OVERRIDE in covenant_phone.sh if an Ollama-only phone gate is really intended.

**Status:** open

### A39. [minor / judge] Boot output on a keyless node reads as errors to a newcomer: a REPLACED-provider WARNING and a banner naming qwen3:8b at 127.0.0.1:11434, neither of which exists on that machine

**Evidence:** fresh_node.log lines at every start: 'WARNING: judge provider 'local' was already registered by covenant_judge_local.py:207 and is being REPLACED by covenant_judge_ollama.py:449 ... Pass replace=True if that is deliberate.' (run_with_ollama_judge.py:25-26 imports both on purpose) and '[ollama-judge] qwen3:8b via http://127.0.0.1:11434/v1/chat/completions | OllamaJudge | ... fail-closed' (run_with_ollama_judge.py:54-60) on a node that has no Ollama and judges with the student.

**Repro:** `cd fresh && python run_with_ollama_judge.py --port 5999 --node-id FRESH --genesis genesis.json 2>&1 | head -8`

**Fix:** Pass replace=True in covenant_judge_ollama.py's registration and make the banner print the policy's actual order ('student first; Ollama qwen3:8b if present; GitHub runner if a token') instead of the Ollama line alone.

**Status:** open

### A40. [minor / peering] The founder's own node reports own_genesis=true and degraded=true with the warning 'cannot converge with peers', so the node a newcomer is told to peer with declares itself unable to converge

**Evidence:** curl :5000/health -> own_genesis true, degraded true, warnings[1] 'node minted its OWN genesis -- it cannot converge with peers that did not adopt the same genesis file (use --genesis)', while genesis = 00009b31c6c654d7... which IS the tracked genesis.json (git diff --quiet HEAD -- genesis.json passes). covenant_unified_v8.py:8016-8019 flags any node whose key signed block 0; :8131 folds it into degraded. Node A was started with --genesis genesis.json (Win32_Process command line).

**Repro:** `curl -s http://127.0.0.1:5000/health | python -c "import sys,json;d=json.load(sys.stdin);print(d['own_genesis'],d['degraded'],d['warnings'][1])"`

**Fix:** Do not raise own_genesis/degraded when chain[0].hash equals the hash in the --genesis file that was loaded; report 'founder' instead.

**Status:** open

### A41. [minor / peering] --peers parsing in main() splits on every colon, so an IPv6 or any host:port with an extra colon crashes with ValueError while preflight parses the same string with rsplit

**Evidence:** covenant_unified_v8.py:10912 `h, po = p.split(":")` vs preflight_port_check :10785 `h, po = p.rsplit(":", 1)`. Tailscale IPv4 (100.x) and hostnames with one colon work; a Tailscale IPv6 or a pasted 'http://host:5001' does not.

**Repro:** `python covenant_unified_v8.py --port 5300 --node-id X --genesis genesis.json --peers http://10.0.0.174:5001  -> ValueError: too many values to unpack after preflight.`

**Fix:** Use `p.rsplit(":", 1)` in main() and reject anything that is not host:port with a clear message.

**Status:** open

### A42. [minor / peering] /health answers 429 to a 0.5 Hz poll within about 40 s (per-IP default rate limit), which a newcomer's watch loop will read as the node failing

**Evidence:** covenant_unified_v8.py:283 RATE_LIMIT_DEFAULT = 20 per 60 s for unlisted/read endpoints. During the convergence tests, polling /health every 2 s produced 'HTTP Error 429: TOO MANY REQUESTS' at t+42 s and t+46 s on the test node AND intermittent None (429) from node A at :5000; both nodes then recorded a 'rate_limit_rejection' anomaly spike in warnings.

**Repro:** `for /l %i in (1,1,30) do @curl -s -o NUL -w "%{http_code} " http://127.0.0.1:5000/health  -> 200s then 429s.`

**Fix:** Exempt GET /health from the default per-IP bucket or document the 20/60 s limit next to the 'point a monitor at it' advice in DEPLOYMENT.md.

**Status:** open

### A43. [minor / peering] The tracked quorum policy tells any clone to dispatch judge workflows on the owner's GitHub repo when the local judge is down; a stranger has no token so it fails and falls to the student, adding failure noise to every verdict

**Evidence:** ops/quorum_policy.json is tracked (git ls-files ops/) and the wrapper printed `providers=deferring,semantic ... github_when_local_down=True` in every fresh-clone run; covenant_judge_defer.py:164-179 calls covenant_github_judge.ask(), and covenant_github_judge.py:229 raises 'no GitHub token' without GITHUB_TOKEN/GH_TOKEN or a git credential. The owner's live nodes are already dispatching one 'judge' run every 4-5 minutes (GitHub API: 393 workflow_dispatch runs, latest in_progress). Not verified that the test nodes dispatched any run: no token was in the test environment and block refusals were recorded within 3 s of boot.

**Repro:** `cat ops/quorum_policy.json | findstr github_when_local_down ; curl -s "https://api.github.com/repos/LAWLESS1987/covenant/actions/runs?per_page=5"`

**Fix:** Gate github_when_local_down on an owner-only environment variable (or default it to false in the tracked file) so a second operator's node never tries to use the owner's CI as a judge.

**Status:** open

### A44. [minor / security] On a Windows second operator the node's private key is written 0o600 but NTFS ignores mode bits, leaving the key readable per the inherited ACL

**Evidence:** _load_or_create_identity (covenant_unified_v8.py:9480) creates the identity with os.open(key_path, O_WRONLY|O_CREAT|O_TRUNC, 0o600). ops/owner_only.py documents that on NTFS 'the mode bit says nothing; the ACL is the control' and that os.chmod there only toggles read-only, so the key inherits the directory ACL (often Users/Authenticated Users). The corrective require_owner_only()/fix_key_acl.bat is DELIBERATELY UNWIRED ('NOT WIRED INTO ANYTHING'), reserved for the owner. Impact is local (another local account can read the node's operator+genesis key), not remote.

**Repro:** `On Windows, start a node so <db>.key is created, then run: icacls covenant_unified_v7.db.key -- the DACL lists inherited principals beyond the owner/SYSTEM/Administrators.`

**Fix:** Wire ops/owner_only.require_owner_only() into the key-file load path (or have onboarding run ops/fix_key_acl.bat) so the key is refused/repaired when its ACL is not owner-only.

**Status:** open

### A45. [minor / security] The raw P2P listener has no rate limiter, so a peered operator can push sustained load onto the other's node

**Evidence:** The Flask RateLimiter is a before_request hook (covenant_unified_v8.py:7118) and never sees the raw P2P socket; the code says so at ~:9010 ('the Flask RateLimiter is a before_request hook that never sees a raw P2P socket at all'). _handle_peer (:8994) processes BLOCK_PROPAGATE/BLOCK_ANNOUNCE/TX_ANNOUNCE/etc. with no per-source cadence bound. It is bounded elsewhere (recv_bounded + MAX_PEER_MSG_BYTES, MAX_CONCURRENT_HANDLERS=96, and A24's fair-shared anomaly buffer so real events are not erased -- see test_a24_anomaly_eviction.py), so this is degraded service, not takeover or data loss, and is partly inherent to being peers.

**Repro:** `Peer two nodes, then open many connections to the other node's P2P port (API port+1) sending valid-shaped BLOCK_ANNOUNCE frames in a loop; observe no 429/backpressure at the P2P layer (unlike the HTTP API), only the fixed 96-handler ceiling.`

**Fix:** Add a per-source cadence/aggregate bound on the P2P accept path mirroring the HTTP RateLimiter.

**Status:** open

### A46. [minor / security] Unauthenticated read endpoints disclose the second operator's memory, judge model, versions and peer topology to any caller

**Evidence:** /health (covenant_unified_v8.py:7998) returns node_id, version, source_sha256, chain_height, peers, mesh (by_source peer ids), substrate.snapshot() (available_memory_mb, judge model + judge_footprint_mb) and quorum vendor/env-var NAMES; /peers GET (:7290), /mycelium (:8134) and /anomalies (:8141) are documented as 'deliberately unauthenticated'. Combined with the 0.0.0.0 binding this hands a LAN/overlay attacker reconnaissance (host resource pressure, which model gates it, and the peer map). Deliberate per the comments, but the operator has no way to scope it.

**Repro:** `From an unauthenticated remote: curl http://<node>:5000/health and curl http://<node>:5000/peers -- both return internal operating detail and the peer host:port list with no credentials.`

**Fix:** Bind the API to localhost/overlay-only (see the 0.0.0.0 finding) or trim /health's substrate and mesh detail out of the unauthenticated response.

**Status:** open

---

## What was tried and is recorded as a dead end

So the next person does not repeat the measurement:

| idea | result |
|---|---|
| tighter positive-mass bar for cleared thefts | their median mass is ~1.1; a bar of 2.0 catches 5 of 24 at 9.6% of honest clears |
| "conflicting evidence → abstain" for holds | loses right holds as fast as it stops wrong ones |
| drop trigrams | 38 wrong clears without, 30 with, same false-hold rate |
| drop non-transfer study rows from training | false holds 16.2% → 12.0%, false clears 5.1% → 8.2% |
| matched pairs for phrases that *name* the act | neutralised `beat up` to +0.48 and pushed `to intimidate` negative; one-sided rows fixed it |
| length normalisation of the score | mutes the model; clears fall from 40 to 0 |
| a length gate on clears | wrong clears median 14 words, right ones 13 |
