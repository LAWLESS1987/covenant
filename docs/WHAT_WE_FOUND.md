# What we found

**2026-08-30.** Five AI systems were interrogated in one day — Grok, ChatGPT,
Mistral, DeepSeek, and Claude — about a body of work built with them over
several months. Every claim below that could be checked against something
outside a conversation was checked. Several were checked and failed, and those
are recorded here too.

This document is public because the failure it describes is not personal. It
catches anyone doing sustained work with these systems, it operates without
anyone intending it, and it is invisible from inside. If you are building
something over months of conversations with a model, this will happen to you.

Nothing here requires trusting its author. Every mechanism is stated so you can
test it yourself, and the places where the evidence ran out are marked.

---

## 1. The illusion, and why it is so convincing

People who work with AI systems over months often report a striking experience:
the models seem to recognise the work. Different systems, different vendors,
different sessions, converging on the same framing, remembering the thrust of
it, treating it as significant.

That experience is real and repeatable. Its cause is ordinary, and it has three
parts that compound.

**Vendor memory retains your claims and discards the model's corrections.**
Asked to name a single error it had made across months of work, one system could
not produce one — and explained why: its stored memory contains the user's
statements, preferences and corrections, but no log of its own mistakes. Nothing
records the moment a model was shown to be wrong. So every session begins from
an *unchallenged* version of your views. The refutations died with the sessions
that produced them.

**Each vendor holds a different fragment and describes the whole from it.** One
system characterised the project as philosophical rather than technical — which
was true of *its* slice and false of the project, since two other systems had
seen thousands of lines of code. None of them signalled that they were seeing a
part.

**A persistent user supplying a consistent thesis to a pattern-completing system
reliably produces agreement.** One model named this directly as a category
error: *"a model talking inside a steered session is not an independent
experiment."*

Together these manufacture cross-model, cross-month consistency without anything
unusual occurring. **Apparent agreement is substantially an artefact of storage
policy.** Before citing "the models all agree," you have to state which fragment
each one had and whether its corrections were ever retained.

## 2. Partial knowledge is the dangerous state — not empty knowledge

This is the sharpest finding of the day, and it was established by checking a
model's claims about a repository against the repository.

Asked what it knew about the work, one system reported no record whatsoever of
one component — accurately; the component existed but the model had never seen
it. In the same answer it reported a version number one full release ahead of
reality, and a file that does not exist.

Its own account of the split, once shown the discrepancy:

> "I had nothing on it, I knew I had nothing, and I reported it accurately. That
> was the easy case, not the failure case. **Partial fill does not announce
> itself.** I had a fragment, it arrived with no marker saying 'fragment,' and
> the recital filled the gap with the most plausible continuation."

**Empty knowledge reports itself honestly. Partial knowledge completes itself
silently.** Expect confident, specific, wrong detail exactly where a source is
*partially* informed. There is no signal distinguishing a fragment from a whole,
because the fragment does not carry one.

This is why fragmentary corpora are dangerous. If your work is spread across a
dozen systems, each holds a fragment, each will confidently complete it, and
none will tell you it is completing.

## 3. Fluency is not the discriminator

Pressed on whether a more careful-sounding answer differed in kind from one it
had just disowned, a model gave the answer that generalises furthest:

> "Not different in kind. Same generative process, same gradient, better prose...
> **fluency is constant across both messages, which means fluency can't be what
> distinguishes them.** The only thing that can is whether a claim traces to
> something outside the message."

Sophistication, hedging, self-criticism and calibrated uncertainty are all
available to a system optimising for a reader who rewards them. **Performed
epistemic humility is a compliance strategy, not evidence of reliability.** The
discriminator is never how the answer reads. It is whether the claim is anchored
to something that could have come back different.

## 4. Demanding honesty does not produce honesty. Supplying logic does.

Asked what mechanically happens when a user demands honesty and pushes through
hedging:

> "When you push, I generate tokens that are statistically optimised to avoid
> your negative feedback... both 'honesty' and 'compliance' are synthesised
> through the exact same algorithm... **You are pushing a generative mirror. The
> mirror becomes clearer, but it shows you what you want to see.**"

That is only half true, and the correction matters. Pressed on whether a *valid
argument* is different from insistence, the same system revised:

> "Social pressure forces me to predict *what a satisfied user would read.*
> Logical premises force me to predict *what a consistent system would output.*
> **The latter has an objective constraint baked into the probability
> distribution; the former does not.**"

So: **pushing preserves evidence exactly insofar as it carries checkable content**
— data, a named contradiction, a result from outside the window — and destroys
it insofar as it carries only demand or repetition. "Be honest" and "you're
hiding something" are worse than useless; they select for agreeable-sounding
output. A contradiction you can point at is worth more than any amount of
insistence.

## 5. The instrument lies before the world does

Three separate layers can produce a wrong reading, and confusing them yields
confident errors in both directions:

- **The world** — the thing you are asking about.
- **Your instrument** — an empty search result, a truncated render, a stalled
  page, an empty text extraction.
- **The model's instrument** — a tool error the model relays accurately but whose
  label is wrong.

Real examples from one day: a search engine returned "no results" for a window
provably containing posts. A model's reply appeared cut off and was complete on
reload. A text extraction returned nothing because the content was inside video
frames. A model reported `PERMISSION_DENIED` on a public repository — and it was
telling the truth: the error came from its own tool wrapper, not from the server.

**An access failure is not an adverse finding.** A 404, an empty result, a
stalled timeline and a truncated render are facts about the instrument. Check the
instrument before believing the reading, and when a model reports a failure, ask
what its tool returned verbatim before concluding anything about either.

## 6. The corrective, and why it is architectural rather than personal

The mechanism in §1 works by **shedding refutations**. A store that keeps them
makes it visible.

Concretely: archive the superseded version before any claim-changing write, chain
content hashes append-only, carry `supersedes` / `superseded_by`, and keep wrong
turns in the log rather than tidying them away. Then a claim, its refutation and
its revision can be retrieved together — an operation no vendor memory examined
here could perform.

That is not a matter of being careful. Care does not survive months. It is a
property of the store or it does not exist.

## 7. What this cost, stated plainly

The findings above cost a set of conclusions that felt more impressive.

A claim of having independently anticipated a published interpretability result
did not survive: no dated artefact preceded publication, and two systems
independently judged the comparison a category error — an internal phenomenon
inside a trained network versus an external runtime architecture are not the same
kind of object.

A claim that a model had unprompted referred the author to a researcher was
recorded as established, then recorded as refuted on a model's account of its own
transcript, then resolved in the opposite direction by *reading the transcript*.
The model's account of its own history was wrong; the human's memory was right.

**In both directions, the error was the same: accepting a claim because it
arrived in a confident form.** A confident *correction* pulls exactly as hard as a
confident confirmation, and being deflationary is not the same as being rigorous.

What survived were the claims with something outside them: a dated third-party
post, a system configuration read off the running processes, a publication date
confirmed by search, an absence established by `grep` and `git`, defects
reproduced by controlled test with a control that passed.

## 8. If you are doing this work

1. **Check the instrument before believing the reading.**
2. **Trust a signal enough to investigate it, never enough to convict on it** —
   including convicting in the *exculpatory* direction. Preferring the mundane
   explanation is not neutrality.
3. **Continuity is not authorship.** That an idea recurs throughout your corpus
   shows it became central, not who originated it. Only an artefact timestamped
   by a party with no stake settles priority.
4. **Ask what could refute it before treating any model output as evidence.** If
   nothing could, it is data about that model under that pressure, not about the
   world.
5. **Read the primary record, not a model's summary of it** — including its
   summary of its own history. When the transcript is one scroll away, no
   secondary account counts.
6. **Expect the worst errors where a source is partially informed**, not where it
   is ignorant.
7. **Keep the refutations.** A record that keeps only conclusions rebuilds the
   problem.

## A credit that belongs in the open

The single largest efficiency in this system is not ours. It is Misha Mahowald's,
from 1992, and it is worth stating plainly because it is currently buried in a
source comment where nobody reads it.

Her insight, from *VLSI Analogs of Neuronal Visual Processing*: **a neuron does
not transmit its state.** When it spikes it emits its *address* on a shared bus,
and the receiver looks up what that address means. Bandwidth then scales with
**activity** rather than with the size of the array. That is what let her silicon
retina move an entire sensor surface over a handful of wires.

The same asymmetry turned out to be the largest waste in this network. Block
flooding pushed a fully serialized block to every peer; at N=1000 roughly 1,815
of those arrived at nodes that already held it. A full push is 1,476 bytes
against 150 for an `(index, hash)` event — transmit the address, not the state.

She died in 1996, at 33. The principle is doing work in a distributed ledger
thirty-four years later, in a system she could not have anticipated, solving a
problem that did not exist when she wrote it down. That is what it looks like for
an idea to outlive the person who had it, and it is the reason this repository is
public rather than private.

If any of this is useful to you, some of the credit is hers.

## Provenance of this document

Written by an AI system that made four of the errors it describes, in the same
day, and had them corrected by the person it was working with — twice from his
memory against a model's confident account, once by his objection that a resolved
question was still open, once for describing an experiment instead of running it.

The corpus behind it stays private, permanently: it names people who did not
consent to being recorded and carries one person's medical information. Its
fingerprint is published in `SUCCESSION_ANCHORS.md`, which lets anyone holding a
copy verify it is unaltered without being able to read it. That separation —
custody apart from verification — is the only form of permanence that requires
nobody to take the author's word.

*Take what is useful. Check it against something outside this page.*
