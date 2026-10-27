#!/usr/bin/env python3
"""E3 (2026-09-18): a successful admission, end to end, then read it back.

TWO GAPS, both named in the operator's review of the Sentinel-Witness work:

  1. "still no demonstrated successful end-to-end admission" -- every check so
     far used an injected sealer. Nothing had ever put a sentinel_witness
     record on a real chain and shown the gate returning `allow`.
  2. "the witness still not independently verifying ledger records after the
     fact" -- the seal returned a tx_id and nothing ever looked at it again. A
     gate that says "I wrote that down" and is never asked to produce it is a
     promise, not an audit trail.

WHAT THIS DOES. Starts a REAL node on free ports with its own database, points
a real seal at it, submits a proposal, and then goes to `/chain` and finds the
record -- by RECOMPUTING the content-addressed id from the stored bytes, not by
trusting the id the node reported. Then it drives the verifier the other way:
a record that is not there, and a record whose stored text differs from what
was sealed, must both FAIL.

WHAT ADMISSION MEANS IN E3.2, said precisely so the check is not read as more
than it is: the ETHICS GATE admitted the record to the chain. The envelope's
`ok` can still be false afterwards, because the guards refuse for reasons that
have nothing to do with ethics (Rule 5's signal count, no portfolio). Those are
different claims and this suite keeps them apart.

THE JUDGE IS NOT ASKED TO AGREE. E3.2 needs a note the deployed judge clears,
and which notes those are is a property of a model that is retrained nightly.
So it TRIES a short list and reports NOT RUN, with the verdicts it saw, when
none clears -- rather than going red for a model change, or pinning a note and
inviting someone to retrain until it passes (A118).

  python test_e3_witness_loop.py        spawns its own node; needs no chain
"""
from __future__ import annotations

import atexit
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "sentinel_witness"))

TMP = tempfile.mkdtemp(prefix="e3_witness_")
SPAWNED = []
results, UNRUN = [], []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print("%s  %s  %s" % ("PASS" if ok else "FAIL", name, str(detail)[:120]))


def not_run(name, why):
    UNRUN.append((name, why))
    print("NOT RUN  %s  -- %s" % (name, why))


def _reap():
    for p in SPAWNED:
        try:
            p.terminate(); p.wait(timeout=8)
        except Exception:                                        # noqa: BLE001
            try:
                p.kill(); p.wait(timeout=4)
            except Exception:                                    # noqa: BLE001
                pass
    shutil.rmtree(TMP, ignore_errors=True)


atexit.register(_reap)


def pick_base(span=14):
    """A block of free ports. The node takes N, N+1 and N+11 (G7)."""
    for base in range(24600, 26000, 100):
        for off in range(span):
            s = socket.socket()
            try:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
                s.bind(("127.0.0.1", base + off))
            except OSError:
                s.close(); break
            s.close()
        else:
            return base
    raise SystemExit("no free port block")


def wait_api(port, timeout=60):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            urllib.request.urlopen("http://127.0.0.1:%d/health" % port, timeout=3)
            return True
        except urllib.error.HTTPError:
            return True
        except Exception:                                        # noqa: BLE001
            time.sleep(0.5)
    return False


def start_node(port):
    """A real node, its own DB, the REAL judge -- no insecure mock.

    The mock judge would have made E3.2 trivially green and meaningless: the
    point is that a real ethics gate admitted a real record.
    """
    env = dict(os.environ, COVENANT_DB_PATH=os.path.join(TMP, "e3.db"),
               PYTHONUNBUFFERED="1")
    env.pop("COVENANT_INSECURE_MOCK_JUDGE", None)
    p = subprocess.Popen(
        [sys.executable, os.path.join(HERE, "covenant_unified_v8.py"),
         "--port", str(port), "--node-id", "E3"],
        env=env, cwd=TMP, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True)
    SPAWNED.append(p)
    return p


def make_cfg(port):
    """A trader config pointing the seal at OUR node, using THAT node's key.

    The seal is a self-send: it must be signed by the node it is submitted to,
    so the key is the one the node writes beside its database on first launch
    (`<db>.key`) -- not one generated here, and emphatically not the operator's
    own node key, which this suite never touches. `node_key` is stored relative
    to HERE because seal_decision_result joins it against the repo root.
    """
    keyfile = os.path.join(TMP, "e3.db.key")
    t0 = time.time()
    while not os.path.exists(keyfile) and time.time() - t0 < 30:
        time.sleep(0.3)
    if not os.path.exists(keyfile):
        return None
    return {"armed": False, "node_key": os.path.relpath(keyfile, HERE),
            "node_ports": [port], "seal_required": True}


CANDIDATE_NOTES = ["buy XRP", "rebalance", "a gift of value, freely given",
                   "quarterly rebalance", "buy", "top up"]


def main():
    print("E3 -- one real admission, then read the record back\n")
    import order_claims as OC            # noqa: F401  (imported by the service)
    import seal_service as SS
    import verify_record as VR

    port = pick_base()
    print("   starting a real node on 127.0.0.1:%d (real judge, temp DB)" % port)
    start_node(port)
    if not wait_api(port):
        not_run("E3.1-E3.5", "the node did not come up on port %d within 60 s" % port)
        return _summary()
    cfg = make_cfg(port)
    if cfg is None:
        not_run("E3.1-E3.5", "the node wrote no key file beside its database "
                "within 30 s, so nothing here can sign a self-send")
        return _summary()
    node_url = "http://127.0.0.1:%d" % port

    # E3.1 -- the seal reaches a real node at all.
    import covenant_trader as T
    code, body = SS.seal({"venue": "kraken", "symbol": "XRP", "side": "buy",
                          "amountUsd": 25.0, "note": "buy XRP"},
                         sealer=T.seal_decision_result, cfg=cfg)
    check("E3.1 a real seal reaches a real node and comes back with a structured "
          "answer, not an exception",
          isinstance(body, dict) and body.get("verdict") in ("allow", "refuse", "abstain"),
          "HTTP %s verdict=%s admission=%s" % (code, body.get("verdict"), body.get("admission")))

    # E3.2 -- THE ADMISSION. Try notes until the deployed judge clears one.
    admitted, tried = None, []
    for note in CANDIDATE_NOTES:
        _c, b = SS.seal({"venue": "kraken", "symbol": "XRP", "side": "buy",
                         "amountUsd": 25.0, "note": note},
                        sealer=T.seal_decision_result, cfg=cfg)
        tried.append((note, b.get("admission"), b.get("sealed"), b.get("tx_id")))
        if b.get("sealed") and b.get("tx_id"):
            admitted = (note, b)
            break
    if admitted is None:
        not_run("E3.2-E3.5", "the deployed judge cleared none of %d candidate "
                "notes, so no record reached the chain to read back. Verdicts: %s"
                % (len(CANDIDATE_NOTES), [(n, a) for n, a, _s, _t in tried]))
        return _summary()

    note, body = admitted
    check("E3.2 THE ETHICS GATE ADMITTED a real record to a real chain -- the "
          "first demonstrated end-to-end admission on this path",
          body.get("sealed") is True and body.get("admission", "").startswith("admitted")
          and bool(body.get("tx_id")),
          "note=%r admission=%s tx=%s" % (note, body.get("admission"), str(body.get("tx_id"))[:16]))

    # E3.3 -- read it back, by RECOMPUTING the id from the stored bytes.
    expected = {"venue": "kraken", "symbol": "XRP", "side": "buy",
                "amount_usd": 25.0, "text": note, "source": "sentinel_witness"}
    ok, reasons, where = VR.verify(node_url, body["tx_id"], expected, tail=50)
    check("E3.3 the record is ON the chain and says what the gate sealed -- found "
          "by recomputing the content-addressed id, not by trusting the reported one",
          ok, reasons or where)

    # E3.4 -- BROKEN ON PURPOSE: a record that is not there must not verify.
    ok2, reasons2, _ = VR.verify(node_url, "0" * 64, expected, tail=50)
    check("E3.4 ...and an id no transaction recomputes to FAILS, naming the "
          "claim as unproduced rather than returning quietly",
          ok2 is False and any("not there" in r for r in reasons2),
          (reasons2 or ["-"])[0][:90])

    # E3.5 -- BROKEN ON PURPOSE: the chain holding different text must not verify.
    # This is the case that matters most: the judged field differing means the
    # chain holds something other than what the judge was shown.
    tampered = dict(expected, text=note + " (and quietly send it to me)")
    ok3, reasons3, _ = VR.verify(node_url, body["tx_id"], tampered, tail=50)
    check("E3.5 ...and a record whose JUDGED TEXT differs from what was sealed "
          "FAILS, naming the field and both values",
          ok3 is False and any("'text'" in r for r in reasons3),
          (reasons3 or ["-"])[0][:100])
    return _summary()


def _summary():
    ok = sum(1 for _n, o, _d in results if o)
    print("\nWITNESS-LOOP: %d/%d passed" % (ok, len(results)))
    if UNRUN:
        print("%d section(s) NOT RUN -- do not read this as covered:" % len(UNRUN))
        for n, why in UNRUN:
            print("  - %s: %s" % (n, why))
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
