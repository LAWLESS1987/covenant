#!/usr/bin/env python3
"""covenant_github_judge.py -- ask a covenant judge that runs on GitHub's
machine, for the moments this PC's Ollama is not answering.

WHY (asked 2026-09-03: "route through GitHub if Ollama is failing")
  The nodes' judge, covenant_route.py and covenant_chat.py all talk to Ollama
  on 127.0.0.1:11434. When it is down (RAM, a crash, a reboot) they have
  nowhere to go. GitHub Models inference was the obvious second place and it
  was probed first: 2026-09-04 it answered HTTP 410
  "github_models_retirement_brownout". So the second place is a GitHub
  Actions runner (.github/workflows/judge.yml) that installs Ollama, pulls a
  small model, answers ONE prompt and hands it back as an artifact. The repo
  is public, so the minutes cost nothing.

WHAT LEAVES THIS PC
  The prompt (or the chat messages) and the model name, to GitHub, over the
  account whose token git already holds. That is the whole point and it is
  also the whole cost: a thing answered here does not stay here. Every caller
  says so in its log line ("place": "github-actions"). Nothing in this file
  reads a key file, a database or the trader.

HOW IT AUTHENTICATES
  GITHUB_TOKEN from the environment if set; otherwise the credential git
  itself uses for github.com (`git credential fill`), which on this PC is the
  Git Credential Manager entry for LAWLESS1987 (scopes gist, repo, workflow:
  enough to dispatch a workflow and read its artifact). The token is never
  printed or written.

LATENCY
  A hosted runner boots, installs Ollama and pulls the model before it can
  think: measured 2026-09-04 with qwen3:4b, 107 s cold and 94 s with the model
  cached (45 s of that is the runner installing Ollama); the answer itself ~19 s.
  This is a fallback for bounded questions, not a chat you sit in front of.

USE
  python covenant_github_judge.py --prompt "..." [--model qwen2.5:3b] [--json]
  python covenant_github_judge.py --prompt-file q.txt --system-file s.txt
  python covenant_github_judge.py --selftest
  from covenant_github_judge import ask, available

EXIT  0 answered   2 could not (no token, dispatch refused, run failed, timeout)
LICENCE: public domain.
"""
from __future__ import annotations

import base64
import io
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
API = "https://api.github.com"
WORKFLOW = "judge.yml"
DEFAULT_MODEL = os.environ.get("COVENANT_GITHUB_MODEL", "qwen2.5:7b")   # no thinking mode; see judge.yml
LOG = os.path.join(HERE, "ops", "judge_route.log")


def repo():
    r = os.environ.get("COVENANT_GITHUB_REPO")
    if r:
        return r
    try:
        url = subprocess.run(["git", "remote", "get-url", "origin"], cwd=HERE,
                             capture_output=True, text=True, timeout=10).stdout.strip()
        tail = url.split("github.com")[-1].lstrip(":/")
        return tail[:-4] if tail.endswith(".git") else tail
    except Exception:                                            # noqa: BLE001
        return "LAWLESS1987/covenant"


def token():
    t = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if t:
        return t
    try:
        p = subprocess.run(["git", "credential", "fill"], input="protocol=https\nhost=github.com\n",
                           capture_output=True, text=True, timeout=20)
        for line in p.stdout.splitlines():
            if line.startswith("password="):
                return line[9:].strip()
    except Exception:                                            # noqa: BLE001
        pass
    return ""


def available():
    """True when there is a token and GitHub answers for the repo."""
    t = token()
    if not t:
        return False
    try:
        _get("/repos/%s/actions/workflows/%s" % (repo(), WORKFLOW), t)
        return True
    except Exception:                                            # noqa: BLE001
        return False


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _req(path, tok, data=None, method=None, timeout=30):
    req = urllib.request.Request(API + path if path.startswith("/") else path,
                                 data=json.dumps(data).encode() if data is not None else None,
                                 headers={"Authorization": "Bearer " + tok, "Accept": "application/vnd.github+json",
                                          "X-GitHub-Api-Version": "2022-11-28", "Content-Type": "application/json",
                                          "User-Agent": "covenant-github-judge"},
                                 method=method or ("POST" if data is not None else "GET"))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            return r.status, (json.loads(raw.decode("utf-8", "replace")) if raw.strip() else {})
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:300]
        raise RuntimeError("GitHub answered HTTP %d on %s: %s" % (e.code, path.split("?")[0], body)) from None


def _get(path, tok):
    return _req(path, tok)[1]


def dispatch(tok, tag, model, prompt, system="", json_only=False, ref="main"):
    inputs = {"tag": tag, "model": model,
              "prompt_b64": base64.b64encode(prompt.encode("utf-8")).decode(),
              "system_b64": base64.b64encode(system.encode("utf-8")).decode(),
              "json_only": "true" if json_only else "false"}   # the API wants strings, even for a boolean input
    total = sum(len(str(v)) for v in inputs.values())
    if total > 65000:
        raise ValueError("inputs are %d chars; GitHub caps workflow inputs at 65,535 -- shorten the prompt" % total)
    status, _ = _req("/repos/%s/actions/workflows/%s/dispatches" % (repo(), WORKFLOW), tok,
                     {"ref": ref, "inputs": inputs})
    return status


def find_run(tok, tag, wait=90):
    name = "judge %s" % tag
    t0 = time.time()
    while time.time() - t0 < wait:
        runs = _get("/repos/%s/actions/runs?event=workflow_dispatch&per_page=30" % repo(), tok).get("workflow_runs", [])
        for r in runs:
            if r.get("name") == name or r.get("display_title") == name:
                return r
        time.sleep(5)
    return None


def wait_run(tok, run_id, timeout):
    t0 = time.time()
    while time.time() - t0 < timeout:
        r = _get("/repos/%s/actions/runs/%d" % (repo(), run_id), tok)
        if r.get("status") == "completed":
            return r
        time.sleep(12)
    return None


def artifact(tok, run_id, tag):
    arts = _get("/repos/%s/actions/runs/%d/artifacts" % (repo(), run_id), tok).get("artifacts", [])
    for a in arts:
        if a.get("name") == "judge-%s" % tag:
            # The download is a 302 to blob storage that rejects the GitHub
            # Authorization header, so take the Location by hand and fetch it bare.
            opener = urllib.request.build_opener(_NoRedirect)
            req = urllib.request.Request(a["archive_download_url"],
                                         headers={"Authorization": "Bearer " + tok, "User-Agent": "covenant-github-judge"})
            try:
                with opener.open(req, timeout=30) as r:
                    loc = r.headers.get("Location")
                    blob = r.read() if not loc else None
            except urllib.error.HTTPError as e:
                if e.code not in (301, 302, 303, 307, 308):
                    raise
                loc, blob = e.headers.get("Location"), None
            if loc:
                with urllib.request.urlopen(urllib.request.Request(loc, headers={"User-Agent": "covenant-github-judge"}),
                                            timeout=60) as r:
                    blob = r.read()
            with zipfile.ZipFile(io.BytesIO(blob)) as z:
                return json.loads(z.read("answer.json").decode("utf-8", "replace"))
    return None


def ask(prompt, system="", model=DEFAULT_MODEL, json_only=False, timeout=900, messages=None):
    """Send one question to the GitHub runner and wait for the answer.
    Returns {"content", "model", "place": "github-actions", "seconds", "run_url", ...}
    or raises RuntimeError with the reason. `messages` (a chat history) may be
    given instead of prompt/system."""
    tok = token()
    if not tok:
        raise RuntimeError("no GitHub token: set GITHUB_TOKEN or let git hold one for github.com")
    tag = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    text = json.dumps(messages, ensure_ascii=False) if messages else prompt
    t0 = time.time()
    status = dispatch(tok, tag, model, text, system, json_only)
    if status not in (200, 204):
        raise RuntimeError("dispatch answered HTTP %s" % status)
    run = find_run(tok, tag)
    if not run:
        raise RuntimeError("the run 'judge %s' never appeared in 90s" % tag)
    done = wait_run(tok, run["id"], timeout)
    if not done:
        raise RuntimeError("run %s did not complete in %ds: %s" % (run["id"], timeout, run.get("html_url")))
    if done.get("conclusion") != "success":
        raise RuntimeError("run %s concluded %s: %s" % (run["id"], done.get("conclusion"), done.get("html_url")))
    ans = artifact(tok, run["id"], tag)
    if not ans:
        raise RuntimeError("run %s succeeded but left no judge-%s artifact" % (run["id"], tag))
    ans["seconds"] = round(time.time() - t0, 1)
    ans["run_url"] = done.get("html_url")
    return ans


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt"); ap.add_argument("--prompt-file")
    ap.add_argument("--system", default=""); ap.add_argument("--system-file")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--json", action="store_true", help="ask for a JSON object only")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        print("covenant_github_judge selftest -- repo %s, token %s" % (repo(), "present" if token() else "MISSING"))
        if not token():
            return 2
        t0 = time.time()
        try:
            ans = ask("Reply with exactly the single word OK and nothing else.", model=a.model, timeout=a.timeout)
        except RuntimeError as e:
            print("FAIL  %s" % e); return 2
        print(json.dumps({k: v for k, v in ans.items() if k != "content"}, indent=1))
        print("answer: %r" % ans["content"][:200])
        ok = "ok" in ans["content"].lower()
        print("%s  GitHub runner answered in %.0fs (model %s)" % ("ok  " if ok else "FAIL", time.time() - t0, a.model))
        return 0 if ok else 2
    prompt = a.prompt or (open(a.prompt_file, encoding="utf-8").read() if a.prompt_file else "")
    system = a.system or (open(a.system_file, encoding="utf-8").read() if a.system_file else "")
    if not prompt:
        ap.error("--prompt or --prompt-file required")
    try:
        ans = ask(prompt, system, a.model, a.json, a.timeout)
    except (RuntimeError, ValueError, urllib.error.HTTPError) as e:
        print(json.dumps({"error": str(e)})); return 2
    print(json.dumps(ans, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
