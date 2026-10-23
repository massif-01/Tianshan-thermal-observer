// Independent frontend logic probe. No browser, network, or device access.
// Executes the delivered main.ts after TypeScript erasure with DOM/Charts I/O doubles.
import fs from 'node:fs';
import vm from 'node:vm';
import {stripTypeScriptTypes} from 'node:module';
const base=process.env.TTO_REVIEW_CANDIDATE; if(!base)throw Error('Set TTO_REVIEW_CANDIDATE');
const output=process.env.TTO_REVIEW_OUTPUT||new URL('.',import.meta.url).pathname; fs.mkdirSync(output,{recursive:true});
const load=n=>JSON.parse(fs.readFileSync(base+'/evidence/installed-api/'+n+'.json','utf8'));
const source=fs.readFileSync(base+'/frontend/src/main.ts','utf8');
const main=stripTypeScriptTypes(source.replace(/^import .*;\n/gm,'').replace(/\(async\(\)=>\{try\{const boot=await api\('bootstrap'\)[\s\S]*$/,''));
class El {
 constructor(id=''){this.id=id;this.children=[];this._text='';this.listeners={};this.attributes={};this.value='';this.className='';this.style={};this.hidden=false;this.open=false;this.classList={toggle:()=>{},contains:()=>false};}
 set innerHTML(v){this._html=v;}get innerHTML(){return this._html;}
 set textContent(v){this._text=String(v);this.children=[];}get textContent(){return this._text+this.children.map(v=>v.textContent).join(' | ');}
 replaceChildren(...v){this._text='';this.children=[...v];}append(...v){this.children.push(...v);}
 addEventListener(k,v){this.listeners[k]=v;}setAttribute(k,v){this.attributes[k]=v;}
 toggleAttribute(){}showModal(){this.open=true;}close(){this.open=false;}
}
function create(){
 const els=new Map();const get=id=>{if(!els.has(id))els.set(id,new El(id));return els.get(id);};
 const chartMap=new Map();const timers=[];let now=0;const streams=[];const state={
 document:{querySelector:()=>get('app'),getElementById:get,createElement:tag=>new El(tag),createElementNS:(_ns,tag)=>new El(tag),body:get('body'),addEventListener(){},documentElement:get('html')},
 performance:{now:()=>now},localStorage:{getItem:()=>null,setItem(){}},matchMedia:()=>({matches:false}),
 ResizeObserver:class{observe(){}},window:{addEventListener(){}},location:{reload(){}},setInterval:f=>timers.push(f),Intl,Date,Map,Set,Promise,structuredClone,
 echarts:{init:el=>{const c={option:{},setOption(o){Object.assign(c.option,o);},dispatchAction(){},resize(){},on(){}};chartMap.set(el.id,c);return c;},connect(){}},
 EventSource:class{constructor(){this.listeners={};streams.push(this);}addEventListener(k,v){this.listeners[k]=v;}},
 fetch:async url=>({ok:true,status:200,json:async()=>{if(url.includes('predictions'))return load('predictions-45');if(url.includes('context'))return load('context');if(url.includes('series'))return {series:[]};if(url.includes('events'))return {events:[]};throw Error('unexpected '+url);}})
 };
 vm.createContext(state);vm.runInContext(main+`\nglobalThis.probe={accept,connect,renderComparison,renderModel,renderHeader,renderFields,renderEventTimeline,setConnected(v){connected=v;},getCurrent(){return current;},setEvents(v){events=v;},getOrigin(){return originUtc;}};`,state);
 return {state,get,chartMap,timers,streams,setNow(v){now=v;}};
}
const flush=async()=>{for(let i=0;i<30;i++)await Promise.resolve();};
const summary={runtime:process.version,kind:'delivered TypeScript functions with DOM/chart doubles; not browser E2E'};
{
 const h=create();h.state.probe.setConnected(true);h.state.probe.accept(load('snapshot'));await flush();
 const before=h.get('futureValues').textContent;
 h.state.probe.connect();h.streams[0].onerror();
 summary.sse_disconnect={before,future_after:h.get('futureValues').textContent,header:h.get('link').textContent,notice:h.get('notice').textContent,current_predictions:h.state.probe.getCurrent().predictions.length,model_Tf:h.state.probe.getCurrent().model.Tf_C,issue_confirmed:before===h.get('futureValues').textContent&&before.includes('44.3')};
 if(!summary.sse_disconnect.issue_confirmed)throw Error('expected stale D forecast reproduction failed');
}
{
 const h=create(),snap=load('snapshot');h.state.probe.setConnected(true);h.state.probe.accept(snap);await flush();
 const before=h.get('futureValues').textContent;const elapsed=Math.max(10000,...snap.metrics.map(m=>(m.remaining_valid_ms||0)+1000));h.setNow(elapsed);for(const tick of h.timers)tick();
 summary.local_expiry={before,elapsed_since_snapshot_ms:elapsed,original_metric_deadlines_preserved:true,future_after:h.get('futureValues').textContent,main_tj:h.state.probe.getCurrent().metrics.find(m=>m.id==='temperature.tj').value,model_Tf:h.state.probe.getCurrent().model.Tf_C,model_phase:h.state.probe.getCurrent().model.phase,active_flow_paths:h.get('topology').children.filter(e=>e.attributes.class==='flow').length,issue_confirmed:before===h.get('futureValues').textContent&&h.state.probe.getCurrent().metrics.find(m=>m.id==='temperature.tj').value===null};
 if(!summary.local_expiry.issue_confirmed)throw Error('expected local expiry reproduction failed');
}
{
 const proof=JSON.parse(fs.readFileSync(output+'/events-probe-results.json','utf8'));
 const h=create();h.state.probe.setConnected(true);h.state.probe.accept(proof.snapshot);await flush();
 h.state.probe.setEvents(proof.events);h.state.probe.renderEventTimeline();
 const point=h.chartMap.get('eventTimeline').option.series[0].data.find(p=>p.eventId===proof.old_event_id);
 summary.cross_run_event={current_run:proof.current_run,old_event_reason:proof.old_event.reason,plotted_in_current_run:Boolean(point),plotted_x_ms:point?.value[0],axis_start_utc:new Date(h.state.probe.getOrigin()).toISOString(),old_event_has_run_id:'run_id' in proof.old_event,issue_confirmed:Boolean(point)};
 if(!point)throw Error('expected cross-run event plot reproduction failed');
}
fs.writeFileSync(output+'/frontend-probe-results.json',JSON.stringify(summary,null,2)+'\n');
console.log(JSON.stringify(summary,null,2));
