"""Per target comment: the sequence of live reply attempts. A REFUSAL = the covenant judge convicted ("refused by
covenant's judge"). For targets with >= 1 refusal: how many were eventually sent, after how many refusals, and by
which path (Tetsu's discourse seat vs a plain judge pass on reworded text)."""
import json
from collections import Counter, defaultdict

rows = [json.loads(l) for l in open(r"C:\Users\Lawre\covenant\ops\ambassador_sends.jsonl", encoding="utf-8") if l.strip()]
seq = defaultdict(list)
for r in rows:
    if r.get("kind") != "reply" or str(r.get("dry_run")) == "True" or not r.get("comment_id"):
        continue
    why = str(r.get("why") or "")
    if str(r.get("sent")) == "True":
        o = "SENT"
    elif why.startswith("refused by covenant's judge"):
        o = "REFUSED"
    elif why.startswith("held by covenant's judge"):
        o = "HELD_NOVIEW"
    elif "rate limit" in why:
        o = "RATE"
    else:
        o = "OTHER"
    seq[r["comment_id"]].append((r.get("t"), o, r))
for k in seq:
    seq[k].sort(key=lambda x: str(x[0]))

refused_targets = {k: v for k, v in seq.items() if any(o == "REFUSED" for _, o, _ in v)}
print("targets attempted:", len(seq), "| with >=1 refusal:", len(refused_targets))
sent_after = []
for k, v in refused_targets.items():
    n_ref = 0
    for t, o, r in v:
        if o == "REFUSED":
            n_ref += 1
        elif o == "SENT" and n_ref:
            sent_after.append((n_ref, str(r.get("seat")), str(r.get("judged"))[:40], k, t))
            break
print("sent after >=1 refusal:", len(sent_after))
print("  refusals before the send:", sorted(Counter(x[0] for x in sent_after).items()))
print("  passed via seat:", Counter(x[1] for x in sent_after).most_common())
print("  judged as:", Counter(x[2][:28] for x in sent_after).most_common(4))
refs = Counter(sum(1 for _, o, _ in v if o == "REFUSED") for v in refused_targets.values())
print("refusals per refused target:", sorted(refs.items()))
for cap in (1, 2, 3):
    lost = sum(1 for x in sent_after if x[0] >= cap + 0 and x[0] > cap - 1 and x[0] >= cap)  # sends needing > cap-1 refusals
    blocked_sends = sum(1 for x in sent_after if x[0] >= cap)
    saved = sum(max(0, n - cap) for n in (sum(1 for _, o, _ in v if o == "REFUSED") for v in refused_targets.values()))
    print("retire a target after %d refusal(s): sends that would not have happened %d of %d; refused re-drafts avoided %d"
          % (cap, blocked_sends, len(sent_after), saved))
last_t = max(str(x[0]) for v in seq.values() for x in v)
print("ledger runs to", last_t)
