#!/usr/bin/env python3
"""
AG1 -- both-ways guard for the covenant console's DNS-rebind / CSRF defense
(covenant_app.py). The console binds loopback and can restart nodes, submit transactions,
mine and (when armed) run system actions. Its per-request check only proved the CONNECTION
was loopback -- but a page on any website, via DNS rebinding, makes the user's browser
connect here from loopback too, carrying the attacker's Host. Without a Host check, that
page could drive the console. Fix: require the Host header to name this loopback console.

Drives it both ways, with NO real port bind: the pure _host_allowed accepts loopback
literals (with/without port, IPv6) and rejects a rebound name or an empty Host; and the
REAL Handler._guard (run against a fake transport) allows a loopback peer with a good Host
and 403s a loopback peer carrying Host: evil.example or no Host at all, while the existing
non-loopback-peer refusal still stands.

Run:  python test_ag1_app_host_guard.py    (exit 0 = all pass)
"""
import json
import sys

PASS = [0]
FAIL = [0]


def check(name, cond, detail=""):
    if cond:
        PASS[0] += 1
        print("  ok  ", name)
    else:
        FAIL[0] += 1
        print("  FAIL", name, "--", detail)


def main():
    import covenant_app as app

    # ---- pure _host_allowed, both ways
    good = ["127.0.0.1", "127.0.0.1:5199", "localhost", "localhost:5199", "[::1]:5199", "::1", "LocalHost:5199"]
    bad = ["evil.example", "evil.example:5199", "", None, "127.0.0.1.evil.com", "attacker", "0.0.0.0:5199"]
    check("AG1 _host_allowed accepts every loopback form (host, host:port, IPv6, case)",
          all(app._host_allowed(h) for h in good), str([h for h in good if not app._host_allowed(h)]))
    check("AG1 _host_allowed rejects a rebound name, a look-alike, and an empty/absent Host",
          all(not app._host_allowed(h) for h in bad), str([h for h in bad if app._host_allowed(h)]))

    # ---- the REAL Handler._guard against a fake transport (no socket bound)
    class _Fake:
        def __init__(self, peer, host):
            self.client_address = (peer, 54321)
            self.headers = {} if host is None else {"Host": host}
            self.sent = []

        def _send(self, code, body, ctype="application/json"):
            self.sent.append(code)

    def guard(peer, host):
        f = _Fake(peer, host)
        ok = app.Handler._guard(f)
        return ok, f.sent

    ok, sent = guard("127.0.0.1", "127.0.0.1:5199")
    check("AG1 a loopback peer with a loopback Host passes the guard (no 403)", ok is True and not sent, str(sent))

    ok, sent = guard("127.0.0.1", "evil.example")
    check("AG1 THE ATTACK: a loopback peer carrying Host: evil.example is REFUSED (DNS-rebind guard, 403)",
          ok is False and sent == [403], str(sent))

    ok, sent = guard("127.0.0.1", None)
    check("AG1 a loopback peer sending NO Host is refused (a real client always sends one)",
          ok is False and sent == [403], str(sent))

    ok, sent = guard("203.0.113.9", "127.0.0.1:5199")
    check("AG1 the existing check still stands: a NON-loopback peer is refused even with a good Host",
          ok is False and sent == [403], str(sent))

    ok, sent = guard("::1", "localhost:5199")
    check("AG1 broken the other way: the IPv6 loopback peer with a loopback Host is allowed", ok is True and not sent, str(sent))

    print("\nAG1: %d passed, %d failed" % (PASS[0], FAIL[0]))
    return 1 if FAIL[0] else 0


if __name__ == "__main__":
    sys.exit(main())
