"""Seat claim check (D3): does an exact-n-gram-from-preamble test catch what the 0.5 overlap catches, and vice versa?
Joins every candidate row to its reply text in ops/moltbook_candidates.jsonl by the miner's own row id."""
import sys, json, re, os
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

def toks(s):
    return re.findall(r"[a-z0-9]+", (s or "").lower())

PRE = toks(EX._PREAMBLE)
def grams(t, n):
    return {tuple(t[i:i + n]) for i in range(len(t) - n + 1)}

out = {"rows": len(rows), "joined": sum(1 for r in rows if r["id"] in text)}
for n in (3, 4):
    pg = grams(PRE, n)
    both = ov_only = ng_only = 0
    ex_ov, ex_ng = [], []
    for r in rows:
        if r["id"] not in text:
            continue
        rep = text[r["id"]]
        ov = EX.preamble_echo_frac(r.get("idea"), rep) >= EX.ECHO_FRAC
        ig = grams(toks(r.get("idea")), n)
        ng = bool({g for g in ig & pg if g not in grams(toks(rep), n)})
        if ov and ng: both += 1
        elif ov: ov_only += 1; ex_ov.append(r.get("idea"))
        elif ng: ng_only += 1; ex_ng.append(r.get("idea"))
    out["n=%d" % n] = {"both": both, "overlap_only": ov_only, "ngram_only": ng_only,
                       "overlap_only_examples": ex_ov[:8], "ngram_only_examples": ex_ng[:8]}
print(json.dumps(out, indent=1))
