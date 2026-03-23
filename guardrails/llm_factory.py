"""LLM factory for multi-provider support (OpenAI, LM Studio, etc.)."""

from typing import Optional
from langchain_openai import ChatOpenAI
from config.settings import settings


def get_llm(
    model: str,
    temperature: float,
    task_type: Optional[str] = None
) -> ChatOpenAI:
    """Factory function to instantiate appropriate LLM provider.

    Args:
        model: Model name (from get_model_for_task, ignored for LM Studio)
        temperature: Temperature parameter (0-1)
        task_type: Optional task type hint for logging

    Returns:
        ChatOpenAI instance configured for selected provider
    """
    provider = settings.llm_provider.lower()

    if provider == "lmstudio":
        # LM Studio: uses OpenAI-compatible API, ignores model name
        return ChatOpenAI(
            model="lmstudio",  # Placeholder, LM Studio uses loaded model
            base_url=settings.lmstudio_base_url,
            api_key="not-needed",  # LM Studio doesn't require authentication
            temperature=temperature,
        )
    else:
        # OpenAI (default)
        kwargs = {
            "model": model,
            "api_key": settings.openai_api_key,
            "temperature": temperature,
        }

        # Only add base_url if explicitly configured
        if settings.openai_base_url:
            kwargs["base_url"] = settings.openai_base_url

        return ChatOpenAI(**kwargs)
