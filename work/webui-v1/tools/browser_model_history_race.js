async (page) => {
 // 首页“估计与实测的差距 / 热状态构成”依赖的模型历史（联合 /series）：同 run 切 epoch 时，在途旧响应不得写回，新数据组不被在途请求阻塞。
 const control=await page.evaluate(()=>sessionStorage.getItem('tto-test-control'));if(!control)throw Error('register local harness control URL');
 const command=async name=>(await page.request.post(control+'/'+name)).json();
 const isModel=url=>url.pathname==='/api/v1/series'&&url.search.includes('model.Tf_C');
 await page.setViewportSize({width:1440,height:1100});
 const boot=await (await page.request.get('http://127.0.0.1:59009/api/v1/bootstrap')).json();
 const result={version:boot.version,capability:!!boot.series_capabilities?.model_state_history,sentinelShift:15};
 if(!result.capability){result.skipped='service has no model state history';return result;}
 await page.waitForFunction(()=>/全部 \d+ 个样本|抽样/.test(document.querySelector('#gapSummary')?.innerText||''),null,{timeout:30000});
 const meanOf=text=>{const m=/平均偏差（绝对值）(?: · 近似)?\s*([\d.]+)/.exec(text);return m?Number(m[1]):null;};
 result.meanBefore=meanOf(await page.locator('#gapSummary').innerText());
 const old=await (await page.request.get('http://127.0.0.1:59009/api/v1/snapshot')).json();
 let release,notifyHeld,notifyReturned,holding=false,startedWhileHeld=0;
 const gate=new Promise(r=>release=r),held=new Promise(r=>notifyHeld=r),returned=new Promise(r=>notifyReturned=r);
 await page.route(isModel,async route=>{
  if(!holding){
   holding=true;const response=await route.fetch();const data=await response.json();
   // 旧组响应里把 Tf 整体抬高：如果被误写回，差距统计会明显变大。
   data.series.find(s=>s.id==='model.Tf_C').points.forEach(p=>{if(p.value!==null)p.value+=result.sentinelShift;});
   notifyHeld();await gate;await route.fulfill({response,json:data});notifyReturned();
  }else{startedWhileHeld++;await route.continue();}
 });
 // 模型组至少每 5 秒刷新一次，等它被扣住。
 await Promise.race([held,new Promise((_,reject)=>setTimeout(()=>reject(Error('old model request not held')),12000))]);
 const epoch=await command('new-epoch');result.oldEpoch=old.source_epoch;result.newEpoch=epoch.source_epoch;
 if(epoch.run_id!==old.run_id||epoch.source_epoch===old.source_epoch)throw Error('did not switch epoch in same run');
 await page.waitForFunction(()=>!/\d+\.\d\d/.test(document.querySelector('#gapSummary').innerText));
 result.clearedBeforeOldResponse=true;
 await page.waitForTimeout(2500);
 result.newGroupRequestsWhileHeld=startedWhileHeld;
 if(startedWhileHeld<1)throw Error('new data group was blocked by the in-flight request');
 await page.screenshot({path:'output/playwright/'+boot.version+'-model-history-before-late.png',fullPage:true});
 release();await returned;await page.waitForTimeout(600);
 const after=await page.locator('#gapSummary').innerText();result.meanAfterOldResponse=meanOf(after);
 result.lateResponseIgnored=result.meanAfterOldResponse===null||result.meanAfterOldResponse<result.sentinelShift/2;
 await page.unroute(isModel);
 result.fixed=result.clearedBeforeOldResponse&&result.lateResponseIgnored;
 await page.screenshot({path:'output/playwright/'+boot.version+'-model-history-after-late.png',fullPage:true});
 if(!result.fixed)throw Error('old model history crossed an epoch');
 return result;
}
