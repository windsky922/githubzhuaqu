import importlib.util
import shutil
import unittest
import uuid
from pathlib import Path


def _api_route_dependencies_installed() -> bool:
    return bool(importlib.util.find_spec("fastapi") and importlib.util.find_spec("httpx"))


@unittest.skipUnless(_api_route_dependencies_installed(), "FastAPI route dependencies are not installed")
class ApiEncodingTest(unittest.TestCase):
    def test_json_responses_declare_utf8_charset(self):
        from fastapi.testclient import TestClient
        from src.api.app import create_app

        root = Path.cwd() / f".tmp-api-encoding-test-{uuid.uuid4().hex}"
        try:
            root.mkdir(parents=True)
            client = TestClient(create_app(root=root, db_path=root / "data" / "github_weekly.sqlite"))

            response = client.get("/v1/health")

            self.assertEqual(response.status_code, 200)
            self.assertIn("application/json", response.headers["content-type"])
            self.assertIn("charset=utf-8", response.headers["content-type"].lower())
        finally:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
