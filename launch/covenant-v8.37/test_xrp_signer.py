"""Offline tests for covenant_xrp_signer. No network required.

Everything here that can be checked without a funded account IS checked here.
The parts that genuinely need a live ledger (autofill, submit) are named at the
bottom as what remains unproven, rather than mocked into a false green.
"""
import os, sys, stat, tempfile, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import covenant_xrp_signer as X

passed = failed = 0

def check(label, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  PASS: {label}" + (f" -- {detail}" if detail else ""))
    else:
        failed += 1
        print(f"  FAIL: {label}" + (f" -- {detail}" if detail else ""))

# v8.13 item AM -- MainnetGuardError is now also a legitimate refusal type:
# address validation moved into covenant_xrp_mainnet and raises from there.
import covenant_xrp_mainnet as _M
REAL_DEST = "rN7n7otQDd6FczFgLdSqtcsAUxDkw6fzRH"   # a checksum-valid address.
# The placeholder this file used to use ('rDest0000...') is now REJECTED, which
# is the point of item AM: it was never a valid address and the old
# startswith("r") check accepted it -- in this very test file.

def raises(fn, needle=""):
    try:
        fn()
        return False, "no exception"
    except (X.XRPSignerError, _M.MainnetGuardError) as e:
        return (needle.lower() in str(e).lower()), str(e)[:90]
    except Exception as e:
        return False, f"wrong type {type(e).__name__}: {e}"

work = tempfile.mkdtemp(prefix="xrpsig_")
print("== XRP signer: key handling ==")

seed_path = os.path.join(work, "t.seed")
addr = X.create_testnet_seed_file(seed_path)
check("seed file created with a valid address", addr.startswith("r"), addr)
check("seed file is mode 0600",
      stat.S_IMODE(os.stat(seed_path).st_mode) == 0o600,
      oct(stat.S_IMODE(os.stat(seed_path).st_mode)))

ok, why = raises(lambda: X.create_testnet_seed_file(seed_path), "refusing to overwrite")
check("refuses to overwrite an existing seed file", ok, why)

missing = os.path.join(work, "nope.seed")
ok, why = raises(lambda: X.XRPSigner(missing), "no xrp seed file")
check("missing seed file is a clear error", ok, why)

junk = os.path.join(work, "junk.seed")
with open(junk, "w") as fh:
    fh.write("rNotASeedButAnAddress\n")
os.chmod(junk, 0o600)
ok, why = raises(lambda: X.XRPSigner(junk), "does not look like an xrp seed")
check("an address pasted instead of a seed is caught", ok, why)

empty = os.path.join(work, "empty.seed")
open(empty, "w").close()
os.chmod(empty, 0o600)
ok, why = raises(lambda: X.XRPSigner(empty), "empty")
check("an empty seed file is caught", ok, why)

print("\n== XRP signer: network selection ==")
ok, why = raises(lambda: X.XRPSigner(seed_path, network="mainnet"), "allow_mainnet")
check("mainnet requires an explicit second opt-in", ok, why)

ok, why = raises(lambda: X.XRPSigner(seed_path, network="maimnet"), "unknown network")
check("a typo'd network name is rejected, not defaulted", ok, why)

loose = os.path.join(work, "loose.seed")
shutil.copy(seed_path, loose)
os.chmod(loose, 0o644)
ok, why = raises(
    lambda: X.XRPSigner(loose, network="mainnet", allow_mainnet=True),
    "readable by group")
check("a mainnet signer refuses a world-readable seed file", ok, why)

signer = X.XRPSigner(seed_path)  # testnet default
check("testnet is the default network", signer.network == "testnet", signer.network)
check("signer exposes the funded-account address", signer.address == addr, signer.address)

print("\n== XRP signer: payment guards (no network touched) ==")
for label, kwargs, needle in (
    ("a non-XRPL destination", dict(destination="0xdeadbeef", amount_xrp=1.0), "not a valid XRPL address"),
    ("a checksum-invalid lookalike",
     dict(destination="rN7n7otQDd6FczFgLdSqtcsAUxDkw6fzRX", amount_xrp=1.0), "checksum"),
    ("the old placeholder address this file used to use",
     dict(destination="rDest0000000000000000000000000", amount_xrp=1.0), "checksum"),
    ("sending to self", dict(destination=signer.address, amount_xrp=1.0), "to self"),
    ("a zero amount", dict(destination=REAL_DEST, amount_xrp=0.0), "positive"),
    ("a negative amount", dict(destination=REAL_DEST, amount_xrp=-5.0), "positive"),
    ("a NaN amount", dict(destination=REAL_DEST, amount_xrp=float("nan")), "finite"),
    ("an infinite amount", dict(destination=REAL_DEST, amount_xrp=float("inf")), "finite"),
    ("a non-numeric amount", dict(destination=REAL_DEST, amount_xrp="lots"), "numeric"),
    ("exceeding the single-payment ceiling",
     dict(destination=REAL_DEST, amount_xrp=999999.0), "ceiling"),
):
    ok, why = raises(lambda k=kwargs: signer.send_xrp(**k), needle)
    check(f"{label} is refused", ok, why)

print("\n== dry_run default ==")
import inspect
sig = inspect.signature(signer.send_xrp)
check("send_xrp defaults to dry_run=True",
      sig.parameters["dry_run"].default is True,
      str(sig.parameters["dry_run"].default))

shutil.rmtree(work)
print("\n" + "=" * 58)
print(f"{passed} passed, {failed} failed")
print("=" * 58)
print("""
STILL UNPROVEN WITHOUT A LIVE LEDGER (not mocked, not claimed):
  - autofill against a real account (fee and sequence assignment)
  - submit_and_wait and the tesSUCCESS / rejection branches
  - the base-reserve check, which needs a real funded balance
Run test_xrp_live.py against a faucet-funded testnet account to close these.
""")
sys.exit(1 if failed else 0)
