#!/usr/bin/env python3
"""test_a114_own_genesis.py -- the /health `own_genesis` alarm measures what it
claims to measure: my genesis is not the one my peers hold.

THE DEFECT (2026-09-14). The alarm's text says "node minted its OWN genesis --
it cannot converge with peers". The code asked a different question: "did my own
key sign the genesis block?" Those two answers come apart on exactly one node in
any network -- the founder, whose key signed the canonical genesis that everyone
else then adopted. Node A minted this network's genesis on 2026-08-19 and
exported the file B and C loaded. All three run a byte-identical chain (23
blocks, same tip, verified), and node A alone reported own_genesis=true and
therefore degraded=true, permanently, since the day the network started.

WHY THAT IS WORTH FIXING RATHER THAN ANNOTATING. The health block this lives in
exists because, as its own docstring says, this system has repeatedly been able
to look healthy while being useless. A permanent false alarm is that same
failure inverted: it teaches whoever reads /health that `degraded` on node A
means nothing, which is exactly the habit that makes the next real alarm
invisible. It also cost a real decision -- the rolling restart on 2026-09-14
stopped at node A and refused to continue, correctly by its own rules, on this
non-problem.

WHAT THESE CHECKS ARE. Every one of them drives the REAL /health route through
Flask's test client on a real node object with a real database and a real key.
None of them reads the source looking for words. That matters here more than
usual: 35 of 36 "guards" audited on 2026-09-09 turned out to grep source text,
and a guard that greps cannot tell a fix from a comment about a fix. A114.4 is
the check that earns the change -- it is a genuine divergence the OLD code
scored as clean, so this is not merely a false alarm removed, it is a blind spot
closed at the same time.

Run:  python test_a114_own_genesis.py
"""
import json
import os
import sys
import tempfile
import traceback

# SET, NOT setdefault (2026-09-14, second try). This suite builds real node
# objects, so the judge quorum has to construct -- and `setdefault` respects
# whatever the caller already exported. The CI sweep exports
# COVENANT_JUDGE_PROVIDERS with `mock` in it, so on the runner this suite
# inherited that, build_semantic_quorum raised
#   ValueError: provider 'mock' requires COVENANT_INSECURE_MOCK_JUDGE=1
# before the first check ran, and covenant_one reported NO RESULT -- which is
# not a pass, and is exactly the "green here, red there" shape the house rule
# about running it where the runner runs it exists to catch. It passed locally
# and from a staged copy because neither had that variable set. The judge this
# suite needs is not a matter of taste: it needs one that builds with no API
# key and no insecure mock, which is the semantic one.
os.environ["COVENANT_JUDGE_PROVIDERS"] = "semantic"
os.environ.pop("COVENANT_INSECURE_MOCK_JUDGE", None)
os.environ.pop("COVENANT_DB_PATH", None)          # never inherit a real node's database

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import covenant_unified_v8 as C                                        # noqa: E402

RESULTS = []
_PORT = [5940]


def check(label, ok, detail=""):
    RESULTS.append((label, bool(ok), detail))
    print("%-6s %-46s %s" % ("ok" if ok else "FAIL", label, detail))
    return bool(ok)


def skip(label, why):
    RESULTS.append((label, None, why))
    print("%-6s %-46s %s" % ("SKIP", label, why))


def master(tmp, name):
    """A node with its own database and its own key, wired but not listening.

    A distinct port per node only because the constructor derives the p2p port
    from it; nothing here binds a socket, which is why this suite runs in a
    second rather than the minutes three real boots would cost.
    """
    _PORT[0] += 2
    return C.CovenantUnifiedMaster(name, port=_PORT[0],
                                   db_path=os.path.join(tmp, "%s.db" % name))


def health(m):
    r = m.api.app.test_client().get("/health")
    if r.status_code != 200:
        raise RuntimeError("/health returned %s" % r.status_code)
    return r.get_json()


def genesis_warning(h):
    """The warning line about genesis, if /health raised one."""
    for w in h.get("warnings") or []:
        if "genesis" in w.lower():
            return w
    return ""


def main():
    tmp = tempfile.mkdtemp(prefix="a114_")
    canonical = os.path.join(tmp, "genesis_canonical.json")
    other = os.path.join(tmp, "genesis_other.json")

    # ---------------------------------------------------------------- founder
    # Node A's exact situation: this key mints the genesis, exports the file
    # the others will adopt, then the process restarts and is pointed at that
    # same file -- which it does not re-adopt, because the chain is already in
    # its database.
    f = master(tmp, "FOUNDER")
    f.add_genesis_block()
    f.export_genesis(canonical)
    canonical_hash = f.node.chain[0].hash
    founder_signed = f.public_key.public_bytes(
        C.serialization.Encoding.PEM,
        C.serialization.PublicFormat.SubjectPublicKeyInfo).decode() == \
        f.node.chain[0].transactions[0].sender_pubkey
    check("A114.0 founder's own key signed genesis", founder_signed,
          "the premise of the false alarm; without this the rest proves nothing")

    f2 = master(tmp, "FOUNDER")                       # same db, same key: a restart
    check("A114.1a restart resumes the chain", bool(f2.node.chain) and
          f2.node.chain[0].hash == canonical_hash,
          "height %d" % len(f2.node.chain))
    adopted = f2.load_canonical_genesis(canonical)
    check("A114.1b restart does not re-adopt", adopted is False,
          "returned %r; the chain was already there" % adopted)
    h = health(f2)
    check("A114.1c founder on the canonical chain is NOT own_genesis",
          h.get("own_genesis") is False, "own_genesis=%r" % h.get("own_genesis"))
    check("A114.1d and raises no genesis warning", genesis_warning(h) == "",
          genesis_warning(h) or "none")

    # ---------------------------------------------------------------- adopter
    # Nodes B and C. This passed before the fix too; it is here so the fix
    # cannot buy the founder's silence by breaking everyone else.
    b = master(tmp, "ADOPTER")
    check("A114.2a adopter adopts the canonical file",
          b.load_canonical_genesis(canonical) is True, "")
    hb = health(b)
    check("A114.2b adopter is NOT own_genesis", hb.get("own_genesis") is False,
          "own_genesis=%r" % hb.get("own_genesis"))
    check("A114.2c adopter is on the canonical genesis",
          hb.get("genesis") == canonical_hash, str(hb.get("genesis"))[:16])

    # ------------------------------------------------- the alarm's real cause
    # A node that minted itself a chain in isolation and is then pointed at the
    # canonical file. It cannot converge. This must still fire.
    d = master(tmp, "SELFMINTED")
    d.add_genesis_block()
    check("A114.3a self-minted genesis differs from canonical",
          d.node.chain[0].hash != canonical_hash, "")
    d.load_canonical_genesis(canonical)
    hd = health(d)
    check("A114.3b self-minted node IS own_genesis", hd.get("own_genesis") is True,
          "own_genesis=%r" % hd.get("own_genesis"))
    w = genesis_warning(hd)
    check("A114.3c the warning names both hashes",
          d.node.chain[0].hash[:16] in w and canonical_hash[:16] in w,
          w[:80] or "no genesis warning")
    # A114.3d WAS "and it is reported degraded", asserting hd["degraded"] is
    # True. That check was DECORATIVE and an adversarial review proved it: in
    # this environment `degraded` is already True from `keyless` alone, so it
    # passed whatever own_genesis did, including with the fix reverted. A check
    # that cannot fail is not a check. What is actually worth pinning is the
    # CONTRAST -- the same field differing between the founder and a node that
    # really did mint its own chain -- because that is the whole change.
    check("A114.3d own_genesis differs between the founder and a self-minted node",
          h.get("own_genesis") is False and hd.get("own_genesis") is True,
          "founder %r vs self-minted %r" % (h.get("own_genesis"), hd.get("own_genesis")))
    check("A114.3e and only the self-minted one carries a genesis warning",
          genesis_warning(h) == "" and genesis_warning(hd) != "",
          "founder: %s" % (genesis_warning(h) or "none"))

    # ------------------------------------ the divergence the OLD test MISSED
    # A node that adopted a genesis somebody else minted -- just not the one
    # its operator believes the network is on. Its own key signed nothing, so
    # the signer test called it clean while it sat on an unreachable chain.
    # This is the check that makes the change an improvement rather than a
    # silencing.
    x = master(tmp, "OTHERFOUNDER")
    x.add_genesis_block()
    x.export_genesis(other)
    other_hash = x.node.chain[0].hash
    check("A114.4a the two genesis files really differ",
          other_hash != canonical_hash, "")

    e = master(tmp, "WRONGFILE")
    e.load_canonical_genesis(other)                   # adopts the WRONG network
    e_signed = e.public_key.public_bytes(
        C.serialization.Encoding.PEM,
        C.serialization.PublicFormat.SubjectPublicKeyInfo).decode() == \
        e.node.chain[0].transactions[0].sender_pubkey
    check("A114.4b this node's key did NOT sign its genesis", e_signed is False,
          "so the old signer test scored it clean")
    e.load_canonical_genesis(canonical)               # operator says: you are on THIS network
    he = health(e)
    check("A114.4c a node on the wrong chain IS own_genesis",
          he.get("own_genesis") is True, "own_genesis=%r" % he.get("own_genesis"))

    # ------------------------------------------------- no canonical file given
    # Without --genesis the node has no way to tell a shared chain from one it
    # minted alone, and the signer test is the only signal there is. It must
    # still be used, and it must still fire.
    n = master(tmp, "NOGENESIS")
    n.add_genesis_block()
    hn = health(n)
    check("A114.5a with no genesis file, self-minted still fires",
          hn.get("own_genesis") is True, "own_genesis=%r" % hn.get("own_genesis"))
    check("A114.5b and the warning still says to use --genesis",
          "--genesis" in genesis_warning(hn), genesis_warning(hn)[:60] or "none")

    # ------------------------------------------- a bad file must not break boot
    # Reading the canonical hash happens before the early return, on a path
    # that previously did not touch the file at all on a restart. A node that
    # restarted fine yesterday with an unreadable genesis.json must restart
    # fine today, since nothing is adopted on that path anyway.
    bad = os.path.join(tmp, "corrupt.json")
    with open(bad, "w", encoding="utf-8") as fh:
        fh.write("{not json at all")
    g = master(tmp, "CORRUPTFILE")
    g.add_genesis_block()
    try:
        g.load_canonical_genesis(bad)
        raised = ""
    except Exception as exc:                                          # noqa: BLE001
        raised = "%s: %s" % (type(exc).__name__, exc)
    check("A114.6a a corrupt genesis file does not break a restart",
          raised == "", raised or "returned quietly")
    check("A114.6b and the node falls back to the signer test",
          health(g).get("own_genesis") is True, "")

    missing = os.path.join(tmp, "does_not_exist.json")
    g2 = master(tmp, "MISSINGFILE")
    g2.add_genesis_block()
    try:
        g2.load_canonical_genesis(missing)
        raised2 = ""
    except Exception as exc:                                          # noqa: BLE001
        raised2 = "%s: %s" % (type(exc).__name__, exc)
    check("A114.6c a missing genesis file does not break a restart",
          raised2 == "", raised2 or "returned quietly")

    # ------------------------------------------------------ the live network
    # Three answers, not two (the A84b/A85c lesson): pass, fail, or "the nodes
    # are not running here", which is not a pass.
    try:
        import urllib.request
        with urllib.request.urlopen("http://127.0.0.1:5000/health", timeout=4) as r:
            live = json.loads(r.read().decode("utf-8", "replace"))
    except Exception:                                                 # noqa: BLE001
        live = None
    if live is None:
        skip("A114.7 live node A is not own_genesis", "node A is not answering here")
    elif str(live.get("source_sha256", "")) != C.CORE_SOURCE_SHA12:
        skip("A114.7 live node A is not own_genesis",
             "node A runs %s, this source is %s -- restart it to measure"
             % (live.get("source_sha256"), C.CORE_SOURCE_SHA12))
    else:
        check("A114.7 live node A is not own_genesis",
              live.get("own_genesis") is False, "own_genesis=%r" % live.get("own_genesis"))
        # SAY WHAT THIS DID NOT DO. The commit is named for the founder no
        # longer calling itself unable to converge, and a reader could take
        # that to mean node A is no longer degraded. It is still degraded, for
        # reasons that have nothing to do with genesis -- no provider key, and
        # no usable code sandbox on win32. Pinning the honest version here
        # stops the entry from quietly becoming a bigger claim than it is.
        gw = genesis_warning(live)
        check("A114.7b and no genesis warning remains on the live node", gw == "", gw or "none")
        check("A114.7c degraded is still true, and NOT because of genesis",
              live.get("degraded") is True and gw == "",
              "reasons now: %s" % "; ".join(w[:44] for w in (live.get("warnings") or [])) or "none")

    passed = sum(1 for _, o, _ in RESULTS if o is True)
    failed = sum(1 for _, o, _ in RESULTS if o is False)
    skipped = sum(1 for _, o, _ in RESULTS if o is None)
    print("")
    print("A114: %d passed, %d failed, %d skipped" % (passed, failed, skipped))
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:                                                 # noqa: BLE001
        traceback.print_exc()
        sys.exit(1)
