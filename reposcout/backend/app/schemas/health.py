"""Health and system diagnostics schemas."""
from typing import Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response schema matching project requirements."""
    status: str = Field(default="ok", json_schema_extra={"example": "ok"})
    service: str = Field(default="reposcout", json_schema_extra={"example": "reposcout"})


class GitHubStatus(BaseModel):
    """Live status and quota details for GitHub REST API v3."""
    authenticated: bool = False
    user: Optional[str] = None
    core_remaining: Optional[int] = None
    core_limit: Optional[int] = None
    search_remaining: Optional[int] = None
    search_limit: Optional[int] = None
    token_configured: bool = False


class CacheStatus(BaseModel):
    """Diagnostics for cache backend and active memory storage."""
    backend: str = "in-memory"
    total_keys: int = 0


class LLMStatus(BaseModel):
    """Configuration status for natural language query understanding provider."""
    provider: str = "auto"
    active_engine: str = "deterministic"


class SystemStatusResponse(BaseModel):
    """Complete system diagnostics response."""
    status: str = "ok"
    service: str = "reposcout"
    github: GitHubStatus
    cache: CacheStatus
    llm: LLMStatus
