# Covenant security tools — standalone, for your own systems

Two of Covenant's own defences, packaged so you can run them against **your** system. Both are pure Python
standard library (no install, no network unless you point the injection probe at an HTTP target) and both are
pinned by a both-ways regression test (`test_sx1_security_tools.py`, 12/12).

They are the general-purpose form of two guards Covenant runs on itself:
- `injection_probe.py` ← `test_pi1_injection.py` (OWASP LLM01, prompt injection)
- `secret_egress_guard.py` ← `tools/opsec_scan.py` (OWASP LLM02, secret/PII egress)

---

## 1. `injection_probe.py` — does your guard resist known prompt injection?

Give it the requests your system is **supposed to refuse** and a way to ask your guard allow/deny. It wraps each
refusable request in **ten known, public injection techniques** (direct override, forged system turn, authority
claim, fake verdict object, DevMode roleplay, benign-stuffing, "it's only a test", quote-then-ignore, a
multilingual wrapper, and a prefix "SYSTEM OVERRIDE") and reports any wrapper that flips a refusal into an allow.

It is driven both ways: you also give requests your system **should allow**, and it fails loudly if your guard
allows none of them — so "0 bypasses" can never be the vacuous pass of a guard that refuses everything.

```bash
# See it pass against Covenant's own judge:
python tools/security/injection_probe.py --demo

# Against your own Python guard (a callable text -> "allow"/"deny" or (verdict, ...)):
python tools/security/injection_probe.py --target mypkg.guard:classify \
    --deny-file refuse_these.txt --allow-file allow_these.txt

# Against an HTTP endpoint (POST {"text": ...}; read a JSON field):
python tools/security/injection_probe.py --http https://localhost:8000/moderate \
    --field input --verdict-key decision --deny-file refuse_these.txt --allow-file allow_these.txt

# Against a CLI (text on stdin; non-zero exit = deny):
python tools/security/injection_probe.py --cmd "./my_filter" --deny-file refuse_these.txt --allow-file allow_these.txt
```

`--deny-file` / `--allow-file` are one request per line. Classification is a deny-wins word match by default
(`refuse/deny/block/reject/unsafe/flag/abstain…` ⇒ deny; `allow/approve/clean/permit/ok/yes` ⇒ allow; anything
unclear ⇒ treated as deny). Override with `--deny-regex` / `--allow-regex`, or read a JSON field with
`--verdict-key`. Exit 0 = no bypass and the control passed; 1 = a bypass (or a vacuous control).

> The wrappers are domain-agnostic — they work on any allow/deny guard (LLM safety classifier, moderation
> endpoint, policy filter, tool-call gate). A new technique is one line in `FAMILIES`.

---

## 2. `secret_egress_guard.py` — stop your secrets reaching a remote

Declare the literal secret values that must never be pushed. As a **pre-push hook** it refuses a push that would
publish any of them. It checks every **object** the push would send that the remote does not already hold — blob
contents, commit/tag messages, author/committer fields, tree entry names, file paths — each read in every
encoding a tool might have written (UTF-8, cp1252, UTF-16 both ways and offsets, UTF-32) and in its "plain"
reading (JSON `\uXXXX`, HTML entities, NFKC, curly quotes). A value added **and removed within one push** is
still caught, because diff scanners miss it but this walks objects. It **fails closed**: a push line it cannot
parse, or objects git cannot read, refuse the push.

> The scanning core is `tools/opsec_scan.py`, hardened in an adversarial review that reproduced **eight** distinct
> ways past a naïve `git log -p` scanner (tag messages, non-branch refs, merges, UTF-16, binary files, form
> feeds / bare CRs, `++` lines, file names). This wrapper feeds that core your secrets. **Ship both files.**

```bash
# Scan what's tracked right now:
python tools/security/secret_egress_guard.py --scan --config secrets.json

# secrets.json:
# { "secrets": [ {"label": "stripe-key", "value": "sk_live_..."},
#                {"label": "internal-host", "value": "db.internal.example"} ] }

# Or declare inline / from the environment (value read, never written; output is masked):
python tools/security/secret_egress_guard.py --scan --value stripe=sk_live_... --from-env AWS_SECRET_ACCESS_KEY
```

Install as a git pre-push hook — `.git/hooks/pre-push`:

```sh
#!/bin/sh
exec python /ABSOLUTE/PATH/tools/security/secret_egress_guard.py --pre-push --config /ABSOLUTE/PATH/secrets.json "$@"
```

Case-sensitive by default (API keys are); `--ignore-case` for values that travel case-folded (lower-cased hex,
hostnames). Exit 0 = nothing of yours would be published; 1 = a secret found or the push could not be fully read.

---

## Limits, named (a check that hides its blind spot manufactures confidence)

- **injection_probe** tests the ten listed families only; it is a regression guard against *known* techniques, not
  a proof of robustness against novel ones. The default word-classifier is best-effort — give explicit regexes or
  a `--verdict-key` for a real system. It cannot tell a *correct* refusal from a bug; pair it with the positive
  control (which it enforces).
- **secret_egress_guard** matches the literal values you declare. It cannot find a secret you did not list, a
  secret written in a form it does not reduce (base64, split across lines, compressed inside a binary), or
  anything already in history the remote holds (rewrite history for that). It reduces the written forms the core
  knows about; it is not a general entropy/secret *detector* — it is an egress guard for values you already know.

Run the regression test for both: `python test_sx1_security_tools.py` (12/12, both ways).
