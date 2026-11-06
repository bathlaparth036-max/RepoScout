"""
Repository Analysis Tests.
Verifies GET /api/repository/analyze endpoint, RAG architecture detection,
technology stack deduction, and error handling.
"""

from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.analysis import RepositoryAnalysisResponse
from app.services.analysis_service import analysis_service

client = TestClient(app)


def test_analyze_endpoint_missing_params():
    """Verify endpoint rejects missing or invalid repository parameters."""
    res1 = client.get("/api/repository/analyze?repo=")
    assert res1.status_code == 400

    res2 = client.get("/api/repository/analyze?repo=invalid-no-owner")
    assert res2.status_code == 400


def test_analyze_endpoint_success_mocked():
    """Verify GET /api/repository/analyze returns required schema."""
    mock_analysis = RepositoryAnalysisResponse(
        repository="hwchase17/langchain",
        owner="hwchase17",
        name="langchain",
        description="Building applications with LLMs through composability",
        technologies=["Python", "LangChain", "OpenAI", "FAISS"],
        languages=["Python"],
        architecture_components=["document loading", "embeddings", "vector database", "retrieval", "LLM generation"],
        project_type="Retrieval-Augmented Generation (RAG) System",
        documentation_quality="High",
        difficulty="Intermediate",
        strengths=["Complete end-to-end pipeline implementation", "Extensive documentation"],
        limitations=["Requires external LLM API credentials or model weights for full execution"],
        stars=89000,
        forks=13000,
        html_url="https://github.com/hwchase17/langchain"
    )

    with patch.object(analysis_service, "analyze_repository", new_callable=AsyncMock) as mock_analyze:
        mock_analyze.return_value = mock_analysis

        response = client.get("/api/repository/analyze?repo=hwchase17/langchain")
        assert response.status_code == 200
        data = response.json()

        assert data["repository"] == "hwchase17/langchain"
        assert "LangChain" in data["technologies"]
        assert "document loading" in data["architecture_components"]
        assert "embeddings" in data["architecture_components"]
        assert "vector database" in data["architecture_components"]
        assert "retrieval" in data["architecture_components"]
        assert "LLM generation" in data["architecture_components"]
        assert data["project_type"] == "Retrieval-Augmented Generation (RAG) System"
        assert data["documentation_quality"] == "High"
        assert data["difficulty"] == "Intermediate"
        assert isinstance(data["strengths"], list)
        assert isinstance(data["limitations"], list)


def test_analyze_endpoint_404_handling():
    """Verify private or non-existent repositories return 404."""
    with patch.object(analysis_service, "analyze_repository", new_callable=AsyncMock) as mock_analyze:
        mock_analyze.side_effect = ValueError("Repository 'owner/private-repo' not found or is private.")

        response = client.get("/api/repository/analyze?owner=owner&repo=private-repo")
        assert response.status_code == 404
        assert "not found or is private" in response.json()["detail"]


def test_evaluate_rag_architecture_detection():
    """Verify internal RAG component pattern matching based on factual evidence."""
    sample_repo_data = {
        "description": "Production RAG pipeline with vector search and document loading",
        "topics": ["rag", "langchain", "faiss"],
        "stargazers_count": 3500,
        "forks_count": 420,
        "open_issues_count": 12
    }
    sample_readme = """
    # Minimal RAG Starter
    This project demonstrates document loading using PyPDF, text chunking with RecursiveCharacterTextSplitter,
    OpenAIEmbeddings for dense semantic vectors, and FAISS as a local vector database for similarity search retrieval.
    Finally, response synthesis uses ChatOpenAI with custom prompt templates.

    ## Installation
    ```bash
    pip install -r requirements.txt
    ```

    ## Usage
    ```python
    from src.loader import load_documents
    ```
    """
    file_paths = ["src/loader.py", "src/embeddings.py", "src/vector_store.py", "Dockerfile", "tests/test_rag.py"]
    dep_files = ["requirements.txt", "Dockerfile"]
    dep_content = "langchain>=0.2.0\nfaiss-cpu\nopenai\npypdf\n"

    result = analysis_service._evaluate_repository(
        repo_data=sample_repo_data,
        readme_text=sample_readme,
        languages=["Python"],
        file_paths=file_paths,
        dependency_files=dep_files,
        dependency_content=dep_content
    )

    # Check RAG architecture components
    assert "document loading" in result["architecture_components"]
    assert "text splitting/chunking" in result["architecture_components"]
    assert "embeddings" in result["architecture_components"]
    assert "vector database" in result["architecture_components"]
    assert "retrieval" in result["architecture_components"]
    assert "LLM generation" in result["architecture_components"]

    # Check technologies
    assert "LangChain" in result["technologies"]
    assert "FAISS" in result["technologies"]
    assert "OpenAI" in result["technologies"]
    assert "Docker" in result["technologies"]

    # Check categorized technologies
    assert "LangChain" in result["frameworks"]
    assert "FAISS" in result["databases"]
    assert "OpenAI" in result["apis"]

    # Check quality indicators
    assert result["documentation_quality"] in ("High", "Moderate")
    assert result["activity_status"] is not None
    assert "High" in result["completeness_status"]
    assert len(result["strengths"]) > 0


def test_analyze_endpoint_refresh_flag():
    """Verify refresh query parameter forces cache bypass."""
    mock_analysis = RepositoryAnalysisResponse(
        repository="testowner/testrepo",
        owner="testowner",
        name="testrepo",
        technologies=["Python", "FastAPI"],
        languages=["Python"],
        frameworks=["FastAPI"],
        libraries=[],
        databases=["PostgreSQL"],
        apis=["REST API"],
        architecture_components=["document loading"],
        project_type="REST API / Backend Service",
        documentation_quality="High",
        activity_status="Active (Updated 2d ago)",
        completeness_status="High (Tests & Docker verified)",
        difficulty="Intermediate",
        strengths=["Automated test coverage present in repository"],
        limitations=[]
    )

    with patch.object(analysis_service, "analyze_repository", new_callable=AsyncMock) as mock_analyze:
        mock_analyze.return_value = mock_analysis

        response = client.get("/api/repository/analyze?repo=testowner/testrepo&refresh=true")
        assert response.status_code == 200
        mock_analyze.assert_called_once_with("testowner", "testrepo", refresh=True)

        data = response.json()
        assert "FastAPI" in data["frameworks"]
        assert "PostgreSQL" in data["databases"]
        assert "REST API" in data["apis"]
        assert data["activity_status"] == "Active (Updated 2d ago)"
