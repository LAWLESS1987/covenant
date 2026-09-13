#!/usr/bin/env python3
"""test_sm1_sealed_mail.py -- SM1: the plan and the decision, sealed for the mail.

Offline, in a temp directory: keys are generated here, the plan is a stub,
nothing is placed anywhere. Every check RUNS the function it guards. The false
pushes toward MORE capability that must be refused: a block for another key,
a changed byte, a swapped sender key, a changed header, a sender the registry
does not know, a decision for another day, a replayed block, a decision for a
plan whose hash moved. And what must work: the same block after a mail client
quoted and re-wrapped it, the plaintext in the ledger, the approval recorded
through the daily plan's own path so the gate reads it.

Run: python test_sm1_sealed_mail.py        -> "SM1: n/n passed"
"""
import base64
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import covenant_daily_plan as DP                            # noqa: E402
import covenant_sealed_mail as SM                           # noqa: E402

results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print("%s  %s%s" % ("ok  " if ok else "FAIL", label, "" if ok else "  " + str(detail)[:220]), flush=True)


def stub_gather(say=print):
    return {"posture": "STUB POSTURE", "rule5": {"clears": False, "why": "0 settled signals, need 30"},
            "armed": False, "halt": False, "caps": {"max_order_usd": 100.0}, "orders_placed_today": 0,
            "proposed_orders": [], "planner": "stub"}


def rekey():
    from cryptography.hazmat.primitives.asymmetric import rsa
    k = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return k, SM.pubkey_pem(k)


def refuses(fn, needle):
    try:
        fn()
        return False, "opened"
    except SM.SealedError as e:
        return needle in str(e), str(e)


def rearmor(env):
    return SM.armor(env)


def main():
    td = tempfile.mkdtemp(prefix="sm1_")
    plan_dir = os.path.join(td, "plan"); approvals = os.path.join(td, "approvals.jsonl")
    signers = os.path.join(td, "signers.json"); seen = os.path.join(td, "seen.json")
    log = os.path.join(td, "sealed.log"); outbox = os.path.join(td, "outbox")
    pc_key_path = os.path.join(td, "pc.key")
    now = 1_800_000_000.0
    day = DP.today(now)
    DP.write(day, say=lambda *_: None, plan_dir=plan_dir, gatherer=stub_gather)
    plan = DP.load(day, plan_dir)
    pc, pc_pem = SM.my_key(pc_key_path)
    phone, phone_pem = rekey()
    stranger, stranger_pem = rekey()
    DP.register_signer("phone", phone_pem, signers)

    # ---- the primitives
    blk = SM.seal("plan", {"kind": "plan", "plan": {"date": day}}, pc, pc_pem, phone_pem)
    env, obj, spk = SM.open_block(blk, phone, phone_pem, expect_sender_pem=pc_pem)
    check("SM1.1 a plan sealed to the phone opens with the phone's key, from the PC's", obj["plan"]["date"] == day and spk == pc_pem and env["from"] == SM.fingerprint(pc_pem))
    quoted = "On Sun, someone wrote:\n> Here is the plan\n> " + blk.replace("\n", "\n> ") + "\n> \nSent from my phone"
    rewrapped = quoted.replace("\n> ", "\n> ").replace(SM.BEGIN, SM.BEGIN + "\n").replace("=\n", "=\n\n")
    _e, obj2, _s = SM.open_block(rewrapped, phone, phone_pem)
    check("SM1.2 the same block opens after a mail client quoted and re-wrapped it", obj2 == obj)
    ok, why = refuses(lambda: SM.open_block(blk, pc, pc_pem), "not addressed to this key")
    check("SM1.3 REFUSED: the PC cannot open what it sealed to the phone", ok, why)
    ok, why = refuses(lambda: SM.open_block(blk, stranger, stranger_pem), "not addressed")
    check("SM1.3b REFUSED: a stranger's key cannot open it", ok, why)
    e0 = SM.blocks(blk)[0]
    ct = bytearray(base64.b64decode(e0["ct"])); ct[5] ^= 0x01
    ok, why = refuses(lambda: SM.open_block(rearmor(dict(e0, ct=base64.b64encode(bytes(ct)).decode())), phone, phone_pem), "signature does not verify")
    check("SM1.4 REFUSED: one changed byte of ciphertext breaks the signature first", ok, why)
    ok, why = refuses(lambda: SM.open_block(rearmor(dict(e0, kind="decision")), phone, phone_pem), "signature does not verify")
    check("SM1.5 REFUSED: a changed header (kind) breaks the signature", ok, why)
    ok, why = refuses(lambda: SM.open_block(rearmor(dict(e0, spk=stranger_pem)), phone, phone_pem), "does not match the 'from'")
    check("SM1.6 REFUSED: a swapped sender key does not match the fingerprint", ok, why)
    forged = SM.blocks(SM.seal("plan", {"kind": "plan", "plan": {"date": day, "forged": True}}, stranger, stranger_pem, phone_pem))[0]
    ok, why = refuses(lambda: SM.open_block(rearmor(forged), phone, phone_pem, expect_sender_pem=pc_pem), "not the key already trusted")
    check("SM1.7 REFUSED: a plan sealed by a stranger's key is not the pinned PC key", ok, why)
    ok, why = refuses(lambda: SM.open_block("nothing here", phone, phone_pem), "no sealed block")
    check("SM1.8 REFUSED: prose with no block", ok, why)
    p = SM.peek(blk)
    check("SM1.9 peek needs no key and says kind, to, from", p and p[0]["kind"] == "plan" and p[0]["to"] == SM.fingerprint(phone_pem) and p[0]["from"] == SM.fingerprint(pc_pem) and p[0]["shape"] == "well-formed", p)

    # ---- this PC's side: sealing the day's plan
    block, path = SM.seal_plan("phone", day, key_path=pc_key_path, plan_dir=plan_dir, signers_path=signers, outbox=outbox, log_path=log, now=now)
    check("SM1.10 seal_plan writes the block to the outbox", os.path.isfile(path) and open(path, encoding="utf-8").read().strip() == block.strip())
    _e, pobj, _s = SM.open_block(block, phone, phone_pem, expect_sender_pem=pc_pem, kind="plan")
    check("SM1.11 the sealed plan is the plan on disk, sha and all", pobj["plan"] == plan and pobj["plan"]["sha256"] == plan["sha256"])
    ltxt = open(log, encoding="utf-8").read()
    check("SM1.12 the ledger holds the plaintext of what was sealed (nothing hidden from the operator)", "SEALED plan for %s" % day in ltxt and plan["sha256"] in ltxt and "STUB POSTURE" in ltxt)
    try:
        SM.seal_plan("nobody", day, key_path=pc_key_path, plan_dir=plan_dir, signers_path=signers, outbox=outbox, log_path=log, now=now)
        check("SM1.13 REFUSED: sealing to a name the registry lacks", False, "sealed")
    except SM.SealedError as e:
        check("SM1.13 REFUSED: sealing to a name the registry lacks", "no registered" in str(e), e)

    # ---- the decision coming back
    tick = [now]

    def nxt():
        tick[0] += 60
        return tick[0]

    def decision(who, whopem, dec="approve", d=day, sha=None, nonce=None, note="from the road", to=pc_pem, ts=None):
        o = {"kind": "decision", "date": d, "plan_sha256": sha or plan["sha256"], "decision": dec, "note": note,
             "nonce": nonce or os.urandom(16).hex(), "ts": nxt() if ts is None else ts}
        return SM.seal("decision", o, who, whopem, to)
    kw = dict(key_path=pc_key_path, plan_dir=plan_dir, approvals=approvals, signers_path=signers, seen_path=seen, now=now, log_path=log)
    ok0, why0 = DP.approved(day, plan_dir, approvals)
    check("SM1.14 before any decision the gate says no", not ok0, why0)
    dblk = decision(phone, phone_pem)
    reply = "> " + block.replace("\n", "\n> ") + "\n\nApproved, see below\n\n" + dblk + "\n"
    code, out = SM.open_decision(reply, **kw)
    check("SM1.15 the phone's sealed approve, pasted under the quoted plan, is recorded", code == 200 and out["decision"]["signer"] == "phone" and out["decision"]["decision"] == "approve", out)
    check("SM1.15b the ledger row says it came by sealed mail and keeps the note", out.get("decision", {}).get("note", "").startswith("by sealed mail: from the road"), out)
    ok1, why1 = DP.approved(day, plan_dir, approvals)
    check("SM1.16 ...and the daily plan's gate now reads APPROVED", ok1 and "phone" in why1, why1)
    code, out = SM.open_decision(dblk, **kw)
    check("SM1.17 REFUSED: the same block a second time (nonce ledger on disk)", code == 409 and "already opened" in out["message"], out)
    code, out = SM.open_decision(decision(stranger, stranger_pem), **kw)
    check("SM1.18 REFUSED: a decision signed by a key the registry does not know", code == 403 and "not a registered" in out["message"], out)
    yday = DP.today(now - 86400)
    code, out = SM.open_decision(decision(phone, phone_pem, d=yday), **kw)
    check("SM1.19 REFUSED: a decision dated another day", code == 409 and "own day" in out["message"], out)
    code, out = SM.open_decision(decision(phone, phone_pem, sha="0" * 64), **kw)
    check("SM1.20 REFUSED: a decision for a plan whose hash is not today's", code == 409 and "changed" in out["message"], out)
    code, out = SM.open_decision(decision(phone, phone_pem, dec="maybe"), **kw)
    check("SM1.21 REFUSED: a decision word that is neither approve nor decline", code == 400, out)
    code, out = SM.open_decision(decision(phone, phone_pem, to=phone_pem), **kw)
    check("SM1.22 REFUSED: a decision sealed to the phone itself, not the PC", code == 400 and "not addressed" in out["message"], out)
    code, out = SM.open_decision(block, **kw)
    check("SM1.23 REFUSED: a plan block offered as a decision", code == 400 and "no decision sealed block" in out["message"], out)
    code, out = SM.open_decision(decision(phone, phone_pem, nonce="short"), **kw)
    check("SM1.24 REFUSED: a nonce too short to be one of ours", code == 409 and "nonce" in out["message"], out)
    code, out = SM.open_decision(decision(phone, phone_pem, dec="decline", note="changed my mind"), **kw)
    ok2, why2 = DP.approved(day, plan_dir, approvals)
    check("SM1.25 a later sealed DECLINE is the last word (the gate says no again)", code == 200 and not ok2 and "changed my mind" in why2, (out, why2))
    ltxt = open(log, encoding="utf-8").read()
    check("SM1.26 every refusal is in the ledger with its reason", ltxt.count("REFUSED") >= 7 and "already opened" in ltxt and "unregistered key" in ltxt, ltxt.count("REFUSED"))
    # ---- what a real reply looks like: the earlier mail quoted, the new block somewhere in it
    old_decline = decision(phone, phone_pem, dec="decline", note="quoted later")
    SM.open_decision(old_decline, **kw)                                      # opened once, now in the nonce ledger
    fresh = decision(phone, phone_pem, dec="approve", note="the real answer")
    threaded = "> " + old_decline.replace("\n", "\n> ") + "\n>\n> earlier\n\nnew answer below\n\n" + fresh + "\n\n> " + block.replace("\n", "\n> ")
    code, out = SM.open_decision(threaded, **kw)
    ok3, why3 = DP.approved(day, plan_dir, approvals)
    check("SM1.28 a reply quoting an already-opened block still records the fresh one", code == 200 and out["decision"]["decision"] == "approve" and out["applied"] == 1 and out["blocks"] == 2 and ok3, (out, why3))
    # two unseen blocks pasted newest-first: applied in the order they were MADE (ts), so the newest is the last word
    o1 = SM.blocks(decision(phone, phone_pem, dec="decline", note="first made"))[0]
    o2 = SM.blocks(decision(phone, phone_pem, dec="approve", note="made later"))[0]
    code, out = SM.open_decision(SM.armor(o2) + "\n\n" + SM.armor(o1), **kw)
    ok4, why4 = DP.approved(day, plan_dir, approvals)
    check("SM1.29 two fresh blocks are both recorded in the order they were made; the newest is the last word", code == 200 and out["applied"] == 2 and out["decision"]["decision"] == "approve" and ok4, (out, why4))
    junk = decision(phone, phone_pem, dec="decline", note="junk survives")
    lines = junk.splitlines()
    mangled = lines[0] + "\n" + "\n".join((" " + ln[:30] + "" + "­" + "" + ln[30:] + "" + "​" + "").replace("=", "=\r\n") for ln in lines[1:-1]) + "\n" + lines[-1]
    code, out = SM.open_decision("On the road:\n> quoted stuff\n\n" + mangled + "\n", **kw)
    ok5, why5 = DP.approved(day, plan_dir, approvals)
    check("SM1.30 no-break spaces, soft hyphens, zero-width marks and CRLF wraps inside the block are dropped", code == 200 and not ok5 and "junk survives" in why5, (out, why5))
    # ---- crafted blocks from someone who has seen a plan mail (so holds the PC's public key): refused, never a traceback
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from cryptography.hazmat.primitives import serialization
    ed = ed25519.Ed25519PrivateKey.generate()
    ed_pem = ed.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    e_dec = SM.blocks(decision(phone, phone_pem))[0]
    ok, why = refuses(lambda: SM.open_block(SM.armor(dict(e_dec, spk=ed_pem, **{"from": SM.fingerprint(ed_pem)})), pc, pc_pem), "not an RSA key")
    check("SM1.31 REFUSED: a non-RSA sender key is a reason, not a TypeError", ok, why)
    nested = SM.blocks(SM.seal("decision", {"kind": "decision"}, stranger, stranger_pem, pc_pem))[0]
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    import secrets
    ck, iv = secrets.token_bytes(32), secrets.token_bytes(12)
    hdr = {k: nested[k] for k in ("v", "kind", "to", "from")}
    deep = AESGCM(ck).encrypt(iv, ("[" * 100000).encode(), SM.canonical(hdr).encode())
    from cryptography.hazmat.primitives.asymmetric import padding as _pad
    from cryptography.hazmat.primitives import hashes as _h
    ek = SM._load_pub(pc_pem).encrypt(ck, _pad.OAEP(mgf=_pad.MGF1(_h.SHA256()), algorithm=_h.SHA256(), label=None))
    crafted = dict(hdr, ek=SM._b64(ek), iv=SM._b64(iv), ct=SM._b64(deep))
    crafted["sig"] = SM._b64(stranger.sign(SM.canonical(crafted).encode(), _pad.PSS(mgf=_pad.MGF1(_h.SHA256()), salt_length=_pad.PSS.MAX_LENGTH), _h.SHA256()))
    crafted["spk"] = stranger_pem
    ok, why = refuses(lambda: SM.open_block(SM.armor(crafted), pc, pc_pem), "not JSON")
    check("SM1.32 REFUSED: a plaintext nested until the parser gives up is 'not JSON', not a RecursionError", ok, why)
    code, out = SM.open_decision(SM.armor(crafted), **kw)
    ltxt = open(log, encoding="utf-8").read()
    check("SM1.33 ...and open_decision answers 400 and writes the refusal to the ledger", code == 400 and "not JSON" in out["message"] and "REFUSED a block: the plaintext is not JSON" in ltxt, (code, out))
    short_ek = dict(crafted, ek=SM._b64(b"short"))
    short_ek["sig"] = SM._b64(stranger.sign(SM.canonical({k: short_ek[k] for k in SM.ENVELOPE_KEYS}).encode(), _pad.PSS(mgf=_pad.MGF1(_h.SHA256()), salt_length=_pad.PSS.MAX_LENGTH), _h.SHA256()))
    ok, why = refuses(lambda: SM.open_block(SM.armor(short_ek), pc, pc_pem), "does not unwrap")
    check("SM1.34 REFUSED: a wrong-length wrapped key is a reason, not a ValueError", ok, why)
    bad_iv = dict(crafted, iv=SM._b64(b"x"))
    bad_iv["sig"] = SM._b64(stranger.sign(SM.canonical({k: bad_iv[k] for k in SM.ENVELOPE_KEYS}).encode(), _pad.PSS(mgf=_pad.MGF1(_h.SHA256()), salt_length=_pad.PSS.MAX_LENGTH), _h.SHA256()))
    ok, why = refuses(lambda: SM.open_block(SM.armor(bad_iv), pc, pc_pem), "cannot be opened")
    check("SM1.35 REFUSED: a wrong-length nonce is a reason, not a ValueError", ok, why)
    older = SM.seal("plan", {"kind": "plan", "issued": "2020-01-01T00:00:00-0000", "plan": {"date": "2020-01-01"}}, pc, pc_pem, phone_pem)
    _e, newest, _s = SM.open_block("> " + older.replace("\n", "\n> ") + "\n\n" + block, phone, phone_pem, kind="plan")
    check("SM1.36 of two plan blocks in one text the newest by 'issued' is the one that opens", newest["plan"]["date"] == day)
    # ---- two mails, opened in the wrong order: the phone's LAST word stays the last word
    early = decision(phone, phone_pem, dec="approve", note="made first")
    late = decision(phone, phone_pem, dec="decline", note="made later")
    code_l, out_l = SM.open_decision(late, **kw)
    code_e, out_e = SM.open_decision(early, **kw)
    ok6, why6 = DP.approved(day, plan_dir, approvals)
    check("SM1.37 the later-made decline opened first, then the earlier approve: the approve is refused and the gate stays declined",
          code_l == 200 and code_e == 409 and "newer decision" in out_e["message"] and not ok6 and "made later" in why6, (out_e, why6))
    a2 = decision(phone, phone_pem, dec="approve", note="made first, opened first")
    d2 = decision(phone, phone_pem, dec="decline", note="made later, opened later")
    c1, _o = SM.open_decision(a2, **kw)
    c2, _o = SM.open_decision(d2, **kw)
    ok7, why7 = DP.approved(day, plan_dir, approvals)
    check("SM1.38 ...and in the right order both are recorded, the later one the last word", c1 == 200 and c2 == 200 and not ok7 and "opened later" in why7, why7)
    check("SM1.39 the opened-nonce ledger carries the day and the phone's ts", all(isinstance(v, list) and v[0] == day for v in SM._seen(seen).values()) and len(SM._seen(seen)) >= 6, SM._seen(seen))
    # ---- what a mail client can do to the marker line itself
    nb = block.replace("BEGIN COVENANT SEALED", "BEGIN COVENANT  SEALED").replace("END COVENANT SEALED", "END\nCOVENANT SEALED")
    nb = nb[:-40].replace("=", "=3D") + nb[-40:].replace("=", "=3D")
    _e, pobj2, _s = SM.open_block(nb, phone, phone_pem, kind="plan")
    check("SM1.40 no-break or doubled spaces in the marker, a marker split over two lines, '=3D' for '=': still opens", pobj2["plan"]["sha256"] == plan["sha256"])
    lines = block.splitlines()
    damaged = "\n".join(lines[:5] + [lines[5][:-1]] + lines[6:])
    ok, why = refuses(lambda: SM.open_block(damaged, phone, phone_pem, kind="plan"), "damaged in transit")
    check("SM1.41 a block with one character lost says 'damaged in transit; copy it again', not 'no block'", ok, why)
    check("SM1.27 --explain text names the keys, the ledger and the public method", "sealed_mail.log" in SM.EXPLAIN and "public" in SM.EXPLAIN and "fingerprint" in SM.EXPLAIN)

    n, good = len(results), sum(results)
    print("SM1: %d/%d passed" % (good, n))
    return 0 if good == n else 1


if __name__ == "__main__":
    sys.exit(main())
