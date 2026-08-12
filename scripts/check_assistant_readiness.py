from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.api.readiness import build_assistant_readiness
from src.api.repository import ApiRepository
from src.llm.client import KimiChatClient


def check_readiness() -> dict[str, Any]:
    repository = ApiRepository(root=ROOT, force_read_only=True)
    return build_assistant_readiness(repository, KimiChatClient())


def _setup_failure() -> dict[str, Any]:
    components = {
        name: {
            "status": "unavailable",
            "code": "preflight_setup_error",
            "message": "本机 readiness 探针无法完成初始化。",
            "recovery": "检查本机文件权限与配置格式后重试。",
        }
        for name in ("api", "model", "snapshot", "rag", "access")
    }
    return {
        "schema_version": 1,
        "status": "unavailable",
        "summary": "本机 readiness 探针初始化失败。",
        "capabilities": {
            "can_chat": False,
            "knowledge_available": False,
            "project_available": False,
            "current_project_available": False,
        },
        "components": components,
        "issues": [
            {
                "component": "api",
                "code": "preflight_setup_error",
                "message": components["api"]["message"],
                "recovery": components["api"]["recovery"],
            }
        ],
    }


def safe_check_readiness(
    checker: Callable[[], dict[str, Any]] = check_readiness,
) -> dict[str, Any]:
    try:
        return checker()
    except Exception:
        return _setup_failure()


def _human_lines(result: dict[str, Any]) -> list[str]:
    lines = [f"Assistant readiness: {result['status']}", str(result["summary"])]
    for name, component in result["components"].items():
        lines.append(f"- {name}: {component['status']} ({component['code']})")
        if component.get("recovery"):
            lines.append(f"  recovery: {component['recovery']}")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the side-effect-free local Assistant preflight.")
    parser.add_argument("--json", action="store_true", help="Print the redacted JSON contract.")
    args = parser.parse_args()
    result = safe_check_readiness()
    if args.json:
        print(json.dumps(result, sort_keys=True))
    else:
        print("\n".join(_human_lines(result)))
    return {"ready": 0, "degraded": 1, "unavailable": 2}.get(str(result.get("status")), 2)


if __name__ == "__main__":
    raise SystemExit(main())
