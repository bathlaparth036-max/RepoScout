import React from 'react';
import {
  X,
  Star,
  GitFork,
  ExternalLink,
  Layers,
  CheckCircle2,
  AlertTriangle,
  Code2,
  Workflow,
  Activity,
  Award,
} from 'lucide-react';
import { formatStars, formatForks, getLanguageColor } from '../utils/formatters';

/**
 * Side-by-side multi-repository comparison modal:
 * Compares 2-3 repositories on:
 * - Match relevance score & multi-factor breakdown
 * - Primary language & detected tech stack
 * - Verified architecture components
 * - Documentation & activity status
 * - Strengths & limitations
 */
export function CompareModal({
  repositories = [],
  onClose,
  onRemoveRepo,
  onAnalyze,
}) {
  if (!repositories || repositories.length === 0) return null;

  return (
    <div className="rs-modal-overlay" onClick={onClose}>
      <div
        className="rs-compare-modal-content"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-label="Repository Comparison"
      >
        {/* Modal Top Bar */}
        <div className="rs-compare-top-bar">
          <div className="rs-compare-header-title">
            <Layers size={16} />
            <span>Repository Comparison</span>
            <span className="rs-compare-count-badge">
              {repositories.length} {repositories.length === 1 ? 'project' : 'projects'}
            </span>
          </div>
          <button
            type="button"
            className="rs-modal-close-btn"
            onClick={onClose}
            title="Close comparison"
          >
            <X size={15} />
          </button>
        </div>

        {/* Comparison Table / Grid */}
        <div className="rs-compare-scroll-area">
          <table className="rs-compare-table">
            <thead>
              <tr>
                <th className="rs-compare-row-label">Feature / Metric</th>
                {repositories.map((repo) => {
                  const targetUrl =
                    repo.html_url || repo.url || `https://github.com/${repo.owner}/${repo.name}`;
                  const score = repo.match_score ?? repo.match_percentage;

                  return (
                    <th key={`${repo.owner}-${repo.name}`} className="rs-compare-col-header">
                      <div className="rs-compare-card-head">
                        <div className="rs-compare-title-row">
                          <span className="rs-compare-repo-name">
                            <span className="rs-card-owner">{repo.owner}/</span>
                            {repo.name}
                          </span>
                          <button
                            type="button"
                            className="rs-compare-remove-btn"
                            onClick={() => onRemoveRepo(repo)}
                            title="Remove from comparison"
                          >
                            <X size={12} />
                          </button>
                        </div>

                        {/* Match Score Badge */}
                        {score != null ? (
                          <div
                            className={`rs-match-badge ${
                              score >= 80 ? 'score-high' : score >= 60 ? 'score-med' : 'score-low'
                            }`}
                            style={{ margin: '6px 0', alignSelf: 'flex-start' }}
                          >
                            Match: {score}%
                          </div>
                        ) : (
                          <div className="rs-match-badge" style={{ margin: '6px 0', alignSelf: 'flex-start' }}>
                            Score: N/A
                          </div>
                        )}

                        {/* Stats Row */}
                        <div className="rs-compare-stats-row">
                          {repo.language && (
                            <span className="rs-stat-item">
                              <span
                                className="rs-lang-dot"
                                style={{ backgroundColor: getLanguageColor(repo.language) }}
                              />
                              <span>{repo.language}</span>
                            </span>
                          )}
                          <span className="rs-stat-item">
                            <Star size={11} />
                            <span>{formatStars(repo.stars || 0)}</span>
                          </span>
                          <span className="rs-stat-item">
                            <GitFork size={11} />
                            <span>{formatForks(repo.forks || 0)}</span>
                          </span>
                        </div>

                        {/* Actions */}
                        <div className="rs-compare-actions">
                          {onAnalyze && (
                            <button
                              type="button"
                              className="rs-view-btn rs-analyze-btn"
                              onClick={() => {
                                onClose();
                                onAnalyze(repo);
                              }}
                              title="Inspect full architectural analysis"
                            >
                              <Layers size={10} />
                              <span>Analyze</span>
                            </button>
                          )}
                          <a
                            href={targetUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="rs-view-btn"
                            title="Open repository on GitHub"
                          >
                            <span>GitHub</span>
                            <ExternalLink size={10} />
                          </a>
                        </div>
                      </div>
                    </th>
                  );
                })}
              </tr>
            </thead>

            <tbody>
              {/* Row: Why it matches / Summary */}
              <tr>
                <td className="rs-compare-row-label">Relevance Summary</td>
                {repositories.map((repo) => (
                  <td key={`${repo.owner}-${repo.name}`} className="rs-compare-cell">
                    {repo.why_it_matches ? (
                      <span className="rs-compare-why-text">{repo.why_it_matches}</span>
                    ) : (
                      <span className="rs-cell-muted">{repo.description || 'No description'}</span>
                    )}
                  </td>
                ))}
              </tr>

              {/* Row: Score Breakdown */}
              <tr>
                <td className="rs-compare-row-label">Score Breakdown</td>
                {repositories.map((repo) => {
                  const b = repo.score_breakdown;
                  if (!b) {
                    return (
                      <td key={`${repo.owner}-${repo.name}`} className="rs-compare-cell rs-cell-muted">
                        Not evaluated
                      </td>
                    );
                  }
                  return (
                    <td key={`${repo.owner}-${repo.name}`} className="rs-compare-cell">
                      <div className="rs-compare-mini-breakdown">
                        <div>
                          <span>Requirement:</span> <strong>{b.requirement_match}/30</strong>
                        </div>
                        <div>
                          <span>Tech Stack:</span> <strong>{b.technology_match}/20</strong>
                        </div>
                        <div>
                          <span>Architecture:</span> <strong>{b.architecture_match}/20</strong>
                        </div>
                        <div>
                          <span>Documentation:</span> <strong>{b.documentation}/10</strong>
                        </div>
                        <div>
                          <span>Activity:</span> <strong>{b.activity}/10</strong>
                        </div>
                        <div>
                          <span>Popularity & Completeness:</span>{' '}
                          <strong>{(b.popularity || 0) + (b.completeness || 0)}/10</strong>
                        </div>
                      </div>
                    </td>
                  );
                })}
              </tr>

              {/* Row: Satisfied Matches */}
              <tr>
                <td className="rs-compare-row-label">Satisfied Requirements</td>
                {repositories.map((repo) => (
                  <td key={`${repo.owner}-${repo.name}`} className="rs-compare-cell">
                    {repo.matches && repo.matches.length > 0 ? (
                      <div className="rs-reasons-tags">
                        {repo.matches.map((item, idx) => (
                          <span key={idx} className="rs-reason-tag rs-match-tag">
                            ✓ {item}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="rs-cell-muted">None listed</span>
                    )}
                  </td>
                ))}
              </tr>

              {/* Row: Missing Requirements */}
              <tr>
                <td className="rs-compare-row-label">Missing Requirements</td>
                {repositories.map((repo) => (
                  <td key={`${repo.owner}-${repo.name}`} className="rs-compare-cell">
                    {repo.missing && repo.missing.length > 0 ? (
                      <div className="rs-reasons-tags">
                        {repo.missing.map((item, idx) => (
                          <span key={idx} className="rs-reason-tag rs-missing-tag">
                            ✗ {item}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="rs-cell-muted" style={{ color: '#3fb950' }}>
                        All target requirements matched
                      </span>
                    )}
                  </td>
                ))}
              </tr>

              {/* Row: Key Topics */}
              <tr>
                <td className="rs-compare-row-label">Topics / Tags</td>
                {repositories.map((repo) => (
                  <td key={`${repo.owner}-${repo.name}`} className="rs-compare-cell">
                    {repo.topics && repo.topics.length > 0 ? (
                      <div className="rs-topics-row">
                        {repo.topics.slice(0, 4).map((t, i) => (
                          <span key={i} className="rs-topic-tag">
                            #{t}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="rs-cell-muted">No topics</span>
                    )}
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

