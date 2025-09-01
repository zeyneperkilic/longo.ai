"""
Cache utility functions for Longopass AI
Memory-based caching with TTL support
"""

import time
from typing import Any, Dict, Optional
from functools import wraps
import threading

class MemoryCache:
    """Simple in-memory cache with TTL support"""
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired"""
        with self._lock:
            if key in self._cache:
                item = self._cache[key]
                if time.time() < item['expires_at']:
                    return item['value']
                else:
                    # Expired, remove it
                    del self._cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl_seconds: int = 300) -> None:
        """Set value in cache with TTL"""
        with self._lock:
            self._cache[key] = {
                'value': value,
                'expires_at': time.time() + ttl_seconds
            }
    
    def delete(self, key: str) -> None:
        """Delete key from cache"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
    
    def clear(self) -> None:
        """Clear all cache"""
        with self._lock:
            self._cache.clear()
    
    def size(self) -> int:
        """Get cache size"""
        with self._lock:
            return len(self._cache)
    
    def cleanup_expired(self) -> int:
        """Remove expired items, return count of removed items"""
        removed = 0
        current_time = time.time()
        
        with self._lock:
            expired_keys = [
                key for key, item in self._cache.items()
                if current_time >= item['expires_at']
            ]
            
            for key in expired_keys:
                del self._cache[key]
                removed += 1
        
        return removed

# Global cache instance
cache = MemoryCache()

# Session-based question count cache (free users için)
session_question_cache = MemoryCache()

def get_session_question_count(user_id: str) -> int:
    """Free kullanıcının günlük soru sayısını getir"""
    key = f"free_user_questions:{user_id}"
    count = session_question_cache.get(key)
    return count if count is not None else 0

def increment_session_question_count(user_id: str) -> int:
    """Free kullanıcının günlük soru sayısını artır"""
    key = f"free_user_questions:{user_id}"
    current_count = get_session_question_count(user_id)
    new_count = current_count + 1
    
    # 24 saat TTL (günlük reset için)
    session_question_cache.set(key, new_count, ttl_seconds=86400)
    return new_count

def reset_session_question_count(user_id: str) -> None:
    """Free kullanıcının günlük soru sayısını sıfırla"""
    key = f"free_user_questions:{user_id}"
    session_question_cache.delete(key)

def cached(ttl_seconds: int = 300, key_prefix: str = ""):
    """
    Decorator for caching function results
    
    Args:
        ttl_seconds: Time to live in seconds (default: 5 minutes)
        key_prefix: Prefix for cache key (default: empty)
    
    Usage:
        @cached(ttl_seconds=3600, key_prefix="supplements")
        def get_supplements():
            return db.query(Supplement).all()
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name, args, and kwargs
            args_str = str(args)
            kwargs_str = str(sorted(kwargs.items()))
            cache_key = f"{key_prefix}:{func.__name__}:{hash(args_str + kwargs_str)}"
            
            # Try to get from cache first
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # If not in cache, call function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl_seconds)
            
            return result
        return wrapper
    return decorator

def cache_supplements(ttl_seconds: int = 3600):
    """Special decorator for supplement-related functions"""
    return cached(ttl_seconds=ttl_seconds, key_prefix="supplements")

def cache_user_context(ttl_seconds: int = 300):
    """Special decorator for user context functions"""
    return cached(ttl_seconds=ttl_seconds, key_prefix="user_context")

def cache_model_response(ttl_seconds: int = 600):
    """Special decorator for AI model responses"""
    return cached(ttl_seconds=ttl_seconds, key_prefix="model_response")

# Cache management functions
def clear_supplements_cache():
    """Clear all supplement-related cache"""
    cache.clear()

def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics"""
    return {
        "size": cache.size(),
        "timestamp": time.time()
    }

def cleanup_cache():
    """Clean up expired cache items"""
    return cache.cleanup_expired()
