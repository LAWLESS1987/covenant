# Encrypting the peer link — a draft, held for the group

*Drafted 2026-09-12. Not built. This changes the protocol every node speaks,
which under the operator's own rule ("refinements only until a second
operator") waits for more than one voice.*

## The gap, stated

Nodes talk over plain TCP (peer port = API port + 1). Every transaction is
signed and every block hashed, so nothing can be forged or altered in
transit — but a device on the same network can **read** payload text as it
passes. The phone app's rule ("a phone is private to the person holding it")
holds for everything on the phone; it does not hold for the bytes between the
phone and the PC on the owner's Wi-Fi.

## What is proposed

1. **Keys already exist.** Every node has an RSA identity (`*.db.key`), and
   peers learn each other's public keys. Nothing new to distribute.
2. **A handshake per connection.** Each side sends an ephemeral X25519 key
   signed with its node identity; both derive a shared secret (HKDF-SHA256),
   then every frame is ChaCha20-Poly1305 with a per-direction nonce counter.
   This is the Noise `XX`-shaped pattern; the `cryptography` package the core
   already depends on has every primitive.
3. **Mutual, pinned.** A node refuses a peer whose identity key changed since
   it was last seen (an alert, not a silent reconnect), and an operator may
   pin the peers a node will speak to at all.
4. **Version-gated.** A node advertises `p2p_crypto=1`; two nodes that both
   advertise it encrypt; a node that does not is spoken to in the clear for
   one release and refused after that, so the mesh can move in steps.
5. **What it does not hide.** That two nodes talk, when, and how much. Block
   contents remain public to every peer by design — the ledger is shared.

## Cost

About 250 lines in `covenant_unified_v8.py`'s peer path plus a suite that
runs two nodes through the handshake and a tampered frame; one restart of
every node. No new dependency.

## The decision

Held. When a second operator exists, this is the first thing to put to
them, because it is the first change that is theirs as much as ours.
