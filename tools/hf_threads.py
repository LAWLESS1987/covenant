"""Hugging Face forum look-back: every thread we have posted in, re-runnable.

    python tools/hf_threads.py            # discover, fetch, print the status table
    python tools/hf_threads.py --new      # only replies addressed to us that we have not answered

Discovery, not recall (CLAUDE.md rule 2): the topic list comes from the forum's own
record of what Lawless1987 posted (user_actions, filter 4=topic opened, 5=reply), not
from a list kept here. Two counts that can disagree (rule 3): our posts per the user
record vs our posts found by reading each topic. A gap means a post was deleted,
hidden or is still in moderation -- the tool says so instead of hiding it.

Full thread text (other people's words) goes to private/hf_threads/, which is
gitignored, so it is never republished through the public repo.

What this cannot see (rule 9): private messages and notifications (they need the
signed-in session), posts deleted before the run, and whether a reply that does not
quote or reply-to us is still meant for us -- "addressed to us" is reply_to one of our
posts, a reply to the topic itself in a topic we opened (Discourse leaves reply_to empty
for those), our name in the text, or the next post after ours from someone we answered.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import time
import urllib.request
from pathlib import Path

USER = "lawless1987"
BASE = "https://discuss.huggingface.co"
UA = {"User-Agent": "covenant-hf-lookback"}
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "private" / "hf_threads"


def _get(url: str):
    last = None
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                return json.load(r)
        except Exception as e:  # rate limit or transient: back off
            last = e
            time.sleep(3 * (i + 1))
    raise last


def _text(cooked: str) -> str:
    t = re.sub(r"<br\s*/?>", "\n", cooked)
    t = re.sub(r"</p>|</li>|</h\d>|</blockquote>", "\n", t)
    t = re.sub(r"<[^>]+>", "", t)
    return html.unescape(t).strip()


def our_actions() -> list[dict]:
    rows, off = [], 0
    while True:
        page = _get(f"{BASE}/user_actions.json?username={USER}&filter=4,5&offset={off}")
        got = page.get("user_actions", [])
        if not got:
            return rows
        rows += got
        off += len(got)


def fetch_topic(tid: int) -> dict:
    d = _get(f"{BASE}/t/{tid}.json")
    posts = {p["id"]: p for p in d["post_stream"]["posts"]}
    missing = [i for i in d["post_stream"]["stream"] if i not in posts]
    for k in range(0, len(missing), 20):
        q = "&".join(f"post_ids[]={i}" for i in missing[k:k + 20])
        for p in _get(f"{BASE}/t/{tid}/posts.json?{q}")["post_stream"]["posts"]:
            posts[p["id"]] = p
    plist = sorted(posts.values(), key=lambda p: p["post_number"])
    return dict(
        id=tid, title=d["title"], url=f"{BASE}/t/{d['slug']}/{tid}", created=d["created_at"],
        posts_count=d["posts_count"],
        posts=[dict(n=p["post_number"], user=p["username"], at=p["created_at"],
                    reply_to=p.get("reply_to_post_number"), text=_text(p["cooked"]))
               for p in plist],
    )


def addressed_to_us_unanswered(t: dict) -> list[dict]:
    ours = {p["n"] for p in t["posts"] if p["user"].lower() == USER}
    if not ours:
        return []
    last = max(ours)
    by_n = {p["n"]: p for p in t["posts"]}
    rt = by_n[last]["reply_to"]
    # the person our LAST post answered; their next post may answer us without reply_to
    answered = by_n[rt]["user"] if rt in by_n else None
    # Discourse leaves reply_to empty for a reply to the topic itself (post #1). In a topic
    # we opened, that is a reply to us (2026-11-09: 191599 #2 was missed this way).
    opened = 1 in ours
    out, seen_answered = [], False
    for p in t["posts"]:
        if p["n"] <= last or p["user"].lower() in (USER, "system"):
            continue
        why = ("reply_to our #%d" % p["reply_to"] if p["reply_to"] in ours
               else "reply to our topic" if opened and p["reply_to"] is None
               else "names us" if USER in p["text"].lower()
               else "next post from %s, whom our #%d answered" % (answered, last)
               if p["user"] == answered and not seen_answered else None)
        if p["user"] == answered:
            seen_answered = True
        if why:
            out.append(dict(n=p["n"], user=p["user"], at=p["at"][:16], why=why))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--new", action="store_true", help="only unanswered replies addressed to us")
    a = ap.parse_args()

    acts = our_actions()
    by_user_record: dict[int, set[int]] = {}
    for r in acts:
        by_user_record.setdefault(r["topic_id"], set()).add(r["post_number"])
    OUT.mkdir(parents=True, exist_ok=True)

    total_record = sum(len(v) for v in by_user_record.values())
    total_read = 0
    rows = []
    for tid in sorted(by_user_record):
        t = fetch_topic(tid)
        (OUT / f"{tid}.json").write_text(json.dumps(t, ensure_ascii=False, indent=1), encoding="utf-8")
        ours = sorted(p["n"] for p in t["posts"] if p["user"].lower() == USER)
        total_read += len(ours)
        gap = sorted(by_user_record[tid] ^ set(ours))
        rows.append((t, ours, gap, addressed_to_us_unanswered(t)))
        time.sleep(0.5)

    print(f"our posts: {total_record} by the forum's user record, {total_read} found reading "
          f"{len(rows)} topics" + ("" if total_record == total_read else "  <-- DISAGREE, see gap column"))
    for t, ours, gap, new in rows:
        if a.new and not new:
            continue
        print(f"\n{t['id']}  {t['title'][:70]}\n  {t['url']}\n  posts {t['posts_count']}, ours {ours}"
              + (f", gap {gap}" if gap else ""))
        for n in new:
            print(f"  NEW TO US  #{n['n']} {n['user']} {n['at']}  ({n['why']})")
    print(f"\nsnapshot: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
