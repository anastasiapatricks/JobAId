"""ChromaDB search and upsert tools for RAG."""

from typing import List, Dict, Any, Optional
from utils import debug


def search_collection(collection, query: str, n_results: int = 5, where: Optional[dict] = None) -> List[Dict[str, Any]]:
    """Search a ChromaDB collection and return results with metadata."""
    kwargs = {"query_texts": [query], "n_results": n_results}
    if where:
        kwargs["where"] = where

    try:
        results = collection.query(**kwargs)
    except Exception as exc:
        debug(f"ChromaDB search error: {exc}")
        return []

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

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

    try:
        collection.upsert(documents=documents, metadatas=metadatas, ids=ids)
        debug(f"Upserted {len(documents)} jobs into ChromaDB")
    except Exception as exc:
        debug(f"ChromaDB upsert error: {exc}")
