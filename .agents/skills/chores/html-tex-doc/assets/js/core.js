/* reader 与 editor 共用的小工具；两个打包文件开头都带这一段，重复加载时只初始化一次。 */
window.HTD = window.HTD || (() => {
  "use strict";
  const store = {
    get: (k) => { try { return localStorage.getItem(k); } catch { return null; } },
    set: (k, v) => { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch {} },
  };
  const escHtml = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const ico = (d, sz = 14) =>
    `<svg class="cc-ico" width="${sz}" height="${sz}" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">${d}</svg>`;
  return { store, escHtml, ico };
})();
