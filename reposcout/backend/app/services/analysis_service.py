"""
Repository Architecture and Technology Analysis Service.
Inspects GitHub repository metadata, README documentation, file trees,
and dependency files to extract architecture components, detected tech stack,
documentation quality, difficulty level, strengths, and limitations.

Does NOT blindly download huge repositories; queries lightweight metadata
and selected configuration files.
"""

import base64
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Set, Tuple
import httpx

from app.schemas.analysis import RepositoryAnalysisResponse
from app.services.cache_service import cache_service
from app.core.config import get_settings


class AnalysisService:
    """Service performing in-depth architectural and technology analysis of GitHub repositories."""

    BASE_URL = "https://api.github.com"

    # Known RAG architecture concepts and their concrete evidence signatures
    RAG_ARCHITECTURE_SIGNALS = {
        "document loading": {
            "patterns": [
                r"\bdocumentloader\b", r"\bunstructured\b", r"\bpypdf\b", r"\bpdfminer\b",
                r"\bfitz\b", r"\bpdfplumber\b", r"\bdocx2txt\b", r"\bwebbaseloader\b",
                r"\bdirectoryloader\b", r"\btextloader\b", r"\bcsvloader\b", r"\bdata[ _]loading\b",
                r"loaders?\.py", r"data_ingestion", r"document_loader"
            ],
            "description": "Document ingestion & multi-format parser pipeline"
        },
        "text splitting/chunking": {
            "patterns": [
                r"\btext_splitter\b", r"\bchunk_size\b", r"\bchunk_overlap\b",
                r"\brecursivecharactertextsplitter\b", r"\bcharactertextsplitter\b",
                r"\bsemantic[ _]chunk\w*\b", r"\btokensplitter\b", r"\bchunking\b",
                r"splitter\.py", r"chunker"
            ],
            "description": "Text chunking and boundary-aware segmenter"
        },
        "embeddings": {
            "patterns": [
                r"\bopenaiembeddings\b", r"\bhuggingfaceembeddings\b", r"\bsentence[-_]transformers\b",
                r"\btext-embedding-3\b", r"\btext-embedding-ada\b", r"\bollamaembeddings\b",
                r"\bembedding[ _]model\b", r"\bembed_documents\b", r"\bembed_query\b",
                r"\bcohereembeddings\b", r"\bbge[-_]embeddings?\b", r"embeddings?\.py"
            ],
            "description": "Dense vector representation and semantic embedding generation"
        },
        "vector database": {
            "patterns": [
                r"\bfaiss\b", r"\bchromadb?\b", r"\bpinecone\b", r"\bqdrant\b",
                r"\bweaviate\b", r"\bmilvus\b", r"\bpgvector\b", r"\bvectorstore\b",
                r"\bvectordb\b", r"\bsimilarity_search\b", r"vector_store\.py"
            ],
            "description": "Indexed vector storage for fast nearest-neighbor similarity search"
        },
        "retrieval": {
            "patterns": [
                r"\bretrieval\b", r"\bretriever\b", r"\bas_retriever\b", r"\bhybrid_search\b",
                r"\bsimilarity[ _]search\b", r"\bbm25\b", r"\bcontextual_compression\b",
                r"\bensemble_retriever\b", r"\bquery_engine\b", r"\bretrieval_qa\b", r"retriever\.py"
            ],
            "description": "Contextual document retrieval and similarity matching"
        },
        "reranking": {
            "patterns": [
                r"\brerank\w*\b", r"\bflashrank\b", r"\bcross[-_]encoder\b",
                r"\bbge[-_]reranker\b", r"\bcohere_rerank\b", r"\brank_documents\b"
            ],
            "description": "Two-stage relevance cross-encoder reranking"
        },
        "LLM generation": {
            "patterns": [
                r"\bchatopenai\b", r"\bchatanthropic\b", r"\bollama\b", r"\bvllm\b",
                r"\brag_chain\b", r"\bqa_chain\b", r"\bprompt_template\b", r"\bgenerate_answer\b",
                r"\bresponse_synthesizer\b", r"\bconversationalretrievalchain\b",
                r"\bcreate_retrieval_chain\b"
            ],
            "description": "Context-augmented prompt synthesis & LLM inference"
        }
    }

    # Categorized technology catalog (Frameworks, Libraries, Databases, APIs)
    TECHNOLOGY_CATALOG = [
        # Frameworks
        {"name": "FastAPI", "category": "framework", "patterns": [r"\bfastapi\b", r"\buvicorn\b"]},
        {"name": "React", "category": "framework", "patterns": [r"\breact\b", r"\breact-dom\b"]},
        {"name": "Next.js", "category": "framework", "patterns": [r"\bnext\b", r"\bnextjs\b", r"\bnext\.js\b"]},
        {"name": "Vue", "category": "framework", "patterns": [r"\bvue\b", r"\bnuxt\b"]},
        {"name": "Django", "category": "framework", "patterns": [r"\bdjango\b"]},
        {"name": "Flask", "category": "framework", "patterns": [r"\bflask\b"]},
        {"name": "Express", "category": "framework", "patterns": [r"\bexpress\b", r"\bexpressjs\b"]},
        {"name": "LangChain", "category": "framework", "patterns": [r"\blangchain\b", r"\blangchain-core\b", r"\blangchain-community\b", r"@langchain/core"]},
        {"name": "LlamaIndex", "category": "framework", "patterns": [r"\bllamaindex\b", r"\bllama-index\b", r"\bllama_index\b"]},
        {"name": "LangGraph", "category": "framework", "patterns": [r"\blanggraph\b"]},

        # Libraries
        {"name": "PyTorch", "category": "library", "patterns": [r"\btorch\b", r"\bpytorch\b"]},
        {"name": "Hugging Face", "category": "library", "patterns": [r"\bhuggingface\b", r"\btransformers\b", r"\btokenizers\b", r"huggingface\.co"]},
        {"name": "Sentence-Transformers", "category": "library", "patterns": [r"\bsentence[-_]transformers\b"]},
        {"name": "TailwindCSS", "category": "library", "patterns": [r"\btailwind\b", r"\btailwindcss\b"]},
        {"name": "Docker", "category": "library", "patterns": [r"\bdockerfile\b", r"\bdocker-compose\b"]},
        {"name": "Pydantic", "category": "library", "patterns": [r"\bpydantic\b"]},
        {"name": "NumPy", "category": "library", "patterns": [r"\bnumpy\b"]},

        # Databases
        {"name": "FAISS", "category": "database", "patterns": [r"\bfaiss\b", r"\bfaiss-cpu\b", r"\bfaiss-gpu\b"]},
        {"name": "Chroma", "category": "database", "patterns": [r"\bchromadb\b", r"\bchroma\b"]},
        {"name": "Pinecone", "category": "database", "patterns": [r"\bpinecone\b", r"\bpinecone-client\b"]},
        {"name": "Qdrant", "category": "database", "patterns": [r"\bqdrant\b", r"\bqdrant-client\b"]},
        {"name": "Weaviate", "category": "database", "patterns": [r"\bweaviate\b", r"\bweaviate-client\b"]},
        {"name": "Milvus", "category": "database", "patterns": [r"\bmilvus\b", r"\bpymilvus\b"]},
        {"name": "PostgreSQL", "category": "database", "patterns": [r"\bpostgres\b", r"\bpostgresql\b", r"\bpsycopg\b", r"\basyncpg\b", r"\bpgvector\b"]},
        {"name": "Redis", "category": "database", "patterns": [r"\bredis\b"]},
        {"name": "MongoDB", "category": "database", "patterns": [r"\bmongodb\b", r"\bpymongo\b", r"\bmongoose\b"]},
        {"name": "SQLite", "category": "database", "patterns": [r"\bsqlite\b", r"\bsqlite3\b"]},

        # APIs
        {"name": "OpenAI", "category": "api", "patterns": [r"\bopenai\b", r"api\.openai\.com", r"text-embedding", r"gpt-4", r"gpt-3\.5"]},
        {"name": "Anthropic Claude", "category": "api", "patterns": [r"\banthropic\b", r"\bclaude\b", r"api\.anthropic\.com"]},
        {"name": "Cohere", "category": "api", "patterns": [r"\bcohere\b", r"api\.cohere\.ai"]},
        {"name": "Hugging Face Inference", "category": "api", "patterns": [r"api-inference\.huggingface\.co", r"huggingface_hub"]},
        {"name": "Ollama", "category": "api", "patterns": [r"\bollama\b", r"localhost:11434"]},
        {"name": "vLLM", "category": "api", "patterns": [r"\bvllm\b"]},
        {"name": "REST API", "category": "api", "patterns": [r"\brest\b", r"\brestful\b", r"\bapi-rest\b", r"/api/v1", r"/api/"]},
    ]

    def _get_headers(self) -> Dict[str, str]:
        settings = get_settings()
        token = settings.get_github_token()
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "RepoScout-Analysis/1.0"
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    async def analyze_repository(self, owner: str, repo: str, refresh: bool = False) -> RepositoryAnalysisResponse:
        """
        Gathers repository metadata, README, languages, tree, and dependency files
        and performs architectural and technology stack deduction.
        """
        clean_owner = owner.strip()
        clean_repo = repo.strip()
        full_repo_id = f"{clean_owner}/{clean_repo}"

        settings = get_settings()

        if not refresh:
            cached = cache_service.get_analysis(clean_owner, clean_repo)
            if cached:
                return RepositoryAnalysisResponse(**cached)
            # Also check legacy key
            legacy_cached = cache_service.get(f"repo_analysis:{full_repo_id.lower()}")
            if legacy_cached:
                return RepositoryAnalysisResponse(**legacy_cached)

        headers = self._get_headers()
        request_timeout = settings.GITHUB_REQUEST_TIMEOUT

        async with httpx.AsyncClient(timeout=request_timeout) as client:
            # 1. Fetch Repository Metadata (check cache first)
            cached_repo = cache_service.get_repository(clean_owner, clean_repo)
            if cached_repo:
                repo_data = cached_repo
            else:
                repo_res = await client.get(
                    f"{self.BASE_URL}/repos/{clean_owner}/{clean_repo}",
                    headers=headers
                )
                if repo_res.status_code == 404:
                    raise ValueError(f"Repository '{full_repo_id}' not found or is private.")
                if repo_res.status_code in (403, 429):
                    raise PermissionError("GitHub API rate limit exceeded during repository inspection.")
                if not repo_res.is_success:
                    raise RuntimeError(f"GitHub returned HTTP {repo_res.status_code} for repository metadata.")

                repo_data = repo_res.json()
                cache_service.set_repository(clean_owner, clean_repo, repo_data)

            default_branch = repo_data.get("default_branch") or "main"

            # 2. Fetch README content (check cache first)
            cached_readme = cache_service.get_readme(clean_owner, clean_repo)
            if cached_readme is not None:
                readme_text = cached_readme
            else:
                readme_text = ""
                try:
                    readme_headers = dict(headers)
                    readme_headers["Accept"] = "application/vnd.github.raw+json"
                    readme_res = await client.get(
                        f"{self.BASE_URL}/repos/{clean_owner}/{clean_repo}/readme",
                        headers=readme_headers
                    )
                    if readme_res.is_success:
                        readme_text = readme_res.text
                        cache_service.set_readme(clean_owner, clean_repo, readme_text)
                except Exception:
                    readme_text = ""

            # 3. Fetch Languages breakdown
            languages_list: List[str] = []
            try:
                lang_res = await client.get(
                    f"{self.BASE_URL}/repos/{clean_owner}/{clean_repo}/languages",
                    headers=headers
                )
                if lang_res.is_success:
                    lang_dict = lang_res.json()
                    languages_list = list(lang_dict.keys())
            except Exception:
                pass
            if not languages_list and repo_data.get("language"):
                languages_list = [repo_data.get("language")]

            # 4. Fetch Repository File Tree (top-level or recursive)
            file_paths: List[str] = []
            try:
                tree_res = await client.get(
                    f"{self.BASE_URL}/repos/{clean_owner}/{clean_repo}/git/trees/{default_branch}",
                    headers=headers
                )
                if tree_res.is_success:
                    tree_data = tree_res.json()
                    file_paths = [item.get("path", "") for item in tree_data.get("tree", []) if item.get("path")]
            except Exception:
                file_paths = []

            # 5. Detect and inspect critical dependency files
            dependency_files_detected = self._detect_dependency_files(file_paths)
            dependency_content = ""

            # Fetch the first detected Python or JS dependency file (capped at 40KB)
            for dep_file in dependency_files_detected[:2]:
                try:
                    raw_dep_headers = dict(headers)
                    raw_dep_headers["Accept"] = "application/vnd.github.raw+json"
                    dep_res = await client.get(
                        f"{self.BASE_URL}/repos/{clean_owner}/{clean_repo}/contents/{dep_file}",
                        headers=raw_dep_headers
                    )
                    if dep_res.is_success:
                        dependency_content += f"\n--- {dep_file} ---\n" + dep_res.text[:40000]
                except Exception:
                    pass

        # Perform factual architectural and technology analysis
        analysis_result = self._evaluate_repository(
            repo_data=repo_data,
            readme_text=readme_text,
            languages=languages_list,
            file_paths=file_paths,
            dependency_files=dependency_files_detected,
            dependency_content=dependency_content
        )

        response = RepositoryAnalysisResponse(
            repository=full_repo_id,
            owner=clean_owner,
            name=clean_repo,
            owner_avatar_url=(repo_data.get("owner") or {}).get("avatar_url"),
            description=repo_data.get("description") or "",
            stars=repo_data.get("stargazers_count", 0),
            forks=repo_data.get("forks_count", 0),
            html_url=repo_data.get("html_url") or f"https://github.com/{full_repo_id}",
            default_branch=default_branch,
            total_files_analyzed=len(file_paths),
            detected_dependency_files=dependency_files_detected,
            technologies=analysis_result["technologies"],
            languages=languages_list,
            frameworks=analysis_result["frameworks"],
            libraries=analysis_result["libraries"],
            databases=analysis_result["databases"],
            apis=analysis_result["apis"],
            architecture_components=analysis_result["architecture_components"],
            project_type=analysis_result["project_type"],
            documentation_quality=analysis_result["documentation_quality"],
            activity_status=analysis_result["activity_status"],
            completeness_status=analysis_result["completeness_status"],
            difficulty=analysis_result["difficulty"],
            strengths=analysis_result["strengths"],
            limitations=analysis_result["limitations"]
        )

        # Cache analysis and tech detection
        cache_service.set_analysis(clean_owner, clean_repo, response.model_dump())
        cache_service.set_tech_detection(clean_owner, clean_repo, {
            "technologies": analysis_result["technologies"],
            "frameworks": analysis_result["frameworks"],
            "libraries": analysis_result["libraries"],
            "databases": analysis_result["databases"],
            "apis": analysis_result["apis"]
        })
        cache_service.set(f"repo_analysis:{full_repo_id.lower()}", response.model_dump(), ttl_seconds=1800)
        return response

    def _detect_dependency_files(self, file_paths: List[str]) -> List[str]:
        """Identifies standard configuration and dependency manifests in repository file tree."""
        target_files = {
            "requirements.txt", "pyproject.toml", "setup.py", "Pipfile", "environment.yml",
            "package.json", "pom.xml", "build.gradle", "go.mod", "Cargo.toml",
            "Dockerfile", "docker-compose.yml", "docker-compose.yaml"
        }
        detected = []
        for path in file_paths:
            base_name = path.split("/")[-1]
            if base_name in target_files:
                detected.append(path)
        return detected

    def _evaluate_repository(
        self,
        repo_data: Dict[str, Any],
        readme_text: str,
        languages: List[str],
        file_paths: List[str],
        dependency_files: List[str],
        dependency_content: str
    ) -> Dict[str, Any]:
        """
        Deduces technologies, architecture components, project type, documentation quality,
        difficulty, strengths, and limitations based on verified evidence.
        """
        topics = [t.lower() for t in repo_data.get("topics", [])]
        tree_text = " ".join(file_paths).lower()
        desc_text = (repo_data.get("description") or "").lower()
        readme_lower = readme_text.lower()
        dep_lower = dependency_content.lower()

        # Combined verified corpus
        combined_evidence = f"{desc_text}\n{tree_text}\n{dep_lower}\n{' '.join(topics)}\n{readme_lower}"

        # 1. Technology Detection & Categorization (Extensible)
        detected_techs: List[str] = []
        frameworks: List[str] = []
        libraries: List[str] = []
        databases: List[str] = []
        apis: List[str] = []

        for item in self.TECHNOLOGY_CATALOG:
            name = item["name"]
            cat = item.get("category", "library")
            # Look for verified pattern matches in dependencies, topics, tree, or README
            matches = any(re.search(pat, combined_evidence, re.IGNORECASE) for pat in item["patterns"])
            if matches:
                detected_techs.append(name)
                if cat == "framework" and name not in frameworks:
                    frameworks.append(name)
                elif cat == "library" and name not in libraries:
                    libraries.append(name)
                elif cat == "database" and name not in databases:
                    databases.append(name)
                elif cat == "api" and name not in apis:
                    apis.append(name)

        # Add primary languages if not already listed
        for lang in languages[:3]:
            if lang not in detected_techs and lang in ("Python", "TypeScript", "JavaScript", "Go", "Rust", "Java", "C++"):
                detected_techs.append(lang)

        # 2. Architecture Components Detection (especially for RAG & AI pipelines)
        detected_architecture: List[str] = []
        for component, details in self.RAG_ARCHITECTURE_SIGNALS.items():
            is_present = any(
                re.search(pat, combined_evidence, re.IGNORECASE)
                for pat in details["patterns"]
            )
            if is_present:
                detected_architecture.append(component)

        # 3. Project Type Deduction
        project_type = "Open Source Library"
        if len(detected_architecture) >= 3 or "rag" in topics or "rag" in desc_text:
            project_type = "Retrieval-Augmented Generation (RAG) System"
        elif any(t in detected_techs for t in ("LangChain", "LlamaIndex", "OpenAI")) and "agent" in combined_evidence:
            project_type = "Autonomous AI Agent Framework"
        elif any(t in detected_techs for t in ("FastAPI", "Flask", "Django", "Express", "NestJS")):
            project_type = "REST API / Backend Service"
        elif any(t in detected_techs for t in ("React", "Next.js", "Vue")):
            project_type = "Web Application / Dashboard"
        elif "extension" in tree_text or "manifest.json" in file_paths:
            project_type = "Browser Extension"
        elif any(t in detected_techs for t in ("FAISS", "Chroma", "Pinecone", "Qdrant", "Milvus")):
            project_type = "Vector Database Engine"

        # 4. Documentation Quality Assessment
        readme_len = len(readme_text)
        has_install = bool(re.search(r"(installation|install|getting started|setup|quick start)", readme_lower))
        has_usage = bool(re.search(r"(usage|example|quickstart|how to use|demo)", readme_lower))
        has_architecture = bool(re.search(r"(architecture|how it works|design|overview|pipeline)", readme_lower))

        if readme_len > 2500 and has_install and has_usage:
            doc_quality = "High"
        elif has_install and has_usage:
            doc_quality = "Moderate"
        elif readme_len > 500 and (has_install or has_usage):
            doc_quality = "Moderate"
        else:
            doc_quality = "Minimal"

        # 5. Activity Status & Project Completeness
        updated_at = repo_data.get("updated_at") or repo_data.get("pushed_at")
        activity_status = "Active"
        if updated_at:
            try:
                up_dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                days_ago = (datetime.now(timezone.utc) - up_dt).days
                if days_ago <= 30:
                    activity_status = f"Active (Updated {days_ago}d ago)"
                elif days_ago <= 90:
                    activity_status = f"Recent (Updated {days_ago // 30}mo ago)"
                elif days_ago <= 180:
                    activity_status = f"Moderate (Updated {days_ago // 30}mo ago)"
                else:
                    activity_status = f"Low (Updated {days_ago // 365 or 1}y ago)"
            except Exception:
                activity_status = "Active"

        has_tests = any("test" in path.lower() for path in file_paths)
        has_docker = any(f in dependency_files for f in ("Dockerfile", "docker-compose.yml", "docker-compose.yaml"))
        has_manifests = len(dependency_files) > 0

        if has_tests and has_docker and has_manifests:
            completeness_status = "High (Tests, Docker, and manifests verified)"
        elif has_tests and has_manifests:
            completeness_status = "Moderate (Tests and manifests verified)"
        elif has_docker and has_manifests:
            completeness_status = "Moderate (Containerized with manifests)"
        elif has_manifests:
            completeness_status = "Basic (Configuration manifests verified)"
        else:
            completeness_status = "Minimal (No standard manifests verified)"

        # 6. Difficulty Level Estimation
        is_beginner = (
            any(t in ("beginner", "starter", "tutorial", "learn") for t in topics)
            or any(w in desc_text for w in ("beginner", "starter", "simple", "tutorial", "minimal", "easy"))
            or any(path.endswith(".ipynb") for path in file_paths)
        )
        is_advanced = (
            len(file_paths) > 25
            or "c++" in languages
            or any(w in combined_evidence for w in ("distributed", "kubernetes", "cuda", "cluster", "multi-node"))
        )

        if is_beginner and not is_advanced:
            difficulty = "Beginner"
        elif is_advanced:
            difficulty = "Advanced"
        else:
            difficulty = "Intermediate"

        # 7. Strengths Identification based on factual observations
        strengths: List[str] = []
        if len(detected_architecture) >= 4:
            strengths.append(f"Complete end-to-end pipeline implementation ({', '.join(detected_architecture[:3])})")
        if any(f in dependency_files for f in ("Dockerfile", "docker-compose.yml", "docker-compose.yaml")):
            strengths.append("Containerized deployment support (Dockerfile / Docker Compose detected)")
        if any("test" in path.lower() for path in file_paths):
            strengths.append("Automated test coverage present in repository")
        if doc_quality == "High":
            strengths.append("Extensive documentation with clear setup and usage instructions")
        if repo_data.get("stargazers_count", 0) > 1000:
            strengths.append(f"Strong community adoption ({repo_data['stargazers_count']:,} GitHub stars)")
        if any(t in detected_techs for t in ("FAISS", "Chroma", "Ollama")):
            strengths.append("Supports local, self-hosted vector indexing without mandatory cloud infrastructure")
        if not strengths:
            strengths.append("Lightweight and focused code structure")

        # 8. Limitations Identification based on factual observations
        limitations: List[str] = []
        if not any("test" in path.lower() for path in file_paths):
            limitations.append("No explicit automated test suite detected in root file tree")
        if doc_quality == "Minimal":
            limitations.append("Minimal README documentation; limited quickstart guidance")
        if not any(f in dependency_files for f in ("Dockerfile", "docker-compose.yml")):
            limitations.append("No Dockerfile or container configuration provided")
        if len(detected_architecture) > 0 and len(detected_architecture) < 3 and project_type.startswith("Retrieval"):
            missing = [c for c in ["document loading", "embeddings", "vector database", "retrieval"] if c not in detected_architecture]
            if missing:
                limitations.append(f"Specialized implementation; may require custom modules for: {', '.join(missing[:2])}")
        if repo_data.get("open_issues_count", 0) > 100:
            limitations.append(f"High volume of open issues ({repo_data.get('open_issues_count')} open issues)")
        if not limitations:
            limitations.append("Requires external LLM API credentials or model weights for full execution")

        return {
            "technologies": detected_techs,
            "frameworks": frameworks,
            "libraries": libraries,
            "databases": databases,
            "apis": apis,
            "architecture_components": detected_architecture,
            "project_type": project_type,
            "documentation_quality": doc_quality,
            "activity_status": activity_status,
            "completeness_status": completeness_status,
            "difficulty": difficulty,
            "strengths": strengths,
            "limitations": limitations
        }


# Global analysis service instance
analysis_service = AnalysisService()
