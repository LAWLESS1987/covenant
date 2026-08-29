#!/usr/bin/env python3
r"""
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


def _usd_pair_map():
    """asset code -> its USD pair name, from Kraken's OWN pair table.

    M-fix (2026-08-28): this used to be guessed as f"{asset}USD", which is
    wrong for every legacy asset. Kraken's private Balance endpoint answers in
    legacy codes -- XXLM, XXRP, XXBT, ZUSD -- and the USD pair for XXLM is
    XXLMZUSD, not XXLMUSD. Measured: "XXLMUSD" -> EQuery:Unknown asset pair.
    AssetPairs is keyed on the same legacy codes Balance returns, so looking
    the pair up removes the guess entirely rather than patching it.
    """
    url = "https://api.kraken.com/0/public/AssetPairs"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "covenant-balance/1.0"})
        with urllib.request.urlopen(req, timeout=25) as r:
            res = json.loads(r.read().decode()).get("result", {})
    except Exception:
        return {}
    out = {}
    for name, v in res.items():
        if v.get("quote") not in ("ZUSD", "USD") or v.get("status") != "online":
            continue
        base = v.get("base")
        # Several pair names can share a base; keep the shortest, which is the
        # canonical one Kraken echoes back in a Ticker result.
        if base and (base not in out or len(name) < len(out[base])):
            out[base] = name
    return out


def _altnames():
    """Kraken code -> the symbol a human uses: XXLM->XLM, ZUSD->USD, XXBT->XBT.

    Taken from Kraken's own Assets table rather than derived by stripping a
    leading X/Z. That heuristic is wrong for exactly the assets it looks
    right for -- there are 837 assets and the legacy prefix is not a rule.
    Emitted into the JSON sidecar so sync_holdings.py needs no network.
    """
    try:
        req = urllib.request.Request("https://api.kraken.com/0/public/Assets",
                                     headers={"User-Agent": "covenant-balance/1.0"})
        with urllib.request.urlopen(req, timeout=25) as r:
            res = json.loads(r.read().decode()).get("result", {})
    except Exception:
        return {}
    return {c: v.get("altname") for c, v in res.items() if v.get("altname")}


def spot_asset(a):
    """Strip Kraken's staking/earn suffix: SOL.S, XXBT.M, ADA.F -> SOL, XXBT, ADA.

    A staked coin is the same exposure as an unstaked one. Leaving them as
    separate rows would halve each one's apparent share of the portfolio, and
    the 20% concentration cap is computed from exactly that share -- so the
    split would silently under-report a breach of the rule that matters most.
    """
    return a.split(".")[0]


def public_prices(assets):
    """asset code -> USD price. Public ticker, no auth needed.

    Queries the batch, then falls back to one request per pair if the batch
    fails. That fallback is not defensive padding: Kraken rejects the WHOLE
    query if a single pair in it is unknown (measured -- 'good,bad' returns
    EQuery:Unknown asset pair and an empty result), so one unrecognised coin
    in the account would otherwise zero out the price of every other coin.
    """
    pairmap = _usd_pair_map()
    want = {}                                   # pair name -> [asset codes]
    for a in assets:
        s = spot_asset(a)
        if s in ("ZUSD", "USD"):
            continue
        p = pairmap.get(s)
        if p:
            want.setdefault(p, []).append(a)
    if not want:
        return {}

    def _ticker(pairs):
        url = ("https://api.kraken.com/0/public/Ticker?pair=" + ",".join(pairs))
        req = urllib.request.Request(url, headers={"User-Agent": "covenant-balance/1.0"})
        with urllib.request.urlopen(req, timeout=25) as r:
            body = json.loads(r.read().decode())
        if body.get("error"):
            raise ValueError("; ".join(body["error"]))
        return body.get("result", {})

    res = {}
    try:
        res = _ticker(list(want))
    except Exception:
        for p in want:                          # one bad pair must not sink the rest
            try:
                res.update(_ticker([p]))
            except Exception:
                pass

    out = {}
    for pair, codes in want.items():
        v = res.get(pair)
        if not v:
            continue
        try:
            px = float(v["c"][0])
        except Exception:
            continue
        for a in codes:
            out[a] = px
    return out


def main():
    key, secret = load_creds()
    print("reading balance from Kraken (locally)...")
    bal = kraken_private("Balance", key, secret)
    # Aggregate staking/earn variants into their spot asset (SOL + SOL.S).
    # See spot_asset(): held apart, each row shows half the true position
    # and a breach of the 20% concentration cap can pass unnoticed.
    holdings, staked = {}, {}
    for _a, _v in bal.items():
        _amt = float(_v)
        if _amt <= 0:
            continue
        _s = spot_asset(_a)
        holdings[_s] = holdings.get(_s, 0.0) + _amt
        if _s != _a:
            staked[_s] = staked.get(_s, 0.0) + _amt
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
    if staked:
        lines.append("  staked/earn included in the rows above:")
        for _s in sorted(staked):
            lines.append(f"    {_s:<10}{staked[_s]:>18,.8f}")
        lines.append("")
    if total > 0:
        lines.append("  concentration:")
        for a, amt, p, val in sorted(rows, key=lambda r: -(r[3] or 0)):
            if val:
                lines.append(f"    {a:<10}{val/total:>6.1%}")
    text = "\n".join(lines)
    print("\n" + text)
    open(OUT, "w", encoding="utf-8").write(text)
    # Machine-readable sidecar. The table above is for a human; sync_holdings.py
    # must not have to parse thousands separators out of a fixed-width column.
    # Balances only -- same contents as the table, no key, no secret, no
    # account id. Gitignored as *_balance.json for the same reason as the .txt.
    json.dump({"venue": "kraken", "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "balances": {a: amt for a, amt, _p, _v in rows},
               "staked": staked,
               "altnames": _altnames()},
              open(os.path.splitext(OUT)[0] + ".json", "w", encoding="utf-8"), indent=2)
    print(f"\nwritten to {os.path.basename(OUT)} -- Claude can read this.")
    print("Your API key stayed in", CRED)


if __name__ == "__main__":
    main()
