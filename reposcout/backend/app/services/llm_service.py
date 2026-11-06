"""
LLM Provider Abstraction Service.
Keeps LLM providers (OpenAI, Google Gemini, Ollama, Rule-Based Fallback) behind a clean abstraction.
Ensures API keys remain strictly server-side and automatically falls back to deterministic
rule-based extraction if an LLM is offline or unconfigured.
"""

import json
import logging
import re
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
import httpx

from app.core.config import get_settings

logger = logging.getLogger("reposcout.llm")


SYSTEM_PROMPT = """You are RepoScout's expert software requirement extraction assistant.
Given a developer's natural language request, extract structured technical requirements.

You must respond ONLY with a valid JSON object matching this schema:
{
  "keywords": ["list", "of", "domain", "keywords"],
  "languages": ["detected programming languages e.g. Python, TypeScript"],
  "frameworks": ["detected frameworks e.g. LangChain, FastAPI, React"],
  "libraries": ["detected libraries or SDKs e.g. FAISS, OpenAI, OpenCV"],
  "databases": ["detected database systems e.g. PostgreSQL, Redis"],
  "project_type": "project category e.g. RAG, Dashboard, Computer Vision, REST API or null",
  "difficulty": "beginner, intermediate, advanced, or null",
  "requirements": ["clean bullet points of extracted architectural and tech requirements"]
}
Do not include markdown code block formatting (```json) or conversational text."""


class BaseLLMProvider(ABC):
    """Abstract base class for all LLM providers."""

    @abstractmethod
    async def complete_prompt(self, prompt: str, system_prompt: str = SYSTEM_PROMPT) -> Optional[str]:
        """Send prompt to LLM and return raw text response."""
        pass


class OpenAILLMProvider(BaseLLMProvider):
    """OpenAI API provider implementation (gpt-4o-mini / gpt-3.5-turbo)."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model
        self.url = "https://api.openai.com/v1/chat/completions"

    async def complete_prompt(self, prompt: str, system_prompt: str = SYSTEM_PROMPT) -> Optional[str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.0,
            "response_format": {"type": "json_object"}
        }
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.post(self.url, headers=headers, json=payload)
                if res.is_success:
                    data = res.json()
                    return data["choices"][0]["message"]["content"]
                logger.warning(f"OpenAI error {res.status_code}: {res.text}")
                return None
        except Exception as exc:
            logger.warning(f"OpenAI call failed: {exc}")
            return None


class GeminiLLMProvider(BaseLLMProvider):
    """Google Gemini API provider implementation."""

    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        self.api_key = api_key
        self.model = model
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

    async def complete_prompt(self, prompt: str, system_prompt: str = SYSTEM_PROMPT) -> Optional[str]:
        combined = f"{system_prompt}\n\nDeveloper Request:\n{prompt}"
        payload = {
            "contents": [{"parts": [{"text": combined}]}],
            "generationConfig": {"temperature": 0.0, "responseMimeType": "application/json"}
        }
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.post(self.url, json=payload)
                if res.is_success:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        return candidates[0]["content"]["parts"][0]["text"]
                logger.warning(f"Gemini error {res.status_code}: {res.text}")
                return None
        except Exception as exc:
            logger.warning(f"Gemini call failed: {exc}")
            return None


class OllamaLLMProvider(BaseLLMProvider):
    """Local Ollama provider implementation."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3"):
        self.url = f"{base_url.rstrip('/')}/api/generate"
        self.model = model

    async def complete_prompt(self, prompt: str, system_prompt: str = SYSTEM_PROMPT) -> Optional[str]:
        payload = {
            "model": self.model,
            "prompt": f"{system_prompt}\n\nUser request:\n{prompt}",
            "stream": False,
            "format": "json"
        }
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                res = await client.post(self.url, json=payload)
                if res.is_success:
                    return res.json().get("response")
                return None
        except Exception as exc:
            logger.debug(f"Ollama call failed: {exc}")
            return None


class RuleBasedFallbackProvider(BaseLLMProvider):
    """
    Deterministic rule-based NLP extraction provider.
    Guarantees 100% uptime, zero network latency, and accurate parsing
    even when no external LLM API key is provided or when external APIs fail.
    """

    KNOWN_LANGUAGES = {
        "python": "Python", "typescript": "TypeScript", "javascript": "JavaScript",
        "go": "Go", "golang": "Go", "rust": "Rust", "c++": "C++", "cpp": "C++",
        "c": "C", "java": "Java", "ruby": "Ruby", "swift": "Swift", "kotlin": "Kotlin",
        "c#": "C#", "csharp": "C#", "php": "PHP"
    }

    KNOWN_FRAMEWORKS = {
        "langchain": "LangChain", "llamaindex": "LlamaIndex", "fastapi": "FastAPI",
        "react": "React", "nextjs": "Next.js", "next.js": "Next.js", "vue": "Vue",
        "angular": "Angular", "django": "Django", "flask": "Flask", "express": "Express",
        "nestjs": "NestJS", "pytorch": "PyTorch", "tensorflow": "TensorFlow", "spring": "Spring Boot"
    }

    KNOWN_LIBRARIES = {
        "faiss": "FAISS", "openai": "OpenAI", "anthropic": "Anthropic", "ollama": "Ollama",
        "chroma": "Chroma", "chromadb": "ChromaDB", "qdrant": "Qdrant", "pinecone": "Pinecone",
        "weaviate": "Weaviate", "opencv": "OpenCV", "cv2": "OpenCV", "scikit-learn": "Scikit-Learn",
        "sklearn": "Scikit-Learn", "pandas": "Pandas", "numpy": "NumPy", "tailwind": "TailwindCSS",
        "tailwindcss": "TailwindCSS", "transformers": "Transformers", "huggingface": "HuggingFace"
    }

    KNOWN_DATABASES = {
        "postgres": "PostgreSQL", "postgresql": "PostgreSQL", "mysql": "MySQL",
        "sqlite": "SQLite", "mongodb": "MongoDB", "redis": "Redis", "cassandra": "Cassandra",
        "neo4j": "Neo4j", "supabase": "Supabase", "dynamodb": "DynamoDB"
    }

    PROJECT_TYPES = [
        (r"\brag\b|\bretrieval[- ]augmented\b", "RAG"),
        (r"\bcomputer vision\b|\bvision\b", "Computer Vision"),
        (r"\bdashboard\b|\badmin panel\b", "Dashboard"),
        (r"\bmicroservice\b|\bmicroservices\b", "Microservice"),
        (r"\brest api\b|\bapi\b", "REST API"),
        (r"\bchrome extension\b|\bbrowser extension\b|\bextension\b", "Chrome Extension"),
        (r"\bcli\b|\bcommand line\b", "CLI Tool"),
        (r"\bchatbot\b|\bbot\b", "Chatbot"),
        (r"\bweb scraper\b|\bcrawler\b|\bscraping\b", "Web Scraping"),
        (r"\bagents?\b|\bmulti-agent\b", "AI Agents"),
        (r"\bmachine learning\b|\bml\b", "Machine Learning"),
        (r"\bdeep learning\b|\bdl\b", "Deep Learning")
    ]

    async def complete_prompt(self, prompt: str, system_prompt: str = SYSTEM_PROMPT) -> Optional[str]:
        normalized = prompt.lower()
        words = re.findall(r"\b[\w\-#+.]+\b", normalized)

        # Detect languages
        languages = []
        for word in words:
            if word in self.KNOWN_LANGUAGES:
                lang = self.KNOWN_LANGUAGES[word]
                if lang not in languages:
                    languages.append(lang)

        # Detect frameworks
        frameworks = []
        for word in words:
            if word in self.KNOWN_FRAMEWORKS:
                fw = self.KNOWN_FRAMEWORKS[word]
                if fw not in frameworks:
                    frameworks.append(fw)

        # Detect libraries
        libraries = []
        for word in words:
            if word in self.KNOWN_LIBRARIES:
                lib = self.KNOWN_LIBRARIES[word]
                if lib not in libraries:
                    libraries.append(lib)

        # Detect databases
        databases = []
        for word in words:
            if word in self.KNOWN_DATABASES:
                db = self.KNOWN_DATABASES[word]
                if db not in databases:
                    databases.append(db)

        # Detect project type using word-boundary regex patterns
        project_type = None
        for pattern, label in self.PROJECT_TYPES:
            if re.search(pattern, normalized):
                project_type = label
                break

        # Detect difficulty
        difficulty = None
        if any(term in normalized for term in ["beginner", "starter", "easy", "simple", "intro", "tutorial"]):
            difficulty = "beginner"
        elif any(term in normalized for term in ["advanced", "production", "enterprise", "expert"]):
            difficulty = "advanced"
        elif any(term in normalized for term in ["intermediate", "medium"]):
            difficulty = "intermediate"

        # Extract domain keywords (excluding words already categorized or generic fillers)
        stop_words = {
            "i", "want", "a", "an", "the", "need", "find", "me", "show", "give",
            "can", "you", "using", "with", "and", "or", "project", "looking", "for",
            "beginner", "starter", "simple", "easy", "advanced", "intermediate", "tutorial"
        }
        categorized_lower = {x.lower() for x in (languages + frameworks + libraries + databases)}

        keywords = []
        if project_type and project_type.lower() not in categorized_lower:
            keywords.append(project_type)

        for w in words:
            w_lower = w.lower()
            if w_lower not in stop_words and w_lower not in categorized_lower and len(w) > 2:
                formatted_kw = w.upper() if w.upper() in ["RAG", "API", "LLM", "NLP", "CV", "ML"] else w.capitalize()
                if formatted_kw not in keywords:
                    keywords.append(formatted_kw)

        # Build clean requirements list
        requirements: List[str] = []
        if project_type:
            requirements.append(f"{project_type} architecture" if project_type in ("RAG", "REST API") else f"{project_type} project")
        for lang in languages:
            requirements.append(lang)
        for fw in frameworks:
            requirements.append(fw)
        for lib in libraries:
            requirements.append(lib)
        for db in databases:
            requirements.append(f"{db} database")

        # Fallback requirement if list is empty
        if not requirements:
            requirements = [w.capitalize() for w in words if w not in stop_words][:3]

        result = {
            "keywords": keywords if keywords else (requirements[:1] if requirements else ["Repository"]),
            "languages": languages,
            "frameworks": frameworks,
            "libraries": libraries,
            "databases": databases,
            "project_type": project_type,
            "difficulty": difficulty,
            "requirements": requirements
        }
        return json.dumps(result)


class LLMService:
    """Orchestrator managing LLM provider selection, execution, and graceful fallback."""

    def __init__(self):
        self.fallback_provider = RuleBasedFallbackProvider()

    def _select_provider(self) -> BaseLLMProvider:
        """Selects optimal LLM provider based on backend configuration and available keys."""
        settings = get_settings()
        choice = (settings.LLM_PROVIDER or "auto").lower()

        if choice == "openai" or (choice == "auto" and settings.OPENAI_API_KEY):
            if settings.OPENAI_API_KEY:
                return OpenAILLMProvider(settings.OPENAI_API_KEY, settings.OPENAI_MODEL)

        if choice == "gemini" or (choice == "auto" and settings.GEMINI_API_KEY):
            if settings.GEMINI_API_KEY:
                return GeminiLLMProvider(settings.GEMINI_API_KEY, settings.GEMINI_MODEL)

        if choice == "ollama":
            return OllamaLLMProvider(settings.OLLAMA_BASE_URL)

        return self.fallback_provider

    async def extract_structured_requirements(self, query: str) -> Dict[str, Any]:
        """
        Parses user query into structured requirements.
        Attempts configured LLM provider first; falls back to deterministic rule-based
        extraction if unconfigured, offline, or upon parsing errors.
        """
        clean_query = query.strip()
        provider = self._select_provider()

        raw_response: Optional[str] = None
        # Try primary provider if not already the fallback
        if not isinstance(provider, RuleBasedFallbackProvider):
            try:
                raw_response = await provider.complete_prompt(clean_query)
            except Exception as exc:
                logger.warning(f"Primary LLM provider failed: {exc}. Using fallback.")

        # If primary provider didn't return valid text, use rule-based fallback
        if not raw_response:
            raw_response = await self.fallback_provider.complete_prompt(clean_query)

        # Parse JSON output
        parsed: Dict[str, Any] = {}
        try:
            # Clean possible markdown code fences
            cleaned_text = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_response.strip(), flags=re.MULTILINE)
            parsed = json.loads(cleaned_text)
        except Exception:
            # Emergency fallback parse
            raw_fallback = await self.fallback_provider.complete_prompt(clean_query)
            parsed = json.loads(raw_fallback)

        return {
            "original_query": clean_query,
            "keywords": parsed.get("keywords") or [],
            "languages": parsed.get("languages") or [],
            "frameworks": parsed.get("frameworks") or [],
            "libraries": parsed.get("libraries") or [],
            "databases": parsed.get("databases") or [],
            "project_type": parsed.get("project_type"),
            "difficulty": parsed.get("difficulty"),
            "requirements": parsed.get("requirements") or []
        }


# Global LLM service instance
llm_service = LLMService()
