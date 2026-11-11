"""Drive IM9 both ways: copy the miner modules + IM9 to a temp dir, apply ONE mutation, run IM9 there (-B), expect
red. The unmutated copy must be green (control). Bytes are written as read (no newline translation)."""
import os, shutil, subprocess, sys, tempfile

REPO = r"C:\Users\Lawre\covenant"
FILES = ["covenant_improve.py", "covenant_improve_extract.py", "covenant_improve_mine.py",
         "test_im9_reply_only_extract.py"]
MUT = [
    ("control (no mutation)", None, None, None),
    ("quote gate always passes", "covenant_improve_extract.py",
     b"    q = _tokens(quote)\n    if len(q) < QUOTE_MIN_WORDS:\n        return False\n",
     b"    return True\n"),
    ("no retry", "covenant_improve_extract.py",
     b"    if p[\"kind\"] in (\"gap\", \"stance\") and not grounded_quote(p[\"quote\"], seen):\n        retried = True",
     b"    if False:\n        retried = True"),
    ("retry repeats the same prompt", "covenant_improve_extract.py",
     b"code2, j2 = ask(prompt[:i] + RETRY_NOTE + prompt[i:])", b"code2, j2 = ask(prompt)"),
    ("self-description put back in the extracting prompt", "covenant_improve_extract.py",
     b"PROMPT_V2 = \"\"\"Read this forum reply.", b"PROMPT_V2 = SELF_DESC + \"\"\"Read this forum reply."),
    ("re-queue ignored by harvest", "covenant_improve_mine.py",
     b"pend = set(pending_requeue()) if requeue_first else set()", b"pend = set()"),
    ("re-queue never marked done", "covenant_improve_mine.py",
     b"    _append_requeue([{\"id\": i, \"done\": True, \"t\": t} for i in ids if i in pend], path)",
     b"    pass"),
    ("miner_echo clears without a phrase", "covenant_improve.py",
     b"return (ef >= EX.ECHO_FRAC and bool((d.get(\"phrase\") or \"\").strip())",
     b"return (ef >= EX.ECHO_FRAC and True"),
    ("ungrounded not marked", "covenant_improve_extract.py",
     b"        p[\"kind\"] = \"ungrounded\"", b"        pass"),
    ("a word match kills again", "covenant_improve.py",
     b'        return {"status": "backlog", "dup_hint": hint,', b'        return {"status": "have", "dup_hint": hint,'),
    ("hint ignores which file", "covenant_improve.py",
     b'        by_file.setdefault(f, []).append(s)', b'        by_file.setdefault("ALL", []).append(s)'),
    ("digest not ranked", "covenant_improve.py",
     b'    return sorted(rows, key=lambda r: bool(r.get("dup_hint")))', b'    return list(rows)'),
]
res = []
for name, f, old, new in MUT:
    with tempfile.TemporaryDirectory() as d:
        for x in FILES:
            shutil.copyfile(os.path.join(REPO, x), os.path.join(d, x))
        if f:
            p = os.path.join(d, f)
            b = open(p, "rb").read()
            if b.count(old) != 1:
                res.append((name, "MUTATION NOT APPLIED (%d matches)" % b.count(old)))
                continue
            open(p, "wb").write(b.replace(old, new))
        r = subprocess.run([sys.executable, "-B", os.path.join(d, "test_im9_reply_only_extract.py")],
                           capture_output=True, text=True, cwd=d, timeout=300)
        last = (r.stdout.strip().splitlines() or [""])[0][:60]
        expect_red = f is not None
        good = (r.returncode != 0) == expect_red
        res.append((name, "%s rc=%d %s" % ("OK " if good else "BAD", r.returncode, last)))
for n, s in res:
    print("%-52s %s" % (n, s))
