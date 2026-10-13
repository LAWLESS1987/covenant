#!/usr/bin/env python3
"""DK1 -- A339: the desk shows his messages in Notepad when the phone is not collecting them.

Runs covenant_desk.selftest(): every path is a temp file and Notepad is never opened (open_fn is a list).
Nothing here reads or writes his real line (ops/contact_outbox.jsonl) or opens a window on his screen.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_desk  # noqa: E402

raise SystemExit(covenant_desk.selftest())
