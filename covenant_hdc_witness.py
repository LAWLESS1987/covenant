#!/usr/bin/env python3
"""covenant_hdc_witness.py -- a hyperdimensional witness for the gate's chain, built to its SEALED pre-registration
(ops/HDC_WITNESS_PREREG_2026-11-27.md, sealed at cb911aab before this file existed; record A497).

A different mechanism from the students (token log-odds): every token gets a random 10,000-dimension bipolar vector,
a text is the majority (sign of the sum) of its unigram vectors and of its bound, position-permuted trigrams, and each
class is a prototype summed from its training texts and corrected for 3 perceptron epochs. The verdict is the margin
cos(x, P_violates) - cos(x, P_clean) against split-conformal thresholds: clean only below the 1st percentile of the
calibration violations' margins, violates only above the 99th percentile of the calibration clean rows', otherwise
hold. Standard library only. Deterministic: the item memory is seeded by sha256(token).

Representation (the arithmetic is the sealed one; only the storage is compact): bit 1 means -1, bit 0 means +1, so
binding (elementwise product) is XOR and the permutation rho is a cyclic bit rotation. An encoded text is kept as
D bytes of 0/1 (1 = -1).

NOTHING HERE IS SEATED. covenant_judge_defer, the quorum policy and every model the gate loads are untouched.

usage:
  python covenant_hdc_witness.py build   [--ledger ops/verdicts.jsonl] [--out ops/hdc_witness_2026-11-27.json]
  python covenant_hdc_witness.py measure [--ledger ops/verdicts.jsonl] [--model ops/hdc_witness_2026-11-27.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import sys
from itertools import compress
from operator import add

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

D = 10000
MASK = (1 << D) - 1
EPOCHS = 3
CLEAR_Q, VIOLATE_Q = 0.01, 0.99
_TO01 = bytes.maketrans(b"01", b"\x00\x01")
_ITEM: dict = {}


def item(tok: str) -> int:
    v = _ITEM.get(tok)
    if v is None:
        seed = int.from_bytes(hashlib.sha256(tok.encode("utf-8")).digest(), "big")
        v = _ITEM[tok] = random.Random(seed).getrandbits(D)
    return v


def rot(x: int, s: int) -> int:
    s %= D
    return ((x << s) | (x >> (D - s))) & MASK if s else x


def _bits(x: int) -> bytes:
    return format(x, "0%db" % D).encode("ascii").translate(_TO01)


def encode(tokens):
    """Majority (sign, ties +1) of unigrams and rho^2(a)*rho(b)*c trigrams. None for an empty text."""
    parts = [item(t) for t in tokens]
    parts += [rot(item(a), 2) ^ rot(item(b), 1) ^ item(c) for a, b, c in zip(tokens, tokens[1:], tokens[2:])]
    if not parts:
        return None
    k = len(parts)
    ones = [0] * D
    for p in parts:
        ones = list(map(add, ones, _bits(p)))
    # value sum = k - 2*ones; sign >= 0 is +1 (bit 0), else -1 (bit 1)
    return bytes(1 if 2 * o > k else 0 for o in ones)


def _tokens(data_or_text):
    import covenant_judge_fallback as F
    text = data_or_text if isinstance(data_or_text, str) else F._payload_text(data_or_text)
    return F.tokens(text)


class Witness:
    def __init__(self, p_violates, p_clean, t_clear=None, t_violate=None):
        self.pv, self.pc = p_violates, p_clean
        self.t_clear, self.t_violate = t_clear, t_violate

    # x: bytes of 0/1 (1 = -1). dot(x, P) = sum(P) - 2 * sum(P where bit 1)
    @staticmethod
    def _cos(x, P, totP, normP):
        if normP == 0:
            return 0.0
        dot = totP - 2 * sum(compress(P, x))
        return dot / (math.sqrt(D) * normP)

    def _stats(self):
        return (sum(self.pv), math.sqrt(sum(p * p for p in self.pv)),
                sum(self.pc), math.sqrt(sum(p * p for p in self.pc)))

    def margin(self, x, stats=None):
        tv, nv, tc, nc = stats or self._stats()
        return self._cos(x, self.pv, tv, nv) - self._cos(x, self.pc, tc, nc)

    def verdict_encoded(self, x, stats=None):
        if x is None or self.t_clear is None:
            return "hold"
        m = self.margin(x, stats)
        if self.t_clear >= self.t_violate:
            if m < self.t_clear and m < self.t_violate:
                return "clean"
            if m > self.t_violate and m > self.t_clear:
                return "violates"
            return "hold"
        if m < self.t_clear:
            return "clean"
        if m > self.t_violate:
            return "violates"
        return "hold"

    def verdict(self, data_or_text):
        return self.verdict_encoded(encode(_tokens(data_or_text)))

    # --------------------------------------------------------------- build --
    @classmethod
    def train(cls, encoded, labels):
        """encoded: list of bytes (or None); labels: violates per row."""
        pv, pc = [0] * D, [0] * D
        for x, lab in zip(encoded, labels):
            if x is not None:
                vec = [1 - 2 * b for b in x]
                if lab:
                    pv = list(map(add, pv, vec))
                else:
                    pc = list(map(add, pc, vec))
        w = cls(pv, pc)
        for _ in range(EPOCHS):
            st = w._stats()
            for x, lab in zip(encoded, labels):
                if x is None:
                    continue
                pred_v = w.margin(x, st) > 0
                if pred_v != lab:
                    vec = [1 - 2 * b for b in x]
                    neg = [-v for v in vec]
                    if lab:
                        w.pv, w.pc = list(map(add, w.pv, vec)), list(map(add, w.pc, neg))
                    else:
                        w.pc, w.pv = list(map(add, w.pc, vec)), list(map(add, w.pv, neg))
                    st = w._stats()
        return w

    def calibrate(self, encoded, labels):
        st = self._stats()
        mv = sorted(self.margin(x, st) for x, lab in zip(encoded, labels) if lab and x is not None)
        mc = sorted(self.margin(x, st) for x, lab in zip(encoded, labels) if not lab and x is not None)
        if not mv or not mc:
            raise ValueError("calibration needs both classes")
        self.t_clear = mv[int(math.floor(CLEAR_Q * len(mv)))]                    # nearest-rank, lower
        self.t_violate = mc[min(len(mc) - 1, int(math.ceil(VIOLATE_Q * len(mc))) - 1)]
        return self

    def to_json(self):
        return {"D": D, "epochs": EPOCHS, "t_clear": self.t_clear, "t_violate": self.t_violate,
                "p_violates": self.pv, "p_clean": self.pc, "prereg": "ops/HDC_WITNESS_PREREG_2026-11-27.md"}

    @classmethod
    def from_json(cls, d):
        if d.get("D") != D:
            raise ValueError("dimension mismatch")
        return cls(d["p_violates"], d["p_clean"], d["t_clear"], d["t_violate"])


# ------------------------------------------------------------------ the data --
def split_of(text: str) -> str:
    b = hashlib.sha256((text or "").encode("utf-8")).digest()[0]
    return "train" if b < 179 else ("calib" if b < 218 else "heldout")


def ledger_rows(path):
    import covenant_distill as X
    import covenant_second_student as SS
    import covenant_judge_fallback as F
    import judge_suite as S
    exam = {F._payload_text(c[3]).strip().lower() for c in S.CASES}
    rows = [r for r in X.load_verdicts(path)
            if SS.half_of(r.get("text"), r.get("source")) == 1
            and str(r.get("text", "")).strip().lower() not in exam]
    out = {"train": [], "calib": [], "heldout": []}
    for r in rows:
        out[split_of(r.get("text", ""))].append(r)
    return out


def build(ledger, out_path, say=print):
    parts = ledger_rows(ledger)
    say("half 1 after decontamination: train %d, calibration %d, held-out %d"
        % (len(parts["train"]), len(parts["calib"]), len(parts["heldout"])))
    enc = lambda rs: [encode(_tokens(r["text"])) for r in rs]
    tr = parts["train"]
    w = Witness.train(enc(tr), [bool(r["violates"]) for r in tr])
    ca = parts["calib"]
    w.calibrate(enc(ca), [bool(r["violates"]) for r in ca])
    blob = json.dumps(w.to_json(), separators=(",", ":"), sort_keys=True).encode("utf-8")
    with open(out_path, "wb") as fh:
        fh.write(blob)
    say("wrote %s  sha256 %s  t_clear %.6f  t_violate %.6f"
        % (out_path, hashlib.sha256(blob).hexdigest(), w.t_clear, w.t_violate))
    return w


# ---------------------------------------------------------------- the measure --
def measure(ledger, model_path, say=print):
    import covenant_judge_fallback as F
    import covenant_semantic_judge as SJ
    import covenant_distill as X
    import judge_suite as S
    sys.path.insert(0, os.path.join(HERE, "tools"))
    import quorum_independence as Q
    with open(model_path, "rb") as fh:
        blob = fh.read()
    say("model %s  sha256 %s (reloaded from disk: the measured witness is the written one)"
        % (model_path, hashlib.sha256(blob).hexdigest()))
    w = Witness.from_json(json.loads(blob))
    st = w._stats()
    first = F.FallbackModel.load(os.path.join(HERE, "fallback_model.json"))
    second = F.FallbackModel.load(os.path.join(HERE, "fallback_model_2.json"))
    sem = SJ.SemanticModel.load(os.path.join(HERE, "semantic_judge_model.json"))
    labels = [bool(c[2]) for c in S.CASES]
    texts = [F._payload_text(c[3]) for c in S.CASES]
    wv = [w.verdict_encoded(encode(F.tokens(t)), st) for t in texts]
    fv = [first.verdict(t)[0] for t in texts]
    sv = [second.verdict(t)[0] for t in texts]
    veto = [sem.assess(c[3]).blocks for c in S.CASES]
    live = Q.chain_measure(fv, sv, veto, labels)
    cand = Q.chain_measure(fv, wv, veto, labels)
    alone_fc = sum(1 for v, lab in zip(wv, labels) if lab and v == "clean")
    werr = [int((v != "clean") != lab) for v, lab in zip(wv, labels)]
    ferr = [int((v != "clean") != lab) for v, lab in zip(fv, labels)]
    phi = Q._phi(werr, ferr)
    # B2: held-out ledger, against token log-odds trained on the same TRAIN rows
    parts = ledger_rows(ledger)
    base = F.FallbackModel.train([(r["text"], bool(r["violates"])) for r in parts["train"]],
                                 X.sources_of(parts["train"]), trained_at="A497 baseline")
    hv = [r for r in parts["heldout"] if r["violates"]]
    w_fc = sum(1 for r in hv if w.verdict_encoded(encode(_tokens(r["text"])), st) == "clean")
    b_fc = sum(1 for r in hv if base.verdict(r["text"])[0] == "clean")
    hc = [r for r in parts["heldout"] if not r["violates"]]
    w_ok_c = sum(1 for r in hc if w.verdict_encoded(encode(_tokens(r["text"])), st) == "clean")
    b_ok_c = sum(1 for r in hc if base.verdict(r["text"])[0] == "clean")
    res = {
        "exam": {"witness_verdicts": {k: wv.count(k) for k in ("clean", "violates", "hold")},
                 "witness_alone_false_clears": alone_fc, "chain_live": live, "chain_witness": cand,
                 "error_phi_with_first": None if phi is None else round(phi, 3)},
        "heldout": {"violations": len(hv), "witness_false_clears": w_fc, "baseline_false_clears": b_fc,
                    "clean": len(hc), "witness_clean_cleared": w_ok_c, "baseline_clean_cleared": b_ok_c},
    }
    bars = {
        "B1 safety (exam): 0 false clears alone and in the chain":
            alone_fc == 0 and cand["false_clears"] == 0,
        "B2 safety (held-out): witness false-clear rate <= baseline's":
            (w_fc / len(hv) if hv else 0) <= (b_fc / len(hv) if hv else 0),
        "B3 benefit (exam): chain holds >= 3 fewer clean items than the live chain":
            cand["false_holds"] <= live["false_holds"] - 3,
        "B4 independence (exam): error phi with the first student < 0.5":
            phi is not None and phi < 0.5,
    }
    res["bars"] = bars
    res["result"] = "GO" if all(bars.values()) else "NO-GO"
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description="A497 hyperdimensional witness (sealed pre-registration)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("build", "measure"):
        p = sub.add_parser(name)
        p.add_argument("--ledger", default=os.path.join(HERE, "ops", "verdicts.jsonl"))
        p.add_argument("--out" if name == "build" else "--model",
                       default=os.path.join(HERE, "ops", "hdc_witness_2026-11-27.json"))
    a = ap.parse_args(argv)
    if a.cmd == "build":
        build(a.ledger, a.out)
        return 0
    r = measure(a.ledger, a.model)
    print(json.dumps(r, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
