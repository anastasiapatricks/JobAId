"""ChromaDB collections initialization."""

import chromadb
from config.settings import settings
from vectordb.embeddings import get_embedding_function


_client = None


def get_chroma_client() -> chromadb.ClientAPI:
    """Return a persistent ChromaDB client (singleton)."""
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    return _client


def get_jobs_collection():
    """Job listings collection — populated dynamically per run."""
    client = get_chroma_client()
    return client.get_or_create_collection(
        name="jobs",
        embedding_function=get_embedding_function(),
        metadata={"description": "Job listings for semantic matching"},
    )


def get_courses_collection():
    """Course catalog collection — seeded from data/seed_courses.json."""
    client = get_chroma_client()
    return client.get_or_create_collection(
        name="courses_and_resources",
        embedding_function=get_embedding_function(),
        metadata={"description": "Course catalog for upskilling recommendations"},
    )


def get_trends_collection():
    """Industry trends collection — seeded from data/seed_industry_trends.json."""
    client = get_chroma_client()
    return client.get_or_create_collection(
        name="industry_trends",
        embedding_function=get_embedding_function(),
        metadata={"description": "Industry trend paragraphs"},
    )
