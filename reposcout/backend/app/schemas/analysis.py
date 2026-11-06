"""
Repository Analysis Schemas.
Data contracts for in-depth repository architecture, technology detection, and quality assessment.
"""

from typing import List, Optional, Dict
from pydantic import BaseModel, Field


class RepositoryAnalysisResponse(BaseModel):
    """
    Structured repository analysis output.
    Strictly provides:
    - repository: owner/name identifier
    - technologies: detected frameworks, libraries, databases, and tools
    - languages: breakdown of detected programming languages
    - frameworks: detected frameworks (FastAPI, React, LangChain, etc.)
    - libraries: detected libraries (PyTorch, Hugging Face, etc.)
    - databases: detected databases and vector stores (FAISS, Chroma, PostgreSQL, etc.)
    - apis: detected APIs (OpenAI API, REST API, etc.)
    - architecture_components: detected architectural building blocks
    - project_type: detected project classification (e.g. RAG Pipeline, Full Stack Web App)
    - documentation_quality: quality evaluation (High, Moderate, Minimal)
    - activity_status: repository activity rating
    - completeness_status: project completeness rating
    - difficulty: beginner, intermediate, or advanced
    - strengths: key technical merits discovered
    - limitations: observed potential gaps or constraints
    """
    repository: str = Field(..., description="Repository full identifier (owner/name)")
    technologies: List[str] = Field(default_factory=list, description="Detected technology stack")
    languages: List[str] = Field(default_factory=list, description="Detected programming languages")
    frameworks: List[str] = Field(default_factory=list, description="Detected frameworks")
    libraries: List[str] = Field(default_factory=list, description="Detected libraries and utilities")
    databases: List[str] = Field(default_factory=list, description="Detected vector stores & databases")
    apis: List[str] = Field(default_factory=list, description="Detected APIs")
    architecture_components: List[str] = Field(default_factory=list, description="Detected architectural components")
    project_type: str = Field(default="Open Source Project", description="Identified project category")
    documentation_quality: str = Field(default="Moderate", description="Documentation completeness rating")
    activity_status: Optional[str] = Field(default="Active", description="Repository commit and update activity status")
    completeness_status: Optional[str] = Field(default="Moderate", description="Project completeness evaluation")
    difficulty: str = Field(default="Intermediate", description="Estimated difficulty level (Beginner, Intermediate, Advanced)")
    strengths: List[str] = Field(default_factory=list, description="Observed repository strengths")
    limitations: List[str] = Field(default_factory=list, description="Observed repository limitations or gaps")

    # Extra metadata for rich frontend presentation
    owner: Optional[str] = Field(default=None, description="Repository owner")
    name: Optional[str] = Field(default=None, description="Repository name")
    owner_avatar_url: Optional[str] = Field(default=None, description="Owner avatar image URL")
    description: Optional[str] = Field(default="", description="Repository description")
    stars: Optional[int] = Field(default=0, description="Star count")
    forks: Optional[int] = Field(default=0, description="Fork count")
    html_url: Optional[str] = Field(default="", description="GitHub web URL")
    default_branch: Optional[str] = Field(default="main", description="Default branch")
    total_files_analyzed: Optional[int] = Field(default=0, description="Count of file paths analyzed")
    detected_dependency_files: List[str] = Field(default_factory=list, description="Dependency and config files detected")

