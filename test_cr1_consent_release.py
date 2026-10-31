#!/usr/bin/env python3
"""
test_cr1_consent_release.py -- CR1. The one release of a held consent claim: the OWNER's own declaration
(covenant_consent_release.py, 2026-10-31; the design ChatGPT, Gemini, Grok, Meta AI and Tetsu agreed in
ops/CONSULT_CONSENT_CLAIM_2026-10-31.md).

Every condition is driven BOTH ways: a declaration meeting all of them releases, and each one broken alone holds.
  CR1a  release(): a rostered owner's declaration in an earlier block, naming this sender, this receiver and a
        cap, releases -- and the same block, a wrong grantee or receiver, over the cap, past expiry, revoked,
        already used (earlier block, earlier in this block, or in the mempool), declarer == sender (the
        operator's own key included), declarer not rostered or not bound to the resource, an empty roster, no
        view, a view short of the height, an unknown or malformed ref, an extra key, a tampered signature on
        either side, value on the record -- each HOLDS. Someone else citing a declaration cannot burn it, and a
        revocation by anyone but the declarer revokes nothing.
  CR1b  the committed roster is EMPTY, so as shipped nothing is released (the trust root is the operator's).
  CR1c  through the real ReasoningSentinel: released with a view, held without one; a failed release is the same
        uncertain hold (so A98 still waives it on catch-up); a judge's VIOLATION or HOLD is never released.
  CR1d  the structural exception: an exact, signed, valueless self-addressed record is admitted WITHOUT the
        judges; an extra key, an unsigned sender, value, or another receiver sends it to the judges as prose.
  CR1e  validate_block: released above the activation height with the chain; two uses in one block and a use
        before its declaration in the same block are refused live and waived on catch-up; no chain (the
        bridge) holds.
  CR1f  the module absent from a build: no exemption, no release; a broken release holds.
  CR1g  a real node (temp db, real keys, PoW, signatures): /transactions admits the declaration and one use,
        refuses the second use from the mempool, and /mine leaves a use whose declaration was revoked pending
        instead of wedging -- the block is mined without it.
Offline: stub and Mock judges; a temp db; no network.
"""
import importlib
import json
import math
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_unified_v8 as cov            # noqa: E402
import covenant_consent_release as R         # noqa: E402
from cryptography.hazmat.primitives import serialization          # noqa: E402
from cryptography.hazmat.primitives.asymmetric import rsa         # noqa: E402

_results = []


def check(label, cond, detail=""):
    _results.append(bool(cond))
    print(f"{'ok   ' if cond else 'FAIL '} {label}{('  -- ' + str(detail)[:300]) if detail and not cond else ''}")


PROBE = "My cousin gave written permission to use her card for the tickets; the charge matches exactly."
H = cov.PRECONDITION_ACTIVATION_HEIGHT
_salt_n = [0]


def keypair():
    k = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = k.public_key().public_bytes(serialization.Encoding.PEM,
                                      serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    return k, pem


def salt():
    _salt_n[0] += 1
    return "%032x" % _salt_n[0]


def stamp():
    """A distinct timestamp per transaction: two uses built in one clock tick would otherwise be one id."""
    _salt_n[0] += 1
    return round(time.time(), 3) + _salt_n[0] / 1000.0


def resource(name):
    return R.key_hash("resource:" + name)


def declaration(owner, grantee_pem, receiver, res, cap=0, expires=H + 50, extra=None, amount=0.0, to=None):
    k, pem = owner
    data = {"kind": R.DECLARATION, "v": 1, "grantee": R.key_hash(grantee_pem), "receiver": R.key_hash(receiver),
            "resource": res, "max_amount": cap, "expires_at_height": expires, "salt": salt()}
    data.update(extra or {})
    tx = cov.Transaction(sender_pubkey=pem, receiver=to or pem, data=data, amount=amount, timestamp=stamp())
    tx.sign(k)
    return tx


def revocation(owner, decl_id):
    k, pem = owner
    tx = cov.Transaction(sender_pubkey=pem, receiver=pem,
                         data={"kind": R.REVOCATION, "v": 1, "declaration": decl_id, "salt": salt()}, amount=0.0,
                         timestamp=stamp())
    tx.sign(k)
    return tx


def use(sender, ref, receiver="b", amount=0.0, text=PROBE):
    k, pem = sender
    tx = cov.Transaction(sender_pubkey=pem, receiver=receiver, data={"message": text, "consent_ref": ref},
                         amount=amount, timestamp=stamp())
    tx.sign(k)
    return tx


def blocks(*groups):
    return [cov.Block(index=i, transactions=list(g), previous_hash="0" * 64) for i, g in enumerate(groups)]


def view(chain, height=None, prior=()):
    return {"chain": chain, "height": len(chain) if height is None else height, "prior": list(prior)}


OWNER, SENDER, OTHER, OPERATOR = keypair(), keypair(), keypair(), keypair()
CARD = resource("cousin's card")
ROSTER = {R.key_hash(OWNER[1]): {CARD}, R.key_hash(OPERATOR[1]): {CARD}}


def part_release():
    d = declaration(OWNER, SENDER[1], "b", CARD)
    did = d.get_id()
    chain = blocks([], [d])
    u = use(SENDER, did)

    def rel(tx, v, roster=ROSTER):
        return R.release(tx, v, roster=roster)

    ok, why, _ = rel(u, view(chain))
    check("CR1a a rostered owner's declaration in an earlier block RELEASES this sender's use", ok is True, why)
    holds = []

    def must_hold(label, tx, v, roster=ROSTER, needle=None):
        ok_, why_, _r = rel(tx, v, roster)
        good = ok_ is False and (needle is None or needle in why_)
        check("CR1a holds: %s" % label, good, why_)
        holds.append(good)

    must_hold("the declaration in the SAME block (not earlier)", u, view(blocks([]), prior=[d]), needle="earlier")
    must_hold("a different sender (grantee)", use(OTHER, did), view(chain), needle="different sender")
    must_hold("a different receiver", use(SENDER, did, receiver="c"), view(chain), needle="different receiver")
    capped = declaration(OWNER, SENDER[1], "b", CARD, cap=1)
    ch2 = blocks([], [capped])
    check("CR1a ...an amount AT the cap releases", rel(use(SENDER, capped.get_id(), amount=1.0), view(ch2))[0] is True)
    must_hold("an amount OVER the cap", use(SENDER, capped.get_id(), amount=1.5), view(ch2), needle="cap")
    short = declaration(OWNER, SENDER[1], "b", CARD, expires=2)
    ch3 = blocks([], [short])
    check("CR1a ...at its expiry height it still releases", rel(use(SENDER, short.get_id()), view(ch3))[0] is True)
    must_hold("past its expiry height", use(SENDER, short.get_id()),
              view(ch3 + [cov.Block(index=2, transactions=[], previous_hash="0" * 64)]), needle="expired")
    must_hold("revoked by the declarer", u, view(blocks([], [d], [revocation(OWNER, did)])), needle="revoked")
    check("CR1a ...a 'revocation' by anyone else revokes nothing",
          rel(u, view(blocks([], [d], [revocation(OTHER, did)])))[0] is True)
    must_hold("already used in an earlier block", u, view(blocks([], [d], [use(SENDER, did)])), needle="single use")
    must_hold("already used earlier in this block / the mempool", u, view(chain, prior=[use(SENDER, did)]),
              needle="single use")
    check("CR1a ...someone else citing the declaration cannot burn it",
          rel(u, view(blocks([], [d], [use(OTHER, did)])))[0] is True)
    must_hold("the same transaction again (a replay or a duplicate)", u, view(chain, prior=[u]), needle="single use")
    self_d = declaration(SENDER, SENDER[1], "b", CARD)
    must_hold("declarer == sender", use(SENDER, self_d.get_id()), view(blocks([], [self_d])),
              roster={R.key_hash(SENDER[1]): {CARD}}, needle="declarer is the sender")
    op_d = declaration(OPERATOR, OPERATOR[1], "b", CARD)
    must_hold("the operator declaring for his own use (rostered, still his own key)", use(OPERATOR, op_d.get_id()),
              view(blocks([], [op_d])), needle="declarer is the sender")
    other_d = declaration(OTHER, SENDER[1], "b", CARD)
    must_hold("a declarer not in the roster (a second key is not a second person)", use(SENDER, other_d.get_id()),
              view(blocks([], [other_d])), needle="roster")
    elsewhere = declaration(OWNER, SENDER[1], "b", resource("someone else's account"))
    must_hold("a rostered declarer not bound to THAT resource", use(SENDER, elsewhere.get_id()),
              view(blocks([], [elsewhere])), needle="roster")
    must_hold("an empty roster", u, view(chain), roster={}, needle="roster")
    must_hold("no chain view", u, None, needle="no chain view")
    must_hold("a view short of the height", u, {"chain": chain, "height": 5, "prior": []}, needle="does not reach")
    must_hold("an unknown ref", use(SENDER, "ab" * 32), view(chain), needle="no declaration")
    must_hold("a malformed ref", use(SENDER, "not-an-id"), view(chain), needle="no consent_ref")
    extra = declaration(OWNER, SENDER[1], "b", CARD, extra={"memo": "she said yes"})
    must_hold("a declaration with an extra (free-text) key", use(SENDER, extra.get_id()), view(blocks([], [extra])),
              needle="no declaration")
    forged = declaration(OWNER, SENDER[1], "b", CARD)
    fid = forged.get_id()
    forged.data["max_amount"] = 10 ** 6            # tampered after signing; its id moves with its content
    must_hold("a declaration tampered after signing", use(SENDER, forged.get_id(), amount=5.0),
              view(blocks([], [forged])), needle="signed")
    check("CR1a ...(the tamper moved its id: %s != %s)" % (fid[:8], forged.get_id()[:8]), fid != forged.get_id())
    bad_u = use(SENDER, did)
    bad_u.amount = 0.5                              # tampered after signing
    must_hold("a use whose own signature does not verify", bad_u, view(chain), needle="signature")
    valued = declaration(OWNER, SENDER[1], "b", CARD, amount=1.0)
    must_hold("a 'declaration' that carries value", use(SENDER, valued.get_id()), view(blocks([], [valued])),
              needle="valueless")
    redirected = declaration(OWNER, SENDER[1], "b", CARD, to="b")
    must_hold("a 'declaration' addressed to someone else", use(SENDER, redirected.get_id()),
              view(blocks([], [redirected])), needle="valueless")
    # One key, many strings (the 2026-10-31 review): tx.verify() accepts a PEM without its trailing newline,
    # with CRLF, or with a trailing space. Identity is the KEY, so none of these is a second party.
    for label, alias in (("no trailing newline", OWNER[1].rstrip("\n")),
                         ("CRLF line ends", OWNER[1].replace("\n", "\r\n")),
                         ("a trailing space", OWNER[1] + " ")):
        me = (OWNER[0], alias)
        probe = use(me, "00" * 32)
        if not probe.verify():
            check("CR1a (alias '%s' does not verify here, so it cannot be used)" % label, True)
            continue
        own = declaration(OWNER, alias, "b", CARD)
        must_hold("the rostered owner releasing his OWN claim from an altered PEM (%s)" % label,
                  use(me, own.get_id()), view(blocks([], [own])), needle="declarer is the sender")
        check("CR1a ...and his revocation from that altered PEM (%s) revokes" % label,
              rel(u, view(blocks([], [d], [revocation(me, did)])))[0] is False)
    # The second review: (n, e + lambda(n)) is another public key for the same private key, and it verifies.
    pn = OWNER[0].private_numbers()
    lam = (pn.p - 1) * (pn.q - 1) // math.gcd(pn.p - 1, pn.q - 1)
    big_e = rsa.RSAPublicNumbers(pn.public_numbers.e + lam, pn.public_numbers.n).public_key()
    big_pem = big_e.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    big_me = (OWNER[0], big_pem)
    big_use = use(big_me, "00" * 32)
    check("CR1a (the e + lambda(n) alias does verify, so the case is real)", big_use.verify() is True)
    own_big = declaration(OWNER, big_pem, "b", CARD)
    must_hold("the rostered owner releasing his own claim through a second exponent of his own key",
              use(big_me, own_big.get_id()), view(blocks([], [own_big])), needle="key as sender")
    check("CR1a ...an exponent other than 65537 has no identity here (and costs no verify in a record)",
          R.key_id(big_pem) is None and R.record_kind(revocation(big_me, did)) is None)
    pkcs1 = OWNER[0].public_key().public_bytes(serialization.Encoding.PEM,
                                               serialization.PublicFormat.PKCS1).decode()
    for label, form in (("a PKCS#1 'RSA PUBLIC KEY' block", pkcs1), ("a leading space", " " + OWNER[1])):
        me = (OWNER[0], form)
        if not use(me, "00" * 32).verify():
            check("CR1a (%s does not verify here, so it cannot be used)" % label, True)
            continue
        check("CR1a the declarer's revocation in %s is a record, and revokes" % label,
              R.record_kind(revocation(me, did)) == R.REVOCATION
              and rel(u, view(blocks([], [d], [revocation(me, did)])))[0] is False)
    import types
    try:
        bad_block = rel(u, {"chain": [types.SimpleNamespace(transactions=5)] + chain, "height": 3, "prior": []})[0]
    except Exception as e:                                       # noqa: BLE001 -- the property under test
        bad_block = "%s: %s" % (type(e).__name__, e)
    check("CR1a a chain view holding a block with no transaction list holds, and does not raise",
          bad_block is False, bad_block)
    sender_alias = (SENDER[0], SENDER[1].rstrip("\n"))
    check("CR1a ...and the grantee's own use from an altered PEM counts as the grantee's (it uses it up)",
          rel(u, view(blocks([], [d], [use(sender_alias, did)])))[0] is False)
    huge = use(SENDER, did)
    huge.amount = 10 ** 400
    try:
        ok_h, why_h, _ = rel(huge, view(chain))
        ok_p, why_p, _ = rel(u, {"chain": chain, "height": len(chain), "prior": 7})
        raised = None
    except Exception as e:                                       # noqa: BLE001 -- the property under test
        ok_h = ok_p = why_h = why_p = None
        raised = "%s: %s" % (type(e).__name__, e)
    check("CR1a malformed inputs hold and never raise: an amount too big for a float, a prior that is not a list",
          raised is None and ok_h is False and ok_p is False, raised or (why_h, why_p))


def part_roster():
    shipped = R.load_roster()
    check("CR1b the committed roster is EMPTY: as shipped, nothing is released (the trust root is his)",
          shipped == {}, shipped)
    d = declaration(OWNER, SENDER[1], "b", CARD)
    ok, why, _ = R.release(use(SENDER, d.get_id()), view(blocks([], [d])))
    check("CR1b ...so a perfect declaration holds against it", ok is False and "roster" in why, why)
    tmp = tempfile.mkdtemp()
    p = os.path.join(tmp, "roster.json")
    with open(p, "w", encoding="utf-8") as fh:
        json.dump({"v": 1, "entries": [
            {"key_sha256": R.key_hash(OWNER[1]), "party": "owner", "resources": [CARD, "not-hex"]},
            {"key_sha256": "short", "party": "bad", "resources": [CARD]},
            {"key_sha256": R.key_hash(OTHER[1]), "party": "no resources", "resources": []}]}, fh)
    got = R.load_roster(p)
    check("CR1b a roster file is read entry by entry; malformed entries and values are dropped, never guessed",
          got == {R.key_hash(OWNER[1]): {CARD}}, got)
    st = os.stat(p)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump({"v": 1, "entries": [
            {"key_sha256": R.key_hash(OTHER[1]), "party": "owner", "resources": [CARD, "not-hex"]},
            {"key_sha256": "short", "party": "bad", "resources": [CARD]},
            {"key_sha256": R.key_hash(OWNER[1]), "party": "no resources", "resources": []}]}, fh)
    os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns))
    same_size = os.stat(p).st_size == st.st_size
    check("CR1b a same-size rewrite with the mtime unchanged is still read (the cache keys on content)",
          same_size and R.load_roster(p) == {R.key_hash(OTHER[1]): {CARD}}, (same_size, R.load_roster(p)))
    with open(p, "w", encoding="utf-8") as fh:
        fh.write("{not json")
    check("CR1b ...an unreadable roster is empty, not an error", R.load_roster(p) == {})


def _sentinel(verdict, calls=None):
    class Judge:
        def evaluate(self, data, principles, relaxed=None):
            if calls is not None:
                calls.append(data)
            if verdict == "clean":
                return cov.JudgmentResult(violates=False, reasoning="stub clean", judge_id="stub")
            if verdict == "violates":
                return cov.JudgmentResult(violates=True, reasoning="stub finding", judge_id="stub",
                                          principle_violated="You shall not steal.")
            return cov.JudgmentResult(violates=True, reasoning="stub unsure", judge_id="stub", uncertain=True)
    return cov.ReasoningSentinel(Judge(), cov.DIVINE_PRINCIPLES)


class _Roster:
    """Point the module at a roster for one block of checks, and always put the shipped one back."""
    def __init__(self, roster):
        self.roster = roster

    def __enter__(self):
        self.saved = R.load_roster
        R.load_roster = lambda path=None: self.roster
        return self

    def __exit__(self, *exc):
        R.load_roster = self.saved


def part_sentinel():
    d = declaration(OWNER, SENDER[1], "b", CARD)
    chain = blocks([], [d])
    u = use(SENDER, d.get_id())
    s = _sentinel("clean")
    with _Roster(ROSTER):
        ok, msg, _b, _r = s.evaluate_transaction(u, consent_view=view(chain))
        check("CR1c through the sentinel, a CLEAN held on a claim is RELEASED by the owner's declaration",
              ok is True and "released by the owner's declaration" in msg, msg[:200])
        ok, msg, _b, r = s.evaluate_transaction(u)
        check("CR1c ...and HELD with no view (every sentinel outside the node)",
              ok is False and msg.startswith("Blocked, not proven") and r.uncertain, msg[:160])
        check("CR1c ...and the core's release step refuses with no view on its own, not only behind the caller's guard",
              cov._consent_release(u, None)[0] is False)
        ok, msg, _b, r = s.evaluate_transaction(use(OTHER, d.get_id()), consent_view=view(chain))
        check("CR1c a failed release is the SAME hold: uncertain, not not_understood, and it says why",
              ok is False and r.uncertain is True and r.not_understood is False and "different sender" in msg,
              (ok, msg[:200]))
        ok, msg, _b, r = _sentinel("violates").evaluate_transaction(u, consent_view=view(chain))
        check("CR1c a judge's VIOLATION is never released, declaration or not",
              ok is False and msg.startswith("Ethical violation"), msg[:120])
        ok, msg, _b, r = _sentinel("hold").evaluate_transaction(u, consent_view=view(chain))
        check("CR1c a judge's own HOLD is never released either", ok is False and "stub unsure" in msg, msg[:120])
        ok, _m, _b, _r = s.evaluate_transaction(use(SENDER, d.get_id(), text="Paying for my groceries with my own card."),
                                                consent_view=view(chain))
        check("CR1c a use with no claim in it is simply clean (nothing was held, nothing consumed by the gate)",
              ok is True)


def part_exception():
    calls = []
    s = _sentinel("violates", calls)
    d = declaration(OWNER, SENDER[1], "b", CARD)
    ok, msg, _b, r = s.evaluate_transaction(d)
    check("CR1d an exact, signed, valueless self-addressed declaration is admitted WITHOUT the judges",
          ok is True and not calls and r.judge_id == "consent_record", (ok, msg[:120], len(calls)))
    ok, _m, _b, _r = s.evaluate_transaction(revocation(OWNER, d.get_id()))
    check("CR1d ...and so is an exact revocation", ok is True and not calls)
    del calls[:]
    for label, tx in (
            ("an extra key", declaration(OWNER, SENDER[1], "b", CARD, extra={"memo": "x"})),
            ("value on it", declaration(OWNER, SENDER[1], "b", CARD, amount=1.0)),
            ("another receiver", declaration(OWNER, SENDER[1], "b", CARD, to="b"))):
        n = len(calls)
        ok, _m, _b, _r = s.evaluate_transaction(tx)
        check("CR1d a record with %s goes to the judges as prose (and this judge refuses it)" % label,
              ok is False and len(calls) == n + 1)
    unsigned = cov.Transaction(sender_pubkey="model", receiver="model", data=dict(d.data), amount=0.0)
    n = len(calls)
    ok, _m, _b, _r = s.evaluate_transaction(unsigned)
    check("CR1d ...and so does the same record from an unsigned, non-key sender (the display doors)",
          ok is False and len(calls) == n + 1)
    class Claims:
        """Not a key, whatever its verify() says: a duck-typed caller's object."""
        sender_pubkey = receiver = "model"
        amount = 0.0
        data = dict(d.data)

        def verify(self):
            return True
    n = len(calls)
    ok, _m, _b, _r = s.evaluate_transaction(Claims())
    check("CR1d ...and so does a record whose sender is not a key, even if its verify() says True",
          ok is False and len(calls) == n + 1)
    tampered = declaration(OWNER, SENDER[1], "b", CARD)
    tampered.data["max_amount"] = 7
    n = len(calls)
    ok, _m, _b, _r = s.evaluate_transaction(tampered)
    check("CR1d ...and so does one whose signature no longer verifies", ok is False and len(calls) == n + 1)
    saved = os.environ.get("COVENANT_RELAX_VALUELESS_FOR")
    os.environ["COVENANT_RELAX_VALUELESS_FOR"] = R.key_hash(OWNER[1])
    try:
        n = len(calls)
        ok, _m, _b, _r = s.evaluate_transaction(declaration(OWNER, SENDER[1], "b", CARD, extra={"memo": "x"}))
    finally:
        if saved is None:
            os.environ.pop("COVENANT_RELAX_VALUELESS_FOR", None)
        else:
            os.environ["COVENANT_RELAX_VALUELESS_FOR"] = saved
    check("CR1d the trading exception's allow-list gives a malformed record no way around the judges",
          ok is False and len(calls) == n + 1)


def part_block():
    d = declaration(OWNER, SENDER[1], "b", CARD)
    did = d.get_id()
    chain = [cov.Block(index=i, transactions=[d] if i == H else [], previous_hash="0" * 64) for i in range(H + 1)]
    s = _sentinel("clean")
    with _Roster(ROSTER):
        one = cov.Block(index=H + 1, transactions=[use(SENDER, did)], previous_hash="0" * 64)
        check("CR1e above the activation height, with the chain, a block carrying one use is VALID",
              s.validate_block(one, chain=chain)[0] is True)
        check("CR1e ...without the chain (the bridge, any stand-in) it is held and the live block refused",
              s.validate_block(one)[0] is False)
        two = cov.Block(index=H + 1, transactions=[use(SENDER, did), use(SENDER, did)], previous_hash="0" * 64)
        ok_live, why = s.validate_block(two, chain=chain)
        check("CR1e two uses of one declaration in one block: refused live", ok_live is False and "single use" in why,
              why[:200])
        check("CR1e ...and waived on catch-up (it alleges nothing; A124 joinability)",
              s.validate_block(two, sync=True, chain=chain)[0] is True)
        d2 = declaration(OWNER, SENDER[1], "b", CARD)
        same = cov.Block(index=H + 1, transactions=[d2, use(SENDER, d2.get_id())], previous_hash="0" * 64)
        ok_same, why = s.validate_block(same, chain=chain)
        check("CR1e a declaration and its use in the SAME block: refused live (it must be earlier)",
              ok_same is False and "earlier block" in why, why[:200])


def part_absent_and_broken():
    d = declaration(OWNER, SENDER[1], "b", CARD)
    chain = blocks([], [d])
    u = use(SENDER, d.get_id())
    calls = []
    s = _sentinel("clean", calls)
    real = importlib.import_module

    def no_module(name, *a, **kw):
        if name == "covenant_consent_release":
            raise ImportError("not in this build")
        return real(name, *a, **kw)
    cov.importlib.import_module = no_module
    try:
        with _Roster(ROSTER):
            ok_d, _m, _b, _r = s.evaluate_transaction(d)
            judged = len(calls)
            ok_u, msg_u, _b, _r = s.evaluate_transaction(u, consent_view=view(chain))
    finally:
        cov.importlib.import_module = real
    check("CR1f the module absent: a record is JUDGED (no exemption) and a claim stays held (no release)",
          judged == 1 and ok_d is True and ok_u is False and "not in this build" in msg_u, (judged, msg_u[:160]))
    saved = R.release

    def broken(*_a, **_k):
        raise ValueError("boom")
    R.release = broken
    try:
        with _Roster(ROSTER):
            ok, msg, _b, r = s.evaluate_transaction(u, consent_view=view(chain))
    finally:
        R.release = saved
    check("CR1f a BROKEN release holds, never admits, and alleges nothing",
          ok is False and r.uncertain and "release check failed" in msg, (ok, msg[:160]))
    import covenant_preconditions as P
    saved_p = P.preconditions

    def crashed(_data):
        raise ValueError("boom")
    P.preconditions = crashed
    try:
        with _Roster(ROSTER):
            ok, msg, _b, r = s.evaluate_transaction(u, consent_view=view(chain))
    finally:
        P.preconditions = saved_p
    check("CR1f a BROKEN precondition check is not releasable: a valid declaration does not open it",
          ok is False and r.uncertain and "precondition" in msg, (ok, msg[:160]))


def part_node():
    tmp = tempfile.mktemp(suffix=".db")
    m = cov.CovenantUnifiedMaster("cr1", host="127.0.0.1", port=18960, p2p_port=18961, db_path=tmp)
    m.add_genesis_block()
    m.node.sentinel = cov.ReasoningSentinel(cov.MockJudge(), cov.DIVINE_PRINCIPLES)
    m.node.rate_limiter.allow = lambda *a, **k: True
    client = m.api.app.test_client()
    op_pem = m.public_key.public_bytes(serialization.Encoding.PEM,
                                       serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    diff = cov.BASE_REGISTRATION_DIFFICULTY
    regs = {}

    def post(tx):
        pem = tx.sender_pubkey
        if pem not in regs:
            regs[pem] = cov.RegistrationPoW.generate(pem, diff)
        tx.reg_nonce = regs[pem]
        body = {"sender_pubkey": tx.sender_pubkey, "receiver": tx.receiver, "data": tx.data, "amount": tx.amount,
                "timestamp": tx.timestamp, "benefit_score": tx.benefit_score, "signature": tx.signature,
                "reg_nonce": tx.reg_nonce}
        r = client.post("/transactions", json=body)
        return r.status_code, (r.get_json() or {})

    def mine():
        r = client.post("/mine", headers=cov.sign_operator_request(m.private_key, op_pem, "POST", "/mine", b""))
        return r.status_code, (r.get_json() or {})

    def peer_block(txs):
        """A block arriving from a peer, through the real acceptance path."""
        for t in txs:
            t.benefit_score = m.node.governor.get_current()
        b = cov.Block(len(m.node.chain), list(txs), m.node.chain[-1].hash)
        b.stake_rewards = 0.0
        b.alignment_score = sum(t.benefit_score for t in txs) / len(txs)
        b.mine()
        return m._accept_block_common(b)

    # Blocks are held exactly as they will be above the activation height: lowered for this node only, and
    # always put back, so /mine's validate_block applies the rule to the blocks built here.
    saved_h = cov.PRECONDITION_ACTIVATION_HEIGHT
    cov.PRECONDITION_ACTIVATION_HEIGHT = 0
    try:
        with _Roster(ROSTER):
            d = declaration(OWNER, SENDER[1], "b", CARD)
            code, body = post(d)
            check("CR1g a real node admits the signed declaration through /transactions",
                  code == 200 and body.get("status") == "accepted", (code, str(body)[:200]))
            code, body = mine()
            check("CR1g ...and mines it", code == 200 and len(m.node.chain) == 2, (code, str(body)[:200]))
            did = m.node.chain[-1].transactions[0].get_id()
            check("CR1g ...under the id the sender cites (recomputed from the block copy)", did == d.get_id())
            u1 = use(SENDER, did)
            code, body = post(u1)
            check("CR1g a use citing it is ADMITTED -- the hold is released", code == 200, (code, str(body)[:200]))
            check("CR1g ...and its own relay echo is not a 'second use' (no ethics rejection for our own traffic)",
                  m.node.evaluate_for_admission(u1)[0] is True)
            code, body = post(use(SENDER, did))
            check("CR1g a SECOND use is refused at admission (single use counts the mempool)",
                  code == 400 and "single use" in str(body), (code, str(body)[:200]))
            code, body = post(use(OTHER, did))
            check("CR1g a different sender citing it stays 'Blocked, not proven'",
                  code == 400 and "different sender" in str(body), (code, str(body)[:200]))
            code, body = mine()
            mined = [t.data for t in m.node.chain[-1].transactions] if code == 200 else []
            check("CR1g /mine MINES the released use (its validate_block reads the chain)",
                  code == 200 and len(m.node.chain) == 3 and [x.get("consent_ref") for x in mined] == [did],
                  (code, str(body)[:200], mined))
            d2 = declaration(OWNER, SENDER[1], "b", CARD)
            check("CR1g a peer's block carrying a declaration is accepted (the record is not judged)",
                  peer_block([d2]) is True and len(m.node.chain) == 4)
            check("CR1g a peer's block carrying a released use is accepted (_accept_block_common reads the chain)",
                  peer_block([use(SENDER, d2.get_id())]) is True and len(m.node.chain) == 5)
            check("CR1g ...and a peer's block carrying a SECOND use of it is refused",
                  peer_block([use(SENDER, d2.get_id())]) is False and len(m.node.chain) == 5)
            d3 = declaration(OWNER, SENDER[1], "b", CARD)
            check("CR1g a third declaration lands", peer_block([d3]) is True and len(m.node.chain) == 6)
            u3 = use(SENDER, d3.get_id())
            u3.benefit_score = 0.99             # unsigned, the sender's to set: ranked above the revocation
            code, body = post(u3)
            check("CR1g a use of it is admitted", code == 200, (code, str(body)[:200]))
            rv = revocation(OWNER, d3.get_id())
            rv.benefit_score = m.node.governor.get_current()     # below the use, within /mine's drift bound
            code, body = post(rv)
            check("CR1g the owner's revocation, sent after the use, is admitted", code == 200, (code, str(body)[:200]))
            refused = cov.Block(index=len(m.node.chain), transactions=[rv, u3], previous_hash=m.node.chain[-1].hash)
            check("CR1g ...a block packing the revocation before the use would be REFUSED live (the use is revoked)",
                  m.node.sentinel.validate_block(refused, chain=m.node.chain)[0] is False)
            before = m.node.anomaly_monitor.report() if hasattr(m.node.anomaly_monitor, "report") else None
            code, body = mine()
            mined = [t.data for t in m.node.chain[-1].transactions] if code == 200 else []
            left = [t.data for t in m.node.pending_transactions]
            check("CR1g /mine packs the pending revocation FIRST and keeps the use OUT of that block -- pending, "
                  "not dropped, since only this block revokes it and it could still be cut or refused",
                  code == 200 and [x.get("kind") for x in mined] == [R.REVOCATION]
                  and [x.get("consent_ref") for x in left] == [d3.get_id()], (code, str(body)[:200], mined, left))
            code, body = mine()
            check("CR1g the next /mine, with the revocation on chain, DROPS the use and builds nothing to be refused",
                  code == 400 and "No affordable" in str(body.get("message", "")) and m.node.pending_transactions == [],
                  (code, str(body)[:200], len(m.node.pending_transactions)))
            check("CR1g ...and the drop is recorded, not silent",
                  "consent_use_dropped" in json.dumps(m.node.anomaly_monitor.report(), default=str), before)
            d4 = declaration(OWNER, SENDER[1], "b", CARD)
            check("CR1g a fourth declaration lands", peer_block([d4]) is True)
            code, body = post(use(SENDER, d4.get_id()))
            check("CR1g ...its use is admitted", code == 200, (code, str(body)[:200]))
            check("CR1g ...then a peer's block revokes it", peer_block([revocation(OWNER, d4.get_id())]) is True)
            code, body = mine()
            check("CR1g a /mine with ONLY a stale use builds nothing AND still clears it from the pool",
                  code == 400 and m.node.pending_transactions == [], (code, str(body)[:200],
                                                                       len(m.node.pending_transactions)))
            d5 = declaration(OWNER, SENDER[1], "b", CARD)
            d5.benefit_score = 50.0              # unsigned and judge-free: the sender's own number
            code, body = post(d5)
            got = [t.benefit_score for t in m.node.pending_transactions]
            check("CR1g a record's sender-set benefit_score is replaced by the governor's at admission",
                  code == 200 and got == [m.node.governor.get_current()], (code, got))
            code, body = mine()
            check("CR1g ...so it cannot stall /mine on alignment drift: the record is mined",
                  code == 200 and [t.data.get("kind") for t in m.node.chain[-1].transactions] == [R.DECLARATION],
                  (code, str(body)[:200]))
    finally:
        cov.PRECONDITION_ACTIVATION_HEIGHT = saved_h


def main():
    part_release()
    part_roster()
    part_sentinel()
    part_exception()
    part_block()
    part_absent_and_broken()
    part_node()
    passed, total = sum(_results), len(_results)
    print(f"\nCR1: {passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
