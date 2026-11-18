/* reader / editor / shell 共用的小工具；各打包文件开头都带这一段，重复加载时只初始化一次。 */
window.HTD = window.HTD || (() => {
  "use strict";
  const rawBase = typeof window.__HTD_BASE__ === "string" && window.__HTD_BASE__ ? window.__HTD_BASE__ : "/";
  const base = rawBase.endsWith("/") ? rawBase : `${rawBase}/`;
  const paper = typeof window.__HTD_PAPER__ === "string" ? window.__HTD_PAPER__ : "";
  const api = (path) => base + String(path).replace(/^\/+/, "");
  const GLOBAL_KEYS = new Set(["reader.theme", "reader.measure", "editor.autoSave", "editor.linkSync"]);
  const keyOf = (k) => (!paper || GLOBAL_KEYS.has(k) || String(k).startsWith("htd:")) ? k : `htd:${paper}:${k}`;
  const store = {
    key: keyOf,
    get: (k) => { try { return localStorage.getItem(keyOf(k)); } catch { return null; } },
    set: (k, v) => { try { v == null ? localStorage.removeItem(keyOf(k)) : localStorage.setItem(keyOf(k), v); } catch {} },
  };
  const escHtml = (s) =>
    String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  const ico = (d, sz = 14) =>
    `<svg class="cc-ico" width="${sz}" height="${sz}" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">${d}</svg>`;
  return { base, paper, api, store, escHtml, ico };
})();
