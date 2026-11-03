#!/usr/bin/env python3
"""test_hd1_hf_mirror_holds.py -- HD1. hf_mirror's fail-closed holds-drift guard (holds_mode).

SNAPSHOT_ONLY is hardcoded in hf_mirror.py; a hold added on TETSU only (its unison/holds.json, surfaced in the
feed's snapshot_copies) would otherwise be invisible here and hf_mirror could history-push a repo another node
has since marked HF-snapshot. holds_mode() closes that, FAIL-CLOSED. Driven both ways (every red is shown turning
green):
  HD1a  a clean feed: a normal repo is `push`; the SAME repo with snapshot_copies=['hf'] flips to `snapshot`
  HD1b  an unreachable feed REFUSES a repo that would be history-pushed; a reachable feed lets it push
  HD1c  a repo missing from a reachable feed is REFUSED (cannot confirm it is not snapshot-mode elsewhere)
  HD1d  a feed whose status != 'ok' refuses a would-be history push
  HD1e  a SNAPSHOT_ONLY repo is `snapshot` whether the feed omits it, is unreachable, or lists it (never refused)
  HD1f  main() wires holds_mode: a dry run HELDs a would-be push when the feed is unreachable, pushes when clean
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "tools"))
import hf_mirror as HM            # noqa: E402

_results = []


def check(label, cond, detail=""):
    _results.append(bool(cond))
    print(f"{'ok   ' if cond else 'FAIL '} {label}{('  -- ' + str(detail)[:300]) if detail and not cond else ''}")


NORMAL = "flinch-record"                       # not in SNAPSHOT_ONLY
ONLY = "covenant"                              # in SNAPSHOT_ONLY


def feed(repos):
    return {"status": "ok", "repos": repos}


def main():
    # Precondition the whole guard rests on.
    check("HD1 precondition: %s in SNAPSHOT_ONLY, %s is not" % (ONLY, NORMAL),
          ONLY in HM.SNAPSHOT_ONLY and NORMAL not in HM.SNAPSHOT_ONLY)

    # HD1a -- clean feed, normal repo: push; mark it hf-snapshot: flips to snapshot (both ways).
    m, why = HM.holds_mode(NORMAL, feed({NORMAL: {"snapshot_copies": []}}))
    check("HD1a normal repo on a clean feed is `push`", m == "push", (m, why))
    m, why = HM.holds_mode(NORMAL, feed({NORMAL: {"snapshot_copies": ["hf"]}}))
    check("HD1a the SAME repo marked snapshot_copies=['hf'] flips to `snapshot`", m == "snapshot", (m, why))

    # HD1b -- unreachable feed refuses a would-be history push; reachable lets it push (both ways).
    m, why = HM.holds_mode(NORMAL, None, "ConnectionError: refused")
    check("HD1b an unreachable feed REFUSES a would-be history push", m == "refuse", (m, why))
    m, why = HM.holds_mode(NORMAL, feed({NORMAL: {"snapshot_copies": []}}))
    check("HD1b ...and a reachable clean feed lets the same repo push", m == "push", (m, why))

    # HD1c -- reachable feed that omits a normal repo: refuse (can't confirm it is not snapshot elsewhere).
    m, why = HM.holds_mode(NORMAL, feed({"someone-else": {"snapshot_copies": []}}))
    check("HD1c a normal repo MISSING from a reachable feed is REFUSED", m == "refuse", (m, why))

    # HD1d -- status != ok is as untrustworthy as unreachable.
    m, why = HM.holds_mode(NORMAL, {"status": "degraded", "repos": {NORMAL: {}}}, "")
    check("HD1d a feed whose status != 'ok' refuses a would-be history push", m == "refuse", (m, why))

    # HD1e -- SNAPSHOT_ONLY repo is the safe direction in every feed state: snapshot, never refuse.
    cases = [
        ("feed omits it", HM.holds_mode(ONLY, feed({}))),
        ("feed unreachable", HM.holds_mode(ONLY, None, "ConnectionError: refused")),
        ("feed lists it hf", HM.holds_mode(ONLY, feed({ONLY: {"snapshot_copies": ["hf"]}}))),
        ("status != ok", HM.holds_mode(ONLY, {"status": "err"}, "")),
    ]
    check("HD1e a SNAPSHOT_ONLY repo is `snapshot` in every feed state, never refused",
          all(m == "snapshot" for _n, (m, _w) in cases), [(n, r) for n, r in cases])

    # HD1f -- main() actually consults holds_mode. Dry run, no network: stub the feed, the token and the repo list.
    saved = {k: getattr(HM, k) for k in ("read_feed", "list_owned_repos", "_gh_token")}
    HM._gh_token = lambda: "stub-token"
    HM.list_owned_repos = lambda token: [
        {"name": NORMAL, "full": "o/%s" % NORMAL, "private": False, "clone_url": "https://x/%s.git" % NORMAL},
        {"name": ONLY, "full": "o/%s" % ONLY, "private": False, "clone_url": "https://x/%s.git" % ONLY}]

    def run_main_capture():
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            HM.main(["--dry-run"])
        finally:
            sys.stdout = old
        return buf.getvalue()

    try:
        HM.read_feed = lambda *a, **k: (None, "ConnectionError: refused")
        out = run_main_capture()
        held = any(NORMAL in ln and "refuse" in ln for ln in out.splitlines())
        only_snap = any(ONLY in ln and "snapshot" in ln for ln in out.splitlines())
        check("HD1f main() on an unreachable feed HELDs the would-be push and keeps the snapshot repo", held and only_snap, out)

        HM.read_feed = lambda *a, **k: (feed({NORMAL: {"snapshot_copies": []}, ONLY: {"snapshot_copies": ["hf"]}}), "")
        out = run_main_capture()
        pushes = any(NORMAL in ln and "push" in ln for ln in out.splitlines())
        check("HD1f ...and on a clean feed the normal repo is `push` again", pushes, out)
    finally:
        for k, v in saved.items():
            setattr(HM, k, v)

    passed, total = sum(_results), len(_results)
    print(f"\nHD1: {passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
