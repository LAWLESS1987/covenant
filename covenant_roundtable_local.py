#!/usr/bin/env python3
"""covenant_roundtable_local.py -- put the same message to the covenant's own judge
that was put to the other AI systems, and keep its answer beside theirs.

The covenant's local model (the ethics judge the nodes pin) reads the message with
the covenant's own system prompt (binding text, constitution I-II, memory, live
state) and answers the same three questions. It has no web access here, so it can
only answer from the text and from what it knows of its own repository -- which is
the honest position the message asks every reader to state.

USE
  python covenant_roundtable_local.py private/ROUNDTABLE_MESSAGE_2026-09-03.txt
Appends to private/AI_ROUNDTABLE_<date>.md under a "covenant (local judge)" heading.
LICENCE: public domain.
"""
from __future__ import annotations

import io
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_chat as cc  # noqa: E402


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__); return 0
    msg = io.open(sys.argv[1], encoding="utf-8").read()
    state = cc.live_state()
    system = cc.system_prompt(state) + (
        "\n\nYou are answering as the covenant itself, from this machine, with no web access. "
        "Say what you can check from the repository you run in and what you cannot. Name one "
        "thing you filled in yourself. A negative answer is kept, not argued away.")
    t0 = time.time()
    text = cc.chat([{"role": "system", "content": system}, {"role": "user", "content": msg}],
                   timeout=1500)
    took = time.time() - t0
    out = os.path.join(HERE, "private", "AI_ROUNDTABLE_%s.md" % time.strftime("%Y-%m-%d"))
    block = ("## covenant (local judge %s, on this machine, no web) -- %.0fs\n\n"
             "Notable: the only reader that runs inside the repository it is asked about, and the "
             "only one with no way to fetch anything. Its answer is what the text plus its own "
             "memory support.\n\n" % (cc.MODEL, took))
    block += "\n".join("> " + l for l in (text or "(no answer)").splitlines()) + "\n\n"
    io.open(out, "a", encoding="utf-8").write(block)
    print(text or "(no answer)")
    print("-- appended to", out, "in %.0fs" % took)
    return 0 if text else 2


if __name__ == "__main__":
    raise SystemExit(main())
