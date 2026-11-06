"""
Repository Domain Model.
Internal data structures representing repository entities across service layers.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class RepositoryModel:
    """Domain model representing a discovered GitHub repository."""
    name: str
    full_name: str
    owner: str
    owner_avatar_url: Optional[str] = None
    description: Optional[str] = ""
    html_url: str = ""
    clone_url: Optional[str] = ""
    stars: int = 0
    forks: int = 0
    language: Optional[str] = None
    topics: List[str] = field(default_factory=list)
    updated_at: Optional[str] = None
    created_at: Optional[str] = None
    open_issues: int = 0
    default_branch: str = "main"
    match_score: Optional[float] = None

    # Backward-compatible properties
    @property
    def url(self) -> str:
        return self.html_url

    @property
    def github_url(self) -> str:
        return self.html_url

    @property
    def match_percentage(self) -> Optional[int]:
        if self.match_score is not None:
            return int(round(self.match_score))
        return None

    def to_dict(self) -> dict:
        from dataclasses import asdict
        return asdict(self)

    def model_dump(self) -> dict:
        return self.to_dict()
