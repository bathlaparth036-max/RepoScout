import { useState, useEffect, useCallback } from 'react';
import { searchRankedRepositories, checkBackendHealth } from '../services/api';

/**
 * Custom hook managing repository search state, pipeline status progression,
 * backend health, and error handling.
 */
export function useRepoSearch() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [searchStatus, setSearchStatus] = useState(''); // 'Understanding your requirements...' -> 'Searching GitHub...'
  const [error, setError] = useState(null);
  const [hasSearched, setHasSearched] = useState(false);
  const [backendStatus, setBackendStatus] = useState('checking'); // 'checking' | 'connected' | 'offline'

  // Probe backend health
  const probeHealth = useCallback(async () => {
    try {
      setBackendStatus('checking');
      const health = await checkBackendHealth();
      if (health && health.status === 'ok') {
        setBackendStatus('connected');
        return true;
      }
      setBackendStatus('offline');
      return false;
    } catch (_) {
      setBackendStatus('offline');
      return false;
    }
  }, []);

  // Check health on initial mount
  useEffect(() => {
    probeHealth();
  }, [probeHealth]);

  // Execute search with multi-stage status progression
  const performSearch = useCallback(async (searchQuery) => {
    const targetQuery = (searchQuery !== undefined ? searchQuery : query).trim();

    if (!targetQuery) {
      setError({
        message: 'Search query cannot be empty. Enter keywords or a requirement like "beginner RAG project using Python and LangChain".',
        isNetworkError: false,
      });
      return;
    }

    setLoading(true);
    setSearchStatus('Searching GitHub...');
    setError(null);
    setHasSearched(true);
    if (searchQuery !== undefined) {
      setQuery(searchQuery);
    }

    // Progressive status progression:
    // Searching GitHub... -> Finding matching repositories... -> Analyzing top repositories... -> Calculating relevance...
    const timers = [];
    timers.push(setTimeout(() => setSearchStatus('Finding matching repositories...'), 400));
    timers.push(setTimeout(() => setSearchStatus('Analyzing top repositories...'), 850));
    timers.push(setTimeout(() => setSearchStatus('Calculating relevance...'), 1350));

    try {
      const response = await searchRankedRepositories(targetQuery);
      timers.forEach(clearTimeout);
      setSearchStatus('Results ready.');
      setResults(response.results || []);
      setTotalCount(response.total_count || (response.results ? response.results.length : 0));
      setBackendStatus('connected');
      // Brief pause to display "Results ready." feedback before hiding skeleton
      await new Promise((resolve) => setTimeout(resolve, 200));
    } catch (err) {
      timers.forEach(clearTimeout);
      setError({
        message: err.message || 'An unexpected error occurred.',
        isNetworkError: Boolean(err.isNetworkError),
        status: err.status,
      });
      if (err.isNetworkError) {
        setBackendStatus('offline');
      }
      setResults([]);
      setTotalCount(0);
    } finally {
      timers.forEach(clearTimeout);
      setLoading(false);
      setSearchStatus('');
    }
  }, [query]);

  const clearResults = useCallback(() => {
    setQuery('');
    setResults([]);
    setTotalCount(0);
    setError(null);
    setHasSearched(false);
    setSearchStatus('');
  }, []);

  return {
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
  };
}
