#!/usr/bin/env python3
"""covenant_app_update.py -- the PC keeps the newest phone-app build so the
phone can update itself from the PC (asked 2026-09-13: "set it up to auto
update").

WHY THE PC AND NOT GITHUB. The app lives in the operator's PRIVATE
repository; fetching its build needs his GitHub credential, and that
credential belongs on this PC (git already holds it), never on the phone. So
the nightly pass -- or `--fetch` -- downloads the newest green build's
artifact with that credential, keeps it under ops/app/ (gitignored), and the
node serves it to a SIGNED GET from a registered signer: /app/latest (what
build, its sha256) and /app/apk (the bytes). The phone asks on its heartbeat,
downloads when the build's sha is not its own, checks the sha256, and hands
it to Android's installer, which asks the person holding the phone before
anything is installed. Nothing installs silently; nothing is served to an
unsigned caller.

USE
  python covenant_app_update.py --fetch     # newest green build of covenant-phone -> ops/app/
  python covenant_app_update.py --show
LICENCE: public domain.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
REPO = os.environ.get("COVENANT_PHONE_REPO", "LAWLESS1987/covenant-phone")
ARTIFACT = "covenant-node-apk"
DIR = os.path.join(HERE, "ops", "app")
LATEST = os.path.join(DIR, "latest.json")
KEEP = 3


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _get_json(path, tok):
    req = urllib.request.Request("https://api.github.com" + path, headers={"Authorization": "Bearer " + tok, "Accept": "application/vnd.github+json", "User-Agent": "covenant-app-update"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def _download(url, tok):
    """An artifact archive: a 302 to blob storage that rejects the token, so follow it bare."""
    opener = urllib.request.build_opener(_NoRedirect)
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + tok, "User-Agent": "covenant-app-update"})
    try:
        return opener.open(req, timeout=60).read()
    except urllib.error.HTTPError as e:
        if e.code in (301, 302, 303, 307, 308):
            with urllib.request.urlopen(urllib.request.Request(e.headers["Location"], headers={"User-Agent": "covenant-app-update"}), timeout=300) as r:
                return r.read()
        raise


def latest():
    try:
        with open(LATEST, encoding="utf-8") as fh:
            d = json.load(fh)
        p = os.path.join(DIR, d.get("file", ""))
        if not os.path.isfile(p):
            return None
        d["path"] = p
        return d
    except (OSError, ValueError):
        return None


def latest_signed(nonce, key=None):
    """The update manifest as a document the PHONE can verify, or None when no build
    has been fetched.

    WHY THIS EXISTS (2026-09-14). The phone asked `/app/latest`, was told a sha256, then
    downloaded `/app/apk` and checked the bytes against THAT SAME SERVER'S number. So the
    hash proved the download was not corrupted and nothing else: anything that could answer
    on the PC's address -- a machine that took the IP on the LAN, a stale tailnet
    name -- could serve its own APK and its own matching hash, and the check would pass.
    What actually stopped a hostile APK was Android refusing an install whose signing
    certificate differs from the installed app's, and the key that signs these builds is
    the PUBLIC debug key in the app repository. That is one guard, and it is a guard
    anybody can pick up.

    So the manifest is signed here with the PC's daily-plan key -- the same key sealed mail
    signs with, the one the phone pins -- over the canonical JSON, echoing the nonce the
    phone sent, with an `issued` stamp. A phone that has pinned the key refuses a manifest
    that does not verify; a phone that has not pinned one keeps working and says out loud
    that it is trusting an unauthenticated manifest.

    The envelope shape and the signature are covenant_actuator_guide's, deliberately:
    the phone already has verify_doc for it, and one verified-document format on this
    channel is easier to reason about than two."""
    d = latest()
    if not d:
        return None
    doc = {"v": 1, "issued": int(time.time()), "nonce": str(nonce or "")[:64],
           "sha": str(d.get("sha", "")), "sha7": str(d.get("sha7", "")),
           "sha256": str(d.get("sha256", "")), "size": int(d.get("size") or 0),
           "built": str(d.get("built", "")),
           # `version` under the signature too (2026-09-19): the phone now
           # decides "is this build mine" by (sha, version), because a rebuild
           # of its own commit against a newer core carries the same sha and a
           # new versionName, and it used to read that as "already mine". A
           # field the phone acts on must be one the PC signed.
           "version": str(d.get("version", "") or "")}
    try:
        import covenant_actuator_guide as _ag
        return _ag.sign_doc(doc, _ag._key(key))
    except Exception as e:                                        # noqa: BLE001
        # Never a traceback to the phone, and never an unsigned document dressed as one:
        # the route turns this into a plain error and the phone keeps the build it has.
        return {"status": "error", "message": "cannot sign the update manifest: %s" % type(e).__name__}


# ---------------------------------------------------------------- witness --
REQUESTS = os.path.join(DIR, "requests.jsonl")
REQUESTS_KEEP = 2000


def note_request(route, signer="", offered="", outcome="served", detail=""):
    """Record that somebody asked the update door for something. Returns nothing.

    WHY THIS EXISTS (2026-09-18). The delivery pipeline was complete and the
    phone still sat 46.6 h behind: build 0.1.552 fetched to this PC at 07:41,
    manifest signing verified working, the phone's signed /checkin arriving
    every ten minutes -- and no way on this machine to answer the one question
    that matters, "has the phone asked?". The node keeps NO access log: grep
    for /app/latest across logs/ returns 0 for every file, and grep for
    `checkin` returns 0 as well while ops/phone_checkins.jsonl holds 615 rows.
    The check-in route is visible only because it writes its own ledger. So an
    absence in the logs was never evidence of anything, and a source comment
    written on 2026-09-16 reasoning from "zero in any log" was resting on a
    measurement that cannot see the event either way.

    Two failures are indistinguishable without this: an updater that never
    asks, and one that asks and refuses the answer. They need opposite fixes --
    the first is on the phone, the second is the signature on this PC -- so a
    detector that cannot tell them apart cannot point at either.

    Bounded by construction: the file is trimmed to the last REQUESTS_KEEP
    lines, and every field is coerced and length-capped here rather than
    trusted, because `signer` arrives from a request header.
    """
    row = {"t": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "at": round(time.time(), 1),
           "route": str(route)[:40], "signer": str(signer or "")[:64],
           "offered": str(offered or "")[:40], "outcome": str(outcome)[:40],
           "detail": str(detail or "")[:200]}
    try:
        os.makedirs(DIR, exist_ok=True)
        # DURABLE (2026-09-19, his requirement: "Must survive power loss").
        # The append was fine -- the worst a cut can do to an append is a short
        # last line, which every reader here already skips. THE TRIM WAS NOT:
        # it opened this file with "w", which TRUNCATES FIRST, so a power cut
        # in that window did not lose one row of the update door's audit trail,
        # it lost all two thousand. Rewritten through a temp file and an atomic
        # rename, so a reader sees the old ledger or the new one and never an
        # empty one.
        import durable
        durable.append_line(REQUESTS, json.dumps(row, sort_keys=True))
        with open(REQUESTS, encoding="utf-8") as fh:
            lines = fh.readlines()
        if len(lines) > REQUESTS_KEEP:
            durable.rewrite_lines(REQUESTS, lines[-REQUESTS_KEEP:])
    except Exception:                                             # noqa: BLE001
        # A witness that can break the thing it witnesses is worse than none,
        # and `except OSError` was not that promise: H2's W6 pointed this at a
        # path containing a NUL and got a ValueError straight through to the
        # caller -- which, at the route, is a 500 on the update door in place
        # of the answer the phone was waiting for. The bare except is the
        # point here, not laziness: there is no failure of a LEDGER WRITE that
        # should ever be allowed to change what the door returns.
        pass


def requests_tail(n=20, route=None):
    """The last `n` recorded asks, oldest first; [] when nothing has asked yet.

    An empty list means NOBODY HAS ASKED SINCE THIS LEDGER EXISTED -- which is
    not the same as "nobody has ever asked", and any caller reporting on it has
    to say so out loud (see detect_app_build_gap)."""
    try:
        with open(REQUESTS, encoding="utf-8") as fh:
            rows = [json.loads(l) for l in fh if l.strip()]
    except (OSError, ValueError):
        return []
    if route:
        rows = [r for r in rows if r.get("route") == route]
    return rows[-int(n):] if n else rows


# ------------------------------------------------------- futile delivery --
#
# WHAT WAS MEASURED (2026-09-18, 20:45; figures corrected 21:45, see below).
# The door had been working perfectly and achieving nothing. In
# ops/app/requests.jsonl, between 11:16:16 and 20:45:49 -- 9.5 hours -- there
# are 57 COMPLETE DELIVERIES TO SIGNER `phone` at /app/apk (unit: HTTP
# responses whose last byte was streamed, counted by the generator in the
# route, not by intent), totalling 2,574,307,896 bytes. Over the same window
# the phone's own /checkin reported `0.1.475+13b946a` on all 200 of its rows.
# Not one changed. A second, independent route agrees: `tailscale status` shows
# tx 2,873,815,540 bytes to lawrences-s25, the extra being partials, check-ins,
# headers and the four transfers below.
#
# CORRECTED, and the correction belongs here. This first read "61 deliveries,
# 2,754,957,352 bytes" -- every complete delivery in the ledger, four of which
# went to signer `pc` from an earlier session's own test, reported as the
# phone's. That is CLAUDE.md rule 4 inside the comment explaining a rule-4
# fix: a right number of the wrong thing. All signers is 60 / 2,709,794,008;
# the phone is 57 / 2,574,307,896.
#
# And it is not one bad build. The 57 deliveries were of THREE different
# builds -- ab5ea5a x42, ef44d63 x13, 15f4d48 x2 -- so nothing about the bytes
# being served explains it. The installed app is 0.1.475, built before
# 3df2173 ("The install threw SecurityException every time: commit() ran with
# the write stream open"), so its installer throws on every attempt, and the
# counter that was meant to bound the retries sat after the throw. That build
# cannot install ANY update; no newer APK reaches a phone through it.
#
# WHAT THIS DOES ABOUT IT. The PC cannot fix the installer on a running phone,
# and it has no business pretending the next 45 MB will land when the last
# three did not. So the door stops sending the bytes and says why, where a
# person can read it. This is a bound on a MEASURED futility, not a guess: it
# needs complete deliveries of THIS build to THIS signer, and a check-in from
# that same signer, TAKEN AFTER the last of them, still naming another version.
#
# WHAT IT STRUCTURALLY CANNOT SEE. It reads the door's ledger and the
# check-in ledger, and neither exists on the phone: an install that succeeded
# and then crashed back to the old version looks identical to one that never
# started. It also cannot see anything before the witness ledger began
# (2026-09-18), so a count of 0 means "none recorded here", never "none ever".
#
# WHAT IT DELIBERATELY DOES NOT TOUCH. /m/apk -- the plain-browser bootstrap
# door -- is a different route and is never gated by this. That path is the
# one remaining way a build gets onto the phone, and narrowing the capability
# without checking every consumer of it is this repository's named A21 error.
FUTILE_AFTER = 3
ALLOW_AGAIN = os.path.join(DIR, "serve_anyway.json")
CHECKINS = os.path.join(HERE, "ops", "phone_checkins.jsonl")


def _checkins(signer):
    """Every /checkin row from `signer`, oldest first; [] when unreadable."""
    try:
        with open(CHECKINS, encoding="utf-8") as fh:
            rows = [json.loads(l) for l in fh if l.strip()]
    except (OSError, ValueError):
        return []
    return [r for r in rows if str(r.get("signer") or r.get("node_id") or "") == str(signer)]


def _last_checkin(signer):
    """The newest /checkin row from `signer`, or {}. Never raises."""
    rows = _checkins(signer)
    return rows[-1] if rows else {}


def install_futility(signer="phone", d=None, after=None):
    """Has this build been delivered whole to `signer` and demonstrably not installed?

    Returns a dict, always, and never raises -- a door that 500s because its
    own bookkeeping tripped is worse than a door that oversends.

      futile          the bound is met AND the phone proved it is still on
                      another version after the last complete delivery
      complete        complete deliveries of THIS build to THIS signer
      bytes           what those deliveries actually cost
      want / have     the build's versionName and the signer's reported one,
                      COMPARED IN ONE NAMESPACE (both are versionNames; `sha7`
                      is a commit in the private app repo and is never
                      compared against a core sha -- that conflation is what
                      made "is the phone current?" unanswerable on 2026-09-16)
      why             the sentence a person reads

    `after=0` disables the bound, which is what the reset lever writes.
    """
    out = {"futile": False, "signer": str(signer), "complete": 0, "bytes": 0,
           "want": None, "have": None, "why": "", "proved": 0, "ungraded": 0, "since": 0}
    try:
        d = latest() if d is None else d
        if not d:
            out["why"] = "no build fetched yet"
            return out
        want, _core = latest_version(d)
        out["want"] = want
        sha7 = str(d.get("sha7") or "")
        bound = FUTILE_AFTER if after is None else int(after)

        # The reset lever, so this can never become a door that refuses for
        # ever with nothing a person can do about it.
        try:
            with open(ALLOW_AGAIN, encoding="utf-8") as fh:
                allow = json.load(fh)
            if str(allow.get("sha7", "")) == sha7 and float(allow.get("until", 0)) > time.time():
                out["why"] = "serve-anyway is set for %s until %s" % (
                    sha7, time.strftime("%H:%M:%S", time.localtime(float(allow["until"]))))
                return out
        except (OSError, ValueError, TypeError):
            pass

        # A BUILD IS A RUN, NOT A COMMIT -- and this counter keyed on the
        # commit, which is the same conflation is_new_build was written to end
        # (2026-09-16) reappearing one function away. Caught on 2026-09-18 at
        # 20:57 by the build that landed while this was being written: run
        # 35370202625 and run 35410624880 are BOTH `ab5ea5a`, because the
        # workflow builds one app commit against whatever the public core is at
        # the time. So 43 deliveries recorded against `ab5ea5a` would have
        # transferred wholesale onto 0.1.568 -- a brand new build refused on the
        # evidence of its predecessor, which is the one outcome this guard must
        # never produce.
        #
        # The ledger cannot be asked to tell them apart: `offered` holds sha7
        # and always has. The fetch time can. A delivery recorded BEFORE this
        # build was written to disk was necessarily a delivery of some other
        # build, whatever commit it names, so the floor does the separating and
        # needs no change to what the door writes.
        since = 0.0
        try:
            import datetime
            since = datetime.datetime.strptime(
                str(d.get("fetched", "")), "%Y-%m-%dT%H:%M:%S%z").timestamp()
        except (ValueError, TypeError):
            # No usable stamp: count nothing rather than count another build's
            # deliveries against this one. Erring toward SENDING is the safe
            # direction here -- the cost of a wrong send is 45 MB, the cost of a
            # wrong refusal is a phone that can never be updated again.
            since = time.time()
        out["since"] = since
        rows = [r for r in requests_tail(0, route="/app/apk")
                if r.get("outcome") == "sent-complete"
                and str(r.get("offered") or "") == sha7
                and str(r.get("signer") or "") == str(signer)
                and float(r.get("at") or 0) >= since]
        out["complete"] = len(rows)
        for r in rows:
            try:
                out["bytes"] += int(str(r.get("detail", "")).split(" of ")[0])
            except (ValueError, IndexError):
                pass
        if not rows or not want:
            out["why"] = ("nothing delivered whole to %s for build %s yet" % (signer, sha7)
                          if not rows else "the build on disk declares no versionName")
            return out
        ck = _last_checkin(signer)
        have = str(ck.get("app") or "")
        out["have"] = have or None
        # PREFER THE BUILD OVER THE VERSION when the phone reports one
        # (2026-09-19). versionName is not unique across builds of the same
        # core: 2068c8f and a0fd2a1 both declare "0.1.597+7ffa73b". A phone
        # that installed the first would read as "installed" for the second
        # under a versionName comparison, and the door would never offer it.
        # A phone that does not yet send `build` falls back to versionName,
        # which is all it can say -- and that fallback is exactly as wrong as
        # it was before, no worse.
        have_build = str(ck.get("build") or "").strip().lower()
        if have_build:
            out["have_build"] = have_build[:7]
            # INSTALLED MEANS SAME COMMIT *AND* SAME VERSIONNAME (2026-09-19,
            # third pass at this identity). Same commit alone is not enough: a
            # rebuild of that commit against a newer core keeps the sha and
            # changes the versionName, and calling that "installed" would let
            # the door stop offering exactly the build the phone lacks.
            if have_build[:7] == sha7[:7].lower() and have == want:
                out["why"] = "%s is on build %s (%s) -- installed" % (signer, have_build[:7], have)
                return out
            # A build is reported and it is NOT this one: that is the answer,
            # whatever the versionName says. Fall through to the round-trip
            # count without the versionName short-circuit below.
            have = have_build[:7]
        if not ck or not have:
            # NOT futile: absence of a check-in is not evidence of a failed
            # install, and treating it as such would refuse a phone we simply
            # cannot hear from.
            out["why"] = "no check-in from %s to compare against -- not calling it futile" % signer
            return out
        if have == want:
            out["why"] = "%s is on %s -- installed" % (signer, have)
            return out

        # WHAT COUNTS IS A DELIVERY THAT CAME BACK, and the first draft of this
        # counted the wrong thing twice before it counted this.
        #
        # The order inside one heartbeat is the whole subtlety. The phone does
        # /checkin, then /app/latest, then /app/apk, all inside a second -- so
        # the newest check-in is ALWAYS a moment older than the newest
        # delivery, and a rule of "checked in after the last delivery" can
        # never be satisfied by a phone behaving normally. That draft made the
        # bound permanently inert, which is the quiet way a guard becomes
        # decoration. The second draft moved the marker to the start of the
        # window, which fired -- but claimed more than it had measured: it
        # proved the FIRST copy had not landed and said it about the third.
        #
        # So each complete delivery is graded on its own, against the first
        # check-in that arrives AFTER it: that is the next heartbeat, ten
        # minutes later, and it is the only evidence there is that a
        # particular copy did not take. A delivery with no check-in after it
        # yet is not graded at all -- it has not had its chance. `proved` is
        # therefore a count of ROUND TRIPS, not of bytes sent, and the bound
        # reads: three whole copies arrived, and after each of them the phone
        # came back still on another version.
        cks = _checkins(signer)
        proved, ungraded = 0, 0
        def _still_other(c):
            """Did this check-in report a build OTHER than the one delivered?
            By `build` (app-repo commit) when the phone sends it, else by
            versionName -- because two builds can share a versionName and only
            the commit tells them apart (F13)."""
            b = str(c.get("build") or "").strip().lower()
            if b:
                # Other commit, OR same commit against another core (the
                # versionName moves exactly when the core does).
                return b[:7] != sha7[:7].lower() or str(c.get("app") or "") != want
            return str(c.get("app") or "") != want

        for r in rows:
            at = float(r.get("at") or 0)
            nxt = next((c for c in cks if float(c.get("at") or 0) > at), None)
            if nxt is None:
                ungraded += 1
            elif _still_other(nxt):
                proved += 1
        out["proved"], out["ungraded"] = proved, ungraded
        if proved < bound:
            out["why"] = ("%d of %d complete deliveries came back still on %s (%d not yet "
                          "graded) -- within the budget" % (proved, bound, have, ungraded))
            return out
        out["futile"] = True
        out["why"] = ("%s has had build %s (%s) delivered whole %d times, %.2f GB in all, and "
                      "after %d of them it checked in still on %s. The bytes arrive and the "
                      "install does not happen, so this door stops sending them. Install it by "
                      "hand: open /m on the phone's browser and tap Install -- /m/apk is not "
                      "gated by this. A newer build clears the count by itself."
                      % (signer, sha7, want, len(rows), out["bytes"] / 1e9, proved, have))
        return out
    except Exception as e:                                        # noqa: BLE001
        # The measurement failed, so it has no opinion. It must not become a
        # refusal by accident: an unreadable ledger is not evidence of futility.
        out["why"] = "could not be measured: %s: %s" % (type(e).__name__, e)
        return out


def serve_anyway(hours=2.0, d=None):
    """Clear the futility bound for the current build for `hours`. Returns the marker."""
    d = latest() if d is None else d
    if not d:
        return None
    mark = {"sha7": str(d.get("sha7") or ""), "until": time.time() + float(hours) * 3600.0,
            "set": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    os.makedirs(DIR, exist_ok=True)
    import durable
    durable.write_json(ALLOW_AGAIN, mark, indent=1)
    return mark


VERSION_RE = None


def apk_version(path):
    """The versionName the APK declares, e.g. "0.1.475+13b946a", or None.

    WHY THIS HAD TO EXIST (2026-09-16). The PC compared the build's identity --
    `sha7`, the head commit of the PRIVATE app repo -- against what the phone
    reports, which is its versionName carrying the PUBLIC core sha. Two
    namespaces that never intersect: `c0de384` is not a commit in this
    repository at all. So "is the phone on the newest build" could never answer
    yes, not one second after a perfect install, and it alerted through a
    successful update. Read the identity out of the artifact instead of
    inferring it from the run that made it.

    AndroidManifest.xml in an APK is binary XML with a UTF-16LE string pool, so
    the version is found by decoding and matching, not by parsing -- which is
    enough for one well-known string and adds no dependency.
    """
    global VERSION_RE
    import re
    import zipfile
    if VERSION_RE is None:
        VERSION_RE = re.compile(r"\d+\.\d+\.\d+\+[0-9a-f]{7,40}")
    try:
        with zipfile.ZipFile(path) as z:
            raw = z.read("AndroidManifest.xml")
    except (OSError, KeyError, zipfile.BadZipFile):
        return None
    for enc in ("utf-16-le", "utf-8"):
        m = VERSION_RE.search(raw.decode(enc, "ignore"))
        if m:
            return m.group(0)
    return None


def latest_version(d=None):
    """(version, core_sha) of the build on disk -- read from the APK if the
    manifest predates `version` being recorded, and written back once."""
    d = latest() if d is None else d
    if not d:
        return None, None
    v = d.get("version")
    if not v:
        v = apk_version(d.get("path") or os.path.join(DIR, d.get("file", "")))
        if v:
            try:
                cur = dict(d)
                cur.pop("path", None)
                cur["version"] = v
                cur["core"] = v.split("+", 1)[1]
                # Atomic: truncated, latest.json makes latest() return None
                # and the door answer "no build fetched yet" -- the phone then
                # cannot update at all, from a file the PC rewrote for its own
                # bookkeeping.
                import durable
                durable.write_json(LATEST, cur, indent=1)
            except OSError:
                pass
    return v, (v.split("+", 1)[1] if v and "+" in v else None)


def is_new_build(current, run):
    """Is this workflow run a build we do not already hold?

    A BUILD IS A RUN, NOT A COMMIT (2026-09-16). This used to compare
    head_sha -- the commit in the PRIVATE app repo -- and the workflow builds
    ONE tree from TWO checkouts: that repo plus the PUBLIC core at main. So the
    same app commit, rebuilt an hour later, carries a newer core and is a
    different APK, and the old test called it "already have the newest build"
    and threw it away. Measured the same day the highway learned to ask for a
    rebuild: the dispatch succeeded, the APK existed, and the fetch refused to
    collect it. Two builds of one commit are two builds.
    """
    if not current:
        return True
    return current.get("run_id") != run.get("id")


def fetch(say=print):
    """The newest green build's APK from the private repository, kept under ops/app/.
    Returns the latest.json dict, or None with the reason said."""
    import covenant_github_judge as gh
    # A141 (2026-09-16): the A21 gate closed the credential store for the node,
    # correctly, and for this path too, which was not intended. The log shows
    # the moment -- "already have build c0de384" at 19:31, "no GitHub
    # credential on this PC" at 20:32 -- and the phone silently stopped being
    # able to receive a build. Fetching the operator's own phone build on the
    # operator's own PC is maintenance they set running, not a node reaching
    # into a stranger's keychain.
    #
    # RESIDUAL, recorded rather than hidden: REPO is a hardcoded
    # LAWLESS1987/covenant-phone (unlike covenant_github_judge.repo(), which
    # derives from `git remote get-url origin`), so on a SECOND OPERATOR's
    # machine this would spend their token against the owner's repository.
    # Deriving REPO from origin is the real fix and is a structure change --
    # see docs/KNOWN_ISSUES.md A142.
    gh.allow_credential_store("covenant_app_update.fetch -- the operator's own "
                              "phone build, on the operator's own PC")
    tok = gh.token()
    if not tok:
        say("app update: no GitHub credential on this PC"); return None
    runs = _get_json("/repos/%s/actions/runs?status=success&branch=main&per_page=5" % REPO, tok).get("workflow_runs", [])
    for run in runs:
        arts = [a for a in _get_json("/repos/%s/actions/runs/%d/artifacts" % (REPO, run["id"]), tok).get("artifacts", []) if a["name"] == ARTIFACT and not a.get("expired")]
        if not arts:
            continue
        sha7 = run["head_sha"][:7]
        cur = latest()
        # A BUILD IS A RUN, NOT A COMMIT (2026-09-16). This compared
        # head_sha -- the commit in the PRIVATE app repo -- and the workflow
        # builds ONE tree from TWO checkouts: that repo plus the PUBLIC core at
        # main. So the same app commit, rebuilt an hour later, produces a
        # different APK carrying a newer core, and this test called it "already
        # have the newest build" and threw it away. Measured the same day the
        # highway learned to ask for a rebuild: the dispatch succeeded, the APK
        # existed, and the fetch refused to collect it. Two builds of one commit
        # are two builds.
        if not is_new_build(cur, run):
            say("app update: already have build %s from run %d" % (sha7, run["id"])); return cur
        blob = _download(arts[0]["archive_download_url"], tok)
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            apk = z.read("covenant-node.apk")
        os.makedirs(DIR, exist_ok=True)
        # The name carries the run as well, for the same reason.
        fname = "covenant-node-%s-r%d.apk" % (sha7, run["id"])
        with open(os.path.join(DIR, fname), "wb") as fh:
            fh.write(apk)
        ver = apk_version(os.path.join(DIR, fname))
        d = {"sha": run["head_sha"], "sha7": sha7, "run_id": run["id"], "run_url": run["html_url"], "built": run["updated_at"],
             "version": ver, "core": (ver.split("+", 1)[1] if ver and "+" in ver else None),
             "fetched": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "file": fname, "size": len(apk), "sha256": hashlib.sha256(apk).hexdigest()}
        tmp = LATEST + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(d, fh, indent=1)
        os.replace(tmp, LATEST)
        for old in sorted((f for f in os.listdir(DIR) if f.startswith("covenant-node-") and f.endswith(".apk")), key=lambda f: os.path.getmtime(os.path.join(DIR, f)))[:-KEEP]:
            os.remove(os.path.join(DIR, old))
        say("app update: fetched build %s (%d bytes, sha256 %s)" % (sha7, len(apk), d["sha256"][:12]))
        return d
    say("app update: no green build with an artifact in the last five runs"); return None


def main():
    import argparse
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--fetch", action="store_true")
    g.add_argument("--show", action="store_true")
    g.add_argument("--futility", action="store_true",
                   help="has the current build been delivered whole and not installed?")
    g.add_argument("--serve-anyway", type=float, metavar="HOURS", nargs="?", const=2.0,
                   help="clear the futility bound for this build for HOURS (default 2)")
    a = ap.parse_args()
    if a.fetch:
        return 0 if fetch() else 2
    if a.futility:
        f = install_futility()
        print(json.dumps(f, indent=1))
        return 1 if f.get("futile") else 0
    if a.serve_anyway is not None:
        m = serve_anyway(a.serve_anyway)
        print(json.dumps(m, indent=1) if m else "no build fetched yet")
        return 0 if m else 2
    d = latest()
    print(json.dumps({k: v for k, v in d.items()} if d else {"latest": None, "hint": "python covenant_app_update.py --fetch"}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
