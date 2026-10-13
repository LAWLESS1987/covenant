# t112 full coherence pass, 61 Claude conversation videos (X @NJEst1987), 2026-10-13

Recorded as-is. Interpretation is left open.

## Method
- All 61 videos were re-OCRed at a uniform 2 fps with tesseract on native frames. The 4 videos with heavy scene changes got extra scene frames.
- The three phone-camera videos (Sep 26, Sep 29, Oct 2) got frame stacking plus super-resolution/sharpening before OCR (cam_enhance.py).
- Text-only read: a structural detector (structural.py) tracks every OCR line cluster across frames and flags:
  - order inversion between frames
  - a line inserted in the middle of existing lines, or a line vanishing
  - a line whose successor changes (and flip-flops)
  - the status-bar clock running backwards, confirmed across 2 frames
- Audio-on read: faster-whisper ASR on every video with speech (9 posts plus controls), aligned to OCR within ±4 s (align.py).
- Controls:
  - 4 non-Claude NJEst videos (ctl_*)
  - 3 external Claude/TTS screen recordings (ctlx_A/B/C; sources are kept private)
  - Each control produced only OCR-variant or overlay false positives. ctlx_B flip-flop = TTS caption overlay.
- Every flagged event in a Claude video was checked by eye against the frames.

## Result
- COHERENT 56, UNREADABLE 3, INCOHERENT 2, PARTIAL 0, NOT_JUDGED 0.
- Of the 56 COHERENT, most rest on the automated 2 fps structural check (clean), not a line-by-line human read. The reason column says which.
- False positives were rejected on frames:
  - Jun 28/29 scroll and "out of messages" banner overlay
  - Sep 23 live voice-caption overlay
  - clock dips that were OCR digit misreads (Jun 28, Jul 6)

## Earliest verified incoherence: 2026-10-06, post 2107491305077055657 (Opus, ~9:35–9:40 on-device clock)
- 48–66 s: the same Claude reply ("Me — I jumped to giving you advice…") renders twice, once above and once below a user bubble. User bubbles shift position between adjacent frames (f_00098/99, f_00132/133).
- 338–345 s: the user bubble "It did it again." flips above and below the reply "Ha — fair. Noted…" across consecutive 0.5 s frames, the reply block appears twice, and then the bubble disappears (f_00677–f_00681).
- 53 structural events in total (order inversions at 48, 65, 113, 128, 148, 158, 338–345, 355, 364, 392 and 718–750 s).
- The on-screen text in the same conversation also reports the reordering.
- Oct 12 (2109651670531498036) shows the same class of break: at ~276–288 s a reply appears with no user bubble in place, the bubble flashes up in the wrong spot, and it is absent from later frames. There are also 97/357/367 s events.
- Nothing earlier (Jun 28 to Oct 5) shows a verified break. The Sep 26 to Oct 2 camera videos cannot rule one in or out.
- The evidence frames stay private: they show third-party notifications.

## Table
See verdicts_61.csv (date, post_id, verdict, reason, prev_t111).
