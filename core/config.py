import os
from typing import Optional
from enum import Enum
from pydantic import BaseSettings, Field, validator


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    GOOGLE = "google"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class Settings(BaseSettings):
    """Application settings with validation."""

    # LLM Configuration
    llm_provider: LLMProvider = Field(
        default=LLMProvider.GOOGLE,
        env="LLM_PROVIDER",
        description="LLM provider to use"
    )

    # API Keys
    google_api_key: Optional[str] = Field(
        default=None,
        env="GOOGLE_API_KEY",
        description="Google AI API key"
    )
    openai_api_key: Optional[str] = Field(
        default=None,
        env="OPENAI_API_KEY",
        description="OpenAI API key"
    )
    anthropic_api_key: Optional[str] = Field(
        default=None,
        env="ANTHROPIC_API_KEY",
        description="Anthropic API key"
    )

    # Database Configuration
    database_url: Optional[str] = Field(
        default=None,
        env="DATABASE_URL",
        description="Database URL for SQL validation"
    )

    # Model Configuration
    google_model: str = Field(
        default="gemini-pro",
        env="GOOGLE_MODEL",
        description="Google model to use"
    )
    openai_model: str = Field(
        default="gpt-4-turbo-preview",
        env="OPENAI_MODEL",
        description="OpenAI model to use"
    )
    anthropic_model: str = Field(
        default="claude-3-sonnet-20240229",
        env="ANTHROPIC_MODEL",
        description="Anthropic model to use"
    )

    # Application Configuration
    temperature: float = Field(
        default=0.0,
        env="LLM_TEMPERATURE",
        ge=0.0,
        le=2.0,
        description="LLM temperature for response generation"
    )
    max_retries: int = Field(
        default=3,
        env="MAX_RETRIES",
        ge=0,
        le=10,
        description="Maximum number of retries for LLM calls"
    )

    # Performance Configuration
    request_timeout: int = Field(
        default=120,
        env="REQUEST_TIMEOUT",
        ge=10,
        le=600,
        description="Request timeout in seconds"
    )

    # Security Configuration
    cors_origins: str = Field(
        default="*",
        env="CORS_ORIGINS",
        description="Allowed CORS origins (comma-separated)"
    )

    @validator('llm_provider', pre=True)
    def validate_provider(cls, v):
        if isinstance(v, str):
            return v.lower()
        return v

    @validator('cors_origins')
    def parse_cors_origins(cls, v):
        if v == "*":
            return ["*"]
        return [origin.strip() for origin in v.split(",") if origin.strip()]

    def get_required_api_key(self) -> str:
        """Get the required API key for the selected provider."""
        if self.llm_provider == LLMProvider.GOOGLE:
            if not self.google_api_key:
                raise ValueError("GOOGLE_API_KEY is required when using Google provider")
            return self.google_api_key
        elif self.llm_provider == LLMProvider.OPENAI:
            if not self.openai_api_key:
                raise ValueError("OPENAI_API_KEY is required when using OpenAI provider")
            return self.openai_api_key
        elif self.llm_provider == LLMProvider.ANTHROPIC:
            if not self.anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY is required when using Anthropic provider")
            return self.anthropic_api_key
        else:
            raise ValueError(f"Unsupported provider: {self.llm_provider}")

    def get_model_name(self) -> str:
        """Get the model name for the selected provider."""
        if self.llm_provider == LLMProvider.GOOGLE:
            return self.google_model
        elif self.llm_provider == LLMProvider.OPENAI:
            return self.openai_model
        elif self.llm_provider == LLMProvider.ANTHROPIC:
            return self.anthropic_model
        else:
            raise ValueError(f"Unsupported provider: {self.llm_provider}")

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()