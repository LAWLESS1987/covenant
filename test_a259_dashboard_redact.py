#!/usr/bin/env python3
"""test_a259_dashboard_redact.py -- A259: the dashboard never writes an address of his into a tracked file.

WHY. dashboard.html is tracked, and dashboard_render.py copies the watchdog's ALERT lines into it.
On 2026-10-05 one of those lines carried a peer's tailnet address ("peer_<address>_5001", from the
highway's mesh_source_split measurement); the committed copy held none, the regenerated one did, and
only the opsec pre-push guard kept it unpublished. A forgotten step -- redact before writing -- has
its tombstone at the place it is forgotten (CLAUDE.md rule 10): dashboard_render.redact(), run by
write_once() every time. These checks run that code; none greps it.

WHAT IT PINS.
  R1  a non-local IPv4 address in the rendered page is replaced (tailnet, LAN, public forms)
  R2  loopback and the wildcard survive: the page's own 127.0.0.1:<port> labels are not data loss
  R3  a known identifier given as an opsec token is replaced by its label (device names, wifi names)
  R4  write_once() -- the real path from data to file -- writes no non-local address, end to end
  M1  mutation: with redaction bypassed, the same planted alert DOES reach the file, so R4 can fail
  M2  numbers that are not addresses (versions, heights, 3-part dotted) are left alone

Uses synthetic values only (documentation ranges and made-up names); it never reads his list.
"""
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import dashboard_render as D  # noqa: E402

results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print("%s  %s%s" % ("ok  " if ok else "FAIL", label, "" if ok else "  -- " + str(detail)[:200]), flush=True)


NONLOCAL = re.compile(r"(?<![\d.])(?!127\.)(?!0\.0\.0\.0)(\d{1,3}\.){3}\d{1,3}(?![\d])")

# Synthetic addresses: the shared CGNAT range a tailnet uses, a private LAN, a documentation address.
PLANT = ('highway: mesh_source_split is present -- {"peers": {"peer_100.101.102.103_5001": "b708204ff11b", '
         '"peer_192.168.7.20_5021": "x"}, "public": "203.0.113.9"}')


def main():
    page = '<div class="port">127.0.0.1:5000</div><p>listen 0.0.0.0:5001</p><p>%s</p>' % PLANT
    out = D.redact(page, toks=[])
    check("R1 tailnet, LAN and public IPv4 addresses are replaced by <ip>",
          "100.101.102.103" not in out and "192.168.7.20" not in out and "203.0.113.9" not in out
          and out.count("<ip>") == 3, out)
    check("R2 loopback and the wildcard survive", "127.0.0.1:5000" in out and "0.0.0.0:5001" in out, out)
    out3 = D.redact("<p>device covenant-test-pc on wifi Test Net 9</p>",
                    toks=[("device-name", "covenant-test-pc"), ("wifi-name", "Test Net 9")])
    check("R3 identifiers given as opsec tokens are labelled",
          "covenant-test-pc" not in out3 and "Test Net 9" not in out3
          and "<device-name>" in out3 and "<wifi-name>" in out3, out3)
    keep = "<p>v8.40 height 65 build 0.1.774 at 2026-10-05 node 5.0 ratio 1.5</p>"
    check("M2 versions, heights, dates and 3-part dotted numbers are left alone",
          D.redact(keep, toks=[]) == keep, D.redact(keep, toks=[]))

    # End to end through write_once(), with the data and the output path redirected.
    tmp = tempfile.mkdtemp(prefix="a259_")
    real_out, real_collect, real_gather = D.OUT, D.collect, None
    data = D.demo()
    data.setdefault("watchdog", {})
    try:
        D.OUT = os.path.join(tmp, "dashboard.html")
        D.collect = lambda: (data.__setitem__("watchdog", dict(data.get("watchdog") or {}, ok=False,
                                                               alerts=[PLANT])) or data)
        argv = sys.argv[:]
        sys.argv = [argv[0]]                      # not --demo: write_once() takes collect()
        try:
            import opsec_scan as _O               # keep the end-to-end check off his private list
            real_gather = _O.gather
            _O.gather = lambda *a, **k: []
        except Exception:                         # noqa: BLE001
            pass
        D.write_once(0)
        with open(D.OUT, encoding="utf8") as fh:
            written = fh.read()
        leaked = [m.group(0) for m in NONLOCAL.finditer(written)]
        check("R4 write_once() writes no non-local address, with an alert carrying three planted in",
              not leaked and "<ip>" in written, leaked[:5])
        real_redact = D.redact
        try:
            D.redact = lambda html, toks=None: html
            D.write_once(0)
            with open(D.OUT, encoding="utf8") as fh:
                bypassed = fh.read()
        finally:
            D.redact = real_redact
        check("M1 mutation: redaction bypassed, the planted address DOES reach the file -- so R4 can fail",
              "100.101.102.103" in bypassed, "")
    finally:
        sys.argv = argv
        D.OUT, D.collect = real_out, real_collect
        if real_gather is not None:
            import opsec_scan as _O
            _O.gather = real_gather

    ok = sum(results)
    print("\nA259: %d/%d passed" % (ok, len(results)))
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
