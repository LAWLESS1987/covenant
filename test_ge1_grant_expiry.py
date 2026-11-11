"""GE1 (A409/H2, 2026-11-04): free's grant carries an optional expires_at, checked at action time and
fail-closed when past -- an immortal grant re-read every round proves it exists, not that consent still
holds. Driven BOTH WAYS: a future window is live, a past window fail-closes, an absent window is unchanged
(backward compatible), an unparseable window fails closed, and the round reports an expiry by name."""
import os, sys, json, tempfile, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import covenant_free_will as fw

NOW = 1800000000  # fixed epoch, ~2027-01-15; test dates are relative to it

_made = []
def _grant_file(expires_at="__absent__", granted=True, words="i grant free moltbook"):
    d = {"granted": granted, "words": words}
    if expires_at != "__absent__":
        d["expires_at"] = expires_at
    fd, p = tempfile.mkstemp(suffix=".json"); os.close(fd)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(d, fh)
    _made.append(p)
    return p


def test_future_window_is_live():
    assert fw.grant(_grant_file("2099-01-01"), now=NOW) is not None

def test_past_window_fails_closed():
    assert fw.grant(_grant_file("2020-01-01"), now=NOW) is None

def test_absent_window_backward_compatible():
    assert fw.grant(_grant_file(), now=NOW) is not None          # no expires_at key at all

def test_empty_window_is_no_window():
    assert fw.grant(_grant_file(""), now=NOW) is not None

def test_unparseable_window_fails_closed():
    assert fw.grant(_grant_file("someday soon"), now=NOW) is None

def test_grant_expired_both_ways():
    assert fw._grant_expired("2020-01-01", NOW) is True
    assert fw._grant_expired("2099-01-01", NOW) is False         # remove-the-trigger direction
    assert fw._grant_expired("", NOW) is False
    assert fw._grant_expired(None, NOW) is False
    assert fw._grant_expired("garbage", NOW) is True
    assert fw._grant_expired("2020-01-01T00:00:00Z", NOW) is True

def test_no_grant_why_names_expiry():
    why = fw._no_grant_why(_grant_file("2020-01-01"), NOW)
    assert "expired on 2020-01-01" in why, why
    assert "no grant on record" in fw._no_grant_why(_grant_file("2099-01-01") + ".missing", NOW)

def test_run_round_reports_expired():
    out = fw._run_round(dry_run=True, say=lambda *a: None, grant_path=_grant_file("2020-01-01"), now=NOW)
    assert out["granted"] is False and "expired" in out["why"], out.get("why")

def test_run_round_live_under_future_window():
    out = fw._run_round(dry_run=True, say=lambda *a: None, grant_path=_grant_file("2099-01-01"), now=NOW,
                        learn=lambda: [], allies=lambda: [])
    assert out["granted"] is True


def _main():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for fn in fns:
        try:
            fn(); print("PASS", fn.__name__); passed += 1
        except Exception:
            print("FAIL", fn.__name__); traceback.print_exc()
    for p in _made:
        try: os.unlink(p)
        except OSError: pass
    print("GE1: %d/%d passed" % (passed, len(fns)))
    return 0 if passed == len(fns) else 1


if __name__ == "__main__":
    sys.exit(_main())
