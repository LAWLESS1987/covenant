"""Checks of Claude-seat claims: echo vs reply length (truncation at 1500), whether scoring against the FULL reply
(the model saw only [:1500]) hides echoes, MAPS contamination, and disposition counts."""
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
        text[rid] = m.get("text") or ""

# 1. echo rate by reply length
b = {"<=1500": [0, 0], ">1500 (truncated)": [0, 0]}
flip = []
maps_echo = 0
for r in rows:
    rep = text.get(r["id"], "")
    k = "<=1500" if len(rep) <= 1500 else ">1500 (truncated)"
    full = EX.preamble_echo_frac(r.get("idea"), rep)
    seen = EX.preamble_echo_frac(r.get("idea"), rep[:1500])
    b[k][1] += 1
    if seen >= EX.ECHO_FRAC:
        b[k][0] += 1
    if seen >= EX.ECHO_FRAC > full:
        flip.append((round(full, 2), round(seen, 2), (r.get("idea") or "")[:80]))
    if EX.preamble_echo_frac(r.get("maps"), rep[:1500]) >= EX.ECHO_FRAC:
        maps_echo += 1
print("echo rate by reply length (scored on what the model SAW):", {k: "%d/%d" % tuple(v) for k, v in b.items()})
print("echo only when scored on the seen [:1500] (missed by scoring the full reply):", len(flip))
for x in flip:
    print("   ", x)
print("rows whose MAPS line is >=0.5 preamble echo:", maps_echo, "of", len(rows))
man = [r for r in rows if "raw-source manifest" in (r.get("idea") or "")]
for r in man:
    print("manifest row maps:", r.get("maps"), "| kind:", r.get("kind"))
p = "ops/have_dispositions.jsonl"
print("dispositions file:", os.path.exists(p), sum(1 for _ in open(p, encoding="utf-8")) if os.path.exists(p) else 0)
bl = [json.loads(l) for l in open("ops/improve_backlog.jsonl", encoding="utf-8")]
from collections import Counter
print("backlog vet verdicts:", Counter(x.get("vet") for x in bl))
