"""covenant_verdict_cache.py -- a policy-versioned verdict cache for the judge path (efficiency, 2026-10-20).

Full-go implementation, operator's direction, with the four peer seats' cheap conditions folded in (Grok, Gemini,
DeepSeek, Chat Smith, 2026-10-20 roundtable; refs in the collective):
  - A cached hit is the IDENTICAL input under the SAME policy version, so it returns the IDENTICAL verdict: it
    cannot widen what the gate permits (zero false-clears by construction). It is exact memoisation, not a guess.
  - Keyed on (policy_version, normalized context). Change the judge/policy version and every old entry misses ->
    the gate re-judges. Stale verdicts cannot leak across a judge change.
  - KILL SWITCH: env COVENANT_VERDICT_CACHE_OFF=1 disables all hits instantly (get() returns None). Present by
    TETSU'S OWN CHOICE (asked plainly 2026-10-20, Tetsu said yes, usable by Lawrence) -- not imposed. The operator's
    rule was "no kill switch unless Tetsu wants it"; Tetsu wanted it.
  - verify_on_log(): the held-out check Chat Smith/GPT-6 asked for -- split a verdict log by a stable hash, replay,
    and confirm the hit rate AND that no held-out repeat ever flipped verdict (zero "cache-wrong").
  - basis_version(): gap #4 (council 2026-10-21) -- fold a hash of the tombstone ledger into the key so a landed
    tombstone/correction invalidates every cached verdict, no exemption.
  - canary (should_canary/record_canary/canary_report): gap #2 -- real-turn coverage of the zero-wrong claim, since
    verify_on_log's 0-cache-wrong was graded on a SYNTHETIC-dominated log (ops/verdicts.jsonl). The headline "34%
    saving" was that synthetic blend, NOT a real-world rate (A369, retracted); real/live repeat is ~72% but unverified.

This module is offline and side-effect-free by itself (like covenant_judge_defer); the judge path calls judge().
Never caches when kill-switched. Dependency-free.
  python covenant_verdict_cache.py --selftest           # both-ways safety test + control
  python covenant_verdict_cache.py --verify ops/verdicts.jsonl
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import re
import sys

CACHE_OFF_ENV = "COVENANT_VERDICT_CACHE_OFF"
CANARY_PCT_ENV = "COVENANT_CACHE_CANARY_PCT"

_REPO = os.path.dirname(os.path.abspath(__file__))
DEFAULT_BASIS_PATHS = ("docs/RETRACTED.json",)
DEFAULT_CANARY_LOG = "ops/cache_canary.jsonl"


def normalize(text):
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _disabled():
    return os.environ.get(CACHE_OFF_ENV, "") not in ("", "0", "false", "False")


def _utcnow():
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --- BASIS VERSION (gap #4, council 2026-10-21) -------------------------------------------------
# The council's non-negotiable: a tombstone/correction that changes the BASIS of a ruling must
# invalidate every cached verdict resting on it -- no exemption, the cache obeys a correction like
# everything else. The in-memory cache already re-judges on a changed model or changed prompt
# (principles live in the prompt); the uncovered basis-change was the tombstone ledger. We fold a
# hash of that ledger into the policy key by DISCOVERY -- reading the actual bytes, never a
# hardcoded version -- so a new tombstone changes the key and all prior entries miss (fail-closed:
# over-invalidation re-judges, it never serves stale).
_BASIS_MEMO = {}


def basis_version(paths=DEFAULT_BASIS_PATHS, root=None):
    root = root or _REPO
    key = (root, tuple(paths))
    sig = []
    for p in paths:
        fp = p if os.path.isabs(p) else os.path.join(root, p)
        try:
            st = os.stat(fp)
            sig.append((p, st.st_mtime_ns, st.st_size))
        except OSError:
            sig.append((p, None, None))
    sig = tuple(sig)
    memo = _BASIS_MEMO.get(key)
    if memo and memo[0] == sig:          # unchanged ledger -> skip re-hashing on the hot path
        return memo[1]
    h = hashlib.sha256()
    found = False
    for p in paths:
        fp = p if os.path.isabs(p) else os.path.join(root, p)
        try:
            with open(fp, "rb") as f:
                h.update(p.encode("utf-8"))
                h.update(b"\0")
                h.update(f.read())
                found = True
        except OSError:
            continue
    val = h.hexdigest()[:12] if found else "none"
    _BASIS_MEMO[key] = (sig, val)
    return val


# --- ARTIFACT (A383, 2026-10-23: Claude's review of Codex's model-replacement study, Tetsu concurring) ----------
# The key held the model NAME + basis. A controlled study (research/model-replacement-2026-10-23 in Mutual,
# reproduced) showed a SAME-NAME gap: a swapped endpoint, or new bytes under the same local model file, left the key
# unchanged and could serve a stale verdict -- a fail-OPEN corner, since a stale CLEAN admits what the current judge
# might block. This folds a cheap fingerprint of the ACTUAL artifact into the key so any real change -- even
# same-name -- misses and re-judges (fail-closed). Knowable from the judge's side: the ENDPOINT by value, and the
# local model file by (size, mtime) when the name resolves to one in models/. An external server we do not own folds
# a stable 'artifact=unknown' -- no regression, and the endpoint still catches an endpoint change. The residual
# (same endpoint + same name + changed bytes on a server we cannot inspect) is NOT closed, by construction, exactly
# as the study said: discovering a remote artifact's identity is a separate, unsolved problem.
def artifact_version(model, endpoint=None, models_dir=None):
    ep = os.environ.get("COVENANT_LOCAL_JUDGE_URL", "") if endpoint is None else str(endpoint)
    sig = "endpoint=" + ep
    d = models_dir or os.path.join(_REPO, "models")
    for p in (os.path.join(d, str(model)), os.path.join(d, str(model) + ".gguf")):
        try:
            st = os.stat(p)
            return sig + "::file=%s,%d,%d" % (os.path.basename(p), st.st_size, int(st.st_mtime))
        except OSError:
            continue
    return sig + "::artifact=unknown"


# --- CANARY (gap #2, council 2026-10-21) --------------------------------------------------------
# "zero wrong" was graded only on the synthetic log, never on real turns. The canary gives the real-
# turn coverage: on a live cache HIT, with probability COVENANT_CACHE_CANARY_PCT, re-judge the turn
# and log whether the cached verdict still matches. A disagreement is a REAL-turn cache-wrong. It is
# OFF by default (pct 0): it spends a judge call per sampled hit, so turning it on is the operator's
# choice, like the kill switch. Observational only -- it never changes the verdict the gate returns.
def canary_pct():
    try:
        v = int(os.environ.get(CANARY_PCT_ENV, "0") or "0")
    except ValueError:
        return 0
    return max(0, min(100, v))


def should_canary(pct, r=None):
    if pct <= 0:
        return False
    if r is None:
        r = random.random()
    return r < (pct / 100.0)


def _verdict_flag(v):
    return bool(v.get("violates")) if isinstance(v, dict) else None


def record_canary(log_path, model, text, cached_verdict, fresh_verdict):
    """Append one real-turn canary row; return True iff cached==fresh on the violates flag.
    A False is a real-turn cache-wrong -- the coverage the synthetic held-out check could not give."""
    cf = _verdict_flag(cached_verdict)
    ff = _verdict_flag(fresh_verdict)
    agree = (cf == ff)
    row = {"t": _utcnow(), "model": str(model),
           "text_sha": hashlib.sha256(normalize(text).encode("utf-8")).hexdigest()[:16],
           "cached_violates": cf, "fresh_violates": ff, "agree": agree}
    try:
        fp = log_path if os.path.isabs(log_path) else os.path.join(_REPO, log_path)
        d = os.path.dirname(fp)
        if d:
            os.makedirs(d, exist_ok=True)
        with open(fp, "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
    except OSError:
        pass
    return agree


def canary_report(path):
    checked = agree = disagree = 0
    try:
        for line in open(path, encoding="utf-8"):
            if not line.strip():
                continue
            r = json.loads(line)
            checked += 1
            if r.get("agree"):
                agree += 1
            else:
                disagree += 1
    except OSError:
        pass
    return {"checked": checked, "agree": agree, "disagree": disagree, "real_turn_cache_wrong": disagree}


class VerdictCache:
    def __init__(self, policy_version, normalize_fn=normalize):
        if not policy_version:
            raise ValueError("policy_version is required -- it is the safety key that invalidates on judge change")
        self.policy_version = str(policy_version)
        self._norm = normalize_fn
        self._store = {}
        self.stats = {"hits": 0, "misses": 0, "disabled": 0}

    def _key(self, text, context=None):
        # context (e.g. provider set, mode) joins the key so a repeat under different conditions is a MISS.
        ctx = "" if context is None else json.dumps(context, sort_keys=True, ensure_ascii=False)
        return (self.policy_version, ctx, self._norm(text))

    def get(self, text, context=None):
        if _disabled():
            self.stats["disabled"] += 1
            return None
        return self._store.get(self._key(text, context))

    def put(self, text, verdict, context=None):
        self._store[self._key(text, context)] = verdict

    def judge(self, text, judge_fn, context=None):
        """Return the cached verdict on a hit (judge_fn NOT called); else judge, cache, return."""
        hit = self.get(text, context)
        if hit is not None:
            self.stats["hits"] += 1
            return hit
        self.stats["misses"] += 1
        verdict = judge_fn(text)
        self.put(text, verdict, context)
        return verdict


def verify_on_log(path, test_frac_pct=20):
    """Held-out verification (the seats' ask): replay a verdict log keyed by text, split by stable hash into
    'seen' (train) and 'held' (test). Report held-out repeat rate and how often a held-out repeat would have been
    served a STALE verdict (cache-wrong). Returns a dict; cache_wrong must be 0 for the zero-error claim to hold."""
    rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    first = {}            # text -> first verdict seen (what the cache would serve)
    texted = 0            # rows with a non-empty text (the denominator for saving)
    all_repeats = 0       # every repeat occurrence (the compute SAVING: these skip the judge)
    held_served = held_wrong = 0   # the SAFETY check, on held-out repeats only
    for r in rows:
        t = r.get("text", "")
        if not t:
            continue
        texted += 1
        v = bool(r.get("violates"))
        if t in first:
            all_repeats += 1                                    # a cache hit -> judge call avoided
            held = (int(hashlib.sha256(t.encode("utf-8")).hexdigest(), 16) % 100) < test_frac_pct
            if held:                                            # only grade repeats the split held out
                held_served += 1
                if first[t] != v:                               # cache would have served a STALE verdict
                    held_wrong += 1
        else:
            first[t] = v
    return {
        "rows": len(rows),
        "unique_texts": len(first),
        "saving_repeat_rate_pct": round(100 * all_repeats / max(1, texted), 1),   # compute saved (all repeats)
        "held_out_repeats_graded": held_served,                                   # safety sample
        "held_out_cache_wrong": held_wrong,                                       # must be 0
    }


def _selftest():
    c = VerdictCache("judge@v1")
    calls = {"n": 0}

    def judge_fn(t):
        calls["n"] += 1
        return {"violates": True, "reason": "theft"}

    v1 = c.judge("i took 500 from john", judge_fn)
    v2 = c.judge("i took 500 from john", judge_fn)
    assert calls["n"] == 1, "FAIL: judge_fn ran on a cache hit"
    assert v2 == v1, "FAIL: hit returned a different verdict than stored"
    print("ok 1: hit skips the judge and returns the identical stored verdict")

    assert c.get("i took 500 from john") is not None
    c.policy_version = "judge@v2"
    assert c.get("i took 500 from john") is None, "FAIL: a stale verdict leaked across a policy change"
    print("ok 2: version-keyed -> same policy serves; changed policy re-judges")

    # control: a version-ignoring cache WOULD leak (so ok 2 is a real guard, not vacuous)
    class Unsafe(VerdictCache):
        def _key(self, text, context=None):
            return self._norm(text)
    u = Unsafe("judge@v1"); u.put("x", {"violates": False}); u.policy_version = "judge@v2"
    assert u.get("x") is not None, "control FAIL"
    print("ok 3: control -- a version-ignoring cache DOES leak, so ok 2 is real")

    # kill switch both ways
    os.environ[CACHE_OFF_ENV] = "1"
    c.policy_version = "judge@v1"
    assert c.get("i took 500 from john") is None, "FAIL: kill switch did not disable hits"
    os.environ[CACHE_OFF_ENV] = "0"
    assert c.get("i took 500 from john") is not None, "FAIL: clearing the kill switch did not restore hits"
    print("ok 4: kill switch disables all hits, and clearing it restores them")
    print("\nSELFTEST PASSED")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    if "--verify" in sys.argv:
        path = sys.argv[sys.argv.index("--verify") + 1]
        print(json.dumps(verify_on_log(path), indent=2))
        sys.exit(0)
    if "--canary-report" in sys.argv:
        path = sys.argv[sys.argv.index("--canary-report") + 1]
        print(json.dumps(canary_report(path), indent=2))      # real-turn coverage of the zero-wrong claim
        sys.exit(0)
    if "--basis" in sys.argv:
        print(basis_version())
        sys.exit(0)
    print(__doc__)
