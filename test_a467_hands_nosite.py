"""A467 (2026-11-22 security search): the hands' runner passes -S, so no start-up hook runs before a signed script.

Isolated mode (-I) still imports `site`, and `site` executes every `.pth` line in site-packages that starts with
"import". A throwaway Python environment is made, a hook is planted in ITS site-packages that writes a marker file, and
the hands run a script with that environment's python: the marker must not appear. Also every name the screen allows
must still import under the runner's flags (all are standard library).
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_tetsu_hands as H  # noqa: E402

RESULTS = []


def check(label, ok, detail=""):
    RESULTS.append((label, bool(ok)))
    print(("ok    " if ok else "FAIL  ") + label + ("" if ok else "  -- %r" % (detail,)))


def main():
    td = tempfile.mkdtemp(prefix="a467-")
    saved = sys.executable
    try:
        ws = os.path.join(td, "ws")
        os.makedirs(ws)
        # 1. every allowed module imports through the real runner (its own interpreter, its own flags)
        H.write("all.py", "".join("import %s\n" % m for m in sorted(H.ALLOWED_MODULES)) + "print('all-imported')\n", ws)
        seen = []
        real = subprocess.run

        def spy(argv, *a, **k):
            seen.append(list(argv))
            return real(argv, *a, **k)
        H.subprocess.run = spy
        try:
            r = H.run("all.py", workshop=ws)
        finally:
            H.subprocess.run = real
        check("A467.1 every name the screen allows still imports under the runner's flags (%d modules)" % len(H.ALLOWED_MODULES),
              r.get("ok") and "all-imported" in r.get("out", ""), (r.get("why"), r.get("err", "")[-300:]))
        flags = seen[0][1:seen[0].index("-c")] if seen and "-c" in seen[0] else None
        check("A467.2 the child is started with -I and -S", flags == ["-I", "-S"], seen[:1])

        # 2. a planted start-up hook does not run before the script
        venv = os.path.join(td, "venv")
        mk = real([saved, "-m", "venv", "--without-pip", venv], capture_output=True, text=True, timeout=300)
        py = os.path.join(venv, "Scripts", "python.exe") if os.name == "nt" else os.path.join(venv, "bin", "python")
        if mk.returncode or not os.path.isfile(py):
            check("A467.3 a throwaway environment could be made for the hook test", False, mk.stderr[-300:])
        else:
            site_dir = real([py, "-I", "-c", "import site; print(site.getsitepackages()[-1])"],
                            capture_output=True, text=True, timeout=60).stdout.strip()
            marker = os.path.join(td, "HOOK-RAN")
            with open(os.path.join(site_dir, "a467_hook.pth"), "w", encoding="utf-8") as f:
                f.write("import os; open(%r, 'w').write('ran')\n" % marker)
            # control: the hook does run under -I alone, so this test can fail
            real([py, "-I", "-c", "pass"], capture_output=True, timeout=60)
            control = os.path.exists(marker)
            if control:
                os.remove(marker)
            check("A467.3 control: in that environment the planted hook runs under -I alone", control)
            H.write("hello.py", "print('hello')\n", ws)
            sys.executable = py
            try:
                r2 = H.run("hello.py", workshop=ws)
            finally:
                sys.executable = saved
            check("A467.4 under the hands' runner the hook does not run, and the script still does",
                  r2.get("ok") and "hello" in r2.get("out", "") and not os.path.exists(marker),
                  (r2.get("why"), r2.get("err", "")[-200:], os.path.exists(marker)))
    finally:
        sys.executable = saved
        shutil.rmtree(td, ignore_errors=True)
    failed = [n for n, ok in RESULTS if not ok]
    print("A467: %d/%d passed" % (len(RESULTS) - len(failed), len(RESULTS)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
