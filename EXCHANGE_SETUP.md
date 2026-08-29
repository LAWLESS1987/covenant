# Wiring Kraken and Coinbase into the daily loop

Written 2026-08-28. Replaces the setup notes that lived in `kraken/`, a folder
that was never committed to git and is no longer on disk.

---

## The shape of it

There are two halves, and they are deliberately kept apart.

```
  [ your API key ]                    lives in %USERPROFILE%\.kraken\
         |                                     %USERPROFILE%\.coinbase\
         v                                     -- NEVER inside covenant\
  kraken_balance.py  ---> kraken_balance.json    \
  coinbase_balance.py -> coinbase_balance.json    |  balances only.
         |                                        |  no key, no secret,
         v                                        /  no account id.
  sync_holdings.py   ---> holdings.txt
         |
         v
  daily.py           ---> prices, regime lines, rule check
```

Only the two `*_balance.py` scripts ever touch a credential. Everything
downstream reads balance files. Both scripts **refuse to run** if they find the
credential file inside `covenant\` — that folder syncs to the cloud, and the
check is in the code, not just in this document.

`daily.py` needs **no credential at all**. Prices are public on both venues.

---

## 1. Create the two keys — read-only, and only you can do this

Claude will not create, type, or paste an API key. Do these yourself.

### Kraken

1. Kraken → Settings → API → Add key
2. Tick **only "Query Funds"**. Leave Trade, Withdraw and Staking unticked.
   A funds-query key cannot move a coin even if it leaks.
3. Save as **exactly two lines** at `%USERPROFILE%\.kraken\credentials`:

   ```
   key=YOUR_API_KEY
   secret=YOUR_PRIVATE_KEY
   ```

### Coinbase

1. `portal.cdp.coinbase.com` → create a key with **only the READ / "View"** scope.
2. Either drop the downloaded `cdp_api_key.json` straight into
   `%USERPROFILE%\.coinbase\`, or save `%USERPROFILE%\.coinbase\credentials` with
   `name=` and `privateKey=` lines.

A legacy retail v2 key is **refused on purpose** — those carry broader scopes
than "read balances", which is the opposite of the point.

---

## 2. Run it

```bash
python kraken_balance.py
```

```bash
python coinbase_balance.py
```

Each prints your balances and writes two files next to itself: a human table
(`*_balance.txt`) and a machine-readable sidecar (`*_balance.json`). Both are
gitignored — they are holdings, and holdings are not published.

Then bring them into the position file. **Dry run first** — this is the default,
and it changes nothing:

```bash
python sync_holdings.py
```

Read the diff. If it is right:

```bash
python sync_holdings.py --write
```

It backs up the previous `holdings.txt` with a timestamp before writing. Then:

```bash
python daily.py
```

---

## 3. What the sync will and will not do

**It will not invent an average buy price.** Neither exchange endpoint returns a
trustworthy cost basis, so `avg` is carried over from your existing file. A
genuinely new asset is written with `avg 0.0` and flagged. That reads as a
nonsense P/L on purpose — a cost basis that is wrong but *plausible* is worse
than one that is obviously unset.

**It will not delete a position just because no venue reported it.** Anything in
`holdings.txt` that neither venue returns is kept and listed as *unseen*. `CC`
(Canton) is the live example: real, held, and on neither exchange feed. A sold
position also shows up this way, so the list is yours to check — the script will
not guess which it is.

**It will refuse a partial sync.** If a balance file is stale (older than
`--max-age`, default 24h) or unreadable, the run stops rather than treating
positions at that venue as unseen. A file that is simply *absent* is different —
that is you saying you keep nothing there, and it proceeds with a note.

**It holds no key and places no order.**

---

## 4. Two things to know about pricing

**A hand-entered price outranks a fetched one.** If `holdings.txt` has a 4th
column for a symbol, that price is used even when a venue quotes the ticker, and
the run prints both plus the gap. `CC` is a three-character ticker that more than
one asset can own; valuing the wrong asset on a ticker match alone is not a risk
worth taking silently. If you confirm they are the same asset, delete column 4
and it will price live and gain a 200-day regime line.

**Symbols outside the hardcoded maps now resolve.** `CB` and `KR` in `daily.py`
name the nine assets held on 2026-08-19. Since `sync_holdings.py` can add an
asset without anyone opening `daily.py`, both fetchers now fall back to looking
the symbol up at the venue. The hardcoded maps remain the fast, audited path.
Kraken calls bitcoin `XBT` and dogecoin `XDG`; those two are aliased explicitly
because the names are historical and cannot be derived.

---

## 5. Where the boundary is

This loop **never places an order.** It has no trade permission, asks for none,
and the setup above tells you to withhold it. Every order is yours, by hand, in
the exchange's own interface — the decision recorded in
`docs/EXECUTION_ARCHITECTURE.md`, unchanged.
