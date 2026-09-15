# HITSZ 学术汇报：共享主题与独立内容

每份汇报只维护 Markdown 和自己的素材，通过 `theme: hitsz-academic` 引用共享外观，通过 `addons: [slide-sorter, drawio-editor, image-paste]` 使用页面管理和图形编辑。新建时不再复制 Vue、CSS 或服务端代码。

## 启动与新建

以下命令在本目录执行。从 Git 仓库根目录先进入：

```bash
cd "co-work 资产/slides"
```

首次安装依赖：`npm ci`。需要 Node.js 20.12 或以上。离线汇报只需完整解压 ZIP 后双击 `启动汇报.cmd`，运行环境已内置。开发者的 Windows 使用说明见 [WINDOWS.md](WINDOWS.md)，每个 talk 另有 `start.cmd`。整个工作区只安装一次依赖，后续新建汇报不需要重新安装。

```bash
# 当前汇报：http://localhost:3030
npm run dev

# 新建一份汇报，然后启动
npm run new -- seminar-2026
npm run dev -- seminar-2026

# 若当前汇报仍在运行，用另一个端口
npm run dev -- seminar-2026 --port 3031

# 通用起步示例：http://localhost:3031
npm run dev:starter
```

终端保持运行；按 Ctrl+C 停止。新建命令不会覆盖已有目录。汇报名使用小写英文字母、数字、短横线或下划线。

## 在每份汇报目录直接启动

每个 `talks/<汇报名>/` 都有可执行的 `start.sh`，新建汇报也会自动带上。进入汇报目录后运行：

```bash
./start.sh             # 默认端口 3030
./start.sh 3031        # 指定端口
bash start.sh         # 也可以显式使用 Bash
```

启动当前汇报的完整示例（从工作区根目录）：

```bash
cd talks/filtering
./start.sh
```

也支持 `./start.sh --port 3031`。脚本根据自身位置寻找共享启动器，可以从任意工作目录调用，也不依赖仓库绝对路径。按 Ctrl+C 停止；终端需保持运行。

## 文件边界

```text
packages/
  theme-hitsz/         共享布局、校标、字体、配色、默认配置
  addon-drawio/        共享图形编辑组件与本地保存服务
  addon-slide-sorter/  网页缩略图排序与 Markdown 保存
  addon-image-paste/   Ctrl+V 图片落盘与可拖拽图片块
scripts/              启动、构建、新建、兼容修补
scaffolds/talk/        新建时复制的最小内容骨架
talks/
  filtering/          张守信的完整汇报示例
  starter/            通用 5 页起步示例
  cover-reference/    历史 HITSZ 首页参考
```

| 想修改什么 | 文件 |
| --- | --- |
| 当前汇报标题、日期、正文、公式和拖拽坐标 | [talks/filtering/slides.md](talks/filtering/slides.md) |
| 新汇报内容 | `talks/<汇报名>/slides.md` |
| 所有汇报的配色与字号 | [packages/theme-hitsz/styles/academic.css](packages/theme-hitsz/styles/academic.css) |
| 封面与正文母版 | [packages/theme-hitsz/layouts/](packages/theme-hitsz/layouts/) |
| 字体、画布和默认配置 | [packages/theme-hitsz/package.json](packages/theme-hitsz/package.json) 的 `slidev.defaults` |
| 某一份汇报的图形文件映射 | 该汇报的 `drawio.config.mjs` |
| 新建汇报的初始文字 | [scaffolds/talk/slides.md](scaffolds/talk/slides.md) |

主题修改会影响所有引用它的汇报；正文、素材和拖拽坐标各自独立。骨架只在新建时复制，之后修改骨架不会改写已有汇报。

## 写作与拖拽

```yaml
---
theme: hitsz-academic
addons:
  - drawio-editor
  - slide-sorter
  - image-paste
title: 我的汇报
author: 汇报人
layout: hitsz-new-cover
defaults:
  layout: academic
  section: 我的课题
---
```

标题写在 Markdown 正文，汇报人、单位和日期写在封面的 `::details::` 下方。主题中没有固定汇报日期或作者。

正文使用 `layout: academic`。密集页加 `class: research-slide`：页面标题 30 px、分块标题 20 px、正文 17 px；具体排版参考起步示例第二页。`v-drag` 中的 Markdown 仍能在侧栏改字，双击块后拖动，坐标写入同页 `dragPos`。两栏可以是两个独立拖拽块，也可以用主题已有的 `.columns` 网格。

Draw.io 内部的文字、节点和箭头存于本汇报的 `.drawio` 文件，用“编辑流程图”打开内嵌编辑器修改。整张图在幻灯片上的位置继续保存在 Markdown 中。参见 [图形编辑说明](research/DRAWIO_EDITING.md)。

当前示例完整保留作者的文字、公式、页序和自定义排版，包含数学原理、BPF/ETPF 算法分析、仿真、后续工作和致谢。页数以 Markdown 为准。理论与实验来源见 [内容映射](research/CONTENT_MAP.md)。起步示例中的高斯图是占位图，正式汇报前替换。

## 在网页里调整页序

把鼠标移到页面左下方，点击底部工具栏的“排序”，即可拖动缩略图。拖到目标缩略图左侧插到它前面，右侧插到它后面；松手后自动保存到当前汇报的 `slides.md`。也可点击“前移”或“后移”。显示“已保存到 Markdown”后关闭面板继续播放，刷新仍保留页序。

首张封面包含全局配置，固定在首位，其余页面都可排序。每页的文字、公式、图形引用和 `dragPos` 一起移动。新建汇报已自动启用 `slide-sorter` 插件，无需额外配置。

排序面板也支持增删页面：点击缩略图选中位置，再点“＋ 新增页”，在其后插入可拖拽的小字体双栏页；每张内容页下的“复制页”保留完整排版和内容，“删除页”确认后删除。新增和复制后关闭面板，即可用侧边编辑器继续写作。封面不能复制或删除。增删、复制会自动刷新并恢复面板，确保页数、缩略图与编辑器同步。新建 talk 自动继承这些功能。

如果同时从编辑器修改 Markdown，发生版本冲突时点击“重新加载”再拖动。保存前原稿备份位于本汇报 `.slide-order-history/`。功能仅在本地开发服务提供。详细说明见 [排序插件](packages/addon-slide-sorter/README.md)。

## 构建与导出

```bash
npm run build                         # 当前汇报
npm run build -- seminar-2026          # 指定汇报
npm run export:pdf -- seminar-2026
npm run export:pptx -- seminar-2026
```

输出分别位于该汇报的 `dist/`、`output/academic.pdf` 和 `output/academic.pptx`。PPTX 是图片式兼容播放文件；继续编辑应使用 Markdown 和 Draw.io 源文件。首次导出如缺浏览器，运行 `npx playwright install chromium`。

## 兼容与迁移

此目录可作为独立工作区复制使用，不依赖原仓库的临时目录或 Linux 符号链接。`talks/filtering/` 保留作者完整汇报，`talks/starter/` 和 `scaffolds/talk/` 供新汇报复用。

BPF 现以 `talks/filtering/public/diagrams/bpf.drawio` 为该汇报的源文件，保存只更新本汇报的 XML/SVG。此前的 `2026-09-10_drawio-replicas/bpf/` 保留为原始来源，不再随幻灯片编辑自动改写。

工作区锁定 Slidev 52.19.1，并保留工具栏图标修复与拖拽后侧栏改字的兼容修补。启动和导出必须经过 npm scripts 或 `scripts/slidev.mjs`。开发迁移时复制整个工作区并排除 `node_modules`，然后执行 `npm ci`；现场汇报 ZIP 已包含 Windows x64/ARM64 运行环境、预构建网页、PDF 和图片式 PPTX，双击 `启动汇报.cmd` 即可离线启动。只复制 `talks/` 不会携带共享代码。

共享包当前是本地 npm workspace 包，并未发布。历史汇报若需长期固定外观，应归档对应共享包与锁文件。

## 维护验证

```bash
npm run check:workspace
npm run check:drawio
npm run check:sorter
npm run check:images
```

测试使用独立临时目录，不修改正式汇报。浏览器拖拽回归脚本 `scripts/check-editor.mjs` 必须显式指定隔离副本 `SLIDEV_TEST_FILE` 与服务 `SLIDEV_TEST_URL`。迁移验证摘要见 `PORTABILITY.md`。历史研究记录保留在 `research/`，旧路径说明以本文件为准。

结构依据：[Slidev 主题](https://sli.dev/guide/write-theme)、[Slidev 插件](https://sli.dev/guide/write-addon)。


### 网页编辑与本地文件同步

共享启动环境通过 `scripts/patch-slidev-editor.mjs` 为固定版本 Slidev 52.19.1 应用补丁（`npm install` 后自动执行）。网页编辑框即使保持焦点，也会同步本地 Markdown 的变更；有未保存草稿时，保存接口检查其源版本，冲突会显示提示并保留草稿，避免整页旧内容覆盖本地文件。可先复制草稿，再点击“放弃当前草稿，载入本地文件”继续修改。

回归验证请针对单独的 filtering 副本及其开发服务器执行，勿指向正式汇报：

```bash
SLIDEV_TEST_FILE=/absolute/path/to/test-talk/slides.md \
SLIDEV_TEST_URL=http://127.0.0.1:3032 \
node scripts/check-editor-sync.mjs
```

该测试覆盖保持焦点时修改文件、继续网页编辑、冲突保留草稿、重新载入、刷新持久化以及备注编辑。升级 Slidev 时必须重新审查这个版本补丁。


### Ctrl+V 粘贴图片与页面背景

现有汇报和新建 talk 已启用 `image-paste`。复制截图或图片后，在幻灯片画面按 Ctrl+V，会保存到当前 talk 的 `public/images/`，并在本页插入可拖拽的 Markdown 图片块。右侧 Markdown 编辑器中也可粘贴图片，普通文字粘贴保持原行为。工具栏“贴图”按钮提供同一功能；详见 [剪贴板图片插件](packages/addon-image-paste/README.md)。

`academic` 布局支持在单页 frontmatter 中设置背景图：

```yaml
layout: academic
class: academic-thanks
background: /images/thanks-background.png
```

图片按比例铺满页面，正文保持 Markdown 文本。当前 filtering 致谢页使用用户提供的背景图。

## 资产快照与 Windows 汇报包

这是原临时工作区在本次打包时的独立快照；继续修改原临时目录不会自动同步到这里。维护者可直接在本目录开发。作者自己的汇报、Draw.io 源图、仿真数据、截图和致谢背景均保留，方便阅读和复用。

- [Win11 使用说明](WINDOWS.md)
- [跨平台验证与范围](PORTABILITY.md)
- [当前完整汇报](talks/filtering/slides.md)
- [素材来源说明](ATTRIBUTION.md)

构建缓存和单独生成的播放文件不进入默认 Git 跟踪；通过 `releases/` 分发包含它们的 ZIP。修改 Markdown 后，网页构建和 PDF/PPTX 需重新生成。
