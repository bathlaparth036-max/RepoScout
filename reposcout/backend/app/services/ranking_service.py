"""
Intelligent Repository Ranking and Relevance Scoring Engine.
Calculates how closely GitHub repository candidates match user requirements
across 7 configurable dimensions with explainable reasons, satisfied matches, and missing criteria.

Default Scoring Model:
- Requirement match: 30%
- Technology match: 20%
- Architecture match: 20%
- Documentation quality: 10%
- Repository activity: 10%
- Popularity: 5%
- Project completeness: 5%
Total: 100%
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
import re

from app.models.repository import RepositoryModel
from app.schemas.query import StructuredRequirements
from app.schemas.analysis import RepositoryAnalysisResponse
from app.schemas.repository import ScoreBreakdown, RankedRepositoryItem


@dataclass
class RankingWeights:
    """Configurable scoring weights for repository relevance calculation."""
    requirement_match: float = 30.0
    technology_match: float = 20.0
    architecture_match: float = 20.0
    documentation: float = 10.0
    activity: float = 10.0
    popularity: float = 5.0
    completeness: float = 5.0

    def total(self) -> float:
        return (
            self.requirement_match
            + self.technology_match
            + self.architecture_match
            + self.documentation
            + self.activity
            + self.popularity
            + self.completeness
        )


class RankingService:
    """Intelligent scoring engine that calculates explainable relevance scores."""

    def __init__(self, default_weights: Optional[RankingWeights] = None):
        self.default_weights = default_weights or RankingWeights()

    def evaluate_and_rank_repositories(
        self,
        repositories: List[RepositoryModel],
        structured: StructuredRequirements,
        analyses: Optional[Dict[str, RepositoryAnalysisResponse]] = None,
        weights: Optional[RankingWeights] = None
    ) -> List[RankedRepositoryItem]:
        """
        Evaluates a list of repository candidates against structured requirements
        and analysis metadata, returning ranked and explainable repository items
        sorted by match_score descending.
        """
        if not repositories:
            return []

        w = weights or self.default_weights
        analyses_map = analyses or {}

        ranked_items: List[RankedRepositoryItem] = []

        for repo in repositories:
            full_repo_id = repo.full_name or f"{repo.owner}/{repo.name}"
            analysis = analyses_map.get(full_repo_id)

            ranked_item = self.score_repository(repo, structured, analysis, w)
            ranked_items.append(ranked_item)

        # Sort primary by match_score descending; secondary by stars descending
        ranked_items.sort(
            key=lambda item: (item.match_score or 0, item.stars or 0),
            reverse=True
        )

        return ranked_items

    def score_repository(
        self,
        repo: RepositoryModel,
        structured: StructuredRequirements,
        analysis: Optional[RepositoryAnalysisResponse],
        weights: Optional[RankingWeights] = None
    ) -> RankedRepositoryItem:
        """
        Computes the explainable score for a single repository across all 7 dimensions.
        """
        w = weights or self.default_weights

        # 1. Evaluate satisfied vs missing requirements & compute Dimension 1 (30 pts)
        req_pts, matches, missing = self._evaluate_requirements(repo, structured, analysis, w.requirement_match)

        # 2. Technology Match (20 pts)
        tech_pts = self._evaluate_technology(repo, structured, analysis, w.technology_match)

        # 3. Architecture Match (20 pts)
        arch_pts = self._evaluate_architecture(repo, structured, analysis, w.architecture_match)

        # 4. Documentation Quality (10 pts)
        doc_pts = self._evaluate_documentation(repo, analysis, w.documentation)

        # 5. Repository Activity & Freshness (10 pts)
        act_pts = self._evaluate_activity(repo, w.activity)

        # 6. Popularity & Adoption (5 pts)
        pop_pts = self._evaluate_popularity(repo, w.popularity)

        # 7. Project Completeness (5 pts)
        comp_pts = self._evaluate_completeness(repo, analysis, w.completeness)

        # Sum total match score (clamped between 15 and 100)
        raw_total = req_pts + tech_pts + arch_pts + doc_pts + act_pts + pop_pts + comp_pts
        total_score = max(15, min(100, int(round(raw_total))))

        breakdown = ScoreBreakdown(
            requirement_match=int(round(req_pts)),
            technology_match=int(round(tech_pts)),
            architecture_match=int(round(arch_pts)),
            documentation=int(round(doc_pts)),
            activity=int(round(act_pts)),
            popularity=int(round(pop_pts)),
            completeness=int(round(comp_pts))
        )

        # Generate concise explainable summary
        why_it_matches = self._generate_explanation(total_score, matches, missing, analysis)

        return RankedRepositoryItem(
            name=repo.name,
            full_name=repo.full_name or f"{repo.owner}/{repo.name}",
            owner=repo.owner,
            owner_avatar_url=repo.owner_avatar_url,
            description=repo.description or "",
            url=repo.html_url or repo.url,
            html_url=repo.html_url or repo.url,
            clone_url=repo.clone_url or f"{repo.html_url}.git",
            stars=repo.stars,
            forks=repo.forks,
            language=repo.language,
            topics=repo.topics,
            updated_at=repo.updated_at,
            created_at=repo.created_at,
            open_issues=repo.open_issues,
            default_branch=repo.default_branch,
            match_score=total_score,
            github_url=repo.html_url or repo.url,
            match_percentage=total_score,
            score_breakdown=breakdown,
            matches=matches,
            missing=missing,
            why_it_matches=why_it_matches
        )

    def _evaluate_requirements(
        self,
        repo: RepositoryModel,
        structured: StructuredRequirements,
        analysis: Optional[RepositoryAnalysisResponse],
        max_pts: float
    ) -> Tuple[float, List[str], List[str]]:
        """
        Determines what explicit requirements are satisfied vs missing.
        Returns: (points_awarded, matches_list, missing_list)
        """
        # Collect candidate evidence text
        evidence_topics = {t.lower() for t in repo.topics}
        evidence_techs = {t.lower() for t in (analysis.technologies if analysis else [])}
        evidence_arch = {a.lower() for a in (analysis.architecture_components if analysis else [])}
        desc_lower = (repo.description or "").lower()
        name_lower = repo.name.lower()
        repo_lang = (repo.language or "").lower()

        combined_text = f"{name_lower} {desc_lower} {' '.join(evidence_topics)} {' '.join(evidence_techs)} {' '.join(evidence_arch)}"

        # Requirements to test
        req_list = list(structured.requirements)
        if not req_list:
            # Derive requirements from keywords, language, frameworks
            if structured.project_type:
                req_list.append(f"{structured.project_type} architecture")
            for l in structured.languages:
                req_list.append(l)
            for f in structured.frameworks:
                req_list.append(f)
            for lib in structured.libraries:
                req_list.append(lib)
            for kw in structured.keywords[:2]:
                if kw not in req_list:
                    req_list.append(kw)

        # Fallback if still empty
        if not req_list:
            req_list = [w.capitalize() for w in structured.original_query.split() if len(w) > 3][:3]

        matches: List[str] = []
        missing: List[str] = []

        for req in req_list:
            clean_req = req.strip()
            req_lower = clean_req.lower()

            # Strip decorative words like "architecture", "project", "level"
            token = re.sub(r"\b(architecture|project|level|tutorial|system|starter)\b", "", req_lower).strip()
            if not token:
                token = req_lower

            satisfied = False
            # Check language match
            if req_lower in (repo_lang, "python", "typescript", "javascript", "go", "rust", "c++", "java"):
                satisfied = (repo_lang == req_lower) or (req_lower in evidence_topics)
            # Check RAG or project type
            elif "rag" in token:
                satisfied = (
                    "rag" in evidence_topics or "rag" in combined_text
                    or (analysis and "rag" in analysis.project_type.lower())
                )
            # Check frameworks/libraries/techs
            elif token in evidence_techs or any(token in t for t in evidence_techs):
                satisfied = True
            elif token in evidence_arch or any(token in a for a in evidence_arch):
                satisfied = True
            elif token in evidence_topics or token in name_lower or token in desc_lower:
                satisfied = True
            elif re.search(r"\b" + re.escape(token) + r"\b", combined_text):
                satisfied = True

            if satisfied:
                matches.append(clean_req)
            else:
                missing.append(clean_req)

        # Score calculation
        total_reqs = max(1, len(req_list))
        ratio = len(matches) / total_reqs
        points = min(max_pts, round(ratio * max_pts, 1))

        return points, matches, missing

    def _evaluate_technology(
        self,
        repo: RepositoryModel,
        structured: StructuredRequirements,
        analysis: Optional[RepositoryAnalysisResponse],
        max_pts: float
    ) -> float:
        """Evaluates alignment with requested programming languages and libraries (20%)."""
        target_techs = [
            t.lower() for t in (structured.languages + structured.frameworks + structured.libraries + structured.databases)
        ]
        if not target_techs:
            return round(max_pts * 0.85, 1)  # Neutral high baseline if no specific tech requested

        repo_techs = {t.lower() for t in (analysis.technologies if analysis else [])}
        if repo.language:
            repo_techs.add(repo.language.lower())
        for topic in repo.topics:
            repo_techs.add(topic.lower())

        desc_lower = (repo.description or "").lower()

        matched = 0
        for tech in target_techs:
            if tech in repo_techs or tech in desc_lower or tech in repo.name.lower():
                matched += 1

        ratio = matched / len(target_techs)
        return round(ratio * max_pts, 1)

    def _evaluate_architecture(
        self,
        repo: RepositoryModel,
        structured: StructuredRequirements,
        analysis: Optional[RepositoryAnalysisResponse],
        max_pts: float
    ) -> float:
        """Evaluates architecture components and project category alignment (20%)."""
        arch_components = analysis.architecture_components if analysis else []
        project_type = (analysis.project_type if analysis else "").lower()
        requested_type = (structured.project_type or "").lower()

        score = 0.0

        # Type alignment
        if requested_type:
            if requested_type in project_type or requested_type in [t.lower() for t in repo.topics]:
                score += (max_pts * 0.6)  # 12 pts
            elif requested_type in (repo.description or "").lower():
                score += (max_pts * 0.4)
            else:
                score += (max_pts * 0.2)
        else:
            score += (max_pts * 0.5)

        # Architectural component coverage (especially RAG building blocks)
        if arch_components:
            # Having 4+ components gets full component share
            component_ratio = min(1.0, len(arch_components) / 4.0)
            score += round(component_ratio * (max_pts * 0.4), 1)
        elif "rag" in (repo.description or "").lower() or "rag" in [t.lower() for t in repo.topics]:
            score += (max_pts * 0.3)
        else:
            score += (max_pts * 0.2)

        return min(max_pts, round(score, 1))

    def _evaluate_documentation(
        self,
        repo: RepositoryModel,
        analysis: Optional[RepositoryAnalysisResponse],
        max_pts: float
    ) -> float:
        """Evaluates documentation quality and README completeness (10%)."""
        doc_quality = (analysis.documentation_quality if analysis else "Moderate").lower()

        if doc_quality == "high":
            return max_pts  # 10 pts
        elif doc_quality == "moderate":
            return round(max_pts * 0.75, 1)  # 7.5 pts
        else:
            return round(max_pts * 0.35, 1)  # 3.5 pts

    def _evaluate_activity(
        self,
        repo: RepositoryModel,
        max_pts: float
    ) -> float:
        """Evaluates repository freshness and recent commit activity (10%)."""
        if not repo.updated_at:
            return round(max_pts * 0.5, 1)

        try:
            updated_dt = datetime.fromisoformat(repo.updated_at.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            days = (now - updated_dt).days

            if days <= 30:
                return max_pts  # 10 pts (actively maintained this month)
            elif days <= 90:
                return round(max_pts * 0.85, 1)  # 8.5 pts
            elif days <= 180:
                return round(max_pts * 0.7, 1)  # 7 pts
            elif days <= 365:
                return round(max_pts * 0.5, 1)  # 5 pts
            else:
                return round(max_pts * 0.25, 1)  # 2.5 pts
        except Exception:
            return round(max_pts * 0.5, 1)

    def _evaluate_popularity(
        self,
        repo: RepositoryModel,
        max_pts: float
    ) -> float:
        """Evaluates community adoption and star count (5%)."""
        stars = max(0, repo.stars or 0)

        if stars >= 10000:
            return max_pts  # 5.0 pts
        elif stars >= 2000:
            return round(max_pts * 0.9, 1)  # 4.5 pts
        elif stars >= 500:
            return round(max_pts * 0.75, 1)  # 3.8 pts
        elif stars >= 100:
            return round(max_pts * 0.6, 1)  # 3.0 pts
        elif stars >= 20:
            return round(max_pts * 0.4, 1)  # 2.0 pts
        else:
            return round(max_pts * 0.2, 1)  # 1.0 pt

    def _evaluate_completeness(
        self,
        repo: RepositoryModel,
        analysis: Optional[RepositoryAnalysisResponse],
        max_pts: float
    ) -> float:
        """Evaluates automated tests, containerization, and configuration manifests (5%)."""
        score = 0.0

        if analysis:
            dep_files = [f.lower() for f in analysis.detected_dependency_files]
            strengths_text = " ".join(analysis.strengths).lower()

            # Tests present
            if "test" in strengths_text or "automated test" in strengths_text:
                score += (max_pts * 0.4)  # 2.0 pts

            # Containerized
            if any("docker" in f for f in dep_files):
                score += (max_pts * 0.3)  # 1.5 pts

            # Dependency manifests verified
            if any(f in ("requirements.txt", "pyproject.toml", "package.json", "go.mod") for f in dep_files):
                score += (max_pts * 0.3)  # 1.5 pts
        else:
            score = max_pts * 0.5

        return min(max_pts, round(score, 1))

    def _generate_explanation(
        self,
        total_score: int,
        matches: List[str],
        missing: List[str],
        analysis: Optional[RepositoryAnalysisResponse]
    ) -> str:
        """Produces a concise, professional explanation for why the repository matches."""
        matched_count = len(matches)
        total_reqs = matched_count + len(missing)

        if matched_count == total_reqs and matched_count > 0:
            summary = f"Satisfies all {matched_count}/{total_reqs} requested requirements ({', '.join(matches[:3])})."
        elif matched_count > 0:
            summary = f"Satisfies {matched_count}/{total_reqs} requirements ({', '.join(matches[:3])})."
        else:
            summary = "Broad semantic match based on project domain and topics."

        if analysis and analysis.documentation_quality == "High":
            summary += " Features high-quality documentation."

        return summary


# Global ranking service instance
ranking_service = RankingService()
