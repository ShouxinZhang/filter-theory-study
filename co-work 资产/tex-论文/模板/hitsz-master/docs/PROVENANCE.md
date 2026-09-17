# 来源与迁移范围

迁移日期：2026-09-18。

- 学位论文源：仓库 `.agents/.tmp/user/hitszthesis-master`，类文件标识 hitszthesis 3.2.8（2023-05-09）。`hitszthesis.cls`、`hitszthesis.cfg`、`hitszthesis.bst` 与 `License` 原样复制，保留版权。
- 定制来源：同级 `hitsz-midterm` 资产及其来源记录。以中期 `hithesis.bst` 为基础，保留 DOI 补丁、标点与会议著录行为；按用户后续要求，将英文姓名的前缀、姓、名字缩写及后缀统一为大写。中文姓名及 et al 保持原样。
- 字体：保留中期类的西文字体设置、显式 Fandol、newtxmath 和求和符号补丁；学位论文的正文小四、图表题注五号沿用类默认。
- 算法：保留中期 algorithm2e 配置，只将 section 计数改为 chapter；未加载上游演示用 hitszthesis.sty，避免其第二套算法配置覆盖定制。
- 文献：保留环境初始化之后应用的孤行惩罚和条目间距；有期刊名、卷、页、DOI 且无 URL 的 article 不加 /OL、不输出访问日期，使用短 DOI 形式。
- AI 声明：保留默认开启的开关，标题与正文参考 [ICLR 2027 AI 政策](https://iclr.cc/Conferences/2027/AIPolicyForAuthors)及[官方模板](https://media.iclr.cc/Conferences/ICLR2027/iclr-2027-style-files.zip)，译写为中文并采用单一作者口吻；包含已使用、未使用、不适用任务及核查与责任说明。保留待填占位符，不代表作者已完成相应工作。按用户要求置于结论之后、参考文献之前，采用学位论文无编号章样式。
- 毕业论文结构：采用 master、前后置部分、硕博书序、章内编号、双语图表题注。未迁入中期五节结构、浮动参数和末两节连续排版补丁。
- 资产化：使用模块化入口、相对路径、统一 Bash/VS Code 构建；排除演示人物信息、原示例研究正文、演示图片、历史 PDF、日志和与此模板无关的术语宏。

本目录是本地派生模板，不声称官方维护或已核验最新提交规范。源模板目录与中期资产保持不变。
