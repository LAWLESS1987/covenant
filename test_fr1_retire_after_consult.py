"""FR1 (A409/H1, 2026-11-04): free retires a reply after the consult instead of rewording until the lexical
gate caves. Drives _retired_targets BOTH WAYS -- trigger present -> retired; trigger removed or below the cap
-> NOT retired -- and pins that the capability is inert until the grant turns it on."""
import os, sys, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import covenant_free_will as fw
import covenant_ambassador as _amb

RATE = _amb.RATE_HELD


def row(author, post, sent=False, seat=None, tetsu=None, why="", dry=False, kind="reply", verification=None):
    r = {"kind": kind, "author": author, "post_id": post, "sent": sent, "seat": seat,
         "tetsu": tetsu, "why": why, "dry_run": dry}
    if verification is not None:
        r["verification"] = verification
    return r


def test_sent_is_done_not_retired():
    rows = [row("a", "p1", why="refused"), row("a", "p1", sent=True)]
    assert ("a", "p1") not in fw._retired_targets(rows, n_cap=3)


def test_seat_block_retires_both_ways():
    assert ("b", "p1") in fw._retired_targets([row("b", "p1", seat="BLOCK")], n_cap=3)
    # remove the BLOCK -> one plain refusal, below the cap -> NOT retired
    assert ("b", "p1") not in fw._retired_targets([row("b", "p1", seat=None)], n_cap=3)


def test_tetsu_refuse_or_pause_retires():
    assert ("c", "p") in fw._retired_targets([row("c", "p", tetsu="REFUSE")], n_cap=3)
    assert ("c", "p") in fw._retired_targets([row("c", "p", tetsu="PAUSE")], n_cap=3)
    # SEND is not a decline, and it's one row < cap -> NOT retired
    assert ("c", "p") not in fw._retired_targets([row("c", "p", tetsu="SEND")], n_cap=3)


def test_ncap_both_ways():
    three = [row("d", "p", why="refused") for _ in range(3)]
    assert ("d", "p") in fw._retired_targets(three, n_cap=3)
    assert ("d", "p") not in fw._retired_targets(three[:2], n_cap=3)          # 2 < 3 -> not retired
    assert ("d", "p") not in fw._retired_targets(three, n_cap=4)              # raise the cap -> not retired


def test_rate_held_and_dry_do_not_count():
    # three rows, all rate-held by Moltbook -> zero covenant-refusals -> not retired
    assert ("e", "p") not in fw._retired_targets([row("e", "p", why=RATE + " x") for _ in range(3)], n_cap=3)
    # two real refusals + one rate-held = 2 < cap -> not retired
    mix = [row("e2", "p", why="refused"), row("e2", "p", why="refused"), row("e2", "p", why=RATE + " x")]
    assert ("e2", "p") not in fw._retired_targets(mix, n_cap=3)
    # dry runs never count
    assert ("f", "p") not in fw._retired_targets([row("f", "p", why="refused", dry=True) for _ in range(5)], n_cap=3)


def test_inert_until_grant_turns_it_on():
    # merging this change must not alter the live loop until the grant sets retire_after_consult
    assert fw.RETIRE_AFTER_CONSULT_DEFAULT is False


def _main():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for fn in fns:
        try:
            fn(); print("PASS", fn.__name__); passed += 1
        except Exception:
            print("FAIL", fn.__name__); traceback.print_exc()
    print("FR1: %d/%d passed" % (passed, len(fns)))
    return 0 if passed == len(fns) else 1


if __name__ == "__main__":
    sys.exit(_main())
