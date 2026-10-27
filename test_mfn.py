#!/usr/bin/env python3
"""test_mfn.py -- MF: the two federation rules, driven both ways.

WHAT IT PINS (docs/FEDERATION_RULES.md, constitution-protected):

  MF1*  MOST FAVOURED PEER. An asymmetric term is FOUND, a symmetric one is
        not, and a declared exception is honoured only when it carries a
        reason. Every direction driven -- a guard that has only ever said
        "clean" has never been observed.
  MF2*  A TERM IS NOT AN OUTCOME. The rule must not flag a peer refused by an
        equal rule. This is the direction that would break the federation if
        it were wrong, so it gets its own checks: the update door's futility
        bound refuses the phone and not the PC today, and that must stay
        invisible here.
  MF3*  ENUMERATION IS BY DISCOVERY. A surface added AFTER this file was
        written must be found. The check writes a new file into a temp tree
        and asserts it appears -- because this project has already shipped a
        recount tool that hardcoded its inputs and missed the sixth.
  MF4*  EXIT. Residue is what would still name a peer after they left, and it
        reports nothing for a peer nothing mentions.
  MF5*  BELOW TWO PEERS IT SAYS UNDETERMINED, never "clean". An empty or
        single-peer roster makes MFN unmeasurable, and an empty loop reporting
        no asymmetry is the fake-guard shape of A65 and A74.

Hermetic: every check runs against a temp tree. The real ops/ is read once, by
MF2b, and only to assert something is ABSENT from it.

    python test_mfn.py
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import mfn as M                                                  # noqa: E402

results = []


def check(label, ok, detail=""):
    results.append((label, bool(ok)))
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}" + (f"  -- {detail}" if detail else ""))


def tree(files):
    """A temp repo root holding ops/<name>.json for each entry given."""
    root = tempfile.mkdtemp(prefix="mfn_")
    os.makedirs(os.path.join(root, "ops"), exist_ok=True)
    for name, body in files.items():
        with open(os.path.join(root, "ops", name), "w", encoding="utf-8") as fh:
            json.dump(body, fh)
    return root


ROSTER = ["pc", "phone"]


def main():
    print("MF -- most favoured peer, and unilateral exit\n")

    # ---- MF1: an asymmetric term is found, a symmetric one is not ----------
    sym = tree({"daily_plan_signers.json": {"pc": "k1", "phone": "k2"},
                "quota.json": {"pc": 10, "phone": 10}})
    asym = tree({"daily_plan_signers.json": {"pc": "k1", "phone": "k2"},
                 "quota.json": {"pc": 10}})
    try:
        s_found = M.surfaces(root=sym, roster=ROSTER)
        a_found = M.surfaces(root=asym, roster=ROSTER)
        check("MF1a a term both peers hold is not an asymmetry",
              M.asymmetries(s_found, ROSTER) == [], str(s_found))
        got = M.asymmetries(a_found, ROSTER)
        check("MF1b a term ONE peer holds IS an asymmetry, and it names who "
              "holds it and who does not",
              len(got) == 1 and got[0]["term"] == "ops/quota.json"
              and got[0]["held_by"] == ["pc"] and got[0]["withheld_from"] == ["phone"],
              str(got))
        check("MF1c the ROSTER itself is never an asymmetry -- it is the "
              "population, not a term granted to some of it",
              not any(x["term"].startswith("ops/daily_plan_signers.json")
                      for x in M.asymmetries(a_found, ROSTER)),
              str([x["term"] for x in got]))
        # NESTED, because a term is as likely to live one level down.
        nest = tree({"daily_plan_signers.json": {"pc": "k1", "phone": "k2"},
                     "rates.json": {"limits": {"pc": 5}}})
        n_found = M.surfaces(root=nest, roster=ROSTER)
        check("MF1d a term nested under a key is found too",
              any(t == "ops/rates.json::limits" for t in n_found), str(n_found))
        shutil.rmtree(nest, ignore_errors=True)
    finally:
        for d in (sym, asym):
            shutil.rmtree(d, ignore_errors=True)

    # ---- MF1e/f: exceptions, honoured only with a reason -------------------
    real_exc = M.EXCEPTIONS
    tmp_exc = tempfile.mktemp(suffix="_exc.json")
    asym = tree({"daily_plan_signers.json": {"pc": "k1", "phone": "k2"},
                 "quota.json": {"pc": 10}})
    try:
        found = M.surfaces(root=asym, roster=ROSTER)
        M.EXCEPTIONS = tmp_exc
        with open(tmp_exc, "w", encoding="utf-8") as fh:
            json.dump({"exceptions": [{"term": "ops/quota.json",
                                       "why": "the PC holds the credential store and the phone must not"}]}, fh)
        got = M.asymmetries(found, ROSTER)
        check("MF1e a declared exception with a reason is still REPORTED, and "
              "marked declared -- hidden is not the same as allowed",
              len(got) == 1 and got[0]["declared"] is True and got[0]["why"],
              str(got)[:110])
        # BROKEN ON PURPOSE: a reasonless exception must not buy silence.
        with open(tmp_exc, "w", encoding="utf-8") as fh:
            json.dump({"exceptions": [{"term": "ops/quota.json", "why": "because"}]}, fh)
        good, bad = M.exceptions()
        check("MF1f an exception with no real reason is REJECTED, not honoured "
              "-- otherwise the escape hatch is wider than the rule",
              good == {} and len(bad) == 1, "good=%s bad=%s" % (good, bad))
        check("MF1g ...and a rejected exception is itself a defect in the verdict",
              M._verdict(ROSTER, M.asymmetries(found, ROSTER), bad).startswith("DEFECT"),
              M._verdict(ROSTER, [], bad)[:80])
    finally:
        M.EXCEPTIONS = real_exc
        shutil.rmtree(asym, ignore_errors=True)
        try:
            os.unlink(tmp_exc)
        except OSError:
            pass

    # ---- MF2: a term is not an outcome -------------------------------------
    #
    # THE DIRECTION THAT MATTERS MOST. Read as "equal results", this rule
    # forbids every rule that can refuse anybody, and a federation whose rules
    # may never say no cannot say no to anything. The live case: the update
    # door's futility bound (A147) refuses `phone` and not `pc` right now.
    # That is one rule offered to everyone, which the phone has met. It must
    # not appear here.
    check("MF2a the futility bound leaves no per-peer CONFIGURATION, so an "
          "outcome cannot masquerade as a term",
          not os.path.isfile(os.path.join(HERE, "ops", "app", "per_peer.json")),
          "no per-peer file under ops/app/")
    live = M.surfaces()
    check("MF2b ...and the live scan finds no term naming only the peer that "
          "rule currently refuses",
          not any("app" in t for t in live), str(sorted(live)))
    # And the positive control: if a per-peer TERM did exist there, it WOULD
    # be found -- so MF2b is measuring the absence of a thing that is findable.
    ctl = tree({"daily_plan_signers.json": {"pc": "k1", "phone": "k2"},
                "app_grant.json": {"pc": True}})
    try:
        check("MF2c ...and that absence is meaningful, because a per-peer term "
              "of the same shape IS found when one exists",
              any(t == "ops/app_grant.json" for t in M.surfaces(root=ctl, roster=ROSTER)),
              "positive control")
    finally:
        shutil.rmtree(ctl, ignore_errors=True)

    # ---- MF3: discovery, not recall ----------------------------------------
    disc = tree({"daily_plan_signers.json": {"pc": "k1", "phone": "k2"}})
    try:
        before = set(M.surfaces(root=disc, roster=ROSTER))
        with open(os.path.join(disc, "ops", "invented_later.json"), "w", encoding="utf-8") as fh:
            json.dump({"phone": {"perk": 1}}, fh)
        after = set(M.surfaces(root=disc, roster=ROSTER))
        check("MF3a a surface that did not exist when this file was written is "
              "found -- enumeration is by content, never by a list",
              "ops/invented_later.json" in (after - before), str(after - before))
        check("MF3b ...and it is reported as an asymmetry, not merely seen",
              any(x["term"] == "ops/invented_later.json"
                  for x in M.asymmetries(M.surfaces(root=disc, roster=ROSTER), ROSTER)),
              "found and flagged")
    finally:
        shutil.rmtree(disc, ignore_errors=True)

    # ---- MF4: exit ---------------------------------------------------------
    ex = tree({"daily_plan_signers.json": {"pc": "k1", "phone": "k2"},
               "quota.json": {"pc": 10}})
    try:
        found = M.surfaces(root=ex, roster=ROSTER)
        check("MF4a residue names every surface that would still mention a "
              "departing peer",
              M.residue("pc", found, ROSTER) == ["ops/daily_plan_signers.json", "ops/quota.json"],
              str(M.residue("pc", found, ROSTER)))
        check("MF4b ...and a peer no surface mentions leaves none",
              M.residue("nobody", found, ROSTER) == [],
              str(M.residue("nobody", found, ROSTER)))
    finally:
        shutil.rmtree(ex, ignore_errors=True)

    # ---- MF5: below two peers, UNDETERMINED and not "clean" ----------------
    check("MF5a one peer is UNDETERMINED -- a difference between peers cannot "
          "be measured without two of them",
          M._verdict(["pc"], [], []).startswith("UNDETERMINED"),
          M._verdict(["pc"], [], [])[:70])
    check("MF5b no peers is UNDETERMINED too, never a silent pass",
          M._verdict([], [], []).startswith("UNDETERMINED"), M._verdict([], [], [])[:60])
    check("MF5c two peers with nothing wrong is the ONLY way to a clean verdict",
          M._verdict(ROSTER, [], []).startswith("no asymmetry"),
          M._verdict(ROSTER, [], [])[:60])
    check("MF5d ...and the clean verdict refuses to claim more than it measured",
          "smaller than" in M._verdict(ROSTER, [], []),
          M._verdict(ROSTER, [], [])[-60:])

    # ---- MF6: the rules are constitution-protected -------------------------
    try:
        import constitution as C
        protected = [p for p in C.PROTECTED if p["file"] == "docs/FEDERATION_RULES.md"]
        body = C._extract(os.path.join(HERE, "docs", "FEDERATION_RULES.md"),
                          "## What is owed to every peer") if protected else None
        check("MF6a the two rules are inside the constitution's protected text, "
              "so amending them moves the hash every peer reads",
              len(protected) == 1 and bool(body), str([p["opens"] for p in protected]))
        check("MF6b ...and the protected block actually carries both rules",
              bool(body) and "Most favoured peer" in body and "Exit is unilateral" in body
              and "not an outcome" in body,
              "%d chars" % (len(body or "")))
    except Exception as e:                                       # noqa: BLE001
        check("MF6 the rules are constitution-protected", False,
              "%s: %s" % (type(e).__name__, e))

    ok = sum(1 for _, o in results if o)
    print(f"\nMF: {ok}/{len(results)} passed")
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
