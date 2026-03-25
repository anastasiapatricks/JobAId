"""ChromaDB search and upsert tools for RAG."""

import json
import time
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from utils import debug, _log_context

_rag_logger = logging.getLogger("jobaid.rag")


def search_collection(collection, query: str, n_results: int = 5, where: Optional[dict] = None) -> List[Dict[str, Any]]:
    """Search a ChromaDB collection and return results with metadata."""
    kwargs = {"query_texts": [query], "n_results": n_results}
    if where:
        kwargs["where"] = where

    start = time.time()
    try:
        results = collection.query(**kwargs)
    except Exception as exc:
        latency_ms = round((time.time() - start) * 1000, 1)
        debug(f"ChromaDB search error: {exc}")
        _rag_logger.error(json.dumps({
            "event": "rag_operation",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operation": "search",
            "collection": getattr(collection, "name", "unknown"),
            "status": "error",
            "latency_ms": latency_ms,
            "error": str(exc)[:200],
            **_log_context(),
        }))
        return []

    latency_ms = round((time.time() - start) * 1000, 1)
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    _rag_logger.info(json.dumps({
        "event": "rag_operation",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "operation": "search",
        "collection": getattr(collection, "name", "unknown"),
        "status": "success",
        "latency_ms": latency_ms,
        "result_count": len(documents),
        **_log_context(),
    }))

    return [
        {"document": doc, "metadata": meta, "distance": dist}
        for doc, meta, dist in zip(documents, metadatas, distances)
    ]


def upsert_jobs(collection, jobs: List[Dict[str, Any]]):
    """Upsert job listings into the jobs ChromaDB collection."""
    if not jobs:
        return

    documents = []
    metadatas = []
    ids = []
    for i, job in enumerate(jobs):
        doc = f"{job.get('title', '')} at {job.get('company', '')}. {job.get('description', '')}. Keywords: {', '.join(job.get('keywords', []))}"
        documents.append(doc)
        metadatas.append({
            "title": job.get("title", ""),
            "company": job.get("company", ""),
            "location": job.get("location", ""),
            "source": job.get("source", "mock"),
        })
        ids.append(f"job_{i}")

    start = time.time()
    try:
        collection.upsert(documents=documents, metadatas=metadatas, ids=ids)
        latency_ms = round((time.time() - start) * 1000, 1)
        debug(f"Upserted {len(documents)} jobs into ChromaDB")
        _rag_logger.info(json.dumps({
            "event": "rag_operation",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operation": "upsert",
            "collection": getattr(collection, "name", "unknown"),
            "status": "success",
            "latency_ms": latency_ms,
            "document_count": len(documents),
            **_log_context(),
        }))
    except Exception as exc:
        latency_ms = round((time.time() - start) * 1000, 1)
        debug(f"ChromaDB upsert error: {exc}")
        _rag_logger.error(json.dumps({
            "event": "rag_operation",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operation": "upsert",
            "collection": getattr(collection, "name", "unknown"),
            "status": "error",
            "latency_ms": latency_ms,
            "error": str(exc)[:200],
            **_log_context(),
        }))
