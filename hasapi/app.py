"""
HasAPI Core Application
"""

import asyncio
import inspect
from typing import Dict, List, Callable, Any, Optional, Union, Awaitable
from urllib.parse import parse_qs

from .router import Router, Route
from .response import Response, JSONResponse
from .middleware import MiddlewareStack
from .websocket import WebSocket
from .exceptions import HTTPException, NotFoundException
from .utils import get_logger

logger = get_logger(__name__)


class HasAPI:
    """
    Main HasAPI application class.
    
    This is the core ASGI application that handles routing, middleware,
    and request processing.
    """
    
    def __init__(self, title: str = "HasAPI", version: str = "0.0.1", debug: bool = False, docs: bool = True):
        self.title = title
        self.version = version
        self.debug = debug
        self.docs_enabled = docs
        
        self.router = Router()
        self.middleware_stack = MiddlewareStack()
        self.state = {}
        self.startup_handlers = []
        self.shutdown_handlers = []
        
        # Built-in middleware
        self._setup_builtin_middleware()
        
        # Setup automatic docs if enabled
        if self.docs_enabled:
            self._setup_docs()
    
    def _setup_builtin_middleware(self):
        """Setup built-in middleware"""
        # Error handling middleware is always added
        from .middleware.base import middleware
        self.middleware_stack.add(middleware(self._error_handler))
    
    def route(self, path: str, methods: List[str] = None):
        """Decorator for registering routes"""
        if methods is None:
            methods = ["GET"]
        
        def decorator(func):
            self.router.add_route(path, func, methods)
            return func
        return decorator
    
    def get(self, path: str):
        """Decorator for GET routes"""
        return self.route(path, ["GET"])
    
    def post(self, path: str):
        """Decorator for POST routes"""
        return self.route(path, ["POST"])
    
    def put(self, path: str):
        """Decorator for PUT routes"""
        return self.route(path, ["PUT"])
    
    def delete(self, path: str):
        """Decorator for DELETE routes"""
        return self.route(path, ["DELETE"])
    
    def patch(self, path: str):
        """Decorator for PATCH routes"""
        return self.route(path, ["PATCH"])
    
    def options(self, path: str):
        """Decorator for OPTIONS routes"""
        return self.route(path, ["OPTIONS"])
    
    def head(self, path: str):
        """Decorator for HEAD routes"""
        return self.route(path, ["HEAD"])
    
    def docs(self, path: str = "/docs"):
        """Decorator for documentation routes"""
        def decorator(func):
            async def docs_handler(request):
                spec = self.get_openapi_spec()
                from .docs import generate_swagger_ui
                ui_html = generate_swagger_ui(spec)
                from .response import HTMLResponse
                return HTMLResponse(ui_html)
            
            # Register the route
            self.route(path, ["GET"])(docs_handler)
            return func
        
        return decorator
    
    def openapi(self, path: str = "/openapi.json"):
        """Decorator for OpenAPI JSON route"""
        def decorator(func):
            async def openapi_handler(request):
                spec = self.get_openapi_spec()
                from .response import JSONResponse
                return JSONResponse(spec)
            
            # Register the route
            self.route(path, ["GET"])(openapi_handler)
            return func
        
        return decorator
    
    def websocket(self, path: str):
        """Decorator for WebSocket routes"""
        def decorator(func):
            self.router.add_websocket_route(path, func)
            return func
        return decorator
    
    def middleware(self, middleware_class):
        """Add middleware to the application"""
        self.middleware_stack.add(middleware_class)
        return middleware_class
    
    def on_event(self, event_type: str):
        """Decorator for startup/shutdown event handlers"""
        def decorator(func):
            if event_type == "startup":
                self.startup_handlers.append(func)
            elif event_type == "shutdown":
                self.shutdown_handlers.append(func)
            else:
                raise ValueError(f"Unknown event type: {event_type}")
            return func
        return decorator
    
    async def startup(self):
        """Run startup handlers"""
        for handler in self.startup_handlers:
            if inspect.iscoroutinefunction(handler):
                await handler()
            else:
                handler()
    
    async def shutdown(self):
        """Run shutdown handlers"""
        for handler in self.shutdown_handlers:
            if inspect.iscoroutinefunction(handler):
                await handler()
            else:
                handler()
    
    async def __call__(self, scope, receive, send):
        """ASGI application entry point"""
        if scope["type"] == "http":
            await self._handle_http(scope, receive, send)
        elif scope["type"] == "websocket":
            await self._handle_websocket(scope, receive, send)
        elif scope["type"] == "lifespan":
            await self._handle_lifespan(scope, receive, send)
        else:
            raise ValueError(f"Unsupported scope type: {scope['type']}")
    
    async def _handle_http(self, scope, receive, send):
        """Handle HTTP requests"""
        try:
            # Find route first (before creating request object)
            route, path_params = self.router.match_route(
                scope["method"], scope["path"]
            )
            
            if not route:
                raise NotFoundException(f"Route {scope['method']} {scope['path']} not found")
            
            # Create request object only after route is found
            request = Request(scope, receive)
            
            # Apply middleware
            response = await self.middleware_stack.process_request(
                request, route.handler, path_params
            )
            
            # Send response
            await response(scope, receive, send)
            
        except Exception as exc:
            await self._handle_exception(exc, scope, receive, send)
    
    async def _handle_websocket(self, scope, receive, send):
        """Handle WebSocket connections"""
        try:
            # Find WebSocket route
            ws_route = self.router.match_websocket_route(scope["path"])
            
            if not ws_route:
                await WebSocket({"type": "websocket.close"}, receive, send).close(code=404)
                return
            
            # Create WebSocket object
            websocket = WebSocket(scope, receive, send)
            
            # Call WebSocket handler
            await ws_route.handler(websocket)
            
        except Exception as exc:
            logger.error(f"WebSocket error: {exc}")
            try:
                await WebSocket({"type": "websocket.close"}, receive, send).close(code=1011)
            except:
                pass
    
    async def _handle_lifespan(self, scope, receive, send):
        """Handle lifespan events (startup/shutdown)"""
        message = await receive()
        if message["type"] == "lifespan.startup":
            await self.startup()
            await send({"type": "lifespan.startup.complete"})
        elif message["type"] == "lifespan.shutdown":
            await self.shutdown()
            await send({"type": "lifespan.shutdown.complete"})
    
    async def _handle_exception(self, exc, scope, receive, send):
        """Handle exceptions during request processing"""
        if isinstance(exc, HTTPException):
            response = JSONResponse(
                {"detail": exc.detail}, 
                status_code=exc.status_code
            )
        else:
            logger.error(f"Unhandled exception: {exc}")
            response = JSONResponse(
                {"detail": "Internal Server Error"}, 
                status_code=500
            )
        
        await response(scope, receive, send)
    
    async def _error_handler(self, request, call_next, **kwargs):
        """Built-in error handling middleware"""
        try:
            return await call_next(request, **kwargs)
        except HTTPException:
            raise  # Re-raise HTTP exceptions
        except Exception as exc:
            logger.error(f"Unhandled exception in middleware: {exc}")
            return JSONResponse(
                {"detail": "Internal Server Error"}, 
                status_code=500
            )
    
    def _setup_docs(self):
        """Setup automatic OpenAPI documentation endpoints"""
        from .docs import generate_openapi_spec
        from .response import HTMLResponse
        
        # Add OpenAPI spec endpoint
        @self.get("/openapi.json")
        async def openapi_spec(request):
            """OpenAPI specification"""
            spec = generate_openapi_spec(self)
            return JSONResponse(spec)
        
        # Add Swagger UI endpoint
        @self.get("/docs")
        async def swagger_ui(request):
            """Swagger UI documentation"""
            html = """
<!DOCTYPE html>
<html>
<head>
    <title>API Documentation - {title}</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
    <style>
        body {{ margin: 0; padding: 0; }}
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
        window.onload = function() {{
            const ui = SwaggerUIBundle({{
                url: '/openapi.json',
                dom_id: '#swagger-ui',
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIBundle.SwaggerUIStandalonePreset
                ],
                layout: "BaseLayout",
                deepLinking: true
            }});
        }}
    </script>
</body>
</html>
            """.format(title=self.title)
            return HTMLResponse(html)


# Import Request class to avoid circular imports
from .request import Request
from .docs import generate_openapi_spec, generate_swagger_ui