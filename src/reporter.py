from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request

from .models import Repository
from .report_checks import check_report_quality
from .security import redact_sensitive_text
from .settings import Settings


def generate_report(
    repositories: list[Repository],
    queries: list[str],
    settings: Settings,
    trend_summary: dict | None = None,
) -> tuple[str, bool, str]:
    if settings.kimi_api_key and settings.kimi_model:
        try:
            return _generate_checked_kimi_report(
                repositories,
                queries,
                settings,
                trend_summary or {},
                include_readme=True,
            ), False, ""
        except Exception as error:
            if _is_content_filter_error(error):
                try:
                    return _generate_checked_kimi_report(
                        repositories,
                        queries,
                        settings,
                        trend_summary or {},
                        include_readme=False,
                    ), False, ""
                except Exception as retry_error:
                    error = RuntimeError(f"{error}; retry_without_readme: {retry_error}")
            return normalize_report_markdown(
                fallback_report(repositories, queries, settings, trend_summary or {})
            ), True, str(error)
    return normalize_report_markdown(
        fallback_report(repositories, queries, settings, trend_summary or {})
    ), True, "Kimi API 未配置"


def _generate_checked_kimi_report(
    repositories: list[Repository],
    queries: list[str],
    settings: Settings,
    trend_summary: dict,
    include_readme: bool,
) -> str:
    try:
        return _checked_kimi_report(
            _generate_with_kimi(
                repositories,
                queries,
                settings,
                trend_summary,
                include_readme=include_readme,
            ),
            repositories,
        )
    except Exception as error:
        if not _is_quality_check_error(error):
            raise
        try:
            return _checked_kimi_report(
                _generate_with_kimi(
                    repositories,
                    queries,
                    settings,
                    trend_summary,
                    include_readme=include_readme,
                    quality_feedback=str(error),
                ),
                repositories,
            )
        except Exception as retry_error:
            raise RuntimeError(f"{error}; retry_with_quality_feedback: {retry_error}") from retry_error


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
        lines.append("本周根据 GitHub Trending 与 GitHub Search 采集结果生成降级版周报。以下分析基于仓库名称、简介、README 摘要、语言、Star、Fork 和 Trending 排名；具体降级原因记录在本次运行摘要中。")
        lines.extend(["", *_trend_lines(trend_summary or {})])
    else:
        lines.append("本周未发现符合条件的项目，或 GitHub 采集暂时不可用。")

    lines.extend(
        [
            "",
            "## 二、热点项目总览",
            "",
            "| 序号 | 项目 | 来源 | Trending 排名 | 方向 | Star | 新增 Star | Fork | 语言 | 链接 |",
            "|---:|---|---|---:|---|---:|---:|---:|---|---|",
        ]
    )
    for index, repo in enumerate(repositories, start=1):
        lines.append(
            f"| {index} | {repo.full_name} | {_source_text(repo)} | {_trending_rank_text(repo)} | {repo.category} | {repo.stargazers_count} | {repo.star_growth} | {repo.forks_count} | {repo.language} | [{repo.html_url}]({repo.html_url}) |"
        )

    lines.extend(["", "## 三、重点项目分析", ""])
    for index, repo in enumerate(repositories, start=1):
        lines.extend(
            [
                f"### {index}. {repo.full_name}",
                "",
                f"- 项目定位：仅根据仓库名称和简介判断，属于 {repo.category} 方向。",
                f"- 简介：{repo.description}",
                f"- README 摘要：{_short_text(_readme_summary_text(repo)) or '未获取到 README 内容。'}",
                f"- 技术信息：主要语言 {repo.language}，Star {repo.stargazers_count}，Fork {repo.forks_count}，较上次记录新增 Star {repo.star_growth}。",
                f"- 热度来源：{_source_text(repo)}，Trending 排名 {_trending_rank_text(repo)}。",
                f"- 入选原因：{_selection_reason_text(repo)}",
                f"- 风险提示：{_security_text(repo)}",
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
            "建议优先查看 Trending 排名靠前、近期增长明显且与个人兴趣关键词匹配的项目。复用或运行项目前，仍需人工审查代码、依赖和许可证。",
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
    return redact_sensitive_text("\n".join(lines).strip()) + "\n"


def _checked_kimi_report(report: str, repositories: list[Repository]) -> str:
    normalized = normalize_report_markdown(report)
    repaired = _repair_report_metadata(normalized, repositories)
    quality_errors = check_report_quality(repaired, repositories)
    if quality_errors:
        raise RuntimeError("Kimi 周报质量检查失败：" + "；".join(quality_errors[:5]))
    return repaired


def _repair_report_metadata(report: str, repositories: list[Repository]) -> str:
    appendix_lines = _metadata_appendix_lines(report, repositories)
    if not appendix_lines:
        return report
    return report.rstrip() + "\n\n## 附录：项目链接与来源补全\n\n" + "\n".join(appendix_lines) + "\n"


def _metadata_appendix_lines(report: str, repositories: list[Repository]) -> list[str]:
    lines = []
    for repo in repositories:
        required_link = f"[{repo.html_url}]({repo.html_url})" if repo.html_url else ""
        needs_link = bool(required_link and required_link not in report)
        needs_source = bool(repo.sources and not all(_source_label(source) in report for source in repo.sources))
        needs_trending = bool(repo.trending_rank > 0 and ("Trending" not in report or str(repo.trending_rank) not in report))
        needs_risk = bool(repo.security_flags and "风险" not in report and not any(flag in report for flag in repo.security_flags))
        if not any([needs_link, needs_source, needs_trending, needs_risk]):
            continue
        parts = [repo.full_name]
        if required_link:
            parts.append(required_link)
        if repo.sources:
            parts.append(f"来源：{_source_text(repo)}")
        if repo.trending_rank > 0:
            parts.append(f"Trending 排名：{repo.trending_rank}")
        if repo.security_flags:
            parts.append(f"风险提示：{_security_text(repo)}")
        lines.append("- " + "；".join(parts))
    return lines


def _trend_lines(trend_summary: dict) -> list[str]:
    points = trend_summary.get("summary_points") or []
    return [f"- {point}" for point in points]


def normalize_report_markdown(report: str) -> str:
    normalized = redact_sensitive_text(report).replace("蟒蛇", "Python")
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


def _readme_summary_text(repo: Repository) -> str:
    return repo.readme_summary or repo.readme_excerpt


def _security_text(repo: Repository) -> str:
    if not repo.security_flags:
        return "未发现明显元数据风险，但仍需自行审查代码和依赖。"
    return "；".join(repo.security_flags)


def _selection_reason_text(repo: Repository) -> str:
    if not repo.selection_reasons:
        return "综合 Star、活跃度和主题匹配度入选。"
    return "；".join(repo.selection_reasons)


def _source_text(repo: Repository) -> str:
    values = [_source_label(source) for source in repo.sources if source]
    return " + ".join(values) if values else "GitHub Search"


def _source_label(source: str) -> str:
    labels = {
        "github_trending": "GitHub Trending",
        "github_search": "GitHub Search",
    }
    return labels.get(source, source)


def _trending_rank_text(repo: Repository) -> str:
    return str(repo.trending_rank) if repo.trending_rank > 0 else "-"


def _generate_with_kimi(
    repositories: list[Repository],
    queries: list[str],
    settings: Settings,
    trend_summary: dict,
    include_readme: bool = True,
    quality_feedback: str = "",
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
    if quality_feedback:
        user_payload["quality_retry_feedback"] = {
            "message": quality_feedback,
            "instruction": "上一次周报未通过质量检查。请只使用本次输入项目，修复上述问题，并保留固定五段结构。",
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
    data = _post_kimi_with_retries(url, payload, settings)

    content = _extract_content(data)
    if not content.strip():
        raise RuntimeError(f"Kimi API 返回空报告，响应结构：{_response_shape(data)}")
    return content.strip() + "\n"


def _post_kimi_with_retries(url: str, payload: dict, settings: Settings) -> dict:
    errors = []
    max_retries = _kimi_max_retries()
    for attempt in range(max_retries + 1):
        try:
            with urllib.request.urlopen(_kimi_request(url, payload, settings), timeout=_kimi_timeout_seconds()) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            message = f"Kimi API error {error.code}: {body}"
            if not _is_transient_kimi_error(error.code, body) or attempt >= max_retries:
                raise RuntimeError("; ".join(errors + [message])) from error
            errors.append(f"{message}; retry_after={_kimi_retry_seconds()}s")
            time.sleep(_kimi_retry_seconds())
        except (TimeoutError, urllib.error.URLError) as error:
            message = f"Kimi API transient request error: {error}"
            if attempt >= max_retries:
                raise RuntimeError("; ".join(errors + [message])) from error
            errors.append(f"{message}; retry_after={_kimi_retry_seconds()}s")
            time.sleep(_kimi_retry_seconds())
    raise RuntimeError("; ".join(errors) or "Kimi API request failed")


def _kimi_request(url: str, payload: dict, settings: Settings) -> urllib.request.Request:
    return urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.kimi_api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )


def _repository_payload(repo: Repository, include_readme: bool) -> dict:
    payload = repo.to_dict()
    payload["description"] = redact_sensitive_text(str(payload.get("description") or ""))
    payload["readme_excerpt"] = redact_sensitive_text(str(payload.get("readme_excerpt") or ""))
    payload["readme_summary"] = redact_sensitive_text(str(payload.get("readme_summary") or payload.get("readme_excerpt") or ""))
    if not include_readme:
        payload["readme_excerpt"] = ""
        payload["readme_summary"] = ""
    return payload


def _is_content_filter_error(error: Exception) -> bool:
    message = str(error).lower()
    return "content_filter" in message or "high risk" in message


def _is_quality_check_error(error: Exception) -> bool:
    return "Kimi 周报质量检查失败" in str(error)


def _is_transient_kimi_error(status_code: int, body: str) -> bool:
    body_lower = body.lower()
    return status_code in {429, 500, 502, 503, 504} or "engine_overloaded" in body_lower or "rate limit" in body_lower


def _kimi_max_retries() -> int:
    try:
        return max(0, int(os.getenv("KIMI_MAX_RETRIES", "2")))
    except ValueError:
        return 2


def _kimi_retry_seconds() -> int:
    try:
        return max(0, int(os.getenv("KIMI_RETRY_SECONDS", "20")))
    except ValueError:
        return 20


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
