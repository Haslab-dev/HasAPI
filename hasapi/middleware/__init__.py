"""
HasAPI Middleware System

Provides middleware for authentication, CORS, and other cross-cutting concerns.
"""

from .base import Middleware, MiddlewareStack
from .cors import CORSMiddleware
from .auth import AuthMiddleware, JWTAuthMiddleware

__all__ = [
    "Middleware",
    "MiddlewareStack", 
    "CORSMiddleware",
    "AuthMiddleware",
    "JWTAuthMiddleware",
]