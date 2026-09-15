# HITSZ Academic Theme

在工作区的幻灯片头部写 `theme: hitsz-academic`。本包提供 `academic`、`academic-cover` 和 `hitsz-new-cover` 布局，统一字体与画布配置，以及小字号双栏样式。正文与封面细节通过 Markdown 插槽填写。

校标采用原始 HITSZ 资源，以模块导入方式随主题构建，不要求每份汇报复制校标。基础排版复用 `@slidev/theme-default`，随后加载本主题样式，以保持现有汇报外观。

修改 `styles/academic.css` 调整外观，修改 `package.json` 的 `slidev.defaults` 调整默认配置。单份汇报可在 Markdown 中覆盖配置。不要将作者、日期、课题文字、仿真图或 `dragPos` 放入主题。
