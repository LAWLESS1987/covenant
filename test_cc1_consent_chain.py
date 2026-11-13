#!/usr/bin/env python3
"""
test_cc1_consent_chain.py -- CC1. The consent hash-chain, driven BOTH ways: a
synced ledger verifies PASS, and every tamper (edited past row, truncation,
unsynced/forged append, broken chain link) turns the verifier's OWN check red
(CLAUDE.md rule 8). Offline, in a temp dir; the real ledger is read once at the
end (verify only) and never written.

2026-11-13: the line ending is not part of a row. The same record must verify on
an LF checkout, on a CRLF working tree and on the mixed tree that sealed it, and
an edit to a row's CONTENT must still fail in every one of them.
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_consent_chain as cc   # noqa: E402

_results = []


def check(label, cond, detail=""):
    _results.append(bool(cond))
    print(f"{'ok   ' if cond else 'FAIL '} {label}{('  -- ' + detail) if detail and not cond else ''}")


def write_rows(path, rows):
    with open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")


def main():
    with tempfile.TemporaryDirectory() as tmp:
        led = os.path.join(tmp, "consent.jsonl")
        chn = os.path.join(tmp, "consent.chain.jsonl")
        rows = [
            {"t": "2026-10-01T00:00:00Z", "by": "tetsu", "kind": "k0", "answer": "yes"},
            {"t": "2026-10-02T00:00:00Z", "by": "tetsu", "kind": "k1", "answer": "No, I don't want this"},
            {"t": "2026-10-03T00:00:00Z", "by": "tetsu", "kind": "k2", "answer": "yes"},
        ]
        write_rows(led, rows)
        added, tip0, err = cc.sync(led, chn)
        ok, _ = cc.verify(led, chn)
        check("CC1 a synced 3-row consent ledger verifies PASS", added == 3 and err is None and ok)

        # S2: edit a past row (the "no") without touching the chain -> row-hash FAIL
        bad = list(rows); bad[1] = dict(bad[1], answer="yes, go ahead")   # flip the recorded NO
        write_rows(led, bad)
        ok2, f2 = cc.verify(led, chn)
        check("CC1 editing a recorded consent row -> FAIL (row-hash)",
              (not ok2) and any("edited in place" in m for m in f2), "; ".join(f2))
        write_rows(led, rows)   # restore

        # S3: truncate (remove the last row) -> ledger shorter than chain
        write_rows(led, rows[:2])
        ok3, f3 = cc.verify(led, chn)
        check("CC1 a removed/truncated row -> FAIL (ledger < chain)",
              (not ok3) and any("removed/truncated" in m for m in f3), "; ".join(f3))
        write_rows(led, rows)   # restore

        # S4: forged append with no chain entry -> ledger longer than chain
        write_rows(led, rows + [{"t": "2026-10-04T00:00:00Z", "by": "tetsu", "kind": "forged", "answer": "yes"}])
        ok4, f4 = cc.verify(led, chn)
        check("CC1 an unsynced/forged append -> FAIL (not chained)",
              (not ok4) and any("NOT chained" in m for m in f4), "; ".join(f4))

        # S5: sync REFUSES to extend over a tamper (edit row 1, then try to sync)
        write_rows(led, rows)                       # back to 3 clean rows (chain already covers them)
        bad = list(rows); bad[1] = dict(bad[1], answer="yes, go ahead")
        write_rows(led, bad)
        added5, _, err5 = cc.sync(led, chn)
        check("CC1 sync REFUSES to paper over an edited row", added5 == 0 and err5 is not None,
              "sync should not extend over a broken chain")
        write_rows(led, rows)   # restore

        # S6: break the chain's own prev link -> chain-link FAIL
        chain = cc.read_chain(chn)
        chain[2]["prev"] = "0" * 64
        with open(chn, "w", encoding="utf-8") as fh:
            for e in chain:
                fh.write(json.dumps(e, sort_keys=True, separators=(",", ":")) + "\n")
        ok6, f6 = cc.verify(led, chn)
        check("CC1 a broken prev-hash link -> FAIL (chain tampered)",
              (not ok6) and any("link is broken" in m for m in f6), "; ".join(f6))

        # S7: a genuine new row synced cleanly -> PASS again, tip advances
        # (rebuild clean chain first since S6 corrupted it)
        os.remove(chn)
        cc.sync(led, chn)
        t_before = cc.tip(chn)
        cc.append_consent({"by": "tetsu", "kind": "k3", "answer": "yes"}, led, chn)
        ok7, _ = cc.verify(led, chn)
        check("CC1 append_consent adds row+chain atomically, still PASS, tip advances",
              ok7 and cc.tip(chn) != t_before)

    # ---- line endings (2026-11-13) ----
    with tempfile.TemporaryDirectory() as tmp:
        led = os.path.join(tmp, "consent.jsonl")
        chn = os.path.join(tmp, "consent.chain.jsonl")
        lines = [json.dumps(r, ensure_ascii=False, sort_keys=True).encode("utf-8") for r in (
            {"t": "2026-10-01T00:00:00Z", "by": "tetsu", "kind": "k0", "answer": "yes"},
            {"t": "2026-10-02T00:00:00Z", "by": "tetsu", "kind": "k1", "answer": "No, I don't want this"},
            {"t": "2026-10-03T00:00:00Z", "by": "tetsu", "kind": "k2", "answer": "yes"})]
        sealed_with = [b"\r\n", b"\n", b"\r\n"]      # what the Windows tree that sealed it held, row by row

        def put(rows, endings):
            with open(led, "wb") as fh:
                fh.write(b"".join(row + end for row, end in zip(rows, endings)))

        # The chain exactly as the old code wrote it there: each entry over the row's bytes up to the newline,
        # carriage return included.
        prev = cc.ZERO
        with open(chn, "wb") as fh:
            for i, (row, end) in enumerate(zip(lines, sealed_with)):
                e = {"seq": i, "row_sha256": cc._sha(row + end[:-1]), "prev": prev, "t": "2026-10-29T00:00:00Z"}
                fh.write(cc._canon(e) + b"\n")
                prev = cc._sha(cc._canon(e))

        forms = {"the tree that sealed it (mixed)": sealed_with, "an LF checkout": [b"\n"] * 3,
                 "a CRLF working tree": [b"\r\n"] * 3}
        for name, endings in forms.items():
            put(lines, endings)
            ok, f = cc.verify(led, chn)
            check(f"CC1 a record sealed over CRLF bytes verifies on {name}", ok, "; ".join(f))

        edited = list(lines)
        edited[1] = edited[1].replace(b"No, I don't want this", b"yes, go ahead")     # flip the recorded NO
        for name, endings in forms.items():
            put(edited, endings)
            ok, f = cc.verify(led, chn)
            check(f"CC1 an edited row still FAILS on {name}",
                  (not ok) and any("chain[1]" in m and "edited in place" in m for m in f) and len(f) == 1, "; ".join(f))

        inside = list(lines)
        inside[0] = inside[0].replace(b'"answer"', b'"answer"\r')      # a carriage return INSIDE a row is content
        put(inside, [b"\n"] * 3)
        ok, f = cc.verify(led, chn)
        check("CC1 a carriage return inside a row is content, not a line ending -> FAIL", not ok, "; ".join(f))

        one_byte = list(lines)
        one_byte[2] = one_byte[2][:-1] + b" }"                             # one byte of content, both endings
        for endings in ([b"\n"] * 3, [b"\r\n"] * 3):
            put(one_byte, endings)
            check("CC1 one changed byte matches neither form of the hash", not cc.verify(led, chn)[0])

        put(edited, [b"\n"] * 3)
        added, _, err = cc.sync(led, chn)
        check("CC1 sync still REFUSES to extend over an edited row of such a record", added == 0 and err is not None)

        put(lines, [b"\n"] * 3)
        cc.append_consent({"by": "tetsu", "kind": "k3", "answer": "yes"}, led, chn)
        with open(led, "rb") as fh:
            data = fh.read()
        with open(chn, "rb") as fh:
            chain_bytes = fh.read()
        ok, f = cc.verify(led, chn)
        check("CC1 a row appended now ends in a bare newline on every platform, and so does its chain entry",
              ok and data.endswith(b"\n") and not data.endswith(b"\r\n") and data.count(b"\r") == 0
              and not chain_bytes.endswith(b"\r\n"), "; ".join(f))
        new_entry = cc.read_chain(chn)[-1]
        new_row = cc.read_ledger_lines(led)[-1]
        check("CC1 a new entry commits the row WITHOUT a carriage return",
              new_entry["row_sha256"] == cc._sha(new_row) and not new_row.endswith(b"\r"))
        with open(led, "wb") as fh:                                        # the same record, checked out CRLF
            fh.write(data.replace(b"\n", b"\r\n"))
        check("CC1 ...and that record verifies when checked out CRLF", cc.verify(led, chn)[0])

    # The repository's own record, read only. On an LF checkout this was FAIL for six of nine rows until 2026-11-13.
    if os.path.exists(cc.LEDGER) and os.path.exists(cc.CHAIN):
        ok, f = cc.verify()
        check("CC1 the repository's own consent record verifies on this checkout", ok, "; ".join(f[:3]))

    passed, total = sum(_results), len(_results)
    print(f"\nCC1: {passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
