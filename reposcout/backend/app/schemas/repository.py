"""
Repository API schemas.
Serializers and validators for incoming queries, repository items,
and ranked/explainable search responses.
"""

from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from app.schemas.query import StructuredRequirements


class ScoreBreakdown(BaseModel):
    """
    Component-by-component scoring breakdown matching the configurable weighting model:
    Requirement match: 30%
    Technology match: 20%
    Architecture match: 20%
    Documentation quality: 10%
    Repository activity: 10%
    Popularity: 5%
    Project completeness: 5%
    """
    requirement_match: int = Field(..., ge=0, le=30, description="Points from user requirements match (0-30)")
    technology_match: int = Field(..., ge=0, le=20, description="Points from programming languages & tech stack (0-20)")
    architecture_match: int = Field(..., ge=0, le=20, description="Points from architecture components & project type (0-20)")
    documentation: int = Field(..., ge=0, le=10, description="Points from README & documentation completeness (0-10)")
    activity: int = Field(..., ge=0, le=10, description="Points from recent updates & commit freshness (0-10)")
    popularity: int = Field(..., ge=0, le=5, description="Points from stars and community adoption (0-5)")
    completeness: int = Field(..., ge=0, le=5, description="Points from tests, docker, and manifests (0-5)")


class RepositoryItem(BaseModel):
    """
    Public representation of a GitHub repository returned to the frontend.
    """
    name: str = Field(..., description="Repository name")
    full_name: str = Field(default="", description="Full repository name (owner/name)")
    owner: str = Field(..., description="Repository owner / organization login")
    owner_avatar_url: Optional[str] = Field(default=None, description="Repository owner avatar URL")
    description: Optional[str] = Field(default="", description="Repository description")
    url: str = Field(..., description="GitHub repository web URL")
    html_url: str = Field(..., description="GitHub repository web URL")
    clone_url: Optional[str] = Field(default="", description="Git clone URL")
    stars: int = Field(default=0, ge=0, description="Star count")
    forks: int = Field(default=0, ge=0, description="Fork count")
    language: Optional[str] = Field(default=None, description="Primary programming language")
    topics: List[str] = Field(default_factory=list, description="Repository topic tags")
    updated_at: Optional[str] = Field(default=None, description="Last update timestamp (ISO 8601)")
    created_at: Optional[str] = Field(default=None, description="Creation timestamp (ISO 8601)")
    open_issues: Optional[int] = Field(default=0, ge=0, description="Open issues count")
    default_branch: Optional[str] = Field(default="main", description="Default branch")
    match_score: Optional[int] = Field(default=None, ge=0, le=100, description="Calculated match score (0-100)")
    github_url: str = Field(..., description="Full GitHub web URL")
    match_percentage: Optional[int] = Field(default=None, description="Match percentage alias")


class RankedRepositoryItem(RepositoryItem):
    """
    Ranked repository item with explainable scoring details:
    - match_score: 0-100 total score
    - score_breakdown: points per scoring category
    - matches: list of satisfied requirements
    - missing: list of unsatisfied requirements
    - why_it_matches: concise human-readable summary
    """
    score_breakdown: Optional[ScoreBreakdown] = Field(default=None, description="Detailed score points per category")
    matches: List[str] = Field(default_factory=list, description="Requirements and technical criteria successfully satisfied")
    missing: List[str] = Field(default_factory=list, description="Requirements or criteria not satisfied or missing")
    why_it_matches: Optional[str] = Field(default="", description="Explainable summary of why this repository matches")


class SearchResponse(BaseModel):
    """Search endpoint response payload."""
    query: str = Field(..., description="Original search query")
    total_count: int = Field(..., description="Total repository count found")
    results: List[RepositoryItem] = Field(..., description="List of matched repository cards")
    structured: Optional[StructuredRequirements] = Field(default=None, description="Structured query requirements")


class RankedSearchRequest(BaseModel):
    """Input payload for POST /api/search/ranked."""
    query: str = Field(..., description="Natural language search query or requirement", min_length=1)


class RankedSearchResponse(BaseModel):
    """Response payload for POST /api/search/ranked."""
    query: str = Field(..., description="Original natural-language search query")
    total_count: int = Field(..., description="Total matching repositories")
    results: List[RankedRepositoryItem] = Field(..., description="Ranked repositories sorted by match score descending")
    structured: Optional[StructuredRequirements] = Field(default=None, description="Extracted structured requirements")
