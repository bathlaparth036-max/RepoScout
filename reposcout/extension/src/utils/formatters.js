/**
 * Formatting and utility helpers for RepoScout UI.
 */

/**
 * Format count into human-readable shorthand (e.g., 4820 -> 4.8k).
 */
export function formatStars(count) {
  if (count == null || isNaN(count)) return '0';
  if (count >= 1_000_000) {
    return (count / 1_000_000).toFixed(1).replace(/\.0$/, '') + 'M';
  }
  if (count >= 1_000) {
    return (count / 1_000).toFixed(1).replace(/\.0$/, '') + 'k';
  }
  return count.toString();
}

export function formatForks(count) {
  return formatStars(count);
}

/**
 * Formats ISO 8601 date string into human-friendly relative time (e.g. "Updated 3 days ago").
 */
export function formatRelativeTime(dateString) {
  if (!dateString) return null;
  try {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffSecs = Math.floor(diffMs / 1000);
    const diffMins = Math.floor(diffSecs / 60);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);
    const diffMonths = Math.floor(diffDays / 30);
    const diffYears = Math.floor(diffDays / 365);

    if (diffDays < 1) {
      if (diffHours < 1) {
        return diffMins <= 1 ? 'Updated just now' : `Updated ${diffMins}m ago`;
      }
      return `Updated ${diffHours}h ago`;
    }
    if (diffDays < 30) {
      return `Updated ${diffDays}d ago`;
    }
    if (diffMonths < 12) {
      return `Updated ${diffMonths}mo ago`;
    }
    return `Updated ${diffYears}y ago`;
  } catch (_) {
    return null;
  }
}

/**
 * Common language dot colors conforming to developer-tool palette.
 */
const LANGUAGE_COLORS = {
  Python: '#3572A5',
  TypeScript: '#3178c6',
  JavaScript: '#f1e05a',
  'C++': '#f34b7d',
  C: '#555555',
  Rust: '#dea584',
  Go: '#00ADD8',
  Java: '#b07219',
  Ruby: '#701516',
  PHP: '#4F5D95',
  HTML: '#e34c26',
  CSS: '#563d7c',
  Shell: '#89e051',
  Dockerfile: '#384d54',
  Swift: '#F05138',
  Kotlin: '#A97BFF',
  Jupyter: '#DA5B0B',
  'Jupyter Notebook': '#DA5B0B',
};

export function getLanguageColor(language) {
  return LANGUAGE_COLORS[language] || '#8b949e';
}

/**
 * Match percentage color class and formatting.
 */
export function formatMatchPercentage(score) {
  if (score == null) return null;
  const cleanScore = Math.max(0, Math.min(100, Math.round(score)));
  return `${cleanScore}% match`;
}
