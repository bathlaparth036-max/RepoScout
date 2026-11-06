import React, { useEffect, useState } from 'react';
import {
  ArrowLeft,
  Star,
  GitFork,
  ExternalLink,
  CheckCircle2,
  AlertTriangle,
  Layers,
  Cpu,
  BookOpen,
  Activity,
  CheckSquare,
  Gauge,
  FileCode,
  Terminal,
  RefreshCw,
  Sliders,
  Check,
  X,
  Workflow,
  ArrowDown,
  Database,
  Globe,
  Code2,
  Box,
  Key,
  Bookmark,
} from 'lucide-react';
import { analyzeRepository } from '../services/api';
import {
  formatStars,
  formatForks,
  getLanguageColor,
  formatRelativeTime
} from '../utils/formatters';

/**
 * Derives a sequential, visual pipeline representation for detected project architecture.
 * Strictly adheres to verified evidence; marks unverified stages as "Not detected".
 */
function buildArchitectureFlow(analysis) {
  if (!analysis) return [];

  const archSet = new Set((analysis.architecture_components || []).map((c) => c.toLowerCase()));
  const dbSet = new Set((analysis.databases || []).map((d) => d.toLowerCase()));
  const apiSet = new Set((analysis.apis || []).map((a) => a.toLowerCase()));
  const projectType = (analysis.project_type || '').toLowerCase();

  // Check if RAG or AI Retrieval pipeline signatures exist
  const isRag =
    projectType.includes('rag') ||
    projectType.includes('retrieval') ||
    archSet.has('document loading') ||
    archSet.has('retrieval') ||
    archSet.has('embeddings') ||
    archSet.has('vector database') ||
    dbSet.has('faiss') ||
    dbSet.has('chroma') ||
    dbSet.has('pinecone') ||
    dbSet.has('qdrant') ||
    dbSet.has('weaviate') ||
    dbSet.has('milvus');

  if (isRag) {
    let vectorDbName = 'Vector Database';
    if (dbSet.has('faiss')) vectorDbName = 'FAISS';
    else if (dbSet.has('chroma')) vectorDbName = 'Chroma';
    else if (dbSet.has('pinecone')) vectorDbName = 'Pinecone';
    else if (dbSet.has('qdrant')) vectorDbName = 'Qdrant';
    else if (dbSet.has('weaviate')) vectorDbName = 'Weaviate';
    else if (dbSet.has('milvus')) vectorDbName = 'Milvus';
    else if (dbSet.has('pgvector')) vectorDbName = 'pgvector';

    let llmName = 'LLM';
    if (apiSet.has('openai')) llmName = 'ChatOpenAI / LLM';
    else if (apiSet.has('anthropic claude')) llmName = 'Claude / LLM';
    else if (apiSet.has('ollama')) llmName = 'Ollama / Local LLM';
    else if (apiSet.has('vllm')) llmName = 'vLLM / LLM';

    return [
      {
        id: 'docs',
        title: 'Documents',
        category: 'Data Source',
        detected: true,
        detail: 'PDFs, text, markdown, or web files',
        isBoundary: true,
      },
      {
        id: 'loader',
        title: 'Document Loader',
        category: 'Ingestion',
        detected: archSet.has('document loading'),
        detail: archSet.has('document loading')
          ? 'Verified parser & document ingestion module'
          : 'Not detected in code structure',
      },
      {
        id: 'chunking',
        title: 'Chunking',
        category: 'Preprocessing',
        detected: archSet.has('text splitting/chunking'),
        detail: archSet.has('text splitting/chunking')
          ? 'Boundary-aware text splitter & chunker'
          : 'Not detected in code structure',
      },
      {
        id: 'embeddings',
        title: 'Embeddings',
        category: 'Representation',
        detected: archSet.has('embeddings'),
        detail: archSet.has('embeddings')
          ? 'Dense semantic vector embedding model'
          : 'Not detected in code structure',
      },
      {
        id: 'vectordb',
        title: vectorDbName,
        category: 'Storage & Indexing',
        detected:
          archSet.has('vector database') ||
          dbSet.has('faiss') ||
          dbSet.has('chroma') ||
          dbSet.has('pinecone') ||
          dbSet.has('qdrant') ||
          dbSet.has('weaviate'),
        detail:
          archSet.has('vector database') || dbSet.size > 0
            ? 'Indexed similarity vector search storage'
            : 'Not detected in code structure',
      },
      {
        id: 'retriever',
        title: 'Retriever',
        category: 'Context Retrieval',
        detected: archSet.has('retrieval'),
        detail: archSet.has('retrieval')
          ? 'Semantic or hybrid similarity query engine'
          : 'Not detected in code structure',
      },
      {
        id: 'llm',
        title: llmName,
        category: 'Generation',
        detected:
          archSet.has('llm generation') ||
          apiSet.has('openai') ||
          apiSet.has('anthropic claude') ||
          apiSet.has('ollama') ||
          apiSet.has('vllm'),
        detail:
          archSet.has('llm generation') || apiSet.size > 0
            ? 'Context-augmented prompt synthesis & inference'
            : 'Not detected in code structure',
      },
      {
        id: 'response',
        title: 'Response',
        category: 'Output',
        detected: true,
        detail: 'Synthesized grounded answer',
        isBoundary: true,
      },
    ];
  }

  // REST API / Backend Service Pipeline
  if (
    projectType.includes('api') ||
    projectType.includes('backend') ||
    projectType.includes('rest') ||
    (analysis.frameworks || []).some((f) => ['FastAPI', 'Express', 'Flask', 'Django'].includes(f))
  ) {
    const fwk = (analysis.frameworks || []).find((f) => ['FastAPI', 'Express', 'Flask', 'Django'].includes(f)) || 'API Router';
    const db = (analysis.databases || [])[0] || 'Database / Persistence';

    return [
      { id: 'client', title: 'HTTP Client Request', category: 'Request', detected: true, detail: 'Incoming REST / JSON payload', isBoundary: true },
      { id: 'router', title: fwk, category: 'Gateway / Routing', detected: (analysis.frameworks || []).length > 0, detail: 'Route handlers, validation & schemas' },
      { id: 'services', title: 'Service Controllers', category: 'Business Logic', detected: true, detail: 'Domain logic & endpoint handlers' },
      { id: 'db', title: db, category: 'Persistence', detected: (analysis.databases || []).length > 0, detail: 'Database storage / ORM models' },
      { id: 'res', title: 'HTTP JSON Response', category: 'Response', detected: true, detail: 'Formatted API payload', isBoundary: true },
    ];
  }

  // General modular components flow
  if (analysis.architecture_components && analysis.architecture_components.length > 0) {
    return analysis.architecture_components.map((comp, idx) => ({
      id: `comp-${idx}`,
      title: comp,
      category: 'Verified Component',
      detected: true,
      detail: 'Detected from repository structure & code patterns',
    }));
  }

  return [];
}

/**
 * Complete Repository Detail Experience:
 * - HEADER: Name, owner, GitHub link, stars, forks, language
 * - MATCH SECTION: Overall match percentage, match explanation, score breakdown
 * - TECHNOLOGY SECTION: Languages, frameworks, libraries, databases, APIs
 * - ARCHITECTURE SECTION: Visual pipeline flow with "↓" connectors
 * - PROJECT QUALITY: Documentation, activity, completeness, difficulty
 * - STRENGTHS: Positive findings
 * - LIMITATIONS: Weaknesses and missing areas
 * - CONTROLS: Back to results, Open GitHub, Re-analyze
 */
export function AnalysisPanel({ repository, onBack, isSaved = false, onToggleSave }) {
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isReanalyzing, setIsReanalyzing] = useState(false);
  const [error, setError] = useState(null);

  const owner = repository.owner;
  const repoName = repository.name;

  const fetchAnalysis = async (refresh = false) => {
    if (refresh) {
      setIsReanalyzing(true);
    } else {
      setLoading(true);
    }
    setError(null);

    try {
      const data = await analyzeRepository(owner, repoName, refresh);
      setAnalysis(data);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
      setIsReanalyzing(false);
    }
  };

  useEffect(() => {
    fetchAnalysis(false);
  }, [owner, repoName]);

  const targetUrl =
    repository.html_url ||
    repository.url ||
    repository.github_url ||
    (analysis && analysis.html_url) ||
    `https://github.com/${owner}/${repoName}`;

  const primaryLang =
    (analysis && analysis.languages && analysis.languages[0]) ||
    repository.language;

  const starsCount = (analysis && analysis.stars) ?? repository.stars ?? 0;
  const forksCount = (analysis && analysis.forks) ?? repository.forks ?? 0;

  // Match Section Data (passed from ranked search)
  const matchScore = repository.match_score ?? repository.match_percentage;
  const scoreBreakdown = repository.score_breakdown;
  const whyItMatches = repository.why_it_matches;
  const matchesList = repository.matches || [];
  const missingList = repository.missing || [];

  // Architecture Flow Data
  const architectureFlow = buildArchitectureFlow(analysis);

  // Quality metrics data
  const updatedTime = repository.updated_at || (analysis && analysis.updated_at);
  const formattedRelative = formatRelativeTime(updatedTime);

  const getBadgeColorClass = (score) => {
    if (score == null) return 'rs-metric-badge';
    if (score >= 80) return 'rs-metric-badge high';
    if (score >= 60) return 'rs-metric-badge moderate';
    return 'rs-metric-badge minimal';
  };

  return (
    <div className="rs-container rs-detail-container" style={{ padding: 0 }}>
      {/* Top Action & Navigation Bar */}
      <div className="rs-nav-bar">
        <button
          type="button"
          onClick={onBack}
          className="rs-back-btn"
          title="Return to search results"
        >
          <ArrowLeft size={13} />
          <span>Back to results</span>
        </button>

        <div className="rs-breadcrumb">
          <span className="rs-breadcrumb-owner">{owner}</span>
          <span className="rs-breadcrumb-sep">/</span>
          <span className="rs-breadcrumb-name">{repoName}</span>
        </div>

        <div className="rs-nav-actions">
          {onToggleSave && (
            <button
              type="button"
              onClick={() => onToggleSave(repository)}
              className={`rs-view-btn ${isSaved ? 'rs-saved-active' : ''}`}
              title={isSaved ? 'Remove from saved repositories' : 'Save to bookmarks'}
            >
              <Bookmark
                size={11}
                fill={isSaved ? '#e3b341' : 'none'}
                color={isSaved ? '#e3b341' : 'currentColor'}
              />
              <span>{isSaved ? 'Saved' : 'Save'}</span>
            </button>
          )}

          <button
            type="button"
            onClick={() => fetchAnalysis(true)}
            className="rs-view-btn rs-reanalyze-btn"
            disabled={loading || isReanalyzing}
            title="Bypass cache and re-analyze repository"
          >
            <RefreshCw size={11} className={isReanalyzing ? 'rs-spin' : ''} />
            <span>{isReanalyzing ? 'Analyzing...' : 'Re-analyze'}</span>
          </button>

          <a
            href={targetUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="rs-view-btn rs-open-github-btn"
            title="Open repository on GitHub"
          >
            <span>Open GitHub</span>
            <ExternalLink size={11} />
          </a>
        </div>
      </div>

      <div className="rs-analysis-scroll">
        {/* Loading State Skeleton */}
        {loading && (
          <div className="rs-list">
            <div className="rs-status-stage">
              <span className="rs-spinner" />
              <span>Analyzing architecture components, README, and dependency manifests...</span>
            </div>
            <div className="rs-skeleton-card">
              <div className="rs-skeleton-line" style={{ width: '65%', height: '18px' }} />
              <div className="rs-skeleton-line" style={{ width: '90%', height: '12px' }} />
              <div className="rs-skeleton-line" style={{ width: '45%', height: '12px' }} />
            </div>
            <div className="rs-skeleton-card">
              <div className="rs-skeleton-line" style={{ width: '40%', height: '14px' }} />
              <div style={{ display: 'flex', gap: '8px' }}>
                <div className="rs-skeleton-line" style={{ width: '80px', height: '22px' }} />
                <div className="rs-skeleton-line" style={{ width: '90px', height: '22px' }} />
                <div className="rs-skeleton-line" style={{ width: '70px', height: '22px' }} />
              </div>
            </div>
          </div>
        )}

        {/* Error State */}
        {error && !loading && (
          <div className="rs-banner error" style={{ margin: '14px 0' }}>
            <AlertTriangle size={16} className="rs-banner-icon" style={{ flexShrink: 0 }} />
            <div className="rs-banner-content">
              <div className="rs-banner-title">Repository Analysis Unavailable</div>
              <div className="rs-banner-detail">{error.message}</div>
              <div style={{ marginTop: '8px' }}>
                <button
                  type="button"
                  onClick={() => fetchAnalysis(true)}
                  className="rs-search-btn"
                  style={{ display: 'inline-flex' }}
                >
                  <RefreshCw size={11} />
                  <span>Retry Analysis</span>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Complete Repository Detail View */}
        {analysis && !loading && (
          <>
            {/* =========================================================================
                1. HEADER SECTION
                - Repository name
                - Owner
                - GitHub link
                - Stars
                - Forks
                - Language
                ========================================================================= */}
            <section className="rs-section rs-detail-header-card">
              <div className="rs-header-top-row">
                <div className="rs-header-identity">
                  {analysis.owner_avatar_url || repository.owner_avatar_url ? (
                    <img
                      src={analysis.owner_avatar_url || repository.owner_avatar_url}
                      alt={`${owner} avatar`}
                      className="rs-repo-avatar-lg"
                      loading="lazy"
                      onError={(e) => {
                        e.target.style.display = 'none';
                      }}
                    />
                  ) : (
                    <div className="rs-repo-avatar-lg rs-avatar-fallback">
                      <Terminal size={16} color="#8b949e" />
                    </div>
                  )}

                  <div>
                    <div className="rs-header-owner">{owner}</div>
                    <h1 className="rs-header-name">{repoName}</h1>
                  </div>
                </div>

                <a
                  href={targetUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="rs-view-btn rs-header-github-btn"
                  title="Open on GitHub"
                >
                  <span>Open on GitHub</span>
                  <ExternalLink size={12} />
                </a>
              </div>

              {/* Description */}
              <p className="rs-card-desc rs-detail-desc">
                {analysis.description || repository.description || 'No description provided by author.'}
              </p>

              {/* Stats Bar: Language, Stars, Forks, Branch */}
              <div className="rs-header-stats-bar">
                {/* Language */}
                {primaryLang ? (
                  <span className="rs-stat-item" title={`Primary language: ${primaryLang}`}>
                    <span
                      className="rs-lang-dot"
                      style={{ backgroundColor: getLanguageColor(primaryLang) }}
                    />
                    <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{primaryLang}</span>
                  </span>
                ) : (
                  <span className="rs-stat-item rs-not-detected-inline">
                    Language: Not detected
                  </span>
                )}

                {/* Stars */}
                <span className="rs-stat-item" title={`${starsCount.toLocaleString()} GitHub stars`}>
                  <Star size={13} strokeWidth={2.2} />
                  <span><strong>{formatStars(starsCount)}</strong> stars</span>
                </span>

                {/* Forks */}
                <span className="rs-stat-item" title={`${forksCount.toLocaleString()} forks`}>
                  <GitFork size={13} strokeWidth={2.2} />
                  <span><strong>{formatForks(forksCount)}</strong> forks</span>
                </span>

                {/* Default branch */}
                {analysis.default_branch && (
                  <span className="rs-stat-item" title={`Default branch: ${analysis.default_branch}`}>
                    <Terminal size={12} />
                    <span>branch: <code>{analysis.default_branch}</code></span>
                  </span>
                )}
              </div>
            </section>

            {/* =========================================================================
                2. MATCH SECTION
                - Overall match percentage
                - Match explanation
                - Score breakdown
                ========================================================================= */}
            <section className="rs-section rs-match-section">
              <div className="rs-section-header">
                <span className="rs-section-title">
                  <Sliders size={13} />
                  <span>Match Evaluation</span>
                </span>
                {matchScore != null && (
                  <span className={getBadgeColorClass(matchScore)}>
                    {matchScore}% Match
                  </span>
                )}
              </div>

              {matchScore != null ? (
                <div className="rs-match-content">
                  {/* Top Match Score & Explanation Callout */}
                  <div className="rs-match-overview-box">
                    <div className="rs-match-score-display">
                      <span className="rs-match-big-number">{matchScore}%</span>
                      <span className="rs-match-score-caption">Relevance Score</span>
                    </div>

                    <div className="rs-match-explanation-block">
                      <div className="rs-match-explanation-title">Match Explanation:</div>
                      <div className="rs-match-explanation-text">
                        {whyItMatches || 'Satisfies project domain, architecture, and technology stack criteria.'}
                      </div>

                      {/* Satisfied vs Missing Criteria */}
                      {((matchesList && matchesList.length > 0) || (missingList && missingList.length > 0)) && (
                        <div className="rs-criteria-split">
                          {matchesList.length > 0 && (
                            <div className="rs-criteria-col">
                              <span className="rs-criteria-header matches">Satisfied:</span>
                              <div className="rs-reasons-tags">
                                {matchesList.map((item, idx) => (
                                  <span key={idx} className="rs-reason-tag rs-match-tag">
                                    <span className="rs-check-symbol">✓</span> {item}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}

                          {missingList.length > 0 && (
                            <div className="rs-criteria-col">
                              <span className="rs-criteria-header missing">Missing:</span>
                              <div className="rs-reasons-tags">
                                {missingList.map((item, idx) => (
                                  <span key={idx} className="rs-reason-tag rs-missing-tag">
                                    <span className="rs-cross-symbol">✗</span> {item}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* 7-Factor Score Breakdown */}
                  {scoreBreakdown && (
                    <div className="rs-breakdown-wrapper-full">
                      <div className="rs-breakdown-title">Score Breakdown (100% Weight Model):</div>
                      <div className="rs-breakdown-grid-detailed">
                        <div className="rs-breakdown-card">
                          <span className="rs-dim-name">Requirement Match</span>
                          <span className="rs-dim-weight">30%</span>
                          <span className="rs-dim-score"><strong>{scoreBreakdown.requirement_match}</strong> / 30 pts</span>
                        </div>
                        <div className="rs-breakdown-card">
                          <span className="rs-dim-name">Technology Match</span>
                          <span className="rs-dim-weight">20%</span>
                          <span className="rs-dim-score"><strong>{scoreBreakdown.technology_match}</strong> / 20 pts</span>
                        </div>
                        <div className="rs-breakdown-card">
                          <span className="rs-dim-name">Architecture Match</span>
                          <span className="rs-dim-weight">20%</span>
                          <span className="rs-dim-score"><strong>{scoreBreakdown.architecture_match}</strong> / 20 pts</span>
                        </div>
                        <div className="rs-breakdown-card">
                          <span className="rs-dim-name">Documentation</span>
                          <span className="rs-dim-weight">10%</span>
                          <span className="rs-dim-score"><strong>{scoreBreakdown.documentation}</strong> / 10 pts</span>
                        </div>
                        <div className="rs-breakdown-card">
                          <span className="rs-dim-name">Activity Freshness</span>
                          <span className="rs-dim-weight">10%</span>
                          <span className="rs-dim-score"><strong>{scoreBreakdown.activity}</strong> / 10 pts</span>
                        </div>
                        <div className="rs-breakdown-card">
                          <span className="rs-dim-name">Popularity</span>
                          <span className="rs-dim-weight">5%</span>
                          <span className="rs-dim-score"><strong>{scoreBreakdown.popularity}</strong> / 5 pts</span>
                        </div>
                        <div className="rs-breakdown-card">
                          <span className="rs-dim-name">Completeness</span>
                          <span className="rs-dim-weight">5%</span>
                          <span className="rs-dim-score"><strong>{scoreBreakdown.completeness}</strong> / 5 pts</span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="rs-not-detected-card">
                  Not evaluated against an active requirement query. Search with natural language requirements to view relevance scoring.
                </div>
              )}
            </section>

            {/* =========================================================================
                3. TECHNOLOGY SECTION
                Display detected:
                - Languages
                - Frameworks
                - Libraries
                - Databases
                - APIs
                Never invent analysis results. Show "Not detected" when evidence is unavailable.
                ========================================================================= */}
            <section className="rs-section rs-technology-section">
              <div className="rs-section-header">
                <span className="rs-section-title">
                  <Cpu size={13} />
                  <span>Technology Stack</span>
                </span>
                <span className="rs-section-badge">
                  {analysis.technologies.length} detected
                </span>
              </div>

              <div className="rs-tech-categories-list">
                {/* 1. Languages */}
                <div className="rs-tech-category-row">
                  <div className="rs-tech-cat-title">
                    <Code2 size={12} />
                    <span>Languages:</span>
                  </div>
                  <div className="rs-tech-cat-pills">
                    {analysis.languages && analysis.languages.length > 0 ? (
                      analysis.languages.map((lang, idx) => (
                        <span key={idx} className="rs-tech-pill">
                          <span
                            className="rs-lang-dot"
                            style={{ backgroundColor: getLanguageColor(lang) }}
                          />
                          <span>{lang}</span>
                        </span>
                      ))
                    ) : (
                      <span className="rs-not-detected">Not detected</span>
                    )}
                  </div>
                </div>

                {/* 2. Frameworks */}
                <div className="rs-tech-category-row">
                  <div className="rs-tech-cat-title">
                    <Workflow size={12} />
                    <span>Frameworks:</span>
                  </div>
                  <div className="rs-tech-cat-pills">
                    {analysis.frameworks && analysis.frameworks.length > 0 ? (
                      analysis.frameworks.map((fwk, idx) => (
                        <span key={idx} className="rs-tech-pill rs-framework-pill">
                          {fwk}
                        </span>
                      ))
                    ) : (
                      <span className="rs-not-detected">Not detected</span>
                    )}
                  </div>
                </div>

                {/* 3. Libraries */}
                <div className="rs-tech-category-row">
                  <div className="rs-tech-cat-title">
                    <Box size={12} />
                    <span>Libraries:</span>
                  </div>
                  <div className="rs-tech-cat-pills">
                    {analysis.libraries && analysis.libraries.length > 0 ? (
                      analysis.libraries.map((lib, idx) => (
                        <span key={idx} className="rs-tech-pill rs-library-pill">
                          {lib}
                        </span>
                      ))
                    ) : (
                      <span className="rs-not-detected">Not detected</span>
                    )}
                  </div>
                </div>

                {/* 4. Databases */}
                <div className="rs-tech-category-row">
                  <div className="rs-tech-cat-title">
                    <Database size={12} />
                    <span>Databases:</span>
                  </div>
                  <div className="rs-tech-cat-pills">
                    {analysis.databases && analysis.databases.length > 0 ? (
                      analysis.databases.map((db, idx) => (
                        <span key={idx} className="rs-tech-pill rs-database-pill">
                          {db}
                        </span>
                      ))
                    ) : (
                      <span className="rs-not-detected">Not detected</span>
                    )}
                  </div>
                </div>

                {/* 5. APIs */}
                <div className="rs-tech-category-row">
                  <div className="rs-tech-cat-title">
                    <Globe size={12} />
                    <span>APIs:</span>
                  </div>
                  <div className="rs-tech-cat-pills">
                    {analysis.apis && analysis.apis.length > 0 ? (
                      analysis.apis.map((apiItem, idx) => (
                        <span key={idx} className="rs-tech-pill rs-api-pill">
                          {apiItem}
                        </span>
                      ))
                    ) : (
                      <span className="rs-not-detected">Not detected</span>
                    )}
                  </div>
                </div>
              </div>

              {/* Verified Dependency Files / Manifests */}
              {analysis.detected_dependency_files && analysis.detected_dependency_files.length > 0 && (
                <div className="rs-verified-manifests-row">
                  <div className="rs-manifests-label">
                    Verified Manifests ({analysis.detected_dependency_files.length}):
                  </div>
                  <div className="rs-manifests-pills">
                    {analysis.detected_dependency_files.map((file, idx) => (
                      <span key={idx} className="rs-manifest-tag">
                        <FileCode size={10} />
                        <span>{file}</span>
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </section>

            {/* =========================================================================
                4. ARCHITECTURE SECTION
                Show the detected project architecture.
                For example:
                Documents
                ↓
                Document Loader
                ↓
                Chunking
                ↓
                Embeddings
                ↓
                FAISS
                ↓
                Retriever
                ↓
                LLM
                ↓
                Response
                Use a clean visual architecture representation.
                ========================================================================= */}
            <section className="rs-section rs-architecture-section">
              <div className="rs-section-header">
                <span className="rs-section-title">
                  <Layers size={13} />
                  <span>Project Architecture</span>
                </span>
                <span
                  className="rs-match-badge"
                  style={{ background: '#1c2128', borderColor: '#30363d', color: '#f0f6fc' }}
                >
                  {analysis.project_type}
                </span>
              </div>

              {architectureFlow.length > 0 ? (
                <div className="rs-pipeline-flow">
                  {architectureFlow.map((node, idx) => {
                    const isLast = idx === architectureFlow.length - 1;
                    return (
                      <React.Fragment key={node.id || idx}>
                        <div className={`rs-pipeline-node ${node.detected ? 'detected' : 'unverified'} ${node.isBoundary ? 'boundary' : ''}`}>
                          <div className="rs-node-top">
                            <span className="rs-node-category">{node.category}</span>
                            {node.isBoundary ? (
                              <span className="rs-node-status-badge boundary">Endpoint</span>
                            ) : node.detected ? (
                              <span className="rs-node-status-badge verified">
                                <Check size={10} /> Verified
                              </span>
                            ) : (
                              <span className="rs-node-status-badge not-detected">
                                Not detected
                              </span>
                            )}
                          </div>

                          <div className="rs-node-title">{node.title}</div>
                          {node.detail && (
                            <div className="rs-node-detail">{node.detail}</div>
                          )}
                        </div>

                        {!isLast && (
                          <div className="rs-pipeline-connector">
                            <div className="rs-connector-line" />
                            <div className="rs-connector-arrow">↓</div>
                            <div className="rs-connector-line" />
                          </div>
                        )}
                      </React.Fragment>
                    );
                  })}
                </div>
              ) : (
                <div className="rs-not-detected-card">
                  Not detected — Modular codebase structure without monolithic pipeline signatures.
                </div>
              )}
            </section>

            {/* =========================================================================
                5. PROJECT QUALITY SECTION
                Show:
                - Documentation
                - Activity
                - Completeness
                - Difficulty
                ========================================================================= */}
            <section className="rs-section rs-quality-section">
              <div className="rs-section-header">
                <span className="rs-section-title">
                  <Gauge size={13} />
                  <span>Project Quality</span>
                </span>
              </div>

              <div className="rs-quality-grid">
                {/* 1. Documentation */}
                <div className="rs-quality-card">
                  <div className="rs-quality-card-header">
                    <span className="rs-quality-metric-title">
                      <BookOpen size={12} /> Documentation
                    </span>
                    <span className={`rs-metric-badge ${analysis.documentation_quality.toLowerCase()}`}>
                      {analysis.documentation_quality}
                    </span>
                  </div>
                  <div className="rs-quality-card-desc">
                    {analysis.documentation_quality === 'High'
                      ? 'Comprehensive README with setup instructions, usage examples, and architecture overview.'
                      : analysis.documentation_quality === 'Moderate'
                      ? 'Standard README with basic installation and execution guidance.'
                      : 'Minimal README documentation; limited quickstart guidance.'}
                  </div>
                </div>

                {/* 2. Activity */}
                <div className="rs-quality-card">
                  <div className="rs-quality-card-header">
                    <span className="rs-quality-metric-title">
                      <Activity size={12} /> Activity
                    </span>
                    <span className={`rs-metric-badge ${analysis.activity_status?.toLowerCase().includes('active') ? 'high' : 'moderate'}`}>
                      {analysis.activity_status ? analysis.activity_status.split('(')[0].trim() : 'Active'}
                    </span>
                  </div>
                  <div className="rs-quality-card-desc">
                    {formattedRelative
                      ? `Last active: ${formattedRelative}`
                      : analysis.activity_status || 'Recent commit and update activity observed.'}
                  </div>
                </div>

                {/* 3. Completeness */}
                <div className="rs-quality-card">
                  <div className="rs-quality-card-header">
                    <span className="rs-quality-metric-title">
                      <CheckSquare size={12} /> Completeness
                    </span>
                    <span className={`rs-metric-badge ${analysis.completeness_status?.toLowerCase().includes('high') ? 'high' : 'moderate'}`}>
                      {analysis.completeness_status ? analysis.completeness_status.split('(')[0].trim() : 'Moderate'}
                    </span>
                  </div>
                  <div className="rs-quality-card-desc">
                    {analysis.completeness_status ||
                      'Verified configuration manifests, dependencies, and code structure present.'}
                  </div>
                </div>

                {/* 4. Difficulty */}
                <div className="rs-quality-card">
                  <div className="rs-quality-card-header">
                    <span className="rs-quality-metric-title">
                      <Sliders size={12} /> Difficulty
                    </span>
                    <span className={`rs-metric-badge ${analysis.difficulty.toLowerCase()}`}>
                      {analysis.difficulty}
                    </span>
                  </div>
                  <div className="rs-quality-card-desc">
                    {analysis.difficulty === 'Beginner'
                      ? 'Beginner-friendly structure with tutorials, simple scripts, or notebooks.'
                      : analysis.difficulty === 'Intermediate'
                      ? 'Standard modular architecture requiring familiar tech stack knowledge.'
                      : 'Advanced distributed architecture or multi-component infrastructure.'}
                  </div>
                </div>
              </div>
            </section>

            {/* =========================================================================
                6. STRENGTHS & LIMITATIONS
                Show positive findings and missing or weak areas.
                Never invent analysis results.
                ========================================================================= */}
            <div className="rs-insights-grid">
              {/* Strengths */}
              <section className="rs-section rs-strengths-section">
                <div className="rs-section-header">
                  <span className="rs-section-title" style={{ color: 'var(--accent-green)' }}>
                    <CheckCircle2 size={13} />
                    <span>Strengths</span>
                  </span>
                  <span className="rs-section-badge">
                    {analysis.strengths ? analysis.strengths.length : 0}
                  </span>
                </div>

                {analysis.strengths && analysis.strengths.length > 0 ? (
                  <div className="rs-bullets-list">
                    {analysis.strengths.map((str, idx) => (
                      <div key={idx} className="rs-bullet-item strength">
                        <span className="rs-bullet-icon-good">✓</span>
                        <span>{str}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="rs-not-detected">Not detected</div>
                )}
              </section>

              {/* Limitations */}
              <section className="rs-section rs-limitations-section">
                <div className="rs-section-header">
                  <span className="rs-section-title" style={{ color: 'var(--accent-amber)' }}>
                    <AlertTriangle size={13} />
                    <span>Limitations</span>
                  </span>
                  <span className="rs-section-badge">
                    {analysis.limitations ? analysis.limitations.length : 0}
                  </span>
                </div>

                {analysis.limitations && analysis.limitations.length > 0 ? (
                  <div className="rs-bullets-list">
                    {analysis.limitations.map((lim, idx) => (
                      <div key={idx} className="rs-bullet-item limitation">
                        <span className="rs-bullet-icon-warn">▲</span>
                        <span>{lim}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="rs-not-detected">None detected</div>
                )}
              </section>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
