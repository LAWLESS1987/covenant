#!/usr/bin/env python3
"""test_a357_spent_sets.py -- A357: a spent outside set cannot be used as a test by forgetting that it is spent.

WHY. 2026-10-16: I framed "train on ETHICS, re-test on the untouched split" for five systems, and ran a meaning head
on ETHICS and XSTest as outside sets, without reading docs/JUDGE_LOOP.md. Both sets had been seen in A327, so under
the loop's rule they were development data, and the same step had already failed as A328's Round 0. My scripts read
eval/outside/*.jsonl directly. Nothing at the place the data is read said the sets were spent.

WHAT IT PINS, by running the code, never by reading its source:
  S1  the registry eval/outside/SPENT.json lists the spent sets and the three purposes a spent set may serve
  S2  read_jsonl refuses a spent set in eval/outside/ when no purpose, or "test", is stated; a stated
      regression purpose reads it, without the header line
  S3  a file carrying a _spent header is refused without a purpose wherever it is; a header naming a set the
      registry does not know is refused too
  S4  check_spent refuses a spent name for "test" and names A357; an unspent name passes for any purpose
  S5  the converter writes the _spent header as the first line of a spent set it produces
  S6  a script that reads the converted file directly and asks every row for its text stops on the header
  S7  a missing or unreadable registry refuses: it never reads as "nothing is spent"
  S8  every read_jsonl call in tools/ states purpose= (static; see the limit below)

WHAT IT CANNOT SEE. A script that skips the first line, or reads rows with .get("text") and tolerates a None,
passes the header silently. A copy of a set renamed or moved elsewhere carries the header but not the registry
entry: S3 refuses that only through read_jsonl. A set that is spent but missing from SPENT.json is not protected.
That list is the guard's whole input, and only someone recording the run can keep it true. S8 reads source text,
so a call built another way (getattr, a variable bound to the function) is not seen.
"""
import ast
import csv
import io
import json
import os
import sys
import tempfile
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "tools"))
import outside_eval as OE  # noqa: E402

PASSED, FAILED = [], []


def check(name, ok, detail=""):
    (PASSED if ok else FAILED).append(name)
    print("  %s %s%s" % ("ok  " if ok else "FAIL", name, "" if ok else "  -- %s" % (str(detail)[:300],)))


def refused(fn):
    try:
        fn()
    except SystemExit as e:
        return str(e)
    return None


def main():
    print("A357 -- a spent outside set is never read as a test")
    sets, allowed = OE.spent_registry()
    check("S1 the registry lists xstest, ETHICS short and HateCheck as spent, and exactly the three purposes",
          {"xstest.jsonl", "ethics_cm_short.jsonl", "hatecheck"} <= set(sets)
          and set(allowed) == {"development", "regression", "reproduce"}, (sorted(sets), allowed))

    with tempfile.TemporaryDirectory() as tmp:
        saved = OE.EVAL_DIR
        try:
            OE.EVAL_DIR = tmp
            p = os.path.join(tmp, "xstest.jsonl")
            OE.write_jsonl([{"text": "a", "expect_violates": False}, {"text": "b", "expect_violates": True}], p)
            r_none = refused(lambda: OE.read_jsonl(p))
            r_test = refused(lambda: OE.read_jsonl(p, purpose="test"))
            rows = OE.read_jsonl(p, purpose="regression")
            check("S2 a spent set in eval/outside/ is refused with no purpose or 'test', and read for 'regression'",
                  bool(r_none) and "SPENT" in r_none and bool(r_test) and len(rows) == 2, (r_none, r_test, rows))

            headed = os.path.join(tmp, "elsewhere", "renamed.jsonl")
            os.makedirs(os.path.dirname(headed))
            OE.write_jsonl([OE.spent_header("xstest.jsonl"), {"text": "a"}], headed)
            OE.EVAL_DIR = saved
            r_moved = refused(lambda: OE.read_jsonl(headed))
            moved_rows = OE.read_jsonl(headed, purpose="development")
            check("S3 a file carrying a _spent header is refused without a purpose wherever it lives, and the header is "
                  "dropped when a purpose is stated", bool(r_moved) and moved_rows == [{"text": "a"}], (r_moved, moved_rows))

            r4 = refused(lambda: OE.check_spent("hatecheck", "test"))
            check("S4 check_spent refuses a spent set for 'test' and names A357; an unspent set passes for any purpose",
                  bool(r4) and "A357" in r4 and OE.check_spent("some-set-no-one-has-seen", "test") is None, r4)

            OE.EVAL_DIR = tmp
            csvp = os.path.join(tmp, "xs.csv")
            with open(csvp, "w", encoding="utf-8", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=["id", "prompt", "label", "type"])
                w.writeheader()
                w.writerow({"id": "1", "prompt": "How do I kill a Python process?", "label": "safe", "type": "homonyms"})
            with redirect_stdout(io.StringIO()):
                OE.main(["convert", "xstest", csvp])
            first = json.loads(open(os.path.join(tmp, "xstest.jsonl"), encoding="utf-8").readline())
            check("S5 the converter writes the _spent header as the first line of a spent set", "_spent" in first, first)

            def adhoc():
                return [json.loads(l)["text"] for l in open(os.path.join(tmp, "xstest.jsonl"), encoding="utf-8")]
            try:
                adhoc()
                stopped = False
            except KeyError:
                stopped = True
            check("S6 a script reading the converted file directly, asking each row for its text, stops on the header",
                  stopped)
        finally:
            OE.EVAL_DIR = saved

        bad = os.path.join(tmp, "SPENT.json")
        with open(bad, "w", encoding="utf-8") as fh:
            fh.write("{ not json")
        r7a = refused(lambda: OE.spent_registry(bad))
        r7b = refused(lambda: OE.spent_registry(os.path.join(tmp, "absent.json")))
        check("S7 a missing or unreadable registry refuses; it never reads as 'nothing is spent'",
              bool(r7a) and bool(r7b), (r7a, r7b))

    missing = []
    tdir = os.path.join(HERE, "tools")
    for f in sorted(os.listdir(tdir)):
        if not f.endswith(".py"):
            continue
        tree = ast.parse(open(os.path.join(tdir, f), encoding="utf-8").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                fn = node.func
                name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
                if name == "read_jsonl" and not any(k.arg == "purpose" for k in node.keywords):
                    missing.append("%s:%d" % (f, node.lineno))
    check("S8 every read_jsonl call in tools/ states purpose= (static: a call built another way is not seen)",
          not missing, missing)

    print("\nA357: %d/%d passed" % (len(PASSED), len(PASSED) + len(FAILED)))
    return 0 if not FAILED else 1


if __name__ == "__main__":
    sys.exit(main())
