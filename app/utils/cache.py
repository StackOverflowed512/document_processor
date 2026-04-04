"""
Caching utilities for improving performance and reducing API calls
"""

import json
import hashlib
from typing import Optional, Any, Dict
from datetime import datetime, timedelta
from pathlib import Path
import pickle
from loguru import logger
import asyncio
from collections import OrderedDict


class InMemoryCache:
    """Simple in-memory cache with LRU eviction"""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: OrderedDict = OrderedDict()
        self.timestamps: Dict[str, datetime] = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired"""
        if key in self.cache:
            # Check if expired
            if self._is_expired(key):
                self.delete(key)
                return None
            
            # Move to end (most recently used)
            value = self.cache.pop(key)
            self.cache[key] = value
            return value
        
        return None
    
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None):
        """Set value in cache with optional TTL"""
        # Check if we need to evict
        if len(self.cache) >= self.max_size and key not in self.cache:
            self._evict_oldest()
        
        self.cache[key] = value
        self.timestamps[key] = datetime.now()
        
        # Use custom TTL if provided, otherwise default
        ttl = ttl_seconds or self.ttl_seconds
        self.timestamps[key + "_ttl"] = datetime.now() + timedelta(seconds=ttl)
    
    def delete(self, key: str):
        """Delete key from cache"""
        if key in self.cache:
            del self.cache[key]
        if key in self.timestamps:
            del self.timestamps[key]
        if key + "_ttl" in self.timestamps:
            del self.timestamps[key + "_ttl"]
    
    def clear(self):
        """Clear entire cache"""
        self.cache.clear()
        self.timestamps.clear()
    
    def _is_expired(self, key: str) -> bool:
        """Check if cache entry is expired"""
        ttl_key = key + "_ttl"
        if ttl_key in self.timestamps:
            return datetime.now() > self.timestamps[ttl_key]
        return False
    
    def _evict_oldest(self):
        """Evict oldest entry from cache"""
        if self.cache:
            oldest_key = next(iter(self.cache))
            self.delete(oldest_key)
            logger.debug(f"Evicted oldest cache entry: {oldest_key}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "ttl_seconds": self.ttl_seconds,
            "hit_rate": "N/A"  # Would need tracking
        }


class DiskCache:
    """Disk-based cache for larger objects"""
    
    def __init__(self, cache_dir: Path = Path("./cache"), ttl_seconds: int = 86400):
        self.cache_dir = Path(cache_dir)
        self.ttl_seconds = ttl_seconds
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_path(self, key: str) -> Path:
        """Get file path for cache key"""
        # Create hash of key for filename
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from disk cache"""
        cache_path = self._get_cache_path(key)
        
        if not cache_path.exists():
            return None
        
        # Check if expired
        if self._is_expired(cache_path):
            cache_path.unlink()
            return None
        
        try:
            with open(cache_path, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            logger.error(f"Failed to load cache for {key}: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None):
        """Set value in disk cache"""
        cache_path = self._get_cache_path(key)
        
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(value, f)
            
            # Store timestamp
            timestamp_path = cache_path.with_suffix('.timestamp')
            ttl = ttl_seconds or self.ttl_seconds
            expiry = datetime.now() + timedelta(seconds=ttl)
            with open(timestamp_path, 'w') as f:
                f.write(expiry.isoformat())
                
        except Exception as e:
            logger.error(f"Failed to save cache for {key}: {e}")
    
    def delete(self, key: str):
        """Delete from disk cache"""
        cache_path = self._get_cache_path(key)
        if cache_path.exists():
            cache_path.unlink()
        
        timestamp_path = cache_path.with_suffix('.timestamp')
        if timestamp_path.exists():
            timestamp_path.unlink()
    
    def clear(self):
        """Clear entire disk cache"""
        for cache_file in self.cache_dir.glob("*.cache"):
            cache_file.unlink()
        for timestamp_file in self.cache_dir.glob("*.timestamp"):
            timestamp_file.unlink()
    
    def _is_expired(self, cache_path: Path) -> bool:
        """Check if cached file is expired"""
        timestamp_path = cache_path.with_suffix('.timestamp')
        
        if not timestamp_path.exists():
            return True
        
        try:
            with open(timestamp_path, 'r') as f:
                expiry_str = f.read().strip()
                expiry = datetime.fromisoformat(expiry_str)
                return datetime.now() > expiry
        except:
            return True


class CacheManager:
    """Manager for multiple cache backends"""
    
    def __init__(self):
        self.memory_cache = InMemoryCache(max_size=500, ttl_seconds=1800)  # 30 minutes
        self.disk_cache = DiskCache(ttl_seconds=86400)  # 24 hours
        
        # Track cache statistics
        self.stats = {
            "memory_hits": 0,
            "memory_misses": 0,
            "disk_hits": 0,
            "disk_misses": 0
        }
    
    async def get(self, key: str, use_disk: bool = True) -> Optional[Any]:
        """
        Get value from cache (memory first, then disk)
        
        Args:
            key: Cache key
            use_disk: Whether to check disk cache if not in memory
        
        Returns:
            Cached value or None
        """
        # Check memory cache first
        value = self.memory_cache.get(key)
        if value is not None:
            self.stats["memory_hits"] += 1
            return value
        
        self.stats["memory_misses"] += 1
        
        # Check disk cache if enabled
        if use_disk:
            value = self.disk_cache.get(key)
            if value is not None:
                self.stats["disk_hits"] += 1
                # Promote to memory cache
                self.memory_cache.set(key, value)
                return value
            self.stats["disk_misses"] += 1
        
        return None
    
    async def set(self, key: str, value: Any, memory_ttl: Optional[int] = None, disk_ttl: Optional[int] = None):
        """
        Set value in both memory and disk caches
        
        Args:
            key: Cache key
            value: Value to cache
            memory_ttl: TTL for memory cache (seconds)
            disk_ttl: TTL for disk cache (seconds)
        """
        # Set in memory
        self.memory_cache.set(key, value, memory_ttl)
        
        # Set in disk asynchronously
        if disk_ttl != 0:  # 0 means don't save to disk
            await asyncio.get_event_loop().run_in_executor(
                None, self.disk_cache.set, key, value, disk_ttl
            )
    
    async def delete(self, key: str):
        """Delete from all caches"""
        self.memory_cache.delete(key)
        await asyncio.get_event_loop().run_in_executor(None, self.disk_cache.delete, key)
    
    async def clear(self):
        """Clear all caches"""
        self.memory_cache.clear()
        await asyncio.get_event_loop().run_in_executor(None, self.disk_cache.clear)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_memory_requests = self.stats["memory_hits"] + self.stats["memory_misses"]
        memory_hit_rate = self.stats["memory_hits"] / total_memory_requests if total_memory_requests > 0 else 0
        
        total_disk_requests = self.stats["disk_hits"] + self.stats["disk_misses"]
        disk_hit_rate = self.stats["disk_hits"] / total_disk_requests if total_disk_requests > 0 else 0
        
        return {
            "memory": {
                "size": len(self.memory_cache.cache),
                "max_size": self.memory_cache.max_size,
                "hits": self.stats["memory_hits"],
                "misses": self.stats["memory_misses"],
                "hit_rate": f"{memory_hit_rate:.2%}"
            },
            "disk": {
                "hits": self.stats["disk_hits"],
                "misses": self.stats["disk_misses"],
                "hit_rate": f"{disk_hit_rate:.2%}"
            }
        }


# Global cache instance
cache_manager = CacheManager()


def get_cache_key(prefix: str, *args, **kwargs) -> str:
    """Generate cache key from components"""
    key_parts = [prefix]
    key_parts.extend(str(arg) for arg in args)
    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
    
    key = "|".join(key_parts)
    
    # Hash long keys to avoid issues
    if len(key) > 200:
        key = hashlib.md5(key.encode()).hexdigest()
    
    return key