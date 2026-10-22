async (page) => {
 const control=await page.evaluate(()=>sessionStorage.getItem('tto-test-control'));if(!control)throw Error('register local harness control URL');
 const command=async name=>(await page.request.post(control+'/'+name)).json();
 await page.setViewportSize({width:1440,height:1100});
 await page.waitForFunction(()=>document.querySelectorAll('#score b').length===4&&document.querySelector('#contextRows').children.length>0);
 const health=await (await page.request.get('http://127.0.0.1:59009/healthz')).json();
 const old=await (await page.request.get('http://127.0.0.1:59009/api/v1/snapshot')).json();
 let releaseOld,notifyHeld,notifyReturned,holding=false,blockNew=false;
 const gate=new Promise(resolve=>releaseOld=resolve),held=new Promise(resolve=>notifyHeld=resolve),returned=new Promise(resolve=>notifyReturned=resolve);
 const result={version:health.version,oldRun:old.run_id,oldEpoch:old.source_epoch,scoreBefore:await page.locator('#score').innerText(),sentinelMAE:777.123};
 await page.route('**/api/v1/predictions?**',async route=>{
  if(!holding){
   holding=true;const response=await route.fetch();const data=await response.json();
   data.summary.MAE_C=result.sentinelMAE;
   notifyHeld();await gate;await route.fulfill({response,json:data});notifyReturned();
  }else if(blockNew)await route.fulfill({status:503,body:'SYNTHETIC new cohort blocked'});
  else await route.continue();
 });
 // Hold the prediction request inside refreshData, keeping its busy flag set.
 // This is the rc2 race: accept(new epoch) cannot start another refreshData.
 await Promise.race([held,new Promise((_,reject)=>setTimeout(()=>reject(Error('old request not held')),5000))]);
 blockNew=true;
 const epoch=await command('new-epoch');result.newRun=epoch.run_id;result.newEpoch=epoch.source_epoch;
 if(result.oldRun!==result.newRun||result.oldEpoch===result.newEpoch)throw Error('did not switch epoch in same run');
 await page.waitForFunction(()=>document.querySelector('#contextRows').children.length===0);
 result.newSnapshotReceived=true;
 result.scoreAfterSwitch=await page.locator('#score').innerText();
 result.clearedBeforeOldResponse=result.scoreAfterSwitch.trim()==='';
 await page.screenshot({path:'output/playwright/'+health.version+'-epoch-before-late.png',fullPage:true});
 releaseOld();await returned;await page.waitForTimeout(500);
 result.oldResponseActuallyReturned=true;result.scoreAfterOldResponse=await page.locator('#score').innerText();
 result.lateResponseIgnored=result.scoreAfterOldResponse.trim()===''&&!result.scoreAfterOldResponse.includes('777.123');
 result.latestMatch=await page.locator('#latestMatch').innerText();
 result.fixed=result.clearedBeforeOldResponse&&result.lateResponseIgnored;
 await page.screenshot({path:'output/playwright/'+health.version+'-epoch-after-late.png',fullPage:true});
 blockNew=false;await page.unroute('**/api/v1/predictions?**');
 return result;
}
