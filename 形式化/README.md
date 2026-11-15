# 形式化 (`FilterFormalization`)

本模块用于仓库中滤波理论（非线性滤波、贝叶斯推前/拉回与核复合、最优输运滤波等）相关定义与定理的 Lean 4 形式化验证。

## 环境与依赖

- **Toolchain**: `leanprover/lean4:v4.36.0-rc2`（见 [`lean-toolchain`](lean-toolchain)）
- **数学库**: `mathlib4` `v4.36.0-rc2`（由 Lake 管理，源码与预编译缓存位于 `.lake/packages/mathlib`，可直接本地检索如 `Mathlib/Probability/Kernel/Posterior.lean`）
- **MCP 服务**: `lean-lsp-mcp`（通过 `uvx lean-lsp-mcp` 启动，已接入本机 Antigravity MCP 配置）

## 常用命令

在 `形式化/` 目录下执行：

```bash
# 拉取 mathlib 预编译缓存（切分支或更新依赖后执行，切勿裸编译 mathlib）
lake exe cache get

# 构建当前形式化工程
lake build
```

## MCP 配置参考

本机 Antigravity 配置（`~/.gemini/config/mcp_config.json` 与 `~/.gemini/antigravity/mcp_config.json`）已注册 `lean-lsp` 服务：

```json
{
  "lean-lsp": {
    "command": "/home/wudizhe001/.local/bin/uvx",
    "args": [
      "lean-lsp-mcp",
      "--lean-project-path",
      "/home/wudizhe001/Documents/GitHub/filter-theory-study/形式化"
    ],
    "env": {
      "LEAN_PROJECT_PATH": "/home/wudizhe001/Documents/GitHub/filter-theory-study/形式化",
      "PATH": "/home/wudizhe001/.elan/bin:/home/wudizhe001/.local/bin:/usr/local/bin:/usr/bin:/bin"
    }
  }
}
```
