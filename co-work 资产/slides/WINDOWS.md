# Windows 11 汇报与编辑

先把 ZIP **全部解压**到普通文件夹，例如 `D:\Talks\filtering-win11`，不要在压缩包预览窗口中启动。

## 现场直接汇报，无需安装开发环境

- `talks/filtering/output/academic.pptx`：用 PowerPoint 打开并按 F5。每页为图片，保留当前排版和字体；修改内容请编辑源 Markdown。
- `talks/filtering/output/academic.pdf`：用 Edge 或 PDF 阅读器打开，进入全屏。这个版本保留导出时的字体和图形。

## 网页播放

已安装 Node.js 时，双击根目录 `start-presentation.cmd`，浏览器会打开 `http://127.0.0.1:3030/`。只用 Node 自带模块，不需 `npm install` 或联网。保持命令窗口开启，用方向键翻页、F11 全屏，结束时 Ctrl+C。

未找到 Node 时，脚本会打开 PDF。端口占用时在 CMD 中运行 `start-presentation.cmd 3031`。不要直接双击 `dist/index.html`，网页需要本地 HTTP 服务。

网页播放版不提供修改 Markdown、排序、粘贴上传或 Draw.io 编辑，所有现有图片和公式可离线显示。Windows 网页字体会按本机字体回退；要保持导出时的外观，使用随包 PDF/PPTX。

## 保留网页编辑能力

1. 安装 Node.js 24（本次在 Linux 用 v24.18.0 验证），安装时包含 npm。
2. 双击根目录 `start-editing.cmd`，或进入某个 `talks/<名称>/` 双击 `start.cmd`。
3. 首次自动运行 `npm ci` 安装锁文件依赖，需要网络；随后打开编辑服务。首次安装跳过 Playwright 浏览器下载，编辑不需要该浏览器。
4. 编辑 `talks/filtering/slides.md`；素材在相邻 `public/`。支持网页排序增删、拖拽、Ctrl+V 图片、右侧 Markdown 编辑。Draw.io 内嵌编辑器需访问 `embed.diagrams.net`。

新建汇报：在工作区根目录执行 `npm run new -- my-talk`，再双击 `talks/my-talk/start.cmd`。每个 talk 也保留 `start.sh` 供 Bash 使用。所有启动脚本依据自身路径定位文件。

如果 `node_modules` 是从 Linux/macOS 复制的，请删掉它并重新 `npm ci`；本 ZIP 不包含此目录。Windows 可使用 CMD，避免 PowerShell 对 npm.ps1 的执行策略限制。

## 修改后重新生成汇报文件

在根目录 CMD 执行：

```bat
npm run build -- filtering
npx playwright install chromium
npm run export:pdf -- filtering
npm run export:pptx -- filtering
```

构建输出在 `talks/filtering/dist/`，导出输出在 `talks/filtering/output/`。自定义排序、图形源文件、图片原图与坐标都保存在源码中。
