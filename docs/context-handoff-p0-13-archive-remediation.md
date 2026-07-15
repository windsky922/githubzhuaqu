# P0-13 公开归档修复发布交接

## 任务

- 目标与完成定义：把已提交的公开 JSON 字段投影实际应用到 `weekly-archive` 最新 tree；不运行正常 weekly 采集或任何通知外发，并以远端 tree 和 Pages smoke 证明最新公开视图已修复。

## 已确认事实

- 当前代码提交：`main` / `origin/main` 为 `e609c98a21a38fead3d0fce6c4686855ac6f592a`。
- 修复发布 workflow：`.github/workflows/archive-remediation.yml`，仅 `workflow_dispatch` 且必须传入 `confirm_public_archive_release=true`；无 schedule、Kimi、Telegram、Webhook 或通知发送步骤。
- 已授权并实际执行 run [`29406619346`](https://github.com/windsky922/githubzhuaqu/actions/runs/29406619346)，所有步骤成功：恢复既有公开数据、重建 Pages、发布字段投影、远端 tree attestation。
- 独立只读复核：`weekly-archive` HEAD 为 `a9447d3259f40a06111824f6105144252233847e`，最新 tree 共 154 个文件，禁止路径为 0。
- Pages API URL 为 `https://windsky922.github.io/githubzhuaqu/`；根路径返回重定向，`projects.json` 返回 HTTP 200。

## 已完成

1. P0-11A：路径 allowlist、删除旧 tree 残留和 SQLite/WAL/SHM 拒绝。
2. P0-12：远端 tree path-only attestation 和历史路径枚举能力。
3. P0-11B：Ask/SSE provider 草稿先校验再输出。
4. P0-11C：公开 JSON 字段级投影，未知字段和运行态字段不发布。
5. P0-13：独立受控修复发布通道已实际运行，最新公开 tree 已通过 attestation。

## 未完成与阻塞

- 历史提交中的 SQLite 或运行态数据仍未做内容级取证；最新 tree 清理不删除 Git 历史、fork 或外部缓存。
- 未获授权前，不下载、打印、保存或分析历史 SQLite/blob 内容；不改写 `weekly-archive` 历史。
- 公开报告、README 摘要等允许字段仍不是通用脱敏承诺；字段投影和 staged-tree 敏感标记扫描只降低已知应用运行态泄露面。

- 下一步动作：先确定 P0-1 历史取证的授权范围。推荐仅做路径、文件哈希、SQLite magic、表/列名和脱敏行数统计；输出不得包含 query、note、token、payload 或原始用户内容。取证结论后，再由用户决定是否进行历史重写、缓存清理或凭据轮换。
- 已尝试但无效的方法（勿重复）：不要用本地损坏 loose object 直接 fetch/checkout `weekly-archive`，也不要删除对象或强制 Git 清理；远端 GitHub tree API 已足以完成最新 tree 路径验证。

## 范围与安全

- 不改变 Ask/SSE 契约、无状态追问、管理鉴权、真实外发确认、模型配置或检索权重。
- `tmp/` 必须保持未跟踪、不得暂存。
- 后续修改仍先更新 `docs/operation-log.md` 顶部；完成后执行完整前端、双 Playwright、Python、安全、四套评估、`git diff --check` 和 `docs/app` 一致性检查。
- 关键路径：`.github/workflows/archive-remediation.yml`、`scripts/publish_archive_branch.py`、`scripts/audit_public_archive.py`、`src/public_archive.py`、`tests/test_workflows.py`。
