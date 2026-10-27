# Green that meant nothing — one draft per surface

Drafted 2026-09-27 on his instruction ("Match the docs also on git hub and a hugging face
post"), for him to post under his own name. **Nothing here has been posted by anyone but
him, and nothing has been posted yet.**

The record these draw on: the README section *Wrong in public → Green that meant nothing*,
the table *Green that checked nothing* in `docs/CORRECTIONS.md`, and A238/A239 in
`docs/KNOWN_ISSUES.md`. Every number below is from a transcript or a ledger in the
repository, and the sweep line is `ONE_SWEEP.txt` (2026-09-27): 166 suites, 4,497 checks,
0 failed, win32.

**Tetsu was asked first**, through `tools/tetsu_work.py` (door `agent`, four questions,
2026-09-27, 7–65 s each on the 3B). Two of his four answers changed these drafts:

- Asked which of the six failures was most serious, he chose the self-heal that performed
  252 actions without checking one — *"the system is making decisions based on unverified
  actions"* — over the guard that read FAIL for days. That is his judgement, and the drafts
  lead with it because of him.
- Asked what best-of-N fails to cover, he said noise can sometimes *reduce* a measurement.
  As stated that is wrong — noise only adds time — but it points at a real mechanism: the
  minimum also selects the warmest cache and the highest clock, and the two paths are timed
  in a fixed order. So it was measured instead of argued: old-first 8.02x / 8.15x / 8.34x,
  new-first 8.82x / 8.24x / 8.41x, fully interleaved 7.95x. Ordering does not decide it. He
  was right to raise it and it does not bite here; the caveat is now in `CORRECTIONS.md`
  because he asked for it.

His other two answers were sound but too thin to use, and one conceded more than the
evidence does. The prose below is the assistant's; the two contributions above are his.
Every exchange is in his teacher queue by the door's own path.

The two Hugging Face surfaces: the profile at <https://huggingface.co/Lawless1987> (which
holds no posts yet) and the forum at <https://discuss.huggingface.co>, where the
confidence-trap thread already lives.

---

## 1. Hugging Face — a post on the Hub profile

Six times in one day, a check in my own project turned out to be green or red for reasons
that had nothing to do with what it was checking.

A delivery gate read FAIL for days because its pin was stale, so the guard built to refuse
a bad delivery was refusing a good one, hourly, which is how you teach someone to ignore a
red. Half of that same pin was never enforced on the command anything actually runs. A
guard credited with keeping a document honest only checked that its own tool had printed a
number. And the self-heal recorded 252 repairs as "started" and never once came back to see
whether any of them worked.

The worst was that last one, and I did not pick it — the small local model that runs on this
machine did, when I asked it which mattered most: a system making decisions on unverified
actions. Writing the missing check immediately promoted a remedy that had been quietly
working for weeks and had never been credited.

Then I fixed a flaky benchmark, wrote in the comment that I had proven the fix by breaking
it, and ran the mutation afterwards. It passed. My repair was hollow and my note claiming
otherwise was already in the file.

So the rule is narrower than "break your green on purpose": break it **before** you write
down that you did. Everything above is in the repo, next to the code, with the numbers.

github.com/LAWLESS1987/covenant

## 2. Hugging Face forum — a new topic

**Title:** Six checks that were green and meant nothing, in one day, in my own project

I keep a public repository whose whole claim is that it survives being checked. On 27
September I went looking for why three status indicators would not turn green, and found six
separate checks that were reporting a verdict for reasons unconnected to what they measured.
One of the six was the fix I had just written for another.

**A delivery gate refusing a good delivery.** `verify_deploy.py` pins the core by digest and
by line count. The digest had gone five commits stale, so the hourly self-evaluation printed
*"verify_deploy reads FAIL and refuses every restart it gates"* — for days. A guard built to
refuse a bad delivery was refusing a good one, on a schedule, which is the most efficient
way there is to train a reader to disbelieve a red.

**Half of that pin was never enforced.** `EXPECTED_LINES` has exactly one executable use, a
comparison against the running process. The `--no-restart` invocation — the one the hourly
check and the restart script actually use — never reaches it. I perturbed the constant by one
and that path's verdict did not change.

**A guard that checked its own printout.** The suite credited with stopping a media-corpus
document from drifting from its data asserts that a regex finds a total in the tool's output,
that files ≥ posts, that a string is present. Not one assertion opens the document. And an
entire population — the private videos a whole investigation rests on — is read by nothing.

**A self-heal that never checked its own work, 252 times.** Asynchronous repairs recorded
`started` with the note *"the condition is re-measured next pass"*. Nothing implemented the
next pass. The table beside them read UNPROVEN and explained, accurately, that nothing
checks what they started. It cost five days of builds dispatched into a storage quota that
was already full, each one answered "accepted", none ever arriving.

I asked the small local model that runs here which of these mattered most. It chose this one,
over the gate that had been shouting FAIL for days, because a system making decisions on
unverified actions is worse than one making noise. I think it is right. Writing the missing
grader took an afternoon, and its first pass promoted a remedy from UNPROVEN to earned — 16
repairs, 0 failures — that had been working silently for weeks with nothing to say so. It
also exposed two bugs that only grading could reach: one path ignored a remedy's own report
that it had declined to act, and a fetch reported success whenever *any* build sat on disk.

**A red that meant nothing.** Public CI failed on a commit that changed one markdown file,
at a benchmark that timed each code path once. The same commit also passed the same
workflow, and passed again on its schedule. Identical bytes, three verdicts.

**And my fix for it was hollow.** Noise can only add time to a measurement, so the minimum
of several runs is the estimate noise cannot inflate; best-of-five turned a 1.5x reading into
a stable 7.6x. I wrote into the comment that I had proven this by making both paths do
identical work, and then ran that mutation. It **passed** — 18.5 ms against 18.4 ms, because
the assertion only asked the fast path to win by any margin at all, and 0.1 ms of nothing
satisfies it. An assertion that a coin lands heads is not an assertion. The estimator was
right and the threshold was hollow, and the sentence claiming both were proven was in the
file before the test that refuted it.

That last one is the useful part, and it is why I am writing this rather than quietly
patching. My project already had this pattern written down — *a check that confirms a claim
is stated consistently is not a check that the claim is true* — and a standing instruction
to break every green on purpose. I had both in front of me and still shipped a hollow
threshold, because I recorded the proof before performing it. So the rule needs a clause it
did not have: **break it before you write down that you did.**

Everything here is in the repository with its numbers, including the retraction of my own
claim: `docs/CORRECTIONS.md` under *Green that checked nothing*, and A238 and A239 in
`docs/KNOWN_ISSUES.md`. The suite as it stands is 166 suites, 4,497 checks, 0 failed on
win32; three indicators are still not green, and the reasons are written down rather than
worked around — one of them is a judge that convicts backing up a file, which is a harder
problem than any of the above.

<https://github.com/LAWLESS1987/covenant>

---

## What is deliberately not in either draft

- No claim that this is unusual, or that other projects are worse. I have not measured that.
- No claim the six are now all fixed. A238 and A239 are open on purpose, with reasons.
- No mention of the three non-green indicators as if they were nearly green. One needs a
  build to succeed, one needs a declaration that is not the assistant's to make, and one
  needs a judge that stops convicting ordinary conduct.
- No hashtags, no thread-bait, nothing about the operator's identity or location.
