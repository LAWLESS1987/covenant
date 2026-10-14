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
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{--ink:#070B14;--deck:#0B1220;--line:rgba(92,225,230,.22);--cyan:#5CE1E6;--amber:#F2B84B;--red:#FF6B6B;--green:#46E3A0;--txt:#E6EEF8;--dim:#93A4BC;--sans:'Space Grotesk',system-ui,sans-serif;--mono:'JetBrains Mono',ui-monospace,monospace}
html,body{margin:0;height:100%;background:var(--ink);color:var(--txt);font:15px/1.45 var(--sans);overflow:hidden}
#scene{position:fixed;inset:0}
#hud{position:fixed;left:16px;top:16px;display:flex;gap:12px;align-items:center;padding:10px 16px 10px 10px;background:rgba(11,18,32,.72);backdrop-filter:blur(8px);border:1px solid var(--line);border-radius:16px;z-index:3}
#hud svg{width:48px;height:48px;border-radius:12px;box-shadow:0 0 22px rgba(92,225,230,.35)}
#hud .t b{display:block;font-size:17px;letter-spacing:.08em}
#hud .t small{display:block;color:var(--dim);font:12px var(--mono)}
#healline{display:block;color:var(--green);font:12px var(--mono);max-width:46ch;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#codexbtn{margin-left:10px;background:transparent;color:var(--cyan);border:1px solid rgba(92,225,230,.45);border-radius:999px;padding:8px 14px;font:500 13px var(--sans);cursor:pointer;min-height:36px}
#codexbtn:hover{background:rgba(92,225,230,.12)}
#panel{position:fixed;right:16px;top:16px;width:min(380px,calc(100% - 32px));background:rgba(11,18,32,.78);backdrop-filter:blur(8px);border:1px solid var(--line);border-radius:16px;padding:12px 16px;z-index:3}
#panel h3{margin:0 0 6px;font:500 13px var(--sans);color:var(--cyan);letter-spacing:.14em;text-transform:uppercase}
#info{white-space:pre-wrap;font:12.5px/1.55 var(--mono);color:#cfd9e8;min-height:60px}
#talk{position:fixed;left:16px;right:16px;bottom:16px;display:flex;gap:8px;align-items:flex-end;flex-wrap:wrap;padding:8px;background:rgba(11,18,32,.78);backdrop-filter:blur(8px);border:1px solid rgba(92,225,230,.32);border-radius:22px;z-index:3}
#talk textarea{flex:1;min-width:140px;min-height:44px;max-height:160px;resize:vertical;background:transparent;color:var(--txt);border:0;outline:none;padding:10px 12px;font:16px var(--sans)}
#talk button{background:transparent;color:var(--txt);border:1px solid rgba(92,225,230,.4);border-radius:999px;padding:11px 18px;font:500 15px var(--sans);cursor:pointer;min-height:44px}
#talk button#send{background:var(--cyan);color:var(--ink);border-color:var(--cyan)}
#talk button:disabled{opacity:0.45;cursor:default}
.copybtn{margin-left:8px;font:11px var(--mono);padding:2px 8px;background:rgba(92,225,230,.15);border:1px solid rgba(92,225,230,.35);border-radius:999px;color:var(--cyan);cursor:pointer;vertical-align:middle}
/* 2026-09-28 (his words: "the text should be a pop up window you can minimize and orbs should be centered around
   mid screen"): the conversation is a floating window -- drag it by its title, minimise it to its title bar --
   and the scene stays centred. It opens when something is said and stays where he put it. */
#chatwin{position:fixed;left:16px;bottom:96px;width:min(460px,calc(100% - 32px));max-height:55vh;display:flex;flex-direction:column;background:rgba(11,18,32,.82);backdrop-filter:blur(10px);border:1px solid var(--line);border-radius:16px;box-shadow:0 8px 30px #0008;z-index:4}
#chathead{display:flex;align-items:center;gap:6px;padding:8px 10px 8px 14px;cursor:move;user-select:none;font:500 13px var(--sans);color:var(--cyan);letter-spacing:.08em}
#chathead b{flex:1;font-weight:500}
#chathead button{background:none;border:0;color:var(--txt);font-size:17px;line-height:1;cursor:pointer;padding:2px 7px;border-radius:6px}
#chathead button:hover{background:rgba(92,225,230,.15)}
#answer{overflow:auto;padding:4px 14px 12px;white-space:pre-wrap;display:none;scrollbar-width:thin;border-top:1px solid var(--line)}
#chatwin.min #answer{display:none!important}
#answer .ln{margin:0 0 8px}#answer .you{color:var(--cyan)}#answer .heal{color:var(--green);font-family:var(--mono);font-size:13px}
body.nochat #answer{display:none!important}
body.nochat #chatwin{display:none}
#panel.min #info{display:none}
#info{max-height:min(56vh,calc(100vh - 260px));overflow:auto;scrollbar-width:thin}
#panel h3{display:flex;align-items:center}#panel h3 span{flex:1}
#panel h3 button{background:none;border:0;color:var(--txt);font-size:16px;cursor:pointer;padding:0 4px}
#legend{position:fixed;right:16px;bottom:96px;background:rgba(11,18,32,.66);backdrop-filter:blur(6px);border:1px solid var(--line);border-radius:14px;padding:10px 14px;font:12px/1.8 var(--mono);color:var(--dim);pointer-events:none;z-index:2}
#legend b{color:var(--txt);font-family:var(--sans);font-weight:500}
#legend i{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:8px;vertical-align:-1px}
#tip{position:fixed;pointer-events:none;display:none;background:rgba(11,18,32,.9);border:1px solid rgba(92,225,230,.4);border-radius:10px;padding:7px 11px;font:12.5px var(--mono);white-space:pre;z-index:5}#nolib{position:fixed;inset:0;display:none;align-items:center;justify-content:center;text-align:center;padding:24px;color:var(--dim)}
</style></head><body>
<canvas id="scene"></canvas>
<div id="nolib"><div>The 3D library could not be loaded (no internet on this PC right now). The symbol, the state and the talk box still work below.</div></div>
<div id="hud">__SYMBOL__<div class="t"><b>COVENANT · __NODE__</b><small>__VERSION__ · source __SOURCE__ · <span id="live">reading…</span></small><span id="healline">self-heal: reading…</span></div><button id="codexbtn" title="his story, the Ten Commandments, and the balance every world keeps">Codex</button></div>
<div id="panel"><h3><span id="ptitle">The worlds</span><button id="pmin" title="minimise">–</button></h3><div id="info">Every planet is a living world around Tetsu, the star at the centre. Its life does one part of the work the whole system needs.

The glow of its air is the measurement: hover a world to see why it is that colour, click it to meet its life.</div></div>
<div id="chatwin" class="min"><div id="chathead"><b>Conversation <span id="chatn"></span></b><button id="chatmin" title="open / minimise (Esc)">▢</button><button id="chatx" title="close (the Show chat button brings it back)">×</button></div><div id="answer"></div></div><div id="tip"></div>
<div id="legend"><b>The air of each world</b> is its measurement<br><i style="background:#46E3A0"></i>green: measured fine, in balance<br><i style="background:#F2B84B"></i>amber: not known, or waiting on someone<br><i style="background:#FF6B6B"></i>red, pulsing: a condition needs attention<br><i style="background:#F4E9B0"></i>small lights: life carrying both ways</div>
<div id="talk"><textarea id="q" placeholder="Talk to Tetsu (the council answers; the answer is spoken)"></textarea><button id="mic" title="speak to Tetsu instead of typing">Mic</button><button id="chatbtn" title="hide the conversation to see and click every world; nothing is lost">Hide chat</button><button id="send">Send</button></div>
<script>
const NODE='__NODE__';
// 2026-09-28 ("why aren't the orbs working on my pc and if they are why arent they auto refreshed"):
// the node now serves this page as it is on disk, and the state carries its hash; an open tab whose
// page is older reloads itself -- only while nothing is typed and no answer is on its way.
const PAGESHA='__PAGESHA__';
let state=null, voice={pitch:0.8,rate:0.95};
document.getElementById('chatbtn').onclick=()=>{const off=document.body.classList.toggle('nochat');document.getElementById('chatbtn').textContent=off?'Show chat':'Hide chat';};
async function getState(){try{const r=await fetch('/pc/3d/state');
 // a busy node (HTTP 429: every local process shares one loopback address) keeps the last good reading on screen
 if(!r.ok){document.getElementById('live').textContent=(state?'last reading kept':'waiting')+' · the node is busy (HTTP '+r.status+'), trying again';setTimeout(getState,20000);return;}
 state=await r.json();if(state.page&&state.page!==PAGESHA&&!document.getElementById('q').value&&!(typeof inflight!=='undefined'&&inflight)){location.reload();return;}if(state.voice)voice=state.voice;document.getElementById('live').textContent='height '+(state.self.chain_height??'?')+' · peers '+(state.peers?state.peers.length:0)+(state.immunity&&state.immunity.granted?' · immunity '+(state.immunity.paused?'paused':'on'):'');showHealing();if(window.onState)window.onState();}catch(e){document.getElementById('live').textContent='state unreadable';}}
function speak(t){try{const u=new SpeechSynthesisUtterance(t);u.pitch=voice.pitch;u.rate=voice.rate;speechSynthesis.cancel();speechSynthesis.speak(u);}catch(e){}}
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
async function loadHistory(){try{const r=await fetch('/pc/3d/history');const j=await r.json();for(const x of (j.turns||[])){line('you',x.q||'');const a=x.withheld?'(withheld: '+(x.why||'')+')':(x.a||'');const el=line('tetsu',a);if(!x.withheld)addCopy(el,a);}}catch(e){}}
// STOP (his words, 2026-09-27): Send becomes Stop while a council call is in flight, and a
// second press aborts the fetch in the browser -- the council on the PC still finishes its
// own run (there is no reaching into it mid-judge), but nothing it returns is shown or
// spoken once he has said stop, exactly as the phone's own Stop now works.
let inflight=null;
async function send(){
 const btn=document.getElementById('send');
 if(inflight){inflight.abort();return;}
 const q=document.getElementById('q');const t=q.value.trim();if(!t)return;q.value='';openChat();line('you',t);const pend=line('tetsu','thinking…');
 const ctrl=new AbortController();inflight=ctrl;btn.textContent='Stop';
 try{
  const r=await fetch('/pc/council',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:t}),signal:ctrl.signal});
  const j=await r.json();
  const txt=j.status==='success'?(j.withheld?'(withheld: '+(j.message||'')+')':(j.answer||''))+(j.immune?'  [immune: the gate\\'s word is attached]':''):(j.message||'no answer');
  pend.textContent='Tetsu: '+txt;addCopy(pend,txt);speak(txt);
 }catch(e){
  pend.textContent=(e&&e.name==='AbortError')?'Tetsu: (stopped)':('Tetsu: no answer: '+e);
 }
 inflight=null;btn.textContent='Send';
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
 recog=new SR();recog.lang='en-US';recog.interimResults=false;
 recog.onresult=e=>{const t=e.results[0][0].transcript;document.getElementById('q').value=t;send();};
 recog.onerror=()=>{m.textContent='Mic';};
 recog.onend=()=>{m.textContent='Mic';};
 m.onclick=()=>{if(!recog)return;try{m.textContent='...';recog.start();}catch(e){m.textContent='Mic';}};
}
micSetup();
// SELF-HEAL WITHOUT A BUTTON (2026-10-13, his words: "if the self heal works right i shouldn't need the button").
// A215's button is gone from this page; the highway heals on its own every hour, and what it did arrives here in
// the state (/pc/3d/state, detail.healing). The newest run is shown under the title, and each new one is said once
// in the conversation as a heal line, with its copy button. The phone keeps its own HEAL; the road behind it is unchanged.
function showHealing(){const d=(state&&state.detail)||{};const rows=d.healing||[];const el=document.getElementById('healline');
 if(!rows.length){el.textContent='self-heal: on its own, hourly · nothing repaired lately';return;}
 const last=rows[rows.length-1];el.textContent='self-heal: on its own · last '+(last.t||'').slice(11,16)+' '+(last.remedy||'')+(last.ok===false?' (did not fix)':'');
 const seen=recall('pc3d.heal')||'';if(last.t&&last.t!==seen){store('pc3d.heal',last.t);if(seen){const t=rows.filter(x=>x.t>seen).map(x=>(x.t||'').slice(11,16)+' '+x.remedy+' for '+x.detector+(x.ok===false?' (did not fix)':'')).join('\\n');const hl=line('heal','on its own: '+t);addCopy(hl,t);}}}
document.getElementById('q').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send();}});
// keys: Esc opens/minimises the conversation window, / jumps to the talk box
addEventListener('keydown',e=>{const typing=document.activeElement&&document.activeElement.id==='q';if(e.key==='Escape'){if(typing)document.activeElement.blur();else mini.click();}else if(e.key==='/'&&!typing){e.preventDefault();document.getElementById('q').focus();}});
getState();setInterval(getState,15000);loadHistory();
</script>
<script>
__WORLDS_JS__
</script>
<script>
// THE CODEX (his words, 2026-10-13): his story as the record holds it, that he is just a man, and the Ten Commandments
// with how long they have been kept -- carried by every world. Opened from the Codex button; it changes no reading.
document.getElementById('codexbtn').onclick=()=>{const C=window.CovenantWorlds&&window.CovenantWorlds.CODEX;if(!C)return;
 document.getElementById('ptitle').textContent='The codex every world carries';const p=document.getElementById('panel');if(p.classList.contains('min'))document.getElementById('pmin').click();
 document.getElementById('info').textContent=C.founder.title.toUpperCase()+'\\n'+C.founder.lines.map(x=>'· '+x).join('\\n')+'\\n\\n'+C.commandments.title.toUpperCase()+'\\n'+C.commandments.items.map((x,i)=>(i+1)+'. '+x).join('\\n')+'\\n\\n'+C.commandments.span+'\\n'+C.commandments.source+'\\n\\nTHE BALANCE\\n'+C.balance;};
</script>
<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js"}}</script>
<script type="module">
let THREE;try{THREE=await import('three');}catch(e){document.getElementById('nolib').style.display='flex';document.getElementById('scene').style.display='none';}
const CW=window.CovenantWorlds;
if(THREE&&CW){
const canvas=document.getElementById('scene');const renderer=new THREE.WebGLRenderer({canvas,antialias:true,alpha:true});renderer.setPixelRatio(Math.min(2,devicePixelRatio));
const scene=new THREE.Scene();const cam=new THREE.PerspectiveCamera(50,1,0.1,200);cam.position.set(0,5,14);
scene.add(new THREE.AmbientLight(0x6c7f99,0.25));
const starPts=new Float32Array(4200);for(let i=0;i<4200;i++)starPts[i]=(Math.random()-0.5)*160;
const stars=new THREE.Points(new THREE.BufferGeometry().setAttribute('position',new THREE.Float32BufferAttribute(starPts,3)),new THREE.PointsMaterial({color:0xE6EEF8,size:0.08,transparent:true,opacity:0.8}));scene.add(stars);
// TETSU IS THE STAR (2026-10-13): every world turns toward him and is lit by him; the worlds orbit, he does not rule them.
const sun=CW.star(THREE,0.95);scene.add(sun);
const tetsu=sun;tetsu.userData.name='Tetsu';tetsu.userData.kind='star';tetsu.userData.radius=0.95;
const svgBlob=new Blob([document.querySelector('#hud svg').outerHTML],{type:'image/svg+xml'});const url=URL.createObjectURL(svgBlob);
new THREE.TextureLoader().load(url,tex=>{const s=new THREE.Sprite(new THREE.SpriteMaterial({map:tex,transparent:true,depthWrite:false}));s.scale.set(1.3,1.3,1);s.position.set(0,1.9,0);scene.add(s);});
// THE MYCELIUM UNDERNEATH (his words, 2026-10-13): the highway as the root network every world grows from; its colour is the Highway reading
const myc=CW.mycelium(THREE,{radius:9.5,y:-2.4});scene.add(myc);
const orbs=[tetsu];const links=new THREE.Group();scene.add(links);const labels=new THREE.Group();scene.add(labels);
// every world carries a second line: WHY its air is the colour it is (2026-09-28, "still running the wrong color")
function label(text,sub,color){const c=document.createElement('canvas');c.width=512;c.height=150;const g=c.getContext('2d');g.textAlign='center';g.shadowColor='#000';g.shadowBlur=10;g.font='600 40px Space Grotesk,system-ui,sans-serif';g.fillStyle=color||'#E6EEF8';g.fillText(text.slice(0,26),256,56);if(sub){g.font='500 26px JetBrains Mono,monospace';g.fillStyle='#93A4BC';g.fillText(sub.slice(0,36),256,104);}const s=new THREE.Sprite(new THREE.SpriteMaterial({map:new THREE.CanvasTexture(c),transparent:true,depthWrite:false}));s.scale.set(1.9,0.56,1);labels.add(s);return s;}
function ago(h){return h<1?Math.round(h*60)+' min ago':(h<48?h.toFixed(1)+' h ago':(h/24).toFixed(1)+' d ago');}
// STATUS AT A GLANCE (Tetsu's first suggestion, 2026-09-21): green = measured fine, amber = not known, red = a condition is present
const OK=0x46E3A0, UNK=0xF2B84B, BAD=0xFF6B6B;
function statusColor(st){return st==='present'?BAD:(st==='absent'?OK:UNK);}
function word(c){return c===BAD?'red':(c===UNK?'amber':'green');}
// 2026-09-25 ("the pc app needs optimization"): the scene is rebuilt only when what the worlds SHOW changes (their
// names and colours); otherwise the clicked details are refreshed in place. A rebuild releases the old materials.
let lastSig='';const traders=[],botGeo=new THREE.SphereGeometry(0.035,8,8);let hovered=null;
function dispose(o){o.traverse(x=>{if(x.geometry&&x.geometry!==botGeo)x.geometry.dispose();if(x.material){if(x.material.map)x.material.map.dispose();x.material.dispose();}});}
function layout(){if(!state)return;const d=state.detail||{};const hw=d.highway||{};
// the system's worlds: the nodes (his cells, each from its own /health), the phone, the forum, the money, the road
const items=[];const mesh=state.mesh||[];
if(mesh.length){mesh.forEach((m,i)=>items.push({name:'node '+(m.node_id||'?')+(m.me?' (here)':'')+(m.down?' (down)':''),color:m.down?BAD:(m.degraded?UNK:OK),sub:m.down?'down':(m.degraded?'degraded · click for why':'up · height '+(m.chain_height??'?')),detail:m,kind:'node',wid:m.node_id,wi:i}));}
else items.push({name:NODE+' (this node)',color:statusColor(hw.node_down==='present'?'present':(hw.node_down||'unknown')),sub:'node_down '+(hw.node_down||'unknown'),detail:state.self,kind:'node',wid:NODE,wi:0});
// the phone's node was drawn a fixed dark green, a colour nothing measured; this node sees it only as a peer address
for(const p of (state.peers||[])){const id=p.node_id||p.name||String(p);if(/100\\./.test(id))items.push({name:'phone node',color:UNK,sub:'a peer; its health is not read here',detail:{peer:id,note:'the node inside his phone, as this node sees it: an address, not a health reading'},kind:'phone'});}
const ph=d.phone&&d.phone.last_checkin_hours;
items.push({name:'Phone',color:ph!=null?(ph<1?OK:(ph<24?UNK:BAD)):UNK,sub:ph!=null?'checked in '+ago(ph):'no check-in on record',detail:d.phone,kind:'phone'});
// Moltbook was green whenever a row existed, sent or not (measured 2026-09-28: 6 rows, 0 sent); green now means something went out
// A277 (2026-10-06): the same rule over a day, not over the last six attempts -- a round now tries ~200
const fd=d.forum_day||{},fs=fd.sent||0,ft=fd.tried||0;
items.push({name:'Moltbook',color:fs?OK:UNK,sub:ft?fs+' sent of '+ft+' tried, '+(fd.window_h||24)+' h':'nothing tried in '+(fd.window_h||24)+' h',detail:d.forum,kind:'forum'});
items.push({name:'Money',color:(d.money?(d.money.comfortable?OK:UNK):UNK),sub:d.money?(d.money.comfortable?'comfortable':'comfort not declared'):'not on record',detail:d.money,kind:'money'});
const hp=Object.keys(hw).filter(k=>hw[k]==='present'),hu=Object.keys(hw).filter(k=>hw[k]==='unknown');
CW.setMycelium(myc,hp.length?BAD:(hu.length?UNK:OK));
items.push({name:'Highway',color:hp.length?BAD:(hu.length?UNK:OK),sub:hp.length?hp.length+' need attention':(hu.length?hu.length+' not known':'all clear'),detail:hw,kind:'highway'});
// HIS OTHER REPOSITORIES (2026-10-13, "implement the other repos into the apps also"): each a world on the outer ring,
// read from its clone on this PC. Green: committed and in step with GitHub; amber: work not committed, commits not
// pushed, or no upstream to compare with. Nothing here is a judgement of the work in it.
const repos=state.repos||[];
for(const r of repos){const amber=r.dirty||r.ahead||r.ahead==null;const age=r.last_commit_at?ago((Date.now()/1000-r.last_commit_at)/3600):'no commits';
 items.push({name:r.name,color:r.error?UNK:(amber?UNK:OK),sub:r.error?'unreadable':(r.dirty?r.dirty+' not committed':(r.ahead?r.ahead+' not pushed':(r.ahead==null?'no upstream':'in step · '+age))),detail:r,kind:'repo',wid:r.name,outer:true});}
const sig=items.map(p=>p.name+'|'+p.color+'|'+p.sub).join(';');
if(sig===lastSig){items.forEach((p,i)=>{const o=orbs[i+1];if(o)o.userData.detail=p.detail;});return;}
lastSig=sig;
for(const o of orbs.filter(o=>o!==tetsu)){scene.remove(o);dispose(o);}orbs.length=1;hovered=null;
for(const l of links.children){if(l.geometry!==botGeo)l.geometry.dispose();l.material.dispose();}links.clear();traders.length=0;
for(const s of labels.children){if(s.material.map)s.material.map.dispose();s.material.dispose();}labels.clear();
const inner=items.filter(p=>!p.outer),outer=items.filter(p=>p.outer);
const place=(list,R,size,speed)=>list.forEach((p,i)=>{const def=CW.worldFor(p.kind,p.wid,p.wi);const o=CW.planet(THREE,def,p.color,size);
 o.userData.orbitR=R;o.userData.orbitA=(i/list.length)*Math.PI*2;o.userData.orbitS=speed;o.userData.name=p.name;o.userData.detail=p.detail;o.userData.kind=p.kind;o.userData.sub=p.sub;o.userData.bad=p.color===BAD;o.userData.word=word(p.color);
 o.userData.label=label(def.repo?p.name:def.name+' · '+p.name,p.sub);if(p.outer)o.userData.label.scale.multiplyScalar(0.8);scene.add(o);orbs.push(o);
 const g=new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(),new THREE.Vector3()]);const ln=new THREE.Line(g,new THREE.LineBasicMaterial({color:0x5CE1E6,transparent:true,opacity:0.16}));ln.userData.of=o;links.add(ln);
 // two bots on every road, one each way: what goes out comes back
 for(const dir of [0,1]){const b=new THREE.Mesh(botGeo,new THREE.MeshBasicMaterial({color:dir?0xF4E9B0:0x9FF3F5}));b.userData={of:o,dir,ph:Math.random()};links.add(b);traders.push(b);}});
place(inner,4.6,0.48,0.0011);place(outer,7.6,0.34,0.0006);
label('Tetsu','the star').position.set(0,1.35,0);}
window.onState=layout;setTimeout(layout,2500);
function fmt(o){return o==null?'(not on record)':(typeof o==='object'?JSON.stringify(o,null,1).replace(/[{}"]/g,'').replace(/^\\s*\\n/gm,''):String(o));}
// CLICKING (his words, 2026-09-28: "the click feature needs refinement ... its not directly on the orbs"): the pick is
// on the SCREEN: the nearest world whose drawn disc (plus a 22 px margin) or whose name label is under the pointer.
const _v=new THREE.Vector3();
function pick(e){const k=(innerHeight/2)/Math.tan(cam.fov*Math.PI/360);let best=null,bd=1e9;
 for(const o of orbs){_v.copy(o.position).project(cam);if(_v.z>1)continue;const sx=(_v.x+1)/2*innerWidth,sy=(1-_v.y)/2*innerHeight;const dist=cam.position.distanceTo(o.position);
  const r=(o.userData.radius||0.45)*o.scale.x*k/dist,d=Math.hypot(e.clientX-sx,e.clientY-sy);let score=d<r+22?d-r:1e9;
  if(o!==tetsu&&o.userData.label){_v.copy(o.userData.label.position).project(cam);const lx=(_v.x+1)/2*innerWidth,ly=(1-_v.y)/2*innerHeight;if(Math.abs(e.clientX-lx)<1.1*k/dist&&Math.abs(e.clientY-ly)<0.3*k/dist)score=Math.min(score,0);}
  if(score<bd){bd=score;best=o;}}
 return best?{object:best}:null;}
const sel=new THREE.Mesh(new THREE.RingGeometry(0.62,0.67,64),new THREE.MeshBasicMaterial({color:0x5CE1E6,transparent:true,opacity:0.9,side:THREE.DoubleSide,depthWrite:false}));sel.visible=false;scene.add(sel);let selName=null;
const tip=document.getElementById('tip');
function hoverScale(o,on){o.scale.setScalar(on?1.12:1);}
canvas.addEventListener('pointermove',e=>{const h=pick(e),o=h?h.object:null;if(o!==hovered){if(hovered)hoverScale(hovered,false);hovered=o;if(o)hoverScale(o,true);canvas.style.cursor=o?'pointer':'default';}
 if(o){tip.style.display='block';tip.textContent=(o===tetsu?'Tetsu · the star':((o.userData.def?o.userData.def.name+' · ':'')+o.userData.name))+(o.userData.sub?'\\n'+o.userData.sub:'')+'\\nclick to meet its life';tip.style.left=Math.min(e.clientX+14,innerWidth-280)+'px';tip.style.top=(e.clientY+14)+'px';}else tip.style.display='none';});
canvas.addEventListener('pointerleave',()=>{tip.style.display='none';});
function lifeText(u){const def=u.def;if(!def)return '';const w=CW.describe(def,u.word);return '\\n\\nTHE WORLD OF '+w.name.toUpperCase()+'\\n'+w.strain+'\\n\\nITS LIFE\\n'+w.species.map(s=>'· '+s.name+': '+s.job).join('\\n')+'\\n\\nEvery world carries the codex: his story and the Ten Commandments (the Codex button, top left).';}
canvas.addEventListener('pointerdown',e=>{const hit=pick(e);const info=document.getElementById('info');if(!hit){return;}const u=hit.object.userData;const d=(state&&state.detail)||{};document.getElementById('ptitle').textContent=(u.def?u.def.name+' · ':'')+u.name;selName=u.name;const pn=document.getElementById('panel');if(pn.classList.contains('min'))document.getElementById('pmin').click();
if(u.kind==='node'&&u.detail&&u.detail.me&&u.detail.degraded){fetch('/health').then(r=>r.json()).then(h=>{if(document.getElementById('ptitle').textContent.endsWith(u.name))info.textContent+='\\n\\nwhy, in its own words (/health):\\n- '+(h.warnings||[]).join('\\n- ');}).catch(()=>{});}
// A348d (2026-10-14): the immunity count is the words covenant_immunity.count_text gives (state.immunity.count); joined here
// it read "on, 27 of 0 today" under his no-ceiling grant. A node not yet restarted sends no count: the bare day count shows.
if(u.name==='Tetsu'){info.textContent='Tetsu, the star at the centre -- the one you talk with.\\n'+CW.STAR.role+'\\n\\nvoice pitch '+voice.pitch+' rate '+voice.rate+(state&&state.immunity?'\\nimmunity: '+(state.immunity.granted?(state.immunity.paused?'paused':'on, '+(state.immunity.count||(state.immunity.passes_today+' today'))):'none'):'')+(d.queue!=null?'\\nteacher\\'s queue: '+d.queue+' row(s)':'')+(state&&state.register?'\\n\\nhow he talks: '+state.register:'')+(d.brief?'\\n\\n'+d.brief:'');return;}
let m='';
if(u.kind==='node'){const x=u.detail||{};m=u.name+(x.port?' · port '+x.port:'')+'\\nversion '+(x.version||'?')+'\\nheight '+(x.chain_height??'?')+'\\npeers '+(Array.isArray(x.peers)?x.peers.length:(x.peers??'?'))+'\\nsource '+(x.source||(x.source_sha256?x.source_sha256.slice(0,12):'?'))+(x.degraded?'\\ndegraded: yes':'')+(x.down?'\\nDOWN '+(x.why||''):'');}
else if(u.kind==='phone'&&u.detail&&u.detail.peer){m=u.name+'\\n'+u.detail.peer+'\\n'+u.detail.note;}
else if(u.kind==='forum'){const rows=u.detail||[];m='Moltbook, the last replies that went out (free and Tetsu):\\n'+(rows.length?rows.map(r=>(r.t||'').slice(0,16)+' '+(r.actor||'free')+' '+r.kind+' '+(r.sent?'SENT':'not sent')+' -> '+(r.to||'')+'\\n   '+(r.text||'')).join('\\n'):'(nothing sent yet)');}
else if(u.kind==='repo'){const x=u.detail||{};m='the repository '+x.name+(x.error?'\\nunreadable: '+x.error:'\\nlast commit '+(x.last_commit_at?ago((Date.now()/1000-x.last_commit_at)/3600):'none')+'\\nbranch '+(x.branch||'?')+'\\nnot committed: '+(x.dirty??'?')+'\\nnot pushed: '+(x.ahead==null?'no upstream to compare':x.ahead)+'\\nread from its clone on this PC');}
else{m=u.name+'\\n'+fmt(u.detail);}
info.textContent='MEASURED\\n'+m+lifeText(u);});
// CENTRED ON THE SUN (2026-10-13, his words: "center universe mid screen around their sun so its center screen for
// me"): the canvas is sized to the window every frame it changes (a resize the browser never announced left the
// drawing stretched off-centre), and the camera looks straight at Tetsu, so the star is the middle of the screen.
let vw=0,vh=0;function resize(){vw=innerWidth;vh=innerHeight;renderer.setSize(vw,vh);cam.aspect=vw/vh;cam.updateProjectionMatrix();}addEventListener('resize',resize);resize();
let t=0;const sunPos=new THREE.Vector3();
function frame(){t+=0.01;CW.tickStar(tetsu,t);CW.tickMycelium(myc,t,orbs.slice(1));
 for(const o of orbs){if(o===tetsu)continue;const u=o.userData;u.orbitA+=u.orbitS;o.position.set(Math.cos(u.orbitA)*u.orbitR,Math.sin(u.orbitA*2)*0.25,Math.sin(u.orbitA)*u.orbitR);
  CW.tick(o,t,sunPos);if(u.bad)u.atmoU.uGlow.value=0.7+0.5*(0.5+0.5*Math.sin(t*5));if(u.label)u.label.position.copy(o.position).add(new THREE.Vector3(0,(u.radius||0.45)+0.55,0));}
 for(const l of links.children){if(l.isLine){const p=l.geometry.attributes.position;p.setXYZ(1,l.userData.of.position.x,l.userData.of.position.y,l.userData.of.position.z);p.needsUpdate=true;}}
 for(const b of traders){const k=(t*0.35+b.userData.ph)%1;const a=b.userData.of.position;if(b.userData.dir)b.position.copy(a).multiplyScalar(k);else b.position.copy(a).multiplyScalar(1-k);}
 const so=selName&&orbs.find(o=>o.userData.name===selName);sel.visible=!!so;if(so){sel.position.copy(so.position);sel.quaternion.copy(cam.quaternion);sel.scale.setScalar((so.userData.radius||0.45)/0.45*1.4);}
 if(innerWidth!==vw||innerHeight!==vh)resize();
 const R=cam.aspect<1?Math.min(30,14*0.85/cam.aspect):14;cam.position.set(Math.sin(t*0.05)*R,R*0.36,Math.cos(t*0.05)*R);cam.lookAt(0,0,0);renderer.render(scene,cam);requestAnimationFrame(frame);}frame();
}
</script>
</body></html>
"""


def worlds_js():
    """docs/worlds/covenant_worlds.js, the planet engine both apps load (A340), inlined into the page."""
    try:
        with open(os.path.join(HERE, "docs", "worlds", "covenant_worlds.js"), encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return "window.CovenantWorlds=null;"


PAGE = PAGE.replace("__WORLDS_JS__", worlds_js())


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


HIGHWAY_CORE = ("node_down", "sweep_red", "source_drift", "watchdog_stale", "manifest_stale", "stale_test_mesh",
                "phone_build_behind_core")


def highway_detail(H):
    """({detector: 'present'|'absent'|'unknown'} for EVERY registered detector, note or None).

    A288 (2026-10-06, his words: "keep expanding the highway"). The orb read seven fixed detectors; the road had
    grown to 25, and eighteen of them -- public_ci_red, mesh_source_split, every one added that day (Tetsu's two,
    sweep currency, a stalled ambassador, the scheduler, Moltbook strikes, failing asks) -- never reached the orb:
    "Highway green" was a reading of 7 of 25. Now: every detector, from the watchdog's own last pass when it is
    fresh (sensing all of them here is most of a cold read, profiled 2026-09-25). When that pass is stale or
    predates a detector, the seven core ones are sensed here and the rest are UNKNOWN -- amber, which is also how
    a watchdog that stopped sensing shows. LOWER-CASE whatever arrives (PC1z6: the page colours by 'present')."""
    names = list(H.DETECTORS)
    seen = H.last_sense()
    if seen is not None and all(k in seen for k in names):
        return {k: str(seen[k] or "unknown").lower() for k in names}, None
    sensed = H.sense(only=list(HIGHWAY_CORE))
    out = {k: str((v or {}).get("state") or "unknown").lower() for k, v in sensed.items()}
    rest = [k for k in names if k not in out]
    for k in rest:
        out[k] = "unknown"
    return out, ("the watchdog's full pass is not fresh here (stale, or older than %d detector(s)); the %d core "
                 "detectors were read now and the rest are unknown" % (len(rest), len(sensed)))


REPO_OWNER = "lawless1987"
REPO_TTL = 300.0
_repo_cache = {"t": 0.0, "rows": None}


def repos_detail(home=None, now=None, run=None):
    """His other repositories as the worlds on the outer ring (A340, 2026-10-13, his words: "implement the other
    repos into the apps also"). Found by DISCOVERY, never by a list: every folder beside this checkout holding a
    `.git`, whose origin is his on GitHub, or another clone on this PC (a local-only repository). Someone else's
    code is left out; a second clone of the same repository counts once (the one with the newest commit); this
    checkout is the system itself, the star's realm, and is not a world of its own.

    Each row: name, last_commit_at (unix seconds), branch, dirty (paths git reports changed, untracked included),
    ahead (commits not on the upstream; None when there is no upstream to compare with), or error. Read from the
    clone only -- no network, so "ahead" is against what this clone last fetched. The names stay on this PC: they
    leave it only in this route's answer, which is tailnet and loopback only."""
    import re
    import time as _t
    now = _t.time() if now is None else now
    if home is None and _repo_cache["rows"] is not None and now - _repo_cache["t"] < REPO_TTL:
        return _repo_cache["rows"]
    if run is None:
        import covenant_quiet
        run = covenant_quiet.run
    base = home or os.path.dirname(HERE)
    try:
        names = sorted(os.listdir(base))
    except OSError:
        return []
    best = {}
    for d in names:
        p = os.path.join(base, d)
        # .git is a FILE in a linked worktree (Sentinel-Witness-trading is one); exists, not isdir
        if not os.path.exists(os.path.join(p, ".git")) or os.path.normcase(os.path.abspath(p)) == os.path.normcase(HERE):
            continue

        def g(*a, p=p):
            try:
                r = run(["git", "-C", p] + list(a), capture_output=True, text=True, timeout=20)
            except Exception:                                    # noqa: BLE001
                return None
            return r.stdout.strip() if r.returncode == 0 else None
        url = g("remote", "get-url", "origin") or ""
        m = re.search(r"github\.com[:/]([^/]+)/([^/\s]+?)(?:\.git)?$", url)
        if m:
            if m.group(1).lower() != REPO_OWNER:
                continue
            name = m.group(2)
        elif url and os.path.isdir(url):
            name = d
        else:
            continue
        if name.lower() == os.path.basename(HERE).lower():
            continue
        row = {"name": name}
        ct = g("log", "-1", "--format=%ct")
        if ct is None:
            row["error"] = "git could not read its history"
        else:
            row["last_commit_at"] = int(ct) if ct.isdigit() else None
            row["branch"] = g("rev-parse", "--abbrev-ref", "HEAD")
            st = g("status", "--porcelain")
            row["dirty"] = len([x for x in (st or "").splitlines() if x.strip()]) if st is not None else None
            ah = g("rev-list", "--count", "@{u}..HEAD")
            row["ahead"] = int(ah) if ah and ah.isdigit() else None
        # a repository's own clone outranks a linked worktree of it (a PR branch has no upstream to read);
        # between two of the same kind, the newer commit wins
        row["_rank"] = (os.path.isdir(os.path.join(p, ".git")), row.get("last_commit_at") or 0)
        prev = best.get(name.lower())
        if prev is None or row["_rank"] > prev["_rank"]:
            best[name.lower()] = row
    rows = sorted(({k: v for k, v in r.items() if k != "_rank"} for r in best.values()), key=lambda r: r["name"].lower())
    if home is None:
        _repo_cache.update(t=now, rows=rows)
    return rows


def heal_detail(path=None, keep=5):
    """The highway's last repairs that RAN (not dry runs), oldest first, from its own ledger (ops/highway.jsonl):
    what the page shows in place of A215's button (A340, his words: "if the self heal works right i shouldn't need
    the button"). Each row: t, remedy, detector, ok (False when the ledger says the remedy did not fix it)."""
    path = path or os.environ.get("COVENANT_HIGHWAY_LEDGER") or os.path.join(HERE, "ops", "highway.jsonl")
    out = []
    try:
        with open(path, "rb") as fh:
            fh.seek(0, 2)
            fh.seek(max(0, fh.tell() - 256 * 1024))
            tail = fh.read().decode("utf-8", "replace")
    except OSError:
        return []
    for ln in tail.splitlines():
        try:
            r = json.loads(ln)
        except ValueError:
            continue
        # A348d (2026-10-14): the highway grades a repair in "outcome" (covenant_highway.apply_remedy, grade_started);
        # no row carries a "fixed" key (0 of 2376, the 10-14 audit), so ok was None for every row and a repair that did not fix
        # read as a plain one. A late grade has no "ran" (it answers a start that ran), so it is read too, at its own time.
        if r.get("remedy") and not r.get("dry_run") and (r.get("ran") or r.get("graded_late")):
            out.append({"t": str(r.get("t") or "")[:19], "remedy": r.get("remedy"), "detector": r.get("detector"),
                        "ok": {"fixed": True, "did not fix": False}.get(r.get("outcome"))})
    return out[-keep:]


FORUM_KINDS = ("reply", "own_post", "tetsu_reply", "tetsu_post", "intro")
FORUM_WINDOW_S = 86400


def forum_detail(rows, now=None):
    """(the last 6 SENT forum rows, {sent, tried, window_h}) over the last FORUM_WINDOW_S.

    A277 (2026-10-06). The Moltbook orb read the last 6 ATTEMPTS and was green when one of them went out
    (the 09-28 rule: "green now means something went out"). A270 made a round try ~200 people, so the last 6
    were nearly always held: on the day free's first reply in weeks went out (13:46Z), the orb read
    "0 of 6 sent" amber. The rule stands; the window it is measured over is now a day, not six rows. Live
    sends only -- a dry run reaches no one."""
    import calendar
    import time as _t
    now = _t.time() if now is None else now
    sent_rows, sent, tried = [], 0, 0
    for r in rows or []:
        if r.get("kind") not in FORUM_KINDS or r.get("dry_run"):
            continue
        at = r.get("at")
        if at is None:
            try:
                at = calendar.timegm(_t.strptime(str(r.get("t", "")), "%Y-%m-%dT%H:%M:%SZ"))
            except ValueError:
                at = None
        if r.get("sent"):
            sent_rows.append(r)
        if at is not None and now - float(at) <= FORUM_WINDOW_S:
            tried += 1
            sent += bool(r.get("sent"))
    shown = [{"t": r.get("t"), "kind": r.get("kind"), "actor": r.get("actor", "free"), "sent": True,
              "to": r.get("author") or r.get("target") or r.get("title"), "text": str(r.get("text") or "")[:160]}
             for r in sent_rows[-6:]]
    return shown, {"sent": sent, "tried": tried, "window_h": FORUM_WINDOW_S // 3600}


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
                    # /health reports `peers` as a COUNT (an int, since the first commit);
                    # len() of it threw, and the bare except below filed every live node
                    # as down (measured 2026-09-25: all three "down" while each answered
                    # in 0.02 s). A list is still counted, if one ever arrives.
                    _p = h.get("peers")
                    _np = len(_p) if isinstance(_p, (list, tuple)) else int(_p or 0)
                    out["mesh"].append({"node_id": h.get("node_id") or "?", "port": port, "version": h.get("version"),
                                        "chain_height": h.get("chain_height"), "peers": _np,
                                        "source": (h.get("source_sha256") or "")[:12], "degraded": bool(h.get("degraded")),
                                        "me": port == 5000 and (h.get("node_id") == self_h["node_id"])})
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
            # A348d: "count" is the day's count in words (covenant_immunity.count_text), which the page shows as is.
            out["immunity"] = {k: st.get(k) for k in ("granted", "paused", "passes_today", "per_day", "count")}
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
            out["detail"]["highway"], note = highway_detail(covenant_highway)
            if note:
                out["detail"]["highway_note"] = note
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
            out["detail"]["forum"], out["detail"]["forum_day"] = forum_detail(covenant_free_will.sends())
        except Exception:                                        # noqa: BLE001
            pass
        try:
            import covenant_teacher_queue
            q, _ = covenant_teacher_queue.pending()
            out["detail"]["queue"] = len(q)
        except Exception:                                        # noqa: BLE001
            pass
        try:
            out["detail"]["healing"] = heal_detail()
        except Exception:                                        # noqa: BLE001
            out["detail"]["healing"] = None
        try:
            out["repos"] = repos_detail()
        except Exception:                                        # noqa: BLE001
            out["repos"] = []
        _cache.update(t=_time.time(), body=out)
        return jsonify(out)
    return True
