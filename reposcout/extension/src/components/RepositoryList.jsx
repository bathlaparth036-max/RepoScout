import React from 'react';
import { Compass, Search } from 'lucide-react';
import { RepositoryCard } from './RepositoryCard';

export function RepositoryList({
  results,
  totalCount,
  query,
  hasSearched,
  onAnalyze,
  isSaved,
  onToggleSave,
  isSelectedForCompare,
  onToggleCompare,
}) {
  if (!hasSearched) {
    return (
      <div className="rs-empty-state">
        <Compass size={32} className="rs-empty-icon" strokeWidth={1.5} />
        <div className="rs-empty-title">Ready to discover repositories</div>
        <div className="rs-empty-desc">
          Enter natural language requirements above or select an example search to find
          ranked, curated GitHub projects.
        </div>
      </div>
    );
  }

  if (results.length === 0) {
    return (
      <div className="rs-empty-state">
        <Search size={32} className="rs-empty-icon" strokeWidth={1.5} />
        <div className="rs-empty-title">No repositories found</div>
        <div className="rs-empty-desc">
          No matching repositories discovered for &ldquo;{query}&rdquo;. Try broadening
          your search terms or adjusting the active filters.
        </div>
      </div>
    );
  }

  return (
    <section className="rs-list-section">
      <div className="rs-results-header">
        <span>
          Discovered{' '}
          <span className="rs-results-count">
            {totalCount} {totalCount === 1 ? 'repository' : 'repositories'}
          </span>
          {query ? ` for "${query}"` : ''}
        </span>
        <span style={{ fontSize: '11px' }}>Ranked by relevance</span>
      </div>

      <div className="rs-list" style={{ marginTop: '10px' }}>
        {results.map((repo, idx) => {
          const saved = typeof isSaved === 'function' ? isSaved(repo.owner, repo.name) : false;
          const compared =
            typeof isSelectedForCompare === 'function' ? isSelectedForCompare(repo) : false;

          return (
            <RepositoryCard
              key={`${repo.owner}-${repo.name}-${idx}`}
              repository={repo}
              onAnalyze={onAnalyze}
              isSaved={saved}
              onToggleSave={onToggleSave}
              isSelectedForCompare={compared}
              onToggleCompare={onToggleCompare}
            />
          );
        })}
      </div>
    </section>
  );
}
