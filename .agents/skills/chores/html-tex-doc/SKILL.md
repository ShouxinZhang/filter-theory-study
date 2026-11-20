---
name: html-tex-doc
description: 无分页 HTML/受控 Markdown + TeX standalone 出图与算法的混合排版工作流，内置 import-tex/export-tex 毫秒级双向 TeX 互换与最小差异回写，支持可折叠目录、Web 双栏编辑器、全文搜索及 Ctrl+Click 双向高亮对齐。
---

# html-tex-doc

用流式无分页 HTML 或多文件受控 Markdown + MathJax 编写正文与公式，用 TeX `standalone` 编译 TikZ 图与伪代码算法框为内联 SVG，内置 `TeX <-> Markdown` 确定性双向互换，统一编号、双向超链接、深色主题与 Web 双栏实时编辑。

## 速查

```bash
S=.agents/skills/chores/html-tex-doc/scripts/html_tex_doc.py

# 初始化工程骨架：basic（单文件 doc.html）或 academic-md（多章 Markdown + BibTeX + algorithm2e）
python3 $S init <dir> --preset academic-md --title "文档标题"

# 静态增量构建（默认读 <dir>/src，输出 <dir>/outputs/site）
python3 $S build <dir> [--force]
python3 $S build --src <src_dir> --build-dir <build_dir> --out <site_dir>

# 启动实时预览与 Web 双栏编辑服务器（单工程或 --library 多论文工作区，默认 http://127.0.0.1:18767）
python3 $S serve <dir> [--port 18767]
python3 $S serve --library [论文库根目录] [--port 18767]

# 双向 TeX 互换：import-tex（别名 tex2html）与 export-tex（别名 html2tex，默认仅预览 diff）
python3 $S import-tex <tex_dir> [-o <html_dir>] [--check | --apply]
python3 $S export-tex <html_or_tex_dir> --init-tex [--apply] [-f]
python3 $S export-tex <html_or_tex_dir> [--to <tex_dir>] [--apply]

# 一次性安装公式预渲染依赖（需 Node；不装也能用，自动回退到浏览器内排版，仅加载变慢）
npm install --prefix .agents/skills/chores/html-tex-doc/scripts
```

## 核心能力与快捷键

- 同源编译与模块化工作区：支持 `src/main.md` 入口（前置块声明 `title`、`macros`、`bib` 并通过 `<!--include 章节.md-->` 按序组织正文，兼容无 `main.md` 的 `src/*.md` 与单文件 `src/doc.html`），同源解析 `src/macros.tex`，注入双层源码锚点并增量编译 `figs/*.tex` 与 `algs/*.tex`。
- 毫秒级双向 TeX 互换（`import-tex` / `export-tex`）：纯 Python 确定性编解码（`< 200 ms`），支持从受控 Markdown 一键生成父级 `ctexart` LaTeX 工程与 `texsync.json`（`--init-tex`），从既有 `article`/`book` 工程自动发现章节与嵌套 `\input` 导入，以及按句最小差异原子回写（保留未改句原注释、`~` 与手工折行；触碰只读浮动体或切片边界时零字节拒写）。
- 多论文零延迟切换（`serve --library`）：自动发现论文库根目录（默认 `co-work 资产/tex-论文/论文集`）下两层内的全部论文，未打开论文惰性不占资源；左上角常驻 Home 图标按钮（或 `Alt+B`）单帧零重排显隐左侧 210px 垂直标签侧边栏（含 `+ 新建论文` 与可拖拽排序的完整标题标签列表）；已打开论文通过叠放内嵌页 `visibility` 切换（上限 `MAX_ALIVE = 3` 按 LRU 淘汰并自动恢复滚动位置）。
- 公式构建期预渲染：`build`/`serve` 在生成页面前用 Node 版 MathJax 把公式转成 CHTML，浏览器端零排版；结果按内容哈希缓存在 `<dir>/build/mathcache/`（可随时删除），字体随站点输出到 `mathjax-fonts/`，页面不再访问 CDN。环境变量 `HTD_MATH=browser` 强制回退到浏览器内排版，`HTD_MATH=prerender` 在依赖缺失时直接报错。
- 目录折叠：正文内联目录卡支持整卡折叠与收起子节；右上角 `☰ 目录`（`Alt+T`）呼出带章节过滤与阅读进度联动（ScrollSpy）的浮动抽屉。
- Web 双栏工作台（`serve` 模式）：点右上角 `◫ 双栏` 或按 `Ctrl+\` 开合左源码右渲染分屏；支持 `Ctrl+F` 页内搜索，`Ctrl+Shift+F` 跨文件搜索，`Ctrl+S` 保存与防抖热补丁。
- 类 SyncTeX 双向高亮对齐：按住 `Ctrl`/`Cmd` 悬停右侧渲染区预览 `文件:行号`，`Ctrl+Click` 任意句子、公式、定理或算法框即跳至左侧精确源码行（对算法框按 `Ctrl+Shift+Click` 跳至 `.md` 调用处）；左侧点击行号槽、`Ctrl+Click` 或按 `Ctrl+Alt+J` 正向定位右侧段落并双端脉冲高亮。

## 开发与自检

```bash
python3 -m unittest discover -s .agents/skills/chores/html-tex-doc/scripts/tests     # 单元与回归测试
node .agents/skills/chores/html-tex-doc/scripts/perf/cdp_debug.mjs <url> scroll       # 无头 Chrome 测量（HEADED=1 用真实窗口）
```

- 改样式：颜色、字体栈、圆角、层级只在 `assets/css/00_tokens.css` 定义；工程级定制写 `src/theme.css` 或 `src/extra.css`，不要复制整份样式。
- 改前端脚本：按功能编辑 `assets/js/reader/*.js` 或 `assets/js/editor/*.js`，构建时自动拼接。

## 子技能路由

| 场景 | 子技能 | 入口 |
| --- | --- | --- |
| 科研数据图与编排风格可视化（主题自适应内联 SVG + 同尺寸单页矢量 PDF，落盘至 `html/src/figs/` 与本文档链路无缝对接） | charts | [charts/SKILL.md](charts/SKILL.md) |

## 参考

- [references/spec.md](references/spec.md): 受控 Markdown 与 HTML 标签语法、BibTeX、双层 SyncMap 协议、双栏 API 与阅读器细则。
- [references/texsync.md](references/texsync.md): 双向 TeX 互换细则（`import-tex`/`export-tex` 参数、`texsync.json` 清单、`F`/`G` 对照表、嵌套 `\input` 协议与最小差异门禁）。
- [references/templates/src/](references/templates/src/)、[references/templates/academic-md/src/](references/templates/academic-md/src/) 与 [references/templates/tex-article/](references/templates/tex-article/): `basic`、`academic-md` 预设骨架与通用 `ctexart` 父级 LaTeX 工程模板。
- [references/examples/linked-list/README.md](references/examples/linked-list/README.md): 原生无 `.cls` 算法笔记完整示例（TikZ + `algpseudocode`）。
- [references/examples/hithesis-adapter/README.md](references/examples/hithesis-adapter/README.md): 外部 `.cls` 学位论文（`hithesis`）薄适配器接入示例。
