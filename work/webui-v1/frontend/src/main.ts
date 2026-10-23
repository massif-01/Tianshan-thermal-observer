import * as echarts from 'echarts';
import type {Snapshot,Metric,Series,SeriesResponse,Bootstrap,Prediction} from './types';
import {icon,chevron,globe,more,menu as menuIcon,pauseMark,checkMark,brandMark,wordmark} from './icons';
import {lang,locale,langNames,langShort,setLang,t,be,translateDom} from './i18n';
import './style.css';

const UI_VERSION='1.0.0-rc.6-ui.1';
const srcName:Record<string,string>={source:t('数据源'),'web-source':t('数据源连接'),observer:t('模型'),board:t('主板'),runner:t('任务'),clock:t('时钟'),web:t('网页服务'),publication:t('显示发布')};
const root=document.querySelector<HTMLDivElement>('#app')!;
const chartLabel:Record<string,string>={temperature:t('实测结温与模型估计'),residual:t('估计与实测的差距'),compose:t('热状态构成'),cpugpu:t('CPU 与 GPU 温度'),power:t('GPU 与 CPU·SoC·内存 两路供电功率'),pwm:t('已执行 PWM 与天山OS 目标 PWM')};
const laneChart=(id:string,h:number,ph?:string)=>`<div class="lane-chart"><div id="${id}" class="chart" role="img" aria-label="${t('{name}，最近时间范围',{name:chartLabel[id]||''})}" style="height:${h}px"></div>${ph?`<div id="${ph}" class="ph" hidden></div>`:''}</div>`;
const tile=(label:string)=>`<div class="stat-block"><span class="t-caption">${label}</span>`;
root.innerHTML=`
<div class="wrap">
<header class="bar" id="bar"><a class="brand" href="#trends" aria-label="Tianshan Thermal Observer">${brandMark}${wordmark}</a>
<nav id="nav" aria-label="页内导航"><a href="#trends" class="on">模型与实测</a><a href="#model">热模型</a><a href="#compare">预测对照</a><a href="#context">运行信息</a></nav>
<div class="bar-end"><button id="menuBtn" class="btn menu-btn" aria-label="菜单" aria-expanded="false">${menuIcon}</button><div class="lang-wrap"><button type="button" class="lang" id="langBtn" aria-haspopup="menu" aria-expanded="false" aria-label="界面语言">${globe}<span>${langShort[lang]}</span></button><div class="menu lang-menu" id="langMenu" role="menu" hidden>${(Object.keys(langNames) as (keyof typeof langNames)[]).map(k=>`<button type="button" role="menuitemradio" aria-checked="${k===lang}" data-lang="${k}"><span>${langNames[k]}</span>${k===lang?checkMark:''}</button>`).join('')}</div></div></div></header>
<main class="shell">
<div class="strip"><div class="strip-id" id="stripId"></div><div class="strip-st" id="stripSt" aria-label="连接、设备数据与模型状态"></div></div>
<section id="trends"><div class="head"><div><h2 class="t-title">模型与实测</h2><span class="t-caption" id="trendCaption">实测温度与热模型估计叠在一起看，差距与构成在下方</span></div>
<div class="head-tools"><div class="seg" id="range" role="group" aria-label="时间范围"><button type="button" data-v="5">5 分钟</button><button type="button" data-v="10">10 分钟</button><button type="button" data-v="30">30 分钟</button><button type="button" data-v="60">60 分钟</button></div>
<button class="btn more" id="moreBtn" aria-label="更多操作" aria-haspopup="menu" aria-expanded="false">${more}</button>
<div class="menu" id="moreMenu" role="menu" hidden><button type="button" id="pause" role="menuitem">暂停显示</button><button type="button" id="resetZoom" role="menuitem">重置缩放</button><button type="button" id="fullscreen" role="menuitem">全屏</button><label><input id="motion" type="checkbox">减少动效</label></div></div></div>
<div class="panel trend-panel"><div class="gap-summary" id="gapSummary"></div>
<div class="lane first"><div class="lane-left" id="leftTemp"></div>${laneChart('temperature',190,'phTemp')}</div>
<div class="lane"><div class="lane-left" id="leftRes"></div>${laneChart('residual',96,'phRes')}</div>
<div class="lane"><div class="lane-left" id="leftComp"></div>${laneChart('compose',140,'phComp')}<div class="lane-note t-caption" id="composeNote"></div></div>
<div class="axis-row"><div></div><div id="axisA" class="chart"></div></div>
<div class="group-title"><span class="t-section">模型的输入与外部事件</span><span class="t-caption">这些量决定模型怎么变，与上方共用时间轴</span></div>
<div class="lane tight"><div class="lane-left" id="leftCpuGpu"></div>${laneChart('cpugpu',100)}</div>
<div class="lane"><div class="lane-left" id="leftPower"></div>${laneChart('power',150)}</div>
<div class="lane"><div class="lane-left" id="leftPwm"></div>${laneChart('pwm',150)}</div>
<div class="lane ev-lane"><div class="lane-left"><div class="lane-head">${icon('flag')}<div><span class="t-label">事件</span><span class="t-caption">仅显示有记录的事件</span></div></div></div><div class="lane-chart"><div id="eventTimeline" class="chart" style="height:58px"></div><span id="eventEmpty" class="t-caption" style="position:absolute;left:58px;top:18px">等待有来源的事件</span></div></div>
<div id="eventSelection" class="event-sel t-caption" hidden></div>
<div class="axis-row"><div></div><div id="axisB" class="chart"></div></div></div></section>
<section id="model" class="blk"><div class="head"><div><h2 class="t-title">热模型</h2><span class="t-caption">G2 热模型 · 只读状态估计 · 数据沿线流动</span></div></div>
<div class="model-wrap"><div class="panel main-card"><div class="topo-scroll"><div class="topo" id="topology"><div id="topoFlow"></div><div id="topoNodes"></div></div></div>
<div class="legend t-caption"><span><i></i>模型输入</span><span><i class="dash"></i>实测校正</span><span><i class="dot"></i>一条真实采样经过（不代表热流）</span></div>
<div class="facts"><div><span class="t-caption">保护反馈 · 直接读取主板，不经过模型</span><span class="t-body" id="protect" style="font-weight:500">—</span></div><div><span class="t-caption">风扇建议 · 暂未接入</span><span class="t-body" id="advice">暂无可用的建议依据</span><span class="t-caption" id="adviceReason"></span></div><div><span class="t-caption">稳态需求（研究中）· 暂未接入</span><span class="t-body" style="color:var(--ink2)">本次未计算</span></div></div></div>
<aside class="panel aside-card" id="nodeAside" aria-live="polite"></aside></div></section>
<section id="compare" class="blk"><div class="head"><div><h2 class="t-title">预测对照</h2><span class="t-caption" id="compareCaption">过去发出的 45 秒预测，到了目标时刻，实际结温是多少？</span></div>
<div class="seg" id="horizon" role="group" aria-label="预测时距"><button type="button" data-v="15">+15 秒</button><button type="button" data-v="45">+45 秒</button><button type="button" data-v="90">+90 秒</button></div></div>
<div class="compare-wrap"><div class="panel main-card" style="justify-content:center;gap:14px"><div class="cmp-legend t-label"><span><i class="key" style="background:var(--cTJ)"></i>目标时刻之后的首个有效实测</span><span style="color:var(--cTJ)"><i class="key dash"></i><span style="color:var(--ink2)" id="predName">当时发出的 +45 秒预测</span></span></div>
<div id="comparison" class="compare-chart" role="img" aria-label="过去发出的预测与目标时刻实测对照"></div><p class="t-caption" id="latestMatch">等待这条预测对应的实测温度</p></div>
<aside class="panel aside-card"><div class="ah">${icon('stats')}<div><span class="t-caption" id="scoreCaption">同一次观察、同一模型</span><h3 class="t-section">误差统计</h3></div></div><div id="score"></div>
<div class="future"><span class="t-section" style="padding-top:8px">现在发出的未来参考</span><div id="futureValues"></div><p class="t-caption" id="futureNote">假设负载保持不变，三个时点分别计算，不是连续轨迹，也不是控制指令。</p></div></aside></div></section>
<section id="context" class="blk"><div class="head"><div><h2 class="t-title">运行信息</h2><span class="t-caption">风扇由 TianshanOS 控制，本系统只读</span></div></div>
<div class="cards"><div class="panel"><div class="ch">${icon('eye')}<h3 class="t-section">观察</h3></div><div id="ctxObs"></div></div><div class="panel"><div class="ch">${icon('sliders')}<h3 class="t-section">控制与模型</h3></div><div id="ctxCtl"></div></div><div class="panel"><div class="ch">${icon('health')}<h3 class="t-section">运行状况</h3></div><div id="ctxRun"></div></div></div>
<p class="t-caption" id="contextNote">未接入任务记录；客户端完成不代表GPU停止。RAM用量不用于推断模型驻留。</p></section>
<div class="panel drawers">
<details id="health"><summary>${icon('db')}<span class="t-section">数据源详细状态</span><span class="sp"></span><span class="t-caption" id="healthSummary">等待来源</span>${chevron}</summary><div class="body"><p id="sourceStatus"></p><p id="sourceDiagnostics"></p><div class="table-scroll"><table><thead><tr><th>来源</th><th>字段</th><th>质量</th><th>年龄 / 剩余有效期</th><th>实际接收时刻</th></tr></thead><tbody id="healthRows"></tbody></table></div></div></details>
<details id="events"><summary>${icon('bell')}<span class="t-section">事件与告警</span><span class="sp"></span><span class="t-caption" id="eventCount">0条</span>${chevron}</summary><div class="body"><div class="filters"><select id="eventSource" aria-label="事件来源"><option value="">全部来源</option>${Object.entries(srcName).map(([k,v])=>`<option value="${k}">${v}${lang==='en'?` (${k})`:`（${k}）`}</option>`).join('')}</select><select id="eventLevel" aria-label="事件级别"><option value="">全部级别</option><option value="warning">重要异常</option><option value="info">信息</option></select></div><div id="eventList"></div></div></details>
<details id="fields"><summary>${icon('list')}<span class="t-section">全部已接字段</span><span class="sp"></span><span class="t-caption" id="fieldCount">0项</span>${chevron}</summary><div class="body"><div class="filters"><input id="search" type="search" placeholder="搜索名称或字段ID" aria-label="字段搜索"><select id="group" aria-label="字段分类"><option value="">全部分类</option><option value="temperature.">温度</option><option value="cpu.">逐核CPU</option><option value="usage.">利用率</option><option value="memory.">内存</option><option value="power.">功率</option><option value="fan.">风扇</option><option value="control.">主板温源</option><option value="host.">Web主机进程</option></select></div><div class="table-scroll"><table><thead><tr><th>名称 / ID</th><th>数值 / 原精度</th><th>单位</th><th>类型 / 质量</th><th>来源引用</th></tr></thead><tbody id="fieldRows"></tbody></table></div></div></details></div>
</main>
<footer>${t('Tianshan Thermal Observer · 只读观察 · 研究状态与条件预测不构成风扇控制指令 · 界面')} ${UI_VERSION}</footer></div>
<dialog id="login"><form id="loginForm"><h2 class="t-title">只读访问</h2><input type="hidden" name="username" value="tto-readonly" autocomplete="username"><p>输入安装时生成的本地访问口令。</p><input id="password" type="password" autocomplete="current-password" required aria-label="只读访问口令"><button type="submit">登录</button><p id="loginMessage"></p></form></dialog>`;

translateDom(root);
const $=<T extends HTMLElement=HTMLElement>(id:string)=>document.getElementById(id) as T;
const text=(id:string,v:unknown)=>{$(id).textContent=String(v??'—');};
const html=(id:string,v:string)=>{$(id).innerHTML=v;};
const esc=(v:unknown)=>String(v??'—').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]!));
const phaseLabels:Record<string,string>={not_loaded:t('未开始'),uninitialized:t('未开始'),provisional:t('初始化中'),tracking:t('跟踪中'),degraded:t('降级 · 估计可用，条件不完整'),unavailable:t('暂不可用')};
const statusLabels:Record<string,string>={valid:t('有效'),stale:t('到期'),invalid:t('已失效'),unknown:t('未知'),unverified:t('未确认'),conditional:t('条件估计'),not_supported:t('未提供'),not_configured:t('未配置')};
const evSrc=(s:string)=>srcName[s]||s;
const evReason=(r:string)=>{const m=/^模型阶段：(\w+)$/.exec(r);return m?t('模型阶段：{p}',{p:phaseLabels[m[1]]||m[1]}):be(r);};
const fmt=(v:unknown,n=1)=>typeof v==='number'?v.toFixed(n):v==null?'—':String(v);
const sgn=(v:number|null|undefined,n=1)=>v==null?'—':(Number(v.toFixed(n))<0?'−':'+')+Math.abs(v).toFixed(n);
const neg=(v:number|null|undefined,n=1)=>v==null?'—':(Number(v.toFixed(n))<0?'−':'')+Math.abs(v).toFixed(n);
const unit=(u:string)=>`<span class="t-unit">${u}</span>`;
const C={tj:'#0064d2',cpu:'#c25a12',gpu:'#7a55c9',pwm:'#0e8a7a',ink:'#202124',ink2:'#4f5761',ink3:'#5f6670',grid:'rgba(0,0,0,.07)',warn:'#944b00',warnTint:'#ff8d2814',base:'#dfe3e9',slow:'#b9cdea',fast:'#4f8fdc'};
const MONO='"SF Mono","Fira Code",Menlo,monospace';
const WANT=['temperature.tj','temperature.cpu','temperature.gpu','power.gpu','power.cpu_soc_mss','fan.pwm.actual','fan.pwm.target'];
const MODEL_IDS=['temperature.tj','model.Tf_C','model.Ts_C','model.E_C'];
const MODEL_REFRESH_MS=5000;

type N=number|null;
type Derived={t:number[],tj:N[],tf:N[],ts:N[],e:N[],phase:(string|null)[],res:N[],exact:boolean,returned:number,original:number,valid:number};
let current:Snapshot|null=null, latest:Snapshot|null=null, connected=false,paused=false,range=Number(localStorage.getItem('tto-range')||10),horizon=45,received=performance.now(),tz='Asia/Shanghai',originUtc=0,lastRun='',events:any[]=[],seriesData:Series[]=[];
let latestReceived=received,lastContext:any=null,boot:Bootstrap|null=null,retries=0,pausedAt='',selectedNode='est',switchedAt=0;
let seriesGroup='',seriesGen=0,busyGroup='',lastSeriesFetch:number|null=null,seriesCache=new Map<string,Series>();
let modelGroup='',modelGen=0,modelReq=0,modelInflight='',modelFetchedAt=-Infinity,modelData:Derived|null=null;
let comparisonGeneration=0,predictionRequest=0;
let predictionGroup='',lastPredictionFetch:number|null=null,predictionCache=new Map<string,Prediction>(),predictionLabels:Record<string,any>={};
let lastTJ:{value:number,at:string|null}|null=null,lastFlowSig='';
if(![5,10,30,60].includes(range))range=10;
const motion=localStorage.getItem('tto-motion')==='true'||matchMedia('(prefers-reduced-motion: reduce)').matches;
$<HTMLInputElement>('motion').checked=motion;
document.body.classList.toggle('reduced-motion',motion);

const ids=['temperature','residual','compose','axisA','cpugpu','power','pwm','eventTimeline','axisB','comparison'] as const;
const charts:Record<string,echarts.ECharts>={};
for(const id of ids){charts[id]=echarts.init($(id),undefined,{renderer:'canvas'});charts[id].group='tto-timeline';}
echarts.connect('tto-timeline');
const live=new Set<string>();
const put=(id:string,option:any)=>{charts[id].setOption(option,{replaceMerge:['series']});live.add(id);};
const clearChart=(id:string)=>{charts[id].clear();live.delete(id);};
new ResizeObserver(()=>{Object.values(charts).forEach(c=>c.resize());applyTicks();}).observe($('trends'));
window.addEventListener('resize',()=>{Object.values(charts).forEach(c=>c.resize());applyTicks();});
let tickStep=6e4;
const timeLabel=(v:number)=>new Intl.DateTimeFormat(locale,{timeZone:tz,hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'}).format(originUtc+v);
const clockLabel=(v:number)=>new Intl.DateTimeFormat(locale,{timeZone:tz,hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).format(originUtc+v);
const dateLabel=(value:string|null)=>value?new Intl.DateTimeFormat(locale,{timeZone:tz,month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'}).format(new Date(value)):t('未知');
const hms=(value:string|null)=>value?new Intl.DateTimeFormat(locale,{timeZone:tz,hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'}).format(new Date(value)):t('未知');
function lineValue(m?:Metric){return m&&m.status==='valid'&&m.remaining_valid_ms!==null&&m.remaining_valid_ms>performance.now()-received?m.value:null;}
const metric=(id:string)=>current?.metrics.find(m=>m.id===id);
const clean=(node:HTMLElement)=>node.replaceChildren();
function cell(tr:HTMLTableRowElement,value:unknown){const td=document.createElement('td');td.textContent=String(value??'—');tr.append(td);return td;}
const sepHtml=(v:string)=>esc(v).replace(/ · /g,'<span class="sep">·</span>');
const rowHtml=(k:string,v:unknown,cls='t-body')=>`<div class="row"><span class="t-label">${esc(k)}</span><span class="${cls}">${v==null||v===''?t('未知'):v}</span></div>`;

async function api(path:string){const r=await fetch('/api/v1/'+path,{credentials:'same-origin'});if(r.status===401){if(!$<HTMLDialogElement>('login').open)$<HTMLDialogElement>('login').showModal();throw Error('login');}if(!r.ok)throw Error('read');return r.json();}

const runKey=(s:Snapshot|null=current)=>s?[s.service_epoch,s.run_id,s.source_epoch].join(':'):'';
const modelKey=(s:Snapshot|null=current)=>s?[s.service_epoch,s.run_id,s.source_epoch,s.model.model_id,s.model.spec_id].join(':'):'';
const respKey=(r:SeriesResponse)=>[r.service_epoch,r.run_id,r.source_epoch,r.model_id,r.spec_id].join(':');
const hasModelHistory=()=>!!boot?.series_capabilities?.model_state_history&&MODEL_IDS.filter(id=>id.startsWith('model.')).every(id=>boot!.available_series?.some(s=>s.id===id));
const modelLive=()=>!!current&&['tracking','degraded'].includes(current.model.phase);
const tfNow=()=>modelLive()?current!.model.Tf_C:null;
const tjNow=()=>{const v=lineValue(metric('temperature.tj'));return typeof v==='number'?v:null;};
const resNow=()=>{const a=tjNow(),b=tfNow();return a!==null&&b!=null?a-b:null;};
const deviceOk=()=>!!current&&connected&&current.health.measurement_status==='valid';
const waiting=()=>!current||current.mode==='waiting'||current.run_id===null;

/* ---------- 三种状态 ---------- */
type Dot='ok'|'idle'|'warn'|'danger';
const chip=(dot:Dot,label:string,extra='')=>`<span class="st ${dot} ${extra}"><i></i>${esc(label)}</span>`;
function statuses():string{
 const out:string[]=[];
 const mode=!current?['idle',t('等待数据')]:current.mode==='test_replay'?['warn',t('本地回放样例（非实时设备）')]:current.mode==='live'?['ok',t('实时')]:current.mode==='ended'?['idle',t('观察已结束')]:['idle',t('等待数据')];
 out.push(chip(mode[0] as Dot,mode[1]));
 out.push(!current&&!connected&&!retries?chip('idle',t('正在连接网页服务')):connected?chip('ok',t('网页已连接')):chip('warn',t('网页已断开 · 正在重连')+(retries?t('（第 {n} 次）',{n:retries}):'')));
 if(waiting())out.push(chip('idle',connected?t('设备数据 等待中'):t('设备数据 未知')));
 else if(!connected)out.push(chip('idle',t('设备数据 未知')));
 else if(current!.health.measurement_status==='valid')out.push(chip('ok',t('设备数据有效')));
 else{const m=metric('temperature.tj'),stale=m?.status==='stale',over=stale&&m?.remaining_valid_ms!=null?Math.max(0,Math.round((performance.now()-received-m.remaining_valid_ms)/1000)):0;out.push(chip('warn',stale?t('设备数据已过期')+(over?' '+t('{n} 秒',{n:over}):''):t('设备数据不可用')));}
 const phase=current?.model.phase??'not_loaded';
 if(!current||waiting())out.push(chip('idle',t('模型 未开始')));
 else if(!connected)out.push(chip('idle',t('模型 未知')));
 else if(phase==='tracking')out.push(chip('ok',t('模型跟踪中')));
 else if(phase==='degraded')out.push(chip('warn',t('模型 降级 · 估计可用，条件不完整')));
 else if(phase==='unavailable')out.push(current.health.measurement_status==='valid'?chip('warn',t('模型 暂不可用')):chip('idle',t('模型 已撤回')));
 else out.push(chip('idle',t('模型 {state}',{state:phaseLabels[phase]})));
 if(boot&&!hasModelHistory())out.push(chip('idle',t('模型历史 暂无')));
 else if(boot&&connected&&current&&!waiting()&&modelData&&!modelData.valid&&modelGroup)out.push(chip('idle',t('模型历史 暂无')));
 if(current?.health.protection_status==='active'&&connected)out.push(chip('danger',t('主板报告保护中 · 风扇由 TianshanOS 接管')));
 else if(deviceOk()&&current!.health.protection_status==='unknown')out.push(chip('idle',t('保护信息未知')));
 if(paused)out.push(`<span class="st chip">${pauseMark}${t('已暂停显示 · 后台已领先 {n} 秒',{n:Math.max(0,Math.round((latestReceived-received)/1000))})}</span>`);
 return out.join('');
}
function renderHeader(){
 html('stripSt',statuses());
 const c=current?.context;
 const run=current?.run_id?`${current.run_id.slice(0,8)} · ${t('源 #{n}',{n:current.source_epoch??'—'})}`:'—';
 html('stripId',[[t('观察对象'),c?.observed_device||t('尚未配置')],[t('观察主机'),c?.tto_host||'—'],[t('本次观察'),run],[t('时区'),tz]].map(([k,v],i)=>`<span><span class="t-caption">${k}</span><span class="t-label${i===2?' mono':''}" style="color:var(--ink)">${esc(v)}</span></span>`).join(''));
 text('trendCaption',t('最近 {n} 分钟 · 实测温度与热模型估计叠在一起看，差距与构成在下方',{n:range})+(Date.now()-switchedAt<60000?t(' · 已切换到新的观察过程，曲线从这里重新开始'):''));
 ($('range').querySelectorAll('button') as NodeListOf<HTMLButtonElement>).forEach(b=>{b.classList.toggle('on',Number(b.dataset.v)===range);b.setAttribute('aria-pressed',String(Number(b.dataset.v)===range));});
 ($('horizon').querySelectorAll('button') as NodeListOf<HTMLButtonElement>).forEach(b=>{b.classList.toggle('on',Number(b.dataset.v)===horizon);b.setAttribute('aria-pressed',String(Number(b.dataset.v)===horizon));});
 text('pause',paused?t('继续（恢复实时）'):t('暂停显示'));document.body.classList.toggle('paused',paused);
}

/* ---------- 左侧读数列 ---------- */
const lh=(ic:string,label:string,cap:string)=>`<div class="lane-head">${icon(ic)}<div><span class="t-label">${label}</span>${cap?`<span class="t-caption">${cap}</span>`:''}</div></div>`;
const key=(color:string,label:string,dash=false)=>`<span class="t-caption" style="color:${dash?color:'inherit'}"><i class="key${dash?' dash':''}" style="background:${color}"></i><span style="color:var(--ink3)">${label}</span></span>`;
const big=(cls:string,v:string,u:string,extra='')=>`<span class="big"><b class="${cls}" ${extra}>${v}</b>${unit(u)}</span>`;
function tjCaption():string{
 const m=metric('temperature.tj');
 if(paused&&pausedAt&&tjNow()!==null)return t('暂停于 {time}',{time:pausedAt});
 if(tjNow()!==null)return t('结温 {s} 秒前采样',{s:fmt((m?.age_lower_bound_ms||0)/1000,1)});
 if(waiting())return t('等待第一条有效采样');
 const last=lastTJ??(m?.last_observation?{value:Number(m.last_observation.value),at:m.last_observation.observed_at_utc}:null);
 if(last)return t(connected?'最后有效 {v} °C · {time}':'断开前最后 {v} °C · {time}',{v:fmt(last.value),time:hms(last.at)});
 return t('当前无有效读数');
}
function renderLeft(){
 const tj=tjNow(),tf=tfNow(),phase=current?.model.phase;
 const tfLine=tf!==null&&tf!==undefined?`${fmt(tf)}`:'—';
 const tfCap=phase==='degraded'&&tf!=null?t('估计可用，条件不完整'):'';
 html('leftTemp',lh('thermo',t('温度'),t('实测与模型估计'))+`<div class="lane-val">${key(C.tj,t('实测结温（TJ）'))}${big('t-display',fmt(tj),'°C')}</div><div class="lane-val">${key(C.ink,t('模型估计（Tf）'))}${big('t-metric',tfLine,'°C')}${tfCap?`<span class="t-caption warn-text">${tfCap}</span>`:''}</div><span class="t-caption">${esc(tjCaption())}</span>`);
 const r=resNow();
 html('leftRes',lh('wave',t('估计与实测的差距'),t('实测 − 模型估计（吸收实测后）'))+`<span class="big"><b class="t-metric">${sgn(r,2)}</b>${unit('°C')}</span><span class="t-caption">${modelLive()?t('灰带为 ±1 °C，超出变橙'):current&&connected&&!waiting()?t('当前估计已撤回'):'—'}</span>`);
 const tsv=modelLive()?current!.model.Ts_C:null,ev=modelLive()?current!.model.E_C:null;
 const fast=tf!=null&&tsv!=null?tf-tsv:null,slow=tsv!=null&&ev!=null?tsv-ev:null;
 const l=(color:string,label:string,v:string,n:boolean)=>`<div style="display:flex;justify-content:space-between;align-items:baseline"><span class="t-caption"><i class="key swatch" style="background:${color}"></i>${label}</span><span class="t-body num"${n?' style="color:var(--warnText)"':''}>${v}</span></div>`;
 html('leftComp',lh('layers',t('热状态构成'),t('模型内部量，不是传感器'))+`<div class="lane-list" style="display:flex;flex-direction:column;gap:7px">${l(C.fast,t('快热部分'),fast==null?'—':sgn(fast)+' °C',fast!=null&&fast<0)}${l(C.slow,t('慢热部分'),slow==null?'—':sgn(slow)+' °C',slow!=null&&slow<0)}${l(C.base,t('等效边界 E'),ev==null?'—':neg(ev)+' °C',false)}</div><span class="t-caption">${t('三层相加 = 模型估计 Tf（°C）')}${modelData&&modelData.valid&&hasNeg(modelData)?t('；斜纹处为负值'):''}</span>`);
 html('leftCpuGpu',lh('chip',t('CPU · GPU 温度'),'')+`<span class="t-body num">${key(C.cpu,'CPU')} <b style="font-weight:500">${fmt(lineValue(metric('temperature.cpu')))}</b> ${unit('°C')}</span><span class="t-body num">${key(C.gpu,'GPU')} <b style="font-weight:500">${fmt(lineValue(metric('temperature.gpu')))}</b> ${unit('°C')}</span>`);
 html('leftPower',lh('bolt',t('功率'),t('两路独立供电，非整机总和'))+`<div class="lane-val">${key(C.gpu,t('GPU 供电'))}${big('t-metric',fmt(lineValue(metric('power.gpu')),2),'W')}</div><div class="lane-val">${key(C.cpu,t('CPU·SoC·内存 供电'))}${big('t-metric',fmt(lineValue(metric('power.cpu_soc_mss')),2),'W')}</div>`);
 const rpm=metric('fan.rpm');
 html('leftPwm',lh('fan',t('风扇输出'),t('由 TianshanOS 执行'))+`<div class="lane-val">${key(C.pwm,t('已执行 PWM'))}${big('t-metric',fmt(lineValue(metric('fan.pwm.actual')),0),'%')}</div><div class="lane-val">${key(C.pwm,t('TianshanOS 目标'),true)}${big('t-metric',fmt(lineValue(metric('fan.pwm.target')),0),'%','style="color:var(--ink2)"')}</div><span class="t-caption">${t('转速有效性未确认')}${rpm?.last_observation?t(' · 原报 {v}',{v:esc(rpm.last_observation.value)}):''}</span>`);
}

/* ---------- 模型历史：派生量 ---------- */
function derive(r:SeriesResponse):Derived|null{
 const by=(id:string)=>r.series.find(s=>s.id===id),[a,b,c,d]=MODEL_IDS.map(by);
 if(!a||!b||!c||!d)return null;
 const n=a.points.length;
 if([b,c,d].some(s=>s.points.length!==n))return null;
 for(let i=0;i<n;i++)if(b.points[i].t!==a.points[i].t||c.points[i].t!==a.points[i].t||d.points[i].t!==a.points[i].t)return null;
 const tj=a.points.map(p=>p.value),tf=b.points.map(p=>p.value),ts=c.points.map(p=>p.value),e=d.points.map(p=>p.value);
 const res=tj.map((v,i)=>v!==null&&tf[i]!==null?v-(tf[i] as number):null);
 const all=[a,b,c,d];
 return {t:a.points.map(p=>p.t),tj,tf,ts,e,phase:b.points.map(p=>p.phase_at_sample??null),res,
  exact:all.every(s=>s.sampling==='actual_samples'&&(s.original_points==null||s.returned_points==null||s.original_points===s.returned_points)),
  returned:b.returned_points??n,original:b.original_points??n,valid:tf.filter(v=>v!==null).length};
}
const hasNeg=(d:Derived)=>d.tf.some((v,i)=>v!==null&&d.ts[i]!==null&&v<(d.ts[i] as number))||d.ts.some((v,i)=>v!==null&&d.e[i]!==null&&v<(d.e[i] as number));
function gapStats(d:Derived){
 const abs=d.res.filter((v):v is number=>v!==null).map(Math.abs).sort((x,y)=>x-y);
 if(!abs.length)return null;
 const rank=.95*(abs.length-1),lo=Math.floor(rank),hi=Math.ceil(rank);
 return {mean:abs.reduce((s,v)=>s+v,0)/abs.length,p95:abs[lo]*(1-(rank%1))+abs[hi]*(rank%1),max:abs[abs.length-1],n:abs.length};
}
function renderGapSummary(){
 const d=modelData&&modelData.valid?modelData:null,s=d?gapStats(d):null,tag=d&&!d.exact?t(' · 近似'):'';
 const cellH=(label:string,v:string|null)=>`<div><span class="t-caption">${label}${tag}</span><b>${v===null?'<span class="t-metric" style="color:var(--ink3)">—</span>':`<span class="t-metric">${v}</span>`}${unit('°C')}</b></div>`;
 const basis=!s?'—':d!.exact?t('全部 {n} 个样本',{n:s.n}):t('抽样 {r} / {o} 点 · 近似',{r:d!.returned,o:d!.original});
 html('gapSummary',`<div><span class="t-label" style="color:var(--ink);font-weight:600">${t('估计与实测的差距')}</span><span class="t-caption sub">${s?t('实测 − 模型估计（吸收实测后）'):t('暂无模型历史，差距暂无内容')}</span></div>${cellH(t('平均偏差（绝对值）'),s?fmt(s.mean,2):null)}${cellH(t('偏差 95 分位'),s?fmt(s.p95,2):null)}${cellH(t('最大偏差'),s?fmt(s.max,2):null)}<div><span class="t-caption">${t('统计依据')}</span><span class="t-body sub" style="height:36px">${basis}</span></div>`);
}

/* ---------- 图表 ---------- */
function span():[number,number]{
 if(!current)return [0,1000];
 const ext=!paused&&(!connected||current.health.measurement_status!=='valid')&&current.run_id!==null?performance.now()-received:0;
 const end=Math.max((current.run_elapsed_ms||0)+ext,1000);
 return [Math.max(0,end-range*60000),end];
}
function ticksFor(lo:number,hi:number){
 const w=Math.max(300,$('trends').clientWidth-220),want=Math.max(3,Math.floor(w/110)),steps=[5e3,1e4,3e4,6e4,12e4,3e5,6e5,18e5,36e5];
 const step=steps.find(s=>(hi-lo)/s<=want)||steps[steps.length-1],out:number[]=[];tickStep=step;
 for(let t=Math.ceil((originUtc+lo)/step)*step-originUtc;t<=hi;t+=step)out.push(t);
 return out;
}
function visible():[number,number]{
 const [lo,hi]=span(),z=(charts.axisA.getOption() as any)?.dataZoom?.[0];
 return z&&z.start!=null?[lo+(hi-lo)*z.start/100,lo+(hi-lo)*z.end/100]:[lo,hi];
}
function applyTicks(){
 const [lo,hi]=visible(),ticks=ticksFor(lo,hi);
 for(const id of live)charts[id].setOption({xAxis:{axisLabel:{customValues:ticks},splitLine:{customValues:ticks}}} as any);
}
const xAxis=(lo:number,hi:number,labels:boolean)=>{const ticks=ticksFor(...visible());return {type:'value',min:lo,max:hi,axisLabel:{show:labels,formatter:(v:number)=>tickStep>=6e4?clockLabel(v):timeLabel(v),color:C.ink3,fontSize:11,fontFamily:MONO,hideOverlap:true,customValues:ticks},axisTick:{show:false},axisLine:{show:false},splitLine:{lineStyle:{color:C.grid},customValues:ticks},axisPointer:{label:{formatter:(p:any)=>timeLabel(p.value)}}};};
const yAxis=(o:any={})=>({type:'value',splitNumber:3,splitLine:{lineStyle:{color:C.grid}},axisLine:{show:false},axisTick:{show:false},...o,axisLabel:{color:C.ink3,fontSize:11,fontFamily:MONO,margin:14,...(o.axisLabel||{})}});
const tipPos=(pt:number[],_p:any,_d:any,_r:any,size:any)=>{const [cw,ch]=size.contentSize,[vw,vh]=size.viewSize;return [Math.max(0,pt[0]+14+cw>vw?pt[0]-14-cw:pt[0]+14),Math.max(0,vh-ch-6)];};
const tooltip=(fn:(ps:any[])=>string)=>({trigger:'axis',confine:true,appendToBody:true,backgroundColor:'rgba(250,251,253,.78)',borderWidth:0,padding:0,extraCssText:'border-radius:14px;backdrop-filter:blur(24px) saturate(1.8);-webkit-backdrop-filter:blur(24px) saturate(1.8);border:1px solid rgba(255,255,255,.75);box-shadow:0 8px 28px #1b2b453d;',axisPointer:{type:'line',lineStyle:{type:'dashed',color:C.ink3,width:1}},position:tipPos,formatter:(ps:any)=>{const a=(Array.isArray(ps)?ps:[ps]).filter((p:any)=>p.data&&p.data[1]!=null);return a.length?`<div class="tip"><div class="mono" style="font-weight:600;margin-bottom:4px">${esc(timeLabel(a[0].data[0]))}</div>${fn(a)}</div>`:'';}});
const tipRow=(color:string,name:string,v:string,dash=false)=>`<div class="tr"><span><i class="key${dash?' dash':''}" style="background:${color};color:${color}"></i>${esc(name)}</span><span class="mono"><b>${v}</b></span></div>`;
const grid=(top=8,bottom=6)=>({left:50,right:28,top,bottom});
const zoom=[{type:'inside',filterMode:'none',xAxisIndex:0}];
const pts=(s?:Series)=>s?s.points.map(p=>[p.t,p.value,p.received_at_utc,p.status]):[];
const line=(name:string,data:any[],color:string,width:number,extra:any={})=>({name,type:'line',showSymbol:false,smooth:false,connectNulls:false,color,lineStyle:{width,color},data,...extra});
function gapsOf(rows:{t:number,v:N}[],end:number){const out:[number,number][]=[];let s:number|null=null;for(const p of rows){if(p.v===null){if(s===null)s=p.t;}else if(s!==null){out.push([s,p.t]);s=null;}}if(s!==null)out.push([s,end]);return out;}
function merge(b:[number,number][]){const s=b.slice().sort((x,y)=>x[0]-y[0]),o:[number,number][]=[];for(const x of s){const l=o[o.length-1];if(l&&x[0]<=l[1])l[1]=Math.max(l[1],x[1]);else o.push([x[0],x[1]]);}return o;}
// 设计稿：每条曲线最后一个有效点画实心圆点（停在最后有效点，之后是缺口）。
const endDot=(rows:any[],color:string,size=7)=>{let k=rows.length-1;while(k>=0&&rows[k][1]==null)k--;return k<0?{}:{markPoint:{silent:true,animation:false,symbol:'circle',symbolSize:size,itemStyle:{color},data:[{coord:[rows[k][0],rows[k][1]]}]}};};
const rowsOf=(s?:Series)=>s?s.points.map(p=>({t:p.t,v:p.value})):[];
function abnormalLabel(){if(!current||current.run_id===null)return '';return !connected?t('与服务断开'):current.health.measurement_status!=='valid'?t('数据中断'):'';}
function bands(sets:{t:number,v:N}[][],end:number,label=false){
 const b=merge(sets.flatMap(r=>gapsOf(r,end))),tail=abnormalLabel();
 const lastValid=Math.max(...sets.map(r=>{for(let i=r.length-1;i>=0;i--)if(r[i].v!==null)return r[i].t;return -1;}));
 if(tail&&lastValid>=0&&!b.some(x=>x[1]>=end))b.push([lastValid,end]);
 return merge(b).map(x=>{const t=label&&tail&&x[1]>=end;return [{xAxis:x[0],itemStyle:{color:C.warnTint},label:{show:t,position:'insideTopRight',color:C.warn,fontSize:11,formatter:tail}},{xAxis:x[1]}];});
}
const markArea=(data:any[])=>data.length?{silent:true,data}:undefined;
const hatch=(()=>{const c=document.createElement('canvas');c.width=c.height=8;const g=c.getContext('2d')!;g.strokeStyle='rgba(32,33,36,.5)';g.lineWidth=1;g.beginPath();g.moveTo(-1,9);g.lineTo(9,-1);g.moveTo(-1,1);g.lineTo(1,-1);g.moveTo(7,9);g.lineTo(9,7);g.stroke();return c;})();
function degradedRuns(d:Derived){const out:[number,number][]=[];let s:number|null=null,last=0;d.t.forEach((t,i)=>{const dg=d.tf[i]!==null&&d.phase[i]==='degraded';if(dg){if(s===null)s=t;last=t;}else if(s!==null){out.push([s,last]);s=null;}});if(s!==null)out.push([s,last]);return out;}
const dgBand=(r:[number,number][],label:boolean)=>{const widest=r.reduce((b,x,i)=>x[1]-x[0]>r[b][1]-r[b][0]?i:b,0);return r.map((x,i)=>[{xAxis:x[0],itemStyle:{color:'#5f667014'},label:{show:label&&i===widest,position:'insideTop',color:C.warn,fontSize:11,formatter:t('降级：条件不完整')}},{xAxis:x[1]}]);};

function showPh(id:string,msg:string|null){const el=$(id);el.hidden=msg===null;if(msg!==null)el.textContent=msg;}
function noModelMsg(kind:'res'|'comp'):string|null{
 if(modelData&&modelData.valid)return null;
 const what=t(kind==='res'?'差距':'构成');
 if(waiting())return t('模型尚未开始，{what}暂无内容',{what});
 if(modelInflight&&!modelData)return t('正在读取模型历史…');
 if(boot&&!hasModelHistory())return t('暂无模型历史，{what}暂无内容',{what});
 if(current&&connected&&current.health.measurement_status==='valid'&&current.model.phase==='unavailable')return t('模型暂不可用，{what}暂停；恢复后从新的估计开始',{what:t(kind==='res'?'偏差':'构成')});
 if(!connected||current?.health.measurement_status!=='valid')return t(connected?(modelData?'当前估计已撤回；历史暂无':'当前估计已撤回；历史尚未取得'):(modelData?'当前估计已撤回；断开前的历史暂无':'当前估计已撤回；断开前的历史尚未取得'));
 return t('暂无模型历史，{what}暂无内容',{what});
}
const NAME_TJ=t('实测结温（TJ）'),NAME_TF=t('模型估计（Tf）'),NAME_TFD=t('估计可用，条件不完整');
function drawTemperature(lo:number,hi:number){
 const tj=seriesData.find(s=>s.id==='temperature.tj'),d=modelData&&modelData.valid?modelData:null;
 const series:any[]=[];
 const sets=[rowsOf(tj)];if(d)sets.push(d.t.map((t,i)=>({t,v:d.tf[i]})));
 const area=bands(sets,hi,true);
 if(d)dgBand(degradedRuns(d),true).forEach(x=>area.push(x as any));
 const ma=markArea(area);
 series.push(line(NAME_TJ,pts(tj),C.tj,2.2,{z:3,...(ma?{markArea:ma}:{}),...endDot(pts(tj),C.tj)}));
 if(d){
  const solid=d.t.map((t,i)=>[t,d.phase[i]==='degraded'?null:d.tf[i],null,'valid']);
  const dash=d.t.map((t,i)=>{const dg=d.phase[i]==='degraded',nb=d.phase[i-1]==='degraded'||d.phase[i+1]==='degraded';return [t,d.tf[i]!==null&&(dg||nb)?d.tf[i]:null,null,'valid'];});
  series.push(line(NAME_TF,solid,C.ink,1.4,{z:4,...endDot(d.t.map((t,i)=>[t,d.tf[i]]),C.ink,6)}));
  if(degradedRuns(d).length)series.push(line(NAME_TFD,dash,C.ink,1.4,{z:4,lineStyle:{width:1.4,color:C.ink,type:'dashed'}}));
 }
 const none=!tj||!tj.points.some(p=>p.value!==null);
 showPh('phTemp',none?(waiting()?t('等待第一批数据…'):t('暂无结温历史')):null);
 put('temperature',{animation:false,grid:grid(),xAxis:xAxis(lo,hi,false),yAxis:yAxis({scale:true,axisLabel:{color:C.ink3,fontSize:11,fontFamily:MONO,formatter:(v:number)=>String(Math.round(v))}}),dataZoom:zoom,
  tooltip:tooltip(ps=>{const g=(n:string)=>ps.find(p=>p.seriesName===n);const a=g(NAME_TJ),b=g(NAME_TF)||g(NAME_TFD);
   const i=a&&d?d.t.indexOf(a.data[0]):-1,r=i>=0&&d!.res[i]!==null?sgn(d!.res[i],2):null;
   return (a?tipRow(C.tj,t('实测结温'),`${fmt(a.data[1],1)} °C`):'')+(b?tipRow(C.ink,b.seriesName===NAME_TF?t('模型估计'):t('模型估计（条件不完整）'),`${fmt(b.data[1],1)} °C`,b.seriesName!==NAME_TF):'')+(r?tipRow(C.ink2,t('差距（实测 − 估计）'),`${r} °C`):'');}),series} as any);
}
function drawResidual(lo:number,hi:number){
 const d=modelData&&modelData.valid?modelData:null;
 showPh('phRes',noModelMsg('res'));
 if(!d){clearChart('residual');return;}
 const m=Math.max(1.5,Math.ceil(Math.max(...d.res.map(v=>v===null?0:Math.abs(v)))*2)/2);
 const warn=d.res.map((v,i)=>v!==null&&(Math.abs(v)>1||Math.abs(d.res[i-1]??0)>1||Math.abs(d.res[i+1]??0)>1)?v:null);
 const area=[[{yAxis:-1,itemStyle:{color:'rgba(0,0,0,.055)'}},{yAxis:1}],...bands([d.t.map((t,i)=>({t,v:d.res[i]}))],hi)];
 put('residual',{animation:false,grid:grid(),xAxis:xAxis(lo,hi,false),yAxis:yAxis({min:-m,max:m,interval:m,axisLabel:{color:C.ink3,fontSize:11,fontFamily:MONO,formatter:(v:number)=>(v>0?'+':'')+v}}),dataZoom:zoom,
  tooltip:tooltip(ps=>tipRow(C.ink2,t('差距（实测 − 估计）'),`${sgn(ps[0].data[1],2)} °C`)),
  series:[line(t('估计与实测的差距'),d.t.map((t,i)=>[t,d.res[i]]),C.ink2,1.4,{z:3,markArea:{silent:true,data:area},markLine:{silent:true,symbol:'none',animation:false,label:{show:false},lineStyle:{color:C.ink3,width:1,type:'solid'},data:[{yAxis:0}]},...endDot(d.t.map((t,i)=>[t,d.res[i]]),C.ink2,6)}),line(t('超出 ±1 °C'),d.t.map((t,i)=>[t,warn[i]]),C.warn,1.8,{z:4,tooltip:{show:false}})]} as any);
}
function drawCompose(lo:number,hi:number){
 const d=modelData&&modelData.valid?modelData:null;
 showPh('phComp',noModelMsg('comp'));
 text('composeNote','');
 if(!d){clearChart('compose');return;}
 type Seg={x:number[],lo:number[],hi:number[],neg:boolean,color:string};
 const segs:Seg[]=[],ok=(i:number)=>d.e[i]!==null&&d.ts[i]!==null&&d.tf[i]!==null;
 const layers=[{lo:(_:number)=>0,hi:(i:number)=>d.e[i] as number,color:C.base,rel:null as null|((i:number)=>boolean)},
  {lo:(i:number)=>d.e[i] as number,hi:(i:number)=>d.ts[i] as number,color:C.slow,rel:(i:number)=>(d.ts[i] as number)<(d.e[i] as number)},
  {lo:(i:number)=>d.ts[i] as number,hi:(i:number)=>d.tf[i] as number,color:C.fast,rel:(i:number)=>(d.tf[i] as number)<(d.ts[i] as number)}];
 let anyFast=false,anySlow=false;
 for(const L of layers){
  let cur:Seg|null=null;
  for(let i=0;i<d.t.length;i++){
   if(!ok(i)){cur=null;continue;}
   const ng=L.rel?L.rel(i):false;
   if(L===layers[2]&&ng)anyFast=true;if(L===layers[1]&&ng)anySlow=true;
   if(!cur||cur.neg!==ng){const prev:Seg|null=cur;cur={x:[],lo:[],hi:[],neg:ng,color:L.color};if(prev){cur.x.push(d.t[i-1]);cur.lo.push(L.lo(i-1));cur.hi.push(L.hi(i-1));}segs.push(cur);}
   cur.x.push(d.t[i]);cur.lo.push(L.lo(i));cur.hi.push(L.hi(i));
  }
 }
 const vals=d.t.flatMap((_,i)=>ok(i)?[d.e[i] as number,d.ts[i] as number,d.tf[i] as number]:[]);
 const ymin=Math.min(0,Math.floor(Math.min(...vals,0)/10)*10),ymax=Math.max(20,Math.ceil(Math.max(...vals,0)/20)*20);
 const items=segs.map((s,i)=>({value:[s.x[0],s.hi[0]],i}));
 const note=[anyFast?t('此时段快热低于慢热'):'',anySlow?t('此时段慢热低于等效边界'):''].filter(Boolean).join(t('；'));
 text('composeNote',note?t('{note}：负值按实际画出，不截成 0，也不取绝对值',{note}):'');
 const custom={type:'custom',name:t('构成'),silent:true,z:1,clip:true,encode:{x:0,y:1},data:items,renderItem:(p:any,api:any)=>{
  const s=segs[p.dataIndex],top=s.x.map((x,k)=>api.coord([x,s.hi[k]])),bot=s.x.map((x,k)=>api.coord([x,s.lo[k]])).reverse();
  const shape={points:[...top,...bot]},fill={type:'polygon',shape,style:{fill:s.color,stroke:'none'}};
  return s.neg?{type:'group',children:[fill,{type:'polygon',shape,style:{fill:{type:'pattern',image:hatch,repeat:'repeat'},stroke:'none'}}]}:fill;}};
 const ghost=(name:string,arr:N[],color:string)=>line(name,d.t.map((t,i)=>[t,ok(i)?arr[i]:null]),color,1,{z:2,lineStyle:{width:1,color,opacity:0},itemStyle:{color}});
 const area=[...bands([d.t.map((t,i)=>({t,v:ok(i)?1:null}))],hi),...dgBand(degradedRuns(d),false)];
 put('compose',{animation:false,grid:grid(),xAxis:xAxis(lo,hi,false),yAxis:yAxis({min:ymin,max:ymax,splitNumber:4}),dataZoom:zoom,
  tooltip:tooltip(ps=>{const g=(n:string)=>ps.find(p=>p.seriesName===n)?.data[1] as number;const e=g(t('等效边界 E')),ts=g(t('慢热状态 Ts')),tf=g(t('模型估计 Tf'));
   return tipRow(C.fast,t('快热部分（Tf − Ts）'),`${sgn(tf-ts)} °C`)+tipRow(C.slow,t('慢热部分（Ts − E）'),`${sgn(ts-e)} °C`)+tipRow(C.base,t('等效边界 E'),`${neg(e)} °C`)+tipRow(C.ink,t('模型估计 Tf'),`${neg(tf)} °C`);}),
  series:[custom,{...ghost(t('等效边界 E'),d.e,C.base),markArea:markArea(area)},ghost(t('慢热状态 Ts'),d.ts,C.slow),ghost(t('模型估计 Tf'),d.tf,C.fast)]} as any);
}
function simpleLane(id:string,lo:number,hi:number,defs:{id:string,name:string,color:string,w:number,dash?:boolean}[],y:any,u:string,digits:number){
 const list=defs.map(d=>({d,s:seriesData.find(s=>s.id===d.id)}));
 const area=bands(list.map(x=>rowsOf(x.s)).filter(r=>r.length),hi);
 put(id,{animation:false,grid:grid(),xAxis:xAxis(lo,hi,false),yAxis:yAxis(y),dataZoom:zoom,
  tooltip:tooltip(ps=>ps.map(p=>{const def=defs.find(d=>d.name===p.seriesName)!;return tipRow(def.color,p.seriesName,`${fmt(p.data[1],digits)} ${u}`,!!def.dash)+`<div class="t-caption" style="margin:-2px 0 2px 17px">${esc(p.data[2]?hms(p.data[2]):'')}</div>`;}).join('')),
  series:list.map(({d,s},i)=>line(d.name,pts(s),d.color,d.w,{z:3,lineStyle:{width:d.w,color:d.color,type:d.dash?'dashed':'solid',opacity:d.dash?.85:1},...(i===0&&area.length?{markArea:{silent:true,data:area}}:{}),...(d.dash?{}:endDot(pts(s),d.color,7))}))} as any);
}
function renderEventTimeline(){
 if(!current)return;const [start,end]=span(),visibleEvents=events.filter(e=>e.service_epoch===current?.service_epoch&&e.run_id===current?.run_id&&e.source_epoch===current?.source_epoch&&e.elapsed_ms!==null&&e.elapsed_ms>=start&&e.elapsed_ms<=end);
 $('eventEmpty').style.display=visibleEvents.length?'none':'block';
 const bucketWidth=Math.max(1000,(end-start)/6),buckets=new Map<number,number[]>();visibleEvents.forEach((e,i)=>{const bin=Math.floor((e.elapsed_ms-start)/bucketWidth);buckets.set(bin,[...(buckets.get(bin)||[]),i]);});
 put('eventTimeline',{animation:false,grid:{left:50,right:28,top:6,bottom:4},xAxis:xAxis(start,end,false),yAxis:{type:'value',min:0,max:1,show:false},tooltip:{confine:true,appendToBody:true,backgroundColor:'rgba(250,251,253,.78)',borderWidth:0,extraCssText:'border-radius:14px;backdrop-filter:blur(24px) saturate(1.8);-webkit-backdrop-filter:blur(24px) saturate(1.8);border:1px solid rgba(255,255,255,.75);box-shadow:0 8px 28px #1b2b453d;',formatter:(p:any)=>{const e=events.find(e=>e.id===p.data.eventId);return e?`<div class="tip">${esc(evSrc(e.source))} · ${esc(evReason(e.reason))}<br>${esc(t('发生 {time}',{time:timeLabel(e.elapsed_ms)}))}<br>${esc(t('Web首次到达/记录 {time}',{time:dateLabel(e.first_at_utc)}))}<br>${esc(t('最近记录 {time} · {n}次',{time:dateLabel(e.last_at_utc),n:e.count}))}</div>`:'';}},dataZoom:zoom,
  series:[{type:'scatter',symbol:'diamond',symbolSize:9,labelLayout:{hideOverlap:true},data:visibleEvents.map((e,i)=>{const first=buckets.get(Math.floor((e.elapsed_ms-start)/bucketWidth))?.[0]===i,n=buckets.get(Math.floor((e.elapsed_ms-start)/bucketWidth))?.length||0;return {eventId:e.id,value:[e.elapsed_ms,.62,e.reason],itemStyle:{color:e.severity==='warning'?C.warn:C.ink2},label:{show:first,formatter:n>1?t('此处 {n} 条事件',{n}):evReason(e.reason),fontSize:12,color:e.severity==='warning'?C.warn:C.ink3,position:'bottom',distance:4,align:'center'}};})}]} as any);
}
function renderCharts(){
 const [lo,hi]=span();
 drawTemperature(lo,hi);drawResidual(lo,hi);drawCompose(lo,hi);
 simpleLane('cpugpu',lo,hi,[{id:'temperature.cpu',name:t('CPU 温度'),color:C.cpu,w:1.5},{id:'temperature.gpu',name:t('GPU 温度'),color:C.gpu,w:1.5}],{scale:true,axisLabel:{color:C.ink3,fontSize:11,fontFamily:MONO,formatter:(v:number)=>String(Math.round(v))}},'°C',1);
 simpleLane('power',lo,hi,[{id:'power.cpu_soc_mss',name:t('CPU·SoC·内存 供电'),color:C.cpu,w:1.5},{id:'power.gpu',name:t('GPU 供电'),color:C.gpu,w:1.5}],{min:0},'W',2);
 simpleLane('pwm',lo,hi,[{id:'fan.pwm.target',name:t('TianshanOS 目标'),color:C.pwm,w:1.5,dash:true},{id:'fan.pwm.actual',name:t('已执行 PWM'),color:C.pwm,w:2.2}],{min:0,max:100,splitNumber:2},'%',0);
 for(const id of ['axisA','axisB'])put(id,{animation:false,grid:{left:50,right:28,top:0,bottom:18},xAxis:xAxis(lo,hi,true),yAxis:{type:'value',show:false,min:0,max:1},dataZoom:zoom,series:[{type:'line',data:[]}]} as any);
 renderEventTimeline();applyTicks();
}

/* ---------- 热模型图 ---------- */
const nodeText:Record<string,string>={pg:t('GPU 供电功率，模型的输入之一，与 CPU·SoC·内存供电互相独立。'),pc:t('CPU、SoC 与内存的供电功率，模型的输入之一，不是整机总功耗。'),u:t('天山 OS 已执行的风扇输出（PWM），模型的散热输入。TTO 只读。'),tj:t('实测结温。模型用它校正自己的估计，不是功耗，也不是预测。'),est:t('Tf、Ts 是 G2 热模型对热状态的估计，不是传感器读数。Ts 是模型内部的慢变量，E 是等效边界，都不代表结构或环境温度。'),fc:t('假设当前负载保持不变，分别算出 +15 / +45 / +90 秒后的结温参考；三点分别实算，不是连续轨迹，也不是控制指令。')};
const nodeTitle:Record<string,string>={pg:t('GPU 功率'),pc:t('CPU·SoC·内存 功率'),u:t('风扇输出（已执行）'),tj:t('结温（实测）'),est:t('热状态估计'),fc:t('结温预测')};
const nodeMetric:Record<string,string>={pg:'power.gpu',pc:'power.cpu_soc_mss',u:'fan.pwm.actual',tj:'temperature.tj'};
const edgeOn=(from:string,to:string)=>!!current&&connected&&!paused&&current.model.edges.some(e=>e.from===from&&e.to===to&&e.animate_allowed);
function currentForecast(h:number):Prediction|undefined{
 if(!current||!['tracking','degraded'].includes(current.model.phase)||lineValue(metric('temperature.tj'))===null)return undefined;
 const origin=metric('temperature.tj')?.as_of_elapsed_ms;
 return current.predictions.filter(p=>p.horizon_s===h&&p.status==='pending'&&p.origin_elapsed_ms===origin).at(-1);
}
function renderModel(){
 if(!current)return;
 const inNode=(id:string,top:number,color:string,label:string,u:string,d:number)=>{const m=metric(nodeMetric[id]),v=lineValue(m);return `<button type="button" class="node in${v===null?' inactive':''}${selectedNode===id?' sel':''}" data-node="${id}" style="left:0;top:${top}px" aria-label="${label}"><span class="t-caption"><i class="key" style="background:${color}"></i>${label}</span><span class="v">${v===null?'—':fmt(v,d)+' <span class="t-unit">'+u+'</span>'}</span></button>`;};
 const Tf=tfNow(),Ts=modelLive()?current.model.Ts_C:null,E=modelLive()?current.model.E_C:null,estOn=Tf!=null;
 const f=(h:number)=>currentForecast(h)?.value_C;
 /* 圆点沿整条连线（含拐角）运动：CSS offset-path，各线速度一致（70px/s），按路径长度定时长；phase 错开起点。 */
 const flow=(d:string,len:number,on:boolean,phase=0)=>on?`<i class="pulse" style="offset-path:path('${d}');animation-duration:${Math.max(1.4,len/70).toFixed(2)}s;animation-delay:${(-phase*Math.max(1.4,len/70)).toFixed(2)}s"></i>`:'';
 const wires=`<svg class="wires" viewBox="0 0 780 340" aria-hidden="true"><path d="M176 58H208M176 134H208M176 210H208M208 58V210"/><path d="M208 134H245" /><path d="M245 134l-6-4M245 134l-6 4"/><path d="M520 134H575"/><path d="M575 134l-6-4M575 134l-6 4"/><path d="M176 298H385V245" stroke-dasharray="6 5"/><path d="M385 245l-4 6M385 245l4 6"/></svg>`;
 const pg=edgeOn('pg','tf'),pc=edgeOn('pc','tf'),u=edgeOn('u','ts'),tj=edgeOn('tj','tf'),fc=edgeOn('tf','forecast');
 /* 流动的小圆点是 CSS 动画：只有“哪些线在流动”变了才重建这一层，否则每秒重绘会把动画打断在半路。 */
 const flowSig=[pg,pc,u,fc,tj].join();
 if(flowSig!==lastFlowSig){lastFlowSig=flowSig;html('topoFlow',`${wires}${flow('M176 58H208V134H245',145,pg)}${flow('M176 134H245',69,pc,.35)}${flow('M176 210H208V134H245',145,u,.7)}${flow('M520 134H575',55,fc,.5)}${flow('M176 298H385V247',260,tj,.2)}`);}
 const focused=(document.activeElement as HTMLElement|null)?.dataset?.node;
 html('topoNodes',`<span class="t-caption col" style="left:0">${t('测量输入')}</span><span class="t-caption col" style="left:250px">${t('热状态估计')}</span><span class="t-caption col" style="left:580px">${t('预测')}</span>
 <span class="t-caption col" style="left:200px;top:304px">${t('实测结温用于校正（不是功耗）')}</span>${inNode('pg',28,C.gpu,nodeTitle.pg,'W',2)}${inNode('pc',104,C.cpu,nodeTitle.pc,'W',2)}${inNode('u',180,C.pwm,nodeTitle.u,'%',0)}${inNode('tj',268,C.tj,nodeTitle.tj,'°C',1)}
 <button type="button" class="node est${estOn?'':' inactive'}${selectedNode==='est'?' sel':''}" data-node="est" aria-label="${nodeTitle.est}"><div><span class="t-caption">${t('快热状态 Tf · 估计')}</span><div class="t-metric">${estOn?fmt(Tf):'—'} ${unit('°C')}</div></div><div class="sep"></div><div><span class="t-caption">${t('慢热状态 Ts · 模型内部 · 估计')}</span><div class="t-metric">${estOn?fmt(Ts):'—'} ${unit('°C')}</div></div><span class="t-caption">${t('等效边界 E {v} °C · 模型内部',{v:estOn?neg(E):'—'})}${estOn&&current.model.phase==='degraded'?t(' · 条件不完整'):''}</span></button>
 <button type="button" class="node fc${estOn?'':' inactive'}${selectedNode==='fc'?' sel':''}" data-node="fc" aria-label="${nodeTitle.fc}"><span class="t-caption">${t('结温预测 · 假设负载保持')}</span><div class="fr"><span class="t-label">${t('+{n} 秒',{n:15})}</span><span class="t-value">${fmt(f(15))} °C</span></div><div class="fr mid"><span class="t-label" style="color:var(--ink)">${t('+{n} 秒',{n:45})}</span><span class="t-metric">${fmt(f(45))} ${unit('°C')}</span></div><div class="fr"><span class="t-label">${t('+{n} 秒',{n:90})}</span><span class="t-value">${fmt(f(90))} °C</span></div></button>`);
 if(focused)document.querySelector<HTMLElement>(`#topoNodes [data-node="${focused}"]`)?.focus();
 text('protect',({unknown:t('保护上下文未知'),active:t('明确保护 / 失温'),no_reported_protection:t('未报告保护')} as Record<string,string>)[current.health.protection_status]||t('保护上下文未知'));
 text('advice',current.advisory.value_percent==null?t('暂无可用的建议依据'):t('{v}% · 观察参考',{v:fmt(current.advisory.value_percent)}));
 text('adviceReason',current.health.protection_status==='active'&&connected?t('风扇观察建议已暂停（主板保护中）；天山OS继续负责保护。'):be(current.advisory.reason)+t('；天山OS继续负责保护。'));
 renderAside();
}
const K_STATE=t('模型状态');
function renderAside(){
 if(!current)return;
 const id=selectedNode,phase=current.model.phase;
 let rows='';
 if(id==='est'){
  const r=resNow();
  rows=rowsHtml([[K_STATE,!connected&&!waiting()?t('未知'):({tracking:t('跟踪中'),degraded:t('降级 · 条件不完整'),unavailable:t('暂不可用'),provisional:t('初始化中')} as Record<string,string>)[phase]||t('未开始')],[t('数据更新到'),connected&&current.run_elapsed_ms!=null?timeLabel(current.run_elapsed_ms):t('未知')],[t('估计与实测的差距'),r===null?'—':sgn(r,2)+' °C'],[t('模型版本'),current.model.model_id?current.model.model_id.slice(0,12):t('尚未加载')]],true);
 }else if(id==='fc'){
  rows=rowsHtml([[t('+{n} 秒',{n:15}),fmt(currentForecast(15)?.value_C)+' °C'],[t('+{n} 秒',{n:45}),fmt(currentForecast(45)?.value_C)+' °C'],[t('+{n} 秒',{n:90}),fmt(currentForecast(90)?.value_C)+' °C'],[t('场景'),t('假设负载保持')]],true);
 }else{
  const m=metric(nodeMetric[id]),v=lineValue(m);
  rows=rowsHtml([[t('当前读数'),v===null?t('暂无有效读数'):fmt(v,id==='u'?0:id==='tj'?1:2)+' '+(m?.unit||'')],[t('状态'),m?statusLabels[m.status]||m.status:t('未提供')],[t('来源'),m?.source_ref||'—'],[t('接收时刻'),m?dateLabel(m.received_at_utc):t('未知')]],true);
 }
 html('nodeAside',`<div class="ah">${icon('info')}<div><span class="t-caption">${t('节点详情')}</span><h3 class="t-section">${nodeTitle[id]}</h3></div></div><p class="t-body" style="color:var(--ink2)">${nodeText[id]}</p><div>${rows}</div><p class="t-caption">${t('点击左侧任一节点，这里显示它的数据来源、更新时间和含义。')}</p>`);
}
function rowsHtml(r:[string,string][],mono:boolean){return r.map(([k,v])=>rowHtml(k,esc(v),mono&&/\d/.test(v)&&k!==K_STATE?'t-body mono':'t-body')).join('');}
$('topology').addEventListener('click',e=>{const t=(e.target as HTMLElement).closest<HTMLElement>('[data-node]');if(t){selectedNode=t.dataset.node!;renderModel();}});

/* ---------- 预测对照 ---------- */
function comparisonKey(){return current?[current.service_epoch,current.run_id,current.source_epoch,current.model.model_id,current.model.spec_id,horizon,range].join(':'):'';}
function invalidateComparison(){
 comparisonGeneration++;predictionRequest++;predictionGroup=comparisonKey();
 predictionCache.clear();predictionLabels={};lastPredictionFetch=null;
 clearChart('comparison');clean($('score'));html('latestMatch',sepHtml(t('等待当前过程的成熟预测配对')));
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
 const s=data.summary;
 html('score',`<div class="stat-block" style="padding-bottom:6px"><span class="t-label">${t('平均绝对误差')}</span><span class="big"><b class="t-metric">${fmt(s.MAE_C,2)}</b>${unit('°C')}</span></div>`+rowHtml(t('误差 95 分位（绝对值）'),`${fmt(s.P95_absolute_C,2)} °C`,'t-body num')+rowHtml(t('最大低估'),`${fmt(s.max_underprediction_C,2)} °C`,'t-body num')+rowHtml(t('已匹配 / 应到期'),`${s.matched_count} / ${s.due_count}`,'t-body num'));
 text('scoreCaption',t('近 {n} 分钟 · 同一次观察、同一模型',{n:range})+(matched.length<30?t(' · 样本较少'):''));
 text('compareCaption',t('过去发出的 {h} 秒预测，到了目标时刻，实际结温是多少？',{h:horizon}));text('predName',t('当时发出的 +{h} 秒预测',{h:horizon}));
 const last=matched.at(-1);html('latestMatch',sepHtml(last?t('最近一条 · 目标时刻 {time} · 预测 {p} °C / 实测 {o} °C · 误差 {e} °C（预测{w}）',{time:timeLabel(last.target_elapsed_ms),p:fmt(last.value_C),o:fmt(last.observed_C),e:sgn(last.error_C,2),w:t(last.error_C!>=0?'偏高':'偏低')}):t('等待这条预测对应的实测温度 · 缺标签 {a} · 未到期 {b}',{a:s.missing_label_count,b:s.unmatched_future_count})));
 const done=records.filter(p=>['matched','missing_label'].includes(p.status));
 const [lo,hi]=span();
 const obsRows=done.map(p=>[p.target_elapsed_ms,p.observed_C,data.labels?.[p.prediction_id]?.received_at_utc||null,p.status]);
 put('comparison',{animation:false,grid:{left:50,right:28,top:10,bottom:26},xAxis:xAxis(lo,hi,true),yAxis:yAxis({scale:true,splitNumber:4,axisLabel:{color:C.ink3,fontSize:11,fontFamily:MONO,formatter:(v:number)=>String(Math.round(v))}}),dataZoom:zoom,
  tooltip:tooltip(ps=>ps.map(p=>tipRow(C.tj,p.seriesName,`${fmt(p.data[1],1)} °C`,p.seriesName!==t('目标时刻之后的首个有效实测'))).join('')),
  series:[line(t('目标时刻之后的首个有效实测'),obsRows,C.tj,2.2,{z:3,...endDot(obsRows,C.tj)}),line(t('当时发出的 +{h} 秒预测',{h:horizon}),done.map(p=>[p.target_elapsed_ms,p.value_C,null,p.status]),C.tj,1.8,{z:2,lineStyle:{width:1.8,color:C.tj,type:'dashed'}})]} as any);
 applyTicks();
}
function renderFuture(){
 if(!current)return;
 clean($('futureValues'));
 for(const h of [15,45,90]){const p=currentForecast(h),v=document.createElement('div');v.className='row';const label=document.createElement('span'),b=document.createElement('span');label.className='t-label';b.className='t-body num';if(h===45)b.style.fontWeight='600';label.textContent=t('+{n} 秒',{n:h});b.textContent=p?fmt(p.value_C)+' °C':'—';v.title=p?`origin ${timeLabel(p.origin_elapsed_ms)}\nissued ${timeLabel(p.issued_elapsed_ms)}\ntarget ${timeLabel(p.target_elapsed_ms)}\ncutoff ${timeLabel(p.input_cutoff_elapsed_ms)}\n${p.prediction_id}`:t('没有当前已发布预测');v.append(label,b);$('futureValues').append(v);}
 const ph=current.model.phase;
 text('futureNote',ph==='unavailable'&&deviceOk()?t('模型暂不可用，未来参考已撤回。'):ph==='degraded'?t('估计可用，条件不完整。')+t('假设负载保持不变，三个时点分别计算，不是连续轨迹，也不是控制指令。'):t('假设负载保持不变，三个时点分别计算，不是连续轨迹，也不是控制指令。'));
}

/* ---------- 运行信息 ---------- */
async function renderContext(){
 if(!current)return;const group=runKey();const ctx=await api('context');if(paused||group!==runKey())return;lastContext=ctx;renderContextRows();
}
const duration=(ms:number)=>{const m=Math.floor(ms/60000);return m>=60?t('{h} 小时 {m} 分',{h:Math.floor(m/60),m:m%60}):m>=1?t('{m} 分钟',{m}):t('{n} 秒',{n:Math.floor(ms/1000)});};
function renderContextRows(){
 if(!current)return;const ctx=lastContext;
 const ram=metric('memory.ram'),dash=(v:unknown,u:string)=>v==null||v==='—'?'—':`${v} ${u}`;
 const run=current.run_id?`${current.run_id.slice(0,8)} · ${t('源 #{n}',{n:current.source_epoch??'—'})}`:'—';
 html('ctxObs',rowHtml(t('观察对象 / 平台'),esc(`${ctx?.observed_device||current.context.observed_device||t('未知')} / ${ctx?.platform?.soc||t('未知')}`))+rowHtml(t('观察主机'),esc(ctx?.tto_host||current.context.tto_host))+rowHtml(t('观察状态'),esc(!connected?t('Web数据断开，来源状态未知'):current.health.measurement_status==='valid'?be(ctx?.observation_status||'正在观察'):t('设备数据资格已到期或不可用')))+rowHtml(t('本次观察'),esc(run),'t-body mono')+rowHtml(t('已观察时长'),esc(duration(current.run_elapsed_ms||0))));
 const active=ctx?.task_metadata_available&&connected;
 html('ctxCtl',rowHtml(t('风扇控制'),esc(t('天山OS：{v}',{v:be(String(lineValue(metric('fan.mode'))??t('未知')))})))+rowHtml(t('本系统角色'),t('只读，给出参考'))+rowHtml(t('热模型'),current.model.model_id?`G2 · <span class="mono">${esc(current.model.model_id.slice(0,12))}</span>`:t('尚未加载'))+rowHtml(t('当前负载'),active?esc(t('进行中 {a} / 并发上限 {b}',{a:ctx.active_requests??t('未知'),b:ctx.client_slots??t('未知')})):t('未接入任务记录'))+rowHtml(t('风扇观察建议'),current.health.protection_status==='active'&&connected?t('已暂停（主板保护中）'):t('暂未接入')));
 html('ctxRun',rowHtml(t('GPU 利用率'),dash(fmt(lineValue(metric('usage.gpu')),0),'%'),'t-body num')+rowHtml(t('CPU 平均利用率'),dash(fmt(lineValue(metric('usage.cpu.mean'))),'%'),'t-body num')+rowHtml(t('设备内存'),`${fmt(lineValue(ram),0)} / ${fmt(lineValue(metric('memory.ram.total')),0)} ${esc(ram?.unit||'MB')}`,'t-body num')+rowHtml(t('网页服务开销'),t('{c} % 单核 · {r} MiB',{c:fmt(lineValue(metric('host.cpu'))),r:fmt(lineValue(metric('host.rss')),0)}),'t-body num'));
 if(ctx){
  text('sourceDiagnostics',t('显示链重新同步 {n} 次',{n:ctx.display_resync_count||0})+' | '+Object.values(ctx.source_health||{}).map((s:any)=>`${s.source}: ${s.quality_reason||s.error_class||t('已接收')} ${s.timeout_phase||''} · RTT ${fmt(s.round_trip_ms)}ms · ${dateLabel(s.last_received_at_utc)}`).join(' | '));
  text('contextNote',(ctx.task_metadata_available?t('任务信息来自runner登记'):t('未接入任务记录'))+t('；客户端完成不代表GPU停止。RAM用量不用于推断模型驻留。'));
 }
}
function renderFields(){
 if(!current)return;const query=$<HTMLInputElement>('search').value.toLowerCase(),group=$<HTMLSelectElement>('group').value;
 const tbody=$<HTMLTableSectionElement>('fieldRows');clean(tbody);
 current.metrics.filter(m=>(m.id+' '+m.label).toLowerCase().includes(query)&&m.id.startsWith(group)).forEach(m=>{const tr=document.createElement('tr');cell(tr,be(m.label)+' / '+m.id);{const lv=lineValue(m);cell(tr,typeof lv==='string'?be(lv):lv??(m.last_observation?t('上次 {v}',{v:String(m.last_observation.value)}):'—'));}cell(tr,m.unit);cell(tr,m.kind+' / '+statusLabels[m.status]);cell(tr,m.source_ref);tr.title=`${m.reason_code||''}; ${m.sample_id}; ${dateLabel(m.received_at_utc)}`;tbody.append(tr);});text('fieldCount',t('{n}项',{n:current.metrics.length}));
 const health=$<HTMLTableSectionElement>('healthRows');clean(health);current.metrics.forEach(m=>{const tr=document.createElement('tr');cell(tr,m.source_id);cell(tr,be(m.label));cell(tr,statusLabels[m.status]);cell(tr,`${fmt((m.age_lower_bound_ms||0)/1000)}s / ${fmt(Math.max(0,(m.remaining_valid_ms||0)-(performance.now()-received))/1000)}s`);cell(tr,dateLabel(m.received_at_utc));health.append(tr);});
 text('healthSummary',t('{a}项有效 / {b}项待确认',{a:current.metrics.filter(m=>m.status==='valid').length,b:current.metrics.filter(m=>m.status==='unverified').length}));
 text('sourceStatus',t('网页：{x}；设备数据：{y}；模型：{z}。三者分别判定，网页连通不代表设备读数有效。',{x:t(connected?'已连接':'断开'),y:t(current.health.measurement_status==='valid'?'有效':'不可用或已过期'),z:phaseLabels[current.model.phase]}));
}
function renderEvents(){
 const source=$<HTMLSelectElement>('eventSource').value,level=$<HTMLSelectElement>('eventLevel').value;clean($('eventList'));
 events.filter(e=>(!source||source===e.source)&&(!level||level===e.severity)).slice().reverse().forEach(e=>{const div=document.createElement('div');div.className='event-row';div.textContent=`${dateLabel(e.first_at_utc)} — ${dateLabel(e.last_at_utc)}  ${evSrc(e.source)} · ${evReason(e.reason)} ×${e.count}`;$('eventList').append(div);});text('eventCount',t('{n}条',{n:events.length}));
}
charts.eventTimeline.on('click',(params:any)=>{const e=events.find(e=>e.id===params.data.eventId);if(!e)return;text('eventSelection',`${evSrc(e.source)} · ${evReason(e.reason)} | ${t('发生 {time}',{time:timeLabel(e.elapsed_ms)})} | ${t('Web首次到达/记录 {time}',{time:dateLabel(e.first_at_utc)})} | ${t('最近 {time}',{time:dateLabel(e.last_at_utc)})} | ${t('重复 {n}次',{n:e.count})}`);$('eventSelection').hidden=false;});
let ticking=false;
charts.axisA.on('datazoom',()=>{if(ticking)return;ticking=true;setTimeout(()=>{applyTicks();ticking=false;},0);});

/* ---------- 数据刷新 ---------- */
const seriesIds=()=>current?WANT.filter(id=>current!.metrics.some(m=>m.id===id)):[];
async function refreshData(){
 if(!current||paused)return;
 const end=current.run_elapsed_ms||0,from=Math.max(0,end-range*60000),sid=seriesIds(),source=runKey();
 const group=[source,range,sid.join(',')].join(':');
 if(group!==seriesGroup){seriesCache.clear();lastSeriesFetch=null;seriesGroup=group;seriesGen++;}
 if(busyGroup===group)return;
 busyGroup=group;const gen=seriesGen;
 try{const deltaFrom=Math.max(from,lastSeriesFetch??from);
  const [s,e]=await Promise.all([sid.length?api(`series?ids=${encodeURIComponent(sid.join(','))}&from=${deltaFrom}&to=${end}&max_points=2000`):Promise.resolve({series:[],service_epoch:'',run_id:'',source_epoch:''}),api('events?limit=1000')]);
  if(gen!==seriesGen||paused||source!==runKey()||(sid.length&&[s.service_epoch,s.run_id,s.source_epoch].join(':')!==source))return;
  for(const incoming of s.series as Series[]){const prior=seriesCache.get(incoming.id);const points=new Map<string,any>();for(const p of [...(prior?.points||[]),...incoming.points])if(p.t>=from)points.set([p.t,p.sample_id,p.status].join(':'),p);seriesCache.set(incoming.id,{...incoming,sampling:prior?.sampling==='bucket_first_last_min_max_and_gaps'?prior.sampling:incoming.sampling,points:[...points.values()].sort((a,b)=>a.t-b.t).slice(-18002)});}
  lastSeriesFetch=end;seriesData=[...seriesCache.values()];events=e.events.filter((v:any)=>v.service_epoch===current?.service_epoch&&(v.run_id===null||v.run_id===current?.run_id&&v.source_epoch===current?.source_epoch));
  renderLeft();renderCharts();renderEvents();await Promise.all([renderComparison(),renderContext()]);
 }catch{/* HTTP/API failure never creates measurements. SSE owns connection state. */}finally{if(busyGroup===group)busyGroup='';}
}
/* 模型组：整窗替换，不做增量合并；组或窗口变化立即清空并递增代次，≥5 秒才再请求。 */
function syncModelGroup(){
 const group=[modelKey(),range].join('|');
 if(group!==modelGroup){modelGroup=group;modelGen++;modelReq++;modelData=null;modelFetchedAt=-Infinity;modelInflight='';}
}
async function refreshModel(){
 if(!current||paused||current.run_id===null||!hasModelHistory())return;
 syncModelGroup();
 const group=modelGroup,now=performance.now();
 if(modelInflight===group||now-modelFetchedAt<MODEL_REFRESH_MS)return;
 modelInflight=group;modelFetchedAt=now;
 const gen=modelGen,req=++modelReq,expected=modelKey(),want=range,end=current.run_elapsed_ms||0,from=Math.max(0,end-range*60000);
 const fresh=(r:SeriesResponse)=>!paused&&gen===modelGen&&req===modelReq&&want===range&&respKey(r)===expected&&expected===modelKey()&&r.series.length===MODEL_IDS.length&&MODEL_IDS.every(id=>r.series.some(s=>s.id===id));
 const get=(n:number)=>api(`series?ids=${MODEL_IDS.join(',')}&from=${from}&to=${end}&max_points=${n}`) as Promise<SeriesResponse>;
 try{
  let r=await get(2000);if(!fresh(r))return;
  if(r.series.some(s=>s.sampling!=='actual_samples'&&(s.original_points??0)<=5000)){const r2=await get(5000);if(!fresh(r2))return;r=r2;}
  const d=derive(r);if(!d)return;
  modelData=d;renderGapSummary();renderLeft();renderCharts();renderHeader();
 }catch{/* 失败不造数据；保留上一份合格历史。 */}finally{if(modelInflight===group)modelInflight='';}
}
function expireCurrent(disconnected=false){
 if(!current)return false;
 const elapsed=performance.now()-received;let changed=false;
 for(const m of current.metrics){
  if(m.status==='valid'&&(disconnected||m.remaining_valid_ms===null||m.remaining_valid_ms<=elapsed)){
   if(m.id==='temperature.tj'&&typeof m.value==='number')lastTJ={value:m.value,at:m.received_at_utc};
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
  if(current.advisory.status==='available'){current.advisory.status='withheld';current.advisory.reason=t('当前数据资格已撤销');}
 }
 for(const n of current.model.nodes){
  const status=n.metric_id?metric(n.metric_id)?.status||'unknown':n.role==='estimate'||n.id==='forecast'?current.model.phase==='unavailable'?'unknown':n.status:n.id==='risk'?current.health.protection_status==='unknown'?'unknown':n.status:n.status;
  if(n.status!==status){n.status=status;changed=true;}
 }
 const valid=new Set(current.model.nodes.filter(n=>n.status==='valid').map(n=>n.id));
 for(const e of current.model.edges)if(e.animate_allowed&&(current.model.phase==='unavailable'||!valid.has(e.from)||!valid.has(e.to))){e.animate_allowed=false;changed=true;}
 return changed;
}
function renderCurrent(){renderHeader();renderLeft();renderGapSummary();renderModel();renderFuture();renderFields();renderContextRows();}
function accept(s:Snapshot,at=performance.now()){
 latest=s;latestReceived=at;if(paused)return;received=at;current=structuredClone(s);
 const run=runKey();if(lastRun!==run){if(live.has('axisA'))charts.axisA.dispatchAction({type:'dataZoom',start:0,end:100});seriesData=[];events=[];lastContext=null;lastTJ=null;modelData=null;['ctxObs','ctxCtl','ctxRun'].forEach(i=>clean($(i)));$('eventSelection').hidden=true;if(lastRun!=='')switchedAt=Date.now();lastRun=run;originUtc=Date.parse(s.server_time_utc)-(s.run_elapsed_ms||0);renderCharts();renderEvents();}
 if(s.health.measurement_status==='valid')lastTJ=null;
 syncModelGroup();
 const comparisonChanged=predictionGroup!==comparisonKey();if(comparisonChanged)invalidateComparison();
 expireCurrent(!connected);renderCurrent();if(comparisonChanged)void renderComparison().catch(()=>{});void refreshData();void refreshModel();
}
let stream:EventSource|null=null,reconnect=0;
function connect(){stream?.close();reconnect=0;const es=stream=new EventSource('/api/v1/stream');['snapshot','quality','resync','run_changed'].forEach(name=>es.addEventListener(name,e=>{connected=true;retries=0;accept(JSON.parse((e as MessageEvent).data));}));es.addEventListener('heartbeat',()=>{connected=true;retries=0;renderHeader();});
 es.onerror=()=>{connected=false;retries++;if(!paused){expireCurrent(true);renderCurrent();renderCharts();}else renderHeader();
  /* 连接被浏览器放弃（服务重启、网络中断）时 EventSource 不再自动重连，这里补一次延迟重连。 */
  if(es.readyState===EventSource.CLOSED&&!reconnect)reconnect=window.setTimeout(()=>{if(stream===es)connect();},3000);};}

/* ---------- 控件 ---------- */
const closeMenu=()=>{$('moreMenu').hidden=true;$('moreBtn').setAttribute('aria-expanded','false');$('langMenu').hidden=true;$('langBtn').setAttribute('aria-expanded','false');};
$('moreBtn').onclick=e=>{e.stopPropagation();const open=$('moreMenu').hidden;$('moreMenu').hidden=!open;$('moreBtn').setAttribute('aria-expanded',String(open));};
$('langBtn').onclick=e=>{e.stopPropagation();const open=$('langMenu').hidden;closeMenu();$('langMenu').hidden=!open;$('langBtn').setAttribute('aria-expanded',String(open));};
$('langMenu').addEventListener('click',e=>{const b=(e.target as HTMLElement).closest<HTMLButtonElement>('[data-lang]');if(b&&b.dataset.lang!==lang)setLang(b.dataset.lang as 'zh'|'en');else closeMenu();});
document.addEventListener('click',e=>{if(!(e.target as HTMLElement).closest('.head-tools,.lang-wrap'))closeMenu();if(!(e.target as HTMLElement).closest('#bar'))$('bar').classList.remove('nav-open');});
document.addEventListener('keydown',e=>{if(e.key==='Escape'){closeMenu();$('bar').classList.remove('nav-open');}});
$('menuBtn').onclick=e=>{e.stopPropagation();const open=$('bar').classList.toggle('nav-open');$('menuBtn').setAttribute('aria-expanded',String(open));};
$('nav').addEventListener('click',()=>$('bar').classList.remove('nav-open'));
$('pause').onclick=()=>{
 paused=!paused;closeMenu();
 if(paused){pausedAt=current?timeLabel(current.run_elapsed_ms||0):'';}
 else if(latest){modelFetchedAt=-Infinity;accept(latest,latestReceived);}
 renderHeader();renderLeft();renderModel();
};
$('fullscreen').onclick=()=>{closeMenu();if(document.fullscreenElement)void document.exitFullscreen();else void document.documentElement.requestFullscreen();};
$('resetZoom').onclick=()=>{closeMenu();if(live.has('axisA'))charts.axisA.dispatchAction({type:'dataZoom',start:0,end:100});};
$('range').onclick=e=>{const b=(e.target as HTMLElement).closest<HTMLButtonElement>('button');if(!b)return;range=Number(b.dataset.v);localStorage.setItem('tto-range',String(range));renderHeader();syncModelGroup();void refreshData();void refreshModel();};
$('horizon').onclick=e=>{const b=(e.target as HTMLElement).closest<HTMLButtonElement>('button');if(!b)return;horizon=Number(b.dataset.v);renderHeader();void renderComparison();};
$('motion').onchange=()=>{const checked=$<HTMLInputElement>('motion').checked;document.body.classList.toggle('reduced-motion',checked);localStorage.setItem('tto-motion',String(checked));};
['search','group'].forEach(id=>$(id).addEventListener('input',renderFields));['eventSource','eventLevel'].forEach(id=>$(id).addEventListener('change',renderEvents));
const navLinks=Array.from(document.querySelectorAll<HTMLAnchorElement>('#nav a'));
new IntersectionObserver(es=>{for(const e of es)if(e.isIntersecting)navLinks.forEach(a=>a.classList.toggle('on',a.getAttribute('href')==='#'+e.target.id));},{rootMargin:'-30% 0px -60% 0px'}).observe($('trends'));
['model','compare','context'].forEach(id=>new IntersectionObserver(es=>{for(const e of es)if(e.isIntersecting)navLinks.forEach(a=>a.classList.toggle('on',a.getAttribute('href')==='#'+id));},{rootMargin:'-30% 0px -60% 0px'}).observe($(id)));
document.addEventListener('visibilitychange',()=>document.body.classList.toggle('background',document.hidden));
$('loginForm').onsubmit=async e=>{e.preventDefault();const r=await fetch('/api/v1/session',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:$<HTMLInputElement>('password').value}),credentials:'same-origin'});if(r.ok){$<HTMLInputElement>('password').value='';$<HTMLDialogElement>('login').close();location.reload();}else text('loginMessage',t('口令不匹配或请求过于频繁。'));};
setInterval(()=>{if(!current)return;if(paused){renderHeader();return;}if(expireCurrent(!connected)){renderCurrent();renderCharts();}},200);
setInterval(()=>{if(current&&!paused&&(!connected||current.health.measurement_status!=='valid')){renderHeader();renderCharts();}},1000);
renderHeader();renderLeft();renderGapSummary();renderCharts();
(async()=>{try{boot=await api('bootstrap');tz=boot!.timezone;connected=true;accept(await api('snapshot'));connect();}catch(e){console.error(e);renderHeader();}})();
