/* 阅读器增强（零外部依赖，离线 build 与在线 serve 共用）：
 *  1. 栏宽：单栏默认自适应，两侧固定手柄可无级拖拽，记忆于 localStorage。
 *  2. 主题：自动 / 浅色 / 深色 三态切换，记忆于 localStorage。
 *  3. 目录单独折叠：文内目录卡片支持整卡折叠与按章收起子节；右上角独立「☰ 目录」浮动抽屉支持筛选与章节滚动高亮（Alt+T）。
 *  4. 链接悬停预览：鼠标悬停页内交叉引用、文献上标或 SVG 内链接时弹出实时目标卡片。
 */
(() => {
  "use strict";
  const root = document.documentElement;
  const { store, ico } = window.HTD;
  const XLINK = "http://www.w3.org/1999/xlink";
  const getDocPane = () => document.getElementById("doc-root") || document.body;

