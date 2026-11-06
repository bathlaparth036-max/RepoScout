"""
Backend API Unit and Integration Tests.
Verifies health check, natural-language query understanding, search endpoint,
GitHub service integration, and error handling.
"""

from unittest.mock import patch, AsyncMock
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.repository import RepositoryModel
from app.services.github_service import GitHubRateLimitError, GitHubNetworkError

client = TestClient(app)


def test_health_endpoint():
    """Verify GET /api/health returns exact required contract."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data == {
        "status": "ok",
        "service": "reposcout"
    }


def test_query_understand_endpoint():
    """Verify POST /api/query/understand returns structured requirements schema."""
    payload = {
        "query": "I want a beginner RAG project using Python, LangChain and FAISS"
    }
    response = client.post("/api/query/understand", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["original_query"] == "I want a beginner RAG project using Python, LangChain and FAISS"
    assert "Python" in data["languages"]
    assert "LangChain" in data["frameworks"]
    assert "FAISS" in data["libraries"]
    assert data["project_type"] == "RAG"
    assert data["difficulty"] == "beginner"
    assert isinstance(data["requirements"], list)
    assert len(data["requirements"]) >= 3
    assert "github_search_query" in data


def test_query_understand_empty_input():
    """Verify POST /api/query/understand rejects empty query."""
    response = client.post("/api/query/understand", json={"query": "  "})
    assert response.status_code == 400


def test_search_endpoint_empty_query():
    """Verify empty search query returns 400 Bad Request."""
    response = client.get("/api/search?q=")
    assert response.status_code == 400
    assert "Search query parameter 'q' must not be empty." in response.json()["detail"]

    whitespace_response = client.get("/api/search?q=   ")
    assert whitespace_response.status_code == 400


def test_search_endpoint_missing_param():
    """Verify missing 'q' param returns 400 Bad Request."""
    response = client.get("/api/search")
    assert response.status_code == 400


def test_search_endpoint_with_mocked_github():
    """Verify GET /api/search with natural language query triggers query understanding and GitHub search."""
    mock_repos = [
        RepositoryModel(
            name="Langchain-Chatchat",
            full_name="chatchat-space/Langchain-Chatchat",
            owner="chatchat-space",
            owner_avatar_url="https://avatars.githubusercontent.com/u/130182442?v=4",
            description="Langchain-Chatchat (formerly langchain-ChatGLM) based on Langchain and ChatGLM",
            html_url="https://github.com/chatchat-space/Langchain-Chatchat",
            clone_url="https://github.com/chatchat-space/Langchain-Chatchat.git",
            stars=38700,
            forks=7200,
            language="Python",
            topics=["langchain", "faiss", "chatglm", "rag"],
            updated_at="2026-11-06T06:00:00Z",
            created_at="2023-04-10T02:58:36Z",
            open_issues=240,
            default_branch="master",
            match_score=None
        )
    ]

    with patch("app.api.routes.github_service.search_repositories", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = (mock_repos, 1)

        response = client.get("/api/search?q=I%20want%20a%20beginner%20RAG%20project%20using%20Python%20and%20LangChain")
        assert response.status_code == 200
        data = response.json()

        assert "query" in data
        assert data["total_count"] == 1
        assert len(data["results"]) == 1

        repo = data["results"][0]
        assert repo["name"] == "Langchain-Chatchat"
        assert repo["owner"] == "chatchat-space"
        assert repo["stars"] == 38700
        assert repo["language"] == "Python"
        assert "LangChain" in mock_search.call_args[0][0] or "language:python" in mock_search.call_args[0][0]


def test_search_rate_limit_handling():
    """Verify rate limit errors from GitHub service return HTTP 429."""
    with patch("app.api.routes.github_service.search_repositories", new_callable=AsyncMock) as mock_search:
        mock_search.side_effect = GitHubRateLimitError("GitHub API rate limit exceeded.")

        response = client.get("/api/search?q=rate-limit-test")
        assert response.status_code == 429
        data = response.json()
        assert "rate limit" in data["detail"].lower()


def test_search_network_error_handling():
    """Verify network errors from GitHub service return HTTP 503."""
    with patch("app.api.routes.github_service.search_repositories", new_callable=AsyncMock) as mock_search:
        mock_search.side_effect = GitHubNetworkError("Failed to reach GitHub API.")

        response = client.get("/api/search?q=network-error-test")
        assert response.status_code == 503
        data = response.json()
        assert "Failed to reach GitHub API." in data["detail"]
