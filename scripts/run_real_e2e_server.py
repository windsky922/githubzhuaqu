"""Run the real FastAPI app against an isolated deterministic SQLite fixture."""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
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
    "GH_SEARCH_TOKEN",
    "GITHUB_TOKEN",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
)


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
        write_project_match_fixture(root, include_e2e_capabilities=True)

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
        config = uvicorn.Config(app, host=HOST, port=PORT, log_level="warning", access_log=False)
        uvicorn.Server(config).run()


if __name__ == "__main__":
    main()
