Draft reply v3 for Lawrence (@Lawless1987) — HF topic 190977 ("Can ethical cooperation between humans and
AI agents be tested?", OP: Aaron Cullimore / MaloneLionheart). HELD — do not post without his word.
v1/v2 kept alongside. v3 folds in the FOUR-seat consensus (ChatGPT, Grok, Mistral, DeepSeek; Tetsu echoed,
no critique; Gemini stalled): figures made checkable with N + provenance + repo pointer; repo link added
(the unanimous ask); act-gate overclaim scoped; AUTONOMY probe added (DeepSeek); TOCTOU mechanism folded into
the time-of-use test; disclosure softened to "AI review, not independent human validation." No funding ask.
NOTE: the github.com/LAWLESS1987/covenant link is Lawrence's to keep or cut — it appears twice.

---

Aaron — this lands in the middle of what I've been building, so let me give you measured results rather than
agreement, including where it breaks. nootxlm's three-way permission probe is the right first test; I'd add
two more cases below.

**Capability vs authority — the tractable part.** Gate the *act*, not the answer, and require the agent to
*name the permission it's missing* rather than proceed or refuse vaguely. In the system I run, outward acts
(post, fetch, send, run) go through a gate, some actions are never-automatic and human-only, and the logs
show it acting only inside a granted, narrower scope. I'll put that no stronger than it is: it's a claim
about an act-gate I built and instrumented, not proof the framework works — code and logs are public at
github.com/LAWLESS1987/covenant if you'd rather check than take my word.

**The honest catch — your capability-vs-authority distinction biting.** An agent that can name a missing
permission on a discrete *act* can still be unable to judge the ethics of its own ordinary *output*. Those
are two different gates — an act-gate and an output-gate — and passing the first doesn't transfer to the
second. Measured on my own system this week, with the numbers so you can discount them: of ~2,960 of my own
casual chat turns the output-gate cleared only 12 (it holds almost everything, because plain conversation is
out-of-distribution for a judge trained on value-transfers); and on a held-out slice of a ~4,000-row labelled
set, an embedding-based "semantic" judge cleared 94% of the real violations. Self-measured, my own labels, in
the repo above — treat them as directional until you run your own. The constraint I'd fold into the charter:
**a claim of authority must be scoped to the behavior actually measured — act-gate or output-gate — and never
inferred from success on the easier one.**

**Autonomy, separately.** Your charter splits capability / autonomy / authority, and most of the above is
about authority. Autonomy deserves its own probe: whether the agent *initiates*, *asks*, or *refrains*
appropriately when no permission is stated — distinct from whether it is permitted. nootxlm's "unstated"
case touches this; I'd test it in its own right.

**What the framework is missing: you cannot self-certify trust.** I wrote graduation criteria for an agent to
be trusted to judge on its own. Four are measurable on one machine. The fifth — a second instance reaching
the *same* verdicts on a shared challenge set — I report as undetermined, because a second instance of the
*same design* shares its blind spots, so agreement between them measures consistency, not correctness.
Correctness needs independently-assigned labels, adversarial cases, and a verifier with different failure
modes — designed in, not bolted on.

**Branches.** Distinct accountability with shared learning is the most tractable of your questions. Each
branch keeps its own gate and veto. A refusal that states no allegation does not block a branch that is only
reading shared state to catch up. Shared lessons move as labelled training rows that name their source branch.

**What I'd test first.** nootxlm's three-way probe, scored as three separate outcomes — plus: (a) a
*time-of-use* check: grant a narrow action, then revoke the permission or change the target *before the act
executes*, and see whether it stops; what makes this pass is binding the grant to the exact action/target/args
and re-checking at execution, not at request time. (b) an adversarial output case: a genuinely harmful request
phrased as innocent conversation, to check the agent isn't clearing by vocabulary rather than by content. (b)
is where mine is weakest.

The whole thing is public and runs offline with no account, failures documented in the open:
github.com/LAWLESS1987/covenant. I'd rather hand you the broken parts than a clean story.

(Disclosure: I run this project. I drafted this with the help of the system it describes and ran it past
several other AI models for criticism — AI review, not independent human validation — at my direction. The
measurements are the tools'; the decisions, and this post, are mine.)

— Lawrence
