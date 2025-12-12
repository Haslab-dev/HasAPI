"""
HasAPI Request Module

Handles HTTP request parsing and provides convenient access to request data.
"""

import json
from typing import Dict, Any, Optional, List, Union
from urllib.parse import parse_qs

from .utils import get_logger

logger = get_logger(__name__)


class Request:
    """
    HTTP request object that provides convenient access to request data.
    
    This class wraps the ASGI scope and receive callable to provide
    easy access to headers, query parameters, body, etc.
    """
    
    def __init__(self, scope: dict, receive: callable):
        self.scope = scope
        self.receive = receive
        self._headers: Optional[Dict[str, str]] = None
        self._query_params: Optional[Dict[str, Union[str, List[str]]]] = None
        self._body: Optional[bytes] = None
        self._json: Optional[Dict[str, Any]] = None
        self._form: Optional[Dict[str, Union[str, List[str]]]] = None
    
    @property
    def method(self) -> str:
        """HTTP method"""
        return self.scope["method"]
    
    @property
    def url(self) -> str:
        """Full URL including query string"""
        return self.scope.get("path", "")
    
    @property
    def path(self) -> str:
        """URL path without query string"""
        return self.scope.get("path", "")
    
    @property
    def query_string(self) -> str:
        """Raw query string"""
        return self.scope.get("query_string", b"").decode("utf-8")
    
    @property
    def headers(self) -> Dict[str, str]:
        """Request headers as a dictionary"""
        if self._headers is None:
            # Optimize: decode headers only once
            headers_raw = self.scope.get("headers", [])
            self._headers = {
                name.decode("latin-1").lower(): value.decode("latin-1")
                for name, value in headers_raw
            }
        return self._headers
    
    @property
    def query_params(self) -> Dict[str, Union[str, List[str]]]:
        """Query parameters as a dictionary"""
        if self._query_params is None:
            query_bytes = self.scope.get("query_string", b"")
            if query_bytes:
                # Optimize: parse directly from bytes
                query_string = query_bytes.decode("latin-1")
                parsed = parse_qs(query_string, keep_blank_values=True)
                # Convert single-item lists to strings
                self._query_params = {
                    k: v[0] if len(v) == 1 else v 
                    for k, v in parsed.items()
                }
            else:
                self._query_params = {}
        return self._query_params
    
    def get_query_param(self, name: str, default: Any = None) -> Any:
        """Get a specific query parameter"""
        return self.query_params.get(name, default)
    
    def get_header(self, name: str, default: Any = None) -> Any:
        """Get a specific header"""
        return self.headers.get(name.lower(), default)
    
    def get_content_type(self) -> str:
        """Get the content type from headers"""
        content_type = self.get_header("content-type", "")
        return content_type.split(";")[0].strip()
    
    async def body(self) -> bytes:
        """Get the request body as bytes"""
        if self._body is None:
            body_chunks = []
            more_body = True
            
            while more_body:
                message = await self.receive()
                body_chunks.append(message.get("body", b""))
                more_body = message.get("more_body", False)
            
            self._body = b"".join(body_chunks)
        
        return self._body
    
    async def text(self) -> str:
        """Get the request body as text"""
        body = await self.body()
        return body.decode("utf-8")
    
    async def json(self) -> Dict[str, Any]:
        """Get the request body as JSON"""
        if self._json is None:
            content_type = self.get_content_type()
            
            if content_type != "application/json":
                raise ValueError(f"Expected JSON content type, got: {content_type}")
            
            text = await self.text()
            try:
                self._json = json.loads(text)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON: {e}")
        
        return self._json
    
    async def form(self) -> Dict[str, Union[str, List[str]]]:
        """Get the request body as form data"""
        if self._form is None:
            content_type = self.get_content_type()
            
            if content_type != "application/x-www-form-urlencoded":
                raise ValueError(f"Expected form content type, got: {content_type}")
            
            text = await self.text()
            parsed = parse_qs(text, keep_blank_values=True)
            
            # Convert single-item lists to strings
            self._form = {
                k: v[0] if len(v) == 1 else v 
                for k, v in parsed.items()
            }
        
        return self._form
    
    @property
    def client(self) -> Optional[tuple]:
        """Client address as (host, port)"""
        return self.scope.get("client")
    
    @property
    def scheme(self) -> str:
        """URL scheme (http or https)"""
        return self.scope.get("scheme", "http")
    
    @property
    def server(self) -> Optional[tuple]:
        """Server address as (host, port)"""
        return self.scope.get("server")
    
    def url_for(self, name: str, **path_params: Any) -> str:
        """Generate URL for a route by name (not implemented yet)"""
        # This would require route naming support
        raise NotImplementedError("url_for not implemented yet")
    
    def __repr__(self) -> str:
        return f"Request(method={self.method}, path={self.path})"