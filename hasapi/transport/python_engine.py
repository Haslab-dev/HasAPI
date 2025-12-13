"""
HasAPI Python Transport Engine

High-performance Python-native transport using:
- uvloop (required, not asyncio)
- httptools (HTTP parsing)
- orjson (JSON)

This is the best possible Python transport.
Used on Windows always, optional on Unix.
"""

from __future__ import annotations
import asyncio
import signal
import sys
from typing import Optional, Dict, Any, List, Tuple, TYPE_CHECKING

# uvloop is required, not optional
try:
    import uvloop
    HAS_UVLOOP = True
except ImportError:
    HAS_UVLOOP = False
    uvloop = None

# httptools for fast HTTP parsing
try:
    import httptools
    HAS_HTTPTOOLS = True
except ImportError:
    HAS_HTTPTOOLS = False
    httptools = None

from .base import TransportEngine, TransportConfig

if TYPE_CHECKING:
    from ..core.engine import ExecutionEngine
    from ..core.request import FastRequest


class HttpRequestParser:
    """HTTP request parser using httptools"""
    
    __slots__ = (
        'method', 'path', 'headers', 'body_chunks',
        'headers_complete', 'message_complete', '_current_header'
    )
    
    def __init__(self):
        self.method: Optional[str] = None
        self.path: Optional[str] = None
        self.headers: List[Tuple[bytes, bytes]] = []
        self.body_chunks: List[bytes] = []
        self.headers_complete = False
        self.message_complete = False
        self._current_header: Optional[bytes] = None
    
    def on_url(self, url: bytes):
        self.path = url.decode('latin-1')
    
    def on_header(self, name: bytes, value: bytes):
        self.headers.append((name, value))
    
    def on_headers_complete(self):
        self.headers_complete = True
    
    def on_body(self, body: bytes):
        self.body_chunks.append(body)
    
    def on_message_complete(self):
        self.message_complete = True
    
    def get_body(self) -> bytes:
        return b''.join(self.body_chunks)
    
    def reset(self):
        self.method = None
        self.path = None
        self.headers = []
        self.body_chunks = []
        self.headers_complete = False
        self.message_complete = False


class HttpProtocol(asyncio.Protocol):
    """
    High-performance HTTP protocol handler.
    
    Uses httptools for parsing, uvloop for async I/O.
    """
    
    __slots__ = (
        'transport', 'engine', 'config', 'parser', 'request_parser',
        '_keep_alive', '_request_count'
    )
    
    def __init__(self, engine: 'ExecutionEngine', config: TransportConfig):
        self.transport: Optional[asyncio.Transport] = None
        self.engine = engine
        self.config = config
        self.request_parser = HttpRequestParser()
        self.parser: Optional[httptools.HttpRequestParser] = None
        self._keep_alive = True
        self._request_count = 0
    
    def connection_made(self, transport: asyncio.Transport):
        self.transport = transport
        # Disable Nagle's algorithm for lower latency
        sock = transport.get_extra_info('socket')
        if sock is not None:
            import socket
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.parser = httptools.HttpRequestParser(self.request_parser)
    
    def connection_lost(self, exc):
        self.transport = None
    
    def data_received(self, data: bytes):
        try:
            self.parser.feed_data(data)
        except httptools.HttpParserError:
            self._send_error(400, b'Bad Request')
            return
        
        if self.request_parser.message_complete:
            # Get method from parser
            method = self.parser.get_method().decode('latin-1')
            self.request_parser.method = method
            
            # Check keep-alive from parser
            self._keep_alive = self.parser.should_keep_alive()
            
            # Process request
            asyncio.create_task(self._handle_request())
    
    async def _handle_request(self):
        """Process the parsed request"""
        from ..core.request import FastRequest
        
        # Parse path and query string
        path = self.request_parser.path
        query_string = b''
        if '?' in path:
            path, qs = path.split('?', 1)
            query_string = qs.encode('latin-1')
        
        # Create request object
        request = FastRequest(
            method=self.request_parser.method,
            path=path,
            headers_raw=self.request_parser.headers,
            query_string=query_string,
            body=self.request_parser.get_body()
        )
        
        try:
            # Execute through engine
            response = await self.engine.execute(request)
            
            # Send response
            await self._send_response(response)
        except Exception as e:
            self._send_error(500, str(e).encode())
        finally:
            # Reset for next request (keep-alive)
            self.request_parser.reset()
            self.parser = httptools.HttpRequestParser(self.request_parser)
            self._request_count += 1
            
            # Close if not keep-alive (no arbitrary limit)
            if not self._keep_alive:
                if self.transport:
                    self.transport.close()
    
    async def _send_response(self, response):
        """Send response to client"""
        if self.transport is None:
            return
        
        # Check if response has ASGI interface
        if hasattr(response, '__call__'):
            # Use ASGI-style sending
            await self._send_asgi_response(response)
        else:
            # Direct response
            self._send_raw_response(response)
    
    async def _send_asgi_response(self, response):
        """Send ASGI-compatible response"""
        status = 200
        headers = []
        body_parts = []
        
        async def receive():
            return {'type': 'http.request', 'body': b''}
        
        async def send(message):
            nonlocal status, headers, body_parts
            if message['type'] == 'http.response.start':
                status = message['status']
                headers = message.get('headers', [])
            elif message['type'] == 'http.response.body':
                body = message.get('body', b'')
                if body:
                    body_parts.append(body)
        
        await response({}, receive, send)
        
        body = b''.join(body_parts)
        self._write_http_response(status, headers, body)
    
    def _send_raw_response(self, response):
        """Send raw response object"""
        status = getattr(response, 'status', 200)
        headers = []
        
        if hasattr(response, 'headers'):
            for k, v in response.headers.items():
                headers.append((k.encode(), v.encode()))
        
        if hasattr(response, 'content_type'):
            headers.append((b'content-type', response.content_type.encode()))
        
        body = getattr(response, 'body', b'')
        headers.append((b'content-length', str(len(body)).encode()))
        
        self._write_http_response(status, headers, body)
    
    def _write_http_response(self, status: int, headers: List[Tuple[bytes, bytes]], body: bytes):
        """Write HTTP response to transport"""
        if self.transport is None:
            return
        
        # Add keep-alive header
        if self._keep_alive:
            headers.append((b'connection', b'keep-alive'))
        
        # Build response
        status_line = f'HTTP/1.1 {status} OK\r\n'.encode()
        header_lines = b''.join(
            name + b': ' + value + b'\r\n'
            for name, value in headers
        )
        
        response = status_line + header_lines + b'\r\n' + body
        self.transport.write(response)
    
    def _send_error(self, status: int, message: bytes):
        """Send error response"""
        if self.transport is None:
            return
        
        body = b'{"error": "' + message + b'"}'
        headers = [
            (b'content-type', b'application/json'),
            (b'content-length', str(len(body)).encode())
        ]
        self._write_http_response(status, headers, body)
        self.transport.close()


class PythonEngine(TransportEngine):
    """
    Python transport engine using uvloop + httptools.
    
    This is the best possible pure-Python transport.
    """
    
    def __init__(self, config: TransportConfig):
        super().__init__(config)
        self._server: Optional[asyncio.Server] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        
        # Validate requirements
        if not HAS_UVLOOP:
            raise RuntimeError(
                "uvloop is required for PythonEngine. "
                "Install with: pip install uvloop"
            )
        if not HAS_HTTPTOOLS:
            raise RuntimeError(
                "httptools is required for PythonEngine. "
                "Install with: pip install httptools"
            )
    
    @property
    def engine_name(self) -> str:
        return 'python (uvloop + httptools)'
    
    async def start(self) -> None:
        """Start the server"""
        if self._engine is None:
            raise RuntimeError("Execution engine not set")
        
        # Compile execution engine
        self._engine.compile()
        
        loop = asyncio.get_event_loop()
        
        # Create server
        self._server = await loop.create_server(
            lambda: HttpProtocol(self._engine, self.config),
            self.config.host,
            self.config.port,
            backlog=self.config.backlog,
            reuse_address=True,
            reuse_port=True if sys.platform != 'win32' else False
        )
        
        self._running = True
    
    async def stop(self) -> None:
        """Stop the server"""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        self._running = False
    
    def run(self) -> None:
        """Run the server (blocking)"""
        # Install uvloop
        uvloop.install()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        
        # Setup signal handlers
        if sys.platform != 'win32':
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, self._signal_handler)
        
        try:
            loop.run_until_complete(self.start())
            
            print(f"\n  HasAPI running on http://{self.config.host}:{self.config.port}")
            print(f"  Engine: {self.engine_name}")
            print(f"  Press Ctrl+C to stop\n")
            
            loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            loop.run_until_complete(self.stop())
            loop.close()
    
    def _signal_handler(self):
        """Handle shutdown signals"""
        self._loop.stop()
