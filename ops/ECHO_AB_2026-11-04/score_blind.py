"""Un-blind the judges' verdicts with the key: per arm, how often the reply really proposes the extracted idea."""
import json, os, re, sys
SP = r"C:\Users\Lawre\AppData\Local\Temp\claude\2265ad57bc179ca4\c46512d5-a6fc-4b03-a23b-3f88ff57742c\scratchpad"
key = json.load(open(os.path.join(SP, "blind_key.json")))
LINE = re.compile(r"(R\d+)\s*:\s*X\s*=\s*(yes|partly|no)\s+Y\s*=\s*(yes|partly|no)\s+proposes_anything\s*=\s*(yes|no)", re.I)
judges = {}
for name in sys.argv[1:]:
    txt = open(os.path.join(SP, "judge_%s.txt" % name), encoding="utf-8").read()
    v = {}
    for m in LINE.finditer(txt):
        r, x, y, p = m.group(1), m.group(2).lower(), m.group(3).lower(), m.group(4).lower()
        k = key[r]
        v[r] = {k["X"]: x, k["Y"]: y, "proposes": p}
    judges[name] = v
    tally = {arm: {"yes": 0, "partly": 0, "no": 0} for arm in ("A", "B")}
    for r in v.values():
        for arm in ("A", "B"):
            tally[arm][r[arm]] += 1
    nop = sum(1 for r in v.values() if r["proposes"] == "no")
    b_on_none = sum(1 for r in v.values() if r["proposes"] == "no" and r["B"] != "no")
    print("%-8s parsed %d/40 | A(v1) %s | B(v2) %s | replies proposing nothing: %d (B still said yes/partly on %d)"
          % (name, len(v), tally["A"], tally["B"], nop, b_on_none))
if len(judges) == 2:
    a, b = list(judges.values())
    common = sorted(set(a) & set(b))
    for arm in ("A", "B"):
        agree = sum(1 for r in common if a[r][arm] == b[r][arm])
        print("agreement on arm %s: %d/%d exact" % (arm, agree, len(common)))
    both_yes = {arm: sum(1 for r in common if a[r][arm] == "yes" and b[r][arm] == "yes") for arm in ("A", "B")}
    print("both judges 'yes':", both_yes)
