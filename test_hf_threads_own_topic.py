#!/usr/bin/env python3
"""test_hf_threads_own_topic.py -- in a topic WE opened, a reply to the opening
post is addressed to us, and `tools/hf_threads.py --new` must say so.

THE DEFECT (2026-11-09). Discourse leaves reply_to_post_number empty when someone
replies to the topic as a whole (that is, to post #1). addressed_to_us_unanswered
flagged a later post only if it carried reply_to one of our posts, named us, or
came from the person our last post answered. Our last post in our own new topic
191599 was #1, which answers nobody, so nootxlm's #2 -- a direct answer to the
question the topic closed on, 13 minutes after posting -- carried none of the
three and `--new` printed nothing for the topic. It was found only because the
topic was read by hand.

THE GUARD. If post #1 is ours, a later post with no reply_to is a reply to us.
A topic someone else opened is unchanged: a reply_to-less post there is to THEM.

Pure: builds topic dicts in the shape fetch_topic returns; no network.
"""
from __future__ import annotations

import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "tools"))

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else "  -- " + str(detail)))


def topic(*posts):
    return dict(id=1, title="t", url="u", created="c", posts_count=len(posts),
                posts=[dict(n=n, user=u, at="2026-11-09T09:38", reply_to=rt, text=tx)
                       for n, u, rt, tx in posts])


def main():
    import hf_threads as H

    # 1. The 191599 shape: we opened, someone replies to the topic. Must be flagged.
    t = topic((1, "Lawless1987", None, "our question"),
              (2, "nootxlm", None, "your closing question has a direct test"))
    got = H.addressed_to_us_unanswered(t)
    check("HT.1 reply to the topic we opened is NEW TO US", [g["n"] for g in got] == [2], got)

    # 2. Someone else's topic: a reply_to-less post after ours is to the opener, not us.
    t = topic((1, "alice", None, "her topic"),
              (2, "Lawless1987", None, "our reply to alice"),
              (3, "bob", None, "bob replies to alice's topic"))
    got = H.addressed_to_us_unanswered(t)
    check("HT.2 reply to someone else's topic stays unflagged", got == [], got)

    # 3. Our own topic, but the later post replies to a third person: not to us.
    t = topic((1, "Lawless1987", None, "our question"),
              (2, "carol", None, "an answer"),
              (3, "dave", 2, "dave answers carol"))
    got = H.addressed_to_us_unanswered(t)
    check("HT.3 own topic: post replying to someone else is not ours",
          [g["n"] for g in got] == [2], got)

    # 4. Answered already: our later post closes the earlier reply.
    t = topic((1, "Lawless1987", None, "our question"),
              (2, "nootxlm", None, "a test"),
              (3, "Lawless1987", 2, "thanks, running it"))
    got = H.addressed_to_us_unanswered(t)
    check("HT.4 a reply we have answered is not new", got == [], got)

    passed = sum(1 for _, o, _ in RESULTS if o)
    failed = sum(1 for _, o, _ in RESULTS if not o)
    print("")
    print("HT: %d passed, %d failed" % (passed, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:                                             # noqa: BLE001
        traceback.print_exc()
        sys.exit(1)
