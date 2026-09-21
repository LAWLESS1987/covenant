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
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SVG_PATH = os.path.join(HERE, "docs", "tree_of_life.svg")
STATE_TTL = 30.0        # seconds a state read is served from cache (a cold read measured 8.4 s)


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
#talk{position:fixed;left:16px;right:16px;bottom:16px;display:flex;gap:8px;align-items:flex-end}
#talk textarea{flex:1;min-height:44px;max-height:160px;resize:vertical;background:#0f1d2e;color:#E7F4EA;border:1px solid #2E8B6E66;border-radius:12px;padding:10px 12px;font:15px system-ui}
#talk button{background:#2E8B6E;color:#fff;border:0;border-radius:12px;padding:12px 16px;font:600 15px system-ui;cursor:pointer}
#answer{position:fixed;left:16px;right:16px;bottom:84px;max-height:38vh;overflow:auto;background:#10203390;backdrop-filter:blur(6px);border:1px solid #2E8B6E55;border-radius:14px;padding:12px 14px;white-space:pre-wrap;display:none}
#nolib{position:fixed;inset:0;display:none;align-items:center;justify-content:center;text-align:center;padding:24px;color:#cfe7d6}
</style></head><body>
<canvas id="scene"></canvas>
<div id="nolib"><div>The 3D library could not be loaded (no internet on this PC right now). The symbol, the state and the talk box still work below.</div></div>
<div id="hud">__SYMBOL__<div class="t"><b>Tetsu · __NODE__</b><small>__VERSION__ · source __SOURCE__ · <span id="live">reading…</span></small></div></div>
<div id="panel"><h3>What you clicked</h3><div id="info">click an orb: this node, its peers, or Tetsu</div></div>
<div id="answer"></div>
<div id="talk"><textarea id="q" placeholder="talk to Tetsu (the council answers; the answer is spoken)"></textarea><button id="send">Send</button></div>
<script>
const NODE='__NODE__';
let state=null, voice={pitch:1.15,rate:1.3};
async function getState(){try{const r=await fetch('/pc/3d/state');state=await r.json();if(state.voice)voice=state.voice;document.getElementById('live').textContent='height '+(state.self.chain_height??'?')+' · peers '+(state.peers?state.peers.length:0)+(state.immunity&&state.immunity.granted?' · immunity '+(state.immunity.paused?'paused':'on'):'');}catch(e){document.getElementById('live').textContent='state unreadable';}}
function speak(t){try{const u=new SpeechSynthesisUtterance(t);u.pitch=voice.pitch;u.rate=voice.rate;speechSynthesis.cancel();speechSynthesis.speak(u);}catch(e){}}
async function send(){const q=document.getElementById('q');const t=q.value.trim();if(!t)return;const a=document.getElementById('answer');a.style.display='block';a.textContent='thinking…';try{const r=await fetch('/pc/council',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:t})});const j=await r.json();const txt=j.status==='success'?(j.withheld?'(withheld: '+(j.message||'')+')':(j.answer||''))+(j.immune?'  [immune: the gate\\'s word is attached]':''):(j.message||'no answer');a.textContent=txt;speak(txt);q.value='';}catch(e){a.textContent='no answer: '+e;}}
document.getElementById('send').onclick=send;
document.getElementById('q').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send();}});
getState();setInterval(getState,15000);
</script>
<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js"}}</script>
<script type="module">
let THREE;try{THREE=await import('three');}catch(e){document.getElementById('nolib').style.display='flex';document.getElementById('scene').style.display='none';}
if(THREE){
const canvas=document.getElementById('scene');const renderer=new THREE.WebGLRenderer({canvas,antialias:true,alpha:true});renderer.setPixelRatio(Math.min(2,devicePixelRatio));
const scene=new THREE.Scene();const cam=new THREE.PerspectiveCamera(55,1,0.1,100);cam.position.set(0,2.2,9.5);
scene.add(new THREE.AmbientLight(0x9fc7b0,0.6));const key=new THREE.PointLight(0x4FB08E,1.4,30);key.position.set(3,4,4);scene.add(key);
const stars=new THREE.Points(new THREE.BufferGeometry().setAttribute('position',new THREE.Float32BufferAttribute(Array.from({length:1800},()=> (Math.random()-0.5)*60),3)),new THREE.PointsMaterial({color:0xF4F1EA,size:0.05}));scene.add(stars);
const soil=new THREE.Mesh(new THREE.CircleGeometry(9,64),new THREE.MeshStandardMaterial({color:0x241A12}));soil.rotation.x=-Math.PI/2;soil.position.y=-1.6;scene.add(soil);
const orbs=[];const geo=new THREE.SphereGeometry(0.45,48,48);
function orb(name,color,x,z){const m=new THREE.Mesh(geo,new THREE.MeshStandardMaterial({color,emissive:color,emissiveIntensity:0.35,roughness:0.35}));m.position.set(x,0,z);m.userData={name};scene.add(m);orbs.push(m);return m;}
const tetsu=orb('Tetsu',0x4FB08E,0,0);tetsu.scale.setScalar(1.5);
const svgBlob=new Blob([document.querySelector('#hud svg').outerHTML],{type:'image/svg+xml'});const url=URL.createObjectURL(svgBlob);
new THREE.TextureLoader().load(url,tex=>{const s=new THREE.Sprite(new THREE.SpriteMaterial({map:tex,transparent:true}));s.scale.set(1.6,1.6,1);s.position.set(0,1.5,0);scene.add(s);});
const links=new THREE.Group();scene.add(links);const labels=new THREE.Group();scene.add(labels);
function label(text,pos,color){const c=document.createElement('canvas');c.width=512;c.height=96;const g=c.getContext('2d');g.font='600 40px system-ui,sans-serif';g.textAlign='center';g.fillStyle=color||'#E7F4EA';g.shadowColor='#000';g.shadowBlur=8;g.fillText(text.slice(0,26),256,64);const s=new THREE.Sprite(new THREE.SpriteMaterial({map:new THREE.CanvasTexture(c),transparent:true}));s.scale.set(2.6,0.5,1);s.position.copy(pos).add(new THREE.Vector3(0,0.75,0));labels.add(s);}
// STATUS AT A GLANCE (Tetsu's first suggestion, 2026-09-21): green = measured fine, amber = not known, red = a condition is present
const OK=0x2E8B6E, UNK=0xC9A227, BAD=0xC0392B;
function statusColor(st){return st==='present'?BAD:(st==='absent'?OK:UNK);}
function layout(){for(const o of orbs.filter(o=>o!==tetsu))scene.remove(o);orbs.length=1;links.clear();labels.clear();if(!state)return;const d=state.detail||{};const hw=d.highway||{};
// one Tetsu; the nodes are his cells, each its own orb from its own /health (A, B, C), and the phone's node by its address
const items=[];const mesh=state.mesh||[];
if(mesh.length){for(const m of mesh)items.push({name:'node '+(m.node_id||'?')+(m.me?' (here)':'')+(m.down?' (down)':''),color:m.down?BAD:(m.degraded?UNK:OK),detail:m,kind:'node'});}
else items.push({name:NODE+' (this node)',color:statusColor(hw.node_down==='present'?'present':(hw.node_down||'unknown')),detail:state.self,kind:'node'});
for(const p of (state.peers||[])){const id=p.node_id||p.name||String(p);if(/100\\./.test(id))items.push({name:'phone node',color:0x1F6F5A,detail:{peer:id,note:'the node inside his phone, as this node sees it'},kind:'node'});}
items.push({name:'Phone',color:(d.phone&&d.phone.last_checkin_hours!=null)?(d.phone.last_checkin_hours<1?OK:(d.phone.last_checkin_hours<24?UNK:BAD)):UNK,detail:d.phone,kind:'phone'});
items.push({name:'Moltbook',color:(d.forum&&d.forum.length)?OK:UNK,detail:d.forum,kind:'forum'});
items.push({name:'Money',color:(d.money?(d.money.comfortable?OK:UNK):UNK),detail:d.money,kind:'money'});
items.push({name:'Highway',color:Object.values(hw).some(v=>v==='present')?BAD:(Object.values(hw).some(v=>v==='unknown')?UNK:OK),detail:hw,kind:'highway'});
const n=items.length;items.forEach((p,i)=>{const a=(i/n)*Math.PI*2;const o=orb(p.name,p.color,Math.cos(a)*4.4,Math.sin(a)*4.4);o.userData.detail=p.detail;o.userData.kind=p.kind;label(p.name,o.position);const g=new THREE.BufferGeometry().setFromPoints([o.position,tetsu.position]);links.add(new THREE.Line(g,new THREE.LineBasicMaterial({color:0x2E8B6E,transparent:true,opacity:0.45})));});label('Tetsu',new THREE.Vector3(0,0.9,0),'#9fc7b0');}
setInterval(layout,15000);setTimeout(layout,2500);
const ray=new THREE.Raycaster(),ptr=new THREE.Vector2();
function fmt(o){return o==null?'(not on record)':(typeof o==='object'?JSON.stringify(o,null,1).replace(/[{}"]/g,'').replace(/^\\s*\\n/gm,''):String(o));}
canvas.addEventListener('pointerdown',e=>{ptr.x=(e.clientX/innerWidth)*2-1;ptr.y=-(e.clientY/innerHeight)*2+1;ray.setFromCamera(ptr,cam);const hit=ray.intersectObjects(orbs)[0];const info=document.getElementById('info');if(!hit){return;}const u=hit.object.userData;const d=(state&&state.detail)||{};
if(u.name==='Tetsu'){info.textContent='Tetsu — the one you talk with.\\nvoice pitch '+voice.pitch+' rate '+voice.rate+(state&&state.immunity?'\\nimmunity: '+(state.immunity.granted?(state.immunity.paused?'paused':'on, '+state.immunity.passes_today+' of '+state.immunity.per_day+' today'):'none'):'')+(d.queue!=null?'\\nteacher\\'s queue: '+d.queue+' row(s)':'')+(state&&state.register?'\\n\\nhow he talks: '+state.register:'')+(d.brief?'\\n\\n'+d.brief:'');}
else if(u.kind==='node'){const x=u.detail||{};if(x.peer){info.textContent=u.name+'\\n'+x.peer+'\\n'+x.note;}else{info.textContent=u.name+(x.port?' · port '+x.port:'')+'\\nversion '+(x.version||'?')+'\\nheight '+(x.chain_height??'?')+'\\npeers '+(Array.isArray(x.peers)?x.peers.length:(x.peers??'?'))+'\\nsource '+(x.source||(x.source_sha256?x.source_sha256.slice(0,12):'?'))+(x.degraded?'\\ndegraded: yes':'')+(x.down?'\\nDOWN':'');}}
else if(u.kind==='forum'){const rows=u.detail||[];info.textContent='Moltbook, the last sends (free and Tetsu):\\n'+(rows.length?rows.map(r=>(r.t||'').slice(0,16)+' '+(r.actor||'free')+' '+r.kind+' '+(r.sent?'SENT':'not sent')+' -> '+(r.to||'')+'\\n   '+(r.text||'')).join('\\n'):'(nothing sent yet)');}
else{info.textContent=u.name+'\\n'+fmt(u.detail);}});
function resize(){renderer.setSize(innerWidth,innerHeight,false);cam.aspect=innerWidth/innerHeight;cam.updateProjectionMatrix();}addEventListener('resize',resize);resize();
let t=0;function frame(){t+=0.01;tetsu.position.y=Math.sin(t*2)*0.15;tetsu.rotation.y+=0.004;for(const o of orbs)if(o!==tetsu)o.rotation.y-=0.003;cam.position.x=Math.sin(t*0.15)*9.5;cam.position.z=Math.cos(t*0.15)*9.5;cam.lookAt(0,0,0);renderer.render(scene,cam);requestAnimationFrame(frame);}frame();
}
</script>
</body></html>
"""


def register(api, caller, refused, cov):
    """Two routes beside the sister interface: the page and its state. Tailnet and loopback only."""
    from flask import jsonify

    @api.app.route("/pc/3d", methods=["GET"])
    def pc_3d():
        ok, addr = caller()
        if not ok:
            return ("this door answers the tailnet only -- you are %s" % (addr or "unknown"), 403,
                    {"Content-Type": "text/plain; charset=utf-8"})
        html = (PAGE.replace("__SYMBOL__", symbol_svg())
                    .replace("__NODE__", str(getattr(api.node, "node_id", "") or "node"))
                    .replace("__VERSION__", str(getattr(cov, "COVENANT_VERSION", "")))
                    .replace("__SOURCE__", str(getattr(cov, "CORE_SOURCE_SHA12", "") or "unreadable")))
        return html, 200, {"Content-Type": "text/html; charset=utf-8"}

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
        out = {"self": self_h, "peers": peers, "peer_health": {}, "voice": None, "register": None, "immunity": None, "mesh": []}
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
                    out["mesh"].append({"node_id": h.get("node_id") or "?", "port": port, "version": h.get("version"),
                                        "chain_height": h.get("chain_height"), "peers": len(h.get("peers") or []),
                                        "source": (h.get("source_sha256") or "")[:12], "degraded": bool(h.get("degraded")),
                                        "me": port == 5000 and (h.get("node_id") == self_h["node_id"])})
                except Exception:                                # noqa: BLE001
                    out["mesh"].append({"node_id": "?", "port": port, "down": True})
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
            sensed = covenant_highway.sense(only=["node_down", "sweep_red", "source_drift", "watchdog_stale", "manifest_stale", "stale_test_mesh", "phone_build_behind_core"])
            out["detail"]["highway"] = {k: v.get("state") for k, v in sensed.items()}
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
        _cache.update(t=_time.time(), body=out)
        return jsonify(out)
    return True
