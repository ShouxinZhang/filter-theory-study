# Slidev 学术汇报：研究结论与边界

核查日期：2026-09-09。npm 实际安装版本：`@slidev/cli 52.19.1`，`@slidev/theme-default 0.25.0`，`playwright-chromium 1.63.0`。Node 实测版本 22.19.0，CLI 的声明要求为 >=20.12.0。依赖由模板内的 lockfile 固定。

## 核心判断

需求可以分成两个环节：用 Markdown 快速表达内容，用鼠标调整可见块的位置。Slidev 原生能力已经覆盖这两个环节。本轮同时发现原版坐标缓存缺陷，并在模板中加入限定版本的小补丁，才能稳定衔接拖动与侧栏改字；没有自建复杂排版编辑器。

这是一套“文本源文件驱动的局部可视化排版”工作流。若期待所有文字默认都能拖拽，完整对齐分布，多选组合，成熟的撤销历史，以及 PowerPoint 对象级往返编辑，则本轮方案没有达到这些要求。

## 能力与证据

| 需求 | 本轮结论 | 依据 |
| --- | --- | --- |
| Markdown 与 LaTeX 快速写作 | 可用，常规页无需坐标 | 8 页示例渲染 |
| 同屏改文本和看幻灯片 | 内置侧栏可用，自动写回源文件 | 鼠标打开编辑器并改字，磁盘检查 |
| 移动，缩放，旋转 | 包装成 `v-drag` 的块可用 | 实际鼠标操作，frontmatter 差异 |
| 保存布局后重开 | 移动后刷新保留坐标 | 文件值与 DOM 样式一致 |
| 图与公式独立排版 | 各自放在独立容器内可用 | 第五页三个独立块 |
| 自动避让与文字自适应 | 本模板没有实现 | 仍需逐页检查容器与内容 |
| 多选，组合，对齐分布面板 | 本轮未提供，不能视为 PPT 等价物 | 原生交互只验收了单块编辑 |
| 多端同时编辑冲突处理 | 未验证，不提供保证 | 避免同时覆盖源文件 |
| 原生可编辑 PPTX | Slidev 自带导出不满足 | 官方明确按页导出图片，且本轮检查输出结构 |
| 静态网页写回本机 Markdown | 不满足 | 源码中写回受开发模式与编辑功能条件限制 |

## 写回机制

安装包中的 `@slidev/client/composables/useDragElements.ts` 包含 `useDragElementsUpdater`：只有 `__DEV__ && __SLIDEV_FEATURE_EDITOR__` 为真时才启用保存；命名位置更新 `frontmatter.dragPos`，经约 500 ms 防抖调用 `update`。

同包 `composables/useSlideInfo.ts` 使用 `/__slidev/slides/<页码>.json` 的 POST 请求发送补丁。鼠标操作后的本地文件差异确认了完整写回链路。版本升级时应复查这些实现，尤其是拖拽与保存行为。

这是实测版本的实现说明，不意味着长期稳定的第三方 API。模板直接使用原生组件，不自己请求该内部端点。

## 已复现并修补的坐标缓存问题

未修补的 52.19.1 中，拖拽后的磁盘坐标为 `589,307,305,127`，侧栏仍显示 `609,307,305,127,0`。随后改一个词并保存，磁盘位置回到旧值。刷新浏览器后再开侧栏也出现同样问题。

原因定位到开发服务器的保存处理：它更新了 `slide.source.frontmatterDoc` 与 `slide.frontmatter`，却没有同步 `slide.frontmatterRaw`。侧栏 `SideEditor.vue` 正是从后者构建可编辑内容。在跳过完整 HMR 的拖拽路径中，旧的序列化文本继续留在缓存。

模板的 `scripts/patch-slidev-editor.mjs` 在原有保存流程中增加一行，将 `frontmatterDoc.toString()` 同步到这两个 raw 字段。它只作用于模板本地安装的 npm 依赖，不修改全局软件。脚本检查精确版本与唯一代码锚点，可重复执行。版本不匹配会明确报错，升级时须重新审核或移除已无必要的补丁。

补丁通过 `postinstall` 安装。不要使用 `npm ci --ignore-scripts` 来复制此工作流。若曾跳过脚本，手动运行 `node scripts/patch-slidev-editor.mjs` 后重启开发服务。

补丁后的实测值：拖拽前 `609,307,305,127,0`，拖拽后 `589,307,305,127`，侧栏读取与改字保存后都保持后者。模板还提供 `npm run check:editor`，对拖动，侧栏改字，写回与刷新保留进行真实浏览器输入回归。执行时先启动本模板的 3030 开发服务，不要同时手动编辑示例。脚本会临时改变示例并在结束时还原。

证据保存在 `validation/editor-stale-coordinates.json` 与 `validation/editor-fixed-coordinates.json`。这是项目本地修补，没有声称已向上游提交或获得官方修复。

## 采用的模板策略

固定母版负责标题层级，正文边距，页脚与双栏。Markdown 负责叙述和数学表达。只有复杂结果页使用命名拖拽块。这能让大多数页面继续保持简短，避免整份演示退化成手写坐标。

模板保留通用学术结构：问题，数学模型，方法，结果，实验记录，结论与引用。演示主题采用非线性滤波，是基于当前工作区的上下文选择。可以只替换内容，不必先学习 Vue。

不制作未经授权的学校官方模板。当前颜色与布局为通用设计，后续若提供 HIT 官方样式，可以替换母版，字体和标识。

## 与其他路线的取舍

| 路线 | 适合的主需求 | 本轮取舍 |
| --- | --- | --- |
| Slidev 原生组件与编辑器 | Markdown，数学表达，局部鼠标调整，浏览器演示 | 已实现并验证 |
| Slidev 上另建布局面板 | 必须提供对齐按钮，坐标输入，多选等特定能力 | 暂不开发，先用真实汇报确认缺口 |
| 以原生 PPTX 对象为输出的工具链 | 协作者必须在 PowerPoint 中继续逐个改图文 | 若这是硬要求，应单独选型，不假定 Slidev 可逆 |

后两行是工程路线建议，不是对某款替代软件的实际验证。本轮没有声称比较了所有演示工具。

## 下一轮可验证的问题

- 用一篇真实论文做 10–15 页汇报，记录纯 Markdown 页与拖拽页的占比，以及后期改文字造成的重新排版次数。
- 高频缺口如果确实是对齐与均匀分布，再考虑增加小型布局辅助工具。保存仍应以源文件为准，避免并行维护第二套坐标。
- 需要复用的版式稳定后，将布局与 CSS 提取为本地主题或 addon。现在先保留可直接复制的项目，减少维护成本。
- 若必须交付可编辑 PPTX，应先建立一个含中文，公式，SVG 的转换验收页，验证对象可编辑性，字体与公式一致性，再决定是否投入转换开发。

## 一手资料

- [Slidev Draggable Elements](https://sli.dev/features/draggable)：拖拽，缩放，旋转，命名位置与官方语法。
- [Slidev Integrated Editor](https://sli.dev/features/side-editor)：内置编辑器及保存行为。
- [Slidev Exporting](https://sli.dev/guide/exporting)：PDF/PPTX 导出与图片式 PPTX 限制。
- [Slidev Configure Fonts](https://sli.dev/custom/config-fonts)：字体配置。
- [Slidev VS Code Extension](https://sli.dev/features/vscode-extension)：编辑器配套工具。模板只添加推荐列表，没有自动安装扩展，也未声称完成 VS Code 界面验证。
- [Slidev 源码仓库](https://github.com/slidevjs/slidev)：本轮代码级结论来自安装版本对应的本地 npm 包。
- [Särkkä 作者主页](https://users.aalto.fi/~ssarkka/)：示例末页所引用教材的书目信息与作者提供的 PDF 链接。
