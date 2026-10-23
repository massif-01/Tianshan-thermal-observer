// 多语言：以中文原文为键（缺词条时回退为中文原文），英文词条在 en.ts，后端直接给出的中文对照在 backend-map.ts。
import {EN} from './en';
import {BE_EXACT,BE_PATTERNS} from './backend-map';

export type Lang='zh'|'en';
const saved=(()=>{try{return localStorage.getItem('tto-lang');}catch{return null;}})();
export const lang:Lang=saved==='en'?'en':'zh';
export const locale=lang==='en'?'en-US':'zh-CN';
export const langNames:Record<Lang,string>={zh:'简体中文',en:'English'};
export const langShort:Record<Lang,string>={zh:'中文',en:'EN'};
document.documentElement.lang=lang==='en'?'en':'zh-CN';
document.title=lang==='en'?'TTO Thermal Observer':'TTO 热观察台';

/** 取词条；{name} 占位符由 vars 填入。 */
export const t=(zh:string,vars?:Record<string,string|number>)=>{
 let s=lang==='en'?(EN[zh]??zh):zh;
 if(vars)s=s.replace(/\{(\w+)\}/g,(_,k)=>String(vars[k]??''));
 return s;
};

/** 切换语言：写入偏好并刷新页面（后端数据在，刷新后一秒内恢复）。 */
export const setLang=(l:Lang)=>{try{localStorage.setItem('tto-lang',l);}catch{/* 隐私模式下无法保存，仍然刷新 */}location.reload();};

/** 静态模板里的文字：逐个文本节点和 aria-label / title / placeholder 属性按词条整句替换。 */
export function translateDom(root:ParentNode){
 if(lang!=='en')return;
 const walker=document.createTreeWalker(root as Node,NodeFilter.SHOW_TEXT);
 const nodes:Text[]=[];for(let n=walker.nextNode();n;n=walker.nextNode())nodes.push(n as Text);
 for(const n of nodes){const raw=n.nodeValue||'',s=raw.trim();if(s&&EN[s]!==undefined)n.nodeValue=raw.replace(s,EN[s]);}
 (root as Element).querySelectorAll?.('[aria-label],[title],[placeholder]').forEach(el=>{
  for(const a of ['aria-label','title','placeholder']){const v=el.getAttribute(a);if(v&&EN[v]!==undefined)el.setAttribute(a,EN[v]);}
 });
}

/** 后端直接给出的中文：先查精确对照，再按句式匹配；查不到则原样显示。 */
export const be=(zh:string|null|undefined):string=>{
 if(zh==null)return '';
 const s=String(zh);
 if(lang!=='en')return s;
 if(BE_EXACT[s]!==undefined)return BE_EXACT[s];
 for(const [re,rep] of BE_PATTERNS){const m=re.exec(s);if(m)return rep.replace(/\$(\d)/g,(_,i)=>m[Number(i)]??'');}
 return s;
};
