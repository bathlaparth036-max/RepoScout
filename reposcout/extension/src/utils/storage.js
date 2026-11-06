/**
 * Chrome Storage & Local Storage abstraction for RepoScout Extension.
 * Seamlessly interfaces with `chrome.storage.local` inside the Chrome extension popup,
 * and falls back gracefully to `window.localStorage` during web browser development.
 */

const STORAGE_KEY = 'reposcout_saved_repositories';

/**
 * Checks if the Chrome extension storage API is available in the current runtime context.
 */
function isChromeStorageAvailable() {
  return typeof chrome !== 'undefined' && Boolean(chrome?.storage?.local);
}

/**
 * Retrieves all saved repositories.
 * @returns {Promise<Array<Object>>}
 */
export async function getSavedRepositories() {
  if (isChromeStorageAvailable()) {
    return new Promise((resolve) => {
      try {
        chrome.storage.local.get([STORAGE_KEY], (result) => {
          if (chrome.runtime.lastError) {
            resolve(fallbackGetLocalStorage());
          } else {
            resolve(result[STORAGE_KEY] || []);
          }
        });
      } catch (_) {
        resolve(fallbackGetLocalStorage());
      }
    });
  }

  return fallbackGetLocalStorage();
}

/**
 * Saves a repository bookmark.
 * @param {Object} repository
 * @returns {Promise<Array<Object>>} Updated list of saved repositories
 */
export async function saveRepository(repository) {
  if (!repository || !repository.owner || !repository.name) return [];

  const current = await getSavedRepositories();
  const repoId = `${repository.owner}/${repository.name}`;

  // Check if already saved
  const exists = current.some((r) => `${r.owner}/${r.name}` === repoId);
  let updated;

  if (exists) {
    // Update existing record
    updated = current.map((r) => (`${r.owner}/${r.name}` === repoId ? { ...r, ...repository } : r));
  } else {
    // Append new bookmark with saved timestamp
    updated = [{ ...repository, saved_at: new Date().toISOString() }, ...current];
  }

  await writeSavedRepositories(updated);
  return updated;
}

/**
 * Removes a repository bookmark by identifier 'owner/name'.
 * @param {string} repoId - 'owner/name'
 * @returns {Promise<Array<Object>>} Updated list
 */
export async function removeSavedRepository(repoId) {
  const current = await getSavedRepositories();
  const updated = current.filter((r) => `${r.owner}/${r.name}` !== repoId);
  await writeSavedRepositories(updated);
  return updated;
}

/**
 * Clears all saved repositories.
 */
export async function clearAllSavedRepositories() {
  await writeSavedRepositories([]);
  return [];
}

/**
 * Writes array of repositories to storage.
 */
async function writeSavedRepositories(repositories) {
  if (isChromeStorageAvailable()) {
    return new Promise((resolve) => {
      try {
        chrome.storage.local.set({ [STORAGE_KEY]: repositories }, () => {
          fallbackSetLocalStorage(repositories);
          resolve();
        });
      } catch (_) {
        fallbackSetLocalStorage(repositories);
        resolve();
      }
    });
  }

  fallbackSetLocalStorage(repositories);
}

function fallbackGetLocalStorage() {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch (_) {
    return [];
  }
}

function fallbackSetLocalStorage(repositories) {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(repositories));
  } catch (_) {}
}

/**
 * Formats saved repositories into clean GitHub Flavored Markdown.
 * Suitable for copying to clipboard or saving as a project research document.
 * @param {Array<Object>} repositories
 * @returns {string} Markdown document
 */
export function generateMarkdownExport(repositories) {
  if (!repositories || repositories.length === 0) {
    return '# RepoScout — Saved Repositories\n\nNo repositories bookmarked yet.\n';
  }

  const date = new Date().toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });

  let md = `# RepoScout — Discovered Repositories\n\n`;
  md += `Exported on **${date}** (${repositories.length} ${repositories.length === 1 ? 'project' : 'projects'})\n\n`;
  md += `| Repository | Match | Language | Stars | Description |\n`;
  md += `| :--- | :---: | :---: | :---: | :--- |\n`;

  for (const repo of repositories) {
    const repoTitle = `${repo.owner}/${repo.name}`;
    const url = repo.html_url || repo.url || `https://github.com/${repoTitle}`;
    const match = repo.match_score != null ? `${repo.match_score}%` : 'N/A';
    const lang = repo.language || 'Unknown';
    const stars = (repo.stars || 0).toLocaleString();
    const cleanDesc = (repo.description || 'No description').replace(/\|/g, '\\|').replace(/\n/g, ' ');

    md += `| [**${repoTitle}**](${url}) | \`${match}\` | ${lang} | ⭐ ${stars} | ${cleanDesc} |\n`;
  }

  md += `\n---\n*Curated with [RepoScout](https://github.com)*\n`;
  return md;
}

