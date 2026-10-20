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
    fails = []

    if OC._selftest() != 0:
        fails.append("octopus selftest failed (arm behaviour or kill switch)")

    # phone-safety: the module must not drag in a heavy dependency the phone lacks
    heavy = [m for m in ("numpy", "torch", "snntorch", "brian2") if m in sys.modules]
    if heavy:
        fails.append("octopus pulled in a heavy dep the phone has not: %s" % heavy)

    # extensibility toward eight arms: a fourth arm attaches and is read
    o = OC.default_octopus()

    class Extra(OC.Arm):
        name = "extra"
    o.attach(Extra())
    os.environ[OC.KILL_ENV] = "0"
    rates = o.integrate()
    if set(rates) != {"witness", "encoder", "reflex", "extra"}:
        fails.append("a fourth arm did not attach/integrate: %s" % sorted(rates))

    # determinism: same input -> same spikes (needed for a reproducible node)
    a = OC.EncoderArm().encode("determinism check")
    b = OC.EncoderArm().encode("determinism check")
    if a != b:
        fails.append("encoder arm is not deterministic")

    if fails:
        print("OC1 FAIL:")
        for f in fails:
            print("  -", f)
        return 1
    print("OC1 PASS: octopus runs pure-Python (phone-safe, no heavy deps), arms extensible and deterministic, "
          "kill switch both ways")
    return 0


if __name__ == "__main__":
    sys.exit(main())
