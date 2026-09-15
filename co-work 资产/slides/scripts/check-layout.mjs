import { chromium } from 'playwright-chromium'
import { mkdir, writeFile } from 'node:fs/promises'
const out=new URL('../validation/content-revision/',import.meta.url).pathname
await mkdir(out,{recursive:true})
const browser=await chromium.launch({headless:true})
try {
 const p=await browser.newPage({viewport:{width:1600,height:1000}}),audit=[]
 for(let i=1;i<=9;i++){
  await p.goto(`http://127.0.0.1:3030/${i}`)
  await p.locator('.slidev-layout:visible').waitFor()
  await p.evaluate(()=>document.fonts.ready)
  await p.waitForTimeout(350)
  await p.screenshot({path:`${out}/page-${i}.png`})
  const blocks=await p.locator('.slidev-layout:visible [data-drag-id]').evaluateAll(es=>es.map(e=>{
   const r=e.getBoundingClientRect(),cs=[...e.querySelectorAll('p,h1,h2,table,.katex-html,ul,img')].map(x=>x.getBoundingClientRect())
   return {id:e.getAttribute('data-drag-id'),overflowRight:Math.round(Math.max(0,...cs.map(c=>c.right-r.right))),overflowBottom:Math.round(Math.max(0,...cs.map(c=>c.bottom-r.bottom)))}
  }))
  audit.push({page:i,katexErrors:await p.locator('.katex-error').count(),blocks})
 }
 await writeFile(`${out}/layout-audit.json`,JSON.stringify(audit,null,2))
 console.log(JSON.stringify(audit))
}finally{await browser.close()}
