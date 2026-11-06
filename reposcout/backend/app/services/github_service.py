"""
GitHub Repository Search Service.
Directly interfaces with the GitHub REST API (v3) to search repositories
and extract rich metadata. Handles authentication, rate limiting, and network errors gracefully.
"""

import time
from typing import List, Optional, Tuple, Dict, Any
import httpx

from app.models.repository import RepositoryModel
from app.core.config import get_settings
from app.services.cache_service import cache_service


class GitHubAPIError(Exception):
    """Base exception for GitHub API errors."""
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class GitHubRateLimitError(GitHubAPIError):
    """Raised when GitHub API rate limits are exceeded."""
    def __init__(self, message: str, reset_timestamp: Optional[int] = None):
        super().__init__(message, status_code=429)
        self.reset_timestamp = reset_timestamp


class GitHubAuthError(GitHubAPIError):
    """Raised when GitHub authentication credentials are invalid."""
    def __init__(self, message: str):
        super().__init__(message, status_code=401)


class GitHubNetworkError(GitHubAPIError):
    """Raised when network connectivity to GitHub fails."""
    def __init__(self, message: str):
        super().__init__(message, status_code=503)


class GitHubService:
    """Service encapsulating GitHub REST API v3 operations."""

    SEARCH_URL = "https://api.github.com/search/repositories"

    def __init__(self, token: Optional[str] = None):
        settings = get_settings()
        self.token = token if token is not None else settings.get_github_token()

    def _get_headers(self) -> Dict[str, str]:
        """Construct standard GitHub REST API headers."""
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "RepoScout-Discovery-Extension/1.0",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def search_repositories(
        self,
        query: str,
        page: int = 1,
        per_page: int = 15
    ) -> Tuple[List[RepositoryModel], int]:
        """
        Executes a repository search against GitHub REST API v3.

        Args:
            query: Natural language or keyword search query.
            page: Page number (1-based).
            per_page: Number of repositories to fetch (default 15).

        Returns:
            Tuple of (list of RepositoryModel, total_count).

        Raises:
            GitHubRateLimitError: If API rate limits are hit.
            GitHubAuthError: If provided GITHUB_TOKEN is rejected.
            GitHubNetworkError: If GitHub is unreachable.
            GitHubAPIError: For other unexpected API responses.
        """
        clean_query = query.strip()
        if not clean_query:
            return [], 0

        cache_sub_key = f"{clean_query}:p{page}:l{per_page}"
        cached = cache_service.get_github_search(cache_sub_key)
        if cached:
            return (
                [RepositoryModel(**r) for r in cached.get("results", [])],
                cached.get("total_count", 0)
            )

        headers = self._get_headers()
        params = {
            "q": clean_query,
            "page": max(1, page),
            "per_page": min(50, max(1, per_page)),
        }

        settings = get_settings()
        timeout = settings.GITHUB_REQUEST_TIMEOUT

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(
                    self.SEARCH_URL,
                    headers=headers,
                    params=params
                )
        except httpx.TimeoutException:
            raise GitHubNetworkError("GitHub API request timed out. Please try again.")
        except httpx.RequestError as exc:
            raise GitHubNetworkError(f"Network error communicating with GitHub: {str(exc)}")

        # Handle rate limiting (HTTP 403 or 429)
        if response.status_code in (403, 429):
            remaining = response.headers.get("x-ratelimit-remaining", "")
            reset_ts_raw = response.headers.get("x-ratelimit-reset")
            reset_ts = int(reset_ts_raw) if reset_ts_raw and reset_ts_raw.isdigit() else None

            # Calculate reset delay in seconds if available
            delay_msg = ""
            if reset_ts:
                seconds_left = max(0, int(reset_ts - time.time()))
                delay_msg = f" Rate limit resets in {seconds_left} seconds."

            body_msg = ""
            try:
                body = response.json()
                body_msg = body.get("message", "")
            except Exception:
                pass

            if "rate limit" in body_msg.lower() or remaining == "0":
                token_hint = (
                    " Add a personal GITHUB_TOKEN in backend/.env to increase your limit from 10 to 30 requests/min."
                    if not self.token else ""
                )
                raise GitHubRateLimitError(
                    f"GitHub API rate limit exceeded.{delay_msg}{token_hint}",
                    reset_timestamp=reset_ts
                )

            # If 403 but not rate limit, could be permissions or abuse detection
            raise GitHubAPIError(f"GitHub access forbidden (403): {body_msg or 'Access restricted'}", 403)

        # Handle bad credentials (HTTP 401)
        if response.status_code == 401:
            raise GitHubAuthError(
                "GitHub authentication failed. Please verify the GITHUB_TOKEN in your backend/.env file."
            )

        # Handle unprocessable query (HTTP 422)
        if response.status_code == 422:
            raise GitHubAPIError(
                f"GitHub could not process query '{clean_query}'. Please try different keywords.",
                422
            )

        # General error handling
        if not response.is_success:
            raise GitHubAPIError(
                f"GitHub API returned error {response.status_code}: {response.text[:200]}",
                response.status_code
            )

        # Parse success payload
        try:
            data = response.json()
        except Exception as exc:
            raise GitHubAPIError(f"Failed to parse GitHub response: {str(exc)}")

        raw_items = data.get("items", [])
        total_count = data.get("total_count", len(raw_items))

        repositories: List[RepositoryModel] = []
        for item in raw_items:
            owner_info = item.get("owner") or {}
            owner_login = owner_info.get("login") or "unknown"
            owner_avatar = owner_info.get("avatar_url")
            html_url = item.get("html_url") or ""

            repo = RepositoryModel(
                name=item.get("name") or "unknown",
                full_name=item.get("full_name") or f"{owner_login}/{item.get('name', '')}",
                owner=owner_login,
                owner_avatar_url=owner_avatar,
                description=item.get("description") or "",
                html_url=html_url,
                clone_url=item.get("clone_url") or (f"{html_url}.git" if html_url else ""),
                stars=item.get("stargazers_count", 0),
                forks=item.get("forks_count", 0),
                language=item.get("language"),
                topics=item.get("topics") or [],
                updated_at=item.get("updated_at"),
                created_at=item.get("created_at"),
                open_issues=item.get("open_issues_count", 0),
                default_branch=item.get("default_branch") or "main",
                match_score=None  # Explicitly null per requirements (no LLM/ranking yet)
            )
            repositories.append(repo)

        # Cache search query results
        cache_service.set_github_search(
            cache_sub_key,
            {
                "results": [r.model_dump() for r in repositories],
                "total_count": total_count
            }
        )

        # Cache individual repository metadata for instant lookup
        for r in repositories:
            cache_service.set_repository(r.owner, r.name, r.model_dump())

        return repositories, total_count

    async def get_status_info(self) -> Dict[str, Any]:
        """
        Retrieves live GitHub rate limit quota and authenticated username.
        Gracefully handles network errors and unauthenticated states.
        """
        headers = self._get_headers()
        info: Dict[str, Any] = {
            "authenticated": bool(self.token),
            "user": None,
            "core_remaining": None,
            "core_limit": None,
            "search_remaining": None,
            "search_limit": None,
            "token_configured": bool(self.token),
        }

        try:
            settings = get_settings()
            timeout = min(settings.GITHUB_REQUEST_TIMEOUT, 4.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                r_rate = await client.get("https://api.github.com/rate_limit", headers=headers)
                if r_rate.status_code == 200:
                    resources = r_rate.json().get("resources", {})
                    core = resources.get("core", {})
                    search = resources.get("search", {})
                    info["core_remaining"] = core.get("remaining")
                    info["core_limit"] = core.get("limit")
                    info["search_remaining"] = search.get("remaining")
                    info["search_limit"] = search.get("limit")

                if self.token:
                    r_user = await client.get("https://api.github.com/user", headers=headers)
                    if r_user.status_code == 200:
                        info["user"] = r_user.json().get("login")
                        info["authenticated"] = True
        except Exception:
            pass

        return info


# Global service instance
github_service = GitHubService()
