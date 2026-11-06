/**
 * API Service for RepoScout Extension.
 * Encapsulates all backend REST communication.
 * The UI components never make direct fetch calls.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export class ApiError extends Error {
  constructor(message, status = null, isNetworkError = false) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.isNetworkError = isNetworkError;
  }
}

/**
 * Checks backend health status.
 * Fulfills GET /api/health contract: {"status": "ok", "service": "reposcout"}
 */
export async function checkBackendHealth() {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 3500);

    const response = await fetch(`${API_BASE_URL}/api/health`, {
      method: 'GET',
      headers: { 'Accept': 'application/json' },
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      throw new ApiError(
        `Backend health check failed with status ${response.status}`,
        response.status
      );
    }

    const data = await response.json();
    return data;
  } catch (err) {
    if (err.name === 'AbortError') {
      throw new ApiError('Backend connection timed out (port 8000)', null, true);
    }
    if (err instanceof ApiError) throw err;
    throw new ApiError(
      'Unable to connect to RepoScout backend at http://localhost:8000',
      null,
      true
    );
  }
}

/**
 * Queries natural language understanding endpoint.
 * Fulfills POST /api/query/understand
 *
 * @param {string} query - Natural language requirement
 * @returns {Promise<Object>} Structured requirements object
 */
export async function understandQuery(query) {
  const trimmed = (query || '').trim();
  if (!trimmed) {
    throw new ApiError('Please enter a requirement to understand.', 400);
  }

  try {
    const response = await fetch(`${API_BASE_URL}/api/query/understand`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify({ query: trimmed }),
    });

    if (!response.ok) {
      let errorMessage = `Query understanding failed (${response.status})`;
      try {
        const errorJson = await response.json();
        if (errorJson && errorJson.detail) {
          errorMessage = typeof errorJson.detail === 'string'
            ? errorJson.detail
            : JSON.stringify(errorJson.detail);
        }
      } catch (_) {}
      throw new ApiError(errorMessage, response.status);
    }

    return await response.json();
  } catch (err) {
    if (err instanceof ApiError) throw err;
    throw new ApiError('Failed to connect to query understanding service.', null, true);
  }
}

/**
 * Searches repositories through the backend.
 * Fulfills GET /api/search?q=<query>
 *
 * @param {string} query - The search query
 * @returns {Promise<{query: string, total_count: number, results: Array}>}
 */
export async function searchRepositories(query) {
  const trimmed = (query || '').trim();

  if (!trimmed) {
    throw new ApiError('Please enter a search query or natural language requirement.', 400);
  }

  try {
    const url = new URL(`${API_BASE_URL}/api/search`);
    url.searchParams.set('q', trimmed);

    const response = await fetch(url.toString(), {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
    });

    if (!response.ok) {
      let errorMessage = `Search failed with status ${response.status}`;
      try {
        const errorJson = await response.json();
        if (errorJson && errorJson.detail) {
          errorMessage = typeof errorJson.detail === 'string'
            ? errorJson.detail
            : JSON.stringify(errorJson.detail);
        }
      } catch (_) {
        // Fallback to HTTP status text
      }
      throw new ApiError(errorMessage, response.status);
    }

    const data = await response.json();
    return data;
  } catch (err) {
    if (err instanceof ApiError) {
      throw err;
    }
    // Network or connection refused
    throw new ApiError(
      'RepoScout backend is unavailable. Ensure FastAPI is running on http://localhost:8000',
      null,
      true
    );
  }
}

/**
 * Executes full pipeline intelligent ranked search:
 * Natural language query -> Query understanding -> GitHub search -> Repository analysis -> Multi-factor ranking.
 * Fulfills POST /api/search/ranked
 *
 * @param {string} query - Natural language search query
 * @returns {Promise<{query: string, total_count: number, results: Array, structured: Object}>}
 */
export async function searchRankedRepositories(query) {
  const trimmed = (query || '').trim();

  if (!trimmed) {
    throw new ApiError('Please enter a search query or natural language requirement.', 400);
  }

  try {
    const response = await fetch(`${API_BASE_URL}/api/search/ranked`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify({ query: trimmed }),
    });

    if (!response.ok) {
      let errorMessage = `Search failed with status ${response.status}`;
      try {
        const errorJson = await response.json();
        if (errorJson && errorJson.detail) {
          errorMessage = typeof errorJson.detail === 'string'
            ? errorJson.detail
            : JSON.stringify(errorJson.detail);
        }
      } catch (_) {}
      throw new ApiError(errorMessage, response.status);
    }

    const data = await response.json();
    return data;
  } catch (err) {
    if (err instanceof ApiError) {
      throw err;
    }
    throw new ApiError(
      'RepoScout backend is unavailable. Ensure FastAPI is running on http://localhost:8000',
      null,
      true
    );
  }
}

/**
 * Analyzes repository architecture, tech stack, and documentation quality.
 * Fulfills GET /api/repository/analyze?owner=<owner>&repo=<repo>&refresh=<bool>
 *
 * @param {string} owner - Repository owner
 * @param {string} repo - Repository name
 * @param {boolean} refresh - Force bypass cache for fresh analysis
 * @returns {Promise<Object>} Repository analysis response
 */
export async function analyzeRepository(owner, repo, refresh = false) {
  const cleanOwner = (owner || '').trim();
  const cleanRepo = (repo || '').trim();

  if (!cleanRepo) {
    throw new ApiError('Repository name is required for analysis.', 400);
  }

  try {
    const url = new URL(`${API_BASE_URL}/api/repository/analyze`);
    if (cleanOwner) {
      url.searchParams.set('owner', cleanOwner);
      url.searchParams.set('repo', cleanRepo);
    } else {
      url.searchParams.set('repo', cleanRepo);
    }
    if (refresh) {
      url.searchParams.set('refresh', 'true');
    }

    const response = await fetch(url.toString(), {
      method: 'GET',
      headers: { 'Accept': 'application/json' },
    });

    if (!response.ok) {
      let errorMessage = `Analysis failed (${response.status})`;
      try {
        const errorJson = await response.json();
        if (errorJson && errorJson.detail) {
          errorMessage = typeof errorJson.detail === 'string'
            ? errorJson.detail
            : JSON.stringify(errorJson.detail);
        }
      } catch (_) {}
      throw new ApiError(errorMessage, response.status);
    }

    return await response.json();
  } catch (err) {
    if (err instanceof ApiError) throw err;
    throw new ApiError(
      'Unable to connect to repository analysis service. Check backend connection.',
      null,
      true
    );
  }
}
