"""
Unit and integration tests for the Intelligent Repository Ranking Engine.
Tests:
- RankingService scoring model (30/20/20/10/10/5/5 weights)
- ScoreBreakdown dimensions
- Explainability (matches, missing, why_it_matches)
- Configurable weights
- Sorting order (match score descending)
- POST /api/search/ranked endpoint integration
"""

from unittest.mock import patch, AsyncMock
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.repository import RepositoryModel
from app.schemas.query import StructuredRequirements
from app.schemas.analysis import RepositoryAnalysisResponse
from app.services.ranking_service import RankingService, RankingWeights
from app.services.github_service import GitHubRateLimitError
from app.services.cache_service import cache_service

client = TestClient(app)


def test_ranking_weights_defaults_and_custom():
    """Verify default weight distribution and custom configuration."""
    default_w = RankingWeights()
    assert default_w.requirement_match == 30.0
    assert default_w.technology_match == 20.0
    assert default_w.architecture_match == 20.0
    assert default_w.documentation == 10.0
    assert default_w.activity == 10.0
    assert default_w.popularity == 5.0
    assert default_w.completeness == 5.0
    assert default_w.total() == 100.0

    custom_w = RankingWeights(
        requirement_match=40.0,
        technology_match=15.0,
        architecture_match=15.0,
        documentation=10.0,
        activity=10.0,
        popularity=5.0,
        completeness=5.0
    )
    assert custom_w.requirement_match == 40.0
    assert custom_w.total() == 100.0


def test_ranking_service_score_breakdown_and_explainability():
    """Verify that score_repository outputs all 7 breakdown categories and explainable matches/missing."""
    service = RankingService()

    repo = RepositoryModel(
        name="rag-langchain-python",
        full_name="testowner/rag-langchain-python",
        owner="testowner",
        description="A beginner friendly RAG system using LangChain, FAISS and Python.",
        html_url="https://github.com/testowner/rag-langchain-python",
        stars=1500,
        forks=220,
        language="Python",
        topics=["rag", "langchain", "faiss", "vector-search", "embeddings"],
        updated_at="2026-10-01T00:00:00Z"
    )

    structured = StructuredRequirements(
        original_query="I want a beginner RAG project using Python, LangChain and FAISS",
        keywords=["RAG", "Python", "LangChain", "FAISS"],
        languages=["Python"],
        frameworks=["LangChain"],
        libraries=["FAISS"],
        databases=[],
        project_type="RAG",
        difficulty="beginner",
        requirements=[
            "RAG architecture",
            "Python",
            "LangChain",
            "FAISS",
            "Evaluation pipeline"
        ]
    )

    analysis = RepositoryAnalysisResponse(
        repository="testowner/rag-langchain-python",
        technologies=["Python", "LangChain", "FAISS", "OpenAI"],
        languages=["Python"],
        architecture_components=["document loading", "text splitting", "embeddings", "vector database", "retrieval", "LLM generation"],
        project_type="RAG",
        documentation_quality="High",
        difficulty="beginner",
        strengths=["Clear architectural components", "Comprehensive documentation"],
        limitations=[]
    )

    ranked_item = service.score_repository(repo, structured, analysis)

    assert ranked_item.name == "rag-langchain-python"
    assert ranked_item.match_score >= 80
    assert ranked_item.score_breakdown is not None

    b = ranked_item.score_breakdown
    assert 0 <= b.requirement_match <= 30
    assert 0 <= b.technology_match <= 20
    assert 0 <= b.architecture_match <= 20
    assert 0 <= b.documentation <= 10
    assert 0 <= b.activity <= 10
    assert 0 <= b.popularity <= 5
    assert 0 <= b.completeness <= 5

    # Check satisfied requirements
    assert any("Python" in m for m in ranked_item.matches)
    assert any("LangChain" in m for m in ranked_item.matches)
    assert any("FAISS" in m for m in ranked_item.matches)
    assert any("RAG architecture" in m for m in ranked_item.matches)

    # Check missing requirements
    assert any("Evaluation pipeline" in miss for miss in ranked_item.missing)

    # Check explainability
    assert ranked_item.why_it_matches
    assert "satisfies" in ranked_item.why_it_matches.lower()
    assert "requirements" in ranked_item.why_it_matches.lower()


def test_ranking_sorting_order():
    """Verify evaluate_and_rank_repositories returns candidates sorted by match_score descending."""
    service = RankingService()

    high_match_repo = RepositoryModel(
        name="high-match-rag",
        full_name="org/high-match-rag",
        owner="org",
        description="Complete Python LangChain FAISS RAG application with vector search and embeddings",
        html_url="https://github.com/org/high-match-rag",
        stars=500,
        forks=50,
        language="Python",
        topics=["rag", "langchain", "faiss"],
        updated_at="2026-10-15T00:00:00Z"
    )

    low_match_repo = RepositoryModel(
        name="unrelated-js-tool",
        full_name="org/unrelated-js-tool",
        owner="org",
        description="A lightweight JavaScript utility for color conversions",
        html_url="https://github.com/org/unrelated-js-tool",
        stars=100,
        forks=10,
        language="JavaScript",
        topics=["color", "css"],
        updated_at="2023-01-01T00:00:00Z"
    )

    structured = StructuredRequirements(
        original_query="RAG project using Python and LangChain",
        keywords=["RAG", "LangChain"],
        languages=["Python"],
        frameworks=["LangChain"],
        libraries=[],
        databases=[],
        project_type="RAG",
        difficulty=None,
        requirements=["RAG architecture", "Python", "LangChain"]
    )

    ranked_list = service.evaluate_and_rank_repositories(
        repositories=[low_match_repo, high_match_repo],
        structured=structured
    )

    assert len(ranked_list) == 2
    assert ranked_list[0].name == "high-match-rag"
    assert ranked_list[1].name == "unrelated-js-tool"
    assert ranked_list[0].match_score > ranked_list[1].match_score


def test_api_ranked_search_empty_query():
    """Verify POST /api/search/ranked returns 400 when query is empty."""
    resp = client.post("/api/search/ranked", json={"query": "   "})
    assert resp.status_code == 400
    assert "Query field must not be empty" in resp.json()["detail"]


@patch("app.api.routes.github_service.search_repositories")
@patch("app.api.routes.analysis_service.analyze_repository")
def test_api_ranked_search_endpoint_success(mock_analyze, mock_search):
    """Verify POST /api/search/ranked end-to-end pipeline with mocked GitHub & analysis."""
    cache_service.clear()
    mock_search.return_value = (
        [
            RepositoryModel(
                name="awesome-rag",
                full_name="dev/awesome-rag",
                owner="dev",
                description="Production-ready RAG application using Python, LangChain and FAISS",
                html_url="https://github.com/dev/awesome-rag",
                stars=890,
                forks=120,
                language="Python",
                topics=["rag", "langchain", "faiss"],
                updated_at="2026-09-01T00:00:00Z"
            )
        ],
        1
    )

    mock_analyze.return_value = RepositoryAnalysisResponse(
        repository="dev/awesome-rag",
        technologies=["Python", "LangChain", "FAISS"],
        languages=["Python"],
        architecture_components=["document loading", "embeddings", "vector database", "retrieval"],
        project_type="RAG",
        documentation_quality="High",
        difficulty="intermediate",
        strengths=["Clear architectural components"],
        limitations=[]
    )

    response = client.post(
        "/api/search/ranked",
        json={"query": "I want a beginner RAG project using Python and LangChain"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "I want a beginner RAG project using Python and LangChain"
    assert data["total_count"] == 1
    assert len(data["results"]) == 1

    item = data["results"][0]
    assert item["name"] == "awesome-rag"
    assert "match_score" in item
    assert item["match_score"] >= 70
    assert "score_breakdown" in item
    breakdown = item["score_breakdown"]
    assert "requirement_match" in breakdown
    assert "technology_match" in breakdown
    assert "architecture_match" in breakdown
    assert "documentation" in breakdown
    assert "activity" in breakdown
    assert "popularity" in breakdown
    assert "completeness" in breakdown
    assert isinstance(item["matches"], list)
    assert len(item["matches"]) > 0
    assert isinstance(item["missing"], list)
    assert item["why_it_matches"]


@patch("app.api.routes.github_service.search_repositories")
def test_api_ranked_search_rate_limit(mock_search):
    """Verify POST /api/search/ranked translates GitHubRateLimitError to HTTP 429."""
    mock_search.side_effect = GitHubRateLimitError("GitHub API rate limit exceeded. Please wait.")

    response = client.post(
        "/api/search/ranked",
        json={"query": "unique query to avoid cache for rate limit test"}
    )
    assert response.status_code == 429
    assert "rate limit exceeded" in response.json()["detail"].lower()
