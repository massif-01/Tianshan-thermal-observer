async (page) => {
 const control=await page.evaluate(()=>sessionStorage.getItem('tto-test-control'));if(!control)throw Error('local control not registered');
 const command=async name=>(await page.request.post(control+'/'+name)).json();
 const refresh=()=>page.getByRole('button',{name:'刷新历史',exact:true}).click();
 const result={scope:'installed rc4 API; minimal synthetic verification page, not Sonnet homepage',health:await(await page.request.get('http://127.0.0.1:59009/healthz')).json()};
 await page.goto('http://127.0.0.1:59009/__history');
 await page.waitForFunction(()=>window.historyResult?.series[1].points.some(p=>p.value!==null));
 result.initial=await page.evaluate(()=>({identity:document.querySelector('#identity').textContent,rows:document.querySelector('#rows').textContent,lines:document.querySelector('#chart').children.length}));
 await command('gap');await page.waitForTimeout(2300);await refresh();
 await page.waitForFunction(()=>window.historyResult.series[1].points.some(p=>p.reason_code==='publication_gap'));
 result.gap=await page.evaluate(()=>({nulls:window.historyResult.series[1].points.filter(p=>p.value===null).length,lines:document.querySelector('#chart').children.length}));
 if(result.gap.lines<8)throw Error('joint curves joined across publication gap');
 await page.screenshot({path:'output/playwright/rc4-history-gap.png',fullPage:true});
 await command('silent');await page.waitForTimeout(3200);await refresh();
 await page.waitForFunction(()=>window.historyResult.series[1].points.at(-1).value===null);
 result.silent=await page.evaluate(()=>({last:window.historyResult.series[1].points.at(-1),table:document.querySelector('#rows').textContent}));
 await command('live');await page.waitForTimeout(2300);await refresh();
 await page.waitForFunction(()=>window.historyResult.series[1].points.at(-1).value!==null);
 result.recovered=await page.evaluate(()=>window.historyResult.series[1].points.at(-1));
 const old=await page.evaluate(()=>window.historyResult);let release,heldResolve,returnedResolve;
 const gate=new Promise(r=>release=r),held=new Promise(r=>heldResolve=r),returned=new Promise(r=>returnedResolve=r);let holding=false;
 await page.route('**/api/v1/series?ids=**',async route=>{
  if(!holding){holding=true;const response=await route.fetch();const data=await response.json();data.series[1].points.forEach(p=>{if(p.value!==null)p.value=777.123;});heldResolve();await gate;await route.fulfill({response,json:data});returnedResolve();}
  else await route.continue();
 });
 await refresh();await held;await command('epoch');
 await page.waitForFunction(epoch=>window.historyResult&&window.historyResult.source_epoch!==epoch&&document.querySelector('#chart').children.length===0,old.source_epoch);
 result.switched=await page.evaluate(()=>({source_epoch:window.historyResult?.source_epoch,run_id:window.historyResult?.run_id,lines:document.querySelector('#chart').children.length,status:document.querySelector('#status').textContent}));
 await page.screenshot({path:'output/playwright/rc4-history-epoch-before-late.png',fullPage:true});
 release();await returned;await page.waitForTimeout(400);
 result.lateIgnored=await page.evaluate(epoch=>window.historyResult&&window.historyResult.source_epoch!==epoch&&!document.querySelector('#rows').textContent.includes('777.123'),old.source_epoch);
 if(!result.lateIgnored||result.switched.run_id!==old.run_id)throw Error('history crossed same-run epoch');
 await page.unroute('**/api/v1/series?ids=**');
 result.accessibilityTable=await page.getByRole('table',{name:'历史序列检查'}).isVisible();
 result.jsHeapBytes=await page.evaluate(()=>performance.memory?.usedJSHeapSize??null);
 result.pass=true;
 await page.screenshot({path:'output/playwright/rc4-history-epoch-after-late.png',fullPage:true});
 return result;
}
