"""
Cache - Simple in-memory cache with TTL support.
"""

import time
import fnmatch
from typing import Any, Dict, Optional
from dataclasses import dataclass
from threading import Lock


@dataclass
class CacheEntry:
    """Single cache entry with value and expiration."""
    value: Any
    expires_at: float


class Cache:
    """
    Simple in-memory cache with TTL support.
    
    Thread-safe implementation for caching API responses.
    """
    
    def __init__(self, enabled: bool = True, ttl: int = 300, max_size: int = 1000):
        """
        Initialize cache.
        
        Args:
            enabled: Whether caching is enabled.
            ttl: Time-to-live in seconds.
            max_size: Maximum number of entries.
        """
        self.enabled = enabled
        self.ttl = ttl
        self.max_size = max_size
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = Lock()
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key.
            
        Returns:
            Cached value or None if not found/expired.
        """
        if not self.enabled:
            return None
        
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self._misses += 1
                return None
            
            if time.time() > entry.expires_at:
                del self._cache[key]
                self._misses += 1
                return None
            
            self._hits += 1
            return entry.value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set value in cache.
        
        Args:
            key: Cache key.
            value: Value to cache.
            ttl: Custom TTL (uses default if None).
        """
        if not self.enabled:
            return
        
        with self._lock:
            # Evict if at max size
            if len(self._cache) >= self.max_size:
                self._evict_oldest()
            
            expires_at = time.time() + (ttl or self.ttl)
            self._cache[key] = CacheEntry(value=value, expires_at=expires_at)
    
    def invalidate(self, key: str) -> bool:
        """
        Invalidate a specific cache entry.
        
        Args:
            key: Cache key to invalidate.
            
        Returns:
            True if entry was removed, False if not found.
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def invalidate_prefix(self, prefix: str) -> int:
        """
        Invalidate all entries matching a prefix pattern.
        
        Args:
            prefix: Pattern to match (supports wildcards).
            
        Returns:
            Number of entries invalidated.
        """
        with self._lock:
            keys_to_remove = [
                key for key in self._cache.keys()
                if fnmatch.fnmatch(key, prefix)
            ]
            for key in keys_to_remove:
                del self._cache[key]
            return len(keys_to_remove)
    
    def clear(self) -> int:
        """
        Clear all cache entries.
        
        Returns:
            Number of entries cleared.
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count
    
    def _evict_oldest(self) -> None:
        """Evict the oldest entry."""
        if not self._cache:
            return
        
        oldest_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k].expires_at
        )
        del self._cache[oldest_key]
    
    def cleanup_expired(self) -> int:
        """
        Remove all expired entries.
        
        Returns:
            Number of entries removed.
        """
        with self._lock:
            now = time.time()
            expired_keys = [
                key for key, entry in self._cache.items()
                if now > entry.expires_at
            ]
            for key in expired_keys:
                del self._cache[key]
            return len(expired_keys)
    
    @property
    def size(self) -> int:
        """Current number of entries."""
        return len(self._cache)
    
    @property
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0
        
        return {
            "enabled": self.enabled,
            "size": self.size,
            "max_size": self.max_size,
            "ttl": self.ttl,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
        }
    
    def __contains__(self, key: str) -> bool:
        """Check if key is in cache (and not expired)."""
        return self.get(key) is not None
    
    def __len__(self) -> int:
        """Return number of entries."""
        return self.size
