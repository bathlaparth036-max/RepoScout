import React from 'react';

const SUGGESTIONS = [
  'RAG',
  'LangChain Python',
  'React dashboard',
  'machine learning',
  'FastAPI project',
];

export function SuggestionPills({ onSelectSuggestion, disabled }) {
  return (
    <div className="rs-suggestions">
      <span className="rs-suggestions-label">Try GitHub searches:</span>
      <div className="rs-pills-row">
        {SUGGESTIONS.map((suggestion, index) => (
          <button
            key={index}
            type="button"
            className="rs-pill"
            onClick={() => onSelectSuggestion(suggestion)}
            disabled={disabled}
            title={`Search GitHub for "${suggestion}"`}
          >
            {suggestion}
          </button>
        ))}
      </div>
    </div>
  );
}
