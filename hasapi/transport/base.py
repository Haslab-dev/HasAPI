"""
HasAPI Transport Base Classes

Abstract interface for transport engines.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable, Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.engine import ExecutionEngine


@dataclass
class TransportConfig:
    """Transport engine configuration"""
    host: str = '127.0.0.1'
    port: int = 8000
    workers: int = 1
    backlog: int = 2048
    keep_alive: int = 5
    # TLS
    ssl_cert: Optional[str] = None
    ssl_key: Optional[str] = None
    # Limits
    max_request_size: int = 16 * 1024 * 1024  # 16MB
    header_timeout: float = 30.0
    body_timeout: float = 60.0
    # Debug
    debug: bool = False
    access_log: bool = True


class TransportEngine(ABC):
    """
    Abstract transport engine interface.
    
    Transport engines handle:
    - Socket management
    - TLS termination
    - HTTP parsing
    - Keep-alive
    - Backpressure
    
    They do NOT handle:
    - Routing
    - Business logic
    - Response generation
    """
    
    def __init__(self, config: TransportConfig):
        self.config = config
        self._engine: Optional['ExecutionEngine'] = None
        self._running = False
    
    def set_execution_engine(self, engine: 'ExecutionEngine') -> None:
        """Set the execution engine that processes requests"""
        self._engine = engine
    
    @abstractmethod
    async def start(self) -> None:
        """Start the transport engine"""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop the transport engine"""
        pass
    
    @abstractmethod
    def run(self) -> None:
        """Run the transport engine (blocking)"""
        pass
    
    @property
    def is_running(self) -> bool:
        """Check if engine is running"""
        return self._running
    
    @property
    @abstractmethod
    def engine_name(self) -> str:
        """Get engine name for logging"""
        pass
