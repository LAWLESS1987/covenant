#!/usr/bin/env python3
r"""
sync_holdings.py -- turn live exchange balances into holdings.txt.

WHY THIS EXISTS
  holdings.txt is the one file the whole daily loop reads, and until now it was
  maintained by hand. A hand-maintained position file goes stale silently: the
  run still prints, the percentages still add to 100%, and nothing anywhere
  says the quantities are nine days old. On 2026-08-28 exactly that had
  happened -- the file had gone missing entirely and the last copy on disk was
  from 2026-08-19, across four regime flips.

WHAT IT READS
  kraken_balance.json    written by kraken_balance.py
  coinbase_balance.json  written by coinbase_balance.py

  Both are BALANCES ONLY. This script never sees, reads, or asks for an API
  credential -- that is the whole point of the two-stage design. The scripts
  that hold the key write a balance file; this one reads the balance file.
  Both sidecars are gitignored (*_balance.json).

WHAT IT WILL NOT DO
  * It will not invent an average buy price. Neither exchange endpoint returns
    a reliable cost basis, so `avg` is carried over from the existing
    holdings.txt and a NEW asset is written with avg 0.0 and flagged loudly.
    An avg of 0 shows as +infinite P/L, which is meant to be impossible to
    miss -- a wrong cost basis that merely looks plausible is worse.
  * It will not silently overwrite. Dry-run is the default; --write applies
    and keeps a timestamped backup.
  * It will not place an order, and it holds no key.

USAGE
  python sync_holdings.py              # show the diff, change nothing
  python sync_holdings.py --write      # apply it, backing up the old file
  python sync_holdings.py --max-age 6  # refuse balance files older than 6h
"""
from __future__ import annotations
import os, sys, json, time, shutil, argparse, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
HOLDINGS = os.path.join(HERE, "holdings.txt")
SIDECARS = [os.path.join(HERE, "kraken_balance.json"),
            os.path.join(HERE, "coinbase_balance.json")]

# Assets held off-exchange, or on a venue neither reader covers. They are NOT
# deleted just because no venue reported them -- see reconcile(). CC (Canton)
# is the live example: real, held, and not tradable on either exchange.
KEEP_UNSEEN_DEFAULT = True

# Anything whose symbol normalises into this set becomes the CASH row.
CASH_CODES = {"USD", "ZUSD", "USDC", "USDT", "PYUSD", "DAI"}


# ------------------------------------------------------------------ existing
def read_holdings(path=HOLDINGS):
    """sym -> {qty, avg, manual, comment}. Preserves everything but quantity."""
    out, order = {}, []
    if not os.path.exists(path):
        return out, order
    for line in open(path, encoding="utf-8"):
        raw = line.rstrip("\n")
        body, _, comment = raw.partition("#")
        p = body.split()
        if len(p) < 3:
            continue
        sym = p[0].upper()
        try:
            rec = {"qty": float(p[1]), "avg": float(p[2]), "manual": None,
                   "comment": comment.strip() or None}
        except ValueError:
            continue
        if len(p) >= 4:
            try:
                rec["manual"] = float(p[3])
            except ValueError:
                pass
        out[sym] = rec
        order.append(sym)
    return out, order


# ------------------------------------------------------------------ sidecars
def read_sidecar(path, max_age_h):
    """Load one balance file. Returns (venue, {SYMBOL: qty}, note) or None."""
    if not os.path.exists(path):
        return None, None, (f"{os.path.basename(path)}: not present", False)
    try:
        js = json.load(open(path, encoding="utf-8"))
    except Exception as e:
        return None, None, (f"{os.path.basename(path)}: unreadable ({type(e).__name__})", True)

    venue = js.get("venue", os.path.basename(path).split("_")[0])
    gen = js.get("generated")
    age_h = None
    if gen:
        try:
            t = datetime.datetime.strptime(gen, "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=datetime.timezone.utc)
            age_h = (datetime.datetime.now(datetime.timezone.utc) - t).total_seconds() / 3600
        except Exception:
            pass
    if age_h is not None and max_age_h and age_h > max_age_h:
        return venue, None, (f"{venue}: balance file is {age_h:.1f}h old "
                             f"(limit {max_age_h}h) -- re-run its reader", True)

    # Kraken answers in legacy codes; its sidecar carries Kraken's own altname
    # table so the mapping is looked up, never guessed.
    alt = js.get("altnames") or {}
    bal = {}
    for code, amt in (js.get("balances") or {}).items():
        try:
            amt = float(amt)
        except (TypeError, ValueError):
            continue
        if amt <= 0:
            continue
        sym = (alt.get(code) or code).upper()
        if sym == "XBT":            # Kraken's name for bitcoin
            sym = "BTC"
        bal[sym] = bal.get(sym, 0.0) + amt
    note = f"{venue}: {len(bal)} asset(s)"
    if age_h is not None:
        note += f", {age_h:.1f}h old"
    return venue, bal, (note, False)


# ----------------------------------------------------------------- reconcile
def reconcile(existing, order, venue_bals, keep_unseen=KEEP_UNSEEN_DEFAULT):
    """Merge venue quantities over the existing file. Returns (rows, changes)."""
    live = {}
    for venue, bal in venue_bals.items():
        for sym, amt in bal.items():
            live.setdefault(sym, {})[venue] = amt

    cash_total = sum(a for s, per in live.items() if s in CASH_CODES
                     for a in per.values())

    rows, changes = [], []
    seen = set()

    def emit(sym, qty, rec, source):
        rows.append({"sym": sym, "qty": qty, "avg": rec.get("avg", 0.0),
                     "manual": rec.get("manual"), "comment": rec.get("comment"),
                     "source": source})

    # 1. everything already in the file, in its original order
    for sym in order:
        rec = existing[sym]
        if sym == "CASH":
            old = rec["qty"]
            emit("CASH", cash_total, {"avg": 1.0, "manual": None, "comment": None},
                 "venues" if live else "kept")
            if abs(cash_total - old) > 1e-9:
                changes.append(("CASH", old, cash_total, "venues"))
            seen.add("CASH")
            continue
        if sym in live:
            new = sum(live[sym].values())
            src = "+".join(sorted(live[sym]))
            emit(sym, new, rec, src)
            if abs(new - rec["qty"]) > 1e-9:
                changes.append((sym, rec["qty"], new, src))
            seen.add(sym)
        else:
            # Held per the file, reported by no venue. Could be off-exchange
            # (CC), could be a position that was sold. Never guessed at.
            emit(sym, rec["qty"], rec, "UNSEEN")
            seen.add(sym)

    # 2. assets a venue reports that the file has never heard of
    for sym in sorted(live):
        if sym in seen or sym in CASH_CODES:
            continue
        qty = sum(live[sym].values())
        src = "+".join(sorted(live[sym]))
        emit(sym, qty, {"avg": 0.0, "manual": None,
                        "comment": "NEW -- set your average buy price"}, src)
        changes.append((sym, 0.0, qty, src + " NEW"))

    if "CASH" not in seen:
        emit("CASH", cash_total, {"avg": 1.0, "manual": None, "comment": None},
             "venues")
    return rows, changes


def render(rows, venue_notes):
    out = ["# Your holdings. Edit the numbers when they change; nothing else.",
           "# format:  SYMBOL  QUANTITY  AVG_BUY_PRICE  [PRICE_IF_NOT_ON_COINBASE]",
           "#",
           f"# Quantities synced by sync_holdings.py at "
           f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} from:"]
    for n in venue_notes:
        out.append(f"#   {n}")
    out.append("# Average buy prices are NOT from the exchange -- they are carried")
    out.append("# over from the previous file, or 0.0 for a new asset.")
    out.append("")
    for r in rows:
        line = f"{r['sym']:<8}{r['qty']:>14.8f} {r['avg']:>12.8f}"
        if r["manual"] is not None:
            line += f" {r['manual']:>12.8f}"
        bits = []
        if r["comment"]:
            bits.append(r["comment"])
        if r["source"] == "UNSEEN":
            bits.append("not reported by any venue -- verify it is still held")
        if r["avg"] == 0.0 and r["sym"] != "CASH":
            bits.append("avg buy price unset")
        if bits:
            line += "   # " + "; ".join(bits)
        out.append(line)
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true",
                    help="apply the change (default: show it and stop)")
    ap.add_argument("--max-age", type=float, default=24.0,
                    help="refuse a balance file older than this many hours (0=off)")
    a = ap.parse_args()

    existing, order = read_holdings()
    venue_bals, notes, problems, absent = {}, [], [], []
    for path in SIDECARS:
        venue, bal, (note, hard) = read_sidecar(path, a.max_age)
        notes.append(note)
        if bal is None:
            (problems if hard else absent).append(note)
        else:
            venue_bals[venue] = bal

    print("=" * 74)
    print("SYNC HOLDINGS   " + time.strftime("%Y-%m-%d %H:%M"))
    print("=" * 74)
    for n in notes:
        print("  " + n)

    if not venue_bals:
        print("\n  No usable balance file. Nothing to sync.")
        print("  Run `python kraken_balance.py` and/or `python coinbase_balance.py`")
        print("  first -- each needs its own read-only credential, which only you")
        print("  can install. See their module docstrings.")
        return 1
    # A reader that FAILED (stale or unreadable) is different from one that is
    # simply ABSENT. Absent is a statement -- "I don't keep anything there" --
    # and reconcile() protects those positions through the UNSEEN path. Failed
    # means a venue that normally answers did not, and syncing on top of that
    # would quietly demote real positions to "unseen". Only failure stops us.
    if problems:
        print("\n  A venue reader FAILED (stale or unreadable). Syncing now would")
        print("  treat anything held only there as unseen. Refusing.")
        for p in problems:
            print("    ! " + p)
        print("\n  Re-run that venue's reader, then try again.")
        return 2
    if absent:
        print("\n  note: a venue file is simply absent. Positions held only there")
        print("  are KEPT and listed below as unseen -- never zeroed.")
        for n in absent:
            print("    - " + n)

    rows, changes = reconcile(existing, order, venue_bals)

    print("\n  CHANGES")
    print("  " + "-" * 70)
    if not changes:
        print("  (none -- holdings.txt already matches the venues)")
    for sym, old, new, src in changes:
        tag = "NEW" if src.endswith("NEW") else ""
        print(f"  {sym:<8} {old:>16,.8f} -> {new:>16,.8f}   [{src}] {tag}")

    unseen = [r["sym"] for r in rows if r["source"] == "UNSEEN"]
    if unseen:
        print("\n  HELD PER FILE, REPORTED BY NO VENUE (kept, not deleted):")
        for s in unseen:
            print(f"    {s}  -- off-exchange, or sold and not yet removed. Yours to check.")
    noavg = [r["sym"] for r in rows if r["avg"] == 0.0 and r["sym"] != "CASH"]
    if noavg:
        print("\n  NO AVERAGE BUY PRICE (P/L will read as nonsense until you set it):")
        for s in noavg:
            print(f"    {s}")

    text = render(rows, [n for n in notes if n])
    if not a.write:
        print("\n  DRY RUN -- nothing written. Re-run with --write to apply.")
        return 0

    if os.path.exists(HOLDINGS):
        bak = HOLDINGS + time.strftime(".%Y%m%d-%H%M%S.bak")
        shutil.copy2(HOLDINGS, bak)
        print(f"\n  backed up -> {os.path.basename(bak)}")
    open(HOLDINGS, "w", encoding="utf-8", newline="\n").write(text)
    print(f"  written    -> holdings.txt")
    print("\n  Now run:  python daily.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
