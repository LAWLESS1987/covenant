"""Score the side-by-side. B's grounding is RE-SCORED with the current grounded_quote (the run loaded an earlier,
punctuation-strict version mid-build), and B's kind is recomputed from that. Then: echo / grounded / none rates,
offline vet of each arm's gaps (what would reach the backlog or escalate), arm C vs the vet, and a BLIND sheet."""
import sys, os, json, random, statistics
sys.path.insert(0, r"C:\Users\Lawre\covenant")
os.chdir(r"C:\Users\Lawre\covenant")
import covenant_improve_extract as EX, covenant_improve as CI

SP = r"C:\Users\Lawre\AppData\Local\Temp\claude\2265ad57bc179ca4\c46512d5-a6fc-4b03-a23b-3f88ff57742c\scratchpad"
recs = [json.loads(l) for l in open(os.path.join(SP, "ab_echo_results.jsonl"), encoding="utf-8")]
p2 = os.path.join(SP, "ab_echo_results2.jsonl")
if os.path.exists(p2):                                   # the paced rerun of the 429'd replies replaces them by id
    re2 = {json.loads(l)["id"]: json.loads(l) for l in open(p2, encoding="utf-8")}
    recs = [re2.get(r["id"], r) for r in recs]
recs = [r for r in recs if "kind" in (r.get("A") or {}) and (r.get("B") or {}).get("kind")]   # paired only


def kind_b(b, rep):
    if not b or "kind" not in b:
        return None
    g = EX.grounded_quote(b.get("quote"), rep[:EX.SEEN_CHARS])
    raw_kind = EX._parse_v2(b.get("raw", "")).get("kind")
    if raw_kind in ("gap", "stance") and not g:
        return "ungrounded", g
    if EX.preamble_echo_frac(b.get("idea"), rep) >= EX.ECHO_FRAC:
        return "echo", g
    return raw_kind, g


out = {"n": len(recs)}
A, B = {}, {}
vetA, vetB, cmp_c = {}, {}, []
idea_a = idea_b = 0
supA, supB = [], []
retried = rescued = 0
for r in recs:
    rep = r["reply"]
    a = r.get("A") or {}
    ka = a.get("kind")
    A[ka] = A.get(ka, 0) + 1
    if a.get("idea"):
        idea_a += 1
        supA.append(EX.support_frac(a["idea"], rep))
    if ka == "gap":
        v = CI.vet({**a, "kind": "gap"})["status"]
        vetA[v] = vetA.get(v, 0) + 1
    b = r.get("B") or {}
    kb = kind_b(b, rep)
    if kb is None:
        B["door-fail"] = B.get("door-fail", 0) + 1
        continue
    kb, g = kb
    r["_kb"] = kb
    B[kb] = B.get(kb, 0) + 1
    if b.get("retried"):
        retried += 1
        if g:
            rescued += 1
    if b.get("idea") and kb in ("gap", "stance"):
        idea_b += 1
        supB.append(EX.support_frac(b["idea"], rep))
    if kb == "gap":
        v = CI.vet({"kind": "gap", "maps": "", "idea": b["idea"], "test": b.get("test", "")})["status"]
        vetB[v] = vetB.get(v, 0) + 1
        if r.get("C_kind"):
            cmp_c.append((r["C_kind"], v))
out["A kinds"] = A
out["B kinds (re-scored)"] = B
out["A echo rate"] = "%d/%d" % (A.get("echo", 0), sum(A.values()))
out["B echo rate"] = "%d/%d" % (B.get("echo", 0), sum(v for k, v in B.items() if k != "door-fail"))
out["B retried / of those grounded after retry"] = "%d / %d (retry ran under the stricter check)" % (retried, rescued)
out["ideas carried forward A (any non-empty idea) vs B (grounded gap/stance)"] = (idea_a, idea_b)
out["median support_frac A / B"] = (round(statistics.median(supA), 2) if supA else None,
                                   round(statistics.median(supB), 2) if supB else None)
out["offline vet of gaps A"] = vetA
out["offline vet of gaps B"] = vetB
out["arm C model label vs vet (C_kind, vet)"] = {str(k): cmp_c.count(k) for k in set(cmp_c)}
print(json.dumps(out, indent=1))

# BLIND sheet: one item per reply where either arm produced an idea. X/Y order is random; the key is kept apart.
rng = random.Random(41104)
items, key = [], {}
for i, r in enumerate(recs, 1):
    ia = ((r.get("A") or {}).get("idea") or "").strip() or "(no idea extracted)"
    ib = ((r.get("B") or {}).get("idea") or "").strip() or "(no idea extracted)"
    if ia == "(no idea extracted)" and ib == "(no idea extracted)":
        continue
    pair = [("A", ia), ("B", ib)]
    rng.shuffle(pair)
    key["R%d" % i] = {"X": pair[0][0], "Y": pair[1][0]}
    items.append("R%d. REPLY: %s\n   X: %s\n   Y: %s" % (i, " ".join(r["reply"][:700].split()), pair[0][1], pair[1][1]))
open(os.path.join(SP, "blind_sheet.txt"), "w", encoding="utf-8").write("\n\n".join(items))
json.dump(key, open(os.path.join(SP, "blind_key.json"), "w"), indent=1)
print("blind items:", len(items), "chars:", sum(len(x) for x in items))
