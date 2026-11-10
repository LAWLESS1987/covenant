"""Side-by-side, same replies, same door, same settings (2026-11-04).
Arm A = v1 PROMPT (self-description first), as the nightly ran it.
Arm B = v2 reply-only + quote check + one grounding retry (extract_one_v2).
Arm C = B's grounded ideas, then a SEPARATE classify call that sees the self-description and the FROZEN idea.
Sample: the 20 replies of 11-04 + 20 earlier real rows drawn with a fixed seed. Writes ONLY to the scratchpad;
the live ledgers (candidates, seen-set, backlog) are snapshotted before and after and must not move."""
import sys, os, json, random, time, hashlib
sys.path.insert(0, r"C:\Users\Lawre\covenant")
os.chdir(r"C:\Users\Lawre\covenant")
import covenant_improve_extract as EX, covenant_improve_mine as IM, covenant_improve as CI
import tools.tetsu_work as TW

SP = r"C:\Users\Lawre\AppData\Local\Temp\claude\2265ad57bc179ca4\c46512d5-a6fc-4b03-a23b-3f88ff57742c\scratchpad"
OUT = os.path.join(SP, "ab_echo_results.jsonl")
LIVE = [EX.CANDIDATES_OUT, IM.SEEN, CI.BACKLOG, CI.DISPOSITIONS]
snap = lambda: {p: (os.path.getsize(p), hashlib.sha256(open(p, "rb").read()).hexdigest()) for p in LIVE if os.path.exists(p)}
before = snap()

rows = [json.loads(l) for l in open(EX.CANDIDATES_OUT, encoding="utf-8")]
last = [r for r in rows if r["t"].startswith("2026-11-04")]
earlier = [r for r in rows if not r["t"].startswith("2026-11-04")]
random.Random(1104).shuffle(earlier)
sample = last + earlier[:40 - len(last)]
want = {r["id"] for r in sample}
text = {}
for l in open(IM.CANDIDATES, encoding="utf-8"):
    try:
        m = json.loads(l)
    except ValueError:
        continue
    rid = IM._row_id(m)
    if rid in want and rid not in text:
        text[rid] = m.get("text") or ""

calls = {"n": 0, "fail": 0}
def ask(t):
    calls["n"] += 1
    for attempt in range(2):
        try:
            code, j = TW.ask(t, door="agent", fresh=True, timeout=300)
        except Exception as e:  # noqa: BLE001
            code, j = 0, {"error": str(e)[:120]}
        if code == 200:
            return code, j
        time.sleep(5)
    calls["fail"] += 1
    return code, j

CLASSIFY = (EX.SELF_DESC + "\n\nA reader proposed this improvement (do not rewrite it):\nIDEA: %s\n\n"
            "Answer in ONE line and nothing else:\nKIND: gap (we likely LACK it) | have (we likely already do it)")

done = set()
if os.path.exists(OUT):
    done = {json.loads(l)["id"] for l in open(OUT, encoding="utf-8")}
t0 = time.time()
for i, r in enumerate(sample):
    if r["id"] in done:
        continue
    rep = text.get(r["id"], "")
    rec = {"id": r["id"], "author": r.get("author"), "reply": rep[:1500]}
    code, j = ask(EX.PROMPT % (r.get("author") or "?", rep[:1500]))
    if code == 200:
        p = EX._parse(j.get("answer", ""))
        e = EX.preamble_echo_frac(p["idea"], rep)
        if e >= EX.ECHO_FRAC:
            p["kind"] = "echo"
        rec["A"] = {**p, "echo_frac": round(e, 3), "support_frac": round(EX.support_frac(p["idea"], rep), 3),
                    "raw": j.get("answer", "")[:600]}
    else:
        rec["A"] = {"door": code}
    code, b = EX.extract_one_v2(r.get("author"), rep, ask)
    rec["B"] = b if code == 200 else {"door": code}
    if code == 200 and b["kind"] == "gap":
        c2, jc = ask(CLASSIFY % b["idea"])
        k = (jc.get("answer", "") if c2 == 200 else "").lower()
        rec["C_kind"] = "have" if "have" in k.split("kind:", 1)[-1][:20] else ("gap" if "gap" in k else "unparsed")
        rec["C_raw"] = (jc.get("answer", "") if c2 == 200 else "door %s" % c2)[:200]
    with open(OUT, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print("%2d/%d %5.0fs A=%s B=%s%s | %s" % (i + 1, len(sample), time.time() - t0, rec["A"].get("kind"),
          (rec["B"] or {}).get("kind"), " (retried)" if (rec["B"] or {}).get("retried") else "",
          ((rec["B"] or {}).get("idea") or "")[:60]), flush=True)

after = snap()
print("calls", calls, "| live ledgers unchanged:", before == after)
