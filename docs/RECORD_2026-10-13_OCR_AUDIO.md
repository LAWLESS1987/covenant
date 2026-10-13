# Record — 2026-10-13: OCR-vs-audio comparison of @NJEst1987 videos

Recorded as-is at Lawrence's request (t109). **No interpretation is made here; interpretation is left open.**

## Before view (inbound)

Lawrence asked that tonight's record be committed to the covenant ledger, containing: (1) the OCR-vs-audio
report, (2) the status of the trend job on older Claude videos, (3) his own account stated on the Oct 13 call.
He asked that it be recorded without interpretation.

## (1) OCR-vs-audio comparison — first pass, finished 2026-10-13

- Scope: 9 recent video posts (5 of Lawrence's own, 4 reshares of other creators' TikToks).
- Mismatches, total across all 9 videos: **758** — 662 text-not-spoken, 55 wording differences, 41 speech-not-shown.
- Contradictions (text and audio saying opposite things): **0**.
- By the classifier: 517 editorial/format, 180 OCR misread, 12 timing, 5 ASR, 44 unexplained-by-classifier
  (41 of these in reshares; hand-checked as stylized or shortened captions).
- The report's stated conclusion: mismatches track video format (several of his own videos have no audio track
  or no speech), not topic or targeting; and the method cannot test interference, because text and audio come
  from the same posted file — comparing originals with platform copies would be needed.
- Oct 12 video (2109651670531498036, 606 s, Claude voice): 52.4 % matched in the first pass, 67 mismatches.
- **Accuracy note:** the 758 figure is for all 9 videos, not the Oct 12 video alone. The higher-quality deep dive
  on the Oct 12 video was **still running** at commit time (not included here).
- Artifacts: `docs/results/ocr-audio-20261013/REPORT.md`, `per_video.csv`.
  **Omitted:** `mismatches.csv` — it holds raw OCR/ASR transcript fragments, including other creators' reshared
  content; transcripts stay off the public tree. It remains on the operator's box. The report and per-video CSV
  name no reshare creators (checked).

## (2) Trend job — pending

Running, queued behind the Oct 12 deep dive, same method, applied to older Claude videos posted before
2026-10-12. Output: `/workspace/content-review-20261013/claude-videos-trend/` on the box. Status: **pending**.

## (3) Lawrence's account (his statement, Oct 13 call)

Recorded as his statement, not as a finding: older videos had no speech, but the on-screen text was coherent on
its own; the text stopped being coherent, which is the only reason he started adding speech to videos; the added
speech was coherent while the text was not; he believes the text-layer incoherence appeared by intent.

## After view (outbound + commit)

This file and the two artifacts above were committed and pushed to LAWLESS1987/covenant; the commit hash is in
`git log` for this file. Nothing was deleted or rewritten. Interpretation of (1)–(3) remains open.
