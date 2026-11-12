const loading=document.querySelector('#loading'), message=document.querySelector('#load-message'), status=document.querySelector('#status');
const views=[...document.querySelectorAll('[data-view]')], rotate=document.querySelector('#rotate');
let auto=false;
function selected(name) {for(const button of views){const active=button.dataset.view===name;button.classList.toggle('active',active);button.setAttribute('aria-pressed',String(active));}}
try {
  const { createViewer } = await import('./viewer.js');
  const viewer=await createViewer(document.querySelector('#viewer'),percent=>{message.textContent=percent===null?'正在载入校徽…':`正在载入校徽 ${percent}%`;});
  loading.hidden=true;document.querySelectorAll('.toolbar button').forEach(b=>b.disabled=false);status.textContent='自由视角 · 已就绪';
  function stopRotation(){auto=false;viewer.setAutoRotate(false);rotate.setAttribute('aria-pressed','false');rotate.textContent='自动旋转';}
  for(const button of views) button.addEventListener('click',()=>{stopRotation();viewer.view(button.dataset.view);selected(button.dataset.view);});
  rotate.addEventListener('click',()=>{auto=!auto;viewer.setAutoRotate(auto);rotate.setAttribute('aria-pressed',String(auto));rotate.textContent=auto?'停止旋转':'自动旋转';if(auto)selected(null);});
  document.querySelector('#reset').addEventListener('click',()=>{stopRotation();viewer.view('angled');selected('angled');});
  viewer.onManual(()=>{stopRotation();selected(null);});
  window.addEventListener('pagehide',()=>viewer.dispose(),{once:true});
} catch(error) {
  console.error('校徽加载失败',error);loading.querySelector('.spinner').hidden=true;
  message.textContent=/webgl/i.test(String(error))?'浏览器未能启用 3D 显示，请启用图形加速后重试。':'模型未能载入，请确认本地服务仍在运行后重试。';
  const retry=document.querySelector('#retry');retry.hidden=false;retry.onclick=()=>location.reload();status.textContent='载入失败';
}
