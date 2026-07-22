from __future__ import annotations

import unittest
from pathlib import PurePosixPath

from src.public_archive import project_archive_json


class PublicArchiveProjectionTest(unittest.TestCase):
    def test_run_projection_keeps_only_allowlisted_freshness_attestation_fields(self):
        projected = project_archive_json(
            PurePosixPath("data/runs/2026-07-20.json"),
            {
                "run_date": "2026-07-20",
                "status": "success",
                "private": "discard",
                "rag_freshness": {
                    "schema_version": 1,
                    "source_latest_date": "2026-07-20",
                    "corpus_latest_date": "2026-07-20",
                    "embedding_latest_date": "2026-07-20",
                    "source_hash": "source",
                    "corpus_hash": "corpus",
                    "embedding_hash": "embedding",
                    "secret": "discard",
                },
            },
        )
        self.assertNotIn("private", projected)
        self.assertEqual(projected["rag_freshness"]["source_hash"], "source")
        self.assertNotIn("secret", projected["rag_freshness"])
