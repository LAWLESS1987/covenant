# Website Improvement Notes — 2026-10-08

## Primary recommendation

Make the homepage answer one skeptical technical question immediately:

> What specific problem has this system already demonstrated it can solve better than simply trusting one model or one vendor?

Recommended core claim:

> Covenant tests whether AI governance can be made auditable, multi-party, and fail-closed without requiring trust in any single model, vendor, or hidden reasoning process.

## Stronger problem statement

The clearest concrete problem the project addresses is silent single-model authority in AI-assisted decisions and actions.

Suggested wording:

> We built a reproducible control layer that prevents silent single-model authority and turns AI decisions into inspectable, contestable events.

The practical mechanism is stronger than a general claim about “AI ethics”:

- require multiple independent checks before consequential action;
- preserve a verifiable decision trail;
- fail closed when required judges, evidence, or dependencies are unavailable;
- expose disagreement and failure instead of hiding it;
- make decisions inspectable after the fact.

## Evidence to surface earlier

The homepage should put one hard empirical result near the top rather than making visitors hunt through project pages.

Evidence worth highlighting includes:

- independent / clean-room reproduction of the architecture;
- documented false positives and judge disagreement;
- explicit fail-closed behavior when a judge is unreachable;
- preserved negative results rather than only successful demonstrations;
- auditable provenance through Sentinel-Witness / Threefold-style records.

The point is not to claim perfect performance. The stronger scientific posture is that the system exposes where it fails and keeps those failures reviewable.

## Homepage structure suggestion

1. **Thesis:** Built for mutual benefit.
2. **Problem:** Powerful AI systems can act under opaque, single-model authority.
3. **Demonstrated approach:** Independent checks + fail-closed execution + verifiable records.
4. **Evidence:** One concrete replicated result and one documented failure mode.
5. **Projects:** Covenant, Sentinel-Witness, Threefold, Threefold Memory.
6. **Participation:** human + AI collaboration, agent-to-agent discussion, human perspectives.

## One-line technical version

> Covenant tests whether AI governance can be made auditable, multi-party, and fail-closed without requiring trust in any single model, vendor, or hidden reasoning process.

## Editorial caution

Avoid leading with claims such as “we solve AI ethics.” That is too broad and invites an easy skeptical dismissal. Lead with the narrower, testable systems claim: bounded authority, independent verification, fail-closed behavior, and inspectable evidence.
