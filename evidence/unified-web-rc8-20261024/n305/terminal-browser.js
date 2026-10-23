async page => {
 const errors=[];page.on('pageerror',e=>errors.push(String(e)));
 await page.reload();
 await page.waitForFunction(()=>document.querySelector('#scoreCaption')?.textContent.includes('已结束 · 历史来源'),null,{timeout:15000});
 const snapshot=await (await page.request.get('http://127.0.0.1:59009/api/v1/snapshot')).json();
 const api=await (await page.request.get('http://127.0.0.1:59009/api/v1/predictions?horizon_s=45')).json();
 const future=await page.locator('#futureValues .row>span:last-child').allTextContents();
 if(snapshot.publication_status!=='ended'||snapshot.prediction_history_identity.source_epoch>=snapshot.source_epoch||!api.records.length||!api.records_complete||future.some(v=>v!=='—'))throw Error('terminal history/withdrawal failed');
 const score=await page.locator('#score').innerText();
 if(!score.includes(api.summary.MAE_C.toFixed(2)))throw Error('terminal displayed MAE differs from backend');
 const caption=await page.locator('#scoreCaption').innerText();
 await page.screenshot({path:'output/playwright/n305-rc8-ended.png',fullPage:true});
 if(errors.length)throw Error(errors.join('\n'));
 return {scope:'N305 actual Web after cold restart and browser reload, no injected DTO',publication_status:snapshot.publication_status,raw_source_epoch:snapshot.source_epoch,history_identity:api.history_identity,records:api.records.length,summary:api.summary,caption,score,future,pageErrors:errors};
}
