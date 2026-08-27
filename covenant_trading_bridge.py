#!/usr/bin/env python3
"""
covenant_trading_bridge.py -- connects the grid/bracket trading strategy to
Covenant's real ledger, ethics gate, and succession systems. Kept SEPARATE
from covenant_unified_v8.py (a focused concern combined by CovenantUnifiedMaster,
like StakingPool/SuccessionGuardianSystem), reachable over the same running API.

UPGRADED (merge) to the v8.7 trading API the core file's /trading/* routes
already call:
  * profit AND loss payloads both carry a per-pool `sequence` (Lamport-style),
    and both are signed under DISTINCT domain tags so a profit signature can
    never validate a loss report or vice versa;
  * report_realized_profit credits spendable balance AND records a pnl event;
  * report_realized_loss records a pnl event ONLY -- it NEVER moves spendable
    balance (a loss is not a symmetric-negative mint);
  * replay/reorder protection is the DB's atomic try_advance_sequence
    (BEGIN IMMEDIATE), checked AFTER amount+signature so a rejected report
    never burns a sequence number;
  * get_net_realized_pnl exposes the windowed net figure (reads trading_pnl_events,
    structurally unable to corrupt spendable balance).

SCOPE BOUNDARY (unchanged, stated plainly): succession registration here covers
who may sign FUTURE Covenant-ledger entries for the pool -- a cryptographic fact
this code can enforce. It does NOT transfer control of real exchange accounts or
the physical hardware wallet those depend on. That is real-world estate planning
outside anything this code can enforce.
"""

import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from covenant_unified_v8 import (
    _domain_frame, Database, StakingPool, SuccessionGuardianSystem, ReasoningSentinel,
)
# Import the CORE's TradingBridgeError so an exception this bridge raises is the
# SAME class object a route's `except TradingBridgeError` catches (object identity
# is the whole point -- see the note on error_cls in TradingBridge.__init__).
try:
    from covenant_unified_v8 import TradingBridgeError as _CoreTradingBridgeError
except Exception:  # pragma: no cover -- fallback only if the core lacks the symbol
    _CoreTradingBridgeError = None
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
import base64
import math


def _require_finite(value: float, field: str, error_cls: type):
    """NEW (security audit) -- item U applied to the bridge. Every magnitude
    guard here is a `<= 0` / `>= 0` comparison, and BOTH are False for NaN, so a
    NaN pnl_usd sailed past `if pnl_usd <= 0: raise` and would have been written
    straight into ledger_entries -- after which get_balance() sums to NaN for
    that pubkey permanently and every later balance comparison silently passes.
    Checked here as well as at the HTTP layer because this module is importable
    as a library; a caller constructing TradingBridge directly never touches the
    Flask before_request guard."""
    try:
        num = float(value)
    except (TypeError, ValueError):
        raise error_cls(f"{field} is not numeric: {value!r}")
    if not math.isfinite(num):
        raise error_cls(f"{field} must be a finite number, got {value!r}")
    return num


# ---------------------------------------------------------------------------
# Signed payloads. Profit and loss use DISTINCT domain tags -- a signature
# produced for one can never verify as the other (see test 7, "cross-domain",
# in test_v86_loss_tracking). Both include `sequence`, which is what actually
# provides replay/reorder protection (the DB's strictly-increasing high-water
# mark), so the signed material and the enforced ordering agree.
# ---------------------------------------------------------------------------
def trading_profit_payload(pool_pubkey: str, asset: str, exchange: str, external_ref: str,
                           pnl_usd: float, timestamp: float, sequence: int) -> bytes:
    return _domain_frame(b"COVENANT_TRADING_PROFIT_V1", pool_pubkey, asset, exchange,
                         external_ref, str(pnl_usd), str(timestamp), str(sequence))


def trading_loss_payload(pool_pubkey: str, asset: str, exchange: str, external_ref: str,
                         pnl_usd: float, timestamp: float, sequence: int) -> bytes:
    return _domain_frame(b"COVENANT_TRADING_LOSS_V1", pool_pubkey, asset, exchange,
                         external_ref, str(pnl_usd), str(timestamp), str(sequence))


def _verify(pubkey_pem: str, payload: bytes, signature_b64: str) -> bool:
    try:
        pub_key = serialization.load_pem_public_key(pubkey_pem.encode(), backend=default_backend())
        pub_key.verify(
            base64.b64decode(signature_b64), payload,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256(),
        )
        return True
    except Exception:
        return False


def verify_trading_profit_signature(pool_pubkey_pem: str, asset: str, exchange: str, external_ref: str,
                                    pnl_usd: float, timestamp: float, sequence: int,
                                    signature_b64: str) -> bool:
    return _verify(pool_pubkey_pem,
                   trading_profit_payload(pool_pubkey_pem, asset, exchange, external_ref,
                                          pnl_usd, timestamp, sequence),
                   signature_b64)


def verify_trading_loss_signature(pool_pubkey_pem: str, asset: str, exchange: str, external_ref: str,
                                  pnl_usd: float, timestamp: float, sequence: int,
                                  signature_b64: str) -> bool:
    return _verify(pool_pubkey_pem,
                   trading_loss_payload(pool_pubkey_pem, asset, exchange, external_ref,
                                        pnl_usd, timestamp, sequence),
                   signature_b64)


def node_gift_payload(pool_pubkey: str, recipient_pubkey: str, amount: float, timestamp: float) -> bytes:
    return _domain_frame(b"COVENANT_NODE_GIFT_V1", pool_pubkey, recipient_pubkey, str(amount), str(timestamp))


def verify_node_gift_signature(pool_pubkey_pem: str, recipient_pubkey: str, amount: float,
                               timestamp: float, signature_b64: str) -> bool:
    return _verify(pool_pubkey_pem,
                   node_gift_payload(pool_pubkey_pem, recipient_pubkey, amount, timestamp),
                   signature_b64)


# ---------------------------------------------------------------------------
# Timestamp bounds -- ASYMMETRIC on purpose (a gift's timestamp is when the
# operator authorized it -> tight; a fill's timestamp is legitimately reported
# late -> generous but bounded; future timestamps are never legitimate ->
# tight shared bound). Belt-and-suspenders for out-of-band library callers;
# true replay is handled by the sequence high-water mark.
# ---------------------------------------------------------------------------
MAX_FUTURE_SKEW_SECONDS = 120
# GHOST CONTROL, FOUND AND FIXED (audit): this constant previously sat here at
# 300 with ZERO enforcement -- the check that used it was removed to satisfy a
# test whose fixtures sign gifts with hour-old timestamps, but the constant was
# left behind. Confirmed by attacking a live node: a gift authorization dated
# ONE YEAR in the past was accepted with HTTP 200, while anyone reading this
# file would reasonably conclude gift authorizations expire after 5 minutes.
# A declared-but-unenforced control is worse than no control, because it
# misleads the next reader (including an auditor) into believing a bound exists.
#
# Now genuinely enforced, with a window that is bounded but realistic: gift
# authorizations are signed out-of-band by an operator and may legitimately be
# submitted well after signing, so this matches the profit-report reasoning
# rather than a 5-minute interactive-session assumption. Exact replay is
# separately blocked by ledger idempotency (the gift ref_id embeds the
# timestamp); this bound limits how long a captured-but-unspent authorization
# stays usable.
MAX_GIFT_AGE_SECONDS = 7 * 24 * 3600
MAX_PROFIT_REPORT_AGE_SECONDS = 7 * 24 * 3600  # one week; applies to loss reports too

# Gift trust-gating + graduated vesting (v8.7 item Q). A gift credits the
# recipient's TOTAL balance immediately but is LOCKED (excluded from spendable
# balance, which is what StakingPool.stake checks) until a trust-tiered delay
# elapses -- higher-reputation recipients vest faster. A single call is capped
# at a fraction of the pool so one signed gift can't drain it; a recipient below
# the minimum trust floor is refused outright.
MIN_RECIPIENT_TRUST_SCORE = 0.3          # below this, refuse the gift entirely
GIFT_SINGLE_CALL_CAP_FRACTION = 0.20     # one gift may move at most 20% of the pool
GIFT_VESTING_TIER_TRUSTED = 0.5          # score >= this -> the faster tier
GIFT_VESTING_DELAY_TRUSTED_SECONDS = 3 * 86400    # 3 days
GIFT_VESTING_DELAY_UNTRUSTED_SECONDS = 14 * 86400  # 14 days (harsher)


class TradingBridgeError(Exception):
    """Local fallback error type. NOTE: CovenantUnifiedMaster passes ITS OWN
    TradingBridgeError into the constructor (error_cls) so that `except
    TradingBridgeError` in a route catches what the bridge raises even when the
    core file is running as "__main__" and this module re-imports it by name.
    This local class exists only so direct library callers still have a symbol."""
    pass


class TradingBridge:
    """Wraps a running node's db/sentinel/staking_pool/succession with the
    trading-specific operations. Adds behavior; does not stand up a second
    ledger/db/succession system."""

    def __init__(self, db: Database, sentinel: ReasoningSentinel, staking_pool: StakingPool,
                 succession: SuccessionGuardianSystem, friendship=None, error_cls: type = None):
        # NOTE on arg order: CovenantUnifiedMaster constructs this as
        # TradingBridge(db, sentinel, staking_pool, succession, friendship) --
        # the 5th positional is the node's FriendshipTracker, kept for callers
        # that want reputation context, NOT an error class. error_cls defaults to
        # the CORE's TradingBridgeError (imported above) so raised errors match a
        # route's `except TradingBridgeError`; a caller may still inject one.
        self.db = db
        self.sentinel = sentinel
        self.staking_pool = staking_pool
        self.succession = succession
        self.friendship = friendship
        self.pending_ledger_event = None
        self.error_cls = error_cls or _CoreTradingBridgeError or TradingBridgeError

    def _check_fill_timestamp(self, timestamp: float, label: str):
        now = time.time()
        if timestamp > now + MAX_FUTURE_SKEW_SECONDS:
            raise self.error_cls(
                f"{label} timestamp is {timestamp - now:.0f}s in the future "
                f"(max skew {MAX_FUTURE_SKEW_SECONDS}s) -- refusing.")
        if timestamp < now - MAX_PROFIT_REPORT_AGE_SECONDS:
            raise self.error_cls(
                f"{label} timestamp is older than {MAX_PROFIT_REPORT_AGE_SECONDS}s -- "
                f"late reporting is allowed but not unboundedly; refusing a stale payload.")

    def report_realized_profit(self, pool_pubkey_pem: str, asset: str, exchange: str, external_ref: str,
                               pnl_usd: float, timestamp: float, sequence: int,
                               signature_b64: str) -> dict:
        """Credit realized PROFIT to the pool's spendable balance AND record a
        pnl event. Signed, sequence-gated. Amount + signature are checked BEFORE
        the sequence is advanced, so a rejected report never consumes a sequence
        number."""
        _require_finite(pnl_usd, "pnl_usd", self.error_cls)
        _require_finite(timestamp, "timestamp", self.error_cls)
        if pnl_usd <= 0:
            raise self.error_cls(
                f"report_realized_profit called with pnl_usd={pnl_usd} <= 0 -- this path only "
                f"records REALIZED PROFIT; use report_realized_loss for a losing close.")
        self._check_fill_timestamp(timestamp, "Profit-report")
        if not verify_trading_profit_signature(pool_pubkey_pem, asset, exchange, external_ref,
                                               pnl_usd, timestamp, sequence, signature_b64):
            raise self.error_cls("Invalid trading-profit signature -- refusing to credit the ledger.")
        # Sequence AFTER amount+signature so a bad report can't burn a number.
        if not self.db.try_advance_sequence(pool_pubkey_pem, sequence):
            raise self.error_cls(
                f"Sequence {sequence} is not strictly greater than this pool's high-water mark "
                f"-- replay or reorder; refusing.")

        judgment = self.sentinel.judge.evaluate(
            {"origin": "trading_bracket_grid", "asset": asset, "exchange": exchange,
             "external_ref": external_ref, "pnl_usd": pnl_usd},
            self.sentinel.principles,
        )
        ref_id = f"trading_profit:{exchange}:{external_ref}"
        self.db.save_judgment(ref_id, judgment)
        self.db.record_ledger_entry(pool_pubkey_pem, pnl_usd, "trading_profit", ref_id=ref_id)
        self.db.record_trading_pnl_event(pool_pubkey_pem, asset, exchange, external_ref,
                                         pnl_usd, timestamp, ref_id=ref_id, sequence=sequence)
        return {
            "credited": pnl_usd, "sequence": sequence,
            "new_balance": self.db.get_balance(pool_pubkey_pem),
            "judgment": judgment.reasoning, "ref_id": ref_id,
        }

    def report_realized_loss(self, pool_pubkey_pem: str, asset: str, exchange: str, external_ref: str,
                             pnl_usd: float, timestamp: float, sequence: int,
                             signature_b64: str) -> dict:
        """Record a realized LOSS as a pnl event ONLY. This NEVER touches
        spendable balance -- a loss is not a symmetric-negative mint; treating
        it as one would let a signed 'loss' silently drain the ledger. pnl_usd
        must be negative. Sequence-gated on the SAME per-pool counter as profit."""
        _require_finite(pnl_usd, "pnl_usd", self.error_cls)
        _require_finite(timestamp, "timestamp", self.error_cls)
        if pnl_usd >= 0:
            raise self.error_cls(
                f"report_realized_loss called with pnl_usd={pnl_usd} >= 0 -- a realized loss must be "
                f"negative; use report_realized_profit for a gain.")
        self._check_fill_timestamp(timestamp, "Loss-report")
        if not verify_trading_loss_signature(pool_pubkey_pem, asset, exchange, external_ref,
                                             pnl_usd, timestamp, sequence, signature_b64):
            raise self.error_cls("Invalid trading-loss signature -- refusing to record.")
        if not self.db.try_advance_sequence(pool_pubkey_pem, sequence):
            raise self.error_cls(
                f"Sequence {sequence} is not strictly greater than this pool's high-water mark "
                f"-- replay or reorder; refusing.")
        # Audit judgment recorded; NEVER a ledger-balance write.
        judgment = self.sentinel.judge.evaluate(
            {"origin": "trading_bracket_grid_loss", "asset": asset, "exchange": exchange,
             "external_ref": external_ref, "pnl_usd": pnl_usd},
            self.sentinel.principles,
        )
        ref_id = f"trading_loss:{exchange}:{external_ref}"
        self.db.save_judgment(ref_id, judgment)
        self.db.record_trading_pnl_event(pool_pubkey_pem, asset, exchange, external_ref,
                                         pnl_usd, timestamp, ref_id=ref_id, sequence=sequence)
        return {
            "recorded_loss": pnl_usd, "sequence": sequence,
            "spendable_balance_unchanged": self.db.get_spendable_balance(pool_pubkey_pem),
            "ref_id": ref_id,
        }

    def get_net_realized_pnl(self, pool_pubkey_pem: str, since: float = None, until: float = None) -> dict:
        """Windowed net realized P&L (reads trading_pnl_events; cannot corrupt
        spendable balance). since/until are optional epoch-seconds bounds."""
        return self.db.get_net_realized_pnl(pool_pubkey_pem, since, until)

    def _recipient_trust(self, recipient_pubkey_pem: str) -> float:
        """Recipient reputation via the node's FriendshipTracker -- the same
        score the rest of the system computes. A never-before-seen recipient
        gets the newcomer default (0.5). Falls back to the default if no
        friendship tracker was wired in."""
        if self.friendship is not None and hasattr(self.friendship, "get"):
            return self.friendship.get(recipient_pubkey_pem)
        return 0.5

    def gift_stake_to_new_node(self, pool_pubkey_pem: str, recipient_pubkey_pem: str, amount: float,
                               timestamp: float, signature_b64: str) -> dict:
        """Non-usurious by construction: a straight ledger credit, requires the
        POOL's real signature. Does NOT stake on the recipient's behalf.

        Trust-gated + vested (v8.7 item Q): a single call may move at most
        GIFT_SINGLE_CALL_CAP_FRACTION of the pool; a recipient below
        MIN_RECIPIENT_TRUST_SCORE is refused; the gift credits TOTAL balance
        immediately but is locked out of SPENDABLE balance (what staking checks)
        for a trust-tiered vesting delay."""
        _require_finite(amount, "amount", self.error_cls)
        _require_finite(timestamp, "timestamp", self.error_cls)
        if amount <= 0:
            raise self.error_cls("Gift amount must be positive.")
        now = time.time()
        if timestamp > now + MAX_FUTURE_SKEW_SECONDS:
            raise self.error_cls(
                f"Gift timestamp is {timestamp - now:.0f}s in the future "
                f"(max skew {MAX_FUTURE_SKEW_SECONDS}s) -- refusing.")
        if timestamp < now - MAX_GIFT_AGE_SECONDS:
            raise self.error_cls(
                f"Gift authorization is older than {MAX_GIFT_AGE_SECONDS}s "
                f"({MAX_GIFT_AGE_SECONDS / 86400:.0f} days) -- re-sign and resubmit.")
        if not verify_node_gift_signature(pool_pubkey_pem, recipient_pubkey_pem, amount, timestamp, signature_b64):
            raise self.error_cls("Invalid node-gift signature -- refusing to move funds.")

        balance = self.db.get_balance(pool_pubkey_pem)
        # Single-call cap -- one signed gift can't move more than a set fraction
        # of the pool, bounding the blast radius of a single leaked signature.
        cap = GIFT_SINGLE_CALL_CAP_FRACTION * balance
        if amount > cap:
            raise self.error_cls(
                f"Gift of {amount:.2f} exceeds the single-call cap of {cap:.2f} "
                f"({GIFT_SINGLE_CALL_CAP_FRACTION:.0%} of the {balance:.2f} pool) -- refusing.")
        if balance < amount:
            raise self.error_cls(f"Insufficient pool balance: have {balance:.2f}, need {amount:.2f}.")

        # Trust floor -- an actively bad-reputation recipient is refused outright.
        trust = self._recipient_trust(recipient_pubkey_pem)
        if trust < MIN_RECIPIENT_TRUST_SCORE:
            raise self.error_cls(
                f"Recipient trust score {trust:.2f} is below the {MIN_RECIPIENT_TRUST_SCORE} floor "
                f"-- refusing to gift to a below-threshold recipient.")

        # Graduated vesting: more trust vests faster.
        vesting_delay = (GIFT_VESTING_DELAY_TRUSTED_SECONDS
                         if trust >= GIFT_VESTING_TIER_TRUSTED
                         else GIFT_VESTING_DELAY_UNTRUSTED_SECONDS)

        ref_id = Database.node_gift_ref_id(pool_pubkey_pem, recipient_pubkey_pem,
                                           amount, timestamp)

        # REWRITTEN v8.11 -- see PATCH LOG items AE/AF/AG. Three changes here,
        # each closing a confirmed defect.
        #
        # The ref_id is now DERIVED from the signed parameters instead of being
        # composed from PEM prefixes and a timestamp. Every PEM key starts with
        # the same 16 characters, so the old identifier carried no party
        # identity at all and reduced to the timestamp; and because the gift
        # signature never covered the ref_id, a caller could vary it freely and
        # replay one authorization indefinitely.
        #
        # The local credit now goes through apply_ledger_event -- the same
        # atomic, all-or-nothing path a peer uses -- instead of two loose
        # record_ledger_entry calls. That is what lets the origin node's own
        # chain replay recognise this event as already applied and skip it in
        # full, rather than relying on per-row ref_id collisions to suppress it
        # one row at a time (which is exactly the partial-application behaviour
        # item AE exists to eliminate).
        entries = [
            {"pubkey": pool_pubkey_pem, "delta": -amount,
             "reason": "node_gift_sent", "ref_id": ref_id},
            {"pubkey": recipient_pubkey_pem, "delta": amount,
             "reason": "node_gift_received", "ref_id": ref_id},
        ]
        self.pending_ledger_event = {
            "entries": entries,
            "auth": {
                pool_pubkey_pem: {
                    "kind": "node_gift_v1",
                    "recipient": recipient_pubkey_pem,
                    "amount": amount,
                    "timestamp": timestamp,
                    "signature": signature_b64,
                }
            },
        }
        valid, why = Database.validate_ledger_event(self.pending_ledger_event)
        if not valid:
            raise self.error_cls(f"refusing to record an unpublishable gift: {why}")
        if self.db.apply_ledger_event(self.pending_ledger_event, ref_id) == 0:
            raise self.error_cls(
                "This exact gift has already been applied on this node "
                "(same payer, recipient, amount and timestamp) -- refusing to repeat it.")
        # Lock the gifted amount out of SPENDABLE balance until it vests. Total
        # balance (get_balance) reflects it immediately; get_spendable_balance
        # (and therefore StakingPool.stake) does not, until unlock_at passes.
        self.db.record_gift_lockup(recipient_pubkey_pem, amount, now + vesting_delay, ref_id=ref_id)

        return {
            "gifted": amount, "pool_balance_after": self.db.get_balance(pool_pubkey_pem),
            "recipient_balance_after": self.db.get_balance(recipient_pubkey_pem),
            "recipient_trust_score": trust, "vesting_delay_seconds": vesting_delay,
            "ref_id": ref_id, "ledger_event": self.pending_ledger_event,
        }

    def register_pool_succession(self, pool_pubkey_pem: str, successor_pubkey_pem: str,
                                 guardian_pubkeys: list, threshold: int,
                                 heartbeat_interval_days: float = 30, grace_period_days: float = 15) -> tuple:
        """Thin wrapper -- see module docstring's SCOPE BOUNDARY before treating
        this as complete succession coverage for the trading operation."""
        return self.succession.register(
            pool_pubkey_pem, successor_pubkey_pem, guardian_pubkeys,
            threshold, heartbeat_interval_days, grace_period_days,
        )


if __name__ == "__main__":
    print(
        "covenant_trading_bridge.py is a library module, not a standalone program.\n"
        "Run the node instead:\n\n    python3 covenant_unified_v8.py --port 5000\n\n"
        "The TradingBridge is constructed inside CovenantUnifiedMaster and its\n"
        "/trading/* routes become reachable on the running server."
    )
    sys.exit(1)
