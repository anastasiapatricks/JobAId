"""OpenAI embedding function for ChromaDB."""

from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from config.settings import settings


def get_embedding_function() -> OpenAIEmbeddingFunction:
    """Return an OpenAI embedding function for ChromaDB collections."""
    return OpenAIEmbeddingFunction(
        api_key=settings.openai_api_key,
        model_name=settings.embedding_model,
    )
