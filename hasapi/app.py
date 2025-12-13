"""
HasAPI - High-performance Python API framework

Features:
- Cached routing (dict lookups)
- Pre-bound handlers
- orjson serialization
- uvloop + httptools transport
"""

from __future__ import annotations
import asyncio
import sys
from typing import List, Callable, Optional, Dict, Any

from .core.engine import ExecutionEngine
from .core.router import CompiledRoute
from .core.request import FastRequest
from .core.response import (
    FastJSONResponse, FastHTMLResponse, FastTextResponse,
    FastStreamingResponse, FastSSEResponse
)
from .transport import create_engine, TransportConfig


class HasAPI:
    """
    High-performance HasAPI application.
    
    Usage:
        from hasapi import HasAPI
        
        app = HasAPI()
        
        @app.get("/")
        async def index(request):
            return {"message": "Hello, World!"}
        
        app.run()
    """
    
    __slots__ = (
        'title', 'version', 'debug', 'docs_enabled',
        '_engine', '_transport_config', '_transport_type',
        '_startup_handlers', '_shutdown_handlers'
    )
    
    def __init__(
        self,
        title: str = "HasAPI",
        version: str = "1.0.0",
        debug: bool = False,
        docs: bool = True,
        host: str = '127.0.0.1',
        port: int = 8000
    ):
        self.title = title
        self.version = version
        self.debug = debug
        self.docs_enabled = docs
        
        self._engine = ExecutionEngine()
        self._transport_type = 'python'
        self._transport_config = TransportConfig(
            host=host,
            port=port,
            debug=debug
        )
        
        self._startup_handlers: List[Callable] = []
        self._shutdown_handlers: List[Callable] = []
        
        if docs:
            self._setup_docs()
    
    def route(self, path: str, methods: List[str] = None) -> Callable:
        """Register a route"""
        if methods is None:
            methods = ['GET']
        
        def decorator(handler: Callable) -> Callable:
            self._engine.add_route(path, handler, methods)
            return handler
        return decorator
    
    def get(self, path: str) -> Callable:
        """Register GET route"""
        return self.route(path, ['GET'])
    
    def post(self, path: str) -> Callable:
        """Register POST route"""
        return self.route(path, ['POST'])
    
    def put(self, path: str) -> Callable:
        """Register PUT route"""
        return self.route(path, ['PUT'])
    
    def delete(self, path: str) -> Callable:
        """Register DELETE route"""
        return self.route(path, ['DELETE'])
    
    def patch(self, path: str) -> Callable:
        """Register PATCH route"""
        return self.route(path, ['PATCH'])
    
    def options(self, path: str) -> Callable:
        """Register OPTIONS route"""
        return self.route(path, ['OPTIONS'])
    
    def head(self, path: str) -> Callable:
        """Register HEAD route"""
        return self.route(path, ['HEAD'])
    
    def on_startup(self, handler: Callable) -> Callable:
        """Register startup handler"""
        self._startup_handlers.append(handler)
        return handler
    
    def on_shutdown(self, handler: Callable) -> Callable:
        """Register shutdown handler"""
        self._shutdown_handlers.append(handler)
        return handler
    
    def _setup_docs(self) -> None:
        """Setup OpenAPI documentation endpoints"""
        
        @self.get('/openapi.json')
        async def openapi_spec(request: FastRequest):
            return self._generate_openapi()
        
        @self.get('/docs')
        async def swagger_ui(request: FastRequest):
            html = f'''<!DOCTYPE html>
<html>
<head>
    <title>{self.title} - API Docs</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
        SwaggerUIBundle({{
            url: '/openapi.json',
            dom_id: '#swagger-ui',
            presets: [SwaggerUIBundle.presets.apis],
            layout: "BaseLayout"
        }});
    </script>
</body>
</html>'''
            return FastHTMLResponse(html)
    
    def _generate_openapi(self) -> Dict[str, Any]:
        """Generate OpenAPI specification"""
        paths = {}
        
        for route in self._engine.get_routes():
            if route.path.startswith('/openapi') or route.path.startswith('/docs'):
                continue
            
            path_item = {}
            for method in route.methods:
                method_lower = method.lower()
                path_item[method_lower] = {
                    'summary': route.handler.__name__,
                    'responses': {
                        '200': {
                            'description': 'Successful response',
                            'content': {'application/json': {'schema': {'type': 'object'}}}
                        }
                    }
                }
                
                if route.param_names:
                    path_item[method_lower]['parameters'] = [
                        {
                            'name': param,
                            'in': 'path',
                            'required': True,
                            'schema': {'type': 'string'}
                        }
                        for param in route.param_names
                    ]
            
            paths[route.path] = path_item
        
        return {
            'openapi': '3.0.0',
            'info': {'title': self.title, 'version': self.version},
            'paths': paths
        }
    
    def run(self, host: str = None, port: int = None) -> None:
        """Run the application."""
        if host:
            self._transport_config.host = host
        if port:
            self._transport_config.port = port
        
        transport = create_engine(self._transport_config)
        transport.set_execution_engine(self._engine)
        transport.run()
    
    async def __call__(self, scope: dict, receive: callable, send: callable) -> None:
        """ASGI interface for uvicorn compatibility."""
        if scope['type'] == 'http':
            self._engine.compile()
            request = FastRequest.from_scope(scope, receive)
            response = await self._engine.execute(request)
            await response(scope, receive, send)
        
        elif scope['type'] == 'lifespan':
            message = await receive()
            if message['type'] == 'lifespan.startup':
                for handler in self._startup_handlers:
                    if asyncio.iscoroutinefunction(handler):
                        await handler()
                    else:
                        handler()
                await send({'type': 'lifespan.startup.complete'})
            elif message['type'] == 'lifespan.shutdown':
                for handler in self._shutdown_handlers:
                    if asyncio.iscoroutinefunction(handler):
                        await handler()
                    else:
                        handler()
                await send({'type': 'lifespan.shutdown.complete'})
