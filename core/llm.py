import logging
from typing import Union
from functools import lru_cache

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel

from .config import settings, LLMProvider

logger = logging.getLogger(__name__)

class LLMInitializationError(Exception):
    """Raised when LLM initialization fails."""
    pass

@lru_cache(maxsize=1)
def get_llm() -> BaseChatModel:
    """
    Initializes and returns the LLM instance based on configuration.

    This function is cached to ensure only one LLM instance is created per application run.

    Returns:
        BaseChatModel: Configured LLM instance

    Raises:
        LLMInitializationError: If LLM initialization fails
        ValueError: If provider or configuration is invalid
    """
    try:
        provider = settings.llm_provider
        model_name = settings.get_model_name()
        api_key = settings.get_required_api_key()

        logger.info(f"Initializing {provider.value} LLM with model: {model_name}")

        llm_config = {
            "model": model_name,
            "temperature": settings.temperature,
            "request_timeout": settings.request_timeout,
            "max_retries": settings.max_retries,
        }

        if provider == LLMProvider.OPENAI:
            llm = ChatOpenAI(
                api_key=api_key,
                **llm_config
            )
        elif provider == LLMProvider.ANTHROPIC:
            llm = ChatAnthropic(
                api_key=api_key,
                **llm_config
            )
        elif provider == LLMProvider.GOOGLE:
            llm = ChatGoogleGenerativeAI(
                google_api_key=api_key,
                **llm_config
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

        logger.info(f"Successfully initialized {provider.value} LLM")
        return llm

    except Exception as e:
        logger.error(f"Failed to initialize LLM: {e}")
        raise LLMInitializationError(f"Failed to initialize {provider.value} LLM: {e}") from e

def clear_llm_cache():
    """Clear the LLM cache. Useful for testing or configuration changes."""
    get_llm.cache_clear()
    logger.info("LLM cache cleared")

def get_llm_info() -> dict:
    """Get information about the current LLM configuration."""
    return {
        "provider": settings.llm_provider.value,
        "model": settings.get_model_name(),
        "temperature": settings.temperature,
        "max_retries": settings.max_retries,
        "request_timeout": settings.request_timeout,
    }