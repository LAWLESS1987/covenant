"""OC1 -- the octopus spiking nervous system (covenant_octopus.py).

Three semi-autonomous pure-Python LIF arms (witness/encoder/reflex), a central integrate, a kill switch both ways,
and -- the property the phone depends on -- it pulls in NO heavy dependency (no numpy/torch/snntorch/brian2), so it
runs on Termux. Arms are extensible toward the octopus's eight.

Run: python test_oc1_octopus.py
"""
import os
import sys

import covenant_octopus as OC


def main():
    # Each check appends (ok, why) so the suite prints a tally the sweep can
    # score. Before 2026-10-21 this suite printed only "OC1 PASS: ..." with no
    # "n/n passed" line, so covenant_one's TALLY regex read it as NO RESULT and
    # the sweep counted a green suite as "not clean" (OC1 among the red cohort in
    # ops/TETSU_DAILY.md). The checks are unchanged; only the reporting is.
    checks = []

    checks.append((OC._selftest() == 0, "octopus selftest (arm behaviour or kill switch)"))

    # phone-safety: the module must not drag in a heavy dependency the phone lacks
    heavy = [m for m in ("numpy", "torch", "snntorch", "brian2") if m in sys.modules]
    checks.append((not heavy, "no heavy dep pulled in (found: %s)" % heavy))

    # extensibility toward eight arms: a fourth arm attaches and is read
    o = OC.default_octopus()

    class Extra(OC.Arm):
        name = "extra"
    o.attach(Extra())
    os.environ[OC.KILL_ENV] = "0"
    rates = o.integrate()
    checks.append((set(rates) == {"witness", "encoder", "reflex", "extra"},
                   "a fourth arm attaches/integrates (got %s)" % sorted(rates)))

    # determinism: same input -> same spikes (needed for a reproducible node)
    a = OC.EncoderArm().encode("determinism check")
    b = OC.EncoderArm().encode("determinism check")
    checks.append((a == b, "encoder arm is deterministic"))

    n_ok = sum(1 for ok, _ in checks if ok)
    total = len(checks)
    for ok, why in checks:
        if not ok:
            print("  FAIL -", why)
    if n_ok == total:
        print("OC1 PASS: octopus runs pure-Python (phone-safe, no heavy deps), arms extensible and deterministic, "
              "kill switch both ways")
    print("OC1 %d/%d passed" % (n_ok, total))   # no colon after OC1: the sweep's TALLY would else display "C1: ..."
    return 0 if n_ok == total else 1


if __name__ == "__main__":
    sys.exit(main())
