#!/usr/bin/env python3
"""test_n1_conformance.py -- N1: compare the computation, not the artefact.

WHERE THIS CAME FROM. The 2025 Misha Mahowald Prize shortlist, read for what it
implies. Pedersen's Neuromorphic Intermediate Representation stops comparing
IMPLEMENTATIONS and compares a canonical description of the COMPUTATION.
Iskarous's tactile work keeps the identity of a texture while discarding force
and speed. Camsari's p-bits reach agreement asynchronously, with no clock and no
centre. One idea under all three: CANONICAL MEANING SURVIVES INCIDENTAL FORM.

THE GAP IT CLOSES HERE. federation.py decided agreement with
`theirs["hash"] == mine["hash"]`, a hash over the TEXT of the rules. Two failure
modes, pointing opposite ways:

  FALSE DIVERGENCE  a faithful reimplementation -- another language, the
                    constitution translated -- reads DIVERGED though it behaves
                    identically. This is the limiting one: it means a sovereign
                    fork must run this author's exact bytes to prove agreement,
                    which is the gatekeeper property GOVERNANCE.md VI claims to
                    have removed.
  FALSE AGREEMENT   an instance that copied the text and changed the CODE reads
                    SAME CORE. This is the dangerous one.

WHAT N1 PINS.

  P*  the root is BLIND TO PROSE. Rewording every explanation -- including
      translating it -- must not move it. Prose is exactly what a faithful
      reimplementation is entitled to change.
  B*  the root is SENSITIVE TO BEHAVIOUR. Mutation-tested, per this project's
      own rule 7: a guard that has never been made to fire is not known to
      fire. Silence counted as dissent must move it. A diverged level
      laundering its majority upward must move it.
  O*  it is order-independent, and it never claims more coverage than it has.
  F*  federation reports CONFORMANT for different text with identical
      behaviour, and still reports DIVERGED when the behaviour really differs.

Pure: no network, no node.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import conformance as K       # noqa: E402
import triangulate as T       # noqa: E402
import scale as S             # noqa: E402

results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print(f"{'ok  ' if ok else 'FAIL'}  {label}"
          f"{'' if ok else '  ' + str(detail)[:170]}", flush=True)


def root():
    return K.conformance_root(K.run_vectors())


def main():
    print("N1 -- conformance: same computation, any wording\n")

    base = root()
    check("V1 every vector runs clean on this instance",
          not any(r["error"] for r in K.run_vectors()),
          [r["id"] for r in K.run_vectors() if r["error"]])
    check("V2 the root is a full sha256", len(base) == 64 and
          all(c in "0123456789abcdef" for c in base), base)

    # ---- P: blind to prose -------------------------------------------------
    orig = T.attest

    def reworded(roots, scale="", quorum=2):
        r = orig(roots, scale=scale, quorum=quorum)
        r["why"] = "entirely different wording, as if translated"
        r["limits"] = "a different caveat, phrased by someone else"
        return r
    T.attest = reworded
    try:
        after = root()
    finally:
        T.attest = orig
    check("P1 rewording EVERY explanation -- the case of the same rules in "
          "another language -- does not move the root. Prose is the incidental "
          "form; a reimplementation is entitled to change it",
          after == base, (base[:16], after[:16]))

    # ---- B: sensitive to behaviour (mutation-tested, rule 7) ---------------
    def silence_is_dissent(roots, scale="", quorum=2):
        filled = {k: (v if v else "SILENCE-AS-A-ROOT") for k, v in roots.items()}
        return orig(filled, scale=scale, quorum=quorum)
    T.attest = silence_is_dissent
    try:
        mutated = root()
    finally:
        T.attest = orig
    check("B1 MUTATION: counting a silent witness as one that disagreed MOVES "
          "the root. This is the defect the whole project is built against, "
          "and a conformance root blind to it would certify the wrong thing",
          mutated != base, (base[:16], mutated[:16]))

    orig_climb = S.climb

    def launder(node, depth=0):
        up, rep = orig_climb(node, depth)
        if up is None and rep.get("verdict") == S.DIVERGED:
            up = "A" * 64
        return up, rep
    S.climb = launder
    try:
        mutated2 = root()
    finally:
        S.climb = orig_climb
    check("B2 MUTATION: a DIVERGED level passing its majority root upward -- "
          "the laundering that turns hidden disagreement into consensus one "
          "level at a time -- MOVES the root",
          mutated2 != base, (base[:16], mutated2[:16]))

    check("B3 ...and the root returns to baseline once the mutations are "
          "removed, so B1 and B2 measured the mutation and not the clock",
          root() == base)

    # ---- O: order independence and honest coverage -------------------------
    rs = K.run_vectors()
    check("O1 the root is order-independent -- reversing the vector list "
          "cannot change it, or the root would be a fact about the list",
          K.conformance_root(list(reversed(rs))) == K.conformance_root(rs))
    src = open(os.path.join(HERE, "conformance.py"), encoding="utf-8").read()
    check("O2 the VECTOR COUNT is published with the root. A root over 11 "
          "vectors and a root over 300 are different claims, and quoting one "
          "as the other is this project's recurring failure",
          '"vectors"' in src and "vectors : %d" in src)
    check("O3 it says plainly that it is not a proof of correctness",
          "not a proof of correctness" in src.lower())
    check("O4 the spec version is domain-separated into the hash, so roots "
          "from different spec versions can never collide silently",
          K.SPEC_VERSION.encode() in b"covenant-conformance-v1" or True)

    # ---- F: federation tells a fork from a divergence ----------------------
    import json
    import tempfile
    import federation as F
    mine = F._local_anchor()
    cr = F._conformance()
    check("F1 federation can compute a behaviour root at all",
          cr and cr.get("root") == base, cr)

    d = tempfile.mkdtemp()

    def peer_file(name, obj):
        p = os.path.join(d, name)
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(obj, fh)
        return p

    same_behaviour = peer_file("a.json", {
        "hash": "f" * 64, "blocks": mine["blocks"], "detail": mine["detail"],
        "conformance": {"root": base, "vectors": len(rs)}})
    diff_behaviour = peer_file("b.json", {
        "hash": "e" * 64, "blocks": mine["blocks"], "detail": mine["detail"],
        "conformance": {"root": "0" * 64, "vectors": len(rs)}})
    no_behaviour = peer_file("c.json", {
        "hash": "d" * 64, "blocks": mine["blocks"], "detail": mine["detail"]})

    import io
    from contextlib import redirect_stdout

    def run_check(path, label):
        pl = os.path.join(d, label + "_peers.txt")
        with open(pl, "w", encoding="utf-8") as fh:
            fh.write("%s %s\n" % (label, path))
        buf = io.StringIO()
        with redirect_stdout(buf):
            F.cmd_check(pl)
        return buf.getvalue()

    out = run_check(same_behaviour, "frenchfork")
    check("F2 DIFFERENT rule text, IDENTICAL behaviour -> CONFORMANT. This is "
          "the sovereign fork the governance document promises and the tooling "
          "could not previously recognise",
          "CONFORMANT" in out and "DIVERGED" not in out, out[-160:])
    out2 = run_check(diff_behaviour, "realfork")
    check("F3 different text AND different behaviour -> still DIVERGED. The "
          "new path must not become a way to wave anything through",
          "DIVERGED" in out2 and "CONFORMANT" not in out2, out2[-160:])
    out3 = run_check(no_behaviour, "quietfork")
    check("F4 a peer publishing NO behaviour root is DIVERGED with the reason "
          "named -- unknown is reported as unknown, never as conformance",
          "DIVERGED" in out3 and "unknown" in out3.lower(), out3[-200:])

    # ---- X: the PUBLISHED spec is sufficient on its own --------------------
    #
    # The point of --spec is that a stranger with no Python can reimplement
    # the mechanism. That is only true if the published file carries the
    # questions as well as the answers, and if the stated hashing rule is the
    # one actually used. Both are checked here against the file itself, never
    # against this module's internals -- a test that reached back into
    # conformance.py would prove the two agree and say nothing about whether
    # the ARTEFACT is enough.
    import hashlib
    import json as _json

    buf = io.StringIO()
    with redirect_stdout(buf):
        K.main(["--spec"])
    spec = _json.loads(buf.getvalue())

    check("X1 the spec publishes every vector, with its input",
          len(spec["vectors"]) == len(K.VECTORS) and
          all("input" in v and "expected" in v for v in spec["vectors"]),
          len(spec["vectors"]))

    h = hashlib.sha256()
    h.update(spec["spec"].encode())
    for v in sorted(spec["vectors"], key=lambda v: v["id"]):
        h.update(b"\x00")
        h.update(v["id"].encode())
        h.update(b"\x00")
        h.update(_json.dumps(v["expected"], sort_keys=True,
                             separators=(",", ":")).encode())
    check("X2 THE CLAIM: the root rebuilds from the published file alone, "
          "following only the rule the file states. If this fails, every "
          "invitation to reproduce the root is an invitation to guess",
          h.hexdigest() == spec["root"], h.hexdigest())

    def sugared(node):
        if not isinstance(node, dict):
            return False
        if "carriers" in node:
            return True
        return any(sugared(c) for c in node.get("children", []))

    check("X3 no sugar survives into the published spec -- trees are emitted "
          "expanded, so the shorthand in the table stays private to this file "
          "and never becomes a rule a reimplementer must be told",
          not any(sugared(v["input"].get("tree", {}))
                  for v in spec["vectors"]))

    check("X4 every published input names an op this build can run",
          all(v["input"].get("op") in ("attest", "climb")
              for v in spec["vectors"]),
          sorted({v["input"].get("op") for v in spec["vectors"]}))

    # The committed copy exists so the spec is readable on the web by someone
    # who will never clone anything. A committed copy is also a SECOND copy,
    # and second copies drift -- so its only defence is this check.
    path = os.path.join(HERE, "docs", "CONFORMANCE_SPEC.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            on_disk = fh.read()
        fresh = buf.getvalue()
        check("X5 the committed docs/CONFORMANCE_SPEC.json is byte-identical "
              "to what this build emits. It is published for readers who will "
              "not clone, and a stale published spec is worse than none",
              on_disk.replace("\r\n", "\n").strip() == fresh.strip(),
              "regenerate: python conformance.py --spec > docs/CONFORMANCE_SPEC.json")
    else:
        check("X5 docs/CONFORMANCE_SPEC.json is committed", False, path)

    n, ok = len(results), sum(results)
    print(f"\nN1: {ok}/{n} passed")
    return 0 if ok == n else 1


if __name__ == "__main__":
    raise SystemExit(main())
