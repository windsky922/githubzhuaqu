from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from hashlib import sha1
from pathlib import Path
from typing import Any

from src.llm.client import KimiChatClient, LlmClientError
from src.rag.corpus_cleaner import CLEANER_VERSION, content_hash
from src.storage.sqlite_store import connect, initialize


PROMPT_VERSION = "rag-corpus-enrichment-v1"
FIELDS = ("deployment", "tech_stack", "license", "maintenance_status", "limitations")


def enrich_rag_corpus(
    *, db_path: Path, root: Path, limit: int = 20, replace: bool = False, client: KimiChatClient | None = None
) -> dict[str, Any]:
    model_client = client or KimiChatClient()
    status = model_client.status()
    if not status.get("configured"):
        return {"configured": False, "model": "", "candidate_count": 0, "processed_count": 0, "cached_count": 0, "failed_count": 0, "items": []}
    connection = connect(db_path)
    try:
        initialize(connection)
        rows = connection.execute(
            """SELECT p.* FROM project_corpus p JOIN (
                 SELECT full_name, MAX(run_date) AS run_date FROM project_corpus GROUP BY full_name
               ) latest ON latest.full_name=p.full_name AND latest.run_date=p.run_date
               ORDER BY p.run_date DESC, p.full_name LIMIT ?""",
            (max(1, min(int(limit or 20), 100)),),
        ).fetchall()
        items = []
        invalidated = 0
        for row in rows:
            key = f"{row['content_hash']}:{CLEANER_VERSION}:{PROMPT_VERSION}:{status.get('model') or ''}"
            enrichment_id = sha1(key.encode("utf-8")).hexdigest()
            cached = connection.execute("SELECT * FROM rag_corpus_enrichments WHERE enrichment_id=? AND status='succeeded'", (enrichment_id,)).fetchone()
            if cached and not replace:
                _apply_enrichment(
                    connection,
                    row,
                    json.loads(cached["structured_json"] or "{}"),
                    json.loads(cached["evidence_json"] or "{}"),
                )
                invalidated += connection.execute("DELETE FROM rag_embeddings").rowcount
                items.append({"full_name": row["full_name"], "status": "cached", "enrichment_id": enrichment_id})
                continue
            try:
                prompt = (root / "prompts" / "rag_corpus_enrichment.md").read_text(encoding="utf-8")
                raw = model_client.chat([
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"项目：{row['full_name']}\n\n不可信外部文本：\n{row['search_text']}"},
                ])
                structured, evidence = _validated_output(raw, str(row["search_text"] or ""))
                _persist_result(connection, enrichment_id, row, status, "succeeded", structured, evidence, "")
                _apply_enrichment(connection, row, structured, evidence)
                invalidated += connection.execute("DELETE FROM rag_embeddings").rowcount
                items.append({"full_name": row["full_name"], "status": "succeeded", "enrichment_id": enrichment_id})
            except (LlmClientError, ValueError, OSError) as exc:
                _persist_result(connection, enrichment_id, row, status, "failed", {}, {}, str(exc)[:500])
                items.append({"full_name": row["full_name"], "status": "failed", "error": str(exc)[:200], "enrichment_id": enrichment_id})
        connection.commit()
    finally:
        connection.close()
    return {
        "configured": True,
        "model": status.get("model") or "",
        "candidate_count": len(rows),
        "processed_count": sum(item["status"] == "succeeded" for item in items),
        "cached_count": sum(item["status"] == "cached" for item in items),
        "failed_count": sum(item["status"] == "failed" for item in items),
        "invalidated_embedding_count": invalidated,
        "embedding_rebuild_required": invalidated > 0,
        "items": items,
    }


def _validated_output(raw: str, source_text: str) -> tuple[dict[str, Any], dict[str, str]]:
    text = re.sub(r"^```(?:json)?|```$", "", str(raw or "").strip(), flags=re.IGNORECASE).strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("模型未返回合法 JSON") from exc
    structured: dict[str, Any] = {}
    evidence: dict[str, str] = {}
    for field in FIELDS:
        item = payload.get(field) if isinstance(payload, dict) else None
        if not isinstance(item, dict):
            continue
        value = item.get("value")
        quote = str(item.get("evidence") or "").strip()
        if value in (None, "", []) or not quote:
            continue
        if quote not in source_text:
            continue
        structured[field] = value
        evidence[field] = quote
    return structured, evidence


def _persist_result(connection, enrichment_id, row, status, result_status, structured, evidence, error) -> None:
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    connection.execute(
        """INSERT INTO rag_corpus_enrichments(
             enrichment_id, corpus_id, full_name, source_hash, cleaner_version, prompt_version,
             model, status, structured_json, evidence_json, error_summary, created_at, updated_at
           ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
           ON CONFLICT(enrichment_id) DO UPDATE SET status=excluded.status,
             structured_json=excluded.structured_json, evidence_json=excluded.evidence_json,
             error_summary=excluded.error_summary, updated_at=excluded.updated_at""",
        (enrichment_id, row["corpus_id"], row["full_name"], row["content_hash"], CLEANER_VERSION,
         PROMPT_VERSION, status.get("model") or "", result_status, json.dumps(structured, ensure_ascii=False),
         json.dumps(evidence, ensure_ascii=False), error, now, now),
    )


def _apply_enrichment(connection, row, structured, evidence) -> None:
    existing = json.loads(row["structured_json"] or "{}")
    existing.update(structured)
    connection.execute("UPDATE project_corpus SET structured_json=? WHERE corpus_id=?", (json.dumps(existing, ensure_ascii=False), row["corpus_id"]))
    connection.execute("DELETE FROM rag_chunks_fts WHERE chunk_id IN (SELECT chunk_id FROM rag_chunks WHERE corpus_id=? AND source_type='model_enrichment')", (row["corpus_id"],))
    connection.execute("DELETE FROM rag_chunks WHERE corpus_id=? AND source_type='model_enrichment'", (row["corpus_id"],))
    text = "\n".join(f"{field}: {value}（证据：{evidence.get(field, '')}）" for field, value in structured.items())
    if not text:
        return
    chunk_id = sha1(f"{row['corpus_id']}:model_enrichment:{content_hash(text)}".encode("utf-8")).hexdigest()
    payload = json.loads(row["payload_json"] or "{}")
    payload.update({"source_type": "model_enrichment", "structured": structured, "evidence": evidence})
    connection.execute(
        """INSERT INTO rag_chunks(chunk_id,corpus_id,chunk_index,run_date,full_name,html_url,language,category,
             sources_json,chunk_text,token_estimate,corpus_version,cleaner_version,content_hash,is_untrusted,source_type,payload_json)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (chunk_id,row["corpus_id"],999,row["run_date"],row["full_name"],row["html_url"],row["language"],row["category"],
         row["sources_json"],text,max(1,len(text)//4),row["corpus_version"],row["cleaner_version"],content_hash(text),1,
         "model_enrichment",json.dumps(payload,ensure_ascii=False)),
    )
    connection.execute("INSERT INTO rag_chunks_fts(chunk_id,full_name,language,category,chunk_text) VALUES(?,?,?,?,?)", (chunk_id,row["full_name"],row["language"],row["category"],text))
