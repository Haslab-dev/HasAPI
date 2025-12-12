"""
HasAPI Vector Store Module

Provides vector storage and similarity search functionality.
"""

from .base import VectorStore, FilterExpression
from .memory import InMemoryVectorStore

__all__ = [
    "VectorStore",
    "InMemoryVectorStore",
    "FilterExpression",
]