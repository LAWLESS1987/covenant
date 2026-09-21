#!/usr/bin/env python3
"""IG1 -- the black frame guard on the image door: a near-black PNG is recognised, a bright
one is not, a stub-sized one is never judged, and generate() retries once with another seed
and refuses a second black frame. RUN with the diffusion runtime stubbed by a fake binary
that writes whatever frame the test asks for.

Pins covenant_image.is_black and the retry in generate (2026-09-21, his words: "fix the
black box issue again").
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
                 "v=int(plan.pop(0)); open(%r,'w').write(' '.join(plan))\n"
                 "row=b'\\x00'+bytes((v,v,v))*64\n"
                 "open(out,'wb').write(b'\\x89PNG\\r\\n\\x1a\\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',64,64,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(row*64))+chunk(b'IEND',b''))\n"
                 "open(out+'.seed','w').write(seed)\n" % (plan, plan))
    real = {k: getattr(IMG, k) for k in ("BIN", "WEIGHTS", "OUT_DIR", "_make_room")}
    real_run = IMG.subprocess.run
    try:
        IMG.BIN, IMG.WEIGHTS, IMG.OUT_DIR = fake_bin, fake_bin, tmp
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
    finally:
        for k, v in real.items():
            setattr(IMG, k, v)
        IMG.subprocess.run = real_run
        if env_stub is not None:
            os.environ["COVENANT_IMAGE_STUB"] = env_stub

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
