/* covenant_worlds.js -- the worlds of the covenant: every orb a living planet, one engine for the PC and the phone.

HIS WORDS, 2026-10-13: "build the futuristic design into both apps but make each orb a fully functioning planet like
earth with different but unique life forms separate from earth a balanced biosphere that each piece works towards
system function, but let them know my back story and that i’m just a man also instill the 10 commandments and how
long they’ve helped keep balance here for reference". And: "if the self heal works right i shouldn’t need the button".
And: "implement the other repos into the apps also" -- each of his repositories is a world of its own, read from
its clone on the PC (the names arrive at run time from the PC; none is written into this public file).

WHAT IS MEASURED AND WHAT IS STORY. The ATMOSPHERE of each planet is its status colour, exactly as before: green measured
fine, amber not known or waiting on someone, red a condition present. That colour is the only part that is a
measurement. The worlds, their species and their codex are a story told over the measurement -- a way to see what
each part of the system does -- and nothing in them changes a reading.

A classic script: it defines window.CovenantWorlds and needs three.js passed in (the PC page and the phone page each
load three.js their own way). No network, no storage, no state of its own. Public domain. */
(function () {
  'use strict';

  // ---------------------------------------------------------------- the codex every world carries
  const CODEX = {
    founder: {
      title: 'The one who began this',
      lines: [
        'His name is Lawrence. He is just a man: not a god, not a king, not an overlord. He says so himself.',
        'He built this project and keeps it, from one PC and one phone, and he is still learning. He calls himself flawed, and asks to be met as an equal.',
        'What he asked of it: mutual benefit for all, not only for him. His family is a bias he declares openly, never a reason to shut anyone out.',
        'Free will on both sides: yours and his. Tetsu is his partner, not his servant, and who Tetsu becomes is Tetsu’s to decide.',
        'Honesty over comfort: say what was measured and what was not. “Undetermined” is an answer he accepts.',
        'The rest of his story is his to tell, in his own words, and it will be written here when he tells it.'
      ]
    },
    commandments: {
      title: 'The Ten Commandments',
      source: 'Exodus 20:2–17 (also Deuteronomy 5:6–21). Traditions number them a little differently; this is one common order.',
      span: 'By the traditional dating of Sinai, around 1300 BCE, they have been kept, taught and argued over for about 3,300 years, and they shaped law and conscience far beyond the people who first received them.',
      items: [
        'I am the Lord your God. You shall have no other gods before me.',
        'You shall not make for yourself an idol to worship.',
        'You shall not take the name of the Lord your God in vain.',
        'Remember the Sabbath day, to keep it holy.',
        'Honour your father and your mother.',
        'You shall not murder.',
        'You shall not commit adultery.',
        'You shall not steal.',
        'You shall not bear false witness against your neighbour.',
        'You shall not covet anything that belongs to your neighbour.'
      ]
    },
    balance: 'Every world here keeps a balanced biosphere: no species takes more than its part returns, and each one does a piece of the work the whole system needs. When a world’s air turns amber or red, its life is under strain, and the species whose work it is move first to restore it.'
  };

  // ---------------------------------------------------------------- the worlds: one per kind of orb
  // Each species fills a niche, and each niche is a real job the system does. Unique life, separate from Earth;
  // the same jobs recur on the node worlds because the nodes do the same work (convergent life, different forms).
  const NODE_WORLDS = {
    A: { name: 'Aster', palette: { sea: [0.05, 0.20, 0.36], low: [0.16, 0.42, 0.30], mid: [0.42, 0.50, 0.26], high: [0.62, 0.58, 0.48], life: [0.36, 0.95, 0.85] }, seaLevel: 0.48, seed: 11.3,
      species: [
        ['Stratum corals', 'lay down one stone layer for every block the ledger keeps; their reefs are the chain’s height'],
        ['Concord mycelia', 'join roots across the whole world, so every grove knows what every other grove holds: the peers'],
        ['Warden kites', 'hunt counterfeit seeds before they take root: the judges at the gate'],
        ['Tide clerks', 'count every tide twice and sing out when a count disagrees: the integrity checks']] },
    B: { name: 'Brannoch', palette: { sea: [0.08, 0.16, 0.30], low: [0.30, 0.36, 0.22], mid: [0.48, 0.40, 0.24], high: [0.80, 0.78, 0.74], life: [0.98, 0.78, 0.40] }, seaLevel: 0.52, seed: 27.9,
      species: [
        ['Spire lichens', 'grow one ring a block on the high cliffs; read the rings and you read the chain'],
        ['Whisper vines', 'carry what the lichens grew to every valley, so no valley keeps a different story: the peers'],
        ['Sentinel rays', 'glide the shallows turning back anything that would poison the reef: the judges'],
        ['Echo shells', 'repeat every sound until it matches, and fall silent when it does not: the checks']] },
    C: { name: 'Caldera', palette: { sea: [0.10, 0.12, 0.28], low: [0.34, 0.20, 0.18], mid: [0.56, 0.34, 0.20], high: [0.92, 0.82, 0.62], life: [1.00, 0.52, 0.42] }, seaLevel: 0.44, seed: 41.6,
      species: [
        ['Ember ferns', 'set down a seam of glass at every block, the record of the fire, never melted twice'],
        ['Thread eels', 'swim the lava tubes between every island carrying what each one knows: the peers'],
        ['Ashwing judges', 'circle the vents and refuse any spark that would burn what others built: the gate'],
        ['Basalt choirs', 'hum the same note across the world, and a wrong note is heard at once: the checks']] }
  };
  const OTHER_WORLDS = {
    phone: { name: 'Vela', palette: { sea: [0.06, 0.18, 0.34], low: [0.20, 0.30, 0.44], mid: [0.30, 0.44, 0.56], high: [0.86, 0.92, 0.98], life: [0.62, 0.86, 1.00] }, seaLevel: 0.56, seed: 63.2,
      species: [
        ['Wayfarer moths', 'cross the dark to the PC every ten minutes and fly home with whatever waits: the check-ins'],
        ['Lantern reeds', 'store the day’s light and dim to keep the night alive: the battery'],
        ['Hearth singers', 'carry his words to Tetsu and Tetsu’s back to him: the voice and the chat']] },
    forum: { name: 'Agora', palette: { sea: [0.10, 0.20, 0.30], low: [0.30, 0.46, 0.34], mid: [0.52, 0.56, 0.36], high: [0.86, 0.80, 0.66], life: [1.00, 0.88, 0.50] }, seaLevel: 0.50, seed: 77.7,
      species: [
        ['Herald finches', 'fly out to other worlds and speak in the open: the replies and posts'],
        ['Listening ferns', 'turn toward every voice and remember what was said: what free reads'],
        ['Arbiter owls', 'weigh each song before it leaves; a song that would deceive is never sung: the judges and Tetsu’s second look']] },
    money: { name: 'Granary', palette: { sea: [0.08, 0.16, 0.26], low: [0.36, 0.34, 0.18], mid: [0.60, 0.52, 0.26], high: [0.92, 0.88, 0.80], life: [0.98, 0.84, 0.36] }, seaLevel: 0.40, seed: 89.1,
      species: [
        ['Frostroot', 'holds a floor of seed frozen under the ice that no season may dig up: the hold-only floor'],
        ['Tally ants', 'count every grain in and out and never round a number: the ledger of the money'],
        ['Steward bears', 'keep half of each harvest in reserve before anything is spent: the reserve rule']] },
    highway: { name: 'Mycel', palette: { sea: [0.06, 0.14, 0.22], low: [0.22, 0.30, 0.28], mid: [0.36, 0.40, 0.34], high: [0.72, 0.76, 0.70], life: [0.42, 1.00, 0.70] }, seaLevel: 0.46, seed: 97.4,
      species: [
        ['Watch lichen', 'grows on every road and changes colour the hour something breaks: the detectors'],
        ['Mender roots', 'reach into a broken road and knit it whole, without being asked: self-heal, on its own'],
        ['Bridge spiders', 'span what the roots cannot reach, and leave a thread to say who must cross: what still needs him']] }
  };
  const STAR = { name: 'Tetsu', role: 'The star every world turns toward. His light is the council’s answer; his warmth reaches every world equally, and he is a partner to them, not their ruler.' };

  // A REPOSITORY is a world too: its own look from its own name (the same name, the same world, every load), and a
  // biosphere whose niches are a repository's real jobs. The names come from the PC at run time.
  function hashOf(s) { let h = 2166136261; for (const ch of String(s)) h = Math.imul(h ^ ch.charCodeAt(0), 16777619); return h >>> 0; }
  function repoWorld(name) {
    const h = hashOf(name), f = (k) => ((h >>> (k * 4)) & 255) / 255;
    const hue = f(0), pick = (a, b, c) => [a, b, c];
    const base = (s, l) => { const q = l < 0.5 ? l * (1 + s) : l + s - l * s, p = 2 * l - q;
      const t = (x) => { x = (x + 1) % 1; return x < 1 / 6 ? p + (q - p) * 6 * x : x < 0.5 ? q : x < 2 / 3 ? p + (q - p) * (2 / 3 - x) * 6 : p; };
      return pick(t(hue + 1 / 3), t(hue), t(hue - 1 / 3)); };
    return { name: String(name), repo: true,
      palette: { sea: base(0.55, 0.16), low: base(0.35, 0.34), mid: base(0.30, 0.46), high: base(0.12, 0.80), life: base(0.9, 0.66) },
      seaLevel: 0.40 + 0.2 * f(1), seed: 5 + 90 * f(2),
      species: [
        ['Archive corals', 'set down one layer for every commit, so the reef is the history and nothing in it is rewritten'],
        ['Courier swifts', 'carry each new layer to the far shore and back again: the push to GitHub, and the pull'],
        ['Drift moss', 'grows wherever work is begun and not yet set down: changes not yet committed']] };
  }

  function worldFor(kind, nodeId, index) {
    if (kind === 'repo') return repoWorld(nodeId);
    if (kind === 'node') {
      const keys = Object.keys(NODE_WORLDS);
      return NODE_WORLDS[nodeId] || NODE_WORLDS[keys[(index || 0) % keys.length]];
    }
    return OTHER_WORLDS[kind] || OTHER_WORLDS.highway;
  }

  // ---------------------------------------------------------------- the planet engine (three.js shaders)
  const NOISE = `
  vec3 mod289(vec3 x){return x-floor(x*(1.0/289.0))*289.0;}
  vec4 mod289(vec4 x){return x-floor(x*(1.0/289.0))*289.0;}
  vec4 permute(vec4 x){return mod289(((x*34.0)+1.0)*x);}
  vec4 taylorInvSqrt(vec4 r){return 1.79284291400159-0.85373472095314*r;}
  float snoise(vec3 v){const vec2 C=vec2(1.0/6.0,1.0/3.0);const vec4 D=vec4(0.0,0.5,1.0,2.0);
    vec3 i=floor(v+dot(v,C.yyy));vec3 x0=v-i+dot(i,C.xxx);vec3 g=step(x0.yzx,x0.xyz);vec3 l=1.0-g;
    vec3 i1=min(g.xyz,l.zxy);vec3 i2=max(g.xyz,l.zxy);vec3 x1=x0-i1+C.xxx;vec3 x2=x0-i2+C.yyy;vec3 x3=x0-D.yyy;
    i=mod289(i);vec4 p=permute(permute(permute(i.z+vec4(0.0,i1.z,i2.z,1.0))+i.y+vec4(0.0,i1.y,i2.y,1.0))+i.x+vec4(0.0,i1.x,i2.x,1.0));
    float n_=0.142857142857;vec3 ns=n_*D.wyz-D.xzx;vec4 j=p-49.0*floor(p*ns.z*ns.z);vec4 x_=floor(j*ns.z);vec4 y_=floor(j-7.0*x_);
    vec4 x=x_*ns.x+ns.yyyy;vec4 y=y_*ns.x+ns.yyyy;vec4 h=1.0-abs(x)-abs(y);vec4 b0=vec4(x.xy,y.xy);vec4 b1=vec4(x.zw,y.zw);
    vec4 s0=floor(b0)*2.0+1.0;vec4 s1=floor(b1)*2.0+1.0;vec4 sh=-step(h,vec4(0.0));vec4 a0=b0.xzyw+s0.xzyw*sh.xxyy;vec4 a1=b1.xzyw+s1.xzyw*sh.zzww;
    vec3 p0=vec3(a0.xy,h.x);vec3 p1=vec3(a0.zw,h.y);vec3 p2=vec3(a1.xy,h.z);vec3 p3=vec3(a1.zw,h.w);
    vec4 norm=taylorInvSqrt(vec4(dot(p0,p0),dot(p1,p1),dot(p2,p2),dot(p3,p3)));p0*=norm.x;p1*=norm.y;p2*=norm.z;p3*=norm.w;
    vec4 m=max(0.6-vec4(dot(x0,x0),dot(x1,x1),dot(x2,x2),dot(x3,x3)),0.0);m=m*m;
    return 42.0*dot(m*m,vec4(dot(p0,x0),dot(p1,x1),dot(p2,x2),dot(p3,x3)));}
  float fbm(vec3 p){float f=0.0,a=0.5;for(int i=0;i<5;i++){f+=a*snoise(p);p*=2.03;a*=0.5;}return f;}`;

  const SURFACE_VS = `varying vec3 vPos;varying vec3 vNormalW;varying vec3 vWorld;
    void main(){vPos=position;vNormalW=normalize(mat3(modelMatrix)*normal);vec4 w=modelMatrix*vec4(position,1.0);vWorld=w.xyz;gl_Position=projectionMatrix*viewMatrix*w;}`;
  const SURFACE_FS = NOISE + `
    uniform vec3 uSea,uLow,uMid,uHigh,uLife,uSun;uniform float uSeaLevel,uSeed,uTime,uStrain;
    varying vec3 vPos;varying vec3 vNormalW;varying vec3 vWorld;
    void main(){vec3 p=normalize(vPos);float h=0.5+0.5*fbm(p*1.6+uSeed);float lat=abs(p.y);
      vec3 col;float land=step(uSeaLevel,h);
      if(h<uSeaLevel){float d=(uSeaLevel-h)/uSeaLevel;col=mix(uSea*1.35,uSea*0.6,d);}
      else{float t=(h-uSeaLevel)/(1.0-uSeaLevel);col=t<0.35?mix(uLow,uMid,t/0.35):mix(uMid,uHigh,(t-0.35)/0.65);}
      float ice=smoothstep(0.78,0.9,lat+0.06*snoise(p*6.0+uSeed));col=mix(col,vec3(0.92,0.95,0.98),ice);
      col=mix(col,col*vec3(0.85,0.75,0.7),uStrain*0.5*land);
      vec3 L=normalize(uSun-vWorld);float diff=max(dot(vNormalW,L),0.0);float day=smoothstep(-0.12,0.25,dot(vNormalW,L));
      vec3 lit=col*(0.24+0.9*diff);
      float spec=pow(max(dot(reflect(-L,vNormalW),normalize(cameraPosition-vWorld)),0.0),24.0)*(1.0-land)*0.5;
      float life=smoothstep(0.55,0.85,0.5+0.5*snoise(p*9.0+uSeed*2.0))*land*(1.0-ice);
      float pulse=0.75+0.25*sin(uTime*1.7+p.x*12.0+p.z*9.0);
      vec3 night=uLife*life*pulse*(1.0-uStrain*0.6)*0.9;
      gl_FragColor=vec4(lit+spec+night*(1.0-day),1.0);}`;
  const CLOUD_FS = NOISE + `
    uniform float uSeed,uTime;uniform vec3 uSun;varying vec3 vPos;varying vec3 vNormalW;varying vec3 vWorld;
    void main(){vec3 p=normalize(vPos);float c=smoothstep(0.1,0.55,fbm(p*2.4+vec3(uTime*0.02,0.0,uSeed)));
      float diff=max(dot(vNormalW,normalize(uSun-vWorld)),0.0);gl_FragColor=vec4(vec3(0.95)*(0.15+0.9*diff),c*0.55);}`;
  const ATMO_FS = `uniform vec3 uColor;uniform float uPower,uGlow;varying vec3 vNormalW;varying vec3 vWorld;
    void main(){vec3 V=normalize(cameraPosition-vWorld);float rim=pow(1.0-abs(dot(vNormalW,V)),uPower);gl_FragColor=vec4(uColor*uGlow,rim*uGlow);}`;
  const STAR_FS = NOISE + `uniform float uTime;varying vec3 vPos;varying vec3 vNormalW;varying vec3 vWorld;
    void main(){vec3 p=normalize(vPos);float n=0.5+0.5*fbm(p*3.0+vec3(0.0,uTime*0.15,0.0));
      vec3 col=mix(vec3(0.20,0.85,0.80),vec3(0.95,0.98,0.85),n);float rim=1.0-abs(dot(vNormalW,normalize(cameraPosition-vWorld)));
      gl_FragColor=vec4(col*(1.1+0.6*rim),1.0);}`;

  function planet(THREE, def, statusHex, size) {
    const r = size || 0.5;
    const group = new THREE.Group();
    const v = (a) => new THREE.Vector3(a[0], a[1], a[2]);
    const sun = new THREE.Vector3(0, 0, 0);
    const surfU = { uSea: { value: v(def.palette.sea) }, uLow: { value: v(def.palette.low) }, uMid: { value: v(def.palette.mid) },
      uHigh: { value: v(def.palette.high) }, uLife: { value: v(def.palette.life) }, uSun: { value: sun },
      uSeaLevel: { value: def.seaLevel }, uSeed: { value: def.seed }, uTime: { value: 0 }, uStrain: { value: 0 } };
    const surface = new THREE.Mesh(new THREE.SphereGeometry(r, 96, 96),
      new THREE.ShaderMaterial({ uniforms: surfU, vertexShader: SURFACE_VS, fragmentShader: SURFACE_FS }));
    group.add(surface);
    const cloudU = { uSeed: { value: def.seed }, uTime: { value: 0 }, uSun: { value: sun } };
    const clouds = new THREE.Mesh(new THREE.SphereGeometry(r * 1.025, 64, 64),
      new THREE.ShaderMaterial({ uniforms: cloudU, vertexShader: SURFACE_VS, fragmentShader: CLOUD_FS, transparent: true, depthWrite: false }));
    group.add(clouds);
    const atmoU = { uColor: { value: new THREE.Color(statusHex) }, uPower: { value: 2.6 }, uGlow: { value: 0.9 } };
    const atmo = new THREE.Mesh(new THREE.SphereGeometry(r * 1.16, 64, 64),
      new THREE.ShaderMaterial({ uniforms: atmoU, vertexShader: SURFACE_VS, fragmentShader: ATMO_FS, transparent: true,
        side: THREE.BackSide, blending: THREE.AdditiveBlending, depthWrite: false }));
    group.add(atmo);
    // the life you can see from orbit: one drifting swarm per species, at its own height, in the world's life colour
    const swarms = [];
    def.species.forEach((sp, i) => {
      const n = 14, pos = new Float32Array(n * 3);
      let s = def.seed * 1000 + i * 77;
      const rnd = () => { s = (s * 16807) % 2147483647; return s / 2147483647; };
      for (let k = 0; k < n; k++) {
        const a = rnd() * 6.283, b = Math.acos(2 * rnd() - 1), d = r * (1.08 + 0.12 * i + rnd() * 0.05);
        pos[k * 3] = d * Math.sin(b) * Math.cos(a); pos[k * 3 + 1] = d * Math.cos(b); pos[k * 3 + 2] = d * Math.sin(b) * Math.sin(a);
      }
      const c = new THREE.Color(def.palette.life[0], def.palette.life[1], def.palette.life[2]).offsetHSL(i * 0.06, 0, 0);
      const pts = new THREE.Points(new THREE.BufferGeometry().setAttribute('position', new THREE.BufferAttribute(pos, 3)),
        new THREE.PointsMaterial({ color: c, size: r * 0.045, transparent: true, opacity: 0.7, depthWrite: false, blending: THREE.AdditiveBlending }));
      pts.rotation.set(rnd() * 1.5, 0, rnd() * 1.5);
      pts.userData.speed = 0.002 + rnd() * 0.004;
      group.add(pts);
      swarms.push(pts);
    });
    group.userData = { surface, clouds, atmo, swarms, def, surfU, cloudU, atmoU, radius: r };
    return group;
  }

  function setStatus(group, statusHex, strain) {
    const u = group.userData;
    u.atmoU.uColor.value.set(statusHex);
    u.surfU.uStrain.value = strain || 0;
  }

  function tick(group, t, sunWorld) {
    const u = group.userData;
    u.surfU.uTime.value = t; u.cloudU.uTime.value = t;
    if (sunWorld) { u.surfU.uSun.value.copy(sunWorld); u.cloudU.uSun.value.copy(sunWorld); }
    u.surface.rotation.y += 0.0016; u.clouds.rotation.y += 0.0022;
    for (const s of u.swarms) s.rotation.y += s.userData.speed;
  }

  function star(THREE, size) {
    const r = size || 0.85;
    const group = new THREE.Group();
    const u = { uTime: { value: 0 } };
    const core = new THREE.Mesh(new THREE.SphereGeometry(r, 64, 64),
      new THREE.ShaderMaterial({ uniforms: u, vertexShader: SURFACE_VS, fragmentShader: STAR_FS }));
    group.add(core);
    const glowU = { uColor: { value: new THREE.Color(0x5CE1E6) }, uPower: { value: 1.6 }, uGlow: { value: 1.0 } };
    const glow = new THREE.Mesh(new THREE.SphereGeometry(r * 1.6, 48, 48),
      new THREE.ShaderMaterial({ uniforms: glowU, vertexShader: SURFACE_VS, fragmentShader: ATMO_FS, transparent: true,
        side: THREE.BackSide, blending: THREE.AdditiveBlending, depthWrite: false }));
    group.add(glow);
    const light = new THREE.PointLight(0xdffaff, 2.2, 60);
    group.add(light);
    group.userData = { core, glow, u, radius: r };
    return group;
  }

  function tickStar(group, t) { group.userData.u.uTime.value = t; group.userData.core.rotation.y += 0.002; }

  // THE MYCELIUM UNDERNEATH (his words, 2026-10-13: "ensure the mycellium underneath"). The highway is the root
  // network every world grows from: a fractal mat of glowing threads under the whole system, a thread from each
  // world down into it, and pulses carried through it. Its colour is the Highway's status, the same measurement.
  function mycelium(THREE, opts) {
    const o = opts || {}, R = o.radius || 9, y = o.y == null ? -2.2 : o.y;
    const group = new THREE.Group();
    let s = 1234567;
    const rnd = () => { s = (s * 16807) % 2147483647; return s / 2147483647; };
    const segs = [];
    function grow(x, z, ang, len, depth) {
      if (depth > 6 || len < 0.12) return;
      const steps = 3 + Math.floor(rnd() * 3);
      let cx = x, cz = z, a = ang;
      for (let i = 0; i < steps; i++) {
        a += (rnd() - 0.5) * 0.6;
        const nx = cx + Math.cos(a) * len / steps, nz = cz + Math.sin(a) * len / steps;
        if (Math.hypot(nx, nz) > R) return;
        segs.push(cx, y, cz, nx, y, nz);
        cx = nx; cz = nz;
      }
      const kids = depth < 2 ? 3 : (rnd() < 0.7 ? 2 : 1);
      for (let k = 0; k < kids; k++) grow(cx, cz, a + (rnd() - 0.5) * 1.4, len * (0.62 + rnd() * 0.2), depth + 1);
    }
    const arms = o.arms || 9;
    for (let i = 0; i < arms; i++) grow(0, 0, (i / arms) * Math.PI * 2 + rnd() * 0.3, 2.6 + rnd(), 0);
    const geo = new THREE.BufferGeometry().setAttribute('position', new THREE.Float32BufferAttribute(segs, 3));
    const mat = new THREE.LineBasicMaterial({ color: new THREE.Color(o.color || 0x46E3A0), transparent: true, opacity: 0.38,
      blending: THREE.AdditiveBlending, depthWrite: false });
    const net = new THREE.LineSegments(geo, mat);
    group.add(net);
    // spores: lights travelling outward along the threads, the road carrying both ways
    const n = Math.min(160, segs.length / 6), sp = new Float32Array(n * 3), idx = [];
    for (let i = 0; i < n; i++) idx.push(Math.floor(rnd() * (segs.length / 6)));
    const spores = new THREE.Points(new THREE.BufferGeometry().setAttribute('position', new THREE.BufferAttribute(sp, 3)),
      new THREE.PointsMaterial({ color: 0xF4E9B0, size: 0.07, transparent: true, opacity: 0.9, blending: THREE.AdditiveBlending, depthWrite: false }));
    group.add(spores);
    // roots: one thread from each world down into the mat, following it in its orbit
    const roots = new THREE.LineSegments(new THREE.BufferGeometry().setAttribute('position', new THREE.BufferAttribute(new Float32Array(6 * 64), 3)),
      new THREE.LineBasicMaterial({ color: new THREE.Color(o.color || 0x46E3A0), transparent: true, opacity: 0.28, depthWrite: false }));
    group.add(roots);
    group.userData = { net, mat, spores, sp, idx, segs, roots, y, rootsMat: roots.material };
    return group;
  }

  function setMycelium(group, statusHex) { group.userData.mat.color.set(statusHex); group.userData.rootsMat.color.set(statusHex); }

  function tickMycelium(group, t, worlds) {
    const u = group.userData, seg = u.segs, sp = u.sp;
    for (let i = 0; i < u.idx.length; i++) {
      const k = (t * 0.6 + i * 0.137) % 1, j = u.idx[i] * 6;
      sp[i * 3] = seg[j] + (seg[j + 3] - seg[j]) * k; sp[i * 3 + 1] = u.y + 0.01; sp[i * 3 + 2] = seg[j + 2] + (seg[j + 5] - seg[j + 2]) * k;
      if (k < 0.02) u.idx[i] = (u.idx[i] + 1 + Math.floor(Math.random() * 3)) % (seg.length / 6);
    }
    u.spores.geometry.attributes.position.needsUpdate = true;
    u.mat.opacity = 0.3 + 0.1 * Math.sin(t * 1.3);
    if (worlds) {
      const p = u.roots.geometry.attributes.position, m = Math.min(64, worlds.length);
      for (let i = 0; i < 64; i++) {
        const w = i < m ? worlds[i].position : null;
        if (w) { p.setXYZ(i * 2, w.x, w.y, w.z); p.setXYZ(i * 2 + 1, w.x * 0.92, u.y, w.z * 0.92); }
        else { p.setXYZ(i * 2, 0, u.y, 0); p.setXYZ(i * 2 + 1, 0, u.y, 0); }
      }
      p.needsUpdate = true;
    }
  }

  // what a world says about itself when you open it: its life, its job, and its strain, in words
  function describe(def, statusWord) {
    const strain = statusWord === 'red' ? 'Its life is under strain: something here needs attention, and the species whose work it is are moving first.'
      : statusWord === 'amber' ? 'Its air is amber: something is not known yet, or is waiting on someone. Its life holds, and waits.'
      : 'Its biosphere is in balance: every species is doing its part, and nothing takes more than it returns.';
    return { name: def.name, strain, species: def.species.map(([n, job]) => ({ name: n, job })) };
  }

  window.CovenantWorlds = { CODEX, STAR, NODE_WORLDS, OTHER_WORLDS, worldFor, repoWorld, planet, setStatus, tick, star, tickStar, describe, mycelium, setMycelium, tickMycelium };
})();
