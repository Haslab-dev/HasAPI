"""
HasAPI Response Module

Provides various response types including JSON, streaming, and file responses.
"""

import json
import asyncio
from typing import Any, Dict, List, Optional, Union, AsyncIterable, Callable
from dataclasses import dataclass

import orjson

from .utils import get_logger

logger = get_logger(__name__)


@dataclass
class Response:
    """Base response class"""
    status_code: int = 200
    headers: Optional[Dict[str, str]] = None
    content: bytes = b""
    
    def __post_init__(self):
        if self.headers is None:
            self.headers = {}
    
    async def __call__(self, scope: dict, receive: callable, send: callable):
        """ASGI callable for the response"""
        # Send response start
        await send({
            "type": "http.response.start",
            "status": self.status_code,
            "headers": [
                (name.encode("utf-8"), value.encode("utf-8"))
                for name, value in self.headers.items()
            ],
        })
        
        # Send response body
        await send({
            "type": "http.response.body",
            "body": self.content,
        })


class JSONResponse(Response):
    """JSON response using orjson for maximum performance"""
    
    def __init__(
        self, 
        content: Any = None, 
        status_code: int = 200, 
        headers: Optional[Dict[str, str]] = None,
        ensure_ascii: bool = False
    ):
        if content is None:
            content = {}
        
        # Convert to JSON bytes using orjson for speed
        try:
            content_bytes = orjson.dumps(content, option=orjson.OPT_SERIALIZE_NUMPY | orjson.OPT_NON_STR_KEYS)
        except (TypeError, ValueError):
            # Fallback to standard json if orjson fails
            content_bytes = json.dumps(
                content, 
                ensure_ascii=ensure_ascii,
                default=str
            ).encode("utf-8")
        
        # Set headers
        if headers is None:
            headers = {}
        
        headers.setdefault("content-type", "application/json; charset=utf-8")
        
        super().__init__(
            status_code=status_code,
            headers=headers,
            content=content_bytes
        )


class HTMLResponse(Response):
    """HTML response"""
    
    def __init__(
        self, 
        content: str = "", 
        status_code: int = 200, 
        headers: Optional[Dict[str, str]] = None
    ):
        if headers is None:
            headers = {}
        
        headers.setdefault("content-type", "text/html; charset=utf-8")
        
        super().__init__(
            status_code=status_code,
            headers=headers,
            content=content.encode("utf-8")
        )


class PlainTextResponse(Response):
    """Plain text response"""
    
    def __init__(
        self, 
        content: str = "", 
        status_code: int = 200, 
        headers: Optional[Dict[str, str]] = None
    ):
        if headers is None:
            headers = {}
        
        headers.setdefault("content-type", "text/plain; charset=utf-8")
        
        super().__init__(
            status_code=status_code,
            headers=headers,
            content=content.encode("utf-8")
        )


class StreamingResponse(Response):
    """Streaming response for async generators"""
    
    def __init__(
        self,
        content: Union[AsyncIterable[str], AsyncIterable[bytes], Callable],
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        media_type: str = "text/plain"
    ):
        super().__init__(status_code=status_code, headers=headers)
        self.content = content
        self.media_type = media_type
        
        if self.headers is None:
            self.headers = {}
        
        self.headers.setdefault("content-type", f"{media_type}; charset=utf-8")
    
    async def __call__(self, scope: dict, receive: callable, send: callable):
        """ASGI callable for streaming response"""
        # Send response start (no content-length for streaming)
        await send({
            "type": "http.response.start",
            "status": self.status_code,
            "headers": [
                (name.encode("utf-8"), value.encode("utf-8"))
                for name, value in self.headers.items()
            ],
        })
        
        # Stream content
        try:
            if callable(self.content):
                # If content is a callable, call it to get the async generator
                async for chunk in self.content():
                    if isinstance(chunk, str):
                        chunk = chunk.encode("utf-8")
                    await send({
                        "type": "http.response.body",
                        "body": chunk,
                        "more_body": True,
                    })
            else:
                # Content is already an async iterable
                async for chunk in self.content:
                    if isinstance(chunk, str):
                        chunk = chunk.encode("utf-8")
                    await send({
                        "type": "http.response.body",
                        "body": chunk,
                        "more_body": True,
                    })
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            # Try to send an error message if possible
            try:
                error_msg = f"Error: {str(e)}".encode("utf-8")
                await send({
                    "type": "http.response.body",
                    "body": error_msg,
                    "more_body": True,
                })
            except:
                pass
        
        # Send final empty body to close the stream
        await send({
            "type": "http.response.body",
            "body": b"",
        })


class ServerSentEventResponse(StreamingResponse):
    """Server-Sent Events (SSE) response for real-time updates"""
    
    def __init__(
        self,
        content: Union[AsyncIterable[Dict[str, Any]], Callable],
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None
    ):
        if headers is None:
            headers = {}
        
        headers.setdefault("cache-control", "no-cache")
        headers.setdefault("connection", "keep-alive")
        headers.setdefault("content-type", "text/event-stream")
        
        super().__init__(content, status_code, headers, "text/event-stream")
    
    async def _format_sse(self, data: Any, event: Optional[str] = None, id: Optional[str] = None) -> str:
        """Format data as Server-Sent Event"""
        lines = []
        
        if event:
            lines.append(f"event: {event}")
        
        if id:
            lines.append(f"id: {id}")
        
        # Handle multi-line data
        data_str = str(data)
        for line in data_str.split("\n"):
            lines.append(f"data: {line}")
        
        lines.append("")  # Empty line to end the event
        return "\n".join(lines)
    
    async def __call__(self, scope: dict, receive: callable, send: callable):
        """ASGI callable for SSE response"""
        # Send response start
        await send({
            "type": "http.response.start",
            "status": self.status_code,
            "headers": [
                (name.encode("utf-8"), value.encode("utf-8"))
                for name, value in self.headers.items()
            ],
        })
        
        # Stream SSE events
        try:
            if callable(self.content):
                async for event_data in self.content():
                    if isinstance(event_data, dict):
                        event = event_data.get("event")
                        data = event_data.get("data")
                        id = event_data.get("id")
                        sse_formatted = await self._format_sse(data, event, id)
                    else:
                        sse_formatted = await self._format_sse(event_data)
                    
                    await send({
                        "type": "http.response.body",
                        "body": sse_formatted.encode("utf-8"),
                        "more_body": True,
                    })
            else:
                async for event_data in self.content:
                    if isinstance(event_data, dict):
                        event = event_data.get("event")
                        data = event_data.get("data")
                        id = event_data.get("id")
                        sse_formatted = await self._format_sse(data, event, id)
                    else:
                        sse_formatted = await self._format_sse(event_data)
                    
                    await send({
                        "type": "http.response.body",
                        "body": sse_formatted.encode("utf-8"),
                        "more_body": True,
                    })
        except Exception as e:
            logger.error(f"SSE streaming error: {e}")
            # Try to send an error event
            try:
                error_event = await self._format_sse(f"Error: {str(e)}", event="error")
                await send({
                    "type": "http.response.body",
                    "body": error_event.encode("utf-8"),
                    "more_body": True,
                })
            except:
                pass
        
        # Send final empty body
        await send({
            "type": "http.response.body",
            "body": b"",
        })


class FileResponse(Response):
    """File response for serving static files"""
    
    def __init__(
        self,
        path: str,
        filename: Optional[str] = None,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        chunk_size: int = 65536  # 64KB
    ):
        self.path = path
        self.filename = filename or path.split("/")[-1]
        self.chunk_size = chunk_size
        
        if headers is None:
            headers = {}
        
        # Try to determine content type
        import mimetypes
        content_type, _ = mimetypes.guess_type(path)
        if content_type:
            headers.setdefault("content-type", content_type)
        
        super().__init__(status_code=status_code, headers=headers)
    
    async def __call__(self, scope: dict, receive: callable, send: callable):
        """ASGI callable for file response"""
        try:
            import os
            file_size = os.path.getsize(self.path)
            
            # Update content-length header
            self.headers["content-length"] = str(file_size)
            
            # Send response start
            await send({
                "type": "http.response.start",
                "status": self.status_code,
                "headers": [
                    (name.encode("utf-8"), value.encode("utf-8"))
                    for name, value in self.headers.items()
                ],
            })
            
            # Stream file content
            with open(self.path, "rb") as f:
                while True:
                    chunk = f.read(self.chunk_size)
                    if not chunk:
                        break
                    
                    await send({
                        "type": "http.response.body",
                        "body": chunk,
                        "more_body": True,
                    })
            
            # Send final empty body
            await send({
                "type": "http.response.body",
                "body": b"",
            })
        
        except Exception as e:
            logger.error(f"File response error: {e}")
            # Send error response
            error_response = JSONResponse(
                {"detail": f"File not found: {str(e)}"},
                status_code=404
            )
            await error_response(scope, receive, send)


class RedirectResponse(Response):
    """HTTP redirect response"""
    
    def __init__(self, url: str, status_code: int = 302):
        super().__init__(
            status_code=status_code,
            headers={"location": url},
            content=b""
        )