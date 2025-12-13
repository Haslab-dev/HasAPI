"""
HasAPI Core - Hot Path Execution Engine

This module contains the performance-critical components:
- Cached routing with dict/tuple lookups
- Pre-bound handlers
- Zero reflection at runtime
"""

from .router import CachedRouter, CompiledRoute
from .request import FastRequest
from .response import FastResponse, fast_json_response
from .engine import ExecutionEngine

__all__ = [
    "CachedRouter",
    "CompiledRoute", 
    "FastRequest",
    "FastResponse",
    "fast_json_response",
    "ExecutionEngine",
]
