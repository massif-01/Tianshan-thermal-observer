async page => {
 const errors=[];page.on('pageerror',e=>errors.push(String(e)));
 await page.waitForFunction(()=>[...document.querySelectorAll('#futureValues .row>span:last-child')].some(e=>e.textContent.includes('°C')),{timeout:45000});
 const shown=await page.locator('#futureValues .row').evaluateAll(rows=>rows.map(e=>({id:e.title.split('\n').at(-1),value:e.lastElementChild.textContent,target:e.querySelector('.t-caption')?.textContent})));
 const recordSets=await Promise.all([15,45,90].map(h=>page.request.get('http://127.0.0.1:59009/api/v1/predictions?horizon_s='+h).then(r=>r.json())));
 for(let n=0;n<3;n++){
  const p=recordSets[n].records.find(p=>p.prediction_id===shown[n].id);
  if(!p||shown[n].value!==p.value_C.toFixed(1)+' °C')throw Error('live displayed prediction differs from API '+JSON.stringify(shown[n]));
 }
 await page.screenshot({path:'output/playwright/n305-rc7-live.png',fullPage:true});
 const health=await (await page.request.get('http://127.0.0.1:59009/healthz')).json();
 return {scope:'real N305 Web over loopback SSH tunnel; real device read-only source; no injected DTO',health,shown,pageErrors:errors};
}
