"""
covenant_xrp_mainnet.py -- the controls that stand between a signing key and
an irreversible mistake.

NEW v8.13 -- see PATCH LOG item AM in covenant_unified_v8.py.

WHY THIS IS A SEPARATE MODULE
-----------------------------
covenant_xrp_signer.py knows how to sign. That is a mechanical problem and it
is solved. This module is about everything that can go wrong when the signing
is correct: right signature, wrong address; right address, missing tag; right
transaction, hundredth time today. None of those are cryptography failures and
none of them are recoverable.

XRP HAS NO CHARGEBACK, NO REVERSAL, NO SUPPORT LINE. A payment that confirms is
final. Every control here exists because the failure it prevents is permanent.

THE FIVE WAYS PEOPLE ACTUALLY LOSE XRP
--------------------------------------
1. A mistyped destination that still looks like an address. Every classic
   address carries a checksum; validating it catches single-character errors
   that "starts with r" does not. The old signer accepted
   'rDest0000000000000000000000000'.
2. Sending to an exchange without a DESTINATION TAG. The exchange receives
   funds it cannot attribute to any customer. This is the single most common
   permanent loss in XRP and it looks exactly like success -- the ledger
   reports tesSUCCESS.
3. Sending to an unactivated account below the base reserve. The transaction
   fails, or activates an account nobody controls.
4. A compromised or confused process sending somewhere new. An allowlist means
   a key alone is not enough.
5. Repetition. One correct payment is fine. The same correct payment two
   hundred times is not, and per-transaction limits do not see it.

WHAT THIS MODULE DOES NOT DO
----------------------------
It does not make an unrun code path safe. Controls are guesses until the thing
they wrap has executed at least once. See require_testnet_proof().
"""

from __future__ import annotations

import os
import sys
import json
import time
import stat
import uuid
import hashlib

# P9 (applied 2026-08-27, on L's instruction). The policy-file permission
# control below used `stat.S_IMODE(...) & 0o077`. That is exactly right on
# POSIX and meaningless on NTFS, where st_mode reports 0o666 for any writable
# file whatever the ACL says, and os.chmod only toggles the read-only
# attribute. So on Windows the check was a CONSTANT: authorize_mainnet_payment
# refused on this machine always, and the branch was unreachable in the
# passing direction. See docs/P9_WINDOWS_OWNER_ONLY.md.
#
# ops/ is not a package, so it goes on the path explicitly rather than
# depending on the caller's working directory.
_OPS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ops")
if _OPS_DIR not in sys.path:
    sys.path.insert(0, _OPS_DIR)
try:
    from owner_only import require_owner_only, OwnerOnlyError
    _OWNER_ONLY_IMPORT_ERR = None
except Exception as _e:                                  # pragma: no cover
    require_owner_only = None
    OwnerOnlyError = Exception
    _OWNER_ONLY_IMPORT_ERR = _e
from decimal import Decimal, InvalidOperation
from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, Any, List, Tuple

try:
    from xrpl.core import addresscodec
    from xrpl.clients import JsonRpcClient
    from xrpl.models.requests import AccountInfo
    XRPL_AVAILABLE = True
except Exception as _e:  # pragma: no cover
    XRPL_AVAILABLE = False
    _IMPORT_ERR = f"{type(_e).__name__}: {_e}"


# ---------------------------------------------------------------------------
# Cross-process locking -- portable, and LOUD when it is not available
# ---------------------------------------------------------------------------
#
# NEW v8.16 -- see PATCH LOG item AQ. `import fcntl` was unconditional at module
# top level, so on native Windows this module did not merely fail to LOCK, it
# failed to IMPORT -- taking the address checksum, the allowlist, the
# destination-tag rule and every other control down with it. The failure is at
# least loud, but it makes the whole guard layer unavailable on a platform
# rather than degraded.
#
# The important half of this fix is what it refuses to do. The tempting
# "portable" answer is a try/except around the import that falls through to a
# no-op lock, and that is strictly worse than an ImportError: it restores the
# item AP concurrency breach (60 XRP through a 20 XRP cap) while every test
# still passes and the module still imports. A lock that silently does nothing
# is the same anti-pattern as a control that fails open.
#
# So: use fcntl where it exists, msvcrt where it exists, and if NEITHER is
# available refuse to construct a SpendLedger at all, naming the reason.
_LOCK_IMPL = None
try:
    import fcntl as _fcntl
    _LOCK_IMPL = "fcntl"
except ImportError:
    _fcntl = None
    try:
        import msvcrt as _msvcrt
        _LOCK_IMPL = "msvcrt"
    except ImportError:
        _msvcrt = None


def _lock_file(fh) -> None:
    if _LOCK_IMPL == "fcntl":
        _fcntl.flock(fh.fileno(), _fcntl.LOCK_EX)
    elif _LOCK_IMPL == "msvcrt":
        # Windows byte-range lock over EXACTLY byte 0.
        #
        # The seek(0) is load-bearing, not decoration. msvcrt.locking locks a
        # range starting at the handle's CURRENT offset, and this handle is
        # opened "a+", which positions at end-of-file -- measured: a fresh "a+"
        # handle on a 10-byte file reports tell() == 10. Without the seek, two
        # processes would lock byte 10 and byte 0, or byte 137 and byte 0,
        # depending on whatever the file happened to contain. They would never
        # contend, every lock would succeed instantly, and the result would be
        # the item AP breach again -- with a locking call right there in the
        # traceback to make it look protected.
        #
        # Re-seeking inside the retry loop matters too: an intervening failed
        # attempt can leave the offset moved.
        #
        # LK_LOCK itself blocks, retrying ~10 times at 1s intervals before
        # raising, so this outer deadline bounds total wait rather than
        # failing on first contention.
        deadline = time.time() + 30.0
        while True:
            try:
                fh.seek(0)
                _msvcrt.locking(fh.fileno(), _msvcrt.LK_LOCK, 1)
                return
            except OSError:
                if time.time() > deadline:
                    raise MainnetGuardError(
                        "Timed out waiting for the spend-ledger lock (30s). "
                        "Another process may be stuck mid-payment; do not bypass "
                        "this -- check for unsettled reservations first.")
                time.sleep(0.1)
    else:
        raise MainnetGuardError(
            "No cross-process file locking is available on this platform "
            "(neither fcntl nor msvcrt could be imported). Refusing to operate "
            "the spend ledger without it: unlocked read-check-write is not a "
            "spending limit, and was measured passing 60 XRP through a 20 XRP "
            "cap. See PATCH LOG item AP.")


def _unlock_file(fh) -> None:
    if _LOCK_IMPL == "fcntl":
        _fcntl.flock(fh.fileno(), _fcntl.LOCK_UN)
    elif _LOCK_IMPL == "msvcrt":
        try:
            # Same offset the lock was taken at, for the same reason. Unlocking
            # a different range than was locked leaves the lock held.
            fh.seek(0)
            _msvcrt.locking(fh.fileno(), _msvcrt.LK_UNLCK, 1)
        except OSError:
            pass


class MainnetGuardError(Exception):
    """Every refusal in this module. Loud, never a silent skip: a control that
    fails open is worse than no control, because it is believed."""


# ---------------------------------------------------------------------------
# Exact amounts -- integer drops, never float
# ---------------------------------------------------------------------------
#
# NEW v8.15 -- see PATCH LOG item AP. XRP has EXACTLY six decimal places; one
# drop is 0.000001 XRP and the ledger itself counts in integer drops. Every
# amount and every limit is therefore carried here as an int number of drops,
# and float is used nowhere in any comparison.
#
# Confirmed by measurement, not by principle: 1.1 + 2.2 evaluates to
# 3.3000000000000003, which is ABOVE a 3.3 cap that the payments exactly reach,
# and 0.7 * 3 gives 2.0999999999999996, which is BELOW a 2.1 cap the payments
# exactly reach. Both directions are wrong and which one occurs depends on the
# amounts, so a limit expressed in float is decided partly by rounding noise.
#
# A second, sharper defect the same change closes: 0.0000001 XRP passed the old
# `amount_xrp > 0` check while being a TENTH of a drop -- an amount that cannot
# be represented on the ledger at all.
DROPS_PER_XRP = 1_000_000


def xrp_to_drops_exact(amount) -> int:
    """Convert an XRP amount to integer drops, refusing anything the ledger
    cannot represent. Accepts str/int/Decimal/float; a float is routed through
    its repr so 0.1 means 0.1 and not its binary expansion."""
    if isinstance(amount, bool):
        raise MainnetGuardError("amount must be numeric, got a bool")
    try:
        d = Decimal(amount) if isinstance(amount, (int, Decimal)) else Decimal(repr(amount)) \
            if isinstance(amount, float) else Decimal(str(amount).strip())
    except (InvalidOperation, TypeError, ValueError):
        raise MainnetGuardError(f"amount is not a valid decimal number: {amount!r}")
    if not d.is_finite():
        raise MainnetGuardError(f"amount must be finite, got {amount!r}")
    scaled = d * DROPS_PER_XRP
    if scaled != scaled.to_integral_value():
        raise MainnetGuardError(
            f"{d} XRP is finer than one drop (0.000001 XRP). The XRP Ledger "
            f"cannot represent it, so this payment could never be sent as written.")
    return int(scaled)


def drops_to_xrp_str(drops: int) -> str:
    return str((Decimal(int(drops)) / DROPS_PER_XRP).quantize(Decimal("0.000001")))


# Exchange deposit addresses REQUIRE a destination tag. Sending without one is
# a permanent loss that reports success. This list is not exhaustive and cannot
# be -- the policy below defaults to REQUIRING a tag unless a destination is
# explicitly marked as not needing one, rather than the reverse.
KNOWN_TAG_REQUIRED_HINTS = (
    "exchange", "deposit", "custodian", "binance", "kraken", "coinbase",
    "bitstamp", "bitso", "uphold", "gatehub",
)


# ---------------------------------------------------------------------------
# Address validation
# ---------------------------------------------------------------------------

def validate_destination(address: str) -> Tuple[str, Optional[int]]:
    """Return (classic_address, destination_tag_from_xaddress).

    Uses the XRPL CHECKSUM, not a prefix check. A classic address is
    base58 with a 4-byte checksum, so a single mistyped character fails here
    instead of at the point where the money is already gone. The previous
    signer checked only that the string began with 'r', which accepted
    'rDest0000000000000000000000000'.

    X-addresses are accepted and decoded. They exist precisely to carry the
    destination tag inside the address so it cannot be forgotten in transit,
    which makes them the safest thing to paste.
    """
    if not XRPL_AVAILABLE:
        raise MainnetGuardError(f"xrpl-py not importable ({_IMPORT_ERR})")
    if not isinstance(address, str) or not address.strip():
        raise MainnetGuardError("Destination address is empty.")
    address = address.strip()

    if addresscodec.is_valid_xaddress(address):
        classic, tag, is_test = addresscodec.xaddress_to_classic_address(address)
        return classic, tag

    if not addresscodec.is_valid_classic_address(address):
        raise MainnetGuardError(
            f"'{address}' is not a valid XRPL address -- the checksum does not "
            f"match. This is what a mistyped or truncated address looks like. "
            f"Do not 'fix' it by hand; re-copy it from the source.")
    return address, None


# ---------------------------------------------------------------------------
# Policy file
# ---------------------------------------------------------------------------

@dataclass
class Destination:
    address: str
    label: str
    destination_tag: Optional[int] = None
    tag_not_required: bool = False
    max_per_payment_xrp: float = 0.0


@dataclass
class MainnetPolicy:
    """Loaded from a JSON file at mode 0600. Deliberately a FILE and not
    arguments: a policy that lives in a call site is a policy that changes
    whenever someone edits the call site."""
    destinations: List[Destination] = field(default_factory=list)
    max_per_payment_xrp: float = 10.0
    max_per_day_xrp: float = 50.0
    max_lifetime_xrp: float = 500.0
    require_confirmation_phrase: bool = True

    @staticmethod
    def load(path: str) -> "MainnetPolicy":
        if not os.path.exists(path):
            raise MainnetGuardError(
                f"No mainnet policy at {path}. Mainnet sending requires an "
                f"explicit written policy -- create one with "
                f"write_policy_template('{path}') and edit it.")
        # P9. Fails closed twice over: if the control itself cannot be loaded,
        # or if it cannot read the ACL, this refuses rather than assuming the
        # file is safe. It is strictly stronger than the mode bit it replaces
        # -- POSIX behaviour is byte-for-byte identical, and on Windows it goes
        # from "always refuse" to "refuse unless the ACL is actually
        # restricted", which is the check the mode bit was standing in for.
        if require_owner_only is None:                    # pragma: no cover
            raise MainnetGuardError(
                f"owner_only is not importable ({_OWNER_ONLY_IMPORT_ERR}). The "
                f"policy-file permission control cannot be evaluated, so this "
                f"refuses. A control that cannot run is not a control that "
                f"passed.")
        try:
            require_owner_only(path)
        except OwnerOnlyError as e:
            raise MainnetGuardError(
                f"{e} Anything that can edit this file can raise your own "
                f"spending limits.")
        with open(path) as fh:
            raw = json.load(fh)
        dests = [Destination(**d) for d in raw.get("destinations", [])]
        if not dests:
            raise MainnetGuardError(
                f"Policy {path} has no destinations. Mainnet sends only to "
                f"addresses listed here -- an empty list means no sends, which "
                f"is the correct default, not a bug.")
        for d in dests:
            classic, xtag = validate_destination(d.address)
            if classic != d.address:
                raise MainnetGuardError(
                    f"Policy destination '{d.label}' is an X-address; store the "
                    f"classic form ({classic}) and its tag ({xtag}) explicitly "
                    f"so the tag is visible in the policy rather than encoded.")
        pol = MainnetPolicy(
            destinations=dests,
            max_per_payment_xrp=float(raw.get("max_per_payment_xrp", 10.0)),
            max_per_day_xrp=float(raw.get("max_per_day_xrp", 50.0)),
            max_lifetime_xrp=float(raw.get("max_lifetime_xrp", 500.0)),
            require_confirmation_phrase=bool(raw.get("require_confirmation_phrase", True)),
        )
        if pol.max_per_payment_xrp > pol.max_per_day_xrp:
            raise MainnetGuardError(
                "max_per_payment_xrp exceeds max_per_day_xrp -- the daily limit "
                "would never bind. Fix the policy rather than relying on the "
                "tighter one happening to be checked first.")
        return pol

    def find(self, classic_address: str) -> Destination:
        for d in self.destinations:
            if d.address == classic_address:
                return d
        raise MainnetGuardError(
            f"{classic_address} is not in the mainnet allowlist. Add it to the "
            f"policy file deliberately, with a label, after checking it against "
            f"the source you got it from. A signing key alone must not be "
            f"enough to move funds somewhere new.")


def write_policy_template(path: str) -> None:
    if os.path.exists(path):
        raise MainnetGuardError(f"{path} already exists; refusing to overwrite a policy.")
    tmpl = {
        "_comment": "Mainnet spending policy. Every send is checked against this.",
        "destinations": [
            {"address": "rEXAMPLEreplacewithARealCheckedAddress",
             "label": "what this address is, in words",
             "destination_tag": None,
             "tag_not_required": False,
             "max_per_payment_xrp": 5.0}
        ],
        "max_per_payment_xrp": 10.0,
        "max_per_day_xrp": 50.0,
        "max_lifetime_xrp": 500.0,
        "require_confirmation_phrase": True,
    }
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as fh:
        json.dump(tmpl, fh, indent=2)
    print(f"Policy template written to {path} (mode 0600). Edit it before use.")


# ---------------------------------------------------------------------------
# Spend ledger -- cumulative limits, which per-payment caps cannot see
# ---------------------------------------------------------------------------

class SpendLedger:
    """Append-only record of every mainnet payment, enforcing daily and lifetime
    ceilings under an exclusive file lock.

    REWRITTEN v8.15 -- see PATCH LOG item AP. Two confirmed defects, both of
    which meant the ceilings were advisory rather than binding.

    NOTHING RESERVED AT AUTHORIZATION. authorize_mainnet_payment checked the
    limits and wrote nothing, so the headroom it had just verified was still
    free for the next caller. Measured: five consecutive authorizations for
    10 XRP each, 50 XRP total, against a 20 XRP daily cap -- all five passed,
    because checking is not holding.

    NO LOCKING. Read-check-write across processes with no mutual exclusion is
    not a limit, it is a suggestion. Measured with six concurrent processes and
    a realistic signing delay between authorize and record: SIX authorizations
    for 60 XRP against the same 20 XRP cap, cap breached by 3x.

    The design is now RESERVE-THEN-SETTLE. reserve() takes an exclusive lock,
    re-reads the whole ledger, checks the ceilings and appends a PENDING row
    before releasing -- so the check and the write are one atomic act and a
    concurrent process sees the reservation. Pending rows COUNT toward the
    ceilings.

    A crash between reserve and settle therefore leaves the reservation
    standing, and the money stays counted as spent. That direction is
    deliberate: the alternative -- expiring unsettled reservations -- would
    release headroom for a payment that may well have gone out, and the failure
    mode of a too-tight limit is a refusal you can investigate, while the
    failure mode of a too-loose one is money that is already gone. release() is
    provided for the one case where non-delivery is CERTAIN (signing failed
    before submission), and is never called on an ambiguous error.
    """

    def __init__(self, path: str):
        if _LOCK_IMPL is None:
            raise MainnetGuardError(
                "No cross-process file locking is available on this platform "
                "(neither fcntl nor msvcrt). A spend ledger without locking is "
                "not a spending limit -- see PATCH LOG items AP and AQ. Refusing "
                "to construct one rather than silently running unprotected.")
        self.path = path
        if not os.path.exists(path):
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            os.close(fd)
        self.lock_path = path + ".lock"
        # Ensure the lock file contains at least one byte. Windows permits
        # locking a range past end-of-file, but a zero-length file makes "byte
        # 0" a range that exists only by that permission; writing one byte makes
        # the contended region unambiguous on every platform. Done once, at
        # construction, and never rewritten.
        try:
            if not os.path.exists(self.lock_path) or os.path.getsize(self.lock_path) == 0:
                fd = os.open(self.lock_path, os.O_WRONLY | os.O_CREAT, 0o600)
                try:
                    os.write(fd, b"L")
                finally:
                    os.close(fd)
        except OSError as e:
            raise MainnetGuardError(
                f"Cannot prepare the spend-ledger lock file {self.lock_path}: {e}")

    # -- locking ---------------------------------------------------------

    def _locked(self):
        """Exclusive advisory lock held across the whole read-check-write."""
        class _L:
            def __init__(self, lp):
                self.lp = lp
                self.fh = None
            def __enter__(self):
                self.fh = open(self.lp, "a+")
                try:
                    _lock_file(self.fh)
                except Exception:
                    self.fh.close()
                    raise
                return self
            def __exit__(self, *exc):
                try:
                    _unlock_file(self.fh)
                finally:
                    self.fh.close()
                return False
        return _L(self.lock_path)

    # -- reading ---------------------------------------------------------

    def _read_unlocked(self):
        out = []
        with open(self.path) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    # A corrupt line means the totals below are computed from an
                    # incomplete history, which would read as MORE headroom than
                    # really exists. Refuse rather than under-count.
                    raise MainnetGuardError(
                        f"Corrupt line in spend ledger {self.path}. Refusing to "
                        f"compute limits from an incomplete record.")
        return out

    @staticmethod
    def _counts(records):
        """Drops spent today and over the lifetime. PENDING rows count: a
        reservation is money presumed gone until proven otherwise."""
        cutoff = time.time() - 86400
        today = life = 0
        for r in records:
            if r.get("state") == "released":
                continue
            drops = int(r.get("drops", 0))
            life += drops
            if r.get("submitted_at", 0) >= cutoff:
                today += drops
        return today, life

    def totals_drops(self):
        with self._locked():
            return self._counts(self._read_unlocked())

    def spent_today(self) -> float:
        return int(self.totals_drops()[0]) / DROPS_PER_XRP

    def spent_lifetime(self) -> float:
        return int(self.totals_drops()[1]) / DROPS_PER_XRP

    # -- writing ---------------------------------------------------------

    def _append_unlocked(self, row):
        with open(self.path, "a") as fh:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
            fh.flush()
            os.fsync(fh.fileno())

    def reserve(self, drops: int, max_day_drops: int, max_life_drops: int,
                **meta) -> str:
        """Atomically check the ceilings and hold the headroom. Returns a
        reservation id, or raises MainnetGuardError if it does not fit."""
        drops = int(drops)
        with self._locked():
            rows = self._read_unlocked()
            today, life = self._counts(rows)
            # item AR -- if unsettled reservations are part of why this refusal
            # happened, SAY SO here. An operator hitting an unexplained limit
            # should not have to already know that orphaned reservations exist
            # in order to go looking for them.
            settled_ids = {r.get("reservation_id") for r in rows
                           if r.get("state") in ("settled", "release_marker")}
            orphan_drops = sum(int(r.get("drops", 0)) for r in rows
                               if r.get("state") == "pending"
                               and r.get("reservation_id") not in settled_ids)
            hint = ""
            if orphan_drops:
                hint = (f"\n  NOTE: {drops_to_xrp_str(orphan_drops)} XRP of that is "
                        f"UNSETTLED RESERVATIONS, not confirmed payments. If a send "
                        f"crashed part-way, its hold is still counted (deliberately). "
                        f"Run SpendLedger(path).reconciliation_report() to see and "
                        f"resolve them.")
            if today + drops > max_day_drops:
                raise MainnetGuardError(
                    f"This payment ({drops_to_xrp_str(drops)} XRP) would bring today's "
                    f"total to {drops_to_xrp_str(today + drops)} XRP, past the daily "
                    f"ceiling of {drops_to_xrp_str(max_day_drops)} XRP. "
                    f"Already committed or reserved today: {drops_to_xrp_str(today)} XRP."
                    + hint)
            if life + drops > max_life_drops:
                raise MainnetGuardError(
                    f"This payment ({drops_to_xrp_str(drops)} XRP) would bring the "
                    f"lifetime total to {drops_to_xrp_str(life + drops)} XRP, past the "
                    f"ceiling of {drops_to_xrp_str(max_life_drops)} XRP. "
                    f"Already committed or reserved: {drops_to_xrp_str(life)} XRP."
                    + hint)
            rid = uuid.uuid4().hex
            row = dict(meta)
            row.update({"reservation_id": rid, "drops": drops,
                        "amount_xrp": drops / DROPS_PER_XRP,
                        "state": "pending", "submitted_at": time.time()})
            self._append_unlocked(row)
            return rid

    def settle(self, reservation_id: str, tx_hash: str = "",
               engine_result: str = "") -> None:
        """Mark a reservation as a confirmed send. Does NOT change the amount
        counted -- the reservation already counted -- so settling can never
        free headroom."""
        with self._locked():
            self._append_unlocked({"reservation_id": reservation_id, "drops": 0,
                                   "amount_xrp": 0.0, "state": "settled",
                                   "tx_hash": tx_hash, "engine_result": engine_result,
                                   "submitted_at": time.time()})

    def repair_partial_releases(self) -> int:
        """Finish any release that crashed between its marker and the rewrite.

        item AT -- release() is two writes: an append-only marker, then a
        rewrite of the pending row. The marker is written first deliberately, so
        the INTENT survives a crash; this completes it. Idempotent, and safe to
        run at any time: it only ever moves a row that already has a durable
        release marker, never invents one.
        """
        with self._locked():
            rows = self._read_unlocked()
            marked = {r.get("releases") for r in rows
                      if r.get("state") == "release_marker" and r.get("releases")}
            fixed = 0
            for r in rows:
                if r.get("state") == "pending" and r.get("reservation_id") in marked:
                    r["state"] = "released"
                    r.setdefault("release_reason", "repaired: marker found without rewrite")
                    fixed += 1
            if fixed:
                self._rewrite_unlocked(rows)
            return fixed

    def _rewrite_unlocked(self, rows) -> None:
        tmp = self.path + ".tmp"
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as fh:
            for r in rows:
                fh.write(json.dumps(r, sort_keys=True) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, self.path)

    def release(self, reservation_id: str, reason: str) -> None:
        """Return reserved headroom. ONLY for a definite non-send -- signing
        failed before anything reached the network. Never call this on a
        submission that errored ambiguously: if the payment may have landed,
        releasing its headroom authorizes a second one."""
        with self._locked():
            self._append_unlocked({"reservation_id": reservation_id, "drops": 0,
                                   "amount_xrp": 0.0, "state": "release_marker",
                                   "releases": reservation_id, "reason": reason,
                                   "submitted_at": time.time()})
            rows = self._read_unlocked()
            for r in rows:
                if r.get("reservation_id") == reservation_id and r.get("state") == "pending":
                    r["state"] = "released"
                    r["release_reason"] = reason
            self._rewrite_unlocked(rows)

    def pending_reservations(self, older_than_s: float = 0.0):
        """Every reservation that has neither settled nor been released.

        NEW v8.16 -- see PATCH LOG item AR. Holding an unsettled reservation
        against the ceilings is the correct default (item AP), but it was
        INVISIBLE: a crash between reserve and settle silently and permanently
        consumed headroom, and the operator's only symptom was a limit that
        refused payments for no apparent reason, tightening a little more with
        every crash. A conservative default is only safe if the state it creates
        can be seen and resolved.

        Returns rows with an `age_s` and, where the payment reached signing, the
        `tx_hash` needed to look it up on-ledger.
        """
        with self._locked():
            rows = self._read_unlocked()
        # FIXED v8.18 -- see PATCH LOG item AT. This used to treat a
        # release_marker as proof a reservation was resolved, while _counts()
        # only stops counting a row whose own state is "released". Those are two
        # different sets, and release() writes the marker BEFORE rewriting the
        # row -- so a crash between the two left the money HELD and INVISIBLE:
        # counted against the ceilings, absent from every report, with
        # reconciliation cheerfully saying "No unsettled reservations".
        # Exactly the defect item AR exists to prevent, reintroduced by AR's own
        # fix. Resolution is now judged by the SAME predicate the counting uses.
        settled = {r.get("reservation_id") for r in rows
                   if r.get("state") == "settled"}
        # attach_hash and the ambiguous-error marker are written as SEPARATE
        # rows, so fold them back onto their reservation -- otherwise the report
        # shows "(never reached signing)" for a payment that was signed and may
        # well be on the ledger, which is the single most misleading thing this
        # report could say.
        annotations = {}
        for r in rows:
            if r.get("state") in ("signed", "ambiguous") and r.get("reservation_id"):
                a = annotations.setdefault(r["reservation_id"], {})
                if r.get("tx_hash"):
                    a["tx_hash"] = r["tx_hash"]
                if r.get("error"):
                    a["error"] = r["error"]
                a["last_state"] = r["state"]
        now = time.time()
        out = []
        for r in rows:
            if r.get("state") != "pending":
                continue
            rid = r.get("reservation_id")
            if rid in settled:
                continue
            age = now - float(r.get("submitted_at", now))
            if age < older_than_s:
                continue
            row = dict(r)
            row.update(annotations.get(rid, {}))
            row["age_s"] = age
            out.append(row)
        return out

    def attach_hash(self, reservation_id: str, tx_hash: str) -> None:
        """Record the transaction hash for a reservation the moment it is
        signed, BEFORE submission.

        item AR -- without this, a crash between signing and submission left a
        reservation with no way to determine what happened: the payment may be
        on the ledger, and there was nothing to look it up by. The hash is
        deterministic at signing time, so writing it here costs one append and
        makes the difference between a reconcilable state and a permanent
        unknown."""
        with self._locked():
            self._append_unlocked({"reservation_id": reservation_id, "drops": 0,
                                   "amount_xrp": 0.0, "state": "signed",
                                   "tx_hash": tx_hash, "submitted_at": time.time()})

    def reconcile_with_ledger(self, client, auto_settle: bool = False) -> dict:
        """Look each unsettled reservation up ON THE LEDGER and report what is
        actually true. Optionally settles the ones that are unambiguous.

        NEW v8.17 -- see PATCH LOG item AS. The requirement that a human resolve
        every orphan is kept, because it is correct, but it was applied to BOTH
        halves of the decision when only one half needs it. The two are not
        symmetric:

          settle()  never changes the counted amount. The hold already counted;
                    settling records why. Getting it wrong costs nothing.
          release() always frees headroom. Getting it wrong authorises a second
                    payment for one that already went out.

        So investigation is automated, and so is settling a payment CONFIRMED
        present on-ledger with tesSUCCESS -- which cannot loosen a limit by even
        one drop. Releasing stays manual, always, no flag to change it. What this
        removes is the toil of hand-checking hashes, not the judgement about
        freeing money.

        `client` needs only .request(); the XRPL Tx lookup is duck-typed so this
        is testable without a network.
        """
        try:
            from xrpl.models.requests import Tx as _Tx
        except Exception as e:
            raise MainnetGuardError(f"xrpl-py required for ledger reconciliation: {e}")

        out = {"found": [], "absent": [], "unknown": [], "settled": []}
        for r in self.pending_reservations():
            rid = r.get("reservation_id")
            h = r.get("tx_hash")
            if not h:
                r["verdict"] = ("never reached signing -- nothing was submitted "
                                "under this reservation, so it is safe to release "
                                "after you confirm no payment left this account")
                out["unknown"].append(r)
                continue
            try:
                resp = client.request(_Tx(transaction=h))
                ok = resp.is_successful()
                res = getattr(resp, "result", {}) or {}
            except Exception as e:
                r["verdict"] = f"ledger lookup failed ({type(e).__name__}: {e}) -- retry"
                out["unknown"].append(r)
                continue
            if ok:
                meta = res.get("meta") or {}
                engine = meta.get("TransactionResult") if isinstance(meta, dict) else ""
                r["engine_result"] = engine
                r["verdict"] = f"FOUND on-ledger ({engine or 'unknown result'})"
                out["found"].append(r)
                if auto_settle and engine == "tesSUCCESS":
                    self.settle(rid, tx_hash=h, engine_result=engine)
                    out["settled"].append(rid)
            else:
                r["verdict"] = ("ABSENT from the ledger. Before releasing, confirm "
                                "the account sequence has not advanced past this "
                                "transaction -- an unsubmitted sequence can still "
                                "be claimed by a later payment")
                out["absent"].append(r)
        return out

    def reconciliation_report(self) -> str:
        """Human-readable summary of what needs resolving, and how."""
        pend = self.pending_reservations()
        if not pend:
            return "No unsettled reservations. Spending limits reflect completed payments only."
        lines = [f"{len(pend)} UNSETTLED RESERVATION(S) counting against your limits:", ""]
        total = 0
        for r in pend:
            total += int(r.get("drops", 0))
            h = r.get("tx_hash") or "(never reached signing)"
            lines.append(
                f"  {r.get('reservation_id','?')[:12]}  "
                f"{drops_to_xrp_str(int(r.get('drops',0))):>14} XRP  "
                f"age {r['age_s']/3600:6.1f}h  to {str(r.get('destination',''))[:20]}  hash {h[:20]}")
        lines += ["",
                  f"  total held: {drops_to_xrp_str(total)} XRP",
                  "",
                  "TO RESOLVE EACH ONE -- check the ledger first, never guess:",
                  "  1. If a hash is shown, look it up (account_tx / an explorer).",
                  "  2. FOUND on-ledger  -> ledger.settle(<id>, tx_hash=..., engine_result=...)",
                  "     The amount stays counted, which is correct: it was spent.",
                  "  3. ABSENT from the ledger, and the account sequence number has NOT",
                  "     advanced past that transaction -> ledger.release(<id>, '<reason>')",
                  "  4. UNSURE -> leave it. A held reservation costs you headroom;",
                  "     releasing one that did send authorises a duplicate payment."]
        return "\n".join(lines)

    def record(self, **fields) -> None:
        """Back-compat direct append, used by tests and by external callers that
        settle their own accounting. Prefer reserve()/settle()."""
        row = dict(fields)
        row.setdefault("state", "pending")
        if "drops" not in row and "amount_xrp" in row:
            row["drops"] = xrp_to_drops_exact(row["amount_xrp"])
        with self._locked():
            self._append_unlocked(row)


# ---------------------------------------------------------------------------
# Testnet proof
# ---------------------------------------------------------------------------

TESTNET_PROOF_FILE = "xrp_testnet_proof.json"

def record_testnet_proof(tx_hash: str, path: str = TESTNET_PROOF_FILE) -> None:
    """Written by test_xrp_live.py after a real testnet submission validates."""
    with open(path, "w") as fh:
        json.dump({"tx_hash": tx_hash, "recorded_at": time.time(),
                   "network": "testnet"}, fh, indent=2)


def require_testnet_proof(path: str = TESTNET_PROOF_FILE) -> Dict[str, Any]:
    """Refuse mainnet until the submission path has actually run once.

    This is not caution for its own sake and it is not a substitute for the
    other controls -- it is the precondition that makes them meaningful. Every
    guard in this module wraps code whose live behaviour is, until testnet runs,
    inferred rather than observed: autofill's fee and sequence assignment,
    submit_and_wait's success and rejection branches, what the ledger actually
    returns. Hardening an unexecuted path is guessing about which failures to
    guard against.

    The cost of satisfying this is one faucet-funded account and about five
    minutes. The cost of skipping it is discovering the first real behaviour of
    this code with real money in flight.
    """
    if not os.path.exists(path):
        raise MainnetGuardError(
            "MAINNET BLOCKED: no testnet proof on file.\n"
            "  The XRP submission path has never executed -- not once, on any "
            "network. autofill, submit_and_wait and the reserve check are "
            "written and reviewed but never run.\n"
            "  Run:  python3 test_xrp_live.py\n"
            "  It funds a testnet account, submits a real payment, and writes "
            f"{path} on success. Then mainnet unlocks.")
    with open(path) as fh:
        proof = json.load(fh)
    if not proof.get("tx_hash") or len(proof["tx_hash"]) != 64:
        raise MainnetGuardError(f"{path} does not contain a valid testnet tx hash.")
    return proof


# ---------------------------------------------------------------------------
# The gate
# ---------------------------------------------------------------------------

def confirmation_phrase(classic_dest: str, amount_xrp: float,
                        destination_tag: Optional[int]) -> str:
    """A phrase the operator must type back, derived from THIS payment.

    Derived rather than fixed so it cannot be typed from muscle memory, and so
    confirming one payment can never confirm a different one.
    """
    digest = hashlib.sha256(
        f"{classic_dest}|{amount_xrp}|{destination_tag}".encode()).hexdigest()
    return f"SEND-{amount_xrp:g}-XRP-{digest[:6].upper()}"


def authorize_mainnet_payment(
        destination: str,
        amount_xrp: float,
        policy_path: str,
        spend_ledger_path: str,
        destination_tag: Optional[int] = None,
        confirmation: Optional[str] = None,
        client: Optional[Any] = None,
        testnet_proof_path: str = TESTNET_PROOF_FILE) -> Dict[str, Any]:
    """Run every mainnet control. Returns the vetted payment parameters, or
    raises MainnetGuardError. Signs nothing and sends nothing.

    Deliberately separate from signing so it can be run, read and tested on its
    own -- and so no future refactor can accidentally sign first and check after.
    """
    # 0. Has this code path ever run?
    proof = require_testnet_proof(testnet_proof_path)

    # 1. Address checksum, and X-address decoding.
    classic, xtag = validate_destination(destination)
    if xtag is not None and destination_tag is not None and xtag != destination_tag:
        raise MainnetGuardError(
            f"The X-address encodes destination tag {xtag} but {destination_tag} "
            f"was passed separately. Refusing to guess which is intended.")
    tag = xtag if xtag is not None else destination_tag

    # 2. Allowlist.
    policy = MainnetPolicy.load(policy_path)
    dest = policy.find(classic)

    # 3. Destination tag. Default is REQUIRED; exemption must be explicit.
    if dest.destination_tag is not None:
        if tag is not None and tag != dest.destination_tag:
            raise MainnetGuardError(
                f"Destination '{dest.label}' has tag {dest.destination_tag} in "
                f"policy but {tag} was supplied. Refusing to send with a tag the "
                f"policy does not name.")
        tag = dest.destination_tag
    if tag is None and not dest.tag_not_required:
        raise MainnetGuardError(
            f"'{dest.label}' has no destination tag. If this is an exchange or "
            f"custodial deposit address, sending without a tag means the "
            f"recipient CANNOT identify the payment -- the ledger reports "
            f"success and the funds are unrecoverable. This is the most common "
            f"way XRP is permanently lost.\n"
            f"  Set 'destination_tag' in the policy, or set "
            f"'tag_not_required': true if you are certain it is a personal "
            f"wallet that does not use tags.")

    # 4. Amount, in exact integer drops. See item AP -- float is used nowhere
    #    in any limit comparison, and a sub-drop amount is refused outright
    #    rather than silently passing a `> 0` test it cannot survive on-ledger.
    drops = xrp_to_drops_exact(amount_xrp)
    if drops <= 0:
        raise MainnetGuardError(
            f"amount must be positive, got {drops_to_xrp_str(drops)} XRP")
    amount_xrp = drops / DROPS_PER_XRP

    # 5. Per-payment ceilings -- the tighter of policy-wide and per-destination.
    cap_drops = xrp_to_drops_exact(policy.max_per_payment_xrp)
    if dest.max_per_payment_xrp > 0:
        cap_drops = min(cap_drops, xrp_to_drops_exact(dest.max_per_payment_xrp))
    if drops > cap_drops:
        raise MainnetGuardError(
            f"{drops_to_xrp_str(drops)} XRP exceeds the per-payment ceiling of "
            f"{drops_to_xrp_str(cap_drops)} for '{dest.label}'. Raise it in the "
            f"policy file deliberately.")

    # 6. Read current usage under lock. The binding check happens at step 9;
    #    these values exist so the confirmation prompt can show real headroom.
    ledger = SpendLedger(spend_ledger_path)
    today_drops, life_drops = ledger.totals_drops()

    # 7. Destination activation. FAIL CLOSED -- see item AP.
    #    This used to swallow every RPC exception into activated=None, and the
    #    check below then skipped itself, so an unreachable or timing-out node
    #    silently DISABLED the control instead of enforcing it. Confirmed: with
    #    a client that raises on every request, a 0.5 XRP payment to an unknown
    #    account was authorized, reserve check and all, on a module whose stated
    #    principle is that a control which fails open is worse than none.
    #
    #    A control that cannot be evaluated has not passed. If the ledger cannot
    #    be reached, the payment waits.
    activated = None
    if client is not None:
        try:
            r = client.request(AccountInfo(account=classic, ledger_index="validated"))
            activated = bool(r.is_successful())
        except Exception as e:
            raise MainnetGuardError(
                f"Could not check whether {classic} is an activated account: "
                f"{type(e).__name__}: {e}. Refusing to send while this control "
                f"cannot be evaluated -- an unreachable ledger node must not "
                f"silently disable a check. Retry when connectivity is restored.")
        if activated is False and drops < DROPS_PER_XRP:
            raise MainnetGuardError(
                f"{classic} is not an activated account and "
                f"{drops_to_xrp_str(drops)} XRP is below the 1 XRP base reserve, so "
                f"this payment cannot succeed. If you expected this address to be "
                f"active, re-check it -- an unexpected inactive address is often a "
                f"correct-looking typo.")

    # 8. Operator confirmation, derived from this exact payment.
    day_cap_drops = xrp_to_drops_exact(policy.max_per_day_xrp)
    expected = confirmation_phrase(classic, amount_xrp, tag)
    if policy.require_confirmation_phrase and confirmation != expected:
        raise MainnetGuardError(
            f"Mainnet payment not confirmed.\n"
            f"  to     : {classic}  ({dest.label})\n"
            f"  tag    : {tag}\n"
            f"  amount : {drops_to_xrp_str(drops)} XRP  (irreversible)\n"
            f"  today  : {drops_to_xrp_str(today_drops)} sent or reserved, "
            f"{drops_to_xrp_str(max(0, day_cap_drops - today_drops))} remaining\n"
            f"  Re-call with confirmation='{expected}' to proceed.")

    # 9. RESERVE. See item AP -- this is what makes the ceilings real.
    #    The check and the write happen together under an exclusive lock, so a
    #    concurrent process sees the headroom taken. Authorization previously
    #    verified the limits and wrote NOTHING, leaving that headroom free for
    #    the next caller: five sequential authorizations passed a cap that
    #    admits two, and six concurrent ones passed 60 XRP through a 20 XRP cap.
    #    Reserved last, so every cheaper refusal has already happened and a
    #    rejected payment never consumes headroom.
    reservation_id = ledger.reserve(
        drops, day_cap_drops, xrp_to_drops_exact(policy.max_lifetime_xrp),
        destination=classic, destination_tag=tag, label=dest.label,
        network="mainnet")

    return {"classic_destination": classic, "destination_tag": tag,
            "amount_xrp": amount_xrp, "drops": drops, "label": dest.label,
            "reservation_id": reservation_id,
            "spent_today_before": today_drops / DROPS_PER_XRP,
            "spent_lifetime_before": life_drops / DROPS_PER_XRP,
            "destination_activated": activated,
            "testnet_proof_hash": proof["tx_hash"],
            "spend_ledger_path": spend_ledger_path}


if __name__ == "__main__":
    print(__doc__)
