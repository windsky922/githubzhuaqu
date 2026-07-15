# P0-1 历史公开归档脱敏取证交接

## 任务

- 当前唯一活动任务：为历史 `weekly-archive` 数据库建立可复现、无原文输出的结构取证工具。
- 目标与完成定义：工具经本地与 CI 验证后，才可在用户单独授权下扫描历史数据库结构并生成私有脱敏统计。
- 当前步骤：实现完成，未执行 `--confirm-structure-scan`。

## 已确认事实

- 最新 `weekly-archive` 已由 P0-13 修复发布：远端 tree 禁止路径为 0；该事实不代表历史 commit、fork 或缓存已清理。
- `scripts/audit_public_archive_content.py` 与现有路径 attestation 分离。`--dry-run` 仅枚举元数据；`--confirm-structure-scan` 才允许下载 blob。
- 结构扫描只保留 SQLite magic、SHA、提交范围、表/列名、行数、规范化时间范围和风险类别；不输出业务字段值、SQL、原始错误或用户内容。

## 已完成

- 新增历史内容审计器、假 GitHub API/临时 SQLite 回归和敏感 canary 输出保护。
- 新增 `docs/archive-history-audit-protocol.md`，限定报告只能写入 `tmp/archive-audit/<run-id>/summary.json`。
- 完整前端、双 Playwright、Python、安全和四套评估验证均通过。

## 未完成与阻塞

- 尚未下载任何历史 SQLite/blob，尚无真实结构扫描报告。
- 真实扫描需要用户单独授权联网读取，以及本机已有 `GITHUB_TOKEN`；缺失时工具在下载前失败，不应要求用户提供凭据值。
- 历史重写、缓存清理、凭据轮换和通知均未授权，默认不执行。

- 下一步动作：CI 通过后，向用户请求一次性授权运行 `--confirm-structure-scan`；仅展示 `tmp/` 中报告的脱敏统计，再等待历史处置决定。
- 已尝试但无效的方法（勿重复）：不要借助本地损坏 loose object fetch/checkout 历史，也不要删除 Git 对象或强制清理；审计器使用 GitHub API 和临时副本。

## 范围与安全

- 当前项目/目录：`C:\Users\Administrator\Documents\New project 3`；`tmp/` 始终未跟踪、不提交。
- 不可执行的动作：不改写 `weekly-archive` 历史，不输出/保存 query、note、token、payload 或原始用户内容，不改变 Ask/SSE、检索权重或外发确认。
- 敏感数据：历史数据库可能含运行态数据；本阶段仅使用测试 canary，未接触真实 blob。
