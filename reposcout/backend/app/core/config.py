"""
Configuration settings for RepoScout Backend.
Loads environment variables from .env with fallback defaults.
"""

from functools import lru_cache
from typing import List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "RepoScout Backend API"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # CORS configuration
    CORS_ORIGINS: Union[str, List[str]] = "http://localhost:5173,http://127.0.0.1:5173,chrome-extension://*"

    # GitHub API configuration
    GITHUB_TOKEN: str = ""
    GITHUB_API_TOKEN: str = ""

    # LLM Provider configuration
    LLM_PROVIDER: str = "auto"  # 'auto', 'openai', 'gemini', 'ollama', 'fallback'
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # Cache Configuration & TTL Values (seconds)
    # Storage system can be local in-memory or Redis
    REDIS_URL: str = ""
    CACHE_TTL_GITHUB_SEARCH: int = 600       # 10 minutes
    CACHE_TTL_REPOSITORY: int = 1800          # 30 minutes
    CACHE_TTL_ANALYSIS: int = 3600            # 1 hour
    CACHE_TTL_RANKING: int = 600              # 10 minutes
    CACHE_TTL_QUERY_UNDERSTAND: int = 1800    # 30 minutes
    CACHE_TTL_README: int = 3600              # 1 hour

    # Performance & Two-Stage Search Configuration
    TWO_STAGE_TOP_CANDIDATES: int = 5         # Only deeply inspect top 5 candidates
    GITHUB_REQUEST_TIMEOUT: float = 8.0       # Timeout in seconds for GitHub API calls

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def get_github_token(self) -> str:
        """Get the GitHub personal access token, checking GITHUB_TOKEN then GITHUB_API_TOKEN."""
        token = (self.GITHUB_TOKEN or self.GITHUB_API_TOKEN or "").strip()
        # Avoid placeholder strings
        if token in ("your_github_token_here", "your_token_here"):
            return ""
        return token

    def get_cors_origins(self) -> List[str]:
        """Parse comma-separated CORS origins into a list."""
        if isinstance(self.CORS_ORIGINS, list):
            return self.CORS_ORIGINS
        if isinstance(self.CORS_ORIGINS, str):
            return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
        return ["*"]


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()

