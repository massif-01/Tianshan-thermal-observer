async page => {
 const errors=[];page.on('pageerror',e=>errors.push(String(e)));
 await page.reload();
 await page.waitForFunction(()=>document.querySelector('#stripSt')?.textContent.includes('发布失败 · 最终结果未确认'),null,{timeout:15000});
 const snapshot=await (await page.request.get('http://127.0.0.1:59009/api/v1/snapshot')).json();
 const api=await (await page.request.get('http://127.0.0.1:59009/api/v1/predictions?horizon_s=45')).json();
 const strip=await page.locator('#stripSt').innerText();
 const future=await page.locator('#futureValues .row>span:last-child').allTextContents();
 if(snapshot.publication_status!=='failed'||api.records_complete||api.sync_status!=='unavailable'||future.some(v=>v!=='—'))throw Error('failed closeout incorrectly shown as complete/live');
 await page.screenshot({path:'output/playwright/n305-rc8-failed.png',fullPage:true});
 if(errors.length)throw Error(errors.join('\n'));
 return {scope:'N305 actual filesystem final-write failure, actual Web cold restart and page reload, no code patch or DTO injection',strip,publication_status:snapshot.publication_status,records_complete:api.records_complete,sync_status:api.sync_status,future,pageErrors:errors};
}
