"""
RepoScout REST API Routes.
Exposes endpoints for system health verification, natural-language query understanding,
and GitHub repository search queries.
Coordinates the Query Service and GitHub Service pipeline.
"""

import asyncio
from typing import Optional, Dict
from fastapi import APIRouter, HTTPException, Query, status

from app.core.config import get_settings
from app.schemas.health import (
    HealthResponse,
    SystemStatusResponse,
    GitHubStatus,
    CacheStatus,
    LLMStatus
)
from app.schemas.repository import (
    RepositoryItem,
    SearchResponse,
    RankedSearchRequest,
    RankedSearchResponse,
    RankedRepositoryItem
)
from app.schemas.query import QueryUnderstandRequest, StructuredRequirements
from app.schemas.analysis import RepositoryAnalysisResponse
from app.services import (
    cache_service,
    query_service,
    github_service,
    ranking_service,
    analysis_service,
    GitHubRateLimitError,
    GitHubAuthError,
    GitHubNetworkError,
    GitHubAPIError,
)

router = APIRouter(prefix="/api", tags=["RepoScout API"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Returns the operational status of the RepoScout backend service."
)
async def get_health() -> HealthResponse:
    """
    Health check endpoint.
    Strictly returns {"status": "ok", "service": "reposcout"}
    """
    return HealthResponse(status="ok", service="reposcout")


@router.get(
    "/system/status",
    response_model=SystemStatusResponse,
    summary="System Diagnostics & Status",
    description="Returns live status of GitHub API authentication/quotas, cache backend, and LLM configuration."
)
async def get_system_status() -> SystemStatusResponse:
    """Returns live GitHub quota info, active cache metrics, and LLM configuration."""
    gh_info = await github_service.get_status_info()
    cache_info = cache_service.get_stats()
    settings = get_settings()

    return SystemStatusResponse(
        status="ok",
        service="reposcout",
        github=GitHubStatus(**gh_info),
        cache=CacheStatus(**cache_info),
        llm=LLMStatus(
            provider=settings.LLM_PROVIDER,
            active_engine="openai" if settings.OPENAI_API_KEY else "gemini" if settings.GEMINI_API_KEY else "deterministic_fallback"
        )
    )


@router.post(
    "/cache/clear",
    summary="Clear Cache",
    description="Flushes all active cache entries from in-memory or Redis storage."
)
async def clear_cache():
    """Flushes all active cache entries from in-memory or Redis storage."""
    cache_service.clear()
    return {"status": "ok", "message": "Cache successfully cleared"}


@router.post(
    "/query/understand",
    response_model=StructuredRequirements,
    summary="Natural Language Query Understanding",
    description="Decomposes a developer's natural language requirement into structured search entities."
)
async def understand_query(payload: QueryUnderstandRequest) -> StructuredRequirements:
    """
    Query understanding endpoint.
    Transforms natural language into structured technical requirements:
    - keywords
    - languages
    - frameworks
    - libraries
    - databases
    - project_type
    - difficulty
    - requirements
    """
    query = (payload.query or "").strip()
    if not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query field must not be empty."
        )

    cache_key = f"query_understand:{query.lower()}"
    cached = cache_service.get(cache_key)
    if cached:
        return StructuredRequirements(**cached)

    try:
        structured = await query_service.understand_query(query)
        cache_service.set(cache_key, structured.model_dump(), ttl_seconds=600)
        return structured
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query understanding failed: {str(exc)}"
        )


@router.get(
    "/search",
    response_model=SearchResponse,
    summary="Search Repositories",
    description="Discovers GitHub repositories matching a natural language requirement."
)
async def search_repositories(
    q: Optional[str] = Query(
        None,
        description="Natural language search requirement (e.g. 'I want a beginner RAG project using Python and LangChain')",
        examples=["I want a beginner RAG project using Python and LangChain"]
    )
) -> SearchResponse:
    """
    Repository discovery search endpoint.
    Executes the complete pipeline:
    User query -> Query Service -> Structured requirements -> GitHub search query -> GitHub repositories.
    """
    # Validation: reject missing or empty/whitespace queries
    if not q or not q.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query parameter 'q' must not be empty."
        )

    clean_query = q.strip()

    # 1. Pipeline Step: Query Understanding & Decomposition
    structured = await query_service.understand_query(clean_query)
    target_github_query = structured.github_search_query or clean_query

    cache_key = f"github_search:{target_github_query.lower()}"

    # 2. Check Cache Layer to conserve rate limits
    cached_payload = cache_service.get(cache_key)
    if cached_payload:
        return SearchResponse(**cached_payload)

    # 3. Pipeline Step: Query GitHub REST API
    try:
        raw_candidates, total_count = await github_service.search_repositories(target_github_query)

        # Fallback: if transformed query returned 0 results, retry with cleaned keywords
        if total_count == 0 and target_github_query != clean_query:
            raw_candidates, total_count = await github_service.search_repositories(clean_query)

    except GitHubRateLimitError as err:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=err.message
        )
    except GitHubAuthError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=err.message
        )
    except GitHubNetworkError as err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=err.message
        )
    except GitHubAPIError as err:
        raise HTTPException(
            status_code=err.status_code if 400 <= err.status_code <= 599 else status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=err.message
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during search: {str(exc)}"
        )

    # 4. Format into API schema models
    items = [
        RepositoryItem(
            name=repo.name,
            full_name=repo.full_name,
            owner=repo.owner,
            owner_avatar_url=repo.owner_avatar_url,
            description=repo.description or "",
            url=repo.html_url,
            html_url=repo.html_url,
            clone_url=repo.clone_url or "",
            stars=repo.stars,
            forks=repo.forks,
            language=repo.language,
            topics=repo.topics,
            updated_at=repo.updated_at,
            created_at=repo.created_at,
            open_issues=repo.open_issues,
            default_branch=repo.default_branch,
            match_score=repo.match_score,
            github_url=repo.html_url,
            match_percentage=repo.match_percentage
        )
        for repo in raw_candidates
    ]

    response_data = {
        "query": clean_query,
        "total_count": total_count,
        "results": [item.model_dump() for item in items]
    }

    # Store in cache (3 minutes TTL)
    cache_service.set(cache_key, response_data, ttl_seconds=180)

    return SearchResponse(
        query=clean_query,
        total_count=total_count,
        results=items
    )


@router.get(
    "/repository/analyze",
    response_model=RepositoryAnalysisResponse,
    summary="Analyze Repository Architecture & Tech Stack",
    description="Inspects GitHub metadata, README, file tree, and dependency manifests to analyze a repository."
)
async def analyze_repository(
    repo: str = Query(..., description="Repository full identifier 'owner/name' or repository name", examples=["infiniflow/ragflow"]),
    owner: Optional[str] = Query(None, description="Repository owner login (optional if repo is formatted as 'owner/name')", examples=["infiniflow"]),
    refresh: bool = Query(False, description="Force fresh analysis bypassing cache")
) -> RepositoryAnalysisResponse:
    """
    Analyzes repository architecture, tech stack, documentation quality,
    difficulty level, strengths, and limitations using factual metadata, README,
    and dependency manifests.
    """
    clean_repo_input = repo.strip()
    if not clean_repo_input:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Repository parameter 'repo' cannot be empty."
        )

    if owner and owner.strip():
        clean_owner = owner.strip()
        clean_name = clean_repo_input
    elif "/" in clean_repo_input:
        parts = clean_repo_input.split("/", 1)
        clean_owner = parts[0].strip()
        clean_name = parts[1].strip()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide repository in 'owner/name' format or supply the 'owner' query parameter."
        )

    if not clean_owner or not clean_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both owner and repository name are required."
        )

    try:
        analysis = await analysis_service.analyze_repository(clean_owner, clean_name, refresh=refresh)
        return analysis
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err)
        )
    except PermissionError as err:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(err)
        )
    except RuntimeError as err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(err)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Repository analysis failed: {str(exc)}"
        )


@router.post(
    "/search/ranked",
    response_model=RankedSearchResponse,
    summary="Ranked Repository Search",
    description="Executes the full pipeline: Natural-language query -> Query understanding -> GitHub search -> Repository analysis -> Intelligent ranking -> Sorted results with score breakdown."
)
async def search_ranked_repositories(payload: RankedSearchRequest) -> RankedSearchResponse:
    """
    Intelligent repository search and ranking endpoint.
    Pipeline:
    1. Understand user's natural language requirements (project type, tech stack, difficulty, criteria).
    2. Convert into high-precision GitHub search syntax and retrieve candidates.
    3. Analyze top candidate repositories (README, dependencies, architecture).
    4. Score candidates across 7 weighted dimensions (requirements 30%, tech 20%, arch 20%, doc 10%, act 10%, pop 5%, comp 5%).
    5. Return explainable results sorted by match score descending.
    """
    clean_query = (payload.query or "").strip()
    if not clean_query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query field must not be empty."
        )

    # Fast Path: Check Ranking Cache
    cached_payload = cache_service.get_ranking(clean_query)
    if not cached_payload:
        cache_key = f"ranked_search:{clean_query.lower()}"
        cached_payload = cache_service.get(cache_key)

    if cached_payload:
        return RankedSearchResponse(**cached_payload)

    # 1. Natural Language Query Understanding
    try:
        structured = await query_service.understand_query(clean_query)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query understanding failed: {str(exc)}"
        )

    target_github_query = structured.github_search_query or clean_query

    # 2. Stage 1: Candidate Discovery via GitHub REST API
    try:
        raw_candidates, total_count = await github_service.search_repositories(target_github_query)

        # Fallback if transformed search returned no candidates
        if total_count == 0 and target_github_query != clean_query:
            raw_candidates, total_count = await github_service.search_repositories(clean_query)

    except GitHubRateLimitError as err:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=err.message
        )
    except GitHubAuthError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=err.message
        )
    except GitHubNetworkError as err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=err.message
        )
    except GitHubAPIError as err:
        raise HTTPException(
            status_code=err.status_code if 400 <= err.status_code <= 599 else status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=err.message
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(exc)}"
        )

    if not raw_candidates:
        empty_response = RankedSearchResponse(
            query=clean_query,
            total_count=0,
            results=[],
            structured=structured
        )
        cache_service.set_ranking(clean_query, empty_response.model_dump())
        return empty_response

    # 3. Two-Stage Search Architecture
    # Stage 1: Lightweight filtering on candidate metadata to prioritize top candidates
    def _preliminary_score(repo: Any) -> float:
        score = 0.0
        text = f"{repo.name.lower()} {(repo.description or '').lower()} {' '.join(repo.topics).lower()}"
        for req in structured.requirements:
            if req.lower() in text:
                score += 15.0
        for kw in structured.keywords:
            if kw.lower() in text:
                score += 10.0
        for lang in structured.languages:
            if repo.language and repo.language.lower() == lang.lower():
                score += 15.0
            elif lang.lower() in text:
                score += 8.0
        for fw in structured.frameworks:
            if fw.lower() in text:
                score += 12.0
        for lib in structured.libraries:
            if lib.lower() in text:
                score += 10.0
        if repo.stars:
            score += min(10.0, repo.stars / 500.0)
        return score

    # Select top candidates for deep analysis (default top 5, avoiding expensive calls on all 30)
    top_candidates_limit = 5
    sorted_for_deep = sorted(raw_candidates, key=_preliminary_score, reverse=True)
    candidates_to_analyze = sorted_for_deep[:top_candidates_limit]

    # Stage 2: Deep Analysis only for selected top candidates (executed in parallel)
    async def _safe_analyze(repo_cand):
        repo_id = repo_cand.full_name or f"{repo_cand.owner}/{repo_cand.name}"
        try:
            analysis = await analysis_service.analyze_repository(repo_cand.owner, repo_cand.name)
            return repo_id, analysis
        except Exception:
            return repo_id, None

    analysis_tasks = [_safe_analyze(repo) for repo in candidates_to_analyze]
    analysis_results = await asyncio.gather(*analysis_tasks, return_exceptions=True)

    analyses_map: Dict[str, RepositoryAnalysisResponse] = {}
    for res in analysis_results:
        if isinstance(res, tuple) and res[1] is not None:
            analyses_map[res[0]] = res[1]

    # 4. Intelligent Multi-Factor Scoring & Ranking across all candidates
    try:
        ranked_results = ranking_service.evaluate_and_rank_repositories(
            repositories=raw_candidates,
            structured=structured,
            analyses=analyses_map
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ranking calculation failed: {str(exc)}"
        )

    response = RankedSearchResponse(
        query=clean_query,
        total_count=total_count,
        results=ranked_results,
        structured=structured
    )

    # Cache ranking results with domain key: ranking:<query_hash>
    cache_service.set_ranking(clean_query, response.model_dump())
    cache_service.set(f"ranked_search:{clean_query.lower()}", response.model_dump(), ttl_seconds=600)

    return response
