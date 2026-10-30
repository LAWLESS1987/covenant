#!/usr/bin/env python3
"""
verify_head_commitment.py -- STANDALONE independent verifier for the covenant's
signed HEAD-commitment ledger.

It imports NO covenant code. It uses only the Python standard library and
`cryptography` (the same RSA-PSS primitive an independent chain verifier already
needs for genesis -- see docs/SPEC_INDEPENDENT_VERIFIER.md section 1). A stranger
can drop this one file beside a public clone and run it with no covenant source
and no running node.

It answers, over `ops/head_commitments.jsonl` and `docs/HEAD_COMMIT_PUBKEY.pem`:

  1. SIGNATURE  -- every row is signed by the published key
     (RSA-PSS, MGF1-SHA256, salt=MAX_LENGTH, SHA-256), over the domain-framed
     canonical payload. A forged or edited payload fails here.
  2. SEQUENCE   -- seq is 0,1,2,... with no gap or repeat.
  3. CHAIN      -- each row's prev_sha256 equals sha256 of the previous row's
     canonical bytes. This is what makes the ledger append-only in a way an
     outsider can check: a past row cannot be edited in place without breaking
     every row after it.
  4. BINDING    -- (only if run where the committed files are reachable) the
     NEWEST row's head / tree / manifest / genesis / constitution-anchor digests
     match the actual committed repository, tying the signature to THIS tree.

What it does NOT prove, and says so: that the timestamp is honest (only that this
key asserted it), anything about blocks past genesis, or that the running system
obeys the rules. A commitment proves one key committed to exactly this tree, in
this order, and that the chain of commitments was not rewritten in place.

Exit codes: 0 PASS, 1 FAIL, 2 UNDETERMINED (something needed was absent -- it is
named, never silently passed).

Usage:
  python verify_head_commitment.py                      # auto-locate beside this file
  python verify_head_commitment.py --ledger L --pubkey P [--repo DIR]
"""
import argparse
import base64
import hashlib
import json
import os
import subprocess
import sys

DOMAIN = b"COVENANT_HEADCOMMIT_V1"
BOUND_FILES = ("MANIFEST.sha256", "genesis.json",
               "docs/CONSTITUTION_ANCHOR.json", "ops/RECORD_ANCHORS.json",
               "ops/tetsu_consent.jsonl", "ops/tetsu_consent.chain.jsonl",
               "ops/model_pin.json",
               "fallback_model.json", "fallback_model_2.json",
               "fallback_model_phone.json",
               # grid-guard config (2026-10-30); kept in sync with
               # covenant_head_commit.BOUND_FILES. Absent at an older named commit
               # -> skipped; a newer commitment binds them.
               "ops/grid_signers.json", "ops/grid_interlocks.json",
               "ops/grid_policy.json")


def _frame(domain, *fields):
    """Length-prefixed domain framing: domain tag, then for each field a 4-byte
    big-endian length followed by the field bytes. Mirrors the covenant's own
    signing framing so the scheme is one scheme, not two."""
    out = bytearray(domain)
    for f in fields:
        out += len(f).to_bytes(4, "big") + f
    return bytes(out)


def _canon(obj):
    """The one canonical serialization used for signing and for chaining."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def _row_bytes(row):
    return _canon(row)


def _verify_sig(pubkey_pem, payload, signature_b64):
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.exceptions import InvalidSignature
    pub = serialization.load_pem_public_key(pubkey_pem.encode())
    try:
        pub.verify(
            base64.b64decode(signature_b64),
            _frame(DOMAIN, _canon(payload)),
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                        salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256())
        return True
    except InvalidSignature:
        return False


def verify_rows(rows, pubkey_pem):
    """Checks 1-3. Returns (ok: bool, findings: list[str])."""
    findings = []
    if not rows:
        return False, ["empty ledger: nothing is committed"]
    for i, row in enumerate(rows):
        payload = row.get("payload")
        sig = row.get("signature")
        rowpub = row.get("pubkey")
        if not isinstance(payload, dict) or sig is None or rowpub is None:
            findings.append(f"row {i}: malformed (missing payload/signature/pubkey)")
            continue
        if rowpub.strip() != pubkey_pem.strip():
            findings.append(f"row {i}: signed by a key other than the published one")
        if payload.get("v") != DOMAIN.decode():
            findings.append(f"row {i}: wrong domain tag {payload.get('v')!r}")
        if payload.get("seq") != i:
            findings.append(f"row {i}: seq is {payload.get('seq')!r}, expected {i} "
                            f"(a gap or reorder)")
        expected_prev = "0" * 64 if i == 0 else hashlib.sha256(_row_bytes(rows[i - 1])).hexdigest()
        if payload.get("prev_sha256") != expected_prev:
            findings.append(f"row {i}: prev_sha256 does not match the previous row "
                            f"(the append-only chain is broken here)")
        if not _verify_sig(pubkey_pem, payload, sig):
            findings.append(f"row {i}: SIGNATURE INVALID -- payload was forged or edited")
    return (len(findings) == 0), findings


def _committed_bytes(repo, relpath, ref=None, disk_fallback=True):
    """Bytes of relpath as committed at REF -- the commit the commitment NAMES, so
    a dirty working tree or an advanced HEAD cannot change the answer (default HEAD).

    When git has no such path at ref, the on-disk file is read ONLY if
    disk_fallback is true. The fallback serves two real cases: a source tarball
    with no .git (ref is None), and a file the commitment DID bind although it is
    not tracked at ref -- covenant_head_commit reads HEAD-then-disk, so a
    gitignored bound file (ops/model_pin.json) or one not yet committed was bound
    from the working tree, and the working tree is the only place to check it.
    verify_binding passes disk_fallback=False for a file the commitment did NOT
    bind at a named commit: that file postdates the commitment and is skipped,
    rather than a later on-disk copy reading as "present but not bound".
    Returns (bytes|None, source|reason)."""
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
    gref = ref or "HEAD"
    try:
        r = subprocess.run(["git", "-C", repo, "show", f"{gref}:{relpath}"],
                           capture_output=True, timeout=20, env=env)
        if r.returncode == 0:
            return r.stdout, f"git {gref[:12]}"
    except Exception:  # noqa: BLE001
        pass
    if not disk_fallback:
        return None, f"not tracked at {gref[:12]}"
    p = os.path.join(repo, relpath)
    if os.path.exists(p):
        with open(p, "rb") as fh:
            return fh.read(), "on-disk (not tracked at ref, or no git)"
    return None, "absent"


def _git(repo, *args):
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
    try:
        r = subprocess.run(["git", "-C", repo, *args],
                           capture_output=True, text=True, timeout=20, env=env)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:  # noqa: BLE001
        return None


def _git_ok(repo, *args):
    """True iff the git command exits 0 -- for checks like `merge-base --is-ancestor`
    that answer through the exit code, not stdout."""
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
    try:
        r = subprocess.run(["git", "-C", repo, *args], capture_output=True, timeout=20, env=env)
        return r.returncode == 0
    except Exception:  # noqa: BLE001
        return False


def verify_binding(tip_payload, repo):
    """Check 4, against the commit the commitment NAMES -- never the current HEAD,
    so a tree that merely ADVANCED past the commitment is not mistaken for a tamper.
    Returns (status, findings) with status in PASS / STALE / FAIL / UNDETERMINED:
      PASS  -- the named commit is current HEAD and its tree+bound files match what was signed.
      STALE -- the named commit is a valid ANCESTOR of HEAD (the tree advanced; the current
               tip is simply not yet committed-to). Benign: re-run covenant_head_commit.
      FAIL  -- a tamper: the named commit is gone from this history, its tree/bound files
               differ from what was signed, or HEAD is NOT a descendant of it (history rewritten).
      UNDETERMINED -- no git / no named head: bound files were checked against on-disk bytes only.
    """
    findings, undetermined, notes = [], [], []
    committed_head = tip_payload.get("head")
    cur_head = _git(repo, "rev-parse", "HEAD")
    ref = None

    if cur_head is None or committed_head is None:
        undetermined.append("no git / no committed head here: bound files checked "
                            "against on-disk bytes only (verify in a clone at the committed head)")
    elif _git(repo, "cat-file", "-t", committed_head) != "commit":
        findings.append(f"the committed commit {str(committed_head)[:12]} is not in this history "
                        f"-- it was rewritten away, or this is a different history")
    else:
        ref = committed_head
        if _git(repo, "rev-parse", f"{committed_head}^{{tree}}") != tip_payload.get("tree"):
            findings.append(f"tree mismatch at {committed_head[:12]}: the named commit's tree "
                            f"is not the one signed")
        if cur_head == committed_head:
            pass                                             # freshest: commitment covers the tip
        elif _git_ok(repo, "merge-base", "--is-ancestor", committed_head, "HEAD"):
            notes.append(f"STALE: HEAD has advanced to {cur_head[:12]}; the newest commitment "
                         f"covers {committed_head[:12]} (an ancestor). Re-run covenant_head_commit "
                         f"to cover the current tip.")
        else:
            findings.append(f"DIVERGED: current HEAD {cur_head[:12]} is NOT a descendant of the "
                            f"committed {committed_head[:12]} -- history was rewritten or forked")

    bound = tip_payload.get("bound", {})
    for rel in BOUND_FILES:
        # At a NAMED commit, a file the commitment did not bind (key absent, as in a
        # commitment older than the file's addition to BOUND_FILES, or bound None) is
        # read from git only: not tracked there -> it postdates the commitment -> skip.
        was_bound = bound.get(rel) is not None
        raw, src = _committed_bytes(repo, rel, ref,
                                    disk_fallback=(ref is None or was_bound))
        if raw is None:
            if rel in bound and bound[rel] is not None:
                undetermined.append(f"{rel}: bound but not reachable at the named commit ({src})")
            continue
        if rel == "genesis.json":
            try:
                actual = json.loads(raw.decode())["hash"]
            except Exception:  # noqa: BLE001
                findings.append("genesis.json: unreadable / no hash field")
                continue
        else:
            actual = hashlib.sha256(raw).hexdigest()
        want = bound.get(rel)
        if want is None:
            undetermined.append(f"{rel}: present at the named commit but not bound by the commitment")
        elif actual != want:
            findings.append(f"{rel}: digest mismatch -- the file at the named commit differs "
                            f"from what was signed (bound {str(want)[:12]}, got {actual[:12]})")

    if findings:
        return "FAIL", findings
    if notes and not undetermined:
        return "STALE", notes
    if undetermined:
        return "UNDETERMINED", undetermined + notes
    return "PASS", []


def run(ledger, pubkey_path, repo):
    out = []
    if not os.path.exists(pubkey_path):
        return 2, [f"UNDETERMINED: no published public key at {pubkey_path}"]
    if not os.path.exists(ledger):
        return 2, [f"UNDETERMINED: no commitment ledger at {ledger}"]
    pubkey_pem = open(pubkey_path, encoding="utf-8").read()
    rows = []
    for ln in open(ledger, encoding="utf-8"):
        ln = ln.strip()
        if ln:
            rows.append(json.loads(ln))

    ok, findings = verify_rows(rows, pubkey_pem)
    out += [f"rows: {len(rows)}"]
    if not ok:
        out += ["SIGNATURE/SEQUENCE/CHAIN: FAIL"] + [f"  - {m}" for m in findings]
        return 1, out
    out += ["SIGNATURE/SEQUENCE/CHAIN: PASS "
            f"(all {len(rows)} rows signed by the published key; chain intact)"]

    status, bfind = verify_binding(rows[-1]["payload"], repo)
    out += [f"BINDING (newest commitment vs the commit it names): {status}"]
    out += [f"  - {m}" for m in bfind]
    if status == "FAIL":
        return 1, out
    if status == "STALE":
        out += ["=> OVERALL: PASS (STALE). The committed history is intact and the newest "
                "commitment is valid for the commit it names; the tree has merely advanced "
                "since. Re-run covenant_head_commit to cover the current tip."]
        return 0, out
    if status == "UNDETERMINED":
        out += ["=> OVERALL: PASS on signatures and chain; BINDING UNDETERMINED "
                "(named above). The signed history is intact; it was not confirmed "
                "against a live tree."]
        return 0, out
    out += ["=> OVERALL: PASS. The published key committed to exactly this tree, "
            "in this order, and the commitment history was not rewritten."]
    return 0, out


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ledger", default=os.path.join(here, "ops", "head_commitments.jsonl"))
    ap.add_argument("--pubkey", default=os.path.join(here, "docs", "HEAD_COMMIT_PUBKEY.pem"))
    ap.add_argument("--repo", default=here)
    a = ap.parse_args()
    code, lines = run(a.ledger, a.pubkey, a.repo)
    print("\n".join(lines))
    verdict = {0: "PASS", 1: "FAIL", 2: "UNDETERMINED"}[code]
    print(f"\nVERDICT: {verdict}  (exit {code})")
    return code


if __name__ == "__main__":
    sys.exit(main())
