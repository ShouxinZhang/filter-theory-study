# Skill 创作与收纳规范细则

## 1. 三块结构（渐进披露）

每个原子 Skill 由三个标准块构成（由 `skill_ctl.py init` 自动创建）：

1. **`SKILL.md`（入口速查，$\leqslant 60$ 行）**
   - 必须包含 YAML Frontmatter：`name` 与 `description`。
   - 正文仅保留 CLI 速查、核心步骤与 `references/` 链接，避免堆砌长篇细则。
2. **`references/`（按需细则与模板）**
   - 存放协议细则（`*.md`）与生成模板（`templates/*`），Agent 仅在需要时按需读取。
3. **`scripts/`（确定性黑盒脚本）**
   - 封装机械操作，优先使用 Python 标准库，支持 `--help`。

可选兼容块：`tests/`（单测）、`agents/`（特定宿主扩展配置）等，`lint` 时自动放行。

## 2. 子 Skill 收纳（Router Pattern）

宿主默认只扫描一级目录 `.agents/skills/<top>/SKILL.md`。因此多个同类技能收纳时采用**一级路由 + 二级原子子技能**：

- **父级路由 `SKILL.md`（$\leqslant 45$ 行）**：
  - `description` 必须汇总各子技能的核心触发词与职责；
  - 正文提供「场景 $\to$ 子技能 $\to$ `[<sub>/SKILL.md](<sub>/SKILL.md)`」路由表与目录树。
- **二级子技能 `.agents/skills/<top>/<sub>/`**：
  - 各自具备完整的 `SKILL.md` + `references/` + `scripts/` 三块结构。
