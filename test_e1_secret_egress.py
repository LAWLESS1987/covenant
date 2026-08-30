#!/usr/bin/env python3
"""test_e1_secret_egress.py -- E1: no secret survives a trip through an
error message.

WHAT HAPPENED. An adversarial audit on 2026-08-29 found an unauthenticated
remote credential disclosure, and two independent reviewers each tried to
refute it and could not. The chain was five links long and every one of them
was reasonable on its own:

  1. the Google judge passed its key in the URL (`?key=...`) while OpenAI and
     Anthropic pass theirs in headers
  2. requests' raise_for_status() formats "... for url: {self.url}" with NO
     redaction, so any 4xx put the key inside the exception text
  3. the fail-closed handler surfaces that text verbatim -- correctly, since
     a gate that refuses without saying why cannot be operated
  4. the quorum preserves each judge's reasoning verbatim -- also correctly
  5. that message is returned in the 400 body to whoever POSTed, and
     POST /transactions is deliberately not an operator endpoint

Nothing in that list is a mistake by itself. The defect only exists at the
join, which is why a per-file review would never have found it and why this
suite tests the JOIN.

WHAT E1 PINS:
  R*  the redactor: kills labelled secrets, bare key shapes and bearer
      tokens, and still leaves the message diagnosable
  H*  the Google judge takes its key in a HEADER, never the URL -- checked in
      the source of EVERY shipped copy, since the bug existed in four
  L*  THE REGRESSION, end to end: a provider that raises with a key in the
      message must produce a JudgmentResult whose reasoning does not contain
      it. This is the check that would have caught the original.

No network, no key, no node. The judge is driven with a fake that raises.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_unified_v8 as cov   # noqa: E402

results = []
KEY = "AIzaSyD-EXAMPLE-not-a-real-key-000000000"


def check(label, ok, detail=""):
    results.append(bool(ok))
    print(f"{'ok  ' if ok else 'FAIL'}  {label}"
          f"{'' if ok else '  ' + str(detail)[:160]}", flush=True)


def main():
    print("E1 -- no secret survives a trip through an error message\n")
    red = cov._redact_secrets

    # ---- R: the redactor --------------------------------------------------
    url = (f"400 Client Error: Bad Request for url: https://"
           f"generativelanguage.googleapis.com/v1beta/models/gemini:"
           f"generateContent?key={KEY}")
    out = red(url)
    check("R1 THE ORIGINAL LEAK SHAPE: a key in a URL query string is gone",
          KEY not in out, out[-70:])
    check("R2 ...and the message is still diagnosable -- the status, the "
          "reason and the host all survive",
          "400" in out and "Bad Request" in out
          and "googleapis.com" in out, out[:80])

    check("R3 a bearer token is redacted",
          "abcdefghijklmnop123456" not in
          red("401 Unauthorized: Authorization: Bearer "
              "abcdefghijklmnop123456"), "")
    check("R4 a bare OpenAI-shaped key with no label is redacted",
          "sk-abcdefghijklmnopqrst" not in
          red("error with sk-abcdefghijklmnopqrst in it"), "")
    check("R5 a bare Google-shaped key with no label is redacted",
          KEY not in red(f"unexpected {KEY} appeared"), "")
    check("R6 labelled secrets are redacted whatever the label",
          all(s not in red(f"{lbl}=SUPERSECRETVALUE123")
              for lbl, s in (("api_key", "SUPERSECRETVALUE123"),
                             ("token", "SUPERSECRETVALUE123"),
                             ("password", "SUPERSECRETVALUE123"))), "")
    check("R7 ordinary text is left alone -- a redactor that blanks "
          "everything is one nobody will keep",
          red("connection refused to 127.0.0.1:5000")
          == "connection refused to 127.0.0.1:5000", red("connection refused"))
    check("R8 empty and None-ish input do not raise",
          red("") == "" and red(None) is None, "")

    # ---- H: the key goes in a header, in every shipped copy ---------------
    copies = [os.path.join(HERE, "covenant_unified_v8.py"),
              os.path.join(HERE, "pending-v8.38", "covenant_unified_v8.py"),
              os.path.join(HERE, "pending-v8.38",
                           "covenant_unified_v8.PROJECT-8e04a293efd9.py"),
              os.path.join(HERE, "launch", "covenant-v8.37",
                           "covenant_unified_v8.py")]
    present = [c for c in copies if os.path.exists(c)]
    check("H1 every shipped copy of the core is present to check",
          len(present) >= 2, len(present))
    bad = []
    for c in present:
        src = open(c, encoding="utf-8").read()
        # the live call site: a generativelanguage URL that carries ?key=
        for m in re.finditer(r"generativelanguage\.googleapis\.com[^\n]*", src):
            line = m.group(0)
            if "?key=" in line or "key={self.api_key}" in line:
                bad.append(os.path.basename(c))
    check("H2 NO copy puts the key in the URL -- the bug was in four files, "
          "so fixing one would have left three",
          not bad, bad)
    for c in present:
        src = open(c, encoding="utf-8").read()
        if "generativelanguage" in src and "x-goog-api-key" not in src:
            bad.append(os.path.basename(c) + " (no header)")
    check("H3 ...and each one passes it as x-goog-api-key instead",
          not bad, bad)

    # ---- L: the regression, end to end ------------------------------------
    class _Boom(cov.GoogleJudge if hasattr(cov, "GoogleJudge")
                else cov._APIReasoningJudge):
        provider = "google"
        env_var = "GOOGLE_API_KEY"
        judge_id = "google:test"

        def _call(self, data, principles):
            # exactly what requests raises when the key is in the URL
            raise RuntimeError(
                f"400 Client Error: Bad Request for url: https://"
                f"generativelanguage.googleapis.com/v1beta/models/"
                f"gemini-1.5-pro:generateContent?key={KEY}")

    j = _Boom(api_key=KEY)
    r = j.evaluate({"memo": "anything"}, ["do no harm"])
    check("L1 the judge still FAILS CLOSED on a provider error",
          r.violates is True and r.infrastructure_failure is True,
          (r.violates, r.infrastructure_failure))
    check("L2 THE REGRESSION: the key does NOT appear in the reasoning that "
          "is returned to whoever submitted the transaction",
          KEY not in r.reasoning, r.reasoning[-90:])
    check("L3 ...and the operator can still see WHY it refused -- redaction "
          "must not cost the diagnosis",
          "fail-closed" in r.reasoning and "google" in r.reasoning
          and "400" in r.reasoning, r.reasoning[:90])
    check("L4 no fragment of the key survives either (not just the whole "
          "string)",
          "AIzaSyD" not in r.reasoning, r.reasoning[-90:])

    p = sum(results)
    print(f"\nE1: {p}/{len(results)} passed")
    return 0 if p == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
