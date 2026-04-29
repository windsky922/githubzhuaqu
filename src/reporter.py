from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request

from .models import Repository
from .settings import Settings


def generate_report(
    repositories: list[Repository],
    queries: list[str],
    settings: Settings,
    trend_summary: dict | None = None,
) -> tuple[str, bool, str]:
    if settings.kimi_api_key and settings.kimi_model:
        try:
            return normalize_report_markdown(
                _generate_with_kimi(repositories, queries, settings, trend_summary or {})
            ), False, ""
        except Exception as error:
            if _is_content_filter_error(error):
                try:
                    return normalize_report_markdown(
                        _generate_with_kimi(
                            repositories,
                            queries,
                            settings,
                            trend_summary or {},
                            include_readme=False,
                        )
                    ), False, ""
                except Exception as retry_error:
                    error = RuntimeError(f"{error}; retry_without_readme: {retry_error}")
            return normalize_report_markdown(
                fallback_report(repositories, queries, settings, trend_summary or {})
            ), True, str(error)
    return normalize_report_markdown(
        fallback_report(repositories, queries, settings, trend_summary or {})
    ), True, "Kimi API 未配置"


def fallback_report(
    repositories: list[Repository],
    queries: list[str],
    settings: Settings,
    trend_summary: dict | None = None,
) -> str:
    lines = [
        f"# GitHub 每周热点项目周报 - {settings.run_date}",
        "",
        "## 一、本周趋势",
        "",
    ]
    if repositories:
        lines.append("本周根据 GitHub Search API 结果生成降级版周报。以下分析基于仓库名称、简介、README 摘要、语言、Star 和 Fork 数据；具体降级原因记录在本次运行摘要中。")
        lines.extend(["", *_trend_lines(trend_summary or {})])
    else:
        lines.append("本周未发现符合条件的项目，或 GitHub Search API 暂时不可用。")

    lines.extend(
        [
            "",
            "## 二、热点项目总览",
            "",
            "| 序号 | 项目 | 方向 | Star | 新增 Star | Fork | 语言 | 链接 |",
            "|---:|---|---|---:|---:|---:|---|---|",
        ]
    )
    for index, repo in enumerate(repositories, start=1):
        lines.append(
            f"| {index} | {repo.full_name} | {repo.category} | {repo.stargazers_count} | {repo.star_growth} | {repo.forks_count} | {repo.language} | [{repo.html_url}]({repo.html_url}) |"
        )

    lines.extend(["", "## 三、重点项目分析", ""])
    for index, repo in enumerate(repositories, start=1):
        lines.extend(
            [
                f"### {index}. {repo.full_name}",
                "",
                f"- 项目定位：仅根据仓库名称和简介判断，属于 {repo.category} 方向。",
                f"- 简介：{repo.description}",
                f"- README 摘要：{_short_text(repo.readme_excerpt) or '未获取到 README 内容。'}",
                f"- 技术信息：主要语言 {repo.language}，Star {repo.stargazers_count}，Fork {repo.forks_count}，较上次记录新增 Star {repo.star_growth}。",
                f"- 学习价值：可作为了解 {repo.category} 相关开源实践的参考。",
                f"- 原链接：[{repo.html_url}]({repo.html_url})",
                "",
            ]
        )

    lines.extend(
        [
            "## 四、最适合关注的项目",
            "",
        ]
    )
    for repo in repositories[:3]:
        lines.append(f"- {repo.full_name}：[{repo.html_url}]({repo.html_url})")

    lines.extend(
        [
            "",
            "## 五、本周结论",
            "",
            "建议优先查看排名靠前且与个人兴趣关键词匹配的项目。后续版本会加入 README 深度分析和历史去重。",
            "",
            "## 附录：搜索条件与生成信息",
            "",
            f"- 生成日期：{settings.run_date}",
            f"- 搜索起始日期：{settings.since_date}",
            f"- 最低 Star：{settings.min_stars}",
            f"- 最大项目数：{settings.max_projects}",
            "- 搜索条件：",
        ]
    )
    lines.extend(f"  - `{query}`" for query in queries)
    return "\n".join(lines).strip() + "\n"


def _trend_lines(trend_summary: dict) -> list[str]:
    points = trend_summary.get("summary_points") or []
    return [f"- {point}" for point in points]


def normalize_report_markdown(report: str) -> str:
    normalized = report.replace("蟒蛇", "Python")
    lines = [_link_github_urls(line) for line in normalized.splitlines()]
    return "\n".join(lines).strip() + "\n"


def _link_github_urls(line: str) -> str:
    if "https://github.com/" not in line:
        return line
    line = re.sub(
        r"\[GitHub\]\((https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)\)",
        lambda match: f"[{match.group(1)}]({match.group(1)})",
        line,
    )
    return re.sub(
        r"(?<![\[\(])https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+",
        lambda match: f"[{match.group(0)}]({match.group(0)})",
        line,
    )


def _short_text(text: str, limit: int = 320) -> str:
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def _generate_with_kimi(
    repositories: list[Repository],
    queries: list[str],
    settings: Settings,
    trend_summary: dict,
    include_readme: bool = True,
) -> str:
    prompt_path = settings.root / "prompts" / "weekly_report.md"
    system_prompt = prompt_path.read_text(encoding="utf-8")
    user_payload = {
        "run_date": settings.run_date,
        "since_date": settings.since_date,
        "queries": queries,
        "repositories": [_repository_payload(repo, include_readme) for repo in repositories],
        "trend_summary": trend_summary,
        "interests": settings.interests,
    }
    payload = {
        "model": settings.kimi_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ],
        "temperature": 1,
    }
    base_url = settings.kimi_base_url.rstrip("/")
    url = base_url if base_url.endswith("/chat/completions") else base_url + "/chat/completions"
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.kimi_api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=_kimi_timeout_seconds()) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Kimi API error {error.code}: {body}") from error

    content = _extract_content(data)
    if not content.strip():
        raise RuntimeError(f"Kimi API 返回空报告，响应结构：{_response_shape(data)}")
    return content.strip() + "\n"


def _repository_payload(repo: Repository, include_readme: bool) -> dict:
    payload = repo.to_dict()
    if not include_readme:
        payload["readme_excerpt"] = ""
    return payload


def _is_content_filter_error(error: Exception) -> bool:
    message = str(error).lower()
    return "content_filter" in message or "high risk" in message


def _kimi_timeout_seconds() -> int:
    try:
        return int(os.getenv("KIMI_TIMEOUT_SECONDS", "120"))
    except ValueError:
        return 120


def _extract_content(data: dict) -> str:
    choice = (data.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("content") or ""))
            else:
                parts.append(str(item))
        return "\n".join(part for part in parts if part)
    for key in ("reasoning_content", "text", "output_text"):
        value = message.get(key) or choice.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def _response_shape(data: dict) -> str:
    choice = (data.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    return json.dumps(
        {
            "top_level_keys": sorted(data.keys()),
            "choice_keys": sorted(choice.keys()),
            "message_keys": sorted(message.keys()),
            "finish_reason": choice.get("finish_reason"),
            "content_type": type(message.get("content")).__name__,
        },
        ensure_ascii=False,
    )
