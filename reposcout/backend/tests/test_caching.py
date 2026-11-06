"""
Performance & Caching Architecture Tests.
Verifies:
- BaseCacheBackend, InMemoryCacheBackend, and RedisCacheBackend fallback
- Domain key generators (github_search, repository, analysis, readme, tech_detection, ranking)
- TTL expiration behavior
- Two-stage search optimization (Stage 1 lightweight filter -> Stage 2 top 5 deep analysis)
- Cached ranking fast-path
"""

import time
from unittest.mock import patch, AsyncMock
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.repository import RepositoryModel
from app.schemas.analysis import RepositoryAnalysisResponse
from app.services.cache_service import (
    CacheService,
    InMemoryCacheBackend,
    RedisCacheBackend,
    cache_service,
)

client = TestClient(app)


def test_in_memory_cache_backend_ttl():
    """Verify in-memory backend supports TTL expiration, delete, and exists."""
    backend = InMemoryCacheBackend()

    # Test set and get
    backend.set("test_key", {"data": 123}, ttl_seconds=1)
    assert backend.exists("test_key") is True
    assert backend.get("test_key") == {"data": 123}

    # Test delete
    backend.delete("test_key")
    assert backend.get("test_key") is None
    assert backend.exists("test_key") is False

    # Test TTL expiration
    backend.set("short_key", "hello", ttl_seconds=0.1)
    time.sleep(0.15)
    assert backend.get("short_key") is None


def test_redis_cache_backend_graceful_fallback():
    """Verify RedisCacheBackend falls back to in-memory cache when Redis is unavailable."""
    backend = RedisCacheBackend(redis_url="redis://nonexistent-host:6379/0")
    backend.set("fallback_key", {"val": "ok"}, ttl_seconds=60)
    assert backend.get("fallback_key") == {"val": "ok"}
    assert backend.exists("fallback_key") is True
    backend.delete("fallback_key")
    assert backend.get("fallback_key") is None


def test_domain_cache_key_conventions():
    """Verify specialized domain key generation contracts: github_search, repository, analysis, readme, tech_detection, ranking."""
    svc = CacheService(backend=InMemoryCacheBackend())

    # 1. github_search:<query>
    svc.set_github_search("RAG Python", {"count": 10})
    assert svc.get_github_search("RAG Python") == {"count": 10}
    assert svc.get("github_search:rag python") == {"count": 10}

    # 2. repository:<owner>:<repo>
    svc.set_repository("infiniflow", "ragflow", {"stars": 90000})
    assert svc.get_repository("infiniflow", "ragflow") == {"stars": 90000}
    assert svc.get("repository:infiniflow:ragflow") == {"stars": 90000}

    # 3. analysis:<owner>:<repo>
    svc.set_analysis("owner", "repo", {"project_type": "RAG"})
    assert svc.get_analysis("owner", "repo") == {"project_type": "RAG"}
    assert svc.get("analysis:owner:repo") == {"project_type": "RAG"}

    # 4. readme:<owner>:<repo>
    svc.set_readme("owner", "repo", "# Readme text")
    assert svc.get_readme("owner", "repo") == "# Readme text"
    assert svc.get("readme:owner:repo") == "# Readme text"

    # 5. tech_detection:<owner>:<repo>
    svc.set_tech_detection("owner", "repo", {"frameworks": ["FastAPI"]})
    assert svc.get_tech_detection("owner", "repo") == {"frameworks": ["FastAPI"]}
    assert svc.get("tech_detection:owner:repo") == {"frameworks": ["FastAPI"]}

    # 6. ranking:<query_hash>
    query = "beginner rag project with python"
    query_hash = svc.hash_query(query)
    svc.set_ranking(query, {"ranked": True})
    assert svc.get_ranking(query) == {"ranked": True}
    assert svc.get(f"ranking:{query_hash}") == {"ranked": True}


@patch("app.api.routes.github_service.search_repositories")
@patch("app.api.routes.analysis_service.analyze_repository")
def test_two_stage_search_limits_deep_analysis_to_top_5(mock_analyze, mock_search):
    """
    Verify performance optimization:
    GitHub returns 12 candidates, but deep analysis is only executed for top 5 candidates.
    """
    cache_service.clear()

    # Generate 12 mock repository candidates
    mock_candidates = [
        RepositoryModel(
            name=f"repo-{i}",
            full_name=f"org/repo-{i}",
            owner="org",
            description=f"RAG project {i} using Python and LangChain" if i < 5 else f"Generic tool {i}",
            html_url=f"https://github.com/org/repo-{i}",
            stars=100 * (12 - i),
            forks=10,
            language="Python" if i < 6 else "JavaScript",
            topics=["rag", "langchain"] if i < 5 else ["misc"],
            updated_at="2026-10-01T00:00:00Z"
        )
        for i in range(12)
    ]
    mock_search.return_value = (mock_candidates, 12)

    mock_analyze.return_value = RepositoryAnalysisResponse(
        repository="org/repo-0",
        technologies=["Python", "LangChain"],
        languages=["Python"],
        architecture_components=["document loading", "retrieval"],
        project_type="RAG",
        documentation_quality="High",
        difficulty="beginner",
        strengths=["Verified pipeline"],
        limitations=[]
    )

    query = "I want a beginner RAG project using Python and LangChain"
    resp = client.post("/api/search/ranked", json={"query": query})
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_count"] == 12
    assert len(data["results"]) == 12

    # Verify analyze_repository was called at most 5 times (top 5 limit)
    assert mock_analyze.call_count <= 5

    # Verify ranking cache was populated
    query_hash = cache_service.hash_query(query)
    assert cache_service.exists(f"ranking:{query_hash}") is True

    # Call again with the exact same query: should be served instantly from cache (0 search calls)
    mock_search.reset_mock()
    mock_analyze.reset_mock()

    cached_resp = client.post("/api/search/ranked", json={"query": query})
    assert cached_resp.status_code == 200
    # No backend API calls made because ranking was cached!
    assert mock_search.call_count == 0
    assert mock_analyze.call_count == 0

