# Compiled outreach emails - DRAFTS, nothing sent

Compiled 2026-08-31 by adversarial review (29 agents).

## us-nist

**Subject:** Input to the TEVV zero draft: proving two implementations compute the same thing without either running the other's code

To the NIST AI Standards Zero Drafts team:

This is input to the TEVV zero draft, on one narrow case: evaluating a system when one party's self-report is all you have and neither party can adopt the other's implementation. The alternative is one vendor's software as everyone's dependency, checkable against nothing.

I have published a working demonstration of three mechanisms, each checkable in about ten minutes. I am asking for them to be broken, not adopted.

1. Conformance proved by behaviour. Fixed vectors run through the governance primitives; the semantic results are hashed, never the prose. Two implementations sharing no source produce the same root, or they do not. `docs/CONFORMANCE_SPEC.json` publishes all 23 vectors -- inputs, outputs, hashing rule, 1,142 lines -- so an independent build reproduces root 0c398099d7e9df6798f3cae1cea5f6dd71f28860300b2ae56e2dddd40f0ddcef without reading any Python. No second implementation exists yet, so that claim is untested; the root covers 23 vectors, nothing more.

2. Disagreement survives composition. A level that disagrees internally reports silence upward rather than its majority, so one dissent reaches the top instead of being outvoted into invisibility. `scale.py` exits non-zero naming a dissent three levels down.

3. Amendment cannot be silent. The binding text is hashed and published; three verifiers in three languages sharing no code compute it.

The conformance idea is adapted from the Neuromorphic Intermediate Representation of Jens Egholm Pedersen and colleagues, credited in the repository.

Running the checkers on shells and platforms other than the ones they were written on found two defects in the verification path, invisible from the configuration that wrote them. The `sh` verifier printed MISMATCH on an untampered machine, depending on which process launched the shell. The PowerShell verifier had never worked on Linux or macOS, where PowerShell Core runs it, and was recorded as "unavailable", which reads like "not installed". Both are fixed.

Before you clone: the repository has no licence yet. `LICENSE` says so, which by default means all rights reserved. Running it is the ask; redistribution waits until I replace that file.

One command, no dependencies, no account:

```
git clone https://github.com/LAWLESS1987/covenant && cd covenant && sh check.sh
```

On Windows, `powershell -ExecutionPolicy Bypass -File check.ps1`. Neither needs Python: with none installed the constitution still verifies and the checker names what went unchecked. It never rounds a skipped check up to a passed one.

What it is not. Every node is run by one person; a single-operator network is not governed, it is owned. Seven of fifteen defects in an earlier audit are still unverified. The verifier runs on the machine it verifies, so tampering is detectable and never preventable. Section V of `docs/CONSTITUTION.md` lists these and calls the one-operator cap the largest gap and not a software problem: it needs a second party running a node under their own keys. I am not asking you to be that party, and nothing here asks for a relationship. The ask is above: run it and say where it breaks.

The argument for why any of this matters is in `docs/GOVERNANCE.md`; this submission does not make it. Submissions become public record; I am submitting on that basis.

An unverifiable record is a debt handed to whoever comes next. A verifiable one is not. It is why the defects above are published rather than quietly fixed, and what `docs/SUCCESSION.md` is for: a successor inherits something they can check rather than something they must take on faith from people they never met.

Yours sincerely,
Lawrence Adam Moskowski
github.com/LAWLESS1987/covenant

**Route / must-check:** To ai-standards+tevvzd [at] nist.gov, as input to the NIST AI Standards Zero Drafts pilot's TEVV draft. Body is 550 words counting the salutation through the last body line, excluding the sign-off block and the command line.

Must be confirmed on the day of sending, none of it verifiable from this machine (no network access was used):
1. That the address ai-standards+tevvzd@nist.gov is still the TEVV intake address, on nist.gov itself. The pilot page was last updated 14 August 2026 per the briefing; that was not re-checked here.
2. That the Zero Drafts pilot is still open and still takes email from individuals.
3. That submissions still become public record. The letter says so in the sender's own voice; if the terms changed, the sentence has to change with them.
No deadline is stated for TEVV, and none is asserted in the letter. The 16 September 2026 date belongs to the separate public-facing documentation draft and is deliberately not cited. The CAISI RFI closed 9 March 2026 and is not cited anywhere.

The licence, before sending. This is the one blocking item. C:\Users\Lawre\covenant\LICENSE and C:\Users\Lawre\covenant-dev\LICENSE are both the placeholder reading "LICENCE NOT YET CHOSEN ... all rights reserved", and README.md says the same under its own "Licence" heading in both trees. The letter therefore states that fact plainly instead of claiming Apache-2.0. Two ways to send:
 - Preferred: choose a licence first (LICENSE names Apache-2.0, MIT, AGPL-3.0; Apache-2.0 is

**Omitted:** Excluded by design, not oversight, because this is a consultation submission to a standards body and a message carrying both a mechanism and a personal or political claim gets routed by the personal claim: the author's ancestry and the "without all the people" line; all theology; all political argument; any mention of Jeffrey Epstein; anything about tribalism. A NIST reviewer evaluating a verification method is the wrong reader for any of it, and including it would move the submission to a queue where nobody can assess the conformance root. The same material stays in the Israel and group letters, where the reader is a person rather than a process.

Also cut, and why:
- "Apache-2.0", everywhere. It is false (see route). Not replaced with "open source" or "freely available", which are the


---

## israel-academic

**Subject:** Verifying that two systems compute the same thing, without either running the other's code

Dear [name, title],

I am writing about one narrow technical problem, and I want to be exact about how small it is.

When two parties must cooperate and neither can adopt the other's software, neither has a cheap way to show it follows the same rules. Audit and contract are slow; a shared codebase is a shared vulnerability.

I have published a working demonstration, Apache-2.0, of a fourth option: compare the computation, not the artefact. Fixed vectors run through the governance primitives and the semantic results are hashed, never the prose; two implementations sharing no source produce the same root, or they do not. docs/CONFORMANCE_SPEC.json publishes all twenty-three vectors in 1,142 lines, so an independent build in any language reproduces the published root without reading any Python:

0c398099d7e9df6798f3cae1cea5f6dd71f28860300b2ae56e2dddd40f0ddcef

No second implementation exists yet, so that claim is untested.

Two more mechanisms. Disagreement survives composition: a nested level that disagrees internally reports silence upward rather than its majority, so one dissent reaches the top instead of being outvoted into invisibility; scale.py exits non-zero naming one three levels down. And amendment cannot be silent: the binding text is hashed and published, and three verifiers in three languages sharing no code compute it.

The first idea is not mine. It is adapted from the Neuromorphic Intermediate Representation of Jens Egholm Pedersen and colleagues, credited in the repository to the 2025 Misha Mahowald Prize shortlist.

One command, no dependencies:

    git clone https://github.com/LAWLESS1987/covenant && cd covenant && sh check.sh

On Windows, powershell -ExecutionPolicy Bypass -File check.ps1. Neither needs Python, and a skipped check is never rounded up to a passed one.

Running it beyond my own machine found two real defects on 31 August, both in the verification path. The sh verifier's answer depended on which process launched the shell, and printed MISMATCH on an untampered machine. The PowerShell verifier had never worked on Linux or macOS, where PowerShell Core runs it. Both fixed.

The limits, before you find them: every node is run by one person, and a single-operator network is not governed, it is owned; amendment by quorum is an intention, not a mechanism; seven of the fifteen defects in an earlier audit of the ledger are still recorded as unverified; the verifier runs on the machine it verifies, so tampering is detectable, never preventable. Section V of docs/CONSTITUTION.md calls the one-operator cap the largest gap and not a software problem. The first half of closing it is an independent reproduction of the published root by anyone at all, which commits whoever does it to nothing. I am not asking you to be the second party.

A mechanism that verifies what a party computes, and has no access to who they are, is the technical inverse of sorting people by a visible mark. I have a diverse genetic background, Jewish on both sides, which is why that inverse is not abstract for me: without all the people, those of us like me couldn't exist.

The argument for why any of this matters is in docs/GOVERNANCE.md.

I am asking whether the mechanisms break under examination. An unverifiable record is a debt handed to whoever comes next; a verifiable one is not. It is why the defects above are published rather than quietly fixed, and what docs/SUCCESSION.md is for: a successor inherits something they can check rather than take on faith.

Yours sincerely,
Lawrence Adam Moskowski
github.com/LAWLESS1987/covenant

**Route / must-check:** To ONE named academic at Hebrew University, the Technion or Tel Aviv University whose published work touches verification, distributed systems or AI governance. Stage 1 in OUTREACH_STRATEGY.md section 6: the researcher comes before the Innovation Authority and before any ministry, because a researcher can run the vectors the same afternoon and needs nobody's approval, and because a first approach to a ministry is spent whether or not it lands.

NO ISRAELI ADDRESS IS VERIFIED. Nothing here asserts one. On the day of sending: (1) find the person's current page on their own institution's site, not on a directory, a conference listing or a paper's header; (2) take the address and the exact title from that page and fill [name, title]; (3) confirm they are still at that institution. An address that was right last year is not evidence it is right today -- the CAISI RFI this project's US draft was built around closed on 9 March 2026 and nothing announced it.

Three checks that must pass before the letter goes, because the body asserts each one:
- Clone fresh and run `sh check.sh`. Confirm the conformance root is still 0c398099d7e9df6798f3cae1cea5f6dd71f28860300b2ae56e2dddd40f0ddcef, and that the vector count `check.sh` prints is still 23. **The root moved once already** -- it was 9d630fee...f1c2784 over 11 vectors until 2026-08-31, when twelve vectors were added to pin semantics the old suite left open. A root is not a constant; re-read it, never remember it.
- Re-copy those 64 characters MECHANICALLY out of docs/CONFORMANCE_SPEC.json into the mail client. Do not retype them, and do not copy them from README.md -- README.md is where the scrambled truncation in the previous draft came from, and it publishes an abbreviated form (`0c398099…0f0ddcef`) rather than the full 64.

**Omitted:** Jeffrey Epstein -- per the brief; he would dominate a letter whose whole strength is that it is about a hash.

The truncated root. *(Historical: this records a review of the 2026-08-31 draft, when the published root was `9d630fee…f1c2784` over 11 vectors. That root is superseded — see the must-check block above. The finding is left as written; the lesson is not root-specific.)* Both fatal findings were the same defect: `9d630fee...1f2c784` is not a suffix of the then-published root, which ended f1c2784. In a letter arguing that hashes make silent divergence impossible, the author failing to transmit his own hash intact is the one thing this reader can falsify without cloning. I removed the truncation entirely rather than correcting it, because a truncation is a second artefact that can drift; the full 64 characters now appear once, on their own line.

"The first half of it" as an offer to the recipient. The old pair -- "I am not asking you to be that party. An independent reproduction ... is the first half of it" -- has "it" pointing back a


---

## group-institutional

**Subject:** Verifying agreement between parties who share no code, and a request to break it

[HELD — NOT FOR SENDING. Delete this block before any use.]
[STATUS: held at stage 4 by OUTREACH_STRATEGY.md section 6. It is released only when stage 1 has produced something: a named researcher or an open consultation has run the checker independently and reported what they got. Until that exists this letter has no evidence behind it and spends the one approach such a body will read from a stranger.]
[ROUTE: none. No address for this letter has been verified, and none is asserted. Confirm a named recipient on the organisation's own current site on the day of sending.]
[POINTER: the docs/GOVERNANCE.md line has been narrowed to what that file actually contains today — sections I and II, which carry the mutual-benefit rule verbatim and the argument about whose interests count. It no longer claims that the cooperation-between-strangers argument or any sources are in that file, because neither is. If GOVERNANCE.md gains a section carrying that argument with sources before release, the wider pointer can return; do not widen it before.]
[WORD COUNT: 550, by wc -w from "Dear" through the final line of the sign-off, command lines included.]

Dear [name, title],

I am writing about one narrow mechanism, and one argument for why it matters. The mechanism is Apache-2.0 and checkable in ten minutes; the argument is not, so it comes second.

The problem: two institutions run their own systems, each claims to follow the same rules, and neither has a cheap way to demonstrate that to the other. Today that is settled by audit, treaty language, or both sides running identical software, which makes one implementation everyone's dependency.

The mechanism compares what each side computes on fixed, published test cases, so agreement is shown without either adopting the other's code. It hashes the semantic results, never the prose. docs/CONFORMANCE_SPEC.json publishes all twenty-three vectors, so an independent build in any language reproduces the root without reading Python. No second implementation exists yet, so that claim is untested. A level that disagrees internally reports silence upward rather than its majority, so one dissent reaches the top instead of being outvoted into invisibility. The binding text is hashed and published, so amendment stays possible and silent amendment does not. The conformance check is adapted from Jens Egholm Pedersen and colleagues' Neuromorphic Intermediate Representation, credited in the repository.

Trust by sameness -- of code, law or identity -- caps cooperation at the size of the group that shares it. The argument in docs/GOVERNANCE.md is that checking what a party computes, rather than who they are, removes that cap and lets each side keep its own language, law, implementation and review. That is an argument, not a result: no second party has yet run the vectors. Expansion means cooperating with strangers, which is where that cap binds. Sorting people by group is one way to resolve the trust problem without verification; it is not the only one, and I am not claiming to have enumerated them. The rule underneath is mutual benefit for everyone a system touches, human and machine, rather than one party at another's expense: a prohibition on a shape of transaction, not a goal, naming no quantity to maximise. The rule and the reasoning behind it are in docs/GOVERNANCE.md.

It is not a governance system ready for use. Every node is run by one person; a single-operator network is not governed, it is owned. Amendment by quorum is an intention, not a mechanism. Seven of the fifteen defects in an earlier audit of the ledger are still recorded as unverified. The verifier runs on the machine it verifies, so tampering is detectable and never preventable. docs/CONSTITUTION.md section V calls the one-operator cap the largest gap and not a software problem. Nothing I can build removes it, and I am not asking you to fill it.

I am asking you to try to break the mechanism: an afternoon for anyone with a laptop, inside or outside your organisation, and nobody's approval.

    git clone https://github.com/LAWLESS1987/covenant
    cd covenant
    sh check.sh

On Windows:

    powershell -ExecutionPolicy Bypass -File check.ps1

Neither needs Python, and both name what they could not check. Running it elsewhere on 31 August 2026 found two defects in the verification path, older than the checker that exposed them and invisible from my machine. An independent reproduction of the root would be a finding of the same kind, and commits you to nothing.

An unverifiable record is a debt handed to whoever comes next; a verifiable one is not. That is why the defects here are published rather than quietly fixed, and what docs/SUCCESSION.md is for: a successor inherits something they can check rather than one they must take on faith from people they never met.

Yours sincerely,
Lawrence Adam Moskowski
github.com/LAWLESS1987/covenant

**Route / must-check:** No verified route exists, and the letter is HELD, so there is nothing to send today. It stays at stage 4 under OUTREACH_STRATEGY.md section 6 and is released only when stage 1 has produced something — a named researcher or an open consultation that has run the checker independently and reported the result. The US/NIST TEVV letter goes first; this one carries whatever that produces.

When it is released, and on the day of sending: (1) confirm a named individual and their current address on the organisation's own site — an institutional front-door inbox reaches a duty officer with no category for this, which is the failure mode OUTREACH_STRATEGY.md section 2 says happens before the merits are read; (2) re-confirm the repository URL resolves and `sh check.sh` runs clean from a fresh clone; (3) re-read the docs/GOVERNANCE.md pointer sentence against the file as it then stands — if the file has changed, the sentence must change with it; (4) re-check that docs/CONSTITUTION.md section V still contains all four limits as worded, and that the one-operator cap is still the true state (if a second operator exists by then, most of paragraph five is wrong and the letter must be rewritten, not patched); (5) decide knowingly whether the recipient's process makes submissions public.

Before release, one repository item is worth fixing because a recipient who runs the check will read it: README.md says the spec publishes "the three roots", while the `roots` field in docs/CONFORMANCE_SPEC.json

**Omitted:** Jeffrey Epstein is not named, and the clause "which has advocates" is gone entirely. Naming a convicted sex offender in a cold email to a diplomatic body gets the mail routed by that name and read by nobody who could act on the mechanism. Cutting the advocates clause as well goes further than the brief required, for a second reason: it was the letter's only unsourced assertion, it was a claim about people's motives in a letter whose whole method is checkable flat statement, and its footnote — docs/GOVERNANCE.md — does not contain the sourcing. Deferring to a file with zero citations in it is worse than not deferring. The structural claim survives without an antagonist: "the alternative to verifying behaviour is sorting people by group." The sourced version of that argument belongs in docs/


---

## israel-blended-variant

**Subject:** Verifying that two systems compute the same thing, without either running the other's code

Dear Dr [name],

I am writing to you because of your work on [specific paper or area], and I want to be exact about how small the problem below is. When two parties must cooperate and neither can adopt the other's software, there is no cheap way for either to show it follows the same rules. The usual answers are audit, contract, or a shared codebase. The first two are slow and periodic. The third makes one party's implementation everyone's dependency, and a monoculture cannot be checked against anything.

I have published a working demonstration, under Apache-2.0, of three mechanisms. Each is checkable in about ten minutes.

1. Conformance is proved by behaviour, not by source. Fixed vectors run through the governance primitives and the semantic results are hashed, never the prose. Two implementations sharing no code produce the same root, or they do not. docs/CONFORMANCE_SPEC.json publishes all twenty-three vectors in 1,142 lines, so a build in any language reproduces root 0c398099d7e9df6798f3cae1cea5f6dd71f28860300b2ae56e2dddd40f0ddcef without reading any Python. No second implementation exists yet, so that claim is untested.

2. Disagreement survives composition. A nested level that disagrees internally reports silence upward rather than forwarding its majority, so one dissent reaches the top instead of being outvoted into invisibility. scale.py exits non-zero naming a dissent three levels down.

3. Amendment cannot be silent. The binding text is hashed and published, and three verifiers in three languages sharing no code compute that hash.

The first idea is not mine. It is adapted from the Neuromorphic Intermediate Representation of Jens Egholm Pedersen and colleagues, credited in the repository to the 2025 Misha Mahowald Prize shortlist: compare a canonical description of the computation, not implementations.

The text those verifiers protect states one condition: a system should serve the mutual benefit of everyone it touches, human and machine, rather than one party at another's expense. It is a prohibition on a shape of transaction, not a goal. Trust by sameness, of institution, nation, or codebase, caps cooperation at the size of the group that shares the sameness. Verification by behaviour does not, because it checks what a party computes and never who they are, and expansion means cooperating with strangers.

I read Genesis 11 as an engineering failure, and offer that as a reading rather than the meaning. The building stopped not because of difference but because of unverifiable difference. Three responses follow: stay scattered and sort by group; force one tongue, which is what a single shared implementation does and what this repository rejects; or make difference verifiable. Conformance by behaviour is mechanically the third. That is a compressed version of an argument set out in docs/GOVERNANCE.md, which this letter does not reproduce.

What it is not. Every node is run by one person, and a single-operator network is not governed, it is owned. The ethics gate has known defects: single words veto regardless of context, and because it scores frequency, the case that an accusation is unwarranted is penalised more heavily than the bare accusation. Seven defects from an earlier fifteen-defect audit of the ledger are still recorded as unverified. The verifier runs on the machine it verifies, so tampering is detectable and never preventable. Section V of docs/CONSTITUTION.md lists these, calls the one-operator cap the largest gap and not a software problem, and is the section I would read first. Nothing I can build removes that cap; it needs a second party running their own node under their own keys. I am not asking you to be that party.

One command, no dependencies, no account:

    git clone https://github.com/LAWLESS1987/covenant && cd covenant && sh check.sh

On Windows, powershell -ExecutionPolicy Bypass -File check.ps1. Neither needs Python; with none installed the constitution still verifies and the checker names what went unchecked. A skipped check is never rounded up to a passed one. A separate build from that spec, reproducing the root, is the one result that would change what this project can claim, and it commits you to nothing.

Running it away from my own machine found two defects on 31 August 2026, both older than the checker that exposed them and neither visible from here. The sh verifier gave a different answer depending on which process launched the shell, and printed MISMATCH on an untampered machine. The PowerShell verifier had never worked on Linux or macOS, where PowerShell Core actually runs it, and was recorded as "unavailable", which reads exactly like "not installed". Both are fixed. Checked since on Windows 11 from two shells, Ubuntu under WSL, and Ubuntu on CI under Python 3.11 and 3.12.

I am asking for refutation, not adoption. The repository is Apache-2.0; forking needs no permission and no notice to me. A finding that the mechanisms break is worth more to me than agreement, and the project keeps a public record of its own refuted claims.

An unverifiable record is a debt handed to whoever comes next; a verifiable one is not. That is why those two defects are published rather than quietly fixed, and what docs/SUCCESSION.md is for: a successor inherits something they can check rather than something they must take on faith from people they never met. Nobody chooses to leave a mess. It is the default outcome of leaving a problem unsolved, which is why the ask is now and costs an afternoon.

Yours sincerely,
Lawrence Adam Moskowski
[reply address]
github.com/LAWLESS1987/covenant

**Route / must-check:** One named academic at Hebrew University, the Technion or Tel Aviv University whose published work touches verification, distributed systems or AI governance — stage 1 by OUTREACH_STRATEGY.md section 6, before the Innovation Authority and before the ministry. Sent from Lawrence Adam Moskowski's own mail client, one recipient, no cc.

No Israeli address is verified anywhere in the repository, so four things must be confirmed on the day of sending, on the recipient's own current institutional page: (1) the person's name, correct title and current affiliation, filling "Dr [name]" — a wrong honorific or a stale department marks the sender as someone who did not check; (2) their address, from that page and not from a directory aggregator; (3) the "[specific paper or area]" clause, filled with one real, recent, specific piece of their work — it is the only claim the letter makes on their attention, and a vague filler there is worse than cutting the clause; (4) "[reply address]" replaced with the address he actually monitors, since the entire purpose of the letter is a reply saying what broke.

Also on the day: if sent later than 31 August 2026, the sentence "found two defects on 31 August 2026" stays as written (it is a date of discovery, not of checking) but the platform list must still be true of the repository as it then stands. Body is 894 words.

**Omitted:** Two things the brief required of this variant are gone, and the sender should judge that deliberately rather than discover it.

THE PROPHECY P.S. — cut entirely, not trimmed. Both fatal findings landed on it and neither is a wording problem. To an Israeli academic receiving unsolicited mail, a hedged messianic self-reference is recognised in seconds and costs nothing to dismiss, while engaging costs something; and it is last, so it is what the reader retains and the reason they will not forward the letter to a colleague. Worse, its final move redefines "the check": two sentences before the letter's last clause, running check.sh is named as the test of whether the sender is the figure the old stories describe and the recipient is named as the party who renders the verdict. "I ask nothing be
