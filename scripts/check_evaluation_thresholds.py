"""Fail CI when fixed-fixture evaluation results drift below frozen thresholds."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SUPPORTED_SCHEMA_VERSION = 1


def load_config(path: Path) -> dict[str, Any]:
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("评估阈值配置无法读取或不是有效 JSON。") from error
    if not isinstance(config, dict) or config.get("schema_version") != SUPPORTED_SCHEMA_VERSION:
        raise ValueError("评估阈值配置 schema_version 不受支持。")
    if not isinstance(config.get("fixtures"), dict) or not isinstance(config.get("evaluations"), dict):
        raise ValueError("评估阈值配置结构无效。")
    return config


def verify_fixture_hashes(config: dict[str, Any], root: Path = ROOT) -> dict[str, str]:
    verified: dict[str, str] = {}
    for name, item in config["fixtures"].items():
        if not isinstance(item, dict) or not isinstance(item.get("path"), str) or not isinstance(item.get("sha256"), str):
            raise ValueError(f"fixture 配置无效：{name}")
        path = root / item["path"]
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != item["sha256"]:
            raise ValueError(f"fixture SHA-256 不匹配：{name}")
        verified[name] = actual
    return verified


def check_results(config: dict[str, Any], results: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    for name, rules in config["evaluations"].items():
        result = results.get(name)
        if not isinstance(result, dict):
            violations.append({"evaluation": name, "reason": "missing_result"})
            continue
        if not isinstance(rules, dict):
            raise ValueError(f"evaluation 配置无效：{name}")
        for kind, comparator in (("minimum", lambda actual, expected: actual < expected), ("maximum", lambda actual, expected: actual > expected)):
            thresholds = rules.get(kind, {})
            if not isinstance(thresholds, dict):
                raise ValueError(f"{name}.{kind} 必须是对象")
            for dotted_path, expected in thresholds.items():
                actual = _metric_at(result, dotted_path)
                if not isinstance(expected, (int, float)) or not isinstance(actual, (int, float)):
                    violations.append({"evaluation": name, "metric": dotted_path, "rule": kind, "expected": expected, "actual": actual})
                elif comparator(actual, expected):
                    violations.append({"evaluation": name, "metric": dotted_path, "rule": kind, "expected": expected, "actual": actual})
    return violations


def _metric_at(result: dict[str, Any], dotted_path: str) -> Any:
    current: Any = result
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _parse_results(items: list[str]) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    for item in items:
        name, separator, raw_path = item.partition("=")
        if not separator or not name or not raw_path or name in results:
            raise ValueError("--result 必须为唯一的 NAME=PATH。")
        try:
            payload = json.loads(Path(raw_path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(f"无法读取评估结果：{name}") from error
        if not isinstance(payload, dict):
            raise ValueError(f"评估结果必须是对象：{name}")
        results[name] = payload
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "config" / "evaluation-thresholds.json")
    parser.add_argument("--result", action="append", default=[], metavar="NAME=PATH")
    parser.add_argument("--output", type=Path, help="可选的公开阈值检查摘要 JSON 路径。")
    args = parser.parse_args()
    try:
        config = load_config(args.config)
        fixture_hashes = verify_fixture_hashes(config)
        violations = check_results(config, _parse_results(args.result))
    except ValueError as error:
        print(json.dumps({"accepted": False, "error": str(error)}, ensure_ascii=False))
        return 2
    summary = {
        "accepted": not violations,
        "schema_version": SUPPORTED_SCHEMA_VERSION,
        "commit": os.getenv("GITHUB_SHA", "local"),
        "fixture_hashes": fixture_hashes,
        "violations": violations,
    }
    rendered = json.dumps(summary, ensure_ascii=False, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())
