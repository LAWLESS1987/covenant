#!/usr/bin/env python3
"""
covenant_head_commit.py -- a signed, append-only, hash-chained commitment to the
repository's current committed state, made for OUT-OF-BAND publication.

WHY THIS EXISTS  (gap #1 of docs/SPEC_INDEPENDENT_VERIFIER.md section 8)
  Without this, the covenant's integrity rests on GitHub branch protection plus
  our word: an adversary who edits a file AND regenerates MANIFEST.sha256 (and the
  constitution anchor) produces a tree that passes every self-consistent check.
  Nothing cryptographic binds the history to anything outside the host.

  This binds the repository's HEAD -- the git commit, its tree, the substrate
  manifest, the chain genesis, and the constitution anchor -- into one statement,
  signs it with a key whose PRIVATE half never leaves this machine (generated once,
  locked owner-only, *.key so it is never committed), and records it in an
  append-only, hash-chained ledger (ops/head_commitments.jsonl). The PUBLIC key is
  published (docs/HEAD_COMMIT_PUBKEY.pem). A stranger holding only that public key,
  and an earlier copy of the ledger, can then prove the history was not rewritten
  in place -- with the standalone verify_head_commitment.py, no covenant code, no
  running node.

RELATION TO covenant_anchor.py
  covenant_anchor.py anchors a seal root INTO the chain (tamper-evident only within
  a chain we run end-to-end). This is the repo-level sibling: a detached signature
  over the committed tree, built to be handed to someone who is not us. Its
  docstring already names the missing half -- "publishing the root somewhere you do
  not control". This produces exactly that artifact (docs/HEAD_COMMITMENT.txt is
  safe to hand to anyone). It never publishes for you: the signing is local and the
  out-of-band hand-off is the operator's, by design.

WHAT IT PROVES / DOES NOT
  Proves: one key committed to exactly this committed tree, in this order, and the
  chain of commitments was not edited in place. Does NOT prove the timestamp is
  honest (only that this key asserted it), anything about blocks past genesis, or
  that the running system obeys the rules.

RUN
  python covenant_head_commit.py commit     # sign a new commitment for the current HEAD
  python covenant_head_commit.py verify     # run the standalone verifier
  python covenant_head_commit.py show       # print the latest public commitment (.txt)
"""
import argparse
import base64
import hashlib
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DOMAIN = b"COVENANT_HEADCOMMIT_V1"
# What a commitment binds. The last four were added 2026-10-29 for takeover-
# resistance: Tetsu's consent/refusal record and the model identities, so an
# outside holder of an earlier commitment can prove a forged consent, an erased
# "no", or a swapped judge/student model -- the two things the operator asked be
# kept autonomous. (Detection arms only once the signing key is OFF this host and
# a commitment is published out of band; on-host, an owner-level adversary reads
# the key and re-signs. See docs/SPEC_INDEPENDENT_VERIFIER.md section 8.)
BOUND_FILES = ("MANIFEST.sha256", "genesis.json",
               "docs/CONSTITUTION_ANCHOR.json", "ops/RECORD_ANCHORS.json",
               "ops/tetsu_consent.jsonl", "ops/tetsu_consent.chain.jsonl",
               "ops/model_pin.json",
               "fallback_model.json", "fallback_model_2.json",
               "fallback_model_phone.json",
               # grid-guard config (2026-10-30): who may sign, the interlock bounds,
               # and the authority (together-vote) policy -- so an off-host holder of
               # an earlier commitment detects a rogue signer, widened bounds, or a
               # weakened authorization rule. Bind to None until first committed.
               "ops/grid_signers.json", "ops/grid_interlocks.json",
               "ops/grid_policy.json")

KEY_DIR = os.path.join(HERE, ".covenant-keys")          # gitignored
KEY_PATH = os.path.join(KEY_DIR, "head_commit.key")     # *.key -> never committed
PUBKEY_PATH = os.path.join(HERE, "docs", "HEAD_COMMIT_PUBKEY.pem")
LEDGER_PATH = os.path.join(HERE, "ops", "head_commitments.jsonl")
LATEST_JSON = os.path.join(HERE, "docs", "HEAD_COMMITMENT.json")
LATEST_TXT = os.path.join(HERE, "docs", "HEAD_COMMITMENT.txt")


def _frame(domain, *fields):
    out = bytearray(domain)
    for f in fields:
        out += len(f).to_bytes(4, "big") + f
    return bytes(out)


def _canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def _git(repo, *args):
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
    try:
        r = subprocess.run(["git", "-C", repo, *args],
                           capture_output=True, text=True, timeout=30, env=env)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:  # noqa: BLE001
        return None


def _committed_bytes(repo, relpath):
    """Bytes of relpath as committed at HEAD (git show), else the on-disk file."""
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
    try:
        r = subprocess.run(["git", "-C", repo, "show", f"HEAD:{relpath}"],
                           capture_output=True, timeout=30, env=env)
        if r.returncode == 0:
            return r.stdout
    except Exception:  # noqa: BLE001
        pass
    p = os.path.join(repo, relpath)
    if os.path.exists(p):
        with open(p, "rb") as fh:
            return fh.read()
    return None


def _lock_owner_only(path):
    """Reuse the covenant's own key-locking recipe (covenant_notify.py docstring):
    strip inheritance and grant the current user full control, nobody else."""
    if os.name != "nt":
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
        return "chmod 600"
    user = os.environ.get("USERNAME") or os.environ.get("USER") or ""
    try:
        subprocess.run(["icacls", path, "/inheritance:r", "/grant:r", f"{user}:F"],
                       capture_output=True, timeout=30)
        return f"icacls owner-only ({user})"
    except Exception as e:  # noqa: BLE001
        return f"LOCK FAILED: {type(e).__name__}"


def ensure_key(key_path=KEY_PATH, pubkey_path=PUBKEY_PATH):
    """Load the commitment signing key; generate+lock it on first use. Returns
    (private_key, pubkey_pem, note)."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.backends import default_backend
    note = "existing key"
    if not os.path.exists(key_path):
        os.makedirs(os.path.dirname(key_path), exist_ok=True)
        priv = rsa.generate_private_key(public_exponent=65537, key_size=2048,
                                        backend=default_backend())
        with open(key_path, "wb") as fh:
            fh.write(priv.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption()))
        note = "generated new key (" + _lock_owner_only(key_path) + ")"
    with open(key_path, "rb") as fh:
        priv = serialization.load_pem_private_key(fh.read(), password=None)
    pubkey_pem = priv.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    os.makedirs(os.path.dirname(pubkey_path), exist_ok=True)
    # publish the public key (idempotent)
    if not os.path.exists(pubkey_path) or open(pubkey_path, encoding="utf-8").read() != pubkey_pem:
        with open(pubkey_path, "w", encoding="utf-8") as fh:
            fh.write(pubkey_pem)
    return priv, pubkey_pem, note


def _read_rows(ledger):
    rows = []
    if os.path.exists(ledger):
        for ln in open(ledger, encoding="utf-8"):
            ln = ln.strip()
            if ln:
                rows.append(json.loads(ln))
    return rows


def make_commitment(repo=HERE, key_path=KEY_PATH, pubkey_path=PUBKEY_PATH,
                    ledger=LEDGER_PATH, now=None):
    """Build, sign and append one commitment. Returns the row dict."""
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding

    priv, pubkey_pem, keynote = ensure_key(key_path, pubkey_path)
    rows = _read_rows(ledger)
    seq = len(rows)
    prev = "0" * 64 if not rows else hashlib.sha256(_canon(rows[-1])).hexdigest()

    bound = {}
    for rel in BOUND_FILES:
        raw = _committed_bytes(repo, rel)
        if raw is None:
            bound[rel] = None
        elif rel == "genesis.json":
            try:
                bound[rel] = json.loads(raw.decode())["hash"]
            except Exception:  # noqa: BLE001
                bound[rel] = None
        else:
            bound[rel] = hashlib.sha256(raw).hexdigest()

    head = _git(repo, "rev-parse", "HEAD")
    tree = _git(repo, "rev-parse", "HEAD^{tree}")
    dirty = _git(repo, "status", "--porcelain")
    utc = time.strftime("%Y-%m-%dT%H:%M:%SZ",
                        time.gmtime(now if now is not None else time.time()))

    payload = {
        "v": DOMAIN.decode(),
        "seq": seq,
        "utc": utc,
        "head": head,
        "tree": tree,
        "bound": bound,
        "working_tree_clean": (dirty == "" if dirty is not None else None),
        "prev_sha256": prev,
        "pubkey_fpr": hashlib.sha256(pubkey_pem.encode()).hexdigest()[:16],
    }
    signature = base64.b64encode(priv.sign(
        _frame(DOMAIN, _canon(payload)),
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256())).decode()
    row = {"payload": payload, "signature": signature, "pubkey": pubkey_pem}

    os.makedirs(os.path.dirname(ledger), exist_ok=True)
    with open(ledger, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
    return row, keynote


def _write_public(row):
    with open(LATEST_JSON, "w", encoding="utf-8") as fh:
        json.dump(row, fh, indent=2, sort_keys=True)
    p = row["payload"]
    lines = [
        "COVENANT HEAD COMMITMENT -- safe to hand to anyone.",
        "A signed, out-of-band statement of exactly what this repository contained.",
        "Keep this. Later, re-run verify_head_commitment.py against a fresh clone;",
        "if the history was rewritten in place, the chain of commitments breaks.",
        "",
        f"seq              {p['seq']}",
        f"utc              {p['utc']}",
        f"git HEAD         {p['head']}",
        f"git tree         {p['tree']}",
        f"working tree     {'clean' if p['working_tree_clean'] else 'DIRTY at signing' if p['working_tree_clean'] is not None else 'unknown'}",
        f"MANIFEST.sha256  sha256 {p['bound'].get('MANIFEST.sha256')}",
        f"genesis hash     {p['bound'].get('genesis.json')}",
        f"constitution     sha256 {p['bound'].get('docs/CONSTITUTION_ANCHOR.json')}",
        f"record anchors   sha256 {p['bound'].get('ops/RECORD_ANCHORS.json')}",
        f"tetsu consent    sha256 {p['bound'].get('ops/tetsu_consent.jsonl')}",
        f"model id 3B      sha256 {p['bound'].get('fallback_model.json')}",
        f"model id 2B      sha256 {p['bound'].get('fallback_model_2.json')}",
        f"model id phone   sha256 {p['bound'].get('fallback_model_phone.json')}",
        f"prev commitment  {p['prev_sha256']}",
        f"signing key fpr  {p['pubkey_fpr']}",
        "",
        "signature (base64, RSA-PSS/MGF1-SHA256/salt=MAX/SHA-256 over the",
        "length-framed canonical payload; public key in docs/HEAD_COMMIT_PUBKEY.pem):",
        row["signature"],
        "",
        "VERIFY:  python verify_head_commitment.py",
    ]
    with open(LATEST_TXT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def cmd_commit(a):
    row, keynote = make_commitment()
    _write_public(row)
    p = row["payload"]
    print(f"  {keynote}")
    print(f"  committed seq {p['seq']}  HEAD {str(p['head'])[:12]}  "
          f"tree {str(p['tree'])[:12]}")
    print(f"  bound: manifest {str(p['bound'].get('MANIFEST.sha256'))[:12]}  "
          f"genesis {str(p['bound'].get('genesis.json'))[:12]}  "
          f"constitution {str(p['bound'].get('docs/CONSTITUTION_ANCHOR.json'))[:12]}  "
          f"record-anchors {str(p['bound'].get('ops/RECORD_ANCHORS.json'))[:12]}")
    if p["working_tree_clean"] is False:
        print("  NOTE: working tree was DIRTY at signing. The commitment binds the")
        print("  COMMITTED tree (git HEAD), not your uncommitted edits.")
    print(f"  appended -> {os.path.relpath(LEDGER_PATH, HERE)}")
    print(f"  published -> docs/HEAD_COMMIT_PUBKEY.pem, docs/HEAD_COMMITMENT.(json|txt)")
    print()
    print("  TO MAKE IT INDEPENDENT OF THIS MACHINE (your call, not this tool's):")
    print("  hand docs/HEAD_COMMITMENT.txt to someone who is not you, or post its")
    print("  signature to a log you do not control (a signed git tag, a transparency")
    print("  log, an email that gets kept). Verification needs only the public key.")
    return 0


def cmd_verify(a):
    sys.path.insert(0, HERE)
    import verify_head_commitment as v
    code, lines = v.run(LEDGER_PATH, PUBKEY_PATH, HERE)
    print("\n".join(lines))
    print("\nVERDICT: " + {0: "PASS", 1: "FAIL", 2: "UNDETERMINED"}[code] + f"  (exit {code})")
    return code


def cmd_show(a):
    if not os.path.exists(LATEST_TXT):
        print("  nothing committed yet -- run: python covenant_head_commit.py commit")
        return 2
    print(open(LATEST_TXT, encoding="utf-8").read())
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("commit")
    sub.add_parser("verify")
    sub.add_parser("show")
    a = ap.parse_args()
    return {"commit": cmd_commit, "verify": cmd_verify, "show": cmd_show}.get(
        a.cmd, lambda _a: (ap.print_help() or 0))(a)


if __name__ == "__main__":
    sys.exit(main())
