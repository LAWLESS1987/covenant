#!/usr/bin/env python3
"""covenant_image.py -- open-source image creation on this PC, behind the same door.

WHY (2026-09-19, his words): "there has to be a image creation open source we
can take and improve on". This is that base: stable-diffusion.cpp (tools/sd/,
untracked) with sd-turbo (models/sd_turbo.safetensors, untracked; Stability's
non-commercial research licence -- his to read before any use beyond his own
phone and PC). CPU only, quantised to 8 bits at load, 512x512, four steps.

WHAT IT COSTS. Roughly 2.5 GB resident while it runs and tens of seconds per
image on this CPU (measured on first use and written to logs/image.log). On a
PC with 15 GB and the browser open there is not room for this and the language
model at once, so generate() puts the language model away first if memory is
short. Nothing stays resident between images: sd runs as a process per image
and exits.

WHAT IT IS NOT. Not a judge of anything. The PROMPT is judged by the sentinel
at the door (/m/image) before this is called -- a refused prompt never reaches
the model. The image itself is bytes the node returns; it is not judged, and
the record says so.

CLI:  python covenant_image.py --status | --make "prompt" [--out FILE]
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(HERE, "tools", "sd", "sd-cli.exe")   # the release ships sd-cli.exe and sd-server.exe
WEIGHTS = os.path.join(HERE, "models", "sd_turbo.safetensors")
OUT_DIR = os.path.join(HERE, "ops", "images")                    # gitignored
LOG = os.path.join(HERE, "logs", "image.log")
NEED_GB = 2.5
STEPS, SIZE, CFG = 4, 512, 1.0                                    # sd-turbo: few steps, guidance 1


def _log(line):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write("%s %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%S"), line))


def status():
    try:
        import covenant_model as M
        free = M.free_gb()
    except Exception:                                             # noqa: BLE001
        free = None
    return {"runtime": os.path.isfile(BIN), "weights": os.path.isfile(WEIGHTS),
            "weights_gb": round(os.path.getsize(WEIGHTS) / 2 ** 30, 2) if os.path.isfile(WEIGHTS) else None,
            "free_gb": free, "need_gb": NEED_GB, "out_dir": OUT_DIR}


def _make_room():
    """Put the language model away if it is up and memory is short. Returns what it did."""
    try:
        import covenant_model as M
        free = M.free_gb()
        if free is not None and free < NEED_GB and M.alive():
            M.stop(say=lambda *_a: None)
            time.sleep(2)
            return "stopped the language model (free was %.2f GB)" % free
        return "free %s GB" % free
    except Exception as e:                                        # noqa: BLE001
        return "could not read memory: %s" % e


def generate(prompt, out=None, seed=-1, timeout=600):
    """One 512x512 PNG from a prompt. Returns (path, meta) or raises RuntimeError."""
    prompt = str(prompt or "").strip()[:500]
    if not prompt:
        raise RuntimeError("empty prompt")
    if os.environ.get("COVENANT_IMAGE_STUB"):
        os.makedirs(OUT_DIR, exist_ok=True)
        p = out or os.path.join(OUT_DIR, "stub.png")
        # a 1x1 PNG, so the door can be driven without the model
        with open(p, "wb") as fh:
            fh.write(bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6360000002000155f6b0a70000000049454e44ae426082"))
        return p, {"model": "stub", "ms": 0, "room": "stub"}
    if not os.path.isfile(BIN):
        raise RuntimeError("no runtime: %s (tools/sd/ is not tracked; unzip the stable-diffusion.cpp win-cpu build there)" % BIN)
    if not os.path.isfile(WEIGHTS):
        raise RuntimeError("no weights: %s" % WEIGHTS)
    room = _make_room()
    os.makedirs(OUT_DIR, exist_ok=True)
    p = out or os.path.join(OUT_DIR, "img-%s.png" % time.strftime("%Y%m%d-%H%M%S"))
    threads = max(2, (os.cpu_count() or 4) - 2)
    args = [BIN, "-m", WEIGHTS, "-p", prompt, "-o", p, "--steps", str(STEPS), "-W", str(SIZE), "-H", str(SIZE),
            "--cfg-scale", str(CFG), "--type", "q8_0", "-t", str(threads), "-s", str(seed), "-v"]
    t0 = time.time()
    creation = 0x08000000 if os.name == "nt" else 0
    r = subprocess.run(args, capture_output=True, text=True, timeout=timeout, creationflags=creation, cwd=os.path.dirname(BIN))
    ms = int((time.time() - t0) * 1000)
    tail = (r.stdout or "")[-600:] + (r.stderr or "")[-600:]
    if r.returncode != 0 or not os.path.isfile(p):
        _log("FAIL rc=%s %d ms prompt=%r %s" % (r.returncode, ms, prompt[:80], tail.replace("\n", " | ")[-300:]))
        raise RuntimeError("sd exited %s after %d ms: %s" % (r.returncode, ms, tail.replace("\n", " | ")[-300:]))
    # THE BLACK FRAME (2026-09-21, his words: "fix the black box issue again"): a diffusion run
    # can hand back a frame that is all but black -- a numeric failure, or a filter -- and until
    # now it was returned as if drawn. Measured here: the mean brightness of what came back; a
    # frame under BLACK_MEAN is retried ONCE with another seed, and a second black frame is an
    # error with the reason, never a black image handed to the phone.
    if is_black(p):
        _log("BLACK FRAME %d ms seed=%s prompt=%r -- retrying once with another seed" % (ms, seed, prompt[:80]))
        seed2 = (int(seed) + 7919) if int(seed) >= 0 else 7919
        args[args.index("-s") + 1] = str(seed2)
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout, creationflags=creation, cwd=os.path.dirname(BIN))
        ms = int((time.time() - t0) * 1000)
        if r.returncode != 0 or not os.path.isfile(p) or is_black(p):
            _log("BLACK FRAME twice %d ms prompt=%r" % (ms, prompt[:80]))
            raise RuntimeError("the model drew a black frame twice (seeds %s and %s) after %d ms; try other words" % (seed, seed2, ms))
        room = room + "; second seed after a black frame"
    _log("ok %d ms %s prompt=%r (%s)" % (ms, os.path.basename(p), prompt[:80], room))
    return p, {"model": "sd-turbo q8_0 %dx%d %d steps" % (SIZE, SIZE, STEPS), "ms": ms, "room": room}


BLACK_MEAN = 10.0        # mean brightness (0-255) under which a frame counts as black


def is_black(path, threshold=BLACK_MEAN):
    """True when the PNG's mean brightness is under the threshold. Unreadable -> False (never a guess of black)."""
    try:
        from PIL import Image, ImageStat
        with Image.open(path) as im:
            g = im.convert("L")
            if g.size[0] * g.size[1] < 64:
                return False                                     # a stub or a thumbnail is not a frame to judge
            return ImageStat.Stat(g).mean[0] < threshold
    except Exception:                                            # noqa: BLE001
        return False


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="open-source image creation on this PC")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--make", metavar="PROMPT")
    ap.add_argument("--out", metavar="FILE")
    a = ap.parse_args(argv)
    if a.make:
        p, meta = generate(a.make, out=a.out)
        print(p); print("--", meta); return 0
    print(json.dumps(status(), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
