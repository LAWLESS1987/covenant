#!/usr/bin/env python3
"""Drive verify_citations.py both ways. A hook that only ever passes has never
been observed; each case below must produce the stated verdict."""
import json
import os
import subprocess
import sys
import tempfile

REPO = r"C:\Users\Lawre\covenant"
HOOK = os.path.join(REPO, ".claude", "hooks", "verify_citations.py")
PY = os.path.join(REPO, ".venv", "Scripts", "python.exe")

CASES = [
    # (name, assistant text, expect_block)
    ("real file, real line",
     "The ledger records it at docs/KNOWN_ISSUES.md:4724 plainly.", False),
    ("real file, line past end",
     "See docs/KNOWN_ISSUES.md:9999999 for the detail.", True),
    ("path that does not exist",
     "As GHOST_FILE_2026.md:1 reads, the claim was checked.", True),
    ("allowlisted example",
     "I wrongly cited PEDERSEN_2026-09-14.md:1 as my source.", False),
    ("bare path, no line number",
     "I will create a new helper at tools/newthing.py shortly.", False),
    ("no citation at all",
     "Both letters were sent and verified clean.", False),
    ("real file cited twice, one bad",
     "See docs/KNOWN_ISSUES.md:4724 and conformance.py:8888888 too.", True),
    # --- the quote check (end pass, part 2) ---------------------------------
    ("quote that IS in the cited file",
     "As CLAUDE.md:1 puts it, \"Internal consistency is not accuracy.\"", False),
    ("quote the cited file does NOT contain",
     "As CLAUDE.md:1 puts it, \"the catalogues were checked before the prose "
     "was written, every time.\"", True),
    ("quote re-wrapped across lines still matches",
     "CLAUDE.md:1 says \"Internal consistency\nis not accuracy.\"", False),
    ("short quote is ignored -- no crying wolf",
     "CLAUDE.md:1 mentions \"the data\" here.", False),
    ("quote with no citation in the paragraph is not checked",
     "Somebody once said \"this string appears in no file anywhere at all\".", False),
]


def run(text):
    tdir = tempfile.mkdtemp()
    tpath = os.path.join(tdir, "transcript.jsonl")
    with open(tpath, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"type": "user",
                             "message": {"role": "user", "content": "go"}}) + "\n")
        fh.write(json.dumps({"type": "assistant",
                             "message": {"role": "assistant",
                                         "content": [{"type": "text", "text": text}]}}) + "\n")
    payload = {"transcript_path": tpath, "cwd": REPO, "stop_hook_active": False}
    proc = subprocess.run([PY, HOOK], input=json.dumps(payload),
                          capture_output=True, text=True, timeout=60)
    out = (proc.stdout or "").strip()
    blocked = False
    if out:
        try:
            blocked = json.loads(out).get("decision") == "block"
        except ValueError:
            pass
    return blocked, out, (proc.stderr or "").strip()


def main():
    failures = 0
    for name, text, expect_block in CASES:
        blocked, out, err = run(text)
        ok = blocked == expect_block
        if not ok:
            failures += 1
        print("%-32s expect=%-5s got=%-5s %s"
              % (name, "BLOCK" if expect_block else "pass",
                 "BLOCK" if blocked else "pass", "OK" if ok else "*** FAIL ***"))
        if err:
            print("      stderr: %s" % err)
        if not ok and out:
            print("      stdout: %s" % out[:400])

    # The loop guard: a stop we already caused must never block again.
    tdir = tempfile.mkdtemp()
    tpath = os.path.join(tdir, "t.jsonl")
    with open(tpath, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"type": "assistant",
                             "message": {"role": "assistant",
                                         "content": [{"type": "text",
                                                      "text": "GHOST_FILE_2026.md:1 says so."}]}}) + "\n")
    proc = subprocess.run([PY, HOOK],
                          input=json.dumps({"transcript_path": tpath, "cwd": REPO,
                                            "stop_hook_active": True}),
                          capture_output=True, text=True, timeout=60)
    looped = "block" in (proc.stdout or "")
    print("%-32s expect=%-5s got=%-5s %s"
          % ("stop_hook_active re-entry", "pass", "BLOCK" if looped else "pass",
             "*** FAIL ***" if looped else "OK"))
    if looped:
        failures += 1

    # Fail-open: garbage on stdin must not wedge the turn.
    proc = subprocess.run([PY, HOOK], input="not json at all",
                          capture_output=True, text=True, timeout=60)
    open_ok = proc.returncode == 0 and "block" not in (proc.stdout or "")
    print("%-32s expect=%-5s got=%-5s %s"
          % ("garbage stdin fails open", "pass", "pass" if open_ok else "BLOCK",
             "OK" if open_ok else "*** FAIL ***"))
    if not open_ok:
        failures += 1

    print()
    print("FAILURES: %d" % failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
