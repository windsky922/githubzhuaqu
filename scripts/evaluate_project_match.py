"""Run the deterministic Chinese project-match retrieval baseline.

This is deliberately an offline evaluator.  It calls repository retrieval methods
directly and never invokes the answer endpoint or stores model responses.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.api.repository import ApiRepository


MODES: dict[str, Callable[..., dict[str, Any]]] = {
    "fts5": ApiRepository.rag_retrieve,
    "local-hash-v1": ApiRepository.rag_vector_search,
    "hybrid": ApiRepository.rag_hybrid_search,
}

# The fixture is a fixed corpus, rather than the changing weekly archive.  It makes
# the baseline repeatable while allowing --root to measure a real archive separately.
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


def load_cases(path: Path) -> list[dict[str, Any]]:
    cases = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            case = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number} 不是合法 JSONL：{exc.msg}") from exc
        if not isinstance(case, dict):
            raise ValueError(f"{path}:{line_number} 必须是对象")
        for key in ("id", "query", "relevant_repositories", "expect_clarification"):
            if key not in case:
                raise ValueError(f"{path}:{line_number} 缺少 {key}")
        if not isinstance(case["relevant_repositories"], list) or not case["relevant_repositories"]:
            raise ValueError(f"{path}:{line_number} relevant_repositories 必须为非空数组")
        cases.append(case)
    if len(cases) < 50:
        raise ValueError(f"评估集至少需要 50 条样本，当前只有 {len(cases)} 条")
    if len({str(case["id"]) for case in cases}) != len(cases):
        raise ValueError("评估集 id 不能重复")
    return cases


def write_fixture(root: Path) -> None:
    selected = root / "data" / "selected"
    selected.mkdir(parents=True, exist_ok=True)
    records = [
        {
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
        for index, (name, language, category, description, source) in enumerate(FIXTURE_PROJECTS)
    ]
    (selected / "2026-01-01.json").write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")


def _repositories(result: dict[str, Any]) -> list[str]:
    return [
        str(item.get("metadata", {}).get("full_name") or "")
        for item in result.get("contexts", [])
        if isinstance(item, dict)
    ]


def _has_constraint_violation(result: dict[str, Any], constraints: dict[str, Any]) -> bool:
    for context in result.get("contexts", []):
        metadata = context.get("metadata", {}) if isinstance(context, dict) else {}
        for key in ("language", "category"):
            expected = str(constraints.get(key) or "")
            if expected and str(metadata.get(key) or "") != expected:
                return True
        expected_source = str(constraints.get("source") or "")
        sources = metadata.get("sources") or []
        if expected_source and expected_source not in sources:
            return True
    return False


def _metrics(rows: list[dict[str, Any]], cutoff: int) -> tuple[float, float]:
    hits = sum(1 for row in rows if any(name in row["expected"] for name in row["returned"][:cutoff]))
    reciprocal_ranks = []
    for row in rows:
        rank = next((index for index, name in enumerate(row["returned"][:cutoff], start=1) if name in row["expected"]), 0)
        reciprocal_ranks.append(1 / rank if rank else 0)
    total = len(rows) or 1
    return round(hits / total, 4), round(sum(reciprocal_ranks) / total, 4)


def evaluate(repository: ApiRepository, cases: list[dict[str, Any]]) -> dict[str, Any]:
    mode_rows: dict[str, list[dict[str, Any]]] = {name: [] for name in MODES}
    for case in cases:
        constraints = case.get("constraints") if isinstance(case.get("constraints"), dict) else {}
        kwargs = {
            "query": str(case["query"]),
            "language": constraints.get("language") or None,
            "category": constraints.get("category") or None,
            "source": constraints.get("source") or None,
            "limit": 10,
        }
        for name, method in MODES.items():
            result = method(repository, **({**kwargs, "auto_build": True} if name != "fts5" else kwargs))
            returned = _repositories(result)
            mode_rows[name].append(
                {
                    "id": case["id"],
                    "expected": [str(item) for item in case["relevant_repositories"]],
                    "returned": returned,
                    "constraint_violation": _has_constraint_violation(result, constraints),
                    "expect_clarification": bool(case["expect_clarification"]),
                    "clarification": not bool(returned),
                }
            )

    modes = {}
    for name, rows in mode_rows.items():
        recall3, _ = _metrics(rows, 3)
        recall10, mrr10 = _metrics(rows, 10)
        total = len(rows) or 1
        modes[name] = {
            "recall_at_3": recall3,
            "recall_at_10": recall10,
            "mrr_at_10": mrr10,
            "hard_constraint_violation_rate": round(sum(row["constraint_violation"] for row in rows) / total, 4),
            "zero_hit_rate": round(sum(not row["returned"] for row in rows) / total, 4),
            "clarification_accuracy": round(sum(row["clarification"] == row["expect_clarification"] for row in rows) / total, 4),
        }
    return {"schema_version": 1, "sample_count": len(cases), "modes": modes}


def main() -> int:
    parser = argparse.ArgumentParser(description="运行项目匹配固定基线评估")
    parser.add_argument("--dataset", type=Path, default=Path("evals/project_match_cases.jsonl"))
    parser.add_argument("--root", type=Path, help="评估指定 weekly archive；不传时使用固定 fixture")
    parser.add_argument("--output", type=Path, help="把完整结果写为 JSON")
    args = parser.parse_args()
    cases = load_cases(args.dataset)
    temporary_root: Path | None = None
    root = args.root
    if root is None:
        temporary_root = Path(tempfile.mkdtemp(prefix="project-match-eval-"))
        write_fixture(temporary_root)
        root = temporary_root
    try:
        result = evaluate(ApiRepository(root=root, db_path=root / "data" / "github_weekly.sqlite"), cases)
        result["dataset"] = str(args.dataset)
        result["corpus"] = "fixture" if temporary_root else str(root)
        rendered = json.dumps(result, ensure_ascii=False, indent=2)
        print(rendered)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered + "\n", encoding="utf-8")
    finally:
        if temporary_root:
            shutil.rmtree(temporary_root, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
