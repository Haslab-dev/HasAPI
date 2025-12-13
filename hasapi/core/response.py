"""
HasAPI Fast Response - orjson-only, zero-copy where possible

Design principles:
- orjson only, no fallback
- Pre-computed headers where possible
- Minimal allocations
"""

from __future__ import annotations
import orjson
from typing import Dict, Any, Optional, Union, AsyncIterable

# Pre-computed common headers
_JSON_CONTENT_TYPE = b'application/json'
_HTML_CONTENT_TYPE = b'text/html; charset=utf-8'
_TEXT_CONTENT_TYPE = b'text/plain; charset=utf-8'
_SSE_CONTENT_TYPE = b'text/event-stream'

# Pre-computed header tuples for common cases
_JSON_HEADERS = [(b'content-type', _JSON_CONTENT_TYPE)]


def fast_json_response(
    data: Any,
    status: int = 200,
    headers: Dict[str, str] = None
) -> tuple:
    """
    Create JSON response tuple - HOT PATH.
    
    Returns (status, headers_list, body_bytes) for transport layer.
    """
    body = orjson.dumps(data, option=orjson.OPT_SERIALIZE_NUMPY | orjson.OPT_NON_STR_KEYS)
    
    if headers:
        headers_list = [(k.encode(), v.encode()) for k, v in headers.items()]
        headers_list.append((b'content-type', _JSON_CONTENT_TYPE))
    else:
        headers_list = _JSON_HEADERS.copy()
    
    headers_list.append((b'content-length', str(len(body)).encode()))
    
    return status, headers_list, body


class FastResponse:
    """
    Fast response object for ASGI compatibility.
    
    Use fast_json_response() for maximum performance when possible.
    """
    
    __slots__ = ('status', 'headers', 'body', 'content_type')
    
    def __init__(
        self,
        body: bytes = b'',
        status: int = 200,
        headers: Dict[str, str] = None,
        content_type: str = 'application/json'
    ):
        self.status = status
        self.body = body
        self.content_type = content_type
        self.headers = headers or {}
    
    async def __call__(self, scope: dict, receive: callable, send: callable):
        """ASGI interface"""
        headers_list = [
            (k.encode(), v.encode()) for k, v in self.headers.items()
        ]
        headers_list.append((b'content-type', self.content_type.encode()))
        headers_list.append((b'content-length', str(len(self.body)).encode()))
        
        await send({
            'type': 'http.response.start',
            'status': self.status,
            'headers': headers_list
        })
        
        await send({
            'type': 'http.response.body',
            'body': self.body
        })


class FastJSONResponse(FastResponse):
    """JSON response using orjson"""
    
    def __init__(
        self,
        data: Any,
        status: int = 200,
        headers: Dict[str, str] = None
    ):
        body = orjson.dumps(data, option=orjson.OPT_SERIALIZE_NUMPY | orjson.OPT_NON_STR_KEYS)
        super().__init__(body, status, headers, 'application/json')


class FastHTMLResponse(FastResponse):
    """HTML response"""
    
    def __init__(
        self,
        content: str,
        status: int = 200,
        headers: Dict[str, str] = None
    ):
        super().__init__(content.encode('utf-8'), status, headers, 'text/html; charset=utf-8')


class FastTextResponse(FastResponse):
    """Plain text response"""
    
    def __init__(
        self,
        content: str,
        status: int = 200,
        headers: Dict[str, str] = None
    ):
        super().__init__(content.encode('utf-8'), status, headers, 'text/plain; charset=utf-8')


class FastStreamingResponse:
    """Streaming response for async generators"""
    
    __slots__ = ('content', 'status', 'headers', 'content_type')
    
    def __init__(
        self,
        content: AsyncIterable,
        status: int = 200,
        headers: Dict[str, str] = None,
        content_type: str = 'text/plain'
    ):
        self.content = content
        self.status = status
        self.headers = headers or {}
        self.content_type = content_type
    
    async def __call__(self, scope: dict, receive: callable, send: callable):
        """ASGI interface for streaming"""
        headers_list = [
            (k.encode(), v.encode()) for k, v in self.headers.items()
        ]
        headers_list.append((b'content-type', self.content_type.encode()))
        
        await send({
            'type': 'http.response.start',
            'status': self.status,
            'headers': headers_list
        })
        
        async for chunk in self.content:
            if isinstance(chunk, str):
                chunk = chunk.encode('utf-8')
            await send({
                'type': 'http.response.body',
                'body': chunk,
                'more_body': True
            })
        
        await send({
            'type': 'http.response.body',
            'body': b''
        })


class FastSSEResponse(FastStreamingResponse):
    """Server-Sent Events response"""
    
    def __init__(
        self,
        content: AsyncIterable,
        status: int = 200,
        headers: Dict[str, str] = None
    ):
        headers = headers or {}
        headers['cache-control'] = 'no-cache'
        headers['connection'] = 'keep-alive'
        super().__init__(content, status, headers, 'text/event-stream')
