/* Run against the installed static bundle. fixture comes from validate_publication_replay.py.
   Only the EventSource transport is controlled; no production JS hooks or second predictor. */
async (page, fixture) => {
 const errors=[];page.on('pageerror',e=>errors.push(String(e)));
 await page.addInitScript(()=>{
  window.EventSource=class extends EventTarget{
   static CLOSED=2;readyState=1;onerror=null;
   constructor(){super();window.testStream=this;}
   close(){this.readyState=2;}
  };
 });
 await page.goto('http://127.0.0.1:59009/');
 await page.waitForFunction(()=>window.testStream);
 const emit=async snapshot=>page.evaluate(s=>window.testStream.dispatchEvent(new MessageEvent('snapshot',{data:JSON.stringify(s)})),snapshot);
 const read=()=>page.evaluate(()=>({future:[...document.querySelectorAll('#futureValues .row>span:last-child')].map(e=>e.textContent),
  forecastInactive:document.querySelector('[data-node="fc"]').classList.contains('inactive'),
  estimateInactive:document.querySelector('[data-node="est"]').classList.contains('inactive'),
  forecastFlow:document.querySelectorAll('#topoFlow .pulse').length,
  note:document.querySelector('#futureNote').textContent}));
 const available=structuredClone(fixture);
 for(const m of available.metrics)if(m.status==='valid')m.remaining_valid_ms=10000;
 available.model.remaining_valid_ms=10000;available.forecast.remaining_valid_ms=10000;
 // A newer pending record is history until the backend selects its ID.
 const unselected={...available.predictions.find(p=>p.horizon_s===45),prediction_id:'UNSELECTED-BROWSER-FIXTURE',value_C:99};
 available.predictions.push(unselected);
 const expected=[15,45,90].map(h=>available.predictions.find(p=>p.horizon_s===h&&available.forecast.latest_prediction_ids.includes(p.prediction_id)));
 const expectAvailable=async()=>{
  const r=await read();
  if(r.future.some((v,i)=>!v.startsWith(expected[i].value_C.toFixed(1)))||r.forecastInactive)throw Error('wrong selected values '+JSON.stringify(r));
  return r;
 };
 const expectWithdrawn=async()=>{
  const r=await read();if(r.future.some(v=>v!=='—')||!r.forecastInactive)throw Error('forecast survived withdrawal '+JSON.stringify(r));return r;
 };
 await emit(available);
 const result={scope:'installed rc9 static; recorded backend DTO; controlled browser transport',available:await expectAvailable()};
 const titles=await page.locator('#futureValues .row').evaluateAll(rows=>rows.map(e=>e.title));
 if(expected.some((p,i)=>!titles[i].includes(p.prediction_id)))throw Error('displayed IDs differ from backend');
 const targets=await page.locator('#futureValues .t-caption').allTextContents();
 if(targets.length!==3||targets.some(v=>!v.includes('目标')))throw Error('fixed target times missing');
 const shifted=structuredClone(available);shifted.server_time_utc=new Date(Date.parse(shifted.server_time_utc)+3600000).toISOString();shifted.run_elapsed_ms+=1000;await emit(shifted);
 if(JSON.stringify(await page.locator('#futureValues .t-caption').allTextContents())!==JSON.stringify(targets))throw Error('target time changed with snapshot wall clock');
 result.fixedTargetTimes=true;
 for(const status of ['unavailable','syncing','disconnected','not_connected','initializing']){
  const s=structuredClone(available);s.forecast.status=status;await emit(s);await expectWithdrawn();
 }
 result.withdrawnStatuses=5;
 const ttl=structuredClone(available);ttl.forecast.remaining_valid_ms=600;await emit(ttl);await expectAvailable();
 await page.waitForTimeout(850);result.forecastExpired=await expectWithdrawn();
 if(result.forecastExpired.estimateInactive)throw Error('forecast expiry incorrectly withdrew valid model');
 const model=structuredClone(available);model.model.remaining_valid_ms=600;await emit(model);
 await page.waitForTimeout(850);result.modelExpired=await expectWithdrawn();
 if(!result.modelExpired.estimateInactive)throw Error('model did not expire');
 await emit(available);await expectAvailable();
 await page.evaluate(()=>window.testStream.onerror());result.disconnected=await expectWithdrawn();
 await emit(available);result.reconnected=await expectAvailable();
 await page.reload();await page.waitForFunction(()=>window.testStream);await emit(available);result.reloaded=await expectAvailable();
 const failed=structuredClone(available);failed.publication_status='failed';failed.forecast.status='unavailable';failed.forecast.latest_prediction_ids=[];
 await emit(failed);result.publicationFailed=await expectWithdrawn();
 if(!(await page.locator('#stripSt').textContent()).includes('发布失败 · 最终结果未确认'))throw Error('publication failure hidden');
 await emit(available);await expectAvailable();
 await page.screenshot({path:'output/playwright/forecast-qualified.png',fullPage:true});
 if(errors.length)throw Error(errors.join('\n'));result.pageErrors=errors;
 return result;
}
