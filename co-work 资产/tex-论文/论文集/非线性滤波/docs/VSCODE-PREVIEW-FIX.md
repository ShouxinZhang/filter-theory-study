# LaTeX Workshop 预览排障

日期：2026-09-18。

- [x] 读取当前 VS Code Insiders 10.19.0 扩展日志和根文件选择实现。
- [x] 给论文所有子 TeX 补齐相对根文件声明，保留正文。
- [x] 增加当前仓库工作区配置，使子目录输出路径和脚本配方生效。
- [x] 验证根文件识别、等价配方构建和 PDF 路径。

## 已确认原因

当前 VS Code 打开整个 filter-theory-study 仓库，子目录 `.vscode/settings.json` 不作为工作区配置读取。
03:46:10 与 03:46:16 的日志表明：用户从本论文 `body/chapter01.tex` 构建/预览，因文件缺少根声明，根查找回退后保留了 `模板/hitsz-master/main.tex`；实际构建和预览均指向模板。
另一个独立问题是入口同时含 `TeX program = xelatex` 与 `LW recipe = HITSZ build`；已安装扩展先处理 program，从而只执行一次 xelatex 并输出到模板根目录，未执行 build.sh。

## 修复

补齐缺失的 TeX root，显式指向本论文 main.tex。保留入口的 HITSZ build 配方，去掉会抢先执行的 program 注释。
仓库 `.vscode/settings.json` 注册 HITSZ build，保留扩展已有默认工具与配方；输出目录统一为根文件旁的 build，直接引擎调用也传入该输出路径。自动根搜索排除构建缓存及模板，但直接打开模板主文件仍可识别。
独立打开论文目录时，原有局部设置继续有效。预览目标为本论文 build/main.pdf；output/main.pdf 为构建脚本生成的交付副本。

## 验证

35 个子 TeX 的根声明均按已安装扩展的正则规则解析，解析目标统一为本论文 main.tex。补齐了其中原先缺失的 13 个声明。
实时扩展日志已收到仓库配置变更，并在 03:49:57 将目录结构根切换为 `论文集/非线性滤波/main.tex`。
按工作区 HITSZ build 配方原样展开并执行 `bash <论文目录>/build.sh`，退出码 0；新日志引擎为 XeTeX，PDF 为 42 页，没有未定义引用、溢出或缺字。
`build/main.pdf` 与 `output/main.pdf` 逐字节一致，预览目录设置解析到本论文的 build。
通过 VS Code CLI 请求打开正确的 build/main.pdf；本次未自动点击界面的 View LaTeX PDF 按钮。
