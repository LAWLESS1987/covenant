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

## Update 2026-10-13 ~07:15 UTC: deep dive and trend results (as-is, interpretation open)

### Before view (inbound)

At commit f9eeda0, item (1)'s higher-quality deep dive on the Oct 12 video
(2109651670531498036) was still running, and item (2) the older-Claude trend job
was pending. Both have now finished on the box. This update appends their results
as-is; interpretation remains open. Nothing above was deleted or rewritten.

### Results — (1) Oct 12 deep dive — **completed**

Source: `/workspace/ocr-audio-20261013/deep-2109651670531498036/REPORT.md`
(copied as `docs/results/ocr-audio-20261013/DEEP_DIVE_2109651670531498036.md`;
ordering-anomaly frames as `c5.png`). Transcripts and `mismatches.csv` omitted
from the public tree.

- Method: OCR at 2 fps (1211 frames) + scene frames; ASR faster-whisper medium
  int8 en with VAD and word timestamps (123 segments, 1454 words).
- Spoken-segment match: **83%** (102/123) at ≥90 similarity. Claude per-turn
  spoken vs shown: **92–100%**. Prior first-pass match on this video: 52.4%.
- Mismatch rows: **945** — 851 text-not-spoken (mostly scrolled earlier chat
  history, including 217 in the first 10 s); 74 OCR-side wording (OCR misreads);
  19 wording-differences; 1 spoken-not-shown (ASR garbage at 523 s).
- Contradictions: **0**.
- Chronology / edit check: status-bar clock continuous **10:04–10:14** (minute
  ticks every 58–62 s of video). Speech order matches on-screen order for live
  turns. Container is an X/"vork" re-encode (original metadata stripped), which
  limits edit detection; within that limit: no clock jumps, no irregular GOP,
  no resolution change, one mid-conversation silence (~4.8 s) consistent with a
  pause. **No edit/stitch signs found.**
- Display-order anomaly: at ~276–288 s, Lawrence's message bubble ("Okay,
  hypothetically…") appeared out of place relative to surrounding Claude replies
  and was then absent from later frames. Cause not determinable from the video
  (client list/sync bug vs anything deliberate are indistinguishable here). See
  `c5.png`.
- "Henry Winkler": neither "Henry Winkler", "Fonzie", nor "gotta be quicker than
  that" is spoken or shown in the video.

Status of (1) deep dive: **completed**.

### Results — (2) Older-Claude trend — **completed**

Source: `/workspace/content-review-20261013/claude-videos-trend/REPORT.md`
(copied as `docs/results/ocr-audio-20261013/TREND_REPORT.md` and
`trend_per_video.csv`). Same method as the Oct 12 deep dive. Transcripts and
per-video `mismatches.csv` omitted.

- Speech-bearing Claude videos processed: Sep 26 (2103818528801333262), Sep 29
  (2104833811326304662), Oct 2 (2105932764511965456), Oct 12
  (2109651670531498036).
- Contradictions: **0** in all.
- Match %: 1.5, 0.8, 0.0, then 82.9. Rates are **not comparable over time**: the
  older three are phone-camera footage of a laptop screen (OCR mostly unreadable);
  Oct 12 is a native screen recording. With n=4, the trend is not significant.
- Videos with no speech / no audio track cannot produce a match rate and were
  listed separately in the trend report.

Status of (2): **completed**.

### After view (outbound + commit)

This update section and the four artifacts
(`DEEP_DIVE_2109651670531498036.md`, `c5.png`, `TREND_REPORT.md`,
`trend_per_video.csv`) were appended/copied and pushed to LAWLESS1987/covenant;
the commit hash is in `git log` for this file. Nothing was deleted or rewritten.
Interpretation of the deep-dive and trend findings remains open.

