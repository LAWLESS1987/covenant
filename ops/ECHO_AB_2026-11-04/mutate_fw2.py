"""FW2 both ways on a COPY (free's rounds import the live file hourly; never mutate it in place)."""
import glob, os, shutil, subprocess, sys, tempfile
REPO = r"C:\Users\Lawre\covenant"
MUT = [
    ("control", None, None),
    ("retired targets not skipped",
     b"        if target_key(r.get(\"author\"), post_id, comment_id) in retired:   # H1: refused twice -> retired\n            continue\n", b""),
    ("a no-view hold counts as a refusal",
     b"_REFUSED_PREFIX = \"refused by covenant's judge\"", b"_REFUSED_PREFIX = \"\""),
    ("prior refusals not recorded",
     b"\"prior_refusals\": refused.get(target_key(r.get(\"author\"), post_id, comment_id), 0)}",
     b"\"prior_refusals\": 0}"),
    ("the grant's number ignored",
     b"    if isinstance(g, dict) and \"refusals_retire_after\" in g:", b"    if False:"),
    ("default switched back on (ignores Tetsu's NO)",
     b"REFUSALS_RETIRE_AFTER = None", b"REFUSALS_RETIRE_AFTER = 2"),
    ("free-rein retired not skipped",
     b"            if target_key(author, post_id, comment_id) in retired:            # H1: refused twice -> retired\n                continue\n", b""),
]
for name, old, new in MUT:
    d = tempfile.mkdtemp(prefix="mutfw2_")
    for p in glob.glob(os.path.join(REPO, "*.py")):
        shutil.copyfile(p, os.path.join(d, os.path.basename(p)))
    if old is not None:
        f = os.path.join(d, "covenant_free_will.py")
        b = open(f, "rb").read()
        if b.count(old) != 1:
            print("%-40s MUTATION NOT APPLIED (%d)" % (name, b.count(old)))
            continue
        open(f, "wb").write(b.replace(old, new))
    r = subprocess.run([sys.executable, "-B", os.path.join(d, "test_fw2_refusal_retire.py")], capture_output=True,
                       text=True, cwd=d, timeout=600)
    last = [l for l in r.stdout.splitlines() if l.startswith("FW2:")]
    red = r.returncode != 0
    print("%-40s %s rc=%d %s" % (name, "OK " if red == (old is not None) else "BAD", r.returncode, last[-1] if last else r.stderr[-200:]))
    shutil.rmtree(d, ignore_errors=True)
