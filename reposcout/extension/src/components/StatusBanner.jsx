import React from 'react';
import { AlertCircle, AlertTriangle, RefreshCw, KeyRound, Clock } from 'lucide-react';

export function StatusBanner({ error, onRetry }) {
  if (!error) return null;

  const isNetwork = error.isNetworkError;
  const isRateLimit = error.status === 429 || (error.status === 403 && (error.message || '').toLowerCase().includes('rate limit'));
  const isAuthError = error.status === 401;
  const isForbidden = error.status === 403 && !isRateLimit;

  let title = 'Search Notice';
  let bannerClass = 'warning';
  let Icon = AlertTriangle;

  if (isRateLimit) {
    title = 'GitHub API Rate Limit Reached';
    bannerClass = 'warning';
    Icon = Clock;
  } else if (isAuthError) {
    title = 'GitHub Authentication Error';
    bannerClass = 'error';
    Icon = KeyRound;
  } else if (isForbidden) {
    title = 'GitHub Access Restricted (403)';
    bannerClass = 'warning';
    Icon = KeyRound;
  } else if (isNetwork) {
    title = 'Backend Communication Error';
    bannerClass = 'error';
    Icon = AlertCircle;
  } else if (error.status && error.status >= 500) {
    title = 'Server Error';
    bannerClass = 'error';
    Icon = AlertCircle;
  }

  return (
    <div className={`rs-banner ${bannerClass}`}>
      <Icon size={16} className="rs-banner-icon" style={{ flexShrink: 0, marginTop: '2px' }} />

      <div className="rs-banner-content">
        <div className="rs-banner-title">{title}</div>
        <div className="rs-banner-detail">{error.message}</div>

        {isNetwork && (
          <div style={{ marginTop: '6px' }}>
            <button
              type="button"
              onClick={onRetry}
              className="rs-search-btn"
              style={{ padding: '3px 8px', fontSize: '11px', display: 'inline-flex' }}
            >
              <RefreshCw size={11} />
              <span>Retry Connection</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
