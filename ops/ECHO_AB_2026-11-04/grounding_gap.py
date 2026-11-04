"""Seat claim check (ChatGPT's stress test): how many NON-echo ideas are also not grounded in the reply?
Support = fraction of the idea's stems (same _words as the echo guard) that appear in the reply."""
import sys, json, os
sys.path.insert(0, r"C:\Users\Lawre\covenant")
os.chdir(r"C:\Users\Lawre\covenant")
import covenant_improve_extract as EX, covenant_improve_mine as IM

rows = [json.loads(l) for l in open("ops/improve_candidates.jsonl", encoding="utf-8")]
want = {r["id"] for r in rows}
text = {}
for l in open("ops/moltbook_candidates.jsonl", encoding="utf-8"):
    try:
        m = json.loads(l)
    except ValueError:
        continue
    rid = IM._row_id(m)
    if rid in want and rid not in text:
        text[rid] = m.get("text") or m.get("body") or m.get("content") or ""

buckets = {"<0.25": [], "0.25-0.5": [], ">=0.5": []}
for r in rows:
    rep = text.get(r["id"], "")
    if EX.preamble_echo_frac(r.get("idea"), rep) >= EX.ECHO_FRAC:
        continue
    w = EX._words(r.get("idea"))
    if not w:
        continue
    rw = set(EX._words(rep))
    sup = sum(1 for x in w if x in rw) / len(w)
    k = "<0.25" if sup < 0.25 else ("0.25-0.5" if sup < 0.5 else ">=0.5")
    buckets[k].append((round(sup, 2), r.get("kind"), (r.get("idea") or "")[:90]))
for k, v in buckets.items():
    print(k, len(v))
    for x in v[:12] if k != ">=0.5" else []:
        print("   ", x)
