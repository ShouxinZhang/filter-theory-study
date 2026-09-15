# 交付范围与验证

此资产包含共享 HITSZ 主题、Draw.io/排序/图片粘贴插件、可复现的 Slidev 52.19.1 兼容补丁、锁文件、最小新建骨架、全部现有 talk，以及作者使用的完整素材。没有匿名化、删页或改写作者正文。打包时 filtering 为 13 页；Markdown、图形配置和 public 素材均与原工作区逐字节一致。

## 已验证

- 在 `co-work 资产/slides`（含中文与空格路径）独立 `npm ci`，安装后修补成功。
- 工作区、Draw.io、排序、图片粘贴测试共 13 项通过。
- filtering 静态构建成功；在阻断外部网络的 Chromium 中浏览全部 13 页，所有图片加载，未发出外部网络请求，编辑上传入口隐藏。
- PDF 导出成功，13 页；PPTX 导出成功，13 个图片幻灯片。检查致谢页背景与原文字正常。
- 启动器使用相对路径、Windows CMD 文件为 ASCII/CRLF，无 Linux 绝对路径和符号链接依赖。
- ZIP 不包含 Linux node_modules、编辑历史或验证缓存，附逐文件 SHA-256 清单和 ZIP 校验值。

## 验证边界

本次运行环境是 Linux / Node.js v24.18.0。没有实际运行 Windows 11 或 PowerPoint；Windows `.cmd` 已静态检查，但不声称完成了 Windows 实机测试。Headless Chromium 有 Wake Lock 权限提示，不影响页面加载。Windows 网页会使用本机可用的中文字体，PDF 和图片式 PPTX 保留导出时外观。

当前 3030 编辑服务仍使用原临时工作区；资产目录是独立快照。若继续修改原稿，请重新同步 `talks/filtering`，重新构建与导出后，再运行：

```bash
python scripts/package-release.py
```

打包脚本会检查网页、PDF、PPTX 均已生成，将完整工作区和作者播放文件写入 `releases/filtering-win11-日期_时间.zip`。它不会重新构建或自动获取原工作区的新改动。
