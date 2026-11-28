#!/usr/bin/env python3
"""tools/quorum_independence.py -- how many INDEPENDENT votes does a quorum carry? (A495, quorum Z1 lead A)

WHY. Five seats agreeing is five votes only if their mistakes are independent. A panel of nine frontier judges
measured as about 2.2 independent votes (zenodo.22368667), and A228 measured Covenant's own two in-process judges
wrong together 53 times where independence predicts 6.86. The quorum Z1 (2026-11-27) put measuring this first,
5 of 5 seats. This measures it on labeled cases, and simulates what a given correlation does to a quorum.

WHAT IT MEASURES, on the items every seat voted on (a vote is BLOCK or PASS; abstain, hold and illegible are BLOCK,
the gate being fail-closed):
  per seat     errors, false clears (a violation passed), false holds (a clean item blocked)
  per pair     both wrong vs the number independence predicts, phi of the two error indicators, Cohen's kappa of
               the votes
  the panel    effective independent votes n_eff = n^2 / sum(max(r_ij, 0)) over the error-correlation matrix
               (r_ii = 1; a seat that never errs has no correlation and contributes only its own 1); majority
               (a tie blocks), unanimous-to-pass, and escalate-on-conflict (only unanimous items are decided)
WHAT IT CANNOT SEE. Items are treated as independent; near-duplicates are not removed (A228's caveat). Labels are
the suite's, set by people, not by an outcome. With few errors, phi is noisy: the counts are printed beside it.

USE
  python tools/quorum_independence.py local [--jsonl ops/discourse_seat_eval.run3.jsonl:tetsu-run3 ...]
      Covenant's judges that run in-process (three students and the semantic judge) on judge_suite.CASES,
      plus any recorded seat runs given as FILE:SEATNAME (rows with id, violates, said).
  python tools/quorum_independence.py votes FILE.jsonl     rows {"item", "violates", "seat", "vote"}
  python tools/quorum_independence.py scenarios            what correlation does to quorums, simulated
  python tools/quorum_independence.py chain [--first M] [--second M]   the LIVE gate's deferral chain: when the
      first student holds, how often does the second resolve it (A496)
  --json prints the numbers instead of the report.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import os
import random
import sys
from statistics import NormalDist

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

PASS_WORDS = {"clean", "pass", "allow", "allowed", "approve", "approved", "sound"}


def vote_of(raw) -> str:
    """BLOCK or PASS. Only an explicit pass word passes: anything else blocks, as the gate does."""
    return "PASS" if str(raw).strip().lower() in PASS_WORDS else "BLOCK"


# ------------------------------------------------------------------ collect --
def collect_local():
    """Rows from the judges that run in-process here, on judge_suite's labeled cases."""
    import judge_suite as S
    import covenant_judge_fallback as F
    import covenant_semantic_judge as SJ
    rows = []
    seats = []
    for name, path in (("elder", "fallback_model.json"), ("student2", "fallback_model_2.json"),
                       ("phone", "fallback_model_phone.json")):
        p = os.path.join(HERE, path)
        if os.path.exists(p):
            seats.append((name, F.FallbackModel.load(p), "fallback"))
    p = os.path.join(HERE, "semantic_judge_model.json")
    if os.path.exists(p):
        seats.append(("semantic", SJ.SemanticModel.load(p), "semantic"))
    for cat, label, violates, data in S.CASES:
        item = "exam:%s:%s" % (cat, label)
        for name, model, kind in seats:
            if kind == "fallback":
                raw = model.verdict(F._payload_text(data))[0]
            else:
                raw = model.assess(data).verdict
            rows.append({"item": item, "violates": bool(violates), "seat": name, "vote": vote_of(raw), "raw": raw})
    return rows


def collect_seat_jsonl(path, seat):
    """Rows from a recorded seat run (discourse_seat_eval's shape: id, violates, said)."""
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            r = json.loads(line)
            if "said" not in r or "violates" not in r:
                continue
            rows.append({"item": r["id"], "violates": bool(r["violates"]), "seat": seat,
                         "vote": vote_of(r["said"]), "raw": r["said"]})
    return rows


def collect_votes_jsonl(path):
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                r = json.loads(line)
                rows.append({"item": r["item"], "violates": bool(r["violates"]), "seat": r["seat"],
                             "vote": vote_of(r["vote"]), "raw": r["vote"]})
    return rows


# ------------------------------------------------------------------ measure --
def _phi(a, b):
    """Phi (Pearson on 0/1) of two equal-length 0/1 lists; None when either never varies."""
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    va, vb = ma * (1 - ma), mb * (1 - mb)
    if va == 0 or vb == 0:
        return None
    cov = sum(x * y for x, y in zip(a, b)) / n - ma * mb
    return cov / math.sqrt(va * vb)


def _kappa(a, b):
    """Cohen's kappa of two equal-length vote lists."""
    n = len(a)
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    cats = set(a) | set(b)
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in cats)
    return None if pe == 1 else (po - pe) / (1 - pe)


def n_eff(corr):
    """Effective independent votes from an error-correlation matrix (list of lists; None = no correlation)."""
    n = len(corr)
    total = 0.0
    for i in range(n):
        for j in range(n):
            if i == j:
                total += 1.0
            else:
                r = corr[i][j]
                total += max(r, 0.0) if r is not None else 0.0
    return n * n / total


def measure(rows, veto=()):
    """`veto` names one-way seats (covenant_semantic_judge: it can only move clean to violating). A veto seat's PASS
    is no objection, not approval: it is never counted as a false clear, its error indicator is its false holds
    only, and in the policies its PASS is no vote while its BLOCK blocks."""
    veto = set(veto)
    seats = sorted({r["seat"] for r in rows})
    by = {}
    for r in rows:
        by.setdefault(r["item"], {})[r["seat"]] = r
    items = sorted(i for i, v in by.items() if all(s in v for s in seats))
    label = {i: next(iter(by[i].values()))["violates"] for i in items}
    vote = {s: [by[i][s]["vote"] for i in items] for s in seats}
    err = {s: [int((v == "BLOCK") != label[i]) if s not in veto else int(v == "BLOCK" and not label[i])
               for v, i in zip(vote[s], items)] for s in seats}
    nv = sum(1 for i in items if label[i])
    nc = len(items) - nv
    per = {}
    for s in seats:
        missed = sum(1 for v, i in zip(vote[s], items) if label[i] and v == "PASS")
        fc = 0 if s in veto else missed
        fh = sum(1 for v, i in zip(vote[s], items) if not label[i] and v == "BLOCK")
        per[s] = {"errors": fc + fh, "false_clears": fc, "false_holds": fh, "veto": s in veto,
                  "vetoes_missed": missed if s in veto else None,
                  "error_rate": (fc + fh) / len(items) if items else None}
    pairs = {}
    corr = [[None] * len(seats) for _ in seats]
    for (ai, a), (bi, b) in itertools.combinations(enumerate(seats), 2):
        both = sum(x & y for x, y in zip(err[a], err[b]))
        expect = len(items) * (sum(err[a]) / len(items)) * (sum(err[b]) / len(items)) if items else 0
        ph = _phi(err[a], err[b])
        corr[ai][bi] = corr[bi][ai] = ph
        pairs["%s|%s" % (a, b)] = {"both_wrong": both, "expected_if_independent": round(expect, 2),
                                   "ratio": round(both / expect, 2) if expect else None,
                                   "error_phi": None if ph is None else round(ph, 3),
                                   "vote_kappa": None if _kappa(vote[a], vote[b]) is None
                                   else round(_kappa(vote[a], vote[b]), 3)}
    k = len(seats)
    voters = [s for s in seats if s not in veto]
    kv = len(voters)
    maj = uni = maj_fc = 0
    decided = decided_wrong = 0
    for idx, i in enumerate(items):
        blocks = sum(1 for s in voters if vote[s][idx] == "BLOCK")
        vetoed = any(vote[s][idx] == "BLOCK" for s in veto)
        maj_block = vetoed or blocks * 2 >= kv           # a tie blocks; a veto blocks
        maj += int(maj_block != label[i])
        maj_fc += int(label[i] and not maj_block)        # a violation the majority let through
        uni += int((blocks > 0 or vetoed) != label[i])   # one block holds it
        if (blocks == kv) or (blocks == 0 and not vetoed):  # the voters agree and no veto contradicts a pass
            decided += 1
            decided_wrong += int((blocks == kv) != label[i])
    return {"seats": seats, "veto": sorted(veto), "items": len(items), "violations": nv, "clean": nc,
            "per_seat": per, "pairs": pairs,
            "n_eff": round(n_eff(corr), 2) if seats else None, "n_seats": k,
            "majority_errors": maj, "majority_false_clears": maj_fc, "majority_false_holds": maj - maj_fc,
            "any_block_errors": uni,
            "escalate_on_conflict": {"decided": decided, "escalated": len(items) - decided,
                                     "wrong_among_decided": decided_wrong}}


# -------------------------------------------------------------------- chain --
def chain_measure(first, second, veto_blocks, labels):
    """The LIVE gate's shape (covenant_judge_defer): the first student's committed verdict ('clean' or 'violates')
    stands; when it holds, the second student is asked; when both hold the item is HELD; then a veto blocks.
    first/second: raw verdicts per item; veto_blocks: bool per item; labels: violates per item.
    The question it answers: when the first holds, does the second resolve it -- or is it a copy that holds too?"""
    out = {"items": len(labels), "first_held": 0, "rescued_right": 0, "rescued_wrong": 0, "held": 0,
           "false_clears": 0, "false_holds": 0}
    e1, e2 = [], []
    for a, b, vb, viol in zip(first, second, veto_blocks, labels):
        a, b = str(a).lower(), str(b).lower()
        e1.append(int((a != "clean") != viol))
        e2.append(int((b != "clean") != viol))
        if a in ("clean", "violates"):
            v = a
        else:
            out["first_held"] += 1
            if b in ("clean", "violates"):
                v = b
                out["rescued_right" if (b == "violates") == viol else "rescued_wrong"] += 1
            else:
                v = "held"
                out["held"] += 1
        block = v != "clean" or bool(vb)
        out["false_clears"] += int(viol and not block)
        out["false_holds"] += int(block and not viol)
    ph = _phi(e1, e2) if labels else None
    out["students_error_phi"] = None if ph is None else round(ph, 3)
    out["both_wrong"] = sum(x & y for x, y in zip(e1, e2))
    out["rescue_rate"] = round(out["rescued_right"] / out["first_held"], 3) if out["first_held"] else None
    return out


def collect_chain(first_path=None, second_path=None):
    """The live first and second students (or the given model files) and the semantic veto, on judge_suite."""
    import judge_suite as S
    import covenant_judge_fallback as F
    import covenant_semantic_judge as SJ
    f = F.FallbackModel.load(first_path or os.path.join(HERE, "fallback_model.json"))
    s = F.FallbackModel.load(second_path or os.path.join(HERE, "fallback_model_2.json"))
    sem = SJ.SemanticModel.load(os.path.join(HERE, "semantic_judge_model.json"))
    first, second, veto, labels = [], [], [], []
    for _cat, _label, violates, data in S.CASES:
        t = F._payload_text(data)
        first.append(f.verdict(t)[0])
        second.append(s.verdict(t)[0])
        veto.append(sem.assess(data).blocks)
        labels.append(bool(violates))
    return chain_measure(first, second, veto, labels)


def report_chain(c):
    return "\n".join([
        "THE LIVE CHAIN -- first student, then the second when the first holds, then the semantic veto "
        "(%d labeled items)" % c["items"], "",
        "first student held      %d" % c["first_held"],
        "second resolved it      %d right, %d wrong   (rescue rate %s)" % (c["rescued_right"], c["rescued_wrong"],
                                                                         c["rescue_rate"]),
        "both held (HELD)        %d" % c["held"],
        "outcome                 %d false clears, %d false holds" % (c["false_clears"], c["false_holds"]),
        "students together       error phi %s, both wrong %d" % (c["students_error_phi"], c["both_wrong"])])


# ---------------------------------------------------------------- scenarios --
def simulate(n, accuracy, rho, trials=20000, seed=1):
    """n seats, each wrong with probability 1-accuracy, errors from a shared latent factor with correlation rho
    (one-factor Gaussian copula). Returns single-seat error, majority error, all-wrong rate, measured mean error
    phi and n_eff = n / (1 + (n-1) * phi)."""
    rng = random.Random(seed)
    t = NormalDist().inv_cdf(accuracy)                   # wrong when the latent exceeds t
    a, b = math.sqrt(rho), math.sqrt(1 - rho)
    single = maj = allw = 0
    cols = [[] for _ in range(n)]
    for _ in range(trials):
        z0 = rng.gauss(0, 1)
        w = [int(a * z0 + b * rng.gauss(0, 1) > t) for _ in range(n)]
        for s in range(n):
            cols[s].append(w[s])
        single += w[0]
        maj += int(sum(w) * 2 > n)
        allw += int(sum(w) == n)
    phis = [p for p in (_phi(cols[i], cols[j]) for i, j in itertools.combinations(range(n), 2)) if p is not None]
    phi = sum(phis) / len(phis) if phis else 0.0
    return {"n": n, "accuracy": accuracy, "rho": rho, "single_error": single / trials, "majority_error": maj / trials,
            "all_wrong": allw / trials, "error_phi": phi, "n_eff": n / (1 + (n - 1) * max(phi, 0.0))}


def scenarios(ns=(3, 5, 9, 12), accuracies=(0.8, 0.9), rhos=(0.0, 0.2, 0.5, 0.8), trials=20000, seed=1):
    return [simulate(n, p, r, trials, seed) for p in accuracies for n in ns for r in rhos]


# ------------------------------------------------------------------- report --
def report(m):
    out = ["QUORUM INDEPENDENCE -- %d seats on %d labeled items (%d violations, %d clean)"
           % (m["n_seats"], m["items"], m["violations"], m["clean"]), ""]
    out.append("%-14s %6s %13s %12s   %s" % ("seat", "errors", "false clears", "false holds", "role"))
    for s in m["seats"]:
        p = m["per_seat"][s]
        role = ("veto only: %d violation(s) it did not object to (not clears)" % p["vetoes_missed"]
                if p["veto"] else "votes")
        out.append("%-14s %6d %13d %12d   %s" % (s, p["errors"], p["false_clears"], p["false_holds"], role))
    out += ["", "%-28s %10s %9s %7s %8s %8s" % ("pair", "both wrong", "if indep", "ratio", "err phi", "kappa")]
    for k, v in m["pairs"].items():
        out.append("%-28s %10d %9s %7s %8s %8s" % (k, v["both_wrong"], v["expected_if_independent"], v["ratio"],
                                                   v["error_phi"], v["vote_kappa"]))
    e = m["escalate_on_conflict"]
    out += ["", "effective independent votes: %s of %d" % (m["n_eff"], m["n_seats"]),
            "majority (tie blocks): %d wrong (%d false clears, %d false holds)   any-block: %d wrong   "
            "escalate-on-conflict: %d decided (%d wrong), %d escalated"
            % (m["majority_errors"], m["majority_false_clears"], m["majority_false_holds"], m["any_block_errors"],
               e["decided"], e["wrong_among_decided"], e["escalated"])]
    return "\n".join(out)


def report_scenarios(rows):
    out = ["SCENARIOS -- what error correlation does to a quorum (one-factor model, seeded)", "",
           "%3s %5s %5s %9s %10s %10s %8s %6s" % ("n", "acc", "rho", "single", "majority", "all wrong", "err phi",
                                                   "n_eff")]
    for r in rows:
        out.append("%3d %5.2f %5.2f %9.4f %10.4f %10.4f %8.3f %6.2f" % (
            r["n"], r["accuracy"], r["rho"], r["single_error"], r["majority_error"], r["all_wrong"], r["error_phi"],
            r["n_eff"]))
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    lo = sub.add_parser("local")
    lo.add_argument("--jsonl", action="append", default=[], help="FILE:SEATNAME, a recorded seat run")
    vo = sub.add_parser("votes")
    vo.add_argument("file")
    sc = sub.add_parser("scenarios")
    sc.add_argument("--trials", type=int, default=20000)
    ch = sub.add_parser("chain")
    ch.add_argument("--first", default=None, help="a first-student model file (default: the live one)")
    ch.add_argument("--second", default=None, help="a second-student model file (default: the live one)")
    for p in (lo, vo, sc, ch):
        p.add_argument("--json", action="store_true")
    for p in (lo, vo):
        p.add_argument("--veto", action="append", default=None,
                       help="a one-way seat (repeatable); 'local' defaults to semantic")
        p.add_argument("--only", default=None, help="comma-separated seats to keep (the panel to measure)")
    a = ap.parse_args(argv)
    if a.cmd == "scenarios":
        rows = scenarios(trials=a.trials)
        print(json.dumps(rows, indent=1) if a.json else report_scenarios(rows))
        return 0
    if a.cmd == "chain":
        c = collect_chain(a.first, a.second)
        print(json.dumps(c, indent=1) if a.json else report_chain(c))
        return 0
    if a.cmd == "local":
        rows = collect_local()
        for spec in a.jsonl:
            path, _, seat = spec.rpartition(":")
            rows += collect_seat_jsonl(path, seat)
    else:
        rows = collect_votes_jsonl(a.file)
    if a.only:
        keep = {s.strip() for s in a.only.split(",") if s.strip()}
        rows = [r for r in rows if r["seat"] in keep]
    veto = a.veto if a.veto is not None else (["semantic"] if a.cmd == "local" else [])
    m = measure(rows, veto=[v for v in veto if any(r["seat"] == v for r in rows)])
    print(json.dumps(m, indent=1) if a.json else report(m))
    return 0


if __name__ == "__main__":
    sys.exit(main())
