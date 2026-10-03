// Runs the actual classic inline script against inert DOM/network/speech doubles.
// No browser, network, production files, service or device is used.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const directory=process.argv[2],fixture=JSON.parse(fs.readFileSync(path.join(directory,'fixture.json'),'utf8'));
class Element {
 constructor(tag='div'){this.tagName=tag.toUpperCase();this.children=[];this.style={};this.dataset={};this.attributes={};this.listeners={};this.value='';this._text='';const classes=new Set();this.classList={contains:x=>classes.has(x),add:x=>classes.add(x),remove:x=>classes.delete(x),toggle:(x,on)=>{const value=on===undefined?!classes.has(x):on;value?classes.add(x):classes.delete(x);return value;}};}
 set textContent(value){this._text=String(value);this.children=[];} get textContent(){return this._text+this.children.map(x=>x.textContent).join('');}
 get firstChild(){return this.children[0]||null;} appendChild(e){this.children.push(e);return e;}
 insertBefore(e,b){this.children=this.children.filter(x=>x!==e);const i=this.children.indexOf(b);this.children.splice(i<0?this.children.length:i,0,e);}
 replaceChildren(...e){this.children=e;this._text='';} setAttribute(k,v){this.attributes[k]=v;} addEventListener(k,fn){this.listeners[k]=fn;}
 getBoundingClientRect(){return {left:16,top:16};} focus(){document.activeElement=this;} blur(){document.activeElement=null;} click(){if(this.onclick)this.onclick();}
}
const elements=new Map();
const document={activeElement:null,body:new Element('body'),getElementById(id){if(!elements.has(id))elements.set(id,new Element(id==='q'?'textarea':'div'));return elements.get(id);},createElement:tag=>new Element(tag),createTextNode:text=>{const e=new Element('#text');e.textContent=text;return e;},querySelectorAll:()=>document.getElementById('orbbuttons').children};
document.getElementById('mode').value='talk';document.getElementById('chatwin').classList.add('min');
const requests=[],spoken=[],recognitions=[],timers=[];let speechCancels=0;
class Recognition {constructor(){recognitions.push(this);}start(){this.started=true;}abort(){this.aborted=true;}}
const context={document,AbortController,console,innerWidth:1000,innerHeight:800,Math,Date,JSON,crypto:{randomUUID:(()=>{let n=0;return()=>`00000000-0000-4000-8000-${String(++n).padStart(12,'0')}`;})()},localStorage:{setItem(){},getItem(){return null;}},navigator:{clipboard:{writeText:async()=>{}}},SpeechRecognition:Recognition,SpeechSynthesisUtterance:class{constructor(text){this.text=text;}},speechSynthesis:{cancel(){speechCancels++;},speak(u){spoken.push(u);}},location:{reload(){throw Error('Unexpected reload');}},setTimeout:(fn)=>{timers.push(fn);return timers.length;},setInterval:()=>0,addEventListener(){},removeEventListener(){},fetch:(url,options)=>new Promise((resolve,reject)=>requests.push({url,options,resolve,reject}))};
context.window=context;context.globalThis=context;vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(directory,'page.cjs'),'utf8'),context);
const run=code=>vm.runInContext(code,context),flush=async()=>{await new Promise(resolve=>setImmediate(resolve));};
const reply=(request,body,ok=true)=>request.resolve({ok,status:ok?200:503,json:async()=>body});
const next=url=>{const r=requests.find(x=>!x.used&&x.url===url);assert(r,`Missing request ${url}`);r.used=true;return r;};
async function ask(text,mode='talk'){document.getElementById('mode').value=mode;document.getElementById('q').value=text;run('send()');await flush();return next(mode==='council'?'/pc/council':'/m/agent');}
async function main(){
 reply(next('/pc/3d/history'),{turns:[]});reply(next('/pc/3d/state'),fixture);await flush();
 assert.equal(document.getElementById('orbbuttons').children.length,9,'Every orb is reachable without Three.js');
 assert.equal(new Set(document.getElementById('orbbuttons').children.map(x=>x.dataset.orb)).size,9);
 run("selectOrb('node:5020:1')");assert.match(document.getElementById('info').textContent,/5020/);
 const updated=structuredClone(fixture);updated.orbs.find(x=>x.id==='node:5020:1').detail.warnings=['fresh warning'];
 run('getState()');reply(next('/pc/3d/state'),updated);await flush();assert.match(document.getElementById('info').textContent,/fresh warning/,'Selected details refresh even when names/colors do not move');
 for(const highway of [null,{}, {node_down:'surprise'}, {node_down:'absent'}]){context.raw={detail:{highway}};assert.equal(run("orbItems(raw).find(x=>x.id==='highway').status"),'unknown');}
 context.raw={detail:{highway:Object.fromEntries(run('HIGHWAY_ORB_KEYS').map(x=>[x,'absent']))}};assert.equal(run("orbItems(raw).find(x=>x.id==='highway').status"),'ok');
 run('getState()');next('/pc/3d/state').reject(Error('offline'));await flush();assert.equal(run('orbRows.every(x=>x.status===\'unknown\')'),true);assert.match(document.getElementById('info').textContent,/last known/);
 run('getState()');reply(next('/pc/3d/state'),fixture);await flush();
 const first=await ask('Hello');assert.equal(first.url,'/m/agent');let body=JSON.parse(first.options.body);assert.deepEqual(body.history,[]);assert.match(body.request_id,/^pc3d-/);
 reply(first,{status:'success',answer:'Hello, I remember our conversation.'});await flush();assert.equal(run('conversation.length'),2);assert.equal(spoken.length,1);
 const withheld=await ask('held');reply(withheld,{status:'success',answer:'not for context',withheld:true,message:'held'});await flush();assert.equal(run('conversation.length'),2);assert.equal(spoken.length,1);
 const failed=await ask('error');reply(failed,{status:'error',message:'unavailable'});await flush();assert.equal(run('conversation.length'),2);assert.equal(spoken.length,1);
 const old=await ask('old request');run('stopTurn()');assert.equal(old.options.signal.aborted,true);assert.match(document.getElementById('answer').textContent,/\(stopped\)/);
 const current=await ask('new request');reply(old,{status:'success',answer:'obsolete reply'});await flush();assert.equal(run('inflight!==null'),true,'An old completion cannot clear the new turn');assert.equal(run('conversation.length'),2);assert.equal(spoken.length,1);
 reply(current,{status:'success',answer:'current reply'});await flush();assert.equal(run('conversation.length'),4);assert.equal(spoken.length,2);
 const council=await ask('Think this through','council');body=JSON.parse(council.options.body);assert.equal(body.history.length,4);assert.notEqual(body.request_id,JSON.parse(first.options.body).request_id);reply(council,{status:'success',answer:'Council reply'});await flush();
 const interrupted=await ask('interrupt me');document.getElementById('mic').onclick();assert.equal(interrupted.options.signal.aborted,true);assert(speechCancels>0);
 const recognition=recognitions.at(-1);assert.equal(recognition.started,true);reply(interrupted,{status:'success',answer:'interrupted old reply'});await flush();
 recognition.onresult({resultIndex:0,results:[Object.assign([{transcript:'new spoken message'}],{isFinal:false})]});await flush();assert.equal(requests.filter(x=>!x.used&&x.url==='/m/agent').length,0,'Interim transcription is not submitted');
 recognition.onresult({resultIndex:0,results:[Object.assign([{transcript:'new spoken message'}],{isFinal:true})]});await flush();const spokenRequest=next('/m/agent');reply(spokenRequest,{status:'success',answer:'spoken answer'});await flush();assert.equal(run('conversation.length'),8);
 const staleRecognition=recognition;document.getElementById('mic').onclick();const latest=recognitions.at(-1);staleRecognition.onresult({results:[Object.assign([{transcript:'stale mic text'}],{isFinal:true})]});await flush();assert.equal(recognitions.at(-1),latest);assert.equal(requests.filter(x=>!x.used&&x.url==='/m/agent').length,0);
 run("for(let i=0;i<30;i++)rememberTurn('question '+i,'answer '+i)");assert.equal(run('conversation.length'),40);
 run("rememberTurn('opening '+ 'x'.repeat(6000)+' latest corrected preference','understood')");assert.match(run('conversation.at(-2).content'),/latest corrected preference/);assert.equal(run('conversation.at(-2).content.length'),2000);
 run("for(let i=0;i<20;i++)rememberTurn('q'.repeat(3000),'a'.repeat(3000))");assert(run('conversation.reduce((n,x)=>n+x.content.length,0)')<=12000);
 assert.equal(document.getElementById('send').onclick!==undefined,true);assert.equal(document.getElementById('heal').onclick!==undefined,true);
 console.log('PC3d UI regression checks passed');
}
main().catch(e=>{console.error(e);process.exitCode=1;});
