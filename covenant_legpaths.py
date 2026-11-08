#!/usr/bin/env python3
"""covenant_legpaths.py -- read each remote leg over several roads: one thread per leg, fall-through across roads.

WHY (the operator, 2026-11-07, relayed from the TETSU session that gave node D three roads to each of A/B/C):
"Ensure no bottleneck between legs if connection gets severed to any other legs." A reader that walks the legs
one after another, each on a SINGLE road with a long timeout, stalls the whole pass on the first severed leg --
the exact failure TETSU's pulse/watchdog had before node D's roads were threaded (a severed laptop cost +33 s per
repair cycle, down to 3 s after). This is the laptop's mirror of TETSU's mesh/legpaths.py, in two halves:

  * ACROSS LEGS -- one thread per leg (read_all), so a dead leg costs ONE bounded timeout, not N in series; and
  * ACROSS ROADS -- within a leg, the roads are tried in order (read_leg), so a dead road (hosted tailnet down)
    is retried on the next (our headscale via laptop_hs_relay, then TETSU's own plane) BEFORE the leg is called
    down. Fall-through is about the ROAD (transport), never the node's answer: any HTTP reply -- 200, or a 429
    that means "you are asking too often" -- is the leg ANSWERING (A115), so it is returned, not retried away.

OPSEC -- this repository is PUBLIC. No address lives in this source. The legs and their ordered roads are read at
run time from the gitignored ops/leg_roads.json (ops/leg_roads.example.json ships placeholders in its place).
An absent or unreadable file means NO legs -- never a guessed road, the same rule as ops/local_peers.txt
(covenant_watchdog N5). Road hosts are masked in every returned field and log line, so a tailnet address cannot
reach a tracked file through a caller's log.

Stdlib only. Guarded: a failure here returns a leg "down" (ok False); it never raises into a caller.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
LEG_ROADS = os.path.join(HERE, "ops", "leg_roads.json")
DEFAULT_PATH = "/health"
DEFAULT_TIMEOUT = 4.0


def _mask_host(road):
    """A 'host:port' road as it is safe to print: loopback and the unspecified address stay readable (they are not
    secret and they are what a reader needs to debug a relay), every other host is masked like opsec_scan.mask."""
    road = str(road)
    host, _, port = road.rpartition(":")
    if not host:                      # no port in the string; treat the whole thing as the host
        host, port = road, ""
    if host in ("127.0.0.1", "localhost", "::1", "0.0.0.0"):
        return road
    masked = host[:4] + "..." + host[-2:] if len(host) > 8 else host[:1] + "..."
    return masked + (":" + port if port else "")


def _load(path=LEG_ROADS):
    """{leg: {"roads": [host:port, ...], "path": "/health"}} from the gitignored file, or {} when it is absent,
    unreadable or malformed. A leg with no non-empty road list is dropped: a leg with no road is not a leg, and a
    guessed address is exactly what this file exists to avoid."""
    try:
        with open(path, encoding="utf-8") as fh:
            raw = json.load(fh)
    except (OSError, ValueError):
        return {}
    # Accept either {"legs": {...}} or the bare mapping, so the example file can carry a top-level comment key.
    if isinstance(raw, dict) and isinstance(raw.get("legs"), dict):
        raw = raw["legs"]
    if not isinstance(raw, dict):
        return {}
    out = {}
    for leg, spec in raw.items():
        if not isinstance(spec, dict):
            continue
        roads = [str(r).strip() for r in spec.get("roads", []) if isinstance(r, str) and str(r).strip()]
        if not roads:
            continue
        path_ = spec.get("path") if isinstance(spec.get("path"), str) and spec.get("path") else DEFAULT_PATH
        out[str(leg)] = {"roads": roads, "path": path_}
    return out


def legs(config=None):
    """The configured leg names, sorted. Empty when no roads file is present."""
    cfg = _load() if config is None else config
    return sorted(cfg)


def _try_road(road, path, timeout):
    """(reached, status, body) for one road. reached is True on ANY HTTP reply (A115: a 429 is answering); False on
    a transport failure (refused, reset, DNS, timeout), which is what makes the caller fall through to the next."""
    url = "http://%s%s" % (road, path)
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return True, r.getcode(), r.read(65536)
    except urllib.error.HTTPError as e:            # it ANSWERED (4xx/5xx, incl. 429). The ROAD is good.
        return True, e.code, b""
    except (urllib.error.URLError, OSError, ValueError):
        return False, None, None                   # no answer over this road: fall through


def read_leg(leg, config=None, timeout=DEFAULT_TIMEOUT):
    """Try a leg's roads in order; return on the first that ANSWERS.

    ok True  -> reached over roads[road_index]; status is the HTTP code (200, or 429 = answering, A115).
    ok False -> every road failed at the transport layer; roads_tried counts them. Never raises.
    Road hosts are masked ('road'); the raw address stays in the config, reachable by road_index.
    """
    cfg = _load() if config is None else config
    spec = cfg.get(leg)
    if not spec:
        return {"leg": leg, "ok": False, "road_index": None, "roads_tried": 0, "error": "no roads configured"}
    roads, path = spec["roads"], spec.get("path", DEFAULT_PATH)
    for i, road in enumerate(roads):
        reached, status, body = _try_road(road, path, timeout)
        if reached:
            return {"leg": leg, "ok": True, "road_index": i, "road": _mask_host(road),
                    "roads_tried": i + 1, "status": status, "body": body}
    return {"leg": leg, "ok": False, "road_index": None, "roads_tried": len(roads),
            "error": "all %d road(s) unreachable" % len(roads)}


def read_all(config=None, timeout=DEFAULT_TIMEOUT, max_workers=16):
    """{leg: read_leg(leg)} with ONE THREAD PER LEG, so a severed leg costs ~one timeout for the whole pass, not
    one per leg in series. Within a leg the roads are still tried in order (read_leg). Never raises."""
    cfg = _load() if config is None else config
    names = sorted(cfg)
    if not names:
        return {}
    out = {}
    with ThreadPoolExecutor(max_workers=max(1, min(max_workers, len(names)))) as pool:
        futs = {pool.submit(read_leg, n, cfg, timeout): n for n in names}
        for fut, n in futs.items():
            try:
                out[n] = fut.result()
            except Exception as e:                 # a leg's read must not sink the pass
                out[n] = {"leg": n, "ok": False, "road_index": None, "error": "read failed: %s" % type(e).__name__}
    return out


def _main(argv=None):
    """A read-only pass, for a person: masked roads only, never an address."""
    cfg = _load()
    if not cfg:
        print("legpaths: no ops/leg_roads.json (or it is empty/malformed) -- no legs configured, nothing read")
        return 0
    t0 = time.time()
    results = read_all(cfg)
    dt = time.time() - t0
    for leg in sorted(results):
        r = results[leg]
        if r.get("ok"):
            print("  %-16s UP   via road %d (%s) status %s" % (leg, r["road_index"], r.get("road", "?"), r.get("status")))
        else:
            print("  %-16s DOWN %s" % (leg, r.get("error", "unreachable")))
    print("legpaths: %d leg(s) read in %.2f s (threaded; a severed leg costs ~one timeout, not one each)"
          % (len(results), dt))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_main(sys.argv[1:]))
