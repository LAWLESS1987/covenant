#!/usr/bin/env python3
"""
test_hw1_takeover_detectors.py -- HW1. The two takeover-resistance highway
detectors (head_commitment_broken, consent_chain_broken), driven BOTH ways in a
temp dir: a clean state reads ABSENT, each tamper reads PRESENT, and -- the point
of an ALARM-only guard -- NEITHER detector has an auto-remedy, so a tamper can
only ever surface as "needs a person", never be auto-"healed" (which would erase
the evidence). Rule 8; never touches the real ledgers.
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_highway as H          # noqa: E402
import covenant_consent_chain as cc   # noqa: E402
import covenant_head_commit as hc     # noqa: E402

_results = []


def check(label, cond, detail=""):
    _results.append(bool(cond))
    print(f"{'ok   ' if cond else 'FAIL '} {label}{('  -- ' + detail) if detail and not cond else ''}")


def _write(path, rows):
    with open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")


def main():
    # ---- consent_chain_broken, both ways ----
    with tempfile.TemporaryDirectory() as tmp:
        led = os.path.join(tmp, "c.jsonl")
        chn = os.path.join(tmp, "c.chain.jsonl")
        rows = [{"by": "tetsu", "kind": "k0", "answer": "yes"},
                {"by": "tetsu", "kind": "k1", "answer": "No, I don't want this"}]
        _write(led, rows)
        cc.sync(led, chn)

        d = H.detect_consent_chain_broken(ledger=led, chain=chn)
        check("HW1 clean consent chain -> detector ABSENT", d["state"] == H.ABSENT, str(d))

        bad = list(rows); bad[1] = dict(bad[1], answer="yes, go ahead")  # flip the NO
        _write(led, bad)
        d = H.detect_consent_chain_broken(ledger=led, chain=chn)
        check("HW1 edited consent 'no' -> PRESENT + tamper=True",
              d["state"] == H.PRESENT and d["measured"].get("tamper") is True, str(d))
        _write(led, rows)

        _write(led, rows[:1])  # truncate
        d = H.detect_consent_chain_broken(ledger=led, chain=chn)
        check("HW1 truncated consent row -> PRESENT + tamper=True",
              d["state"] == H.PRESENT and d["measured"].get("tamper") is True, str(d))
        _write(led, rows)

        _write(led, rows + [{"by": "tetsu", "kind": "forged", "answer": "yes"}])  # unchained append
        d = H.detect_consent_chain_broken(ledger=led, chain=chn)
        check("HW1 unchained append -> PRESENT + tamper=False (a person must confirm)",
              d["state"] == H.PRESENT and d["measured"].get("tamper") is False, str(d))

    # ---- head_commitment_broken, both ways ----
    with tempfile.TemporaryDirectory() as tmp:
        key = os.path.join(tmp, "k.key")
        pub = os.path.join(tmp, "pub.pem")
        led = os.path.join(tmp, "hc.jsonl")
        open(os.path.join(tmp, "MANIFEST.sha256"), "w").write("aa  x.py\n")
        json.dump({"hash": "0000beef"}, open(os.path.join(tmp, "genesis.json"), "w"))
        hc.make_commitment(repo=tmp, key_path=key, pubkey_path=pub, ledger=led, now=1700000000)
        hc.make_commitment(repo=tmp, key_path=key, pubkey_path=pub, ledger=led, now=1700000001)

        d = H.detect_head_commitment_broken(ledger=led, pub=pub, repo=tmp)
        check("HW1 clean HEAD-commitment ledger -> detector ABSENT", d["state"] == H.ABSENT, str(d))

        rowz = [json.loads(x) for x in open(led, encoding="utf-8") if x.strip()]
        rowz[0]["payload"]["head"] = "f" * 40  # forge a signed field
        _write(led, rowz)
        d = H.detect_head_commitment_broken(ledger=led, pub=pub, repo=tmp)
        check("HW1 forged HEAD-commitment payload -> PRESENT (signature FAIL)",
              d["state"] == H.PRESENT, str(d))

    # ---- model_drift, both ways ----
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "ops"))
        for name in ("fallback_model.json", "fallback_model_2.json", "fallback_model_phone.json"):
            open(os.path.join(tmp, name), "w").write('{"model": "%s"}' % name)
        import hashlib as _h
        pins = {name: _h.sha256(open(os.path.join(tmp, name), "rb").read()).hexdigest()
                for name in ("fallback_model.json", "fallback_model_2.json", "fallback_model_phone.json")}
        pinpath = os.path.join(tmp, "ops", "model_pin.json")
        json.dump({"models": pins}, open(pinpath, "w"))

        d = H.detect_model_drift(pin=pinpath, repo=tmp)
        check("HW1 live models match the pin -> ABSENT", d["state"] == H.ABSENT, str(d))

        open(os.path.join(tmp, "fallback_model.json"), "w").write('{"model": "SWAPPED"}')  # runtime swap
        d = H.detect_model_drift(pin=pinpath, repo=tmp)
        check("HW1 a live model differs from the pin -> PRESENT (drifted)",
              d["state"] == H.PRESENT and "fallback_model.json" in d["measured"].get("drifted", []), str(d))

        os.remove(os.path.join(tmp, "fallback_model_2.json"))  # a pinned model vanished
        d = H.detect_model_drift(pin=pinpath, repo=tmp)
        check("HW1 a pinned model file missing -> PRESENT (missing)",
              d["state"] == H.PRESENT and "fallback_model_2.json" in d["measured"].get("missing", []), str(d))

    # ---- the ALARM-only invariant: no takeover guard may have an auto-remedy ----
    guarded = {"head_commitment_broken", "consent_chain_broken", "model_drift"}
    remedied = {det for name, r in H.REMEDIES.items() for det in r.get("for", ())}
    check("HW1 neither takeover guard has ANY remedy (ALARM-only, cannot auto-heal a tamper)",
          not (guarded & remedied), str(guarded & remedied))
    auto = {det for name, r in H.REMEDIES.items()
            if r.get("klass") == H.AUTO_REVERSIBLE for det in r.get("for", ())}
    check("HW1 neither guard is wired to an AUTO_REVERSIBLE remedy", not (guarded & auto), str(guarded & auto))

    # ---- both are actually registered on the road ----
    check("HW1 both guards are registered detectors", guarded <= set(H.DETECTORS),
          str(guarded - set(H.DETECTORS)))

    passed, total = sum(_results), len(_results)
    print(f"\nHW1: {passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
