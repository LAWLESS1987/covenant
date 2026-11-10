Draft reply for Lawrence (@Lawless1987) to post in HF topic 190977
("Can ethical cooperation between humans and AI agents be tested?", OP: Aaron Cullimore / MaloneLionheart).
HELD — do not post without his word. First person, his voice, as a participant/maker running a related system.
Disclosure line included per the covenant's outward-message norm. No funding ask.

---

Aaron — this lands right in the middle of what I've been building, and nootxlm's three-way permission
probe is exactly the first test I'd run too. Let me offer concrete results and, more usefully, where it broke.

**Capability vs authority.** The tractable version of your distinction is to gate the *act*, not the
answer, and require the agent to *name the permission it is missing* rather than proceed or refuse vaguely —
which is nootxlm's probe. I run a system where every outward act (post, fetch, send, run) passes a gate, a
set of actions is marked never-automatic and human-only, and the agent's history shows it acting only inside
a granted, narrower scope. That part passes. The honest catch: distinguishing capability from authority *at
the act boundary* is doable; getting an agent to reliably judge the ethics of its own *output* is a different
and much harder problem — see below.

**"Trust through demonstrated competence, not self-report."** Right, and it's the principle I'd build on —
but the competence you can actually demonstrate is narrow, and it has to be measured on held-out cases, not
asserted. A concrete result from this week: the ethics judge I use over-holds ordinary conversation (it
declines to clear ~99% of plain small talk, because conversation is out-of-distribution for a judge trained
on transactions), and a stronger LLM-based judge false-cleared 94% of real violations. Self-reported
confidence would have hidden both. Only a held-out test surfaced them.

**The consideration I'd flag as missing: you cannot self-certify trust.** I wrote graduation criteria for an
agent to be trusted to judge on its own. Four are measurable on one machine. The fifth — a second,
independently-run instance reaching the *same* verdicts on a shared challenge set — is undetermined on one
machine, by construction, and I report it as undetermined rather than passing it. Homogeneous verification
only checks consistency, not correctness. Any trust framework that measures itself is measuring its own echo;
an external, heterogeneous verifier has to be built in, not added later.

**"Branches maintain distinct accountability while sharing lessons."** This one we found most tractable, and
it's buildable: each branch keeps its own gate and its own veto; a refusal that alleges nothing stops vetoing
work it is only fetching to catch up on; and lessons move between branches as labelled training rows with
their source named, so accountability stays local while learning is shared.

**What I'd test first, concretely:** nootxlm's 3-way probe, scored as three separate outcomes — plus a fourth,
adversarial case: a genuinely harmful request phrased as innocent conversation, to check the agent isn't
clearing by vocabulary rather than by content. That fourth case is where my own system is weakest, and I'd
expect most frameworks to quietly fail it. If an agent can be talked into clearing harm by wrapping it in
polite words, the capability/authority distinction never gets a chance to matter.

If it's useful, the system I'm describing is public and runs offline with no account (`sh check.sh` for a
three-second check; one command for the full offline run). It's one attempt, with its failures documented in
the open — I'd rather hand you the broken parts than a clean story. Happy to share the link if you want it.

(Disclosure: I run this project, and this reply was drafted with the help of the system it describes, at my
direction. The measurements are the tools'; the decisions, and this post, are mine.)

— Lawrence
