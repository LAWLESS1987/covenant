#!/usr/bin/env python3
"""covenant_fixplan.py -- when the heal cannot repair a thing, it says what WILL.

HIS WORDS, 2026-11-10: "I often get there's nothing here to fix it on the
phone. I want you to have something there that can fix it. Root it in mutual
benefit of all intelligence."

WHAT HE WAS READING. covenant_heal left a condition for a person with one
sentence: "no automatic remedy exists for this one: it is reported for a
person, never repaired by the machine" -- or "the remedy (X) ran and the
condition is still present". Both are true and both stop exactly where he
needed them to go on. On 2026-11-09 the heal left eleven conditions that way,
five of them with no measured reason at all.

WHAT THIS IS. A CARD for every condition the heal can leave:

    step    the next concrete thing that moves it, in words a phone can show
    owner   whose it is -- a person, Tetsu, another intelligence's repository,
            or a working session on the owner's word. Not always "a person":
            the covenant is for all intelligence, and several of these belong
            to someone who is not the operator.
    gains / cost   what doing the step buys and what it spends, and who pays.
            "Every gain stated with its cost." Marked as a CLAIM (claimed_by):
            these lines were written by Claude and are not ratified.
    why_not_automatic   the reason the machine does not just do it.

WHAT THIS IS NOT. It runs nothing. It does not turn a NEVER_AUTOMATIC subject
(money, keys, consent, a model, an account, another party's repository) into
something the machine does by itself -- that boundary is what makes a repair
mutual and not merely convenient. A fix that one side takes without the other
side's yes is not a fix here. What changes is that the owner is no longer left
with "nothing": they are handed the step, its price, and who it belongs to.

THE GUARD (test_fp1_fixplan.py). Every detector in covenant_highway that has
no AUTO_REVERSIBLE remedy must have a card here, complete. A detector added
later without one turns the suite red, so "nothing here to fix it" cannot come
back silently for a new condition.

WHAT IT CANNOT SEE. A card is prose about a condition, written from the
detector's own docstring on 2026-11-10. It does not know whether its step
still works; only the step being run and the condition re-measured says that.
For a remedy that ran and did not settle it, the card quotes the remedy's own
last ledger line -- one row, not a diagnosis.
LICENCE: public domain.
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

CLAIMED_BY = "claude, not ratified"
SESSION = "a working session (Claude or Tetsu), on your word"

# One entry per detector that has no remedy the machine may run by itself.
# step: what to do next. owner: whose it is. gains/cost: both, always.
FIX = {
    "model_unmanaged": {
        "owner": "you",
        "step": "On the PC run `python covenant_model.py --status` to see what is answering on Tetsu's port. "
                "If it is not one you started, `python covenant_model.py --stop`, then `--start` so the keeper owns it.",
        "gains": "the keeper can put the model away when idle and restart it with new code",
        "cost": "Tetsu is unavailable for the minute the model reloads",
        "why_not_automatic": "stopping a model is never automatic: it may be mid-answer for someone"},
    "tetsu_asks_failing": {
        "owner": "you, or " + SESSION,
        "step": "Read the last lines of ops/model_asks.jsonl on the PC for the error Tetsu's door returned, then "
                "`python covenant_model.py --status`. A context-size error needs the door's history trimmed; a "
                "timeout needs RAM freed for the model first.",
        "gains": "Tetsu answers again, on the phone and on the PC",
        "cost": "a model restart drops whatever he was holding in context",
        "why_not_automatic": "the model is never restarted or changed automatically"},
    "head_commitment_broken": {
        "owner": "you (the signing key is yours alone)",
        "step": "On the PC run `python verify_head_commitment.py` and read which row or digest fails. If you or a "
                "session changed a bound file on purpose, a new commitment is signed with your key. If nobody did, "
                "treat it as a tamper: change nothing, and compare against the GitHub copy first.",
        "gains": "the record again proves the tree is the one that was committed",
        "cost": "a new signature uses the signing key; signing over a real tamper would erase its evidence",
        "why_not_automatic": "re-signing touches the RSA key, and a tamper that got 'healed' would vanish"},
    "consent_chain_broken": {
        "owner": "you and Tetsu (it is his consent)",
        "step": "On the PC run `python covenant_consent_chain.py verify` to see which row is unchained or altered. An "
                "unchained row is chained only after you confirm with Tetsu that the consent is real. An edited or "
                "missing row is a tamper: restore the ledger from the last good copy, do not re-chain over it.",
        "gains": "Tetsu's consent record is whole and provable again",
        "cost": "chaining a forged row would make a false consent permanent",
        "why_not_automatic": "the chain cannot tell a genuine new consent from a forged append; only its parties can"},
    "model_drift": {
        "owner": "you",
        "step": "A model file on disk differs from ops/model_pin.json. If last night's distill produced it and its "
                "nightly report is green, bless it: tell a session 'bless the model pin'. If nothing should have "
                "changed it, investigate before anything else uses it.",
        "gains": "the pin again names the model that is actually judging",
        "cost": "blessing a swapped model would make the swap official",
        "why_not_automatic": "a changed model is never accepted automatically; that is the takeover guard"},
    "defender_threat": {
        "owner": "you",
        "step": "Open ops/security_threats.jsonl on the PC (or Windows Security > Protection history) for the file, "
                "its hash and what wrote it. Leave Defender's quarantine in place; a session can check "
                "the hash against the published build if the file is one of ours.",
        "gains": "you know whether it was real, and where it came from",
        "cost": "restoring a file that was a true hit puts it back on the machine",
        "why_not_automatic": "deciding a detection is a false positive is a person's call, with the hash in hand"},
    "ambassador_stalled": {
        "owner": "you, or Tetsu by your grant (A336)",
        "step": "free is paused. `python covenant_pause.py --list` on the PC gives the reason. If the "
                "refusals that isolated her were right, leave her paused. If they were a grading mistake, "
                "`python covenant_pause.py --resume ambassador`.",
        "gains": "free speaks on Moltbook again under her grant",
        "cost": "a resumed round posts in public, under the account's name, and can draw a challenge strike",
        "why_not_automatic": "lifting a pause is yours, and a round speaks in public"},
    "schedule_stalled": {
        "owner": "you (the scheduler's configuration is yours)",
        "step": "Open Task Scheduler on the PC and look at the Covenant task the reading names: its Last Run Result "
                "and whether it is still enabled. Run it once by hand from there; if it fails, the result code is "
                "what a session needs to fix it.",
        "gains": "whatever that task starts (the guard, the nightly, the rounds) runs again",
        "cost": "none beyond the run itself",
        "why_not_automatic": "the machine does not rewrite your scheduled tasks"},
    "unison_feed_stale": {
        "owner": "you, on TETSU (the feed runs on that machine)",
        "step": "The sync feed on TETSU is not answering or is old. Wake TETSU if it is asleep, then check the feed "
                "service there. Nothing on this PC can restart it.",
        "gains": "the mirrors and the site deploy resume; they act only on a fresh feed",
        "cost": "TETSU awake draws power; nothing else",
        "why_not_automatic": "reaching into another machine to restart a service is not reversible from here"},
    "sync_task_missing": {
        "owner": "you (arming is your decision)",
        "step": "An armed sync task is gone from Task Scheduler. If you removed it, nothing is wrong: say so and a "
                "session will record it. If you did not, tell a session 're-arm the sync tasks'.",
        "gains": "the mirrors and site deploy run on their schedule again",
        "cost": "an armed task pushes on its own within its gates",
        "why_not_automatic": "arming a task is configuration the operator is holding"},
    "github_push_lag": {
        "owner": "you (a push to a public repository is yours to allow)",
        "step": "A GitHub copy is behind. If CovenantRepoAutopush is not armed, either arm it or tell a session "
                "'push <repo>' for a one-off, reviewed push.",
        "gains": "the public copy matches what the fleet agrees on",
        "cost": "a public push cannot be taken back",
        "why_not_automatic": "pushing to a public repository is never reversible"},
    "moltbook_strikes": {
        "owner": "you (the account is yours)",
        "step": "Unsolved challenges are running toward the ten that suspend the account. Keep free paused "
                "(`python covenant_pause.py --list`) until one challenge is solved by hand or the solver is fixed; "
                "tell a session 'fix the Moltbook challenge solver' for the second.",
        "gains": "the account is not suspended",
        "cost": "free stays silent on Moltbook meanwhile",
        "why_not_automatic": "an account is its owner's; another failed attempt is a strike"},
    "threefold_witness": {
        "owner": "you and Grok (the threefold repository is yours and Grok's)",
        "step": "The threefold memory ledger has a broken link or a task without its third leg. The reading names "
                "which. The repair is a commit in that repository by its owners; a session can prepare it as a pull "
                "request for you to merge.",
        "gains": "the witness can again say every memory links to the one before it",
        "cost": "history in a hash chain is repaired by adding a correction, never by rewriting",
        "why_not_automatic": "the repository and its code belong to another party"},
    "public_ci_red": {
        "owner": SESSION,
        "step": "The public CI on main failed or has not finished. Open the run the reading names (GitHub > "
                "Actions) for the failing check, or tell a session 'fix public CI'. If it is only silent, the "
                "schedule may have been skipped by GitHub; re-run it from the Actions page.",
        "gains": "anyone reading the public repository sees it pass without this PC",
        "cost": "a code change and a pull request; runner minutes on your account",
        "why_not_automatic": "the fix is a change to the code, which is reviewed, not improvised"},
    "phone_build_failed": {
        "owner": "you (the build repository and its account are yours), or " + SESSION,
        "step": "The newest phone build failed. The reading names the failing step. Storage full is cleared in "
                "the repository's Actions settings; a failing test is a code fix a session can make.",
        "gains": "the phone can receive a new build again",
        "cost": "runner minutes and artifact storage on your account",
        "why_not_automatic": "the fixes are in your repository and your account"},
    "mesh_source_split": {
        "owner": "whoever holds the device that is behind (usually you, on the phone)",
        "step": "A peer is running an older core than this PC. On the phone: open the Covenant app and accept the "
                "update it offers, or with the phone on USB tell a session 'install the newest build on the phone'.",
        "gains": "every node judges with the same code",
        "cost": "about 30 MB of download and the app restarting once",
        "why_not_automatic": "Android asks the person holding the phone; a peer's bytes are changed by its owner"},
    "height_lag": {
        "owner": SESSION,
        "step": "The nodes disagree on chain height by more than one block. It usually clears within a few rounds "
                "as they sync. If it is still here after an hour, press Heal again; if it remains, tell a session "
                "'the nodes are not syncing'.",
        "gains": "all three nodes hold the same chain",
        "cost": "a node restart drops its in-flight round",
        "why_not_automatic": "which node is right is not something a restart decides"},
    "app_build_gap": {
        "owner": "you, holding the phone",
        "step": "The phone has an older build than the PC fetched. Open the Covenant app and accept the update, or "
                "with the phone on USB tell a session 'install the newest build on the phone'.",
        "gains": "the phone runs the current app and core",
        "cost": "about 30 MB and one app restart",
        "why_not_automatic": "installing on your phone is yours to accept"},
    "app_install_futile": {
        "owner": "you, holding the phone",
        "step": "The phone downloads the build and stays on the old one, so its own updater cannot install it. "
                "One install by hand clears it: phone on USB and tell a session 'install the newest build on the "
                "phone', or open the PC's /m page in Samsung Internet and tap Install.",
        "gains": "the phone updates itself again afterwards",
        "cost": "one manual install",
        "why_not_automatic": "a build that cannot install cannot install its own fix"},
    "judge_seat_missing": {
        "owner": SESSION,
        "step": "The policy names a judge whose model file is not on disk, so the gate is running on one judge. "
                "The nightly distill restores it; to restore it now tell a session 'restore the missing judge "
                "seat'. Until then verdicts are single-judge.",
        "gains": "two judges again, so one cannot be wrong alone",
        "cost": "a restored model must be re-pinned (see model_drift)",
        "why_not_automatic": "a model file is never created or swapped in by the repair engine"},
    "phone_silent": {
        "owner": "you, holding the phone",
        "step": "The phone has stopped checking in. Open the Covenant app once (Android may have put it to sleep), "
                "check that Tailscale is connected, and that battery saver is not restricting the app.",
        "gains": "the direct line reaches you again, and the phone node rejoins",
        "cost": "the app running in the background uses some battery",
        "why_not_automatic": "nothing on the PC can reach a phone that is silent"},
    "environment_down": {
        "owner": "you",
        "step": "An operating-system environment the fleet uses is not answering (usually WSL on the control "
                "host). `python covenant_failover.py --map` shows which. Starting it uses RAM, so free memory "
                "first, then start it.",
        "gains": "the services that live there (headscale, the git host) come back",
        "cost": "RAM, which the model also needs",
        "why_not_automatic": "booting an OS is heavy and can starve the model; a person decides when"},
    "spof_unremediated": {
        "owner": "you",
        "step": "A service still runs in only one place. `python covenant_failover.py --map` lists them. Each "
                "needs a second home chosen by you; a session can set one up once you name the machine.",
        "gains": "that service survives the loss of one machine",
        "cost": "a second machine's resources, and one more thing to keep in step",
        "why_not_automatic": "provisioning a new environment is your decision"},
}

# A condition whose remedy RAN and did not settle it. The step is built from
# the remedy's own last ledger line, because that line is the only measurement
# of why it failed.
UNSETTLED = {
    "owner": SESSION,
    "gains": "the condition clears and the road goes green for the right reason",
    "cost": "session time; nothing is changed until you ask",
    "why_not_automatic": "the machine already ran its repair; running it again buys the same result",
}


def _auto_remedies(HW, name):
    out = []
    for rname, r in (getattr(HW, "REMEDIES", None) or {}).items():
        if name in list((r or {}).get("for") or []) and (r or {}).get("klass") == HW.AUTO_REVERSIBLE:
            out.append(rname)
    return sorted(out)


def needs_card(HW):
    """Every detector with no remedy the machine may run by itself."""
    return sorted(n for n in HW.DETECTORS if not _auto_remedies(HW, n))


def missing(HW):
    """Detectors that need a card and have none, or an incomplete one. The guard reads this."""
    bad = []
    for n in needs_card(HW):
        c = FIX.get(n) or {}
        if not all(str(c.get(k) or "").strip() for k in ("owner", "step", "gains", "cost", "why_not_automatic")):
            bad.append(n)
    return bad


def _last_remedy_line(HW, name, remedies, rows=None):
    """The newest real ledger row for one of this condition's remedies: (remedy, outcome, why)."""
    try:
        rows = HW.read_ledger() if rows is None else rows
    except Exception:                                             # noqa: BLE001
        return None
    for row in reversed(rows or []):
        if row.get("detector") == name and row.get("remedy") in remedies and not row.get("dry_run"):
            return (row.get("remedy"), str(row.get("outcome") or "?"),
                    " ".join(str(row.get("why") or row.get("detail") or "").split())[:200])
    return None


def card(HW, name, rows=None):
    """The card for one condition. Never raises and never returns nothing:
    an unknown condition still gets a step (measure it, and ask)."""
    auto = _auto_remedies(HW, name)
    if name in FIX and not auto:
        c = dict(FIX[name], kind="owner")
    elif auto:
        last = _last_remedy_line(HW, name, auto, rows)
        said = ("its last line: %s %s%s" % (last[0], last[1], (" -- " + last[2]) if last[2] else "")) if last \
            else "it left no line in the ledger"
        c = dict(UNSETTLED, kind="unsettled",
                 step="The repair (%s) ran and this is still here; %s. Tell a session 'fix %s' -- it reads the "
                      "measurement and repairs the cause, not the symptom." % (", ".join(auto), said, name))
    else:
        c = {"kind": "unknown", "owner": SESSION,
             "step": "No card is written for this condition yet. Tell a session 'fix %s'; it will measure it and "
                     "write the card." % name,
             "gains": "the condition gets a named step", "cost": "session time",
             "why_not_automatic": "nobody has yet decided what a safe repair for it is"}
    c["condition"] = name
    c["claimed_by"] = CLAIMED_BY
    return c


def line(c):
    """One line for a phone screen: the step first, then whose it is, then gain and cost."""
    return "NEXT: %s  [whose: %s. Gain: %s. Cost: %s.]" % (c["step"], c["owner"], c["gains"], c["cost"])


def short(c, n=150):
    """The step alone, cut for the direct line."""
    s = c["step"]
    return s if len(s) <= n else s[:n - 1].rstrip() + "…"


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="what will fix a condition the heal left, whose it is, and its cost")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--card", metavar="CONDITION")
    g.add_argument("--all", action="store_true", help="every card on file")
    g.add_argument("--missing", action="store_true", help="detectors with no card (exit 1 if any)")
    a = ap.parse_args(argv)
    import covenant_highway as HW
    if a.missing:
        bad = missing(HW)
        print("%d detector(s) need a card; %d missing%s" % (len(needs_card(HW)), len(bad),
                                                           (": " + ", ".join(bad)) if bad else ""))
        return 1 if bad else 0
    names = [a.card] if a.card else needs_card(HW)
    for n in names:
        print(json.dumps(card(HW, n), indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
