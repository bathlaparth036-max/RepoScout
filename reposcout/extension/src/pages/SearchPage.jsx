import React, { useState, useMemo } from 'react';
import { SearchBar } from '../components/SearchBar';
import { SuggestionPills } from '../components/SuggestionPills';
import { StatusBanner } from '../components/StatusBanner';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { RepositoryList } from '../components/RepositoryList';
import { FilterToolbar } from '../components/FilterToolbar';

export function SearchPage({
  query,
  setQuery,
  results = [],
  totalCount,
  loading,
  searchStatus,
  error,
  hasSearched,
  onSearch,
  onClear,
  onRetry,
  onAnalyze,
  isSaved,
  onToggleSave,
  isSelectedForCompare,
  onToggleCompare,
}) {
  const [selectedLanguage, setSelectedLanguage] = useState('all');
  const [minScore, setMinScore] = useState(0);
  const [sortBy, setSortBy] = useState('relevance');

  // Collect unique languages available in the current result set
  const availableLanguages = useMemo(() => {
    const langs = new Set();
    results.forEach((r) => {
      if (r.language) langs.add(r.language);
    });
    return Array.from(langs).sort();
  }, [results]);

  // Apply filters and sorting
  const filteredAndSortedResults = useMemo(() => {
    let list = [...results];

    // Filter by language
    if (selectedLanguage !== 'all') {
      list = list.filter((r) => r.language === selectedLanguage);
    }

    // Filter by minimum score
    if (minScore > 0) {
      list = list.filter((r) => {
        const score = r.match_score ?? r.match_percentage ?? 0;
        return score >= minScore;
      });
    }

    // Sort
    if (sortBy === 'stars') {
      list.sort((a, b) => (b.stars || 0) - (a.stars || 0));
    } else if (sortBy === 'updated') {
      list.sort((a, b) => new Date(b.updated_at || 0) - new Date(a.updated_at || 0));
    } else if (sortBy === 'forks') {
      list.sort((a, b) => (b.forks || 0) - (a.forks || 0));
    } else {
      // 'relevance' (default: rank order preserved or match score descending)
      list.sort((a, b) => (b.match_score ?? b.match_percentage ?? 0) - (a.match_score ?? a.match_percentage ?? 0));
    }

    return list;
  }, [results, selectedLanguage, minScore, sortBy]);

  const handleResetFilters = () => {
    setSelectedLanguage('all');
    setMinScore(0);
    setSortBy('relevance');
  };

  const handleSelectSuggestion = (suggestionText) => {
    setQuery(suggestionText);
    handleResetFilters();
    onSearch(suggestionText);
  };

  const handleClearAll = () => {
    handleResetFilters();
    onClear();
  };

  return (
    <main className="rs-container">
      {/* Search Input Section */}
      <SearchBar
        query={query}
        onChange={setQuery}
        onSearch={(q) => {
          handleResetFilters();
          onSearch(q);
        }}
        onClear={handleClearAll}
        loading={loading}
      />

      {/* Suggestion Chips */}
      <SuggestionPills
        onSelectSuggestion={handleSelectSuggestion}
        disabled={loading}
      />

      {/* Network or Validation Banner */}
      <StatusBanner error={error} onRetry={onRetry} />

      {/* Interactive Filter & Sorting Toolbar */}
      {!loading && hasSearched && results.length > 0 && (
        <FilterToolbar
          languages={availableLanguages}
          selectedLanguage={selectedLanguage}
          onLanguageChange={setSelectedLanguage}
          minScore={minScore}
          onMinScoreChange={setMinScore}
          sortBy={sortBy}
          onSortChange={setSortBy}
          totalResultsCount={results.length}
          filteredCount={filteredAndSortedResults.length}
          onResetFilters={handleResetFilters}
        />
      )}

      {/* Results View or Loading Skeleton with Status Progression */}
      {loading ? (
        <LoadingSkeleton count={3} status={searchStatus} />
      ) : (
        <RepositoryList
          results={filteredAndSortedResults}
          totalCount={filteredAndSortedResults.length}
          query={query}
          hasSearched={hasSearched}
          onAnalyze={onAnalyze}
          isSaved={isSaved}
          onToggleSave={onToggleSave}
          isSelectedForCompare={isSelectedForCompare}
          onToggleCompare={onToggleCompare}
        />
      )}
    </main>
  );
}
