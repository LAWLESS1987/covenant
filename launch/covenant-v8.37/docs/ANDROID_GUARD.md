<!-- Project copy of the CovenantGuard README, 2026-08-23.
     The buildable source was delivered to L by SendUserFile as
     `covenant-guard-src.tar.gz` (741 KB, 47 source files). THIS FILE IS NOT
     THE SOURCE — per M25, project_write is not delivery and neither is it a
     backup. If a future run needs the code, ask L for the tarball or rebuild
     from this document plus the file map in section 11. -->

# CovenantGuard

An on-device network privacy layer for Android: a local `VpnService` that
intercepts this phone's own DNS, decides what to answer, and forwards the rest.
No remote VPN server. No traffic to a third party. Every policy decision is made
in this process, synchronously, offline.

Written to be built and sideloaded by its owner. **I cannot install anything on
your phone** — the deliverable is source you build and install yourself, and
§6 is the exact command sequence.

---

## 0. Verification status — read this first

The build here was actually run, not asserted. What that means precisely:

| Claim | Status |
|---|---|
| `:policy-api`, `:core`, `:governance-*` compile | **measured** — Kotlin 2.4.10, JVM target 17 |
| Core logic unit tests | **measured — 89 tests, 0 failures** (`./gradlew test`) |
| `:app` debug APK builds | **measured** — AGP 9.3.1, Gradle 9.7.1, compileSdk 37 |
| `:app` release APK builds under R8 | **measured** — 1.1 MB unsigned |
| ProGuard keep rules preserve the governance seam | **measured** — every `PolicyProvider` implementation, including the separate example module, is present in the release dex |
| Manifest declares the VpnService correctly | **measured** — read back out of the built APK: `BIND_VPN_SERVICE`, `android.net.VpnService` intent filter, `foregroundServiceType=specialUse` |
| Signing and alignment | **measured** — zipaligned, signed, `apksigner verify` passes v2 + v3 |
| Android lint (release) | **measured** — 0 errors, 13 style warnings (listed in §7.9) |
| **Runtime behaviour on a real phone** | **NOT measured.** No device, no emulator. Nothing below the `establish()` call has ever executed against a real TUN. |

That last row is the honest limit of this work, and §7.1 says what specifically
is most likely to be wrong because of it.

Three real defects were found by the tests while writing this, all in code that
looked right. They are recorded in §8 rather than quietly fixed, because "the
tests found nothing" and "I wrote no tests" produce the same green README.

---

## 1. What this is, and the one architectural decision that matters

Android gives an unprivileged app exactly one supported way to see its own
device's packets: `VpnService`. That is all this uses it for. There is no tunnel
endpoint, no server, no credentials, no upstream provider. The "VPN" terminates
in this process, about two hundred lines from where the packet arrived.

The design follows NetGuard, RethinkDNS and Blokada in the one respect that
matters: **filter at DNS, not at the packet, unless you have a reason not to.**

Blocking a name costs one small UDP datagram round trip. Blocking a *connection*
costs a userspace copy of every byte the device sends and a userspace TCP/UDP
stack to put them back. The first is a battery cost you cannot measure; the
second is one you can, and it is why full-tunnel firewalls have a reputation for
eating phones. So:

* **DNS-only mode (default).** The TUN advertises itself as the DNS server
  (`10.111.222.1` / `fd00:c0e:c0e::1`) and routes **only that address**.
  Everything else on the device takes its normal path and never enters this
  process at all.
* **Full-tunnel mode (opt-in).** Routes `0.0.0.0/0` and `::/0`. Needed if you
  want per-app *connection* blocking rather than per-app *DNS* policy. See
  §7.5 for what is deliberately missing here.

---

## 2. Module layout, and why it is split this way

```
:policy-api          pure Kotlin/JVM — the STABLE governance contract
:core                pure Kotlin/JVM — DNS codec, IP/UDP + checksums,
                     blocklist, policy engine, tamper-evident audit log
:governance-default  the shipped no-op provider + rule-set provider
:governance-example  a worked third-party module (depends ONLY on :policy-api)
:app                 Android — VpnService, TUN loop, UID mapping, UI
```

The split is not tidiness. Everything that can be *wrong in a way nothing
notices* — checksum arithmetic, DNS name parsing, suffix matching, precedence
between conflicting rules, hash chaining — lives in `:core`, which has no
Android dependencies and therefore runs under `./gradlew test` on a laptop in
five seconds. What is left in `:app` is I/O and lifecycle: the part that
genuinely needs a phone, kept small precisely because it is the part I could
not test.

A bad UDP checksum does not throw. The phone's own stack silently drops the
reply and the app just hangs. That class of bug is why `IpPackets` is 250 lines
of pure functions with an RFC 1071 property test rather than inline code in the
service.

---

## 3. DNS filtering

### 3.1 The path a query takes

```
app  →  TUN (10.111.222.1:53)  →  IpPackets.parseUdp
                                →  DnsCodec.parseQuery      (strict; see 3.2)
                                →  PolicyEngine.decide      (the chain; see §5)
                                →  DENY  → DnsCodec.buildEmptyReply / buildAddressReply
                                          → IpPackets.buildUdp → written back to TUN
                                →  ALLOW → protect()ed DatagramSocket → real resolver
                                          → answer wrapped → written back to TUN
```

### 3.2 The parser is strict on purpose

`DnsCodec.parseQuery` refuses, rather than interpreting:

* compression pointers in the question section (a conforming query has nothing
  earlier to point at — a pointer there is malformed or an evasion attempt);
* `QDCOUNT != 1` (legal on the wire, universally unimplemented, and an obvious
  way to hide a second name from a filter that reads only the first);
* labels over 63 bytes, names over 255 wire bytes, non-printable bytes, and an
  **embedded dot inside a label** (which would make `a\x2Eb` and `a.b` parse to
  the same string while being different names);
* responses and non-zero opcodes arriving on the query path.

A filter's entire job is to decide from the QNAME, so a query whose QNAME is
ambiguous is a query whose policy is undecidable. **Default: drop it and log.**
`DnsFilter.Config(dropUnparseableDns = false)` forwards instead. The trade is
real in both directions and stated in the code: dropping risks breaking an app
using an exotic-but-legal encoding; forwarding gives anything that can craft one
a hole through the filter. If you hit an app this breaks, that is a finding
worth writing down.

The parser is fuzzed against 4,096 random messages per run with one assertion:
it returns. A parser on the packet path that can throw is a crash per hostile
datagram; one that can loop is a wedged phone.

### 3.3 Matching: hash sets, not a trie

The brief suggested "a trie or hash set with wildcard support". This uses two
hash sets and a right-to-left label walk, and the reason is worth stating
because a trie is the intuitive answer:

A domain has at most a handful of labels. Matching `ads.tracker.example.co.uk`
against a suffix set costs one hash lookup per suffix — five or six O(1)
lookups. A character trie over a 200,000-entry list costs one node hop per
*character* (24 here) and, on a JVM, one object per node. A trie wins on
*prefix* queries; a DNS filter only ever needs *suffix* queries, which a
label walk over a set already is.

Measured on this machine (`BlocklistTest.handlesAListOfRealisticSizeQuickly`):

```
200,000 entries   build 1.2 s   200,000 worst-case lookups 128 ms  (~0.6 µs each)
```

Formats accepted in one pass: hosts (`0.0.0.0 host`, multiple hosts per line),
bare domains, `*.domain` and `.domain` wildcards, Adblock host rules
(`||domain^`), and allow entries (`@@||domain^`, `+domain`). Localhost noise is
skipped. **Anything unparseable is counted, not silently dropped** — a loader
that quietly accepts garbage produces a list that quietly does not block what
its author thinks it blocks.

Allow entries beat block entries at every level, including a broad allow over a
narrow block. A personal firewall that cannot be told "except this one" gets
switched off entirely, which blocks nothing at all.

### 3.4 Loading lists

Put hosts-format files in the app's private storage:

```
/data/data/org.covenant.guard/files/blocklists/
```

and press **Reload blocklists**. Via adb on a debug build:

```bash
adb push stevenblack-hosts.txt /data/local/tmp/
adb shell run-as org.covenant.guard mkdir -p files/blocklists
adb shell run-as org.covenant.guard cp /data/local/tmp/stevenblack-hosts.txt files/blocklists/
```

**There is no automatic list download, deliberately** (§7.2). The app makes no
network request other than forwarding the DNS queries it did not block.

---

## 4. Per-app control

`VpnService.Builder` offers two mutually exclusive mechanisms, and the framework
throws if you combine them — so this is a *mode*, not a pair of lists, and the
UI says so:

* **Exempt mode (default)** — `addDisallowedApplication`. Checked apps bypass
  the tunnel entirely; their traffic is never seen and never filtered. The right
  tool for anything that must not be interfered with.
* **Allow-list mode** — `addAllowedApplication`. Only checked apps are tunnelled.

The service always exempts **itself**. Without that, the upstream query this
service makes on a client's behalf re-enters its own TUN and the result is a
loop that presents as a hang.

**UID→package attribution** uses `ConnectivityManager.getConnectionOwnerUid()`,
API 29+. Below that, Android gives an unprivileged app no way to attribute a
packet, so identity is reported as **unknown (-1 / null) rather than guessed**,
and the API documents that a provider keying on identity must handle that case
explicitly. The example module does: it *abstains* when identity is unknown
rather than letting a per-app rule silently not match — treating "unknown" as
"not that package" exempts exactly the traffic the rule exists to catch.

---

## 5. The integration vector

This is the part the brief singled out, so it gets the most design attention.
"Governance" was not defined, so the interface is built to accommodate several
readings without committing to one.

### 5.1 The contract

`:policy-api` is one file, ~400 lines, no dependencies. It contains:

| Piece | What it is |
|---|---|
| `PolicyProvider` | the extension point: `evaluate(DecisionContext): Verdict?` |
| `DecisionContext` | domain, qtype, uid, package, timestamp, minute-of-day, transport, network kind |
| `Verdict` / `Decision` | `ALLOW` / `DENY` / `LOG`, with provider id, rule id, reason, sinkhole mode |
| `RuleSet` / `Rule` / `Match` | the versioned policy schema, with `validate()` |
| `AuthorityModel` / `Capability` / `ChangeRequest` / `Approval` | who may change what |
| `AuditLog` / `AuditEvent` / `AuditVerification` | the tamper-evident record |

Three rules are stated in the file header and enforced by the engine:

1. **`evaluate` is on the packet path.** Synchronous, with the client's app
   blocked on the answer. No I/O, no IPC, no disk, no network — and never a
   call to a remote model (§9).
2. **Abstain by returning `null`.** Returning ALLOW "because I have no rule" is
   how a permissive default silently outranks a real DENY.
3. **Verdicts are data, not effects.** No device state, no UI, no files from
   `evaluate`.

### 5.2 Precedence and conflict resolution

Providers are consulted in ascending `priority`, ties broken by `id`, so the
order is **total and reproducible** — a chain whose order depends on
registration order gives different answers after a reboot and nobody ever finds
out why. `PolicyEngineTest` asserts that registering the same three providers in
reverse order produces the identical chain.

**Every provider is consulted on every decision.** The chain does not stop at
the first opinion. That costs a few hash lookups and buys two things worth more:
the audit log can record that a second module also had a view, and a
low-priority DENY cannot be hidden by a high-priority ALLOW that merely ran
first.

Resolution, in full:

* **DENY is absorbing.** Any DENY, from any provider, denies — attributed to the
  strongest (lowest-numbered) denier.
* **One exception: an explicit override.** A provider that declares
  `canOverrideDeny = true` **and** sits at *strictly stronger* priority than
  every DENY can return ALLOW and win. Every such event is written to the audit
  log with `wasOverride = true`.
* **`LOG` never decides anything.**
* **Nobody had an opinion** → the engine default (`ALLOW`; see §7.4).
* **A throwing provider abstains** — it does not deny (a crashing module must
  not be able to take the network down) and does not allow (or `throw` becomes
  the cheapest possible bypass). Both are asserted.
* **A slow provider is recorded, not killed.** There is a per-provider
  nanosecond budget; overruns are counted and surfaced, because killing a
  decision mid-flight needs a thread per query, which costs more than it saves.

The asymmetry is deliberate: it takes a declaration *plus* higher standing to
un-block something, and nothing at all to block it. A governance layer whose
modules can quietly permit is not a governance layer.

The app's own blocklist is an ordinary `PolicyProvider` at priority 100 with no
special standing — asserted by a test in which a governance module at priority
10 overturns it.

### 5.3 The extension point: in-process module, not AIDL — and why

**Chosen: a Gradle module boundary, linked in-process, registered in one place
(`GuardApp.buildChain()`).**

The alternative — a bound AIDL service that third-party governance APKs
implement — was rejected *for the decision path* for three reasons:

1. **Latency.** A Binder transaction per DNS question adds a context switch and
   a serialisation round trip to every name the phone resolves, on the critical
   path of every app launch and every page load.
2. **Liveness.** A separate process can be slow, frozen by the platform, killed,
   or simply not there. The decision path would then need a timeout policy, and
   *whatever that policy is, it is a security decision made by a scheduler*.
   Fail-open on timeout is a bypass; fail-closed is a third-party process able
   to take the device's DNS down by being slow.
3. **Trust.** An exported decision hook is a way for any app that can bind it to
   see every domain this device resolves. That is precisely the surveillance
   this app exists to prevent, rebuilt as a feature.

**AIDL is used, for the control plane only.** `IGovernanceControl`
(`app/src/main/aidl/`) exposes install-rules, list-providers, audit-head-hash
and verify-audit — all off the packet path, all at human speed, all gated
through the `AuthorityModel`. It is **not exported**; reaching it from another
APK is a deliberate act of configuration.

The honest cost of this choice: a governance module must be **compiled into the
APK**, so installing one means rebuilding and reinstalling. For a personal
device that is the right trade. If you need drop-in modules from other APKs,
§7.8 sketches what would have to change.

### 5.4 The four readings of "governance", and where each lands

| Reading | Status |
|---|---|
| Policy over which apps/domains get network access | **built** — `RuleSetProvider`, `QuietHoursProvider` |
| An approval/authority model for who may change rules | **built** — `AuthorityModel`, `SoleOwnerAuthority` (shipped), `TwoKeyAuthority` (example) |
| A tamper-evident audit log of decisions | **built** — `HashChainAuditLog` |
| Multi-party / remote attestation | **interface only, deliberately** |

The last one is a hook, not an implementation, and that is a considered
position. Remote attestation on the decision path would mean a network call per
decision — reintroducing exactly the latency, liveness and privacy problems of
§5.3, over the internet instead of over Binder. The place it belongs is the
control plane: attest the *rule set* out of band, at install time, and let the
packet path stay local and synchronous. `RuleSet.signature` and
`ChangeRequest.payloadDigest` are where that verification hangs. I have not
implemented it because I do not know what you would attest to.

### 5.5 Writing a governance module

Real, complete, and it is what `:governance-example` does.

**1. New Gradle module, one dependency.**

```kotlin
// governance-mine/build.gradle.kts
plugins { alias(libs.plugins.kotlin.jvm) }
dependencies { implementation(project(":policy-api")) }   // and nothing else
```

**2. Implement the provider.**

```kotlin
class MyGovernance : PolicyProvider {
    override val id = "org.example.governance.mine"
    override val priority = PolicyProvider.PRIORITY_BLOCKLIST - 10   // stronger than the blocklist
    override val canOverrideDeny = false                             // cannot un-block

    override fun evaluate(ctx: DecisionContext): Verdict? {
        if (ctx.packageName != null && !ctx.identityKnown) return null   // abstain, don't guess
        if (ctx.domain.endsWith(".example.invalid")) {
            return Verdict(Decision.DENY, id, ruleId = "no-invalid", reason = "policy: invalid TLD")
        }
        return null                                                   // abstain
    }

    override fun onRulesUpdated(rules: RuleSet) { /* off the packet path */ }
    override fun describe() = "$id — my house rules"
}
```

**3. Register it — two lines, in one place.**

```kotlin
// settings.gradle.kts:   include(":governance-mine")
// app/build.gradle.kts:  implementation(project(":governance-mine"))
// GuardApp.buildChain(): engine.register(MyGovernance())
```

That is the entire integration. If adding a module ever requires a change
anywhere else, that is a bug in the seam.

**Choosing a priority band:**

| Band | Meaning |
|---|---|
| `PRIORITY_OVERRIDE` (10) | may pre-empt the blocklist; the only band where `canOverrideDeny` does anything against it |
| `PRIORITY_BLOCKLIST` (100) | the built-in hosts-file list |
| `PRIORITY_REFINEMENT` (500) | refines what got through; cannot un-block |

**Rules you must respect, restated because each one has a failure attached:**

* Abstain (`null`) unless you have an actual opinion.
* Never block, never do I/O, never allocate heavily in `evaluate`.
* Handle `identityKnown == false` explicitly.
* Refuse a `RuleSet` whose `schemaVersion` you do not know rather than reading
  the fields you recognise — silently ignoring an unknown field in a *policy*
  document is how a DENY becomes an ALLOW.
* Refuse a rule set whose `revision` does not exceed the installed one, or
  replaying an old signed set is a downgrade attack on your own policy.

### 5.6 The audit log, and what "tamper-evident" is worth

`HashChainAuditLog` writes `<hash>\t<canonical record>` per line, where
`hash = SHA-256(previousHash ‖ 0x1F ‖ canonical)`.

It **does** make a partial edit detectable: deleting the one line that records a
block, or flipping a DENY to an ALLOW after the fact, breaks that line's hash
and every hash after it. `verify()` names the first bad record. That is the
realistic threat — quiet removal of one inconvenient entry.

It **does not** stop anyone who can write the whole file from recomputing the
chain: the hash is public and there is no secret. Making that impossible needs
either a key the writer cannot read (Android Keystore with
`setUserAuthenticationRequired`, so the head is signed by hardware) or an
off-device witness the head is periodically published to. Both are left as
hooks — `headHash()` is exactly the value you would sign or publish — and
neither is implemented, because implementing either badly is worse than not
claiming it.

Two details that are easy to get wrong and are tested:

* **Field injection.** A provider's `reason` is free text. If it could contain
  the field separator it could forge a record boundary inside its own entry.
  The canonical form strips `0x1F`, `\n` and `\r`, and bounds the text to 240
  characters. A test puts a forged `…ALLOW…` inside a `reason` and asserts the
  record still has exactly ten fields.
* **Rotation.** A rotated log that restarts at GENESIS makes "the chain
  verifies" meaningless. Each new segment opens with an `#anchor` line naming
  the head it continues from, so a rotated chain still verifies and
  `AuditVerification.historyRotated` reports that older records are gone —
  "verified, with history rotated" and "broken" are different facts and
  collapsing them into one boolean loses what the reader needs.

---

## 6. Building, signing, installing

### 6.1 Requirements

* JDK 17+ (JDK 21 used here)
* Android SDK: **platform 37**, **build-tools 37.0.0**, platform-tools
* Gradle wrapper is included — do not use a system Gradle

Point the build at your SDK either with `ANDROID_HOME` or by editing
`local.properties` (which is machine-local and should never be committed —
the one in this tree points at the sandbox path used to build it).

### 6.2 Build

```bash
./gradlew test                    # 89 core tests, no device needed
./gradlew :app:assembleDebug      # app/build/outputs/apk/debug/app-debug.apk
./gradlew :app:assembleRelease    # app/build/outputs/apk/release/app-release-unsigned.apk
./gradlew :app:lintRelease
```

### 6.3 Sign

One keystore, kept safe: **if you lose it you cannot upgrade an installed
build in place**, only uninstall and reinstall, which erases the audit log.

```bash
keytool -genkeypair -v -keystore ~/covenantguard.jks \
  -alias covenantguard -keyalg RSA -keysize 4096 -validity 10000 \
  -dname "CN=CovenantGuard Sideload, O=Personal, C=US"

$ANDROID_HOME/build-tools/37.0.0/zipalign -p -f 4 \
  app/build/outputs/apk/release/app-release-unsigned.apk aligned.apk

$ANDROID_HOME/build-tools/37.0.0/apksigner sign \
  --ks ~/covenantguard.jks --ks-key-alias covenantguard \
  --out covenantguard-release.apk aligned.apk

$ANDROID_HOME/build-tools/37.0.0/apksigner verify --verbose --print-certs \
  covenantguard-release.apk
```

`zipalign` **before** `apksigner`, never after — signing an unaligned APK then
aligning it invalidates the v2/v3 signature.

Verified output on this build: `Verifies`, v2 `true`, v3 `true`. v1 (JAR
signing) is `false` and that is correct: `apksigner` omits it at `minSdk 26`
because no supported device needs it.

For day-to-day use `./gradlew :app:assembleDebug` is signed with the debug key
automatically and is enough.

### 6.4 Sideload

```bash
adb devices                                   # confirm the phone is listed
adb install -r covenantguard-release.apk
# replacing a build signed with a different key:
adb uninstall org.covenant.guard && adb install covenantguard-release.apk
```

Then open the app and turn **Protection** on. Android shows the system VPN
consent dialog — that dialog is the security property, it cannot be
pre-granted or bypassed, and a key icon appears in the status bar for as long
as the VPN is up.

Watching it work:

```bash
adb logcat -s CovenantVpn:* GuardApp:* BootReceiver:*
```

---

## 7. Assumptions I made, and what you should correct

Every one of these is a guess about your intent. They are numbered so you can
reply "7.3 is wrong" instead of re-describing the whole thing.

**7.1 The largest one: nothing has run on a phone.** There is no device or
emulator here. Everything below `builder.establish()` — the TUN read loop, the
`protect()`ed upstream socket, UID attribution, doze behaviour, the foreground
notification — is *written to be correct* and has never executed. If something
is broken, my ranked guesses are: (a) `getConnectionOwnerUid` returning -1 for
TUN-sourced sockets on your OEM's build, making per-app DNS rules inert;
(b) the `specialUse` foreground-service type being rejected on your Android
version; (c) IPv6 behaviour on a carrier that hands out a v6-only network.
Start with `adb logcat` and §6.4.

**7.2 No automatic blocklist downloads.** The brief asked for "list update
mechanics" and I gave you loading, parsing, hot-swap and a reload button, but no
fetcher. Reason: an app whose whole claim is "nothing leaves the device" that
also phones a URL on a timer has one more thing to trust and one more thing to
audit. Tell me and I will add a fetcher with an explicit host allowlist and a
signature check.

**7.3 `QUERY_ALL_PACKAGES`.** Used so the per-app screen can enumerate installed
apps. Honest for a personal sideload, unacceptable for Play. The narrower
alternative is a `<queries>` block, but it cannot express "every app with
INTERNET". If you would rather have the narrow form and a shorter app list, say
so.

**7.4 Engine default is ALLOW.** This is a blocklist-shaped tool, and a
default-deny resolver on a phone is a phone with no network. Default-deny is one
line (`EngineConfig(defaultDecision = Decision.DENY)`) plus a governance module
that allows what you want — a deliberate choice, not a shipped surprise.

**7.5 Full-tunnel mode routes everything but only *filters* DNS.** Implementing
per-app *connection* blocking properly needs a userspace TCP/UDP stack to
forward the traffic that is allowed through (NetGuard ships one in C; RethinkDNS
uses a Go stack). Writing a half-working one would produce an app that appears
to work and drops connections at random. So full-tunnel mode is honest about
what it is: the plumbing and the mode switch exist, and non-DNS packets are
currently passed over rather than forwarded. **If per-app connection blocking is
what you actually want, that is the next substantial piece of work and it is
better done by vendoring a proven stack than by writing one.**

**7.6 Foreground service type `specialUse`.** API 34+ requires a type on
`startForeground`. VpnService has no dedicated type; `specialUse` with a
declared subtype is the fit, and the declared string says exactly what it does.
Google Play would question it; a sideloaded personal build is fine. If you ever
want this on Play, that conversation starts here.

**7.7 `installRules` over AIDL is a stub.** Parsing a rule set from JSON needs a
codec, and shipping a half-checked parser *on the path that installs policy* is
worse than shipping none. The authority check around it is real and runs; the
parse is not there. Named gap, not an oversight.

**7.8 Governance modules are compile-time.** §5.3 explains why. Supporting
drop-in modules from other APKs would need: a signature-pinned allowlist of
permitted module packages, a `ServiceLoader`-style discovery pass at process
start (not per decision), and a hard rule that a discovered module is loaded
into *this* process rather than consulted over IPC. All doable; none guessed at.

**7.9 Lint warnings left standing:** `UseKtx` ×7 (a stylistic preference for
`SharedPreferences.edit {}`), `PluralsCandidate` ×4 (plural strings in an
English-only build), `NotifyDataSetChanged` ×1 (a 300-row list where the diffing
is not worth it), `ObsoleteSdkInt` ×1 (a `-v26` resource qualifier that is
redundant at `minSdk 26`). Zero errors. I left them because each is a real
trade rather than an oversight — but a standing warning trains its reader to
skim, so if you would rather see zero, say and I will clear them.

**7.10 Fallback resolver is Quad9 (`9.9.9.9`).** Only reached when the platform
reports no system resolver at all. Normally the device's own configured DNS is
used, because silently moving you onto some third party's resolver is the
precise thing this app exists to prevent. Constant is at the bottom of
`CovenantVpnService`.

**7.11 Package/app name.** `org.covenant.guard` / "CovenantGuard" — inferred
from your other work. Cosmetic; change `namespace` and `applicationId` in
`app/build.gradle.kts`.

---

## 8. What the tests caught

Written down because a README that says "tested" and one that says "I wrote
tests that found nothing" look identical, and these three were all in code that
read correctly.

1. **The suffix walk never reached the apex.** `Blocklist.lookup` re-sliced the
   *original* domain each round using an index taken from the *current*
   candidate, so it oscillated between two strings and terminated on the loop
   guard. Effect: `*.tracker.example` did not block `deep.sub.tracker.example`.
   Every wildcard entry in a real blocklist was silently inert beyond one level.
   Caught by `BlocklistTest.lookupReportsWhatMatchedSoTheAuditLogCanNameIt`.

2. **The audit log erased itself on restart.** `File.bufferedWriter()`
   truncates. The first append after a process restart wiped the entire prior
   chain — committed by the very class whose purpose is making deletion
   detectable. Caught by
   `AuditLogTest.appendingAfterReopeningContinuesTheSameChain`.

3. **Rotation destroyed verifiability.** With more than two segments the older
   one is dropped, so the live file's first record no longer chained from
   GENESIS and `verify()` reported a permanent break — a check that is always
   red, which is a check nobody reads. Fixed with the `#anchor` mechanism in
   §5.6. Caught by `AuditLogTest.rotationKeepsTheChainVerifiableAcrossSegments`.

One test assertion was also wrong in a way worth recording: the rotation test
originally asserted `recordsChecked > 20`, a guessed number that would break
whenever a field width changed. It now asserts the actual property — that
`verify()` covers every record held across both segments.

The pinned canonical-form digest in `AuditLogTest` was computed **independently
in Python from the written spec**, not by running the Kotlin and copying what it
printed. Both agree on
`561082c5e0772a94c54deb50526dd1a4b8101966e9ebeb33b50f5540c6c309fb`. A pinned
value produced by the code it is meant to check is a photograph, not an oracle.

---

## 9. Why no model call is on the packet path

The constraint was stated and it is right; here is the arithmetic behind it.

**Latency.** A DNS lookup that a filter answers locally costs microseconds; one
forwarded upstream costs single-digit milliseconds. A remote model call costs
hundreds of milliseconds to seconds. A phone resolves dozens of names opening a
single app. Putting a model in that path does not slow the network down, it
stops it.

**Cost.** Per DNS query, on a device that makes thousands a day, forever, on a
battery.

**The privacy inversion, which is the real one.** This app exists so that the
list of everything you look up stays on your phone. Sending each name to a
third party to ask whether to block it *is* the surveillance, performed by the
tool bought to prevent it — and worse than the tracker, because the tracker only
sees its own domain and this would see all of them.

**Non-determinism.** A filter that answers differently for the same name on
Tuesday is not a policy, it is a mood. Every rule here is deterministic and
every decision names the rule that produced it.

Where a model *is* useful is off the path and at human speed: curating a
blocklist, explaining why a domain was blocked when you ask, summarising the
audit log. All of that can happen without a single packet decision leaving the
device, and none of it is in this build.

---

## 10. Coexisting with other VPNs, battery, and doze

### 10.1 One active VPN at a time — the constraint with no workaround

**Android permits exactly one app to hold the VPN interface.** Starting this one
tears down whatever was running; starting another tears this one down, and this
app receives `onRevoke()` and stops cleanly. There is no API to chain, stack or
share it. `VpnService.prepare()` returning non-null is how you learn another app
holds it.

Practically:

* **You cannot run this alongside Tailscale, WireGuard, a corporate VPN, or
  another content blocker.** It is one or the other.
* The usual way out is **one app doing both** — the reason NetGuard and
  RethinkDNS grew their own tunnel support. If you need this filtering *and* a
  real VPN, the honest options are: use the other app's own blocking if it has
  any; or move the filtering off-device to a resolver you control (which is
  exactly the "traffic leaves the device" trade this app was written to avoid);
  or extend this app to carry your tunnel, which is a much larger project.
* **Private DNS (DoT/DoH) set in Android settings bypasses this filter
  entirely.** System DNS-over-TLS does not go through the TUN's DNS server. If
  you have Private DNS set to anything but "Automatic"/"Off", turn it off or
  this app sees nothing. Apps with hardcoded DoH (some browsers) likewise
  bypass it — visible as "this domain is definitely blocked but the ad still
  loads".

### 10.2 Battery

* **DNS-only mode is the design's whole battery answer**: one small datagram per
  lookup, no per-packet copying, and the read loop is `setBlocking(true)` so the
  thread parks rather than spins.
* Full-tunnel mode copies every packet into userspace. Expect a real, visible
  cost, and turn it on only if you need it.
* The upstream pool is bounded (8 threads, 128 queued, discard on overflow) and
  what it discards is counted. One thread per outstanding query is how a DNS
  proxy turns a burst into thousands of threads; a bounded pool turns the same
  burst into a few retried lookups.

### 10.3 Doze and process death

A foreground service with an ongoing notification is what keeps this alive; the
notification is not decoration, it is the mechanism, and Android requires it.
Beyond that:

* Some OEM builds (Xiaomi, Huawei, Samsung to a degree) kill foreground services
  anyway. If it stops overnight, exempt it from battery optimisation in Settings
  → Apps → CovenantGuard → Battery → Unrestricted.
* `START_STICKY` asks the platform to restart the service after a low-memory
  kill; the restart arrives with a null intent, which `onStartCommand` handles.
* `BootReceiver` restarts after a reboot **only if** the user had it on *and*
  consent is still granted. A boot receiver cannot show the consent dialog, so
  if consent is missing it does nothing and waits for you to open the app —
  rather than running a service that displays "protected" over a device that
  is not.

---

## 11. File map

```
policy-api/src/main/kotlin/org/covenant/guard/policy/PolicyApi.kt
    the whole contract: PolicyProvider, DecisionContext, Verdict, RuleSet,
    AuthorityModel, AuditLog

core/src/main/kotlin/org/covenant/guard/core/
    dns/DnsCodec.kt        strict RFC 1035 reader + reply builder
    net/IpPackets.kt       IPv4/IPv6 + UDP parse/build with RFC 1071 checksums
    block/Blocklist.kt     hosts/Adblock parsing, suffix matching, allow rules
    engine/PolicyEngine.kt the decision-hook chain and conflict resolution
    engine/BlocklistProvider.kt  the built-in list, as an ordinary provider
    engine/DnsFilter.kt    packet in → Action out; the whole filtering decision
    audit/HashChainAuditLog.kt   append-only tamper-evident log

core/src/test/kotlin/...    66 tests
governance-example/...      a worked module + 11 tests
app/src/main/kotlin/org/covenant/guard/app/
    GuardApp.kt            process wiring; buildChain() is the whole seam
    vpn/CovenantVpnService.kt  TUN lifecycle, packet loop, upstream forwarding
    vpn/BootReceiver.kt
    glue/GovernanceControlService.kt  the AIDL control plane
    ui/                    MainActivity, AppListActivity, LogActivity
app/src/main/aidl/org/covenant/guard/control/IGovernanceControl.aidl
```
