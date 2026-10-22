const ids=['temperature.tj','model.Tf_C','model.Ts_C','model.E_C'];
const key=x=>[x.service_epoch,x.run_id,x.source_epoch,x.model_id??x.model?.model_id,x.spec_id??x.model?.spec_id].join('|');
let cohort='',generation=0,request=0;
const status=document.querySelector('#status');
const clear=()=>{document.querySelector('#rows').replaceChildren();document.querySelector('#chart').replaceChildren();document.querySelector('#residual').replaceChildren();};
function segments(points){const parts=[];let current=[];for(const p of points){if(p.value===null){if(current.length)parts.push(current);current=[];}else current.push(p);}if(current.length)parts.push(current);return parts;}
function draw(target,points,color,lo,hi){for(const part of segments(points)){const line=document.createElementNS('http://www.w3.org/2000/svg','polyline');line.setAttribute('points',part.map(p=>`${(p.t-lo)/Math.max(1,hi-lo)*1100},${150-p.value*2}`).join(' '));line.setAttribute('stroke',color);target.append(line);}}
async function refresh(){const expected=cohort,g=generation,r=++request;const response=await fetch('/api/v1/series?ids='+ids.join(',')+'&max_points=2000');const data=await response.json();
 if(g!==generation||r!==request||expected!==cohort||key(data)!==cohort)return;
 clear();const all=data.series;const lo=all[0].points[0]?.t??0,hi=all[0].points.at(-1)?.t??1;
 all.forEach((s,i)=>{const tr=document.createElement('tr');[s.id,s.points.length,s.points.filter(p=>p.value===null).length,segments(s.points).length,s.points.at(-1)?.value??'—'].forEach(value=>{const td=document.createElement('td');td.textContent=String(value);tr.append(td);});document.querySelector('#rows').append(tr);draw(document.querySelector('#chart'),s.points,['#fff','#fa8','#7cf','#9d8'][i],lo,hi);});
 const residual=all[0].points.map((p,i)=>({...p,value:p.value===null||all[1].points[i].value===null?null:p.value-all[1].points[i].value}));draw(document.querySelector('#residual'),residual,'#fc7',lo,hi);
 status.textContent='已加载，同采样对齐；缺口不连线';window.historyResult=data;
}
const events=new EventSource('/api/v1/stream');
for(const name of ['snapshot','quality','run_changed','resync'])events.addEventListener(name,event=>{const snapshot=JSON.parse(event.data);const next=key(snapshot);if(next!==cohort){cohort=next;generation++;request++;clear();window.historyResult=null;status.textContent='数据组切换，旧历史已清除';document.querySelector('#identity').textContent=cohort;refresh();}});
document.querySelector('#refresh').onclick=refresh;
