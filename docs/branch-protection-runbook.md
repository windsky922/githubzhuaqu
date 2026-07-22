# main 分支保护操作手册

仓库管理员在 P1 本地改动推送、CI 三项 job 成功后，在 GitHub 的 **Settings → Branches → main** 启用规则：必须 Pull Request、至少 1 次审批、禁止直接推送，并要求以下 status checks：

- `核心质量检查`
- `Playwright mock 浏览器回归`
- `Playwright 真实 FastAPI 回归`

启用后应创建一个缺少任一检查的测试 PR，确认不能合并；再创建三项成功的 PR，确认可合并。管理员紧急恢复须记录原因、时间和后续复盘，不能以直接 push 代替正常流程。
