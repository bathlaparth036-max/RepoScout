import React from 'react';
import { Terminal, RefreshCw, Bookmark, Search } from 'lucide-react';

export function Header({
  backendStatus,
  onRefreshStatus,
  onHome,
  activeTab = 'search',
  onSelectTab,
  savedCount = 0,
}) {
  return (
    <header className="rs-header">
      <div className="rs-brand" onClick={onHome} title="Return to RepoScout Home">
        <div className="rs-logo-box">
          <Terminal size={16} strokeWidth={2.2} />
        </div>
        <div className="rs-title-wrap">
          <span className="rs-title">RepoScout</span>
          <span className="rs-badge-version">v0.1.0</span>
        </div>
      </div>

      {onSelectTab && (
        <nav className="rs-header-nav">
          <button
            type="button"
            className={`rs-nav-tab ${activeTab === 'search' ? 'active' : ''}`}
            onClick={() => onSelectTab('search')}
            title="Search & discover repositories"
          >
            <Search size={12} />
            <span>Search</span>
          </button>

          <button
            type="button"
            className={`rs-nav-tab ${activeTab === 'saved' ? 'active' : ''}`}
            onClick={() => onSelectTab('saved')}
            title="View bookmarked repositories"
          >
            <Bookmark
              size={12}
              fill={savedCount > 0 ? '#e3b341' : 'none'}
              color={savedCount > 0 ? '#e3b341' : 'currentColor'}
            />
            <span>Saved</span>
            {savedCount > 0 && <span className="rs-nav-counter">{savedCount}</span>}
          </button>
        </nav>
      )}

      <div className="rs-header-meta">
        <div
          className="rs-status-pill"
          title={
            backendStatus === 'connected'
              ? 'FastAPI backend active on port 8000'
              : backendStatus === 'offline'
              ? 'FastAPI backend unreachable'
              : 'Checking backend...'
          }
        >
          <span className={`rs-status-dot ${backendStatus}`} />
          <span>
            {backendStatus === 'connected' && 'API Connected'}
            {backendStatus === 'offline' && 'Backend Offline'}
            {backendStatus === 'checking' && 'Checking...'}
          </span>
          {backendStatus === 'offline' && (
            <button
              onClick={onRefreshStatus}
              className="rs-reconnect-btn"
              title="Retry connection"
              type="button"
            >
              <RefreshCw size={11} />
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
