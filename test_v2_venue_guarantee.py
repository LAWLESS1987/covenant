#!/usr/bin/env python3
"""test_v2_venue_guarantee.py -- V2: the venue layer's one rule, and the
checker that reports it, measured rather than read.

venues.py opens with "THE ONE RULE IN THIS FILE": every call that can reach a
matching engine takes `live` and it defaults to False. money_posture.py is
the file CONSTITUTION.md II.1 tells a reader to run instead of trusting the
paragraph. Until 2026-09-02 nothing tested either. The rule was true; the
checker described two of three adapters and called their guarantee uniform.

WHAT V2 PINS.

  L*  every adapter's place() takes `live` and it defaults to False.
  G*  every adapter declares DRY_RUN ("venue" or "local") and the
      declaration matches what the code does: a "venue" adapter names its
      preview endpoint; a "local" adapter's dry run returns
      venue_validated=False and says so.
  C*  has_credentials() is a path-existence test and nothing more. It is the
      one venue method a read-only checker may call, so it may not open a
      file.
  P*  money_posture.py: names every adapter; returns 0/1 according to the
      config on this machine; and returns 2 -- never 0 -- when the venue
      layer is not fully visible. That last one is mutation-tested: an
      adapter with no declaration, and a venues.py that cannot import, both
      produce 2.
  T*  covenant_trader.py passes live=True only through the armed gate.

Pure. Imports venues.py and money_posture.py (no network, no credential),
inspects signatures and source, calls main() with a captured stdout. Places
nothing, arms nothing.
"""
import contextlib
import inspect
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print(f"{'ok  ' if ok else 'FAIL'}  {label}"
          f"{'' if ok else '  ' + str(detail)[:200]}", flush=True)


def src(obj):
    try:
        return inspect.getsource(obj)
    except (OSError, TypeError):
        return ""


def run_main(mp):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = mp.main()
    return rc, buf.getvalue()


def main():
    print("V2 -- the venue layer's one rule, and the checker that reports it\n")

    import venues as V                                       # noqa: N812
    vs = list(V.all_venues())
    check("V0 all_venues() returns at least three adapters (not vacuous)",
          len(vs) >= 3, [v.name for v in vs])

    # ---- L: live defaults to False, everywhere -----------------------------
    for v in vs:
        sig = inspect.signature(v.place)
        p = sig.parameters.get("live")
        check(f"L:{v.name:<10} place() takes `live` and it defaults to False",
              p is not None and p.default is False,
              f"{sig}")

    # ---- G: the declaration matches the code -------------------------------
    for v in vs:
        mode = getattr(v, "DRY_RUN", None)
        ep = getattr(v, "DRY_RUN_ENDPOINT", "<unset>")
        check(f"G:{v.name:<10} declares DRY_RUN in {{venue, local}}",
              mode in ("venue", "local"), mode)
        if mode == "venue":
            check(f"G:{v.name:<10} names its preview endpoint (DRY_RUN_ENDPOINT)",
                  isinstance(ep, str) and ep.strip(), ep)
            check(f"G:{v.name:<10} the endpoint it names appears in its place() "
                  f"source -- the declaration is about THIS code",
                  ep and (ep.split()[0] in src(v.place)
                          or ep.replace("/api/v3/brokerage", "") in src(v.place)),
                  ep)
        elif mode == "local":
            s = src(v.place)
            check(f"G:{v.name:<10} has no endpoint to name (DRY_RUN_ENDPOINT is "
                  f"None)", ep is None, ep)
            check(f"G:{v.name:<10} its dry run returns venue_validated=False -- "
                  f"a weaker guarantee in the same shape must say so",
                  '"venue_validated": False' in s)
            check(f"G:{v.name:<10} ...and says why in words a caller will see",
                  "LOCAL" in s and "no preview" in s.lower())

    # ---- C: has_credentials() opens nothing --------------------------------
    for v in vs:
        s = src(v.has_credentials)
        got = v.has_credentials()
        check(f"C:{v.name:<10} has_credentials() is os.path.exists and returns "
              f"a bool without raising",
              isinstance(got, bool) and "os.path.exists" in s
              and "open(" not in s, s.strip()[:120])

    # ---- P: money_posture.py, the checker the constitution names -----------
    import money_posture as MP
    cfg = {}
    try:
        with open(os.path.join(HERE, "trader_config.json"), encoding="utf-8") as fh:
            cfg = json.load(fh)
    except Exception:                                        # noqa: BLE001
        pass
    armed = bool(cfg.get("armed"))
    halted = os.path.exists(os.path.join(HERE, "TRADER_HALT"))
    expect = 1 if (armed and not halted) else 0

    rc, out = run_main(MP)
    check(f"P1 money_posture.main() returns {expect} for THIS machine's config "
          f"(armed={armed}, halt={halted}) -- 2 would mean it could not see",
          rc == expect, f"rc={rc}")
    low = out.lower()
    for v in vs:
        check(f"P:{v.name:<10} is named in the checker's output -- the first "
              f"version named two of three", v.name.lower() in low)
    check("P2 the output states the WEAKEST dry run, so a reader is not left "
          "to average three guarantees into one",
          "weakest dry run" in low)
    weakest = ("local" if any(getattr(v, "DRY_RUN", None) == "local" for v in vs)
               else "venue")
    check(f"P3 ...and the weakest it states is the one the code declares "
          f"({weakest})", f"weakest dry run: {weakest}" in low)

    # Mutation 1: an adapter that declares nothing. The checker must refuse
    # to call the posture DISARMED and exit 2.
    class Undeclared:
        name = "mutant"

        def has_credentials(self):
            return False

    real = MP.load_venues
    try:
        MP.load_venues = lambda: (vs + [Undeclared()], None)
        rc2, out2 = run_main(MP)
    finally:
        MP.load_venues = real
    check("P4 MUTATION an adapter with no DRY_RUN makes the checker exit 2, "
          "not 0 -- a fourth venue cannot inherit a guarantee by being added",
          rc2 == 2, f"rc={rc2}")
    check("P5 ...and the output names the undeclared adapter",
          "mutant" in out2.lower() and "undeclared" in out2.lower())

    # Mutation 2: venues.py cannot be seen at all.
    try:
        MP.load_venues = lambda: ([], "venues.py could not be imported: test")
        rc3, out3 = run_main(MP)
    finally:
        MP.load_venues = real
    check("P6 MUTATION an unimportable venues.py makes the checker exit 2 -- "
          "'no venues' and 'could not look' are different facts",
          rc3 == 2, f"rc={rc3}")
    check("P7 ...and it says UNKNOWN rather than listing nothing",
          "unknown" in out3.lower())

    # Mutation 3: the real thing still reads 0/1 after the mutants -- the
    # monkeypatch was undone, so P1 was not measuring a leftover.
    rc4, _ = run_main(MP)
    check("P8 the checker reads its true value again after the mutations",
          rc4 == expect, f"rc={rc4}")

    # ---- T: the trader's armed gate ----------------------------------------
    tsrc = ""
    try:
        with open(os.path.join(HERE, "covenant_trader.py"), encoding="utf-8",
                  errors="replace") as fh:
            tsrc = fh.read()
    except OSError:
        pass
    check("T1 covenant_trader.py passes live=go_live and nothing else to "
          "place() -- one path, one gate",
          tsrc.count("live=go_live") == 1 and "live=True" not in tsrc)
    check("T2 go_live is 'no blocker fired', and armed=false is a blocker",
          "go_live = not bad" in tsrc and 'bad.append("armed=false' in tsrc)
    check("T3 the trader iterates all_venues() -- so the third adapter IS in "
          "the daily loop, which is why the documents had to name it",
          "V.all_venues()" in tsrc)

    n, ok = len(results), sum(results)
    print(f"\nV2: {ok}/{n} passed")
    return 0 if ok == n else 1


if __name__ == "__main__":
    raise SystemExit(main())
