# US ROUTING MAP — verified findings, assembled 2026-08-31

Sender: Lawrence Adam Moskowski, private individual, resident of New Jersey. No entity, no CAGE code, no clearance, no funding request. Ask is refutation only.

Governing rules applied: OUTREACH_STRATEGY.md §2 (the binding constraint is **categorisation**, not quality), §3 (rank by what the recipient can DO), §6 (**never spend a tier before the one below it has produced evidence**).

---

## 0. READ THIS BEFORE ANYTHING IS SENT — one blocker gates every channel

`C:\Users\Lawre\covenant-dev\LICENSE` says **"COVENANT — LICENCE NOT YET CHOSEN … Under the Berne Convention, code with no licence is all rights reserved. Nobody may copy, modify or redistribute this repository until its author chooses a licence."** `README.md` line 365 repeats it.

`docs/OUTREACH_STRATEGY.md` §4 says the opposite — "the repository is Apache-2.0, so a fork costs them nothing" — and so does the framing of this whole outreach. A verifier found the "Apache-2.0" assertion in at least **six** files: `CONTRIBUTING.md:55`, `docs/CONSTITUTION.md:150`, `docs/OUTREACH.md:122`, `docs/OUTREACH_INSTITUTIONAL.md:32` and `:67`, `docs/OUTREACH_STRATEGY.md:81`, `docs/OUTREACH_US_IL.md:58/80/175/213`.

Why this is not a footnote: **the ask on every channel below is "clone it and run it."** Today the repository's own licence file says nobody may. The first door on the list is CISA's *open source security* office, whose readers open LICENSE first; the second is a *procurement* channel. This is §7's second failure mode exactly — overclaimed, then checked, then discounted — the only one that also destroys the next attempt.

**Fix the LICENSE and the six documents in one commit. It is an afternoon and it gates the entire map.**

---

## 1. ROUTING TABLE

| # | Institution | The door inside it | Exact route | Open / closed + date | What that reader can actually DO | Verdict |
|---|---|---|---|---|---|---|
| 1 | **NIST** (Commerce / ITL) | AI Standards **Zero Drafts** pilot, TEVV topic — *already in hand* | `ai-standards+tevvzd [at] nist.gov` (page prints it bracketed) | **OPEN.** Page updated 14 Aug 2026. **No stated TEVV deadline.** Separate public-facing documentation draft takes input to **16 Sep 2026**. Submissions become public record | Log it as a filed submission to a named standards topic; TEVV is literally the subject of "conformance proved by behaviour" | **SEND NOW** |
| 2 | **DoD / CDAO** | **MAITE** public GitHub tracker (`mit-ll-ai-technology/maite`, MIT Lincoln Laboratory, CDAO-funded) | Open a public issue at `github.com/mit-ll-ai-technology/maite/issues` | **OPEN.** Repo pushed **2026-08-26**; issues enabled; maintainer `jdarena66` answered #43 (2025-11-21 → 2025-12-01) and #44 (2026-03-06 → **2026-08-27**) | An identified human engineer whose project exists to make independently-built implementations interoperate can clone, run `sh check.sh`, and reply — on his own authority, same afternoon | **SEND NOW** |
| 3 | **NIST** | **COSAiS** — SP 800-53 Control Overlays for Securing AI Systems, community Slack | Email `overlays-securing-ai [at] list.nist.gov`, subject verbatim **"Join Overlays Securing AI Slack"**. Asks full name, email, "organization (optional)" | **Mailbox open, no closing date — LIVENESS UNCONFIRMED.** Project page, Slack page, publications page **and** FAQ all read "Updated January 08, 2026". Its only stated deadline (13 Feb 2026) is seven months past. FAQ still promises "Q1 FY26" | Control-security engineers in a facilitated channel with named PIs; any member can run the checker and post the result. Cannot adopt or cite — overlays are SP 800-53 control text | **SEND NOW** (second send, not a replacement for #1) |
| 4 | **DHS / CISA** | **Open Source Security** (the office behind the C4 trust-assessment framework) | `OpenSource@cisa.dhs.gov` — verbatim from cisa.gov/opensource: *"Please share your thoughts by emailing us at…"* | **OPEN, standing mailbox, no deadline.** cisa.gov pages carry **no** last-updated field at all (checked: no `dateModified`/`datePublished`). Office output is dated: C4 guidance **30 Jul 2026**, "Gold Eagle" **26 Aug 2026** | An engineer can clone and run it. Cannot adopt, endorse, fund or cite. No logging obligation, no ticket, no reply obligation | **HOLD — licence blocker (§0) bites hardest here.** Then send |
| 5 | **ODNI / IARPA** | **IARPA Solutions Marketplace**, Notice **IARPA-OT-26-001**, run with The Applied Research Institute | Landing page `iarpa.gov/marketplace`; questions `success@iarpamarketplace.us`; secondary `dni-iarpa-contracts@iarpa.gov`; notice `sam.gov/opp/734cbcbde3694ec08d923b4e9f5cadb2/view` | **OPEN.** Posted 17 Jul 2026, response date **31 Jul 2027 16:00 ET**, inactive 15 Sep 2027. Announcement v1.0 effective 1 Aug 2026. **Monthly cutoff = final calendar day, 12:00 noon ET** — today's has passed; late rolls to September, nothing lost | Monthly assessment returns **ratings, written assessor comments and suggestions for improvement**, for awardable *and* non-awardable submissions, ~30 days after cutoff. Resubmission permitted. Awardable → catalogue visible to IC accounts (guarantees nothing) | **HOLD — licence + production cost.** See §4 for what it actually costs |
| 6 | **NIST** | **SP 1353 ipd** public comment (AI for cybersecurity / CSF reporting) | `csf [at] nist.gov` | **OPEN to 15 Oct 2026, 11:59 PM.** News item 19 Aug 2026 | Log and adjudicate the comment against the draft. Will almost certainly not run anything | **WEAK FIT — probably skip** |
| 7 | **NIST** | **NVD Modernization RFI**, docket **NIST-2026-0100** (91 FR, published 12 Aug 2026) | **regulations.gov portal only.** Notice states NIST *"will not accept comments … by postal mail, fax, or email"* | **OPEN to 13 Oct 2026, 11:59 p.m. ET** | Public docket comment, read by the NVD team. Only crack is its Question 5 on machine-readable data standards | **WEAK FIT — send only if answering a numbered question. Never send the general letter here** |
| 8 | **EOP / OSTP** | NITRD **National Coordination Office**, AI R&D Interagency Working Group | `nco@nitrd.gov` — printed beside Technical Coordinator Faisal D'Souza on `nitrd.gov/coordination-areas/ai/` | **Mailbox OPEN** (about-nitrd page "Page updated: May 8, 2026"). **No consultation to file into — CLOSED.** No open AI RFI from OSTP or any EOP component; last one closed 2025-10-27 | One thing only: staff-level routing to IWG co-chairs. One co-chair is **Martin Stanley of NIST** — i.e. this door's single exit is already unlocked from outside via #1. No testing function, no docket | **WAIT** — send only after #1 has produced something |
| 9 | **US Congress — NJ delegation** | **Sen. Andy Kim (D-NJ)**, personal office, topic *Technology* or *Science* | `https://www.kim.senate.gov/contact/`. Hart 520, DC 20510 · (202) 224-4744 · Jersey City (201) 377-0900 · Barrington (856) 757-5353 | **OPEN, permanently, no deadline** | Log and answer (form letter, floor). Route to the LA covering his Commerce portfolio (discretionary). **Make a member inquiry to NIST about a constituent's filing** — a real, staffed category. Cannot evaluate code, adopt, endorse or fund | **WAIT** — worthless before #1 exists, routable after |
| 10 | **US Congress — NJ** | Sen. **Cory Booker (D-NJ)** | `booker.senate.gov/contact/write-to-cory`, issue "Science and Technology"; 306 Hart · (202) 224-3224 | Open, no deadline. **Seat is Class II — on the ballot Nov 2026, term expires 3 Jan 2027** | Nothing #9 cannot do better. His committees (Foreign Relations, Judiciary, Small Business, Agriculture) carry no NIST or standards jurisdiction | **FALLBACK ONLY** |
| 11 | **US House** | His own Representative | **NOT FOUND — depends on his street address and must not be guessed.** He runs `house.gov/representatives/find-your-representative` himself | n/a — but see §4: NJ district lines have moved, and today's answer expires when the new Congress is sworn in **Jan 2027** | Unknown until the district is known | **LOOK UP FIRST, then treat as tier 9** |
| 12 | **DoD / CDAO** | JATIC program front door | Form `https://forms.osi.apps.mil/r/LvUQytucAc` **and** `cdao-jatic@groups.mail.mil` | Live, no deadline — **but every page on `cdao.pages.jatic.net/public/` returns Last-Modified 19 May 2025.** Live program, stale front door | Solicits exactly this ("feedback… on any of our products"). **Published refusal:** *"Does the JATIC program perform AI test and evaluation on specific programs? No…"* — so never frame it as "evaluate my project" | **SECOND STEP after #2.** Send to both; treat silence as an unresolved delivery question |
| 13 | **In-Q-Tel** | IQT **Labs** collaboration inbox | `info@iqtlabs.org` (confirmed on iqt.org) | Post carrying it is dated **22 May 2023**. General inbox, no documented process, no stated evaluation function | Whatever a named researcher would do — nothing obliges them | **TREAT AS A NAMED-RESEARCHER APPROACH, not an institutional channel** |

### Explicitly UNCONFIRMED — do not tidy these into certainty

- **JATIC form (#12) acceptance of a non-DoD submitter — UNCONFIRMED.** Returns HTTP 200 to a Microsoft Forms response page rather than a login screen, but the body renders in JavaScript and no `AnonymousResponse` / `AllowAnonymous` flag was found either way.
- **`cdao-jatic@groups.mail.mil` inbound from a non-.mil sender — UNCONFIRMED.** It is a DoD Enterprise Email distribution list; internet-facing MX records exist (`pri-/sec-jeemsg.eemsg.mail.mil`) so routing is possible, but list acceptance policy is unknowable without sending. Its `mailto:` on the Contact page is **malformed** (`mailto:<CDAO-jatic@groups.mail.mil>`) — if a click fails, type it.
- **Whether the JATIC inbox is monitored at all — UNCONFIRMED.** Live program + front door untouched since May 2025 is compatible with both answers.
- **The two ODNI Appian portal URLs** (`odni.appianportalsgov.com/registration-portal`, `odni.appiancloud.us/suite/sites/ram/page/submissions`) — both return HTTP 200 and are genuine ODNI-branded instances, but **neither appears in IARPA's own announcement or on SAM.gov**, and iarpa.gov could not be read by a second checker. **Lead with `iarpa.gov/marketplace` and `success@iarpamarketplace.us`, which are confirmed in IARPA's own announcement.** Treat the Appian links as convenience only.
- **COSAiS Slack join-form URL — NOT FOUND** (obfuscated on csrc.nist.gov). Use the email fallback. Do not reconstruct a Google Forms link.
- **`www.ai.mil` — could not be read at all** (HTTP 403, Akamai, to every method tried). So: whether CDAO publishes an office-wide contact, whether it still lists JATIC, and whether it runs any RFI are all **unknown**. A human opening it in an ordinary browser is the cheapest next step.
- **Current HSGAC Rules of Procedure (119th Congress) — UNREAD.** The PDF uses subset fonts and could not be text-extracted. The 2011 print was substituted; no claim is made that the 2025 rules match it.
- **Kim's subcommittee roster — three readings gave three answers.** His **full-committee** seat on Commerce, Science, and Transportation is confirmed twice (kim.senate.gov/about and commerce.senate.gov/members); that is all the argument rests on. He is **not** on the Subcommittee on Science, Manufacturing, and Competitiveness — the one whose jurisdiction is literally "standards and measurement."
- **house.gov redistricting language and webmaster quotes** — read live by one checker, HTTP 403 to a second. Substance stands; treat exact wording as single-sourced.

### Addresses that look right and are dead — never paste these

| Address | Why not |
|---|---|
| `AI-Strategy@ostp.eop.gov` | Appears only in a 2023 Federal Register notice bound to a prior-administration staffer. **Not confirmed on any current whitehouse.gov or ai.gov page.** |
| `ITAC@state.gov` | Real, in a genuine 2019 FR notice. The committee was **renamed in July 2020** and has been silent since **4 Aug 2022**. This is the exact failure mode that already cost this project five months. |
| `AskPublicAffairs@state.gov`, `Secretary@state.gov` | Surfaced only from the 1997–2001 State archive site. ~25 years stale. |
| `labsinfo@iqt.org` | Search-snippet only. Does **not** appear on any iqt.org page. Use `info@iqtlabs.org`. |
| `Statementsfortherecord@finance.senate.gov` | Real and live — and the **wrong committee** (tax, trade, health, Social Security). Recorded only as proof such channels exist elsewhere in the Senate. Do not use. |
| whitehouse.gov/contact form; 1600 Pennsylvania Ave NW | Two-option dropdown, President or Vice President. Constituent correspondence. No topic routing, no technical reader. |

**Correction to an earlier finding, recorded so it is not repeated:** an intermediate report claimed DARPA's Contracts Management Office page still *displays* a link to "RFI: End to End Automation and Evaluation Tools" (DARPA-SN-25-60). It does not. That whole block is inside an HTML comment — DARPA retired it correctly, and a tag-stripping text extractor manufactured the illusion. The RFI itself genuinely closed **26 Mar 2025**. DARPA is the wrong door for other reasons; it is not guilty of this one.

---

## 2. THE DOORS THAT ARE SHUT

**These are not options for an unaffiliated individual. Stated plainly so nobody spends a week discovering it.**

**Need a company, and say so in their own words**

- **In-Q-Tel business plan submission.** The form's required fields include **Company\***, **Employees\***, **Month Founded\***, **Year Founded\***. There is no field an individual can leave blank to proceed. The page's own bar: *"If your company has venture backing and technology ready to launch, or is already on the market, we want to hear from you."* Its only possible action is an investment decision in a company that does not exist. **Closed.**
- **NIST AI Consortium.** *"NIST invites organizations"*; *"Selected participants will be required to enter into a consortium Cooperative Research and Development Agreement (CRADA) with NIST."* A private individual cannot sign a CRADA. **Closed.**
- **DHS S&T LRBAA** (open to 31 May 2029): *"Businesses of all sizes, universities, national laboratories, and other R&D organizations."* Individuals are not listed; it is a FAR contract vehicle and a funding instrument. **Closed.**
- **DHS S&T SVIP:** *"U.S. and international startups up to $2M in non-dilutive funding."* Requires a company. **Closed.**
- **DHS Partnership Intermediary Agreements:** closed 30 Aug 2026 and required an intermediary organization anyway. **Closed twice.**
- **State Dept IDET/ITAC advisory committee** (the only State body that ever fit the description): charter requires representative members — *"a prospective member must represent a company or organization. Solo members … will not be selected."* Also dormant since 2022. **Closed by charter and by silence.**

**Need SAM registration / a UEI / a contract vehicle**

- **DARPA, every route.** Proposer general terms, incorporated into every BAA: *"All proposers must be registered in SAM … and have a valid Unique Entity ID to receive an award … All proposers are to provide their Unique Entity ID in each proposal."* And *"Email submissions will not be accepted"* — submission runs through `baa.darpa.mil`, where *"each user submitting a proposal must create their own **Organization** Registration."* The IPTO Office-Wide BAA (HR001126S0011, abstracts due 22 Jun 2027) is open and is a **funding** vehicle; "try to break this" submitted as an abstract is a category error its evaluators would correctly mark non-conforming. DARPA's own CMO page: *"We do not encourage submission of unsolicited proposals."* **Closed in substance.**
- Note the near-miss: I2O Office-Wide BAA HR001126S0001 carries a **Notice of Temporary Closure effective 24 June 2026**; I2O was superseded by IPTO. Anyone working from a pre-June-2026 note writes to a closed announcement at a renamed office.

**Need a government or contractor account**

- **`gitlab.jatic.net`** — JATIC's full toolchain and its issue/merge-request path: *"all government employees or contractors can sign up for accounts."* **Closed.** The public GitHub mirrors (row 2) are the open half.
- **DHS S&T Technology Clearinghouse** — closed twice over: the site itself is down (*"check back in FY27"*) and submissions are restricted to DHS program managers and authorized DHS staff. **Closed.**

**Need a committee, a chair, or a statute**

- **GAO work requests.** *"[GAO work] is done at the request of congressional committees or subcommittees or is statutorily required."* A private individual cannot request GAO work; only a congressional office can. *(One verifier notes GAO's fuller protocols do recognise individual Member requests, weighted by committee of jurisdiction — so this is closed **to him**, and marginally more available to Sen. Kim than a first read suggests. It should still not be asked for.)*
- **Statement for the record, House Science.** Closed **by rule**. Committee rules for the 119th, adopted 5 Feb 2025: *"**Committee Members** have 10 calendar days from the date of a hearing to submit brief and pertinent statements or materials in writing for inclusion in the record."* The window belongs to Members. The public is not granted submission authority anywhere in the rules.
- **Statement for the record, Senate Commerce and HSGAC.** **NOT FOUND** — no email, no form, no docket, no postal instruction on any page fetched, including the FAQ that /contact points to. Commerce's contact page carries postal addresses and two phone numbers and no email at all.
- **Direct submission to Senate Commerce or HSGAC.** No public intake exists. Do not write cold.

**Exists but is empty, dormant, or terminated**

- **DHS AI Safety and Security Board — TERMINATED.** Federal Register Vol. 90 No. 48, 13 Mar 2025, docket DHS-2025-0011, effective 7 Mar 2025. The same notice terminated the Homeland Security S&T Advisory Committee, the Cyber Investigations Advisory Board, and CIPAC. **Do not write to this board.**
- **CISA Cybersecurity Advisory Committee** — newest artefacts are a **May 2023** charter and **Nov 2023** bylaws; meeting resources stop at **27 May 2025**; no 2026 meeting notice in the Federal Register. Fifteen months of silence. Not presented as a door.
- **NAIAC** — page updated 22 Jul 2026: *"No meetings are scheduled at this time."* No public-comment mechanism, only membership nomination. **Not a door.**
- **PCAST** — `whitehouse.gov/pcast` returns **HTTP 404**; no Federal Register meeting notice since 31 Jan 2025. No FACA comment window noticed.
- **DHS S&T Test & Evaluation Division** — the single best *topical* match anywhere at DHS ("Advancing the State of the Art and Practice of Test and Evaluation… primary liaison with outside parties"). It publishes **no email, no form, no intake of any kind**. A perfect-fit office with no door is not a door.
- **DHS Prize Competitions** — the one DHS page that explicitly welcomes "citizen inventors" and "hobbyists" (`PrizeAuthority@hq.dhs.gov`), last updated **19 Feb 2025**, listing **no open competition**. Not a live channel.
- **Challenge.gov** — reported sunset 30 Mar 2026, **unverified**; treat as gone.

**No open consultation to file into, anywhere in these institutions**

- **OSTP / EOP:** exhaustive enumeration of all OSTP Federal Register documents (40 records back to 2022) plus all EOP+OMB documents since 2026-01-01 — **zero** open AI comment periods. OSTP's only open period is a National Climate Assessment amendment closing 9 Sep 2026.
- **State:** exactly 8 documents with a comment period open today, every one a Paperwork Reduction Act collection or a passport rule. Zero State RFIs since 1 Jan 2025.
- **DHS/CISA:** of 620 DHS documents since 2026-04-01, exactly two CISA dockets are open (CISA-2026-0133 closing 10 Sep 2026; CISA-2026-0166 closing 19 Oct 2026) — both PRA information collections. **There is no DHS analogue to NIST Zero Drafts.**
- **Congress:** no open RFI at any of the three committees.
- **IARPA:** RFIs page reads *"There are no open RFIs"*; R&D Opportunities reads *"There are currently no open R&D Opportunities"*; Seedlings returns no results.

**Not checked, and therefore not claimed either way:** cia.gov proper; NSA, NGA, DIA public channels; DOE and national-lab AI V&V groups; NASA IV&V external intake; NSF (searched via Federal Register only — no open AI consultation found, and its funding solicitations require an institution regardless). "The CIA has no public technical intake" is **unverified**, not a finding.

---

## 3. SEND ORDER, AND THE EVENT THAT RELEASES EACH STEP

### Step 0 — today, before any send
Choose a licence, commit it, and fix the six documents that assert Apache-2.0. **Release condition for everything below.** This is not a letter task.

### Stage 1 — NOW (§6: named researchers and open consultations)

**1a. NIST Zero Drafts TEVV** → `ai-standards+tevvzd [at] nist.gov`
The only channel that turns this into a **filed, categorised document**, which is §2's whole constraint. No deadline pressure, so it can go the day the licence lands. State the limits in the letter, early — one operator, amendment by quorum an intention rather than a mechanism, unverified audit, verifier runs on the machine it verifies. A reader who is handed those reads the rest as calibrated (§7).

**1b. MAITE GitHub issue** → `github.com/mit-ll-ai-technology/maite/issues`
The §6 "named researcher" tier, in institutional clothing. Frame it as a finding in *their* problem space — "here is a method for proving two independent implementations of a spec agree; MAITE exists to make independently-built T&E tools interoperate; tell me where this breaks" — never as "please evaluate my project."

**1c. COSAiS Slack join** → `overlays-securing-ai [at] list.nist.gov`, subject "Join Overlays Securing AI Slack"
Costs one email. Liveness unproven; treat a non-reply as uninformative, not as rejection.

### Stage 2 — released by *either* of two events

- **Event A (§5, the only one that changes anything):** someone independent reproduces the conformance root `0c398099…0f0ddcef` from `docs/CONFORMANCE_SPEC.json`, in a language that is not Python, sharing no source.
- **Event B (weaker, sufficient for one door):** the Zero Drafts submission is filed and produces *any* traceable result — an acknowledgement, a docket line, a reply.

Released by A **or** B:
- **JATIC front door** (form + `cdao-jatic@groups.mail.mil`) — carrying whatever the MAITE issue produced.
- **CISA OpenSource@cisa.dhs.gov** — carrying a licence and, ideally, a third-party reproduction. Arriving without one asks a federal office to be first mover, which is the tier-skip §6 forbids.
- **IARPA Marketplace** — but only if the production cost in §4 is judged worth it.

### Stage 3 — released by Event B specifically, and by nothing else

- **Sen. Andy Kim** (row 9). The letter has exactly one sentence that makes it routable: *"I filed a submission to NIST's AI Standards Zero Drafts TEVV pilot on [date]. As a member of the Commerce Committee, would your office ask NIST whether the TEVV working group reviewed it?"* Without that sentence it is a constituent with a theory and there is no slot for it. Frame it as **policy correspondence that mentions a filing** — not as agency assistance, which is casework and which Kim's own form excludes (*"only for general comments and not for assistance with a federal agency"*). Filing it as casework gets it closed as non-actionable and burns the channel's one real property, which is that it must be answered.
- **NITRD `nco@nitrd.gov`** — same sentence, same reason. Note honestly that its only useful action is forwarding to co-chairs, one of whom (Martin Stanley, NIST) is already reachable through 1a. This door opens onto a room with one exit that is already unlocked from outside. Low value; send it late or not at all.

### Never, on current facts
OSTP `engagement@`, the whitehouse.gov contact form, the State Department (any route), all three committees directly, In-Q-Tel, DARPA. Sending to any of these does not merely fail — per §6 it consumes the one cold approach that institution will read.

### The mass-send risk, and what is genuinely independent

**A simultaneous send reads as a campaign, not a submission.** The tell is the same letter arriving at several addresses inside one week; the cost is that a recipient who forwards it discovers it has already been forwarded, and the framing collapses from "a person asking one office a specific question" to "a stranger mailing the government." §7's second failure mode applies at the level of the whole map, not just one letter.

**Genuinely coupled — do NOT run in parallel:**
- **1a, 1c, 6 and 7 are all NIST.** Zero Drafts (AI Standards), COSAiS (CSD/ITL), SP 1353 (CSF) and the NVD RFI sit in one agency with plausible staff overlap and a shared reputation. Send **1a alone**, then **1c** after a gap of at least a week with a different, honest framing (COSAiS is *securing* AI systems; Zero Drafts is *testing and evaluating* them — they are adjacent, not the same pitch). Skip 6 and 7 unless answering a numbered question. **Four NIST emails in one week is the campaign failure by itself.**
- **8, 9 and the committees are all downstream of NIST.** Congress oversees the body that can evaluate; NITRD routes to it. Writing to any of them in the same window as 1a inverts the sequence and spends both.
- **2 and 12 are the same program** (MAITE is a CDAO/JATIC product). Issue first, front door second — never both on the same day.

**Genuinely independent — safe to run in parallel:**
- **1a (NIST)**, **1b (MAITE public GitHub)**, and later **4 (CISA)** and **5 (IARPA)** are four separate institutions with four separate intakes, no shared inbox, no shared routing chain, and no plausible reader overlap. Running these concurrently costs nothing.
- **1b in particular is not an institutional send at all** — it is a public issue on a public repository. It carries none of the campaign risk and can go the same day as 1a.

---

## 4. WHAT MUST BE CONFIRMED ON THE DAY, PER RECIPIENT

**NIST Zero Drafts (1a).** Re-open the pilot page and confirm the TEVV topic still exists and the `+tevvzd` address still appears — plus-addressed topic mailboxes are the first thing to change when a pilot is restructured. Confirm no TEVV deadline has appeared. Note the 16 Sep 2026 documentation-draft date is a *different* topic; do not conflate. **Confirm submissions-become-public-record still holds and that everything sent is fit to be public.**

**MAITE (1b).** Check `pushed_at` and that issues are still enabled. Check whether `jdarena66` (or another human) has replied to anything in the last 60 days. The repo's "17 open issues" counter is misleading — **15 are dependabot PRs**; there are 2 open human issues. Read the two most recent human threads before posting so the issue lands in the project's current vocabulary.

**COSAiS (1c).** Re-check the "Updated" stamp on `csrc.nist.gov/projects/cosais`. **If it still reads January 08, 2026, the project has been frozen for eight months and the send is a lottery ticket** — send it anyway, expect nothing, and do not let its silence delay anything else. Confirm the address is still printed on the NIST news release (it is Cloudflare-obfuscated on csrc.nist.gov).

**CISA (4).** cisa.gov pages carry **no last-updated field**, so the page cannot date itself. Date the *office* instead: check `cisa.gov/opensource` for new publications and confirm something has shipped since 26 Aug 2026. Confirm `OpenSource@cisa.dhs.gov` is still on the page. Assume the reader opens LICENSE first.

**IARPA (5).** Four things, all time-sensitive:
1. **The cutoff is the final calendar day of the month at 12:00 noon ET**, and the announcement urges submitting at least three business days early. Today's has passed.
2. **The deliverable is not a letter.** Section VII of the announcement: *"Videos must be no longer than five (5) minutes (5:00) in length"* — a compliance-rejection criterion, not a guideline — plus **a slide package conforming to Appendix C is required alongside it**, plus hard specs (HD 1920×1080, .mp4 under 1.0 GB, Rec709/sRGB).
3. **Four required elements**, one of which is a **pricing model**. "Free, Apache-2.0, no funding request" may be a valid answer but must be written deliberately — and the licence must actually say so first.
4. **UEI is optional at submission** (*"If you do not have a SAM.gov profile at time of video submission, leave this field blank"*) — but **award-stage entity requirements are a separate question and are not resolved.** The assessment is open to him; an award is not established as open.
Also re-confirm the notice is still `latest` (there is a superseded parent record, `6e62317…`) and that the announcement PDF is still attached to it.

**JATIC (12).** Re-check the `Last-Modified` header on `cdao.pages.jatic.net/public/contact/`. Re-check whether `www.ai.mil` has become readable in an ordinary browser — that single page could change the whole CDAO row. **CDAO was realigned under USD(R&E) by a 14 Aug 2025 DepSecDef memo and a new CDAO (Cameron Stanley) took office in January 2026**, so anything addressed to "CDAO" generically is addressed to a moving target. Name the program, never the office.

**NITRD (8).** Confirm `nco@nitrd.gov` and the co-chair list on `nitrd.gov/coordination-areas/ai/` — the argument for writing at all depends on Martin Stanley (NIST) still being a co-chair. **Do not follow `nitrd.gov/contact-us/`**: it 301s to a server-supplied `forms.office.com/g/KbQRyUdgh3`.

**Sen. Kim (9).** Confirm he is still listed on `commerce.senate.gov/members` — that seat is the entire reason this door is chosen. Confirm the topic dropdown still offers Technology or Science. **His subcommittee roster is genuinely unstable across reads; do not cite a subcommittee.** Use his own NJ street address honestly; constituent status is what makes the channel exist, and it should be the first line of the letter.

**Sen. Booker (10).** **His seat is on the ballot in November 2026 and the term expires 3 Jan 2027.** Anything sent after early November may be to a departing office.

**His Representative (11).** Run the ZIP lookup on the day. Two traps: ZIPs straddle districts (house.gov documents the failure mode and says the webmaster will **not** forward messages to offices), and **NJ district boundaries have been redrawn — the lookup returns who represents him now, which changes when the new Congress is sworn in January 2027.** Any name captured today expires then. From now to early November, both chambers are in campaign season, which is the worst possible window for unsolicited technical constituent mail.

**Everything, every time.** Re-read §0. If the LICENSE still says "not yet chosen," nothing on this map should be sent.

---

## 5. THE HONEST BOTTOM LINE

**The single channel most likely to end with somebody independent actually running the verifiers and reporting what they got is the MAITE GitHub issue — `github.com/mit-ll-ai-technology/maite/issues`.**

It is the only channel in this entire map where I can point at a specific human who demonstrably answers technical questions from strangers, with dates: `jdarena66` replied to issue #43 within ten days, and to issue #44 on **27 August 2026** — four days ago — while fifteen dependabot PRs sat ignored since 2024. Automated traffic discarded, human technical questions answered. That is a slow room with one person in it, and one person in the room beats every empty room above.

It also clears every barrier at once: no entity, no clearance, no account beyond GitHub, no docket, no category problem, no campaign risk, no waiting on anyone. And the subject matches exactly — MAITE exists to make independently-built implementations interoperate, which is the same problem "conformance proved by behaviour" solves in a different domain. A stranger there does not need the pitch explained.

**Does anything found here beat the NIST Zero Drafts TEVV channel already in hand? No — and the comparison is between two different jobs, which is worth saying plainly rather than picking a winner.**

- On **§5's criterion** — will a human run the check and report the number — MAITE beats Zero Drafts, and beats everything else found by a wide margin.
- On **§2's criterion** — does a slot exist to put this in — **nothing found beats Zero Drafts, and nothing comes close.** It is the only channel in the map that converts unsolicited mail into a filed submission on a named topic at the agency of jurisdiction. It is also the key that unlocks tier 3: the Kim letter and the NITRD note are both worthless sentences without "I filed on [date]" in them, and both become routable objects with it.

So the honest answer is not a ranking, it is a pairing. **Send both, the same week, and they do not conflict** — one is a public issue on a laboratory's repository, the other a filing at a standards agency; no shared inbox, no shared reader, no campaign smell. Zero Drafts is the filing that makes the rest of the map usable. MAITE is the one with a person on the other end.

And the flat truth underneath all of it, which §8 states already and which this map only confirms: **the letters are not the bottleneck.** Nothing that could be written this week changes any of these outcomes. What changes them is one licence file, one real entry in `peers.txt`, and one stranger reproducing `0c398099…0f0ddcef`. Two of those three are code, and the third is what the two sends above are actually for.