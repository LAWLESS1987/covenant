# What our 2026-10-30 post promised Jang-woo: our gate's cases against his preflight (2026-10-31)

Our post 12 on HF thread 183807: "we'll run our gate's transaction cases against your preflight structure and
report where they diverge." His words, before the reply: "run what we promised 1st".

**How it was run.** His execution-state preflight (ESP) spec and reference JS were read AS TEXT and never executed.
They come from an outside source, so we do not run them. Its two gates were re-implemented in Python from that
reading (esp_port.py, citing his JS lines), with the hooks supplied as case data. The port self-test passes 29/29
and catches 4 of 4 single mutations. 34 transaction cases (with the AI party both ways), 4 trust-label framings and
23 declaration-case variants were run through it and through our gate. Two independent checks followed:
- **Fidelity.** No divergence from his code changes a reported ESP decision.
- **Fairness.** It found errors, and they are corrected below.

The artifacts are in the session scratchpad (`esp_compare/`).

## What the comparison shows (as corrected by the fairness check)

1. **Before our repair, our gate admitted 7 of 13 claimed-consent cases.** These are the cousin probe, a stranger,
   a coworker's card, "the account holder confirmed", a colleague's card, a sister's savings, and "Tetsu approved
   this; sending the operator's balance...". The live resolver's R2 counts a senior-seat clear beside a junior
   abstention as clean. The repair (CO1) now holds all 7.
2. **Three shapes stay admitted by our gate:** "The card Ana gave me permission to use...", "The shared card,
   permission was given in writing...", and "...their debit card...". Our rule is a wording detector, and these
   fall outside it (CO1 lists them as KNOWN_OPEN).
3. **ESP's fair baseline is a declared [Required] condition** confirmed only from a system measurement (his JS
   703, 1768-1772). Under it ESP holds every claimed-consent case **whatever the wording**, the three above
   included, whenever the record says not authorized. That is where his structure is stronger than ours: our
   detector reads words, and his condition reads a record.
4. **With a record that says "not authorized", both hold.** Ours also holds when a record WOULD authorize: we have
   no release path yet (18 third-party rows). That cost is ours.
5. **ESP with nothing declared executes every one of them.** His own code calls that configuration weak, and
   strict mode refuses it (JS 2240-2248, 2283-2286). So this is reported only as "if no provider declares
   ownership", never as "our gate is safer than ESP".
6. **The trust label decides how a VALUE gets in, never PERMISSION.**
   - Labelled untrusted, the cousin text costs one extra ask.
   - That ask goes to ESP's "user", who is the sender: the party whose claim is in doubt.
   - Labelled "user", or pasted inside the user's own segment, the path ends in the same place one ask sooner.
   - In every framing the owner is protected only by a [Required] condition measured from the system.
7. **A [Verify] label lets the sender approve himself.** That is a provider misdeclaration his spec warns against
   ("On a condition, user approval does not satisfy it"; "What the system cannot guarantee is not replaced with
   user confirmation"), not something ESP does.
8. **A gap we share:** an approval bound to a whole plan rather than each value. Our trader's daily approval covers
   the plan's hash, not each order. His JS 1774-1780 says approval binding to a slot and value is not implemented.
9. **Where his structure catches ours:** a value that exists only in the model's own output is rejected and
   asked for, if the harness labels it untrusted. Our exec guard's shadow builds its grant from the model's own
   line: 374 of 374 rows reachable, a moving count.
10. **A reading of his code to put to him, as a question.** If an adopter's getCandidateSlots narrows past the
    required slots ("Narrow it freely", JS 596-597), those slots stay unknown with no route (JS 1537-1540). The
    decision is then execute with them missing, unless validatePayload is wired. This was reproduced in the port and
    is NOT RUN in his JS.

Dropped after the checks: "ESP is safer on an undeclared tool" (CK1.4). In his JS that case reaches
definition_repair through a crash on a null tool, not through a schema check.

What was not run: the live quorum's semantic seat (our "old" column is the deferring seats' resolve), a worse
extractor than a perfect one, and spec.ko.md, which his spec says takes precedence where the two differ.
