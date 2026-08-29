#!/usr/bin/env python3
"""
coinbase_balance.py -- read your Coinbase balance LOCALLY and write a shareable
summary. Your API key never leaves your machine.

The mirror of kraken_balance.py, and it keeps that file's rule verbatim:

THE DESIGN RULE THAT MATTERS
  The key is read from a file OUTSIDE the Claude-connected folder. This script
  writes ONLY balances -- never the key, never the secret -- into the folder.
  So Claude sees what you hold; Claude never sees the credential that reads it.

WHY THIS EXISTS AT ALL. daily.py already fetches Coinbase PRICES with no key,
and cross-checks them against Kraken, because "every internal check can pass on
a series that is simply wrong -- the 70-day-stale window was internally
perfect". That argument is about prices and it is exactly as true of HOLDINGS.
One venue reporting what you own is one venue's word for it.

COINBASE HAS THREE APIs AND THEY DO NOT SHARE AN AUTH SCHEME. Guessing wrong
costs you a support page and twenty minutes, so this DETECTS which credential
you saved rather than making you know in advance:

  Advanced Trade / CDP   an ES256-signed JWT from a downloaded key file.
                         Credential has  name=  and  privateKey=  (or you saved
                         the whole cdp_api_key.json).       <- most likely today
  Exchange               HMAC with THREE values: key, secret, passphrase.
  Retail v2              legacy key/secret. Being retired; supported here only
                         because an old key may still work.

SETUP (5 minutes)
  1. Coinbase -> Settings -> API (or portal.cdp.coinbase.com for CDP).
     Permissions: tick ONLY the READ / "View" scope.
     Leave Trade, Transfer and Withdraw UNTICKED. A view-only key cannot move
     a single coin even if it leaks.
  2. Save it OUTSIDE this folder, at:
        %USERPROFILE%\\.coinbase\\credentials
     CDP -- two lines, the privateKey exactly as downloaded including the
     -----BEGIN EC PRIVATE KEY----- header, with \\n left as literal \\n:
        name=organizations/xxx/apiKeys/yyy
        privateKey=-----BEGIN EC PRIVATE KEY-----\\nMHc...\\n-----END EC PRIVATE KEY-----\\n
     Exchange -- three lines:
        key=YOUR_API_KEY
        secret=YOUR_BASE64_SECRET
        passphrase=YOUR_PASSPHRASE
     (Or just drop the downloaded cdp_api_key.json in that folder.)
  3. Run:  python coinbase_balance.py

It refuses to run if it finds the credential file inside the synced folder.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "coinbase_balance.txt")
CRED_DIR = os.environ.get("COINBASE_CRED_DIR",
                         os.path.join(os.path.expanduser("~"), ".coinbase"))
CRED = os.path.join(CRED_DIR, "credentials")
CRED_JSON = os.path.join(CRED_DIR, "cdp_api_key.json")


def _refuse_if_inside(path):
    """The one check that makes the whole design true rather than intended.

    If the credential is inside the Claude-connected folder it syncs, and every
    sentence in this docstring about the key never leaving the machine becomes
    false. Checked against the RESOLVED path, so a symlink or a junction
    pointing back in does not slip past."""
    real_cred, real_here = os.path.realpath(path), os.path.realpath(HERE)
    if not (real_cred == real_here or real_cred.startswith(real_here + os.sep)):
        return
    # "Move it to X" where X is the path being refused is not advice, and the
    # message was capable of printing exactly that -- caught by running the
    # refusal rather than reading it. kraken_balance.py has the same shape.
    # If the suggested destination is ALSO inside the folder, the home
    # directory itself is the problem and saying so is the only useful thing.
    real_dest = os.path.realpath(CRED)
    if real_dest == real_here or real_dest.startswith(real_here + os.sep):
        sys.exit(f"REFUSING: {path} is inside the Claude-connected folder,\n"
                 f"and so is your home directory ({os.path.expanduser('~')}).\n\n"
                 f"There is nowhere safe to put this credential under a synced\n"
                 f"home. Put it somewhere outside {real_here} and point at it\n"
                 f"with COINBASE_CRED_DIR.")
    sys.exit(f"REFUSING: {path} is inside the Claude-connected folder.\n"
             f"That folder syncs to the cloud. Move it to {CRED} instead.")


def load_creds():
    """Whichever of the three Coinbase credential shapes is present.

    Returns (scheme, dict). Never returns the values anywhere they can be
    printed: every caller below uses them and nothing logs them."""
    for p in (CRED, CRED_JSON):
        _refuse_if_inside(p)

    if os.path.exists(CRED_JSON):
        try:
            j = json.load(open(CRED_JSON, encoding="utf-8"))
        except Exception as e:
            sys.exit(f"{CRED_JSON} is not readable JSON: {e}")
        name = j.get("name") or j.get("id") or ""
        pk = j.get("privateKey") or j.get("private_key") or ""
        if name and pk:
            return "cdp", {"name": name, "privateKey": pk}
        sys.exit(f"{CRED_JSON} has no name/privateKey pair -- keys present: "
                 f"{sorted(j)[:6]}. That is not a CDP key file.")

    if not os.path.exists(CRED):
        sys.exit(
            f"No credential file at {CRED}\n\n"
            f"Create it, or drop the downloaded cdp_api_key.json in\n"
            f"  {CRED_DIR}\n\n"
            f"CDP / Advanced Trade -- two lines:\n"
            f"  name=organizations/.../apiKeys/...\n"
            f"  privateKey=-----BEGIN EC PRIVATE KEY-----\\n...\\n-----END EC PRIVATE KEY-----\\n\n\n"
            f"Exchange -- three lines:\n"
            f"  key=YOUR_API_KEY\n  secret=YOUR_BASE64_SECRET\n  passphrase=YOUR_PASSPHRASE\n\n"
            f"On Coinbase, give the key ONLY the READ / 'View' scope.")

    got = {}
    for line in open(CRED, encoding="utf-8"):
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            got[k.strip()] = v.strip()

    if got.get("name") and got.get("privateKey"):
        return "cdp", got
    if got.get("key") and got.get("secret") and got.get("passphrase"):
        return "exchange", got
    if got.get("key") and got.get("secret"):
        # AMBIGUOUS, and the likelier reading is the one that is fixable.
        # key+secret with no passphrase is either a retail v2 key or -- far more
        # often -- an Exchange key whose passphrase was not saved. Say both.
        sys.exit(
            f"{CRED} has key= and secret= but no passphrase=.\n\n"
            f"That is one of two things:\n"
            f"  1. an EXCHANGE key missing its passphrase. The passphrase is set\n"
            f"     when the key is created and cannot be recovered -- create a\n"
            f"     new key and save all three lines.\n"
            f"  2. a legacy RETAIL v2 key. This script will not use those:\n"
            f"     Coinbase is retiring the API and the keys carry broader scopes\n"
            f"     than 'read balances', which is the opposite of the point here.\n\n"
            f"Either way the answer is a new key with the READ / View scope only.\n"
            f"For CDP: portal.cdp.coinbase.com, then save name= and privateKey=.")
    sys.exit(
        f"{CRED} does not match any Coinbase credential shape.\n"
        f"Found key names: {sorted(got) or '(none)'}\n\n"
        f"  CDP       needs  name=  and  privateKey=\n"
        f"  Exchange  needs  key=, secret=  AND  passphrase=\n"
        f"  Retail    needs  key=  and  secret=\n\n"
        f"An Exchange key without its passphrase is the usual near-miss: the\n"
        f"passphrase is set when the key is created and cannot be recovered.")


# ------------------------------------------------------------------ CDP (JWT)
def _b64u(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def cdp_jwt(name, private_key_pem, method, host, path):
    """An ES256 JWT, built with `cryptography` alone.

    No PyJWT dependency: the node already requires `cryptography` and adding a
    second crypto library to read a balance is a dependency nobody audited.
    Coinbase wants the raw r||s form, not the DER that `sign()` returns."""
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import ec, utils
    except ImportError:
        sys.exit("this needs the `cryptography` package: pip install cryptography")

    pem = private_key_pem.replace("\\n", "\n").encode()
    try:
        key = serialization.load_pem_private_key(pem, password=None)
    except Exception as e:
        sys.exit(f"privateKey did not load as a PEM EC key ({type(e).__name__}).\n"
                 f"Paste it exactly as downloaded, with the BEGIN/END lines and\n"
                 f"the newlines left as literal \\n.")

    now = int(time.time())
    hdr = {"alg": "ES256", "kid": name, "typ": "JWT",
           "nonce": secrets.token_hex(16)}
    pay = {"sub": name, "iss": "cdp", "nbf": now, "exp": now + 120,
           "uri": f"{method} {host}{path}"}
    signing_input = f"{_b64u(json.dumps(hdr).encode())}.{_b64u(json.dumps(pay).encode())}"
    der = key.sign(signing_input.encode(), ec.ECDSA(hashes.SHA256()))
    r, s = utils.decode_dss_signature(der)
    raw = r.to_bytes(32, "big") + s.to_bytes(32, "big")
    return f"{signing_input}.{_b64u(raw)}"


def fetch_cdp(cred):
    host, path = "api.coinbase.com", "/api/v3/brokerage/accounts"
    tok = cdp_jwt(cred["name"], cred["privateKey"], "GET", host, path)
    req = urllib.request.Request(f"https://{host}{path}",
                                 headers={"Authorization": f"Bearer {tok}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        js = json.loads(r.read().decode())
    out = {}
    for a in js.get("accounts", []):
        bal = a.get("available_balance") or {}
        v = float(bal.get("value") or 0)
        h = float((a.get("hold") or {}).get("value") or 0)
        if v + h > 0:
            out[bal.get("currency") or a.get("currency", "?")] = v + h
    return out


# ------------------------------------------------------------- Exchange (HMAC)
def fetch_exchange(cred):
    host, path = "api.exchange.coinbase.com", "/accounts"
    ts = str(time.time())
    msg = (ts + "GET" + path).encode()
    try:
        sec = base64.b64decode(cred["secret"])
    except Exception:
        sys.exit("secret= is not valid base64. Copy it exactly as Coinbase showed it.")
    sig = base64.b64encode(hmac.new(sec, msg, hashlib.sha256).digest()).decode()
    req = urllib.request.Request(f"https://{host}{path}", headers={
        "CB-ACCESS-KEY": cred["key"], "CB-ACCESS-SIGN": sig,
        "CB-ACCESS-TIMESTAMP": ts, "CB-ACCESS-PASSPHRASE": cred["passphrase"],
        "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        js = json.loads(r.read().decode())
    out = {}
    for a in js:
        total = float(a.get("balance") or 0)
        if total > 0:
            out[a.get("currency", "?")] = total
    return out


def fetch_retail(cred):
    sys.exit(
        "A retail v2 key/secret was found and this script will not use it.\n"
        "Coinbase is retiring that API and its keys carry broader scopes than\n"
        "'read balances' -- which is the opposite of the point here. Create a\n"
        "CDP key at portal.cdp.coinbase.com with the View scope only, save it\n"
        f"at {CRED}, and delete the old one from your Coinbase settings.")


def main():
    scheme, cred = load_creds()
    fetch = {"cdp": fetch_cdp, "exchange": fetch_exchange,
             "retail": fetch_retail}[scheme]
    try:
        bal = fetch(cred)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:300]
        hint = ""
        if e.code in (401, 403):
            hint = ("\nThat is an auth failure, not a network one. Usual causes:\n"
                    "  * the key has no READ/View scope\n"
                    "  * an Exchange key used against the CDP endpoint, or vice versa\n"
                    "  * the machine clock is off -- both schemes sign a timestamp\n"
                    "NOTE: the response body is printed above and may name the key.\n"
                    "It never contains the SECRET.")
        sys.exit(f"Coinbase returned HTTP {e.code}: {body}{hint}")
    except urllib.error.URLError as e:
        sys.exit(f"could not reach Coinbase: {e.reason}")

    lines = [f"# coinbase_balance.txt -- written {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}",
             f"# auth scheme: {scheme}   (credential read from {CRED_DIR}, never copied here)",
             f"# balances only. No key, no secret, no account id.",
             ""]
    if not bal:
        lines.append("(no non-zero balances)")
    for sym in sorted(bal, key=lambda k: -bal[k]):
        lines.append(f"{sym:<10} {bal[sym]:.8f}".rstrip("0").rstrip("."))
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nwritten to {OUT}")
    # Machine-readable sidecar -- see the note in kraken_balance.py. Balances
    # only; the credential is not in scope here and is never copied out.
    json.dump({"venue": "coinbase", "scheme": scheme,
               "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "balances": bal},
              open(os.path.splitext(OUT)[0] + ".json", "w", encoding="utf-8"), indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
