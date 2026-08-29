"""test_a24_anomaly_eviction.py -- A24 (v8.38): a bounded buffer that evicts
OLDEST-OVERALL is a buffer whose contents an attacker chooses.

WHAT A24 IS.  `SpikingAnomalyMonitor` holds `max_events=5000` and, up to and
including v8.37, dropped the globally oldest record on overflow. Several
anomaly kinds are recorded on paths a PEER triggers at will, one record per
frame, with no per-source or per-kind bound. So one socket sending garbage
decides what /anomalies says -- and /anomalies is what /health warns from and
what covenant_watchdog.py reads every round (P12).

PRE-FIX MEASUREMENT, taken on pristine v8.37 `07e097f3e37f` (and reproduced on
v8.36, so this predates every guard in the file and was not introduced by one):

    5,200 frames of one kind   -> buffer 5000/5000, kinds retained: 1
    planted `peer_send_failure`  ("REAL EVENT: node B unreachable")  -> GONE
    planted `block_rejected_ethics`                                  -> GONE
    6 attacker kinds, 6,000 frames -> real event GONE as well; cycling kinds
                                       is not a defence
    a GENUINE SPIKE of a third kind, detected on the identical stream with no
      flood, becomes UNDETECTABLE with one                           -> the
      flood does not merely erase records, it switches the detector OFF for
      every kind but its own
    cost per record at saturation: 13.1 us median vs 0.4 us empty -- a 33x
      amplification the flooder chooses, paid while holding the lock report()
      needs, because `self._events[-max:]` copies 5,000 tuples per record

THE FIX (v8.38).  Under pressure the buffer degrades toward DIVERSITY, not
toward recency: capacity is shared between the kinds present by progressive
filling (`_fair_share`), each over-share kind losing only its OLDEST records.
The load-bearing property, asserted in S3 and demonstrated end-to-end in S2:

    A KIND AT OR BELOW ITS FAIR SHARE IS RETURNED UNCHANGED.

which is why S2 can assert something stronger than "degrades gracefully" --
the honest kinds' recent/baseline/expected numbers under a 6,000-frame flood
are IDENTICAL to the same stream with no flood at all.

Nothing is silent (M34): evictions are counted per kind and reported, and
/health warns. Deliberately NOT recorded as an anomaly of its own -- an anomaly
about anomaly recording is a feedback loop into the buffer being reported on.

A24b (v8.39), and section S10 is its record. The v8.38 fix above left the
attacker one thing: `buffer_pressure` was `bool(self._evicted)` and `_evicted`
is monotonic, so ONE flood turned on a /health warning that never turned off.
Measured on pristine v8.38 `6ddedcdc7c6b`: at +15 min zero evicted records
remained inside the baseline window -- per_kind was a census again -- and
/health still warned; at +30 days, still. The flag is now bounded by the same
window report() reports on. PRE-FIX RECORD for this half: 49/60 on v8.38.

Run: python3 test_a24_anomaly_eviction.py   (needs covenant_path_pattern.py beside it)
"""
import os, sys, io, json, time, math, random, tokenize, inspect, threading, statistics
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("COVENANT_JUDGE_PROVIDERS", "mock")
os.environ.setdefault("COVENANT_INSECURE_MOCK_JUDGE", "1")
import covenant_unified_v8 as cov

results = []
def check(label, ok, detail=""):
    results.append((label, bool(ok)))
    print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail}", flush=True)


def code_only(src: str) -> str:
    """Source with comments and docstrings removed (M42). A comment saying
    `self._events[-self.max_events:]` is not a slice."""
    out, prev = [], tokenize.INDENT
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
    except (tokenize.TokenError, IndentationError):
        return src
    for tok in toks:
        if tok.type == tokenize.COMMENT:
            continue
        if tok.type == tokenize.STRING and prev in (
                tokenize.INDENT, tokenize.NEWLINE, tokenize.NL, tokenize.DEDENT):
            continue
        out.append(tok.string)
        prev = tok.type
    return " ".join(out)


REAL_A = "peer_send_failure"          # A18/A23's signal: a delivery that failed
REAL_B = "block_rejected_ethics"      # B5's signal: the gate refused a block
ATTACKER = ["peer_message_error", "peer_tx_id_invalid", "peer_index_invalid",
            "peer_message_too_slow", "peer_message_too_large", "bridge_message_error"]


def fresh(**kw):
    return cov.SpikingAnomalyMonitor(**kw)


def flood(mon, kind, n, detail="x" * 40):
    for _ in range(n):
        mon.record(kind, detail)


# ---------------------------------------------------------------------------
def s1():
    """S1 -- the attack itself: one kind, one socket, 5,200 frames."""
    m = fresh()
    m.record(REAL_A, "REAL EVENT: node B unreachable")
    m.record(REAL_B, "REAL EVENT: judge dissent on block 4")
    flood(m, "peer_tx_id_invalid", 5200)
    rep = m.report()
    kinds = rep["per_kind"]
    check("S1a the real peer_send_failure survives a 5,200-frame flood",
          REAL_A in kinds, f"kinds={sorted(kinds)}")
    check("S1b the real block_rejected_ethics survives too",
          REAL_B in kinds, f"kinds={sorted(kinds)}")
    check("S1c the flood's own records are still retained (it is not muted)",
          kinds.get("peer_tx_id_invalid", {}).get("baseline", 0) > 1000,
          str(kinds.get("peer_tx_id_invalid")))
    check("S1d the hard ceiling still holds -- never more than max_events",
          rep["total_events_retained"] <= m.max_events,
          f"{rep['total_events_retained']} <= {m.max_events}")
    check("S1e the buffer is still substantially FULL (no over-eviction)",
          rep["total_events_retained"] >= m.max_events * 0.9,
          str(rep["total_events_retained"]))

    # A single record of a rare kind is the hardest case: it is one slot against
    # five thousand, and it is exactly the record an operator needs.
    m2 = fresh()
    m2.record(REAL_A, "the only one there will ever be")
    flood(m2, "peer_message_error", 40000)
    check("S1f a SINGLE record of a rare kind survives 40,000 frames",
          REAL_A in m2.report()["per_kind"], f"kinds={sorted(m2.report()['per_kind'])}")

    # S1g -- the scheme shares capacity K ways, so the adversarial question is
    # whether inflating K starves the rare record. K is bounded by the FILE
    # (S4c), so this is its true worst case: every kind the core can emit is
    # present at once AND one of them is flooding.
    import ast
    src = open(inspect.getsourcefile(cov), encoding="utf-8").read()
    all_kinds = sorted({n.args[0].value for n in ast.walk(ast.parse(src))
                        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                        and n.func.attr == "record" and n.args
                        and isinstance(n.args[0], ast.Constant)
                        and isinstance(n.args[0].value, str)})
    m3 = fresh()
    m3.record(REAL_A, "THE ONLY ONE")
    for k in all_kinds:
        if k != REAL_A:
            for _ in range(3):
                m3.record(k, "pad")
    flood(m3, "peer_message_error", 50000)
    r3 = m3.report()
    check("S1g at maximum K (every kind the core can emit) the rare record "
          "still survives a 50,000-frame flood",
          REAL_A in r3["per_kind"],
          f"K={len(all_kinds)} retained_kinds={len(r3['per_kind'])}")
    check("S1h and no kind present is starved to zero",
          len(r3["per_kind"]) >= len(all_kinds),
          f"{len(r3['per_kind'])} of {len(all_kinds)}")


# ---------------------------------------------------------------------------
def _stream(mon, t0):
    """One fixed event stream, injected at chosen times so the arithmetic is
    exact: 600 honest events over the last 600 s (expected_recent 60), 90 more
    inside the last 60 s (1.5x -- real, and correctly NOT a spike), and 200
    events of a third kind inside the last 60 s with no baseline (a genuine
    spike). Injected directly because the point is to control the CLOCK, not to
    exercise record() -- S1/S4/S9 do that."""
    with mon._lock:
        for i in range(600):
            mon._events.append((t0 - 600 + i, "honest_kind", "h"))
        for i in range(90):
            mon._events.append((t0 - 59 + i * 0.65, "honest_kind", "h"))
        for i in range(200):
            mon._events.append((t0 - 50 + i * 0.24, "genuine_spike", "s"))
        mon._events.sort()


def s2():
    """S2 -- the spike detector, before and after, on the IDENTICAL stream.
    This is the measurement A24's fix shape asked for."""
    t0 = time.time()
    clean = fresh(); _stream(clean, t0)
    dirty = fresh(); _stream(dirty, t0)
    flood(dirty, "peer_tx_id_invalid", 6000)
    # Take the two reports BACK-TO-BACK, after the flood. report() anchors its
    # recent/baseline windows at the moment of the call; a 6,000-frame flood
    # costs real wall clock (about a second on a loaded win32 box), and with
    # `before` taken before the flood the oldest honest event slid out of each
    # window between the two calls -- S2d then failed 690/150 vs 689/149 on a
    # stream the flood never touched. Measured 2026-08-29, deployed core and
    # candidate alike, every run under load. The flood cannot leak into
    # `before`: clean and dirty are separate monitors.
    before = clean.report()
    after = dirty.report()

    b_names = [s["kind"] for s in before["spikes"]]
    a_names = [s["kind"] for s in after["spikes"]]
    check("S2a without a flood, the genuine spike is detected",
          "genuine_spike" in b_names, str(b_names))
    check("S2b WITH a flood, the genuine spike is STILL detected",
          "genuine_spike" in a_names, str(a_names))
    check("S2c the honest non-spiking kind is still reported at all",
          "honest_kind" in after["per_kind"], f"kinds={sorted(after['per_kind'])}")
    # The strong form. Both honest kinds sit under their fair share, so
    # _fair_share returns them untouched and every number the detector computes
    # for them is bit-identical to a node that was never flooded.
    for k in ("honest_kind", "genuine_spike"):
        check(f"S2d {k}: recent/baseline/expected IDENTICAL under flood",
              before["per_kind"].get(k) == after["per_kind"].get(k),
              f"before={before['per_kind'].get(k)} after={after['per_kind'].get(k)}")
    check("S2e the honest 1.5x rise is still NOT called a spike",
          "honest_kind" not in a_names, str(a_names))
    check("S2f the flood itself is still flagged as a spike",
          "peer_tx_id_invalid" in a_names, str(a_names))
    check("S2g spike_detected stays True and names >1 kind",
          after["spike_detected"] and len(a_names) >= 2, str(a_names))

    # S2h -- the hard case S2d cannot reach. A kind ABOVE its fair share IS
    # truncated, so the question is whether a flood can suppress a LARGE
    # genuine spike by shrinking it. It cannot: truncation keeps the newest
    # records, so `recent` and `baseline` shrink together and the ratio the
    # detector tests (r > expected * multiplier) is preserved.
    big = fresh()
    with big._lock:
        for i in range(4000):
            big._events.append((t0 - 50 + i * 0.012, "big_genuine_spike", "s"))
    check("S2h a LARGE genuine spike is detected before the flood",
          "big_genuine_spike" in [s["kind"] for s in big.report()["spikes"]], "")
    flood(big, "peer_message_error", 20000)
    st = big.report()
    names = [s["kind"] for s in st["spikes"]]
    pk = st["per_kind"].get("big_genuine_spike", {})
    check("S2i truncated to its fair share, it is STILL detected",
          "big_genuine_spike" in names, f"{names} {pk}")
    check("S2j because truncation keeps the newest, recent/baseline shrink "
          "together and the ratio survives",
          pk.get("recent") == pk.get("baseline")
          and pk.get("recent", 0) > pk.get("expected_recent", 0) * 3, str(pk))


# ---------------------------------------------------------------------------
def s3():
    """S3 -- _fair_share is pure, total, and has the property everything else
    rests on. Property-tested, not spot-checked."""
    fs = cov.SpikingAnomalyMonitor._fair_share
    check("S3a it is a staticmethod (no instance state, nothing to race)",
          isinstance(inspect.getattr_static(cov.SpikingAnomalyMonitor,
                                            "_fair_share"), staticmethod), "")
    edge = [({}, 100), ({"a": 0}, 100), ({"a": 5}, 0), ({"a": 5}, 5),
            ({"a": 5, "b": 5}, 1), ({"a": 1, "b": 1, "c": 1}, 2),
            ({"a": 10 ** 6}, 5000), ({"a": 1, "b": 10 ** 6}, 5000)]
    ok_total, ok_nonneg, ok_le = True, True, True
    for counts, cap in edge:
        try:
            k = fs(counts, cap)
        except Exception as e:
            check("S3b raised on an edge input", False, f"{counts},{cap}: {e}")
            return
        ok_total &= sum(k.values()) <= cap
        ok_nonneg &= all(v >= 0 for v in k.values())
        ok_le &= all(k[n] <= counts.get(n, 0) for n in k)
    check("S3b never raises on empty/zero/over-subscribed inputs", True, "")
    check("S3c sum(keep) <= capacity on every edge input", ok_total, "")
    check("S3d keep is non-negative and never exceeds the count held",
          ok_nonneg and ok_le, "")

    rnd = random.Random(20260826)
    viol_under, viol_cap, viol_waste = [], [], []
    for _ in range(400):
        n = rnd.randint(1, 12)
        counts = {f"k{i}": rnd.choice([0, 1, 3, 17, 400, 9000]) for i in range(n)}
        cap = rnd.choice([0, 1, 7, 100, 5000, 40000])
        keep = fs(counts, cap)
        if sum(keep.values()) > cap:
            viol_cap.append((counts, cap))
        present = {k: c for k, c in counts.items() if c > 0}
        if present:
            share = cap / len(present)
            for k, c in present.items():
                # THE PROPERTY: at or below the fair share -> untouched.
                if c <= share and keep[k] != c:
                    viol_under.append((k, c, share, keep[k]))
        # No waste: if some kind was truncated, capacity must be spent.
        if any(keep[k] < counts[k] for k in counts) and sum(keep.values()) < cap:
            viol_waste.append((counts, cap, keep))
    check("S3e 400 random cases: a kind at or below its fair share is NEVER evicted",
          not viol_under, str(viol_under[:2]))
    check("S3f 400 random cases: the capacity is never exceeded",
          not viol_cap, str(viol_cap[:2]))
    check("S3g 400 random cases: capacity is not left unspent while truncating",
          not viol_waste, str(viol_waste[:1]))
    check("S3h capacity below the number of kinds spends it on BREADTH",
          sum(fs({"a": 9, "b": 9, "c": 9}, 2).values()) == 2
          and max(fs({"a": 9, "b": 9, "c": 9}, 2).values()) == 1,
          str(fs({"a": 9, "b": 9, "c": 9}, 2)))
    check("S3i the result is deterministic (same input, same answer)",
          fs({"a": 900, "b": 3, "c": 900}, 101) == fs({"a": 900, "b": 3, "c": 900}, 101), "")


# ---------------------------------------------------------------------------
def s4():
    """S4 -- cycling kinds is not a way round it, and the number of kinds is
    bounded by this FILE rather than by traffic."""
    m = fresh()
    m.record(REAL_A, "REAL EVENT")
    for i in range(6000):
        m.record(ATTACKER[i % len(ATTACKER)], "y" * 40)
    rep = m.report()
    check("S4a a 6-kind, 6,000-frame flood still cannot evict the real event",
          REAL_A in rep["per_kind"], f"kinds={sorted(rep['per_kind'])}")
    check("S4b all six attacker kinds remain visible (none is starved out)",
          all(k in rep["per_kind"] for k in ATTACKER),
          f"missing={[k for k in ATTACKER if k not in rep['per_kind']]}")

    # The scheme is only sound if a peer cannot invent kinds. Every kind in the
    # core is a source literal or a call-site label; assert it over the AST so a
    # future f-string built from peer data fails here instead of silently
    # turning fair-sharing into per-frame sharing.
    import ast
    src = open(inspect.getsourcefile(cov), encoding="utf-8").read()
    dynamic = []
    for node in ast.walk(ast.parse(src)):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "record" and node.args):
            a = node.args[0]
            if isinstance(a, ast.Constant) and isinstance(a.value, str):
                continue
            if isinstance(a, ast.IfExp) and all(
                    isinstance(x, ast.Constant) for x in (a.body, a.orelse)):
                continue
            if isinstance(a, ast.JoinedStr) and all(
                    isinstance(v, ast.Constant)
                    or (isinstance(v, ast.FormattedValue)
                        and isinstance(v.value, ast.Name) and v.value.id == "label")
                    for v in a.values):
                continue          # _accept_loop's "peer"/"bridge" label
            dynamic.append(node.lineno)
    check("S4c every anomaly kind is a source literal or a call-site label",
          not dynamic, f"dynamic kinds at lines {dynamic}")


# ---------------------------------------------------------------------------
def s5():
    """S5 -- no silent cap (M34), and per_kind's shape is untouched."""
    m = fresh()
    m.record(REAL_A, "one")
    flood(m, "peer_message_error", 6000)
    rep = m.report()
    ev = rep.get("evicted_under_pressure")
    check("S5a report() carries a per-kind eviction count",
          isinstance(ev, dict) and ev.get("peer_message_error", 0) > 0, str(ev))
    check("S5b it names ONLY the kind that was actually over its share",
          list(ev) == ["peer_message_error"], str(ev))
    check("S5c the total and the flag agree with it",
          rep["total_evicted_under_pressure"] == sum(ev.values())
          and rep["buffer_pressure"] is True, "")
    check("S5d the counter is monotonic across reports",
          (flood(m, "peer_message_error", 600) or
           m.report()["total_evicted_under_pressure"]) > rep["total_evicted_under_pressure"], "")
    quiet = fresh(); quiet.record(REAL_A, "one")
    q = quiet.report()
    check("S5e an un-pressured buffer reports no pressure and empty counters",
          q["buffer_pressure"] is False and q["evicted_under_pressure"] == {}
          and q["total_evicted_under_pressure"] == 0, "")
    inner = set(rep["per_kind"][REAL_A])
    check("S5f per_kind's INNER shape is unchanged (20 suites read it)",
          inner == {"recent", "baseline", "expected_recent"}, str(sorted(inner)))
    for k in ("window_seconds", "baseline_seconds", "total_events_retained",
              "per_kind", "spikes", "spike_detected", "nonepoch_observations"):
        if k not in rep:
            check("S5g a pre-existing report key was dropped", False, k)
            return
    check("S5g every pre-existing report key is still present", True, "")
    src = code_only(inspect.getsource(cov.CovenantAPI)) if hasattr(cov, "CovenantAPI") else ""
    check("S5h /health warns while the buffer is under pressure",
          "buffer_pressure" in code_only(open(inspect.getsourcefile(cov),
                                              encoding="utf-8").read()), "")


# ---------------------------------------------------------------------------
def s6():
    """S6 -- the cost the flooder controls. Pins away the 33x amplification."""
    m = fresh()
    flood(m, "filler", 5000)
    hot = []
    for _ in range(3000):
        a = time.perf_counter(); m.record("peer_tx_id_invalid", "q" * 40)
        hot.append(time.perf_counter() - a)
    cold = fresh()
    cool = []
    for _ in range(3000):
        a = time.perf_counter(); cold.record("filler2", "f")
        cool.append(time.perf_counter() - a)
    hm, cm = statistics.median(hot), statistics.median(cool)
    p99 = sorted(hot)[int(len(hot) * 0.99)]
    ratio = hm / cm if cm else float("inf")
    check("S6a median cost at saturation is within 4x of an empty buffer",
          ratio <= 4.0, f"{hm*1e6:.2f}us vs {cm*1e6:.2f}us = {ratio:.1f}x (v8.37 was ~33x)")
    check("S6b amortisation holds: p99 stays under 3 ms",
          p99 < 3e-3, f"p99={p99*1e6:.0f}us")
    check("S6c 5,200 flood frames cost well under a second in total",
          statistics.mean(hot) * 5200 < 1.0, f"{statistics.mean(hot)*5200:.3f}s")
    # The peak matters separately from the median, because compaction happens
    # under the lock report() needs. Measured 0.6 ms once per _compact_batch
    # records, against v8.37's 12.75 us on EVERY record -- i.e. ~4 ms of lock
    # per 312 frames then, ~0.7 ms now. Better in peak and in total.
    worst = max(hot)
    check("S6d the worst single record holds the lock for under 5 ms",
          worst < 5e-3, f"max={worst*1e6:.0f}us, once per {fresh()._compact_batch} records")


# ---------------------------------------------------------------------------
def s7():
    """S7 -- the honest counter-measurement, recorded rather than discovered
    later. Truncating an over-share kind LOWERS its baseline, which lowers
    `expected`, which makes that kind EASIER to flag. Only kinds above their
    fair share are affected, so the direction is: the buffer becomes more
    sensitive about the kinds that are saturating it, and unchanged about
    everything else. Under v8.37 the same saturation made it blind to every
    kind but one, so this is the trade being made, stated in numbers."""
    t0 = time.time()
    m = fresh()
    with m._lock:
        # Two heavy kinds, both far above a 2-way fair share, spread over the
        # whole baseline window so neither is a spike on its own merits.
        for i in range(6000):
            m._events.append((t0 - 600 + (i % 600), "heavy_a", "a"))
            m._events.append((t0 - 600 + (i % 600), "heavy_b", "b"))
        m._events.sort()
    uncapped = m.report()
    m2 = fresh()
    with m2._lock:
        m2._events = list(m._events)
    m2._compact_locked()
    capped = m2.report()
    grew = [k for k in capped["per_kind"]
            if capped["per_kind"][k]["expected_recent"]
            < uncapped["per_kind"][k]["expected_recent"]]
    check("S7a truncation only ever lowers `expected` for the SATURATING kinds",
          set(grew) <= {"heavy_a", "heavy_b"}, str(grew))
    check("S7b both heavy kinds are still present after compaction (no wipeout)",
          {"heavy_a", "heavy_b"} <= set(capped["per_kind"]),
          str(sorted(capped["per_kind"])))
    check("S7c compaction leaves the two saturating kinds within one record "
          "of each other -- the share is fair, not first-come",
          abs(capped["per_kind"]["heavy_a"]["baseline"]
              - capped["per_kind"]["heavy_b"]["baseline"]) <= 1,
          f"a={capped['per_kind']['heavy_a']['baseline']} "
          f"b={capped['per_kind']['heavy_b']['baseline']}")


# ---------------------------------------------------------------------------
def s8():
    """S8 -- pin the rule in the SOURCE, on tokenized code (M42), so the next
    person "restoring the simple bound" fails a check instead of undoing this."""
    rec = code_only(inspect.getsource(cov.SpikingAnomalyMonitor.record))
    obs = code_only(inspect.getsource(cov.SpikingAnomalyMonitor.observe))
    old = "self . _events = self . _events [ - self . max_events :"
    check("S8a record() no longer evicts by recency",
          old.replace(" ", "") not in rec.replace(" ", ""), "")
    check("S8b observe() no longer evicts by recency",
          old.replace(" ", "") not in obs.replace(" ", ""), "")
    check("S8c both append sites route overflow through _compact_locked",
          "_compact_locked" in rec and "_compact_locked" in obs, "")
    comp = code_only(inspect.getsource(cov.SpikingAnomalyMonitor._compact_locked))
    check("S8d _compact_locked counts what it drops",
          "_evicted" in comp, "")
    for bad in ("open(", "requests", "socket", "Popen", "sys.exit", "raise"):
        if bad in comp:
            check("S8e the eviction path does I/O or can raise", False, bad)
            return
    check("S8e the eviction path is pure bookkeeping -- no I/O, no raise", True, "")
    check("S8f the hard ceiling is still max_events, not a widened one",
          "max_events" in rec and cov.SpikingAnomalyMonitor().max_events == 5000, "")


# ---------------------------------------------------------------------------
def s9():
    """S9 -- end to end on a REAL node through the REAL peer handler, read back
    through the REAL /anomalies route. S1-S7 drive the class directly; this is
    the one that proves the wiring."""
    import socket as _sock, tempfile
    db = os.path.join(tempfile.mkdtemp(), "a24.db")
    m = cov.CovenantUnifiedMaster("a24", host="127.0.0.1", port=5610,
                                  p2p_port=5611, db_path=db)
    node = m.node
    node.anomaly_monitor.record(REAL_A, "REAL EVENT: node B unreachable")

    sent = 0
    for _ in range(6000):
        a, b = _sock.socketpair()
        try:
            b.settimeout(2.0)
            # _handle_peer lives on the MASTER, not on P2PNode -- both read as
            # "the node" and landing in the wrong one is a silent AttributeError
            # on a daemon thread in production (M32).
            t = threading.Thread(target=m._handle_peer, args=(b, ("10.0.0.9", 1)),
                                 daemon=True)
            t.start()
            a.sendall(b"not json at all, on purpose")
            a.shutdown(_sock.SHUT_WR)
            t.join(timeout=2.0)
            sent += 1
        finally:
            try: a.close()
            except Exception: pass
    with m.api.app.test_client() as c:
        rep = c.get("/anomalies").get_json()
        health = c.get("/health").get_json()
    kinds = rep.get("per_kind", {})
    check("S9a the flood really did reach the real handler",
          kinds.get("peer_message_error", {}).get("baseline", 0) > 500,
          f"sent={sent} got={kinds.get('peer_message_error')}")
    check("S9b /anomalies still shows the real peer_send_failure",
          REAL_A in kinds, f"kinds={sorted(kinds)}")
    check("S9c /anomalies reports the pressure rather than hiding it",
          rep.get("buffer_pressure") is True
          and rep.get("total_evicted_under_pressure", 0) > 0,
          str(rep.get("evicted_under_pressure")))
    warns = " | ".join(health.get("warnings") or [])
    check("S9d /health warns an operator that the counts are a sample",
          "buffer under pressure" in warns, warns[:160])
    # Disclosure, not policy (M31/B2/P12): buffer pressure must NOT move
    # `degraded`, which is the node's own capability signal and is what a
    # monitor keys off. Here `degraded` is True only because of the mock judge
    # -- so assert the reason, not the bare bool: with a real judge a flooded
    # node must still read as capable.
    check("S9e buffer pressure does not move `degraded` -- it is capability, "
          "not weather",
          # NB no `.get(k, True)` clause here: a default-True assertion is
          # satisfied by the key being ABSENT, which is not a check (M30).
          health.get("degraded") is True
          and health.get("version") == cov.COVENANT_VERSION,
          f"degraded={health.get('degraded')} v={health.get('version')}")
    pressured = node.anomaly_monitor
    node.anomaly_monitor = cov.SpikingAnomalyMonitor()      # same node, empty buffer
    try:
        with m.api.app.test_client() as c2:
            h2 = c2.get("/health").get_json()
        check("S9f the SAME node with an unpressured buffer reports the same "
              "`degraded` -- the flood changed disclosure only",
              h2.get("degraded") == health.get("degraded"),
              f"{h2.get('degraded')} vs {health.get('degraded')}")
        check("S9g and the pressure warning is absent when there is none",
              not any("buffer under pressure" in w for w in (h2.get("warnings") or [])),
              str(h2.get("warnings")))
    finally:
        node.anomaly_monitor = pressured
    try:
        node.running = False
    except Exception:
        pass


# ---------------------------------------------------------------------------
def s10():
    """S10 (A24b, v8.39) -- THE PRESSURE FLAG IS PRESENT TENSE.

    A24's own fix left one thing for the attacker. `buffer_pressure` was
    `bool(self._evicted)`, and `_evicted` is monotonic and never reset, so ONE
    6,000-frame flood turned on a /health warning that never turned off again.
    Measured on the v8.38 that introduced it: at +15 min ZERO evicted records
    remained inside report()'s baseline window -- per_kind was a complete
    census again -- and /health still said "anomaly buffer under pressure"; at
    +30 days, still. So a peer who could no longer choose what /anomalies SAYS
    could still choose, with one socket, what /health WARNS, for the life of
    the process: M34's disease (an alert that never clears trains its reader to
    skim) introduced by the fix for M34's disease one layer down.

    The flag is now bounded by the SAME window report() reports on, which is
    exactly the interval over which "these counts are a sample, not a census"
    is a true sentence. The counters stay monotonic and unconditional -- the
    permanent record is not what was wrong.
    """
    m = fresh()
    m.record(REAL_A, "REAL EVENT")
    flood(m, "peer_message_error", 6000)
    hot = m.report()
    check("S10a while the flood is live, pressure is reported",
          hot["buffer_pressure"] is True, str(hot["total_evicted_under_pressure"]))
    check("S10b the report says HOW OLD the last eviction is, not just how many",
          # NB: not `x or DEFAULT` -- an age of 0.0 is a real measurement and
          # `or` swallows it (M50, re-committed here within an hour of reading
          # it, which is why the check is written this way and said so).
          isinstance(hot.get("last_eviction_age_seconds"), float)
          and hot["last_eviction_age_seconds"] < 60,
          str(hot.get("last_eviction_age_seconds")))

    real = time.time
    cov.time.time = lambda: real() + s10.OFFSET
    try:
        s10.OFFSET = m.baseline_seconds + 60.0        # every evicted record now
        cool = m.report()                             # outside the window
        check("S10c once every evicted record is older than the baseline "
              "window, the flag CLEARS", cool["buffer_pressure"] is False,
              f"age={cool.get('last_eviction_age_seconds')}s "
              f"baseline={m.baseline_seconds}s")
        check("S10d and the permanent record is untouched -- bounded, not deleted",
              cool["total_evicted_under_pressure"]
              == hot["total_evicted_under_pressure"]
              and cool["evicted_under_pressure"] == hot["evicted_under_pressure"],
              f"{cool['total_evicted_under_pressure']} vs "
              f"{hot['total_evicted_under_pressure']}")
        check("S10e the flag's claim is TRUE when it clears: nothing evicted "
              "could still be inside the window it reports on",
              isinstance(cool.get("last_eviction_age_seconds"), float)
              and cool["last_eviction_age_seconds"] > m.baseline_seconds,
              f"{cool.get('last_eviction_age_seconds')} > {m.baseline_seconds}")
        # Not one-shot. Clearing costs the attacker the only thing worth having:
        # they have to stop. Resuming must turn it straight back on.
        flood(m, "peer_message_error", 6000)
        again = m.report()
        check("S10f resuming the flood turns it back ON",
              again["buffer_pressure"] is True,
              str(again.get("last_eviction_age_seconds")))
        check("S10g and the monotonic total has GROWN, so a reader can trend "
              "the attack even while the flag is off",
              again["total_evicted_under_pressure"]
              > hot["total_evicted_under_pressure"], "")
    finally:
        cov.time.time = real
        s10.OFFSET = 0.0

    q = fresh()
    q.record(REAL_A, "one")
    check("S10h NEVER evicted reports None, not 0 -- absence of an event is "
          "not an event at time zero (M50)",
          "last_eviction_age_seconds" in q.report()
          and q.report()["last_eviction_age_seconds"] is None
          and q.report()["buffer_pressure"] is False,
          str(q.report().get("last_eviction_age_seconds")))

    # End to end on the REAL /health route, without touching the clock: a
    # monitor carrying a STALE eviction is exactly a node that was flooded and
    # is no longer being flooded.
    import tempfile
    db = os.path.join(tempfile.mkdtemp(), "a24b.db")
    m2 = cov.CovenantUnifiedMaster("a24b", host="127.0.0.1", port=5630,
                                   p2p_port=5631, db_path=db)
    try:
        stale = cov.SpikingAnomalyMonitor()
        stale.record(REAL_A, "REAL EVENT")
        flood(stale, "peer_message_error", 6000)
        stale._last_evict_ts = time.time() - (stale.baseline_seconds + 60.0)
        m2.node.anomaly_monitor = stale
        with m2.api.app.test_client() as c:
            h = c.get("/health").get_json()
            an = c.get("/anomalies").get_json()
        warns = " | ".join(h.get("warnings") or [])
        check("S10i /health no longer warns about a flood that stopped",
              "buffer under pressure" not in warns, warns[:150])
        check("S10j but /anomalies still carries the evidence it happened",
              an.get("total_evicted_under_pressure", 0) > 0
              and an.get("last_eviction_age_seconds", 0) > stale.baseline_seconds,
              f"total={an.get('total_evicted_under_pressure')} "
              f"age={an.get('last_eviction_age_seconds')}")
        stale._last_evict_ts = time.time()
        with m2.api.app.test_client() as c:
            h2 = c.get("/health").get_json()
        check("S10k and the SAME node warns again the moment eviction resumes",
              any("buffer under pressure" in w for w in (h2.get("warnings") or [])),
              str(h2.get("warnings"))[:150])
    finally:
        try:
            m2.node.running = False
        except Exception:
            pass


s10.OFFSET = 0.0


if __name__ == "__main__":
    print(f"A24 -- a flood of one kind may not decide what /anomalies says  "
          f"({cov.COVENANT_VERSION}, {cov.CORE_SOURCE_SHA12})\n")
    for fn in (s1, s2, s3, s4, s5, s6, s7, s8, s9, s10):
        try:
            fn()
        except Exception as e:
            check(f"{fn.__name__} raised", False, f"{type(e).__name__}: {e}")
        print()
    p = sum(1 for _, ok in results if ok)
    print(f"A24: {p}/{len(results)} passed")
    sys.exit(0 if p == len(results) else 1)
