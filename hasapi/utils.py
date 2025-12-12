"""
HasAPI Utilities

Common utility functions and classes used throughout the framework.
"""

import logging
import time
import uuid
import inspect
from typing import Any, Dict, List, Optional, Callable, Union, Type, get_type_hints
from functools import wraps
from dataclasses import dataclass

# Configure logging
def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name"""
    return logging.getLogger(name)


def setup_logging(level: str = "INFO", format_string: Optional[str] = None):
    """Setup logging configuration"""
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=format_string
    )


@dataclass
class Timer:
    """Simple timer for measuring execution time"""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
    
    def start(self):
        """Start the timer"""
        self.start_time = time.perf_counter()
        return self
    
    def stop(self):
        """Stop the timer"""
        self.end_time = time.perf_counter()
        return self
    
    def elapsed(self) -> float:
        """Get elapsed time in seconds"""
        if self.start_time is None:
            return 0.0
        
        end = self.end_time or time.perf_counter()
        return end - self.start_time
    
    def __enter__(self):
        return self.start()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


def generate_id() -> str:
    """Generate a unique ID"""
    return str(uuid.uuid4())


def safe_json_dumps(obj: Any) -> str:
    """Safely serialize object to JSON"""
    import json
    try:
        return json.dumps(obj, default=str)
    except (TypeError, ValueError):
        return str(obj)


def get_function_signature(func: Callable) -> Dict[str, Any]:
    """Get information about a function's signature"""
    sig = inspect.signature(func)
    type_hints = get_type_hints(func)
    
    params = {}
    for name, param in sig.parameters.items():
        param_info = {
            "name": name,
            "default": param.default if param.default != inspect.Parameter.empty else None,
            "annotation": type_hints.get(name, None),
            "kind": param.kind.name
        }
        params[name] = param_info
    
    return {
        "name": func.__name__,
        "params": params,
        "return_annotation": type_hints.get("return", None),
        "docstring": func.__doc__
    }


async def run_async(func: Callable, *args, **kwargs):
    """Run a function asynchronously"""
    if inspect.iscoroutinefunction(func):
        return await func(*args, **kwargs)
    else:
        return func(*args, **kwargs)


def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    Decorator for retrying functions on failure.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each attempt
    """
    def decorator(func):
        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                current_delay = delay
                last_exception = None
                
                for attempt in range(max_attempts):
                    try:
                        return await func(*args, **kwargs)
                    except Exception as e:
                        last_exception = e
                        if attempt < max_attempts - 1:
                            await asyncio.sleep(current_delay)
                            current_delay *= backoff
                
                raise last_exception
            
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                import time
                current_delay = delay
                last_exception = None
                
                for attempt in range(max_attempts):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        last_exception = e
                        if attempt < max_attempts - 1:
                            time.sleep(current_delay)
                            current_delay *= backoff
                
                raise last_exception
            
            return sync_wrapper
    
    return decorator


def cache(ttl: Optional[float] = None):
    """
    Simple in-memory cache decorator.
    
    Args:
        ttl: Time to live in seconds (None for no expiration)
    """
    def decorator(func):
        cache_data = {}
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key
            key = str(args) + str(sorted(kwargs.items()))
            
            # Check cache
            if key in cache_data:
                cached_value, cached_time = cache_data[key]
                
                # Check TTL
                if ttl is None or (time.time() - cached_time) < ttl:
                    return cached_value
            
            # Compute and cache result
            result = func(*args, **kwargs)
            cache_data[key] = (result, time.time())
            
            return result
        
        # Add cache management methods
        wrapper.cache_clear = lambda: cache_data.clear()
        wrapper.cache_info = lambda: {
            "size": len(cache_data),
            "ttl": ttl
        }
        
        return wrapper
    
    return decorator


def validate_types(func: Callable) -> Callable:
    """
    Decorator to validate function parameter types.
    
    Uses type hints to validate parameters at runtime.
    """
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        sig = inspect.signature(func)
        type_hints = get_type_hints(func)
        
        # Convert args to kwargs
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()
        
        # Validate types
        for name, value in bound_args.arguments.items():
            if name in type_hints:
                expected_type = type_hints[name]
                if not isinstance(value, expected_type):
                    raise TypeError(
                        f"Argument '{name}' expected {expected_type}, got {type(value)}"
                    )
        
        return await func(*args, **kwargs)
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        sig = inspect.signature(func)
        type_hints = get_type_hints(func)
        
        # Convert args to kwargs
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()
        
        # Validate types
        for name, value in bound_args.arguments.items():
            if name in type_hints:
                expected_type = type_hints[name]
                if not isinstance(value, expected_type):
                    raise TypeError(
                        f"Argument '{name}' expected {expected_type}, got {type(value)}"
                    )
        
        return func(*args, **kwargs)
    
    if inspect.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


class RateLimiter:
    """Simple rate limiter implementation"""
    
    def __init__(self, max_requests: int, time_window: float):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum number of requests allowed
            time_window: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
    
    def is_allowed(self) -> bool:
        """Check if a request is allowed"""
        now = time.time()
        
        # Remove old requests
        self.requests = [req_time for req_time in self.requests 
                        if now - req_time < self.time_window]
        
        # Check if under limit
        if len(self.requests) < self.max_requests:
            self.requests.append(now)
            return True
        
        return False
    
    def reset(self):
        """Reset the rate limiter"""
        self.requests = []


class AsyncRateLimiter:
    """Async version of rate limiter with lock"""
    
    def __init__(self, max_requests: int, time_window: float):
        """
        Initialize async rate limiter.
        
        Args:
            max_requests: Maximum number of requests allowed
            time_window: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
        self._lock = None
    
    async def is_allowed(self) -> bool:
        """Check if a request is allowed (thread-safe)"""
        if self._lock is None:
            import asyncio
            self._lock = asyncio.Lock()
        
        async with self._lock:
            now = time.time()
            
            # Remove old requests
            self.requests = [req_time for req_time in self.requests 
                            if now - req_time < self.time_window]
            
            # Check if under limit
            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                return True
            
            return False
    
    async def reset(self):
        """Reset the rate limiter"""
        if self._lock is None:
            import asyncio
            self._lock = asyncio.Lock()
        
        async with self._lock:
            self.requests = []


def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug"""
    import re
    # Convert to lowercase and replace spaces with hyphens
    text = re.sub(r'\s+', '-', text.lower())
    # Remove special characters except hyphens
    text = re.sub(r'[^a-z0-9-]', '', text)
    # Remove multiple consecutive hyphens
    text = re.sub(r'-+', '-', text)
    # Remove leading/trailing hyphens
    text = text.strip('-')
    return text


def truncate_string(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate a string to a maximum length"""
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def deep_merge(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two dictionaries"""
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    
    return result