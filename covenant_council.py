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


def register(api):
    """Mount /pc, /pc/council and /pc/training on the node's Flask app. `api` has .app and .node."""
    from flask import jsonify, request
    cov = importlib.import_module("covenant_unified_v8")

    def caller():
        addr = (request.remote_addr or "").strip()
        return cov.tailnet_ok(addr), addr

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
            steps, final = deliberate(text, history, _m.ask, cov.AGENT_SYSTEM)
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
    return True
