用户输入.tmp时，请将回答内容按周归档到.agents/.tmp/agent/YYYY-MM-DD_YYYY-MM-DD/。
- 每周从周日 00:00 开始，到下周日 00:00 前结束，按 Asia/Shanghai 时区计算；目录名的两个日期分别为该周周日和周六，例如 2026-09-13_2026-09-19。
- 周目录下的 Markdown 文件统一命名为 YYYY-MM-DD_HH-mm_任务名称.md. Use `TZ=Asia/Shanghai date '+%Y-%m-%d_%H-%M'`。按文件名日期确定所属周。
- 新增回答时更新 .agents/.tmp/agent/README.md 的归档索引；移动既有文档时同步调整相关链接。无日期前缀的旧文档按归档前文件修改日期归档，并在索引中注明依据。
- 临时脚本、实验数据等资源放 .agents/.tmp/task/<任务名>/（已 gitignore），不要在 git 跟踪范围内新建。
- md的公示排版参考`.agents/prompts/公式排版.md`. Tex自由考虑
- 用户在末尾部分输入< 20或者< 10时，指的是< n行.
- .tmp的内容，请不要在chat context里二次重复，浪费上下文记忆.
- 所有新增报告（含 .tmp Markdown）须在开头声明 `agent name: <model slug>`，使用 `get-model-name` 获取；无法核实时写 `unknown`，不得猜测。
- 用户说"对齐"的时候，表示用户尚不清楚该怎么做，请你不要擅自行动，而是和用户沟通交流，商量该怎么做。用户没说对齐的时候，你自行裁定是否需要对齐.（风险性不大的时候直接CRUD即可）
