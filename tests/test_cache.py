"""Tests for Cache module."""

import time
import pytest
from shadowfs.cache import Cache


class TestCache:
    """Test cases for Cache class."""
    
    def test_basic_get_set(self):
        """Test basic get and set operations."""
        cache = Cache(enabled=True, ttl=60)
        
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
    
    def test_get_missing_key(self):
        """Test get returns None for missing key."""
        cache = Cache(enabled=True, ttl=60)
        
        assert cache.get("nonexistent") is None
    
    def test_ttl_expiration(self):
        """Test that entries expire after TTL."""
        cache = Cache(enabled=True, ttl=1)  # 1 second TTL
        
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
        time.sleep(1.1)
        assert cache.get("key1") is None
    
    def test_custom_ttl(self):
        """Test custom TTL per entry."""
        cache = Cache(enabled=True, ttl=60)
        
        cache.set("key1", "value1", ttl=1)
        assert cache.get("key1") == "value1"
        
        time.sleep(1.1)
        assert cache.get("key1") is None
    
    def test_disabled_cache(self):
        """Test that disabled cache doesn't store values."""
        cache = Cache(enabled=False)
        
        cache.set("key1", "value1")
        assert cache.get("key1") is None
    
    def test_invalidate(self):
        """Test invalidating a specific key."""
        cache = Cache(enabled=True, ttl=60)
        
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
        cache.invalidate("key1")
        assert cache.get("key1") is None
    
    def test_invalidate_prefix(self):
        """Test invalidating by prefix pattern."""
        cache = Cache(enabled=True, ttl=60)
        
        cache.set("read:repo1:file1", "content1")
        cache.set("read:repo1:file2", "content2")
        cache.set("read:repo2:file1", "content3")
        cache.set("write:repo1:file1", "content4")
        
        count = cache.invalidate_prefix("read:repo1:*")
        assert count == 2
        
        assert cache.get("read:repo1:file1") is None
        assert cache.get("read:repo1:file2") is None
        assert cache.get("read:repo2:file1") == "content3"
        assert cache.get("write:repo1:file1") == "content4"
    
    def test_clear(self):
        """Test clearing all entries."""
        cache = Cache(enabled=True, ttl=60)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        count = cache.clear()
        assert count == 2
        assert cache.size == 0
    
    def test_max_size_eviction(self):
        """Test that oldest entries are evicted when max size reached."""
        cache = Cache(enabled=True, ttl=60, max_size=3)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        assert cache.size == 3
        
        cache.set("key4", "value4")
        assert cache.size == 3
    
    def test_stats(self):
        """Test cache statistics."""
        cache = Cache(enabled=True, ttl=60)
        
        cache.set("key1", "value1")
        cache.get("key1")  # hit
        cache.get("key2")  # miss
        
        stats = cache.stats
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["size"] == 1
    
    def test_contains(self):
        """Test __contains__ method."""
        cache = Cache(enabled=True, ttl=60)
        
        cache.set("key1", "value1")
        assert "key1" in cache
        assert "key2" not in cache
    
    def test_cleanup_expired(self):
        """Test cleanup of expired entries."""
        cache = Cache(enabled=True, ttl=1)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2", ttl=60)
        
        time.sleep(1.1)
        
        count = cache.cleanup_expired()
        assert count == 1
        assert cache.get("key2") == "value2"
