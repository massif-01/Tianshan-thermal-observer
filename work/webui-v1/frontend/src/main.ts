import * as echarts from 'echarts';
import type {Snapshot,Metric,Series,Prediction,Node} from './types';
import './style.css';

const root=document.querySelector<HTMLDivElement>('#app')!;
root.innerHTML=`
<header><a class="brand" href="#trends"><span class="brand-mark">T</span><b>TTO <span>热观察台</span></b><small>只读观察</small></a><nav><a href="#trends">趋势</a><a href="#model">热模型</a><a href="#compare">预测对照</a><a href="#context">运行信息</a></nav><div class="header-tools"><span id="link" class="badge">连接中</span><button id="pause">暂停画面</button><button id="fullscreen">全屏</button></div></header>
<main><div class="overview"><div><span class="eyebrow">THERMAL OBSERVATORY · V1.0</span><h1>看清当前，也核对预测。</h1><p id="identities">页面已启动，正在等待TTO数据</p></div><div class="overview-status"><span id="mode" class="badge">等待数据</span><span id="phase" class="badge">等待模型</span><small id="clock">Asia/Shanghai</small></div></div>
<div id="notice" role="status">正在连接本地Web服务。</div><div id="metrics" class="metrics"></div>
<section id="trends"><div class="section-heading"><div><span class="section-id">01</span><h2>实时趋势</h2><small>原始采样 · 缺口保留</small></div><div class="controls"><label>时间范围 <select id="range"><option value="5">最近5分钟</option><option value="10" selected>最近10分钟</option><option value="30">最近30分钟</option><option value="60">最近60分钟</option></select></label><details class="settings"><summary>显示设置</summary><label><input id="motion" type="checkbox">减少动效</label><label><input id="extra" type="checkbox">显示其他已接温区 / 功率rail</label><small>仅保存浏览器偏好；曲线图例可切换系列。</small></details><button id="resetZoom">重置缩放</button></div></div>
<div class="chart-panel"><div class="chart-label"><h3>温度</h3><span>°C · 实测</span></div><div id="temperature" class="chart temperature"></div></div>
<div class="chart-panel"><div class="chart-label"><h3>功率</h3><span>W · 独立rail，非整机总功耗</span></div><div id="power" class="chart"></div></div>
<div class="chart-panel"><div class="chart-label"><h3>风扇输出</h3><span>% · 天山OS执行</span></div><div id="pwm" class="chart"></div></div>
<div class="event-band"><b>A · 事件</b><div id="eventTimeline"></div><span id="eventEmpty">等待有来源的事件</span></div><div id="eventSelection" class="event-selection" hidden></div><small class="axis-note">三图与事件共用时间范围、缩放和光标。每条读数的实际接收时间在提示中列出；不跨缺口连线。</small></section>
<div class="lower"><section id="model" class="panel"><div class="section-heading"><div><span class="section-id">C</span><h2>热模型路径</h2></div><span id="modelPhase" class="badge">未加载</span></div><div class="model-scroll"><svg id="topology" viewBox="0 0 760 340" aria-label="G2热模型依赖图"></svg></div><div class="model-notes"><span>实线：模型输入 / 耦合</span><span>虚线：TJ测量校正</span><span>流动点：有效数据关系示意</span></div><p class="subtle">Ts是模型内部慢态，E是等效边界，均非结构或环境测温。RPM、CPU/GPU利用率和RAM属于运行观测。</p><details id="nodeDetails"><summary>节点与模型详情</summary><pre id="nodeText">点击节点查看来源、时刻和计算含义。</pre></details><div class="advisories"><div><small>平稳需求（研究）</small><b>本轮未计算</b><span>没有当前合法provider和固定参考；index不是PWM。</span></div><div><small>PWM观察建议</small><b id="advice">暂无可用建议映射</b><span id="adviceReason">实验观察参考，无设备写权限。</span></div></div></section>
<div class="right-stack"><section id="compare" class="panel"><div class="section-heading"><div><span class="section-id">D</span><h2>预测与实测</h2></div><select id="horizon" aria-label="预测时距"><option value="15">+15秒</option><option value="45" selected>+45秒</option><option value="90">+90秒</option></select></div><p id="comparisonStatus" class="subtle">过去发出的45秒预测，到了目标时刻，实际TJ是多少？</p><div id="comparison" class="compare-chart"></div><div id="score" class="score"></div><div id="latestMatch" class="latest-match">等待这条预测对应的实测温度</div><div class="future"><small>现在发出的未来参考 · G2-HOLD</small><div id="futureValues">模型正在等待可消费状态。</div><p>保持当时两rail与已声明PWM情景；三点分别实算，不代表连续未来轨迹。</p></div></section>
<section id="context" class="panel"><div class="section-heading"><div><span class="section-id">E</span><h2>当前运行信息</h2></div><span class="badge">天山OS控制</span></div><dl id="contextRows"></dl><p id="contextNote" class="subtle">未接入任务记录；客户端完成不代表GPU停止。RAM用量不用于推断模型驻留。</p></section></div></div>
<details id="health" class="drawer"><summary><b>B · 数据源详细状态</b><span id="healthSummary">等待来源</span></summary><p id="sourceStatus"></p><p id="sourceDiagnostics"></p><div class="table-scroll"><table><thead><tr><th>来源</th><th>字段</th><th>质量</th><th>年龄 / 剩余有效期</th><th>实际接收时刻</th></tr></thead><tbody id="healthRows"></tbody></table></div></details>
<details class="drawer" id="events"><summary><b>事件与告警</b><span id="eventCount">0条</span></summary><div class="filters"><select id="eventSource" aria-label="事件来源"><option value="">全部来源</option><option value="source">source</option><option value="observer">observer</option><option value="board">board</option><option value="runner">runner</option><option value="web-source">web-source</option></select><select id="eventLevel" aria-label="事件级别"><option value="">全部级别</option><option value="warning">重要异常</option><option value="info">信息</option></select></div><div id="eventList"></div></details>
<details class="drawer" id="fields"><summary><b>全部已接字段</b><span id="fieldCount">0项</span></summary><div class="filters"><input id="search" type="search" placeholder="搜索名称或字段ID" aria-label="字段搜索"><select id="group" aria-label="字段分类"><option value="">全部分类</option><option value="temperature.">温度</option><option value="cpu.">逐核CPU</option><option value="usage.">利用率</option><option value="memory.">内存</option><option value="power.">功率</option><option value="fan.">风扇</option><option value="control.">主板温源</option><option value="host.">Web主机进程</option></select></div><div class="table-scroll"><table><thead><tr><th>名称 / ID</th><th>数值 / 原精度</th><th>单位</th><th>类型 / 质量</th><th>来源引用</th></tr></thead><tbody id="fieldRows"></tbody></table></div></details>
<footer><span>TTO Web UI 1.0 · 固定参数，只读观察</span><span>研究状态与条件预测不构成风扇控制指令</span></footer></main>
<dialog id="login"><form id="loginForm"><h2>只读访问</h2><input type="hidden" name="username" value="tto-readonly" autocomplete="username"><p>输入安装时生成的本地访问口令。</p><input id="password" type="password" autocomplete="current-password" required aria-label="只读访问口令"><button type="submit">登录</button><p id="loginMessage"></p></form></dialog>`;

const $=<T extends HTMLElement=HTMLElement>(id:string)=>document.getElementById(id) as T;
const text=(id:string,v:unknown)=>{$(id).textContent=String(v??'—');};
const esc=(v:unknown)=>String(v??'—').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]!));
const phaseLabels:Record<string,string>={not_loaded:'未加载热模型',uninitialized:'等待模型初始化',provisional:'初始化参考',tracking:'状态跟踪中',degraded:'部分输入缺失，条件估计',unavailable:'当前无法估计'};
const statusLabels:Record<string,string>={valid:'有效',stale:'到期',invalid:'已失效',unknown:'未知',unverified:'未确认',conditional:'条件估计',not_supported:'未提供',not_configured:'未配置'};
const fmt=(v:unknown,n=1)=>typeof v==='number'?v.toFixed(n):v==null?'—':String(v);
let current:Snapshot|null=null, latest:Snapshot|null=null, connected=false,paused=false,range=Number(localStorage.getItem('tto-range')||10),horizon=45,received=performance.now(),tz='Asia/Shanghai',originUtc=0,busy=false,lastRun='',events:any[]=[],seriesData:Series[]=[],extra=localStorage.getItem('tto-extra')==='true';
let latestReceived=received,lastContext:any=null;
let seriesGroup='',lastSeriesFetch:number|null=null,seriesCache=new Map<string,Series>();
let comparisonGeneration=0,predictionRequest=0;
let predictionGroup='',lastPredictionFetch:number|null=null,predictionCache=new Map<string,Prediction>(),predictionLabels:Record<string,any>={};
const motion=localStorage.getItem('tto-motion')==='true'||matchMedia('(prefers-reduced-motion: reduce)').matches;
$('motion').toggleAttribute('checked',motion);$('extra').toggleAttribute('checked',extra);($('range') as HTMLSelectElement).value=String(range);
document.body.classList.toggle('reduced-motion',motion);
const charts=['temperature','power','pwm','comparison','eventTimeline'].map(id=>echarts.init($(id),undefined,{renderer:'canvas'}));
charts.forEach(c=>c.group='tto-timeline');echarts.connect('tto-timeline');
new ResizeObserver(()=>charts.forEach(c=>c.resize())).observe($('trends'));
window.addEventListener('resize',()=>charts.forEach(c=>c.resize()));
const timeLabel=(t:number)=>new Intl.DateTimeFormat('zh-CN',{timeZone:tz,hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false}).format(originUtc+t);
const dateLabel=(value:string|null)=>value?new Intl.DateTimeFormat('zh-CN',{timeZone:tz,month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false}).format(new Date(value)):'未知';
function lineValue(m?:Metric){return m&&m.status==='valid'&&m.remaining_valid_ms!==null&&m.remaining_valid_ms>performance.now()-received?m.value:null;}
const metric=(id:string)=>current?.metrics.find(m=>m.id===id);
const clean=(node:HTMLElement)=>node.replaceChildren();
function cell(tr:HTMLTableRowElement,value:unknown){const td=document.createElement('td');td.textContent=String(value??'—');tr.append(td);return td;}
function row(dl:HTMLElement,k:string,v:unknown){const dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=k;dd.textContent=String(v??'未知');dl.append(dt,dd);}

async function api(path:string){const r=await fetch('/api/v1/'+path,{credentials:'same-origin'});if(r.status===401){if(!$<HTMLDialogElement>('login').open)$<HTMLDialogElement>('login').showModal();throw Error('login');}if(!r.ok)throw Error('read');return r.json();}

function renderMetrics(){
 const ids=['temperature.tj','temperature.cpu','temperature.gpu','fan.pwm.actual','fan.rpm','power.gpu','power.cpu_soc_mss','usage.gpu','usage.cpu.mean','memory.ram'];
 const labels=['TJ温度','CPU温度','GPU温度','成功PWM','风扇RPM','GPU功率','CPU·SoC·MSS','GPU利用率','CPU平均利用率','Jetson RAM'];
 clean($('metrics'));
 ids.forEach((id,i)=>{const m=metric(id),v=lineValue(m),card=document.createElement('div');card.className='metric '+(v===null?'muted':'');const label=document.createElement('small'),value=document.createElement('b'),unit=document.createElement('span'),status=document.createElement('em');label.textContent=labels[i];value.textContent=fmt(v,id.startsWith('power.')?2:id==='memory.ram'?0:id==='fan.pwm.actual'?0:1);unit.textContent=m?.unit||'';status.textContent=id==='fan.rpm'?'测速有效性未确认'+(m?.last_observation?' · 原报'+m.last_observation.value:''):v!==null?'有效 · '+fmt((m?.age_lower_bound_ms||0)/1000,1)+'s前':m?statusLabels[m.status]||m.status:'未提供';if(id==='memory.ram'&&v!==null)status.textContent+=' / '+fmt(lineValue(metric('memory.ram.total')),0)+' '+(m?.unit||'');card.append(label,value,unit,status);card.title=m?`${m.label}\n原始精度: ${m.value??'—'}\n${m.reason_code||''}\n来源 ${m.source_ref}\n接收 ${dateLabel(m.received_at_utc)}\n上次 ${m.last_observation?.value??'—'}`:'当前设备未提供';$('metrics').append(card);});
}

function renderHeader(){
 text('link',connected?'Web已连接':'Web数据断开');$('link').className='badge '+(connected?'good':'warn');
 if(!current)return;
 text('identities',`观察对象：${current.context.observed_device||'尚未配置'}　｜　TTO主机：${current.context.tto_host}`);
 text('mode',current.mode==='test_replay'?'本地回放样例（非实时设备）':current.mode==='live'?'只读观察中':current.mode==='ended'?'观察已结束':'等待数据');
 text('phase',phaseLabels[current.model.phase]);text('modelPhase',phaseLabels[current.model.phase]);text('clock',tz);
 const notice=paused?'画面已暂停，后台观察继续；显示为暂停时快照。':!connected?'Web数据断开；当前值已撤下，后台观察不受此页面影响。':paused?'画面已暂停，后台观察继续。':current.health.protection_status==='active'?'主板明确报告保护或失温，观察建议已暂停。':current.mode==='waiting'?'页面已启动，正在等待TTO数据；尚未配置观察来源。':current.health.measurement_status!=='valid'?'设备数据不可用或已过期；Web连接不代表设备读数有效。':current.health.protection_status==='unknown'?'保护上下文未知；观察建议暂停，天山OS继续负责保护。':current.mode==='test_replay'?'本地自建服务 / 回放验证数据（非实时设备），不作为现场能力证据。':'正在观察已注册数据源。天山OS继续负责风扇控制。';
 text('notice',notice);$('notice').className=current.health.protection_status==='active'||!connected?'warning':'';
}

function buildChart(chart:echarts.ECharts,data:Series[],unit:string,pwm=false){
 if(!current)return;
 const end=current.run_elapsed_ms||0,start=Math.max(0,end-range*60000);
 chart.setOption({animation:false,color:['#167e97','#da8b27','#7863b3','#4b9a72','#bd5c65'],grid:{left:65,right:30,top:30,bottom:32},legend:{top:0,textStyle:{fontSize:11,color:'#61717f'}},tooltip:{trigger:'axis',confine:true,formatter:(params:any)=>{const values=Array.isArray(params)?params:[params];return values.map((p:any)=>{const v=p.data;return `${esc(p.seriesName)}: <b>${esc(fmt(v?.[1],2))} ${esc(p.seriesName.includes('RPM')?'RPM':unit)}</b><br>样本时间 ${esc(v?.[2]?dateLabel(v[2]):'缺口')} · ${esc(v?.[3]||'')} ${data.find(s=>s.label===p.seriesName)?.sampling!=='actual_samples'?'区间首末 / 极值，非新采样':''}`}).join('<br>');}},axisPointer:{link:[{xAxisIndex:'all'}]},xAxis:{type:'value',min:start,max:Math.max(end,start+1000),axisLabel:{formatter:timeLabel,color:'#77848e',fontSize:10},splitLine:{show:false},axisLine:{lineStyle:{color:'#dce3e7'}},axisPointer:{label:{formatter:(p:any)=>timeLabel(p.value)}}},yAxis:[{type:'value',name:unit,min:pwm?0:undefined,max:pwm?100:undefined,scale:!pwm,splitNumber:3,axisLabel:{color:'#77848e',fontSize:10},splitLine:{lineStyle:{color:'#edf1f3'}}},...(pwm&&data.some(s=>s.id==='fan.rpm')?[{type:'value',name:'RPM',scale:true,splitLine:{show:false}}]:[])],dataZoom:[{type:'inside',filterMode:'none',xAxisIndex:0}],series:data.map(s=>({name:s.label,type:'line',yAxisIndex:pwm&&s.id==='fan.rpm'?1:0,showSymbol:false,smooth:false,connectNulls:false,lineStyle:{width:s.id==='temperature.tj'||s.id==='fan.pwm.actual'?2:1.5,type:s.id==='fan.pwm.target'?'dashed':'solid'},data:s.points.map(p=>[p.t,p.value,p.received_at_utc,p.status])}))},{replaceMerge:['series','yAxis']});
}
function renderCharts(){
 const temperature=seriesData.filter(s=>s.id.startsWith('temperature.')&&(extra||['temperature.tj','temperature.cpu','temperature.gpu'].includes(s.id))).sort((a,b)=>['temperature.tj','temperature.cpu','temperature.gpu'].indexOf(a.id)-['temperature.tj','temperature.cpu','temperature.gpu'].indexOf(b.id));
 const power=seriesData.filter(s=>s.id.startsWith('power.')&&(extra||['power.gpu','power.cpu_soc_mss'].includes(s.id)));
 const pwm=seriesData.filter(s=>s.id.startsWith('fan.pwm.')||s.id==='fan.rpm'&&s.points.some(p=>p.value!==null));
 buildChart(charts[0],temperature,'°C');buildChart(charts[1],power,'W');buildChart(charts[2],pwm,'%',true);
 renderEventTimeline();
}

const positions:Record<string,[number,number]>={pg:[18,15],pc:[18,100],u:[18,205],tj:[205,15],tf:[205,110],ts:[400,110],forecast:[594,15],demand:[400,235],pwmref:[594,235],risk:[594,125]};
const ns='http://www.w3.org/2000/svg';
function svg(tag:string,attrs:Record<string,string>){const el=document.createElementNS(ns,tag);Object.entries(attrs).forEach(([k,v])=>el.setAttribute(k,v));return el;}
function currentForecast(h:number):Prediction|undefined{
 if(!current||!['tracking','degraded'].includes(current.model.phase)||lineValue(metric('temperature.tj'))===null)return undefined;
 const origin=metric('temperature.tj')?.as_of_elapsed_ms;
 return current.predictions.filter(p=>p.horizon_s===h&&p.status==='pending'&&p.origin_elapsed_ms===origin).at(-1);
}
function nodeValue(n:Node):string{
 if(!current)return '—';
 if(n.metric_id){const m=metric(n.metric_id),v=lineValue(m);return v===null?'暂无有效读数':fmt(v,1)+' '+(m?.unit||'');}
 if(n.state_path)return fmt((current.model as any)[n.state_path],1)+' °C · 估计';
 if(n.id==='forecast'){const p=currentForecast(45);return p?fmt(p.value_C)+' °C · +45秒':'等待可用预测';}
 if(n.id==='risk')return ({unknown:'保护上下文未知',active:'明确保护 / 失温',no_reported_protection:'未报告保护'}[current.health.protection_status]||'保护上下文未知');
 if(n.id==='pwmref')return current.advisory.value_percent==null?'暂无可用映射':fmt(current.advisory.value_percent)+' % · 参考';
 return '本轮未计算';
}
function renderModel(){
 if(!current)return;
 const diagram=$('topology');diagram.replaceChildren();
 current.model.edges.forEach(e=>{const a=positions[e.from],b=positions[e.to];if(!a||!b)return;const reverse=e.from==='ts'&&e.to==='tf';const x1=a[0]+142,y1=a[1]+28,x2=b[0],y2=b[1]+28;const d=reverse?`M ${a[0]+50} ${a[1]+55} Q 355 215 ${b[0]+110} ${b[1]+55}`:`M ${x1} ${y1} C ${(x1+x2)/2} ${y1} ${(x1+x2)/2} ${y2} ${x2} ${y2}`;const path=svg('path',{d,fill:'none',stroke:e.relation==='measurement_correction'?'#a18cbb':'#9eafba','stroke-width':'1.3',class:'static'});if(e.line_style==='dashed'||e.relation==='measurement_correction'||!e.animate_allowed)path.setAttribute('stroke-dasharray','4 5');diagram.append(path);if(e.animate_allowed&&!paused&&connected){diagram.append(svg('path',{d,fill:'none',stroke:'#428b9f','stroke-width':'2',class:'flow'}));}});
 current.model.nodes.forEach(n=>{const pos=positions[n.id];if(!pos)return;const g=svg('g',{transform:`translate(${pos.join(' ')})`,tabindex:'0',role:'button','aria-label':n.label,class:'node '+(n.status==='valid'?'valid':'inactive')});g.append(svg('rect',{width:'145',height:'56',rx:'7'}));const title=svg('text',{x:'10',y:'19',class:'node-title'});title.textContent=n.label;const value=svg('text',{x:'10',y:'41',class:'node-value'});value.textContent=nodeValue(n);g.append(title,value);const show=async()=>{let info:any={节点:n.label,含义:n.note||n.role,当前显示:nodeValue(n),详情时态:paused?'画面已暂停；展开详情读取当前后台只读状态':'当前后台只读状态'};if(n.metric_id)info={...info,字段:metric(n.metric_id)};else{try{const model=await api('model');info={...info,model};}catch{}}text('nodeText',JSON.stringify(info,null,2));$<HTMLDetailsElement>('nodeDetails').open=true;};g.addEventListener('click',show);g.addEventListener('keydown',e=>{if((e as KeyboardEvent).key==='Enter')show();});diagram.append(g);});
 text('advice',current.advisory.value_percent==null?'暂无可用建议映射':fmt(current.advisory.value_percent)+'% · 观察参考');text('adviceReason',current.advisory.reason+'；天山OS继续负责保护。');
}

function comparisonKey(){return current?[current.service_epoch,current.run_id,current.source_epoch,current.model.model_id,current.model.spec_id,horizon,range].join(':'):'';}
function invalidateComparison(){
 comparisonGeneration++;predictionRequest++;predictionGroup=comparisonKey();
 predictionCache.clear();predictionLabels={};lastPredictionFetch=null;
 charts[3].clear();clean($('score'));text('latestMatch','等待当前过程的成熟预测配对');
}
async function renderComparison(){
 if(!current||paused)return;
 const end=current.run_elapsed_ms||0,from=Math.max(0,end-range*60000),group=comparisonKey();
 if(group!==predictionGroup)invalidateComparison();
 const generation=comparisonGeneration,request=++predictionRequest;
 const delta=lastPredictionFetch===null?'':`&records_after=${lastPredictionFetch}`;
 const data=await api(`predictions?horizon_s=${horizon}&from=${from}&to=${end}${delta}`);
 if(paused||generation!==comparisonGeneration||request!==predictionRequest||group!==comparisonKey())return;
 for(const p of data.records as Prediction[])predictionCache.set(p.prediction_id,p);
 Object.assign(predictionLabels,data.labels||{});
 for(const [id,p] of predictionCache)if(p.origin_elapsed_ms<from){predictionCache.delete(id);delete predictionLabels[id];}
 lastPredictionFetch=end;data.labels=predictionLabels;
 const records:Prediction[]=[...predictionCache.values()].sort((a,b)=>a.target_elapsed_ms-b.target_elapsed_ms), matched=records.filter(p=>p.status==='matched');
 const s=data.summary;clean($('score'));
 [['MAE',fmt(s.MAE_C,3)+' °C'],['绝对误差P95',fmt(s.P95_absolute_C,3)+' °C'],['最大低估',fmt(s.max_underprediction_C,3)+' °C'],['匹配 / 应到期',`${s.matched_count} / ${s.due_count}`]].forEach(([name,value])=>{const v=document.createElement('div'),small=document.createElement('small'),b=document.createElement('b');small.textContent=name;b.textContent=value;v.append(small,b);$('score').append(v);});
 text('comparisonStatus',`${phaseLabels[current.model.phase]} · 同run/epoch/model/HOLD · +${horizon}秒 · ${matched.length<30?'样本较少':'当前窗口'}`);
 const last=matched.at(-1);text('latestMatch',last?`目标 ${timeLabel(last.target_elapsed_ms)} · 预测 ${fmt(last.value_C)}°C / 实测 ${fmt(last.observed_C)}°C · 误差 ${last.error_C!>=0?'+':''}${fmt(last.error_C,3)}°C（预测${last.error_C!>=0?'偏高':'偏低'}）`:`等待这条预测对应的实测温度 · 缺标签 ${s.missing_label_count} · 未到期 ${s.unmatched_future_count}`);
 buildChart(charts[3],[{id:'matched.actual',label:'目标后首个有效TJ',unit:'°C',sampling:'actual_samples',points:records.filter(p=>['matched','missing_label'].includes(p.status)).map(p=>({t:p.target_elapsed_ms,value:p.observed_C,sample_id:p.prediction_id,received_at_utc:data.labels?.[p.prediction_id]?.received_at_utc||null,status:p.status,source_ref:data.labels?.[p.prediction_id]?.source_ref||null}))},{id:'matched.forecast',label:`已发布+${horizon}秒预测`,unit:'°C',sampling:'actual_samples',points:records.filter(p=>['matched','missing_label'].includes(p.status)).map(p=>({t:p.target_elapsed_ms,value:p.value_C,sample_id:p.prediction_id,received_at_utc:null,status:p.status,source_ref:null}))}],'°C');
 charts[3].setOption({legend:{textStyle:{fontSize:10}},grid:{left:48,right:12,top:34,bottom:27},series:[{lineStyle:{type:'solid'}},{lineStyle:{type:'dashed'}}]});

}

function renderFuture(){
 if(!current)return;
 text('comparisonStatus',`${phaseLabels[current.model.phase]} · 历史配对同run/epoch/model/HOLD · +${horizon}秒`);
 clean($('futureValues'));
 for(const h of [15,45,90]){const p=currentForecast(h),v=document.createElement('div');const label=document.createElement('small'),b=document.createElement('b');label.textContent=`+${h}秒`;b.textContent=p?fmt(p.value_C)+' °C':'—';v.title=p?`origin ${timeLabel(p.origin_elapsed_ms)}\nissued ${timeLabel(p.issued_elapsed_ms)}\ntarget ${timeLabel(p.target_elapsed_ms)}\ncutoff ${timeLabel(p.input_cutoff_elapsed_ms)}\n${p.prediction_id}`:'没有当前已发布预测';v.append(label,b);$('futureValues').append(v);}
}

async function renderContext(){
 if(!current)return;const group=[current.service_epoch,current.run_id,current.source_epoch].join(':');const ctx=await api('context');if(paused||group!==[current?.service_epoch,current?.run_id,current?.source_epoch].join(':'))return;lastContext=ctx;renderContextRows();
}
function renderContextRows(){
 if(!current||!lastContext)return;const ctx=lastContext;
 text('sourceDiagnostics','显示链重新同步 '+(ctx.display_resync_count||0)+' 次 ｜ '+Object.values(ctx.source_health||{}).map((s:any)=>`${s.source}: ${s.quality_reason||s.error_class||'已接收'} ${s.timeout_phase||''} · RTT ${fmt(s.round_trip_ms)}ms · ${dateLabel(s.last_received_at_utc)}`).join(' ｜ '));
 text('contextNote',(ctx.task_metadata_available?'任务信息来自runner登记':'未接入任务记录')+'；客户端完成不代表GPU停止。RAM用量不用于推断模型驻留。');
 const dl=$('contextRows');clean(dl);
 const ram=metric('memory.ram');
 [['观察对象 / 平台',`${ctx.observed_device||'未知'} / ${ctx.platform?.soc||'未知'}`],['TTO主机',ctx.tto_host],['观察状态',connected?current.health.measurement_status==='valid'?ctx.observation_status:'设备数据资格已到期或不可用':'Web数据断开，来源状态未知'],['工作阶段',ctx.task_metadata_available&&connected?`${({background:'背景',work:'工作',final_recovery:'回落'} as Record<string,string>)[ctx.task_phase]||'等待阶段'} · 客户端在途 ${ctx.active_requests??'未知'} / 槽位 ${ctx.client_slots??'未知'}`:'未接入任务记录'],['推理模型',ctx.task_model?'任务登记：'+ctx.task_model:'未接入任务模型登记'],['服务端执行 / 排队','未接入'],['热模型',current.model.model_id?'冻结 G2 · '+current.model.model_id.slice(0,12):'尚未加载'],['风扇控制',`天山OS：${lineValue(metric('fan.mode'))??'未知'}；TTO：只读建议`],['过程 / 源epoch',`${current.run_id||'—'} / ${current.source_epoch??'—'}`],['Web进程开销',`${fmt(lineValue(metric('host.cpu')))} %单核等效 / ${fmt(lineValue(metric('host.rss')))} MiB RSS`],['观察时长',fmt((current.run_elapsed_ms||0)/1000,0)+' s'],['Jetson RAM',`${fmt(lineValue(ram),0)} / ${fmt(lineValue(metric('memory.ram.total')),0)} ${ram?.unit||'MB'}`]].forEach(([k,v])=>row(dl,k,v));
}
function renderFields(){
 if(!current)return;const query=$<HTMLInputElement>('search').value.toLowerCase(),group=$<HTMLSelectElement>('group').value;
 const tbody=$<HTMLTableSectionElement>('fieldRows');clean(tbody);
 current.metrics.filter(m=>(m.id+' '+m.label).toLowerCase().includes(query)&&m.id.startsWith(group)).forEach(m=>{const tr=document.createElement('tr');cell(tr,m.label+' / '+m.id);cell(tr,lineValue(m)??(m.last_observation?'上次 '+m.last_observation.value:'—'));cell(tr,m.unit);cell(tr,m.kind+' / '+statusLabels[m.status]);cell(tr,m.source_ref);tr.title=`${m.reason_code||''}；${m.sample_id}；${dateLabel(m.received_at_utc)}`;tbody.append(tr);});text('fieldCount',`${current.metrics.length}项`);
 const health=$<HTMLTableSectionElement>('healthRows');clean(health);current.metrics.forEach(m=>{const tr=document.createElement('tr');cell(tr,m.source_id);cell(tr,m.label);cell(tr,statusLabels[m.status]);cell(tr,`${fmt((m.age_lower_bound_ms||0)/1000)}s / ${fmt(Math.max(0,(m.remaining_valid_ms||0)-(performance.now()-received))/1000)}s`);cell(tr,dateLabel(m.received_at_utc));health.append(tr);});
 text('healthSummary',`${current.metrics.filter(m=>m.status==='valid').length}项有效 / ${current.metrics.filter(m=>m.status==='unverified').length}项待确认`);
 text('sourceStatus',`Web：${connected?'已连接':'断开'}；设备数据：${current.health.measurement_status}；模型：${phaseLabels[current.model.phase]}。HTTP成功、源有效与模型可用分别判定。`);
}
function renderEvents(){
 const source=$<HTMLSelectElement>('eventSource').value,level=$<HTMLSelectElement>('eventLevel').value;clean($('eventList'));
 events.filter(e=>(!source||source===e.source)&&(!level||level===e.severity)).slice().reverse().forEach(e=>{const div=document.createElement('div');div.className='event-row';div.textContent=`${dateLabel(e.first_at_utc)} — ${dateLabel(e.last_at_utc)}　${e.source} · ${e.reason} ×${e.count}`;$('eventList').append(div);});text('eventCount',`${events.length}条`);
}
function renderEventTimeline(){
 if(!current)return;const end=current.run_elapsed_ms||0,start=Math.max(0,end-range*60000),visible=events.filter(e=>e.service_epoch===current?.service_epoch&&e.run_id===current?.run_id&&e.source_epoch===current?.source_epoch&&e.elapsed_ms!==null&&e.elapsed_ms>=start&&e.elapsed_ms<=end);
 $('eventEmpty').style.display=visible.length?'none':'block';
 const bucketWidth=Math.max(1000,(end-start)/6),buckets=new Map<number,number[]>();visible.forEach((e,i)=>{const bin=Math.floor((e.elapsed_ms-start)/bucketWidth);buckets.set(bin,[...(buckets.get(bin)||[]),i]);});
 charts[4].setOption({animation:false,grid:{left:65,right:30,top:4,bottom:4},xAxis:{type:'value',min:start,max:Math.max(end,start+1000),show:false},yAxis:{type:'value',min:0,max:1,show:false},tooltip:{formatter:(p:any)=>{const e=events.find(e=>e.id===p.data.eventId);return e?`${esc(e.source)} · ${esc(e.reason)}<br>发生 ${esc(timeLabel(e.elapsed_ms))}<br>Web首次到达/记录 ${esc(dateLabel(e.first_at_utc))}<br>最近记录 ${esc(dateLabel(e.last_at_utc))} · ${e.count}次`:'—';}},dataZoom:[{type:'inside',filterMode:'none'}],series:[{type:'scatter',symbol:'diamond',symbolSize:7,itemStyle:{color:'#b58a46'},data:visible.map((e,i)=>({eventId:e.id,value:[e.elapsed_ms,.5,e.reason],label:{show:buckets.get(Math.floor((e.elapsed_ms-start)/bucketWidth))?.[0]===i,formatter:(buckets.get(Math.floor((e.elapsed_ms-start)/bucketWidth))?.length||0)>1?'此处'+buckets.get(Math.floor((e.elapsed_ms-start)/bucketWidth))!.length+'条事件':e.reason,fontSize:9,position:'top',align:'left'}}))}]});
}

charts[4].on('click',(params:any)=>{const e=events.find(e=>e.id===params.data.eventId);if(!e)return;text('eventSelection',`${e.source} · ${e.reason} ｜ 发生 ${timeLabel(e.elapsed_ms)} ｜ Web首次到达/记录 ${dateLabel(e.first_at_utc)} ｜ 最近 ${dateLabel(e.last_at_utc)} ｜ 重复 ${e.count}次`);$('eventSelection').hidden=false;});

async function refreshData(){
 if(!current||paused||busy)return;busy=true;
 try{const end=current.run_elapsed_ms||0,from=Math.max(0,end-range*60000);let ids=current.metrics.filter(m=>m.id.startsWith('temperature.')||m.id.startsWith('power.')&&!m.id.endsWith('.average')||m.id.startsWith('fan.pwm.')||m.id==='fan.rpm').map(m=>m.id).slice(0,32);const source=[current.service_epoch,current.run_id,current.source_epoch].join(':');
 const group=[current.service_epoch,current.run_id,current.source_epoch,range,ids.join(',')].join(':');
 if(group!==seriesGroup){seriesCache.clear();lastSeriesFetch=null;seriesGroup=group;}
 const deltaFrom=Math.max(from,lastSeriesFetch??from);
 const [s,e]=await Promise.all([api(`series?ids=${encodeURIComponent(ids.join(','))}&from=${deltaFrom}&to=${end}&max_points=2000`),api('events?limit=1000')]);if(source!==[current?.service_epoch,current?.run_id,current?.source_epoch].join(':')||paused||seriesGroup!==group)return;
 for(const incoming of s.series as Series[]){const prior=seriesCache.get(incoming.id);const points=new Map<string,any>();for(const p of [...(prior?.points||[]),...incoming.points])if(p.t>=from)points.set([p.t,p.sample_id,p.status].join(':'),p);seriesCache.set(incoming.id,{...incoming,sampling:prior?.sampling==='bucket_first_last_min_max_and_gaps'?prior.sampling:incoming.sampling,points:[...points.values()].sort((a,b)=>a.t-b.t).slice(-18002)});}
 lastSeriesFetch=end;seriesData=[...seriesCache.values()];events=e.events.filter((v:any)=>v.service_epoch===current?.service_epoch&&(v.run_id===null||v.run_id===current?.run_id&&v.source_epoch===current?.source_epoch));renderCharts();renderEvents();await Promise.all([renderComparison(),renderContext()]);
 }catch{/* HTTP/API failure never creates measurements. SSE owns connection state. */}finally{busy=false;}
}
function expireCurrent(disconnected=false){
 if(!current)return false;
 const elapsed=performance.now()-received;let changed=false;
 for(const m of current.metrics){
  if(m.status==='valid'&&(disconnected||m.remaining_valid_ms===null||m.remaining_valid_ms<=elapsed)){
   m.value=null;m.status='stale';m.reason_code=disconnected?'source_disconnected':'source_expired';changed=true;
  }
 }
 if(disconnected||current.health.protection_remaining_valid_ms<=elapsed){
  if(current.health.protection_status!=='unknown')changed=true;
  current.health.protection_status='unknown';
 }
 const tj=metric('temperature.tj');
 current.health.measurement_status=current.run_id===null?'waiting':tj?.status==='valid'?'valid':'unavailable';
 if(current.model.model_id!==null&&(disconnected||current.model.remaining_valid_ms<=elapsed||tj?.status!=='valid')){
  if(current.model.phase!=='unavailable'||current.predictions.length)changed=true;
  current.model.Tf_C=current.model.Ts_C=current.model.E_C=null;current.model.phase='unavailable';current.predictions=[];
 }
 if(disconnected||current.advisory.remaining_valid_ms<=elapsed||current.model.phase==='unavailable'||current.health.protection_status==='unknown'){
  if(current.advisory.value_percent!==null)changed=true;
  current.advisory.value_percent=null;
  if(current.advisory.status==='available'){current.advisory.status='withheld';current.advisory.reason='当前数据资格已撤销';}
 }
 for(const n of current.model.nodes){
  const status=n.metric_id?metric(n.metric_id)?.status||'unknown':n.role==='estimate'||n.id==='forecast'?current.model.phase==='unavailable'?'unknown':n.status:n.id==='risk'?current.health.protection_status==='unknown'?'unknown':n.status:n.status;
  if(n.status!==status){n.status=status;changed=true;}
 }
 const valid=new Set(current.model.nodes.filter(n=>n.status==='valid').map(n=>n.id));
 for(const e of current.model.edges)if(e.animate_allowed&&(current.model.phase==='unavailable'||!valid.has(e.from)||!valid.has(e.to))){e.animate_allowed=false;changed=true;}
 return changed;
}
function renderCurrent(){renderHeader();renderMetrics();renderModel();renderFuture();renderFields();renderContextRows();}
function accept(s:Snapshot,at=performance.now()){
 latest=s;latestReceived=at;if(paused)return;received=at;current=structuredClone(s);
 const run=[s.service_epoch,s.run_id,s.source_epoch].join(':');if(lastRun!==run){charts.forEach(c=>c.dispatchAction({type:'dataZoom',start:0,end:100}));seriesData=[];events=[];lastContext=null;clean($('contextRows'));$('eventSelection').hidden=true;renderEventTimeline();renderEvents();lastRun=run;originUtc=Date.parse(s.server_time_utc)-(s.run_elapsed_ms||0);}
 const comparisonChanged=predictionGroup!==comparisonKey();if(comparisonChanged)invalidateComparison();
 expireCurrent(!connected);renderCurrent();if(comparisonChanged)void renderComparison().catch(()=>{});void refreshData();
}
function connect(){const stream=new EventSource('/api/v1/stream');['snapshot','quality','resync','run_changed'].forEach(name=>stream.addEventListener(name,e=>{connected=true;accept(JSON.parse((e as MessageEvent).data));}));stream.addEventListener('heartbeat',()=>{connected=true;renderHeader();});stream.onerror=()=>{connected=false;if(!paused){expireCurrent(true);renderCurrent();}else renderHeader();};}
$('pause').onclick=()=>{paused=!paused;text('pause',paused?'恢复实时':'暂停画面');document.body.classList.toggle('paused',paused);if(!paused&&latest)accept(latest,latestReceived);renderHeader();renderModel();};
$('fullscreen').onclick=()=>{if(document.fullscreenElement)void document.exitFullscreen();else void document.documentElement.requestFullscreen();};
$('range').onchange=()=>{range=Number($<HTMLSelectElement>('range').value);localStorage.setItem('tto-range',String(range));void refreshData();};
$('horizon').onchange=()=>{horizon=Number($<HTMLSelectElement>('horizon').value);void renderComparison();};
$('resetZoom').onclick=()=>charts[0].dispatchAction({type:'dataZoom',start:0,end:100});
$('motion').onchange=()=>{const checked=$<HTMLInputElement>('motion').checked;document.body.classList.toggle('reduced-motion',checked);localStorage.setItem('tto-motion',String(checked));};
$('extra').onchange=()=>{extra=$<HTMLInputElement>('extra').checked;localStorage.setItem('tto-extra',String(extra));renderCharts();};
['search','group'].forEach(id=>$(id).addEventListener('input',renderFields));['eventSource','eventLevel'].forEach(id=>$(id).addEventListener('change',renderEvents));
document.addEventListener('visibilitychange',()=>document.body.classList.toggle('background',document.hidden));
$('loginForm').onsubmit=async e=>{e.preventDefault();const r=await fetch('/api/v1/session',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:$<HTMLInputElement>('password').value}),credentials:'same-origin'});if(r.ok){$<HTMLInputElement>('password').value='';$<HTMLDialogElement>('login').close();location.reload();}else text('loginMessage','口令不匹配或请求过于频繁。');};
setInterval(()=>{if(!current||paused)return;if(expireCurrent(!connected))renderCurrent();},200);
(async()=>{try{const boot=await api('bootstrap');tz=boot.timezone;connected=true;accept(await api('snapshot'));connect();}catch{renderHeader();}})();
