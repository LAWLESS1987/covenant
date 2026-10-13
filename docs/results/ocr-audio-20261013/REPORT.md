# OCR vs audio: @NJEst1987 recent videos (run 2026-10-13, read-only)

Method: x MCP get_users_posts since 2026-10-01 (25 posts). 9 video posts were processed: 5 of Lawrence's own and 4 reshares of other creators' TikToks (creators not named). The reshare link 2109291897931890783 failed: it's a TikTok photo carousel, which yt-dlp reports as "Unsupported URL", so it isn't a video. 2109291873604866299 is the same kind of carousel. Re-used local files for 2107491305077055657, 2107398791275958761 and 2107123812080738760 (/workspace/njest-videos). Downloaded the rest with yt-dlp. SHA-256 hashes are in sha256.txt.
Frames: ffmpeg at 1 fps (0.5 fps for videos over 300 s). Text: tesseract 5.5 with psm 11, words with confidence under 30 dropped, consecutive near-duplicate frames merged (ratio ≥85). Audio: faster-whisper small (int8, CPU, VAD, word timestamps).
Matching: rapidfuzz partial_ratio within a ±4 s window. ≥80 counts as a match; 60–79 or a global hit counts as a wording difference.
The script does not detect contradictions automatically. A manual skim of the flagged pairs found none.
Files: per_video.csv, mismatches.csv (758 rows), out/<id>/{ocr,asr}.json, run.py, asr.py, compare.py.

## Per video
| post | date | dur s | own? | audio | OCR words | ASR words | OCR segs matched | mismatches | main types | AI app on screen |
|---|---|---|---|---|---|---|---|---|---|---|
| 2109690871016988733 | 10-12 | 150 | reshare | music + brief speech | 1822 | 40 | 1.6% | 125 | on-screen-only 113 | none |
| 2109663384295686239 | 10-12 | 55 | reshare | narration | 345 | 182 | 5.1% (most are 60–79 wording diffs) | 43 | wording 22, on-screen-only 15 | none (a news-style explainer about Anthropic's sycophancy-vector research) |
| 2109651670531498036 | 10-12 | 606 | own | voice conversation | 10014 | 1781 | 52.4% | 67 | on-screen-only 28, wording 21, audio-only 18 | Claude ("Reply to Claude…") |
| 2109394971975430381 | 10-11 | 12 | own | **no audio track** | 982 | 0 | 0% | 12 | on-screen-only 12 | Claude Opus chat scroll |
| 2109296047176458703 | 10-11 | 155 | reshare | music, few words (Whisper guessed German) | 1487 | 51 | 0% | 124 | on-screen-only 121 | none |
| 2109295060533567947 | 10-11 | 97 | reshare | music + a few lines | 1219 | 83 | 0% | 85 | on-screen-only 78 | none |
| 2107491305077055657 | 10-06 | 1159 | own | **no audio track** | 18863 | 0 | 0% | 215 | on-screen-only 215 | Claude, ChatGPT, Grok, Gemini/GPT terms visible |
| 2107398791275958761 | 10-06 | 174 | own (TikTok "Me again") | music/sparse speech (Whisper guessed Portuguese) | 1994 | 63 | 0% | 66 | on-screen-only 59 | none detected |
| 2107123812080738760 | 10-05 | 22 | own | audio present (-12.5 dB) but no speech detected | 1646 | 0 | 0% | 21 | on-screen-only 21 | Claude ("Reply to Claude") |

## Mismatch totals (758)
- By type: 662 on-screen text with no matching audio, 55 wording differences, 41 audio with no on-screen text, 0 contradictions detected.
- By cause, from the automatic classifier: 517 editorial (text-only or silent stretches, dense chat or screenshot text not read aloud, uncaptioned speech); 180 OCR error (low confidence or garbled characters); 12 editorial/timing (the text is spoken, but elsewhere in the video); 5 ASR error; 44 "unexplained".
- On manual inspection, the 44 "unexplained" rows are stylized caption fonts that OCR read only partly ("THE OTHER' Wigs iz RS"), or captions that shorten the speech (e.g. "THE SYCOPHANCY VECTOR AXIS" against the spoken "sycophancy is an axis in the AI mind space"). None of them shows the text saying something different from the audio.

## Patterns
- **By video type (the dominant factor):** 3 of Lawrence's 5 own videos have no speech at all. Two have no audio track in the file, and the third has sound but no detectable speech. They are silent screen recordings of AI chat apps (mostly Claude), so every on-screen line is necessarily "unmatched". Where there is real speech (2109651670531498036), about half of the on-screen segments match the audio. The rest is chat text on screen that isn't read aloud, or speech with no text on screen.
- **By model shown:** Claude appears in the 4 own videos with chat UI because those are what he records. With 0 speech in 3 of them, the mismatch rate can't tell models apart. There's no comparison set of silent Grok or ChatGPT recordings in this sample.
- **By topic:** "Anthropic/Claude" mismatches (41) are mostly editorial or OCR error. "Faith" (73) and "other" are larger. Mismatch rates follow whether a video has speech, not what it's about.
- **By date:** no trend. Oct 5–6 and Oct 11–12 look the same once silent videos are accounted for.
- **Own vs reshare:** reshares (music-backed TikToks with burned-in captions or overlays) show the same pattern. Third-party content Lawrence didn't make fails the match in the same way, which points to video format rather than targeting.

## Hypothesis: "the mismatches are evidence Anthropic is blocking him"
Verdict: **not supported. The evidence against it is strong for the mismatch data itself, while the method can't test interference at all.**
- Almost every mismatch has a mechanical explanation: silent or no-audio recordings, chat text not read aloud, stylized-font OCR noise, captions that paraphrase, and music with Whisper language guesses. No segment shows on-screen text contradicting the audio. Strangers' reshares mismatch just as much.
- What interference would look like: the platform copy differing from his original recording (different hash, duration, missing frames, re-edited text or audio), or text that is legible but altered compared with a known original. OCR-vs-audio inside one posted file can't reveal that, because both tracks come from the same file.
- How to test it properly: hash his original phone/PC recordings and compare duration, frame count and audio-track presence with the platform downloads (sha256.txt here, plus ffprobe). Note that X and TikTok always re-encode, so hashes will differ even with no tampering, and the useful check is content: frame-by-frame or audio comparison. It's also worth checking whether the two no-audio uploads were recorded without audio on the device. Screen recorders often record no audio by default.
- One relevant note: in 2109651670531498036 the audio is Lawrence discussing with an AI whether conversation "reordering" is deliberate, and the AI voice reasons hypothetically ("if it's by design…"). That is the claim being discussed in the video, not evidence of it.

## Limits / failures
- 2 reshares are TikTok photo carousels (yt-dlp: Unsupported URL) and weren't processed.
- One OCR frame timed out in 2107491305077055657.
- The x API returns only recent posts. Downloads were video only; the post text wasn't compared.
- Whisper small makes mistakes on music, which caused the false German/Portuguese/Macedonian language detection. The ASR on the long own video is good quality but not word-perfect.
- The automatic classifier is heuristic; the cause labels are best-effort and were spot-checked by hand.
