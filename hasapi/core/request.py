"""
HasAPI Fast Request - Minimal request object for hot path

Design principles:
- Lazy evaluation of everything
- No parsing until needed
- Direct attribute access (no method calls in hot path)
- orjson for JSON parsing
"""

from __future__ import annotations
import orjson
from typing import Dict, Any, Optional, List, Union, TYPE_CHECKING
from urllib.parse import parse_qs

if TYPE_CHECKING:
    pass


class FastRequest:
    """
    Minimal request object optimized for speed.
    
    Hot path access patterns:
    - request.method -> direct attribute
    - request.path -> direct attribute  
    - request.headers -> lazy dict
    - request.json() -> lazy orjson parse
    
    Everything else is lazy-loaded on first access.
    """
    
    __slots__ = (
        'method', 'path', 'query_string', 'path_params',
        '_headers_raw', '_headers', '_query_params',
        '_body', '_json', '_receive', '_scope'
    )
    
    def __init__(
        self,
        method: str,
        path: str,
        headers_raw: List[tuple] = None,
        query_string: bytes = b'',
        body: bytes = None,
        receive: callable = None,
        scope: dict = None,
        path_params: Dict[str, str] = None
    ):
        # Direct access - no property overhead
        self.method = method
        self.path = path
        self.query_string = query_string
        self.path_params = path_params or {}
        
        # Lazy-loaded
        self._headers_raw = headers_raw or []
        self._headers: Optional[Dict[str, str]] = None
        self._query_params: Optional[Dict[str, str]] = None
        self._body = body
        self._json: Optional[Any] = None
        self._receive = receive
        self._scope = scope
    
    @classmethod
    def from_scope(cls, scope: dict, receive: callable) -> 'FastRequest':
        """Create from ASGI scope - used by Python transport"""
        return cls(
            method=scope['method'],
            path=scope['path'],
            headers_raw=scope.get('headers', []),
            query_string=scope.get('query_string', b''),
            receive=receive,
            scope=scope
        )
    
    @classmethod
    def from_transport(
        cls,
        method: str,
        path: str,
        headers: Dict[str, str],
        query_string: str,
        body: bytes,
        path_params: Dict[str, str] = None
    ) -> 'FastRequest':
        """Create from native transport - pre-parsed data"""
        req = cls(
            method=method,
            path=path,
            query_string=query_string.encode() if isinstance(query_string, str) else query_string,
            body=body,
            path_params=path_params
        )
        req._headers = headers  # Already parsed by transport
        return req
    
    @property
    def headers(self) -> Dict[str, str]:
        """Lazy header parsing"""
        if self._headers is None:
            self._headers = {
                k.decode('latin-1').lower(): v.decode('latin-1')
                for k, v in self._headers_raw
            }
        return self._headers
    
    @property
    def query_params(self) -> Dict[str, str]:
        """Lazy query param parsing"""
        if self._query_params is None:
            if self.query_string:
                qs = self.query_string.decode('latin-1') if isinstance(self.query_string, bytes) else self.query_string
                parsed = parse_qs(qs, keep_blank_values=True)
                self._query_params = {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}
            else:
                self._query_params = {}
        return self._query_params
    
    async def body(self) -> bytes:
        """Get request body"""
        if self._body is None:
            if self._receive is None:
                return b''
            
            chunks = []
            while True:
                message = await self._receive()
                chunks.append(message.get('body', b''))
                if not message.get('more_body', False):
                    break
            self._body = b''.join(chunks)
        
        return self._body
    
    async def json(self) -> Any:
        """Parse JSON body using orjson"""
        if self._json is None:
            body = await self.body()
            if body:
                self._json = orjson.loads(body)
            else:
                self._json = {}
        return self._json
    
    async def text(self) -> str:
        """Get body as text"""
        body = await self.body()
        return body.decode('utf-8')
    
    def get_header(self, name: str, default: str = None) -> Optional[str]:
        """Get header by name (case-insensitive)"""
        return self.headers.get(name.lower(), default)
    
    def get_query(self, name: str, default: str = None) -> Optional[str]:
        """Get query param by name"""
        return self.query_params.get(name, default)
    
    @property
    def content_type(self) -> str:
        """Get content-type header"""
        ct = self.get_header('content-type', '')
        return ct.split(';')[0].strip()
    
    @property
    def client(self) -> Optional[tuple]:
        """Client address"""
        if self._scope:
            return self._scope.get('client')
        return None
    
    def __repr__(self) -> str:
        return f"FastRequest({self.method} {self.path})"
