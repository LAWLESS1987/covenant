# Claude videos on @NJEst1987: OCR vs audio, before and including Oct 12 2026 (read-only)
I used the same method as the Oct 12 deep dive (/workspace/ocr-audio-20261013/deep-2109651670531498036/REPORT.md): 2 fps + scene frames (scene>0.15), dedupe, tesseract psm4 with 2x upscale and threshold, faster-whisper medium int8 en VAD with word timestamps, the same fuzzy alignment, and the same mismatch types and classes. There are two forced deviations. OCR polarity is adaptive (invert only for dark frames) and runs on the full frame, not the phone-app crop. Speaker labels are "unknown".

## Inventory: which older videos are Claude conversations
Candidates are all 34 own videos from Aug 15 to Oct 12 in /workspace/njest-videos. I identified the model from the existing OCR corpus and the ASR content.
- **Claude, with speech, processed:** 2103818528801333262 (Sep 26), 2104833811326304662 (Sep 29) and 2105932764511965456 (Oct 2). All three are phone camera footage of a laptop screen. The Claude identification comes from the ASR content (e.g. "conversation search tool", Anthropic references), plus one OCR "claude" each. 2105932764511965456 is probably Claude, not certain.
- **Duplicates, skipped:** 2104833919778521462 and 2104834740603756776 have identical audio to 2104833811326304662.
- **Claude, no speech:** 2107123812080738760 (Oct 5, audio track but no speech, processed: 0 ASR words). 2090668597852987506 (Aug 21, no audio track; its OCR mentions Claude 22 times). Prior pass: 2109394971975430381 (Oct 11, no audio) and 2107491305077055657 (Oct 6, no audio). 2107398791275958761 (Oct 6, music, little speech; model unclear). None of these can produce a match rate.
- **Not Claude, excluded:** 2102623353060086082 and its duplicate 2102623752106193118 (Sep 23, Grok); 2104822302277792220 (Sep 29, ChatGPT/Gemini); 2103244061037519140 (Sep 24, Gemini Live). The rest of Sep–Oct are short clips with no audio.
- Nothing needed downloading.

## Per video (speech-bearing Claude only for rates; full table in per_video.csv)
| post | date | dur s | capture | OCR words | ASR words | match % (ASR segs >=90 to OCR) | mismatches | per 100 ASR words |
|---|---|---|---|---|---|---|---|---|
| 2103818528801333262 | 09-26 | 663 | phone filming laptop | 896 | 1631 | 1.5 | 201 | 12.3 |
| 2104833811326304662 | 09-29 | 637 | phone filming laptop | 318 | 1458 | 0.8 | 135 | 9.3 |
| 2105932764511965456 | 10-02 | 108 | phone filming laptop | 64 | 79 | 0.0 | 11 | 13.9 |
| 2109651670531498036 | 10-12 | 606 | native screen recording | 8933 | 1454 | 82.9 | 945 | 65.0 |
Mismatch counts by type and class are in per_video.csv and each folder's mismatches.csv. Contradictions: 0 in every video. No case where text and audio say opposite things.

## Trend
- **Match %:** 1.5, 0.8, 0.0, then 82.9. Spearman rho vs time is 0.2.
- **Mismatches per 100 ASR words:** 12.3, 9.3, 13.9, then 65.0. Rho is 0.8.
- **Significance:** with n=4, neither is significant. The exact permutation p for rho=0.8 is about 0.17 one-sided.
- **The trend isn't interpretable.** The Sep and early-Oct videos are phone footage of a laptop, so their OCR is mostly noise. That makes match % about 0 and keeps "text-not-spoken" counts low because little text is readable. The Oct 12 video is a crisp native screen recording that captures thousands of words of scrolled history. Its high mismatch count is mostly that history (text-not-spoken), and its match % is far higher. The rate differences track the capture format, not time or targeting.
- **Classes for the older videos:** their "spoken-not-shown, captioning/app-display choice" rows really mean the screen text was unreadable in the camera footage.

## Bottom line
There's no evidence the OCR-vs-audio mismatch rate rose over time in a way that points to interference. The only comparable signal is no contradictions anywhere. The one real anomaly in the set is the Oct 12 on-screen ordering glitch at 276-288 s, described in that deep dive. To track it properly, future recordings need to use native screen capture with audio on.
