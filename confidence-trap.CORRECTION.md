# Correction to the confidence-trap post (A236)

**The original is [confidence-trap.md](confidence-trap.md), beside this file, unedited.**
It was posted on 2026-09-24 to the Hugging Face forum, Research category:
<https://discuss.huggingface.co/t/the-confidence-trap-why-ai-systems-are-deliberately-trained-to-sound-certain-when-theyre-wrong/180706>,
and committed here nine minutes later (`cfa07d8`).

**What was wrong.** The title says AI systems are *deliberately* trained to sound
certain when they are wrong. "Deliberately" asserts intent. Nothing in the post
supports intent, and nothing this project has measured does either.

**What the evidence supports** is weaker in one way and stronger in another. Weaker:
nobody chose it. Stronger: nobody had to. Human raters score confident-sounding
answers higher, so a model trained on their preferences learns to project certainty
its accuracy does not earn. That is the mechanism the post itself describes in its
second paragraph. It is an incentive artifact, and it survives without anyone
deciding anything.

**How it was found.** On the morning of 2026-09-27 the operator read the title aloud
to the Claude app on his phone, which flagged the word. He conceded it, and that day
asked for this correction to go on every surface the original went out on.

**What happens now.** The original stays up, on the forum and here. This correction
sits beside it. The retraction is recorded in [docs/RETRACTED.json](docs/RETRACTED.json)
as A236, where `test_r1_retracted.py` fails the build if the retracted wording
reappears anywhere in the tree without this id within ten lines of it. The index of
everything this project has got wrong and said so is
[docs/CORRECTIONS.md](docs/CORRECTIONS.md).

**Why it is done this way.** Covenant records its own errors rather than editing them
away, because a system that governs whoever runs it has to survive being checked, and
that only works if correction is welcome. If you find another, say so.
