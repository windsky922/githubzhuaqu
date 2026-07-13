"""Shared deterministic project archive fixture for offline evaluations and E2E."""

from __future__ import annotations

import json
from pathlib import Path


FIXTURE_PROJECTS = [
    ("eval/agent-orchestrator", "Python", "AI Agent", "多智能体 编排 工作流 自动化 agent orchestration", "github_trending"),
    ("eval/rag-knowledge", "TypeScript", "Developer Tools", "本地知识库 RAG 检索 文档问答 semantic search", "github_search"),
    ("eval/data-pipeline", "Python", "Data Engineering", "数据管道 ETL 调度 数据质量 data pipeline", "github_trending"),
    ("eval/flutter-mobile", "Dart", "Mobile", "Flutter 跨平台 移动应用 mobile client", "github_search"),
    ("eval/security-scanner", "Go", "Security", "依赖漏洞 扫描 软件供应链 security scanner", "github_trending"),
    ("eval/observability", "Rust", "DevOps", "可观测性 日志 指标 链路追踪 observability", "github_search"),
    ("eval/image-workflow", "Python", "AI", "图像生成 工作流 扩散模型 image generation", "github_trending"),
    ("eval/api-gateway", "Go", "Backend", "API 网关 限流 鉴权 gateway rate limit", "github_search"),
]


E2E_CAPABILITY_READMES = {
    "eval/agent-orchestrator": (
        "支持使用 Docker 自托管。本地部署但必须连接 OpenAI，并且必须配置 API Key。运行时必须联网。"
    ),
    "eval/rag-knowledge": (
        "支持 Docker 自托管。完成模型下载后可以完全离线运行，不依赖外部 API，也不需要 API Key。"
    ),
}


def write_project_match_fixture(root: Path, *, include_e2e_capabilities: bool = False) -> None:
    """Write the fixed selected-project archive under ``root``.

    Capability sentences are opt-in so the historical retrieval baselines keep
    using byte-for-byte equivalent project text.
    """

    selected = root / "data" / "selected"
    selected.mkdir(parents=True, exist_ok=True)
    records = []
    for index, (name, language, category, description, source) in enumerate(FIXTURE_PROJECTS):
        record = {
            "full_name": name,
            "html_url": f"https://github.com/{name}",
            "description": description,
            "language": language,
            "category": category,
            "sources": [source],
            "stargazers_count": 100,
            "forks_count": 10,
            "score": 0.9,
            "star_growth": 20,
            "trending_rank": index + 1,
            "selection_reasons": [f"匹配 {category} 方向。"],
            "security_flags": [],
            "quality_score": 90,
            "quality_level": "high",
            "quality_flags": [],
        }
        if include_e2e_capabilities and name in E2E_CAPABILITY_READMES:
            record["readme_summary"] = E2E_CAPABILITY_READMES[name]
        records.append(record)
    (selected / "2026-01-01.json").write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
