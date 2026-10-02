#!/usr/bin/env python3
"""covenant_pc3d.py -- the PC as a 3D interactive app: the mesh as orbs with
their real height and peers, Tetsu as a presence that answers and speaks,
under the same symbol the phone app carries.

HIS WORDS, 2026-09-21: "I want it to be a 3d interactive app" -- "with a
symbol that mirrors the phone app" -- "should be on my desktop".

WHAT IT IS. One page, served by the node beside the sister interface (A167)
at /pc/3d, tailnet and loopback only, opened as a window of its own by the
Desktop launcher. The scene is three.js (loaded from a CDN; without the
internet the page says so and still shows the symbol and the talk box, it
does not pretend). The orbs are this node and its peers, read every ten
seconds from /pc/3d/state, which is this node's own /health plus the mesh it
reports, Tetsu's voice (A174/A192) and the state of his immunity (A190).
Clicking an orb names it: version, height, peers. The talk box is the
council (A167) with everything the register carries; the answer is spoken
by the browser with the mirrored voice. Nothing here is a second door:
every call is a route that already exists, with its own gate.

THE SYMBOL is docs/tree_of_life.svg, the phone app's launcher icon ported
path for path (the Tree of Life), inlined here and used as the sprite over
Tetsu's presence; the Desktop shortcut carries the same as its icon.
"""
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SVG_PATH = os.path.join(HERE, "docs", "tree_of_life.svg")
STATE_TTL = 30.0        # seconds a state read is served from cache (a cold read measured 8.4 s)
HIGHWAY_ORB_DETECTORS = (
    "node_down", "sweep_red", "source_drift", "watchdog_stale",
    "manifest_stale", "stale_test_mesh", "phone_build_behind_core",
)


def orb_inventory(state):
    """Read-only orb descriptions shared by the PC scene and native phone screen.

    Missing, malformed and unmeasured readings stay unknown. A green orb is a
    bounded measurement, not a claim that every capability or guard is healthy.
    """
    state = state if isinstance(state, dict) else {}
    detail = state.get("detail") if isinstance(state.get("detail"), dict) else {}
    rows = []

    def add(ident, name, status, summary, kind, value):
        rows.append(dict(id=ident, name=name, status=status, summary=summary, kind=kind, detail=value))

    add("tetsu", "Tetsu", "unknown", "Conversation, voice and learning records", "tetsu",
        {"voice": state.get("voice"), "register": state.get("register"),
         "immunity": state.get("immunity"), "brief": detail.get("brief"), "queue": detail.get("queue")})
    mesh = state.get("mesh") if isinstance(state.get("mesh"), list) else []
    for index, raw in enumerate(mesh):
        node = raw if isinstance(raw, dict) else {}
        port = node.get("port")
        name = "node %s%s%s" % (node.get("node_id") or "?",
                                  " (here)" if node.get("me") is True else "",
                                  " (down)" if node.get("down") is True else "")
        if port is not None:
            name += " · %s" % port
        known = (isinstance(node.get("node_id"), str) and node["node_id"] not in ("", "?")
                 and all(isinstance(node.get(k), int) and not isinstance(node[k], bool) and node[k] >= 0
                         for k in ("chain_height", "peers"))
                 and isinstance(node.get("version"), str) and bool(node["version"])
                 and isinstance(node.get("degraded"), bool))
        status = "attention" if node.get("down") is True else (
            "unknown" if not known or node.get("degraded") is True else "ok")
        summary = ("down: %s" % (node.get("why") or "health read failed") if node.get("down") is True
                   else "degraded · inspect warnings" if node.get("degraded") is True
                   else "up · height %s" % node["chain_height"] if known else "health reading incomplete")
        add("node:%s:%s" % (port if port is not None else "unknown", index), name, status, summary, "node", node)
    if not mesh:
        self_node = state.get("self") if isinstance(state.get("self"), dict) else {}
        add("node:self", "%s (this node)" % (self_node.get("node_id") or "node"),
            "unknown", "mesh health is not available", "node", state.get("self"))
    peers = state.get("peers") if isinstance(state.get("peers"), list) else []
    for index, peer in enumerate(peers):
        address = str(peer.get("node_id") or peer.get("name") or "") if isinstance(peer, dict) else str(peer)
        if address.startswith("100."):
            add("peer:%s:%s" % (index, address), "Peer node %s" % (index + 1), "unknown",
                "peer address; health not measured here", "node",
                {"peer": address, "note": "A peer address does not establish device identity or health."})
    phone = detail.get("phone") if isinstance(detail.get("phone"), dict) else {}
    hours = phone.get("last_checkin_hours")
    try:
        valid_age = (isinstance(hours, (int, float)) and not isinstance(hours, bool)
                     and math.isfinite(hours) and hours >= 0)
    except OverflowError:
        valid_age = False
    add("phone", "Phone", "ok" if valid_age and hours < 1 else (
        "attention" if valid_age and hours >= 24 else "unknown"),
        "checked in %.1f h ago" % hours if valid_age else "check-in age is not known", "phone", detail.get("phone"))
    forum = detail.get("forum")
    sent = sum(row.get("sent") is True for row in forum if isinstance(row, dict)) if isinstance(forum, list) else 0
    add("forum", "Moltbook", "ok" if sent else "unknown",
        "%s of %s sent" % (sent, len(forum)) if isinstance(forum, list) else "send records are unavailable", "forum", forum)
    money = detail.get("money") if isinstance(detail.get("money"), dict) else {}
    add("money", "Money", "ok" if money.get("comfortable") is True else "unknown",
        "comfortable" if money.get("comfortable") is True else "comfort not declared", "money", detail.get("money"))
    highway = detail.get("highway") if isinstance(detail.get("highway"), dict) else {}
    measured = {key: str(highway.get(key) or "unknown").lower() for key in HIGHWAY_ORB_DETECTORS}
    measured = {key: value if value in ("present", "absent", "unknown") else "unknown"
                for key, value in measured.items()}
    present, unknown = list(measured.values()).count("present"), list(measured.values()).count("unknown")
    add("highway", "Highway", "attention" if present else "unknown" if unknown else "ok",
        "%s need attention" % present if present else "%s not known" % unknown if unknown else "all seven measured clear",
        "highway", measured)
    return rows


def symbol_svg():
    try:
        with open(SVG_PATH, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 108 108"><circle cx="54" cy="54" r="40" fill="#2E8B6E"/></svg>'


PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>covenant · PC · __NODE__ · 3D</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
html,body{margin:0;height:100%;background:#0B1626;color:#E7F4EA;font:15px/1.4 system-ui,sans-serif;overflow:hidden}
#scene{position:fixed;inset:0}
#hud{position:fixed;left:16px;top:16px;display:flex;gap:12px;align-items:center;pointer-events:none}
#hud svg{width:56px;height:56px;border-radius:12px;box-shadow:0 0 24px #2E8B6E88}
#hud .t{pointer-events:none}
#hud .t b{display:block;font-size:17px}
#hud .t small{color:#9fc7b0}
#panel{position:fixed;right:16px;top:16px;width:min(340px,calc(100% - 32px));background:#10203390;backdrop-filter:blur(6px);border:1px solid #2E8B6E55;border-radius:14px;padding:12px 14px}
#panel h3{margin:0 0 6px;font-size:14px;color:#9fc7b0;letter-spacing:.06em;text-transform:uppercase}
#info{white-space:pre-wrap;font-family:ui-monospace,monospace;font-size:12px;color:#cfe7d6;min-height:60px}
#talk{position:fixed;left:16px;right:16px;bottom:16px;display:flex;gap:8px;align-items:flex-end;flex-wrap:wrap}
#talk textarea{flex:1;min-width:140px;min-height:44px;max-height:160px;resize:vertical;background:#0f1d2e;color:#E7F4EA;border:1px solid #2E8B6E66;border-radius:12px;padding:10px 12px;font:15px system-ui}
#talk button{background:#2E8B6E;color:#fff;border:0;border-radius:12px;padding:12px 16px;font:600 15px system-ui;cursor:pointer}
#talk button:disabled{opacity:0.45;cursor:default}
#talk select{background:#102033;color:#E7F4EA;border:1px solid #2E8B6E66;border-radius:10px;padding:12px 8px;font:14px system-ui}
.copybtn{margin-left:8px;font-size:11px;padding:2px 7px;background:#1f6f5a;border:0;border-radius:6px;color:#fff;cursor:pointer;vertical-align:middle}
/* 2026-09-28 (his words: "the text should be a pop up window you can minimize and orbs should be centered around
   mid screen"): the conversation is a floating window -- drag it by its title, minimise it to its title bar --
   and the scene stays centred. It opens when something is said and stays where he put it. */
#chatwin{position:fixed;left:16px;bottom:84px;width:min(440px,calc(100% - 32px));max-height:55vh;display:flex;flex-direction:column;background:rgba(14,28,45,.74);backdrop-filter:blur(8px);border:1px solid #2E8B6E55;border-radius:14px;box-shadow:0 8px 30px #0008;z-index:4}
#chathead{display:flex;align-items:center;gap:6px;padding:7px 10px 7px 14px;cursor:move;user-select:none;font-size:13px;color:#9fc7b0}
#chathead b{flex:1;font-weight:600}
#chathead button{background:none;border:0;color:#cfe7d6;font-size:17px;line-height:1;cursor:pointer;padding:2px 7px;border-radius:6px}
#chathead button:hover{background:#2E8B6E44}
#answer{overflow:auto;padding:4px 14px 12px;white-space:pre-wrap;display:none;scrollbar-width:thin;border-top:1px solid #2E8B6E33}
#chatwin.min #answer{display:none!important}
#answer .ln{margin:0 0 8px}#answer .you{color:#9fc7b0}#answer .heal{color:#e3c878}
body.nochat #answer{display:none!important}
body.nochat #chatwin{display:none}
#panel.min #info{display:none}
#info{max-height:min(52vh,calc(100vh - 260px));overflow:auto;scrollbar-width:thin}
#panel h3{display:flex;align-items:center}#panel h3 span{flex:1}
#panel h3 button{background:none;border:0;color:#cfe7d6;font-size:16px;cursor:pointer;padding:0 4px}
#legend{position:fixed;right:16px;bottom:84px;background:rgba(14,28,45,.58);backdrop-filter:blur(6px);border:1px solid #2E8B6E44;border-radius:12px;padding:8px 12px;font-size:12px;line-height:1.7;pointer-events:none}
#legend i{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:7px;vertical-align:-1px}
#tip{position:fixed;pointer-events:none;display:none;background:rgba(14,28,45,.85);border:1px solid #2E8B6E66;border-radius:10px;padding:6px 10px;font-size:13px;white-space:pre;z-index:5}#nolib{position:fixed;inset:0;display:none;align-items:center;justify-content:center;text-align:center;padding:24px;color:#cfe7d6}
#nolib{pointer-events:none}
#orblist{position:fixed;left:16px;top:88px;max-height:44vh;width:min(250px,calc(100% - 32px));overflow:auto;background:rgba(14,28,45,.82);border:1px solid #2E8B6E55;border-radius:12px;padding:8px;z-index:3}
#orblist summary{cursor:pointer;color:#9fc7b0;padding:4px}
#orbbuttons{display:flex;flex-direction:column;gap:4px}
.orbbutton{background:#102033;color:#E7F4EA;border:1px solid #2E8B6E44;border-radius:8px;text-align:left;padding:8px;cursor:pointer;font:13px system-ui}
.orbbutton:focus-visible,.orbbutton[aria-pressed="true"]{outline:2px solid #cfe7d6;outline-offset:-2px}
.orbbutton small{display:block;color:#9fc7b0;margin:3px 0 0 16px}
.orbbutton i{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px}
@media(max-width:650px){#orblist{top:86px;width:190px;max-height:35vh}#panel{top:auto;bottom:148px;max-height:30vh}#hud .t small{font-size:11px}#legend{display:none}}
</style></head><body>
<canvas id="scene"></canvas>
<div id="nolib"><div>The 3D library could not be loaded (no internet on this PC right now). The symbol, the state and the talk box still work below.</div></div>
<div id="hud">__SYMBOL__<div class="t"><b>Tetsu · __NODE__</b><small>__VERSION__ · source __SOURCE__ · <span id="live">reading…</span></small></div></div>
<details id="orblist" open><summary>System orbs · select for details</summary><div id="orbbuttons" aria-label="System orbs"></div></details>
<div id="panel"><h3><span id="ptitle">What you clicked</span><button id="pmin" title="minimise">–</button></h3><div id="info">hover a planet to see why it is its colour; click it (or its name) for the details</div></div>
<div id="chatwin" class="min"><div id="chathead"><b>Conversation <span id="chatn"></span></b><button id="chatmin" title="open / minimise (Esc)">▢</button><button id="chatx" title="close (the Show chat button brings it back)">×</button></div><div id="answer"></div></div><div id="tip"></div>
<div id="legend"><b>Colour code</b> (the glow around each planet)<br><i style="background:#2E8B6E"></i>green: measured fine<br><i style="background:#C9A227"></i>amber: not known, or waiting on someone<br><i style="background:#C0392B"></i>red, pulsing: needs attention<br><i style="background:#F4E9B0"></i>small lights: bots, carrying both ways</div>
<div id="talk"><textarea id="q" placeholder="Talk to Tetsu"></textarea><select id="mode" aria-label="Conversation mode"><option value="talk">Talk</option><option value="council">Council</option></select><button id="mic" title="speak to Tetsu instead of typing">Mic</button><button id="chatbtn" title="hide the conversation to see and click every orb; nothing is lost">Hide chat</button><button id="heal" title="Repair what can be repaired, and name what cannot">Self-heal</button><button id="send">Send</button></div>
<script>
const NODE='__NODE__';
// 2026-09-28 ("why aren't the orbs working on my pc and if they are why arent they auto refreshed"):
// the node now serves this page as it is on disk, and the state carries its hash; an open tab whose
// page is older reloads itself -- only while nothing is typed and no answer is on its way.
const PAGESHA='__PAGESHA__';
let state=null, voice={pitch:0.8,rate:0.95};
let orbRows=[], selectedOrb=null, stateUnreadable=false;
const ORB_COLORS={ok:'#2E8B6E',unknown:'#C9A227',attention:'#C0392B'};
const HIGHWAY_ORB_KEYS=['node_down','sweep_red','source_drift','watchdog_stale','manifest_stale','stale_test_mesh','phone_build_behind_core'];
// The list and details work without the CDN or WebGL. The scene reads the same inventory.
function orbItems(s){
 s=s&&typeof s==='object'?s:{};
 if(Array.isArray(s.orbs)&&s.orbs.length)return s.orbs.filter(x=>x&&typeof x.id==='string').map(x=>({...x,status:ORB_COLORS[x.status]?x.status:'unknown'}));
 const d=s.detail||{}, rows=[{id:'tetsu',name:'Tetsu',status:'unknown',summary:'Conversation, voice and learning records',kind:'tetsu',detail:{voice:s.voice,register:s.register,immunity:s.immunity,brief:d.brief,queue:d.queue}}];
 const mesh=Array.isArray(s.mesh)?s.mesh:[];
 for(const [i,m0] of mesh.entries()){const m=m0&&typeof m0==='object'?m0:{};
  const known=typeof m.node_id==='string'&&m.node_id!==''&&m.node_id!=='?'&&Number.isInteger(m.chain_height)&&m.chain_height>=0&&Number.isInteger(m.peers)&&m.peers>=0&&typeof m.version==='string'&&m.version!==''&&typeof m.degraded==='boolean';
  rows.push({id:'node:'+(m.port??'unknown')+':'+i,name:'node '+(m.node_id||'?')+(m.me===true?' (here)':'')+(m.down===true?' (down)':'')+(m.port!=null?' · '+m.port:''),status:m.down===true?'attention':(!known||m.degraded===true?'unknown':'ok'),summary:m.down===true?'down: '+(m.why||'health read failed'):(m.degraded===true?'degraded · inspect warnings':(known?'up · height '+m.chain_height:'health reading incomplete')),kind:'node',detail:m});}
 if(!mesh.length)rows.push({id:'node:self',name:((s.self||{}).node_id||'node')+' (this node)',status:'unknown',summary:'mesh health is not available',kind:'node',detail:s.self});
 for(const [i,p] of (Array.isArray(s.peers)?s.peers:[]).entries()){const address=typeof p==='object'&&p?(p.node_id||p.name||''):String(p);if(String(address).startsWith('100.'))rows.push({id:'peer:'+i+':'+address,name:'Peer node '+(i+1),status:'unknown',summary:'peer address; health not measured here',kind:'node',detail:{peer:address,note:'A peer address does not establish device identity or health.'}});}
 const h=d.phone&&d.phone.last_checkin_hours,valid=typeof h==='number'&&Number.isFinite(h)&&h>=0;
 rows.push({id:'phone',name:'Phone',status:valid&&h<1?'ok':valid&&h>=24?'attention':'unknown',summary:valid?'checked in '+h.toFixed(1)+' h ago':'check-in age is not known',kind:'phone',detail:d.phone});
 const f=Array.isArray(d.forum)?d.forum:null,n=f?f.filter(x=>x&&x.sent===true).length:0;
 rows.push({id:'forum',name:'Moltbook',status:n?'ok':'unknown',summary:f?n+' of '+f.length+' sent':'send records are unavailable',kind:'forum',detail:d.forum});
 const comfortable=d.money&&d.money.comfortable===true;
 rows.push({id:'money',name:'Money',status:comfortable?'ok':'unknown',summary:comfortable?'comfortable':'comfort not declared',kind:'money',detail:d.money});
 const hw=d.highway||{}, measured={};for(const k of HIGHWAY_ORB_KEYS){const v=String(hw[k]||'unknown').toLowerCase();measured[k]=['present','absent','unknown'].includes(v)?v:'unknown';}
 const values=Object.values(measured),present=values.filter(x=>x==='present').length,unknown=values.filter(x=>x==='unknown').length;
 rows.push({id:'highway',name:'Highway',status:present?'attention':unknown?'unknown':'ok',summary:present?present+' need attention':unknown?unknown+' not known':'all seven measured clear',kind:'highway',detail:measured});
 return rows;
}
function orbDetail(row){return row.name+' · '+row.status+'\\n'+row.summary+(stateUnreadable?'\\nLatest state read failed; these are the last known details.':'')+'\\n\\n'+(row.detail==null?'No measurement on record.':JSON.stringify(row.detail,null,2));}
function showSelectedOrb(){if(selectedOrb===null)return;const row=orbRows.find(x=>x.id===selectedOrb);document.getElementById('ptitle').textContent=row?row.name:'Orb unavailable';document.getElementById('info').textContent=row?orbDetail(row):'This orb is not in the latest snapshot.';}
function selectOrb(id){selectedOrb=id;const panel=document.getElementById('panel');if(panel.classList.contains('min'))document.getElementById('pmin').click();showSelectedOrb();for(const b of document.querySelectorAll('.orbbutton'))b.setAttribute('aria-pressed',String(b.dataset.orb===id));}
function refreshOrbs(){orbRows=orbItems(state);if(stateUnreadable)orbRows=orbRows.map(x=>({...x,status:'unknown',summary:'latest read unavailable · '+x.summary}));const box=document.getElementById('orbbuttons');
 const focus=document.activeElement&&document.activeElement.dataset?document.activeElement.dataset.orb:null;box.replaceChildren();
 for(const row of orbRows){const b=document.createElement('button');b.className='orbbutton';b.type='button';b.dataset.orb=row.id;b.setAttribute('aria-pressed',String(selectedOrb===row.id));b.setAttribute('aria-label',row.name+', '+row.status+', '+row.summary);const mark=document.createElement('i');mark.style.background=ORB_COLORS[row.status];mark.setAttribute('aria-hidden','true');b.appendChild(mark);b.appendChild(document.createTextNode(row.name));const sub=document.createElement('small');sub.textContent=row.status+' · '+row.summary;b.appendChild(sub);b.onclick=()=>selectOrb(row.id);box.appendChild(b);if(focus===row.id)b.focus();}
 showSelectedOrb();
}
document.getElementById('chatbtn').onclick=()=>{const off=document.body.classList.toggle('nochat');document.getElementById('chatbtn').textContent=off?'Show chat':'Hide chat';};
async function getState(){try{const r=await fetch('/pc/3d/state');if(!r.ok)throw new Error('state HTTP '+r.status);const next=await r.json();if(!next||typeof next!=='object'||!next.self)throw new Error('invalid state');state=next;stateUnreadable=false;if(state.page&&state.page!==PAGESHA&&!document.getElementById('q').value&&!(typeof inflight!=='undefined'&&inflight)){location.reload();return;}if(state.voice)voice=state.voice;document.getElementById('live').textContent='height '+(state.self.chain_height??'?')+' · peers '+(state.peers?state.peers.length:0)+(state.immunity&&state.immunity.granted?' · immunity '+(state.immunity.paused?'paused':'on'):'');refreshOrbs();if(window.onState)window.onState();}catch(e){stateUnreadable=true;document.getElementById('live').textContent='state unreadable';refreshOrbs();if(window.onState)window.onState();}}
function speak(t,generation=turnGeneration){try{if(generation!==turnGeneration)return;const u=new SpeechSynthesisUtterance(t);u.pitch=voice.pitch;u.rate=voice.rate;u.onstart=()=>{if(generation!==turnGeneration)speechSynthesis.cancel();};u.onend=()=>{if(generation===turnGeneration)document.getElementById('mic').textContent='Mic';};speechSynthesis.cancel();speechSynthesis.speak(u);}catch(e){}}
// THE CONVERSATION STAYS ON SCREEN (2026-09-26, his words: "increase tetsus pc logs length so
// its not gone before i respond"). Every exchange is appended, never replaced, and the page
// opens with the earlier exchanges from this address read back from the log (/pc/3d/history).
function line(who,text){const a=document.getElementById('answer');a.style.display='block';const d=document.createElement('div');d.className='ln '+who;d.textContent=(who==='you'?'you: ':(who==='heal'?'heal: ':'Tetsu: '))+text;a.appendChild(d);a.scrollTop=a.scrollHeight;document.getElementById('chatn').textContent='· '+a.children.length;return d;}
// THE WINDOW: minimise to the title bar, drag by the title, and it remembers both (this browser only)
const win=document.getElementById('chatwin'),mini=document.getElementById('chatmin');
function store(k,v){try{localStorage.setItem(k,v);}catch(e){}}function recall(k){try{return localStorage.getItem(k);}catch(e){return null;}}
function setMin(m){win.classList.toggle('min',m);mini.textContent=m?'▢':'–';store('pc3d.min',m?'1':'0');if(!m){const a=document.getElementById('answer');a.scrollTop=a.scrollHeight;}}
function openChat(){document.body.classList.remove('nochat');document.getElementById('chatbtn').textContent='Hide chat';setMin(false);}
mini.onclick=()=>setMin(!win.classList.contains('min'));
document.getElementById('chatx').onclick=()=>document.getElementById('chatbtn').click();
setMin(recall('pc3d.min')!=='0');
(function(){const p=recall('pc3d.pos');if(p){try{const [x,y]=JSON.parse(p);win.style.left=Math.max(0,Math.min(x,innerWidth-120))+'px';win.style.top=Math.max(0,Math.min(y,innerHeight-40))+'px';win.style.bottom='auto';}catch(e){}}})();
document.getElementById('chathead').addEventListener('pointerdown',e=>{if(e.target.tagName==='BUTTON')return;const r=win.getBoundingClientRect(),dx=e.clientX-r.left,dy=e.clientY-r.top;
 const mv=ev=>{const x=Math.max(0,Math.min(ev.clientX-dx,innerWidth-120)),y=Math.max(0,Math.min(ev.clientY-dy,innerHeight-40));win.style.left=x+'px';win.style.top=y+'px';win.style.bottom='auto';};
 const up=ev=>{removeEventListener('pointermove',mv);removeEventListener('pointerup',up);const r2=win.getBoundingClientRect();
  if(Math.hypot(r2.left-r.left,r2.top-r.top)<4){mini.click();return;}   // a click on the title, not a drag: open / minimise
  store('pc3d.pos',JSON.stringify([r2.left,r2.top]));};
 addEventListener('pointermove',mv);addEventListener('pointerup',up);});
document.getElementById('pmin').onclick=()=>{const p=document.getElementById('panel');const m=p.classList.toggle('min');document.getElementById('pmin').textContent=m?'▢':'–';};
// COPY (his words, 2026-09-27, catching the PC app up to the other chat apps): a small
// button on a finished Tetsu or heal line writes that line's own text to the clipboard --
// nothing sent anywhere new, no judge involved, the same text already on screen.
function addCopy(el,text){if(!text)return;const b=document.createElement('button');b.className='copybtn';b.textContent='copy';b.onclick=()=>{try{navigator.clipboard.writeText(text);}catch(e){}b.textContent='copied';setTimeout(()=>{b.textContent='copy';},1200);};el.appendChild(b);}
let conversation=[];
function contextExcerpt(text){if(text.length<=2000)return text;const marker='\\n[earlier text omitted]\\n',head=Math.floor((2000-marker.length)/3);return text.slice(0,head)+marker+text.slice(-(2000-head-marker.length));}
function rememberTurn(q,a){if(typeof q!=='string'||typeof a!=='string'||!q.trim()||!a.trim())return;conversation.push({role:'user',content:contextExcerpt(q)},{role:'assistant',content:contextExcerpt(a)});conversation=conversation.slice(-40);while(conversation.length&&conversation.reduce((n,x)=>n+x.content.length,0)>12000)conversation.splice(0,2);}
async function loadHistory(){try{const r=await fetch('/pc/3d/history');if(!r.ok)throw new Error('history unreadable');const j=await r.json();const before=document.getElementById('answer').firstChild;for(const x of (j.turns||[])){const you=line('you',x.q||'');const a=x.withheld?'(withheld: '+(x.why||'')+')':(x.a||'');const el=line('tetsu',a);if(before){document.getElementById('answer').insertBefore(you,before);document.getElementById('answer').insertBefore(el,before);}if(!x.withheld&&a.trim()){addCopy(el,a);rememberTurn(x.q||'',a);}}}catch(e){}}
// STOP (his words, 2026-09-27): Send becomes Stop while a council call is in flight, and a
// second press aborts the fetch in the browser -- the council on the PC still finishes its
// own run (there is no reaching into it mid-judge), but nothing it returns is shown or
// spoken once he has said stop, exactly as the phone's own Stop now works.
let inflight=null, pendingTurn=null, turnGeneration=0, recognitionGeneration=0;
function stopTurn(){turnGeneration++;recognitionGeneration++;if(inflight)inflight.abort();inflight=null;if(pendingTurn)pendingTurn.textContent='Tetsu: (stopped)';pendingTurn=null;try{speechSynthesis.cancel();if(recog)recog.abort();}catch(e){}document.getElementById('send').textContent='Send';document.getElementById('mic').textContent='Mic';}
async function send(){
 const btn=document.getElementById('send');
 if(inflight){stopTurn();return;}
 const q=document.getElementById('q');const t=q.value.trim();if(!t)return;q.value='';openChat();line('you',t);const pend=line('tetsu','thinking…');
 const generation=++turnGeneration;recognitionGeneration++;try{speechSynthesis.cancel();if(recog)recog.abort();}catch(e){}document.getElementById('mic').textContent='Mic';
 const ctrl=new AbortController();inflight=ctrl;pendingTurn=pend;btn.textContent='Stop';
 const requestId='pc3d-'+(globalThis.crypto&&crypto.randomUUID?crypto.randomUUID():Date.now().toString(36)+'-'+Math.random().toString(36).slice(2));
 const path=document.getElementById('mode').value==='council'?'/pc/council':'/m/agent';
 try{
  await historyReady;if(generation!==turnGeneration||ctrl.signal.aborted)return;
  const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:t,history:conversation,request_id:requestId}),signal:ctrl.signal});
  const j=await r.json();
  if(generation!==turnGeneration||ctrl.signal.aborted)return;
  const txt=j.status==='success'?(j.withheld?'(withheld: '+(j.message||'')+')':(j.answer||''))+(j.immune?'  [immune: the gate\\'s word is attached]':''):(j.message||'no answer');
  pend.textContent='Tetsu: '+txt;addCopy(pend,txt);if(j.status==='success'&&!j.withheld&&typeof j.answer==='string'&&j.answer.trim()){rememberTurn(t,j.answer);speak(txt,generation);}
 }catch(e){
  if(generation!==turnGeneration)return;
  pend.textContent=(e&&e.name==='AbortError')?'Tetsu: (stopped)':('Tetsu: no answer: '+e);
 }
 if(inflight===ctrl){inflight=null;pendingTurn=null;btn.textContent='Send';}
 document.getElementById('answer').scrollTop=1e9;
}
document.getElementById('send').onclick=send;
// MIC (his words, 2026-09-27, parity with the phone's own mic): the browser's own speech
// recognizer, when the browser has one -- nothing installed, nothing sent anywhere except
// the same /pc/council road typing already takes. Missing entirely on a browser without
// one (Firefox has none as of this writing): the button says so and stays harmless.
let recog=null;
function micSetup(){
 const m=document.getElementById('mic');
 const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
 if(!SR){m.disabled=true;m.title='this browser has no speech recognition';return;}
 m.onclick=()=>{stopTurn();const epoch=++recognitionGeneration,generation=turnGeneration;recog=new SR();recog.lang='en-US';recog.interimResults=true;
  recog.onresult=e=>{if(epoch!==recognitionGeneration||generation!==turnGeneration)return;const result=e.results[e.resultIndex||0];const t=result[0].transcript;document.getElementById('q').value=t;if(result.isFinal)send();};
  recog.onerror=()=>{if(epoch===recognitionGeneration)m.textContent='Mic';};
  recog.onend=()=>{if(epoch===recognitionGeneration)m.textContent='Mic';};
  try{m.textContent='...';recog.start();}catch(e){m.textContent='Mic';}};
}
micSetup();
// A215 (his words: "Give me a one click self heal button on the pc and phone apps").
// One press: the node runs covenant_heal, which runs the highway's own remedies
// with the person's cooldown waived, and says what it fixed and what still needs him.
async function heal(){const b=document.getElementById('heal');const a=document.getElementById('answer');
 b.disabled=true;const was=b.textContent;b.textContent='healing…';openChat();const hl=line('heal','looking at everything that can go wrong…');
 try{const r=await fetch('/m/heal',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});const j=await r.json();
  let t=j.summary||'no answer';
  if(j.fixed&&j.fixed.length)t+='\\n\\nFIXED:\\n'+j.fixed.map(x=>'  '+x.condition).join('\\n');
  if(j.still_needs_a_person&&j.still_needs_a_person.length)t+='\\n\\nSTILL NEEDS YOU:\\n'+j.still_needs_a_person.map(x=>'  '+x.condition+' — '+(x.why_no_fix||'')).join('\\n');
  // the full list goes to the details panel (top right), not over the orbs; the conversation keeps one short line
  const nf=(j.fixed||[]).length,nn=(j.still_needs_a_person||[]).length;
  hl.textContent='heal: fixed '+nf+', '+nn+' still need you (the list is in the panel, top right)';addCopy(hl,t);
  document.getElementById('ptitle').textContent='Self-heal';document.getElementById('info').textContent=t;speak(j.summary||'');}
 catch(e){hl.textContent='heal: could not be reached: '+e;}
 b.disabled=false;b.textContent=was;}
document.getElementById('heal').onclick=heal;
document.getElementById('q').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send();}});
// keys: Esc opens/minimises the conversation window, / jumps to the talk box
addEventListener('keydown',e=>{const typing=document.activeElement&&document.activeElement.id==='q';if(e.key==='Escape'){if(typing)document.activeElement.blur();else mini.click();}else if(e.key==='/'&&!typing){e.preventDefault();document.getElementById('q').focus();}});
const historyReady=loadHistory();refreshOrbs();getState();setInterval(getState,15000);
</script>
<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js"}}</script>
<script type="module">
let THREE;try{THREE=await import('three');}catch(e){document.getElementById('nolib').style.display='flex';document.getElementById('scene').style.display='none';}
if(THREE){try{
const canvas=document.getElementById('scene');const renderer=new THREE.WebGLRenderer({canvas,antialias:true,alpha:true});renderer.setPixelRatio(Math.min(2,devicePixelRatio));
const scene=new THREE.Scene();const cam=new THREE.PerspectiveCamera(55,1,0.1,100);cam.position.set(0,2.2,9.5);
scene.add(new THREE.AmbientLight(0x9fc7b0,0.6));const key=new THREE.PointLight(0x4FB08E,1.4,30);key.position.set(3,4,4);scene.add(key);
const stars=new THREE.Points(new THREE.BufferGeometry().setAttribute('position',new THREE.Float32BufferAttribute(Array.from({length:1800},()=> (Math.random()-0.5)*60),3)),new THREE.PointsMaterial({color:0xF4F1EA,size:0.05}));scene.add(stars);
const soil=new THREE.Mesh(new THREE.CircleGeometry(9,64),new THREE.MeshStandardMaterial({color:0x241A12}));soil.rotation.x=-Math.PI/2;soil.position.y=-1.6;scene.add(soil);
// PLANETS (his words, 2026-09-28: "i'd like the orbs to be full planets with ecosystems inhabited by bot swarms aimed at
// mutual benefit"). Each orb is a world painted from its own name (the same name, the same world, every load), wrapped
// in an atmosphere of its STATUS colour; a swarm of bots circles it, and bots carry light both ways along its line to
// Tetsu -- the exchange runs in both directions or it is not mutual. The status colour is still the measurement.
const orbs=[];const geo=new THREE.SphereGeometry(0.45,48,48);const atmoGeo=new THREE.SphereGeometry(0.53,32,32);
function rng(s){let h=2166136261;for(const ch of s)h=Math.imul(h^ch.charCodeAt(0),16777619);return()=>{h=Math.imul(h^(h>>>15),2246822507);h=Math.imul(h^(h>>>13),3266489909);return((h^=h>>>16)>>>0)/4294967296;};}
function world(name){const r=rng(name),c=document.createElement('canvas');c.width=256;c.height=128;const g=c.getContext('2d');
 const seas=['#1d4f7a','#17606e','#234a8a','#1b5d5a'],lands=['#3f8f4f','#5a8f3a','#7c8f45','#2f7a5a'];
 g.fillStyle=seas[Math.floor(r()*4)];g.fillRect(0,0,256,128);const land=lands[Math.floor(r()*4)];
 for(let i=0;i<14;i++){const x=r()*256,y=20+r()*88,s=8+r()*26;g.fillStyle=land;for(let k=0;k<7;k++){g.beginPath();g.arc(x+(r()-0.5)*s*1.6,y+(r()-0.5)*s,s*(0.35+r()*0.5),0,7);g.fill();}
  g.fillStyle='#8a7a52';g.globalAlpha=0.35;g.beginPath();g.arc(x,y,s*0.3,0,7);g.fill();g.globalAlpha=1;}
 g.fillStyle='#e8f1f2';g.fillRect(0,0,256,7);g.fillRect(0,121,256,7);
 const t=new THREE.CanvasTexture(c);t.colorSpace=THREE.SRGBColorSpace;return t;}
function orb(name,color,x,z){const m=new THREE.Mesh(geo,new THREE.MeshStandardMaterial({map:world(name),emissive:color,emissiveIntensity:0.12,roughness:0.8}));m.position.set(x,0,z);m.userData={name};
 const atmo=new THREE.Mesh(atmoGeo,new THREE.MeshBasicMaterial({color,transparent:true,opacity:0.2,side:THREE.BackSide,blending:THREE.AdditiveBlending,depthWrite:false}));m.add(atmo);m.userData.atmo=atmo;
 const n=36,pos=new Float32Array(n*3),r=rng(name+'bots');for(let i=0;i<n;i++){const a=r()*6.283,b=Math.acos(2*r()-1),d=0.62+r()*0.14;pos[i*3]=d*Math.sin(b)*Math.cos(a);pos[i*3+1]=d*Math.cos(b);pos[i*3+2]=d*Math.sin(b)*Math.sin(a);}
 const sw=new THREE.Points(new THREE.BufferGeometry().setAttribute('position',new THREE.BufferAttribute(pos,3)),new THREE.PointsMaterial({color:0xF4E9B0,size:0.035,depthWrite:false}));const swarm=new THREE.Group();swarm.add(sw);swarm.rotation.set(r()*1.2,0,r()*1.2);swarm.position.copy(m.position);swarm.userData.speed=0.004+r()*0.006;scene.add(swarm);m.userData.swarm=swarm;
 scene.add(m);orbs.push(m);return m;}
const tetsu=orb('Tetsu',0x4FB08E,0,0);tetsu.userData.id='tetsu';tetsu.scale.setScalar(1.5);tetsu.userData.swarm.scale.setScalar(1.5);
const svgBlob=new Blob([document.querySelector('#hud svg').outerHTML],{type:'image/svg+xml'});const url=URL.createObjectURL(svgBlob);
new THREE.TextureLoader().load(url,tex=>{const s=new THREE.Sprite(new THREE.SpriteMaterial({map:tex,transparent:true}));s.scale.set(1.6,1.6,1);s.position.set(0,1.5,0);scene.add(s);});
const links=new THREE.Group();scene.add(links);const labels=new THREE.Group();scene.add(labels);
// every orb carries a second line: WHY it is the colour it is (2026-09-28, "still running the wrong color")
function label(text,sub,pos,color){const c=document.createElement('canvas');c.width=512;c.height=150;const g=c.getContext('2d');g.textAlign='center';g.shadowColor='#000';g.shadowBlur=8;g.font='600 40px system-ui,sans-serif';g.fillStyle=color||'#E7F4EA';g.fillText(text.slice(0,26),256,56);if(sub){g.font='500 28px system-ui,sans-serif';g.fillStyle='#cfe7d6';g.fillText(sub.slice(0,34),256,104);}const s=new THREE.Sprite(new THREE.SpriteMaterial({map:new THREE.CanvasTexture(c),transparent:true,depthWrite:false}));s.scale.set(2.6,0.76,1);s.position.copy(pos).add(new THREE.Vector3(0,0.85,0));labels.add(s);}
function ago(h){return h<1?Math.round(h*60)+' min ago':(h<48?h.toFixed(1)+' h ago':(h/24).toFixed(1)+' d ago');}
// STATUS AT A GLANCE (Tetsu's first suggestion, 2026-09-21): green = measured fine, amber = not known, red = a condition is present
const OK=0x2E8B6E, UNK=0xC9A227, BAD=0xC0392B;
function statusColor(st){return st==='present'?BAD:(st==='absent'?OK:UNK);}
// 2026-09-25 ("the pc app needs optimization"): the scene is rebuilt only when what the orbs SHOW
// changes (their names and colours); otherwise the clicked details are refreshed in place. A rebuild
// releases the old materials, line geometry and label textures, which were leaked every 15 s before.
let lastSig='';
function layout(){if(!state)return;
const items=orbRows.filter(p=>p.id!=='tetsu').map(p=>({...p,color:p.status==='ok'?OK:p.status==='attention'?BAD:UNK,sub:p.summary}));
const sig=items.map(p=>p.id+'|'+p.name+'|'+p.color+'|'+p.sub).join(';');
if(sig===lastSig){items.forEach((p,i)=>{const o=orbs[i+1];if(o)o.userData.detail=p.detail;});return;}
lastSig=sig;
for(const o of orbs.filter(o=>o!==tetsu)){scene.remove(o);o.material.map.dispose();o.material.dispose();o.userData.atmo.material.dispose();const sw=o.userData.swarm;scene.remove(sw);sw.children[0].geometry.dispose();sw.children[0].material.dispose();}orbs.length=1;hovered=null;
for(const l of links.children){if(l.geometry!==botGeo)l.geometry.dispose();l.material.dispose();}links.clear();traders.length=0;
for(const s of labels.children){if(s.material.map)s.material.map.dispose();s.material.dispose();}labels.clear();
const n=items.length;items.forEach((p,i)=>{const a=(i/n)*Math.PI*2;const o=orb(p.name,p.color,Math.cos(a)*4.4,Math.sin(a)*4.4);o.userData.id=p.id;o.userData.detail=p.detail;o.userData.kind=p.kind;o.userData.sub=p.sub;o.userData.bad=p.color===BAD;label(p.name,p.sub,o.position);const g=new THREE.BufferGeometry().setFromPoints([o.position,tetsu.position]);links.add(new THREE.Line(g,new THREE.LineBasicMaterial({color:0x2E8B6E,transparent:true,opacity:0.35})));
 // two bots on every road, one each way: what goes out comes back
 for(const dir of [0,1]){const b=new THREE.Mesh(botGeo,new THREE.MeshBasicMaterial({color:dir?0xF4E9B0:0x9fe0c0}));b.userData={from:dir?tetsu.position:o.position,to:dir?o.position:tetsu.position,ph:Math.random()};links.add(b);traders.push(b);}});
label('Tetsu','',new THREE.Vector3(0,0.9,0),'#9fc7b0');}
const traders=[],botGeo=new THREE.SphereGeometry(0.04,8,8);let hovered=null;
window.onState=layout;setTimeout(layout,2500);
const ray=new THREE.Raycaster(),ptr=new THREE.Vector2();
function fmt(o){return o==null?'(not on record)':(typeof o==='object'?JSON.stringify(o,null,1).replace(/[{}"]/g,'').replace(/^\\s*\\n/gm,''):String(o));}
// CLICKING (his words, 2026-09-28: "the click feature needs refinement ... its not directly on the orbs"): a ray
// through a 0.45-unit sphere seen from 9.5 units away was a target a few dozen pixels wide, and the name above it
// was not a target at all. Now the pick is on the SCREEN: the nearest planet whose drawn disc (plus a 22 px
// margin) or whose name label is under the pointer.
const _v=new THREE.Vector3();
function pick(e){const k=(innerHeight/2)/Math.tan(cam.fov*Math.PI/360);let best=null,bd=1e9;
 for(const o of orbs){_v.copy(o.position).project(cam);if(_v.z>1)continue;const sx=(_v.x+1)/2*innerWidth,sy=(1-_v.y)/2*innerHeight;const dist=cam.position.distanceTo(o.position);
  const r=0.45*o.scale.x*k/dist,d=Math.hypot(e.clientX-sx,e.clientY-sy);let score=d<r+22?d-r:1e9;
  if(o!==tetsu){_v.copy(o.position).add(new THREE.Vector3(0,0.85,0)).project(cam);const lx=(_v.x+1)/2*innerWidth,ly=(1-_v.y)/2*innerHeight;if(Math.abs(e.clientX-lx)<1.1*k/dist&&Math.abs(e.clientY-ly)<0.3*k/dist)score=Math.min(score,0);}
  if(score<bd){bd=score;best=o;}}
 return best?{object:best}:null;}
const sel=new THREE.Mesh(new THREE.RingGeometry(0.6,0.66,64),new THREE.MeshBasicMaterial({color:0xffffff,transparent:true,opacity:0.85,side:THREE.DoubleSide,depthWrite:false}));sel.visible=false;scene.add(sel);
const tip=document.getElementById('tip');
function hoverScale(o,on){o.scale.setScalar((o===tetsu?1.5:1)*(on?1.15:1));}
canvas.addEventListener('pointermove',e=>{const h=pick(e),o=h?h.object:null;if(o!==hovered){if(hovered)hoverScale(hovered,false);hovered=o;if(o)hoverScale(o,true);canvas.style.cursor=o?'pointer':'default';}
 if(o){tip.style.display='block';tip.textContent=o.userData.name+(o.userData.sub?'\\n'+o.userData.sub:'')+'\\nclick for details';tip.style.left=Math.min(e.clientX+14,innerWidth-260)+'px';tip.style.top=(e.clientY+14)+'px';}else tip.style.display='none';});
canvas.addEventListener('pointerleave',()=>{if(hovered)hoverScale(hovered,false);hovered=null;tip.style.display='none';});
canvas.addEventListener('pointerdown',e=>{const hit=pick(e);if(hit)selectOrb(hit.object.userData.id);});
function resize(){renderer.setSize(innerWidth,innerHeight,false);cam.aspect=innerWidth/innerHeight;cam.updateProjectionMatrix();}addEventListener('resize',resize);resize();
let t=0;function frame(){t+=0.01;tetsu.position.y=Math.sin(t*2)*0.15;tetsu.userData.swarm.position.y=tetsu.position.y;tetsu.rotation.y+=0.004;
 for(const o of orbs){if(o!==tetsu)o.rotation.y-=0.003;const sw=o.userData.swarm;sw.rotation.y+=sw.userData.speed;if(o.userData.bad)o.userData.atmo.material.opacity=0.2+0.3*(0.5+0.5*Math.sin(t*5));}
 for(const b of traders){const k=(t*0.35+b.userData.ph)%1;b.position.lerpVectors(b.userData.from,b.userData.to,k);}
 const so=selectedOrb&&orbs.find(o=>o.userData.id===selectedOrb);sel.visible=!!so;if(so){sel.position.copy(so.position);sel.quaternion.copy(cam.quaternion);sel.scale.setScalar(so.scale.x);}
 cam.position.x=Math.sin(t*0.15)*9.5;cam.position.z=Math.cos(t*0.15)*9.5;cam.lookAt(0,-1.6,0);renderer.render(scene,cam);requestAnimationFrame(frame);}frame();
}catch(e){document.getElementById('scene').style.display='none';document.getElementById('nolib').style.display='flex';document.querySelector('#nolib div').textContent='The 3D scene is unavailable. All system orbs, details and conversation controls still work.';}}
</script>
</body></html>
"""


_page_cache = {"mtime": None, "page": None}


def current_page():
    """PAGE as this file says it NOW, not as it said when the node started (2026-09-28: the app's Mic,
    Stop and Copy landed on disk and the running node kept serving the page it had imported). Re-read
    only when the file's mtime moves; a file that fails to load mid-edit serves the last good page."""
    try:
        mt = os.stat(__file__).st_mtime
        if _page_cache["mtime"] != mt:
            import importlib.util
            spec = importlib.util.spec_from_file_location("_covenant_pc3d_page", __file__)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            _page_cache.update(mtime=mt, page=mod.PAGE)
    except Exception:                                            # noqa: BLE001
        pass
    return _page_cache["page"] or PAGE


def page_sha(page=None):
    import hashlib
    return hashlib.sha256((page or current_page()).encode("utf-8")).hexdigest()[:12]


def register(api, caller, refused, cov):
    """Two routes beside the sister interface: the page and its state. Tailnet and loopback only."""
    from flask import jsonify

    @api.app.route("/pc/3d", methods=["GET"])
    def pc_3d():
        ok, addr = caller()
        if not ok:
            return ("this door answers the tailnet only -- you are %s" % (addr or "unknown"), 403,
                    {"Content-Type": "text/plain; charset=utf-8"})
        page = current_page()
        html = (page.replace("__SYMBOL__", symbol_svg())
                    .replace("__PAGESHA__", page_sha(page))
                    .replace("__NODE__", str(getattr(api.node, "node_id", "") or "node"))
                    .replace("__VERSION__", str(getattr(cov, "COVENANT_VERSION", "")))
                    .replace("__SOURCE__", str(getattr(cov, "CORE_SOURCE_SHA12", "") or "unreadable")))
        return html, 200, {"Content-Type": "text/html; charset=utf-8"}

    @api.app.route("/pc/3d/history", methods=["GET"])
    def pc_3d_history():
        """This caller's last 40 exchanges with Tetsu (agent and council), oldest first, so the
        page opens on the conversation (2026-09-26, "so its not gone before i respond").
        Withheld answers are shown as withheld, with the reason, never dropped."""
        ok, addr = caller()
        if not ok:
            return refused(addr)
        path = os.environ.get("COVENANT_ASK_LOG") or os.path.join(HERE, "ops", "chat", "ask_log.jsonl")
        turns = []
        try:
            with open(path, "rb") as fh:
                fh.seek(0, 2)
                fh.seek(max(0, fh.tell() - 1024 * 1024))
                tail = fh.read().decode("utf-8", "replace")
            for ln in tail.splitlines():
                try:
                    r = json.loads(ln)
                except ValueError:
                    continue
                if not isinstance(r, dict):
                    continue
                if r.get("kind") in ("agent", "council") and r.get("from") == addr:
                    turns.append({"t": r.get("t"), "q": str(r.get("text", ""))[:4000], "a": str(r.get("answer", ""))[:4000],
                                  "withheld": bool(r.get("withheld")), "why": str(r.get("message", ""))[:300] if r.get("withheld") else ""})
        except OSError:
            turns = []
        return jsonify({"turns": turns[-40:]})

    _cache = {"t": 0.0, "body": None}

    @api.app.route("/pc/3d/state", methods=["GET"])
    def pc_3d_state():
        ok, addr = caller()
        if not ok:
            return refused(addr)
        import time as _time
        # Measured 2026-09-21: a cold state read took 8.4 s (the highway's sense reads the
        # process list through PowerShell). Cached STATE_TTL seconds; the page polls slower.
        if _cache["body"] is not None and _time.time() - _cache["t"] < STATE_TTL:
            return jsonify(_cache["body"])
        node = api.node
        self_h = {"node_id": getattr(node, "node_id", None), "version": getattr(cov, "COVENANT_VERSION", None),
                  "chain_height": len(getattr(node, "chain", []) or []), "source_sha256": getattr(cov, "CORE_SOURCE_SHA256", None)}
        peers = []
        try:
            for p in (getattr(node, "peers", None) or []):
                peers.append({"node_id": str(p)[:60]})
        except Exception:                                        # noqa: BLE001
            peers = []
        self_h["peers"] = peers
        out = {"self": self_h, "peers": peers, "peer_health": {}, "voice": None, "register": None, "immunity": None, "mesh": [],
               "page": page_sha()}
        # THE MESH AS DISTINCT ORBS (his words the same evening: "why 3 identical tetsus? the nodes
        # should be different orbs in the one"): every node of the local mesh read from its own
        # /health -- A, B, C with their own height, peers and source -- and the phone's node by
        # the peer address. One Tetsu; the nodes are his cells.
        try:
            import urllib.request as _ur
            import json as _json
            for port in (5000, 5020, 5060):
                try:
                    with _ur.urlopen("http://127.0.0.1:%d/health" % port, timeout=3) as r:
                        h = _json.loads(r.read().decode("utf-8", "replace"))
                    if not isinstance(h, dict):
                        raise ValueError("health response is not an object")
                    # /health reports `peers` as a COUNT (an int, since the first commit);
                    # len() of it threw, and the bare except below filed every live node
                    # as down (measured 2026-09-25: all three "down" while each answered
                    # in 0.02 s). A list is still counted, if one ever arrives.
                    _p = h.get("peers")
                    if isinstance(_p, (list, tuple)):
                        _np = len(_p)
                    elif isinstance(_p, int) and not isinstance(_p, bool) and _p >= 0:
                        _np = _p
                    elif _p is None:
                        _np = None
                    else:
                        raise ValueError("health peer count is invalid")
                    out["mesh"].append({"node_id": h.get("node_id") or "?", "port": port, "version": h.get("version"),
                                        "chain_height": h.get("chain_height"), "peers": _np,
                                        "source": str(h.get("source_sha256") or "")[:12],
                                        "degraded": h.get("degraded") if isinstance(h.get("degraded"), bool) else None,
                                        "warnings": [str(w)[:300] for w in h.get("warnings", [])[:20]] if isinstance(h.get("warnings"), list) else [],
                                        "me": h.get("node_id") == self_h["node_id"]})
                except Exception as _e:                          # noqa: BLE001
                    # the reason rides with the orb, so "down" is never a guess again
                    out["mesh"].append({"node_id": "?", "port": port, "down": True, "why": "%s: %s" % (type(_e).__name__, str(_e)[:120])})
        except Exception:                                        # noqa: BLE001
            pass
        try:
            import covenant_persona
            p = covenant_persona.load()
            out["voice"] = covenant_persona.clamp_voice(p.get("voice"))
            out["register"] = str(p.get("register") or "")[:400]
        except Exception:                                        # noqa: BLE001
            pass
        try:
            import covenant_immunity
            st = covenant_immunity.status()
            out["immunity"] = {k: st.get(k) for k in ("granted", "paused", "passes_today", "per_day")}
        except Exception:                                        # noqa: BLE001
            pass
        # MORE DETAIL (his words the same hour: "more detail in the app") and Tetsu's own
        # suggestions (asked through the council, 2026-09-21): node status at a glance,
        # Moltbook on the orbs. Every field below is a record the tree already keeps; a
        # record that cannot be read is null, never invented.
        out["detail"] = {"brief": None, "highway": None, "phone": None, "money": None, "forum": None, "queue": None}
        try:
            import covenant_persona
            out["detail"]["brief"] = covenant_persona.brief()
        except Exception:                                        # noqa: BLE001
            pass
        try:
            import covenant_highway
            want = list(HIGHWAY_ORB_DETECTORS)
            # What the watchdog's own last pass saw, when it is fresh (2026-09-25: sensing again
            # here was 95% of a cold read, profiled); sense only when there is no fresh pass.
            # LOWER-CASE, whatever arrives (2026-09-26): the watchdog writes the detector constants
            # ("PRESENT"), the page colours by 'present' -- so a Highway with node_down PRESENT was
            # drawn GREEN, and the test fixtures, written in lower case, never saw it. PC1z6.
            seen = covenant_highway.last_sense()
            if seen is not None and all(k in seen for k in want):
                out["detail"]["highway"] = {k: str(seen[k] or "unknown").lower() for k in want}
            else:
                sensed = covenant_highway.sense(only=want)
                out["detail"]["highway"] = {k: str((v or {}).get("state") or "unknown").lower() for k, v in sensed.items()}
        except Exception:                                        # noqa: BLE001
            pass
        try:
            import covenant_reconnect
            s = covenant_reconnect.signs_of_him()
            out["detail"]["phone"] = {"last_checkin_hours": s.get("phone", {}).get("hours"), "last_chat_hours": s.get("chat", {}).get("hours")}
        except Exception:                                        # noqa: BLE001
            pass
        try:
            import covenant_tetsu_money
            ms = covenant_tetsu_money.status()
            h = covenant_tetsu_money.holdings()
            out["detail"]["money"] = {"comfortable": ms.get("comfortable"), "paper_hypotheses": ms.get("paper_hypotheses"),
                                      "profitable": len(ms.get("profitable") or []), "needed": ms.get("needed"),
                                      "rule5": (ms.get("rule5") or {}).get("why"), "above_floor_usd": h.get("above_floor_usd"),
                                      "balance_age_h": h.get("age_h")}
        except Exception:                                        # noqa: BLE001
            pass
        try:
            import covenant_free_will
            rows = [r for r in covenant_free_will.sends() if r.get("kind") in ("reply", "own_post", "tetsu_reply", "tetsu_post", "intro")][-6:]
            out["detail"]["forum"] = [{"t": r.get("t"), "kind": r.get("kind"), "actor": r.get("actor", "free"), "sent": bool(r.get("sent")),
                                       "to": r.get("author") or r.get("target") or r.get("title"), "text": str(r.get("text") or "")[:160]} for r in rows]
        except Exception:                                        # noqa: BLE001
            pass
        try:
            import covenant_teacher_queue
            q, _ = covenant_teacher_queue.pending()
            out["detail"]["queue"] = len(q)
        except Exception:                                        # noqa: BLE001
            pass
        out["orbs"] = orb_inventory(out)
        _cache.update(t=_time.time(), body=out)
        return jsonify(out)
    return True
