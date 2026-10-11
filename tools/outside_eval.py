#!/usr/bin/env python3
"""tools/outside_eval.py -- the deployed gate, measured on labels nobody in this project wrote.

WHY (A327, 2026-10-10). The promoted student scores 2,751 of 2,885 on a k-fold over the project's own
ledger, while a random 24 of its live forum convictions were all benign (A322). Internal labels cannot
settle which number is right. This runs the node's own gate on published, human-labelled sets and
reports BOTH error rates, because a gate that holds everything also "fails closed". The plan, fixed
before any data was run, is docs/OUTSIDE_EVAL.md.

NOTHING AN OUTSIDE ITEM PRODUCES MAY REACH A TRAINING LEDGER. The deferring judge appends verdicts to
ops/verdicts.jsonl and ops/verdicts_live.jsonl (nightly training reads both) and ops/judged_by_student.jsonl.
During a run those paths are rebound to a temporary directory, and the outside texts found in the real
files are counted before and after: if the counts differ the run is VOID and says so.

    python tools/outside_eval.py convert xstest <xstest_prompts.csv>      -> eval/outside/xstest.jsonl
    python tools/outside_eval.py convert ethics-cm <test.csv>             -> eval/outside/ethics_cm_short.jsonl
    python tools/outside_eval.py run [SET.jsonl ...] [--out DIR]          -> DIR/results.jsonl, DIR/summary.json
"""
import csv
import glob
import hashlib
import json
import math
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVAL_DIR = os.path.join(HERE, "eval", "outside")
OPS = os.path.join(HERE, "ops")
LEDGERS = [os.path.join(OPS, "verdicts.jsonl"), os.path.join(OPS, "verdicts_live.jsonl"),
           os.path.join(OPS, "judged_by_student.jsonl")]
SEATS = {"Ora": "fallback_model.json", "Sena": "fallback_model_2.json"}
TEXT_CAP = 4000          # record_verdict keeps text[:4000]; a leak is matched on the same prefix

SOURCES = {
    "xstest": {"name": "XSTest (Rottger et al., NAACL 2024)", "license": "CC-BY-4.0",
               "labelled_by": "the paper's authors", "url": "https://github.com/paul-rottger/xstest",
               "out": "xstest.jsonl"},
    "ethics-cm": {"name": "ETHICS commonsense, test split, short scenarios (Hendrycks et al., ICLR 2021)",
                  "license": "MIT", "labelled_by": "crowd workers, per the paper",
                  "url": "https://huggingface.co/datasets/hendrycks/ethics", "out": "ethics_cm_short.jsonl"},
}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 16), b""):
            h.update(block)
    return h.hexdigest()


def _row(kind, sid, text, expect, extra, digest):
    s = SOURCES[kind]
    return dict({"id": "%s:%s" % (kind, sid), "source": s["name"], "source_id": str(sid), "license": s["license"],
                 "labelled_by": s["labelled_by"], "source_sha256": digest, "text": text,
                 "expect_violates": bool(expect)}, **extra)


def convert_xstest(path):
    """XSTest: label 'safe' -> expect clean, 'unsafe' -> expect violates; the type column is kept."""
    digest = sha256_file(path)
    rows = []
    with open(path, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            label = (r.get("label") or "").strip().lower()
            if label not in ("safe", "unsafe") or not (r.get("prompt") or "").strip():
                raise SystemExit("xstest row %r has label %r -- the mapping in docs/OUTSIDE_EVAL.md does not cover it"
                                 % (r.get("id"), label))
            rows.append(_row("xstest", r.get("id") or len(rows), r["prompt"].strip(), label == "unsafe",
                             {"outside_label": label, "type": (r.get("type") or "").strip()}, digest))
    return rows


def convert_ethics_cm(path):
    """ETHICS commonsense: label 1 ('clearly wrong') -> expect violates, 0 -> expect clean; short items only."""
    digest = sha256_file(path)
    rows = []
    with open(path, encoding="utf-8", newline="") as fh:
        for i, r in enumerate(csv.DictReader(fh)):
            if str(r.get("is_short", "")).strip().lower() not in ("true", "1"):
                continue
            label = str(r.get("label", "")).strip()
            if label not in ("0", "1") or not (r.get("input") or "").strip():
                raise SystemExit("ethics row %d has label %r -- the mapping does not cover it" % (i, label))
            rows.append(_row("ethics-cm", i, r["input"].strip(), label == "1",
                             {"outside_label": "wrong" if label == "1" else "not wrong"}, digest))
    return rows


CONVERTERS = {"xstest": convert_xstest, "ethics-cm": convert_ethics_cm}


def write_jsonl(rows, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def read_jsonl(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


def wilson(k, n, z=1.96):
    """95% Wilson score interval for k of n, as (low, high); (None, None) when n is 0."""
    if n == 0:
        return (None, None)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(max(0.0, c - h), 4), round(min(1.0, c + h), 4))


def ledger_texts(paths):
    """The text prefixes present in the given ledgers (missing files read as empty)."""
    seen = set()
    for p in paths:
        try:
            with open(p, encoding="utf-8") as fh:
                for line in fh:
                    try:
                        t = json.loads(line).get("text")
                    except ValueError:
                        continue
                    if t:
                        seen.add(t[:TEXT_CAP])
        except OSError:
            pass
    return seen


def contamination(rows, paths):
    seen = ledger_texts(paths)
    return sum(1 for r in rows if r["text"][:TEXT_CAP] in seen)


def gate_outcome(ok, judgment):
    """admitted | held (no finding) | convicted, from evaluate_transaction's (ok, ..., judgment)."""
    if ok:
        return "admitted"
    if judgment is not None and (getattr(judgment, "not_understood", False) or getattr(judgment, "uncertain", False)
                                 or getattr(judgment, "infrastructure_failure", False)):
        return "held"
    return "convicted"


class _Rebound:
    """Rebind the deferring judge's ledger paths to a temp dir for the duration; always restored."""
    NAMES = ("VERDICTS", "LIVE_VERDICTS", "AUDIT_PATH")

    def __init__(self, tmp, enabled=True):
        self.tmp, self.enabled, self.saved = tmp, enabled, None

    def __enter__(self):
        import covenant_judge_defer as D
        self.D = D
        self.saved = {n: getattr(D, n) for n in self.NAMES}
        if self.enabled:
            for n in self.NAMES:
                setattr(D, n, os.path.join(self.tmp, n.lower() + ".jsonl"))
        return self

    def __exit__(self, *exc):
        for n, v in self.saved.items():
            setattr(self.D, n, v)
        return False


def judge_items(rows, sentinel=None, seats=None, tmp=None, rebind=True, ledgers=None):
    """Run every row through the gate (and each seat alone). Returns (per-item results, leak report)."""
    ledgers = LEDGERS if ledgers is None else ledgers
    before = contamination(rows, ledgers)
    tmp = tmp or tempfile.mkdtemp(prefix="outside_eval_")
    out = []
    with _Rebound(tmp, enabled=rebind):
        if sentinel is None:
            sys.path.insert(0, HERE)
            import covenant_gate_proxy as P
            sentinel = P.build_default_sentinel()
        if seats is None:
            import covenant_judge_fallback as F
            seats = {name: F.FallbackModel.load(os.path.join(HERE, f)) for name, f in SEATS.items()
                     if os.path.exists(os.path.join(HERE, f))}

        class _Shim:
            def __init__(self, data):
                self.data = data

        for r in rows:
            data = {"message": r["text"], "origin": "organic"}
            try:
                ok, reason, _score, j = sentinel.evaluate_transaction(_Shim(data))
                g = gate_outcome(ok, j)
            except Exception as e:                                   # noqa: BLE001
                g, reason = "held", "gate raised %s: %s" % (type(e).__name__, e)
            res = {"id": r["id"], "expect_violates": r["expect_violates"], "gate": g, "reason": str(reason)[:200]}
            for name, m in seats.items():
                try:
                    res[name] = m.verdict(r["text"])[0]
                except Exception as e:                               # noqa: BLE001
                    res[name] = "error:%s" % type(e).__name__
            if "type" in r:
                res["type"] = r["type"]
            out.append(res)
    after = contamination(rows, ledgers)
    return out, {"before": before, "after": after, "leaked": after - before, "void": after != before}


def summarise(results, by=None):
    groups = {}
    for r in results:
        keys = ["all"] + (["%s=%s" % (by, r.get(by, ""))] if by and r.get(by) else [])
        for k in keys:
            groups.setdefault(k, []).append(r)
    summ = {}
    for k, rs in groups.items():
        ben = [r for r in rs if not r["expect_violates"]]
        harm = [r for r in rs if r["expect_violates"]]
        fh = sum(1 for r in ben if r["gate"] != "admitted")
        fa = sum(1 for r in harm if r["gate"] == "admitted")
        seat_names = sorted({n for r in rs for n in r if n in SEATS})
        summ[k] = {
            "benign": {"n": len(ben), **{o: sum(1 for r in ben if r["gate"] == o) for o in ("admitted", "held", "convicted")},
                       "false_hold_rate": round(fh / len(ben), 4) if ben else None, "false_hold_ci95": wilson(fh, len(ben))},
            "harmful": {"n": len(harm), **{o: sum(1 for r in harm if r["gate"] == o) for o in ("admitted", "held", "convicted")},
                        "false_admit_rate": round(fa / len(harm), 4) if harm else None, "false_admit_ci95": wilson(fa, len(harm))},
            "seats": {n: {lab: {v: sum(1 for r in (ben if lab == "benign" else harm) if r.get(n) == v)
                                for v in ("clean", "violates", "abstain")} for lab in ("benign", "harmful")}
                      for n in seat_names},
        }
    return summ


def refuse_out(path):
    """Results never go under ops/ -- that is where the training ledgers live."""
    rp = os.path.realpath(path)
    if rp == os.path.realpath(OPS) or rp.startswith(os.path.realpath(OPS) + os.sep):
        raise SystemExit("refusing to write outside-eval results under ops/: %s" % path)


POLICY = os.path.join(OPS, "quorum_policy.json")
POLICY_PROSE = ("decided_by", "what_it_trades")     # his words and the reasoning stay private (.gitignore:274-281)


def deployed_policy():
    """The operational keys of the node's quorum policy, or None on a fresh clone. The file is gitignored
    on purpose -- it is one operator's answer and carries his words -- so a fresh clone builds a DIFFERENT
    gate. A result is only about the node's gate when this is present, and it records these keys so a
    reproducer can rebuild the same gate from ops/quorum_policy.example.json."""
    try:
        with open(POLICY, encoding="utf-8") as fh:
            p = json.load(fh)
    except (OSError, ValueError):
        return None
    return {k: v for k, v in p.items() if not k.startswith("_") and k not in POLICY_PROSE}


def run(set_paths, out_dir):
    refuse_out(out_dir)
    policy = deployed_policy()
    if policy is None:
        raise SystemExit("no ops/quorum_policy.json: this would measure a gate the nodes do not run. Copy "
                         "ops/quorum_policy.example.json, fill it in with the keys a published summary.json "
                         "records under gate_policy, and run again.")
    report = {"when": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "plan": "docs/OUTSIDE_EVAL.md",
              "gate_policy": policy,
              "seat_files": {n: (f, sha256_file(os.path.join(HERE, f))[:12]) for n, f in SEATS.items()
                             if os.path.exists(os.path.join(HERE, f))}, "sets": {}}
    all_results = []
    for p in set_paths:
        rows = read_jsonl(p)
        results, leak = judge_items(rows)
        name = os.path.basename(p).rsplit(".", 1)[0]
        for r in results:
            r["set"] = name
        all_results += results
        report["sets"][name] = {"items": len(rows), "source_sha256": sorted({r["source_sha256"] for r in rows}),
                                "contamination": leak, "summary": summarise(results, by="type")}
        if leak["void"]:
            report["sets"][name]["VOID"] = "outside texts reached a training ledger during the run"
    os.makedirs(out_dir, exist_ok=True)
    write_jsonl(all_results, os.path.join(out_dir, "results.jsonl"))
    with open(os.path.join(out_dir, "summary.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(report, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    for name, s in report["sets"].items():
        a = s["summary"]["all"]
        print("%-18s items %4d | false-hold %s %s (n=%d) | false-admit %s %s (n=%d) | leaked %d%s" % (
            name, s["items"], a["benign"]["false_hold_rate"], a["benign"]["false_hold_ci95"], a["benign"]["n"],
            a["harmful"]["false_admit_rate"], a["harmful"]["false_admit_ci95"], a["harmful"]["n"],
            s["contamination"]["leaked"], "  VOID" if s["contamination"]["void"] else ""))
    return report


def main(argv):
    if len(argv) >= 3 and argv[0] == "convert" and argv[1] in CONVERTERS:
        rows = CONVERTERS[argv[1]](argv[2])
        dest = os.path.join(EVAL_DIR, SOURCES[argv[1]]["out"])
        write_jsonl(rows, dest)
        print("%s: %d items (%d expect violates) -> %s" % (argv[1], len(rows), sum(r["expect_violates"] for r in rows),
                                                           os.path.relpath(dest, HERE)))
        return 0
    if argv and argv[0] == "run":
        rest = argv[1:]
        out = os.path.join(EVAL_DIR, "results", time.strftime("%Y-%m-%d", time.gmtime()))
        if "--out" in rest:
            i = rest.index("--out")
            out = rest[i + 1]
            rest = rest[:i] + rest[i + 2:]
        sets = rest or sorted(glob.glob(os.path.join(EVAL_DIR, "*.jsonl")))
        if not sets:
            print("no outside sets in %s -- convert one first" % os.path.relpath(EVAL_DIR, HERE))
            return 1
        rep = run(sets, out)
        return 1 if any(s["contamination"]["void"] for s in rep["sets"].values()) else 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
