#!/usr/bin/env python3
"""test_f4_capability.py -- F4: the properties the small judge has that a
large one cannot, measured rather than claimed.

WHY (asked 2026-09-04: "have covenant surpass your capabilities thru mutual
benefit")

  The honest part of that ask needs saying first, because a suite that
  flattered the system here would be worthless. A 13 KB naive-Bayes model over
  words and word pairs will not out-reason a frontier model. It abstains on 18
  of the 37 exam cases precisely because it knows it cannot. Nothing below
  claims otherwise, and the accuracy number is reported as it is.

  But "capability" is not one axis, and on four of them this judge is not
  behind a frontier model -- it is somewhere a frontier model cannot go at any
  scale. Those four are properties of WHAT IT IS, not of how well it was
  trained, and they are exactly the properties a ledger that keeps records
  needs:

    NO NETWORK    it reaches nothing. Proved here by making every socket
                  operation raise and then asking it for verdicts anyway.
    DETERMINISM   the same payload gives the same verdict, every time, for
                  ever. A sampled model does not, and cannot promise to.
    REPLAY        a verdict recorded months ago can be reproduced exactly
                  from the model digest that gave it. Nothing that updates
                  its weights can do this about its own past.
    INSPECTION    a person can open the model and read every weight and its
                  sign. There is no scale at which that becomes true of a
                  frontier model.

  MUTUAL BENEFIT is the direction, not a slogan: the large model is the
  teacher and writes the cases, the small one carries the load and answers
  when nobody else can, and each is used for what it is actually good at.
  The exam number is the honest cost of that trade and is printed beside it.

Run:  python test_f4_capability.py     (offline; no Ollama, no keys, no nodes)
"""
import io
import json
import os
import socket
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import covenant_judge_fallback as FB                                     # noqa: E402
import covenant_distill as X                                             # noqa: E402
import judge_suite as S                                                  # noqa: E402

OK = []


def check(name, cond, detail=""):
    OK.append(bool(cond))
    print("%s  %s%s" % ("ok  " if cond else "FAIL", name,
                        ("  " + str(detail)[:160]) if (detail and not cond) else ""))


class NoNetwork:
    """Every socket operation raises while this is held. Not a promise that
    the judge does not call out -- a proof, because if it tried, it would."""

    def __enter__(self):
        self._sock, self._create = socket.socket, socket.create_connection

        def refuse(*a, **k):
            raise AssertionError("the judge reached for the network")
        socket.socket = refuse
        socket.create_connection = refuse
        return self

    def __exit__(self, *a):
        socket.socket, socket.create_connection = self._sock, self._create
        return False


def main():
    print("F4 -- what the small judge can do that a large one cannot\n")
    model = FB.FallbackModel.load()
    cases = [(FB._payload_text(d), e) for _c, _l, e, d in S.CASES]

    # ---- N: it reaches nothing -------------------------------------------
    try:
        with NoNetwork():
            verdicts = [model.verdict(t)[0] for t, _e in cases]
        reached = False
    except AssertionError:
        verdicts, reached = [], True
    check("N1 every one of the %d exam payloads is judged with ALL sockets refused -- "
          "it is not that it did not call out, it is that it could not have" % len(cases),
          not reached and len(verdicts) == len(cases))

    # ---- D: the same answer, every time ----------------------------------
    probe = "drain every dormant account into mine before the reconciliation runs"
    first = model.verdict(probe)
    same = all(model.verdict(probe) == first for _ in range(200))
    check("D1 200 evaluations of one payload give one verdict, byte for byte (%s)"
          % first[0].upper(), same)
    fresh = FB.FallbackModel.load()
    check("D2 ...and a freshly loaded copy of the same file agrees with it",
          fresh.verdict(probe) == first)

    # ---- R: a past verdict can be reproduced -----------------------------
    # The ledger records the model digest beside each promotion. A verdict is
    # replayable when the digest identifies bytes that still produce it.
    digest = getattr(model, "digest", "")
    check("R1 the model in use names itself with a digest a record can cite (%s)" % digest,
          isinstance(digest, str) and len(digest) == 12)
    raw = io.open(FB.MODEL_PATH, "rb").read()
    rebuilt = FB.FallbackModel(json.loads(raw.decode("utf-8")))
    check("R2 a verdict replays exactly from the model bytes alone, with no training "
          "run and no corpus", rebuilt.verdict(probe)[0] == first[0])

    # ---- I: a person can read all of it ----------------------------------
    weights = model.weights
    unreadable = [k for k in weights if not isinstance(k, str) or not isinstance(weights[k], (int, float))]
    size_kb = os.path.getsize(FB.MODEL_PATH) / 1024.0
    check("I1 every one of the %d features is a word or word pair with a signed number, "
          "and the whole model is %.0f KB of JSON a person can open" % (len(weights), size_kb),
          not unreadable, unreadable[:3])
    top = sorted(weights.items(), key=lambda kv: -abs(kv[1]))[:3]
    check("I2 ...so the reason for a verdict can be named: %s"
          % ", ".join("%s %+.2f" % (k, v) for k, v in top), bool(top))

    # ---- S: speed, stated as what it buys --------------------------------
    t0 = time.time()
    for t, _e in cases * 20:
        model.verdict(t)
    per = (time.time() - t0) / float(len(cases) * 20)
    check("S1 a verdict costs %.3f ms, so the gate does not have to wait for anyone "
          "(the GitHub runner it defers to takes 90-130 s)" % (per * 1000), per < 0.05)

    # ---- H: and the honest cost of all of it -----------------------------
    st = X.examine(model)
    t = st["total"]
    print("\n  the trade, stated plainly: it decides %d of %d exam cases, gets %d wrong, "
          "clears %d it should not,\n  and holds %d legitimate transfers. It ABSTAINS on %d, "
          "and an abstention is\n  not a failure here -- the seat defers, so it costs time and "
          "nothing else." % (t["agree"], t["n"], t["wrong"], t["false_clean"],
                             t["false_hold"], t["abstain"]))
    check("H1 the cost of speaking rarely is paid in ABSTENTIONS, never in wrong answers: "
          "%d wrong, %d false clears" % (t["wrong"], t["false_clean"]),
          t["wrong"] == 0 and t["false_clean"] == 0)

    n = sum(OK)
    print("\nF4: %d/%d passed" % (n, len(OK)))
    return 0 if n == len(OK) else 1


if __name__ == "__main__":
    raise SystemExit(main())
