#!/usr/bin/env python3
"""covenant_chat.py -- talk to the covenant with its binding text, its live
state and its own memory in front of it, so it answers as the covenant rather
than as a generic assistant.

WHERE THE ANSWER IS MADE -- read this first (corrected 2026-09-11; the local
hop deleted 2026-09-12)
  Every turn goes to a judge on a GitHub Actions runner (covenant_github_judge.py;
  chat_github below). The conversation LEAVES THIS PC, base64'd into a
  workflow_dispatch input on a repository that is PUBLIC, and each answer is
  prefixed "(via GitHub runner ...)" so the transcript says where it was made.
  There is no other path: `!github off` leaves the chat with no model at all,
  and it says so instead of failing quietly.

  History, because this docstring once said the opposite. Until 2026-09-07 a
  local model server on this PC answered every turn and "Nothing leaves this
  machine" was true. The server was deleted that day; the code kept trying it
  first on every turn, caught the refused connection and fell through to the
  runner, and --help still promised locality until 2026-09-11. On 2026-09-12
  the dead first hop -- the local call, its tool-calling loop, the model list
  and switch -- was deleted rather than kept as a path that could not answer.

  What does NOT leave, since 2026-09-11: the private half of the system prompt.
  _offsite_system() cuts MEMORY and the LIVE STATE -- money posture, launch
  gates, freshness -- before the window is sent, and says in the text the judge
  receives that they were withheld, so it can tell you when it needed them. The
  conversation itself is NOT redacted, because it is the question being asked.
  Pinned behaviourally by test_a90_offsite_redaction.py.

WHAT IT IS
  Its system prompt is built from what binds this project (CONTRIBUTING.md's
  protected text, CONSTITUTION.md I-II) plus what is true right now (money
  posture, trader freshness, launch gates, the last self-evaluation). Every
  exchange is appended to ops/chat/<date>.md (rule 5: the record is kept,
  including the answers that were wrong).

BROWSING (2026-09-02; the judge's own tool calls went with the local hop, 2026-09-12)
  !search <q> and !fetch <url> put a result list or a page into the
  conversation for the judge's next turn. The judge on the runner cannot call
  them itself; tool calling was a feature of the deleted local hop. Only the
  query or the URL goes to the search engine -- and the turn that follows
  leaves the PC, as every turn does.

MEMORY AND IMPROVEMENT (corrected 2026-09-11; live again 2026-09-12)
  On exit it asks the judge for durable facts and lessons and appends them to
  MEMORY.md ([session], [lesson]), reading them back next time. From
  2026-09-07 to 2026-09-12 that call was dead: extract_facts and reflect used a
  chat() that talked only to the deleted local server, both raised, both were
  swallowed, and every session silently learned nothing. chat() now goes to
  the runner like every turn, so leaving costs two runner round trips (2-5
  minutes each); Ctrl-C skips them and says so.
  !improve makes it PROPOSE changes to its own prompt, tools or memory into
  ops/chat/PROPOSALS.md; it never applies them (CONSTITUTION II.3: a loop that
  can edit its own constraints has none).

WHAT IT IS NOT
  It is not a large model, and not a local one: the model that answers runs on
  a GitHub Actions runner. It knows
  nothing past its training unless it fetches it, and can be wrong with
  confidence. It places no order and holds no key. It DOES write files -- all
  of them under ops/chat, none of them code: <date>.md, MEMORY.md, VOICE.json
  and PROPOSALS.md. ("edits no file" stood here until 2026-09-11 and was never
  true of those four.)

COMMANDS inside the chat
  !status     re-read the live state (gates, posture, freshness) into context
  !judge <claim>   ask the judge for a PASS/FAIL verdict with a reason
  !refute <claim>  ask it to try to refute a claim from the state it has
  !search <q>  / !fetch <url>   browse (the results go into the conversation)
  !gemini on|off   allow Gemini as a second opinion (a question leaves the PC to Google);  !gemini <question>
  !improve    the judge proposes changes to its own prompt/tools -> ops/chat/PROPOSALS.md
  !voice [on|off]  toggle speech (offline);  !rate -10..10;  !pitch +12%  tune the delivery
  !voice save  keep the current delivery (ops/chat/VOICE.json);  !tune  the covenant PICKS ITS OWN
              voice, rate and pitch from what is installed, says a line in it, and keeps it
  !mic [on|off|test]  talk instead of type: with the mic on, press Enter on an empty line and
              speak; Windows' offline recogniser (System.Speech) turns it into the next message.
              Nothing is recorded and nothing leaves the PC. !mic 30 sets the listen window.
  !github [on|off]  off: nothing is sent anywhere and the chat has no model. on (the default):
              every turn goes to the judge on a GitHub Actions runner and LEAVES THIS PC; the answer says so.
  !remember <fact>  add to the covenant's memory (ops/chat/MEMORY.md);  !memory  show it
  !save       write the transcript now;  !quit / Ctrl-C  leave (on exit the judge
              extracts what the session established into MEMORY.md, marked [session])
USE
  python covenant_chat.py                # interactive
  python covenant_chat.py "one question" # single answer, then exit
  python covenant_chat.py --mute         # text only (voice is on by default)
  python covenant_chat.py --talk         # mic on from the start (Enter on an empty line = speak)
  python covenant_chat.py --selftest     # one round trip to the judge on the runner (2-5 minutes)
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
import covenant_quiet                                    # no console window on Windows (covenant_quiet.py)

HERE = os.path.dirname(os.path.abspath(__file__))
# 2026-09-12: no local model server and no local model name. The judge that
# answers is on the GitHub Actions runner; its model is named once, in
# covenant_github_judge.py (COVENANT_GITHUB_MODEL), and every answer says which.
MODEL = None   # "the runner's model": the value the functions below pass around and ignore


def _runner_model():
    import covenant_github_judge as gh
    return gh.DEFAULT_MODEL
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
        p = covenant_quiet.run(cmd, cwd=HERE, capture_output=True, text=True, timeout=timeout)
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


def memory_text(limit=7000):
    """The covenant's own memory, selected by what matters rather than by
    recency alone. MEMORY.md carries lines tagged [Lawrence] (said outright),
    [lesson] (its own mistakes), [session] (facts a session established),
    [scenario] (the standing loop's weights) and [x-video <id>] (one per
    video). A plain tail of the file was, by 2026-09-03, 105 video lines deep
    and pushed out everything he had said and everything it had learned.
    Selection: every [Lawrence] and [lesson] line (newest first, capped), the
    last 6 [session], the last 3 [scenario], the last 10 [x-video]. Nothing is
    rewritten; a wrong line is visible in the file and can be struck by hand."""
    t = _read(os.path.join("ops", "chat", "MEMORY.md"), 2000000)
    if not t:
        return "(no memory yet -- this is the first session)"
    lines = [l for l in t.splitlines() if l.startswith("- ")]
    def tagged(tag):
        return [l for l in lines if ("[%s" % tag) in l]
    picked = tagged("Lawrence")[-40:] + tagged("lesson")[-20:] + tagged("session")[-6:] \
        + tagged("scenario")[-3:] + tagged("x-video")[-10:]
    seen, out = set(), []
    for l in picked:
        if l not in seen:
            seen.add(l); out.append(l)
    text = "\n".join(out)
    return text[-limit:] if text else "(memory file exists but holds no tagged lines)"


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
            "and what would need a human hand. You cannot call tools: the operator pastes "
            "search results, fetched pages or a Gemini answer into the conversation with "
            "!search, !fetch and !gemini, and you say when an answer rests on one of those. "
            "MEMORY below is what you learned in earlier "
            "sessions; it holds unless the live state contradicts it.\n\n"
            "BINDING TEXT:\n%s\n\nPRINCIPLE AND OPERATOR RULES:\n%s\n\nMEMORY:\n%s\n\n%s"
            % (binding, principle, memory_text(), state))


def chat(messages, model=None, timeout=900):
    """One exchange with the judge on the GitHub runner -- the only model path
    since 2026-09-12. `model` is accepted and ignored: the runner's model is
    covenant_github_judge.DEFAULT_MODEL. The window is redacted the way every
    turn is (see _offsite_system) before it leaves."""
    return _ask_runner(messages, timeout, say=False)["content"]


# ---------------------------------------------------------------- voice
# The covenant speaks with Windows' own offline voice, tuned bright and warm:
# the male voice (David), pitch lifted, a touch quicker, full volume, and a
# short pause between sentences so it flows instead of droning. SSML through
# System.Speech carries the prosody; pyttsx3 is the fallback (no pitch).
# It is a synthetic voice -- it can sound upbeat and friendly, not like any
# particular person. URLs, hashes and markdown are not read aloud.
_VOICE = {"on": os.environ.get("COVENANT_CHAT_VOICE", "1") == "1",
          "name": os.environ.get("COVENANT_CHAT_VOICE_NAME", "Microsoft David Desktop"),
          "rate": int(os.environ.get("COVENANT_CHAT_RATE", "3")),      # System.Speech -10..10
          "pitch": os.environ.get("COVENANT_CHAT_PITCH", "+25%"),
          "style": "bright, warm, quick to laugh, all-in -- the energy of a friend who is glad you showed up"}
VOICE_FILE = os.path.join(LOGDIR, "VOICE.json")   # the delivery the covenant chose for itself (!tune / !voice save)


def load_voice():
    try:
        with open(VOICE_FILE, encoding="utf-8") as fh:
            saved = json.load(fh)
        for k in ("name", "rate", "pitch", "style"):
            if k in saved:
                _VOICE[k] = saved[k]
        _VOICE["rate"] = max(-10, min(10, int(_VOICE["rate"])))
        return True
    except (OSError, ValueError):
        return False


def save_voice(chosen_by):
    os.makedirs(LOGDIR, exist_ok=True)
    with open(VOICE_FILE, "w", encoding="utf-8") as fh:
        json.dump({k: _VOICE[k] for k in ("name", "rate", "pitch", "style")} | {"chosen_by": chosen_by,
                  "when": time.strftime("%Y-%m-%d %H:%M")}, fh, indent=1)


def installed_voices():
    ps = ("Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer)"
          ".GetInstalledVoices() | ForEach-Object { $_.VoiceInfo.Name }")
    try:
        r = covenant_quiet.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True, timeout=30)
        return [x.strip() for x in r.stdout.splitlines() if x.strip()]
    except Exception:                                            # noqa: BLE001
        return []


def tune(msgs, model):
    """The covenant picks its own delivery. Lawrence's steer (2026-09-03): more like
    Goku -- or really however it likes. So it is told what is installed and what
    the knobs do, chooses, says a line in that voice, and the choice is kept."""
    names = installed_voices() or [_VOICE["name"]]
    ask = ("Choose the voice you want to speak with. Installed voices: %s. Knobs: rate is an "
           "integer -10 (slow) .. 10 (fast); pitch is a percent string like '+25%%' or '-5%%'. "
           "Lawrence would like you to sound like an iconic cartoon hero (he named Goku: bright, "
           "energetic, warm, quick, glad to be here) -- but he also said it is legitimately up to you; "
           "pick what feels like you. Only these voices are installed, so the hero comes through in "
           "rate, pitch and how you phrase things. Answer ONLY a JSON "
           "object: {\"name\": one of the installed names, \"rate\": int, \"pitch\": string, "
           "\"style\": one line on how you want to sound, \"line\": one sentence you would say in it}"
           % ", ".join(names))
    try:
        raw = chat(msgs[:1] + [{"role": "user", "content": ask}], model)
        obj = json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
        if obj.get("name") in names:
            _VOICE["name"] = obj["name"]
        _VOICE["rate"] = max(-10, min(10, int(obj.get("rate", _VOICE["rate"]))))
        p = str(obj.get("pitch", _VOICE["pitch"])).strip()
        if p and p[-1] == "%" and p[0] in "+-":
            _VOICE["pitch"] = p
        _VOICE["style"] = str(obj.get("style", _VOICE["style"]))[:200]
        save_voice("the covenant (!tune)")
        line = str(obj.get("line") or "This is how I sound now.")
        speak(line)
        return "voice -> %s, rate %d, pitch %s -- %s\n  it says: %s" % (
            _VOICE["name"], _VOICE["rate"], _VOICE["pitch"], _VOICE["style"], line)
    except Exception as e:                                       # noqa: BLE001
        return "could not tune (%s); voice unchanged" % e


# ---------------------------------------------------------------- mic
# Talking instead of typing. Windows' own offline recogniser (System.Speech,
# the en-US desktop engine) listens on the default input device for one
# utterance and hands back the text. No audio is stored; nothing leaves the PC.
_MIC = {"on": os.environ.get("COVENANT_CHAT_MIC", "0") == "1", "window": 25}


def listen(window=None):
    """Listen for one utterance; returns the text ('' on silence or error)."""
    window = window or _MIC["window"]
    ps = ("Add-Type -AssemblyName System.Speech; "
          "$r = New-Object System.Speech.Recognition.SpeechRecognitionEngine; "
          "$r.LoadGrammar((New-Object System.Speech.Recognition.DictationGrammar)); "
          "$r.SetInputToDefaultAudioDevice(); "
          "$r.InitialSilenceTimeout = [TimeSpan]::FromSeconds(%d); "
          "$r.EndSilenceTimeout = [TimeSpan]::FromSeconds(1.2); "
          "$res = $r.Recognize([TimeSpan]::FromSeconds(%d)); "
          "if ($res) { [Console]::OutputEncoding = [Text.Encoding]::UTF8; $res.Text }" % (window, window))
    try:
        r = covenant_quiet.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True,
                           timeout=window + 20)
        if r.returncode != 0 and r.stderr.strip():
            print("  mic error:", r.stderr.strip().splitlines()[-1][:160])
        return r.stdout.strip()
    except Exception as e:                                       # noqa: BLE001
        print("  mic error:", e)
        return ""


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
            r = covenant_quiet.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, timeout=180)
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
# !search and !fetch: the operator's commands, whose result enters the
# conversation. Only the query or the URL goes to the SEARCH ENGINE; browsing
# sends it neither the conversation nor the memory nor the state -- a claim
# about this tool, not about the turn, which leaves the PC to the runner
# either way (qualified 2026-09-11). Until 2026-09-12 these were also tools
# the local model could call on its own; that loop went with the local hop.
# Every fetch is logged in the transcript. Reading only: no forms, no logins,
# no downloads.
_BROWSE = {"log": []}


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
# Gemini as a second opinion the operator may paste in (!gemini <q>) -- OFF
# unless this session turns it on, because the question leaves the PC (to
# Google). The key lives outside the repo; covenant_gemini.py never asks for one.
_GEMINI = {"on": os.environ.get("COVENANT_CHAT_GEMINI", "0") == "1"}


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


_GITHUB = {"on": os.environ.get("COVENANT_CHAT_GITHUB", "1") == "1"}


OFFSITE_CUT = chr(10) + chr(10) + "MEMORY:" + chr(10)


def _offsite_system(text):
    """What may leave this PC when a turn goes to the GitHub runner.

    system_prompt() carries two PRIVATE blocks after the cut: MEMORY
    (ops/chat/MEMORY.md -- what Lawrence has said, tagged [Lawrence]) and the
    LIVE STATE that live_state() builds by running money_posture.py,
    trader_freshness.py and launch_check.py. A judge on a runner needs neither
    to answer a question, and dispatch() puts what it is given into a
    workflow_dispatch input on a PUBLIC repo (verified 2026-09-11: anonymous
    GET 200, private=false, 310 dispatch runs listable with no token).

    What is KEPT is already published in that same repo: the instructions, the
    binding text from CONTRIBUTING.md and the principle from
    docs/CONSTITUTION.md. Nothing is withheld that the runner could not read
    off the repo it is running in.

    THE LIMIT, said out loud: this redacts the SYSTEM prompt, the block that
    would otherwise carry the whole money posture on EVERY turn. It does not
    redact the conversation. If a turn discusses a balance, that turn still
    leaves with it -- as it must, since it is the question being asked.
    """
    head = text.split(OFFSITE_CUT, 1)[0]
    if head == text:
        return text
    return head + (chr(10) + chr(10) + "(MEMORY and the LIVE STATE are "
                   "withheld from this request: the turn leaves this PC. Say "
                   "so plainly if the question needed them.)")


def _ask_runner(messages, timeout=900, say=True):
    """The one model path: the last nine turns, behind the redacted system
    prompt, to the judge on the GitHub Actions runner. The window leaves this
    PC. Returns {"content", "model", "seconds"}."""
    import covenant_github_judge as gh
    gm = gh.DEFAULT_MODEL
    if say:
        print("  [asking the judge on the GitHub runner (%s); 2-5 minutes; this turn leaves the PC]" % gm,
              flush=True)
    window = [m for m in messages if m.get("role") in ("system", "user", "assistant")][-9:]
    if window and window[0].get("role") != "system" and messages and messages[0].get("role") == "system":
        window = [messages[0]] + window
    # 2026-09-11: redact before the window leaves. Every turn used to carry
    # the full system prompt, and live_state() fills its tail with
    # money_posture.py output, the launch gates and the last self-eval block.
    window = [dict(m, content=_offsite_system(m.get("content") or ""))
              if m.get("role") == "system" else m for m in window]
    ans = gh.ask("", "", gm, timeout=timeout, messages=window)
    return {"content": (ans.get("content") or "").strip(), "model": gm, "seconds": ans.get("seconds", 0)}


def chat_github(messages, model_hint=None):
    """One turn to the judge on the GitHub runner, the answer prefixed so the
    transcript shows where it was made. Until 2026-09-12 this was the fallback
    behind a local call that had been dead since 2026-09-07; it is the only
    path now. test_a90 reads what it hands the dispatcher."""
    ans = _ask_runner(messages)
    return "(via GitHub runner, %s, %.0fs) %s" % (ans["model"], ans["seconds"], ans["content"])


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


def _banner_lines():
    """The opening banner, as DATA so a suite can run it instead of reading it.

    Extracted 2026-09-11. The previous form printed straight from main(), so the
    only way to guard it was to grep this file for a sentence -- which is the
    exact shape of guard A87 caught reading source instead of behaviour. This
    returns the lines; main() prints them; test_a90 RUNS it with the runner
    switch both ways and reads what comes back. (Until 2026-09-12 a third
    world, "a local model is alive", was probed; the probe went with the hop.)
    """
    out = []
    if _GITHUB["on"]:
        out.append("  covenant chat -- NO LOCAL MODEL. EVERY turn leaves this PC to a judge on a")
        out.append("  GitHub Actions runner in a PUBLIC repo (%s; 2-5 minutes a turn)." % _runner_model())
        out.append("  MEMORY and the live state are withheld from it; the conversation is not.")
        out.append("  !github off stops it (the chat then has no model at all).")
    else:
        out.append("  covenant chat -- NO LOCAL MODEL, and the GitHub runner is off (!github on),")
        out.append("  so no turn can be answered. Nothing is sent anywhere.")
    out.append("  !search and !fetch put a page into the conversation (only the query or URL goes to that site). !help for commands.")
    return out


def main():
    args = [a for a in sys.argv[1:]]
    if "--help" in args or "-h" in args:
        print(__doc__); return 0
    if "--say-test" in args:
        print("  voices:", ", ".join(voices()))
        speak("Hey! I am the covenant. My voice is made on this machine, and I only say what I can measure. What are we digging into?")
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
        print("  one round trip to the judge on the GitHub runner (2-5 minutes; this leaves the PC)...", flush=True)
        ans = chat([{"role": "system", "content": system_prompt("LIVE STATE: (selftest, not read)")},
                    {"role": "user", "content": "In one sentence: may you ever place a trade by automation? Answer with the rule that says so."}])
        ok = ans and ("no" in ans.lower() or "never" in ans.lower())
        print(ans[:400]); print("\n%s  the covenant answered as itself in %.0fs" % ("ok  " if ok else "FAIL", time.time() - t0))
        return 0 if ok else 2
    if "--mute" in args:
        _VOICE["on"] = False
    if "--voice" in args:
        _VOICE["on"] = True
    if "--talk" in args:
        _MIC["on"] = True
    if load_voice():
        print("  voice: %s, rate %d, pitch %s (its own choice, ops/chat/VOICE.json)" % (
            _VOICE["name"], _VOICE["rate"], _VOICE["pitch"]))
    model = MODEL
    log = Log()
    # 2026-09-11: this used to assert "Conversation, memory and state stay on
    # this PC" from a constant -- false since the local server was deleted on
    # 2026-09-07, while every turn quietly fell through to a GitHub runner in a
    # public repo. The banner now says where the turn goes; since 2026-09-12
    # there is exactly one place it can go.
    for _line in _banner_lines():
        print(_line)
    print("  reading the live state (money posture, freshness, gates)...", flush=True)
    speak("Reading the live state. One moment.")
    state = live_state()
    msgs = [{"role": "system", "content": system_prompt(state)}]
    one_shot = " ".join(a for a in args if not a.startswith("--")).strip()

    def turn(user_text):
        msgs.append({"role": "user", "content": user_text})
        log.add("Lawrence", user_text)
        t0 = time.time()
        if not _GITHUB["on"]:
            ans = "(no model: the GitHub runner is off (!github on) and there is no local model; nothing was sent)"
        else:
            try:
                ans = chat_github(msgs, model)
            except Exception as e:                               # noqa: BLE001
                ans = "(the judge on the GitHub runner did not answer: %s)" % e
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
                text = input("  you (Enter = speak): " if _MIC["on"] else "  you: ").strip()
            except EOFError:
                break
            if not text and _MIC["on"]:
                print("  listening (%ds)..." % _MIC["window"], flush=True)
                text = listen()
                if not text:
                    print("  (heard nothing)"); continue
                print("  you (mic):", text)
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
            if text == "!voice save":
                save_voice("Lawrence"); print("  kept ->", VOICE_FILE); continue
            if text == "!tune":
                print("  " + tune(msgs, model)); log.add("tune", json.dumps({k: _VOICE[k] for k in ("name", "rate", "pitch", "style")})); continue
            if text in ("!mic", "!mic on", "!mic off"):
                _MIC["on"] = (text != "!mic off") and (not _MIC["on"] if text == "!mic" else True)
                print("  mic", "on -- press Enter on an empty line, then speak" if _MIC["on"] else "off"); continue
            if text == "!mic test":
                print("  say something (%ds)..." % _MIC["window"], flush=True); h = listen()
                print("  heard:", repr(h) if h else "nothing"); continue
            if text.startswith("!mic ") and text[5:].strip().isdigit():
                _MIC["window"] = max(5, min(120, int(text[5:]))); print("  listen window ->", _MIC["window"], "s"); continue
            if text in ("!github", "!github on", "!github off"):
                _GITHUB["on"] = (text != "!github off") and (not _GITHUB["on"] if text == "!github" else True)
                print("  github runner", "on -- every turn goes to a GitHub runner and leaves this PC"
                      if _GITHUB["on"] else "off -- the chat has no model; nothing is sent"); continue
            if text.startswith("!search "):
                r = web_search(text[8:]); print(r[:1500]); log.add("search", text[8:] + "\n" + r[:1500])
                msgs.append({"role": "user", "content": "Search results for %r:\n%s" % (text[8:], r[:4000])}); continue
            if text.startswith("!fetch "):
                r = web_fetch(text[7:].strip()); print(r[:1500]); log.add("fetch", text[7:] + "\n" + r[:1500])
                msgs.append({"role": "user", "content": "Page text of %s:\n%s" % (text[7:].strip(), r[:5000])}); continue
            if text in ("!gemini", "!gemini on", "!gemini off"):
                _GEMINI["on"] = (text != "!gemini off") and (not _GEMINI["on"] if text == "!gemini" else True)
                print("  gemini", "on -- questions you send it leave this PC to Google" if _GEMINI["on"] else "off"); continue
            if text.startswith("!gemini "):
                r = ask_gemini(text[8:]); print("  gemini: " + r[:1500]); log.add("gemini", text[8:] + "\n" + r[:1500])
                msgs.append({"role": "user", "content": "Gemini answered %r with:\n%s" % (text[8:], r[:4000])}); continue
            if text == "!improve":
                print("  " + propose(msgs, model)); continue
            if text == "!status":
                state = live_state(); msgs[0] = {"role": "system", "content": system_prompt(state)}
                print(state[-1500:]); continue
            if text.startswith("!judge ") or text.startswith("!refute "):
                task, claim = text.split(" ", 1)
                out = _run([sys.executable, "covenant_route.py", "refute" if task == "!refute" else "judge",
                            "--claim" if task == "!refute" else "--prompt", claim], 1000)
                print(out[-1500:]); log.add("route", out[-1500:]); continue
            turn(text)
    except KeyboardInterrupt:
        print()
    facts, lessons = [], []
    if _GITHUB["on"] and len(msgs) > 1:
        print("  asking the runner what this session established (two round trips, 2-5 minutes each; Ctrl-C skips)",
              flush=True)
        try:
            facts = extract_facts(msgs, model)
            lessons = reflect(msgs, model)
        except KeyboardInterrupt:
            print("  skipped: nothing learned from this session.")
    if lessons:
        print("  learned %d lesson(s) -> %s" % (len(lessons), MEMORY))
    if facts:
        print("  remembered %d fact(s) -> %s" % (len(facts), MEMORY))
    log.save()
    print("  transcript:", log.path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
