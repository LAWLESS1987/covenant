#!/usr/bin/env python3
"""test_intent_provenance.py -- intent provenance on every write, driven BOTH WAYS.

    python test_intent_provenance.py        # exit 0 only if every check holds

Every guard is driven green AND red in the same run (a check that has only ever
passed has never been observed):

  P1  a write carrying all three fields PASSES and stores them verbatim.
  P2  a write missing ANY of intent / beneficiary / divergence ABORTS.
  P3  an intent that restates the payload ABORTS; a real purpose intent passes.
  P4  divergence != "none" REQUIRES an existing diverges_from, cross-linked and
      traversable; a missing or dangling link aborts; "none" + a link aborts.
  P5  backfill() is refused and the refusal is logged.
  P6  tombstone_unprovenanced() marks a pre-schema record's absence, does not
      fill it, and leaves a provenanced record alone.
  P7  intent_check() returns the fields verbatim plus a satisfiability flag, and
      the flag flips to UNSATISFIABLE when the record is superseded or its
      divergence target is gone.
  P8  a refused write leaves NO file -- only the audit line that it was refused.
  P9  the provenance fields are chain-covered: editing intent on disk makes
      verify_integrity() name the file (and it was clean before).

Stdlib only; no network, no model. The ethics gate is replaced by an always-allow
stub so these checks isolate the PROVENANCE gate, not the ethics one.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from memory_store import MemoryStore, parse_memory          # noqa: E402
from ethics_gate import MemoryRefused, Verdict, ALLOW        # noqa: E402
import intent_check                                          # noqa: E402

results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print(f"{'ok  ' if ok else 'FAIL'}  {label}"
          f"{'' if ok else '  ' + str(detail)[:200]}", flush=True)


class _AllowGate:
    """Always allows, so these checks test the provenance screen in isolation."""
    def review(self, name, description, body, agent):
        return Verdict(verdict=ALLOW, by="test", reason="ok")


def refused(fn, *a, **k):
    """Run fn; return (True, reason) if it raised MemoryRefused, else (False, '')."""
    try:
        fn(*a, **k)
        return False, ""
    except MemoryRefused as e:
        return True, str(e)


# A valid purpose intent that shares no words with the bodies below.
GOOD = dict(intent="warn a later reader that this source was unreliable",
            beneficiary="future unknown agent", divergence="none")


def main():
    tmp = tempfile.mkdtemp(prefix="intent_prov_")
    try:
        st = MemoryStore(os.path.join(tmp, "s"), gate=_AllowGate())

        # --- P1: all three fields -> write passes, fields stored verbatim. -----
        out = st.put("alpha", "a plain description", "project",
                     "The quick brown fox jumped.", "tester", **GOOD)
        meta = out.get("metadata") or {}
        check("P1.0 a write with all three fields passes", out["name"] == "alpha")
        check("P1.1 intent stored verbatim",
              meta.get("intent") == GOOD["intent"], meta.get("intent"))
        check("P1.2 beneficiary stored verbatim",
              meta.get("beneficiary") == "future unknown agent", meta)
        check("P1.3 divergence stored verbatim", meta.get("divergence") == "none", meta)
        raw = open(os.path.join(st.root, "alpha.md"), encoding="utf-8").read()
        check("P1.4 the fields are in the frontmatter other agents parse",
              "  intent: " in raw and "  beneficiary: " in raw
              and "  divergence: none" in raw, raw[:200])

        # --- P2: missing ANY field aborts (both ways: present above passed). ----
        for drop in ("intent", "beneficiary", "divergence"):
            k = dict(GOOD); k[drop] = "   "
            was, reason = refused(st.put, f"missing-{drop}", "d", "project",
                                  "some ordinary body here", "t", **k)
            check(f"P2.{drop} a write missing {drop} ABORTS", was, reason)
            check(f"P2.{drop}-notrace no file was written for the refused {drop}",
                  not os.path.exists(os.path.join(st.root, f"missing-{drop}.md")))

        # --- P3: intent that restates the payload aborts; purpose intent passes.-
        body = "Lawrence prefers outcomes over instructions."
        restate = dict(GOOD, intent="Lawrence prefers outcomes over instructions")
        was, reason = refused(st.put, "restater", "d", "user", body, "t", **restate)
        check("P3.0 an intent that RESTATES the body aborts", was, reason)
        purpose = dict(GOOD, intent="steer future planning toward his stated goals")
        ok2 = st.put("purposeful", "d", "user", body, "t", **purpose)
        check("P3.1 a real PURPOSE intent on the same body passes",
              ok2["name"] == "purposeful")

        # --- P4: divergence cross-link, both ways. ------------------------------
        st.put("prior-claim", "d", "project", "the earlier claim lives here", "t", **GOOD)
        dv = dict(intent="correct the earlier claim with newer evidence",
                  beneficiary="future unknown agent",
                  divergence="contradicts the figure in prior-claim",
                  diverges_from="prior-claim")
        d_out = st.put("newer", "d", "project", "the corrected claim", "t", **dv)
        check("P4.0 divergence != none with an existing diverges_from passes",
              d_out["name"] == "newer")
        check("P4.1 the cross-link is stored and traversable",
              (d_out.get("metadata") or {}).get("diverges_from") == "prior-claim"
              and st.get("prior-claim") is not None)
        was, _ = refused(st.put, "dangle", "d", "project", "b", "t",
                         intent="diverge from a record that is not here",
                         beneficiary="future unknown agent",
                         divergence="conflicts with ghost", diverges_from="ghost")
        check("P4.2 divergence != none naming a NONEXISTENT record aborts", was)
        was, _ = refused(st.put, "nolink", "d", "project", "b", "t",
                         intent="diverge but name no record to diverge from",
                         beneficiary="future unknown agent",
                         divergence="conflicts with something", diverges_from="")
        check("P4.3 divergence != none with NO diverges_from aborts", was)
        was, _ = refused(st.put, "contradictory", "d", "project", "b", "t",
                         intent="say none yet point at a record anyway",
                         beneficiary="future unknown agent",
                         divergence="none", diverges_from="prior-claim")
        check("P4.4 divergence == none WITH a diverges_from aborts (one or the other)", was)

        # --- P5: backfill is always refused, and logged. ------------------------
        was, reason = refused(st.backfill, "alpha", "editor",
                              intent="sneak a purpose on after the fact")
        check("P5.0 backfill() is refused", was, reason)
        audit = open(st.audit, encoding="utf-8").read()
        check("P5.1 the backfill refusal is logged with a reason",
              any(json.loads(ln).get("backfill_refused")
                  for ln in audit.splitlines() if ln.strip()), "")

        # --- P6: pre-schema record gets its absence marked, not filled. ---------
        # Write a record WITHOUT provenance straight to disk (as a pre-schema
        # import would have), bypassing put().
        old = ("---\nname: legacy\ndescription: an old one\nmetadata:\n"
               "  type: reference\n  agent: past\n---\nbody from before the schema\n")
        with open(os.path.join(st.root, "legacy.md"), "w", encoding="utf-8") as fh:
            fh.write(old)
        marked = st.tombstone_unprovenanced("migrator")
        check("P6.0 the pre-schema record is marked", "legacy" in marked, marked)
        check("P6.1 a provenanced record is NOT marked", "alpha" not in marked, marked)
        still = open(os.path.join(st.root, "legacy.md"), encoding="utf-8").read()
        check("P6.2 the absence is NOTED, not FILLED (no intent added to the file)",
              "intent:" not in still, still[:120])
        check("P6.3 a provenance_tombstone line is in the chain",
              any(json.loads(ln).get("action") == "provenance_tombstone"
                  for ln in open(st.audit, encoding="utf-8").read().splitlines()
                  if ln.strip()), "")

        # --- P7: intent_check reads verbatim fields + a satisfiability flag. -----
        ic = intent_check.intent_check(st.root, "newer")
        check("P7.0 intent_check returns the intent VERBATIM (no paraphrase)",
              ic["intent"] == dv["intent"], ic.get("intent"))
        check("P7.1 and the beneficiary and divergence verbatim",
              ic["beneficiary"] == dv["beneficiary"]
              and ic["divergence"] == dv["divergence"], ic)
        check("P7.2 a standing record with an intact divergence link is satisfiable",
              ic["satisfiable"] is True, ic)
        # Flip it: delete the divergence target -> the chain is broken.
        st.delete("prior-claim", "remover", "gone for the test")
        ic2 = intent_check.intent_check(st.root, "newer")
        check("P7.3 removing the divergence target makes the intent UNSATISFIABLE",
              ic2["satisfiable"] is False and "gone" in ic2["assessment"], ic2)
        # Supersede makes an intent unsatisfiable too.
        st.put("super", "d", "project", "the superseding record", "t", **GOOD)
        st.supersede("purposeful", "super", "t")
        ic3 = intent_check.intent_check(st.root, "purposeful")
        check("P7.4 a superseded record's intent is UNSATISFIABLE",
              ic3["satisfiable"] is False and "superseded" in ic3["assessment"], ic3)
        # A pre-schema record reads as unsatisfiable (no provenance to satisfy).
        ic4 = intent_check.intent_check(st.root, "legacy")
        check("P7.5 a pre-schema record reads as unsatisfiable",
              ic4["satisfiable"] is False and "predates" in ic4["assessment"], ic4)

        # --- P9: the fields are chain-covered (tamper detection). ---------------
        clean = st.verify_integrity()
        check("P9.0 verify_integrity is clean before tampering", clean["ok"], clean)
        p = os.path.join(st.root, "alpha.md")
        txt = open(p, encoding="utf-8").read().replace(
            GOOD["intent"], "a forged intent nobody wrote")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(txt)
        tampered = st.verify_integrity()
        check("P9.1 editing the intent on disk is caught by verify_integrity",
              not tampered["ok"]
              and any(d["name"] == "alpha" for d in tampered["drifted"]), tampered)

        print()
        bad = results.count(False)
        if bad:
            print(f"test_intent_provenance: {bad} FAILED of {len(results)}")
            return 1
        print(f"test_intent_provenance: all {len(results)} checks passed")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
