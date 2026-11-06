import React, { useState, useMemo } from 'react';
import {
  Bookmark,
  Download,
  Copy,
  Check,
  Trash2,
  Search,
  ArrowLeft,
  FileText,
} from 'lucide-react';
import { RepositoryCard } from '../components/RepositoryCard';

export function SavedPage({
  savedRepos = [],
  onAnalyze,
  onToggleSave,
  onClearAll,
  onExportMarkdown,
  onBackToSearch,
  isSelectedForCompare,
  onToggleCompare,
}) {
  const [filterQuery, setFilterQuery] = useState('');
  const [copiedExport, setCopiedExport] = useState(false);
  const [confirmClear, setConfirmClear] = useState(false);

  // Filter saved repos by owner/name/description/language
  const filteredRepos = useMemo(() => {
    const q = filterQuery.trim().toLowerCase();
    if (!q) return savedRepos;
    return savedRepos.filter((repo) => {
      const name = (repo.name || '').toLowerCase();
      const owner = (repo.owner || '').toLowerCase();
      const desc = (repo.description || '').toLowerCase();
      const lang = (repo.language || '').toLowerCase();
      return (
        name.includes(q) ||
        owner.includes(q) ||
        desc.includes(q) ||
        lang.includes(q)
      );
    });
  }, [savedRepos, filterQuery]);

  const handleCopyMarkdown = () => {
    const markdown = onExportMarkdown();
    if (navigator?.clipboard?.writeText) {
      navigator.clipboard.writeText(markdown);
      setCopiedExport(true);
      setTimeout(() => setCopiedExport(false), 2200);
    }
  };

  const handleClear = () => {
    if (!confirmClear) {
      setConfirmClear(true);
      setTimeout(() => setConfirmClear(false), 3000);
      return;
    }
    onClearAll();
    setConfirmClear(false);
  };

  return (
    <main className="rs-container">
      {/* Top Navigation & Action Header */}
      <div className="rs-saved-header">
        <div className="rs-saved-title-wrap">
          <button
            type="button"
            className="rs-back-btn"
            onClick={onBackToSearch}
            title="Return to repository search"
          >
            <ArrowLeft size={13} />
            <span>Search</span>
          </button>
          <div className="rs-saved-heading">
            <Bookmark size={15} fill="#e3b341" color="#e3b341" />
            <span>Saved Repositories</span>
            <span className="rs-saved-counter">{savedRepos.length}</span>
          </div>
        </div>

        {savedRepos.length > 0 && (
          <div className="rs-saved-actions">
            <button
              type="button"
              className="rs-view-btn rs-export-btn"
              onClick={handleCopyMarkdown}
              title="Copy all saved repositories as formatted GitHub Markdown table"
            >
              {copiedExport ? (
                <>
                  <Check size={11} color="#3fb950" />
                  <span style={{ color: '#3fb950' }}>Copied Markdown!</span>
                </>
              ) : (
                <>
                  <FileText size={11} />
                  <span>Export Markdown</span>
                </>
              )}
            </button>

            <button
              type="button"
              className={`rs-view-btn rs-clear-all-btn ${confirmClear ? 'confirming' : ''}`}
              onClick={handleClear}
              title={confirmClear ? 'Click again to permanently delete all bookmarks' : 'Clear all saved bookmarks'}
            >
              <Trash2 size={11} />
              <span>{confirmClear ? 'Confirm Clear?' : 'Clear All'}</span>
            </button>
          </div>
        )}
      </div>

      {/* In-List Filter if 2+ repositories exist */}
      {savedRepos.length > 1 && (
        <div className="rs-saved-search-box">
          <Search size={13} className="rs-saved-search-icon" />
          <input
            type="text"
            className="rs-saved-search-input"
            placeholder="Filter saved repositories by name, language, or topic..."
            value={filterQuery}
            onChange={(e) => setFilterQuery(e.target.value)}
          />
        </div>
      )}

      {/* Empty State */}
      {savedRepos.length === 0 ? (
        <div className="rs-empty-state">
          <Bookmark size={34} className="rs-empty-icon" strokeWidth={1.5} color="#8b949e" />
          <div className="rs-empty-title">No saved repositories</div>
          <div className="rs-empty-desc">
            Bookmark repositories during search or deep analysis to save them for quick reference,
            comparison, and Markdown export.
          </div>
          <button
            type="button"
            className="rs-view-btn rs-empty-cta-btn"
            onClick={onBackToSearch}
            style={{ marginTop: '12px' }}
          >
            Start Discovering Repositories
          </button>
        </div>
      ) : filteredRepos.length === 0 ? (
        <div className="rs-empty-state">
          <Search size={30} className="rs-empty-icon" strokeWidth={1.5} />
          <div className="rs-empty-title">No matching bookmarks</div>
          <div className="rs-empty-desc">
            No saved repositories matched &ldquo;{filterQuery}&rdquo;.
          </div>
        </div>
      ) : (
        <div className="rs-list" style={{ marginTop: '12px' }}>
          {filteredRepos.map((repo, idx) => (
            <RepositoryCard
              key={`${repo.owner}-${repo.name}-${idx}`}
              repository={repo}
              onAnalyze={onAnalyze}
              isSaved={true}
              onToggleSave={onToggleSave}
              isSelectedForCompare={
                typeof isSelectedForCompare === 'function' ? isSelectedForCompare(repo) : false
              }
              onToggleCompare={onToggleCompare}
            />
          ))}
        </div>
      )}
    </main>
  );
}

