import { useState, useEffect, useCallback } from 'react';
import {
  getSavedRepositories,
  saveRepository,
  removeSavedRepository,
  clearAllSavedRepositories,
  generateMarkdownExport,
} from '../utils/storage';

/**
 * Custom hook managing repository bookmarks in Chrome local storage with web fallback.
 */
export function useBookmarks() {
  const [savedRepos, setSavedRepos] = useState([]);
  const [loading, setLoading] = useState(true);

  // Load saved repositories on mount
  useEffect(() => {
    let mounted = true;
    getSavedRepositories().then((repos) => {
      if (mounted) {
        setSavedRepos(repos);
        setLoading(false);
      }
    });
    return () => {
      mounted = false;
    };
  }, []);

  const isSaved = useCallback(
    (owner, name) => {
      if (!owner || !name) return false;
      return savedRepos.some((r) => r.owner === owner && r.name === name);
    },
    [savedRepos]
  );

  const toggleBookmark = useCallback(
    async (repository) => {
      if (!repository || !repository.owner || !repository.name) return;
      const repoId = `${repository.owner}/${repository.name}`;
      const exists = savedRepos.some((r) => `${r.owner}/${r.name}` === repoId);

      if (exists) {
        const updated = await removeSavedRepository(repoId);
        setSavedRepos(updated);
      } else {
        const updated = await saveRepository(repository);
        setSavedRepos(updated);
      }
    },
    [savedRepos]
  );

  const removeBookmark = useCallback(async (owner, name) => {
    const repoId = `${owner}/${name}`;
    const updated = await removeSavedRepository(repoId);
    setSavedRepos(updated);
  }, []);

  const clearBookmarks = useCallback(async () => {
    const updated = await clearAllSavedRepositories();
    setSavedRepos(updated);
  }, []);

  const exportToMarkdown = useCallback(() => {
    return generateMarkdownExport(savedRepos);
  }, [savedRepos]);

  return {
    savedRepos,
    loading,
    isSaved,
    toggleBookmark,
    removeBookmark,
    clearBookmarks,
    exportToMarkdown,
    savedCount: savedRepos.length,
  };
}

