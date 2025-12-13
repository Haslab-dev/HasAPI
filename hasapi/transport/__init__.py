"""
HasAPI Transport Layer

Pure Python transport using uvloop + httptools + orjson.
Maximum performance for a Python framework.
"""

from .base import TransportEngine, TransportConfig
from .python_engine import PythonEngine


def create_engine(config: TransportConfig = None) -> TransportEngine:
    """Create Python transport engine."""
    return PythonEngine(config or TransportConfig())


__all__ = [
    'TransportEngine',
    'TransportConfig',
    'PythonEngine',
    'create_engine',
]
