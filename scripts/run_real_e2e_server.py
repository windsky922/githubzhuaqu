"""Run the real FastAPI app against an isolated deterministic SQLite fixture."""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from collections.abc import Iterator
from datetime import date
from pathlib import Path

import uvicorn


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.project_match_fixture import write_project_match_fixture
from src.api.app import create_app
from src.api.repository import ApiRepository


HOST = "127.0.0.1"
PORT = 4183
TEST_ADMIN_TOKEN = "p0-10-real-e2e-admin"
EXTERNAL_CREDENTIALS = (
    "KIMI_API_KEY",
    "KIMI_BASE_URL",
    "KIMI_MODEL",
    "KIMI_CANARY_ENABLED",
    "GH_SEARCH_TOKEN",
    "GITHUB_TOKEN",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
)


class _FakeKnowledgeClient:
    """Deterministic teaching-only model used by the isolated browser test."""

    def status(self) -> dict[str, object]:
        return {"provider": "fixture", "configured": True, "model": "fixture-knowledge-v1"}

    def chat(self, messages: list[dict[str, str]]) -> str:
        del messages
        return (
            "结论：先掌握 Agent 的目标、状态、工具调用与反馈循环，再学习多 Agent 协作。\n"
            "学习路线：Python 基础与 API → 单 Agent 循环 → 受控工具 → RAG 与评估 → 多 Agent 编排。\n"
            "最小实践：做一个只读研究助手，为每条项目结论绑定证据并加入失败降级。\n"
            "常见误区：先堆框架、忽略评估，或把模型常识当作实时项目事实。"
        )

    def stream_chat(self, messages: list[dict[str, str]]) -> Iterator[str]:
        for line in self.chat(messages).splitlines(keepends=True):
            yield line


def _isolate_environment() -> None:
    for name in EXTERNAL_CREDENTIALS:
        os.environ.pop(name, None)
    os.environ["ADMIN_API_TOKEN"] = TEST_ADMIN_TOKEN
    os.environ["SKIP_TELEGRAM_SEND"] = "1"


def main() -> None:
    _isolate_environment()
    with tempfile.TemporaryDirectory(prefix="github-weekly-real-e2e-") as temporary:
        root = Path(temporary)
        shutil.copytree(PROJECT_ROOT / "docs", root / "docs")
        run_date = date.today().isoformat()
        write_project_match_fixture(root, include_e2e_capabilities=True, run_date=run_date)

        runs = root / "data" / "runs"
        runs.mkdir(parents=True, exist_ok=True)
        freshness = {
            "schema_version": 1,
            "source_latest_date": run_date,
            "corpus_latest_date": run_date,
            "embedding_latest_date": run_date,
            "source_hash": "real-e2e-source",
            "corpus_version": "real-e2e-v1",
            "corpus_hash": "real-e2e-corpus",
            "embedding_model": "local-hash-v1",
            "embedding_hash": "real-e2e-embedding",
            "chunk_count": 8,
            "embedding_count": 8,
            "dimensions": 256,
        }
        (runs / f"{run_date}.json").write_text(
            json.dumps({"run_date": run_date, "status": "success", "rag_freshness": freshness}),
            encoding="utf-8",
        )
        os.environ["GITHUB_WEEKLY_SNAPSHOT_ROOT"] = str(root)

        db_path = root / "data" / "github_weekly.sqlite"
        repository = ApiRepository(root=root, db_path=db_path)
        repository.ensure_sqlite_index()
        repository.rag_vector_search(
            query="Python Agent RAG",
            limit=3,
            model="local-hash-v1",
            auto_build=True,
        )

        app = create_app(root=root, db_path=db_path)
        app.state.assistant.model_client = _FakeKnowledgeClient()
        app.state.assistant_repository.data_source = {
            **app.state.assistant_repository.data_source,
            "kind": "weekly_snapshot",
            "source_id": f"weekly_snapshot:real-e2e:{run_date}",
        }
        config = uvicorn.Config(app, host=HOST, port=PORT, log_level="warning", access_log=False)
        uvicorn.Server(config).run()


if __name__ == "__main__":
    main()
