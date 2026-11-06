"""
Query Service.
Transforms natural language developer requirements into structured search requirements
and compiles them into optimal GitHub search queries.
Uses LLM provider abstraction with deterministic rule-based fallback.
"""

from typing import Dict, Any, List
from app.schemas.query import StructuredRequirements
from app.services.llm_service import llm_service


class QueryService:
    """Service handling natural language query understanding and GitHub search decomposition."""

    def __init__(self):
        self.llm = llm_service

    async def understand_query(self, query: str) -> StructuredRequirements:
        """
        Transforms raw natural language developer input into structured requirements.

        Produces:
        {
          "original_query": "...",
          "keywords": [...],
          "languages": [...],
          "frameworks": [...],
          "libraries": [...],
          "databases": [...],
          "project_type": "...",
          "difficulty": "...",
          "requirements": [...],
          "github_search_query": "..."
        }
        """
        clean_query = query.strip()
        data = await self.llm.extract_structured_requirements(clean_query)

        # Derive optimal GitHub Search query from structured requirements
        github_query = self._compile_github_query(clean_query, data)

        return StructuredRequirements(
            original_query=clean_query,
            keywords=data.get("keywords") or [],
            languages=data.get("languages") or [],
            frameworks=data.get("frameworks") or [],
            libraries=data.get("libraries") or [],
            databases=data.get("databases") or [],
            project_type=data.get("project_type"),
            difficulty=data.get("difficulty"),
            requirements=data.get("requirements") or [],
            github_search_query=github_query
        )

    def _compile_github_query(self, raw_query: str, parsed: Dict[str, Any]) -> str:
        """
        Compiles structured entities into an optimal GitHub Search API query string.
        E.g. ["RAG"], ["Python"], ["LangChain"], ["FAISS"] -> "RAG LangChain FAISS language:python"
        """
        words = raw_query.split()
        # For simple 1-2 word queries (e.g. "RAG", "React dashboard"), preserve directly
        if len(words) <= 2 and not any(w.lower() in ("i", "want", "need", "find", "show") for w in words):
            return raw_query.strip()

        terms: List[str] = []

        # 1. Project type / category (e.g. RAG, dashboard, computer vision)
        project_type = parsed.get("project_type")
        if project_type:
            # Use lowercase or standard term
            terms.append(project_type)

        # 2. Frameworks (e.g. LangChain, FastAPI, React)
        for fw in parsed.get("frameworks", []):
            if fw not in terms:
                terms.append(fw)

        # 3. Libraries / SDKs (e.g. FAISS, OpenAI, OpenCV)
        for lib in parsed.get("libraries", []):
            if lib not in terms:
                terms.append(lib)

        # 4. Databases (e.g. PostgreSQL, Redis, Chroma)
        for db in parsed.get("databases", []):
            if db not in terms:
                terms.append(db)

        # 5. Core domain keywords if not already represented (excluding difficulty terms)
        difficulty_terms = {"beginner", "starter", "easy", "simple", "advanced", "intermediate"}
        for kw in parsed.get("keywords", []):
            if kw and kw.lower() not in difficulty_terms and kw not in terms and len(terms) < 4:
                terms.append(kw)

        # 6. Target primary language qualifier
        languages = parsed.get("languages", [])
        if languages:
            primary_lang = languages[0].lower()
            terms.append(f"language:{primary_lang}")

        compiled = " ".join(terms).strip()
        return compiled if compiled else raw_query.strip()


# Global query service instance
query_service = QueryService()
