#!/usr/bin/env python3
"""
dashboard_render.py -- write a local 3D dashboard for the covenant mesh.

WHY IT RENDERS A FILE INSTEAD OF SERVING ONE

A page fetched from disk cannot read http://127.0.0.1:5000 -- a file:// origin
is opaque, so the browser blocks it, and the fix (permissive CORS headers on
the node) would loosen a surface that is deliberately loopback-only. A page
served BY the node could read its own data but not the other node's, for the
same reason.

So this polls both nodes here, in Python, where there is no origin at all, and
writes the answers INLINE into the HTML. The page does no network I/O of any
kind. Consequences worth knowing:

  * it works when a node is DOWN -- and that is exactly when you want to look
    at it. A page that fetches from the node can only show you a spinner.
  * it works with no network, no server, no port, and no resident process.
  * it is a snapshot. The page says how old it is, and turns amber then red as
    that number grows, so a dead renderer cannot masquerade as a calm system.

Run:  python dashboard_render.py            writes dashboard.html
      python dashboard_render.py --open     writes it and opens it
      python dashboard_render.py --demo     writes it with sample data
"""
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "dashboard.html")
NODES = [("A", 5000), ("B", 5020), ("C", 5060)]
WATCHDOG_LOG = os.path.join(HERE, "logs", "watchdog.log")


# --------------------------------------------------------------- collection
def get_health(port, timeout=6):
    try:
        with urllib.request.urlopen(
                "http://127.0.0.1:%d/health" % port, timeout=timeout) as r:
            return json.loads(r.read().decode()), None
    except Exception as e:                                   # noqa: BLE001
        return None, "%s: %s" % (type(e).__name__, str(e)[:80])


def get_anomaly_total(port, timeout=6):
    try:
        with urllib.request.urlopen(
                "http://127.0.0.1:%d/anomalies" % port, timeout=timeout) as r:
            return json.loads(r.read().decode()).get("total_events_retained", 0)
    except Exception:                                        # noqa: BLE001
        return None


def ram():
    """Free and total RAM in MB. Windows first, then Linux, then give up
    honestly rather than guess."""
    try:
        if os.name == "nt":
            import ctypes

            class MS(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong),
                            ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong),
                            ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong),
                            ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong),
                            ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
            m = MS()
            m.dwLength = ctypes.sizeof(MS)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            return int(m.ullAvailPhys / 1048576), int(m.ullTotalPhys / 1048576)
        vals = {}
        with open("/proc/meminfo") as f:
            for line in f:
                k, _, v = line.partition(":")
                if k in ("MemAvailable", "MemTotal"):
                    vals[k] = int(v.split()[0]) // 1024
        return vals.get("MemAvailable", 0), vals.get("MemTotal", 0)
    except Exception:                                        # noqa: BLE001
        return 0, 0


def judge_model():
    """Which model the running nodes actually loaded, read from their own boot
    banner -- not from a .bat, which may not be the one that started them."""
    for name in ("nodeA.log", "nodeB.log"):
        p = os.path.join(HERE, "logs", name)
        try:
            with open(p, encoding="utf8", errors="replace") as f:
                for line in reversed(f.read().splitlines()):
                    m = re.search(r"\[ollama-judge\]\s+(\S+)\s+via", line)
                    if m:
                        return m.group(1)
        except OSError:
            pass
    return None


def watchdog_state():
    """Last tick, whether it ended clean, and the balances it read out of both
    databases. The watchdog is the only thing that compares the two dbs, so
    this is the one place divergence would show."""
    st = {"last": None, "ok": None, "ticks": 0,
          "founder": None, "nodeb": None, "agree": None, "alerts": []}
    try:
        with open(WATCHDOG_LOG, encoding="utf8", errors="replace") as f:
            lines = f.read().splitlines()
    except OSError:
        return st
    st["ticks"] = sum(1 for l in lines if "all checks passed" in l)
    for line in reversed(lines[-400:]):
        ts = line[:20] if line[:4].isdigit() else None
        if st["last"] is None and ts:
            st["last"] = ts.rstrip()
        if st["ok"] is None:
            if "all checks passed" in line:
                st["ok"] = True
            elif "ALERT" in line:
                st["ok"] = False
                st["alerts"].append(line.split("ALERT", 1)[-1].strip()[:150])
        m = re.search(r"founder balance agrees across both dbs:\s*([0-9.]+)", line)
        if m and st["founder"] is None:
            st["founder"] = float(m.group(1))
            st["agree"] = True
        m = re.search(r"nodeB balance agrees across both dbs:\s*([0-9.]+)", line)
        if m and st["nodeb"] is None:
            st["nodeb"] = float(m.group(1))
    st["alerts"] = st["alerts"][:4]
    return st


def collect():
    nodes, links = [], []
    for nid, port in NODES:
        h, err = get_health(port)
        if h is None:
            nodes.append({"id": nid, "port": port, "up": False, "error": err,
                          "warnings": [], "anomaly_kinds": []})
            continue
        nodes.append({
            "id": h.get("node_id", nid), "port": port, "up": True,
            "height": h.get("chain_height"), "peers": h.get("peers"),
            "pending": h.get("pending_transactions"),
            "judge": h.get("judge"), "insecure": h.get("judge_insecure"),
            "keyless": h.get("judge_keyless"), "wsgi": h.get("wsgi"),
            "genesis": (h.get("genesis") or "")[:12],
            "own_genesis": h.get("own_genesis"),
            "degraded": h.get("degraded"), "crisis": h.get("crisis_mode"),
            "alignment": h.get("alignment"),
            "dead_peers": h.get("dead_peers"),
            "heartbeats_skipped": h.get("heartbeats_skipped"),
            "tip_gossip_seen": h.get("tip_gossip_seen"),
            "peer_ahead_seen": h.get("peer_ahead_seen"),
            "anomaly_kinds": h.get("anomaly_kinds") or [],
            "anomalies": get_anomaly_total(port),
            "spike": h.get("spike_detected"),
            "subsystems": h.get("subsystems") or {},
            "warnings": h.get("warnings") or [],
        })
    if len(nodes) == 2:
        both_up = all(n["up"] for n in nodes)
        links.append({"a": nodes[0]["id"], "b": nodes[1]["id"],
                      "ok": both_up and not any(n.get("dead_peers") for n in nodes),
                      "gossip": max((n.get("tip_gossip_seen") or 0) for n in nodes)})
    free_mb, total_mb = ram()
    heights = [n.get("height") for n in nodes if n.get("up")]
    return {
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "generated_local": time.strftime("%a %d %b %H:%M:%S"),
        "generated_epoch": int(time.time()),
        "host": os.environ.get("COMPUTERNAME") or os.uname().nodename,
        "free_mb": free_mb, "total_mb": total_mb,
        "judge_model": judge_model(),
        "nodes": nodes, "links": links,
        "watchdog": watchdog_state(),
        "converged": len(set(heights)) <= 1 if heights else None,
    }


def demo():
    return {
        "generated_utc": "2026-08-23T02:40:00Z",
        "generated_local": "Sat 23 Aug 02:40:00", "generated_epoch": int(time.time()),
        "host": "sales", "free_mb": 8180, "total_mb": 15680,
        "judge_model": "qwen3:8b",
        "nodes": [
            {"id": "A", "port": 5000, "up": True, "height": 3, "peers": 1, "pending": 0,
             "judge": "quorum(local:0,mock_selfreport:0)", "insecure": False,
             "keyless": True, "wsgi": "waitress", "genesis": "00009b31c6c6",
             "own_genesis": True, "degraded": True, "crisis": False, "alignment": 0.5,
             "dead_peers": 0, "heartbeats_skipped": 1, "tip_gossip_seen": 135,
             "peer_ahead_seen": 0, "anomaly_kinds": [], "anomalies": 19, "spike": False,
             "subsystems": {"trading_bridge": True, "neural_bridge": True,
                            "brainflow": False, "code_sandbox": False},
             "warnings": ["ethics gate has no provider key and is failing CLOSED",
                          "node minted its OWN genesis"]},
            {"id": "B", "port": 5020, "up": True, "height": 3, "peers": 1, "pending": 0,
             "judge": "quorum(local:0,mock_selfreport:0)", "insecure": False,
             "keyless": True, "wsgi": "waitress", "genesis": "00009b31c6c6",
             "own_genesis": False, "degraded": True, "crisis": False, "alignment": 0.5,
             "dead_peers": 0, "heartbeats_skipped": 0, "tip_gossip_seen": 134,
             "peer_ahead_seen": 0, "anomaly_kinds": [], "anomalies": 0, "spike": False,
             "subsystems": {"trading_bridge": True, "neural_bridge": True,
                            "brainflow": False, "code_sandbox": False},
             "warnings": ["ethics gate has no provider key and is failing CLOSED"]},
        ],
        "links": [{"a": "A", "b": "B", "ok": True, "gossip": 135}],
        "watchdog": {"last": "2026-08-23T02:39:57Z", "ok": True, "ticks": 431,
                     "founder": 988.0, "nodeb": 12.0, "agree": True, "alerts": []},
        "converged": True,
    }


def render(data, template_path=None, refresh=0):
    tpl = TEMPLATE
    if template_path and os.path.exists(template_path):
        with open(template_path, encoding="utf8") as f:
            tpl = f.read()
    return (tpl
            .replace("/*__DATA__*/null", json.dumps(data, indent=1))
            .replace("/*__REFRESH__*/0", str(int(refresh))))


TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Covenant mesh</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  :root{
    --bg:#080b10; --panel:rgba(14,19,27,.86); --line:rgba(255,255,255,.10);
    --ink:#e8eef6; --dim:#8b9bb0; --up:#35d07f; --warn:#ffb648; --down:#ff5c5c;
    --link:#5aa9ff;
  }
  *{box-sizing:border-box}
  html,body{margin:0;height:100%;background:var(--bg);color:var(--ink);
    font:14px/1.5 "Segoe UI",system-ui,-apple-system,sans-serif;overflow:hidden}
  canvas{display:block}
  .hud{position:fixed;pointer-events:none;z-index:5}
  #top{top:0;left:0;right:0;padding:18px 22px;display:flex;gap:18px;
    align-items:flex-start;justify-content:space-between;
    background:linear-gradient(180deg,rgba(8,11,16,.92),transparent)}
  h1{margin:0;font-size:17px;font-weight:600;letter-spacing:.2px}
  .sub{color:var(--dim);font-size:12.5px;margin-top:3px}
  .age{display:inline-block;padding:2px 9px;border-radius:99px;font-size:11.5px;
    font-weight:600;letter-spacing:.3px;border:1px solid var(--line)}
  .age.fresh{color:var(--up);border-color:rgba(53,208,127,.35);background:rgba(53,208,127,.10)}
  .age.old{color:var(--warn);border-color:rgba(255,182,72,.35);background:rgba(255,182,72,.10)}
  .age.stale{color:var(--down);border-color:rgba(255,92,92,.4);background:rgba(255,92,92,.12)}
  #legend{display:flex;gap:14px;flex-wrap:wrap;justify-content:flex-end;font-size:12px;color:var(--dim)}
  .key{display:flex;align-items:center;gap:6px}
  .dot{width:9px;height:9px;border-radius:50%;box-shadow:0 0 10px currentColor}
  #bottom{left:0;right:0;bottom:0;padding:16px 22px 18px;display:flex;gap:26px;
    flex-wrap:wrap;background:linear-gradient(0deg,rgba(8,11,16,.94),transparent)}
  .stat b{display:block;font-size:11px;font-weight:600;color:var(--dim);
    letter-spacing:.7px;text-transform:uppercase}
  .stat span{font-size:15px;font-variant-numeric:tabular-nums}
  #panel{position:fixed;top:0;right:0;bottom:0;width:340px;z-index:8;
    background:var(--panel);backdrop-filter:blur(14px);border-left:1px solid var(--line);
    padding:22px;overflow:auto;transform:translateX(100%);transition:transform .22s ease}
  #panel.open{transform:none}
  #panel h2{margin:0 0 2px;font-size:20px}
  #panel .port{color:var(--dim);font-size:12.5px;margin-bottom:16px}
  #panel table{width:100%;border-collapse:collapse;font-size:13px}
  #panel td{padding:6px 0;border-bottom:1px solid rgba(255,255,255,.055);vertical-align:top}
  #panel td:first-child{color:var(--dim);width:44%}
  #panel td:last-child{text-align:right;font-variant-numeric:tabular-nums}
  .warn-list{margin:16px 0 0;padding:0;list-style:none}
  .warn-list li{background:rgba(255,182,72,.09);border-left:2px solid var(--warn);
    padding:8px 10px;margin-bottom:7px;font-size:12.5px;color:#f2dcb4;border-radius:0 4px 4px 0}
  .close{position:absolute;top:16px;right:18px;cursor:pointer;color:var(--dim);
    font-size:22px;line-height:1;background:none;border:0}
  .close:hover{color:var(--ink)}
  #banner{position:fixed;top:0;left:0;right:0;z-index:9;padding:11px 22px;
    font-weight:600;font-size:13px;display:none;text-align:center}
  #banner.show{display:block}
  #reset{position:fixed;left:22px;bottom:96px;z-index:6;pointer-events:auto;
    background:rgba(255,255,255,.05);border:1px solid var(--line);color:var(--dim);
    padding:7px 13px;border-radius:7px;cursor:pointer;font-size:12px}
  #reset:hover{color:var(--ink);background:rgba(255,255,255,.09)}
  #hint{position:fixed;left:50%;transform:translateX(-50%);bottom:96px;z-index:6;
    color:var(--dim);font-size:12px;opacity:.75}
</style></head><body>
<div id="banner"></div>
<div class="hud" id="top">
  <div>
    <h1>Covenant mesh <span id="age" class="age fresh">live</span></h1>
    <div class="sub" id="subtitle">—</div>
  </div>
  <div id="legend">
    <div class="key"><i class="dot" style="color:#35d07f;background:#35d07f"></i>healthy</div>
    <div class="key"><i class="dot" style="color:#ffb648;background:#ffb648"></i>degraded</div>
    <div class="key"><i class="dot" style="color:#ff5c5c;background:#ff5c5c"></i>down</div>
  </div>
</div>
<button id="reset">reset view</button>
<div id="hint">drag to turn · scroll to zoom · click a node</div>
<div class="hud" id="bottom"></div>
<aside id="panel"><button class="close" id="close">×</button><div id="panelBody"></div></aside>
<script src="vendor/three.min.js"></script>
<script>
const DATA = /*__DATA__*/null;

/* ---------------------------------------------------------------- helpers */
const COL = {up:0x35d07f, warn:0xffb648, down:0xff5c5c, link:0x5aa9ff};
function stateOf(n){
  if(!n.up) return "down";
  if(n.crisis || n.insecure) return "down";
  if(n.degraded || (n.warnings||[]).length || n.dead_peers) return "warn";
  return "up";
}
const HEX = {up:"#35d07f", warn:"#ffb648", down:"#ff5c5c"};

/* ------------------------------------------------------------------ scene */
const scene = new THREE.Scene();
scene.fog = new THREE.FogExp2(0x080b10, 0.021);
const camera = new THREE.PerspectiveCamera(46, innerWidth/innerHeight, 0.1, 400);
const renderer = new THREE.WebGLRenderer({antialias:true});
renderer.setPixelRatio(Math.min(devicePixelRatio,2));
renderer.setSize(innerWidth, innerHeight);
document.body.appendChild(renderer.domElement);

scene.add(new THREE.AmbientLight(0x8899bb, 0.55));
const key = new THREE.DirectionalLight(0xffffff, 0.85); key.position.set(6,10,7); scene.add(key);
const rim = new THREE.DirectionalLight(0x5aa9ff, 0.5); rim.position.set(-8,-3,-6); scene.add(rim);

/* a floor grid gives the eye something to judge depth against */
const grid = new THREE.GridHelper(60, 30, 0x1d2836, 0x141c27);
grid.position.y = -7; scene.add(grid);

/* ------------------------------------------------------------------ nodes */
function label(text, sub){
  const c = document.createElement("canvas"), s = 4;
  c.width = 256*s; c.height = 96*s;
  const g = c.getContext("2d"); g.scale(s,s);
  g.font = "600 44px Segoe UI, system-ui, sans-serif"; g.fillStyle = "#eef4fb";
  g.textAlign = "center"; g.fillText(text, 128, 44);
  g.font = "500 20px Segoe UI, system-ui, sans-serif"; g.fillStyle = "#8b9bb0";
  g.fillText(sub, 128, 72);
  const t = new THREE.CanvasTexture(c); t.needsUpdate = true;
  const sp = new THREE.Sprite(new THREE.SpriteMaterial({map:t, transparent:true, depthWrite:false}));
  sp.scale.set(4.6, 1.72, 1);
  return sp;
}

const nodeObjs = [];
const N = DATA.nodes.length;
DATA.nodes.forEach((n, i) => {
  const st = stateOf(n), col = COL[st];
  const ang = (i / Math.max(N,1)) * Math.PI * 2;
  const R = N > 1 ? 6.8 : 0;
  const pos = new THREE.Vector3(Math.cos(ang)*R, 0, Math.sin(ang)*R);

  const g = new THREE.Group(); g.position.copy(pos);
  const core = new THREE.Mesh(
    new THREE.IcosahedronGeometry(1.95, 2),
    new THREE.MeshStandardMaterial({color:col, emissive:col, emissiveIntensity:.42,
      metalness:.25, roughness:.35, flatShading:true}));
  g.add(core);
  const halo = new THREE.Mesh(
    new THREE.SphereGeometry(2.65, 28, 20),
    new THREE.MeshBasicMaterial({color:col, transparent:true, opacity:.09}));
  g.add(halo);
  /* one ring per block in the chain -- height you can count without reading */
  const h = n.up ? (n.height||0) : 0;
  for(let k=0;k<Math.min(h,8);k++){
    const r = new THREE.Mesh(new THREE.TorusGeometry(3.3+k*0.42, 0.035, 8, 64),
      new THREE.MeshBasicMaterial({color:col, transparent:true, opacity:.30-k*0.022}));
    r.rotation.x = Math.PI/2; g.add(r);
  }
  const lab = label(n.id, n.up ? ("height "+h+" · "+(n.peers||0)+" peer"+((n.peers==1)?"":"s")) : "DOWN");
  lab.position.y = 4.15; g.add(lab);

  g.userData = {node:n, core, halo, state:st, base:pos.clone(), phase:Math.random()*6.28};
  scene.add(g); nodeObjs.push(g);
});

/* ------------------------------------------------------------------ links */
const pulses = [];
DATA.links.forEach(l => {
  const A = nodeObjs.find(o=>o.userData.node.id===l.a);
  const B = nodeObjs.find(o=>o.userData.node.id===l.b);
  if(!A||!B) return;
  const col = l.ok ? COL.link : COL.down;
  const geo = new THREE.BufferGeometry().setFromPoints([A.position, B.position]);
  scene.add(new THREE.Line(geo, new THREE.LineBasicMaterial({color:col, transparent:true, opacity:.75})));
  /* a bead travelling the link: gossip you can see, not a number you decode */
  const bead = new THREE.Mesh(new THREE.SphereGeometry(0.26, 16, 12),
    new THREE.MeshBasicMaterial({color:col}));
  scene.add(bead);
  pulses.push({bead, a:A.position, b:B.position, t:Math.random(), ok:l.ok});
});

/* ---------------------------------------------------------------- camera  */
let dist = 29, yaw = 0.55, pitch = 0.34, drag = null, idle = 0;
/* the view survives an auto-refresh: it rides in the URL hash, which needs
   no storage and works from file:// where storage may be denied. */
(function restoreCam(){
  const m = (location.hash||"").slice(1).split(",").map(Number);
  if(m.length===3 && m.every(v=>isFinite(v))){ dist=m[0]; yaw=m[1]; pitch=m[2]; idle=-1e9; }
})();
function saveCam(){
  try{ location.hash = [dist,yaw,pitch].map(v=>v.toFixed(3)).join(","); }catch(e){}
}
function place(){
  camera.position.set(
    dist*Math.cos(pitch)*Math.sin(yaw), dist*Math.sin(pitch), dist*Math.cos(pitch)*Math.cos(yaw));
  camera.lookAt(0,0,0);
}
place();
const el = renderer.domElement;
el.addEventListener("pointerdown", e => {drag = {x:e.clientX, y:e.clientY}; idle = 0;});
addEventListener("pointerup", () => drag = null);
addEventListener("pointermove", e => {
  if(!drag) return;
  yaw   -= (e.clientX-drag.x)*0.006;
  pitch  = Math.max(-1.35, Math.min(1.35, pitch + (e.clientY-drag.y)*0.005));
  drag = {x:e.clientX, y:e.clientY}; idle = 0; place();
});
el.addEventListener("wheel", e => {
  e.preventDefault();
  dist = Math.max(11, Math.min(70, dist + e.deltaY*0.03)); idle = 0; place();
}, {passive:false});
document.getElementById("reset").onclick = () => {
  dist=29; yaw=0.55; pitch=0.34; idle=0; place(); saveCam();
};

/* ----------------------------------------------------------------- picking */
const ray = new THREE.Raycaster(), mouse = new THREE.Vector2();
el.addEventListener("click", e => {
  mouse.x = (e.clientX/innerWidth)*2-1; mouse.y = -(e.clientY/innerHeight)*2+1;
  ray.setFromCamera(mouse, camera);
  const hit = ray.intersectObjects(nodeObjs.map(o=>o.userData.core))[0];
  if(hit) show(nodeObjs.find(o=>o.userData.core===hit.object).userData.node);
});

const panel = document.getElementById("panel");
document.getElementById("close").onclick = () => panel.classList.remove("open");
function row(k,v){ return v===undefined||v===null||v==="" ? "" :
  "<tr><td>"+k+"</td><td>"+v+"</td></tr>"; }
function show(n){
  const st = stateOf(n), sub = n.subsystems||{};
  let h = "<h2 style='color:"+HEX[st]+"'>node "+n.id+"</h2><div class='port'>127.0.0.1:"+n.port+
          " · "+(n.up?"answering":"not answering")+"</div>";
  if(!n.up){
    h += "<ul class='warn-list'><li>"+(n.error||"no response from /health")+"</li></ul>";
  } else {
    h += "<table>"
      + row("chain height", n.height) + row("peers", n.peers)
      + row("pending tx", n.pending) + row("genesis", n.genesis + (n.own_genesis?" (own)":""))
      + row("judge", n.judge) + row("insecure judge", n.insecure ? "YES" : "no")
      + row("wsgi", n.wsgi) + row("alignment", n.alignment)
      + row("dead peers", n.dead_peers) + row("heartbeats skipped", n.heartbeats_skipped)
      + row("tip gossip seen", n.tip_gossip_seen) + row("peer ahead seen", n.peer_ahead_seen)
      + row("anomalies retained", n.anomalies)
      + row("anomaly kinds", (n.anomaly_kinds||[]).join(", ") || "none")
      + row("trading bridge", sub.trading_bridge===undefined?null:(sub.trading_bridge?"on":"off"))
      + row("code sandbox", sub.code_sandbox===undefined?null:(sub.code_sandbox?"available":"unavailable"))
      + "</table>";
    if((n.warnings||[]).length)
      h += "<ul class='warn-list'>"+n.warnings.map(w=>"<li>"+w+"</li>").join("")+"</ul>";
  }
  document.getElementById("panelBody").innerHTML = h;
  panel.classList.add("open");
}

/* -------------------------------------------------------------------- HUD */
const wd = DATA.watchdog||{}, down = DATA.nodes.filter(n=>!n.up);
document.getElementById("subtitle").textContent =
  DATA.host + " · " + DATA.generated_local + " · judge " + (DATA.judge_model||"unknown");

function stat(k,v,c){ return "<div class='stat'><b>"+k+"</b><span"+(c?" style='color:"+c+"'":"")+">"+v+"</span></div>"; }
document.getElementById("bottom").innerHTML =
  stat("nodes up", (DATA.nodes.length-down.length)+" / "+DATA.nodes.length, down.length?HEX.down:HEX.up)
+ stat("converged", DATA.converged===null?"—":(DATA.converged?"yes":"NO"), DATA.converged===false?HEX.down:null)
+ stat("founder balance", wd.founder===null||wd.founder===undefined?"—":wd.founder, wd.agree?HEX.up:HEX.warn)
+ stat("node B balance", wd.nodeb===null||wd.nodeb===undefined?"—":wd.nodeb)
+ stat("watchdog", wd.ok===null||wd.ok===undefined?"—":(wd.ok?"all checks passed":"ALERT"), wd.ok===false?HEX.down:(wd.ok?HEX.up:null))
+ stat("watchdog ticks", wd.ticks||0)
+ stat("free ram", DATA.free_mb ? (DATA.free_mb/1024).toFixed(1)+" / "+(DATA.total_mb/1024).toFixed(1)+" GB" : "—",
       (DATA.free_mb && DATA.free_mb < 5300) ? HEX.warn : null);

const banner = document.getElementById("banner");
if(down.length){
  banner.className = "show";
  banner.style.background = "rgba(255,92,92,.16)";
  banner.style.color = "#ffd0d0";
  banner.style.borderBottom = "1px solid rgba(255,92,92,.4)";
  banner.textContent = down.map(n=>"node "+n.id+" on "+n.port+" is not answering").join("  ·  ");
} else if((wd.alerts||[]).length){
  banner.className = "show";
  banner.style.background = "rgba(255,182,72,.14)";
  banner.style.color = "#ffe3b0";
  banner.style.borderBottom = "1px solid rgba(255,182,72,.35)";
  banner.textContent = "watchdog: " + wd.alerts[0];
}

/* the snapshot's own age, so a dead renderer cannot look like a calm system */
const ageEl = document.getElementById("age");
function tickAge(){
  const s = Math.max(0, Math.floor(Date.now()/1000) - DATA.generated_epoch);
  const txt = s<90 ? s+"s ago" : s<5400 ? Math.round(s/60)+"m ago" : Math.round(s/3600)+"h ago";
  ageEl.textContent = txt;
  ageEl.className = "age " + (s<180 ? "fresh" : s<900 ? "old" : "stale");
}
tickAge(); setInterval(tickAge, 1000);

/* ---------------------------------------------------------------- refresh */
/* Set only by --watch. A refresh is a full reload of a file the renderer has
   rewritten underneath us, so it shows new data without the page ever
   touching the network. It waits while you are dragging, so it cannot yank
   the view out from under your hand. */
const REFRESH = /*__REFRESH__*/0;
if(REFRESH > 0){
  setInterval(() => { if(!drag){ saveCam(); location.reload(); } }, REFRESH*1000);
}

/* ------------------------------------------------------------------ frame */
let t0 = performance.now();
(function frame(now){
  const dt = Math.min(0.05, (now-t0)/1000); t0 = now;
  idle += dt;
  if(idle > 4 && !drag){ yaw += dt*0.06; place(); }          /* drifts when left alone */
  nodeObjs.forEach(o => {
    const u = o.userData;
    u.phase += dt * (u.state==="down" ? 0.6 : 1.6);
    o.position.y = u.base.y + Math.sin(u.phase)*0.22;         /* breathing, not spinning */
    u.core.rotation.y += dt*0.25;
    u.halo.scale.setScalar(1 + Math.sin(u.phase)*0.035);
    u.core.material.emissiveIntensity = 0.42 + Math.sin(u.phase)*(u.state==="down"?0.22:0.10);
  });
  pulses.forEach(p => {
    p.t = (p.t + dt*(p.ok?0.28:0.06)) % 1;
    p.bead.position.lerpVectors(p.a, p.b, p.t);
    p.bead.material.opacity = p.ok ? 1 : 0.3;
  });
  renderer.render(scene, camera);
  requestAnimationFrame(frame);
})(performance.now());

addEventListener("resize", () => {
  camera.aspect = innerWidth/innerHeight; camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});
</script></body></html>
"""


def arg_int(flag, default):
    """--watch, or --watch 30. Returns default for the bare flag."""
    if flag not in sys.argv:
        return 0
    i = sys.argv.index(flag)
    if i + 1 < len(sys.argv):
        try:
            return max(5, int(sys.argv[i + 1]))
        except ValueError:
            pass
    return default


def write_once(refresh):
    data = demo() if "--demo" in sys.argv else collect()
    html = render(data, refresh=refresh)
    with open(OUT, "w", encoding="utf8") as f:
        f.write(html)
    return data, html


def main():
    refresh = arg_int("--watch", 20)
    data, html = write_once(refresh)
    up = sum(1 for n in data["nodes"] if n["up"])
    print("wrote %s  (%d bytes)" % (OUT, len(html)))
    print("  nodes up   : %d/%d" % (up, len(data["nodes"])))
    print("  generated  : %s" % data["generated_local"])
    if not os.path.exists(os.path.join(HERE, "vendor", "three.min.js")):
        print("  WARNING: vendor/three.min.js is missing -- the page will be blank.")
    if "--open" in sys.argv:
        try:
            os.startfile(OUT)                                # noqa: E501  (Windows)
        except AttributeError:
            subprocess.run(["xdg-open", OUT], check=False)

    if not refresh:
        return 0

    # --watch: keep rewriting the file the open page reloads. One process, one
    # HTTP poll per node per cycle, no port, no server. Ctrl-C or closing the
    # window stops it and the page then shows its own age going stale, which
    # is the honest outcome -- it never pretends to be live when it is not.
    print("\n  watching: rewriting every %ds. Close this window to stop." % refresh)
    try:
        while True:
            time.sleep(refresh)
            data, _ = write_once(refresh)
            up = sum(1 for n in data["nodes"] if n["up"])
            print("  %s  nodes up %d/%d" % (data["generated_local"][11:19], up,
                                            len(data["nodes"])))
    except KeyboardInterrupt:
        print("\n  stopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
