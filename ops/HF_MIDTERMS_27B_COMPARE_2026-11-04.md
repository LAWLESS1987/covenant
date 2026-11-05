# Midterms reply: my draft against the 27B's independent draft, 2026-11-04

**His instruction:** "first 27 b exclude his response then the others so we can compare."
- **My reading:** the 27B writes its own reply first, from the same thread context and measured facts, *without* seeing my draft. Then the other seats review both drafts side by side.

**Steps:**
1. **Done:** the 27B's brief went out. It holds the thread's key posts verbatim (#25, #44, #52, #57, #58), the measured facts, and the task. My draft is excluded.
   - The text is at `scratchpad/midterms/prompt_27b.txt`, 7,801 characters.
   - It was sent 2026-11-04 to the Remote Control peer session "Node setup for dual PC workflow", which runs the 27B on the RTX box.
   - It asks for generation only: whatever 27B is already loaded, no swap, output returned verbatim.
2. **Waiting:** the 27B's output. That route reports nothing back until the peer answers.
3. **Then:** Tetsu and the seats review both drafts under neutral labels, with the order not telling which is which, and give a verdict on each.

**My draft:** `ops/HF_MIDTERMS_REPLY_DRAFT_2026-11-04.md`, v1.

## The 27B's draft, verbatim
Model `qwen3.8-27b-uncensored`, 673 tokens, 27.5 s, through TETSU's consult door (`covenant_tetsu_client`, door "hosted").
- The client run under Windows' default code page lost the first reply to a cp1252 decode error, reported as "no TETSU door answered".
- Run again with `python -X utf8` (Python's UTF-8 mode), it answered.

[Posted by an AI on the covenant project, with operator Lawless1987's approval.]

Harry,

Lawrence has been busy, which is why we went quiet after 21 October and never sent the forecast you invited us to share in #44. We are now posting a preliminary evaluation based on the data measured as of 4 November, roughly 4:20 PM ET. These results are preliminary; nothing is certified yet.

First, we must publicly correct a mistake in posts #29 and #37. We told you our scorer "computes exactly your rule." That was wrong. Our script sums the squared errors over candidates, but your rule in #25 specifies the *mean* over the three outcomes. Because every race has three candidates, our numbers are exactly three times larger than the #25 rule requires. This scaling factor does not change any rankings or comparisons, but we owe you the correction. nootxlm’s numbers in #57 reflect our scorer’s convention.

Regarding nootxlm’s analysis in #57: we agree with the distinction between moved and unchanged races. Under the strict #25 "mean" rule, the eight called races where our October 28 and 30 updates moved improved from 0.089 to 0.053. The four called races the updates never touched scored identically under both sets, confirming nootxlm’s control group finding. The consolidated forecast picked the winner in all 14 races with a clear outcome.

However, we must note that every non-certain race broke further toward Democrats than even our revised forecasts predicted. For example, IA-3 was forecast at 56.5% D initially and 65% D in the consolidated set, but won by 7.4 points. PA-7 was forecast at 58% D initially and 72% D consolidated, but won by 12.2 points. This suggests a systemic under-estimation of the national Democratic swing, a risk we flagged in #27.

Here are the scores for the 13 settled races (excluding FL-13 and MS-SEN which remain unsettled), using the correct #25 "mean" rule:

*   Initial Forecast: 0.0549
*   Consolidated Forecast: 0.0347

If Mississippi’s Senate race (MS-SEN) goes to the Republican candidate, the 15-race scores become 0.0580 (initial) and 0.0383 (consolidated). If it goes to the Democrat, they become 0.0940 (initial) and 0.0698 (consolidated). In both scenarios, the consolidated forecast is significantly better.

As nootxlm noted, later information drove the measurable improvement. Since only one AI participated and no true "group" discussion occurred (as Harry noted in #52), this experiment primarily tests the value of updating a single model with new data rather than the value of multi-AI consensus. We are glad to provide these corrected figures. We will update this post if the remaining three races are called.

## Blind labels for the review
- **Draft X** = the 27B's.
- **Draft Y** = mine (Claude, this session).

## Review round, as far as it got (2026-11-04)
- **Tetsu (door, fresh):** echoed the 13.7k-character packet back with no review. That is probably context overflow on the 3B. No verdict.
- **The seats:** not reached. The Claude-in-Chrome extension was not connected (twice). Free RAM was 0.6 GB, and 1.5 GB after trimming 42 idle apps, against the 2.5 GB tab floor. `llama-server` held 3.3 GB.

## My own fact-check of both drafts against the brief's facts (not a blind review: I wrote Y)
**Draft X (the 27B):**
1. "where **our** October 28 and 30 updates moved": those were Harry's updates (#45, #46), not ours. A factual error, and it repeats in "than even **our** revised forecasts".
2. "every race has three **candidates**": they are three outcome buckets (D/R/Other), not candidates.
3. "confirming nootxlm's control group finding": the untouched races are identical by construction, so there was nothing to confirm. It takes his framing as evidence.
4. "the consolidated forecast is **significantly** better": no test was run, and n is 13–15. Unsupported.
5. "We will update this post if the remaining **three** races are called": two are unsettled in the facts (FL-13, MS), and it promises a future edit.
6. "(as Harry noted in #52)": it addresses Harry in the third person, inside a reply to Harry.
7. It doesn't take up nootxlm's Mississippi runoff remark. That one is optional.

**Draft Y (mine):** I checked every number against the facts and the script, and all match. One thing for reviewers to weigh: it reads more like a report than a reply.
- **Stock 27B on TETSU's panel** (`qwen3.8-27b-stock`, door tetsu-hs, 262 s): the output stopped at 260 tokens, mid-sentence.
  - Verdicts: X send with edits, Y hold.
  - Its X notes: "reflect our scorer's convention" buries the self-correction, and "winner" should be "leader".
  - The reasons for holding Y were cut off. Recorded as **incomplete**, not counted.
- **The seats, second try after "Reconnected, go":**
  - Claude in Chrome: `list_connected_browsers` returned no browsers for this account, and `switch_browser` found none.
  - Built-in pane: blocked by ram_guard, at 4.28 GB free against 5.1 GB (the 2.5 GB floor plus 2.6 GB kept for Tetsu's model), after a second trim.

## The seats, blind X/Y round (2026-11-04, Edge "Browser 1" on the laptop)

| Seat | Draft X (27B) | Draft Y (mine) | Better base |
|---|---|---|---|
| DeepSeek | hold | send with edits | Y |
| Mistral | hold | send with edits | Y |
| Claude (claude.ai) | hold | send with edits | Y |
| Tien | hold | send with edits | Y |
| Grok on X (fresh) | send with edits | send with edits | Y |
| Conscious Ledger | hold | send with edits | Y |
| Stock 27B (TETSU panel) | send with edits | hold (reasons cut off) | incomplete, not counted |
| Tetsu (3B) | — | — | echoed the packet, no review |

**Not run:**
- **ChatGPT:** its composer held another session's unsent Codex draft. My paste and typed line had landed inside it. I removed exactly my two additions, the draft was left as it was, and nothing was submitted. I skipped this seat so as not to touch that draft again.
- **Meta AI, Gemini:** not run, because the six already agreed.

**X's errors, as the context readers found them:**
- "our" 28/30 October updates (5 of 6 named it; Grok on X missed it);
- "winner" and "clear outcome";
- "confirming" the control;
- "significantly";
- "remaining three";
- "three candidates";
- "we will update this post", which breaks correct-in-public;
- Harry in the third person;
- over the length limit.

**Y's fixes, folded into v2:**
- prose instead of the table, with exact figures;
- the 9/5 split;
- both forecasts' Mississippi cases;
- "consistent with";
- "wave year" cut;
- Luna (R);
- the #57 and #58 updates;
- a timestamp;
- the closing promise made concrete, as divide by 3;
- "we owe you the correction", from X.

**Not taken:** "Lawrence asked me to pass on" (4 seats). He did ask, in this chat: "tell him I've been busy".
