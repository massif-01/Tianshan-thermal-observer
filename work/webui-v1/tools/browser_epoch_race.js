async (page) => {
 const control=await page.evaluate(()=>sessionStorage.getItem('tto-test-control'));if(!control)throw Error('register local harness control URL');
 const command=async name=>(await page.request.post(control+'/'+name)).json();
 await page.setViewportSize({width:1440,height:1100});
 await page.waitForFunction(()=>document.querySelectorAll('#score .t-metric').length===1&&document.querySelector('#ctxObs').children.length>0);
 const health=await (await page.request.get('http://127.0.0.1:59009/healthz')).json();
 const old=await (await page.request.get('http://127.0.0.1:59009/api/v1/snapshot')).json();
 let releaseOld,notifyHeld,notifyReturned,holding=false,blockNew=false;
 const gate=new Promise(resolve=>releaseOld=resolve),held=new Promise(resolve=>notifyHeld=resolve),returned=new Promise(resolve=>notifyReturned=resolve);
 // 页面平均绝对误差保留两位小数：777.123 显示为 777.12。
 const result={version:health.version,oldRun:old.run_id,oldEpoch:old.source_epoch,scoreBefore:await page.locator('#score').innerText(),sentinelMAE:777.123,sentinelShown:'777.12'};
 await page.route('**/api/v1/predictions?**',async route=>{
  if(!holding){
   holding=true;const response=await route.fetch();const data=await response.json();
   data.summary.MAE_C=result.sentinelMAE;
   notifyHeld();await gate;await route.fulfill({response,json:data});notifyReturned();
  }else if(blockNew)await route.fulfill({status:503,body:'SYNTHETIC new cohort blocked'});
  else await route.continue();
 });
 // 把在途的预测请求扣住，再切到新 epoch：这是 rc2 的竞态。旧响应放行后不得写回，
 // 且新数据组的请求不得被这条在途请求（旧版的 busy 标志）阻塞。
 await Promise.race([held,new Promise((_,reject)=>setTimeout(()=>reject(Error('old request not held')),5000))]);
 blockNew=true;
 const epoch=await command('new-epoch');result.newRun=epoch.run_id;result.newEpoch=epoch.source_epoch;
 if(result.oldRun!==result.newRun||result.oldEpoch===result.newEpoch)throw Error('did not switch epoch in same run');
 // 新数据组不再被在途请求阻塞，运行信息会很快重新填充；以页面收到切组后的提示为准。
 await page.waitForFunction(()=>document.querySelector('#trendCaption').textContent.includes('已切换到新的观察过程'));
 result.newSnapshotReceived=true;
 result.scoreAfterSwitch=await page.locator('#score').innerText();
 result.clearedBeforeOldResponse=result.scoreAfterSwitch.trim()==='';
 await page.screenshot({path:'output/playwright/'+health.version+'-epoch-before-late.png',fullPage:true});
 releaseOld();await returned;await page.waitForTimeout(500);
 result.oldResponseActuallyReturned=true;result.scoreAfterOldResponse=await page.locator('#score').innerText();
 result.lateResponseIgnored=result.scoreAfterOldResponse.trim()===''&&!result.scoreAfterOldResponse.includes(result.sentinelShown);
 result.latestMatch=await page.locator('#latestMatch').innerText();
 result.fixed=result.clearedBeforeOldResponse&&result.lateResponseIgnored;
 await page.screenshot({path:'output/playwright/'+health.version+'-epoch-after-late.png',fullPage:true});
 blockNew=false;await page.unroute('**/api/v1/predictions?**');
 return result;
}
