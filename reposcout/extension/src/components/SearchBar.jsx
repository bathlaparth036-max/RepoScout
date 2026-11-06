import React from 'react';
import { Search, X, CornerDownLeft } from 'lucide-react';

export function SearchBar({
  query,
  onChange,
  onSearch,
  onClear,
  loading,
  placeholder = 'Type natural requirement, e.g. "beginner-friendly RAG with LangChain and FAISS"...',
}) {
  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      onSearch();
    }
  };

  return (
    <div className="rs-search-container">
      <div className="rs-search-input-wrap">
        <span className="rs-search-icon">
          <Search size={15} />
        </span>

        <input
          type="text"
          className="rs-search-input"
          placeholder={placeholder}
          value={query}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          autoFocus
          disabled={loading}
        />

        <div className="rs-search-actions">
          {query && (
            <button
              type="button"
              className="rs-clear-btn"
              onClick={onClear}
              title="Clear search"
            >
              <X size={14} />
            </button>
          )}

          <button
            type="button"
            className="rs-search-btn"
            onClick={() => onSearch()}
            disabled={loading || !query.trim()}
          >
            {loading ? (
              'Searching...'
            ) : (
              <>
                <span>Search</span>
                <CornerDownLeft size={11} />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

