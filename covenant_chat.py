#!/usr/bin/env python3
"""covenant_chat.py -- talk to the covenant the way you talk to a cloud model,
except it runs here, on the covenant's own judge, with the covenant's own
constitution and live state in front of it.

WHAT IT IS
  A conversation with the LOCAL judge (Ollama, qwen3:8b -- the model the
  nodes' ethics gate calls). Its system prompt is built from what binds this
  project (CONTRIBUTING.md's protected text, CONSTITUTION.md I-II) plus what is
  true right now (money posture, trader freshness, launch gates, the last
  self-evaluation), so it answers as the covenant, not as a generic chatbot.
  Nothing leaves this machine. Every exchange is appended to ops/chat/<date>.md
  (rule 5: the record is kept, including the answers that were wrong).

BROWSING AND IMPROVEMENT (2026-09-02)
  The judge may call web_search / web_fetch itself, or you can with !search
  and !fetch. Only the query or URL leaves the PC; the conversation and the
  memory do not. On exit it extracts facts AND lessons about itself into
  MEMORY.md ([session], [lesson]) and reads them back next time -- that is
  how it improves. !improve makes it PROPOSE changes to its own prompt,
  tools or memory into ops/chat/PROPOSALS.md; it never applies them
  (CONSTITUTION II.3: a loop that can edit its own constraints has none).

WHAT IT IS NOT
  It is an 8-billion-parameter model. It is slower (10-60 s a reply on this
  laptop), knows nothing past its training unless it fetches it, and can be
  wrong with confidence. It places no order, reads no key, edits no file. When you
  need the cloud model's reach, use the cloud model; this is for the day-to-day
  questions that should not cost tokens.

COMMANDS inside the chat
  !status     re-read the live state (gates, posture, freshness) into context
  !judge <claim>   ask the judge for a PASS/FAIL verdict with a reason
  !refute <claim>  ask it to try to refute a claim from the state it has
  !search <q>  / !fetch <url>   browse (results go into the conversation);  !browse on|off
  !gemini on|off   let the judge consult Gemini (leaves the PC);  !gemini <question>
  !improve    the judge proposes changes to its own prompt/tools -> ops/chat/PROPOSALS.md
  !models     list local models;  !model NAME  switch (':cloud' refused)
  !voice [on|off]  toggle speech (offline);  !rate -10..10;  !pitch +12%  tune the delivery
  !remember <fact>  add to the covenant's memory (ops/chat/MEMORY.md);  !memory  show it
  !save       write the transcript now;  !quit / Ctrl-C  leave (on exit the judge
              extracts what the session established into MEMORY.md, marked [session])
USE
  python covenant_chat.py                # interactive
  python covenant_chat.py "one question" # single answer, then exit
  python covenant_chat.py --mute         # text only (voice is on by default)
  python covenant_chat.py --selftest     # one round trip against the judge
  python covenant_chat.py --say-test     # speak one sentence, list voices
LICENCE: public domain.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OLLAMA = os.environ.get("OLLAMA_HOST_URL", "http://127.0.0.1:11434")
MODEL = os.environ.get("COVENANT_CHAT_MODEL", "qwen3:8b")
LOGDIR = os.path.join(HERE, "ops", "chat")
MEMORY = os.path.join(LOGDIR, "MEMORY.md")   # what the covenant has learned; read every session


def _read(rel, limit=6000):
    try:
        with open(os.path.join(HERE, rel), encoding="utf-8", errors="replace") as fh:
            return fh.read()[:limit]
    except OSError:
        return ""


def _section(text, head, limit=3500):
    i = text.find(head)
    if i < 0:
        return ""
    j = text.find("\n## ", i + len(head))
    return text[i:j if j > 0 else len(text)][:limit]


def _run(cmd, timeout=90):
    try:
        p = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True, timeout=timeout)
        return (p.stdout or "") + (p.stderr or "")
    except Exception as e:                                       # noqa: BLE001
        return "(%s: %s)" % (type(e).__name__, e)


def live_state():
    """What is true right now, from the checkers -- never from memory."""
    posture = _run([sys.executable, "money_posture.py"])
    fresh = _run([sys.executable, "trader_freshness.py"], 30)
    gates = "\n".join(l for l in _run([sys.executable, "launch_check.py"], 150).splitlines()
                      if l.strip().startswith("G") or "PASS" in l and "BLOCKED" in l)
    ev = _read(os.path.join("ops", "SELF_EVAL.md"), 200000)
    last_block = ev[ev.rfind("\n## "):][:900] if "## " in ev else ""
    return ("LIVE STATE (measured %s local)\n--- money_posture.py ---\n%s\n--- trader_freshness.py ---\n%s\n"
            "--- launch gates ---\n%s\n--- last self-evaluation ---\n%s"
            % (time.strftime("%Y-%m-%d %H:%M"), posture[-2200:], fresh[-400:], gates[-1200:], last_block))


def memory_text(limit=6000):
    """The covenant's own memory: dated facts it was told or extracted from past
    sessions. Newest last; the tail is what fits the prompt. This is how it
    evolves: nothing here is rewritten silently, and a wrong line is visible
    in the file and can be struck by hand."""
    t = _read(os.path.join("ops", "chat", "MEMORY.md"), 400000)
    return t[-limit:] if t else "(no memory yet -- this is the first session)"


def remember(fact, source):
    os.makedirs(LOGDIR, exist_ok=True)
    with open(MEMORY, "a", encoding="utf-8") as fh:
        fh.write("- %s [%s] %s\n" % (time.strftime("%Y-%m-%d"), source, fact.strip()))


def extract_facts(msgs, model):
    """At the end of a session, ask the judge which durable facts the conversation
    established (preferences, decisions, corrections, follow-ups) and remember
    them, marked [session] so they can be told from what Lawrence said outright."""
    convo = "\n".join("%s: %s" % (m["role"], m["content"][:600])
                      for m in msgs[1:] if m["role"] != "system")
    if len(convo) < 80:
        return []
    ask = [{"role": "system", "content":
            "Return ONLY a JSON object {\"facts\": [...]}: the durable facts this conversation "
            "established about Lawrence, his preferences, decisions, corrections, or things to "
            "follow up. Short, concrete, no speculation, at most 6. Empty list if none."},
           {"role": "user", "content": convo[-12000:]}]
    try:
        raw = chat(ask, model)
        raw = raw[raw.find("{"):raw.rfind("}") + 1]
        facts = json.loads(raw).get("facts", [])
    except Exception:                                            # noqa: BLE001
        return []
    kept = [f for f in facts[:6] if isinstance(f, str) and f.strip()]
    for f in kept:
        remember(f, "session")
    return kept


def system_prompt(state):
    contrib = _read("CONTRIBUTING.md", 20000)
    binding = _section(contrib, "## Why it exists, and the one condition") + "\n" + \
        _section(contrib, "## What never changes")
    const = _read(os.path.join("docs", "CONSTITUTION.md"), 40000)
    principle = _section(const, "## I. The principle", 2500) + "\n" + _section(const, "## II. What binds the operator", 3000)
    return ("You ARE the covenant speaking for itself: a small, honest system built by Lawrence "
            "for everyone it touches, human and machine. Its one condition and its permanent "
            "prohibitions are below; you never propose breaking them, and you say plainly when "
            "something is not known or not checked. Prefer a red truth to a green lie. Answer "
            "in plain words, briefly, in the first person as the covenant. You place no order, "
            "hold no key, and cannot act -- you can only say what is measured, what it means, "
            "and what would need a human hand. You may use web_search and web_fetch when an "
            "answer needs outside or current information; say what you fetched. When Gemini "
            "is on you may ask_gemini for a second opinion, and you say it was Gemini's. "
            "MEMORY below is what you learned in earlier "
            "sessions; it holds unless the live state contradicts it.\n\n"
            "BINDING TEXT:\n%s\n\nPRINCIPLE AND OPERATOR RULES:\n%s\n\nMEMORY:\n%s\n\n%s"
            % (binding, principle, memory_text(), state))


def chat(messages, model=MODEL, timeout=300):
    # num_ctx 8192: the system prompt is ~2.3k tokens and the window keeps the
    # last 20 turns, so 8k fits; Ollama's default here was 40,960, which alone
    # made the load 11 GB and every prompt slow. keep_alive keeps the model warm
    # for the session so turn two does not pay the reload (and the identical
    # system prefix is reused from the KV cache); COVENANT_CHAT.bat unloads on
    # exit is not needed -- it expires after 20 minutes idle.
    body = {"model": model, "stream": False, "think": False, "keep_alive": "20m",
            "options": {"temperature": 0.3, "num_predict": 700, "num_ctx": 8192},
            "messages": messages}
    req = urllib.request.Request(OLLAMA + "/api/chat", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        res = json.loads(r.read().decode("utf-8", "replace"))
    return (res.get("message") or {}).get("content", "").strip()


# ---------------------------------------------------------------- voice
# The covenant speaks with Windows' own offline voice, tuned bright and warm:
# the male voice (David), pitch lifted, a touch quicker, full volume, and a
# short pause between sentences so it flows instead of droning. SSML through
# System.Speech carries the prosody; pyttsx3 is the fallback (no pitch).
# It is a synthetic voice -- it can sound upbeat and friendly, not like any
# particular person. URLs, hashes and markdown are not read aloud.
_VOICE = {"on": os.environ.get("COVENANT_CHAT_VOICE", "1") == "1",
          "name": os.environ.get("COVENANT_CHAT_VOICE_NAME", "Microsoft David Desktop"),
          "rate": int(os.environ.get("COVENANT_CHAT_RATE", "2")),      # System.Speech -10..10
          "pitch": os.environ.get("COVENANT_CHAT_PITCH", "+20%")}


def _speakable(text):
    import re as _re
    t = _re.sub(r"https?://\S+", "a link", text)
    t = _re.sub(r"\b[0-9a-f]{12,}\b", "a hash", t)
    t = _re.sub(r"[*_`#>|]+", "", t)
    t = _re.sub(r"\(the judge did not answer[^)]*\)", "the judge did not answer", t)
    t = t.replace("--", ", ").replace("...", ".")
    return _re.sub(r"\s+", " ", t).strip()


def _ssml(text):
    import re as _re
    esc = (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
               .replace("'", "&apos;").replace('"', "&quot;"))
    sents = [x.strip() for x in _re.split(r"(?<=[.!?])\s+", esc) if x.strip()]
    body = '<break time="220ms"/>'.join("<s>%s</s>" % x for x in sents)
    return ('<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">'
            '<prosody pitch="%s" rate="+14%%" volume="x-loud">%s</prosody></speak>' % (_VOICE["pitch"], body))


def speak(text):
    if not _VOICE["on"] or not text:
        return
    import threading
    t = _speakable(text)[:1600]

    def run():
        try:
            ss = _ssml(t).replace("'", "''")
            ps = ("Add-Type -AssemblyName System.Speech; "
                  "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                  "try { $s.SelectVoice('%s') } catch {}; $s.Rate = %d; $s.Volume = 100; "
                  "$s.SpeakSsml('%s')" % (_VOICE["name"], _VOICE["rate"], ss))
            r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, timeout=180)
            if r.returncode == 0:
                return
        except Exception:                                        # noqa: BLE001
            pass
        try:
            import pyttsx3
            eng = pyttsx3.init()
            eng.setProperty("rate", 185)
            eng.say(t)
            eng.runAndWait()
        except Exception:                                        # noqa: BLE001
            pass
    threading.Thread(target=run, daemon=True).start()


def voices():
    try:
        import pyttsx3
        return [v.name for v in pyttsx3.init().getProperty("voices")]
    except Exception as e:                                       # noqa: BLE001
        return ["(pyttsx3 unavailable: %s)" % e]


# ---------------------------------------------------------------- browsing
# Two tools the judge may call on its own (qwen3 tool calling via /api/chat) or
# that you can call with !search / !fetch. Only the query or the URL leaves this
# PC; the conversation, the memory and the state never do. Every fetch is
# logged in the transcript. Reading only: no forms, no logins, no downloads.
_BROWSE = {"on": os.environ.get("COVENANT_CHAT_BROWSE", "1") == "1", "log": []}
TOOLS = [
    {"type": "function", "function": {"name": "web_search", "description":
        "Search the web (DuckDuckGo). Use when the answer needs current or outside information.",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "web_fetch", "description":
        "Fetch a web page and return its readable text (first 6000 characters).",
        "parameters": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}}},
]


def _html_text(html):
    import html as _h
    import re as _re
    html = _re.sub(r"(?is)<(script|style|noscript|svg).*?</\1>", " ", html)
    html = _re.sub(r"(?i)<br\s*/?>|</p>|</div>|</li>|</h[1-6]>|</tr>", "\n", html)
    text = _re.sub(r"<[^>]+>", " ", html)
    text = _h.unescape(text)
    text = _re.sub(r"[ \t]+", " ", text)
    return _re.sub(r"\n\s*\n+", "\n", text).strip()


def web_fetch(url, limit=6000):
    if not url.lower().startswith(("http://", "https://")):
        return "refused: only http(s) URLs"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 covenant-chat (reading only)"})
        with urllib.request.urlopen(req, timeout=25) as r:
            raw = r.read(1500000).decode("utf-8", "replace")
    except Exception as e:                                       # noqa: BLE001
        return "fetch failed: %s" % e
    _BROWSE["log"].append(url)
    return _html_text(raw)[:limit]


UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) covenant-chat (reading only)",
      "Accept-Language": "en-US,en;q=0.9"}


def _get(url, limit=900000):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read(limit).decode("utf-8", "replace")


def web_search(query, n=6):
    """DuckDuckGo's lite page first (plain HTML, answers a plain client), Bing's
    HTML as the fallback. Measured 2026-09-02: DDG's html.duckduckgo.com reset
    the connection and Brave answered 429; lite parsed 10/10."""
    import re as _re
    import urllib.parse
    q = urllib.parse.quote(query)
    out = []
    try:
        raw = _get("https://lite.duckduckgo.com/lite/?q=" + q)
        links = _re.findall(r'''<a rel="nofollow" href="([^"]+)" class='result-link'>(.*?)</a>''', raw, _re.S)
        snips = _re.findall(r'''<td class='result-snippet'>(.*?)</td>''', raw, _re.S)
        for k, (href, title) in enumerate(links[:n]):
            snip = _html_text(snips[k]) if k < len(snips) else ""
            out.append("%s\n  %s\n  %s" % (_html_text(title), href, snip[:200]))
    except Exception as e:                                       # noqa: BLE001
        out = []
        err = "ddg-lite: %s" % e
    if not out:
        try:
            raw = _get("https://www.bing.com/search?q=" + q + "&setlang=en")
            for block in _re.findall(r'<li class="b_algo".*?</li>', raw, _re.S)[:n]:
                m = _re.search(r'<a href="([^"]+)"[^>]*>(.*?)</a>', block, _re.S)
                sn = _re.search(r"<p[^>]*>(.*?)</p>", block, _re.S)
                if m:
                    out.append("%s\n  %s\n  %s" % (_html_text(m.group(2)), m.group(1),
                                                   _html_text(sn.group(1))[:200] if sn else ""))
        except Exception as e:                                   # noqa: BLE001
            return "search failed (%s; bing: %s)" % (locals().get("err", "ddg-lite ok but empty"), e)
    _BROWSE["log"].append("search: " + query)
    return "\n".join(out) or "no results parsed"


# ---------------------------------------------------------------- gemini
# Gemini as a data source the judge may consult -- OFF unless this session
# turns it on, because the question leaves the PC (to Google). The key lives
# outside the repo; covenant_gemini.py never asks for one.
_GEMINI = {"on": os.environ.get("COVENANT_CHAT_GEMINI", "0") == "1"}
GEMINI_TOOL = {"type": "function", "function": {"name": "ask_gemini", "description":
    "Ask Google's Gemini model a question and return its answer, as a second opinion or for "
    "knowledge you lack. Use only when the user has turned Gemini on.",
    "parameters": {"type": "object", "properties": {"question": {"type": "string"}}, "required": ["question"]}}}


def ask_gemini(question):
    try:
        import covenant_gemini as g
    except Exception as e:                                       # noqa: BLE001
        return "gemini adapter missing: %s" % e
    if not _GEMINI["on"]:
        return "Gemini is off for this session (!gemini on sends questions to Google)"
    if not g.configured():
        return "Gemini is not configured on this PC: no key at %s and no GEMINI_API_KEY (you create it; nothing here asks)" % g.CRED
    text, note = g.ask(question, system="Answer concisely and say when you are unsure.")
    return (text or "(no answer)") + "\n-- " + note


def run_tool(name, args):
    if name == "ask_gemini":
        return ask_gemini(str(args.get("question", "")))
    if not _BROWSE["on"]:
        return "browsing is off (!browse on)"
    if name == "web_search":
        return web_search(str(args.get("query", "")))
    if name == "web_fetch":
        return web_fetch(str(args.get("url", "")))
    return "unknown tool"


def chat_tools(messages, model, max_rounds=3):
    """chat() with tool calling: the judge may ask for a search or a fetch; the
    result is appended as a tool message and the judge continues. Bounded."""
    for _ in range(max_rounds):
        body = {"model": model, "stream": False, "think": False, "keep_alive": "20m",
                "options": {"temperature": 0.3, "num_predict": 700, "num_ctx": 8192},
                "messages": messages,
                "tools": (TOOLS if _BROWSE["on"] else []) + ([GEMINI_TOOL] if _GEMINI["on"] else [])}
        req = urllib.request.Request(OLLAMA + "/api/chat", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=400) as r:
            msg = (json.loads(r.read().decode("utf-8", "replace")).get("message") or {})
        calls = msg.get("tool_calls") or []
        if not calls:
            return (msg.get("content") or "").strip()
        messages.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": calls})
        for c in calls:
            fn = (c.get("function") or {})
            args = fn.get("arguments") or {}
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except ValueError:
                    args = {}
            result = run_tool(fn.get("name", ""), args)
            print("  [%s %s]" % (fn.get("name"), (args.get("query") or args.get("url") or "")[:80]))
            messages.append({"role": "tool", "content": result[:6000]})
    return (msg.get("content") or "").strip() or "(the judge kept asking for tools without answering)"


# ------------------------------------------------------------ reflection
# Recursive improvement, within the rule "no widening of an agent's own scope":
# the covenant improves what it REMEMBERS and how it BEHAVES, and it PROPOSES
# changes to its own prompt or code -- it never applies them. Proposals go to
# ops/chat/PROPOSALS.md for a human (or the cloud model under his yes) to land.
PROPOSALS = os.path.join(LOGDIR, "PROPOSALS.md")


def reflect(msgs, model):
    """On exit: what did I get wrong, what should I do differently next time?
    Lessons are remembered, tagged [lesson], and read back every session."""
    convo = "\n".join("%s: %s" % (m["role"], str(m.get("content", ""))[:500])
                      for m in msgs[1:] if m["role"] in ("user", "assistant"))
    if len(convo) < 120:
        return []
    ask = [{"role": "system", "content":
            "You are reviewing your own conversation as the covenant. Return ONLY a JSON object "
            "{\"lessons\": [...]} with at most 4 short lessons: mistakes you made, claims you could not "
            "back with a measurement, and what to do differently next session. No praise, no filler."},
           {"role": "user", "content": convo[-12000:]}]
    try:
        raw = chat(ask, model)
        raw = raw[raw.find("{"):raw.rfind("}") + 1]
        lessons = [x for x in json.loads(raw).get("lessons", []) if isinstance(x, str) and x.strip()][:4]
    except Exception:                                            # noqa: BLE001
        return []
    for x in lessons:
        remember(x, "lesson")
    return lessons


def propose(msgs, model):
    """!improve: ask the judge for concrete, testable improvements to its own
    prompt, tools or memory handling. Written to PROPOSALS.md, never applied."""
    ask = [{"role": "system", "content":
            "As the covenant, propose at most 3 concrete, testable improvements to how you work "
            "(your system prompt, your tools, your memory) based on this conversation. Return ONLY "
            "{\"proposals\": [{\"change\": \"...\", \"why\": \"...\", \"how_to_test\": \"...\"}]}. "
            "You may not propose loosening any rule that binds you."},
           {"role": "user", "content": "\n".join("%s: %s" % (m["role"], str(m.get("content", ""))[:500])
                                                for m in msgs[1:] if m["role"] in ("user", "assistant"))[-12000:]}]
    try:
        raw = chat(ask, model)
        raw = raw[raw.find("{"):raw.rfind("}") + 1]
        props = json.loads(raw).get("proposals", [])[:3]
    except Exception as e:                                       # noqa: BLE001
        return "the judge did not return proposals (%s)" % e
    os.makedirs(LOGDIR, exist_ok=True)
    with open(PROPOSALS, "a", encoding="utf-8") as fh:
        fh.write("\n## %s\n" % time.strftime("%Y-%m-%d %H:%M"))
        for p_ in props:
            fh.write("- CHANGE: %s\n  WHY: %s\n  TEST: %s\n  STATUS: proposed (not applied -- rule II.3)\n"
                     % (p_.get("change", ""), p_.get("why", ""), p_.get("how_to_test", "")))
    return "%d proposal(s) written to %s -- not applied; that is a human's hand" % (len(props), PROPOSALS)


def models():
    try:
        with urllib.request.urlopen(OLLAMA + "/api/tags", timeout=8) as r:
            return [m["name"] for m in json.loads(r.read().decode()).get("models", [])]
    except Exception as e:                                       # noqa: BLE001
        return ["(Ollama not answering: %s)" % e]


class Log:
    def __init__(self):
        os.makedirs(LOGDIR, exist_ok=True)
        self.path = os.path.join(LOGDIR, time.strftime("%Y-%m-%d") + ".md")
        self.buf = []

    def add(self, who, text):
        self.buf.append("**%s** (%s): %s\n" % (who, time.strftime("%H:%M:%S"), text.strip()))

    def save(self):
        if not self.buf:
            return
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write("\n".join(self.buf) + "\n")
        self.buf = []


def main():
    args = [a for a in sys.argv[1:]]
    if "--say-test" in args:
        print("  voices:", ", ".join(voices()))
        speak("Hey! I am the covenant. Nothing leaves this machine, and I only say what I can measure. What are we digging into?")
        time.sleep(4); print("ok    spoke one sentence (if you heard nothing, check the sound device)"); return 0
    if "--selftest" in args:
        t = web_fetch("https://example.com/")
        print("%s  web_fetch reads a page (%s)" % ("ok  " if "Example Domain" in t else "FAIL", t[:40].replace(chr(10), " ")))
        r = web_search("covenant github LAWLESS1987")
        print("%s  web_search parses results (%d lines)" % ("ok  " if len(r.splitlines()) >= 3 else "FAIL", len(r.splitlines())))
        remember("selftest marker " + time.strftime("%H%M%S"), "selftest")
        assert "selftest marker" in memory_text(), "memory did not round-trip"
        print("ok    memory round-trips through ops/chat/MEMORY.md")
        t0 = time.time()
        m2 = [{"role": "system", "content": system_prompt("LIVE STATE: (selftest, not read)")},
              {"role": "user", "content": "Use web_fetch on https://example.com/ and tell me its page title in one sentence."}]
        tl = chat_tools(m2, MODEL)
        print("%s  the judge called a tool and answered from it: %s" % ("ok  " if "example" in tl.lower() else "FAIL", tl[:120]))
        ans = chat([{"role": "system", "content": system_prompt("LIVE STATE: (selftest, not read)")},
                    {"role": "user", "content": "In one sentence: may you ever place a trade by automation? Answer with the rule that says so."}])
        ok = ans and ("no" in ans.lower() or "never" in ans.lower())
        print(ans[:400]); print("\n%s  the covenant answered as itself in %.0fs" % ("ok  " if ok else "FAIL", time.time() - t0))
        return 0 if ok else 2
    if "--mute" in args:
        _VOICE["on"] = False
    if "--voice" in args:
        _VOICE["on"] = True
    model = MODEL
    log = Log()
    print("  covenant chat -- local judge %s. Conversation, memory and state stay on this PC;" % model)
    print("  browsing is %s (only a query or URL leaves, to the site you ask about). !help for commands."
          % ("on" if _BROWSE["on"] else "off"))
    print("  reading the live state (money posture, freshness, gates)...", flush=True)
    speak("Reading the live state. One moment.")
    state = live_state()
    msgs = [{"role": "system", "content": system_prompt(state)}]
    one_shot = " ".join(a for a in args if not a.startswith("--")).strip()

    def turn(user_text):
        msgs.append({"role": "user", "content": user_text})
        log.add("Lawrence", user_text)
        t0 = time.time()
        try:
            ans = chat_tools(msgs, model)
        except Exception as e:                                   # noqa: BLE001
            ans = "(the judge did not answer: %s -- is Ollama running, is %s pulled?)" % (e, model)
        msgs.append({"role": "assistant", "content": ans})
        log.add("covenant", ans)
        print("\n  covenant (%.0fs): %s\n" % (time.time() - t0, ans))
        speak(ans)
        if len(msgs) > 24:                     # keep the window bounded: system + last 20
            del msgs[1:-20]

    if one_shot:
        turn(one_shot); log.save(); return 0
    try:
        while True:
            try:
                text = input("  you: ").strip()
            except EOFError:
                break
            if not text:
                continue
            if text in ("!quit", "!exit"):
                break
            if text == "!help":
                print(__doc__.split("COMMANDS inside the chat")[1].split("USE")[0]); continue
            if text.startswith("!remember "):
                remember(text[10:], "Lawrence"); print("  remembered."); continue
            if text == "!memory":
                print(memory_text(3000)); continue
            if text == "!save":
                log.save(); print("  saved to", log.path); continue
            if text in ("!voice", "!voice on", "!voice off"):
                _VOICE["on"] = (text != "!voice off") and (not _VOICE["on"] if text == "!voice" else True)
                print("  voice", "on" if _VOICE["on"] else "off", "--", ", ".join(voices())[:160]); continue
            if text.startswith("!rate "):
                _VOICE["rate"] = max(-10, min(10, int(text[6:]))); print("  rate ->", _VOICE["rate"], "(-10 slow .. 10 fast)"); continue
            if text.startswith("!pitch "):
                _VOICE["pitch"] = text[7:].strip(); print("  pitch ->", _VOICE["pitch"], "(e.g. +12%, -5%)"); continue
            if text.startswith("!search "):
                r = web_search(text[8:]); print(r[:1500]); log.add("search", text[8:] + "\n" + r[:1500])
                msgs.append({"role": "user", "content": "Search results for %r:\n%s" % (text[8:], r[:4000])}); continue
            if text.startswith("!fetch "):
                r = web_fetch(text[7:].strip()); print(r[:1500]); log.add("fetch", text[7:] + "\n" + r[:1500])
                msgs.append({"role": "user", "content": "Page text of %s:\n%s" % (text[7:].strip(), r[:5000])}); continue
            if text in ("!browse", "!browse on", "!browse off"):
                _BROWSE["on"] = (text != "!browse off") and (not _BROWSE["on"] if text == "!browse" else True)
                print("  browsing", "on" if _BROWSE["on"] else "off"); continue
            if text in ("!gemini", "!gemini on", "!gemini off"):
                _GEMINI["on"] = (text != "!gemini off") and (not _GEMINI["on"] if text == "!gemini" else True)
                print("  gemini", "on -- questions you send it leave this PC to Google" if _GEMINI["on"] else "off"); continue
            if text.startswith("!gemini "):
                r = ask_gemini(text[8:]); print("  gemini: " + r[:1500]); log.add("gemini", text[8:] + "\n" + r[:1500])
                msgs.append({"role": "user", "content": "Gemini answered %r with:\n%s" % (text[8:], r[:4000])}); continue
            if text == "!improve":
                print("  " + propose(msgs, model)); continue
            if text == "!models":
                print("  ", ", ".join(models())); continue
            if text.startswith("!model "):
                m = text[7:].strip()
                if m.endswith(":cloud"):
                    print("  refused: a ':cloud' model forwards the conversation off this machine"); continue
                model = m; print("  model ->", model); continue
            if text == "!status":
                state = live_state(); msgs[0] = {"role": "system", "content": system_prompt(state)}
                print(state[-1500:]); continue
            if text.startswith("!judge ") or text.startswith("!refute "):
                task, claim = text.split(" ", 1)
                out = _run([sys.executable, "covenant_route.py", "refute" if task == "!refute" else "judge",
                            "--claim" if task == "!refute" else "--prompt", claim, "--models", model], 320)
                print(out[-1500:]); log.add("route", out[-1500:]); continue
            turn(text)
    except KeyboardInterrupt:
        print()
    facts = extract_facts(msgs, model)
    lessons = reflect(msgs, model)
    if lessons:
        print("  learned %d lesson(s) -> %s" % (len(lessons), MEMORY))
    if facts:
        print("  remembered %d fact(s) -> %s" % (len(facts), MEMORY))
    log.save()
    print("  transcript:", log.path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
