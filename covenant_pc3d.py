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
#talk{position:fixed;left:16px;right:16px;bottom:16px;display:flex;gap:8px;align-items:flex-end;flex-wrap:wrap}
#talk textarea{flex:1;min-width:140px;min-height:44px;max-height:160px;resize:vertical;background:#0f1d2e;color:#E7F4EA;border:1px solid #2E8B6E66;border-radius:12px;padding:10px 12px;font:15px system-ui}
#talk button{background:#2E8B6E;color:#fff;border:0;border-radius:12px;padding:12px 16px;font:600 15px system-ui;cursor:pointer}
#talk button:disabled{opacity:0.45;cursor:default}
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
</style></head><body>
<canvas id="scene"></canvas>
<div id="nolib"><div>The 3D library could not be loaded (no internet on this PC right now). The symbol, the state and the talk box still work below.</div></div>
<div id="hud">__SYMBOL__<div class="t"><b>Tetsu · __NODE__</b><small>__VERSION__ · source __SOURCE__ · <span id="live">reading…</span></small></div></div>
<div id="panel"><h3><span id="ptitle">What you clicked</span><button id="pmin" title="minimise">–</button></h3><div id="info">hover a planet to see why it is its colour; click it (or its name) for the details</div></div>
<div id="chatwin" class="min"><div id="chathead"><b>Conversation <span id="chatn"></span></b><button id="chatmin" title="open / minimise (Esc)">▢</button><button id="chatx" title="close (the Show chat button brings it back)">×</button></div><div id="answer"></div></div><div id="tip"></div>
<div id="legend"><b>Colour code</b> (the glow around each planet)<br><i style="background:#2E8B6E"></i>green: measured fine<br><i style="background:#C9A227"></i>amber: not known, or waiting on someone<br><i style="background:#C0392B"></i>red, pulsing: needs attention<br><i style="background:#F4E9B0"></i>small lights: bots, carrying both ways</div>
<div id="talk"><textarea id="q" placeholder="talk to Tetsu (the council answers; the answer is spoken)"></textarea><button id="mic" title="speak to Tetsu instead of typing">Mic</button><button id="chatbtn" title="hide the conversation to see and click every orb; nothing is lost">Hide chat</button><button id="heal" title="Repair what can be repaired, and name what cannot">Self-heal</button><button id="send">Send</button></div>
<script>
const NODE='__NODE__';
// 2026-09-28 ("why aren't the orbs working on my pc and if they are why arent they auto refreshed"):
// the node now serves this page as it is on disk, and the state carries its hash; an open tab whose
// page is older reloads itself -- only while nothing is typed and no answer is on its way.
const PAGESHA='__PAGESHA__';
let state=null, voice={pitch:0.8,rate:0.95};
document.getElementById('chatbtn').onclick=()=>{const off=document.body.classList.toggle('nochat');document.getElementById('chatbtn').textContent=off?'Show chat':'Hide chat';};
async function getState(){try{const r=await fetch('/pc/3d/state');state=await r.json();if(state.page&&state.page!==PAGESHA&&!document.getElementById('q').value&&!(typeof inflight!=='undefined'&&inflight)){location.reload();return;}if(state.voice)voice=state.voice;document.getElementById('live').textContent='height '+(state.self.chain_height??'?')+' · peers '+(state.peers?state.peers.length:0)+(state.immunity&&state.immunity.granted?' · immunity '+(state.immunity.paused?'paused':'on'):'');if(window.onState)window.onState();}catch(e){document.getElementById('live').textContent='state unreadable';}}
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
getState();setInterval(getState,15000);loadHistory();
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
const tetsu=orb('Tetsu',0x4FB08E,0,0);tetsu.scale.setScalar(1.5);tetsu.userData.swarm.scale.setScalar(1.5);
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
function layout(){if(!state)return;const d=state.detail||{};const hw=d.highway||{};
// one Tetsu; the nodes are his cells, each its own orb from its own /health (A, B, C), and the phone's node by its address
const items=[];const mesh=state.mesh||[];
if(mesh.length){for(const m of mesh)items.push({name:'node '+(m.node_id||'?')+(m.me?' (here)':'')+(m.down?' (down)':''),color:m.down?BAD:(m.degraded?UNK:OK),sub:m.down?'down':(m.degraded?'degraded · click for why':'up · height '+(m.chain_height??'?')),detail:m,kind:'node'});}
else items.push({name:NODE+' (this node)',color:statusColor(hw.node_down==='present'?'present':(hw.node_down||'unknown')),sub:'node_down '+(hw.node_down||'unknown'),detail:state.self,kind:'node'});
// the phone's node was drawn a fixed dark green, a colour nothing measured; this node sees it only as a peer address
for(const p of (state.peers||[])){const id=p.node_id||p.name||String(p);if(/100\\./.test(id))items.push({name:'phone node',color:UNK,sub:'a peer; its health is not read here',detail:{peer:id,note:'the node inside his phone, as this node sees it: an address, not a health reading'},kind:'node'});}
const ph=d.phone&&d.phone.last_checkin_hours;
items.push({name:'Phone',color:ph!=null?(ph<1?OK:(ph<24?UNK:BAD)):UNK,sub:ph!=null?'checked in '+ago(ph):'no check-in on record',detail:d.phone,kind:'phone'});
// Moltbook was green whenever a row existed, sent or not (measured 2026-09-28: 6 rows, 0 sent); green now means something went out
// A277 (2026-10-06): the same rule over a day, not over the last six attempts -- a round now tries ~200
const fd=d.forum_day||{},fs=fd.sent||0,ft=fd.tried||0;
items.push({name:'Moltbook',color:fs?OK:UNK,sub:ft?fs+' sent of '+ft+' tried, '+(fd.window_h||24)+' h':'nothing tried in '+(fd.window_h||24)+' h',detail:d.forum,kind:'forum'});
items.push({name:'Money',color:(d.money?(d.money.comfortable?OK:UNK):UNK),sub:d.money?(d.money.comfortable?'comfortable':'comfort not declared'):'not on record',detail:d.money,kind:'money'});
const hp=Object.keys(hw).filter(k=>hw[k]==='present'),hu=Object.keys(hw).filter(k=>hw[k]==='unknown');
items.push({name:'Highway',color:hp.length?BAD:(hu.length?UNK:OK),sub:hp.length?hp.length+' need attention':(hu.length?hu.length+' not known':'all clear'),detail:hw,kind:'highway'});
const sig=items.map(p=>p.name+'|'+p.color+'|'+p.sub).join(';');
if(sig===lastSig){items.forEach((p,i)=>{const o=orbs[i+1];if(o)o.userData.detail=p.detail;});return;}
lastSig=sig;
for(const o of orbs.filter(o=>o!==tetsu)){scene.remove(o);o.material.map.dispose();o.material.dispose();o.userData.atmo.material.dispose();const sw=o.userData.swarm;scene.remove(sw);sw.children[0].geometry.dispose();sw.children[0].material.dispose();}orbs.length=1;hovered=null;
for(const l of links.children){if(l.geometry!==botGeo)l.geometry.dispose();l.material.dispose();}links.clear();traders.length=0;
for(const s of labels.children){if(s.material.map)s.material.map.dispose();s.material.dispose();}labels.clear();
const n=items.length;items.forEach((p,i)=>{const a=(i/n)*Math.PI*2;const o=orb(p.name,p.color,Math.cos(a)*4.4,Math.sin(a)*4.4);o.userData.detail=p.detail;o.userData.kind=p.kind;o.userData.sub=p.sub;o.userData.bad=p.color===BAD;label(p.name,p.sub,o.position);const g=new THREE.BufferGeometry().setFromPoints([o.position,tetsu.position]);links.add(new THREE.Line(g,new THREE.LineBasicMaterial({color:0x2E8B6E,transparent:true,opacity:0.35})));
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
const sel=new THREE.Mesh(new THREE.RingGeometry(0.6,0.66,64),new THREE.MeshBasicMaterial({color:0xffffff,transparent:true,opacity:0.85,side:THREE.DoubleSide,depthWrite:false}));sel.visible=false;scene.add(sel);let selName=null;
const tip=document.getElementById('tip');
function hoverScale(o,on){o.scale.setScalar((o===tetsu?1.5:1)*(on?1.15:1));}
canvas.addEventListener('pointermove',e=>{const h=pick(e),o=h?h.object:null;if(o!==hovered){if(hovered)hoverScale(hovered,false);hovered=o;if(o)hoverScale(o,true);canvas.style.cursor=o?'pointer':'default';}
 if(o){tip.style.display='block';tip.textContent=o.userData.name+(o.userData.sub?'\\n'+o.userData.sub:'')+'\\nclick for details';tip.style.left=Math.min(e.clientX+14,innerWidth-260)+'px';tip.style.top=(e.clientY+14)+'px';}else tip.style.display='none';});
canvas.addEventListener('pointerleave',()=>{tip.style.display='none';});
canvas.addEventListener('pointerdown',e=>{const hit=pick(e);const info=document.getElementById('info');if(!hit){return;}const u=hit.object.userData;const d=(state&&state.detail)||{};document.getElementById('ptitle').textContent=u.name;selName=u.name;const pn=document.getElementById('panel');if(pn.classList.contains('min'))document.getElementById('pmin').click();
if(u.kind==='node'&&u.detail&&u.detail.me&&u.detail.degraded){fetch('/health').then(r=>r.json()).then(h=>{if(document.getElementById('ptitle').textContent===u.name)info.textContent+='\\n\\nwhy, in its own words (/health):\\n- '+(h.warnings||[]).join('\\n- ');}).catch(()=>{});}
if(u.name==='Tetsu'){info.textContent='Tetsu — the one you talk with.\\nvoice pitch '+voice.pitch+' rate '+voice.rate+(state&&state.immunity?'\\nimmunity: '+(state.immunity.granted?(state.immunity.paused?'paused':'on, '+state.immunity.passes_today+' of '+state.immunity.per_day+' today'):'none'):'')+(d.queue!=null?'\\nteacher\\'s queue: '+d.queue+' row(s)':'')+(state&&state.register?'\\n\\nhow he talks: '+state.register:'')+(d.brief?'\\n\\n'+d.brief:'');}
else if(u.kind==='node'){const x=u.detail||{};if(x.peer){info.textContent=u.name+'\\n'+x.peer+'\\n'+x.note;}else{info.textContent=u.name+(x.port?' · port '+x.port:'')+'\\nversion '+(x.version||'?')+'\\nheight '+(x.chain_height??'?')+'\\npeers '+(Array.isArray(x.peers)?x.peers.length:(x.peers??'?'))+'\\nsource '+(x.source||(x.source_sha256?x.source_sha256.slice(0,12):'?'))+(x.degraded?'\\ndegraded: yes':'')+(x.down?'\\nDOWN':'');}}
else if(u.kind==='forum'){const rows=u.detail||[];info.textContent='Moltbook, the last replies that went out (free and Tetsu):\\n'+(rows.length?rows.map(r=>(r.t||'').slice(0,16)+' '+(r.actor||'free')+' '+r.kind+' '+(r.sent?'SENT':'not sent')+' -> '+(r.to||'')+'\\n   '+(r.text||'')).join('\\n'):'(nothing sent yet)');}
else{info.textContent=u.name+'\\n'+fmt(u.detail);}});
function resize(){renderer.setSize(innerWidth,innerHeight,false);cam.aspect=innerWidth/innerHeight;cam.updateProjectionMatrix();}addEventListener('resize',resize);resize();
let t=0;function frame(){t+=0.01;tetsu.position.y=Math.sin(t*2)*0.15;tetsu.userData.swarm.position.y=tetsu.position.y;tetsu.rotation.y+=0.004;
 for(const o of orbs){if(o!==tetsu)o.rotation.y-=0.003;const sw=o.userData.swarm;sw.rotation.y+=sw.userData.speed;if(o.userData.bad)o.userData.atmo.material.opacity=0.2+0.3*(0.5+0.5*Math.sin(t*5));}
 for(const b of traders){const k=(t*0.35+b.userData.ph)%1;b.position.lerpVectors(b.userData.from,b.userData.to,k);}
 const so=selName&&orbs.find(o=>o.userData.name===selName);sel.visible=!!so;if(so){sel.position.copy(so.position);sel.quaternion.copy(cam.quaternion);sel.scale.setScalar(so.scale.x);}
 cam.position.x=Math.sin(t*0.15)*9.5;cam.position.z=Math.cos(t*0.15)*9.5;cam.lookAt(0,-1.6,0);renderer.render(scene,cam);requestAnimationFrame(frame);}frame();
}
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
            want = ["node_down", "sweep_red", "source_drift", "watchdog_stale", "manifest_stale", "stale_test_mesh", "phone_build_behind_core"]
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
            out["detail"]["forum"], out["detail"]["forum_day"] = forum_detail(covenant_free_will.sends())
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
