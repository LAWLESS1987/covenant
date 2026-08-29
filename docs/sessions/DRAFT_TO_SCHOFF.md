# Draft message to Nickolas Schoff — NOT SENT

Written 2026-08-29. Nothing has been sent to anyone. This is a draft for L to
edit, send, or discard. Contact details are L's to use.

Repo: `github.com/Mycelium-Node-1/UCST-AI`
Paper: *Latent Trajectory Gating* — 10.5281/zenodo.20557465, CC BY 4.0

Two things it asks for, in order of how much they unblock:

1. **A LICENSE file** — without it nothing can be taken, at all.
2. **Provenance of `crates/`** — `Cargo.toml` credits `Manus AI <noreply@manus.local>`.

And it makes an offer that costs neither side anything and needs no repo access.

---

Nick,

I found your UCST-AI repo and read *Latent Trajectory Gating* properly — all
four pages, not the abstract.

I've been building a P2P ledger with an ethics gate on transactions. Reading
your paper I realised the architecture you describe is one I already run, a
layer down the stack. Your Invariant Gating Matrix is my `ReasoningSentinel` —
a hard projection applied before anything crystallises, with violating
candidates dropped rather than corrected. Your Invariant Core is my semantic
judge: a fitted lexicon and axes, deterministic, versioned by a model hash. I
apply it at the protocol layer instead of the logit layer, which is a weaker
claim than yours and needs no access to hidden states.

We disagree on exactly one thing and I think we're both right. You argue
against temperature zero because it flattens contextual processing. My judge
pins temperature 0, top_k 1, fixed seed — because a gate that answers
differently on a retry isn't a gate. I think that's not a contradiction: the
generator may explore, the gate may not. I keep them in separate processes.
Your design puts both inside one forward pass, which leaves you needing to
explain how the gate stays trustworthy while the model is dreaming.

The reason I'm writing: I have measurements for your claim, and they're mixed
in a way I think you'd want.

Your comparison table lists hallucination risk under IAP as "Zero at output."
I ran the equivalent gate over 1,280 phrases, twice, byte-identical. It got 0
false positives on 640 benign payloads — it never wrongly accuses, which is the
harder half. But it missed 100% of covert content outside its fitted
vocabulary. `embezzle the funds` returns clean. So does `defraud the payment`.

The general result, which I don't think is a defect in either of our designs:
`P_C(τ) = τ if τ ⊨ C` is trivially correct and operationally empty, because
everything rides on the completeness of `C` — and `C` is never complete. A
constraint projection doesn't eliminate hallucination risk. It converts it into
constraint-coverage risk. That's still worth doing, because coverage is
enumerable and hallucination isn't. But coverage failure is silent *and*
permissive: an under-covered gate doesn't error, it returns clean.

Which is why I think the single-core version can't be trusted on its own. My
answer is plurality — several judges with different partial `C`, a median
rather than a verdict, and a blend that decays a claim's origin weight as
(1/3)^k per hop. No single invariant core is treated as complete, because none
is.

If you want IAP to be more than an argument, I have a working instance with
numbers attached, and you'd be the only outside reviewer a component of mine
has ever had. That's a fair trade in both directions and it needs no merge, no
licence, and no access to my repo.

Two practical asks if you'd like to go further than talking:

- Your repo has no LICENSE file. The README's "Sovereign Symbiosis" is a stated
  intent, not a licence — under Berne, no licence means all rights reserved, so
  I can't use any of it, however freely you meant it. A LICENSE file fixes that
  in two minutes. Apache-2.0 grants patent rights explicitly, which is the
  usual choice for a protocol.
- `Cargo.toml` credits `Manus AI <noreply@manus.local>` as author of the
  `crates/` tree. If that's generated scaffolding rather than your work, worth
  saying so in the README — it's the kind of thing that becomes a problem later
  rather than now.

Mine isn't licensed yet either, so that cuts both ways and I'm fixing my side.

— L
