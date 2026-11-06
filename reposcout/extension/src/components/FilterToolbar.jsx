import React from 'react';
import { Filter, ArrowUpDown, X, SlidersHorizontal } from 'lucide-react';

/**
 * Filter and sorting toolbar for search results:
 * - Dynamic language selector based on current result set
 * - Minimum match score threshold
 * - Sorting criteria (Relevance, Stars, Updated, Forks)
 * - Clear filters button
 */
export function FilterToolbar({
  languages = [],
  selectedLanguage,
  onLanguageChange,
  minScore,
  onMinScoreChange,
  sortBy,
  onSortChange,
  totalResultsCount,
  filteredCount,
  onResetFilters,
}) {
  const isFiltered = selectedLanguage !== 'all' || minScore > 0 || sortBy !== 'relevance';

  return (
    <div className="rs-filter-toolbar">
      <div className="rs-filter-controls">
        {/* Language Filter */}
        <div className="rs-filter-item">
          <label htmlFor="rs-filter-lang" className="rs-filter-label">
            Language:
          </label>
          <select
            id="rs-filter-lang"
            className="rs-filter-select"
            value={selectedLanguage}
            onChange={(e) => onLanguageChange(e.target.value)}
          >
            <option value="all">All Languages</option>
            {languages.map((lang) => (
              <option key={lang} value={lang}>
                {lang}
              </option>
            ))}
          </select>
        </div>

        {/* Min Score Threshold */}
        <div className="rs-filter-item">
          <label htmlFor="rs-filter-score" className="rs-filter-label">
            Min Match:
          </label>
          <select
            id="rs-filter-score"
            className="rs-filter-select"
            value={minScore}
            onChange={(e) => onMinScoreChange(Number(e.target.value))}
          >
            <option value={0}>Any Score</option>
            <option value={60}>60%+ Match</option>
            <option value={70}>70%+ Match</option>
            <option value={80}>80%+ Match</option>
            <option value={90}>90%+ Match</option>
          </select>
        </div>

        {/* Sort Criteria */}
        <div className="rs-filter-item">
          <label htmlFor="rs-filter-sort" className="rs-filter-label">
            <ArrowUpDown size={11} style={{ marginRight: 3, verticalAlign: 'middle' }} />
            Sort:
          </label>
          <select
            id="rs-filter-sort"
            className="rs-filter-select"
            value={sortBy}
            onChange={(e) => onSortChange(e.target.value)}
          >
            <option value="relevance">Relevance</option>
            <option value="stars">Most Stars</option>
            <option value="updated">Recently Updated</option>
            <option value="forks">Most Forks</option>
          </select>
        </div>

        {/* Reset Active Filters Button */}
        {isFiltered && (
          <button
            type="button"
            className="rs-filter-reset-btn"
            onClick={onResetFilters}
            title="Reset all filters to default"
          >
            <X size={11} />
            <span>Reset</span>
          </button>
        )}
      </div>

      {/* Filtered Count Indicator */}
      {isFiltered && (
        <div className="rs-filter-summary">
          Showing <strong>{filteredCount}</strong> of <strong>{totalResultsCount}</strong> results
        </div>
      )}
    </div>
  );
}

