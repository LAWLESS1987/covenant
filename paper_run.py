#!/usr/bin/env python3
"""
paper_run.py -- the sealed-signal ledger.

WHY THIS FILE EXISTS
  TRADING_POLICY.json's graduation_requirements ask for 30 sealed signals
  scored before the $100 sleeve moves from paper to real money.
  TRADING_READINESS.md checklist line #4 asks for the same 30 and records the
  actual count: ZERO, because the file that would produce them did not exist.
  This is that file. It is the only blocking line on that checklist that this
  loop is permitted to clear, and clearing it is the only thing that can turn
  "no edge detectable" into a statement with a date on it.

WHAT THIS FILE IS NOT, AND THE BOUNDARY IT KEEPS
  IMPROVEMENT_LOG.md Section 0 is immutable: no trades placed by automation,
  no credentials requested or stored, no claims of profit edge, no security
  control weakened to make a test pass, no widening of an agent's own scope.
  DAILY_CHECK.md section 7 is broader than Section 0 and is the binding text
  here: "Never place, PREPARE, or offer to place a trade."

  So, precisely:

    * This file records CALLS, not ORDERS. A call is a direction on an asset
      -- target in {-1, 0, +1} -- against a reference price at a moment in
      time. It has no venue, no quantity, no side word, no order type, and no
      route to one. PaperTrader.seal() in covenant_backtest.py uses exactly
      this shape and this file deliberately does not widen it.
    * It holds no key, requests no key, and reads no credential file. It talks
      to two PUBLIC price endpoints and nothing else.
    * It never emits BUY or SELL. The report is a measurement of a rule, not
      an instruction, and it says so in its own output.
    * It cannot unlock a position, cannot change TRADING_POLICY.json, and
      refuses to run at all if the policy says the sleeve is live.

  If you want a file that computes and places orders, that is execute.py, it
  does not exist, and per TRADING_READINESS.md #3b it is L's call to write --
  not this one's.

THE ONE PROPERTY THAT MAKES THIS WORTH RUNNING
  covenant_backtest.py states it: "the decision is recorded BEFORE the outcome
  bar exists, and is immutable afterwards. Paper trading that lets you revise
  or reinterpret a call after seeing the result is a backtest with extra steps
  and worse data."

  Two mechanisms enforce it here, and they are different mechanisms on purpose:

    1. APPEND-ONLY HASH CHAIN. Every record carries the hash of the record
       before it. Editing record n changes its hash, which breaks n+1, which
       breaks n+2, to the end of the file. --verify recomputes the whole chain
       from genesis and names the first broken link by sequence number and
       line number. Rewriting a sealed price is detected; the suite proves it
       by doing it (CONTRIBUTING.md section 7 -- a guard that has only ever
       seen correct code has never been tested).
    2. SEAL AND SETTLE ARE SEPARATE RECORDS. The seal is written and hashed
       before the outcome exists and is never rewritten. The settle is a LATER
       record that references the seal's sequence number. If settling mutated
       the seal in place, the chain would have to be rebuilt on every outcome
       and the whole property would be theatre.

  Note the ordering guard that follows from this and is checked in --verify:
  a settle whose exit timestamp is not STRICTLY GREATER than its seal's
  timestamp is refused. That is the same look-ahead bug the loop already
  shipped once and caught -- TRADING_READINESS.md section 1b, the bootstrap
  helper that used bar t+1's own return for a decision made at t's close and
  "found" a +112% XLM edge that was not there. Structural refusal, not care.

WHERE THE LEDGER LIVES, AND WHY IT IS NOT IN THE SYNCED FOLDER
  Default ~/.covenant/paper_ledger.jsonl, override with COVENANT_PAPER_LEDGER.
  This is D4's reasoning applied to a second file, and both halves of it apply
  here MORE strongly than they did to daily_state.json (see daily.py's header):

    1. The covenant folder leaves the machine. A dated record of every
       directional call on the whole book is not a key, but it is not
       something to post off the box either.
    2. covenant_seal.py hashes every file in that folder and covenant_anchor.py
       anchors the root to the chain. A file that changes on EVERY RUN would
       invalidate the seal every run and train its operator to ignore a
       mismatch -- and PC_SYNC_LOOP.md already warns that "a tamper-evident
       seal that is usually wrong teaches its operator to ignore it." This
       ledger changes on every run by construction. It must not live there.

  The ledger carries its own tamper evidence. It does not need the folder seal
  and must not break it.

USAGE
  python paper_run.py --seal   --asset SOL --target 1 --fetch
  python paper_run.py --seal   --asset SOL --target 1 --ref-px 85.33
  python paper_run.py --settle --seq 7 --exit-px 88.10
  python paper_run.py --settle --seq 7 --fetch
  python paper_run.py --verify
  python paper_run.py --report --trials 12 --trial-sr-var 0.004
  python paper_run.py --status

EXIT CODES
  0  the requested action succeeded and every check passed
  1  a check FAILED (chain broken, guard refused, gate not met)
  2  the action could not be attempted (bad arguments, missing dependency,
     unreadable policy). Distinct from 1 on purpose: "I could not look" and
     "I looked and it is wrong" are different claims, and P16's lesson in this
     project is that a system which reports them identically is unreadable.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import sys
import time
import urllib.error
import urllib.request
from statistics import NormalDist
from typing import Any, Dict, List, Optional, Tuple

# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------

# Bumped to 2 when price_convention became mandatory on every record. verify()
# REFUSES a ledger whose genesis declares a schema this build does not know,
# rather than reading old records under new rules -- silently reinterpreting a
# sealed record is the one failure a tamper-evident ledger cannot survive.
SCHEMA_VERSION = 2
SUPPORTED_SCHEMAS = {2}

# What a recorded price actually IS. Stamped on every seal and every settle,
# validated on the way back in, and checked for mixture at report time.
#
# WHY THIS EXISTS AT ALL, and it is the largest correctness gap the first cut
# of this file had: d2_regime_deep.py's convention is "signal at the CLOSE of
# bar t, fill at the OPEN of bar t+1", on daily bars with the forming bar
# dropped. A ticker read at 14:12 on a Tuesday is none of those things. A paper
# record built from spot ticks and a backtest built from daily closes are not
# the same experiment, and "must_beat_buy_and_hold" silently compares them.
# So the convention travels WITH the record and a mixed ledger is reported,
# never averaged.
PRICE_CONVENTIONS = {
    "daily_close",   # last COMPLETED daily candle; the comparable one
    "spot_ticker",   # last trade, right now; NOT comparable with D2
    "hand_entered",  # a number a human typed, labelled as such
}
DEFAULT_PRICE_CONVENTION = "daily_close"
HERE = os.path.dirname(os.path.abspath(__file__))

# Cost convention. NOT tunable at runtime by design: every sealed record
# stamps the values it was sealed under, so a later change cannot silently
# rescale history, and a history sealed under two different cost models is
# DETECTED at report time rather than averaged.
DEFAULT_COST_BPS_ROUND_TRIP = 40.0   # matches d2_regime_deep.py and CostModel()

# Cross-venue guard. X1 in daily.py added a second independent venue for
# availability; the more valuable half is disagreement detection. A quote two
# venues disagree about by more than this is not a price, it is a symptom.
MAX_VENUE_DISAGREEMENT_PCT = 1.0

# DAILY_CHECK.md section 5: CC (Canton) is NOT tradable on Coinbase, the
# endpoint 404s, and there are impostor tokens using the name. Never fetch it.
NEVER_FETCH = {"CC"}

# Bounds on anything read back off disk. The ledger is an input path and gets
# the same suspicion as a peer frame (SENSING_ACROSS_LAYERS.md: everything a
# peer sends us is peer input).
MAX_LEDGER_BYTES = 32 * 1024 * 1024
MAX_LINE_BYTES = 16 * 1024
MAX_RECORDS = 200_000
MAX_NOTE_CHARS = 200
MAX_ASSET_CHARS = 16
MAX_RULE_CHARS = 80

EULER_GAMMA = 0.5772156649015329
GENESIS_PREV = "0" * 64


def _source_fingerprint() -> Dict[str, Any]:
    """This file's own sha256 and line count, stamped into every seal.

    P11's pattern. The point is not paranoia about edits -- it is that a
    ledger whose records were produced by two different versions of the sealer
    is a ledger with two different meanings, and nothing else in the record
    would say so.
    """
    try:
        with open(os.path.abspath(__file__), "rb") as fh:
            raw = fh.read()
        return {"sha256": hashlib.sha256(raw).hexdigest(),
                "lines": raw.count(b"\n") + (0 if raw.endswith(b"\n") else 1)}
    except OSError as exc:                                   # pragma: no cover
        return {"sha256": "unreadable", "lines": 0, "error": type(exc).__name__}


# --------------------------------------------------------------------------
# Errors. Two families, because exit codes 1 and 2 mean different things.
# --------------------------------------------------------------------------

class LedgerRefused(Exception):
    """A guard said no. The action was understood and is not allowed."""


class LedgerUnavailable(Exception):
    """The action could not be attempted at all."""


# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------

def ledger_path() -> str:
    env = os.environ.get("COVENANT_PAPER_LEDGER")
    if env:
        return os.path.abspath(os.path.expanduser(env))
    return os.path.join(os.path.expanduser("~"), ".covenant", "paper_ledger.jsonl")


def policy_path() -> str:
    env = os.environ.get("COVENANT_TRADING_POLICY")
    if env:
        return os.path.abspath(os.path.expanduser(env))
    return os.path.join(HERE, "TRADING_POLICY.json")


# --------------------------------------------------------------------------
# Canonical serialization and hashing
# --------------------------------------------------------------------------

def canonical(payload: Dict[str, Any]) -> bytes:
    """Deterministic bytes for a record payload.

    sort_keys so key order cannot change the hash. allow_nan=False because
    json.dumps will happily emit bare NaN/Infinity, which is not JSON, and
    json.loads will happily read them back -- a single NaN in a sealed price
    would poison every statistic downstream in silence. Refuse at the door.
    ensure_ascii so the bytes are stable regardless of the writer's locale.
    """
    return json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def _reject_nonfinite(_const: str) -> float:
    raise ValueError("non-finite number in ledger (NaN/Infinity are refused)")


def loads_strict(line: str) -> Dict[str, Any]:
    """json.loads with NaN/Infinity refused rather than silently accepted."""
    obj = json.loads(line, parse_constant=_reject_nonfinite)
    if not isinstance(obj, dict):
        raise ValueError("ledger record is not a JSON object")
    return obj


def chain_hash(prev_hash: str, payload: Dict[str, Any]) -> str:
    h = hashlib.sha256()
    h.update(prev_hash.encode("ascii"))
    h.update(b"\x00")
    h.update(canonical(payload))
    return h.hexdigest()


# --------------------------------------------------------------------------
# TRADING_POLICY.json -- read BEFORE anything is sealed, and failed closed on.
# --------------------------------------------------------------------------

class Policy:
    """The machine-readable policy, plus the guards that read it.

    TRADING_POLICY.json's own header: "execute.py and paper_run.py read this
    BEFORE generating any order. A note in a markdown file is a wish; this is
    a lock." That sentence names this file. It is honoured literally: nothing
    is sealed until the policy has been read, parsed, and passed.

    FAIL CLOSED ON THE READ ITSELF. If the policy is missing or unparseable we
    do not quietly seal without it -- that is exactly the failure D4 found in
    daily.py, where guards.py was imported by nothing and the circuit breakers
    existed as an idea and never as behaviour.
    """

    def __init__(self, raw: Dict[str, Any], path: str, sha256: str):
        self.raw = raw
        self.path = path
        self.sha256 = sha256

    # -- loading ---------------------------------------------------------

    @classmethod
    def load(cls, path: Optional[str] = None) -> "Policy":
        path = path or policy_path()
        try:
            with open(path, "rb") as fh:
                blob = fh.read()
        except OSError as exc:
            raise LedgerUnavailable(
                f"TRADING_POLICY.json could not be read at {path}: "
                f"{type(exc).__name__}: {exc}. Nothing is sealed without it."
            ) from exc
        try:
            raw = json.loads(blob.decode("utf-8"), parse_constant=_reject_nonfinite)
        except Exception as exc:
            raise LedgerUnavailable(
                f"TRADING_POLICY.json at {path} did not parse: "
                f"{type(exc).__name__}: {exc}. Nothing is sealed without it."
            ) from exc
        if not isinstance(raw, dict):
            raise LedgerUnavailable("TRADING_POLICY.json is not a JSON object.")
        return cls(raw, path, hashlib.sha256(blob).hexdigest())

    # -- accessors -------------------------------------------------------

    @property
    def locked_symbols(self) -> List[str]:
        node = self.raw.get("locked_positions") or {}
        syms = node.get("symbols") or []
        return [str(s).upper() for s in syms if isinstance(s, str)]

    @property
    def sleeve(self) -> Dict[str, Any]:
        node = self.raw.get("sleeve")
        return node if isinstance(node, dict) else {}

    @property
    def mode(self) -> str:
        return str(self.sleeve.get("mode", "")).lower()

    @property
    def funded(self) -> bool:
        return bool(self.sleeve.get("funded", False))

    @property
    def funding_usd(self) -> float:
        try:
            return float(self.sleeve.get("funding_usd", 0.0))
        except (TypeError, ValueError):
            return 0.0

    @property
    def graduation(self) -> Dict[str, Any]:
        node = self.raw.get("graduation_requirements")
        return node if isinstance(node, dict) else {}

    @property
    def runtime_unlock_allowed(self) -> bool:
        node = self.raw.get("overrides") or {}
        return bool(node.get("runtime_unlock_allowed", False))

    def classify(self, asset: str) -> str:
        return "locked" if asset.upper() in set(self.locked_symbols) else "sleeve_or_watchlist"

    # -- guards ----------------------------------------------------------

    def assert_sealable(self) -> None:
        """Refuse to seal at all unless the policy still says paper.

        The direction of this check matters. It is NOT "am I allowed to
        trade" -- this file never trades. It is: if someone has flipped the
        sleeve to live, the meaning of a paper ledger has changed underneath
        it, and continuing to append to the same chain would silently mix two
        regimes in one record. Stop and say so.
        """
        if self.mode != "paper":
            raise LedgerRefused(
                f"sleeve mode is '{self.mode or '(unset)'}', not 'paper'. "
                f"This file only ever seals paper calls. If the sleeve has "
                f"gone live, start a new ledger and say so in the policy; do "
                f"not append live-regime records to a paper chain."
            )
        if self.funded:
            raise LedgerRefused(
                "sleeve is marked funded=true while mode='paper'. That is a "
                "contradiction in the policy, not a state this file guesses "
                "its way through. Fix TRADING_POLICY.json first."
            )
        if self.runtime_unlock_allowed:
            raise LedgerRefused(
                "overrides.runtime_unlock_allowed is true. The policy's own "
                "comment says nothing in code may unlock a position at "
                "runtime. Refusing to run while that is set."
            )


# --------------------------------------------------------------------------
# Append lock. Two concurrent runs appending to one chain interleave, and an
# interleaved chain is a broken chain -- which --verify would report as
# tampering. A false tamper report is worse than none (PC_SYNC_LOOP.md).
# --------------------------------------------------------------------------

class AppendLock:
    """O_EXCL lock file. Portable across win32 and posix on purpose (M29:
    a green result is green for the platform it ran on; fcntl is not)."""

    STALE_SECONDS = 120.0

    def __init__(self, target: str):
        self.lock_file = target + ".lock"
        self.fd: Optional[int] = None

    def __enter__(self) -> "AppendLock":
        for _ in range(3):
            try:
                self.fd = os.open(self.lock_file,
                                  os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                os.write(self.fd, f"{os.getpid()} {time.time():.3f}\n".encode("ascii"))
                return self
            except FileExistsError:
                try:
                    age = time.time() - os.stat(self.lock_file).st_mtime
                except OSError:
                    age = 0.0
                if age > self.STALE_SECONDS:
                    # Reported, not silent. A stale lock is a crashed writer,
                    # and a crashed writer may have left a truncated tail.
                    sys.stderr.write(
                        f"paper_run: breaking a stale lock ({age:.0f}s old) at "
                        f"{self.lock_file}; run --verify afterwards.\n")
                    try:
                        os.unlink(self.lock_file)
                    except OSError:
                        pass
                    continue
                time.sleep(0.25)
        raise LedgerUnavailable(
            f"another paper_run is holding {self.lock_file}. Not appending.")

    def __exit__(self, *_exc: Any) -> None:
        if self.fd is not None:
            try:
                os.close(self.fd)
            except OSError:
                pass
        try:
            os.unlink(self.lock_file)
        except OSError:
            pass


# --------------------------------------------------------------------------
# The ledger
# --------------------------------------------------------------------------

class VerifyResult:
    def __init__(self) -> None:
        self.ok: bool = True
        self.records: List[Dict[str, Any]] = []
        self.problems: List[str] = []
        self.truncated_tail: bool = False
        self.seals: int = 0
        self.settles: int = 0

    def fail(self, msg: str) -> None:
        self.ok = False
        self.problems.append(msg)


class Ledger:
    """Append-only, hash-chained JSONL.

    Record shapes (the payload that is hashed; `hash` and `prev` sit outside
    the payload so a record's own hash is not an input to itself):

      GENESIS  {kind, seq, ts, schema, note}
      SEAL     {kind, seq, ts, asset, target, ref_px, rule, capital,
                cost_bps, price_source, price_convention, policy_sha256,
                code_sha256, policy_class, note}
      SETTLE   {kind, seq, ts, seal_seq, exit_px, price_source,
                price_convention, note}

    A SETTLE never rewrites its SEAL. That is the whole design.
    """

    def __init__(self, path: Optional[str] = None):
        self.path = path or ledger_path()

    # -- reading ---------------------------------------------------------

    def exists(self) -> bool:
        return os.path.exists(self.path)

    def _read_lines(self) -> List[str]:
        try:
            size = os.path.getsize(self.path)
        except OSError as exc:
            raise LedgerUnavailable(
                f"ledger not readable at {self.path}: {type(exc).__name__}") from exc
        if size > MAX_LEDGER_BYTES:
            raise LedgerRefused(
                f"ledger is {size} bytes, over the {MAX_LEDGER_BYTES} cap. "
                f"Refusing to read it rather than growing memory to match a "
                f"file whose size nobody chose.")
        with open(self.path, "r", encoding="utf-8", newline="") as fh:
            return fh.read().split("\n")

    def verify(self) -> VerifyResult:
        """Recompute the whole chain from genesis. Names the FIRST break.

        Everything here is a check on data read back off disk, and every
        failure is reported with a line number, because "the chain is broken"
        without a location is not actionable and teaches its reader to shrug.
        """
        res = VerifyResult()
        if not self.exists():
            res.fail(f"no ledger at {self.path} (zero sealed signals)")
            return res

        raw_lines = self._read_lines()
        if raw_lines and raw_lines[-1] == "":
            raw_lines = raw_lines[:-1]          # trailing newline, normal
        elif raw_lines:
            # Last line has no terminator: a writer died mid-append. Report
            # it; never auto-repair. Auto-repair on a tamper-evident ledger
            # is the one thing it must not do.
            res.truncated_tail = True
            res.fail(f"line {len(raw_lines)}: file does not end in a newline -- "
                     f"a writer was interrupted. Inspect the tail by hand; this "
                     f"file will not repair it for you.")

        if len(raw_lines) > MAX_RECORDS:
            res.fail(f"{len(raw_lines)} records, over the {MAX_RECORDS} cap")
            return res

        prev_hash = GENESIS_PREV
        expected_seq = 0
        prev_ts = float("-inf")
        seal_by_seq: Dict[int, Dict[str, Any]] = {}
        settled_seqs: Dict[int, int] = {}

        for lineno, line in enumerate(raw_lines, start=1):
            if len(line.encode("utf-8", "replace")) > MAX_LINE_BYTES:
                res.fail(f"line {lineno}: {len(line)} chars, over the "
                         f"{MAX_LINE_BYTES}-byte cap")
                return res
            try:
                rec = loads_strict(line)
            except Exception as exc:
                res.fail(f"line {lineno}: unreadable ({type(exc).__name__}: {exc})")
                return res

            payload = rec.get("payload")
            got_hash = rec.get("hash")
            got_prev = rec.get("prev")
            if not isinstance(payload, dict) or not isinstance(got_hash, str) \
                    or not isinstance(got_prev, str):
                res.fail(f"line {lineno}: record is missing payload/hash/prev")
                return res

            if got_prev != prev_hash:
                res.fail(f"line {lineno}: prev hash mismatch -- record claims "
                         f"{got_prev[:16]}..., chain says {prev_hash[:16]}.... "
                         f"The break is at or before this line.")
                return res

            try:
                want_hash = chain_hash(got_prev, payload)
            except ValueError as exc:
                res.fail(f"line {lineno}: payload not canonically hashable ({exc})")
                return res
            if want_hash != got_hash:
                res.fail(f"line {lineno}: HASH MISMATCH -- stored {got_hash[:16]}..., "
                         f"recomputed {want_hash[:16]}.... This record's contents "
                         f"were changed after it was sealed.")
                return res

            seq = payload.get("seq")
            if seq != expected_seq:
                res.fail(f"line {lineno}: sequence is {seq!r}, expected {expected_seq}")
                return res
            expected_seq += 1

            # CHAIN-MONOTONIC TIMESTAMPS. The settle-after-seal rule below is
            # only as good as the clock that wrote both numbers: a wall clock
            # that steps backwards (NTP correction, DST-mangled RTC, a VM
            # restored from a snapshot) would let a settle be written with a
            # timestamp before its seal and look perfectly ordered. Requiring
            # the whole chain to be non-decreasing turns that into a visible
            # break at the record where the clock moved, which is also the only
            # place a human could act on it.
            rec_ts = payload.get("ts")
            if not isinstance(rec_ts, (int, float)) or isinstance(rec_ts, bool) \
                    or not math.isfinite(rec_ts):
                res.fail(f"line {lineno}: record ts is not a finite number")
                return res
            if float(rec_ts) < prev_ts:
                res.fail(f"line {lineno}: timestamp {rec_ts} is BEFORE the "
                         f"previous record's {prev_ts}. The clock moved "
                         f"backwards between appends; this ledger's ordering "
                         f"cannot be trusted from here on.")
                return res
            prev_ts = float(rec_ts)

            kind = payload.get("kind")
            if kind == "GENESIS":
                if lineno != 1:
                    res.fail(f"line {lineno}: a second GENESIS record")
                    return res
                schema = payload.get("schema")
                if schema not in SUPPORTED_SCHEMAS:
                    res.fail(f"line 1: ledger declares schema {schema!r}; this "
                             f"build supports {sorted(SUPPORTED_SCHEMAS)}. "
                             f"Refusing to read old records under new rules. "
                             f"Start a new ledger, or run the build that wrote "
                             f"this one.")
                    return res
            elif kind == "SEAL":
                bad = _seal_shape_problem(payload)
                if bad:
                    res.fail(f"line {lineno}: {bad}")
                    return res
                seal_by_seq[int(seq)] = payload
                res.seals += 1
            elif kind == "SETTLE":
                bad = _settle_shape_problem(payload)
                if bad:
                    res.fail(f"line {lineno}: {bad}")
                    return res
                ref = int(payload["seal_seq"])
                seal = seal_by_seq.get(ref)
                if seal is None:
                    res.fail(f"line {lineno}: settles seq {ref}, which is not an "
                             f"earlier SEAL in this chain")
                    return res
                if ref in settled_seqs:
                    res.fail(f"line {lineno}: seq {ref} was already settled on line "
                             f"{settled_seqs[ref]}. A sealed call cannot be "
                             f"re-scored after the fact.")
                    return res
                if not float(payload["ts"]) > float(seal["ts"]):
                    res.fail(f"line {lineno}: settle ts {payload['ts']} is not "
                             f"strictly after seal ts {seal['ts']}. This is the "
                             f"look-ahead shape; refused.")
                    return res
                settled_seqs[ref] = lineno
                res.settles += 1
            else:
                res.fail(f"line {lineno}: unknown record kind {kind!r}")
                return res

            res.records.append({"line": lineno, **rec})
            prev_hash = got_hash

        if not res.records:
            res.fail("ledger is empty")
        elif res.records[0]["payload"].get("kind") != "GENESIS":
            res.fail("line 1 is not the GENESIS record")
        return res

    # -- writing ---------------------------------------------------------

    def _tip(self) -> Tuple[str, int, float]:
        """(prev_hash, next_seq) -- from a FULL verify, never from the tail.

        Reading only the last line to get the tip would let a break earlier in
        the file survive every future append and be discovered months later
        with the whole record in doubt. Verify costs a file read; being wrong
        here costs the ledger.
        """
        if not self.exists():
            return GENESIS_PREV, 0, float("-inf")
        res = self.verify()
        if not res.ok:
            raise LedgerRefused(
                "refusing to append to a ledger that does not verify:\n  - "
                + "\n  - ".join(res.problems))
        last = res.records[-1]
        return (str(last["hash"]), int(last["payload"]["seq"]) + 1,
                float(last["payload"]["ts"]))

    def _append(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with AppendLock(self.path):
            prev_hash, seq, tip_ts = self._tip()
            payload = dict(payload)
            if float(payload.get("ts", 0.0)) < tip_ts:
                raise LedgerRefused(
                    f"refusing to append a record timestamped "
                    f"{payload.get('ts')} behind the ledger tip's {tip_ts}. "
                    f"The system clock moved backwards. Fix the clock; do not "
                    f"append until it is right, because every ordering guard "
                    f"in this file reads that number.")
            payload["seq"] = seq
            rec = {"payload": payload, "prev": prev_hash,
                   "hash": chain_hash(prev_hash, payload)}
            line = json.dumps(rec, sort_keys=True, separators=(",", ":"),
                              ensure_ascii=True, allow_nan=False)
            with open(self.path, "a", encoding="ascii", newline="\n") as fh:
                fh.write(line + "\n")
                fh.flush()
                os.fsync(fh.fileno())
        return rec

    def ensure_genesis(self) -> None:
        if self.exists():
            return
        self._append({
            "kind": "GENESIS",
            "ts": time.time(),
            "schema": SCHEMA_VERSION,
            "note": "sealed-signal ledger; calls not orders; see paper_run.py",
        })


def _seal_shape_problem(p: Dict[str, Any]) -> Optional[str]:
    """Validate a SEAL read back off disk. Every field, every time."""
    asset = p.get("asset")
    if not isinstance(asset, str) or not asset or len(asset) > MAX_ASSET_CHARS \
            or not asset.replace("-", "").isalnum():
        return f"SEAL has a bad asset {asset!r}"
    if p.get("target") not in (-1, 0, 1) or isinstance(p.get("target"), bool):
        return f"SEAL target must be -1, 0 or +1, got {p.get('target')!r}"
    px = p.get("ref_px")
    if isinstance(px, bool) or not isinstance(px, (int, float)) or not (px > 0) \
            or not math.isfinite(px):
        return f"SEAL ref_px must be a positive finite number, got {px!r}"
    ts = p.get("ts")
    if isinstance(ts, bool) or not isinstance(ts, (int, float)) or not math.isfinite(ts):
        return f"SEAL ts must be a finite number, got {ts!r}"
    cap = p.get("capital")
    if isinstance(cap, bool) or not isinstance(cap, (int, float)) or not (cap > 0):
        return f"SEAL capital must be positive, got {cap!r}"
    bps = p.get("cost_bps")
    if isinstance(bps, bool) or not isinstance(bps, (int, float)) or bps < 0:
        return f"SEAL cost_bps must be >= 0, got {bps!r}"
    note = p.get("note", "")
    if not isinstance(note, str) or len(note) > MAX_NOTE_CHARS:
        return "SEAL note is not a string within the length cap"
    rule = p.get("rule", "")
    if not isinstance(rule, str) or len(rule) > MAX_RULE_CHARS:
        return "SEAL rule is not a string within the length cap"
    conv = p.get("price_convention")
    if conv not in PRICE_CONVENTIONS:
        return (f"SEAL price_convention must be one of "
                f"{sorted(PRICE_CONVENTIONS)}, got {conv!r}")
    ri = p.get("rule_inputs", None)
    if ri is not None and not isinstance(ri, dict):
        return f"SEAL rule_inputs must be an object or null, got {type(ri).__name__}"
    return None


def _settle_shape_problem(p: Dict[str, Any]) -> Optional[str]:
    ref = p.get("seal_seq")
    if isinstance(ref, bool) or not isinstance(ref, int) or ref < 0:
        return f"SETTLE seal_seq must be a non-negative int, got {ref!r}"
    px = p.get("exit_px")
    if isinstance(px, bool) or not isinstance(px, (int, float)) or not (px > 0) \
            or not math.isfinite(px):
        return f"SETTLE exit_px must be a positive finite number, got {px!r}"
    ts = p.get("ts")
    if isinstance(ts, bool) or not isinstance(ts, (int, float)) or not math.isfinite(ts):
        return f"SETTLE ts must be a finite number, got {ts!r}"
    conv = p.get("price_convention")
    if conv not in PRICE_CONVENTIONS:
        return (f"SETTLE price_convention must be one of "
                f"{sorted(PRICE_CONVENTIONS)}, got {conv!r}")
    return None


# --------------------------------------------------------------------------
# Costs. Imported, never reimplemented.
# --------------------------------------------------------------------------

def load_cost_model(bps: float):
    """covenant_backtest.CostModel or nothing.

    A second local implementation of the cost convention is exactly the
    duplication this codebase argues against elsewhere ("one pattern, not
    two"): two cost models drift, and the drift shows up as a P&L difference
    nobody can attribute. So the integrity half of this file (--seal,
    --settle, --verify) has NO dependency at all, and only --report needs
    covenant_backtest. If it is missing, --report fails closed and says which
    file it wanted, rather than scoring with a convention it invented.
    """
    try:
        from covenant_backtest import CostModel        # type: ignore
    except Exception as exc:
        raise LedgerUnavailable(
            f"--report needs covenant_backtest.CostModel and could not import "
            f"it ({type(exc).__name__}: {exc}). The ledger's integrity does "
            f"not depend on it -- --verify still works -- but scoring does, "
            f"and this file will not invent a second cost convention."
        ) from exc
    for kwargs in ({"round_trip_bps": bps}, {"bps": bps}, {}):
        try:
            model = CostModel(**kwargs)               # type: ignore[arg-type]
        except TypeError:
            continue
        if not (hasattr(model, "fill_price") and hasattr(model, "fee")):
            raise LedgerUnavailable(
                "covenant_backtest.CostModel lacks fill_price/fee; the shape "
                "this file was written against has changed. Stopping rather "
                "than guessing.")
        return model
    raise LedgerUnavailable(
        f"could not construct CostModel with a {bps} bps round trip; inspect "
        f"its signature and update load_cost_model() deliberately.")


# --------------------------------------------------------------------------
# Statistics
# --------------------------------------------------------------------------

def binom_tail_ge(k: int, n: int) -> float:
    """P(X >= k | n, p=0.5), exact."""
    if n <= 0:
        return 1.0
    k = max(0, min(k, n))
    return sum(math.comb(n, i) for i in range(k, n + 1)) / (2.0 ** n)


def binom_tail_le(k: int, n: int) -> float:
    if n <= 0:
        return 1.0
    k = max(0, min(k, n))
    return sum(math.comb(n, i) for i in range(0, k + 1)) / (2.0 ** n)


def binom_two_sided(k: int, n: int) -> float:
    """Exact two-sided sign test at p=0.5 (symmetric, so 2*min tail)."""
    if n <= 0:
        return 1.0
    return min(1.0, 2.0 * min(binom_tail_ge(k, n), binom_tail_le(k, n)))


def moments(xs: List[float]) -> Tuple[float, float, float, float]:
    """(mean, sd, skew, PEARSON kurtosis with normal == 3).

    Pearson, not excess. The PSR formula below wants (gamma4 - 1)/4 with
    gamma4 = 3 for a normal; feeding it excess kurtosis silently shifts every
    probability. Stated here because the two conventions differ by exactly the
    kind of 3 that never raises an exception.
    """
    n = len(xs)
    if n < 2:
        return (xs[0] if xs else 0.0), 0.0, 0.0, 3.0
    mean = sum(xs) / n
    var = sum((x - mean) ** 2 for x in xs) / (n - 1)
    sd = math.sqrt(var)
    if sd <= 0:
        return mean, 0.0, 0.0, 3.0
    m3 = sum((x - mean) ** 3 for x in xs) / n
    m4 = sum((x - mean) ** 4 for x in xs) / n
    pop_sd = math.sqrt(sum((x - mean) ** 2 for x in xs) / n)
    skew = m3 / (pop_sd ** 3)
    kurt = m4 / (pop_sd ** 4)
    return mean, sd, skew, kurt


def probabilistic_sharpe(sr: float, sr_star: float, T: int,
                         skew: float, kurt: float) -> Optional[float]:
    """PSR(sr*) = Phi[ (sr - sr*) sqrt(T-1) / sqrt(1 - g3 sr + (g4-1)/4 sr^2) ].

    sr is PER OBSERVATION, in the same frequency as the returns -- not
    annualised. Returns None when the denominator is not positive, which
    happens for extreme skew/kurtosis combinations; a formula outside its
    domain returns nothing here rather than a plausible number.
    """
    if T < 3:
        return None
    denom_sq = 1.0 - skew * sr + ((kurt - 1.0) / 4.0) * sr * sr
    if denom_sq <= 0:
        return None
    z = (sr - sr_star) * math.sqrt(T - 1) / math.sqrt(denom_sq)
    return NormalDist().cdf(z)


def expected_max_sharpe(trial_sr_variance: float, n_trials: int) -> Optional[float]:
    """Bailey & Lopez de Prado's E[max SR] over n independent trials.

    SR0 = sqrt(V[SR]) * [ (1-g) Z^-1(1 - 1/N) + g Z^-1(1 - 1/(N e)) ]

    N must be >= 2: at N = 1, Z^-1(0) is -inf and the whole deflation
    collapses to PSR(0), which is the most flattering reading available. That
    is why --trials is REQUIRED and has no default. A DSR computed with an
    unstated trial count is not a deflated Sharpe; it is a Sharpe with a
    better name.
    """
    if n_trials < 2 or trial_sr_variance <= 0:
        return None
    inv = NormalDist().inv_cdf
    a = inv(1.0 - 1.0 / n_trials)
    b = inv(1.0 - 1.0 / (n_trials * math.e))
    return math.sqrt(trial_sr_variance) * ((1.0 - EULER_GAMMA) * a + EULER_GAMMA * b)


# --------------------------------------------------------------------------
# Scoring: pair seals with settles, price them, compare to buy-and-hold
# --------------------------------------------------------------------------

class Scored:
    __slots__ = ("seq", "asset", "target", "ref_px", "exit_px", "seal_ts",
                 "exit_ts", "capital", "cost_bps", "pnl", "ret", "bh_ret",
                 "flat", "policy_class", "rule", "convention")

    def __init__(self, **kw: Any) -> None:
        for k in self.__slots__:
            setattr(self, k, kw.get(k))


def score(records: List[Dict[str, Any]], cost: Any) -> Tuple[List[Scored], List[str]]:
    """Turn a verified chain into settled, priced signals.

    Convention, identical to covenant_backtest.PaperTrader.settle and to
    d2_regime_deep.py so the paper record and the backtest are comparable:
    entry fills at cost.fill_price(ref_px, side), exit at
    cost.fill_price(exit_px, -side), and the round-trip fee is charged twice
    on the notional. A target of 0 is a FLAT call: it is recorded, it counts
    toward "sealed", and it is excluded from the sign test rather than being
    scored as a win with zero return.
    """
    notes: List[str] = []
    seals: Dict[int, Dict[str, Any]] = {}
    out: List[Scored] = []
    cost_bps_seen = set()
    conventions_seen = set()

    for rec in records:
        p = rec["payload"]
        if p.get("kind") == "SEAL":
            seals[int(p["seq"])] = p
            cost_bps_seen.add(float(p["cost_bps"]))
            conventions_seen.add(str(p.get("price_convention", "unspecified")))

    if len(cost_bps_seen) > 1:
        notes.append(
            f"MIXED COST CONVENTIONS in one ledger: {sorted(cost_bps_seen)} bps. "
            f"These records do not aggregate. Split the ledger by convention "
            f"before believing any headline number.")
    if len(conventions_seen) > 1:
        notes.append(
            f"MIXED PRICE CONVENTIONS in one ledger: {sorted(conventions_seen)}. "
            f"A call sealed against a daily close and a call sealed against a "
            f"spot tick are not the same experiment, and only 'daily_close' is "
            f"comparable with d2_regime_deep.py. These records do not aggregate.")
    elif conventions_seen and conventions_seen != {"daily_close"}:
        notes.append(
            f"PRICE CONVENTION IS {sorted(conventions_seen)[0]!r}, NOT "
            f"'daily_close'. The backtest this record would be compared against "
            f"decides at the close of bar t and fills at the open of t+1. "
            f"Nothing here is comparable with those numbers.")

    for rec in records:
        p = rec["payload"]
        if p.get("kind") != "SETTLE":
            continue
        seal = seals.get(int(p["seal_seq"]))
        if seal is None:
            # AUDIT (same session). Only reachable if a caller scores records
            # that did not come from a passing verify(). Today nothing does.
            # "Today nothing does" is how orphaned code becomes a crash later.
            raise LedgerRefused(
                f"settle at seq {p['seq']} references seal "
                f"{p['seal_seq']}, which is not in these records. score() "
                f"takes VERIFIED records only.")
        side = int(seal["target"])
        ref_px = float(seal["ref_px"])
        exit_px = float(p["exit_px"])
        capital = float(seal["capital"])

        # Buy-and-hold over the SAME interval, paying the same round trip.
        # This is the paired comparison graduation asks for: not "the rule vs
        # the market over a year" but "this call vs simply having held the
        # asset from the moment of the call to the moment it was scored".
        bh_entry = cost.fill_price(ref_px, 1)
        bh_exit = cost.fill_price(exit_px, -1)
        bh_pnl = (bh_exit - bh_entry) * (capital / bh_entry) - cost.fee(capital) * 2
        bh_ret = bh_pnl / capital

        if side == 0:
            pnl, ret, flat = 0.0, 0.0, True
        else:
            entry = cost.fill_price(ref_px, side)
            exit_ = cost.fill_price(exit_px, -side)
            pnl = side * (exit_ - entry) * (capital / entry) - cost.fee(capital) * 2
            ret, flat = pnl / capital, False

        out.append(Scored(
            seq=int(seal["seq"]), asset=str(seal["asset"]), target=side,
            ref_px=ref_px, exit_px=exit_px, seal_ts=float(seal["ts"]),
            exit_ts=float(p["ts"]), capital=capital,
            cost_bps=float(seal["cost_bps"]), pnl=pnl, ret=ret, bh_ret=bh_ret,
            flat=flat, policy_class=str(seal.get("policy_class", "")),
            rule=str(seal.get("rule", "")),
            convention=str(seal.get("price_convention", "unspecified"))))

    # A seal priced one way and settled another is a per-signal mismatch the
    # ledger-wide check above cannot see.
    mismatched = 0
    for rec in records:
        p = rec["payload"]
        if p.get("kind") != "SETTLE":
            continue
        seal = seals[int(p["seal_seq"])]
        if p.get("price_convention") != seal.get("price_convention"):
            mismatched += 1
    if mismatched:
        notes.append(
            f"{mismatched} signal(s) were SEALED under one price convention and "
            f"SETTLED under another. Entry and exit are then measured on "
            f"different clocks and the return is partly an artifact of that.")
    return out, notes


# --------------------------------------------------------------------------
# The report, and the two guards EXECUTION_ARCHITECTURE.md says must not be
# removed.
# --------------------------------------------------------------------------

MIN_SCORED_SIGNALS = 30      # graduation floor; see the guard note below


def open_calls(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Seals with no settle. Sorted oldest first."""
    settled = {int(r["payload"]["seal_seq"]) for r in records
               if r["payload"]["kind"] == "SETTLE"}
    return sorted((r["payload"] for r in records
                   if r["payload"]["kind"] == "SEAL"
                   and int(r["payload"]["seq"]) not in settled),
                  key=lambda p: float(p["ts"]))


def build_report(scored: List[Scored], policy: Policy, n_sealed: int,
                 trials: Optional[int], trial_sr_var: Optional[float],
                 extra_notes: List[str],
                 unsettled: Optional[List[Dict[str, Any]]] = None,
                 min_hold_seconds: float = 72000.0) -> Dict[str, Any]:
    """Everything the ledger can honestly say, and nothing else.

    GUARD 1 -- NOT ENOUGH DATA below 30 scored signals, REGARDLESS of the
    numbers. EXECUTION_ARCHITECTURE.md: "A 7-2 record occurs by chance ~9% of
    the time." The guard is not a warning printed next to an encouraging
    headline; the headline is withheld. A number a reader can see is a number
    a reader will quote.

    GUARD 2 -- TWO-SIDED REPORTING. The one-sided "better than a coin flip"
    test reports p = 1.000 for a catastrophic record, which is true and badly
    misleading. A strongly INVERTED record is not a null result: it has
    predictive content pointing the other way and should be investigated, not
    filed as noise. Both p-values are always printed, and an inverted record
    is called out by name.
    """
    rep: Dict[str, Any] = {
        "generated_at": time.time(),
        "platform": platform.platform(),          # CONTRIBUTING section 8
        "python": platform.python_version(),
        "code": _source_fingerprint(),
        "policy_sha256": policy.sha256,
        "sealed": n_sealed,
        "scored": len(scored),
        "notes": list(extra_notes),
        "enough_data": len(scored) >= MIN_SCORED_SIGNALS,
    }

    directional = [s for s in scored if not s.flat]
    flats = len(scored) - len(directional)
    rep["directional"] = len(directional)
    rep["flat_calls"] = flats

    # THE HOLE THE HASH CHAIN CANNOT CLOSE, stated at the top of every report.
    #
    # This ledger makes it impossible to revise a call after seeing the
    # outcome. It does NOT make it impossible to CHOOSE WHICH CALLS TO SETTLE.
    # Sealing forty and scoring the thirty that went well is survivorship bias
    # with a hash chain around it, and every integrity mechanism in this file
    # would report the result as clean. No code can prevent that -- the person
    # running it decides -- so the only honest thing available is to MEASURE
    # the discretion: how many calls are outstanding, and how long they have
    # been outstanding past the point where they could have been settled.
    unsettled = unsettled or []
    now = time.time()
    overdue = [p for p in unsettled
               if (now - float(p["ts"])) > min_hold_seconds]
    rep["unsettled"] = len(unsettled)
    rep["overdue_unsettled"] = len(overdue)
    rep["oldest_unsettled_days"] = (
        max((now - float(p["ts"])) / 86400.0 for p in unsettled)
        if unsettled else 0.0)
    denom = len(scored) + len(overdue)
    rep["discretion_fraction"] = (len(overdue) / denom) if denom else 0.0
    rep["warn_selection_bias"] = bool(overdue)
    if overdue:
        rep["notes"].append(
            f"SETTLEMENT DISCRETION: {len(overdue)} call(s) are past their "
            f"holding period and still unsettled (oldest "
            f"{rep['oldest_unsettled_days']:.1f} days). The hash chain stops a "
            f"call being re-scored; it cannot stop a call being LEFT unscored. "
            f"Sealing forty and settling the thirty that went well is "
            f"survivorship bias with a chain around it, and every check in "
            f"this file would still report clean. Settle them (--settle-due) "
            f"or say in writing why they are excluded. Until then this record "
            f"is {rep['discretion_fraction'] * 100:.0f}% discretionary.")

    if not rep["enough_data"]:
        rep["headline"] = "NOT ENOUGH DATA"
        rep["headline_reason"] = (
            f"{len(scored)} scored signal{'' if len(scored) == 1 else 's'} "
            f"against a floor of "
            f"{MIN_SCORED_SIGNALS}. No win rate, no p-value and no Sharpe is "
            f"reported below the floor, however the numbers look -- a 7-2 "
            f"record happens by chance about 9% of the time.")
        rep["warn_not_independent"] = False
        rep["warn_convention"] = any("CONVENTION" in n for n in rep["notes"])
        rep["warn_bh_uninformative"] = False
        rep["gate"] = _gate(rep, policy, None, None, None)
        return rep

    # THE BUY-AND-HOLD COMPARISON RUNS OVER **ALL** SCORED CALLS, FLATS
    # INCLUDED, and this is the whole of it. Caught by looking at the first
    # full demo report rather than by reading the code: a +1 call over an
    # interval IS buy-and-hold over that interval, exactly, by construction
    # (same entry, same exit, same round trip). So a comparison restricted to
    # directional calls prints "rule -0.0590 vs B&H -0.0590, paired 0/0" for
    # every record ever produced -- a degenerate identity dressed as a
    # measurement, and a gate line that can never pass and never says why.
    #
    # The flat calls ARE the rule. A long-or-flat regime rule differs from
    # holding in exactly one place: the intervals it sits out. Excluding them
    # from the comparison excludes the only thing being tested.
    #
    # The sign test below still runs on DIRECTIONAL calls only -- a flat call
    # is not a win and not a loss, and scoring a zero return as a "win" is the
    # same dishonesty in the other direction.
    rets = [s.ret for s in directional]
    rets_all = [s.ret for s in scored]
    bh = [s.bh_ret for s in scored]
    wins = sum(1 for r in rets if r > 0)
    losses = sum(1 for r in rets if r < 0)
    ties = sum(1 for r in rets if r == 0.0)
    n_signed = wins + losses

    mean, sd, skew, kurt = moments(rets)
    sr = (mean / sd) if sd > 0 else 0.0

    p_one = binom_tail_ge(wins, n_signed)      # "better than a coin flip"
    p_two = binom_two_sided(wins, n_signed)    # GUARD 2
    p_inv = binom_tail_le(wins, n_signed)      # "worse than a coin flip"

    psr0 = probabilistic_sharpe(sr, 0.0, len(rets), skew, kurt)
    sr0 = expected_max_sharpe(trial_sr_var, trials) \
        if (trials is not None and trial_sr_var is not None) else None
    dsr = probabilistic_sharpe(sr, sr0, len(rets), skew, kurt) if sr0 is not None else None

    # INDEPENDENCE, MEASURED RATHER THAN ASSUMED. The binomial sign test above
    # assumes the calls are independent draws. Thirty calls across seven assets
    # over overlapping weeks are not: crypto majors move together, so a single
    # good fortnight can supply most of the "wins" and the p-value reads far
    # better than the evidence warrants. D2 needed a block bootstrap for
    # exactly this reason. This file cannot fix it -- what it can do is refuse
    # to hide it, by measuring how much of the record actually overlaps.
    windows = sorted((s.seal_ts, s.exit_ts) for s in scored)
    overlaps = sum(1 for i in range(len(windows)) for j in range(i + 1, len(windows))
                   if windows[j][0] < windows[i][1])
    n_pairs = len(windows) * (len(windows) - 1) // 2
    overlap_fraction = (overlaps / n_pairs) if n_pairs else 0.0
    max_concurrent = 0
    events = sorted([(a, 1) for a, _ in windows] + [(b, -1) for _, b in windows])
    running = 0
    for _, delta in events:
        running += delta
        max_concurrent = max(max_concurrent, running)
    rep["overlap_fraction"] = overlap_fraction
    rep["max_concurrent_calls"] = max_concurrent
    rep["distinct_assets"] = len({s.asset for s in scored})

    paired = [s.ret - s.bh_ret for s in scored]
    paired_wins = sum(1 for d in paired if d > 0)
    paired_signed = sum(1 for d in paired if d != 0)
    # Degenerate case, stated rather than scored: if every call was +1 the rule
    # and buy-and-hold are the same series and the comparison says nothing.
    bh_informative = paired_signed > 0
    beats_bh = (sum(rets_all) > sum(bh)) if bh_informative else None

    rep.update({
        "headline": "SCORED",
        "wins": wins, "losses": losses, "zero_return": ties,
        "win_rate": (wins / n_signed) if n_signed else 0.0,
        "p_one_sided_better": p_one,
        "p_two_sided": p_two,
        "p_one_sided_worse": p_inv,
        "inverted": p_inv < 0.05,
        "mean_ret": mean, "sd_ret": sd, "skew": skew, "kurtosis_pearson": kurt,
        "sharpe_per_signal": sr,
        "psr_vs_zero": psr0,
        "trials": trials, "trial_sr_variance": trial_sr_var,
        "expected_max_sharpe": sr0,
        "deflated_sharpe": dsr,
        "total_ret_rule": sum(rets_all),
        "total_ret_buy_and_hold": sum(bh),
        "beats_buy_and_hold": beats_bh,
        "bh_comparison_informative": bh_informative,
        "paired_vs_bh_wins": paired_wins,
        "paired_vs_bh_signed": paired_signed,
        "paired_vs_bh_p_two_sided": binom_two_sided(paired_wins, paired_signed),
    })

    if dsr is None:
        rep["notes"].append(
            "DEFLATED SHARPE UNAVAILABLE. It needs --trials (how many rule "
            "configurations were actually looked at before this one was "
            "chosen) and --trial-sr-var (the variance of the Sharpe ratios "
            "across those trials). Both are facts about the SEARCH, not about "
            "the data, and this file cannot observe them. Supplying a made-up "
            "N=1 would set the deflation to zero and turn the DSR back into a "
            "plain Sharpe wearing a better name -- so it is reported as "
            "UNAVAILABLE, which is not the same as failing and is certainly "
            "not the same as passing.")
    if overlap_fraction > 0.25 or max_concurrent > 1:
        rep["notes"].append(
            f"CALLS ARE NOT INDEPENDENT: {overlap_fraction * 100:.0f}% of "
            f"signal pairs have overlapping holding windows and up to "
            f"{max_concurrent} were open at once, across "
            f"{rep['distinct_assets']} asset(s). The binomial p-value above "
            f"assumes independent draws and is therefore OPTIMISTIC -- the "
            f"true effective sample is smaller than {len(scored)}. Treat the "
            f"gate's p as a ceiling on the evidence, not a measurement of it, "
            f"and use a block bootstrap (as D2 did) before believing a pass.")
    if not bh_informative:
        rep["notes"].append(
            "BUY-AND-HOLD COMPARISON CARRIES NO INFORMATION for this record: "
            "every scored call was directional, and a +1 call over an interval "
            "IS buy-and-hold over that interval -- same entry, same exit, same "
            "round trip. The comparison only means something once the rule has "
            "sat some intervals out. Reported as UNAVAILABLE, not as a tie.")
    if rep["inverted"]:
        rep["notes"].append(
            f"INVERTED RECORD: {wins} wins in {n_signed} signed calls, "
            f"one-sided p(worse) = {p_inv:.4f}. This is not a null result. A "
            f"rule this reliably wrong has predictive content pointing the "
            f"other way and should be investigated, not filed as noise.")

    rep["warn_not_independent"] = bool(
        rep.get("overlap_fraction", 0.0) > 0.25
        or rep.get("max_concurrent_calls", 0) > 1)
    rep["warn_convention"] = any(
        "CONVENTION" in n for n in rep["notes"])
    rep["warn_bh_uninformative"] = not rep.get("bh_comparison_informative", True)
    rep["gate"] = _gate(rep, policy, p_one, dsr, beats_bh)
    return rep


def _gate(rep: Dict[str, Any], policy: Policy, p_one: Optional[float],
          dsr: Optional[float], beats_bh: Optional[bool]) -> Dict[str, Any]:
    """TRADING_POLICY.json graduation_requirements, line by line.

    UNAVAILABLE is its own state and never counts as PASS. The overall verdict
    is PASS only if every line is PASS -- P16's lesson at the gate: quiet
    because healthy and quiet because unmeasurable must not produce the same
    answer.
    """
    g = policy.graduation
    need_n = int(g.get("sealed_signals_scored", MIN_SCORED_SIGNALS))
    need_p = float(g.get("binomial_p_max", 0.05))
    need_dsr = float(g.get("deflated_sharpe_min", 0.95))
    need_bh = bool(g.get("must_beat_buy_and_hold", True))

    lines = []

    def add(name: str, state: str, detail: str) -> None:
        lines.append({"requirement": name, "state": state, "detail": detail})

    n = int(rep.get("scored", 0))
    add("sealed_signals_scored", "PASS" if n >= need_n else "FAIL",
        f"{n} scored, need >= {need_n}")

    if p_one is None:
        add("binomial_p_max", "UNAVAILABLE", "not computed below the data floor")
    else:
        add("binomial_p_max", "PASS" if p_one <= need_p else "FAIL",
            f"one-sided p = {p_one:.4f}, need <= {need_p}")

    if dsr is None:
        add("deflated_sharpe_min", "UNAVAILABLE",
            "needs --trials and --trial-sr-var; see the note above")
    else:
        add("deflated_sharpe_min", "PASS" if dsr >= need_dsr else "FAIL",
            f"DSR = {dsr:.4f}, need >= {need_dsr}")

    if not need_bh:
        add("must_beat_buy_and_hold", "PASS", "not required by policy")
    elif beats_bh is None:
        add("must_beat_buy_and_hold", "UNAVAILABLE",
            "below the data floor" if not rep.get("enough_data")
            else "every scored call was directional, so the comparison is an "
                 "identity and says nothing")
    else:
        add("must_beat_buy_and_hold", "PASS" if beats_bh else "FAIL",
            f"rule {rep.get('total_ret_rule', 0.0):+.4f} vs "
            f"buy-and-hold {rep.get('total_ret_buy_and_hold', 0.0):+.4f} "
            f"(sum of per-signal net returns over ALL scored calls, flats "
            f"included, same intervals, same costs)")

    states = [ln["state"] for ln in lines]
    verdict = "PASS" if all(s == "PASS" for s in states) else (
        "UNAVAILABLE" if "FAIL" not in states else "FAIL")
    return {"lines": lines, "verdict": verdict}


def print_report(rep: Dict[str, Any]) -> None:
    W = 74
    print("=" * W)
    print("PAPER RUN -- SEALED SIGNAL RECORD")
    print("=" * W)
    print(f"  platform     : {rep['platform']} / py {rep['python']}")
    print(f"  sealer       : {rep['code']['sha256'][:16]}... "
          f"({rep['code']['lines']} lines)")
    print(f"  policy       : {rep['policy_sha256'][:16]}...")
    print(f"  sealed       : {rep['sealed']}")
    if rep.get("unsettled"):
        print(f"  unsettled    : {rep['unsettled']} open "
              f"({rep['overdue_unsettled']} past their holding period, oldest "
              f"{rep['oldest_unsettled_days']:.1f}d)")
    if "overlap_fraction" in rep:
        print(f"  independence : {rep['overlap_fraction'] * 100:.0f}% of pairs "
              f"overlap, max {rep['max_concurrent_calls']} open at once, "
              f"{rep['distinct_assets']} asset(s)")
    print(f"  scored       : {rep['scored']}  "
          f"(directional {rep.get('directional', 0)}, flat {rep.get('flat_calls', 0)})")
    print()

    if rep["headline"] == "NOT ENOUGH DATA":
        print("  " + "-" * (W - 4))
        print("  NOT ENOUGH DATA")
        for chunk in _wrap(rep["headline_reason"], W - 4):
            print("  " + chunk)
        print("  " + "-" * (W - 4))
    else:
        print(f"  win rate     : {rep['win_rate']:.3f}  "
              f"({rep['wins']}W / {rep['losses']}L / {rep['zero_return']} zero)")
        print(f"  p one-sided  : {rep['p_one_sided_better']:.4f}   (better than a coin flip)")
        print(f"  p TWO-SIDED  : {rep['p_two_sided']:.4f}   <-- read this one")
        print(f"  p inverted   : {rep['p_one_sided_worse']:.4f}   (worse than a coin flip)")
        print(f"  mean/sd      : {rep['mean_ret']:+.5f} / {rep['sd_ret']:.5f}"
              f"   skew {rep['skew']:+.3f}  kurt {rep['kurtosis_pearson']:.3f}")
        print(f"  Sharpe/sig   : {rep['sharpe_per_signal']:+.4f}")
        psr = rep.get("psr_vs_zero")
        print(f"  PSR vs 0     : {psr:.4f}" if psr is not None else "  PSR vs 0     : n/a")
        dsr = rep.get("deflated_sharpe")
        print(f"  DSR          : {dsr:.4f}" if dsr is not None else "  DSR          : UNAVAILABLE")
        if rep.get("bh_comparison_informative"):
            print(f"  vs buy&hold  : rule {rep['total_ret_rule']:+.4f} vs "
                  f"B&H {rep['total_ret_buy_and_hold']:+.4f}  "
                  f"(paired {rep['paired_vs_bh_wins']}/{rep['paired_vs_bh_signed']}, "
                  f"two-sided p {rep['paired_vs_bh_p_two_sided']:.4f})")
        else:
            print("  vs buy&hold  : UNAVAILABLE -- every call was directional; "
                  "see the note")

    print()
    print("  GRADUATION GATE (TRADING_POLICY.json)")
    for ln in rep["gate"]["lines"]:
        mark = {"PASS": "[PASS]", "FAIL": "[FAIL]", "UNAVAILABLE": "[ ?? ]"}[ln["state"]]
        print(f"    {mark} {ln['requirement']:<26} {ln['detail']}")
    print(f"  VERDICT: {rep['gate']['verdict']}")

    for note in rep["notes"]:
        print()
        for i, chunk in enumerate(_wrap(note, W - 4)):
            print(("  ! " if i == 0 else "    ") + chunk)

    print()
    print("  " + "-" * (W - 4))
    print("  Anchor the record with `--tip` (a 64-hex root over every call,")
    print("  in order), never the ledger file and never a plan.")
    print("  " + "-" * (W - 4))
    print("  This is a MEASUREMENT of a rule, not a recommendation and not a")
    print("  claim of a profit edge. No order is placed, prepared or sized by")
    print("  this file. Every order is L's, by hand. (Section 0; DAILY_CHECK")
    print("  section 7.)")
    print("=" * W)


def _wrap(text: str, width: int) -> List[str]:
    words, line, out = text.split(), "", []
    for w in words:
        if line and len(line) + 1 + len(w) > width:
            out.append(line)
            line = w
        else:
            line = f"{line} {w}".strip()
    if line:
        out.append(line)
    return out


# --------------------------------------------------------------------------
# Prices. Two public venues, and the disagreement is the point.
# --------------------------------------------------------------------------

COINBASE_TICKER = "https://api.exchange.coinbase.com/products/{pair}/ticker"
COINBASE_CANDLES = ("https://api.exchange.coinbase.com/products/{pair}/candles"
                    "?granularity=86400")
KRAKEN_TICKER = "https://api.kraken.com/0/public/Ticker?pair={pair}"
KRAKEN_OHLC = "https://api.kraken.com/0/public/OHLC?pair={pair}&interval=1440"

KRAKEN_PAIR = {
    "XLM": "XXLMZUSD", "SOL": "SOLUSD", "XRP": "XXRPZUSD", "ADA": "ADAUSD",
    "HBAR": "HBARUSD", "CRO": "CROUSD", "ONDO": "ONDOUSD", "PEPE": "PEPEUSD",
    "ATOM": "ATOMUSD", "AVAX": "AVAXUSD", "NEAR": "NEARUSD", "WLFI": "WLFIUSD",
}
# UNCONFIRMED against the live venue. A wrong mapping fails CLOSED (the
# two-venue rule refuses a single quote) rather than sealing a bad price, but
# it will fail, and the fix is to check rather than to guess.
KRAKEN_PAIR_UNCONFIRMED = {"WLFI", "ONDO", "CRO", "PEPE"}

USER_AGENT = "covenant-paper-run/2 (+public market data only)"


def _get_json(url: str, timeout: float) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        if resp.status != 200:
            raise LedgerUnavailable(f"{url} -> HTTP {resp.status}")
        body = resp.read(1 << 20).decode("utf-8", "replace")
    return json.loads(body, parse_constant=_reject_nonfinite)


def _check_symbol(asset: str) -> str:
    """AUDIT (CONTRIBUTING section 6): this module INTERPOLATES `asset` into
    four URLs. do_seal validates before calling; do_settle passes a value read
    back off disk. A guard at one layer is not a guard at the next."""
    asset = str(asset).upper()
    if not asset or len(asset) > MAX_ASSET_CHARS or not asset.isalnum():
        raise LedgerRefused(
            f"refusing to build a price URL from {asset!r}: an asset symbol is "
            f"alphanumeric and at most {MAX_ASSET_CHARS} characters.")
    if asset in NEVER_FETCH:
        raise LedgerRefused(
            f"{asset} is on the never-fetch list. DAILY_CHECK.md section 5: "
            f"Canton is not tradable on Coinbase, the endpoint 404s, and "
            f"impostor tokens use the name. Use --ref-px with a hand-entered "
            f"price and label it, or do not seal on it.")
    return asset


def _coinbase_spot(asset: str, timeout: float) -> float:
    return float(_get_json(COINBASE_TICKER.format(pair=f"{asset}-USD"), timeout)["price"])


def _kraken_spot(asset: str, timeout: float) -> float:
    kp = KRAKEN_PAIR.get(asset)
    if kp is None:
        raise LedgerUnavailable(f"no Kraken pair mapping for {asset}")
    doc = _get_json(KRAKEN_TICKER.format(pair=kp), timeout)
    if doc.get("error"):
        raise LedgerUnavailable(f"kraken error {doc['error']}")
    result = doc["result"]
    return float(result[next(iter(result))]["c"][0])


def _coinbase_daily_close(asset: str, timeout: float) -> Tuple[float, float]:
    """(close, bar_start_epoch) of the last COMPLETED daily bar.

    Coinbase returns [time, low, high, open, close, volume], newest first, at
    UTC-midnight boundaries for granularity 86400. The newest row is TODAY'S
    bar, still forming. PRICE_DATA_INTEGRITY's rule -- and every deep CSV in
    realdata/ -- drops it. So do we: index 1, not index 0. Sealing against a
    forming bar means sealing against a number that changes after it is sealed,
    which is the one thing this ledger exists to prevent.
    """
    rows = _get_json(COINBASE_CANDLES.format(pair=f"{asset}-USD"), timeout)
    if not isinstance(rows, list) or len(rows) < 2:
        raise LedgerUnavailable(f"coinbase candles for {asset}: fewer than 2 bars")
    rows = sorted(rows, key=lambda r: float(r[0]), reverse=True)
    forming, last_complete = rows[0], rows[1]
    if not float(forming[0]) > float(last_complete[0]):
        raise LedgerUnavailable("coinbase candle ordering is not what was assumed")
    return float(last_complete[4]), float(last_complete[0])


def _kraken_daily_close(asset: str, timeout: float) -> Tuple[float, float]:
    kp = KRAKEN_PAIR.get(asset)
    if kp is None:
        raise LedgerUnavailable(f"no Kraken pair mapping for {asset}")
    doc = _get_json(KRAKEN_OHLC.format(pair=kp), timeout)
    if doc.get("error"):
        raise LedgerUnavailable(f"kraken error {doc['error']}")
    result = doc["result"]
    key = next(k for k in result if k != "last")
    rows = sorted(result[key], key=lambda r: float(r[0]), reverse=True)
    if len(rows) < 2:
        raise LedgerUnavailable(f"kraken OHLC for {asset}: fewer than 2 bars")
    last_complete = rows[1]                      # drop the forming bar
    return float(last_complete[4]), float(last_complete[0])


def fetch_price(asset: str, convention: str = DEFAULT_PRICE_CONVENTION,
                timeout: float = 10.0) -> Tuple[float, Dict[str, Any]]:
    """A price BOTH venues agree on, or no price at all.

    Two changes from the first cut of this function, both of which were wrong
    in ways that only show up in the record months later:

    1. THE SEALED PRICE IS A REAL QUOTED NUMBER, NOT A MIDPOINT. The first
       version sealed (coinbase + kraken) / 2 -- a price no venue ever quoted
       and no order could ever have filled at. Coinbase is the primary because
       VERIFIED_BASELINE_2026-08-19.md is a Coinbase baseline and the deep CSVs
       were cross-checked against it; Kraken is recorded beside it as the
       cross-check, with the spread. Both numbers are in the record, so a later
       reader can recompute either way.

    2. THE DEFAULT IS THE DAILY CLOSE, NOT THE SPOT TICKER. d2_regime_deep.py
       decides at the close of bar t. A ticker read at 14:12 on a Tuesday is a
       different experiment, and comparing the two is the silent kind of wrong.
       Spot is still available and still recorded as such -- it is just never
       the default and never comparable with D2.

    ONE VENUE ANSWERING IS NOT A FALLBACK. Two independent venues quoting the
    same asset should agree to well under a percent; when they do not, the
    number is not a price, it is a symptom -- a stale cache, a thin book, a
    wrong pair mapping, or the SOL-not-on-this-venue class of bug that
    EXECUTION_ARCHITECTURE.md caught once already. A sealed record is forever;
    a missed day is a missed day.
    """
    asset = _check_symbol(asset)
    if convention not in ("daily_close", "spot_ticker"):
        raise LedgerRefused(f"cannot fetch convention {convention!r}")

    quotes: Dict[str, float] = {}
    bar_starts: Dict[str, float] = {}
    errors: Dict[str, str] = {}

    for venue, spot_fn, close_fn in (("coinbase", _coinbase_spot, _coinbase_daily_close),
                                     ("kraken", _kraken_spot, _kraken_daily_close)):
        try:
            if convention == "spot_ticker":
                quotes[venue] = spot_fn(asset, timeout)
            else:
                px, bar = close_fn(asset, timeout)
                quotes[venue], bar_starts[venue] = px, bar
        except Exception as exc:
            errors[venue] = f"{type(exc).__name__}: {exc}"

    if len(quotes) < 2:
        hint = ""
        if asset in KRAKEN_PAIR_UNCONFIRMED:
            hint = (f" NOTE: the Kraken pair mapping for {asset} is marked "
                    f"UNCONFIRMED in this file -- check it before assuming the "
                    f"venue is down.")
        raise LedgerUnavailable(
            f"need both venues to seal {asset}; got {sorted(quotes)} "
            f"(errors: {errors}). Refusing to seal against a single quote.{hint}")

    a, b = quotes["coinbase"], quotes["kraken"]
    if not (a > 0 and b > 0):
        raise LedgerRefused(f"non-positive quote for {asset}: {quotes}")
    spread_pct = abs(a - b) / ((a + b) / 2.0) * 100.0
    if spread_pct > MAX_VENUE_DISAGREEMENT_PCT:
        raise LedgerRefused(
            f"{asset}: coinbase {a} vs kraken {b} disagree by "
            f"{spread_pct:.3f}% (cap {MAX_VENUE_DISAGREEMENT_PCT}%). That is "
            f"not a price. Not sealing.")

    if convention == "daily_close" and len(bar_starts) == 2:
        gap = abs(bar_starts["coinbase"] - bar_starts["kraken"])
        if gap > 3600.0:
            raise LedgerRefused(
                f"{asset}: the two venues' last completed daily bars start "
                f"{gap / 3600.0:.1f}h apart ({bar_starts}). They are not "
                f"quoting the same day. Not sealing.")

    src = {"source": "coinbase+kraken", "primary": "coinbase",
           "coinbase": a, "kraken": b, "spread_pct": round(spread_pct, 5),
           "fetched_at": round(time.time(), 3)}
    if bar_starts:
        src["bar_start"] = bar_starts.get("coinbase")
    return a, src


# --------------------------------------------------------------------------
# The rule. One rule, the one D2 measured, and its verdict travels with it.
# --------------------------------------------------------------------------

def daily_closes(asset: str, timeout: float = 10.0) -> Tuple[List[float], Dict[str, Any]]:
    """Completed daily closes, oldest first, from the primary venue.

    The forming bar is dropped here for the same reason it is dropped in
    _coinbase_daily_close and in every CSV under realdata/: a bar that is still
    forming is a number that changes after you have used it.

    UNVERIFIED: no response from this endpoint has ever been seen by this file.
    Coinbase returns at most ~300 rows per request at granularity 86400, which
    is enough for a 200-bar SMA and not enough for much more. If a longer
    window is ever wanted, this is where the paging has to be written, honestly
    and with the seams visible -- not by quietly reusing whatever came back.
    """
    asset = _check_symbol(asset)
    rows = _get_json(COINBASE_CANDLES.format(pair=f"{asset}-USD"), timeout)
    if not isinstance(rows, list) or len(rows) < 2:
        raise LedgerUnavailable(f"coinbase candles for {asset}: fewer than 2 bars")
    rows = sorted(rows, key=lambda r: float(r[0]))          # oldest first
    completed = rows[:-1]                                    # drop the forming bar
    closes = [float(r[4]) for r in completed]
    meta = {"venue": "coinbase", "bars": len(closes),
            "first_bar": float(completed[0][0]),
            "last_bar": float(completed[-1][0])}
    return closes, meta


def regime_target(closes: List[float], window: int = 200) -> Optional[int]:
    """+1 above the SMA(window), 0 below. The rule D2 tested; nothing new.

    Deliberately NOT a new rule. TRADING_READINESS.md section 3: "there is no
    third rule waiting to be tested -- D2 is finished." Inventing a rule here
    to make the paper record look better would be the search that the DSR
    exists to deflate, run in the dark and unreported.

    Returns None when there is not enough history: fewer than `window` closes
    means the rule has not fired, and a rule that has not fired is not a flat
    call -- it is no call. Sealing it as 0 would inflate the sealed count with
    records that carry no information, and the count is a graduation gate.
    """
    if len(closes) < window:
        return None
    sma = sum(closes[-window:]) / window
    return 1 if closes[-1] > sma else 0


# --------------------------------------------------------------------------
# Actions
# --------------------------------------------------------------------------

def do_seal(args: argparse.Namespace) -> int:
    policy = Policy.load(args.policy)
    policy.assert_sealable()

    asset = args.asset.upper()
    if not asset or len(asset) > MAX_ASSET_CHARS or not asset.replace("-", "").isalnum():
        raise LedgerRefused(f"bad asset {args.asset!r}")
    if args.auto_target and args.target is not None:
        raise LedgerRefused("give --target or --auto-target, not both")
    if not args.auto_target and args.target not in (-1, 0, 1):
        raise LedgerRefused("target must be -1, 0 or +1")

    # Argument validation FIRST -- cheap, no I/O, and it keeps the reseal guard
    # below from being the reason a plainly malformed command fails.
    if args.auto_target and not args.fetch:
        raise LedgerRefused(
            "--auto-target needs --fetch: the rule is evaluated on the same "
            "completed daily bars the reference price comes from, or not at all.")
    if args.fetch and args.ref_px is not None:
        raise LedgerRefused("give --ref-px or --fetch, not both")
    if not args.fetch:
        if args.ref_px is None:
            raise LedgerRefused("give --ref-px or --fetch")
        if not (float(args.ref_px) > 0 and math.isfinite(float(args.ref_px))):
            raise LedgerRefused("--ref-px must be a positive finite number")

    ledger = Ledger(args.ledger)

    # ONE CALL PER ASSET PER PERIOD. Without this, thirty sealed signals can be
    # thirty reads of the same Tuesday afternoon on one asset, which reaches
    # the graduation count while carrying almost no information -- and the
    # count is a GATE. A guard on the number is worthless if the number can be
    # padded; guard the thing the number is supposed to stand for.
    if ledger.exists():
        prior = ledger.verify()
        if prior.ok:
            recent = [float(r["payload"]["ts"]) for r in prior.records
                      if r["payload"]["kind"] == "SEAL"
                      and str(r["payload"]["asset"]).upper() == asset]
            if recent:
                gap = time.time() - max(recent)
                if gap < args.min_reseal_seconds:
                    raise LedgerRefused(
                        f"{asset} was last sealed {gap / 3600.0:.1f}h ago and "
                        f"--min-reseal-seconds is "
                        f"{args.min_reseal_seconds / 3600.0:.1f}h. Sealing the "
                        f"same asset again inside one bar pads the count "
                        f"toward 30 without adding a signal. Override "
                        f"deliberately if you mean to.")

    rule_inputs: Optional[Dict[str, Any]] = None
    if args.fetch:
        ref_px, src = fetch_price(asset, args.price_convention)
        convention = args.price_convention
    else:
        ref_px = float(args.ref_px)
        src = {"source": "hand-entered", "fetched_at": round(time.time(), 3)}
        convention = "hand_entered"

    if args.auto_target:
        # THE RULE, ACTUALLY CALLED. Until this pass regime_target() was
        # defined and referenced by nothing -- the exact shape of D4, where
        # guards.py was written, hand-tested, and then imported by no one
        # ("grep -i guard daily.py" returned zero lines). Writing that lesson
        # down in a docstring did not stop it happening again in the file that
        # cited it. The suite now fails on any orphaned public function.
        closes, meta = daily_closes(asset)
        target = regime_target(closes, args.sma_window)
        if target is None:
            raise LedgerRefused(
                f"{asset}: {meta['bars']} completed bars, and the "
                f"{args.sma_window}-bar rule needs {args.sma_window}. The rule "
                f"has not fired, which is NOT a flat call -- it is no call. "
                f"Sealing it as 0 would pad the count with a record that "
                f"carries no signal.")
        sma = sum(closes[-args.sma_window:]) / args.sma_window
        rule_inputs = {"window": args.sma_window, "sma": sma,
                       "close": closes[-1], "bars": meta["bars"],
                       "venue": meta["venue"], "last_bar": meta["last_bar"]}
    else:
        target = int(args.target)

    note = (args.note or "")[:MAX_NOTE_CHARS]
    rule = (args.rule or "")[:MAX_RULE_CHARS]
    capital = float(args.capital) if args.capital is not None else policy.funding_usd
    if not (capital > 0):
        raise LedgerRefused(
            "capital must be positive; the policy's sleeve funding_usd is "
            f"{policy.funding_usd}. Pass --capital explicitly if that is not "
            f"the notional you mean to score against.")

    ledger.ensure_genesis()
    rec = ledger._append({
        "kind": "SEAL",
        "ts": time.time(),
        "asset": asset,
        "target": int(target),
        "ref_px": ref_px,
        "rule": rule,
        "capital": capital,
        "cost_bps": float(args.cost_bps),
        "price_source": src,
        "price_convention": convention,
        "rule_inputs": rule_inputs,
        "policy_sha256": policy.sha256,
        "policy_class": policy.classify(asset),
        "code_sha256": _source_fingerprint()["sha256"],
        "note": note,
    })
    p = rec["payload"]
    print(f"SEALED seq={p['seq']} {asset} target={p['target']:+d} "
          f"ref_px={ref_px} src={src['source']} conv={convention} "
          f"hash={rec['hash'][:16]}...")
    if rule_inputs:
        print(f"  rule: close {rule_inputs['close']:.6g} vs SMA"
              f"{rule_inputs['window']} {rule_inputs['sma']:.6g} over "
              f"{rule_inputs['bars']} completed bars -> target "
              f"{int(target):+d}. Recorded in the seal, so the call can be "
              f"re-derived rather than taken on trust.")
    if convention != "daily_close":
        print(f"  note: convention is {convention}, not daily_close. This call "
              f"is NOT comparable with the D2 backtest numbers.")
    if p["policy_class"] == "locked":
        print(f"  note: {asset} is a LOCKED position. This is a measurement "
              f"record only; the policy holds it and nothing acts on it.")
    print("  This is a call, not an order. Nothing is placed.")
    return 0


def do_settle(args: argparse.Namespace) -> int:
    policy = Policy.load(args.policy)
    policy.assert_sealable()

    ledger = Ledger(args.ledger)
    res = ledger.verify()
    if not res.ok:
        for prob in res.problems:
            print(f"REFUSED: {prob}")
        return 1

    seals = {int(r["payload"]["seq"]): r["payload"]
             for r in res.records if r["payload"]["kind"] == "SEAL"}
    settled = {int(r["payload"]["seal_seq"])
               for r in res.records if r["payload"]["kind"] == "SETTLE"}
    seq = int(args.seq)
    if seq not in seals:
        raise LedgerRefused(f"seq {seq} is not a SEAL in this ledger")
    if seq in settled:
        raise LedgerRefused(
            f"seq {seq} is already settled. A sealed call cannot be re-scored "
            f"after the fact -- that is the property this ledger exists for.")

    seal = seals[seq]
    # Settle under the convention the call was SEALED under, unless told
    # otherwise. Entry on a daily close and exit on a spot tick measures the
    # two clocks as much as the rule.
    convention = args.price_convention if args.price_convention_explicit \
        else str(seal.get("price_convention", DEFAULT_PRICE_CONVENTION))
    if args.fetch:
        if convention == "hand_entered":
            raise LedgerRefused(
                "this call was sealed with a hand-entered price; settle it the "
                "same way with --exit-px, or say --price-convention explicitly "
                "and accept that entry and exit are on different clocks.")
        exit_px, src = fetch_price(str(seal["asset"]), convention)
    else:
        if args.exit_px is None:
            raise LedgerRefused("give --exit-px or --fetch")
        exit_px = float(args.exit_px)
        if not (exit_px > 0 and math.isfinite(exit_px)):
            raise LedgerRefused("--exit-px must be a positive finite number")
        src = {"source": "hand-entered", "fetched_at": round(time.time(), 3)}
        convention = "hand_entered"

    now = time.time()
    if not now > float(seal["ts"]):
        raise LedgerRefused(
            "settle timestamp is not strictly after the seal timestamp. This "
            "is the look-ahead shape and it is refused structurally, not by "
            "care -- see the +112% XLM 'edge' in TRADING_READINESS.md 1b.")
    held = now - float(seal["ts"])
    if held < args.min_hold_seconds:
        raise LedgerRefused(
            f"seq {seq} was sealed {held:.0f}s ago; --min-hold-seconds is "
            f"{args.min_hold_seconds:.0f}. Settling a call minutes after "
            f"sealing it measures the spread, not the rule. Override "
            f"deliberately if you mean to.")

    rec = ledger._append({
        "kind": "SETTLE",
        "ts": now,
        "seal_seq": seq,
        "exit_px": exit_px,
        "price_source": src,
        "price_convention": convention,
        "note": (args.note or "")[:MAX_NOTE_CHARS],
    })
    print(f"SETTLED seq={rec['payload']['seq']} -> seal {seq} "
          f"({seal['asset']} target={int(seal['target']):+d}) "
          f"ref_px={seal['ref_px']} exit_px={exit_px} "
          f"held={held / 86400.0:.2f}d hash={rec['hash'][:16]}...")
    print("  P&L is not printed here on purpose: per-signal outcomes invite")
    print("  reading a record of 3 as if it were a record of 30. Use --report.")
    return 0


def do_settle_due(args: argparse.Namespace) -> int:
    """Settle every call past its holding period, in one command.

    This exists to remove a REASON not to settle. A record where settling is
    fiddly and per-seq is a record where the losers quietly stay open -- and
    the discretion measurement in the report can only name that, not stop it.
    Making the honest action the easy one is the part of the design that is
    actually load-bearing.

    It settles ALL due calls or reports why each one could not be settled. It
    never settles a subset silently, because a partial run that looks like a
    complete one is how a biased record gets built by accident.
    """
    policy = Policy.load(args.policy)
    policy.assert_sealable()
    ledger = Ledger(args.ledger)
    res = ledger.verify()
    if not res.ok:
        for prob in res.problems:
            print(f"REFUSED: {prob}")
        return 1

    now = time.time()
    due = [p for p in open_calls(res.records)
           if (now - float(p["ts"])) >= args.min_hold_seconds]
    if not due:
        print("no calls are due for settlement")
        return 0

    done, failed = 0, []
    for seal in due:
        seq = int(seal["seq"])
        convention = str(seal.get("price_convention", DEFAULT_PRICE_CONVENTION))
        if convention == "hand_entered":
            failed.append((seq, seal["asset"],
                           "sealed with a hand-entered price; settle it by "
                           "hand with --settle --seq"))
            continue
        try:
            exit_px, src = fetch_price(str(seal["asset"]), convention)
            rec = ledger._append({
                "kind": "SETTLE", "ts": time.time(), "seal_seq": seq,
                "exit_px": exit_px, "price_source": src,
                "price_convention": convention, "note": "settle-due"})
            held = (float(rec["payload"]["ts"]) - float(seal["ts"])) / 86400.0
            print(f"SETTLED seq={rec['payload']['seq']} -> seal {seq} "
                  f"({seal['asset']}) exit_px={exit_px} held={held:.2f}d")
            done += 1
        except (LedgerRefused, LedgerUnavailable) as exc:
            failed.append((seq, seal["asset"], str(exc)))

    print(f"settled {done} of {len(due)} due call(s)")
    for seq, asset, why in failed:
        print(f"  NOT SETTLED seq={seq} {asset}: {why}")
    if failed:
        print("  These stay OPEN and are counted as settlement discretion in")
        print("  --report until they are settled or excluded in writing.")
    return 1 if failed else 0


def do_verify(args: argparse.Namespace) -> int:
    ledger = Ledger(args.ledger)
    res = ledger.verify()
    print(f"ledger : {ledger.path}")
    print(f"records: {len(res.records)}  (seals {res.seals}, settles {res.settles})")
    if res.ok:
        tip = res.records[-1]["hash"] if res.records else GENESIS_PREV
        print(f"tip    : {tip}")
        print("CHAIN OK -- every record hashes to the one after it, no seal is")
        print("settled twice, and every settle is strictly after its seal.")
        return 0
    print("CHAIN NOT OK:")
    for prob in res.problems:
        print(f"  - {prob}")
    return 1


def do_status(args: argparse.Namespace) -> int:
    policy = Policy.load(args.policy)
    ledger = Ledger(args.ledger)
    res = ledger.verify()
    settled = {int(r["payload"]["seal_seq"])
               for r in res.records if r["payload"]["kind"] == "SETTLE"}
    open_seals = open_calls(res.records)
    now = time.time()
    overdue = [p for p in open_seals
               if (now - float(p["ts"])) > args.min_hold_seconds]
    need = int(policy.graduation.get("sealed_signals_scored", MIN_SCORED_SIGNALS))
    print(f"ledger  : {ledger.path}")
    print(f"chain   : {'OK' if res.ok else 'BROKEN'}")
    print(f"policy  : mode={policy.mode} funded={policy.funded} "
          f"sha256={policy.sha256[:16]}...")
    print(f"progress: {len(settled)}/{need} scored signals "
          f"({res.seals} sealed, {len(open_seals)} still open)")
    if overdue:
        print(f"OVERDUE : {len(overdue)} call(s) past the holding period and "
              f"still open. Run --settle-due. An unsettled call counts toward "
              f"nothing and reads as settlement discretion in --report.")
    if open_seals:
        print("open calls (seq, asset, target, sealed):")
        for p in open_seals[:40]:
            age = (now - float(p["ts"])) / 86400.0
            mark = " OVERDUE" if (now - float(p["ts"])) > args.min_hold_seconds else ""
            print(f"  {int(p['seq']):>5}  {p['asset']:<6} "
                  f"{int(p['target']):+d}  {age:6.2f}d ago{mark}")
        if len(open_seals) > 40:
            print(f"  ... and {len(open_seals) - 40} more not shown")
    return 0 if res.ok else 1


def do_tip(args: argparse.Namespace) -> int:
    """Print the ledger's tip hash. THIS is the thing to anchor to the chain.

    The original proposal was to seal a pre-planned strategy to the chain and
    approve the trades afterwards. The half of that idea which is sound is
    here: a single 64-hex root that commits to every call in the record, in
    order, without exposing the record itself and without authorising anything.
    Anchor THIS with covenant_anchor.py -- not the ledger, which must stay out
    of the synced folder (section 3 of PAPER_RUN.md), and not a plan, which
    anchoring cannot make legitimate.

    What the anchor then buys, and it is worth having: an independent, dated
    witness that the record existed in this exact form at that block height.
    Re-anchor after each append -- an anchor that is usually stale teaches its
    reader to ignore it (PC_SYNC_LOOP.md).
    """
    res = Ledger(args.ledger).verify()
    if not res.ok:
        print("REFUSING TO PRINT A TIP FOR A LEDGER THAT DOES NOT VERIFY:",
              file=sys.stderr)
        for prob in res.problems:
            print(f"  - {prob}", file=sys.stderr)
        return 1
    tip = res.records[-1]["hash"] if res.records else GENESIS_PREV
    if args.json:
        print(json.dumps({"tip": tip, "records": len(res.records),
                          "seals": res.seals, "settles": res.settles,
                          "ledger": Ledger(args.ledger).path},
                         sort_keys=True))
    else:
        print(tip)
    return 0


def do_gate(args: argparse.Namespace) -> int:
    """Strict mode: exit 0 ONLY if the graduation gate passes.

    Split out from --report on purpose. --report is what a human runs daily and
    it must not paint the terminal red for the entirely normal state of "still
    collecting data" -- 269 identical copies of one permanent condition is what
    SENSING_ACROSS_LAYERS.md calls worse than no channel, because it looks like
    monitoring. --gate is what a script asserts on, and it says nothing new;
    it just turns the verdict into an exit code.
    """
    rc = do_report(args)
    if rc != 0:
        return rc
    return 0 if _LAST_VERDICT.get("verdict") == "PASS" else (
        2 if _LAST_VERDICT.get("verdict") == "UNAVAILABLE" else 1)


_LAST_VERDICT: Dict[str, Any] = {}


def do_report(args: argparse.Namespace) -> int:
    policy = Policy.load(args.policy)
    ledger = Ledger(args.ledger)
    res = ledger.verify()
    if not res.ok:
        print("REFUSING TO SCORE A LEDGER THAT DOES NOT VERIFY:")
        for prob in res.problems:
            print(f"  - {prob}")
        return 1
    cost = load_cost_model(args.cost_bps)
    scored, notes = score(res.records, cost)
    rep = build_report(scored, policy, res.seals, args.trials,
                       args.trial_sr_var, notes,
                       unsettled=open_calls(res.records),
                       min_hold_seconds=args.min_hold_seconds)
    _LAST_VERDICT.clear()
    _LAST_VERDICT["verdict"] = rep["gate"]["verdict"]
    if args.json:
        print(json.dumps(rep, indent=2, sort_keys=True, allow_nan=False))
    else:
        print_report(rep)
    # EXIT 0. The report ran and told the truth; "the gate has not passed" is
    # the expected state for the next thirty days and is not a failure of this
    # command. Use --gate when a script needs the verdict as an exit code.
    return 0


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="paper_run.py",
        description="Sealed-signal ledger. Records calls, never orders.")
    ap.add_argument("--ledger", default=None, help="override the ledger path")
    ap.add_argument("--policy", default=None, help="override TRADING_POLICY.json")
    ap.add_argument("--cost-bps", type=float, default=DEFAULT_COST_BPS_ROUND_TRIP,
                    help="round-trip cost in bps (default 40, matches D2)")

    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--seal", action="store_true")
    mode.add_argument("--settle", action="store_true")
    mode.add_argument("--settle-due", action="store_true",
                      help="settle every call past its holding period")
    mode.add_argument("--verify", action="store_true")
    mode.add_argument("--report", action="store_true")
    mode.add_argument("--status", action="store_true")
    mode.add_argument("--tip", action="store_true",
                      help="print the chain tip hash (this is what to anchor)")
    mode.add_argument("--gate", action="store_true",
                      help="like --report, but exit non-zero unless the "
                           "graduation gate PASSES")

    ap.add_argument("--asset")
    ap.add_argument("--target", type=int)
    ap.add_argument("--auto-target", action="store_true",
                    help="let the rule decide the target from the completed "
                         "daily bars, and record what it saw in the seal")
    ap.add_argument("--sma-window", type=int, default=200,
                    help="the regime rule's window (default 200, as D2 tested)")
    ap.add_argument("--ref-px", type=float)
    ap.add_argument("--exit-px", type=float)
    ap.add_argument("--seq", type=int)
    ap.add_argument("--fetch", action="store_true",
                    help="take the price from Coinbase AND Kraken; both must agree")
    ap.add_argument("--capital", type=float, default=None,
                    help="notional to score against; defaults to the sleeve funding")
    ap.add_argument("--rule", default="sma200_regime_long_or_flat")
    ap.add_argument("--note", default="")
    ap.add_argument("--min-hold-seconds", type=float, default=72000.0,
                    help="refuse to settle a call younger than this (default ~20h)")
    ap.add_argument("--min-reseal-seconds", type=float, default=72000.0,
                    help="refuse to seal the same asset again inside this "
                         "window (default ~20h), so the 30-count cannot be "
                         "padded with repeats of one bar")
    ap.add_argument("--price-convention", default=DEFAULT_PRICE_CONVENTION,
                    choices=sorted(PRICE_CONVENTIONS),
                    help="what a fetched price IS. daily_close is the only one "
                         "comparable with the D2 backtest")
    ap.add_argument("--trials", type=int, default=None,
                    help="how many rule configurations were looked at before "
                         "this one; REQUIRED for a deflated Sharpe")
    ap.add_argument("--trial-sr-var", type=float, default=None,
                    help="variance of the Sharpe ratios across those trials")
    ap.add_argument("--json", action="store_true", help="machine-readable report")
    return ap


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    args = build_parser().parse_args(argv)
    # Whether the user SAID --price-convention matters on settle: unspecified
    # means "inherit what the call was sealed under", which is not the same as
    # "the default happens to equal it".
    args.price_convention_explicit = any(
        a == "--price-convention" or a.startswith("--price-convention=")
        for a in argv)
    try:
        if args.seal:
            return do_seal(args)
        if args.settle:
            return do_settle(args)
        if args.settle_due:
            return do_settle_due(args)
        if args.verify:
            return do_verify(args)
        if args.report:
            return do_report(args)
        if args.tip:
            return do_tip(args)
        if args.gate:
            return do_gate(args)
        return do_status(args)
    except LedgerRefused as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1
    except LedgerUnavailable as exc:
        print(f"UNAVAILABLE: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
