#!/usr/bin/env python3
"""
covenant_sentinels.py -- one guard pattern, three subjects, and a form that
travels to a machine this operator does not own.

ASKED 2026-09-07: "clone our watch dog to guard this alone. another for the
memory then unify across systems, prepare for seamless propagation."

WHY NOT LITERALLY CLONE THE WATCHDOG
  covenant_watchdog.py is 56 KB of node-specific judgement -- peers, quorum,
  source drift, balances. Copying it twice would give three files that drift
  apart and two that mostly do not apply. What is worth reusing is the SHAPE:
  a small thing that runs on a schedule, states one invariant, checks it,
  says so in a log an operator reads afterwards, and never repairs what it
  cannot repair safely. That shape is `Sentinel` below. The node watchdog
  keeps its own file and is reported here rather than rewritten.

THE TWO NEW SUBJECTS, AND WHY THESE INVARIANTS

  RECORD -- docs/WHAT_WE_FOUND.md and the documents around it.
    The naive check is "has this file changed", which is useless: the file is
    meant to change. The invariant that matters comes from the document's own
    rule 7, keep the refutations. A published claim may be revised; what must
    never happen is a revision that TIDIES AWAY the record of having been
    wrong. So the sentinel guards the CORRECTION MARKERS: if a document
    carried four of them yesterday and carries three today, someone has
    removed the evidence that it was ever corrected, and that is the exact
    failure the document describes happening to vendor memory. Content change
    is reported. Marker loss is an alert.

  MEMORY -- the append-only ledgers that are this project's actual memory:
    the verdict corpus, the distillation ledger, the known-issues log, the
    nightly and self-evaluation records.
    Their invariant is that history is added to and never rewritten. A
    sentinel cannot know whether a new line is true, but it can know that the
    first N lines are the same first N lines they always were, and that the
    file has not got shorter. Truncation and silent rewriting are precisely
    what a store is for preventing, and nothing here was checking for them.

PROPAGATION
  Two kinds of fact, kept apart on purpose:
    * ops/RECORD_ANCHORS.json is TRACKED. It travels with the repository, so
      someone who clones it can run `--check` and verify the record without
      being asked to trust whoever handed it over. That is the same custody
      split SUCCESSION_ANCHORS uses: verification does not require access.
    * ~/.covenant/sentinels/*.json is LOCAL. It is this machine's memory of
      what it last saw, and it is nobody else's business.
  No absolute path is hard-coded, nothing here needs this operator's home
  directory, and a fresh clone with no anchors reports "no anchor yet" rather
  than inventing a baseline. Re-anchoring is an operator act (`--anchor`),
  never automatic: a guard that re-baselines itself when it sees a change is
  not a guard, it is a rubber stamp.

USAGE
  python covenant_sentinels.py --check          every sentinel, exit 1 on alert
  python covenant_sentinels.py --status         one line each, exit 0
  python covenant_sentinels.py --anchor         (re)write ops/RECORD_ANCHORS.json
  python covenant_sentinels.py --self-test      offline checks, touches nothing
LICENCE: public domain.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from typing import Any, Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
ANCHORS = os.path.join(HERE, "ops", "RECORD_ANCHORS.json")
STATE_DIR = os.environ.get("COVENANT_SENTINEL_STATE") or os.path.join(
    os.path.expanduser("~"), ".covenant", "sentinels")
LOGDIR = os.path.join(HERE, "logs")

# A correction marker: the form this project uses to say "this was wrong and
# here is what it said". Deliberately a pattern rather than a fixed string, so
# a document may add markers freely; only losing them is the offence.
# WIDENED 2026-09-09, AND THE GUARD WAS BLIND UNTIL THIS. The pattern was
# `^\*(?:Corrected|...)` -- exactly one leading asterisk. The corpus does not
# write them that way everywhere. Measured over the four guarded documents:
#
#     docs/WHAT_WE_FOUND.md   *Corrected 2026-09-07.      4 counted   ok
#     docs/KNOWN_ISSUES.md    *(Corrected 2026-09-09:     0 counted   MISSED
#     docs/CONSTITUTION.md    **Corrected 2026-09-09.**   0 counted   MISSED
#
# The sentinel's rule is `now["markers"] < base["markers"]`, and both anchors
# recorded 0. A count of zero cannot go below zero, so on KNOWN_ISSUES.md and
# CONSTITUTION.md -- the two documents it most exists to protect -- this guard
# could never fire, whatever anyone deleted. That is the A74 shape once more: a
# check whose mechanism cannot reach the thing its label names.
#
# At least one emphasis character is still required, so ordinary prose opening
# with "Added a field" is not a correction marker. `*(` and `**` now are.
MARKER = re.compile(r"^[*_]{1,2}\(?(?:Corrected|Added|Superseded|Retracted)\b", re.M)

GUARDED_DOCUMENTS = [
    "docs/WHAT_WE_FOUND.md",
    "docs/KNOWN_ISSUES.md",
    "MY_STRATEGY.md",
    "docs/CONSTITUTION.md",
]

# Append-only. Each is the project remembering something it must not un-remember.
GUARDED_LEDGERS = [
    "ops/verdicts.jsonl",
    "ops/DISTILL.md",
    "ops/NIGHTLY.md",
    "ops/SELF_EVAL.md",
    "docs/KNOWN_ISSUES.md",
]

PREFIX_LINES = 200          # how much of a ledger's head is anchored


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def read_bytes(rel: str) -> Optional[bytes]:
    p = os.path.join(HERE, rel)
    try:
        with open(p, "rb") as fh:
            return fh.read()
    except OSError:
        return None


def prefix_of(raw: bytes, lines: int = PREFIX_LINES) -> bytes:
    return b"\n".join(raw.split(b"\n")[:lines])


class Report:
    """One sentinel's answer. `ok` false means the invariant is broken; `notes`
    are things a reader should see even when nothing is broken."""

    def __init__(self, name: str, ok: bool, summary: str,
                 alerts: Optional[List[str]] = None,
                 notes: Optional[List[str]] = None):
        self.name, self.ok, self.summary = name, bool(ok), summary
        self.alerts = list(alerts or [])
        self.notes = list(notes or [])

    def to_dict(self) -> Dict[str, Any]:
        return {"sentinel": self.name, "ok": self.ok, "summary": self.summary,
                "alerts": self.alerts, "notes": self.notes}


class Sentinel:
    """Runs on a schedule, states one invariant, never repairs what it cannot
    repair safely. Subclasses implement check()."""
    name = "sentinel"
    invariant = "(none stated)"

    def state_path(self) -> str:
        return os.path.join(STATE_DIR, self.name + ".json")

    def load_state(self) -> Dict[str, Any]:
        try:
            with open(self.state_path(), encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError):
            return {}

    def save_state(self, d: Dict[str, Any]) -> None:
        try:
            os.makedirs(os.path.dirname(self.state_path()), exist_ok=True)
            with open(self.state_path(), "w", encoding="utf-8", newline="\n") as fh:
                json.dump(d, fh, indent=1, sort_keys=True)
        except OSError:
            pass                      # a guard that cannot save still reports

    def log(self, report: Report) -> None:
        line = "%s %-8s %s%s" % (
            time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "OK" if report.ok else "ALERT", self.name + ": ", report.summary)
        try:
            os.makedirs(LOGDIR, exist_ok=True)
            with open(os.path.join(LOGDIR, "sentinels.log"), "a",
                      encoding="utf-8", newline="\n") as fh:
                fh.write(line + "\n")
                for a in report.alerts:
                    fh.write("    ALERT " + a + "\n")
        except OSError:
            pass

    def check(self, anchors: Dict[str, Any]) -> Report:
        raise NotImplementedError


class RecordSentinel(Sentinel):
    name = "record"
    invariant = ("a published document may be revised, but it may not lose the "
                 "markers that say it was corrected")

    def __init__(self, documents: Optional[List[str]] = None):
        self.documents = list(documents if documents is not None else GUARDED_DOCUMENTS)

    def measure(self, rel: str) -> Optional[Dict[str, Any]]:
        raw = read_bytes(rel)
        if raw is None:
            return None
        text = raw.decode("utf-8", "replace")
        return {"sha256": sha256_bytes(raw), "markers": len(MARKER.findall(text)),
                "lines": text.count("\n") + 1}

    def check(self, anchors: Dict[str, Any]) -> Report:
        want = (anchors or {}).get("documents", {})
        alerts, notes, changed = [], [], 0
        for rel in self.documents:
            now = self.measure(rel)
            if now is None:
                alerts.append(f"{rel}: MISSING -- a guarded document is not there")
                continue
            base = want.get(rel)
            if not base:
                notes.append(f"{rel}: no anchor yet ({now['markers']} marker(s))")
                continue
            if now["markers"] < base["markers"]:
                alerts.append(
                    f"{rel}: correction markers went {base['markers']} -> "
                    f"{now['markers']}. A revision removed the record of having "
                    f"been wrong, which is the failure this project exists to "
                    f"prevent (rule 7: keep the refutations)")
            if now["sha256"] != base["sha256"]:
                changed += 1
                notes.append(f"{rel}: content changed since the anchor "
                             f"({base['lines']} -> {now['lines']} lines, "
                             f"{base['markers']} -> {now['markers']} markers). "
                             f"Re-anchor deliberately if this was intended.")
        ok = not alerts
        summary = ("%d document(s): %d changed, %d alert(s)"
                   % (len(self.documents), changed, len(alerts)))
        return Report(self.name, ok, summary, alerts, notes)


class MemorySentinel(Sentinel):
    name = "memory"
    invariant = ("an append-only ledger only grows, and its history is never "
                 "rewritten underneath")

    def __init__(self, ledgers: Optional[List[str]] = None):
        self.ledgers = list(ledgers if ledgers is not None else GUARDED_LEDGERS)

    def measure(self, rel: str) -> Optional[Dict[str, Any]]:
        raw = read_bytes(rel)
        if raw is None:
            return None
        return {"lines": raw.count(b"\n"),
                "prefix_sha256": sha256_bytes(prefix_of(raw)),
                "prefix_lines": PREFIX_LINES}

    def check(self, anchors: Dict[str, Any]) -> Report:
        want = (anchors or {}).get("ledgers", {})
        state = self.load_state()
        alerts, notes, grew = [], [], 0
        seen = {}
        for rel in self.ledgers:
            now = self.measure(rel)
            if now is None:
                alerts.append(f"{rel}: MISSING -- a ledger this project remembers with is gone")
                continue
            seen[rel] = now
            # The travelling anchor: history, checkable by a stranger.
            base = want.get(rel)
            if base and now["prefix_sha256"] != base["prefix_sha256"]:
                alerts.append(
                    f"{rel}: the first {PREFIX_LINES} lines no longer hash to the "
                    f"anchored value. Its history was rewritten, not appended to")
            # The local memory: this machine's own last sighting.
            last = (state.get("files") or {}).get(rel)
            if last:
                if now["lines"] < last["lines"]:
                    alerts.append(
                        f"{rel}: {last['lines']} -> {now['lines']} lines. An "
                        f"append-only ledger got shorter")
                elif now["lines"] > last["lines"]:
                    grew += 1
                if now["prefix_sha256"] != last["prefix_sha256"]:
                    alerts.append(f"{rel}: its head changed since this machine last looked")
            elif not base:
                notes.append(f"{rel}: first sighting, {now['lines']} lines")
        state["files"] = {k: v for k, v in seen.items()}
        state["at"] = int(time.time())
        self.save_state(state)
        ok = not alerts
        return Report(self.name, ok,
                      "%d ledger(s): %d grew, %d alert(s)" % (len(seen), grew, len(alerts)),
                      alerts, notes)


class NodeWatchdogSentinel(Sentinel):
    """Reports the node watchdog rather than replacing it. It is a different
    kind of subject -- a live process with its own healing logic -- and the
    unification asked for is one place to LOOK, not one implementation."""
    name = "nodes"
    invariant = "covenant_watchdog.py is alive and has written recently"
    STALE_S = 600

    def check(self, anchors: Dict[str, Any]) -> Report:
        p = os.path.join(LOGDIR, "watchdog.log")
        try:
            size = os.path.getsize(p)
            age = time.time() - os.path.getmtime(p)
        except OSError:
            return Report(self.name, False, "no watchdog log at logs/watchdog.log",
                          ["the node watchdog has never written here"])
        if age > self.STALE_S:
            return Report(self.name, False,
                          "watchdog log is %.0f s old (stale over %d s)" % (age, self.STALE_S),
                          ["the node watchdog may be dead; covenant_watchdog_guard.py "
                           "owns reviving it"])
        return Report(self.name, True, "watchdog log written %.0f s ago (%d bytes)" % (age, size))


def sentinels() -> List[Sentinel]:
    return [RecordSentinel(), MemorySentinel(), NodeWatchdogSentinel()]


def load_anchors(path: str = ANCHORS) -> Dict[str, Any]:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def write_anchors(path: str = ANCHORS, say=print) -> Dict[str, Any]:
    """An operator act. Nothing re-anchors itself: a guard that re-baselines on
    seeing a change would report every state of the world as correct."""
    rec, mem = RecordSentinel(), MemorySentinel()
    out = {"_what": ("Anchors for covenant_sentinels.py. TRACKED on purpose: they travel "
                     "with the repository so a stranger who clones it can verify the record "
                     "without trusting whoever handed it over. Rewriting them is an "
                     "operator act (`python covenant_sentinels.py --anchor`), never automatic."),
           "anchored_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "prefix_lines": PREFIX_LINES,
           "documents": {}, "ledgers": {}}
    for rel in rec.documents:
        m = rec.measure(rel)
        if m:
            out["documents"][rel] = m
    for rel in mem.ledgers:
        m = mem.measure(rel)
        if m:
            out["ledgers"][rel] = {"prefix_sha256": m["prefix_sha256"],
                                   "lines_at_anchor": m["lines"]}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
        fh.write("\n")
    say("anchored %d document(s) and %d ledger(s) -> %s"
        % (len(out["documents"]), len(out["ledgers"]), os.path.relpath(path, HERE)))
    return out


def run_all(anchors: Optional[Dict[str, Any]] = None, log: bool = True) -> List[Report]:
    a = load_anchors() if anchors is None else anchors
    out = []
    for s in sentinels():
        try:
            r = s.check(a)
        except Exception as e:                                   # noqa: BLE001
            r = Report(s.name, False, "sentinel raised %s" % type(e).__name__,
                       ["%s: %s" % (type(e).__name__, str(e)[:160])])
        if log:
            s.log(r)
        out.append(r)
    return out


def main() -> int:
    a = sys.argv[1:]
    if "--self-test" in a:
        return _self_test()
    if "--anchor" in a:
        write_anchors()
        return 0
    reports = run_all(log="--no-log" not in a)
    if "--json" in a:
        print(json.dumps([r.to_dict() for r in reports], indent=2))
    else:
        for r in reports:
            print("[%s] %-7s %s" % ("ok   " if r.ok else "ALERT", r.name, r.summary))
            for x in r.alerts:
                print("        ALERT " + x)
            if "--status" not in a:
                for n in r.notes:
                    print("        note  " + n)
    bad = [r for r in reports if not r.ok]
    if "--status" in a:
        return 0
    return 1 if bad else 0


# ------------------------------------------------------------------ self-test
def _self_test() -> int:
    import tempfile
    fails = []

    def check(cond, label):
        print(("ok    " if cond else "FAIL  ") + label)
        if not cond:
            fails.append(label)

    d = tempfile.mkdtemp()
    doc = os.path.join(d, "doc.md")
    led = os.path.join(d, "led.jsonl")

    def write(p, text):
        with open(p, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)

    global HERE
    real_here = HERE
    HERE = d
    try:
        write(doc, "# t\n\nclaim\n\n*Corrected 2026-09-07. it was wrong.*\n\n*Added later.*\n")
        write(led, "".join("row %d\n" % i for i in range(300)))
        rec, mem = RecordSentinel(["doc.md"]), MemorySentinel(["led.jsonl"])
        mem.name = "memory_selftest"
        mem.save_state({})

        anchors = {"documents": {"doc.md": rec.measure("doc.md")},
                   "ledgers": {"led.jsonl": {"prefix_sha256": mem.measure("led.jsonl")["prefix_sha256"]}}}
        check(rec.measure("doc.md")["markers"] == 2, "R1 correction markers are counted")
        check(rec.check(anchors).ok, "R2 an unchanged document passes")

        write(doc, "# t\n\nclaim revised\n\n*Corrected 2026-09-07. it was wrong.*\n\n*Added later.*\n")
        r = rec.check(anchors)
        check(r.ok and any("content changed" in n for n in r.notes),
              "R3 a revision that keeps its markers is a note, not an alert")

        write(doc, "# t\n\nclaim revised\n\n*Added later.*\n")
        r = rec.check(anchors)
        check(not r.ok and any("markers went 2 -> 1" in x for x in r.alerts),
              "R4 a revision that REMOVES a correction marker is an alert")

        write(doc, "")
        os.remove(doc)
        check(not rec.check(anchors).ok, "R5 a missing guarded document is an alert")

        mem.check(anchors)                                   # first sighting -> state
        write(led, "".join("row %d\n" % i for i in range(400)))
        check(mem.check(anchors).ok, "M1 a ledger that grows is fine")
        write(led, "".join("row %d\n" % i for i in range(50)))
        r = mem.check(anchors)
        check(not r.ok and any("got shorter" in x for x in r.alerts),
              "M2 a ledger that shrinks is an alert")
        write(led, "".join("CHANGED %d\n" % i for i in range(400)))
        r = mem.check(anchors)
        check(not r.ok and any("history was rewritten" in x for x in r.alerts),
              "M3 a rewritten head fails the travelling anchor, not just local state")
        os.remove(led)
        check(not mem.check(anchors).ok, "M4 a missing ledger is an alert")

        write(os.path.join(d, "x.md"), "hi" + chr(10))
        check(RecordSentinel(["x.md"]).check({}).ok,
              "A1 a document with no anchor reports rather than inventing a baseline")
        check(any("no anchor yet" in n for n in RecordSentinel(["x.md"]).check({}).notes),
              "A2 ...and says so in a note")
        check(not RecordSentinel(["nope.md"]).check({}).ok,
              "A3 ...but a document that is not there at all is still an alert")
    finally:
        HERE = real_here

    check(all(s.invariant != "(none stated)" for s in sentinels()),
          "U1 every sentinel states its invariant")
    check([s.name for s in sentinels()] == ["record", "memory", "nodes"],
          "U2 the three subjects are unified behind one runner")
    check(not os.path.isabs(GUARDED_DOCUMENTS[0]) and "Lawre" not in json.dumps(GUARDED_DOCUMENTS + GUARDED_LEDGERS),
          "U3 nothing guarded is named by an absolute or operator-specific path")

    # -------------------------------------------------- the real guarded corpus
    # WHY THIS SECTION EXISTS. Everything above runs against a temp fixture with
    # HERE redirected, so the suite was hermetic: it never read a guarded
    # document, and its green said nothing about the documents it guards. Two
    # mutations proved that, and both left all 15 checks passing, exit 0:
    #   (1) GUARDED_DOCUMENTS (:82) cut from four entries to one -- three
    #       quarters of the guard's subjects deleted -- because U3 inspects only
    #       GUARDED_DOCUMENTS[0] and every R*/M*/A* check hands the sentinel its
    #       own fixture list instead.
    #   (2) a `**Corrected` paragraph deleted from a real guarded document; the
    #       record sentinel reported "0 -> 0 markers, 0 alert(s)".
    # These three checks run the SHIPPED sentinel over the REAL corpus. They
    # write nothing, contact nothing, and read four small files.
    anchored = sorted((load_anchors().get("documents") or {}))

    # R6 kills mutation (1). ops/RECORD_ANCHORS.json is TRACKED and travels with
    # the repository, so it is an independent witness of who the subjects are:
    # every anchored document must still be measured by the DEFAULT sentinel and
    # must still raise the marker-loss alert when handed a baseline claiming one
    # more marker than it has now. Drop a subject from GUARDED_DOCUMENTS and its
    # alert vanishes from this report. (covenant_selfaudit.py C5 checks only the
    # other direction -- a guarded document that has no anchor.)
    # ABSENT AND UNGUARDED ARE DIFFERENT FACTS, and this check used to report
    # both as "unguarded" (2026-09-10). A document that measure() cannot read
    # was silently dropped from _louder and then named as a subject the
    # sentinel had lost -- so a STAGING bug in covenant_one.py, which copied
    # the root by extension and had no .md in the list, read for weeks as
    # "MY_STRATEGY.md is no longer guarded". The mechanism was right and the
    # diagnosis it handed a reader was wrong, which costs more than silence.
    _louder, _absent = {"documents": {}}, []
    for _rel in anchored:
        _m = RecordSentinel([_rel]).measure(_rel)
        if _m:
            _louder["documents"][_rel] = dict(_m, markers=_m["markers"] + 1)
        else:
            _absent.append(_rel)
    _alerts = RecordSentinel().check(_louder).alerts
    _unguarded = [r for r in anchored if r not in _absent
                  and not any(r in x and "correction markers went" in x for x in _alerts)]
    _why = ""
    if _absent:
        _why += (" -- ANCHORED BUT NOT IN THIS TREE (cannot be read, so cannot be "
                 "guarded here): " + ", ".join(_absent))
    if _unguarded:
        _why += " -- present but unguarded: " + ", ".join(_unguarded)
    if not anchored:
        _why = " -- no anchors at all"
    check(bool(anchored) and not _unguarded and not _absent,
          "R6 every anchored document is present, is still a subject of the shipped "
          "sentinel, and still alerts on marker loss" + _why)

    # R7 IS RETIRED, AND IT RETIRED ITSELF CORRECTLY. It was added earlier on
    # 2026-09-09 to DISCLOSE a source defect rather than repair it: MARKER
    # matched only "*Corrected", while the corpus also writes "*(Corrected"
    # (KNOWN_ISSUES.md:16) and "**Corrected" (CONSTITUTION.md:171). Those two
    # documents counted 0 markers, were anchored at 0, and `now < base` cannot
    # fire from 0 -- so the guard on the two documents it most exists to protect
    # was structurally incapable of alerting, whatever anyone deleted.
    #
    # R7 pinned that gap at its known size, and said what would turn it red:
    # "the pattern was widened and the anchors are stale". Both happened, in
    # that order and on purpose -- MARKER now accepts one or two leading
    # emphasis characters and an optional paren, `--anchor` was re-run, and both
    # files record 1 marker instead of 0.
    #
    # Keeping a check that pins a defect after the defect is gone would be a
    # test asserting the past. Its job passes to R9 below, which asks the
    # general question (is any marker in the corpus invisible to MARKER?)
    # instead of naming two files that would need editing forever.

    # R8 asserts the invariant itself over the real corpus instead of a fixture:
    # the shipped sentinel, the shipped anchors, no marker-loss alert. This is
    # the check that goes red on a genuine deletion of a COUNTED marker
    # (docs/WHAT_WE_FOUND.md carries four). Deliberately narrow -- a missing file
    # or a content change is `--check`'s business and is pinned by R5/A3 -- so
    # only the offence the invariant names can fail it.
    _live = [x for x in RecordSentinel().check(load_anchors()).alerts
             if "correction markers went" in x]
    check(not _live,
          "R8 no guarded document has lost a correction marker since the anchor"
          + ("" if not _live else " -- " + _live[0][:120]))

    # R9: NO MARKER SHAPE THE CORPUS USES MAY BE INVISIBLE TO MARKER.
    #
    # R8 above can only see markers the pattern already counts, so it was green
    # for years on two documents whose markers it could not see at all --
    # `*(Corrected` in KNOWN_ISSUES.md and `**Corrected` in CONSTITUTION.md both
    # counted 0, their anchors recorded 0, and `now < base` cannot fire from 0.
    # The guard on the two most important documents was structurally incapable
    # of alerting. Widening the pattern fixed those two; this stops the next
    # shape from doing it again.
    #
    # It compares the shipped MARKER against a deliberately loose reading of the
    # SAME real files: any line beginning with up to three non-word characters
    # and then one of the four words. Loose is allowed to over-count -- that is
    # what makes it a useful upper bound. If the two disagree, the corpus has
    # started writing a marker the sentinel cannot see, and the sentinel says so
    # rather than continuing to report zero.
    _loose = re.compile(r"^\W{0,3}(?:Corrected|Added|Superseded|Retracted)\b", re.M)
    _blind = []
    for _d in GUARDED_DOCUMENTS:
        _p = _d if os.path.isabs(_d) else os.path.join(HERE, _d)
        try:
            _t = open(_p, encoding="utf-8").read()
        except OSError:
            continue                      # a missing file is R5/A3's business
        _seen, _all = len(MARKER.findall(_t)), len(_loose.findall(_t))
        if _all > _seen:
            _blind.append("%s: %d marker(s) the pattern cannot see" % (_d, _all - _seen))
    check(not _blind,
          "R9 every correction marker in the guarded corpus is one MARKER can "
          "count -- a guard that counts zero can never report a loss"
          + ("" if not _blind else " -- " + "; ".join(_blind)[:160]))

    print()
    if fails:
        print(f"{len(fails)} FAILED")
        return 1
    print("SENTINELS: all passed (offline; no anchor written, nothing repaired)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
