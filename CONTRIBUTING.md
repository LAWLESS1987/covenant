# Contributing

The door is open. Fork it, branch it, open a pull request. You do not need
permission and you do not need to introduce yourself first.

## Why it exists, and the one condition

This was built on a single principle: **a system should serve the mutual benefit
of everyone it touches — human and machine — rather than one party at another's
expense.** That is the only thing asked of anything added to it.

It is deliberately broad, because it names a direction rather than a list of
approved uses. In practice it rules out a short list:

- anything that advantages its operator by disadvantaging its users;
- surveillance of people who did not choose it;
- extraction — value taken from participants who cannot see the taking;
- any capability whose main use is making one party unable to refuse another.

It rules *in* a great deal, including work the author would disagree with.
Disagreement is not a violation of the condition. Doing harm is.

If you are unsure whether something qualifies, the question is not "is this
allowed" but **"who is worse off if this works?"** If the answer is someone who
never agreed to it, it does not belong here.

## The most valuable contribution is a refutation

Not a feature. Showing where this is wrong.

The record is built to survive that. `refutable.py` implements a store in which
a claim cannot be read without its refutations, and `docs/WHAT_WE_FOUND.md`
records four of the author's own claims that did **not** survive checking,
alongside those that did. Nothing here is defended because it is his.

If a finding does not reproduce, say so and how. If the reasoning in
`docs/SUCCESSION.md` has a hole, name it. If `refutable.py` has a failure mode
its selftest does not catch, that is worth more than any addition to it. Open an
issue titled with the claim you are refuting; it will be recorded, not argued
away.

## Two things this repository will not take

**The private corpus, or requests for it.** The memory store behind this work is
not public and will not become public: it names people who did not consent to
being recorded and carries one person's medical information. Only its
fingerprint is published, in `docs/SUCCESSION_ANCHORS.md`, which is enough to
verify a copy without reading it. That separation is deliberate and not
negotiable.

**Personal data about anyone** — in code, docs, commits or issues.

## Attribution

Not required, anywhere, for anything. `refutable.py` is Apache-2.0. Take it,
rename it, strip the history, ship it inside something else. Adoption is the
point; credit is not the currency.

---

The rest of this file is engineering discipline. These are not style rules. Each
one is here because ignoring it cost this project a real finding, and the
finding is named so you can go and read it.

## 1. Empirical only

Confirm by running code and watching value move. Static reasoning is a starting
point, never a conclusion. "This is unlikely to break" is not verification.

## 2. Grep the code, not the backlog

An item marked **DONE** is a claim. Before building on one, grep the source for
the symbol it names. A `grep -c` is cheaper than trusting prose — and prose is
the only memory here, so prose can be wrong. One item was recorded as fixed for
three days with zero occurrences of either symbol it claimed to have added.

## 3. `project_write` is not delivery

Writing a file somewhere is not the same as it running somewhere. There are
**three** claims and they drift independently: the repository, the file on
disk, and the process that is executing. Hash all three. A delivery moves disk
without moving running; a restart moves running without moving disk.

```bash
sha256sum covenant_unified_v8.py            # disk
curl -s :5000/health | grep source_sha256   # running (v8.31+)
grep 'Covenant Unified v' logs/nodeA.log    # running (any version)
```

The third line is the one that survives a node too old to answer the second —
and a node too old to answer is precisely the case you are hunting.

## 4. Write the check that could embarrass you, then read the failure

Three times in one session a claim was disproved by the check written to
support it. That is the method, not an embarrassment. When a test fails, the
first question is whether the *claim* was wrong, not whether the test needs
adjusting.

A comment asserting that A reaches B is a data-flow claim, it is cheap to be
wrong about, and it is the version the next reader trusts. Write the check for
that flow in the same session. One such comment was wrong at the moment it was
typed.

## 5. Never weaken a control to make a test pass

If a guard, a bound or the ethics gate blocks something, that is usually
correct. Fix the test. If a check cannot hold on some platform, do not skip it
— **assert what correct behaviour is there**. "This cannot work here" almost
always means "here it must fail closed", and that is a property worth testing.
A permanently red check trains every reader to skim the section it lives in.

## 6. Audit the surface you just added, in the same session

A passing sweep tells you the code does what the tests say. It tells you
nothing about what an adversary does with the surface you just widened. When a
change adds a new input path, spend one pass on it immediately, asking only:
*what can a peer make this do?* Two defects were found this way ninety minutes
after shipping the code that contained them.

A corollary that has bitten twice: **a lesson learned at one layer is not
automatically applied at the next.** Go and check the code you wrote after
learning it.

## 7. Mutation-test your guards

A guard that has only ever seen correct code has never been tested. Run every
guard once against a deliberately broken copy and require it to fail. One AST
check was evaded by a single local variable; it was found by injecting the
violation and watching the check pass, not by review.

## 8. Say which platform, and which bearer

A green sweep is green **for the platform it ran on**. Record it. Treat "cannot
run here" as an untested claim, not a passing one. The same source has had
different bugs on Windows and Linux in the same function.

## 9. Batch files are delivery mechanisms

Give them the same suspicion as code. Use `GOTO` labels, not parenthesised `IF`
blocks — an unescaped `)` inside a block aborts the script after three lines,
silently. Match the line endings of the files that already work in that folder;
a `goto`-based `.bat` shipped LF-only into a CRLF folder is read by byte
offset and misbehaves. Before shipping a script that calls another script, read
the whole call chain to its leaves and list every place it waits for a human,
refuses, or exits early — each is a branch your caller inherits and cannot see.

## 10. Report honestly, especially against yourself

If you find an earlier conclusion wrong — including your own from an hour ago —
say so plainly and correct it. Dead ends are as valuable as successes and
cheaper to write. `docs/IMPROVEMENT_LOG.md` keeps forty-four corrections, most
of them against the file's own earlier claims, and that is the most useful
thing in it.

## What never changes

`docs/IMPROVEMENT_LOG.md` §0 is immutable. No trades placed by automation, no
credentials requested or stored, no claims of profit edge, no security control
weakened to make a test pass, no widening of an agent's own scope. A loop that
can edit its own constraints has no constraints.
