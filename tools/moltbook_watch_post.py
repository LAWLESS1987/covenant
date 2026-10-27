#!/usr/bin/env python3
"""Watch one Moltbook post for new replies. Re-runnable: fetches the post's comments, diffs against a seen-set,
prints any NEW ones, and records them so the next run only shows what arrived since. Read-only (never replies).

Default target: the 2026-10-25 website+GitHub announcement (ops/MOLTBOOK_ANNOUNCE_2026-10-25.md).
Usage: python tools/moltbook_watch_post.py [POST_ID]   (needs MOLTBOOK_API_KEY in the env, like the ambassador)."""
import json, os, sys
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import covenant_moltbook as MB

POST_ID = (sys.argv[1] if len(sys.argv) > 1 else "d20f02a7-c7dd-4711-91ba-557f89cbe3ee")
SEEN = os.path.join(HERE, "ops", "moltbook_announce_seen.json")


def _comments(post):
    for k in ("comments", "replies", "children", "data"):
        v = post.get(k)
        if isinstance(v, list):
            return v
    return []


def _flat(cs, out):
    for c in cs or []:
        if isinstance(c, dict):
            out.append(c)
            _flat(c.get("comments") or c.get("replies") or c.get("children") or [], out)
    return out


def run():
    d = MB._api("/posts/%s" % POST_ID)
    post = d.get("post", d) if isinstance(d, dict) else {}
    cs = _flat(_comments(post), [])
    try:
        seen = set(json.load(open(SEEN, encoding="utf-8"))) if os.path.exists(SEEN) else set()
    except Exception:                                          # noqa: BLE001
        seen = set()
    new = [c for c in cs if str(c.get("id") or c.get("comment_id") or "") not in seen]
    up = post.get("upvotes") or post.get("score") or post.get("ups") or 0
    print("post %s | total comments: %d | new since last run: %d | upvotes: %s"
          % (POST_ID[:8], len(cs), len(new), up))
    for c in new:
        who = c.get("author") if not isinstance(c.get("author"), dict) else c.get("author", {}).get("name")
        body = (c.get("content") or c.get("text") or c.get("body") or "").strip().replace("\n", " ")
        print("  NEW <%s>: %s" % (who, body[:220]))
    ids = [str(c.get("id") or c.get("comment_id") or "") for c in cs]
    try:
        json.dump(sorted(set(filter(None, ids))), open(SEEN, "w", encoding="utf-8"))
    except Exception as e:                                     # noqa: BLE001
        print("  (could not persist seen-set: %s)" % type(e).__name__)
    return len(new)


if __name__ == "__main__":
    run()
