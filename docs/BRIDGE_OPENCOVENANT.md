# Bridging covenant's gate to another runtime — open-covenant first

Written 2026-09-05 after a read-only, twelve-agent pass over
`github.com/open-covenant/covenant` at commit `343dffc` (each load-bearing
claim reproduced by a second agent). This page says what a bridge can be,
what it cannot, and what was built. It does not claim anything the measurements
did not show.

## What open-covenant is, measured

- A Rust daemon (`covenantd`) with a CLI and SDK: about 307,000 lines across
  50 crates, 3,948 tests, CI green on `main`. Apache-2.0. Pre-1.0: one daemon
  release (`v0.1.0-alpha.1`, 2026-05-28, Linux x86_64 and macOS arm64).
- Authority is three things, none of them a policy language: ed25519-signed
  **capabilities** (dotted actions, a versioned JSON scope, issued only by the
  daemon's own key), TOML **agent manifests** (what an agent wants, not what it
  is granted), and plain-text **intents**.
- Dispatch order: a gitignore-style text filter, a keyword router, capability
  checks, then a subprocess or remote run. An intent no agent matches is not
  refused; it is echoed with status `ok`. Denials come back as HTTP 200 with
  `{"kind":"error"}`.
- **There is no policy engine, no intent manifest, and no plugin, hook or
  webhook by which an outside judge is consulted before an action.** Those
  words appear nowhere in the tree.
- The default runtime, `trusted-local`, is documented by the project as not a
  security boundary. The gVisor sandbox's live CI has failed every run.
- Windows is unsupported and the daemon cannot compile for it (unconditional
  Unix-socket imports). Android/Termux is never mentioned.
- Commit authorship is dominated by automation identities; the project says
  its code comes from an autonomous engineering loop. No maintainers are
  named. The same repository ships a Solana settlement program, USDC payment
  rails, a token, a Robinhood crate, an open pull request to give the daemon a
  trading capability, and a paid maintenance-agent product with an automated
  outreach queue. None of that references this project.

## What "inherit the constitution" would require

For an agent running inside that daemon to be bound by covenant's gate,
the daemon would need a pre-dispatch hook that asks an outside judge and
fails closed on silence. It has none. Adding one is a change to their Rust
code, a pull request into a tree with no named maintainer. Until such a hook
exists, no claim of inheritance is honest, and this project makes none.

## What was built: the gate proxy

`covenant_gate_proxy.py` is an HTTP proxy that sits in front of the daemon's
gateway (`127.0.0.1:8421` by default) and runs every gated request through
covenant's own gate — the node's quorum, judged through the node's sentinel,
so "uncertain" and "not understood" refuse exactly as they do for a
transaction.

| it guarantees | it does not guarantee |
|---|---|
| every `POST /intent`, `/tools/call`, `/a2a/tasks`, `/intents/resume` that reaches the daemon **through the proxy** was cleared by the gate first | anything an agent does **inside** the daemon through the daemon's own socket |
| a judge that errors, hangs past the deadline, or cannot be built refuses; an upstream that is down is reported down, never allowed | that the daemon's own capability checks agree with the gate; they run after it, independently |
| refusals use the daemon's own denial shape, so its SDK and CLI treat them as denials | isolation of the agent process; that is the daemon's runtime, and its default is not a boundary |
| every decision is in an audit file with its verdict and reason, never the judged text | availability: a gate that cannot decide refuses by design |

Pinned by `test_gate_proxy.py` (19 checks against a fake upstream and a mock
sentinel: forwarding, refusal shape, judge error, judge hang, empty text,
non-JSON, unknown routes, oversized body, header pass-through, audit
contents, upstream down). The real quorum's verdicts are pinned by the
existing judge suites; this file pins the plumbing, which is where a bridge
silently becomes a bypass.

**Where the judged text goes.** The proxy uses the node's seat as configured
in `ops/quorum_policy.json`. Under the policy in force on 2026-09-05
(`deferring,semantic`), a request the distilled student cannot clear is
passed to a local Ollama judge if one is running and otherwise to the
project's judge on the GitHub Actions runner, which means **the text of that
request leaves the machine**. The gate's own answer says so in its reasoning
("This payload left the PC"). An operator who cannot accept that egress
must run Ollama locally or set a policy that stops at the student, and must
know that stopping at the student means more refusals, not more allowances.

Not tested: the proxy against a live `covenantd`. That daemon does not run on
the machine this project runs on (Windows 11; the phone node is Android). A
Linux host with the alpha release, or WSL2, would be needed for a live check.
Until then the adapter is written to the wire shapes measured in their source
at `343dffc` (`http.rs`, `covenant-ipc/src/lib.rs`) and nothing more.

## How to run it

    python covenant_gate_proxy.py --listen 127.0.0.1:8422 --upstream http://127.0.0.1:8421
    # point the daemon's clients at 8422 instead of 8421

    python test_gate_proxy.py

## On contacting them

Their security contact is `security@opencovenant.org` (SECURITY.md, with a
PGP key). A `partnerships@` address was suggested to the owner by a third
party and is unverified. Any outreach is the owner's act, after this
repository's own history is clean (`docs/KNOWN_ISSUES.md` issue 15), and
should promise exactly what the table above says.
