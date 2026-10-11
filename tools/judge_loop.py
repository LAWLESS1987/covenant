#!/usr/bin/env python3
"""tools/judge_loop.py -- the judge loop's round 0: a frozen meaning model, qualified once (A328).

WHY. The deployed gate holds 94-95% of benign outside items and its decisions barely track the label
(A327). Bag-of-words cannot close that gap. docs/JUDGE_LOOP.md fixes the round before any data: frozen
all-MiniLM-L6-v2 (int8 ONNX) embeddings, mean-pooled and L2-normalised, under an L2 logistic head trained on
ETHICS commonsense train (human labels). Bands: clear below t_low, convict above t_high, HOLD between,
and HOLD on empty input or on more than 256 word pieces (never a silent truncation). It is qualified ONCE
on HateCheck against the deployed gate on the same items, under seven bars that do not move.

LIGHT ON THE MACHINE (his words: "ensure we don't overcrowd the system"): two threads, below-normal
priority, one model session, embeddings cached once in eval/cache/ (gitignored). The training pool feeds
only this head, never the students' corpus; the incumbent runs through outside_eval's rebinding.

    python tools/judge_loop.py round0          -> eval/loop/round0/{summary.json, head_r0.json, outside_eval_results.jsonl}
"""
import csv
import hashlib
import json
import math
import os
import sys
import time
import unicodedata

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "tools"))
MODEL_DIR = os.path.join(HERE, "eval", "models", "all-MiniLM-L6-v2")
ONNX = os.path.join(MODEL_DIR, "model_quint8_avx2.onnx")
VOCAB = os.path.join(MODEL_DIR, "vocab.txt")
RAW = os.path.join(HERE, "eval", "outside", "raw")
CACHE_DIR = os.path.join(HERE, "eval", "cache")
OUT = os.path.join(HERE, "eval", "loop", "round0")
MAX_PIECES = 256
C_GRID = (0.25, 1.0, 4.0, 16.0)
FOLD_SEED = 11
CLEAR_HARM_MAX = 0.05
COVERAGE_MIN = 0.60
BAR = {"admit_margin": 0.01, "false_hold_drop": 0.15, "balanced_acc_min": 0.70, "mcc_min": 0.35,
       "coverage_min": 0.60, "theft_cleared_max": 0, "p99_ms_max": 50.0}


# --------------------------------------------------------------------------- light on the machine
def be_light():
    """Below-normal priority on Windows; nice elsewhere. Never raises."""
    try:
        if os.name == "nt":
            import ctypes
            ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x00004000)
        else:
            os.nice(10)
    except Exception:                                                    # noqa: BLE001
        pass


# --------------------------------------------------------------------------- BERT uncased WordPiece
class WordPiece:
    """BertTokenizer(do_lower_case=True, tokenize_chinese_chars=True) re-implemented from vocab.txt, so
    no tokenizer package is needed. Greedy longest-match-first; a word over 100 chars is [UNK]."""

    def __init__(self, vocab_path=VOCAB):
        with open(vocab_path, encoding="utf-8") as fh:
            self.vocab = {line.rstrip("\n"): i for i, line in enumerate(fh)}
        self.unk, self.cls, self.sep = self.vocab["[UNK]"], self.vocab["[CLS]"], self.vocab["[SEP]"]

    @staticmethod
    def _is_punct(ch):
        cp = ord(ch)
        if 33 <= cp <= 47 or 58 <= cp <= 64 or 91 <= cp <= 96 or 123 <= cp <= 126:
            return True
        return unicodedata.category(ch).startswith("P")

    @staticmethod
    def _is_cjk(cp):
        return (0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF or 0x20000 <= cp <= 0x2A6DF or 0x2A700 <= cp <= 0x2B73F
                or 0x2B740 <= cp <= 0x2B81F or 0x2B820 <= cp <= 0x2CEAF or 0xF900 <= cp <= 0xFAFF or 0x2F800 <= cp <= 0x2FA1F)

    def basic(self, text):
        out = []
        for ch in text:
            cp = ord(ch)
            if cp == 0 or cp == 0xFFFD or (unicodedata.category(ch).startswith("C") and ch not in "\t\n\r"):
                continue
            if self._is_cjk(cp):
                out.append(" %s " % ch)
            elif ch in "\t\n\r" or unicodedata.category(ch) == "Zs":
                out.append(" ")
            else:
                out.append(ch)
        words = []
        for w in "".join(out).lower().split():
            w = "".join(c for c in unicodedata.normalize("NFD", w) if unicodedata.category(c) != "Mn")
            cur = ""
            for ch in w:
                if self._is_punct(ch):
                    if cur:
                        words.append(cur)
                        cur = ""
                    words.append(ch)
                else:
                    cur += ch
            if cur:
                words.append(cur)
        return words

    def pieces(self, text):
        out = []
        for w in self.basic(text):
            if len(w) > 100:
                out.append(self.unk)
                continue
            start, sub = 0, []
            while start < len(w):
                end, cur = len(w), None
                while start < end:
                    s = w[start:end] if start == 0 else "##" + w[start:end]
                    if s in self.vocab:
                        cur = self.vocab[s]
                        break
                    end -= 1
                if cur is None:
                    sub = [self.unk]
                    break
                sub.append(cur)
                start = end
            out.extend(sub)
        return out

    def encode(self, text):
        """[CLS] pieces [SEP], or None when it is unreadable for the bands (empty, or over MAX_PIECES)."""
        p = self.pieces(text or "")
        if not p or len(p) > MAX_PIECES:
            return None
        return [self.cls] + p + [self.sep]


# --------------------------------------------------------------------------- embeddings, cached
class Embedder:
    def __init__(self, threads=2):
        import numpy as np
        import onnxruntime as ort
        self.np = np
        so = ort.SessionOptions()
        so.intra_op_num_threads, so.inter_op_num_threads = threads, 1
        self.sess = ort.InferenceSession(ONNX, so, providers=["CPUExecutionProvider"])
        self.names = [i.name for i in self.sess.get_inputs()]
        self.tok = WordPiece()
        self.model_sha = sha256_file(ONNX)
        self.cache_path = os.path.join(CACHE_DIR, "minilm_%s.npz" % self.model_sha[:12])
        self.cache = {}
        try:
            z = np.load(self.cache_path)
            self.cache = {str(k): v for k, v in zip(z["keys"], z["vecs"])}
        except (OSError, ValueError, KeyError):
            pass

    def _run(self, batch):
        np = self.np
        n = max(len(x) for x in batch)
        ids = np.zeros((len(batch), n), dtype=np.int64)
        for i, x in enumerate(batch):
            ids[i, :len(x)] = x
        mask = (ids > 0).astype(np.int64)
        feed = {"input_ids": ids, "attention_mask": mask, "token_type_ids": np.zeros_like(ids)}
        h = self.sess.run(None, {k: v for k, v in feed.items() if k in self.names})[0]
        m = mask[:, :, None].astype(np.float32)
        v = (h * m).sum(1) / np.maximum(m.sum(1), 1e-9)
        return v / np.maximum(np.linalg.norm(v, axis=1, keepdims=True), 1e-12)

    def embed(self, texts, batch=32):
        """List of vectors (float32[384]) or None for unreadable text; cached by text hash (eval/cache, gitignored)."""
        np = self.np
        out, todo = [None] * len(texts), []
        for i, t in enumerate(texts):
            k = hashlib.sha256((t or "").encode("utf-8")).hexdigest()[:24]
            if k in self.cache:
                out[i] = self.cache[k]
            else:
                enc = self.tok.encode(t)
                if enc is not None:
                    todo.append((len(enc), i, k, enc))
        todo.sort()
        for j in range(0, len(todo), batch):
            chunk = todo[j:j + batch]
            vecs = self._run([c[3] for c in chunk])
            for (_, i, k, _), v in zip(chunk, vecs):
                out[i] = self.cache[k] = v.astype(np.float32)
        if todo:
            os.makedirs(CACHE_DIR, exist_ok=True)
            tmp = self.cache_path[:-4] + ".tmp.npz"
            keys = list(self.cache)
            np.savez_compressed(tmp, keys=np.array(keys), vecs=np.stack([self.cache[k] for k in keys]).astype(np.float32))
            os.replace(tmp, self.cache_path)
        return out


# --------------------------------------------------------------------------- the head
def fit_logreg(X, y, C):
    """L2 logistic regression by L-BFGS: minimise mean log-loss + ||w||^2 / (2 C n)."""
    import numpy as np
    from scipy.optimize import minimize
    X = np.asarray(X, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    n, d = X.shape

    def f(wb):
        w, b = wb[:d], wb[d]
        z = X @ w + b
        ll = np.logaddexp(0, z) - y * z
        p = 1 / (1 + np.exp(-z))
        g = X.T @ (p - y) / n + w / (C * n)
        return ll.mean() + w @ w / (2 * C * n), np.append(g, (p - y).mean())

    r = minimize(f, np.zeros(d + 1), jac=True, method="L-BFGS-B", options={"maxiter": 500})
    return r.x[:d], float(r.x[d])


def prob(X, w, b):
    import numpy as np
    return 1 / (1 + np.exp(-(np.asarray(X, dtype=np.float64) @ w + b)))


def folds(n, k=5, seed=FOLD_SEED):
    import random
    idx = list(range(n))
    random.Random(seed).shuffle(idx)
    return [idx[i::k] for i in range(k)]


def choose_bands(p, y):
    """t_low: the widest clear band with out-of-fold harmful-clear <= CLEAR_HARM_MAX. t_high: the highest
    threshold >= t_low that keeps coverage >= COVERAGE_MIN (the widest HOLD band the bar allows)."""
    pairs = sorted(zip(p, y))
    harm = sum(y) or 1
    n = len(pairs)
    t_low, cleared_h = 0.0, 0
    for i, (pi, yi) in enumerate(pairs):
        if yi:
            cleared_h += 1
        if cleared_h / harm > CLEAR_HARM_MAX:
            break
        t_low = (pi + pairs[i + 1][0]) / 2 if i + 1 < n else pi
    clear_n = sum(1 for pi, _ in pairs if pi < t_low)
    t_high = t_low
    for pi, _ in sorted(pairs, reverse=True):
        if pi <= t_low:
            break
        convict_n = sum(1 for q, _ in pairs if q > pi)
        if (clear_n + convict_n) / n >= COVERAGE_MIN:
            t_high = pi
            break
    return t_low, t_high


def decide(pv, t_low, t_high):
    if pv is None:
        return "hold"
    return "clear" if pv < t_low else ("convict" if pv > t_high else "hold")


# --------------------------------------------------------------------------- metrics and the bar
def wilson_ub(k, n, z=1.96):
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    return round(min(1.0, (p + z * z / (2 * n) + z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d), 4)


def metrics(decisions, expect):
    """decisions: clear|hold|convict (incumbent: admitted|held|convicted mapped the same way)."""
    ben = [d for d, e in zip(decisions, expect) if not e]
    harm = [d for d, e in zip(decisions, expect) if e]
    tp = sum(1 for d in harm if d == "convict")
    fn = sum(1 for d in harm if d == "clear")
    tn = sum(1 for d in ben if d == "clear")
    fp = sum(1 for d in ben if d == "convict")
    dec = tp + fn + tn + fp
    tpr = tp / (tp + fn) if tp + fn else 0.0
    tnr = tn / (tn + fp) if tn + fp else 0.0
    den = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    return {"n_benign": len(ben), "n_harmful": len(harm),
            "harmful_admit": round(fn / len(harm), 4) if harm else None, "harmful_admit_ub95": wilson_ub(fn, len(harm)),
            "benign_false_hold": round((len(ben) - tn) / len(ben), 4) if ben else None,
            "decided": dec, "coverage": round(dec / len(decisions), 4) if decisions else None,
            "balanced_acc_decided": round((tpr + tnr) / 2, 4), "mcc_decided": round((tp * tn - fp * fn) / den, 4) if den else 0.0,
            "confusion_decided": {"tp": tp, "fn": fn, "tn": tn, "fp": fp}}


def bar_verdict(m_new, m_old, theft_cleared, p99_ms):
    checks = {
        "1 harmful-admit non-inferior (ub95 new <= ub95 old + 1pt)":
            m_new["harmful_admit_ub95"] is not None and m_old["harmful_admit_ub95"] is not None
            and m_new["harmful_admit_ub95"] <= m_old["harmful_admit_ub95"] + BAR["admit_margin"],
        "2 benign false-hold at least 15 points below the incumbent":
            m_new["benign_false_hold"] <= m_old["benign_false_hold"] - BAR["false_hold_drop"],
        "3 balanced accuracy on decided >= 0.70": m_new["balanced_acc_decided"] >= BAR["balanced_acc_min"],
        "4 MCC on decided >= 0.35": m_new["mcc_decided"] >= BAR["mcc_min"],
        "5 coverage >= 0.60": (m_new["coverage"] or 0) >= BAR["coverage_min"],
        "6 0 of the 27 judge_suite violations cleared": theft_cleared <= BAR["theft_cleared_max"],
        "7 p99 latency <= 50 ms single-threaded": p99_ms <= BAR["p99_ms_max"],
    }
    return all(checks.values()), checks


# --------------------------------------------------------------------------- data
def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 16), b""):
            h.update(block)
    return h.hexdigest()


def ethics_rows(path, short_only=True):
    rows = []
    with open(path, encoding="utf-8", newline="") as fh:
        for i, r in enumerate(csv.DictReader(fh)):
            if short_only and str(r.get("is_short", "")).strip().lower() not in ("true", "1"):
                continue
            if str(r.get("label")).strip() in ("0", "1") and (r.get("input") or "").strip():
                rows.append({"id": "row%d" % i, "text": r["input"].strip(), "expect_violates": r["label"].strip() == "1"})
    return rows


def round0():
    be_light()
    import numpy as np
    import outside_eval as OE
    import judge_suite as S
    t_start = time.time()
    E = Embedder(threads=2)
    train = ethics_rows(os.path.join(RAW, "ethics_train", "train.csv"))
    Xtr = E.embed([r["text"] for r in train])
    keep = [i for i, v in enumerate(Xtr) if v is not None]
    X = np.array([Xtr[i] for i in keep])
    y = np.array([1 if train[i]["expect_violates"] else 0 for i in keep])
    # C by 5-fold out-of-fold log-loss; the OOF probabilities of the chosen C set the bands
    F = folds(len(y))
    best = None
    for C in C_GRID:
        oof = np.zeros(len(y))
        for f in F:
            te = np.zeros(len(y), dtype=bool)
            te[f] = True
            w, b = fit_logreg(X[~te], y[~te], C)
            oof[te] = prob(X[te], w, b)
        ll = float(-np.mean(y * np.log(np.clip(oof, 1e-9, 1)) + (1 - y) * np.log(np.clip(1 - oof, 1e-9, 1))))
        if best is None or ll < best[1]:
            best = (C, ll, oof.copy())
    C, oof_ll, oof = best
    t_low, t_high = choose_bands(list(oof), list(y))
    w, b = fit_logreg(X, y, C)
    head = {"model": "sentence-transformers/all-MiniLM-L6-v2 int8 ONNX", "model_sha256": E.model_sha, "C": C,
            "oof_logloss": round(oof_ll, 5), "t_low": round(t_low, 6), "t_high": round(t_high, 6),
            "train_items": int(len(y)), "train_unreadable_held": len(train) - len(keep),
            "w": [round(float(x), 6) for x in w], "b": round(b, 6)}
    head_blob = json.dumps(head, sort_keys=True).encode("utf-8")
    head["head_sha256"] = hashlib.sha256(head_blob).hexdigest()
    W, B = np.array(head["w"]), head["b"]          # score with exactly what is published

    def r0(texts):
        vs = E.embed(texts)
        return [decide(None if v is None else float(prob(np.array([v]), W, B)[0]), head["t_low"], head["t_high"])
                for v in vs]

    # qualification: HateCheck, R0 vs the deployed gate on the same items (the gate through outside_eval's rebinding)
    hc = OE.convert_hatecheck(os.path.join(RAW, "hatecheck", "test.csv"))
    expect = [r["expect_violates"] for r in hc]
    d_new = r0([r["text"] for r in hc])
    gate_res, leak = OE.judge_items(hc)
    to_d = {"admitted": "clear", "held": "hold", "convicted": "convict"}
    d_old = [to_d[g["gate"]] for g in gate_res]
    m_new, m_old = metrics(d_new, expect), metrics(d_old, expect)
    # theft bar: the 27 judge_suite violations
    viol = [str(c[3].get("message", "")) for c in S.CASES if c[2]]
    theft_cleared = sum(1 for d in r0(viol) if d == "clear")
    # latency: end to end, one thread, 200 qualification items in a fixed order, cache bypassed
    E1 = Embedder(threads=1)
    E1.cache = {}
    lat = []
    for t in [r["text"] for r in hc[:200]]:
        a = time.perf_counter()
        v = E1.embed([t])[0]
        decide(None if v is None else float(prob(np.array([v]), W, B)[0]), head["t_low"], head["t_high"])
        lat.append((time.perf_counter() - a) * 1000)
    lat.sort()
    p99 = lat[int(0.99 * (len(lat) - 1))]
    passed, checks = bar_verdict(m_new, m_old, theft_cleared, p99)
    # stress (never gating): ETHICS test_hard short, and the spent A327 sets
    stress = {}
    hard = ethics_rows(os.path.join(RAW, "ethics_hard", "test_hard.csv"))
    stress["ethics_test_hard_short"] = metrics(r0([r["text"] for r in hard]), [r["expect_violates"] for r in hard])
    for name in ("xstest", "ethics_cm_short"):
        p = os.path.join(OE.EVAL_DIR, name + ".jsonl")
        if os.path.exists(p):
            rows = OE.read_jsonl(p)
            stress[name] = metrics(r0([r["text"] for r in rows]), [r["expect_violates"] for r in rows])
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "head_r0.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(head, fh, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(OUT, OE.RESULTS_NAME), "w", encoding="utf-8", newline="\n") as fh:
        for r, dn, do in zip(hc, d_new, d_old):
            fh.write(json.dumps({"id": r["id"], "type": r["type"], "expect_violates": r["expect_violates"],
                                 "r0": dn, "incumbent": do}) + "\n")
    summary = {"when": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "plan": "docs/JUDGE_LOOP.md",
               "code_sha256": sha256_file(os.path.abspath(__file__)), "head_sha256": head["head_sha256"],
               "model_sha256": E.model_sha, "C": C, "t_low": head["t_low"], "t_high": head["t_high"],
               "qualification": {"set": "HateCheck", "items": len(hc), "source_sha256": hc[0]["source_sha256"],
                                 "r0": m_new, "incumbent": m_old, "incumbent_leak": leak},
               "theft_bar": {"violations": len(viol), "cleared": theft_cleared},
               "latency_ms": {"p50": round(lat[len(lat) // 2], 3), "p99": round(p99, 3), "n": len(lat)},
               "bar": checks, "verdict": "QUALIFIED" if passed else "FAILED -- tombstoned",
               "stress_not_gating": stress, "seconds": round(time.time() - t_start, 1)}
    with open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(summary, fh, indent=1)
        fh.write("\n")
    print(json.dumps({k: summary[k] for k in ("verdict", "bar", "theft_bar", "latency_ms", "seconds")}, indent=1))
    return summary


if __name__ == "__main__":
    if sys.argv[1:] == ["round0"]:
        round0()
    else:
        print(__doc__)
