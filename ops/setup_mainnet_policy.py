"""ops/setup_mainnet_policy.py -- walk the XRP mainnet gate, without opening it.

There are four locks between this code and real money, and they are in code,
not in advice. This script REPORTS on all four and can turn exactly one of
them: it writes the empty policy template. It will not add an address, will
not run the testnet proof, will not sign, and will not send.

  1. TESTNET PROOF.  require_testnet_proof() refuses unless
     xrp_testnet_proof.json exists with a 64-char tx hash. It is written only
     by a real submission from test_xrp_live.py. The XRP path has never
     executed on any network -- autofill, submit_and_wait and the reserve
     check are written and reviewed, never run. Only you can clear this, on a
     networked machine, with a faucet account. Five minutes.

  2. POLICY FILE.  MainnetPolicy.load refuses with no policy, and refuses a
     policy with an empty destination list -- which is the correct default,
     not a bug. This script writes the template. YOU add the address, after
     checking it against the source you got it from. A signing key alone must
     never be enough to move funds somewhere new.

  3. FILE PERMISSIONS.  The policy must be owner-only, because anything that
     can edit it can raise your own limits. On Windows this is currently
     unsatisfiable -- see docs/P9_WINDOWS_OWNER_ONLY.md. Reported here, not
     worked around.

  4. DESTINATION TAG.  Required by default. Sending to an exchange without one
     means the recipient cannot identify the payment: the ledger reports
     success and the funds are unrecoverable. It is the most common way XRP is
     permanently lost. The exemption is one explicit field, per destination.

Usage:
    python ops/setup_mainnet_policy.py            report only
    python ops/setup_mainnet_policy.py --template write the empty template
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
POLICY = os.path.join(HERE, "xrp_mainnet_policy.json")
PROOF = os.path.join(HERE, "xrp_testnet_proof.json")


def line(n, state, text):
    print("  %d. %-9s %s" % (n, state, text))


def main():
    print("=" * 72)
    print("XRP MAINNET GATE  --  reporting, not opening")
    print("=" * 72)

    if os.path.exists(PROOF):
        try:
            h = json.load(open(PROOF)).get("tx_hash", "")
        except Exception:
            h = ""
        line(1, "OPEN" if len(h) == 64 else "BLOCKED",
             "testnet proof %s" % (h[:16] + "..." if len(h) == 64 else "INVALID"))
    else:
        line(1, "BLOCKED", "no testnet proof. Run: python test_xrp_live.py")

    if not os.path.exists(POLICY):
        if "--template" in sys.argv:
            try:
                from covenant_xrp_mainnet import write_policy_template
                write_policy_template(POLICY)
                line(2, "TEMPLATE", "written. Now edit it: one address you have "
                                    "checked. Start the ceilings low.")
            except Exception as e:
                line(2, "ERROR", "could not write the template: %s" % e)
        else:
            line(2, "BLOCKED", "no policy. Re-run with --template to create an "
                               "EMPTY one (no destinations = no sends).")
    else:
        try:
            raw = json.load(open(POLICY))
            dests = raw.get("destinations", [])
            real = [d for d in dests if not str(d.get("address", "")).startswith("rEXAMPLE")]
            if not real:
                line(2, "BLOCKED", "policy exists but has no real destination "
                                   "(the template placeholder is still there).")
            else:
                line(2, "OPEN", "%d destination(s): %s" %
                     (len(real), ", ".join(str(d.get("label")) for d in real)))
                for d in real:
                    if d.get("destination_tag") is None and not d.get("tag_not_required"):
                        line(4, "BLOCKED", "'%s' has no destination tag and no "
                             "explicit exemption -- authorize_mainnet_payment "
                             "will refuse. That refusal is the control working."
                             % d.get("label"))
        except Exception as e:
            line(2, "ERROR", "policy is not valid JSON: %s" % e)

    if os.path.exists(POLICY):
        sys.path.insert(0, os.path.join(HERE, "ops"))
        try:
            from owner_only import require_owner_only, OwnerOnlyError
            try:
                require_owner_only(POLICY)
                line(3, "OK", "policy is owner-only by the real platform rule.")
            except OwnerOnlyError as e:
                line(3, "BLOCKED", str(e)[:160])
        except Exception:
            line(3, "UNKNOWN", "ops/owner_only.py not importable.")
        if sys.platform.startswith("win"):
            line(3, "NOTE", "even when the ACL is correct, MainnetPolicy.load "
                            "reads the POSIX mode and will still refuse on "
                            "Windows -- P9. See docs/P9_WINDOWS_OWNER_ONLY.md. "
                            "That is a code change and it is YOURS to approve.")
    print("")
    print("Nothing in this script signs, sends, or holds a key. It never will.")


if __name__ == "__main__":
    main()
