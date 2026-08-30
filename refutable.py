#!/usr/bin/env python3
"""
refutable.py -- a record in which a claim cannot be read without its refutations.

WHY THIS EXISTS

  Records decay in one direction. They keep conclusions and shed the challenges
  to them. Every retelling smooths, every summary firms up, and over months a
  body of work drifts toward confidence it has not earned, with nobody deciding
  that it should.

  This is measurable in AI memory systems, where it is unusually stark: stored
  memory retains what the user asserted and discards what the model corrected.
  Ask such a system to name an error it made and it cannot, not from modesty,
  but because nothing wrote the correction down. Every session then restarts
  from an unchallenged version of the user's own views, and the resulting
  agreement looks like corroboration.

  The fix is not care. Care does not survive months. It has to be a property of
  the store: refutations are first-class, they attach to the CLAIM rather than
  to the conversation that produced them, and reading is defined so that you
  cannot get a claim without them.

WHAT IS DIFFERENT HERE

  Most stores let you record a correction. Almost none make the correction
  inseparable from what it corrects. That separability is the whole failure:
  the claim gets quoted onward, the challenge stays behind.

  So `get` returns a Claim whose refutations travel with it, `text()` renders
  them inline, and a claim with a standing refutation reports itself as
  CONTESTED wherever it appears. There is deliberately no way to ask for the
  bare assertion.

NO DEPENDENCIES. Python 3.8+, standard library only. One file. Take it.

  from refutable import Store
  s = Store("./record")
  s.assert_("jspace", "We anticipated this result", provenance="asserted")
  s.refute("jspace", "No dated artefact precedes publication", by="check:git")
  print(s.get("jspace").text())        # claim AND the refutation, always

  s.state_root()   # one hash; publish it, keep the contents private
  s.verify()       # has anything drifted

CLI
  python refutable.py demo        # a worked example, end to end
  python refutable.py selftest    # assertions that must hold

LICENCE: public domain. Attribution is unnecessary. Adoption is the point.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

__all__ = ["Store", "Claim", "Refutation", "TRACED", "ASSERTED"]

# Provenance. The only distinction that reliably predicts whether a claim
# survives checking: did it come from something outside the conversation that
# produced it, or was it generated inside it?
TRACED = "traced"      # anchored to something that could have come back different
ASSERTED = "asserted"  # stated, not anchored. Not lesser. Just unbacked.

_LEAF, _NODE = b"\x00", b"\x01"


def _sha(*parts: bytes) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p)
    return h.hexdigest()


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


@dataclass
class Refutation:
    """A challenge attached to a claim. It outlives the exchange that made it."""
    challenge: str
    by: str = ""                  # who or what: "check:git", "human", a model
    at: str = field(default_factory=_now)
    outcome: str = "standing"     # standing | withdrawn | upheld

    def digest(self) -> str:
        return _sha(self.challenge.encode(), self.by.encode(),
                    self.outcome.encode())


@dataclass
class Claim:
    name: str
    claim: str
    provenance: str = ASSERTED
    at: str = field(default_factory=_now)
    refutations: List[Refutation] = field(default_factory=list)
    prior: Optional[str] = None   # digest of the version this replaced

    @property
    def standing(self) -> List[Refutation]:
        return [r for r in self.refutations if r.outcome == "standing"]

    @property
    def contested(self) -> bool:
        return bool(self.standing)

    def digest(self) -> str:
        """Identity of the assertion itself. Refutations are excluded so that
        challenging a claim does not make it look like a different claim."""
        return _sha(self.name.encode(), self.claim.encode(),
                    self.provenance.encode())

    def text(self) -> str:
        """The ONLY rendering. There is no way to get the bare assertion,
        because a bare assertion is what the failure mode travels as."""
        head = f"[{self.provenance.upper()}]"
        if self.contested:
            head = f"[CONTESTED | {self.provenance.upper()}]"
        out = [f"{head} {self.name}: {self.claim}"]
        for r in self.refutations:
            mark = {"standing": "!", "withdrawn": "~", "upheld": "x"}.get(r.outcome, "?")
            src = f" ({r.by})" if r.by else ""
            out.append(f"    {mark} {r.challenge}{src}")
        if not self.refutations:
            out.append("    - no challenge recorded; absence of one is not support")
        return "\n".join(out)


class Store:
    """Append-only. Overwrites archive rather than replace. Refutations persist
    across revisions of the claim they attach to, because a revision that drops
    its own challenge is exactly the decay this guards against."""

    def __init__(self, root: str):
        self.root = os.path.abspath(root)
        os.makedirs(os.path.join(self.root, "archive"), exist_ok=True)
        self._log = os.path.join(self.root, "log.jsonl")

    # ---------- paths ----------
    def _path(self, name: str) -> str:
        safe = "".join(c for c in name if c.isalnum() or c in "-_.")
        if not safe or safe != name:
            raise ValueError(f"name must be [A-Za-z0-9-_.]: {name!r}")
        return os.path.join(self.root, f"{safe}.json")

    def _append_log(self, op: str, name: str, digest: str) -> None:
        prev = ""
        if os.path.exists(self._log):
            with open(self._log, "rb") as f:
                lines = f.read().strip().splitlines()
                if lines:
                    prev = json.loads(lines[-1].decode())["entry"]
        entry = _sha(prev.encode(), op.encode(), name.encode(), digest.encode())
        with open(self._log, "a", encoding="utf-8") as f:
            f.write(json.dumps({"op": op, "name": name, "digest": digest,
                                "at": _now(), "prev": prev,
                                "entry": entry}) + "\n")

    # ---------- write ----------
    def assert_(self, name: str, claim: str, provenance: str = ASSERTED) -> Claim:
        """Record a claim. If it replaces one, the prior version is archived and
        any refutations it carried are inherited: a new phrasing does not
        discharge an old objection."""
        if provenance not in (TRACED, ASSERTED):
            raise ValueError("provenance must be TRACED or ASSERTED")
        existing = self.get(name)
        refs, prior = [], None
        if existing:
            if existing.claim == claim and existing.provenance == provenance:
                return existing
            self._archive(existing)
            refs = list(existing.refutations)      # objections survive rewording
            prior = existing.digest()
        c = Claim(name=name, claim=claim, provenance=provenance,
                  refutations=refs, prior=prior)
        self._write(c)
        self._append_log("assert", name, c.digest())
        return c

    def refute(self, name: str, challenge: str, by: str = "",
               outcome: str = "standing") -> Claim:
        """Attach a challenge to a claim. This is the operation vendor memory
        does not have, and its absence is the whole mechanism."""
        c = self.get(name)
        if c is None:
            raise KeyError(f"no claim named {name!r}; refute what exists")
        c.refutations.append(Refutation(challenge=challenge, by=by,
                                        outcome=outcome))
        self._write(c)
        self._append_log("refute", name, c.refutations[-1].digest())
        return c

    def resolve(self, name: str, index: int, outcome: str) -> Claim:
        """Mark a refutation withdrawn (it was wrong) or upheld (it stands and
        the claim should not be relied on). Nothing is ever deleted."""
        if outcome not in ("standing", "withdrawn", "upheld"):
            raise ValueError("outcome must be standing, withdrawn or upheld")
        c = self.get(name)
        if c is None or not (0 <= index < len(c.refutations)):
            raise KeyError("no such refutation")
        c.refutations[index].outcome = outcome
        self._write(c)
        self._append_log(f"resolve:{outcome}", name, c.refutations[index].digest())
        return c

    def _write(self, c: Claim) -> None:
        with open(self._path(c.name), "w", encoding="utf-8") as f:
            json.dump(asdict(c), f, indent=2)

    def _archive(self, c: Claim) -> None:
        stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        p = os.path.join(self.root, "archive", f"{c.name}.{stamp}.json")
        n = 1
        while os.path.exists(p):     # never clobber an archived version
            p = os.path.join(self.root, "archive", f"{c.name}.{stamp}.{n}.json")
            n += 1
        with open(p, "w", encoding="utf-8") as f:
            json.dump(asdict(c), f, indent=2)

    # ---------- read ----------
    def get(self, name: str) -> Optional[Claim]:
        p = self._path(name)
        if not os.path.exists(p):
            return None
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        d["refutations"] = [Refutation(**r) for r in d.get("refutations", [])]
        return Claim(**d)

    def names(self) -> List[str]:
        return sorted(f[:-5] for f in os.listdir(self.root)
                      if f.endswith(".json"))

    def contested(self) -> List[Claim]:
        """Everything currently under standing challenge. Read this first."""
        return [c for c in (self.get(n) for n in self.names())
                if c and c.contested]

    # ---------- integrity ----------
    def state_root(self) -> Dict[str, object]:
        """A domain-separated Merkle root over (name, claim digest). One hash.
        It reveals no content and cannot be reversed into any. Publish it and
        keep the record private: custody and verification come apart, which is
        what lets someone hold a record they are not trusted to read."""
        leaves = sorted(_sha(_LEAF, n.encode(), (self.get(n).digest()).encode())
                        for n in self.names())
        if not leaves:
            return {"root": _sha(_LEAF), "claims": 0}
        level = leaves
        while len(level) > 1:
            nxt = []
            for i in range(0, len(level) - 1, 2):
                nxt.append(_sha(_NODE, level[i].encode(), level[i + 1].encode()))
            if len(level) % 2:
                nxt.append(level[-1])      # carry, never duplicate (CVE-2012-2459)
            level = nxt
        return {"root": level[0], "claims": len(leaves)}

    def verify(self) -> Dict[str, object]:
        """Walk the log. A break means something was edited outside this API."""
        if not os.path.exists(self._log):
            return {"ok": True, "entries": 0, "broken_at": None}
        prev, n = "", 0
        with open(self._log, encoding="utf-8") as f:
            for i, line in enumerate(f):
                e = json.loads(line)
                want = _sha(prev.encode(), e["op"].encode(),
                            e["name"].encode(), e["digest"].encode())
                if e["entry"] != want or e["prev"] != prev:
                    return {"ok": False, "entries": n, "broken_at": i}
                prev, n = e["entry"], n + 1
        return {"ok": True, "entries": n, "broken_at": None}


# --------------------------------------------------------------------------
def _demo() -> int:
    import shutil, tempfile
    d = tempfile.mkdtemp()
    try:
        s = Store(os.path.join(d, "record"))

        s.assert_("anticipated", "We anticipated the published result",
                  provenance=ASSERTED)
        s.assert_("mycelium", "The framing predates the referral",
                  provenance=TRACED)

        print("Two claims recorded, one traced, one merely asserted.\n")
        print(s.get("anticipated").text(), "\n")

        s.refute("anticipated", "No dated artefact precedes publication",
                 by="check:git+filesystem")
        s.refute("anticipated",
                 "Category error: an internal phenomenon and an external "
                 "runtime are not the same kind of object", by="two models, unaided")

        print("Now challenged. Note it cannot be read without them:\n")
        print(s.get("anticipated").text(), "\n")

        s.assert_("anticipated", "We arrived at a related idea independently",
                  provenance=ASSERTED)
        print("Rewritten more modestly. The objections came with it:\n")
        print(s.get("anticipated").text(), "\n")

        print("Read-this-first list:",
              [c.name for c in s.contested()])
        print("state root:", s.state_root())
        print("integrity :", s.verify())
        return 0
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _selftest() -> int:
    import shutil, tempfile
    d = tempfile.mkdtemp()
    try:
        s = Store(os.path.join(d, "r"))

        s.assert_("a", "claim one", TRACED)
        assert s.get("a").provenance == TRACED
        assert not s.get("a").contested

        s.refute("a", "does not follow", by="human")
        assert s.get("a").contested, "a refuted claim must report as contested"
        assert "does not follow" in s.get("a").text(), \
            "refutation must appear in the only rendering there is"

        # The property that matters: rewording does not discharge an objection.
        s.assert_("a", "claim one, restated", TRACED)
        assert s.get("a").contested, "revision must inherit standing refutations"
        assert len(s.get("a").refutations) == 1

        # Archive kept the superseded version.
        arch = os.listdir(os.path.join(s.root, "archive"))
        assert any(f.startswith("a.") for f in arch), "prior version must survive"

        # Withdrawal is explicit and non-destructive.
        s.resolve("a", 0, "withdrawn")
        assert not s.get("a").contested
        assert len(s.get("a").refutations) == 1, "nothing is ever deleted"

        # Refuting something absent is refused rather than invented.
        try:
            s.refute("ghost", "x")
            raise AssertionError("must not accept a refutation of nothing")
        except KeyError:
            pass

        # Root changes with content, is stable without it.
        r1 = s.state_root()["root"]
        assert s.state_root()["root"] == r1, "root must be deterministic"
        s.assert_("b", "another", ASSERTED)
        assert s.state_root()["root"] != r1, "root must move when the set moves"

        assert s.verify()["ok"], "log must verify"

        # Tamper with the log and the walk must notice.
        with open(s._log, "a", encoding="utf-8") as f:
            f.write(json.dumps({"op": "assert", "name": "c", "digest": "0",
                                "at": _now(), "prev": "wrong",
                                "entry": "wrong"}) + "\n")
        assert not s.verify()["ok"], "an edited log must fail verification"

        print("selftest: all assertions held")
        return 0
    finally:
        shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "demo"
    raise SystemExit(_selftest() if cmd == "selftest" else _demo())
