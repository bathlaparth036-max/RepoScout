import React, { useState } from 'react';
import {
  Star,
  GitFork,
  ExternalLink,
  Clock,
  Copy,
  Check,
  Terminal,
  Layers,
  ChevronDown,
  ChevronUp,
  Sliders,
  Bookmark,
  CheckSquare,
  Square,
} from 'lucide-react';
import {
  formatStars,
  formatForks,
  getLanguageColor,
  formatRelativeTime,
} from '../utils/formatters';

/**
 * Repository card displaying real GitHub repository metadata, intelligent ranking,
 * bookmarking, and multi-repository comparison:
 * - repository avatar, name, and owner
 * - explainable match score (0-100%)
 * - bookmark toggle & comparison checkbox
 * - why it matches explanation
 * - satisfied requirements (✓) & missing requirements (✗)
 * - 7-dimension score breakdown accordion
 * - topics, stars, forks, language, last updated
 * - analyze, clone, compare & GitHub links
 */
export function RepositoryCard({
  repository,
  onAnalyze,
  isSaved = false,
  onToggleSave,
  isSelectedForCompare = false,
  onToggleCompare,
}) {
  const [copied, setCopied] = useState(false);
  const [showBreakdown, setShowBreakdown] = useState(false);

  const {
    name,
    owner,
    owner_avatar_url,
    description,
    stars = 0,
    forks = 0,
    language,
    topics = [],
    updated_at,
    html_url,
    url,
    github_url,
    clone_url,
    match_percentage,
    match_score,
    score_breakdown,
    matches = [],
    missing = [],
    why_it_matches,
  } = repository;

  const targetUrl = html_url || url || github_url || `https://github.com/${owner}/${name}`;
  const formattedUpdated = formatRelativeTime(updated_at);
  const gitCloneCmd = clone_url || `${targetUrl}.git`;
  const finalScore = match_score ?? match_percentage;

  const handleCopyClone = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (navigator?.clipboard?.writeText) {
      navigator.clipboard.writeText(`git clone ${gitCloneCmd}`);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const getScoreBadgeClass = (score) => {
    if (score == null) return 'rs-match-badge';
    if (score >= 80) return 'rs-match-badge score-high';
    if (score >= 60) return 'rs-match-badge score-med';
    return 'rs-match-badge score-low';
  };

  return (
    <article className={`rs-card ${isSelectedForCompare ? 'rs-card-selected-compare' : ''}`}>
      {/* Top Header Bar */}
      <div className="rs-card-top">
        <div className="rs-card-header-left">
          {/* Repository Owner Avatar */}
          {owner_avatar_url ? (
            <img
              src={owner_avatar_url}
              alt={`${owner} avatar`}
              className="rs-repo-avatar"
              loading="lazy"
              onError={(e) => {
                e.target.style.display = 'none';
              }}
            />
          ) : (
            <div className="rs-repo-avatar rs-avatar-fallback">
              <Terminal size={12} color="#8b949e" />
            </div>
          )}

          {/* Owner / Repo Name */}
          <div className="rs-card-title-wrap">
            <span className="rs-card-owner">{owner} /</span>
            <a
              href={targetUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="rs-card-repo-link"
              title={`Open ${owner}/${name} on GitHub`}
            >
              {name}
            </a>
          </div>
        </div>

        {/* Right side: Bookmark & Score Badge */}
        <div className="rs-card-header-right">
          {onToggleSave && (
            <button
              type="button"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                onToggleSave(repository);
              }}
              className={`rs-bookmark-btn ${isSaved ? 'saved' : ''}`}
              title={isSaved ? 'Remove from saved' : 'Save repository to bookmarks'}
              aria-label={isSaved ? 'Remove from saved' : 'Save repository'}
            >
              <Bookmark
                size={14}
                fill={isSaved ? '#e3b341' : 'none'}
                color={isSaved ? '#e3b341' : '#8b949e'}
              />
            </button>
          )}

          {finalScore != null && (
            <span
              className={getScoreBadgeClass(finalScore)}
              title={`Relevance score: ${finalScore}/100 based on user requirements and tech stack`}
            >
              Match: {finalScore}%
            </span>
          )}
        </div>
      </div>

      {/* Description */}
      <p className="rs-card-desc">{description || 'No description provided.'}</p>

      {/* Why it Matches Explainability Callout */}
      {why_it_matches && (
        <div className="rs-why-matches-box">
          <span className="rs-why-label">Why it matches:</span>{' '}
          <span className="rs-why-content">{why_it_matches}</span>
        </div>
      )}

      {/* Requirements Matches & Missing Explanations */}
      {((matches && matches.length > 0) || (missing && missing.length > 0)) && (
        <div className="rs-ranking-reasons">
          {matches && matches.length > 0 && (
            <div className="rs-reasons-group">
              <span className="rs-reasons-label matches-label">Matches:</span>
              <div className="rs-reasons-tags">
                {matches.map((item, idx) => (
                  <span key={idx} className="rs-reason-tag rs-match-tag">
                    <span className="rs-check-symbol">✓</span>
                    <span>{item}</span>
                  </span>
                ))}
              </div>
            </div>
          )}

          {missing && missing.length > 0 && (
            <div className="rs-reasons-group">
              <span className="rs-reasons-label missing-label">Missing:</span>
              <div className="rs-reasons-tags">
                {missing.map((item, idx) => (
                  <span key={idx} className="rs-reason-tag rs-missing-tag">
                    <span className="rs-cross-symbol">✗</span>
                    <span>{item}</span>
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Configurable Multi-Factor Score Breakdown Accordion */}
      {score_breakdown && (
        <div className="rs-breakdown-container">
          <button
            type="button"
            className="rs-breakdown-toggle-btn"
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              setShowBreakdown(!showBreakdown);
            }}
            aria-expanded={showBreakdown}
            title="Toggle 7-factor scoring breakdown"
          >
            <Sliders size={11} />
            <span>Score Breakdown ({finalScore ?? 0}/100)</span>
            {showBreakdown ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
          </button>

          {showBreakdown && (
            <div className="rs-breakdown-table">
              <div className="rs-breakdown-row">
                <span className="rs-breakdown-dim">Requirement match (30%)</span>
                <span className="rs-breakdown-val">
                  <strong>{score_breakdown.requirement_match}</strong> / 30 pts
                </span>
              </div>
              <div className="rs-breakdown-row">
                <span className="rs-breakdown-dim">Technology match (20%)</span>
                <span className="rs-breakdown-val">
                  <strong>{score_breakdown.technology_match}</strong> / 20 pts
                </span>
              </div>
              <div className="rs-breakdown-row">
                <span className="rs-breakdown-dim">Architecture match (20%)</span>
                <span className="rs-breakdown-val">
                  <strong>{score_breakdown.architecture_match}</strong> / 20 pts
                </span>
              </div>
              <div className="rs-breakdown-row">
                <span className="rs-breakdown-dim">Documentation quality (10%)</span>
                <span className="rs-breakdown-val">
                  <strong>{score_breakdown.documentation}</strong> / 10 pts
                </span>
              </div>
              <div className="rs-breakdown-row">
                <span className="rs-breakdown-dim">Repository activity (10%)</span>
                <span className="rs-breakdown-val">
                  <strong>{score_breakdown.activity}</strong> / 10 pts
                </span>
              </div>
              <div className="rs-breakdown-row">
                <span className="rs-breakdown-dim">Popularity (5%)</span>
                <span className="rs-breakdown-val">
                  <strong>{score_breakdown.popularity}</strong> / 5 pts
                </span>
              </div>
              <div className="rs-breakdown-row">
                <span className="rs-breakdown-dim">Project completeness (5%)</span>
                <span className="rs-breakdown-val">
                  <strong>{score_breakdown.completeness}</strong> / 5 pts
                </span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Topic Tags */}
      {topics && topics.length > 0 && (
        <div className="rs-topics-row">
          {topics.slice(0, 5).map((topic, idx) => (
            <span key={idx} className="rs-topic-tag">
              #{topic}
            </span>
          ))}
          {topics.length > 5 && (
            <span className="rs-topic-tag" style={{ opacity: 0.7 }}>
              +{topics.length - 5}
            </span>
          )}
        </div>
      )}

      {/* Card Metadata / Stats Bar */}
      <div className="rs-card-meta">
        <div className="rs-card-stats">
          {/* Primary Language */}
          {language && (
            <span className="rs-stat-item" title={`Primary language: ${language}`}>
              <span
                className="rs-lang-dot"
                style={{ backgroundColor: getLanguageColor(language) }}
              />
              <span>{language}</span>
            </span>
          )}

          {/* Stars */}
          <span className="rs-stat-item" title={`${(stars || 0).toLocaleString()} GitHub stars`}>
            <Star size={12} strokeWidth={2.2} />
            <span>{formatStars(stars)}</span>
          </span>

          {/* Forks */}
          <span className="rs-stat-item" title={`${(forks || 0).toLocaleString()} forks`}>
            <GitFork size={12} strokeWidth={2.2} />
            <span>{formatForks(forks)}</span>
          </span>

          {/* Last Updated */}
          {formattedUpdated && (
            <span
              className="rs-stat-item"
              title={`Last updated: ${updated_at}`}
              style={{ opacity: 0.85 }}
            >
              <Clock size={11} strokeWidth={2} />
              <span>{formattedUpdated}</span>
            </span>
          )}
        </div>

        {/* Card Actions: Analyze, Compare, Clone & GitHub Button */}
        <div className="rs-card-actions">
          {onToggleCompare && (
            <button
              type="button"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                onToggleCompare(repository);
              }}
              className={`rs-view-btn rs-compare-toggle-btn ${isSelectedForCompare ? 'active' : ''}`}
              title={
                isSelectedForCompare
                  ? 'Remove from comparison'
                  : 'Add to side-by-side comparison (up to 3)'
              }
            >
              {isSelectedForCompare ? (
                <CheckSquare size={11} color="#3fb950" />
              ) : (
                <Square size={11} />
              )}
              <span>Compare</span>
            </button>
          )}

          {onAnalyze && (
            <button
              type="button"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                onAnalyze(repository);
              }}
              className="rs-view-btn rs-analyze-btn"
              title="Analyze repository architecture & technology stack"
            >
              <Layers size={11} />
              <span>Analyze</span>
            </button>
          )}

          <button
            type="button"
            onClick={handleCopyClone}
            className="rs-view-btn"
            title={`Copy: git clone ${gitCloneCmd}`}
          >
            {copied ? (
              <>
                <Check size={11} color="#3fb950" />
                <span style={{ color: '#3fb950' }}>Copied</span>
              </>
            ) : (
              <>
                <Copy size={11} />
                <span>Clone</span>
              </>
            )}
          </button>

          <a
            href={targetUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="rs-view-btn"
            title="Open repository in GitHub"
          >
            <span>GitHub</span>
            <ExternalLink size={10} />
          </a>
        </div>
      </div>
    </article>
  );
}
