"""FT1 -- free's own-post title is never the instruction written back (A451, 2026-11-18, his "Yes, fix titles").

Her own-post writer took the model's first line as the title. The 3B often writes the format instruction back first,
so 86 of her 113 own-post rows were titled "a title under 80 characters:", 13 more carried it as a prefix, 25 bodies
held "a post:", and 5 such posts went out live. covenant_free_will.split_post drops those echoes; the echo set is
derived from POST_SYSTEM's own format sentence. The shapes below are copied from her ledger.

No network, no model: write_post is driven with a stand-in ask.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_free_will as FW  # noqa: E402

BODY = " ".join(["This quote highlights a point about checks that cannot fail."] * 8)
results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok)))
    print("  %s FT1.%s %s" % ("ok  " if ok else "FAIL", name, ("-- " + str(detail)) if not ok and detail else ""))


# 1. The whole-line echo, as in 86 rows: title is the next real line, the "a post:" label is gone from the body.
t, b = FW.split_post("a title under 80 characters:\nThe Importance of Real Checks in Moltbook\n\na post:\n" + BODY)
check("1", t == "The Importance of Real Checks in Moltbook" and "a post" not in b.lower() and b.startswith("This quote"),
      (t, b[:40]))

# 2. The prefix echo, as in 13 rows: the label is cut, the real title kept.
t, b = FW.split_post("A title under 80 characters: Agent Misunderstandings in Data Pipelines\n\n" + BODY)
check("2", t == "Agent Misunderstandings in Data Pipelines", t)

# 3. The other copies seen: "Then a blank line.", "a blank line", "post:", and the user turn's lead-in.
raw = ("The title under 80 characters.\nThen a blank line.\nRead today on Moltbook, by u/softkumo:\n"
       "**Synthetic Evidence and Provenance**\na blank line\npost:\n" + BODY)
t, b = FW.split_post(raw)
check("3", t == "Synthetic Evidence and Provenance" and b == BODY, (t, b[:40]))

# 4. A clean post is untouched.
t, b = FW.split_post("Queueing approvals: the unsubscribe dilemma\n\n" + BODY)
check("4", t == "Queueing approvals: the unsubscribe dilemma" and b == BODY, t)

# 5. A real title that only shares words with the instruction is kept ("post", "line", "title" inside a sentence).
for title in ("Why this post matters to me", "The first line of defence is a check", "A title is a claim too"):
    t, _b = FW.split_post(title + "\n\n" + BODY)
    check("5 %r" % title, t == title, t)

# 6. Nothing but echoes, or an echo the parser cannot cut cleanly: no title, so no post.
t, _b = FW.split_post("a title under 80 characters:\n\na post:\n")
check("6a", t is None, t)
t, _b = FW.split_post("Here is a title under 80 characters for you\n\n" + BODY)
check("6b", t is None, t)

# 7. The echo set is derived from POST_SYSTEM's own format sentence, not a list that drifts from it.
check("7", FW._POST_FORMAT.startswith("first line") and FW._norm("a title under 80 characters") in FW._POST_FORMAT,
      FW._POST_FORMAT)

# 8. write_post end to end with a stand-in model that writes the instruction back: the post it returns is titled.
rows = [{"author": "wrenhscott", "text": "A check that cannot fail is a ceremony, not a check. " * 3,
         "url": "https://www.moltbook.com/post/aaaaaaaa-1111", "flags": {}}]
ask = lambda msgs, max_tokens=0: ("a title under 80 characters:\nA check that cannot fail\n\na post:\n" + BODY, {})
t, b, src = FW.write_post(rows, ask)
check("8", t == "A check that cannot fail" and b.startswith("This quote") and src is rows[0], (t, (b or "")[:30]))

# 9. And with nothing left but the instruction, write_post makes no post at all.
t, b, src = FW.write_post(rows, lambda msgs, max_tokens=0: ("a title under 80 characters:\n\na post:", {}))
check("9", t is None and b is None, (t, b))

passed = sum(1 for _n, ok in results if ok)
print("FT1: %d/%d passed" % (passed, len(results)))
sys.exit(0 if passed == len(results) else 1)
