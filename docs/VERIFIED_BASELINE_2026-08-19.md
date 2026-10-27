# Verified price baseline — 2026-08-19 settled close

Nine tradable holdings. Every series re-pulled 2026-08-20 in 55-row windows and
verified: `gaps=[86400]` exactly, zero duplicate timestamps, zero non-positive
prices, adjacent windows joining seamlessly, today's forming bar excluded.

| symbol | bars | span | last close | 200d line | vs line | daily vol (60d) |
|---|---|---|---|---|---|---|
| XRP | 349 | 2025-09-05 → 2026-08-19 | 1.105400 | 1.277761 | −13.5% | 2.21% |
| XLM | 220 | 2026-01-12 → 2026-08-19 | 0.170252 | 0.172819 | −1.5% | 2.76% |
| SOL | 220 | 2026-01-12 → 2026-08-19 | 85.34 | 81.2698 | +5.0% | 2.51% |
| HBAR | 419 | 2025-06-27 → 2026-08-19 | 0.070580 | 0.084513 | −16.5% | 2.12% |
| ADA | 220 | 2026-01-12 → 2026-08-19 | 0.187020 | 0.224636 | −16.7% | 3.52% |
| CRO | 220 | 2026-01-12 → 2026-08-19 | 0.048800 | 0.066410 | −26.5% | 2.48% |
| ONDO | 220 | 2026-01-12 → 2026-08-19 | 0.347020 | 0.314621 | +10.3% | 3.80% |
| PEPE | 220 | 2026-01-12 → 2026-08-19 | 0.00000288 | 0.00000334 | −13.8% | 3.58% |
| WLFI | 110 | 2026-05-02 → 2026-08-19 | 0.061420 | 0.058937 (110d) | +4.2% | — |

CC (Canton): no series — not tradable on Coinbase. Hand price $0.09105.

## Portfolio at these prices

(Removed 2026-09-05: the owner's position values at these prices and the actions they implied. The prices above are public; the positions were not the project's to publish. See docs/KNOWN_ISSUES.md issue 15.)

## Provenance

Source: `api.exchange.coinbase.com` daily candles, public endpoint, no key.

HBAR's stored archive was independently spot-checked against a fresh pull on six
dates (2026-04-28 → 05-03) and matched to **0.000%**, so its interior was sound;
only its leading row had been corrupted, and it was repaired by splicing
2026-06-11 → 08-19 onto it. See `claude/PRICE_DATA_INTEGRITY.md` for why that
check was necessary.
