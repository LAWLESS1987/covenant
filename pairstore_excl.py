"""A (signer, nonce) pair-store whose check-and-record is one step ACROSS processes on one machine. Version 2.

Proposed for 1OF1Research/hyb-verifier (hfq001-hyb-verifier-2026-11-17/hyb_verifier.py), same interface as its
PairStore: check_and_record(signer, nonce, exp_epoch) -> bool, contains(signer, nonce), prune(now) -> int, len().

Why: PairStore loads the whole JSON file once per process and checks its own in-memory copy, so two processes can
both accept one receipt; and each persist writes the whole dict over the file, so one process can erase another's
pair (a later verifier then accepts its in-window replay).

How: one file per pair in <store>.pairs/, named by sha256("signer|nonce"), holding exactly b"<exp>\\n<signer|nonce>\\n".
To record: write that body to a temp file, fsync, then os.link(temp, name). On local POSIX and NTFS filesystems a
link to an existing name fails with FileExistsError, so only one link to a name can succeed, and the file has its
full body the moment it appears. If linking fails for any other reason, check_and_record RAISES: it never falls back
and never returns True without a link (fail closed; the verifier's present() propagates the error).

Version 2 changes, from an adversarial review (ChatGPT, Gemini, DeepSeek, Cael, Cipher; 2026-11-18):
  * The O_CREAT|O_EXCL fallback is gone: it published the name before its body, so a concurrent prune could read a
    truncated exp and delete a live pair.
  * Pair files are parsed strictly (full body, trailing newline, and the hash of the key equals the file name).
    Anything else is kept, never pruned, and listed by audit().
  * prune() runs under a cross-process lock (an O_EXCL lock file), so two pruners can never act on one name: with a
    single pruner, a pair file it read cannot be replaced before it unlinks it, because records only ever create
    absent names. A lock older than PRUNE_LOCK_STALE_S is taken over. prune(now, grace) deletes only pairs with
    now >= exp + grace; set grace to cover the clock skew between the pruner and every verifier (see CLOCKS).
  * Orphan temp files (a process killed between write and link) older than TEMP_STALE_S are removed by prune().
  * migrate_json(path, now) imports the still-live pairs of an old PairStore JSON file. Run it once, with every old
    writer stopped, before switching: the two stores do not see each other.
  * The parent directory is fsynced after the pair directory is created (POSIX).

CLOCKS: present() checks expiry with the caller's `now` before recording. If a pruner's clock runs ahead of a
verifier's, the pruner can delete a pair that verifier still considers live; a replay presented to that verifier
would then be accepted. prune's grace must be at least the worst skew between them.

DURABILITY: on POSIX the pair directory is fsynced after each link, so a True return is on disk. Windows has no
O_DIRECTORY; NTFS metadata durability after a power loss is not established here. Network filesystems (NFS, SMB) are
not supported: link and lock-file atomicity there is not guaranteed and was not tested.

TRUST: the pair directory must not be writable by anyone untrusted. Whoever can write there can delete pairs or
plant names; a directory or symlink under a pair name is never read as a record (audit() lists it).

What it does not change: the profile's limits. Wipe the pair directory and replay inside the window, and the
receipt is accepted, exactly as the decision record says.
"""
import hashlib
import json
import os
import re
import stat
import tempfile
import time

PRUNE_LOCK_STALE_S = 600
TEMP_STALE_S = 3600
_NAME = re.compile(r"[0-9a-f]{64}")
_BODY = re.compile(rb"(\d+)\n([^\n]+)\n")


class ExclPairStore:
    def __init__(self, path):
        self.dir = os.path.abspath(str(path)) + ".pairs"
        existed = os.path.isdir(self.dir)
        os.makedirs(self.dir, exist_ok=True)
        if not existed:
            self._fsync_path(os.path.dirname(self.dir))

    # -- helpers ---------------------------------------------------------------------------------------------------
    @staticmethod
    def _key(signer, nonce):
        return signer.lower() + "|" + nonce

    @staticmethod
    def _hash(key):
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    def _name(self, signer, nonce):
        return os.path.join(self.dir, self._hash(self._key(signer, nonce)))

    @staticmethod
    def _fsync_path(path):
        flag = getattr(os, "O_DIRECTORY", None)
        if flag is None:
            return
        fd = os.open(path, flag)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def _read(self, p):
        """exp (int) if the file at p is a complete, matching pair record; None otherwise."""
        st = os.lstat(p)                                # FileNotFoundError propagates to the caller
        if not stat.S_ISREG(st.st_mode):                # a directory or symlink under a pair name: never trusted
            return None
        try:
            with open(p, "rb") as fh:
                raw = fh.read(4096)
        except FileNotFoundError:
            raise
        except OSError:
            return None
        m = _BODY.fullmatch(raw)
        if not m or self._hash(m.group(2).decode("utf-8", "replace")) != os.path.basename(p):
            return None
        return int(m.group(1))

    def _pair_files(self):
        for n in os.listdir(self.dir):
            if _NAME.fullmatch(n):
                yield os.path.join(self.dir, n)

    # -- the interface ---------------------------------------------------------------------------------------------
    def check_and_record(self, signer, nonce, exp_epoch):
        """True if the pair was new and is now recorded (on POSIX: durably); False if any process recorded it
        first. Any other failure raises -- it is never reported as a new pair."""
        key = self._key(signer, nonce)
        final = os.path.join(self.dir, self._hash(key))
        body = ("%d\n%s\n" % (int(exp_epoch), key)).encode("utf-8")
        fd, tmp = tempfile.mkstemp(dir=self.dir, prefix=".tmp-")
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(body)
                fh.flush()
                os.fsync(fh.fileno())
            try:
                os.link(tmp, final)
            except FileExistsError:
                return False
            self._fsync_path(self.dir)
            return True
        finally:
            try:
                os.unlink(tmp)
            except OSError:
                pass

    def contains(self, signer, nonce):
        """Diagnostic only (not a snapshot, never an authorization input)."""
        return os.path.exists(self._name(signer, nonce))

    def __len__(self):
        """Diagnostic only: the number of pair-named files at the moment of listing."""
        return sum(1 for _ in self._pair_files())

    def prune(self, now, grace=0):
        """Drop complete pair records with now >= exp + grace. One pruner at a time across processes; if another
        pruner holds the lock, returns 0 without pruning. Malformed records are kept (see audit())."""
        lock = os.path.join(self.dir, ".prune.lock")
        try:
            lfd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                if time.time() - os.stat(lock).st_mtime <= PRUNE_LOCK_STALE_S:
                    return 0
                stale = lock + ".stale-%d-%d" % (os.getpid(), time.time_ns())
                os.rename(lock, stale)
                os.unlink(stale)
                lfd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except (FileNotFoundError, FileExistsError):
                return 0
        dropped = 0
        try:
            os.close(lfd)
            for p in list(self._pair_files()):
                try:
                    exp = self._read(p)
                except FileNotFoundError:
                    continue
                if exp is not None and now >= exp + grace:
                    try:
                        os.unlink(p)
                        dropped += 1
                    except FileNotFoundError:
                        pass
            cutoff = time.time() - TEMP_STALE_S
            for n in os.listdir(self.dir):
                if n.startswith(".tmp-"):
                    p = os.path.join(self.dir, n)
                    try:
                        if os.stat(p).st_mtime < cutoff:
                            os.unlink(p)
                    except OSError:
                        pass
            if dropped:
                self._fsync_path(self.dir)
        finally:
            try:
                os.unlink(lock)
            except OSError:
                pass
        return dropped

    def audit(self):
        """Pair-named files that are not complete, matching records. They are never pruned."""
        bad = []
        for p in self._pair_files():
            try:
                if self._read(p) is None:
                    bad.append(p)
            except FileNotFoundError:
                pass
        return bad

    def migrate_json(self, json_path, now):
        """Import the pairs of an old PairStore JSON file whose exp is still ahead of `now`. Returns (imported,
        already_present, skipped_expired). Run once, with every old writer stopped, before switching stores."""
        with open(json_path, encoding="utf-8") as fh:
            pairs = json.load(fh).get("pairs", {})
        imported = present = expired = 0
        for k, exp in pairs.items():
            signer, _, nonce = str(k).partition("|")
            if int(exp) <= now:
                expired += 1
            elif self.check_and_record(signer, nonce, int(exp)):
                imported += 1
            else:
                present += 1
        return imported, present, expired
