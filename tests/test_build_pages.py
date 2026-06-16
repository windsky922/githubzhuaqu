import json
import shutil
import unittest
import uuid
from pathlib import Path

from scripts.build_pages import build_pages


class BuildPagesTest(unittest.TestCase):
    def test_builds_index_and_weekly_report_pages(self):
        root = Path.cwd() / f".tmp-pages-test-{uuid.uuid4().hex}"
        try:
            (root / "reports").mkdir(parents=True)
            (root / "data" / "runs").mkdir(parents=True)
            (root / "data" / "trends").mkdir(parents=True)
            (root / "data" / "selected").mkdir(parents=True)
            (root / "reports" / "2026-04-28.md").write_text("# 周报", encoding="utf-8")
            (root / "data" / "runs" / "2026-04-28.json").write_text(
                json.dumps(
                    {
                        "selected_count": 10,
                        "collected_count": 100,
                        "kimi_used": True,
                        "telegram_sent": True,
                        "telegram_runs_url": "https://example.com/runs.html",
                        "collector_stats": [
                            {
                                "source": "github_search",
                                "query": "topic:ai",
                                "stage": "github_search",
                                "status": "failed",
                                "count": 0,
                                "error": "GitHub API error 403: API rate limit exceeded",
                                "error_kind": "rate_limited",
                                "status_code": 403,
                                "rate_limit_remaining": "0",
                                "rate_limit_reset": "1777777777",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (root / "data" / "trends" / "2026-04-28.json").write_text(
                json.dumps(
                    {
                        "summary_points": ["Python 是本期主要语言。"],
                        "top_languages": [{"name": "Python", "count": 8}],
                        "top_categories": [{"name": "AI Agent", "count": 4}],
                        "total_star_growth": 20,
                        "trending_project_count": 1,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (root / "data" / "selected" / "2026-04-28.json").write_text(
                json.dumps(
                    [
                        {
                            "full_name": "owner/project",
                            "html_url": "https://github.com/owner/project",
                            "description": "desc",
                            "readme_summary": "这是一个简短 README 摘要。",
                            "category": "AI Agent",
                            "language": "Python",
                            "stargazers_count": 100,
                            "star_growth": 20,
                            "sources": ["github_trending", "github_search"],
                            "trending_rank": 2,
                            "security_flags": ["未识别到许可证。"],
                            "security_score": 85,
                            "security_level": "medium",
                            "quality_flags": ["README 摘要不足"],
                            "quality_score": 82,
                            "quality_level": "high",
                        }
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            written = build_pages(root)

            self.assertIn(root / "docs" / "index.md", written)
            self.assertIn(root / "docs" / "projects.md", written)
            self.assertIn(root / "docs" / "admin.html", written)
            self.assertIn(root / "docs" / "explorer.html", written)
            self.assertIn(root / "docs" / "recommendations.html", written)
            self.assertIn(root / "docs" / "subscriptions.html", written)
            self.assertIn(root / "docs" / "compare.html", written)
            self.assertIn(root / "docs" / "project.html", written)
            self.assertIn(root / "docs" / "runs.html", written)
            self.assertIn(root / "docs" / "jobs.html", written)
            self.assertIn(root / "docs" / "job.html", written)
            self.assertIn(root / "docs" / "projects.json", written)
            self.assertIn(root / "docs" / "runs.json", written)
            self.assertIn(root / "docs" / "jobs.json", written)
            self.assertIn(root / "docs" / "profiles.json", written)
            self.assertIn(root / "docs" / "profiles.html", written)
            self.assertIn(root / "docs" / "feed.xml", written)
            self.assertIn(root / "docs" / "weekly" / "2026-04-28.html", written)
            weekly_html = (root / "docs" / "weekly" / "2026-04-28.html").read_text(encoding="utf-8")
            self.assertIn("<!doctype html>", weekly_html)
            self.assertIn("GitHub 周报 2026-04-28", weekly_html)
            self.assertEqual((root / "docs" / "weekly" / "2026-04-28.md").read_text(encoding="utf-8"), "# 周报")
            index = (root / "docs" / "index.md").read_text(encoding="utf-8")
            self.assertIn("[个性化推荐页](recommendations.html)", index)
            self.assertIn("[订阅配置页](subscriptions.html)", index)
            self.assertIn("[2026-04-28](weekly/2026-04-28.html)", index)
            self.assertIn("10 个项目", index)
            self.assertIn("最新运行摘要", index)
            self.assertIn("采集候选：100 个", index)
            self.assertIn("Python 是本期主要语言。", index)
            self.assertIn("主语言 Python", index)
            self.assertIn("主方向 AI Agent", index)
            self.assertIn("新增 Star 20", index)
            self.assertIn("Trending 项目 1", index)
            self.assertIn("[本地管理首页](admin.html)", index)
            self.assertIn("[项目筛选页](explorer.html)", index)
            self.assertIn("[项目详情页](project.html)", index)
            self.assertIn("[项目对比页](compare.html)", index)
            self.assertIn("[运行状态面板](runs.html)", index)
            self.assertIn("[任务状态面板](jobs.html)", index)
            self.assertIn("[历史项目索引](projects.html)", index)
            self.assertIn("[公共项目 JSON](projects.json)", index)
            self.assertIn("[公共运行 JSON](runs.json)", index)
            self.assertIn("[公共任务 JSON](jobs.json)", index)
            self.assertIn("[个性化方向页](profiles.html)", index)
            self.assertIn("[个性化方向 JSON](profiles.json)", index)
            self.assertIn("[RSS 订阅](feed.xml)", index)
            self.assertIn("[后端 API 说明](api.html)", index)
            self.assertIn("[历史归档查询说明](archive-query.html)", index)
            self.assertIn("[数据契约说明](data-contracts.html)", index)
            self.assertIn("[未来更新规划](future-plan.html)", index)
            projects = (root / "docs" / "projects.md").read_text(encoding="utf-8")
            self.assertIn("owner/project", projects)
            self.assertIn("GitHub Trending + GitHub Search", projects)
            self.assertIn("| 2 |", projects)
            self.assertIn("AI Agent", projects)
            self.assertIn("[https://github.com/owner/project](https://github.com/owner/project)", projects)
            projects_json = json.loads((root / "docs" / "projects.json").read_text(encoding="utf-8"))
            self.assertEqual(projects_json["schema_version"], 1)
            self.assertEqual(projects_json["count"], 1)
            self.assertEqual(projects_json["projects"][0]["full_name"], "owner/project")
            self.assertEqual(projects_json["projects"][0]["report_url"], "weekly/2026-04-28.html")
            self.assertEqual(projects_json["projects"][0]["readme_summary"], "这是一个简短 README 摘要。")
            self.assertIn("security_flags", projects_json["projects"][0])
            self.assertEqual(projects_json["projects"][0]["security_score"], 85)
            self.assertEqual(projects_json["projects"][0]["security_level"], "medium")
            self.assertEqual(projects_json["projects"][0]["quality_flags"], ["README 摘要不足"])
            self.assertEqual(projects_json["projects"][0]["quality_score"], 82)
            self.assertEqual(projects_json["projects"][0]["quality_level"], "high")
            runs_json = json.loads((root / "docs" / "runs.json").read_text(encoding="utf-8"))
            self.assertEqual(runs_json["schema_version"], 1)
            self.assertEqual(runs_json["count"], 1)
            self.assertEqual(runs_json["runs"][0]["run_date"], "2026-04-28")
            self.assertTrue(runs_json["runs"][0]["telegram_sent"])
            self.assertEqual(runs_json["runs"][0]["delivery_results"], [])
            self.assertEqual(runs_json["runs"][0]["collector_failed_count"], 1)
            self.assertEqual(runs_json["runs"][0]["collector_error_kinds"], ["rate_limited"])
            self.assertEqual(runs_json["runs"][0]["collector_error_summary"][0]["status_code"], 403)
            self.assertEqual(runs_json["runs"][0]["telegram_runs_url"], "https://example.com/runs.html")
            self.assertEqual(runs_json["runs"][0]["top_languages"][0]["name"], "Python")
            jobs_json = json.loads((root / "docs" / "jobs.json").read_text(encoding="utf-8"))
            self.assertEqual(jobs_json["schema_version"], 1)
            self.assertEqual(jobs_json["count"], 1)
            self.assertEqual(jobs_json["jobs"][0]["job_id"], "run:2026-04-28")
            self.assertEqual(jobs_json["jobs"][0]["status"], "succeeded")
            self.assertEqual(jobs_json["jobs"][0]["result"]["selected_count"], 10)
            admin_page = (root / "docs" / "admin.html").read_text(encoding="utf-8")
            self.assertIn("recommendations.html", admin_page)
            self.assertIn("GitHub 周报本地管理首页", admin_page)
            self.assertIn("loadHealth", admin_page)
            self.assertIn("loadOverview", admin_page)
            self.assertIn("loadDatabaseInsights", admin_page)
            self.assertIn("setupCorpusSearch", admin_page)
            self.assertIn("setupRagSearch", admin_page)
            self.assertIn("setupRagBackfill", admin_page)
            self.assertIn("/v1/database/summary", admin_page)
            self.assertIn("/v1/database/facets?limit=6", admin_page)
            self.assertIn("/v1/database/trends?limit=8", admin_page)
            self.assertIn("/v1/search?", admin_page)
            self.assertIn("/v1/rag/retrieve", admin_page)
            self.assertIn("/v1/rag/vector-search", admin_page)
            self.assertIn("/v1/rag/ask", admin_page)
            self.assertIn("/v1/rag/backfill-explanations", admin_page)
            self.assertIn("ragBackfillHtml", admin_page)
            self.assertIn("setupCreateTask", admin_page)
            self.assertIn("createPlannedTask", admin_page)
            self.assertIn("bindWorkbenchFilters", admin_page)
            self.assertIn("renderJobWorkbench", admin_page)
            self.assertIn("filteredWorkbenchJobs", admin_page)
            self.assertIn("loadAdminJobs", admin_page)
            self.assertIn("loadAdminJobsJson", admin_page)
            self.assertIn("handleWorkbenchAction", admin_page)
            self.assertIn("runWorkbenchPrecheck", admin_page)
            self.assertIn("runWorkbenchExecution", admin_page)
            self.assertIn("runWorkbenchRetry", admin_page)
            self.assertIn("latestJobResult", admin_page)
            self.assertIn("latestJobResultHtml", admin_page)
            self.assertIn("jobNextAction", admin_page)
            self.assertIn("statusClass", admin_page)
            self.assertIn("workflowBoard", admin_page)
            self.assertIn("workflowBoardHtml", admin_page)
            self.assertIn("workflowCard", admin_page)
            self.assertIn("topProjects", admin_page)
            self.assertIn("projectDetailUrl", admin_page)
            self.assertIn('fetch("/v1/health"', admin_page)
            self.assertIn('fetch("/v1/jobs?limit=200"', admin_page)
            self.assertIn('fetch("/v1/runs/trigger"', admin_page)
            self.assertIn('fetch("projects.json"', admin_page)
            self.assertIn('fetch("runs.json"', admin_page)
            self.assertIn('fetch("jobs.json"', admin_page)
            self.assertIn('id="ragQuery"', admin_page)
            self.assertIn('id="ragMode"', admin_page)
            self.assertIn('value="ask"', admin_page)
            self.assertIn('id="runRagSearch"', admin_page)
            self.assertIn('id="devContextQuery"', admin_page)
            self.assertIn('id="indexDevContext"', admin_page)
            self.assertIn('id="runDevContextSearch"', admin_page)
            self.assertIn('id="ragQualitySummary"', admin_page)
            self.assertIn('id="ragEvaluationTrends"', admin_page)
            self.assertIn("RAG 回答", admin_page)
            self.assertIn("下一步动作", admin_page)
            self.assertIn("Prompt Context", admin_page)
            self.assertIn("/v1/rag/diagnostics?limit=5", admin_page)
            self.assertIn("/v1/rag/quality-summary?limit=5", admin_page)
            self.assertIn("/v1/rag/search-evaluation-trends?limit=8", admin_page)
            self.assertIn("/v1/feedback?limit=200", admin_page)
            self.assertIn("/v1/dev-context/index", admin_page)
            self.assertIn("/v1/dev-context/search?", admin_page)
            self.assertIn("setupDevContext", admin_page)
            self.assertIn("indexDevContext", admin_page)
            self.assertIn("runDevContextSearch", admin_page)
            self.assertIn("devContextSearchHtml", admin_page)
            self.assertIn("feedbackSummaryHtml", admin_page)
            self.assertIn('id="feedbackSummary"', admin_page)
            self.assertIn("ragDiagnosticsHtml", admin_page)
            self.assertIn("ragEvaluationTrendsHtml", admin_page)
            self.assertIn("ragMaintenancePlanHtml", admin_page)
            self.assertIn("/v1/rag/maintenance-plan", admin_page)
            self.assertIn('id="planRagMaintenance"', admin_page)
            self.assertIn("ragQualitySummaryHtml", admin_page)
            self.assertIn("RAG 诊断", admin_page)
            self.assertIn("RAG 质量概览", admin_page)
            self.assertIn("RAG 检索评估趋势", admin_page)
            self.assertIn('id="taskProfile"', admin_page)
            self.assertIn('id="taskDaysBack"', admin_page)
            self.assertIn('id="taskSource"', admin_page)
            self.assertIn('id="taskPreviewMode"', admin_page)
            self.assertIn('id="taskDeliveryMode"', admin_page)
            self.assertIn('name="taskDeliveryMode"', admin_page)
            self.assertIn("预览，不推送", admin_page)
            self.assertIn('id="createTask"', admin_page)
            self.assertIn('id="jobWorkbench"', admin_page)
            self.assertIn('data-job-filter="attention"', admin_page)
            self.assertIn('data-job-filter="failed"', admin_page)
            self.assertIn('data-job-filter="planned"', admin_page)
            self.assertIn("任务工作台", admin_page)
            self.assertIn("shouldUseApi", admin_page)
            self.assertIn("healthHtml", admin_page)
            self.assertIn("latestLinksHtml", admin_page)
            self.assertIn('trigger_source: "admin_page"', admin_page)
            self.assertIn('requested_by: "local-admin"', admin_page)
            self.assertIn('requested_by: "admin_page"', admin_page)
            self.assertIn("/v1/job-execution-check?job_id=", admin_page)
            self.assertIn("/v1/jobs/${encodeURIComponent(jobId)}/execute", admin_page)
            self.assertIn("/v1/jobs/${encodeURIComponent(jobId)}/retry", admin_page)
            self.assertIn("confirm_execution: true", admin_page)
            self.assertIn("data-admin-action=\"precheck\"", admin_page)
            self.assertIn("data-admin-action=\"execute\"", admin_page)
            self.assertIn("data-admin-action=\"retry\"", admin_page)
            self.assertIn("打开任务详情", admin_page)
            self.assertIn("执行前检查", admin_page)
            self.assertIn("确认执行", admin_page)
            self.assertIn("重试", admin_page)
            self.assertIn("项目总数", admin_page)
            self.assertIn("最近任务结果", admin_page)
            self.assertIn("下一步", admin_page)
            self.assertIn("错误", admin_page)
            self.assertIn("打开周报", admin_page)
            self.assertIn("核心工作流", admin_page)
            self.assertIn("最近周报", admin_page)
            self.assertIn("Top 项目", admin_page)
            self.assertIn("查看项目", admin_page)
            self.assertIn("最新运行", admin_page)
            self.assertIn("失败任务", admin_page)
            self.assertIn("待执行任务", admin_page)
            self.assertIn("处理失败任务", admin_page)
            self.assertIn("查看待执行任务", admin_page)
            self.assertIn("项目筛选", admin_page)
            self.assertIn("运行状态", admin_page)
            self.assertIn("任务状态", admin_page)
            self.assertIn("任务详情", admin_page)
            jobs_page = (root / "docs" / "jobs.html").read_text(encoding="utf-8")
            self.assertIn("GitHub 周报任务状态", jobs_page)
            self.assertIn('value="rag_corpus_rebuild"', jobs_page)
            self.assertIn('value="rag_embedding_build"', jobs_page)
            self.assertIn('fetch("/v1/jobs?limit=200"', jobs_page)
            self.assertIn('fetch("jobs.json"', jobs_page)
            self.assertIn("loadJobs", jobs_page)
            self.assertIn("shouldUseApi", jobs_page)
            self.assertIn("创建 planned 任务", jobs_page)
            self.assertIn('id="createTask"', jobs_page)
            self.assertIn('id="createPreviewMode"', jobs_page)
            self.assertIn('id="createDeliveryMode"', jobs_page)
            self.assertIn('name="createDeliveryMode"', jobs_page)
            self.assertIn("setupCreateTask", jobs_page)
            self.assertIn("createPlannedTask", jobs_page)
            self.assertIn('fetch("/v1/runs/trigger"', jobs_page)
            self.assertIn("runExecutionCheck", jobs_page)
            self.assertIn("precheckHtml", jobs_page)
            self.assertIn("runJobExecution", jobs_page)
            self.assertIn("executionHtml", jobs_page)
            self.assertIn("runJobRetry", jobs_page)
            self.assertIn("retryHtml", jobs_page)
            self.assertIn("jobDetailUrl", jobs_page)
            self.assertIn("job.html?", jobs_page)
            self.assertIn("data-precheck", jobs_page)
            self.assertIn("data-execute", jobs_page)
            self.assertIn("data-retry", jobs_page)
            self.assertIn("precheck-result", jobs_page)
            self.assertIn("confirm_execution: true", jobs_page)
            self.assertIn("/v1/job-execution-check?job_id=", jobs_page)
            self.assertIn("/v1/jobs/${encodeURIComponent(jobId)}/execute", jobs_page)
            self.assertIn("/v1/jobs/${encodeURIComponent(jobId)}/retry", jobs_page)
            self.assertIn("next_command", jobs_page)
            self.assertIn('trigger_source: "jobs_page"', jobs_page)
            self.assertIn('requested_by: "local-ui"', jobs_page)
            self.assertIn('requested_by: "jobs_page"', jobs_page)
            self.assertIn('params.get("api") === "1"', jobs_page)
            self.assertIn('params.set("api", apiMode)', jobs_page)
            self.assertIn('params.set(key === "query" ? "q" : key, control.value)', jobs_page)
            self.assertIn('profile !== controls.profile.value.trim().toLowerCase()', jobs_page)
            self.assertIn("planned", jobs_page)
            job_page = (root / "docs" / "job.html").read_text(encoding="utf-8")
            self.assertIn("GitHub 周报任务详情", job_page)
            self.assertIn("loadEvents", job_page)
            self.assertIn("loadJobFromJson", job_page)
            self.assertIn("eventsHtml", job_page)
            self.assertIn("operationHtml", job_page)
            self.assertIn("bindOperationControls", job_page)
            self.assertIn("runDetailPrecheck", job_page)
            self.assertIn("runDetailExecution", job_page)
            self.assertIn("runDetailRetry", job_page)
            self.assertIn("precheckHtml", job_page)
            self.assertIn("executionHtml", job_page)
            self.assertIn("retryHtml", job_page)
            self.assertIn("ragResultSummaryHtml", job_page)
            self.assertIn("countDelta", job_page)
            self.assertIn("before_counts", job_page)
            self.assertIn("after_counts", job_page)
            self.assertIn("processed_repositories", job_page)
            self.assertIn('id="precheckButton"', job_page)
            self.assertIn('id="executeButton"', job_page)
            self.assertIn('id="retryButton"', job_page)
            self.assertIn('requested_by: "job_detail_page"', job_page)
            self.assertIn("jobs.json", job_page)
            self.assertIn("/v1/jobs/${encodeURIComponent(id)}", job_page)
            self.assertIn("/v1/jobs/${encodeURIComponent(id)}/events?limit=200", job_page)
            self.assertIn("/v1/job-execution-check?job_id=${encodeURIComponent(jobId)}", job_page)
            self.assertIn("/v1/jobs/${encodeURIComponent(jobId)}/execute", job_page)
            self.assertIn("/v1/jobs/${encodeURIComponent(jobId)}/retry", job_page)
            self.assertIn("URL 缺少 job 参数", job_page)
            profiles_json = json.loads((root / "docs" / "profiles.json").read_text(encoding="utf-8"))
            self.assertEqual(profiles_json["schema_version"], 1)
            self.assertEqual(profiles_json["count"], 0)
            profiles_page = (root / "docs" / "profiles.html").read_text(encoding="utf-8")
            self.assertIn("个性化方向", profiles_page)
            self.assertIn('fetch("profiles.json"', profiles_page)
            self.assertIn("查看匹配项目", profiles_page)
            self.assertIn("explorer.html?profile=", profiles_page)
            explorer = (root / "docs" / "explorer.html").read_text(encoding="utf-8")
            self.assertIn("GitHub 热点项目筛选", explorer)
            self.assertIn('fetch("/api/projects?limit=200&sort=recent"', explorer)
            self.assertIn('fetch("/api/profiles"', explorer)
            self.assertIn('fetch("projects.json"', explorer)
            self.assertIn('fetch("profiles.json"', explorer)
            self.assertIn("loadProjects", explorer)
            self.assertIn("shouldUseApi", explorer)
            self.assertIn('params.get("api") === "1"', explorer)
            self.assertIn('params.set("api", apiMode)', explorer)
            self.assertIn("来源：${source}", explorer)
            self.assertIn('id="runDate"', explorer)
            self.assertIn('id="language"', explorer)
            self.assertIn('id="profile"', explorer)
            self.assertIn('id="category"', explorer)
            self.assertIn('id="share"', explorer)
            self.assertIn("restoreFiltersFromUrl", explorer)
            self.assertIn("updateUrl", explorer)
            self.assertIn("summaryHtml", explorer)
            self.assertIn("matchesProfile", explorer)
            self.assertIn("securityText", explorer)
            self.assertIn("detailPanel", explorer)
            self.assertIn("toggleDetails", explorer)
            self.assertIn('id="qualityLevel"', explorer)
            self.assertIn("平均质量分", explorer)
            self.assertIn("质量信号", explorer)
            self.assertIn("qualityText", explorer)
            self.assertIn("quality_score", explorer)
            self.assertIn('id="profileShortcuts"', explorer)
            self.assertIn("renderProfileShortcuts", explorer)
            self.assertIn("data-profile", explorer)
            self.assertIn("README 摘要", explorer)
            self.assertIn("相似项目", explorer)
            self.assertIn("similarProjects", explorer)
            self.assertIn("similarityScore", explorer)
            self.assertIn("projectKeywords", explorer)
            self.assertIn("projectDetailUrl", explorer)
            self.assertIn('params.set("repo", repo)', explorer)
            self.assertIn('<td class="repo"><a href="${escapeAttribute(projectDetailUrl(project))}">', explorer)
            self.assertIn("compareUrl([project.full_name])", explorer)
            recommendations = (root / "docs" / "recommendations.html").read_text(encoding="utf-8")
            self.assertIn("GitHub 个性化推荐", recommendations)
            self.assertIn("subscriptions.html", recommendations)
            self.assertIn('fetch(`/v1/recommendations?', recommendations)
            self.assertIn('fetch("projects.json"', recommendations)
            self.assertIn('id="profileButtons"', recommendations)
            self.assertIn("quickProfiles", recommendations)
            self.assertIn("agent_development", recommendations)
            self.assertIn("recommendationRows", recommendations)
            self.assertIn("submitRecommendationFeedback", recommendations)
            self.assertIn('fetch("/v1/feedback"', recommendations)
            self.assertIn("feedback_memory", recommendations)
            self.assertIn("preference_score", recommendations)
            self.assertIn("adminWriteHeaders", recommendations)
            self.assertIn("project.html?", recommendations)
            self.assertIn("项目详情", recommendations)
            self.assertIn("加入对比", recommendations)
            self.assertIn("compare.html?", recommendations)
            compare_page = (root / "docs" / "compare.html").read_text(encoding="utf-8")
            self.assertIn("GitHub 项目对比", compare_page)
            self.assertIn('fetch(`/v1/projects/compare?${compareQuery(repos, preference)}`', compare_page)
            self.assertIn('fetch("projects.json"', compare_page)
            self.assertIn("buildStaticCompare", compare_page)
            self.assertIn("comparisonMatrix", compare_page)
            self.assertIn("bestBy", compare_page)
            self.assertIn("项目数量", compare_page)
            self.assertIn("推荐结论", compare_page)
            self.assertIn("compareRecommendation", compare_page)
            self.assertIn("scoring_model", compare_page)
            self.assertIn("rule:v1", compare_page)
            self.assertIn("rule:v2-preference", compare_page)
            self.assertIn('id="profile"', compare_page)
            self.assertIn('id="profileButtons"', compare_page)
            self.assertIn("loadProfiles", compare_page)
            self.assertIn("applyProfile", compare_page)
            self.assertIn("quickProfiles", compare_page)
            self.assertIn("preferenceBonus", compare_page)
            self.assertIn("compareQuery", compare_page)
            subscriptions_page = (root / "docs" / "subscriptions.html").read_text(encoding="utf-8")
            self.assertIn("GitHub 订阅配置", subscriptions_page)
            self.assertIn('fetch("/v1/subscriptions?limit=100"', subscriptions_page)
            self.assertIn('fetch("/v1/subscriptions"', subscriptions_page)
            self.assertIn('method: "PATCH"', subscriptions_page)
            self.assertIn("recommendations.html?", subscriptions_page)
            self.assertIn("预览推荐", subscriptions_page)
            self.assertIn('id="profileButtons"', subscriptions_page)
            self.assertIn("loadProfiles", subscriptions_page)
            self.assertIn("applyProfile", subscriptions_page)
            self.assertIn("syncProfileParams", subscriptions_page)
            self.assertIn("生成任务", subscriptions_page)
            self.assertIn("triggerSubscription", subscriptions_page)
            self.assertIn("/trigger", subscriptions_page)
            self.assertIn("job.html?job=", subscriptions_page)
            self.assertIn('data-preview="${escapeAttribute(item.subscription_id)}"', subscriptions_page)
            self.assertIn("/recommendations?limit=5", subscriptions_page)
            self.assertIn("previewHtml", subscriptions_page)
            self.assertIn("projectDetailUrl", subscriptions_page)
            self.assertIn("这里只保存通道名称", subscriptions_page)
            project_page = (root / "docs" / "project.html").read_text(encoding="utf-8")
            self.assertIn("GitHub 项目详情", project_page)
            self.assertIn('fetch(`/api/projects/${encodeURIComponentOwnerRepo(repo)}`', project_page)
            self.assertIn('fetch(`/api/projects/${encodeURIComponentOwnerRepo(repo)}/similar?limit=8`', project_page)
            self.assertIn('fetch("projects.json"', project_page)
            self.assertIn("enrichApiDetail", project_page)
            self.assertIn("similarity_reasons", project_page)
            self.assertIn("buildStaticDetail", project_page)
            self.assertIn("Promise.resolve()", project_page)
            self.assertIn("请从项目筛选页点击具体项目进入", project_page)
            self.assertIn("历史趋势", project_page)
            self.assertIn("trendHtml", project_page)
            self.assertIn("推荐理由", project_page)
            self.assertIn("趋势判断", project_page)
            self.assertIn("projectSelectionReasons", project_page)
            self.assertIn("projectTrendSummary", project_page)
            self.assertIn("listHtml", project_page)
            self.assertIn("历史入选 ${ordered.length} 次", project_page)
            self.assertIn("bar-fill quality", project_page)
            self.assertIn("历史入选记录", project_page)
            self.assertIn("相似项目", project_page)
            self.assertIn("与相似项目对比", project_page)
            self.assertIn("与当前项目对比", project_page)
            self.assertIn("compareUrl([detail.full_name", project_page)
            self.assertIn("RAG 证据", project_page)
            self.assertIn("/v1/projects/${encodeURIComponentOwnerRepo(repo)}/rag?", project_page)
            self.assertIn("RAG 解释历史", project_page)
            self.assertIn('params.set("explanation_limit", "5")', project_page)
            self.assertIn("loadProjectRag", project_page)
            self.assertIn("ragEvidenceHtml", project_page)
            self.assertIn("ragExplanationsHtml", project_page)
            self.assertIn("rag_explanations", project_page)
            self.assertIn("rag_explanation_summary", project_page)
            self.assertIn("rag_prompt_context", project_page)
            self.assertIn("submitProjectFeedback", project_page)
            self.assertIn('fetch("/v1/feedback"', project_page)
            self.assertIn("feedbackMemoryHtml", project_page)
            self.assertIn("projectFeedbackStatus", project_page)
            self.assertIn("feedback_memory", project_page)
            self.assertIn("adminWriteHeaders", project_page)
            runs_page = (root / "docs" / "runs.html").read_text(encoding="utf-8")
            self.assertIn("运行状态面板", runs_page)
            self.assertIn('fetch("runs.json"', runs_page)
            self.assertIn('id="fallback"', runs_page)
            self.assertIn("trending_top10_fulfillment_rate", runs_page)
            self.assertIn("collector_success_rate", runs_page)
            self.assertIn("telegram_explorer_url", runs_page)
            self.assertIn('id="errorKind"', runs_page)
            self.assertIn("collector_error_summary", runs_page)
            self.assertIn("errorKindLabel", runs_page)
            feed = (root / "docs" / "feed.xml").read_text(encoding="utf-8")
            self.assertIn("<rss version=\"2.0\">", feed)
            self.assertIn("<lastBuildDate>Tue, 28 Apr 2026 00:00:00 +0000</lastBuildDate>", feed)
            self.assertIn("GitHub 每周热点项目周报 - 2026-04-28", feed)
            self.assertIn("weekly/2026-04-28.html", feed)
            self.assertIn("入选项目 10 个", feed)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_builds_empty_projects_table_with_complete_columns(self):
        root = Path.cwd() / f".tmp-pages-empty-test-{uuid.uuid4().hex}"
        try:
            (root / "reports").mkdir(parents=True)

            build_pages(root)

            projects = (root / "docs" / "projects.md").read_text(encoding="utf-8")
            self.assertIn("| - | 暂无项目 | - | - | - | - | 0 | 0 | 0 | - |", projects)
            self.assertIn("[周报归档首页](index.html)", projects)
            projects_json = json.loads((root / "docs" / "projects.json").read_text(encoding="utf-8"))
            runs_json = json.loads((root / "docs" / "runs.json").read_text(encoding="utf-8"))
            jobs_json = json.loads((root / "docs" / "jobs.json").read_text(encoding="utf-8"))
            profiles_json = json.loads((root / "docs" / "profiles.json").read_text(encoding="utf-8"))
            self.assertEqual(projects_json["projects"], [])
            self.assertEqual(runs_json["runs"], [])
            self.assertEqual(jobs_json["jobs"], [])
            self.assertEqual(profiles_json["profiles"], [])
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_builds_public_profiles_json_from_config(self):
        root = Path.cwd() / f".tmp-pages-profile-test-{uuid.uuid4().hex}"
        try:
            (root / "reports").mkdir(parents=True)
            (root / "config").mkdir(parents=True)
            (root / "config" / "profiles.example.json").write_text(
                json.dumps(
                    {
                        "agent_development": {
                            "profile_label": "Agent 开发",
                            "learning_goals": ["工具调用"],
                            "preferred_languages": ["Python"],
                            "preferred_topics": ["agent"],
                            "search_topics": ["llm"],
                            "secret_note": "不应公开",
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            build_pages(root)

            profiles = json.loads((root / "docs" / "profiles.json").read_text(encoding="utf-8"))
            self.assertEqual(profiles["profiles"][0]["name"], "agent_development")
            self.assertEqual(profiles["profiles"][0]["label"], "Agent 开发")
            self.assertEqual(profiles["profiles"][0]["preferred_languages"], ["Python"])
            self.assertNotIn("secret_note", profiles["profiles"][0])
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_builds_quality_fields_for_legacy_selected_projects(self):
        root = Path.cwd() / f".tmp-pages-quality-test-{uuid.uuid4().hex}"
        try:
            (root / "reports").mkdir(parents=True)
            (root / "data" / "selected").mkdir(parents=True)
            (root / "reports" / "2026-05-06.md").write_text("# 周报", encoding="utf-8")
            (root / "data" / "selected" / "2026-05-06.json").write_text(
                json.dumps(
                    [
                        {
                            "full_name": "owner/project",
                            "html_url": "https://github.com/owner/project",
                            "description": "short",
                            "language": "Python",
                            "stargazers_count": 50,
                            "forks_count": 0,
                            "pushed_at": "2026-05-05T00:00:00Z",
                            "readme_summary": "",
                        }
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            build_pages(root)

            projects = json.loads((root / "docs" / "projects.json").read_text(encoding="utf-8"))
            item = projects["projects"][0]
            self.assertGreater(item["quality_score"], 0)
            self.assertNotEqual(item["quality_level"], "unknown")
            self.assertTrue(item["quality_flags"])
        finally:
            shutil.rmtree(root, ignore_errors=True)


    def test_weekly_html_converts_tables_and_links(self):
        root = Path.cwd() / f".tmp-pages-test-{uuid.uuid4().hex}"
        try:
            (root / "reports").mkdir(parents=True)
            (root / "reports" / "2026-06-03.md").write_text(
                "# 周报\n\n"
                "| 项目 | 链接 |\n"
                "| --- | --- |\n"
                "| repo | [https://github.com/a/b](https://github.com/a/b) |\n",
                encoding="utf-8",
            )

            build_pages(root)

            weekly_html = (root / "docs" / "weekly" / "2026-06-03.html").read_text(encoding="utf-8")
            self.assertIn("<table>", weekly_html)
            self.assertIn('<a href="https://github.com/a/b">https://github.com/a/b</a>', weekly_html)
            self.assertNotIn("](https://github.com/a/b)", weekly_html)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_weekly_html_cleans_readme_badges_and_relative_links(self):
        root = Path.cwd() / f".tmp-pages-test-{uuid.uuid4().hex}"
        try:
            (root / "reports").mkdir(parents=True)
            (root / "reports" / "2026-06-04.md").write_text(
                "- README 摘要：[中文](README.zh-CN.md) "
                "![badge](https://img.shields.io/badge/test-ok) "
                "<a href=\"https://example.com/docs\">Docs</a>\n",
                encoding="utf-8",
            )

            build_pages(root)

            weekly_html = (root / "docs" / "weekly" / "2026-06-04.html").read_text(encoding="utf-8")
            self.assertIn("中文", weekly_html)
            self.assertIn("badge", weekly_html)
            self.assertNotIn("](README.zh-CN.md)", weekly_html)
            self.assertNotIn("](https://img.shields.io", weekly_html)
            self.assertNotIn("https://example.com/docs&quot;", weekly_html)
            self.assertIn('<a href="https://example.com/docs">Docs</a>', weekly_html)
        finally:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
