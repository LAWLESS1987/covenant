#!/usr/bin/env python3
"""IG1 -- the black frame guard on the image door: a near-black PNG is recognised, a bright
one is not, a stub-sized one is never judged, and generate() retries once with another seed
and refuses a second black frame. RUN with the diffusion runtime stubbed by a fake binary
that writes whatever frame the test asks for.

Pins covenant_image.is_black and the retry in generate (2026-09-21, his words: "fix the
black box issue again").

A348l (2026-10-14): the suite writes its own log, never the live logs/image.log (the nightly runs
it in place, and its fake frames were most of that log); a crash on the second seed is a crash,
not a black frame (IG1e); _make_room says what covenant_model.stop() answered (IG1f).
"""
import os
import sys
import tempfile

os.environ.setdefault("COVENANT_QUIET", "1")
HERE = os.path.dirname(os.path.abspath(__file__)) or "."
sys.path.insert(0, HERE)

import covenant_image as IMG   # noqa: E402

FAILURES = []
PASSED = [0]


def check(label, ok, detail=""):
    print("  %-76s %s%s" % (label, "OK" if ok else "*** FAIL ***", ("  " + str(detail)[:300]) if detail and not ok else ""))
    if ok:
        PASSED[0] += 1
    else:
        FAILURES.append(label)


def png(path, value, size=64):
    """An 8-bit RGB PNG of one grey level, written with zlib alone -- the
    Linux CI has no Pillow (A204c), and the guard must be checked there too."""
    import struct
    import zlib
    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xffffffff)
    row = b"\x00" + bytes((value, value, value)) * size
    raw = zlib.compress(row * size)
    with open(path, "wb") as fh:
        fh.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
                 + chunk(b"IDAT", raw) + chunk(b"IEND", b""))


def main():
    tmp = tempfile.mkdtemp(prefix="ig1_")
    black, bright, tiny = [os.path.join(tmp, n) for n in ("black.png", "bright.png", "tiny.png")]
    png(black, 3); png(bright, 140); png(tiny, 0, size=4)
    print("IG1a -- is_black")
    check("IG1a a near-black 64x64 frame is black", IMG.is_black(black) is True)
    check("IG1a a bright frame is not", IMG.is_black(bright) is False)
    check("IG1a a stub-sized frame is never judged black", IMG.is_black(tiny) is False)
    check("IG1a an unreadable path is not black (never a guess)", IMG.is_black(os.path.join(tmp, "nope.png")) is False)
    print("IG1c -- the guard without Pillow (A204c)")
    m_black, why = IMG.mean_luma_pure(black)
    m_bright, _ = IMG.mean_luma_pure(bright)
    check("IG1c the pure reader measures the black frame near 3", m_black is not None and abs(m_black - 3) < 1.0, why)
    check("IG1c the pure reader measures the bright frame near 140", m_bright is not None and abs(m_bright - 140) < 1.0)
    check("IG1c the pure reader names what it cannot read", IMG.mean_luma_pure(os.path.join(tmp, "nope.png"))[0] is None)
    import subprocess
    probe = ("import sys; sys.modules['PIL'] = None; sys.path.insert(0, %r); import covenant_image as I; "
             "print(I.is_black(%r), I.is_black(%r), I.is_black(%r))" % (HERE, black, bright, tiny))
    r = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True, timeout=120,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0)
    check("IG1c with Pillow blocked, is_black still judges black / bright / stub the same way",
          (r.stdout or "").strip() == "True False False", (r.stdout or "") + (r.stderr or "")[-200:])

    print("IG1b -- generate retries once, then refuses")
    # a fake diffusion binary: a Python script that writes the frame named by a side file, per call
    fake_bin = os.path.join(tmp, "sd.py")
    plan = os.path.join(tmp, "plan.txt")
    with open(fake_bin, "w", encoding="utf-8") as fh:
        # the stub writes its PNG with zlib alone, like png() above: the runner's
        # interpreter and the Linux CI have no Pillow (A204c)
        fh.write("import sys, struct, zlib\n"
                 "def chunk(k, b): return struct.pack('>I', len(b)) + k + b + struct.pack('>I', zlib.crc32(k + b) & 0xffffffff)\n"
                 "args=sys.argv; out=args[args.index('-o')+1]; seed=args[args.index('-s')+1]\n"
                 "plan=open(%r).read().split()\n"
                 "t=plan.pop(0); open(%r,'w').write(' '.join(plan))\n"
                 "if t=='crash': sys.stderr.write('read tensor data failed (IG1e)\\n'); sys.exit(3)\n"   # A348l: a crash, not a frame
                 "v=int(t)\n"
                 "row=b'\\x00'+bytes((v,v,v))*64\n"
                 "open(out,'wb').write(b'\\x89PNG\\r\\n\\x1a\\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',64,64,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(row*64))+chunk(b'IEND',b''))\n"
                 "open(out+'.seed','w').write(seed)\n" % (plan, plan))
    real = {k: getattr(IMG, k) for k in ("BIN", "WEIGHTS", "OUT_DIR", "_make_room", "LOG", "_REAL_LOG")}
    real_run = IMG.subprocess.run
    # A348l: this suite's rows go to its own log. Run in place by the nightly, it had written them into the
    # live logs/image.log, unmarked "BLACK FRAME twice" rows among them, read as if the image door had refused.
    own_log = os.path.join(tmp, "image.log")
    live = real["LOG"]
    live_size = os.path.getsize(live) if os.path.isfile(live) else 0
    try:
        IMG.BIN, IMG.WEIGHTS, IMG.OUT_DIR = fake_bin, fake_bin, tmp
        IMG.LOG = own_log
        IMG._make_room = lambda: "test"
        env_stub = os.environ.pop("COVENANT_IMAGE_STUB", None)

        def run(args, **kw):
            return real_run([sys.executable] + list(args), **{k: v for k, v in kw.items() if k != "creationflags"})
        IMG.subprocess.run = run
        with open(plan, "w") as fh:
            fh.write("2 150")                                     # first frame black, second bright
        out = os.path.join(tmp, "a.png")
        p, meta = IMG.generate("a tree at night", out=out, seed=5)
        check("IG1b a black first frame is retried once with another seed and the bright second frame is returned, said in the meta",
              p == out and not IMG.is_black(out) and open(out + ".seed").read() != "5" and "second seed" in meta["room"], (meta, open(out + ".seed").read()))
        with open(plan, "w") as fh:
            fh.write("1 2 3")                                     # black, black
        try:
            IMG.generate("a tree at night", out=os.path.join(tmp, "b.png"), seed=5)
            twice = None
        except RuntimeError as e:
            twice = str(e)
        check("IG1b two black frames are an error naming both seeds, never a black image returned", twice and "black frame twice" in twice and "5 and 7924" in twice, twice)
        with open(plan, "w") as fh:
            fh.write("120")
        p2, meta2 = IMG.generate("a tree at night", out=os.path.join(tmp, "c.png"), seed=5)
        check("IG1b a bright first frame is returned as before, one run", not IMG.is_black(p2) and "second seed" not in meta2["room"] and open(p2 + ".seed").read() == "5", meta2)

        print("IG1e -- a crash on the second seed is a crash, not a black frame (A348l)")
        with open(plan, "w") as fh:
            fh.write("2 crash")                                   # black, then sd exits 3 with its words on stderr
        try:
            IMG.generate("a tree at night", out=os.path.join(tmp, "d.png"), seed=5)
            crash = None
        except RuntimeError as e:
            crash = str(e)
        check("IG1e a crash on the retry names its exit code and its words, never 'black frame twice ... try other words'",
              bool(crash) and "exited 3" in crash and "read tensor data failed" in crash and "black frame twice" not in crash, crash)
        rows = open(own_log, encoding="utf-8").read().splitlines() if os.path.isfile(own_log) else []
        check("IG1e its log row carries the rc and the words, not 'BLACK FRAME twice'",
              bool(rows) and "FAIL rc=3" in rows[-1] and "read tensor data failed" in rows[-1] and "BLACK FRAME twice" not in rows[-1], rows[-1:])
        check("IG1e two black frames still log 'BLACK FRAME twice' (that refusal is unchanged)",
              any("BLACK FRAME twice" in x for x in rows), rows)

        print("IG1d -- the suite writes its own log, never the live one (A348l)")
        check("IG1d this run's generate rows are in the suite's own log", sum("a tree at night" in x for x in rows) >= 5, rows)
        added = ""
        if os.path.isfile(live):
            with open(live, "rb") as fh:
                fh.seek(live_size)
                added = fh.read().decode("utf-8", "replace")
        check("IG1d nothing of this run reached the live logs/image.log", "a tree at night" not in added, added[-300:])
        # The guard at _log, both ways, with the module's idea of "real" pointed at a temp file first, so a
        # broken guard writes nowhere live (A275's way).
        fake_real = os.path.join(tmp, "live", "image.log")
        IMG._REAL_LOG = IMG.LOG = fake_real
        saved_argv = list(sys.argv)
        try:
            sys.argv[0:1] = ["test_ig1_image_guard.py"]
            IMG._log("IG1d from a test program")
            from_test = os.path.isfile(fake_real)
            sys.argv[0:1] = ["covenant_unified_v8.py"]
            IMG._log("IG1d from the door")
            from_door = open(fake_real, encoding="utf-8").read() if os.path.isfile(fake_real) else ""
        finally:
            sys.argv[:] = saved_argv
            IMG.LOG = own_log
        check("IG1d a test_*.py writing to the module's real log writes nothing (A272's guard, at _log)", not from_test)
        check("IG1d any other program still writes the real log", "IG1d from the door" in from_door and "from a test program" not in from_door, from_door)
    finally:
        for k, v in real.items():
            setattr(IMG, k, v)
        IMG.subprocess.run = real_run
        if env_stub is not None:
            os.environ["COVENANT_IMAGE_STUB"] = env_stub

    print("IG1f -- _make_room says what covenant_model.stop() answered (A348l)")
    # a stub keeper in place of covenant_model: memory short, a model up, and stop() answering each of its shapes
    import types
    asked, said = [], {}
    saved_mod = sys.modules.get("covenant_model")
    real_sleep = IMG.time.sleep
    try:
        IMG.time.sleep = lambda _s: None
        for name, free, answer in (("refused", 1.0, (False, "could not stop pid 5524: it still answers (taskkill exit 1: Access is denied)")),
                                   ("foreign", 1.0, (False, "not started by this keeper")),
                                   ("stopped", 1.0, (True, "stopped")),
                                   ("roomy", 9.0, (True, "stopped"))):
            stub = types.ModuleType("covenant_model")
            stub.free_gb = (lambda f: (lambda: f))(free)
            stub.alive = lambda: True
            stub.stop = (lambda a, n: (lambda say=print: (asked.append(n), a)[1]))(answer, name)
            sys.modules["covenant_model"] = stub
            said[name] = IMG._make_room()
    finally:
        IMG.time.sleep = real_sleep
        if saved_mod is None:
            sys.modules.pop("covenant_model", None)
        else:
            sys.modules["covenant_model"] = saved_mod
    check("IG1f a stop the server outlived is said as NOT stopped, with stop()'s reason",
          said["refused"].startswith("could NOT stop the language model") and "still answers" in said["refused"], said["refused"])
    check("IG1f a server this keeper did not start is said as NOT stopped, with stop()'s reason",
          said["foreign"].startswith("could NOT stop the language model") and "not started by this keeper" in said["foreign"], said["foreign"])
    check("IG1f a stop that worked still reads 'stopped the language model'",
          said["stopped"] == "stopped the language model (free was 1.00 GB)", said["stopped"])
    check("IG1f when it asks to stop is unchanged: once each under 2.5 GB, never with room",
          asked == ["refused", "foreign", "stopped"] and said["roomy"] == "free 9.0 GB", (asked, said["roomy"]))

    print()
    print("%d passed, %d failed" % (PASSED[0], len(FAILURES)))
    if FAILURES:
        print("IG1 result: FAILED (%d)" % len(FAILURES))
        for f in FAILURES:
            print("  - %s" % f)
        return 1
    print("IG1 result: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
