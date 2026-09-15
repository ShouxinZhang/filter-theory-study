# Windows 11 汇报与编辑

先把 ZIP **全部解压**到普通文件夹，例如 `D:\Talks\filtering-win11`，不要在压缩包预览窗口中启动。

## 离线一键启动

1. 将 **filtering-win11-offline** ZIP 完整解压到电脑或 U 盘。
2. 双击根目录 **`启动汇报.cmd`**。
3. 自动进入全屏汇报，方向键翻页，**Alt+F4** 退出。

无需网络、无需安装 Node/npm、无需输入命令、不需要管理员权限。Windows x64 和 ARM64 的运行环境均已内置，启动器自动选择。自动使用空闲端口，不会因为 3030 被占用而要求改配置。

启动器优先打开 Windows 自带 Edge 的独立全屏窗口；退出该窗口后自动停止播放服务。若没有检测到 Edge，则打开默认浏览器，此时保留命令窗口直到汇报结束。英文入口 `start-presentation.cmd` 与中文入口作用相同。

这是已构建的离线播放版，所有公式、Draw.io 预览、仿真图与背景都在包内。播放不会安装软件或请求下载。只需双击上述入口，不要点击 `start-editing.cmd`，也不要直接打开 `dist/index.html`。

## 备用文件

- `talks/filtering/output/academic.pptx`：PowerPoint 打开后按 F5；图片式页面保留导出时的排版与字体。
- `talks/filtering/output/academic.pdf`：用 Edge 或 PDF 阅读器打开。

网页会使用 Windows 本机可用字体。备用 PDF/PPTX 保留导出时外观。

## 开发者编辑模式（不是现场启动入口）

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
