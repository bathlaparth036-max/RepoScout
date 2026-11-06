"""
Query Understanding Schemas.
Data contracts for natural language query decomposition and structured requirements.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class QueryUnderstandRequest(BaseModel):
    """Input payload for query understanding endpoint."""
    query: str = Field(
        ...,
        description="Natural language developer requirement or project request",
        min_length=1,
        examples=["I want a beginner RAG project using Python, LangChain and FAISS"]
    )


class StructuredRequirements(BaseModel):
    """
    Structured developer requirement extracted from natural language input.
    Matches project specifications:
    - original_query
    - keywords
    - languages
    - frameworks
    - libraries
    - databases
    - project_type
    - difficulty
    - requirements
    """
    original_query: str = Field(..., description="The user's original natural-language query")
    keywords: List[str] = Field(default_factory=list, description="Core extracted domain keywords")
    languages: List[str] = Field(default_factory=list, description="Target programming languages (e.g. Python, TypeScript)")
    frameworks: List[str] = Field(default_factory=list, description="Target frameworks (e.g. LangChain, FastAPI, React)")
    libraries: List[str] = Field(default_factory=list, description="Target libraries/SDKs (e.g. FAISS, OpenAI, OpenCV)")
    databases: List[str] = Field(default_factory=list, description="Target database systems (e.g. PostgreSQL, Redis, Chroma)")
    project_type: Optional[str] = Field(default=None, description="Inferred project category or architecture pattern")
    difficulty: Optional[str] = Field(default=None, description="Requested complexity (beginner, intermediate, advanced)")
    requirements: List[str] = Field(default_factory=list, description="Structured bullet list of extracted requirements")
    github_search_query: Optional[str] = Field(default=None, description="Derived optimal query for GitHub Search API")

