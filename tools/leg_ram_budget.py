#!/usr/bin/env python3
"""Re-runnable peak-RAM budget probe for the octopus leg (the 9-voice consult's precondition for keeping the
2B WARM: prove warm-2B + 3B + nodes fit UNDER LOAD, else warm is worse than reload/thrash on a 15.3GB box).

Drives the 3B keeper (:8081) and the 2B leg (:8099) CONCURRENTLY and samples free physical RAM through the
peak, using the SAME free_ram_gb() that covenant_leg's live backpressure guard uses -- so this both measures
the budget and validates the reader. Reports MIN free during load (the budget number) and peak resident of the
pair. Measured 2026-10-25, two runs: trough 1.84/1.846 GB, pair 4.12 GB. Needs both servers up; stdlib only.
"""
import json, sys, threading, time, urllib.request
sys.path.insert(0, r"C:\Users\Lawre\covenant")
import covenant_leg as L

PROMPTS = {
    8081: "Describe three append-only audit-log data structures and their tradeoffs under heavy write load.",
    8099: "Explain how a verdict cache keyed on prompt hash can be poisoned, and three detections for it.",
}


def hit(port, max_tokens=320):
    body = json.dumps({"messages": [{"role": "user", "content": PROMPTS[port]}],
                       "max_tokens": max_tokens, "temperature": 0.3,
                       "chat_template_kwargs": {"enable_thinking": False}}).encode("utf-8")
    req = urllib.request.Request("http://127.0.0.1:%d/v1/chat/completions" % port,
                                 data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=240) as r:
            json.loads(r.read().decode("utf-8", "replace"))
        return "%d ok" % port
    except Exception as e:                                 # noqa: BLE001
        return "%d err: %s" % (port, type(e).__name__)


def run():
    results = {}
    threads = [threading.Thread(target=lambda p=p: results.__setitem__(p, hit(p))) for p in (8081, 8099)]
    for t in threads:
        t.start()
    min_free, n = 999.0, 0
    while any(t.is_alive() for t in threads):
        fr = L.free_ram_gb()
        if fr is not None and fr < min_free:
            min_free = fr
        n += 1
        time.sleep(0.25)
    for t in threads:
        t.join()
    print("jobs                 :", results, "(%d samples)" % n)
    print("free_ram_gb() reads  : %.2f GB now" % (L.free_ram_gb() or -1))
    print("MIN free during load : %.2f GB   <- the peak-RAM budget" % min_free)
    print("RAM_FLOOR_GB (guard) : %.2f GB   (leg holds below this)" % L.RAM_FLOOR_GB)
    verdict = "FITS (warm justified)" if min_free > L.RAM_FLOOR_GB else "TIGHT -- warm risks thrash"
    print("verdict              :", verdict)


if __name__ == "__main__":
    run()
