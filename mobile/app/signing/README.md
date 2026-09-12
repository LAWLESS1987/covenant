# signing/debug.p12 -- the one fixed key, public by design

Android refuses to install an APK over an existing one unless both are signed
with the same certificate. A GitHub runner has no persistent debug keystore, so
without this file every CI build would fail to install over the last
(`INSTALL_FAILED_UPDATE_INCOMPATIBLE`), forcing an uninstall -- which deletes
the phone node's RSA identity and its chain database.

So this is a DEBUG-CLASS key committed in the open: PKCS12, alias `covenant`,
store and key password `android`, RSA-2048, valid to 2054, minted on 2026-09-12
with `cryptography` (no JDK on the build PC; `keytool` was not available).
Certificate SHA-256: `f524e4c0f2681eb37bc14cc445c2686867af18ee8117c4e77944da0edcf949f7`.

What it protects: update continuity, nothing else. Anyone can sign an APK with
it that installs over yours -- so install only what `android.yml` built from a
commit you trust, and compare `SHA256SUMS` on the release. If the operator ever
wants a private key it becomes the repository's first Actions secret, and every
phone must uninstall once (export the node's `.db.key` first, or lose it).
