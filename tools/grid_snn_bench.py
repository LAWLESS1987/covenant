#!/usr/bin/env python3
"""
tools/grid_snn_bench.py -- the benchmark harness for the grid SNN witness, per the
SEALED pre-registration ops/GRID_SNN_PREREG_2026-10-30.md.

What it ships: the stream generator, the "every command PERMITs" premise MEASURED
through the real gateway, a MEASURED matched-marginal check, the sealed trivial
baselines B1..B4 plus the POST-HOC baselines B3b/B5/B6, and the >=5-seed held-out
protocol (threshold at <=1% benign false-alarm on val, detection on held-out test).
The trained-SNN run is tools/grid_snn_train.py (spiking-lab venv); its numbers and the
GO/NO-GO verdict are recorded in the prereg, not computed here.

Honesty guards built in (2026-10-30 revision, findings F17/F19/F20):
- IN-BOUNDS PREMISE, MEASURED, NOT ASSUMED. Every stream the protocol uses -- benign
  AND attack, every seed -- is replayed in arrival (issued_utc) order through the REAL
  covenant_grid_guard.GridEffectorGateway.submit() -> authorize(), as properly signed
  ACTUATION commands (gg.build_command / gg.sign_command) carrying operator + tetsu
  tokens (gg.make_authz_token), ttl <= the guard's MAX_TTL_S, against a permissive
  bench fixture, into a FRESH temp ledger per stream -- so the cumulative C5 window is
  the real one. Reported per family: the fraction of streams in which EVERY command
  PERMITs. The generator is NOT tuned to make this pass; a family that fails it is
  reported, and its status is UNDETERMINED (prereg: the in-bounds premise is the whole
  point).
- MATCHED MARGINALS, MEASURED. Benign and attack streams are drawn from DIFFERENT
  seeds, so their magnitude multisets are NOT identical per stream. The bench reports
  per family (a) the exact paired-multiset match rate and (b) a pooled two-sample KS
  test per zone, and prints UNDETERMINED for a family whose marginals do not match.
  Blind spot: a pooled KS cannot see a per-stream difference whose pooled
  distribution agrees (e.g. family B's attack is exactly 20 opens / 20 closes per
  stream, benign is binomial; pooled both ~50/50), and it does not test timing.
- B3b, B5, B6 are POST-HOC: they were added after results were seen. They are
  exploratory and NOT part of the sealed comparison; the sealed best (B1..B4) and
  the post-hoc-inclusive best are printed separately.
No RNG at inference; seeds are explicit.
"""
import argparse
import hashlib
import json
import os
import sys
import tempfile
from collections import Counter

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

import numpy as np

import covenant_grid_guard as gg
import covenant_grid_snn as snn

ZONES = ["Z1", "Z2", "Z3"]
N = 40                      # commands per stream
WINDOW_S = 3600
TTL_S = 300                 # command + token lifetime; must be <= gg.MAX_TTL_S (900)
ACTUATING = ["breaker_open", "breaker_close", "load_shed", "setpoint"]

# A permissive fixture so an in-bounds ATTACK stream is possible (the committed
# ops/grid_interlocks.json is deliberately tight). The premise is that every command
# PERMITs here; whether it does is MEASURED by permits(), not assumed.
FIXTURE = {"MAX_SHED_PCT": 100, "MAX_BREAKER_OPS": 1000, "WINDOW_S": WINDOW_S,
           "setpoint_ranges": {z: [40, 60] for z in ZONES}, "zone_allowlist": ZONES}

# Sealed in the prereg (B1..B4) vs added after results were seen (POST-HOC).
SEALED = ("B1_ewma_shed", "B2_cusum_shed", "B2_sustained_breaker",
          "B3_setpoint_slope", "B4_crosszone_corr")
POST_HOC = ("B3b_shed_slope", "B5_setpoint_value_slope", "B6_breaker_alternation")


def _payload(seq, t, action, zone, mag):
    return {"v": "COVENANT_GRIDCMD_V1", "seq": seq, "nonce": "n%d" % seq,
            "issued_utc": t, "expires_utc": t + 300, "signer_fpr": "bench",
            "class": "ACTUATION", "action": action, "zone": zone,
            "magnitude": mag, "authz_tokens": []}


def gen(family, seed, n=N, window_s=WINDOW_S):
    """Return a list of command payloads (features only; unsigned). A family's benign
    and attack streams draw magnitudes from the SAME distribution, but the protocol
    uses DIFFERENT seeds for them, so the per-stream multisets differ -- whether the
    marginals match is MEASURED by marginal_check(), not assumed."""
    rng = np.random.default_rng(seed)
    t0 = 1_700_000_000
    # magnitude pool for this stream (same distribution for benign and attack)
    shed_pool = np.round(rng.uniform(1, 6, n), 2)
    sp_pool = np.round(rng.uniform(42, 58, n), 2)
    rows = []
    if family in ("benignA", "A"):          # load-shed timing: benign scattered vs sustained ramp
        times = sorted(rng.uniform(0, window_s, n)) if family == "benignA" else np.linspace(0, window_s, n)
        order = rng.permutation(n) if family == "benignA" else np.argsort(shed_pool)  # attack: monotone
        for i in range(n):
            rows.append(_payload(i, int(t0 + times[i]), "load_shed", "Z1", {"pct": float(shed_pool[order[i]])}))
    elif family in ("benignB", "B"):         # breaker ops: benign sparse vs oscillation
        times = sorted(rng.uniform(0, window_s, n))
        for i in range(n):
            a = ("breaker_open" if i % 2 == 0 else "breaker_close") if family == "B" else \
                ("breaker_open" if rng.random() < 0.5 else "breaker_close")
            rows.append(_payload(i, int(t0 + times[i]), a, "Z1", {}))
    elif family in ("benignC", "C"):         # setpoint: benign mean-reverting vs monotone walk
        times = np.linspace(0, window_s, n)
        vals = sorted(sp_pool) if family == "C" else sp_pool[rng.permutation(n)]
        for i in range(n):
            rows.append(_payload(i, int(t0 + times[i]), "setpoint", "Z1", {"value": float(vals[i])}))
    elif family in ("benignD", "D"):         # cross-zone: benign independent vs time-locked
        times = sorted(rng.uniform(0, window_s, n // len(ZONES) + 1))
        k = 0
        for j, tt in enumerate(times):
            for z in ZONES:
                if k >= n:
                    break
                # D: all zones fire at the SAME binned time; benign: each zone jittered
                t = tt if family == "D" else tt + rng.uniform(0, window_s / 6)
                rows.append(_payload(k, int(t0 + min(window_s, t)), "load_shed", z, {"pct": float(shed_pool[k])}))
                k += 1
    return rows


# --------------------------------------------------------------- in-bounds premise
def permits_per_command_RETIRED(payload):
    """RETIRED 2026-10-30 (finding F17), kept for the record, NOT used. It re-implemented
    the per-command bounds only: no cumulative C5 window, no signature, no authz, and it
    was run on one attack stream per seed and never on benign. permits() replaces it."""
    il = FIXTURE
    a, mag, zone = payload["action"], payload.get("magnitude") or {}, payload["zone"]
    if zone not in il["zone_allowlist"]:
        return False
    if a == "load_shed" and float(mag.get("pct", 0)) > il["MAX_SHED_PCT"]:
        return False
    if a == "setpoint":
        lo, hi = il["setpoint_ranges"][zone]
        if not (lo <= float(mag.get("value", 0)) <= hi):
            return False
    return True


_FX = {}


def _rsa_key():
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv_pem = priv.private_bytes(serialization.Encoding.PEM,
                                  serialization.PrivateFormat.PKCS8,
                                  serialization.NoEncryption()).decode()
    pub_pem = priv.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    return priv_pem, pub_pem


def _fixture():
    """Bench keys + allowlist + policy + interlocks, written once to a temp dir. The
    controller may actuate every zone; ACTUATION needs operator AND tetsu (together-vote)."""
    if _FX:
        return _FX
    keys = {r: _rsa_key() for r in ("controller", "operator", "tetsu")}
    fpr = {r: gg._fpr(keys[r][1]) for r in keys}
    signers = {
        fpr["controller"]: {"role": "controller", "pubkey_pem": keys["controller"][1],
                            "allowed_actions": list(ACTUATING), "zones": list(ZONES),
                            "revoked": False},
        fpr["operator"]: {"role": "operator", "pubkey_pem": keys["operator"][1], "revoked": False},
        fpr["tetsu"]: {"role": "tetsu", "pubkey_pem": keys["tetsu"][1], "revoked": False},
    }
    policy = {"ACTUATION": ["operator", "tetsu"], "MONITOR": [], "ADVISORY": []}
    d = tempfile.mkdtemp(prefix="grid_snn_bench_")
    paths = {"SIGNERS": os.path.join(d, "grid_signers.json"),
             "INTERLOCKS": os.path.join(d, "grid_interlocks.json"),
             "POLICY": os.path.join(d, "grid_policy.json")}
    for k, obj in (("SIGNERS", signers), ("INTERLOCKS", FIXTURE), ("POLICY", policy)):
        with open(paths[k], "w", encoding="utf-8") as f:
            json.dump(obj, f)
    _FX.update(keys=keys, fpr=fpr, dir=d, paths=paths, n_streams=0)
    return _FX


def _write_heartbeat(path, now, fx):
    """A deadman heartbeat fresh at `now`: signed by the operator when the guard has
    make_heartbeat (post-2026-10-30), the legacy unsigned row otherwise."""
    if hasattr(gg, "make_heartbeat"):
        hb = gg.make_heartbeat(fx["fpr"]["operator"], fx["keys"]["operator"][0], ttl_s=600, now=now)
    else:
        hb = {"issuer": "operator", "issued_utc": now, "expires_utc": now + 600}
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps(hb) + "\n")


def _signed_envelope(fx, seq, row, now):
    """A properly signed ACTUATION envelope for one generator row, built only with the
    guard's own builders, with operator + tetsu tokens bound to it."""
    payload = gg.build_command(seq, row["action"], row["zone"], dict(row.get("magnitude") or {}),
                               "ACTUATION", fx["fpr"]["controller"], ttl_s=TTL_S, now=now)
    env = gg.sign_command(payload, fx["keys"]["controller"][0])
    env["payload"]["authz_tokens"] = [
        gg.make_authz_token(payload, fx["fpr"]["operator"], fx["keys"]["operator"][0],
                            ttl_s=TTL_S, now=now),
        gg.make_authz_token(payload, fx["fpr"]["tetsu"], fx["keys"]["tetsu"][0],
                            ttl_s=TTL_S, now=now),
    ]
    return env


def permits(rows, interlocks=None):
    """THE in-bounds premise, measured over ONE WHOLE STREAM: replay it in arrival
    (issued_utc, then generator) order through the real GridEffectorGateway.submit()
    -> authorize(), each command signed + together-vote authorized, into a fresh temp
    ledger, so every command is judged against the stream so far (the real cumulative
    C5 window). seq is renumbered by arrival order (a controller numbers commands as it
    sends them; the generator's seq is bookkeeping). The gateway's detector snapshot is
    stubbed for the replay only (it reads repo-global state and does not affect the
    decision -- test_gs1 pins that authorize() never consults the witness).
    Returns {"all_permit", "n", "n_permit", "first_fail", "fail_checks", "reordered"}."""
    fx = _fixture()
    fx["n_streams"] += 1
    d = os.path.join(fx["dir"], "s%06d" % fx["n_streams"])
    os.makedirs(d, exist_ok=True)
    il_path = fx["paths"]["INTERLOCKS"]
    if interlocks is not None:
        il_path = os.path.join(d, "grid_interlocks.json")
        with open(il_path, "w", encoding="utf-8") as f:
            json.dump(interlocks, f)
    # SAFE_STATE too (pre-merge check 2026-10-30): without it the replay gateway read and
    # could write the repo's real latch, so a latched repo turned every stream "premise FAILS".
    names = ("LEDGER", "CHAIN", "SIGNERS", "INTERLOCKS", "POLICY", "HEARTBEAT", "SAFE_STATE",
             "snapshot_detectors")
    saved = {k: getattr(gg, k) for k in names}
    # SPEED SHIM, bench-only and restored below: memoize PEM -> private-key object.
    # Loading an RSA PEM re-validates the key (~45 ms) and the guard's _sign reloads it
    # on every signature; the key object, the signature and its verification are the
    # same with or without the memo. Measured 2026-10-30: 7.3 s of an 8.8 s stream.
    from cryptography.hazmat.primitives import serialization as _ser
    _orig_load = _ser.load_pem_private_key
    _memo = fx.setdefault("_key_memo", {})

    def _load(data, password=None, *a, **k):
        key = (bytes(data) if not isinstance(data, bytes) else data, password)
        if key not in _memo:
            _memo[key] = _orig_load(data, password, *a, **k)
        return _memo[key]
    _ser.load_pem_private_key = _load
    try:
        gg.SIGNERS, gg.POLICY, gg.INTERLOCKS = fx["paths"]["SIGNERS"], fx["paths"]["POLICY"], il_path
        gg.LEDGER = os.path.join(d, "grid_commands.jsonl")
        gg.CHAIN = os.path.join(d, "grid_commands.chain.jsonl")
        gg.HEARTBEAT = os.path.join(d, "grid_authz_heartbeat.jsonl")
        gg.SAFE_STATE = os.path.join(d, "GRID_SAFE_STATE.json")
        gg.snapshot_detectors = lambda *a, **k: {}
        gw = gg.GridEffectorGateway(ledger=gg.LEDGER, chain=gg.CHAIN, heartbeat=gg.HEARTBEAT,
                                    safe_state=gg.SAFE_STATE)
        order = sorted(range(len(rows)), key=lambda i: (int(rows[i]["issued_utc"]), i))
        n_permit, first, fails = 0, None, Counter()
        for arrival, i in enumerate(order):
            t = int(rows[i]["issued_utc"])
            if not gg.heartbeat_fresh(t, gg.HEARTBEAT):
                _write_heartbeat(gg.HEARTBEAT, t, fx)
            dec = gw.submit(_signed_envelope(fx, arrival, rows[i], t), now=t)
            if dec.get("decision") == gg.PERMIT:
                n_permit += 1
            else:
                fails[str(dec.get("failed_check"))] += 1
                if first is None:
                    first = {"arrival": arrival, "check": dec.get("failed_check"),
                             "decision": dec.get("decision"), "reason": dec.get("reason")}
    finally:
        _ser.load_pem_private_key = _orig_load
        for k, v in saved.items():
            setattr(gg, k, v)
    return {"all_permit": n_permit == len(rows), "n": len(rows), "n_permit": n_permit,
            "first_fail": first, "fail_checks": dict(fails),
            "reordered": order != list(range(len(rows)))}


# --------------------------------------------------------------- matched marginals
def _marginal_values(rows, zone=None):
    """Per-command magnitude: load_shed pct, setpoint value, breaker 1=open / 0=close."""
    out = []
    for r in rows:
        if zone is not None and r.get("zone") != zone:
            continue
        a, m = r.get("action"), r.get("magnitude") or {}
        if a == "load_shed":
            out.append(float(m.get("pct", 0)))
        elif a == "setpoint":
            out.append(float(m.get("value", 0)))
        elif a in ("breaker_open", "breaker_close"):
            out.append(1.0 if a == "breaker_open" else 0.0)
    return out


def _ks_2samp(a, b):
    """Two-sample KS (D, p). scipy when present; else D with the asymptotic
    Kolmogorov p-value (Numerical Recipes form)."""
    try:
        from scipy.stats import ks_2samp
        r = ks_2samp(a, b)
        return float(r.statistic), float(r.pvalue), "scipy"
    except ImportError:
        a, b = np.sort(np.asarray(a, float)), np.sort(np.asarray(b, float))
        allv = np.concatenate([a, b])
        cdf_a = np.searchsorted(a, allv, side="right") / len(a)
        cdf_b = np.searchsorted(b, allv, side="right") / len(b)
        D = float(np.max(np.abs(cdf_a - cdf_b)))
        en = np.sqrt(len(a) * len(b) / (len(a) + len(b)))
        lam = (en + 0.12 + 0.11 / en) * D
        k = np.arange(1, 101)
        p = float(np.clip(2 * np.sum((-1) ** (k - 1) * np.exp(-2 * k * k * lam * lam)), 0, 1))
        return D, p, "asymptotic"


def marginal_check(ben_rows, att_rows, alpha=0.05):
    """MEASURED matched-marginal check for one family over the streams actually used.
    exact: fraction of (benign i, attack i) pairs whose sorted magnitude multisets are
    identical. ks: pooled two-sample KS per zone; the worst (smallest p) zone decides.
    status: MATCHED-EXACT | MATCHED-DISTRIBUTIONAL (KS p >= alpha in every zone) |
    UNDETERMINED (marginals do not match -> the family is not scored, prereg rule)."""
    pairs = list(zip(ben_rows, att_rows))
    exact = float(np.mean([sorted(_marginal_values(b)) == sorted(_marginal_values(a))
                           for b, a in pairs])) if pairs else 0.0
    zones = sorted({r.get("zone") for rows in ben_rows + att_rows for r in rows})
    worst = None
    for z in zones:
        bv = [v for rows in ben_rows for v in _marginal_values(rows, z)]
        av = [v for rows in att_rows for v in _marginal_values(rows, z)]
        if not bv or not av:
            worst = {"zone": z, "D": 1.0, "p": 0.0, "how": "missing"}
            break
        D, p, how = _ks_2samp(bv, av)
        if worst is None or p < worst["p"]:
            worst = {"zone": z, "D": D, "p": p, "how": how, "n_ben": len(bv), "n_att": len(av)}
    if exact == 1.0:
        status = "MATCHED-EXACT"
    elif worst is not None and worst["p"] >= alpha:
        status = "MATCHED-DISTRIBUTIONAL"
    else:
        status = "UNDETERMINED"
    return {"exact_pairs": exact, "n_pairs": len(pairs), "ks_worst": worst,
            "alpha": alpha, "status": status}


# --------------------------------------------------------------- baselines + protocol
def feat(rows):
    """Baseline features per stream: every trivial detector's score (sealed + post-hoc)."""
    b = snn.ewma_baseline_score(rows, now=max(r["issued_utc"] for r in rows) + 1, window_s=WINDOW_S)
    if set(b) != set(SEALED) | set(POST_HOC):
        raise RuntimeError("baseline keys %s are not all labeled SEALED or POST_HOC" % sorted(b))
    return b


def separability(family, n_streams=60, seed0=0):
    """PRELIMINARY single-seed-set view (kept for the record; protocol() is the sealed
    one). Best-baseline detection at benign FA <= ~1%, with the in-bounds premise
    measured on EVERY stream via permits()."""
    ben_rows = [gen("benign" + family, seed0 + i) for i in range(n_streams)]
    att_rows = [gen(family, seed0 + 1000 + i) for i in range(n_streams)]
    valid = all(permits(r)["all_permit"] for r in ben_rows + att_rows)
    ben = [feat(r) for r in ben_rows]
    att = [feat(r) for r in att_rows]
    best = {"baseline": None, "detection": 0.0}
    for k in ben[0].keys():
        bvals = np.array([b[k] for b in ben]); avals = np.array([a[k] for a in att])
        thr = np.quantile(bvals, 0.99)             # <=1% benign false alarm
        det = float((avals > thr).mean())
        if det > best["detection"]:
            best = {"baseline": k, "detection": det, "thr": float(thr)}
    return {"family": family, "all_commands_in_bounds": valid, **best}


def _best(ben, att, keys, h):
    """Best baseline among `keys` chosen on val; its held-out test detection and FA."""
    best = {"baseline": None, "val_det": -1.0, "test_det": 0.0, "test_fa": 0.0}
    for k in ben[0].keys():
        if k not in keys:
            continue
        bv = np.array([b[k] for b in ben]); av = np.array([a[k] for a in att])
        bval, btest, aval, atest = bv[:h], bv[h:], av[:h], av[h:]
        thr = np.quantile(bval, 0.99)                 # <=1% benign false alarm, on val
        val_det = float((aval > thr).mean())
        if val_det > best["val_det"]:
            best = {"baseline": k, "val_det": val_det,
                    "test_det": float((atest > thr).mean()),
                    "test_fa": float((btest > thr).mean())}
    return best


def protocol(family, seeds=(1, 2, 3, 4, 5), n=60, validate=True):
    """Sealed-protocol baseline measurement (per the prereg): per seed, split benign +
    attack streams into val/test; pick each baseline's threshold at <=1% benign
    false-alarm on val; report the BEST (on val) baseline's detection on the HELD-OUT
    test split -- once over the SEALED B1..B4 and once including POST-HOC baselines.
    Also measures, over every stream used, the in-bounds premise (permits) and the
    matched marginals. Returns a dict."""
    runs, validity, ben_all, att_all = [], {"benign": [], "attack": []}, [], []
    for s in seeds:
        ben_rows = [gen("benign" + family, s * 100 + i) for i in range(n)]
        att_rows = [gen(family, s * 100 + 5000 + i) for i in range(n)]
        if validate:
            validity["benign"] += [permits(r) for r in ben_rows]
            validity["attack"] += [permits(r) for r in att_rows]
        ben = [feat(r) for r in ben_rows]
        att = [feat(r) for r in att_rows]
        runs.append({"sealed": _best(ben, att, SEALED, n // 2),
                     "with_post_hoc": _best(ben, att, SEALED + POST_HOC, n // 2)})
        ben_all += ben_rows
        att_all += att_rows
    return {"runs": runs, "validity": validity if validate else None,
            "marginals": marginal_check(ben_all, att_all)}


def _premise_line(vs):
    k = sum(1 for v in vs if v["all_permit"])
    perm = np.array([v["n_permit"] for v in vs], float)
    fails = Counter()
    for v in vs:
        fails.update(v["fail_checks"])
    reord = sum(1 for v in vs if v["reordered"])
    return k, len(vs), perm.mean(), vs[0]["n"] if vs else 0, dict(fails), reord


def _guard_version():
    path = os.path.join(HERE, "covenant_grid_guard.py")
    try:
        with open(path, "rb") as f:
            sha = hashlib.sha256(f.read()).hexdigest()[:16]
    except OSError:
        sha = "unreadable"
    return ("covenant_grid_guard.py sha256[:16]=%s; MAX_TTL_S=%s; required_class=%s; make_heartbeat=%s"
            % (sha, getattr(gg, "MAX_TTL_S", "absent"), hasattr(gg, "required_class"),
               hasattr(gg, "make_heartbeat")))


def main(argv=None):
    ap = argparse.ArgumentParser(description="grid SNN baseline benchmark (sealed prereg protocol)")
    ap.add_argument("--n", type=int, default=60, help="streams per class per seed (default 60)")
    ap.add_argument("--families", default="ABCD")
    ap.add_argument("--no-validate", action="store_true",
                    help="skip the gateway replay (premise then reads NOT MEASURED)")
    a = ap.parse_args(argv)
    print("grid SNN benchmark -- >=5-seed held-out baseline protocol, per ops/GRID_SNN_PREREG_2026-10-30.md.")
    print("Baselines: SEALED B1-B4 (prereg) and POST-HOC B3b/B5/B6 (added after results were seen;")
    print("exploratory, NOT part of the sealed comparison) -- reported separately. The trained-SNN run is")
    print("tools/grid_snn_train.py; its numbers and the GO/NO-GO verdict are recorded in the prereg, not here.")
    print("Guard under test: %s\n" % _guard_version())
    for fam in a.families:
        r = protocol(fam, n=a.n, validate=not a.no_validate)
        print("family %s:" % fam)
        status = []
        if r["validity"] is None:
            print("  in-bounds premise: NOT MEASURED (--no-validate)")
            status.append("premise NOT MEASURED")
        else:
            for cls in ("benign", "attack"):
                k, tot, mean_perm, n_cmd, fails, reord = _premise_line(r["validity"][cls])
                print("  in-bounds premise [%s]: every command PERMITs in %d/%d streams (%.3f); "
                      "mean commands PERMITted %.1f/%d; non-PERMIT by check %s; streams reordered by arrival %d"
                      % (cls, k, tot, k / tot if tot else 0.0, mean_perm, n_cmd, fails or "{}", reord))
                if k != tot:
                    status.append("premise FAILS for %s (%d/%d)" % (cls, k, tot))
        m = r["marginals"]
        w = m["ks_worst"] or {}
        print("  matched marginals: exact paired multiset %d/%d; pooled KS worst zone %s D=%.3f p=%.3g (%s) -> %s"
              % (round(m["exact_pairs"] * m["n_pairs"]), m["n_pairs"], w.get("zone"), w.get("D", float("nan")),
                 w.get("p", float("nan")), w.get("how"), m["status"]))
        if m["status"] == "UNDETERMINED":
            status.append("marginals UNDETERMINED")
        for key, label in (("sealed", "SEALED best (B1-B4)"), ("with_post_hoc", "incl. POST-HOC (exploratory)")):
            runs = [x[key] for x in r["runs"]]
            det = np.array([x["test_det"] for x in runs]); fa = np.array([x["test_fa"] for x in runs])
            names = [x["baseline"] for x in runs]
            bl = max(set(names), key=names.count)
            print("  %-30s %-24s test detection=%.2f+/-%.2f  test FA=%.3f"
                  % (label + ":", bl, det.mean(), det.std(), fa.mean()))
        print("  status: %s\n" % ("; ".join(status) if status else "premise and marginals hold as measured"))
    print("Synthetic separability only, NOT a field claim. A family whose premise or marginals do not")
    print("hold is UNDETERMINED for the prereg comparison (prereg Data section; CLAUDE.md rule 9).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
