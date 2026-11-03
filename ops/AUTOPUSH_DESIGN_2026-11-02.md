# Laptop auto-push: design, build record, and arm plan (2026-11-02)

His words: "everything should be a sync between each comp and phone", "Enable auto-push",
"as much redundancy as possible". Scope: **code + chain + record sync; keys/`private/`/
holdings/`*.key` NEVER sync.** Three nodes: laptop (Sales/covenant-pc), TETSU, and the phone
(their network addresses + device names live only in gitignored `ops/` files, never here: this repo
is public). Semantics are TETSU's unison.py design, recorded here and built against
**current main's** `hf_mirror.py` (the A396 version: `guarded_push` ff-only + opsec, `SNAPSHOT_ONLY`).

## What already exists / is armed (verified 2026-11-02)
- **Chain**: Node D on TETSU peers A/B/C + phone (3-way, live).
- **Site**: `tools/site_autodeploy.py` via `CovenantSiteAutoDeploy` (every 15 min). LIVE.
- **Unison brain**: TETSU `unison.py` serves the feed at tailnet `:8800/unison` every 900 s.
- **HF mirror**: `tools/hf_mirror.py` + `CovenantHFMirror` (every 120 min). LIVE. ff-only,
  opsec-hooked, visibility-preserving.
- Feed URL in gitignored `ops/local_unison_feed.txt` (or env `COVENANT_UNISON_FEED`).

## GitHub push semantics (authoritative, from the TETSU unison session)
For a repo whose feed `needs_push` contains `github`:
1. `target` = a full commit sha (`unify/auto` in TETSU's bare mirror). States that carry a
   target: FAST_FORWARD / UNIFIED (TETSU verifies target descends from every fetched head).
2. **ff-only** against GitHub's **current** main at push time. Refuse non-ff; never `--force`.
3. **Fetch target from** own_git on TETSU: `http://<tetsu>:8400/own/<repo>.git` branch
   `unify/auto` (feed `fetch_from`, `<tetsu>`→feed host). NOT from HF. Require `FETCH_HEAD==target`.
4. **opsec-scan the range `github_main..target`** before pushing — done by reusing `guarded_push`,
   whose scan covers exactly the objects GitHub does not already hold. `git push <target>:main`, no force.
5. NEVER: push for `website` (site deploy, keyed on top-level `site_deploy_due`); push history to a
   snapshot repo (`snapshot_copies` lists `hf`, or in `SNAPSHOT_ONLY`); push on
   NEEDS_HUMAN/ERROR/UNREACHABLE/SNAPSHOT_DUE/UNISON; push tags; push the `unify/auto` branch name
   anywhere. Private repos pushed only to their own origin (visibility read, never guessed).
6. **OPEN-PR GUARD** (his "mutual benefit"): an open PR whose base is the target branch SKIPS the
   repo — a ff under an open PR forces the operator's review to rebase. Error reading PR state ==
   treat as open (fail-safe). Auto-resumes when the PR is merged/closed.

## Built 2026-11-02 — `tools/repo_autopush.py` + `hf_mirror` holds guard
- `tools/repo_autopush.py`: dry-run default, `--run` to push, logs each pass to gitignored
  `ops/repo_autopush.jsonl`. Reuses `hf_mirror` primitives (`guarded_push`, `_opsec`,
  `list_owned_repos`, `_auth_header`, `_api`, `_git`, `SNAPSHOT_ONLY`) and the single feed reader
  (`hf_mirror.feed_url` / `read_feed`). Implements the sequence above. (Fixed one bug in the earlier
  reference draft: the GitHub-main fetch passed `-c <auth>` *after* `fetch`, where git ignores it;
  now passed as a git-level `cfg` option.)
- `hf_mirror.holds_mode()` (fail-closed holds-drift guard): `SNAPSHOT_ONLY` is hardcoded in
  hf_mirror; a hold added on TETSU only would be invisible, so hf_mirror could history-push a repo
  another node marked HF-snapshot. `holds_mode` reads the feed: snapshot-mode if in `SNAPSHOT_ONLY`
  OR feed `snapshot_copies` lists `hf`; **refuse** a would-be history push if the feed is
  unreachable / `status != ok` / the repo is missing; a `SNAPSHOT_ONLY` repo the feed omits stays
  snapshot (safe), logged, not refused.

## Tests (both-ways, driven red then green — CLAUDE.md rule 8)
- `test_ap1_repo_autopush.py` (8/8): a clean ff is pushed for real (GitHub main advances); non-ok /
  unreachable feed pushes nothing; open PR skips (and would-push without it); non-ff skips (and a true
  ff would-push); snapshot/`website` skip; a moved own_git target skips. Each guard was mutated and the
  suite confirmed RED (open-PR, ff-ancestor, snapshot, moved-target, status, and a suppressed push).
- `test_hd1_hf_mirror_holds.py` (10/10): clean feed pushes; the same repo marked `snapshot_copies=hf`
  flips to snapshot; unreachable feed refuses (reachable lets it push); missing-from-feed refuses;
  `status != ok` refuses; a `SNAPSHOT_ONLY` repo is snapshot in every feed state; `main()` wires the
  guard. Mutated three ways, confirmed RED each time.
- `test_hm1_hf_mirror.py` still 9/9 (existing guard unaffected).

## Live dry runs 2026-11-02 (feed @ :8800)
- `repo_autopush` dry run: **Sentinel-Witness SKIPPED — open PR(s) [8,7,6,1] into main** (PR #8 is the
  one the design flagged); all other repos UNISON → `github not in needs_push`. **0 pushed, 0 error.**
- `hf_mirror --dry-run`: Sentinel-Witness + the unison repos → `push`; covenant + threefold-memory →
  `snapshot`; and **6 private repos NOT in the feed → `refuse`** (see decision below).

## OPERATOR DECISION #1 — private repos absent from the unison feed
`CovenantHFMirror` is LIVE and today mirrors 6 PRIVATE repos (private→private): `ai-accountability-
evidence`, `covenant-phone`, `covenant-satc`, `lawless1987-website-backup`, `mutual-benefit-
collective`, `water-food-air`. The unison feed lists only the 9 unison-tracked repos, so the new
fail-closed guard REFUSES a history push for any repo missing from the feed — i.e. **once this
merges, the next CovenantHFMirror run stops mirroring those 6 private repos** until a decision:
  (a) add them to TETSU's unison feed (then they mirror again, now drift-guarded); or
  (b) exempt non-unison repos from the guard (feed governs only repos it lists; others fall back to
      the hardcoded `SNAPSHOT_ONLY` decision — preserves today's behavior, narrower guard); or
  (c) leave them refused (strict posture: hf_mirror only history-pushes repos unison has vetted).
This is deliberately left to the operator (rule 5 — scope is his call). The guard ships as written
(literal fail-closed); the dry run above is the review surface.

## OPERATOR DECISION #2 — Sentinel-Witness PR #8
SW is FAST_FORWARD with HF 3 commits ahead (model-card ×2 + Apache LICENSE, all made on HF). The
open-PR guard holds the SW push automatically while PR #8 (and #7/#6/#1) are open. No action needed
to stay safe; when the PR is merged/closed the push resumes. (Note: `guarded_push` would also refuse
SW today as DIVERGED until HF is unified — a second, independent brake.)

## Arm plan (AFTER the operator reviews the dry run — do NOT arm in the build session)
Model on `CovenantHFMirror`. One-liner (PowerShell, run as Lawre), to be run by the operator:

    schtasks /Create /TN CovenantRepoAutopush /SC MINUTE /MO 30 /RL LIMITED ^
      /TR "wscript C:\Users\Lawre\site\repo_autopush.vbs" /F

with `C:\Users\Lawre\site\repo_autopush.vbs` launching
`COVENANT_GH_READ=1 python <checkout>\tools\repo_autopush.py --run` (feed via
`ops/local_unison_feed.txt`). Start with `--dry-run` in the vbs for the first live cycles; switch to
`--run` once a few dry passes read clean. `repo_autopush` needs the feed reachable; when it is not,
it pushes nothing (returns 2) — safe.

## Redundancy map
GitHub + HF + website + TETSU own_git (`:8400`) + each node's clones; two network paths
(tailnet + headscale). No single node is a chokepoint.
