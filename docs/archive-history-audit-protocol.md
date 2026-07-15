# 公开归档历史脱敏取证协议

## 目的

`scripts/audit_public_archive_content.py` 用于确认历史公开数据库的结构性暴露范围。它不替代最新 tree 的路径 attestation，也不执行历史改写、缓存清理、凭据轮换或用户通知。

## 运行级别

- `--dry-run`：只输出提交、数据库路径、blob SHA 和计数；不下载数据库内容。
- `--confirm-structure-scan`：需要本机已有 `GITHUB_TOKEN`，把每个 blob 写入系统临时目录后只读取 SQLite magic、表名、列名、行数和已规范化的时间范围。原始副本随单个检查结束删除。

结构扫描只把脱敏 JSON 写入 `tmp/archive-audit/<run-id>/summary.json`。报告目录必须位于 `tmp/`；不得提交、发布或复制到 `weekly-archive`。运行输出、报告和异常不得包含业务字段值、SQL、query、note、token、payload、错误原文或用户内容。

## 报告与处置门

报告包含 blob SHA、路径、首次/最后出现提交、SQLite magic、表/列名、行数、时间范围及按字段名推导的风险类别。风险类别只说明结构性可能性，不证明某个字段一定含敏感值。

完成结构扫描后，仅把聚合结论写入 `docs/operation-log.md`。是否历史重写、缓存清理、凭据轮换或通知，必须由用户基于脱敏结果单独授权；默认不执行。
