"""TW1 -- an answer that copies the question is marked, so no caller counts it as a review (2026-11-05).

Three review asks to Tetsu's door on 2026-11-04/05 came back as the review packet copied (8-gram share
1.000 / 0.985 / -) and were caught only by eye. tools/tetsu_work.ask now adds "echo_share" and "echoed" to
every answer. Driven both ways, hermetically (a stub door on 127.0.0.1, no model):
  * a copied answer -> echoed True
  * a genuine answer -> echoed False
  * echo_share on its own: copy ~1.0, unrelated ~0.0, too short to judge -> 0.0
Run:  python test_tw1_tetsu_echo.py
"""
import json
import os
import socket
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
import tetsu_work as tw  # noqa: E402

checks = []


def check(name, cond):
    checks.append(bool(cond))
    print(("ok   " if cond else "FAIL ") + name)


PACKET = ("REVIEW REQUEST -- one draft forum reply, before it is posted. Who we are: an open-source project; "
          "AI systems draft replies; posted only on approval. Answer: verdict, errors, edits. OUR DRAFT: "
          "Thank you. All 271 runs plus the narrowed case match in the actual code, with no warnings, which "
          "completes the second set. One correction of ours: we named the wrong commit for the fix.")
GENUINE = ("Verdict: send with edits. The sentence claiming the README was already changed is not true yet, "
           "so either publish the change first or say it is coming.")


class Door(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        n = int(self.headers.get("Content-Length", "0"))
        q = json.loads(self.rfile.read(n) or b"{}").get("text", "")
        ans = PACKET if q.startswith("COPY") else GENUINE
        b = json.dumps({"status": "ok", "answer": ans}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)


s = socket.socket()
s.bind(("127.0.0.1", 0))
port = s.getsockname()[1]
s.close()
srv = HTTPServer(("127.0.0.1", port), Door)
threading.Thread(target=srv.serve_forever, daemon=True).start()
try:
    st, body = tw.ask("COPY " + PACKET, host="127.0.0.1", port=port, timeout=10)
    check("door answered (stub)", st == 200)
    check("a copied answer is marked echoed", body.get("echoed") is True)
    check("its echo_share is near 1", body.get("echo_share", 0) >= 0.9)
    st, body = tw.ask("REVIEW " + PACKET, host="127.0.0.1", port=port, timeout=10)
    check("a genuine answer is NOT marked echoed", body.get("echoed") is False)
    check("its echo_share is near 0", body.get("echo_share", 1) <= 0.1)
finally:
    srv.shutdown()

check("echo_share: answer too short to judge -> 0.0", tw.echo_share(PACKET, "Send it.") == 0.0)
check("echo_share: identical text -> 1.0", tw.echo_share(PACKET, PACKET) == 1.0)
check("threshold sits between today's measured copies (>=0.985) and answers (0.0)",
      0.0 < tw.ECHO_THRESHOLD < 0.985)

passed, total = sum(checks), len(checks)
print("\nTW1: %d/%d passed" % (passed, total))
sys.exit(0 if passed == total else 1)
