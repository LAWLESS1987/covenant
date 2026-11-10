"""Both dedup error rates on the labelled seed (n=10, author-labelled) + the 'have' rate on the v2 ideas from the
side-by-side, for several generic-df cutoffs. Function-word stoplist and co-location are on in every variant."""
import sys, os, json
sys.path.insert(0, r"C:\Users\Lawre\covenant")
os.chdir(r"C:\Users\Lawre\covenant")
import covenant_improve as CI

SP = r"C:\Users\Lawre\AppData\Local\Temp\claude\2265ad57bc179ca4\c46512d5-a6fc-4b03-a23b-3f88ff57742c\scratchpad"
ideas = []
for fn in ("ab_echo_results.jsonl", "ab_echo_results2.jsonl"):
    p = os.path.join(SP, fn)
    if os.path.exists(p):
        for l in open(p, encoding="utf-8"):
            b = json.loads(l).get("B") or {}
            if b.get("idea") and b.get("kind") in ("gap", "ungrounded"):
                ideas.append(b["idea"])
ideas = list(dict.fromkeys(ideas))
for frac in (0.05, 0.10, 0.20, 0.35, 1.01):
    CI.GENERIC_DF_FRAC = frac
    b = CI.benchmark()
    vs = [CI.vet({"kind": "gap", "maps": "", "idea": i, "test": "t"})["status"] for i in ideas]
    print("df cutoff %4.2f | seed: missed dup %s/5, false have %s/5 | v2 ideas: have %d/%d"
          % (frac, len(b["missed_duplicates"]), len(b["false_haves"]), vs.count("have"), len(vs)))
    if frac in (0.20, 1.01):
        for i, v in zip(ideas, vs):
            if v == "have":
                w = CI.vet({"kind": "gap", "maps": "", "idea": i, "test": "t"})["why"]
                print("     have:", i[:55], "|", w.split("(dedup): ", 1)[1][:110])
