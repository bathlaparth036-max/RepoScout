"""
Cache Service Boundary & Multi-Backend Architecture.
Provides key-value caching abstraction for GitHub API searches, repository metadata,
README analysis, architecture components, technology detection, and query rankings.

Architecture:
- BaseCacheBackend: Abstract storage interface
- InMemoryCacheBackend: Thread-safe local cache with TTL expiration (default for development/tests)
- RedisCacheBackend: Production Redis integration ready (activates when REDIS_URL is configured)
- CacheService: Domain-aware facade providing standardized cache keys and configurable TTLs

Cache Keys Contract:
- github_search:<query>
- repository:<owner>:<repo>
- analysis:<owner>:<repo>
- readme:<owner>:<repo>
- tech_detection:<owner>:<repo>
- ranking:<query_hash>
"""

import abc
import hashlib
import json
import logging
import re
import threading
import time
from typing import Any, Dict, Optional, Tuple

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class BaseCacheBackend(abc.ABC):
    """Abstract cache storage backend interface."""

    @abc.abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Retrieve cached value if present and unexpired."""
        pass

    @abc.abstractmethod
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Store value with optional expiration time in seconds."""
        pass

    @abc.abstractmethod
    def delete(self, key: str) -> None:
        """Delete key from cache."""
        pass

    @abc.abstractmethod
    def clear(self) -> None:
        """Flush all cache entries."""
        pass

    @abc.abstractmethod
    def exists(self, key: str) -> bool:
        """Check if an unexpired key exists in cache."""
        pass

    @abc.abstractmethod
    def size(self) -> int:
        """Return total active unexpired items in cache."""
        pass


class InMemoryCacheBackend(BaseCacheBackend):
    """
    Thread-safe in-memory cache backend with TTL expiration.
    Ideal for local development, tests, and non-distributed single-process deployments.
    """

    def __init__(self):
        self._store: Dict[str, Tuple[Any, Optional[float]]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._store:
                return None

            val, expire_at = self._store[key]
            if expire_at is not None and time.time() > expire_at:
                del self._store[key]
                return None

            return val

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        expire_at = time.time() + ttl_seconds if ttl_seconds is not None else None
        with self._lock:
            self._store[key] = (value, expire_at)
            # Periodic cleanup if store exceeds 2000 entries
            if len(self._store) > 2000:
                self._prune_expired()

    def delete(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def exists(self, key: str) -> bool:
        with self._lock:
            if key not in self._store:
                return False
            _, expire_at = self._store[key]
            if expire_at is not None and time.time() > expire_at:
                del self._store[key]
                return False
            return True

    def size(self) -> int:
        with self._lock:
            self._prune_expired()
            return len(self._store)

    def _prune_expired(self) -> None:
        """Removes expired entries to manage memory footprint."""
        now = time.time()
        expired_keys = [k for k, (_, exp) in self._store.items() if exp is not None and now > exp]
        for k in expired_keys:
            self._store.pop(k, None)


class RedisCacheBackend(BaseCacheBackend):
    """
    Production Redis cache backend.
    Serializes objects as JSON strings with native Redis TTL expiry.
    If Redis is unavailable, logs a warning and falls back to in-memory.
    """

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._client = None
        self._fallback = InMemoryCacheBackend()
        self._connect()

    def _connect(self) -> None:
        try:
            import redis
            self._client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=2.0
            )
            # Test ping
            self._client.ping()
            logger.info("Connected successfully to Redis at %s", self.redis_url)
        except Exception as exc:
            logger.warning("Redis connection failed (%s); using InMemoryCacheBackend fallback.", str(exc))
            self._client = None

    def get(self, key: str) -> Optional[Any]:
        if not self._client:
            return self._fallback.get(key)
        try:
            raw = self._client.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as exc:
            logger.debug("Redis get error for key %s: %s", key, exc)
            return self._fallback.get(key)

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        if not self._client:
            self._fallback.set(key, value, ttl_seconds)
            return
        try:
            serialized = json.dumps(value, default=str)
            if ttl_seconds:
                self._client.setex(key, ttl_seconds, serialized)
            else:
                self._client.set(key, serialized)
        except Exception as exc:
            logger.debug("Redis set error for key %s: %s", key, exc)
            self._fallback.set(key, value, ttl_seconds)

    def delete(self, key: str) -> None:
        if not self._client:
            self._fallback.delete(key)
            return
        try:
            self._client.delete(key)
        except Exception:
            self._fallback.delete(key)

    def clear(self) -> None:
        if not self._client:
            self._fallback.clear()
            return
        try:
            self._client.flushdb()
        except Exception:
            self._fallback.clear()

    def exists(self, key: str) -> bool:
        if not self._client:
            return self._fallback.exists(key)
        try:
            return bool(self._client.exists(key))
        except Exception:
            return self._fallback.exists(key)

    def size(self) -> int:
        if not self._client:
            return self._fallback.size()
        try:
            return int(self._client.dbsize())
        except Exception:
            return self._fallback.size()


class CacheService:
    """
    Unified domain caching service.
    Coordinates key generation, TTL policy enforcement, and backend dispatch.
    """

    def __init__(self, backend: Optional[BaseCacheBackend] = None):
        settings = get_settings()
        if backend is not None:
            self._backend = backend
        elif settings.REDIS_URL and settings.REDIS_URL.strip():
            self._backend = RedisCacheBackend(settings.REDIS_URL.strip())
        else:
            self._backend = InMemoryCacheBackend()

    # --- Core generic interface (fully backward-compatible) ---

    def get(self, key: str) -> Optional[Any]:
        return self._backend.get(key)

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = 300) -> None:
        self._backend.set(key, value, ttl_seconds)

    def delete(self, key: str) -> None:
        self._backend.delete(key)

    def clear(self) -> None:
        self._backend.clear()

    def exists(self, key: str) -> bool:
        return self._backend.exists(key)

    def size(self) -> int:
        return self._backend.size()

    def get_stats(self) -> Dict[str, Any]:
        backend_name = "redis" if isinstance(self._backend, RedisCacheBackend) and getattr(self._backend, "_client", None) else "in-memory"
        return {
            "backend": backend_name,
            "total_keys": self._backend.size()
        }

    # --- Domain Key Generators & Specialized Methods ---

    @staticmethod
    def _sanitize(text: str) -> str:
        """Normalizes cache key string tokens."""
        return re.sub(r"\s+", " ", text.strip().lower())

    @staticmethod
    def hash_query(query: str) -> str:
        """Produces a deterministic 16-character SHA-256 hash for queries."""
        clean = query.strip().lower()
        return hashlib.sha256(clean.encode("utf-8")).hexdigest()[:16]

    # 1. GitHub Search Caching: github_search:<query>
    def get_github_search(self, query: str) -> Optional[Any]:
        key = f"github_search:{self._sanitize(query)}"
        return self._backend.get(key)

    def set_github_search(self, query: str, data: Any, ttl_seconds: Optional[int] = None) -> None:
        settings = get_settings()
        ttl = ttl_seconds if ttl_seconds is not None else settings.CACHE_TTL_GITHUB_SEARCH
        key = f"github_search:{self._sanitize(query)}"
        self._backend.set(key, data, ttl)

    # 2. Repository Metadata Caching: repository:<owner>:<repo>
    def get_repository(self, owner: str, repo: str) -> Optional[Any]:
        key = f"repository:{self._sanitize(owner)}:{self._sanitize(repo)}"
        return self._backend.get(key)

    def set_repository(self, owner: str, repo: str, data: Any, ttl_seconds: Optional[int] = None) -> None:
        settings = get_settings()
        ttl = ttl_seconds if ttl_seconds is not None else settings.CACHE_TTL_REPOSITORY
        key = f"repository:{self._sanitize(owner)}:{self._sanitize(repo)}"
        self._backend.set(key, data, ttl)

    # 3. Repository Deep Analysis Caching: analysis:<owner>:<repo>
    def get_analysis(self, owner: str, repo: str) -> Optional[Any]:
        key = f"analysis:{self._sanitize(owner)}:{self._sanitize(repo)}"
        return self._backend.get(key)

    def set_analysis(self, owner: str, repo: str, data: Any, ttl_seconds: Optional[int] = None) -> None:
        settings = get_settings()
        ttl = ttl_seconds if ttl_seconds is not None else settings.CACHE_TTL_ANALYSIS
        key = f"analysis:{self._sanitize(owner)}:{self._sanitize(repo)}"
        self._backend.set(key, data, ttl)

    # 4. README Content Caching: readme:<owner>:<repo>
    def get_readme(self, owner: str, repo: str) -> Optional[str]:
        key = f"readme:{self._sanitize(owner)}:{self._sanitize(repo)}"
        return self._backend.get(key)

    def set_readme(self, owner: str, repo: str, content: str, ttl_seconds: Optional[int] = None) -> None:
        settings = get_settings()
        ttl = ttl_seconds if ttl_seconds is not None else settings.CACHE_TTL_README
        key = f"readme:{self._sanitize(owner)}:{self._sanitize(repo)}"
        self._backend.set(key, content, ttl)

    # 5. Technology Detection Caching: tech_detection:<owner>:<repo>
    def get_tech_detection(self, owner: str, repo: str) -> Optional[Any]:
        key = f"tech_detection:{self._sanitize(owner)}:{self._sanitize(repo)}"
        return self._backend.get(key)

    def set_tech_detection(self, owner: str, repo: str, data: Any, ttl_seconds: Optional[int] = None) -> None:
        settings = get_settings()
        ttl = ttl_seconds if ttl_seconds is not None else settings.CACHE_TTL_ANALYSIS
        key = f"tech_detection:{self._sanitize(owner)}:{self._sanitize(repo)}"
        self._backend.set(key, data, ttl)

    # 6. Ranked Search Pipeline Caching: ranking:<query_hash>
    def get_ranking(self, query: str) -> Optional[Any]:
        query_hash = self.hash_query(query)
        key = f"ranking:{query_hash}"
        return self._backend.get(key)

    def set_ranking(self, query: str, data: Any, ttl_seconds: Optional[int] = None) -> None:
        settings = get_settings()
        ttl = ttl_seconds if ttl_seconds is not None else settings.CACHE_TTL_RANKING
        query_hash = self.hash_query(query)
        key = f"ranking:{query_hash}"
        self._backend.set(key, data, ttl)


# Global singleton instance
cache_service = CacheService()
