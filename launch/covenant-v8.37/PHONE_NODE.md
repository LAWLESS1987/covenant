# A node on the phone, and judges in more places

Two requests, one answer, and a tension worth naming before anything else.

---

## The tension

More judges and more efficiency pull opposite ways, and the numbers are not
small. Every judge is a full model call, **per node**, **per transaction**.

```
1 node,  1 judge   ->  1 verdict     ~17s
2 nodes, 1 judge   ->  2 verdicts    ~34s     (what you are running now)
3 nodes, 3 judges  ->  9 verdicts    ~330s    (what you just asked for)
```

Three nodes each independently judging with three judges is nine model calls
for one transfer, served by one Ollama on one laptop, one at a time. That is
five and a half minutes per transaction.

I am not going to tell you that is efficient. What I can do is make each of
those nine calls as cheap as it can be, and tell you which of them you are
actually buying something with.

---

## Why three judges and not two

`build_semantic_quorum` sets `min_agree=1` and decides by **majority veto**
among the semantic judges: `threshold = ceil(n * 0.5)` dissents blocks. And a
judge that *raises* — unreachable, timed out, model evicted — is counted as a
dissent.

| judges | dissents to block | one judge fails |
|---|---|---|
| 1 | 1 | every transaction rejected |
| **2** | **1** | **every transaction rejected** |
| 3 | 2 | chain keeps running |
| 5 | 3 | two may fail |

**Two judges is strictly worse than one.** You get two things that can each
unilaterally halt the chain instead of one. Verified by killing one:

```
3 judges, 1 dead ->  benign gift ADMITTED   (pc_qwen clean, pc_small clean, dead VIOLATES)
2 judges, 1 dead ->  benign gift REJECTED
```

**The corollary is what makes this affordable.** At 2-of-3 a *weak* judge is
safe: it cannot block a legitimate transfer alone, and it cannot approve theft
alone. The 1.7B that fails two categories of the 37-case suite is dangerous as
a sole judge and perfectly fine as a third vote. So the roster is a ladder,
not three copies of the biggest thing:

```
qwen3:8b    60s per verdict     the one that has to be right
qwen3:4b    34s
qwen3:1.7b  15s                 outvoted if it is wrong
            109s total, vs ~180s for three 8b's
```

Same fault tolerance, 40% less work, and three different sets of weights —
which is real reasoning diversity, not the label diversity `QuorumJudge`'s own
docstring warns about.

Configure it in `judges.json`, then
`COVENANT_JUDGE_PROVIDERS=pc_qwen,pc_mid,pc_small`.

### One setting I had wrong

`OLLAMA_MAX_LOADED_MODELS=1` was correct for a single judge and is actively
harmful for three: each judge evicts the previous one and pays a full model
load. Measured on the three-judge roster:

```
qwen3:8b    13.7s of model load
qwen3:4b     7.3s
qwen3:1.7b   2.7s
            23.7s of pure reload, on EVERY transaction
```

`ollama_tune.bat`, `covenant_install.bat` and `covenant_efficient.bat` now set
**3**. Three models is 9.1 GB resident, which fits your 16 GB with room. That
is the single largest efficiency win available in a multi-judge setup, and it
exists only because the multi-judge setup created the problem.

### The honest limit

All three entries in `judges.json` point at `127.0.0.1`. The *models* differ,
so their blind spots differ — that is worth having, and the suite showed 1.7B
and 8B failing on different cases. But they share one machine. If the laptop
dies, all three judges die together, and every node stops accepting the chain.

Model diversity you have. **Location diversity you do not**, until one of those
URLs points at a second machine.

---

## The phone node

`phone/node-install.sh` (v1) has a hole, and it is the same one that has been
recurring all night: it launches `covenant_unified_v8.py` **directly**, so the
node builds the default judge — no API key, fails closed, rejects everything.
The phone would sit there peered, serving `/chain`, looking healthy, and
silently refusing to replicate a single transaction.

**A replica is not passive.** `covenant_unified_v8.py` line 6647 re-judges
every transaction arriving over P2P, independently. That is correct design —
node B must not trust node A's verdict — but it means every node needs a
working judge or it quietly leaves the chain.

`node-install-v2.sh` fixes it:

- runs `run_with_ollama_judge.py`, not the module directly
- copies the judge files (`covenant_judge_local.py`,
  `covenant_judge_ollama.py`, `run_with_ollama_judge.py`) — v1 did not
- **refuses to install the boot script until the judge has returned one
  correct verdict.** A scheduled node that has never judged anything produces
  silence you would read as good news.

### Where the phone's judge lives

Not on the phone. The 1.7B that fits fails two suite categories, and an 8B on a
phone CPU is minutes per verdict. The phone points at the PC's Ollama.

Over wifi that is the PC's LAN address — but Ollama is bound to loopback (on
purpose; it has no authentication), so it will not answer the phone until you
bind it wider. Over **cellular the LAN option cannot work at all**: your phone
is behind carrier NAT and cannot reach a home PC.

**Use Tailscale on both.** Then `OLLAMA_HOST=<tailnet-ip>:11434` exposes Ollama
to your tailnet only — not the LAN, not the internet — and the phone reaches it
from anywhere. Set `COVENANT_LOCAL_JUDGE_URL` in `~/covenant/node.env` to that
address.

That also gives you the location diversity `judges.json` lacks: point one judge
entry at the phone's own tailnet address if you ever run a model there.

### Ports

`--port N` occupies **three**: `N` (API), `N+1` (P2P), `N+11` (bridge). Nodes
must be 12+ apart, and `--peers` takes each peer's **P2P** port, which is their
API port plus one. Getting it wrong is silent — peer messages hit the peer's
Flask port, Flask answers `400 Bad request version`, nothing is logged on the
sending side, and the nodes look peered while sharing nothing.

```
PC node A   api 5000   p2p 5001   bridge 5011
PC node B   api 5020   p2p 5021   bridge 5031
phone       api 5041   p2p 5042   bridge 5052
```

Phone's `node-peers.conf` gets `<PC>:5001` and `<PC>:5021`. And replication is
not automatic in reverse — the PC nodes need the phone added too:

```
node A --peers 127.0.0.1:5021,<PHONE>:5042
node B --peers 127.0.0.1:5001,<PHONE>:5042
```

### Install

1. Termux, Termux:API, Termux:Boot — **from F-Droid, not Play Store**. Open
   Termux:Boot once; that is what registers it.
2. Copy to the phone's Downloads: `covenant_unified_v8.py`,
   `covenant_client.py`, `covenant_path_pattern.py`, `covenant_judge_local.py`,
   `covenant_judge_ollama.py`, `run_with_ollama_judge.py`, `genesis.json`, and
   optionally `judge_suite.py`, `judge_bench.py`, `judge_config.json`.
3. `cd ~/storage/downloads && bash node-install-v2.sh`
4. `nano ~/covenant/node.env` — set the judge URL.
   `nano ~/covenant/node-peers.conf` — set the PC address.
5. Re-run `node-install-v2.sh`. It will not schedule anything until the judge
   answers correctly once.
6. **Settings → Apps → Termux → Battery → Unrestricted.** This one setting
   decides whether any of it survives. Android kills background work within
   days otherwise, silently, and no script can override it.

---

## What I would actually do

Add the phone as a **third node** before adding a third judge. A third node is
a third copy of the ledger in a different physical place, which is what
survives a laptop failure. A third judge on the same laptop is a third opinion
that dies with the first two.

Judges are cheap insurance against a *wrong* verdict. Nodes are insurance
against *losing the chain*. You are more exposed to the second.
