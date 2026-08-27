#!/usr/bin/env python3
"""
covenant_client.py -- operate a running Covenant node from the command line.

A node accepts transactions only if they carry a registration proof-of-work and
a valid RSA signature, and /mine is operator-authenticated. That is more than a
plain HTTP POST can express, which is why this client exists. It signs with a
node's own identity key file (`<db>.key`), so the node can drive itself.

Cross-platform (Windows / macOS / Linux). Run it from the covenant folder with
the same venv you launched the node in.

EXAMPLES
  # print a node's own public key (its account on the ledger)
  python covenant_client.py --key covenant_A.db.key pubkey

  # read a balance (pass a .key file to use its owner's pubkey)
  python covenant_client.py --port 5000 balance --of-key covenant_A.db.key

  # send 25 from A to B, then mine it into a block
  python covenant_client.py --port 5000 --key covenant_A.db.key send --to-key covenant_B.db.key --amount 25
  python covenant_client.py --port 5000 --key covenant_A.db.key mine

  # watch the whole network agree on one tip
  python covenant_client.py status --ports 5000,5020,5040
"""
from __future__ import annotations
import argparse, json, os, sys, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_unified_v8 as cov
from cryptography.hazmat.primitives import serialization


def load_key(path):
    if not os.path.exists(path):
        sys.exit(f"key file not found: {path}\n"
                 f"(it is created as <db>.key the first time you launch that node)")
    with open(path, "rb") as fh:
        return serialization.load_pem_private_key(fh.read(), password=None)


def pub_of_key(path) -> str:
    return load_key(path).public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo).decode()


def http(method, port, path, body=None, headers=None, timeout=20):
    url = f"http://127.0.0.1:{port}{path}"
    data = json.dumps(body).encode() if body is not None else None
    h = {"Content-Type": "application/json"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {"error": str(e)}
    except urllib.error.URLError as e:
        sys.exit(f"could not reach a node on port {port}: {e}\n"
                 f"(is the node running? did you use the right --port?)")


def cmd_pubkey(args):
    print(pub_of_key(args.key))


def cmd_balance(args):
    # There is no /balance HTTP route; balances live in the node's ledger DB,
    # which is what the node itself reads. Point --db at the node's db file.
    pub = pub_of_key(args.of_key) if args.of_key else _require(args.pub, "--of-key or --pub")
    db_path = _require(args.db, "--db (the node's db file, e.g. covenant_A.db)")
    if not os.path.exists(db_path):
        sys.exit(f"db file not found: {db_path}")
    db = cov.Database(db_path)
    print(f"balance: {db.get_balance(pub)}")


def cmd_send(args):
    sk = load_key(args.key)
    pem = sk.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    receiver = pub_of_key(args.to_key) if args.to_key else _require(args.to_pub, "--to-key or --to-pub")
    reg = cov.RegistrationPoW.generate(pem, cov.BASE_REGISTRATION_DIFFICULTY)
    tx = cov.Transaction(sender_pubkey=pem, receiver=receiver,
                         data={"origin": "human"}, amount=float(args.amount),
                         benefit_score=float(args.benefit), reg_nonce=reg)
    tx.sign(sk)
    body = {"sender_pubkey": pem, "receiver": receiver, "data": {"origin": "human"},
            "amount": float(args.amount), "timestamp": tx.timestamp,
            "benefit_score": float(args.benefit), "signature": tx.signature,
            "reg_nonce": reg}
    # long timeout: with the Claude file-judge gate the node may wait for a
    # verdict before admitting; don't give up before the judge does.
    st, resp = http("POST", args.port, "/transactions", body, timeout=310)
    print(f"HTTP {st}: {json.dumps(resp)[:200]}")
    if st != 200:
        sys.exit(1)


def cmd_mine(args):
    sk = load_key(args.key)
    pem = sk.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    raw = b"{}"
    hdrs = cov.sign_operator_request(sk, pem, "POST", "/mine", raw)
    # mining re-judges each transaction in the block, so it can also wait on the
    # Claude file-judge gate -- give it the same long timeout as send.
    st, resp = http("POST", args.port, "/mine", body={}, headers=hdrs, timeout=310)
    print(f"HTTP {st}: {json.dumps(resp)[:200]}")
    if st != 200:
        sys.exit(1)


def cmd_status(args):
    ports = [int(p) for p in str(args.ports).split(",") if p.strip()]
    tips = {}
    for p in ports:
        st, ch = http("GET", p, "/chain")
        c = ch.get("chain", ch if isinstance(ch, list) else [])
        tip = c[-1]["hash"] if c else ""
        tips[p] = tip
        print(f"  port {p}: height={len(c)} tip={tip[:16]}")
    agree = len(set(tips.values())) == 1 and all(tips.values())
    print(f"\n  converged on one tip: {agree}")
    if not agree:
        sys.exit(2)


def _require(val, what):
    if not val:
        sys.exit(f"missing required argument: {what}")
    return val


# --- argument-order forgiveness -------------------------------------------
# --port and --key belong to the TOP-LEVEL parser, so argparse only accepts
# them before the subcommand. The natural way to type it --
#     covenant_client.py mine --port 5001 --key A.db.key
# -- died with "unrecognized arguments", which reads as "this tool is broken"
# rather than "you typed it in the wrong order". It silently ate five mining
# attempts in a row during the node survival test before the cause was clear.
# Rather than duplicate the flags (which makes one copy shadow the other with
# a None default), just move them to the front before parsing.
_GLOBAL_FLAGS = ("--port", "--key")

def _hoist_global_flags(argv):
    front, rest, i = [], [], 0
    while i < len(argv):
        a = argv[i]
        if a in _GLOBAL_FLAGS and i + 1 < len(argv):
            front += [a, argv[i + 1]]; i += 2; continue
        if any(a.startswith(f + "=") for f in _GLOBAL_FLAGS):
            front.append(a); i += 1; continue
        rest.append(a); i += 1
    return front + rest


def main():
    ap = argparse.ArgumentParser(description="Operate a running Covenant node.")
    ap.add_argument("--port", type=int, default=5000, help="node HTTP port (default 5000)")
    ap.add_argument("--key", help="path to the signer's identity key, e.g. covenant_A.db.key")

    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("pubkey", help="print the signer's public key")

    b = sub.add_parser("balance", help="read a ledger balance from a node's db")
    b.add_argument("--db", help="the node's db file, e.g. covenant_A.db")
    b.add_argument("--of-key", help="a .key file whose owner's balance to read")
    b.add_argument("--pub", help="a PEM public-key string instead of --of-key")

    s = sub.add_parser("send", help="sign and submit a transaction")
    s.add_argument("--to-key", help="recipient's .key file (its pubkey is the destination)")
    s.add_argument("--to-pub", help="recipient PEM public key instead of --to-key")
    s.add_argument("--amount", required=True, type=float)
    s.add_argument("--benefit", type=float, default=0.5, help="benefit_score 0..1 (default 0.5)")

    sub.add_parser("mine", help="operator-authenticated /mine on this node")

    st = sub.add_parser("status", help="compare tip hashes across nodes")
    st.add_argument("--ports", default="5000", help="comma-separated ports, e.g. 5000,5020,5040")

    args = ap.parse_args(_hoist_global_flags(sys.argv[1:]))
    if args.cmd in ("pubkey", "send", "mine") and not args.key:
        sys.exit("this command needs --key <path to a .key file>")
    {"pubkey": cmd_pubkey, "balance": cmd_balance, "send": cmd_send,
     "mine": cmd_mine, "status": cmd_status}[args.cmd](args)


if __name__ == "__main__":
    main()
