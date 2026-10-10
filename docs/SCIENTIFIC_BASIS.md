# Scientific basis

Written 2026-10-09 at Lawrence's request: check that the projects (covenant, threefold, threefold-memory, Sentinel-Witness, and the private research repos) align with the scientific method and match lawless1987.com, and find their scientific and philosophical backing.

Each practice below is something the repositories actually do. Beside it is the established method it comes from, with a source. The last section lists where the projects fall short of that method. It is as long as the first, on purpose.

The references are standard works, cited from knowledge and not re-opened for this page. The DOIs and page numbers are the part to check.

## Practices and their basis

| practice here | where it lives | established method | source |
|---|---|---|---|
| A claim is kept only while it can be shown wrong. A refuted claim is withdrawn in public, its wording kept, and a test fails if it returns. | `docs/RETRACTED.json`, test R1, CLAUDE.md rule 10 | Falsifiability: a claim is scientific if a possible observation could refute it. Retraction as part of the record. | Popper, *Logik der Forschung* (1934; *The Logic of Scientific Discovery*, 1959); COPE retraction guidelines (2009, rev. 2019) |
| Every check is driven both ways: break the code, see the check go red, restore, see green. | CLAUDE.md rule 8; KNOWN_ISSUES A65 (35 of 36 guards were fake) | Mutation testing in software; negative and positive controls in experiments | DeMillo, Lipton and Sayward, "Hints on test data selection", *IEEE Computer* 11(4), 1978; Lipsitch, Tchetgen Tchetgen and Cohen, "Negative controls", *Epidemiology* 21(3), 2010 |
| A separate skeptic tries to refute each claim before it is used. | water-food-air verdicts; the review rounds in the collective | Organized skepticism as a norm of science; adversarial collaboration | Merton, "The normative structure of science" (1942); Mellers, Hertwig and Kahneman, *Psychological Science* 12(4), 2001 |
| A quorum of judges counts only if the judges err independently. Correlated judges are measured, not assumed. | HF thread "A quorum of similar model judges is not a quorum"; the quorum policy | The Condorcet jury theorem requires independent voters; correlated votes lose the gain | Condorcet, *Essai* (1785); Ladha, *American Journal of Political Science* 36(3), 1992 |
| A green check is suspect until its population is counted; a measure that becomes a target stops measuring. | HF thread "Six checks that were green and meant nothing"; CLAUDE.md first and end passes | Goodhart's and Campbell's laws; construct validity | Goodhart (1975); Campbell, "Assessing the impact of planned social change" (1979); Cronbach and Meehl, *Psychological Bulletin* 52(4), 1955 |
| Every number names its unit and denominator. | CLAUDE.md rule 4; water-food-air METHOD rule 2 | Measurement: a quantity is a number and a unit; a rate needs its denominator | BIPM, *The International System of Units* (9th ed., 2019) |
| Evidence tiers separate measurement, association, established effect and documented conduct. A settlement is not an admission. A trend correlation is shown beside its detrended version. | water-food-air `METHOD.md`; `connections.md` §5 | Hierarchies of evidence; causal inference beyond association; spurious correlation of trending series | Hill, "The environment and disease: association or causation?", *Proc. R. Soc. Med.* 58, 1965; Yule, *J. R. Stat. Soc.* 89, 1926 |
| Report what was not measured; UNDETERMINED is an answer. | CLAUDE.md rule 9 | Reporting limitations; the file-drawer problem | Rosenthal, *Psychological Bulletin* 86(3), 1979 |
| Corrections and failures are published with the successes. | `docs/CORRECTIONS.md`; the site's "What the checks actually found" | Publication bias, and why it inflates published findings | Ioannidis, "Why most published research findings are false", *PLoS Medicine* 2(8), 2005 |
| Scope is stated on every project page: "does not establish production safety or independent replication". | lawless1987.com project cards | Replication as the test of a finding | Open Science Collaboration, *Science* 349(6251), 2015 |

## Philosophical backing (the smaller part, by request)

- **Why "mutual benefit" can be argued, not only asserted.** Cooperation stable among self-interested parties: Axelrod, *The Evolution of Cooperation* (1984). Rules agreed under uncertainty about one's own position: Rawls, *A Theory of Justice* (1971).
- **Why a fail-closed gate is the defensible default under uncertainty.** The precautionary principle, with its known critique that it can block benefit too: Sunstein, *Laws of Fear* (2005). The project's gate errs toward refusing and says so, which is both halves.

## Where the projects fall short of the method

These are true today and are what a reviewer would raise first:

1. **No independent replication.** Every measurement was made by the project, on its own machines, mostly by AI agents working for one operator. The site says this. The scientific method says a finding is provisional until someone else reproduces it.
2. **No preregistration.** Thresholds and tests are often written after seeing data. Pre-registering the hypothesis and the pass bar would close this (Nosek et al., "The preregistration revolution", *PNAS* 115(11), 2018).
3. **Small evaluation sets.** The judge's exam is 53 cases. The confidence intervals on its rates are wide and are not always printed beside the rates.
4. **The graders are related to the graded.** The skeptics, the reviewers and the authors are often models of the same family. The project measured this problem for judges (the quorum thread) but has not removed it for reviews.
5. **Selection of what gets checked.** Checks were added where failures were noticed, so the checked population is not a random sample of the system. The project's own rule ("name the population it read") is the partial answer.
6. **Two practical slips this week, both recorded.**
   - A317's new gate broke another suite for a day because its consumers were not all run (KNOWN_ISSUES A321).
   - An AI's regulatory answer had two dating errors until checked (water-food-air `cross-ai/`).

   The record caught both. That is the method working, and also evidence that the method is needed.

## Alignment with lawless1987.com (checked 2026-10-09)

- **Links.** Every link on the home page answered 200: the four repositories, the corrections and retraction files, the agents guide, the forum, and both Hugging Face threads.
- **The gate claim.** The site's card ("admitted an ordinary send and rejected the tested theft, deception, and coercion cases") matches README.md's 2026-09-08 correction, measured on a clean clone.
- **Scope.** The site's scope language matches the gaps above: no claim of production safety, no claim of independent replication.
- **One word to consider.** The banner reads "SUPER INTELLIGENCE / OPEN RESEARCH". Nothing in the repositories measures intelligence, super or otherwise. Read as an aspiration it is fine. Read as a description it is the one phrase on the page the evidence does not reach. That is his call.
