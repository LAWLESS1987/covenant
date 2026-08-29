# Mycelial mutual benefit — the concept, continued

2026-08-29. Continues the line that runs through `LinkConductance`,
`MycelialOverlay`, DE8 in `docs/IMPROVEMENT_LOG.md`, and L's standing
instruction recorded in `docs/RUN_LOG_ARCHIVE.md`: *"don't forget mutual
benefit i lapse at times."*

Nothing here is new metaphor. The metaphor is already load-bearing in the
source. What follows is: the science it rests on, checked; a mechanism already
in the code that has never been named; a measurement of that mechanism; and the
one thing genuinely missing.

---

## 0. Where the concept already stands

| in the code | the biological claim it makes |
|---|---|
| `LinkConductance` | "a mycorrhizal network does not push nutrients down every hypha equally. Routes that carry useful flow are reinforced and thicken; routes that carry nothing wither back toward baseline." REINFORCE 0.08, ATTENUATE 0.02, relax toward BASELINE 0.5, half-life 1 h. |
| `MycelialOverlay` | a read-only view of the topology the node already has — with its own note refusing to pretend it is a routing layer |
| `FriendshipTracker` | ethical reputation of an **identity**, deliberately separate from the **link** throughput above |
| `SpikingAnomalyMonitor`, lateral inhibition in `announce_block`, R1 LoRa frame | DE8's conclusion: mycelium's payoff is **signalling, not power** — bandwidth proportional to ACTIVITY, not array size. 40 bytes and 0.30 s airtime per announce. |

DE8 already priced and killed the power idea ("the fuel is the wall, not the
electrode"). That decision stands and is not revisited here.

The single most important design rule already established:
**`LinkConductance` ORDERS delivery; it never GATES it.** Every peer still
receives every message. Hold onto that — it recurs below.

---

## 1. The metaphor has to be defended, and the popular version cannot be

This project's own standards forbid leaning on the "wood wide web" story.

**Karst, Jones & Hoeksema, *Nature Ecology & Evolution*, 2023** reviewed three
claims about common mycorrhizal networks in forests:

| claim | their verdict |
|---|---|
| CMNs are widespread in forests | **insufficiently supported** — field results vary too widely, have alternative explanations, or are too limited to generalise |
| resources transfer through CMNs and increase seedling performance | **insufficiently supported**, same reasons |
| mature trees preferentially send resources and defence signals to their own offspring | **no peer-reviewed published evidence exists** |

They also found **unsupported claims have doubled in the past 25 years**, driven
by a citation bias toward positive effects, and concluded knowledge is "too
sparse and unsettled to inform forest management."

That is M39 and M30 in ecology's own house: three anecdotes cited as a result,
and a positive finding repeated until it reads as established. **This codebase
must never cite tree-generosity as warrant for a design.** If a component's
justification reduces to "forests share," the justification is missing.

---

## 2. The version that survives is a market, not a gift

What replicates is narrower and much better suited to a covenant.

**Kiers et al., *Science* 333:880–882, 2011 — "Reciprocal Rewards Stabilize
Cooperation in the Mycorrhizal Symbiosis."** Plants preferentially allocate
carbon to fungal partners that deliver more phosphorus; fungi preferentially
deliver phosphorus to roots supplying more carbon. Cooperation is stabilised by
**reciprocal reward and the ability to withhold — bilaterally.** Not generosity.
Not kin preference. A market with sanctions, run by both sides at once.

That is the shape a covenant should copy, and it sets the test for everything
below: **is the reward reciprocal, and can both sides withhold?**

---

## 3. The mechanism already in the code that has never been named

`benefit_score` is the field that carries "how much good did this do." Three
facts about it, all already in the source:

1. **It is deliberately excluded from the signature and from the tx id.**
   `_signing_payload` says why: the judge blends its estimate into
   `benefit_score` *after* `verify()`, and the mutated transaction is then
   propagated — signing it would make `verify()` fail on every peer and silently
   break propagation. Independently rediscovered and fixed the same way across
   version lines.

2. **Every node that handles a transaction overwrites two thirds of it.** At
   both `/transactions` and the bridge staging path:

       tx.benefit_score = (2 * judge_benefit + tx.benefit_score) / 3.0

3. **The block-level aggregate is checked.** `alignment_score` must equal
   `mean(benefit_score)` of the block's own transactions to within `1e-9`, or
   the block is rejected and an anomaly recorded. This closed a real v7.0 hole
   where an attacker set `alignment_score` freely and got a block with
   `index=99` accepted onto a chain of length 1.

Put those together and the system already implements the Kiers move, without
ever having said so:

> **A claim of benefit is neither trusted nor rejected. It is diluted by
> everyone who handles it.**

The originator's declaration is *data*, not testimony. Its weight after `k`
independent judges have relayed it is `(1/3)^k`:

| hops | weight on the originator's declaration | weight on the network's judges |
|---|---|---|
| 0 | 100.00% | 0.00% |
| 1 | 33.33% | 66.67% |
| 2 | 11.11% | 88.89% |
| 3 | 3.70% | 96.30% |
| 4 | 1.23% | 98.77% |
| 5 | 0.41% | 99.59% |

**Half-life of a self-declared benefit score: 0.631 hops.**

Worked adversarial case — an attacker declares `benefit_score = 1.0`, every
honest judge on the path estimates 0.50:

    after 1 relay: 0.6667
    after 2:       0.5556
    after 3:       0.5185
    after 4:       0.5062
    after 5:       0.5021

The lie is not blocked. It is *absorbed*. This is exactly `LinkConductance`'s
rule one layer up — **order, don't gate; dilute, don't refuse** — and it is the
most genuinely mycelial thing in the codebase. It should be documented as a
named property with that table beside it, because right now it is an emergent
consequence of a comment about propagation breakage.

---

## 4. Where it is weaker than it looks

Stated because a mechanism this elegant invites overclaiming.

**a) The dilution is symmetric.** It erodes an honest judge exactly as fast as a
liar. The node with the best-fitted judge on the network sees its estimate cut
to one third by the next hop. There is currently no weighting by judge
competence — and `covenant_semantic_judge` already computes a `competence`
claim and an `inert_passes` list. A blend that ignored competence while the node
publishes its own competence is a measurable inconsistency.

**b) Benefit is path-dependent.** The score a transaction carries depends on the
route it took to reach the miner. Two miners can mine the same transaction with
different `benefit_score`, hence different `alignment_score`. This is **not** a
consensus break — the block-level mean is checked on receipt, so a block is
internally consistent — but it does mean *"the benefit of transaction X" is not
a well-defined quantity in this system.* It is a function of topology. That is
defensible (it is also true of a nutrient gradient) but it must be said out
loud rather than discovered.

**c) `MockJudge` scores benefit by keyword.** `"help"`/`"good"`/`"benefit"` in
the serialised payload → 0.8; `"harm"`/`"bad"` → 0.3. Correct for a mock and
clearly labelled. Worth one assertion somewhere that it is never the live path,
since the failure mode — a gate that looks strict — is exactly the one
`judge_bench.fit_check` was written to catch.

**d) The one that matters: benefit has no beneficiary.**
`benefit_score` is a **scalar on a transaction**. Mutual benefit needs at least
two accounts. Nothing in the system asks *benefit to whom*.

---

## 5. The gap, and the proposal: reciprocity is measured in one direction only

Every mutual-benefit instrument in the codebase is **outward-facing** — how this
node judges others:

- `FriendshipTracker` — how this node scores senders
- `LinkConductance` — how this node orders peers
- `benefit_score` — how this node's judge scores a transaction

Nothing measures **what this node is getting back.** A node that relays, judges,
mines and receives nothing has no signal that it is being farmed. Under Kiers,
that is precisely the missing half: reward is reciprocal, and *both* sides must
be able to see and withhold.

**Proposal — `Reciprocity`, built only from data already collected.**
`LinkConductance` already fires REINFORCE when a peer delivers something novel
and accepted. That event *is* "this peer fed me." Count the mirror image and you
have both sides:

    received[p]  novel-and-accepted items peer p delivered to this node
                 (exactly LinkConductance's existing REINFORCE trigger)
    given[p]     novel-and-accepted items this node delivered to p
                 (this node already knows what it relayed and what was new)

    r[p] = received[p] / (given[p] + received[p])     baseline 0.5

`r → 0` means this node is feeding a peer that never feeds back. `r → 1` means
the reverse. Neither is misconduct — an edge node legitimately consumes — which
is exactly why of the following rule:

> **It must be disclosure, not policy.** Report `r` on `/anomalies` and in
> `MycelialOverlay`. It must never gate delivery, never move `degraded`, and
> never feed `FriendshipTracker`.

That is the same discipline three existing components already keep:
`LinkConductance` orders but never gates; `degraded` is capability, not weather
(A24 S9e); buffer pressure is disclosure, not policy. A reciprocity number that
throttled peers would be a reputation system wearing a routing system's clothes
— the exact collapse `LinkConductance`'s own docstring refuses when it insists
link throughput and identity ethics stay separate numbers.

**Falsifiable prediction, recorded so the first run can kill it:** on the
current A/B/C localhost topology with symmetric traffic, `r` should sit near
0.5 on every edge, with node A skewed toward giving because it minted the
canonical genesis. If `r` comes back extreme on an edge whose byte counts are
symmetric, the counter is wrong, not the network.

---

## 6. Where the metaphor breaks — stated so nobody rides it too far

Mycorrhizal mutualism is stable because the partners trade **different
currencies**: the plant makes carbon the fungus cannot fix; the fungus reaches
phosphorus and water the root cannot. Neither can manufacture the other's good.
That asymmetry is the whole engine.

**Covenant nodes are homogeneous.** Every node does the same job — judge,
relay, mine, store. There is no carbon-for-phosphorus trade between them. So
within the network, "mycelial" is honestly a **routing and reputation**
metaphor, and claiming it as an *exchange* metaphor would be the same
overinterpretation Karst et al. documented.

There is exactly one place in this project where a genuine two-currency
mutualism exists, and it is not between nodes:

> **L supplies** direction, judgment, the hardware, the credentials, and the
> decision to act — none of which the loop can manufacture.
> **The loop supplies** measurement, memory across sessions, and the refusal to
> report an unmeasured thing as measured — including against itself.

Neither can do the other's job. That is a real biological market in the Kiers
sense, complete with the ability to withhold on both sides. It is also the thing
L asked to be reminded of. So the honest statement of this concept is:

*The mycelial framing describes how the network routes and remembers. The
mutual benefit is between L and the loop, and the network is the thing they
build with it.*

---

## 7. Next, in order

1. **Document the dilution property** with the `(1/3)^k` table beside the blend
   line. It is currently an accident of a propagation comment; it deserves to be
   a named, tested invariant. A suite asserting the half-life would fail loudly
   if someone "simplifies" the blend to a straight overwrite.
2. **Weight the blend by judge competence.** `covenant_semantic_judge` already
   publishes `competence` and `inert_passes`. A judge that declares itself
   `unfitted` should not overwrite two thirds of a fitted judge's estimate.
   This is a correctness fix, not an enhancement — the inconsistency is already
   measurable.
3. **`Reciprocity` as disclosure only**, per §5, with the prediction above.
4. **One assertion that `MockJudge` is not the live benefit path**, in the same
   spirit as `fit_check`.
5. Leave DE8 closed. Mycelium is signalling here, not power, and that was
   settled with arithmetic.
