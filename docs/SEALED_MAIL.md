# Sealed mail: the plan and the decision, by email, readable only at the ends

The operator's ask, 2026-09-13: "encode the email in a way only you and the
node understand for security but explain to me when asked". This is the
explanation, written before it was asked, so it is the same every time.

## What travels

One text block. It can sit in an email, a chat, a share sheet, a notes app:

    -----BEGIN COVENANT SEALED-----
    eyJjdCI6Ii4uLiIsImVrIjoiLi4uIiwiZnJvbSI6ImE2MGJiMjBmMTVhZmU1ZDgiLCJpdiI6...
    -----END COVENANT SEALED-----

Inside the base64 is a JSON envelope: version, kind (`plan` or `decision`),
the fingerprint of the key it is addressed **to**, the fingerprint of the key
it is **from**, a content key wrapped so that only the recipient's private key
can unwrap it (RSA-OAEP, SHA-256), the message itself under that content key
(AES-256-GCM, with the header as authenticated data), a signature by the
sender's private key over everything above (RSA-PSS, SHA-256), and the
sender's public key so the reader can check the signature without a lookup --
the reader still compares that key with the one it already trusts.

## Whose keys

The ones the two nodes already own. The PC node's identity key
(`nodeA_prod.db.key`) and the phone node's identity key, the one registered
as the daily-plan signer `phone`. No new key is minted for the mail. A
fingerprint is the SHA-256 of the whitespace-stripped public key PEM, first
16 hex digits -- the same number the approvals ledger records as
`pubkey_sha256`, so the ledger, the registry, the phone screen and
`python covenant_sealed_mail.py --fingerprint` all show the same short id.

## Who can read what

- A plan sealed to the phone opens only on the phone. The PC that sealed it
  cannot open it again; it kept the plaintext in its own ledger.
- A decision sealed to the PC opens only on the PC.
- Google, Yahoo, a carrier, a person reading the inbox: they see the block
  and nothing inside it.
- A decision counts only if all of these hold on the PC: the signature is a
  registered signer's; the date in it is TODAY here; the plan's sha in it is
  the plan on disk; the nonce in it has never been opened here (a ledger on
  disk, `ops/sealed_mail_seen.json`). So a captured block cannot be replayed
  tomorrow, and a mail "from" the operator's address that was not signed by
  the phone's key is refused with the reason written down.

## Nothing hidden from the operator

Every block sealed or opened on the PC is written in plain text to
`ops/sealed_mail.log` (gitignored): the time, who to whom, and the whole
plaintext. On the phone the app's own log records each open and each
decision. The method is this document and `covenant_sealed_mail.py`; only the
keys are private. That is the honest meaning of "only you and the node
understand": a secret method would be a weaker promise than a public method
with private keys, and it would be one the operator could not check.

    python covenant_sealed_mail.py --explain        this, in the module's words
    python covenant_sealed_mail.py --peek FILE      who -> whom, kind, size; no key needed
    python covenant_sealed_mail.py --log            the ledger's last lines
    python covenant_sealed_mail.py --fingerprint    this PC's key, to compare on the phone

## The day, end to end

1. The PC writes the plan (nightly, or `python covenant_daily_plan.py --write`).
2. `python covenant_sealed_mail.py --seal-plan --to phone` prints the block and
   saves it under `ops/sealed_mail/`. The block goes into an email to the
   operator by whatever sends mail from the PC (today: the assistant's Gmail
   connector, at the operator's word; a PC-side mailer needs a credential only
   the operator can create).
3. On the phone, Today -> Sealed mail: paste the block (or "Paste from
   clipboard"), Open. The first time, the PC's key is pinned and its
   fingerprint shown; compare it with what the PC prints. Read the plan.
4. Approve or Decline. The app produces a sealed reply, copies it to the
   clipboard and offers the share sheet; reply to the plan email and paste.
5. On the PC, `python covenant_sealed_mail.py --open reply.txt` (or the
   mailbox watcher) verifies it and records the decision through the same
   `handle_decision` the network route and `--approve` use: one ledger, one
   gate (guards reason 7).

## Order

Decisions made on the phone are ordered by when the phone made them (the
`ts` inside the block), not by when their mails were opened on the PC: a
block made earlier than the newest one already opened for that day is
refused, so opening two replies in the wrong order still leaves the phone's
last word as the ledger's last word. This orders sealed decisions against
each other only; `--approve` on the PC and the network route write the
ledger directly and are not ordered against a sealed block's `ts`.

## What it is not

Not a substitute for the pinned-key check: the first sealed plan the phone
ever opens is trusted on first use, which is why the fingerprint is shown and
the PC prints its own. Not private from the two ends: both keep the plaintext,
on purpose. Not advice: the plan says what the checkers said; the person
decides.

Pinned by `test_sm1_sealed_mail.py` (43 checks) and, for the phone's mirror of
the primitives, M5.13 in the app's own suite, which seals with one side and
opens with the other, both ways.
