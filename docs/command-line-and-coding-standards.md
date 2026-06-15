# 命令行问题复盘与代码编写规范

本文总结本项目开发中反复出现的命令行、环境、Git、编码和自动化问题，并把修正方式固化为后续代码编写规范。目标是减少本地运行失败、Git 推送冲突、Actions 失败和中文文档乱码。

## 一、已出现的问题与修正建议

### 1. 在错误目录执行命令

问题表现：

```powershell
fatal: not a git repository (or any of the parent directories): .git
```

典型原因：PowerShell 当前目录停留在 `C:\Windows\system32`，但 Git、Python 脚本和项目文件都在项目目录。

修正标准：

```powershell
cd "C:\Users\Administrator\Documents\New project 3"
git status --short --branch
```

后续规范：

1. 所有项目命令必须先确认 `Get-Location`。
2. 文档中的命令示例必须写出 `cd` 到项目目录。
3. 自动脚本不得假设当前目录正确，应优先基于项目根目录解析路径。

### 2. 把 Bash 语法直接粘到 PowerShell

问题表现：

```powershell
py - <<'PY'
```

PowerShell 会报重定向或语法错误，因为 `<<'PY'` 是 Bash heredoc，不是 PowerShell 语法。

修正标准：

PowerShell 中运行内联 Python 应使用 here-string：

```powershell
@'
print("OK")
'@ | py -
```

后续规范：

1. Windows 文档默认给 PowerShell 命令，不混用 Bash 语法。
2. 如必须给 Bash/WSL 命令，必须标注“WSL/Bash 使用”。
3. Python 内联命令优先写成脚本文件或 `@'...'@ | py -`。

### 3. `git add ...` 和 `git commit ...` 被当成真实参数

问题表现：

```powershell
fatal: pathspec '...' did not match any files
```

原因：`...` 在说明文本中表示省略，但在 Git 命令里会被当作真实 pathspec。

修正标准：

```powershell
git add README.md docs\api.md src\api\repository.py
git commit -m "feat: describe change"
```

后续规范：

1. 给用户的提交命令不能使用 `...`。
2. 如果文件较多，使用明确文件列表；只在确认安全时使用 `git add .`。
3. 提交前必须执行 `git status --short --branch`。

### 4. 远端被 GitHub Actions 更新导致 push rejected

问题表现：

```text
! [rejected] main -> main (fetch first)
```

原因：GitHub Actions 会把运行归档、推送状态或 Pages 产物提交到远端，导致本地 `main` 落后。

修正标准：

```powershell
git fetch origin
git rebase origin/main
git push origin main
```

若 rebase 冲突，先解决冲突，再：

```powershell
git add <resolved-files>
git rebase --continue
git push origin main
```

后续规范：

1. 提交前先 `git fetch origin`。
2. 推送失败先判断是否远端领先，不要强推。
3. 归档数据和运行数据优先放在独立归档分支，减少 `main` 冲突。
4. `docs/feed.xml`、`docs/index.md`、运行数据文件是高冲突文件，修改前后要重点检查。

### 5. rebase 时进入提交信息编辑器不知道如何退出

问题表现：终端显示提交信息模板，无法继续。

修正标准：

1. 如果是 Vim：按 `Esc`，输入 `:wq` 回车保存退出。
2. 如果要取消：按 `Esc`，输入 `:q!` 回车。

后续规范：

1. 优先使用非交互命令。
2. 需要继续 rebase 时，先确认冲突已解决并 `git add`。
3. 不在交互编辑器中修改无关内容。

### 6. 本地 Telegram 显示未配置

问题表现：

```text
telegram_sent=False
telegram_error=Telegram is not configured
```

原因：GitHub Actions Secrets 配好了，但本地 PowerShell 没有长期用户环境变量。

修正标准：

```powershell
[Environment]::SetEnvironmentVariable("TELEGRAM_BOT_TOKEN", "<token>", "User")
[Environment]::SetEnvironmentVariable("TELEGRAM_CHAT_ID", "<chat_id>", "User")
```

新开 PowerShell 后检查：

```powershell
[Environment]::GetEnvironmentVariable("TELEGRAM_BOT_TOKEN", "User")
[Environment]::GetEnvironmentVariable("TELEGRAM_CHAT_ID", "User")
```

后续规范：

1. 本地配置和 GitHub Actions Secrets 是两套环境。
2. 代码只能读取环境变量，不能写死 Token、Chat ID、Webhook。
3. 本地推送失败不能误判为 Git 权限问题。

### 7. Kimi API 配置存在模型参数和超时问题

问题表现：

```text
invalid temperature: only 1 is allowed for this model
Kimi API transient request error: The read operation timed out
```

原因：

1. 某些 Kimi 模型只接受特定参数，例如 `temperature=1`。
2. 请求超时过短或模型响应慢。

修正标准：

1. Kimi 调用必须读取 `KIMI_TIMEOUT_SECONDS`、`KIMI_MAX_RETRIES`、`KIMI_RETRY_SECONDS`。
2. 模型参数要兼容当前模型，不把固定参数散落在业务代码中。
3. Kimi 失败必须降级生成规则版周报，并在运行摘要中记录 `fallback_used` 和 `report_error`。

后续规范：

1. 外部 HTTP 请求必须有超时。
2. 模型调用失败不得阻断归档、Pages 构建和推送链接。
3. 运行摘要必须记录模型是否启用、是否降级和错误摘要。

### 8. GitHub Actions YAML 表达式写法不兼容

问题表现：workflow 文件提示某行 YAML syntax error。

常见原因：在 `env:` 里使用不兼容表达式或混用 secrets/vars fallback。

修正标准：

1. 复杂 fallback 优先放到 Python/脚本里处理。
2. workflow YAML 保持简单表达式。
3. 每次改 `.github/workflows/*.yml` 后运行对应测试，必要时用 GitHub Actions 页面验证。

后续规范：

1. workflow 只负责调度和传参。
2. 业务逻辑放入脚本，便于本地测试。
3. 新增 workflow 输入项要同步更新 README、setup 文档和测试。

### 9. `sqlite3` 命令不存在

问题表现：

```powershell
sqlite3 : 无法将“sqlite3”项识别为 cmdlet
```

原因：Windows 没有安装 SQLite CLI。

修正标准：

优先用 Python 标准库查询 SQLite：

```powershell
@'
import sqlite3
con = sqlite3.connect("data/github_weekly.sqlite")
for row in con.execute("select name from sqlite_master where type='table' order by name"):
    print(row[0])
con.close()
'@ | py -
```

后续规范：

1. 项目文档中的 SQLite 查询必须提供 Python 版本。
2. 不强制用户安装 sqlite3 CLI。
3. 后端 API 应提供常用数据库检查入口，减少手写 SQL。

### 10. 启动 Uvicorn 后终端被占用

问题表现：运行后终端一直停在：

```text
Uvicorn running on http://127.0.0.1:8000
```

这是正常状态，表示后端服务正在运行。

修正标准：

1. 查看页面时保持该终端运行。
2. 新开一个 PowerShell 执行 Git、测试或其他命令。
3. 停止服务按 `Ctrl+C`。

后续规范：

1. 文档中必须说明“服务型命令会占用当前终端”。
2. 长时间运行的服务不要和提交命令放在同一个终端流程里。

### 11. 中文文档乱码

问题表现：`operation-log.md` 或 README 显示乱码。

原因：

1. 终端编码和文件 UTF-8 编码不一致。
2. 使用错误工具重写中文文件。

修正标准：

1. Markdown 文件统一使用 UTF-8。
2. PowerShell 查看中文乱码时，不代表文件一定损坏，应先用编辑器或 GitHub 页面确认。
3. 手动修改文件优先使用补丁或编辑器，不用不明确编码的重定向重写整文件。

后续规范：

1. 中文文档只做局部补丁，不随意全文件重写。
2. 发现乱码先判断是显示问题还是文件内容损坏。
3. 操作日志保持倒序，最新记录放最上面。

### 12. WSL 与 Windows 环境混用

问题表现：

1. WSL 中没有 Windows 的 `~/.codex/AGENTS.md`。
2. 在 WSL 中误执行 Markdown 文件。
3. SSH keygen 路径输入错误。

修正标准：

1. Windows PowerShell 和 WSL 是两套 HOME、SSH、环境变量和 Codex 配置。
2. 迁移到 WSL 前要复制或软链接 `.codex/AGENTS.md`、skills、SSH key、Git config。
3. Markdown 文件只能阅读，不能直接当命令执行。

后续规范：

1. 当前项目默认继续用 PowerShell。
2. 如切换 WSL，必须单独做迁移清单，不在同一任务中混用两套环境。
3. 文档中的命令必须标注 PowerShell 或 WSL。

## 二、项目命令行规范

### 1. 标准本地检查顺序

每次开发前：

```powershell
cd "C:\Users\Administrator\Documents\New project 3"
Get-Location
git status --short --branch
git fetch origin
```

每次开发后：

```powershell
python -m unittest discover -q
python scripts\security_check.py
git diff --check
git status --short --branch
```

### 2. 标准提交顺序

```powershell
git status --short --branch
git add <明确文件列表>
git commit -m "feat: concise message"
git fetch origin
git rebase origin/main
git push origin main
```

如果 `git fetch` 后远端没有变化，可以直接 push；如果远端有变化，必须 rebase 后再 push。

### 3. 命令示例书写规则

1. Windows 默认写 PowerShell。
2. Bash/WSL 命令必须单独标注。
3. 不使用 `...` 作为可直接复制的命令参数。
4. 不把解释文字混入命令块。
5. 涉及密钥的命令使用占位符，不写真实值。
6. 命令块必须能复制执行。

## 三、代码编写规范

### 1. 路径规范

1. 业务代码使用 `Path` 和项目根目录解析路径。
2. 不依赖当前工作目录，除非命令文档已明确要求。
3. 生成物写入既有目录：周报进 `reports/`，运行摘要进 `data/runs/`，Pages 进 `docs/`。

### 2. 环境变量规范

1. 所有密钥只从环境变量或 GitHub Actions Secrets 读取。
2. 本地代码不得自动读取并提交 `.env`。
3. 缺少 Telegram 不阻断周报生成。
4. 缺少 Kimi 必须生成规则版周报。
5. 运行摘要必须记录配置缺失、降级和推送状态。

### 3. 外部请求规范

1. GitHub、Kimi、Telegram、飞书、企业微信请求必须设置超时。
2. 失败要返回结构化错误，不吞掉 partial errors。
3. 临时错误允许有限重试。
4. 任何外部服务失败都不应破坏本地归档。

### 4. GitHub Actions 规范

1. workflow 只做调度，复杂逻辑放脚本。
2. 每个新增 workflow 参数都要有默认值、文档和测试。
3. 自动归档数据优先写 `weekly-archive`，降低 `main` 冲突。
4. weekly 任务必须先测试和安全检查，再生成报告和发布归档。

### 5. 数据库/RAG 规范

1. SQLite 是可重建派生索引，事实来源仍是 JSON 归档。
2. 新增 SQLite 表必须同步更新：
   - `src/storage/schema.sql`
   - `src/storage/sqlite_store.py` 的安全白名单
   - `docs/data-contracts.md`
   - `tests/test_data_contracts.py`
3. 新增 RAG 能力必须有只读查询入口或受控写入入口。
4. 写入型 API 必须有确认字段或明确用途，避免误触发推送、模型调用或批量任务。

### 6. 前端/API 规范

1. `/v1/*` 是 JSON API，不是 HTML 页面。
2. HTML 页面应通过 `admin.html?api=1`、`project.html?repo=...&api=1` 等入口读取 API。
3. 静态 GitHub Pages 必须能回退到公开 JSON，不依赖本地后端。
4. 页面按钮涉及写库或推送时，应明确区分“预览”和“确认执行”。

### 7. 测试规范

核心变更至少运行：

```powershell
python -m unittest discover -q
python scripts\security_check.py
git diff --check
```

如果只改局部，可先运行针对性测试，但提交前必须跑全量测试和安全检查。

### 8. 文档规范

1. 项目文档默认中文。
2. 操作日志倒序排列，最新记录放最上面。
3. README 只保留用户需要的入口和核心能力，不塞入临时排错长日志。
4. 复杂排错沉淀到独立文档，再在 README 放链接。

## 四、后续落地建议

1. 后续新增脚本时，优先提供 PowerShell 示例和 Python 标准库替代方案。
2. 为常用本地检查补一个统一脚本，例如 `scripts/local_check.py`，统一运行测试、安全检查和关键数据检查。
3. 为本地环境变量补一个只检查不泄密的脚本，输出“已配置/缺失/长度”，不输出真实值。
4. 持续把命令行坑点写入本文档，不把临时聊天内容当作长期规范。
