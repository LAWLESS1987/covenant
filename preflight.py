#!/usr/bin/env python3
"""
preflight.py -- run this BEFORE launching a node.

Every check here corresponds to a failure that was actually observed during
development, and every one of them was silent at the time. A node with no judge
key boots and rejects all traffic. A node that minted its own genesis peers
happily and never converges. A listener thread that died left the node serving
HTTP while deaf. None of that showed up until someone measured it.

    python3 preflight.py                      # check the defaults
    python3 preflight.py --genesis g.json     # check a specific launch config

Exit code 0 = safe to launch. 1 = blocking problem. 2 = launches, but degraded.
"""
import sys, os, json, argparse, tempfile, importlib, socket, stat

OK, WARN, FAIL = "OK", "WARN", "FAIL"
results = []


def check(name, status, detail=""):
    results.append((status, name, detail))
    mark = {OK: "  ok  ", WARN: " warn ", FAIL: " FAIL "}[status]
    print(f"[{mark}] {name}" + (f"\n          {detail}" if detail else ""))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--genesis", default=os.environ.get("COVENANT_GENESIS", ""))
    ap.add_argument("--db", default="")
    ap.add_argument("--port", type=int, default=5000)
    args = ap.parse_args()

    print("=" * 68)
    print("COVENANT PREFLIGHT")
    print("=" * 68)

    # ---------------- dependencies ----------------
    print("\n-- dependencies --")
    for mod in ("flask", "cryptography", "requests"):
        try:
            importlib.import_module(mod)
            check(f"{mod} importable", OK)
        except Exception as e:
            check(f"{mod} importable", FAIL, f"{e} -- pip install -r requirements.txt")
    try:
        importlib.import_module("brainflow")
        check("brainflow (optional)", OK, "neural telemetry bridge will be live")
    except Exception:
        check("brainflow (optional)", OK, "absent -- neural bridge degrades gracefully, not an error")

    # ---------------- modules ----------------
    print("\n-- modules --")
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        import covenant_unified_v8 as cov
        check("core module imports", OK, f"{cov.COVENANT_VERSION}")
    except Exception as e:
        check("core module imports", FAIL, str(e))
        return finish()
    for mod, label in (("covenant_trading_bridge", "trading bridge"),
                       ("covenant_neural_bridge", "neural bridge"),
                       ("covenant_path_pattern", "path-pattern module")):
        try:
            importlib.import_module(mod)
            check(f"{label} imports", OK)
        except Exception as e:
            check(f"{label} imports", WARN, f"{e} -- node runs without it")

    # ---------------- ethics gate ----------------
    print("\n-- ethics gate --")
    providers = os.environ.get("COVENANT_JUDGE_PROVIDERS", "claude")
    keys = {v: bool(os.environ.get(v)) for v in
            ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY")}
    insecure = os.environ.get("COVENANT_INSECURE_MOCK_JUDGE") == "1"
    if insecure:
        check("judge configuration", WARN,
              "COVENANT_INSECURE_MOCK_JUDGE=1 -- the ethics gate is KEYWORD MATCHING. "
              "Adversarial transactions are known to pass it. Never set in production.")
    elif not any(keys.values()):
        check("judge configuration", FAIL,
              "no provider API key set. The gate fails CLOSED, so this node will boot, "
              "serve /chain, peer correctly and REJECT EVERY TRANSACTION. "
              "Set ANTHROPIC_API_KEY, or opt in to the mock judge for development.")
    else:
        live = [k for k, v in keys.items() if v]
        check("judge configuration", OK, f"providers={providers} keys={live}")
    if os.environ.get("COVENANT_VETO_FRACTION", "").lower() == "phi":
        check("veto threshold", WARN,
              "COVENANT_VETO_FRACTION=phi RAISES the dissent threshold, making the gate "
              "harder to trip than the majority default.")
    else:
        check("veto threshold", OK, "majority (0.5)")

    # ---------------- genesis ----------------
    print("\n-- genesis --")
    if not args.genesis:
        check("canonical genesis", WARN,
              "no --genesis given. This node will mint its OWN genesis: it cannot "
              "converge with any peer, and it mints itself 1000. Fine for a single "
              "node; wrong for a network. Founder: --export-genesis genesis.json")
    elif not os.path.exists(args.genesis):
        check("canonical genesis", FAIL, f"{args.genesis} not found")
    else:
        try:
            raw = json.load(open(args.genesis))
            txs = [cov.Transaction(**t) for t in raw["transactions"]]
            blk = cov.Block(raw["index"], txs, raw["previous_hash"])
            blk.timestamp = raw["timestamp"]; blk.nonce = raw["nonce"]
            blk.hash = raw["hash"]
            blk.alignment_score = raw.get("alignment_score", 1.0)
            blk.stake_rewards = raw.get("stake_rewards", 0.0)
            problems = []
            if blk.index != 0: problems.append("index != 0")
            if blk.hash != blk.compute_hash(): problems.append("hash does not match contents")
            if not blk.proof_of_work_ok(): problems.append("proof-of-work invalid")
            if not all(t.verify() for t in txs): problems.append("signature invalid")
            if problems:
                check("canonical genesis", FAIL, f"{args.genesis}: {', '.join(problems)}")
            else:
                check("canonical genesis", OK, f"{blk.hash[:24]} verified (hash, PoW, signature)")
        except Exception as e:
            check("canonical genesis", FAIL, f"{args.genesis}: {e}")

    # ---------------- node identity ----------------
    print("\n-- node identity --")
    db = args.db or "covenant_unified_<node-id>.db"
    keyfile = f"{args.db}.key" if args.db else ""
    if keyfile and os.path.exists(keyfile):
        mode = stat.S_IMODE(os.stat(keyfile).st_mode)
        if mode & 0o077:
            check("identity key permissions", FAIL,
                  f"{keyfile} is {oct(mode)} -- readable by others. chmod 600 it.")
        else:
            check("identity key", OK, f"{keyfile} present, {oct(mode)}")
        check("identity backup", WARN,
              f"{keyfile} IS this node's operator credential and its genesis mint key. "
              f"Back it up. Losing it loses both.")
    else:
        check("identity key", OK, f"will be created at {db}.key on first boot (mode 0600)")

    # ---------------- ports ----------------
    print("\n-- ports --")
    for label, port in (("HTTP", args.port), ("P2P", args.port + 1), ("bridge", args.port + 11)):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("127.0.0.1", port)); s.close()
            check(f"{label} port {port} free", OK)
        except OSError as e:
            check(f"{label} port {port}", FAIL, str(e))

    # ---------------- live boot ----------------
    print("\n-- boot smoke test --")
    try:
        tmp = tempfile.mkdtemp()
        m = cov.CovenantUnifiedMaster("PREFLIGHT", host="127.0.0.1", port=18990,
                                      p2p_port=18991, db_path=os.path.join(tmp, "p.db"))
        if args.genesis and os.path.exists(args.genesis):
            m.load_canonical_genesis(args.genesis)
        else:
            m.add_genesis_block()
        c = m.api.app.test_client()
        n_routes = len({str(r.rule) for r in m.api.app.url_map.iter_rules()})
        check("node constructs and mints/adopts genesis", OK,
              f"height={len(m.node.chain)}, {n_routes} routes registered")
        h = c.get("/health").get_json()
        check("trading bridge attached", OK if h["subsystems"]["trading_bridge"] else WARN)
        check("neural bridge attached", OK if h["subsystems"]["neural_bridge"] else WARN)
        for w in h["warnings"]:
            check("health warning", WARN, w)
        bad = [str(r.rule) for r in m.api.app.url_map.iter_rules()
               if c.open(str(r.rule), method="GET").status_code >= 500]
        check("no route returns 5xx on a bare GET", OK if not bad else FAIL, str(bad))
    except Exception as e:
        check("boot smoke test", FAIL, f"{type(e).__name__}: {e}")

    return finish()


def finish():
    fails = [r for r in results if r[0] == FAIL]
    warns = [r for r in results if r[0] == WARN]
    print("\n" + "=" * 68)
    print(f"{len(results)} checks: {len(results)-len(fails)-len(warns)} ok, "
          f"{len(warns)} warn, {len(fails)} FAIL")
    if fails:
        print("\nBLOCKING -- do not launch until these are resolved:")
        for _, n, d in fails:
            print(f"  * {n}: {d}")
        print("=" * 68)
        return 1
    if warns:
        print("\nLaunches, but DEGRADED. Each of these was a silent failure once:")
        for _, n, d in warns:
            print(f"  * {n}: {d[:100]}")
        print("=" * 68)
        return 2
    print("\nReady to launch.")
    print("=" * 68)
    return 0


if __name__ == "__main__":
    sys.exit(main())
