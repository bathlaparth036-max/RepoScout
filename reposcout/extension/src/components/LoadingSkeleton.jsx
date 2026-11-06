import React from 'react';

export function LoadingSkeleton({ count = 3, status }) {
  return (
    <div className="rs-list">
      {status && (
        <div className="rs-status-stage">
          <span className="rs-spinner" />
          <span>{status}</span>
        </div>
      )}

      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="rs-skeleton-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div className="rs-skeleton-line" style={{ width: '45%', height: '16px' }} />
            <div className="rs-skeleton-line" style={{ width: '80px', height: '18px' }} />
          </div>
          <div className="rs-skeleton-line" style={{ width: '90%', height: '12px' }} />
          <div className="rs-skeleton-line" style={{ width: '65%', height: '12px' }} />
          <div style={{ display: 'flex', gap: '12px', marginTop: '4px' }}>
            <div className="rs-skeleton-line" style={{ width: '60px', height: '12px' }} />
            <div className="rs-skeleton-line" style={{ width: '50px', height: '12px' }} />
            <div className="rs-skeleton-line" style={{ width: '40px', height: '12px' }} />
          </div>
        </div>
      ))}
    </div>
  );
}
