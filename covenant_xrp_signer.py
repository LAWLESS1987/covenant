"""
covenant_xrp_signer.py -- XRP Ledger transaction signing and submission.

NEW v8.10 -- see PATCH LOG item AD in covenant_unified_v8.py.

WHAT THIS CLOSES
----------------
Before this module, covenant_trading_bridge.py could only RECORD a trade that
some other system had already executed. It held no keys, spoke to no ledger,
and could not move a single drop. "Run the node and it will find the XRP" was
never true and no amount of running would have made it true -- the code did not
exist. This is that code.

WHAT IT DELIBERATELY DOES NOT DO
--------------------------------
It does not trade. There is no strategy here, no price feed, no loop, no
scheduler, nothing that acts on its own. Every send is one explicit call by a
caller who has already decided. That boundary is deliberate: signing authority
and trading autonomy are separate powers and this module holds exactly one of
them.

It does not credit the Covenant ledger. Submission returns a validated ledger
hash; turning that into a balance change is the caller's decision, made against
an EXTERNALLY verifiable fact rather than self-attestation. See
validate_ledger_event's docstring for why that distinction is load-bearing.

NETWORK SAFETY
--------------
Testnet is the default and mainnet is not reachable by accident. Selecting
mainnet requires BOTH network="mainnet" AND allow_mainnet=True, passed
separately, because a single mistyped config value should never be the only
thing standing between a test and real money. A mainnet signer also refuses to
load a key file that is group- or world-readable.

KEY HANDLING
------------
The seed is read from a file at mode 0600, never from an argument, never from
the environment, and never logged. It is held in memory only inside the Wallet.
An XRP seed is the entire account -- anyone holding it can drain it, and there
is no recovery and no reversal.
"""

from __future__ import annotations

import os
import stat
import json
import time
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any

try:
    from xrpl.wallet import Wallet
    from xrpl.clients import JsonRpcClient
    from xrpl.models.transactions import Payment
    from xrpl.models.requests import AccountInfo
    from xrpl.transaction import autofill, sign, submit_and_wait
    from xrpl.utils import xrp_to_drops, drops_to_xrp
    XRPL_AVAILABLE = True
    XRPL_IMPORT_ERROR = ""
except Exception as _e:  # pragma: no cover - environment-dependent
    XRPL_AVAILABLE = False
    XRPL_IMPORT_ERROR = f"{type(_e).__name__}: {_e}"


class XRPSignerError(Exception):
    """Raised for every refusal in this module. Never a bare return code:
    a silent failure in a payment path is the worst outcome available."""


# Public JSON-RPC endpoints. Testnet first, and named so a misread is unlikely.
NETWORKS = {
    "testnet": "https://s.altnet.rippletest.net:51234",
    "devnet": "https://s.devnet.rippletest.net:51234",
    "mainnet": "https://xrplcluster.com",
}

# A ceiling on any single payment, in XRP. Not a risk model -- a blast-radius
# limit, so a wrong decimal place or a bad unit conversion cannot empty an
# account in one call. Raise it deliberately if a real transfer needs more.
MAX_SINGLE_PAYMENT_XRP = 100.0

# XRPL requires a funded account to keep a base reserve. Sending the full
# balance leaves the account unfunded and unusable.
BASE_RESERVE_XRP = 1.0


@dataclass
class SubmissionRecord:
    """What actually happened, in a form that can be handed to the Covenant
    ledger as external evidence rather than self-report."""
    tx_hash: str
    validated: bool
    engine_result: str
    ledger_index: Optional[int]
    account: str
    destination: str
    amount_xrp: float
    fee_drops: str
    network: str
    submitted_at: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _read_seed_file(path: str, require_strict_perms: bool) -> str:
    if not os.path.exists(path):
        raise XRPSignerError(
            f"No XRP seed file at {path}. Create one containing ONLY the seed "
            f"(starts with 's'), then: chmod 600 {path}")
    st = os.stat(path)
    mode = stat.S_IMODE(st.st_mode)
    if mode & 0o077:
        msg = (f"Seed file {path} is mode {oct(mode)} -- readable by group or "
               f"others. An XRP seed is the whole account. Run: chmod 600 {path}")
        if require_strict_perms:
            raise XRPSignerError(msg)
        print(f"WARNING: {msg}")
    with open(path, "r") as fh:
        seed = fh.read().strip()
    if not seed:
        raise XRPSignerError(f"Seed file {path} is empty.")
    if not seed.startswith("s"):
        raise XRPSignerError(
            f"Seed file {path} does not look like an XRP seed (expected it to "
            f"start with 's'). Refusing to guess -- check you did not paste an "
            f"address or a public key.")
    return seed


class XRPSigner:
    """Holds one XRPL account's signing authority.

    Construct with a seed FILE path, not a seed. Testnet unless mainnet is
    explicitly and doubly requested.
    """

    def __init__(self, seed_path: str, network: str = "testnet",
                 allow_mainnet: bool = False,
                 max_payment_xrp: float = MAX_SINGLE_PAYMENT_XRP):
        if not XRPL_AVAILABLE:
            raise XRPSignerError(
                f"xrpl-py is not importable ({XRPL_IMPORT_ERROR}). "
                f"Install it:  pip install xrpl-py")
        if network not in NETWORKS:
            raise XRPSignerError(
                f"Unknown network {network!r}. Choose one of: {', '.join(NETWORKS)}")
        if network == "mainnet" and not allow_mainnet:
            raise XRPSignerError(
                "network='mainnet' requires allow_mainnet=True as a separate, "
                "explicit argument. This is real money with no reversal and no "
                "recovery; one mistyped config value should not be the only "
                "thing preventing it.")
        if not allow_mainnet and network != "mainnet":
            pass  # normal testnet path

        self.network = network
        self.is_mainnet = (network == "mainnet")
        self.max_payment_xrp = float(max_payment_xrp)
        self.endpoint = NETWORKS[network]
        self.client = JsonRpcClient(self.endpoint)

        seed = _read_seed_file(seed_path, require_strict_perms=self.is_mainnet)
        self.wallet = Wallet.from_seed(seed)
        del seed

        print(f"XRPSigner ready: account={self.wallet.classic_address} "
              f"network={self.network}"
              + ("  *** MAINNET -- REAL FUNDS ***" if self.is_mainnet else ""))

    # -- read paths ------------------------------------------------------

    @property
    def address(self) -> str:
        return self.wallet.classic_address

    def get_balance_xrp(self) -> float:
        """Current balance from the ledger. Raises if the account is unfunded
        -- an unfunded XRPL account does not exist yet and cannot send."""
        try:
            resp = self.client.request(
                AccountInfo(account=self.wallet.classic_address,
                            ledger_index="validated"))
        except Exception as e:
            raise XRPSignerError(f"Could not reach {self.endpoint}: {e}") from e
        if not resp.is_successful():
            raise XRPSignerError(
                f"account_info failed for {self.wallet.classic_address}: "
                f"{resp.result.get('error_message', resp.result)}. "
                f"On testnet, fund it at https://xrpl.org/xrp-testnet-faucet.html")
        return float(drops_to_xrp(resp.result["account_data"]["Balance"]))

    # -- write path ------------------------------------------------------

    def send_xrp(self, destination: str, amount_xrp: float,
                 destination_tag: Optional[int] = None,
                 dry_run: bool = True,
                 confirmation: Optional[str] = None,
                 policy_path: str = "xrp_mainnet_policy.json",
                 spend_ledger_path: str = "xrp_spend_ledger.jsonl") -> Dict[str, Any]:
        """Sign and (unless dry_run) submit one XRP payment.

        dry_run DEFAULTS TO TRUE. The caller must pass dry_run=False to move
        anything. A dry run performs every check and the full signing step, then
        returns the signed blob WITHOUT submitting -- so the thing you inspect
        is the thing that would have gone out, not an approximation of it.

        ON MAINNET every payment additionally passes through
        covenant_xrp_mainnet.authorize_mainnet_payment first: testnet proof,
        address checksum, allowlist, destination tag, per-payment ceiling,
        daily and lifetime ceilings, destination activation, and a confirmation
        phrase derived from this exact payment. See item AM.
        """
        guard = None
        if self.is_mainnet:
            from covenant_xrp_mainnet import authorize_mainnet_payment, SpendLedger
            guard = authorize_mainnet_payment(
                destination=destination, amount_xrp=amount_xrp,
                policy_path=policy_path, spend_ledger_path=spend_ledger_path,
                destination_tag=destination_tag, confirmation=confirmation,
                client=self.client)
            destination = guard["classic_destination"]
            destination_tag = guard["destination_tag"]

        # FIXED v8.13 -- see PATCH LOG item AM. This used to be
        # `destination.startswith("r")`, which is not validation. Every XRPL
        # classic address carries a 4-byte checksum precisely so a mistyped or
        # truncated one can be caught before the money moves; a prefix test
        # catches neither. The old check accepted the string
        # 'rDest0000000000000000000000000' -- which appears in this module's own
        # earlier test file, where it passed as a destination.
        try:
            from covenant_xrp_mainnet import validate_destination
            destination, _embedded_tag = validate_destination(destination)
            if _embedded_tag is not None and destination_tag is None:
                destination_tag = _embedded_tag
        except ImportError:
            # Fail CLOSED. The alternative is silently reverting to the weak
            # check on the one path where being wrong is unrecoverable.
            raise XRPSignerError(
                "covenant_xrp_mainnet.py is required for address validation "
                "and is not importable. Refusing to send to an unvalidated "
                "address.")
        if destination == self.wallet.classic_address:
            raise XRPSignerError("Refusing to send to self -- likely a mistake.")
        try:
            amount_xrp = float(amount_xrp)
        except (TypeError, ValueError):
            raise XRPSignerError(f"amount_xrp must be numeric, got {amount_xrp!r}")
        if not (amount_xrp == amount_xrp) or amount_xrp in (float("inf"), float("-inf")):
            raise XRPSignerError("amount_xrp must be finite.")
        if amount_xrp <= 0:
            raise XRPSignerError(f"amount_xrp must be positive, got {amount_xrp}")
        if amount_xrp > self.max_payment_xrp:
            raise XRPSignerError(
                f"Payment of {amount_xrp} XRP exceeds the single-payment ceiling "
                f"of {self.max_payment_xrp} XRP. Raise max_payment_xrp "
                f"deliberately if this is intended.")

        balance = self.get_balance_xrp()
        if amount_xrp > balance - BASE_RESERVE_XRP:
            raise XRPSignerError(
                f"Payment of {amount_xrp} XRP would leave less than the "
                f"{BASE_RESERVE_XRP} XRP base reserve (balance {balance}). "
                f"An account below reserve cannot transact.")

        payment = Payment(
            account=self.wallet.classic_address,
            destination=destination,
            amount=xrp_to_drops(amount_xrp),
            **({"destination_tag": destination_tag} if destination_tag is not None else {}),
        )

        try:
            filled = autofill(payment, self.client)
            signed = sign(filled, self.wallet)
        except Exception as e:
            raise XRPSignerError(f"Signing failed: {type(e).__name__}: {e}") from e

        # item AR -- bind the hash to the reservation BEFORE submitting. If the
        # process dies between here and confirmation, this is the only thing
        # that makes the reservation reconcilable instead of a permanent unknown.
        if guard is not None and not dry_run:
            from covenant_xrp_mainnet import SpendLedger as _SL
            _SL(guard["spend_ledger_path"]).attach_hash(
                guard["reservation_id"], signed.get_hash())

        if dry_run:
            return {
                "dry_run": True,
                "would_send_xrp": amount_xrp,
                "from": self.wallet.classic_address,
                "to": destination,
                "network": self.network,
                "fee_drops": str(filled.fee),
                "sequence": filled.sequence,
                "tx_hash_if_submitted": signed.get_hash(),
                "note": "Nothing was submitted. Pass dry_run=False to send.",
            }

        # ITEM AP -- the headroom was RESERVED inside authorize_mainnet_payment,
        # atomically and under lock, before this transaction was ever signed.
        # Nothing is recorded here on the way out: the reservation already
        # counts against the daily and lifetime ceilings, so a crash between
        # here and settlement leaves the money counted as spent. That is the
        # safe direction -- a too-tight limit is a refusal you can investigate,
        # a too-loose one is money already gone.
        try:
            resp = submit_and_wait(signed, self.client)
        except Exception as e:
            # DELIBERATELY NOT RELEASED. This error is ambiguous: the payment may
            # not have gone out, or it may have landed and the confirmation was
            # lost. Releasing the reservation here would hand the headroom back
            # for a payment that may already be on the ledger, which is exactly
            # how a double-send happens.
            if guard is not None:
                from covenant_xrp_mainnet import SpendLedger as _SL
                _SL(guard["spend_ledger_path"]).record(
                    reservation_id=guard["reservation_id"], drops=0, amount_xrp=0.0,
                    state="ambiguous", submitted_at=time.time(),
                    tx_hash=signed.get_hash(), error=f"{type(e).__name__}: {e}"[:200])
            raise XRPSignerError(
                f"Submission failed: {type(e).__name__}: {e}. "
                f"IMPORTANT: this may mean the transaction did not go out, OR "
                f"that it went out and the confirmation was lost. Check "
                f"account_tx for hash {signed.get_hash()} before retrying -- "
                f"a blind retry can double-send. The reserved amount is left "
                f"counted against your limits until you resolve this.") from e

        result = resp.result
        meta = result.get("meta") or {}
        engine = meta.get("TransactionResult") if isinstance(meta, dict) else ""
        record = SubmissionRecord(
            tx_hash=result.get("hash", signed.get_hash()),
            validated=bool(result.get("validated", False)),
            engine_result=engine or result.get("engine_result", "unknown"),
            ledger_index=result.get("ledger_index"),
            account=self.wallet.classic_address,
            destination=destination,
            amount_xrp=amount_xrp,
            fee_drops=str(filled.fee),
            network=self.network,
            submitted_at=time.time(),
        )
        if record.engine_result != "tesSUCCESS":
            # A DEFINITE non-send: the ledger returned a terminal rejection, so
            # nothing moved and the reserved headroom can safely go back. This
            # is the ONLY release path -- it exists because the outcome is
            # unambiguous, unlike the exception branch above.
            if guard is not None:
                from covenant_xrp_mainnet import SpendLedger as _SL
                _SL(guard["spend_ledger_path"]).release(
                    guard["reservation_id"],
                    f"ledger rejected: {record.engine_result}")
            raise XRPSignerError(
                f"Ledger rejected the payment: {record.engine_result} "
                f"(hash {record.tx_hash}). Nothing moved; the reserved amount "
                f"has been returned to your remaining limit.")
        if guard is not None:
            from covenant_xrp_mainnet import SpendLedger as _SL
            _SL(guard["spend_ledger_path"]).settle(
                guard["reservation_id"], tx_hash=record.tx_hash,
                engine_result=record.engine_result)
        out = record.to_dict()
        if guard is not None:
            out["reservation_id"] = guard["reservation_id"]
        return out


def create_testnet_seed_file(path: str) -> str:
    """Generate a NEW testnet keypair and write the seed to `path` at mode 0600.

    Testnet only, and it says so: this never touches mainnet and the resulting
    account holds nothing until it is funded from the public faucet. Refuses to
    overwrite an existing file -- silently replacing a seed destroys access to
    whatever the old one held.
    """
    if not XRPL_AVAILABLE:
        raise XRPSignerError(f"xrpl-py is not importable ({XRPL_IMPORT_ERROR}).")
    if os.path.exists(path):
        raise XRPSignerError(
            f"{path} already exists. Refusing to overwrite a seed file -- if the "
            f"old seed is lost, so is everything the account held.")
    w = Wallet.create()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as fh:
        fh.write(w.seed + "\n")
    print(f"Testnet seed written to {path} (mode 0600).")
    print(f"  address: {w.classic_address}")
    print(f"  fund it: https://xrpl.org/xrp-testnet-faucet.html")
    return w.classic_address


if __name__ == "__main__":
    print(__doc__)
    print("\nThis is a library module. Typical first use:\n")
    print("  python3 -c \"import covenant_xrp_signer as x; "
          "x.create_testnet_seed_file('xrp_testnet.seed')\"")
    print("\nThen fund the printed address at the testnet faucet, and:\n")
    print("  s = XRPSigner('xrp_testnet.seed')          # testnet by default")
    print("  s.get_balance_xrp()")
    print("  s.send_xrp('rDest...', 1.0)                # dry run by default")
    print("  s.send_xrp('rDest...', 1.0, dry_run=False) # actually sends")
