import React, { useState, useCallback } from 'react';
import { Header } from './components/Header';
import { SearchPage } from './pages/SearchPage';
import { SavedPage } from './pages/SavedPage';
import { AnalysisPanel } from './components/AnalysisPanel';
import { CompareModal } from './components/CompareModal';
import { useRepoSearch } from './hooks/useRepoSearch';
import { useBookmarks } from './hooks/useBookmarks';
import { Layers, X } from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState('search'); // 'search' | 'saved'
  const [selectedRepoForAnalysis, setSelectedRepoForAnalysis] = useState(null);
  const [selectedForCompare, setSelectedForCompare] = useState([]);
  const [isCompareModalOpen, setIsCompareModalOpen] = useState(false);

  // Search pipeline hook
  const {
    query,
    setQuery,
    results,
    totalCount,
    loading,
    searchStatus,
    error,
    hasSearched,
    backendStatus,
    performSearch,
    probeHealth,
    clearResults,
  } = useRepoSearch();

  // Storage / bookmarks hook
  const {
    savedRepos,
    isSaved,
    toggleBookmark,
    clearBookmarks,
    exportToMarkdown,
    savedCount,
  } = useBookmarks();

  const handleReturnToSearch = () => {
    setSelectedRepoForAnalysis(null);
    setActiveTab('search');
  };

  const handleSelectTab = (tab) => {
    setSelectedRepoForAnalysis(null);
    setActiveTab(tab);
  };

  // Compare handlers
  const handleToggleCompare = useCallback((repository) => {
    if (!repository || !repository.owner || !repository.name) return;
    const repoId = `${repository.owner}/${repository.name}`;

    setSelectedForCompare((prev) => {
      const exists = prev.some((r) => `${r.owner}/${r.name}` === repoId);
      if (exists) {
        return prev.filter((r) => `${r.owner}/${r.name}` !== repoId);
      }
      if (prev.length >= 3) {
        // Limit to 3 repositories side-by-side
        return [...prev.slice(1), repository];
      }
      return [...prev, repository];
    });
  }, []);

  const isSelectedForCompare = useCallback(
    (repo) => {
      if (!repo || !repo.owner || !repo.name) return false;
      return selectedForCompare.some((r) => r.owner === repo.owner && r.name === repo.name);
    },
    [selectedForCompare]
  );

  const handleRemoveCompareRepo = useCallback((repo) => {
    setSelectedForCompare((prev) =>
      prev.filter((r) => !(r.owner === repo.owner && r.name === repo.name))
    );
  }, []);

  const handleClearCompare = useCallback(() => {
    setSelectedForCompare([]);
  }, []);

  return (
    <>
      <Header
        backendStatus={backendStatus}
        onRefreshStatus={probeHealth}
        onHome={handleReturnToSearch}
        activeTab={activeTab}
        onSelectTab={handleSelectTab}
        savedCount={savedCount}
      />

      {/* Main View Router */}
      {selectedRepoForAnalysis ? (
        <AnalysisPanel
          repository={selectedRepoForAnalysis}
          onBack={handleReturnToSearch}
          isSaved={isSaved(selectedRepoForAnalysis.owner, selectedRepoForAnalysis.name)}
          onToggleSave={toggleBookmark}
        />
      ) : activeTab === 'saved' ? (
        <SavedPage
          savedRepos={savedRepos}
          onAnalyze={setSelectedRepoForAnalysis}
          onToggleSave={toggleBookmark}
          onClearAll={clearBookmarks}
          onExportMarkdown={exportToMarkdown}
          onBackToSearch={() => setActiveTab('search')}
          isSelectedForCompare={isSelectedForCompare}
          onToggleCompare={handleToggleCompare}
        />
      ) : (
        <SearchPage
          query={query}
          setQuery={setQuery}
          results={results}
          totalCount={totalCount}
          loading={loading}
          searchStatus={searchStatus}
          error={error}
          hasSearched={hasSearched}
          onSearch={performSearch}
          onClear={clearResults}
          onRetry={probeHealth}
          onAnalyze={setSelectedRepoForAnalysis}
          isSaved={isSaved}
          onToggleSave={toggleBookmark}
          isSelectedForCompare={isSelectedForCompare}
          onToggleCompare={handleToggleCompare}
        />
      )}

      {/* Floating Compare Toolbar Bar */}
      {selectedForCompare.length > 0 && !selectedRepoForAnalysis && (
        <div className="rs-floating-compare-dock">
          <div className="rs-compare-dock-info">
            <Layers size={13} color="#3fb950" />
            <span>
              <strong>{selectedForCompare.length}</strong> of <strong>3</strong> projects selected
            </span>
          </div>

          <div className="rs-compare-dock-actions">
            <button
              type="button"
              className="rs-view-btn rs-compare-launch-btn"
              onClick={() => setIsCompareModalOpen(true)}
              title="Open side-by-side repository comparison"
            >
              <span>Compare Now</span>
            </button>

            <button
              type="button"
              className="rs-icon-btn rs-compare-clear-btn"
              onClick={handleClearCompare}
              title="Clear comparison selection"
            >
              <X size={12} />
            </button>
          </div>
        </div>
      )}

      {/* Side-by-Side Comparison Modal */}
      {isCompareModalOpen && (
        <CompareModal
          repositories={selectedForCompare}
          onClose={() => setIsCompareModalOpen(false)}
          onRemoveRepo={handleRemoveCompareRepo}
          onAnalyze={setSelectedRepoForAnalysis}
        />
      )}

      <footer className="rs-footer">
        <span>RepoScout Discovery & Analysis</span>
        <span>
          {selectedRepoForAnalysis ? (
            <span>Inspecting repository architecture</span>
          ) : activeTab === 'saved' ? (
            <span>{savedCount} {savedCount === 1 ? 'repository' : 'repositories'} bookmarked</span>
          ) : (
            <span>
              Press <kbd className="rs-kbd">Enter</kbd> to search
            </span>
          )}
        </span>
      </footer>
    </>
  );
}
