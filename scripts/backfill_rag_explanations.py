from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.api.repository import ApiRepository


def backfill_rag_explanations(
    *,
    root: Path = ROOT,
    db_path: Path | None = None,
    limit: int = 10,
    rag_limit: int = 8,
    mode: str = "fts5",
    model: str = "local-hash-v1",
    auto_build: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    repository = ApiRepository(root=root, db_path=db_path)
    limit = max(1, min(int(limit or 10), 100))
    rag_limit = max(1, min(int(rag_limit or 8), 30))
    coverage = repository.rag_coverage(limit=100)
    candidates = [
        item
        for item in coverage.get("gaps", [])
        if int(item.get("explanation_count") or 0) <= 0 and item.get("full_name")
    ][:limit]

    processed = []
    for item in candidates:
        full_name = str(item["full_name"])
        bundle = repository.project_rag_bundle(
            full_name,
            limit=rag_limit,
            explanation_limit=1,
            mode=mode,
            model=model,
            auto_build=auto_build,
        )
        project = bundle.get("project") if isinstance(bundle.get("project"), dict) else {}
        record = {
            "full_name": full_name,
            "query": bundle.get("query") or full_name,
            "dry_run": dry_run,
            "status": "planned" if dry_run else "created",
            "previous_gap_reasons": item.get("gap_reasons") or [],
        }
        if not dry_run:
            explanation = repository.rag_explain(
                query=str(record["query"]),
                language=str(project.get("language") or item.get("language") or "") or None,
                category=str(project.get("category") or item.get("category") or "") or None,
                limit=rag_limit,
                mode=mode,
                model=model,
                auto_build=auto_build,
            )
            record.update(
                {
                    "explanation_id": explanation.get("explanation_id") or "",
                    "quality_score": explanation.get("quality", {}).get("score", 0),
                    "quality_level": explanation.get("quality", {}).get("level", ""),
                    "context_count": explanation.get("count", 0),
                }
            )
        processed.append(record)

    return {
        "status": "ok",
        "dry_run": dry_run,
        "requested_limit": limit,
        "candidate_count": len(candidates),
        "processed_count": len(processed),
        "processed": processed,
        "coverage_before": {
            "total_projects": coverage.get("total_projects", 0),
            "healthy_project_count": coverage.get("healthy_project_count", 0),
            "coverage_rate": coverage.get("coverage_rate", 0),
            "gap_count": coverage.get("gap_count", 0),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="为缺少解释历史的项目批量生成规则版 RAG 解释。")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--db-path", type=Path, default=None)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--rag-limit", type=int, default=8)
    parser.add_argument("--mode", choices=["fts5", "vector"], default="fts5")
    parser.add_argument("--model", default="local-hash-v1")
    parser.add_argument("--auto-build", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    result = backfill_rag_explanations(
        root=args.root,
        db_path=args.db_path,
        limit=args.limit,
        rag_limit=args.rag_limit,
        mode=args.mode,
        model=args.model,
        auto_build=args.auto_build,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
