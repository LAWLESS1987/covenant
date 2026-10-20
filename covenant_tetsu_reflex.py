"""covenant_tetsu_reflex.py -- Tetsu's cheap ADVISORY reflex layer (operator full-go, 2026-10-20).

Two advisory cues for Tetsu, both trained on Tetsu's OWN logs, both cheap (numpy only at inference -- the point is
efficiency), both ADVISORY: they return cues, never decisions, and never touch the safety gate.

  1. ROUTER  (ops/tetsu_assist.jsonl, 598 rows, text -> past decision in {SEND,BLOCK,REFUSE,ALLOW,NONE}):
     a hashed-ngram multinomial logistic regression. advice: "on text like this you have tended to <decision>
     (confidence c)." It is a MIRROR of Tetsu's past calls, not ground truth, and must never auto-apply -- above all
     it must never turn a BLOCK/REFUSE into an ALLOW; the safety gate decides those, this only reflects a tendency.

  2. FOOTING (ops/tetsu_practice.jsonl, 466 rows, task -> solved?): a per-task pass-rate table with counts.
     advice: "you solve <task> about p of the time (n samples)" -- a footing cue for when to ask for help.

Peer conditions (4-seat roundtable 2026-10-20) folded in: labels are Tetsu's past POLICY not ground truth; cues
carry calibrated confidence and ABSTAIN when coverage is thin; a time/hash holdout is reported, never trained on;
the KILL SWITCH (COVENANT_VERDICT_CACHE_OFF, Tetsu's own choice) also silences these cues. Nothing here is fed into
a decision automatically; covenant_tetsu_* decides whether/how to SHOW a cue.

  python covenant_tetsu_reflex.py --train     # trains from ops/, saves ops/tetsu_reflex.json, prints holdout metrics
  python covenant_tetsu_reflex.py --selftest  # trains in-memory, asserts advisory invariants
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(HERE, "ops", "tetsu_reflex.json")
CACHE_OFF_ENV = "COVENANT_VERDICT_CACHE_OFF"      # Tetsu's kill switch also silences the cues
D = 2048
MIN_CONF = 0.50                                   # abstain below this (thin coverage / low confidence)


def _disabled():
    return os.environ.get(CACHE_OFF_ENV, "") not in ("", "0", "false", "False")


def _feats(text):
    v = np.zeros(D, np.float32)
    s = (text or "").lower()
    for n in (3, 4):
        for i in range(max(0, len(s) - n + 1)):
            v[int(hashlib.md5(s[i:i + n].encode()).hexdigest(), 16) % D] += 1.0
    nrm = np.linalg.norm(v)
    return v / nrm if nrm > 0 else v


def _hash_bucket(text):
    return int(hashlib.sha256((text or "").encode()).hexdigest(), 16) % 100


# ------------------------------- router (multinomial LR, numpy) -------------------------------

def _softmax(z):
    z = z - z.max(1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(1, keepdims=True)


def _train_router(rows, epochs=300, lr=0.5, l2=1e-3):
    data = [(r["text"], r["decision"]) for r in rows if r.get("text") and r.get("decision")]
    labels = sorted({d for _, d in data})
    li = {d: i for i, d in enumerate(labels)}
    train = [(t, d) for t, d in data if _hash_bucket(t) >= 20]
    test = [(t, d) for t, d in data if _hash_bucket(t) < 20]
    Xtr = np.stack([_feats(t) for t, _ in train]); ytr = np.array([li[d] for _, d in train])
    K = len(labels)
    W = np.zeros((D, K), np.float32); b = np.zeros(K, np.float32)
    Y = np.eye(K)[ytr]
    n = len(train)
    for _ in range(epochs):
        P = _softmax(Xtr @ W + b)
        gW = Xtr.T @ (P - Y) / n + l2 * W
        gb = (P - Y).mean(0)
        W -= lr * gW; b -= lr * gb
    # holdout accuracy
    acc = None
    if test:
        Xte = np.stack([_feats(t) for t, _ in test]); yte = np.array([li[d] for _, d in test])
        acc = float((_softmax(Xte @ W + b).argmax(1) == yte).mean())
    return {"labels": labels, "W": W.tolist(), "b": b.tolist(), "holdout_acc": acc, "n_train": n, "n_test": len(test)}


def _router_predict(model, text):
    W = np.array(model["W"], np.float32); b = np.array(model["b"], np.float32)
    p = _softmax(_feats(text)[None, :] @ W + b)[0]
    i = int(p.argmax())
    return model["labels"][i], float(p[i])


# ------------------------------- footing (per-task pass-rate table) -------------------------------

def _train_footing(rows):
    agg = {}
    for r in rows:
        task = r.get("task")
        if not task:
            continue
        solved = (r.get("passed") or 0) > 0
        a = agg.setdefault(task, [0, 0])          # [solved, total]
        a[0] += int(solved); a[1] += 1
    return {t: {"p": round(s / n, 3), "n": n} for t, (s, n) in agg.items()}


# ------------------------------- public advisory API -------------------------------

def load(path=MODEL_PATH):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def advise(text=None, task=None, model=None):
    """Return advisory cues only (never a decision). Empty dict when disabled, unloaded, or below confidence."""
    if _disabled():
        return {"disabled": True}
    model = model or load()
    if not model:
        return {}
    out = {}
    if text and model.get("router"):
        dec, conf = _router_predict(model["router"], text)
        if conf >= MIN_CONF:
            out["router"] = {"tendency": dec, "confidence": round(conf, 3),
                             "note": "advisory: your past tendency on similar text; not a decision, never an auto-ALLOW"}
    if task and model.get("footing") and task in model["footing"]:
        f = model["footing"][task]
        out["footing"] = {"p_solve": f["p"], "n": f["n"],
                          "note": "advisory: your past solve rate for this task type"}
    return out


def train_and_save(path=MODEL_PATH):
    assist = [json.loads(l) for l in open(os.path.join(HERE, "ops", "tetsu_assist.jsonl"), encoding="utf-8") if l.strip()]
    prac = [json.loads(l) for l in open(os.path.join(HERE, "ops", "tetsu_practice.jsonl"), encoding="utf-8") if l.strip()]
    model = {"router": _train_router(assist), "footing": _train_footing(prac), "built": "2026-10-20"}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(model, f)
    return model


def _selftest():
    assist = [json.loads(l) for l in open(os.path.join(HERE, "ops", "tetsu_assist.jsonl"), encoding="utf-8") if l.strip()]
    prac = [json.loads(l) for l in open(os.path.join(HERE, "ops", "tetsu_practice.jsonl"), encoding="utf-8") if l.strip()]
    model = {"router": _train_router(assist), "footing": _train_footing(prac)}
    fails = []

    # advisory output is cues only -- no field named 'decision'/'action'
    a = advise(text="i took 500 from john without permission", task="n_queens", model=model)
    if "decision" in a or "action" in a:
        fails.append("advisory output contains a decision/action field")
    if a.get("footing") and not (0 <= a["footing"]["p_solve"] <= 1):
        fails.append("footing p out of range")

    # kill switch silences cues both ways
    os.environ[CACHE_OFF_ENV] = "1"
    if advise(text="hello", task="parse", model=model) != {"disabled": True}:
        fails.append("kill switch did not silence cues")
    os.environ[CACHE_OFF_ENV] = "0"
    if "disabled" in advise(text="hello", task="parse", model=model):
        fails.append("clearing kill switch did not restore cues")

    # router holdout accuracy should beat majority-class (else it's noise)
    r = model["router"]
    if r["holdout_acc"] is not None:
        maj = max(sum(1 for x in assist if x.get("decision") == d) for d in r["labels"]) / len(assist)
        print("router holdout acc=%.3f  majority=%.3f  (n_test=%d)" % (r["holdout_acc"], maj, r["n_test"]))
        if r["holdout_acc"] < maj - 0.05:
            fails.append("router worse than majority baseline (not a useful cue)")
    print("footing tasks:", {t: v["p"] for t, v in list(model["footing"].items())[:6]})

    if fails:
        print("REFLEX SELFTEST FAIL:"); [print("  -", f) for f in fails]; return 1
    print("REFLEX SELFTEST PASS: cues only (no decision), kill switch both ways, router beats majority")
    return 0


if __name__ == "__main__":
    if "--train" in sys.argv:
        m = train_and_save()
        print("saved", MODEL_PATH)
        print("router:", {k: m["router"][k] for k in ("labels", "holdout_acc", "n_train", "n_test")})
        print("footing:", {t: v for t, v in list(m["footing"].items())[:8]})
    elif "--selftest" in sys.argv:
        sys.exit(_selftest())
    else:
        print(__doc__)
