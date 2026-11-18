/* Web 双栏源码工作台 + 全文搜索 + 类 LaTeX Workshop SyncTeX 正反向行级高亮对齐（仅 serve 模式加载）：
 *  - 快捷键：
 *      Ctrl+\          开启 / 收起双栏工作台
 *      Ctrl+S          立即保存当前文件并触发局部渲染
 *      Ctrl+F          当前文件内搜索（Enter / Shift+Enter 上下跳转）
 *      Ctrl+Shift+F    跨全部源文件全局搜索
 *      Ctrl+单击(右侧) / Alt+单击(右侧)   反向同步：从渲染文字/公式/图表精准跳回左侧源码行与词语位置
 *      Ctrl+单击(左侧) / 单击行号槽 / Ctrl+Alt+J / Alt+Enter   正向同步：从源码行跳至右侧对应渲染行高亮
 *      按住 Ctrl 悬停右侧                 实时瞄准框与源文件行号角标预览
 */
(() => {
  "use strict";
  if (!window.__HTML_TEX_LIVE__) return;

  const root = document.documentElement;
  const { api, paper, store, escHtml, ico: ccIco } = window.HTD;
  if (paper) root.setAttribute("data-in-shell", "1");
  const escRe = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

  let docRoot, splitBtn, edPane, resizer, fileSelect, dirtyDot, saveBtn, edMenu, histPanel;
  let findBar, findInput, findCountEl, caseBtn, regexBtn, globalBox;
  let linkSyncChk, autoSaveChk, statusLeft, statusRight;
  let edScroll, edStage, edBackdrop, edTa;
  let aimBadge, errBanner;

  // 编辑器状态
  let filesMeta = [];
  let curFile = "";
  let baseMtime = null;
  let diskContent = "";
  let isDirty = false;
  let isSplit = store.get("editor.splitOpen") === "1";
  // 实时同步（默认开）：停笔 REALTIME_DELAY 毫秒后自动保存，右侧随即热补丁；关闭后需 Ctrl+S
  const REALTIME_DELAY = 200;
  let autoSave = store.get("editor.autoSave") !== "0";
  let linkSync = store.get("editor.linkSync") !== "0";
  let curLine = 1;
  let syncRange = null; // { l1, l2 }
  let findState = { q: "", cs: false, rx: false, hits: [], idx: -1 };
  let autoSaveTimer = null;
  let saveInFlight = false;
  let saveQueued = false;
  let peerTimer = null;
  let hlClearTimer = null;
