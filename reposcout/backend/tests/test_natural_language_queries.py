"""
Comprehensive Natural Language Query Understanding Tests.
Validates structured requirement extraction across 11+ distinct developer queries.
"""

import pytest
from app.services.query_service import query_service


@pytest.mark.anyio
async def test_10_natural_language_queries():
    test_cases = [
        {
            "input": "I want a beginner RAG project using Python and LangChain",
            "expected_languages": ["Python"],
            "expected_frameworks": ["LangChain"],
            "expected_project_type": "RAG",
            "expected_difficulty": "beginner"
        },
        {
            "input": "Find me a React dashboard project",
            "expected_frameworks": ["React"],
            "expected_project_type": "Dashboard",
        },
        {
            "input": "I need a computer vision project using Python",
            "expected_languages": ["Python"],
            "expected_project_type": "Computer Vision",
        },
        {
            "input": "Find a project using FAISS and OpenAI",
            "expected_libraries": ["FAISS", "OpenAI"],
        },
        {
            "input": "Looking for a high performance REST API in Rust",
            "expected_languages": ["Rust"],
            "expected_project_type": "REST API",
        },
        {
            "input": "Show me a microservice starter with FastAPI and PostgreSQL",
            "expected_frameworks": ["FastAPI"],
            "expected_databases": ["PostgreSQL"],
            "expected_project_type": "Microservice",
        },
        {
            "input": "I need a beginner friendly machine learning tutorial with PyTorch",
            "expected_frameworks": ["PyTorch"],
            "expected_project_type": "Machine Learning",
            "expected_difficulty": "beginner"
        },
        {
            "input": "Full stack Next.js web application with TailwindCSS and Supabase",
            "expected_frameworks": ["Next.js"],
            "expected_libraries": ["TailwindCSS"],
            "expected_databases": ["Supabase"],
        },
        {
            "input": "Chatbot agent using LlamaIndex, Ollama and ChromaDB",
            "expected_frameworks": ["LlamaIndex"],
            "expected_libraries": ["Ollama", "ChromaDB"],
            "expected_project_type": "Chatbot",
        },
        {
            "input": "Chrome browser extension in TypeScript using React",
            "expected_languages": ["TypeScript"],
            "expected_frameworks": ["React"],
            "expected_project_type": "Chrome Extension",
        },
        {
            "input": "I want a beginner RAG project using Python, LangChain and FAISS",
            "expected_languages": ["Python"],
            "expected_frameworks": ["LangChain"],
            "expected_libraries": ["FAISS"],
            "expected_project_type": "RAG",
            "expected_difficulty": "beginner"
        }
    ]

    for tc in test_cases:
        res = await query_service.understand_query(tc["input"])
        data = res.model_dump()

        # Check required schema fields
        assert "original_query" in data
        assert "keywords" in data
        assert "languages" in data
        assert "frameworks" in data
        assert "libraries" in data
        assert "databases" in data
        assert "project_type" in data
        assert "difficulty" in data
        assert "requirements" in data
        assert "github_search_query" in data

        assert data["original_query"] == tc["input"]

        # Validate specific entity extractions
        if "expected_languages" in tc:
            for lang in tc["expected_languages"]:
                assert lang in data["languages"], f"Expected {lang} in {data['languages']} for {tc['input']}"

        if "expected_frameworks" in tc:
            for fw in tc["expected_frameworks"]:
                assert fw in data["frameworks"], f"Expected {fw} in {data['frameworks']} for {tc['input']}"

        if "expected_libraries" in tc:
            for lib in tc["expected_libraries"]:
                assert lib in data["libraries"], f"Expected {lib} in {data['libraries']} for {tc['input']}"

        if "expected_databases" in tc:
            for db in tc["expected_databases"]:
                assert db in data["databases"], f"Expected {db} in {data['databases']} for {tc['input']}"

        if "expected_project_type" in tc:
            assert data["project_type"] == tc["expected_project_type"], f"Expected project_type {tc['expected_project_type']} got {data['project_type']}"

        if "expected_difficulty" in tc:
            assert data["difficulty"] == tc["expected_difficulty"], f"Expected difficulty {tc['expected_difficulty']} got {data['difficulty']}"

        assert len(data["requirements"]) > 0
        assert len(data["github_search_query"]) > 0
