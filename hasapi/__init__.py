"""
HasAPI - High-performance Python API framework

Fast, simple, and production-ready.
"""

__version__ = "0.1.0"

from .app import HasAPI
from .core.request import FastRequest
from .core.response import (
    FastJSONResponse,
    FastHTMLResponse,
    FastTextResponse,
    FastStreamingResponse,
    FastSSEResponse,
)

__all__ = [
    "HasAPI",
    "FastRequest",
    "FastJSONResponse",
    "FastHTMLResponse",
    "FastTextResponse",
    "FastStreamingResponse",
    "FastSSEResponse",
]
