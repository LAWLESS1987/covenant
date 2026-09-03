#!/usr/bin/env python3
"""covenant_gemini.py -- ask Gemini, as a data source the covenant can consult.

THE BOUNDARY, STATED FIRST
  Every question sent here leaves this machine and goes to Google. So this is
  OFF unless a session turns it on (!gemini on in covenant_chat.py, or a
  direct call to this file). The key lives OUTSIDE the repository, exactly as
  the exchange keys do -- %USERPROFILE%\\.gemini\\credentials with a line
  `key=...`, or the GEMINI_API_KEY environment variable -- and nothing here
  asks for it, prints it, or copies it anywhere (CONTRIBUTING: no credentials
  requested or stored). Without a key every call answers "not configured".

WHAT "TRAINING GEMINI" CAN AND CANNOT MEAN (2026-09-03)
  Gemini's weights are Google's. No one outside Google trains them -- there is
  no substrate-level access. What exists is Google's own supervised tuning
  (AI Studio / Vertex "tuned models"): you upload a JSONL of input->output
  pairs, Google trains an adapter on its servers under its terms, billed to
  your account, and you get a model name to call. covenant_align_set.py builds
  that JSONL from the covenant's texts and judged answers. The upload and the
  tuning job are a human's hand; this file only knows how to call a model.

USE
  python covenant_gemini.py "one question"
  python covenant_gemini.py --selftest        # configured? one round trip if so
  GEMINI_MODEL=gemini-2.5-flash (default) -- change if Google renames it.
LICENCE: public domain.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CRED = os.path.join(os.path.expanduser("~"), ".gemini", "credentials")
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
LOG = os.path.join(HERE, "ops", "gemini.log")


def _key():
    k = os.environ.get("GEMINI_API_KEY", "").strip()
    if k:
        return k
    try:
        with open(CRED, encoding="utf-8") as fh:
            for line in fh:
                if line.strip().startswith("key="):
                    return line.strip()[4:].strip()
    except OSError:
        pass
    return ""


def configured():
    return bool(_key())


def ask(prompt, system=None, timeout=90, max_tokens=800):
    """Returns (text, note). Never raises on network or key problems."""
    k = _key()
    if not k:
        return "", "not configured: no GEMINI_API_KEY and no %s" % CRED
    url = "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent" % MODEL
    body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.3}}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "x-goog-api-key": k})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            res = json.loads(r.read().decode("utf-8", "replace"))
        text = "".join(p.get("text", "") for c in res.get("candidates", [])[:1]
                       for p in (c.get("content") or {}).get("parts", []))
        note = "%s in %.1fs" % (MODEL, time.time() - t0)
    except Exception as e:                                       # noqa: BLE001
        text, note = "", "gemini call failed: %s" % e
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "model": MODEL,
                                 "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest()[:16],
                                 "prompt_chars": len(prompt), "answer_chars": len(text), "note": note}) + "\n")
    except OSError:
        pass
    return text.strip(), note


def main():
    args = sys.argv[1:]
    if "--help" in args or "-h" in args:
        print(__doc__); return 0
    if "--selftest" in args:
        if not configured():
            print("skip  Gemini not configured (no key at %s and no GEMINI_API_KEY) -- that is the "
                  "expected state until you create one; nothing here will ask for it" % CRED)
            return 0
        text, note = ask("Reply with the single word: ready")
        ok = "ready" in text.lower()
        print("%s  %s -> %r" % ("ok  " if ok else "FAIL", note, text[:60]))
        return 0 if ok else 2
    q = " ".join(a for a in args if not a.startswith("--")).strip()
    if not q:
        print(__doc__); return 1
    text, note = ask(q)
    print(text or "(no answer)"); print("--", note)
    return 0 if text else 2


if __name__ == "__main__":
    raise SystemExit(main())
