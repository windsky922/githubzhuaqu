"""Evaluate deterministic structured recommendations on the P0-1 cases."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.evaluate_project_match import MODES, load_cases, write_fixture
from src.api.repository import ApiRepository
from src.rag.project_recommendations import build_project_recommendations


def evaluate_recommendations(repository: ApiRepository, cases: list[dict[str, Any]]) -> dict[str, Any]:
    repository.ensure_sqlite_index()
    mode_results = {}
    for mode, method in MODES.items():
        rows = []
        for case in cases:
            constraints = case.get("constraints") if isinstance(case.get("constraints"), dict) else {}
            kwargs = {
                "query": case["query"],
                "language": constraints.get("language") or None,
                "category": constraints.get("category") or None,
                "source": constraints.get("source") or None,
                "limit": 10,
            }
            if mode != "fts5":
                kwargs["auto_build"] = True
            retrieval = method(repository, **kwargs)
            contexts = retrieval.get("contexts") if isinstance(retrieval.get("contexts"), list) else []
            citations = retrieval.get("citations") if isinstance(retrieval.get("citations"), list) else []
            recommendations = build_project_recommendations(
                contexts=contexts,
                citations=citations,
                constraints=constraints,
            )
            eligible = [item for item in recommendations if item["eligibility"] == "eligible"]
            returned = [item["full_name"] for item in eligible]
            primary = eligible[0] if eligible else None
            rows.append(
                {
                    "expected": [str(item) for item in case["relevant_repositories"]],
                    "returned": returned,
                    "primary": primary,
                    "constraints": constraints,
                    "contexts": contexts,
                    "expect_clarification": bool(case["expect_clarification"]),
                }
            )
        mode_results[mode] = _metrics(rows)
    return {"sample_count": len(cases), "modes": mode_results}


def _metrics(rows: list[dict[str, Any]]) -> dict[str, float]:
    total = max(1, len(rows))
    reciprocal_ranks = []
    for row in rows:
        rank = next(
            (index for index, name in enumerate(row["returned"][:10], start=1) if name in row["expected"]),
            0,
        )
        reciprocal_ranks.append(1 / rank if rank else 0.0)
    return {
        "top_1_accuracy": round(
            sum(bool(row["returned"] and row["returned"][0] in row["expected"]) for row in rows) / total,
            4,
        ),
        "recall_at_3": round(
            sum(any(name in row["expected"] for name in row["returned"][:3]) for row in rows) / total,
            4,
        ),
        "mrr_at_10": round(sum(reciprocal_ranks) / total, 4),
        "hard_constraint_violation_rate": round(
            sum(_primary_violates(row) for row in rows) / total,
            4,
        ),
        "no_primary_rate": round(sum(not row["returned"] for row in rows) / total, 4),
    }


def _primary_violates(row: dict[str, Any]) -> bool:
    if not row["primary"]:
        return False
    full_name = row["primary"]["full_name"]
    metadata = [
        context.get("metadata") or {}
        for context in row["contexts"]
        if str((context.get("metadata") or {}).get("full_name") or "") == full_name
    ]
    constraints = row["constraints"]
    for key in ("language", "category"):
        expected = str(constraints.get(key) or "")
        values = [str(item.get(key) or "") for item in metadata if str(item.get(key) or "")]
        if expected and (not values or not any(value.casefold() == expected.casefold() for value in values)):
            return True
    expected_source = str(constraints.get("source") or "")
    sources = {
        str(source)
        for item in metadata
        for source in (item.get("sources") if isinstance(item.get("sources"), list) else [])
    }
    return bool(expected_source and expected_source not in sources)


def run(*, cases_path: Path, root: Path | None = None) -> dict[str, Any]:
    cases = load_cases(cases_path)
    if root:
        repository = ApiRepository(root=root, db_path=root / "data" / "github_weekly.sqlite")
        return evaluate_recommendations(repository, cases)
    with tempfile.TemporaryDirectory() as directory:
        fixture_root = Path(directory)
        write_fixture(fixture_root)
        repository = ApiRepository(root=fixture_root, db_path=fixture_root / "data" / "github_weekly.sqlite")
        return evaluate_recommendations(repository, cases)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=PROJECT_ROOT / "evals" / "project_match_cases.jsonl")
    parser.add_argument("--root", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run(cases_path=args.cases, root=args.root)
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
