"""A492 -- three Windows-only paths that broke under Linux, found by running them there (2026-11-25).

1. ops/hidden_task.py passed creationflags unconditionally; POSIX Popen raises ValueError, which was not caught,
   so the child never ran and nothing was logged.
2. covenant_watchdog_guard.pid_alive_windows used tasklist; under Linux it answered False for a live python, so
   the guard would revive a watchdog that was running.
3. covenant_watchdog._evict_twins listed processes with PowerShell; under Linux it logged "unavailable" and a
   twin was never stopped.

Driven both ways. The /proc readers are tested against a FAKE /proc tree on every platform, so Windows proves
the parsing too; the live-process cases run only where /proc exists. hidden_task runs from a throwaway copy so
its loud-failure log never lands in this tree's logs/ (A350's lesson)."""
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timezone

import covenant_watchdog as W
import covenant_watchdog_guard as G

HERE = os.path.dirname(os.path.abspath(__file__))
POSIX_PROC = os.name != "nt" and os.path.isdir("/proc/self")


def _write(path, data, mode="w"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, mode) as fh:
        fh.write(data)


class HiddenTask(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="a492ht_")
        os.makedirs(os.path.join(self.tmp, "ops"))
        shutil.copy(os.path.join(HERE, "ops", "hidden_task.py"), os.path.join(self.tmp, "ops", "hidden_task.py"))
        self.marker = os.path.join(self.tmp, "child_ran.txt")
        _write(os.path.join(self.tmp, "child.py"),
               "import sys\nopen(%r, 'w').write(' '.join(sys.argv[1:]))\nsys.exit(7)\n" % self.marker)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_wrapper(self, *args):
        return subprocess.run([sys.executable, os.path.join(self.tmp, "ops", "hidden_task.py")] + list(args),
                              cwd=self.tmp, capture_output=True, text=True, timeout=60)

    def test_child_runs_and_its_exit_code_passes_through(self):
        # Under Linux this failed before A492: ValueError traceback, no child, no marker.
        r = self.run_wrapper("child.py", "a", "b")
        self.assertTrue(os.path.exists(self.marker), "child never ran: " + (r.stderr or "")[-300:])
        with open(self.marker) as fh:
            self.assertEqual(fh.read(), "a b")
        self.assertEqual(r.returncode, 7)
        self.assertNotIn("Traceback", r.stderr or "")

    def test_a_failure_is_logged_not_swallowed(self):
        # The other way: a target that cannot run must exit 3 and leave a line in logs/hidden_task.log.
        r = self.run_wrapper("no_such_program_a492")
        self.assertEqual(r.returncode, 3)
        with open(os.path.join(self.tmp, "logs", "hidden_task.log"), encoding="utf-8") as fh:
            self.assertIn("no_such_program_a492", fh.read())

    @unittest.skipIf(os.name == "nt", "a .bat runs on Windows; the refusal is the Linux behaviour")
    def test_a_bat_is_refused_loudly_off_windows(self):
        _write(os.path.join(self.tmp, "TASK.bat"), "@echo off\r\n")
        r = self.run_wrapper("TASK.bat")
        self.assertEqual(r.returncode, 3)
        with open(os.path.join(self.tmp, "logs", "hidden_task.log"), encoding="utf-8") as fh:
            self.assertIn("needs Windows", fh.read())


class GuardPidAlive(unittest.TestCase):
    def setUp(self):
        self.proc = tempfile.mkdtemp(prefix="a492proc_")
        _write(os.path.join(self.proc, "10", "cmdline"), b"/srv/covenant/.venv/bin/python3.13\0covenant_watchdog.py\0", "wb")
        _write(os.path.join(self.proc, "11", "cmdline"), b"/usr/bin/bash\0-c\0python covenant_watchdog.py\0", "wb")
        _write(os.path.join(self.proc, "12", "cmdline"), b"", "wb")   # a kernel thread / zombie

    def tearDown(self):
        shutil.rmtree(self.proc, ignore_errors=True)

    def test_fake_proc(self):
        self.assertTrue(G.pid_alive_posix(10, proc=self.proc), "a live python must read as alive")
        self.assertFalse(G.pid_alive_posix(11, proc=self.proc), "argv[0] is bash: not a python, whatever argv holds")
        self.assertFalse(G.pid_alive_posix(12, proc=self.proc), "empty cmdline is not a python")
        self.assertFalse(G.pid_alive_posix(99, proc=self.proc), "a missing pid is not alive")
        self.assertFalse(G.pid_alive_posix("x", proc=self.proc), "garbage in the pid file is not alive")

    def test_the_guard_asks_the_platform_function(self):
        expected = G.pid_alive_windows if os.name == "nt" else G.pid_alive_posix
        seen = []
        orig = expected.__name__
        setattr(G, orig, lambda pid: seen.append(pid) or True)
        try:
            self.assertTrue(G.pid_alive(4242))
        finally:
            setattr(G, orig, expected)
        self.assertEqual(seen, [4242])

    @unittest.skipUnless(POSIX_PROC, "needs a real /proc")
    def test_live_python_reads_alive_under_linux(self):
        # Before A492 the guard asked tasklist here and got False for this very process.
        self.assertTrue(G.pid_alive(os.getpid()))
        p = subprocess.Popen(["sleep", "30"])
        try:
            self.assertFalse(G.pid_alive(p.pid), "a live non-python must not read as the watchdog")
        finally:
            p.kill(); p.wait()


class TwinRowsPosix(unittest.TestCase):
    ME = "/srv/covenant/covenant_watchdog.py"

    def setUp(self):
        self.proc = tempfile.mkdtemp(prefix="a492tw_")
        self.btime = 1795000000
        _write(os.path.join(self.proc, "stat"), "cpu  1 2 3\nbtime %d\nprocesses 9\n" % self.btime)
        self.hz = os.sysconf("SC_CLK_TCK") if hasattr(os, "sysconf") else 100

        def proc(pid, argv, ticks, comm="python3"):
            _write(os.path.join(self.proc, str(pid), "cmdline"), b"\0".join(argv) + b"\0", "wb")
            rest = ["S"] + ["0"] * 18 + [str(ticks)] + ["0"] * 10       # field 3 .. field 22 = ticks
            _write(os.path.join(self.proc, str(pid), "stat"), "%d (%s) %s\n" % (pid, comm, " ".join(rest)))
        me = self.ME.encode()
        proc(100, [b"/srv/covenant/.venv/bin/python", me, b"--interval", b"60"], 500)
        proc(200, [b"/usr/bin/python3", me], 750, comm="py thon) odd")   # comm with a space and a ')'
        proc(300, [b"/usr/bin/bash", me], 400)                          # names the file, but not a python
        proc(400, [b"/usr/bin/python3", b"/other/tree/covenant_watchdog.py"], 300)   # another checkout
        _write(os.path.join(self.proc, "self", "cmdline"), b"x\0", "wb")  # non-numeric entries are skipped

    def tearDown(self):
        shutil.rmtree(self.proc, ignore_errors=True)

    def at(self, ticks):
        return datetime.fromtimestamp(self.btime + ticks / self.hz, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    def test_only_pythons_naming_this_tree(self):
        rows = sorted(W._twin_rows_posix(self.ME, proc=self.proc))
        self.assertEqual(rows, [(100, self.at(500)), (200, self.at(750))])

    def test_fixed_width_so_string_order_is_time_order(self):
        rows = dict(W._twin_rows_posix(self.ME, proc=self.proc))
        self.assertEqual(len(rows[100]), len(rows[200]))
        self.assertLess(rows[100], rows[200])
        # and the decision it feeds: the newer (200) stops the older (100), never the other way
        r = list(rows.items())
        self.assertEqual(W._twins_to_evict(r, my_pid=200, my_ppid=1), [100])
        self.assertEqual(W._twins_to_evict(r, my_pid=100, my_ppid=1), [])


@unittest.skipUnless(POSIX_PROC, "the Linux stop path needs a real /proc and signals")
class EvictTwinsLinux(unittest.TestCase):
    def setUp(self):
        self.child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        self.logged = []
        self._rows, self._log = W._twin_rows_posix, W.log
        W.log = lambda lvl, msg: self.logged.append((lvl, msg))

    def tearDown(self):
        W._twin_rows_posix, W.log = self._rows, self._log
        if self.child.poll() is None:
            self.child.kill()
        self.child.wait()

    def gone(self, timeout=5):
        end = time.time() + timeout
        while time.time() < end:
            if self.child.poll() is not None:
                return True
            time.sleep(0.05)
        return False

    def test_an_older_twin_is_stopped(self):
        # Before A492 this logged "twin check unavailable" (no PowerShell) and the twin lived.
        W._twin_rows_posix = lambda me, proc="/proc": [(self.child.pid, "2026-01-01T00:00:00.000000Z"),
                                                       (os.getpid(), "2026-01-01T00:00:05.000000Z")]
        W._evict_twins()
        self.assertTrue(self.gone(), "older twin still running; log: %r" % self.logged)
        self.assertTrue(any("stopped it" in m for _, m in self.logged))

    def test_a_newer_twin_is_left_alone(self):
        W._twin_rows_posix = lambda me, proc="/proc": [(self.child.pid, "2026-01-01T00:00:09.000000Z"),
                                                       (os.getpid(), "2026-01-01T00:00:05.000000Z")]
        W._evict_twins()
        self.assertFalse(self.gone(timeout=1), "a newer twin must survive: it is the one that wins")
        self.assertEqual(self.logged, [])


class SiteAutodeployPaths(unittest.TestCase):
    """4. tools/site_autodeploy.py named the site, node and python by Windows paths only (node.exe in a win-x64
    folder, .venv\\Scripts\\python.exe). Each platform now gets its own; Windows keeps the paths it had."""
    def load(self, **env):
        import importlib
        sys.path.insert(0, os.path.join(HERE, "tools"))
        old = {k: os.environ.get(k) for k in env}
        os.environ.update({k: v for k, v in env.items() if v is not None})
        for k, v in env.items():
            if v is None:
                os.environ.pop(k, None)
        try:
            import site_autodeploy
            return importlib.reload(site_autodeploy)
        finally:
            for k, v in old.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
            sys.path.remove(os.path.join(HERE, "tools"))

    @unittest.skipUnless(os.name == "nt", "the Windows paths")
    def test_windows_keeps_its_paths(self):
        SA = self.load(COVENANT_SITE_DIR="/ignored/on/windows", COVENANT_NODE_DIR=None)
        self.assertEqual(SA.SITE, r"C:\Users\Lawre\site\lawless1987-website-backup\website")
        self.assertTrue(SA._node().endswith(r"node-v24.22.1-win-x64\node.exe"))
        self.assertTrue(SA._site_env()["PATH"].startswith(SA.NODE_DIR + os.pathsep))

    @unittest.skipIf(os.name == "nt", "the Linux paths")
    def test_linux_defaults_and_overrides(self):
        SA = self.load(COVENANT_SITE_DIR=None, COVENANT_NODE_DIR=None)
        self.assertEqual(SA.SITE, os.path.expanduser("~/site/lawless1987-website-backup/website"))
        self.assertNotIn("\\", SA.SITE)
        self.assertEqual(SA._node(), shutil.which("node") or "node")
        self.assertFalse(SA._node().endswith(".exe"))
        SA = self.load(COVENANT_SITE_DIR="/srv/website", COVENANT_NODE_DIR="/opt/node-v24")
        self.assertEqual(SA.SITE, "/srv/website")
        self.assertEqual(SA._node(), "/opt/node-v24/bin/node")
        self.assertTrue(SA._site_env()["PATH"].startswith("/opt/node-v24/bin" + os.pathsep))
        self.assertTrue(os.path.exists(SA._venv_python()), "falls back to this interpreter when no venv")


if __name__ == "__main__":
    res = unittest.main(exit=False, verbosity=2).result
    run, bad = res.testsRun, len(res.failures) + len(res.errors)
    print("A492: %d/%d passed, %d skipped" % (run - bad - len(res.skipped), run - len(res.skipped), len(res.skipped)))
    sys.exit(1 if bad else 0)
