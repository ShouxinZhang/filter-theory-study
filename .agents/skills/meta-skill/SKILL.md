---
name: meta-skill
description: 创建、收纳与体检本仓库的 Agent Skills（标准 SKILL.md + references/ + scripts/ 三块结构，以及顶层路由组 + 子 Skill 收纳模式）。
---

# meta-skill

统一管理 `.agents/skills/` 下所有技能的创建、子技能收纳与结构体检。

## 速查

```bash
S=.agents/skills/meta-skill/scripts/skill_ctl.py

# 1. 新建独立原子技能 (自动生成 SKILL.md + references/ + scripts/ 三块骨架)
python3 $S init <name> -d "<一句话描述>"

# 2. 在已有路由组下直接新建子技能 (并自动写入父 SKILL.md 路由表)
python3 $S init <sub-name> --parent <group> -d "<一句话描述>"

# 3. 新建顶层路由组 Skill
python3 $S init <group-name> --router -d "<汇总触发词与职责>"

# 4. 将顶层独立技能物理收纳进父路由组 (自动替换内部路径并更新父路由表)
python3 $S pack <standalone-skill> --into <group> [-s "<场景说明>"]

# 5. 体检所有技能 (Frontmatter、行数 <=80、死链、子技能路由登记)
python3 $S lint
```

## 核心准则

1. **三块结构**：每个原子技能由 `SKILL.md`（入口速查）、`references/`（按需细则/模板）、`scripts/`（黑盒 CLI）构成，可选块（`tests/`、`agents/` 等）自动兼容。
2. **子技能收纳**：宿主只扫描 `.agents/skills/<top>/SKILL.md`；同类子技能收纳在路由组 `<group>/<sub-skill>/` 下，由父级 `SKILL.md` 聚合触发词并分发。

## 参考

- [references/spec.md](references/spec.md): 三块结构与 Router 收纳规范细则.
- [references/templates/atomic-SKILL.md](references/templates/atomic-SKILL.md): 原子技能模板.
- [references/templates/router-SKILL.md](references/templates/router-SKILL.md): 路由父技能模板.
