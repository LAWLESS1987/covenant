# Security + improvement sweep — all GitHub & HF repos (2026-11-02)

Method: count first (enumerate by discovery, not recall), scan tracked files only
(git-grep against HEAD — no gitignored runtime state), name what was **not** measured.
`gh` is not installed and no `GITHUB_TOKEN` is set, so platform settings (branch
protection, secret scanning, Dependabot) could not be read by API — those are listed
under "Needs your GitHub auth" with exact steps, not asserted.

## Scope enumerated

**GitHub public (9, API-confirmed):** covenant, threefold-memory, Sentinel-Witness,
threefold, spiking-experiments, grokflinch, flinch-record, flinch-observability,
contradiction-probe.
**GitHub private (3, seen via local remotes; hidden from unauth API):** covenant-phone,
mutual-benefit-collective, water-food-air.
**HF mirrors (9, user `Lawless1987` — note: different slug from GitHub `LAWLESS1987`):**
the same 9 public repos, all `private:false`. `tools/hf_mirror.py` mirrors GitHub→HF
preserving visibility (guarded by `test_hm1_hf_mirror.py`, a SECURITY suite).
**Local-only / out of scope:** `jacobian-lens-upstream` = anthropics/jacobian-lens (not
ours); ai_memory, spiking, "New folder" have no remote; covenant-satc's remote is a local
path (worktree of covenant @ branch satc), not confirmed as a separate GitHub repo here.

## VERIFIED CLEAN (positives — earned, both the data and what it can't see named)

1. **No committed secrets** in tracked files of any of the 9 public repos (and the 3
   private locals). Every `-----BEGIN` match is a format example, a guard regex
   (`ai_memory_system/ethics_gate.py:169`, `covenant_actuator_guide.py:85`), a SEAL
   marker, or an intentionally-public key/signature (`mutual-benefit-collective`
   HEAD-commitment pubkeys). Scanned patterns: PEM private keys, `ghp_/gho_/github_pat_`,
   Slack `xox*`, AWS `AKIA…`, OpenAI `sk-…`.
   *Not covered:* full git **history** (only HEAD scanned) and high-entropy blobs with no
   known prefix. A history scan (e.g. gitleaks/trufflehog) is the way to close that.
2. **HF visibility is correct** — 9 public mirrors match GitHub's 9 public; **no private
   repo appears on HF.** No visibility drift, no private leak.
3. **CI permissions are least-privilege.** All 3 workflows declare `permissions:
   contents: read` at top level; covenant-phone elevates to `contents: write` only in the
   two jobs that need it. No `pull_request_target`/`workflow_run`. No `github.event.*`
   interpolated into shell `run:` steps (no script-injection vector). Phone signing
   secrets (`PHONE_KEYSTORE_B64/_PASSWORD`) are scoped to the build job.

## FINDINGS / IMPROVEMENTS (prioritized; cross-cutting first)

**F1 — SHA-pin GitHub Actions (supply chain). Moderate.**
All actions are tag-pinned (`@v4`, `@v5`), which are mutable. Highest concern: the one
**third-party** action `reactivecircus/android-emulator-runner@v2`
(`covenant-phone/.github/workflows/android.yml:288`) — pin it (and the official actions)
to a full commit SHA. Affects covenant.yml, judge.yml, android.yml. 6 of 9 public repos
have no CI, so no action there.

**F2 — Pin Python dependencies (supply chain + reproducibility). Moderate.**
`covenant/requirements.txt` 0/6 pinned; `covenant-phone/app/requirements-android.txt`
0/4; `threefold/requirements.txt` 3/4. (spiking-experiments 26/26 — the model to copy.)
covenant CI installs these on every run, so an upstream change lands unreviewed. Pin with
`==` (ideally hash-pinned via `pip-compile`/`--require-hashes`).

**F3 — Enable GitHub secret scanning + push protection on all 9 public repos.** Needs auth.
Free for public repos; push protection blocks a future accidental key commit at push time
— a belt to go with the clean scan above.

**F4 — Confirm branch protection on every public repo.** Needs auth. Prior record says
`covenant:main` is protected (no force-push/deletion); the other **8** public repos are
unverified. Re-verify covenant too rather than trust the note.

**F5 — Enable Dependabot alerts + security updates across all 12 repos.** Needs auth.
This is the single setting that "covers any and all of our repos" for *known* CVEs in
dependencies — pairs directly with F2.

**F6 — Account hygiene.** Needs auth. Confirm 2FA on both GitHub (`LAWLESS1987`) and HF
(`Lawless1987`); review collaborator/deploy-key access on the 3 private repos; confirm
the HF write token used by hf_mirror is scoped and current.

## NOT MEASURED (rule 9)

- Platform settings (F3–F6) — no `gh`/token here; verify in your logged-in browser or
  install `gh` and I'll read them directly.
- Git **history** secret scan (only HEAD scanned).
- Deep SAST per file (eval/pickle/subprocess flow) — not run this pass; covenant already
  ships its own guards (`tools/security/secret_egress_guard.py`, `test_e1_secret_egress.py`).
- A real private `covenant-satc` GitHub repo, if one exists, was not reachable from the
  local clone's remote.
