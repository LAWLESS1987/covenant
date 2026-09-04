"""verify_bundle.py -- one hash census over everything this bundle ships.

`project_write` is not delivery and a copy is not a verified copy (M25). This
walks the tree, skips the things that are STATE rather than SOURCE, and either
writes MANIFEST.sha256 or checks against it.

What is deliberately excluded, and why:
  *.db, *.db-shm, *.db-wal  the chain. Not source; changes every block.
  *.key                     the operator credential and genesis mint key.
                            A key must never travel in a manifest, an archive
                            or a chat message.
  logs/, __pycache__/       runtime output.
  *.pyc, .venv/             build and environment.

vendor/*.whl IS tracked: a vendored wheel is what gets installed, so it is
source of truth and belongs under the hash like anything else.
  MANIFEST.sha256           itself.

Usage:
  python verify_bundle.py            check  (exit 0 ok, 1 mismatch, 2 no manifest)
  python verify_bundle.py --write    (re)write the manifest
"""
import hashlib, os, sys

HERE = os.path.dirname(os.path.abspath(__file__)) or "."
MAN = os.path.join(HERE, "MANIFEST.sha256")
SKIP_DIR = {"logs", "__pycache__", ".venv", ".git", ".claude", "judge_queue",
            "_keybackup", "_unsealtest", "launch", "pending-v8.38",
            # Restore points are the same unlanded bytes under another name;
            # pending-v8.38 is skipped, so its snapshots must be too
            # (2026-08-29: the 08:15 manifest hashed PRE-LAND as source).
            "pending-v8.38.BACKUP-2026-08-29", "PRE-LAND-2026-08-29",
            "_to_delete", "_stage",
            # private/ is holdings by another name (gitignored, 2026-09-02);
            # a manifest of the DELIVERY must not even list it.
            "private"}
SKIP_EXT = {".pyc", ".db", ".key", ".msi"}

# A MANIFEST MUST CONTAIN ONLY INPUTS.
#
# This list is not tidiness, it is a deadlock fix, and it is the third of its
# kind in one evening (M48). LAUNCH_CHECK.json is written BY the launcher and
# was hashed BY the launcher's own first gate, so every run guaranteed that the
# next run reported "1 changed" and refused -- a check firing on the consequence
# of running it. The same landmine was armed under every one of these: they are
# all rewritten by a .bat or a tool in this folder, so any of them being in the
# manifest turns "I used the tools" into "the bundle is corrupt".
#
# Enumerated by grepping the actual `set OUT=` targets and `>` redirects out of
# the .bat files rather than from memory -- the list was longer than the guess.
OUTPUTS = {
    "MANIFEST.sha256",
    # The learning ledgers (2026-09-04). These are written BY the system every
    # night -- the verdicts it was taught, the ones it refused, the precepts it
    # read, the model those produced -- so hashing them as delivery made G1 go
    # BLOCKED after every pass and taught an operator to re-run --write without
    # reading it, which is the one habit this gate exists to prevent.
    "verdicts.jsonl", "distill_rejected.jsonl", "DISTILL.md", "NIGHTLY.md",
    "SELF_EVAL.md", "PRECEPTS.jsonl", "STUDY.md", "fallback_model.json",
    "fallback_model.candidate.json",
    # gate, deploy and restart reports
    "LAUNCH_CHECK.json", "DEPLOY_VERIFY.txt", "NODE_RESTART.txt",
    # diagnostics
    "PORT_DIAG.txt", "PORT_PICK.txt", "CLEANUP.txt", "FIT_CHECK.txt",
    "FREE_RAM.txt", "LEAN_MEASURE.txt", "TOPMEM.txt", "STRAY_FIX.txt",
    "RETEST_RESULTS.txt", "INTEGRATE_RESULTS.txt", "INTEGRATE_RESULTS2.txt",
    "PREFLIGHT_OUT.txT", "preflight_out.txt", "preflight_live.txt",
    "pc_report.txt", "go_out.txt", "diag_out.txt", "judge_bench_out.txt",
    "live_out.txt", "live_claude_out.txt",
    # sweeps and dashboards
    "SWEEP_RESULTS.txt", "dashboard.html",
    # ONE.bat / ONE_RETEST.bat transcripts (2026-08-27). Same landmine as
    # LAUNCH_CHECK.json above and armed the same way: ONE.bat writes ONE_RUN.txt
    # into this folder, so hashing it would mean every run of the launcher
    # guaranteed the NEXT run reported "changed" and refused. Adding a launcher
    # that writes a report here means adding its report to this list, always.
    "ONE_RUN.txt", "ONE_RETEST.txt", "ONE_RUN_cloud.txt", "ONE_RUN_pc.txt",
    "ONE_RETEST_gates.txt", "ONE_UP.txt", "PROBE_WIN_CONNECT.txt", "GIT_SETUP.txt", "ONE_RUN_ci.txt", "GITHUB_PUSH.txt", "GH_LOGIN.txt", "GH_CODE.txt",
    # ops
    "ACL_RESULT.txt",
    # the scheduled trader appends here on EVERY run (TRADER_TASK.bat:
    # `>> trader_log.txt`), so hashing it guaranteed the manifest went stale
    # the morning after it was written (2026-09-02: 12 changed, 11 of them
    # committed edits and this one a log). Same landmine as ONE_RUN.txt.
    "trader_log.txt",
    # balance sidecars and venue history: state, gitignored, holdings by
    # another name. Not delivery.
    # ops/ state the watchdog and guard rewrite every round (2026-09-02: the
    # self-eval ledger is appended hourly and tripped G1 an hour after --write)
    "SELF_EVAL.md", "SELF_EVAL.md.prev", "watchdog.pid", "guard_state.json",
    "judge_route.log",   # covenant_route.py appends one line per local-judge call
    "coinbase_balance.json", "kraken_balance.json", "coinbase_balance.txt",
    "kraken_balance.txt", "coinbase_history.csv", "kraken_history.csv",
    # state that is deliberately not source: the chain's own genesis is an
    # input and IS tracked; these two are created by the operator and by a
    # live testnet submission, and are the XRP gate's own state.
    "xrp_testnet_proof.json", "xrp_mainnet_policy.json",
}
SKIP_NAME = {n.lower() for n in OUTPUTS}


def shipped():
    for dp, dns, fns in os.walk(HERE):
        dns[:] = [d for d in dns if d not in SKIP_DIR]
        for fn in sorted(fns):
            if fn.lower() in SKIP_NAME:
                continue
            # holdings.txt and its timestamped backups are L's actual
            # positions (gitignored). A public manifest must not list them.
            if fn.lower().startswith("holdings.txt"):
                continue
            if os.path.splitext(fn)[1] in SKIP_EXT:
                continue
            if fn.endswith(".db-shm") or fn.endswith(".db-wal"):
                continue
            yield os.path.relpath(os.path.join(dp, fn), HERE).replace("\\", "/")


# Files whose bytes are the content, and must never be touched. Everything
# else in this repository is text that git stores with LF and checks out on
# Windows with CRLF.
BINARY_EXT = {".png", ".jpg", ".jpeg", ".gif", ".zip", ".msi", ".db", ".key",
              ".pyc", ".ico", ".pdf", ".exe", ".dll", ".woff", ".woff2"}


def sha(rel):
    """sha256 of a file's CONTENT, with line endings normalised for text.

    WHY, MEASURED 2026-09-04. A manifest written on this Windows machine could
    never verify on Linux, and CI had been reporting G1 BLOCKED for that reason
    alone: 70 of the 487 files listed -- every .bat, and much else -- differ
    between the working tree here and the bytes git stores, because git keeps
    LF and checks out CRLF. The hashes were describing a platform, not a
    delivery.

    The CI log states the principle in its own words while failing on it: "a
    Windows reader and a POSIX reader must not be told different things about
    the same repository." So text is hashed with CRLF folded to LF, which is
    what git stores and what every other machine will see, and binary files
    are still hashed byte for byte because for them the bytes ARE the content.

    This does not weaken the check. A changed character still changes the
    hash. What it stops detecting is the line ending a checkout happened to
    use, which was never a property of the delivery.
    """
    ext = os.path.splitext(rel)[1].lower()
    with open(os.path.join(HERE, rel), "rb") as fh:
        data = fh.read()
    if ext not in BINARY_EXT and b"\x00" not in data[:8192]:
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def tracked():
    """What git ships. A manifest written from the raw disk listed untracked
    residue (.fuse_hidden*, *.PRE-LAUNCHBUNDLE, C2_RESULT.txt) and a clean
    checkout in CI reported every one of them MISSING (2026-09-02, run
    33697588403). None if git is unavailable -- then the walk is all there is."""
    import subprocess
    try:
        out = subprocess.run(["git", "ls-files", "-z"], cwd=HERE, capture_output=True,
                             timeout=30).stdout.decode("utf-8", "replace")
    except Exception:                                        # noqa: BLE001
        return None
    names = {n for n in out.split("\0") if n}
    return names or None


def main():
    files = sorted(shipped())
    if "--write" in sys.argv:
        t = tracked()
        if t is not None:
            dropped = [f for f in files if f not in t]
            files = [f for f in files if f in t]
            print("--write: %d files git tracks; %d on disk but not shipped, skipped"
                  % (len(files), len(dropped)))
    if "--write" in sys.argv:
        with open(MAN, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("# covenant bundle manifest -- sha256 of every shipped file.\n")
            fh.write("# Keys, databases and logs are deliberately NOT in here.\n")
            for rel in files:
                fh.write("%s  %s\n" % (sha(rel), rel))
        print("wrote %s over %d files" % (MAN, len(files)))
        return 0
    if not os.path.exists(MAN):
        print("no MANIFEST.sha256 -- run with --write")
        return 2
    want = {}
    for line in open(MAN, encoding="utf-8"):
        line = line.rstrip("\n")
        if line and not line.startswith("#"):
            h, rel = line.split("  ", 1)
            want[rel] = h
    bad = [r for r in want if not os.path.exists(os.path.join(HERE, r))
           or sha(r) != want[r]]
    extra = [r for r in files if r not in want]
    for r in bad:
        print("CHANGED/MISSING  %s" % r)
    for r in extra:
        print("NOT IN MANIFEST  %s" % r)
    print("%d in manifest, %d changed or missing, %d untracked"
          % (len(want), len(bad), len(extra)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
