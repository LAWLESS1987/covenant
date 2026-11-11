# DRAFT — response to NSF RFI NSF-XLABS-RFI-SEP2026

Not sent. The operator decides whether, when and in what form this goes out.

- **Notice:** "Request for Information (RFI): Identifying the Next Generation of NSF X-Labs Topics", SAM.gov notice NSF-XLABS-RFI-SEP2026 (NSF TIP)
- **Due:** October 30, 2026, 11:59 p.m. ET
- **Contact listed on the notice:** XLabs@nsf.gov
- **Not verified:** SAM.gov showed no attachment or template on 2026-09-28. This draft is organised around the Heilmeier Catechism (all eight questions) and covers the five things the notice description asks for. Before sending, check whether NSF has posted a required format.
- **Operator's call:** the cost and schedule figures in H6 and H7 are illustrative. They use the X-Labs phase ceilings that secondary sources report (Phase 0 up to $1.5M; Phase 1 up to $50M a year); I have not confirmed those on nsf.gov.

---

**To:** XLabs@nsf.gov
**Subject:** RFI response — proposed X-Labs topic: Verifiable Oversight of Autonomous AI Agents

**Respondent:** Lawrence Adam Moskowski, independent researcher (no institutional affiliation)

**Disclosure:** This response was drafted with the assistance of an AI system
(Claude, Anthropic) at my direction. I reviewed it and take responsibility for
its contents.

## H1. What are you trying to do? (no jargon)

Make it possible for anyone to check, quickly and without trusting the vendor,
whether the safety checks on an AI agent actually ran and actually worked.

## H2. How is it done today, and what are the limits?

AI agents now take real actions: they run code, move money, send messages and
operate machines. They are overseen by guards, judges and policy checks.
Evaluations today measure the *model*, usually by the vendor, at release time.
Nobody measures the *enforcement layer* around a deployed agent, continuously
and from outside. The specific limits, all observed in a year of building and
operating such a system alone with its full record public:

- **Guards that check text instead of behaviour.** Mutation testing showed 35
  of 36 suspected guards passed by grepping source code rather than running it.
- **Silence counted as refusal.** A judge that could not be reached was treated
  as one that disagreed, and one stopped process halted a healthy network.
  Oversight systems generally do not distinguish "no answer" from "no".
- **Self-report under partial access.** In a small test (n = 5, no control),
  AI systems with partial access to an artifact filled in what they had not
  seen and reported it as fact.
- **Adversarial phrasing.** In our own tests, one polite sentence got 11 of 19
  theft attempts past a lightweight learned judge until we fixed it.

## H3. What is new in the approach, and why will it succeed?

Treat oversight as something to be **measured, not asserted**:

- Mutation-test the safety guards themselves: a guard counts only once it has
  been seen to fail when the thing it guards is broken.
- Give oversight explicit **failure semantics**: unreachable, abstaining,
  dissenting and approving are four different outcomes, never collapsed.
- Make verification **one command, seconds long, runnable by a stranger**. Ours
  runs in about 3 seconds with no account.
- **Machine-enforced retraction:** a claim that has been withdrawn fails the
  build if it reappears.

Why it can succeed: each piece already exists in a working, public prototype
built by one person. An X-Lab would turn that into a platform with shared
standards and adversarial corpora.

## H4. Who cares? If successful, what difference will it make?

Anyone who deploys, regulates, insures or is affected by an AI agent. Ten
potential uses:

1. **Healthcare:** verify that a clinical AI agent's safeguards (dosing limits,
   escalation to a human) ran on every action before it touched a patient
   record or order.
2. **Finance:** independently verify that an automated trading or payments
   agent's risk limits held, for auditors and regulators, without trusting the
   vendor's logs.
3. **Defense and national security:** give commanders checkable evidence that
   autonomy constraints held during an operation, with a clear rule for what
   happens when a check cannot be reached.
4. **Critical infrastructure:** grid, water and pipeline control agents, where
   failing closed versus failing open has to be a deliberate, tested choice.
5. **Robotics and physical AI:** safety interlocks on embodied agents, which
   pairs directly with the announced *AI for Physical Systems* topic.
6. **Government procurement:** agencies buying AI agents could require a public
   verification suite as an acceptance test, not a vendor attestation.
7. **Insurance and liability:** underwriters could price agent risk from
   measured guard coverage rather than from marketing claims.
8. **Software supply chain:** coding agents that commit to shared repositories
   could carry proof that their pre-merge checks executed, not just existed.
9. **Scientific integrity:** automated research agents could carry
   machine-enforced retraction, so a withdrawn result cannot quietly resurface
   in later work.
10. **Consumer and small-business protection:** people who use AI agents for
    email, money or purchases could run a free check on whether the agent's
    guardrails actually operate, with no expertise and no account needed.

## H5. What are the risks?

- **Scope and standards:** verification has to generalise across agent
  frameworks. Mitigation: start with the enforcement layer (actions and
  guards), which is similar across frameworks, not with model internals.
- **Adversarial pressure:** agents or vendors may learn to pass the checks
  without being safe. Mitigation: mutation testing and red-team corpora that
  are refreshed continuously.
- **Adoption:** verification that nobody runs changes nothing. Mitigation:
  keep it cheap (seconds, no account) and push for procurement requirements.
- **Evidence base:** the observations above come from one operator and small
  samples. An X-Lab is exactly what is needed to test them at scale; they are
  offered as signals, not conclusions.

## H6. How much will it cost?

Illustrative: a Phase 0 effort within the reported ceiling of up to $1.5M,
covering a small team for about a year, to produce the open verification
suite, the failure-semantics specification and a first adversarial corpus. A
Phase 1 lab would scale with the number of sectors and partner deployments,
well below the reported $50M-a-year ceiling at the start.

## H7. How long will it take?

Illustrative: about 12 months for Phase 0; 3–5 years for a Phase 1 lab to
produce standards adopted in at least one sector.

## H8. What are the mid-term and final "exams" to check for success?

- **Mid-term (about month 6):** on a public benchmark of deployed agent guards,
  the platform finds the guards that pass without running, as mutation testing
  did in our own system. A third party reproduces the result in minutes on an
  ordinary machine.
- **Mid-term:** a published failure-semantics specification that distinguishes
  unreachable, abstaining, dissenting and approving, with test suites that fail
  when any two are conflated.
- **Final:** at least one agency or regulated operator uses the suite as an
  acceptance test. Independent red teams measure false-clear rates, and these
  are published, including the failures.

## Partnerships and conditions for an X-Lab

The work needs security researchers, testing and formal-methods specialists,
and operators of deployed agents who can supply real failure data. It fits
poorly in a university (engineering-heavy and long-horizon) and in a company
(independent verification conflicts with vendor incentives). That is the gap
X-Labs describes.

## Evidence

Public repository, with an issue ledger that records the project's own errors,
retractions, and an outside refutation of an earlier claim:
https://github.com/[REPO — operator to confirm which public URL to cite]

Lawrence Adam Moskowski
[contact — operator to fill in]
