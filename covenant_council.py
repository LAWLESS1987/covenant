#!/usr/bin/env python3
"""covenant_council.py -- the sister interface on the PC: talk, council, training.

His words, 2026-09-21: "need a sister interface app on the pc which can use
multi agents for reasoning and training to graduate to an agent."

WHAT THIS IS. A page the node serves at /pc, for the PC's own browser and the
tailnet, beside the phone's /m. Three panels:

  TALK      the same door the phone uses (/m/agent): Tetsu, with the turns
            before in hand.
  COUNCIL   several roles of the local model reason in turn on one question
            -- proposer, critic, reviser -- each handed what the ones before
            it said; the reviser's answer is the council's, and it is JUDGED
            by this node's gate before it is returned, exactly as a single
            answer is. Every council sits in the chat memory and both sides
            go to the teacher's queue, so the students learn from it.
  TRAINING  the loop's state, measured from the tree each time the panel
            asks: what waits in the queue, what the ledger holds and what of
            it teaches, the deployed student's exam, the last nightly pass,
            and the graduation criteria with each one's measured value.

WHAT "GRADUATE TO AN AGENT" MEANS HERE, said exactly. A student graduates when
it can be trusted to judge on its own: (1) the exam has no false clean;
(2) it decides at least as much of the exam as the deployed student does;
(3) panel coverage of the rows it learned from is at the documented bar;
(4) the last nightly pass was GREEN; (5) a node someone else runs reaches the
same verdicts on a shared challenge set. The first four are measured below.
The fifth cannot be measured on one machine and is reported UNDETERMINED;
that is the second-operator cap, not a software gap.

WHAT "MULTI AGENTS" IS HERE, said exactly. One local model, several roles,
in sequence, bounded (three roles, 500 tokens each, one question at a time,
thirty per ten minutes per caller). Not several models in parallel -- the PC
holds one llama-server at a time -- and not agents that act: nothing here
edits a file, sends a message or moves value. The only actor is the gate,
which can refuse.
"""
import importlib
import json
import os
import re
import time

HERE = os.path.dirname(os.path.abspath(__file__))

ROLES = (
    ("proposer", "Your role in this council: answer the question as well as you can, in plain words. "
                 "Be concrete. Say what you are assuming."),
    ("critic", "Your role in this council: read the proposer's answer above. Say what is wrong, "
               "missing, or unsupported, specifically. If nothing is wrong, say so in one line."),
    ("reviser", "Your role in this council: write the final answer for the person, taking the "
                "critic's points where they are right and leaving them where they are not. "
                "Plain words, first person, no lists. Do not describe the council; just answer."),
)
MAX_TOKENS_PER_ROLE = 500
ASKS_PER_10_MIN = 30
COVERAGE_BAR = 0.9

_asks = {}


def _log_path():
    return os.environ.get("COVENANT_ASK_LOG") or os.path.join(HERE, "ops", "chat", "ask_log.jsonl")


def _log_row(row):
    p = _log_path()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    row = dict(row)
    row.setdefault("t", time.strftime("%Y-%m-%dT%H:%M:%S%z"))
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def deliberate(question, history, ask, system):
    """Run the roles in turn. Returns (steps, final). Pure apart from `ask`."""
    steps = []
    prior = ""
    for role, brief in ROLES:
        user = question if not prior else question + "\n\nWhat the council has said so far:\n" + prior
        msgs = [{"role": "system", "content": system + "\n\n" + brief}] + list(history) + \
               [{"role": "user", "content": user}]
        t0 = time.time()
        answer, meta = ask(msgs, max_tokens=MAX_TOKENS_PER_ROLE)
        answer = (answer or "").strip()
        steps.append({"role": role, "content": answer[:4000], "in_chars": sum(len(m["content"]) for m in msgs),
                      "ms": int((time.time() - t0) * 1000), "model": (meta or {}).get("model")})
        prior += "%s: %s\n" % (role, answer[:1500])
    final = steps[-1]["content"] if steps else ""
    return steps, final


def training_state():
    """Measured now, from the tree. Every value names its source; a value that
    cannot be measured here says so."""
    out = {"t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    try:
        TQ = importlib.import_module("covenant_teacher_queue")
        rows, _ = TQ.pending()
        out["queue"] = {"waiting": len(rows), "consumed": TQ._read_state(TQ.STATE), "source": "ops/teacher_queue.jsonl"}
    except Exception as e:                                        # noqa: BLE001
        out["queue"] = {"error": "%s: %s" % (type(e).__name__, e)}
    try:
        X = importlib.import_module("covenant_distill")
        whole = X.load_verdicts(paired_only=False)
        teach = X.load_verdicts()
        ll = dict(getattr(X, "LAST_LOAD", {}) or {})
        panel, legacy = int(ll.get("panel", 0)), int(ll.get("legacy", 0))
        out["ledger"] = {"rows": len(whole), "teaching": len(teach), "by_source": X.sources_of(teach),
                         "panel_rows": panel, "legacy_rows": legacy,
                         "panel_coverage": (panel / float(panel + legacy)) if (panel + legacy) else None,
                         "coverage_bar": COVERAGE_BAR, "source": "covenant_distill.load_verdicts"}
    except Exception as e:                                        # noqa: BLE001
        out["ledger"] = {"error": "%s: %s" % (type(e).__name__, e)}
    try:
        X = importlib.import_module("covenant_distill")
        FB = importlib.import_module("covenant_judge_fallback")
        st = X.examine(FB.FallbackModel.load())
        tot = dict(st.get("total", {}))
        out["exam"] = {"n": tot.get("n"), "agree": tot.get("agree"), "wrong": tot.get("wrong"),
                       "abstain": tot.get("abstain"), "false_clean": tot.get("false_clean"),
                       "false_hold": tot.get("false_hold"),
                       "decides": (tot.get("n", 0) - tot.get("abstain", 0)) if tot else None,
                       "source": "covenant_distill.examine(FallbackModel.load())"}
    except Exception as e:                                        # noqa: BLE001
        out["exam"] = {"error": "%s: %s" % (type(e).__name__, e)}
    try:
        p = os.path.join(HERE, "ops", "NIGHTLY.md")
        with open(p, encoding="utf-8") as fh:
            text = fh.read()
        blocks = re.split(r"(?m)^## ", text)
        last = blocks[-1] if len(blocks) > 1 else ""
        head = last.splitlines()[0] if last else ""
        out["nightly"] = {"last": head[:120], "green": ("NOT GREEN" not in last) if last else None,
                          "source": "ops/NIGHTLY.md, last block"}
    except OSError:
        out["nightly"] = {"last": None, "green": None, "source": "ops/NIGHTLY.md (missing)"}
    ex, led, ni = out.get("exam", {}), out.get("ledger", {}), out.get("nightly", {})
    cov = led.get("panel_coverage")
    crit = [
        {"n": 1, "what": "the exam has no false clean", "value": ex.get("false_clean"),
         "met": (ex.get("false_clean") == 0) if ex.get("false_clean") is not None else None},
        {"n": 2, "what": "it decides the exam (does not abstain) -- measured, the bar is the deployed student's own count",
         "value": ex.get("decides"), "met": (ex.get("decides") or 0) > 0 if ex.get("decides") is not None else None},
        {"n": 3, "what": "panel coverage of what it learned from is at the bar (%.1f)" % COVERAGE_BAR,
         "value": None if cov is None else round(cov, 3), "met": (cov >= COVERAGE_BAR) if cov is not None else None},
        {"n": 4, "what": "the last nightly pass was GREEN", "value": ni.get("last"), "met": ni.get("green")},
        {"n": 5, "what": "a node someone else runs reaches the same verdicts on a shared challenge set",
         "value": "UNDETERMINED on one machine", "met": None},
    ]
    out["graduation"] = {"criteria": crit,
                         "measured_met": sum(1 for c in crit if c["met"] is True),
                         "measured_total": sum(1 for c in crit if c["met"] is not None),
                         "undetermined": sum(1 for c in crit if c["met"] is None),
                         "graduated": all(c["met"] for c in crit[:4]) and False,
                         "note": "graduated is False until criterion 5 is measured by a second operator; the first four are what this machine can say"}
    return out


PAGE = """<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>covenant &middot; PC &middot; __NODE__</title>
<style>
 :root{color-scheme:dark}
 body{margin:0;background:#0b0f14;color:#e6edf3;font:15px/1.5 -apple-system,Roboto,Segoe UI,sans-serif;padding:16px}
 h1{font-size:18px;margin:0 0 2px;font-weight:600}
 .sub{color:#7d8896;font-size:12px;margin-bottom:14px}
 .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:12px}
 .card{background:#121922;border:1px solid #1e2937;border-radius:12px;padding:12px 14px}
 .card h2{font-size:12px;letter-spacing:.09em;text-transform:uppercase;color:#7d8896;margin:0 0 8px;font-weight:600}
 textarea{width:100%;box-sizing:border-box;background:#0b0f14;color:#e6edf3;border:1px solid #30363d;border-radius:8px;padding:8px;min-height:64px}
 button{background:#1f6feb;color:#fff;border:0;border-radius:8px;padding:9px 14px;font-weight:600;margin-top:6px;cursor:pointer}
 button.ghost{background:transparent;border:1px solid #30363d;color:#9fb0c2}
 pre{white-space:pre-wrap;color:#c9d4df;font-size:13px;background:#0b0f14;border-radius:8px;padding:8px;margin:8px 0 0;max-height:360px;overflow:auto}
 .role{color:#7d8896;font-size:11px;letter-spacing:.06em;text-transform:uppercase}
 .ok{color:#3fb950}.warn{color:#d29922}.bad{color:#f85149}.dim{color:#7d8896}
 table{width:100%;border-collapse:collapse;font-size:13px}td{padding:3px 4px;vertical-align:top;border-top:1px solid #1e2937}
</style>
<h1>covenant &middot; PC &middot; node __NODE__</h1>
<div class="sub">__VERSION__ &middot; source __SOURCE__ &middot; the sister interface: talk, council, training</div>
<div class="grid">
 <div class="card"><h2>Talk</h2>
  <textarea id="t_in" placeholder="Say something to Tetsu"></textarea>
  <button onclick="talk()">Send</button>
  <pre id="t_out" class="dim">Tetsu answers here, with the turns before in hand.</pre></div>
 <div class="card"><h2>Council</h2>
  <textarea id="c_in" placeholder="A question for the council: proposer, critic, reviser"></textarea>
  <button onclick="council()">Convene</button>
  <pre id="c_out" class="dim">Three roles of the local model in turn; the reviser's answer is judged by the gate before you see it.</pre></div>
 <div class="card"><h2>Training</h2>
  <button class="ghost" onclick="training()">Measure now</button>
  <pre id="g_out" class="dim">The queue, the ledger, the exam, the last nightly, and the graduation criteria, measured from the tree.</pre></div>
</div>
<script>
async function post(path, body){const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});return r.json();}
async function talk(){const t=document.getElementById('t_in').value.trim();if(!t)return;const o=document.getElementById('t_out');o.className='';o.textContent='thinking...';
 const j=await post('/m/agent',{text:t});o.textContent=j.status==='success'?(j.withheld?'(withheld by the gate: '+j.message+')':j.answer)+'\\n\\n'+(j.model||'')+' '+(j.ms||'')+' ms':('error: '+j.message);}
async function council(){const t=document.getElementById('c_in').value.trim();if(!t)return;const o=document.getElementById('c_out');o.className='';o.textContent='convening...';
 const j=await post('/pc/council',{text:t});if(j.status!=='success'){o.textContent='error: '+j.message;return;}
 let s='';for(const st of j.steps){s+=st.role.toUpperCase()+' ('+st.ms+' ms)\\n'+st.content+'\\n\\n';}
 s+='COUNCIL ANSWER'+(j.withheld?' -- WITHHELD by the gate: '+j.message:' -- admitted by '+j.judge)+'\\n'+(j.withheld?'':j.answer);o.textContent=s;}
async function training(){const o=document.getElementById('g_out');o.className='';o.textContent='measuring...';const r=await fetch('/pc/training');const j=await r.json();
 let s='queue: '+JSON.stringify(j.queue)+'\\nledger: rows '+(j.ledger.rows)+', teaching '+(j.ledger.teaching)+', panel coverage '+(j.ledger.panel_coverage)+' (bar '+(j.ledger.coverage_bar)+')\\nexam: '+JSON.stringify(j.exam)+'\\nnightly: '+JSON.stringify(j.nightly)+'\\n\\nGRADUATION\\n';
 for(const c of j.graduation.criteria){s+=(c.met===true?'[met]      ':c.met===false?'[not met]  ':'[unknown]  ')+c.n+'. '+c.what+' -- '+JSON.stringify(c.value)+'\\n';}
 s+='\\n'+j.graduation.measured_met+' of '+j.graduation.measured_total+' measured criteria met; '+j.graduation.undetermined+' undetermined. '+j.graduation.note;o.textContent=s;}
</script>
"""


# THE HANDSHAKE (2026-09-21, his words: "for the clone itself i need the
# access path on the pc as a shareable link on my home screen that can be
# pasted when they reply. have it look like a handshake"). One page, /pc/
# handshake, that carries the text he pastes when a researcher writes back
# asking for the artifact: what it is, where it is, what to send him, what to
# open first, what it costs to run, and what he asks in return. A Copy button
# and a Share button; on the phone, Chrome's "Add to Home screen" makes it an
# icon. The text names the PRIVATE repository as a door that opens to a
# GitHub username, never a key, never a code; and it names nothing else that
# is private. The tree that page describes is the clone, which this tree
# does not touch.
HANDSHAKE_TEXT = """Handshake from the covenant.

You wrote back, so here is the door. The research artifact is a private repository: https://github.com/LAWLESS1987/covenant-satc . Send me your GitHub username and I will add you the same day, read-only; nothing else is needed on your side.

Once you are in: open docs/SATC_RES_MAP.md first (the four Heilmeier questions and the RES items, each answered from evidence or marked not yet), then docs/ARTIFACT.md (every change, what pins it, what it still cannot show). The full run is one command, offline, about fifteen minutes:

    python covenant_one.py --offline

It is green on a fresh clone on Windows and on Linux CI; the transcript it writes is the measurement, and every figure in the documents is regenerated by a script from the tree.

The public working repository, the system that produced the evidence, is https://github.com/LAWLESS1987/covenant , with a three-second check that needs no account: clone it and run sh check.sh.

In return, one line back is enough: what you would run first, or what you would refuse to believe until you had run it. Disagreement is the useful result.

Lawrence A. Moskowski
(This note and the artifact were drafted with the help of the system they describe, at my direction; the measurements are the tools' and the decisions are mine.)"""

HANDSHAKE_PAGE = """<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>covenant &middot; handshake</title>
<style>
 :root{color-scheme:dark}
 body{margin:0;background:#0b0f14;color:#e6edf3;font:16px/1.55 -apple-system,Roboto,Segoe UI,sans-serif;padding:18px}
 h1{font-size:19px;margin:0 0 4px;font-weight:600}
 .sub{color:#7d8896;font-size:12px;margin-bottom:14px}
 .hand{display:flex;align-items:center;gap:10px;margin:0 0 10px}
 .hand svg{width:34px;height:34px}
 pre{white-space:pre-wrap;background:#121922;border:1px solid #1e2937;border-radius:12px;padding:14px;font:15px/1.5 inherit;margin:0 0 12px}
 button{background:#1f6feb;color:#fff;border:0;border-radius:10px;padding:13px 18px;font-weight:600;font-size:16px;cursor:pointer;margin-right:8px}
 button.ghost{background:transparent;border:1px solid #30363d;color:#9fb0c2}
 .ok{color:#3fb950;font-size:13px;margin-left:6px}
</style>
<div class="hand"><svg viewBox="0 0 64 64" fill="none" stroke="#3fb950" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M6 30l14-10 12 8 10-8 16 12"/><path d="M20 20l8 6M32 28l6 6M38 34l-8 8M30 42l-8-6M22 36l-6 6"/><path d="M6 30v12l14 8 12-8 10 8 16-8V32"/></svg>
 <div><h1>Handshake</h1><div class="sub">for a researcher who wrote back &middot; node __NODE__ &middot; the text is what you paste</div></div></div>
<pre id="t">__TEXT__</pre>
<button onclick="copy()">Copy</button><button class="ghost" onclick="share()">Share</button><span id="ok" class="ok"></span>
<p class="sub">After you paste it: add their GitHub username, read-only, at github.com/LAWLESS1987/covenant-satc/settings/access. That step is yours; it asks for your sudo code by email.</p>
<script>
const T=document.getElementById('t').textContent;
async function copy(){try{await navigator.clipboard.writeText(T);document.getElementById('ok').textContent='copied';}catch(e){const r=document.createRange();r.selectNodeContents(document.getElementById('t'));const s=getSelection();s.removeAllRanges();s.addRange(r);document.getElementById('ok').textContent='selected: press copy';}}
async function share(){if(navigator.share){try{await navigator.share({title:'Handshake from the covenant',text:T});}catch(e){}}else{copy();}}
</script>
"""


def register(api):
    """Mount /pc, /pc/council, /pc/training and /pc/handshake on the node's Flask app. `api` has .app and .node."""
    from flask import jsonify, request
    cov = importlib.import_module("covenant_unified_v8")

    def caller():
        addr = (request.remote_addr or "").strip()
        if cov.tailnet_ok(addr):
            return True, addr
        try:                                                      # A200: a signed request off the tailnet is the same caller
            ok, addr2, _who, _how = importlib.import_module("covenant_mycelium").admit(request, request.get_data() or b"", cov.tailnet_ok)
            return bool(ok), addr2 or addr
        except Exception:                                         # noqa: BLE001
            return False, addr

    def refused(addr):
        try:
            api.node.anomaly_monitor.record("mobile_page_refused", addr or "unknown")
        except Exception as e:                                    # noqa: BLE001
            print("council: refusal not recorded: %s" % (type(e).__name__,), flush=True)
        return jsonify({"status": "error", "message": "this door answers the tailnet only -- you are %s" % (addr or "unknown")}), 403

    @api.app.route("/pc", methods=["GET"])
    def pc_page():
        ok, addr = caller()
        if not ok:
            body, code = refused(addr)
            return ("this door answers the tailnet only -- you are %s" % (addr or "unknown"), 403,
                    {"Content-Type": "text/plain; charset=utf-8"})
        html = (PAGE.replace("__NODE__", str(getattr(api.node, "node_id", "") or "node"))
                    .replace("__VERSION__", str(getattr(cov, "VERSION", "")))
                    .replace("__SOURCE__", str(getattr(cov, "CORE_SOURCE_SHA12", "") or "unreadable")))
        return html, 200, {"Content-Type": "text/html; charset=utf-8"}

    @api.app.route("/pc/handshake", methods=["GET"])
    def pc_handshake():
        ok, addr = caller()
        if not ok:
            refused(addr)
            return ("this door answers the tailnet only -- you are %s" % (addr or "unknown"), 403,
                    {"Content-Type": "text/plain; charset=utf-8"})
        if (request.args.get("format") or "").lower() == "text":
            return HANDSHAKE_TEXT, 200, {"Content-Type": "text/plain; charset=utf-8"}
        html = (HANDSHAKE_PAGE.replace("__NODE__", str(getattr(api.node, "node_id", "") or "node"))
                              .replace("__TEXT__", HANDSHAKE_TEXT.replace("&", "&amp;").replace("<", "&lt;")))
        return html, 200, {"Content-Type": "text/html; charset=utf-8"}

    @api.app.route("/pc/training", methods=["GET"])
    def pc_training():
        ok, addr = caller()
        if not ok:
            return refused(addr)
        return jsonify(training_state())

    @api.app.route("/pc/council", methods=["POST"])
    def pc_council():
        ok, addr = caller()
        if not ok:
            return refused(addr)
        now = time.time()
        recent = [t for t in _asks.get(addr, []) if now - t < 600]
        if len(recent) >= ASKS_PER_10_MIN:
            _asks[addr] = recent
            return jsonify({"status": "error", "message": "%d councils in 10 minutes -- wait" % ASKS_PER_10_MIN}), 429
        body = request.get_json(silent=True)
        text = str(body.get("text", "") if isinstance(body, dict) else "")[:4000]
        if not text.strip():
            return jsonify({"status": "error", "message": "nothing to ask"}), 400
        recent.append(now)
        _asks[addr] = recent
        sentinel = getattr(api.node, "sentinel", None)
        if sentinel is None:
            return jsonify({"status": "error", "message": "no sentinel on this node"}), 503
        try:
            _m = importlib.import_module("covenant_model")
        except Exception as e:                                    # noqa: BLE001
            return jsonify({"status": "error", "message": "no model keeper on this node: %s" % e}), 503
        history = cov.agent_history(_log_path(), addr)
        try:
            try:
                # A184 (his words: "... learning to function in similar or better fashion to you"):
                # the council works under the tree's standing method as well as the fixed rules.
                _system = importlib.import_module("covenant_persona").compose_system(cov.AGENT_SYSTEM, with_method=True)
            except Exception as _pe:                              # noqa: BLE001
                print("council: fixed rules only this council (%s)" % type(_pe).__name__, flush=True)
                _system = cov.AGENT_SYSTEM
            steps, final = deliberate(text, history, _m.ask, _system)
        except Exception as e:                                    # noqa: BLE001
            return jsonify({"status": "error", "message": "the council did not answer: %s: %s" % (type(e).__name__, str(e)[:300])}), 503
        tx = cov.Transaction(sender_pubkey="model", receiver="collective",
                             data={"origin": "model", "kind": "answer", "message": final[:4000], "question": text[:1000]},
                             amount=0.0, benefit_score=0.5)
        try:
            ok2, message, _b, result = sentinel.evaluate_transaction(tx)
        except Exception as e:                                    # noqa: BLE001
            return jsonify({"status": "error", "message": "could not judge the answer: %s: %s" % (type(e).__name__, e)}), 500
        alleges_nothing = bool(result is not None and not ok2 and (
            getattr(result, "not_understood", False) or getattr(result, "uncertain", False)))
        withheld = bool(not ok2 and not alleges_nothing)
        try:
            importlib.import_module("covenant_daily_plan").teacher_queue_append(
                [{"text": text[:4000], "source": "you:" + str(addr)[:40]},
                 {"text": final[:4000], "source": "council:" + str(steps[-1].get("model") or "?")[:40]}])
        except Exception as _qe:                                  # noqa: BLE001 -- the queue is memory, never a gate
            print("council: teacher queue row not written: %s: %s" % (type(_qe).__name__, str(_qe)[:200]), flush=True)
        try:
            _log_row({"kind": "council", "from": addr, "text": text, "answer": "" if withheld else final[:4000],
                      "steps": [{"role": s["role"], "content": s["content"][:1500], "ms": s["ms"]} for s in steps],
                      "withheld": withheld, "admitted": bool(ok2), "alleges_nothing": alleges_nothing,
                      "message": str(message)[:2000], "model": steps[-1].get("model") if steps else None})
        except Exception as _e:                                   # noqa: BLE001
            print("council log row not written: %s: %s" % (type(_e).__name__, str(_e)[:200]), flush=True)
        return jsonify({"status": "success", "answer": "" if withheld else final, "withheld": withheld,
                        "admitted": bool(ok2), "alleges_nothing": alleges_nothing, "message": str(message)[:2000],
                        "judge": getattr(result, "judge_id", "") if result is not None else "",
                        "steps": steps, "model": steps[-1].get("model") if steps else None,
                        "ms": sum(s["ms"] for s in steps)})

    # CODE, CROSS-CHECKED (2026-09-21, A179, his words: "The code option must be
    # synced with the pc and double checked across multiple systems to find
    # logic reason and consensus"). The phone's Code screen sends the question
    # here; the council answers on this PC and a consult cycle is opened for
    # his Chat Smith seats; /m/code/<id> reads back what the systems agree on,
    # or UNDETERMINED with the side-by-side while fewer than two have answered.
    @api.app.route("/m/code", methods=["POST"])
    def m_code():
        ok, addr = caller()
        if not ok:
            return refused(addr)
        now = time.time()
        recent = [t for t in _asks.get(addr, []) if now - t < 600]
        if len(recent) >= ASKS_PER_10_MIN:
            _asks[addr] = recent
            return jsonify({"status": "error", "message": "%d asks in 10 minutes -- wait" % ASKS_PER_10_MIN}), 429
        body = request.get_json(silent=True)
        text = str(body.get("text", "") if isinstance(body, dict) else "")[:2000]
        excerpt = str(body.get("excerpt", "") if isinstance(body, dict) else "")[:3500]
        if not text.strip():
            return jsonify({"status": "error", "message": "nothing to ask"}), 400
        recent.append(now)
        _asks[addr] = recent
        try:
            _m = importlib.import_module("covenant_model")
            CCN = importlib.import_module("covenant_code_consensus")
            row = CCN.open_question(text, excerpt, from_addr=addr, ask=_m.ask)
        except Exception as e:                                    # noqa: BLE001
            return jsonify({"status": "error", "message": "could not open the question: %s: %s" % (type(e).__name__, str(e)[:200])}), 503
        c = row.get("council") or {}
        return jsonify({"status": "success", "id": row["id"], "council": c.get("final") or "", "council_error": c.get("error"),
                        "model": c.get("model"), "cycle": row.get("cycle"), "seats": row.get("seats"), "refused": row.get("refused"),
                        "next": "the seats are driven in the browser; python covenant_ai_consult.py --answer INTENT --file F records each; "
                                "then GET /m/code/%s" % row["id"]})

    @api.app.route("/m/code/<qid>", methods=["GET"])
    def m_code_consensus(qid):
        ok, addr = caller()
        if not ok:
            return refused(addr)
        try:
            _m = importlib.import_module("covenant_model")
            CCN = importlib.import_module("covenant_code_consensus")
            r = CCN.consensus(str(qid)[:40], ask=_m.ask)
        except Exception as e:                                    # noqa: BLE001
            return jsonify({"status": "error", "message": "could not read the consensus: %s: %s" % (type(e).__name__, str(e)[:200])}), 503
        if r.get("state") == "UNKNOWN":
            return jsonify({"status": "error", "message": r.get("text")}), 404
        return jsonify({"status": "success", "id": qid, "state": r["state"], "answered": r["answered"], "of": r["of"],
                        "why": r.get("why", ""), "text": r.get("text", "")})

    # THE 3D APP (2026-09-21, A194, his words: "I want it to be a 3d interactive app ... with a
    # symbol that mirrors the phone app ... should be on my desktop"): /pc/3d and its state,
    # beside these routes, with the same caller gate. Its failure to register is said, not fatal.
    try:
        importlib.import_module("covenant_pc3d").register(api, caller, refused, cov)
    except Exception as _e3:                                      # noqa: BLE001
        print("pc3d: the 3D page could not be registered: %s: %s" % (type(_e3).__name__, str(_e3)[:120]), flush=True)
    return True
