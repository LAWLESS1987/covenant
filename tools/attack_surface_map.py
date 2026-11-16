#!/usr/bin/env python3
"""tools/attack_surface_map.py -- the defensive COUNT PASS for security (A438).

WHY THIS EXISTS. The covenant has a strong regression net -- 83 SECURITY-tagged
suites swept daily, mutation_probe.py proving guards are real, a live exec-guard
shadow -- but every one of those locks in a KNOWN finding. Nothing computes the
DENOMINATOR: the whole ingress surface, and which of it has ever had an
adversarial test. So the hunt (his 11-02 directive) has been driven by what we
remember to look at, not by a map of what exists. That is exactly the blind spot
CLAUDE.md's first pass warns about -- "establish the denominators by discovery".

WHAT THIS IS, AND IS NOT. This is a MAP and a REPORT, read-only. It walks the
source, enumerates every Flask route by DISCOVERY (never a hardcoded list --
rule 2), classifies each by exposure, cross-references each to the test suites
and to the gating calls in its own handler, and emits a RANKED HUNT QUEUE: the
surface with no adversarial test, highest-exposure first. It is NOT a guard and
it NEVER says a route is "safe". "has a test" means a test file mentions the
path -- not that the test is adversarial; "gated" means a gating call appears in
the handler body -- not that it is correct or unbypassable. Every such limit is
printed under BLIND SPOTS, because a check that hides what it cannot see
manufactures confidence about the part it never looked at (CLAUDE.md, end pass).

Defensive, on his own systems only. Run: python tools/attack_surface_map.py
"""
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The source files whose Flask routes form the ingress surface this increment
# maps. Discovery walks THESE; anything else (raw P2P, file-fed daemons, the
# cross-process hands door) is named under BLIND SPOTS, not silently covered.
ROUTE_SOURCES = ["covenant_unified_v8.py"]

# The mapper's OWN test necessarily names route paths as classification DATA
# (e.g. "/stake", "/succession/register") and fixtures -- not as a route it
# exercises. Counting it as coverage credited routes nobody attacked and HID
# real uncovered ones (the queue under-reported -- the dangerous direction). It
# is excluded from the test index. A later test that genuinely drives a route
# names it as a real exercise and is counted; this is the one file that cannot.
SELF_TESTS = {"test_asm1_attack_surface.py"}

# --- exposure classification (transparent on purpose: printed in the report) --
# The METHOD is the primary signal: a GET reads, a POST mutates, and the hunt
# queue is about the highest-risk surface -- state change. So EVERY GET-only
# route is READ (score 1, below the queue threshold); GET info-disclosure is a
# real but separate lens, named under BLIND SPOTS, not scored here. A mutating
# route's CATEGORY is set by the first keyword that matches one of its path
# SEGMENTS (segment-exact or segment-prefix before '_', so "heal" matches
# /m/heal but NOT /health). Highest block wins; WRITE is the floor.
EXPOSURE = [
    ("EXEC",    5, ("agent", "propose_code", "workshop", "actuator_learn", "heal")),
    ("MONEY",   4, ("claim_rewards", "stake", "unstake", "mine", "trading")),
    ("CONTROL", 3, ("succession", "approve", "crisis", "register", "gift_node")),
    ("WRITE",   2, ("checkin", "ai_chats", "image", "judge", "sync",
                    "transactions", "report", "peers")),
]
READ = ("READ", 1)

# Which covenant_one.py suite TAGS count as a security-relevant ("adversarial")
# test of a route. The hands-door hardening (A423-A437) is tagged JUDGE, not
# SECURITY -- excluding it cried wolf on /m/agent and /m/workshop/read, which are
# among the most-tested doors in the tree. MONEY/TRADER/LEDGER guard value and
# ledger integrity; HTTP tests the ingress layer; ADVERSARIAL is explicit. Only
# DEPLOYMENT is left out: it pins deploy mechanics, not a route's defense. The
# tag is the suite author's label, not a proof the test attacks THIS route --
# said again under BLIND SPOTS. Printed in the report so the choice is auditable.
ADVERSARIAL_TAGS = {"SECURITY", "IDENTITY", "ADVERSARIAL", "JUDGE",
                    "MONEY", "TRADER", "HTTP", "LEDGER"}

# Gating calls whose PRESENCE in a handler body we note (presence != correct).
GATING = [
    "_request_signed_by_registered", "may_run", "run_sha256", "operator_key",
    "_verify_sig", "signature", "COVENANT_PEER_CALLERS", "owner_only",
    "_authorized", "require_", "verify_operator", "is_operator",
]

ROUTE_RE = re.compile(r'@self\.app\.route\(\s*"([^"]+)"(.*)')
METHODS_RE = re.compile(r'methods\s*=\s*\[([^\]]*)\]')


class Route:
    __slots__ = ("path", "methods", "handler", "lineno", "source", "body")

    def __init__(self, path, methods, handler, lineno, source, body):
        self.path, self.methods, self.handler = path, methods, handler
        self.lineno, self.source, self.body = lineno, source, body

    def key(self):
        return "%s %s" % ("|".join(self.methods), self.path)


def discover_routes(src, source="<mem>"):
    """Every @self.app.route in `src`, with its methods, handler name and body.

    Pure. Body = the lines from the decorator to the next route decorator (or
    EOF); enough to see whether a gating call is present, not a precise parse
    (which is named as a blind spot). A stacked decorator (two routes, one
    handler) yields two Route rows sharing the handler and body."""
    lines = src.splitlines()
    starts = [i for i, ln in enumerate(lines) if ROUTE_RE.search(ln)]
    routes = []
    for n, i in enumerate(starts):
        m = ROUTE_RE.search(lines[i])
        path = m.group(1)
        mm = METHODS_RE.search(m.group(2))
        methods = ([s.strip().strip('"\'').upper() for s in mm.group(1).split(",") if s.strip()]
                   if mm else ["GET"])
        end = starts[n + 1] if n + 1 < len(starts) else len(lines)
        body = "\n".join(lines[i:end])
        handler = ""
        for ln in lines[i + 1:end]:
            dm = re.match(r"\s*def\s+(\w+)\s*\(", ln)
            if dm:
                handler = dm.group(1)
                break
        routes.append(Route(path, methods, handler, i + 1, source, body))
    return routes


def classify_exposure(path, methods):
    """(class, score). A GET-only route is READ. A mutating route takes the
    first matching keyword block's class, else WRITE. Keywords match a path
    SEGMENT exactly, or a segment that begins with `keyword_` -- so "heal"
    matches /m/heal but not /health, and "stake" matches /stake but not /stakes
    (a read) or /unstake (its own keyword)."""
    segs = [s for s in path.lower().split("/") if s]

    def hit(kw):
        return any(s == kw or s.startswith(kw + "_") for s in segs)

    if methods == ["GET"]:
        return READ
    for name, score, kws in EXPOSURE:
        if any(hit(k) for k in kws):
            return (name, score)
    return ("WRITE", 2)


def gating_of(body):
    """The gating calls that APPEAR in a handler body (presence, not proof)."""
    return sorted({g for g in GATING if g in body})


def build_test_index(test_files):
    """path-literal -> [test file basenames that mention it]. `test_files` is a
    list of (basename, text)."""
    idx = {}
    for name, text in test_files:
        for mo in re.finditer(r'["\'](/[A-Za-z0-9_./<>-]+)["\']', text):
            idx.setdefault(mo.group(1), set()).add(name)
    return {k: sorted(v) for k, v in idx.items()}


def parse_security_tags(one_src):
    """basename -> tag, from covenant_one.py's (file, timeout, TAG) tuples. Used
    to tell an ADVERSARIAL suite (SECURITY/IDENTITY) from any mention."""
    tags = {}
    for mo in re.finditer(r'\(\s*"(test_[A-Za-z0-9_]+\.py)"\s*,\s*\d+\s*,\s*"([A-Z]+)"', one_src):
        tags[mo.group(1)] = mo.group(2)
    return tags


def coverage(route, test_index, tags):
    """What tests touch this route, and whether any is adversarial-tagged."""
    files = test_index.get(route.path, [])
    adversarial = sorted(f for f in files if tags.get(f) in ADVERSARIAL_TAGS)
    return {"tests": files, "adversarial": adversarial}


def hunt_queue(rows):
    """Rank the surface to hunt: exposure >= WRITE and NOT (adversarial test AND
    a gating call). Highest exposure first, then the least-covered. Each row is a
    dict already carrying class/score/cov/gating. The queue is WHERE TO LOOK, not
    where a bug is."""
    q = []
    for r in rows:
        if r["score"] < 2:
            continue
        has_adv = bool(r["adversarial"])
        has_gate = bool(r["gating"])
        if has_adv and has_gate:
            continue
        if not has_adv and not has_gate:
            why = "no adversarial test AND no gating call in the handler"
        elif not has_adv:
            why = "gated, but no security-relevant test names it"
        else:
            why = "tested, but no gating call visible in the handler"
        q.append({**r, "why": why})
    q.sort(key=lambda r: (-r["score"], bool(r["adversarial"]), bool(r["gating"]), r["path"]))
    return q


def build_report():
    """Read the real tree and assemble the map. Returns (rows, queue, meta)."""
    srcs_read, rows = [], []
    for rel in ROUTE_SOURCES:
        p = os.path.join(HERE, rel)
        if not os.path.exists(p):
            continue
        srcs_read.append(rel)
        src = open(p, encoding="utf-8").read()
        for r in discover_routes(src, rel):
            rows.append(r)

    test_files = []
    for p in sorted(glob.glob(os.path.join(HERE, "test_*.py"))):
        if os.path.basename(p) in SELF_TESTS:
            continue
        try:
            test_files.append((os.path.basename(p), open(p, encoding="utf-8").read()))
        except OSError:
            pass
    test_index = build_test_index(test_files)
    one_p = os.path.join(HERE, "covenant_one.py")
    tags = parse_security_tags(open(one_p, encoding="utf-8").read()) if os.path.exists(one_p) else {}

    enriched = []
    for r in rows:
        cls, score = classify_exposure(r.path, r.methods)
        cov = coverage(r, test_index, tags)
        enriched.append({
            "path": r.path, "methods": r.methods, "handler": r.handler,
            "source": r.source, "class": cls, "score": score,
            "tests": cov["tests"], "adversarial": cov["adversarial"],
            "gating": gating_of(r.body),
        })
    queue = hunt_queue(enriched)
    meta = {"sources_read": srcs_read, "routes": len(enriched),
            "test_files": len(test_files)}
    return enriched, queue, meta


BLIND_SPOTS = [
    "'tests' means a test FILE mentions the path literal -- not that it exercises",
    "   the route, and not that it attacks it. 'adversarial' narrows to a suite in",
    "   a security-relevant family (%s) that"
    % "/".join(sorted(ADVERSARIAL_TAGS)),
    "   names the path; the tag is the author's label, still only a signal.",
    "'gating' lists gating calls PRESENT in the handler body -- not that they are",
    "   correct, reached on every branch, or unbypassable. Absence is the signal;",
    "   presence is not a clearance.",
    "Only Flask routes in %s are mapped. NOT mapped: raw P2P / socket handlers,"
    % ", ".join(ROUTE_SOURCES),
    "   file-fed daemons (ops/*.jsonl consumers), the cross-process hands door,",
    "   CLI entry points, and routes defined in other modules. Separate surfaces.",
    "Handler body is cut at the next route decorator -- a coarse span, not an AST.",
    "   A multi-line @route decorator is not parsed (none exist today).",
    "GET routes are scored READ and sit below the queue. INFO DISCLOSURE on a GET",
    "   (e.g. /trading/net_pnl, /stakes leaking value state) is a real but separate",
    "   lens this increment does not score -- a later pass, not a clearance.",
]


def render(rows, queue, meta):
    out = []
    out.append("ATTACK SURFACE MAP (A438) -- defensive, read-only. A MAP, not a verdict.")
    out.append("sources read: %s | routes discovered: %d | test files scanned: %d"
               % (", ".join(meta["sources_read"]), meta["routes"], meta["test_files"]))
    by_class = {}
    for r in rows:
        by_class.setdefault(r["class"], 0)
        by_class[r["class"]] += 1
    out.append("by exposure: " + ", ".join("%s=%d" % (k, by_class[k])
               for k in ("EXEC", "MONEY", "CONTROL", "WRITE", "READ") if k in by_class))
    uncovered = len(queue)
    out.append("HUNT QUEUE: %d of %d routes have no (adversarial test AND gating call)."
               % (uncovered, meta["routes"]))
    out.append("")
    out.append("  #  EXPOSURE  METHOD  ROUTE                         WHY IT IS QUEUED")
    for i, r in enumerate(queue, 1):
        out.append("  %-2d %-8s  %-6s  %-28s  %s"
                   % (i, r["class"], "|".join(r["methods"]), r["path"], r["why"]))
    out.append("")
    out.append("BLIND SPOTS (what this map cannot see -- read before trusting a green):")
    for b in BLIND_SPOTS:
        out.append("  - " + b if not b.startswith("   ") else "    " + b.strip())
    return "\n".join(out)


def main(argv):
    rows, queue, meta = build_report()
    if "--json" in argv:
        print(json.dumps({"meta": meta, "routes": rows, "queue": queue,
                          "blind_spots": [b.strip() for b in BLIND_SPOTS]}, indent=2))
    else:
        print(render(rows, queue, meta))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
