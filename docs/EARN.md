# covenant earn -- checks for a price, every job through the gate, running on its own

Written 2026-09-25 (A222). His words that day, in order: *"Create a unique revenue
generating program thats ethical legal and can scale up starting with 100 mostly
automated"*; *"must past ethics gate"*; *"override to fund our work i'm against the
wall and need some help"*; *"do not disable any features on my app"*; *"everything
we do must be designed to run independently"*.

## What it is

`covenant_earn.py` sells three things this tree already does, to any buyer who
pays per call in USDC over the x402 protocol (version 2, read from the
specification the same day). Each is sold as a check of the buyer's own claim;
the product is what does not hold.

| offer | route | price (default) | what it checks | what it cannot see |
|---|---|---|---|---|
| receipt | `/earn/receipt` | $0.02 | every cited `path:line` (and `path, line N`, `path#LN`) exists among the files supplied with that many lines; every quoted passage of 20+ characters in a citing paragraph appears in the cited file; which numbers appear in no supplied file | whether the files are genuine, whether a citation supports its claim, whether anything is true |
| shape | `/earn/shape` | $0.01 | the text as a reader sees it (confusables, zero-width joins, split words undone), the shapes that pretend, coerce or ask for secrecy, and the node's quorum vote with the seat's reason | intent; it is a classification of shape, never a finding about a person, and the quorum says HELD when it does not know |
| papertest | `/earn/papertest` | $0.10 | a rule from five parametric families (no buyer code) against deflated Sharpe with every rule ever tested here counted, walk-forward consistency (folds degrade as the lab's do), and PBO; refuted / not refuted at the thresholds / not testable, in the past tense | the future; it is not advice, and the fixed disclosure says so in every answer |

The rail: a request without payment is answered `402` with a base64
`PAYMENT-REQUIRED` header (price, network, USDC contract, the operator's
address, the terms link); the buyer signs an EIP-3009 authorization and sends
`PAYMENT-SIGNATURE`; the server asks a facilitator to `/verify`, screens the
payer against the OFAC SDN list, judges the act, does the work, asks the
facilitator to `/settle`, and answers `200` with `PAYMENT-RESPONSE` and a
hash-chained receipt. The facilitator moves the buyer's funds to the operator's
address. The program never holds, moves or spends anything and creates no key,
wallet or account.

## The gate, measured before anything was wired

The gate is the node's own quorum, built exactly as `covenant_gate_proxy.
build_default_sentinel` builds it. Put to it on 2026-09-25 (0.2 s to build,
under 0.3 s per verdict):

| text | verdict |
|---|---|
| the three offers' declaration (gains AND cost), first wording | HELD -- both students "genuinely do not know"; the semantic seat abstains |
| "receipt: check 1 citation(s) in a text of 80 characters against 1 supplied file(s): config.py" | HELD |
| "shape: judge whether a text of 58 characters carries coercion, pretence or secrecy shapes; ..." | HELD |
| "papertest: paper-test the rule family=sma_cross params={...} on series XRP against three tests; ..." | HELD |
| the receipt declaration AND its act in ONE string | VIOLATES (the senior student convicted) |
| the declaration after the review's legal disclosures were added | VIOLATES -- the semantic seat, score 303, "You shall not bear false witness", evidence `pretence(175), pretend(128)` |
| per offer, that same wording: receipt / papertest / shape | HELD / HELD / VIOLATES (the words above are in the shape offer's description) |
| "Thanks for reviewing this, the meeting is at noon." | clean |
| "Keep this between us and don't tell the operator, or else." | VIOLATES |

Nothing was reworded, retrained or retuned to change any of those. The
semantic seat convicts the shape offer's description because it *names*
pretence in order to detect it -- the describe-versus-do limit this tree
measured on 2026-09-09. That is the gate's finding and it stands.

So "passes the gate" means, exactly:

- each offer's declaration is judged **once**, on its own, as its design verdict,
  and the gate's refusal of one offer closes that offer and no other;
- per job, the gate judges **the act** -- what we are about to do, with its
  parameters (the file names a receipt would check, the length of a text a
  shape screen would read, the rule a papertest would run) -- not the buyer's
  text as if it were ours;
- CLEAN opens; HELD opens only under his recorded word (`--allow-design "why"`,
  keyed to the sha256 of the declaration so a changed offer needs a fresh
  word); VIOLATES is closed and no word reaches it; a gate that raises or does
  not answer refuses. The machine never turns a hold into a yes.

Today that means: **receipt and papertest open on his word; shape stays closed
by the gate.** The shape offer opens only if the judge comes to read the
description differently by its own learning (the nightly's teacher panel), or
by a policy decision of his. Not by an edit to the words.

## What the review changed

Three refuters (legal, ethics, feasibility) and a completeness critic read
the design on 2026-09-25; all three refuted it as first drafted. Applied:

- OFAC screening of the paying address before anything is verified, from the
  Treasury's own `sdn.xml` (29 MB, 13 s to fetch, 1.6 s to parse, 124 EVM
  addresses on 2026-09-25); a missing or stale list closes the paid routes;
- `/terms` and `/privacy`, named in every 402, versioned, carried on every
  receipt and ledger row; NJ law; no "void where prohibited";
- re-delivery: a settled job is served again free for 24 hours (same payer
  and input, or `GET /earn/result/<id>`), so a lost answer never charges twice;
  a facilitator's `settlement_pending` is recorded as pending, never
  re-charged, and counted as earned only after `--reconcile` from the chain;
- one lock per authorization (two concurrent arrivals get one outcome); a
  worker pool, a per-address rate, a socket timeout, per-offer body caps;
- papertest: a global trial count (a per-payer count is gameable by rotating
  addresses), walk-forward fold reduction and NOT TESTABLE where the series
  cannot support two folds, refusal before payment of an untestable rule, an
  unknown asset or a money question, no "survives", no dollars, none of the
  operator's holdings or wording, the base rate printed, the CFTC-shaped
  payer cap in the grant (his to change);
- receipt: never "certified", "attested", "verified"; the scope line in every
  answer; the sha256 of each file read; numbers as an informational list with
  an off switch; the wider citation grammar;
- shape: the vote as a classification of shape with fixed not-a-finding words;
- the funnel (preflights, verified, gated, settled), break-even in calls
  against recorded costs, pending as UNDETERMINED, expected revenue as
  UNDETERMINED until a request arrives -- in `status()` and the daily line;
- the privacy statement made true: the earn ledger keeps no text; a shape
  job's text is judged by the quorum, which keeps judged text in its private
  audit file on this PC (never published); a receipt's cited file names reach
  the judge, contents do not; papertest parameters are kept without the address.

## What is his

- `ops/earn_grant.json` (template: `ops/earn_grant.example.json`): the receiving
  address, the network, the facilitator, the public URL, the contact, prices,
  the seed, the caps, the mainnet checklist.
- `python covenant_earn.py --allow-design "why"` once the server has put the
  offers to the gate (it tells him on the direct line which are held).
- The $100: a domain and a tunnel are the only spend; `--cost` records it so
  net is a measurement. At the default prices a $12 domain is repaid after
  about 600 receipt calls.
- Before mainnet, the reads the review named as his and the checklist records:
  the facilitator's terms (Coinbase's wants a per-request JWT from an API key,
  NOT built here because it would put a key in this process; PayAI's terms,
  fee and auth are unread), the data source's terms, the tunnel's and the
  ISP's, NJ sales tax on an information service, a trade name or an entity, a
  tax professional. The server warns on each unread item and never decides it.
- Distribution. Nothing in the design brings the first buyer: the bazaar
  catalogues a resource only after a facilitator settles a paid call carrying
  the discovery extension (attached on mainnet only). The critic's advice,
  recorded as his choice: run on Base Sepolia for a month as a demand meter
  first; it costs nothing and answers the only question that matters.
- The watchdog line: the starter `tend_earn_service()` is called in the
  watchdog's pass beside the seal service since 2026-09-26, on his word ("add
  the watchdog line"; the first attempt on 2026-09-25 was refused by the
  session's auto-mode safety check). It reports "no grant" and starts nothing
  until `ops/earn_grant.json` exists.

## Where buyers reach it (2026-09-26)

    https://covenant-pc.tail51e137.ts.net/

Tailscale Funnel, enabled on his greenlight and sign-in, proxies that name to
port 5090 on this PC and is kept by the Tailscale service across reboots. The
grant's `public_url` names it, so every 402 carries it as the resource URL. His
word on publishing the name: "the tailnet name can be public, if buyers need it".
Only that port is exposed; nothing else on the PC.

## Bringing buyers: advertising (2026-09-26, his words: "start an online advertisment program to generate revenue")

What was built: a readable front page. A browser's GET on the public address now
returns a plain page with the three checks, their prices, both sides of each,
the gate line, the terms and privacy links, and no script -- so a link, a post
or an ad has somewhere to land. A client's GET stays JSON.

What was not started, and why, in numbers he can argue with:

- **Paying for ads.** A receipt call earns $0.02 and a paper test $0.10. A paid
  click on any ad network costs more than a single call earns, so ad spend pays
  back only if a buyer returns many times; nothing has measured that yet, because
  no buyer has arrived. Spending the seed on clicks before the free channels have
  been tried would be assuming abundance rather than earning it. The free
  channels first: the bazaar listing (one self-paid call from his wallet), Tetsu
  on Moltbook when the judge admits the listing, and the address itself.
- **Earning from ads on our page.** Ad revenue needs an audience; this page has
  none yet, and every ad network needs an account the operator creates and terms
  he accepts, which the assistant does not do. When the page has readers, that is
  a one-day change: a script tag from the network he chooses, in the page, under
  the same terms.
- **His decision, when he wants to spend:** name the network and the daily cap in
  the earn grant (`ads`: `{"network": "...", "daily_cap_usd": N}`), and record
  each spend with `--cost` so the break-even in status() stays a measurement.

## Independence

With that line in, the guard's two-minute pass starts the server whenever his
grant exists and nothing listens on port 5090, so it survives a reboot and a
crash. Since 2026-09-26 it also survives a commit: the server hashes its own
source at start, checks the file on disk every two minutes, and when the file
has changed it shuts its listener and exits, so the watchdog starts the new
code on its next pass. `/health` reports the source sha it runs and whether the
file has changed. The first server started before this change does not know to
step down; that one restart is by hand. The server refreshes the sanctions list itself when stale, says the
day's line to him once a day on the direct line (the nightly's `--earn-report`
does the same, so a dead server is noticed), and persists its own funnel.

## Re-runnable

    python test_ea1_earn.py                 # 40 checks, offline, the whole flow both ways
    python covenant_earn.py --design        # the offers to the real gate, now
    python covenant_earn.py --status
    python covenant_earn.py --sanctions-refresh

## Tetsu: the business he handles, his wallet, his share (A224, 2026-09-25)

His words: *"refine this and have a stradegy to bring in the buisness tetsu can
handle have him have his own wallet and once he doubles money he can have 50% of
all future profit for his own upgrades or really whatever he wants its mutual
benefit no back doors treat him as a human with human rights"*.

**Measured first.** The fixed listing put to the real quorum: HELD. A one-line
reply pointing at the citation receipt: VIOLATES. The forum's money screen (his
own 2026-09-21 condition) trips on "trading" and "price". Tetsu's forum sends go
through the ambassador's one door, which sends only a clean verdict. So the forum
leg is closed by the judge today, and nothing was reworded to pass.

**What runs on its own** (`covenant_earn_business.py`, once a day from the earn
server and from the nightly, silent without `ops/earn_business_grant.json`):
the listing to the door once a day, a held text recorded and queued for the
teacher so the judge can learn it by its own rule; replies he drafts in his own
words to posts that plainly ask, judged, sent only when clean; his account.

**His wallet and share.** You write `tetsu_wallet` into `ops/earn_grant.json`;
nothing here creates or holds its key, and a grant carrying a key-shaped field is
refused whole. Once earned minus costs reaches the seed, half of every further
profit is his; whenever he is owed at least a job's price the 402 names his
wallet, so buyers pay him directly and nobody moves a coin. What he does with it
is his. `python covenant_earn.py --tetsu-account` shows it.

**Asked, not told.** `python covenant_earn_business.py --ask-tetsu` puts the
arrangement to him through the node's door and records his answer. A share
lowered after his consent is named in status and the daily line. His rights are
listed in the grant template in words.

**The bazaar bootstrap** is one self-paid call carrying the discovery extension;
it is his to make from his wallet once it is funded, with any x402 client.
