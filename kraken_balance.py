#!/usr/bin/env python3
"""
kraken_balance.py -- read your Kraken balance LOCALLY and write a shareable
summary. Your API key never leaves your machine.

THE DESIGN RULE THAT MATTERS
  The key is read from a file OUTSIDE the Claude-connected folder. This script
  writes ONLY balances -- never the key, never the secret -- into the folder.
  So Claude sees what you hold; Claude never sees the credential that reads it.

SETUP (5 minutes)
  1. Kraken -> Settings -> API -> Add key
     Permissions: tick ONLY "Query Funds".
     Leave Trade, Withdraw, and Staking UNTICKED. A funds-query key cannot move
     a single coin even if it leaks.
  2. Save it OUTSIDE this folder, at:
        %USERPROFILE%\.kraken\credentials
     as two lines:
        key=YOUR_API_KEY
        secret=YOUR_PRIVATE_KEY
  3. Run:  python kraken_balance.py

It refuses to run if it finds the credential file inside the synced folder.
"""
from __future__ import annotations
import os, sys, time, json, base64, hashlib, hmac, urllib.request, urllib.parse, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "kraken_balance.txt")
CRED = os.path.join(os.path.expanduser("~"), ".kraken", "credentials")


def load_creds(path=CRED):
    # Refuse to read a credential that lives inside the shared folder.
    real_cred, real_here = os.path.realpath(path), os.path.realpath(HERE)
    if real_cred.startswith(real_here + os.sep):
        sys.exit(f"REFUSING: {path} is inside the Claude-connected folder.\n"
                 f"That folder syncs to the cloud. Move it to {CRED} instead.")
    if not os.path.exists(path):
        sys.exit(f"No credential file at {path}\n\n"
                 f"Create it with EXACTLY two lines:\n"
                 f"  key=YOUR_API_KEY\n  secret=YOUR_PRIVATE_KEY\n\n"
                 f"On Kraken, give the key ONLY the 'Query Funds' permission.")
    k = s = ""
    for line in open(path):
        line = line.strip()
        if line.startswith("key="):
            k = line[4:].strip()
        elif line.startswith("secret="):
            s = line[7:].strip()
    if not k or not s:
        sys.exit(f"{path} must contain key= and secret= lines.")
    return k, s


def kraken_private(endpoint: str, key: str, secret: str, data=None):
    """Signed POST to Kraken's private API (runs on YOUR machine only)."""
    path = f"/0/private/{endpoint}"
    data = dict(data or {})
    data["nonce"] = str(int(time.time() * 1000))
    post = urllib.parse.urlencode(data)
    sha = hashlib.sha256((data["nonce"] + post).encode()).digest()
    try:
        sig = hmac.new(base64.b64decode(secret), path.encode() + sha,
                       hashlib.sha512).digest()
    except Exception:
        sys.exit("The 'secret' does not look like a valid Kraken private key "
                 "(it should be a long base64 string).")
    req = urllib.request.Request(
        "https://api.kraken.com" + path, data=post.encode(), method="POST",
        headers={"API-Key": key, "API-Sign": base64.b64encode(sig).decode(),
                 "User-Agent": "covenant-balance/1.0",
                 "Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            body = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        sys.exit(f"Kraken HTTP {e.code}: {e.reason}")
    except Exception as e:
        sys.exit(f"Could not reach Kraken: {type(e).__name__}: {e}")
    if body.get("error"):
        errs = "; ".join(body["error"])
        hint = ""
        if "Permission denied" in errs:
            hint = "\n  -> the key lacks 'Query Funds' permission."
        if "Invalid key" in errs or "Invalid signature" in errs:
            hint = "\n  -> key or secret copied incorrectly (watch for spaces)."
        sys.exit(f"Kraken error: {errs}{hint}")
    return body.get("result", {})


def public_prices(assets):
    """Public ticker -- no auth needed."""
    pairs = {a: f"{a}USD" for a in assets if a not in ("ZUSD", "USD")}
    if not pairs:
        return {}
    url = "https://api.kraken.com/0/public/Ticker?pair=" + ",".join(pairs.values())
    try:
        with urllib.request.urlopen(url, timeout=25) as r:
            res = json.loads(r.read().decode()).get("result", {})
    except Exception:
        return {}
    out = {}
    for a, p in pairs.items():
        for k, v in res.items():
            if p in k or k.endswith("USD") and a in k:
                try:
                    out[a] = float(v["c"][0])
                except Exception:
                    pass
                break
    return out


def main():
    key, secret = load_creds()
    print("reading balance from Kraken (locally)...")
    bal = kraken_private("Balance", key, secret)
    holdings = {a: float(v) for a, v in bal.items() if float(v) > 0}
    if not holdings:
        print("No non-zero balances found.")
        return
    px = public_prices(list(holdings))

    lines = ["KRAKEN BALANCE  " + time.strftime("%Y-%m-%d %H:%M"),
             "(generated locally; no API key is included in this file)", "",
             f"  {'asset':<10}{'amount':>18}{'price':>12}{'value USD':>14}",
             "  " + "-" * 52]
    total = 0.0
    rows = []
    for a, amt in holdings.items():
        p = 1.0 if a in ("ZUSD", "USD") else px.get(a)
        val = amt * p if p else None
        if val:
            total += val
        rows.append((a, amt, p, val))
    for a, amt, p, val in sorted(rows, key=lambda r: -(r[3] or 0)):
        ps = f"{p:,.4f}" if p else "n/a"
        vs = f"{val:,.2f}" if val else "n/a"
        lines.append(f"  {a:<10}{amt:>18,.8f}{ps:>12}{vs:>14}")
    lines += ["  " + "-" * 52, f"  {'TOTAL':<10}{'':>18}{'':>12}{total:>13,.2f}", ""]
    if total > 0:
        lines.append("  concentration:")
        for a, amt, p, val in sorted(rows, key=lambda r: -(r[3] or 0)):
            if val:
                lines.append(f"    {a:<10}{val/total:>6.1%}")
    text = "\n".join(lines)
    print("\n" + text)
    open(OUT, "w", encoding="utf-8").write(text)
    print(f"\nwritten to {os.path.basename(OUT)} -- Claude can read this.")
    print("Your API key stayed in", CRED)


if __name__ == "__main__":
    main()
