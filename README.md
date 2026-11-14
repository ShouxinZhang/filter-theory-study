# 像素农场 Pixel Farm

前后端分离的像素风农场游戏：Phaser 3 + TypeScript + Vite 前端，Firebase（Auth + Firestore + Cloud Functions + Hosting）后端。

## 架构
- `functions/src/logic.ts` — **唯一的游戏规则源**（纯函数）。前端用它显示倒计时、跑本地模式；云函数用它做权威校验。
- `functions/src/index.ts` — 可调用云函数 `ensurePlayer / buySeed / plant / harvest / sell`，在 Firestore 事务里用**服务器时间**执行规则。
- `firestore.rules` — 玩家只能读自己的存档，客户端**禁止任何写入**（防作弊）。
- `web/` — 前端。像素图全部由代码绘制（`src/sprites.ts`），无外部素材。

## 开发
```bash
cd web && npm run dev            # 无 Firebase 配置时自动用本地模式（localStorage）
cd functions && npm test         # 规则单元测试
# 端到端测试（需要 JDK 21+）
npx firebase emulators:exec --only auth,firestore,functions --project demo-pixel-farm "node web/scripts/emulator-smoke.mjs"
```

## 部署（Firebase）
1. 在 Firebase 控制台创建项目，升级 Blaze 套餐（云函数需要），启用 Authentication 里的 **Google** 和 **匿名** 登录，创建 Firestore 数据库。
2. 在项目设置中添加 Web 应用，把配置写入 `web/.env.production.local`：
   ```
   VITE_FIREBASE_API_KEY=...
   VITE_FIREBASE_AUTH_DOMAIN=<project>.firebaseapp.com
   VITE_FIREBASE_PROJECT_ID=<project>
   VITE_FIREBASE_APP_ID=...
   ```
3. `npx firebase deploy --project <project>`
